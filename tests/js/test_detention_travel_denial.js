'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
function section(start, end) {
    const a = source.indexOf(start), b = source.indexOf(end, a);
    assert(a >= 0 && b > a);
    return source.slice(a, b);
}
async function main() {
    const timers = [], messages = [], cleaned = [];
    let position;
    const state = {queue: [{lat: 1, lng: 2}], pendingBackendTravelCommit: {},
        pendingRouteWaypoints: [{}], travelPulseCleanupById: {one: true}};
    const marker = {setLatLng: value => {position = value;}};
    const context = {window: {motorcycleTravelState: state,
        setMotorcyclePositionFromSnapshot: p => {position = [p.lat, p.lng];}},
        finishMotorcycleTravelPulse: id => cleaned.push(id), hideMotorcycleTravelPhone: () => {},
        addSystemMessage: (...args) => messages.push(args), getBikeDirection: () => 'right',
        renderMotorcycleMarkerVisual: () => {}, setTimeout: fn => timers.push(fn)};
    vm.createContext(context);
    vm.runInContext(section('function handleDetentionTravelDenial', 'async function flushMotorcycleTravelCommit'), context);
    vm.runInContext(section('async function animateAvatarTravel', 'window.motorcycleTravelState ='), context);
    assert.strictEqual(context.handleDetentionTravelDenial({reason: 'unrelated'}), false);
    const animation = context.animateAvatarTravel(marker, {lat: 0, lng: 0}, {lat: 50, lng: 20});
    assert(timers.length > 0);
    context.handleDetentionTravelDenial({reason: 'detention_movement_blocked', remaining_seconds: 300,
        current_position: {lat: 52, lng: 21}});
    timers.shift()();
    await animation;
    assert.deepStrictEqual(position, [52, 21], 'old animation cannot overwrite authoritative rollback');
    assert.strictEqual(state.queue.length, 0);
    assert.strictEqual(state.pendingBackendTravelCommit, null);
    assert.strictEqual(state.pendingRouteWaypoints.length, 0);
    assert.deepStrictEqual(cleaned, ['one']);
    assert.strictEqual(messages.length, 1);
    assert(messages[0][2].includes('5 min online'));
    console.log('detention travel denial: OK');
}
main().catch(error => {console.error(error); process.exitCode = 1;});
