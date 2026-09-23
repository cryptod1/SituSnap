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
        versionCode 3
        versionName '1.0'
    }
}
""")

put("app/src/main/res/values/styles.xml", """<resources>
<style name="AppTheme" parent="android:style/Theme.Material.Light.NoActionBar">
<item name="android:statusBarColor">#07192b</item>
<item name="android:navigationBarColor">#07192b</item>
<item name="android:windowLightStatusBar">false</item>
<item name="android:windowLightNavigationBar">false</item>
<item name="android:windowOptOutEdgeToEdgeEnforcement">true</item>
</style>
</resources>
""")

put("app/src/main/res/drawable/situsnap_icon.xml", """<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#07192B" android:pathData="M0,0h108v108h-108z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M20,16h22v6h-16v16h-6zM66,16h22v22h-6v-16h-16zM20,70h6v16h16v6h-22zM82,70h6v22h-22v-6h16z"/>
    <path android:fillColor="#2FA866" android:pathData="M54,25c-13,0 -23,10 -23,23c0,18 23,38 23,38s23,-20 23,-38c0,-13 -10,-23 -23,-23z"/>
    <path android:fillColor="#FFFFFF" android:pathData="M54,34a14,14 0,1 0,0 28a14,14 0,1 0,0 -28z"/>
    <path android:fillColor="#2FA866" android:pathData="M41,55l8,-9l6,6l5,-5l8,8v4h-27z"/>
    <path android:strokeColor="#FFFFFF" android:strokeWidth="3" android:strokeLineCap="round"
        android:fillColor="@android:color/transparent" android:pathData="M53,60c-3,5 -5,9 -4,15c1,5 5,8 7,11"/>
</vector>
""")

put("app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml", """<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/icon_background"/>
    <foreground android:drawable="@drawable/situsnap_icon"/>
</adaptive-icon>
""")

put("app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml", """<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/icon_background"/>
    <foreground android:drawable="@drawable/situsnap_icon"/>
</adaptive-icon>
""")

put("app/src/main/res/values/colors.xml", """<resources>
    <color name="icon_background">#07192B</color>
</resources>
""")

put("app/src/main/AndroidManifest.xml", """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
<uses-permission android:name="android.permission.CAMERA"/>
<application android:theme="@style/AppTheme" android:label="SituSnap" android:icon="@mipmap/ic_launcher" android:roundIcon="@mipmap/ic_launcher_round" android:usesCleartextTraffic="false">
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
import android.net.Uri;
import android.os.Bundle;
import android.webkit.GeolocationPermissions;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import java.util.HashMap;
import java.util.Map;

public class MainActivity extends Activity {
    private WebView webView;
    private ValueCallback<Uri[]> fileCallback;
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
        s.setTextZoom(100);
        s.setUseWideViewPort(true);
        s.setLoadWithOverviewMode(false);
        // Prefer the network when online, but retain WebView's cache for dead-zone/offline use.
        s.setCacheMode(WebSettings.LOAD_DEFAULT);

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
                try {
                    startActivityForResult(params.createIntent(), FILE_CHOOSER);
                    return true;
                } catch (Exception e) {
                    fileCallback = null;
                    return false;
                }
            }
        });

        // Cache-bust the HTML shell on each online launch so a newly deployed SituSnap
        // version is picked up immediately. If offline, fall back to the cached page.
        if (isOnline()) {
            webView.loadUrl("https://cryptod1.github.io/SituSnap/?app_launch=" + System.currentTimeMillis());
        } else {
            s.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);
            webView.loadUrl("https://cryptod1.github.io/SituSnap/");
        }
    }

    private boolean isOnline() {
        try {
            android.net.ConnectivityManager cm =
                (android.net.ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            android.net.Network n = cm.getActiveNetwork();
            if (n == null) return false;
            android.net.NetworkCapabilities c = cm.getNetworkCapabilities(n);
            return c != null && c.hasCapability(android.net.NetworkCapabilities.NET_CAPABILITY_INTERNET);
        } catch (Exception e) {
            return true;
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER && fileCallback != null) {
            fileCallback.onReceiveValue(
                WebChromeClient.FileChooserParams.parseResult(resultCode, data)
            );
            fileCallback = null;
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }
}
""")
