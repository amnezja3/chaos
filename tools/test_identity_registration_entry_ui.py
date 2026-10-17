"""Run fixture with --mock-providers. Real start/callback, simulated provider exchange."""
from urllib.parse import urlsplit, parse_qs, urlencode
import json
from playwright.sync_api import sync_playwright, expect

BASE = 'http://127.0.0.1:8997'
with sync_playwright() as playwright:
    browser = playwright.chromium.launch()
    try:
        for width in (1440, 390):
            for provider in ('google', 'github', 'discord', 'steam'):
                context = browser.new_context(viewport={'width': width, 'height': 960})
                page = context.new_page()
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                visited = []
                def external(route):
                    parsed = urlsplit(route.request.url)
                    if parsed.path == '/auth/' + provider and parsed.hostname == '127.0.0.1':
                        response = route.fetch(max_redirects=0)
                        assert response.status == 302
                        route.fulfill(content_type='text/html', body='<script>location.assign(' + json.dumps(response.headers['location']) + ')</script>')
                    elif parsed.hostname in ('accounts.google.com', 'github.com', 'discord.com', 'steamcommunity.com'):
                        visited.append(parsed.hostname)
                        query = parse_qs(parsed.query)
                        state = (parse_qs(urlsplit(query['openid.return_to'][0]).query)['state'][0]
                                 if provider == 'steam' else query['state'][0])
                        route.fulfill(status=302, headers={'Location': BASE + '/auth/' + provider + '/callback?' + urlencode({'state': state, 'code': 'fixture'})})
                    else:
                        route.continue_()
                page.route('**/*', external)
                page.goto(BASE + '/register')
                button = page.locator('[data-identity-provider="' + provider + '"]')
                expect(button).to_be_enabled()
                button.locator('svg').click()
                page.wait_for_url('**/auth/register')
                expect(page.locator('[data-setup-step="0"]')).to_be_visible()
                expect(page.locator('input[name=nick]')).to_be_visible()
                assert visited, 'Provider authorization was not reached'
                assert not errors, errors
                print('PASS', width, provider, 'register -> provider -> shortened registration')
                context.close()
    finally:
        browser.close()
