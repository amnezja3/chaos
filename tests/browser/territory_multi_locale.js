// Playwright MCP; isolated tools/sprint_153_browser_fixture.py on port 8993.
// Real map reconciliation/binding and catalogs; Leaflet geometry is a test double.
async (page) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8993/frame');
    await page.waitForFunction(() => window.GhostLocale);
    const result = await page.evaluate(async () => {
        const assert = (condition, message) => { if (!condition) throw Error(message); };
        window.mapScanEffectState = {element: null};
        window.escapeMapText = value => {
            const node = document.createElement('span');
            node.textContent = String(value);
            return node.innerHTML;
        };
        const output = document.createElement('section');
        output.id = 'multi-conflict-test';
        document.body.append(output);
        window.map = {};
        window.territoryEngagementRegistry = {};
        window.territoryEngagementLayers = {};
        window.ensureTerritoryConflictRegistries = () => {};
        window.normalizeMapVertex = point => point;
        window.isSaneTerritoryPolygon = points => points.length >= 3;
        window.territoryPathRenderer = () => null;
        window.bindTerritoryMapContextMenu = () => {};
        window.L = {polygon: points => {
            const node = document.createElement('div');
            output.append(node);
            return {
                points, node,
                addTo() { return this; },
                on() {},
                bindTooltip(html) { this.node.innerHTML = html; return this; },
                setTooltipContent(html) { this.node.innerHTML = html; },
                setLatLngs(next) { this.points = next; },
                redraw() {}
            };
        }};
        await new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = '/map-workspace-locale.js';
            script.onload = resolve; script.onerror = reject;
            document.head.append(script);
        });
        await GhostLocale.changeLocale('en', false);
        const snapshot = {
            engagement_id: 'isolated-multi', snapshot_version: 1, geometry_version: 1,
            participant_usernames: ['main', 'run', '<third>'],
            geometry: [[[52, 21], [52.01, 21], [52, 21.01]]]
        };
        assert(reconcileTerritoryEngagementSnapshot(snapshot), 'new snapshot accepted');
        const layer = window.territoryEngagementLayers['isolated-multi:geometry:0'].layer;
        const initial = layer.node.innerText;
        assert(initial === 'Multi-party conflict\nParticipants: main, run, <third>', initial);
        assert(!layer.node.querySelector('third'), 'participant text is escaped');
        const updated = {...snapshot, snapshot_version: 2, geometry_version: 2,
            participant_usernames: ['main', 'run', 'neo1', 'kot2'],
            geometry: [[[52, 21], [52.02, 21], [52, 21.02]]]};
        assert(reconcileTerritoryEngagementSnapshot(updated), 'updated snapshot accepted');
        assert(layer === window.territoryEngagementLayers['isolated-multi:geometry:0'].layer, 'layer reused');
        assert(layer.points[1][0] === 52.02, 'geometry updated');
        const english = layer.node.innerText;
        assert(english === 'Multi-party conflict\nParticipants: main, run, neo1, kot2', english);
        await GhostLocale.changeLocale('pl', false);
        const polish = layer.node.innerText;
        assert(polish === 'Multi-konflikt\nUczestnicy: main, run, neo1, kot2', polish);
        await GhostLocale.changeLocale('en', false);
        assert(layer.node.innerText === english, 'existing tooltip changes back to EN');
        assert(reconcileTerritoryEngagementSnapshot(snapshot), 'stale snapshot handled');
        assert(layer.node.innerText === english, 'stale snapshot does not revert participants');
        assert(Object.keys(window.territoryEngagementLayers).length === 1, 'no duplicated layer');
        return {initial, updated: english, polish, status: 'PASS'};
    });
    if (errors.length) throw Error(errors.join('\n'));
    return {...result, errors};
}
