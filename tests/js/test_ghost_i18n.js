'use strict';
const fs = require('fs'), path = require('path'), assert = require('node:assert/strict');
const root = path.resolve(__dirname, '../..');
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const i18n = require('../../static/js/ghost_i18n.js');
const manifest = read('static/locales/manifest.json');
const bundles = Object.fromEntries(Object.keys(manifest.locales).map(locale => [locale, {
    locale, format_version: manifest.format_version, content_version: manifest.content_version,
    messages: Object.assign({}, ...manifest.domains.map(domain => read(`static/locales/${locale}/${domain}.json`).messages))
}]));
const cases = read('tests/fixtures/i18n_conformance.json');
const runtime = i18n.createTranslator(manifest, bundles);
for (const test of cases.translations) assert.equal(runtime.t(test.key, test.params, test.locale), test.expected);
for (const test of cases.resolution) assert.equal(i18n.resolveLocale(manifest, test.input), test.expected);
for (const params of [...cases.invalid_params, {count: NaN}, {count: Infinity}]) {
    assert.throws(() => runtime.t('shell.files.count', params), /invalid_message_params/);
}
assert.deepEqual(Object.keys(bundles.pl.messages).sort(), Object.keys(bundles.en.messages).sort());
for (const [locale, bundle] of Object.entries(bundles)) {
    for (const [key, entry] of Object.entries(bundle.messages)) {
        assert.deepEqual(entry.params, bundles.pl.messages[key].params);
        if (entry.plural) {
            assert.equal(entry.params[entry.plural], 'number');
            assert.deepEqual(Object.keys(entry.forms).sort(), [...manifest.locales[locale].plural_rules.map(r => r.category), 'other'].sort());
        }
        runtime.t(key, Object.fromEntries(Object.entries(entry.params).map(([name, kind]) => [name, kind === 'number' ? 2 : '<b>UGC</b>'])), locale);
    }
}
const missing = structuredClone(bundles), diagnostics = [];
delete missing.en.messages['shell.files.count'];
const fallback = i18n.createTranslator(manifest, missing, (...args) => diagnostics.push(args));
assert.equal(fallback.t('shell.files.count', {count: 22}, 'en'), '22 pliki');
assert.deepEqual(diagnostics, [['missing_key', 'shell.files.count', 'en']]);
const envelope = {key: 'shell.desktop.files', params: {}, content_version: manifest.content_version};
assert.equal(runtime.message(envelope, 'en'), 'Files');
assert.equal(runtime.message(envelope, 'pl'), 'Pliki');
assert.throws(() => runtime.message({...envelope, content_version: 'old'}), /message_version_mismatch/);
assert.throws(() => i18n.createTranslator(manifest, {...bundles, en: {...bundles.en, content_version: 'old'}}), /catalog_version_mismatch/);
const registry = structuredClone(manifest), extra = structuredClone(bundles);
registry.locales.zz = {...registry.locales.en, name: 'Pseudo', status: 'test'};
extra.zz = {...structuredClone(extra.en), locale: 'zz'};
extra.zz.messages['shell.desktop.files'].text = '[Файлы — extended label]';
assert.equal(i18n.createTranslator(registry, extra).t('shell.desktop.files', {}, 'zz'), '[Файлы — extended label]');
// Caller mutations and prototype keys must not affect translations.
bundles.en.messages['shell.desktop.files'].text = 'mutated';
assert.equal(runtime.t('shell.desktop.files', {}, 'en'), 'Files');
assert.equal(runtime.t('constructor', {}, 'en'), 'Message unavailable.');
console.log(`Ghost i18n: PASS (${cases.translations.length} shared translations, locale precedence, contracts, fallback, extra package)`);
