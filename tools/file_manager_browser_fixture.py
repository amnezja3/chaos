"""Isolated FM renderer + real Flask endpoints; localhost only, temporary accounts.

python tools/file_manager_browser_fixture.py -> http://127.0.0.1:8991
"""
import json
import os
from pathlib import Path
import sys
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / 'tests')]
temporary = tempfile.TemporaryDirectory(prefix='fm-browser-')
os.chdir(temporary.name)
os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(temporary.name) / 'sessions')
os.environ['CHAOS_SECRET_KEY'] = 'isolated-fm-browser-only'
from tests.test_file_manager_inventory import FileManagerInventoryTest
from inventory_bootstrap import repair_missing_inventory
fixture = FileManagerInventoryTest()
fixture.setUp()
fixture.seed()
source = (root / 'static/js/terminal.js').read_text(encoding='utf-8')
def section(start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]
script = section('function renderFileManagerLoadError(', 'function createEmailClientLegacy(')
script += section('function escapeHTML(', 'function sanitizeToastHTML(')
script += section('function renderStorageMeterInner(', 'function updateStorageView(')
script += section('function formatStorageSize(', 'function normalizeCybernerNotificationThread(')
generation = fixture.client.environ_base['HTTP_X_CHAOS_SESSION_GENERATION']
html = '''<!doctype html><meta charset="utf-8"><title>FM regression fixture</title>
<link rel="icon" href="data:,"><link rel="stylesheet" href="/static/css/style.css">
<style>body{background:#191a28;color:#eee}.terminal{position:absolute;display:flex}</style>
<button id="open">Otwórz FM</button><div id="messages"></div><script>
const fileManagerInstances=new Map();
function findAvailablePosition(){return {top:50,left:20}}
function makeDraggable(){}
function selectMapActionTool(){}
function addSystemMessage(type,title,text){document.getElementById('messages').textContent=text}
</script><script type="application/json" id="session-generation-config">CONFIG</script>
<script src="/static/js/session_generation.js"></script><script>CODE
document.getElementById('open').onclick=()=>createFileManager();
</script>'''.replace('CONFIG', json.dumps({'generation': generation, 'username': 'attacker'})).replace('CODE', script)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        headers = {'X-Chaos-Session-Generation': generation, 'X-Chaos-Session-User': 'attacker'}
        if path == '/':
            status, body, content_type = 200, html.encode(), 'text/html; charset=utf-8'
        elif path.startswith('/static/'):
            target = (root / path.lstrip('/')).resolve()
            if not target.is_relative_to(root / 'static') or not target.is_file():
                self.send_error(404)
                return
            status, body = 200, target.read_bytes()
            content_type = 'text/css' if target.suffix == '.css' else 'application/javascript'
        elif path == '/fixture/legacy':
            fixture.make_legacy()
            status, body, content_type = 200, b'{}', 'application/json'
        elif path == '/fixture/repair':
            result = repair_missing_inventory(fixture.path, 'attacker', apply=True)
            status, body, content_type = 200, json.dumps(result).encode(), 'application/json'
        else:
            # Forward actual browser generation; do not let fixture defaults hide omissions.
            actual = {'X-Chaos-Session-Generation': self.headers.get('X-Chaos-Session-Generation', '')}
            with fixture.no_heavy():
                response = fixture.client.get(self.path, headers=actual)
            status, body, content_type = response.status_code, response.data, response.content_type
            headers = {k: v for k, v in response.headers if k.lower().startswith('x-chaos-')}
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8991), Handler)
    print('READY FM http://127.0.0.1:8991', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        fixture.doCleanups()
        os.chdir(root)
        temporary.cleanup()
