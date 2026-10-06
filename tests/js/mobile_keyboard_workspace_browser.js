// Run with Playwright MCP and tools/workspace_browser_fixture.js on port 8990.
// Simulates both mobile viewport resize policies; native game fullscreen is real.
async page => {
    await page.setViewportSize({width:390, height:844});
    await page.goto('http://127.0.0.1:8990/');
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addStyleTag({url:'/static/css/mobile_messenger.css'});
    await page.evaluate(async () => {
        const source = await fetch('/static/js/terminal.js').then(r => r.text());
        const start = source.indexOf('function setupSystemTerminalKeyboardGuard(');
        (0, eval)(source.slice(start, source.indexOf('function addSystemMessage(', start)));
        const viewport = new EventTarget();
        viewport.height = 844; viewport.offsetTop = 0;
        Object.defineProperty(window, 'visualViewport', {configurable:true, value:viewport});
        window.keyboardViewport = viewport;
        window.openKeyboardFixture = app => {
            document.querySelectorAll('.terminal').forEach(node => node.remove());
            const win = fixtureOpen(app);
            win.dataset.mobileSafeMode = 'true';
            if (app === 'system-terminal') {
                win.classList.add('system-terminal-window');
                win.innerHTML = '<div class="title-bar">Terminal<button class="close-btn">X</button></div><div class="terminal-body"><div class="content">History</div><div class="system-terminal-composer"><input class="system-terminal-input terminal-input" value="draft"></div></div>';
                setupSystemTerminalKeyboardGuard(win);
            } else {
                win.classList.add('mail-window-narrow');
                win.innerHTML = '<div class="title-bar">Cyberner<button class="close-btn">X</button></div><div class="mail-app" data-mobile-view="chat"><div class="mail-sidebar"></div><div class="mail-main mail-chat"><div class="mail-header mail-chat-header">World</div><div class="mail-messages">History</div><form class="mail-message-form mail-composer"><input value="draft"><button>Send</button></form></div></div>';
                const mailStart = source.indexOf('    const updateMailViewportInset =');
                const mailEnd = source.indexOf('    const updateMailNarrowMode =', mailStart);
                const updateMail = new Function('mailApp', source.slice(mailStart, mailEnd)
                    + '; return updateMailViewportInset;')(win.querySelector('.mail-app'));
                updateMail();
                keyboardViewport.addEventListener('resize', updateMail);
            }
            updateWorkspaceBounds();
        };
    });
    const results = [];
    for (const gameFullscreen of [false, true, false]) {
        await page.evaluate(async fullscreen => {
            if (fullscreen) await document.documentElement.requestFullscreen();
            else if (document.fullscreenElement) await document.exitFullscreen();
        }, gameFullscreen);
        for (const app of ['system-terminal','email']) {
          for (const appMaximized of [false, true]) {
            await page.evaluate(app => openKeyboardFixture(app), app);
            await page.evaluate(maximized => {
                document.querySelector('.terminal').classList.toggle('is-window-maximized', maximized);
                updateWorkspaceBounds();
            }, appMaximized);
            await page.locator('.terminal input').focus();
            for (const [layoutHeight, visibleHeight, offsetTop] of [[844,844,0],[844,480,0],[844,450,30],[480,480,0],[844,844,0]]) {
                await page.setViewportSize({width:390,height:layoutHeight});
                await page.evaluate(({visibleHeight,offsetTop}) => {
                    Object.assign(keyboardViewport, {height:visibleHeight,offsetTop});
                    keyboardViewport.dispatchEvent(new Event('resize'));
                }, {visibleHeight,offsetTop});
                await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
                const state = await page.evaluate(() => {
                    const win=document.querySelector('.terminal'), input=win.querySelector('input');
                    const toolbar=document.getElementById('system-toolbar').getBoundingClientRect();
                    const rect=win.getBoundingClientRect(), box=input.getBoundingClientRect();
                    return {windowBottom:rect.bottom, toolbarTop:toolbar.top, toolbarBottom:toolbar.bottom,
                        inputBottom:box.bottom, inputTop:box.top, draft:input.value};
                });
                if (Math.abs(state.windowBottom-state.toolbarTop)>1 || Math.abs(state.toolbarBottom-visibleHeight-offsetTop)>1
                    || state.inputBottom>state.toolbarTop || state.toolbarTop-state.inputBottom>40 || state.inputTop<offsetTop || state.draft!=='draft') {
                    throw Error(JSON.stringify({app,appMaximized,gameFullscreen,layoutHeight,visibleHeight,offsetTop,state}));
                }
                results.push({app,appMaximized,gameFullscreen,layoutHeight,visibleHeight,offsetTop});
            }
          }
        }
    }
    if (errors.length) throw Error(errors.join('\n'));
    return {passed:results.length, pageErrors:errors, keyboard:'simulated visualViewport; native fullscreen toggled'};
}
