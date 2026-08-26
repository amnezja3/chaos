"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const start = source.indexOf("function googleplexInstallErrorDetails");
const end = source.indexOf("function showInstallAppProgress", start);
assert.ok(start >= 0 && end > start, "Googleplex response helpers must exist");

const focused = [];
const sandbox = {
    Number, String, Object,
    notifyOpenMapsBlacknetFocus(payload) { focused.push(payload); }
};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);

assert.strictEqual(sandbox.applyGoogleplexTravelToOpenMaps({ travel: {
    receipt: "receipt-1", position: { lat: 52.2, lng: 21.0 }, position_version: 3
} }), true);
assert.strictEqual(focused.length, 1);
assert.strictEqual(focused[0].mode, "teleport");
assert.strictEqual(focused[0].receipt, "receipt-1");
assert.strictEqual(sandbox.applyGoogleplexTravelToOpenMaps({}), false);

const conflict = sandbox.googleplexInstallErrorDetails(
    { status: 409 }, { reason: "profile_write_conflict", message: "Stan konta sie zmienil." }
);
assert.strictEqual(conflict.httpStatus, 409);
assert.strictEqual(conflict.reasonCode, "profile_write_conflict");
assert.strictEqual(conflict.message, "Stan konta sie zmienil.");
const validation = sandbox.googleplexInstallErrorDetails({ status: 422 }, {});
assert.ok(validation.message.includes("walidacji"));

console.log("googleplex runtime bridge tests: OK");
