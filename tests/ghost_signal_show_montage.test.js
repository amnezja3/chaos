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
let version=0;
function seek(seconds) {
    const now=Date.now(); controller.apply({show_active:true,cycle_number:1,state_version:++version,
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
    assert.strictEqual(root.querySelector('.ghost-signal-show__stage').children.length,0);
    seek(430);
    const hiddenVideo = root.querySelector('.ghost-show-video'); assert(hiddenVideo);
    controller.apply({show_active:false,cycle_number:2,state_version:1,server_now:new Date().toISOString()});
    assert.strictEqual(root.style.display,'none');
    assert(hiddenVideo.paused && hiddenVideo.released && !hiddenVideo.src);
} finally {controller.stop();}
console.log('ghost signal montage asset fallback/scene cleanup: PASS');
