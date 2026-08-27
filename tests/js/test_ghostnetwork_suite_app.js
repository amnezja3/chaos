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

const cardStart = source.indexOf("function ghostnetworkSuiteCard");
const cardEnd = source.indexOf("function ghostnetworkSuiteCycleStatus", cardStart);
const cardSandbox = {
    escapeHTML: value => String(value == null ? "" : value),
    TERRITORY_CONTROL_ICONS: { map: "▣", teleport: "➜" },
    String,
};
vm.createContext(cardSandbox);
vm.runInContext(source.slice(cardStart, cardEnd), cardSandbox);
const activeCard = cardSandbox.ghostnetworkSuiteCard({
    public_entity_id: "p-active",
    display_label: "AKTYWNY WEZEL GHOSTNETWORK",
    summary: "AKTYWNY WEZEL GHOSTNETWORK",
    status: "active",
    conflict_state: "none",
    location: { visibility: "exact" },
    actions: { can_show_on_map: true, can_teleport: true },
});
assert.strictEqual((activeCard.match(/AKTYWNY WEZEL GHOSTNETWORK/g) || []).length, 1, "identical label and summary must render once");
assert.doesNotMatch(activeCard, />none</, "neutral conflict sentinel must not be rendered");

const suiteStart = source.indexOf("const GHOSTNETWORK_SUITE_ENDPOINT");
const suiteEnd = source.indexOf("function appHasMapRuntime", suiteStart);
const suiteSource = source.slice(suiteStart, suiteEnd);
assert.match(suiteSource, /\/api\/ghostnetwork\/snapshot\?view=suite/);
assert.doesNotMatch(suiteSource, /\/api\/profile|\/map-action|teleport-player/);
assert.match(suiteSource, /data-app="ghostnetwork-suite"/);
assert.match(suiteSource, /TERRITORY_CONTROL_ICONS\.map/);
assert.match(suiteSource, /TERRITORY_CONTROL_ICONS\.teleport/);
assert.doesNotMatch(suiteSource, />MAPA<|>TELEPORT</);
assert.match(suiteSource, /body: JSON\.stringify\(target\)/);
assert.doesNotMatch(suiteSource, /body: JSON\.stringify\(\{[^}]*lat/s);
assert.match(suiteSource, /GHOSTNETWORK ZAMKNIETY · TRANSMISJA W TOKU/);
assert.match(suiteSource, /NOWY CYKL OCZEKUJE NA STABILIZACJE/);
assert.match(suiteSource, /const existing = document\.querySelector/);
assert.match(suiteSource, /GhostNetworkDeltaClient/);
assert.match(suiteSource, /registerAdapter/);
assert.match(suiteSource, /unregisterAdapter/);
assert.match(suiteSource, /suite_part_projection/);
assert.match(suiteSource, /scheduleGhostNetworkSuiteRecovery/);
assert.doesNotMatch(suiteSource, /setInterval\s*\(/, "Suite must not create a second poller");
assert.doesNotMatch(suiteSource, /GameSfx|playGhostNetworkDeltaSfx/, "snapshot and recovery must not play lifecycle SFX");

const recoveryStart = source.indexOf("async function recoverGhostNetworkDeltaScope");
const recoveryEnd = source.indexOf("async function recoverDeltaScopes", recoveryStart);
assert.ok(recoveryStart >= 0 && recoveryEnd > recoveryStart);
assert.match(source.slice(recoveryStart, recoveryEnd), /_ghostNetworkSuiteRecover/);
assert.doesNotMatch(source.slice(recoveryStart, recoveryEnd), /api\/profile/);

console.log("ghostnetwork suite app tests: OK");
