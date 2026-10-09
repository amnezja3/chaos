async(page)=>{
    const assert=(v,m)=>{if(!v)throw Error(m);};
    const errors=[],posts=[];page.on('pageerror',e=>errors.push(e.message));
    let purchased=false,flashed=false;
    const fulfill=async(route,json)=>{const res=await page.request.get('http://127.0.0.1:8993/api/profile');await route.fulfill({headers:res.headers(),json});};
    await page.route('**/api/ghostlab/installed/service*/maintenance*',async route=>{
        if(route.request().method()==='POST'){
            posts.push(route.request().postDataJSON());
            await fulfill(route,{success:true,kind:'file_cleanup',count:1,freed_mb:3,message_i18n:{key:'lab.service.cleanup_result',params:{count:1,size:3},content_version:await page.evaluate(()=>GhostLocale.contentVersion)}});
        }else await fulfill(route,{success:true,token:'signed-plan',preview:{kind:'file_cleanup',count:1,size:3,files:[{name:'Mój <plik>',size:3}],can_execute:true,logs:['Autorski <log>']}});
    });
    await page.route('**/api/ghostlab/firmware/service**',async route=>{
        if(route.request().method()==='POST'){
            const body=route.request().postDataJSON();posts.push(body);
            if(route.request().url().endsWith('/purchase'))purchased=true;else flashed=true;
            await fulfill(route,{success:true,succeeded:true,disk_mb:100,scan_m:20});
        }else await fulfill(route,{success:true,state:{crash_id:'',cooldown_until:0},server_time:100,
            pending:purchased?'receipt-stable':null,has_pending:purchased,available:{price:250,artifact_id:'artifact-stable'},policy:{success_percent:50},gains:{disk_mb:100,scan_m:20,storage:{capacity:5000},scan_range_m:1000}});
    });
    await page.route('**/api/ghostlab/scanner/service/activate',async route=>{
        posts.push(route.request().postDataJSON());
        await fulfill(route,{success:true,token:'lease-stable',ttl:35,presentation:{name:'Mój skaner',icon:'X',menu_name:'Autorskie menu',app_id:'service',artifact_id:'artifact-stable'}});
    });
    await page.route('**/api/ghostlab/scanner/lease',async route=>{posts.push(route.request().postDataJSON());await fulfill(route,{success:true,ttl:35});});
    await page.goto('http://127.0.0.1:8993').catch(()=>{});
    await page.evaluate(()=>{sessionStorage.clear();localStorage.clear();});
    await page.goto('http://127.0.0.1:8993');
    await page.evaluate(async()=>{
        const app=document.createElement('section');app.id='service-test';app.style.cssText='position:fixed;inset:10px 10px 80px;overflow:auto;background:#001008;z-index:100';document.body.append(app);
        window.serviceFixture={app,data:{product:{id:'service',template_id:'file_cleanup',runtime_enabled:true,description:'Opis autora <PL>',installed_version:1,artifact_id:'artifact-stable'},available_version:1}};
        await renderGhostLabMaintenance(app,app,serviceFixture.data,()=>{});
    });
    const app=page.locator('#service-test');
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    assert((await app.innerText()).includes('Files to remove: 1'),'cleanup preview EN');
    await app.locator('summary').click();
    assert((await app.innerText()).includes('Mój <plik>'),'file name unchanged');
    await app.locator('[data-maintenance-run]').click();
    const dialog=page.locator('[role=dialog]');
    await dialog.waitFor();
    assert((await dialog.innerText()).includes('Remove 1 files'),'cleanup confirmation EN');
    await dialog.locator('[data-choice=cancel]').click();
    assert(posts.length===0,'cancel is read only');
    await app.locator('[data-maintenance-run]').click();
    await dialog.locator('[data-choice=confirm]').click();
    await page.waitForFunction(()=>document.querySelector('[data-maintenance-progress]').value===100);
    assert(posts.length===1&&posts[0].token==='signed-plan','signed cleanup payload preserved');
    assert((await app.innerText()).includes('Autorski <log>'),'author logs remain literal');
    assert((await app.innerText()).includes('Removed 1 files'),'typed result EN');
    await page.evaluate(async()=>{await renderGhostLabFirmware(serviceFixture.app,serviceFixture.app,serviceFixture.data,()=>renderGhostLabFirmware(serviceFixture.app,serviceFixture.app,serviceFixture.data,()=>{}));});
    await app.locator('[data-buy]').click();
    assert((await dialog.innerText()).includes('250 HC'),'firmware price present');
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert((await dialog.innerText()).includes('Kupić jedną próbę'),'open dialog changes language');
    await dialog.locator('[data-choice=confirm]').click();
    await page.waitForFunction(()=>document.querySelector('[data-flash]')?.disabled===false);
    assert(purchased&&posts[1].expected_price===250&&posts[1].expected_artifact_id==='artifact-stable'&&posts[1].client_action_key,'stable purchase contract');
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    await app.locator('[data-flash]').click();await dialog.locator('[data-choice=confirm]').click();
    await page.waitForFunction(()=>document.querySelector('[data-progress]').value===100);
    assert(flashed&&posts[2].receipt==='receipt-stable','uses purchased receipt');
    assert((await app.innerText()).includes('permanent bonuses saved'),'flash result EN');
    await page.evaluate(()=>DeepScanner.render(serviceFixture.app,serviceFixture.app,serviceFixture.data,()=>{}));
    assert((await app.innerText()).includes('Active: X Autorskie menu'),'scanner EN / UGC');
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert((await app.innerText()).includes('Aktywny: X Autorskie menu'),'scanner live PL');
    await page.setViewportSize({width:390,height:844});
    assert(await app.evaluate(el=>el.scrollWidth<=el.clientWidth+1),'mobile no horizontal overflow');
    await page.evaluate(()=>DeepScanner.stop());
    assert((await app.innerText()).includes('Nakładka wyłączona'),'scanner release status');
    assert(posts.at(-1).token==='lease-stable'&&posts.at(-1).release,'lease released');
    assert(errors.length===0,errors.join('\n'));
    return {status:'PASS',flows:'cleanup cancel/use, firmware purchase/flash, scanner activate/release',errors};
}
