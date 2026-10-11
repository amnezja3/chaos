async(page)=>{
 const assert=(value,message)=>{if(!value)throw Error(message);},errors=[];
 page.on('pageerror',error=>errors.push(error.message));
 await page.goto('http://127.0.0.1:8993');
 await page.evaluate(()=>{localStorage.clear();sessionStorage.clear();});await page.reload();
 await page.waitForFunction(()=>!document.getElementById('boot-preloader') || document.getElementById('boot-preloader').classList.contains('done'));
 await page.evaluate(async()=>{
   await GhostLocale.changeLocale('en',false);
   const config=await (await fetch('/static/data/operation_feedback.v1.json')).json();
   const app=document.createElement('div');app.id='ofs-locale-test';document.body.appendChild(app);
   const host=document.createElement('div');app.appendChild(host);
   const timers=new Map();let sequence=0;
   const clock={setTimeout:(fn,delay)=>{timers.set(++sequence,{fn,delay});return sequence;},clearTimeout:id=>timers.delete(id)};
   const session=new OperationFeedbackSystem.OperationFeedbackSession({actionKey:'car_hack',appId:'author-id',appWindow:app,rendererHost:host,clock,configLoader:()=>new Promise(()=>{})});
   session.start();session.profile={...config.operations.car_hack,...config.button_choice_action_profiles.car_hack};
   session.renderChoice(config.choice_library['feedback.car_hack.bus']);
   window.__ofsLocale={session,timers,choice:session.activeChoice,timeout:session.choiceTimeoutId,sessionId:session.sessionId};
 });
 const app=page.locator('#ofs-locale-test');
 assert((await app.innerText()).includes('Operation in progress...'),'English status');
 assert((await app.innerText()).includes('Vehicle bus'),'English choice');
 assert((await app.innerText()).includes('Default selection in 10s'),'English countdown');
 await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
 assert((await app.innerText()).includes('Magistrala pojazdu'),'choice changes while open');
 assert((await app.innerText()).includes('Operacja w toku...'),'status changes while open');
 assert(await page.evaluate(()=>{const x=__ofsLocale;return x.session.activeChoice===x.choice&&x.session.choiceTimeoutId===x.timeout&&x.session.sessionId===x.sessionId;}),'session, choice and deadline preserved');
 await page.evaluate(()=>GhostLocale.changeLocale('en',false));
 await app.locator('[data-feedback-value=control]').click();
 assert((await app.innerText()).includes('Choice saved locally.'),'choice confirmed');
 assert(await page.evaluate(()=>__ofsLocale.session.presentationState.action_mode==='control'),'canonical choice mutation');
 await page.evaluate(()=>{__ofsLocale.session.render('Author status',['Opis autora po polsku'],'pending');});
 await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
 assert((await app.innerText()).includes('Opis autora po polsku'),'author text stays literal');
 await page.evaluate(()=>{__ofsLocale.session.dispose('test_complete');document.getElementById('ofs-locale-test').remove();});
 assert(!errors.length,errors.join('\n'));
 return {status:'PASS',flows:'OFS live status/choices/countdown, stable session and deadline, canonical action, authored text',errors};
}
