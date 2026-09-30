/* One live scanner window per desktop; server lease is the runtime authority. */
(function(global) {
    let current = null, heartbeat = null;
    const jobs = new Set();
    const maps = new Set();
    const palette = {green:'#b6ff54',cyan:'#65eaff',amber:'#ffcd67',violet:'#d0a2ff'};
    let scanAudio = null;
    function stopScanAudio() {
        const old = scanAudio;
        scanAudio = null;
        if (!old) return;
        clearTimeout(old.timer);
        old.handle?.stop({fade_ms:80});
    }
    function startScanAudio(saved) {
        if (scanAudio || !global.GameSfx) return;
        const loop = {timer:null,handle:null};
        scanAudio = loop;
        const live = () => scanAudio === loop && jobs.size > 0 && snapshot() === saved;
        const schedule = delay => {
            if (!live()) return;
            clearTimeout(loop.timer);
            loop.timer = setTimeout(play,delay);
        };
        function play() {
            if (!live()) return;
            loop.handle = global.GameSfx.play(saved.presentation.sfx_event,{
                event_id:crypto.randomUUID(),
                on_end:() => schedule(250)
            });
            // Muting or a temporarily occupied voice slot must not end the scan loop.
            loop.handle?.started?.then(result => {if (!result.ok) schedule(1000);}, () => schedule(1000));
        }
        play();
    }
    async function post(url, body) {
        const response = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),keepalive:true});
        const data = await response.json();
        if (!response.ok || !data.success) throw Error(data.message || data.error || 'Skaner niedostępny.');
        return data;
    }
    function changed() {
        maps.forEach(map => { try { if (map.closed) maps.delete(map); else map.dispatchEvent(new map.Event('deep-scanner-change')); } catch (_) {maps.delete(map);} });
    }
    function stop() {
        const old = current;
        current = null;
        stopScanAudio();
        clearInterval(heartbeat); heartbeat = null;
        jobs.forEach(job => job.dispose()); jobs.clear();
        changed();
        if (old?.token) post('/api/ghostlab/scanner/lease',{token:old.token,release:true}).catch(() => {});
        if (old?.status?.isConnected) old.status.textContent = 'Nakładka wyłączona. Otwórz aplikację ponownie, aby ją aktywować.';
    }
    function snapshot() {
        if (current && (!current.app.isConnected || Date.now() >= current.until ||
                (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive))) stop();
        return current?.token ? current : null;
    }
    async function renew() {
        const saved = snapshot();
        if (!saved) return;
        try {
            const result = await post('/api/ghostlab/scanner/lease',{token:saved.token});
            if (current === saved) saved.until = Date.now() + result.ttl*1000;
        } catch (_) { if (current === saved) stop(); }
    }
    function style(element, p) {
        element.classList.add('deep-scanner-styled');
        element.dataset.scannerFrame = p.frame_id;
        element.style.setProperty('--scanner-frame',palette[p.frame_color] || palette.green);
        element.style.setProperty('--scanner-button',palette[p.button_color] || palette.green);
    }
    function begin(map, overlay, cancelEffect) {
        const saved = snapshot();
        if (!saved) return null;
        global.GameSfx?.unlock();
        const id = crypto.randomUUID();
        const job = {id, saved, map, overlay, token:saved.token, done:false,
            live() {return !this.done && snapshot() === saved;},
            dispose() {
                if (this.done) return;
                this.done = true; jobs.delete(this);
                if (!jobs.size) stopScanAudio();
                if (overlay) {overlay.classList.remove('deep-scanner-styled');overlay.style.removeProperty('--scanner-frame');overlay.style.removeProperty('--scanner-button');}
                cancelEffect?.();
            }};
        if (overlay) {style(overlay,saved.presentation); overlay.dataset.label=saved.presentation.logs.start;}
        jobs.add(job);
        startScanAudio(saved);
        return job;
    }
    function inventory(apps) {
        if (!current || !Array.isArray(apps)) return;
        const installed = apps.find(app => (app.id || app.app_id) === current.presentation.app_id);
        if (!installed || installed.status === 'uninstalled' || (installed.artifact_id && installed.artifact_id !== current.presentation.artifact_id)) stop();
    }
    async function render(app, body, data, reload) {
        body.innerHTML = `<p>Zainstalowana wersja: ${Number(data.product.installed_version)}. Opublikowana: ${data.available_version == null ? '—' : Number(data.available_version)}.</p>
            <p>${escapeHTML(data.product.description)}</p><p data-scanner-status>Aktywowanie nakładki…</p>
            <div class="pro-tool-actions"><button data-scanner-reopen>Odśwież aktywację</button>
            ${data.update_available ? '<button data-scanner-update>Aktualizuj bezpłatnie</button>' : ''}</div>`;
        const status = body.querySelector('[data-scanner-status]');
        body.querySelector('[data-scanner-reopen]').onclick = () => { if (current?.app === app) stop(); reload(); };
        body.querySelector('[data-scanner-update]')?.addEventListener('click', () => {
            if (current?.app === app) stop();
            reload({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
                expected_artifact_id:data.product.artifact_id, artifact_id:data.available_artifact_id})});
        });
        if (!data.product.runtime_enabled) {status.textContent = data.product.disabled_reason;return;}
        if (snapshot() && current.app !== app) {status.textContent='Najpierw zamknij skaner: '+current.presentation.name;return;}
        app._scannerWindowId ||= crypto.randomUUID();
        try {
            const result = await post('/api/ghostlab/scanner/'+encodeURIComponent(data.product.id)+'/activate',{window_id:app._scannerWindowId});
            if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) {
                await post('/api/ghostlab/scanner/lease',{token:result.token,release:true});return;
            }
            current = {app,status,token:result.token,presentation:result.presentation,until:Date.now()+result.ttl*1000};
            clearInterval(heartbeat);heartbeat=setInterval(renew,10000);
            status.textContent=`Aktywny: ${result.presentation.icon} ${result.presentation.menu_name}. Pozostaw to okno otwarte i użyj Skanuj na mapie. Zamknięcie przywraca zwykły skaner.`;
            changed();
        } catch(error) {status.textContent=error.message;}
    }
    global.DeepScanner = {snapshot,stop,begin,render,style,inventory,
        owns:app => current?.app === app,
        focus(id) {const s=snapshot();if (s?.presentation.app_id!==id) return false;
            s.app.style.display='';s.app.scrollIntoView({block:'nearest'});s.app.querySelector('button')?.focus();return true;},
        attach(map) {maps.add(map);return () => {maps.delete(map);jobs.forEach(job => {if (job.map===map) job.dispose();});}},
        async previewSound(id) {global.GameSfx?.unlock();return global.GameSfx?.play('scanner.regular.'+(id==='regular_ping'?'ping':'sweep'));}
    };
    global.addEventListener('pagehide',stop);
    global.addEventListener('DOMContentLoaded', () => new MutationObserver(() => {if (current && !current.app.isConnected) stop();}).observe(document.body,{childList:true,subtree:true}));
})(window);

function mountGhostLabScannerPreview(main) {
    const panel=document.createElement('section');panel.className='deep-scanner-preview';
    panel.innerHTML='<p>DEMONSTRACJA — bez skanowania i aktywacji aplikacji.</p><div class="deep-scanner-preview-map"><div class="chaos-map-scan-overlay" data-label="Skanowanie mapy"></div></div><button type="button" data-visual>Podgląd regular</button> <button type="button" data-audio>Odsłuch SFX</button>';
    const preview = main.querySelector('[data-ghostlab-preview-panel]');
    if (preview) preview.after(panel); else main.appendChild(panel);
    let sound=null,timer=null;
    panel.querySelector('[data-visual]').onclick=()=>{
        const effect=panel.querySelector('.chaos-map-scan-overlay');
        const value=key=>main.querySelector(`[data-ghostlab-blueprint-key="${key}"]`)?.value;
        DeepScanner.style(effect,{frame_id:value('frame_id'),frame_color:value('frame_color'),button_color:value('button_color')});
        effect.dataset.label=value('start_text') || 'Skanowanie mapy';
        effect.classList.add('is-visible');clearTimeout(timer);timer=setTimeout(()=>effect.classList.remove('is-visible'),2400);
    };
    panel.querySelector('[data-audio]').onclick=async()=>{sound?.stop();const id=main.querySelector('[data-ghostlab-blueprint-key="sfx_id"]')?.value;sound=await DeepScanner.previewSound(id);if (!panel.isConnected) sound?.stop();};
    const observer=new MutationObserver(()=>{if (!panel.isConnected) {sound?.stop();clearTimeout(timer);observer.disconnect();}});
    observer.observe(document.body,{childList:true,subtree:true});
}
