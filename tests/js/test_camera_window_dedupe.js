const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const windows = [];
let focused = 0;
const context = {
    window: {}, console,
    document: {querySelectorAll: () => windows},
    toolbarProfile: {aimed_target: {lat: 52, lng: 21, camera_id: 'one'}},
    runSystemLauncherApp: () => false,
    bringWindowToFront: () => focused++,
    buildApplicationLaunchContext: () => ({}),
    appFlowTrace() {}, getToolbarTargetStableKey: () => 'target',
    app_window() { windows.push({dataset: {cameraLaunchKey: context.window.__pendingApplicationLaunchContext.camera_launch_key}}); },
};
vm.createContext(context);
function load(start, end) {
    const a = source.indexOf(start), b = source.indexOf(end, a);
    assert(a >= 0 && b > a);
    vm.runInContext(source.slice(a, b), context);
}
load('function cameraApplicationLaunchKey(', 'function launchApplicationFromEntry(');
load('function launchApplicationEffect(', 'function scheduleOperationalAppAutoClose(');
const app = {id: 'camera-off', interface: 'window', operation_types: ['camera_shutdown']};
context.launchApplicationEffect(app);
context.launchApplicationEffect({...app, id: 'other-camera-off'});
context.launchApplicationEffect(app);
assert.strictEqual(windows.length, 1);
assert.strictEqual(focused, 2);
context.activeProvisionalHydrationSession = {appWindow: windows[0]};
context.app_window = () => { context.hydrated = true; };
context.launchApplicationEffect(app);
assert.strictEqual(context.hydrated, true, 'queue hydration must reuse its provisional window');
context.activeProvisionalHydrationSession = null;
context.app_window = () => windows.push({dataset: {cameraLaunchKey: context.window.__pendingApplicationLaunchContext.camera_launch_key}});
context.toolbarProfile.aimed_target.lng = 22;
context.launchApplicationEffect(app);
assert.strictEqual(windows.length, 2, 'different cameras may have independent windows');
console.log('camera window deduplication: PASS');
