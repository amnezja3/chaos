"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/operation_feedback.js", "utf8");
const profileData = JSON.parse(fs.readFileSync("static/data/operation_feedback.v1.json", "utf8"));
const sandbox = {
    window: {
        document: null,
        console,
        performance: { now: () => 0 },
        fetch: () => Promise.reject(new Error("fetch disabled in composer test"))
    },
    console,
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
let fakeTimerId = 0;
const fakeClock = {
    setTimeout(callback) {
        fakeTimerId += 1;
        fakeTimers.set(fakeTimerId, callback);
        return fakeTimerId;
    },
    clearTimeout(timerId) {
        fakeTimers.delete(timerId);
    },
    run(timerId) {
        const callback = fakeTimers.get(timerId);
        fakeTimers.delete(timerId);
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

session.activeChoice = config.choice_library["feedback.scan_ports.pace"];
session.choiceTimeoutId = session.setTimer(() => session.resolveChoice("quiet", "timeout"), 7000);
session.complete({success: true});
assert.strictEqual(session.state, "completing");
assert.strictEqual(session.activeChoice, null);
assert.strictEqual(fakeTimers.size, 1); // tylko kontrolowany dispose completion

const invalidMutationConfig = JSON.parse(JSON.stringify(profileData));
invalidMutationConfig.choice_library["feedback.scan_ports.visibility"].options[0].set = {gameplay_power: 999};
assert.throws(() => ofs.validateFeedbackConfig(invalidMutationConfig), /undeclared state/);

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
    console.log("operation feedback composer OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
