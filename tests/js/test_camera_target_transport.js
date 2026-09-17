const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('templates/map_template.html', 'utf8');
const target = {camera_id: 'camera-test', scan_id: 'scan-test', parent_target_id: 'shop-test'};
function payload(functionName, values) {
    const start = source.indexOf(functionName);
    assert(start >= 0);
    const body = source.indexOf('body: JSON.stringify({', start);
    const end = source.indexOf('})', body);
    assert(body > start && end > body);
    return JSON.parse(vm.runInNewContext(source.slice(body + 'body: '.length, end + 2), values));
}
const shared = {action: 'mark_target', lat: 52, lng: 21, label: 'Kamera', icon: 'camera',
    sourceType: 'camera', name: 'Kamera', generated: true, targetContext: target};
for (const body of [
    payload('async function mapAction(', shared),
    payload('async function aimMapTargetOnly(', {normalized: target}),
    payload('function hackingAction(', {...shared, action: 'camera_shutdown', source_type: 'camera',
        vulnerability_id: null, target_mode: null, contest_owner_username: null,
        foreign_area_id: null, target_username: null, target_id: null, conflict_id: null,
        hackFlowId: 'flow', hackActionKey: 'key'})
]) {
    assert.strictEqual(body.camera_id, target.camera_id);
    assert.strictEqual(body.scan_id, target.scan_id);
}
console.log('camera target transport: PASS');
