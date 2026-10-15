const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const handlers = {}, cached = [], writes = [];
const cache = {put: async (url) => writes.push(url), match: async () => 'neutral-offline'};
const context = {URL, Request, Response, caches:{open:async()=>cache,match:async()=> 'neutral-offline',keys:async()=>[],delete:async()=>{}},
    fetch: async request => {cached.push(request); return {ok:true,redirected:false};},
    self:{location:{origin:'https://chaos.re'},addEventListener:(name,fn)=>handlers[name]=fn}};
// Node requires absolute Request URLs, browsers resolve these against the worker.
context.Request = class extends Request {constructor(url, options){super(new URL(url,'https://chaos.re'),options);}};
vm.runInNewContext(fs.readFileSync('static/pwa/worker.js','utf8'),context);
(async()=>{
    let task; handlers.install({waitUntil:p=>task=p}); await task;
    assert.equal(writes.length,5);
    assert(cached.every(r=>r.credentials==='omit'));
    for(const [path,method,mode] of [['/api/session/status','GET','cors'],['/api/desktop-shell','GET','cors'],['/api/buy','POST','cors'],['/map','GET','navigate'],['/static/pwa/offline.html?user=alice','GET','cors']]){
        let handled=false;
        handlers.fetch({request:{url:'https://chaos.re'+path,method,mode},respondWith:()=>handled=true});
        assert.equal(handled,false,path);
    }
    context.fetch=async()=>{throw new Error('offline');};
    let result; handlers.fetch({request:{url:'https://chaos.re/launch',method:'GET',mode:'navigate'},respondWith:p=>result=p});
    assert.equal(await result,'neutral-offline');
    console.log('Installation worker isolation PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
