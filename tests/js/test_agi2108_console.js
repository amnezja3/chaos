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
const appStart = source.indexOf("function createAgi2108ConsoleApp()");
const appEnd = source.indexOf("window.createAgi2108ConsoleApp", appStart);
const appSource = source.slice(appStart, appEnd);
assert.doesNotMatch(appSource, /setInterval\s*\(/);
assert.match(appSource, /app\.isConnected && receiptId/);
assert.match(appSource, /window\.setTimeout\(loadStatus, 5000\)/);
assert.match(appSource, /if \(state === 'accepted' \|\| state === 'queued' \|\| state === 'processing'\) scheduleStatus\(\)/);
assert.match(appSource, /stopPolling\(\);[\s\S]*app\.remove\(\)/);
assert.match(source, /pendingAction\.topic === value/);
assert.match(source, /if \(submitting\) return/);
assert.match(source, /Candidate oczekuje na bezpieczną publikację/);
assert.match(source, /data\.publication && typeof data\.publication === 'object'/);
assert.match(source, /publication\.body/);
assert.doesNotMatch(source, /receipt\.(body|raw_output|validation|claimed_by)/);

assert.match(styles, /\.agi2108-console-window/);
assert.match(styles, /\.agi2108-shell\s*\{[^}]*overflow-y:\s*auto/s);
assert.match(styles, /@media \(max-width: 680px\), \(max-height: 600px\)/);

console.log("AGI 2108 Console frontend contract tests: OK");
