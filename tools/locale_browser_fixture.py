"""Local PL/EN settings renderer with real isolated settings endpoint (port 8992)."""
import json
import os
from pathlib import Path
import sys
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / 'tests')]
temporary = tempfile.TemporaryDirectory(prefix='locale-browser-')
os.chdir(temporary.name)
os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(temporary.name) / 'sessions')
os.environ['CHAOS_SECRET_KEY'] = 'isolated-locale-only'
from tests.test_desktop_settings_writer import DesktopSettingsWriterTest
from ghost_i18n import manifest, translator
from flask import render_template
import run
run.app.jinja_env.auto_reload = True
fixture = DesktopSettingsWriterTest()
fixture.setUp()
fixture.seed()
source = (root / 'static/js/terminal.js').read_text(encoding='utf-8')
def section(start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]
script = section('function createSettings(', 'async function createProfile(')
script += section('function escapeHTML(', 'function sanitizeToastHTML(')
script += section('function ghostText(', 'function applyDesktopSettings(')
script += section('function mergeDesktopSettings(', 'function sendDesktopSettingsBeacon(')
generation = fixture.client.environ_base['HTTP_X_CHAOS_SESSION_GENERATION']
html = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>153 locale fixture</title><link rel="icon" href="data:,"><link rel="stylesheet" href="/static/css/style.css">
<style>body{background:#10131c;color:#eee}.terminal{position:absolute}.settings-shell{overflow:auto}</style>
<script id="session-generation-config" type="application/json">SESSION</script>
<script src="/static/js/session_generation.js"></script>
<script id="ghost-i18n-bootstrap" type="application/json">CONFIG</script>
<script src="/static/js/ghost_i18n.js"></script><script src="/static/js/ghost_i18n_runtime.js"></script>
<button id="open" data-ghost-i18n="shell.desktop.settings">Ustawienia</button>
<input id="terminal-draft" aria-label="Terminal draft" value="run my-tool.sh">
<div id="author-text">Moje narzędzie — do not translate</div>
<script>
let desktopSettings={},desktopSessionActive=true;
function findAvailablePosition(){return {top:70,left:5}}
function makeDraggable(){}
function bringWindowToFront(){}
function renderRunningApps(){}
function isGhostRadioAutoplayEnabled(){return false}
function isAutoFullscreenEnabled(){return false}
async function getUserProfile(){return {email:'fixture@example.com'}}
CODE
document.getElementById('open').onclick=()=>createSettings();
(async()=>{const response=await fetch('/api/profile/desktop');const data=await response.json();
desktopSettings=data.desktop_settings||{}; await initializeDesktopLocale(desktopSettings);document.body.dataset.ready='true';})();
</script>'''.replace('SESSION', json.dumps({'generation': generation, 'username': 'attacker'})).replace(
    'CONFIG', json.dumps({'manifest': manifest(), 'fallback': translator().catalogs['pl']})).replace('CODE', script)


class Handler(BaseHTTPRequestHandler):
    def route(self):
        path = self.path.split('?')[0]
        headers = {}
        if path == '/':
            status, body, content_type = 200, html.encode(), 'text/html; charset=utf-8'
        elif path in ('/entry', '/register'):
            with run.app.test_request_context('/'):
                entry = render_template('register.html' if path == '/register' else 'login.html')
            status, body, content_type = 200, entry.encode(), 'text/html; charset=utf-8'
        elif path.startswith('/static/'):
            target = (root / path.lstrip('/')).resolve()
            if not target.is_relative_to(root / 'static') or not target.is_file():
                self.send_error(404)
                return
            status, body = 200, target.read_bytes()
            import mimetypes
            content_type = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        else:
            actual = {'X-Chaos-Session-Generation': self.headers.get('X-Chaos-Session-Generation', '')}
            raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            with fixture.no_heavy():
                response = fixture.client.open(self.path, method=self.command, headers=actual, data=raw or None, content_type='application/json')
            status, body, content_type = response.status_code, response.data, response.content_type
            headers = {k:v for k,v in response.headers if k.lower().startswith('x-chaos-')}
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        for key,value in headers.items(): self.send_header(key,value)
        self.end_headers()
        self.wfile.write(body)
    do_GET = do_POST = route


if __name__ == '__main__':
    HTTPServer.request_queue_size = 128
    server = HTTPServer(('127.0.0.1', 8992), Handler)
    print('READY LOCALE http://127.0.0.1:8992', flush=True)
    try: server.serve_forever()
    finally:
        server.server_close()
        fixture.doCleanups()
        os.chdir(root)
        temporary.cleanup()
