// Isolated desktop fixture. Real BN renderer and catalogs; no playback/publication.
async (page) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const assert = (ok, reason) => { if (!ok) throw Error(reason); };
    await page.setViewportSize({width:1440, height:1000});
    await page.unroute('**/api/blacknet/world-signals**');
    await page.route('**/api/blacknet/world-signals**', async route => {
        const profile = await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:profile.headers(), json:{signals:[{
            id:'stable-radio-pl', source:'world_generated', signal_type:'radio_promotion',
            title:'Polska audycja autora', label:'KANALY ONLINE', stat:'114 TRACKOW W ETERZE',
            channel:'BLACKNET AUDIO', value:'4', timer:'00:10', output_locale:'pl',
            layout:5, cta_action:'play_radio_podcast', cta_target_id:'radio-pl',
            system_copy:{
                label:{key:'apps.blacknet.rule.radio_channels_available.label', params:{}},
                stat:{key:'apps.blacknet.rule.radio_channels_available.stat', params:{tracks_total:114}}
            }
        }]}});
    });
    await page.goto('http://127.0.0.1:8993');
    await page.waitForFunction(() => window.GhostLocale && typeof createBrowser === 'function');
    await page.evaluate(async () => { await GhostLocale.changeLocale('en',false); createBrowser(); });
    await page.locator('[data-browser-tab="blacknet"]').click();
    const stage = page.locator('.blacknet-stage');
    await stage.getByText('CHANNELS ONLINE', {exact:true}).waitFor();
    assert((await stage.innerText()).includes('114 TRACKS ON AIR'), 'EN count');
    assert((await stage.innerText()).includes('Polska audycja autora'), 'original title');
    const id = await stage.locator('[data-blacknet-capture]').getAttribute('data-blacknet-capture');
    await page.evaluate(() => GhostLocale.changeLocale('pl',false));
    await stage.getByText('KANALY ONLINE', {exact:true}).waitFor();
    assert((await stage.innerText()).includes('114 TRACKOW W ETERZE'), 'PL count');
    await page.setViewportSize({width:390,height:844});
    await page.evaluate(() => GhostLocale.changeLocale('en',false));
    await stage.getByText('CHANNELS ONLINE', {exact:true}).waitFor();
    assert(await stage.locator('[data-blacknet-capture]').getAttribute('data-blacknet-capture') === id, 'stable publication ID');
    assert((await stage.innerText()).includes('Polska audycja autora'), 'mobile original title');
    assert(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), 'mobile overflow');
    assert(!errors.length, errors.join('\n'));
    return {status:'PASS', desktop:true, mobile:true, originalPublication:true, errors};
}
