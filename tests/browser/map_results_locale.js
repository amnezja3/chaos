// Playwright MCP with tools/sprint_153_browser_fixture.py; isolated API responses.
async (page) => {
    await page.goto('http://127.0.0.1:8993');
    if (!await page.evaluate(() => !!window.GhostLocale)) await page.goto('http://127.0.0.1:8993');
    await page.addScriptTag({url:'/map-result-locale.js'});
    const assert = (value, message) => { if (!value) throw Error(message); };
    const requests = [];
    let phase = 'api_error';
    const version = await page.evaluate(() => GhostLocale.contentVersion);
    const target = {target_id:'car:stable',name:"Mike's <keep>",label:"Mike's <keep>",icon:'🚗',lat:37.5,lon:-122.1,source_type:'vehicle'};
    await page.route('**/api/map/aim-target', async route => {
        requests.push(route.request().postDataJSON());
        const response = await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:response.headers(),json:{success:true,status:'aimed_target_set',target,
            message_i18n:{key:'map.result.aimed',params:{name:target.label},content_version:version}}});
    });
    await page.route('**/map-action', async route => {
        requests.push(route.request().postDataJSON());
        const response = await page.request.get('http://127.0.0.1:8993/api/profile');
        await route.fulfill({headers:response.headers(),json:{status:'Legacy status',scan_outcome:phase,markers:[],
            message_i18n:{key:phase==='api_error'?'map.result.upstream':'map.result.out_of_range',params:{},content_version:version}}});
    });
    await page.evaluate(() => {
        window.resultMessages=[];
        window.addSystemMessage=(...args)=>resultMessages.push(args);
        window.normalizeMapMenuTarget=target=>target;
        window.guardMapGameplayAction=()=>false;
        window.armSecretPathAudio=()=>{};
        window.closeAllMapMenus=()=>{};
        window.showSecretPathLore=()=>{};
        window.updateParentToolbarAimedTarget=target=>{window.testAimed=target;};
        window.beginMapScanEffect=()=>()=>{};
        window.finishMapScanEffectAfterPaint=finish=>finish?.();
        window.mapScanEffectState={element:null};
        window.DeepScannerMap={begin:()=>({dispose(){}}),log:()=> 'Autorski log <keep>',messageKey:()=> 'stable-dedupe'};
        window.escapeMapText=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    });
    for (const locale of ['pl','en']) {
        await page.evaluate(locale=>GhostLocale.changeLocale(locale,false),locale);
        await page.evaluate(target=>aimMapTargetOnly(target,null),target);
        const aimed=await page.evaluate(()=>testAimed);
        assert(JSON.stringify(aimed)===JSON.stringify(target),'Target changed');
        const message=await page.evaluate(()=>resultMessages.at(-1)[2]);
        assert(message.includes(locale==='pl'?'Cel ustawiony:':'Target selected:'),'Wrong selection language');
        assert(message.includes('&lt;keep&gt;'),'Unescaped target name');
        await page.evaluate(()=>mapAction('scan',37.5,-122.1));
        const scan=await page.evaluate(()=>resultMessages.at(-1));
        assert(scan[2].includes('Autorski log &lt;keep&gt;'),'Authored log changed');
        assert(scan[2].includes(locale==='pl'?'Nie udało się pobrać':'Could not retrieve'),'Wrong scan error language');
        assert(scan[3]==='stable-dedupe','Deduplication changed');
    }
    phase='denied';
    await page.evaluate(()=>mapAction('scan',37.5,-122.1));
    assert((await page.evaluate(()=>resultMessages.at(-1)[2])).includes('out of range'),'Denial untranslated');
    assert(JSON.stringify(requests[0])===JSON.stringify(requests[2]),'Selection request depends on locale');
    assert(JSON.stringify(requests[1])===JSON.stringify(requests[3]),'Scan request depends on locale');
    return {selection:true,stableRequests:true,escapedNames:true,scanErrors:true,authoredLogs:true,deduplication:true};
}
