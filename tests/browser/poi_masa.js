// Playwright MCP; start tools/poi_browser_fixture.py first. No public upstream.
async (page) => {
    const base = 'http://127.0.0.1:8996';
    const assert = (value, message) => { if (!value) throw Error(message); };
    const mode = value => page.request.get(base + '/__mode/' + value);
    const scan = () => page.evaluate(() => mapAction('scan', 52, 21));
    const calls = async () => (await (await page.request.get(base + '/__stats')).json()).calls;
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const evidence = [];
    for (const width of [1440, 390]) for (const lang of ['pl', 'en']) for (const deep of [false, true]) {
        await page.setViewportSize({width, height:850});
        await mode('upstream');
        await page.goto(base);
        await page.selectOption('#locale', lang);
        if (deep) {
            const activation = await (await page.request.get(base + '/__activate')).json();
            await page.evaluate(token => window.fixtureToken = token, activation.token);
            await page.check('#deep');
        }
        assert((await scan()).scan_outcome === 'success', 'success');
        await mode('stale');
        assert((await scan()).interference.state === 'degraded', 'degraded');
        assert(await page.locator('#markers li').count() === 1, 'stale markers');
        await mode('cold');
        assert((await scan()).interference.state === 'blocked', 'blocked');
        const before = await calls();
        await page.evaluate(async () => { for (let i=0; i<10; i++) await mapAction('scan',52,21); });
        assert(await calls() === before, 'no upstream from blocked clicks');
        assert(await page.locator('#markers li').count() === 1, 'error preserves markers');
        // Refresh has no automatic scan, but the next manual call sees shared policy.
        await page.reload();
        assert(await calls() === before, 'refresh no scan');
        assert((await scan()).interference.state === 'blocked', 'shared block after refresh');
        assert(await calls() === before, 'shared block no upstream');
        evidence.push({width, lang, deep, degraded:true, blocked:true, zeroExtraHTTP:true});
    }
    for (const lang of ['pl', 'en']) {
        await mode('timer'); await page.reload(); await page.selectOption('#locale', lang);
        await page.evaluate(() => { Date.now = () => 1; });
        assert((await scan()).interference.state === 'blocked', 'timer');
        const before = await calls();
        await page.waitForTimeout(2300);
        assert(/Możesz sprawdzić|check the signal again/.test(await page.locator('#poi-channel-status').innerText()), 'expiry not restored');
        assert(await calls() === before, 'no auto-retry');
        await mode('recovering'); assert((await scan()).interference.state === 'recovering', 'real probe');
        await mode('restore'); assert((await scan()).interference.state === 'restored', 'restored');
        await mode('empty'); assert((await scan()).scan_outcome === 'empty', 'empty');
        await mode('invalid'); assert(!(await scan()).interference, 'invalid is not MASA');
        await page.evaluate(() => PoiMasa.accept({interference:{type:'masa', state:'blocked'}}));
        assert(!/\d/.test(await page.locator('#poi-channel-status').innerText()), 'no fictional deadline');
        await page.emulateMedia({reducedMotion:'reduce'});
        assert(await page.locator('#poi-channel-status').evaluate(e => getComputedStyle(e).animationName) === 'none', 'reduced motion');
    }
    assert(!errors.length, JSON.stringify(errors));
    return {evidence, pageErrors:errors, timerRecoveryAndErrors:'PASS'};
}
