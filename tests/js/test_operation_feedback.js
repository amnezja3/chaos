"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/operation_feedback.js", "utf8");
const profileData = JSON.parse(fs.readFileSync("static/data/operation_feedback.v1.json", "utf8"));
const testConsole = {log: console.log, error: console.error, warn() {}};
const sandbox = {
    window: {
        document: null,
        console: testConsole,
        performance: { now: () => 0 },
        fetch: () => Promise.reject(new Error("fetch disabled in composer test"))
    },
    console: testConsole,
    Math,
    Object,
    Array,
    Number,
    Set,
    Promise,
    Error
};
vm.createContext(sandbox);
vm.runInContext(source, sandbox);

const ofs = sandbox.window.OperationFeedbackSystem;
const compactBrand = ofs.buildApplicationBrandModel({
    name: "V-MAP",
    icon: "❄️",
    interface: "terminal"
});
const compactBrandAgain = ofs.buildApplicationBrandModel({
    name: "V-MAP",
    icon: "❄️",
    interface: "terminal"
});
const pairedBrand = ofs.buildApplicationBrandModel({
    name: "Trace Compass",
    icon: "🎯",
    interface: "window"
});
const denseBrand = ofs.buildApplicationBrandModel({
    name: "Katolicka Szkola Podstawowa Security Console",
    icon: "🏫",
    interface: "button_choices"
});
const missingBrand = ofs.buildApplicationBrandModel({interface: "progressbar_random"});
const specialBrand = ofs.buildApplicationBrandModel({name: "Słówko ++", interface: "window"});
assert.deepStrictEqual(JSON.parse(JSON.stringify(compactBrand)), JSON.parse(JSON.stringify(compactBrandAgain)));
assert.strictEqual(Object.isFrozen(compactBrand), true);
assert.strictEqual(compactBrand.name_metrics.name_class, "compact-mark");
assert.strictEqual(compactBrand.author_logo_header.mode, "icon_text_horizontal");
assert.strictEqual(pairedBrand.name_metrics.word_count, 2);
assert.strictEqual(denseBrand.name_metrics.name_class, "dense-title");
assert.strictEqual(denseBrand.author_logo_header.mode, "icon_only");
assert.strictEqual(denseBrand.author_footer.mode, "icon_only");
assert.ok(compactBrand.title_sequence.duration_ms >= 1800);
assert.ok(compactBrand.title_sequence.duration_ms <= 3800);
assert.strictEqual(compactBrand.title_sequence.readable_ms, 900);
assert.strictEqual(missingBrand.name, "Aplikacja");
assert.strictEqual(missingBrand.icon, "▣");
assert.strictEqual(specialBrand.name_metrics.word_count, 2);
class FakeNode {
    constructor(tagName = "div") {
        this.tagName = tagName;
        this.className = "";
        this.dataset = {};
        this.children = [];
        this.parentNode = null;
        this.isConnected = true;
        this.hidden = false;
        this.textContent = "";
    }
    appendChild(node) {
        node.parentNode = this;
        node.isConnected = true;
        this.children.push(node);
        return node;
    }
    replaceChildren(...nodes) {
        this.children.forEach(node => { node.parentNode = null; node.isConnected = false; });
        this.children = [];
        nodes.forEach(node => this.appendChild(node));
    }
    querySelector(selector) {
        const className = selector.startsWith(".") ? selector.slice(1) : "";
        for (const child of this.children) {
            if (String(child.className).split(/\s+/).includes(className)) return child;
            const nested = child.querySelector(selector);
            if (nested) return nested;
        }
        return null;
    }
    querySelectorAll(selector) {
        const found = [];
        const className = selector.startsWith(".") ? selector.slice(1) : "";
        this.children.forEach(child => {
            if ((selector === "button" && child.tagName === "button")
                || String(child.className).split(/\s+/).includes(className)) found.push(child);
            found.push(...child.querySelectorAll(selector));
        });
        return found;
    }
    setAttribute() {}
    addEventListener() {}
    remove() {
        if (this.parentNode) {
            this.parentNode.children = this.parentNode.children.filter(child => child !== this);
        }
        this.parentNode = null;
        this.isConnected = false;
    }
    get firstElementChild() { return this.children[0] || null; }
}
sandbox.window.document = {createElement: tagName => new FakeNode(tagName)};
const provisionalEnvelope = ofs.createSceneEnvelope({
    presentation_mode: "ofs_provisional",
    phase: "booting",
    scene_id: "local_init",
    lines: ["Inicjalizacja lokalnego profilu.", "Przygotowanie widoku aplikacji."],
    transition: "replace",
    content_source: "local_fallback"
});
assert.strictEqual(provisionalEnvelope.presentation_mode, "ofs_provisional");
assert.strictEqual(provisionalEnvelope.lines.length, 2);
assert.ok(Object.isFrozen(provisionalEnvelope));
assert.ok(Object.isFrozen(provisionalEnvelope.lines));
assert.throws(
    () => ofs.createSceneEnvelope({presentation_mode: "unknown", lines: ["test"]}),
    /unsupported presentation mode/
);
assert.throws(
    () => ofs.createSceneEnvelope({presentation_mode: "ofs_provisional", transition: "progress", lines: ["test"]}),
    /unsupported scene transition/
);
const executionRenderers = ["terminal", "button_choice", "window", "progressbar_random"].map(mode =>
    ofs.createPresentationRenderer(mode, {})
);
assert.deepStrictEqual(
    executionRenderers.map(renderer => renderer.presentationMode),
    ["terminal", "button_choice", "window", "progressbar_random"]
);
executionRenderers.forEach(renderer => renderer.dispose());
assert.strictEqual(ofs.createPresentationRenderer("unknown", {}), null);
assert.strictEqual(ofs.presentationModeForInterface("progressbar_random"), "progressbar_random");
assert.strictEqual(ofs.presentationModeForInterface("terminal"), "terminal");
assert.strictEqual(ofs.presentationModeForInterface("button_choices"), "button_choice");
assert.strictEqual(ofs.presentationModeForInterface("unsupported"), null);
for (const mode of ["terminal", "button_choice", "window", "progressbar_random"]) {
    const host = new FakeNode("main");
    const renderer = ofs.createPresentationRenderer(mode, {
        host,
        sessionId: `test:${mode}`,
        applicationContent: {title: `TEST ${mode}`}
    });
    assert.strictEqual(renderer.render({
        phase: "running",
        scene_id: "probe",
        status: "Operacja w toku",
        lines: ["Linia A", "Linia B"],
        transition: "replace"
    }), true);
    assert.strictEqual(host.dataset.presentationOwner, renderer.owner);
    assert.strictEqual(renderer.panel.querySelector(".operation-feedback-lines").children.length, 2);
    assert.strictEqual(
        renderer.panel.querySelector(".operation-feedback-line").dataset.sceneRole,
        "command"
    );
    assert.ok(renderer.panel.querySelector(".ofs-scene-icon"));
    assert.strictEqual(Boolean(renderer.choiceContainer()), mode === "button_choice");
    renderer.render({
        phase: "running",
        scene_id: "follow_up",
        status: "Dalsza praca",
        lines: ["C", "D", "E", "F", "G", "H"],
        slots: mode === "window" ? {stage: "probe", activity: "local"} : {},
        transition: "append_short"
    });
    assert.strictEqual(renderer.panel.querySelector(".operation-feedback-lines").children.length, 6);
    if (mode === "window") {
        assert.strictEqual(renderer.panel.querySelector(".operation-feedback-slots").children.length, 2);
    }
    renderer.dispose();
    assert.strictEqual(host.dataset.presentationOwner, undefined);
}
const semanticHost = new FakeNode("main");
const semanticRenderer = ofs.createPresentationRenderer("ofs_provisional", {host: semanticHost});
const hydrationEnvelope = ofs.createSceneEnvelope({
    presentation_mode: "ofs_provisional",
    phase: "booting",
    scene_id: "hydration_wait",
    lines: ["Oczekiwanie na runtime."],
    transition: "replace",
    wait_band: "long",
    content_source: "local_fallback"
});
assert.strictEqual(semanticRenderer.render(hydrationEnvelope), true);
assert.strictEqual(semanticHost.dataset.sceneRole, "checkpoint");
assert.strictEqual(semanticHost.dataset.ofsWaitBand, "long");
assert.strictEqual(
    semanticHost.querySelector(".provisional-app-scene-line").dataset.sceneRole,
    "checkpoint"
);
assert.ok(semanticHost.querySelector(".ofs-scene-icon"));
semanticRenderer.dispose();
assert.strictEqual(semanticHost.dataset.ofsWaitBand, undefined);
assert.strictEqual(semanticHost.dataset.sceneRole, undefined);
const occupiedHost = {isConnected: true, dataset: {presentationOwner: "other:1"}};
const provisionalRenderer = ofs.createPresentationRenderer("ofs_provisional", {host: occupiedHost});
assert.throws(
    () => provisionalRenderer.render(provisionalEnvelope),
    /already has an owner/
);
provisionalRenderer.dispose();
const config = ofs.validateFeedbackConfig(profileData);
const operation = config.operations.scan_ports;
const securityState = ofs.sanitizeSecurityState({
    scan_detection: true,
    firewall: true,
    firewall_core: true
});
const history = { last_scene: null, last_security: null, last_line: null };
const randomValues = [0.03, 0.71, 0.22, 0.88, 0.41, 0.62];
let randomIndex = 0;
const random = () => randomValues[(randomIndex++) % randomValues.length];

const elapsedValues = [0, 4500, 16000, 18000, 41000, 91000];
const scenes = elapsedValues.map(elapsedMs => ofs.composeScene({
    config,
    profile: operation,
    securityState,
    history,
    elapsedMs,
    random
}));

assert.ok(new Set(scenes.map(scene => scene.scene_id)).size >= 3);
scenes.forEach((scene, index) => {
    assert.ok(scene.lines.length >= scene.min_lines);
    assert.ok(scene.lines.length <= 5);
    assert.ok(scene.delay_ms >= 0 && scene.delay_ms <= 10000);
    if (index > 0) assert.notStrictEqual(scene.scene_id, scenes[index - 1].scene_id);
});
assert.strictEqual(ofs.durationProfileFor(config, 0).id, "instant");
assert.strictEqual(ofs.durationProfileFor(config, 15000).id, "medium");
assert.strictEqual(ofs.durationProfileFor(config, 90000).id, "very_long");

const voiceA = ofs.projectApplicationContent({
    id: "quiet_mapper",
    name: "Quiet Mapper",
    interface: "terminal",
    levels: [{command: "quiet-map --ports", logs: ["passive service sampling"]}]
});
const voiceB = ofs.projectApplicationContent({
    id: "neon_scanner",
    name: "Neon Scanner",
    interface: "terminal",
    levels: [{command: "neon-scan --burst", logs: ["burst channel sweep"]}]
});
const voiceScene = content => ofs.composeScene({
    config,
    profile: operation,
    securityState,
    history: {last_scene: null, last_security: null, last_line: null},
    elapsedMs: 0,
    random: () => 0,
    applicationContent: content,
    presentationState: {}
});
const transcriptA = voiceScene(voiceA);
const transcriptB = voiceScene(voiceB);
assert.ok(transcriptA.lines.includes("quiet-map --ports"));
assert.ok(transcriptB.lines.includes("neon-scan --burst"));
assert.notDeepStrictEqual(transcriptA.lines, transcriptB.lines);
assert.strictEqual(transcriptA.content_source, "app_legacy");

const structuredVoice = ofs.projectApplicationContent({
    id: "structured_mapper",
    name: "Structured Mapper",
    interface: "button_choices",
    levels: [{command: "legacy-command"}],
    feedback_content: {
        schema_version: "1.0.0",
        labels: {session_title: "STRUCTURED MAPPER"},
        scene_lines: {boot: ["structured passive boot"]}
    }
});
const structuredTranscript = voiceScene(structuredVoice);
assert.ok(structuredTranscript.lines.includes("structured passive boot"));
assert.ok(!structuredTranscript.lines.includes("legacy-command"));
assert.strictEqual(structuredTranscript.content_source, "app_structured");

const rejectedVoice = ofs.projectApplicationContent({
    id: "unsafe_mapper",
    levels: [{command: "target captured", logs: ["safe local probe"]}],
    feedback_content: {schema_version: "broken", scene_lines: {boot: ["structured line"]}}
});
const rejectedTranscript = voiceScene(rejectedVoice);
assert.ok(!rejectedTranscript.lines.includes("target captured"));
assert.ok(!rejectedTranscript.lines.includes("structured line"));

const fakeTimers = new Map();
const fakeTimerDelays = new Map();
let fakeTimerId = 0;
const fakeClock = {
    setTimeout(callback, delayMs) {
        fakeTimerId += 1;
        fakeTimers.set(fakeTimerId, callback);
        fakeTimerDelays.set(fakeTimerId, Number(delayMs) || 0);
        return fakeTimerId;
    },
    clearTimeout(timerId) {
        fakeTimers.delete(timerId);
        fakeTimerDelays.delete(timerId);
    },
    run(timerId) {
        const callback = fakeTimers.get(timerId);
        fakeTimers.delete(timerId);
        fakeTimerDelays.delete(timerId);
        if (callback) callback();
    }
};
const session = new ofs.OperationFeedbackSession({
    actionKey: "scan_ports",
    presentationMode: "button_choice",
    applicationContent: voiceA,
    clock: fakeClock,
    now: () => 5000
});
session.state = "running";
session.config = config;
session.profile = operation;
session.render = () => {};
session.activeChoice = config.choice_library["feedback.scan_ports.visibility"];
session.askedChoices.add(session.activeChoice.choice_id);
assert.strictEqual(session.resolveChoice("masked", "user"), true);
assert.strictEqual(session.presentationState.scan_mode, "masked");
const choiceDrivenTranscript = buildTranscript([5000, 16000, 30000], voiceB, session.presentationState);
choiceDrivenTranscript.forEach(scene => {
    assert.ok(scene.lines.some(line => /maskowan/i.test(line)));
});

const timeoutSession = new ofs.OperationFeedbackSession({
    actionKey: "scan_ports",
    presentationMode: "button_choice",
    applicationContent: voiceA,
    clock: fakeClock,
    now: () => 5000
});
timeoutSession.state = "running";
timeoutSession.config = config;
timeoutSession.profile = operation;
timeoutSession.render = () => {};
timeoutSession.activeChoice = config.choice_library["feedback.scan_ports.pace"];
const timeoutId = timeoutSession.setTimer(
    () => timeoutSession.resolveChoice(timeoutSession.activeChoice.default_value, "timeout"),
    timeoutSession.activeChoice.timeout_ms
);
fakeClock.run(timeoutId);
assert.strictEqual(timeoutSession.presentationState.probe_mode, "quiet");
timeoutSession.dispose("test_complete");

const frozenChoiceSession = new ofs.OperationFeedbackSession({
    actionKey: "scan_ports",
    presentationMode: "button_choice",
    applicationContent: voiceA,
    clock: fakeClock,
    now: () => 5000
});
frozenChoiceSession.state = "running";
frozenChoiceSession.config = config;
frozenChoiceSession.profile = operation;
frozenChoiceSession.activeChoice = config.choice_library["feedback.scan_ports.visibility"];
let frozenChoiceRenderCount = 0;
frozenChoiceSession.render = () => { frozenChoiceRenderCount += 1; };
frozenChoiceSession.renderNextScene();
assert.strictEqual(frozenChoiceRenderCount, 0, "active choice must freeze OFS scene rotation");
frozenChoiceSession.dispose("test_complete");

const phaseHost = new FakeNode("main");
const phaseEvents = [];
const phaseSession = new ofs.OperationFeedbackSession({
    actionKey: "scan_ports",
    presentationMode: "button_choice",
    rendererHost: phaseHost,
    applicationContent: voiceA,
    clock: fakeClock,
    now: () => 5000,
    onTrace: (eventName, details) => phaseEvents.push({eventName, details})
});
phaseSession.startedAt = 1000;
phaseSession.setPresentationPhase("author_intro");
assert.strictEqual(phaseHost.dataset.ofsPhase, "author_intro");
assert.strictEqual(phaseHost.dataset.ofsTemplate, "button_choice");
assert.ok(phaseEvents.some(event => event.eventName === "feedback_phase_changed"));
phaseSession.dispose("test_complete");

session.activeChoice = config.choice_library["feedback.scan_ports.pace"];
session.choiceTimeoutId = session.setTimer(() => session.resolveChoice("quiet", "timeout"), 7000);
session.complete({success: true});
assert.strictEqual(session.state, "completing");
assert.strictEqual(session.activeChoice, null);
assert.strictEqual(fakeTimers.size, 1); // tylko kontrolowany dispose completion

const invalidMutationConfig = JSON.parse(JSON.stringify(profileData));
invalidMutationConfig.choice_library["feedback.scan_ports.visibility"].options[0].set = {gameplay_power: 999};
const isolatedInvalidConfig = ofs.validateFeedbackConfig(invalidMutationConfig);
assert.strictEqual(isolatedInvalidConfig.operations.scan_ports.enabled, false);
assert.match(isolatedInvalidConfig.operations.scan_ports.validation_error, /undeclared state/);
assert.strictEqual(isolatedInvalidConfig.operations.exploit.enabled, true);

const expectedModes = {
    scan_ports: "button_choice", exploit: "terminal", sniff: "terminal",
    trace: "window", trace_gps: "window", trace_device: "window",
    mic_sniff: "terminal", atm_logs: "terminal", install_sniffer: "button_choice",
    camera_stream: "window", camera_shutdown: "button_choice", car_hack: "button_choice"
};
assert.strictEqual(Object.keys(config.operations).length, 12);
Object.entries(expectedModes).forEach(([actionKey, expectedMode]) => {
    const profile = config.operations[actionKey];
    assert.strictEqual(profile.enabled, true, profile.validation_error);
    assert.strictEqual(profile.default_presentation_mode, expectedMode);
    assert.strictEqual(ofs.presentationModeForAction(actionKey), expectedMode);
    assert.strictEqual(profile.provisional_profile.timeline_profile, "launch_150s");
    assert.ok(profile.provisional_profile.scene_pool.includes("extended_wait"));
    const scene = ofs.composeScene({
        config,
        profile,
        securityState: Object.fromEntries(Object.keys(profile.security).map(key => [key, true])),
        history: {last_scene: null, last_security: null, last_line: null},
        elapsedMs: 16000,
        random: () => 0,
        applicationContent: voiceA,
        presentationState: {}
    });
    assert.ok(scene.lines.length >= 2);
});
assert.strictEqual(ofs.isEnabled("exploit", {enabled: true, enabled_actions: ["exploit"]}), true);
assert.strictEqual(ofs.isEnabled("sniff", {enabled: true, enabled_actions: ["exploit"]}), false);
assert.strictEqual(ofs.isEnabled("scan_ports", {enabled: true, enabled_actions: ["scan_ports"]}), true);
assert.strictEqual(ofs.isEnabled("scan_ports", {enabled: true, enabled_actions: []}), false);

const provisionalTimeline = config.provisional_timelines.launch_150s;
assert.strictEqual(provisionalTimeline.stages[0].start_after_ms, 0);
assert.strictEqual(
    provisionalTimeline.stages[provisionalTimeline.stages.length - 1].start_after_ms,
    150000
);
assert.strictEqual(provisionalTimeline.stages.length, 15);
const provisionalProfile = config.operations.scan_ports;
const provisionalContext = {
    app_title: "Port Sentinel",
    description: "Lokalny skaner portow",
    interface: "button_choices",
    target_label: "POI-TEST",
    action_label: "scan_ports"
};
const firstProvisional = ofs.composeProvisionalScene({
    config, profile: provisionalProfile, stage: provisionalTimeline.stages[0],
    context: provisionalContext, history: {}, random: () => 0
});
assert.ok(firstProvisional.lines.some(line => line.includes("Port Sentinel")));
assert.ok(!firstProvisional.lines.some(line => /undefined/.test(line)));
const extendedStage = provisionalTimeline.stages[provisionalTimeline.stages.length - 1];
const extendedA = ofs.composeProvisionalScene({
    config, profile: provisionalProfile, stage: extendedStage,
    context: provisionalContext, history: {}, random: () => 0
});
const extendedB = ofs.composeProvisionalScene({
    config, profile: provisionalProfile, stage: extendedStage,
    context: provisionalContext, history: {last_variant: extendedA.variant_key}, random: () => 0
});
assert.notStrictEqual(extendedA.variant_key, extendedB.variant_key);
assert.deepStrictEqual(
    Object.keys(config.provisional_wait_bands),
    ["instant", "short", "medium", "long", "extended", "overdue"]
);
[
    [0, "instant"], [1499, "instant"], [1500, "short"], [8000, "medium"],
    [30000, "long"], [90000, "extended"], [150000, "overdue"]
].forEach(([elapsedMs, expected]) => {
    assert.strictEqual(ofs.provisionalWaitBandFor(config, elapsedMs).id, expected);
});
const provisionalFamilies = new Set(provisionalTimeline.stages.map(stage => stage.family));
["terminal", "button_choices", "window", "progressbar_random"].forEach(voice => {
    provisionalFamilies.forEach(family => {
        assert.ok(config.provisional_voice_packs[voice][family].length >= 3, `${voice}.${family}`);
    });
});
const rotationHistory = {recent_variants: []};
const rotated = [0, 1, 2].map(() => {
    const scene = ofs.composeProvisionalScene({
        config, profile: provisionalProfile, stage: extendedStage,
        context: provisionalContext, history: rotationHistory, elapsedMs: 160000, random: () => 0
    });
    rotationHistory.recent_variants.push(scene.variant_key);
    return scene;
});
assert.strictEqual(new Set(rotated.map(scene => scene.variant_key)).size, 3);
assert.ok(rotated.every(scene => scene.content_source === "provisional_voice_pack"));
assert.ok(rotated.every(scene => scene.wait_band === "overdue"));

const invalidVoicePack = JSON.parse(JSON.stringify(profileData));
delete invalidVoicePack.provisional_voice_packs.window.context_bind;
assert.throws(() => ofs.validateFeedbackConfig(invalidVoicePack), /too few variants/);

const invalidPlaceholderConfig = JSON.parse(JSON.stringify(profileData));
invalidPlaceholderConfig.provisional_scene_library.app_identity.voices.default[0][0] = "{owner_username}";
assert.throws(() => ofs.validateFeedbackConfig(invalidPlaceholderConfig), /forbidden placeholder/);

function buildTranscript(elapsedValues, applicationContent, presentationState = {}) {
    const localHistory = {last_scene: null, last_security: null, last_line: null};
    let index = 0;
    const localRandom = () => randomValues[(index++) % randomValues.length];
    return elapsedValues.map(elapsedMs => ofs.composeScene({
        config,
        profile: operation,
        securityState,
        history: localHistory,
        elapsedMs,
        random: localRandom,
        applicationContent,
        presentationState
    }));
}

const fastTranscript = buildTranscript([0, 2500], voiceA);
const mediumTranscript = buildTranscript([0, 5000, 16000, 30000], voiceB, {scan_mode: "masked"});
const longTranscript = buildTranscript([0, 5000, 16000, 41000, 91000], voiceA, {probe_mode: "fast"});
assert.notDeepStrictEqual(fastTranscript, mediumTranscript);
assert.notDeepStrictEqual(mediumTranscript, longTranscript);
assert.strictEqual(longTranscript[longTranscript.length - 1].duration_profile, "very_long");
mediumTranscript.slice(1).forEach(scene => {
    assert.ok(scene.lines.some(line => /maskowan/i.test(line)));
});
if (process.argv.includes("--transcripts")) {
    console.log(JSON.stringify({fastTranscript, mediumTranscript, longTranscript}, null, 2));
}

(async () => {
    let resolveProfile;
    const deferredProfile = new Promise(resolve => {
        resolveProfile = resolve;
    });
    const traceEvents = [];
    const deferredSession = new ofs.OperationFeedbackSession({
        actionKey: "scan_ports",
        presentationMode: "button_choice",
        applicationContent: voiceA,
        clock: fakeClock,
        now: () => 0,
        configLoader: () => deferredProfile,
        onTrace: eventName => traceEvents.push(eventName)
    });
    deferredSession.render = () => {};
    deferredSession.start();
    deferredSession.complete({success: true});
    resolveProfile(profileData);
    await Promise.resolve();
    await Promise.resolve();
    assert.strictEqual(deferredSession.state, "completing");
    assert.ok(!traceEvents.includes("feedback_scene_started"));

    const fallbackConfig = JSON.parse(JSON.stringify(profileData));
    fallbackConfig.operations.exploit.default_presentation_mode = "window";
    let fallbackCalled = false;
    const invalidProfileSession = new ofs.OperationFeedbackSession({
        actionKey: "exploit",
        presentationMode: "terminal",
        applicationContent: voiceA,
        clock: fakeClock,
        now: () => 0,
        configLoader: () => fallbackConfig,
        onProfileUnavailable: () => { fallbackCalled = true; }
    });
    invalidProfileSession.render = () => {};
    invalidProfileSession.start();
    await Promise.resolve();
    await Promise.resolve();
    assert.strictEqual(fallbackCalled, true);
    assert.strictEqual(invalidProfileSession.disposed, true);

    const authorTimers = new Map();
    let authorTimerId = 0;
    const authorClock = {
        setTimeout(callback, delayMs) {
            authorTimerId += 1;
            authorTimers.set(authorTimerId, {callback, delayMs});
            return authorTimerId;
        },
        clearTimeout(timerId) { authorTimers.delete(timerId); }
    };
    const authorEvents = [];
    const authorSession = new ofs.OperationFeedbackSession({
        actionKey: "scan_ports",
        presentationMode: "button_choice",
        applicationContent: voiceA,
        clock: authorClock,
        now: () => 0,
        configLoader: () => profileData,
        onTrace: eventName => authorEvents.push(eventName)
    });
    authorSession.render = () => {};
    authorSession.start();
    await Promise.resolve();
    await Promise.resolve();
    assert.strictEqual(authorSession.presentationPhase, "author_intro");
    assert.ok(authorEvents.includes("feedback_author_scene_started"));
    assert.ok(Array.from(authorTimers.values()).some(timer => timer.delayMs >= 4000));
    authorSession.dispose("test_complete");

    const reusedAuthorEvents = [];
    const reusedAuthorSession = new ofs.OperationFeedbackSession({
        actionKey: "scan_ports",
        presentationMode: "button_choice",
        applicationContent: voiceA,
        authorIntroPresented: true,
        clock: authorClock,
        now: () => 0,
        configLoader: () => profileData,
        onTrace: eventName => reusedAuthorEvents.push(eventName)
    });
    reusedAuthorSession.render = () => {};
    reusedAuthorSession.renderNextScene = () => {};
    reusedAuthorSession.start();
    await Promise.resolve();
    await Promise.resolve();
    assert.strictEqual(reusedAuthorSession.presentationPhase, "executing");
    assert.ok(reusedAuthorEvents.includes("feedback_execution_started"));
    assert.ok(!reusedAuthorEvents.includes("feedback_author_scene_started"));
    reusedAuthorSession.dispose("test_complete");
    console.log("operation feedback composer OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
