async (page) => {
    // Isolated read-response fixtures through actual app renderers. No messages
    // are sent, publications written, or teleport confirmations accepted.
    const target='48.864173348628704:2.330499567661377';
    const text=`Spotkanie focus:${target} albo teleport:${target}.`;
    const chat = async route => {
        const response=await route.fetch(), data=await response.json();
        data.messages=[{id:987654321,sender:'main',recipient:'main',body:text,subject:'CHAOS link test',created_at:'2026-10-31T12:00:00Z'}];
        await route.fulfill({response,json:data});
    };
    const news = async route => {
        const response=await route.fetch(), data=await response.json();
        data.entries=[{content:{news_id:'chaos-link-test',title:'CHAOS link test',summary:text,category:'SYSTEM'},presentation:{weight:'hero',state:'verified',asset_family:'scene'},action:{kind:'ACTIONABLE',action_type:'open_map',action_target:'world'}}];
        await route.fulfill({response,json:data});
    };
    await page.route('**/api/chats/messages?**',chat);
    await page.route('**/api/googleplex/news?**',news);
    try {
        await page.evaluate(()=>createEmailClient());
        await page.waitForSelector('.mail-message-body [data-chaos-link]');
        if(await page.locator('.mail-message-body [data-chaos-link]').count()!==2) throw Error('Cyberner did not render both links');
        await page.evaluate(()=>createBrowser());
        await page.waitForSelector('.gp-news-card__summary [data-chaos-link]');
        if(await page.locator('.gp-news-card__summary [data-chaos-link]').count()!==2) throw Error('Google Plex did not render both links');
        if(await page.locator('button [data-chaos-link]').count()) throw Error('Nested interactive controls');
        await page.locator('.gp-news-card__summary [data-chaos-link="teleport"]').click();
        await page.waitForSelector('.blacknet-decision');
        await page.locator('.blacknet-decision [data-choice="cancel"]').click();
        await page.locator('.gp-news-card__summary [data-chaos-link="focus"]').click();
        await page.waitForFunction(()=>{
            const marker=document.querySelector('.map-window iframe')?.contentWindow.blacknetCoordinateFocusLayer;
            return marker && Math.abs(marker.getLatLng().lat-48.864173348628704)<.0001;
        }, {}, {timeout:30000});
        await page.locator('.map-window .close-btn').click();
        await page.evaluate(()=>{
            const root=document.createElement('section');root.dataset.chaosText='';root.id='chaos-links-safety';
            const text=document.createElement('p');text.textContent='<img src=x onerror=alert(1)> focus:1:2; teleport:999:2; focus:1:2:3';
            const code=document.createElement('code');code.textContent='focus:1:2';
            const input=document.createElement('textarea');input.value='teleport:1:2';
            const editable=document.createElement('div');editable.contentEditable='true';editable.textContent='focus:1:2';
            root.append(text,code,input,editable);document.body.append(root);
        });
        await page.waitForSelector('#chaos-links-safety [data-chaos-link]');
        const safe=page.locator('#chaos-links-safety');
        if(await safe.locator('[data-chaos-link]').count()!==1 || await safe.locator('img').count()) throw Error('Unsafe or excessive linkification');
        await safe.locator('p').evaluate(e=>e.textContent='teleport:3:4');
        await page.waitForSelector('#chaos-links-safety [data-chaos-link="teleport"]');
        await page.evaluate(()=>{ChaosLinks.enhance(document.querySelector('#chaos-links-safety'));ChaosLinks.enhance(document.querySelector('#chaos-links-safety'));});
        if(await safe.locator('[data-chaos-link]').count()!==1) throw Error('Duplicate enhancement');
        await safe.evaluate(e=>e.remove());
        return {cyberner:'PASS',googleplex:'PASS',focus:'PASS',teleportDialog:'PASS',safeText:'PASS',dynamicAndIdempotent:'PASS'};
    } finally {
        await page.unroute('**/api/chats/messages?**',chat);
        await page.unroute('**/api/googleplex/news?**',news);
    }
}
