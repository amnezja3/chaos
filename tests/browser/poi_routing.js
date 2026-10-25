// Reproduce against tools/poi_admin_fixture.py --world --routing (no external APIs).
async(page)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const results=[];
 for(const width of [1440,390])for(const locale of ['pl','en']){
  await page.setViewportSize({width,height:844});
  await page.goto('http://127.0.0.1:8997/?fixture_locale='+locale);
  await page.waitForFunction(()=>document.querySelector('#routing-preview')?.textContent.includes('maplark'));
  await page.locator('[name=provider0]').selectOption('geoapify');
  await page.locator('[name=provider1]').selectOption('maplark');
  await page.locator('[name=provider2]').selectOption('overpass');
  await page.locator('#routing-save').click();
  await page.waitForFunction(()=>document.querySelector('#routing-preview').textContent.includes('Geoapify:'));
  const message=await page.locator('#routing-preview').innerText();
  if(!message.includes(locale==='pl'?'niezweryfikowany':'unverified'))throw Error(message);
  await page.locator('#routing-restore').click();
  await page.waitForFunction(()=>document.querySelector('[name=provider0]').value==='overpass');
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('overflow');
  results.push({width,locale,saved:true,restored:true});
 }
 if(errors.length)throw Error(errors.join('\n'));
 return {results,pageErrors:errors};
}
