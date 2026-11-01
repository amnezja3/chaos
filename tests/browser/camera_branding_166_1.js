async page => {
    // Real local desktop/auth/media/grant; provider metadata and external landing
    // response controlled. Does NOT prove live Mapillary acquisition or PWA.
    const checks = [];
    const check = (ok, name) => { if (!ok) throw Error(name); checks.push(name); };
    const metadata = async route => {
        const response = await route.fetch(), data = await response.json();
        for (const s of data.sessions || [data.camera_visual].filter(Boolean)) {
            if (s.viewer_closed || !s.material) continue;
            s.material = {...s.material, source:'Mapillary', author:'Fixture author',
                image_id:'123', source_url:'https://www.mapillary.com/app/?pKey=123',
                license:'CC BY-SA 4.0', license_url:'https://creativecommons.org/licenses/by-sa/4.0/'};
        }
        await route.fulfill({response,json:data});
    };
    const setup = async p => {
        await p.route('**/api/camera-visual/state', metadata);
        await p.route('**/api/camera-visual/window', metadata);
        await p.goto('http://127.0.0.1:8998/desktop');
        await p.waitForSelector('.camera-visual-brand img');
        await p.waitForFunction(()=>document.querySelector('.camera-visual-brand img')?.naturalWidth>0);
        await p.waitForFunction(()=>document.querySelector('img[data-camera-frame].is-active')?.naturalWidth>0);
        await p.locator('[data-camera-viewer]').evaluate(e => window.__brandingViewer = e);
    };
    let mobileContext;
    const externalStub = route => route.fulfill({contentType:'text/html',body:'<title>Controlled external landing</title>'});
    try {
        await page.context().route('https://www.mapillary.com/**',externalStub);
        await page.setViewportSize({width:1440,height:1000});
        await setup(page);
        const viewer = page.locator('[data-camera-viewer]');
        const logo = viewer.locator('.camera-visual-brand a');
        check(await logo.getAttribute('href')==='https://www.mapillary.com/app/?pKey=123','exact photo hyperlink');
        check(await logo.getAttribute('target')==='_blank' && (await logo.getAttribute('rel')).includes('noopener'),'safe new context');
        check(await logo.locator('img').getAttribute('src')==='/static/images/providers/mapillary/logo_green.svg','official local logo');
        await logo.hover();
        check(await viewer.locator('.camera-visual-brand [role=tooltip]').isVisible(),'desktop hover warning');
        await logo.focus();
        check(await logo.getAttribute('aria-describedby'),'keyboard accessible description');
        const before = await page.evaluate(async()=>{
            const data=await (await fetch('/api/camera-visual/state')).json();
            return data.sessions.filter(s=>s.state==='ready').map(s=>({id:s.instance_id,closed:s.viewer_closed,operation:s.operation_id}));
        });
        const popupPromise = page.waitForEvent('popup');
        await logo.press('Enter');
        const popup = await popupPromise; await popup.waitForLoadState();
        check(popup.url()==='https://www.mapillary.com/app/?pKey=123','keyboard native popup');
        check(await popup.evaluate(()=>window.opener===null),'no opener');
        // Exercise browser visibility contract even in headless Chromium.
        await page.evaluate(()=>{
            Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});
            document.dispatchEvent(new Event('visibilitychange'));
        });
        check(await viewer.evaluate(e=>e===window.__brandingViewer && e.isConnected),'hidden tab preserves DOM');
        await popup.close();
        await page.evaluate(()=>{
            delete document.hidden; document.dispatchEvent(new Event('visibilitychange'));
        });
        await page.waitForFunction(()=>!document.querySelector('[data-camera-viewer]').classList.contains('camera-suspended'));
        const after = await page.evaluate(async()=>{
            const data=await (await fetch('/api/camera-visual/state')).json();
            return data.sessions.filter(s=>s.state==='ready').map(s=>({id:s.instance_id,closed:s.viewer_closed,operation:s.operation_id}));
        });
        check(JSON.stringify(before)===JSON.stringify(after),'same authorized grant and operation, not consumed');
        check(await viewer.evaluate(e=>e===window.__brandingViewer),'return keeps same DOM');
        await viewer.locator('[data-camera-panel-link]').click();
        check(await viewer.locator('.camera-source-actions img').count()===1,'panel official logo');
        check((await viewer.innerText()).includes('Fixture author') && (await viewer.innerText()).includes('CC BY-SA 4.0'),'attribution preserved');
        check((await viewer.locator('[data-camera-provenance]').innerText()).includes('123'),'photo ID preserved');
        const photo = viewer.locator('.camera-source-actions a').nth(1);
        const clickPopup = page.waitForEvent('popup'); await photo.click();
        const other = await clickPopup; await other.close();
        checks.push('panel mouse click opens without confirmation');
        await page.emulateMedia({reducedMotion:'reduce'});
        await logo.hover();
        check(await viewer.locator('.camera-visual-brand [role=tooltip] > span').first().evaluate(e=>getComputedStyle(e).animationName)==='none','reduced motion');
        await page.emulateMedia({reducedMotion:'no-preference'});
        await photo.blur(); await logo.hover(); await page.waitForTimeout(700);
        await viewer.screenshot({path:'artifacts/camera-branding-166-1-desktop.png'});
        await viewer.locator('.browser-maximize-btn').click();
        check(await logo.isVisible(),'logo in maximized window');
        await viewer.locator('.browser-maximize-btn').click();
        // Release the local lease by leaving the desktop, preserving the grant.
        const storage = await page.context().storageState();
        await page.goto('about:blank');
        mobileContext = await page.context().browser().newContext({storageState:storage,
            viewport:{width:390,height:844},isMobile:true,hasTouch:true});
        await mobileContext.route('https://www.mapillary.com/**',externalStub);
        const mobile = await mobileContext.newPage(); await setup(mobile);
        const mLogo = mobile.locator('.camera-visual-brand a');
        await mLogo.tap();
        check(mobileContext.pages().length===1,'first tap does not navigate');
        check(await mobile.locator('.camera-visual-brand .is-armed [role=tooltip]').isVisible(),'first tap warning');
        const mobilePopup = mobile.waitForEvent('popup'); await mLogo.tap();
        const destination = await mobilePopup; await destination.waitForLoadState();
        check(destination.url()==='https://www.mapillary.com/app/?pKey=123','second tap opens photo');
        await destination.close();
        check(await mobile.locator('[data-camera-viewer]').evaluate(e=>e===window.__brandingViewer),'touch preserves viewer');
        await mobile.locator('[data-camera-panel-link]').click();
        const overflow = await mobile.locator('.app-content').evaluate(e=>e.scrollWidth-e.clientWidth);
        check(overflow<=1,'mobile no horizontal content overflow');
        await mLogo.tap(); await mobile.waitForTimeout(700);
        await mobile.locator('[data-camera-viewer]').screenshot({path:'artifacts/camera-branding-166-1-mobile.png'});
        return {checks, count:checks.length, providerMetadata:'controlled fixture', liveAcquisition:false};
    } catch (error) {
        return {checks, failure:String(error)};
    } finally {
        if(mobileContext) {
            for(const p of mobileContext.pages()) await p.unrouteAll({behavior:'wait'});
            await mobileContext.close();
        }
        await page.unrouteAll({behavior:'wait'});
        await page.context().unroute('https://www.mapillary.com/**',externalStub);
    }
}
