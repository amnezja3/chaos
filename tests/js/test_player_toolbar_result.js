const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const names = ['buildApplicationLaunchContext', 'applicationResponseMatchesCurrentTarget',
    'toolbarTargetsShareProgressIdentity', 'hasToolbarAimedTarget',
    'toolbarResultCapturedTarget', 'handleToolbarTargetCapturedResult',
    'triggerToolbarTargetHackedEffect', 'getToolbarTargetHackedEffectKey'];
const sandbox = {
    console, Date, setTimeout: () => 1, clearTimeout() {},
    toolbarProfile: { aimed_target: { target_mode: 'player', target_username: 'victim',
        target_id: 'player:victim', label: 'Victim', lat: 52, lng: 21 } },
    toolbarTargetHackedEffectKeys: new Set(), toolbarTargetHackedEffectTimer: null,
    getCurrentAppFlowId: () => '', createApplicationInvocationReceipt: () => 'receipt',
    resolveApplicationFeedbackAction: () => 'scan_ports', toolbarTargetMatchesCaptured: () => true,
    window: {}, isToolbarPlaceholderTarget: () => false,
    clearToolbarTargetLocalOverride() {}, renderToolbarStatus() {},
    setToolbarProfile(profile) { sandbox.toolbarProfile = profile; },
};
vm.createContext(sandbox);
for (const name of names) {
    const start = source.indexOf(`function ${name}(`);
    const end = source.indexOf('\n}\n', start) + 3;
    assert.ok(start >= 0 && end > start, name);
    vm.runInContext(source.slice(start, end), sandbox);
}
const context = sandbox.buildApplicationLaunchContext({ id: 'xmapper', _source: 'terminal' });
assert.equal(context.expected_target.target_username, 'victim');
// Movement does not change player identity, switching or clearing does.
sandbox.toolbarProfile.aimed_target.lat = 53;
assert.equal(sandbox.applicationResponseMatchesCurrentTarget(context), true);
sandbox.toolbarProfile.aimed_target.target_username = 'other';
assert.equal(sandbox.applicationResponseMatchesCurrentTarget(context), false);
sandbox.toolbarProfile.aimed_target = {};
assert.equal(sandbox.applicationResponseMatchesCurrentTarget(context), false);
sandbox.toolbarProfile.aimed_target = context.expected_target;
const result = { success: true, target: null, captured_target: null,
    player_hack_access: { active: true }, captured_player: {
        ...context.expected_target, player_hack_access_until: '2026-09-16T12:00:00' } };
assert.equal(sandbox.handleToolbarTargetCapturedResult(result), true);
assert.equal(sandbox.hasToolbarAimedTarget(sandbox.toolbarProfile.aimed_target), false);
assert.equal(sandbox.toolbarTargetHackedEffect.label, 'Victim');
assert.equal(sandbox.toolbarTargetHackedEffectKeys.size, 1);
sandbox.handleToolbarTargetCapturedResult(result);
assert.equal(sandbox.toolbarTargetHackedEffectKeys.size, 1);
assert.equal(sandbox.toolbarResultCapturedTarget({ ...result, replayed: true }), false);
assert.equal(sandbox.toolbarResultCapturedTarget({ ...result, success: false }), false);
assert.equal(sandbox.toolbarResultCapturedTarget({ ...result, player_hack_access: {active: false} }), false);
console.log('player toolbar identity, capture animation and replay guards PASS');
