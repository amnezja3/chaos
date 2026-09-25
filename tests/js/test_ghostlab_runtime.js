const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
function extract(name) {
    const start = source.search(new RegExp(`(?:async )?function ${name}\\(`));
    const tail = source.slice(start), end = tail.slice(1).search(/\n(?:async )?function /);
    return tail.slice(0, end + 1);
}
let routed;
const route = {window:{}, openGhostLabInstalledApp:id=>{routed=id;}};
vm.createContext(route);
vm.runInContext(extract('launchApplicationEffect'),route);
route.launchApplicationEffect({id:'ghostlab_child',interface:'terminal'});
assert.equal(routed,'ghostlab_child','offspring must not run placeholder terminal logs');
const nodes = {};
function node(selector) { return nodes[selector] ||= {textContent:'',disabled:false,addEventListener(_,fn){this.click=fn;}}; }
const body = {innerHTML:'',querySelector:node};
const app = {style:{},isConnected:true,querySelector:s=>s==='[data-body]'?body:node(s),remove(){this.isConnected=false;}};
const calls=[]; let used;
const state={success:true,product:{name:'Own Reader',icon:'X',installed_version:1,artifact_id:'a1',runtime_enabled:true},
    available_artifact_id:'a2',available_version:2,update_available:true,
    access:{active:true,victim_username:'target',tools:[{id:'ghostlab_child',enabled:true}]}};
const ctx={document:{createElement:()=>app,body:{appendChild(){}}},findAvailablePosition:()=>({top:0,left:0}),
    makeDraggable(){},escapeHTML:String,encodeURIComponent,desktopSessionActive:true,
    fetch:async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>state};},
    refreshPlayerHackAccess:async()=>{},usePlayerHackTool:async id=>{used=id;}};
vm.createContext(ctx); vm.runInContext(extract('openGhostLabInstalledApp'),ctx);
(async()=>{
    await ctx.openGhostLabInstalledApp('ghostlab_child');
    assert(body.innerHTML.includes('Aktualizuj bezpłatnie'));
    assert(node('[data-title]').textContent.includes('Own Reader v1'));
    await node('[data-run]').onclick({target:node('[data-run]')});
    assert.equal(used,'ghostlab_child');
    node('[data-update]').click({target:node('[data-update]')});
    await new Promise(setImmediate);
    const update=calls.find(c=>c.options.method==='POST');
    assert.deepEqual(JSON.parse(update.options.body),{expected_artifact_id:'a1',artifact_id:'a2'});
    assert(calls.every(c=>c.url.startsWith('/api/ghostlab/installed/')));
    let fm;
    const delta = {toolbarProfile:{apps:[{id:'keep'},{id:'child',name:'Old'}],files:{tools:[{app_id:'keep',name:'keep.sh'},{app_id:'child',name:'Old.sh'}]}},
        setToolbarProfile:p=>{delta.toolbarProfile=p;}, rebuildDesktopAppsFromProfile:async()=>{},
        refreshOpenFileManagersForApps:p=>{fm=p;}, window:{dispatchEvent(){}}, CustomEvent:function(){}};
    vm.createContext(delta); vm.runInContext(extract('updateAppsView'),delta);
    await delta.updateAppsView({reason:'ghostlab_update',app:{id:'child',name:'New'},removed_tool_ids:['Old.sh'],updated_tools:[{app_id:'child',name:'New.sh'}]});
    assert.equal(delta.toolbarProfile.apps.length,2);
    assert.equal(fm.files.tools.length,2);
    assert(fm.files.tools.some(t=>t.name==='New.sh'));
    assert(!fm.files.tools.some(t=>t.name==='Old.sh'));
    console.log('GhostLab runtime launcher: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
