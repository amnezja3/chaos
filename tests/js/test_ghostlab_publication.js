const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
function extract(name) {
    const re = new RegExp(`(?:async )?function ${name}\\(`);
    const start = source.search(re);
    assert(start >= 0, name);
    const tail = source.slice(start);
    const next = tail.slice(1).search(/\n(?:async )?function /);
    return next < 0 ? tail : tail.slice(0, next + 1);
}
let blueprint = {log_limit: 5};
let calls = [];
let messages = [];
const project = {id: 'p', revision: 2, blueprint: {log_limit: 5}, artifact: {artifact_id: 'a', source_revision: 2}};
const context = vm.createContext({
    collectGhostLabBlueprint: () => blueprint,
    setGhostLabMessage: (_root, message) => messages.push(message),
    setGhostLabWorking: () => {},
    refreshGhostLabEditorFeedback: () => ({valid:true}),
    ghostLabState: {projects:[project]},
    renderGhostLabEditor: () => {},
    selectedGhostLabProject: () => project,
    console, encodeURIComponent,
    fetch: async (url, options) => {
        calls.push({url,body:JSON.parse(options.body)});
        return {ok:true,json:async()=>({success:true,project,projects:[project]})};
    },
    window: {refreshDesktop: () => {throw Error('Full desktop refresh forbidden');}},
});
for (const name of ['ghostLabBlueprintDirty','ghostLabBuildIsCurrent','publishGhostLabProject','compileGhostLabProject']) {
    vm.runInContext(extract(name),context);
}
(async () => {
    blueprint = {log_limit:1};
    await context.publishGhostLabProject({},'p');
    await context.compileGhostLabProject({},'p');
    assert.equal(calls.length,0,'Unsaved blueprint must not publish/compile silently');
    blueprint = {log_limit:5};
    project.artifact.source_revision=1;
    await context.publishGhostLabProject({},'p');
    assert.equal(calls.length,0,'Old build must not publish');
    project.artifact.source_revision=2;
    await context.publishGhostLabProject({},'p');
    assert.equal(calls.length,1);
    assert.equal(calls[0].body.revision,2);
    assert.equal(calls[0].body.artifact_id,'a');
    assert(messages.length>=3);
    console.log('GhostLab publication JS: PASS (dirty, stale, explicit build, no heavy refresh)');
})().catch(error=>{console.error(error);process.exitCode=1;});
