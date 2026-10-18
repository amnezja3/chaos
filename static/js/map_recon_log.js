/* Recon contributes to the existing map glitch/log, without a loading job. */
(function (global) {
    let current = {text:'', blocked:false};
    function sync() {
        const loading = global.mapLoadingState;
        if (!loading || !global.ensureMapGlitchOverlay) return;
        const overlay = loading.overlay || global.ensureMapGlitchOverlay();
        if (!overlay) return;
        const active = Boolean(loading.visible);
        const base = active ? (loading.intensity || 'normal') : 'normal';
        const heavy = ['heavy', 'overloaded', 'error'].includes(base);
        // MASA supplies a minimum second level, never downgrades a real load.
        overlay.classList.toggle('is-heavy', heavy);
        overlay.classList.toggle('is-overloaded', heavy);
        overlay.classList.toggle('is-slow', heavy || base === 'slow' || Boolean(current.text && current.blocked));
        overlay.classList.toggle('has-recon-log', Boolean(current.text));
        if (current.text) {
            const other = active ? loading.log?.textContent : '';
            overlay.dataset.log = [other, 'Chaos Log // ' + current.text].filter(Boolean).join('\n');
            overlay.classList.add('is-visible', 'has-map-log');
        } else if (active) {
            overlay.dataset.log = loading.log?.textContent || '';
            overlay.classList.add('is-visible', 'has-map-log');
        } else {
            overlay.dataset.log = '';
            overlay.classList.remove('is-visible', 'has-map-log', 'is-slow', 'is-heavy', 'is-overloaded');
        }
    }
    global.MapReconLog = {sync, set(text, blocked) { current = {text, blocked}; sync(); }};
    global.addEventListener('pagehide', () => {current = {text:'', blocked:false}; sync();});
})(window);
