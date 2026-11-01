'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const start = source.indexOf('function buildApplicationLaunchContext(');
const end = source.indexOf('\nfunction ', start + 1);
const target = {target_id:'map:48.8529:2.3347:Kamera sklepu',lat:48.8529,lng:2.3347,
    camera_id:'camera_world',scan_id:'scan_current',parent_target_id:'4465816539',
    target_type:'camera',source_type:'camera',label:'Kamera sklepu'};
const context = vm.createContext({window:{},toolbarProfile:{aimed_target:target},
    getCurrentAppFlowId:()=> 'flow',hasToolbarAimedTarget:t=>!!t.lat,
    createApplicationInvocationReceipt:()=> 'receipt',
    resolveApplicationFeedbackAction:()=> 'camera_stream',toolbarTargetMatchesCaptured:()=>true});
vm.runInContext(source.slice(start,end),context);
for (const app of [{id:'glass'}, {id:'glass',_expected_target:target,_launch_receipt:'queued'}]) {
    const result=context.buildApplicationLaunchContext(app);
    const wire=JSON.parse(JSON.stringify(result)).expected_target;
    for(const key of ['camera_id','scan_id','parent_target_id','target_type','source_type'])
        assert.equal(wire[key],target[key],key);
    assert.equal(wire.target_id,target.target_id);
}
console.log('PASS: desktop and queued camera identity survives request serialization');
