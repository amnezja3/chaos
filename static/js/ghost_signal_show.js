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
            '<div class="ghost-signal-show__stage" aria-live="off"></div>',
            '<div class="ghost-signal-show__panel">',
            '<div class="ghost-signal-show__eyebrow">GHOSTNETWORK // GLOBAL EVENT</div>',
            '<div class="ghost-signal-show__signal"></div>',
            '<h1 class="ghost-signal-show__phase"></h1>',
            '<p class="ghost-signal-show__copy"></p>',
            '<div class="ghost-signal-show__versions"></div>',
            '<div class="ghost-signal-show__progress"><span></span></div>',
            '<div class="ghost-signal-show__time"></div>',
            '<button type="button" class="ghost-signal-show__sound">Dźwięk</button>',
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

    // Approved v6 composition; identity is independent of reveal order.
    const PART_POSES = {
        V1: {"depth":1,"values":[8,61,-3,52,1.27,-13]},
        S5: {"depth":4,"values":[84,90,90,89,1.03,17]},
        E4: {"depth":2,"values":[80,9,86,10,0.87,11]},
        P3: {"depth":3,"values":[32,8,32,5,1.14,-8]},
        V2: {"depth":1,"values":[56,53,64,66,1.08,18]},
        E1: {"depth":2,"values":[17,27,18,29,0.92,-14]},
        S4: {"depth":4,"values":[48,70,49,64,0.92,-12]},
        P5: {"depth":3,"values":[91,52,91,56,1.04,-19]},
        V3: {"depth":1,"values":[30,85,24,86,1.15,-21]},
        S2: {"depth":4,"values":[65,10,73,7,0.89,-15]},
        E5: {"depth":2,"values":[68,86,62,91,1.12,24]},
        P1: {"depth":3,"values":[8,11,11,12,1.06,-17]},
        V4: {"depth":1,"values":[104,73,105,81,1.34,14]},
        E3: {"depth":2,"values":[52,17,51,17,1.02,-22]},
        S1: {"depth":4,"values":[46,6,53,5,1.1,9]},
        P4: {"depth":3,"values":[10,82,12,73,0.98,26]},
        V5: {"depth":1,"values":[88,29,86,35,1.03,-9]},
        S3: {"depth":4,"values":[32,29,33,27,1.07,22]},
        E2: {"depth":2,"values":[38,44,44,49,1.08,16]},
        P2: {"depth":3,"values":[69,38,70,29,0.89,21]}
    };

    function sceneLayout(manifest, scene) {
        const catalog = manifest && manifest.catalog || {};
        const parts = Array.isArray(catalog.parts) ? catalog.parts.slice(0, 20) : [];
        const machines = Array.isArray(catalog.machines) ? catalog.machines.slice(0, 4) : [];
        const history = manifest.cycle_history || {};
        const historical = Array.isArray(history.parts) ? history.parts.slice(0, 20) : [];
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
            const pose = PART_POSES[part.part_code];
            let x = pose ? pose.values[0] * 10 : 100 + ((i * 173) % 800);
            let y = pose ? pose.values[1] * 6 : 80 + ((i * 107) % 390);
            if (group) {
                x = 260 + (machineIndex % 2) * 480 + Math.cos(slot * Math.PI * 2 / 5) * 100;
                y = 175 + Math.floor(machineIndex / 2) * 250 + Math.sin(slot * Math.PI * 2 / 5) * 85;
            } else if (round) { x = 500 + Math.cos(angle) * 370; y = 300 + Math.sin(angle) * 220; }
            return {part, pose, history: byCode.get(part.part_code) || {}, x, y, visible: i < visible,
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
        stage._partsRows = null;
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
                if (stage._video !== video) return;
                video._audioBlocked = true; video.muted = true;
                const silent = video.play();
                if (silent && silent.catch) silent.catch(() => {
                    if (stage._video === video && video.onerror) video.onerror();
                });
            });
            else video._showPlayPending = false;
        }
    }

    const INTERFACE_SCENES = {
        takeover: ["CHAOS", "INTERFACE\nLOST_", "SYSTEM PRZEJĘTY PRZEZ GHOST NETWORK", 0],
        network_layer: ["GHOST", "NETWORK_", "JEDEN ŚWIAT. CZTERY KLANY. JEDEN SYGNAŁ.", 1],
        system_layers: ["CHAOS", "REKONSTRUKCJA_", "WARSTWY ZAPISU ZAKOŃCZONEGO CYKLU", 2],
        desktop_assembly: ["PULPIT", "REKONSTRUKCJA_", "PRZYGOTOWANIE WIDOKU NOWEGO CYKLU", 3],
        system_ready: ["CHAOS", "WIDOK GOTOWY_", "REKONSTRUKCJA — PODSUMOWANIE", 4],
        shutdown: ["KONIEC", "TEGO CYKLU_", "ZAMYKANIE PREZENTACJI", 4],
        restart: ["NOWY", "CYKL_", "OCZEKIWANIE NA POTWIERDZENIE RESTARTU", 4]
    };

    function renderInterface(doc, stage, snapshot, scene) {
        const spec = INTERFACE_SCENES[scene.id];
        const make = (tag, cls, text) => {
            const n = doc.createElement(tag); n.className = cls;
            if (text !== undefined) n.textContent = text;
            return n;
        };
        const canvas = make("div", "ghost-show-interface");
        canvas.setAttribute("data-composition", scene.id);
        const city = make("div", "gsi-city"); city.setAttribute("aria-hidden", "true");
        canvas.appendChild(city);
        if (global.ChaosMapGlitch) {
            const glitch = make("div", "chaos-map-glitch-overlay is-visible gsi-glitch");
            glitch.setAttribute("aria-hidden", "true");
            // Fixed positions across clients and re-entry; same map block generator.
            let seed = 139140;
            global.ChaosMapGlitch.seed(glitch, doc, () => {
                seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
                return seed / 4294967296;
            });
            canvas.appendChild(glitch);
        }
        canvas.appendChild(make("p", "gsi-tag", "CHAOS / GHOST NETWORK"));
        const message = make("div", "gsi-message");
        message.appendChild(make("p", "gsi-kicker", scene.label));
        const title = make("h2", "gsi-title");
        title.appendChild(make("span", "gsi-brand", spec[0]));
        title.appendChild(make("span", "gsi-hero", spec[1]));
        message.appendChild(title);
        message.appendChild(make("p", "gsi-statement", spec[2]));
        canvas.appendChild(message);
        const list = make("ol", "gsi-layers");
        ["INTERFEJS", "GHOST NETWORK", "ŚWIAT", "UCZESTNICY", "GHOSTSIGNAL"].forEach((label, index) => {
            const row = make("li", index === spec[3] ? "is-current" : "");
            row.style.setProperty("--gsi-fx-offset", (index * 2.4) + "s");
            row.appendChild(make("span", "gsi-index ofs-scene-icon", "0" + (index + 1) + " /"));
            row.appendChild(make("span", "gsi-label ofs-scene-text", label));
            list.appendChild(row);
        });
        list.setAttribute("aria-label", "Warstwy prezentacji");
        canvas.appendChild(list);
        const data = (snapshot.show_manifest.cycle_history || {}).settlement;
        const late = scene.elapsed >= 720;
        const note = late ? (scene.id === "restart" || scene.id === "shutdown"
            ? "Przejście nastąpi po potwierdzeniu nowego cyklu."
            : "Rekonstrukcja wizualna. Rzeczywisty boot nastąpi po potwierdzeniu restartu.")
            : "JEDEN ŚWIAT. CZTERY KLANY. JEDEN SYGNAŁ.";
        const details = make("div", "gsi-details");
        details.appendChild(make("p", "gsi-note", note));
        if (late) details.appendChild(make("p", "gsi-facts", data && data.available
            ? "ZAPIS CYKLU / " + data.players_total + " uczestników / " + data.rewards_total + " nagród"
            : "Oczekiwanie na zapis wyników finału."));
        canvas.appendChild(details);
        stage.appendChild(canvas);
    }

    const PART_SCENES = ["parts_enter", "parts_complete", "connections", "history_logs", "part_states"];

    function syncParts(stage, scene) {
        (stage._partsRows || []).forEach((row, index) => {
            const visible = scene.id !== "parts_enter" || index < Math.ceil(scene.progress * 20);
            row.card.style.visibility = visible ? "visible" : "hidden";
            row.card.tabIndex = visible ? 0 : -1;
            row.card.setAttribute("aria-hidden", visible ? "false" : "true");
            if (visible && !row.loaded) { row.load(); row.loaded = true; }
        });
    }

    function renderParts(doc, stage, manifest, scene, layout, pageIndex, element, addImage) {
        const canvas = element("section", "ghost-show-parts");
        const recordsView = scene.id === "history_logs" || scene.id === "part_states";
        canvas.setAttribute("data-view", recordsView ? "records" : "parts");
        canvas.appendChild(element("div", "background"));
        const glitch = element("div", "chaos-map-glitch-overlay is-visible gsi-glitch parts-glitch");
        glitch.setAttribute("aria-hidden", "true");
        canvas.appendChild(glitch);
        if (global.ChaosMapGlitch) {
            let seed = 139140;
            global.ChaosMapGlitch.seed(glitch, doc, () => {
                seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
                return seed / 4294967296;
            });
        }
        const header = element("header", "");
        header.appendChild(element("span", "", "CHAOS / GHOST NETWORK"));
        header.appendChild(element("span", "", "CZTERY PLANY / JEDNA SIEĆ"));
        canvas.appendChild(header);
        const heading = element("section", "heading");
        heading.appendChild(element("p", "eyebrow", scene.id === "history_logs" ? "HISTORIA CZĘŚCI / UTC"
            : scene.id === "part_states" ? "STANY CZĘŚCI / ZAPIS CYKLU" : "GHOSTSIGNAL / HISTORIA CZĘŚCI"));
        const title = element("h1", "");
        title.appendChild(element("span", "twenty", String(layout.nodes.length)));
        const word = element("span", "word", "CZĘŚCI");
        word.appendChild(element("span", "underscore", "_")); title.appendChild(word);
        heading.appendChild(title);
        heading.appendChild(element("p", "deck", "CZTERY MASZYNY. JEDNA SIEĆ."));
        const legend = element("div", "legend");
        layout.machines.forEach((machine, index) => {
            const label = element("span", "", "0" + (index + 1) + " / " + machine.name);
            label.setAttribute("data-clan", machine.clan_code); legend.appendChild(label);
        });
        heading.appendChild(legend);
        const history = manifest.cycle_history || {};
        if (!history.available) heading.appendChild(element("p", "parts-history-note", "Historia niepełna — pokazujemy dostępny zapis."));
        if (recordsView) {
            const records = element("ol", "parts-records");
            const codes = (layout.machines[pageIndex] || {}).part_codes || [];
            const rows = codes.slice(0, 5).map(code => layout.nodes.find(n => n.part.part_code === code)).filter(Boolean);
            const timestamp = value => {
                const time = Date.parse(value || "");
                return Number.isFinite(time) ? new Date(time).toISOString().replace("T", " ").slice(0, 19) : "brak zapisu";
            };
            rows.forEach(node => {
                const row = element("li", "parts-record");
                row.appendChild(element("b", "", node.part.part_code + " / " + node.part.name));
                row.appendChild(element("span", "", scene.id === "history_logs"
                    ? "Odkrycie: " + timestamp(node.history.discovered_at)
                    : "Stan: " + (node.history.status || "brak zapisu")));
                row.appendChild(element("span", "", "Aktywacja: " + timestamp(node.history.activated_at)));
                records.appendChild(row);
            });
            if (!rows.length) records.appendChild(element("li", "", "Brak części w zapisie tej grupy."));
            heading.appendChild(records);
            heading.appendChild(element("p", "parts-page", (layout.machines[pageIndex] || {}).name || "Brak grupy"));
        }
        canvas.appendChild(heading);
        const board = element("ol", "parts-board");
        board.setAttribute("aria-label", "Części w czterech planach");
        // Connections carry the same addresses until the network template (.3).
        // Edges come exclusively from the frozen ring, never a guessed catalog order.
        if (scene.id === "connections") {
            [false, true].forEach(portrait => {
                const svg = doc.createElementNS("http://www.w3.org/2000/svg", "svg");
                svg.setAttribute("class", "parts-edges " + (portrait ? "is-portrait" : "is-desktop"));
                svg.setAttribute("viewBox", "0 0 1000 1000"); svg.setAttribute("preserveAspectRatio", "none");
                svg.setAttribute("aria-hidden", "true");
                layout.edges.forEach(pair => {
                    const a = PART_POSES[pair[0]], b = PART_POSES[pair[1]];
                    if (!a || !b) return;
                    const offset = portrait ? 2 : 0;
                    const line = doc.createElementNS("http://www.w3.org/2000/svg", "line");
                    line.setAttribute("x1", a.values[offset] * 10); line.setAttribute("y1", a.values[offset + 1] * 10);
                    line.setAttribute("x2", b.values[offset] * 10); line.setAttribute("y2", b.values[offset + 1] * 10);
                    svg.appendChild(line);
                });
                board.appendChild(svg);
            });
            if (!layout.edges.length) heading.appendChild(element("p", "parts-history-note", "Brak zapisu połączeń."));
        }
        stage._partsRows = layout.nodes.map((node, index) => {
            const part = node.part, pose = node.pose || {depth: 4, values: [50,50,50,50,1,0]};
            const card = element("li", "part");
            card.setAttribute("data-code", part.part_code); card.setAttribute("data-depth", pose.depth);
            card.setAttribute("data-clan", part.clan_code || "");
            ["--x", "--y", "--mx", "--my", "--scatter-scale", "--turn"].forEach((key, i) =>
                card.style.setProperty(key, pose.values[i] + (i < 4 ? "%" : i === 5 ? "deg" : "")));
            card.style.setProperty("--fx-offset", (index * .37).toFixed(2) + "s");
            const identity = element("div", "identity");
            identity.appendChild(element("b", "", part.part_code)); card.appendChild(identity);
            const frame = element("span", "part-art-frame");
            // is-active selects the existing decorative map effect, not gameplay state.
            const art = element("span", "ghostnetwork-node is-active");
            const halo = element("span", "ghostnetwork-part-halo"); halo.setAttribute("aria-hidden", "true");
            art.appendChild(halo); frame.appendChild(art); card.appendChild(frame);
            card.appendChild(element("h2", "", part.name)); board.appendChild(card);
            return {card, loaded: false, load: () => addImage(art,
                "/static/images/ghostnetwork/parts/" + part.part_code.toLowerCase() + "_" + part.icon_key + ".png",
                "ghostnetwork-part-art", part.name)};
        });
        canvas.appendChild(board); stage.appendChild(canvas);
        syncParts(stage, scene);
    }

    function renderMontage(doc, root, snapshot, scene) {
        const stage = root.querySelector(".ghost-signal-show__stage");
        root.classList.remove("has-interface");
        root.classList.remove("has-parts");
        if (!stage || !scene || scene.blocked) {
            clearMontage(stage);
            root.classList.remove("has-montage");
            return;
        }
        const manifest = snapshot.show_manifest;
        const isInterface = !!INTERFACE_SCENES[scene.id];
        const isParts = PART_SCENES.includes(scene.id);
        if (isParts) root.classList.add("has-parts");
        if (isInterface) root.classList.add("has-interface");
        const history = manifest.cycle_history || {};
        const settlement = history.settlement || {};
        const pageCounts = {history_logs: 4, part_states: 4, players: Math.ceil((settlement.players || []).length / 4),
            player_ranking: Math.ceil((settlement.players || []).length / 4),
            clan_ranking: Math.ceil((settlement.clans || []).length / 4),
            achievements: Math.ceil((settlement.players || []).length / 4),
            reward_ledger: Math.ceil((settlement.reward_groups || []).length / 4),
            clans: Math.ceil((settlement.clans || []).length / 4),
            conflict_results: Math.ceil(((settlement.conflicts || []).length + (settlement.production_conflicts || []).length) / 4),
            googleplex: (settlement.publications || []).filter(p => p.medium === "googleplex_news").length,
            blacknet_history: (settlement.publications || []).filter(p => p.medium === "blacknet").length};
        const pageCount = Math.max(1, pageCounts[scene.id] || 1);
        const pageIndex = Math.min(pageCount - 1, Math.floor(scene.progress * pageCount));
        const key = [snapshot.signal_public_id, scene.id, !!manifest.signal_confirmed,
            !!history.settlement,
            pageIndex,
            scene.id === "terminal_2108" ? Math.floor(scene.progress * 100) : ""].join(":");
        root.classList.add("has-montage");
        stage.style.setProperty("--scene-progress", scene.progress);
        // Subtle OFS-like light follows the existing server-aligned render tick.
        // No extra timer or animation history is needed after seek/reconnect.
        if (isInterface || isParts) {
            const elapsed = Number(scene.elapsed) || 0;
            stage.style.setProperty("--gsi-fx-clock", (-elapsed) + "s");
            stage.style.setProperty("--gsi-light", (0.5 - 0.5 * Math.cos(elapsed * Math.PI * 2 / 5.4)).toFixed(4));
            stage.style.setProperty("--gsi-line-light", (0.5 - 0.5 * Math.cos(elapsed * Math.PI * 2 / 8 + 1.2)).toFixed(4));
            stage.style.setProperty("--fx-clock", (-elapsed) + "s");
            stage.style.setProperty("--light", (0.5 - 0.5 * Math.cos(elapsed * Math.PI * 2 / 5.4)).toFixed(4));
        }
        root.style.background = scene.id === "takeover" && !isInterface
            ? "rgba(5,9,13," + (0.15 + scene.progress * 0.8) + ")" : "#05090d";
        const syncGlitch = () => {
            const glitch = stage.querySelector(".gsi-glitch");
            if (glitch) {
                const high = (Number(scene.elapsed) || 0) % 12 >= 7;
                glitch.className = "chaos-map-glitch-overlay is-visible gsi-glitch is-slow"
                    + (isParts ? " parts-glitch" : "")
                    + (high ? " is-heavy is-overloaded" : "");
                glitch.setAttribute("data-glitch-level", high ? "overloaded" : "slow");
            }
        };
        if (stage._showKey === key) { syncVideo(stage, scene); syncGlitch(); syncParts(stage, scene); return; }
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
        if (isInterface) {
            renderInterface(doc, stage, snapshot, scene);
        } else if (isParts) {
            renderParts(doc, stage, manifest, scene, layout, pageIndex, element, addImage);
        } else if (scene.elapsed >= 480) {
            const data = history.settlement;
            const panel = element("div", "ghost-show-settlement");
            panel.appendChild(element("p", "ghost-show-kicker", "ARCHIWUM FINAŁU / REKONSTRUKCJA"));
            const line = text => panel.appendChild(element("p", "", text));
            if (data && data.details_truncated) line("Ograniczony zakres szczegółów — dostępne podsumowanie finału.");
            if (!data || !data.available) {
                line("Oczekiwanie na zapis wyników finału.");
            } else if (["aftershock", "world_before", "territory_outcomes", "territory_reduction", "world_final"].includes(scene.id)) {
                line("Zakres rozliczenia sygnału: " + data.territories_total + " terytoriów skonsumowanych.");
                if (scene.id === "territory_reduction") {
                    line("Brak osobnej projekcji terytoriów zredukowanych i zachowanych.");
                }
                const shapes = (data.territories || []).slice(0, 40).filter(t => t.geometry_available && t.points.length >= 3);
                if (shapes.length) {
                    const svg = doc.createElementNS("http://www.w3.org/2000/svg", "svg");
                    svg.classList.add("ghost-show-settlement-map");
                    const points = shapes.flatMap(t => t.points);
                    const xs = points.map(p => p[0]), ys = points.map(p => p[1]);
                    const minX = Math.min.apply(null, xs), minY = Math.min.apply(null, ys);
                    const spanX = Math.max(0.0001, Math.max.apply(null, xs) - minX);
                    const spanY = Math.max(0.0001, Math.max.apply(null, ys) - minY);
                    const scale = Math.min(900 / spanX, 340 / spanY);
                    svg.setAttribute("viewBox", "0 0 1000 440");
                    for (const territory of shapes) {
                        const polygon = doc.createElementNS("http://www.w3.org/2000/svg", "polygon");
                        polygon.setAttribute("points", territory.points.map(p =>
                            (50 + (p[0] - minX) * scale) + "," + (390 - (p[1] - minY) * scale)).join(" "));
                        polygon.setAttribute("class", scene.id === "world_before" ? "is-before" : "is-consumed");
                        const title = doc.createElementNS("http://www.w3.org/2000/svg", "title");
                        title.textContent = territory.label + " / " + territory.clan;
                        polygon.appendChild(title); svg.appendChild(polygon);
                    }
                    panel.appendChild(svg);
                } else { line("Geometria archiwalna niedostępna — podsumowanie tekstowe."); }
                line("Mapa schematyczna zakresu finału; poza nim brak projekcji świata.");
                if (data.territories_truncated) line("Geometria: ograniczony wybór 40 terytoriów.");
            } else if (scene.id === "conflict_results") {
                line("Archiwalne konflikty strategiczne: " + data.conflicts_total);
                const rows = (data.conflicts || []).slice(0, 20).concat((data.production_conflicts || []).slice(0, 20));
                for (const row of rows.slice(pageIndex * 4, pageIndex * 4 + 4)) line(row.label + " / " + row.status + " / " + (row.resolved_at || ""));
                line("Strona " + (pageIndex + 1) + " / " + pageCount);
                line("Podsumowanie obejmuje konflikty wskazane w archiwum finału.");
            } else if (scene.id === "reward_ledger") {
                line("Nagrody finału: " + data.rewards_total + " / RSP: " + data.rsp_total);
                const labels = {ghost_signal_node_holder: "Kontrola węzłów", ghost_signal_closer: "Zamknięcie sygnału",
                    ghost_signal_territory_consumed: "Terytoria finału"};
                for (const row of (data.reward_groups || []).slice(pageIndex * 4, pageIndex * 4 + 4)) line((labels[row.type] || "Nagroda finału") + " / " + row.count + " / " + row.rsp + " RSP");
            } else if (scene.id === "players" || scene.id === "achievements") {
                line("Uczestnicy: " + data.players_total + (data.players_truncated ? " / wybór pierwszych 20" : ""));
                const players = (data.players || []).slice(0, 20);
                const pages = Math.max(1, Math.ceil(players.length / 4));
                const page = Math.min(pages - 1, Math.floor(scene.progress * pages));
                line("Strona " + (page + 1) + " / " + pages);
                for (const player of players.slice(page * 4, page * 4 + 4)) {
                    line(player.alias + " / " + player.clan + " / " + player.rsp + " RSP / węzły: " + player.nodes
                        + (player.closer ? " / ZAMKNIĘCIE SYGNAŁU" : ""));
                }
                if (scene.id === "achievements") line("Osiągnięcia wynikają z rankingu finału; bez dodatkowych odznak.");
            } else if (scene.id === "clans") {
                line("Clan Ghost Score / " + data.score_policy);
                for (const clan of (data.clans || []).slice(pageIndex * 4, pageIndex * 4 + 4)) line(clan.code + " / " + clan.score
                    + " / uczestnicy: " + clan.members + " / " + clan.rsp + " RSP");
            } else if (scene.elapsed >= 840) {
                if (scene.id === "player_ranking") {
                    line("RANKING GRACZY / " + data.players_total);
                    if (data.players_truncated) line("Wyświetlany jest wybór pierwszych " + (data.players || []).length + " uczestników.");
                    for (const player of (data.players || []).slice(pageIndex * 4, pageIndex * 4 + 4))
                        line(player.rank + ". " + player.alias + " / " + player.rsp + " RSP");
                } else if (scene.id === "clan_ranking") {
                    line("RANKING KLANÓW / " + data.score_policy);
                    for (const clan of (data.clans || []).slice(pageIndex * 4, pageIndex * 4 + 4))
                        line(clan.rank + ". " + clan.code + " / " + clan.score);
                } else if (scene.id === "cycle_statistics") {
                    line("Uczestnicy: " + data.players_total + " / nagrody: " + data.rewards_total);
                    line("RSP finału: " + data.rsp_total + " / terytoria: " + data.territories_total);
                } else if (scene.id === "archive") {
                    line("SIGNAL REGISTRY / " + snapshot.signal_public_id);
                    line("Archiwum finału będzie dostępne na pulpicie po restarcie.");
                } else {
                    line("GHOSTSYSTEM / OCZEKIWANIE NA RESTART");
                    line("Przejście nastąpi po potwierdzeniu nowego cyklu.");
                }
            } else {
                const layers = {
                    system_layers: "CHAOS / warstwy systemu",
                    googleplex: "GOOGLEPLEX / zapis publikacji",
                    pro_tools: "PRO TOOLS / TERMINAL",
                    file_system: "PLIKI / ARCHIWUM SYGNAŁU",
                    blacknet_history: "BLACKNET / HISTORIA",
                    desktop_assembly: "PULPIT / REKONSTRUKCJA",
                    system_ready: "WARSTWY PREZENTACJI GOTOWE"
                };
                panel.appendChild(element("h2", "", layers[scene.id] || scene.label));
                line("Rekonstrukcja wizualna — rzeczywisty boot nastąpi według procedury restartu.");
                if (scene.id === "googleplex" || scene.id === "blacknet_history") {
                    const medium = scene.id === "googleplex" ? "googleplex_news" : "blacknet";
                    const records = (data.publications || []).filter(p => p.medium === medium).slice(0, 6);
                    const index = Math.min(records.length - 1, Math.floor(scene.progress * records.length));
                    for (const record of records.slice(Math.max(0, index), index + 1)) {
                        panel.appendChild(element("h3", "", record.title));
                        line(record.body); line(record.published_at);
                    }
                    if (!records.length) line("Brak publicznego zapisu w tej projekcji finału.");
                } else {
                    line("GhostSignal / " + snapshot.signal_public_id);
                    line("Zapisano: " + data.players_total + " uczestników / " + data.rewards_total + " nagród finału.");
                }
            }
            stage.appendChild(panel);
        } else if (heroIndex >= 0) {
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
                        if (playing && playing.catch) playing.catch(() => {
                            if (stage._video !== video) return;
                            video._audioBlocked = true; video.muted = true;
                            const silent = video.play();
                            if (silent && silent.catch) silent.catch(failed);
                        });
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
        syncGlitch();
    }

    function showAudioAt(snapshot, now, offset) {
        const config = snapshot && snapshot.show_manifest && snapshot.show_manifest.audio;
        const start = Date.parse(snapshot && snapshot.show_started_at || "");
        const end = Date.parse(snapshot && snapshot.show_ends_at || "");
        if (!snapshot || !snapshot.show_active || !config || !Array.isArray(config.show_tracks)
                || config.show_tracks.length !== 4 || !Number.isFinite(start) || !(end > start)) return null;
        const elapsed = Math.max(0, (now + (offset || 0) - start) * 900 / (end - start));
        const pauseAt = 425.5, resumeAt = 463.12;
        const position = elapsed < pauseAt ? elapsed : elapsed < resumeAt ? pauseAt : elapsed - (resumeAt - pauseAt);
        let base = 0;
        for (const track of config.show_tracks) {
            if (!Number.isFinite(track.duration) || track.duration <= 0) return null;
            if (position < base + track.duration) return {key: snapshot.signal_public_id || snapshot.show_started_at,
                src: track.src, offset: position - base, elapsed,
                paused: elapsed >= pauseAt && elapsed < resumeAt};
            base += track.duration;
        }
        return {key: snapshot.signal_public_id || snapshot.show_started_at, src: "", offset: 0, elapsed, paused: true};
    }

    function ownsShowAudio() { return !global.top || global.top === global; }

    function createController(options) {
        options = options || {};
        const doc = options.document || global.document;
        const fetcher = options.fetch || global.fetch;
        let snapshot = null;
        let offsetMs = 0;
        let timer = 0;
        let pollTimer = 0;
        let mediaTimer = 0;
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
            global.clearTimeout(mediaTimer); mediaTimer = 0;
            if (ownsShowAudio() && global.GhostRadio && global.GhostRadio.endShow) global.GhostRadio.endShow(!rebooting);
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
            global.clearTimeout(mediaTimer); mediaTimer = 0;
            const clockStart = Date.parse(snapshot.show_started_at || "");
            const clockEnd = Date.parse(snapshot.show_ends_at || "");
            if (clockEnd > clockStart) {
                const clockNow = Date.now() + offsetMs;
                const nextCue = [425, 463.12].map(t => clockStart + t * (clockEnd - clockStart) / 900)
                    .find(t => t > clockNow);
                if (nextCue) mediaTimer = global.setTimeout(render, Math.max(1, nextCue - clockNow));
            }
            const radio = ownsShowAudio() && global.GhostRadio && global.GhostRadio.syncShow ? global.GhostRadio : null;
            const audioState = showAudioAt(snapshot, Date.now(), offsetMs);
            if (radio && radio.syncShow) {
                if (audioState) radio.syncShow(audioState);
                else radio.endShow(false);
            }
            renderMontage(doc, root, snapshot, scene);
            const stage = root.querySelector(".ghost-signal-show__stage");
            const video = stage && stage._video;
            const sound = root.querySelector(".ghost-signal-show__sound");
            const settings = radio && radio.getState ? radio.getState() : null;
            if (video) {
                video.muted = !!(!settings || settings.muted || settings.showAudioBlocked || video._audioBlocked);
                video.volume = settings ? Math.max(0, Math.min(1, settings.effectiveVolume)) : 0;
            }
            if (sound) {
                sound.style.display = radio && audioState ? "" : "none";
                sound.textContent = settings && (settings.showAudioBlocked || (video && video._audioBlocked))
                    ? "Włącz dźwięk" : settings && settings.muted ? "Włącz dźwięk" : "Wycisz";
                sound.onclick = () => {
                    if (!radio) return;
                    const current = radio.getState();
                    const enable = current.muted || current.showAudioBlocked || (video && video._audioBlocked);
                    radio.mute(!enable);
                    if (enable) radio.unlockShow();
                    if (video) {
                        video._audioBlocked = false; video.muted = !enable;
                        const playing = video.play();
                        if (playing && playing.catch) playing.catch(() => { video._audioBlocked = true; video.muted = true; });
                    }
                };
            }
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
            global.clearTimeout(mediaTimer); mediaTimer = 0;
            if (ownsShowAudio() && global.GhostRadio && global.GhostRadio.endShow) global.GhostRadio.endShow(false);
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

    const api = {createController, serverOffset, secondsRemaining, phaseAt, sceneAt, sceneLayout, showAudioAt, PHASE_COPY};
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
