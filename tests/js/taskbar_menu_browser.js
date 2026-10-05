// Run through Playwright MCP with tools/workspace_browser_fixture.js active.
async page => {
    await page.goto('http://127.0.0.1:8990/');
    await page.setViewportSize({width: 1440, height: 1000});
    await page.evaluate(() => {
        const win = fixtureOpen('windowmaker');
        win.querySelector('.close-btn').onclick = () => { win.dataset.closeRequested = '1'; };
    });
    const task = page.locator('.system-task-button');
    const nativePrevented = await task.evaluate(button => !button.dispatchEvent(new MouseEvent('contextmenu', {bubbles: true, cancelable: true})));
    if (!nativePrevented) throw Error('Native context menu allowed');
    await page.keyboard.press('Escape');
    if (await page.locator('#system-task-context-menu').count()) throw Error('Escape did not dismiss');
    await task.click({button: 'right'});
    await page.getByRole('menuitem', {name: 'Zamknij'}).click();
    const win = page.locator('[data-app="windowmaker"]');
    if (await win.getAttribute('data-close-requested') !== '1' || !await win.isVisible()) throw Error('Close handler bypassed');
    if (await win.locator('textarea').inputValue() !== 'unsaved draft') throw Error('Lost unsaved content');
    await page.evaluate(() => document.querySelector('[data-app="windowmaker"] .close-btn').onclick = event => {
        event.target.closest('.terminal').remove(); renderRunningApps();
    });
    await task.click({button: 'right'});
    await page.getByRole('menuitem', {name: 'Zamknij'}).click();
    if (await win.count() || await task.count()) throw Error('Close did not remove window/task');
    return {nativeMenuBlocked: true, escape: 'PASS', closeHandler: 'PASS', unsavedState: 'PASS'};
}
