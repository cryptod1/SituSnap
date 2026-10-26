from pathlib import Path

main = Path("app/src/main/java/com/situsnap/app/MainActivity.java")
html = Path("index.html")
if not main.is_file() or not html.is_file():
    raise SystemExit("FAIL: generated Android project or index.html is missing")

source = main.read_text(encoding="utf-8")
if "import android.app.AlertDialog;" not in source:
    anchor = "package com.situsnap.app;\n"
    if anchor not in source:
        raise SystemExit("FAIL: expected Java package declaration not found")
    source = source.replace(anchor, anchor + "\nimport android.app.AlertDialog;\n", 1)

old = '''    @Override
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
    }'''
new = '''    @Override
    public void onBackPressed() {
        if (webView == null) {
            super.onBackPressed();
            return;
        }
        webView.evaluateJavascript(
            "(function(){try{return !!(window.ssIsReportOpen && window.ssIsReportOpen());}catch(e){return false;}})()",
            reportOpen -> {
                if ("true".equals(reportOpen)) {
                    runOnUiThread(() -> new AlertDialog.Builder(MainActivity.this)
                        .setTitle("Leave this report?")
                        .setMessage("Your report may contain unsaved details or photos. If you leave now, this work may be lost.")
                        .setNegativeButton("STAY ON REPORT", (dialog, which) -> dialog.dismiss())
                        .setPositiveButton("LEAVE REPORT", (dialog, which) -> finish())
                        .setCancelable(true)
                        .show());
                } else if (webView != null && webView.canGoBack()) {
                    webView.goBack();
                } else {
                    finish();
                }
            }
        );
    }'''
if old not in source:
    raise SystemExit("FAIL: expected current candidate Back handler not found; no Java source written")
source = source.replace(old, new, 1)
if "new AlertDialog.Builder(MainActivity.this)" not in source or "window.ssIsReportOpen" not in source:
    raise SystemExit("FAIL: native dialog verification failed")
main.write_text(source, encoding="utf-8")

page = html.read_text(encoding="utf-8")
needle = "  window.ssHandleNativeBack=function(){"
if needle not in page:
    raise SystemExit("FAIL: existing report-state helper not found")
if "window.ssIsReportOpen=hasUnfinishedReport;" not in page:
    page = page.replace(needle, "  window.ssIsReportOpen=hasUnfinishedReport;\n" + needle, 1)
html.write_text(page, encoding="utf-8")
print("PASS: Android Back uses a native AlertDialog and reads the active report state from the WebView")
