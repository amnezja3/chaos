"""Read-only pages and in-place legal dialog on disposable fixture at :8997."""
import time
import socket
import re
from playwright.sync_api import sync_playwright, expect

for attempt in range(120):
    try:
        with socket.create_connection(('127.0.0.1', 8997), timeout=1):
            break
    except OSError:
        time.sleep(1)
else:
    raise RuntimeError('Fixture unavailable')

with sync_playwright() as p:
    browser = p.chromium.launch()
    try:
        for width, locale in [(1440, 'pl'), (390, 'en')]:
            context = browser.new_context(viewport={'width': width, 'height': 900})
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            for kind in ('privacy', 'terms'):
                response = page.goto(f'http://127.0.0.1:8997/{kind}?locale={locale}')
                assert response.status == 200
                assert 'noindex' in response.headers['x-robots-tag']
                expect(page.locator('html')).to_have_attribute('lang', locale)
                expect(page.locator('main')).to_contain_text(re.compile(r'Michał\w* Cezar\w* Jankiewicz\w*'))
                expect(page.locator('main')).to_contain_text('year2108@chaos.re')
                assert page.locator('body').evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1')
                page.screenshot(path=f'.playwright-mcp/legal-{kind}-{locale}.png', full_page=True)
            page.goto('http://127.0.0.1:8997/register')
            field = page.locator('#step-content input').first
            field.fill('LegalTest')
            page.locator('[data-legal-link][href="/privacy"]').click()
            expect(page.locator('.legal-dialog')).to_be_visible()
            expect(page.frame_locator('.legal-dialog iframe').locator('h1')).to_be_visible()
            assert len(context.pages) == 1
            page.keyboard.press('Escape')
            expect(page.locator('.legal-dialog')).not_to_be_visible()
            expect(field).to_have_value('LegalTest')
            assert not errors, errors
            print('PASS', width, locale, 'public documents, dialog, preserved form, no JS errors', flush=True)
            context.close()
    finally:
        browser.close()
