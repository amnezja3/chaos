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
        const stateSchema = ensureObject(profile.presentation_state_schema, "presentation state schema");
        Object.values(config.security_library).forEach(security => {
            Object.values((security && security.interactions) || {}).forEach(variants => {
                (Array.isArray(variants) ? variants : []).forEach(variant => {
                    Object.entries((variant && typeof variant === "object" && variant.when) || {}).forEach(([key, value]) => {
                        if (!Array.isArray(stateSchema[key]) || !stateSchema[key].includes(value)) {
                            throw new Error("OFS variant references undeclared presentation state");
                        }
                    });
                });
            });
        });
        if (!Array.isArray(profile.choice_pools) || profile.choice_pools.length < 3) {
            throw new Error("OFS scan_ports requires three presentation choices");
        }
        profile.choice_pools.forEach(choiceId => {
            const choice = ensureObject(config.choice_library[choiceId], `choice ${choiceId}`);
            if (!choiceId.startsWith("feedback.") || choice.choice_id !== choiceId
                || choice.effect_scope !== "presentation") {
                throw new Error(`OFS invalid presentation choice ${choiceId}`);
            }
            if (!Array.isArray(choice.options) || choice.options.length < 2
                || !Number.isFinite(choice.timeout_ms) || choice.timeout_ms <= 0 || choice.timeout_ms > 30000) {
                throw new Error(`OFS invalid choice contract ${choiceId}`);
            }
            if (!choice.options.some(option => option.value === choice.default_value)) {
                throw new Error(`OFS choice ${choiceId} has no valid default`);
            }
            choice.options.forEach(option => {
                Object.entries(ensureObject(option.set, `choice ${choiceId} mutation`)).forEach(([key, value]) => {
                    if (!Array.isArray(stateSchema[key]) || !stateSchema[key].includes(value)) {
                        throw new Error(`OFS choice ${choiceId} mutates undeclared state`);
                    }
                });
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

    function variantMatchesState(variant, presentationState) {
        if (!variant || typeof variant !== "object" || Array.isArray(variant)) return true;
        const when = variant.when;
        if (!when || typeof when !== "object") return true;
        return Object.entries(when).every(([key, value]) => presentationState[key] === value);
    }

    function eligibleVariantTexts(variants, presentationState) {
        const eligible = (Array.isArray(variants) ? variants : []).filter(
            variant => variantMatchesState(variant, presentationState)
        );
        const conditional = eligible.filter(
            variant => variant && typeof variant === "object" && !Array.isArray(variant) && variant.when
        );
        const preferred = conditional.length ? conditional : eligible;
        return preferred.map(variant => typeof variant === "string" ? variant : variant.text).filter(Boolean);
    }

    function applicationLines(applicationContent, slot, presentationState) {
        const structured = applicationContent && applicationContent.structured;
        const structuredLines = structured
            ? eligibleVariantTexts(structured[slot], presentationState)
            : [];
        if (structuredLines.length) return { lines: structuredLines, source: "app_structured" };
        const legacyLines = applicationContent && applicationContent.legacy
            ? applicationContent.legacy[slot]
            : [];
        if (Array.isArray(legacyLines) && legacyLines.length) {
            return { lines: legacyLines, source: "app_legacy" };
        }
        return { lines: [], source: "global_fallback" };
    }

    function composeScene({
        config, profile, securityState, history, elapsedMs, random = Math.random,
        presentationState = {}, applicationContent = null
    }) {
        const duration = durationProfileFor(config, elapsedMs);
        const allowedScenes = duration.scene_pool.filter(sceneId => profile.scene_pools.includes(sceneId));
        const sceneId = randomItem(allowedScenes, random, history.last_scene)
            || randomItem(profile.scene_pools, random, history.last_scene);
        const scene = config.scene_library[sceneId];
        if (!scene) throw new Error("OFS composer has no valid scene");

        const activeSecurity = Object.keys(profile.security).filter(key => securityState[key] === true);
        const sceneOperationLines = eligibleVariantTexts(scene.operation_lines, presentationState);
        const sceneTransitionLines = eligibleVariantTexts(scene.transition_lines, presentationState);
        const lines = [];
        const contentSources = [];
        scene.sequence.forEach(role => {
            let line = null;
            if (role === "security" && activeSecurity.length) {
                const securityKey = randomItem(activeSecurity, random, history.last_security);
                const allowedInteractions = profile.security[securityKey];
                const interaction = randomItem(allowedInteractions, random);
                const structuredSecurity = applicationContent && applicationContent.structured
                    && applicationContent.structured.security
                    && applicationContent.structured.security[securityKey];
                const appVariants = structuredSecurity && structuredSecurity[interaction]
                    ? eligibleVariantTexts(structuredSecurity[interaction], presentationState)
                    : [];
                const globalVariants = eligibleVariantTexts(
                    config.security_library[securityKey].interactions[interaction],
                    presentationState
                );
                line = chooseLine(appVariants.length ? appVariants : globalVariants, history, random);
                contentSources.push(appVariants.length ? "app_structured" : "global_fallback");
                history.last_security = securityKey;
            } else if (role === "transition") {
                const content = applicationLines(applicationContent, "transition", presentationState);
                line = chooseLine(content.lines.length ? content.lines : sceneTransitionLines, history, random);
                contentSources.push(content.lines.length ? content.source : "global_fallback");
            } else {
                const slot = sceneId === "boot" ? "boot" : "operation";
                const content = applicationLines(applicationContent, slot, presentationState);
                line = chooseLine(content.lines.length ? content.lines : sceneOperationLines, history, random);
                contentSources.push(content.lines.length ? content.source : "global_fallback");
            }
            if (line && lines[lines.length - 1] !== line) lines.push(line);
        });
        history.last_scene = sceneId;
        const minLines = Math.max(1, Number(scene.min_lines || 1));
        const maxLines = Math.max(minLines, Number(scene.max_lines || config.defaults.max_lines || 5));
        let fillAttempts = 0;
        while (lines.length < minLines && fillAttempts < 12) {
            const fallbackLine = chooseLine(sceneOperationLines, history, random)
                || chooseLine(sceneTransitionLines, history, random);
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
            transition: scene.transition || "replace",
            allow_choice: scene.allow_choice === true,
            content_source: contentSources.includes("app_structured")
                ? "app_structured"
                : (contentSources.includes("app_legacy") ? "app_legacy" : "global_fallback")
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

    function safeContentText(value, { allowOutcome = false } = {}) {
        if (typeof value !== "string") return null;
        const text = value.trim().replace(/\s+/g, " ").slice(0, 240);
        if (!text || /<[^>]+>/.test(text)) return null;
        if (!allowOutcome && /(sukces|success|captur|przej[eę]|owned|disabled|wy[lł][aą]cz|connection lost|timeout|packet loss|worker restart|reconnect)/i.test(text)) {
            return null;
        }
        return text;
    }

    function safeContentLines(values, options = {}) {
        const source = Array.isArray(values) ? values : (values ? [values] : []);
        return source.map(value => safeContentText(value, options)).filter(Boolean).slice(0, 20);
    }

    function sanitizeStructuredVariants(values) {
        const source = Array.isArray(values) ? values : [];
        return source.map(value => {
            if (typeof value === "string") return safeContentText(value);
            if (!value || typeof value !== "object") return null;
            const text = safeContentText(value.text);
            const when = value.when && typeof value.when === "object" && !Array.isArray(value.when)
                ? Object.fromEntries(Object.entries(value.when).map(([key, item]) => [String(key), String(item)]))
                : null;
            return text ? { text, when } : null;
        }).filter(Boolean).slice(0, 20);
    }

    function deepFreeze(value) {
        if (!value || typeof value !== "object" || Object.isFrozen(value)) return value;
        Object.values(value).forEach(deepFreeze);
        return Object.freeze(value);
    }

    function projectApplicationContent(appData = {}) {
        const levels = Array.isArray(appData.levels) ? appData.levels : [];
        const level = levels[0] && typeof levels[0] === "object" ? levels[0] : {};
        const legacy = {
            boot: safeContentLines([level.command]),
            operation: safeContentLines([
                ...(Array.isArray(level.list) ? level.list : []),
                ...(Array.isArray(level.logs) ? level.logs : []),
                ...(Array.isArray(level.steps) ? level.steps : [])
            ]),
            transition: safeContentLines([level.text, level.description, appData.description]),
            completion: {
                success: safeContentLines([level.result_success], { allowOutcome: true }),
                failure: safeContentLines([level.result_failure], { allowOutcome: true })
            }
        };
        const rawStructured = appData.feedback_content;
        let structured = null;
        if (rawStructured && rawStructured.schema_version === "1.0.0") {
            const sceneLines = rawStructured.scene_lines || {};
            const security = {};
            Object.entries(rawStructured.security || {}).forEach(([securityKey, interactions]) => {
                if (!CANONICAL_SECURITY_KEYS.has(securityKey) || !interactions || typeof interactions !== "object") return;
                security[securityKey] = {};
                Object.entries(interactions).forEach(([interaction, variants]) => {
                    security[securityKey][interaction] = sanitizeStructuredVariants(variants);
                });
            });
            structured = {
                boot: sanitizeStructuredVariants(sceneLines.boot),
                operation: sanitizeStructuredVariants(sceneLines.operation),
                transition: sanitizeStructuredVariants(sceneLines.transition),
                security,
                completion: {
                    success: safeContentLines(rawStructured.completion && rawStructured.completion.success, { allowOutcome: true }),
                    failure: safeContentLines(rawStructured.completion && rawStructured.completion.failure, { allowOutcome: true })
                }
            };
        }
        return deepFreeze({
            title: safeContentText(
                (rawStructured && rawStructured.labels && rawStructured.labels.session_title)
                || level.title || appData.name || appData.id,
                { allowOutcome: true }
            ) || "OPERATION FEEDBACK",
            structured,
            legacy,
            interface: String(appData.interface || "")
        });
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
            this.applicationContent = options.applicationContent || projectApplicationContent({});
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
            this.presentationState = {};
            this.askedChoices = new Set();
            this.activeChoice = null;
            this.choiceTimeoutId = null;
            this.choiceTickId = null;
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
            this.choiceTimeoutId = null;
            this.choiceTickId = null;
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
            title.textContent = this.applicationContent.title || "OPERATION FEEDBACK";
            panel.appendChild(title);

            const status = global.document.createElement("div");
            status.className = "operation-feedback-status";
            panel.appendChild(status);

            const lines = global.document.createElement("div");
            lines.className = "operation-feedback-lines";
            panel.appendChild(lines);

            const choice = global.document.createElement("div");
            choice.className = "operation-feedback-choice";
            choice.hidden = true;
            panel.appendChild(choice);

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

        cancelTimer(timerId) {
            if (timerId === null || timerId === undefined) return;
            this.clock.clearTimeout(timerId);
            this.timers.delete(timerId);
        }

        clearChoice(disableOnly = false) {
            this.cancelTimer(this.choiceTimeoutId);
            this.cancelTimer(this.choiceTickId);
            this.choiceTimeoutId = null;
            this.choiceTickId = null;
            const container = this.panel && this.panel.querySelector(".operation-feedback-choice");
            if (container) {
                container.querySelectorAll("button").forEach(button => {
                    button.disabled = true;
                });
                if (!disableOnly) {
                    container.replaceChildren();
                    container.hidden = true;
                }
            }
            this.activeChoice = null;
        }

        resolveChoice(value, reason = "user") {
            if (this.disposed || !this.activeChoice
                || (this.state !== "running" && this.state !== "awaiting_payload")) return false;
            const choice = this.activeChoice;
            const option = choice.options.find(item => item.value === value);
            if (!option) return false;
            const schema = this.profile.presentation_state_schema || {};
            const mutations = option.set || {};
            for (const [key, nextValue] of Object.entries(mutations)) {
                if (!Array.isArray(schema[key]) || !schema[key].includes(nextValue)) return false;
            }
            Object.assign(this.presentationState, mutations);
            this.cancelTimer(this.choiceTimeoutId);
            this.cancelTimer(this.choiceTickId);
            this.choiceTimeoutId = null;
            this.choiceTickId = null;
            const container = this.panel && this.panel.querySelector(".operation-feedback-choice");
            if (container) {
                container.querySelectorAll("button").forEach(button => {
                    button.disabled = true;
                });
                const countdown = container.querySelector(".operation-feedback-choice-countdown");
                if (countdown) countdown.textContent = reason === "timeout" ? "Wybrano domyslnie." : "Wybor zapisany lokalnie.";
            }
            this.trace("feedback_choice_resolved", {
                choice_id: choice.choice_id,
                choice_value: option.value,
                completion_reason: reason
            });
            this.activeChoice = null;
            this.setTimer(() => {
                if (!this.disposed && !this.activeChoice && container) {
                    container.replaceChildren();
                    container.hidden = true;
                }
            }, 450);
            return true;
        }

        renderChoice(choice) {
            if (!choice || this.activeChoice || this.disposed) return;
            const container = this.panel && this.panel.querySelector(".operation-feedback-choice");
            if (!container) return;
            this.activeChoice = choice;
            this.askedChoices.add(choice.choice_id);
            container.replaceChildren();
            container.hidden = false;

            const prompt = global.document.createElement("div");
            prompt.className = "operation-feedback-choice-prompt";
            prompt.textContent = choice.prompt;
            container.appendChild(prompt);

            const buttons = global.document.createElement("div");
            buttons.className = "operation-feedback-choice-buttons";
            choice.options.forEach(option => {
                const button = global.document.createElement("button");
                button.type = "button";
                button.dataset.feedbackChoice = choice.choice_id;
                button.dataset.feedbackValue = option.value;
                button.textContent = option.label;
                button.addEventListener("click", () => this.resolveChoice(option.value, "user"));
                buttons.appendChild(button);
            });
            container.appendChild(buttons);

            const countdown = global.document.createElement("div");
            countdown.className = "operation-feedback-choice-countdown";
            container.appendChild(countdown);
            const deadline = this.now() + choice.timeout_ms;
            const updateCountdown = () => {
                if (this.disposed || this.activeChoice !== choice) return;
                const seconds = Math.max(0, Math.ceil((deadline - this.now()) / 1000));
                countdown.textContent = `Domyslny wybor za ${seconds}s`;
                if (seconds > 0) this.choiceTickId = this.setTimer(updateCountdown, 1000);
            };
            updateCountdown();
            this.choiceTimeoutId = this.setTimer(
                () => this.resolveChoice(choice.default_value, "timeout"),
                choice.timeout_ms
            );
            this.trace("feedback_choice_presented", { choice_id: choice.choice_id });
        }

        maybePresentChoice(scene) {
            if (!scene.allow_choice || this.activeChoice || scene.duration_profile === "instant") return;
            if (scene.duration_profile === "short" && this.askedChoices.size >= 1) return;
            const choiceId = randomItem(
                this.profile.choice_pools.filter(id => !this.askedChoices.has(id)),
                this.random
            );
            if (choiceId) this.renderChoice(this.config.choice_library[choiceId]);
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
                random: this.random,
                presentationState: this.presentationState,
                applicationContent: this.applicationContent
            });
            if (this.state === "awaiting_payload") this.transition("running");
            this.render("Operacja w toku...", scene.lines);
            this.trace("feedback_scene_started", {
                scene_id: scene.scene_id,
                duration_profile: scene.duration_profile,
                elapsed_ms: Math.round(elapsedMs),
                content_source: scene.content_source
            });
            this.maybePresentChoice(scene);
            this.setTimer(() => {
                if (this.disposed || this.state !== "running") return;
                this.renderNextScene();
            }, scene.delay_ms);
        }

        complete(payload = {}) {
            if (this.disposed || TERMINAL_STATES.has(this.state)) return;
            this.clearTimers();
            this.clearChoice(true);
            this.transition("completing");
            const success = payload && payload.success === true;
            const completion = this.config && this.profile
                ? this.config.completion_library[this.profile.completion_pool]
                : null;
            const structuredCompletion = this.applicationContent.structured
                && this.applicationContent.structured.completion
                && this.applicationContent.structured.completion[success ? "success" : "failure"];
            const legacyCompletion = this.applicationContent.legacy
                && this.applicationContent.legacy.completion
                && this.applicationContent.legacy.completion[success ? "success" : "failure"];
            const fallbackCompletion = completion
                ? (success ? completion.success : completion.failure)
                : null;
            const completionLines = structuredCompletion && structuredCompletion.length
                ? structuredCompletion
                : (legacyCompletion && legacyCompletion.length
                    ? legacyCompletion
                    : fallbackCompletion);
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
            this.clearChoice(true);
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
            this.clearChoice(true);
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
            this.clearChoice(true);
            if (this.state !== "disposed") this.transition("disposed");
            this.disposed = true;
            this.presentationState = {};
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
        projectApplicationContent,
        validateFeedbackConfig,
        loadFeedbackConfig,
        durationProfileFor,
        composeScene
    });
})(window);
