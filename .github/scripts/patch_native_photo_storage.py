from pathlib import Path
import re
import sys

main = Path("app/src/main/java/com/situsnap/app/MainActivity.java")
gradle = Path("app/build.gradle")
manifest = Path("app/src/main/AndroidManifest.xml")
if not main.is_file() or not gradle.is_file() or not manifest.is_file():
    raise SystemExit("FAIL: generated Android project is missing expected files")

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"FAIL: expected exactly one match for {label}; found {count}; no source written")
    return source.replace(old, new, 1)

s = main.read_text(encoding="utf-8")
# Fail closed if the generator changes. Every transformation below is checked.
s = replace_once(s, "import android.content.ContentValues;\n", "", "ContentValues import")
s = replace_once(s, "import android.provider.MediaStore;\n", "", "MediaStore import")
s = replace_once(s, "camera.putExtra(MediaStore.EXTRA_OUTPUT, cameraOutputUri);",
                  "camera.putExtra(android.provider.MediaStore.EXTRA_OUTPUT, cameraOutputUri);",
                  "camera EXTRA_OUTPUT reference")
if "import androidx.core.content.FileProvider;" not in s:
    s = replace_once(s, "import android.net.Uri;\n",
        "import android.net.Uri;\nimport java.io.File;\nimport androidx.core.content.FileProvider;\n",
        "URI import anchor")
s = replace_once(s, "    private Uri cameraOutputUri;\n",
                 "    private Uri cameraOutputUri;\n    private File cameraOutputFile;\n",
                 "camera output field")
old = '''                        ContentValues values = new ContentValues();
                        values.put(MediaStore.Images.Media.DISPLAY_NAME,
                                "SituSnap_" + System.currentTimeMillis() + ".jpg");
                        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
                        cameraOutputUri = getContentResolver().insert(
                                MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);

                        if (cameraOutputUri != null) {
                            Intent camera = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);'''
new = '''                        // Capture into app-private cache, never shared Gallery/MediaStore.
                        File photoDir = new File(getCacheDir(), "situsnap-camera");
                        if (photoDir.exists() && photoDir.isDirectory()) {
                            File[] oldCaptures = photoDir.listFiles();
                            if (oldCaptures != null) {
                                long staleBefore = System.currentTimeMillis() - 7L * 24 * 60 * 60 * 1000;
                                for (File oldCapture : oldCaptures) {
                                    if (oldCapture.isFile() && oldCapture.lastModified() < staleBefore) {
                                        try { oldCapture.delete(); } catch (Exception ignored) {}
                                    }
                                }
                            }
                        }
                        if (!photoDir.exists() && !photoDir.mkdirs()) {
                            throw new java.io.IOException("Could not create private photo cache");
                        }
                        cameraOutputFile = new File(photoDir, "capture_" + System.currentTimeMillis() + ".jpg");
                        if (!cameraOutputFile.createNewFile()) {
                            throw new java.io.IOException("Could not create private capture file");
                        }
                        cameraOutputUri = FileProvider.getUriForFile(
                                MainActivity.this, getPackageName() + ".photos", cameraOutputFile);

                        if (cameraOutputUri != null) {
                            Intent camera = new Intent(android.provider.MediaStore.ACTION_IMAGE_CAPTURE);'''
s = replace_once(s, old, new, "legacy MediaStore camera creation block")
s = replace_once(s, '''                    cameraOutputUri = null;
                    return false;''',
'''                    cameraOutputUri = null;
                    if (cameraOutputFile != null) {
                        try { cameraOutputFile.delete(); } catch (Exception ignored) {}
                    }
                    cameraOutputFile = null;
                    return false;''', "camera launch failure cleanup")
old2 = '''                if (resultCode == RESULT_OK && cameraOutputUri != null) {
                    fileCallback.onReceiveValue(new Uri[]{cameraOutputUri});
                } else {
                    if (cameraOutputUri != null) {
                        try { getContentResolver().delete(cameraOutputUri, null, null); }
                        catch (Exception ignored) {}
                    }
                    fileCallback.onReceiveValue(null);
                }'''
new2 = '''                if (resultCode == RESULT_OK && cameraOutputUri != null
                        && cameraOutputFile != null && cameraOutputFile.isFile()
                        && cameraOutputFile.length() > 0) {
                    // Return the private content URI. Keep the original until a future
                    // camera launch's seven-day stale-file sweep; the user may finish
                    // the form later, and JavaScript reads the file when saving to IndexedDB.
                    fileCallback.onReceiveValue(new Uri[]{cameraOutputUri});
                } else {
                    if (cameraOutputFile != null) {
                        try { cameraOutputFile.delete(); } catch (Exception ignored) {}
                    }
                    fileCallback.onReceiveValue(null);
                }'''
s = replace_once(s, old2, new2, "camera result handling")
s = replace_once(s, '''            cameraCapturePending = false;
            cameraOutputUri = null;
        }
    }''',
'''            cameraCapturePending = false;
            cameraOutputUri = null;
            cameraOutputFile = null;
        }
    }''', "camera state reset")
if "MediaStore.Images.Media.EXTERNAL_CONTENT_URI" in s:
    raise SystemExit("FAIL: legacy shared-gallery insertion remains")
if "FileProvider.getUriForFile" not in s or "situsnap-camera" not in s:
    raise SystemExit("FAIL: private camera storage wiring is missing")
main.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
if "androidx.core:core:" not in g:
    g += '\n\ndependencies {\n    implementation "androidx.core:core:1.13.1"\n}\n'
gradle.write_text(g, encoding="utf-8")

gradle_properties = Path("gradle.properties")
gp = gradle_properties.read_text(encoding="utf-8") if gradle_properties.exists() else ""
if not re.search(r"(?m)^android\\.useAndroidX\\s*=\\s*true\\s*$", gp):
    gp = gp.rstrip() + "\nandroid.useAndroidX=true\n"
gradle_properties.write_text(gp, encoding="utf-8")

m = manifest.read_text(encoding="utf-8")
# Android 11+ package visibility can hide camera apps from resolveActivity().
# Declare the exact camera action so the native private-capture path can find
# an installed camera app instead of silently falling through to the file picker.
camera_query = '<intent><action android:name="android.media.action.IMAGE_CAPTURE" /></intent>'
if "android.media.action.IMAGE_CAPTURE" not in m:
    if "</queries>" in m:
        m = replace_once(m, "</queries>", camera_query + "\\n</queries>", "camera visibility query")
    elif "<application" in m:
        m = replace_once(m, "<application", "<queries>" + camera_query + "</queries>\\n<application", "manifest application opening")
    else:
        raise SystemExit("FAIL: manifest application opening tag not found for camera visibility query")
provider = '''<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="${applicationId}.photos"
    android:exported="false"
    android:grantUriPermissions="true">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/situsnap_photo_paths"/>
</provider>'''
if "androidx.core.content.FileProvider" not in m:
    if "</application>" not in m:
        raise SystemExit("FAIL: manifest application closing tag not found")
    m = replace_once(m, "</application>", provider + "\n</application>", "manifest application closing tag")
elif 'android:authorities="${applicationId}.photos"' not in m:
    raise SystemExit("FAIL: existing FileProvider authority is not applicationId-based")
manifest.write_text(m, encoding="utf-8")

paths = Path("app/src/main/res/xml/situsnap_photo_paths.xml")
paths.parent.mkdir(parents=True, exist_ok=True)
paths.write_text('''<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <cache-path name="situsnap_camera" path="situsnap-camera/"/>
</paths>
''', encoding="utf-8")

# Explicit checks cannot be disabled with python -O.
checks = {
    "no legacy gallery insert": "MediaStore.Images.Media.EXTERNAL_CONTENT_URI" not in s,
    "FileProvider call present": "FileProvider.getUriForFile" in s,
    "private FileProvider manifest entry": "androidx.core.content.FileProvider" in m,
    "applicationId-based authority": 'android:authorities="${applicationId}.photos"' in m,
    "FileProvider paths resource": "situsnap_photo_paths" in m,
    "AndroidX dependency": "androidx.core:core:" in g,
    "private paths XML exists": paths.is_file(),
    "camera visibility query": "android.media.action.IMAGE_CAPTURE" in m,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("FAIL: " + ", ".join(failed))
print("PASS: private camera capture, guarded source replacements, appId-based provider and bounded stale-file cleanup")
