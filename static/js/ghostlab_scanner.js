/* One live scanner window per desktop; server lease is the runtime authority. */
(function(global) {
    let current = null, heartbeat = null;
    const jobs = new Set();
    const maps = new Set();
    const previews = new Set();
    const palette = {green:'#b6ff54',cyan:'#65eaff',amber:'#ffcd67',violet:'#d0a2ff'};
    let scanAudio = null;
    function stopScanAudio() {
        const old = scanAudio;
        scanAudio = null;
        if (!old) return;
        old.stop();
    }
    function soundLoop(event, isLive) {
        const loop = {timer:null,handle:null,stopped:false,stop() {
            if (this.stopped) return;
            this.stopped=true;clearTimeout(this.timer);this.handle?.stop({fade_ms:80});
        }};
        const live = () => !loop.stopped && isLive();
        const schedule = delay => {
            if (!live()) return;
            clearTimeout(loop.timer);
            loop.timer = setTimeout(play,delay);
        };
        function play() {
            if (!live()) return;
            loop.handle = global.GameSfx?.play(event,{
                event_id:crypto.randomUUID(),
                on_end:() => schedule(250)
            });
            // Muting or a temporarily occupied voice slot must not end the scan loop.
            loop.handle?.started?.then(result => {if (!result.ok) schedule(1000);}, () => schedule(1000));
        }
        play();
        return loop;
    }
    function startScanAudio(saved) {
        if (scanAudio || !global.GameSfx) return;
        scanAudio = soundLoop(saved.presentation.sfx_event, () => jobs.size > 0 && snapshot() === saved);
    }
    async function post(url, body) {
        const response = await fetch(url, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),keepalive:true});
        const data = await response.json();
        if (!response.ok || !data.success) throw Error(ghostResponseText(data, 'lab.service.scanner_unavailable'));
        return data;
    }
    function changed() {
        maps.forEach(map => { try { if (map.closed) maps.delete(map); else map.dispatchEvent(new map.Event('deep-scanner-change')); } catch (_) {maps.delete(map);} });
    }
    function stop() {
        const old = current;
        current = null;
        stopScanAudio();
        previews.forEach(dispose => dispose());
        clearInterval(heartbeat); heartbeat = null;
        jobs.forEach(job => job.dispose()); jobs.clear();
        changed();
        if (old?.token) post('/api/ghostlab/scanner/lease',{token:old.token,release:true}).catch(() => {});
        if (old?.status?.isConnected) ghostSet(old.status, 'lab.service.scanner_stopped');
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
        element.dataset.scannerPattern = ['regular','pulse','wave','viewfinder','direct'].includes(p.pattern_id) ? p.pattern_id : 'regular';
        element.dataset.scannerFrame = p.frame_id;
        element.style.setProperty('--scanner-frame',palette[p.frame_color] || palette.green);
        element.style.setProperty('--scanner-button',palette[p.button_color] || palette.green);
        if (element.classList.contains('chaos-map-scan-overlay')) {
            let scene = element.querySelector('.deep-scanner-scene');
            if (!scene) {
                // Use the map's document when decorating an iframe. Fixed, bounded
                // layers: no particle timers, canvas loop or fabricated detections.
                scene = element.ownerDocument.createElement('div');
                scene.className = 'deep-scanner-scene';
                scene.setAttribute('aria-hidden', 'true');
                for (const part of ['illumination','grid','aperture','echo','wake','reticle','rail','caption']) {
                    const layer = element.ownerDocument.createElement('div');
                    layer.className = 'scanner-show-' + part;
                    scene.appendChild(layer);
                }
                element.appendChild(scene);
            }
            const modes = {regular:'LINE / SWEEP',pulse:'PULSE / SONAR',wave:'WAVE / SPECTRUM',viewfinder:'VIEWFINDER / OPTICS',direct:'DIRECT / BEAM'};
            scene.querySelector('.scanner-show-caption').textContent = modes[element.dataset.scannerPattern];
        }
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
                if (overlay && !Array.from(jobs).some(job => job.overlay === overlay)) {
                    overlay.classList.remove('deep-scanner-styled');
                    delete overlay.dataset.scannerPattern;delete overlay.dataset.scannerFrame;
                    overlay.querySelector('.deep-scanner-scene')?.remove();
                    for(const key of ['--scanner-frame','--scanner-button','--scanner-x','--scanner-y']) overlay.style.removeProperty(key);
                }
                cancelEffect?.();
                changed();
            }};
        if (overlay) {style(overlay,saved.presentation); overlay.dataset.label=saved.presentation.logs.start;}
        jobs.add(job);
        startScanAudio(saved);
        changed();
        return job;
    }
    function inventory(apps) {
        if (!current || !Array.isArray(apps)) return;
        const installed = apps.find(app => (app.id || app.app_id) === current.presentation.app_id);
        if (!installed || installed.status === 'uninstalled' || (installed.artifact_id && installed.artifact_id !== current.presentation.artifact_id)) stop();
    }
    async function render(app, body, data, reload) {
        body.innerHTML = `<p>${ghostLabel('lab.runtime.versions', {installed:Number(data.product.installed_version), available:String(data.available_version ?? '—')})}</p>
            <p>${escapeHTML(data.product.description)}</p><p data-scanner-status>${ghostLabel("lab.service.scanner_activating")}</p>
            <div class="pro-tool-actions"><button data-scanner-reopen>${ghostLabel("lab.service.scanner_refresh")}</button>
            ${data.update_available ? `<button data-scanner-update>${ghostLabel("lab.service.scanner_update")}</button>` : ''}</div>`;
        const status = body.querySelector('[data-scanner-status]');
        body.querySelector('[data-scanner-reopen]').onclick = () => { if (current?.app === app) stop(); reload(); };
        body.querySelector('[data-scanner-update]')?.addEventListener('click', () => {
            if (current?.app === app) stop();
            reload({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
                expected_artifact_id:data.product.artifact_id, artifact_id:data.available_artifact_id})});
        });
        if (!data.product.runtime_enabled) {ghostSet(status, 'lab.runtime.unavailable');return;}
        if (snapshot() && current.app !== app) {ghostSet(status, 'lab.service.scanner_close', {name:current.presentation.name});return;}
        app._scannerWindowId ||= crypto.randomUUID();
        try {
            const result = await post('/api/ghostlab/scanner/'+encodeURIComponent(data.product.id)+'/activate',{window_id:app._scannerWindowId});
            if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) {
                await post('/api/ghostlab/scanner/lease',{token:result.token,release:true});return;
            }
            current = {app,status,token:result.token,presentation:result.presentation,until:Date.now()+result.ttl*1000};
            clearInterval(heartbeat);heartbeat=setInterval(renew,10000);
            ghostSet(status, 'lab.service.scanner_active', {name:result.presentation.icon+' '+result.presentation.menu_name});
            changed();
        } catch(error) {delete status.dataset.ghostI18n; status.textContent=error.message;}
    }
    global.DeepScanner = {snapshot,stop,begin,render,style,inventory,soundLoop,
        registerPreview(dispose) {previews.add(dispose);return () => previews.delete(dispose);},
        busy:() => jobs.size > 0,
        owns:app => current?.app === app,
        focus(id) {const s=snapshot();if (s?.presentation.app_id!==id) return false;
            s.app.style.display='';s.app.scrollIntoView({block:'nearest'});s.app.querySelector('button')?.focus();return true;},
        attach(map) {maps.add(map);return () => {maps.delete(map);jobs.forEach(job => {if (job.map===map) job.dispose();});}},
        async previewSound(id) {
            const variants={regular:['sweep','ping'],pulse:['sonar','heartbeat'],wave:['tide','ripple'],viewfinder:['focus','tracking'],direct:['beam','radar']};
            const [pattern,variant]=String(id).split('_');
            if (!variants[pattern]?.includes(variant)) return null;
            global.GameSfx?.unlock();return global.GameSfx?.play(`scanner.${pattern}.${variant}`);
        }
    };
    global.addEventListener('pagehide',stop);
    global.addEventListener('DOMContentLoaded', () => new MutationObserver(() => {if (current && !current.app.isConnected) stop();}).observe(document.body,{childList:true,subtree:true}));
})(window);

function mountGhostLabScannerPreview(main, project) {
    const panel=document.createElement('section');panel.className='deep-scanner-preview';
    panel.innerHTML=`<p>${ghostLabel("lab.service.demo")}</p><div class="deep-scanner-preview-map"><div class="chaos-map-scan-overlay"></div></div><div class="deep-scanner-preview-controls"><button type="button" data-visual>${ghostLabel("lab.service.demo_visual")}</button><button type="button" data-audio>${ghostLabel("lab.service.demo_audio")}</button><button type="button" data-stop>${ghostLabel("lab.service.stop")}</button><select data-ghost-aria-label="lab.service.demo_result" aria-label="${escapeHTML(window.GhostLocale.t('lab.service.demo_result'))}" data-result><option value="success">${ghostLabel("lab.service.detection")}</option><option value="empty">${ghostLabel("lab.service.empty")}</option><option value="error">${ghostLabel("lab.service.api_error")}</option><option value="denied">${ghostLabel("lab.service.denied")}</option></select></div><p class="deep-scanner-preview-result" aria-live="polite" data-preview-log></p>`;
    const preview = main.querySelector('[data-ghostlab-preview-panel]');
    if (preview) preview.after(panel); else main.appendChild(panel);
    let sound=null,timer=null,active=false,serial=0;
    const input=key=>main.querySelector(`[data-ghostlab-blueprint-key="${key}"]`);
    const value=key=>input(key)?.value;
    const schema=project.field_schema;
    const effect=panel.querySelector('.chaos-map-scan-overlay'),log=panel.querySelector('[data-preview-log]');
    const text=phase=>value(phase+'_text')?.trim() || schema[phase+'_log'].option_labels[value(phase+'_log')];
    const stop=()=>{serial++;active=false;sound?.stop();sound=null;clearTimeout(timer);effect.classList.remove('is-visible');};
    const sync=()=>{
        stop();
        const select=input('sfx_id'),previous=select.value;
        select.replaceChildren();
        for(const id of schema.sfx_id.pattern_options[value('pattern_id')] || []) {
            const option=document.createElement('option');option.value=id;option.textContent=id.replaceAll('_',' ');select.append(option);
        }
        if(Array.from(select.options).some(option=>option.value===previous))select.value=previous;
        ghostSet(log, 'lab.service.demo_selected', {effect:value('pattern_id')});
    };
    input('pattern_id').addEventListener('change',sync);
    main.querySelectorAll('[data-ghostlab-blueprint-key]').forEach(field=>field.addEventListener('input',stop));
    sync();
    panel.querySelector('[data-visual]').onclick=()=>{
        stop();active=true;
        DeepScanner.style(effect,{pattern_id:value('pattern_id'),frame_id:value('frame_id'),frame_color:value('frame_color'),button_color:value('button_color')});
        effect.dataset.label=text('start');effect.classList.add('is-visible');delete log.dataset.ghostI18n; log.textContent=text('start');
        window.GameSfx?.unlock();
        sound=DeepScanner.soundLoop(schema.sfx_id.sound_events[value('sfx_id')],()=>active && panel.isConnected);
        timer=setTimeout(()=>{
            const phase=panel.querySelector('[data-result]').value;
            stop();
            log.textContent=text(phase)+' — '+window.GhostLocale.t('lab.service.demo_'+phase);
        },6000);
    };
    panel.querySelector('[data-stop]').onclick=()=>{stop();ghostSet(log, 'lab.service.demo_stopped');};
    panel.querySelector('[data-audio]').onclick=async()=>{
        stop();const ownSerial=serial;
        const handle=await DeepScanner.previewSound(value('sfx_id'));
        if(!panel.isConnected || ownSerial!==serial)handle?.stop();else sound=handle;
    };
    const detach=DeepScanner.registerPreview(stop);
    const observer=new MutationObserver(()=>{if (!panel.isConnected) {stop();detach();observer.disconnect();}});
    observer.observe(document.body,{childList:true,subtree:true});
}
