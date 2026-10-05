# SituSnap trial API (staging only)

This is a separate, not-yet-deployed Worker for the replacement Play Store app. It does not modify the live Worker, the current APK/HTML, or `main`.

## Security contract

- Cloudflare Access JWT verification and an enrolled colleague email allowlist guard every `/v1/*` route. CORS is only a browser boundary; it is not identity verification.
- Verified records must already exist in D1 under the trial company. This API has no route to create or verify records.
- R2 is reachable only through the Worker binding. The bucket must remain private, with no `r2.dev` URL or public custom domain.
- D1 triggers reserve each incoming byte before moderation and reject any reservation that would put used + reserved bytes above **7,000,000,000**. This is the hard logical photo cap, with 1 GB headroom below 8 GB.
- Each verified record has two unique photo slots; uploads are JPEG, PNG, or WebP, up to 12 MiB each. The Worker checks the file signature as well as `Content-Type` and `Content-Length`.
- Images are screened before R2 retention. The Worker accepts only the screening service's explicit `{"verdict":"allow","model":"..."}` response. Rejection, timeout, malformed response, or missing service fails closed.
- Authenticated limits are enforced in D1 (6 upload attempts and 6 deletes per minute; 60 reads per minute) and the Cloudflare rate-limit binding adds a per-colleague burst layer. Cloudflare's binding is approximate; the D1 byte ledger, not rate limiting, enforces storage capacity.
- Photo reads go through an authenticated Worker route and are `private, no-store`. Permanent delete removes the R2 object before deleting metadata; D1 only releases used bytes after confirmed R2 deletion. Failed metadata cleanup safely leaves quota charged so deletion can be retried.
- An hourly reservation cleanup removes abandoned pending uploads. It deletes any corresponding R2 object before releasing the D1 reservation.
- Worker logs record screening rejections, screening outages, and throttling with a pseudonymous actor hash; they do not contain the image, raw email, or record identifier.

## Routes

| Method and route | Behavior |
| --- | --- |
| `GET /health` | Non-sensitive liveness response |
| `POST /v1/records/{recordId}/photos?slot=1\|2` | Authenticated upload, screening, quota reservation, then private R2 write |
| `GET /v1/records/{recordId}/photos` | List metadata for stored photos on an enrolled company's verified record |
| `GET /v1/photos/{photoId}` | Stream the private image through the Worker |
| `DELETE /v1/photos/{photoId}` | Uploader or configured trial manager deletes image and metadata |
| `GET /v1/admin/usage` | Trial manager only: used, reserved, remaining bytes, and stored photo count |

Photo upload body is the raw image bytes, not JSON or base64. No credentials, image bytes, access tokens, or photo paths are logged.

## Local checks

From this folder:

```sh
npm test
```

The tests cover fail-closed Access and moderation behavior, image-signature checks, origin checks, orphan cleanup order, D1 quota boundaries, atomic reservation/release, the two-slot constraint, and legal state transitions.

## Cloudflare staging setup gates

Nothing in this folder provisions a bucket, turns on paid services, or deploys. Do these only after the manager reviews pricing and explicitly provisions isolated staging resources. Do not use production resources.

1. Create a separate D1 database and private R2 bucket named for staging. Do not expose the bucket through `r2.dev` or a public custom domain.
2. Assign a staging hostname and configure a Cloudflare Access application for that exact hostname; enroll named colleague emails only. Record its team domain and audience tag.
3. Create and cost-check the image screening service; test representative legitimate field photos and explicit-content rejection before connecting it. If screening has no safe verdict, uploads must remain disabled.
4. In `wrangler.jsonc`, replace the D1 UUID, team domain, Access audience, origin, moderation Worker service name, and rate-limit namespace ID. Give the limiter namespace a unique number not shared with another Worker.
5. Set `SITUSNAP_TRIAL_EMAILS` and `SITUSNAP_TRIAL_MANAGERS` as Worker secrets. Manager emails may also be allowlisted, but no colleague should be able to edit the allowlist through the API.
6. Apply the D1 migration, add only verified synthetic test records, bind the private R2 bucket, and configure the moderator service binding.
7. Deploy only to staging. First test unauthorized requests, wrong/expired/revoked Access identities, invalid origins, image mismatch, third photo, explicit image, unavailable screening, rate limits, concurrent cap reservations, retrieve, delete, failed delete, and cleanup after interrupted upload.
8. Confirm the bucket is not public and inspect D1/R2 to verify the object and counters match. No genuine colleague photos until every check passes.
9. Then add the staging API base to the replacement app on `product/playstore-clean-site`; keep synchronization disabled in production until sign-in and field tests pass.

## Operational limitations to close before trial

- The screening service is an interface only; no provider is selected or enabled in this branch. Its price and false-positive behavior need review before staging uploads.
- The D1 cap is a logical ceiling on objects written through this Worker. Restrict the bucket so no other client or Worker can write to it, and monitor the actual R2 bucket as a reconciliation check.
- Cloudflare's regional rate-limit counters are intentionally approximate. They reduce bursts but are not a global request quota or storage limit.
- Records are seeded by an administrator outside this API. No admin record-import or enrolment-management endpoint is included.
- A database outage fails closed. If R2 deletion succeeds but D1 deletion fails, the photo row continues to consume quota until an authenticated delete retry or operator repair succeeds.
