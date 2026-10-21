from pathlib import Path
import re

path = Path("app/src/main/java/com/situsnap/app/MainActivity.java")
if not path.is_file():
    raise SystemExit("FAIL: generated MainActivity.java was not found")

source = path.read_text(encoding="utf-8")
pattern = re.compile(
    r'    @Override\n'
    r'    public void onBackPressed\(\) \{\n'
    r'        if \(webView != null && webView\.canGoBack\(\)\) webView\.goBack\(\);\n'
    r'        else super\.onBackPressed\(\);\n'
    r'    \}',
)
replacement = '''    @Override
    public void onBackPressed() {
        if (webView == null) {
            finish();
            return;
        }

        if (webView.canGoBack()) {
            webView.goBack();
            return;
        }

        // No dialog: while an unfinished submission contains user input or photos,
        // keep the app open so Android Back cannot silently discard that work.
        // Exit only when the page explicitly reports no unfinished submission.
        String unfinishedWorkCheck =
                "(() => {"
                + "const d=document.getElementById('recordDetails');"
                + "if(!d || !d.open) return false;"
                + "const ids=['postcode','address','notes','accessDirections'];"
                + "if(ids.some(id=>{const e=document.getElementById(id);"
                + "return e && String(e.value||'').trim().length>0;})) return true;"
                + "return ['photoCamera','photo1','photo2'].some(id=>{"
                + "const e=document.getElementById(id);"
                + "return e && e.files && e.files.length>0;});"
                + "})()";

        webView.evaluateJavascript(unfinishedWorkCheck, value -> {
            // Fail safe: only finish when JavaScript positively reports false.
            // true, null, or an unexpected result leaves the app open.
            if ("false".equals(value)) {
                finish();
            }
        });
    }'''
updated, count = pattern.subn(replacement, source, count=1)
if count != 1:
    raise SystemExit("FAIL: expected Android Back handler was not found exactly once")
path.write_text(updated, encoding="utf-8")
check = path.read_text(encoding="utf-8")
if "unfinishedWorkCheck" not in check or 'if ("false".equals(value))' not in check:
    raise SystemExit("FAIL: Android Back handler patch verification failed")
print("PASS: Android Back is popup-free and fails safe when unfinished work is detected")
