from pathlib import Path

path = Path("app/src/main/java/com/situsnap/app/MainActivity.java")
if not path.is_file():
    raise SystemExit("Generated MainActivity.java is missing")

source = path.read_text(encoding="utf-8")
if "window.ssHandleNativeBack" in source:
    raise SystemExit("Back-button warning patch appears to have already been applied")

import_anchor = "import android.webkit.WebViewClient;"
if import_anchor not in source:
    raise SystemExit("Could not find WebViewClient import")
source = source.replace(import_anchor, import_anchor + "\nimport android.webkit.JavascriptInterface;", 1)

setup_anchor = "        setContentView(webView);"
if setup_anchor not in source:
    raise SystemExit("Could not find WebView setup")
bridge = """        setContentView(webView);

        webView.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void exitApp() {
                runOnUiThread(() -> finish());
            }
        }, "SituSnapNative");"""
source = source.replace(setup_anchor, bridge, 1)

old_back = """    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }"""
new_back = """    @Override
    public void onBackPressed() {
        if (webView == null) {
            super.onBackPressed();
            return;
        }
        webView.evaluateJavascript(
            "(function(){return !!(window.ssHandleNativeBack && window.ssHandleNativeBack());})()",
            value -> {
                if ("true".equals(value)) return;
                if (webView != null && webView.canGoBack()) webView.goBack();
                else finish();
            }
        );
    }"""
if old_back not in source:
    raise SystemExit("Could not find expected native Back handler")
source = source.replace(old_back, new_back, 1)
path.write_text(source, encoding="utf-8")
print("Android Back-button warning bridge installed.")
