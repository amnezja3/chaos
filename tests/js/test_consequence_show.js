const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('static/js/consequence_show.js','utf8');
const flush = async () => {for (let i=0;i<12;i++) await Promise.resolve();};
function setup(mode='audio', stage=5) {
    let requests=0, stopped=0, dialog=0, audio;
    const nodes=[], timers=new Map(); let sequence=0;
    const doc={createElement: () => ({style:{},append(){},remove(){const i=nodes.indexOf(this);if(i>=0)nodes.splice(i,1);}}),
        querySelector: selector => selector === '.leaflet-container' ? {} : null,
        body:{appendChild: el => nodes.push(el)}};
    const frame={getClientRects:()=>[{}],contentDocument:doc,contentWindow:{applyDetentionView(){}}};
    const state={document:{visibilityState:'visible',querySelectorAll:()=>mode==='closed'?[]:[frame]},
        console, setTimeout:(fn,ms)=>{timers.set(++sequence,{fn,ms});return sequence;}, clearTimeout:id=>timers.delete(id),
        setInterval:()=>99,clearInterval:()=>{},
        fetch:async()=>{requests++;return {ok:true,json:async()=>({show:{encounter_id:'receipt',stage,effects:{fine_hc:93,tool_ids:['a','b','c'],sanction_id:stage>=6?'s':null}}})};},
        window:{DetentionUI:{state:{sanction_id:'s'},blockedAction:async()=>{dialog++;}},GameSfx:{play:(key,opts)=>{
            audio=opts; return {stop:()=>{stopped++;}, started:mode==='muted'?Promise.resolve({ok:false}):new Promise(()=>{})};
        }}}};
    vm.runInNewContext(source,state);
    return {state,nodes,timers,get audio(){return audio;},get requests(){return requests;},get stopped(){return stopped;},get dialog(){return dialog;}};
}
(async()=>{
    const t=setup(); t.state.window.ConsequenceShow.receive({encounter_id:'receipt'}); await flush();
    assert.equal(t.nodes.length,0,'visual waits for actual audio start');
    t.audio.on_start(); assert.equal(t.nodes.length,1); assert(t.nodes[0].className.includes('is-visible'));
    assert.equal(t.timers.size,0,'audible show follows ended, not an independent hold');
    t.audio.on_end(); await flush(); assert.equal(t.nodes.length,0);
    t.state.window.ConsequenceShow.receive({encounter_id:'receipt'}); await flush(); assert.equal(t.requests,1);
    const mute=setup('muted',7); mute.state.window.ConsequenceShow.receive({encounter_id:'receipt'}); await flush();
    assert.equal(mute.nodes.length,1); assert.equal(mute.stopped,1);
    const timer=[...mute.timers.values()][0]; assert.equal(timer.ms,1253.875);
    timer.fn(); await flush(); assert.equal(mute.nodes.length,0); assert.equal(mute.dialog,1);
    const pending=setup(); pending.state.window.ConsequenceShow.receive({encounter_id:'receipt'}); await flush();
    [...pending.timers.values()][0].fn(); assert.equal(pending.stopped,1,'timeout cancels late audio');
    const closed=setup('closed',6); closed.state.window.ConsequenceShow.receive({encounter_id:'receipt'}); await flush();
    assert.equal(closed.nodes.length,0); assert.equal(closed.dialog,1,'closed map still receives verdict');
    const hidden=setup(); hidden.state.document.visibilityState='hidden';
    hidden.state.window.ConsequenceShow.receive({encounter_id:'receipt'}); await flush(); assert.equal(hidden.requests,0);
    console.log('consequence audio sync, mute fallback, dedupe and closed map: OK');
})().catch(error=>{console.error(error);process.exitCode=1;});
