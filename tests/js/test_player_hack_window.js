const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
let node = null, binds = 0, interval, delayed;
function makeNode() {
    const classes = new Set();
    const content = {innerHTML: ''};
    const minimize = {addEventListener(_, fn) { this.click = fn; }};
    return {dataset: {}, style: {}, content, minimize,
        classList: {add: x => classes.add(x), remove: x => classes.delete(x), contains: x => classes.has(x)},
        querySelector(selector) {
            if (selector === '[data-player-hack-content]') return content;
            if (selector === '[data-player-hack-minimize]') return minimize;
            return {textContent: ''};
        }, querySelectorAll: () => [], remove() { node = null; }};
}
const ctx = {
    document: {getElementById: () => node, createElement: makeNode, body: {appendChild(n) { node = n; }}},
    findAvailablePosition: () => ({left: 20, top: 40}),
    makeDraggable() { binds++; }, bringWindowToFront(n) { n.classList.remove('hidden'); },
    clearInterval() {}, setInterval(fn) { interval = fn; return 1; },
    setTimeout(fn) { delayed = fn; }, formatHackAccessTime: String, escapeHTML: String,
    playerHackAccessState: null, playerHackAccessTimer: null
};
vm.createContext(ctx);
vm.runInContext(source.slice(source.indexOf('function getPlayerHackAccessPanel()'), source.indexOf('async function refreshPlayerHackAccess(')), ctx);
const access = {active: true, victim_username: 'a', seconds_left: 5, tools: []};
ctx.renderPlayerHackAccessPanel(null);
assert.equal(node, null, 'inactive access does not create a window');
ctx.renderPlayerHackAccessPanel(access);
const first = node;
ctx.renderPlayerHackAccessPanel({...access,tools:[
    {id:'missing-parent',name:'Absent parent',installed:false},
    {id:'child',name:'Own child',icon:'🐍',installed:true,enabled:false,disabled_reason:'Runtime pending'}
]});
assert(!node.content.innerHTML.includes('Absent parent'));
assert(node.content.innerHTML.includes('Own child'));
assert(node.content.innerHTML.includes('🐍'));
ctx.renderPlayerHackAccessPanel(access);
assert(node.content.innerHTML.includes('Brak zainstalowanych'));
node.style.left = '210px';
node.minimize.click();
ctx.renderPlayerHackAccessPanel(access);
assert.equal(node, first);
assert.equal(node.style.left, '210px');
assert(node.classList.contains('hidden'), 'refresh does not undo minimization');
assert.equal(binds, 1, 'stable title bar binds once');
ctx.renderPlayerHackAccessPanel({...access, victim_username: 'b', seconds_left: 1});
assert(!node.classList.contains('hidden'));
interval();
ctx.renderPlayerHackAccessPanel({...access, victim_username: 'c'});
delayed();
assert.equal(node, first, 'old expiry must not close a new grant');
ctx.renderPlayerHackAccessPanel(null);
assert.equal(node, null);
console.log('Player hack application window lifecycle: PASS');
