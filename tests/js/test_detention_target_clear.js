const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source=fs.readFileSync('static/js/terminal.js','utf8');
let disposed=0, removed=0, closed=0, frameCleared=0, overrides=0;
const targetWindow={dataset:{expectedTarget:'{"target_id":"old"}'},
    querySelector:()=>({click:()=>closed++}), remove:()=>removed++};
const ordinaryWindow={dataset:{expectedTarget:''}};
const ctx={window:{profileData:{aimed_target:{target_id:'old'}},__pendingApplicationLaunchContext:{expected_target:{}}},
    toolbarProfile:{aimed_target:{target_id:'old'}},toolbarTargetHackedEffect:{},
    clearToolbarTargetLocalOverride:()=>overrides++,disposeOperationFeedbackWindow:()=>disposed++,
    document:{querySelectorAll:selector=>selector==='iframe'
        ? [{contentWindow:{clearDetentionTarget:()=>frameCleared++}}] : [targetWindow,ordinaryWindow]}};
vm.createContext(ctx);
const start=source.indexOf('window.clearDetentionTarget = function');
vm.runInContext(source.slice(start,source.indexOf('function renderToolbarStatus()',start)),ctx);
ctx.window.clearDetentionTarget();
assert.equal(Object.keys(ctx.toolbarProfile.aimed_target).length,0);
assert.equal(Object.keys(ctx.window.profileData.aimed_target).length,0);
assert.equal(ctx.window.__pendingApplicationLaunchContext,null);
assert.equal(targetWindow.dataset.expectedTarget,'');
assert.equal(disposed,1); assert.equal(removed,1); assert.equal(closed,1);
assert.equal(frameCleared,1); assert.equal(overrides,1);
ctx.window.DetentionUI={state:{stage:6}};
const n=source.indexOf('function normalizeToolbarProfileProgress(');
const body=source.slice(n,source.indexOf('\nfunction ',n+10));
vm.runInContext(body,ctx);
const normalized=ctx.normalizeToolbarProfileProgress({aimed_target:{target_id:'late-response'}});
assert.equal(Object.keys(normalized.aimed_target).length,0);
console.log('detention target cleared in toolbar, tools, map and delayed profiles: OK');
