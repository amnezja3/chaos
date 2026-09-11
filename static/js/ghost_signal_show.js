(function (global) {
    "use strict";

    const PHASE_COPY = {
        network_lock: ["NETWORK LOCK", "Closing the old GhostSystem world"],
        machine_synchronization: ["MACHINE SYNCHRONIZATION", "Four machines / twenty nodes"],
        signal_transmission: ["SIGNAL TRANSMISSION", "GhostSignal uplink to 2108"],
        world_consumption: ["WORLD CONSUMPTION / ARCHIVE", "Nodes and territory enter history"],
        results: ["RESULTS / REWARDS", "Final settlement is being committed"],
        ghostsystem_restart: ["GHOSTSYSTEM RESTART", "Booting the prepared vNext world"]
    };

    function serverOffset(snapshot, localNow) {
        const server = Date.parse(snapshot && snapshot.server_now || "");
        return Number.isFinite(server) ? server - Number(localNow || Date.now()) : 0;
    }

    function secondsRemaining(snapshot, nowMs, offsetMs) {
        const end = Date.parse(snapshot && snapshot.show_ends_at || "");
        if (!Number.isFinite(end)) return 0;
        return Math.max(0, Math.ceil((end - (Number(nowMs || Date.now()) + Number(offsetMs || 0))) / 1000));
    }

    function phaseAt(snapshot, nowMs, offsetMs) {
        const start = Date.parse(snapshot && snapshot.show_started_at || "");
        const end = Date.parse(snapshot && snapshot.show_ends_at || "");
        if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
            return snapshot && snapshot.show_phase || {};
        }
        const now = Number(nowMs || Date.now()) + Number(offsetMs || 0);
        const overall = Math.max(0, Math.min(100, (now - start) * 100 / (end - start)));
        const phases = [
            ["network_lock", 8], ["machine_synchronization", 22],
            ["signal_transmission", 42], ["world_consumption", 62],
            ["results", 80], ["ghostsystem_restart", 100]
        ];
        const selected = phases.find(item => overall < item[1]) || phases[phases.length - 1];
        return {code: selected[0], overall_percent: Math.round(overall)};
    }

    function ensureOverlay(doc) {
        let root = doc.getElementById("ghost-signal-show");
        if (root) return root;
        root = doc.createElement("section");
        root.id = "ghost-signal-show";
        root.className = "ghost-signal-show";
        // Clip the oversized perspective grid, matching the shared stylesheet.
        root.style.cssText = "position:fixed;inset:0;z-index:2147483646;background:#05090d;color:#d5fff1;overflow:hidden;place-items:center";
        root.setAttribute("role", "status");
        root.setAttribute("aria-live", "polite");
        root.innerHTML = [
            '<div class="ghost-signal-show__grid"></div>',
            '<div class="ghost-signal-show__panel">',
            '<div class="ghost-signal-show__eyebrow">GHOSTNETWORK // GLOBAL EVENT</div>',
            '<div class="ghost-signal-show__signal"></div>',
            '<h1 class="ghost-signal-show__phase"></h1>',
            '<p class="ghost-signal-show__copy"></p>',
            '<div class="ghost-signal-show__versions"></div>',
            '<div class="ghost-signal-show__progress"><span></span></div>',
            '<div class="ghost-signal-show__time"></div>',
            '</div>'
        ].join("");
        doc.body.appendChild(root);
        return root;
    }

    function sceneAt(snapshot, nowMs, offsetMs) {
        const manifest = snapshot && snapshot.show_manifest;
        if (!manifest || manifest.version !== "ghostsignal-show-manifest-v2"
                || !Array.isArray(manifest.scenes) || !manifest.scenes.length
                || manifest.scenes.length > 64 || manifest.nominal_duration_seconds !== 900) return null;
        const start = Date.parse(snapshot.show_started_at || "");
        const end = Date.parse(snapshot.show_ends_at || "");
        if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) return null;
        let boundary = 0;
        for (const scene of manifest.scenes) {
            if (!scene || typeof scene.id !== "string" || typeof scene.label !== "string"
                    || !Number.isFinite(scene.start) || !Number.isFinite(scene.end)
                    || scene.start !== boundary || scene.end <= scene.start || scene.end > 900) return null;
            boundary = scene.end;
        }
        if (boundary !== 900) return null;
        const now = Number(nowMs === undefined ? Date.now() : nowMs) + Number(offsetMs || 0);
        const elapsed = Math.max(0, Math.min(900, (now - start) * 900 / (end - start)));
        const scene = manifest.scenes.find(item => elapsed < item.end) || manifest.scenes[manifest.scenes.length - 1];
        if (scene.requires_signal_sent && !manifest.signal_confirmed) {
            return {id: "waiting_for_signal_sent", label: "OCZEKIWANIE NA POTWIERDZENIE SYGNAŁU",
                progress: 0, blocked: true};
        }
        return {id: scene.id, label: scene.label,
            progress: Math.max(0, Math.min(1, (elapsed - scene.start) / (scene.end - scene.start))),
            blocked: false};
    }

    function createController(options) {
        options = options || {};
        const doc = options.document || global.document;
        const fetcher = options.fetch || global.fetch;
        let snapshot = null;
        let offsetMs = 0;
        let timer = 0;
        let pollTimer = 0;
        let inFlight = null;
        let cancelRequest = null;
        let started = false;
        let rebooting = false;
        let bootReceipt = null;
        let ackInFlight = false;

        function acknowledgeBoot(profile) {
            if (profile && profile.client_restart && profile.restart_boot_token && profile.signal_registry_available) {
                bootReceipt = {epoch: profile.client_restart.epoch, boot_token: profile.restart_boot_token};
            }
            if (!bootReceipt || ackInFlight || typeof fetcher !== "function") return;
            ackInFlight = true;
            const abort = global.AbortController ? new global.AbortController() : null;
            let expired = false;
            let timeout;
            const deadline = new Promise(resolve => {
                timeout = global.setTimeout(() => {
                    expired = true;
                    if (abort) abort.abort();
                    resolve(null);
                }, 8000);
            });
            const sent = bootReceipt;
            const request = Promise.resolve().then(() => fetcher("/api/ghostnetwork/restart/ack", {
                method: "POST", credentials: "same-origin", headers: {"Content-Type": "application/json"},
                body: JSON.stringify(sent), signal: abort ? abort.signal : undefined
            })).then(response => response.ok ? response.json() : null).catch(() => null);
            Promise.race([request, deadline]).then(data => {
                if (!expired && data && data.ok && data.epoch === sent.epoch && bootReceipt === sent) bootReceipt = null;
                global.clearTimeout(timeout);
                ackInFlight = false;
            });
        }

        function restartIfRequired(next) {
            const restart = next.client_restart;
            const session = global.ChaosSessionGeneration && global.ChaosSessionGeneration.getState();
            if (!restart || !restart.epoch || !session || restart.epoch === (session.ghost_epoch || "") || next.show_active) return false;
            if (rebooting) return true;
            rebooting = true;
            snapshot = Object.assign({}, next, {show_active: true, gameplay_locked: true,
                show_phase: {code: "ghostsystem_restart"}, show_started_at: null, show_ends_at: null,
                signal_public_id: restart.signal_public_id,
                from_system_version: next.last_completed_from_system_version || next.from_system_version,
                to_system_version: restart.to_system_version});
            render();
            if (global.top && global.top !== global && global.top.GhostSignalShowController) {
                global.top.GhostSignalShowController.refresh();
                return true;
            }
            if (typeof global.teardownDesktopForInvalidatedSession === "function") global.teardownDesktopForInvalidatedSession();
            const destination = "/desktop?_session_generation=" + encodeURIComponent(session.query_token || session.generation);
            global.setTimeout(() => global.location.replace(destination), 750);
            return true;
        }

        function locked() { return !!(snapshot && (snapshot.show_active || snapshot.gameplay_locked)); }

        function blockInput(event) {
            if (!locked()) return;
            const root = doc && doc.getElementById("ghost-signal-show");
            if (root && root.contains && root.contains(event.target)) return;
            event.preventDefault();
            event.stopImmediatePropagation();
        }

        function hide() {
            if (!doc) return;
            const root = doc.getElementById("ghost-signal-show");
            if (root) { root.classList.remove("is-active"); root.style.display = "none"; }
            const fallback = doc.getElementById("ghost-signal-show-fallback");
            if (fallback) fallback.remove();
            if (timer) global.clearInterval(timer);
            timer = 0;
        }

        function render() {
            if (!doc || !locked()) return hide();
            try {
            const root = ensureOverlay(doc);
            root.style.display = "grid";
            root.classList.add("is-active");
            const phase = phaseAt(snapshot, Date.now(), offsetMs);
            const copy = PHASE_COPY[phase.code] || [phase.label || "GHOSTSIGNAL", "Global transmission in progress"];
            const scene = sceneAt(snapshot, Date.now(), offsetMs);
            root.setAttribute("data-show-scene", scene ? scene.id : phase.code || "fallback");
            root.querySelector(".ghost-signal-show__signal").textContent = snapshot.signal_public_id || "GHOSTSIGNAL";
            root.querySelector(".ghost-signal-show__phase").textContent = scene ? scene.label : copy[0];
            root.querySelector(".ghost-signal-show__copy").textContent = scene
                ? (scene.blocked ? "Trwa odtwarzanie stanu transmisji." : "Historia zakończenia cyklu GhostNetwork")
                : copy[1];
            root.querySelector(".ghost-signal-show__versions").textContent =
                `${snapshot.from_system_version || "vN"}  >  ${snapshot.to_system_version || "vNext"}`;
            root.querySelector(".ghost-signal-show__progress span").style.width =
                `${Math.max(0, Math.min(100, Number(phase.overall_percent || 0)))}%`;
            root.querySelector(".ghost-signal-show__time").textContent =
                `T-${String(secondsRemaining(snapshot, Date.now(), offsetMs)).padStart(3, "0")}s`;
            root.classList.add("is-active");
            const fallback = doc.getElementById("ghost-signal-show-fallback");
            if (fallback) fallback.remove();
            } catch (error) {
                let fallback = doc.getElementById("ghost-signal-show-fallback");
                if (!fallback) {
                    fallback = doc.createElement("section");
                    fallback.id = "ghost-signal-show-fallback";
                    fallback.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:#05090d;color:#d5fff1;padding:10vh 8vw";
                    fallback.textContent = "GHOSTSIGNAL — transmisja trwa. Trwa odtwarzanie widoku.";
                    fallback.setAttribute("role", "status");
                    doc.body.appendChild(fallback);
                    if (global.console) global.console.warn("[ghostnetwork] show renderer recovery");
                }
            }
        }

        function apply(next) {
            if (!next || typeof next.show_active !== "boolean") return locked();
            if (rebooting) return true;
            if (snapshot) {
                const oldCycle = Number(snapshot.cycle_number || 0), newCycle = Number(next.cycle_number || 0);
                if (newCycle < oldCycle || (newCycle === oldCycle &&
                    Number(next.state_version || 0) < Number(snapshot.state_version || 0))) return locked();
                if (Date.parse(next.server_now || "") < Date.parse(snapshot.server_now || "")) return locked();
            }
            if (restartIfRequired(next)) return true;
            snapshot = next;
            offsetMs = serverOffset(snapshot, Date.now());
            render();
            try {
            if (!locked() && snapshot.last_completed_signal_public_id && global.localStorage) {
                const receipt = `chaos:${snapshot.last_completed_signal_public_id}:show-seen`;
                if (!global.localStorage.getItem(receipt)) {
                    global.localStorage.setItem(receipt, "1");
                    const toastHost = doc && doc.getElementById("system-toast-container");
                    if (toastHost) {
                        const toast = doc.createElement("div");
                        toast.className = "system-toast";
                        toast.textContent = `${snapshot.last_completed_signal_public_id} // GhostSystem ${snapshot.last_completed_to_system_version || "vNext"} online`;
                        toastHost.appendChild(toast);
                        global.setTimeout(() => toast.remove(), 9000);
                    }
                }
            }
            } catch (error) { /* Optional toast receipts cannot interrupt the show. */ }
            if (locked() && !timer) {
                timer = global.setInterval(function () {
                    render();
                }, 1000);
            }
            return locked();
        }

        function refresh() {
            acknowledgeBoot();
            if (inFlight) return inFlight;
            if (typeof fetcher !== "function") return Promise.resolve(false);
            const abort = global.AbortController ? new global.AbortController() : null;
            let expired = false;
            let timeout;
            const timedOut = new Promise(resolve => {
                cancelRequest = function () {
                    expired = true;
                    if (abort) abort.abort();
                    resolve(false);
                };
                timeout = global.setTimeout(cancelRequest, 8000);
            });
            const request = Promise.resolve().then(() => fetcher("/api/ghostnetwork/show", {
                credentials: "same-origin", cache: "no-store", signal: abort ? abort.signal : undefined
            }))
                .then(response => response.ok ? response.json() : null)
                .then(data => !expired && data && data.ok ? apply(data) : false)
                .catch(() => false);
            inFlight = Promise.race([request, timedOut]).then(result => {
                global.clearTimeout(timeout);
                inFlight = null;
                cancelRequest = null;
                return result;
            });
            return inFlight;
        }

        function wake() { refresh("wake"); }
        function start() {
            if (started) return;
            started = true;
            refresh("boot");
            pollTimer = global.setInterval(() => refresh("poll"), 5000);
            if (doc && doc.addEventListener) {
                doc.addEventListener("visibilitychange", wake);
                ["keydown", "keypress", "keyup", "click", "pointerdown", "contextmenu", "submit"].forEach(
                    type => doc.addEventListener(type, blockInput, true));
            }
            if (global.addEventListener) ["online", "pageshow", "focus"].forEach(type => global.addEventListener(type, wake));
        }
        function stop() {
            started = false;
            if (cancelRequest) cancelRequest();
            global.clearInterval(pollTimer);
            global.clearInterval(timer);
            pollTimer = timer = 0;
            if (doc && doc.removeEventListener) {
                doc.removeEventListener("visibilitychange", wake);
                ["keydown", "keypress", "keyup", "click", "pointerdown", "contextmenu", "submit"].forEach(
                    type => doc.removeEventListener(type, blockInput, true));
            }
            if (global.removeEventListener) ["online", "pageshow", "focus"].forEach(type => global.removeEventListener(type, wake));
        }
        return {apply, refresh, render, start, stop, acknowledgeBoot, get snapshot() { return snapshot; }};
    }

    const api = {createController, serverOffset, secondsRemaining, phaseAt, sceneAt, PHASE_COPY};
    if (typeof module !== "undefined" && module.exports) module.exports = api;
    global.GhostSignalShow = api;

    if (!global.document) return;
    const start = function () {
        const controller = createController({document: global.document, fetch: global.fetch && global.fetch.bind(global)});
        global.GhostSignalShowController = controller;
        controller.start();
        const delta = global.GhostNetworkDeltaClient;
        if (delta && typeof delta.registerAdapter === "function") {
            delta.registerAdapter("ghost-signal-show", {
                accepts(event) {
                    return ["ghost.signal_sent", "ghost.stabilization_started", "ghost.signal_show_started",
                        "ghost.cycle_activated"].includes(String(event && event.type || ""));
                },
                apply() { controller.refresh("delta"); return true; },
                recover() { return controller.refresh("recovery"); }
            });
        }
    };
    if (global.document.readyState === "loading") global.document.addEventListener("DOMContentLoaded", start);
    else start();
})(typeof window !== "undefined" ? window : globalThis);
