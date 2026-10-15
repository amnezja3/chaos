import json,tempfile
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 for mobile in (False,True):
  with tempfile.TemporaryDirectory(prefix='chaos-pwa-public-') as profile:
   options={'viewport':{'width':390 if mobile else 1280,'height':844},'is_mobile':mobile,'has_touch':mobile}
   if mobile: options['user_agent']='Mozilla/5.0 (Linux; Android 15; Redmi A5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
   ctx=p.chromium.launch_persistent_context(profile,channel='chrome',headless=True,**options)
   try:
    page=ctx.pages[0];errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.add_init_script("window.installEvents=[];window.addEventListener('beforeinstallprompt',()=>window.installEvents.push('prompt'))")
    response=page.goto('https://chaos.re/?login=1',wait_until='networkidle',timeout=60000)
    page.mouse.click(20,200);page.wait_for_timeout(10000)
    cdp=ctx.new_cdp_session(page)
    print(json.dumps({'mobile_emulation':mobile,'http':response.status,'errors':errors,'installability':cdp.send('Page.getInstallabilityErrors'),'manifest_errors':cdp.send('Page.getAppManifest')['errors'],'page':page.evaluate("async()=>({events:installEvents,worker:(await navigator.serviceWorker.getRegistration())?.active?.scriptURL,waiting:!!(await navigator.serviceWorker.getRegistration())?.waiting,installButtonVisible:!!document.querySelector('[data-install-now]')&&!document.querySelector('[data-install-now]').hidden,status:document.querySelector('[data-install-status]')?.textContent})")},ensure_ascii=True),flush=True)
   finally:ctx.close()
