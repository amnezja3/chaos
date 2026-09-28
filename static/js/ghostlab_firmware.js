/* The server owns the roll, crash, cooldown and durable receipt. */
async function firmwareRequest(url, body) {
    const response = await fetch(url, body === undefined ? {cache: 'no-store'} : {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok || data.success === false) throw Error(data.message || data.error || 'Firmware niedostępny.');
    return data;
}

async function confirmFirmwarePurchase(appId) {
    const info = await firmwareRequest('/api/ghostlab/firmware/' + encodeURIComponent(appId));
    if (info.state.crash_id) { await syncFirmwareCrash(); return null; }
    if (info.pending) {
        const accepted = await showGhostDecisionDialog({title: 'FIRMWARE', message: 'Masz już opłaconą próbę. Przywrócić jej aplikację bez ponownej opłaty?', confirmLabel: 'PRZYWRÓĆ'});
        return accepted ? info.pending_offer : null;
    }
    if (!info.available) throw Error('Firmware wycofano ze sprzedaży.');
    if (info.has_pending) throw Error('Wykorzystaj wcześniej zakupioną próbę firmware.');
    if (info.state.cooldown_until > info.server_time) throw Error('Kolejny zakup możliwy: ' + new Date(info.state.cooldown_until * 1000).toLocaleString());
    if (!info.gains.disk_mb && !info.gains.scan_m) throw Error('Osiągnięto limity: 2 TB dysku i 30 km skanu.');
    const accepted = await showGhostDecisionDialog({title: 'ZAKUP PRÓBY FIRMWARE',
        message: `Jedna próba za ${info.available.price} HC. Szansa powodzenia: ${info.policy.success_percent}%.`,
        details: `Możliwy przyrost: ${info.gains.disk_mb} MB i ${info.gains.scan_m} m. Porażka: crash i restart, bez zwrotu HC. Cooldown po obu wynikach: 24 h.`, confirmLabel: 'KUP PRÓBĘ'});
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
            <h1 id="firmware-crash-title">Awaria systemu</h1><p>Flashowanie firmware’u nie powiodło się. Pulpit został zatrzymany.</p>
            <pre>FLASH WRITE ........ FAILED\nSYSTEM HALTED\nRECOVERY IMAGE ..... READY</pre>
            <p>Pliki i wcześniejsze ulepszenia są bezpieczne. Próba została zużyta; kolejny zakup będzie możliwy po 24 godzinach od próby.</p>
            <p data-recovery role="status">Przygotowanie restartu…</p><button type="button" disabled>Uruchom ponownie system</button></div>`;
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
        setTimeout(() => { if (overlay.isConnected) { button.disabled = false; status.textContent = 'System gotowy do restartu.'; button.focus(); } }, wait);
        overlay.addEventListener('keydown', event => {
            if (event.key === 'Tab') { event.preventDefault(); button.focus(); }
            event.stopPropagation();
        });
        button.onclick = async () => {
            button.disabled = true;
            status.textContent = 'Przywracanie systemu…';
            try {
                await firmwareRequest('/api/firmware/restart', {crash_id: state.crash_id});
                location.reload();
            } catch (error) { status.textContent = error.message; button.disabled = false; }
        };
    } catch (_error) { /* Preserve an existing crash overlay during a network outage. */ }
}

async function renderGhostLabFirmware(app, body, data, reload) {
    const product = data.product;
    const endpoint = '/api/ghostlab/firmware/' + encodeURIComponent(product.id);
    body.innerHTML = '<p>Sprawdzanie firmware’u…</p>';
    try {
        const info = await firmwareRequest(endpoint);
        if (!app.isConnected || !body.isConnected) return;
        if (info.state.crash_id) { await syncFirmwareCrash(); return; }
        const ready = info.state.cooldown_until <= info.server_time;
        const gains = info.gains;
        const room = gains && (gains.disk_mb > 0 || gains.scan_m > 0);
        body.innerHTML = `<p>Zainstalowana wersja: ${Number(product.installed_version)}. Opublikowana: ${data.available_version == null ? '—' : Number(data.available_version)}.</p>
            <p>${escapeHTML(product.description || '')}</p>
            <p>Jedna zakupiona próba. Sukces daje trwałe ulepszenia; porażka powoduje crash i wymaga restartu. Cooldown po obu wynikach: 24 h.</p>
            ${info.policy ? `<div class="firmware-stats"><p>Szansa powodzenia: <b>${Number(info.policy.success_percent)}%</b></p>
            <p>Możliwy przyrost: <b>+${Number(gains.disk_mb)} MB</b> dysku i <b>+${Number(gains.scan_m)} m</b> zasięgu skanu.</p>
            <p>Obecnie: ${Number(gains.storage.capacity)} MB / 2 TB; ${Number(gains.scan_range_m)} m / 30 km.</p></div>` : ''}
            <p>${info.pending ? 'Próba opłacona. Obowiązują parametry wersji zakupionej — aktualizacja aplikacji ich nie zmienia.' : 'Brak niewykorzystanej próby.'}</p>
            ${!ready ? `<p>Kolejna próba: ${escapeHTML(new Date(info.state.cooldown_until * 1000).toLocaleString())}</p>` : ''}
            ${!room ? '<p>Brak dostępnych przyrostów lub oferty.</p>' : ''}
            <div class="pro-tool-actions"><button data-flash ${!info.pending || !ready || !room || !product.runtime_enabled ? 'disabled' : ''}>Flashuj firmware</button>
            <button data-buy ${info.has_pending || !info.available || !ready || !room ? 'disabled' : ''}>Kup próbę — ${Number(info.available?.price || 0)} HC</button>
            <button data-refresh>Odśwież</button>
            ${data.update_available ? '<button data-update>Aktualizuj aplikację bezpłatnie</button>' : ''}</div>
            <progress data-progress hidden max="100" value="0"></progress><pre data-log role="status" aria-live="polite"></pre>`;
        const log = body.querySelector('[data-log]');
        const progress = body.querySelector('[data-progress]');
        const resultText = result => result.message + (result.succeeded ? `\nZapisano: +${result.disk_mb} MB, +${result.scan_m} m.` : '');
        if (info.last_result) log.textContent = 'Ostatnia próba: ' + resultText(info.last_result);
        body.querySelector('[data-refresh]').onclick = () => reload();
        body.querySelector('[data-update]')?.addEventListener('click', () => reload({method: 'POST',
            headers: {'Content-Type': 'application/json'}, body: JSON.stringify({expected_artifact_id: product.artifact_id, artifact_id: data.available_artifact_id})}));
        const operation = async (buy) => {
            const buttons = [...body.querySelectorAll('button')];
            const disabled = buttons.map(button => button.disabled);
            buttons.forEach(button => button.disabled = true);
            let committed = false;
            try {
                const confirmed = await showGhostDecisionDialog({title: buy ? 'ZAKUP PRÓBY FIRMWARE' : 'FLASHOWANIE FIRMWARE',
                    message: buy ? `Kupić jedną próbę za ${info.available.price} HC?` : `Rozpocząć próbę z szansą ${info.policy.success_percent}%?`,
                    details: `Możliwy przyrost: ${gains.disk_mb} MB i ${gains.scan_m} m. Porażka: crash i restart, bez zwrotu HC. Cooldown po obu wynikach: 24 h.`,
                    confirmLabel: buy ? 'KUP PRÓBĘ' : 'FLASHUJ'});
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
                    for (const [index, text] of ['Sprawdzanie opłaconej próby…', 'Przygotowanie obrazu firmware…', 'Zapisywanie firmware…'].entries()) {
                        if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) return;
                        progress.value = (index + 1) * 25;
                        log.textContent = text;
                        await new Promise(resolve => setTimeout(resolve, 500));
                    }
                    if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) return;
                    const result = await firmwareRequest(endpoint, {receipt: info.pending});
                    committed = true;
                    if (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive) return;
                    progress.value = 100;
                    log.textContent = resultText(result);
                    if (typeof updateStorageView === 'function') updateStorageView(result.storage);
                    await syncFirmwareCrash();
                }
            } catch (error) { log.textContent = error.message + '\nOdśwież stan lub ponów żądanie — wynik próby jest zapamiętywany.'; }
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
