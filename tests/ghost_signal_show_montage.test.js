const assert = require('assert');
require('../static/js/map_glitch.js');
require('../static/js/ghost_signal_network_details.js');
const {createController,networkPositions,machineFocusPoses} = require('../static/js/ghost_signal_show.js');
class Node {
    constructor(tag) {
        this.tag = tag; this.children = []; this.attrs = {}; this.className = '';
        this.clientWidth=640;this.clientHeight=360;this.events={};
        this.style = {setProperty(name, value) {this[name] = value;}};
        this.classList = {add: name => {this.className += ' ' + name;}, remove: name => {this.className = this.className.replace(name, '');}};
    }
    setAttribute(name, value) {this.attrs[name] = value; if (name === 'class') this.className = value;}
    getAttribute(name) {return this.attrs[name];}
    addEventListener(type,fn) {this.events[type]=fn;}
    removeEventListener(type) {delete this.events[type];}
    removeAttribute(name) {delete this.attrs[name]; if (name === 'src') this.src = '';}
    play() {this.played = true; return Promise.resolve();}
    pause() {this.paused = true;}
    load() {this.released = true;}
    appendChild(node) {node.parent = this; this.children.push(node); return node;}
    replaceChildren() {this.children = [];}
    remove() {if (this.parent) this.parent.children = this.parent.children.filter(n => n !== this);}
    set innerHTML(value) {
        this.children = [];
        for (const match of value.matchAll(/class="([^"]+)"/g)) {
            const node = new Node('div'); node.className = match[1];
            if (node.className.includes('__progress')) node.appendChild(new Node('span'));
            this.appendChild(node);
        }
    }
    querySelector(selector) {
        if (selector.endsWith(' span')) {const parent = this.querySelector(selector.slice(0,-5)); return parent && parent.children[0];}
        for (const child of this.children) {
            if (child.className.split(' ').includes(selector.slice(1))) return child;
            const nested = child.querySelector(selector); if (nested) return nested;
        }
        return null;
    }
}
const body = new Node('body');
const doc = {body, createElement: tag => new Node(tag), createElementNS: (_,tag) => new Node(tag),
    getElementById: id => body.children.find(n => n.id === id)};
const controller = createController({document:doc});
const catalog = {parts:[{part_code:'V1',name:'Part',machine_code:'virex_oracle',icon_key:'ledger_nexus',ability_code:'ability'}],
    machines:[{code:'virex_oracle',name:'VIREX ORACLE',clan_code:'virex',part_codes:['V1']}], professions:[],abilities:[]};
const manifest = {version:'ghostsignal-show-manifest-v2',nominal_duration_seconds:900, signal_confirmed:true,
    catalog,cycle_history:{available:false},assets:[{id:'machine_virex_oracle',available:true,src:'/static/images/ghostnetwork/signal_sends/machine_virex_oracle.png'}],
    scenes:[{id:'parts_enter',label:'Parts',start:0,end:360},{id:'machine_hero_1',label:'Machine',start:360,end:425},
        {id:'transmission_video',label:'Film',start:425,end:463.12},
        {id:'transmission_replay',label:'Replay',start:463.12,end:480,requires_signal_sent:true},
        {id:'aftershock',label:'World',start:480,end:900}]};
let version=0, cycle=1;
function seek(seconds) {
    const now=Date.now(),clock=Date.now;
    // A seek is one instant; CPU scheduling must not advance its render clock.
    Date.now=()=>now;
    try { controller.apply({show_active:true,cycle_number:cycle,state_version:++version,
        server_now:new Date(now).toISOString(),show_started_at:new Date(now-seconds*1000).toISOString(),
        show_ends_at:new Date(now+(900-seconds)*1000).toISOString(),show_manifest:manifest,signal_public_id:'DEMO'});
    } finally {Date.now=clock;}
}
try {
    seek(45);
    const root=doc.getElementById('ghost-signal-show');
    assert(root.querySelector('.parts-board'));
    seek(370);
    assert(!root.querySelector('.parts-board'));
    assert.strictEqual(root.querySelector('.hero-machine').attrs['data-machine'],'virex_oracle');
    assert(root.querySelector('.hero-heading'));
    assert(root.querySelector('.hero-light'));
    assert.strictEqual(root.querySelector('.hero-components').children[1].children.length,1);
    const heroCanvas=root.querySelector('.hero-machine');
    seek(371); assert.strictEqual(root.querySelector('.hero-machine'),heroCanvas,'tick preserves hero DOM');
    const img=root.querySelector('.hero-art'); assert(img);
    assert(!img.className.split(' ').includes('ghost-show-hero__image'),'legacy dimensions must not override the approved hero');
    assert(img.className.split(' ').includes('hero-image'));
    assert(root.querySelector('.hero-outline').className.split(' ').includes('hero-image'),'art and outline share geometry');
    img.onerror(); assert(!root.querySelector('.hero-art'));
    assert(root.querySelector('.ghost-show-asset-fallback'));
    manifest.assets.push({id:'ghostsignal_transmission_video',available:true,
        src:'/static/video/ghostsignal_transmission_video.mp4',duration_seconds:38.12});
    seek(435);
    assert(!root.querySelector('.hero-machine'),'video removes hero and its backdrop');
    assert.strictEqual(root.querySelector('.archive-scene').attrs['data-state'],'video');
    const video = root.querySelector('.ghost-show-video'); assert(video);
    video.duration = 38.12; video.readyState = 1; video.currentTime = 0;
    video.onloadedmetadata();
    assert(video.muted && video.playsInline && video.played);
    assert.strictEqual(video.controls, false);
    assert.strictEqual(video.tabIndex, -1);
    assert(video.disablePictureInPicture && video.disableRemotePlayback);
    assert(video.attrs.controlslist.includes('nofullscreen'));
    assert(video.parent.className.split(' ').includes('ghost-show-video-field'));
    assert(video.parent.className.split(' ').includes('archive-video-field'));
    assert.strictEqual(video.parent.parent.className,'archive-video-shell');
    assert.strictEqual(video.parent.attrs.inert, '');
    assert(Math.abs(video.currentTime - 10) < 0.1);
    seek(450);
    assert.strictEqual(root.querySelector('.ghost-show-video'), video);
    assert(Math.abs(video.currentTime - 25) < 0.1);
    seek(465);
    assert(video.paused && video.released && !video.src);
    assert(!root.querySelector('.ghost-show-video'));
    seek(430);
    const broken = root.querySelector('.ghost-show-video'); broken.onerror();
    assert(!root.querySelector('.ghost-show-video'));
    assert.strictEqual(root.querySelector('.ghost-show-video-fallback').style.display, '');
    seek(500);
    assert(root.querySelector('.world-scene'));
    assert.strictEqual(root.querySelector('.world-territory').children.length,0,'no demo triangle without archived geometry');
    assert(!root.querySelector('.ghost-show-video'));
    const stages = [[480,'aftershock'],[495,'world_before'],[525,'territory_outcomes'],[555,'territory_reduction'],
        [585,'conflict_results'],[615,'world_final'],[630,'reward_ledger'],[660,'players'],[680,'achievements'],
        [700,'clans'],[720,'system_layers'],[740,'googleplex'],[760,'pro_tools'],[780,'file_system'],
        [800,'blacknet_history'],[820,'desktop_assembly'],[835,'system_ready'],[840,'player_ranking']];
    manifest.scenes.splice(4, 1, ...stages.map((s,i) => ({start:s[0],id:s[1],label:s[1],
        end:stages[i+1] ? stages[i+1][0] : 900,requires_signal_sent:true})));
    manifest.cycle_history.settlement = {available:true,territories_total:1,area_consumed:1,
        territories:[{label:'T1',clan:'virex',geometry_available:true,points:[[21,52],[22,52],[22,53]]}],
        players_total:1,players:[{alias:'<script>unsafe()</script>',clan:'virex',rsp:7,nodes:1}],
        clans:[],conflicts:[],reward_groups:[],publications:[],rewards_total:1,rsp_total:7};
    seek(500); // Projection arrives during the same scene.
    assert(root.querySelector('.world-overlay'));
    assert.strictEqual(root.querySelector('.world-territory').children[0].attrs['data-territory'],'T1');
    const savedGlobe=root.querySelector('.world-scene');seek(500.2);
    assert.strictEqual(root.querySelector('.world-scene'),savedGlobe,'ticks do not rebuild land or geometry');
    const savedTerritories=manifest.cycle_history.settlement.territories;
    manifest.cycle_history.settlement.territories=[
        {label:'far',geometry_available:true,points:[[-160,-30],[-150,-30],[-150,-40]]},
        {label:'invalid',geometry_available:true,points:[[NaN,1],[1,2],[2,3]]},
        {label:'horizon',geometry_available:true,points:[[20,30],[140,30],[20,40]]}];
    seek(481);seek(496);
    const globePaths=root.querySelector('.world-territory').children.filter(n=>n.tag==='path');
    assert.strictEqual(globePaths.length,1);
    assert.strictEqual(globePaths[0].attrs['data-territory'],'far');
    assert.strictEqual(globePaths[0].attrs.d,'M310.00,240.00L690.00,240.00L690.00,620.00Z');
    manifest.cycle_history.settlement.territories=[{label:'tiny',geometry_available:true,points:[[1,2],[1.001,2],[1.001,1.999]]}];
    seek(481);seek(497);
    assert.strictEqual(root.querySelector('.world-territory').children[0].attrs.d,globePaths[0].attrs.d,
        'location and geographic size do not alter the symbolic outline');
    manifest.cycle_history.settlement.territories=[0,1,2].map(i=>({label:'T'+i,owner_alias:'Owner'+i,clan:'virex',geometry_available:true,points:[[1,1],[2,1],[2,2]]}));
    for(const pair of [[480.1,0],[495,0],[525,0],[529.9,0],[530,1],[555,1],[579.9,1],[580,2],[585,2],[615,2],[629.9,2]]){
        seek(pair[0]);
        assert.strictEqual(root.querySelector('.world-territory').children[0].attrs['data-territory'],'T'+pair[1],'one equal slot per territory across scene boundaries');
        assert.strictEqual(root.querySelector('.world-scene').attrs['data-view'],'territory');
    }
    manifest.cycle_history.settlement.territories=savedTerritories;
    for (const entry of stages.filter(s => s[0] >= 525 && s[0] < 840)) {
        seek(entry[0]+0.1);
        assert(root.querySelector(['system_layers','desktop_assembly','system_ready'].includes(entry[1])
            ? '.ghost-show-interface' : ['googleplex','blacknet_history'].includes(entry[1]) ? '.publications-scene' : ['pro_tools','file_system'].includes(entry[1]) ? '.archive-scene'
                : entry[1]==='reward_ledger' ? '.rewards-scene' : entry[0]<630 ? '.world-scene' : ['players','achievements','clans'].includes(entry[1]) ? '.ranking-scene' : '.ghost-show-settlement'), entry[1]);
        assert(!root.querySelector('.ghost-show-video'));
    }
    manifest.signal_confirmed = false;
    seek(650);
    assert(!root.querySelector('.ghost-show-settlement'));
    manifest.signal_confirmed = true;
    seek(850);
    assert(root.querySelector('.ranking-scene'));
    assert.strictEqual(root.querySelector('.ranking-title').children[1].textContent,'<script>unsafe()</script>');
    assert.strictEqual(root.querySelector('.ranking-position').children[1].textContent,'#01');
    const savedPlayers=manifest.cycle_history.settlement.players;
    manifest.cycle_history.settlement.players=[
        {alias:'Alpha',clan:'virex',rank:1,rsp:100,level:42,avatar:'/static/images/avatar-frakcja-1-player-1.png'},
        {alias:'Beta',clan:'echo',rank:2,rsp:50,avatar:'https://example.com/tracker.png'}];
    for(const [time,name,rank] of [[660.1,'Alpha','#01'],[679.9,'Alpha','#01'],[680,'Beta','#02'],[699.9,'Beta','#02']]){
        seek(time);
        assert.strictEqual(root.querySelector('.ranking-title').children[1].textContent,name);
        assert.strictEqual(root.querySelector('.ranking-position').children[1].textContent,rank);
        const rows=root.querySelector('.ranking-list').children[1].children;
        assert.strictEqual(rows.filter(row=>row.attrs['aria-current']==='true').length,1);
        assert.strictEqual(rows[name==='Alpha'?0:1].attrs['aria-current'],'true');
    }
    assert.strictEqual(root.querySelector('.ranking-hero').children[1].src,'/static/images/avatar-default.jpg');
    manifest.cycle_history.settlement.players=savedPlayers;
    manifest.cycle_history.settlement.reward_groups=[
        {type:'ghost_signal_node_holder',rsp:0,count:2},
        {type:'ghost_signal_closer',rsp:7,count:1},
        {type:'unknown_reward',rsp:3,count:1}];
    manifest.cycle_history.settlement.rsp_total=10;
    for(const [time,amount,index] of [[630.1,'0',0],[639.9,'0',0],[640,'7',1],[650,'3',2],[659.9,'3',2]]){
        seek(time);assert(root.querySelector('.reward-trophy'));
        assert.strictEqual(root.querySelector('.reward-value').children[0].textContent,amount);
        const rows=root.querySelector('.reward-ledger').children[1].children;
        assert.strictEqual(rows.filter(r=>r.attrs['aria-current']==='true').length,1);
        assert.strictEqual(rows[index].attrs['aria-current'],'true');
        assert.strictEqual(root.querySelector('.reward-total').children[1].textContent,'10');
    }
    manifest.cycle_history.settlement.available=false;seek(660);seek(630);
    assert.strictEqual(root.querySelector('.reward-total').children[1].textContent,'—');
    manifest.cycle_history.settlement.available=true;
    manifest.catalog=manifest.catalog||{};
    manifest.catalog.clans=[{code:'virex',name:'VIREX'},{code:'echo_freedom',name:'Echo'}];
    manifest.cycle_history.settlement.clans=[{code:'virex',rank:1,score:180,rsp:14000,members:3},{code:'echo_freedom',rank:2,score:0,rsp:4800,members:1}];
    manifest.scenes.find(s=>s.id==='player_ranking').end=855;
    manifest.scenes.push({id:'clan_ranking',start:855,end:870,label:'clans',requires_signal_sent:true},{id:'cycle_statistics',start:870,end:900,label:'stats',requires_signal_sent:true});
    for(const [time,name,position,score] of [[700.1,'VIREX','#01','180'],[709.9,'VIREX','#01','180'],[710,'Echo','#02','0'],[855.1,'VIREX','#01','180'],[862.5,'Echo','#02','0']]){
        seek(time);assert(root.querySelector('.clans-scene'));
        assert.strictEqual(root.querySelector('.ranking-title').children[1].textContent,name);
        assert.strictEqual(root.querySelector('.ranking-position').children[1].textContent,position);
        assert.strictEqual(root.querySelector('.ranking-stats').children[0].children[1].textContent,score);
        assert.strictEqual(root.querySelector('.ranking-stats').children.length,3);
        const list=root.querySelector('.ranking-list').children[1];
        assert.strictEqual(list.children.filter(r=>r.attrs['aria-current']==='true').length,1);
        const logo=root.querySelector('.ranking-hero').children[1];assert.strictEqual(logo.src,'/static/images/ghostnetwork/clans/'+(name==='VIREX'?'virex':'echo')+'_logo_pro.png');
    }
    const logo=root.querySelector('.ranking-hero').children[1];logo.onerror();assert(root.querySelector('.ranking-missing'));
    manifest.cycle_history.settlement.available=false;seek(720);seek(700);
    assert.strictEqual(root.querySelector('.ranking-title').children[1].textContent,'RANKING');
    manifest.cycle_history.settlement.available=true;
    manifest.cycle_history.settlement.publications=[
      {medium:'googleplex_news',title:'First <script>',body:'Original body',published_at:'2026-09-11T07:32:00Z'},
      {medium:'googleplex_news',title:'Second',body:'Second body',published_at:''},
      {medium:'blacknet',title:'BlackNet record',body:'Exact archival text',published_at:'2026-09-11T07:33:00Z'}];
    manifest.scenes.find(s=>s.id==='cycle_statistics').end=880;
    manifest.scenes.push({id:'archive',label:'archive',start:880,end:900,requires_signal_sent:true});
    for(const [time,title,body] of [[740.1,'First <script>','Original body'],[749.9,'First <script>','Original body'],[750,'Second','Second body'],[800.1,'BlackNet record','Exact archival text']]){
      seek(time);assert(root.querySelector('.publications-scene'));
      const content=root.querySelector('.screen-content');
      assert.strictEqual(content.children[1].textContent,title);
      assert.strictEqual(content.children[2].textContent,body);
      assert.strictEqual(root.querySelector('.publication-index').children[1].children.filter(n=>n.attrs['aria-current']==='true').length,1);
    }
    seek(880.1);assert.strictEqual(root.querySelector('.publications-scene').attrs['data-view'],'archive');
    manifest.cycle_history.settlement.publications=[];seek(740.1);
    assert(root.querySelector('.publication-dateline').textContent.includes('Brak'));
    assert(!root.querySelector('.publication-body').textContent.includes('Original body'));
    manifest.cycle_history.settlement.publications=[{medium:'googleplex_news',title:'Long',body:'A'.repeat(480),published_at:'date'}];
    seek(750);assert.strictEqual(root.querySelector('.publication-body').textContent.length,240);
    manifest.cycle_history.settlement.publications[0].body='Updated';seek(750.1);
    assert.strictEqual(root.querySelector('.publication-body').textContent,'Updated','publication arriving in same scene refreshes content');
    seek(870.1);assert(root.querySelector('.publication-statistics'));
    assert.strictEqual(root.querySelector('.publication-statistics').children[1].textContent,'1');
    const audioCalls = [];
    global.GhostRadio = {syncShow: state => audioCalls.push(state), endShow() {},
        getState: () => ({muted:false,effectiveVolume:0.5}), mute() {}, unlockShow() {}};
    manifest.audio = {show_tracks:[203.702813,210.964875,234.083250,211.304438].map((duration,i) => ({duration,
        src:'/static/audio/ghostnetwork/show/ghostsignal_show_part_0'+(i+1)+'.mp3'}))};
    global.top = {};
    seek(430);
    assert.strictEqual(audioCalls.length,0,'iframe must not own show audio');
    assert(root.querySelector('.ghost-show-video').muted);
    delete global.top;
    seek(431);
    assert.strictEqual(audioCalls.length,1);
    assert.strictEqual(root.querySelector('.ghost-show-video').muted,false,'top-level film has AAC audio');
    assert.strictEqual(root.querySelector('.ghost-show-video').volume,0.5);
    seek(430);
    const hiddenVideo = root.querySelector('.ghost-show-video'); assert(hiddenVideo);
    controller.apply({show_active:false,cycle_number:2,state_version:1,server_now:new Date().toISOString()});
    assert.strictEqual(root.style.display,'none');
    assert(hiddenVideo.paused && hiddenVideo.released && !hiddenVideo.src);
    const interfaces = ['takeover','network_layer','system_layers','desktop_assembly','system_ready','shutdown','restart'];
    cycle=2;
    const timeline = [[0,'takeover'],[15,'network_layer'],[30,'parts_complete'],[720,'system_layers'],
        [740,'googleplex'],[820,'desktop_assembly'],[835,'system_ready'],[840,'player_ranking'],[890,'shutdown'],[896,'restart']];
    manifest.scenes = timeline.map((row,i) => ({start:row[0],id:row[1],label:row[1],
        end:timeline[i+1] ? timeline[i+1][0] : 900,requires_signal_sent:row[0]>=720}));
    manifest.cycle_history.settlement = null;
    for (const row of timeline.filter(row => interfaces.includes(row[1]))) {
        seek(row[0]+1);
        const canvas = root.querySelector('.ghost-show-interface');
        assert(canvas, row[1]+' renders without settlement');
        assert.strictEqual(canvas.attrs['data-composition'],row[1]);
        assert(root.className.includes('has-interface'));
        assert(root.querySelector('.gsi-title'));
        assert.strictEqual(root.querySelector('.gsi-index').textContent,'01 /');
        assert.strictEqual(root.querySelector('.gsi-label').textContent,'INTERFEJS');
        assert.strictEqual(root.querySelector('.chaos-map-glitch-field').children.length,18);
        const stage = root.querySelector('.ghost-signal-show__stage');
        const firstLight = Number(stage.style['--gsi-light']);
        assert(Math.abs(parseFloat(stage.style['--gsi-fx-clock']) + row[0] + 1)<.05);
        assert(firstLight >= 0 && firstLight <= 1);
        seek(row[0]+2);
        assert.strictEqual(root.querySelector('.ghost-show-interface'),canvas,'tick reuses scene DOM');
        assert.notStrictEqual(Number(stage.style['--gsi-light']),firstLight,'light progresses on existing clock');
        seek(row[0]+1);
        assert(Math.abs(Number(stage.style['--gsi-light'])-firstLight)<.005,'seek restores light phase');
    }
    assert(root.querySelector('.gsi-note').textContent.includes('potwierdzeniu nowego cyklu'));
    seek(2);
    const glitch = root.querySelector('.gsi-glitch');
    assert.strictEqual(glitch.attrs['data-glitch-level'],'slow');
    const firstPosition = root.querySelector('.chaos-map-glitch-field').children[0].style['--glitch-x'];
    seek(9);
    assert.strictEqual(root.querySelector('.gsi-glitch'),glitch);
    assert.strictEqual(glitch.attrs['data-glitch-level'],'overloaded');
    seek(13);
    assert.strictEqual(glitch.attrs['data-glitch-level'],'slow');
    seek(16);seek(9);
    assert.strictEqual(root.querySelector('.gsi-glitch').attrs['data-glitch-level'],'overloaded');
    assert.strictEqual(root.querySelector('.chaos-map-glitch-field').children[0].style['--glitch-x'],firstPosition);
    assert(!root.querySelector('.ghost-show-video'));
    seek(40);
    assert(!root.querySelector('.ghost-show-interface'));
    assert(root.querySelector('.gsi-glitch'));
    assert(!root.className.includes('has-interface'));
    // Approved four-depth layout, real frozen records and lazy reveal.
    catalog.parts = ['V','E','P','S'].flatMap((prefix, group) => Array.from({length:5}, (_,i) => ({
        part_code:prefix+(i+1),name:prefix+' name '+i,icon_key:'part',machine_code:'m'+group,
        clan_code:['virex','echo_freedom','phantom_mesh','sentinel_order'][group]})));
    catalog.machines = ['V','E','P','S'].map((prefix,i) => ({code:'m'+i,name:'Machine '+prefix,
        clan_code:catalog.parts[i*5].clan_code,part_codes:catalog.parts.slice(i*5,i*5+5).map(p=>p.part_code)}));
    manifest.scenes = [[0,'takeover'],[30,'parts_enter'],[60,'parts_complete'],[90,'connections'],
        [120,'history_logs'],[140,'part_states'],[160,'machine_groups'],[720,'system_layers']].map((row,i,rows) => ({
            start:row[0],id:row[1],label:row[1],end:rows[i+1] ? rows[i+1][0] : 900,requires_signal_sent:row[0]>=720}));
    manifest.cycle_history.parts = catalog.parts.map((p,i) => ({part_code:p.part_code,status:'consumed',
        discovered_at:new Date(Date.UTC(2026,0,20-i)).toISOString(),activated_at:''}));
    manifest.cycle_history.ring_codes = catalog.parts.map(p=>p.part_code);
    seek(31);
    const partsStage=root.querySelector('.ghost-signal-show__stage');
    const rows=partsStage._partsRows;
    assert.strictEqual(rows.length,20);
    assert.strictEqual(rows.filter(r=>r.loaded).length,1,'load images only as they appear');
    assert.strictEqual(rows.filter(r=>r.card.tabIndex===0).length,1);
    const positions=rows.map(r=>[r.card.attrs['data-code'],r.card.style['--x'],r.card.style['--mx']]);
    seek(45);
    assert.strictEqual(partsStage._partsRows,rows,'reveal keeps the same DOM');
    assert.strictEqual(rows.filter(r=>r.card.style.visibility==='visible').length,10);
    assert.deepStrictEqual(rows.map(r=>[r.card.attrs['data-code'],r.card.style['--x'],r.card.style['--mx']]),positions);
    assert.strictEqual(rows.find(r=>r.card.attrs['data-code']==='V4').card.style['--x'],'104%');
    for (let depth=1;depth<=4;depth++) assert.strictEqual(rows.filter(r=>r.card.attrs['data-depth']===depth).length,5);
    seek(75);
    assert.strictEqual(partsStage._partsRows.filter(r=>r.loaded).length,20);
    partsStage._partsRows.forEach(row => {
        const src=row.card.querySelector('.ghostnetwork-part-art').src;
        assert(src.includes(row.card.attrs['data-depth']===1 ? '/superpower/' : '/parts/'),
            'only foreground loads the detailed asset');
    });
    const failed=root.querySelector('.ghostnetwork-part-art'); failed.onerror();
    assert(root.querySelector('.ghost-show-asset-fallback'));
    seek(95);
    const energy=root.querySelector('.parts-edges');
    assert.strictEqual(energy.children.filter(n=>n.className==='parts-energy-link').length,20);
    const energyLink=root.querySelector('.parts-energy-link');
    assert.strictEqual(energyLink.children.length,2,'glow and core follow the same edge');
    assert.strictEqual(energyLink.children[0].attrs.x1,energyLink.children[1].attrs.x1);
    assert.strictEqual(energy.children[0].children[0].attrs.gradientUnits,'userSpaceOnUse');
    const energyAnimation={currentTime:0}; energy.getAnimations=()=>[energyAnimation];
    seek(96);
    assert.strictEqual(root.querySelector('.parts-edges'),energy);
    assert(Math.abs(energyAnimation.currentTime-96000)<50);
    seek(121);
    assert.strictEqual(root.querySelector('.parts-records').children.length,5);
    assert(root.querySelector('.parts-history-note'),'partial history is explicit');
    const firstRecords=root.querySelector('.parts-records');
    const recordAnimations=[{currentTime:0},{currentTime:0}];
    firstRecords.getAnimations = options => {
        assert.strictEqual(options.subtree,true);
        return recordAnimations;
    };
    assert(firstRecords.children[0].children[1].textContent.includes('2026-01-20'),'retain actual partial records');
    seek(122); assert.strictEqual(root.querySelector('.parts-records'),firstRecords);
    recordAnimations.forEach(animation => assert(Math.abs(animation.currentTime-122000)<50));
    seek(121.5);
    recordAnimations.forEach(animation => assert(Math.abs(animation.currentTime-121500)<50,'seek restores OFS phase'));
    seek(126); assert.notStrictEqual(root.querySelector('.parts-records'),firstRecords);
    assert(root.querySelector('.parts-records').children[0].children[0].textContent.startsWith('E1'));
    seek(141);
    assert(root.querySelector('.parts-records').children[0].children[1].textContent.includes('consumed'));
    assert(root.querySelector('.parts-records').children[0].children[2].textContent.includes('brak zapisu'));
    seek(161);
    assert(root.querySelector('.ghost-show-parts'));
    assert(!root.querySelector('.parts-records'));
    manifest.scenes = [[0,'takeover'],[30,'parts_enter'],[60,'parts_complete'],[90,'connections'],
        [120,'history_logs'],[140,'part_states'],[160,'machine_groups'],[180,'machine_group_1'],
        [210,'machine_group_2'],[240,'machine_group_3'],[270,'machine_group_4'],[300,'network_expand'],
        [320,'network_ring'],[340,'network_tension'],[350,'network_ready'],[360,'machine_hero_1'],
        [720,'system_layers']].map((row,i,rows)=>({start:row[0],id:row[1],label:row[1],end:rows[i+1]?rows[i+1][0]:900,requires_signal_sent:row[0]>=720}));
    const startPositions=networkPositions(manifest,{elapsed:300});
    const lastGroup=machineFocusPoses(manifest,299);
    for(const code of Object.keys(startPositions))assert.deepStrictEqual(startPositions[code],lastGroup[code].values.slice(0,2));
    for(const second of [195,225,255,285]) {
        seek(second);
        assert(root.querySelector('.machine-focus'));
        const shown=partsStage._partsRows.filter(r=>r.card.attrs['data-presented']==='true');
        assert.strictEqual(shown.length,5);
        const prefix=['V','E','P','S'][Math.floor((second-180)/30)];
        assert(shown.every(r=>r.code[0]===prefix));
        assert(shown.every(r=>r.card.querySelector('.ghostnetwork-part-art').src.includes('/superpower/')));
        assert.strictEqual(partsStage._network.links.length,40);
        const count=partsStage._partsRows.filter(r=>r.card.attrs['data-presented']==='false').length;
        assert.strictEqual(count,15);
    }
    seek(240.2);
    const moving=partsStage._partsRows.find(r=>r.code==='P2');
    const atStart=moving.card.style['--x'];
    seek(240.6);assert.notStrictEqual(moving.card.style['--x'],atStart);
    seek(240.2);assert.strictEqual(moving.card.style['--x'],atStart);
    const edge=partsStage._network.links.find(e=>e.pair[0]==='P2'&&!e.portrait);
    assert(Math.abs(edge.elements[0].attrs.x1-parseFloat(atStart)*10)<.001);
    const ringPositions=networkPositions(manifest,{elapsed:320});
    for(const point of Object.values(ringPositions))assert(Math.abs(Math.hypot(point[0]-50,point[1]-50)-41)<.00001);
    assert.notDeepStrictEqual(startPositions,ringPositions);
    assert.deepStrictEqual(networkPositions(manifest,{elapsed:301.5}),ringPositions,'ring completes within 1.5 seconds');
    const networkFrames=new Map();let networkFrameId=0;
    global.requestAnimationFrame=callback=>{networkFrames.set(++networkFrameId,callback);return networkFrameId;};
    global.cancelAnimationFrame=id=>networkFrames.delete(id);
    seek(300.3);
    assert.strictEqual(networkFrames.size,1);
    const net=root.querySelector('.network-field');
    assert.strictEqual(net.style['--network-size'],'360px');
    const before=root.querySelector('.part').style['--x'];
    seek(300.9);assert.strictEqual(root.querySelector('.network-field'),net);
    assert.strictEqual(networkFrames.size,1,'tick replaces, never duplicates entrance animation');
    assert.notStrictEqual(root.querySelector('.part').style['--x'],before);
    seek(300.3);assert.strictEqual(root.querySelector('.part').style['--x'],before,'seek restores geometry');
    for(const second of [330,345,355]){
        seek(second);assert(root.querySelector('.network-square'));
        assert.strictEqual(networkFrames.size,0,'no frame loop after entrance');
        assert(root.querySelector('.network-tooltip'),'tooltip stays inside locked show root');
        assert.strictEqual(root.querySelector('.parts-edges').children.length,21);
        const row=partsStage._partsRows[0],point=ringPositions[row.code];
        assert(Math.abs(parseFloat(row.card.style['--x'])-point[0])<.0001);
    }
    const previousHelper=partsStage._networkDetails;
    seek(370);assert(!root.querySelector('.network-field'));assert(!root.querySelector('.network-tooltip'));
    assert.strictEqual(partsStage._networkDetails,null);assert(previousHelper);
    manifest.cycle_history.ring_codes=[];
    seek(330);assert(root.querySelector('.parts-history-note'));assert.strictEqual(root.querySelector('.parts-edges').children.length,0);
    seek(95);
    assert.strictEqual(root.querySelector('.parts-edges').children.length,0,'never invent a ring');
    seek(721);
    manifest.signal_confirmed=false;
    seek(722);
    assert(!root.querySelector('.ghost-show-interface'),'signal gate must remove interface layout');
    assert(!root.className.includes('has-interface'));
    manifest.signal_confirmed=true;
    const machineCodes=['virex_oracle','echo_libertas','phantom_veil','sentinel_aegis'];
    catalog.machines.forEach((machine,i)=>{
        machine.code=machineCodes[i]; machine.name=machine.code.replace('_',' ').toUpperCase();
        machine.purpose='Purpose '+i; machine.risk_extreme='Risk '+i;
        catalog.parts.filter(p=>machine.part_codes.includes(p.part_code)).forEach(p=>p.machine_code=machine.code);
    });
    manifest.assets=machineCodes.map(code=>({id:'machine_'+code,available:true,src:'/static/images/ghostnetwork/signal_sends/machine_'+code+'.png'}));
    manifest.scenes=machineCodes.map((_,i)=>({id:'machine_hero_'+(i+1),label:'Hero',start:360+i*15,end:375+i*15}));
    manifest.scenes.unshift({id:'parts_enter',label:'Parts',start:0,end:360});
    manifest.scenes.push({id:'transmission_reconstruction',label:'Transmission',start:420,end:900});
    let previousHero=null;
    for(const i of [0,1,2,3,2,1,0]) {
        seek(368+i*15);
        const hero=root.querySelector('.hero-machine');
        assert(hero && hero!==previousHero); previousHero=hero;
        assert.strictEqual(hero.attrs['data-machine'],machineCodes[i]);
        assert.strictEqual(hero.querySelector('.hero-art').src,manifest.assets[i].src);
        assert.strictEqual(hero.querySelector('.hero-outline').src,manifest.assets[i].src);
        const rows=hero.querySelector('.hero-components').children[1].children;
        assert.deepStrictEqual(rows.map(row=>row.children[1].textContent),catalog.machines[i].part_codes);
        assert.strictEqual(hero.querySelector('.hero-purpose').children[1].textContent,'Purpose '+i);
        assert.strictEqual(hero.querySelector('.hero-heading').children[1].children[0].textContent,catalog.machines[i].name.split(' ')[1]);
    }
    seek(421); assert(!root.querySelector('.hero-machine'),'transmission cleans up all machine layers');
    manifest.scenes.pop();
    manifest.scenes.push({id:'transmission_quiet',label:'Archive',start:420,end:425},
        {id:'transmission_video',label:'Video',start:425,end:463.12},
        {id:'transmission_replay',label:'Replay',start:463.12,end:900});
    manifest.assets.push({id:'ghostsignal_transmission_video',available:true,src:'/static/video/ghostsignal_transmission_video.mp4',duration_seconds:38.12});
    seek(421);
    const archive=root.querySelector('.archive-scene'); assert(archive);
    assert(!root.querySelector('.ghost-show-video'),'archive must not start video early');
    assert.strictEqual(archive.querySelector('.archive-source-light').attrs.viewBox,'0 0 1678 937');
    assert.strictEqual(archive.querySelector('.archive-source-light').attrs.preserveAspectRatio,'xMidYMid slice');
    assert.strictEqual(archive.querySelector('.archive-source-pulse').attrs.cx,'835');
    const pulseAnimation={currentTime:0}; archive.getAnimations=()=>[pulseAnimation];
    seek(423);assert.strictEqual(root.querySelector('.archive-scene'),archive);
    assert(Math.abs(pulseAnimation.currentTime-423000)<50,'archive pulse follows show clock');
    seek(426);assert.notStrictEqual(root.querySelector('.archive-scene'),archive);assert(root.querySelector('.ghost-show-video'));
    assert.strictEqual(root.querySelector('.archive-scene').attrs['data-state'],'video');
    assert(root.querySelector('.archive-video-time').textContent.startsWith('00:01'));
    seek(464);assert(root.querySelector('.archive-flash-terminal'));assert(!root.querySelector('.ghost-show-video'));
    seek(422);assert(root.querySelector('.archive-scene'));assert(!root.querySelector('.ghost-show-video'));
    manifest.scenes.pop();
    manifest.scenes.push({id:'transmission_replay',label:'Replay',start:463.12,end:466.12,requires_signal_sent:true},
        {id:'signal_point',label:'Trace',start:466.12,end:469.12,requires_signal_sent:true},
        {id:'terminal_2108',label:'2108',start:469.12,end:477,requires_signal_sent:true},
        {id:'signal_confirmation',label:'Sent',start:477,end:480,requires_signal_sent:true},
        {id:'aftershock',label:'World',start:480,end:900});
    manifest.signal_sent_at='2026-09-11T07:24:15Z';
    manifest.cycle_history.future_2108_timestamp='2108-03-04T12:00:00Z';
    seek(463.13);
    const flash=root.querySelector('.archive-flash'), terminalScene=root.querySelector('.archive-scene');
    assert(flash.style.clipPath.includes('1px'));
    seek(463.18);assert.strictEqual(flash.style.clipPath,'inset(12.5% 0 12.5% 0)');
    seek(463.26);assert.strictEqual(flash.style.clipPath,'inset(0)');assert.strictEqual(flash.style.opacity,'1');
    seek(463.80);assert(Number(flash.style.opacity)<1 && Number(flash.style.opacity)>0);
    seek(463.88);assert.strictEqual(flash.style.visibility,'hidden');
    seek(467);assert.strictEqual(root.querySelector('.archive-scene'),terminalScene);
    seek(476);assert.strictEqual(root.querySelector('.archive-scene'),terminalScene);
    const terminalText=root.querySelector('.archive-flash-terminal').children[0].textContent;
    assert(terminalText.includes(manifest.signal_sent_at));assert(terminalText.includes(manifest.cycle_history.future_2108_timestamp));
    seek(465);assert.strictEqual(root.querySelector('.archive-scene'),terminalScene);
    assert(!root.querySelector('.archive-flash-terminal').children[0].textContent.includes('2108-03-04'));
    seek(463.13);assert.strictEqual(flash.style.opacity,'1');
    manifest.signal_confirmed=false;seek(464);assert(!root.querySelector('.archive-flash'));assert(!root.querySelector('.archive-scene'));
    manifest.signal_confirmed=true;seek(477.1);assert.strictEqual(root.querySelector('.archive-flash').style.visibility,'hidden');
    seek(463);
    const tailVideo=root.querySelector('.ghost-show-video');
    tailVideo.duration=38.12;tailVideo.currentTime=37.8;tailVideo.readyState=2;tailVideo.paused=false;tailVideo.ended=false;
    seek(463.13);assert.strictEqual(root.querySelector('.ghost-show-video'),tailVideo);
    assert(!root.querySelector('.archive-flash'),'wait for actual ending before flash');
    assert.strictEqual(tailVideo.currentTime,37.8,'do not seek away the final effect');
    tailVideo.currentTime=38.12;tailVideo.ended=true;
    seek(463.45);assert(!root.querySelector('.ghost-show-video'));
    assert(root.querySelector('.archive-flash').style.clipPath.includes('1px'),'flash starts from its first frame after ended');
    seek(463);const stalled=root.querySelector('.ghost-show-video');
    stalled.duration=38.12;stalled.currentTime=37.9;stalled.readyState=2;stalled.paused=false;stalled.ended=false;
    seek(463.2);assert.strictEqual(root.querySelector('.ghost-show-video'),stalled);
    seek(470);assert(!root.querySelector('.ghost-show-video'),'seek past the finale must not wait for a stale player');
    manifest.scenes.pop();
    manifest.scenes.push({id:'aftershock',label:'World',start:480,end:760},
        {id:'pro_tools',label:'Tools',start:760,end:780,requires_signal_sent:true},
        {id:'file_system',label:'Files',start:780,end:800,requires_signal_sent:true},
        {id:'blacknet_history',label:'History',start:800,end:900});
    const screenText=()=>root.querySelector('.archive-flash-terminal').children[0].children.map(n=>n.textContent).join('\n');
    for(const [second,id] of [[479.5,'signal_confirmation'],[777,'pro_tools'],[797,'file_system']]) {
        seek(second);const screen=root.querySelector('.archive-scene');
        assert.strictEqual(screen.attrs['data-screen'],id);
        assert(root.querySelector('.archive-video-shell'));
        assert.strictEqual(root.querySelector('.archive-flash').style.visibility,'hidden','screen scenes never replay flash');
        assert(screenText().length>30);
        seek(second+.1);assert.strictEqual(root.querySelector('.archive-scene'),screen,'typewriter reuses frame');
    }
    seek(479.5);assert(screenText().includes(manifest.signal_sent_at));
    manifest.cycle_history.settlement={available:false};seek(761);seek(777);
    assert(screenText().includes('Brak zapisu'),'missing settlement is not reported as zero');
    seek(760.1);assert(screenText().length<30,'seek resets typed content');
    manifest.signal_confirmed=false;seek(778);assert(!root.querySelector('.archive-scene'));
    manifest.signal_confirmed=true;seek(801);assert(!root.querySelector('.archive-flash'));
} finally {controller.stop();delete global.GhostRadio;delete global.top;delete global.requestAnimationFrame;delete global.cancelAnimationFrame;}
console.log('ghost signal montage asset fallback/scene cleanup: PASS');
