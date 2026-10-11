async(page) => {
 const assert=(ok,msg)=>{if(!ok)throw Error(msg);};
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.context().clearCookies();
 await page.goto('http://127.0.0.1:8993');
 await page.evaluate(()=>{localStorage.clear();sessionStorage.clear();});
 await page.goto('http://127.0.0.1:8993');
 if(!await page.evaluate(()=>!!window.GhostLocale))await page.goto('http://127.0.0.1:8993');
 await page.waitForFunction(()=>!document.getElementById('boot-preloader')||document.getElementById('boot-preloader').classList.contains('done'));
 await page.context().grantPermissions(['clipboard-read','clipboard-write'],{origin:'http://127.0.0.1:8993'});
 await page.evaluate(()=>{createTerminal();window.pasteSubmits=0;document.querySelector('.system-terminal-composer').addEventListener('submit',()=>window.pasteSubmits++);});
 const input=page.locator('.system-terminal-input').last();
 for(const locale of ['pl','en']){
  await page.evaluate(async locale=>{await GhostLocale.changeLocale(locale,false);await navigator.clipboard.writeText('hello\nworld');},locale);
  await input.fill('left OLD right');
  await input.evaluate(node=>{node.focus();node.setSelectionRange(5,8);node.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true,clientX:150,clientY:150}));});
  await page.getByRole('menuitem',{name:locale==='pl'?'Wklej':'Paste',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.system-terminal-input').value==='left hello world right');
  assert(await page.evaluate(()=>window.pasteSubmits)===0,'Paste submitted a command');
 }
 await page.evaluate(()=>Object.defineProperty(navigator.clipboard,'readText',{configurable:true,value:()=>Promise.reject(new Error('denied'))}));
 await input.click({button:'right'});
 await page.getByRole('menuitem',{name:'Paste',exact:true}).click();
 await page.getByRole('status').filter({hasText:'Clipboard access unavailable'}).waitFor();
 assert(await input.inputValue()==='left hello world right','Denied paste changed input');
 await page.keyboard.press('Escape');
 assert(await page.locator('#terminal-paste-menu').count()===0,'Escape did not close menu');
 assert(errors.length===0,errors.join('\n'));
 return {locales:2,clipboard:'real',replacement:true,noSubmit:true,deniedFallback:true,errors};
}
