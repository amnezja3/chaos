async(page)=>{
    // Metadata-only fixture over a real authorized grant; no provider request.
    let phase='pending',bound=false;
    const patch=async route=>{
        const response=await route.fetch();
        const data=await response.json();
        const windowRoute=route.request().url().endsWith('/window');
        for(const s of data.sessions || [data.camera_visual].filter(Boolean)) {
            if(!s.archive_id || s.viewer_closed)continue;
            if(phase==='pending') {delete s.image_id;s.material=null;s.visual_status='QUEUED';}
            else {
                s.visual_status='READY';
                if(!windowRoute && !bound)delete s.image_id;
                if(s.material)s.material={...s.material,source:'Mapillary',author:'Fixture author',
                    image_id:'123',source_url:'https://www.mapillary.com/app/?pKey=123',
                    license:'CC BY-SA 4.0',license_url:'https://creativecommons.org/licenses/by-sa/4.0/'};
            }
        }
        if(windowRoute && phase==='source')bound=true;
        try { await route.fulfill({response,json:data}); }
        catch(error) { if(!String(error).includes('already handled')) throw error; }
    };
    await page.route('**/api/camera-visual/state',patch);
    await page.route('**/api/camera-visual/window',patch);
    try {
        await page.reload();
        const viewer=page.locator('[data-camera-viewer]');
        await viewer.waitFor();
        await page.waitForFunction(()=>!document.querySelector('.camera-visual-no-signal').hidden);
        await viewer.evaluate(e=>{window.__materialViewer=e;});
        phase='source';
        await page.waitForSelector('img[data-camera-frame].is-active',{timeout:15000});
        if(!await viewer.evaluate(e=>e===window.__materialViewer))throw Error('Material arrival recreated viewer');
        await page.locator('[data-camera-panel-link]').click();
        if(!await page.getByText('Fixture author',{exact:true}).count())throw Error('Wrong attribution');
        const url=page.url();
        await page.locator('.camera-source-actions > a').first().click();
        await page.locator('[data-external-confirm] button').press('Escape');
        if(page.url()!==url || await page.locator('[data-external-confirm]').count())throw Error('External cancel');
        await viewer.screenshot({path:'artifacts/camera-street-view-material.png'});
        return {lateMaterialSameDOM:true,attribution:true,externalCancel:true};
    } finally {
        await page.unrouteAll({behavior:'wait'});
        await page.reload();
    }
}
