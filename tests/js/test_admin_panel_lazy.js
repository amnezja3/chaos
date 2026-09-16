const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.attributes={};this.value='';this.textContent='';}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=nodes;}
 setAttribute(k,v){this.attributes[k]=v;}
 add(option){this.append(option);}
 querySelectorAll(tag){return this.children.flatMap(c=>[...(c.tag===tag?[c]:[]),...c.querySelectorAll(tag)]);}
}
const ids=Object.fromEntries(['listing','detail','notice','search','prev','next','page-label','search-form'].map(id=>[id,new Element('div')]));
const pending=[];
const ctx={window:{adminSection:'users'},document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag)},
 URLSearchParams,Option:class extends Element {constructor(text,value){super('option');this.textContent=text;this.value=value;}},
 fetch:(url,options)=>new Promise(resolve=>pending.push({url,options,resolve}))};
vm.createContext(ctx);vm.runInContext(fs.readFileSync('static/js/admin_panel.js','utf8'),ctx);
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function respond(request,data){request.resolve({ok:true,status:200,json:async()=>({success:true,...data})});}
function user(username){return {user:{username,nick:username},profession:{choices:[{code:'broker',name:'Broker'}],selected:{code:'broker'}},security:{firewall:true}};}
(async()=>{
 assert.equal(pending.length,1,'Shell loads only list');
 respond(pending.shift(),{items:[{username:'a'},{username:'b'}],has_more:false});await flush();
 const buttons=ids.listing.querySelectorAll('button');buttons[0].onclick();buttons[1].onclick();
 const a=pending.shift(),b=pending.shift();assert(b.url.includes('username=b'));
 respond(b,user('b'));await flush();respond(a,user('a'));await flush();
 assert.equal(ids.detail.children[0].textContent,'b','Late A must not replace selected B');
 assert.equal(pending.length,0,'Resources are not fetched before category selection');
 const apps=ids.detail.querySelectorAll('button').find(n=>n.textContent==='Aplikacje');apps.onclick();
 assert(pending[0].url.includes('section=apps')&&pending[0].url.includes('username=b'));
 respond(pending.shift(),{items:[],has_more:false});await flush();
 const form=ids.detail.querySelectorAll('form')[0];form.onsubmit({preventDefault(){}});
 assert.equal(pending[0].options.method,'POST');assert.equal(JSON.parse(pending[0].options.body).username,'b');
 respond(pending.shift(),{});await flush();assert(pending[0].url.includes('username=b'));
 respond(pending.shift(),user('b'));await flush();
 console.log('Admin lazy list, selection race, resource scope and profession save: PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
