"""Generate a demo or read-only historical preview; never emit game events."""
import argparse
import json
from pathlib import Path
import sys
import sqlite3
import hashlib
from contextlib import contextmanager, closing

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ghostnetwork.show_manifest import build_manifest, prepare_settlement_scene  # noqa: E402
from ghostnetwork.catalog import TOPOLOGY_ANCHOR  # noqa: E402
from ghostnetwork.repository import GhostNetworkRepository  # noqa: E402
from ghostnetwork.ranking import GhostSignalRankingService  # noqa: E402
from ghostnetwork.show_manifest import prepare_scene_snapshot  # noqa: E402


class HistoricalReader(GhostNetworkRepository):
    """Tool-only adapter: no schema initialization, writes denied by SQLite."""
    def __init__(self, connection):
        self.connection = connection

    @contextmanager
    def _conn(self):
        yield self.connection


def historical_manifest(db_path, cycle_id):
    with closing(sqlite3.connect(Path(db_path).resolve().as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        # Bound offline snapshot hydration; never read users/profile or live world.
        for table in ("ghost_cycle_lock_snapshots", "ghost_signal_rankings"):
            size = conn.execute("SELECT length(CAST(snapshot_json AS BLOB)) FROM " + table
                                + " WHERE cycle_id=?", (cycle_id,)).fetchone()
            if not size or size[0] > 32 * 1024 * 1024:
                raise ValueError(table + ": missing or exceeds 32 MiB")
        repo = HistoricalReader(conn)
        show = repo.get_signal_show_for_cycle(cycle_id)
        if not show:
            raise ValueError("show_missing")
        facts = repo.get_show_presentation_facts(show["signal_id"])
        if not facts.get("sent_at") or not facts.get("sent_event"):
            raise ValueError("canonical_signal_sent_missing")
        ranking = repo.get_signal_ranking(show["signal_id"])
        service = GhostSignalRankingService(repo)
        if not service.validate(ranking)["valid"]:
            raise ValueError("ranking_checksum_invalid")
        if ranking["cycle_id"] != cycle_id or (ranking["snapshot"] or {}).get("signal_id") != show["signal_id"]:
            raise ValueError("ranking_lineage_invalid")
        lock = repo.get_cycle_lock_snapshot(cycle_id)
        from ghostnetwork.closure import _snapshot_checksum
        if _snapshot_checksum(lock["snapshot"]) != lock["snapshot_checksum"]:
            raise ValueError("lock_checksum_invalid")
        stored = show.get("scene_snapshot") or {}
        reconstructed = not bool(stored.get("settlement"))
        history = stored or json.loads(prepare_scene_snapshot(lock, show["signal_id"]))
        if not stored:
            history.pop("future_2108_timestamp", None)  # Never invent a historical destination date.
        history["settlement"] = stored.get("settlement") or service.build_show_scene(ranking)
        expected = prepare_settlement_scene(ranking)
        for key in ("players_total", "rewards_total", "rsp_total", "territories_total"):
            if history["settlement"].get(key) != expected[key]:
                raise ValueError("stored_projection_mismatch:" + key)
        manifest = build_manifest(facts, history)
        info = {"mode": "historical", "cycle_id": cycle_id, "public_id": show["signal_public_id"],
                "from_version": show.get("from_system_version"), "to_version": show.get("to_system_version"),
                "projection_reconstructed": reconstructed,
                "ranking_checksum_valid": True, "lock_checksum_valid": True,
                "read_only": True,
                "counts": {key: expected[key] for key in ("players_total", "rewards_total", "rsp_total", "territories_total")}}
        conn.rollback()
    info["manifest_bytes"] = len(json.dumps(manifest, ensure_ascii=False).encode())
    info["manifest_sha256"] = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
    return manifest, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--db")
    parser.add_argument("--cycle-id")
    args = parser.parse_args()
    if bool(args.db) != bool(args.cycle_id):
        parser.error("--db and --cycle-id must be used together")
    manifest = build_manifest({"sent_at": "2026-09-11T10:00:01+00:00", "sent_event": True})
    # Explicit demo layout, not claimed as the topology/history of any real cycle.
    manifest["cycle_history"] = {"available": False, "parts": [], "ring_codes": list(TOPOLOGY_ANCHOR),
                                  "future_2108_timestamp": "2108-04-27T23:17:08+00:00"}
    manifest["cycle_history"]["settlement"] = prepare_settlement_scene({
        "signal_id": "DEMO", "snapshot": {
            "territories": [{"clan_code": "virex", "area_size": 1,
                             "vertices": [{"lat": 52, "lng": 21}, {"lat": 52.01, "lng": 21},
                                          {"lat": 52.01, "lng": 21.02}]}],
            "players": [{"display_alias_snapshot": "GRACZ DEMO", "clan_id_snapshot": "virex",
                         "rank": 1, "rsp_signal": 10, "nodes_held": 1, "closer": True}],
            "rewards": [{"signal_id": "DEMO", "reward_type": "ghost_signal_closer", "final_rsp": 10}],
            "clans": [{"clan_id": "virex", "rank": 1, "clan_ghost_score": 10,
                       "member_count_participating": 1, "rsp_members_total": 10}],
            "conflicts": [{"status": "resolved"}], "score_policy": {"policy_version": "DEMO"}}},
        [{"target_medium": medium, "title": "PUBLIKACJA DEMO", "body": "Dane demonstracyjne, nie historia gry.",
          "published_at": "2026-09-11T10:00:00Z"} for medium in ("blacknet", "googleplex_news")])
    info = {"mode": "demo", "public_id": "PODGLĄD — DANE DEMO", "from_version": "DEMO", "to_version": "DEMO"}
    if args.db:
        manifest, info = historical_manifest(args.db, args.cycle_id)
    encoded = json.dumps(manifest, ensure_ascii=False).replace("<", "\\u003c")
    html = """<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GhostSignal — podgląd operatorski</title>
<link rel="stylesheet" href="/static/css/style.css?v=signal-show-stylization-1-glitch-1">
<style>body{background:#05090d;color:#caffdf}#preview-controls{position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#071b13;padding:8px;font:12px monospace;display:flex;gap:8px;align-items:center;flex-wrap:wrap}#preview-controls input{width:min(30vw,350px)}#preview-controls select{max-width:40vw}</style>
<div id="preview-controls"><strong id="preview-source"></strong>
<button id="export-performance">Raport wydajności</button>
<select id="scene-select" aria-label="Scena"></select>
<input id="seek" aria-label="Sekundy show" type="range" min="0" max="899" value="0">
<output id="position">0 s</output><label><input type="checkbox" id="sent" checked>potwierdzony sygnał</label></div>
<script>window.fetch=()=>Promise.resolve({ok:true,json:()=>Promise.resolve({ok:true,show_active:false})});</script>
<script src="/static/js/ghost_radio.js?v=radio-show-140-4"></script>
<link rel="stylesheet" href="/static/css/map_glitch.css?v=map-glitch-shared-1">
<script src="/static/js/map_glitch.js?v=map-glitch-shared-1"></script>
<script src="/static/js/ghost_signal_show.js?v=signal-show-stylization-1-glitch-1"></script>
<script>
const manifest = MANIFEST;
const previewInfo = PREVIEW_INFO;
document.getElementById('preview-source').textContent=previewInfo.mode==='historical'?'REPLAY / DANE ARCHIWALNE':'PODGLĄD / DANE DEMO';
let previewController;
const select=document.getElementById('scene-select'), seek=document.getElementById('seek');
for(const scene of manifest.scenes) {
 const option=document.createElement('option'); option.value=scene.start; option.textContent=scene.start+' s / '+scene.label; select.appendChild(option);
}
function showAt(seconds) {
 if(previewController) previewController.stop();
 const start=Date.now()-Number(seconds)*1000;
 manifest.signal_confirmed=document.getElementById('sent').checked;
 previewController=GhostSignalShow.createController({document,fetch:window.fetch});
 previewController.apply({show_active:true,gameplay_locked:true,cycle_number:0,state_version:1,
  signal_public_id:previewInfo.public_id,server_now:new Date().toISOString(),
  show_started_at:new Date(start).toISOString(),show_ends_at:new Date(start+900000).toISOString(),
  show_manifest:manifest,from_system_version:previewInfo.from_version,to_system_version:previewInfo.to_version});
 document.getElementById('position').textContent=seconds+' s'; seek.value=seconds;
}
select.onchange=()=>showAt(select.value); seek.oninput=()=>showAt(seek.value);
document.getElementById('sent').onchange=()=>showAt(seek.value);
// Preview-only measurement: bounded aggregates, no telemetry requests.
const measurement={mode:previewInfo.mode,manifest_sha256:previewInfo.manifest_sha256||null,
 started_at:new Date().toISOString(),viewport:{width:innerWidth,height:innerHeight},
 visible_frames:0,visible_ms:0,max_frame_gap_ms:0,frames_over_50ms:0,
 samples:0,max_dom_nodes:0,long_tasks:0,max_long_task_ms:0,scene_visits:[],js_errors:0,resource_samples:[]};
let lastFrame=null,frameHandle=0,measureStopped=false,observer=null;
function frameStamp(t){
 if(measureStopped)return;
 if(!document.hidden && lastFrame!==null){const gap=t-lastFrame;
  measurement.visible_frames++;measurement.visible_ms+=gap;
  measurement.max_frame_gap_ms=Math.max(measurement.max_frame_gap_ms,gap);
  if(gap>50)measurement.frames_over_50ms++;
 }
 lastFrame=document.hidden?null:t;frameHandle=requestAnimationFrame(frameStamp);
}
document.addEventListener('visibilitychange',()=>{lastFrame=null;});
window.addEventListener('error',()=>{measurement.js_errors++;});
window.addEventListener('unhandledrejection',()=>{measurement.js_errors++;});
try{observer=new PerformanceObserver(list=>{for(const task of list.getEntries()){
 measurement.long_tasks++;measurement.max_long_task_ms=Math.max(measurement.max_long_task_ms,task.duration);
}});observer.observe({entryTypes:['longtask']});}catch(_){measurement.long_tasks_supported=false;}
function sample(){
 const root=document.getElementById('ghost-signal-show');
 if(!root)return;
 measurement.samples++;
 measurement.max_dom_nodes=Math.max(measurement.max_dom_nodes,root.getElementsByTagName('*').length);
 const scene=root.getAttribute('data-show-scene');
 if(measurement.samples%10===0 && measurement.resource_samples.length<100)
  measurement.resource_samples.push({scene,at:new Date().toISOString(),nodes:root.getElementsByTagName('*').length,
   heap_bytes:performance.memory?performance.memory.usedJSHeapSize:null});
 const last=measurement.scene_visits[measurement.scene_visits.length-1];
 if(scene && (!last||last.scene!==scene) && measurement.scene_visits.length<200)
  measurement.scene_visits.push({scene,at:new Date().toISOString()});
}
frameHandle=requestAnimationFrame(frameStamp);
const sampleTimer=setInterval(sample,1000);
function stopMeasurement(){measureStopped=true;cancelAnimationFrame(frameHandle);clearInterval(sampleTimer);if(observer)observer.disconnect();}
setTimeout(stopMeasurement,920000);
window.addEventListener('pagehide',stopMeasurement,{once:true});
document.getElementById('export-performance').onclick=()=>{
 sample();const report=Object.assign({},measurement,{exported_at:new Date().toISOString(),
  mean_frame_ms:measurement.visible_frames?measurement.visible_ms/measurement.visible_frames:null,
  heap_bytes:performance.memory?performance.memory.usedJSHeapSize:null,
  resource_transfer_bytes:performance.getEntriesByType('resource').reduce((sum,r)=>sum+(r.transferSize||0),0)});
 const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download='ghostsignal-140-5-performance.json';a.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
};
document.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{if(window.GhostSignalShowController)window.GhostSignalShowController.stop();showAt(0);},0));
</script></html>""".replace("const previewInfo = PREVIEW_INFO;", "const previewInfo = " + json.dumps(info, ensure_ascii=False).replace("<", "\\u003c") + ";", 1).replace("const manifest = MANIFEST;", "const manifest = " + encoded + ";", 1)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit("Output exists; choose another path to preserve the earlier preview.")
    output.write_text(html, encoding="utf-8")
    print(output)
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
