// Playwright MCP; tools/poi_browser_fixture.py uses production map loading/log code.
async (page) => {
    const assert = (value, message) => { if (!value) throw Error(message); };
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const evidence = [];
    for (const width of [1440, 390]) for (const lang of ['pl', 'en']) {
        await page.setViewportSize({width, height:850});
        await page.goto('http://127.0.0.1:8996');
        await page.selectOption('#locale', lang);
        const result = await page.evaluate(async () => {
            const check = (ok, message) => { if (!ok) throw Error(message); };
            PoiMasa.accept({interference:{type:'masa',state:'blocked',retry_after_seconds:36}});
            const overlay = mapLoadingState.overlay;
            check(overlay.classList.contains('is-slow'), 'second glitch level');
            check(!overlay.classList.contains('is-heavy'), 'not heavy');
            check(overlay.dataset.log.includes('Chaos Log //'), 'shared Chaos Log');
            const hidden = document.getElementById('poi-channel-status');
            check(hidden.getBoundingClientRect().width === 1, 'no visible banner');
            const style = getComputedStyle(overlay, '::after');
            check(style.right === '12px' && style.bottom === '12px', 'bottom right');
            check(style.whiteSpace === 'pre-line', 'full message wraps');
            check(parseFloat(style.width) <= innerWidth - 24, 'fits viewport');
            const token = beginMapLoading('sync test');
            updateMapLoadingStatus('sync test');
            setMapLoadingIntensity('heavy');
            check(overlay.dataset.log.includes(mapLoadingState.log.textContent), 'preserves other log');
            check(overlay.dataset.log.includes('Chaos Log //'), 'preserves MASA log');
            check(overlay.classList.contains('is-heavy'), 'preserves heavier loading');
            endMapLoading(token);
            check(overlay.classList.contains('is-visible') && overlay.classList.contains('is-slow'), 'block persists after loader');
            check(!overlay.classList.contains('is-heavy'), 'loader heavy clears');
            const next = beginMapLoading('sync test');
            updateMapLoadingStatus('sync test');
            setMapLoadingIntensity('normal');
            PoiMasa.accept({interference:{type:'masa',state:'ready'}});
            check(overlay.classList.contains('is-visible'), 'loader survives MASA clear');
            check(!overlay.classList.contains('is-slow'), 'normal loader restored');
            check(overlay.dataset.log === mapLoadingState.log.textContent, 'original log restored');
            endMapLoading(next);
            check(!overlay.classList.contains('is-visible'), 'clean idle');
            PoiMasa.accept({interference:{type:'masa',state:'blocked',retry_after_seconds:0.5}});
            await new Promise(resolve => setTimeout(resolve, 800));
            check(!overlay.classList.contains('is-slow'), 'expiry removes blocking glitch');
            check(!overlay.classList.contains('has-map-log'), 'expiry silently removes log');
            check(document.getElementById('poi-channel-status').textContent === '', 'no expiry announcement');
            return {log:overlay.dataset.log, placement:'bottom-right', secondLevel:true, loaderCoexistence:true};
        });
        await page.emulateMedia({reducedMotion:'reduce'});
        assert(await page.locator('.chaos-map-glitch-overlay').evaluate(e => getComputedStyle(e).animationName) === 'none', 'reduced motion');
        evidence.push({width, lang, ...result});
    }
    assert(errors.length === 0, errors.join('\n'));
    return {evidence, pageErrors:errors};
}
