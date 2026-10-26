from pathlib import Path

main = Path("app/src/main/java/com/situsnap/app/MainActivity.java")
html = Path("index.html")
if not main.is_file() or not html.is_file():
    raise SystemExit("FAIL: generated Android project or index.html is missing")

source = main.read_text(encoding="utf-8")

def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"FAIL: expected exactly one {label}; found {count}")
    return text.replace(old, new, 1)

if "import android.webkit.JavascriptInterface;" not in source:
    source = replace_once(
        source,
        "import android.webkit.ServiceWorkerController;",
        "import android.webkit.ServiceWorkerController;\nimport android.webkit.JavascriptInterface;",
        "JavaScript bridge import",
    )

if 'webView.addJavascriptInterface(new ExitBridge(), "SituSnapNative");' not in source:
    source = replace_once(
        source,
        "        setContentView(webView);",
        '        setContentView(webView);\n        webView.addJavascriptInterface(new ExitBridge(), "SituSnapNative");',
        "native exit bridge registration",
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
if "public class ExitBridge" not in source:
    source = replace_once(source, old_back, new_back, "Android Back handler")

if not all(check in source for check in (
    "import android.webkit.JavascriptInterface;",
    'webView.addJavascriptInterface(new ExitBridge(), "SituSnapNative");',
    "public void exitApp()",
    "window.ssHandleNativeBack",
)):
    raise SystemExit("FAIL: native Back confirmation bridge validation failed")

page = html.read_text(encoding="utf-8")
page = replace_once(page, "Leave SituSnap?", "Leave this report?", "dialog heading")
page = replace_once(
    page,
    "Leaving SituSnap now may result in the loss of your unfinished work. Do you want to exit?",
    "Your report may contain unsaved details or photos. If you leave now, this work may be lost.",
    "dialog warning",
)
page = replace_once(page, "Continue Working", "STAY ON REPORT", "stay button label")
page = replace_once(page, "Exit SituSnap", "LEAVE REPORT", "leave button label")

old_show = """  window.ssShowExitConfirm=function(){
    overlay.setAttribute('aria-hidden','false');
    if(continueButton)continueButton.focus();
  };"""
new_show = """  function hasUnfinishedReport(){
    var details=document.getElementById('recordDetails');
    if(!details||!details.open)return false;
    var fields=['postcode','address','notes','accessDirections'];
    if(fields.some(function(id){
      var field=document.getElementById(id);
      return !!(field&&String(field.value||'').trim());
    }))return true;
    var photos=['photoCamera','photo1','photo2Camera','photo2'];
    return photos.some(function(id){
      var field=document.getElementById(id);
      return !!(field&&field.files&&field.files.length>0);
    });
  }
  window.ssHandleNativeBack=function(){
    if(overlay.getAttribute('aria-hidden')==='false')return true;
    if(!hasUnfinishedReport())return false;
    overlay.setAttribute('aria-hidden','false');
    if(continueButton)continueButton.focus();
    return true;
  };"""
page = replace_once(page, old_show, new_show, "exit-confirmation JavaScript handler")
page = replace_once(page, "if(window.ssShowExitConfirm) { window.ssShowExitConfirm(); }", "if(window.ssHandleNativeBack) { window.ssHandleNativeBack(); }", "legacy JavaScript callback")

# The candidate version is deliberately distinct from the previous test APK.
for old, new in (("1.3.4", "1.3.5"), ("SituSnap-1.3.4", "SituSnap-1.3.5")):
    page = page.replace(old, new)

main.write_text(source, encoding="utf-8")
html.write_text(page, encoding="utf-8")
print("PASS: Back checks unfinished report before WebView navigation; dialog uses agreed wording; candidate version is 1.3.5")
