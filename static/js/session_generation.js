(function initChaosSessionGeneration(root, factory) {
    const api = factory(root || {});
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    }
    if (root) {
        root.ChaosSessionGeneration = api;
        if (root.document) api.install();
    }
})(typeof globalThis !== "undefined" ? globalThis : this, function sessionGenerationFactory(root) {
    "use strict";

    const CHANNEL_NAME = "chaos-session-generation-v1";
    const DEFAULT_HEADER = "X-Chaos-Session-Generation";
    const USER_HEADER = "X-Chaos-Session-User";
    const ERROR_HEADER = "X-Chaos-Session-Error";

    const state = {
        installed: false,
        invalidated: false,
        generation: "",
        queryToken: "",
        username: "",
        header: DEFAULT_HEADER,
        nativeFetch: null,
        controllers: new Set(),
        channel: null,
        redirectScheduled: false,
    };

    class SessionGenerationMismatchError extends Error {
        constructor(reason) {
            super(`Session generation mismatch: ${reason}`);
            this.name = "SessionGenerationMismatchError";
            this.code = "session_generation_mismatch";
            this.reason = reason;
        }
    }

    function readDocumentConfig() {
        const node = root.document?.getElementById?.("session-generation-config");
        if (!node) return {};
        try {
            const parsed = JSON.parse(node.textContent || "{}");
            return parsed && typeof parsed === "object" ? parsed : {};
        } catch (_error) {
            return {};
        }
    }

    function sameOriginRequest(input) {
        const raw = typeof input === "string"
            ? input
            : (typeof input?.url === "string" ? input.url : input?.href);
        // Unknown request-like objects are not safe to decorate. Native fetch
        // will validate them; the bridge must never guess that they are local.
        if (typeof raw !== "string" || !raw) return false;
        try {
            const base = root.location?.href || "http://localhost/";
            const target = new URL(raw, base);
            const origin = root.location?.origin || new URL(base).origin;
            return target.origin === origin;
        } catch (_error) {
            return false;
        }
    }

    function responseRequiresIdentityHeaders(input) {
        const raw = typeof input === "string"
            ? input
            : (typeof input?.url === "string" ? input.url : input?.href);
        if (typeof raw !== "string" || !raw) return false;
        try {
            const base = root.location?.href || "http://localhost/";
            const path = new URL(raw, base).pathname;
            if (path.startsWith("/static/")) return false;
            return !new Set([
                "/register",
                "/api/register-check",
            ]).has(path);
        } catch (_error) {
            return false;
        }
    }

    function dispatchInvalidation(reason) {
        const detail = { reason, username: state.username };
        try {
            const EventCtor = root.CustomEvent;
            if (EventCtor && root.dispatchEvent) {
                root.dispatchEvent(new EventCtor("chaos:session-invalidated", { detail }));
            }
        } catch (_error) {
            // A full document teardown below remains authoritative.
        }
    }

    function clearUserScopedClientState() {
        try {
            root.sessionStorage?.clear?.();
        } catch (_error) {
            // Storage can be disabled by browser policy.
        }
        try {
            root.document?.querySelectorAll?.("iframe.map-frame, iframe[src^='/map']")
                ?.forEach((frame) => {
                    frame.removeAttribute("src");
                    frame.remove?.();
                });
        } catch (_error) {
            // Navigation still destroys the document and its child frames.
        }
    }

    function invalidate(reason = "mismatch", options = {}) {
        if (state.invalidated) return false;
        state.invalidated = true;
        state.controllers.forEach((controller) => {
            try { controller.abort(); } catch (_error) { /* noop */ }
        });
        state.controllers.clear();
        dispatchInvalidation(reason);
        clearUserScopedClientState();

        if (options.redirect !== false && !state.redirectScheduled) {
            state.redirectScheduled = true;
            const navigate = () => {
                try {
                    root.location?.replace?.("/");
                } catch (_error) {
                    // The caller still receives a mismatch error and cannot
                    // apply the stale response.
                }
            };
            if (typeof root.setTimeout === "function") root.setTimeout(navigate, 0);
            else navigate();
        }
        return true;
    }

    function combinedSignal(callerSignal, controller) {
        if (!callerSignal) return controller.signal;
        if (root.AbortSignal?.any) {
            return root.AbortSignal.any([callerSignal, controller.signal]);
        }
        if (callerSignal.aborted) controller.abort();
        else callerSignal.addEventListener?.("abort", () => controller.abort(), { once: true });
        return controller.signal;
    }

    function responseHeader(response, name) {
        try {
            return String(response?.headers?.get?.(name) || "").trim();
        } catch (_error) {
            return "";
        }
    }

    function validateResponse(response, requestGeneration, options = {}) {
        if (state.invalidated) {
            throw new SessionGenerationMismatchError("client_invalidated");
        }
        if (requestGeneration !== state.generation) {
            invalidate("generation_changed_during_request");
            throw new SessionGenerationMismatchError("generation_changed_during_request");
        }

        const responseGeneration = responseHeader(response, state.header);
        const responseUsername = responseHeader(response, USER_HEADER);
        const responseError = responseHeader(response, ERROR_HEADER);
        if (responseError === "mismatch" || response?.status === 409 && responseError) {
            invalidate("server_generation_mismatch");
            throw new SessionGenerationMismatchError("server_generation_mismatch");
        }
        if (response?.status === 401) {
            invalidate("session_unauthorized");
            throw new SessionGenerationMismatchError("session_unauthorized");
        }
        if (
            options.requireIdentityHeaders === true
            && (!responseGeneration || !responseUsername)
        ) {
            invalidate("response_identity_headers_missing");
            throw new SessionGenerationMismatchError("response_identity_headers_missing");
        }
        if (responseGeneration && responseGeneration !== state.generation) {
            invalidate("response_generation_mismatch");
            throw new SessionGenerationMismatchError("response_generation_mismatch");
        }
        if (responseUsername && state.username && responseUsername !== state.username) {
            invalidate("response_user_mismatch");
            throw new SessionGenerationMismatchError("response_user_mismatch");
        }
        return response;
    }

    function installFetchBridge(fetchImpl) {
        const nativeFetch = fetchImpl || root.fetch;
        if (typeof nativeFetch !== "function") return false;
        state.nativeFetch = nativeFetch.bind ? nativeFetch.bind(root) : nativeFetch;

        root.fetch = async function generationBoundFetch(input, init = {}) {
            if (!sameOriginRequest(input) || !state.generation) {
                return state.nativeFetch(input, init);
            }
            if (state.invalidated) {
                throw new SessionGenerationMismatchError("client_invalidated");
            }

            const HeadersCtor = root.Headers || (typeof Headers !== "undefined" ? Headers : null);
            const AbortControllerCtor = root.AbortController
                || (typeof AbortController !== "undefined" ? AbortController : null);
            const inheritedHeaders = init.headers || input?.headers || {};
            const headers = HeadersCtor ? new HeadersCtor(inheritedHeaders) : { ...inheritedHeaders };
            if (HeadersCtor) headers.set(state.header, state.generation);
            else headers[state.header] = state.generation;

            const requestGeneration = state.generation;
            const requestInit = { ...init, headers };
            let controller = null;
            if (AbortControllerCtor) {
                controller = new AbortControllerCtor();
                requestInit.signal = combinedSignal(init.signal || input?.signal, controller);
                state.controllers.add(controller);
            }
            try {
                const response = await state.nativeFetch(input, requestInit);
                return validateResponse(response, requestGeneration, {
                    requireIdentityHeaders: responseRequiresIdentityHeaders(input),
                });
            } finally {
                if (controller) state.controllers.delete(controller);
            }
        };
        return true;
    }

    function installBroadcastBridge() {
        const BroadcastCtor = root.BroadcastChannel;
        if (typeof BroadcastCtor !== "function" || !state.generation) return false;
        try {
            state.channel = new BroadcastCtor(CHANNEL_NAME);
            state.channel.onmessage = (event) => {
                const message = event?.data;
                if (!message || message.type !== "authenticated_session") return;
                if (message.generation !== state.generation || message.username !== state.username) {
                    invalidate("browser_session_replaced");
                }
            };
            state.channel.postMessage({
                type: "authenticated_session",
                generation: state.generation,
                username: state.username,
            });
            return true;
        } catch (_error) {
            state.channel = null;
            return false;
        }
    }

    function install(options = {}) {
        if (state.installed) return getState();
        const config = options.config || readDocumentConfig();
        state.generation = String(config.generation || "").trim();
        state.queryToken = String(config.query_token || "").trim();
        state.username = String(config.username || "").trim();
        state.header = String(config.header || DEFAULT_HEADER).trim() || DEFAULT_HEADER;
        state.installed = true;
        installFetchBridge(options.fetch);
        installBroadcastBridge();
        return getState();
    }

    function getState() {
        return {
            installed: state.installed,
            invalidated: state.invalidated,
            generation: state.generation,
            query_token: state.queryToken,
            username: state.username,
            header: state.header,
            active_requests: state.controllers.size,
        };
    }

    return {
        SessionGenerationMismatchError,
        install,
        invalidate,
        validateResponse,
        getState,
        constants: {
            CHANNEL_NAME,
            DEFAULT_HEADER,
            USER_HEADER,
            ERROR_HEADER,
        },
    };
});
