# SituSnap trial storage — 8 GB preparation

Preparation only. This must not replace or reconstruct the protected SituSnap FOUNDATION baseline (Build #229 / commit 56f5b93).

## Storage contract
- App talks only to the trial API/Worker; never expose bucket credentials or public bucket URLs to the client.
- Private object storage.
- Hard logical trial ceiling: 8 GB. Reject a new upload before it would cross the ceiling.
- User message at capacity: "Trial photo storage is full."
- Maximum 2 photos per verified record, enforced server-side as well as in the UI.
- Validate accepted image MIME/type and byte size server-side.
- Store generated evidence/object IDs; do not trust client-supplied storage paths.
- Permanent delete must remove the stored object and its evidence/index record, not merely hide it from the UI.
- Trial admission/authorisation must be checked before accepting an upload.
- Retrieval should use the Worker/API (or short-lived signed access), never a permanently public object URL.

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
4. check current bytes + incoming bytes <= 8 GB logical cap;
5. store object;
6. persist evidence metadata/accounting;
7. return success.

Deletion must decrement accounting only after confirmed object deletion.

## Image preparation
Client-side compression can reduce cost/traffic, but server limits remain authoritative. Strip unnecessary metadata where practical. Do not invent unreadable evidence or silently accept corrupt images.

## 04:00 cleanup
Treat temporary/offline/transient upload material separately from submitted evidence. The cleanup job must never delete retained submitted evidence unless the retention rule explicitly requires it.

## Monitoring
Expose/record at minimum:
- bytes used / bytes remaining
- object/photo count
- rejected uploads by reason
- failed uploads
- failed deletions

## Provider setup checklist
When the 8 GB storage is provisioned:
1. create a private bucket/container;
2. create least-privilege Worker credentials;
3. add credentials as Worker secrets, never source code;
4. configure the bucket binding/API endpoint;
5. test authorised upload;
6. test unauthorised rejection;
7. test 3rd-photo rejection;
8. test capacity rejection without partial object;
9. test retrieve;
10. test permanent delete and verify object is actually gone;
11. verify storage accounting;
12. only then connect the protected SituSnap client.

## FOUNDATION guardrail
No application UI/build changes are authorised by this preparation document. Future integration must build forward from Build #229 / commit 56f5b93 and keep HTML/APK/app behaviour aligned.
