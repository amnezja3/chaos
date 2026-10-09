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

function ghostLabSecurityChangeLog(changes) {
    const value = item => item === true ? 'ON' : item === false ? 'OFF' : String(item);
    return changes.map(change => `${window.GhostLocale.hasKey('map.security.' + change.key) ? window.GhostLocale.t('map.security.' + change.key) : change.key}: ${value(change.before)} → ${value(change.after)}`).join('\n');
}

async function renderGhostLabMaintenance(app, body, data, reload) {
    const product = data.product;
    const endpoint = '/api/ghostlab/installed/' + encodeURIComponent(product.id) + '/maintenance';
    body.innerHTML = `<p>${ghostLabel('lab.runtime.versions', {installed:Number(product.installed_version), available:String(data.available_version ?? '—')})}</p>
        <p>${product.runtime_enabled ? escapeHTML(product.description) : ghostLabel('lab.ui.runtime_unavailable')}</p>
        <div data-maintenance-preview></div><div class="pro-tool-actions">
        <button data-maintenance-run disabled>${ghostLabel("lab.service.run")}</button><button data-maintenance-refresh>${ghostLabel("lab.service.refresh")}</button>
        ${data.update_available ? `<button data-maintenance-update>${ghostLabel('lab.runtime.update', {version:Number(data.available_version)})}</button>` : ''}</div>
        <progress data-maintenance-progress max="100" value="0" hidden style="width:100%;accent-color:#aaff00"></progress>
        <div data-maintenance-log role="status" aria-live="polite" style="white-space:pre-wrap;overflow-wrap:anywhere"></div>`;
    const view = body.querySelector('[data-maintenance-preview]');
    const log = body.querySelector('[data-maintenance-log]');
    const run = body.querySelector('[data-maintenance-run]');
    body.querySelector('[data-maintenance-refresh]').onclick = () => reload();
    body.querySelector('[data-maintenance-update]')?.addEventListener('click', event => {
        event.currentTarget.disabled = true;
        reload({method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
            expected_artifact_id: product.artifact_id, artifact_id: data.available_artifact_id
        })});
    });
    if (!product.runtime_enabled) return;
    let plan;
    try {
        const selection = product.template_id === 'security_restore' && app._ghostLabSecurityPreset
            ? '?preset=' + encodeURIComponent(app._ghostLabSecurityPreset) : '';
        const response = await fetch(endpoint + selection, {cache: 'no-store'});
        plan = await response.json();
        if (!response.ok || !plan.success) throw Error(ghostResponseText(plan, 'lab.service.preview_error'));
    } catch (error) { log.textContent = error.message; return; }
    if (!app.isConnected || !view.isConnected) return;
    const preview = plan.preview;
    if (preview.kind === 'file_cleanup') {
        view.innerHTML = `<p>${ghostLabel("lab.service.cleanup_count", {count:Number(preview.count), size:Number(preview.size)})}</p>
            <details><summary>${ghostLabel("lab.service.cleanup_scope")}</summary><ul>${preview.files.map(f => `<li>${escapeHTML(f.name)} — ${Number(f.size)} MB</li>`).join('')}</ul></details>`;
        ghostSet(run, preview.count ? 'lab.service.cleanup_run' : 'lab.service.clean');
    } else if (preview.kind === 'security_restore') {
        app._ghostLabSecurityPreset = preview.preset;
        view.innerHTML = `<p>${ghostLabel("lab.service.security_choose")}</p><div class="pro-tool-actions ghostlab-security-presets" role="group" data-ghost-aria-label="lab.service.security_level" aria-label="${escapeHTML(window.GhostLocale.t('lab.service.security_level'))}">
            ${(preview.presets || ['open', 'low', 'regular', 'all']).map(preset => `<button type="button" data-maintenance-preset="${escapeHTML(preset)}" aria-pressed="${preset === preview.preset}">${ghostSystemValue('map.preset.', preset)}</button>`).join('')}</div>
            <p>${ghostLabel("lab.service.preset")}: <b>${ghostSystemValue('map.preset.', preview.preset)}</b></p><pre data-maintenance-changes style="white-space:pre-wrap;overflow-wrap:anywhere"></pre>`;
        view.querySelector('[data-maintenance-changes]').textContent = preview.changes?.length
            ? window.GhostLocale.t('lab.service.planned') + '\n' + ghostLabSecurityChangeLog(preview.changes) : window.GhostLocale.t('lab.service.security_ready');
        view.querySelectorAll('[data-maintenance-preset]').forEach(button => {
            button.onclick = () => {
                app._ghostLabSecurityPreset = button.dataset.maintenancePreset;
                return renderGhostLabMaintenance(app, body, data, reload);
            };
        });
        ghostSet(run, 'lab.service.security_run');
    } else {
        ghostSet(view, preview.installed ? 'lab.service.current_help' : 'lab.service.update_help');
        ghostSet(run, preview.installed ? 'lab.service.current' : 'lab.service.update_run');
    }
    run.disabled = preview.can_execute === false;
    if (preview.message) ghostSet(log, preview.kind === 'file_cleanup' ? 'lab.service.clean' : preview.kind === 'security_restore' ? 'lab.service.security_ready' : 'lab.service.current_help');
    run.onclick = async () => {
        if (preview.can_execute === false) return;
        const buttons = Array.from(body.querySelectorAll('button'));
        buttons.forEach(b => b.disabled = true);
        let committed = false;
        const progress = body.querySelector('[data-maintenance-progress]');
        try {
            if (preview.kind !== 'system_update' && (preview.kind !== 'file_cleanup' || preview.count)) {
                const accepted = await showGhostDecisionDialog({titleKey:'lab.service.title', messageKey:preview.kind === 'file_cleanup' ? 'lab.service.cleanup_confirm' : 'lab.service.security_confirm', messageParams:preview.kind === 'file_cleanup' ? {count:Number(preview.count),size:Number(preview.size)} : {preset:window.GhostLocale.t('map.preset.'+preview.preset)}, detailsKey:'lab.service.confirm_details', confirmKey:'lab.service.confirm'});
                if (!accepted) return;
            }
            progress.hidden = false;
            delete log.dataset.ghostI18n; log.textContent = '';
            const stages = preview.logs || [window.GhostLocale.t('lab.service.checking'), window.GhostLocale.t('lab.service.preparing')];
            for (let i = 0; i < stages.length; i++) {
                if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) return;
                log.textContent += stages[i] + '\n';
                progress.value = Math.round((i + 1) / stages.length * 85);
                await new Promise(resolve => setTimeout(resolve, 600));
            }
            if (!app.isConnected || (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive)) return;
            const response = await fetch(endpoint, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({token: plan.token})});
            const result = await response.json();
            if (!response.ok || !result.success) throw Error(ghostResponseText(result, 'lab.service.failed'));
            committed = true;
            if (typeof desktopSessionActive !== 'undefined' && !desktopSessionActive) return;
            if (!result.duplicate && !result.already_installed) applyGhostLabMaintenanceResult(result);
            progress.value = 100;
            log.textContent += (result.duplicate ? window.GhostLocale.t('lab.service.duplicate') : '') + ghostResponseText(result, 'lab.service.failed') + '\n' + window.GhostLocale.t('lab.service.refresh_next');
            if (Array.isArray(result.changes) && result.changes.length) {
                log.textContent += '\n' + window.GhostLocale.t('lab.service.saved') + '\n' + ghostLabSecurityChangeLog(result.changes);
            }
            if (preview.kind === 'system_update') {
                ghostSet(view, 'lab.service.current_help');
                ghostSet(run, 'lab.service.current');
            } else if (preview.kind === 'security_restore') {
                ghostSet(view.querySelector('[data-maintenance-changes]'), 'lab.service.security_ready');
            }
        } catch (error) {
            log.textContent = error.message + '\n' + window.GhostLocale.t('lab.service.retry');
        } finally {
            buttons.forEach(b => b.disabled = false);
            run.disabled = committed;
        }
    };
}
