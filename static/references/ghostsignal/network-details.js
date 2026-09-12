/* Reference-only catalog inspection. No API calls or show controls. */
(function () {
    'use strict';
    const field = document.querySelector('.network-field');
    const data = document.getElementById('network-catalog');
    if (!field || !data) return;
    const catalog = JSON.parse(data.textContent);
    const tip = document.createElement('div');
    tip.className = 'network-tooltip'; tip.id = 'network-part-tooltip';
    tip.setAttribute('role', 'tooltip'); tip.hidden = true;
    document.body.appendChild(tip);
    let active = null;
    function position() {
        if (!active) return;
        const rect = active.getBoundingClientRect();
        const box = tip.getBoundingClientRect();
        tip.style.left = Math.max(8, Math.min(innerWidth - box.width - 8, rect.left + rect.width / 2 - box.width / 2)) + 'px';
        tip.style.top = Math.max(8, Math.min(innerHeight - box.height - 8,
            rect.bottom + box.height + 16 <= innerHeight ? rect.bottom + 8 : rect.top - box.height - 8)) + 'px';
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
    field.querySelectorAll('.part').forEach(part => {
        part.addEventListener('pointerenter', event => { if (event.pointerType !== 'touch') show(part); });
        part.addEventListener('pointerleave', event => {
            if (event.pointerType !== 'touch' && !tip.contains(event.relatedTarget) && document.activeElement !== part) hide();
        });
        part.addEventListener('focus', () => show(part));
        part.addEventListener('blur', hide);
        part.addEventListener('click', () => show(part));
    });
    tip.addEventListener('pointerleave', event => {
        if (active && !active.contains(event.relatedTarget) && document.activeElement !== active) hide();
    });
    document.addEventListener('pointerdown', event => {
        if (active && !active.contains(event.target) && !tip.contains(event.target)) hide();
    });
    document.addEventListener('keydown', event => { if (event.key === 'Escape') hide(); });
    function resize() {
        field.style.setProperty('--network-size', Math.min(field.clientWidth, field.clientHeight) + 'px');
        position();
    }
    if (typeof ResizeObserver === 'function') new ResizeObserver(resize).observe(field);
    window.addEventListener('resize', resize);
    window.addEventListener('pagehide', hide);
    resize();
})();
