async(page)=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8993');if(!await page.evaluate(()=>!!window.GhostLocale))await page.goto('http://127.0.0.1:8993');
 await page.waitForFunction(()=>!document.getElementById('boot-preloader')||document.getElementById('boot-preloader').classList.contains('done'));
 const result=await page.evaluate(async()=>{
   await GhostLocale.changeLocale('en',false);
   const config=await OperationFeedbackSystem.loadFeedbackConfig(),profile=config.operations.car_hack;
   const stages=config.provisional_timelines[profile.provisional_profile.timeline_profile].stages;
   const nodes=[],sessions=[];
   for(const voice of ['terminal','button_choices','window','progressbar_random']){
     for(const stage of stages)for(const pick of [0,.4,.9]){
       const scene=OperationFeedbackSystem.composeProvisionalScene({config,profile,stage,context:{interface:voice,app_title:'Nazwa autora',description:'Opis autora po polsku',target_label:'Nazwa celu',action_label:'car_hack'},random:()=>pick});
       const node=document.createElement('div');node.className='preloader-locale-line';document.body.appendChild(node);
       OperationFeedbackSystem.setSystemText(node,scene.lines[0]);nodes.push(node);
       sessions.push(scene.variant_key);
     }
   }
   const fallbacks=buildPreExecutionScenes({name:'Nazwa autora',interface:'window',description:'Opis autora po polsku'},{label:'Nazwa celu',action:'car_hack'});
   const host=document.createElement('div');host.id='preloader-fallback';document.body.appendChild(host);
   for(const scene of fallbacks)for(const line of scene.lines){const n=document.createElement('p');OperationFeedbackSystem.setSystemText(n,line);host.appendChild(n);}
   return {count:nodes.length,allBound:nodes.every(n=>n.dataset.ghostI18n?.startsWith('apps.preload.scene.')),variants:sessions};
 });
 assert(result.count===180&&result.allBound,'all voices/stages/variants use system locale');
 assert((await page.locator('#preloader-fallback').innerText()).includes('Author profile: Opis autora po polsku'),'author text preserved in translated frame');
 assert((await page.locator('#preloader-fallback').innerText()).includes('Preparing the application view.'),'fallback preloader English');
 await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
 assert((await page.locator('#preloader-fallback').innerText()).includes('Profil autora: Opis autora po polsku'),'fallback updates without changing author text');
 assert((await page.locator('.preloader-locale-line').first().innerText()).startsWith('Uruchamianie'),'active preloader updates');
 await page.evaluate(()=>{document.querySelectorAll('.preloader-locale-line,#preloader-fallback').forEach(n=>n.remove());});
 assert(!errors.length,errors.join('\n'));return {status:'PASS',variants:result.count,errors};
}
