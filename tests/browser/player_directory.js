// tools/identity_gateway_browser_fixture.py --safety --directory
async page=>{
 const errors=[],background=[];
 const onError=e=>errors.push(e.message);
 const onConsole=m=>{if(m.type()==='error'){
   if(m.location().url.endsWith('/launch-queue')||m.location().url.endsWith('/favicon.ico'))background.push(m.location().url);
   else errors.push(m.text()+' '+m.location().url);
 }};
 page.on('pageerror',onError);page.on('console',onConsole);
 const results=[];
 try {
  for(const [locale,width] of [['pl',1440],['en',390]]){
   await page.setViewportSize({width,height:900});
   await page.goto('http://127.0.0.1:8997/__fixture/account/alice?locale='+locale);
   await page.goto('http://127.0.0.1:8997/__fixture/workspace');
   await page.waitForFunction(()=>typeof createEmailClient==='function');
   await page.evaluate(()=>createEmailClient());
   for(const [nick,id] of [['Trinity','google'],['Neo','discord'],['Żółw','steam'],['Octocat','github']]){
    await page.locator('.mail-contact-search input').fill(nick);
    await page.locator('.mail-contact-search button').click();
    await page.getByText('@id_'+id+'_fixture',{exact:true}).waitFor();
   }
   await page.getByRole('button',{name:locale==='pl'?'Wybierz gracza':'Select player',exact:true}).click();
   const frame=page.frameLocator('[data-app="identity-settings"] iframe');
   await frame.locator('#contact-form input').waitFor();
   if(await frame.locator('#contact-form input').inputValue()!=='@id_github_fixture')throw Error('wrong account selected');
   await frame.locator('#contact-form button[value=invite]').click();
   await frame.getByText(locale==='pl'?'Gotowe.':'Done.',{exact:true}).waitFor();
   await page.goto('http://127.0.0.1:8997/account/safety');
   await page.locator('#player-search input').fill('@id_steam_fixture');
   await page.locator('#player-search button').click();
   await page.getByRole('button',{name:locale==='pl'?'Wybierz gracza':'Select player',exact:true}).click();
   if(await page.locator('#contact-form input').inputValue()!=='@id_steam_fixture')throw Error('handle lookup');
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('safety overflow');
   results.push({locale,width,providers:4,invitation:true,handleLookup:true});
  }
  await page.goto('http://127.0.0.1:8997/__fixture/account/id_github_fixture?locale=en');
  await page.goto('http://127.0.0.1:8997/account/safety');
  const invitation=page.locator('#invites article').filter({hasText:'alice'});
  await invitation.getByRole('button',{name:'Accept',exact:true}).click();
  await invitation.waitFor({state:'detached'});
  await page.goto('http://127.0.0.1:8997/__fixture/map-player');
  await page.getByText('ID CHAOS / Cyberner',{exact:true}).waitFor();
  await page.getByText('@id_google_fixture',{exact:true}).waitFor();
  await page.locator('.player-actor-modal__close').click();
  if(await page.locator('.player-actor-modal').count())throw Error('profile close');
  if(errors.length)throw Error(errors.join('\n'));
  return {results,acceptance:true,mapHandle:true,errors,fixtureBackgroundErrors:background};
 }finally{page.off('pageerror',onError);page.off('console',onConsole);}
}
