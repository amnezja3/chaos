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
    const PRESENTATION_MODES = new Set(["ofs_provisional", "terminal", "button_choice", "window"]);
    const SCENE_TRANSITIONS = new Set(["replace", "clear", "fade", "append_short"]);
    const PROVISIONAL_VOICES = new Set(["default", "terminal", "button_choices", "window", "progressbar_random"]);
    const PROVISIONAL_PLACEHOLDERS = new Set(["app_title", "description", "interface", "target_label", "action_label"]);
    const ACTION_PRESENTATION_MODES = Object.freeze({
        scan_ports: "button_choice",
        exploit: "terminal",
        sniff: "terminal",
        trace: "window",
        trace_gps: "window",
        trace_device: "window",
        mic_sniff: "terminal",
        atm_logs: "terminal",
        install_sniffer: "button_choice",
        camera_stream: "window",
        camera_shutdown: "button_choice",
        car_hack: "button_choice"
    });
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
    let rendererSequence = 0;
    let profilePromise = null;

    function ensureObject(value, label) {
        if (!value || typeof value !== "object" || Array.isArray(value)) {
            throw new Error(`OFS invalid ${label}`);
        }
        return value;
    }

    function createSceneEnvelope(value = {}) {
        const mode = String(value.presentation_mode || value.mode || "").trim();
        if (!PRESENTATION_MODES.has(mode)) throw new Error("OFS unsupported presentation mode");
        const transition = String(value.transition || "replace").trim();
        if (!SCENE_TRANSITIONS.has(transition)) throw new Error("OFS unsupported scene transition");
        const phase = String(value.phase || "").trim();
        const allowOutcome = phase === "completing" || phase === "failed";
        const lines = (Array.isArray(value.lines) ? value.lines : [])
            .map(line => safeContentText(String(line || ""), { allowOutcome }))
            .filter(Boolean)
            .slice(0, 6);
        const slots = Object.fromEntries(Object.entries(
            value.slots && typeof value.slots === "object" && !Array.isArray(value.slots)
                ? value.slots
                : {}
        ).filter(([key]) => /^[a-z][a-z0-9_]{0,31}$/.test(key)).slice(0, 6).map(([key, slotValue]) => [
            key,
            safeContentText(String(slotValue || ""), { allowOutcome })
        ]).filter(([, slotValue]) => Boolean(slotValue)));
        if (!lines.length && transition !== "clear") throw new Error("OFS scene envelope has no lines");
        return Object.freeze({
            schema_version: "1.0.0",
            presentation_mode: mode,
            phase,
            scene_id: String(value.scene_id || value.family || "scene").trim(),
            status: safeContentText(String(value.status || ""), { allowOutcome }) || "",
            lines: Object.freeze(lines),
            slots: Object.freeze(slots),
            transition,
            tone: String(value.tone || "pending").trim(),
            content_source: String(value.content_source || "fallback").trim()
        });
    }

    class ProvisionalSceneRenderer {
        constructor(options = {}) {
            this.host = options.host || null;
            this.appWindow = options.appWindow || null;
            this.disposed = false;
            rendererSequence += 1;
            this.owner = `ofs_provisional:${rendererSequence}`;
        }

        render(rawEnvelope) {
            if (this.disposed || !this.host || !this.host.isConnected) return false;
            const currentOwner = this.host.dataset.presentationOwner;
            if (currentOwner && currentOwner !== this.owner) {
                throw new Error("OFS provisional viewport already has an owner");
            }
            const envelope = createSceneEnvelope({ ...rawEnvelope, presentation_mode: "ofs_provisional" });
            this.host.dataset.presentationOwner = this.owner;
            this.host.dataset.sceneId = envelope.scene_id;
            this.host.dataset.sceneTransition = envelope.transition;
            this.host.dataset.sceneTone = envelope.tone;
            if (envelope.transition === "clear") {
                this.host.replaceChildren();
                return true;
            }
            const nodes = envelope.lines.map(text => {
                const line = global.document.createElement("div");
                line.className = "provisional-app-scene-line";
                line.textContent = text;
                return line;
            });
            if (envelope.transition === "append_short") {
                nodes.forEach(node => this.host.appendChild(node));
                while (this.host.children.length > 6) this.host.firstElementChild.remove();
            } else {
                this.host.replaceChildren(...nodes);
            }
            return true;
        }

        dispose() {
            if (this.disposed) return;
            this.disposed = true;
            if (this.host && this.host.dataset.presentationOwner === this.owner) {
                delete this.host.dataset.presentationOwner;
            }
        }
    }

    class ExecutionSceneRenderer {
        constructor(options = {}) {
            this.host = options.host || null;
            this.appWindow = options.appWindow || null;
            this.applicationContent = options.applicationContent || {};
            this.presentationMode = String(options.presentationMode || "window").trim();
            this.sessionId = String(options.sessionId || "").trim();
            this.panel = null;
            this.disposed = false;
            rendererSequence += 1;
            this.owner = `ofs_execution:${this.presentationMode}:${rendererSequence}`;
        }

        ensurePanel() {
            if (this.disposed || !this.host || !this.host.isConnected) {
                throw new Error("OFS renderer host is unavailable");
            }
            const currentOwner = this.host.dataset.presentationOwner;
            if (currentOwner && currentOwner !== this.owner) {
                throw new Error("OFS execution viewport already has an owner");
            }
            if (this.panel && this.panel.isConnected) return this.panel;
            this.host.dataset.presentationOwner = this.owner;
            const panel = global.document.createElement("section");
            panel.className = `operation-feedback-panel operation-feedback-${this.presentationMode}`;
            panel.dataset.ofsSessionId = this.sessionId;
            panel.dataset.presentationMode = this.presentationMode;
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

            this.extendPanel(panel);
            this.host.appendChild(panel);
            this.panel = panel;
            return panel;
        }

        extendPanel() {}

        choiceContainer() {
            return null;
        }

        render(rawEnvelope) {
            const envelope = createSceneEnvelope({
                ...rawEnvelope,
                presentation_mode: this.presentationMode
            });
            const panel = this.ensurePanel();
            panel.dataset.tone = envelope.tone;
            panel.dataset.sceneId = envelope.scene_id;
            panel.dataset.sceneTransition = envelope.transition;
            const status = panel.querySelector(".operation-feedback-status");
            const lines = panel.querySelector(".operation-feedback-lines");
            status.textContent = envelope.status;
            if (envelope.transition === "clear") {
                lines.replaceChildren();
                this.renderEnvelope(envelope, panel);
                return true;
            }
            const nodes = envelope.lines.map(text => {
                const line = global.document.createElement("div");
                line.className = "operation-feedback-line";
                line.textContent = text;
                return line;
            });
            if (envelope.transition === "append_short") {
                nodes.forEach(node => lines.appendChild(node));
                while (lines.children.length > 6) lines.firstElementChild.remove();
            } else {
                lines.replaceChildren(...nodes);
            }
            this.renderEnvelope(envelope, panel);
            return true;
        }

        renderEnvelope() {}

        dispose() {
            if (this.disposed) return;
            this.disposed = true;
            if (this.panel && this.panel.isConnected) this.panel.remove();
            if (this.host && this.host.dataset.presentationOwner === this.owner) {
                delete this.host.dataset.presentationOwner;
            }
            this.panel = null;
        }
    }

    class TerminalSceneRenderer extends ExecutionSceneRenderer {
        constructor(options = {}) {
            super({ ...options, presentationMode: "terminal" });
        }
    }

    class ButtonChoiceSceneRenderer extends ExecutionSceneRenderer {
        constructor(options = {}) {
            super({ ...options, presentationMode: "button_choice" });
        }

        extendPanel(panel) {
            const choice = global.document.createElement("div");
            choice.className = "operation-feedback-choice";
            choice.hidden = true;
            panel.appendChild(choice);
        }

        choiceContainer() {
            return this.panel && this.panel.querySelector(".operation-feedback-choice");
        }
    }

    class WindowSceneRenderer extends ExecutionSceneRenderer {
        constructor(options = {}) {
            super({ ...options, presentationMode: "window" });
        }

        extendPanel(panel) {
            const slots = global.document.createElement("div");
            slots.className = "operation-feedback-slots";
            panel.appendChild(slots);
        }

        renderEnvelope(envelope, panel) {
            const slots = panel.querySelector(".operation-feedback-slots");
            slots.replaceChildren();
            Object.entries(envelope.slots).forEach(([key, value]) => {
                const slot = global.document.createElement("div");
                slot.className = "operation-feedback-slot";
                slot.dataset.slot = key;
                const label = global.document.createElement("span");
                label.className = "operation-feedback-slot-label";
                label.textContent = key.replaceAll("_", " ");
                const content = global.document.createElement("span");
                content.className = "operation-feedback-slot-value";
                content.textContent = value;
                slot.appendChild(label);
                slot.appendChild(content);
                slots.appendChild(slot);
            });
            slots.hidden = slots.children.length === 0;
        }
    }

    function createPresentationRenderer(mode, options = {}) {
        const normalizedMode = String(mode || "").trim();
        if (normalizedMode === "ofs_provisional") return new ProvisionalSceneRenderer(options);
        if (normalizedMode === "terminal") return new TerminalSceneRenderer(options);
        if (normalizedMode === "button_choice") return new ButtonChoiceSceneRenderer(options);
        if (normalizedMode === "window") return new WindowSceneRenderer(options);
        return null;
    }

    function presentationModeForInterface(interfaceName) {
        const normalized = String(interfaceName || "").trim();
        if (normalized === "progressbar_random" || normalized === "window") return "window";
        if (normalized === "terminal") return "terminal";
        if (normalized === "button_choices" || normalized === "button_choice") return "button_choice";
        return null;
    }

    function presentationModeForAction(actionKey, interfaceName = "") {
        const action = String(actionKey || "").trim();
        return ACTION_PRESENTATION_MODES[action]
            || presentationModeForInterface(interfaceName)
            || "window";
    }

    function validateFeedbackConfig(rawConfig) {
        const config = ensureObject(rawConfig, "config");
        if (config.schema_version !== "1.0.0") throw new Error("OFS unsupported schema_version");
        [
            "defaults", "duration_profiles", "provisional_timelines", "provisional_scene_library", "scene_library",
            "security_library", "transport_library", "choice_library",
            "completion_library", "failure_library", "operations"
        ].forEach(section => ensureObject(config[section], section));

        const validatePlainText = value => {
            if (typeof value === "string" && /<[^>]+>/.test(value)) {
                throw new Error("OFS content must be plain text");
            }
            if (Array.isArray(value)) value.forEach(validatePlainText);
            else if (value && typeof value === "object") Object.values(value).forEach(validatePlainText);
        };
        validatePlainText(config);

        Object.entries(config.scene_library).forEach(([sceneId, sceneValue]) => {
            const scene = ensureObject(sceneValue, `scene ${sceneId}`);
            if (!Array.isArray(scene.sequence) || !scene.sequence.length
                || scene.sequence.some(role => !["operation", "security", "transition"].includes(role))) {
                throw new Error(`OFS scene ${sceneId} has invalid sequence`);
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

        let previousThreshold = -1;
        Object.entries(config.duration_profiles).forEach(([durationId, durationValue]) => {
            const duration = ensureObject(durationValue, `duration ${durationId}`);
            if (!Number.isFinite(duration.min_elapsed_ms) || duration.min_elapsed_ms < previousThreshold) {
                throw new Error(`OFS duration ${durationId} has invalid threshold`);
            }
            previousThreshold = duration.min_elapsed_ms;
            if (!Array.isArray(duration.scene_pool) || !duration.scene_pool.length) {
                throw new Error(`OFS duration ${durationId} has no scenes`);
            }
        });

        const allowedState = {};
        Object.values(config.operations).forEach(profile => {
            Object.entries((profile && profile.presentation_state_schema) || {}).forEach(([key, values]) => {
                if (!allowedState[key]) allowedState[key] = new Set();
                (Array.isArray(values) ? values : []).forEach(value => allowedState[key].add(value));
            });
        });
        Object.values(config.security_library).forEach(security => {
            Object.values((security && security.interactions) || {}).forEach(variants => {
                (Array.isArray(variants) ? variants : []).forEach(variant => {
                    Object.entries((variant && typeof variant === "object" && variant.when) || {}).forEach(([key, value]) => {
                        if (!allowedState[key] || !allowedState[key].has(value)) {
                            throw new Error("OFS variant references undeclared presentation state");
                        }
                    });
                });
            });
        });

        const timeline = ensureObject(config.provisional_timelines.launch_150s, "launch_150s timeline");
        const timelineStarts = Array.isArray(timeline.stages)
            ? timeline.stages.map(stage => Number(stage.start_after_ms))
            : [];
        const extendedWait = timeline.extended_wait_ms;
        if (!Array.isArray(timeline.stages) || !timeline.stages.length
            || Number(timeline.min_coverage_ms) < 150000
            || timelineStarts.some((value, index) => !Number.isFinite(value)
                || (index > 0 && value < timelineStarts[index - 1]))
            || !timeline.stages.some(stage => Number(stage.start_after_ms) >= 150000)
            || !Array.isArray(extendedWait) || extendedWait.length !== 2
            || extendedWait[0] < 12000 || extendedWait[1] > 20000
            || extendedWait[0] > extendedWait[1]) {
            throw new Error("OFS launch_150s provisional timeline is incomplete");
        }
        const timelineFamilies = new Set(timeline.stages.map(stage => String(stage.family || "")));
        const stageIds = new Set();
        timeline.stages.forEach(stage => {
            const sceneId = String(stage.scene_id || "").trim();
            const family = String(stage.family || "").trim();
            if (!sceneId || stageIds.has(sceneId) || !family) throw new Error("OFS invalid provisional stage identity");
            stageIds.add(sceneId);
            const definition = ensureObject(config.provisional_scene_library[sceneId], `provisional scene ${sceneId}`);
            if (!SCENE_TRANSITIONS.has(definition.transition) || definition.cancelable !== true) {
                throw new Error(`OFS provisional scene ${sceneId} is not safely cancelable`);
            }
            const voices = ensureObject(definition.voices, `provisional scene ${sceneId} voices`);
            if (!Object.keys(voices).length || Object.keys(voices).some(voice => !PROVISIONAL_VOICES.has(voice))) {
                throw new Error(`OFS provisional scene ${sceneId} has invalid voices`);
            }
            Object.values(voices).forEach(variants => {
                if (!Array.isArray(variants) || !variants.length) throw new Error(`OFS provisional scene ${sceneId} has no variants`);
                variants.forEach(lines => {
                    if (!Array.isArray(lines) || !lines.length || lines.some(line => typeof line !== "string")) {
                        throw new Error(`OFS provisional scene ${sceneId} has invalid content`);
                    }
                    lines.forEach(line => {
                        if (/(sukces|success|captur|connection lost|packet loss|worker restart|reconnect|retry|firewall|security|zabezpiecze)/i.test(line)) {
                            throw new Error(`OFS provisional scene ${sceneId} contains outcome or runtime fiction`);
                        }
                        Array.from(line.matchAll(/\{([a-z_]+)\}/g)).forEach(match => {
                            if (!PROVISIONAL_PLACEHOLDERS.has(match[1])) throw new Error(`OFS forbidden placeholder ${match[1]}`);
                        });
                    });
                });
            });
            if (family === "extended_wait" && Math.max(...Object.values(voices).map(variants => variants.length)) < 3) {
                throw new Error("OFS extended wait requires at least three variants");
            }
        });

        const validateProfile = (operationId, profileValue) => {
            const profile = ensureObject(profileValue, `${operationId} profile`);
            if (profile.action_key !== operationId || profile.enabled !== true) {
                throw new Error(`OFS invalid ${operationId} profile identity`);
            }
            if (Object.prototype.hasOwnProperty.call(profile, "security_keys")
                || Object.prototype.hasOwnProperty.call(profile, "interaction_types")) {
                throw new Error("OFS security profile must use an explicit matrix");
            }
            const expectedMode = ACTION_PRESENTATION_MODES[operationId];
            if (!expectedMode || profile.default_presentation_mode !== expectedMode
                || !Array.isArray(profile.presentation_modes)
                || !profile.presentation_modes.includes(expectedMode)) {
                throw new Error(`OFS ${operationId} has invalid presentation mode`);
            }
            if (!Array.isArray(profile.scene_pools) || !profile.scene_pools.length) {
                throw new Error(`OFS ${operationId} scene pool is empty`);
            }
            profile.scene_pools.forEach(sceneId => ensureObject(config.scene_library[sceneId], `scene ${sceneId}`));
            const durationPools = ensureObject(profile.duration_scene_pools, `${operationId} duration pools`);
            Object.keys(config.duration_profiles).forEach(durationId => {
                const pool = durationPools[durationId];
                if (!Array.isArray(pool) || !pool.length
                    || pool.some(sceneId => !profile.scene_pools.includes(sceneId))) {
                    throw new Error(`OFS ${operationId} has invalid ${durationId} scene pool`);
                }
            });
            const provisional = ensureObject(profile.provisional_profile, `${operationId} provisional profile`);
            ["security", "completion_pool", "failure_pool", "choice_pools"].forEach(forbidden => {
                if (Object.prototype.hasOwnProperty.call(provisional, forbidden)) {
                    throw new Error(`OFS provisional profile contains forbidden ${forbidden}`);
                }
            });
            if (provisional.timeline_profile !== "launch_150s"
                || !Array.isArray(provisional.scene_pool) || !provisional.scene_pool.length
                || provisional.scene_pool.some(family => !timelineFamilies.has(family))
                || Array.from(timelineFamilies).some(family => !provisional.scene_pool.includes(family))
                || !["terminal", "button_choices", "window", "progressbar_random"].includes(provisional.interface_voice)) {
                throw new Error(`OFS ${operationId} has invalid provisional profile`);
            }
            const securityMatrix = ensureObject(profile.security, `${operationId} security matrix`);
            if (!Object.keys(securityMatrix).length) throw new Error(`OFS ${operationId} security matrix is empty`);
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
            const stateSchema = ensureObject(profile.presentation_state_schema, `${operationId} presentation state schema`);
            const choicePools = Array.isArray(profile.choice_pools) ? profile.choice_pools : [];
            if (expectedMode === "button_choice" && operationId === "scan_ports" && choicePools.length < 3) {
                throw new Error("OFS scan_ports requires three presentation choices");
            }
            choicePools.forEach(choiceId => {
                const choice = ensureObject(config.choice_library[choiceId], `choice ${choiceId}`);
                if (!choiceId.startsWith("feedback.") || choice.choice_id !== choiceId
                    || choice.effect_scope !== "presentation" || !Array.isArray(choice.options)
                    || choice.options.length < 2 || !Number.isFinite(choice.timeout_ms)
                    || choice.timeout_ms <= 0 || choice.timeout_ms > 30000
                    || !choice.options.some(option => option.value === choice.default_value)) {
                    throw new Error(`OFS invalid presentation choice ${choiceId}`);
                }
                choice.options.forEach(option => {
                    Object.entries(ensureObject(option.set, `choice ${choiceId} mutation`)).forEach(([key, value]) => {
                        if (!Array.isArray(stateSchema[key]) || !stateSchema[key].includes(value)) {
                            throw new Error(`OFS choice ${choiceId} mutates undeclared state`);
                        }
                    });
                });
            });
            ensureObject(config.completion_library[profile.completion_pool], `${operationId} completion pool`);
            if (!Array.isArray(config.failure_library[profile.failure_pool])) {
                throw new Error(`OFS ${operationId} failure pool is invalid`);
            }
            return profile;
        };

        const validatedOperations = {};
        Object.keys(ACTION_PRESENTATION_MODES).forEach(operationId => {
            try {
                validatedOperations[operationId] = validateProfile(operationId, config.operations[operationId]);
            } catch (error) {
                console.warn(`[OFS] Profil ${operationId} wylaczony`, error);
                validatedOperations[operationId] = Object.freeze({
                    action_key: operationId,
                    enabled: false,
                    validation_error: String(error && error.message || "invalid_profile")
                });
            }
        });
        config.operations = validatedOperations;
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

    function composeProvisionalScene({ config, profile, stage, context = {}, history = {}, random = Math.random } = {}) {
        const sceneId = String(stage && stage.scene_id || "").trim();
        const family = String(stage && stage.family || "").trim();
        const definition = ensureObject(config && config.provisional_scene_library && config.provisional_scene_library[sceneId], `provisional scene ${sceneId}`);
        if (!profile || !profile.provisional_profile || !profile.provisional_profile.scene_pool.includes(family)) {
            throw new Error(`OFS provisional family ${family} is unavailable`);
        }
        const actualVoice = String(context.interface || "").trim().toLowerCase();
        const configuredVoice = String(profile.provisional_profile.interface_voice || "default").trim();
        const voice = PROVISIONAL_VOICES.has(actualVoice) ? actualVoice : configuredVoice;
        const variants = definition.voices[voice] || definition.voices.default;
        const previous = String(history.last_variant || "");
        const candidates = variants.map((lines, index) => ({ lines, key: `${sceneId}:${voice}:${index}` }));
        const available = candidates.filter(candidate => candidate.key !== previous);
        const selected = (available.length ? available : candidates)[Math.floor(random() * (available.length || candidates.length))];
        const values = {
            app_title: safeContentText(context.app_title, { allowOutcome: true }) || "Aplikacja",
            description: safeContentText(context.description) || "Opis autora nie zostal udostepniony.",
            interface: safeContentText(context.interface, { allowOutcome: true }) || configuredVoice,
            target_label: safeContentText(context.target_label, { allowOutcome: true }) || "cel operacji",
            action_label: safeContentText(context.action_label, { allowOutcome: true }) || "operacja"
        };
        const lines = selected.lines.map(line => line.replace(/\{([a-z_]+)\}/g, (match, key) => values[key] || ""))
            .map(line => safeContentText(line, { allowOutcome: true })).filter(Boolean);
        return {
            scene_id: sceneId,
            family,
            phase: String(definition.phase || "booting"),
            lines,
            status: lines[0] || "Oczekiwanie na runtime.",
            transition: definition.transition,
            content_source: family === "author_content" || family === "author_manifest" ? "app_projection" : "global_fallback",
            variant_key: selected.key
        };
    }

    function randomItem(items, random = Math.random, excluded = null) {
        const source = Array.isArray(items) ? items.filter(item => item !== excluded) : [];
        const pool = source.length ? source : (Array.isArray(items) ? items : []);
        if (!pool.length) return null;
        return pool[Math.min(pool.length - 1, Math.floor(random() * pool.length))];
    }

    function durationProfileFor(config, elapsedMs, profile = null) {
        const entries = Object.entries(config.duration_profiles)
            .sort((left, right) => Number(left[1].min_elapsed_ms) - Number(right[1].min_elapsed_ms));
        let selected = entries[0];
        entries.forEach(entry => {
            if (elapsedMs >= Number(entry[1].min_elapsed_ms || 0)) selected = entry;
        });
        if (!selected) return { id: "instant", scene_pool: [] };
        const override = profile && profile.duration_scene_pools
            && profile.duration_scene_pools[selected[0]];
        return {
            id: selected[0],
            ...selected[1],
            scene_pool: Array.isArray(override) && override.length ? override : selected[1].scene_pool
        };
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
        const duration = durationProfileFor(config, elapsedMs, profile);
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
        if (!node) return { enabled: false, scan_ports: false, enabled_actions: [] };
        try {
            const parsed = JSON.parse(node.textContent || "{}");
            return {
                enabled: parsed.enabled === true,
                scan_ports: parsed.scan_ports === true,
                enabled_actions: Array.isArray(parsed.enabled_actions)
                    ? parsed.enabled_actions.map(value => String(value || "").trim()).filter(Boolean)
                    : []
            };
        } catch (error) {
            console.warn("[OFS] Nieprawidlowy config; pozostaje legacy pending UI", error);
            return { enabled: false, scan_ports: false, enabled_actions: [] };
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
        const enabledActions = new Set(Array.isArray(flags.enabled_actions) ? flags.enabled_actions : []);
        if (flags.scan_ports === true) enabledActions.add("scan_ports");
        return flags.enabled === true
            && Object.prototype.hasOwnProperty.call(ACTION_PRESENTATION_MODES, action)
            && enabledActions.has(action);
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
            this.renderer = options.renderer || null;
            this.securityState = sanitizeSecurityState(options.securityState);
            this.applicationContent = options.applicationContent || projectApplicationContent({});
            this.clock = options.clock || global;
            this.now = typeof options.now === "function" ? options.now : () => global.performance.now();
            this.random = typeof options.random === "function" ? options.random : Math.random;
            this.configLoader = options.configLoader || loadFeedbackConfig;
            this.onTrace = typeof options.onTrace === "function" ? options.onTrace : function noop() {};
            this.onProfileUnavailable = typeof options.onProfileUnavailable === "function"
                ? options.onProfileUnavailable
                : function noop() {};
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
            if (!this.renderer) {
                this.renderer = createPresentationRenderer(this.presentationMode, {
                    host: this.rendererHost,
                    appWindow: this.appWindow,
                    applicationContent: this.applicationContent,
                    sessionId: this.sessionId
                });
            }
            if (!this.renderer || this.presentationMode === "ofs_provisional") {
                throw new Error("OFS execution renderer is unavailable");
            }
            this.panel = this.renderer.ensurePanel();
            return this.panel;
        }

        render(statusText, lineItems, tone = "pending", transition = "replace", sceneId = "session_state") {
            this.ensurePanel();
            this.renderer.render({
                phase: this.state,
                scene_id: sceneId,
                status: statusText,
                lines: lineItems,
                transition,
                tone,
                content_source: "execution_session"
            });
            this.panel = this.renderer.panel;
        }

        choiceContainer() {
            return this.renderer && typeof this.renderer.choiceContainer === "function"
                ? this.renderer.choiceContainer()
                : null;
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
            const container = this.choiceContainer();
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
            const container = this.choiceContainer();
            if (container) {
                container.querySelectorAll("button").forEach(button => {
                    button.disabled = true;
                });
                const countdown = container.querySelector(".operation-feedback-choice-countdown");
                if (countdown) countdown.textContent = reason === "timeout" ? "Wybrano domyslnie." : "Wybor zapisany lokalnie.";
            }
            this.trace(reason === "timeout" ? "feedback_choice_timed_out" : "feedback_choice_selected", {
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
            const container = this.choiceContainer();
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
            this.trace("feedback_choice_shown", { choice_id: choice.choice_id });
        }

        maybePresentChoice(scene) {
            if (this.presentationMode !== "button_choice") return;
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
                if (!this.profile || this.profile.enabled !== true
                    || !Array.isArray(this.profile.presentation_modes)
                    || !this.profile.presentation_modes.includes(this.presentationMode)) {
                    throw new Error("OFS profile does not support renderer");
                }
                this.trace("feedback_profile_loaded", { content_version: this.config.content_version });
                this.renderNextScene();
            }).catch(error => {
                if (this.disposed || this.state !== "running") return;
                this.trace("feedback_profile_failed", { completion_reason: error.message || "invalid_profile" });
                try {
                    this.onProfileUnavailable(error);
                } finally {
                    this.cancel("profile_unavailable");
                }
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
            this.render("Operacja w toku...", scene.lines, "pending", "replace", scene.scene_id);
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
            const normalizedReason = String(reason || "request_failed").toLowerCase();
            const failureCategory = /abort|cancel/.test(normalizedReason) ? "abort"
                : /json|payload|parse|syntax/.test(normalizedReason) ? "invalid_response"
                    : /http|status/.test(normalizedReason) ? "http_error"
                        : /network|fetch|connection/.test(normalizedReason) ? "network_error"
                            : /gameplay|rejected/.test(normalizedReason) ? "gameplay_failure"
                                : "default";
            const failurePool = this.config
                ? (this.config.failure_library[failureCategory]
                    || (this.profile && this.config.failure_library[this.profile.failure_pool]))
                : null;
            this.render("Blad odpowiedzi runtime.", [
                randomItem(failurePool, this.random) || "Operacja nie zostala potwierdzona."
            ], "failure");
            this.trace("feedback_failed", {
                completion_reason: String(reason || "request_failed"),
                failure_category: failureCategory
            });
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
            if (this.renderer && typeof this.renderer.dispose === "function") this.renderer.dispose();
            this.renderer = null;
            this.panel = null;
            if (this.appWindow && this.appWindow._operationFeedbackSession === this) {
                this.appWindow._operationFeedbackSession = null;
            }
            this.trace("feedback_disposed", { completion_reason: String(reason || "disposed") });
        }
    }

    function createSession(options = {}) {
        if (!isEnabled(options.actionKey, options.flags || readFlags())) return null;
        const mode = String(options.presentationMode || "button_choice").trim();
        if (!PRESENTATION_MODES.has(mode) || mode === "ofs_provisional") return null;
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
        composeScene,
        composeProvisionalScene,
        createSceneEnvelope,
        createPresentationRenderer,
        presentationModeForInterface,
        presentationModeForAction,
        ProvisionalSceneRenderer,
        ExecutionSceneRenderer,
        TerminalSceneRenderer,
        ButtonChoiceSceneRenderer,
        WindowSceneRenderer
    });
})(window);
