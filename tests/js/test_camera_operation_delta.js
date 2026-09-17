"use strict";
const assert = require("assert");
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("static/js/terminal.js", "utf8");
const select = (start, end) => {
    const from = source.indexOf(start);
    const to = source.indexOf(end, from);
    assert.ok(from >= 0 && to > from);
    return source.slice(from, to);
};
let refreshes = 0;
const seen = new Set();
const context = {
    desktopSessionActive: true,
    rememberProcessedDelta(key) { if (seen.has(key)) return true; seen.add(key); return false; },
    async notifyOpenMapsOperationsChanged() { refreshes++; },
    document: { querySelectorAll() { return []; } },
    console,
};
vm.createContext(context);
vm.runInContext(select("async function applyDelta(event)", "async function recoverProfileDeltaScopes"), context);
vm.runInContext(select("async function recoverMapDeltaScope()", "async function recoverTerritoryDeltaScope()"), context);
(async () => {
    const event = { scope: "map", type: "map.operations_changed", dedupe_key: "camera-one" };
    assert.strictEqual(await context.applyDelta(event), true);
    assert.strictEqual(refreshes, 1);
    assert.strictEqual(await context.applyDelta(event), false);
    assert.strictEqual(refreshes, 1);
    await context.recoverMapDeltaScope();
    assert.strictEqual(refreshes, 2);
    context.desktopSessionActive = false;
    assert.strictEqual(await context.applyDelta({ ...event, dedupe_key: "camera-two" }), false);
    assert.strictEqual(refreshes, 2);
    console.log("camera operation delta: PASS");
})().catch(error => { console.error(error); process.exitCode = 1; });
