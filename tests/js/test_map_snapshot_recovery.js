const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const template = fs.readFileSync("templates/map_template.html", "utf8");

function sourceBetween(startMarker, endMarker) {
    const start = template.indexOf(startMarker);
    const end = template.indexOf(endMarker, start);
    assert.ok(start >= 0 && end > start, `missing source: ${startMarker}`);
    return template.slice(start, end);
}

async function testCriticalSnapshotCoalescesExistingOwner() {
    let fetchCount = 0;
    let releaseFetch;
    const fetchResult = new Promise(resolve => { releaseFetch = resolve; });
    const sandbox = {
        window: {
            mapBootState: { loading: false, ready: true },
            mapRefreshState: {
                inFlight: {}, controllers: {}, critical: {}, promises: {},
                paused: false, pauseReason: ""
            }
        },
        AbortController,
        console: { warn() {} },
        clearTimeout,
        setTimeout,
        fetch: async () => {
            fetchCount += 1;
            return fetchResult;
        }
    };
    vm.createContext(sandbox);
    vm.runInContext(sourceBetween(
        "window.fetchMapSnapshot = async function",
        "window.buildClanVulnerabilityIcon"
    ), sandbox);

    const optional = sandbox.window.fetchMapSnapshot("player_areas", "/snapshot");
    const critical = sandbox.window.fetchMapSnapshot(
        "player_areas", "/snapshot", { recovery: true }
    );
    assert.strictEqual(fetchCount, 1, "critical recovery must share the in-flight owner");
    releaseFetch({ ok: true });
    const [optionalResult, criticalResult] = await Promise.all([optional, critical]);
    assert.strictEqual(optionalResult.res.ok, true);
    assert.strictEqual(criticalResult.res.ok, true);
}

async function testRecoveryRetriesAndNewestSequenceWins() {
    let calls = 0;
    let releaseFirst;
    const sandbox = {
        window: {},
        Promise,
        console: { warn() {} },
        setTimeout(callback) { callback(); return 1; }
    };
    vm.createContext(sandbox);
    vm.runInContext(sourceBetween(
        "window.territoryRecoveryState =",
        "window.applyTerritoryDelta"
    ), sandbox);
    sandbox.window.refreshPlayerAreas = async () => {
        calls += 1;
        if (calls === 1) await new Promise(resolve => { releaseFirst = resolve; });
        return calls > 1;
    };

    const first = sandbox.window.requestTerritorySnapshotRecovery("delta-a");
    await Promise.resolve();
    const second = sandbox.window.requestTerritorySnapshotRecovery("delta-b");
    assert.strictEqual(first, second, "one recovery owner must be shared");
    releaseFirst();
    assert.strictEqual(await first, true);
    assert.strictEqual(calls, 2, "a newer delta must force a newest-sequence snapshot");
    assert.strictEqual(sandbox.window.territoryRecoveryState.lastResult.ok, true);
}

(async () => {
    await testCriticalSnapshotCoalescesExistingOwner();
    await testRecoveryRetriesAndNewestSequenceWins();
    console.log("map snapshot recovery tests: OK");
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
