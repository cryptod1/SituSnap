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
if 'id="ssBackExitOverlay"' not in page:
    page += r"""
<style id="ss-back-exit-confirmation-style">
#ssBackExitOverlay{position:fixed;inset:0;z-index:2147483000;display:none;align-items:center;justify-content:center;padding:22px;background:rgba(0,8,17,.82);backdrop-filter:blur(5px);-webkit-backdrop-filter:blur(5px)}
#ssBackExitOverlay[aria-hidden="false"]{display:flex}
#ssBackExitCard{width:min(100%,390px);box-sizing:border-box;padding:23px;border:1px solid rgba(49,223,104,.48);border-radius:20px;background:#07192b;color:#f4fbff;box-shadow:0 22px 70px rgba(0,0,0,.5);font-family:inherit}
#ssBackExitCard h2{margin:0 0 12px;font-size:20px;line-height:1.25;font-weight:850;color:#fff}
#ssBackExitCard p{margin:0 0 22px;font-size:15px;line-height:1.55;color:#d6e4ec}
#ssBackExitActions{display:grid;grid-template-columns:1fr;gap:10px}
#ssBackExitActions button{width:100%;min-height:48px;padding:12px 16px;border-radius:12px;font:800 14px/1.2 inherit;letter-spacing:.02em;cursor:pointer}
#ssBackExitContinue{border:1px solid #31df68;background:#31df68;color:#07192b}
#ssBackExitExit{border:1px solid #6b8291;background:#102b40;color:#f4fbff}
</style>
<div id="ssBackExitOverlay" aria-hidden="true">
  <section id="ssBackExitCard" role="dialog" aria-modal="true" aria-labelledby="ssBackExitTitle" aria-describedby="ssBackExitMessage">
    <h2 id="ssBackExitTitle">Leave this report?</h2>
    <p id="ssBackExitMessage">Your report may contain unsaved details or photos. If you leave now, this work may be lost.</p>
    <div id="ssBackExitActions">
      <button id="ssBackExitContinue" type="button">STAY ON REPORT</button>
      <button id="ssBackExitExit" type="button">LEAVE REPORT</button>
    </div>
  </section>
</div>
<script id="ss-back-exit-confirmation">
(function(){
  var overlay=document.getElementById('ssBackExitOverlay');
  if(!overlay)return;
  var stay=document.getElementById('ssBackExitContinue');
  var leave=document.getElementById('ssBackExitExit');
  function close(){overlay.setAttribute('aria-hidden','true');if(stay)stay.focus()}
  function hasUnfinishedReport(){
    var details=document.getElementById('recordDetails');
    if(details&&details.open)return true;
    // Also protect unsaved work when the report details section is collapsed.
    var fields=['postcode','address','notes','street'];
    if(fields.some(function(id){var el=document.getElementById(id);return !!(el&&String(el.value||'').trim())}))return true;
    return ['photoCamera','photo1','photo2Camera','photo2'].some(function(id){var el=document.getElementById(id);return !!(el&&el.files&&el.files.length>0)});
  }
  window.ssHandleNativeBack=function(){
    if(overlay.getAttribute('aria-hidden')==='false')return true;
    if(!hasUnfinishedReport())return false;
    overlay.setAttribute('aria-hidden','false');
    if(stay)stay.focus();
    return true;
  };
  if(stay)stay.addEventListener('click',close);
  if(leave)leave.addEventListener('click',function(){
    if(window.SituSnapNative&&typeof window.SituSnapNative.exitApp==='function')window.SituSnapNative.exitApp();
    else close();
  });
  overlay.addEventListener('click',function(event){if(event.target===overlay)close()});
  document.addEventListener('keydown',function(event){if(event.key==='Escape'&&overlay.getAttribute('aria-hidden')==='false'){event.preventDefault();close()}});
})();
</script>
"""
# Keep this test build distinct from the previous candidate.
page = page.replace("1.3.3", "1.3.6").replace("1.3.4", "1.3.6")


# Give the test candidate its own Android package so it installs alongside
# the Play-signed production app and cannot overwrite or remove production data.
# Candidate package identity is applied once by the candidate workflow before this patch.
# Keep applicationId mutation out of this script to avoid conflicting patches.

strings_file = Path("app/src/main/res/values/strings.xml")
if strings_file.is_file():
    strings_source = strings_file.read_text(encoding="utf-8")
    strings_source, label_count = re.subn(
        r'(<string\b[^>]*\bname=["\']app_name["\'][^>]*>).*?(</string>)',
        r"\1SituSnap Test\2",
        strings_source,
        count=1,
    )
    if label_count == 1:
        strings_file.write_text(strings_source, encoding="utf-8")


# Android 13+ predictive-back can bypass the legacy WebView Activity callback.
# Route Back through onBackPressed() so the report-warning bridge is invoked.
manifest = Path("app/src/main/AndroidManifest.xml")
if not manifest.is_file():
    raise SystemExit("FAIL: Android manifest is missing")
manifest_source = manifest.read_text(encoding="utf-8")
if 'android:enableOnBackInvokedCallback="false"' not in manifest_source:
    marker = "<application"
    if marker not in manifest_source:
        raise SystemExit("FAIL: Android application element not found in manifest")
    manifest_source = manifest_source.replace(
        marker,
        '<application android:enableOnBackInvokedCallback="false"',
        1,
    )
    manifest.write_text(manifest_source, encoding="utf-8")

main.write_text(source, encoding="utf-8")
html.write_text(page, encoding="utf-8")
print("PASS: Android Back routed through report warning; open report always prompts; isolated test candidate version is 1.3.6")
