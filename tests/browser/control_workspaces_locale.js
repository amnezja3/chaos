async(page)=>{
    const assert=(v,m)=>{if(!v)throw Error(m);};
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const posts=[];
    const target={target_id:'target-1',label:'VW <UGC> / PL',lat:52,lng:21,icon:'🚙',candidate_source:'profile.targets',target_mode:'standard',can_aim:true,in_range:true,distance_m:250,focus:{lat:52,lng:21},teleport:{lat:52,lng:21},node_role:'pillar',security:{firewall:true},ownership_version:7};
    const candidate={...target};
    const denied={...target,target_id:'blocked',label:'Hidden <UGC>',can_aim:false,disabled_reason:'missing_position',focus:null,teleport:null};
    const cluster={cluster_id:'cluster-1',label:'Area <UGC>',pillars:[target],inners:[],node_count:1,pillar_count:1,inner_count:0,area_size:1500,distance_from_bike:500,threat_state:'collision',conflict_count:1};
    const snapshot={success:true,clusters:[cluster],alone_pillars:[],position:{lat:52,lng:21}};
    const fulfill=async(route,json)=>{const res=await page.request.get('http://127.0.0.1:8993/api/profile');await route.fulfill({headers:res.headers(),json});};
    await page.route('**/api/victim-picker/**',async route=>{
        if(route.request().method()==='POST'){posts.push(route.request().postDataJSON());candidate.is_aimed=true;await fulfill(route,{success:true,target:candidate});}
        else await fulfill(route,{success:true,candidates:[candidate,denied],position:{lat:52,lng:21},action_range_m:1000});
    });
    await page.route('**/api/ghost-control/territory**',async route=>{
        if(route.request().method()==='POST'){posts.push(route.request().postDataJSON());await fulfill(route,{success:true,snapshot});}
        else await fulfill(route,route.request().url().endsWith('/cluster-1')?{success:true,cluster}:snapshot);
    });
    await page.goto('http://127.0.0.1:8993');
    await page.evaluate(()=>{localStorage.clear();sessionStorage.clear();});
    await page.goto('http://127.0.0.1:8993');
    await page.evaluate(()=>{createVictimPickerApp();});
    const victim=page.locator('.victim-picker-window');
    await victim.locator('[data-victim-picker-action=victims]').waitFor();
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    await victim.locator('[data-victim-picker-action=victims]').click();
    assert((await victim.innerText()).toLowerCase().includes('marked'),'source translated');
    assert((await victim.innerText()).includes('VW <UGC> / PL'),'name preserved');
    assert(await victim.locator('[data-victim-picker-action=aim][data-target-id=blocked]').isDisabled(),'denied target stays disabled');
    await victim.locator('[data-victim-picker-action=teleport]').click();
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert((await page.locator('[role=dialog]').innerText()).includes('Wykonać teleport'),'dialog translated while open');
    await page.locator('[data-choice=cancel]').click();
    assert(posts.length===0,'cancel causes no mutation');
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    await victim.locator('[data-victim-picker-action=aim][data-target-id=target-1]').click();
    await page.waitForFunction(()=>document.querySelector('.victim-picker-row.is-aimed'));
    assert(posts.length===1 && posts[0].target_id==='target-1','aim keeps canonical ID');
    await victim.locator('.close-btn').click();
    await page.evaluate(()=>createTerritoryControlApp());
    const territory=page.locator('.territory-control-window');
    await territory.locator('[data-territory-control-action=cluster-detail]').waitFor();
    assert((await territory.innerText()).includes('COLLISION'),'threat translated');
    await territory.locator('[data-territory-control-action=cluster-detail]').click();
    await territory.locator('[data-territory-control-action=object-abandon]').waitFor();
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert((await territory.innerText()).includes('FILARY'),'detail view preserved on language switch');
    await territory.locator('[data-territory-control-action=object-abandon]').click();
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    assert((await page.locator('[role=dialog]').innerText()).includes('Abandon controlled object: VW <UGC> / PL?'),'dialog keeps literal target');
    await page.locator('[data-choice=cancel]').click();
    assert(posts.length===1,'abandon cancel causes no mutation');
    await territory.locator('[data-territory-control-action=security-preset][data-preset=secure]').click();
    await page.waitForFunction(()=>!document.querySelector('.territory-control-window').classList.contains('is-loading'));
    assert(posts[1].preset==='secure' && posts[1].label===target.label,'preset and label unchanged');
    await page.setViewportSize({width:390,height:844});
    assert(await territory.locator('[data-territory-control-action=refresh]').isVisible(),'mobile controls visible');
    assert(!errors.length,JSON.stringify(errors));
    return {pass:true,posts,errors};
}
