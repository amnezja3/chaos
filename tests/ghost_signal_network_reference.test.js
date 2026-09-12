const assert=require('assert'),fs=require('fs'),vm=require('vm');
const html=fs.readFileSync('static/references/ghostsignal/network.html','utf8');
const metadata=html.match(/<script id="network-catalog" type="application\/json">([\s\S]*?)<\/script>/)[1];
assert.strictEqual(Object.keys(JSON.parse(metadata)).length,20);
class Element {
    constructor(){this.children=[];this.events={};this.attrs={};this.style={setProperty:(k,v)=>{this.style[k]=v;}};}
    addEventListener(k,fn){this.events[k]=fn;}
    appendChild(node){this.children.push(node);}
    replaceChildren(){this.children=[];}
    setAttribute(k,v){this.attrs[k]=v;}
    getAttribute(k){return this.attrs[k];}
    removeAttribute(k){delete this.attrs[k];}
    contains(node){return this===node||this.children.includes(node);}
    getBoundingClientRect(){return {left:240,top:600,right:260,bottom:620,width:264,height:230};}
}
const part=new Element();part.attrs['data-code']='V1';
const field=new Element();field.clientWidth=280;field.clientHeight=500;field.querySelectorAll=()=>[part];
const body=new Element(),doc=new Element(),win=new Element();
Object.assign(doc,{body,activeElement:null,querySelector:()=>field,getElementById:()=>({textContent:metadata}),createElement:()=>new Element()});
vm.runInNewContext(fs.readFileSync('static/references/ghostsignal/network-details.js','utf8'),{
    document:doc,window:win,innerWidth:280,innerHeight:650,ResizeObserver:class{observe(){}},JSON,Math
});
const tip=body.children[0];
assert.strictEqual(field.style['--network-size'],'280px');
field.clientWidth=800;field.clientHeight=450;win.events.resize();
assert.strictEqual(field.style['--network-size'],'450px');
part.events.pointerenter({pointerType:'touch'});assert(tip.hidden);
part.events.click();assert.strictEqual(tip.hidden,false);
assert.strictEqual(part.attrs['aria-describedby'],tip.id);
const values=tip.children[1].children.map(n=>n.textContent);
assert(values.includes('Ledger Nexus'));assert(values.includes('VIREX ORACLE'));
assert(values.includes('Przeplywy rynku'));
assert(parseFloat(tip.style.left)>=8&&parseFloat(tip.style.left)+264<=272);
assert(parseFloat(tip.style.top)>=8&&parseFloat(tip.style.top)+230<=642);
doc.events.keydown({key:'Escape'});assert(tip.hidden);
part.events.focus();assert(!tip.hidden);
doc.events.pointerdown({target:new Element()});assert(tip.hidden);
assert(!part.attrs['aria-describedby']);
console.log('Network reference square fit / catalog tooltip / touch / focus / Escape: PASS');
