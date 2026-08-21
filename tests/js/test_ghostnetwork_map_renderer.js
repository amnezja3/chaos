const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

function marker(coords, options) {
    return {
        coords, options,
        addTo() { return this; },
        setLatLng(next) { this.coords = next; return this; },
        setIcon(next) { this.options.icon = next; return this; },
        on() { return this; },
        off() { return this; },
        bindPopup() { return this; },
        openPopup() { return this; },
        getLatLng() { return { lat: this.coords[0], lng: this.coords[1] }; }
    };
}

const panes = {};
function territoryLayer() {
    const classes = new Set(["leaflet-interactive"]);
    return {
        _classes: classes,
        getElement() {
            return {
                classList: {
                    add(...names) { names.forEach(name => classes.add(name)); },
                    remove(...names) { names.forEach(name => classes.delete(name)); }
                }
            };
        }
    };
}
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

    win.applyGhostPartDelta({
        scope: "ghostnetwork", type: "ghost.part_discovered", version: 3,
        payload: { projection: {
            public_entity_id: "art-part", can_show_on_map: true,
            location_visibility: "exact", latitude: 1.2, longitude: 2.2,
            module_state: "neutral",
            visual_asset_url: "/static/images/ghostnetwork/parts/v1_ledger_nexus.png"
        } }
    });
    const artMarker = win.ghostNetworkPartLayers["art-part"];
    assert.ok(artMarker.options.icon.html.includes("v1_ledger_nexus.png"));
    assert.ok(artMarker.options.icon.html.includes("ghostnetwork-part-fallback"));
    assert.deepStrictEqual(Array.from(artMarker.options.icon.iconSize), [54, 54]);

    win.applyGhostPartDelta({
        scope: "ghostnetwork", type: "ghost.part_contained", version: 4,
        payload: { projection: {
            public_entity_id: "art-part", can_show_on_map: true,
            location_visibility: "exact", latitude: 1.2, longitude: 2.2,
            module_state: "blocked",
            visual_asset_url: "/static/images/ghostnetwork/parts/v1_ledger_nexus.png"
        } }
    });
    assert.ok(artMarker.options.icon.html.includes("transition-contained"));
    assert.strictEqual(Object.keys(win.ghostNetworkPartLayers).filter(key => key === "art-part").length, 1);

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

    const territoryA = territoryLayer();
    win.territoryAreaLayers = { "territory-a": { layer: territoryA } };
    win.applyGhostPartDelta({
        scope: "ghostnetwork", type: "ghost.part_activated", version: 5,
        payload: { projection: {
            public_entity_id: "active-part", can_show_on_map: true,
            location_visibility: "exact", latitude: 3, longitude: 4,
            territory_id: "territory-a", module_state: "active"
        } }
    });
    assert.strictEqual(territoryA._ghostNetworkStrategicState, "active");
    assert.ok(territoryA._classes.has("ghostnetwork-territory-active"));

    win.applyGhostPartDelta({
        scope: "ghostnetwork", type: "ghost.part_contained", version: 6,
        payload: { projection: {
            public_entity_id: "hostile-part", can_show_on_map: true,
            location_visibility: "exact", latitude: 5, longitude: 6,
            territory_id: "territory-a", module_state: "blocked"
        } }
    });
    assert.strictEqual(territoryA._ghostNetworkStrategicState, "hostile", "hostile must win over active");
    assert.ok(territoryA._classes.has("ghostnetwork-territory-hostile"));
    assert.ok(!territoryA._classes.has("ghostnetwork-territory-active"));

    win.removeGhostPartMarker("hostile-part");
    assert.strictEqual(territoryA._ghostNetworkStrategicState, "active", "removing hostile restores active");

    const rebuiltTerritory = territoryLayer();
    win.territoryAreaLayers = { "territory-a": { layer: rebuiltTerritory } };
    win.refreshGhostTerritoryStates();
    assert.strictEqual(rebuiltTerritory._ghostNetworkStrategicState, "active", "snapshot rebuild restores state");

    assert.strictEqual(win.applyGhostPartDelta({
        scope: "ghostnetwork", type: "ghost.part_deactivated", version: 7,
        payload: { projection: {
            public_entity_id: "active-part", can_show_on_map: true,
            location_visibility: "exact", latitude: 3, longitude: 4,
            territory_id: "territory-a", module_state: "contained"
        } }
    }), true);
    assert.strictEqual(rebuiltTerritory._ghostNetworkStrategicState, "none");
    assert.ok(!rebuiltTerritory._classes.has("ghostnetwork-territory-active"));
    assert.ok(!rebuiltTerritory._classes.has("ghostnetwork-territory-hostile"));

    console.log("ghostnetwork map renderer tests: OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
