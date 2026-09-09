const assert = require("assert");
const show = require("../static/js/ghost_signal_show.js");

const snapshot = {
  server_now: "2026-09-09T10:00:00Z",
  show_started_at: "2026-09-09T10:00:00Z",
  show_ends_at: "2026-09-09T10:15:00Z"
};

assert.strictEqual(show.serverOffset(snapshot, Date.parse(snapshot.server_now)), 0);
assert.strictEqual(show.secondsRemaining(snapshot, Date.parse(snapshot.server_now), 0), 900);
assert.strictEqual(show.phaseAt(snapshot, Date.parse("2026-09-09T10:00:10Z"), 0).code, "network_lock");
assert.strictEqual(show.phaseAt(snapshot, Date.parse("2026-09-09T10:04:00Z"), 0).code, "signal_transmission");
assert.strictEqual(show.phaseAt(snapshot, Date.parse("2026-09-09T10:14:00Z"), 0).code, "ghostsystem_restart");
console.log("ghost signal show frontend contract: PASS");
