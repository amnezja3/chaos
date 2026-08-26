"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const start = source.indexOf("const GHOSTNETWORK_SFX_BY_EVENT");
const end = source.indexOf("async function applyDelta", start);
assert.ok(start >= 0 && end > start, "GhostNetwork SFX dispatcher source must exist");

const playedIds = new Set();
const played = [];
const sandbox = {
    window: {
        GameSfx: {
            play(key, context) {
                if (!playedIds.has(context.event_id)) {
                    playedIds.add(context.event_id);
                    played.push({ key, context });
                }
                return { started: Promise.resolve({ ok: true }) };
            }
        }
    },
    Number, String, Object
};
sandbox.window.window = sandbox.window;
vm.createContext(sandbox);
vm.runInContext(
    `let stateDeltaSfxPlaybackAllowed = true;\n${source.slice(start, end)}`,
    sandbox
);

function event(type, id, payload = {}) {
    return {
        scope: "ghostnetwork",
        type,
        version: payload.state_version || 1,
        entity_id: payload.part_id || "ghost-entity",
        payload: { event_id: id, cycle_id: "cycle-1", ...payload }
    };
}

function expectPlayback(type, id, payload, expected) {
    const before = played.length;
    const accepted = sandbox.playGhostNetworkDeltaSfx(event(type, id, payload));
    assert.strictEqual(accepted, expected, `${type} transition acceptance mismatch`);
    assert.strictEqual(played.length - before, expected ? 1 : 0, `${type} playback mismatch`);
}

expectPlayback("ghost.part_discovered", "discovered-1", {}, true);
expectPlayback("ghost.part_contained", "contained-real", {
    previous_status: "public", status: "contained"
}, true);
expectPlayback("ghost.part_contained", "contained-redraw", {
    previous_status: "contained", status: "contained"
}, false);
expectPlayback("ghost.part_activated", "activated-real", {
    previous_status: "contained", status: "active"
}, true);
expectPlayback("ghost.part_activated", "activated-rebuild", {
    previous_status: "active", status: "active"
}, false);
expectPlayback("ghost.part_contested", "hostile-real", {
    previous_conflict_state: "none", conflict_state: "contested"
}, true);
expectPlayback("ghost.part_contested", "hostile-redraw", {
    previous_conflict_state: "contested", conflict_state: "contested"
}, false);
expectPlayback("ghost.part_revealed", "lost-real", {
    previous_status: "active", status: "public"
}, true);
expectPlayback("ghost.part_revealed", "lost-redraw", {
    previous_status: "public", status: "public"
}, false);
expectPlayback("ghost.part_deactivated", "deactivated-real", {
    previous_status: "active", status: "contained"
}, true);
expectPlayback("ghost.part_deactivated", "deactivated-redraw", {
    previous_status: "contained", status: "contained"
}, false);
expectPlayback("ghost.machine_progress_changed", "progress-real", {
    previous_active_parts: 1, active_parts: 2
}, true);
expectPlayback("ghost.machine_progress_changed", "progress-redraw", {
    previous_active_parts: 2, active_parts: 2
}, false);
expectPlayback("ghost.machine_online", "module-complete-1", {}, true);
expectPlayback("ghost.signal_sent", "signal-1", {}, true);

const beforeReplay = played.length;
assert.strictEqual(sandbox.playGhostNetworkDeltaSfx(event("ghost.part_activated", "activated-real", {
    previous_status: "contained", status: "active"
})), true);
assert.strictEqual(played.length, beforeReplay, "same canonical event id must be deduplicated");

console.log("ghostnetwork transition sfx tests: OK");
