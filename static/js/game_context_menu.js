/* Keep gameplay context menus; suppress only the browser's default action. */
(function (root) {
    'use strict';
    if (root.GhostContextMenuGuard) return;
    const documents = new WeakSet();
    function install(view) {
        let doc;
        try { doc = view.document; } catch (_) { return; }
        if (!doc || documents.has(doc)) return;
        documents.add(doc);
        // WebKit image/link callouts can be displayed without contextmenu.
        doc.documentElement?.style.setProperty('-webkit-touch-callout', 'none');
        view.addEventListener('contextmenu', event => event.preventDefault(), {capture:true, passive:false});
        doc.addEventListener('contextmenu', event => {
            const terminal = event.target.closest?.('.terminal');
            const input = event.target.closest?.('.terminal-input') || terminal?.querySelector('.terminal-input');
            if (!input || input.disabled || input.readOnly || typeof view.ghostSet !== 'function') return;
            event.preventDefault();
            doc.getElementById('terminal-paste-menu')?._dismiss?.();
            const start = input.selectionStart, end = input.selectionEnd;
            const original = input.value;
            const menu = doc.createElement('div');
            menu.id = 'terminal-paste-menu';
            menu.setAttribute('role', 'menu');
            const button = doc.createElement('button');
            button.type = 'button';
            button.setAttribute('role', 'menuitem');
            view.ghostSet(button, 'terminal.paste');
            menu.append(button);
            doc.body.append(menu);
            const controller = new view.AbortController();
            const dismiss = () => { controller.abort(); menu.remove(); };
            menu._dismiss = dismiss;
            doc.addEventListener('pointerdown', e => { if (!menu.contains(e.target)) dismiss(); }, {capture:true, signal:controller.signal});
            doc.addEventListener('keydown', e => {
                if (e.key === 'Escape') { dismiss(); input.focus(); }
            }, {signal:controller.signal});
            view.addEventListener('resize', dismiss, {signal:controller.signal});
            button.addEventListener('click', async () => {
                button.disabled = true;
                try {
                    const text = await view.navigator.clipboard.readText();
                    if (!menu.isConnected || !input.isConnected || input.disabled || input.readOnly) return;
                    input.focus();
                    // Never submit pasted commands. Preserve edits made while permission was pending.
                    if (input.value === original) input.setSelectionRange(start, end);
                    input.setRangeText(text.replace(/[\r\n]+/g, ' '), input.selectionStart, input.selectionEnd, 'end');
                    input.dispatchEvent(new view.Event('input', {bubbles:true}));
                    dismiss();
                } catch (_) {
                    if (!menu.isConnected) return;
                    const status = doc.createElement('div');
                    status.setAttribute('role', 'status');
                    view.ghostSet(status, 'terminal.paste_fallback');
                    menu.append(status);
                    input.focus();
                }
            });
            const rect = menu.getBoundingClientRect();
            menu.style.left = Math.max(4, Math.min(event.clientX, view.innerWidth - rect.width - 4)) + 'px';
            menu.style.top = Math.max(4, Math.min(event.clientY, view.innerHeight - rect.height - 4)) + 'px';
            button.focus();
        });
        const attach = frame => {
            try { if (frame.contentWindow) install(frame.contentWindow); } catch (_) { /* External sites own their documents. */ }
        };
        doc.addEventListener('load', event => {
            if (event.target?.tagName === 'IFRAME') attach(event.target);
        }, true);
        const scan = node => {
            if (node.tagName === 'IFRAME') attach(node);
            node.querySelectorAll?.('iframe').forEach(attach);
        };
        new view.MutationObserver(records => {
            for (const record of records) for (const node of record.addedNodes) scan(node);
        }).observe(doc, {childList:true, subtree:true});
        scan(doc);
    }
    root.GhostContextMenuGuard = Object.freeze({install});
    install(root);
})(window);
