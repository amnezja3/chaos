async(page)=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8993');if(!await page.evaluate(()=>!!window.GhostLocale))await page.reload();
 await page.addScriptTag({url:'/map-operation-locale.js'});
 await page.evaluate(()=>{
   window.escapeMapText=escapeHTML;window.operationClientId=o=>o.operation_id;window.formatOperationDate=x=>x||'';window.formatRemainingTime=()=>'01:30';window.closeMenus=()=>{};
   window.activeOperationCardCache=new Map();window.operationCenterState='expanded';
   const panel=document.createElement('div');panel.id='active-operations-panel';document.body.appendChild(panel);
   window.renderActiveOperationsPanel([{operation_id:'op-stable',operation_type:'camera_shutdown',status:'active',target:{name:'Kamera autora <PL>'},risk_level:'low',expires_at:'2026-10-09T10:00:00Z'}],[]);
 });
 await page.evaluate(()=>GhostLocale.changeLocale('en',false));
 const panel=page.locator('#active-operations-panel');assert((await panel.innerText()).includes('Camera'),'operation type EN');assert((await panel.innerText()).includes('Remaining'),'operation labels EN');assert((await panel.innerText()).includes('Kamera autora <PL>'),'target unchanged');
 await page.evaluate(()=>{
   window.showPlayerActorProfile({username:'author-stable',nick:'Nick <PL>',relation:'friend',actions:{chat:{enabled:false,message_i18n:{key:'map.actor.chat_blocked',params:{},content_version:GhostLocale.contentVersion}}}});
 });
 const modal=page.locator('.player-actor-modal');assert((await modal.innerText()).includes('Start chat'),'actor action EN');assert((await modal.innerText()).includes('Chat is available only with friends.'),'typed actor block EN');assert((await modal.innerText()).includes('Nick <PL>'),'nick literal');await modal.locator('.player-actor-modal__close').click();
 await page.evaluate(()=>{window.abandoned=null;confirmCapturedObjectAbandon('Auto autora <PL>').then(v=>window.abandoned=v);});
 const dialog=page.locator('[role=dialog]');assert((await dialog.innerText()).includes('Abandon captured object'),'standalone map confirmation EN');
 await page.evaluate(()=>GhostLocale.changeLocale('pl',false));assert((await dialog.innerText()).includes('Auto autora <PL>'),'dialog label unchanged');await dialog.getByRole('button',{name:'ANULUJ',exact:true}).click();assert(await page.evaluate(()=>window.abandoned)===false,'cancel is read only');
 assert(await panel.locator('[data-operation-cancel=op-stable]').count()===1,'operation identity unchanged');
 assert(errors.length===0,errors.join('\n'));return {status:'PASS',flows:'map operation labels, actor profile/blocked action, standalone abandon/cancel',errors};
}
