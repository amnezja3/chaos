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
            '<div class="ghost-signal-show__stage" aria-hidden="true"></div>',
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
            elapsed,
            progress: Math.max(0, Math.min(1, (elapsed - scene.start) / (scene.end - scene.start))),
            blocked: false};
    }

    function sceneLayout(manifest, scene) {
        const catalog = manifest && manifest.catalog || {};
        const parts = Array.isArray(catalog.parts) ? catalog.parts.slice(0, 20) : [];
        const machines = Array.isArray(catalog.machines) ? catalog.machines.slice(0, 4) : [];
        const history = manifest.cycle_history || {};
        const historical = history.available && Array.isArray(history.parts) ? history.parts : [];
        const byCode = new Map(historical.map(p => [p.part_code, p]));
        const completeDates = parts.length === 20 && parts.every(p => (byCode.get(p.part_code) || {}).discovered_at);
        const ordered = completeDates ? parts.slice().sort((a, b) =>
            String(byCode.get(a.part_code).discovered_at).localeCompare(String(byCode.get(b.part_code).discovered_at))
                || parts.indexOf(a) - parts.indexOf(b)) : parts.slice();
        const elapsed = scene.elapsed || 0;
        const ring = Array.isArray(history.ring_codes) ? history.ring_codes : [];
        const visible = elapsed < 30 ? 0 : elapsed < 60 ? Math.ceil((elapsed - 30) * 20 / 30) : 20;
        const group = elapsed >= 160 && elapsed < 300;
        const round = elapsed >= 320;
        const nodes = ordered.map((part, i) => {
            const machineIndex = Math.max(0, machines.findIndex(m => m.code === part.machine_code));
            const machine = machines[machineIndex] || {};
            const slot = Math.max(0, (machine.part_codes || []).indexOf(part.part_code));
            const ringIndex = ring.indexOf(part.part_code);
            const angle = ((ringIndex < 0 ? i : ringIndex) / 20) * Math.PI * 2 - Math.PI / 2;
            let x = 100 + ((i * 173) % 800), y = 80 + ((i * 107) % 390);
            if (group) {
                x = 260 + (machineIndex % 2) * 480 + Math.cos(slot * Math.PI * 2 / 5) * 100;
                y = 175 + Math.floor(machineIndex / 2) * 250 + Math.sin(slot * Math.PI * 2 / 5) * 85;
            } else if (round) { x = 500 + Math.cos(angle) * 370; y = 300 + Math.sin(angle) * 220; }
            return {part, history: byCode.get(part.part_code) || {}, x, y, visible: i < visible,
                highlighted: elapsed < 180 || elapsed >= 300 || machineIndex === Math.floor((elapsed - 180) / 30)};
        });
        const codes = new Set(parts.map(p => p.part_code));
        const validRing = ring.length === 20 && new Set(ring).size === 20 && ring.every(c => codes.has(c));
        const edges = validRing && elapsed >= 90 ? ring.map((code, i) => [code, ring[(i + 1) % 20]]) : [];
        return {nodes, edges, machines};
    }

    function clearMontage(stage) {
        if (!stage) return;
        const video = stage._video;
        stage._video = null;
        if (video) {
            video.onloadedmetadata = null;
            video.onerror = null;
            video.pause();
            video.removeAttribute("src");
            video.load();
        }
        if (stage.replaceChildren) stage.replaceChildren();
        stage._showKey = null;
    }

    function syncVideo(stage, scene) {
        const video = stage._video;
        if (!video) return;
        video._showTarget = scene.progress * video._showDuration;
        if (video.readyState >= 1 && Number.isFinite(video.duration)) {
            const target = Math.max(0, Math.min(video.duration - 0.05, video._showTarget));
            if (Math.abs(video.currentTime - target) > 0.75) video.currentTime = target;
        }
        if (video.readyState >= 2 && video.paused && !video.ended && !video._showPlayPending) {
            video._showPlayPending = true;
            const playing = video.play();
            if (playing && playing.then) playing.then(() => { video._showPlayPending = false; }, () => {
                video._showPlayPending = false;
                if (stage._video === video && video.onerror) video.onerror();
            });
            else video._showPlayPending = false;
        }
    }

    function renderMontage(doc, root, snapshot, scene) {
        const stage = root.querySelector(".ghost-signal-show__stage");
        if (!stage || !scene || scene.blocked || scene.elapsed >= 480) {
            clearMontage(stage);
            root.classList.remove("has-montage");
            return;
        }
        const manifest = snapshot.show_manifest;
        const history = manifest.cycle_history || {};
        const key = [snapshot.signal_public_id, scene.id, !!manifest.signal_confirmed,
            scene.id === "parts_enter" ? Math.ceil(scene.progress * 20)
                : scene.id === "terminal_2108" ? Math.floor(scene.progress * 100) : ""].join(":");
        root.classList.add("has-montage");
        stage.style.setProperty("--scene-progress", scene.progress);
        root.style.background = scene.id === "takeover"
            ? "rgba(5,9,13," + (0.15 + scene.progress * 0.8) + ")" : "#05090d";
        if (stage._showKey === key) { syncVideo(stage, scene); return; }
        clearMontage(stage);
        const element = (tag, className, text) => {
            const node = doc.createElement(tag); node.className = className;
            if (text !== undefined) node.textContent = text;
            return node;
        };
        const addImage = (parent, url, className, name) => {
            if (!/^\/static\/images\/ghostnetwork\/[a-z0-9_./-]+\.png$/.test(url || "") || url.includes("..")) return;
            const img = element("img", className);
            img.alt = name || ""; img.decoding = "async";
            img.onerror = () => { img.remove(); parent.appendChild(element("span", "ghost-show-asset-fallback", name)); };
            img.src = url; parent.appendChild(img);
        };
        const layout = sceneLayout(manifest, scene);
        const heroIndex = /^machine_hero_[1-4]$/.test(scene.id) ? Number(scene.id.slice(-1)) - 1 : -1;
        if (heroIndex >= 0) {
            const machine = layout.machines[heroIndex];
            if (!machine) return;
            const asset = (manifest.assets || []).find(a => a.id === "machine_" + machine.code);
            const hero = element("div", "ghost-show-hero");
            if (asset && asset.available) addImage(hero, asset.src, "ghost-show-hero__image", machine.name);
            const info = element("div", "ghost-show-hero__info");
            info.appendChild(element("p", "ghost-show-kicker", "GHOST NETWORK / " + machine.clan_code));
            info.appendChild(element("h2", "", machine.name));
            info.appendChild(element("p", "", "PARTS: " + (machine.part_codes || []).join(" · ")));
            const professions = (manifest.catalog.professions || []).filter(p => p.machine_code === machine.code);
            info.appendChild(element("p", "", professions.map(p => p.name).join(" / ")));
            const abilityCodes = new Set(layout.nodes.filter(n => n.part.machine_code === machine.code).map(n => n.part.ability_code));
            info.appendChild(element("p", "ghost-show-powers", (manifest.catalog.abilities || []).filter(a => abilityCodes.has(a.ability_code)).map(a => a.name).join(" / ")));
            hero.appendChild(info); stage.appendChild(hero);
        } else if (scene.elapsed >= 420) {
            const frame = element("div", "ghost-show-transmission");
            frame.appendChild(element("p", "ghost-show-kicker", "ARCHIWALNY ZAPIS TRANSMISJI"));
            if (scene.id === "transmission_video") {
                const field = element("div", "ghost-show-video-field");
                field.setAttribute("inert", "");
                frame.appendChild(field);
                const fallback = element("div", "ghost-show-video-fallback", "GHOSTSIGNAL // TRANSMISSION RECORD");
                field.appendChild(fallback);
                const asset = (manifest.assets || []).find(a => a.id === "ghostsignal_transmission_video");
                if (asset && asset.available && asset.src === "/static/video/ghostsignal_transmission_video.mp4"
                        && Number.isFinite(asset.duration_seconds) && asset.duration_seconds > 0) {
                    const video = element("video", "ghost-show-video");
                    stage._video = video;
                    video._showDuration = asset.duration_seconds;
                    video.muted = true; video.defaultMuted = true;
                    video.playsInline = true; video.preload = "auto";
                    video.controls = false; video.tabIndex = -1;
                    video.disablePictureInPicture = true;
                    video.disableRemotePlayback = true;
                    video.setAttribute("controlslist", "nodownload nofullscreen noremoteplayback noplaybackrate");
                    video.setAttribute("disablepictureinpicture", "");
                    video.setAttribute("disableremoteplayback", "");
                    video.setAttribute("tabindex", "-1");
                    video.setAttribute("aria-hidden", "true");
                    video.oncontextmenu = event => { event.preventDefault(); return false; };
                    video.setAttribute("playsinline", "");
                    video.setAttribute("muted", "");
                    const failed = () => {
                        if (stage._video !== video) return;
                        stage._video = null;
                        video.onloadedmetadata = null; video.onerror = null;
                        video.pause(); video.removeAttribute("src"); video.load(); video.remove();
                        fallback.style.display = "";
                    };
                    video.onerror = failed;
                    video.onloadedmetadata = () => {
                        if (stage._video !== video) return;
                        syncVideo(stage, {progress: video._showTarget / video._showDuration});
                        const playing = video.play();
                        if (playing && playing.catch) playing.catch(failed);
                        fallback.style.display = "none";
                    };
                    syncVideo(stage, scene);
                    video.src = asset.src;
                    field.appendChild(video);
                }
            } else if (scene.id === "terminal_2108") {
                const text = ["GHOSTSIGNAL // " + snapshot.signal_public_id,
                    "TRANSMISSION UTC // " + (manifest.signal_sent_at || "—"),
                    "TEMPORAL CHANNEL // 2108", "DESTINATION // " + (history.future_2108_timestamp || "—")].join("\n");
                // Seek directly to the current text length; no per-character timers.
                frame.appendChild(element("pre", "ghost-show-terminal", text.slice(0, Math.ceil(text.length * scene.progress))));
            } else if (scene.id === "signal_confirmation") {
                frame.appendChild(element("h2", "", "GHOSTSIGNAL WYSŁANY"));
                frame.appendChild(element("p", "", manifest.signal_sent_at || ""));
                if (history.future_2108_timestamp) frame.appendChild(element("p", "ghost-show-future", history.future_2108_timestamp));
            } else { frame.appendChild(element("div", "ghost-show-signal-point", "")); }
            stage.appendChild(frame);
        } else {
            const board = element("div", "ghost-show-board");
            const svg = doc.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("viewBox", "0 0 1000 600"); svg.setAttribute("preserveAspectRatio", "none");
            svg.classList.add("ghost-show-links");
            const indexed = new Map(layout.nodes.map(n => [n.part.part_code, n]));
            // Public frozen node positions; never load the changing gameplay map.
            for (const n of layout.nodes) {
                if (!Number.isFinite(n.history.latitude) || !Number.isFinite(n.history.longitude)) continue;
                const marker = doc.createElementNS("http://www.w3.org/2000/svg", "circle");
                marker.setAttribute("cx", (n.history.longitude + 180) * 1000 / 360);
                marker.setAttribute("cy", (90 - n.history.latitude) * 600 / 180);
                marker.setAttribute("r", "4"); marker.classList.add("ghost-show-map-node");
                svg.appendChild(marker);
            }
            for (const [a, b] of layout.edges) {
                const left = indexed.get(a), right = indexed.get(b);
                const line = doc.createElementNS("http://www.w3.org/2000/svg", "line");
                for (const [attr, value] of Object.entries({x1: left.x, y1: left.y, x2: right.x, y2: right.y})) line.setAttribute(attr, value);
                svg.appendChild(line);
            }
            board.appendChild(svg);
            for (const node of layout.nodes.filter(n => n.visible)) {
                const card = element("div", "ghost-show-part" + (node.highlighted ? " is-highlighted" : ""));
                card.style.left = node.x / 10 + "%"; card.style.top = node.y / 6 + "%";
                addImage(card, "/static/images/ghostnetwork/parts/" + node.part.part_code.toLowerCase() + "_" + node.part.icon_key + ".png", "", node.part.name);
                card.appendChild(element("span", "", node.part.part_code + " / " + node.part.name));
                if (scene.id === "part_states") {
                    const states = [];
                    if (node.history.discovered_at) states.push("DISCOVERED");
                    if (node.history.activated_at) states.push("ACTIVE");
                    if (states.length) card.appendChild(element("small", "", states.join(" → ")));
                }
                board.appendChild(card);
            }
            stage.appendChild(board);
            if (scene.elapsed >= 120) {
                const logs = element("div", "ghost-show-history");
                const lines = layout.nodes.flatMap(n => [
                    n.history.discovered_at ? n.part.part_code + " / DISCOVERED / " + n.history.discovered_at : "",
                    n.history.activated_at ? n.part.part_code + " / ACTIVE / " + n.history.activated_at : ""
                ].filter(Boolean)).slice(-8);
                logs.textContent = lines.join("\n"); stage.appendChild(logs);
            }
        }
        stage._showKey = key;
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
            if (root) {
                root.classList.remove("is-active"); root.style.display = "none";
                try {
                    const stage = root.querySelector(".ghost-signal-show__stage");
                    clearMontage(stage);
                } catch (error) { /* Cleanup must survive a broken renderer. */ }
            }
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
            renderMontage(doc, root, snapshot, scene);
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
            try {
                const root = doc && doc.getElementById("ghost-signal-show");
                if (root) clearMontage(root.querySelector(".ghost-signal-show__stage"));
            } catch (_) { /* Keep shutdown safe if the renderer failed. */ }
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

    const api = {createController, serverOffset, secondsRemaining, phaseAt, sceneAt, sceneLayout, PHASE_COPY};
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
