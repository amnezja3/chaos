const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
let requests = [];
let click;
let homeCalls = 0;
let button = {disabled:false,setAttribute(){},removeAttribute(){},addEventListener(_name, fn){click=fn;}};
const context = vm.createContext({
    catalog: [{id:'old'}], catalogLoaded:true, catalogLoading:null,
    googleplexDownloadUpdates:new Map(), applyGoogleplexDownloadUpdate(){},
    dedupeGoogleplexCatalog: value => value,
    toolbarProfile:{}, walletBalance:0, renderBrowserWallet(){}, renderCatalog(){},
    pendingGoogleplexSearch:'', browserQueries:{}, activeBrowserTab:'googleplex', search:{value:''},
    fetch: () => new Promise(resolve => requests.push(resolve)),
    term:{querySelector:()=>button},
    loadGoogleplexHome:async options=>{assert.equal(options.force,true);homeCalls++;},
    rememberGoogleplexHomeScroll(){}, console,
    addSystemMessage(){throw Error('unexpected refresh error');}
});
vm.runInContext(source.slice(source.indexOf('    async function loadCatalog('),
                            source.indexOf('    async function loadExchange(')), context);
const refreshStart = source.indexOf("    const browserRefreshButton = term.querySelector('.browser-refresh-btn');");
vm.runInContext(source.slice(refreshStart,
                            source.indexOf("    term.querySelectorAll('.browser-tab').forEach", refreshStart)), context);
const finish = (resolve, id) => resolve({ok:true,json:async()=>[{id}]});
const settle = async () => { for(let i=0;i<12;i++) await Promise.resolve(); };
(async()=>{
    // Home refresh must replace the cached catalog even without a search query.
    let pending = click();
    assert.equal(homeCalls,1);
    assert.equal(requests.length,1);
    finish(requests.shift(),'published');
    await pending;
    assert.equal(context.catalog[0].id,'published');
    assert.equal(button.disabled,false);
    // Refresh during an old in-flight load must make another request.
    context.catalogLoaded=false;
    context.search.value='Syslog';
    const initial=context.loadCatalog();
    pending=click();
    assert.equal(requests.length,1);
    finish(requests.shift(),'stale');
    await initial;
    await settle();
    assert.equal(requests.length,1,'refresh must fetch again after old request');
    finish(requests.shift(),'latest');
    await pending;
    assert.equal(context.catalog[0].id,'latest');
    assert.equal(context.search.value,'Syslog');
    assert.equal(button.disabled,false);
    console.log('WebDragon refresh PASS: home catalog invalidation and in-flight search refresh');
})().catch(error=>{console.error(error);process.exitCode=1;});
