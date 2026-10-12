/* Authoritative capabilities arrive with each state poll; client time never releases. */
(() => {
    const t = (key, fallback, params = {}) => window.GhostLocale?.t('apps.detention.' + key, params) || fallback.replace(/\{(\w+)\}/g, (_, name) => params[name]);
    const number = value => Number(value).toLocaleString(window.GhostLocale?.getLocale() || 'pl');
    const notices = new Map();
    const refreshAmount = amount => root => {
        root.querySelectorAll('[data-ghost-i18n]').forEach(element => {
            const params = JSON.parse(element.getAttribute('data-ghost-params') || '{}');
            if (Object.prototype.hasOwnProperty.call(params, 'amount')) {
                params.amount = number(amount);
                window.ghostSet?.(element, element.getAttribute('data-ghost-i18n'), params);
            }
        });
    };
    let state = null;
    const allowed = new Set(['map', 'browser', 'webdragon', 'ghost-radio', 'ghost_hack_radio', 'radio', 'email', 'cyberner']);
    function appAllowed(id) { return !state || state.app_access !== 'webdragon_radio' || allowed.has(String(id || '').toLowerCase()); }
    function chatReason(channel, sending = true) {
        if (!state) return '';
        if (channel === 'world') {
            if (state.cyberner_world === 'blocked') return t('world_blocked', "World jest niedostępny podczas tego aresztu.");
            if (sending && state.cyberner_world === 'read_only') return t('world_readonly', "World: tylko odczyt podczas aresztu.");
        } else if (sending && !state.private_messages_remaining) {
            return t('message_used', "Wysłano jedną wiadomość na ten wyrok. Nadal możesz czytać.");
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
                cover.setAttribute('aria-label', t('cover_label', "Informacja o areszcie i kaucji"));
                cover.onclick = blockedAction;
                cover.onkeydown = event => {
                    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); blockedAction(); }
                };
                win.appendChild(cover);
            }
            cover.setAttribute('aria-label', t('cover_label', 'Informacja o areszcie i kaucji'));
            const text = t('cover', 'Areszt — aplikacja niedostępna. Pozostało {seconds} s online. Web Dragon, radio i prywatny Cyberner pozostają dostępne.', {seconds:String(state.remaining_seconds)});
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
    }
    let paying = false;
    async function submitBail(sanctionId) {
        const paid = await fetch('/api/response/detention/bail', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({sanction_id: sanctionId})});
        const result = await paid.json();
        if (!paid.ok) throw new Error(t('pay_error', "Nie udało się opłacić kaucji."));
        await refresh();
        await window.showGhostDecisionDialog({title: t('bail', "KAUCJA"), showConfirm: false, cancelLabel: t('close', "ZAMKNIJ"),
            titleKey:'apps.detention.bail',cancelLabelKey:'apps.detention.close',messageKey:'apps.detention.'+(result.paid?'paid':'finished'),
            message: result.paid ? t('paid', "Kaucja opłacona. Gracz został zwolniony. HC trafiły na konto admin.") : t('finished', "Wyrok już zakończony. Nie pobrano HC.")});
    }
    async function blockedAction() {
        if (paying) return;
        paying = true;
        try {
            const response = await fetch('/api/response/detention?bail_offer=1');
            const data = await response.json();
            if (!response.ok) throw new Error(t('quote_error', "Nie można pobrać informacji o kaucji."));
            update(data.detention);
            if (!data.detention) return;
            const sentence = data.detention;
            const canPay = data.bail_offer?.can_pay === true;
            const amount = number(sentence.bail_hc);
            const communication = sentence.private_messages_remaining > 0
                ? t('one_message', "Możesz wysłać jedną wiadomość prywatną w Cybernerze, aby poprosić innego gracza o opłacenie kaucji.")
                : t('no_message', "Wiadomość prywatna na ten wyrok została już wykorzystana. Nadal możesz czytać odpowiedzi w Cybernerze.");
            const accepted = await window.showGhostDecisionDialog({title: t('detained', "CHAOS // ARESZT"),
                titleKey:'apps.detention.detained', messageKey:'apps.detention.sentence',
                messageParams:{minutes:String(Math.ceil(Number(sentence.duration_seconds)/60)),prison:sentence.prison_name || t('prison', 'Areszt')},
                message:t('sentence','Zostałeś skazany na {minutes} min więzienia w zakładzie karnym {prison}. Twoje prawa zostały ograniczone na czas odbywania kary.',{minutes:String(Math.ceil(Number(sentence.duration_seconds)/60)),prison:sentence.prison_name || t('prison', 'Areszt')}),
                details: `${communication} ${t('remaining','Pozostało {seconds} s online. Kaucja: {amount} HC.',{seconds:String(sentence.remaining_seconds),amount})} ${canPay ? t('can_pay', "Możesz opłacić kaucję ze swojego konta. Odbiorca: admin.") : t('cannot_pay', "Nie masz wystarczających HC na samodzielne opłacenie kaucji.")}`,
                detailsParts:[{key:'apps.detention.'+(sentence.private_messages_remaining>0?'one_message':'no_message')},
                    {key:'apps.detention.remaining',params:{seconds:String(sentence.remaining_seconds),amount}},
                    {key:'apps.detention.'+(canPay?'can_pay':'cannot_pay')}],
                confirmLabelKey:'apps.detention.pay_amount',confirmParams:{amount},cancelLabelKey:'apps.detention.close',
                onLocaleChange:refreshAmount(sentence.bail_hc),
                showConfirm: canPay, confirmLabel:t('pay_amount','ZAPŁAĆ {amount} HC',{amount}), cancelLabel: t('close', "ZAMKNIJ")});
            if (canPay && accepted) await submitBail(sentence.sanction_id);
        } catch (error) {
            await window.showGhostDecisionDialog({title: t('bail', "KAUCJA"), titleKey:'apps.detention.bail',cancelLabelKey:'apps.detention.close',showConfirm: false, cancelLabel: t('close', "ZAMKNIJ"), message: error.message});
        } finally { paying = false; }
    }
    async function payBail(notice) {
        if (paying || !notice?.sanction_id || !notice?.actor_id) return;
        paying = true;
        try {
            const response = await fetch('/api/response/detention/bail-quote?username=' + encodeURIComponent(notice.actor_id));
            const data = await response.json();
            if (!response.ok) throw new Error(t('quote_error','Nie można pobrać informacji o kaucji.'));
            if (!data.quote || data.quote.sanction_id !== notice.sanction_id) throw new Error(t('finished','Wyrok już zakończony. Nie pobrano HC.'));
            if (!await window.showGhostDecisionDialog({title: t('bail_title', "CHAOS // KAUCJA"),
                titleKey:'apps.detention.bail_title', messageKey:'apps.detention.pay_prompt',
                messageParams:{amount:number(data.quote.bail_hc),player:notice.actor_id},
                detailsKey:'apps.detention.pay_details',detailsParams:{prison:notice.prison_name},
                message:t('pay_prompt','Zapłacić {amount} HC za zwolnienie gracza {player}?',{amount:number(data.quote.bail_hc),player:notice.actor_id}),
                details:t('pay_details','Areszt: {prison}. Odbiorca HC: admin. Kartoteka pozostaje bez zmian.',{prison:notice.prison_name}),
                confirmLabelKey:'apps.detention.pay',cancelLabelKey:'apps.detention.cancel',
                onLocaleChange:refreshAmount(data.quote.bail_hc),
                confirmLabel: t('pay', "OPŁAĆ KAUCJĘ"), cancelLabel: t('cancel', "ANULUJ")})) return;
            await submitBail(notice.sanction_id);
        } catch (error) {
            await window.showGhostDecisionDialog({title: t('bail', "KAUCJA"), titleKey:'apps.detention.bail',cancelLabelKey:'apps.detention.close',confirmLabel: 'OK', cancelLabel: t('close', "ZAMKNIJ"), message: error.message});
        } finally { paying = false; }
    }
    const escape = value => String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
    function toolbarMarkup() {
        if (!state) return '';
        const remaining = Math.max(0, Number(state.remaining_seconds) || 0);
        const total = Math.max(1, Number(state.duration_seconds) || remaining);
        const time = `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}`;
        return `<span class="system-status-detention" role="button" tabindex="0" onclick="DetentionUI.blockedAction()" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();DetentionUI.blockedAction()}" title="${escape(t('toolbar','Wyrok i kaucja — czas odliczany tylko online'))}">
            <svg viewBox="0 0 24 24" width="22" height="22" aria-label="${escape(t('prison_label','Więzienie'))}"><path d="M3 3h18v18H3zM8 3v18M16 3v18M3 9h18M3 16h18" fill="none" stroke="currentColor" stroke-width="2"/></svg>
            <span class="detention-status-body"><b>${escape(state.prison_name || t('prison', "Areszt"))}</b>
            <span class="detention-status-time"><i class="detention-dots" aria-hidden="true">● ● ●</i> ${time}</span>
            <progress max="${total}" value="${Math.min(total, remaining)}" aria-label="${escape(t('time_label','Pozostały czas aresztu'))}"></progress></span></span>`;
    }
    function appendNotice(container, notice) {
        if (!notice?.sanction_id || !notice?.actor_id) return;
        const card = document.createElement('div'); card.className = 'cyberner-detention-notice';
        const text = document.createElement('p');
        const button = document.createElement('button'); button.type = 'button';
        const render = () => {
            text.textContent = t('censored','CENZURA PROKURATORSKA // Wiadomość ocenzurowana. Nadawca wiadomości przebywa w areszcie {prison} i może wyjść za kaucją.',{prison:notice.prison_name});
            button.textContent = t('amount','Kaucja: {amount} HC',{amount:number(notice.bail_hc)});
        };
        render();
        for (const item of notices.keys()) if (!item.isConnected) notices.delete(item);
        notices.set(card,render);
        button.onclick = () => payBail(notice);
        card.append(text, button); container.appendChild(card);
    }
    window.DetentionUI = {update, refresh, appAllowed, chatReason, toolbarMarkup, appendNotice, payBail, blockedAction, get state() { return state; }};
    if (typeof document === 'undefined') return;
    document.addEventListener('ghost:locale-changed', () => {
        applyWindows();
        window.renderToolbarStatus?.();
        for (const [card,render] of notices) {
            if (card.isConnected) render(); else notices.delete(card);
        }
    });
    document.addEventListener('DOMContentLoaded', () => {
        new MutationObserver(applyWindows).observe(document.body, {childList: true, subtree: true});
        refresh().catch(() => {});
    });
})();
