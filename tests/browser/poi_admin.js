// Real admin routes and templates; start tools/poi_admin_fixture.py.
async(page)=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('status of 400')&&!m.text().includes('status of 404'))errors.push(m.text());});
 const results=[];
 for(const width of [1440,390])for(const lang of ['pl','en']){
  await page.setViewportSize({width,height:850});
  await page.goto('http://127.0.0.1:8997/?fixture_locale='+lang);
  await page.waitForFunction(()=>document.getElementById('poi-admin')?.dataset.ready==='true');
  const id='fixture-'+width+'-'+lang;
  for(const [key,value] of Object.entries({id,name:'Test '+id,url:'https://example.org/api/interpreter',operator_group:'example.org'}))await page.locator('#poi-form [name='+key+']').fill(value);
  await page.locator('#poi-form button').click();
  const card=page.locator('#poi-providers section').filter({has:page.locator('h3',{hasText:id})});
  await card.locator('h3').waitFor();
  await card.getByRole('button',{name:lang==='pl'?'Włącz':'Enable',exact:true}).click();
  await page.waitForFunction(id=>document.querySelector('[data-provider="'+id+'"]').textContent.length>20,id);
  const message=await card.locator('[role=status]').innerText();
  if(!message.includes(lang==='pl'?'zatwierdzenia':'approved'))throw Error(message);
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('viewport overflow');
  const before=await page.request.get('http://127.0.0.1:8997/api/admin/poi-providers').then(r=>r.json());
  for(let i=0;i<5;i++)await page.locator('#poi-refresh').click();
  const after=await page.request.get('http://127.0.0.1:8997/api/admin/poi-providers').then(r=>r.json());
  if(before.health.length!==after.health.length)throw Error('refresh performed health calls');
  results.push({width,lang,candidateSaved:true,activationRejected:true,inlineMessage:message});
 }
 if(errors.length)throw Error(errors.join('\n'));
 return {results,pageErrors:errors};
}
