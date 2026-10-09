async(page)=>{
    const assert=(ok,message)=>{if(!ok)throw Error(message);};
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto('http://127.0.0.1:8993').catch(()=>{});
    await page.waitForTimeout(300);
    await page.evaluate(()=>{sessionStorage.clear();localStorage.setItem('ghost_radio_autoplay','0');});
    await page.goto('http://127.0.0.1:8993');
    const version=await page.evaluate(()=>GhostLocale.contentVersion);
    const message=key=>({key,params:{},content_version:version});
    await page.route('**/api/profile',async route=>{
        const response=await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:response.headers(),json:{...await response.json(),hackcoins:10000,apps:[]}});
    });
    await page.route('**/api/wallet',async route=>{
        const response=await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:response.headers(),json:{balance:10000,reserved:0,available:10000,transactions:[]}});
    });
    await page.route('**/api/travel-tickets/*',async route=>{
        const response=await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:response.headers(),json:{success:true,offer:{destination:{city:'Londyn'}},counts:{},historical_counts:{},reaction_receipt:null}});
    });
    const builtin={id:'operationControl',name:'Operation Control',description:'Konsola operacji',price:20,required_level:1,
        purchase_confirmation:true,bounded_install:true,presentation_owner:'system',
        presentation_i18n:{name:message('catalog.system.operationControl.name'),description:message('catalog.system.operationControl.description')},
        search_aliases:['active operations'],map_actions:[],operation_types:[],resource_types:[],type:'pro-system-tool'};
    const authored={id:'creator_test',name:'Oryginalna nazwa <keep>',description:'catalog.system.operationControl.description',price:10,type:'scanner',map_actions:['scan_ports']};
    const ticket={id:'ticket_londyn',name:'Bilet: Londyn',description:'Przejazd',price:50,product_type:'travel_ticket',consumable:true,travel_city:'Londyn',
        presentation_owner:'system',presentation_i18n:{name:message('catalog.system.ticket_londyn.name'),description:message('catalog.system.ticket_londyn.description')},search_aliases:['London'],effects:[{type:'travel_city',city:'Londyn'}]};
    await page.route('**/api/catalog',async route=>{
        const response=await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:response.headers(),json:[builtin,authored,ticket]});
    });
    const purchases=[];
    await page.route('**/install-app',async route=>{
        purchases.push({body:route.request().postDataJSON(),key:route.request().headers()['x-client-action-key']});
        const response=await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:response.headers(),json:{status:'success',hackcoins:9980,message_i18n:message('shop.installed'),app:{id:'operationControl'},apps:[],files:{tools:[]}}});
    });
    await page.evaluate(()=>{setToolbarProfile({...toolbarProfile,hackcoins:10000,apps:[]});createBrowser();});
    const app=page.locator('.terminal[data-app="browser"]');
    const search=app.locator('.googolplex-search');
    await search.fill('/all');await search.dispatchEvent('input');
    await app.locator('[data-app-id="operationControl"]').waitFor();
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    const system=app.locator('[data-app-id="operationControl"]');
    assert((await system.textContent()).includes('Monitor active operations'),'builtin description translated');
    assert((await app.locator('[data-app-id="creator_test"]').textContent()).includes('catalog.system.operationControl.description'),'UGC key-shaped text remains literal');
    assert(await search.inputValue()==='/all','query retained on locale switch');
    await app.locator('.gp-category-filter select').selectOption('travel_ticket');
    await app.locator('[data-app-id="ticket_londyn"]').waitFor();
    assert((await app.locator('[data-app-id="ticket_londyn"] h2').textContent()).includes('Ticket: London'),'ticket presentation');
    await app.locator('[data-app-id="ticket_londyn"] [data-googleplex-install]').click();
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert((await page.locator('[role=dialog]').textContent()).includes('Potwierdzenie podróży'),'travel dialog locale switch');
    await page.locator('[data-choice=cancel]').click();
    assert(purchases.length===0,'cancel travel does not buy');
    await app.locator('.gp-category-filter select').selectOption('tools');
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    await system.locator('[data-googleplex-install]').click();
    await page.locator('[data-choice=confirm]').click();
    await page.waitForFunction(()=>document.querySelector('.progress-log')?.textContent.includes('Starting installation'));
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert((await page.locator('.progress-log').textContent()).includes('Rozpoczynanie instalacji'),'running installer changes locale');
    await page.waitForFunction(()=>document.querySelector('.result-msg')?.textContent.includes('Aplikacja zainstalowana'),null,{timeout:20000});
    assert(purchases.length===1 && purchases[0].body.app_id==='operationControl' && purchases[0].body.expected_price===20,'canonical purchase payload');
    assert(purchases[0].key===purchases[0].body.client_action_key,'idempotency key unchanged');
    await page.setViewportSize({width:390,height:844});
    assert(await app.locator('.gp-category-filter select').isVisible(),'mobile category filter');
    assert(errors.length===0,JSON.stringify(errors));
    return {pass:true,scenarios:['catalog PL/EN','UGC','category filter','ticket cancel','purchase confirm','installer locale switch','canonical request/idempotency','mobile'],errors};
}
