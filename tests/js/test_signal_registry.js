const assert = require("assert");
const fs = require("fs");

const terminal = fs.readFileSync("static/js/terminal.js", "utf8");
const styles = fs.readFileSync("static/css/style.css", "utf8");

assert.match(terminal, /signal_registry_available === true/);
assert.match(terminal, /label: 'Signal Registry'/);
assert.match(terminal, /\/api\/ghostnetwork\/rankings\?limit=50/);
assert.match(terminal, /\/api\/ghostnetwork\/rankings\/all-time/);
assert.match(terminal, /IMMUTABLE \/\/ REBUILDABLE/);
assert.match(terminal, /createGhostSignalArchiveApp/);
assert.match(styles, /\.ghostsignal-ranking-grid/);
assert.match(styles, /\.ghostsignal-ranking-row/);

console.log("signal registry frontend contract: OK");
