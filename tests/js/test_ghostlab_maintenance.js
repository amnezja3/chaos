const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('static/js/ghostlab_maintenance.js', 'utf8');
function fixture(kind = 'system_update') {
    const nodes = {};
    const node = key => nodes[key] ||= {isConnected: true, textContent: '', innerHTML: '', disabled: false,
        addEventListener(_, fn) { this.onclick = fn; }};
    const body = {innerHTML: '', querySelector: node, querySelectorAll: () =>
        ['[data-maintenance-run]', '[data-maintenance-refresh]'].map(node)};
    let posts = 0, storageUpdates = 0, accepted = true, fail = false;
    const app = {isConnected: true};
    const plan = {success: true, token: 'signed', preview: {kind, count: 1, size: 3, preset: 'regular',
        files: [{name: '<img onerror=alert(1)>', size: 3}], logs: ['<script>alert(1)</script>', 'Installing']}};
    const ctx = {escapeHTML: s => String(s).replaceAll('<', '&lt;').replaceAll('>', '&gt;'),
        encodeURIComponent, desktopSessionActive: true, setTimeout: callback => callback(),
        document: {querySelectorAll: () => [], getElementById: () => null},
        fileManagerInstances: new Map(), updateStorageView: () => storageUpdates++,
        showGhostDecisionDialog: async () => accepted,
        fetch: async (url, options) => {
            if (options.method !== 'POST') return {ok: true, json: async () => plan};
            posts++;
            assert.deepEqual(JSON.parse(options.body), {token: 'signed'});
            if (fail) throw Error('lost response');
            return {ok: true, json: async () => ({success: true, message: 'Done', storage: {used: 0}})};
        }};
    vm.createContext(ctx); vm.runInContext(source, ctx);
    return {ctx, nodes, body, app, plan, posts: () => posts, storageUpdates: () => storageUpdates,
        accept: value => accepted = value, fail: value => fail = value,
        render: () => ctx.renderGhostLabMaintenance(app, body, {product: {id: 'child', runtime_enabled: true,
            name: 'Own', installed_version: 1, description: '<img onerror=alert(1)>'}}, () => {})};
}
(async () => {
    let f = fixture(); await f.render();
    assert(f.body.innerHTML.includes('&lt;img'));
    await f.nodes['[data-maintenance-run]'].onclick();
    assert.equal(f.posts(), 1);
    assert(f.nodes['[data-maintenance-log]'].textContent.includes('<script>'));
    assert.equal(f.nodes['[data-maintenance-log]'].innerHTML, '', 'author logs never become HTML');
    assert(f.nodes['[data-maintenance-run]'].disabled, 'new operation needs a fresh preview');

    f = fixture('file_cleanup'); await f.render();
    assert(f.nodes['[data-maintenance-preview]'].innerHTML.includes('&lt;img'));
    f.accept(false); await f.nodes['[data-maintenance-run]'].onclick();
    assert.equal(f.posts(), 0, 'cancel does not mutate inventory');
    f.accept(true); f.fail(true); await f.nodes['[data-maintenance-run]'].onclick();
    assert(!f.nodes['[data-maintenance-run]'].disabled, 'retry remains available after network loss');
    f.fail(false); await f.nodes['[data-maintenance-run]'].onclick();
    assert.equal(f.posts(), 2);

    f = fixture('security_restore'); await f.render();
    assert(f.nodes['[data-maintenance-preview]'].textContent.includes('REGULAR'));
    f.app.isConnected = false; await f.nodes['[data-maintenance-run]'].onclick();
    assert.equal(f.posts(), 0, 'closing during animation cancels execution');

    f = fixture(); await f.render(); f.ctx.desktopSessionActive = false;
    await f.nodes['[data-maintenance-run]'].onclick();
    assert.equal(f.posts(), 0, 'session change cancels execution');

    f = fixture();
    f.ctx.toolbarProfile = {files: {camera: [{id:'removed'}, {id:'keep'}], tools: [{id:'tool'}]}};
    f.ctx.setToolbarProfile = state => { f.ctx.toolbarProfile = state; };
    f.ctx.applyGhostLabMaintenanceResult({removed_file_ids:['removed']});
    assert.equal(f.ctx.toolbarProfile.files.camera.length, 1);
    assert.equal(f.ctx.toolbarProfile.files.camera[0].id, 'keep');
    assert.equal(f.ctx.toolbarProfile.files.tools.length, 1);
    console.log('GhostLab maintenance UI: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
