"""Local Chrome UI check, isolated world; final submission intercepted deliberately."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    with tempfile.TemporaryDirectory(prefix='chaos-onboarding-ui-') as directory:
        previous = Path.cwd()
        os.chdir(directory)
        os.environ['CHAOS_SESSION_FILE_DIR'] = str(Path(directory) / 'sessions')
        os.environ['CHAOS_SECRET_KEY'] = 'isolated-onboarding'
        import run
        from werkzeug.serving import make_server
        from playwright.sync_api import sync_playwright
        assert Path(run.user_store.db_path).resolve().is_relative_to(Path(directory).resolve())
        server = make_server('127.0.0.1', 0, run.app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        evidence = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(channel='chrome', headless=True)
                try:
                    for locale, width in [('pl', 1280), ('en', 390)]:
                        context = browser.new_context(locale=locale, viewport={'width': width, 'height': 900}, reduced_motion='reduce')
                        page = context.new_page()
                        errors, console, submissions = [], [], []
                        page.on('pageerror', lambda e: errors.append(str(e)))
                        page.on('console', lambda m: console.append(m.text) if m.type == 'error' else None)
                        def finalize(route):
                            submissions.append(route.request.post_data_json)
                            route.fulfill(json={'success': False, 'error_key': 'onboarding.failed'} if len(submissions) == 1
                                          else {'success': True, 'redirect': '/?login=1'})
                        page.route('**/api/register-finalize', finalize)
                        page.goto(base + '/register')
                        page.locator('#username').wait_for()
                        page.locator('[data-entry-locale]').select_option(locale)
                        page.wait_for_function('(locale) => GhostLocale.getLocale() === locale', arg=locale)
                        page.locator('.js-next-step').click()
                        assert page.locator('#error-msg').inner_text()
                        assert page.locator('[data-identity-provider]').count() == 4
                        assert page.locator('[data-identity-provider]').evaluate_all('(items) => items.every(i => i.disabled)')
                        for step in range(6):
                            page.wait_for_function('(step) => currentStep === step', arg=step)
                            assert page.locator('[aria-current="step"]').count() == 1
                            assert page.locator('#progress-label').inner_text() == f'{step + 1}/6'
                            for probe in (width, 320, 768, 1920):
                                page.set_viewport_size({'width': probe, 'height': 900})
                                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (step, probe)
                            page.set_viewport_size({'width': width, 'height': 900})
                            if step == 0:
                                page.locator('#username').fill('ui_operator_' + locale)
                                # Changing language preserves entered data and the step.
                                page.locator('[data-entry-locale]').select_option('en' if locale == 'pl' else 'pl')
                                page.locator('[data-entry-locale]').select_option(locale)
                                assert page.locator('#username').input_value() == 'ui_operator_' + locale
                            elif step == 1:
                                # Every refreshed faction/role asset must decode and retain 2:3.
                                for faction_index in range(4):
                                    page.locator('.faction-options button').nth(faction_index).click()
                                    assert_preview(page)
                                    page.locator('.js-next-step').click()
                                    for role_index in range(5):
                                        page.locator('.role-options button').nth(role_index).click()
                                        assert_preview(page)
                                    page.locator('.ghost-btn.secondary').click()
                                page.locator('.faction-options button').nth(1).click()
                                assert page.locator('.faction-options .selected').count() == 1
                            elif step == 2:
                                page.locator('.role-options button').nth(2).click()
                                page.locator('.ghost-btn.secondary').click()
                                assert page.locator('.faction-options .selected').count() == 1
                                page.locator('.js-next-step').click()
                                assert page.locator('.role-options .selected').count() == 1
                            elif step == 3:
                                page.locator('#password').fill('Fixture1234')
                                page.locator('#confirm_password').fill('Different1234')
                                page.locator('.js-next-step').click()
                                assert page.locator('#error-msg').inner_text()
                                page.locator('#confirm_password').fill('Fixture1234')
                            elif step == 4:
                                page.locator('#email').fill(f'onboarding-{locale}@example.test')
                            else:
                                page.locator('#nick').fill('Operator ' + locale)
                                assert 'ui_operator_' + locale in page.locator('.summary-card').inner_text()
                            page.evaluate('window.scrollTo(0,0)')
                            page.mouse.move(0, 0)
                            if step in (1, 2):
                                selected_image = page.locator('.avatar-button.selected').get_attribute('data-img')
                                assert selected_image in page.locator('#avatar-preview').evaluate('el => el.style.backgroundImage')
                            page.locator('.story-image-wrap img').evaluate('(img) => img.decode()')
                            page.screenshot(path=str(ROOT / f'.playwright-mcp/onboarding-{locale}-{step + 1}.png'), full_page=True)
                            page.locator('.js-next-step').click()
                        page.wait_for_function('!isSubmitting')
                        assert page.locator('#error-msg').inner_text()
                        assert len(submissions) == 1
                        page.locator('.js-next-step').click()
                        page.wait_for_url('**/?login=1')
                        assert len(submissions) == 2
                        assert submissions[1]['faction'] == 2 and submissions[1]['role'] == 3
                        assert submissions[1]['locale'] == locale
                        assert not errors, errors
                        assert not console, console
                        evidence.append({'locale': locale, 'steps': 6, 'widths': [320, 390, 768, 1280, 1920], 'errors': errors})
                        context.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            os.chdir(previous)
        print(json.dumps({'ok': True, 'finalize': 'intercepted; backend covered by test_registration_locale', 'evidence': evidence}))


def assert_preview(page):
    result = page.locator('#avatar-preview').evaluate('''async el => {
        const image = new Image();
        image.src = el.style.backgroundImage.slice(5, -2);
        await image.decode();
        return {width: image.naturalWidth, height: image.naturalHeight,
                fit: getComputedStyle(el).backgroundSize};
    }''')
    assert result['width'] * 3 == result['height'] * 2, result
    assert result['fit'] == 'contain', result


if __name__ == '__main__':
    main()
