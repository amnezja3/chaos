async(page)=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));
 const fulfill=async(route,json)=>{const r=await page.request.get('http://127.0.0.1:8993/api/profile');await route.fulfill({headers:r.headers(),json});};
 await page.goto('http://127.0.0.1:8993').catch(()=>{});await page.waitForTimeout(400);await page.goto('http://127.0.0.1:8993');
 await page.route('**/api/creators/policy',route=>fulfill(route,{enabled:false,security_keys:['firewall','vpn']}));
 await page.route('**/api/apps/generate',route=>{requests.push(route.request().postDataJSON());return fulfill(route,{success:true,app:{project_file:'author-project.json'}});});
 await page.setViewportSize({width:1280,height:900});
 for(const [launch,app]of[['createAppForge','appforge'],['createTermCreator','termcreator'],['createWindowMaker','windowmaker'],['createButtonMaker','buttonmaker']]){
   await page.evaluate(async launch=>{window.CreatorEditor={launch:async()=>false};await GhostLocale.changeLocale('en',false);await window[launch]();},launch);
   const win=page.locator('.creator-window[data-app='+app+']');await win.locator('[name=name]').fill('Nazwa autora');await page.evaluate(()=>GhostLocale.changeLocale('en',false));
   assert((await win.innerText()).includes('Give the tool an identity'),'fallback narrative EN '+app);
   await win.locator('[data-creator-step="1"]').click();await win.locator('[name=tool_family]').selectOption('exploit');
   await win.locator('[data-creator-step="2"]').click();await win.locator('[data-appforge-field=target_types] [data-creator-option=vehicle]').click();
   await win.locator('[data-creator-step="3"]').click();await win.locator('[data-appforge-field=map_actions] [data-creator-option=car_hack]').click();
   await page.evaluate(()=>GhostLocale.changeLocale('pl',false));assert(await win.locator('[name=name]').inputValue()==='Nazwa autora','draft retained');assert(await win.locator('[data-appforge-field=map_actions] input[value=car_hack]').isChecked(),'action retained');
   await page.evaluate(()=>GhostLocale.changeLocale('en',false));assert((await win.innerText()).includes('Take over onboard system'),'action EN');
   await win.locator('[data-creator-step="4"]').click();await win.locator('[data-appforge-field=operation_types] [data-creator-option=vehicle_ecu]').click();
   await win.locator('[data-creator-step="8"]').click();assert((await win.innerText()).includes('Publish in Googleplex'),'publish EN');
   await win.locator('button[type=submit]').click();await page.waitForFunction(app=>document.querySelector('.creator-window[data-app='+app+'] .appforge-status').textContent.includes('Project saved'),app);
   const req=requests.at(-1);assert(req.name==='Nazwa autora'&&req.map_actions[0]==='car_hack'&&req.operation_types[0]==='vehicle_ecu','canonical contract');
   await win.locator('.close-btn').click();
 }
 assert(requests.length===4,'one publish per interface');assert(errors.length===0,errors.join('\n'));return {status:'PASS',flows:'four fallback creators PL/EN, draft, canonical action, publish',errors};
}
