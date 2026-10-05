// Run with Playwright MCP browser_run_code_unsafe(filename=...) after starting
// node tools/workspace_browser_fixture.js. This tests the real window manager/CSS
// with isolated content, without database or gameplay requests.
async page => {
    await page.goto('http://127.0.0.1:8990/');
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const results = [];
    for (const size of [{width: 1440, height: 1000}, {width: 390, height: 844}]) {
        await page.setViewportSize(size);
        for (const app of ['map', 'territory-control', 'operation-control', 'victim-picker',
            'ghostnetwork-suite', 'appforge', 'termcreator', 'windowmaker', 'buttonmaker',
            'ghostlab', 'browser', 'files', 'email', 'system-terminal', 'ghostsignal-archive']) {
            await page.evaluate(app => {
                const win = fixtureOpen(app);
                win.querySelector('.fixture-scroll').scrollTop = 70;
                win._frame = win.querySelector('iframe');
                win._draft = win.querySelector('textarea');
                bindWindowMaximize(win, app); // Rebinding must not duplicate controls.
            }, app);
            const win = page.locator('[data-app="' + app + '"]');
            await win.frameLocator('iframe').locator('input').fill('retained iframe state');
            await win.locator('.browser-maximize-btn').click();
            const box = await win.boundingBox();
            const toolbarTop = (await page.locator('#system-toolbar').boundingBox()).y;
            if (box.x !== 0 || box.y !== 0 || Math.abs(box.width - size.width) > 1
                || Math.abs(box.height - toolbarTop) > 1) throw Error('fullscreen ' + app);
            const controls = await win.locator('.browser-window-controls').evaluate(bar => {
                const buttons = [...bar.children].map(el => el.getBoundingClientRect());
                const close = bar.querySelector('.close-btn');
                return buttons.length === 3 && buttons.every(b => Math.abs(b.y - buttons[0].y) < 1 && b.height === 30)
                    && getComputedStyle(close).fontSize === '0px'
                    && getComputedStyle(close, '::before').fontSize === '16px';
            });
            if (!controls) throw Error('misaligned or duplicated close ' + app);
            await win.locator('.workspace-minimize-btn').click();
            if (await win.isVisible()) throw Error('minimize ' + app);
            const id = await win.getAttribute('data-window-id');
            if (size.width < 650) await page.locator('#system-window-tab-button').click();
            else await page.locator('.system-task-button[data-window-id="' + id + '"]').click();
            if (!await win.isVisible()) throw Error('restore ' + app);
            if (!await win.evaluate(w => w.classList.contains('is-window-maximized'))) throw Error('lost fullscreen');
            await win.locator('.browser-maximize-btn').click();
            const preserved = await win.evaluate(w => w._frame === w.querySelector('iframe')
                && w._draft === w.querySelector('textarea') && w._draft.value === 'unsaved draft'
                && w.querySelector('.fixture-scroll').scrollTop === 70
                && w.style.top === '60px' && w.style.left === '80px'
                && w.style.width === '620px' && w.style.height === '480px');
            if (!preserved) throw Error('lost state ' + app);
            if (await win.frameLocator('iframe').locator('input').inputValue() !== 'retained iframe state') throw Error('iframe reloaded');
            // Minimize/restore also preserves the normal mode.
            await win.locator('.workspace-minimize-btn').click();
            await page.evaluate(app => bringWindowToFront(document.querySelector('[data-app="' + app + '"]')), app);
            if (await win.evaluate(w => w.classList.contains('is-window-maximized'))) throw Error('lost normal mode');
            results.push(app + ' ' + size.width);
            await win.locator('.close-btn').click();
        }
    }
    if (errors.length) throw Error(errors.join('\n'));
    return {passed: results.length, errors};
}
