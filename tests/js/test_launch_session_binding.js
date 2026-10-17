const assert = require('assert');
const vm = require('vm');
const fs = require('fs');
const source = fs.readFileSync(require('path').join(__dirname, '../../static/js/session_generation.js'), 'utf8');

function setup() {
    const storage = new Map([['private-profile', 'old data']]);
    const listeners = {};
    const sent = [];
    const child = {postMessage: (...args) => sent.push(args)};
    let result = {ok:true, status:200, headers:new Headers({'X-Chaos-Session-Generation':'generation-a',
        'X-Chaos-Session-User':'alice'}), json:async()=>({ok:true, authenticated:true})};
    const root = {
        URL, Headers, AbortController, console, setTimeout, clearTimeout,
        location: {href:'https://chaos.test/launch', origin:'https://chaos.test', replace() {}},
        sessionStorage: {getItem:k=>storage.get(k), setItem:(k,v)=>storage.set(k,v), clear:()=>storage.clear()},
        addEventListener: (name, fn) => { listeners[name] = fn; },
        document: {
            visibilityState: 'visible',
            getElementById: () => ({textContent:JSON.stringify({generation:'generation-a', username:'alice',
                csrf_token:'csrf', launch_enabled:true, launch_binding:'binding-a'})}),
            addEventListener: (name, fn) => { listeners[name] = fn; },
            querySelectorAll: selector => selector === 'iframe' ? [{contentWindow: child}] : [],
        },
        fetch: async () => { if (result instanceof Error) throw result; return result; },
    };
    root.parent = root;
    vm.runInNewContext(source, root);
    return {root, storage, listeners, child, sent, setResult: r => {result = r;}};
}

(async () => {
    const adult = setup();
    let adultRedirect;
    adult.root.location.replace = value => {adultRedirect = value;};
    adult.setResult({status:403,ok:false,json:async()=>({error:'adult_acceptance_required'})});
    await adult.listeners.visibilitychange();
    assert.equal(adultRedirect,'/account/terms','warm PWA resumes into acceptance gate');
    assert.equal(adult.root.ChaosSessionGeneration.getState().invalidated,false);
    assert.equal(adult.storage.get('chaos-launch-binding-v1'),'binding-a');
    const r = setup();
    assert.equal(r.storage.get('chaos-launch-binding-v1'), 'binding-a');
    const event = {origin:'https://chaos.test', source:r.child, data:{type:'chaos:launch-request', nonce:'test'}};
    r.listeners.message({...event, origin:'https://evil.test'});
    r.listeners.message({...event, source:{}});
    assert.equal(r.sent.length, 0, 'reject foreign origins and non-child windows');
    r.listeners.message(event);
    assert.equal(r.sent.length, 1);
    assert.equal(r.sent[0][0].context.generation, 'generation-a');
    assert.equal(r.sent[0][1], 'https://chaos.test');
    r.setResult(new Error('offline'));
    await r.listeners.visibilitychange();
    assert.equal(r.root.ChaosSessionGeneration.getState().invalidated, false);
    r.setResult({ok:false, status:409});
    await r.listeners.visibilitychange();
    assert.equal(r.root.ChaosSessionGeneration.getState().invalidated, true);
    assert.equal(r.storage.get('chaos-launch-binding-v1'), 'binding-a', 'reload cannot adopt newer cookie');
    assert.equal(r.storage.has('private-profile'), false);
    r.listeners.message(event);
    assert.equal(r.sent[1][0].context, null, 'invalidated parent cannot give a frame credentials');
    const logout = setup();
    await logout.root.ChaosSessionGeneration.logout();
    assert.equal(logout.storage.size, 0, 'explicit logout clears all local data');
    console.log('Launch binding, frame handshake, resume and teardown PASS');
})().catch(error => { console.error(error); process.exitCode = 1; });
