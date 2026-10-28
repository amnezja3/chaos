// Local --safety --directory fixture. Mock invitation responses to test UI repetition only.
async page=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8997/__fixture/account/alice?locale=pl');
 await page.goto('http://127.0.0.1:8997/__fixture/workspace');
 await page.route('**/api/player-contact/request',route=>route.fulfill({json:{success:true},headers:{
  'X-Chaos-Session-Generation':route.request().headers()['x-chaos-session-generation'],
  'X-Chaos-Session-User':'alice'}}));
 await page.evaluate(()=>{document.body.dataset.communicationSafety='0';createEmailClient();});
 await page.locator('.mail-contact-search input').fill('Trinity');
 await page.locator('.mail-contact-search button').click();
 const card=page.locator('.player-directory-card'),status=card.locator('[role=status]');
 const button=card.getByRole('button',{name:'Wybierz gracza'});
 await button.waitFor();
 const heights=[];
 heights.push((await card.boundingBox()).height);
 for(let i=0;i<3;i++){
  await button.click();await page.waitForFunction(()=>document.querySelector('.player-directory-status').textContent.length>0);
  heights.push((await card.boundingBox()).height);
 }
 if(await status.count()!==1||new Set(heights).size!==1)throw Error('Feedback grows result card');
 await page.waitForTimeout(3200);
 if(await status.textContent()!=='')throw Error('Feedback did not expire');
 if((await card.boundingBox()).height!==heights[0])throw Error('Feedback expiry shifts layout');
 const views=[];
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:900});
  if(width===390)await page.locator('.mail-back-button').click();
  await page.mouse.move(0,0);
  views.push(await button.evaluate(b=>{
   const r=b.getBoundingClientRect(),s=getComputedStyle(b);
   return {width:innerWidth,visible:b.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)),background:s.backgroundColor};
  }));
 }
 if(views.some(v=>!v.visible||v.background!=='rgb(6, 51, 27)')||errors.length)throw Error(JSON.stringify({views,errors}));
 await page.unroute('**/api/player-contact/request');
 return {repeatedClicks:3,singleStatus:true,expiredAfter3s:true,stableHeight:true,views,errors};
}
