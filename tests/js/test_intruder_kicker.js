const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const map = fs.readFileSync('templates/map_template.html', 'utf8');
let app;
let point;
const context = {
    document: { createElement() { return app = {style: {}, querySelector: () => ({addEventListener() {}})}; }, body: {appendChild() {}} },
    makeDraggable() {}, escapeHTML: value => String(value).replace(/</g, '&lt;'),
    window: {profileData: {username: 'victim'}, setMotorcyclePositionFromSnapshot(value, options) {point = value; assert.strictEqual(options.authoritative, true); return true;}}
};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function openIntruderKickerApp('), source.indexOf('async function usePlayerHackTool(')), context);
context.openIntruderKickerApp({message: '<script>wyrzucono'});
assert.ok(app.innerHTML.includes('&lt;script>wyrzucono'));
const start = map.indexOf('window.applyMapPlayerActorDelta = function');
vm.runInContext(map.slice(start, map.indexOf('window.renderPlayerActors', start)), context);
assert.strictEqual(context.window.applyMapPlayerActorDelta({type: 'map.player_forced_position', payload: {username: 'other', lat: 1, lng: 2}}), false);
assert.strictEqual(point, undefined);
assert.strictEqual(context.window.applyMapPlayerActorDelta({type: 'map.player_forced_position', payload: {username: 'victim', lat: 1, lng: 2, position_version: 4}}), true);
assert.strictEqual(point.position_version, 4);
assert.strictEqual(point.source, 'intruderKicker');
console.log('Intruder Kicker UI tests: OK');
