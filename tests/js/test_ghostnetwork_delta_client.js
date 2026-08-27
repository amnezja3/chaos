const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/ghostnetwork_delta_client.js", "utf8");

function loadClient(windowOverrides = {}) {
    const window = {
        console: { warn() {} },
        Set,
        Promise,
        ...windowOverrides
    };
    window.window = window;
    if (!window.parent) window.parent = window;
    const sandbox = { window, console: window.console, Set, Promise };
    vm.createContext(sandbox);
    vm.runInContext(source, sandbox);
    return sandbox.window;
}

function ghostEvent(overrides = {}) {
    return {
        type: "ghost.part_discovered",
        scope: "ghostnetwork",
        dedupe_key: "event-1",
        payload: { cycle_id: "cycle-1", state_version: 2 },
        ...overrides
    };
}

function testWorksWithoutLeafletOrMap() {
    const window = loadClient();
    let notified = 0;
    window.GhostNetworkDeltaClient.registerView("suite", () => { notified += 1; });

    assert.strictEqual(window.GhostNetworkDeltaClient.handle(ghostEvent()), true);
    assert.strictEqual(notified, 1);
    assert.strictEqual(window.GhostNetworkDeltaClient.state.cycleId, "cycle-1");
    assert.strictEqual(window.GhostNetworkDeltaClient.state.stateVersion, 2);
    assert.strictEqual(window.GhostNetworkDeltaClient.handle(ghostEvent()), false);
    assert.strictEqual(notified, 1, "duplicate must not be delivered twice");
}

function testAdapterAndRecoveryContracts() {
    const window = loadClient();
    let applied = 0;
    let recovered = "";
    const client = window.GhostNetworkDeltaClient;
    client.registerAdapter("map", {
        apply() { applied += 1; return true; },
        recover(reason) { recovered = reason; return true; }
    });
    client.setBaseline({ cycleId: "cycle-1", stateVersion: 3 });

    assert.strictEqual(client.handle(ghostEvent({ dedupe_key: "event-2" })), true);
    assert.strictEqual(applied, 1);
    assert.strictEqual(client.handle(ghostEvent({
        dedupe_key: "event-3",
        payload: { cycle_id: "cycle-2", state_version: 4 }
    })), false);
    assert.strictEqual(recovered, "cycle_mismatch");
}

function testTransportGapTriggersRecovery() {
    const window = loadClient();
    let recovered = "";
    const client = window.GhostNetworkDeltaClient;
    client.setRecoveryHandler(reason => { recovered = reason; return true; });
    assert.strictEqual(client.handle(ghostEvent({
        dedupe_key: "transport-1",
        transport_version: 1
    })), true);
    assert.strictEqual(client.handle(ghostEvent({
        dedupe_key: "transport-3",
        transport_version: 3,
        payload: { cycle_id: "cycle-1", state_version: 3 }
    })), false);
    assert.strictEqual(recovered, "transport_gap");
}

function testIframeReusesDesktopSingleton() {
    const desktop = loadClient();
    const child = loadClient({ parent: desktop });
    assert.strictEqual(child.GhostNetworkDeltaClient, desktop.GhostNetworkDeltaClient);
}

function testFailedAdapterRecoversWithoutBlockingSuccessfulSibling() {
    const window = loadClient();
    const client = window.GhostNetworkDeltaClient;
    let suiteRecoveries = 0;
    let mapApplies = 0;
    client.registerAdapter("suite", {
        accepts: event => String(event.type || "").startsWith("ghost.part_"),
        apply() { return false; },
        recover(reason) {
            assert.strictEqual(reason, "unapplied_delta");
            suiteRecoveries += 1;
            return true;
        }
    });
    client.registerAdapter("map", {
        accepts: event => String(event.type || "").startsWith("ghost.part_"),
        apply() { mapApplies += 1; return true; },
    });

    assert.strictEqual(client.handle(ghostEvent({ dedupe_key: "partial-adapter" })), true);
    assert.strictEqual(mapApplies, 1);
    assert.strictEqual(suiteRecoveries, 1, "failed Suite adapter must recover even when map applied the event");
}

function testAdapterPredicateSkipsUnrelatedEvent() {
    const window = loadClient();
    const client = window.GhostNetworkDeltaClient;
    let applies = 0;
    client.registerAdapter("part-only", {
        accepts: event => String(event.type || "").startsWith("ghost.part_"),
        apply() { applies += 1; return true; },
    });
    assert.strictEqual(client.handle(ghostEvent({
        dedupe_key: "machine-event",
        type: "ghost.machine_progress_changed",
    })), true);
    assert.strictEqual(applies, 0);
}

function testMapAndSuiteBaselinesDoNotRegressSharedVersion() {
    const window = loadClient();
    const client = window.GhostNetworkDeltaClient;
    client.setBaseline({ view: "map", cycleId: "cycle-1", stateVersion: 12, snapshotChecksum: "map-12" });
    client.setBaseline({ view: "suite", cycleId: "cycle-1", stateVersion: 10, snapshotChecksum: "suite-10" });
    assert.strictEqual(client.state.stateVersion, 12);
    assert.strictEqual(client.state.baselines.map.snapshotChecksum, "map-12");
    assert.strictEqual(client.state.baselines.suite.snapshotChecksum, "suite-10");
}

function testAdapterUnregisterLeavesSharedClientAlive() {
    const window = loadClient();
    const client = window.GhostNetworkDeltaClient;
    client.registerAdapter("suite", { apply() { return true; } });
    assert.ok(client.state.adapters.suite);
    assert.strictEqual(client.unregisterAdapter("suite"), true);
    assert.strictEqual(client.state.adapters.suite, undefined);
    assert.strictEqual(typeof window.GhostNetworkDeltaClient.handle, "function");
}

testWorksWithoutLeafletOrMap();
testAdapterAndRecoveryContracts();
testTransportGapTriggersRecovery();
testIframeReusesDesktopSingleton();
testFailedAdapterRecoversWithoutBlockingSuccessfulSibling();
testAdapterPredicateSkipsUnrelatedEvent();
testMapAndSuiteBaselinesDoNotRegressSharedVersion();
testAdapterUnregisterLeavesSharedClientAlive();

console.log("ghostnetwork delta client tests: ok");
