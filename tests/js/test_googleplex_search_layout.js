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
assert.match(catalogSource, /layoutIndex === 0[\s\S]*\? "hero"/);
assert.match(catalogSource, /layoutIndex <= 2[\s\S]*\? "large"/);
assert.match(catalogSource, /layoutIndex <= 5 \? "medium" : "small"/);
assert.match(catalogSource, /gp-news-grid gp-catalog-editorial-grid/);
assert.match(catalogSource, /gp-news-card gp-news-card--\$\{weight\}/);
assert.match(catalogSource, /gp-catalog-classic-grid/);
assert.match(source, /Szukaj aplikacji\.\.\.  \/all - pokaz wszystkie/);

assert.match(styles, /\.gp-catalog-classic-grid/);
assert.match(styles, /\.gp-catalog-card\.gp-news-card--small \.gp-news-card__summary/);
assert.match(styles, /@container \(max-width: 767px\)[\s\S]*\.gp-catalog-classic-grid \{ grid-template-columns: minmax\(0, 1fr\); \}/);
assert.match(styles, /\.gp-news-grid \{ display: flex; flex-direction: column/);

console.log("Googleplex search layout contract tests: OK");
