const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
let resolve, requests = 0, opened = 0;
const message = {textContent: ''};
const button = {disabled: false};
const panel = {isConnected: true, querySelector: () => message, querySelectorAll: () => [button]};
const ctx = {
    playerHackAccessState: {active: true, victim_username: 'a'}, desktopSessionActive: true,
    getPlayerHackAccessPanel: () => panel, openFriendKickerApp() { opened++; },
    fetch() { requests++; return new Promise(done => { resolve = done; }); }
};
vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('async function usePlayerHackTool('), source.indexOf('window.refreshPlayerHackAccess')), ctx);
(async () => {
    const first = ctx.usePlayerHackTool('friendKicker');
    assert(button.disabled);
    await ctx.usePlayerHackTool('friendKicker');
    assert.equal(requests, 1);
    ctx.playerHackAccessState = {active: true, victim_username: 'b'};
    resolve({ok: true, json: async () => ({success: true, result_type: 'friend_kicker'})});
    await first;
    assert.equal(opened, 0);
    assert(!button.disabled);
    const second = ctx.usePlayerHackTool('friendKicker');
    resolve({ok: false, status: 502, json: async () => { throw Error('HTML'); }});
    await second;
    assert(message.textContent.includes('502'));
    assert(message.textContent.includes('niepotwierdzony'));
    assert(!button.disabled);
    const third = ctx.usePlayerHackTool('friendKicker');
    ctx.desktopSessionActive = false;
    resolve({ok: true, json: async () => ({success: true, result_type: 'friend_kicker'})});
    await third;
    assert.equal(opened, 0);
    console.log('PvP request guard: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
