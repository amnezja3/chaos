// Run with Playwright MCP browser_run_code_unsafe after starting
// tools/sprint_153_browser_fixture.py. API fixtures isolate publication from production.
async (page) => {
    const assert = (ok, message) => { if (!ok) throw new Error(message); };
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.setViewportSize({width: 1440, height: 1000});
    await page.unroute('**/api/creators/**');
    await page.goto('http://127.0.0.1:8993');
    if (!await page.evaluate(() => !!window.CreatorEditor)) await page.goto('http://127.0.0.1:8993');
    const contentVersion = await page.evaluate(() => GhostLocale.contentVersion);
    const kinds = ['terminal', 'window', 'button_choices', 'progressbar_random'];
    const projects = Object.fromEntries(kinds.map(kind => [kind, {
        id: kind, interface: kind, version: 0, revision: 1,
        contract: {interface: kind, power: 73, power_cap: 100, action: 'car_hack', creates_file: false, price: 700, options: [{price: 0, effect: {firewall: false}}]},
        presentation: {name: 'Mój projekt <keep>', icon: '🍓', title: 'creator.editor.publish', description: 'Opis autora {version}', commands: [{command: 'run', logs: ['Własny output']}], logs: ['Własny log'], button_labels: ['Mój przycisk'], prompt: 'Moje pytanie', option_labels: ['Moja opcja'], steps: ['Mój krok'], result_success: 'Mój sukces', result_failure: 'Moja porażka'}
    }]));
    const writes = [];
    let rejectNext = false;
    let sessionHeaders;
    await page.route('**/api/creators/**', async route => {
        // Read canonical identity once; the fixture HTTP server does not implement PATCH.
        if (!sessionHeaders) sessionHeaders = (await route.fetch()).headers();
        const path = new URL(route.request().url()).pathname;
        const method = route.request().method();
        if (path.endsWith('/policy')) return route.fulfill({headers: sessionHeaders, json: {success: true, enabled: true, installed_interfaces: kinds, effect_enabled: true, effect_min_level: 10, recipes: {car_hack: {resource_types: [], requires_file: false}}}});
        const id = path.split('/')[4], project = projects[id];
        if (method !== 'GET') {
            const body = route.request().postDataJSON();
            writes.push({path, method, body});
            if (rejectNext === 'typed') {
                rejectNext = false;
                return route.fulfill({headers: sessionHeaders, status: 400, json: {
                    success: false, reason: 'invalid_creator_input', message: 'Unknown effect key',
                    message_i18n: {key: 'creator.validation.effect_unknown', params: {key: '<keep>'},
                        option_index: 2, content_version: contentVersion}}});
            }
            if (rejectNext) { rejectNext = false; return route.fulfill({headers: sessionHeaders, status: 409, json: {success: false, reason: 'revision_conflict', message: 'Projekt zmienil sie.'}}); }
            if (path.endsWith('/publish')) { project.version = 1; return route.fulfill({headers: sessionHeaders, json: {success: true, app: {version: 1}}}); }
            if (body.presentation) project.presentation = body.presentation;
            project.revision++;
        }
        return route.fulfill({headers: sessionHeaders, json: {success: true, project}});
    });
    const results = [];
    for (const kind of kinds) {
        await page.evaluate(() => GhostLocale.changeLocale('pl', false));
        await page.evaluate(kind => CreatorEditor.launch(kind, kind), kind);
        const win = page.locator('.creator-v2').last();
        const name = win.locator('label').filter({has: page.locator('[data-ghost-i18n="creator.editor.name"]')}).locator('input');
        await name.fill('Zmieniona nazwa <keep> ' + kind);
        const before = await win.locator('input,textarea').evaluateAll(nodes => nodes.map(node => node.value));
        await win.evaluate(node => { window.localeTestWindow = node; });
        await page.evaluate(() => GhostLocale.changeLocale('en', false));
        const after = await win.locator('input,textarea').evaluateAll(nodes => nodes.map(node => node.value));
        assert(JSON.stringify(before) === JSON.stringify(after), kind + ': authored fields changed');
        assert(await win.evaluate(node => node === window.localeTestWindow), 'Window replaced');
        await win.getByRole('button', {name: 'Preview text — without execution', exact: true}).click();
        assert((await win.locator('.creator-v2-preview').innerText()).includes('creator.editor.publish'), 'UGC key translated');
        await win.getByRole('button', {name: 'Save draft', exact: true}).click();
        await win.getByRole('status').filter({hasText: 'Draft saved.'}).waitFor();
        const saved = writes.filter(w => w.path.endsWith('/' + kind) && w.body.presentation).at(-1);
        assert(saved.body.presentation.name === 'Zmieniona nazwa <keep> ' + kind, 'Wrong saved name');
        assert(saved.body.presentation.title === 'creator.editor.publish', 'Wrong saved title');
        await win.getByRole('button', {name: 'Publish', exact: true}).click();
        await win.getByRole('status').filter({hasText: 'Version 1 published.'}).waitFor();
        assert(await win.locator('input[type="number"]').first().isDisabled(), 'Published price unlocked');
        await page.evaluate(() => GhostLocale.changeLocale('pl', false));
        assert((await win.getByRole('status').innerText()) === 'Opublikowano wersję 1.', 'Status did not translate');
        results.push({kind, saved: true, published: true, preserved: true});
        await win.evaluate(node => node.remove());
    }
    await page.setViewportSize({width: 390, height: 844});
    await page.evaluate(() => CreatorEditor.launch('window', 'window'));
    const win = page.locator('.creator-v2').last();
    await win.locator('input').first().fill('Konflikt <keep>');
    rejectNext = true;
    await win.getByRole('button', {name: 'Zapisz szkic', exact: true}).click();
    await win.locator('[data-ghost-i18n="creator.error.revision_conflict"]').waitFor();
    await page.evaluate(() => GhostLocale.changeLocale('en', false));
    assert((await win.getByRole('status').innerText()).startsWith('The project has changed.'), 'Conflict did not translate');
    assert(await win.locator('input').first().inputValue() === 'Konflikt <keep>', 'Conflict lost input');
    assert(!await win.getByRole('button', {name: 'Save draft', exact: true}).isDisabled(), 'Busy lock stuck');
    rejectNext = 'typed';
    await win.getByRole('button', {name: 'Save draft', exact: true}).click();
    await win.locator('[data-ghost-i18n="creator.validation.effect_unknown"]').waitFor();
    assert(await win.getByRole('status').innerText() === 'Option 2: Unknown effect key: <keep>', 'Typed error context lost');
    await page.evaluate(() => GhostLocale.changeLocale('pl', false));
    assert(await win.getByRole('status').innerText() === 'Opcja 2: Nieznany klucz effect: <keep>', 'Typed error did not switch language');
    assert(await win.getByRole('status').locator('keep').count() === 0, 'Error parameter parsed as HTML');
    assert(!await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), 'Mobile overflow');
    assert(!errors.length, errors.join('\n'));
    return {results, mobileConflict: true, typedValidation: true, errors, writes: writes.length};
}
