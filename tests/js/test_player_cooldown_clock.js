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
ctx.L = {divIcon: options => options};
ctx.window.escapeMapText = value => value;
ctx.window.normalizeMapAvatarUrl = value => value;
vm.runInContext(source.slice(source.indexOf('window.buildPlayerActorIcon ='), source.indexOf('window.clearPlayerActorMarkerTooltip =')), ctx);
const icon = ctx.window.buildPlayerActorIcon({username: 'victim', target_status: 'aimed',
    player_hack_cooldown_until: '2026-09-16T12:00:00'});
assert(icon.html.includes('CD 1:58:50'));
assert(icon.html.indexOf('player-actor-cooldown') < icon.html.indexOf('player-actor-marker-hitbox'),
    'Clock must be outside the clipped clickable hitbox');
assert.deepEqual(Array.from(icon.iconSize), [68, 76]);
const rootCss = source.match(/\.player-actor-marker-root\s*\{([^}]+)\}/)[1];
assert(rootCss.includes('overflow: visible !important'));
assert(rootCss.includes('pointer-events: none !important'));
const expired = ctx.window.buildPlayerActorIcon({username: 'victim',
    player_hack_cooldown_until: '2026-09-16T09:00:00'});
assert(!expired.html.includes('data-player-cooldown-deadline'));
console.log('PvP cooldown clock: PASS');
const terminal = fs.readFileSync('static/js/terminal.js', 'utf8');
let mapRefreshes = 0;
const accessCtx = {playerHackAccessState: null,
    renderPlayerHackAccessPanel(access) { accessCtx.playerHackAccessState = access; },
    recoverMapDeltaScope() { mapRefreshes++; }};
vm.createContext(accessCtx);
vm.runInContext(terminal.slice(terminal.indexOf('async function refreshPlayerHackAccess('),
    terminal.indexOf('function openIntruderKickerApp(')), accessCtx);
const grant = {active: true, victim_username: 'victim', hacked_until: '2026-09-16T10:05:00'};
accessCtx.refreshPlayerHackAccess(grant);
accessCtx.refreshPlayerHackAccess({...grant});
assert.equal(mapRefreshes, 1, 'New grant refreshes map immediately, tool responses do not flood it');
