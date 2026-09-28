const fs = require('fs'), vm = require('vm'), assert = require('assert');
const source = fs.readFileSync('static/js/ghostlab_firmware.js', 'utf8');
function fixture() {
    const nodes = {};
    const node = key => nodes[key] ||= {textContent:'', innerHTML:'', disabled:false,
        addEventListener(_, fn) { this.onclick = fn; }};
    const buttons = ['[data-flash]', '[data-buy]', '[data-refresh]'].map(node);
    const body = {isConnected:true, innerHTML:'', querySelector:node, querySelectorAll:() => buttons};
    const app = {isConnected:true};
    const info = {success:true, state:{crash_id:'',cooldown_until:0}, server_time:100,
        pending:'paid-receipt', has_pending:true, policy:{success_percent:50},
        available:{price:100,artifact_id:'v2'}, gains:{disk_mb:100,scan_m:50,storage:{capacity:5000},scan_range_m:4000}};
    let accepted = true, fail = false, posts = [], reloads = 0, state = {success:true,crash_id:''};
    let overlay, restartCalls = 0, reloadCalls = 0;
    const sibling = {tagName:'MAIN', inert:false};
    const timers = [];
    const ctx = {console, encodeURIComponent, Date, Map, Set,
        escapeHTML: s => String(s).replaceAll('<', '&lt;'), desktopSessionActive:true,
        sessionStorage:{getItem:() => 'stable-key',setItem(){},removeItem(){}}, crypto:{randomUUID:() => 'key'},
        setTimeout:(fn, ms) => ms > 1000 ? timers.push(fn) : fn(), setInterval(){},
        window:{addEventListener(){}}, location:{reload(){reloadCalls++;}}, updateStorageView(){},
        showGhostDecisionDialog:async () => accepted,
        document:{hidden:false, addEventListener(){},
            getElementById:() => overlay,
            createElement:() => {
                const button = {disabled:true,focus(){}};
                const status = {textContent:''};
                return {isConnected:true,dataset:{},setAttribute(){},focus(){},addEventListener(){},
                    querySelector: s => s === 'button' ? button : status,
                    remove(){this.isConnected=false;overlay=null;}};
            },
            body:{children:[sibling], classList:{add(){},remove(){}}, appendChild(el){overlay=el;}}
        },
        fetch:async (url, options) => {
            if (url === '/api/firmware/state') return {ok:true,json:async () => state};
            if (url === '/api/firmware/restart') {restartCalls++;return {ok:true,json:async () => ({success:true})};}
            if (options?.method !== 'POST') return {ok:true,json:async () => info};
            posts.push(JSON.parse(options.body));
            if (fail) throw Error('lost response');
            return {ok:true,json:async () => ({success:true,succeeded:true,message:'Saved',disk_mb:100,scan_m:50,storage:{capacity:5100}})};
        }};
    vm.createContext(ctx); vm.runInContext(source,ctx);
    return {ctx,app,body,nodes,info,timers,sibling, posts:() => posts,reloads:() => reloads,
        restartCalls:() => restartCalls,reloadCalls:() => reloadCalls,overlay:() => overlay,
        state:s => state=s,accept:a => accepted=a,fail:a => fail=a,
        render:() => ctx.renderGhostLabFirmware(app,body,{product:{id:'child',template_id:'firmware_update',installed_version:1,runtime_enabled:true}},async () => reloads++)};
}
(async () => {
    let f = fixture(); await f.render();
    f.accept(false); await f.nodes['[data-flash]'].onclick(); assert.equal(f.posts().length,0);
    f.accept(true); f.fail(true); await f.nodes['[data-flash]'].onclick();
    f.fail(false); await f.nodes['[data-flash]'].onclick();
    assert.equal(f.posts().length,2);
    assert.equal(f.posts()[0].receipt,f.posts()[1].receipt,'lost response retries the paid attempt');
    assert(f.nodes['[data-flash]'].disabled,'committed attempt cannot be used twice');

    f = fixture(); await f.render(); f.app.isConnected=false;
    await f.nodes['[data-flash]'].onclick(); assert.equal(f.posts().length,0,'closed window cannot begin flash');

    f = fixture(); f.info.pending=null;f.info.has_pending=false;
    await f.render(); await f.nodes['[data-buy]'].onclick();
    assert.equal(f.posts()[0].client_action_key,'stable-key');assert.equal(f.reloads(),1);

    f = fixture(); f.state({success:true,crash_id:'crash-1',server_time:100,restart_after:108});
    await f.ctx.syncFirmwareCrash();
    assert(f.overlay()); assert(f.sibling.inert,'background keyboard and pointer interaction disabled');
    assert(f.overlay().querySelector('button').disabled);
    f.timers[0](); await f.overlay().querySelector('button').onclick();
    assert.equal(f.restartCalls(),1); assert.equal(f.reloadCalls(),1);
    f.state({success:true,crash_id:''}); await f.ctx.syncFirmwareCrash();
    assert(!f.overlay()); assert(!f.sibling.inert,'successful recovery restores background');
    console.log('GhostLab firmware UI PASS');
})().catch(error => {console.error(error);process.exit(1);});
