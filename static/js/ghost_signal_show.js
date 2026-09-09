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

    function createController(options) {
        options = options || {};
        const doc = options.document || global.document;
        const fetcher = options.fetch || global.fetch;
        let snapshot = null;
        let offsetMs = 0;
        let timer = 0;

        function hide() {
            if (!doc) return;
            const root = doc.getElementById("ghost-signal-show");
            if (root) root.classList.remove("is-active");
            if (timer) global.clearInterval(timer);
            timer = 0;
        }

        function render() {
            if (!doc || !snapshot || !snapshot.show_active) return hide();
            const root = ensureOverlay(doc);
            const phase = phaseAt(snapshot, Date.now(), offsetMs);
            const copy = PHASE_COPY[phase.code] || [phase.label || "GHOSTSIGNAL", "Global transmission in progress"];
            root.querySelector(".ghost-signal-show__signal").textContent = snapshot.signal_public_id || "GHOSTSIGNAL";
            root.querySelector(".ghost-signal-show__phase").textContent = copy[0];
            root.querySelector(".ghost-signal-show__copy").textContent = copy[1];
            root.querySelector(".ghost-signal-show__versions").textContent =
                `${snapshot.from_system_version || "vN"}  >  ${snapshot.to_system_version || "vNext"}`;
            root.querySelector(".ghost-signal-show__progress span").style.width =
                `${Math.max(0, Math.min(100, Number(phase.overall_percent || 0)))}%`;
            root.querySelector(".ghost-signal-show__time").textContent =
                `T-${String(secondsRemaining(snapshot, Date.now(), offsetMs)).padStart(3, "0")}s`;
            root.classList.add("is-active");
        }

        function apply(next) {
            snapshot = next || {show_active: false};
            offsetMs = serverOffset(snapshot, Date.now());
            render();
            if (!snapshot.show_active && snapshot.last_completed_signal_public_id && global.localStorage) {
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
            if (snapshot.show_active && !timer) {
                timer = global.setInterval(function () {
                    render();
                    if (!secondsRemaining(snapshot, Date.now(), offsetMs)) refresh("deadline");
                }, 1000);
            }
            return snapshot.show_active;
        }

        function refresh() {
            if (typeof fetcher !== "function") return Promise.resolve(false);
            return fetcher("/api/ghostnetwork/show", {credentials: "same-origin", cache: "no-store"})
                .then(response => response.ok ? response.json() : null)
                .then(data => data && data.ok ? apply(data) : false)
                .catch(() => false);
        }

        return {apply, refresh, render, hide, get snapshot() { return snapshot; }};
    }

    const api = {createController, serverOffset, secondsRemaining, phaseAt, PHASE_COPY};
    if (typeof module !== "undefined" && module.exports) module.exports = api;
    global.GhostSignalShow = api;

    if (!global.document || (global.top && global.top !== global)) return;
    const start = function () {
        const controller = createController({document: global.document, fetch: global.fetch && global.fetch.bind(global)});
        global.GhostSignalShowController = controller;
        controller.refresh("boot");
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
