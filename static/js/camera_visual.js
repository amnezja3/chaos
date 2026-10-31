/* Real desktop integration. All windows use the standard application shell. */
(() => {
    'use strict';
    const owner = crypto.randomUUID();
    const states = new Map(), viewers = new Map(), references = new Map();
    let busy = false, stopped = false, retryAfter = 0;
    const en = () => (document.documentElement.lang || '').startsWith('en');
    const label = (pl, english) => en() ? english : pl;
    async function request(url, data) {
        const response = await fetch(url, data ? {method: 'POST', keepalive:data.action === 'release', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)} : {});
        if ([401, 403].includes(response.status)) {
            if (response.status === 401) stopped = true;
            throw new Error('camera_access_denied');
        }
        const result = await response.json();
        if (!response.ok || result.success === false) throw new Error(result.reason || 'camera_request_failed');
        return result;
    }
    function windowAction(s, action) {
        return request('/api/camera-visual/window', {owner, receipt: s.reference_id, action});
    }
    function remove(app) {
        if (!app) return;
        app._cameraDispose?.();
        disposeOperationFeedbackWindow(app, 'camera_window_closed');
        app.remove();
        if (typeof renderRunningApps === 'function') renderRunningApps();
    }
    function standardWindow(id, title, content) {
        const {app, hydrated} = prepareApplicationRenderWindow(id, 'window');
        app.dataset.appTitle = title;
        app.innerHTML = `<div class="title-bar"><span>${escapeHTML(title)}</span><span class="close-btn">✕</span></div><div class="app-content">${content}</div>`;
        finishApplicationRenderWindow(app, hydrated);
        bindWindowMaximize(app, title);
        return app;
    }
    function reference(s, existing) {
        let app = existing || references.get(s.reference_id);
        if (s.reference_closed) return;
        if (s.success && Date.now() >= s.close_at * 1000) {
            if (app?.isConnected) remove(app);
            references.delete(s.reference_id);
            return;
        }
        if (!app?.isConnected) {
            app = standardWindow(`camera-reference-${s.reference_id}`, s.app_name,
                `<p role="status">${s.success ? label('Połączenie przyjęte.', 'Connection accepted.') : label('Operacja kamery nie powiodła się.', 'Camera operation failed.')}</p>`);
        }
        references.set(s.reference_id, app);
        app.dataset.cameraReference = s.reference_id;
        // The authored scene may finish or clear its viewport after the reply.
        // Keep the authoritative final result visible in that same instance.
        if (existing && !app.querySelector('.camera-reference-result')) {
            const result = document.createElement('p');
            result.className = 'camera-reference-result';
            result.setAttribute('role', 'status');
            result.dataset.success = String(s.success);
            result.textContent = s.success ? label('Połączenie przyjęte.', 'Connection accepted.')
                : label('Operacja kamery nie powiodła się.', 'Camera operation failed.');
            app.appendChild(result);
        }
        if (!app.dataset.cameraReferenceBound) {
            app.dataset.cameraReferenceBound = '1';
            app.querySelector('.close-btn')?.addEventListener('click', () => {
                s.reference_closed = true;
                windowAction(s, 'close_reference').catch(() => { s.reference_closed = false; });
                remove(app);
            });
        }
        if (s.success) {
            app.dataset.cameraCloseAt = String(s.close_at * 1000);
            scheduleOperationalAppAutoClose(app);
        }
    }
    function viewer(s, lease) {
        // A running pre-upgrade server can still return v1 while static assets
        // are refreshed. Never construct a partial window from that contract.
        if (s.motion?.version !== 2 || !s.motion.start || !s.motion.control || !s.motion.end) return;
        let entry = viewers.get(s.instance_id);
        if (!entry?.app.isConnected) {

            const panelId = s.instance_id + '-panel';
            const lat = Number(s.target.lat), lon = Number(s.target.lng ?? s.target.lon);
            const coordinates = `${lat.toFixed(4)}:${lon.toFixed(4)}`;
            const app = standardWindow(s.instance_id, `Camera Network · ${s.target.camera_id ? label('Kamera', 'Camera') : label('Paryż', 'Paris')}`, `
                <div class="camera-visual-location"><div data-camera-actions></div><span title="${lat}:${lon}">${coordinates}</span></div>
                <div class="camera-visual-frame">
                    <div class="camera-visual-images"><img data-camera-frame="${s.motion.image}" alt="" hidden></div>
                    <div class="camera-visual-effects" aria-hidden="true"><div class="camera-fx-grain"></div><div class="camera-fx-scan"></div><div class="camera-fx-tracking"></div><div class="camera-fx-chroma"></div><div class="camera-fx-blocks"></div></div>
                    <div class="camera-visual-brand"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 25V7l12 12L28 7v18M4 25l12-6 12 6"/></svg><span>MapiFi</span></div>
                    <div class="camera-visual-hud"><span data-camera-status>CONNECTING</span><span class="camera-visual-rec" hidden>● REC</span><time data-camera-clock></time></div>
                    <div class="camera-visual-logs" aria-hidden="true"></div>
                    <div class="camera-visual-no-signal" role="status" hidden>NO SIGNAL</div>
                </div>
                <footer class="camera-visual-footer mapifi-credit"><div class="mapifi-credit-heading"><strong>MapiFi</strong><span data-camera-material></span><button type="button" aria-controls="${panelId}" aria-expanded="false" data-camera-panel-link></button></div><dl><div><dt data-camera-author-label></dt><dd data-camera-author></dd></div><div><dt data-camera-source-label></dt><dd>CHAOS · Paris</dd></div><div><dt data-camera-rights-label></dt><dd data-camera-rights></dd></div></dl></footer>
                <section id="${panelId}" class="camera-visual-panel" hidden><p data-camera-provenance></p></section><div data-chaos-link-output role="status" hidden></div>`);
            app.classList.add('camera-visual-window');
            app._cameraState = s;
            app.dataset.cameraViewer = s.instance_id;
            const actions = app.querySelector('[data-camera-actions]');
            const focus = ChaosLinks.create(`focus:${lat}:${lon}`, true);
            focus.dataset.cameraLocation = '';
            actions.append(focus, ChaosLinks.create(`teleport:${lat}:${lon}`, true));
            const title = app.querySelector('.title-bar > span');
            const icon = document.createElement('img');
            icon.className = 'camera-network-icon';
            icon.src = '/static/images/camera_visual/camera-network-v1.png';
            icon.alt = ''; icon.draggable = false;
            title.prepend(icon);
            const images = [...app.querySelectorAll('img[data-camera-frame]')];
            const compareButton = document.createElement('button');
            compareButton.type = 'button';
            compareButton.dataset.cameraCompare = '';
            compareButton.textContent = label('Porównaj 6 zakłóceń', 'Compare 6 effects');
            compareButton.disabled = true;
            compareButton.setAttribute('aria-expanded', 'false');
            app.querySelector('.mapifi-credit-heading').append(compareButton);
            const comparison = document.createElement('section');
            comparison.className = 'camera-effect-comparison';
            comparison.hidden = true;
            comparison.setAttribute('aria-label', label('Porównanie zakłóceń', 'Effects comparison'));
            app.querySelector('.camera-visual-frame').append(comparison);
            compareButton.addEventListener('click', () => {
                if (!comparison.hidden) {
                    comparison.hidden = true; comparison.replaceChildren();
                    compareButton.setAttribute('aria-expanded', 'false');
                    return;
                }
                const scenarios = [
                    ['grain', label('Ziarno sensora', 'Sensor grain')],
                    ['scan', label('Linie skanowania', 'Scan lines')],
                    ['tracking', label('Pas zakłóceń', 'Tracking band')],
                    ['chroma', label('Rozjazd kolorów', 'Chroma tear')],
                    ['blocks', label('Bloki kompresji', 'Compression blocks')],
                    ['dropout', label('Utrata sygnału', 'Signal loss')]
                ];
                for (const [effect, name] of scenarios) {
                    const card = document.createElement('article');
                    const heading = document.createElement('h3'); heading.textContent = name;
                    const frame = document.createElement('div'); frame.className = 'camera-visual-frame';
                    const imageLayer = document.createElement('div'); imageLayer.className = 'camera-visual-images';
                    const image = images[0].cloneNode(); image.removeAttribute('data-camera-frame');
                    imageLayer.append(image); frame.append(imageLayer);
                    const layer = document.createElement('div'); layer.className = 'camera-visual-effects';
                    layer.setAttribute('aria-hidden', 'true');
                    const noise = document.createElement('div'); noise.className = 'camera-fx-' + effect;
                    layer.append(noise); frame.append(layer);
                    const caption = document.createElement('span'); caption.className = 'camera-effect-caption';
                    caption.textContent = effect === 'dropout' ? 'SIMULATION · NO SIGNAL' : 'MapiFi · FX PREVIEW';
                    frame.append(caption); card.append(heading, frame); comparison.append(card);
                }
                comparison.hidden = false;
                compareButton.setAttribute('aria-expanded', 'true');
            });
            const track = s.motion;
            const pathName = 'camera-path-' + s.instance_id;
            const pathStyle = document.createElement('style');
            const frames = Array.from({length:61}, (_, index) => {
                const fraction = index / 60;
                const t = (1 - Math.cos(Math.PI * fraction)) / 2;
                const point = [0,1].map(axis => (1-t)**2 * track.start[axis] + 2*(1-t)*t*track.control[axis] + t*t*track.end[axis]);
                return (fraction*100) + '% { transform:translate(' + (-point[0]) + '%,' + (-point[1]) + '%); }';
            });
            pathStyle.textContent = '@keyframes ' + pathName + ' {' + frames.join('') + '}';
            app.appendChild(pathStyle);
            images[0].style.animationName = pathName;
            images[0].style.animationDuration = track.seconds + 's';
            images[0].style.animationTimingFunction = 'linear';
            images[0].style.animationDelay = (-((Date.now()/1000-s.ready_at) % (track.seconds*2))) + 's';
            const fallback = app.querySelector('.camera-visual-no-signal');
            const abort = new AbortController(), urls = new Set();
            let disposed = false, active = -1;
            const clock = app.querySelector('[data-camera-clock]');
            const logs = app.querySelector('.camera-visual-logs');
            const clockFormat = new Intl.DateTimeFormat('en-GB', {timeZone:'Europe/Paris', hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false});
            let tickCount = 0;
            const tick = () => {
                if (disposed || app.classList.contains('is-window-minimized') || app.classList.contains('camera-suspended')) return;
                const now = new Date();
                clock.dateTime = now.toISOString();
                clock.textContent = `${clockFormat.format(now)} PARIS`;
                if (active < 0 || !fallback.hidden || tickCount++ % 3 !== 0) return;
                const line = document.createElement('div');
                const messages = ['LINK SYNC', 'FRAME BUFFER OK', 'CHANNEL ACTIVE', 'SIGNAL LOCK'];
                line.textContent = `${clockFormat.format(now)} > ${messages[Math.floor(tickCount / 3) % messages.length]}`;
                logs.appendChild(line);
                while (logs.children.length > 3) logs.firstElementChild.remove();
            };
            tick();
            const telemetry = setInterval(tick, 1000);
            const load = () => images.map(async (img, i) => {
                try {
                    if (s.archive_id && !app._cameraState?.material) return false;
                    const response = await fetch('/api/camera-visual/media/'+encodeURIComponent(s.reference_id)+'/'+s.motion.image, {cache:'no-store', signal:abort.signal});
                    if (!response.ok) throw new Error('media_unavailable');
                    const blob = await response.blob();
                    if (disposed) return false;
                    const url = URL.createObjectURL(blob);
                    urls.add(url); img.src = url;
                    await img.decode();
                    return !disposed;
                } catch (_) { return false; }
            });
            let loaded = load();
            const show = async () => {
                const i = 0;
                const attempt = loaded;
                const available = await attempt[i];
                if (attempt !== loaded) return;
                if (!available || disposed) {
                    if (!disposed && active < 0) {
                        fallback.hidden = false;
                        app.querySelector('[data-camera-status]').textContent = 'OFFLINE';
                    }
                    return;
                }
                fallback.hidden = true;
                app.querySelector('[data-camera-status]').textContent = 'ONLINE';
                app.querySelector('.camera-visual-rec').hidden = false;
                images.forEach((img, index) => {
                    img.hidden = false;
                    img.classList.toggle('is-active', index === i);
                    img.setAttribute('aria-hidden', String(index !== i));
                });
                active = i; app.dataset.cameraFrame = String(s.motion.image);
                compareButton.disabled = false;
            };
            app._cameraMaterialReady = state => {
                app._cameraState = state;
                localizeViewer(app);
                loaded = load(); show();
            };
            app._cameraDispose = () => {
                disposed = true; clearInterval(telemetry); abort.abort();
                urls.forEach(url => URL.revokeObjectURL(url)); urls.clear();
            };
            app.querySelector('[data-camera-panel-link]').addEventListener('click', event => {
                event.preventDefault();
                const panel = app.querySelector('.camera-visual-panel');
                panel.hidden = !panel.hidden;
                event.currentTarget.setAttribute('aria-expanded', String(!panel.hidden));
            });
            localizeViewer(app);
            app.querySelector('.close-btn').addEventListener('click', async event => {
                // Persist consumption before the standard shell removes the DOM.
                event.preventDefault(); event.stopImmediatePropagation();
                if (app.dataset.cameraClosing) return;
                app.dataset.cameraClosing = '1';
                try {
                    const closed = await windowAction(s, 'close');
                    if (!closed.closed) throw new Error('close_not_confirmed');
                    s.viewer_closed = true;
                    remove(app); viewers.delete(s.instance_id);
                } catch (_) {
                    const message = app.querySelector('[data-chaos-link-output]');
                    message.hidden = false;
                    message.textContent = label('Nie zapisano zamknięcia. Spróbuj ponownie.', 'Close was not saved. Please retry.');
                } finally { delete app.dataset.cameraClosing; }
            }, true);
            show();
            entry = {app, timer: null};
            viewers.set(s.instance_id, entry);
        } else if (s.image_id && s.image_id !== entry.app._cameraState?.image_id) {
            entry.app._cameraMaterialReady(s);
        }
        clearTimeout(entry.timer);
        entry.app.classList.remove('camera-suspended');
        entry.renewAt = lease * 1000 - 20000;
        // Ownership expiry pauses presentation, not the application's lifetime.
        // Keep the DOM and decoded media; never show an active feed without a lease.
        entry.timer = setTimeout(() => suspend(entry), Math.max(0, lease * 1000 - Date.now() - 1000));
    }
    function suspend(entry) {
        entry.app.classList.add('camera-suspended');
    }
    async function reconcile(s) {
        states.set(s.reference_id, s);
        reference(s);
        const entry = viewers.get(s.instance_id);
        if (entry && s.archive_id && s.image_id && !s.material) {
            entry.app.querySelector('.camera-visual-no-signal').hidden = false;
            entry.app.querySelector('[data-camera-status]').textContent = 'OFFLINE';
            entry.app.querySelector('.camera-visual-rec').hidden = true;
            entry.app.querySelector('.camera-effect-comparison').hidden = true;
            entry.app.querySelector('[data-camera-compare]').disabled = true;
        }
        if (s.state !== 'ready' || s.viewer_closed) {
            if (entry) { clearTimeout(entry.timer); remove(entry.app); viewers.delete(s.instance_id); }
            return;
        }
        const needsImage = s.archive_id && !s.image_id && s.visual_status === 'READY';
        if (entry?.app.isConnected && Date.now() < entry.renewAt && !needsImage) return;
        const response = await windowAction(s, 'claim');
        if (response.granted) viewer(response.camera_visual, response.lease_until);
        else if (entry) suspend(entry);
    }
    async function poll() {
        if (busy || stopped || document.hidden || Date.now() < retryAfter) return;
        busy = true;
        try {
            const data = await request('/api/camera-visual/state');
            if (!data.enabled) { stopped = true; return; }
            const visible = new Set(data.sessions.map(s => s.instance_id));
            for (const [id, entry] of viewers) if (!visible.has(id)) {remove(entry.app); viewers.delete(id);}
            for (const s of data.sessions) await reconcile(s);
            document.querySelectorAll('[data-camera-progress]').forEach(node => {
                const s = states.get(node.dataset.cameraProgress);
                if (!s) return;
                node.querySelector('b').textContent = `${s.progress || 0}%`;
                node.querySelector('progress').value = s.progress || 0;
            });
            document.querySelectorAll('[data-camera-activation-list]').forEach(node => {
                node.innerHTML = window.CameraVisualPilot.controlMarkup();
            });
        } catch (_) {
            // Never open a viewer or extend its local lease on an unverified response.
            retryAfter = Date.now() + 5000;
        } finally { busy = false; }
    }
    window.CameraVisualPilot = {
        accept(context, s) {
            states.set(s.reference_id, s);
            const source = [...document.querySelectorAll('.app-window')].find(a => a.dataset.launchReceipt === context.launch_receipt);
            if (source) {
                references.set(s.reference_id, source);
                if (s.success) source.dataset.cameraCloseAt = String(s.close_at * 1000);
                reference(s, source);
            }
        },
        operationMarkup(item) {
            const v = item.camera_visual;
            if (!v) return '';
            const start = Date.parse(item.started_at)/1000 || v.download_at;
            const end = Date.parse(item.expires_at)/1000 || v.ready_at;
            const percent = Math.max(0, Math.min(100, Math.floor((Date.now()/1000-start)/Math.max(1,end-start)*100)));
            return `<label class="camera-activation-progress" data-camera-progress="${escapeHTML(v.receipt)}">${label('Pobieranie aktywatora','Activation download')} <b>${percent}%</b><progress max="100" value="${percent}"></progress></label>`;
        },
        controlMarkup() {
            return [...states.values()].filter(s=>s.success && Date.now()>=s.close_at*1000).map(s => {
                const ready = s.state === 'ready';
                const status = s.viewer_closed ? label('Dostęp zużyty — wymagane nowe hakowanie','Access consumed — hack again') : ready ? label('Aktywator zapisany — podgląd otwiera się automatycznie','Activation saved — viewer opens automatically') : s.state === 'save_pending' ? label('Oczekiwanie na zapis — sprawdź wolne miejsce na dysku','Waiting for save — check free disk space') : s.state === 'cancelled' ? label('Operacja zakończona bez aktywatora','Operation ended without activation') : `${label('Pobieranie aktywatora','Activation download')} ${s.progress || 0}%`;
                return `<div class="camera-activation-progress" data-camera-activation="${escapeHTML(s.reference_id)}"><span>${escapeHTML(s.app_name)}: ${status}</span></div>`;
            }).join('');
        }
    };

    function localizeViewer(app) {
        app.querySelector('[data-camera-panel-link]').textContent = label('O materiale', 'About image');
        app.querySelector('[data-camera-material]').textContent = label('Widok syntetyczny', 'Synthetic view');
        app.querySelector('[data-camera-author-label]').textContent = label('Autorstwo', 'Attribution');
        app.querySelector('[data-camera-author]').textContent = label('Generowane AI', 'AI-generated');
        app.querySelector('[data-camera-source-label]').textContent = label('Źródło', 'Source');
        app.querySelector('[data-camera-rights-label]').textContent = label('Licencja', 'License');
        app.querySelector('[data-camera-rights]').textContent = label('Nie przypisano', 'Not assigned');
        app.querySelector('[data-camera-location]').title = label('Pokaż lokalizację kamery na mapie', 'Focus camera location on map');
        app.querySelector('[data-camera-provenance]').textContent = label(
            'Fikcyjna ulica Paryża, wygenerowana AI dla CHAOS. Obraz nie dokumentuje wskazanej lokalizacji. Ruch, REC i logi stanowią symulację, bez nagrywania; zegar wskazuje czas Paryża.',
            'AI-generated fictional Paris street created for CHAOS. The image does not document this location. Motion, REC and logs are simulated, with no recording; the clock shows Paris time.');
        app.querySelectorAll('img[data-camera-frame]').forEach(img => {
            img.alt = label('Symulowany podgląd kamery w Paryżu', 'Simulated Paris camera view');
        });
        const s = app._cameraState;
        const material = s?.material;
        if (s?.archive_id) {
            app.querySelector('[data-camera-material]').textContent = material?.source === 'Mapillary'
                ? label('Materiał archiwalny — symulacja', 'Archive material — simulation')
                : material ? label('Widok syntetyczny', 'Synthetic view') : label('Brak materiału', 'No material');
            app.querySelector('[data-camera-author]').textContent = material?.author || '—';
            app.querySelector('[data-camera-source-label]').nextElementSibling.textContent = material?.source || '—';
            app.querySelector('[data-camera-rights]').textContent = material?.license || '—';
            app.querySelector('[data-camera-provenance]').textContent = material
                ? `${material.source} · ${material.image_id} · ${material.source === 'Mapillary' ? label('Otoczenie lokalizacji; symulacja, nie transmisja na żywo.', 'Location surroundings; simulation, not a live broadcast.') : label('Fikcyjna ulica Paryża wygenerowana AI; nie dokumentuje tej lokalizacji.', 'AI-generated fictional Paris street; does not document this location.')} ${label('Zmiany', 'Changes')}: ${(material.changes || []).join(', ')}`
                : label('Materiał niedostępny. Dostęp do okna nie potwierdza dostępności fotografii.', 'Material unavailable. Window access does not guarantee imagery coverage.');
            app.querySelectorAll('img[data-camera-frame]').forEach(img=>{img.alt=label('Symulowany podgląd otoczenia kamery','Simulated camera surroundings');});
            app.querySelector('.camera-source-actions')?.remove();
            if (material?.source === 'Mapillary' && /^https:\/\/www\.mapillary\.com\/app\/\?pKey=\d+$/.test(material.source_url || '')) {
                const section=document.createElement('div'); section.className='camera-source-actions';
                const source=document.createElement('a'); source.href=material.source_url;
                source.textContent=label('Otwórz źródło — Mapillary','Open source — Mapillary');
                const copy=document.createElement('button'); copy.type='button'; copy.textContent=label('Kopiuj adres','Copy URL');
                const feedback=document.createElement('span'); feedback.setAttribute('role','status');
                copy.addEventListener('click',async()=>{try {await navigator.clipboard.writeText(source.href);feedback.textContent=label('Skopiowano','Copied');}catch(_){feedback.textContent=source.href;}});
                source.addEventListener('click',event=>{
                    event.preventDefault();
                    if(section.querySelector('[data-external-confirm]')) return;
                    const confirm=document.createElement('div'); confirm.dataset.externalConfirm='';
                    const text=document.createElement('p');text.textContent=label('EXTERNAL CONNECTION — opuścisz CHAOS i przejdziesz do Mapillary. Kontynuować?','EXTERNAL CONNECTION — leave CHAOS and visit Mapillary. Continue?');
                    const stay=document.createElement('button');stay.type='button';stay.textContent=label('POZOSTAŃ W CHAOS','STAY IN CHAOS');
                    const go=document.createElement('a');go.href=source.href;go.textContent=label('OTWÓRZ MAPILLARY','OPEN MAPILLARY');
                    const cancel=()=>{confirm.remove();source.focus();};stay.addEventListener('click',cancel);
                    confirm.addEventListener('keydown',e=>{if(e.key==='Escape'){e.stopPropagation();cancel();}});
                    confirm.append(text,stay,go);section.append(confirm);stay.focus();
                });
                section.append(source,copy,feedback);
                if (/^https:\/\/creativecommons\.org\/licenses\/[a-z-]+\/[0-9.]+\/$/.test(material.license_url || '')) {
                    const license=document.createElement('a');license.href=material.license_url;license.textContent=material.license;section.append(license);
                }
                app.querySelector('.camera-visual-panel').append(section);
            }
        }
    }
    document.addEventListener('ghost:locale-changed', () => {
        for (const {app} of viewers.values()) localizeViewer(app);
    });
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            for (const entry of viewers.values()) { clearTimeout(entry.timer); remove(entry.app); }
            for (const s of states.values()) if (viewers.has(s.instance_id)) windowAction(s, 'release').catch(()=>{});
            viewers.clear();
        } else poll();
    });
    window.addEventListener('pagehide', () => {
        for (const s of states.values()) if (viewers.has(s.instance_id)) windowAction(s, 'release').catch(()=>{});
    });
    setInterval(poll, 2000);
    poll();
})();
