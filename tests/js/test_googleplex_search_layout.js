"use strict";

const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const presentation = require("../../static/js/googleplex_search_presentation.js");

const terminalSource = fs.readFileSync("static/js/terminal.js", "utf8");
const presentationSource = fs.readFileSync(
    "static/js/googleplex_search_presentation.js",
    "utf8"
);
const presentationStyles = fs.readFileSync(
    "static/css/googleplex_search.css",
    "utf8"
);
const newsStyles = fs.readFileSync("static/css/googleplex_news.css", "utf8");
const socketDirectory = path.join(
    "static",
    "images",
    "googleplx",
    "icons",
    "app-sockets"
);
const socketAssets = [
    "01_icon_socket_core.svg",
    "02_icon_socket_side.svg",
    "03_icon_socket_compact.svg",
    "04_icon_socket_hex.svg",
    "05_icon_socket_target.svg"
];

class FakeClassList {
    constructor(node) {
        this.node = node;
    }

    values() {
        return new Set(String(this.node.className || "").split(/\s+/).filter(Boolean));
    }

    toggle(name, force) {
        const values = this.values();
        const enabled = force === undefined ? !values.has(name) : Boolean(force);
        if (enabled) values.add(name);
        else values.delete(name);
        this.node.className = Array.from(values).join(" ");
        return enabled;
    }

    contains(name) {
        return this.values().has(name);
    }
}

class FakeNode {
    constructor(ownerDocument, tagName) {
        this.ownerDocument = ownerDocument;
        this.tagName = String(tagName || "").toUpperCase();
        this.className = "";
        this.classList = new FakeClassList(this);
        this.children = [];
        this.dataset = {};
        this.attributes = {};
        this.parentNode = null;
    }

    appendChild(node) {
        assert.ok(node instanceof FakeNode, "mount must append DOM nodes");
        node.parentNode = this;
        this.children.push(node);
        return node;
    }

    append(...nodes) {
        nodes.forEach(node => this.appendChild(node));
    }

    replaceChildren(...nodes) {
        this.children.forEach(node => {
            node.parentNode = null;
        });
        this.children = [];
        this.append(...nodes);
    }

    setAttribute(name, value) {
        this.attributes[String(name)] = String(value);
    }
}

class FakeDocument {
    createElement(tagName) {
        return new FakeNode(this, tagName);
    }
}

const collect = (node, predicate, output = []) => {
    if (predicate(node)) output.push(node);
    node.children.forEach(child => collect(child, predicate, output));
    return output;
};

const itemsFor = count => Array.from(
    { length: count },
    (_, index) => Object.freeze({ id: `app-${index}`, ordinal: index })
);

const expectedGroups = count => Array.from(
    { length: Math.ceil(count / presentation.GROUP_SIZE) },
    (_, groupIndex) => {
        const offset = groupIndex * presentation.GROUP_SIZE;
        return {
            hero: count > offset ? `app-${offset}` : null,
            middle: Array.from(
                { length: Math.max(0, Math.min(2, count - offset - 1)) },
                (_unused, index) => `app-${offset + index + 1}`
            ),
            small: Array.from(
                { length: Math.max(0, Math.min(3, count - offset - 3)) },
                (_unused, index) => `app-${offset + index + 3}`
            )
        };
    }
);

const assertGroupPlan = count => {
    const items = Object.freeze(itemsFor(count));
    const before = items.map(item => item.id);
    const groups = presentation.group(items);
    const actual = groups.map(group => ({
        hero: group.hero && group.hero.id,
        middle: group.middle.map(item => item.id),
        small: group.small.map(item => item.id)
    }));

    assert.deepStrictEqual(actual, expectedGroups(count), `invalid group plan for ${count}`);
    assert.deepStrictEqual(items.map(item => item.id), before, "grouping must not mutate input order");
};

const assertMounted = count => {
    const documentRef = new FakeDocument();
    const root = documentRef.createElement("main");
    root.appendChild(documentRef.createElement("i"));
    const items = Object.freeze(itemsFor(count));
    const calls = [];
    const createCard = (item, variant, layoutIndex) => {
        const card = documentRef.createElement("article");
        card.className = `gp-search-product gp-search-product--${variant}`;
        card.dataset.appId = item.id;
        card.dataset.variant = variant;
        card.dataset.layoutIndex = String(layoutIndex);
        calls.push({ id: item.id, variant, layoutIndex });
        return card;
    };

    const result = presentation.mount(root, items, createCard);
    const cards = collect(root, node => node.tagName === "ARTICLE");
    const groups = collect(root, node => node.classList.contains("gp-search-group"));

    assert.strictEqual(result.rendered_count, count, `reported rendered count for ${count}`);
    assert.strictEqual(cards.length, count, `DOM card count for ${count}`);
    assert.strictEqual(calls.length, count, `card factory count for ${count}`);
    assert.deepStrictEqual(cards.map(card => card.dataset.appId), items.map(item => item.id));
    assert.deepStrictEqual(calls.map(call => call.layoutIndex), items.map(item => item.ordinal));

    if (count === 1) {
        assert.strictEqual(result.single, true);
        assert.strictEqual(result.group_count, 0);
        assert.strictEqual(groups.length, 0);
        assert.strictEqual(calls[0].variant, "single");
        assert.strictEqual(root.classList.contains("gp-search-results--single"), true);
    } else {
        const expectedGroupCount = Math.ceil(count / presentation.GROUP_SIZE);
        assert.strictEqual(result.single, false);
        assert.strictEqual(result.group_count, expectedGroupCount);
        assert.strictEqual(groups.length, expectedGroupCount);
        assert.strictEqual(root.classList.contains("gp-search-results--single"), false);
    }

    return { root, cards, groups, calls, result };
};

assert.strictEqual(presentation.GROUP_SIZE, 6);
assert.strictEqual(presentation.MIDDLE_PER_GROUP, 2);
assert.strictEqual(presentation.SMALL_PER_GROUP, 3);

// The mandatory regression matrix exercises both the pure plan and real DOM
// mounting. In particular, 70 must result in 70 reachable card nodes rather
// than merely reporting 70 matches in the header.
[0, 1, 2, 3, 4, 6, 7, 12, 70].forEach(count => {
    assertGroupPlan(count);
    assertMounted(count);
});

const zero = assertMounted(0);
assert.strictEqual(zero.root.children.length, 0, "empty mount must clear stale results");
assert.strictEqual(zero.result.group_count, 0);

const seven = assertMounted(7);
assert.deepStrictEqual(
    seven.calls.filter(call => call.variant === "hero").map(call => call.id),
    ["app-0", "app-6"],
    "every group must restart with HERO"
);

const seventy = assertMounted(70);
assert.strictEqual(seventy.groups.length, 12);
assert.strictEqual(seventy.calls.filter(call => call.variant === "hero").length, 12);
assert.strictEqual(seventy.calls.filter(call => call.variant === "middle").length, 24);
assert.strictEqual(seventy.calls.filter(call => call.variant === "small").length, 34);
assert.deepStrictEqual(
    seventy.calls.slice(-4).map(call => [call.id, call.variant]),
    [
        ["app-66", "hero"],
        ["app-67", "middle"],
        ["app-68", "middle"],
        ["app-69", "small"]
    ]
);

assert.throws(
    () => presentation.mount(null, [], () => null),
    /googleplex_search_root_missing/
);
assert.throws(
    () => presentation.mount(new FakeDocument().createElement("main"), [], null),
    /googleplex_search_card_factory_missing/
);

// Presentation transport is standalone, deterministic and network-free.
assert.doesNotMatch(
    presentationSource,
    /fetch\s*\(|XMLHttpRequest|\/api\/profile|\/api\/catalog|get_profile|list_profiles/
);
assert.match(presentationSource, /root\.GoogleplexSearchPresentation = api/);
assert.match(presentationSource, /module\.exports = api/);

// User-selected icons are canonical text. Emoji, runes and other Unicode
// symbols must survive the same escaping path used by the card renderer; only
// markup metacharacters may change.
const escapeStart = terminalSource.indexOf("function escapeHTML(value)");
const escapeEnd = terminalSource.indexOf("function sanitizeToastHTML", escapeStart);
assert.ok(escapeStart >= 0 && escapeEnd > escapeStart, "escapeHTML helper missing");
const escapeSource = terminalSource.slice(escapeStart, escapeEnd);
const escapeIcon = value => {
    const sandbox = { __icon: value };
    vm.runInNewContext(
        `${escapeSource}\nglobalThis.__escaped = escapeHTML(globalThis.__icon);`,
        sandbox
    );
    return sandbox.__escaped;
};
[
    "\u{1F47B}", // emoji
    "\u16B1",    // rune
    "\u232C",    // single Unicode symbol
    "\u{1F6F0}\uFE0F" // multi-codepoint emoji with variation selector
].forEach(icon => {
    assert.strictEqual(escapeIcon(icon), icon, `user icon must be preserved: ${icon}`);
    assert.strictEqual(escapeIcon(icon).includes("\uFFFD"), false);
});
assert.strictEqual(
    escapeIcon('<img src=x onerror="boom">'),
    "&lt;img src=x onerror=&quot;boom&quot;&gt;",
    "creator icon remains text and cannot inject markup"
);

// MAP / OPS / DATA can carry long canonical lists. Exercise the production
// list normalizer itself and require every token to remain present and ordered.
const listStart = terminalSource.indexOf("const googleplexList = (value) =>");
const listEnd = terminalSource.indexOf("const googleplexSearchText", listStart);
assert.ok(listStart >= 0 && listEnd > listStart, "Googleplex list normalizer missing");
const listSource = terminalSource.slice(listStart, listEnd);
const normalizeCanonicalList = value => {
    const sandbox = { __list: value };
    vm.runInNewContext(
        `${listSource}\nglobalThis.__formatted = googleplexList(globalThis.__list);`,
        sandbox
    );
    return Array.from(sandbox.__formatted);
};
const longMetadataFixtures = {
    map: [
        "scan_ports",
        "scan_hotspots",
        "territory_conflict_projection_north_sector",
        "world_map_player_actor_focus",
        "ghostnetwork_public_connection_overlay",
        "foreign_territory_boundary_analysis"
    ],
    ops: [
        "wifi_scanner",
        "persistent_sniffer",
        "vehicle_tracking_with_position_history",
        "credential_extraction_and_validation",
        "conflict_pillar_terminal_operation"
    ],
    data: [
        "internal_recon_state",
        "device_logs",
        "hotspot_database",
        "encrypted_credentials_archive",
        "operator_position_history",
        "\u{1F47B}_unicode_fact_reference"
    ]
};
Object.entries(longMetadataFixtures).forEach(([field, values]) => {
    const normalized = normalizeCanonicalList(values);
    assert.deepStrictEqual(normalized, values, `${field} must not be truncated or reordered`);
    values.forEach(value => assert.ok(normalized.includes(value), `${field} lost ${value}`));
});
assert.doesNotMatch(listSource, /\.slice\s*\(|substring\s*\(|substr\s*\(|\.\.\./);

// Long identifiers retain their exact text and receive legal break points only
// after canonical separators. This prevents scanner_reco|n style wrapping.
const breakStart = terminalSource.indexOf("const googleplexBreakableText =");
const breakEnd = terminalSource.indexOf("const googleplexIconSocketAssets", breakStart);
assert.ok(breakStart >= 0 && breakEnd > breakStart, "breakable identifier helper missing");
const breakSource = terminalSource.slice(breakStart, breakEnd);
const renderBreakable = value => {
    const sandbox = { __value: value };
    vm.runInNewContext(
        `${escapeSource}\n${breakSource}\nglobalThis.__rendered = googleplexBreakableText(globalThis.__value);`,
        sandbox
    );
    return sandbox.__rendered;
};
assert.strictEqual(
    renderBreakable("system_product,scanner_recon"),
    "system_<wbr>product,<wbr>scanner_<wbr>recon"
);
assert.strictEqual(renderBreakable("travel_ticket"), "travel_<wbr>ticket");
assert.strictEqual(
    renderBreakable('<img src=x onerror="boom">'),
    "&lt;img src=x onerror=&quot;boom&quot;&gt;"
);

const scrollHelperStart = terminalSource.indexOf("const getGoogleplexScrollSurface =");
const scrollHelperEnd = terminalSource.indexOf("const renderBrowserWallet", scrollHelperStart);
assert.ok(scrollHelperStart >= 0 && scrollHelperEnd > scrollHelperStart, "Googleplex scroll lifecycle helper missing");
const scrollHelperSource = terminalSource.slice(scrollHelperStart, scrollHelperEnd);
assert.match(scrollHelperSource, /overflowY/);
assert.match(scrollHelperSource, /return results/);
assert.match(scrollHelperSource, /return googleplexShell/);
assert.match(scrollHelperSource, /googleplexRenderedViewKey !== viewKey/);
assert.match(scrollHelperSource, /surface\.scrollTop = viewChanged \? 0 : previousTop/);
assert.match(scrollHelperSource, /surface\.scrollLeft = viewChanged \? 0 : previousLeft/);
assert.match(scrollHelperSource, /googleplexHomeScrollTop = Math\.max/);

const runScrollLifecycle = mode => {
    const resultsNode = {
        scrollTop: mode === "desktop" ? 420 : 0,
        scrollLeft: mode === "desktop" ? 17 : 0,
        querySelector: () => ({ className: "gp-home" })
    };
    const shellNode = {
        scrollTop: mode === "mobile" ? 360 : 0,
        scrollLeft: mode === "mobile" ? 11 : 0
    };
    const sandbox = {
        __results: resultsNode,
        __shell: shellNode,
        __mode: mode
    };
    vm.runInNewContext(`
        const results = globalThis.__results;
        const googleplexShell = globalThis.__shell;
        let googleplexRenderedViewKey = "all";
        let googleplexHomeScrollTop = 0;
        const window = {
            getComputedStyle(node) {
                if (globalThis.__mode === "desktop") {
                    return { overflowY: node === results ? "auto" : "visible" };
                }
                return { overflowY: node === googleplexShell ? "auto" : "visible" };
            }
        };
        const requestAnimationFrame = callback => callback();
        ${scrollHelperSource}
        globalThis.__begin = beginGoogleplexCatalogView;
        globalThis.__rememberHome = rememberGoogleplexHomeScroll;
        globalThis.__homeTop = () => googleplexHomeScrollTop;
    `, sandbox);
    return sandbox;
};

const desktopScroll = runScrollLifecycle("desktop");
desktopScroll.__begin("query:bilet")();
assert.strictEqual(desktopScroll.__results.scrollTop, 0, "new desktop query resets result scroller");
assert.strictEqual(desktopScroll.__results.scrollLeft, 0);
desktopScroll.__results.scrollTop = 233;
desktopScroll.__begin("query:bilet")();
assert.strictEqual(desktopScroll.__results.scrollTop, 233, "same query rerender preserves desktop scroll");

const mobileScroll = runScrollLifecycle("mobile");
mobileScroll.__begin("query:bilet")();
assert.strictEqual(mobileScroll.__shell.scrollTop, 0, "new mobile query resets shell scroller");
mobileScroll.__shell.scrollTop = 187;
mobileScroll.__rememberHome();
assert.strictEqual(mobileScroll.__homeTop(), 187, "Home remembers the canonical mobile shell scroll");

const renderStart = terminalSource.indexOf("const renderCatalog = () =>");
const renderEnd = terminalSource.indexOf("appsProjectionListener =", renderStart);
assert.ok(renderStart >= 0 && renderEnd > renderStart, "Googleplex catalog renderer missing");
const catalogSource = terminalSource.slice(renderStart, renderEnd);

// Data selection remains unchanged: Home for empty query, all public catalog
// entries for /all, deterministic /all ranking and source order for queries.
assert.match(catalogSource, /if \(!query\)[\s\S]*renderGoogleplexHome\(\)/);
assert.match(catalogSource, /const showAll = query === "\/all"/);
assert.match(catalogSource, /beginGoogleplexCatalogView\(showAll \? "all" : `query:\$\{query\}`\)/);
assert.match(catalogSource, /settleCatalogScroll\(\)/);
assert.match(
    catalogSource,
    /const matches = showAll[\s\S]*filteredMatches\.slice\(\)\.sort[\s\S]*Number\(right\.downloads \|\| 0\) - Number\(left\.downloads \|\| 0\)/
);
assert.match(catalogSource, /String\(left\.id \|\| left\.app_id[\s\S]*localeCompare/);
assert.doesNotMatch(
    catalogSource,
    /visibleMatches|visibleLimit|catalogVisibleGroups|gp-search-more|\.slice\(0\s*,\s*(?:12|18|24)\)/
);

// The clean rewrite delegates layout to one standalone DOM engine and passes
// the complete ordered list. It must not retain a second inline group system.
assert.match(
    catalogSource,
    /GoogleplexSearchPresentation|googleplexSearchPresentation|searchPresentation/
);
assert.match(catalogSource, /\.mount\(\s*cardsRoot\s*,\s*matches\s*,\s*createProductCard\s*\)/);
assert.doesNotMatch(terminalSource, /function groupGoogleplexSearchResults\s*\(/);

// One renderer retains the complete canonical card content for single, hero,
// middle and small; the variant is presentation-only.
assert.strictEqual((catalogSource.match(/card\.innerHTML = `/g) || []).length, 1);
assert.match(catalogSource, /gp-search-product--\$\{variant\}/);
assert.match(
    catalogSource,
    /const requirementsMeta[\s\S]*const coreParameterRows[\s\S]*const technicalParameterRows[\s\S]*const metricParameterRows[\s\S]*const coreParametersMeta[\s\S]*const technicalParametersMeta[\s\S]*const metricParametersMeta[\s\S]*const purchaseState/
);
assert.match(
    catalogSource,
    /\$\{requirementsMeta\}[\s\S]*\$\{coreParametersMeta\}[\s\S]*\$\{technicalParametersMeta\}[\s\S]*\$\{metricParametersMeta\}[\s\S]*\$\{purchaseState\}/
);
[
    '"Poziom"',
    '"Rodzina"',
    '"Tryb"',
    '"Tier"',
    '"Map"',
    '"Ops"',
    '"Data"',
    '"Waga"',
    '"Instalacja"',
    '"Jako\\u015b\\u0107"',
    '"Niezawodno\\u015b\\u0107"',
    '"Moc tw\\u00f3rcy"',
    '"Moc"',
    '"Cena sugerowana"'
].forEach(label => {
    assert.ok(catalogSource.includes(label), `missing full-card field: ${label}`);
});
assert.match(catalogSource, /item\.description \|\| ["']Brak opisu\.["']/);
[
    "gp-app-card__header",
    "gp-app-status-strip",
    "gp-app-card__body",
    "gp-app-icon-stage",
    "gp-app-icon-stage__socket",
    "gp-app-icon-stage__user-icon",
    "gp-app-spec-panel",
    "gp-app-purchase-state",
    "gp-app-market-footer"
].forEach(className => {
    assert.ok(catalogSource.includes(className), `missing card presentation class: ${className}`);
});
assert.match(
    catalogSource,
    /gp-app-icon-stage__user-icon[^>]*>\s*\$\{escapeHTML\(iconValue\)\}\s*</,
    "the foreground layer must render the exact escaped creator icon"
);
assert.match(
    catalogSource,
    /<img class="gp-app-icon-stage__socket" src="\$\{escapeHTML\(iconSocketAsset\)\}" alt="" draggable="false">/,
    "the code-owned SVG socket must remain a separate background image layer"
);
const statusMarkupStart = catalogSource.indexOf("const requirementsMeta");
const statusMarkupEnd = catalogSource.indexOf("const coreParameterRows", statusMarkupStart);
const statusMarkup = catalogSource.slice(statusMarkupStart, statusMarkupEnd);
assert.match(statusMarkup, /gp-app-status-strip__item/);
assert.match(statusMarkup, /<small>LVL<\/small>[\s\S]*<small>RESPECT<\/small>[\s\S]*<small>RISK<\/small>/);
assert.doesNotMatch(statusMarkup, /<button\b/, "LVL / RESPECT / RISK are status, not actions");
assert.match(catalogSource, /values:\s*googleplexList\(item\.map_actions\)/);
assert.match(catalogSource, /values:\s*googleplexList\(item\.operation_types\)/);
assert.match(catalogSource, /values:\s*googleplexList\(item\.resource_types\)/);
assert.match(catalogSource, /values\.map\(value => `<span class="gp-app-spec-panel__token">\$\{googleplexBreakableText\(value\)\}<\/span>`\)/);
assert.match(catalogSource, /installed \? "Aplikacja juz kupiona\."/);
assert.match(catalogSource, /installed \? \(isProduct \? "KUPIONO" : "ZAINSTALOWANO"\)/);
assert.doesNotMatch(catalogSource, /line-clamp|safeAsset|visual_asset_url|asset_path|icon_url/);

const cardStart = catalogSource.indexOf("const createProductCard =");
const returnCard = catalogSource.indexOf("return card;", cardStart);
assert.ok(cardStart >= 0 && returnCard > cardStart, "single card renderer missing");
const cardSource = catalogSource.slice(cardStart, returnCard);
assert.doesNotMatch(
    cardSource,
    /fetch\s*\(|\/api\/profile|\/api\/catalog|get_profile|list_profiles|loadCatalog\s*\(/
);

// Search CSS is owned by a standalone stylesheet. Icon geometry cannot add a
// panel/background, and responsive rules cannot hide or truncate card data.
assert.match(presentationStyles, /\.gp-search-group\b/);
assert.match(presentationStyles, /\.gp-search-group__hero\b/);
assert.match(presentationStyles, /\.gp-search-group__middle\b/);
assert.match(presentationStyles, /\.gp-search-group__small\b/);
assert.match(presentationStyles, /\.gp-search-product--single\b/);
assert.match(presentationStyles, /\.gp-search-product--hero\b/);
assert.match(presentationStyles, /\.gp-search-product--middle\b/);
assert.match(presentationStyles, /\.gp-search-product--small\b/);
assert.match(
    presentationStyles,
    /\.gp-search-view\s*\{[\s\S]*?width:\s*100%[\s\S]*?max-width:\s*none/
);
assert.match(
    presentationStyles,
    /\.browser-window\.is-window-maximized\.is-browser-googleplex \.gp-search-group\s*\{[\s\S]*?grid-template-columns:\s*repeat\(4, minmax\(0, 1fr\)\)/
);
assert.match(
    presentationStyles,
    /\.browser-window\.is-window-maximized\.is-browser-googleplex \.gp-search-group__hero,[\s\S]*?\.gp-search-group__small\s*\{[\s\S]*?display:\s*contents/
);
assert.match(
    presentationStyles,
    /\.browser-window\.is-window-maximized\.is-browser-googleplex \.gp-search-product--hero\s*\{[\s\S]*?grid-column:\s*span 3/
);
assert.match(
    presentationStyles,
    /\.browser-window:not\(\.is-window-maximized\):not\(\.browser-narrow\)\.is-browser-googleplex \.googolplex-shell\s*\{[\s\S]*?grid-template-columns:/
);
assert.match(
    presentationStyles,
    /\.browser-window:not\(\.is-window-maximized\):not\(\.browser-narrow\)\.is-browser-googleplex \.googolplex-search\s*\{[\s\S]*?grid-column:\s*2[\s\S]*?grid-row:\s*1/
);
assert.match(
    presentationStyles,
    /@container \(max-width: 767px\)[\s\S]*?\.gp-search-group__[\s\S]*?flex-direction:\s*column/
);
assert.match(
    presentationStyles,
    /\.browser-window\.browser-narrow\.is-browser-googleplex \.googolplex-grid\s*\{[\s\S]*?overflow:\s*visible !important/
);
[
    ".gp-app-card__header",
    ".gp-app-status-strip",
    ".gp-app-card__body",
    ".gp-app-icon-stage",
    ".gp-app-icon-stage__socket",
    ".gp-app-icon-stage__user-icon",
    ".gp-app-spec-panel",
    ".gp-app-purchase-state",
    ".gp-app-market-footer"
].forEach(selector => {
    assert.ok(presentationStyles.includes(selector), `missing card selector: ${selector}`);
});

// The socket is a decorative background layer. The creator-owned foreground
// icon itself stays transparent, borderless and free of image replacement or
// visual filters.
const userIconRule = presentationStyles.match(
    /\.gp-app-icon-stage__user-icon(?:\s*,[^\{]*)?\s*\{([^}]*)\}/
);
assert.ok(userIconRule, "foreground user-icon CSS rule missing");
assert.match(userIconRule[1], /border:\s*0(?:\s+[^;]+)?;/);
assert.match(userIconRule[1], /background:\s*none\s*;/);
assert.doesNotMatch(
    userIconRule[1],
    /background-image\s*:|url\s*\(|filter\s*:|mask(?:-image)?\s*:|(?:^|[;\s])content\s*:/
);
assert.doesNotMatch(presentationStyles, /line-clamp:\s*[1-9]/);
[
    "gp-app-card__header",
    "gp-app-status-strip",
    "gp-app-card__body",
    "gp-app-icon-stage",
    "gp-app-spec-panel",
    "gp-app-purchase-state",
    "gp-app-market-footer"
].forEach(className => {
    const hiddenRule = new RegExp(`\\.${className}(?![-_])[^{}]*\\{[^}]*display:\\s*none`);
    assert.doesNotMatch(presentationStyles, hiddenRule, `${className} cannot be hidden`);
});
assert.match(
    presentationStyles,
    /\.gp-app-spec-panel__token\s*\{[\s\S]*?overflow-wrap:\s*normal[\s\S]*?word-break:\s*normal/,
    "technical identifiers may only wrap at renderer-owned opportunities"
);
assert.doesNotMatch(presentationStyles, /min-height:\s*360px/);
assert.doesNotMatch(presentationStyles, /\.gp-search-product\s*\{[^}]*overflow-wrap:\s*anywhere/);
assert.match(presentationStyles, /:where\(\.gp-search-view, \.gp-search-view \*\)[\s\S]*?box-sizing:\s*border-box/);
assert.match(
    presentationStyles,
    /\.gp-app-icon-stage\s*\{[\s\S]*?display:\s*flex[\s\S]*?align-items:\s*center[\s\S]*?justify-content:\s*center/
);
assert.match(
    presentationStyles,
    /\.gp-app-icon-stage__user-icon\s*\{[\s\S]*?display:\s*flex[\s\S]*?align-items:\s*center[\s\S]*?justify-content:\s*center/
);
assert.doesNotMatch(presentationStyles, /overflow-x:\s*hidden/);
assert.doesNotMatch(newsStyles, /\.gp-search-group\b|\.gp-search-product\b/);
assert.doesNotMatch(catalogSource, /class="gp-home|class="googolplex-card/);

// Five local, lightweight SVG sockets form the visual holder. They may not
// embed an application icon, raster image, executable markup or remote asset.
socketAssets.forEach(fileName => {
    const assetPath = path.join(socketDirectory, fileName);
    assert.ok(fs.existsSync(assetPath), `missing Googleplex icon socket: ${fileName}`);
    const stats = fs.statSync(assetPath);
    assert.ok(stats.size > 0 && stats.size <= 32768, `${fileName} must remain lightweight`);
    const svg = fs.readFileSync(assetPath, "utf8");
    assert.match(svg, /<svg\b/i, `${fileName} must be SVG`);
    assert.match(svg, /viewBox\s*=\s*["'][^"']+["']/i, `${fileName} needs a viewBox`);
    assert.match(
        svg,
        /currentColor|var\(--|(?:stroke|fill)=["']#(?:fff|ffffff)["']/i,
        `${fileName} must be monochrome/CSS-tintable`
    );
    assert.doesNotMatch(svg, /<text\b|<image\b|<script\b|<foreignObject\b/i);
    assert.doesNotMatch(svg, /(?:href|xlink:href)\s*=\s*["'](?:https?:|\/\/|data:)/i);
    assert.doesNotMatch(svg, /\son(?:load|error|click|mouseover|focus)\s*=/i);
    assert.ok(
        presentationStyles.includes(fileName) || terminalSource.includes(fileName),
        `${fileName} is generated but not wired into the card system`
    );
});

for (const templatePath of [
    "templates/index.html",
    "templates/linux.html",
    "templates/linux_old.html"
]) {
    const template = fs.readFileSync(templatePath, "utf8");
    const cssIndex = template.indexOf("css/googleplex_search.css");
    const presentationIndex = template.indexOf("js/googleplex_search_presentation.js");
    const terminalIndex = template.indexOf("js/terminal.js");
    assert.ok(cssIndex >= 0, `${templatePath} must load standalone Search CSS`);
    assert.ok(presentationIndex >= 0, `${templatePath} must load standalone Search JS`);
    assert.ok(
        presentationIndex < terminalIndex,
        `${templatePath} must load Search presentation before terminal.js`
    );
}

assert.match(terminalSource, /Szukaj aplikacji\.\.\.  \/all - pokaz wszystkie/);

console.log("Googleplex search presentation repair tests: OK");
