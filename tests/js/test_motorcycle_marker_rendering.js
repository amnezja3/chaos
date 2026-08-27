"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("templates/map_template.html", "utf8");
const start = source.indexOf("const bikeDirectionIcons =");
const end = source.indexOf("async function animateAvatarTravel", start);
assert.ok(start >= 0 && end > start, "motorcycle renderer source must exist");

const image = {
    dataset: { bikeDirection: "right" },
    src: "/static/icons/racing_bike_right.png",
};
const toggles = [];
const shell = {
    classList: { toggle: (name, enabled) => toggles.push([name, enabled]) },
    querySelector: selector => selector === ".motorcycle-avatar-bike" ? image : null,
};
const iconElement = {
    querySelector: selector => selector === ".motorcycle-avatar-shell" ? shell : null,
};
let iconReplacements = 0;
const marker = {
    getElement: () => iconElement,
    getLatLng: () => ({ lat: 52, lng: 21 }),
    setIcon: () => { iconReplacements += 1; },
};

class FakeImage {
    constructor() { this.decoding = ""; this.src = ""; }
}

const sandbox = {
    Image: FakeImage,
    Object, String, Math, Boolean,
    L: { divIcon: options => options },
    window: {
        avatarMarkerRef: marker,
        avatarBikeDirection: "right",
        motorcycleTravelState: { travelPhoneVisible: false },
        profileData: { nick: "RIN.BASS" },
        escapeMapText: value => String(value),
    },
};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);

assert.strictEqual(sandbox.renderMotorcycleMarkerVisual("up_left"), true);
assert.strictEqual(image.dataset.bikeDirection, "up_left");
assert.match(image.src, /racing_bike_up_left\.png$/);
assert.strictEqual(iconReplacements, 0, "direction change must preserve the existing Leaflet icon DOM");

sandbox.window.motorcycleTravelState.travelPhoneVisible = true;
assert.strictEqual(sandbox.renderMotorcycleMarkerVisual("up_left"), true);
assert.deepStrictEqual(toggles[toggles.length - 1], ["is-travel-waiting", true]);
assert.strictEqual(iconReplacements, 0, "phone state change must not replace the marker DOM");

marker.getElement = () => null;
assert.strictEqual(sandbox.renderMotorcycleMarkerVisual("down"), true);
assert.strictEqual(iconReplacements, 1, "missing Leaflet DOM may be repaired with one canonical icon mount");

const movementStart = source.indexOf("function updateAvatarDirection");
const movementEnd = source.indexOf("function addLiveMarker", movementStart);
const movementSource = source.slice(movementStart, movementEnd);
assert.doesNotMatch(movementSource, /marker\.setIcon\(buildBikeIcon/, "movement and activity paths must not churn the Leaflet icon DOM");

console.log("motorcycle marker rendering tests: OK");
