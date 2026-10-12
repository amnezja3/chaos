"""Isolated admin browser fixture. No production DB or external API calls.

python tools/sprint_154_8_browser_fixture.py -> http://127.0.0.1:8998/dev?tab=narrative
"""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]


def main():
    import os
    import tempfile
    from unittest.mock import patch
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from urllib.parse import urlsplit, parse_qs
    temporary=tempfile.TemporaryDirectory(prefix='chaos-provider-ui-')
    os.chdir(temporary.name)
    os.environ['CHAOS_SESSION_FILE_DIR']=str(Path(temporary.name)/'sessions')
    os.environ['CHAOS_SECRET_KEY']='isolated-provider-browser-only'
    import run
    import test_player_hack_read_paths as fixtures
    from ghostnetwork.llm.router import NarrativeRouter
    fixture=fixtures.PlayerHackReadPathsTest()
    fixture.setUp()
    fixture.generation.authenticate(fixture.client,'admin')
    fixture.stack.enter_context(patch.object(run,'request_ui_locale',side_effect=lambda:run.request.args.get('locale','pl')))
    fixture.stack.enter_context(patch.object(NarrativeRouter,'models',return_value=['fixture-model']))
    fixture.stack.enter_context(patch('ghostnetwork.llm.provider_admin.secret_configured',return_value=True))
    fixture.stack.enter_context(patch.object(NarrativeRouter,'verify',return_value={'ok':True,'providers':{'ollama':{'ok':True},'mistral':{'ok':False,'errors':['fixture_unavailable']}}}))
    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            body=self.rfile.read(int(self.headers.get('Content-Length',0)))
            forwarded={'Content-Type':self.headers.get('Content-Type','application/json')}
            if self.headers.get('Origin'):
                forwarded['Origin']=self.headers['Origin'].replace('127.0.0.1:8998','localhost')
            response=fixture.client.open(self.path,method=self.command,data=body,headers=forwarded)
            self.send_response(response.status_code)
            self.send_header('Content-Type',response.content_type)
            for name in ('Location','X-Chaos-Session-Generation','X-Chaos-Session-User','Cache-Control'):
                if name in response.headers:
                    self.send_header(name,response.headers[name])
            self.end_headers()
            self.wfile.write(response.data)
        do_GET=do_POST=handle_request
    server=HTTPServer(('127.0.0.1',8998),Handler)
    print('READY http://127.0.0.1:8998/dev?tab=narrative',flush=True)
    try:server.serve_forever()
    finally:
        server.server_close()
        fixture.doCleanups()
        os.chdir(ROOT)
        temporary.cleanup()


if __name__=='__main__':
    main()
