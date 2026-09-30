/* Same-origin map adapter. It decorates the existing action, never adds a scan API. */
(function(global) {
    function controller() {try {return global.parent !== global ? global.parent.DeepScanner : null;} catch (_) {return null;}}
    function paintMenus() {
        const p=controller()?.snapshot()?.presentation;
        document.querySelectorAll('[data-default-scan]').forEach(button=>{
            button.classList.remove('deep-scanner-styled');button.removeAttribute('style');button.removeAttribute('data-scanner-frame');button.removeAttribute('data-scanner-pattern');
            button.removeAttribute('aria-busy');button.removeAttribute('data-scanner-busy');
            button.replaceChildren();
            if (!p) {button.textContent='🔎 Skanuj';button.removeAttribute('title');return;}
            const icon=document.createElement('span'),label=document.createElement('span');
            icon.textContent=p.icon;icon.setAttribute('aria-hidden','true');label.textContent=p.menu_name;label.className='deep-scanner-label';
            button.append(icon,label);button.title=p.menu_name;controller().style(button,p);
            const busy=Boolean(controller().busy?.());
            button.setAttribute('aria-busy',String(busy));button.setAttribute('data-scanner-busy',String(busy));
        });
    }
    global.DeepScannerMap={paintMenus,
        begin(overlay, cancel) {return controller()?.begin(global,overlay,cancel) || null;},
        log(job,phase) {return job?.live() ? job.saved.presentation.logs[phase] : '';},
        messageKey(job,phase) {return job?.live() ? `scanner:${job.id}:${phase}` : undefined;},
        stop() {controller()?.stop();}
    };
    global.addEventListener('deep-scanner-change',paintMenus);
    global.addEventListener('DOMContentLoaded',()=>{
        const detach=controller()?.attach(global);
        global.addEventListener('pagehide',()=>detach?.(),{once:true});
    });
})(window);
