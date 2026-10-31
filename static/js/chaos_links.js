/* CHAOS location links v1. Actions reuse the canonical terminal handlers. */
(() => {
    'use strict';
    const parse = href => {
        const match = /^(?:chaos:(focus|teleport)\/|(focus|teleport):)(.+)$/.exec(href || '');
        if (!match) return null;
        const action = match[1] || match[2], target = match[3];
        if (target === 'cur:loc') return {action, current:true};
        if (!/^-?\d+(?:\.\d+)?:-?\d+(?:\.\d+)?$/.test(target)) return null;
        const [lat, lng] = target.split(':').map(Number);
        return Math.abs(lat)<=90 && Math.abs(lng)<=180 ? {action, lat, lng} : null;
    };
    const compactCoordinates = target => target.current ? 'cur:loc' : `${target.lat.toFixed(4)}:${target.lng.toFixed(4)}`;
    function create(value, compact=false) {
        const target = parse(value);
        if (!target) return null;
        const link = document.createElement('a');
        const name = target.action === 'focus' ? 'Focus' : 'Teleport';
        link.className = 'chaos-link';
        link.dataset.chaosLink = target.action;
        link.href = `chaos:${target.action}/${target.current ? 'cur:loc' : `${target.lat}:${target.lng}`}`;
        link.title = `${name} · ${target.current ? 'cur:loc' : `${target.lat}:${target.lng}`}`;
        link.setAttribute('aria-label', link.title);
        const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        icon.setAttribute('viewBox','0 0 24 24'); icon.setAttribute('aria-hidden','true');
        const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
        use.setAttribute('href',`/static/images/system/chaos-actions.svg#${target.action}`);
        icon.append(use);
        const text = document.createElement('span');
        text.textContent = compact ? name : `${name} ${compactCoordinates(target)}`;
        link.append(icon,text);
        return link;
    }
    const excluded = 'a,button,input,textarea,select,script,style,code,pre,svg,[contenteditable]:not([contenteditable="false"]),[data-chaos-no-links],[data-chaos-link-output]';
    const scope = '.app-window,.terminal,[data-chaos-text]';
    function enhance(root) {
        if (!root?.isConnected) return;
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const nodes = root.nodeType === Node.TEXT_NODE ? [root] : [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        for (const node of nodes) {
            const parent = node.parentElement;
            if (!parent?.closest(scope) || parent.closest(excluded) || !/(?:focus|teleport):/.test(node.data)) continue;
            const pattern = /\b(?:focus|teleport):(?:cur:loc|-?\d+(?:\.\d+)?:-?\d+(?:\.\d+)?)(?![\w:]|\.\d)/g;
            const fragment = document.createDocumentFragment();
            let offset = 0;
            for (const match of node.data.matchAll(pattern)) {
                if (match.index && /[\w/:]/.test(node.data[match.index-1])) continue;
                const link = create(match[0]);
                if (!link) continue;
                fragment.append(document.createTextNode(node.data.slice(offset,match.index)),link);
                offset = match.index + match[0].length;
            }
            if (offset) { fragment.append(document.createTextNode(node.data.slice(offset))); node.replaceWith(fragment); }
        }
    }
    window.ChaosLinks = {parse, create, enhance};
    const start = () => {
        enhance(document.body);
        new MutationObserver(records => {
            // Only inspect changed text/subtrees, never rescan the whole desktop
            // for a clock tick, locale update or incoming message.
            const roots = new Set();
            for (const record of records) {
                if (record.type === 'characterData') roots.add(record.target);
                else for (const node of record.addedNodes) if (node.nodeType===1 || node.nodeType===3) roots.add(node);
            }
            for (const root of roots) if (!root.parentElement?.closest(excluded)) enhance(root);
        }).observe(document.body, {childList:true, subtree:true, characterData:true});
    };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true}); else start();
    document.addEventListener('click', async event => {
        const link = event.target.closest('a[data-chaos-link]');
        if (!link) return;
        event.preventDefault();
        event.stopPropagation();
        const target = parse(link.getAttribute('href'));
        if (!target || link.dataset.busy) return;
        const host = link.closest('.app-window,.terminal,[data-chaos-text]');
        if (!host) return;
        let output = host.querySelector('[data-chaos-link-output]');
        if (!output) {
            output = document.createElement('div');
            output.dataset.chaosLinkOutput = ''; output.setAttribute('role','status');
            (host.querySelector('.app-content,.mail-message-content,.content') || host).append(output);
        }
        output.hidden = false; output.replaceChildren();
        link.dataset.busy = '1'; link.setAttribute('aria-disabled', 'true');
        try {
            if (target.current) await handleTerminalGeolocationRequest(output, {purpose:target.action});
            else if (target.action === 'focus') handleTerminalMapFocus(output, target);
            else await handleTerminalTeleport(output, target);
        } catch (_) {
            output.textContent = 'CHAOS: action unavailable';
        } finally {
            delete link.dataset.busy; link.removeAttribute('aria-disabled');
            if (!output.textContent.trim()) output.hidden = true;
        }
    }, true);
})();
