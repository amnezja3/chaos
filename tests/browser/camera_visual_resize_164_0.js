async (page) => {
    await page.setViewportSize({width:1440,height:900});
    const viewer = page.locator('[data-camera-viewer]');
    await viewer.waitFor();
    if (await viewer.evaluate(e=>e.classList.contains('is-window-maximized'))) await viewer.locator('.browser-maximize-btn').click();
    const image = viewer.locator('.camera-visual-images img').first();
    const motion = await image.getAttribute('style');
    const original = await viewer.boundingBox();
    if (await viewer.evaluate(e=>getComputedStyle(e).resize)!=='both') throw new Error('Missing native resize');
    await page.mouse.move(original.x+original.width-3, original.y+original.height-3);
    await page.mouse.down();
    await page.mouse.move(original.x+460, original.y+520, {steps:20});
    await page.mouse.up();
    const resized = await viewer.boundingBox();
    if (Math.abs(resized.width-original.width)<100 || Math.abs(resized.height-original.height)<50) throw new Error('Resize handle did not resize both axes');
    if (await image.getAttribute('style')!==motion) throw new Error('Resize changed motion characteristic');
    const hud = await viewer.locator('.camera-visual-hud').boundingBox();
    if (hud.x<resized.x || hud.x+hud.width>resized.x+resized.width) throw new Error('HUD overflows');
    await viewer.locator('[data-camera-panel-link]').click();
    if (await viewer.locator('[data-chaos-link]').count()!==2) throw new Error('Expected only Focus and Teleport');
    const links = viewer.locator('.chaos-link');
    for (const link of await links.all()) {
        const box = await link.boundingBox();
        if (box.x<resized.x || box.x+box.width>resized.x+resized.width) throw new Error('Link overflows');
    }
    await page.screenshot({path:'artifacts/cvn-164-resize-links.png'});
    await viewer.locator('[data-camera-panel-link]').click();
    await page.mouse.move(resized.x+resized.width-3,resized.y+resized.height-3);
    await page.mouse.down();await page.mouse.move(original.x+original.width-3,original.y+original.height-3,{steps:20});await page.mouse.up();
    return {nativeResize:'PASS', responsiveHUD:'PASS', twoLinks:'PASS', motionPreserved:true, resized};
}
