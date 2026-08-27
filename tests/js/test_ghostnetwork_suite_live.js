"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const start = source.indexOf("const GHOSTNETWORK_SUITE_SECTIONS");
const end = source.indexOf("function ghostnetworkSuiteCard", start);
assert.ok(start >= 0 && end > start, "Suite live projection helpers must exist");

let renders = 0;
const sandbox = {
    Set, Map, String, Number, Array, Object, Date, Math,
    renderGhostNetworkSuite: () => { renders += 1; },
};
vm.createContext(sandbox);
vm.runInContext(source.slice(start, end), sandbox);

const fullPart = {
    public_entity_id: "ghost-node:one",
    part_id: "secret-part",
    name: "SECRET NAME",
    part_code: "SECRET-CODE",
    machine_code: "SECRET-MACHINE",
    profession_code: "SECRET-PROFESSION",
    ability_code: "SECRET-ABILITY",
    visual_asset_url: "/secret.png",
    identity_visible: true,
    ability_visible: true,
    viewer_relation: "self_foreign_blocked",
    module_state: "blocked",
    status: "contained",
    conflict_state: "none",
    location_visibility: "exact",
    latitude: 52.2,
    longitude: 21.0,
    territory_id: "territory-one",
    territory_owner_id: "alice",
    territory_clan: "virex",
    owner: { owner_id: "alice", owner_alias: "Alice", owner_clan: "virex" },
    location: { visibility: "exact", latitude: 52.2, longitude: 21.0 },
    actions: { can_show_on_map: true, can_teleport: true },
};
const state = {
    closed: false,
    restartRequired: false,
    snapshot: {
        cycle: { cycle_id: "cycle-135", status: "active" },
        state_version: 10,
        parts: [fullPart],
        connections: [],
    },
};
const app = { isConnected: true };

const hiddenProjection = {
    public_entity_id: "ghost-node:one",
    part_id: null,
    name: null,
    part_code: null,
    machine_code: null,
    profession_code: null,
    ability_code: null,
    visual_asset_url: null,
    marker_asset_url: "/classified.png",
    display_label: "TERYTORIUM ZAWIERA CZESC GHOSTNETWORK",
    summary: "TERYTORIUM ZAWIERA CZESC GHOSTNETWORK",
    identity_visible: false,
    ability_visible: false,
    viewer_relation: "foreign_blocked",
    module_state: "blocked",
    status: "contained",
    conflict_state: "none",
    location_visibility: "territory_only",
    latitude: null,
    longitude: null,
    territory_id: "territory-one",
    territory_owner_id: "alice",
    territory_clan: "virex",
    can_show_on_map: true,
};
assert.strictEqual(sandbox.ghostnetworkSuiteApplyDelta(app, state, {
    scope: "ghostnetwork",
    type: "ghost.part_contained",
    entity_id: "ghost-node:one",
    payload: {
        cycle_id: "cycle-135", state_version: 11,
        suite_part_projection: hiddenProjection,
    },
}), true);
const hidden = state.snapshot.parts[0];
assert.strictEqual(hidden.identity_visible, false);
assert.strictEqual(hidden.part_id, null);
assert.strictEqual(hidden.location.latitude, null);
assert.strictEqual(hidden.actions.map_target_type, "ghostnetwork_territory");
assert.strictEqual(hidden.actions.map_target_id, "territory-one");
assert.strictEqual(hidden.owner.owner_alias, "Alice", "unchanged owner alias may survive the projection replacement");
const hiddenJson = JSON.stringify(hidden);
["SECRET NAME", "SECRET-CODE", "SECRET-MACHINE", "SECRET-PROFESSION", "SECRET-ABILITY", "/secret.png"]
    .forEach(secret => assert.ok(!hiddenJson.includes(secret), `hidden delta must purge ${secret}`));
assert.deepStrictEqual(Array.from(state.snapshot.groups.blocked), ["ghost-node:one"]);

assert.strictEqual(sandbox.ghostnetworkSuiteApplyDelta(app, state, {
    type: "ghost.part_activated",
    entity_id: "ghost-node:unknown",
    payload: { cycle_id: "cycle-135", suite_part_projection: { ...hiddenProjection, public_entity_id: "ghost-node:unknown" } },
}), false, "unknown non-discovery delta must request recovery");

assert.strictEqual(sandbox.ghostnetworkSuiteApplyDelta(app, state, {
    type: "ghost.part_discovered",
    entity_id: "ghost-node:new",
    payload: {
        cycle_id: "cycle-135", state_version: 12,
        suite_part_projection: {
            ...hiddenProjection,
            public_entity_id: "ghost-node:new",
            viewer_relation: "public_neutral",
            module_state: "neutral",
            status: "public",
            location_visibility: "exact",
            latitude: 50.0,
            longitude: 19.0,
        },
    },
}), true);
assert.strictEqual(state.snapshot.parts.length, 2);
assert.deepStrictEqual(Array.from(state.snapshot.groups.public), ["ghost-node:new"]);

assert.strictEqual(sandbox.ghostnetworkSuiteApplyDelta(app, state, {
    type: "ghost.part_consumed",
    entity_id: "ghost-node:new",
    payload: { cycle_id: "cycle-135", state_version: 13, removed: true, public_entity_id: "ghost-node:new" },
}), true);
assert.strictEqual(state.snapshot.parts.length, 1);

assert.strictEqual(sandbox.ghostnetworkSuiteApplyDelta(app, state, {
    type: "ghost.restart_required",
    payload: { cycle_id: "cycle-135", state_version: 14 },
}), true);
assert.strictEqual(state.restartRequired, true);
assert.strictEqual(state.snapshot.parts[0].actions.can_show_on_map, false);
assert.ok(renders >= 4);

console.log("ghostnetwork suite live delta tests: OK");
