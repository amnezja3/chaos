'use strict';
const CACHE = 'chaos-install-156-4';
const OFFLINE = '/static/pwa/offline.html?v=156-4';
const PUBLIC = [OFFLINE, '/static/pwa/offline.js?v=156-4', '/static/pwa/install.css?v=156-4',
    '/static/pwa/icon-192.png?v=156-4', '/static/pwa/icon-512.png?v=156-4'];
self.addEventListener('install', event => event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    for (const url of PUBLIC) {
        const response = await fetch(new Request(url, {credentials: 'omit', cache: 'reload'}));
        if (!response.ok || response.redirected) throw new Error('public_asset_unavailable');
        await cache.put(url, response);
    }
})()));
// Updates wait for all old windows to close. Never force an in-game reload.
self.addEventListener('activate', event => event.waitUntil((async () => {
    for (const name of await caches.keys()) {
        if (name.startsWith('chaos-install-') && name !== CACHE) await caches.delete(name);
    }
})()));
self.addEventListener('fetch', event => {
    const request = event.request, url = new URL(request.url);
    if (request.method !== 'GET' || url.origin !== self.location.origin) return;
    if (PUBLIC.includes(url.pathname + url.search)) {
        event.respondWith(caches.match(request, {cacheName:CACHE}).then(response =>
            response || fetch(new Request(request, {credentials:'omit'}))));
    } else if (request.mode === 'navigate' && ['/launch', '/desktop', '/'].includes(url.pathname)) {
        event.respondWith(fetch(request).catch(async () =>
            (await caches.match(OFFLINE, {cacheName:CACHE})) || Response.error()));
    }
    // All APIs, private documents and mutations remain network-only.
});
