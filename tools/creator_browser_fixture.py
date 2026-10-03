"""Isolated component host for Playwright; no production writes. Port 8878."""
import json
import os
import sys
import tempfile
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / 'tests')]
temporary = tempfile.TemporaryDirectory(prefix='creator-browser-')
os.chdir(temporary.name)
os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(temporary.name) / 'sessions')
from tests.test_creator_routes import CreatorRoutesTest
from creator_legacy import adopt

fixture = CreatorRoutesTest()
fixture.setUp()
fixture.prepare()
app = dict(id='legacy-browser', name='Historical browser test', icon='X',
    creator_username='attacker', project_file='Historical.sh', generated=True, published=True,
    price=100, interface='button_choices', type='exploit', map_actions=['exploit'],
    levels=[dict(title='Historical', text='Choose', options=[dict(id=0, label='Hack', price=500,
        effect={'firewall': False})])])
fixture.store.publish_legacy('attacker', app)
project_id = adopt(fixture.store, [app], ['attacker'], apply=True)[0]['project_id']
fixture.inventory.install_app('attacker', app, purchase_key='browser-original')
source = (root / 'static/js/terminal.js').read_text(encoding='utf-8')
base = source[source.index('function creatorBaseWindow('):source.index('function wireCreatorSubmit(')]
html = '''<!doctype html><meta charset="utf-8"><title>148 legacy editor fixture</title>
<link rel="stylesheet" href="/static/css/creator_editor.css">
<style>body{background:#001009;color:#cfc}.terminal{position:absolute;overflow:auto}
.creator-workspace{height:90%;overflow:auto}input,textarea{background:#021;color:#cfc}</style>
<script>function findAvailablePosition(){return {top:5,left:5}}function makeDraggable(){}
function addSystemMessage(a,b,c){document.body.dataset.error=c}</script><script>''' + base + '''</script>
<script src="/static/js/creator_editor.js"></script><div id="update"></div><script>
window.appId='legacy-browser';CreatorEditor.launch('button_choices', ''' + json.dumps(project_id) + ''');</script>'''


class Handler(BaseHTTPRequestHandler):
    def route(self):
        if self.path.split('?')[0] == '/':
            code, body, content_type = 200, html.encode(), 'text/html; charset=utf-8'
        elif self.path.startswith('/static/'):
            path = root / self.path.lstrip('/')
            code, body, content_type = 200, path.read_bytes(), 'text/css' if path.suffix == '.css' else 'application/javascript'
        else:
            raw = self.rfile.read(int(self.headers.get('Content-Length', '0')))
            response = fixture.client.open(self.path, method=self.command, data=raw or None, content_type='application/json')
            code, body, content_type = response.status_code, response.data, response.content_type
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.end_headers()
        self.wfile.write(body)

    do_GET = do_POST = do_PATCH = route


if __name__ == '__main__':
    server = HTTPServer(('127.0.0.1', 8878), Handler)
    print('READY 148 LEGACY http://127.0.0.1:8878', flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        fixture.doCleanups()
        os.chdir(root)
        temporary.cleanup()
