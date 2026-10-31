async (page) => {
    // Playwright MCP on the REAL /desktop. Requires a completed local pilot
    // activation and a normal authenticated main session; no stubbed routes.
    const checks = [];
    const check = (value, name) => { if (!value) throw new Error(name); checks.push(name); };
    await page.setViewportSize({width:1440,height:900});
    await page.waitForSelector('[data-camera-viewer]', {timeout:20000});
    const viewer = () => page.locator('[data-camera-viewer]');
    const instance = await viewer().getAttribute('data-camera-viewer');
    check(await viewer().getAttribute('data-app-interface') === 'window', 'standard window interface');
    check(await page.locator('[data-camera-reference]').count() === 0, 'reference closed');
    const before = await viewer().boundingBox();
    const bar = await viewer().locator('.title-bar').boundingBox();
    await page.mouse.move(bar.x+100,bar.y+12);
    await page.mouse.down();await page.mouse.move(bar.x+160,bar.y+50,{steps:8});await page.mouse.up();
    const after = await viewer().boundingBox();
    check(Math.abs(after.x-before.x)>10, 'standard drag');
    await viewer().locator('.browser-maximize-btn').click();
    check(await viewer().evaluate(e=>e.classList.contains('is-window-maximized')), 'maximize');
    await viewer().locator('.browser-maximize-btn').click();
    const windowId = await viewer().getAttribute('data-window-id');
    await viewer().locator('.workspace-minimize-btn').click();
    check(await viewer().evaluate(e=>e.classList.contains('is-window-minimized')), 'minimize');
    await page.locator(`.system-task-button[data-window-id="${windowId}"]`).click();
    check(await viewer().isVisible(), 'taskbar restore');
    check((await viewer().locator('.title-bar').innerText()).includes('Camera Network'), 'system title');
    check(await viewer().locator('.camera-network-icon').evaluate(i=>i.complete && i.naturalWidth>0), 'generated system icon');
    check(await viewer().locator('[data-camera-location]').innerText()==='Focus' && await viewer().locator('[data-chaos-link]').count()===2, 'two compact system actions');
    check(await viewer().locator('.camera-visual-brand').innerText()==='MapiFi', 'MapiFi logo');
    check(await viewer().locator('[data-frame]').count()===0, 'no time-of-day controls');
    await page.waitForFunction(()=>[...document.querySelectorAll('img[data-camera-frame]')].every(i=>i.naturalWidth>0));
    check(await viewer().locator('img[data-camera-frame]').count()===1, 'one authorized image decoded');
    const crop = await viewer().locator('.camera-visual-images img').first().evaluate(i=>({image:i.getBoundingClientRect().width,frame:i.parentElement.getBoundingClientRect().width,transform:getComputedStyle(i).transform}));
    check(Math.abs(crop.image/crop.frame-2)<.01, 'quarter-area crop');
    await page.waitForTimeout(1100);
    check(await viewer().locator('.camera-visual-images img').first().evaluate(i=>getComputedStyle(i).transform)!==crop.transform, 'camera pans');
    check(await viewer().locator('[data-camera-status]').innerText()==='ONLINE' && await viewer().locator('.camera-visual-rec').isVisible(), 'online recording HUD');
    const clock = await viewer().locator('[data-camera-clock]').innerText();
    await page.waitForTimeout(3200);
    check(await viewer().locator('[data-camera-clock]').innerText()!==clock, 'live clock');
    check(await viewer().locator('.camera-visual-logs > div').count()>0 && await viewer().locator('.camera-visual-logs > div').count()<=3, 'bounded connection logs');
    const selected = await viewer().getAttribute('data-camera-frame');
    const source = await viewer().locator('img[data-camera-frame]').getAttribute('src');
    await page.waitForTimeout(26000);
    check(await viewer().getAttribute('data-camera-frame')===selected && await viewer().locator('img[data-camera-frame]').getAttribute('src')===source, 'no image cycling');
    const path = await viewer().locator('img[data-camera-frame]').evaluate(async img => {
        const animation = img.getAnimations().find(a=>a.animationName?.startsWith('camera-path-'));
        const saved = animation.currentTime, duration = animation.effect.getTiming().duration;
        animation.pause();
        const points=[];
        for (const fraction of [0,.25,.5,1,1.5,1.75,2]) {
            animation.currentTime=animation.effect.getTiming().delay+duration*(2+fraction);
            await new Promise(requestAnimationFrame);
            const m=new DOMMatrix(getComputedStyle(img).transform);points.push([m.m41,m.m42]);
        }
        animation.currentTime=saved;animation.play();
        return {duration,points};
    });
    const near=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1])<.1;
    check(path.duration>=180000 && path.duration<=300000, 'slow path duration');
    check(near(path.points[0],path.points[6]) && near(path.points[1],path.points[5]) && near(path.points[2],path.points[4]), 'exact reverse path');
    const [start,,mid,end]=path.points;
    check(Math.abs((mid[0]-start[0])*(end[1]-start[1])-(mid[1]-start[1])*(end[0]-start[0]))>1, 'curved camera path');
    await viewer().locator('[data-camera-panel-link]').click();
    check(await viewer().locator('.camera-visual-panel').isVisible(), 'panel link opens provenance');
    await viewer().locator('[data-camera-panel-link]').click();
    await page.reload();
    await page.waitForSelector('[data-camera-viewer]', {timeout:20000});
    check(await viewer().getAttribute('data-camera-viewer')===instance, 'reload restores durable instance');
    await page.waitForFunction(()=>!!document.querySelector('img[data-camera-frame]')?.naturalWidth && document.querySelector('[data-camera-viewer]')?.dataset.cameraFrame !== undefined);
    check(await viewer().getAttribute('data-camera-frame')===selected, 'reload keeps selected image');
    const other = await page.context().newPage();
    try {
        await other.goto(page.url());
        await other.waitForFunction(()=>typeof window.CameraVisualPilot==='object');
        await page.waitForTimeout(3000);
        check(await viewer().count()+await other.locator('[data-camera-viewer]').count()===1, 'two tabs one viewer');
    } finally { await other.close(); }
    await page.bringToFront();
    await page.waitForSelector('[data-camera-viewer]', {timeout:20000});
    await page.evaluate(()=>GhostLocale.changeLocale('en'));
    await viewer().locator('[data-camera-panel-link]').click();
    check((await viewer().innerText()).includes('AI-generated'), 'English provenance');
    await page.setViewportSize({width:390,height:844});
    await page.emulateMedia({reducedMotion:'reduce'});
    const mobile = await viewer().boundingBox();
    check(mobile.x>=0 && mobile.x+mobile.width<=391, 'mobile bounds');
    await page.screenshot({path:'artifacts/cvn-164-camera-hud-mobile.png'});
    await page.setViewportSize({width:1440,height:900});
    await page.evaluate(()=>GhostLocale.changeLocale('pl'));
    await page.emulateMedia({reducedMotion:'no-preference'});
    // Explicit close consumes the canonical grant; reload is not a reopen path.
    await viewer().locator('.close-btn').click();
    await page.waitForTimeout(2500);
    check(await viewer().count()===0, 'explicit close stays closed');
    await page.reload();
    await page.waitForFunction(()=>typeof CameraVisualPilot==='object');
    await page.waitForTimeout(2500);
    check(await viewer().count()===0, 'reload cannot restore consumed viewer');
    const consumed=await page.evaluate(async()=>{
        const state=await (await fetch('/api/camera-visual/state')).json();
        const closed=state.sessions.find(s=>s.viewer_closed && s.state==='consumed');
        if(!closed) return false;
        const response=await fetch('/api/camera-visual/window',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receipt:closed.reference_id,owner:'browser-replay-test-owner',action:'reopen'})});
        return response.status===409 && (await response.json()).reason==='camera_new_hack_required';
    });
    check(consumed,'server rejects direct reopen');
    check(await page.locator('[data-camera-reopen]').count()===0,'no reopen control');
    return {checks, count:checks.length};
}
