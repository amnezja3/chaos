"""Run against a fresh identity_gateway_browser_fixture.py on loopback 8997.
Uses real account APIs and the fixture's mock email outbox; no external mail.
"""
import time
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as playwright:
    browser=playwright.chromium.launch()
    try:
        for locale,width,unverified in [('en',1440,False),('pl',390,True)]:
            context=browser.new_context(viewport={'width':width,'height':960})
            page=context.new_page()
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.goto('http://127.0.0.1:8997/__fixture/registration?locale='+locale+'&unverified='+str(int(unverified)))
            expect(page.locator('[data-setup-step="0"]')).to_be_visible()
            expect(page.locator('input[name=email]')).not_to_be_visible()
            page.locator('input[name=nick]').fill('Ui'+locale+str(time.time_ns())[-10:])
            page.locator('#setup-next').click()
            expect(page.locator('[data-faction]')).to_have_count(4)
            page.locator('[data-faction="3"]').click()
            expect(page.locator('[data-faction="3"]')).to_have_attribute('aria-pressed','true')
            assert len(page.locator('#setup-story-copy').inner_text())>20
            page.screenshot(path=f'.playwright-mcp/identity-registration-clans-{locale}.png',full_page=True)
            page.locator('#setup-next').click()
            expect(page.locator('[data-role]')).to_have_count(5)
            page.locator('[data-role="2"]').click()
            page.locator('#setup-back').click()
            page.locator('[data-faction="2"]').click()
            page.locator('#setup-next').click()
            expect(page.locator('input[name=role]')).to_have_value('')
            page.locator('[data-role="3"]').click()
            page.screenshot(path=f'.playwright-mcp/identity-registration-roles-{locale}.png',full_page=True)
            page.locator('#setup-next').click()
            assert page.locator('body').evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1')
            assert page.locator('#setup-summary-avatar').get_attribute('src').endswith('avatar-frakcja-2-player-3.png?v=156-7-art')
            if not unverified:
                expect(page.locator('#registration-send')).not_to_be_visible()
                email=page.locator('input[name=email]').input_value()
                page.locator('input[name=email]').fill('changed@example.test')
                expect(page.locator('#registration-send')).to_be_visible()
                page.locator('input[name=email]').fill(email)
                expect(page.locator('#registration-send')).not_to_be_visible()
            else:
                page.locator('#registration-verify').click()
                expect(page.locator('#registration-email-verification [data-operation-status]')).to_contain_text('Wpisz kod')
                page.locator('#registration-send').click()
                expect(page.locator('#registration-send + [data-operation-status]')).to_contain_text('Kod został wysłany')
                code=context.request.get('http://127.0.0.1:8997/__fixture/mail-code').json()['code']
                page.locator('#registration-code').fill(code)
                page.locator('#registration-verify').click()
                expect(page.locator('#registration-email-state')).to_have_attribute('data-verified','true')
                expect(page.locator('input[name=faction]')).to_have_value('2')
                expect(page.locator('input[name=role]')).to_have_value('3')
                expect(page.locator('#registration-send')).not_to_be_visible()
            page.locator('input[name=terms]').check()
            page.screenshot(path=f'.playwright-mcp/identity-registration-summary-{locale}.png',full_page=True)
            page.route('**/desktop?*',lambda route:route.fulfill(content_type='text/html',body='<h1>Created</h1>'))
            with page.expect_response('**/auth/complete-registration') as response:
                page.locator('#registration-complete').click()
            assert response.value.status==200
            expect(page.locator('h1')).to_have_text('Created')
            assert not errors,errors
            print('PASS',locale,width,'unverified='+str(unverified),'avatars, email, preserved choices, account created')
            context.close()
    finally:
        browser.close()
