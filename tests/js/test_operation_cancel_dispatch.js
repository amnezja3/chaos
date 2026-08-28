"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("templates/map_template.html", "utf8");
const start = source.indexOf("window.operationCancelInFlight =");
const end = source.indexOf("if (!window.activeOperationCancelHandlerBound)", start);
assert.ok(start >= 0 && end > start, "operation cancel client must exist");

let resolveFetch;
let requests = 0;
let refreshes = 0;
let panelRenders = 0;
let markerRenders = 0;
const fetchResult = new Promise(resolve => { resolveFetch = resolve; });
const sandbox = {
    Map, Promise, String, Array, JSON,
    console: { warn() {} },
    fetch: async (url, options) => {
        requests += 1;
        assert.strictEqual(url, "/api/operations/cancel");
        assert.deepStrictEqual(JSON.parse(options.body), { operation_id: "op-one" });
        return fetchResult;
    },
    window: {
        latestActiveOperations: [{ operation_id: "op-one", status: "running" }],
        latestOperationHistory: [],
        renderActiveOperationsPanel() { panelRenders += 1; },
        renderActiveOperationMarkers() { markerRenders += 1; },
        notifyOperationLifecycle() {},
        async refreshActiveOperations() { refreshes += 1; return true; },
    },
};
sandbox.window.window = sandbox.window;
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);

(async () => {
    const first = sandbox.window.cancelActiveOperation("op-one");
    const duplicate = sandbox.window.cancelActiveOperation("op-one");

    assert.strictEqual(first, duplicate, "concurrent cancel must share one logical request");
    assert.strictEqual(requests, 1, "one user operation may emit at most one POST while in flight");
    assert.strictEqual(sandbox.window.operationCancelInFlight.size, 1);

    resolveFetch({
        ok: true,
        status: 200,
        json: async () => ({
            success: true,
            result: "cancelled",
            active_operations: [],
            operation_history: [{ operation_id: "op-one", status: "cancelled" }],
        }),
    });
    const payload = await first;

    assert.strictEqual(payload.result, "cancelled");
    assert.strictEqual(requests, 1);
    assert.strictEqual(refreshes, 1);
    assert.strictEqual(sandbox.window.operationCancelInFlight.size, 0);
    assert.deepStrictEqual(sandbox.window.latestActiveOperations, []);
    assert.strictEqual(markerRenders, 1);
    assert.ok(panelRenders >= 2, "button state and canonical response must both render");

    const routeCalls = source.match(/fetch\('\/api\/operations\/cancel'/g) || [];
    assert.strictEqual(routeCalls.length, 1, "frontend must keep one canonical cancel endpoint callsite");
    console.log("operation cancel dispatch tests: OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
