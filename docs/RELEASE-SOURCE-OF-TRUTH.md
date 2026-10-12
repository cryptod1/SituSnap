# SituSnap release source of truth

## Canonical runtime source

- The canonical web app is the repository-root `index.html` on `main`.
- GitHub Pages serves that file as the SituSnap website.
- The Android release workflow copies those exact bytes into `assets/phoenix.html` in the APK and `base/assets/phoenix.html` in the AAB.
- The workflow fails if either packaged copy differs from the source. Its job summary records the source commit and SHA-256.
- Signed Play release builds run from `main` only. Branch builds are prototypes and are not release artefacts.

Do not package `app-source/situsnap-app.html`, a branch copy, or a separately edited HTML file for a Play release. Prototype work must be reconciled into root `index.html` before release.

## Current alignment change

This branch promotes the exact root HTML used by the successful SituSnap 1.3.1 / version-code 29 local-only candidate (source branch commit `1588d7177a5e4410962918737201dd5d985eb3b9`) to the canonical root path. The approved page layout is preserved; the source change adds the local-only network guard and updates its displayed/build version markers.

The website will use that same file after this branch is merged to `main`. The Android workflow remains byte-for-byte gated against it. No APK/AAB is uploaded to Google Play by this change.

## Version-code rule

Version name and code are currently set in `.github/workflows/situsnap-android.yml`. Version code 29 is already assigned to the closed-testing candidate; do not upload a second bundle with code 29. Before the next Play submission, raise the workflow to an unused code (at least 30), update the HTML version markers to the same name, then build and verify from `main`.

## Release evidence still required

The HTML hash check proves website/APK/AAB source parity; it does not by itself prove privacy or field behaviour. Before professional handover, verify on the exact release APK that photo capture, two-photo blocking, the 8 GB hard stop, geofence rules, offline behaviour, and removal behave as promised. Confirm whether any network requests occur during capture, save, sync, or deletion.
