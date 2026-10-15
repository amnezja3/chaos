import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.chromium.launch(channel='chrome',headless=True)
 try:
  for mobile in (False,True):
   options={'viewport':{'width':390 if mobile else 1280,'height':844},'is_mobile':mobile,'has_touch':mobile}
   if mobile: options['user_agent']='Mozilla/5.0 (Linux; Android 15; Redmi A5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'
   ctx=browser.new_context(**options);page=ctx.new_page();errors=[]
   page.on('pageerror',lambda e: errors.append(str(e)))
   page.add_init_script("window.installEvents=[];window.addEventListener('beforeinstallprompt',()=>window.installEvents.push('prompt'));window.addEventListener('appinstalled',()=>window.installEvents.push('installed'));")
   res=page.goto('https://chaos.re/?login=1',wait_until='networkidle',timeout=60000)
   page.wait_for_timeout(10000)
   cdp=ctx.new_cdp_session(page)
   result={'mobile_emulation':mobile,'http':res.status,'url':page.url,'errors':errors,'installability':cdp.send('Page.getInstallabilityErrors'),'manifest':cdp.send('Page.getAppManifest'),'page':page.evaluate("async()=>({events:window.installEvents,secure:isSecureContext,standalone:matchMedia('(display-mode: standalone)').matches,manifest:document.querySelector('link[rel=manifest]')?.href,scripts:[...document.scripts].map(s=>s.src).filter(s=>s.includes('/pwa/')),worker:(await navigator.serviceWorker.getRegistration())?.active?.scriptURL,waiting:!!(await navigator.serviceWorker.getRegistration())?.waiting,status:document.querySelector('[data-install-status]')?.textContent})")}
   print(json.dumps(result,ensure_ascii=True),flush=True)
   page.screenshot(path=f'.playwright-mcp/prod-install-{mobile}.png',full_page=True)
   ctx.close()
 finally: browser.close()
