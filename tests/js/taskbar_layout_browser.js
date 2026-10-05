// Playwright MCP component regression; start tools/workspace_browser_fixture.js.
async page => {
    await page.goto('http://127.0.0.1:8990/');
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const populate = async count => page.evaluate(count => {
        document.querySelectorAll('.terminal').forEach(win => win.remove());
        runningWindows.clear();
        for (let i = 0; i < count; i++) {
            const win = document.createElement('div');
            win.className = 'terminal';
            win.dataset.appTitle = 'Long application title ' + i;
            win.dataset.appIcon = 'X';
            win.style.display = 'none';
            document.body.append(win);
            registerWindowInTaskbar(win);
        }
        renderRunningApps();
    }, count);
    let passed = 0;
    for (const width of [1440, 1100, 901]) {
        await page.setViewportSize({width, height: 900});
        for (const count of [1, 5, 12, 20, 40, 80]) {
            await populate(count);
            await page.waitForTimeout(50);
            const valid = await page.locator('#system-running-apps').evaluate(box => {
                const bounds = box.getBoundingClientRect();
                return bounds.height === 34 && box.scrollWidth <= box.clientWidth
                    && box.scrollHeight <= box.clientHeight && [...box.children].every(button => {
                        const rect = button.getBoundingClientRect();
                        return (box.dataset.rows !== '2' || Math.abs(rect.width - rect.height) < 1)
                            && rect.width > 0 && rect.height > 0 && rect.left >= bounds.left - 1
                            && rect.right <= bounds.right + 1 && rect.top >= bounds.top - 1
                            && rect.bottom <= bounds.bottom + 1 && button.getAttribute('aria-label');
                    });
            });
            if (!valid) throw Error('Overflow at ' + width + ', ' + count + ' windows');
            passed++;
        }
    }
    await page.setViewportSize({width: 1440, height: 900});
    await populate(24);
    if (await page.locator('#system-running-apps').getAttribute('data-rows') !== '1') throw Error('Premature second row');
    await page.setViewportSize({width: 901, height: 900});
    await page.waitForFunction(() => document.getElementById('system-running-apps').dataset.rows === '2');
    await page.setViewportSize({width: 1440, height: 900});
    await page.waitForFunction(() => document.getElementById('system-running-apps').dataset.rows === '1');
    await page.setViewportSize({width: 390, height: 844});
    if (await page.locator('#system-running-apps').isVisible()) throw Error('Mobile layout changed');
    if (!await page.locator('#system-window-tab-button').isVisible()) throw Error('Mobile switch missing');
    if (errors.length) throw Error(errors.join('\n'));
    return {passed, resize: 'PASS', mobile: 'PASS'};
}
