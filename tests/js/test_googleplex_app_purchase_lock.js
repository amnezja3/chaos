"use strict";

const assert = require("assert");
const fs = require("fs");

const source = fs.readFileSync("static/js/terminal.js", "utf8");

assert.match(source, /item\.purchase_confirmation === true/);
assert.match(source, /title: "POTWIERDZENIE ZAKUPU"/);
assert.match(source, /confirmLabel: "KUP I ZAINSTALUJ"/);
assert.match(source, /const projectedApps = Array\.isArray\(\(toolbarProfile \|\| \{\}\)\.apps\)/);
assert.match(source, /projectedApps\.some\(app => String\(app\?\.id/);
assert.match(source, /"ZAINSTALOWANO"/);
assert.match(source, /if \(installInFlight\) return/);
assert.match(source, /installButton\.disabled = true/);
assert.match(source, /const staleInstalledProjection = !isProduct/);
assert.match(source, /item\.installed === true[\s\S]*&& !installed/);
assert.match(source, /walletBalance = Number\(\(toolbarProfile \|\| \{\}\)\.hackcoins/);
assert.match(source, /chaos:apps-projection-updated/);
assert.match(source, /window\.dispatchEvent\(new CustomEvent/);
assert.match(source, /installed \? "Aplikacja juz kupiona\."/);
assert.match(source, /gp-search-card gp-search-card--\$\{weight\}\$\{installed \? " is-installed"/);
assert.match(source, /const dedupeGoogleplexCatalog = payload =>/);
assert.match(source, /catalog = dedupeGoogleplexCatalog\(catalogPayload\)/);

const purchaseCallStart = source.indexOf("showInstallAppProgress(\n                    item,");
const purchaseCallEnd = source.indexOf("\n                );", purchaseCallStart);
assert.ok(purchaseCallStart >= 0 && purchaseCallEnd > purchaseCallStart);
const postInstallCall = source.slice(purchaseCallStart, purchaseCallEnd);
assert.doesNotMatch(postInstallCall, /loadCatalog|getUserProfile|\/api\/profile|\/api\/catalog/);
assert.match(postInstallCall, /\n                    null,/);

const appsProjectionStart = source.indexOf("async function updateAppsView");
const appsProjectionEnd = source.indexOf("function updateCybernerDeltaViews", appsProjectionStart);
const appsProjectionSource = source.slice(appsProjectionStart, appsProjectionEnd);
assert.doesNotMatch(appsProjectionSource, /fetch\s*\(|\/api\/profile|\/api\/catalog|getUserProfile|refreshToolbarProfile/);

const catalogLoadStart = source.indexOf("async function loadCatalog()");
const catalogLoadEnd = source.indexOf("async function loadExchange()", catalogLoadStart);
const catalogLoadSource = source.slice(catalogLoadStart, catalogLoadEnd);
assert.match(catalogLoadSource, /fetch\('\/resources\.json'/);
assert.doesNotMatch(catalogLoadSource, /\/api\/profile|\/api\/catalog|getUserProfile|load_profile/);
assert.match(catalogLoadSource, /toolbarProfile \|\| \{\}\)\.hackcoins/);

console.log("Googleplex app purchase lock tests: OK");
