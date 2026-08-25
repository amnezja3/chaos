const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

function marker(coords, options) {
    return {
        coords, options, popupOpened: false,
        addTo() { return this; },
        setLatLng(next) { this.coords = next; return this; },
        setIcon(next) { this.options.icon = next; return this; },
        on() { return this; },
        off() { return this; },
        bindPopup() { return this; },
        openPopup() { this.popupOpened = true; return this; },
        getLatLng() { return { lat: this.coords[0], lng: this.coords[1] }; }
    };
}

const panes = {};
let mobileMode = false;
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
    handlers: {},
    createPane(name) { return (panes[name] = { style: {} }); },
    getPane(name) { return panes[name] || null; },
    on(name, handler) { this.handlers[name] = handler; return this; },
    latLngToContainerPoint(latLng) { return { x: latLng.lng, y: latLng.lat }; },
    removeLayer() {}
};
const sandbox = {
    console: { warn() {} },
    Set, Promise,
    window: {
        chaosMap: map,
        matchMedia() { return { matches: mobileMode }; },
        addEventListener() {}
    },
    L: {
        divIcon(options) { return options; },
        marker,
        canvas(options) { return { options }; },
        polyline(points, options) { return { points, options, addTo() { return this; } }; },
        layerGroup(layers) { return { layers, addTo() { return this; } }; }
    }
};
sandbox.window.window = sandbox.window;
sandbox.window.L = sandbox.L;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync("static/js/ghostnetwork_delta_client.js", "utf8"), sandbox);
vm.runInContext(fs.readFileSync("static/js/map/ghostnetwork.js", "utf8"), sandbox);

function testLeafletPolylineBoundsGuard() {
    const template = fs.readFileSync("templates/map_template.html", "utf8");
    const start = template.indexOf("function hasFiniteLeafletBounds(bounds)");
    const end = template.indexOf("function registerLayerInArray", start);
    assert.ok(start >= 0 && end > start, "polyline bounds guard source must exist");

    let delegated = 0;
    let clipBehavior = function renderNormally() {
        delegated += 1;
        this._parts = ["rendered"];
    };
    const prototype = {
        _clipPoints() {
            return clipBehavior.call(this);
        }
    };
    const guardSandbox = {
        Number,
        window: {},
        L: { Polyline: { prototype } }
    };
    guardSandbox.window.L = guardSandbox.L;
    vm.createContext(guardSandbox);
    vm.runInContext(`${template.slice(start, end)}\ninstallLeafletPolylineBoundsGuard();`, guardSandbox);

    const validBounds = { min: { x: 0, y: 0 }, max: { x: 10, y: 10 } };
    const line = Object.create(prototype);
    line._map = {};
    line._renderer = { _bounds: undefined };
    line._pxBounds = validBounds;
    line._parts = ["stale"];
    assert.doesNotThrow(() => line._clipPoints());
    assert.strictEqual(line._parts.length, 0);
    assert.strictEqual(delegated, 0, "invalid renderer frame must not reach Leaflet clipping");

    line._renderer._bounds = validBounds;
    line._clipPoints();
    assert.strictEqual(delegated, 1, "valid subsequent frame must use Leaflet clipping");
    assert.strictEqual(line._parts.length, 1);
    assert.strictEqual(line._parts[0], "rendered");

    clipBehavior = function transientRace() {
        this._renderer._bounds = undefined;
        throw new TypeError("Cannot read properties of undefined (reading 'x')");
    };
    const racingLine = Object.create(prototype);
    racingLine._map = {};
    racingLine._renderer = { _bounds: validBounds };
    racingLine._pxBounds = validBounds;
    racingLine._parts = ["stale"];
    assert.doesNotThrow(() => racingLine._clipPoints());
    assert.deepStrictEqual(Array.from(racingLine._parts), []);

    clipBehavior = function unrelatedFailure() {
        throw new Error("unrelated renderer defect");
    };
    const unrelatedLine = Object.create(prototype);
    unrelatedLine._map = {};
    unrelatedLine._renderer = { _bounds: validBounds };
    unrelatedLine._pxBounds = validBounds;
    assert.throws(() => unrelatedLine._clipPoints(), /unrelated renderer defect/);
}

testLeafletPolylineBoundsGuard();

async function testOptionalBootRetriesFalseResult() {
    const template = fs.readFileSync("templates/map_template.html", "utf8");
    const start = template.indexOf("window.bootStep = async function");
    const end = template.indexOf("window.startMapSnapshotRefreshTimers", start);
    assert.ok(start >= 0 && end > start, "map boot step source must exist");

    const bootWindow = { mapBootState: { loadedScopes: new Set(), failed: false } };
    const bootSandbox = {
        window: bootWindow,
        Set,
        Math,
        console: { warn() {} },
        setInterval,
        clearInterval,
        normalizeBootLoadedScopes() { return bootWindow.mapBootState.loadedScopes; },
        updateMapBootOverlay() {},
        waitForMapBootPaint: async () => {},
        waitForMapBootRetry: async () => {}
    };
    vm.createContext(bootSandbox);
    vm.runInContext(template.slice(start, end), bootSandbox);

    let attempts = 0;
    const recovered = await bootWindow.bootStep("GhostNetwork", "ghostnetwork", async () => {
        attempts += 1;
        return attempts >= 3;
    }, { silent: true, retries: 2 });
    assert.strictEqual(recovered, true);
    assert.strictEqual(attempts, 3, "optional GN boot must retry a false snapshot result");
    assert.ok(bootWindow.mapBootState.loadedScopes.has("ghostnetwork"));

    bootWindow.mapBootState.loadedScopes.delete("ghostnetwork");
    attempts = 0;
    const failed = await bootWindow.bootStep("GhostNetwork", "ghostnetwork", async () => {
        attempts += 1;
        return false;
    }, { silent: true, retries: 1 });
    assert.strictEqual(failed, false);
    assert.strictEqual(attempts, 2);
    assert.ok(!bootWindow.mapBootState.loadedScopes.has("ghostnetwork"), "failed scope must not be marked loaded");
}

function response(payload) {
    return { ok: true, json: async () => payload };
}

(async () => {
    await testOptionalBootRetriesFalseResult();
    const win = sandbox.window;
    win.fetchMapSnapshot = async () => ({ res: response({
        ok: true,
        cycle: { cycle_id: "cycle-1", state_version: 2 },
        parts: [{ public_entity_id: "part-1", can_show_on_map: true, location_visibility: "exact", latitude: 1, longitude: 2 }],
        connections: []
    }) });
    assert.strictEqual(await win.loadGhostNetworkSnapshot(), true);
    assert.ok(win.ghostNetworkPartLayers["part-1"]);

    const activeConnection = win.createGhostConnectionLayer({
        public_connection_id: "connection-1",
        can_show_on_map: true,
        state: "active",
        endpoint_a: { latitude: 50.0, longitude: 20.0 },
        endpoint_b: { latitude: 50.4, longitude: 20.5 }
    });
    assert.ok(activeConnection);
    assert.strictEqual(activeConnection.layers.length, 3);
    activeConnection.layers.forEach(layer => {
        assert.strictEqual(layer.options.noClip, true, "GN connection must bypass Leaflet bounds clipping");
        assert.strictEqual(layer.points.length, 9, "active GN curve must use the lightweight point budget");
    });

    for (const viewer of ["owner", "same-clan", "foreign-clan", "neutral"]) {
        const viewerLayer = win.createGhostConnectionLayer({
            public_connection_id: "globally-public-active-connection",
            can_show_on_map: true,
            state: "active",
            viewer_relation: viewer,
            endpoint_a: { location_visibility: "exact", latitude: 50.0, longitude: 20.0 },
            endpoint_b: { location_visibility: "exact", latitude: 50.4, longitude: 20.5 }
        });
        assert.ok(viewerLayer, `${viewer} must render the public active connection`);
        assert.strictEqual(viewerLayer.layers.length, 3);
    }

    win.fetchMapSnapshot = async () => ({ res: response({
        ok: true,
        cycle: { cycle_id: "cycle-1", state_version: 3 },
        parts: [
            { public_entity_id: "part-1", can_show_on_map: true, location_visibility: "exact", latitude: 1, longitude: 2 },
            { public_entity_id: "part-2", can_show_on_map: true, location_visibility: "exact", latitude: 3, longitude: 4 }
        ],
        connections: [{
            public_connection_id: "connection-after-activation",
            can_show_on_map: true,
            state: "active",
            endpoint_a: { latitude: 1, longitude: 2 },
            endpoint_b: { latitude: 3, longitude: 4 }
        }]
    }) });
    assert.strictEqual(win.applyGhostNetworkDelta({
        scope: "ghostnetwork", type: "ghost.part_activated", version: 3,
        dedupe_key: "activation-recovery-3",
        payload: {
            cycle_id: "cycle-1", state_version: 3,
            part_projection: {
                public_entity_id: "part-2", can_show_on_map: true,
                location_visibility: "exact", latitude: 3, longitude: 4,
                module_state: "active"
            }
        }
    }), true);
    await new Promise(resolve => setImmediate(resolve));
    assert.ok(
        win.ghostNetworkConnectionLayers["connection-after-activation"],
        "part activation delta must recover the canonical active connection snapshot"
    );

    assert.strictEqual(win.updateGhostConnectionLayer({
        public_connection_id: "atomic-connection",
        can_show_on_map: true,
        state: "active",
        endpoint_a: { latitude: 50.0, longitude: 20.0 },
        endpoint_b: { latitude: 50.4, longitude: 20.5 }
    }), true);
    const previousAtomicLayer = win.ghostNetworkConnectionLayers["atomic-connection"];
    const originalLayerGroup = sandbox.L.layerGroup;
    sandbox.L.layerGroup = layers => ({
        layers,
        addTo() { throw new TypeError("renderer candidate failed"); }
    });
    assert.strictEqual(win.updateGhostConnectionLayer({
        public_connection_id: "atomic-connection",
        can_show_on_map: true,
        state: "active",
        endpoint_a: { latitude: 51.0, longitude: 21.0 },
        endpoint_b: { latitude: 51.4, longitude: 21.5 }
    }), false);
    assert.strictEqual(
        win.ghostNetworkConnectionLayers["atomic-connection"],
        previousAtomicLayer,
        "failed candidate must retain the previous valid connection layer"
    );
    sandbox.L.layerGroup = originalLayerGroup;

    mobileMode = true;
    const mobileConnection = win.createGhostConnectionLayer({
        public_connection_id: "connection-mobile",
        can_show_on_map: true,
        state: "active",
        endpoint_a: { latitude: 50.0, longitude: 20.0 },
        endpoint_b: { latitude: 50.4, longitude: 20.5 }
    });
    assert.ok(mobileConnection);
    assert.strictEqual(mobileConnection.layers, undefined, "mobile connection must use one canvas path, not an SVG group");
    assert.ok(mobileConnection.options.renderer, "mobile connection must use the shared canvas renderer");
    assert.strictEqual(mobileConnection.options.noClip, true);
    mobileMode = false;

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

    win.applyGhostPartDelta({
        scope: "ghostnetwork", type: "ghost.part_activated", version: 5,
        payload: { projection: {
            public_entity_id: "classified-active", can_show_on_map: true,
            location_visibility: "exact", latitude: 1.4, longitude: 2.4,
            module_state: "active", identity_visible: false,
            marker_asset_url: "/static/images/ghostnetwork/parts/classified_part.png"
        } }
    });
    const classifiedMarker = win.ghostNetworkPartLayers["classified-active"];
    assert.ok(classifiedMarker.options.icon.html.includes("classified_part.png"));
    assert.ok(classifiedMarker.options.icon.html.includes("is-active"));

    win.renderGhostTerritoryBadge({
        public_entity_id: "classified-blocked", can_show_on_map: true,
        location_visibility: "territory_only", territory_id: "classified-territory",
        territory_latitude: 5, territory_longitude: 6, module_state: "blocked",
        identity_visible: false, marker_asset_url: "/static/images/ghostnetwork/parts/classified_part.png"
    });
    const classifiedBadge = win.ghostNetworkTerritoryLayers["classified-blocked"];
    assert.ok(classifiedBadge.options.icon.html.includes("classified_part.png"));
    assert.ok(classifiedBadge.options.icon.html.includes("is-blocked"));
    assert.deepStrictEqual(Array.from(classifiedBadge.options.icon.iconSize), [38, 38]);

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

    mobileMode = true;
    win.applyGhostPartDelta({
        scope: "ghostnetwork", type: "ghost.part_discovered", version: 8,
        payload: { projection: {
            public_entity_id: "mobile-part", can_show_on_map: true,
            location_visibility: "exact", latitude: 70, longitude: 100,
            module_state: "neutral"
        } }
    });
    const mobileMarker = win.ghostNetworkPartLayers["mobile-part"];
    assert.strictEqual(mobileMarker.options.interactive, false, "part marker must not capture map gestures");
    assert.strictEqual(typeof map.handlers.click, "function", "mobile tap bridge must be bound once");
    map.handlers.click({ containerPoint: { x: 100, y: 70 } });
    assert.strictEqual(mobileMarker.popupOpened, true, "short map tap over a part must still open its panel");
    mobileMarker.popupOpened = false;
    map.handlers.click({ latlng: { lat: 70, lng: 100 } });
    assert.strictEqual(mobileMarker.popupOpened, true, "tap bridge must recover a missing containerPoint from latlng");
    assert.doesNotThrow(() => map.handlers.click({}), "incomplete Leaflet click event must be ignored safely");

    console.log("ghostnetwork map renderer tests: OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
