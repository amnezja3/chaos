const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const content = { innerHTML: '' };
const message = { textContent: '' };
let requests = 0;
let refreshes = 0;
let toolbarRefreshes = 0;
let failNetwork = false;
let rejected = false;
const sandbox = {
    document: { createElement: () => ({ style: {}, dataset: {}, querySelector: selector =>
        selector === '.financial-sniffer-content' ? content : { addEventListener() {} } }),
        body: { appendChild() {} } },
    findAvailablePosition: () => ({ top: 0, left: 0 }),
    makeDraggable() {}, appFlowTrace(_id, _event, details) { assert.strictEqual(details.app_id, 'financialSniffer'); },
    formatHackAccessTime: String, escapeHTML: value => String(value).replace(/</g, '&lt;'),
    playerHackAccessState: { active: true, victim_username: 'victim', seconds_left: 100 },
    refreshToolbarProfile() { toolbarRefreshes++; },
    getPlayerHackAccessPanel: () => ({ querySelector: () => message }),
    refreshPlayerHackAccess() { refreshes++; },
    async fetch() {
        requests++;
        if (failNetwork) throw new Error('offline');
        return { ok: !rejected, async json() { return rejected ? { success: false, error: 'Dostęp wygasł.' } : {
            success: true, result_type: 'financial_sniffer', stolen_amount: 8, attacker_balance: 18,
            message: 'Przechwycono 8 HC.', access: { victim_nick: '<script>', seconds_left: 100 }
        }; } };
    }
};
vm.createContext(sandbox);
const renderStart = source.indexOf('function renderFinancialSnifferResult(');
const renderEnd = source.indexOf('window.openFinancialSnifferApp', renderStart);
vm.runInContext(source.slice(renderStart, renderEnd), sandbox);
const useStart = source.indexOf('async function usePlayerHackTool(');
const useEnd = source.indexOf('window.refreshPlayerHackAccess', useStart);
vm.runInContext(source.slice(useStart, useEnd), sandbox);
(async () => {
    await sandbox.usePlayerHackTool('financialSniffer');
    assert.ok(content.innerHTML.includes('8 HC'));
    assert.ok(content.innerHTML.includes('&lt;script>'));
    assert.strictEqual(toolbarRefreshes, 1);
    assert.strictEqual(refreshes, 1);
    assert.strictEqual(message.textContent, 'Przechwycono 8 HC.');
    sandbox.openFinancialSnifferApp = () => { throw new Error('renderer failure'); };
    await sandbox.usePlayerHackTool('financialSniffer');
    assert.ok(message.textContent.includes('Przechwycono 8 HC.'));
    assert.ok(message.textContent.includes('wyświetlić'));
    assert.ok(!message.textContent.includes('komunikacji'));
    failNetwork = true;
    await sandbox.usePlayerHackTool('financialSniffer');
    assert.ok(message.textContent.includes('niepotwierdzony'));
    failNetwork = false;
    rejected = true;
    await sandbox.usePlayerHackTool('financialSniffer');
    assert.strictEqual(message.textContent, 'Dostęp wygasł.');
    assert.strictEqual(requests, 4, 'one request per explicit use, never automatic retry');
    console.log('Player hack Financial Sniffer result tests: OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
