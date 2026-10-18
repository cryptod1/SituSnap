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

const restore = section("async function ssRestoreCachedPhotoPair(id,", "function ssConfirmRemoveVerified(");
assert(restore.includes("store.put(mainBlob,String(id))") && restore.includes('store.put(extraBlob,String(id)+"::extra")'),
  "rollback must restore the previous main and extra photo blobs");
assert(restore.includes("Photo restore read-back failed"), "rollback must verify restored photo presence");
assert(finish.includes("previousPhotoState={main,extra,mainPresent:!!main,extraPresent:!!extra}"),
  "existing photo state must be snapshotted before a save attempt");

const removal = section("async function ssRemoveVerifiedLocation(id){", "function render(){");
assert(
  removal.indexOf("await ssDeleteCachedPhoto(sid)") < removal.indexOf('localStorage.setItem("situSnapRecords"'),
  "location removal must not mutate the saved record list before photo deletion is confirmed"
);
assert(
  removal.includes("if(!photoDeleted)") && removal.includes("return;"),
  "failed photo deletion must stop the location-removal path"
);


// Exercise the actual deletion function with an IndexedDB-shaped test double.
// Bind the IndexedDB helpers lexically for the function body.
const deleteSandbox = {
  console: { warn() {} },
  ssPhotoDb: null,
  ssGetCachedPhoto: null,
  ssGetExtraCachedPhoto: null
};
const deletionRunner = vm.runInNewContext(`${deletion}; async function run(){ return await ssDeleteCachedPhoto("rec-1"); }`, deleteSandbox);
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

  // Simulate a partially failed update and verify rollback restores old blobs.
  const restoreSandbox = {
    console: { warn() {} },
    ssPhotoDb: null,
    ssGetCachedPhoto: null,
    ssGetExtraCachedPhoto: null
  };
  const restoreRunner = vm.runInNewContext(
    `${restore}; async function run(){ return await ssRestoreCachedPhotoPair("rec-2", "old-main", "old-extra", true, true); }`,
    restoreSandbox
  );
  const changedPhotos = new Map([["rec-2", "new-main"], ["rec-2::extra", "old-extra"]]);
  const restoreDb = {
    close() {},
    transaction() {
      const tx = {
        error: new Error("simulated restore failure"),
        objectStore() {
          return {
            delete(key) { changedPhotos.delete(key); },
            put(value, key) { changedPhotos.set(key, value); }
          };
        }
      };
      queueMicrotask(() => tx.oncomplete?.());
      return tx;
    }
  };
  restoreSandbox.ssPhotoDb = async () => restoreDb;
  restoreSandbox.ssGetCachedPhoto = async id => changedPhotos.get(String(id)) || null;
  restoreSandbox.ssGetExtraCachedPhoto = async id => changedPhotos.get(String(id) + "::extra") || null;
  assert.equal(await restoreSandbox.run(), true, "rollback should restore prior photo pair");
  assert.equal(changedPhotos.get("rec-2"), "old-main");
  assert.equal(changedPhotos.get("rec-2::extra"), "old-extra");

  const writes = [];
  const alerts = [];
  const removeRunner = vm.runInNewContext(
    `${removal}; ssRemoveVerifiedLocation`,
    {
      getRecords: () => [{ id: "rec-1", address: "1, Oaklands Rise", postcode: "CF31 4SP" }],
      ssConfirmRemoveVerified: async () => true,
      ssDeleteCachedPhoto: async () => false,
      alert: message => alerts.push(message),
      localStorage: { setItem: (...args) => writes.push(args) },
      console: { warn() {} }
    }
  );
  await removeRunner("rec-1");
  assert.equal(writes.length, 0, "failed photo deletion must not mutate saved removal state");
  assert.equal(alerts.length, 1);
  assert.match(alerts[0], /LOCATION NOT REMOVED/);

  console.log("PASS: deletion success, partial deletion, and transaction failure cases");
  console.log("PASS: failed deletion leaves the verified location and removal state untouched");
  console.log("PASS: failed save restores the previous main/extra photo pair");
})().catch(error => { console.error(error); process.exitCode = 1; });

console.log("PASS: 4 photo-target resolution cases");
console.log("PASS: photo save uses resolved ID before writing");
console.log("PASS: failed-save cleanup protects existing photos");
console.log("PASS: deletion read-back checks main and extra photos");
console.log("PASS: location removal stops if deletion cannot be confirmed");
