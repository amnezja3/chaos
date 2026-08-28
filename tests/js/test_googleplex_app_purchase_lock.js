"use strict";

const assert = require("assert");
const fs = require("fs");

const source = fs.readFileSync("static/js/terminal.js", "utf8");

assert.match(source, /item\.purchase_confirmation === true/);
assert.match(source, /title: "POTWIERDZENIE ZAKUPU"/);
assert.match(source, /confirmLabel: "KUP I ZAINSTALUJ"/);
assert.match(source, /const projectedApps = Array\.isArray\(\(toolbarProfile \|\| \{\}\)\.apps\)/);
assert.match(source, /projectedApps\.some\(app => String\(app\?\.id/);
assert.match(source, /"ZAINSTALOWANO"/);
assert.match(source, /if \(installInFlight\) return/);
assert.match(source, /installButton\.disabled = true/);
assert.match(source, /const staleInstalledProjection = !isProduct/);
assert.match(source, /item\.installed === true[\s\S]*&& !installed/);
assert.match(source, /walletBalance = Number\(\(toolbarProfile \|\| \{\}\)\.hackcoins/);
assert.match(source, /chaos:apps-projection-updated/);
assert.match(source, /window\.dispatchEvent\(new CustomEvent/);

console.log("Googleplex app purchase lock tests: OK");
