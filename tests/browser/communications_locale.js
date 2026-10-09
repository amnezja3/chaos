async(page)=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},errors=[],sent=[];
 page.on('pageerror',e=>errors.push(e.message));
 const fulfill=async(route,json)=>{const response=await page.request.get('http://127.0.0.1:8993/api/profile');await route.fulfill({headers:response.headers(),json});};
 let messages=[{message_id:'one',sender:'Gracz <PL>',body:'Treść autora <img>',created_at:'2026-10-08T08:00:00Z',channel:'world',scope:'group'}];
 await page.route('**/api/mail/bootstrap',async route=>{
   const version=await page.evaluate(()=>GhostLocale.contentVersion);
   const fields=Object.fromEntries(['title','subtitle','preview','meta'].map(field=>[field,{key:'apps.cyberner.channel.friends.'+field,params:field==='meta'?{count:1}:{},content_version:version}]));
   await fulfill(route,{username:'tester',channels:[{source:'friends',channel:'friends',scope:'channel',peer:'friends',title:'ZNAJOMI',subtitle:'Kanał znajomych',preview:'Wspólny kanał',meta:'1 znajomy',enabled:true,presentation_i18n:fields}],contacts:[{name:'Autor <PL>',status:'online',preview:'Opis autora'}],group_messages:messages,group_active_count:1});
 });
 await page.route('**/api/chats/messages**',async route=>{
   if(route.request().method()==='POST'){const body=route.request().postDataJSON();sent.push(body);messages=[...messages,{message_id:'two',sender:'tester',body:body.body,scope:body.scope,peer:body.peer,created_at:'2026-10-08T08:00:01Z'}];}
   await fulfill(route,{messages,contacts:[{name:'Autor <PL>',status:'online'}]});
 });
 await page.route('**/api/ghost-exchange',route=>fulfill(route,{success:true,sectors:[{sector:'camera',pending_files:3,pending_mb:5,missing_records:7,progress_percent:30,status:'collecting',listed_batches:1}],summary:{pending_files:3,pending_mb:5,hc_today:100},recent_transactions:[{file_name:'Paczka autora <PL>',market_sector:'camera',price:100,volume_mb:5}],history_7d:[]}));
 await page.goto('http://127.0.0.1:8993').catch(()=>{});await page.evaluate(()=>{sessionStorage.clear();localStorage.clear();});await page.goto('http://127.0.0.1:8993');
 await page.setViewportSize({width:1280,height:900});
 await page.evaluate(()=>createEmailClient());
 const mail=page.locator('[data-app=email]');
 await mail.locator('[data-channel=friends]').waitFor();
 const input=mail.locator('.mail-message-form input');await input.fill('Mój szkic <PL>');
 await page.evaluate(()=>GhostLocale.changeLocale('en',false));
 assert((await mail.innerText()).includes('FRIENDS'),'system channel name EN');
 assert((await mail.innerText()).includes('Autor <PL>'),'contact untouched');
 assert((await mail.innerText()).includes('Treść autora <img>'),'message untouched');
 assert(await input.inputValue()==='Mój szkic <PL>','draft retained');
 assert(await input.getAttribute('placeholder')==='Write a message…','composer placeholder EN');
 await mail.locator('[data-channel=friends]').click();
 await input.fill('Nowa wiadomość <PL>');await mail.locator('.mail-message-form button').click();
 await page.waitForFunction(()=>document.querySelector('.mail-message-form input').value==='');
 assert(sent.length===1&&sent[0].scope==='channel'&&sent[0].peer==='friends'&&sent[0].body==='Nowa wiadomość <PL>'&&sent[0].client_message_id,'canonical message payload');
 await page.evaluate(()=>createBrowser());
 const browser=page.locator('[data-app=browser]');
 await browser.locator('[data-browser-tab=exchange]').click();await browser.locator('.gx-sector-card').waitFor();
 assert((await browser.innerText()).includes('Cameras'),'market sector EN');
 assert((await browser.innerText()).includes('3 files'),'market units EN');
 assert((await browser.innerText()).includes('Paczka autora <PL>'),'sold file name untouched');
 await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
 assert((await browser.innerText()).includes('Kamery'),'market sector live PL');
 await page.evaluate(()=>createGhostLabHub());const lab=page.locator('[data-app=ghostlab]');
 await lab.locator('[data-ghostlab-tab=Documentation]').click();
 await page.evaluate(()=>GhostLocale.changeLocale('en',false));
 assert((await lab.innerText()).includes('Player product names'),'documentation EN');
 assert((await lab.innerText()).includes('postponed until further notice'),'frozen roadmap accurate');
 await lab.locator('[data-ghostlab-tab=Research]').click();
 await lab.locator('[data-ghostlab-research-branch=finance]').click();
 assert((await lab.innerText()).includes('Future financial research'),'research description EN');
 await page.setViewportSize({width:390,height:844});
 assert(await lab.locator('[data-ghostlab-research-detail]').isVisible(),'mobile research detail');
 assert(errors.length===0,errors.join('\n'));
 return {status:'PASS',flows:'Cyberner draft/send, market PL/EN, GhostLab docs/research',errors};
}
