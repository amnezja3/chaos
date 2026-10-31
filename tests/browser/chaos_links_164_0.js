async (page) => {
    const v = page.locator('[data-camera-viewer]');
    if (!await v.locator('.camera-visual-panel').isVisible()) await v.locator('[data-camera-panel-link]').click();

    let teleports = 0;
    const count = r => { if (r.url().includes('/api/blacknet/cta/teleport')) teleports++; };
    page.on('request', count);
    try {
        for (const href of ['chaos:teleport/48.864173348628704:2.330499567661377']) {
            await v.locator(`a[href="${href}"]`).click();
            await page.waitForSelector('.blacknet-decision');
            await page.locator('.blacknet-decision [data-choice="cancel"]').click();
        }
        if (teleports!==0) throw new Error('Teleport before confirmation');
        await v.locator('[data-camera-location]').click();
        await page.waitForFunction(()=>{
            const f=document.querySelector('.map-window iframe');
            const marker=f?.contentWindow.blacknetCoordinateFocusLayer;
            return marker && Math.abs(marker.getLatLng().lat-48.864173348628704)<.0001;
        }, {}, {timeout:30000});
        await page.locator('.map-window .close-btn').click();
        const rejected=await page.evaluate(()=>['chaos:delete/cur:loc','chaos:focus/91:2','chaos:teleport/1:181','chaos:focus/1:2;bad'].every(s=>ChaosLinks.parse(s)===null));
        if (!rejected) throw new Error('Invalid link accepted');
        return {teleportConfirmation:'PASS', cancelledTeleportRequests:teleports, cameraLocationFocus:'PASS', invalidLinks:'PASS'};
    } finally {
        page.off('request',count);
    }
}
