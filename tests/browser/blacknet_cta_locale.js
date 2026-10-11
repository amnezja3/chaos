async(page)=>{
 const assert=(value,message)=>{if(!value)throw Error(message);},errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.route('**/api/blacknet/world-signals**',async route=>{
   const response=await page.request.get('http://127.0.0.1:8993/api/profile');
   await route.fulfill({headers:response.headers(),json:{signals:[{id:'locale-cta-test',source:'world',channel:'BLACKNET',title:'Publikacja po polsku',label:'Tekst publikacji',cta:'STARY PODPIS',cta_action:'open_radio',tone:'lime',layout:1}]}});
 });
 await page.goto('http://127.0.0.1:8993');
 await page.evaluate(()=>{localStorage.clear();sessionStorage.clear();});await page.reload();
 await page.waitForFunction(()=>!document.getElementById('boot-preloader')||document.getElementById('boot-preloader').classList.contains('done'));
 await page.evaluate(async()=>{await GhostLocale.changeLocale('en',false);createBrowser();});
 await page.locator('[data-browser-tab=blacknet]').click();
 const button=page.locator('[data-blacknet-capture="locale-cta-test"]');await button.waitFor();
 assert((await button.innerText()).includes('OPEN RADIO'),'action label uses UI language');
 assert((await page.locator('.blacknet-stage').innerText()).includes('Publikacja po polsku'),'publication stays original');
 await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
 assert((await button.innerText()).includes('OTWÓRZ RADIO'),'button changes language live');
 assert(await button.getAttribute('data-blacknet-cta-action')==='open_radio','canonical CTA unchanged');
 assert(!errors.length,errors.join('\n'));
 return {status:'PASS',flows:'BlackNet CTA live locale, unchanged publication and canonical action',errors};
}
