'use strict';
const assert = require('assert'), fs = require('fs'), vm = require('vm');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
const a = source.indexOf('window.applyMapPlayerActorDelta = function(event)'),
    b = source.indexOf('window.renderPlayerActors =', a);
assert(a > 0 && b > a);
let focus = 0, moves = 0;
const state = {queue: [{}], pendingBackendTravelCommit: {}, pendingRouteWaypoints: [{}],
    lastConfirmedVersion: 4, travelPulseCleanupById: {}};
const window = {profileData: {username: 'alice'}, playerActorChangeSerial: 0,
    motorcycleTravelState: state, focusMapOnMotorcycle: () => {focus++;},
    setMotorcyclePositionFromSnapshot: point => {moves++; state.lastConfirmedVersion = point.position_version; return true;}};
const context = {window, finishMotorcycleTravelPulse() {}, hideMotorcycleTravelPhone() {}};
vm.createContext(context);
vm.runInContext(source.slice(a, b), context);
const event = (version, reason='detention_imposed', username='alice') => ({type: 'map.player_forced_position',
    payload: {username, reason, position_version: version, lat: 38, lng: -105}});
assert(window.applyMapPlayerActorDelta(event(5)));
assert.strictEqual(state.queue.length, 0);
assert.strictEqual(state.pendingBackendTravelCommit, null);
assert.strictEqual(focus, 1);
state.queue.push({});
assert.strictEqual(window.applyMapPlayerActorDelta(event(5)), false);
assert.strictEqual(window.applyMapPlayerActorDelta(event(4)), false);
assert.strictEqual(state.queue.length, 1, 'replayed transport must not cancel a newer local action');
assert.strictEqual(window.applyMapPlayerActorDelta(event(6, 'detention_imposed', 'bob')), false);
assert(window.applyMapPlayerActorDelta(event(6, 'detention_release')));
assert.strictEqual(state.queue.length, 0);
assert.strictEqual(moves, 2);
assert.strictEqual(focus, 2);
console.log('detention transport: OK');
