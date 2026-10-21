from pathlib import Path

path = Path("app/src/main/java/com/situsnap/app/MainActivity.java")
source = path.read_text(encoding="utf-8")

import_anchor = "import android.webkit.WebViewClient;\n"
if import_anchor not in source:
    raise SystemExit("FAIL: MainActivity WebViewClient import not found")
if "import android.webkit.JavascriptInterface;" not in source:
    source = source.replace(import_anchor, import_anchor + "import android.webkit.JavascriptInterface;\n", 1)

field_anchor = "    private static final int FILE_CHOOSER = 1001;\n"
bridge = """
    private final class SituSnapBridge {
        @JavascriptInterface
        public void exitApp() {
            runOnUiThread(() -> {
                if (webView != null) webView.loadUrl("about:blank");
                finish();
            });
        }
    }

"""
if "private final class SituSnapBridge" not in source:
    if field_anchor not in source:
        raise SystemExit("FAIL: MainActivity field anchor not found")
    source = source.replace(field_anchor, field_anchor + bridge, 1)

webview_anchor = "        webView = new WebView(this);\n"
bridge_attach = """        webView = new WebView(this);
        webView.addJavascriptInterface(new SituSnapBridge(), "SituSnapNative");
"""
if 'addJavascriptInterface(new SituSnapBridge(), "SituSnapNative")' not in source:
    if webview_anchor not in source:
        raise SystemExit("FAIL: WebView initialization anchor not found")
    source = source.replace(webview_anchor, bridge_attach, 1)

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
            "(function(){try{return !!(window.ssHandleNativeBack && window.ssHandleNativeBack());}catch(e){return false;}})()",
            handled -> {
                if ("true".equals(handled)) return;
                if (webView != null && webView.canGoBack()) webView.goBack();
                else finish();
            }
        );
    }"""
if new_back not in source:
    if old_back not in source:
        raise SystemExit("FAIL: expected original onBackPressed implementation not found")
    source = source.replace(old_back, new_back, 1)

if "window.ssHandleNativeBack" not in source or "SituSnapNative" not in source:
    raise SystemExit("FAIL: native Back warning bridge was not fully installed")

path.write_text(source, encoding="utf-8")
print("PASS: native Back handling now consults the in-house warning and exposes exit action")
