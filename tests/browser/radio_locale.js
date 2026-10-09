// Run through Playwright MCP against tools/sprint_153_browser_fixture.py.
async (page) => {
    await page.addInitScript(() => {
        localStorage.setItem('ghost_radio_autoplay', '0');
        localStorage.removeItem('chaos:radio:language-filter');
        window.testAudios = [];
        window.Audio = class extends EventTarget {
            constructor() { super(); this.dataset={}; this.paused=true; this.currentTime=0; this.duration=300; this.volume=.8; this.muted=false; this.src=''; this.loads=0; window.testAudios.push(this); }
            getAttribute() { return this.src; }
            removeAttribute() { this.src=''; }
            load() { this.loads++; }
            play() { this.paused=false; this.dispatchEvent(new Event('play')); return Promise.resolve(); }
            pause() { this.paused=true; this.dispatchEvent(new Event('pause')); }
        };
    });
    const channels = ['pl','en','neutral','mixed','unknown'].map(language => ({id:language,name:'Author '+language,language}));
    let empty = false;
    await page.route('**/api/radio/**', async route => {
        const id = route.request().url().split('/').pop();
        const channel = channels.find(item => item.id === id);
        const response = await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:response.headers(),json:id === 'channels' ? {channels:empty?channels.filter(c=>c.language==='unknown'):channels,default_channel:'pl'} : {
            channel:{...channel,schema:1,mode:'ordered'},tracks:[{file:'original.mp3',title:'PL tytuł / EN title <keep>',language:channel?.language==='mixed'?'en':channel?.language}]
        }});
    });
    const errors=[];
    page.on('pageerror', error=>errors.push(error.message));
    await page.goto('http://127.0.0.1:8993');
    await page.evaluate(()=>createGhostHackRadioApp());
    await page.waitForFunction(()=>GhostRadio.getState().playlist.length===1);
    const assert=(value,message)=>{if(!value)throw Error(message);};
    assert(await page.locator('[data-radio-select] option').count()===3,'PL + neutral');
    await page.locator('[data-radio-action=play]').click();
    const before=await page.evaluate(()=>{testAudios[0].currentTime=73;return {src:testAudios[0].src,loads:testAudios[0].loads};});
    await page.locator('[data-radio-filter]').selectOption('en');
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    assert(await page.locator('[data-radio-select] option').count()===3,'EN + neutral');
    const after=await page.evaluate(()=>({src:testAudios[0].src,loads:testAudios[0].loads,time:testAudios[0].currentTime,paused:testAudios[0].paused}));
    assert(after.src===before.src && after.loads===before.loads && after.time===73 && !after.paused,'filter/locale must preserve playing source/time');
    assert(await page.locator('[data-radio-track]').innerText()==='PL tytuł / EN title <keep>','authored title');
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert(await page.locator('[data-radio-filter]').inputValue()==='en','explicit preference wins over UI locale');
    assert(await page.evaluate(()=>localStorage.getItem('chaos:radio:language-filter'))==='en','persist explicit preference');
    await page.locator('[data-radio-filter]').selectOption('ANY');
    assert(await page.locator('[data-radio-select] option').count()===6,'ANY includes unknown and mixed');
    await page.locator('[data-radio-select]').selectOption('mixed');
    await page.waitForFunction(()=>GhostRadio.getState().channel.id==='mixed');
    assert((await page.locator('[data-radio-language]').innerText()).includes('EN'),'mixed programme language');
    empty=true;
    await page.evaluate(async()=>{await GhostRadio.loadChannels();GhostRadio.setLanguageFilter('pl');});
    assert(await page.locator('[data-radio-empty]').isVisible(),'empty state');
    await page.locator('[data-radio-any]').click();
    assert(await page.locator('[data-radio-filter]').inputValue()==='ANY','explicit ANY action');
    await page.setViewportSize({width:390,height:844});
    const bounds=await page.locator('.ghost-radio-filters').evaluate(node=>({width:node.clientWidth,scroll:node.scrollWidth}));
    assert(bounds.scroll<=bounds.width,'mobile filters fit');
    assert(errors.length===0,JSON.stringify(errors));
    return {pass:true,scenarios:['PL/EN/ANY','programme language','playing source/time unchanged','UGC unchanged','independent persisted choice','empty + ANY','mobile'],errors};
}

