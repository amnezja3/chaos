"use strict";

(function initGameSfxModule(global) {
    const DEFAULT_MANIFEST_URL = "/static/audio/sfx/manifest.v1.json?v=sfx-capture-3";
    const STORAGE_ENABLED = "chaos_sfx_enabled";
    const STORAGE_VOLUME = "chaos_sfx_volume";
    const DEFAULT_BUS_LIMITS = Object.freeze({
        lore: 1,
        gameplay: 2,
        message: 2,
        system: 1,
        ui: 3
    });
    const ALLOWED_BUSES = new Set(Object.keys(DEFAULT_BUS_LIMITS));
    const RECENT_TTL_MS = 5 * 60 * 1000;
    const NEGATIVE_CACHE_MS = 30 * 1000;

    const state = {
        initialized: false,
        manifestUrl: DEFAULT_MANIFEST_URL,
        manifest: null,
        manifestPromise: null,
        enabled: readStoredEnabled(),
        volume: readStoredVolume(),
        unlocked: false,
        unlockBound: false,
        audioContext: null,
        voiceSequence: 0,
        voices: new Map(),
        recentEvents: new Map(),
        cooldowns: new Map(),
        negativeAssets: new Map(),
        preloaded: new Set(),
        counters: {
            loaded: 0,
            played: 0,
            blocked: 0,
            failed: 0
        },
        debug: false
    };

    function now() {
        return Date.now();
    }

    function clamp(value, minimum, maximum) {
        const numeric = Number(value);
        if (!Number.isFinite(numeric)) return minimum;
        return Math.max(minimum, Math.min(maximum, numeric));
    }

    function readStorage(key) {
        try {
            return global.localStorage ? global.localStorage.getItem(key) : null;
        } catch (error) {
            return null;
        }
    }

    function writeStorage(key, value) {
        try {
            if (global.localStorage) global.localStorage.setItem(key, value);
        } catch (error) {
            // Local settings are optional and must never block audio or boot.
        }
    }

    function readStoredEnabled() {
        return readStorage(STORAGE_ENABLED) !== "0";
    }

    function readStoredVolume() {
        const stored = readStorage(STORAGE_VOLUME);
        return stored === null ? 0.8 : clamp(stored, 0, 1);
    }

    function debugLog(kind, details) {
        if (!state.debug || !global.console || typeof global.console.debug !== "function") return;
        global.console.debug(`[GAME_SFX] ${kind}`, details || {});
    }

    function skipResult(eventKey, reason) {
        state.counters.blocked += 1;
        const result = { ok: false, event_key: String(eventKey || ""), voice_id: null, reason };
        debugLog("skip", result);
        return result;
    }

    function failResult(eventKey, reason) {
        state.counters.failed += 1;
        const result = { ok: false, event_key: String(eventKey || ""), voice_id: null, reason };
        debugLog("fail", result);
        return result;
    }

    function isSafeRelativeAudioPath(value) {
        const path = String(value || "").trim();
        return Boolean(path)
            && !path.startsWith("/")
            && !path.includes("..")
            && !path.includes("\\")
            && /^[a-zA-Z0-9/_ .-]+\.mp3$/i.test(path);
    }

    function normalizeManifest(payload) {
        if (!payload || Number(payload.schema) !== 1) throw new Error("unsupported_schema");
        const basePath = String(payload.base_path || "").replace(/\/+$/, "");
        if (!basePath.startsWith("/static/audio/sfx")) throw new Error("invalid_base_path");
        const rawEvents = payload.events && typeof payload.events === "object" ? payload.events : {};
        const events = {};
        Object.keys(rawEvents).forEach(eventKey => {
            const raw = rawEvents[eventKey];
            if (!raw || !isSafeRelativeAudioPath(raw.file)) return;
            const bus = ALLOWED_BUSES.has(String(raw.bus || "")) ? String(raw.bus) : "ui";
            events[eventKey] = Object.freeze({
                file: String(raw.file).trim(),
                url: `${basePath}/${String(raw.file).trim().split("/").map(encodeURIComponent).join("/")}`,
                bus,
                priority: Math.round(clamp(raw.priority, 0, 100)),
                volume: clamp(raw.volume === undefined ? 1 : raw.volume, 0, 1),
                max_duration_ms: Math.round(clamp(raw.max_duration_ms || 10000, 100, 30000)),
                cooldown_ms: Math.round(clamp(raw.cooldown_ms || 0, 0, 60000)),
                duck_radio: clamp(raw.duck_radio === undefined ? 1 : raw.duck_radio, 0, 1)
            });
        });
        const buses = {};
        Object.keys(DEFAULT_BUS_LIMITS).forEach(bus => {
            const configured = payload.buses && payload.buses[bus];
            const requestedLimit = configured && configured.max_voices !== undefined
                ? configured.max_voices
                : DEFAULT_BUS_LIMITS[bus];
            buses[bus] = Object.freeze({
                max_voices: Math.round(clamp(
                    requestedLimit,
                    1,
                    DEFAULT_BUS_LIMITS[bus]
                ))
            });
        });
        return Object.freeze({ schema: 1, base_path: basePath, events: Object.freeze(events), buses: Object.freeze(buses) });
    }

    function loadManifest() {
        if (state.manifest) return Promise.resolve(state.manifest);
        if (state.manifestPromise) return state.manifestPromise;
        if (typeof global.fetch !== "function") return Promise.reject(new Error("fetch_unavailable"));
        state.manifestPromise = global.fetch(state.manifestUrl, { cache: "force-cache" })
            .then(response => {
                if (!response || !response.ok) throw new Error(`manifest_http_${response ? response.status : 0}`);
                return response.json();
            })
            .then(normalizeManifest)
            .then(manifest => {
                state.manifest = manifest;
                return manifest;
            })
            .catch(error => {
                state.manifestPromise = null;
                throw error;
            });
        return state.manifestPromise;
    }

    function bindUnlock() {
        if (state.unlockBound || !global.document || typeof global.document.addEventListener !== "function") return;
        const unlockFromGesture = () => {
            GameSfx.unlock();
            global.document.removeEventListener("pointerdown", unlockFromGesture);
            global.document.removeEventListener("keydown", unlockFromGesture);
            state.unlockBound = false;
        };
        global.document.addEventListener("pointerdown", unlockFromGesture, { passive: true });
        global.document.addEventListener("keydown", unlockFromGesture);
        state.unlockBound = true;
    }

    function cleanupRecent() {
        const cutoff = now() - RECENT_TTL_MS;
        state.recentEvents.forEach((timestamp, key) => {
            if (timestamp < cutoff) state.recentEvents.delete(key);
        });
    }

    function activeVoicesForBus(bus) {
        const result = [];
        state.voices.forEach(voice => {
            if (voice.bus === bus && !voice.stopped) result.push(voice);
        });
        return result;
    }

    function releaseVoice(voice, fadeMs) {
        if (!voice || voice.stopped) return false;
        voice.stopped = true;
        if (voice.timeoutId) global.clearTimeout(voice.timeoutId);
        const finish = () => {
            try {
                if (voice.audio) {
                    voice.audio.pause();
                    voice.audio.removeAttribute("src");
                }
            } catch (error) {
                // Cleanup remains best effort.
            }
            if (voice.duckHandle && typeof voice.duckHandle.release === "function") {
                voice.duckHandle.release();
            }
            state.voices.delete(voice.id);
        };
        const delay = Math.round(clamp(fadeMs || 0, 0, 500));
        if (delay > 0) global.setTimeout(finish, delay); else finish();
        return true;
    }

    function chooseVoiceSlot(entry) {
        const manifestBus = state.manifest.buses[entry.bus];
        const limit = manifestBus ? manifestBus.max_voices : DEFAULT_BUS_LIMITS[entry.bus];
        const active = activeVoicesForBus(entry.bus);
        if (active.length < limit) return { ok: true };
        active.sort((left, right) => left.priority - right.priority || left.startedAt - right.startedAt);
        const weakest = active[0];
        // Lore is a single replaceable channel: a fresh Secret Path show
        // replaces the previous scene even at the same priority.
        if (entry.bus === "lore" && weakest) {
            releaseVoice(weakest, 0);
            return { ok: true };
        }
        if (!weakest || entry.priority <= weakest.priority) return { ok: false };
        releaseVoice(weakest, 40);
        return { ok: true };
    }

    function createHandle(eventKey) {
        const pending = { voice: null };
        const handle = {
            event_key: String(eventKey || ""),
            voice_id: null,
            started: null,
            stop(options) {
                return pending.voice ? releaseVoice(pending.voice, options && options.fade_ms) : false;
            }
        };
        return { handle, pending };
    }

    function startVoice(eventKey, context, handleState) {
        if (!state.enabled) return Promise.resolve(skipResult(eventKey, "disabled"));
        if (state.volume <= 0) return Promise.resolve(skipResult(eventKey, "muted"));
        return loadManifest().then(manifest => {
            const entry = manifest.events[eventKey];
            if (!entry) return skipResult(eventKey, "unknown_event");
            cleanupRecent();
            const eventId = String(context.event_id || "").trim();
            if (eventId && state.recentEvents.has(eventId)) return skipResult(eventKey, "duplicate");
            const cooldownUntil = state.cooldowns.get(eventKey) || 0;
            if (cooldownUntil > now()) return skipResult(eventKey, "cooldown");
            const assetBlockedUntil = state.negativeAssets.get(entry.url) || 0;
            if (assetBlockedUntil > now()) return skipResult(eventKey, "missing_asset");
            if (!chooseVoiceSlot(entry).ok) return skipResult(eventKey, "voice_limit");
            if (typeof global.Audio !== "function") return failResult(eventKey, "play_failed");

            state.voiceSequence += 1;
            const voice = {
                id: `sfx-${state.voiceSequence}`,
                eventKey,
                eventId,
                bus: entry.bus,
                priority: entry.priority,
                startedAt: now(),
                stopped: false,
                audio: new global.Audio(entry.url),
                duckHandle: null,
                timeoutId: null
            };
            voice.audio.preload = "auto";
            voice.audio.volume = clamp(state.volume * entry.volume, 0, 1);
            handleState.pending.voice = voice;
            handleState.handle.voice_id = voice.id;
            state.voices.set(voice.id, voice);
            if (entry.duck_radio < 1 && global.GhostRadio && typeof global.GhostRadio.requestDuck === "function") {
                voice.duckHandle = global.GhostRadio.requestDuck(entry.duck_radio, voice.id);
            }
            const onEnded = () => releaseVoice(voice, 0);
            if (typeof voice.audio.addEventListener === "function") {
                voice.audio.addEventListener("ended", onEnded, { once: true });
                voice.audio.addEventListener("error", () => {
                    state.negativeAssets.set(entry.url, now() + NEGATIVE_CACHE_MS);
                    releaseVoice(voice, 0);
                }, { once: true });
            }
            voice.timeoutId = global.setTimeout(onEnded, entry.max_duration_ms);
            return Promise.resolve(voice.audio.play()).then(() => {
                if (eventId) state.recentEvents.set(eventId, now());
                state.cooldowns.set(eventKey, now() + entry.cooldown_ms);
                state.counters.played += 1;
                const result = { ok: true, event_key: eventKey, voice_id: voice.id, reason: null };
                debugLog("play", result);
                return result;
            }).catch(error => {
                releaseVoice(voice, 0);
                const reason = error && error.name === "NotAllowedError" ? "autoplay_blocked" : "play_failed";
                return failResult(eventKey, reason);
            });
        }).catch(() => failResult(eventKey, "missing_asset"));
    }

    const GameSfx = {
        init(options) {
            const settings = options && typeof options === "object" ? options : {};
            if (settings.manifest_url) state.manifestUrl = String(settings.manifest_url);
            if (settings.debug === true) state.debug = true;
            state.initialized = true;
            bindUnlock();
            const manifestPromise = loadManifest();
            manifestPromise.catch(() => {});
            return manifestPromise;
        },

        unlock() {
            if (state.unlocked) return Promise.resolve(true);
            const AudioContextClass = global.AudioContext || global.webkitAudioContext;
            if (!AudioContextClass) {
                state.unlocked = true;
                return Promise.resolve(true);
            }
            try {
                if (!state.audioContext) state.audioContext = new AudioContextClass();
                const resumed = state.audioContext.state === "suspended" && typeof state.audioContext.resume === "function"
                    ? state.audioContext.resume()
                    : Promise.resolve();
                return Promise.resolve(resumed).then(() => {
                    state.unlocked = true;
                    return true;
                }).catch(() => false);
            } catch (error) {
                return Promise.resolve(false);
            }
        },

        preload(groupOrKeys) {
            if (!state.unlocked) return Promise.resolve([]);
            return loadManifest().then(manifest => {
                const requested = Array.isArray(groupOrKeys) ? groupOrKeys.map(String) : [String(groupOrKeys || "")];
                const keys = Object.keys(manifest.events).filter(key => requested.some(value => key === value || key.startsWith(`${value}.`)));
                const loaded = [];
                keys.forEach(key => {
                    const entry = manifest.events[key];
                    if (state.preloaded.has(entry.url) || typeof global.Audio !== "function") return;
                    const audio = new global.Audio(entry.url);
                    audio.preload = "auto";
                    if (typeof audio.load === "function") audio.load();
                    state.preloaded.add(entry.url);
                    state.counters.loaded += 1;
                    loaded.push(key);
                });
                return loaded;
            }).catch(() => []);
        },

        play(eventKey, context) {
            if (!state.initialized) this.init().catch(() => {});
            const handleState = createHandle(eventKey);
            handleState.handle.started = startVoice(String(eventKey || ""), context || {}, handleState);
            return handleState.handle;
        },

        stop(handleOrChannel, options) {
            if (handleOrChannel && typeof handleOrChannel.stop === "function") return handleOrChannel.stop(options || {});
            const selector = String(handleOrChannel || "");
            let stopped = 0;
            Array.from(state.voices.values()).forEach(voice => {
                if (voice.id === selector || voice.bus === selector) {
                    if (releaseVoice(voice, options && options.fade_ms)) stopped += 1;
                }
            });
            return stopped;
        },

        setEnabled(enabled) {
            state.enabled = Boolean(enabled);
            writeStorage(STORAGE_ENABLED, state.enabled ? "1" : "0");
            if (!state.enabled) {
                Object.keys(DEFAULT_BUS_LIMITS).forEach(bus => this.stop(bus));
            }
            return state.enabled;
        },

        setVolume(value) {
            state.volume = clamp(value, 0, 1);
            writeStorage(STORAGE_VOLUME, String(state.volume));
            state.voices.forEach(voice => {
                const entry = state.manifest && state.manifest.events[voice.eventKey];
                if (entry && voice.audio) voice.audio.volume = clamp(state.volume * entry.volume, 0, 1);
            });
            return state.volume;
        },

        getState() {
            return {
                initialized: state.initialized,
                manifest_loaded: Boolean(state.manifest),
                enabled: state.enabled,
                volume: state.volume,
                unlocked: state.unlocked,
                active_voices: state.voices.size,
                counters: Object.assign({}, state.counters)
            };
        },

        _normalizeManifestForTest: normalizeManifest
    };

    global.GameSfx = Object.freeze(GameSfx);
    if (global.document && global.document.readyState === "loading") {
        global.document.addEventListener("DOMContentLoaded", () => GameSfx.init().catch(() => {}), { once: true });
    } else {
        GameSfx.init().catch(() => {});
    }
}(window));
