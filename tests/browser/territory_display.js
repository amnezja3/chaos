// Playwright MCP + python tools/territory_display_fixture.py, real Leaflet.
async (page) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8997/');
    await page.waitForFunction(() => window.playerAreaLayers?.length === 2);
    await page.getByRole('button', {name: 'Capture pillar / grow main'}).click();
    const grown = await page.evaluate(() => {
        const layer = territoryAreaLayers['453761'].layer;
        return {count: playerAreaLayers.length, onMap: map.hasLayer(layer),
            span: layer.getBounds().getEast() - layer.getBounds().getWest(),
            path: layer.getElement().getAttribute('d')};
    });
    if (grown.count !== 2 || !grown.onMap || grown.span <= 2 || !grown.path) {
        throw Error('large territory missing: ' + JSON.stringify(grown));
    }
    for (let i = 0; i < 3; i++) {
        await page.getByRole('button', {name: 'Reload snapshot'}).click();
    }
    if (await page.locator('.leaflet-overlay-pane path').count() !== 2) {
        throw Error('snapshot replacement lost or duplicated a polygon');
    }
    await page.setViewportSize({width: 390, height: 844});
    await page.evaluate(() => map.invalidateSize());
    await page.getByRole('button', {name: 'Reload snapshot'}).click();
    if (await page.locator('.leaflet-overlay-pane path').count() !== 2 || errors.length) {
        throw Error('mobile render failed: ' + JSON.stringify(errors));
    }
    return {grown, errors};
};
