/* Authoritative capabilities arrive with each state poll; client time never releases. */
(() => {
    let state = null;
    const allowed = new Set(['browser', 'webdragon', 'ghost-radio', 'ghost_hack_radio', 'radio', 'email', 'cyberner']);
    function appAllowed(id) { return !state || state.app_access !== 'webdragon_radio' || allowed.has(String(id || '').toLowerCase()); }
    function chatReason(channel, sending = true) {
        if (!state) return '';
        if (channel === 'world') {
            if (state.cyberner_world === 'blocked') return 'World jest niedostępny podczas tego aresztu.';
            if (sending && state.cyberner_world === 'read_only') return 'World: tylko odczyt podczas aresztu.';
        } else if (sending && !state.private_messages_remaining) {
            return 'Wysłano jedną wiadomość na ten wyrok. Nadal możesz czytać.';
        }
        return '';
    }
    function applyWindows() {
        document.querySelectorAll('.terminal, .app-window').forEach(win => {
            const blocked = !appAllowed(win.dataset.app);
            let cover = win.querySelector(':scope > .detention-cover');
            if (!blocked) {
                if (cover) cover.remove();
                win.querySelectorAll('[data-detention-inert]').forEach(el => {
                    el.inert = el.dataset.detentionInert === 'true';
                    delete el.dataset.detentionInert;
                });
                return;
            }
            Array.from(win.children).filter(el => el !== cover).forEach(el => {
                if (!('detentionInert' in el.dataset)) el.dataset.detentionInert = String(el.inert);
                el.inert = true;
            });
            if (!cover) {
                cover = document.createElement('div');
                cover.className = 'detention-cover';
                cover.style.cssText = 'position:absolute;inset:0;z-index:9999;background:#071009f5;color:#b8ff86;padding:24px;display:grid;place-content:center;';
                win.appendChild(cover);
            }
            const text = `Areszt — aplikacja niedostępna. Pozostało ${state.remaining_seconds} s online. Web Dragon, radio i prywatny Cyberner pozostają dostępne.`;
            if (cover.textContent !== text) cover.textContent = text;
        });
    }
    function update(next) {
        state = next || null;
        if (typeof document === 'undefined') return;
        const label = document.getElementById('detention-state');
        if (label) label.textContent = state ? `Areszt · ${state.remaining_seconds} s online · wiadomość prywatna: ${state.private_messages_remaining}/1` : '';
        applyWindows();
        window.dispatchEvent(new CustomEvent('detention:changed', {detail: state}));
    }
    async function refresh() {
        const response = await fetch('/api/response/detention');
        if (!response.ok) return;
        update((await response.json()).detention);
    }
    async function bail() {
        const target = window.prompt('Login aresztowanego (puste pole — Twój wyrok):', '');
        if (target === null) return;
        try {
            const response = await fetch('/api/response/detention/bail-quote?username=' + encodeURIComponent(target.trim()));
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || data.error || 'Nie można pobrać kaucji.');
            if (!data.quote) { window.alert('Ten gracz nie ma aktywnego aresztu.'); return; }
            if (!window.confirm(`Zapłacić ${data.quote.bail_hc.toLocaleString('pl-PL')} HC za zwolnienie ${target.trim() || 'Ciebie'}?`)) return;
            const paid = await fetch('/api/response/detention/bail', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({sanction_id: data.quote.sanction_id})});
            const result = await paid.json();
            if (!paid.ok) throw new Error(result.message || result.error || 'Nie udało się opłacić kaucji.');
            window.alert(result.paid ? 'Kaucja opłacona. Gracz został zwolniony.' : 'Wyrok już zakończony. Nie pobrano HC.');
            await refresh();
        } catch (error) { window.alert(error.message); }
    }
    window.DetentionUI = {update, refresh, appAllowed, chatReason, get state() { return state; }};
    if (typeof document === 'undefined') return;
    document.addEventListener('DOMContentLoaded', () => {
        const bar = document.createElement('aside');
        bar.style.cssText = 'position:fixed;top:4px;right:8px;z-index:100100;background:#071009;color:#caff9b;padding:5px;border:1px solid #59852d;font:12px monospace;max-width:90vw;';
        const label = document.createElement('span'); label.id = 'detention-state';
        const button = document.createElement('button'); button.textContent = 'Kaucja'; button.onclick = bail;
        bar.append(label, button); document.body.appendChild(bar);
        new MutationObserver(applyWindows).observe(document.body, {childList: true, subtree: true});
        refresh().catch(() => {});
    });
})();
