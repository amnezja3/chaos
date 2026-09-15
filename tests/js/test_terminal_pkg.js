"use strict";

const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const start = source.indexOf('async function handleTerminalPkgCommand');
const end = source.indexOf('async function executeSystemTerminalCommand', start);
const output = [];
const calls = [];
const installs = [];
let accept = true;
let result = [true, {}];
let payload = [
    { id: 'logReader', name: 'System Log Reader', price: 900 },
    { id: 'tool-a', name: 'Duplicate', price: 10 },
    { id: 'tool-b', name: 'Duplicate', price: 20 },
    { id: 'ticket', name: 'Travel Ticket', product_type: 'travel_ticket', price: 100 },
    { id: 'confirm', name: 'Confirm', purchase_confirmation: true },
    { id: 'unsafe', name: '<img onerror=attack>' },
    { id: 'hidden', name: 'Hidden', published: false },
    { id: 'logReader', name: 'Duplicate record' }
];
let responseOk = true;
let badJson = false;
const sandbox = {
    appendSystemTerminalOutput(_content, text) { output.push(text); },
    escapeHTML(text) { return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); },
    async fetch(url) {
        calls.push(url);
        return { ok: responseOk, status: responseOk ? 200 : 503, async json() {
            if (badJson) throw new Error('not JSON');
            return payload;
        } };
    },
    async showGhostDecisionDialog() { return accept; },
    showInstallAppProgress(item, callback, settled) {
        assert.strictEqual(callback, null, 'reuse normal installer projection handling');
        installs.push(item.id);
        settled(...result);
    }
};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);
const run = command => sandbox.handleTerminalPkgCommand(command, {});

(async () => {
    assert.strictEqual(await run('apps'), null);
    for (const command of ['pkg', 'pkg install', 'pkg search ""', 'pkg nope x', 'pkg list-all extra']) {
        assert.strictEqual(await run(command), false);
    }
    assert.strictEqual(calls.length, 0, 'invalid syntax does not fetch or install');
    assert.strictEqual(await run('pkg list-all'), true);
    assert.ok(output.at(-1).includes('6 pozycji'));
    assert.ok(!output.at(-1).includes('Hidden'));
    assert.ok(!output.at(-1).includes('<img'));
    assert.strictEqual(await run('PKG search log'), true);
    assert.ok(output.at(-1).includes('System Log Reader [logReader] — 900 HC'));
    await run('pkg search absent');
    assert.ok(output.at(-1).includes('Brak pozycji'));
    assert.strictEqual(await run('pkg install log'), false);
    assert.strictEqual(await run('pkg install Duplicate'), false);
    assert.strictEqual(installs.length, 0, 'partial and ambiguous names never purchase');
    assert.strictEqual(await run('pkg install "system log reader"'), true);
    assert.strictEqual(installs[0], 'logReader');
    assert.strictEqual(await run('pkg install TOOL-B'), true);
    assert.strictEqual(installs[1], 'tool-b');
    accept = false;
    assert.strictEqual(await run('pkg install ticket'), false);
    assert.strictEqual(await run('pkg install confirm'), false);
    assert.strictEqual(installs.length, 2, 'cancel does not invoke installer');
    accept = true;
    result = [false, { message: 'Brak HC.', reason: 'insufficient_funds' }];
    assert.strictEqual(await run('pkg install logReader'), false);
    assert.ok(output.at(-1).includes('Brak HC.'));
    assert.ok(output.at(-1).includes('insufficient_funds'));
    result = [false, { reason: 'network_error' }];
    assert.strictEqual(await run('pkg install logReader'), false);
    assert.ok(output.at(-1).includes('niepotwierdzony'));
    responseOk = false;
    badJson = true;
    assert.strictEqual(await run('pkg list-all'), false);
    assert.ok(output.at(-1).includes('503'));
    responseOk = true;
    badJson = false;
    payload = [];
    assert.strictEqual(await run('pkg list-all'), true);
    assert.ok(output.at(-1).includes('pusty'));
    assert.ok(calls.every(url => url === '/resources.json'), 'no full profile or alternate installation API');
    const dispatcher = source.slice(end, source.indexOf('function attachSystemTerminalInputHandler', end));
    assert.ok(dispatcher.indexOf('await handleTerminalPkgCommand') < dispatcher.indexOf("fetch('/command'"));
    console.log('Terminal pkg tests: OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
