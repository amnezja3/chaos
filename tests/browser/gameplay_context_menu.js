async(page)=>{
 const assert=(v,m)=>{if(!v)throw Error(m);},errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8993');
 if(!await page.evaluate(()=>!!window.GhostLocale))await page.goto('http://127.0.0.1:8993');
 await page.waitForFunction(()=>!document.getElementById('boot-preloader')||document.getElementById('boot-preloader').classList.contains('done'));
 const result=await page.evaluate(async()=>{
   const surfaces=['div','input','textarea','button','canvas','img'];let ownMenu=0;
   const prevented=surfaces.map(tag=>{const el=document.createElement(tag);document.body.appendChild(el);el.addEventListener('contextmenu',()=>ownMenu++);const e=new MouseEvent('contextmenu',{bubbles:true,cancelable:true});el.dispatchEvent(e);el.remove();return e.defaultPrevented;});
   const frame=document.createElement('iframe');frame.id='context-guard-test';frame.src='/frame';document.body.appendChild(frame);
   await new Promise(resolve=>frame.addEventListener('load',resolve,{once:true}));
   const nested=frame.contentDocument.createElement('iframe');frame.contentDocument.body.appendChild(nested);
   await new Promise(resolve=>setTimeout(resolve,0));
   const event=new frame.contentWindow.MouseEvent('contextmenu',{bubbles:true,cancelable:true});frame.contentDocument.body.dispatchEvent(event);
   const nestedEvent=new nested.contentWindow.MouseEvent('contextmenu',{bubbles:true,cancelable:true});nested.contentDocument.body.dispatchEvent(nestedEvent);
   return {prevented,ownMenu,frame:event.defaultPrevented,nested:nestedEvent.defaultPrevented};
 });
 assert(result.prevented.every(Boolean)&&result.frame&&result.nested,'native menu cancelled on all surfaces and nested frames');
 assert(result.ownMenu===6,'own handlers still receive right click');
 await page.locator('#context-guard-test').evaluate(el=>el.remove());
 await page.evaluate(()=>createTerminal());
 const task=page.locator('.system-task-button').last();await task.click({button:'right'});
 await page.locator('#system-task-context-menu [role=menuitem]').waitFor();
 await page.evaluate(id=>{window.__contextTarget=[...runningWindows.entries()].find(([key])=>String(key)===id)?.[1];},await task.getAttribute('data-window-id'));
 assert(await page.evaluate(()=>!!window.__contextTarget?.isConnected),'selected window exists');
 await page.locator('#system-task-context-menu [role=menuitem]').click();
 await page.waitForFunction(()=>!window.__contextTarget.isConnected);
 assert(!errors.length,errors.join('\n'));
 return {status:'PASS',...result,errors};
}
