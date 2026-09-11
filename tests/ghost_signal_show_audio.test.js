const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const {showAudioAt} = require('../static/js/ghost_signal_show.js');
const durations = [203.702813,210.964875,234.083250,211.304438];
const tracks = durations.map((duration,i) => ({duration,src:'/static/audio/ghostnetwork/show/ghostsignal_show_part_0'+(i+1)+'.mp3'}));
const snapshot = {show_active:true,signal_public_id:'S1',show_started_at:new Date(0).toISOString(),
    show_ends_at:new Date(900000).toISOString(),show_manifest:{audio:{show_tracks:tracks}}};
function at(t) {return showAudioAt(snapshot,t*1000,0);}
assert.strictEqual(at(203.702813).src,tracks[1].src);
assert.strictEqual(at(425.25).paused,false);
assert.strictEqual(at(425.5).paused,true);
assert.strictEqual(at(463.12).paused,false);
assert(Math.abs(at(425.5).offset-at(463.12).offset)<1e-8);
assert.strictEqual(at(898).src,'');
assert.strictEqual(showAudioAt({show_active:false},0,0),null);

let now=0, sequence=0;
const jobs=new Map(), audios=[];
function later(fn,delay) {const id=++sequence;jobs.set(id,{fn,time:now+(delay||0)});return id;}
function advance(ms) {
    const until=now+ms;
    for (;;) {
        const pending=Array.from(jobs.entries()).filter(item=>item[1].time<=until).sort((a,b)=>a[1].time-b[1].time)[0];
        if(!pending) break;
        jobs.delete(pending[0]);now=pending[1].time;pending[1].fn();
    }
    now=until;
}
class Audio {
    constructor(){this.dataset={};this.events={};this.paused=true;this.currentTime=0;this.duration=300;this.readyState=1;this.volume=0.8;this.muted=false;this.src='';audios.push(this);}
    addEventListener(name,fn){(this.events[name]||(this.events[name]=[])).push(fn);}
    removeEventListener(name,fn){this.events[name]=(this.events[name]||[]).filter(f=>f!==fn);}
    emit(name){for(const fn of (this.events[name]||[]).slice())fn();}
    getAttribute(){return this.src;}
    removeAttribute(){this.src='';}
    load(){this.currentTime=0;this.emit('loadedmetadata');}
    pause(){this.paused=true;this.emit('pause');}
    play(){if(this.deny)return Promise.reject(new Error('autoplay'));this.paused=false;this.emit('play');return Promise.resolve();}
}
const storage=new Map();
const context={Audio,console,Date:{now:()=>now},document:{readyState:'loading',querySelector:()=>null,addEventListener(){},removeEventListener(){}},
    setTimeout:later,clearTimeout:id=>jobs.delete(id),requestAnimationFrame:fn=>later(fn,16),cancelAnimationFrame:id=>jobs.delete(id),
    localStorage:{getItem:()=>null},sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
    fetch:async()=>({ok:true,json:async()=>({channel:{schema:1,name:'Radio'},tracks:[{file:'normal.mp3'}]})})};
context.window=context;
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/js/ghost_radio.js'),'utf8'),context);
const radio=context.GhostRadio;
(async()=>{
    await radio.playTrack('normal');
    const audio=audios[0], original=audio.src; audio.currentTime=42;
    radio.syncShow(at(425));
    assert.strictEqual(audios.length,1,'reuse existing radio element');
    assert.strictEqual(audio.src,tracks[2].src);
    assert(!audio.paused);
    advance(250);
    assert(audio.volume>0.35 && audio.volume<0.45,'half gain during 0.5 second overlap');
    advance(270);
    assert(audio.paused && audio.volume===0);
    radio.syncShow(at(463.12));
    assert.strictEqual(audio.volume,0);
    await Promise.resolve();
    advance(250);
    assert(audio.volume>0.35 && audio.volume<0.45);
    advance(270);
    assert(Math.abs(audio.volume-0.8)<1e-8);
    radio.mute(true);radio.syncShow(at(470));assert(audio.muted);
    const duck=radio.requestDuck(0.25);assert(Math.abs(audio.volume-0.2)<1e-8);duck.release();
    audio.emit('ended');assert.strictEqual(audio.src,tracks[2].src,'ended cannot advance show');
    radio.endShow();await Promise.resolve();
    assert.strictEqual(audio.src,original);assert.strictEqual(audio.currentTime,42);assert(!audio.paused);
    radio.pause();radio.syncShow(at(100));radio.endShow();assert(audio.paused,'restore paused radio');
    let reply;
    context.fetch=()=>new Promise(resolve=>{reply=resolve;});
    const lateChannel=radio.loadChannel('late');
    radio.syncShow(at(100));
    reply({ok:true,json:async()=>({channel:{schema:1},tracks:[{file:'late.mp3'}]})});
    await lateChannel;
    assert.strictEqual(audio.src,tracks[0].src,'late channel cannot replace soundtrack');
    audio.emit('error');radio.syncShow(at(110));assert(audio.paused,'missing asset stays silent');
    radio.syncShow(at(210));await Promise.resolve();assert.strictEqual(audio.src,tracks[1].src);
    radio.endShow();
    audio.deny=true;radio.syncShow(at(100));await Promise.resolve();
    assert(radio.getState().showAudioBlocked);
    audio.deny=false;radio.unlockShow();await Promise.resolve();assert(!audio.paused);
    radio.endShow(false);
    assert.strictEqual(jobs.size,0,'fade scheduling released');
    const afterBoot=Object.assign({},context);afterBoot.window=afterBoot;
    vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../static/js/ghost_radio.js'),'utf8'),afterBoot);
    assert(afterBoot.GhostRadio.getState().muted,'mute survives restart');
    afterBoot.GhostRadio.endShow();
    assert.strictEqual(await afterBoot.GhostRadio.startAutoplay(),false,'paused radio does not autoplay after restart');
    console.log('ghost signal audio timeline/fades/radio restore/autoplay: PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
