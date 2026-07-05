const RADIO_BASE_PATH = "/static/mp3/radio/channel";
const DEFAULT_RADIO_CHANNEL = "ghost_streem_1";

(function initGhostRadioModule() {
    const state = {
        basePath: RADIO_BASE_PATH,
        defaultChannel: DEFAULT_RADIO_CHANNEL,
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
        firstInteractionBound: false,
        firstInteractionAttempted: false,
        autostartBlocked: false,
        elements: {}
    };

    function escapeRadioHTML(value) {
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({
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

    function currentTrack() {
        return state.playlist[state.currentIndex] || null;
    }

    function setStatus(text) {
        if (state.elements.status) {
            state.elements.status.textContent = text || "SIGNAL IDLE";
        }
    }

    function isAutoplayEnabled() {
        try {
            return window.localStorage?.getItem("ghost_radio_autoplay") !== "0";
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
        if (state.elements.nextButton) state.elements.nextButton.disabled = state.playlist.length < 2;
        if (state.elements.previousButton) state.elements.previousButton.disabled = state.playlist.length < 2;
        updateVolumeView();
    }

    function updateTrackView() {
        const track = currentTrack();
        const channelName = state.channel?.name || "Ghost Hack Radio";
        const trackTitle = track?.title || "Brak utworu";
        const position = state.playlist.length ? `${state.currentIndex + 1} / ${state.playlist.length}` : "0 / 0";

        if (state.elements.channelName) state.elements.channelName.textContent = channelName;
        if (state.elements.trackTitle) state.elements.trackTitle.textContent = trackTitle;
        if (state.elements.trackCount) state.elements.trackCount.textContent = position;
        updatePlaybackView();
    }

    function updateProgress() {
        const audio = state.audio;
        const duration = Number.isFinite(audio?.duration) && audio.duration > 0 ? audio.duration : 0;
        const current = Number.isFinite(audio?.currentTime) ? audio.currentTime : 0;
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
        if (!state.audio || !state.playlist.length) return;
        state.currentIndex = Math.max(0, Math.min(index, state.playlist.length - 1));
        const track = currentTrack();
        state.audio.src = track.url;
        state.audio.load();
        updateTrackView();
        updateProgress();
    }

    function syncAudioSettings() {
        if (!state.audio) return;
        state.audio.volume = Math.max(0, Math.min(1, Number(state.volume) || 0));
        state.audio.muted = Boolean(state.muted);
        updateVolumeView();
    }

    function updateVolumeView() {
        if (state.elements.volumeInput) {
            state.elements.volumeInput.value = String(Math.round((state.volume || 0) * 100));
        }
        if (state.elements.volumeValue) {
            state.elements.volumeValue.textContent = `${Math.round((state.volume || 0) * 100)}%`;
        }
        if (state.elements.muteButton) {
            state.elements.muteButton.textContent = state.muted ? "Unmute" : "Mute";
            state.elements.muteButton.classList.toggle("is-active", state.muted);
        }
    }

    function bindAudioEvents() {
        if (!state.audio || state.audio.dataset.ghostRadioBound === "1") return;
        state.audio.dataset.ghostRadioBound = "1";
        state.audio.addEventListener("ended", () => {
            GhostRadio.next({ fromEnded: true });
        });
        state.audio.addEventListener("timeupdate", updateProgress);
        state.audio.addEventListener("loadedmetadata", updateProgress);
        state.audio.addEventListener("play", () => {
            state.isPlaying = true;
            setStatus("SIGNAL ONLINE");
            updatePlaybackView();
        });
        state.audio.addEventListener("pause", () => {
            state.isPlaying = false;
            setStatus("SIGNAL PAUSED");
            updatePlaybackView();
        });
        state.audio.addEventListener("error", () => {
            setStatus("SIGNAL ERROR");
        });
        state.audio.addEventListener("volumechange", () => {
            state.muted = Boolean(state.audio.muted);
            state.volume = state.audio.volume;
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
            volumeValue: root.querySelector("[data-radio-volume-value]")
        };

        if (state.elements.playButton) state.elements.playButton.addEventListener("click", () => GhostRadio.play());
        if (state.elements.pauseButton) state.elements.pauseButton.addEventListener("click", () => GhostRadio.pause());
        if (state.elements.nextButton) state.elements.nextButton.addEventListener("click", () => GhostRadio.next());
        if (state.elements.previousButton) state.elements.previousButton.addEventListener("click", () => GhostRadio.previous());
        if (state.elements.muteButton) state.elements.muteButton.addEventListener("click", () => GhostRadio.mute());
        if (state.elements.volumeInput) {
            state.elements.volumeInput.addEventListener("input", (event) => {
                GhostRadio.setVolume(Number(event.target.value) / 100);
            });
        }
    }

    const GhostRadio = {
        init(root = document) {
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
            return this.loadChannel(state.defaultChannel);
        },

        async loadChannel(id = state.defaultChannel) {
            const channelId = String(id || state.defaultChannel);
            setStatus("SIGNAL LOADING");
            const response = await fetch(`${channelPath(channelId)}/meta.channel`, { cache: "no-store" });
            if (!response.ok) {
                setStatus("SIGNAL LOST");
                throw new Error(`Ghost Radio channel load failed: ${response.status}`);
            }
            const channel = await response.json();
            if (Number(channel.schema) !== 1) {
                setStatus("BAD SCHEMA");
                throw new Error("Unsupported Ghost Radio channel schema.");
            }
            const tracks = Array.isArray(channel.tracks) ? channel.tracks : [];
            state.channel = channel;
            state.channelId = channelId;
            state.playlist = tracks
                .filter(track => track && track.file)
                .map((track, index) => ({
                    title: track.title || `Track ${index + 1}`,
                    file: track.file,
                    url: trackUrl(channelId, track.file)
                }));
            state.currentIndex = 0;
            setAudioSource(0);
            setStatus(state.playlist.length ? "SIGNAL READY" : "NO TRACKS");
            updateTrackView();
            syncAudioSettings();
            return state.channel;
        },

        async play() {
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
            return state.volume;
        },

        async startAutoplay() {
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
            if (!state.playlist.length) return;
            const wasPlaying = state.isPlaying || options.fromEnded;
            const atEnd = state.currentIndex >= state.playlist.length - 1;
            if (atEnd && !state.channel?.loop) {
                this.pause();
                return;
            }
            const nextIndex = atEnd ? 0 : state.currentIndex + 1;
            setAudioSource(nextIndex);
            if (wasPlaying) {
                this.play();
            }
        },

        previous() {
            if (!state.playlist.length) return;
            const wasPlaying = state.isPlaying;
            const previousIndex = state.currentIndex <= 0 ? state.playlist.length - 1 : state.currentIndex - 1;
            setAudioSource(previousIndex);
            if (wasPlaying) {
                this.play();
            }
        },

        getState() {
            return {
                channel: state.channel,
                playlist: state.playlist.slice(),
                currentIndex: state.currentIndex,
                isPlaying: state.isPlaying,
                volume: state.volume,
                muted: state.muted,
                autostartBlocked: state.autostartBlocked
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
                    <button type="button" data-radio-action="previous">Prev</button>
                    <button type="button" data-radio-action="play">Play</button>
                    <button type="button" data-radio-action="pause" disabled>Pause</button>
                    <button type="button" data-radio-action="next">Next</button>
                    <button type="button" data-radio-action="mute">Mute</button>
                </div>
                <label class="ghost-radio-volume">
                    <span>Volume</span>
                    <input type="range" min="0" max="100" value="80" step="1" data-radio-volume>
                    <b data-radio-volume-value>80%</b>
                </label>
                <p class="ghost-radio-note"><span>Source</span><code>/static/mp3/radio/channel/${escapeRadioHTML(DEFAULT_RADIO_CHANNEL)}/meta.channel</code></p>
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
