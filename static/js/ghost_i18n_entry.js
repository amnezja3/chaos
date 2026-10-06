/* Device preference applies only before login; account locale wins on desktop. */
(async function () {
    'use strict';
    const runtime = window.GhostLocale;
    const select = document.querySelector('[data-entry-locale]');
    if (!runtime || !select) return;
    const config = JSON.parse(document.getElementById('ghost-i18n-bootstrap').textContent);
    let device;
    try { device = localStorage.getItem('ghost_entry_locale'); } catch (_) { /* storage optional */ }
    const preferred = window.GhostI18n.resolveLocale(config.manifest, {device: config.resume_locale || device, browser: navigator.language});
    for (const language of runtime.languages()) {
        const option = document.createElement('option');
        option.value = language.tag;
        option.textContent = language.name;
        select.appendChild(option);
    }
    const hidden = document.querySelector('[name=locale]');
    const status = document.querySelector('[data-entry-locale-status]');
    const sync = () => {
        select.value = runtime.getLocale();
        if (hidden) hidden.value = runtime.getLocale();
    };
    select.disabled = true;
    try { await runtime.changeLocale(preferred); }
    catch (_) { if (status) status.textContent = runtime.t('locale.load_failed'); }
    finally { sync(); select.disabled = false; runtime.render(); }
    select.addEventListener('change', async () => {
        select.disabled = true;
        if (status) status.textContent = '';
        try {
            await runtime.changeLocale(select.value);
            try { localStorage.setItem('ghost_entry_locale', runtime.getLocale()); } catch (_) { /* storage optional */ }
        } catch (_) { if (status) status.textContent = runtime.t('locale.load_failed'); }
        finally { sync(); select.disabled = false; }
    });
})();
