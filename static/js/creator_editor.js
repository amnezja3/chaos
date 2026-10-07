/* Creator projects: system-owned mechanics, editable presentation. */
window.CreatorEditor = (() => {
    const actionIcons = {exploit: '💥', scan_ports: '🛠️', trace: '📍', trace_gps: '📍', trace_device: '📡', scan_hotspots: '📶', camera_stream: '🎥', camera_shutdown: '❌', install_sniffer: '🐛', sniff: '📡', mic_sniff: '🎙️', atm_logs: '📊', audio_hack: '🔊', car_hack: '🚗'};
    const names = {terminal: 'TermCreator', window: 'WindowMaker', button_choices: 'ButtonMaker', progressbar_random: 'AppForge'};
    const objectGroups = {"exploit":"general","scan_ports":"general","trace":"general","sniff":"general","trace_gps":"cars","car_hack":"cars","trace_device":"people","mic_sniff":"people","scan_hotspots":"audio","audio_hack":"audio","camera_stream":"cameras","camera_shutdown":"cameras","atm_logs":"atms","install_sniffer":"atms"};
    function localized(tag, key, parent, params = {}) {
        const el = node(tag, undefined, parent);
        ghostSet(el, key, params);
        return el;
    }
    function errorKey(error) {
        const key = 'creator.error.' + error.reason;
        return GhostLocale.hasKey(key) ? key : error.localeKey;
    }
    function showError(target, error) {
        if (error.envelope) {
            delete target.dataset.ghostI18n;
            delete target.dataset.ghostParams;
            target.replaceChildren();
            const envelope = error.envelope;
            if (Number.isInteger(envelope.option_index)) {
                localized('span', 'creator.validation.option', target, {index: envelope.option_index});
                node('span', ' ', target);
            }
            localized('span', envelope.key, target, envelope.params);
            return;
        }
        const key = errorKey(error);
        if (key) ghostSet(target, key);
        else {
            // Legacy validation details stay literal until they have typed codes.
            delete target.dataset.ghostI18n;
            delete target.dataset.ghostParams;
            target.textContent = error.message || GhostLocale.t('creator.editor.error');
        }
    }
    async function api(path, method = 'GET', body) {
        const response = await fetch('/api/creators/' + path, {method, cache: 'no-store', headers: {'Content-Type': 'application/json'}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
        const data = await response.json();
        if (!response.ok || !data.success) {
            const error = new Error(data.message || GhostLocale.t('creator.editor.error'));
            error.status = response.status;
            error.reason = data.reason;
            if (data.message_i18n?.content_version === GhostLocale.contentVersion
                && GhostLocale.hasKey(data.message_i18n.key)) error.envelope = data.message_i18n;
            if (!data.message) error.localeKey = 'creator.editor.error';
            throw error;
        }
        return data;
    }
    function node(tag, text, parent) {
        const el = document.createElement(tag);
        if (text !== undefined) el.textContent = text;
        if (parent) parent.appendChild(el);
        return el;
    }
    async function open(kind, projectId) {
        const policy = await api('policy');
        if (!policy.enabled) return false;
        if (!policy.installed_interfaces.includes(kind)) {
            const error = new Error(GhostLocale.t('creator.editor.not_installed'));
            error.localeKey = 'creator.editor.not_installed';
            throw error;
        }
        const existing = document.querySelector(`.creator-window[data-app="${names[kind].toLowerCase()}"]`);
        if (existing) {
            bringWindowToFront(existing);
            if (projectId) existing.dispatchEvent(new CustomEvent('creator:open', {detail: projectId}));
            return true;
        }
        const term = creatorBaseWindow(names[kind], kind);
        term.classList.add('creator-v2');
        const form = term.querySelector('form');
        let project = null, dirty = false, busy = false;
        const close = term.querySelector('.close-btn');
        const discard = () => showGhostDecisionDialog({titleKey: 'creator.editor.title', messageKey: 'creator.editor.discard_question', confirmKey: 'creator.editor.discard', cancelKey: 'creator.editor.back'});
        close.addEventListener('click', async event => {
            if (!busy && !dirty) return;
            event.stopImmediatePropagation();
            if (!busy && await discard()) term.remove();
        }, true);
        form.addEventListener('input', () => { dirty = true; });
        form.addEventListener('submit', event => event.preventDefault());
        let status;
        function reset(title) {
            form.replaceChildren();
            const hero = node('header', undefined, form); hero.className = 'creator-v2-hero';
            node('span', '▣', hero).className = 'creator-v2-emblem';
            const heading = node('div', undefined, hero);
            localized('h3', title, heading);
            node('p', names[kind] + ' / CHAOS TOOLBUILDER', heading);
            status = node('p', '', form); status.setAttribute('role', 'status');
        }
        async function action(work) {
            if (busy) return;
            busy = true;
            term.setAttribute('aria-busy', 'true');
            const controls = [...form.querySelectorAll('input,textarea,select,button')];
            const enabled = controls.filter(el => !el.disabled);
            enabled.forEach(el => { el.disabled = true; });
            try { await work(); } catch (error) { showError(status, error); }
            finally { busy = false; term.removeAttribute('aria-busy'); enabled.forEach(el => { el.disabled = el.dataset.unavailable === 'true'; }); }
        }
        function button(text, work, parent = form, system = true) {
            const el = node('button', text, parent); el.type = 'button';
            if (system && text.startsWith('creator.editor.')) ghostSet(el, text);
            el.addEventListener('click', () => action(work)); return el;
        }
        function field(text, value = '', multiline = false, parent = form) {
            const label = node('label', undefined, parent);
            localized('span', text, label);
            const input = node(multiline ? 'textarea' : 'input', undefined, label);
            input.value = value; input.maxLength = multiline ? 6000 : 120;
            if (multiline) input.rows = 4;
            return input;
        }
        function iconField(value) {
            localized('p', 'creator.editor.icon', form);
            const group = node('div', undefined, form);
            group.className = 'appforge-icon-row';
            const input = field('creator.editor.icon', value, false, group);
            input.name = 'icon'; input.maxLength = 16;
            node('span', value, group).className = 'appforge-icon-preview';
            setupIconPicker(form, value);
            input.addEventListener('input', () => {
                input.value = creatorIconGraphemes(input.value).slice(0, 1).join('');
                group.querySelector('.appforge-icon-preview').textContent = validateCreatorIcon(input, value);
            });
            return input;
        }
        function lines(input) { return input.value.split('\n').map(s => s.trim()).filter(Boolean); }
        async function home() {
            reset('creator.editor.new'); dirty = false;
            const name = field('creator.editor.name', ''); name.maxLength = 80;
            const icon = iconField('🛠️');
            localized('p', 'creator.purpose.purpose', form);
            const choices = node('div', undefined, form); choices.className = 'creator-v2-choices';
            let selected = Object.keys(policy.recipes)[0], createsFile = false;
            const actionButtons = Object.keys(policy.recipes).map(key => {
                const el = button('', () => { selected = key; dirty = true; refresh(); }, choices);
                node('span', actionIcons[key] || '◇', el).className = 'creator-action-icon';
                const caption = node('span', undefined, el); caption.className = 'creator-action-caption';
                localized('span', 'map.action_name.' + key, caption).className = 'creator-action-label';
                localized('small', 'creator.objects.' + objectGroups[key], caption).className = 'creator-action-objects';
                node('span', '›', el).className = 'creator-action-arrow';
                el.dataset.action = key; return el;
            });
            const selection = node('p', '', form);
            selection.className = 'creator-action-selection';
            selection.setAttribute('aria-live', 'polite');
            const file = button('', () => { createsFile = !createsFile; dirty = true; refresh(); });
            file.className = 'creator-v2-file-toggle';
            const fileNote = node('p', '', form);
            fileNote.className = 'creator-v2-file-note';
            function refresh() {
                actionButtons.forEach(el => el.setAttribute('aria-pressed', String(el.dataset.action === selected)));
                selection.replaceChildren();
                localized('span', 'map.action.' + selected, selection);
                node('span', ' · ', selection);
                localized('span', 'creator.purpose.menu', selection);
                node('span', ' ', selection);
                localized('span', 'creator.objects.' + objectGroups[selected], selection);
                const resources = policy.recipes[selected].resource_types;
                const required = policy.recipes[selected].requires_file === true;
                file.disabled = required || !resources.length;
                file.dataset.unavailable = String(file.disabled);
                if (required) createsFile = true;
                else if (!resources.length) createsFile = false;
                file.setAttribute('aria-pressed', String(createsFile));
                ghostSet(file, 'creator.purpose.' + (createsFile ? 'file_yes' : 'file_no'));
                ghostSet(fileNote, 'creator.purpose.' + (required ? 'file_required' : createsFile ? 'file_optional' : 'file_none'));
            }
            refresh();
            // Retain the request identity and payload after a lost response: no second roll.
            let pending;
            button('creator.editor.generate', async () => {
                pending ||= {name: name.value, icon: icon.value, action: selected, creates_file: createsFile, interface: kind, request_id: crypto.randomUUID()};
                try { project = (await api('projects', 'POST', pending)).project; }
                catch (error) { if (error.status >= 400 && error.status < 500) pending = undefined; throw error; }
                dirty = false; edit();
            }).classList.add('creator-v2-generate');
            localized('h4', 'creator.editor.projects', form);
            const list = node('div', '', form);
            list.className = 'creator-v2-projects';
            async function page(after = '') {
                const data = await api('projects' + (after ? '?after=' + encodeURIComponent(after) : ''));
                data.projects.filter(p => p.interface === kind).forEach(p => button(`${p.icon} ${p.name} · v${p.version}`, async () => {
                    if (dirty && !await discard()) return;
                    project = (await api('projects/' + encodeURIComponent(p.id))).project; dirty = false; edit();
                }, list, false));
                if (data.next_cursor) { const more = button('creator.editor.more', async () => { more.remove(); await page(data.next_cursor); }, list); }
            }
            await page();
        }
        function edit() {
            let saved = project.version > 0;
            reset('creator.editor.edit');
            const c = project.contract, p = project.presentation;
            localized('p', 'creator.editor.' + (c.legacy ? 'legacy' : 'power'), form, c.legacy ? {version: project.version} : {power: c.power, cap: c.power_cap, version: project.version});
            if (!c.legacy) localized('p', 'map.action.' + c.action, form);
            if (!c.legacy) {
                const fileSummary = localized('p', 'creator.purpose.' + (c.creates_file ? 'file_yes' : 'file_no'), form);
                fileSummary.className = 'creator-file-summary';
                fileSummary.dataset.createsFile = String(c.creates_file);
            }
            const name = field('creator.editor.name', p.name); name.maxLength = 80;
            const icon = iconField(p.icon);
            const title = field('creator.editor.interface_title', p.title || p.name);
            const description = field('creator.editor.description', p.description || '', true);
            const price = field('creator.editor.price', c.price); price.type = 'number'; price.min = '0'; price.step = '1'; price.disabled = !!project.version;
            const rows = [];
            let prompt, logs, buttons, steps, success, failure;
            const list = node('div', '', form);
            if (kind === 'terminal') {
                const add = (command = {command: '', logs: []}) => {
                    const group = node('fieldset', undefined, list);
                    rows.push({command: field('creator.editor.command', command.command, false, group), logs: field('creator.editor.outputs', command.logs.join('\n'), true, group)});
                };
                (p.commands || [{command: 'run', logs: [GhostLocale.t('creator.editor.default_start')]}]).forEach(add);
                if (!c.legacy) button('creator.editor.add_command', () => { if (rows.length < 32) { add(); dirty = true; } }, list);
            } else if (kind === 'window') {
                logs = field('creator.editor.logs', (p.logs || []).join('\n'), true);
                buttons = field('creator.editor.buttons', (p.button_labels || [GhostLocale.t('creator.editor.default_run')]).join('\n'), true);
            } else if (kind === 'button_choices') {
                prompt = field('creator.editor.prompt', p.prompt || '', true);
                localized('p', 'creator.editor.' + (c.legacy ? 'legacy_effect' : policy.effect_enabled ? 'effect_enabled' : 'effect_disabled'), form, c.legacy ? {} : {level: policy.effect_min_level});
                const add = (label = GhostLocale.t('creator.editor.default_execute'), option = {}) => {
                    const group = node('fieldset', undefined, list);
                    const effectText = Object.entries(option.effect || {}).map(([key, value]) => `${key}=${value}`).join(',');
                    const row = {label: field('creator.editor.option', label, false, group), effect: field('creator.editor.effect', effectText, false, group), price: field('creator.editor.use_price', option.price || 0, false, group)};
                    row.effect.placeholder = 'risk_level=10,firewall=false';
                    row.effect.maxLength = 6000; row.price.type = 'number'; row.price.min = '0'; row.price.step = '1';
                    row.effect.disabled = row.price.disabled = !!project.version; rows.push(row);
                };
                (p.option_labels || [GhostLocale.t('creator.editor.default_execute')]).forEach((label, index) => add(label, (c.options || [])[index]));
                if (!project.version) button('creator.editor.add_option', () => { if (rows.length < 32) { add(); dirty = true; } }, list);
            } else {
                steps = field('creator.editor.steps', (p.steps || [GhostLocale.t('creator.editor.default_start')]).join('\n'), true);
                success = field('creator.editor.success', p.result_success || GhostLocale.t('creator.editor.default_success'));
                failure = field('creator.editor.failure', p.result_failure || GhostLocale.t('creator.editor.default_failure'));
            }
            function presentation() {
                const value = {name: name.value, icon: icon.value, title: title.value, description: description.value};
                if (kind === 'terminal') value.commands = rows.map(row => ({command: row.command.value, logs: lines(row.logs)}));
                if (kind === 'window') Object.assign(value, {logs: lines(logs), button_labels: lines(buttons)});
                if (kind === 'button_choices') Object.assign(value, {prompt: prompt.value, option_labels: rows.map(row => row.label.value)});
                if (kind === 'progressbar_random') Object.assign(value, {steps: lines(steps), result_success: success.value, result_failure: failure.value});
                return value;
            }
            async function save() {
                if (saved && !dirty) return;
                const base = 'projects/' + encodeURIComponent(project.id);
                if (!project.version) {
                    const configuration = {price: price.value === '' ? null : Number(price.value)};
                    if (kind === 'button_choices') configuration.options = rows.map(row => {
                        const effect = row.effect.value.trim();
                        return {price: Number(row.price.value || 0), effect};
                    });
                    project = (await api(base + '/configuration', 'PATCH', {revision: project.revision, configuration})).project;
                }
                project = (await api(base, 'PATCH', {revision: project.revision, presentation: presentation()})).project;
                dirty = false;
                saved = true;
            }
            button('creator.editor.save', async () => { await save(); ghostSet(status, 'creator.editor.saved'); });
            button('creator.editor.publish', async () => {
                await save();
                const data = await api('projects/' + encodeURIComponent(project.id) + '/publish', 'POST', {revision: project.revision});
                project.version = data.app.version; edit(); ghostSet(status, 'creator.editor.published', {version: project.version});
            });
            const preview = node('pre', '', form); preview.className = 'creator-v2-preview';
            button('creator.editor.preview', () => {
                const view = presentation();
                preview.textContent = [view.title, view.description, view.prompt, ...(view.logs || view.steps || view.option_labels || []), ...(view.commands || []).flatMap(cmd => ['$ ' + cmd.command, ...cmd.logs]), view.result_success, view.result_failure].filter(Boolean).join('\n');
            });
            button('creator.editor.reload', async () => {
                if (dirty && !await discard()) return;
                project = (await api('projects/' + encodeURIComponent(project.id))).project; dirty = false; edit();
            });
            button('creator.editor.list', async () => { if (!dirty || await discard()) await home(); });
            localized('p', 'creator.editor.' + (project.version ? 'locked' : 'will_lock'), form);
        }
        term.addEventListener('creator:open', event => action(async () => {
            if (dirty && !await discard()) return;
            project = (await api('projects/' + encodeURIComponent(event.detail))).project;
            dirty = false; edit();
        }));
        try {
            if (projectId) { project = (await api('projects/' + encodeURIComponent(projectId))).project; edit(); }
            else await home();
        } catch (error) { if (status) showError(status, error); else { term.remove(); throw error; } }
        return true;
    }
    async function launch(kind, projectId) {
        try { return await open(kind, projectId); }
        catch (error) { addSystemMessage('warning', GhostLocale.t('creator.editor.title'), errorKey(error) ? GhostLocale.t(errorKey(error)) : error.message); return true; }
    }
    async function mountUpdate(card, appId) {
        const label = localized('p', 'creator.editor.checking', card);
        try {
            let data = await api('installed/' + encodeURIComponent(appId));
            ghostSet(label, 'creator.editor.' + (data.available_version ? 'available' : 'withdrawn'), data.available_version ? {installed: data.installed_version, available: data.available_version} : {installed: data.installed_version});
            if (!data.update_available) return;
            const button = localized('button', 'creator.editor.update', card); button.type = 'button';
            button.className = 'gp-app-market-footer__action gp-search-product__action';
            button.addEventListener('click', async () => {
                button.disabled = true;
                try {
                    const result = await api('installed/' + encodeURIComponent(appId), 'POST', {expected_version: data.installed_version, version: data.available_version});
                    ghostSet(label, 'creator.editor.installed', {version: result.installed_version});
                    button.remove();
                } catch (error) { showError(label, error); button.disabled = false; }
            });
        } catch (error) { showError(label, error); }
    }
    return {launch, mountUpdate};
})();
