async(page)=>{
    const assert=(value,message)=>{if(!value)throw Error(message);};
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const requests=[];
    const operation={operation_id:'stable-op',operation_type:'vehicle_tracking',operation_family:'gps',target_id:'stable-target',target_label:'Auto <UGC> / EN',remaining_seconds:91,can_cancel:true,distance_available:false,risk:{level:'low',score:2},incident:{active:false},output:{file_category:'gps',directory:'/data/gps',expected_size_mb:2,output_status:'pending'}};
    const snapshot={success:true,operations:[operation],groups:[{operation_family:'gps',count:1,incident_count:0,output_types:['gps']}],active_count:1,incident_count:0};
    await page.route('**/api/ghost-control/operations**',async route=>{
        const response=await page.request.get('http://127.0.0.1:8993/api/profile');
        if(route.request().method()==='GET'){await route.fulfill({headers:response.headers(),json:snapshot});return;}
        requests.push(route.request().postDataJSON());
        await route.fulfill({headers:response.headers(),json:{success:true,cancelled:['stable-op'],snapshot:{...snapshot,operations:[],groups:[],active_count:0}}});
    });
    await page.goto('http://127.0.0.1:8993');
    await page.evaluate(()=>createOperationControlApp());
    const app=page.locator('.operation-control-window');
    await app.locator('[data-operation-id=stable-op]').first().waitFor();
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    assert((await app.innerText()).includes('GPS tracking'),'localized operation type');
    assert((await app.innerText()).includes('Auto <UGC> / EN'),'target untouched');
    assert((await app.innerText()).includes('no position'),'missing position localized');
    await app.locator('[data-operation-control-action=cancel-operation]').click();
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert((await page.locator('[role=dialog]').textContent()).includes('Anuluj operację'),'open dialog changes locale');
    await page.locator('[data-choice=cancel]').click();
    assert(requests.length===0,'declined confirmation sends nothing');
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    await app.locator('[data-operation-control-action=cancel-group]').click();
    await page.locator('[data-choice=confirm]').click();
    await app.locator('.operation-control-empty').waitFor();
    assert(JSON.stringify(requests)==='[{"operation_family":"gps","operation_ids":["stable-op"]}]','stable cancellation payload');
    assert((await app.innerText()).includes('No active operations.'),'localized empty after cancellation');
    await page.setViewportSize({width:390,height:844});
    assert(await app.locator('[data-operation-control-action=refresh]').isVisible(),'mobile refresh visible');
    assert(!errors.length,JSON.stringify(errors));
    return {pass:true,scenarios:['PL/EN rows','UGC','dialog locale switch','declined confirmation','group cancel IDs','empty','mobile'],errors};
}
