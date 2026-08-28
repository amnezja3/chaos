const assert = require("assert");
const fs = require("fs");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const styles = fs.readFileSync("static/css/style.css", "utf8");

assert.match(source, /function createAgi2108ConsoleApp\(\)/);
assert.match(source, /app_id: 'agi2108Console'/);
assert.match(source, /approved_template_id: 'owner-analysis'/);
assert.match(source, /input: \{topic: value\}/);
assert.match(source, /maxlength="120"/);
assert.match(source, /agi2108:receipt:\$\{username\}/);
assert.match(source, /agi2108:pending:\$\{username\}/);
assert.match(source, /pendingAction\.topic === value/);
assert.match(source, /if \(submitting\) return/);
assert.match(source, /Treść pozostaje ukryta do Sprintu 135\.5/);
assert.doesNotMatch(source, /receipt\.(body|raw_output|validation|claimed_by)/);

assert.match(styles, /\.agi2108-console-window/);
assert.match(styles, /\.agi2108-shell\s*\{[^}]*overflow-y:\s*auto/s);
assert.match(styles, /@media \(max-width: 680px\), \(max-height: 600px\)/);

console.log("AGI 2108 Console frontend contract tests: OK");
