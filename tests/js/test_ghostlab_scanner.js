const fs=require('fs'),vm=require('vm'),assert=require('assert');
function fixture() {
    let posts=[],stops=0,plays=0,callbacks=[],fail=false, now=1000;
    const nodes={};
    const node=s=>nodes[s] ||= {textContent:'',isConnected:true,addEventListener(_,fn){this.onclick=fn;}};
    const app={isConnected:true,style:{},scrollIntoView(){},querySelector(){return {focus(){}};}};
    const body={innerHTML:'',querySelector:node};
    const presentation={app_id:'one',artifact_id:'build1',name:'Scanner',menu_name:'Czesacz',icon:'X',
        sfx_event:'scanner.regular.sweep',frame_id:'double',frame_color:'cyan',button_color:'amber',logs:{start:'Start'}};
    const ctx={console,Date:{now:()=>now},Set,Map,encodeURIComponent,desktopSessionActive:true,
        escapeHTML:String,crypto:{randomUUID:()=> 'window-id'},clearInterval(){},
        setInterval:fn=>{callbacks.push(fn);return callbacks.length;},
        MutationObserver:class {observe(){}},document:{body:{}},
        fetch:async(url,options)=>{posts.push({url,body:JSON.parse(options.body)});
            if(fail) throw Error('offline');
            return {ok:true,json:async()=>({success:true,token:'token-one',ttl:35,presentation})};},
        window:{addEventListener(){},GameSfx:{unlock(){},play(){plays++;return {stop(){stops++;}};}}}};
    vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/js/ghostlab_scanner.js','utf8'),ctx);
    const api=ctx.window.DeepScanner;
    const data={product:{id:'one',runtime_enabled:true,description:'safe',installed_version:1}};
    return {ctx,api,app,body,data,posts,callbacks,nodes,plays:()=>plays,stops:()=>stops,
        fail:()=>fail=true,expire:()=>now+=36000,render:()=>api.render(app,body,data,()=>{})};
}
(async()=>{
    let f=fixture();await f.render();assert(f.api.snapshot());assert(f.api.focus('one'));assert(!f.api.focus('two'));
    const other={...f.app};await f.api.render(other,f.body,{product:{...f.data.product,id:'two'}},()=>{});
    assert.equal(f.posts.length,1,'second application does not activate');
    const job=f.api.begin({},null,()=>{});assert(job.live());assert.equal(f.plays(),1);
    const concurrent=f.api.begin({},null,()=>{});assert.equal(f.plays(),1,'concurrent map views do not double audio');
    f.api.stop();assert(!job.live());assert.equal(f.stops(),1);job.dispose();assert.equal(f.stops(),1);
    assert.equal(f.posts.at(-1).body.release,true);
    assert(!concurrent.live());

    f=fixture();await f.render();f.app.isConnected=false;assert.equal(f.api.snapshot(),null);
    f=fixture();await f.render();f.expire();assert.equal(f.api.snapshot(),null);
    f=fixture();await f.render();f.fail();await f.callbacks[0]();assert.equal(f.api.snapshot(),null);
    f=fixture();await f.render();f.ctx.desktopSessionActive=false;assert.equal(f.api.snapshot(),null);
    f=fixture();await f.render();f.api.inventory([{id:'one',artifact_id:'build2'}]);assert.equal(f.api.snapshot(),null);
    f=fixture();await f.render();const map={};const detach=f.api.attach(map);f.api.begin(map,null,()=>{});detach();assert.equal(f.stops(),1);
    f=fixture();f.app.isConnected=false;await f.render();assert.equal(f.api.snapshot(),null);assert(f.posts.at(-1).body.release);

    const manifest=JSON.parse(fs.readFileSync('static/audio/sfx/manifest.v1.json'));
    for(const id of ['scanner.regular.sweep','scanner.regular.ping']) {
        const event=manifest.events[id];assert(event);
        const path='static/audio/sfx/'+event.file;const wav=fs.readFileSync(path);
        assert.equal(wav.toString('ascii',0,4),'RIFF');assert.equal(wav.toString('ascii',8,12),'WAVE');
        assert(wav.length>40000,'real nonempty sound asset');
    }
    let presentation={icon:'X',menu_name:'<Czesacz>',logs:{success:'Found'}};
    const button={classList:{remove(){}},removeAttribute(){},replaceChildren(){this.children=[];},append(...nodes){this.children=nodes;}};
    const mapWindow={parent:{DeepScanner:{snapshot:()=>presentation ? {presentation}:null,style(){}}},addEventListener(){}};
    const adapter={window:mapWindow,document:{querySelectorAll:()=>[button],createElement:()=>({setAttribute(){}})}};
    vm.createContext(adapter);vm.runInContext(fs.readFileSync('static/js/ghostlab_scanner_map.js','utf8'),adapter);
    mapWindow.DeepScannerMap.paintMenus();assert.equal(button.children[1].textContent,'<Czesacz>','author name is text, not HTML');
    presentation=null;mapWindow.DeepScannerMap.paintMenus();assert.equal(button.textContent,'🔎 Skanuj');
    const source=fs.readFileSync('templates/map_template.html','utf8');
    const start=source.indexOf('async function mapAction('),tail=source.slice(start),end=tail.slice(1).search(/\n        (?:async )?function /);
    new vm.Script(tail.slice(0,end+1));
    console.log('Deep Scanner lifecycle, SFX and assets PASS');
})().catch(error=>{console.error(error);process.exit(1);});
