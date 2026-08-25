const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("templates/map_template.html", "utf8");
const helperStart = source.indexOf("function isForeignTerritoryProtectedResponse");
const helperEnd = source.indexOf("async function aimMapTargetOnly", helperStart);
const mapActionStart = source.indexOf("async function mapAction");
const mapActionEnd = source.indexOf("const bikeDirectionIcons", mapActionStart);
const markerActionStart = source.indexOf("async function markerMenuAction");
const markerActionEnd = source.indexOf("function showTravelDestinationPulse", markerActionStart);
assert.ok(helperStart >= 0 && helperEnd > helperStart);
assert.ok(mapActionStart >= 0 && mapActionEnd > mapActionStart);
assert.ok(markerActionStart >= 0 && markerActionEnd > markerActionStart);

const messages = [];
const settlements = [];
const requests = [];
const aimedBefore = { target_id: "existing-target", lat: 51.9, lng: 20.9 };
const sandbox = {
    console: { error() {} },
    JSON, Math, Number, String,
    window: {
        profileData: { aimed_target: { ...aimedBefore } },
        setTimeout
    },
    fetch: async (url, options) => {
        requests.push({ url, body: JSON.parse(options.body) });
        return {
            ok: false,
            status: 403,
            json: async () => ({
                success: false,
                blocked: true,
                reason: "foreign_territory_protected",
                status: "Target znajduje sie na kontrolowanym terenie gracza Defender."
            })
        };
    },
    guardMapGameplayAction: () => false,
    closeMenus() {},
    beginMapScanEffect: () => null,
    finishMapScanEffectAfterPaint() {},
    showPendingMarkedTarget: target => ({ target, settled: false }),
    settlePendingMarkedTarget: (_handle, outcome, message) => settlements.push({ outcome, message }),
    addSystemMessage: (type, title, text) => messages.push({ type, title, text })
};
sandbox.window.window = sandbox.window;
vm.createContext(sandbox);
vm.runInContext(source.slice(helperStart, helperEnd), sandbox);
vm.runInContext(source.slice(mapActionStart, mapActionEnd), sandbox);
vm.runInContext(source.slice(markerActionStart, markerActionEnd), sandbox);

(async () => {
    await sandbox.markerMenuAction(
        "mark_target", 52.001, 21.001, "Enemy object", "X", "bench", "Enemy object", false
    );
    assert.strictEqual(requests.length, 1);
    assert.strictEqual(requests[0].url, "/map-action");
    assert.strictEqual(requests[0].body.action, "mark_target");
    assert.strictEqual(messages.length, 1, "expected 403 must produce exactly one system message");
    assert.strictEqual(messages[0].type, "warning");
    assert.match(messages[0].text, /Defender/);
    assert.deepStrictEqual(settlements, [{ outcome: "failed", message: "TARGET PROTECTED" }]);
    assert.deepStrictEqual(sandbox.window.profileData.aimed_target, aimedBefore);

    messages.length = 0;
    settlements.length = 0;
    requests.length = 0;
    await sandbox.mapAction("scan", 52.001, 21.001);
    assert.strictEqual(requests.length, 1);
    assert.strictEqual(requests[0].body.action, "scan");
    assert.strictEqual(messages.length, 1, "direct foreign scan must keep its controlled message");
    assert.strictEqual(settlements.length, 0);
    assert.deepStrictEqual(sandbox.window.profileData.aimed_target, aimedBefore);
    console.log("foreign territory scan-result mark tests: OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
