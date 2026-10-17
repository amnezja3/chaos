/* Account settings are a CHAOS workspace window, never a new browser window. */
(() => {
    'use strict';
    const returnKey = 'chaos.identity.return';
    const label = () => (window.GhostLocale?.getLocale() || document.documentElement.lang) === 'en'
        ? 'Account & security' : 'Konto i bezpieczeństwo';
    window.createIdentitySettingsWindow = (safetyContext = null) => {
        const safetyUrl = safetyContext ? '/account/safety?' + new URLSearchParams(safetyContext).toString() : null;
        const existing = document.querySelector('[data-app="identity-settings"]');
        if (existing) { if(safetyUrl)existing.querySelector('iframe').src=safetyUrl; bringWindowToFront(existing); return existing; }
        const win = document.createElement('div');
        win.className = 'terminal identity-settings-window';
        win.dataset.app = 'identity-settings';
        win.dataset.appTitle = label();
        win.dataset.appIcon = '◇';
        const position = findAvailablePosition(860, 680);
        Object.assign(win.style, {top: position.top + 'px', left: position.left + 'px',
            width: '860px', height: '680px', maxWidth: 'calc(100vw - 24px)',
            maxHeight: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column'});
        const bar = document.createElement('div');
        bar.className = 'title-bar';
        const title = document.createElement('span');
        title.textContent = label();
        const close = document.createElement('button');
        close.className = 'close-btn'; close.type = 'button'; close.textContent = '×';
        close.setAttribute('aria-label', label() + ' · ×');
        bar.append(title, close);
        const frame = document.createElement('iframe');
        frame.title = label();
        frame.style.cssText = 'width:100%;flex:1;min-height:0;border:0;background:#020b0d';
        frame.src = safetyUrl || '/account/identity?embedded=1';
        win.append(bar, frame);
        document.body.append(win);
        close.addEventListener('click', () => win.remove());
        bindWindowMaximize(win, label());
        makeDraggable(win);
        bringWindowToFront(win);
        return win;
    };
    window.addEventListener('message', event => {
        if (event.origin !== location.origin) return;
        const win = document.querySelector('[data-app="identity-settings"]');
        if (win?.querySelector('iframe')?.contentWindow !== event.source) return;
        if (event.data?.type === 'chaos.identity.close') win.remove();
        if (event.data?.type === 'chaos.identity.status' && typeof event.data.text === 'string') {
            showSystemToast({title: label(), text: escapeHTML(event.data.text.slice(0, 600)),
                source: 'identity'}, event.data.level === 'error' ? 'error' : 'success');
        }
    });
    document.addEventListener('DOMContentLoaded', () => {
        try {
            const timestamp = Number(sessionStorage.getItem(returnKey));
            sessionStorage.removeItem(returnKey);
            if (document.body.dataset.identityGateway === '1' && timestamp && Date.now() - timestamp < 600000) {
                window.createIdentitySettingsWindow();
            }
        } catch (_) { /* Storage restrictions do not prevent ordinary settings. */ }
    });
})();
