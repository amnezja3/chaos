"""Full desktop renderer, isolated accounts and canonical locale/FM/wallet endpoints.

python tools/sprint_153_browser_fixture.py -> http://127.0.0.1:8993
Unrelated live-world feeds are inert fixtures. No production files or network jobs.
"""
import json
import mimetypes
import os
from pathlib import Path
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / 'tests')]
temporary = tempfile.TemporaryDirectory(prefix='sprint153-browser-')
os.chdir(temporary.name)
os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(temporary.name) / 'sessions')
os.environ['CHAOS_SECRET_KEY'] = 'sprint153-isolated-only'
import run
from database import WalletStore
from tests.test_file_manager_inventory import FileManagerInventoryTest
from tests.test_player_hack_read_paths import valid_profile
from flask import render_template

fixture = FileManagerInventoryTest()
fixture.setUp()
profile = valid_profile('attacker')
profile.update(nick='Własny nick <keep>', avatar='/static/images/avatar-default.jpg',
               storage_capacity=2048, storage_used=0, storage_unit='MB', fraction={'id':'3','role':'2'},
               security={'stealth_mode': True}, files={'tools':[], 'download':[]})
fixture.users.save_profile_guarded(profile, source='profile_manager.registration', expected_revision=0, allow_create=True)
fixture.users.save_profile_guarded(valid_profile('recipient'), source='profile_manager.registration', expected_revision=0, allow_create=True)
fixture.stack.enter_context(patch.object(run, 'wallet_store', WalletStore(fixture.path)))
fixture.stack.enter_context(patch.object(run, 'sync_session_profile', side_effect=lambda **kwargs: fixture.users.get_profile('attacker')))
run.app.jinja_env.auto_reload = True
generation = fixture.client.environ_base['HTTP_X_CHAOS_SESSION_GENERATION']


class Handler(BaseHTTPRequestHandler):
    def route(self):
        path = self.path.split('?')[0]
        headers = {'X-Chaos-Session-Generation':generation, 'X-Chaos-Session-User':'attacker'}
        content_type = 'application/json'
        status = 200
        if path.startswith('/static/'):
            target = (root / path.lstrip('/')).resolve()
            if not target.is_relative_to(root / 'static') or not target.is_file():
                self.send_error(404)
                return
            body = target.read_bytes()
            content_type = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        elif path == '/map-menu-locale.js':
            source = (root / 'templates/map_template.html').read_text(encoding='utf-8')
            start = source.index('function showHackingMenuForMarker(')
            end = source.index('// function showHackingMenuForMarker(', start)
            label_start = source.index('function mapTargetLabelHtml(')
            label_end = source.index('function targetStableId(', label_start)
            body = (source[label_start:label_end] + '\n' + source[start:end]).encode()
            content_type = 'application/javascript; charset=utf-8'
        elif path == '/map-workspace-locale.js':
            source = (root / 'templates/map_template.html').read_text(encoding='utf-8')
            boundaries = [('mapResponseText', 'handleForeignTerritoryProtectedResponse'),
                          ('ensureMapScanOverlay', 'normalizeBootLoadedScopes'),
                          ('showContextMenu', 'showMarkerContextMenu'),
                          ('showCapturedObjectMenu', 'confirmCapturedObjectAbandon'),
                          ('showMenuForHacked', None),
                          ('repaintSecurityMenuSafe', 'secureAction'),
                          ('showVulnerabilityReporterMenu', 'markerMenuAction')]
            parts = []
            for name, following in boundaries:
                start = source.index('function ' + name + '(')
                end = source.index('function ' + following + '(', start) if following else source.index('window.MAP_ACTION_DEBUG', start)
                parts.append(source[start:end].rstrip().removesuffix('async').rstrip())
            body = '\n'.join(parts).encode()
            content_type = 'application/javascript; charset=utf-8'
        elif path == '/map-operation-locale.js':
            source = (root / 'templates/map_template.html').read_text(encoding='utf-8')
            operations = source[source.index('window.operationLabel ='):source.index('if (!window.activeOperationClockTimer)')]
            actors = source[source.index('window.playerActorRelationLabels ='):source.index('window.requestPlayerActorFriend =')]
            abandon = source[source.index('async function confirmCapturedObjectAbandon('):source.index('function removeAbandonedCapturedObject(')]
            body = (operations + '\n' + actors + '\n' + abandon).encode()
            content_type = 'application/javascript; charset=utf-8'
        elif path == '/map-result-locale.js':
            source = (root / 'templates/map_template.html').read_text(encoding='utf-8')
            start = source.index('function mapResponseText(')
            end = source.index('function findClanVulnerabilityForTarget(', start)
            action = source.index('async function mapAction(')
            action_end = source.index('const bikeDirectionIcons', action)
            body = (source[start:end] + '\n' + source[action:action_end]).encode()
            content_type = 'application/javascript; charset=utf-8'
        elif path == '/frame':
            with run.app.test_request_context('/frame'):
                run.session['user'] = 'attacker'
                body = render_template('locale_test_frame.html').encode()
            content_type = 'text/html; charset=utf-8'
        elif path == '/api/profile':
            data = fixture.users.get_profile('attacker')
            data['desktop_settings'] = fixture.identity.get_desktop_boot('attacker')['desktop_settings']
            body = json.dumps(data).encode()
        elif path == '/legacy-catalog-locale':
            from catalog_presentation import legacy_presentation, legacy_sources
            seeds = json.loads((root / 'static/app_config.json').read_text(encoding='utf8'))
            body = json.dumps([legacy_presentation(item) for item in seeds if item['id'] in legacy_sources()]).encode()
        elif path in ('/api/ghostlab/files', '/api/ghostlab/documents'):
            body = b'{"files":[]}'
        elif path in ('/system-messages', '/launch-queue'):
            body = b'[]'
        elif path == '/api/state/changes':
            body = b'{"changes":[],"version":0}'
        elif path == '/api/ghost-radio/state':
            body = b'{"channels":[],"tracks":[]}'
        elif path in ('/', '/api/profile/desktop', '/api/ghostlab/file-manager', '/api/wallet', '/api/wallet/transfer', '/command', '/session/recover', '/register', '/entry'):
            actual = {'X-Chaos-Session-Generation':self.headers.get('X-Chaos-Session-Generation', '')}
            raw = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            if path in ('/', '/entry'):
                fixture.generation.authenticate(fixture.client, 'attacker', generation=generation)
                with run.app.test_request_context('/'):
                    run.session['user'] = 'attacker'
                    body = render_template('login.html' if path == '/entry' else 'linux.html',
                        session_generation={'generation':generation,'username':'attacker'},
                        operation_feedback_flags=run.OPERATION_FEEDBACK_FLAGS,
                        provisional_app_launch_flags={'enabled':False}).encode()
                content_type = 'text/html; charset=utf-8'
            else:
                response = fixture.client.open(self.path, method=self.command, headers=actual, data=raw or None, content_type='application/json')
                body, status, content_type = response.data, response.status_code, response.content_type
                headers.update({k:v for k,v in response.headers if k.lower().startswith('x-chaos-')})
        else:
            body = b'{"success":true,"items":[],"files":[],"channels":[],"changes":[],"version":0}'
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        for key, value in headers.items(): self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)
    do_GET = do_POST = route


if __name__ == '__main__':
    # The test frame lives only in the temporary Jinja loader, never in production routing.
    from jinja2 import ChoiceLoader, DictLoader
    run.app.jinja_loader = ChoiceLoader([DictLoader({'locale_test_frame.html': '''<!doctype html><html><body>
        {% include "_ghost_locale.html" %}<p data-ghost-i18n="shell.desktop.map"></p>
        <input id="draft" value="untouched"><script>window.operations=7;</script></body></html>'''}),run.app.jinja_loader])
    HTTPServer.request_queue_size = 128
    server = HTTPServer(('127.0.0.1',8993),Handler)
    print('READY 153 http://127.0.0.1:8993', flush=True)
    try: server.serve_forever()
    finally:
        server.server_close()
        fixture.doCleanups()
        os.chdir(root)
        temporary.cleanup()
