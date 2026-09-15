// Historical audit probe of the d7d477a renderer, with a minimal DOM substitute.
// No browser, network or game state. This characterizes the defect at audit time.
const vm = require('vm');
const assert = require('assert');
const source = require('child_process').execFileSync('git', ['show', 'd7d477a:static/js/terminal.js'], { encoding: 'utf8' });
const start = source.indexOf('function openSystemLogReaderApp(');
const end = source.indexOf('window.openSystemLogReaderApp', start);
let appended = false;
let rendered = false;
const sandbox = {
    document: { createElement: () => ({ style: {}, dataset: {}, querySelector: () => ({ addEventListener() {} }) }),
        body: { appendChild() { appended = true; } } },
    findAvailablePosition: () => ({ top: 0, left: 0 }),
    playerHackAccessState: {}, escapeHTML: String, formatHackAccessTime: String,
    makeDraggable() {}, appFlowTrace() {}, renderSystemLogReaderLogs() { rendered = true; }
};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);
assert.throws(() => sandbox.openSystemLogReaderApp({ logs: [] }), /id is not defined/);
assert.strictEqual(appended, true);
assert.strictEqual(rendered, false);
console.log('Confirmed: System Log Reader throws ReferenceError: id is not defined after appending window, before rendering logs.');
