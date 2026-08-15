(function operationFeedbackBootstrap(global) {
    "use strict";

    const CONFIG_ELEMENT_ID = "operation-feedback-config";
    const PROFILE_URL = "/static/data/operation_feedback.v1.json?v=button-choice-actions-1";
    const CANONICAL_SECURITY_KEYS = new Set([
        "stealth_mode", "scan_detection", "exploit_protection", "vpn_enabled",
        "browser_protection", "os_hardening", "log_guardian", "process_monitor",
        "firewall", "log_integrity", "network_anomaly_detection", "spoofing_protection",
        "activity_monitor", "player_tracking", "system_visibility", "firewall_core",
        "kernel_guard", "system_integrity_check", "heap_protection", "memory_lock",
        "background_injection", "memory_guard", "vpn_blocker"
    ]);
    const TERMINAL_STATES = new Set(["disposed"]);
    const PRESENTATION_MODES = new Set(["ofs_provisional", "terminal", "button_choice", "window", "progressbar_random"]);
    const SCENE_TRANSITIONS = new Set(["replace", "clear", "fade", "append_short"]);
    const PROVISIONAL_VOICES = new Set(["default", "terminal", "button_choices", "window", "progressbar_random"]);
    const PROVISIONAL_INTERFACE_VOICES = Object.freeze(["terminal", "button_choices", "window", "progressbar_random"]);
    const PROVISIONAL_WAIT_BANDS = Object.freeze(["instant", "short", "medium", "long", "extended", "overdue"]);
    const PROVISIONAL_PLACEHOLDERS = new Set(["app_title", "description", "interface", "target_label", "action_label"]);
    const OFS_SFX_SEMANTICS = new Set([
        "intro", "choice_available", "choice_confirmed", "progress_checkpoint",
        "success", "failure", "runtime_warning"
    ]);
    const OFS_SFX_EVENT_KEYS = new Set(Array.from(OFS_SFX_SEMANTICS).map(key => `ofs.${key}`));
    const MAX_PROGRESS_SFX_PER_SESSION = 3;
    const PRESENTATION_PHASES = new Set([
        "provisional", "hydrating", "author_intro", "executing", "completing",
        "completed", "failed", "cancelled", "disposed"
    ]);
    const EXECUTION_TIMING_SCALE = 3;
    const MIN_SCENE_READ_MS = 6000;
    const MIN_AUTHOR_READ_MS = 4000;
    const MIN_COMPLETION_READ_MS = 6500;
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
        scan_hotspots: "button_choice",
        audio_hack: "button_choice",
        camera_stream: "window",
        camera_shutdown: "button_choice",
        car_hack: "button_choice"
    });
    const PROFILE_ACTION_ALIASES = Object.freeze({
        scan_hotspots: "scan_ports",
        audio_hack: "exploit"
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

    function readableSceneDelay(lines, configuredDelay = 0, minimum = MIN_SCENE_READ_MS) {
        const content = (Array.isArray(lines) ? lines : []).join(" ").trim();
        const wordCount = content ? content.split(/\s+/).length : 0;
        const readingDelay = Math.max(minimum, 3000 + wordCount * 400);
        return Math.max(readingDelay, Math.max(0, Number(configuredDelay) || 0) * EXECUTION_TIMING_SCALE);
    }

    const SCENE_ROLE_ICONS = Object.freeze({
        identity: "◉", module: "▣", target: "⌖", author: "✎", command: ">_",
        decision: "◇", checkpoint: "◆", warning: "!", success: "✓", failure: "×"
    });

    function semanticRoleForEnvelope(envelope) {
        const tone = String(envelope.tone || "").toLowerCase();
        const scene = String(envelope.scene_id || "").toLowerCase();
        if (tone === "failure") return "failure";
        if (tone === "success") return "success";
        if (tone === "warning") return "warning";
        if (/choice|decision/.test(scene)) return "decision";
        if (/author/.test(scene)) return "author";
        if (/target|context/.test(scene)) return "target";
        if (/validation|checkpoint|sync|hydration|wait/.test(scene)) return "checkpoint";
        if (/module|boot|init|prepare/.test(scene)) return "module";
        if (/terminal|command|probe|execute/.test(scene)) return "command";
        return "identity";
    }

    function createSemanticSceneLine(envelope, text, className) {
        const role = semanticRoleForEnvelope(envelope);
        const line = global.document.createElement("div");
        line.className = `${className} ofs-scene-role-${role}`;
        line.dataset.sceneRole = role;
        const icon = global.document.createElement("span");
        icon.className = "ofs-scene-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = SCENE_ROLE_ICONS[role];
        const content = global.document.createElement("span");
        content.className = "ofs-scene-text";
        content.textContent = text;
        line.appendChild(icon);
        line.appendChild(content);
        return line;
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
            content_source: String(value.content_source || "fallback").trim(),
            wait_band: String(value.wait_band || "").trim()
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
            this.host.dataset.sceneRole = semanticRoleForEnvelope(envelope);
            if (envelope.wait_band) this.host.dataset.ofsWaitBand = envelope.wait_band;
            if (envelope.transition === "clear") {
                this.host.replaceChildren();
                return true;
            }
            const nodes = envelope.lines.map(text => createSemanticSceneLine(envelope, text, "provisional-app-scene-line"));
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
                delete this.host.dataset.sceneId;
                delete this.host.dataset.sceneTransition;
                delete this.host.dataset.sceneTone;
                delete this.host.dataset.sceneRole;
                delete this.host.dataset.ofsWaitBand;
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
            panel.dataset.template = this.presentationMode;
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
            panel.dataset.sceneRole = semanticRoleForEnvelope(envelope);
            const status = panel.querySelector(".operation-feedback-status");
            const lines = panel.querySelector(".operation-feedback-lines");
            status.textContent = envelope.status;
            if (envelope.transition === "clear") {
                lines.replaceChildren();
                this.renderEnvelope(envelope, panel);
                return true;
            }
            const nodes = envelope.lines.map(text => createSemanticSceneLine(envelope, text, "operation-feedback-line"));
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

        dispose(options = {}) {
            if (this.disposed) return;
            this.disposed = true;
            if (options.preservePanel !== true && this.panel && this.panel.isConnected) this.panel.remove();
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

        renderEnvelope(envelope, panel) {
            const status = panel.querySelector(".operation-feedback-status");
            status.dataset.sysinfo = envelope.tone === "failure" ? "FAILED"
                : (envelope.tone === "success" ? "COMPLETE" : "RUNNING");
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

    class ProgressbarRandomSceneRenderer extends ExecutionSceneRenderer {
        constructor(options = {}) {
            super({ ...options, presentationMode: "progressbar_random" });
        }

        renderEnvelope(envelope, panel) {
            panel.dataset.executorState = envelope.tone === "failure" ? "failed"
                : (envelope.tone === "success" ? "complete" : "running");
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
                label.textContent = String(key).replace(/_/g, " ");
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
        if (normalizedMode === "progressbar_random") return new ProgressbarRandomSceneRenderer(options);
        if (normalizedMode === "window") return new WindowSceneRenderer(options);
        return null;
    }

    function presentationModeForInterface(interfaceName) {
        const normalized = String(interfaceName || "").trim();
        if (normalized === "progressbar_random") return "progressbar_random";
        if (normalized === "window") return "window";
        if (normalized === "terminal") return "terminal";
        if (normalized === "button_choices" || normalized === "button_choice") return "button_choice";
        return null;
    }

    function presentationModeForAction(actionKey, interfaceName = "") {
        const action = String(actionKey || "").trim();
        return presentationModeForInterface(interfaceName)
            || ACTION_PRESENTATION_MODES[action]
            || "window";
    }

    function validateFeedbackConfig(rawConfig) {
        const config = ensureObject(rawConfig, "config");
        if (config.schema_version !== "1.0.0") throw new Error("OFS unsupported schema_version");
        [
            "defaults", "duration_profiles", "provisional_timelines", "provisional_wait_bands",
            "provisional_voice_packs", "provisional_scene_library", "scene_library",
            "security_library", "transport_library", "choice_library", "button_choice_defaults",
            "button_choice_action_profiles",
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
            || Number(timeline.min_coverage_ms) < 180000
            || timelineStarts.some((value, index) => !Number.isFinite(value)
                || (index > 0 && value < timelineStarts[index - 1]))
            || !timeline.stages.some(stage => Number(stage.start_after_ms) >= 180000)
            || !Array.isArray(extendedWait) || extendedWait.length !== 2
            || extendedWait[0] < 18000 || extendedWait[1] > 30000
            || extendedWait[0] > extendedWait[1]) {
            throw new Error("OFS launch_150s provisional timeline is incomplete");
        }
        const timelineFamilies = new Set(timeline.stages.map(stage => String(stage.family || "")));
        const waitBands = Object.entries(config.provisional_wait_bands);
        if (waitBands.length !== PROVISIONAL_WAIT_BANDS.length
            || waitBands.some(([id, band], index) => id !== PROVISIONAL_WAIT_BANDS[index]
                || !Number.isFinite(Number(band.min_elapsed_ms))
                || (index > 0 && Number(band.min_elapsed_ms) <= Number(waitBands[index - 1][1].min_elapsed_ms)))) {
            throw new Error("OFS provisional wait bands are invalid");
        }
        const buttonDefaults = ensureObject(config.button_choice_defaults, "button choice defaults");
        const buttonDefaultPools = Array.isArray(buttonDefaults.choice_pools) ? buttonDefaults.choice_pools : [];
        const buttonDefaultSchema = ensureObject(
            buttonDefaults.presentation_state_schema,
            "button choice default state schema"
        );
        if (!buttonDefaultPools.length) throw new Error("OFS button choice defaults are empty");
        buttonDefaultPools.forEach(choiceId => {
            const choice = ensureObject(config.choice_library[choiceId], `choice ${choiceId}`);
            if (!choiceId.startsWith("feedback.") || choice.choice_id !== choiceId
                || choice.effect_scope !== "presentation" || !Array.isArray(choice.options)
                || choice.options.length < 2 || !Number.isFinite(choice.timeout_ms)
                || choice.timeout_ms <= 0 || choice.timeout_ms > 30000
                || !choice.options.some(option => option.value === choice.default_value)) {
                throw new Error(`OFS invalid default presentation choice ${choiceId}`);
            }
            choice.options.forEach(option => {
                Object.entries(ensureObject(option.set, `choice ${choiceId} mutation`)).forEach(([key, value]) => {
                    if (!Array.isArray(buttonDefaultSchema[key]) || !buttonDefaultSchema[key].includes(value)) {
                        throw new Error(`OFS default choice ${choiceId} mutates undeclared state`);
                    }
                });
            });
        });
        const buttonActionProfiles = ensureObject(
            config.button_choice_action_profiles,
            "button choice action profiles"
        );
        const validateButtonActionProfile = actionKey => {
            const actionProfile = ensureObject(
                buttonActionProfiles[actionKey],
                `button choice action profile ${actionKey}`
            );
            const choicePools = Array.isArray(actionProfile.choice_pools)
                ? actionProfile.choice_pools : [];
            const stateSchema = ensureObject(
                actionProfile.presentation_state_schema,
                `button choice action schema ${actionKey}`
            );
            if (!choicePools.length) throw new Error(`OFS ${actionKey} button choice pool is empty`);
            choicePools.forEach(choiceId => {
                const choice = ensureObject(config.choice_library[choiceId], `choice ${choiceId}`);
                if (!choiceId.startsWith(`feedback.${actionKey}.`)
                    || choice.choice_id !== choiceId || choice.effect_scope !== "presentation"
                    || !Array.isArray(choice.options) || choice.options.length < 2
                    || !Number.isFinite(choice.timeout_ms) || choice.timeout_ms <= 0
                    || choice.timeout_ms > 30000
                    || !choice.options.some(option => option.value === choice.default_value)) {
                    throw new Error(`OFS invalid ${actionKey} button choice ${choiceId}`);
                }
                choice.options.forEach(option => {
                    Object.entries(ensureObject(option.set, `choice ${choiceId} mutation`))
                        .forEach(([key, value]) => {
                            if (!Array.isArray(stateSchema[key]) || !stateSchema[key].includes(value)) {
                                throw new Error(`OFS ${actionKey} choice mutates undeclared state`);
                            }
                        });
                });
            });
            return actionProfile;
        };
        const validateProvisionalVariants = (variants, label, minimum = 1) => {
            if (!Array.isArray(variants) || variants.length < minimum) throw new Error(`OFS ${label} has too few variants`);
            variants.forEach(lines => {
                if (!Array.isArray(lines) || !lines.length || lines.some(line => typeof line !== "string")) {
                    throw new Error(`OFS ${label} has invalid content`);
                }
                lines.forEach(line => {
                    if (/(sukces|success|captur|connection lost|packet loss|worker restart|reconnect|retry|firewall|security|zabezpiecze)/i.test(line)) {
                        throw new Error(`OFS ${label} contains outcome or runtime fiction`);
                    }
                    Array.from(line.matchAll(/\{([a-z_]+)\}/g)).forEach(match => {
                        if (!PROVISIONAL_PLACEHOLDERS.has(match[1])) throw new Error(`OFS forbidden placeholder ${match[1]}`);
                    });
                });
            });
        };
        PROVISIONAL_INTERFACE_VOICES.forEach(voice => {
            const pack = ensureObject(config.provisional_voice_packs[voice], `provisional voice pack ${voice}`);
            timelineFamilies.forEach(family => validateProvisionalVariants(pack[family], `${voice}.${family}`, 3));
        });
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
            Object.values(voices).forEach(variants => validateProvisionalVariants(variants, `provisional scene ${sceneId}`));
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
                const profileOperationId = PROFILE_ACTION_ALIASES[operationId] || operationId;
                const validatedProfile = validateProfile(
                    profileOperationId,
                    config.operations[profileOperationId]
                );
                validateButtonActionProfile(operationId);
                validatedOperations[operationId] = profileOperationId === operationId
                    ? validatedProfile
                    : {
                        ...validatedProfile,
                        action_key: operationId,
                        default_presentation_mode: ACTION_PRESENTATION_MODES[operationId],
                        presentation_modes: [ACTION_PRESENTATION_MODES[operationId]]
                    };
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

    function profileForPresentation(config, profile, presentationMode, actionKey = "") {
        if (!profile || presentationMode !== "button_choice") return profile;
        const actionProfiles = ensureObject(
            config.button_choice_action_profiles,
            "button choice action profiles"
        );
        const actionProfile = ensureObject(
            actionProfiles[String(actionKey || profile.action_key || "").trim()],
            `button choice action profile ${actionKey || profile.action_key || "unknown"}`
        );
        const choicePools = Array.isArray(actionProfile.choice_pools)
            ? actionProfile.choice_pools.slice() : [];
        const stateSchema = ensureObject(
            actionProfile.presentation_state_schema,
            "button choice action state schema"
        );
        if (!choicePools.length) throw new Error("OFS action button choice profile is empty");
        choicePools.forEach(choiceId => ensureObject(config.choice_library[choiceId], `choice ${choiceId}`));
        return {
            ...profile,
            choice_pools: choicePools,
            presentation_state_schema: {...stateSchema}
        };
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

    function provisionalWaitBandFor(config, elapsedMs = 0) {
        const entries = Object.entries(ensureObject(config && config.provisional_wait_bands, "provisional wait bands"));
        let selected = entries[0];
        entries.forEach(entry => {
            if (Math.max(0, Number(elapsedMs) || 0) >= Number(entry[1].min_elapsed_ms || 0)) selected = entry;
        });
        return Object.freeze({ id: selected[0], min_elapsed_ms: Number(selected[1].min_elapsed_ms || 0) });
    }

    function composeProvisionalScene({ config, profile, stage, context = {}, history = {}, elapsedMs = 0, random = Math.random } = {}) {
        const sceneId = String(stage && stage.scene_id || "").trim();
        const family = String(stage && stage.family || "").trim();
        const definition = ensureObject(config && config.provisional_scene_library && config.provisional_scene_library[sceneId], `provisional scene ${sceneId}`);
        if (!profile || !profile.provisional_profile || !profile.provisional_profile.scene_pool.includes(family)) {
            throw new Error(`OFS provisional family ${family} is unavailable`);
        }
        const actualVoice = String(context.interface || "").trim().toLowerCase();
        const configuredVoice = String(profile.provisional_profile.interface_voice || "default").trim();
        const voice = PROVISIONAL_INTERFACE_VOICES.includes(actualVoice) ? actualVoice
            : (PROVISIONAL_INTERFACE_VOICES.includes(configuredVoice) ? configuredVoice : "default");
        const voicePacks = config.provisional_voice_packs || {};
        const voicePack = voicePacks[voice] || {};
        const packedVariants = voicePack[family];
        const variants = packedVariants || definition.voices[voice] || definition.voices.default;
        const sourcePrefix = packedVariants ? "voice_pack" : sceneId;
        const recent = new Set((Array.isArray(history.recent_variants) ? history.recent_variants : [])
            .concat(history.last_variant || "").filter(Boolean).map(String));
        const candidates = variants.map((lines, index) => ({ lines, key: `${sourcePrefix}:${family}:${voice}:${index}` }));
        const available = candidates.filter(candidate => !recent.has(candidate.key));
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
            content_source: family === "author_content" || family === "author_manifest" ? "app_projection"
                : (packedVariants ? "provisional_voice_pack" : "global_fallback"),
            variant_key: selected.key,
            wait_band: provisionalWaitBandFor(config, elapsedMs).id
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
        if (!node) return { enabled: false, enabled_actions: [] };
        try {
            const parsed = JSON.parse(node.textContent || "{}");
            return {
                enabled: parsed.enabled === true,
                enabled_actions: Array.isArray(parsed.enabled_actions)
                    ? parsed.enabled_actions.map(value => String(value || "").trim()).filter(Boolean)
                    : []
            };
        } catch (error) {
            console.warn("[OFS] Nieprawidlowy config; pozostaje legacy pending UI", error);
            return { enabled: false, enabled_actions: [] };
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

    const BRAND_TITLE_MOTIONS = Object.freeze({
        terminal: Object.freeze(["type-lock", "blink-sync", "glitch-anchor"]),
        button_choices: Object.freeze(["icon-lock", "blink-sync", "glitch-anchor"]),
        button_choice: Object.freeze(["icon-lock", "blink-sync", "glitch-anchor"]),
        progressbar_random: Object.freeze(["icon-lock", "title-slide", "blink-sync"]),
        window: Object.freeze(["title-slide", "split-reveal", "icon-lock"])
    });

    function stableBrandHash(value) {
        const text = String(value || "");
        let hash = 2166136261;
        for (let index = 0; index < text.length; index += 1) {
            hash ^= text.charCodeAt(index);
            hash = Math.imul(hash, 16777619);
        }
        return hash >>> 0;
    }

    function normalizeBrandName(value) {
        return String(value || "Aplikacja").trim().replace(/\s+/g, " ").slice(0, 96) || "Aplikacja";
    }

    function buildApplicationBrandModel(appData = {}) {
        const name = normalizeBrandName(appData.title || appData.name || appData.id);
        const words = name.split(" ").filter(Boolean);
        const characterCount = Array.from(name).length;
        const spaceCount = Math.max(0, words.length - 1);
        const longestWord = words.reduce((maximum, word) => Math.max(maximum, Array.from(word).length), 0);
        const interfaceName = String(appData.interface || "window").trim().toLowerCase() || "window";
        const hash = stableBrandHash(`${name}|${interfaceName}`);
        let titleClass = "multi-word";
        if (words.length === 1 && characterCount <= 12) titleClass = "compact-mark";
        else if (words.length === 1 && characterCount <= 18) titleClass = "single-wide";
        else if (words.length === 2 && characterCount <= 18) titleClass = "word-pair";
        else if (characterCount > 32 || longestWord > 18) titleClass = "dense-title";

        const estimatedHorizontalUnits = characterCount + (spaceCount * 2);
        const horizontalSafe = characterCount <= 12 && spaceCount <= 1
            ? true
            : characterCount <= 18 && spaceCount <= 1 && estimatedHorizontalUnits <= 20;
        const logoMode = horizontalSafe ? "horizontal" : "icon_only";
        const motionPool = BRAND_TITLE_MOTIONS[interfaceName] || BRAND_TITLE_MOTIONS.window;
        const titleMotion = motionPool[hash % motionPool.length];
        const weight = [700, 800, 900][(hash >>> 3) % 3];
        const icon = typeof appData.icon === "string" && appData.icon.trim()
            ? appData.icon.trim().slice(0, 512)
            : "▣";
        const authorUsername = normalizeBrandName(appData.creator_username || appData.author_username || "CHAOS SYSTEM");
        const authorNick = normalizeBrandName(appData.creator_nick || appData.author_nick || authorUsername);

        const durationMs = Math.min(12000, 5000 + (characterCount * 180) + (spaceCount * 400));
        const mapDurationMs = Math.min(60000, 12000 + (hash % 48001));
        return deepFreeze({
            schema_version: "1.0.0",
            identity_seed: hash.toString(16).padStart(8, "0"),
            name,
            icon,
            interface: interfaceName,
            author: {
                username: authorUsername,
                nick: authorNick,
                signature: `© CHAOS · Created by ${authorNick}`
            },
            name_metrics: {
                character_count: characterCount,
                word_count: words.length,
                space_count: spaceCount,
                longest_word: longestWord,
                name_class: titleClass
            },
            title_sequence: {
                layout: logoMode === "horizontal" ? "horizontal-lockup" : "icon-lockup",
                motion: titleMotion,
                duration_ms: durationMs,
                map_duration_ms: mapDurationMs,
                duration_band: durationMs < 7000 ? "short" : (durationMs < 9500 ? "medium" : "long"),
                readable_ms: 5000
            },
            author_logo_header: {
                mode: logoMode === "horizontal" ? "icon_text_horizontal" : "icon_only",
                font_weight: weight,
                font_scale: titleClass === "compact-mark" ? "compact" : "standard",
                icon_text_ratio: logoMode === "horizontal" ? "1:0.72" : "1:0",
                icon_position: "leading",
                anchor: "start"
            },
            author_footer: {
                mode: logoMode === "horizontal" ? "signature_compact" : "icon_only",
                font_weight: weight,
                font_scale: "micro",
                icon_text_ratio: logoMode === "horizontal" ? "1:0.58" : "1:0",
                icon_position: "leading",
                anchor: "start"
            }
        });
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
        const audioEvents = {};
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
            Object.entries(rawStructured.audio_events || {}).forEach(([semantic, eventKey]) => {
                const normalizedSemantic = String(semantic || "").trim();
                const normalizedEventKey = String(eventKey || "").trim();
                if (OFS_SFX_SEMANTICS.has(normalizedSemantic)
                    && OFS_SFX_EVENT_KEYS.has(normalizedEventKey)
                    && normalizedEventKey === `ofs.${normalizedSemantic}`) {
                    audioEvents[normalizedSemantic] = normalizedEventKey;
                }
            });
        }
        return deepFreeze({
            title: safeContentText(
                (rawStructured && rawStructured.labels && rawStructured.labels.session_title)
                || level.title || appData.name || appData.id,
                { allowOutcome: true }
            ) || "OPERATION FEEDBACK",
            icon: typeof appData.icon === "string" ? appData.icon.trim().slice(0, 512) : "",
            creator_username: safeContentText(appData.creator_username, { allowOutcome: true }) || "",
            creator_nick: safeContentText(appData.creator_nick, { allowOutcome: true }) || "",
            structured,
            audio_events: audioEvents,
            legacy,
            interface: String(appData.interface || "")
        });
    }

    function isEnabled(actionKey, flags = readFlags()) {
        const action = String(actionKey || "").trim();
        const profileAction = PROFILE_ACTION_ALIASES[action] || action;
        const enabledActions = new Set(Array.isArray(flags.enabled_actions) ? flags.enabled_actions : []);
        return flags.enabled === true
            && Object.prototype.hasOwnProperty.call(ACTION_PRESENTATION_MODES, action)
            && (enabledActions.has(action) || enabledActions.has(profileAction));
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
            this.authorIntroPresented = options.authorIntroPresented === true;
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
            this.presentationPhase = "executing";
            this.askedChoices = new Set();
            this.activeChoice = null;
            this.choiceTimeoutId = null;
            this.choiceTickId = null;
            this.sfxSequence = 0;
            this.sceneSequence = 0;
            this.progressSfxCount = 0;
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

        reduceNonessentialSfx() {
            if (typeof global.matchMedia !== "function") return false;
            try {
                return global.matchMedia("(max-width: 620px), (prefers-reduced-motion: reduce)").matches;
            } catch (error) {
                return false;
            }
        }

        playSemanticSfx(semantic) {
            const normalized = String(semantic || "").trim();
            if (!OFS_SFX_SEMANTICS.has(normalized) || !global.GameSfx
                || typeof global.GameSfx.play !== "function") return false;
            if (normalized === "progress_checkpoint" && this.reduceNonessentialSfx()) return false;
            const overrides = this.applicationContent && this.applicationContent.audio_events;
            const eventKey = overrides && OFS_SFX_EVENT_KEYS.has(overrides[normalized])
                ? overrides[normalized]
                : `ofs.${normalized}`;
            this.sfxSequence += 1;
            global.GameSfx.play(eventKey, {
                event_id: `ofs:${this.sessionId}:${this.presentationPhase}:${this.sfxSequence}`,
                session_id: this.sessionId,
                phase: this.presentationPhase,
                sequence: this.sfxSequence,
                app_id: this.appId,
                action_key: this.actionKey
            });
            return true;
        }

        setPresentationPhase(nextPhase, details = {}) {
            const normalized = String(nextPhase || "").trim();
            if (!PRESENTATION_PHASES.has(normalized)) return false;
            if (this.presentationPhase === normalized) return true;
            const previous = this.presentationPhase;
            this.presentationPhase = normalized;
            if (this.rendererHost && this.rendererHost.dataset) {
                this.rendererHost.dataset.ofsPhase = normalized;
                this.rendererHost.dataset.ofsTemplate = this.presentationMode;
            }
            if (this.appWindow && this.appWindow.dataset) {
                this.appWindow.dataset.ofsPhase = normalized;
            }
            this.trace("feedback_phase_changed", {
                previous_phase: previous,
                next_phase: normalized,
                elapsed_ms: Math.max(0, Math.round(this.now() - this.startedAt)),
                ...details
            });
            return true;
        }

        authorIntroLines() {
            const structured = this.applicationContent && this.applicationContent.structured;
            const legacy = this.applicationContent && this.applicationContent.legacy;
            const normalize = values => (Array.isArray(values) ? values : [])
                .map(value => typeof value === "string" ? value : value && value.text)
                .filter(Boolean);
            const candidates = [
                ...normalize(structured && structured.transition),
                ...normalize(structured && structured.boot),
                ...normalize(legacy && legacy.transition),
                ...normalize(legacy && legacy.boot),
                ...normalize(legacy && legacy.operation)
            ];
            return Array.from(new Set(candidates)).slice(0, 4);
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
            this.playSemanticSfx("choice_confirmed");
            this.activeChoice = null;
            this.setTimer(() => {
                if (!this.disposed && !this.activeChoice && container) {
                    container.replaceChildren();
                    container.hidden = true;
                }
                if (!this.disposed && this.state === "running") this.renderNextScene();
            }, 900);
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
            buttons.dataset.choiceLayout = choice.options.length === 1 ? "single"
                : (choice.options.length <= 4 ? "grid" : "list");
            buttons.dataset.choiceCount = String(choice.options.length);
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
            this.playSemanticSfx("choice_available");
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
            this.playSemanticSfx("intro");
            this.transition("running");
            this.render("Operacja w toku...", [
                `Aplikacja: ${this.appId || "narzedzie"}`,
                "Request przekazany do runtime.",
                "Oczekiwanie na potwierdzony payload."
            ]);
            Promise.resolve(this.configLoader()).then(config => {
                if (this.disposed || this.state !== "running") return;
                this.config = validateFeedbackConfig(config);
                this.profile = profileForPresentation(
                    this.config,
                    this.config.operations[this.actionKey],
                    this.presentationMode,
                    this.actionKey
                );
                if (!this.profile || this.profile.enabled !== true
                    || this.presentationMode === "ofs_provisional"
                    || !PRESENTATION_MODES.has(this.presentationMode)) {
                    throw new Error("OFS profile does not support renderer");
                }
                this.trace("feedback_profile_loaded", { content_version: this.config.content_version });
                if (this.authorIntroPresented) {
                    this.setPresentationPhase("executing");
                    this.trace("feedback_execution_started", { author_intro_reused: true });
                    this.renderNextScene();
                    return;
                }
                const authorLines = this.authorIntroLines();
                this.setPresentationPhase("author_intro");
                this.render(this.applicationContent.title || "Profil aplikacji", authorLines.length
                    ? authorLines
                    : ["Lokalny profil aplikacji jest gotowy."], "pending", "replace", "author_intro");
                this.trace("feedback_author_scene_started", {
                    content_source: this.applicationContent.structured ? "app_structured"
                        : (authorLines.length ? "app_legacy" : "global_fallback")
                });
                this.authorIntroPresented = true;
                this.setTimer(() => {
                    if (this.disposed || this.state !== "running") return;
                    this.setPresentationPhase("executing");
                    this.trace("feedback_execution_started");
                    this.renderNextScene();
                }, readableSceneDelay(authorLines, 0, MIN_AUTHOR_READ_MS));
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
            if (this.activeChoice) return;
            const elapsedMs = Math.max(0, this.now() - this.startedAt);
            const scene = composeScene({
                config: this.config,
                profile: this.profile,
                securityState: this.securityState,
                history: this.history,
                elapsedMs,
                random: this.random,
                presentationState: this.presentationState,
                applicationContent: null
            });
            if (this.state === "awaiting_payload") this.transition("running");
            this.render("Operacja w toku...", scene.lines, "pending", "replace", scene.scene_id);
            this.sceneSequence += 1;
            this.trace("feedback_scene_started", {
                scene_id: scene.scene_id,
                duration_profile: scene.duration_profile,
                elapsed_ms: Math.round(elapsedMs),
                content_source: scene.content_source,
                scene_dom_nodes: this.rendererHost && typeof this.rendererHost.querySelectorAll === "function"
                    ? this.rendererHost.querySelectorAll(".operation-feedback-line").length
                    : 0,
                visual_lift: Boolean(this.appWindow && this.appWindow.classList
                    && this.appWindow.classList.contains("ofs-visual-lift"))
            });
            if (this.progressSfxCount < MAX_PROGRESS_SFX_PER_SESSION
                && (this.sceneSequence === 1 || this.sceneSequence % 3 === 0)) {
                if (this.playSemanticSfx("progress_checkpoint")) this.progressSfxCount += 1;
            }
            this.maybePresentChoice(scene);
            if (this.activeChoice) return;
            this.setTimer(() => {
                if (this.disposed || this.state !== "running") return;
                this.renderNextScene();
            }, readableSceneDelay(scene.lines, scene.delay_ms));
        }

        complete(payload = {}) {
            if (this.disposed || TERMINAL_STATES.has(this.state)) return;
            this.clearTimers();
            this.clearChoice(true);
            this.transition("completing");
            this.setPresentationPhase("completing");
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
            this.playSemanticSfx(success ? "success" : "failure");
            this.setPresentationPhase(success ? "completed" : "failed", { success });
            this.setTimer(() => this.dispose("payload_complete"), MIN_COMPLETION_READ_MS);
        }

        fail(reason = "request_failed") {
            if (this.disposed || TERMINAL_STATES.has(this.state)) return;
            this.clearTimers();
            this.clearChoice(true);
            this.transition("failed");
            this.setPresentationPhase("failed");
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
            this.playSemanticSfx(
                failureCategory === "gameplay_failure" ? "failure" : "runtime_warning"
            );
            this.setTimer(() => this.dispose(reason), MIN_COMPLETION_READ_MS);
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
            this.setPresentationPhase("cancelled");
            this.trace("feedback_cancelled", { completion_reason: String(reason || "cancelled") });
            this.dispose(reason);
        }

        dispose(reason = "disposed") {
            if (this.disposed) return;
            this.clearTimers();
            this.clearChoice(true);
            const preserveFinalScene = this.presentationPhase === "completed" || this.presentationPhase === "failed";
            if (this.state !== "disposed") this.transition("disposed");
            if (!preserveFinalScene) this.setPresentationPhase("disposed");
            this.disposed = true;
            this.presentationState = {};
            if (this.renderer && typeof this.renderer.dispose === "function") {
                this.renderer.dispose({preservePanel: preserveFinalScene});
            }
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
            if (options.rendererHost && typeof options.rendererHost.querySelectorAll === "function") {
                Array.from(options.rendererHost.querySelectorAll(".operation-feedback-panel"))
                    .forEach(panel => panel.remove());
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
        buildApplicationBrandModel,
        validateFeedbackConfig,
        loadFeedbackConfig,
        durationProfileFor,
        composeScene,
        composeProvisionalScene,
        provisionalWaitBandFor,
        createSceneEnvelope,
        createPresentationRenderer,
        presentationModeForInterface,
        presentationModeForAction,
        ProvisionalSceneRenderer,
        ExecutionSceneRenderer,
        TerminalSceneRenderer,
        ButtonChoiceSceneRenderer,
        WindowSceneRenderer,
        ProgressbarRandomSceneRenderer
    });
})(window);
