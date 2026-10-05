// Component verification against the local workspace fixture on port 8990.
async page => {
    await page.goto('http://127.0.0.1:8990/');
    const source = await page.evaluate(() => fetch('/static/js/terminal.js').then(response => response.text()));
    const start = source.indexOf('const renderCatalog = () =>');
    const renderer = source.slice(start, source.indexOf('const createProductCard =', start));
    const htmlStart = source.indexOf('<div class="googolplex-shell">', source.indexOf('function createBrowser('));
    const markup = source.slice(htmlStart, source.indexOf('    `;', htmlStart));
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addScriptTag({url: '/static/js/googleplex_search_presentation.js'});
    for (const css of ['googleplex_news.css', 'googleplex_search.css']) {
        await page.addStyleTag({url: `/static/css/${css}`});
    }
    await page.evaluate(({renderer, markup}) => {
        const setup = `
            const googleplexSearchPresentation = window.GoogleplexSearchPresentation;
            const terminalId = 'test';
            const term = document.createElement('div');
            term.className = 'browser-window is-browser-googleplex';
            term.style.cssText = 'width:100%;height:100vh;';
            term.innerHTML = \`${markup}\`;
            document.body.replaceChildren(term);
            const search = term.querySelector('.googolplex-search');
            const results = term.querySelector('.googolplex-grid');
            let activeBrowserTab = 'googleplex', catalogLoaded = false;
            const catalog = [
                {name:'GX', map_actions:['atm_logs'], downloads:2},
                {name:'Hold', map_actions:['camera_shutdown'], downloads:5},
                {name:'Berlin', product_type:'travel_ticket', downloads:1},
                {name:'Vault', product_type:'storage_upgrade', downloads:0}
            ];
            const updateBrowserNarrowMode = () => {}, rememberGoogleplexHomeScroll = () => {};
            const beginGoogleplexCatalogView = () => () => {};
            const googleplexHomeSnapshot = {}, googleplexHomeLoading = false, googleplexHomeError = false;
            const renderGoogleplexHome = () => results.textContent = 'NEWS HOME';
            const loadGoogleplexHome = async () => {};
            const loadCatalog = async () => { catalogLoaded = true; renderCatalog(); };
            ${renderer}
                googleplexSearchPresentation.mount(cardsRoot, matches, item => {
                    const card = document.createElement('article');card.textContent = item.name;return card;
                });
            };
            term.querySelector('.gp-category-filter select').addEventListener('change', renderCatalog);
            search.addEventListener('input', renderCatalog);
            renderCatalog();
        `;
        (0, eval)(setup);
    }, {renderer, markup});
    const select = page.getByRole('combobox');
    const search = page.locator('.googolplex-search');
    const names = () => page.locator('.gp-search-results article').allTextContents();
    const check = (value, message) => {if (!value) throw new Error(message);};
    check(await page.locator('.googolplex-grid').textContent() === 'NEWS HOME', 'Initial home');
    await select.selectOption('tools');
    check((await names()).join(',') === 'GX,Hold', 'Lazy category-only results');
    await search.fill('bankomat');
    check((await names()).join(',') === 'GX', 'Category plus Polish query');
    await select.selectOption('travel_ticket');
    check(await page.locator('.googolplex-empty').count() === 1, 'Empty intersection');
    await search.fill('');
    check((await names()).join(',') === 'Berlin', 'Switch category');
    await select.selectOption('');
    check(await page.locator('.googolplex-grid').textContent() === 'NEWS HOME', 'Reset returns home');
    await search.fill('/all');
    check((await names()).join(',') === 'Hold,GX,Berlin,Vault', 'Downloads ranking preserved');
    for (const width of [390, 900, 1440]) {
        await page.setViewportSize({width, height:900});
        await page.locator('.browser-window').evaluate((node, width) => {
            node.classList.toggle('is-window-maximized', width > 900);
            node.classList.toggle('browser-narrow', width <= 900);
        }, width);
        const bounds = await select.boundingBox();
        check(bounds.x >= 0 && bounds.x + bounds.width <= width, `Filter fits ${width}`);
        await select.selectOption('storage_upgrade');
        check((await names()).join(',') === 'Vault', `Filter works at ${width}`);
    }
    check(!errors.length, errors.join('\n'));
    return {result:'PASS', widths:[390,900,1440], pageErrors:errors};
}
