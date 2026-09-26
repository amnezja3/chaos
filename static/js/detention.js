/* Authoritative capabilities arrive with each state poll; client time never releases. */
(() => {
    let state = null;
    const allowed = new Set(['map', 'browser', 'webdragon', 'ghost-radio', 'ghost_hack_radio', 'radio', 'email', 'cyberner']);
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
                cover.tabIndex = 0;
                cover.setAttribute('role', 'button');
                cover.setAttribute('aria-label', 'Informacja o areszcie i kaucji');
                cover.onclick = blockedAction;
                cover.onkeydown = event => {
                    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); blockedAction(); }
                };
                win.appendChild(cover);
            }
            const text = `Areszt — aplikacja niedostępna. Pozostało ${state.remaining_seconds} s online. Web Dragon, radio i prywatny Cyberner pozostają dostępne.`;
            if (cover.textContent !== text) cover.textContent = text;
        });
    }
    function update(next) {
        const previous = state;
        state = next || null;
        if (typeof document === 'undefined') return;
        if (state || previous) window.clearDetentionTarget?.();
        if (typeof window.renderToolbarStatus === 'function') window.renderToolbarStatus();
        applyWindows();
        document.querySelectorAll('iframe').forEach(frame => {
            try { frame.contentWindow?.applyDetentionView?.(state); } catch (_) {}
        });
        window.dispatchEvent(new CustomEvent('detention:changed', {detail: state}));
    }
    async function refresh() {
        const response = await fetch('/api/response/detention');
        if (!response.ok) return;
        const data = await response.json();
        update(data.detention);
        let badge = document.getElementById('criminal-record-status');
        if (!badge) {
            badge = document.createElement('div');
            badge.id = 'criminal-record-status';
            badge.style.cssText = 'position:fixed;bottom:64px;right:16px;z-index:999;padding:6px 10px;background:#061109e6;border:1px solid #42632c;color:#c7eab8;font:12px monospace;max-width:calc(100vw - 52px);pointer-events:none';
            document.body.appendChild(badge);
        }
        const record = data.criminal_record;
        badge.hidden = !record?.active_burden;
        if (record?.active_burden) badge.textContent = `Kartoteka: ${record.active_burden} · ${record.paused || data.detention ? 'wygaszanie wstrzymane' : 'spadek za ' + Math.ceil(record.remaining_seconds / 60) + ' min spokojnej aktywności'}`;
    }
    let paying = false;
    async function submitBail(sanctionId) {
        const paid = await fetch('/api/response/detention/bail', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({sanction_id: sanctionId})});
        const result = await paid.json();
        if (!paid.ok) throw new Error(result.message || result.error || 'Nie udało się opłacić kaucji.');
        await refresh();
        await window.showGhostDecisionDialog({title: 'KAUCJA', showConfirm: false, cancelLabel: 'ZAMKNIJ',
            message: result.paid ? 'Kaucja opłacona. Gracz został zwolniony. HC trafiły na konto admin.' : 'Wyrok już zakończony. Nie pobrano HC.'});
    }
    async function blockedAction() {
        if (paying) return;
        paying = true;
        try {
            const response = await fetch('/api/response/detention?bail_offer=1');
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || 'Nie można pobrać informacji o kaucji.');
            update(data.detention);
            if (!data.detention) return;
            const sentence = data.detention;
            const canPay = data.bail_offer?.can_pay === true;
            const amount = Number(sentence.bail_hc).toLocaleString('pl-PL');
            const communication = sentence.private_messages_remaining > 0
                ? 'Możesz wysłać jedną wiadomość prywatną w Cybernerze, aby poprosić innego gracza o opłacenie kaucji.'
                : 'Wiadomość prywatna na ten wyrok została już wykorzystana. Nadal możesz czytać odpowiedzi w Cybernerze.';
            const accepted = await window.showGhostDecisionDialog({title: 'CHAOS // ARESZT',
                message: `Zostałeś skazany na ${Math.ceil(Number(sentence.duration_seconds) / 60)} min więzienia w zakładzie karnym ${sentence.prison_name || 'Areszt'}. Twoje prawa zostały ograniczone na czas odbywania kary.`,
                details: `${communication} Pozostało ${sentence.remaining_seconds} s online. Kaucja: ${amount} HC. ${canPay ? 'Możesz opłacić kaucję ze swojego konta. Odbiorca: admin.' : 'Nie masz wystarczających HC na samodzielne opłacenie kaucji.'}`,
                showConfirm: canPay, confirmLabel: `ZAPŁAĆ ${amount} HC`, cancelLabel: 'ZAMKNIJ'});
            if (canPay && accepted) await submitBail(sentence.sanction_id);
        } catch (error) {
            await window.showGhostDecisionDialog({title: 'KAUCJA', showConfirm: false, cancelLabel: 'ZAMKNIJ', message: error.message});
        } finally { paying = false; }
    }
    async function payBail(notice) {
        if (paying || !notice?.sanction_id || !notice?.actor_id) return;
        paying = true;
        try {
            const response = await fetch('/api/response/detention/bail-quote?username=' + encodeURIComponent(notice.actor_id));
            const data = await response.json();
            if (!response.ok) throw new Error(data.message || data.error || 'Nie można pobrać kaucji.');
            if (!data.quote || data.quote.sanction_id !== notice.sanction_id) throw new Error('Ten wyrok już się zakończył. Nie pobrano HC.');
            if (!await window.showGhostDecisionDialog({title: 'CHAOS // KAUCJA',
                message: `Zapłacić ${Number(data.quote.bail_hc).toLocaleString('pl-PL')} HC za zwolnienie gracza ${notice.actor_id}?`,
                details: `Areszt: ${notice.prison_name}. Odbiorca HC: admin. Kartoteka pozostaje bez zmian.`,
                confirmLabel: 'OPŁAĆ KAUCJĘ', cancelLabel: 'ANULUJ'})) return;
            await submitBail(notice.sanction_id);
        } catch (error) {
            await window.showGhostDecisionDialog({title: 'KAUCJA', confirmLabel: 'OK', cancelLabel: 'ZAMKNIJ', message: error.message});
        } finally { paying = false; }
    }
    const escape = value => String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    function toolbarMarkup() {
        if (!state) return '';
        const remaining = Math.max(0, Number(state.remaining_seconds) || 0);
        const total = Math.max(1, Number(state.duration_seconds) || remaining);
        const time = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}`;
        return `<span class="system-status-detention" role="button" tabindex="0" onclick="DetentionUI.blockedAction()" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();DetentionUI.blockedAction()}" title="Wyrok i kaucja — czas odliczany tylko online">
            <svg viewBox="0 0 24 24" width="22" height="22" aria-label="Więzienie"><path d="M3 3h18v18H3zM8 3v18M16 3v18M3 9h18M3 16h18" fill="none" stroke="currentColor" stroke-width="2"/></svg>
            <span class="detention-status-body"><b>${escape(state.prison_name || 'Areszt')}</b>
            <span class="detention-status-time"><i class="detention-dots" aria-hidden="true">● ● ●</i> ${time}</span>
            <progress max="${total}" value="${Math.min(total, remaining)}" aria-label="Pozostały czas aresztu"></progress></span></span>`;
    }
    function appendNotice(container, notice) {
        if (!notice?.sanction_id || !notice?.actor_id) return;
        const card = document.createElement('div'); card.className = 'cyberner-detention-notice';
        const text = document.createElement('p');
        text.textContent = `CENZURA PROKURATORSKA // Wiadomość ocenzurowana. Nadawca wiadomości przebywa w areszcie ${notice.prison_name} i może wyjść za kaucją.`;
        const button = document.createElement('button'); button.type = 'button';
        button.textContent = `Kaucja: ${Number(notice.bail_hc).toLocaleString('pl-PL')} HC`;
        button.onclick = () => payBail(notice);
        card.append(text, button); container.appendChild(card);
    }
    window.DetentionUI = {update, refresh, appAllowed, chatReason, toolbarMarkup, appendNotice, payBail, blockedAction, get state() { return state; }};
    if (typeof document === 'undefined') return;
    document.addEventListener('DOMContentLoaded', () => {
        new MutationObserver(applyWindows).observe(document.body, {childList: true, subtree: true});
        refresh().catch(() => {});
    });
})();
