"""Generate a synthetic static preview; never open a game database or emit events."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ghostnetwork.show_manifest import build_manifest  # noqa: E402
from ghostnetwork.catalog import TOPOLOGY_ANCHOR  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = build_manifest({"sent_at": "2026-09-11T10:00:01+00:00", "sent_event": True})
    # Explicit demo layout, not claimed as the topology/history of any real cycle.
    manifest["cycle_history"] = {"available": False, "parts": [], "ring_codes": list(TOPOLOGY_ANCHOR),
                                  "future_2108_timestamp": "2108-04-27T23:17:08+00:00"}
    encoded = json.dumps(manifest, ensure_ascii=False).replace("<", "\\u003c")
    html = """<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GhostSignal — PODGLĄD, dane demonstracyjne</title>
<link rel="stylesheet" href="/static/css/style.css?v=signal-show-140-2-media-1">
<style>body{background:#05090d;color:#caffdf}#preview-controls{position:fixed;top:0;left:0;right:0;z-index:2147483647;background:#071b13;padding:8px;font:12px monospace;display:flex;gap:8px;align-items:center;flex-wrap:wrap}#preview-controls input{width:min(30vw,350px)}#preview-controls select{max-width:40vw}</style>
<div id="preview-controls"><strong>PODGLĄD / DANE DEMO</strong>
<select id="scene-select" aria-label="Scena"></select>
<input id="seek" aria-label="Sekundy show" type="range" min="0" max="479" value="0">
<output id="position">0 s</output><label><input type="checkbox" id="sent" checked>potwierdzony sygnał</label></div>
<script>window.fetch=()=>Promise.resolve({ok:true,json:()=>Promise.resolve({ok:true,show_active:false})});</script>
<script src="/static/js/ghost_signal_show.js?v=signal-show-140-2-media-1"></script>
<script>
const manifest = MANIFEST;
let previewController;
const select=document.getElementById('scene-select'), seek=document.getElementById('seek');
for(const scene of manifest.scenes.filter(s=>s.start<480)) {
 const option=document.createElement('option'); option.value=scene.start; option.textContent=scene.start+' s / '+scene.label; select.appendChild(option);
}
function showAt(seconds) {
 if(previewController) previewController.stop();
 const start=Date.now()-Number(seconds)*1000;
 manifest.signal_confirmed=document.getElementById('sent').checked;
 previewController=GhostSignalShow.createController({document,fetch:window.fetch});
 previewController.apply({show_active:true,gameplay_locked:true,cycle_number:0,state_version:1,
  signal_public_id:'PODGLĄD — NIE JEST TO TRANSMISJA',server_now:new Date().toISOString(),
  show_started_at:new Date(start).toISOString(),show_ends_at:new Date(start+900000).toISOString(),
  show_manifest:manifest,from_system_version:'DEMO',to_system_version:'DEMO'});
 document.getElementById('position').textContent=seconds+' s'; seek.value=seconds;
}
select.onchange=()=>showAt(select.value); seek.oninput=()=>showAt(seek.value);
document.getElementById('sent').onchange=()=>showAt(seek.value);
document.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{if(window.GhostSignalShowController)window.GhostSignalShowController.stop();showAt(0);},0));
</script></html>""".replace("MANIFEST", encoded)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit("Output exists; choose another path to preserve the earlier preview.")
    output.write_text(html, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
