"use strict";

const assert = require("assert");
const fs = require("fs");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const styles = fs.readFileSync("static/css/googleplex_news.css", "utf8");
const start = source.indexOf("const renderCatalog = () =>");
const end = source.indexOf("appsProjectionListener =", start);
const catalogSource = source.slice(start, end);

assert.match(catalogSource, /if \(!query\)[\s\S]*renderGoogleplexHome\(\)/);
assert.match(catalogSource, /const showAll = query === "\/all"/);
assert.match(catalogSource, /const editorialMode = showAll \|\| filteredMatches\.length >= 7/);
assert.match(catalogSource, /Number\(right\.downloads \|\| 0\) - Number\(left\.downloads \|\| 0\)/);
assert.match(catalogSource, /String\(left\.id \|\| left\.app_id/);
assert.match(catalogSource, /const cyclePosition = layoutIndex % 8/);
assert.match(catalogSource, /cyclePosition === 0 \? "hero" : cyclePosition <= 2 \? "medium" : "small"/);
assert.doesNotMatch(catalogSource, /gp-news-card gp-news-card/);
assert.match(catalogSource, /gp-search-grid gp-search-grid--editorial/);
assert.match(catalogSource, /googolplex-card gp-search-card gp-search-card--\$\{weight\}/);
assert.match(catalogSource, /className = 'gp-search-group'/);
assert.match(catalogSource, /Math\.floor\(layoutIndex \/ 8\)/);
assert.match(catalogSource, /class="gp-search-card__content"/);
assert.match(catalogSource, /class="gp-search-card__asset"/);
assert.match(catalogSource, /googolplex-card-footer gp-search-card__action/);
assert.match(catalogSource, /class="googolplex-card-icon"/);
assert.doesNotMatch(catalogSource, /safeAsset|visual_asset_url|asset_path|icon_url/);
assert.match(catalogSource, /\$\{proMeta\}[\s\S]*\$\{contractMeta\}[\s\S]*\$\{blockedHint\}/);
assert.match(catalogSource, /Jako\\u015b\\u0107/);
assert.match(catalogSource, /Niezawodno\\u015b\\u0107/);
assert.match(catalogSource, /Moc tw\\u00f3rcy/);
assert.match(catalogSource, /matches\.slice\(0, catalogVisibleLimit\)/);
assert.match(catalogSource, /catalogVisibleLimit \+= 24/);
assert.match(catalogSource, /gp-search-more/);
assert.match(source, /Szukaj aplikacji\.\.\.  \/all - pokaz wszystkie/);

assert.match(styles, /\.gp-search-card--hero/);
assert.match(styles, /\.gp-search-card--medium/);
assert.match(styles, /\.gp-search-card--small/);
assert.match(styles, /\.gp-search-group[\s\S]*grid-template-columns: repeat\(12/);
assert.match(styles, /\.gp-search-card__asset[\s\S]*border: 0;[\s\S]*background: none/);
assert.match(styles, /\.gp-search-card--hero[\s\S]*grid-template-areas: "content asset" "content action"/);
assert.match(styles, /\.gp-search-card--small[\s\S]*grid-template-areas: "asset content" "asset action"/);
assert.match(styles, /@container \(max-width: 767px\)[\s\S]*\.gp-search-grid,[\s\S]*\.gp-search-group \{ display: flex; flex-direction: column/);
assert.doesNotMatch(styles, /\.gp-search-card--small \.gp-search-card__summary \{ display: none/);
assert.doesNotMatch(styles, /\.gp-search-card__params > span:nth-child/);
assert.match(styles, /\.browser-window\.browser-narrow\.is-browser-googleplex \.googolplex-grid[\s\S]*overflow-y: visible !important/);
assert.doesNotMatch(styles.slice(styles.indexOf("/* Search keeps"), styles.indexOf(".gp-search-more")), /background-image\s*:/);

console.log("Googleplex search layout contract tests: OK");
