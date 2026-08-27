"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const start = source.indexOf("function ghostnetworkSuiteIndex");
const end = source.indexOf("function ghostnetworkSuiteCard", start);
assert.ok(start >= 0 && end > start, "GhostNetwork Suite projection helpers must exist");

const sandbox = { Map, Set, String, Array, Object };
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);

const snapshot = {
    parts: [
        { public_entity_id: "p1", viewer_relation: "public", display_label: "Public", status: "public" },
        { public_entity_id: "p2", viewer_relation: "foreign_blocked", display_label: "Ukryta czesc", status: "contained", conflict_state: "contested", identity_visible: false, name: "SECRET NAME", part_code: "SECRET-CODE" },
        { public_entity_id: "p3", viewer_relation: "clan_active", display_label: "Clan active", status: "active" },
        { public_entity_id: "p4", viewer_relation: "foreign_active", display_label: "Foreign active", status: "active" },
        { public_entity_id: "p5", viewer_relation: "self_foreign", display_label: "My blocked", status: "contained" },
        { public_entity_id: "p6", viewer_relation: "self_own", display_label: "My active", status: "active" },
    ],
    groups: {
        public: ["p1"], blocked: ["p2"], clan_active: ["p3"], self_foreign: ["p5"], self_own: ["p6"]
    }
};

assert.deepStrictEqual(Array.from(sandbox.ghostnetworkSuiteSelect(snapshot, "public"), p => p.public_entity_id), ["p1"]);
assert.deepStrictEqual(Array.from(sandbox.ghostnetworkSuiteSelect(snapshot, "blocked"), p => p.public_entity_id), ["p2"]);
assert.deepStrictEqual(Array.from(sandbox.ghostnetworkSuiteSelect(snapshot, "active"), p => p.public_entity_id).sort(), ["p3", "p4"]);
assert.deepStrictEqual(Array.from(sandbox.ghostnetworkSuiteSelect(snapshot, "control"), p => p.public_entity_id).sort(), ["p5", "p6"]);
assert.strictEqual(sandbox.ghostnetworkSuiteSelect(snapshot, "all", "secret").length, 0, "search must not index hidden identity");
assert.strictEqual(sandbox.ghostnetworkSuiteSelect(snapshot, "all", "ukryta").length, 1, "search may use safe display fields");
assert.strictEqual(sandbox.ghostnetworkSuiteSelect(snapshot, "all", "", "strategic")[0].public_entity_id, "p2", "contested items must lead strategic sorting");

const suiteStart = source.indexOf("const GHOSTNETWORK_SUITE_ENDPOINT");
const suiteEnd = source.indexOf("function appHasMapRuntime", suiteStart);
const suiteSource = source.slice(suiteStart, suiteEnd);
assert.match(suiteSource, /\/api\/ghostnetwork\/snapshot\?view=suite/);
assert.doesNotMatch(suiteSource, /\/api\/profile|\/map-action|teleport-player|createMap\s*\(/);
assert.match(suiteSource, /data-app="ghostnetwork-suite"/);
assert.match(suiteSource, /<button type="button" disabled title="Dostepne od Sprintu 134" aria-label="Pokaz na mapie/);
assert.match(suiteSource, /GHOSTNETWORK ZAMKNIETY · TRANSMISJA W TOKU/);
assert.match(suiteSource, /NOWY CYKL OCZEKUJE NA STABILIZACJE/);
assert.match(suiteSource, /const existing = document\.querySelector/);

console.log("ghostnetwork suite app tests: OK");
