const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/terminal.js", "utf8");
const lifecycleStart = source.indexOf("function gonnaWinLifecycleKey");
const lifecycleEnd = source.indexOf("function applyApplicationLaunchContext", lifecycleStart);
const feedbackStart = source.indexOf("function beginOperationFeedbackRequest");
const feedbackEnd = source.indexOf("function startLegacyAppWaitUnlessFeedbackEnabled", feedbackStart);
assert.ok(lifecycleStart >= 0 && lifecycleEnd > lifecycleStart);
assert.ok(feedbackStart >= 0 && feedbackEnd > feedbackStart);

const traces = [];
const sessionCalls = { complete: 0, fail: 0 };
const sysinfo = { dataset: {}, textContent: "RUNNING" };
const context = {
    flow_id: "flow-130-12-2",
    launch_receipt: "receipt-130-12-2",
    invocation_id: "invocation-130-12-2",
    app_id: "sniff_tool",
    action_key: "sniff",
    security_state: {},
    application_content: null
};
const appWindow = {
    dataset: {},
    querySelector(selector) {
        return selector === "[data-terminal-sysinfo]" ? sysinfo : null;
    }
};
const sandbox = {
    console,
    Map,
    Set,
    gonnaWinLifecycleStates: new Map(),
    GONNA_WIN_LIFECYCLE_LIMIT: 128,
    currentApplicationLaunchContext: () => context,
    updateProvisionalApplicationSession() {},
    setApplicationPresentationPhase() {},
    finishApplicationTitleSequence() {},
    startAppWaitLog: () => () => {},
    appFlowTrace: (_flowId, eventName, details) => traces.push({ eventName, details }),
    window: {
        OperationFeedbackSystem: {
            isEnabled: () => true,
            presentationModeForAction: () => "terminal",
            createSession: () => ({
                complete() { sessionCalls.complete += 1; },
                fail() { sessionCalls.fail += 1; },
                presentProgressCompletion() { return true; }
            })
        }
    }
};
vm.createContext(sandbox);
vm.runInContext(
    `${source.slice(lifecycleStart, lifecycleEnd)}\n${source.slice(feedbackStart, feedbackEnd)}`,
    sandbox
);

assert.strictEqual(sandbox.nextGonnaWinRequestOrdinal(context, "choice:auto"), 1);
assert.strictEqual(sandbox.nextGonnaWinRequestOrdinal(context, "choice:auto"), 2);
assert.strictEqual(sandbox.nextGonnaWinRequestOrdinal(context, "operation_only"), 1);

const owner = sandbox.beginOperationFeedbackRequest(appWindow, "sniff_tool", {
    legacyWait: false,
    receiptScope: "choice:auto"
});
assert.strictEqual(owner.complete({
    success: true,
    created_operations: [{ operation_id: "operation-1" }]
}), true);
assert.strictEqual(sessionCalls.complete, 1);
assert.strictEqual(sysinfo.textContent, "COMPLETE");

const sameOwner = sandbox.beginOperationFeedbackRequest(appWindow, "sniff_tool", {
    legacyWait: false,
    receiptScope: "choice:auto"
});
assert.strictEqual(sameOwner, owner, "one semantic receipt must retain one OFS terminal owner");
assert.strictEqual(owner.complete({ success: false, error: "late conflict" }), false);
assert.strictEqual(owner.fail("late_transport_failure"), false);
assert.strictEqual(sessionCalls.complete, 1, "late failure must not overwrite canonical completion");
assert.strictEqual(sessionCalls.fail, 0, "late transport failure must not turn OFS red");
assert.strictEqual(sysinfo.textContent, "COMPLETE");
assert.ok(traces.some(item => item.eventName === "ofs_false_failure_suppressed"));
assert.ok(traces.some(item => item.eventName === "ofs_transport_failure_suppressed"));

const preserved = sandbox.preserveCanonicalGonnaWinSuccess(
    context,
    "choice:auto",
    { success: false }
);
assert.strictEqual(preserved.success, true);
assert.strictEqual(preserved.semantic_success_preserved, true);
assert.deepStrictEqual(Array.from(
    sandbox.getGonnaWinLifecycle(context, "choice:auto").operationIds
), ["operation-1"]);

console.log("gonna-win lifecycle tests: OK");
