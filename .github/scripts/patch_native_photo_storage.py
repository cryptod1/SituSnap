from pathlib import Path
import re

main = Path("app/src/main/java/com/situsnap/app/MainActivity.java")
gradle = Path("app/build.gradle")
manifest = Path("app/src/main/AndroidManifest.xml")
if not main.is_file() or not gradle.is_file() or not manifest.is_file():
    raise SystemExit("FAIL: generated Android project is missing expected files")

s = main.read_text(encoding="utf-8")
s = s.replace("import android.content.ContentValues;\n", "")
s = s.replace("import android.provider.MediaStore;\n", "")
if "import androidx.core.content.FileProvider;" not in s:
    s = s.replace("import android.net.Uri;\n", "import android.net.Uri;\nimport android.os.Handler;\nimport android.os.Looper;\nimport java.io.File;\nimport androidx.core.content.FileProvider;\n")
s = s.replace("    private Uri cameraOutputUri;\n", "    private Uri cameraOutputUri;\n    private File cameraOutputFile;\n")
old = '''                        ContentValues values = new ContentValues();
                        values.put(MediaStore.Images.Media.DISPLAY_NAME,
                                "SituSnap_" + System.currentTimeMillis() + ".jpg");
                        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
                        cameraOutputUri = getContentResolver().insert(
                                MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);

                        if (cameraOutputUri != null) {
                            Intent camera = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);'''
new = '''                        // Capture into app-private cache, never the shared Gallery/MediaStore.
                        File photoDir = new File(getCacheDir(), "situsnap-camera");
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
if old not in s:
    raise SystemExit("FAIL: expected MediaStore camera block not found; no source changed")
s = s.replace(old, new, 1)
s = s.replace('''                    cameraOutputUri = null;
                    return false;''', '''                    cameraOutputUri = null;
                    if (cameraOutputFile != null) cameraOutputFile.delete();
                    cameraOutputFile = null;
                    return false;''', 1)
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
                    fileCallback.onReceiveValue(new Uri[]{cameraOutputUri});
                    // WebView reads the content URI asynchronously. Keep it briefly, then
                    // remove the private temporary original; the app's IndexedDB copy is
                    // the durable record photo. It is never published to Gallery.
                    final File temporaryCapture = cameraOutputFile;
                    new Handler(Looper.getMainLooper()).postDelayed(() -> {
                        try { if (temporaryCapture.exists()) temporaryCapture.delete(); }
                        catch (Exception ignored) {}
                    }, 120000L);
                } else {
                    if (cameraOutputFile != null) {
                        try { cameraOutputFile.delete(); } catch (Exception ignored) {}
                    }
                    fileCallback.onReceiveValue(null);
                }'''
if old2 not in s:
    raise SystemExit("FAIL: expected camera result block not found; no source changed")
s = s.replace(old2, new2, 1)
s = s.replace('''            cameraCapturePending = false;
            cameraOutputUri = null;
        }
    }''', '''            cameraCapturePending = false;
            cameraOutputUri = null;
            cameraOutputFile = null;
        }
    }''', 1)
main.write_text(s, encoding="utf-8")

g = gradle.read_text(encoding="utf-8")
if "androidx.core:core:" not in g:
    g += '\n\ndependencies {\n    implementation "androidx.core:core:1.13.1"\n}\n'
gradle.write_text(g, encoding="utf-8")

m = manifest.read_text(encoding="utf-8")
provider = '''<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="com.situsnap.app.photos"
    android:exported="false"
    android:grantUriPermissions="true">
    <meta-data
        android:name="android.support.FILE_PROVIDER_PATHS"
        android:resource="@xml/situsnap_photo_paths"/>
</provider>'''
if "androidx.core.content.FileProvider" not in m:
    m = m.replace("</application>", provider + "\n</application>")
manifest.write_text(m, encoding="utf-8")

paths = Path("app/src/main/res/xml/situsnap_photo_paths.xml")
paths.write_text('''<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <cache-path name="situsnap_camera" path="situsnap-camera/"/>
</paths>
''', encoding="utf-8")

# Guardrails: fail the build if shared-gallery capture remains or private provider wiring is missing.
assert "MediaStore.Images.Media.EXTERNAL_CONTENT_URI" not in s
assert "FileProvider.getUriForFile" in s
assert "androidx.core.content.FileProvider" in m
assert "situsnap_photo_paths" in m
assert "androidx.core:core:" in g
print("PASS: native camera captures to app-private cache; no shared Gallery/MediaStore insert")
