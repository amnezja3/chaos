const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const source = fs.readFileSync('static/js/terminal.js', 'utf8');
const helper = source.slice(source.indexOf('function applyGoogleplexDownloadUpdate('), source.indexOf('async function updateAppsView('));
const listener = source.slice(source.indexOf('    appsProjectionListener = event => {'), source.indexOf("    window.addEventListener('chaos:apps-projection-updated'"));
const context = {
    catalog: [{ id: 'intruderKicker', downloads: 0 }],
    googleplexDownloadUpdates: new Map(), term: { isConnected: true },
    activeBrowserTab: 'googleplex', search: { value: 'kicker' },
    toolbarProfile: {}, walletBalance: 0, renderBrowserWallet() {},
    renderCatalog() { context.rendered = context.catalog[0].downloads; }
};
vm.createContext(context);
vm.runInContext(helper + listener, context);
const send = downloads => context.appsProjectionListener({detail: {catalog_update: {app_id: 'intruderKicker', downloads}}});
send(1);
assert.equal(context.rendered, 1, 'same event renders updated count');
send(1);
send(0);
assert.equal(context.rendered, 1, 'retry and old responses cannot change the count');
context.activeBrowserTab = 'blacknet';
send(3);
assert.equal(context.catalog[0].downloads, 3, 'hidden tab cache is updated');
context.activeBrowserTab = 'googleplex';
context.renderCatalog();
assert.equal(context.rendered, 3, 'next search uses updated cache');
send(-1);
send('8');
assert.equal(context.catalog[0].downloads, 3);
const olderSnapshot = [{id: 'intruderKicker', downloads: 0}];
context.googleplexDownloadUpdates.forEach((downloads, app_id) => context.applyGoogleplexDownloadUpdate(olderSnapshot, {app_id, downloads}));
assert.equal(olderSnapshot[0].downloads, 3);
context.appsProjectionListener({detail: {reason: 'uninstall'}});
assert.equal(context.catalog[0].downloads, 3);
assert.match(source, /catalog_update: data\.catalog_update \|\| null/);
console.log('Googleplex live download update: PASS');
