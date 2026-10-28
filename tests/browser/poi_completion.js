// Isolated tools/poi_admin_fixture.py --routing --world; no provider HTTP.
async page => {
 const errors=[];
 const onError=e=>errors.push(String(e));
 const onConsole=m=>{if(m.type()==='error')errors.push(m.text());};
 page.on('pageerror',onError);page.on('console',onConsole);
 const results=[];
 try {
  for(const width of [1440,390])for(const locale of ['pl','en']) {
   await page.setViewportSize({width,height:900});
   await page.goto('http://127.0.0.1:8997/?fixture_locale='+locale);
   await page.waitForSelector('#poi-refresh-policy',{state:'attached'});
   await page.locator('details').evaluateAll(nodes=>nodes.forEach(n=>n.open=true));
   const policy=await page.locator('#poi-refresh-policy').innerText();
   if(!policy.includes(locale==='pl'?'raz na godzinę':'hourly'))throw Error('refresh explanation');
   const budget=await page.locator('#poi-world-budget').innerText();
   if(!budget.includes('3 / 200')||!budget.includes('197'))throw Error('collector budget');
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('overflow');
   results.push({width,locale,policy,budgetVisible:true});
  }
  if(errors.length)throw Error(errors.join('\n'));
  return {results,errors};
 } finally {page.off('pageerror',onError);page.off('console',onConsole);}
}
