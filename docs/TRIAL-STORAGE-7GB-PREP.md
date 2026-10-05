# SituSnap trial storage — 7 GB hard cap

Preparation only. This must not replace or reconstruct the protected SituSnap FOUNDATION baseline (Build #229 / commit 56f5b93).

## Storage contract
- App talks only to the trial API/Worker; never expose bucket credentials or public bucket URLs to the client.
- Private object storage.
- Hard logical trial ceiling: 7,000,000,000 bytes (7 GB decimal). Reject a new upload before it would cross the ceiling.
- This leaves a 1,000,000,000-byte (1 GB) buffer below the earlier 8 GB ceiling.
- User message at capacity: "Trial photo storage is full."
- Maximum 2 photos per verified record, enforced server-side as well as in the UI.
- Validate accepted image MIME/type and byte size server-side.
- Store generated evidence/object IDs; do not trust client-supplied storage paths.
- Permanent delete must remove the stored object and its evidence/index record, not merely hide it from the UI.
- Trial admission/authorisation must be checked before accepting an upload.
- Retrieval should use the Worker/API (or short-lived signed access), never a permanently public object URL.

## Public website, app separation, and cutover
- Preserve the current APK and HTML as a frozen reference while building a replacement in a separate branch/project. Do not delete the existing files or alter the protected baseline during replacement work.
- The preferred end state is a public informational website with privacy/support pages and a prominent app download link; no photo upload, record access, or private evidence on the public website.
- Build and test the secure SituSnap app/APK path first. Move the app UI into a dedicated bundled app source (or a native UI) before converting the website's `index.html` into a brochure/download page.
- Current repository evidence: the APK workflow copies public `index.html` into the APK as `phoenix.html` and checks that both copies match. Therefore, do not replace or remove the public app page until the APK has its own independent app source and the replacement APK has passed field tests.
- The HTML bundled inside an APK remains inspectable and modifiable; the Worker must enforce the same authentication, upload, storage, and content rules for app requests.
- Remove the direct unsigned Cloudinary upload path before any production photos are handled; send app uploads only through the authenticated Worker.
- At cutover, remove the old APK download link and disable the old upload endpoint. Installed copies cannot be remotely erased, so the old API/backend must reject retired clients. Keep the old source and release archived for rollback/reference.
- If the current site stays publicly reachable during the build, its old upload route remains an exposure until disabled; a frozen copy should not accept genuine uploads.
- Keep the app useful and stable for Play review. As of 31 August 2026, new Google Play apps and updates must target Android 16 (API 36) or higher. New Play submissions use an Android App Bundle (AAB).
- If the Play Store version should update existing installs, verify the package name and signing-certificate path before release; Google requires the package name and signing continuity for app updates.

## Client, identity, and bot controls
- Treat HTML and APK code as public/untrusted. Do not put secrets or security decisions only in either client.
- Protect every upload, retrieve, list, and delete API route on the Worker. CORS, a hidden button, or a check in HTML does not authenticate a caller.
- Keep R2 private and accessible only through the Worker binding. Do not allow direct client writes.
- Restrict enrolment to the manager's approved tester list. A UK mobile-number format check can reject non-UK numbers, but does not prove the caller owns an approved number or is human.
- Verify possession during enrolment (for example, one-time pairing/verification), then issue a random, revocable device credential. Rate-limit enrolment and verification attempts. Treat the phone number as an enrolment identifier, not a password.
- For browser-based HTML uploads, consider Turnstile and validate every token server-side in the Worker. A client-side widget alone is bypassable. Test the challenge in SituSnap's Android WebView and on weak/offline connections before relying on it.
- For Play Store Android builds, consider Play Integrity verification at the Worker after the app is distributed through Google Play. It can provide app/device integrity signals; it does not prove GPS location.
- Rate-limit by authenticated device for upload actions and use a separate limit for enrolment attempts. IP limits can be an additional layer, but mobile networks may put many colleagues behind a shared IP.
- The server-side 7 GB byte ledger and per-record photo limit remain mandatory; rate limiting is an abuse throttle, not storage accounting.

## Geolocation limits
- Treat GPS coordinates, geofence results, timestamps, and photo EXIF received from a client as evidence signals, not proof: a modified client or spoofed device can falsify them.
- The native Android app can reject locations marked as mock and can check accuracy/time, but this raises the effort required to spoof; it does not guarantee genuine physical presence.
- Enforce the trial geofence on the Worker using the submitted coordinates and record the decision for audit. Combine with approved-device authentication and server-side image checks; do not use geolocation as the upload authorisation control.

## Upload-abuse and explicit-content controls
- Before an image is committed to retained storage, run a server-side check for explicit sexual content. Reject images classified as explicit; if the scanner is unavailable or cannot make a safe decision, fail closed and do not retain the image.
- Check the moderation service's pricing/free allowance and test it on representative legitimate field photos before enabling it. Automated classification reduces risk but cannot guarantee perfect decisions; rejected legitimate photos need a clear contact-admin route.
- Monitor repeated failed authentication, bot challenges, content-screening rejections, and unusual upload patterns. Provide a way to revoke a device credential quickly.

## Evidence metadata
Minimum useful metadata:
- evidence_id
- verified_record_id
- photo_slot (1 or 2)
- captured_at / received_at
- object_key
- content_type
- byte_size
- deletion status/time
- location-verification result where applicable
- authenticated device identifier (pseudonymous; do not store the raw credential)

Do not put unnecessary personal data into object names.

## Capacity/accounting
Maintain authoritative server-side counters for bytes stored and object count. Upload flow:
1. authenticate/authorise;
2. validate record/photo slot and geolocation rule;
3. validate image;
4. atomically reserve/check current bytes + incoming bytes <= 7,000,000,000 bytes;
5. run explicit-content screening before retained storage;
6. store the approved object;
7. persist evidence metadata/accounting;
8. return success.

Deletion must decrement accounting only after confirmed object deletion. Concurrent uploads must not overshoot the cap; reservations must be released if screening or upload fails.

## Image preparation
Client-side compression can reduce cost/traffic, but server limits remain authoritative. Strip unnecessary metadata where practical. Do not invent unreadable evidence or silently accept corrupt images.

## 04:00 cleanup
Treat temporary/offline/transient upload material separately from submitted evidence. The cleanup job must never delete retained submitted evidence unless the retention rule explicitly requires it.

## Monitoring
Expose/record at minimum:
- bytes used / bytes remaining
- object/photo count
- rejected uploads by reason, including authorisation and content screening
- failed uploads
- failed deletions
- moderation service errors and cost/usage
- rate-limit and bot-challenge events

## Provider setup checklist
When storage is provisioned:
1. create a private bucket/container;
2. configure the Worker-only storage binding;
3. configure any moderation binding/secret only after checking cost and testing;
4. test approved-device enrolment and credential revocation;
5. test unauthorised upload/retrieve/delete and direct bucket access rejection;
6. test browser Turnstile validation and Android WebView behavior if enabled;
7. test geofence rejection and mock-location handling without treating either as identity proof;
8. test third-photo rejection;
9. test explicit-content rejection and legitimate field-photo acceptance;
10. test fail-closed behaviour when screening is unavailable;
11. test capacity rejection without partial object;
12. test retrieve;
13. test permanent delete and verify object is actually gone;
14. verify storage accounting, including concurrent uploads and failed-upload reservation release;
15. only then connect the protected SituSnap client.

## FOUNDATION guardrail
No application UI/build changes are authorised by this preparation document. Future integration must build forward from Build #229 / commit 56f5b93 and keep HTML/APK/app behaviour aligned.
