"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const styles = fs.readFileSync("static/css/googleplex_news.css", "utf8");
const renderStart = source.indexOf("const renderCatalog = () =>");
const renderEnd = source.indexOf("appsProjectionListener =", renderStart);
const catalogSource = source.slice(renderStart, renderEnd);
const groupStart = source.indexOf("const GOOGLEPLEX_SEARCH_SMALLS_PER_GROUP");
const groupEnd = source.indexOf("function createBrowser()", groupStart);
const groupSource = source.slice(groupStart, groupEnd);

const context = {};
vm.runInNewContext(`${groupSource}\nthis.groupResults = groupGoogleplexSearchResults;`, context);

const assertGroups = count => {
    const items = Array.from({ length: count }, (_, index) => ({ id: `app-${index}` }));
    const groups = context.groupResults(items);
    assert.deepStrictEqual(
        Array.from(groups, group => [
            group.hero && group.hero.id,
            Array.from(group.middle, item => item.id),
            Array.from(group.small, item => item.id)
        ]),
        Array.from({ length: Math.ceil(count / 6) }, (_, groupIndex) => {
            const offset = groupIndex * 6;
            return [
                `app-${offset}`,
                items.slice(offset + 1, offset + 3).map(item => item.id),
                items.slice(offset + 3, offset + 6).map(item => item.id)
            ];
        })
    );
};

[2, 3, 4, 6, 7, 12, 70].forEach(assertGroups);

assert.match(catalogSource, /if \(!query\)[\s\S]*renderGoogleplexHome\(\)/);
assert.match(catalogSource, /const showAll = query === "\/all"/);
assert.match(catalogSource, /const matches = showAll[\s\S]*Number\(right\.downloads \|\| 0\) - Number\(left\.downloads \|\| 0\)/);
assert.match(catalogSource, /String\(left\.id \|\| left\.app_id[\s\S]*localeCompare/);
assert.match(catalogSource, /const isSingleResult = matches\.length === 1/);
assert.match(catalogSource, /createProductCard\(matches\[0\], "single", 0\)/);
assert.match(catalogSource, /groupGoogleplexSearchResults\(matches\)/);
assert.match(catalogSource, /gp-search-group__hero/);
assert.match(catalogSource, /gp-search-group__middle/);
assert.match(catalogSource, /gp-search-group__small/);
assert.match(catalogSource, /gp-search-product gp-search-product--\$\{variant\}/);
assert.doesNotMatch(catalogSource, /gp-news-card gp-news-card/);

// One renderer retains the complete canonical card content for every variant.
assert.strictEqual((catalogSource.match(/card\.innerHTML = `/g) || []).length, 1);
assert.match(catalogSource, /\$\{proMeta\}[\s\S]*\$\{contractMeta\}[\s\S]*\$\{blockedHint\}/);
[
    "Poziom:", "Rodzina:", "Tryb:", "Tier:", "Map:", "Ops:", "Data:",
    "Waga:", "Instalacja:", "Jako\\u015b\\u0107:",
    "Niezawodno\\u015b\\u0107:", "Moc tw\\u00f3rcy:", "Moc:",
    "Cena sugerowana:"
].forEach(label => assert.ok(catalogSource.includes(label), `missing full-card field: ${label}`));
assert.match(catalogSource, /gp-search-product__icon/);
assert.match(catalogSource, /googolplex-card-icon/);
assert.doesNotMatch(catalogSource, /background-image|safeAsset|visual_asset_url|asset_path|icon_url/);

// Every result is passed to the group engine; /all cannot silently stop at 18.
assert.match(source, /GOOGLEPLEX_SEARCH_GROUP_SIZE = 1 \+ 2 \+ GOOGLEPLEX_SEARCH_SMALLS_PER_GROUP/);
assert.match(catalogSource, /groupGoogleplexSearchResults\(matches\)/);
assert.doesNotMatch(catalogSource, /visibleMatches|visibleLimit|catalogVisibleGroups|gp-search-more/);
assert.match(source, /Szukaj aplikacji\.\.\.  \/all - pokaz wszystkie/);

const searchCssStart = styles.indexOf("/* Search uses one full product renderer");
const searchCssEnd = styles.indexOf(".gp-news-stats", searchCssStart);
const searchStyles = styles.slice(searchCssStart, searchCssEnd);
assert.match(searchStyles, /\.gp-search-group[\s\S]*grid-template-columns: minmax\(390px, 5fr\) minmax\(0, 7fr\)/);
assert.match(searchStyles, /\.gp-search-group__middle \{ grid-template-columns: minmax\(0, 3fr\) minmax\(0, 4fr\)/);
assert.match(searchStyles, /\.gp-search-group__small \{ grid-template-columns: minmax\(0, 2fr\) minmax\(0, 3fr\) minmax\(0, 2fr\)/);
assert.match(searchStyles, /\.gp-search-product__icon[\s\S]*border: 0;[\s\S]*background: none/);
assert.match(searchStyles, /\.gp-search-product--single/);
assert.doesNotMatch(searchStyles, /background-image\s*:|line-clamp|display:\s*none/);
assert.match(styles, /@container \(max-width: 1199px\)[\s\S]*\.gp-search-group \{ display: block; \}/);
assert.match(styles, /@container \(max-width: 767px\)[\s\S]*\.gp-search-group__[\s\S]*flex-direction: column/);
assert.match(styles, /\.browser-window\.browser-narrow\.is-browser-googleplex \.googolplex-grid[\s\S]*overflow-y: visible !important/);

// Per-card presentation never adds a profile/catalog request or network path.
const cardStart = catalogSource.indexOf("const createProductCard =");
const cardEnd = catalogSource.indexOf("\n        if (isSingleResult)", cardStart);
const cardSource = catalogSource.slice(cardStart, cardEnd);
assert.doesNotMatch(cardSource, /fetch\s*\(|\/api\/profile|get_profile|list_profiles|loadCatalog\s*\(/);

console.log("Googleplex search presentation repair tests: OK");
