async(page)=>{
    const assert=(v,m)=>{if(!v)throw Error(m);};
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    const requests=[];
    let project={id:'project-stable',name:'Mój <produkt>',icon:'🧪',description:'Opis autora PL',template_id:'system_log_reader',template_name:'System Log Reader',tool_category:'intel',status:'draft',revision:1,builds:[],blueprint:{log_limit:5},field_schema:{log_limit:{type:'number',default:5,minimum:1,maximum:10,editable:true,integer:true}},template_definition:{id:'system_log_reader',price:100,presentation_ids:['default'],target_kind:'player',launch_mode:'player_hack_access'},publisher_contract:{runtime_status:'player_hack_access'}};
    const installed={success:true,product:{name:'Mój <produkt>',icon:'🧪',installed_version:1,artifact_id:'artifact-old',runtime_enabled:true,family_id:'systemLogReader'},available_artifact_id:'artifact-new',available_version:2,update_available:true,access:{active:true,victim_username:'target-stable',tools:[{id:'ghostlab_stable',enabled:true}]}};
    const fulfill=async(route,json)=>{const res=await page.request.get('http://127.0.0.1:8993/api/profile');await route.fulfill({headers:res.headers(),json});};
    await page.route('**/api/ghostlab/projects**',async route=>{
        if(route.request().method()==='PATCH'){
            const body=route.request().postDataJSON();requests.push(body);
            project={...project,blueprint:body.blueprint,branding:body.branding,name:body.branding.name,revision:2};
        }
        await fulfill(route,{success:true,project,projects:[project]});
    });
    await page.route('**/api/ghostlab/installed/ghostlab_stable',async route=>{
        if(route.request().method()==='POST'){
            requests.push(route.request().postDataJSON());installed.product.installed_version=2;installed.product.artifact_id='artifact-new';installed.update_available=false;
        }
        await fulfill(route,installed);
    });
    await page.goto('http://127.0.0.1:8993').catch(()=>{});
    await page.evaluate(()=>{sessionStorage.clear();localStorage.clear();});
    await page.goto('http://127.0.0.1:8993');
    await page.evaluate(()=>createGhostLabHub());
    const app=page.locator('[data-app=ghostlab]');
    await app.locator('[data-ghostlab-project-id=project-stable]').waitFor();
    await app.locator('[data-ghostlab-open-project]').click();
    const name=app.locator('[data-ghostlab-branding=name]');
    await name.fill('Nowa <nazwa>');
    await app.locator('[data-ghostlab-blueprint-key=log_limit]').fill('7');
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    assert(await name.inputValue()==='Nowa <nazwa>','unsaved branding preserved');
    assert(await app.locator('[data-ghostlab-blueprint-key=log_limit]').inputValue()==='7','unsaved parameter preserved');
    assert((await app.innerText()).includes('Author description'),'branding label translated');
    assert((await app.innerText()).includes('Log limit'),'schema label translated');
    assert(await app.locator('[data-ghostlab-branding=description]').inputValue()==='Opis autora PL','author description unchanged');
    await app.locator('[data-ghostlab-save-blueprint]').click();
    await page.waitForFunction(()=>document.querySelector('[data-app=ghostlab] .ghostlab-shell')._ghostLabEditingProject.revision===2);
    assert(requests[0].blueprint.log_limit===7 && requests[0].branding.name==='Nowa <nazwa>' && requests[0].revision===1,'save payload stable');
    await page.evaluate(()=>openGhostLabInstalledApp('ghostlab_stable'));
    const tool=page.locator('.pro-tool-window').last();
    assert((await tool.innerText()).includes('Read target logs'),'installed action translated');
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert((await tool.innerText()).includes('Odczytaj logi celu'),'installed action changes live');
    await tool.locator('[data-update] span').click();
    await page.waitForFunction(()=>[...document.querySelectorAll('[data-title]')].some(n=>n.textContent.includes('v2')));
    assert(requests[1].expected_artifact_id==='artifact-old' && requests[1].artifact_id==='artifact-new','explicit update keeps artifact IDs');
    assert(await tool.locator('[data-update]').count()===0,'updated state rendered');
    await page.setViewportSize({width:390,height:844});
    assert(await tool.locator('[data-run]').isVisible(),'mobile action visible');
    assert(!errors.length,JSON.stringify(errors));
    return {pass:true,requests,errors};
}
