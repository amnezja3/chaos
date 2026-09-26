/* 143.5a: live committed receipts only; history is intentionally not replayed. */
(() => {
    const variants = Object.freeze([
        null,
        ['consequence_01_fine', 5250.563, 'MANDAT'],
        ['consequence_02_fine', 3526.500, 'MANDAT // RECYDYWA'],
        ['consequence_03_confiscation', 2977.938, 'KONFISKATA'],
        ['consequence_04_confiscation', 2586.063, 'KONFISKATA'],
        ['consequence_05_confiscation_fine', 3813.875, 'KONFISKATA I MANDAT'],
        ['consequence_06_detention', 2089.750, 'WYROK // ARESZT'],
        ['consequence_07_detention', 1253.875, 'WYROK // ARESZT'],
        ['consequence_08_detention', 8045.688, 'WYROK // ARESZT'],
        ['consequence_09_detention', 3813.875, 'WYROK // ARESZT']
    ]);
    const seen = new Set();
    let queue = Promise.resolve();
    function visibleMap() {
        if (document.visibilityState === 'hidden') return null;
        for (const frame of document.querySelectorAll('iframe')) {
            try {
                const doc = frame.contentDocument;
                if (frame.getClientRects().length && doc?.querySelector('.leaflet-container')
                    && frame.contentWindow.applyDetentionView) return doc;
            } catch (_) {}
        }
        return null;
    }
    function present(doc, receipt) {
        return new Promise(resolve => {
            const variant = variants[receipt.stage];
            if (!variant) { resolve(); return; }
            const effects = receipt.effects || {};
            const overlay = doc.createElement('div');
            overlay.className = 'chaos-ghost-ability-overlay is-visible consequence-show';
            overlay.style.cssText = '--ability-accent:#9dffb8;--ability-deep:#ff234b;position:fixed;inset:0;z-index:100000;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.8);pointer-events:none;padding:12px';
            const panel = doc.createElement('div');
            panel.className = 'chaos-ghost-ability-panel';
            panel.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:12px;width:min(94vw,920px);height:auto;min-height:0;padding:0;max-height:94vh;background:transparent;border:0;box-shadow:none;overflow:visible;text-align:center;animation-duration:.15s';
            const img = doc.createElement('img');
            img.src = `/static/images/consequences/show/${variant[0]}.png`;
            img.className = 'chaos-ghost-ability-asset';
            img.alt = ''; img.style.cssText = 'width:min(78vw,58vh,560px);height:min(78vw,58vh,560px);flex-shrink:0;object-fit:contain;image-rendering:auto';
            img.onerror = () => img.remove();
            const text = doc.createElement('div');
            const title = doc.createElement('h2');
            title.className = 'chaos-ghost-ability-title'; title.textContent = variant[2];
            title.style.cssText = 'font-size:clamp(22px,5vw,54px);margin:0 0 10px;overflow-wrap:anywhere';
            const body = doc.createElement('p');
            body.style.cssText = 'color:#c4e6c6;font:700 clamp(12px,2vw,18px) monospace';
            body.textContent = effects.detention_seconds
                ? `Czas aresztu: ${Math.ceil(effects.detention_seconds / 60)} min online.`
                : `Mandat: ${Number(effects.fine_hc || 0)} HC. Skonfiskowane narzędzia: ${(effects.tool_ids || []).length}.`;
            text.append(title, body); panel.append(img, text); overlay.append(panel);
            let done = false, started = false, handle, fallbackTimer, deadline, visibilityTimer;
            const finish = () => {
                if (done) return;
                done = true;
                clearTimeout(fallbackTimer); clearTimeout(deadline);
                clearInterval(visibilityTimer);
                overlay.remove(); handle?.stop({fade_ms: 0}); resolve();
            };
            const start = () => {
                if (done || started) return;
                started = true; clearTimeout(deadline);
                // Keep 20% of the map visible even over the prison's 60% shade:
                // .4 * .5 = .2. Outside prison the overlay itself is 80% black.
                if (doc.querySelector('.detention-map-shade')) overlay.style.background = 'rgba(0,0,0,.5)';
                doc.body.appendChild(overlay);
                visibilityTimer = setInterval(() => { if (visibleMap() !== doc) finish(); }, 200);
            };
            const fallback = () => {
                if (done || started) return;
                handle?.stop({fade_ms: 0}); // cancel pending audio: never play after fallback
                start(); fallbackTimer = setTimeout(finish, variant[1]);
            };
            const playAudio = () => {
                if (visibleMap() !== doc) { finish(); return; }
                deadline = setTimeout(fallback, 1500);
                try {
                    handle = window.GameSfx?.play(`consequence.stage_${receipt.stage}`, {
                        event_id: `consequence:${receipt.encounter_id}`, on_start: start, on_end: finish
                    });
                    if (!handle) fallback();
                    else Promise.resolve(handle.started).then(result => { if (!result?.ok) fallback(); }, fallback);
                } catch (_) { fallback(); }
            };
            const beginAudio = () => {
                // Source deltas precede this receipt. Let Leaflet paint them
                // before covering the map; a stalled frame never blocks a verdict.
                const view = doc.defaultView;
                if (!view?.requestAnimationFrame) { playAudio(); return; }
                let played = false;
                const ready = () => {
                    if (played) return;
                    played = true; clearTimeout(paintDeadline); playAudio();
                };
                const paintDeadline = setTimeout(ready, 250);
                view.requestAnimationFrame(() => view.requestAnimationFrame(ready));
            };
            // Decode the one selected PNG before starting its short soundtrack.
            // Slow/missing assets cannot delay the verdict indefinitely.
            if (typeof img.decode === 'function') {
                let imageTimer;
                Promise.race([
                    img.decode().catch(() => img.remove()),
                    new Promise(done => { imageTimer = setTimeout(() => { img.remove(); done(); }, 1500); })
                ]).then(() => { clearTimeout(imageTimer); beginAudio(); });
            } else beginAudio();
        });
    }
    async function receiveOne(payload) {
        if (document.visibilityState === 'hidden') return;
        const doc = visibleMap();
        // A visible desktop claims once even with a closed map: retain the verdict dialog.
        const response = await fetch('/api/response/consequence-show/claim', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({encounter_id: payload.encounter_id})
        });
        if (!response.ok) return;
        const receipt = (await response.json()).show;
        if (!receipt) return;
        if (doc && visibleMap() === doc) await present(doc, receipt);
        if (receipt.effects?.sanction_id === window.DetentionUI?.state?.sanction_id) {
            await window.DetentionUI.blockedAction();
        }
    }
    window.ConsequenceShow = {receive(payload) {
        const id = payload?.encounter_id;
        if (typeof id !== 'string' || seen.has(id)) return;
        seen.add(id);
        if (seen.size > 256) seen.delete(seen.values().next().value);
        queue = queue.then(() => receiveOne(payload)).catch(error => console.warn('[consequence show]', error));
    }};
})();
