// Start tools/poi_admin_fixture.py --world --routing; run with Playwright MCP.
async(page)=>{
 const errors=[],external=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(new URL(r.url()).hostname!=='127.0.0.1')external.push(r.url());});
 const results=[];
 for(const width of [1440,390])for(const lang of ['pl','en']){
  await page.setViewportSize({width,height:850});
  await page.goto('http://127.0.0.1:8997/?fixture_locale='+lang);
  await page.waitForFunction(()=>document.querySelectorAll('#atlas-list button').length===3);
  const budgets=await page.locator('#world-atlas').innerText();
  if(!budgets.includes('95%')||!budgets.includes('760 / 800'))throw Error('budget warning missing');
  await page.locator('#atlas-layer').selectOption('roads');
  await page.waitForFunction(()=>document.querySelectorAll('#atlas-list button').length===1);
  await page.locator('#atlas-empty').check();
  await page.waitForFunction(()=>document.querySelectorAll('#atlas-list button').length===2);
  const empty=page.locator('#atlas-list button').filter({hasText:/ · 0$/});
  await empty.click();
  if(!(await page.locator('#atlas-details').innerText()).includes('COMPLETE_FRESH'))throw Error('empty proof details missing');
  const before=await page.locator('#atlas-map').getAttribute('viewBox');
  await page.locator('#atlas-in').click();
  if(before===await page.locator('#atlas-map').getAttribute('viewBox'))throw Error('zoom failed');
  await page.locator('#atlas-fit').click();
  if(before!==await page.locator('#atlas-map').getAttribute('viewBox'))throw Error('fit failed');
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('viewport overflow');
  results.push({width,lang,emptyProof:true,budgetWarning:true,zoom:true});
 }
 if(errors.length||external.length)throw Error(JSON.stringify({errors,external}));
 return {results,pageErrors:errors,externalRequests:external};
}
