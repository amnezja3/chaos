// No dependencies; executable with production Node 12.
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
function fixture(broken) {
  let id = 0;
  const timers = new Map(), nodes = new Map(), listeners = new Map();
  const doc = {
    readyState: 'loading',
    addEventListener: (type, fn) => listeners.set(type, fn),
    removeEventListener: type => listeners.delete(type),
    getElementById: key => nodes.get(key),
    createElement: () => ({style: {}, classList: {add() {}, remove() {}},
      setAttribute() {}, contains: () => false,
      querySelector: () => { if (broken) throw new Error('renderer'); return {style: {}}; },
      remove() { nodes.delete(this.id); }}),
    body: {appendChild: node => nodes.set(node.id, node)}
  };
  const window = {document: doc, top: {}, Date, Promise, console: {warn() {}},
    setInterval: (fn, delay) => {timers.set(++id, {fn, delay}); return id;},
    clearInterval: key => timers.delete(key),
    setTimeout: (fn, delay) => {timers.set(++id, {fn, delay}); return id;},
    clearTimeout: key => timers.delete(key),
    addEventListener: (type, fn) => listeners.set(type, fn),
    removeEventListener: type => listeners.delete(type)};
  Object.defineProperty(window, 'localStorage', {get() {throw new Error('storage denied');}});
  vm.runInNewContext(fs.readFileSync(require.resolve('../static/js/ghost_signal_show.js'), 'utf8'), {window});
  return {window, doc, timers, nodes, listeners, create: opts => window.GhostSignalShow.createController(opts)};
}
const active = {ok: true, show_active: true, gameplay_locked: true, cycle_number: 1, state_version: 3,
  server_now: '2026-09-09T10:04:00Z', show_started_at: '2026-09-09T10:00:00Z', show_ends_at: '2026-09-09T10:15:00Z'};
async function main() {
  const f = fixture(true);
  let calls = 0, resolveRequest;
  const controller = f.create({document: f.doc, fetch: () => {calls++; return new Promise(resolve => {resolveRequest = resolve;});}});
  controller.start(); controller.start();
  await Promise.resolve();
  const first = controller.refresh(), repeat = controller.refresh();
  assert.strictEqual(first, repeat);
  assert.strictEqual(calls, 1);
  controller.apply(active);
  assert(f.nodes.has('ghost-signal-show-fallback'));
  assert.strictEqual(f.nodes.get('ghost-signal-show').style.display, 'grid');
  let blocked = 0;
  f.listeners.get('keydown')({preventDefault() {blocked++;}, stopImmediatePropagation() {blocked++;}});
  assert.strictEqual(blocked, 2);
  controller.apply(Object.assign({}, active, {show_active: false, gameplay_locked: false, state_version: 2}));
  assert.strictEqual(controller.snapshot.show_active, true);
  controller.apply(Object.assign({}, active, {show_active: false, gameplay_locked: false, server_now: '2026-09-09T10:03:00Z'}));
  assert.strictEqual(controller.snapshot.show_active, true);
  const timeout = Array.from(f.timers.values()).find(t => t.delay === 8000);
  timeout.fn(); await first;
  const recovered = controller.refresh(); await Promise.resolve();
  assert.strictEqual(calls, 2);
  resolveRequest({ok: true, json: () => Promise.resolve(Object.assign({}, active, {
    show_active: false, gameplay_locked: false, cycle_number: 2, state_version: 1,
    server_now: '2026-09-09T10:16:00Z', last_completed_signal_public_id: 'GHOSTSIGNAL-0001'}))});
  await recovered;
  assert.strictEqual(controller.snapshot.show_active, false);
  assert(!f.nodes.has('ghost-signal-show-fallback'));
  assert.strictEqual(f.nodes.get('ghost-signal-show').style.display, 'none');
  assert(f.listeners.has('online') && f.listeners.has('visibilitychange'));
  controller.stop();
  assert.strictEqual(f.timers.size, 0);
  assert(!f.listeners.has('keydown'));
  // Bootstrap also runs inside a map iframe, without waiting on its parent.
  const frame = fixture(false);
  frame.window.fetch = () => Promise.resolve({ok: true, json: () => Promise.resolve(active)});
  frame.listeners.get('DOMContentLoaded')();
  await frame.window.GhostSignalShowController.refresh();
  assert.strictEqual(frame.window.GhostSignalShowController.snapshot.show_active, true);
  frame.window.GhostSignalShowController.stop();
  const restartState = Object.assign({}, active, {show_active: false, gameplay_locked: false,
    cycle_number: 2, state_version: 1, server_now: '2026-09-09T10:16:00Z',
    client_restart: {epoch: 'epoch-next'}});
  for (let tab = 0; tab < 2; tab++) {
    const old = fixture(false);
    let closedWindows = 0, navigations = 0;
    old.window.top = old.window;
    old.window.ChaosSessionGeneration = {getState: () => ({ghost_epoch: '', query_token: 'current-session'})};
    old.window.teardownDesktopForInvalidatedSession = () => {closedWindows++;};
    old.window.location = {replace(url) {assert(url.includes('/desktop?_session_generation=current-session')); navigations++;}};
    const c = old.create({document: old.doc});
    c.apply(Object.assign({}, active, {client_restart: {epoch: 'epoch-next'}}));
    assert.strictEqual(closedWindows, 0); // Never reboot an active show.
    c.apply(restartState); c.apply(restartState);
    assert.strictEqual(closedWindows, 1);
    const navigation = Array.from(old.timers.values()).filter(t => t.delay === 750);
    assert.strictEqual(navigation.length, 1);
    navigation[0].fn();
    assert.strictEqual(navigations, 1);
    c.stop();
  }
  const boot = fixture(false);
  let ackCalls = 0;
  boot.window.ChaosSessionGeneration = {getState: () => ({ghost_epoch: 'epoch-next'})};
  boot.window.location = {replace() {throw new Error('reload loop');}};
  const bootController = boot.create({document: boot.doc, fetch: async () => {
    ackCalls++;
    return {ok: ackCalls > 1, json: async () => ({ok: true, epoch: 'epoch-next'})};
  }});
  bootController.apply(restartState);
  assert.strictEqual(bootController.snapshot.show_active, false);
  bootController.acknowledgeBoot({client_restart: {epoch: 'epoch-next'},
    restart_boot_token: 'proof', signal_registry_available: true});
  await new Promise(setImmediate);
  bootController.acknowledgeBoot();
  await new Promise(setImmediate);
  bootController.acknowledgeBoot();
  await new Promise(setImmediate);
  assert.strictEqual(ackCalls, 2); // Failed acknowledgement retries, success stops.
  bootController.stop();
  console.log('ghost signal show recovery/lock/iframe contract: PASS');
}
main().catch(error => {console.error(error); process.exitCode = 1;});
