/* Same-origin, explicitly enrolled frames only; no reload or gameplay messages. */
(function (root) {
    'use strict';
    const runtime = root.GhostLocale;
    if (!runtime) return;
    const origin = root.location.origin;
    const token = root.crypto.randomUUID();
    let revision = 0, received = -1;
    const enrolled = new Map();
    const send = (frame, nonce) => frame.postMessage({type:'ghost:locale:commit', nonce,
        version:runtime.contentVersion, revision, locale:runtime.getLocale(), bundle:runtime.getBundle()}, origin);
    root.addEventListener('message', event => {
        if (event.origin !== origin || !event.data || typeof event.data !== 'object') return;
        const message = event.data;
        if (message.type === 'ghost:locale:ready') {
            const frame = [...document.querySelectorAll('iframe[data-ghost-locale-frame]')].find(item => item.contentWindow === event.source);
            if (!frame || typeof message.nonce !== 'string' || message.nonce.length > 100 || message.version !== runtime.contentVersion) return;
            enrolled.set(event.source, message.nonce);
            send(event.source, message.nonce);
        } else if (message.type === 'ghost:locale:commit' && root.parent !== root && event.source === root.parent) {
            if (message.nonce !== token || message.version !== runtime.contentVersion || !Number.isInteger(message.revision) || message.revision <= received) return;
            if (message.bundle?.locale !== message.locale) return;
            try {
                runtime.installBundle(message.bundle);
                received = message.revision;
                runtime.changeLocale(message.locale).catch(() => {});
            } catch (_) { /* A malformed or obsolete pack cannot replace the current locale. */ }
        }
    });
    document.addEventListener('ghost:locale-changed', () => {
        revision++;
        for (const [frame, nonce] of enrolled) {
            if (![...document.querySelectorAll('iframe[data-ghost-locale-frame]')].some(item => item.contentWindow === frame)) enrolled.delete(frame);
            else send(frame, nonce);
        }
    });
    if (root.parent !== root) root.parent.postMessage({type:'ghost:locale:ready', nonce:token, version:runtime.contentVersion}, origin);
})(window);
