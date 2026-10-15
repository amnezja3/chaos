"""Launch transport with real Chrome/Flask and isolated game data.

Playwright MCP is preferred interactively; this reproducible fallback also runs
where that server is unavailable. Does not prove device/PWA installation.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]


def main():
    with tempfile.TemporaryDirectory(prefix='chaos-launch-browser-') as directory:
        old_cwd = Path.cwd()
        os.chdir(directory)
        os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(directory) / 'sessions')
        os.environ['CHAOS_SECRET_KEY'] = 'isolated-launch-browser-only'
        import run
        import test_session_generation_precommit as fixtures
        from database import UserCapabilityProjectionStore
        from werkzeug.serving import make_server
        from playwright.sync_api import sync_playwright, Error as BrowserError
        # All runtime stores must share the same isolated database: a split test
        # fixture would correctly reject background writes in the precommit guard.
        assert Path(run.user_store.db_path).resolve().is_relative_to(Path(directory).resolve())
        fixture = SimpleNamespace(user_store=run.user_store, wallet_store=run.wallet_balance_store,
                                  db_path=run.user_store.db_path)
        for name in ('alice', 'victim'):
            profile = fixtures.complete_profile(name)
            profile['curently_possition'] = {'lat': 52.2297, 'lng': 21.0122}
            fixture.user_store.save_profile_guarded(profile,
                expected_revision=0, source='test.registration', allow_create=True)
        run.app.config.update(CHAOS_PERSISTENT_SESSION_ENABLED=True, CHAOS_LAUNCH_CONTROLLER_ENABLED=True)
        server = make_server('127.0.0.1', 0, run.app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        errors = []
        console_errors = []
        evidence = []
        try:
            with patch.object(run, 'authenticate_user', side_effect=lambda u, p: u in {'alice', 'victim'} and p == 'fixture-pass'), \
                    patch.object(run, 'capability_projection_store', UserCapabilityProjectionStore(fixture.db_path)), \
                    patch.object(run, 'wallet_balance_store', fixture.wallet_store), \
                    sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel='chrome', headless=True)
                try:
                    for locale, size in [('pl', {'width':1280,'height':800}), ('en', {'width':390,'height':844})]:
                        run.identity_projection_store.update_desktop_settings('alice', {'locale': locale},
                            normalize=run.normalize_desktop_settings)
                        context = browser.new_context(viewport=size, locale=locale)
                        page = context.new_page()
                        page.on('pageerror', lambda error: errors.append(str(error)))
                        page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
                        requests = []
                        page.on('request', lambda req: requests.append(req.url))
                        response = context.request.post(base + '/', form={'username':'alice','password':'fixture-pass'})
                        assert response.status == 200
                        page.goto(base + '/launch')
                        page.locator('#desktop-icons .icon').first.wait_for()
                        page.locator('#boot-preloader').wait_for(state='hidden')
                        assert page.locator('html').get_attribute('lang') == locale
                        page.screenshot(path=str(ROOT / '.playwright-mcp' / f'launch-156-3-{locale}.png'))
                        page.wait_for_function("window.ChaosSessionGeneration?.getState().username === 'alice'")
                        assert page.locator('form.login-form').count() == 0
                        assert page.url == base + '/launch'
                        assert not any('_session_generation=' in item for item in requests), requests
                        assert not any('/?login=' in item for item in requests)
                        # Reload keeps the same identity and has no login request.
                        generation = page.evaluate('ChaosSessionGeneration.getState().generation')
                        page.reload()
                        page.wait_for_function("window.ChaosSessionGeneration?.getState().username === 'alice'")
                        assert page.evaluate('ChaosSessionGeneration.getState().generation') == generation
                        # Map shell requests its context from the parent, not from the shared cookie.
                        page.evaluate("""() => {
                            const frame = document.createElement('iframe'); frame.className = 'map-frame';
                            frame.id = 'launch-test-map'; frame.src = '/map?_embedded=1'; document.body.append(frame);
                        }""")
                        frame = page.frame_locator('#launch-test-map')
                        frame.locator('#session-generation-config').wait_for(state='attached')
                        assert json.loads(frame.locator('#session-generation-config').text_content())['generation'] == generation
                        # Preserve A's parent in memory while the browser cookie becomes B.
                        context.request.post(base + '/', form={'username':'victim','password':'fixture-pass'})
                        try:
                            page.evaluate("""() => {
                                const frame = document.getElementById('launch-test-map');
                                if (frame) frame.contentWindow.location.reload();
                            }""")
                        except BrowserError as error:
                            if 'Execution context was destroyed' not in str(error):
                                raise
                            page.wait_for_url('**/?session_notice=*')
                        # Either the pinned iframe rejects B, or an already-running
                        # protected poll tears down all A documents first. Both are safe.
                        page.wait_for_function("""() => {
                            const frame = document.getElementById('launch-test-map');
                            if (!frame) return true;
                            const text = frame.contentDocument.getElementById('launch-status')?.textContent || '';
                            return text.includes('sesja') || text.includes('session');
                        }""")
                        # Reload A must stop rather than render B. Disable BroadcastChannel
                        # in the fixture isn't needed: request API login doesn't instantiate B.
                        page.goto(base + '/launch')
                        page.locator('#launch-login').wait_for(state='visible')
                        assert page.locator('#desktop-icons').count() == 0
                        # A deliberate successful form login clears the old tab binding.
                        page.locator('#launch-login').click()
                        page.locator('input[name="username"]').fill('alice')
                        page.locator('input[name="password"]').fill('fixture-pass')
                        page.locator('form.login-form button[type="submit"]').click()
                        page.wait_for_url(base + '/launch')
                        page.wait_for_function("window.ChaosSessionGeneration?.getState().username === 'alice'")
                        context.close()
                        evidence.append({'locale':locale, 'viewport':size, 'resume':True, 'stale_iframe':True, 'stale_reload':True})
                    # A failed status request stays neutral and does not delete the cookie.
                    context = browser.new_context(locale='en')
                    context.request.post(base + '/', form={'username':'alice','password':'fixture-pass'})
                    page = context.new_page()
                    page.route('**/api/session/status', lambda route: route.abort())
                    before = context.cookies()
                    page.goto(base + '/launch')
                    page.locator('#launch-retry').wait_for(state='visible')
                    assert page.locator('form.login-form').count() == 0
                    assert context.cookies() == before
                    page.unroute('**/api/session/status')
                    page.locator('#launch-retry').click()
                    page.locator('#desktop-icons .icon').first.wait_for()
                    context.close()
                finally:
                    browser.close()
            assert not errors, errors
            unexpected_console = [message for message in console_errors
                if not any(expected in message for expected in ('409 (CONFLICT)', '401 (UNAUTHORIZED)', 'net::ERR_ABORTED'))]
            assert not unexpected_console, unexpected_console
            print(json.dumps({'ok': True, 'evidence': evidence, 'retry_preserves_cookie': True,
                             'page_errors': errors, 'unexpected_console_errors': unexpected_console,
                             'expected_rejection_console_count': len(console_errors)}))
        finally:
            server.shutdown()
            thread.join(timeout=5)
            os.chdir(old_cwd)


if __name__ == '__main__':
    main()
