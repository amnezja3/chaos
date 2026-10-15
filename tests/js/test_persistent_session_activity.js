const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const code = fs.readFileSync(require('path').join(__dirname, '../../static/js/session_generation.js'), 'utf8');

function runtime(persistent = true) {
    const listeners = {};
    const calls = [];
    let clock = 1000000;
    const root = {
        URL, Headers, AbortController, console,
        Date: {now: () => clock},
        location: {href:'https://chaos.test/desktop', origin:'https://chaos.test', replace: url => {root.redirect = url;}},
        sessionStorage: {clear: () => {root.cleared = true;}},
        document: {
            visibilityState: 'visible',
            getElementById: () => ({textContent:JSON.stringify({generation:'gen', username:'alice',
                csrf_token:'csrf', persistent})}),
            addEventListener: (type, callback) => {listeners[type] = callback;}
        },
        fetch: async (url, init) => {
            calls.push({url, init});
            return {ok:true, status:200, headers:new Headers({'X-Chaos-Session-Generation':'gen',
                'X-Chaos-Session-User':'alice'}), json:async()=>({ok:true})};
        }
    };
    vm.runInNewContext(code, root);
    return {root, listeners, calls, advance: () => {clock += 300001;}};
}

(async () => {
    const r = runtime();
    assert.strictEqual(r.calls.length, 0, 'boot must not generate background activity');
    await r.listeners.pointerdown({isTrusted:false});
    r.root.document.visibilityState = 'hidden';
    await r.listeners.keydown({isTrusted:true});
    assert.strictEqual(r.calls.length, 0);
    r.root.document.visibilityState = 'visible';
    await r.listeners.pointerdown({isTrusted:true});
    assert.strictEqual(r.calls.length, 1);
    assert.strictEqual(r.calls[0].url, '/api/session/activity');
    assert.strictEqual(r.calls[0].init.headers.get('X-Chaos-CSRF'), 'csrf');
    await r.listeners.keydown({isTrusted:true});
    assert.strictEqual(r.calls.length, 1, 'throttle');
    r.advance();
    await r.listeners.keydown({isTrusted:true});
    assert.strictEqual(r.calls.length, 2);
    await r.root.ChaosSessionGeneration.logout();
    assert.strictEqual(r.calls[2].url, '/logout');
    assert.strictEqual(r.calls[2].init.method, 'POST');
    assert.ok(r.root.cleared);
    assert.ok(r.root.redirect.includes('session.signed_out'));
    r.advance();
    await r.listeners.keydown({isTrusted:true});
    assert.strictEqual(r.calls.length, 3, 'no activity after logout');
    assert.deepStrictEqual(Object.keys(runtime(false).listeners), []);
    console.log('Persistent activity/logout PASS');
})().catch(error => {console.error(error); process.exitCode = 1;});
