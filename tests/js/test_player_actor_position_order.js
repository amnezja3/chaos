const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
let deltaDuringResponse = true;
let renders = 0;
const sandbox = {
    window: {beginMapLoading() {}, endMapLoading() {}, renderPlayerActors() {renders++;}},
    performance: {now: () => 0}, console: {info() {}, warn() {}},
    AbortController, setTimeout: () => 1, clearTimeout() {},
    invalidateMapAfterLayerUpdate() {}, stopMapRefreshTimers() {},
    async fetch() {return {ok: true, status: 200, async json() {
        if (deltaDuringResponse) sandbox.window.playerActorChangeSerial++;
        return {player_actors: [{username: 'intruder', position_version: 1}]};
    }};}
};
vm.createContext(sandbox);
let a = source.indexOf('window.playerActorPositionVersions =');
let b = source.indexOf('window.upsertPlayerActorMarker =', a);
vm.runInContext(source.slice(a, b), sandbox);
assert.ok(sandbox.window.acceptPlayerActorPositionVersion('intruder', 4));
assert.strictEqual(sandbox.window.acceptPlayerActorPositionVersion('intruder', 3), false);
assert.strictEqual(sandbox.window.acceptPlayerActorPositionVersion('intruder', undefined), false);
assert.ok(sandbox.window.acceptPlayerActorPositionVersion('intruder', 5));
a = source.indexOf('window.refreshPlayerActors = async function');
b = source.indexOf('window.refreshFriendMarkers =', a);
vm.runInContext(source.slice(a, b), sandbox);
(async () => {
    assert.strictEqual(await sandbox.window.refreshPlayerActors(), false);
    assert.strictEqual(renders, 0, 'snapshot started before a removal delta must not resurrect the actor');
    deltaDuringResponse = false;
    assert.strictEqual(await sandbox.window.refreshPlayerActors(), true);
    assert.strictEqual(renders, 1, 'a subsequent snapshot can recover current visibility');
    console.log('Player actor position ordering tests: OK');
})().catch(error => {console.error(error); process.exitCode = 1;});
