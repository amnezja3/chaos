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

function extractConst(name) {
  const start = source.indexOf(`const ${name}`);
  if (start < 0) throw new Error(`Missing const: ${name}`);
  const end = source.indexOf(';\n', start);
  if (end < 0) throw new Error(`Unclosed const: ${name}`);
  return source.slice(start, end + 1);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(
  [
    'let toolbarTargetFeedbackState = { targetKey: "", dotSignature: "", progress: 0 };',
    extractConst('TARGET_FEEDBACK_ACTION_KEYS'),
    extractConst('TARGET_FEEDBACK_SECURITY_KEYS'),
    extractFunction('normalizeButtonChoiceOption'),
    extractFunction('escapeHTML'),
    extractFunction('targetFeedbackClampPercent'),
    extractFunction('hasToolbarAimedTarget'),
    extractFunction('getTargetFeedbackKey'),
    extractFunction('getTargetActionDots'),
    extractFunction('calculateTargetDisarmProgress'),
    extractFunction('resolveTargetBarFeedback'),
    'this.normalizeButtonChoiceOption = normalizeButtonChoiceOption;',
    'this.escapeHTML = escapeHTML;',
    'this.hasToolbarAimedTarget = hasToolbarAimedTarget;',
    'this.getTargetActionDots = getTargetActionDots;',
    'this.calculateTargetDisarmProgress = calculateTargetDisarmProgress;',
    'this.resolveTargetBarFeedback = resolveTargetBarFeedback;',
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

assertEqual(sandbox.hasToolbarAimedTarget({}), false, 'empty aimed target is neutral');
assertEqual(sandbox.hasToolbarAimedTarget({ lat: 0, lng: 0, label: '', name: '' }), false, 'template aimed target coordinates are neutral');
assertEqual(sandbox.hasToolbarAimedTarget({ lat: 52.1, lng: 21.2, label: 'POI-1' }), true, 'labeled aimed target is active');
assertEqual(sandbox.calculateTargetDisarmProgress({}), 0, 'missing security progress is zero');

const feedbackTarget = {
  lat: 52.1,
  lng: 21.2,
  label: 'POI',
  actions_allowed: { scan_ports: true, exploit: false, sniff: true, trace: false },
  security: {
    stealth_mode: false,
    scan_detection: false,
    exploit_protection: true,
    vpn_enabled: true,
    anonymity_score: 99,
    access_level: 4
  }
};
const dots = sandbox.getTargetActionDots(feedbackTarget);
assertEqual(dots.map(dot => dot.active).join(','), 'true,false,true,false', 'actions map to fixed dots');
assertEqual(sandbox.calculateTargetDisarmProgress(feedbackTarget), 50, 'numeric security fields ignored');

const firstFeedback = sandbox.resolveTargetBarFeedback(feedbackTarget);
assertEqual(firstFeedback.progress, 50, 'initial feedback progress');
const staleFeedback = sandbox.resolveTargetBarFeedback({
  ...feedbackTarget,
  security: { stealth_mode: true, scan_detection: true, exploit_protection: true, vpn_enabled: true }
});
assertEqual(staleFeedback.progress, 50, 'same target progress is monotonic');
const nextTargetFeedback = sandbox.resolveTargetBarFeedback({
  ...feedbackTarget,
  lat: 52.2,
  security: { stealth_mode: true, scan_detection: true, exploit_protection: true, vpn_enabled: true }
});
assertEqual(nextTargetFeedback.progress, 0, 'new target resets progress');
assertEqual(nextTargetFeedback.targetChanged, true, 'new target marks target change');

console.log('terminal runtime helper tests passed');
