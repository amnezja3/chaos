/* Own-system GhostLab UI. Author logs are text, never executable markup. */
function applyGhostLabMaintenanceResult(result) {
    if (result.storage) updateStorageView(result.storage);
    if (Array.isArray(result.removed_file_ids)) {
        const removed = new Set(result.removed_file_ids);
        const removeFrom = files => Object.fromEntries(Object.entries(files || {}).map(([folder, entries]) =>
            [folder, folder !== 'tools' && Array.isArray(entries) ? entries.filter(f => !removed.has(f?.id || f?.file_id)) : entries]));
        if (typeof toolbarProfile !== 'undefined') setToolbarProfile({...toolbarProfile, files: removeFrom(toolbarProfile?.files)});
        fileManagerInstances.forEach((state, terminalId) => {
            state.files = removeFrom(state.files);
            if (document.getElementById(`${terminalId}-content`) && state.currentFolder && typeof window.openFolderInManager === 'function') {
                window.openFolderInManager(terminalId, state.currentFolder);
            }
        });
    }
    if (result.security) {
        document.querySelectorAll('.profile-security-toggle').forEach(toggle => {
            if (typeof result.security[toggle.dataset.securityKey] !== 'boolean') return;
            toggle.checked = result.security[toggle.dataset.securityKey];
            const tile = toggle.closest('.profile-security-tile');
            tile?.classList.toggle('is-on', toggle.checked);
            tile?.classList.toggle('is-off', !toggle.checked);
            const label = tile?.querySelector('.profile-security-state');
            if (label) label.textContent = toggle.checked ? 'ON' : 'OFF';
        });
        if (typeof toolbarProfile !== 'undefined') setToolbarProfile({...toolbarProfile, security: result.security});
    }
}

async function renderGhostLabMaintenance(app, body, data, reload) {
    const product = data.product;
    const endpoint = '/api/ghostlab/installed/' + encodeURIComponent(product.id) + '/maintenance';
    body.innerHTML = `<p>Zainstalowana wersja: ${Number(product.installed_version)}. Opublikowana: ${data.available_version == null ? '—' : Number(data.available_version)}.</p>
        <p>${escapeHTML(product.runtime_enabled ? product.description : product.disabled_reason)}</p>
        <div data-maintenance-preview></div><div class="pro-tool-actions">
        <button data-maintenance-run disabled>Uruchom</button><button data-maintenance-refresh>Odśwież podgląd</button>
        ${data.update_available ? `<button data-maintenance-update>Aktualizuj aplikację bezpłatnie do v${Number(data.available_version)}</button>` : ''}</div>
        <progress data-maintenance-progress max="100" value="0" hidden style="width:100%;accent-color:#aaff00"></progress>
        <div data-maintenance-log role="status" aria-live="polite" style="white-space:pre-wrap;overflow-wrap:anywhere"></div>`;
    const view = body.querySelector('[data-maintenance-preview]');
    const log = body.querySelector('[data-maintenance-log]');
    const run = body.querySelector('[data-maintenance-run]');
    body.querySelector('[data-maintenance-refresh]').onclick = () => reload();
    body.querySelector('[data-maintenance-update]')?.addEventListener('click', event => {
        event.target.disabled = true;
        reload({method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
            expected_artifact_id: product.artifact_id, artifact_id: data.available_artifact_id
        })});
    });
    if (!product.runtime_enabled) return;
    let plan;
    try {
        const response = await fetch(endpoint, {cache: 'no-store'});
        plan = await response.json();
        if (!response.ok || !plan.success) throw Error(plan.error || 'Brak podglądu.');
    } catch (error) { log.textContent = error.message; return; }
    if (!app.isConnected || !view.isConnected) return;
    const preview = plan.preview;
    if (preview.kind === 'file_cleanup') {
        view.innerHTML = `<p>Do usunięcia: ${Number(preview.count)} plików, ${Number(preview.size)} MB (maks. 250 na operację).</p>
            <details><summary>Zakres czyszczenia</summary><ul>${preview.files.map(f => `<li>${escapeHTML(f.name)} — ${Number(f.size)} MB</li>`).join('')}</ul></details>`;
        run.textContent = preview.count ? 'Wyczyść pliki' : 'Sprawdź system';
    } else if (preview.kind === 'security_restore') {
        view.textContent = 'Zestaw: ' + preview.preset.toUpperCase() + '. Jednorazowa zmiana własnych zabezpieczeń.';
        run.textContent = 'Przywróć zabezpieczenia';
    } else {
        view.textContent = 'Prezentacja pobierania i instalowania aktualizacji. Bez bonusów do parametrów.';
        run.textContent = 'Rozpocznij aktualizację systemu';
    }
    run.disabled = false;
    run.onclick = async () => {
        const buttons = Array.from(body.querySelectorAll('button'));
        buttons.forEach(b => b.disabled = true);
        let committed = false;
        const progress = body.querySelector('[data-maintenance-progress]');
        try {
            if (preview.kind !== 'system_update' && (preview.kind !== 'file_cleanup' || preview.count)) {
                const accepted = await showGhostDecisionDialog({title: 'KONSERWACJA SYSTEMU',
                    message: preview.kind === 'file_cleanup' ? `Usunąć ${preview.count} plików (${preview.size} MB)?` : `Ustawić zabezpieczenia ${preview.preset.toUpperCase()}?`,
                    details: 'Operacja dotyczy Twojego konta. Serwer ponownie sprawdzi aktualny stan.', confirmLabel: 'WYKONAJ'});
                if (!accepted) return;
            }
            progress.hidden = false;
            log.textContent = '';
            const stages = preview.logs || ['Sprawdzanie zakresu…', 'Przygotowanie operacji…'];
            for (let i = 0; i < stages.length; i++) {
                if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) return;
                log.textContent += stages[i] + '\n';
                progress.value = Math.round((i + 1) / stages.length * 85);
                await new Promise(resolve => setTimeout(resolve, 600));
            }
            if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) return;
            const response = await fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token: plan.token})});
            const result = await response.json();
            if (!response.ok || !result.success) throw Error(result.error || 'Operacja nie powiodła się.');
            committed = true;
            if (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive) return;
            if (!result.duplicate) applyGhostLabMaintenanceResult(result);
            progress.value = 100;
            log.textContent += (result.duplicate ? 'Zapisany wynik poprzedniego żądania: ' : '') + result.message + '\nOdśwież podgląd przed kolejnym uruchomieniem.';
            if (Array.isArray(result.changed) && result.changed.length) {
                log.textContent += '\n' + result.changed.map(key => `${key}: ${result.security[key] === true ? 'ON' : result.security[key] === false ? 'OFF' : result.security[key]}`).join('\n');
            }
        } catch (error) {
            log.textContent = error.message + '\nMożesz ponowić to samo żądanie lub odświeżyć podgląd.';
        } finally {
            buttons.forEach(b => b.disabled = false);
            run.disabled = committed;
        }
    };
}
