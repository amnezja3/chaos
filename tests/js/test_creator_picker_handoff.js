const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const code = source.slice(source.indexOf('function hydrateProvisionalApplicationSession('), source.indexOf('function resolveApplicationFeedbackAction('));
let renders = 0;
const seen = new Set();
const context = {
    console, activeProvisionalHydrationSession: null,
    bindProvisionalApplicationReceipt: (session, item) => { session.receipt = item.receipt; },
    normalizeLaunchQueueItem: item => item,
    updateToolbarAimedTarget: target => { context.target = target; },
    updateProvisionalApplicationSession: (session, state) => { session.state = state; },
    shouldSkipLaunchQueueReceipt: receipt => { const old = seen.has(receipt); seen.add(receipt); return old; },
    launchApplicationEffect: app => {
        assert.strictEqual(app.levels[0].title, 'Author interface');
        assert.strictEqual(context.target.target_id, 'atm:1');
        renders++;
        context.activeProvisionalHydrationSession = null;
    }
};
vm.createContext(context);
vm.runInContext(code, context);
const app = {id: 'creator_test', creator_contract_version: 1, levels: [{title: 'Author interface'}]};
const data = {applicationEffect: app, target: {target_id: 'atm:1'}, added_apps: [{app_id: app.id, receipt: 'receipt-1', action: 'atm_logs'}]};
const session = {appWindow: {isConnected: true}};
assert.strictEqual(context.launchConfirmedPickerApplication(data, session, app, 'flow'), true);
assert.strictEqual(renders, 1);
assert.strictEqual(session.runtimeHydrated, true);
assert.strictEqual(context.hydrateProvisionalApplicationSession(session, app, data.added_apps[0]), 'hydrated');
assert.strictEqual(renders, 1, 'late queue response must not rebuild the app');
assert.strictEqual(context.launchConfirmedPickerApplication(data, session, app, 'flow'), true);
assert.strictEqual(renders, 1, 'replayed picker response must not rebuild the app');
const closed = {disposed: true, appWindow: {isConnected: false}};
assert.strictEqual(context.launchConfirmedPickerApplication(data, closed, app, 'flow'), true);
assert.strictEqual(renders, 1, 'a closed provisional window must not be reopened');
assert.strictEqual(context.launchConfirmedPickerApplication({...data, applicationEffect: {...app, id: 'other'}}, session, app, 'flow'), false);
console.log('creator picker handoff: OK');
