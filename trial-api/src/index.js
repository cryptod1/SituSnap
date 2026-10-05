const MAX_PHOTO_BYTES = 12 * 1024 * 1024;
const STORAGE_CAP_BYTES = 7_000_000_000;
const TRIAL_COMPANY = "situsnap-trial";
const ALLOWED_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);

function cleanOrigin(value) {
  try {
    const u = new URL(value);
    if (u.protocol !== "https:" || u.origin !== value.replace(/\/$/, "")) return "";
    return u.origin;
  } catch { return ""; }
}

function headersFor(request, env) {
  const allowed = cleanOrigin(env.ALLOWED_ORIGIN || "");
  const origin = request.headers.get("Origin");
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "vary": "Origin",
  };
  if (origin && allowed && origin === allowed) {
    headers["access-control-allow-origin"] = allowed;
    headers["access-control-allow-credentials"] = "true";
    headers["access-control-allow-headers"] = "content-type, cf-access-jwt-assertion";
    headers["access-control-allow-methods"] = "GET, POST, DELETE, OPTIONS";
    headers["access-control-max-age"] = "600";
  }
  return headers;
}

function json(request, env, body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...headersFor(request, env), ...extraHeaders },
  });
}

function base64urlBytes(input) {
  const padded = input.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - input.length % 4) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (c) => c.charCodeAt(0));
}

let jwksCache = { domain: "", expiresAt: 0, keys: [] };

function accessConfiguration(env) {
  const domain = String(env.CF_ACCESS_TEAM_DOMAIN || "").trim().toLowerCase();
  const audience = String(env.CF_ACCESS_AUD || "").trim();
  const emails = String(env.SITUSNAP_TRIAL_EMAILS || "")
    .split(",").map((v) => v.trim().toLowerCase()).filter(Boolean);
  const company = String(env.SITUSNAP_COMPANY_ID || TRIAL_COMPANY).trim();
  if (!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(domain) || !audience || !emails.length || !company) return null;
  return { domain, audience, emails, company };
}

async function accessKeys(domain) {
  const now = Date.now();
  if (jwksCache.domain === domain && jwksCache.expiresAt > now && jwksCache.keys.length) return jwksCache.keys;
  const response = await fetch(`https://${domain}/cdn-cgi/access/certs`, {
    headers: { accept: "application/json" }, redirect: "error", signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("ACCESS_KEYS_UNAVAILABLE");
  const data = await response.json();
  if (!Array.isArray(data?.keys) || data.keys.length < 1 || data.keys.length > 20) throw new Error("ACCESS_KEYS_INVALID");
  jwksCache = { domain, keys: data.keys, expiresAt: now + 10 * 60 * 1000 };
  return data.keys;
}

async function authenticate(request, env) {
  const config = accessConfiguration(env);
  if (!config) return { ok: false, status: 503, error: "Trial access is not configured." };
  const token = request.headers.get("cf-access-jwt-assertion") || "";
  const parts = token.split(".");
  if (parts.length !== 3 || token.length > 16_384) return { ok: false, status: 401, error: "Cloudflare Access sign-in is required." };
  try {
    const header = JSON.parse(new TextDecoder().decode(base64urlBytes(parts[0])));
    const claims = JSON.parse(new TextDecoder().decode(base64urlBytes(parts[1])));
    if (header.alg !== "RS256" || typeof header.kid !== "string" || header.crit) throw new Error("TOKEN_INVALID");
    const keys = await accessKeys(config.domain);
    const jwk = keys.find((key) => key.kid === header.kid && key.kty === "RSA" && (!key.alg || key.alg === "RS256"));
    if (!jwk) throw new Error("TOKEN_INVALID");
    const key = await crypto.subtle.importKey("jwk", jwk, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
    const valid = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, base64urlBytes(parts[2]), new TextEncoder().encode(`${parts[0]}.${parts[1]}`));
    if (!valid) throw new Error("TOKEN_INVALID");
    const now = Math.floor(Date.now() / 1000);
    const audiences = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
    if (claims.iss !== `https://${config.domain}` || !audiences.includes(config.audience) ||
        !Number.isSafeInteger(claims.exp) || claims.exp <= now ||
        (claims.nbf !== undefined && (!Number.isSafeInteger(claims.nbf) || claims.nbf > now + 30))) throw new Error("TOKEN_INVALID");
    const email = String(claims.email || "").trim().toLowerCase();
    if (!email || !config.emails.includes(email)) return { ok: false, status: 403, error: "This colleague is not enrolled for the SituSnap trial." };
    return { ok: true, email, company: config.company };
  } catch (error) {
    if (error?.message === "ACCESS_KEYS_UNAVAILABLE" || error?.message === "ACCESS_KEYS_INVALID" || error?.name === "TimeoutError" || error?.name === "TypeError") {
      return { ok: false, status: 503, error: "Trial sign-in could not be checked." };
    }
    return { ok: false, status: 401, error: "Cloudflare Access sign-in is invalid or expired." };
  }
}

async function digestHex(value) {
  const bytes = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function enforceRateLimit(env, auth, action, now = Date.now()) {
  if (!env.DB || !env.RATE_LIMITER?.limit) throw new Error("RATE_LIMIT_NOT_CONFIGURED");
  const subject = await digestHex(`${auth.company}:${auth.email}`);
  const edge = await env.RATE_LIMITER.limit({ key: `${subject}:${action}` });
  if (!edge?.success) return false;
  const limits = { upload: { count: 6, seconds: 60 }, read: { count: 60, seconds: 60 }, delete: { count: 6, seconds: 60 } };
  const limit = limits[action];
  if (!limit) return false;
  const windowStart = Math.floor(now / (limit.seconds * 1000)) * limit.seconds;
  const result = await env.DB.prepare(`
    INSERT INTO rate_windows (window_key, window_start, request_count)
    VALUES (?1, ?2, 1)
    ON CONFLICT(window_key) DO UPDATE SET
      request_count = CASE WHEN rate_windows.window_start = excluded.window_start
        THEN rate_windows.request_count + 1 ELSE 1 END,
      window_start = excluded.window_start
    WHERE rate_windows.window_start <> excluded.window_start OR rate_windows.request_count < ?3
  `).bind(`${subject}:${action}`, windowStart, limit.count).run();
  return result.meta?.changes === 1;
}

function isManager(env, email) {
  return String(env.SITUSNAP_TRIAL_MANAGERS || "").split(",")
    .map((value) => value.trim().toLowerCase()).filter(Boolean).includes(email);
}

async function imageType(bytes) {
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "image/jpeg";
  if (bytes.length >= 8 && bytes[0] === 0x89 && String.fromCharCode(...bytes.subarray(1, 4)) === "PNG" && bytes[4] === 0x0d && bytes[5] === 0x0a && bytes[6] === 0x1a && bytes[7] === 0x0a) return "image/png";
  if (bytes.length >= 12 && String.fromCharCode(...bytes.subarray(0, 4)) === "RIFF" && String.fromCharCode(...bytes.subarray(8, 12)) === "WEBP") return "image/webp";
  return "";
}

function safeId(value) { return /^[A-Za-z0-9_-]{1,80}$/.test(value || ""); }

async function moderate(env, contentType, bytes) {
  if (!env.MODERATOR?.fetch) throw new Error("MODERATION_NOT_CONFIGURED");
  let response;
  try {
    response = await env.MODERATOR.fetch("https://moderation.internal/v1/check", {
      method: "POST",
      headers: { "content-type": contentType, "x-situsnap-purpose": "explicit-content-screening" },
      body: bytes,
      signal: AbortSignal.timeout(10_000),
    });
  } catch { throw new Error("MODERATION_UNAVAILABLE"); }
  if (!response.ok) throw new Error("MODERATION_UNAVAILABLE");
  let result;
  try { result = await response.json(); } catch { throw new Error("MODERATION_UNAVAILABLE"); }
  if (result?.verdict === "reject") throw new Error("IMAGE_REJECTED");
  if (result?.verdict !== "allow" || typeof result.model !== "string" || !result.model) throw new Error("MODERATION_UNAVAILABLE");
  return result.model.slice(0, 80);
}

function routeMatch(path, regex) { return regex.exec(path); }

async function uploadPhoto(request, env, auth, recordId, url) {
  if (!safeId(recordId)) return json(request, env, { error: "Invalid record ID." }, 400);
  const slot = Number(url.searchParams.get("slot"));
  if (![1, 2].includes(slot)) return json(request, env, { error: "Trial limit: up to 2 photos per verified record." }, 400);
  const headerType = String(request.headers.get("content-type") || "").split(";")[0].trim().toLowerCase();
  const length = Number(request.headers.get("content-length"));
  if (!Number.isSafeInteger(length) || length < 1 || length > MAX_PHOTO_BYTES || !ALLOWED_IMAGE_TYPES.has(headerType)) {
    return json(request, env, { error: "Photo must be a JPEG, PNG, or WebP image up to 12 MiB." }, 413);
  }
  const record = await env.DB.prepare("SELECT record_id FROM trial_records WHERE record_id = ?1 AND company_id = ?2 AND verified_at IS NOT NULL LIMIT 1")
    .bind(recordId, auth.company).first();
  if (!record) return json(request, env, { error: "Verified trial record not found." }, 404);

  let bytes;
  try {
    bytes = new Uint8Array(await request.arrayBuffer());
  } catch { return json(request, env, { error: "Photo could not be read." }, 400); }
  if (bytes.length !== length || bytes.length > MAX_PHOTO_BYTES) return json(request, env, { error: "Photo size does not match the request." }, 400);
  const detectedType = await imageType(bytes);
  if (!detectedType || detectedType !== headerType) return json(request, env, { error: "Photo content does not match its declared image type." }, 415);

  const photoId = crypto.randomUUID();
  const objectKey = `trial/${photoId}`;
  const uploadedBy = await digestHex(`${auth.company}:${auth.email}`);
  const now = Math.floor(Date.now() / 1000);
  try {
    await env.DB.prepare(`INSERT INTO photos
      (photo_id, record_id, slot, content_type, byte_size, object_key, state, uploaded_by, uploaded_at, reservation_expires_at)
      VALUES (?1, ?2, ?3, ?4, ?5, ?6, 'reserved', ?7, ?8, ?9)`)
      .bind(photoId, recordId, slot, detectedType, bytes.length, objectKey, uploadedBy, now, now + 15 * 60).run();
  } catch (error) {
    if (/storage full/i.test(String(error?.message))) return json(request, env, { error: "Trial photo storage is full." }, 507);
    if (/UNIQUE|constraint/i.test(String(error?.message))) return json(request, env, { error: "This photo slot is already in use." }, 409);
    throw error;
  }

  let model;
  try {
    model = await moderate(env, detectedType, bytes);
    await env.PHOTOS.put(objectKey, bytes, {
      httpMetadata: { contentType: detectedType, cacheControl: "private, no-store" },
      customMetadata: { photoId, recordId, screenedBy: model },
    });
    const changed = await env.DB.prepare("UPDATE photos SET state = 'stored', reservation_expires_at = NULL, screened_by = ?2 WHERE photo_id = ?1 AND state = 'reserved'")
      .bind(photoId, model).run();
    if (changed.meta?.changes !== 1) throw new Error("PHOTO_COMMIT_FAILED");
  } catch (error) {
    try { await env.PHOTOS.delete(objectKey); } catch { /* retained reservation blocks quota until repair */ }
    try { await env.DB.prepare("DELETE FROM photos WHERE photo_id = ?1 AND state = 'reserved'").bind(photoId).run(); } catch { /* cleanup task retries */ }
    if (error?.message === "IMAGE_REJECTED") {
      console.info("situsnap_trial_event", { event: "photo_rejected", actor: uploadedBy, reason: "explicit_content" });
      return json(request, env, { error: "This image cannot be stored. Please contact the trial manager if you believe this is a mistake." }, 422);
    }
    if (error?.message === "MODERATION_NOT_CONFIGURED" || error?.message === "MODERATION_UNAVAILABLE") {
      console.info("situsnap_trial_event", { event: "photo_screening_unavailable", actor: uploadedBy });
      return json(request, env, { error: "Photo screening is temporarily unavailable; no photo was retained." }, 503);
    }
    throw error;
  }
  return json(request, env, { photoId, recordId, slot, contentType: detectedType, byteSize: bytes.length }, 201);
}

async function handle(request, env) {
  const url = new URL(request.url);
  if (url.pathname === "/health" && request.method === "GET") return json(request, env, { ok: true });
  const configuredOrigin = cleanOrigin(env.ALLOWED_ORIGIN || "");
  const origin = request.headers.get("Origin");
  if (origin && (!configuredOrigin || origin !== configuredOrigin)) return json(request, env, { error: "Origin is not allowed." }, 403);
  if (request.method === "OPTIONS") {
    if (!configuredOrigin || (origin && origin !== configuredOrigin)) return json(request, env, { error: "Origin is not allowed." }, 403);
    return new Response(null, { status: 204, headers: headersFor(request, env) });
  }
  if (!url.pathname.startsWith("/v1/")) return json(request, env, { error: "Not found." }, 404);
  if (!env.DB || !env.PHOTOS) return json(request, env, { error: "Trial storage is not configured." }, 503);
  const auth = await authenticate(request, env);
  if (!auth.ok) return json(request, env, { error: auth.error }, auth.status);
  const recordPhoto = routeMatch(url.pathname, /^\/v1\/records\/([^/]+)\/photos$/);
  const photoResource = routeMatch(url.pathname, /^\/v1\/photos\/([^/]+)$/);

  if (url.pathname === "/v1/admin/usage" && request.method === "GET") {
    if (!isManager(env, auth.email)) return json(request, env, { error: "Trial manager access is required." }, 403);
    let allowed;
    try { allowed = await enforceRateLimit(env, auth, "read"); }
    catch { return json(request, env, { error: "Trial abuse controls are unavailable." }, 503); }
    if (!allowed) return json(request, env, { error: "Read rate limit reached. Try again shortly." }, 429);
    const [usage, count] = await Promise.all([
      env.DB.prepare("SELECT used_bytes AS usedBytes, reserved_bytes AS reservedBytes FROM storage_usage WHERE singleton = 1").first(),
      env.DB.prepare("SELECT COUNT(*) AS photoCount FROM photos WHERE state = 'stored'").first(),
    ]);
    const usedBytes = Number(usage?.usedBytes || 0);
    const reservedBytes = Number(usage?.reservedBytes || 0);
    return json(request, env, {
      capBytes: STORAGE_CAP_BYTES, usedBytes, reservedBytes,
      remainingBytes: Math.max(0, STORAGE_CAP_BYTES - usedBytes - reservedBytes),
      storedPhotoCount: Number(count?.photoCount || 0),
    });
  }

  if (recordPhoto && request.method === "POST") {
    let allowed;
    try { allowed = await enforceRateLimit(env, auth, "upload"); }
    catch { return json(request, env, { error: "Trial abuse controls are unavailable." }, 503); }
    if (!allowed) {
      console.info("situsnap_trial_event", { event: "rate_limited", action: "upload", actor: await digestHex(`${auth.company}:${auth.email}`) });
      return json(request, env, { error: "Upload rate limit reached. Try again shortly." }, 429);
    }
    return uploadPhoto(request, env, auth, decodeURIComponent(recordPhoto[1]), url);
  }
  if (recordPhoto && request.method === "GET") {
    let allowed;
    try { allowed = await enforceRateLimit(env, auth, "read"); }
    catch { return json(request, env, { error: "Trial abuse controls are unavailable." }, 503); }
    if (!allowed) return json(request, env, { error: "Read rate limit reached. Try again shortly." }, 429);
    const recordId = decodeURIComponent(recordPhoto[1]);
    const rows = await env.DB.prepare(`SELECT p.photo_id AS photoId, p.record_id AS recordId, p.slot,
      p.content_type AS contentType, p.byte_size AS byteSize, p.uploaded_at AS uploadedAt
      FROM photos p JOIN trial_records r ON r.record_id = p.record_id
      WHERE p.record_id = ?1 AND r.company_id = ?2 AND p.state = 'stored' ORDER BY p.slot`)
      .bind(recordId, auth.company).all();
    return json(request, env, { photos: rows.results || [] });
  }
  if (photoResource && request.method === "GET") {
    let allowed;
    try { allowed = await enforceRateLimit(env, auth, "read"); }
    catch { return json(request, env, { error: "Trial abuse controls are unavailable." }, 503); }
    if (!allowed) return json(request, env, { error: "Read rate limit reached. Try again shortly." }, 429);
    const photoId = decodeURIComponent(photoResource[1]);
    const photo = await env.DB.prepare(`SELECT p.photo_id, p.object_key, p.content_type, p.byte_size
      FROM photos p JOIN trial_records r ON r.record_id = p.record_id
      WHERE p.photo_id = ?1 AND r.company_id = ?2 AND p.state = 'stored' LIMIT 1`).bind(photoId, auth.company).first();
    if (!photo) return json(request, env, { error: "Photo not found." }, 404);
    const object = await env.PHOTOS.get(photo.object_key);
    if (!object) return json(request, env, { error: "Photo is temporarily unavailable." }, 503);
    return new Response(object.body, { status: 200, headers: {
      "content-type": photo.content_type, "content-length": String(photo.byte_size),
      "cache-control": "private, no-store", "x-content-type-options": "nosniff",
      "content-disposition": "inline; filename=\"evidence\"", "referrer-policy": "no-referrer",
      ...corsHeadersForBinary(request, env),
    } });
  }
  if (photoResource && request.method === "DELETE") {
    let allowed;
    try { allowed = await enforceRateLimit(env, auth, "delete"); }
    catch { return json(request, env, { error: "Trial abuse controls are unavailable." }, 503); }
    if (!allowed) {
      console.info("situsnap_trial_event", { event: "rate_limited", action: "delete", actor: await digestHex(`${auth.company}:${auth.email}`) });
      return json(request, env, { error: "Delete rate limit reached. Try again shortly." }, 429);
    }
    const photoId = decodeURIComponent(photoResource[1]);
    const photo = await env.DB.prepare(`SELECT p.photo_id, p.object_key, p.state, p.uploaded_by
      FROM photos p JOIN trial_records r ON r.record_id = p.record_id
      WHERE p.photo_id = ?1 AND r.company_id = ?2 LIMIT 1`).bind(photoId, auth.company).first();
    if (!photo) return json(request, env, { error: "Photo not found." }, 404);
    const subject = await digestHex(`${auth.company}:${auth.email}`);
    if (photo.uploaded_by !== subject && !isManager(env, auth.email)) return json(request, env, { error: "Only the uploader or a trial manager can delete this photo." }, 403);
    try {
      await env.PHOTOS.delete(photo.object_key);
      await env.DB.prepare("DELETE FROM photos WHERE photo_id = ?1").bind(photoId).run();
    } catch {
      return json(request, env, { error: "Photo deletion could not be confirmed; storage remains reserved." }, 503);
    }
    return json(request, env, { deleted: true, photoId });
  }
  if (request.method === "POST") return json(request, env, { error: "Not found." }, 404);
  return json(request, env, { error: "Method not allowed." }, 405, { allow: "GET, POST, DELETE, OPTIONS" });
}

function corsHeadersForBinary(request, env) {
  const h = headersFor(request, env);
  const out = {};
  for (const key of ["access-control-allow-origin", "access-control-allow-credentials", "vary"]) if (h[key]) out[key] = h[key];
  return out;
}

export default {
  async fetch(request, env) {
    try { return await handle(request, env); }
    catch (error) {
      console.error("situsnap_trial_api_error", { name: error?.name || "Error" });
      return json(request, env, { error: "Trial service temporarily unavailable." }, 503);
    }
  },
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(cleanExpiredReservations(env));
  },
};

async function cleanExpiredReservations(env, now = Math.floor(Date.now() / 1000)) {
  const expired = await env.DB.prepare("SELECT photo_id, object_key FROM photos WHERE state = 'reserved' AND reservation_expires_at < ?1 LIMIT 100")
    .bind(now).all();
  for (const row of expired.results || []) {
    await env.PHOTOS.delete(row.object_key);
    await env.DB.prepare("DELETE FROM photos WHERE photo_id = ?1 AND state = 'reserved'").bind(row.photo_id).run();
  }
  await env.DB.prepare("DELETE FROM rate_windows WHERE window_start < ?1").bind(Math.floor(now / 60) - 10).run();
}

export const __test = { authenticate, enforceRateLimit, imageType, cleanOrigin, moderate, cleanExpiredReservations, isManager, constants: { MAX_PHOTO_BYTES, STORAGE_CAP_BYTES, TRIAL_COMPANY } };
