/* Explicit system-owned presentation. No dictionary matching of DOM text or UGC. */
(function (root) {
    'use strict';
    const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    root.ghostLabel = (key, params = {}) => `<span style="white-space:pre-wrap" data-ghost-i18n="${escape(key)}" data-ghost-params="${escape(JSON.stringify(params))}">${escape(root.GhostLocale.t(key, params))}</span>`;
    root.ghostSystemValue = (prefix, code) => root.GhostLocale.hasKey(prefix + code) ? root.ghostLabel(prefix + code) : escape(code ?? '');
    root.ghostApplicationField = (level, field, fallback = '') => {
        const entry = level?._system_i18n?.[field];
        return entry && entry.content_version === root.GhostLocale.contentVersion && entry.key.startsWith('catalog.system.') && root.GhostLocale.hasKey(entry.key)
            ? root.ghostLabel(entry.key, entry.params || {}) : escape(fallback);
    };
    root.ghostProductLabel = (product, field, fallback = '') => {
        const entry = product?.presentation_owner === 'system' && product?.presentation_i18n?.[field];
        return entry && entry.content_version === root.GhostLocale.contentVersion && entry.key.startsWith('catalog.system.') && root.GhostLocale.hasKey(entry.key)
            ? root.ghostLabel(entry.key, entry.params || {}) : escape(product?.[field] || fallback);
    };
    root.ghostSet = (node, key, params = {}) => {
        if (!node) return;
        node.dataset.ghostI18n = key;
        node.dataset.ghostParams = JSON.stringify(params);
        node.textContent = root.GhostLocale.t(key, params);
    };
    root.ghostNumber = (number, options = {}) => `<span data-ghost-number="${Number(number)}" data-ghost-format="${escape(JSON.stringify(options))}">${escape(root.GhostLocale.formatNumber(Number(number), options))}</span>`;
    root.ghostDate = (date, options = {}) => Number.isFinite(Date.parse(date))
        ? `<span data-ghost-date="${escape(date)}" data-ghost-format="${escape(JSON.stringify(options))}">${escape(root.GhostLocale.formatDate(date, options))}</span>` : escape(date || '');
    root.ghostReply = (data, fallback) => data?.message_i18n?.key && data.message_i18n.content_version === root.GhostLocale.contentVersion
        ? root.ghostLabel(data.message_i18n.key, data.message_i18n.params || {})
        : root.ghostLabel(fallback);
    root.ghostResponseText = (data, fallback) => data?.message_i18n?.key && data.message_i18n.content_version === root.GhostLocale.contentVersion && root.GhostLocale.hasKey(data.message_i18n.key)
        ? root.GhostLocale.t(data.message_i18n.key, data.message_i18n.params || {}) : root.GhostLocale.t(fallback);
    root.ghostRuntimeReply = (data, fallback) => data?.message_i18n?.key
        && data.message_i18n.content_version === root.GhostLocale.contentVersion && root.GhostLocale.hasKey(data.message_i18n.key)
        ? root.ghostLabel(data.message_i18n.key, data.message_i18n.params || {})
        : data?.message ? escape(data.message) : root.ghostLabel(fallback);
})(window);
