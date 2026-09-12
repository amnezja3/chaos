const assert = require('assert');
const {createController} = require('../static/js/ghost_signal_show.js');
class Node {
    constructor(tag) {
        this.tag = tag; this.children = []; this.attrs = {}; this.className = '';
        this.style = {setProperty(name, value) {this[name] = value;}};
        this.classList = {add: name => {this.className += ' ' + name;}, remove: name => {this.className = this.className.replace(name, '');}};
    }
    setAttribute(name, value) {this.attrs[name] = value;}
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
    const now=Date.now(); controller.apply({show_active:true,cycle_number:cycle,state_version:++version,
        server_now:new Date(now).toISOString(),show_started_at:new Date(now-seconds*1000).toISOString(),
        show_ends_at:new Date(now+(900-seconds)*1000).toISOString(),show_manifest:manifest,signal_public_id:'DEMO'});
}
try {
    seek(45);
    const root=doc.getElementById('ghost-signal-show');
    assert(root.querySelector('.ghost-show-board'));
    seek(370);
    assert(!root.querySelector('.ghost-show-board'));
    const img=root.querySelector('.ghost-show-hero__image'); assert(img);
    img.onerror(); assert(!root.querySelector('.ghost-show-hero__image'));
    assert(root.querySelector('.ghost-show-asset-fallback'));
    manifest.assets.push({id:'ghostsignal_transmission_video',available:true,
        src:'/static/video/ghostsignal_transmission_video.mp4',duration_seconds:38.12});
    seek(435);
    const video = root.querySelector('.ghost-show-video'); assert(video);
    video.duration = 38.12; video.readyState = 1; video.currentTime = 0;
    video.onloadedmetadata();
    assert(video.muted && video.playsInline && video.played);
    assert.strictEqual(video.controls, false);
    assert.strictEqual(video.tabIndex, -1);
    assert(video.disablePictureInPicture && video.disableRemotePlayback);
    assert(video.attrs.controlslist.includes('nofullscreen'));
    assert.strictEqual(video.parent.className, 'ghost-show-video-field');
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
    assert(root.querySelector('.ghost-show-settlement'));
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
    assert(root.querySelector('.ghost-show-settlement-map'));
    for (const entry of stages.filter(s => s[0] >= 525 && s[0] < 840)) {
        seek(entry[0]+0.1);
        assert(root.querySelector(['system_layers','desktop_assembly','system_ready'].includes(entry[1])
            ? '.ghost-show-interface' : '.ghost-show-settlement'), entry[1]);
        assert(!root.querySelector('.ghost-show-video'));
    }
    manifest.signal_confirmed = false;
    seek(650);
    assert(!root.querySelector('.ghost-show-settlement'));
    manifest.signal_confirmed = true;
    seek(850);
    assert(root.querySelector('.ghost-show-settlement'));
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
        seek(row[0]+2);
        assert.strictEqual(root.querySelector('.ghost-show-interface'),canvas,'tick reuses scene DOM');
    }
    assert(root.querySelector('.gsi-note').textContent.includes('potwierdzeniu nowego cyklu'));
    assert(!root.querySelector('.ghost-show-video'));
    seek(40);
    assert(!root.querySelector('.ghost-show-interface'));
    assert(!root.className.includes('has-interface'));
    seek(721);
    manifest.signal_confirmed=false;
    seek(722);
    assert(!root.querySelector('.ghost-show-interface'),'signal gate must remove interface layout');
    assert(!root.className.includes('has-interface'));
} finally {controller.stop();delete global.GhostRadio;delete global.top;}
console.log('ghost signal montage asset fallback/scene cleanup: PASS');
