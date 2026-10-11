async (page) => {
    const assert = (ok, message) => { if (!ok) throw new Error(message); };
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8993');
    if (!await page.evaluate(() => !!window.CreatorEditor)) await page.goto('http://127.0.0.1:8993');
    await page.waitForFunction(() => !document.getElementById('boot-preloader') || document.getElementById('boot-preloader').classList.contains('done'));
    const kinds = ['terminal', 'window', 'button_choices', 'progressbar_random'];
    const actions = ['scan_player', 'exploit_player', 'sniff_player', 'trace_player'];
    const recipes = Object.fromEntries(actions.map((action, i) => [action, {
        resource_types: i === 1 ? [] : ['data'], requires_file: i >= 2
    }]));
    let headers;
    await page.route('**/api/creators/**', async route => {
        headers ||= (await route.fetch()).headers();
        const policy = route.request().url().endsWith('/policy');
        await route.fulfill({headers, json: policy ? {
            success: true, enabled: true, installed_interfaces: kinds, recipes, level: 40, power_cap: 100
        } : {success: true, projects: []}});
    });
    const checked = [];
    for (const kind of kinds) {
        await page.evaluate(kind => CreatorEditor.launch(kind), kind);
        const win = page.locator('.creator-v2').last();
        for (const locale of ['pl', 'en']) {
            await page.evaluate(locale => GhostLocale.changeLocale(locale, false), locale);
            for (const [i, action] of actions.entries()) {
                const button = win.locator(`[data-action="${action}"]`);
                await button.click();
                const expected = await page.evaluate(action => GhostLocale.t('map.action_name.' + action), action);
                assert((await button.innerText()).includes(expected), 'Missing category label');
                assert(await button.getAttribute('aria-pressed') === 'true', 'Category not selected');
                const toggle = win.locator('.creator-v2-file-toggle');
                assert(await toggle.isDisabled() === (i !== 0), 'Wrong file toggle policy');
                if (i >= 2) assert(await toggle.getAttribute('aria-pressed') === 'true', 'Required output disabled');
                checked.push(kind + ':' + locale + ':' + action);
            }
        }
    }
    for (const locale of ['pl', 'en']) {
        await page.evaluate(locale => GhostLocale.changeLocale(locale, false), locale);
        for (const [i, action] of ['scan_ports', 'exploit', 'sniff', 'trace'].entries()) {
            const title = await page.evaluate(({action, purpose}) => {
                createMapToolPicker({map_action_id: action,
                    pending_action: {action, target_mode: 'player', label: 'Test victim'},
                    matching_apps: [{id: purpose, name: 'Authored Tool', icon: 'X'}]});
                return GhostLocale.t('map.action.' + purpose);
            }, {action, purpose: actions[i]});
            assert(await page.locator('.map-tool-picker-head h3').innerText() === title, 'Wrong player picker title');
        }
    }
    assert(errors.length === 0, errors.join('\n'));
    return {checked: checked.length, pickerTitles: 8, errors};
}
