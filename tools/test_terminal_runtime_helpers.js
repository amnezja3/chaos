const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('static/js/terminal.js', 'utf8');

function extractFunction(name) {
  const start = source.indexOf(`function ${name}`);
  if (start < 0) throw new Error(`Missing function: ${name}`);
  const braceStart = source.indexOf('{', start);
  let depth = 0;
  for (let index = braceStart; index < source.length; index += 1) {
    const char = source[index];
    if (char === '{') depth += 1;
    if (char === '}') depth -= 1;
    if (depth === 0) {
      return source.slice(start, index + 1);
    }
  }
  throw new Error(`Unclosed function: ${name}`);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(
  [
    extractFunction('normalizeButtonChoiceOption'),
    extractFunction('escapeHTML'),
    'this.normalizeButtonChoiceOption = normalizeButtonChoiceOption;',
    'this.escapeHTML = escapeHTML;',
  ].join('\n'),
  sandbox
);

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(`${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

assertEqual(sandbox.escapeHTML({ label: 'Test <x>' }), 'Test &lt;x&gt;', 'escapeHTML object label');
assertEqual(sandbox.escapeHTML(null), '', 'escapeHTML null');
assertEqual(sandbox.escapeHTML(42), '42', 'escapeHTML number');

const stringOption = sandbox.normalizeButtonChoiceOption('Recon', 0);
assertEqual(stringOption.label, 'Recon', 'string option label');
assertEqual(stringOption.id, 0, 'string option id');

const objectOption = sandbox.normalizeButtonChoiceOption({ title: 'Tryb <safe>', action: 'run' }, 2);
assertEqual(objectOption.label, 'Tryb <safe>', 'object option title label');
assertEqual(objectOption.action, 'run', 'object option action');
assertEqual(sandbox.escapeHTML(objectOption), 'Tryb &lt;safe&gt;', 'object option escapes through label');

console.log('terminal runtime helper tests passed');
