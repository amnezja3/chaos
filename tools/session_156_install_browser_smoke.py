"""Local Chrome fallback for environments without Playwright MCP; isolated DB."""
import os
from pathlib import Path
import sys
import tempfile
import threading
import json
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]


def main():
    with tempfile.TemporaryDirectory(prefix='chaos-install-browser-') as directory:
        previous = Path.cwd()
        os.chdir(directory)
        os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(directory) / 'sessions')
        os.environ['CHAOS_SECRET_KEY'] = 'isolated-install-browser'
        import run
        import test_session_generation_precommit as fixtures
        from werkzeug.serving import make_server
        from playwright.sync_api import sync_playwright
        assert Path(run.user_store.db_path).resolve().is_relative_to(Path(directory).resolve())
        profile = fixtures.complete_profile('alice')
        profile['curently_possition'] = {'lat':52.2297, 'lng':21.0122}
        run.user_store.save_profile_guarded(profile, expected_revision=0, source='test.registration', allow_create=True)
        run.app.config.update(CHAOS_INSTALL_UI_ENABLED=True, CHAOS_PERSISTENT_SESSION_ENABLED=True, CHAOS_LAUNCH_CONTROLLER_ENABLED=True)
        server = make_server('127.0.0.1', 0, run.app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        evidence = []
        try:
            with sync_playwright() as p, patch.object(run, 'authenticate_user', return_value=True):
                browser = p.chromium.launch(channel='chrome', headless=True)
                try:
                    for locale, width in [('pl',1280),('en',390)]:
                        context = browser.new_context(locale=locale, viewport={'width':width,'height':900})
                        page = context.new_page()
                        errors = []
                        console_errors = []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        page.on('console', lambda message: console_errors.append(message.text) if message.type == 'error' else None)
                        page.goto(base+'/?login=1')
                        page.locator('.install-options summary').wait_for()
                        page.locator('[data-entry-locale]').select_option(locale)
                        page.wait_for_function('(locale) => document.querySelector(".entry-heading").innerText === (locale === "pl" ? "Witaj w CHAOS" : "Welcome to CHAOS")', arg=locale)
                        page.screenshot(path=str(ROOT/f'.playwright-mcp/entry-156-7-{locale}.png'), full_page=True)
                        for probe in ([1920, 768] if locale == 'pl' else [320]):
                            page.set_viewport_size({'width':probe,'height':900})
                            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), probe
                            assert page.locator('.entry-submit').is_visible()
                        page.set_viewport_size({'width':width,'height':900})
                        page.locator('.install-options summary').click()
                        password = page.locator('[name="password"]')
                        page.locator('[data-password-toggle]').click()
                        assert password.get_attribute('type') == 'text'
                        page.locator('[data-password-toggle]').click()
                        assert password.get_attribute('type') == 'password'
                        assert page.locator('.entry-tabs a').get_attribute('href') == '/register'
                        page.locator('[data-chaos-install] .chaos-install-grid button').first.wait_for()
                        assert page.locator('[data-chaos-install] .chaos-install-grid button').count() == 4
                        # Entry locale can be explicitly selected, independent of browser language.
                        page.locator('[data-entry-locale]').select_option(locale)
                        page.wait_for_function('(locale) => window.GhostLocale?.getLocale() === locale', arg=locale)
                        assert page.locator('.entry-heading').inner_text() == ('Witaj w CHAOS' if locale == 'pl' else 'Welcome to CHAOS')
                        page.locator('[data-platform="iOS"]').click()
                        detail = page.locator('[data-install-instructions]')
                        detail.wait_for(state='visible')
                        assert ('Safari' in detail.inner_text())
                        page.locator('[data-platform="Android"]').click()
                        assert 'https://chaos.re' in detail.inner_text()
                        page.locator('[data-platform="Linux"]').click()
                        assert page.locator('a[href="/chaos.desktop"]').is_visible()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                        form = page.locator('.login-form').bounding_box()
                        panel = page.locator('[data-chaos-install]').bounding_box()
                        assert panel['y'] >= form['y'] + form['height'], (form, panel)
                        # Real wheel scrolling; locator.click() can auto-scroll even
                        # when overflow:hidden makes content unreachable to users.
                        page.evaluate('window.scrollTo(0,0)')
                        page.mouse.move(10, 100)
                        page.mouse.wheel(0, 5000)
                        page.wait_for_function('window.scrollY > 0')
                        page.wait_for_function('window.scrollY + innerHeight >= document.documentElement.scrollHeight - 3')
                        page.screenshot(path=str(ROOT/f'.playwright-mcp/install-full-{locale}.png'), full_page=True)
                        page.locator('[data-chaos-install]').screenshot(path=str(ROOT/f'.playwright-mcp/install-156-4-{locale}.png'))
                        page.evaluate('navigator.serviceWorker.ready.then(()=>true)')
                        page.reload()
                        page.locator('[data-entry-locale]').select_option(locale)
                        page.wait_for_function('(locale) => window.GhostLocale?.getLocale() === locale', arg=locale)
                        page.wait_for_function('navigator.serviceWorker.controller !== null')
                        keys = page.evaluate('caches.keys().then(async keys => (await Promise.all(keys.map(async key => (await (await caches.open(key)).keys()).map(r=>r.url)))).flat())')
                        assert len(keys) == 5 and all('/static/pwa/' in key for key in keys), keys
                        # Native event simulation tests UI state, not real OS installation.
                        page.evaluate("""() => {const e = new Event('beforeinstallprompt');
                            e.prompt=async()=>{};e.userChoice=Promise.resolve({outcome:'dismissed'});
                            window.dispatchEvent(e);} """)
                        platform = page.evaluate('ChaosInstall.platform()')
                        if platform:
                            page.locator('[data-install-now]').click()
                            assert page.locator('[data-chaos-install]').get_attribute('data-state') == 'cancelled'
                            page.evaluate("""() => {const e = new Event('beforeinstallprompt');
                                e.prompt=async()=>{};e.userChoice=Promise.resolve({outcome:'accepted'});
                                window.dispatchEvent(e);} """)
                            page.locator('[data-install-now]').click()
                            assert page.locator('[data-chaos-install]').get_attribute('data-state') == 'accepted'
                        page.evaluate("window.dispatchEvent(new Event('appinstalled'))")
                        assert ('potwierdzona' if locale == 'pl' else 'confirmed') in page.locator('[data-install-status]').inner_text()
                        context.set_offline(True)
                        page.goto(base+'/launch')
                        assert page.locator('#offline-message').is_visible()
                        assert 'alice' not in page.content()
                        context.set_offline(False)
                        page.goto(base+'/?login=1')
                        run.identity_projection_store.update_desktop_settings('alice', {'locale':locale}, normalize=run.normalize_desktop_settings)
                        page.locator('[name="username"]').fill('alice')
                        page.locator('[name="password"]').fill('fixture')
                        page.locator('.entry-submit').click()
                        page.locator('#desktop-icons .icon').first.wait_for(timeout=20000)
                        page.goto(base+'/launch')
                        page.locator('#desktop-icons .icon').first.wait_for(timeout=30000)
                        page.wait_for_function('!!window.ChaosInstall')
                        page.evaluate('createSettings()')
                        page.locator('[data-chaos-install] .chaos-install-grid button').first.wait_for()
                        assert page.locator('[data-chaos-install] .chaos-install-grid button').count() == 4
                        # Launch replaces the document: late install events must
                        # still reach the Settings panel after document.open().
                        page.evaluate("""() => {window.installPromptCalls=0;
                            const e=new Event('beforeinstallprompt');
                            e.prompt=async()=>{window.installPromptCalls++;};
                            e.userChoice=Promise.resolve({outcome:'accepted'});
                            window.dispatchEvent(e);} """)
                        page.locator('[data-install-now]').wait_for(state='visible', timeout=3000)
                        page.locator('[data-install-now]').click()
                        assert page.evaluate('window.installPromptCalls') == 1
                        assert not errors, errors
                        unexpected = [e for e in console_errors if 'net::ERR_INTERNET_DISCONNECTED' not in e and 'net::ERR_ABORTED' not in e]
                        assert not unexpected, unexpected
                        # Rollback is exercised in a real registered browser, not only as source text.
                        if locale == 'en':
                            page.evaluate("caches.open('unrelated-app-cache')")
                            run.app.config['CHAOS_INSTALL_UI_ENABLED'] = False
                            page.evaluate('navigator.serviceWorker.getRegistration().then(r=>r.update())')
                            page.evaluate('''async () => {
                                for(let i=0;i<100;i++) {
                                    const r=await navigator.serviceWorker.getRegistration();
                                    const keys=await caches.keys();
                                    if(!r && !keys.some(k=>k.startsWith('chaos-install-'))) return;
                                    await new Promise(resolve=>setTimeout(resolve,100));
                                }
                                throw new Error('worker retirement did not finish');
                            }''')
                            remaining = page.evaluate('caches.keys()')
                            assert 'unrelated-app-cache' in remaining and not any(k.startswith('chaos-install-') for k in remaining), remaining
                        evidence.append({'locale':locale,'width':width,'cache_entries':len(keys),'errors':errors,'unexpected_console':unexpected})
                        context.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            os.chdir(previous)
        print(json.dumps({'ok':True,'evidence':evidence}))


if __name__ == '__main__':
    main()
