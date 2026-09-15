const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const start = source.indexOf('function renderSystemLogReaderLogs(');
const end = source.indexOf('window.openSystemLogReaderApp', start);
const list = { innerHTML: '' };
let appended = 0;
const traces = [];
const sandbox = {
    document: { createElement: () => ({ style: {}, dataset: {}, querySelector: selector =>
        selector === '.system-log-reader-list' ? list : { addEventListener() {} } }),
        body: { appendChild() { appended++; } } },
    findAvailablePosition: () => ({ top: 0, left: 0 }),
    playerHackAccessState: {}, escapeHTML: text => String(text).replace(/</g, '&lt;').replace(/>/g, '&gt;'),
    formatHackAccessTime: String, makeDraggable() {},
    appFlowTrace(_id, _event, payload) { traces.push(payload); }
};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);
sandbox.openSystemLogReaderApp({ logs: [{ title: '<script>', text: '<img onerror=x>', truncated: 1 }] });
assert.strictEqual(appended, 1);
assert.strictEqual(traces.length, 1);
assert.strictEqual(traces[0].app_id, 'systemLogReader');
assert.ok(list.innerHTML.includes('&lt;img'));
assert.ok(!list.innerHTML.includes('<script>'));
assert.ok(list.innerHTML.includes('Treść skrócona'));
sandbox.renderSystemLogReaderLogs(list, { logs: [] });
assert.ok(list.innerHTML.includes('Brak logow'));
console.log('Player hack log reader tests: OK');
