async (page) => {
    // Real authenticated gameplay; seek only decorative CSS effects.
    const checks = [];
    const check = (ok, name) => { if (!ok) throw new Error(name); checks.push(name); };
    await page.setViewportSize({width:1440,height:900});
    await page.waitForSelector('img[data-camera-frame].is-active');
    await page.waitForTimeout(2200);
    const result = await page.evaluate(async () => {
        const root='/static/images/camera_visual/effects/';
        const manifest=await (await fetch(root+'manifest.json')).json();
        for(const asset of manifest.assets) {
            const response=await fetch(root+asset.file);
            if(!response.ok) throw new Error(asset.file);
            const image=new Image(); image.src=root+asset.file; await image.decode();
        }
        window.__effectsViewer=document.querySelector('[data-camera-viewer]');
        window.__effectsPhoto=document.querySelector('img[data-camera-frame]');
        return manifest.assets.length;
    });
    check(result===6,'six assets served and decoded');
    check(await page.locator('.camera-visual-effects > div').count()===5,'five live overlays');
    check(await page.locator('.camera-visual-effects').getAttribute('aria-hidden')==='true','decorative layers hidden from accessibility tree');
    check(await page.locator('.camera-visual-effects').evaluate(e=>getComputedStyle(e).pointerEvents==='none'),'actions remain clickable');
    for(const [name,phase] of [['grain',.5],['scan',0],['tracking',.93],['chroma',.95],['blocks',.94]]) {
        const opacity=await page.locator('.camera-fx-'+name).evaluate(async(e,phase)=>{
            const animation=e.getAnimations()[0];
            if(animation) {animation.pause();animation.currentTime=animation.effect.getTiming().duration*phase;}
            await new Promise(requestAnimationFrame);
            return Number(getComputedStyle(e).opacity);
        },phase);
        check(opacity>0,name+' visible');
        await page.locator('[data-camera-viewer]').screenshot({path:'artifacts/cvn-164-effects-'+name+'.png'});
        await page.locator('.camera-fx-'+name).evaluate(e=>{for(const a of e.getAnimations()){a.currentTime=0;a.play();}});
    }
    await page.emulateMedia({reducedMotion:'reduce'});
    check(await page.locator('.camera-visual-effects').evaluate(e=>[...e.children].every(c=>getComputedStyle(c).animationName==='none')),'reduced motion static');
    await page.emulateMedia({reducedMotion:'no-preference'});
    const id=await page.locator('[data-camera-viewer]').getAttribute('data-window-id');
    await page.locator('[data-camera-viewer] .workspace-minimize-btn').click();
    check(await page.locator('.camera-fx-grain').evaluate(e=>getComputedStyle(e).animationPlayState==='paused'),'minimize pauses effects');
    await page.locator(`.system-task-button[data-window-id="${id}"]`).click();
    check(await page.evaluate(()=>document.querySelector('[data-camera-viewer]')===window.__effectsViewer && document.querySelector('img[data-camera-frame]')===window.__effectsPhoto),'same window and image throughout effects');
    return {checks};
}
