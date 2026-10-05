import test from "node:test";
import assert from "node:assert/strict";
import worker, { __test } from "../src/index.js";

test("unconfigured Access fails closed", async () => {
  const request = new Request("https://api.example/v1/records/r1/photos", { method: "GET" });
  const result = await __test.authenticate(request, {});
  assert.equal(result.ok, false);
  assert.equal(result.status, 503);
});

test("malformed Access JWT is rejected before JWKS network access", async () => {
  const request = new Request("https://api.example/v1/records/r1/photos", {
    headers: { "cf-access-jwt-assertion": "not.a.jwt" },
  });
  const env = {
    CF_ACCESS_TEAM_DOMAIN: "team.cloudflareaccess.com",
    CF_ACCESS_AUD: "expected-audience",
    SITUSNAP_TRIAL_EMAILS: "colleague@example.com",
  };
  const result = await __test.authenticate(request, env);
  assert.equal(result.ok, false);
  assert.equal(result.status, 401);
});

test("image sniffing recognizes only supported real file signatures", async () => {
  assert.equal(await __test.imageType(Uint8Array.from([0xff, 0xd8, 0xff, 0x00])), "image/jpeg");
  assert.equal(await __test.imageType(Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])), "image/png");
  assert.equal(await __test.imageType(new TextEncoder().encode("RIFFxxxxWEBP")), "image/webp");
  assert.equal(await __test.imageType(new TextEncoder().encode("GIF89a")), "");
  assert.equal(await __test.imageType(new TextEncoder().encode("not an image")), "");
});

test("malformed, oversized, insecure origins are not accepted", () => {
  assert.equal(__test.cleanOrigin("https://app.example"), "https://app.example");
  assert.equal(__test.cleanOrigin("https://app.example/"), "https://app.example");
  assert.equal(__test.cleanOrigin("http://app.example"), "");
  assert.equal(__test.cleanOrigin("https://app.example/path"), "");
  assert.equal(__test.cleanOrigin("null"), "");
});

test("manager list is case-insensitive and does not grant access by substring", () => {
  assert.equal(__test.isManager({ SITUSNAP_TRIAL_MANAGERS: "Manager@Example.com" }, "manager@example.com"), true);
  assert.equal(__test.isManager({ SITUSNAP_TRIAL_MANAGERS: "manager@example.com" }, "xmanager@example.com"), false);
  assert.equal(__test.isManager({}, "manager@example.com"), false);
});

test("unknown or missing moderation verdict fails closed", async () => {
  await assert.rejects(() => __test.moderate({}, "image/jpeg", new Uint8Array([1])), /MODERATION_NOT_CONFIGURED/);
  await assert.rejects(() => __test.moderate({
    MODERATOR: { fetch: async () => new Response(JSON.stringify({ verdict: "maybe", model: "test" })) },
  }, "image/jpeg", new Uint8Array([1])), /MODERATION_UNAVAILABLE/);
  await assert.rejects(() => __test.moderate({
    MODERATOR: { fetch: async () => new Response(JSON.stringify({ verdict: "reject", model: "test" })) },
  }, "image/jpeg", new Uint8Array([1])), /IMAGE_REJECTED/);
  assert.equal(await __test.moderate({
    MODERATOR: { fetch: async () => new Response(JSON.stringify({ verdict: "allow", model: "unit-test-v1" })) },
  }, "image/jpeg", new Uint8Array([1])), "unit-test-v1");
});

test("unconfigured access cannot reach a private API route", async () => {
  const response = await worker.fetch(new Request("https://api.example/v1/records/r1/photos"), {
    DB: {}, PHOTOS: {},
  });
  assert.equal(response.status, 503);
  assert.match((await response.json()).error, /not configured/i);
});

test("cross-origin browser requests are rejected", async () => {
  const response = await worker.fetch(new Request("https://api.example/v1/records/r1/photos", {
    headers: { Origin: "https://attacker.example" },
  }), { ALLOWED_ORIGIN: "https://app.example", DB: {}, PHOTOS: {} });
  assert.equal(response.status, 403);
});

test("scheduled reservation cleanup deletes the object before releasing its bytes", async () => {
  const events = [];
  const env = {
    DB: {
      prepare(sql) {
        return {
          bind(...args) {
            return {
              async all() { return { results: [{ photo_id: "p1", object_key: "trial/p1" }] }; },
              async run() { events.push(["db", sql.includes("DELETE FROM photos") ? "release" : "prune", args]); return { meta: { changes: 1 } }; },
            };
          },
        };
      },
    },
    PHOTOS: { async delete(key) { events.push(["r2", key]); } },
  };
  await __test.cleanExpiredReservations(env, 10_000);
  assert.deepEqual(events.map((v) => v.slice(0, 2)), [["r2", "trial/p1"], ["db", "release"], ["db", "prune"]]);
});
