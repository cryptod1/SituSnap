from pathlib import Path
import shutil

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
        versionCode 11
        versionName '1.0.11'
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
<style name="SplashTheme" parent="android:style/Theme.Material.Light.NoActionBar">
<item name="android:windowLightStatusBar">false</item>
<item name="android:statusBarColor">#07192b</item>
<item name="android:navigationBarColor">#07192b</item>
<item name="android:windowBackground">#07192b</item>
</style>
</resources>
""")
put("app/src/main/AndroidManifest.xml", """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.CAMERA"/>
<application android:theme="@style/AppTheme" android:label="SituSnap" android:icon="@drawable/ic_situsnap" android:roundIcon="@drawable/ic_situsnap" android:usesCleartextTraffic="false">
<activity android:name=".SplashActivity" android:theme="@style/SplashTheme" android:exported="true">
<intent-filter>
<action android:name="android.intent.action.MAIN"/>
<category android:name="android.intent.category.LAUNCHER"/>
</intent-filter>
</activity>
<activity android:name=".MainActivity" android:exported="false"/>
</application>
</manifest>
""")
put("app/src/main/res/drawable/ic_situsnap.xml", """<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="108dp" android:height="108dp" android:viewportWidth="100" android:viewportHeight="100">
<path android:fillColor="#07192B" android:pathData="M0,0h100v100h-100z"/>
<path android:fillColor="#69DF83" android:pathData="M50,91C44,80 22,66 22,43a28,28 0,1 1,56 0c0,23 -22,37 -28,48z"/>
<path android:fillColor="#F8FBFF" android:pathData="M50,23.5a19.5,19.5 0,1 0,0 39a19.5,19.5 0,1 0,0 -39"/>
<path android:fillColor="#176D52" android:pathData="M31,47 L40,39 L49,45 L58,36 L69,48 L69,58 L31,58z"/>
<path android:fillColor="#5FD36D" android:pathData="M31,50 C38,46 43,47 49,51 C54,54 58,56 63,52 C67,49 70,49 72,50 L72,60 L31,60z"/>
<path android:fillColor="@android:color/transparent" android:strokeColor="#FFFFFF" android:strokeWidth="4.2" android:strokeLineCap="round" android:pathData="M48,44 C53,46 57,48 58,51 C59,55 53,56 51,59 C49,62 53,65 58,67"/>
<path android:fillColor="@android:color/transparent" android:strokeColor="#FFFFFF" android:strokeWidth="6" android:strokeLineCap="round" android:pathData="M9,30 L9,16 C9,12 12,9 16,9 L30,9 M91,30 L91,16 C91,12 88,9 84,9 L70,9 M9,70 L9,84 C9,88 12,91 16,91 L30,91 M91,70 L91,84 C91,88 88,91 84,91 L70,91"/>
</vector>
""")

put("app/src/main/java/com/situsnap/app/SplashActivity.java", """package com.situsnap.app;
import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.graphics.Color;
import android.view.Gravity;
import android.widget.FrameLayout;
import android.widget.ImageView;

public class SplashActivity extends Activity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(7, 25, 43));

        // Use the same approved SituSnap mark as the launcher.
        // CENTER_INSIDE is intentional: never crop the outer logo/artwork.
        int splashId = R.drawable.ic_situsnap;
        if (splashId != 0) {
            ImageView image = new ImageView(this);
            image.setImageResource(splashId);
            image.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
            image.setAdjustViewBounds(true);
            int pad = (int) (24 * getResources().getDisplayMetrics().density);
            image.setPadding(pad, pad, pad, pad);
            root.addView(image, new FrameLayout.LayoutParams(
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    FrameLayout.LayoutParams.MATCH_PARENT,
                    Gravity.CENTER));
        }

        setContentView(root);

        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            startActivity(new Intent(this, MainActivity.class));
            finish();
        }, 2000);
    }
}
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
import android.webkit.ServiceWorkerController;

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
        s.setCacheMode(WebSettings.LOAD_NO_CACHE);
        webView.clearCache(true);

        // Phoenix must never be hijacked by the old production service worker.
        if (android.os.Build.VERSION.SDK_INT >= 24) {
            ServiceWorkerController.getInstance().setServiceWorkerClient(
                new android.webkit.ServiceWorkerClient() {
                    @Override
                    public android.webkit.WebResourceResponse shouldInterceptRequest(
                            android.webkit.WebResourceRequest request) {
                        return null;
                    }
                });
        }

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

        try {
            java.io.InputStream in = getAssets().open("phoenix.html");
            java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) != -1) out.write(buf, 0, n);
            in.close();
            String phoenix = out.toString("UTF-8");
            // Bundle the exact audited Phoenix in the APK, but retain the HTTPS
            // base origin so Breadcrumbs CORS and secure browser APIs behave normally.
            webView.loadDataWithBaseURL(
                "https://cryptod1.github.io/SituSnap/",
                phoenix, "text/html", "UTF-8", null);
        } catch (Exception e) {
            webView.loadUrl("https://cryptod1.github.io/SituSnap/phoenix.html?native=111&cb=phoenix-clean-2");
        }
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

# Freeze the exact audited Phoenix into this APK build.
phoenix = Path("phoenix.html")
if not phoenix.is_file():
    raise SystemExit("phoenix.html missing from repository root")
html = phoenix.read_text(encoding="utf-8")
asset = Path("app/src/main/assets/phoenix.html")
asset.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(phoenix, asset)
print("🔥 PHOENIX-CLEAN-2 bundled into APK")
