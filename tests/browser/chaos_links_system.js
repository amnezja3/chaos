async page => {
    // Read fixtures use real app/document renderers. Teleport uses the REAL
    // canonical backend on the isolated local game account; never run on VPS.
    if (!page.url().startsWith('http://127.0.0.1:9001/')) throw Error('Local game required');
    const target='48.864173348628704:2.330499567661377';
    const text=`focus <${target}> oraz teleport:${target}`;
    const checks=[];
    const assert=(ok,name)=>{if(!ok)throw Error(name);checks.push(name);};
    let requests=0;
    const count=request=>{if(request.url().includes('/api/blacknet/cta/teleport'))requests++;};
    page.on('request',count);
    const chat=async route=>{
        const response=await route.fetch(),data=await response.json();
        data.messages=[{id:987654321,sender:'main',recipient:'main',body:text,subject:'Links fixture',created_at:'2026-10-31T12:00:00Z'}];
        await route.fulfill({response,json:data});
    };
    const news=async route=>{
        const response=await route.fetch(),data=await response.json();
        data.entries=[{content:{news_id:'links-fixture',title:'Links fixture',summary:text,category:'SYSTEM'},presentation:{weight:'hero',state:'verified',asset_family:'scene'},action:{kind:'ACTIONABLE',action_type:'open_map',action_target:'world'}}];
        await route.fulfill({response,json:data});
    };
    const document=async route=>{
        const response=await route.fetch();
        await route.fulfill({response,status:200,json:{document:{author:'Local fixture',title:'Links.ptk',version:1,
            content:'# Linki\n`focus <'+target+'>`\n\n**teleport '+target+'**\n\n<img src=x onerror=alert(1)>\n\nfocus:999:2'}}});
    };
    await page.route('**/api/chats/messages?**',chat);
    await page.route('**/api/googleplex/news?**',news);
    await page.route('**/api/ghostlab/documents/links-system.ptk',document);
    const exercise=async(selector,name)=>{
        await page.waitForSelector(selector+' [data-chaos-link]');
        const root=page.locator(selector).last();
        assert(await root.locator('[data-chaos-link]').count()===2,name+' renders exactly two actions');
        const before=requests;
        await root.locator('[data-chaos-link="focus"]').evaluate(e=>{e.click();e.click();});
        await page.waitForFunction(()=>{
            const marker=window.document.querySelector('.map-window iframe')?.contentWindow.blacknetCoordinateFocusLayer;
            return marker && Math.abs(marker.getLatLng().lat-48.864173348628704)<.00001;
        },{}, {timeout:30000});
        assert(requests===before,name+' focus uses map without teleport');
        await root.locator('[data-chaos-link="teleport"]').evaluate(e=>{e.click();e.click();});
        await page.waitForSelector('.blacknet-decision');
        assert(requests===before,name+' waits for confirmation');
        assert(await page.locator('.blacknet-decision').count()===1,name+' one dialog for double click');
        const responsePromise=page.waitForResponse(r=>r.url().includes('/api/blacknet/cta/teleport'));
        await page.locator('.blacknet-decision [data-choice="confirm"]').click();
        const response=await responsePromise,data=await response.json();
        assert(response.ok() && data.success!==false,name+' canonical backend success');
        assert(Math.abs(data.curently_possition.lat-48.864173348628704)<.00001,name+' canonical position');
        await page.waitForTimeout(650);
        assert(requests===before+1,name+' exactly one teleport request');
    };
    try {
        await page.setViewportSize({width:1440,height:900});
        await page.evaluate(()=>createEmailClient());
        await exercise('.mail-message-body','Cyberner');
        await page.evaluate(()=>createBrowser());
        await exercise('.gp-news-card__summary','Googleplex');
        await page.evaluate(async()=>{await createFileManager();await window.runFile('documents','links-system.ptk');});
        await exercise('.file-manager-markdown','PTK');
        assert(await page.locator('.file-manager-markdown img').count()===0,'PTK escapes injected HTML');
        await page.evaluate(async()=>{await window.runFile('documents','links-system.ptk');});
        await page.waitForSelector('.file-manager-markdown [data-chaos-link]');
        await page.evaluate(()=>{ChaosLinks.enhance(window.document.body);ChaosLinks.enhance(window.document.body);});
        assert(await page.locator('.file-manager-markdown [data-chaos-link]').count()===2,'PTK reopen and enhance idempotent');
        await page.setViewportSize({width:390,height:844});
        await exercise('.file-manager-markdown','PTK mobile');
        const invalid=await page.evaluate(async()=>{
            const parsed=['focus:91:2','teleport:1:181','focus:1:2:3','delete:1:2'].every(v=>ChaosLinks.parse(v)===null);
            const response=await fetch('/api/blacknet/cta/teleport',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:'terminal',lat:999,lng:2})});
            return parsed && response.status===404 && (await response.json()).success===false;
        });
        assert(invalid,'invalid coordinates rejected by parser and backend');
        const anonymous=await page.context().browser().newContext();
        try {const denied=await anonymous.request.post('http://127.0.0.1:9001/api/blacknet/cta/teleport',{data:{source:'terminal',lat:48,lng:2}});assert(denied.status()===401,'anonymous teleport denied');}
        finally {await anonymous.close();}
        return {checks};
    } finally {
        page.off('request',count);
        await page.unroute('**/api/chats/messages?**',chat);
        await page.unroute('**/api/googleplex/news?**',news);
        await page.unroute('**/api/ghostlab/documents/links-system.ptk',document);
    }
}
