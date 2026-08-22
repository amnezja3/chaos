const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const template = fs.readFileSync("templates/map_template.html", "utf8");
const start = template.indexOf("function mapContextEventContainerPoint");
const end = template.indexOf("function showMapMenuFromLeafletContextEvent", start);

assert(start >= 0, "map target hitbox helpers missing");
assert(end > start, "map target hitbox helper boundary missing");

const sandbox = {
    map: {
        mouseEventToContainerPoint(event) {
            return { x: Number(event.clientX), y: Number(event.clientY) };
        },
        latLngToContainerPoint(latlng) {
            return { x: Number(latlng[1]), y: Number(latlng[0]) };
        }
    }
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
