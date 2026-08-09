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

console.log("operation feedback composer OK");
