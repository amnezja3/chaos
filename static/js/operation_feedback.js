(function operationFeedbackBootstrap(global) {
    "use strict";

    const CONFIG_ELEMENT_ID = "operation-feedback-config";
    const PROFILE_URL = "/static/data/operation_feedback.v1.json";
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
    let profilePromise = null;

    function ensureObject(value, label) {
        if (!value || typeof value !== "object" || Array.isArray(value)) {
            throw new Error(`OFS invalid ${label}`);
        }
        return value;
    }

    function validateFeedbackConfig(rawConfig) {
        const config = ensureObject(rawConfig, "config");
        if (config.schema_version !== "1.0.0") throw new Error("OFS unsupported schema_version");
        [
            "defaults", "duration_profiles", "scene_library", "security_library",
            "transport_library", "choice_library", "completion_library",
            "failure_library", "operations"
        ].forEach(section => ensureObject(config[section], section));

        const profile = ensureObject(config.operations.scan_ports, "scan_ports profile");
        if (profile.action_key !== "scan_ports" || profile.enabled !== true) {
            throw new Error("OFS invalid scan_ports profile identity");
        }
        if (Object.prototype.hasOwnProperty.call(profile, "security_keys")
            || Object.prototype.hasOwnProperty.call(profile, "interaction_types")) {
            throw new Error("OFS security profile must use an explicit matrix");
        }
        if (!Array.isArray(profile.scene_pools) || !profile.scene_pools.length) {
            throw new Error("OFS scan_ports scene pool is empty");
        }
        profile.scene_pools.forEach(sceneId => {
            const scene = ensureObject(config.scene_library[sceneId], `scene ${sceneId}`);
            if (!Array.isArray(scene.sequence) || !scene.sequence.length) {
                throw new Error(`OFS scene ${sceneId} has no sequence`);
            }
            if (scene.sequence.some(role => !["operation", "security", "transition"].includes(role))) {
                throw new Error(`OFS scene ${sceneId} has unsupported role`);
            }
            if (scene.sequence.includes("operation")
                && (!Array.isArray(scene.operation_lines) || !scene.operation_lines.length)) {
                throw new Error(`OFS scene ${sceneId} has no operation lines`);
            }
            if (scene.sequence.includes("transition")
                && (!Array.isArray(scene.transition_lines) || !scene.transition_lines.length)) {
                throw new Error(`OFS scene ${sceneId} has no transition lines`);
            }
            const pause = scene.pause_ms;
            if (!Array.isArray(pause) || pause.length !== 2
                || pause.some(value => !Number.isFinite(value) || value < 0 || value > 10000)) {
                throw new Error(`OFS scene ${sceneId} has invalid timing`);
            }
        });
        Object.entries(config.duration_profiles).forEach(([durationId, duration]) => {
            if (!Number.isFinite(duration.min_elapsed_ms) || duration.min_elapsed_ms < 0) {
                throw new Error(`OFS duration ${durationId} has invalid threshold`);
            }
            if (!Array.isArray(duration.scene_pool) || !duration.scene_pool.length) {
                throw new Error(`OFS duration ${durationId} has no scenes`);
            }
            duration.scene_pool.forEach(sceneId => {
                if (!profile.scene_pools.includes(sceneId)) {
                    throw new Error(`OFS duration ${durationId} references forbidden scene ${sceneId}`);
                }
            });
        });
        const securityMatrix = ensureObject(profile.security, "scan_ports security matrix");
        Object.entries(securityMatrix).forEach(([securityKey, interactions]) => {
            const security = ensureObject(config.security_library[securityKey], `security ${securityKey}`);
            const libraryInteractions = ensureObject(security.interactions, `security ${securityKey} interactions`);
            if (!Array.isArray(interactions) || !interactions.length) {
                throw new Error(`OFS security ${securityKey} has no allowed interactions`);
            }
            interactions.forEach(interaction => {
                if (!Array.isArray(libraryInteractions[interaction]) || !libraryInteractions[interaction].length) {
                    throw new Error(`OFS invalid pair ${securityKey} + ${interaction}`);
                }
            });
        });
        const validatePlainText = value => {
            if (typeof value === "string" && /<[^>]+>/.test(value)) {
                throw new Error("OFS content must be plain text");
            }
            if (Array.isArray(value)) value.forEach(validatePlainText);
            else if (value && typeof value === "object") Object.values(value).forEach(validatePlainText);
        };
        validatePlainText(config);
        return config;
    }

    function loadFeedbackConfig() {
        if (!profilePromise) {
            profilePromise = global.fetch(PROFILE_URL, { credentials: "same-origin" })
                .then(response => {
                    if (!response.ok) throw new Error(`OFS profile HTTP ${response.status}`);
                    return response.json();
                })
                .then(validateFeedbackConfig)
                .catch(error => {
                    profilePromise = null;
                    throw error;
                });
        }
        return profilePromise;
    }

    function randomItem(items, random = Math.random, excluded = null) {
        const source = Array.isArray(items) ? items.filter(item => item !== excluded) : [];
        const pool = source.length ? source : (Array.isArray(items) ? items : []);
        if (!pool.length) return null;
        return pool[Math.min(pool.length - 1, Math.floor(random() * pool.length))];
    }

    function durationProfileFor(config, elapsedMs) {
        const entries = Object.entries(config.duration_profiles)
            .sort((left, right) => Number(left[1].min_elapsed_ms) - Number(right[1].min_elapsed_ms));
        let selected = entries[0];
        entries.forEach(entry => {
            if (elapsedMs >= Number(entry[1].min_elapsed_ms || 0)) selected = entry;
        });
        return selected ? { id: selected[0], ...selected[1] } : { id: "instant", scene_pool: [] };
    }

    function chooseLine(lines, history, random) {
        const selected = randomItem(lines, random, history.last_line);
        if (selected) history.last_line = selected;
        return selected;
    }

    function composeScene({ config, profile, securityState, history, elapsedMs, random = Math.random }) {
        const duration = durationProfileFor(config, elapsedMs);
        const allowedScenes = duration.scene_pool.filter(sceneId => profile.scene_pools.includes(sceneId));
        const sceneId = randomItem(allowedScenes, random, history.last_scene)
            || randomItem(profile.scene_pools, random, history.last_scene);
        const scene = config.scene_library[sceneId];
        if (!scene) throw new Error("OFS composer has no valid scene");

        const activeSecurity = Object.keys(profile.security).filter(key => securityState[key] === true);
        const lines = [];
        scene.sequence.forEach(role => {
            let line = null;
            if (role === "security" && activeSecurity.length) {
                const securityKey = randomItem(activeSecurity, random, history.last_security);
                const allowedInteractions = profile.security[securityKey];
                const interaction = randomItem(allowedInteractions, random);
                const variants = config.security_library[securityKey].interactions[interaction];
                line = chooseLine(variants, history, random);
                history.last_security = securityKey;
            } else if (role === "transition") {
                line = chooseLine(scene.transition_lines, history, random);
            } else {
                line = chooseLine(scene.operation_lines, history, random);
            }
            if (line && lines[lines.length - 1] !== line) lines.push(line);
        });
        history.last_scene = sceneId;
        const minLines = Math.max(1, Number(scene.min_lines || 1));
        const maxLines = Math.max(minLines, Number(scene.max_lines || config.defaults.max_lines || 5));
        let fillAttempts = 0;
        while (lines.length < minLines && fillAttempts < 12) {
            const fallbackLine = chooseLine(scene.operation_lines, history, random)
                || chooseLine(scene.transition_lines, history, random);
            if (fallbackLine && lines[lines.length - 1] !== fallbackLine) lines.push(fallbackLine);
            fillAttempts += 1;
        }
        const pause = scene.pause_ms || config.defaults.scene_delay_ms || [900, 1600];
        const delayMs = Math.round(Number(pause[0]) + random() * (Number(pause[1]) - Number(pause[0])));
        return {
            scene_id: sceneId,
            duration_profile: duration.id,
            lines: lines.slice(0, maxLines),
            min_lines: minLines,
            delay_ms: delayMs,
            transition: scene.transition || "replace"
        };
    }

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
            this.now = typeof options.now === "function" ? options.now : () => global.performance.now();
            this.random = typeof options.random === "function" ? options.random : Math.random;
            this.configLoader = options.configLoader || loadFeedbackConfig;
            this.onTrace = typeof options.onTrace === "function" ? options.onTrace : function noop() {};
            this.state = "idle";
            this.disposed = false;
            this.timers = new Set();
            this.panel = null;
            this.config = null;
            this.profile = null;
            this.startedAt = 0;
            this.history = { last_scene: null, last_security: null, last_line: null };
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
            this.startedAt = this.now();
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
            Promise.resolve(this.configLoader()).then(config => {
                if (this.disposed || this.state !== "running") return;
                this.config = validateFeedbackConfig(config);
                this.profile = this.config.operations[this.actionKey];
                if (!this.profile || !this.profile.presentation_modes.includes(this.presentationMode)) {
                    throw new Error("OFS profile does not support renderer");
                }
                this.trace("feedback_profile_loaded", { content_version: this.config.content_version });
                this.renderNextScene();
            }).catch(error => {
                if (this.disposed || this.state !== "running") return;
                this.trace("feedback_profile_failed", { completion_reason: error.message || "invalid_profile" });
                this.setTimer(() => {
                    if (this.state !== "running") return;
                    this.transition("awaiting_payload");
                    this.render("Oczekiwanie na odpowiedz...", [
                        "Sesja pozostaje aktywna.",
                        "Wynik nie zostal jeszcze potwierdzony."
                    ]);
                }, 1200);
            });
            return this;
        }

        renderNextScene() {
            if (this.disposed || (this.state !== "running" && this.state !== "awaiting_payload")) return;
            const elapsedMs = Math.max(0, this.now() - this.startedAt);
            const scene = composeScene({
                config: this.config,
                profile: this.profile,
                securityState: this.securityState,
                history: this.history,
                elapsedMs,
                random: this.random
            });
            if (this.state === "awaiting_payload") this.transition("running");
            this.render("Operacja w toku...", scene.lines);
            this.trace("feedback_scene_started", {
                scene_id: scene.scene_id,
                duration_profile: scene.duration_profile,
                elapsed_ms: Math.round(elapsedMs)
            });
            this.setTimer(() => {
                if (this.disposed || this.state !== "running") return;
                this.renderNextScene();
            }, scene.delay_ms);
        }

        complete(payload = {}) {
            if (this.disposed || TERMINAL_STATES.has(this.state)) return;
            this.clearTimers();
            this.transition("completing");
            const success = payload && payload.success === true;
            const completion = this.config && this.profile
                ? this.config.completion_library[this.profile.completion_pool]
                : null;
            const completionLines = completion
                ? (success ? completion.success : completion.failure)
                : null;
            this.render(success ? "Potwierdzono wynik." : "Operacja zakonczona.", [
                randomItem(completionLines, this.random)
                    || (success ? "Runtime potwierdzil powodzenie." : "Runtime zwrocil wynik operacji.")
            ], success ? "success" : "failure");
            this.trace("feedback_payload_received", { success });
            this.setTimer(() => this.dispose("payload_complete"), 450);
        }

        fail(reason = "request_failed") {
            if (this.disposed || TERMINAL_STATES.has(this.state)) return;
            this.clearTimers();
            this.transition("failed");
            const failurePool = this.config && this.profile
                ? this.config.failure_library[this.profile.failure_pool]
                : null;
            this.render("Blad odpowiedzi runtime.", [
                randomItem(failurePool, this.random) || "Operacja nie zostala potwierdzona."
            ], "failure");
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
        sanitizeSecurityState,
        validateFeedbackConfig,
        loadFeedbackConfig,
        durationProfileFor,
        composeScene
    });
})(window);
