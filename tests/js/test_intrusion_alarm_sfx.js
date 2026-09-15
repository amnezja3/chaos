const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const played = [];
const sandbox = {window: {GameSfx: {play: (key, payload) => played.push({key, payload})}}};
vm.createContext(sandbox);
const start = source.indexOf('function playSystemMessageSfx(');
const end = source.indexOf('\nfunction ', start + 10);
vm.runInContext(source.slice(start, end), sandbox);
for (const id of ['msg_owner_area_intrusion:1', 'msg_owner_area_intrusion:2']) {
    assert.strictEqual(sandbox.playSystemMessageSfx({message_id: id, type: 'warning'}), true);
}
assert.deepStrictEqual(played.map(item => item.key), ['system.warning', 'system.warning']);
assert.notStrictEqual(played[0].payload.event_id, played[1].payload.event_id);
assert.strictEqual(sandbox.playSystemMessageSfx({type: 'warning'}), false);
console.log('Intrusion alarm SFX bridge tests: OK');
