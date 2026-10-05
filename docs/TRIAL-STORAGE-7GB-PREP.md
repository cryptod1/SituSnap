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

## Upload-abuse and explicit-content controls
- Keep the R2 bucket private. The app must not receive R2 credentials or direct write access.
- Require a valid, revocable device credential tied to manager-approved trial access before an upload. A phone number by itself is an enrolment identifier, not a secret.
- Apply request limits to each authenticated device and to unauthenticated enrolment attempts. Rate limits slow abuse; the separate 7 GB accounting gate remains the storage brake.
- Before an image is committed to retained storage, run a server-side check for explicit sexual content. Reject images classified as explicit; if the scanner is unavailable or cannot make a safe decision, fail closed and do not retain the image.
- Check the moderation service's pricing/free allowance and test it on representative legitimate field photos before enabling it. Automated classification reduces risk but cannot guarantee perfect decisions; rejected legitimate photos need a clear contact-admin route.

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

## Provider setup checklist
When storage is provisioned:
1. create a private bucket/container;
2. configure the Worker-only storage binding;
3. configure any moderation binding/secret only after checking cost and testing;
4. test authorised upload;
5. test unauthorised upload and direct bucket access rejection;
6. test third-photo rejection;
7. test explicit-content rejection and legitimate field-photo acceptance;
8. test fail-closed behaviour when screening is unavailable;
9. test capacity rejection without partial object;
10. test retrieve;
11. test permanent delete and verify object is actually gone;
12. verify storage accounting, including concurrent uploads and failed-upload reservation release;
13. only then connect the protected SituSnap client.

## FOUNDATION guardrail
No application UI/build changes are authorised by this preparation document. Future integration must build forward from Build #229 / commit 56f5b93 and keep HTML/APK/app behaviour aligned.
