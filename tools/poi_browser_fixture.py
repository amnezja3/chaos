"""Loopback component test: production mapAction + real /map-action + isolated POI.

Leaflet drawing and scanner shell are adapters; no public tiles/API or live users.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]


def main():
    import json
    import os
    import tempfile
    import time
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='poi-browser-') as directory:
        os.chdir(directory)
        os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(directory) / 'sessions')
        os.environ['CHAOS_SECRET_KEY'] = 'isolated-poi-only'
        os.environ['CHAOS_POI_INFRASTRUCTURE_ENABLED'] = '1'
        import run
        from test_ghostlab_scanner import ScannerTest
        from poiFetchClass import POIFetcher
        from poi_infrastructure.service import Service
        from ghost_i18n import translator
        fixture = ScannerTest()
        fixture.setUp()
        token = fixture.activate()['token']
        mode = {'value': 'upstream', 'calls': 0}
        def transport(*args):
            mode['calls'] += 1
            if mode['value'] != 'upstream':
                return 503, None, None
            return 200, None, {'elements':[{'type':'node','id':777,'lat':52,'lon':21,
                'tags':{'office':'company','name':'Fixture office'}}]}
        fetcher = POIFetcher(tag_filters=['shop','amenity','office'])
        fetcher.endpoints = ['https://fixture.invalid']
        fetcher._poi_service = Service(Path(directory)/'poi.sqlite3', transport=transport)
        service = fetcher._poi_service
        service.repo.initialize()
        for target, key, value in [
            (run,'fetcher',fetcher), (run,'GHOSTNETWORK_ABILITIES_ENABLED',False),
        ]:
            fixture.stack.enter_context(patch.object(target,key,value))
        fixture.stack.enter_context(patch.object(run.player_position_store,'get_position',return_value={'lat':52,'lng':21}))
        fixture.stack.enter_context(patch.object(run.Haversine,'haversine_distance',return_value=1))
        fixture.stack.enter_context(patch.object(run,'foreign_territory_action_block',return_value=None))
        fixture.stack.enter_context(patch.object(run.player_marked_target_store,'list_targets',return_value=[]))
        fixture.stack.enter_context(patch.object(run.player_scan_snapshot_store,'record',return_value={'scan_id':'fixture-scan'}))
        text = (ROOT/'templates/map_template.html').read_text(encoding='utf-8')
        production_action = text[text.index('        async function mapAction('):text.index('        const bikeDirectionIcons =')]
        catalogs = {lang: {key: entry.get('text', entry.get('forms', {}).get('other', key))
                          for key, entry in catalog['messages'].items()}
                    for lang, catalog in translator().catalogs.items()}
        html = '''<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,"><title>POI map component</title>
<style>body{background:#061710;color:#3f9;font:16px monospace;padding:12px}button,select{padding:12px}#markers{overflow-wrap:anywhere}#message{margin:12px 0}</style>
<select id="locale"><option>pl</option><option>en</option></select><label><input type="checkbox" id="deep">GhostLab</label><button id="scan">SCAN</button><div id="message" role="status"></div><ul id="markers"></ul>
<script>
const catalogs=__FIXTURE_CATALOGS__;
const GhostLocale={t:(k,p={})=>{let s=catalogs[locale.value][k]||k;for(const [k,v]of Object.entries(p))s=s.replaceAll('{'+k+'}',v);return s}};
window.escapeMapText=s=>String(s);function mapResponseText(d){return d.message_i18n?GhostLocale.t(d.message_i18n.key,d.message_i18n.params):d.status||d.message||'error'}
window.mapScanEffectState={element:null};function beginMapScanEffect(){return ()=>{}}function finishMapScanEffectAfterPaint(f){f?.()}
function guardMapGameplayAction(){return false}function handleDetentionTravelDenial(){return false}function handleForeignTerritoryProtectedResponse(){return false}
window.fixtureToken=__FIXTURE_TOKEN__;
window.DeepScannerMap={begin:()=>deep.checked?{token:window.fixtureToken,dispose(){}}:null,log:()=>'',messageKey:()=>null,stop:()=>{deep.checked=false}};
function addSystemMessage(type,title,text){message.textContent=text;message.dataset.type=type}
function clearScanResultLayers(){markers.replaceChildren()}function mapTargetDisplayLabel(o){return o.name||o.label||'POI'}function isMissingTargetDisplayName(v){return !v}
function normalizeMapMenuTarget(o){return o}function bindMarkerContextSnapshot(){}function registerTargetMarker(){}function mapTargetLabelHtml(o){return o.name}
function rememberScanResultLayer(m){let e=document.createElement('li');e.textContent=m._scanTarget.name;markers.append(e)}
const L={divIcon:o=>o,marker:()=>({bindTooltip(){},on(){}})};
__FIXTURE_ACTION__
scan.onclick=async()=>{let d=await mapAction('scan',52,21);document.body.dataset.outcome=d?.scan_outcome||'denied'};
</script></html>'''.replace('__FIXTURE_CATALOGS__',json.dumps(catalogs)).replace('__FIXTURE_TOKEN__',json.dumps(token)).replace('__FIXTURE_ACTION__',production_action)
        class Handler(BaseHTTPRequestHandler):
            def route(self):
                if self.path == '/':
                    status, body, content = 200,html.encode(),'text/html; charset=utf-8'
                elif self.path == '/__activate':
                    status,body,content=200,json.dumps(fixture.activate()).encode(),'application/json'
                elif self.path.startswith('/__mode/'):
                    mode['value'] = self.path.rsplit('/',1)[1]
                    with service.repo.transaction() as c:
                        c.execute('DELETE FROM providers')
                        if mode['value']=='cold':c.execute('DELETE FROM cache')
                        elif mode['value']=='stale':c.execute('UPDATE cache SET fetched=?',(time.time()-400,))
                    status,body,content=200,json.dumps(mode).encode(),'application/json'
                else:
                    raw=self.rfile.read(int(self.headers.get('Content-Length',0)))
                    with fixture.no_heavy():
                        response=fixture.client.open(self.path,method=self.command,data=raw or None,content_type='application/json')
                    status,body,content=response.status_code,response.data,response.content_type
                self.send_response(status)
                self.send_header('Content-Type',content)
                self.end_headers()
                self.wfile.write(body)
            do_GET=do_POST=route
        server=HTTPServer(('127.0.0.1',8996),Handler)
        try:
            print('READY http://127.0.0.1:8996',flush=True)
            server.serve_forever()
        finally:
            server.server_close()
            fixture.doCleanups()
            os.chdir(ROOT)


if __name__=='__main__':main()
