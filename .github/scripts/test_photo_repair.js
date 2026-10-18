#!/usr/bin/env node
"use strict";

// Focused regression checks against the actual helper and repair paths in index.html.
// This is deliberately a lightweight source-level test; it does not replace device testing.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");

const html = fs.readFileSync("index.html", "utf8");

function section(startMarker, endMarker) {
  const start = html.indexOf(startMarker);
  assert.notEqual(start, -1, `Missing source marker: ${startMarker}`);
  const end = html.indexOf(endMarker, start);
  assert.notEqual(end, -1, `Missing end marker: ${endMarker}`);
  return html.slice(start, end);
}

const helper = section(
  "function ssResolvePhotoRecordTarget(){",
  "async function finishFound(){"
);

function resolveTarget({ editing = null, postcode = "CF31 4SP", address = "1, Oaklands Rise", records = [] } = {}) {
  const document = {
    getElementById(id) {
      if (id === "postcode") return { value: postcode };
      if (id === "address") return { value: address };
      return null;
    }
  };
  const sandbox = {
    document,
    editingRecordId: editing,
    getRecords: () => records,
    Date: { now: () => 987654321 }
  };
  return vm.runInNewContext(`(() => { ${helper}; return ssResolvePhotoRecordTarget(); })()`, sandbox);
}

assert.deepEqual(
  JSON.parse(JSON.stringify(resolveTarget({ editing: "edit-42" }))),
  { id: "edit-42", existing: true },
  "editing an existing record must preserve its ID"
);

assert.deepEqual(
  JSON.parse(JSON.stringify(resolveTarget({
    records: [{
      id: "archive-17",
      pinVerified: true,
      postcode: " cf31   4sp ",
      address: "1, OAKLANDS RISE"
    }]
  }))),
  { id: "archive-17", existing: true },
  "must reuse a canonical verified record returned by getRecords(), including archived/learned records"
);

assert.deepEqual(
  JSON.parse(JSON.stringify(resolveTarget({
    records: [{ id: "unverified-1", pinVerified: false, postcode: "CF31 4SP", address: "1, Oaklands Rise" }]
  }))),
  { id: 987654321, existing: false },
  "must not reuse an unverified matching record"
);

assert.deepEqual(
  JSON.parse(JSON.stringify(resolveTarget({
    records: [{ id: "other-1", pinVerified: true, postcode: "CF31 4SP", address: "2, Oaklands Rise" }]
  }))),
  { id: 987654321, existing: false },
  "must not reuse a different address"
);

const finish = section("async function finishFound(){", "function ssConfirmRemoveVerified(");
assert(
  finish.indexOf("const photoTarget=ssResolvePhotoRecordTarget();") < finish.indexOf("await ssUploadVerifiedPhoto(draft)"),
  "canonical record ID must be resolved before saving the photo"
);
assert(
  finish.includes("if(!photoTarget.existing){") && finish.includes("await ssDeleteCachedPhoto(recordId)"),
  "failed-save cleanup must be restricted to a newly-created temporary photo"
);

const deletion = section("async function ssDeleteCachedPhoto(id){", "function ssConfirmRemoveVerified(");
assert(deletion.includes("await ssGetCachedPhoto(id)") && deletion.includes("await ssGetExtraCachedPhoto(id)"),
  "deletion must read back both photo keys");
assert(deletion.includes("return false;"), "deletion must report failure rather than swallowing it");

const removal = section("async function ssRemoveVerifiedLocation(id){", "function render(){");
assert(
  removal.indexOf("await ssDeleteCachedPhoto(sid)") < removal.indexOf('localStorage.setItem("situSnapRecords"'),
  "location removal must not mutate the saved record list before photo deletion is confirmed"
);
assert(
  removal.includes("if(!photoDeleted)") && removal.includes("return;"),
  "failed photo deletion must stop the location-removal path"
);


// Exercise the actual deletion function with a small IndexedDB-shaped test double.
const deletionFunction = vm.runInNewContext(
  `(${deletion}; ssDeleteCachedPhoto)`,
  { console: { warn() {} } }
);
async function runDeleteCase({ initial = [], failKey = null, failTransaction = false } = {}) {
  const photos = new Map(initial);
  const db = {
    close() {},
    transaction() {
      const tx = {
        error: new Error("simulated IndexedDB transaction failure"),
        objectStore() {
          return {
            delete(key) {
              if (key !== failKey && !failTransaction) photos.delete(key);
            }
          };
        }
      };
      queueMicrotask(() => {
        if (failTransaction) tx.onerror?.();
        else tx.oncomplete?.();
      });
      return tx;
    }
  };
  const fn = deletionFunction;
  const sandboxResult = await fn.call({
    ssPhotoDb: async () => db,
    ssGetCachedPhoto: async id => photos.get(String(id)) || null,
    ssGetExtraCachedPhoto: async id => photos.get(String(id) + "::extra") || null
  }, "rec-1");
  return { result: sandboxResult, photos };
}

// Bind the IndexedDB helpers lexically for the function body.
const deleteSandbox = {
  console: { warn() {} },
  ssPhotoDb: null,
  ssGetCachedPhoto: null,
  ssGetExtraCachedPhoto: null
};
const deletionRunner = vm.runInNewContext(`async function run(){ return await ssDeleteCachedPhoto("rec-1"); }`, deleteSandbox);
async function executeDelete(initial, failKey = null, failTransaction = false) {
  const photos = new Map(initial);
  const db = {
    close() {},
    transaction() {
      const tx = {
        error: new Error("simulated IndexedDB transaction failure"),
        objectStore() {
          return { delete(key) { if (key !== failKey && !failTransaction) photos.delete(key); } };
        }
      };
      queueMicrotask(() => failTransaction ? tx.onerror?.() : tx.oncomplete?.());
      return tx;
    }
  };
  deleteSandbox.ssPhotoDb = async () => db;
  deleteSandbox.ssGetCachedPhoto = async id => photos.get(String(id)) || null;
  deleteSandbox.ssGetExtraCachedPhoto = async id => photos.get(String(id) + "::extra") || null;
  const result = await deleteSandbox.run();
  return { result, photos };
}
(async () => {
  const success = await executeDelete([["rec-1", "main"], ["rec-1::extra", "extra"]]);
  assert.equal(success.result, true, "deletion should succeed when both cached photos are gone");
  assert.equal(success.photos.size, 0);

  const partial = await executeDelete([["rec-1", "main"], ["rec-1::extra", "extra"]], "rec-1::extra");
  assert.equal(partial.result, false, "read-back must catch a remaining extra photo");
  assert.equal(partial.photos.has("rec-1::extra"), true);

  const transactionFailure = await executeDelete([["rec-1", "main"]], null, true);
  assert.equal(transactionFailure.result, false, "transaction failure must be reported");

  const writes = [];
  const alerts = [];
  const removal = vm.runInNewContext(
    `(${removal}; ssRemoveVerifiedLocation)`,
    {
      getRecords: () => [{ id: "rec-1", address: "1, Oaklands Rise", postcode: "CF31 4SP" }],
      ssConfirmRemoveVerified: async () => true,
      ssDeleteCachedPhoto: async () => false,
      alert: message => alerts.push(message),
      localStorage: { setItem: (...args) => writes.push(args) },
      console: { warn() {} }
    }
  );
  await removal("rec-1");
  assert.equal(writes.length, 0, "failed photo deletion must not mutate saved removal state");
  assert.equal(alerts.length, 1);
  assert.match(alerts[0], /LOCATION NOT REMOVED/);

  console.log("PASS: deletion success, partial deletion, and transaction failure cases");
  console.log("PASS: failed deletion leaves the verified location and removal state untouched");
})().catch(error => { console.error(error); process.exitCode = 1; });

console.log("PASS: 4 photo-target resolution cases");
console.log("PASS: photo save uses resolved ID before writing");
console.log("PASS: failed-save cleanup protects existing photos");
console.log("PASS: deletion read-back checks main and extra photos");
console.log("PASS: location removal stops if deletion cannot be confirmed");
