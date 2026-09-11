const assert = require("assert");
const {sceneAt, sceneLayout} = require("../static/js/ghost_signal_show.js");
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

const parts = Array.from({length:20}, (_,i) => ({part_code: "P" + String(i).padStart(2,"0"), machine_code:"m" + Math.floor(i/5)}));
const machines = Array.from({length:4},(_,i)=>({code:"m"+i, part_codes:parts.slice(i*5,i*5+5).map(p=>p.part_code)}));
const manifest = {catalog:{parts,machines},cycle_history:{available:true,parts:[],ring_codes:parts.map(p=>p.part_code)}};
assert.strictEqual(sceneLayout(manifest,{elapsed:10}).nodes.filter(n=>n.visible).length,0);
assert.strictEqual(sceneLayout(manifest,{elapsed:45}).nodes.filter(n=>n.visible).length,10);
assert.strictEqual(sceneLayout(manifest,{elapsed:330}).edges.length,20);
assert.strictEqual(sceneLayout(manifest,{elapsed:220}).nodes.filter(n=>n.highlighted).length,5);
manifest.cycle_history.ring_codes=[];
assert.strictEqual(sceneLayout(manifest,{elapsed:330}).edges.length,0);
console.log("ghost signal montage topology/grouping/visibility: PASS");
