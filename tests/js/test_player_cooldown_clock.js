const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
let now = Date.parse('2026-09-16T10:00:00Z');
const node = {dataset: {playerCooldownDeadline: now + 65000}, textContent: ''};
const ctx = {window: {}, Date: {now: () => now, parse: Date.parse},
    document: {querySelectorAll: () => [node]}};
vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('window.playerCooldownDeadline ='), source.indexOf('window.buildPlayerActorIcon =')), ctx);
assert.equal(ctx.window.playerCooldownDeadline('2026-09-16T10:00:00'), now);
ctx.window.updatePlayerCooldownClocks();
assert.equal(node.textContent, 'CD 0:01:05');
now += 70000;
ctx.window.updatePlayerCooldownClocks();
assert(node.hidden);
assert.equal(ctx.window.playerCooldownText(NaN), '');
assert(source.includes('scheduleSnapshot(window.updatePlayerCooldownClocks, 1000)'));
console.log('PvP cooldown clock: PASS');
