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
    escapeHTML: value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;'),
    fetch: async (url, options) => {
        calls.push({url,body:JSON.parse(options.body)});
        return {ok:true,json:async()=>({success:true,project,projects:[project]})};
    },
    window: {refreshDesktop: () => {throw Error('Full desktop refresh forbidden');}},
});
for (const name of ['ghostLabSavedBranding','collectGhostLabBranding','ghostLabEditorProject','validateGhostLabBranding','ghostLabBlueprintDirty','ghostLabBuildIsCurrent','publishGhostLabProject','compileGhostLabProject', 'validateGhostLabBlueprint', 'renderGhostLabEditorField']) {
    vm.runInContext(extract(name),context);
}
(async () => {
    const schema = {field_schema: {
        count: {type:'number',minimum:1,maximum:5,integer:true,editable:true},
        policy: {type:'string',max_length:20,default:'locked',editable:false}
    }};
    assert(context.validateGhostLabBlueprint(schema,{count:2,policy:'locked'}).valid);
    for (const count of [NaN,Infinity,true,1.5,6]) {
        assert(!context.validateGhostLabBlueprint(schema,{count,policy:'locked'}).valid);
    }
    assert(!context.validateGhostLabBlueprint(schema,{count:2,policy:'forged'}).valid);
    assert(!context.validateGhostLabBlueprint({},{}).valid);
    assert.match(context.renderGhostLabEditorField({key:'flag',label:'Flag',type:'checkbox',editable:false},true), /disabled/);
    assert.match(context.renderGhostLabEditorField({key:'policy',label:'Policy',type:'textarea',editable:false},'locked'), /readonly/);
    blueprint = {log_limit:1};
    await context.publishGhostLabProject({},'p');
    await context.compileGhostLabProject({},'p');
    assert.equal(calls.length,0,'Unsaved blueprint must not publish/compile silently');
    blueprint = {log_limit:5};
    project.artifact.source_revision=1;
    await context.publishGhostLabProject({},'p');
    assert.equal(calls.length,0,'Old build must not publish');
    project.artifact.source_revision=2;
    const dirtyRoot = {querySelectorAll: () => [{dataset:{ghostlabBranding:'icon'},value:'X'}]};
    assert(context.ghostLabBlueprintDirty(dirtyRoot,project));
    await context.publishGhostLabProject(dirtyRoot,'p');
    await context.compileGhostLabProject(dirtyRoot,'p');
    assert.equal(calls.length,0,'Unsaved branding must block publish and compile');
    const stale = {...project, revision:1};
    assert.equal(context.ghostLabEditorProject({_ghostLabEditingProject:stale},'p').revision,1,
        'A stale editor must not borrow the newer shared-state revision');
    assert.equal(context.validateGhostLabBranding({name:'Name',icon:'X',description:'Desc',suggested_price:null,presentation_id:'default'},project).length,0);
    assert(context.validateGhostLabBranding({name:'Name',icon:'X',description:'Desc',suggested_price:1.5,presentation_id:'default'},project).length);
    await context.publishGhostLabProject({},'p');
    assert.equal(calls.length,1);
    assert.equal(calls[0].body.revision,2);
    assert.equal(calls[0].body.artifact_id,'a');
    assert(messages.length>=3);
    console.log('GhostLab publication JS: PASS (dirty, stale, explicit build, no heavy refresh)');
})().catch(error=>{console.error(error);process.exitCode=1;});
