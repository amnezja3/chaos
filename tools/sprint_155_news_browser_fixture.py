"""Read-only isolated News component fixture; no database, account or LLM.

python tools/sprint_155_news_browser_fixture.py -> http://127.0.0.1:8999/
"""
import json
import sys
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from googleplex_news import build_googleplex_news_snapshot, merge_googleplex_news_publications

HTML = """<!doctype html><html lang="pl"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/css/googleplex_news.css">
<style>body{margin:0;background:#001108;color:#bdffc8;font-family:monospace}
nav{padding:12px}button{padding:10px} .browser-window{width:100%;box-sizing:border-box}</style>
<nav><button id="locale">PL / EN</button><button id="home">Home</button>
<button id="empty">Empty</button><button id="loading">Loading</button><button id="error">Error</button></nav>
<div class="browser-window is-browser-googleplex"><div id="news"></div></div>
<output id="action"></output>
<script src="/static/js/ghost_i18n.js"></script>
<script src="/static/js/googleplex_news.js"></script>
<script>
(async()=>{
 const manifest=await (await fetch('/static/locales/manifest.json')).json();
 const bundles={};
 for(const locale of ['pl','en']){
   const bundle={locale,format_version:1,content_version:manifest.content_version,messages:{}};
   for(const domain of ['foundation','apps'])Object.assign(bundle.messages,(await (await fetch('/static/locales/'+locale+'/'+domain+'.json')).json()).messages);
   bundles[locale]=bundle;
 }
 const translator=GhostI18n.createTranslator(manifest,bundles);
 let locale='pl',state='home';
 window.GhostLocale={t:(key,params={})=>translator.t(key,params,locale),getLocale:()=>locale};
 const snapshot=await (await fetch('/snapshot')).json();
 const root=document.getElementById('news');
 const draw=()=>{
   document.documentElement.lang=locale;
   if(state==='loading')return GoogleplexNewsUI.renderLoading(root);
   if(state==='error')return GoogleplexNewsUI.renderError(root);
   GoogleplexNewsUI.renderHome(root,state==='empty'?{...snapshot,entries:[]}:snapshot,{onAction:entry=>{
     document.getElementById('action').textContent=entry.action.action_type;
   }});
 };
 document.getElementById('locale').onclick=()=>{locale=locale==='pl'?'en':'pl';draw()};
 for(const id of ['home','empty','loading','error'])document.getElementById(id).onclick=()=>{state=id;draw()};
 draw();
})();
</script></html>"""


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        if self.path == '/show':
            from ghostnetwork.show_manifest import build_manifest
            from ghost_i18n import translator, manifest
            config = json.dumps({'manifest':manifest(),'fallback':translator().catalogs['pl'],
                'initial':translator().catalogs['en']}).replace('</','<\\/')
            storyboard = build_manifest({'sent_at':'2026-10-12T12:00:00Z','sent_event':True})
            page = '''<!doctype html><html><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/css/style.css">
<script src="/static/js/ghost_i18n.js"></script><script src="/static/js/ghost_i18n_runtime.js"></script>
<script src="/static/js/ghost_signal_network_details.js"></script><script>'''
            page += 'const config=' + config + ';const storyboard=' + json.dumps(storyboard).replace('</','<\\/') + ';\n'
            page += '''(async()=>{
window.GhostLocale=GhostI18nRuntime.mount(document,config);
const facade={GhostLocale, setTimeout:setTimeout.bind(window),clearTimeout:clearTimeout.bind(window),
 setInterval:setInterval.bind(window),clearInterval:clearInterval.bind(window),
 requestAnimationFrame:requestAnimationFrame.bind(window),cancelAnimationFrame:cancelAnimationFrame.bind(window),
 matchMedia:matchMedia.bind(window),console,GhostSignalNetworkDetails,innerWidth,innerHeight};
const source=await(await fetch('/static/js/ghost_signal_show.js')).text();
const api=Function('window',source+';return window.GhostSignalShow;')(facade);
const controller=api.createController({document});window.fixtureController=controller;
window.fixtureSeek=(seconds)=>{
 const now=Date.now(),start=now-seconds*1000;
 controller.apply({show_active:true,gameplay_locked:true,signal_public_id:'FIXTURE-155',
 show_started_at:new Date(start).toISOString(),show_ends_at:new Date(start+900000).toISOString(),
 server_now:new Date(now).toISOString(),show_manifest:storyboard,cycle_number:155,state_version:1});
};
window.fixtureLocale=async(locale)=>{await GhostLocale.changeLocale(locale);controller.render();};
window.fixtureScenes=storyboard.scenes;fixtureSeek(0);
})();</script></html>'''
            payload, content_type = page.encode('utf-8'), 'text/html; charset=utf-8'
        elif self.path == '/toast':
            from ghost_i18n import translator, manifest
            from system_message_i18n import project_system_copy
            message = project_system_copy({'id':'fixture-install', 'title':'Instalacja zakończona',
                'text':'Aplikacja <b>Moje <img src=x onerror=alert(1)> & narzędzie</b> została poprawnie zainstalowana!'}, 'googleplex_install')
            terminal = (ROOT / 'static/js/terminal.js').read_text(encoding='utf-8')
            functions = terminal[terminal.index('function escapeHTML('):terminal.index('function formatStorageSize(')]
            functions += terminal[terminal.index('function normalizeCybernerNotificationThread('):terminal.index("document.querySelectorAll('.icon').forEach")]
            functions += terminal[terminal.index('function shouldSuppressDuplicateSystemToast('):terminal.index('async function pollSystemMessages(')]
            config = json.dumps({'manifest':manifest(),'fallback':translator().catalogs['pl'], 'initial':translator().catalogs['en']}).replace('</','<\\/')
            page = '''<!doctype html><html><meta charset="utf-8"><button id="locale">PL / EN</button>
<button id="show">Show</button><div id="system-toast-container"></div>
<script src="/static/js/ghost_i18n.js"></script><script src="/static/js/ghost_i18n_runtime.js"></script><script>'''
            page += 'window.GhostLocale=GhostI18nRuntime.mount(document,' + config + ');\n'
            page += 'const ghostText=(key,params={})=>GhostLocale.t(key,params); const toolbarProfile={username:"fixture"}; const CYBERNER_NOTIFICATION_LIBRARY={unknown:{}};\n'
            page += functions + '\nconst message=' + json.dumps(message).replace('</','<\\/') + ';\n'
            cyberner = project_system_copy(dict(id='fixture-cyberner',notification_type='cyberner',
                source='friends',scope='channel',peer='friends',title='ZNAJOMI',
                text='Polski <img src=x> tekst gracza',system_preview=False), 'cyberner')
            page += 'window.fixtureCyberner=' + json.dumps(cyberner).replace('</','<\\/') + ';\n'
            page += "document.getElementById('show').onclick=()=>showSystemToast(message);document.getElementById('locale').onclick=()=>GhostLocale.changeLocale(GhostLocale.getLocale()==='en'?'pl':'en');</script></html>"
            payload = page.encode('utf-8')
            content_type = 'text/html; charset=utf-8'
        elif self.path == '/':
            payload = HTML.encode('utf-8')
            content_type = 'text/html; charset=utf-8'
        elif self.path == '/snapshot':
            snapshot = build_googleplex_news_snapshot(catalog=[], viewer_key='fixture', session_generation='fixture')
            record = {'medium_record_id':'fixture-news','publication_receipt_id':'fixture-receipt',
                'target_medium':'googleplex_news','presentation_slot':'gp-home-world-grid',
                'title':'Komunikat testowy','body':'Wiadomość używana w teście widoku.',
                'fact_refs':['fixture-fact'],'truth_class':'system','audience_scope':'public',
                'published_at':'2026-10-12T12:00:00Z','cta_action':'open_map','cta_payload':{'target_id':'world'}}
            snapshot = merge_googleplex_news_publications(snapshot,[record],locale_variants={
                'fixture-news':{'en':{'title':'Test update','summary':'A publication used to test the view.'}}})
            payload = json.dumps(snapshot).encode('utf-8')
            content_type = 'application/json'
        elif self.path.startswith('/static/'):
            return super().do_GET()
        else:
            return self.send_error(404)
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(payload)


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8999), Handler)
    print('READY http://127.0.0.1:8999/', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
