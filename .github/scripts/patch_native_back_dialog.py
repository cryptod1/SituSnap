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

# Do not depend on an asynchronous WebView/JavaScript callback to decide
# whether to warn: Android Back can otherwise finish the Activity first.
start = source.find("    @Override\n    public void onBackPressed() {")
if start < 0:
    raise SystemExit("FAIL: Android Back handler not found; no Java source written")
# Locate the matching method end using the known final class layout.
end_marker = "\n    }"
end = source.find(end_marker, start)
# The first closing pattern can be an inner block; use the known next method/class
# structure by replacing the complete previously generated handler variants.
old_variants = [
'''    @Override
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
    }''',
'''    @Override
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
    }''',
'''    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }'''
]
new_handler = '''    @Override
    public void onBackPressed() {
        if (webView == null) {
            super.onBackPressed();
            return;
        }
        // Ask the page whether a report is unfinished. Keep normal Back behaviour
        // when no report is open; warn before discarding an unfinished report.
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
matched = [v for v in old_variants if v in source]
if len(matched) != 1:
    raise SystemExit(f"FAIL: expected exactly one known Back handler; found {len(matched)}. No Java source written.")
source = source.replace(matched[0], new_handler, 1)
if "new AlertDialog.Builder(MainActivity.this)" not in source or "STAY ON REPORT" not in source or "LEAVE REPORT" not in source:
    raise SystemExit("FAIL: native Back dialog verification failed")
main.write_text(source, encoding="utf-8")

# Keep the helper available for any UI-specific Back handling, but do not let it
# decide whether the native warning appears.
page = html.read_text(encoding="utf-8")
needle = "  window.ssHandleNativeBack=function(){"
if needle not in page:
    raise SystemExit("FAIL: existing report-state helper not found")
if "window.ssIsReportOpen=hasUnfinishedReport;" not in page:
    page = page.replace(needle, "  window.ssIsReportOpen=hasUnfinishedReport;\n" + needle, 1)
html.write_text(page, encoding="utf-8")

# Android 13+ predictive-back can bypass the legacy Activity callback.
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

print("PASS: Android Back always shows a native confirmation; no asynchronous WebView check can bypass it")
