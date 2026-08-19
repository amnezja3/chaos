const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

function marker(coords, options) {
    return {
        coords, options,
        addTo() { return this; },
        setLatLng(next) { this.coords = next; return this; },
        setIcon() { return this; },
        on() { return this; },
        off() { return this; },
        bindPopup() { return this; },
        openPopup() { return this; },
        getLatLng() { return { lat: this.coords[0], lng: this.coords[1] }; }
    };
}

const panes = {};
const map = {
    createPane(name) { return (panes[name] = { style: {} }); },
    getPane(name) { return panes[name] || null; },
    removeLayer() {}
};
const sandbox = {
    console: { warn() {} },
    Set, Promise,
    window: { chaosMap: map },
    L: {
        divIcon(options) { return options; },
        marker,
        polyline() { return { addTo() { return this; } }; },
        layerGroup() { return { addTo() { return this; } }; }
    }
};
sandbox.window.window = sandbox.window;
sandbox.window.L = sandbox.L;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync("static/js/map/ghostnetwork.js", "utf8"), sandbox);

function response(payload) {
    return { ok: true, json: async () => payload };
}

(async () => {
    const win = sandbox.window;
    win.fetchMapSnapshot = async () => ({ res: response({
        ok: true,
        cycle: { cycle_id: "cycle-1", state_version: 2 },
        parts: [{ public_entity_id: "part-1", can_show_on_map: true, location_visibility: "exact", latitude: 1, longitude: 2 }],
        connections: []
    }) });
    assert.strictEqual(await win.loadGhostNetworkSnapshot(), true);
    assert.ok(win.ghostNetworkPartLayers["part-1"]);

    win.fetchMapSnapshot = async () => ({ res: response({ ok: true, cycle: { cycle_id: "cycle-1" } }) });
    assert.strictEqual(await win.loadGhostNetworkSnapshot(), false);
    assert.ok(win.ghostNetworkPartLayers["part-1"], "incomplete snapshot must retain last good layer");

    win.fetchMapSnapshot = async () => ({ res: response({
        ok: true,
        cycle: { cycle_id: "cycle-1", state_version: 1 },
        parts: [], connections: []
    }) });
    assert.strictEqual(await win.loadGhostNetworkSnapshot(), false);
    assert.ok(win.ghostNetworkPartLayers["part-1"], "stale snapshot must retain newer delta state");

    let recoveryFetches = 0;
    let release;
    win.fetchMapSnapshot = async () => {
        recoveryFetches += 1;
        await new Promise(resolve => { release = resolve; });
        return { res: response({ ok: true, cycle: { cycle_id: "cycle-1", state_version: 2 }, parts: [], connections: [] }) };
    };
    const first = win.recoverGhostNetworkLayer();
    const second = win.recoverGhostNetworkLayer();
    assert.strictEqual(recoveryFetches, 1, "concurrent recovery must share one request");
    release();
    await Promise.all([first, second]);

    for (let index = 0; index < 25; index += 1) {
        win.renderGhostTerritoryBadge({ public_entity_id: `pending-${index}`, territory_id: `missing-${index}` });
    }
    assert.strictEqual(Object.keys(win.ghostNetworkPendingTerritoryParts).length, 20);
    win.removeGhostPartMarker("pending-24");
    assert.strictEqual(win.ghostNetworkPendingTerritoryParts["pending-24"], undefined);

    console.log("ghostnetwork map renderer tests: OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
