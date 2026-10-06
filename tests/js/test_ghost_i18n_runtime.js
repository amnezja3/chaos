'use strict';
const assert = require('node:assert/strict'), fs = require('fs'), path = require('path');
const {createRuntime} = require('../../static/js/ghost_i18n_runtime.js');
const root = path.resolve(__dirname, '../../static/locales');
const read = file => JSON.parse(fs.readFileSync(path.join(root, file), 'utf8'));
const manifest = read('manifest.json');
const pack = locale => ({locale, format_version: 1, content_version: manifest.content_version,
    messages: Object.assign({}, ...manifest.domains.map(domain => read(`${locale}/${domain}.json`).messages))});
const fetchPack = async url => ({ok: true, json: async () => read(new URL(url, 'http://localhost').pathname.replace('/static/locales/', ''))});
const deferred = () => {let resolve, reject; const promise = new Promise((yes, no) => {resolve=yes; reject=no;}); return {promise,resolve,reject};};
(async () => {
    let calls = 0, changes = [];
    const runtime = createRuntime({manifest, fallback: pack('pl'), fetch: url => {calls++; return fetchPack(url);}, onChange: locale => changes.push(locale)});
    await runtime.changeLocale('en-GB');
    assert.equal(runtime.t('settings.email'), 'Email address');
    await runtime.changeLocale('pl'); await runtime.changeLocale('en');
    assert.equal(calls, manifest.domains.length, 'cache is scoped to runtime manifest version');
    assert.equal(runtime.formatNumber(1234.5), '1,234.5');
    assert.equal(runtime.formatNumber(12345.625, {maximumFractionDigits:2}), '12,345.63');
    assert.equal(runtime.formatUnit(12345.625, 'hackcoin'), '12,345.625 HC');
    assert.equal(runtime.formatDate('2026-10-06T23:30:00Z', {timeZone:'UTC'}), '10/06/2026');
    await runtime.changeLocale('pl');
    assert.equal(runtime.formatNumber(1234.5), '1234,5');
    assert.equal(runtime.formatNumber(12345.625, {maximumFractionDigits:2}), '12\u00a0345,63');
    assert.equal(runtime.formatDate('2026-10-06T23:30:00Z', {timeZone:'UTC'}), '06.10.2026');
    await runtime.changeLocale('en');
    assert.match(runtime.formatDate('2026-10-06T00:00:00Z', {timeZone:'UTC',year:'numeric'}), /2026/);
    await assert.rejects(runtime.changeLocale('ANY'), /invalid_locale/);
    await assert.rejects(runtime.changeLocale('pl', async () => {throw Error('save_failed');}), /save_failed/);
    assert.equal(runtime.getLocale(), 'en', 'failed persistence preserves old display');

    const gate = deferred(), saved = [];
    const racing = createRuntime({manifest, fallback: pack('pl'), fetch: async url => {await gate.promise; return fetchPack(url);}});
    const first = racing.changeLocale('en', async locale => saved.push(locale));
    const last = racing.changeLocale('pl', async locale => saved.push(locale));
    gate.resolve();
    assert.equal(await first, false);
    assert.equal(await last, true);
    assert.deepEqual(saved, ['pl'], 'superseded requests never write account state');
    assert.equal(racing.getLocale(), 'pl');

    const saveGate = deferred(), started = deferred();
    const acknowledged = createRuntime({manifest, fallback: pack('pl'), fetch: fetchPack});
    const a = acknowledged.changeLocale('en', async () => {started.resolve(); await saveGate.promise;});
    await started.promise;
    const b = acknowledged.changeLocale('pl', async () => {throw Error('write_failed');});
    const failure = assert.rejects(b, /write_failed/);
    saveGate.resolve(); await a; await failure;
    assert.equal(acknowledged.getLocale(), 'en', 'last acknowledged account state survives a later failure');

    let fail = true, writes = 0;
    const recover = createRuntime({manifest, fallback: pack('pl'), fetch: async url => fail ? {ok:false} : fetchPack(url)});
    await assert.rejects(recover.changeLocale('en', async () => writes++), /catalog_unavailable/);
    assert.equal(recover.getLocale(), 'pl'); assert.equal(writes, 0);
    fail = false; await recover.changeLocale('en'); assert.equal(recover.getLocale(), 'en');
    const incomplete = createRuntime({manifest, fallback: pack('pl'), fetch: async url => {
        const data = await (await fetchPack(url)).json(); delete data.messages['settings.email'];
        return {ok:true,json:async()=>data};
    }});
    await assert.rejects(incomplete.changeLocale('en'), /incomplete_catalog/);
    assert.equal(incomplete.getLocale(), 'pl');
    const stale = createRuntime({manifest, fallback: pack('pl'), fetch: async url => {
        const data = await (await fetchPack(url)).json(); data.content_version = 'old'; return {ok:true,json:async()=>data};
    }});
    await assert.rejects(stale.changeLocale('en'), /catalog_version_mismatch/);
    assert.equal(stale.getLocale(), 'pl');
    const wrongForm = createRuntime({manifest, fallback: pack('pl'), fetch: async url => {
        const data = await (await fetchPack(url)).json();
        if (data.messages['shell.files.count']) data.messages['shell.files.count'].forms.one = '{missing} file';
        return {ok:true,json:async()=>data};
    }});
    await assert.rejects(wrongForm.changeLocale('en'), /invalid_message_template/);
    assert.equal(wrongForm.getLocale(), 'pl');
    console.log('Ghost locale runtime: PASS (atomic packs, cache, race, write/load failure, retry, formats)');
})().catch(error => {console.error(error); process.exitCode=1;});
