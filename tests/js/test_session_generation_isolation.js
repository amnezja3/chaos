const assert = require("assert");
const fs = require("fs");
const path = require("path");

let capturedInit = null;
let redirect = null;
let scheduled = null;
let storageCleared = false;
let invalidationEvent = null;
let forcedResponse = null;

global.location = {
    href: "https://chaos.test/desktop",
    origin: "https://chaos.test",
    replace: (target) => { redirect = target; },
};
global.setTimeout = (callback) => { scheduled = callback; return 1; };
global.sessionStorage = { clear: () => { storageCleared = true; } };
global.dispatchEvent = (event) => { invalidationEvent = event; };
global.CustomEvent = class CustomEvent {
    constructor(type, options) { this.type = type; this.detail = options.detail; }
};
global.BroadcastChannel = class BroadcastChannel {
    constructor() { this.onmessage = null; }
    postMessage(message) { this.lastMessage = message; }
};

const matchingHeaders = {
    get(name) {
        if (name === "X-Chaos-Session-Generation") return "generation-a";
        if (name === "X-Chaos-Session-User") return "alice";
        return "";
    },
};

async function fakeFetch(_input, init) {
    capturedInit = init;
    return forcedResponse || { status: 200, headers: matchingHeaders };
}

const bridge = require("../../static/js/session_generation.js");
bridge.install({
    config: {
        generation: "generation-a",
        username: "alice",
        header: "X-Chaos-Session-Generation",
    },
    fetch: fakeFetch,
});

(async () => {
    const response = await global.fetch("/api/profile");
    assert.strictEqual(response.status, 200);
    assert.strictEqual(
        capturedInit.headers.get("X-Chaos-Session-Generation"),
        "generation-a",
    );
    assert.strictEqual(bridge.getState().invalidated, false);

    capturedInit = null;
    await global.fetch(new URL("https://outside.test/api/profile"));
    assert.strictEqual(capturedInit.headers, undefined);

    capturedInit = null;
    await global.fetch({ href: "https://outside.test/api/profile" });
    assert.strictEqual(capturedInit.headers, undefined);

    capturedInit = null;
    await global.fetch(new URL("https://chaos.test/api/profile"));
    assert.strictEqual(
        capturedInit.headers.get("X-Chaos-Session-Generation"),
        "generation-a",
    );

    capturedInit = null;
    await global.fetch({ unknownRequestObject: true });
    assert.strictEqual(capturedInit.headers, undefined);

    const missingIdentityHeadersResponse = {
        status: 200,
        headers: {
            get() { return ""; },
        },
    };
    forcedResponse = missingIdentityHeadersResponse;
    const staticResponse = await global.fetch("/static/runtime.json");
    assert.strictEqual(staticResponse.status, 200);
    assert.strictEqual(bridge.getState().invalidated, false);

    capturedInit = null;
    const publicCatalogResponse = await global.fetch("/resources.json");
    assert.strictEqual(publicCatalogResponse.status, 200);
    assert.strictEqual(capturedInit.headers, undefined);
    assert.strictEqual(bridge.getState().invalidated, false);

    await assert.rejects(
        () => global.fetch("/api/profile"),
        (error) => error.code === "session_generation_mismatch"
            && error.reason === "response_identity_headers_missing",
    );
    assert.strictEqual(bridge.getState().invalidated, true);
    assert.strictEqual(storageCleared, true);
    assert.strictEqual(invalidationEvent.type, "chaos:session-invalidated");
    assert.strictEqual(redirect, null);
    scheduled();
    assert.strictEqual(
        redirect,
        "/session/recover?reason=response_identity_headers_missing",
    );

    const terminalSource = fs.readFileSync(
        path.join(__dirname, "../../static/js/terminal.js"),
        "utf8",
    );
    assert.ok(terminalSource.includes('"chaos:session-invalidated"'));
    assert.ok(terminalSource.includes("teardownDesktopForInvalidatedSession"));
    assert.ok(terminalSource.includes("desktopSessionTeardownComplete = true"));
    assert.ok(terminalSource.includes("desktopSessionActive = false"));
    assert.ok(terminalSource.includes("processedDeltaKeys.clear()"));
    assert.ok(terminalSource.includes("clearInterval(stateDeltaPollInterval)"));
    assert.ok(terminalSource.includes("clearInterval(systemMessagesPollInterval)"));
    assert.ok(terminalSource.includes("clearTimeout(launchQueuePollTimer)"));

    await assert.rejects(
        () => global.fetch("/api/profile"),
        (error) => error.code === "session_generation_mismatch",
    );

    console.log("session generation JS isolation tests: ok");
})().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
