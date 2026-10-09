/* The server owns the roll, crash, cooldown and durable receipt. */
async function firmwareRequest(url, body) {
    const response = await fetch(url, body === undefined ? {cache: 'no-store'} : {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok || data.success === false) throw Error(ghostResponseText(data, 'lab.service.firmware_unavailable'));
    return data;
}

async function confirmFirmwarePurchase(appId) {
    const info = await firmwareRequest('/api/ghostlab/firmware/' + encodeURIComponent(appId));
    if (info.state.crash_id) { await syncFirmwareCrash(); return null; }
    if (info.pending) {
        const accepted = await showGhostDecisionDialog({titleKey:'lab.service.firmware_title',messageKey:'lab.service.restore_confirm',confirmKey:'lab.service.restore'});
        return accepted ? info.pending_offer : null;
    }
    if (!info.available) throw Error(window.GhostLocale.t('lab.service.withdrawn'));
    if (info.has_pending) throw Error(window.GhostLocale.t('lab.service.pending_first'));
    if (info.state.cooldown_until > info.server_time) throw Error(window.GhostLocale.t('lab.service.next', {date:new Date(info.state.cooldown_until * 1000).toLocaleString(window.GhostLocale.getLocale())}));
    if (!info.gains.disk_mb && !info.gains.scan_m) throw Error(window.GhostLocale.t('lab.service.limits'));
    const accepted = await showGhostDecisionDialog({titleKey:'lab.service.purchase_title',messageKey:'lab.service.purchase_summary',messageParams:{price:info.available.price,chance:info.policy.success_percent},detailsKey:'lab.service.firmware_risk',detailsParams:{disk:info.gains.disk_mb,scan:info.gains.scan_m},confirmKey:'lab.service.buy'});
    return accepted ? info.available : null;
}

const firmwareInertSiblings = new Map();
function removeFirmwareCrash(overlay) {
    overlay?.remove();
    document.body.classList.remove('firmware-crashed');
    firmwareInertSiblings.forEach((wasInert, element) => { element.inert = wasInert; });
    firmwareInertSiblings.clear();
}

async function syncFirmwareCrash() {
    if (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive) return;
    try {
        const state = await firmwareRequest('/api/firmware/state');
        if (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive) return;
        const old = document.getElementById('firmware-crash');
        if (!state.crash_id) {
            removeFirmwareCrash(old);
            return;
        }
        if (old?.dataset.crashId === state.crash_id) return;
        window.DeepScanner?.stop();
        old?.remove();
        const overlay = document.createElement('section');
        overlay.id = 'firmware-crash';
        overlay.dataset.crashId = state.crash_id;
        overlay.setAttribute('role', 'alertdialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-labelledby', 'firmware-crash-title');
        overlay.tabIndex = -1;
        overlay.innerHTML = `<div class="firmware-crash-panel"><div class="firmware-fault-code">GHOST SYSTEM // FLASH FAILURE</div>
            <h1 id="firmware-crash-title">${ghostLabel("lab.service.crash_title")}</h1><p>${ghostLabel("lab.service.crash_description")}</p>
            <pre>FLASH WRITE ........ FAILED\nSYSTEM HALTED\nRECOVERY IMAGE ..... READY</pre>
            <p>${ghostLabel("lab.service.crash_safe")}</p>
            <p data-recovery role="status">${ghostLabel("lab.service.restart_preparing")}</p><button type="button" disabled>${ghostLabel("lab.service.restart")}</button></div>`;
        document.body.appendChild(overlay);
        document.body.classList.add('firmware-crashed');
        [...document.body.children].filter(element => element !== overlay && !['SCRIPT', 'STYLE'].includes(element.tagName)).forEach(element => {
            if (!firmwareInertSiblings.has(element)) firmwareInertSiblings.set(element, element.inert);
            element.inert = true;
        });
        overlay.focus();
        const button = overlay.querySelector('button');
        const status = overlay.querySelector('[data-recovery]');
        const wait = Math.max(0, (state.restart_after - state.server_time) * 1000);
        setTimeout(() => { if (overlay.isConnected) { button.disabled = false; ghostSet(status, 'lab.service.restart_ready'); button.focus(); } }, wait);
        overlay.addEventListener('keydown', event => {
            if (event.key === 'Tab') { event.preventDefault(); button.focus(); }
            event.stopPropagation();
        });
        button.onclick = async () => {
            button.disabled = true;
            ghostSet(status, 'lab.service.restoring');
            try {
                await firmwareRequest('/api/firmware/restart', {crash_id: state.crash_id});
                location.reload();
            } catch (error) { delete status.dataset.ghostI18n; status.textContent = error.message; button.disabled = false; }
        };
    } catch (_error) { /* Preserve an existing crash overlay during a network outage. */ }
}

async function renderGhostLabFirmware(app, body, data, reload) {
    const product = data.product;
    const endpoint = '/api/ghostlab/firmware/' + encodeURIComponent(product.id);
    body.innerHTML = `<p>${ghostLabel("lab.service.firmware_check")}</p>`;
    try {
        const info = await firmwareRequest(endpoint);
        if (!app.isConnected || !body.isConnected) return;
        if (info.state.crash_id) { await syncFirmwareCrash(); return; }
        const ready = info.state.cooldown_until <= info.server_time;
        const gains = info.gains;
        const room = gains && (gains.disk_mb > 0 || gains.scan_m > 0);
        body.innerHTML = `<p>${ghostLabel('lab.runtime.versions', {installed:Number(product.installed_version), available:String(data.available_version ?? '—')})}</p>
            <p>${escapeHTML(product.description || '')}</p>
            <p>${ghostLabel("lab.service.firmware_help")}</p>
            ${info.policy ? `<div class="firmware-stats"><p>${ghostLabel("lab.service.chance", {chance:Number(info.policy.success_percent)})}</p>
            <p>${ghostLabel("lab.service.gains", {disk:Number(gains.disk_mb),scan:Number(gains.scan_m)})}</p>
            <p>${ghostLabel("lab.service.capacity", {disk:Number(gains.storage.capacity),scan:Number(gains.scan_range_m)})}</p></div>` : ''}
            <p>${ghostLabel(info.pending ? 'lab.service.paid' : 'lab.service.no_attempt')}</p>
            ${!ready ? `<p>${ghostLabel("lab.service.next", {date:new Date(info.state.cooldown_until * 1000).toLocaleString(window.GhostLocale.getLocale())})}</p>` : ''}
            ${!room ? `<p>${ghostLabel("lab.service.no_gains")}</p>` : ''}
            <div class="pro-tool-actions"><button data-flash ${!info.pending || !ready || !room || !product.runtime_enabled ? 'disabled' : ''}>${ghostLabel("lab.service.flash")}</button>
            <button data-buy ${info.has_pending || !info.available || !ready || !room ? 'disabled' : ''}>${ghostLabel("lab.service.buy_price", {price:Number(info.available?.price || 0)})}</button>
            <button data-refresh>${ghostLabel('lab.runtime.refresh')}</button>
            ${data.update_available ? `<button data-update>${ghostLabel("lab.service.update")}</button>` : ''}</div>
            <progress data-progress hidden max="100" value="0"></progress><pre data-log role="status" aria-live="polite"></pre>`;
        const log = body.querySelector('[data-log]');
        const progress = body.querySelector('[data-progress]');
        const resultText = result => window.GhostLocale.t(result.succeeded ? 'lab.service.firmware_success' : 'lab.service.firmware_failure') + (result.succeeded ? '\n' + window.GhostLocale.t('lab.service.gains_saved', {disk:Number(result.disk_mb),scan:Number(result.scan_m)}) : '');
        if (info.last_result) log.textContent = window.GhostLocale.t('lab.service.last_attempt') + resultText(info.last_result);
        body.querySelector('[data-refresh]').onclick = () => reload();
        body.querySelector('[data-update]')?.addEventListener('click', () => reload({method: 'POST',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify({expected_artifact_id: product.artifact_id, artifact_id: data.available_artifact_id})}));
        const operation = async (buy) => {
            const buttons = [...body.querySelectorAll('button')];
            const disabled = buttons.map(button => button.disabled);
            buttons.forEach(button => button.disabled = true);
            let committed = false;
            try {
                const confirmed = await showGhostDecisionDialog({titleKey:buy ? 'lab.service.purchase_title' : 'lab.service.flash_title',messageKey:buy ? 'lab.service.buy_confirm' : 'lab.service.flash_confirm',messageParams:buy ? {price:info.available.price} : {chance:info.policy.success_percent},detailsKey:'lab.service.firmware_risk',detailsParams:{disk:gains.disk_mb,scan:gains.scan_m},confirmKey:buy ? 'lab.service.buy' : 'lab.service.flash_action'});
                if (!confirmed || !app.isConnected) return;
                if (buy) {
                    const storageKey = 'firmware-purchase:' + product.id;
                    let key = sessionStorage.getItem(storageKey);
                    if (!key) { key = crypto.randomUUID(); sessionStorage.setItem(storageKey, key); }
                    const result = await firmwareRequest(endpoint + '/purchase', {client_action_key: key,
                        expected_artifact_id: info.available.artifact_id, expected_price: info.available.price});
                    sessionStorage.removeItem(storageKey);
                    committed = true;
                    if (typeof updateStorageView === 'function') updateStorageView(result.storage);
                    await reload();
                } else {
                    progress.hidden = false;
                    for (const [index, text] of ['paid_check','image_prepare','flashing'].entries()) {
                        if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) return;
                        progress.value = (index + 1) * 25;
                        ghostSet(log, 'lab.service.' + text);
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                    if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) return;
                    const result = await firmwareRequest(endpoint, {receipt: info.pending});
                    committed = true;
                    if (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive) return;
                    progress.value = 100;
                    delete log.dataset.ghostI18n; log.textContent = resultText(result);
                    if (typeof updateStorageView === 'function') updateStorageView(result.storage);
                    await syncFirmwareCrash();
                }
            } catch (error) { delete log.dataset.ghostI18n; log.textContent = error.message + '\n' + window.GhostLocale.t('lab.service.firmware_retry'); }
            finally {
                buttons.forEach((button, index) => button.disabled = disabled[index]);
                if (committed && !buy) { body.querySelector('[data-flash]').disabled = true; body.querySelector('[data-buy]').disabled = true; }
            }
        };
        body.querySelector('[data-buy]').onclick = () => operation(true);
        body.querySelector('[data-flash]').onclick = () => operation(false);
    } catch (error) { body.textContent = error.message; }
}

window.addEventListener('DOMContentLoaded', () => {
    syncFirmwareCrash();
    setInterval(() => { if (!document.hidden) syncFirmwareCrash(); }, 15000);
});
document.addEventListener('visibilitychange', () => { if (!document.hidden) syncFirmwareCrash(); });
