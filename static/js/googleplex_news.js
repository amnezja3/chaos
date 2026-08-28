(function (global) {
    "use strict";

    const WEIGHTS = new Set(["hero", "large", "medium", "small"]);
    const ENTRY_STATES = new Set(["normal", "trending", "hot", "warning", "critical", "new", "verified", "stale", "disabled"]);
    const ASSET_FAMILIES = new Set(["scene", "character", "tool", "map", "clan", "package", "storage", "market", "network", "system", "stamp"]);
    const ASSET_STATES = new Set(["neutral", "danger", "victory", "defence"]);
    const ACTIONS = new Set(["open_googleplex_search", "open_blacknet", "open_ghost_exchange", "open_map", "open_cyberner", "open_operation"]);
    const ACTION_LABELS = Object.freeze({
        open_googleplex_search: "ZOBACZ NARZĘDZIE",
        open_blacknet: "OTWÓRZ BLACKNET",
        open_ghost_exchange: "ZOBACZ EXCHANGE",
        open_map: "OTWÓRZ MAPĘ",
        open_cyberner: "OTWÓRZ KANAŁ",
        open_operation: "OPERACJE"
    });
    const ASSET_PREFIX = "/static/images/googleplx/";

    const text = (value, max = 240) => String(value ?? "").replace(/\s+/g, " ").trim().slice(0, max);
    const escapeHtml = value => text(value, 5000)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    const safeAssetPath = value => {
        const path = text(value, 320);
        if (!path.startsWith(ASSET_PREFIX)) return "";
        if (!/\.(?:webp|png|svg)(?:#[a-z0-9_-]+)?$/i.test(path)) return "";
        return path;
    };

    const normalizeEntry = raw => {
        if (!raw || typeof raw !== "object") return null;
        const content = raw.content && typeof raw.content === "object" ? raw.content : {};
        const presentation = raw.presentation && typeof raw.presentation === "object" ? raw.presentation : {};
        const rawAction = raw.action && typeof raw.action === "object" ? raw.action : {};
        const newsId = text(content.news_id, 96);
        if (!newsId) return null;
        const weight = WEIGHTS.has(presentation.weight) ? presentation.weight : "small";
        const family = ASSET_FAMILIES.has(presentation.asset_family) ? presentation.asset_family : "stamp";
        const actionType = ACTIONS.has(rawAction.action_type) ? rawAction.action_type : "";
        const actionable = rawAction.kind === "ACTIONABLE" && Boolean(actionType);
        return {
            content: {
                news_id: newsId,
                source: text(content.source, 48),
                source_ref: text(content.source_ref, 128),
                category: text(content.category, 32),
                title: text(content.title, 72),
                summary: text(content.summary, 220),
                published_at: text(content.published_at, 40),
                truth_class: text(content.truth_class, 24),
                audience_scope: text(content.audience_scope, 16)
            },
            presentation: {
                weight,
                state: ENTRY_STATES.has(presentation.state) ? presentation.state : "normal",
                accent_role: text(presentation.accent_role, 24),
                asset_id: text(presentation.asset_id, 96),
                asset_family: family,
                asset_state: ASSET_STATES.has(presentation.asset_state) ? presentation.asset_state : "neutral",
                asset_path: safeAssetPath(presentation.asset_path),
                asset_kind: presentation.asset_kind === "symbol" ? "symbol" : (presentation.asset_kind === "image" ? "image" : "css"),
                asset_focus_x: Number.isFinite(Number(presentation.asset_focus_x)) ? Number(presentation.asset_focus_x) : 50,
                asset_focus_y: Number.isFinite(Number(presentation.asset_focus_y)) ? Number(presentation.asset_focus_y) : 50,
                asset_scale: Number.isFinite(Number(presentation.asset_scale)) ? Number(presentation.asset_scale) : 1,
                asset_rotation: Number.isFinite(Number(presentation.asset_rotation)) ? Number(presentation.asset_rotation) : 0,
                primary_stat: text(presentation.primary_stat, 22),
                secondary_stat: text(presentation.secondary_stat, 22)
            },
            action: {
                kind: actionable ? "ACTIONABLE" : "STAMP_ONLY",
                action_type: actionable ? actionType : "",
                action_target: actionable ? text(rawAction.action_target, 120) : "",
                action_payload_ref: actionable ? text(rawAction.action_payload_ref, 160) : ""
            }
        };
    };

    const normalizeSnapshot = raw => {
        if (!raw || typeof raw !== "object" || raw.success !== true || raw.view !== "home") return null;
        const entries = Array.isArray(raw.entries) ? raw.entries.map(normalizeEntry).filter(Boolean).slice(0, 24) : [];
        const stats = Array.isArray(raw.global_stats) ? raw.global_stats.filter(item => item && typeof item === "object").slice(0, 6).map(item => ({
            key: text(item.key, 32), label: text(item.label, 24), value: text(item.value, 28), state: ASSET_STATES.has(item.state) ? item.state : "neutral"
        })) : [];
        const protocol = raw.protocol_status && typeof raw.protocol_status === "object" ? raw.protocol_status : {};
        return {
            schema_version: text(raw.schema_version, 48),
            state_version: text(raw.state_version, 64),
            generated_at: text(raw.generated_at, 40),
            entries,
            global_stats: stats,
            protocol_status: {
                source: text(protocol.source, 40),
                integrity: text(protocol.integrity, 24),
                access_mode: text(protocol.access_mode, 24),
                ollama_used: protocol.ollama_used === true,
                publication_enabled: protocol.publication_enabled === true
            }
        };
    };

    const assetMarkup = presentation => {
        const style = `--gp-asset-x:${presentation.asset_focus_x}%;--gp-asset-y:${presentation.asset_focus_y}%;--gp-asset-scale:${presentation.asset_scale};--gp-asset-rotation:${presentation.asset_rotation}deg`;
        if (presentation.asset_kind === "image" && presentation.asset_path) {
            return `<span class="gp-news-card__asset gp-news-card__asset--image" style="${style}"><img src="${escapeHtml(presentation.asset_path)}" alt="" loading="lazy" decoding="async"></span>`;
        }
        if (presentation.asset_kind === "symbol" && presentation.asset_path) {
            return `<span class="gp-news-card__asset gp-news-card__asset--symbol" style="${style}" aria-hidden="true"><svg viewBox="0 0 64 64"><use href="${escapeHtml(presentation.asset_path)}"></use></svg></span>`;
        }
        return `<span class="gp-news-card__asset gp-news-card__asset--fallback" style="${style}" aria-hidden="true"><span>${escapeHtml(presentation.asset_family.toUpperCase())}</span></span>`;
    };

    const cardMarkup = (entry, layoutIndex) => {
        const {content, presentation, action} = entry;
        const interactive = action.kind === "ACTIONABLE";
        const tag = interactive ? "button" : "article";
        const type = interactive ? ' type="button"' : "";
        const actionData = interactive ? ` data-gp-news-action="${escapeHtml(content.news_id)}"` : "";
        const stats = presentation.primary_stat || presentation.secondary_stat
            ? `<span class="gp-news-card__stats"><strong>${escapeHtml(presentation.primary_stat)}</strong><small>${escapeHtml(presentation.secondary_stat)}</small></span>`
            : "";
        const actionLabel = ACTION_LABELS[action.action_type] || "OTWÓRZ";
        const cta = interactive ? `<span class="gp-news-card__cta"><svg aria-hidden="true"><use href="/static/images/googleplx/icons/googleplex-news-icons.svg#open"></use></svg> ${escapeHtml(actionLabel)}</span>` : `<span class="gp-news-card__stamp">READ ONLY</span>`;
        return `<${tag}${type} class="gp-news-card gp-news-card--${presentation.weight}" data-layout-index="${layoutIndex}" data-interactive="${interactive}" data-state="${presentation.state}" data-asset-family="${presentation.asset_family}" data-asset-state="${presentation.asset_state}"${actionData}>
            ${assetMarkup(presentation)}
            <span class="gp-news-card__shade" aria-hidden="true"></span>
            <span class="gp-news-card__body">
                <span class="gp-news-card__eyebrow">${escapeHtml(content.category)} // ${escapeHtml(content.truth_class)}</span>
                <span class="gp-news-card__title">${escapeHtml(content.title)}</span>
                <span class="gp-news-card__summary">${escapeHtml(content.summary)}</span>
                ${stats}
                <span class="gp-news-card__footer"><small>${escapeHtml(content.source)}</small>${cta}</span>
            </span>
        </${tag}>`;
    };

    const statsMarkup = stats => stats.map(item => `<span class="gp-news-stat" data-asset-state="${item.state}"><small>${escapeHtml(item.label)}</small><strong>${escapeHtml(item.value)}</strong></span>`).join("");

    const renderLoading = root => {
        if (!root) return;
        root.innerHTML = `<main class="gp-home gp-home--loading" aria-busy="true"><section class="gp-news-loading"><strong>GOOGLEPLEX NEWS</strong><span></span><p>Synchronizacja canonical sources…</p></section></main>`;
    };

    const renderError = (root, message) => {
        if (!root) return;
        root.innerHTML = `<main class="gp-home gp-home--error"><section class="gp-news-system-panel"><strong>NEWS FEED UNAVAILABLE</strong><p>${escapeHtml(message || "Nie udało się pobrać Googleplex News. Wyszukiwarka pozostaje aktywna.")}</p></section></main>`;
    };

    const renderHome = (root, rawSnapshot, options = {}) => {
        if (!root) return null;
        const snapshot = normalizeSnapshot(rawSnapshot);
        if (!snapshot) {
            renderError(root, "Nieprawidłowy kontrakt Googleplex News.");
            return null;
        }
        const entries = snapshot.entries;
        const cards = entries.length ? entries.map(cardMarkup).join("") : `<article class="gp-news-card gp-news-card--small" data-layout-index="0" data-interactive="false" data-state="stale" data-asset-family="stamp"><span class="gp-news-card__body"><span class="gp-news-card__eyebrow">SYSTEM</span><span class="gp-news-card__title">Brak nowych wpisów</span><span class="gp-news-card__summary">Canonical feed pozostaje pusty.</span><span class="gp-news-card__stamp">READ ONLY</span></span></article>`;
        root.innerHTML = `<main class="gp-home" data-state-version="${escapeHtml(snapshot.state_version)}">
            <header class="gp-home__intro"><span>WORLD INTELLIGENCE // EDITORIAL GRID</span><strong>${entries.length} SIGNALS</strong></header>
            <section class="gp-news-grid" aria-label="Googleplex News">${cards}</section>
            <section class="gp-news-stats" aria-label="Global status">${statsMarkup(snapshot.global_stats)}</section>
            <footer class="gp-news-protocol"><span>SOURCE: ${escapeHtml(snapshot.protocol_status.source)}</span><span>INTEGRITY: ${escapeHtml(snapshot.protocol_status.integrity)}</span><span>ACCESS: ${escapeHtml(snapshot.protocol_status.access_mode)}</span><span>OLLAMA: ${snapshot.protocol_status.ollama_used ? "ACTIVE" : "NOT USED"}</span></footer>
        </main>`;
        const entryById = new Map(entries.map(entry => [entry.content.news_id, entry]));
        root.querySelectorAll("[data-gp-news-action]").forEach(button => {
            button.addEventListener("click", async event => {
                const target = event.currentTarget;
                if (target.dataset.inFlight === "1") return;
                const entry = entryById.get(target.dataset.gpNewsAction || "");
                if (!entry || entry.action.kind !== "ACTIONABLE" || typeof options.onAction !== "function") return;
                target.dataset.inFlight = "1";
                target.disabled = true;
                try {
                    await options.onAction(entry);
                } finally {
                    target.dataset.inFlight = "0";
                    target.disabled = false;
                }
            });
        });
        root.querySelectorAll(".gp-news-card__asset--image img").forEach(image => {
            image.addEventListener("error", () => {
                image.closest(".gp-news-card__asset")?.classList.add("is-missing");
                image.remove();
            }, {once: true});
        });
        return snapshot;
    };

    global.GoogleplexNewsUI = Object.freeze({normalizeSnapshot, renderLoading, renderError, renderHome});
})(typeof window !== "undefined" ? window : globalThis);
