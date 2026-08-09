(function operationFeedbackBootstrap(global) {
    "use strict";

    const CONFIG_ELEMENT_ID = "operation-feedback-config";
    const CANONICAL_SECURITY_KEYS = new Set([
        "stealth_mode", "scan_detection", "exploit_protection", "vpn_enabled",
        "browser_protection", "os_hardening", "log_guardian", "process_monitor",
        "firewall", "log_integrity", "network_anomaly_detection", "spoofing_protection",
        "activity_monitor", "player_tracking", "system_visibility", "firewall_core",
        "kernel_guard", "system_integrity_check", "heap_protection", "memory_lock",
        "background_injection", "memory_guard", "vpn_blocker"
    ]);
    const TERMINAL_STATES = new Set(["disposed"]);
    const ALLOWED_TRANSITIONS = {
        idle: new Set(["starting", "cancelled", "disposed"]),
        starting: new Set(["running", "completing", "failed", "cancelled", "disposed"]),
        running: new Set(["awaiting_payload", "completing", "failed", "cancelled", "disposed"]),
        awaiting_payload: new Set(["running", "completing", "failed", "cancelled", "disposed"]),
        completing: new Set(["disposed"]),
        failed: new Set(["disposed"]),
        cancelled: new Set(["disposed"]),
        disposed: new Set()
    };
    let sessionSequence = 0;

    function readFlags() {
        const node = global.document && global.document.getElementById(CONFIG_ELEMENT_ID);
        if (!node) return { enabled: false, scan_ports: false };
        try {
            const parsed = JSON.parse(node.textContent || "{}");
            return {
                enabled: parsed.enabled === true,
                scan_ports: parsed.scan_ports === true
            };
        } catch (error) {
            console.warn("[OFS] Nieprawidlowy config; pozostaje legacy pending UI", error);
            return { enabled: false, scan_ports: false };
        }
    }

    function sanitizeSecurityState(source) {
        const normalized = {};
        const input = source && typeof source === "object" ? source : {};
        CANONICAL_SECURITY_KEYS.forEach(key => {
            const value = input[key];
            normalized[key] = value === true ? true : (value === false ? false : "unknown");
        });
        return Object.freeze(normalized);
    }

    function isEnabled(actionKey, flags = readFlags()) {
        const action = String(actionKey || "").trim();
        return flags.enabled === true && action === "scan_ports" && flags.scan_ports === true;
    }

    class OperationFeedbackSession {
        constructor(options = {}) {
            this.actionKey = String(options.actionKey || "").trim();
            this.presentationMode = String(options.presentationMode || "button_choice").trim();
            this.appId = String(options.appId || "").trim();
            this.flowId = String(options.flowId || "").trim();
            this.launchReceipt = String(options.launchReceipt || "").trim();
            this.rendererHost = options.rendererHost || null;
            this.appWindow = options.appWindow || null;
            this.securityState = sanitizeSecurityState(options.securityState);
            this.clock = options.clock || global;
            this.onTrace = typeof options.onTrace === "function" ? options.onTrace : function noop() {};
            this.state = "idle";
            this.disposed = false;
            this.timers = new Set();
            this.panel = null;
            sessionSequence += 1;
            this.sessionId = `${this.flowId || "local"}:${this.launchReceipt || this.appId || "app"}:${sessionSequence}`;
        }

        transition(nextState) {
            if (this.state === nextState) return;
            const allowed = ALLOWED_TRANSITIONS[this.state] || new Set();
            if (!allowed.has(nextState)) {
                throw new Error(`OFS invalid transition ${this.state} -> ${nextState}`);
            }
            this.state = nextState;
        }

        trace(eventName, details = {}) {
            this.onTrace(eventName, {
                session_id: this.sessionId,
                action_key: this.actionKey,
                presentation_mode: this.presentationMode,
                state: this.state,
                ...details
            });
        }

        setTimer(callback, delayMs) {
            const timerId = this.clock.setTimeout(() => {
                this.timers.delete(timerId);
                if (!this.disposed) callback();
            }, delayMs);
            this.timers.add(timerId);
            return timerId;
        }

        clearTimers() {
            this.timers.forEach(timerId => this.clock.clearTimeout(timerId));
            this.timers.clear();
        }

        ensurePanel() {
            if (!this.rendererHost || !this.rendererHost.isConnected) {
                throw new Error("OFS renderer host is unavailable");
            }
            if (this.panel && this.panel.isConnected) return this.panel;
            const panel = global.document.createElement("section");
            panel.className = "operation-feedback-panel";
            panel.dataset.ofsSessionId = this.sessionId;
            panel.setAttribute("aria-live", "polite");

            const title = global.document.createElement("div");
            title.className = "operation-feedback-title";
            title.textContent = "OPERATION FEEDBACK";
            panel.appendChild(title);

            const status = global.document.createElement("div");
            status.className = "operation-feedback-status";
            panel.appendChild(status);

            const lines = global.document.createElement("div");
            lines.className = "operation-feedback-lines";
            panel.appendChild(lines);

            this.rendererHost.appendChild(panel);
            this.panel = panel;
            return panel;
        }

        render(statusText, lineItems, tone = "pending") {
            const panel = this.ensurePanel();
            panel.dataset.tone = tone;
            const status = panel.querySelector(".operation-feedback-status");
            const lines = panel.querySelector(".operation-feedback-lines");
            status.textContent = String(statusText || "");
            lines.replaceChildren();
            (Array.isArray(lineItems) ? lineItems : []).slice(0, 5).forEach(item => {
                const line = global.document.createElement("div");
                line.className = "operation-feedback-line";
                line.textContent = String(item || "");
                lines.appendChild(line);
            });
        }

        start() {
            this.transition("starting");
            this.render("Uruchamianie sesji...", [
                `Akcja: ${this.actionKey}`,
                "Przygotowanie lokalnej prezentacji.",
                "Oczekiwanie na runtime."
            ]);
            this.trace("feedback_session_started");
            this.transition("running");
            this.render("Operacja w toku...", [
                `Aplikacja: ${this.appId || "narzedzie"}`,
                "Request przekazany do runtime.",
                "Oczekiwanie na potwierdzony payload."
            ]);
            this.setTimer(() => {
                if (this.state !== "running") return;
                this.transition("awaiting_payload");
                this.render("Oczekiwanie na odpowiedz...", [
                    "Sesja pozostaje aktywna.",
                    "Wynik nie zostal jeszcze potwierdzony."
                ]);
            }, 1200);
            return this;
        }

        complete(payload = {}) {
            if (this.disposed || TERMINAL_STATES.has(this.state)) return;
            this.clearTimers();
            this.transition("completing");
            const success = payload && payload.success === true;
            this.render(success ? "Potwierdzono wynik." : "Operacja zakonczona.", [
                success ? "Runtime potwierdzil powodzenie." : "Runtime zwrocil wynik operacji."
            ], success ? "success" : "failure");
            this.trace("feedback_payload_received", { success });
            this.setTimer(() => this.dispose("payload_complete"), 450);
        }

        fail(reason = "request_failed") {
            if (this.disposed || TERMINAL_STATES.has(this.state)) return;
            this.clearTimers();
            this.transition("failed");
            this.render("Blad odpowiedzi runtime.", ["Operacja nie zostala potwierdzona."], "failure");
            this.trace("feedback_failed", { completion_reason: String(reason || "request_failed") });
            this.setTimer(() => this.dispose(reason), 450);
        }

        cancel(reason = "cancelled") {
            if (this.disposed) return;
            this.clearTimers();
            if (this.state === "completing" || this.state === "failed") {
                this.dispose(reason);
                return;
            }
            if (this.state !== "cancelled") this.transition("cancelled");
            this.trace("feedback_cancelled", { completion_reason: String(reason || "cancelled") });
            this.dispose(reason);
        }

        dispose(reason = "disposed") {
            if (this.disposed) return;
            this.clearTimers();
            if (this.state !== "disposed") this.transition("disposed");
            this.disposed = true;
            if (this.panel && this.panel.isConnected) this.panel.remove();
            if (this.appWindow && this.appWindow._operationFeedbackSession === this) {
                this.appWindow._operationFeedbackSession = null;
            }
            this.trace("feedback_disposed", { completion_reason: String(reason || "disposed") });
        }
    }

    function createSession(options = {}) {
        if (!isEnabled(options.actionKey, options.flags || readFlags())) return null;
        if (options.presentationMode && options.presentationMode !== "button_choice") return null;
        try {
            if (options.appWindow && options.appWindow._operationFeedbackSession) {
                options.appWindow._operationFeedbackSession.cancel("new_request");
            }
            const session = new OperationFeedbackSession(options).start();
            if (options.appWindow) options.appWindow._operationFeedbackSession = session;
            return session;
        } catch (error) {
            console.warn("[OFS] Start nieudany; pozostaje legacy pending UI", error);
            return null;
        }
    }

    function disposeWindowSession(appWindow, reason = "window_closed") {
        const session = appWindow && appWindow._operationFeedbackSession;
        if (session) session.cancel(reason);
    }

    global.OperationFeedbackSystem = Object.freeze({
        OperationFeedbackSession,
        createSession,
        disposeWindowSession,
        isEnabled,
        readFlags,
        sanitizeSecurityState
    });
})(window);
