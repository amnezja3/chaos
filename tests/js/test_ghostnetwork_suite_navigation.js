"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const terminal = fs.readFileSync("static/js/terminal.js", "utf8");
const styles = fs.readFileSync("static/css/style.css", "utf8");
const ctaPresentationStart = terminal.indexOf("function blacknetCtaPresentation");
const ctaPresentationEnd = terminal.indexOf("const renderBlackNet", ctaPresentationStart);
assert.ok(ctaPresentationStart >= 0 && ctaPresentationEnd > ctaPresentationStart);
const ctaPresentationSandbox = { Boolean, String };
vm.createContext(ctaPresentationSandbox);
vm.runInContext(terminal.slice(ctaPresentationStart, ctaPresentationEnd), ctaPresentationSandbox);
assert.deepStrictEqual(
    JSON.parse(JSON.stringify(ctaPresentationSandbox.blacknetCtaPresentation({ cta: "OTWORZ", cta_action: "" }))),
    { action: "", enabled: false, label: "READ ONLY" }
);
assert.deepStrictEqual(
    JSON.parse(JSON.stringify(ctaPresentationSandbox.blacknetCtaPresentation({ cta: "OTWORZ", cta_action: "none" }))),
    { action: "none", enabled: false, label: "READ ONLY" }
);
assert.deepStrictEqual(
    JSON.parse(JSON.stringify(ctaPresentationSandbox.blacknetCtaPresentation({ cta: "OTWORZ", cta_action: "show_ghostnetwork_part" }))),
    { action: "show_ghostnetwork_part", enabled: true, label: "OTWORZ" }
);
const actionStart = terminal.indexOf("function ghostnetworkSuiteOpaqueAction");
const actionEnd = terminal.indexOf("function openGhostNetworkSuiteMap", actionStart);
assert.ok(actionStart >= 0 && actionEnd > actionStart);
const actionSandbox = { String };
vm.createContext(actionSandbox);
vm.runInContext(terminal.slice(actionStart, actionEnd), actionSandbox);

const installGuardStart = terminal.indexOf("function ghostNetworkSuiteInstalledInProfile");
const installGuardEnd = terminal.indexOf("const blacknetOpenGhostNetworkSuite", installGuardStart);
assert.ok(installGuardStart >= 0 && installGuardEnd > installGuardStart);
const installGuardSandbox = { Array, String };
vm.createContext(installGuardSandbox);
vm.runInContext(terminal.slice(installGuardStart, installGuardEnd), installGuardSandbox);
assert.strictEqual(installGuardSandbox.ghostNetworkSuiteInstalledInProfile({ apps: [] }), false);
assert.strictEqual(installGuardSandbox.ghostNetworkSuiteInstalledInProfile({
    apps: [{ id: "ghostnetworkSuite" }],
}), true);
assert.strictEqual(installGuardSandbox.ghostNetworkSuiteInstalledInProfile({
    apps: [{ id: "different", system_launcher: "createGhostNetworkSuiteApp" }],
}), true);

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
const teleportEnd = terminal.indexOf("function renderGhostNetworkSuite", teleportStart);
const teleportSource = terminal.slice(teleportStart, teleportEnd);
const consentIndex = teleportSource.indexOf("await showGhostDecisionDialog");
const requestIndex = teleportSource.indexOf('fetch("/api/blacknet/cta/teleport"');
const openMapIndex = teleportSource.indexOf("createMap()");
assert.ok(consentIndex >= 0 && requestIndex > consentIndex && openMapIndex > requestIndex, "teleport must ask first and open map only after canonical request succeeds");
assert.match(terminal.slice(teleportStart, terminal.indexOf("async function loadGhostNetworkSuite", teleportStart)), /event\.stopPropagation|stopPropagation/);

const mapSource = fs.readFileSync("static/js/map/ghostnetwork.js", "utf8");
const focusStart = mapSource.indexOf("function sameGhostNetworkSuiteFocus");
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

const delayedCalls = [];
const delayedSandbox = {
    String, Math,
    map: {
        getZoom: () => 12,
        setView: (position, zoom) => delayedCalls.push(["setView", position, zoom]),
    },
    openGhostPartPanel: projection => delayedCalls.push(["panel", projection.public_entity_id]),
    window: {
        ghostNetworkPartLayers: {},
        ghostNetworkPartProjections: {},
        territoryAreaLayers: {},
        setTimeout: () => {},
    },
};
vm.createContext(delayedSandbox);
vm.runInContext(mapSource.slice(focusStart, focusEnd), delayedSandbox);
const delayedFocus = { target_type: "ghostnetwork_part", public_entity_id: "ghost-node:delayed" };
assert.strictEqual(delayedSandbox.focusGhostNetworkSuiteTarget(delayedFocus), false);
assert.strictEqual(delayedSandbox.window.pendingGhostNetworkSuiteFocus.public_entity_id, "ghost-node:delayed", "closed-map focus must survive a slow map boot");
delayedSandbox.window.ghostNetworkPartLayers["ghost-node:delayed"] = {
    ghostNetworkProjection: { public_entity_id: "ghost-node:delayed" },
    getLatLng: () => ({ lat: 50.06, lng: 19.94 }),
};
delayedSandbox.window.ghostNetworkPartProjections["ghost-node:delayed"] = { public_entity_id: "ghost-node:delayed" };
assert.strictEqual(delayedSandbox.applyPendingGhostNetworkSuiteFocus(), true);
assert.strictEqual(delayedSandbox.window.pendingGhostNetworkSuiteFocus, null, "pending focus must be consumed exactly once");
assert.deepStrictEqual(JSON.parse(JSON.stringify(delayedCalls[0])), ["setView", [50.06, 19.94], 17]);

const mapTemplate = fs.readFileSync("templates/map_template.html", "utf8");
const readyIndex = mapTemplate.indexOf("enableMapGameplay();");
const pendingIndex = mapTemplate.indexOf("applyPendingGhostNetworkSuiteFocus", readyIndex);
assert.ok(readyIndex >= 0 && pendingIndex > readyIndex, "map boot must replay pending Suite focus after critical scopes are ready");
const snapshotStart = mapSource.indexOf("async function loadGhostNetworkSnapshot");
const snapshotEnd = mapSource.indexOf("function extractDeltaProjection", snapshotStart);
assert.match(mapSource.slice(snapshotStart, snapshotEnd), /applyPendingGhostNetworkSuiteFocus\(\)/, "GN snapshot publication must replay pending exact-part focus");

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

const responsiveStart = styles.indexOf("@media (max-width: 900px), (max-height: 700px)", styles.indexOf(".ghostnetwork-suite-window"));
const responsiveEnd = styles.indexOf(".victim-picker-window::after", responsiveStart);
const responsiveSuite = styles.slice(responsiveStart, responsiveEnd);
assert.match(responsiveSuite, /\.ghostnetwork-suite-shell\s*\{[^}]*overflow-y:\s*auto/s, "responsive Suite must own the single vertical scroll");
assert.match(responsiveSuite, /\.ghostnetwork-suite-list\s*\{[^}]*overflow:\s*visible/s, "responsive list must not create a nested scroll");
assert.doesNotMatch(responsiveSuite, /\.ghostnetwork-suite-list\s*\{[^}]*overflow:\s*auto/s, "responsive list must not keep its desktop scroller");

console.log("ghostnetwork suite navigation tests: OK");
