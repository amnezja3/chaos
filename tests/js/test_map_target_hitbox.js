const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const template = fs.readFileSync("templates/map_template.html", "utf8");
const start = template.indexOf("function mapContextEventContainerPoint");
const end = template.indexOf("function showMapMenuFromLeafletContextEvent", start);

assert(start >= 0, "map target hitbox helpers missing");
assert(end > start, "map target hitbox helper boundary missing");

const mapContainer = {
    addEventListener(type, handler, capture) {
        if (type === "contextmenu" && capture === true) this.contextHandler = handler;
    }
};
let delegatedTarget = null;
const sandbox = {
    document: {
        querySelectorAll() { return []; }
    },
    normalizeMapMenuTarget(target) {
        return Object.freeze({ ...(target || {}) });
    },
    consumeMapContextEvent(event) {
        if (event.preventDefault) event.preventDefault();
    },
    map: {
        getContainer() {
            return mapContainer;
        },
        mouseEventToContainerPoint(event) {
            return { x: Number(event.clientX), y: Number(event.clientY) };
        },
        latLngToContainerPoint(latlng) {
            return { x: Number(latlng[1]), y: Number(latlng[0]) };
        }
    },
    showMarkerContextMenu(x, y, target) { delegatedTarget = target; },
    showVulnerabilityReporterMenu() {},
    showHackingMenuForMarker() {},
    L: { DomEvent: { stop() {} } }
};
vm.createContext(sandbox);
vm.runInContext(template.slice(start, end), sandbox);

const marker = {
    options: {
        icon: { options: { iconSize: [32, 42], iconAnchor: [16, 42] } }
    },
    getLatLng() {
        return { lat: 100, lng: 100 };
    }
};

assert.strictEqual(
    sandbox.isContextEventInsideMarkerHitbox(marker, { containerPoint: { x: 100, y: 80 } }),
    true,
    "direct marker hit must keep the marker menu"
);
assert.strictEqual(
    sandbox.isContextEventInsideMarkerHitbox(marker, { containerPoint: { x: 220, y: 80 } }),
    false,
    "an event captured far outside the icon must fall through to the map menu"
);

const markerA = { getElement() { return this.icon; }, icon: {} };
const markerB = { getElement() { return this.icon; }, icon: {} };
const targetA = { lat: 52.1, lng: 21.1, label: "Zabka" };
const targetB = { lat: 50.0, lng: 19.0, label: "Topaz" };
sandbox.bindMarkerContextSnapshot(markerA, targetA, "scanTargetMarker");
sandbox.bindMarkerContextSnapshot(markerB, targetB, "scanTargetMarker");
const childOfA = { parentNode: markerA.icon };
const resolved = sandbox.resolveMarkerContextBinding(
    markerB,
    { originalEvent: { target: childOfA } },
    targetB,
    "scanTargetMarker"
);
assert.strictEqual(resolved.target.label, "Zabka", "clicked DOM marker must own the menu snapshot");
assert.strictEqual(resolved.marker, markerA, "clicked DOM marker must win over a stale Leaflet callback");
assert.strictEqual(typeof mapContainer.contextHandler, "function", "capture-phase delegation must be installed");
mapContainer.contextHandler({
    target: childOfA,
    clientX: 100,
    clientY: 80,
    preventDefault() {},
    stopPropagation() {},
    stopImmediatePropagation() {}
});
assert.strictEqual(delegatedTarget.label, "Zabka", "delegated menu must resolve before Leaflet layer routing");
assert.strictEqual(
    sandbox.isContextEventInsideProjectedMarkerHitbox(
        { containerPoint: { x: 220, y: 80 } },
        100,
        100,
        [10000, 10000],
        [5000, 5000]
    ),
    false,
    "oversized DOM/icon dimensions must be clamped"
);

console.log("map target hitbox tests passed");

// Marked cameras must keep the same DOM-owned dispatch as raw scan markers.
Object.assign(sandbox, {
    mapTargetDisplayLabel: obj => obj.label,
    removeScanResultAt() {}, hideDomTargetMarkers() {}, registerTargetMarker() {},
    isMissingTargetDisplayName: value => !value,
    rememberTargetLayer: (lat, lng, label, marker) => marker,
    showHackingMenuForMarker: (x, y, target) => { delegatedTarget = target; },
});
sandbox.L.divIcon = options => ({options});
sandbox.L.marker = (position, options) => ({
    options, icon: {}, handlers: {},
    getElement() { return this.icon; },
    addTo() { return this; }, bindTooltip() { return this; },
    on(name, callback) { this.handlers[name] = callback; return this; },
});
const interactiveStart = template.indexOf('function addInteractiveTargetMarker(');
const interactiveEnd = template.indexOf('function renderCurrentAimedTargetMarker()', interactiveStart);
vm.runInContext(template.slice(interactiveStart, interactiveEnd), sandbox);
const cameraA = sandbox.addInteractiveTargetMarker(52, 21, 'Camera A', 'C', {camera_id: 'A', scan_id: 'scan'});
const cameraB = sandbox.addInteractiveTargetMarker(53, 22, 'Camera B', 'C', {camera_id: 'B', scan_id: 'scan'});
cameraB.handlers.contextmenu({originalEvent: {target: {parentNode: cameraA.icon}, clientX: 100, clientY: 80}});
assert.strictEqual(delegatedTarget.camera_id, 'A');
cameraA.icon = {};
cameraA.handlers.add();
mapContainer.contextHandler({target: {parentNode: cameraA.icon}, clientX: 100, clientY: 80});
assert.strictEqual(delegatedTarget.camera_id, 'A');
assert.strictEqual(delegatedTarget.scan_id, 'scan');
console.log('marked camera DOM dispatch and icon recreation: PASS');
