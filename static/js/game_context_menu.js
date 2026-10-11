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
