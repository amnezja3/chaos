const fs=require('fs'),vm=require('vm'),assert=require('assert');
function fixture() {
    let posts=[],stops=0,plays=0,callbacks=[],fail=false, now=1000;
    let sequence=0, audioContext=null;
    const timers=new Map();
    const nodes={};
    const node=s=>nodes[s] ||= {textContent:'',isConnected:true,addEventListener(_,fn){this.onclick=fn;}};
    const app={isConnected:true,style:{},scrollIntoView(){},querySelector(){return {focus(){}};}};
    const body={innerHTML:'',querySelector:node};
    const presentation={app_id:'one',artifact_id:'build1',name:'Scanner',menu_name:'Czesacz',icon:'X',
        sfx_event:'scanner.regular.sweep',frame_id:'double',frame_color:'cyan',button_color:'amber',logs:{start:'Start'}};
    const ctx={console,Date:{now:()=>now},Set,Map,encodeURIComponent,desktopSessionActive:true,
        escapeHTML:String,crypto:{randomUUID:()=> 'id-'+(++sequence)},clearInterval(){},
        setTimeout:(fn,delay)=>{const id=++sequence;timers.set(id,{fn,delay});return id;},
        clearTimeout:id=>timers.delete(id),
        setInterval:fn=>{callbacks.push(fn);return callbacks.length;},
        MutationObserver:class {observe(){}},document:{body:{}},
        fetch:async(url,options)=>{posts.push({url,body:JSON.parse(options.body)});
            if(fail) throw Error('offline');
            return {ok:true,json:async()=>({success:true,token:'token-one',ttl:35,presentation})};},
        window:{addEventListener(){},GameSfx:{unlock(){},play(_,context){plays++;audioContext=context;return {stop(){stops++;context.on_end?.();}};}}}};
    vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/js/ghostlab_scanner.js','utf8'),ctx);
    const api=ctx.window.DeepScanner;
    const data={product:{id:'one',runtime_enabled:true,description:'safe',installed_version:1}};
    return {ctx,api,app,body,data,posts,callbacks,nodes,timers,ended:()=>audioContext.on_end(),plays:()=>plays,stops:()=>stops,
        tick(){const [id,timer]=timers.entries().next().value;timers.delete(id);now+=timer.delay;timer.fn();},
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

    f=fixture();await f.render();const long=f.api.begin({},null,()=>{});
    const parallel=f.api.begin({},null,()=>{});
    for(let i=0;i<3;i++){f.ended();assert.equal([...f.timers.values()][0].delay,250);f.tick();}
    assert.equal(f.plays(),4,'sound repeats throughout a long scan');
    long.dispose();assert.equal(f.stops(),0,'other map still scanning keeps the shared audio');
    f.ended();parallel.dispose();assert.equal(f.timers.size,0,'completion cancels pending repeat');
    assert.equal(f.stops(),1);
    f=fixture();await f.render();f.api.begin({},null,()=>{});f.ended();f.api.stop();
    assert.equal(f.timers.size,0,'closing app during the pause prevents late playback');

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
    const firstScan={id:'scan-one',live:()=>true},secondScan={id:'scan-two',live:()=>true};
    const key=mapWindow.DeepScannerMap.messageKey;
    assert.equal(key(firstScan,'success'),key(firstScan,'success'),'same response remains deduplicated');
    assert.notEqual(key(firstScan,'success'),key(secondScan,'success'),'next scan can repeat the same text');
    assert.equal(key(null,'success'),undefined,'ordinary messages keep their existing deduplication');
    const source=fs.readFileSync('templates/map_template.html','utf8');
    const start=source.indexOf('async function mapAction('),tail=source.slice(start),end=tail.slice(1).search(/\n        (?:async )?function /);
    new vm.Script(tail.slice(0,end+1));
    console.log('Deep Scanner lifecycle, SFX and assets PASS');
})().catch(error=>{console.error(error);process.exit(1);});
