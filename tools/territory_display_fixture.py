"""Loopback visual regression: real Leaflet + production territory replacement.

No game DB, accounts, map tiles, or provider API. Synthetic polygons reproduce
the reported bounds, not the player's complete production geometry.
Run: python tools/territory_display_fixture.py (http://127.0.0.1:8997).
Leaflet 1.9.3 assets load from the CDN; no application data is sent there.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def page():
    source = (ROOT / 'templates/map_template.html').read_text(encoding='utf-8')
    def between(a, b):
        start = source.index('function ' + a + '(')
        return source[start:source.index('function ' + b + '(', start)]
    code = between('createTerritoryAreaLayerCandidate', 'renderTerritoryConflictLayer')
    code += between('isSaneTerritoryPolygon', 'clearScanResultLayers')
    return '''<!doctype html><meta charset="utf-8"><title>Territory display regression</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css">
<style>body{margin:0;font:16px sans-serif}#map{height:80vh;background:#e8eee4}button{padding:12px;margin:8px}</style>
<button onclick="grow()">Capture pillar / grow main</button>
<button onclick="refresh()">Reload snapshot</button><output id="status"></output>
<div id="map"></div>
<script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
<script>
window.map=L.map('map',{preferCanvas:false}).setView([52.3,21.2],8);
window.playerAreaLayers=[];window.territoryAreaLayers={};
function territoryStableId(a){return String(a.id)}
function territoryLayerStyle(a){return {color:a.owner_username==='main'?'#008444':'#e47800',fillOpacity:.3}}
function territoryTooltip(a){return a.owner_username}
function bindTerritoryTooltip(p,t){p.bindTooltip(t)}
function bindTerritoryMapContextMenu(p){}
function removeMapLayerSafe(p){map.removeLayer(p)}
''' + code + '''
let wide=false;
function areas(){return [{id:453761,owner_username:'main',vertices:wide?
 [[51.9610687,20.1131042],[51.9610687,22.2832641],[52.6441913,22.2832641],[52.6441913,20.1131042]]:
 [[51.9610687,20.1131042],[51.9610687,21.9],[52.6441913,21.9],[52.6441913,20.1131042]]},
 {id:453766,owner_username:'run',vertices:[[52.0844621,20.0991092],[52.0844621,21.4197784],
 [52.6166102,21.4197784],[52.6166102,20.0991092]]}]}
function refresh(){
 const ok=replaceTerritoryAreaLayersAtomically(areas());
 document.getElementById('status').textContent=(ok?'OK':'FAIL')+' / territories: '+playerAreaLayers.length;
 return ok;
}
function grow(){wide=true;return refresh()}
refresh();
</script>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(204); self.end_headers(); return
        if self.path != '/':
            self.send_error(404); return
        body = page().encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 8997), Handler).serve_forever()
