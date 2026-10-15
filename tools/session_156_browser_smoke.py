"""Real Chrome + Flask session/CSRF UI smoke; isolated temporary DB and storage.

Requires Playwright and installed Chrome. No production server or game data.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]


def main():
    with tempfile.TemporaryDirectory(prefix='chaos-156-browser-') as directory:
        old_cwd = Path.cwd()
        os.chdir(directory)
        os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(directory) / 'sessions')
        os.environ['CHAOS_SECRET_KEY'] = 'isolated-browser-fixture-only'
        import run
        import test_session_generation_precommit as fixtures
        from werkzeug.serving import make_server
        from database import db_connect
        from session_generation_store import generation_digest
        from playwright.sync_api import sync_playwright
        fixture = fixtures.SessionGenerationPrecommitTests()
        fixture.setUp()
        clock = [datetime.now(timezone.utc)]
        fixture.generation_store.clock = lambda: clock[0]
        run.app.config['CHAOS_PERSISTENT_SESSION_ENABLED'] = True
        server = make_server('127.0.0.1', 0, run.app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        errors = []
        try:
            with patch.object(run, 'authenticate_user', side_effect=lambda u, p: u == 'alice' and p == 'fixture-pass'), \
                    sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel='chrome', headless=True)
                try:
                    for locale, size in [('pl', {'width':1280,'height':800}), ('en', {'width':390,'height':844})]:
                        record = fixture.user_store.get_profile_with_revision('alice')
                        record['profile']['desktop_settings']['locale'] = locale
                        fixture.user_store.save_profile_guarded(record['profile'],
                            expected_revision=record['profile_revision'], source='test.locale')
                        context = browser.new_context(viewport=size, locale=locale)
                        page = context.new_page()
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                        login = context.request.post(base + '/', form={'username':'alice','password':'fixture-pass'}, max_redirects=0)
                        assert login.status == 302, login.status
                        target = login.headers['location'].replace('/desktop?', '/logout?')
                        page.goto(base + target)
                        page.locator('#logout').wait_for()
                        assert page.locator('html').get_attribute('lang') == locale
                        assert page.locator('#logout').inner_text() == ('Wyloguj' if locale == 'pl' else 'Log out')
                        config = json.loads(page.locator('#session-generation-config').text_content())
                        # Seed time after the first login without waiting five real minutes.
                        clock[0] += timedelta(minutes=6)
                        with page.expect_response(lambda r: r.url.endswith('/api/session/activity')) as activity:
                            page.locator('h1').click()
                        assert activity.value.status == 200, activity.value.status
                        with db_connect(fixture.db_path, enforce_request_guard=False) as conn:
                            renewed_at = conn.execute('SELECT last_activity_at FROM session_generation_lineages WHERE generation_hash=?',
                                (generation_digest(config['generation']),)).fetchone()[0]
                        assert datetime.fromisoformat(renewed_at) == clock[0]
                        # The old GET is confirmation only. A CSRF-less POST fails.
                        rejected = context.request.post(base + '/logout', headers={
                            'X-Chaos-Session-Generation':config['generation'], 'Origin':base}, timeout=10000)
                        assert rejected.status == 403, rejected.status
                        with page.expect_response(lambda r: r.url.endswith('/logout') and r.request.method == 'POST') as logout:
                            page.locator('#logout').click()
                        assert logout.value.status == 200, logout.value.status
                        assert 'set-cookie' not in logout.value.headers
                        page.wait_for_url('**/?session_notice=session.signed_out')
                        assert page.locator('form.login-form').is_visible()
                        context.close()
                finally:
                    browser.close()
            assert not errors, errors
            print(json.dumps({'ok':True, 'desktop_pl':True, 'mobile_en':True, 'console_errors':errors}))
        finally:
            server.shutdown()
            thread.join(timeout=5)
            fixture.tearDown()
            os.chdir(old_cwd)


if __name__ == '__main__':
    main()
