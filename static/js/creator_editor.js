/* Creator projects: system-owned mechanics, editable presentation. */
window.CreatorEditor = (() => {
    const actionIcons = {exploit: '💥', scan_ports: '🛠️', trace: '📍', trace_gps: '📍', trace_device: '📡', scan_hotspots: '📶', camera_stream: '🎥', camera_shutdown: '❌', install_sniffer: '🐛', sniff: '📡', mic_sniff: '🎙️', atm_logs: '📊', audio_hack: '🔊', car_hack: '🚗'};
    const names = {terminal: 'TermCreator', window: 'WindowMaker', button_choices: 'ButtonMaker', progressbar_random: 'AppForge'};
    const labels = {exploit: 'Exploit', scan_ports: 'Skan portów', trace: 'Śledzenie', trace_gps: 'GPS pojazdu', trace_device: 'Śledzenie urządzenia', scan_hotspots: 'Hotspoty', camera_stream: 'Obraz kamery', camera_shutdown: 'Wyłączenie kamery', install_sniffer: 'Instalacja sniffera', sniff: 'Sniffer', mic_sniff: 'Podsłuch', atm_logs: 'Logi bankomatu', audio_hack: 'Zakłócenie audio', car_hack: 'System pojazdu'};
    async function api(path, method = 'GET', body) {
        const response = await fetch('/api/creators/' + path, {method, cache: 'no-store', headers: {'Content-Type': 'application/json'}, ...(body === undefined ? {} : {body: JSON.stringify(body)})});
        const data = await response.json();
        if (!response.ok || !data.success) { const error = new Error(data.message || 'Nie udało się wykonać operacji.'); error.status = response.status; throw error; }
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
        if (!policy.installed_interfaces.includes(kind)) throw new Error('Brak narzędzia kreatorskiego. Zainstaluj odpowiedni kreator.');
        const existing = document.querySelector(`.creator-window[data-app="${names[kind].toLowerCase()}"]`);
        if (existing) {
            existing.style.zIndex = String(Date.now());
            if (projectId) existing.dispatchEvent(new CustomEvent('creator:open', {detail: projectId}));
            return true;
        }
        const term = creatorBaseWindow(names[kind], kind);
        term.classList.add('creator-v2');
        const form = term.querySelector('form');
        let project = null, dirty = false, busy = false;
        const close = term.querySelector('.close-btn');
        const discard = () => showGhostDecisionDialog({title: 'KREATOR', message: 'Odrzucić niezapisane zmiany?', confirmLabel: 'ODRZUĆ', cancelLabel: 'WRÓĆ DO EDYCJI'});
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
            node('h3', title, heading);
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
            try { await work(); } catch (error) { status.textContent = error.message; }
            finally { busy = false; term.removeAttribute('aria-busy'); enabled.forEach(el => { el.disabled = el.dataset.unavailable === 'true'; }); }
        }
        function button(text, work, parent = form) {
            const el = node('button', text, parent); el.type = 'button';
            el.addEventListener('click', () => action(work)); return el;
        }
        function field(text, value = '', multiline = false, parent = form) {
            const label = node('label', text, parent);
            const input = node(multiline ? 'textarea' : 'input', undefined, label);
            input.value = value; input.maxLength = multiline ? 6000 : 120;
            if (multiline) input.rows = 4;
            return input;
        }
        function iconField(value) {
            node('p', 'Ikona — jeden znak lub emoji', form);
            const group = node('div', undefined, form);
            group.className = 'appforge-icon-row';
            const input = field('Ikona — jeden znak lub emoji', value, false, group);
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
            reset('Nowe narzędzie'); dirty = false;
            const name = field('Nazwa', ''); name.maxLength = 80;
            const icon = iconField('🛠️');
            node('p', 'Przeznaczenie — akcja na mapie', form);
            const choices = node('div', undefined, form); choices.className = 'creator-v2-choices';
            let selected = Object.keys(policy.recipes)[0], createsFile = false;
            const actionButtons = Object.keys(policy.recipes).map(key => {
                const el = button('', () => { selected = key; dirty = true; refresh(); }, choices);
                node('span', actionIcons[key] || '◇', el).className = 'creator-action-icon';
                node('span', labels[key] || key, el).className = 'creator-action-label';
                el.title = labels[key] || key;
                node('span', '›', el).className = 'creator-action-arrow';
                el.dataset.action = key; return el;
            });
            const file = button('Tworzy plik', () => { createsFile = !createsFile; dirty = true; refresh(); });
            file.className = 'creator-v2-file-toggle';
            const fileNote = node('p', '', form);
            fileNote.className = 'creator-v2-file-note';
            function refresh() {
                actionButtons.forEach(el => el.setAttribute('aria-pressed', String(el.dataset.action === selected)));
                const resources = policy.recipes[selected].resource_types;
                const required = policy.recipes[selected].requires_file === true;
                file.disabled = required || !resources.length;
                file.dataset.unavailable = String(file.disabled);
                if (required) createsFile = true;
                else if (!resources.length) createsFile = false;
                file.setAttribute('aria-pressed', String(createsFile));
                file.textContent = `${actionIcons[selected] || '📄'} Tworzy plik: ` + (createsFile ? 'TAK' : 'NIE');
                fileNote.textContent = required ? 'Ta akcja wymaga pliku. Zapis jest obowiązkowy po skutecznym zakończeniu operacji.' : (createsFile ? 'Plik powstanie po skutecznym zakończeniu operacji.' : 'To narzędzie nie zapisuje pliku.');
            }
            refresh();
            // Retain the request identity and payload after a lost response: no second roll.
            let pending;
            button('Generuj narzędzie', async () => {
                pending ||= {name: name.value, icon: icon.value, action: selected, creates_file: createsFile, interface: kind, request_id: crypto.randomUUID()};
                try { project = (await api('projects', 'POST', pending)).project; }
                catch (error) { if (error.status >= 400 && error.status < 500) pending = undefined; throw error; }
                dirty = false; edit();
            }).classList.add('creator-v2-generate');
            node('h4', 'Zapisane projekty', form);
            const list = node('div', '', form);
            list.className = 'creator-v2-projects';
            async function page(after = '') {
                const data = await api('projects' + (after ? '?after=' + encodeURIComponent(after) : ''));
                data.projects.filter(p => p.interface === kind).forEach(p => button(`${p.icon} ${p.name} · v${p.version}`, async () => {
                    if (dirty && !await discard()) return;
                    project = (await api('projects/' + encodeURIComponent(p.id))).project; dirty = false; edit();
                }, list));
                if (data.next_cursor) { const more = button('Więcej projektów', async () => { more.remove(); await page(data.next_cursor); }, list); }
            }
            await page();
        }
        function edit() {
            let saved = project.version > 0;
            reset('Interfejs i publikacja');
            const c = project.contract, p = project.presentation;
            node('p', c.legacy ? `Projekt historyczny · oryginalna mechanika · wersja ${project.version}` : `Moc: ${c.power}% · maksimum przy generacji: ${c.power_cap}% · ${labels[c.action] || c.action} · wersja ${project.version}`, form);
            if (!c.legacy) {
                const fileSummary = node('p', `${actionIcons[c.action] || '📄'} Tworzy plik: ${c.creates_file ? 'TAK — po zakończeniu operacji' : 'NIE'}`, form);
                fileSummary.className = 'creator-file-summary';
                fileSummary.dataset.createsFile = String(c.creates_file);
            }
            const name = field('Nazwa', p.name); name.maxLength = 80;
            const icon = iconField(p.icon);
            const title = field('Tytuł interfejsu', p.title || p.name);
            const description = field('Opis w Googleplexie', p.description || '', true);
            const price = field('Cena zakupu HC (0 = Open Source)', c.price); price.type = 'number'; price.min = '0'; price.step = '1'; price.disabled = !!project.version;
            const rows = [];
            let prompt, logs, buttons, steps, success, failure;
            const list = node('div', '', form);
            if (kind === 'terminal') {
                const add = (command = {command: '', logs: []}) => {
                    const group = node('fieldset', undefined, list);
                    rows.push({command: field('Komenda', command.command, false, group), logs: field('Outputy — jeden na linię', command.logs.join('\n'), true, group)});
                };
                (p.commands || [{command: 'run', logs: ['Uruchamianie…']}]).forEach(add);
                if (!c.legacy) button('Dodaj komendę', () => { if (rows.length < 32) { add(); dirty = true; } }, list);
            } else if (kind === 'window') {
                logs = field('Logi — jeden na linię', (p.logs || []).join('\n'), true);
                buttons = field('Przyciski — jeden na linię', (p.button_labels || ['Uruchom']).join('\n'), true);
            } else if (kind === 'button_choices') {
                prompt = field('Prompt', p.prompt || '', true);
                node('p', c.legacy ? 'Historyczne efekty i ceny pozostają bez zmian. Możesz edytować etykiety i komunikaty.' : `Effect działa od LVL ${policy.effect_min_level}. ${policy.effect_enabled ? 'Możesz użyć zatwierdzonych przypisań, np. firewall=false.' : 'Na Twoim poziomie wpisany effect nie zmieni działania.'}`, form);
                const add = (label = 'Wykonaj', option = {}) => {
                    const group = node('fieldset', undefined, list);
                    const effectText = Object.entries(option.effect || {}).map(([key, value]) => `${key}=${value}`).join(',');
                    const row = {label: field('Opcja', label, false, group), effect: field('Effect', effectText, false, group), price: field('Cena użycia HC', option.price || 0, false, group)};
                    row.effect.placeholder = 'risk_level=10,firewall=false';
                    row.effect.maxLength = 6000; row.price.type = 'number'; row.price.min = '0'; row.price.step = '1';
                    row.effect.disabled = row.price.disabled = !!project.version; rows.push(row);
                };
                (p.option_labels || ['Wykonaj']).forEach((label, index) => add(label, (c.options || [])[index]));
                if (!project.version) button('Dodaj opcję', () => { if (rows.length < 32) { add(); dirty = true; } }, list);
            } else {
                steps = field('Logi postępu — jeden na linię', (p.steps || ['Uruchamianie…']).join('\n'), true);
                success = field('Komunikat sukcesu', p.result_success || 'Operacja wykonana.');
                failure = field('Komunikat niepowodzenia', p.result_failure || 'Operacja odrzucona.');
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
            button('Zapisz szkic', async () => { await save(); status.textContent = 'Szkic zapisany.'; });
            button('Opublikuj', async () => {
                await save();
                const data = await api('projects/' + encodeURIComponent(project.id) + '/publish', 'POST', {revision: project.revision});
                project.version = data.app.version; edit(); status.textContent = `Opublikowano wersję ${project.version}.`;
            });
            const preview = node('pre', '', form); preview.className = 'creator-v2-preview';
            button('Podgląd tekstów — bez wykonania', () => {
                const view = presentation();
                preview.textContent = [view.title, view.description, view.prompt, ...(view.logs || view.steps || view.option_labels || []), ...(view.commands || []).flatMap(cmd => ['$ ' + cmd.command, ...cmd.logs]), view.result_success, view.result_failure].filter(Boolean).join('\n');
            });
            button('Odczytaj zapisany projekt', async () => {
                if (dirty && !await discard()) return;
                project = (await api('projects/' + encodeURIComponent(project.id))).project; dirty = false; edit();
            });
            button('Lista projektów', async () => { if (!dirty || await discard()) await home(); });
            node('p', project.version ? 'Mechanika, efekty i ceny opublikowanej aplikacji są zablokowane.' : 'Po pierwszej publikacji mechanika i ceny zostaną zablokowane.', form);
        }
        term.addEventListener('creator:open', event => action(async () => {
            if (dirty && !await discard()) return;
            project = (await api('projects/' + encodeURIComponent(event.detail))).project;
            dirty = false; edit();
        }));
        try {
            if (projectId) { project = (await api('projects/' + encodeURIComponent(projectId))).project; edit(); }
            else await home();
        } catch (error) { if (status) status.textContent = error.message; else { term.remove(); throw error; } }
        return true;
    }
    async function launch(kind, projectId) {
        try { return await open(kind, projectId); }
        catch (error) { addSystemMessage('warning', 'Kreator', error.message); return true; }
    }
    async function mountUpdate(card, appId) {
        const label = node('p', 'Sprawdzanie wersji…', card);
        try {
            let data = await api('installed/' + encodeURIComponent(appId));
            label.textContent = `Zainstalowana: v${data.installed_version} · dostępna: ${data.available_version ? 'v' + data.available_version : 'wycofana'}`;
            if (!data.update_available) return;
            const button = node('button', 'AKTUALIZACJA · 0 HC', card); button.type = 'button';
            button.addEventListener('click', async () => {
                button.disabled = true;
                try {
                    const result = await api('installed/' + encodeURIComponent(appId), 'POST', {expected_version: data.installed_version, version: data.available_version});
                    label.textContent = `Zainstalowana: v${result.installed_version}`;
                    button.remove();
                } catch (error) { label.textContent = error.message; button.disabled = false; }
            });
        } catch (error) { label.textContent = error.message; }
    }
    return {launch, mountUpdate};
})();
