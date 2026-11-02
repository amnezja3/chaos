async page => {
    // Real local desktop: tools/camera_visual_local.py --system-test.
    // Requires a naturally completed feed after POST /api/ghostnetwork/ability
    // and a map launch. No mocked HTTP, time travel or manually granted file.
    const read = () => page.evaluate(async () => {
        const data = await (await fetch('/api/camera-visual/state')).json();
        return data.sessions.filter(s => s.target?.parent_target_id === 'local-system-shop');
    });
    const first = (await read()).find(s => s.state === 'ready');
    if (!first) throw Error('Complete the powered local camera operation first');
    const checks = [];
    const check = (ok, name) => { if (!ok) throw Error(name); checks.push(name); };
    check(first.ready_at - first.download_at === 30, 'Insider Feed: 180s / 6 = 30s');
    const selector = `[data-camera-viewer="${first.instance_id}"]`;
    await page.waitForSelector(selector);
    check(await page.locator(selector).getAttribute('data-app-interface') === 'window', 'native Ghost window');
    check(await page.locator(selector + ' img[data-camera-frame]').count() === 1, 'one selected photo');
    check(await page.locator(selector + ' img[data-camera-frame]').evaluate(i => i.naturalWidth > 0), 'authorized photo decoded');
    await page.reload({waitUntil:'domcontentloaded'});
    await page.waitForSelector(selector, {timeout:30000});
    const restored = (await read()).find(s => s.reference_id === first.reference_id);
    check(JSON.stringify(first.feed) === JSON.stringify(restored.feed), 'reload preserves image, motion and FX');
    check(await page.locator(selector).count() === 1, 'reload creates no duplicate');
    await page.locator(selector + ' .close-btn').click();
    await page.waitForFunction(async receipt => {
        const s = (await (await fetch('/api/camera-visual/state')).json()).sessions.find(x=>x.reference_id===receipt);
        return s?.state === 'consumed';
    }, first.reference_id);
    await page.reload({waitUntil:'domcontentloaded'});
    check(await page.locator(selector).count() === 0, 'closed viewer stays consumed');
    const launched = await page.evaluate(async target => {
        const response = await fetch('/hack-action', {method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({...target,action:'camera_stream',selected_app_id:'admin_seed_camera_stream_v1',
                _client_action_key:'system-browser-target',_flow_id:'system-repeat-'+crypto.randomUUID()})});
        const body = await response.json();
        return {http:response.status,success:body.success};
    }, first.target);
    check(launched.http === 200 && launched.success, 'new invocation accepted after consumption');
    return {checks,firstReceipt:first.reference_id,next:'Wait for the real new operation and viewer; do not grant it manually.'};
}
