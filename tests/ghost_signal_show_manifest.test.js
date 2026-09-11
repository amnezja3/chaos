const assert = require("assert");
const {sceneAt} = require("../static/js/ghost_signal_show.js");
const start = Date.parse("2026-09-11T10:00:00Z");
const snapshot = {
    show_started_at: new Date(start).toISOString(),
    show_ends_at: new Date(start + 900000).toISOString(),
    show_manifest: {
        version: "ghostsignal-show-manifest-v2", nominal_duration_seconds: 900,
        signal_confirmed: true,
        scenes: [
            {id: "parts", label: "Parts", start: 0, end: 455},
            {id: "replay", label: "Replay", start: 455, end: 896, requires_signal_sent: true},
            {id: "restart", label: "Wait", start: 896, end: 900, requires_signal_sent: true}
        ]
    }
};
assert.strictEqual(sceneAt(snapshot, start - 1000, 0).id, "parts");
assert.strictEqual(sceneAt(snapshot, start + 454999, 0).id, "parts");
assert.strictEqual(sceneAt(snapshot, start + 455000, 0).id, "replay");
assert.strictEqual(sceneAt(snapshot, start + 900000, 0).id, "restart");
assert.strictEqual(sceneAt(snapshot, start + 2000000, 0).progress, 1);
assert.strictEqual(sceneAt(snapshot, start + 400000, 55000).id, "replay");
snapshot.show_manifest.signal_confirmed = false;
assert.strictEqual(sceneAt(snapshot, start + 500000, 0).id, "waiting_for_signal_sent");
snapshot.show_manifest.scenes[1].start = 460;
assert.strictEqual(sceneAt(snapshot, start + 500000, 0), null);
assert.strictEqual(sceneAt({}, start, 0), null);
console.log("ghost signal show manifest seek/gate/fallback: PASS");
