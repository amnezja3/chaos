async page => {
    // Controlled presentation/revocation responses over a real local grant.
    // Preserve generation headers, authorization, media endpoint and native DOM.
    let revoke=false;
    const patch=async route=>{
        const response=await route.fetch(),data=await response.json();
        for(const s of data.sessions || [data.camera_visual].filter(Boolean)) {
            if(s.viewer_closed || !s.feed)continue;
            s.feed.visual={scenario:'dropout',intensity:.8,period:45,
                phase:(45-(Date.now()/1000-s.ready_at)%45)%45+1,offline_seconds:5};
            if(revoke){s.material=null;s.visual_status='REVOKED';}
        }
        try {await route.fulfill({response,json:data});}
        catch(error) {if(!String(error).includes('already handled'))throw error;}
    };
    await page.route('**/api/camera-visual/state',patch);
    await page.route('**/api/camera-visual/window',patch);
    try {
        await page.reload();
        await page.waitForSelector('[data-camera-viewer]');
        await page.waitForFunction(()=>document.querySelector('[data-camera-status]')?.textContent==='SIGNAL LOST',{}, {timeout:60000});
        const before=await page.locator('[data-camera-viewer]').getAttribute('data-camera-viewer');
        await page.waitForFunction(()=>document.querySelector('[data-camera-status]')?.textContent==='ONLINE',{}, {timeout:12000});
        revoke=true;
        await page.waitForFunction(()=>document.querySelector('[data-camera-viewer]')?.dataset.materialUnavailable==='1',{}, {timeout:20000});
        await page.waitForTimeout(1300);
        if(await page.locator('[data-camera-status]').innerText()!=='OFFLINE')throw Error('Presentation overrode revoked material');
        if(await page.locator('.camera-visual-no-signal').isHidden())throw Error('Revoked material visible');
        if(await page.locator('[data-camera-viewer]').getAttribute('data-camera-viewer')!==before)throw Error('Viewer recreated');
        return {dropout:true,recovery:true,revocationPriority:true,sameInstance:true};
    } finally {
        await page.unrouteAll({behavior:'wait'});
        await page.reload();
    }
}
