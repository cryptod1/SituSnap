from pathlib import Path

path = Path("app/src/main/java/com/situsnap/app/MainActivity.java")
if not path.is_file():
    raise SystemExit("FAIL: generated MainActivity.java not found")

source = path.read_text(encoding="utf-8")

def replace_once(old, new, label):
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"FAIL: expected exactly one {label}; found {count}")
    source = source.replace(old, new, 1)

if "import android.webkit.JavascriptInterface;" not in source:
    replace_once(
        "import android.webkit.ServiceWorkerController;",
        "import android.webkit.ServiceWorkerController;\n"
        "import android.webkit.JavascriptInterface;",
        "WebView JavaScript bridge import",
    )

if 'webView.addJavascriptInterface(new ExitBridge(), "SituSnapNative");' not in source:
    replace_once(
        "        setContentView(webView);",
        '        setContentView(webView);\n'
        '        webView.addJavascriptInterface(new ExitBridge(), "SituSnapNative");',
        "WebView exit bridge registration",
    )

old_back = """    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }"""
new_back = """    public class ExitBridge {
        @JavascriptInterface
        public void exitApp() {
            runOnUiThread(() -> finish());
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else if (webView != null) {
            webView.evaluateJavascript(
                "if (window.ssShowExitConfirm) { window.ssShowExitConfirm(); }",
                null
            );
        } else {
            super.onBackPressed();
        }
    }"""

if "public class ExitBridge" not in source:
    replace_once(old_back, new_back, "Android Back handler")

if not all(check in source for check in (
    "import android.webkit.JavascriptInterface;",
    'webView.addJavascriptInterface(new ExitBridge(), "SituSnapNative");',
    "public void exitApp()",
    "window.ssShowExitConfirm",
)):
    raise SystemExit("FAIL: Android Back confirmation patch validation failed")

path.write_text(source, encoding="utf-8")
print("PASS: Android Back button now opens the in-app exit confirmation")
