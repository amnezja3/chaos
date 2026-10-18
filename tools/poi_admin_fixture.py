"""Loopback-only admin UI fixture with real routes and isolated account/storage."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]


def main():
    import os
    import tempfile
    from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
    import threading
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='poi-admin-browser-') as directory:
        os.chdir(directory)
        os.environ.update(CHAOS_SESSION_FILE_DIR=str(Path(directory)/'sessions'),CHAOS_SECRET_KEY='fixture-only',
                          CHAOS_POI_PROVIDER_ADMIN_ENABLED='1',CHAOS_POI_CACHE_PATH=str(Path(directory)/'poi.sqlite3'))
        import run
        from test_player_hack_read_paths import PlayerHackReadPathsTest
        fixture=PlayerHackReadPathsTest()
        fixture.setUp()
        fixture.generation.authenticate(fixture.client,'admin')
        client_lock=threading.Lock()
        class Handler(BaseHTTPRequestHandler):
            def route(self):
                path='/dev?tab=poi' if self.path.startswith('/?') or self.path=='/' else self.path
                raw=self.rfile.read(int(self.headers.get('Content-Length',0)))
                headers={}
                if self.command=='POST':
                    headers={'Origin':'http://localhost','X-Chaos-CSRF':self.headers.get('X-Chaos-CSRF','')}
                with client_lock,patch.object(run,'request_ui_locale',return_value='en' if 'fixture_locale=en' in self.path else 'pl'):
                    response=fixture.client.open(path,method=self.command,data=raw or None,content_type='application/json',headers=headers)
                self.send_response(response.status_code)
                for key,value in response.headers:
                    if key.lower() not in ('content-length','connection','transfer-encoding','set-cookie'):
                        self.send_header(key,value)
                self.end_headers()
                try:
                    self.wfile.write(response.data)
                except (BrokenPipeError,ConnectionError):
                    pass  # Browser navigation can cancel a previous refresh.
            do_GET=do_POST=route
        class Server(ThreadingHTTPServer):
            request_queue_size=32
        server=Server(('127.0.0.1',8997),Handler)
        try:
            print('READY http://127.0.0.1:8997',flush=True)
            server.serve_forever()
        finally:
            server.server_close();fixture.doCleanups();os.chdir(ROOT)


if __name__=='__main__':main()
