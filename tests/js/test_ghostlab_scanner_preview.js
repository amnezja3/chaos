const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node {
    constructor(){this.value='';this.options=[];this.dataset={};this.isConnected=true;this.events={};this.children={};this.classes=new Set();this.classList={add:k=>this.classes.add(k),remove:k=>this.classes.delete(k)};this.style={setProperty(){},removeProperty(){}};}
    addEventListener(key,fn){(this.events[key] ||= []).push(fn);}
    emit(key){for(const fn of this.events[key] || [])fn();}
    querySelector(key){return this.children[key] ||= new Node();}
    replaceChildren(){this.options=[];this.value='';}
    append(node){this.options.push(node);if(!this.value)this.value=node.value;}
    after(){}
}
const variants={regular:['sweep','ping'],pulse:['sonar','heartbeat'],wave:['tide','ripple'],viewfinder:['focus','tracking'],direct:['beam','radar']};
const schema={sfx_id:{pattern_options:{},sound_events:{}}},inputs={};
for(const [pattern,names] of Object.entries(variants)) {
    schema.sfx_id.pattern_options[pattern]=names.map(v=>pattern+'_'+v);
    for(const name of names)schema.sfx_id.sound_events[pattern+'_'+name]=`scanner.${pattern}.${name}`;
}
for(const phase of ['start','success','empty','error','denied']) {
    schema[phase+'_log']={option_labels:{preset:phase+' default'}};
    inputs[phase+'_log']=Object.assign(new Node(),{value:'preset'});
    inputs[phase+'_text']=new Node();
}
for(const [key,value] of Object.entries({pattern_id:'regular',sfx_id:'regular_ping',frame_id:'double',frame_color:'cyan',button_color:'amber'})) inputs[key]=Object.assign(new Node(),{value});
const main=new Node();main.querySelector=key=>key==='[data-ghostlab-preview-panel]'?new Node():inputs[key.match(/="(.*?)"/)[1]];
main.querySelectorAll=()=>Object.values(inputs);
let panel,observer,sequence=0,played=[],stops=0,requests=0;
const timers=new Map();
const ctx={console,Set,Map,Date,crypto:{randomUUID:()=>String(++sequence)},
    setTimeout:(fn,delay)=>{const id=++sequence;timers.set(id,{fn,delay});return id;},clearTimeout:id=>timers.delete(id),
    addEventListener(){},clearInterval(){},MutationObserver:class {constructor(fn){observer=fn;}observe(){}disconnect(){}},
    document:{body:{},createElement:tag=>tag==='section'?(panel=new Node()):new Node()},
    GameSfx:{unlock(){},play(event,options){played.push({event,options});return {stop(){stops++;}};}},
    fetch(){requests++;throw Error('preview must not fetch');}};
ctx.window=ctx;vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/js/ghostlab_scanner.js','utf8'),ctx);
ctx.mountGhostLabScannerPreview(main,{field_schema:schema});
assert.equal(inputs.sfx_id.value,'regular_ping','opening editor preserves installed sound');
for(const pattern of Object.keys(variants)) {
    inputs.pattern_id.value=pattern;inputs.pattern_id.emit('change');
    assert.deepEqual(inputs.sfx_id.options.map(o=>o.value),schema.sfx_id.pattern_options[pattern]);
    panel.querySelector('[data-visual]').onclick();
    assert.equal(panel.querySelector('.chaos-map-scan-overlay').dataset.scannerPattern,pattern);
    assert(played.at(-1).event.startsWith(`scanner.${pattern}.`));
    played.at(-1).options.on_end();
    const repeat=[...timers].find(([_,t])=>t.delay===250);assert(repeat);timers.delete(repeat[0]);repeat[1].fn();
    panel.querySelector('[data-result]').value='empty';
    const finish=[...timers].find(([_,t])=>t.delay===6000);timers.delete(finish[0]);finish[1].fn();
    assert(panel.querySelector('[data-preview-log]').textContent.includes('0 obiektów'));
    assert(!panel.querySelector('.chaos-map-scan-overlay').classes.has('is-visible'));
    assert.equal(timers.size,0);
}
panel.querySelector('[data-visual]').onclick();ctx.DeepScanner.stop();assert.equal(timers.size,0,'crash/session cleanup also stops preview');
panel.querySelector('[data-visual]').onclick();panel.isConnected=false;observer();assert.equal(timers.size,0);
assert(stops>=6);assert.equal(requests,0);
console.log('Deep Scanner five-pattern preview, sound loop, compatible choices and cleanup PASS');
