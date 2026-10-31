async (page) => {
    // Fault injection only at the ownership boundary; real login/state/media.
    let first = true, blocked = true, mediaRequests = 0, identityHeaders = {};
    const count = request => { if (request.url().includes('/api/camera-visual/media/')) mediaRequests++; };
    page.on('request', count);
    const fault = async route => {
        if (first) {
            const response = await route.fetch();
            identityHeaders = response.headers();
            const data = await response.json();
            if (data.granted) { data.lease_until = Date.now()/1000 + 4; first = false; }
            return route.fulfill({response, json:data});
        }
        if (blocked) return route.fulfill({status:503, headers:identityHeaders, json:{success:false,reason:'camera_storage_busy'}});
        return route.continue();
    };
    await page.route('**/api/camera-visual/window', fault);
    try {
        await page.reload();
        await page.waitForSelector('[data-camera-viewer]');
        await page.waitForFunction(()=>[...document.querySelectorAll('img[data-camera-frame]')].every(i=>i.naturalWidth>0));
        await page.evaluate(()=>{window.__cameraOriginal=document.querySelector('[data-camera-viewer]');});
        await page.waitForSelector('.camera-suspended');
        if (!await page.locator('.camera-visual-frame').evaluate(e=>getComputedStyle(e,'::after').backgroundImage.includes('signal-dropout.svg'))) throw new Error('Missing dropout asset');
        await page.locator('[data-camera-viewer]').screenshot({path:'artifacts/cvn-164-effects-dropout.png'});
        const countBefore = mediaRequests;
        await page.waitForTimeout(16000);
        if (!await page.evaluate(()=>document.querySelector('[data-camera-viewer]')===window.__cameraOriginal)) throw new Error('Window recreated during outage');
        blocked = false;
        await page.waitForFunction(()=>!document.querySelector('[data-camera-viewer]')?.classList.contains('camera-suspended'), {}, {timeout:20000});
        if (!await page.evaluate(()=>document.querySelector('[data-camera-viewer]')===window.__cameraOriginal)) throw new Error('Window recreated during recovery');
        if (mediaRequests!==countBefore) throw new Error('Images reloaded during recovery');
        return {stableDOM:true, mediaReloads:0, recovery:'PASS'};
    } finally {
        blocked = false; await page.unroute('**/api/camera-visual/window', fault);
        page.off('request', count);
    }
}
