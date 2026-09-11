const RADIO_BASE_PATH = "/static/mp3/radio/channel";
const DEFAULT_RADIO_CHANNEL = "ghost_streem_1";

(function initGhostRadioModule() {
    const state = {
        basePath: RADIO_BASE_PATH,
        defaultChannel: DEFAULT_RADIO_CHANNEL,
        channels: [],
        channel: null,
        playlist: [],
        currentIndex: 0,
        channelId: null,
        audio: null,
        initialized: false,
        isPlaying: false,
        volume: 0.8,
        previousVolume: 0.8,
        muted: false,
        duckGain: 1,
        duckRequests: new Map(),
        duckSequence: 0,
        syncingVolume: false,
        firstInteractionBound: false,
        firstInteractionAttempted: false,
        autostartBlocked: false,
        suppressPauseStatus: false,
        resumeAfterSourceChange: false,
        errorSkips: 0,
        elements: {}
    };
    let showPlayback = null;
    let sourceGeneration = 0;
    const showResumeKey = "chaos:ghost-show-radio-resume";
    let pendingRadioRestore = null;
    let resumeAutoplayAllowed = true;
    try {
        const saved = JSON.parse(window.sessionStorage.getItem(showResumeKey) || "null");
        if (saved && typeof saved.wasPlaying === "boolean") {
            pendingRadioRestore = saved;
            resumeAutoplayAllowed = saved.wasPlaying;
            state.volume = Math.max(0, Math.min(1, Number(saved.volume) || 0));
            state.muted = !!saved.muted;
        }
    } catch (_) { /* Storage is optional. */ }

    function rememberShowRadio() {
        if (!showPlayback) return;
        try { window.sessionStorage.setItem(showResumeKey, JSON.stringify({
            wasPlaying: showPlayback.wasPlaying, originalSrc: showPlayback.originalSrc,
            originalTime: showPlayback.originalTime, volume: state.volume, muted: state.muted
        })); } catch (_) { /* Storage is optional. */ }
    }

    function clearShowRadioReceipt() {
        try { window.sessionStorage.removeItem(showResumeKey); } catch (_) { /* Optional. */ }
    }

    function cancelShowFade(current) {
        if (!current) return;
        clearTimeout(current.fadeTimer);
        if (current.fadeFrame) cancelAnimationFrame(current.fadeFrame);
    }

    function scheduleShowFade() {
        const current = showPlayback;
        if (!current) return;
        cancelShowFade(current);
        const step = () => {
            if (showPlayback !== current) return;
            const t = current.elapsed + (Date.now() - current.anchor) / 1000;
            const start = current.videoStart, end = current.videoEnd;
            const fadingOut = t >= start && t < start + 0.5;
            const fadingIn = t >= end && t < end + 0.5;
            current.gain = fadingOut ? (start + 0.5 - t) / 0.5 : fadingIn ? (t - end) / 0.5
                : t >= start + 0.5 && t < end ? 0 : 1;
            if (t >= start + 0.5 && t < end) { current.paused = true; current.inVideo = true; current.offset = current.pauseOffset; state.audio.pause(); }
            if (t >= end && current.inVideo) {
                current.inVideo = false; current.paused = !current.src;
                current.offset += t - end;
                syncShowMedia();
            }
            syncAudioSettings();
            if (fadingOut || fadingIn) current.fadeFrame = requestAnimationFrame(step);
            else {
                const next = t < start ? start : t < end ? end : null;
                if (next !== null) current.fadeTimer = setTimeout(step, Math.max(0, (next - t) * 1000));
            }
        };
        step();
    }

    function syncShowMedia() {
        if (!showPlayback || !state.audio) return;
        const current = showPlayback;
        if (state.audio.readyState >= 1 && Number.isFinite(state.audio.duration)) {
            const target = Math.max(0, Math.min(state.audio.duration - 0.05, current.offset));
            if (Math.abs(state.audio.currentTime - target) > 0.75) state.audio.currentTime = target;
        }
        if (current.paused || current.failed || current.blocked || !current.allowed) {
            state.audio.pause(); return;
        }
        if (state.audio.paused && !current.playPending) {
            current.playPending = true;
            const promise = state.audio.play();
            if (promise && promise.then) promise.then(() => {
                current.playPending = false;
                if (showPlayback === current && current.paused) state.audio.pause();
            }, () => { current.playPending = false; current.blocked = true; });
            else current.playPending = false;
        }
    }

    function escapeRadioHTML(value) {
        return String(value == null ? "" : value).replace(/[&<>"']/g, (char) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[char]));
    }

    function channelPath(id) {
        return `${state.basePath}/${encodeURIComponent(String(id || state.defaultChannel))}`;
    }

    function trackUrl(channelId, fileName) {
        return `${channelPath(channelId)}/${encodeURIComponent(String(fileName || ""))}`;
    }

    function isPlayableMp3Track(track) {
        return Boolean(track && typeof track.file === "string" && /\.mp3$/i.test(track.file.trim()));
    }

    function radioManifestUrl(channelId) {
        return `/api/radio/channel/${encodeURIComponent(String(channelId || state.defaultChannel))}`;
    }

    function radioChannelsUrl() {
        return "/api/radio/channels";
    }

    function currentTrack() {
        return state.playlist[state.currentIndex] || null;
    }

    function shuffleTracks(tracks) {
        const shuffled = tracks.slice();
        for (let index = shuffled.length - 1; index > 0; index -= 1) {
            const swapIndex = Math.floor(Math.random() * (index + 1));
            [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
        }
        return shuffled;
    }

    function streamStartIndex(length, channel = {}) {
        if (!length) return 0;
        return String(channel.mode || "").toLowerCase() === "random"
            ? Math.floor(Math.random() * length)
            : 0;
    }

    function requestedTrackIndex(playlist, options = {}) {
        if (!Array.isArray(playlist) || !playlist.length || !options || typeof options !== "object") {
            return null;
        }
        const requestedFile = String(options.trackFile || options.file || "").trim().toLowerCase();
        if (requestedFile) {
            const matchIndex = playlist.findIndex(track => String(track.file || "").trim().toLowerCase() === requestedFile);
            if (matchIndex >= 0) return matchIndex;
        }
        const rawIndex = Number(options.trackIndex == null ? options.index : options.trackIndex);
        if (Number.isFinite(rawIndex)) {
            const zeroBased = rawIndex > 0 ? rawIndex - 1 : rawIndex;
            return Math.max(0, Math.min(Math.floor(zeroBased), playlist.length - 1));
        }
        return null;
    }

    function displayTrackTitle(track, fallbackIndex = 0) {
        const source = String((track && (track.title || track.file)) || `Track ${fallbackIndex + 1}`);
        const filename = source.split(/[\\/]/).pop() || source;
        return filename.replace(/\.mp3$/i, "").replace(/[_-]+/g, " ").trim() || `Track ${fallbackIndex + 1}`;
    }

    function setStatus(text) {
        if (state.elements.status) {
            state.elements.status.textContent = text || "SIGNAL IDLE";
        }
    }

    function isAutoplayEnabled() {
        try {
            return !window.localStorage || window.localStorage.getItem("ghost_radio_autoplay") !== "0";
        } catch (error) {
            return true;
        }
    }

    function updatePlaybackView() {
        const track = currentTrack();
        const isPlaying = Boolean(state.isPlaying);
        if (state.elements.root) {
            state.elements.root.classList.toggle("is-playing", isPlaying);
            state.elements.root.classList.toggle("is-muted", state.muted);
        }
        if (state.elements.playButton) state.elements.playButton.disabled = !track || isPlaying;
        if (state.elements.pauseButton) state.elements.pauseButton.disabled = !track || !isPlaying;
        const hasChannelSwitch = state.channels.length > 1;
        if (state.elements.nextButton) state.elements.nextButton.disabled = !hasChannelSwitch;
        if (state.elements.previousButton) state.elements.previousButton.disabled = !hasChannelSwitch;
        updateVolumeView();
    }

    function updateTrackView() {
        const track = currentTrack();
        const channelName = (state.channel && state.channel.name) || "Ghost Hack Radio";
        const trackTitle = (track && track.title) || "Brak utworu";
        const position = state.playlist.length ? `${state.currentIndex + 1} / ${state.playlist.length}` : "0 / 0";

        if (state.elements.channelName) state.elements.channelName.textContent = channelName;
        if (state.elements.trackTitle) state.elements.trackTitle.textContent = trackTitle;
        if (state.elements.trackCount) state.elements.trackCount.textContent = position;
        if (state.elements.sourcePath) {
            state.elements.sourcePath.textContent = `${channelPath(state.channelId || state.defaultChannel)}/`;
        }
        updatePlaybackView();
    }

    function updateProgress() {
        const audio = state.audio;
        const duration = audio && Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : 0;
        const current = audio && Number.isFinite(audio.currentTime) ? audio.currentTime : 0;
        const percent = duration > 0 ? Math.min(100, Math.max(0, (current / duration) * 100)) : 0;
        if (state.elements.progressFill) {
            state.elements.progressFill.style.width = `${percent}%`;
        }
        if (state.elements.time) {
            state.elements.time.textContent = `${formatTime(current)} / ${duration ? formatTime(duration) : "--:--"}`;
        }
    }

    function formatTime(seconds) {
        const safe = Math.max(0, Math.floor(Number(seconds) || 0));
        const minutes = Math.floor(safe / 60);
        const rest = String(safe % 60).padStart(2, "0");
        return `${minutes}:${rest}`;
    }

    function setAudioSource(index = state.currentIndex) {
        if (showPlayback) return;
        if (!state.audio || !state.playlist.length) return;
        state.currentIndex = Math.max(0, Math.min(index, state.playlist.length - 1));
        const track = currentTrack();
        state.suppressPauseStatus = true;
        state.audio.pause();
        setTimeout(() => {
            state.suppressPauseStatus = false;
        }, 0);
        state.isPlaying = false;
        setStatus("SIGNAL TUNING");
        state.audio.src = track.url;
        state.audio.load();
        updateTrackView();
        updateProgress();
    }

    function syncAudioSettings() {
        if (!state.audio) return;
        const userVolume = Math.max(0, Math.min(1, Number(state.volume) || 0));
        const duckGain = Math.max(0, Math.min(1, Number(state.duckGain) || 0));
        state.syncingVolume = true;
        state.audio.volume = userVolume * duckGain * (showPlayback ? Math.max(0, Math.min(1, showPlayback.gain)) : 1);
        state.audio.muted = Boolean(state.muted);
        state.syncingVolume = false;
        updateVolumeView();
    }

    function refreshDuckGain() {
        let nextGain = 1;
        state.duckRequests.forEach(gain => {
            nextGain = Math.min(nextGain, Math.max(0, Math.min(1, Number(gain) || 0)));
        });
        state.duckGain = nextGain;
        syncAudioSettings();
        return state.duckGain;
    }

    function updateVolumeView() {
        if (state.elements.volumeInput) {
            state.elements.volumeInput.value = String(Math.round((state.volume || 0) * 100));
        }
        if (state.elements.volumeValue) {
            state.elements.volumeValue.textContent = `${Math.round((state.volume || 0) * 100)}%`;
        }
        if (state.elements.muteButton) {
            state.elements.muteButton.textContent = state.muted ? "\u{1F50A}" : "\u{1F507}";
            state.elements.muteButton.title = state.muted ? "Unmute" : "Mute";
            state.elements.muteButton.setAttribute("aria-label", state.muted ? "Unmute" : "Mute");
            state.elements.muteButton.classList.toggle("is-active", state.muted);
        }
    }

    function bindAudioEvents() {
        if (!state.audio || state.audio.dataset.ghostRadioBound === "1") return;
        state.audio.dataset.ghostRadioBound = "1";
        state.audio.addEventListener("ended", () => {
            if (showPlayback) return;
            GhostRadio.next({ fromEnded: true });
        });
        state.audio.addEventListener("timeupdate", updateProgress);
        state.audio.addEventListener("loadedmetadata", updateProgress);
        state.audio.addEventListener("loadedmetadata", syncShowMedia);
        state.audio.addEventListener("play", () => {
            state.isPlaying = true;
            state.resumeAfterSourceChange = false;
            state.errorSkips = 0;
            setStatus("SIGNAL ONLINE");
            updatePlaybackView();
        });
        state.audio.addEventListener("pause", () => {
            if (state.suppressPauseStatus) {
                updatePlaybackView();
                return;
            }
            state.isPlaying = false;
            setStatus("SIGNAL PAUSED");
            updatePlaybackView();
        });
        state.audio.addEventListener("error", () => {
            if (showPlayback) { showPlayback.failed = true; return; }
            if (state.resumeAfterSourceChange && state.playlist.length && state.errorSkips < state.playlist.length) {
                state.errorSkips += 1;
                setStatus("SIGNAL SEARCH");
                setTimeout(() => GhostRadio.next({ fromEnded: true, skipError: true }), 250);
                return;
            }
            state.resumeAfterSourceChange = false;
            setStatus("SIGNAL ERROR");
            updatePlaybackView();
        });
        state.audio.addEventListener("volumechange", () => {
            if (state.syncingVolume) {
                updateVolumeView();
                return;
            }
            state.muted = Boolean(state.audio.muted);
            updateVolumeView();
        });
    }

    function connectElements(root = document) {
        state.elements = {
            root: root.querySelector(".ghost-radio-shell"),
            status: root.querySelector("[data-radio-status]"),
            channelName: root.querySelector("[data-radio-channel]"),
            trackTitle: root.querySelector("[data-radio-track]"),
            trackCount: root.querySelector("[data-radio-count]"),
            time: root.querySelector("[data-radio-time]"),
            progressFill: root.querySelector("[data-radio-progress-fill]"),
            playButton: root.querySelector("[data-radio-action='play']"),
            pauseButton: root.querySelector("[data-radio-action='pause']"),
            nextButton: root.querySelector("[data-radio-action='next']"),
            previousButton: root.querySelector("[data-radio-action='previous']"),
            muteButton: root.querySelector("[data-radio-action='mute']"),
            volumeInput: root.querySelector("[data-radio-volume]"),
            volumeValue: root.querySelector("[data-radio-volume-value]"),
            sourcePath: root.querySelector("[data-radio-source]")
        };

        if (state.elements.playButton) state.elements.playButton.addEventListener("click", () => GhostRadio.play());
        if (state.elements.pauseButton) state.elements.pauseButton.addEventListener("click", () => GhostRadio.pause());
        if (state.elements.nextButton) state.elements.nextButton.addEventListener("click", () => GhostRadio.nextChannel());
        if (state.elements.previousButton) state.elements.previousButton.addEventListener("click", () => GhostRadio.previousChannel());
        if (state.elements.muteButton) state.elements.muteButton.addEventListener("click", () => GhostRadio.mute());
        if (state.elements.volumeInput) {
            state.elements.volumeInput.addEventListener("input", (event) => {
                GhostRadio.setVolume(Number(event.target.value) / 100);
            });
        }
    }

    const GhostRadio = {
        syncShow(request) {
            if (!request || !request.key) return;
            if (!state.audio) {
                state.audio = new Audio(); bindAudioEvents(); syncAudioSettings();
            }
            if (!showPlayback || showPlayback.key !== request.key) {
                if (showPlayback) this.endShow(false);
                sourceGeneration += 1;
                showPlayback = {key: request.key, originalSrc: state.audio.getAttribute("src") || "",
                    originalTime: state.audio.currentTime || 0, wasPlaying: !state.audio.paused,
                    allowed: isAutoplayEnabled(), src: null, offset: 0, gain: 1};
                if (pendingRadioRestore) {
                    showPlayback.wasPlaying = pendingRadioRestore.wasPlaying;
                    showPlayback.originalSrc = /^\/static\/mp3\/radio\/channel\//.test(pendingRadioRestore.originalSrc || "")
                        ? pendingRadioRestore.originalSrc : "";
                    showPlayback.originalTime = Math.max(0, Number(pendingRadioRestore.originalTime) || 0);
                    pendingRadioRestore = null;
                }
                rememberShowRadio();
                state.resumeAfterSourceChange = false;
            }
            const current = showPlayback;
            const src = /^\/static\/audio\/ghostnetwork\/show\/ghostsignal_show_part_0[1-4]\.mp3$/.test(request.src || "") ? request.src : "";
            current.offset = Math.max(0, Number(request.offset) || 0);
            current.paused = !!request.paused || !src;
            current.elapsed = Number(request.elapsed) || 0; current.anchor = Date.now();
            current.pauseOffset = current.offset + Math.max(0, 425.5 - current.elapsed);
            current.videoStart = 425; current.videoEnd = 463.12;
            current.inVideo = current.elapsed >= current.videoStart + 0.5 && current.elapsed < current.videoEnd;
            if (current.src !== src) {
                current.src = src; current.failed = false; current.playPending = false;
                state.audio.pause();
                if (src) state.audio.src = src; else state.audio.removeAttribute("src");
                state.audio.preload = "auto";
                state.audio.load();
            }
            scheduleShowFade(); syncAudioSettings(); syncShowMedia();
        },

        unlockShow() {
            if (showPlayback) {
                showPlayback.allowed = true; showPlayback.blocked = false;
                syncShowMedia();
            }
        },

        endShow(resume = true) {
            if (!showPlayback) {
                if (pendingRadioRestore && resume) {
                    const old = pendingRadioRestore;
                    pendingRadioRestore = null; clearShowRadioReceipt();
                    if (old.wasPlaying && isAutoplayEnabled()) this.startAutoplay().catch(() => {});
                }
                return;
            }
            const old = showPlayback;
            cancelShowFade(old);
            showPlayback = null; sourceGeneration += 1;
            if (resume) clearShowRadioReceipt();
            else pendingRadioRestore = {wasPlaying: old.wasPlaying, originalSrc: old.originalSrc,
                originalTime: old.originalTime, volume: state.volume, muted: state.muted};
            state.audio.pause();
            state.audio.preload = "metadata";
            const generation = sourceGeneration;
            if (old.originalSrc) {
                const restore = () => {
                    state.audio.removeEventListener("loadedmetadata", restore);
                    if (showPlayback || sourceGeneration !== generation) return;
                    if (Number.isFinite(state.audio.duration)) state.audio.currentTime = Math.min(old.originalTime, state.audio.duration);
                    if (resume && old.wasPlaying) this.play();
                };
                state.audio.addEventListener("loadedmetadata", restore);
                state.audio.src = old.originalSrc;
            } else { state.audio.removeAttribute("src"); }
            state.audio.load(); syncAudioSettings();
        },

        async loadChannels() {
            try {
                const response = await fetch(radioChannelsUrl(), { cache: "no-store" });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const payload = await response.json();
                const channels = Array.isArray(payload.channels) ? payload.channels : [];
                state.channels = channels
                    .filter(channel => channel && channel.id)
                    .map(channel => ({
                        ...channel,
                        id: String(channel.id)
                    }));
                if (payload.default_channel) {
                    state.defaultChannel = String(payload.default_channel);
                }
            } catch (error) {
                state.channels = [{ id: state.defaultChannel, name: "Ghost Hack Radio" }];
            }
            if (!state.channels.some(channel => channel.id === state.defaultChannel)) {
                state.channels.unshift({ id: state.defaultChannel, name: "Ghost Hack Radio" });
            }
            return state.channels.slice();
        },

        init(root = document) {
            if (showPlayback) return Promise.resolve(state.channel);
            if (!state.audio) {
                state.audio = new Audio();
                state.audio.preload = "metadata";
                bindAudioEvents();
                syncAudioSettings();
            }
            connectElements(root);
            state.initialized = true;
            if (state.channel && state.playlist.length) {
                const status = state.isPlaying
                    ? "SIGNAL ONLINE"
                    : (state.autostartBlocked ? "CLICK TO START" : "SIGNAL READY");
                setStatus(status);
                updateTrackView();
                updateProgress();
                syncAudioSettings();
                return Promise.resolve(state.channel);
            }
            return this.loadChannels().then(() => this.loadChannel(state.channelId || state.defaultChannel));
        },

        async loadChannel(id = state.defaultChannel, options = {}) {
            if (showPlayback) return state.channel;
            const generation = sourceGeneration;
            const channelId = String(id || state.defaultChannel);
            setStatus("SIGNAL LOADING");
            const response = await fetch(radioManifestUrl(channelId), { cache: "no-store" });
            if (!response.ok) {
                setStatus("SIGNAL LOST");
                throw new Error(`Ghost Radio channel load failed: ${response.status}`);
            }
            const manifest = await response.json();
            if (showPlayback || generation !== sourceGeneration) return state.channel;
            const channel = manifest.channel || {};
            if (Number(channel.schema) !== 1) {
                setStatus("BAD SCHEMA");
                throw new Error("Unsupported Ghost Radio channel schema.");
            }
            const tracks = Array.isArray(manifest.tracks)
                ? manifest.tracks.filter(isPlayableMp3Track)
                : [];
            const playlistSource = String(channel.mode || "").toLowerCase() === "random"
                ? shuffleTracks(tracks)
                : tracks;
            state.channel = channel;
            state.channelId = channelId;
            state.playlist = playlistSource
                .filter(isPlayableMp3Track)
                .map((track, index) => ({
                    title: displayTrackTitle(track, index),
                    file: track.file.trim(),
                    url: trackUrl(channelId, track.file.trim())
                }));
            const explicitIndex = requestedTrackIndex(state.playlist, options);
            state.currentIndex = explicitIndex === null
                ? streamStartIndex(state.playlist.length, channel)
                : explicitIndex;
            if (state.playlist.length) {
                setAudioSource(state.currentIndex);
            } else if (state.audio) {
                state.audio.removeAttribute("src");
                state.audio.load();
            }
            setStatus(state.playlist.length ? "SIGNAL READY" : "NO TRACKS");
            updateTrackView();
            syncAudioSettings();
            return state.channel;
        },

        async playTrack(channelId, options = {}) {
            if (showPlayback) return false;
            if (!state.audio) {
                state.audio = new Audio();
                state.audio.preload = "metadata";
                bindAudioEvents();
                syncAudioSettings();
            }
            if (!state.initialized) {
                await this.loadChannels();
                state.initialized = true;
            }
            await this.loadChannel(channelId || state.defaultChannel, options);
            return this.play();
        },

        async play() {
            if (showPlayback) return false;
            if (!state.audio || !currentTrack()) return false;
            try {
                await state.audio.play();
                state.autostartBlocked = false;
                return true;
            } catch (error) {
                state.autostartBlocked = true;
                setStatus("CLICK TO START");
                return false;
            }
        },

        pause() {
            if (!state.audio) return;
            state.audio.pause();
        },

        mute(force = null) {
            if (!state.audio) return false;
            const nextMuted = typeof force === "boolean" ? force : !state.muted;
            if (nextMuted) {
                state.previousVolume = state.volume > 0 ? state.volume : state.previousVolume || 0.8;
                state.muted = true;
            } else {
                state.muted = false;
                if (state.volume <= 0 && state.previousVolume > 0) {
                    state.volume = state.previousVolume;
                }
            }
            syncAudioSettings();
            rememberShowRadio();
            return state.muted;
        },

        setVolume(value) {
            const nextVolume = Math.max(0, Math.min(1, Number(value) || 0));
            state.volume = nextVolume;
            if (nextVolume > 0) {
                state.previousVolume = nextVolume;
                state.muted = false;
            } else {
                state.muted = true;
            }
            syncAudioSettings();
            rememberShowRadio();
            return state.volume;
        },

        requestDuck(gain = 1, source = "game-sfx") {
            state.duckSequence += 1;
            const token = `duck-${state.duckSequence}`;
            state.duckRequests.set(token, Math.max(0, Math.min(1, Number(gain) || 0)));
            refreshDuckGain();
            let released = false;
            return Object.freeze({
                token,
                source: String(source || "game-sfx"),
                release() {
                    if (released) return false;
                    released = true;
                    state.duckRequests.delete(token);
                    refreshDuckGain();
                    return true;
                }
            });
        },

        releaseDuck(handleOrToken) {
            if (handleOrToken && typeof handleOrToken.release === "function") {
                return handleOrToken.release();
            }
            const token = String(handleOrToken || "");
            const removed = state.duckRequests.delete(token);
            if (removed) refreshDuckGain();
            return removed;
        },

        async startAutoplay() {
            if (showPlayback || pendingRadioRestore || !resumeAutoplayAllowed) return false;
            if (!isAutoplayEnabled()) {
                setStatus("AUTOPLAY OFF");
                return false;
            }
            await this.init();
            state.firstInteractionAttempted = true;
            const started = await this.play();
            if (!started) {
                state.autostartBlocked = true;
                setStatus("CLICK TO START");
            }
            return started;
        },

        armFirstInteractionAutostart() {
            if (window.top && window.top !== window) return false;
            if (state.firstInteractionBound || state.firstInteractionAttempted || !isAutoplayEnabled()) {
                return false;
            }

            const startFromInteraction = () => {
                document.removeEventListener("pointerdown", startFromInteraction);
                document.removeEventListener("keydown", startFromInteraction);
                state.firstInteractionBound = false;
                this.startAutoplay().catch(error => {
                    console.warn("Ghost Radio autostart failed", error);
                    state.autostartBlocked = true;
                    setStatus("CLICK TO START");
                });
            };

            document.addEventListener("pointerdown", startFromInteraction, { passive: true });
            document.addEventListener("keydown", startFromInteraction);
            state.firstInteractionBound = true;
            return true;
        },

        next(options = {}) {
            if (showPlayback) return;
            if (!state.playlist.length) return;
            const wasPlaying = state.isPlaying || options.fromEnded;
            const atEnd = state.currentIndex >= state.playlist.length - 1;
            if (atEnd && !(state.channel && state.channel.loop)) {
                this.pause();
                return;
            }
            const nextIndex = atEnd ? 0 : state.currentIndex + 1;
            if (wasPlaying) {
                state.resumeAfterSourceChange = true;
            }
            setAudioSource(nextIndex);
            if (wasPlaying) {
                setTimeout(() => this.play(), 0);
            }
        },

        previous() {
            if (showPlayback) return;
            if (!state.playlist.length) return;
            const wasPlaying = state.isPlaying;
            const previousIndex = state.currentIndex <= 0 ? state.playlist.length - 1 : state.currentIndex - 1;
            if (wasPlaying) {
                state.resumeAfterSourceChange = true;
            }
            setAudioSource(previousIndex);
            if (wasPlaying) {
                setTimeout(() => this.play(), 0);
            }
        },

        nextChannel() {
            if (state.channels.length <= 1) {
                setStatus("ONE CHANNEL");
                updatePlaybackView();
                return false;
            }
            const current = state.channelId || state.defaultChannel;
            const index = Math.max(0, state.channels.findIndex(channel => channel.id === current));
            const next = state.channels[(index + 1) % state.channels.length];
            const shouldResume = state.isPlaying;
            return this.loadChannel(next.id).then(() => {
                if (shouldResume) return this.play();
                return true;
            });
        },

        previousChannel() {
            if (state.channels.length <= 1) {
                setStatus("ONE CHANNEL");
                updatePlaybackView();
                return false;
            }
            const current = state.channelId || state.defaultChannel;
            const index = Math.max(0, state.channels.findIndex(channel => channel.id === current));
            const previous = state.channels[(index - 1 + state.channels.length) % state.channels.length];
            const shouldResume = state.isPlaying;
            return this.loadChannel(previous.id).then(() => {
                if (shouldResume) return this.play();
                return true;
            });
        },

        getState() {
            return {
                channel: state.channel,
                playlist: state.playlist.slice(),
                channels: state.channels.slice(),
                currentIndex: state.currentIndex,
                isPlaying: state.isPlaying,
                volume: state.volume,
                effectiveVolume: state.volume * state.duckGain,
                muted: state.muted,
                duckGain: state.duckGain,
                duckRequests: state.duckRequests.size,
                autostartBlocked: state.autostartBlocked,
                showActive: !!showPlayback,
                showAudioBlocked: !!(showPlayback && (showPlayback.blocked || !showPlayback.allowed))
            };
        }
    };

    window.GhostRadio = GhostRadio;

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => GhostRadio.armFirstInteractionAutostart(), { once: true });
    } else {
        GhostRadio.armFirstInteractionAutostart();
    }

    window.createGhostHackRadioApp = function createGhostHackRadioApp() {
        const existing = document.querySelector('.terminal[data-app="ghost-radio"]');
        if (existing) {
            if (typeof bringWindowToFront === "function") bringWindowToFront(existing);
            return;
        }

        const term = document.createElement('div');
        term.className = 'terminal ghost-radio-window';
        term.dataset.app = 'ghost-radio';
        term.dataset.appTitle = 'Ghost Hack Radio';
        term.dataset.appIcon = '\u{1F4FB}';
        const pos = typeof findAvailablePosition === "function"
            ? findAvailablePosition(520, 300)
            : { top: 40, left: 40 };
        term.style.top = `${pos.top}px`;
        term.style.left = `${pos.left}px`;
        term.innerHTML = `
            <div class="title-bar">Ghost Hack Radio <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
            <div class="ghost-radio-shell">
                <div class="ghost-radio-topline">
                    <span class="ghost-radio-status" data-radio-status>SIGNAL BOOT</span>
                    <span class="ghost-radio-count" data-radio-count>0 / 0</span>
                </div>
                <div class="ghost-radio-display">
                    <h2 data-radio-channel>Ghost Hack Radio</h2>
                    <div class="ghost-radio-track" data-radio-track>Loading channel...</div>
                </div>
                <div class="ghost-radio-eq-wrap">
                    <div class="ghost-radio-eq" aria-hidden="true">
                        <span></span><span></span><span></span><span></span><span></span>
                        <span></span><span></span><span></span><span></span><span></span>
                    </div>
                </div>
                <div class="ghost-radio-progress" aria-hidden="true">
                    <span data-radio-progress-fill></span>
                </div>
                <div class="ghost-radio-time" data-radio-time>0:00 / --:--</div>
                <div class="ghost-radio-controls">
                    <button type="button" data-radio-action="previous" title="Poprzedni kanal" aria-label="Poprzedni kanal">\u23EE</button>
                    <button type="button" data-radio-action="play" title="Play" aria-label="Play">\u25B6</button>
                    <button type="button" data-radio-action="pause" title="Pause" aria-label="Pause" disabled>\u23F8</button>
                    <button type="button" data-radio-action="next" title="Nastepny kanal" aria-label="Nastepny kanal">\u23ED</button>
                    <button type="button" data-radio-action="mute" title="Mute" aria-label="Mute">\u{1F507}</button>
                </div>
                <label class="ghost-radio-volume">
                    <span>Volume</span>
                    <input type="range" min="0" max="100" value="80" step="1" data-radio-volume>
                    <b data-radio-volume-value>80%</b>
                </label>
                <p class="ghost-radio-note"><span>MP3</span><code data-radio-source>/static/mp3/radio/channel/${escapeRadioHTML(DEFAULT_RADIO_CHANNEL)}/</code></p>
            </div>
        `;
        document.body.appendChild(term);
        term.querySelector('.close-btn').addEventListener('click', () => term.remove());
        if (typeof makeDraggable === "function") {
            makeDraggable(term);
        }
        if (typeof bringWindowToFront === "function") {
            bringWindowToFront(term);
        }
        GhostRadio.init(term).catch(error => {
            console.warn("Ghost Radio init failed", error);
            setStatus("SIGNAL LOST");
            updateTrackView();
        });
    };
})();
