/* Presentation only: provider policy and probe ownership remain server-owned. */
(function (global) {
    'use strict';
    const panel = document.getElementById('poi-channel-status');
    if (!panel) return;
    let pending = false, currentKey = '', state = '', timer = null;
    const blocks = new Map();
    const metrics = Object.create(null);
    const t = (key, params = {}) => global.GhostLocale.t('map.scan.masa.' + key, params);
    const keyFor = (lat, lng) => `${Number(lat)}:${Number(lng)}`;
    const event = name => {
        metrics[name] = (metrics[name] || 0) + 1;
        global.dispatchEvent(new CustomEvent('poi-ux', {detail: {event: name}}));
        console.info('poi_ux', JSON.stringify({event: name}));
    };
    function remaining(key) { return Math.max(0, (blocks.get(key) || 0) - performance.now()); }
    function paint(lat, lng) {
        const key = lat === undefined ? currentKey : keyFor(lat, lng);
        document.querySelectorAll('[data-default-scan]').forEach(button => {
            const disabled = pending || remaining(key) > 0;
            button.setAttribute('aria-disabled', String(disabled));
            button.classList.toggle('poi-scan-disabled', disabled);
        });
    }
    function render() {
        const milliseconds = remaining(currentKey);
        // Expiry is silent: remove MASA's visual state, without claiming recovery.
        if (state === 'blocked' && blocks.has(currentKey) && milliseconds <= 0) state = '';
        let text = state ? t(state) : '';
        if (state === 'blocked') {
            if (blocks.has(currentKey)) {
                const seconds = Math.ceil(milliseconds / 1000);
                text = t('cooldown', {time: t('duration', {
                    minutes: Math.floor(seconds / 60), seconds: seconds % 60})});
            } else text += ' ' + t('unknown_time');
        }
        panel.dataset.state = state;
        if (panel.textContent !== text) panel.textContent = text;
        global.MapReconLog?.set(text, state === 'blocked' &&
            (!blocks.has(currentKey) || milliseconds > 0));
        paint();
        clearTimeout(timer);
        if (milliseconds > 0) timer = setTimeout(render, 250); // Local clock only; no fetch.
    }
    global.PoiMasa = {
        metrics: () => ({...metrics}),
        paint,
        begin(lat, lng) {
            for (const [oldKey, until] of blocks) if (until <= performance.now()) blocks.delete(oldKey);
            const key = keyFor(lat, lng);
            if (pending || remaining(key) > 0) {
                event('scan_short_circuited');
                return false;
            }
            pending = true;
            currentKey = key;
            paint();
            return true;
        },
        finish() { pending = false; paint(); },
        accept(data) {
            const signal = data.interference;
            if (!signal || signal.type !== 'masa') {
                state = ''; render(); return false;
            }
            const next = signal.state;
            if (!['ready', 'degraded', 'blocked', 'recovering', 'restored'].includes(next)) return false;
            const previous = state;
            state = next === 'ready' ? '' : next;
            if (next === 'blocked') {
                const ttl = Number(signal.retry_after_seconds);
                if (Number.isFinite(ttl) && ttl > 0) blocks.set(currentKey, performance.now() + ttl * 1000);
                else blocks.delete(currentKey);
            } else blocks.delete(currentKey);
            if (['blocked', 'degraded', 'restored'].includes(next) && previous !== state) event('masa_' + next + '_shown');
            render();
            if (next === 'restored') {
                clearTimeout(timer);
                timer = setTimeout(() => {state = ''; render();}, 5000);
            }
            // Chaos Log already explains the result; suppress repeated toasts.
            return next === 'blocked' || next === 'recovering';
        }
    };
    global.addEventListener('pagehide', () => clearTimeout(timer));
    document.addEventListener('ghost:locale-changed', render);
    global.addEventListener('deep-scanner-change', () => {
        // A different installed scanner may have a different eligible provider
        // set. Only the backend can decide whether that policy is blocked.
        blocks.clear(); state = ''; render();
    });
})(window);
