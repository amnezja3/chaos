/* Atomic catalog selection. Only explicitly marked system text is rendered. */
(function (root) {
    'use strict';
    const core = typeof module !== 'undefined' && module.exports ? require('./ghost_i18n.js') : root.GhostI18n;
    function createRuntime({manifest, fallback, fetch: fetcher = root.fetch.bind(root), onChange = () => {}}) {
        const cache = new Map(), pending = new Map();
        let activeLocale = manifest.default_locale;
        let activeTranslator = core.createTranslator(manifest, {[activeLocale]: fallback});
        cache.set(activeLocale, fallback);
        let intent = 0, writes = Promise.resolve();
        function validate(bundle, locale) {
            core.createTranslator(manifest, {[manifest.default_locale]: fallback, [locale]: bundle});
            for (const [key, entry] of Object.entries(fallback.messages)) {
                const other = bundle.messages?.[key];
                if (!other || JSON.stringify(Object.entries(entry.params).sort()) !== JSON.stringify(Object.entries(other.params).sort())) {
                    throw Error('incomplete_catalog');
                }
            }
            const translator = core.createTranslator(manifest, {[manifest.default_locale]: fallback, [locale]: bundle});
            for (const [key, entry] of Object.entries(bundle.messages)) {
                const params = Object.fromEntries(Object.entries(entry.params).map(([name, type]) => [name, type === 'number' ? 2 : 'test']));
                translator.t(key, params, locale);
                for (const template of entry.plural ? Object.values(entry.forms) : [entry.text]) {
                    if (typeof template !== 'string') throw Error('invalid_message_template');
                    const names = [...new Set([...template.matchAll(/\{([a-zA-Z][a-zA-Z0-9_]*)\}/g)].map(match => match[1]))].sort();
                    if (names.join('\0') !== Object.keys(entry.params).sort().join('\0')) throw Error('invalid_message_template');
                }
                if (entry.plural) {
                    if (entry.params[entry.plural] !== 'number') throw Error('invalid_plural');
                    for (const category of [...manifest.locales[locale].plural_rules.map(rule => rule.category), 'other']) {
                        if (typeof entry.forms[category] !== 'string') throw Error('incomplete_plural');
                    }
                }
            }
            return bundle;
        }
        validate(fallback, manifest.default_locale);
        async function load(locale) {
            if (cache.has(locale)) return cache.get(locale);
            if (pending.has(locale)) return pending.get(locale);
            const task = (async () => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), 10000);
                try {
                    const messages = {};
                    for (const domain of manifest.domains) {
                        const response = await fetcher(`/static/locales/${encodeURIComponent(locale)}/${encodeURIComponent(domain)}.json?v=${encodeURIComponent(manifest.content_version)}`,
                            {signal: controller.signal, cache: 'default'});
                        if (!response.ok) throw Error('catalog_unavailable');
                        const bundle = await response.json();
                        core.createTranslator(manifest, {[manifest.default_locale]: fallback, [locale]: bundle});
                        for (const [key, entry] of Object.entries(bundle.messages)) {
                            if (Object.prototype.hasOwnProperty.call(messages, key)) throw Error('duplicate_message_key');
                            messages[key] = entry;
                        }
                    }
                    const bundle = validate({locale, messages, format_version: manifest.format_version, content_version: manifest.content_version}, locale);
                    cache.set(locale, bundle);
                    return bundle;
                } finally { clearTimeout(timer); pending.delete(locale); }
            })();
            pending.set(locale, task);
            return task;
        }
        function changeLocale(value, persist) {
            const locale = core.normalizeLocale(value, manifest, null);
            if (!locale) return Promise.reject(Error('invalid_locale'));
            const ticket = ++intent;
            // Observe rejection immediately even while an earlier write is pending.
            const prepared = load(locale).then(bundle => ({bundle}), error => ({error}));
            const operation = writes.catch(() => {}).then(async () => {
                const result = await prepared;
                if (ticket !== intent) return false;
                if (result.error) throw result.error;
                if (persist) await persist(locale);
                // Once acknowledged, this is the account's last confirmed locale,
                // also when a later choice is still loading or ultimately fails.
                activeTranslator = core.createTranslator(manifest, {[manifest.default_locale]: fallback, [locale]: result.bundle});
                activeLocale = locale;
                onChange(locale, manifest.locales[locale]);
                return true;
            });
            writes = operation;
            return operation;
        }
        return Object.freeze({changeLocale, getLocale: () => activeLocale,
            getBundle: () => JSON.parse(JSON.stringify(cache.get(activeLocale))),
            installBundle: bundle => { cache.set(bundle.locale, validate(bundle, bundle.locale)); },
            contentVersion: manifest.content_version,
            hasKey: key => Object.prototype.hasOwnProperty.call(fallback.messages, key),
            t: (key, params = {}) => activeTranslator.t(key, params, activeLocale),
            languages: () => Object.entries(manifest.locales).map(([tag, data]) => ({tag, ...data})),
            formatNumber: (value, options = {}) => new Intl.NumberFormat(activeLocale, options).format(value),
            formatUnit: (value, unit, options = {}) => {
                const label = manifest.locales[activeLocale].formats.units[unit];
                if (!label) throw Error('unsupported_unit');
                return new Intl.NumberFormat(activeLocale, options).format(value) + ' ' + label;
            },
            formatDate: (value, options = {}) => new Intl.DateTimeFormat(activeLocale, {day:'2-digit', month:'2-digit', year:'numeric', ...options}).format(new Date(value))});
    }
    function mount(document, config, options = {}) {
        let runtime;
        const render = (container = document) => {
            const nodes = selector => [...(container.matches?.(selector) ? [container] : []), ...container.querySelectorAll(selector)];
            for (const node of nodes('[data-ghost-i18n]')) {
                const value = runtime.t(node.dataset.ghostI18n, JSON.parse(node.dataset.ghostParams || '{}'));
                if (node.textContent !== value) node.textContent = value;
            }
            for (const node of container.querySelectorAll('[data-ghost-i18n-placeholder]')) node.placeholder = runtime.t(node.dataset.ghostI18nPlaceholder);
            for (const attr of ['title', 'aria-label']) for (const node of nodes(`[data-ghost-${attr}]`)) {
                node.setAttribute(attr, runtime.t(node.getAttribute(`data-ghost-${attr}`), JSON.parse(node.dataset.ghostParams || '{}')));
            }
            for (const node of nodes('[data-ghost-number]')) node.textContent = runtime.formatNumber(Number(node.dataset.ghostNumber), JSON.parse(node.dataset.ghostFormat || '{}'));
            for (const node of nodes('[data-ghost-date]')) node.textContent = runtime.formatDate(node.dataset.ghostDate, JSON.parse(node.dataset.ghostFormat || '{}'));
        };
        runtime = createRuntime({...config, ...options, onChange(locale, definition) {
            document.documentElement.lang = locale;
            document.documentElement.dir = definition.direction;
            render();
            document.dispatchEvent(new CustomEvent('ghost:locale-changed', {detail: {locale}}));
            options.onChange?.(locale, definition);
        }});
        document.documentElement.lang = config.manifest.default_locale;
        document.documentElement.dir = config.manifest.locales[config.manifest.default_locale].direction;
        // Observe only explicit bindings; never inspect or replace authored text.
        if (root.MutationObserver) {
            const observer = new root.MutationObserver(records => {
                for (const record of records) for (const node of record.addedNodes) if (node.nodeType === 1) render(node);
            });
            observer.observe(document.documentElement, {childList: true, subtree: true});
        }
        return Object.freeze({...runtime, render});
    }
    const api = {createRuntime, mount};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else {
        root.GhostI18nRuntime = api;
        const node = root.document.getElementById('ghost-i18n-bootstrap');
        if (node) {
            const config = JSON.parse(node.textContent);
            root.GhostLocale = mount(root.document, config);
            if (config.locale) root.GhostLocale.changeLocale(config.locale).catch(() => {});
        }
    }
})(typeof globalThis !== 'undefined' ? globalThis : this);
