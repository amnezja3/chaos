"""Disposable loopback fixture only. Never connects to production."""
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser=p.chromium.launch()
        try:
            for locale,width in [('pl',1440),('en',390)]:
                context=browser.new_context(viewport={'width':width,'height':900})
                page=context.new_page()
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto('http://127.0.0.1:8997/__fixture/account/alice?locale='+locale)
                page.goto('http://127.0.0.1:8997/account/safety')
                page.locator('#contact-form input').fill('bob')
                page.locator('button[value="block"]').click()
                page.locator('#blocks article').filter(has_text='bob').wait_for()
                page.locator('#blocks button').click()
                page.wait_for_function("document.querySelector('#blocks').children.length===0")
                page.locator('#report-form [name="key"]').fill('bob')
                page.locator('#report-form [name="details"]').fill('UI fixture report')
                page.locator('#report-form button').click()
                page.locator('#reports article').first.wait_for()
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
                assert not errors, errors
                page.screenshot(path=str(Path('.playwright-mcp')/f'safety-{locale}.png'),full_page=True)
                context.close()
            print('PASS: PL desktop and EN mobile; block/unblock/report, DOM, overflow, console')
        finally:
            browser.close()


if __name__=='__main__':
    main()
