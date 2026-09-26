from pathlib import Path

def put(name, data):
    p = Path(name)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(data, encoding="utf-8")

put("settings.gradle", """pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement { repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); repositories { google(); mavenCentral() } }
rootProject.name='SituSnap'
include ':app'
""")

put("build.gradle", """plugins {
    id 'com.android.application' version '8.7.3' apply false
}
""")

put("app/build.gradle", """plugins {
    id 'com.android.application'
}
android {
    namespace 'com.situsnap.app'
    compileSdk 35
    defaultConfig {
        applicationId 'com.situsnap.app'
        minSdk 26
        targetSdk 35
        versionCode 7
        versionName '1.0.7'
    }

    signingConfigs {
        release {
            storeFile file('../situsnap-release.jks')
            storePassword System.getenv('SITUSNAP_STORE_PASSWORD')
            keyAlias System.getenv('SITUSNAP_KEY_ALIAS')
            keyPassword System.getenv('SITUSNAP_KEY_PASSWORD')
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
        }
    }
}
""")

put("app/src/main/res/values/styles.xml", """<resources>
<style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar">
<item name="android:statusBarColor">#07192b</item>
<item name="android:navigationBarColor">#07192b</item>
</style>
</resources>
""")
put("app/src/main/AndroidManifest.xml", """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.CAMERA"/>
<application android:theme="@style/AppTheme" android:label="SituSnap" android:usesCleartextTraffic="false">
<activity android:name=".MainActivity" android:exported="true">
<intent-filter>
<action android:name="android.intent.action.MAIN"/>
<category android:name="android.intent.category.LAUNCHER"/>
</intent-filter>
</activity>
</application>
</manifest>
""")
put("app/src/main/java/com/situsnap/app/MainActivity.java", """package com.situsnap.app;
import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.ContentValues;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.webkit.GeolocationPermissions;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

public class MainActivity extends Activity {
    private WebView webView;
    private ValueCallback<Uri[]> fileCallback;
    private Uri cameraOutputUri;
    private boolean cameraCapturePending = false;
    private static final int FILE_CHOOSER = 1001;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        requestPermissions(new String[]{
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
            Manifest.permission.CAMERA
        }, 1002);

        webView = new WebView(this);
        setContentView(webView);

        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setGeolocationEnabled(true);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("https://cryptod1.github.io/SituSnap/")
                    || url.contains("cloudinary.com")) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
                    return true;
                } catch (Exception e) {
                    return false;
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onGeolocationPermissionsShowPrompt(
                    String origin,
                    GeolocationPermissions.Callback callback) {
                callback.invoke(origin, true, false);
            }

            @Override
            public boolean onShowFileChooser(
                    WebView view,
                    ValueCallback<Uri[]> callback,
                    FileChooserParams params) {
                if (fileCallback != null) fileCallback.onReceiveValue(null);
                fileCallback = callback;
                cameraCapturePending = false;
                cameraOutputUri = null;

                try {
                    // HTML capture="environment" means TAKE PHOTO: open the native camera.
                    if (params.isCaptureEnabled()) {
                        ContentValues values = new ContentValues();
                        values.put(MediaStore.Images.Media.DISPLAY_NAME,
                                "SituSnap_" + System.currentTimeMillis() + ".jpg");
                        values.put(MediaStore.Images.Media.MIME_TYPE, "image/jpeg");
                        cameraOutputUri = getContentResolver().insert(
                                MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values);

                        if (cameraOutputUri != null) {
                            Intent camera = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                            camera.putExtra(MediaStore.EXTRA_OUTPUT, cameraOutputUri);
                            camera.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                                    | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                            if (camera.resolveActivity(getPackageManager()) != null) {
                                cameraCapturePending = true;
                                startActivityForResult(camera, FILE_CHOOSER);
                                return true;
                            }
                        }
                    }

                    // CHOOSE FILE remains the normal Android picker.
                    startActivityForResult(params.createIntent(), FILE_CHOOSER);
                    return true;
                } catch (Exception e) {
                    fileCallback = null;
                    cameraCapturePending = false;
                    cameraOutputUri = null;
                    return false;
                }
            }
        });

        webView.loadUrl("https://cryptod1.github.io/SituSnap/");
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER && fileCallback != null) {
            if (cameraCapturePending) {
                if (resultCode == RESULT_OK && cameraOutputUri != null) {
                    fileCallback.onReceiveValue(new Uri[]{cameraOutputUri});
                } else {
                    if (cameraOutputUri != null) {
                        try { getContentResolver().delete(cameraOutputUri, null, null); }
                        catch (Exception ignored) {}
                    }
                    fileCallback.onReceiveValue(null);
                }
            } else {
                fileCallback.onReceiveValue(
                    WebChromeClient.FileChooserParams.parseResult(resultCode, data)
                );
            }
            fileCallback = null;
            cameraCapturePending = false;
            cameraOutputUri = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
""")
