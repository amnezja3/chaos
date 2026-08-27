"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const terminal = fs.readFileSync("static/js/terminal.js", "utf8");
const actionStart = terminal.indexOf("function ghostnetworkSuiteOpaqueAction");
const actionEnd = terminal.indexOf("function openGhostNetworkSuiteMap", actionStart);
assert.ok(actionStart >= 0 && actionEnd > actionStart);
const actionSandbox = { String };
vm.createContext(actionSandbox);
vm.runInContext(terminal.slice(actionStart, actionEnd), actionSandbox);

const exact = actionSandbox.ghostnetworkSuiteOpaqueAction({ actions: {
    map_target_type: "ghostnetwork_part", map_target_id: "ghost-node:opaque",
    teleport_target_type: "ghostnetwork_part", teleport_target_id: "ghost-node:opaque",
}}, "teleport");
assert.strictEqual(exact.public_entity_id, "ghost-node:opaque");
assert.strictEqual(exact.territory_id, undefined);
assert.strictEqual("lat" in exact, false);
assert.strictEqual("lng" in exact, false);

const hidden = actionSandbox.ghostnetworkSuiteOpaqueAction({ actions: {
    map_target_type: "ghostnetwork_territory", map_target_id: "territory:opaque",
}}, "map");
assert.strictEqual(hidden.territory_id, "territory:opaque");
assert.strictEqual(hidden.public_entity_id, undefined);
const loaderStart = terminal.indexOf("async function loadGhostNetworkSuite");
const loaderEnd = terminal.indexOf("function createGhostNetworkSuiteApp", loaderStart);
assert.doesNotMatch(terminal.slice(loaderStart, loaderEnd), /createMap\s*\(/, "snapshot load must not open map");
const mapActionStart = terminal.indexOf("function openGhostNetworkSuiteMap");
const teleportStart = terminal.indexOf("async function teleportGhostNetworkSuitePart", mapActionStart);
assert.match(terminal.slice(mapActionStart, teleportStart), /createMap\s*\(/, "explicit map action opens map");
assert.doesNotMatch(terminal.slice(actionStart, teleportStart), /aimed_target|mark_target/, "navigation must not mutate target state");

const mapSource = fs.readFileSync("static/js/map/ghostnetwork.js", "utf8");
const focusStart = mapSource.indexOf("function focusGhostNetworkSuiteTarget");
const focusEnd = mapSource.indexOf("function connectionKey", focusStart);
assert.ok(focusStart >= 0 && focusEnd > focusStart);
const calls = [];
const marker = {
    ghostNetworkProjection: { public_entity_id: "ghost-node:opaque" },
    getLatLng: () => ({ lat: 52.2, lng: 21.1 }),
};
const bounds = { isValid: () => true };
const territoryLayer = { getBounds: () => bounds, openTooltip: () => calls.push("tooltip") };
const mapSandbox = {
    String, Math,
    map: {
        getZoom: () => 12,
        setView: (position, zoom) => calls.push(["setView", position, zoom]),
        fitBounds: (value, options) => calls.push(["fitBounds", value, options]),
    },
    openGhostPartPanel: projection => calls.push(["panel", projection.public_entity_id]),
    window: {
        ghostNetworkPartLayers: { "ghost-node:opaque": marker },
        ghostNetworkPartProjections: { "ghost-node:opaque": marker.ghostNetworkProjection },
        territoryAreaLayers: { "territory:opaque": { layer: territoryLayer } },
        setTimeout: callback => callback(),
    },
};
vm.createContext(mapSandbox);
vm.runInContext(mapSource.slice(focusStart, focusEnd), mapSandbox);
assert.strictEqual(mapSandbox.focusGhostNetworkSuiteTarget({ target_type: "ghostnetwork_part", public_entity_id: "ghost-node:opaque" }), true);
assert.deepStrictEqual(JSON.parse(JSON.stringify(calls[0])), ["setView", [52.2, 21.1], 17]);
assert.deepStrictEqual(JSON.parse(JSON.stringify(calls[1])), ["panel", "ghost-node:opaque"]);
calls.length = 0;
assert.strictEqual(mapSandbox.focusGhostNetworkSuiteTarget({ target_type: "ghostnetwork_territory", territory_id: "territory:opaque" }), true);
assert.strictEqual(calls[0][0], "fitBounds");
assert.strictEqual(calls[1], "tooltip");

const territoryStart = terminal.indexOf("function territoryControlGhostBadge");
const territoryEnd = terminal.indexOf("function territoryControlThreatSummary", territoryStart);
assert.ok(territoryStart >= 0 && territoryEnd > territoryStart);
const territorySandbox = {
    escapeHTML: value => String(value == null ? "" : value),
    TERRITORY_CONTROL_ICONS: { app: "◇" },
    Array, Number, String,
};
vm.createContext(territorySandbox);
vm.runInContext(terminal.slice(territoryStart, territoryEnd), territorySandbox);
assert.strictEqual(territorySandbox.territoryControlGhostBadge({ contains_ghost_part: false }), "");
const hiddenDetails = territorySandbox.renderTerritoryControlGhostDetails({
    contains_ghost_part: true,
    ghost_part_count: 1,
    ghost_part_summary: "TERYTORIUM ZAWIERA CZESC GHOSTNETWORK",
    parts: [{ identity_visible: false, display_label: "NIEZIDENTYFIKOWANY KOMPONENT", module_state: "blocked", machine_code: "SECRET-MACHINE" }],
});
assert.match(hiddenDetails, /NIEZIDENTYFIKOWANY KOMPONENT/);
assert.doesNotMatch(hiddenDetails, /SECRET-MACHINE/);
assert.match(territorySandbox.territoryControlGhostBadge({
    contains_ghost_part: true, ghost_part_relation: "self_own_active", ghost_part_state: "active",
}), /CZESC WLASNEGO KLANU/);

console.log("ghostnetwork suite navigation tests: OK");
