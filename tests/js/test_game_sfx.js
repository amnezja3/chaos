"use strict";

const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

const source = fs.readFileSync("static/js/game_sfx.js", "utf8");
const listeners = {};
const storage = {};
const manifest = {
    schema: 1,
    base_path: "/static/audio/sfx",
    buses: {
        lore: {max_voices: 1},
        gameplay: {max_voices: 2},
        message: {max_voices: 2},
        system: {max_voices: 1},
        ui: {max_voices: 3}
    },
    events: {
        "test.lore": {
            file: "test/lore.mp3",
            bus: "lore",
            priority: 70,
            volume: 0.5,
            max_duration_ms: 10000,
            cooldown_ms: 0,
            duck_radio: 0.4
        },
        "test.quiet": {
            file: "test/quiet.mp3",
            bus: "lore",
            priority: 10,
            volume: 1,
            max_duration_ms: 10000,
            cooldown_ms: 0,
            duck_radio: 1
        },
        "test.gameplay": {
            file: "test/gameplay.mp3",
            bus: "gameplay",
            priority: 60,
            volume: 1,
            max_duration_ms: 10000,
            cooldown_ms: 0,
            duck_radio: 0.7
        },
        "test.critical": {
            file: "test/critical.mp3",
            bus: "system",
            priority: 100,
            volume: 1,
            max_duration_ms: 10000,
            cooldown_ms: 0,
            duck_radio: 0.3,
            interrupt_lower_priority: true
        }
    }
};

class FakeAudio {
    constructor(src) {
        this.src = src || "";
        this.volume = 1;
        this.preload = "";
        this.listeners = {};
        this.paused = false;
    }
    addEventListener(name, callback) { this.listeners[name] = callback; }
    play() { return Promise.resolve(); }
    pause() { this.paused = true; }
    load() {}
    removeAttribute(name) { if (name === "src") this.src = ""; }
}

const duckHandles = [];
const sandbox = {
    window: {
        Audio: FakeAudio,
        Promise,
        Set,
        Map,
        Object,
        Array,
        Number,
        Date,
        console: {debug() {}, warn() {}, error() {}},
        fetch() {
            return Promise.resolve({ok: true, status: 200, json: () => Promise.resolve(manifest)});
        },
        localStorage: {
            getItem(key) { return Object.prototype.hasOwnProperty.call(storage, key) ? storage[key] : null; },
            setItem(key, value) { storage[key] = String(value); }
        },
        document: {
            readyState: "complete",
            addEventListener(name, callback) { listeners[name] = callback; },
            removeEventListener(name) { delete listeners[name]; }
        },
        GhostRadio: {
            requestDuck(gain, sourceId) {
                const handle = {gain, sourceId, released: false, release() { this.released = true; return true; }};
                duckHandles.push(handle);
                return handle;
            }
        },
        setTimeout,
        clearTimeout
    },
    console,
    Promise,
    Set,
    Map,
    Object,
    Array,
    Number,
    Date,
    setTimeout,
    clearTimeout
};
sandbox.window.window = sandbox.window;
vm.createContext(sandbox);
vm.runInContext(source, sandbox);

const sfx = sandbox.window.GameSfx;

(async function run() {
    await sfx.init();
    assert.strictEqual(sfx.getState().manifest_loaded, true);
    assert.strictEqual(sfx.getState().enabled, true);
    assert.strictEqual(sfx.setVolume(2), 1);
    assert.strictEqual(storage.chaos_sfx_volume, "1");

    const normalized = sfx._normalizeManifestForTest({
        schema: 1,
        base_path: "/static/audio/sfx",
        events: {
            safe: {file: "ui/safe.mp3", bus: "ui"},
            unsafe: {file: "../secret.mp3", bus: "ui"}
        }
    });
    assert.ok(normalized.events.safe);
    assert.strictEqual(normalized.events.unsafe, undefined);
    assert.strictEqual(normalized.buses.gameplay.max_voices, 2);
    assert.strictEqual(sfx._voiceWatchdogDelayForTest(4000, 6), 6750);
    assert.strictEqual(sfx._voiceWatchdogDelayForTest(10000, 6), 10000);
    assert.strictEqual(sfx._voiceWatchdogDelayForTest(7000, 45), 30000);

    const first = sfx.play("test.lore", {event_id: "event-1"});
    const firstResult = await first.started;
    assert.strictEqual(firstResult.ok, true);
    assert.strictEqual(duckHandles.length, 1);
    assert.strictEqual(duckHandles[0].gain, 0.4);

    const duplicate = await sfx.play("test.lore", {event_id: "event-1"}).started;
    assert.strictEqual(duplicate.ok, false);
    assert.strictEqual(duplicate.reason, "duplicate");

    const quiet = await sfx.play("test.quiet", {event_id: "event-2"}).started;
    assert.strictEqual(quiet.ok, true);
    assert.strictEqual(first.stop(), false);
    assert.strictEqual(duckHandles[0].released, true);

    assert.strictEqual(sfx.stop("lore"), 1);
    assert.strictEqual(sfx.getState().active_voices, 0);

    const gameplay = sfx.play("test.gameplay", {event_id: "event-gameplay"});
    assert.strictEqual((await gameplay.started).ok, true);
    const gameplayDuck = duckHandles[duckHandles.length - 1];
    const critical = sfx.play("test.critical", {event_id: "event-critical"});
    assert.strictEqual((await critical.started).ok, true);
    await new Promise(resolve => setTimeout(resolve, 60));
    assert.strictEqual(gameplayDuck.released, true);
    assert.strictEqual(gameplay.stop(), false);
    assert.strictEqual(sfx.stop("system"), 1);

    sfx.setEnabled(false);
    const disabled = await sfx.play("test.lore", {event_id: "event-3"}).started;
    assert.strictEqual(disabled.reason, "disabled");
    console.log("game_sfx contract ok");
}()).catch(error => {
    console.error(error);
    process.exitCode = 1;
});
