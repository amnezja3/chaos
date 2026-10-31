async (page) => {
    // Run after camera_visual_lifecycle_164_0.js: Alice has a verified activation.
    const checks=[];const check=(ok,label)=>{if(!ok)throw Error(label);checks.push(label);};
    await page.context().clearCookies();
    await page.emulateMedia({reducedMotion:'no-preference'});
    await page.setViewportSize({width:1440,height:1000});
    await page.goto('http://127.0.0.1:8999');
    await page.locator('#login').click();
    const preview=page.locator('[data-kind=preview]');
    await preview.locator('img').waitFor({timeout:12000});
    await preview.locator('img').evaluate(i=>i.decode());
    check(await preview.locator('img').evaluate(i=>i.naturalWidth===960),'Local thumbnail decoded');
    const id=await preview.getAttribute('data-app-id');
    await preview.locator('[data-frame=detail]').click();
    check(await preview.locator('.viewport').getAttribute('data-frame')==='detail','Crop preserves same photograph');
    await preview.locator('[data-frame=full]').click();
    await preview.locator('[data-pause]').click();
    check(await preview.evaluate(e=>e.classList.contains('cvn-paused')),'Pause effects');
    await preview.locator('[data-info]').click();
    await preview.locator('[data-copy]').click();
    check((await preview.locator('#copy-status').innerText()).length>0,'Clipboard feedback');
    check((await preview.locator('.cvn-panel').innerText()).includes('Cybularny'),'Real attribution');
    await preview.locator('[data-external]').click();
    const target=await page.locator('dialog a').getAttribute('href');
    await page.keyboard.press('Escape');
    check(await preview.locator('[data-external]').evaluate(e=>e===document.activeElement),'Escape restores focus');
    await preview.locator('[data-hide]').click();
    for(const [state,label] of [['NO_COVERAGE','NO SIGNAL'],['FAILED','SIGNAL LOST'],['REVOKED','REVOKED']]){
        await preview.locator('.workspace-minimize-btn').click();
        await page.locator('#scenario').selectOption(state);
        await page.locator('#tasks button').filter({hasText:/^GLASS EYE$/}).click();
        await preview.locator('.empty strong').filter({hasText:label}).waitFor();
        check(await preview.locator('img').count()===0,state+' clears photograph');
    }
    await page.screenshot({path:'artifacts/cvn-164-0-b-no-signal.png',fullPage:true});
    await preview.locator('.workspace-minimize-btn').click();
    await page.locator('#scenario').selectOption('READY');
    await page.locator('#tasks button').filter({hasText:/^GLASS EYE$/}).click();
    await preview.locator('img').waitFor();
    await preview.locator('img').evaluate(i=>i.src='data:image/jpeg;base64,YmFk');
    await preview.locator('.empty strong').filter({hasText:'ARCHIVE CORRUPTED'}).waitFor();
    check(await preview.locator('img').count()===0,'Broken image fails without download retry');
    // Reload restores the same instance, never another download.
    await page.reload();
    await page.locator('[data-kind=preview] img').waitFor({timeout:12000});
    check(await page.locator('[data-kind=preview]').getAttribute('data-app-id')===id,'Reload restores durable viewer identity');
    const s=await page.evaluate(()=>fetch('/api/state').then(r=>r.json()));
    check(s.operations.length===1&&s.files.length===1,'Visual failures do not mutate operation or inventory');
    await page.locator('[data-kind=preview] [data-info]').click();
    await page.locator('[data-kind=preview] [data-external]').click();
    await page.route(target,r=>r.fulfill({status:200,contentType:'text/html',body:'<title>Local navigation destination</title>'}));
    await page.locator('dialog a').click();await page.waitForURL(target);
    check(page.url()===target,'Explicit source navigation in same tab');
    await page.unroute(target);
    return {passed:checks.length,checks};
}
