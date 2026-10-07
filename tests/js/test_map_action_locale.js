'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'../..');
const source=fs.readFileSync(path.join(root,'templates/map_template.html'),'utf8');
const menu=source.slice(source.indexOf('function showHackingMenuForMarker('),source.indexOf('// function showHackingMenuForMarker('));
class Element {
  constructor(){this.children=[];this.dataset={};this.style={};this.events={};}
  appendChild(n){this.children.push(n);}
  addEventListener(type,handler){this.events[type]=handler;}
}
const cases={camera:['camera_stream','camera_shutdown'],person:['trace_device','mic_sniff'],phone:['trace_device','mic_sniff'],car:['car_hack','trace_gps'],vehicle:['car_hack','trace_gps'],atm:['atm_logs','install_sniffer'],restaurant:['scan_hotspots','audio_hack'],parking:['scan_ports','exploit','sniff','trace']};
const captured={};
for(const locale of ['pl','en']){
 const body=new Element(),calls=[];
 const sandbox=vm.createContext({document:{createElement:()=>new Element(),body},guardMapGameplayAction:()=>false,
  normalizeMapMenuTarget:x=>({...x}),closeMenus:()=>{body.children=[];},setupGlobalCloseListener:()=>{},
  hackingAction:(...args)=>calls.push(args),aimMapTargetOnly:()=>{},escapeMapText:s=>String(s).replaceAll('<','&lt;').replaceAll('>','&gt;')});
 require('./locale_fixture')(sandbox,locale);
 vm.runInContext(menu,sandbox);
 for(const [type,expected] of Object.entries(cases)){
  const target={source_type:type,lat:1,lon:2,label:'UGC <keep>',name:'UGC <keep>',icon:'X',target_id:'stable:'+type};
  sandbox.showHackingMenuForMarker(1,2,target,'X',target.label);
  const rows=body.children[0].children.slice(2);
  assert.deepEqual(rows.map(n=>n.dataset.ghostI18n),expected.map(a=>'map.action.'+a));
  assert.match(body.children[0].children[0].innerHTML,/UGC &lt;keep&gt;/);
  for(const row of rows)row.events.click({preventDefault(){},stopPropagation(){}});
  assert.deepEqual(calls.slice(-rows.length).map(args=>args[0]),expected);
  assert.equal(target.label,'UGC <keep>');
 }
 captured[locale]=calls.map(args=>args.filter((_,index)=>index!==13)); // DOM busy control is not a gameplay value.
}
assert.deepEqual(JSON.parse(JSON.stringify(captured.pl)),JSON.parse(JSON.stringify(captured.en)));
console.log('Map action locale: PASS (8 target categories, stable action payloads, escaped UGC)');
