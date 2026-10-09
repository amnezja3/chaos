async (page) => {
    await page.goto('http://127.0.0.1:8993');
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.evaluate(()=>createDevBugReporterApp());
    const app=page.locator('.dev-bug-reporter').last();
    await app.locator('[name=title]').fill('apps.bugs.title <keep>');
    await app.locator('[name=description]').fill('Oryginał / Original');
    await app.locator('[name=category]').selectOption('Files');
    await app.locator('[name=severity]').selectOption('high');
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    const assert=(value,message)=>{if(!value)throw Error(message);};
    assert(await app.locator('[name=title]').inputValue()==='apps.bugs.title <keep>','authored title retained');
    assert(await app.locator('[name=category]').inputValue()==='Files','category value stable');
    assert(await app.locator('[name=severity]').inputValue()==='high','severity value stable');
    assert(await app.locator('button[type=submit]').innerText()==='Submit report','translated button');
    let submitted=null,fail=true;
    await page.route('**/api/dev/bug-reports',async route=>{
        submitted=route.request().postDataJSON();
        const response=await page.request.get('http://127.0.0.1:8993/api/profile');
        const version=await page.evaluate(()=>GhostLocale.contentVersion);
        await route.fulfill({status:fail?400:200,headers:response.headers(),json:fail?{success:false,message_i18n:{key:'apps.bugs.title_required',params:{},content_version:version}}:{success:true,report:{id:42}}});
    });
    await app.locator('button[type=submit]').click();
    await page.waitForFunction(()=>document.querySelector('.dev-bug-reporter [role=status]').textContent==='A report title is required.');
    await page.evaluate(()=>GhostLocale.changeLocale('pl',false));
    assert(await app.locator('[role=status]').innerText()==='Tytuł zgłoszenia jest wymagany.','error changes language');
    assert(submitted.title==='apps.bugs.title <keep>' && submitted.category==='Files' && submitted.severity==='high','canonical request + UGC');
    fail=false;
    await app.locator('button[type=submit]').click();
    await page.waitForFunction(()=>document.querySelector('.dev-bug-reporter [role=status]').textContent.includes('#42'));
    await page.evaluate(()=>GhostLocale.changeLocale('en',false));
    assert(await app.locator('[role=status]').innerText()==='Report #42 has been sent to the administrator.','success changes language');
    await page.setViewportSize({width:390,height:844});
    assert(await app.locator('button[type=submit]').isVisible(),'mobile submit visible');
    assert(!errors.length,JSON.stringify(errors));
    return {pass:true,scenarios:['PL/EN form','draft preserved','canonical values','API error/success bindings','mobile'],errors};
}
