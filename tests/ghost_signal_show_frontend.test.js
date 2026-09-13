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
const journeySnapshot = Object.assign({}, snapshot, {show_manifest: {
  signal_sent_at: "2026-01-01T00:00:00Z",
  cycle_history: {future_2108_timestamp: "2108-01-01T00:00:00Z"}
}});
const begin = Date.parse(snapshot.show_started_at);
const finish = Date.parse(snapshot.show_ends_at);
assert.strictEqual(show.signalJourneyAt(journeySnapshot, begin - 1000, 0).label, "2026-01-01 00:00:00 UTC");
assert.strictEqual(show.signalJourneyAt(journeySnapshot, finish + 1000, 0).label, "2108-01-01 00:00:00 UTC");
const middle = show.signalJourneyAt(journeySnapshot, begin + 450000, 0);
assert.strictEqual(middle.progress, .5);
const expectedMiddle = new Date((Date.parse("2026-01-01T00:00:00Z") + Date.parse("2108-01-01T00:00:00Z")) / 2);
assert.strictEqual(middle.label, expectedMiddle.toISOString().slice(0, 19).replace("T", " ") + " UTC");
assert.deepStrictEqual(show.signalJourneyAt(journeySnapshot, begin + 420000, 30000), middle);
assert.strictEqual(show.signalJourneyAt(snapshot, begin, 0).label.includes("2026"), false);
const reversed = Object.assign({}, journeySnapshot, {show_manifest: {
  signal_sent_at: "2109-01-01", cycle_history: {future_2108_timestamp: "2108-01-01"}
}});
assert.strictEqual(show.signalJourneyAt(reversed, begin, 0).label, show.signalJourneyAt(snapshot, begin, 0).label);
console.log("ghost signal show frontend contract: PASS");
