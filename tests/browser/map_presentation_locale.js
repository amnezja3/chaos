async(page)=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8993');if(!await page.evaluate(()=>!!window.GhostLocale))await page.goto('http://127.0.0.1:8993');
 await page.waitForFunction(()=>!document.getElementById('boot-preloader')||document.getElementById('boot-preloader').classList.contains('done'));
 await page.evaluate(()=>{
   const box=document.createElement('div');box.id='map-presentation';document.body.appendChild(box);
   box.innerHTML='<div id="chaos-map-boot-overlay"><div class="chaos-map-boot-progress"><span></span></div><div class="chaos-map-boot-step"></div></div>';
   window.map={getContainer:()=>box};window.territoryClanPalette={};window.baseMinZoom=10;
   window.GameSfx={play:()=>({stop(){}})};
 });
 await page.addScriptTag({url:'/map-presentation-locale.js'});
 const data=await page.evaluate(async()=>{
   await GhostLocale.changeLocale('en',false);
   updateMapBootOverlay(ghostCopy('map.boot.player_position'),31);
   const original=Math.random;Math.random=()=>0;showSecretPathLore({target_id:'fixed',label:'Nazwa gracza'});Math.random=original;
   window.__ability={ability:{ability_code:'service_entrance',ability_name:'Wejście Serwisowe'},presentation:{display_name:'Wejście Serwisowe',activation_tagline:'BACKDOOR GOTOWY'},window:{window_id:'window-unchanged'}};
   showGhostAbilityActivation(__ability);
   return {scene:document.querySelector('.chaos-secret-path-overlay').dataset.sceneId,timer:ghostAbilityRuntime.overlayTimer};
 });
 assert((await page.locator('.chaos-map-boot-step').innerText())==='Player position','map preloader English');
 assert((await page.locator('.chaos-secret-path-copy').innerText()).includes('You repaired'),'Secret Path English');
 assert((await page.locator('.chaos-secret-path-route').innerText()).includes('Nazwa gracza'),'target preserved');
 assert((await page.locator('.chaos-ghost-ability-title').innerText())==='Service Entrance','ability English');
 assert((await page.locator('.chaos-ghost-ability-copy').innerText())==='BACKDOOR READY','ability tagline English');
 await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
 assert((await page.locator('.chaos-ghost-ability-title').innerText())==='Wejście Serwisowe','active power changes locale');
 assert((await page.locator('.chaos-map-boot-step').innerText())==='Pozycja gracza','active loader changes locale');
 assert(await page.evaluate(timer=>ghostAbilityRuntime.overlayTimer===timer,data.timer),'locale does not restart timer');
 assert(await page.locator('.chaos-secret-path-overlay').getAttribute('data-scene-id')===data.scene,'locale does not select new scene');
 await page.evaluate(async()=>{await GhostLocale.changeLocale('en',false);showGhostMapZoomHandoff({ability:{ability_code:'quarantine'},presentation:{},player:{map_zoom_scale:'world'}});});
 assert((await page.locator('.chaos-ghost-map-zoom-title').innerText())==='ACTIVATING QUARANTINE RING','quarantine English');
 assert(!errors.length,errors.join('\n'));
 await page.evaluate(()=>{clearTimeout(ghostAbilityRuntime.overlayTimer);document.getElementById('map-presentation').remove();});
 return {status:'PASS',flows:'map loader, Secret Path, superpower activation and quarantine, live locale, stable target/scene/timer',errors};
}
