/* Shared catalog tooltip and square sizing; no clock, API or game actions. */
(function (global) {
 function mount(options) {
    'use strict';
    const document = options.document, window = options.window || global;
    const field = options.field, catalog = options.catalog;
    const listeners = [];
    function listen(target, type, fn) {
        if (!target || !target.addEventListener) return;
        target.addEventListener(type, fn); listeners.push(() => target.removeEventListener(type, fn));
    }
    const tip = document.createElement('div');
    tip.className = 'network-tooltip'; tip.id = 'network-part-tooltip';
    tip.setAttribute('role', 'tooltip'); tip.hidden = true;
    (options.host || document.body).appendChild(tip);
    let active = null;
    function position() {
        if (!active) return;
        const rect = active.getBoundingClientRect();
        const box = tip.getBoundingClientRect();
        tip.style.left = Math.max(8, Math.min((window.innerWidth || 1024) - box.width - 8, rect.left + rect.width / 2 - box.width / 2)) + 'px';
        tip.style.top = Math.max(8, Math.min((window.innerHeight || 768) - box.height - 8,
            rect.bottom + box.height + 16 <= (window.innerHeight || 768) ? rect.bottom + 8 : rect.top - box.height - 8)) + 'px';
    }
    function hide() {
        if (active) active.removeAttribute('aria-describedby');
        active = null; tip.hidden = true;
    }
    function show(part) {
        const info = catalog[part.getAttribute('data-code')];
        if (!info) return;
        hide(); active = part; tip.replaceChildren();
        const header = document.createElement('p');
        header.className = 'network-tooltip-title'; header.textContent = '> GN / NODE INSPECT'; tip.appendChild(header);
        const list = document.createElement('dl');
        [['Nazwa',info.name],['Klan',info.clan],['Symbol',info.code],['Supermoc',info.power],['Maszyna',info.machine]].forEach(pair => {
            const label = document.createElement('dt'), value = document.createElement('dd');
            label.textContent = pair[0]; value.textContent = pair[1]; list.appendChild(label); list.appendChild(value);
        });
        tip.appendChild(list);
        const description = document.createElement('p'); description.textContent = info.description; tip.appendChild(description);
        tip.hidden = false; part.setAttribute('aria-describedby', tip.id); position();
    }
    (options.parts || []).forEach(part => {
        listen(part, 'pointerenter', event => { if (event.pointerType !== 'touch') show(part); });
        listen(part, 'pointerleave', event => {
            if (event.pointerType !== 'touch' && !tip.contains(event.relatedTarget) && document.activeElement !== part) hide();
        });
        listen(part, 'focus', () => show(part));
        listen(part, 'blur', hide);
        listen(part, 'click', () => show(part));
    });
    listen(tip, 'pointerleave', event => {
        if (active && !active.contains(event.relatedTarget) && document.activeElement !== active) hide();
    });
    listen(document, 'pointerdown', event => {
        if (active && !active.contains(event.target) && !tip.contains(event.target)) hide();
    });
    listen(document, 'keydown', event => { if (event.key === 'Escape') hide(); });
    function resize() {
        if (options.square !== false) field.style.setProperty('--network-size', Math.min(field.clientWidth, field.clientHeight) + 'px');
        position();
    }
    const observer = typeof window.ResizeObserver === 'function' ? new window.ResizeObserver(resize) : null;
    if (observer) observer.observe(field);
    listen(window, 'resize', resize);
    listen(window, 'pagehide', hide);
    resize();
    return {resize, hide, dispose() { hide(); listeners.forEach(remove => remove()); if (observer) observer.disconnect(); tip.remove(); }};
 }
 const api = {mount};
 if (typeof module !== "undefined" && module.exports) module.exports = api;
 global.GhostSignalNetworkDetails = api;
})(typeof window !== "undefined" ? window : globalThis);
