"""Run with fixture --adult --mock-providers. No production accounts or external mail."""
import socket
import time
from playwright.sync_api import sync_playwright, expect

BASE='http://127.0.0.1:8997'
for attempt in range(120):
    try:
        with socket.create_connection(('127.0.0.1',8997),timeout=1):break
    except OSError:time.sleep(1)

with sync_playwright() as p:
    browser=p.chromium.launch()
    try:
        for width,lang in [(1440,'pl'),(390,'en')]:
            context=browser.new_context(viewport={'width':width,'height':960},locale=lang)
            page=context.new_page()
            errors=[]
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(BASE+'/register')
            page.locator('[data-entry-locale]').select_option(lang)
            suffix=str(time.time_ns())[-10:]
            page.locator('#username').fill('Adult'+suffix)
            page.locator('.js-next-step').click()
            page.locator('.faction-options button').first.click()
            page.locator('.js-next-step').click()
            page.locator('.role-options button').first.click()
            page.locator('.js-next-step').click()
            page.locator('#password').fill('Secret123')
            page.locator('#confirm_password').fill('Secret123')
            page.locator('.js-next-step').click()
            page.locator('#email').fill('adult'+suffix+'@example.test')
            page.locator('.js-next-step').click()
            page.locator('#nick').fill('Adult'+suffix)
            expect(page.locator('#age_confirmed')).not_to_be_checked()
            expect(page.locator('#terms')).not_to_be_checked()
            page.locator('.js-next-step').click()
            expect(page.locator('#error-msg')).to_contain_text('18')
            page.locator('#age_confirmed').check()
            page.locator('.adult-declaration [href="/terms"]').click()
            expect(page.locator('.legal-dialog')).to_be_visible()
            page.keyboard.press('Escape')
            expect(page.locator('#age_confirmed')).to_be_checked()
            page.locator('.js-next-step').click()
            expect(page.locator('#error-msg')).to_contain_text('18')
            page.locator('#terms').check()
            assert page.locator('body').evaluate('()=>document.documentElement.scrollWidth<=innerWidth+1')
            page.screenshot(path=f'.playwright-mcp/adult-local-{lang}.png',full_page=True)
            page.route('**/desktop?*',lambda r:r.fulfill(content_type='text/html',body='<h1>Created</h1>'))
            with page.expect_response('**/api/register-finalize') as result:
                page.locator('.js-next-step').click()
            assert result.value.status==200, result.value.text()
            expect(page.locator('h1')).to_have_text('Created')
            assert not errors,errors
            print('PASS local registration',lang,width,flush=True)
            context.close()

        # Existing account accepts using the actual form, before world boot.
        context=browser.new_context(viewport={'width':1440,'height':960})
        page=context.new_page()
        page.goto(BASE+'/__fixture/account/admin?locale=pl')
        expect(page).to_have_url(BASE+'/account/terms')
        page.locator('#age_confirmed').check()
        page.locator('#terms').check()
        page.route('**/launch',lambda r:r.fulfill(content_type='text/html',body='<h1>Accepted</h1>'))
        with page.expect_response('**/api/account/terms') as acceptance:
            page.locator('#adult-acceptance button').click()
        assert acceptance.value.status==200,acceptance.value.text()
        expect(page.locator('h1')).to_have_text('Accepted')
        print('PASS existing account acceptance UI',flush=True)
        context.close()

        # Existing account, restored cookie store, refusal and in-place documents.
        context=browser.new_context(viewport={'width':390,'height':960})
        page=context.new_page()
        page.goto(BASE+'/__fixture/account/alice?locale=en')
        saved=context.storage_state()
        context.close()
        context=browser.new_context(storage_state=saved,viewport={'width':390,'height':960})
        page=context.new_page()
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'/launch')
        expect(page).to_have_url(BASE+'/account/terms')
        expect(page.locator('#age_confirmed')).not_to_be_checked()
        expect(page.locator('#terms')).not_to_be_checked()
        page.locator('#adult-decline').click()
        expect(page.locator('#adult-decline + [data-operation-status]')).to_contain_text('preserved')
        assert context.request.get(BASE+'/api/profile').status==403
        page.locator('.adult-declaration [href="/privacy"]').click()
        expect(page.frame_locator('iframe').locator('h1')).to_have_text('Privacy policy')
        page.keyboard.press('Escape')
        page.screenshot(path='.playwright-mcp/adult-existing-mobile.png',full_page=True)
        # An explicit underage statement persists, cannot be replaced by accepting.
        page.locator('#adult-underage').click()
        expect(page.locator('[role=alert]')).to_contain_text('restricted')
        expect(page.locator('#age_confirmed')).to_have_count(0)
        page.locator('a[href="/account/identity"]').click()
        expect(page.locator('#identity-delete')).to_be_attached()
        assert context.request.get(BASE+'/api/profile').status==403
        page.goto(BASE+'/account/terms')
        page.locator('#adult-logout').click()
        page.wait_for_url('**/?session_notice=session.signed_out')
        assert not errors,errors
        print('PASS restored session, refusal, underage lock, account access and logout',flush=True)
        context.close()
    finally:
        browser.close()
