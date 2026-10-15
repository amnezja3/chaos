(function () {
    'use strict';
    const config = JSON.parse(document.getElementById('launch-config').textContent);
    const key = 'chaos-launch-binding-v1';
    const nativeFetch = window.fetch.bind(window);
    const text = config.text;
    const status = document.getElementById('launch-status');
    const retry = document.getElementById('launch-retry');
    const login = document.getElementById('launch-login');
    let pending = false;
    const embedded = window.parent !== window;
    const url = new URL(location.href);
    // Remove old compatibility tokens before loading any child resources.
    url.searchParams.delete('_session_generation');
    history.replaceState(null, '', url.pathname + url.search);

    async function fetchChecked(path, options = {}) {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);
        try {
            const response = await nativeFetch(path, {...options, credentials: 'same-origin',
                cache: 'no-store', redirect: 'error', signal: controller.signal});
            if (response.status === 409 || response.status === 401) throw new Error('stale');
            if (!response.ok) throw new Error('network');
            return response;
        } finally { clearTimeout(timeout); }
    }

    async function parentContext() {
        return new Promise((resolve, reject) => {
            const nonce = crypto.randomUUID();
            const timeout = setTimeout(() => { window.removeEventListener('message', receive); reject(new Error('network')); }, 10000);
            function receive(event) {
                if (event.origin !== location.origin || event.source !== parent
                    || event.data?.type !== 'chaos:launch-context' || event.data.nonce !== nonce) return;
                clearTimeout(timeout);
                window.removeEventListener('message', receive);
                if (!event.data.context?.generation) reject(new Error('stale'));
                else resolve(event.data.context);
            }
            window.addEventListener('message', receive);
            parent.postMessage({type: 'chaos:launch-request', nonce}, location.origin);
        });
    }

    async function mount(context) {
        const target = config.view === 'desktop' ? new URL('/api/desktop-shell', location.origin)
            : new URL(config.view === 'map' ? '/map' : '/dev', location.origin);
        for (const name of ['scheme', '_embedded', '_ghost_epoch', 'tab']) {
            if (url.searchParams.has(name)) target.searchParams.set(name, url.searchParams.get(name));
        }
        const response = await fetchChecked(target.href, {headers: {
            'X-Chaos-Session-Generation': context.generation,
            'X-Chaos-Ghost-Epoch': context.ghost_epoch || ''
        }});
        if (response.headers.get('X-Chaos-Session-Generation') !== context.generation
            || response.headers.get('X-Chaos-Session-User') !== context.username
            || !(response.headers.get('Content-Type') || '').includes('text/html')) throw new Error('stale');
        const html = await response.text();
        // Parse as a real document: the established runtime retains parser order,
        // DOMContentLoaded and relative URLs. Only same-origin authorized HTML enters here.
        document.open();
        document.write(html);
        document.close();
    }

    async function start() {
        if (pending) return;
        pending = true;
        retry.hidden = true; login.hidden = true; status.textContent = text.start;
        try {
            if (embedded) { await mount(await parentContext()); return; }
            let previous;
            try {
                previous = sessionStorage.getItem(key) || '';
                sessionStorage.setItem(key, previous);
            } catch (_) { throw new Error('storage'); }
            const headers = {'X-Chaos-Launch': '1'};
            if (previous) headers['X-Chaos-Launch-Binding'] = previous;
            const state = await (await fetchChecked('/api/session/status', {headers})).json();
            if (!state.authenticated) {
                if (previous) throw new Error('stale');
                location.replace('/?login=1');
                return;
            }
            // Pin status before the next request, including a completely fresh tab.
            sessionStorage.setItem(key, state.binding);
            const bootstrap = await (await fetchChecked('/api/session/bootstrap', {method: 'POST', headers: {
                ...headers, 'X-Chaos-Launch-Binding': state.binding, 'X-Chaos-Launch-CSRF': config.csrf
            }})).json();
            await mount(bootstrap.context);
        } catch (error) {
            status.textContent = text[error.message] || text.retry;
            login.hidden = error.message !== 'stale' || embedded;
            retry.hidden = error.message === 'stale' || error.message === 'storage';
        } finally { pending = false; }
    }
    retry.addEventListener('click', start);
    // No automatic retries that could silently adopt a different account.
    start();
})();
