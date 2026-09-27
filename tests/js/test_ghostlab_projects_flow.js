const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
function extract(name) {
    const start = source.search(new RegExp(`(?:async )?function ${name}\\(`));
    assert(start >= 0, name);
    const tail = source.slice(start), next = tail.slice(1).search(/\n(?:async )?function /);
    return next < 0 ? tail : tail.slice(0, next + 1);
}
const nodes = {};
const node = key => nodes[key] ||= {value: '', focus() {}, addEventListener() {}, classList: {toggle() {}}};
const main = {innerHTML: '', querySelector: node};
const root = {querySelector: selector => selector === '[data-ghostlab-main]' ? main : node(selector), querySelectorAll: () => []};
let calls = [], activeTab, opened, accepted = true, fail = false, uuid = 0;
const project = {id: 'new', name: 'Mój projekt', revision: 4, template_id: 'file_cleanup', blueprint: {camera: true}};
const ctx = {crypto: {randomUUID: () => `request-${++uuid}`}, encodeURIComponent, console,
    ghostLabState: {projects: [], selectedProjectId: 'different-selection'},
    escapeHTML: s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;'),
    setGhostLabMessage() {}, setGhostLabWorking() {},
    activateGhostLabTab: (_root, tab) => { activeTab = tab; },
    renderGhostLabEditor: (_root, value) => { opened = value; ctx.ghostLabState.activeProjectId = value.id; },
    showGhostDecisionDialog: async () => accepted,
    selectedGhostLabProject: () => ({id: 'different-selection'}),
    fetch: async (url, options) => {
        calls.push({url, method: options.method, payload: JSON.parse(options.body)});
        if (fail) throw Error('network failure');
        return {ok: true, json: async () => ({success: true, project, projects: [project]})};
    }};
vm.createContext(ctx);
for (const name of ['createGhostLabProject', 'createGhostLabProjectFromTemplate', 'ghostLabCreateRequestId', 'deleteGhostLabProject']) {
    vm.runInContext(extract(name), ctx);
}
(async () => {
    ctx.createGhostLabProject(root);
    assert.equal(calls.length, 0, 'New Project must not create an empty/custom draft');
    node('[data-ghostlab-project-name]').value = '  Mój projekt  ';
    node('[data-ghostlab-new-form]').onsubmit({preventDefault() {}});
    assert.equal(activeTab, 'Templates');
    assert.equal(root._ghostLabNewProjectName, 'Mój projekt');
    assert.equal(calls.length, 0, 'name entry must not create an orphan project');
    const template = {id:'file_cleanup', name:'File Cleanup', icon:'X', category:'maintenance'};
    fail = true;
    await ctx.createGhostLabProjectFromTemplate(root, template);
    const firstId = calls[0].payload.request_id;
    assert.equal(root._ghostLabNewProjectName, 'Mój projekt', 'failure preserves the entered name');
    assert.equal(root._ghostLabCreating, false);
    fail = false;
    await ctx.createGhostLabProjectFromTemplate(root, template);
    assert.equal(calls[1].payload.request_id, firstId, 'network retry uses the same creation key');
    assert.equal(calls[1].payload.name, 'Mój projekt');
    assert.equal(calls[1].payload.template_id, 'file_cleanup');
    assert.equal(opened, project, 'successful creation directly opens the returned editor');
    assert.equal(ctx.ghostLabState.activeProjectId, 'new');
    assert.equal(root._ghostLabNewProjectName, null);

    calls = [];
    root._ghostLabCreating = true;
    await ctx.createGhostLabProjectFromTemplate(root, template);
    assert.equal(calls.length, 0, 'double clicks cannot create multiple projects');
    root._ghostLabCreating = false;
    accepted = false;
    await ctx.deleteGhostLabProject(root, project);
    assert.equal(calls.length, 0, 'cancel does not delete');
    accepted = true;
    await ctx.deleteGhostLabProject(root, {...project, published_artifact_id:'published'});
    assert.equal(calls.length, 0, 'published archive is retained');
    await ctx.deleteGhostLabProject(root, project);
    assert.equal(calls[0].url, '/api/ghostlab/projects/new', 'delete targets the open project, not list selection');
    assert.equal(calls[0].method, 'DELETE');
    assert.equal(calls[0].payload.revision, 4);
    assert.equal(activeTab, 'Projects');
    assert.equal(ctx.ghostLabState.activeProjectId, null);
    assert.equal(root._ghostLabEditingProject, null);

    const list = extract('renderGhostLabTab').split('} else if (tabName === "Templates")')[0];
    assert(!list.includes('data-ghostlab-delete-project'));
    assert(!list.includes('data-ghostlab-rename-project'));
    const editor = extract('renderGhostLabEditor');
    assert(editor.includes('class="ghostlab-danger"'));
    assert(editor.indexOf('data-ghostlab-delete-project') > editor.indexOf('class="ghostlab-danger"'));
    console.log('GhostLab projects flow: PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
