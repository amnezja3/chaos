/* Ghost message format v1. Returns plain text, never HTML. No global account locale. */
(function (root) {
    'use strict';
    const own = (obj, key) => Object.prototype.hasOwnProperty.call(obj, key);
    const token = /\{([a-zA-Z][a-zA-Z0-9_]*)\}/g;
    function normalizeLocale(value, registry, fallback = 'pl') {
        const tag = typeof value === 'string' ? value.trim().toLowerCase().replaceAll('_', '-').split('-')[0] : '';
        return own(registry.locales, tag) ? tag : fallback;
    }
    function resolveLocale(registry, {authenticated = false, account, device, browser} = {}) {
        return authenticated ? normalizeLocale(account, registry)
            : normalizeLocale(device, registry, null) || normalizeLocale(browser, registry);
    }
    function pluralCategory(value, rules) {
        const n = Math.abs(value);
        for (const rule of rules) {
            if (rule.conditions.every(condition => {
                let operand = {n, i: Math.floor(n), integer: Number.isInteger(n) ? 1 : 0}[condition.operand];
                if (own(condition, 'mod')) operand %= condition.mod;
                const found = condition.ranges.some(([low, high]) => low <= operand && operand <= high);
                return condition.not ? !found : found;
            })) return rule.category;
        }
        return 'other';
    }
    function createTranslator(registry, catalogs, diagnostic = (code, key, locale) => console.warn('i18n', code, key, locale)) {
        // Own immutable copies: a caller cannot change a live translator through a cached bundle.
        registry = JSON.parse(JSON.stringify(registry));
        catalogs = JSON.parse(JSON.stringify(catalogs));
        if (registry.format_version !== 1 || !own(catalogs, registry.default_locale)) throw Error('invalid_manifest');
        for (const [locale, bundle] of Object.entries(catalogs)) {
            if (!own(registry.locales, locale) || bundle.locale !== locale || bundle.format_version !== 1
                || bundle.content_version !== registry.content_version) throw Error('catalog_version_mismatch');
        }
        function t(key, params = {}, locale = 'pl') {
            locale = normalizeLocale(locale, registry);
            const fallback = registry.default_locale;
            const messages = catalogs[locale]?.messages || {};
            let entry = own(messages, key) ? messages[key] : null;
            let entryLocale = locale;
            if (!entry) {
                diagnostic('missing_key', key, locale);
                entryLocale = fallback;
                entry = own(catalogs[fallback].messages, key) ? catalogs[fallback].messages[key] : null;
            }
            if (!entry) return (catalogs[locale]?.messages['common.unavailable'] || catalogs[fallback].messages['common.unavailable']).text;
            if (params === null) params = {};
            const spec = entry.params;
            if (typeof params !== 'object' || Array.isArray(params)
                || Object.keys(params).sort().join('\0') !== Object.keys(spec).sort().join('\0')) throw Error('invalid_message_params');
            for (const [name, kind] of Object.entries(spec)) {
                const value = params[name];
                if (!(kind === 'string' && typeof value === 'string')
                    && !(kind === 'number' && typeof value === 'number' && Number.isFinite(value)
                        && Math.abs(value) <= Number.MAX_SAFE_INTEGER)) throw Error('invalid_message_params');
            }
            const template = entry.plural
                ? entry.forms[pluralCategory(params[entry.plural], registry.locales[entryLocale].plural_rules)] || entry.forms.other
                : entry.text;
            const names = [...new Set([...template.matchAll(token)].map(match => match[1]))].sort();
            if (names.join('\0') !== Object.keys(spec).sort().join('\0')) throw Error('invalid_message_template');
            return template.replace(token, (_, name) => String(params[name]));
        }
        return Object.freeze({t, message(envelope, locale = 'pl') {
            if (envelope.content_version !== registry.content_version) throw Error('message_version_mismatch');
            return t(envelope.key, envelope.params, locale);
        }});
    }
    const api = Object.freeze({normalizeLocale, resolveLocale, pluralCategory, createTranslator});
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else root.GhostI18n = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
