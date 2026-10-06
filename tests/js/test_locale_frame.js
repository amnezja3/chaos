'use strict';
const assert=require('node:assert/strict'), fs=require('fs'), path=require('path'), vm=require('vm');
const source=fs.readFileSync(path.resolve(__dirname,'../../static/js/ghost_i18n_frame.js'),'utf8');
function frame(child) {
  const callbacks={}, commits=[], sent=[], parent={postMessage:(data,origin)=>sent.push({data,origin})};
  const runtime={contentVersion:'153.4',getLocale:()=> 'en',getBundle:()=>({locale:'en'}),
    installBundle:bundle=>{if(bundle.invalid)throw Error('invalid');},changeLocale:async locale=>commits.push(locale)};
  const win={GhostLocale:runtime,location:{origin:'https://chaos.test'},crypto:{randomUUID:()=> 'own-nonce'},
    addEventListener:(type,handler)=>callbacks[type]=handler};
  win.parent=child?parent:win;
  const enrolled={contentWindow:parent};
  const document={querySelectorAll:()=>[enrolled],addEventListener:(type,handler)=>callbacks[type]=handler};
  vm.runInNewContext(source,{window:win,document});
  const deliver=(data,changes={})=>callbacks.message({origin:'https://chaos.test',source:parent,data,...changes});
  return {deliver,commits,sent,parent};
}
const child=frame(true);
assert.equal(child.sent[0].data.type,'ghost:locale:ready');
const commit={type:'ghost:locale:commit',nonce:'own-nonce',version:'153.4',revision:1,locale:'en',bundle:{locale:'en'}};
child.deliver(commit,{origin:'https://attacker.test'});
child.deliver(commit,{source:{}});
child.deliver({...commit,nonce:'other'});
child.deliver({...commit,version:'old'});
child.deliver({...commit,bundle:{locale:'pl'}});
child.deliver({...commit,bundle:{locale:'en',invalid:true}});
assert.deepEqual(child.commits,[]);
child.deliver(commit);
child.deliver(commit);
child.deliver({...commit,revision:0});
assert.deepEqual(child.commits,['en']);
child.deliver({...commit,revision:2,locale:'pl',bundle:{locale:'pl'}});
assert.deepEqual(child.commits,['en','pl']);
const host=frame(false);
host.deliver({type:'ghost:locale:ready',nonce:'child',version:'153.4'},{source:{}});
assert.equal(host.sent.length,0);
host.deliver({type:'ghost:locale:ready',nonce:'child',version:'153.4'});
assert.equal(host.sent.length,1);
assert.equal(host.sent[0].data.nonce,'child');
assert.equal(host.sent[0].origin,'https://chaos.test');
console.log('Locale iframe: PASS (origin, enrolled source, nonce, version, validation, monotonic revision)');
