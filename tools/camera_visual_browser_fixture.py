"""Local persistent 164.0 harness. Never imports run.py or opens game.sqlite3."""
import argparse
import json
import re
import secrets
import sys
import threading
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.camera_visual_fixture_store import FixtureStore

BASE=ROOT/'doc/prototypes/camera_view/v164_0'
SOURCE=(ROOT/'static/js/terminal.js').read_text(encoding='utf8')

def extract(start,end):
    a=SOURCE.index(start)
    return SOURCE[a:SOURCE.index(end,a)]

RENDERER='\n'.join([
    extract('function app_window(', 'async function app_progressbar_random('),
    extract('function findCameraApplicationWindow(', 'function launchApplicationFromEntry('),
    extract('function prepareApplicationRenderWindow(', 'function resolveApplicationBrandModel('),
    extract('function updateWorkspaceBounds(', 'function applyMobileSafeModeToOpenWindows('),
])

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default=str(ROOT/'instance/camera-visual-164-0.sqlite3'))
    parser.add_argument('--test-controls',action='store_true',help='Enable explicit fixture-only time advance')
    args=parser.parse_args()
    Path(args.db).parent.mkdir(parents=True,exist_ok=True)
    store=FixtureStore(args.db)
    csrf=secrets.token_hex(24)
    stop=threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def token(self):
            cookies=SimpleCookie(self.headers.get('Cookie',''))
            return cookies['cvn_fixture'].value if 'cvn_fixture' in cookies else ''
        def send(self,status,body,kind='application/json',cookie=None):
            self.send_response(status)
            self.send_header('Content-Type',kind)
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            if cookie is not None:self.send_header('Set-Cookie','cvn_fixture='+cookie+'; HttpOnly; SameSite=Strict; Path=/')
            self.end_headers()
            try:
                self.wfile.write(body if isinstance(body,bytes) else json.dumps(body).encode())
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass  # Closing a browser cannot cancel the committed operation.
        def do_GET(self):
            route=urlparse(self.path).path
            if route=='/api/bootstrap':return self.send(200,dict(csrf=csrf,test_controls=args.test_controls))
            if route=='/api/state':
                try:return self.send(200,store.snapshot(store.user(self.token())))
                except PermissionError:return self.send(200,dict(user=None))
            files={'/':BASE/'index.html','/preview.js':BASE/'preview.js','/preview.css':BASE/'preview.css',
                   '/walowa.jpg':BASE/'walowa.jpg','/style.css':ROOT/'static/css/style.css'}
            if route=='/renderer.js':return self.send(200,RENDERER.encode(),'text/javascript; charset=utf-8')
            path=files.get(route)
            if not path:return self.send(404,{})
            kind={'.html':'text/html','.js':'text/javascript','.css':'text/css','.jpg':'image/jpeg'}[path.suffix]
            content=path.read_bytes()
            if route=='/style.css':
                # The desktop base is real; unrelated GhostSignal/GX modules aren't part of this host.
                content=re.sub(r'@import[^;]+;', '', content.decode('utf8')).encode('utf8')
            self.send(200,content,kind+'; charset=utf-8' if path.suffix!='.jpg' else kind)
        def do_POST(self):
            if self.headers.get('X-Fixture-CSRF')!=csrf:return self.send(403,dict(error='csrf'))
            if self.headers.get('Origin') not in (None,'http://127.0.0.1:8999'):
                return self.send(403,dict(error='origin'))
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<=size<=2048:raise ValueError('body_too_large')
                data=json.loads(self.rfile.read(size) or '{}')
                route=urlparse(self.path).path
                if route=='/api/login':return self.send(200,dict(ok=True),cookie=store.login(data.get('user','')))
                user=store.user(self.token())
                if route=='/api/logout':
                    store.release(user,str(data.get('document','')))
                    store.logout(self.token())
                    return self.send(200,dict(ok=True),cookie='')
                if route=='/api/result':
                    if not isinstance(data.get('success'),bool):raise ValueError('invalid_result')
                    return self.send(200,store.result(user,data['success']))
                if route=='/api/claim':
                    document=str(data.get('document',''))
                    if not 1<=len(document)<=64:raise ValueError('invalid_document')
                    return self.send(200,store.claim(user,document,explicit=data.get('explicit') is True))
                if route=='/api/release':
                    store.release(user,str(data.get('document','')),closed=data.get('closed') is True)
                    return self.send(200,dict(ok=True))
                if route=='/api/advance' and args.test_controls:
                    seconds=data.get('seconds')
                    if seconds not in (5,900,1800):raise ValueError('invalid_advance')
                    store.advance(seconds)
                    return self.send(200,store.snapshot(user))
                return self.send(404,{})
            except PermissionError as error:return self.send(403,dict(error=str(error)))
            except (ValueError,TypeError) as error:return self.send(400,dict(error=str(error)))
            except Exception as error:
                print('fixture error:',type(error).__name__,flush=True)
                return self.send(500,dict(error='storage_error'))

    def worker():
        while not stop.wait(.5):
            for user in ('cvn-alice','cvn-bob'):
                try:store.tick(user)
                except Exception as error:print('fixture worker:',type(error).__name__,flush=True)
    threading.Thread(target=worker,daemon=True).start()
    server=ThreadingHTTPServer(('127.0.0.1',8999),Handler)
    print('CVN 164.0: http://127.0.0.1:8999 — isolated persistent fixture',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:stop.set();server.server_close()

if __name__=='__main__':main()
