async(page) => {
 const assert=(value,message)=>{if(!value)throw Error(message);};
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto('http://127.0.0.1:8993');
 if(!await page.evaluate(()=>!!window.GhostLocale))await page.goto('http://127.0.0.1:8993');
 await page.waitForFunction(()=>!document.getElementById('boot-preloader')||document.getElementById('boot-preloader').classList.contains('done'));
 let release, requests=0;
 const hold=new Promise(resolve=>release=resolve);
 await page.route('**/map?**',async route=>{requests++;await hold;await route.fulfill({contentType:'text/html',body:'<html><body>Fixture map ready</body></html>'});});
 try {
  await page.evaluate(async()=>{await GhostLocale.changeLocale('en',false);createMap();window.loaderTestMap=document.querySelector('.map-window');});
  const win=page.locator('.map-window'),loader=win.locator('.map-window-loader');
  await loader.waitFor({state:'visible'});
  assert(await win.locator('.title-bar [data-ghost-i18n="shell.desktop.map"]').innerText()==='Map','Map window title is not English');
  assert(await loader.locator('.map-window-loader__title').textContent()==='Loading CHAOS map...','Outer loader title is not English');
  const expected=await page.evaluate(()=>GhostLocale.t('map.boot.sync'));
  assert(await loader.locator('.map-window-loader__text').innerText()===expected,'Outer loader status is not English');
  await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
  assert((await loader.textContent()).includes('Ladowanie mapy CHAOS'),'Outer loader did not switch to Polish');
  await page.evaluate(()=>GhostLocale.changeLocale('en',false));
  assert(await win.evaluate(node=>node===window.loaderTestMap),'Locale switch replaced map window');
  assert(requests===1,'Locale switch restarted map request');
  release();
  await loader.waitFor({state:'hidden'});
  assert(errors.length===0,errors.join('\n'));
  return {status:'PASS',outerLoader:true,windowTitle:true,liveLocale:true,mapRequests:requests,errors};
 } finally {release();}
}
