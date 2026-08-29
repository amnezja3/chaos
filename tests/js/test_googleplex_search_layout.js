"use strict";

const assert = require("assert");
const fs = require("fs");

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

const renderStart = terminalSource.indexOf("const renderCatalog = () =>");
const renderEnd = terminalSource.indexOf("appsProjectionListener =", renderStart);
assert.ok(renderStart >= 0 && renderEnd > renderStart, "Googleplex catalog renderer missing");
const catalogSource = terminalSource.slice(renderStart, renderEnd);

// Data selection remains unchanged: Home for empty query, all public catalog
// entries for /all, deterministic /all ranking and source order for queries.
assert.match(catalogSource, /if \(!query\)[\s\S]*renderGoogleplexHome\(\)/);
assert.match(catalogSource, /const showAll = query === "\/all"/);
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
    /const requirementsMeta[\s\S]*const parameterRows[\s\S]*const parametersMeta[\s\S]*const blockedHint/
);
assert.match(
    catalogSource,
    /\$\{requirementsMeta\}[\s\S]*\$\{parametersMeta\}[\s\S]*\$\{blockedHint\}/
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
assert.match(catalogSource, /gp-search-product__icon/);
assert.match(catalogSource, /gp-search-product__icon-symbol/);
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
    /\.browser-window\.is-window-maximized\.is-browser-googleplex \.gp-search-group\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 5fr\) minmax\(0, 7fr\)/
);
assert.match(
    presentationStyles,
    /\.browser-window\.is-window-maximized\.is-browser-googleplex \.gp-search-group__middle\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 3fr\) minmax\(0, 4fr\)/
);
assert.match(
    presentationStyles,
    /\.browser-window\.is-window-maximized\.is-browser-googleplex \.gp-search-group__small\s*\{[\s\S]*?grid-template-columns:\s*minmax\(0, 2fr\) minmax\(0, 3fr\) minmax\(0, 2fr\)/
);
assert.match(
    presentationStyles,
    /@container \(max-width: 767px\)[\s\S]*?\.gp-search-group__[\s\S]*?flex-direction:\s*column/
);
assert.match(
    presentationStyles,
    /\.browser-window\.browser-narrow\.is-browser-googleplex \.googolplex-grid\s*\{[\s\S]*?overflow:\s*visible !important/
);
assert.match(
    presentationStyles,
    /\.gp-search-product__icon[\s\S]*border:\s*0[\s\S]*background:\s*none/
);
assert.doesNotMatch(presentationStyles, /background-image\s*:|line-clamp:\s*[1-9]|display:\s*none/);
assert.doesNotMatch(newsStyles, /\.gp-search-group\b|\.gp-search-product\b/);
assert.doesNotMatch(catalogSource, /class="gp-home|class="googolplex-card/);

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
