async(page)=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},errors=[],calls=[];
 page.on('pageerror',e=>errors.push(e.message));
 const fulfill=async(route,json)=>{const response=await page.request.get('http://127.0.0.1:8993/api/profile');await route.fulfill({headers:response.headers(),json});};
 const families=[['systemLogReader','system_logs','.system-log-reader-window'],['securityPanelProxy','security_panel','.security-panel-proxy-window'],['financialSniffer','financial_sniffer','.financial-sniffer-window'],['friendKicker','friend_kicker','.friend-kicker-window'],['arsenalCleaner','arsenal_cleaner','.arsenal-cleaner-window'],['intruderKicker','intruder_kicker','.intruder-kicker-window']];
 await page.route('**/api/player-hack/tool/use',async route=>{
   const body=route.request().postDataJSON();calls.push(body);
   const family=families.find(x=>x[0]===body.tool_id),version=await page.evaluate(()=>GhostLocale.contentVersion);
   await fulfill(route,{success:true,result_type:family[1],tool_id:body.tool_id,tool:{id:body.tool_id,name:'Narzędzie autora <PL>',artifact_id:'author-artifact',installed_version:1},
     message_i18n:{key:'lab.pvp.complete',params:{},content_version:version},access:{active:true,victim_username:'victim-stable',victim_nick:'Ofiara <PL>',seconds_left:180,tools:[]},
     security:{firewall:true,vpn_enabled:false},security_version:9,security_context:'context-stable',victim_username:'victim-stable',victim_nick:'Ofiara <PL>',
     logs:[{title:'Log autora <PL>',text:'Nie tłumacz tej historii.',type:'info'}],amount:37,removed:true,detected:false,chance:100,roll:1,removed_friend_masked:'Kontakt <PL>',removed_app_masked:'Aplikacja <PL>'});
 });
 await page.route('**/api/player-hack/security/update',async route=>{const body=route.request().postDataJSON();calls.push(body);await fulfill(route,{success:true,security:{firewall:body.value,vpn_enabled:false},security_version:10,security_context:'context-stable',access:{seconds_left:180}});});
 await page.goto('http://127.0.0.1:8993');await page.evaluate(()=>{sessionStorage.clear();localStorage.clear();});await page.reload();await page.setViewportSize({width:1280,height:900});
 for(const[id,,selector]of families){
   await page.evaluate(async id=>{await GhostLocale.changeLocale('en',false);renderPlayerHackAccessPanel({active:true,victim_username:'victim-stable',victim_nick:'Ofiara <PL>',seconds_left:180,tools:[{id,name:'Narzędzie autora <PL>',artifact_id:'author-artifact',installed:true,enabled:true}]});},id);
   await page.locator(`[data-tool-id="${id}"]`).click();
   const app=page.locator(selector).last();await app.waitFor();
   assert((await app.innerText()).includes('Ofiara <PL>'),id+' victim preserved');
   await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
   if(id==='systemLogReader')assert((await app.innerText()).includes('Nie tłumacz tej historii.'),'historical log unchanged');
   if(id==='securityPanelProxy'){
     await app.locator('[data-security-key=firewall]').uncheck();
     await page.waitForFunction(()=>document.querySelector('.security-panel-proxy-content')._securityContext.security_version===10);
     const mutation=calls.find(c=>c.key==='firewall');assert(mutation.security_version===9&&mutation.tool_id===id&&mutation.victim_username==='victim-stable'&&mutation.value===false,'canonical security mutation');
   }
   await app.locator('.close-btn').click();
 }
 assert(calls.filter(c=>c.artifact_id==='author-artifact'&&!c.key).length===6,'one request for each family');
 await page.evaluate(async()=>{await GhostLocale.changeLocale('en',false);renderPlayerHackAccessPanel({active:true,victim_username:'victim-stable',seconds_left:180,tools:[{id:'cooldown-tool',name:'Cooldown',installed:true,enabled:false,cooldown_seconds:30}]});});
 assert(await page.locator('[data-tool-id=cooldown-tool]').isDisabled(),'cooldown blocks use');
 assert((await page.locator('[data-tool-id=cooldown-tool]').innerText()).includes('30'),'cooldown preserved');
 const phases=await page.evaluate(async()=>{const en=GhostSignalShow.phaseCopy({code:'signal_transmission'});await GhostLocale.changeLocale('pl',false);return{en,pl:GhostSignalShow.phaseCopy({code:'signal_transmission'})};});
 assert(phases.en[0]!==phases.pl[0],'Signal Sender phase language');
 await page.setViewportSize({width:390,height:844});assert(await page.locator('#player-hack-access-panel').isVisible(),'mobile access panel');
 assert(errors.length===0,errors.join('\n'));
 return {status:'PASS',families:6,requests:calls.length,flows:'PvP use, security mutation, cooldown, UGC/history, Signal phase, mobile',errors};
}
