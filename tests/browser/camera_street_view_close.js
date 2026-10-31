async(page)=>{
    await page.waitForSelector('img[data-camera-frame].is-active');
    const fault=async route=>{
        const data=route.request().postDataJSON();
        if(data.action==='close')return route.abort('failed');
        return route.continue();
    };
    await page.route('**/api/camera-visual/window',fault);
    await page.locator('[data-camera-viewer] .close-btn').click();
    await page.getByText('Nie zapisano zamknięcia. Spróbuj ponownie.').waitFor();
    if(await page.locator('[data-camera-viewer]').count()!==1)throw Error('Failed close removed viewer');
    await page.unrouteAll({behavior:'wait'});
    await page.locator('[data-camera-viewer] .close-btn').click();
    await page.waitForFunction(()=>!document.querySelector('[data-camera-viewer]'));
    const logout=await page.evaluate(async()=>{const response=await fetch('/logout',{method:'POST'});return response.status;});
    if(logout!==200)throw Error('Logout '+logout);
    // The session bridge performs navigation after the logout response.
    await page.locator('[name=username]').waitFor();
    await page.locator('[name=username]').fill('main');
    await page.locator('[name=password]').fill('cvn-local-164-only');
    await page.locator('button[type=submit]').click();
    await page.waitForURL('**/desktop**');
    await page.waitForFunction(()=>!!window.CameraVisualPilot);
    await page.waitForTimeout(3000);
    if(await page.locator('[data-camera-viewer]').count())throw Error('Relogin reopened consumed grant');
    return {failedCloseKeepsWindow:true,confirmedClose:true,reloginNoReopen:true};
}
