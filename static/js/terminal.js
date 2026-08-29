let terminalCount = 3;
let topZIndex = 1000;
let windowSequence = 0;
let toolbarLauncherApps = [];
const runningWindows = new Map();
let desktopSettings = { wallpaper: "", icon_positions: {}, auto_fullscreen: false, map_tile_scheme: "osm" };
let desktopSaveTimer = null;
let toolbarProfile = null;
let toolbarTargetFeedbackState = { targetKey: "", dotSignature: "", progress: 0 };
let gonnaWinRequestQueue = Promise.resolve();
const gonnaWinLifecycleStates = new Map();
const GONNA_WIN_LIFECYCLE_LIMIT = 128;
let toolbarTargetTruthRefreshing = false;
let toolbarTargetHackedEffect = null;
let toolbarTargetHackedEffectTimer = null;
let toolbarTargetLocalOverride = null;
const toolbarTargetHackedEffectKeys = new Set();
let desktopSessionActive = true;
let desktopSessionTeardownComplete = false;
let userProfileRequestPromise = null;
let desktopRenderedApps = [];
const recentApplicationWindowLaunches = new Map();
const recentLaunchQueueReceipts = new Map();
const notifiedOperationIds = new Map();
const APP_WINDOW_LAUNCH_DEDUPE_MS = 30000;
const LAUNCH_QUEUE_RECEIPT_TTL_MS = 10 * 60 * 1000;
const NOTIFIED_OPERATION_TTL_MS = 30000;
const TOOLBAR_TARGET_LOCAL_OVERRIDE_TTL_MS = 3 * 60 * 1000;
const fileManagerInstances = new Map();
const cybernerDeltaClients = new Set();
const ghostExchangeDeltaViews = new Set();
let desktopLastSafeMode = null;
let playerHackAccessState = null;
let playerHackAccessTimer = null;
let stateDeltaVersion = 0;
let stateDeltaPollInFlight = false;
let stateDeltaSfxLive = false;
let stateDeltaSfxCatchup = true;
let stateDeltaSfxPlaybackAllowed = false;
let systemMessageSfxLive = false;
let systemMessageSfxCatchup = true;
let systemMessagesPollInFlight = false;
let launchQueuePollInFlight = false;
let systemMessagesPollInterval = null;
let stateDeltaStartTimer = null;
let stateDeltaPollInterval = null;
let launchQueuePollTimer = null;
const cybernerSfxChannelCooldowns = new Map();
const processedDeltaKeys = new Set();
const recentLaunchQueueApps = new Map();
const STATE_DELTA_POLL_INTERVAL_MS = 4000;
const DESKTOP_BACKGROUND_FETCH_TIMEOUT_MS = 8000;
const STATE_DELTA_FETCH_TIMEOUT_MS = 30000;
const LAUNCH_QUEUE_FETCH_TIMEOUT_MS = 12000;

function teardownDesktopForInvalidatedSession() {
    if (desktopSessionTeardownComplete) return false;
    desktopSessionTeardownComplete = true;
    desktopSessionActive = false;

    // Do not let an idempotency key survive an authoritative identity change.
    // session_generation.js clears all user-scoped sessionStorage as a second
    // line of defence; this explicit cleanup also covers isolated consumers of
    // the desktop teardown hook.
    clearWalletTransferActionKey();

    clearTimeout(desktopSaveTimer);
    desktopSaveTimer = null;
    clearTimeout(toolbarTargetHackedEffectTimer);
    toolbarTargetHackedEffectTimer = null;
    clearInterval(playerHackAccessTimer);
    playerHackAccessTimer = null;
    clearInterval(systemMessagesPollInterval);
    systemMessagesPollInterval = null;
    clearTimeout(stateDeltaStartTimer);
    stateDeltaStartTimer = null;
    clearInterval(stateDeltaPollInterval);
    stateDeltaPollInterval = null;
    clearTimeout(launchQueuePollTimer);
    launchQueuePollTimer = null;

    toolbarProfile = null;
    toolbarTargetLocalOverride = null;
    toolbarTargetHackedEffect = null;
    toolbarTargetHackedEffectKeys.clear();
    userProfileRequestPromise = null;
    gonnaWinRequestQueue = Promise.resolve();
    gonnaWinLifecycleStates.clear();
    stateDeltaPollInFlight = false;
    systemMessagesPollInFlight = false;
    launchQueuePollInFlight = false;
    stateDeltaSfxLive = false;
    stateDeltaSfxCatchup = true;
    stateDeltaSfxPlaybackAllowed = false;
    systemMessageSfxLive = false;
    systemMessageSfxCatchup = true;

    processedDeltaKeys.clear();
    cybernerSfxChannelCooldowns.clear();
    recentApplicationWindowLaunches.clear();
    recentLaunchQueueReceipts.clear();
    recentLaunchQueueApps.clear();
    notifiedOperationIds.clear();
    fileManagerInstances.clear();
    cybernerDeltaClients.clear();
    ghostExchangeDeltaViews.clear();
    window.__appFlowTraceState?.clear?.();
    window.__systemToastDedupe?.clear?.();

    runningWindows.forEach(win => win?.remove?.());
    runningWindows.clear();
    document.querySelectorAll('.terminal, .app-window, .system-toast').forEach(node => node.remove());
    ["lore", "gameplay", "message", "system", "ui"].forEach(bus => {
        window.GameSfx?.stop?.(bus, { fade_ms: 40 });
    });
    return true;
}

window.addEventListener(
    "chaos:session-invalidated",
    teardownDesktopForInvalidatedSession,
    { once: true }
);
window.teardownDesktopForInvalidatedSession = teardownDesktopForInvalidatedSession;

function fetchDesktopBackground(resource, options = {}, timeoutMs = DESKTOP_BACKGROUND_FETCH_TIMEOUT_MS) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    const requestOptions = Object.assign({}, options, { signal: controller.signal });
    return fetch(resource, requestOptions).finally(() => clearTimeout(timer));
}

function isExpectedFetchAbort(err) {
    return Boolean(err && err.name === "AbortError");
}
const STATE_DELTA_LIMIT = 100;
const STATE_DELTA_DEFAULT_RECOVERY_SCOPES = ["wallet", "storage", "apps", "mail", "ghost_exchange", "map", "territory", "incident", "ghostnetwork"];
const CYBERNER_THREAD_REFRESH_INTERVAL_MS = 10000;
const APP_TERMINAL_AUTO_CLOSE_MS = 5000;
window.APP_FLOW_TRACE = window.APP_FLOW_TRACE !== false;
window.HACK_FLOW_DEBUG = window.HACK_FLOW_DEBUG === true;
window.BLACKNET_CTA_DEBUG = window.BLACKNET_CTA_DEBUG === true;
window.__appFlowTraceState = window.__appFlowTraceState || new Map();
window.__pendingApplicationLaunchContext = null;

function getCurrentAppFlowId(fallback = "") {
    return String(fallback || window.__lastHackFlowId || "manual").trim() || "manual";
}

function appFlowTrace(flowId, step, details = {}) {
    if (!window.APP_FLOW_TRACE) return;
    const key = getCurrentAppFlowId(flowId);
    const now = performance.now();
    let state = window.__appFlowTraceState.get(key);
    if (!state) {
        state = { start: now, last: now };
        window.__appFlowTraceState.set(key, state);
    }
    const deltaMs = Math.round(now - state.last);
    const totalMs = Math.round(now - state.start);
    state.last = now;
    const payload = {
        ...details,
        delta_ms: deltaMs,
        total_ms: totalMs,
        ts: new Date().toISOString()
    };
    console.info(`[APP_FLOW ${key}] ${step} +${deltaMs}ms total=${totalMs}ms`, payload);
}

window.appFlowTrace = appFlowTrace;

function safeHttpHeaderValue(value) {
    try {
        return encodeURIComponent(String(value || "")).slice(0, 500);
    } catch (_err) {
        return String(value || "").replace(/[^\x20-\x7E]/g, "?").slice(0, 500);
    }
}

const DESKTOP_WALLPAPER_CLASSES = [
    "wall-1", "wall-2", "wall-3",
    "wall-chaos-green", "wall-chaos-blue", "wall-chaos-red", "wall-chaos-amber", "wall-chaos-violet"
];
let chaosFullscreenListenersBound = false;

const bootLoader = {
    overlay: document.getElementById('boot-preloader'),
    fill: document.getElementById('boot-progress-fill'),
    status: document.getElementById('boot-status'),
    log: document.getElementById('boot-log'),
    timer: null,
    active: true
};

const BOOT_FAKE_LOGS = [
    "sys_inst --run",
    "mount /net/ghost_bus",
    "reading sectors: 0x4A-0x9F",
    "decrypting local profile shard",
    "checking spoofed hostname",
    "syncing app manifest",
    "probing wallet ledger",
    "restoring desktop coordinates",
    "warming map cache",
    "binding terminal pipes",
    "loading googolplex index",
    "install with caution",
    "loading neural interface",
    "connecting quantum relay",
    "opening darknet tunnel",
    "verifying identity mask",
    "patching memory allocator",
    "loading encrypted registry",
    "checking entropy pool",
    "scanning local devices",
    "initializing packet sniffer",
    "hooking network adapters",
    "injecting runtime modules",
    "loading signal decoder",
    "rebuilding routing table",
    "indexing hidden storage",
    "synchronizing satellite clock",
    "connecting ghost exchange",
    "validating crypto keys",
    "loading biometric bypass",
    "resolving anonymous routes",
    "decrypting archive fragments",
    "starting telemetry daemon",
    "flushing event queue",
    "building world topology",
    "calibrating intrusion sensors",
    "loading exploit database",
    "checking firmware integrity",
    "unlocking secure sandbox",
    "mounting encrypted volumes",
    "generating session fingerprint",
    "replaying cached transactions",
    "loading threat signatures",
    "connecting relay nodes",
    "starting stealth engine",
    "initializing cyberpanel core",
    "building navigation mesh",
    "mapping surveillance network",
    "loading player profile",
    "system ready"
];

function cycleBootLog() {
    if (!bootLoader.overlay || !bootLoader.log || !bootLoader.active) return;
    bootLoader.log.textContent = BOOT_FAKE_LOGS[Math.floor(Math.random() * BOOT_FAKE_LOGS.length)];
    const delay = 180 + Math.floor(Math.random() * 720);
    bootLoader.timer = setTimeout(cycleBootLog, delay);
}

function setBootProgress(percent, message) {
    if (!bootLoader.overlay) return;
    const value = Math.max(4, Math.min(100, Number(percent) || 4));
    if (bootLoader.fill) bootLoader.fill.style.width = `${value}%`;
    if (bootLoader.status) bootLoader.status.textContent = message || "Ładowanie systemu...";
}

function finishBootLoader(message = "System gotowy.") {
    setBootProgress(100, message);
    if (!bootLoader.overlay) return;
    bootLoader.active = false;
    clearTimeout(bootLoader.timer);
    if (bootLoader.log) bootLoader.log.textContent = "handoff to desktop shell";
    setTimeout(() => {
        bootLoader.overlay.classList.add('done');
        setTimeout(() => bootLoader.overlay.remove(), 700);
    }, 450);
}

cycleBootLog();

const desktopLoadingState = {
    active: new Map(),
    seq: 0,
    showTimer: null,
    slowTimer: null,
    visible: false,
    element: null,
    text: null
};

function ensureDesktopLoadingStatus() {
    if (desktopLoadingState.element) {
        return desktopLoadingState.element;
    }
    const status = document.createElement('div');
    status.className = 'desktop-sync-status';
    status.setAttribute('role', 'status');
    status.setAttribute('aria-live', 'polite');
    status.innerHTML = `
        <span class="desktop-sync-status__spinner" aria-hidden="true"></span>
        <span class="desktop-sync-status__text">Sprawdzam system...</span>
    `;
    document.body.appendChild(status);
    desktopLoadingState.element = status;
    desktopLoadingState.text = status.querySelector('.desktop-sync-status__text');
    return status;
}

function updateDesktopLoadingStatus(message) {
    const status = ensureDesktopLoadingStatus();
    if (desktopLoadingState.text) {
        desktopLoadingState.text.textContent = message || 'Sprawdzam system...';
    }
    status.classList.add('is-visible');
    desktopLoadingState.visible = true;
}

function beginDesktopLoading(message) {
    const token = `desktop-load-${++desktopLoadingState.seq}`;
    desktopLoadingState.active.set(token, message || 'Sprawdzam system...');
    clearTimeout(desktopLoadingState.showTimer);
    clearTimeout(desktopLoadingState.slowTimer);
    desktopLoadingState.showTimer = setTimeout(() => {
        const latest = Array.from(desktopLoadingState.active.values()).pop();
        if (latest) {
            updateDesktopLoadingStatus(latest);
        }
    }, 280);
    desktopLoadingState.slowTimer = setTimeout(() => {
        if (desktopLoadingState.active.size > 0) {
            updateDesktopLoadingStatus('Sieć przeciążona...');
        }
    }, 2000);
    return token;
}

function endDesktopLoading(token) {
    if (token) {
        desktopLoadingState.active.delete(token);
    }
    if (desktopLoadingState.active.size > 0) {
        const latest = Array.from(desktopLoadingState.active.values()).pop();
        if (desktopLoadingState.visible && latest) {
            updateDesktopLoadingStatus(latest);
        }
        return;
    }
    clearTimeout(desktopLoadingState.showTimer);
    clearTimeout(desktopLoadingState.slowTimer);
    if (desktopLoadingState.element) {
        desktopLoadingState.element.classList.remove('is-visible');
    }
    desktopLoadingState.visible = false;
}

const SYSTEM_ICON_LIBRARY = [
    '\u{1F6E0}\uFE0F', '\u2328\uFE0F', '\u{1FA9F}', '\u{1F518}', '\u{1F9E0}',
    '\u{1F4A5}', '\u{1F50D}', '\u{1F512}', '\u{1F513}', '\u{1F510}',
    '\u{1F6E1}\uFE0F', '\u{1F4E1}', '\u{1F4F6}', '\u{1F4BB}', '\u{1F5A5}\uFE0F',
    '\u{1F5A7}\uFE0F', '\u{1F4BE}', '\u{1F4BF}', '\u{1F4C1}', '\u{1F4C2}',
    '\u{1F4E6}', '\u{1F4E8}', '\u{1F4AC}', '\u{1F310}', '\u{1F5FA}\uFE0F',
    '\u{1F4CD}', '\u{1F3AF}', '\u{1F52C}', '\u{1F9EA}', '\u{1F9EC}',
    '\u2699\uFE0F', '\u{1F527}', '\u{1F528}', '\u{1F9F2}', '\u{1F9F0}',
    '\u{1F4A3}', '\u26A1', '\u{1F525}', '\u2744\uFE0F', '\u{1F300}',
    '\u{1F441}\uFE0F', '\u{1F575}\uFE0F', '\u{1F464}', '\u{1F465}', '\u{1F977}',
    '\u{1F916}', '\u{1F47E}', '\u{1F47B}', '\u{1F680}', '\u{1F6F8}',
    '\u{1F3CD}\uFE0F', '\u{1F697}', '\u{1F69A}', '\u{1F6A8}', '\u{1F6A6}',
    '\u{1F4B0}', '\u{1FA99}', '\u{1F4B3}', '\u{1F4C8}', '\u{1F4C9}',
    '\u2705', '\u274C', '\u26A0\uFE0F', '\u2753', '\u2139\uFE0F',
    '\u{1F7E2}', '\u{1F534}', '\u{1F535}', '\u{1F7E1}', '\u{1F7E3}',
    '\u{1F539}', '\u{1F538}', '\u{1F53A}', '\u{1F53B}', '\u{1F4AB}'
];

const CYBERNER_ICON_LIBRARY = {
    world: { icon: '\u{1F310}', label: 'WORLD' },
    group: { icon: '\u{1F310}', label: 'WORLD' },
    friends: { icon: '\u{1F465}', label: 'ZNAJOMI' },
    clan: { icon: '\u{1F6E1}\uFE0F', label: 'KLAN' },
    contact: { icon: '\u{1F464}', label: 'Kontakt' },
    friend: { icon: '\u{1F465}', label: 'Znajomy' },
    stranger: { icon: '\u{1F575}\uFE0F', label: 'Nieznany kontakt' },
    request: { icon: '\u{1F4E8}', label: 'Prosba o kontakt' },
    ai: { icon: '\u{1F916}', label: 'AI Central' },
    ghost_exchange: { icon: '\u{1F4B0}', label: 'Ghost Exchange' },
    system: { icon: '\u26A0\uFE0F', label: 'System' },
    mission: { icon: '\u{1F3AF}', label: 'Misje' },
    warning: { icon: '\u26A0\uFE0F', label: 'Ostrzezenie' },
    npc: { icon: '\u{1F464}', label: 'NPC' },
    faction: { icon: '\u{1F3F4}', label: 'Frakcja' },
    marketplace: { icon: '\u{1F4E6}', label: 'Marketplace' },
    blacknet: { icon: '\u{1F4E1}', label: 'BlackNet' },
    drone: { icon: '\u{1F6F8}', label: 'Dron' },
    bike: { icon: '\u{1F3CD}\uFE0F', label: 'Motocykl' },
    own: { icon: '\u2705', label: 'Ty' },
    unknown: { icon: '\u2753', label: 'Nieznane zrodlo' }
};

const CYBERNER_NOTIFICATION_LIBRARY = {
    world: { icon: '\u{1F310}', label: 'WORLD', text: 'Nowa aktywnosc.' },
    friends: { icon: '\u{1F465}', label: 'ZNAJOMI', text: 'Nowa wiadomosc.' },
    clan: { icon: '\u{1F6E1}\uFE0F', label: 'KLAN', text: 'Nowa wiadomosc.' },
    player: { icon: '\u{1F464}', label: 'Cyberner', text: 'Nowa wiadomosc.' },
    system: { icon: '\u26A0\uFE0F', label: 'System', text: 'Nowa wiadomosc.' },
    ai: { icon: '\u{1F916}', label: 'AI Central', text: 'Nowa wiadomosc.' },
    ghost_exchange: { icon: '\u{1F4B0}', label: 'Ghost Exchange', text: 'Nowa wiadomosc.' },
    mission: { icon: '\u{1F3AF}', label: 'Misje', text: 'Nowa wiadomosc.' },
    marketplace: { icon: '\u{1F4E6}', label: 'Marketplace', text: 'Nowa wiadomosc.' },
    blacknet: { icon: '\u{1F4E1}', label: 'BlackNet', text: 'Nowa wiadomosc.' },
    npc: { icon: '\u{1F464}', label: 'NPC', text: 'Nowa wiadomosc.' },
    unknown: { icon: '\u2753', label: 'Cyberner', text: 'Nowa wiadomosc.' }
};

window.activeCybernerThread = window.activeCybernerThread || null;
window.pendingCybernerThread = window.pendingCybernerThread || null;

const desktopApps = [
    { icon: '\u{1F5A5}\uFE0F', label: 'Terminal', action: createTerminal },
    { icon: '\u{1F5FA}\uFE0F', label: 'Mapa', action: createMap },
    { icon: '\u{1F310}', label: 'Browser', action: createBrowser },
    { icon: '\u2699\uFE0F', label: 'Ustawienia', action: createSettings },
    { icon: '\u{1F464}', label: 'Profil', action: createProfile },
    { icon: '\u{1F4C1}', label: 'Pliki', action: createFileManager },
    { icon: '\u{1F4E8}', label: 'Cyberner', action: createEmailClient },
    { id: 'ghost_hack_radio', icon: '\u{1F4FB}', label: 'Ghost Hack Radio', action: () => window.createGhostHackRadioApp && window.createGhostHackRadioApp() },
    { icon: '\u{1F4B0}', label: 'Wallet HC', action: openWalletApp }
];

const devBugReporterApp = {
    id: 'dev_bug_reporter',
    icon: '\u{1F41E}',
    label: 'Dev Bug Reporter',
    action: createDevBugReporterApp
};

const desktop = document.getElementById('desktop-icons');
const iconSpacing = 100; // odstęp w pionie
const MOBILE_SAFE_MODE_QUERY = '(max-width: 900px), (max-height: 700px)';
const MOBILE_DESKTOP_ICON_ORDER = ['wallet_hc', 'pliki', 'mapa', 'browser', 'ghost_hack_radio', 'ustawienia', 'cyberner', 'terminal', 'dev_bug_reporter', 'profil'];
const MOBILE_DESKTOP_ICON_KEYS = new Set(MOBILE_DESKTOP_ICON_ORDER);

function isMobileSafeMode() {
    return window.matchMedia && window.matchMedia(MOBILE_SAFE_MODE_QUERY).matches;
}

function applyMobileSafeModeToWindow(win) {
    if (!win || !win.classList || (!win.classList.contains('terminal') && !win.classList.contains('app-window'))) return;
    if (isMobileSafeMode()) {
        win.dataset.mobileSafeMode = 'true';
        win.style.transform = 'none';
        win.style.resize = 'none';
        return;
    }
    delete win.dataset.mobileSafeMode;
}

function makeDraggable(el) {
    if (!el || el.dataset.draggableBound === '1') return;
    el.dataset.draggableBound = '1';

    registerWindowInTaskbar(el);
    applyMobileSafeModeToWindow(el);
    bringWindowToFront(el);

    const titleBar = el.querySelector('.title-bar') || el;
    const dragHandle = el.querySelector('[data-window-drag-handle]') || titleBar;
    let isDragging = false;
    let offsetX = 0;
    let offsetY = 0;

    const finishDragging = () => {
        if (!isDragging) return;
        isDragging = false;
        document.body.style.userSelect = 'auto';
    };

    dragHandle.addEventListener('mousedown', (e) => {
        if (e.target.closest('.close-btn, button, input, textarea, select, a')) return;
        if (isMobileSafeMode()) return;

        isDragging = true;
        offsetX = e.clientX - el.offsetLeft;
        offsetY = e.clientY - el.offsetTop;
        document.body.style.userSelect = 'none';
        bringWindowToFront(el);
        e.preventDefault();
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        el.style.left = `${e.clientX - offsetX}px`;
        el.style.top = `${e.clientY - offsetY}px`;
    });

    window.addEventListener('mouseup', () => {
        finishDragging();
    });
    window.addEventListener('blur', finishDragging);

    el.addEventListener('mousedown', () => bringWindowToFront(el));
}

function applyMobileSafeModeToOpenWindows() {
    document.querySelectorAll('.terminal, .app-window').forEach(applyMobileSafeModeToWindow);
}

function getDesktopIconKey(app) {
    return String(app.id || app.label || app.name || 'app').toLowerCase().replace(/[^a-z0-9_-]+/g, '_');
}

function isMobileDesktopIcon(app) {
    return MOBILE_DESKTOP_ICON_KEYS.has(getDesktopIconKey(app));
}

function mobileDesktopIconRank(app) {
    const index = MOBILE_DESKTOP_ICON_ORDER.indexOf(getDesktopIconKey(app));
    return index >= 0 ? index : MOBILE_DESKTOP_ICON_ORDER.length;
}

function getSystemDesktopApps(profile = null) {
    const apps = [...desktopApps];
    if ((profile && profile.dev_mode) || isMobileSafeMode()) {
        apps.push(devBugReporterApp);
    }
    return apps;
}

function readStoredAutoFullscreenSetting() {
    try {
        const stored = window.localStorage?.getItem("chaos_auto_fullscreen");
        if (stored === "1") return true;
        if (stored === "0") return false;
    } catch (err) {
        console.warn("Nie udalo sie odczytac ustawienia fullscreen:", err);
    }
    return null;
}

function resolveAutoFullscreenSetting(settings = {}) {
    const stored = readStoredAutoFullscreenSetting();
    if (stored !== null) return stored;
    return settings.auto_fullscreen === true;
}

function applyDesktopSettings(settings = {}) {
    const autoFullscreen = resolveAutoFullscreenSetting(settings);
    desktopSettings = {
        wallpaper: settings.wallpaper || "",
        icon_positions: settings.icon_positions || {},
        auto_fullscreen: autoFullscreen,
        map_tile_scheme: settings.map_tile_scheme || "osm"
    };
    setAutoFullscreenEnabled(desktopSettings.auto_fullscreen);
    if (settings.auto_fullscreen !== desktopSettings.auto_fullscreen && desktopSessionActive) {
        postDesktopSettings({ auto_fullscreen: desktopSettings.auto_fullscreen });
    }
    if (typeof syncChaosFullscreenRuntime === "function") {
        syncChaosFullscreenRuntime();
    }
    document.body.classList.remove(...DESKTOP_WALLPAPER_CLASSES);
    if (desktopSettings.wallpaper) {
        document.body.classList.add(desktopSettings.wallpaper);
    }
}

function collectDesktopIconPositions() {
    if (isMobileSafeMode()) {
        return desktopSettings.icon_positions || {};
    }
    const positions = {};
    document.querySelectorAll('#desktop-icons .icon[data-icon-key]').forEach(icon => {
        const left = Math.round(icon.offsetLeft);
        const top = Math.round(icon.offsetTop);
        if (!Number.isFinite(left) || !Number.isFinite(top)) return;
        positions[icon.dataset.iconKey] = { left, top };
    });
    return positions;
}

function mergeDesktopSettings(partial = {}) {
    desktopSettings = {
        ...desktopSettings,
        ...partial,
        icon_positions: partial.icon_positions || desktopSettings.icon_positions || {}
    };
    return desktopSettings;
}

function postDesktopSettings(settings) {
    if (!desktopSessionActive) return Promise.resolve(null);
    return fetch('/api/profile/desktop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
        keepalive: true
    }).catch(err => console.warn("Nie udało się zapisać pulpitu:", err));
}

function sendDesktopSettingsBeacon(partial = {}) {
    if (!desktopSessionActive || !navigator.sendBeacon) return false;
    const settings = { ...desktopSettings, ...partial };
    try {
        const generation = window.ChaosSessionGeneration?.getState?.().generation || "";
        if (!generation) return false;
        const payload = JSON.stringify({
            ...settings,
            _session_generation: generation
        });
        return navigator.sendBeacon('/api/profile/desktop', new Blob([payload], { type: 'application/json' }));
    } catch (err) {
        console.warn("Nie udało się zapisać pulpitu beaconem:", err);
        return false;
    }
}

function currentSessionGenerationQuery() {
    const state = window.ChaosSessionGeneration?.getState?.() || {};
    const queryToken = state.query_token || state.generation || "";
    return queryToken
        ? `&_embedded=1&_session_generation=${encodeURIComponent(queryToken)}`
        : "&_embedded=1";
}

function authenticatedLogoutUrl() {
    const state = window.ChaosSessionGeneration?.getState?.() || {};
    const queryToken = state.query_token || state.generation || "";
    return queryToken
        ? `/logout?_session_generation=${encodeURIComponent(queryToken)}`
        : "/logout";
}

function reloadOpenMapWindowsForSettings() {
    document.querySelectorAll('.map-window').forEach(mapWindow => {
        const frame = mapWindow.querySelector('iframe.map-frame, iframe[src^="/map"]');
        if (!frame) return;
        mapWindow.classList.remove('map-frame-loaded');
        frame.addEventListener('load', () => {
            mapWindow.classList.add('map-frame-loaded');
        }, { once: true });
        frame.removeAttribute('src');
        requestAnimationFrame(() => {
            if (frame.isConnected) {
                frame.src = `/map?scheme=${encodeURIComponent(desktopSettings.map_tile_scheme || "osm")}&ts=${Date.now()}${currentSessionGenerationQuery()}`;
            }
        });
    });
}

function saveDesktopSettingsNow(partial = {}) {
    clearTimeout(desktopSaveTimer);
    return postDesktopSettings(mergeDesktopSettings(partial));
}

function saveDesktopSettings(partial = {}) {
    mergeDesktopSettings(partial);
    clearTimeout(desktopSaveTimer);
    desktopSaveTimer = setTimeout(() => {
        saveDesktopSettingsNow();
    }, 350);
}

function isGhostRadioAutoplayEnabled() {
    try {
        return window.localStorage?.getItem("ghost_radio_autoplay") !== "0";
    } catch (err) {
        return true;
    }
}

function setGhostRadioAutoplayEnabled(enabled) {
    try {
        window.localStorage?.setItem("ghost_radio_autoplay", enabled ? "1" : "0");
    } catch (err) {
        console.warn("Nie udalo sie zapisac ustawienia radia:", err);
    }
}

function isAutoFullscreenEnabled() {
    return resolveAutoFullscreenSetting(desktopSettings) === true;
}

function setAutoFullscreenEnabled(enabled) {
    desktopSettings.auto_fullscreen = enabled === true;
    try {
        window.localStorage?.setItem("chaos_auto_fullscreen", desktopSettings.auto_fullscreen ? "1" : "0");
    } catch (err) {
        console.warn("Nie udalo sie zapisac ustawienia fullscreen:", err);
    }
}

function requestChaosFullscreen() {
    if (!isAutoFullscreenEnabled() || document.fullscreenElement) return;
    const root = document.documentElement;
    if (!root || typeof root.requestFullscreen !== "function") return;
    root.requestFullscreen().catch(() => {});
}

function bindChaosFullscreenListeners() {
    if (chaosFullscreenListenersBound) return;
    window.addEventListener("pointerdown", requestChaosFullscreen, { passive: true });
    window.addEventListener("touchstart", requestChaosFullscreen, { passive: true });
    window.addEventListener("keydown", requestChaosFullscreen);
    chaosFullscreenListenersBound = true;
}

function unbindChaosFullscreenListeners() {
    if (!chaosFullscreenListenersBound) return;
    window.removeEventListener("pointerdown", requestChaosFullscreen);
    window.removeEventListener("touchstart", requestChaosFullscreen);
    window.removeEventListener("keydown", requestChaosFullscreen);
    chaosFullscreenListenersBound = false;
}

function syncChaosFullscreenRuntime() {
    if (isAutoFullscreenEnabled()) {
        bindChaosFullscreenListeners();
    } else {
        unbindChaosFullscreenListeners();
    }
}

syncChaosFullscreenRuntime();

window.addEventListener('beforeunload', () => {
    if (!desktop || !desktopSessionActive) return;
    if (isMobileSafeMode()) return;
    const settings = mergeDesktopSettings({ icon_positions: collectDesktopIconPositions() });
    sendDesktopSettingsBeacon(settings);
});

function renderDesktopIcons(apps, settings = desktopSettings) {
    if (!desktop) return;
    if (Array.isArray(apps)) {
        desktopRenderedApps = apps;
    }
    desktop.innerHTML = '';
    const iconHeight = 100;
    const topOffset = 10;
    const leftOffset = 10;
    const colSpacing = 100;
    const windowHeight = window.innerHeight;
    const maxPerColumn = Math.max(1, Math.floor((windowHeight - topOffset) / iconHeight));
    const savedPositions = (settings && settings.icon_positions) || {};
    const mobileMode = isMobileSafeMode();
    desktopLastSafeMode = mobileMode;
    const visibleApps = mobileMode
        ? apps.filter(isMobileDesktopIcon).sort((a, b) => mobileDesktopIconRank(a) - mobileDesktopIconRank(b))
        : apps;

    visibleApps.forEach((app, index) => {
        const icon = document.createElement('div');
        const key = getDesktopIconKey(app);
        icon.className = 'icon';
        icon.dataset.iconKey = key;
        icon.innerHTML = `<span style="font-size: 3rem">${app.icon}</span> ${app.label}`;

        const row = index % maxPerColumn;
        const col = Math.floor(index / maxPerColumn);
        const saved = mobileMode ? null : savedPositions[key];
        icon.style.top = `${Number.isFinite(Number(saved?.top)) ? Number(saved.top) : topOffset + row * iconHeight}px`;
        icon.style.left = `${Number.isFinite(Number(saved?.left)) ? Number(saved.left) : leftOffset + col * colSpacing}px`;

        icon.addEventListener('dblclick', app.action);

        let isDragging = false;
        let offsetX = 0;
        let offsetY = 0;

        icon.addEventListener('mousedown', (e) => {
            if (isMobileSafeMode()) return;
            isDragging = true;
            icon.style.zIndex = 999;
            offsetX = e.clientX - icon.offsetLeft;
            offsetY = e.clientY - icon.offsetTop;
            document.body.style.userSelect = 'none';
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            icon.style.left = `${e.clientX - offsetX}px`;
            icon.style.top = `${e.clientY - offsetY}px`;
        });

        window.addEventListener('mouseup', () => {
            if (!isDragging) return;
            isDragging = false;
            icon.style.zIndex = '';
            document.body.style.userSelect = 'auto';
            if (!isMobileSafeMode()) {
                saveDesktopSettingsNow({ icon_positions: collectDesktopIconPositions() });
            }
        });

        desktop.appendChild(icon);
    });
}

window.addEventListener('resize', () => {
    applyMobileSafeModeToOpenWindows();
    const mobileMode = isMobileSafeMode();
    if (desktopLastSafeMode === null) {
        desktopLastSafeMode = mobileMode;
        return;
    }
    if (mobileMode !== desktopLastSafeMode && desktopRenderedApps.length) {
        renderDesktopIcons(desktopRenderedApps, desktopSettings);
    }
});

function ensureSystemToolbar() {
    let toolbar = document.getElementById('system-toolbar');
    if (toolbar) return toolbar;

    toolbar = document.createElement('div');
    toolbar.id = 'system-toolbar';
    toolbar.innerHTML = `
        <div class="system-start-wrap">
            <button id="system-start-button" type="button" aria-label="Menu systemowe">
                <img src="/static/images/ghost_logo_taskbar.png" alt="">
                <span>GH0ST</span>
            </button>
            <div id="system-start-menu" hidden></div>
        </div>
        <button id="system-window-tab-button" type="button" aria-label="Przelacz otwarte okno" title="Przelacz otwarte okno">
            <span aria-hidden="true">⇥</span>
        </button>
        <div id="system-running-apps"></div>
        <div id="system-status-strip"></div>
    `;
    document.body.appendChild(toolbar);

    const startButton = toolbar.querySelector('#system-start-button');
    const startMenu = toolbar.querySelector('#system-start-menu');
    const windowTabButton = toolbar.querySelector('#system-window-tab-button');
    startButton.addEventListener('click', (event) => {
        event.stopPropagation();
        startMenu.hidden = !startMenu.hidden;
    });
    document.addEventListener('click', (event) => {
        if (!toolbar.contains(event.target)) {
            startMenu.hidden = true;
        }
    });
    windowTabButton.addEventListener('click', cycleMobileToolbarWindow);

    renderStartMenu();
    renderRunningApps();
    renderToolbarStatus();
    return toolbar;
}

function getToolbarTargetCoordKey(target) {
    const lat = Number((target || {}).lat);
    const lng = Number((target || {}).lng !== undefined ? (target || {}).lng : (target || {}).lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return "";
    return `${lat.toFixed(5)}|${lng.toFixed(5)}`;
}

function getToolbarTargetLabelKey(target) {
    return String(
        (target || {}).label
        || (target || {}).name
        || (target || {}).display_label
        || (target || {}).title
        || ""
    ).trim().toLowerCase();
}

function toolbarTargetsHaveDifferentSelection(left, right) {
    if (!left || !right || typeof left !== "object" || typeof right !== "object") return false;
    const leftCoords = getToolbarTargetCoordKey(left);
    const rightCoords = getToolbarTargetCoordKey(right);
    if (leftCoords && rightCoords && leftCoords !== rightCoords) return true;

    const leftLabel = getToolbarTargetLabelKey(left);
    const rightLabel = getToolbarTargetLabelKey(right);
    if (leftLabel && rightLabel && leftLabel !== rightLabel) return true;
    return false;
}

function isToolbarTargetGenericId(value) {
    const id = String(value || "").trim().toLowerCase();
    return !id || id === "target" || id === "map:0.0.0.0:target" || id.includes("0.0.0.0");
}

function toolbarTargetsShareProgressIdentity(left, right) {
    if (!left || !right || typeof left !== "object" || typeof right !== "object") return false;
    const leftMode = String(left.target_mode || "").trim();
    const rightMode = String(right.target_mode || "").trim();
    if (leftMode === "player" || rightMode === "player") {
        const leftUser = String(left.target_username || left.username || "").trim();
        const rightUser = String(right.target_username || right.username || "").trim();
        return Boolean(leftUser && rightUser && leftMode === rightMode && leftUser === rightUser);
    }
    const differentSelection = toolbarTargetsHaveDifferentSelection(left, right);
    const leftVulnerability = String(left.vulnerability_id || "").trim();
    const rightVulnerability = String(right.vulnerability_id || "").trim();
    if (leftVulnerability || rightVulnerability) {
        return Boolean(leftVulnerability && leftVulnerability === rightVulnerability && !differentSelection);
    }
    const leftArea = String(left.foreign_area_id || "").trim();
    const rightArea = String(right.foreign_area_id || "").trim();
    if (leftArea || rightArea) {
        return Boolean(leftArea && leftArea === rightArea && getToolbarTargetCoordKey(left) === getToolbarTargetCoordKey(right) && !differentSelection);
    }
    const leftId = String(left.target_id || left.id || "").trim();
    const rightId = String(right.target_id || right.id || "").trim();
    if (leftId && rightId && leftId === rightId && !differentSelection && !isToolbarTargetGenericId(leftId)) return true;
    const leftCoords = getToolbarTargetCoordKey(left);
    const rightCoords = getToolbarTargetCoordKey(right);
    return Boolean(leftCoords && leftCoords === rightCoords && !differentSelection);
}

function toolbarTargetMatchesCaptured(aimedTarget, capturedTarget) {
    const aimedCoords = getToolbarTargetCoordKey(aimedTarget);
    const capturedCoords = getToolbarTargetCoordKey(capturedTarget);
    if (!aimedCoords || !capturedCoords || aimedCoords !== capturedCoords) return false;

    const aimedLabel = getToolbarTargetLabelKey(aimedTarget);
    const capturedLabel = getToolbarTargetLabelKey(capturedTarget);
    if (aimedLabel && capturedLabel && aimedLabel !== capturedLabel) return false;
    return true;
}

function toolbarTargetAlreadyCaptured(profile, aimedTarget) {
    if (!hasToolbarAimedTarget(aimedTarget)) return false;
    const capturedTargets = [];
    const sources = [
        profile && profile.hacked,
        profile && profile.hacked_targets,
        profile && profile.captured_targets,
        toolbarProfile && toolbarProfile.hacked,
        toolbarProfile && toolbarProfile.hacked_targets,
        toolbarProfile && toolbarProfile.captured_targets
    ];
    sources.forEach(source => {
        if (Array.isArray(source)) capturedTargets.push(...source);
    });
    return capturedTargets.some(capturedTarget => toolbarTargetMatchesCaptured(aimedTarget, capturedTarget));
}

function getToolbarTargetHackedEffectKey(target) {
    return getTargetFeedbackKey(target)
        || [
            getToolbarTargetCoordKey(target),
            getToolbarTargetLabelKey(target)
        ].filter(Boolean).join("|");
}

function getToolbarTargetStableKey(target) {
    return [
        getToolbarTargetCoordKey(target),
        getToolbarTargetLabelKey(target),
        String((target || {}).target_mode || "").trim(),
        String((target || {}).vulnerability_id || "").trim(),
        String((target || {}).foreign_area_id || "").trim(),
        String((target || {}).target_username || (target || {}).username || "").trim()
    ].filter(Boolean).join("|") || getToolbarTargetHackedEffectKey(target);
}

function coerceSnapshotTimestampMs(value) {
    if (typeof value === "number" && Number.isFinite(value) && value > 0) return value;
    if (typeof value === "string" && value.trim()) {
        const numeric = Number(value);
        if (Number.isFinite(numeric) && numeric > 0) return numeric;
        const parsed = Date.parse(value);
        if (Number.isFinite(parsed) && parsed > 0) return parsed;
    }
    return 0;
}

function getProfileSnapshotClientRequestedMs(profile) {
    return coerceSnapshotTimestampMs(profile && profile.snapshot_client_requested_ms);
}

function getProfileSnapshotClientReceivedMs(profile) {
    return coerceSnapshotTimestampMs(profile && profile.snapshot_client_received_ms);
}

function getProfileSnapshotServerStartedMs(profile) {
    const meta = (profile && profile.snapshot_meta) || {};
    return coerceSnapshotTimestampMs((profile && profile.snapshot_started_ms) || meta.snapshot_started_ms || meta.snapshot_started_at);
}

function isProfileSnapshotOlderThanToolbarOverride(profile, override) {
    if (!profile || !override) return false;
    const requestedMs = getProfileSnapshotClientRequestedMs(profile);
    if (requestedMs && requestedMs < override.startedAt) return true;
    const receivedMs = getProfileSnapshotClientReceivedMs(profile);
    if (receivedMs && receivedMs < override.startedAt) return true;
    return false;
}

function rememberToolbarTargetLocalOverride(target, startedAt = Date.now()) {
    if (!hasToolbarAimedTarget(target)) return;
    toolbarTargetLocalOverride = {
        key: getToolbarTargetStableKey(target),
        target: {
            ...target,
            client_action_ms: target.client_action_ms || startedAt
        },
        startedAt
    };
}

function clearToolbarTargetLocalOverride(target = null) {
    if (!toolbarTargetLocalOverride) return;
    if (!target || !hasToolbarAimedTarget(target)) {
        toolbarTargetLocalOverride = null;
        return;
    }
    const key = getToolbarTargetStableKey(target);
    if (
        !key
        || key === toolbarTargetLocalOverride.key
        || toolbarTargetsShareProgressIdentity(toolbarTargetLocalOverride.target, target)
    ) {
        toolbarTargetLocalOverride = null;
    }
}

function getActiveToolbarTargetLocalOverride() {
    if (!toolbarTargetLocalOverride) return null;
    if (Date.now() - toolbarTargetLocalOverride.startedAt > TOOLBAR_TARGET_LOCAL_OVERRIDE_TTL_MS) {
        toolbarTargetLocalOverride = null;
        return null;
    }
    return toolbarTargetLocalOverride;
}

function triggerToolbarTargetHackedEffect(target) {
    if (!hasToolbarAimedTarget(target)) return;
    const key = getToolbarTargetHackedEffectKey(target);
    if (!key || toolbarTargetHackedEffectKeys.has(key)) return;
    toolbarTargetHackedEffectKeys.add(key);
    if (toolbarTargetHackedEffectKeys.size > 80) {
        toolbarTargetHackedEffectKeys.clear();
        toolbarTargetHackedEffectKeys.add(key);
    }
    toolbarTargetHackedEffect = {
        key,
        label: target.display_label
            || target.label
            || target.name
            || target.title
            || target.target_id
            || target.id
            || "target",
        startedAt: Date.now()
    };
    clearTimeout(toolbarTargetHackedEffectTimer);
    renderToolbarStatus();
    toolbarTargetHackedEffectTimer = setTimeout(() => {
        toolbarTargetHackedEffect = null;
        toolbarTargetHackedEffectTimer = null;
        renderToolbarStatus();
    }, 1100);
}

function toolbarResultCapturedTarget(data) {
    if (!data || typeof data !== "object" || data.success !== true) return false;
    if (!data.captured_target) return false;
    return !hasToolbarAimedTarget(data.target);
}

function handleToolbarTargetCapturedResult(data) {
    if (!toolbarResultCapturedTarget(data)) return false;
    const target = data.captured_target;
    if (!hasToolbarAimedTarget(target)) return false;
    clearToolbarTargetLocalOverride(target);
    triggerToolbarTargetHackedEffect(target);
    setToolbarProfile({
        ...(toolbarProfile || {}),
        aimed_target: {}
    });
    return true;
}

function mergeToolbarTargetProgress(currentTarget, incomingTarget) {
    if (!incomingTarget || typeof incomingTarget !== "object") return incomingTarget;
    if (!hasToolbarAimedTarget(incomingTarget)) return incomingTarget;
    if (!currentTarget || typeof currentTarget !== "object" || !hasToolbarAimedTarget(currentTarget)) return incomingTarget;
    if (!toolbarTargetsShareProgressIdentity(currentTarget, incomingTarget)) return incomingTarget;

    const merged = { ...incomingTarget };
    const currentActions = currentTarget.actions_allowed || {};
    const incomingActions = incomingTarget.actions_allowed || {};
    merged.actions_allowed = { ...incomingActions };
    Object.entries(currentActions).forEach(([key, value]) => {
        if (value === true) merged.actions_allowed[key] = true;
    });

    const currentSecurity = currentTarget.security || {};
    const incomingSecurity = incomingTarget.security || {};
    merged.security = { ...incomingSecurity };
    Object.entries(currentSecurity).forEach(([key, value]) => {
        if (value === false) merged.security[key] = false;
    });

    const incomingProgress = targetFeedbackClampPercent(
        incomingTarget.disarm_progress !== undefined
            ? incomingTarget.disarm_progress
            : ((incomingTarget.feedback || {}).disarm_progress)
    );
    const currentProgress = targetFeedbackClampPercent(
        currentTarget.disarm_progress !== undefined
            ? currentTarget.disarm_progress
            : ((currentTarget.feedback || {}).disarm_progress)
    );
    if (incomingProgress !== null || currentProgress !== null) {
        merged.disarm_progress = Math.max(incomingProgress || 0, currentProgress || 0);
    }
    return merged;
}

function normalizeToolbarProfileProgress(profile) {
    if (!profile || typeof profile !== "object") return profile;
    if (!Object.prototype.hasOwnProperty.call(profile, "aimed_target")) return profile;
    let incomingTarget = profile.aimed_target;
    const localOverride = getActiveToolbarTargetLocalOverride();
    if (localOverride && hasToolbarAimedTarget(localOverride.target)) {
        if (toolbarTargetAlreadyCaptured(profile, localOverride.target)) {
            clearToolbarTargetLocalOverride(localOverride.target);
        } else if (
            isProfileSnapshotOlderThanToolbarOverride(profile, localOverride)
            || !hasToolbarAimedTarget(incomingTarget)
            || !toolbarTargetsShareProgressIdentity(localOverride.target, incomingTarget)
        ) {
            incomingTarget = localOverride.target;
        }
    }
    const normalized = {
        ...profile,
        aimed_target: mergeToolbarTargetProgress((toolbarProfile || {}).aimed_target, incomingTarget)
    };
    if (toolbarTargetAlreadyCaptured(normalized, normalized.aimed_target)) {
        clearToolbarTargetLocalOverride(normalized.aimed_target);
        triggerToolbarTargetHackedEffect(normalized.aimed_target);
        normalized.aimed_target = {};
    }
    return normalized;
}

function setToolbarProfile(profile) {
    toolbarProfile = profile ? normalizeToolbarProfileProgress(profile) : toolbarProfile;
    renderToolbarStatus();
}

function normalizeToolbarKeyList(value) {
    if (Array.isArray(value)) return value.filter(Boolean).map(String);
    if (typeof value === "string") {
        return value.split(",").map(item => item.trim()).filter(Boolean);
    }
    return [];
}

function extractToolbarUnlockKeys(app) {
    const keys = new Set();
    ["interferes_with", "disables", "affects"].forEach(field => {
        normalizeToolbarKeyList((app || {})[field]).forEach(key => keys.add(key));
    });

    const effect = (app || {}).effect;
    if (effect && typeof effect === "object") {
        Object.entries(effect).forEach(([key, value]) => {
            if (value === false) keys.add(key);
        });
    }

    ((app || {}).levels || []).forEach(level => {
        ((level || {}).options || []).forEach(option => {
            const optionEffect = (option || {}).effect;
            if (optionEffect && typeof optionEffect === "object") {
                Object.entries(optionEffect).forEach(([key, value]) => {
                    if (value === false) keys.add(key);
                });
            }
        });
    });

    return keys;
}

function getToolbarArsenalApps(profile) {
    const source = profile || {};
    if (Array.isArray(source.apps) && source.apps.length) return source.apps;
    if (source.files && Array.isArray(source.files.tools) && source.files.tools.length) {
        return source.files.tools;
    }
    if (Array.isArray(toolbarLauncherApps) && toolbarLauncherApps.length) return toolbarLauncherApps;
    return [];
}

function calculateToolbarArsenalCoverage(profile) {
    const aimedTarget = ((profile || {}).aimed_target || {});
    const hasTarget = hasToolbarAimedTarget(aimedTarget);
    const targetSecurity = aimedTarget.security || {};
    const activeKeys = Object.entries(targetSecurity)
        .filter(([, value]) => value === true)
        .map(([key]) => key);

    if (!activeKeys.length) {
        return hasTarget ? 100 : null;
    }

    const unlockKeys = new Set();
    getToolbarArsenalApps(profile).forEach(app => {
        extractToolbarUnlockKeys(app).forEach(key => unlockKeys.add(key));
    });

    if (!unlockKeys.size && hasTarget) return 100;

    const covered = activeKeys.filter(key => unlockKeys.has(key)).length;
    return Math.round((covered / activeKeys.length) * 100);
}

const TARGET_FEEDBACK_ACTION_KEYS = ["scan_ports", "exploit", "sniff", "trace"];
const TARGET_FEEDBACK_SECURITY_KEYS = [
    "stealth_mode", "scan_detection", "exploit_protection", "vpn_enabled",
    "browser_protection", "os_hardening", "log_guardian", "process_monitor",
    "firewall", "log_integrity", "network_anomaly_detection", "spoofing_protection",
    "activity_monitor", "player_tracking", "system_visibility", "firewall_core",
    "kernel_guard", "system_integrity_check", "heap_protection", "memory_lock",
    "background_injection", "memory_guard", "vpn_blocker"
];

function targetFeedbackClampPercent(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return null;
    return Math.max(0, Math.min(100, Math.round(number)));
}

function isToolbarPlaceholderTarget(aimedTarget) {
    const target = aimedTarget || {};
    const id = String(target.target_id || target.id || "").trim().toLowerCase();
    if (!id) return false;
    if (["map:0.0:0.0:target", "map:0:0:target", "map:unknown:unknown:target"].includes(id)) {
        return true;
    }
    if (/^map:(0(?:\.0+)?|unknown|none|null):(0(?:\.0+)?|unknown|none|null):(target|brak|unknown|none|null)$/i.test(id)) {
        return true;
    }
    const lat = Number(target.lat);
    const lng = Number(target.lng !== undefined ? target.lng : target.lon);
    const label = String(target.label || target.name || target.display_label || target.title || "").trim().toLowerCase();
    return Number.isFinite(lat)
        && Number.isFinite(lng)
        && Math.abs(lat) < 0.000001
        && Math.abs(lng) < 0.000001
        && (!label || label === "target" || label === "brak" || label === "unknown");
}

function hasToolbarAimedTarget(aimedTarget) {
    const target = aimedTarget || {};
    if (isToolbarPlaceholderTarget(target)) return false;
    const identity = String(
        target.label
        || target.name
        || target.display_label
        || target.title
        || target.target_username
        || target.username
        || target.target_id
        || target.id
        || ""
    ).trim();
    return Boolean(identity && identity.toLowerCase() !== "brak");
}

function getTargetFeedbackKey(aimedTarget) {
    const target = aimedTarget || {};
    if (!hasToolbarAimedTarget(target)) return "";
    const lng = target.lng !== undefined ? target.lng : target.lon;
    return [
        target.target_id || target.id || "",
        target.target_mode || "",
        target.target_username || target.username || "",
        target.vulnerability_id || "",
        target.lat !== undefined ? Number(target.lat).toFixed(6) : "",
        lng !== undefined ? Number(lng).toFixed(6) : "",
        target.label || target.name || ""
    ].join("|");
}

function getTargetActionDots(aimedTarget) {
    const actions = ((aimedTarget || {}).actions_allowed || {});
    return TARGET_FEEDBACK_ACTION_KEYS.map(key => ({
        key,
        active: actions[key] === true
    }));
}

function calculateTargetDisarmProgress(aimedTarget) {
    const target = aimedTarget || {};
    const feedback = target.feedback && typeof target.feedback === "object" ? target.feedback : {};
    const backendProgress = targetFeedbackClampPercent(
        target.disarm_progress !== undefined ? target.disarm_progress : feedback.disarm_progress
    );
    const actions = target.actions_allowed && typeof target.actions_allowed === "object"
        ? target.actions_allowed
        : {};
    const actionStates = TARGET_FEEDBACK_ACTION_KEYS
        .filter(key => typeof actions[key] === "boolean")
        .map(key => actions[key] === true);
    const actionProgress = actionStates.length
        ? Math.round((actionStates.filter(Boolean).length / actionStates.length) * 100)
        : null;
    const hasCompletedAction = actionStates.some(Boolean);
    if (backendProgress !== null || hasCompletedAction) {
        return Math.max(backendProgress || 0, actionProgress || 0);
    }

    const security = target.security && typeof target.security === "object" ? target.security : {};
    const keys = TARGET_FEEDBACK_SECURITY_KEYS.filter(key => typeof security[key] === "boolean");
    if (!keys.length) return actionProgress || 0;

    const disabled = keys.filter(key => security[key] === false).length;
    return Math.round((disabled / keys.length) * 100);
}

function resolveTargetBarFeedback(aimedTarget) {
    if (!hasToolbarAimedTarget(aimedTarget)) {
        toolbarTargetFeedbackState = { targetKey: "", dotSignature: "", progress: 0 };
        return null;
    }

    const targetKey = getTargetFeedbackKey(aimedTarget);
    const previous = toolbarTargetFeedbackState || { targetKey: "", dotSignature: "", progress: 0 };
    const dots = getTargetActionDots(aimedTarget);
    const dotSignature = dots.map(dot => dot.active ? "1" : "0").join("");
    const rawProgress = calculateTargetDisarmProgress(aimedTarget);
    const sameTarget = previous.targetKey === targetKey;
    const progress = sameTarget ? Math.max(previous.progress || 0, rawProgress) : rawProgress;
    const targetChanged = Boolean(previous.targetKey && previous.targetKey !== targetKey);
    const changed = targetChanged || previous.dotSignature !== dotSignature || progress !== previous.progress;

    toolbarTargetFeedbackState = { targetKey, dotSignature, progress };
    return { dots, progress, targetKey, changed, targetChanged };
}

function renderTargetBarFeedback(feedback) {
    if (!feedback) return "";
    const dots = feedback.dots.map(dot => {
        const classes = ["target-action-dot"];
        if (dot.active) classes.push("is-active");
        return `<i class="${classes.join(" ")}" data-action="${escapeHTML(dot.key)}"></i>`;
    }).join("");
    return `
        <i class="target-feedback" aria-hidden="true">
            <i class="target-action-dots">${dots}</i>
            <i class="target-disarm-track"><i class="target-disarm-fill"></i></i>
        </i>
    `;
}

async function refreshToolbarProfile() {
    const profile = await getUserProfile();
    if (profile) setToolbarProfile(profile);
    return profile;
}

async function refreshToolbarTargetTruth() {
    if (toolbarTargetTruthRefreshing) return;
    toolbarTargetTruthRefreshing = true;
    renderToolbarStatus();
    try {
        await refreshToolbarProfile();
    } catch (error) {
        console.warn("Nie udalo sie odswiezyc prawdy celu:", error);
    } finally {
        toolbarTargetTruthRefreshing = false;
        renderToolbarStatus();
    }
}

function updateToolbarAimedTarget(aimedTarget) {
    if (!aimedTarget || typeof aimedTarget !== "object") return;
    const startedAt = Date.now();
    const nextTarget = {
        ...aimedTarget,
        client_action_ms: aimedTarget.client_action_ms || startedAt
    };
    rememberToolbarTargetLocalOverride(nextTarget, startedAt);
    toolbarTargetHackedEffect = null;
    clearTimeout(toolbarTargetHackedEffectTimer);
    toolbarTargetHackedEffectTimer = null;
    toolbarProfile = {
        ...(toolbarProfile || {}),
        aimed_target: nextTarget
    };
    renderToolbarStatus();
}

function renderToolbarStatus() {
    const strip = document.getElementById('system-status-strip');
    if (!strip) return;

    const profile = toolbarProfile || {};
    const aimedTarget = profile.aimed_target || {};
    const hasTarget = hasToolbarAimedTarget(aimedTarget);
    const targetLabel = aimedTarget.display_label
        || aimedTarget.label
        || aimedTarget.name
        || aimedTarget.title
        || aimedTarget.target_id
        || aimedTarget.id
        || "brak";
    const arsenalCoverage = calculateToolbarArsenalCoverage(profile);
    const arsenalLabel = arsenalCoverage === null ? "--" : `${arsenalCoverage}%`;
    const targetFeedback = hasTarget ? resolveTargetBarFeedback(aimedTarget) : resolveTargetBarFeedback(null);
    const hackedEffect = !hasTarget
        && toolbarTargetHackedEffect
        && Date.now() - toolbarTargetHackedEffect.startedAt < 1200
        ? toolbarTargetHackedEffect
        : null;
    const targetMarkup = hasTarget ? (() => {
        const targetClasses = [
            "system-status-target",
            "is-aimed",
            toolbarTargetTruthRefreshing ? "is-refreshing" : "",
            targetFeedback ? "has-target-feedback" : "",
            targetFeedback?.changed ? "is-feedback-change" : "",
            targetFeedback?.targetChanged ? "is-target-change" : ""
        ].filter(Boolean).join(" ");
        const targetProgressStyle = targetFeedback ? ` style="--target-disarm-progress: ${targetFeedback.progress}%;"` : "";
        const title = toolbarTargetTruthRefreshing ? "Sprawdzam zrodlo prawdy celu..." : `Cel na celowniku: ${escapeHTML(String(targetLabel))}. Kliknij, aby odswiezyc.`;
        return `<span class="${targetClasses}" role="button" tabindex="0" title="${title}"${targetProgressStyle}><b>CEL</b><i class="target-status-body"><em>${escapeHTML(String(targetLabel))}</em>${renderTargetBarFeedback(targetFeedback)}</i></span>`;
    })() : (hackedEffect
        ? `<span class="system-status-target is-hacked-clear" role="button" tabindex="0" title="Cel przejety. Belka zaraz wroci do stanu neutralnego."><b>CEL</b><i class="target-status-body"><em>${escapeHTML(String(hackedEffect.label))}</em></i></span>`
        : `<span class="system-status-target ${toolbarTargetTruthRefreshing ? "is-refreshing" : ""}" role="button" tabindex="0" title="Kliknij, aby odswiezyc profil celu"><b>CEL</b></span>`);
    strip.innerHTML = `
        ${targetMarkup}
        <span><b>ARS</b> ${arsenalLabel}</span>
        <span><b>HC</b> ${Number(profile.hackcoins || 0)}</span>
        <span><b>LVL</b> ${Number(profile.level || 1)}</span>
        <span><b>RSP</b> ${Number(profile.respect || 0)}</span>
    `;
    const targetRefresh = strip.querySelector('.system-status-target');
    targetRefresh?.addEventListener('click', refreshToolbarTargetTruth);
    targetRefresh?.addEventListener('keydown', event => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        refreshToolbarTargetTruth();
    });
}

function setToolbarLaunchers(apps, profile = null) {
    toolbarLauncherApps = apps || [];
    ensureSystemToolbar();
    if (profile) setToolbarProfile(profile);
    renderStartMenu();
}

function renderStartMenu() {
    const menu = document.getElementById('system-start-menu');
    if (!menu) return;

    const apps = toolbarLauncherApps.length ? toolbarLauncherApps : desktopApps;
    menu.innerHTML = `
        <div class="system-start-programs">
            ${apps.map((app, index) => `
                <button class="system-start-item" type="button" data-launch-index="${index}">
                    <span>${app.icon || '\u25A1'}</span>
                    <span>${escapeHTML(app.label || 'App')}</span>
                </button>
            `).join("")}
        </div>
        <div class="system-start-footer">
            <button class="system-start-item system-action-restart" type="button">
                <span>↻</span>
                <span>Restart</span>
            </button>
            <button class="system-start-item system-action-logout" type="button">
                <span>⏻</span>
                <span>Logout</span>
            </button>
        </div>
    `;

    menu.querySelectorAll('.system-start-item').forEach(button => {
        button.addEventListener('click', () => {
            const app = apps[Number(button.dataset.launchIndex)];
            if (!app || typeof app.action !== 'function') return;
            menu.hidden = true;
            launchFromToolbar(app);
        });
    });

    menu.querySelector('.system-action-restart')?.addEventListener('click', () => {
        menu.hidden = true;
        window.location.reload();
    });

    menu.querySelector('.system-action-logout')?.addEventListener('click', () => {
        menu.hidden = true;
        window.location.href = authenticatedLogoutUrl();
    });
}

async function launchFromToolbar(app) {
    const before = new Set(
        Array.from(document.querySelectorAll('.terminal, .app-window'))
            .map(win => win.dataset.windowId)
            .filter(Boolean)
    );

    try {
        await Promise.resolve(app.action());
    } catch (err) {
        console.error("Błąd uruchamiania aplikacji z paska:", err);
        return;
    }

    setTimeout(() => {
        const windows = Array.from(document.querySelectorAll('.terminal, .app-window'));
        const opened = windows.find(win => win.dataset.windowId && !before.has(win.dataset.windowId));
        if (opened) {
            bringWindowToFront(opened);
            return;
        }

        const label = (app.label || '').toLowerCase();
        const appKeys = {
            mapa: 'map',
            email: 'email',
            pliki: 'files',
            profil: 'profile',
            'wallet hc': 'wallet',
            wallet: 'wallet',
            ustawienia: 'settings',
            appforge: 'appforge',
            termcreator: 'termcreator',
            windowmaker: 'windowmaker',
            buttonmaker: 'buttonmaker'
        };
        const wantedKey = appKeys[label];
        const match = windows.reverse().find(win => {
            const title = (win.dataset.appTitle || getWindowTitle(win)).toLowerCase();
            return (wantedKey && win.dataset.app === wantedKey) || title.includes(label);
        });
        if (match) bringWindowToFront(match);
    }, 0);
}

function getWindowTitle(win) {
    const bar = win.querySelector('.title-bar');
    if (!bar) return win.dataset.appTitle || 'Okno';
    const textNode = Array.from(bar.childNodes).find(node => node.nodeType === Node.TEXT_NODE);
    return (win.dataset.appTitle || textNode?.textContent || bar.textContent || 'Okno').trim();
}

function getWindowIcon(win, title) {
    if (win.dataset.appIcon) return win.dataset.appIcon;
    const normalizedTitle = title.toLowerCase();
    const found = [...desktopApps, ...toolbarLauncherApps].find(app => {
        const label = (app.label || '').toLowerCase();
        return label && (normalizedTitle.includes(label) || label.includes(normalizedTitle));
    });
    return found?.icon || '\u25A3';
}

function bringWindowToFront(win) {
    if (!win || !win.isConnected) return;
    document.querySelectorAll('.terminal, .app-window').forEach(t => t.classList.remove('active'));
    win.classList.add('active');
    win.style.zIndex = ++topZIndex;
    renderRunningApps();
}

function connectedRunningWindows() {
    const windows = [];
    for (const [id, win] of runningWindows.entries()) {
        if (!win || !win.isConnected) {
            runningWindows.delete(id);
            continue;
        }
        windows.push(win);
    }
    return windows;
}

function cycleMobileToolbarWindow() {
    const windows = connectedRunningWindows();
    if (!windows.length) return;
    const activeIndex = windows.findIndex(win => win.classList.contains('active'));
    const nextIndex = activeIndex >= 0 ? (activeIndex + 1) % windows.length : 0;
    bringWindowToFront(windows[nextIndex]);
}

function renderMobileWindowTabButton(windows) {
    const button = document.getElementById('system-window-tab-button');
    if (!button) return;
    const activeIndex = windows.findIndex(win => win.classList.contains('active'));
    const nextIndex = windows.length ? (activeIndex >= 0 ? (activeIndex + 1) % windows.length : 0) : -1;
    const nextWindow = nextIndex >= 0 ? windows[nextIndex] : null;
    const nextTitle = nextWindow ? (nextWindow.dataset.appTitle || getWindowTitle(nextWindow)) : '';
    button.disabled = windows.length === 0;
    button.dataset.windowCount = String(windows.length);
    button.title = nextWindow
        ? `Nastepne okno: ${nextTitle} (${windows.length})`
        : 'Brak otwartych okien';
    button.setAttribute('aria-label', button.title);
}

function registerWindowInTaskbar(win) {
    if (!win || win.dataset.windowId) return;

    const id = `win-${++windowSequence}`;
    const title = getWindowTitle(win);
    win.dataset.windowId = id;
    win.dataset.appTitle = title;
    win.dataset.appIcon = getWindowIcon(win, title);
    runningWindows.set(id, win);
    ensureSystemToolbar();
    renderRunningApps();
}

function renderRunningApps() {
    const box = document.getElementById('system-running-apps');
    if (!box) return;

    const windows = connectedRunningWindows();
    renderMobileWindowTabButton(windows);

    box.innerHTML = "";
    runningWindows.forEach((win, id) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `system-task-button ${win.classList.contains('active') ? 'active' : ''}`;
        button.dataset.windowId = id;
        button.innerHTML = `
            <span class="system-task-icon">${win.dataset.appIcon || '\u25A3'}</span>
            <span class="system-task-label">${escapeHTML(win.dataset.appTitle || getWindowTitle(win))}</span>
        `;
        button.addEventListener('click', () => bringWindowToFront(win));
        box.appendChild(button);
    });
}

const toolbarObserver = new MutationObserver(() => renderRunningApps());
toolbarObserver.observe(document.body, { childList: true });

function runSystemLauncherApp(appData) {
    const launcher = String(appData?.system_launcher || '').trim();
    const launcherMap = {
        createAppForge,
        createTermCreator,
        createWindowMaker,
        createButtonMaker,
        createVictimPickerApp,
        territory_control: createTerritoryControlApp,
        createTerritoryControlApp,
        operation_control: createOperationControlApp,
        createOperationControlApp,
        ghostnetwork_suite: createGhostNetworkSuiteApp,
        createGhostNetworkSuiteApp,
        agi2108_console: createAgi2108ConsoleApp,
        createAgi2108ConsoleApp,
        ghost_lab: createGhostLabHub,
        dev_bug_reporter: createDevBugReporterApp
    };
    if (!launcher || typeof launcherMap[launcher] !== 'function') {
        return false;
    }
    launcherMap[launcher]();
    return true;
}

function buildApplicationWindowLaunchKey(id, type) {
    const base = `${String(type || "app").trim().toLowerCase()}:${String(id || "").trim().toLowerCase()}`;
    const aimedTarget = ((toolbarProfile || {}).aimed_target || {});
    const targetKey = hasToolbarAimedTarget(aimedTarget)
        ? getToolbarTargetStableKey(aimedTarget)
        : "";
    return targetKey ? `${base}:${targetKey}` : base;
}

function readProvisionalAppLaunchFlags() {
    const node = document.getElementById("provisional-app-launch-config");
    if (!node) return { enabled: false };
    try {
        const parsed = JSON.parse(node.textContent || "{}");
        return { enabled: parsed.enabled === true };
    } catch (error) {
        console.warn("[app launch] Nieprawidlowy provisional launch config", error);
        return { enabled: false };
    }
}

const provisionalAppLaunchFlags = readProvisionalAppLaunchFlags();
function readOFSVisualLiftEnabled() {
    const node = document.getElementById("operation-feedback-config");
    if (!node) return true;
    try {
        const parsed = JSON.parse(node.textContent || "{}");
        return parsed.visual_lift_enabled !== false;
    } catch (error) {
        console.warn("[OFS] Nieprawidlowy visual lift config", error);
        return true;
    }
}
const ofsVisualLiftEnabled = readOFSVisualLiftEnabled();
function readOFSTitleSequenceEnabled() {
    const node = document.getElementById("operation-feedback-config");
    if (!node) return true;
    try {
        const parsed = JSON.parse(node.textContent || "{}");
        return parsed.title_sequence_enabled !== false;
    } catch (error) {
        console.warn("[OFS] Nieprawidlowy title sequence config", error);
        return true;
    }
}
const ofsTitleSequenceEnabled = readOFSTitleSequenceEnabled();
const provisionalApplicationSessions = new Map();
let provisionalApplicationTombstones = [];
let activeProvisionalHydrationSession = null;
const PROVISIONAL_APPLICATION_TOMBSTONE_TTL_MS = 120000;

function normalizeLaunchCorrelation(value) {
    return String(value || "").trim().toLowerCase();
}

function provisionalSessionMatchesLaunch(session, item = {}) {
    if (!session) return false;
    const receipt = normalizeLaunchCorrelation(item.receipt);
    if (receipt && normalizeLaunchCorrelation(session.receipt) === receipt) return true;
    const appId = normalizeLaunchCorrelation(item.app_id || item.id || item.name);
    const clientKey = normalizeLaunchCorrelation(item.client_action_key);
    if (clientKey && appId
        && normalizeLaunchCorrelation(session.clientActionKey) === clientKey
        && normalizeLaunchCorrelation(session.appId) === appId) return true;
    return Boolean(appId
        && normalizeLaunchCorrelation(session.appId) === appId
        && normalizeLaunchCorrelation(session.flowId) === normalizeLaunchCorrelation(item.flow_id)
        && normalizeLaunchCorrelation(session.action) === normalizeLaunchCorrelation(item.action));
}

function pruneProvisionalApplicationTombstones() {
    const now = Date.now();
    provisionalApplicationTombstones = provisionalApplicationTombstones.filter(item => item.expiresAt > now);
}

function resolveProvisionalApplicationLaunch(item = {}) {
    if (!provisionalAppLaunchFlags.enabled) return { outcome: "not_found", session: null };
    pruneProvisionalApplicationTombstones();
    if (provisionalApplicationTombstones.some(tombstone => provisionalSessionMatchesLaunch(tombstone, item))) {
        return { outcome: "tombstoned", session: null };
    }
    const matches = Array.from(provisionalApplicationSessions.values())
        .filter(session => !session.disposed && provisionalSessionMatchesLaunch(session, item));
    return matches.length === 1
        ? { outcome: "hydrated", session: matches[0] }
        : { outcome: "not_found", session: null };
}

function bindProvisionalApplicationReceipt(session, item = {}) {
    if (!session || session.disposed) return;
    session.receipt = String(item.receipt || session.receipt || "").trim();
    session.clientActionKey = String(item.client_action_key || session.clientActionKey || "").trim();
    session.action = String(item.action || session.action || "").trim();
}

function buildProvisionalLaunchSessionKey(selection = {}, appData = {}) {
    const pending = selection.pending_action || {};
    const flowId = getHackFlowId(selection);
    const clientKey = String(pending._client_action_key || selection.pending_request_key || flowId || "manual").trim();
    const appId = String(appData.id || appData.name || "app").trim();
    return `${clientKey}:${appId}`;
}

function updateProvisionalApplicationSession(session, state, message = "") {
    if (!session || session.disposed) return;
    session.state = state;
    const appWindow = session.appWindow;
    if (!appWindow || !appWindow.isConnected) return;
    appWindow.dataset.provisionalState = state;
    const status = appWindow.querySelector(".provisional-app-status");
    if (status) status.textContent = message || state;
}

function setApplicationPresentationPhase(session, phase, details = {}) {
    if (!session || session.disposed) return false;
    const normalized = String(phase || "").trim();
    if (!normalized || session.presentationPhase === normalized) return true;
    const previous = session.presentationPhase || "";
    session.presentationPhase = normalized;
    const appWindow = session.appWindow;
    if (appWindow?.dataset) appWindow.dataset.ofsPhase = normalized;
    const host = appWindow?.querySelector?.(".operation-feedback-host")
        || appWindow?.querySelector?.(".provisional-app-scenes")
        || appWindow?.querySelector?.(".app-content");
    if (host?.dataset) {
        host.dataset.ofsPhase = normalized;
        host.dataset.ofsTemplate = String(appWindow?.dataset?.appInterface || "");
    }
    appFlowTrace(session.flowId, "feedback_phase_changed", {
        app_id: session.appId,
        action: session.action,
        mode: "ofs_provisional",
        previous_phase: previous,
        next_phase: normalized,
        elapsed_ms: session.createdAt ? Math.max(0, Math.round(performance.now() - session.createdAt)) : 0,
        ...details
    });
    return true;
}

function buildPreExecutionScenes(appData = {}, pending = {}, projectedContent = null) {
    const appName = String(appData.name || appData.id || "Aplikacja").trim();
    const interfaceType = String(appData.interface || "window").trim().toLowerCase();
    const targetLabel = String(pending.label || pending.name || "").trim();
    const action = String(pending.action || "").trim();
    const authorDescription = String(
        projectedContent?.legacy?.transition?.[0] || appData.description || ""
    ).trim();
    const interfaceLines = {
        terminal: "Przygotowanie lokalnej sesji terminalowej.",
        progressbar_random: "Ladowanie etapow aplikacji.",
        button_choices: "Przygotowanie interfejsu decyzji.",
        window: "Przygotowanie widoku aplikacji."
    };
    const scenes = [
        { phase: "launching", family: "app_identity", lines: [appName, authorDescription ? `Profil autora: ${authorDescription}` : ""].filter(Boolean) },
        { phase: "booting", family: "local_init", lines: ["Inicjalizacja lokalnego profilu.", interfaceLines[interfaceType] || interfaceLines.window] }
    ];
    if (targetLabel || action) {
        scenes.push({
            phase: "booting",
            family: "context_bind",
            lines: [targetLabel ? `Cel: ${targetLabel}` : "", action ? `Profil dzialania: ${action}` : ""].filter(Boolean)
        });
    }
    scenes.push(
        { phase: "booting", family: "runtime_prepare", lines: ["Lokalny kontekst aplikacji jest gotowy.", "Oczekiwanie na autorytatywny stan uruchomienia."] },
        { phase: "booting", family: "hydration_wait", lines: ["Utrzymanie kontekstu aplikacji.", "Oczekiwanie na stan launchera."] }
    );
    return scenes;
}

function stopPreExecutionPresentation(session, reason = "handoff") {
    const presentation = session?.preExecutionPresentation;
    if (!presentation || presentation.stopped) return;
    presentation.stopped = true;
    if (presentation.timerId !== null) window.clearTimeout(presentation.timerId);
    presentation.renderer?.dispose?.();
    if (reason !== "hydration") {
        appFlowTrace(session.flowId, "feedback_cancelled", {
            app_id: session.appId,
            action: session.action,
            mode: "ofs_provisional",
            completion_reason: reason
        });
    }
    appFlowTrace(session.flowId, "pre_execution_stopped", {
        app_id: session.appId,
        family: presentation.currentFamily || "",
        reason
    });
}

function startPreExecutionPresentation(session, appData = {}, pending = {}, projectedContent = null) {
    if (!session || session.disposed || !session.appWindow?.isConnected) return null;
    const viewport = session.appWindow.querySelector(".provisional-app-scenes");
    if (!viewport) return null;
    const fallbackScenes = buildPreExecutionScenes(appData, pending, projectedContent);
    let renderer = null;
    try {
        renderer = window.OperationFeedbackSystem?.createPresentationRenderer?.("ofs_provisional", {
            host: viewport,
            appWindow: session.appWindow
        }) || null;
    } catch (error) {
        console.warn("[app launch] Provisional renderer fallback", error);
    }
    const presentation = {
        renderer,
        index: 0,
        timerId: null,
        stopped: false,
        currentFamily: "",
        startedAt: performance.now(),
        lastVariant: "",
        recentVariants: [],
        waitBand: "instant"
    };
    session.preExecutionPresentation = presentation;

    const renderScene = scene => {
        if (presentation.stopped || session.disposed || !session.appWindow?.isConnected) return;
        presentation.currentFamily = scene.family;
        updateProvisionalApplicationSession(session, scene.phase, scene.lines[0] || "");
        const rendered = renderer?.render?.({
            presentation_mode: "ofs_provisional",
            phase: scene.phase,
            scene_id: scene.scene_id || scene.family,
            status: scene.lines[0] || "",
            lines: scene.lines,
            transition: scene.transition || (scene.family === "hydration_wait" ? "fade" : "replace"),
            tone: "pending",
            content_source: scene.content_source || (scene.family === "app_identity" ? "app_snapshot" : "local_fallback"),
            wait_band: scene.wait_band || presentation.waitBand
        });
        if (!rendered) {
            viewport.dataset.sceneFamily = scene.family;
            viewport.replaceChildren(...scene.lines.map(line => {
                const node = document.createElement("div");
                node.className = "provisional-app-scene-line";
                node.textContent = line;
                return node;
            }));
        }
        appFlowTrace(session.flowId, "feedback_scene_started", {
            app_id: session.appId,
            action: session.action,
            mode: "ofs_provisional",
            scene_id: scene.scene_id || scene.family,
            content_source: scene.content_source || "local_fallback",
            wait_band: scene.wait_band || presentation.waitBand,
            scene_dom_nodes: viewport.querySelectorAll(".provisional-app-scene-line").length,
            visual_lift: ofsVisualLiftEnabled,
            elapsed_ms: Math.round(performance.now() - presentation.startedAt)
        });
    };

    renderScene({ ...fallbackScenes[0], scene_id: "app_identity_fallback" });
    window.OperationFeedbackSystem?.loadFeedbackConfig?.().then(config => {
        if (presentation.stopped || session.disposed) return;
        const profile = config.operations?.[session.action];
        if (!profile || profile.enabled !== true) return;
        appFlowTrace(session.flowId, "feedback_profile_loaded", {
            app_id: session.appId,
            action: session.action,
            mode: "ofs_provisional"
        });
        const timeline = config.provisional_timelines[profile.provisional_profile.timeline_profile];
        const stages = timeline.stages;
        const sceneContext = {
            app_title: String(appData.name || appData.id || "Aplikacja"),
            description: String(projectedContent?.legacy?.transition?.[0] || appData.description || ""),
            interface: String(appData.interface || profile.provisional_profile.interface_voice || "window").toLowerCase(),
            target_label: String(pending.label || pending.name || ""),
            action_label: String(pending.action || session.action || "")
        };
        const schedule = index => {
            if (presentation.stopped || session.disposed || !session.appWindow?.isConnected) return;
            const stage = stages[index];
            const isExtended = index >= stages.length;
            const activeStage = isExtended ? stages[stages.length - 1] : stage;
            const elapsed = performance.now() - presentation.startedAt;
            const dueAt = isExtended ? elapsed : Number(activeStage.start_after_ms);
            const delay = Math.max(0, dueAt - elapsed);
            presentation.timerId = window.setTimeout(() => {
                if (presentation.stopped || session.disposed) return;
                try {
                    const scene = window.OperationFeedbackSystem.composeProvisionalScene({
                        config,
                        profile,
                        stage: activeStage,
                        context: sceneContext,
                        elapsedMs: Math.max(0, performance.now() - presentation.startedAt),
                        history: {
                            last_variant: presentation.lastVariant,
                            recent_variants: presentation.recentVariants
                        }
                    });
                    presentation.lastVariant = scene.variant_key;
                    presentation.recentVariants.push(scene.variant_key);
                    if (presentation.recentVariants.length > 6) presentation.recentVariants.shift();
                    presentation.waitBand = scene.wait_band || presentation.waitBand;
                    viewport.dataset.ofsWaitBand = presentation.waitBand;
                    presentation.index = index;
                    renderScene(scene);
                    if (activeStage.family === "extended_wait" && !presentation.extendedWaitEntered) {
                        presentation.extendedWaitEntered = true;
                        appFlowTrace(session.flowId, "feedback_extended_wait_entered", {
                            app_id: session.appId,
                            action: session.action,
                            mode: "ofs_provisional",
                            elapsed_ms: Math.round(performance.now() - presentation.startedAt)
                        });
                    }
                } catch (error) {
                    console.warn("[app launch] Provisional scene fallback", error);
                }
                if (isExtended || index === stages.length - 1) {
                    const [minWait, maxWait] = timeline.extended_wait_ms;
                    const wait = Math.round(minWait + Math.random() * (maxWait - minWait));
                    presentation.timerId = window.setTimeout(() => schedule(stages.length), wait);
                } else {
                    schedule(index + 1);
                }
            }, delay);
        };
        schedule(0);
    }).catch(error => {
        console.warn("[app launch] Provisional content unavailable; local fallback remains", error);
    });
    return presentation;
}

function disposeProvisionalApplicationSession(session, reason = "window_closed") {
    if (!session || session.disposed) return;
    stopPreExecutionPresentation(session, reason);
    setApplicationPresentationPhase(session, "disposed", { completion_reason: reason });
    session.disposed = true;
    session.state = "disposed";
    provisionalApplicationSessions.delete(session.sessionKey);
    provisionalApplicationTombstones.push({
        receipt: session.receipt || "",
        clientActionKey: session.clientActionKey || "",
        appId: session.appId || "",
        flowId: session.flowId || "",
        action: session.action || "",
        expiresAt: Date.now() + PROVISIONAL_APPLICATION_TOMBSTONE_TTL_MS
    });
    appFlowTrace(session.flowId, "feedback_disposed", {
        app_id: session.appId,
        action: session.action,
        mode: "ofs_provisional",
        completion_reason: reason
    });
    appFlowTrace(session.flowId, "provisional_app_disposed", {
        app_id: session.appId,
        session_key: session.sessionKey,
        reason
    });
}

function beginProvisionalLaunch(selection = {}, appData = {}) {
    if (!provisionalAppLaunchFlags.enabled) return null;
    const sessionKey = buildProvisionalLaunchSessionKey(selection, appData);
    const existing = provisionalApplicationSessions.get(sessionKey);
    if (existing && !existing.disposed && existing.appWindow?.isConnected) {
        bringWindowToFront(existing.appWindow);
        return existing;
    }

    const pending = selection.pending_action || {};
    const flowId = getHackFlowId(selection);
    const appId = String(appData.id || appData.name || "").trim();
    const appName = String(appData.name || appData.id || "Aplikacja").trim();
    const projectedContent = window.OperationFeedbackSystem
        ? window.OperationFeedbackSystem.projectApplicationContent(appData)
        : null;
    const safeDescription = projectedContent?.legacy?.transition?.[0]
        || "Przygotowanie lokalnego srodowiska aplikacji.";
    const position = findAvailablePosition(460, 280);
    const appWindow = document.createElement("div");
    const provisionalTemplate = normalizeOFSApplicationTemplate(appData.interface);
    appWindow.className = ofsVisualLiftEnabled
        ? `app-window provisional-app-window ofs-app-template ofs-visual-lift ofs-template-${provisionalTemplate}`
        : "app-window provisional-app-window ofs-visual-lift-disabled";
    appWindow.dataset.ofsTemplate = provisionalTemplate;
    appWindow.dataset.appId = appId;
    appWindow.dataset.appTitle = appName;
    appWindow.dataset.appInterface = String(appData.interface || "provisional");
    appWindow.dataset.appFlowId = flowId;
    appWindow.dataset.launchSource = "map";
    appWindow.dataset.provisionalSessionKey = sessionKey;
    appWindow.dataset.provisionalState = "launching";
    if (window.OperationFeedbackSystem?.buildApplicationBrandModel) {
        appWindow._ofsBrandModel = window.OperationFeedbackSystem.buildApplicationBrandModel(appData);
    }
    appWindow.style.top = `${position.top}px`;
    appWindow.style.left = `${position.left}px`;
    appWindow.style.width = "460px";
    appWindow.style.maxWidth = "calc(100vw - 24px)";
    appWindow.innerHTML = `
        <div class="title-bar">
            ${escapeHTML(appName)}
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div class="app-content provisional-app-content">
            <div class="provisional-app-heading">
                <span class="provisional-app-icon">${escapeHTML(appData.icon || "\u{1F6E0}\uFE0F")}</span>
                <div>
                    <strong>${escapeHTML(appName)}</strong>
                    <span>${escapeHTML(safeDescription)}</span>
                </div>
            </div>
            <div class="provisional-app-activity" aria-hidden="true"><span></span><span></span><span></span></div>
            <div class="provisional-app-status" role="status">Inicjalizacja lokalnego profilu...</div>
            <div class="provisional-app-scenes" aria-live="polite"></div>
            ${pending.label ? `<div class="provisional-app-target">Cel: ${escapeHTML(pending.label)}</div>` : ""}
        </div>
    `;

    const context = buildApplicationLaunchContext({
        ...appData,
        _flow_id: flowId,
        _source: "map",
        _map_action_id: pending.action || selection.map_action_id || selection.canonical_action || ""
    });
    const session = {
        sessionKey,
        appId,
        flowId,
        appWindow,
        context,
        clientActionKey: String(pending._client_action_key || selection.pending_request_key || "").trim(),
        action: String(pending.action || selection.map_action_id || selection.canonical_action || "").trim(),
        receipt: "",
        state: "launching",
        presentationPhase: "",
        createdAt: performance.now(),
        disposed: false
    };
    appWindow._provisionalApplicationSession = session;
    appWindow._operationFeedbackLaunchContext = Object.freeze({
        action_key: context.action_key || "",
        security_state: context.security_state || {},
        application_content: context.application_content || null
    });
    appWindow.dataset.expectedTarget = pending
        ? JSON.stringify({
            target_id: pending.target_id || pending.id || "",
            lat: pending.lat,
            lng: pending.lng,
            label: pending.label || pending.name || "",
            target_mode: pending.target_mode || "",
            foreign_area_id: pending.foreign_area_id || "",
            stable_conflict_id: pending.stable_conflict_id || "",
            conflict_id: pending.conflict_id || "",
            expected_owner_username: pending.expected_owner_username || pending.contest_owner_username || "",
            ownership_version: pending.ownership_version
        })
        : "";
    appWindow.querySelector(".close-btn")?.addEventListener("click", () => {
        disposeProvisionalApplicationSession(session, "window_closed");
        appWindow.remove();
    });
    provisionalApplicationSessions.set(sessionKey, session);
    document.body.appendChild(appWindow);
    prepareProvisionalApplicationTitle(appWindow);
    startApplicationTitleSequence(appWindow);
    setApplicationPresentationPhase(session, "provisional");
    makeDraggable(appWindow);
    bringWindowToFront(appWindow);
    startPreExecutionPresentation(session, appData, pending, projectedContent);
    appFlowTrace(flowId, "feedback_session_started", {
        app_id: appId,
        action: context.action_key,
        mode: "ofs_provisional"
    });
    appFlowTrace(flowId, "provisional_app_created", {
        app_id: appId,
        session_key: sessionKey,
        action: context.action_key,
        source: "map"
    });
    return session;
}

window.beginProvisionalLaunch = beginProvisionalLaunch;

function consumeProvisionalHydrationWindow(id, type) {
    const session = activeProvisionalHydrationSession;
    activeProvisionalHydrationSession = null;
    if (!session || session.disposed || !session.appWindow?.isConnected) return null;
    if (normalizeLaunchCorrelation(session.appId) !== normalizeLaunchCorrelation(id)) return null;
    appFlowTrace(session.flowId, "feedback_payload_received", {
        app_id: session.appId,
        action: session.action,
        mode: "ofs_provisional",
        completion_reason: "hydration"
    });
    stopPreExecutionPresentation(session, "hydration");
    const app = session.appWindow;
    setApplicationPresentationPhase(session, "hydrating", { completion_reason: "hydration" });
    appFlowTrace(session.flowId, "feedback_provisional_handoff", {
        app_id: session.appId,
        action: session.action,
        mode: "ofs_provisional",
        elapsed_ms: Math.max(0, Math.round(performance.now() - session.createdAt))
    });
    updateProvisionalApplicationSession(session, "hydrating", "Ladowanie autorytatywnej aplikacji...");
    app.className = "app-window";
    delete app.dataset.ofsWaitBand;
    app.style.removeProperty("width");
    app.style.removeProperty("max-width");
    // The authoritative renderer replaces the provisional title bar. Its old
    // drag listener disappears with that DOM node, so allow the new handle to
    // be bound after hydration.
    delete app.dataset.draggableBound;
    app.dataset.appInterface = type;
    app.dataset.provisionalState = "hydrating";
    return app;
}

function beginApplicationRenderLaunch(id, type) {
    const hydrationSession = activeProvisionalHydrationSession;
    if (hydrationSession
        && !hydrationSession.disposed
        && hydrationSession.appWindow?.isConnected
        && normalizeLaunchCorrelation(hydrationSession.appId) === normalizeLaunchCorrelation(id)) {
        return true;
    }
    return beginApplicationWindowLaunch(id, type);
}

function prepareApplicationRenderWindow(id, type) {
    const hydrated = consumeProvisionalHydrationWindow(id, type);
    const app = hydrated || document.createElement("div");
    const template = normalizeOFSApplicationTemplate(type);
    app.className = ofsVisualLiftEnabled
        ? `app-window ofs-app-template ofs-visual-lift ofs-template-${template}`
        : "app-window ofs-visual-lift-disabled";
    app.dataset.ofsTemplate = template;
    app.dataset.launchKey = buildApplicationWindowLaunchKey(id, type);
    app.dataset.appFlowId = getCurrentAppFlowId();
    app.dataset.appId = id;
    app.dataset.appInterface = type;
    const launchContext = applyApplicationLaunchContext(app, { id, interface: type });
    const appTitle = String(
        app.dataset.appTitle || launchContext.app_name || id || "Aplikacja"
    ).trim() || "Aplikacja";
    // Preserve the public application name across provisional -> hydrated DOM
    // replacement. Technical app_id remains available separately in appId.
    app.dataset.appTitle = appTitle;
    if (!hydrated) {
        const position = findAvailablePosition();
        app.style.top = `${position.top}px`;
        app.style.left = `${position.left}px`;
    }
    return { app, hydrated: Boolean(hydrated), appTitle };
}

function normalizeOFSApplicationTemplate(interfaceName) {
    const value = String(interfaceName || "").trim().toLowerCase();
    if (value === "button_choice" || value === "button_choices") return "button-choice";
    if (value === "progressbar_random" || value === "random_progress") return "progressbar-random";
    if (value === "terminal") return "terminal";
    return "window";
}

function resolveApplicationBrandModel(app) {
    if (app?._ofsBrandModel) return app._ofsBrandModel;
    const context = currentApplicationLaunchContext(app);
    const content = context.application_content || {};
    const source = {
        name: context.app_name || content.title || app?.dataset?.appId || "Aplikacja",
        icon: content.icon || "",
        creator_username: content.creator_username || "",
        creator_nick: content.creator_nick || "",
        interface: content.interface || app?.dataset?.appInterface || "window"
    };
    const ofs = window.OperationFeedbackSystem;
    app._ofsBrandModel = ofs?.buildApplicationBrandModel
        ? ofs.buildApplicationBrandModel(source)
        : Object.freeze({ name: source.name, icon: source.icon || "▣" });
    return app._ofsBrandModel;
}

function createApplicationBrandMark(model, placement) {
    const config = model && model[placement] ? model[placement] : {};
    const mark = document.createElement("div");
    mark.className = `ofs-brand-mark ofs-brand-${placement.replace(/_/g, "-")}`;
    mark.dataset.logoMode = config.mode || "icon_only";
    mark.dataset.fontScale = config.font_scale || "standard";
    mark.dataset.anchor = config.anchor || "start";
    mark.style.setProperty("--ofs-brand-weight", String(config.font_weight || 800));

    const icon = document.createElement("span");
    icon.className = "ofs-brand-icon";
    const iconValue = String(model?.icon || "▣");
    if (/^(?:\/static\/|data:image\/(?:png|gif|jpeg|webp);base64,)/i.test(iconValue)) {
        const image = document.createElement("img");
        image.src = iconValue;
        image.alt = "";
        icon.appendChild(image);
    } else {
        icon.textContent = iconValue;
    }
    mark.appendChild(icon);

    const label = document.createElement("span");
    label.className = "ofs-brand-name";
    const accessibleLabel = placement === "author_footer"
        ? (model?.author?.signature || "© CHAOS · Created by CHAOS SYSTEM")
        : (model?.name || "Aplikacja");
    label.textContent = accessibleLabel;
    mark.appendChild(label);
    mark.setAttribute("aria-label", accessibleLabel);
    mark.title = accessibleLabel;
    return mark;
}

function appendApplicationTitleShow(titleScene, model, app) {
    if (!titleScene || titleScene.querySelector(".ofs-title-show")) return;
    const show = document.createElement("div");
    show.className = "ofs-title-show";
    show.dataset.showVariant = String(parseInt(model?.identity_seed || "0", 16) % 3);
    const source = app?.dataset?.launchSource === "map" ? "MAP LINK" : "LOCAL LINK";
    const messages = [
        ["◉", `IDENTITY / ${model?.name || "APPLICATION"}`],
        ["⌁", `CHANNEL / ${source}`],
        ["◇", `AUTHOR / ${model?.author?.nick || "CHAOS SYSTEM"}`],
        ["◆", "RUNTIME / HANDSHAKE ACTIVE"]
    ];
    messages.forEach(([symbol, message]) => {
        const line = document.createElement("div");
        line.className = "ofs-title-show-line";
        const icon = document.createElement("span");
        icon.className = "ofs-title-show-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = symbol;
        const text = document.createElement("span");
        text.textContent = message;
        line.append(icon, text);
        show.appendChild(line);
    });
    titleScene.appendChild(show);
}

function prepareProvisionalApplicationTitle(app) {
    if (!ofsVisualLiftEnabled || !ofsTitleSequenceEnabled || !app) return;
    const content = app.querySelector(".provisional-app-content");
    if (!content || content.querySelector(".ofs-provisional-title-sequence")) return;
    const model = resolveApplicationBrandModel(app);
    const titleScene = document.createElement("section");
    titleScene.className = "ofs-title-sequence ofs-provisional-title-sequence";
    titleScene.dataset.titleClass = model.name_metrics?.name_class || "multi-word";
    titleScene.dataset.titleMotion = model.title_sequence?.motion || "icon-lock";
    titleScene.setAttribute("aria-label", `${model.name}. Uruchamianie aplikacji.`);
    titleScene.appendChild(createApplicationBrandMark(model, "author_logo_header"));
    if ((model.author_logo_header?.mode || "") === "icon_only") {
        const fullTitle = document.createElement("strong");
        fullTitle.className = "ofs-title-full-name";
        fullTitle.textContent = model.name;
        titleScene.appendChild(fullTitle);
    }
    const status = document.createElement("span");
    status.className = "ofs-title-status";
    status.textContent = "BOOT INTERFACE";
    titleScene.appendChild(status);
    appendApplicationTitleShow(titleScene, model, app);
    content.appendChild(titleScene);
}

function prepareApplicationBrandShell(app) {
    if (!ofsVisualLiftEnabled || !app) return null;
    const content = app.querySelector(".ofs-author-shell");
    if (!content || content.dataset.ofsBrandShell === "true") return content;
    const model = resolveApplicationBrandModel(app);
    const feedbackHost = content.querySelector(".operation-feedback-host");
    const authorStage = document.createElement("div");
    authorStage.className = "ofs-author-stage";
    Array.from(content.children).forEach(child => {
        if (child !== feedbackHost) authorStage.appendChild(child);
    });

    const viewport = document.createElement("div");
    viewport.className = "ofs-scene-viewport";
    const titleScene = document.createElement("section");
    titleScene.className = "ofs-title-sequence";
    titleScene.dataset.titleClass = model.name_metrics?.name_class || "multi-word";
    titleScene.dataset.titleMotion = model.title_sequence?.motion || "icon-lock";
    titleScene.setAttribute("aria-label", `${model.name}. Uruchamianie aplikacji.`);
    titleScene.appendChild(createApplicationBrandMark(model, "author_logo_header"));
    if ((model.author_logo_header?.mode || "") === "icon_only") {
        const fullTitle = document.createElement("strong");
        fullTitle.className = "ofs-title-full-name";
        fullTitle.textContent = model.name;
        titleScene.appendChild(fullTitle);
    }
    const titleStatus = document.createElement("span");
    titleStatus.className = "ofs-title-status";
    titleStatus.textContent = "INTERFACE READY";
    titleScene.appendChild(titleStatus);
    appendApplicationTitleShow(titleScene, model, app);
    viewport.appendChild(titleScene);
    viewport.appendChild(authorStage);
    if (feedbackHost) viewport.appendChild(feedbackHost);

    while (content.firstChild) content.removeChild(content.firstChild);
    content.appendChild(createApplicationBrandMark(model, "author_logo_header"));
    content.appendChild(viewport);
    content.appendChild(createApplicationBrandMark(model, "author_footer"));
    content.dataset.ofsBrandShell = "true";
    app.dataset.ofsTitleClass = model.name_metrics?.name_class || "multi-word";
    app.dataset.ofsTitleMotion = model.title_sequence?.motion || "icon-lock";
    return content;
}

function finishApplicationTitleSequence(app, reason = "complete") {
    if (!app) return;
    if (app._ofsTitleTimer) {
        window.clearTimeout(app._ofsTitleTimer);
        app._ofsTitleTimer = null;
    }
    if (app.dataset.ofsTitleActive !== "true") return;
    delete app.dataset.ofsTitleActive;
    app._ofsTitlePresented = true;
    app._ofsAuthorVisibleAt = performance.now();
    app._ofsTitleEndsAt = 0;
    appFlowTrace(app.dataset.appFlowId, "feedback_title_scene_completed", {
        app_id: app.dataset.appId || "",
        completion_reason: reason
    });
}

function startApplicationTitleSequence(app) {
    const model = resolveApplicationBrandModel(app);
    if (!ofsVisualLiftEnabled || !ofsTitleSequenceEnabled || !model.title_sequence) return;
    if (app._ofsTitlePresented || (app.dataset.ofsTitleActive === "true" && app._ofsTitleTimer)) return;
    app.dataset.ofsTitleActive = "true";
    appFlowTrace(app.dataset.appFlowId, "feedback_title_scene_started", {
        app_id: app.dataset.appId || "",
        title_class: model.name_metrics?.name_class || "multi-word",
        title_motion: model.title_sequence.motion,
        duration_ms: app.dataset.launchSource === "map"
            ? model.title_sequence.map_duration_ms
            : model.title_sequence.duration_ms
    });
    const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const configuredDuration = app.dataset.launchSource === "map"
        ? model.title_sequence.map_duration_ms
        : model.title_sequence.duration_ms;
    const duration = reducedMotion ? model.title_sequence.readable_ms : configuredDuration;
    app._ofsTitleEndsAt = performance.now() + duration;
    app._ofsTitleTimer = window.setTimeout(() => finishApplicationTitleSequence(app, "elapsed"), duration);
}

function finishApplicationRenderWindow(app, hydrated) {
    if (!app.isConnected) document.body.appendChild(app);
    prepareApplicationBrandShell(app);
    makeDraggable(app);
    app.dataset.ofsAuthorPresented = "true";
    app.dataset.ofsPhase = "author_intro";
    const session = app._provisionalApplicationSession;
    if (session && !session.disposed) {
        updateProvisionalApplicationSession(session, "presenting", "Ladowanie zawartosci aplikacji...");
        setApplicationPresentationPhase(session, "author_intro");
        appFlowTrace(session.flowId, "feedback_author_scene_started", {
            app_id: session.appId,
            action: session.action,
            mode: "ofs_provisional"
        });
        updateProvisionalApplicationSession(session, "interactive", "Aplikacja gotowa.");
    }
    startApplicationTitleSequence(app);
    if (app.dataset.ofsTitleActive !== "true") app._ofsAuthorVisibleAt = performance.now();
}

function hydrateProvisionalApplicationSession(session, appData, item = {}) {
    if (!session || session.disposed || !session.appWindow?.isConnected) return "tombstoned";
    bindProvisionalApplicationReceipt(session, item);
    activeProvisionalHydrationSession = session;
    try {
        launchApplicationEffect(appData);
        if (activeProvisionalHydrationSession === session) activeProvisionalHydrationSession = null;
        return "hydrated";
    } catch (error) {
        activeProvisionalHydrationSession = null;
        updateProvisionalApplicationSession(session, "failed", "Nie udalo sie zaladowac aplikacji.");
        console.error("[app launch] Hydration failed", error);
        return "failed";
    }
}

function resolveApplicationFeedbackAction(appData = {}) {
    const explicit = String(
        appData._map_action_id ||
        appData.map_action_id ||
        appData.action_key ||
        ""
    ).trim();
    if (explicit) return explicit;
    const mapActions = Array.isArray(appData.map_actions) ? appData.map_actions : [];
    return String(mapActions.find(Boolean) || "").trim();
}

function launchApplicationFromEntry(appData = {}, source = "desktop_menu") {
    const launchData = {
        ...appData,
        _source: String(appData._source || source || "desktop_menu").trim(),
        _map_action_id: resolveApplicationFeedbackAction(appData)
    };
    return launchApplicationEffect(launchData);
}

function createApplicationInvocationReceipt(appId = "", target = null) {
    const targetKey = getToolbarTargetStableKey(target || {}) || "no-target";
    const randomPart = (window.crypto && typeof window.crypto.randomUUID === "function")
        ? window.crypto.randomUUID()
        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
    const safeAppId = String(appId || "application").trim().slice(0, 48) || "application";
    let targetHash = 2166136261;
    for (let index = 0; index < targetKey.length; index += 1) {
        targetHash ^= targetKey.charCodeAt(index);
        targetHash = Math.imul(targetHash, 16777619);
    }
    return `manual:${safeAppId}:${(targetHash >>> 0).toString(36)}:${randomPart}`.slice(0, 160);
}

function buildApplicationLaunchContext(appData = {}) {
    const flowId = getCurrentAppFlowId(appData._flow_id || appData.flow_id || appData.debug_flow?.flow_id || "");
    const appId = String(appData.id || appData.app_id || "").trim();
    const name = String(appData.name || appData.app_name || appId || "").trim();
    const explicitLaunchReceipt = String(
        appData._launch_receipt ||
        appData.launch_receipt ||
        appData.receipt ||
        appData._launch_key ||
        ""
    ).trim();
    const aimedTarget = ((toolbarProfile || {}).aimed_target || {});
    const expectedTarget = hasToolbarAimedTarget(aimedTarget) ? {
        target_id: aimedTarget.target_id || aimedTarget.id || "",
        lat: aimedTarget.lat,
        lng: aimedTarget.lng !== undefined ? aimedTarget.lng : aimedTarget.lon,
        label: aimedTarget.label || aimedTarget.display_label || aimedTarget.name || aimedTarget.title || "",
        target_mode: aimedTarget.target_mode || "",
        foreign_area_id: aimedTarget.foreign_area_id || "",
        stable_conflict_id: aimedTarget.stable_conflict_id || "",
        conflict_id: aimedTarget.conflict_id || "",
        expected_owner_username: aimedTarget.expected_owner_username || aimedTarget.contest_owner_username || "",
        ownership_version: aimedTarget.ownership_version
    } : null;
    const launchReceipt = explicitLaunchReceipt || createApplicationInvocationReceipt(
        appId || name,
        expectedTarget
    );
    const launchKey = launchReceipt;
    const actionKey = resolveApplicationFeedbackAction(appData);
    const targetMatchesLaunch = Boolean(
        expectedTarget && toolbarTargetMatchesCaptured(aimedTarget, expectedTarget)
    );
    const securityState = window.OperationFeedbackSystem
        ? window.OperationFeedbackSystem.sanitizeSecurityState(
            targetMatchesLaunch ? aimedTarget.security : null
        )
        : {};
    const applicationContent = window.OperationFeedbackSystem
        ? window.OperationFeedbackSystem.projectApplicationContent(appData)
        : null;
    return {
        flow_id: flowId,
        invocation_id: launchReceipt,
        launch_key: launchKey,
        launch_receipt: launchReceipt,
        source: String(appData._source || appData.source || "").trim(),
        app_id: appId,
        app_name: name,
        expected_target: expectedTarget,
        action_key: actionKey,
        security_state: securityState,
        application_content: applicationContent
    };
}

function applicationResponseMatchesCurrentTarget(context = {}) {
    const expectedTarget = context.expected_target || null;
    const currentTarget = ((toolbarProfile || {}).aimed_target || {});
    if (!hasToolbarAimedTarget(expectedTarget)) return true;
    // Clearing/capturing a target is also a selection change. A late response
    // bound to the former target must not recreate it on an empty toolbar.
    if (!hasToolbarAimedTarget(currentTarget)) return false;
    return toolbarTargetsShareProgressIdentity(expectedTarget, currentTarget);
}

function currentApplicationLaunchContext(appWindow = null) {
    const pending = window.__pendingApplicationLaunchContext || {};
    const dataset = appWindow && appWindow.dataset ? appWindow.dataset : {};
    const feedbackContext = appWindow && appWindow._operationFeedbackLaunchContext
        ? appWindow._operationFeedbackLaunchContext
        : {};
    const flowId = getCurrentAppFlowId(dataset.appFlowId || pending.flow_id || "");
    const appId = String(dataset.appId || pending.app_id || "").trim();
    let expectedTarget = pending.expected_target || null;
    if (dataset.expectedTarget) {
        try {
            expectedTarget = JSON.parse(dataset.expectedTarget);
        } catch (error) {
            console.warn('[gonna-win] Nieprawidlowy zapis celu startowego aplikacji', error);
        }
    }
    const invocationId = String(
        dataset.appInvocationId ||
        pending.invocation_id ||
        dataset.launchReceipt ||
        pending.launch_receipt ||
        ""
    ).trim();
    return {
        flow_id: flowId,
        invocation_id: invocationId,
        launch_key: String(dataset.launchQueueKey || pending.launch_key || invocationId).trim(),
        launch_receipt: String(dataset.launchReceipt || pending.launch_receipt || invocationId).trim(),
        source: String(dataset.launchSource || pending.source || "").trim(),
        app_id: appId,
        app_name: String(dataset.appTitle || pending.app_name || "").trim(),
        expected_target: expectedTarget,
        action_key: String(feedbackContext.action_key || pending.action_key || "").trim(),
        security_state: feedbackContext.security_state || pending.security_state || {},
        application_content: feedbackContext.application_content || pending.application_content || null
    };
}

function gonnaWinLifecycleKey(context = {}, receiptScope = "choice:auto") {
    return [
        String(context.flow_id || "").trim(),
        String(context.launch_receipt || context.invocation_id || "").trim(),
        String(context.app_id || "").trim(),
        String(receiptScope || "choice:auto").trim()
    ].join("|");
}

function getGonnaWinLifecycle(context = {}, receiptScope = "choice:auto") {
    const key = gonnaWinLifecycleKey(context, receiptScope);
    let state = gonnaWinLifecycleStates.get(key);
    if (!state) {
        state = {
            key,
            requestOrdinal: 0,
            canonicalSuccess: false,
            canonicalPayload: null,
            operationIds: new Set(),
            ofsTerminalState: "pending",
            sfxTerminalState: "pending"
        };
        gonnaWinLifecycleStates.set(key, state);
        while (gonnaWinLifecycleStates.size > GONNA_WIN_LIFECYCLE_LIMIT) {
            gonnaWinLifecycleStates.delete(gonnaWinLifecycleStates.keys().next().value);
        }
    }
    return state;
}

function nextGonnaWinRequestOrdinal(context = {}, receiptScope = "choice:auto") {
    const state = getGonnaWinLifecycle(context, receiptScope);
    state.requestOrdinal += 1;
    return state.requestOrdinal;
}

function rememberGonnaWinCanonicalResult(context, receiptScope, payload = {}) {
    const state = getGonnaWinLifecycle(context, receiptScope);
    (payload.created_operations || []).forEach(operation => {
        const operationId = String(operation && operation.operation_id || "").trim();
        if (operationId) state.operationIds.add(operationId);
    });
    if (payload.success === true) {
        state.canonicalSuccess = true;
        state.canonicalPayload = { ...payload };
        state.ofsTerminalState = "success";
        if (payload.captured_target) state.sfxTerminalState = "success";
    }
    return state;
}

function preserveCanonicalGonnaWinSuccess(context, receiptScope, payload = null) {
    const state = getGonnaWinLifecycle(context, receiptScope);
    if (!state.canonicalSuccess || (payload && payload.success === true)) return payload;
    return {
        ...(state.canonicalPayload || { success: true }),
        success: true,
        duplicate: true,
        idempotent_replay: true,
        semantic_success_preserved: true
    };
}

function applyApplicationLaunchContext(appWindow, fallbackAppData = {}) {
    if (!appWindow || !appWindow.dataset) return currentApplicationLaunchContext();
    const context = {
        ...buildApplicationLaunchContext(fallbackAppData),
        ...(window.__pendingApplicationLaunchContext || {})
    };
    appWindow.dataset.appFlowId = context.flow_id || getCurrentAppFlowId();
    appWindow.dataset.appInvocationId = context.invocation_id || context.launch_receipt || "";
    appWindow.dataset.launchQueueKey = context.launch_key || "";
    appWindow.dataset.launchReceipt = context.launch_receipt || "";
    appWindow.dataset.launchSource = context.source || "";
    appWindow.dataset.expectedTarget = context.expected_target
        ? JSON.stringify(context.expected_target)
        : "";
    appWindow._operationFeedbackLaunchContext = Object.freeze({
        action_key: String(context.action_key || "").trim(),
        security_state: context.security_state || {},
        application_content: context.application_content || null
    });
    return currentApplicationLaunchContext(appWindow);
}

function shouldSkipLaunchQueueReceipt(receipt, details = {}) {
    const key = String(receipt || "").trim().toLowerCase();
    if (!key) return false;
    const now = Date.now();
    for (const [recentKey, expiresAt] of recentLaunchQueueReceipts.entries()) {
        if (expiresAt <= now) {
            recentLaunchQueueReceipts.delete(recentKey);
        }
    }
    if ((recentLaunchQueueReceipts.get(key) || 0) > now) {
        hackFlowDebug(details.flow_id || window.__lastHackFlowId || "", "desktop", "launch_queue_skip_receipt", {
            receipt,
            app_name: details.name || "",
            app_id: details.app_id || ""
        });
        return true;
    }
    recentLaunchQueueReceipts.set(key, now + LAUNCH_QUEUE_RECEIPT_TTL_MS);
    return false;
}

function beginApplicationWindowLaunch(id, type) {
    const key = buildApplicationWindowLaunchKey(id, type);
    const now = Date.now();
    for (const existing of document.querySelectorAll('.app-window')) {
        if (existing.dataset.launchKey === key) {
            bringWindowToFront(existing);
            hackFlowDebug(window.__lastHackFlowId || "", "desktop", "app_launch_skip_existing_window", {
                app_id: id,
                interface: type,
                key
            });
            appFlowTrace("", "app_launch_skip_existing_window", { app_id: id, interface: type, key });
            return false;
        }
    }
    for (const [recentKey, expiresAt] of recentApplicationWindowLaunches.entries()) {
        if (expiresAt <= now) {
            recentApplicationWindowLaunches.delete(recentKey);
        }
    }
    if (!key || key.endsWith(":") || (recentApplicationWindowLaunches.get(key) || 0) > now) {
        hackFlowDebug(window.__lastHackFlowId || "", "desktop", "app_launch_skip_recent", {
            app_id: id,
            interface: type,
            key
        });
        appFlowTrace("", "app_launch_skip_recent", { app_id: id, interface: type, key });
        return false;
    }
    recentApplicationWindowLaunches.set(key, now + APP_WINDOW_LAUNCH_DEDUPE_MS);
    hackFlowDebug(window.__lastHackFlowId || "", "desktop", "app_launch_open", {
        app_id: id,
        interface: type,
        key,
        stack: (new Error().stack || "").split("\n").slice(2, 7)
    });
    appFlowTrace("", "app_launch_open", {
        app_id: id,
        interface: type,
        key
    });
    return true;
}

function launchApplicationEffect(appData) {
    if (runSystemLauncherApp(appData)) return;
    const id = appData.id;
    const levels = appData.levels;
    const type = appData.interface;
    const launchContext = buildApplicationLaunchContext(appData);
    const flowId = launchContext.flow_id;
    window.__lastHackFlowId = flowId;
    appFlowTrace(flowId, "launch_application_effect", {
        app_id: id,
        app_name: appData.name || "",
        interface: type,
        invocation_id: launchContext.invocation_id,
        launch_key: launchContext.launch_key,
        expected_target_id: getToolbarTargetStableKey(launchContext.expected_target || {}),
        source: launchContext.source
    });
    const previousContext = window.__pendingApplicationLaunchContext;
    window.__pendingApplicationLaunchContext = launchContext;
    try {
        if (type === "window") app_window(id, levels);
        else if (type === "progressbar_random") app_progressbar_random(id, levels);
        else if (type === "terminal") app_terminal(id, levels);
        else if (type === "button_choices") app_button_choices(id, levels);
        else if (type === "system_launcher") console.warn(`Brak system_launcher dla: ${appData.name || id}`);
        else console.warn(`Nieznany interface: ${type}`);
    } finally {
        window.__pendingApplicationLaunchContext = previousContext || null;
    }
}

function scheduleOperationalAppAutoClose(appWindow) {
    if (!appWindow || !appWindow.isConnected || appWindow.dataset.autoCloseScheduled === "1") return;
    appWindow.dataset.autoCloseScheduled = "1";
    const flowId = getCurrentAppFlowId(appWindow.dataset.appFlowId || "");
    appFlowTrace(flowId, "app_auto_close_scheduled", {
        app_id: appWindow.dataset.appId || "",
        interface: appWindow.dataset.appInterface || "",
        timeout_ms: APP_TERMINAL_AUTO_CLOSE_MS
    });

    const viewport = appWindow.querySelector('.ofs-scene-viewport') || appWindow.querySelector('.app-content');
    let overlay = viewport?.querySelector('.app-auto-close-overlay');
    if (viewport && !overlay) {
        overlay = document.createElement('div');
        overlay.className = 'app-auto-close-overlay';
        overlay.setAttribute('role', 'timer');
        const initialSeconds = Math.ceil(APP_TERMINAL_AUTO_CLOSE_MS / 1000);
        overlay.innerHTML = `<span>SESSION CLOSE</span><strong data-auto-close-seconds>${String(initialSeconds).padStart(2, '0')}</strong><span>s</span>`;
        viewport.appendChild(overlay);
    }
    const deadline = Date.now() + APP_TERMINAL_AUTO_CLOSE_MS;
    const updateCountdown = () => {
        if (!overlay?.isConnected) return;
        const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
        const output = overlay.querySelector('[data-auto-close-seconds]');
        if (output) output.textContent = String(seconds).padStart(2, '0');
        overlay.setAttribute('aria-label', `Okno zamknie sie za ${seconds} sekund.`);
    };
    updateCountdown();
    appWindow._autoCloseCountdownTimer = window.setInterval(updateCountdown, 1000);

    appWindow._autoCloseTimer = window.setTimeout(() => {
        if (!appWindow.isConnected) return;
        appFlowTrace(flowId, "app_auto_closed", {
            app_id: appWindow.dataset.appId || "",
            interface: appWindow.dataset.appInterface || ""
        });
        disposeOperationFeedbackWindow(appWindow, "auto_close");
        appWindow.remove();
        if (typeof renderRunningApps === "function") {
            renderRunningApps();
        }
    }, APP_TERMINAL_AUTO_CLOSE_MS);
}

async function buildIconsFromJsonWithCommand(jsonData) {
    const icons = [];

    for (const app of jsonData) {
        const name = app.name;

        try {
            const action = () => launchApplicationFromEntry(app, "desktop_menu");
            icons.push({
                icon: getLauncherAppIcon(app),
                label: name,
                action
            });

        } catch (err) {
            console.error(`Błąd przy budowaniu ikony ${name}:`, err);
        }
    }

    return icons;
}

function getLauncherAppIcon(app = {}) {
    const id = String(app.id || app.app_id || "").toLowerCase();
    const name = String(app.name || "").toLowerCase();
    const launcher = String(app.system_launcher || "").toLowerCase();
    if (id === "victimpicker" || name === "victim picker" || launcher === "createvictimpickerapp") {
        return "\u2316";
    }
    return app.icon || '\u2753';
}


(async () => {
    try {
        setBootProgress(12, "Budzenie terminala operatora...");
        // const res = await fetch('static/app_config.json');
        const profileData = await getUserProfile();
        if (!profileData) {
            addSystemMessage("danger", "\u{1F4C1} Profil", "\u2716 Brak danych profilu");
            finishBootLoader("Nie udało się wczytać profilu.");
            return;
        }
        const res = profileData.apps;
        
        setBootProgress(34, `Profil aktywny: ${profileData.nick || profileData.username || "operator"}`);
        // const jsonApps = await res.json();
        const jsonApps = profileData.apps || []; 

        setBootProgress(58, `Indeksowanie aplikacji: ${jsonApps.length}`);
        const generatedIcons = await buildIconsFromJsonWithCommand(jsonApps);
        const systemApps = getSystemDesktopApps(profileData);
        const allApps = [...generatedIcons, ...systemApps]; // dodajesz własne z kodu
        setBootProgress(76, "Montowanie paska systemowego...");
        setToolbarLaunchers(allApps, profileData);
        setBootProgress(88, "Odtwarzanie tapety i pozycji ikon...");
        applyDesktopSettings(profileData.desktop_settings || {});
        renderDesktopIcons(allApps, desktopSettings);
        finishBootLoader("ghost_init.pkg zakończony. System gotowy.");
        return;
    } catch (err) {
        console.error("Błąd startu pulpitu:", err);
        finishBootLoader("Tryb awaryjny: pulpit uruchomiony częściowo.");
        return;
    }

    const iconHeight = 100; // wysokość + padding
    const topOffset = 10;
    const leftOffset = 10;
    const colSpacing = 100;

    const windowHeight = window.innerHeight;
    const maxPerColumn = Math.floor((windowHeight - topOffset) / iconHeight);

    allApps.forEach((app, index) => {
        const icon = document.createElement('div');
        icon.className = 'icon';
        icon.innerHTML = `<span style="font-size: 3rem">${app.icon}</span> ${app.label}`;

        const row = index % maxPerColumn;
        const col = Math.floor(index / maxPerColumn);
        icon.style.top = `${topOffset + row * iconHeight}px`;
        icon.style.left = `${leftOffset + col * colSpacing}px`;

        icon.addEventListener('dblclick', app.action);

        // ⬇️ Obsługa przeciągania:
        let isDragging = false;
        let offsetX = 0;
        let offsetY = 0;

        icon.addEventListener('mousedown', (e) => {
            isDragging = true;
            icon.style.zIndex = 999;
            offsetX = e.clientX - icon.offsetLeft;
            offsetY = e.clientY - icon.offsetTop;
            document.body.style.userSelect = 'none';
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            icon.style.left = `${e.clientX - offsetX}px`;
            icon.style.top = `${e.clientY - offsetY}px`;
        });

        window.addEventListener('mouseup', () => {
            isDragging = false;
            icon.style.zIndex = '';
            document.body.style.userSelect = 'auto';
        });

        desktop.appendChild(icon);
    });
})();


function findAvailablePosition(width = 300, height = 200, padding = 20) {
    if (isMobileSafeMode()) {
        return { top: 0, left: 0 };
    }
    const index = document.querySelectorAll('.terminal, .app-window').length;
    const toolbarHeight = 54;
    const step = 28;
    const maxLeft = Math.max(padding, window.innerWidth - width - padding);
    const maxTop = Math.max(padding, window.innerHeight - height - toolbarHeight - padding);
    const spreadX = Math.max(1, Math.floor((maxLeft - padding) / step) + 1);
    const spreadY = Math.max(1, Math.floor((maxTop - padding) / step) + 1);

    return {
        top: padding + ((index % spreadY) * step),
        left: padding + ((index % spreadX) * step)
    };
}

function getInitialMapWindowLayout() {
    if (isMobileSafeMode()) {
        return { top: 0, left: 0, width: window.innerWidth, height: window.innerHeight };
    }
    const padding = 24;
    const toolbarHeight = 64;
    const availableHeight = Math.max(420, window.innerHeight - toolbarHeight - (padding * 2));
    const availableRightWidth = Math.max(420, Math.floor(window.innerWidth * 0.48));
    const isWideDesktop = window.innerWidth >= 1280 && window.innerHeight >= 720;

    if (isWideDesktop) {
        const size = Math.floor(Math.min(860, availableHeight, availableRightWidth));
        return {
            top: padding,
            left: Math.max(padding, window.innerWidth - size - padding),
            width: size,
            height: size
        };
    }

    const width = Math.floor(Math.min(960, window.innerWidth - (padding * 2)));
    const height = Math.floor(Math.min(620, availableHeight));
    const position = findAvailablePosition(width, height, padding);
    return { ...position, width, height };
}




function attachTerminalInputHandler(input, content) {
    input.addEventListener('keydown', async function(e) {
        if (e.key !== 'Enter') return;
        const value = this.value;
        content.innerHTML += `<br>> ${value}`;
        this.value = '';

        try {
            if (content.pendingConfirm) {
                const answer = value.trim().toLowerCase();
                const pending = content.pendingConfirm;

                if (!["y", "yes", "n", "no"].includes(answer)) {
                    content.innerHTML += `<br>Wpisz Y albo N.`;
                    appendTerminalPrompt(content);
                    return;
                }

                content.pendingConfirm = null;

                if (answer === "n" || answer === "no") {
                    content.innerHTML += `<br>Anulowano.`;
                    appendTerminalPrompt(content);
                    return;
                }

                if (pending.action === "userdel") {
                    const deleteRes = await fetch('/api/users/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username: pending.username })
                    });
                    const deleteData = await deleteRes.json();
                    content.innerHTML += `<br>${escapeHTML(deleteData.message || "Operacja zakonczona.")}`;
                    if (deleteData.logout) {
                        setTimeout(() => {
                            window.location.href = deleteData.redirect || '/';
                        }, 500);
                        return;
                    }
                    appendTerminalPrompt(content);
                    return;
                }
            }

            const res = await fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: value })
            });

            const data = await res.json();

            if (data.clear) {
                content.innerHTML = '';
                appendTerminalPrompt(content);
                return;
            }

            if (data.confirm) {
                content.pendingConfirm = data.confirm;
                content.innerHTML += `<br>${escapeHTML(data.confirm.prompt)}`;
                appendTerminalPrompt(content);
                return;
            }

            if (data.response) {
                content.innerHTML += `<br>${data.response.replace(/\n/g, "<br>")}`;
            }

            if (data.target) {
                updateToolbarAimedTarget(data.target);
            }
            notifyCreatedOperations(data);

            if (data.terminalTeleport) {
                await handleTerminalTeleport(content, data.terminalTeleport);
                return;
            }

            if (data.terminalGeolocationRequest) {
                await handleTerminalGeolocationRequest(content, data.terminalGeolocationRequest);
                return;
            }

            if (data.closeTerminal) {
                setTimeout(() => {
                    content.closest('.terminal')?.remove();
                }, 180);
                return;
            }

            if (data.openSystemApp) {
                openSystemAppFromTerminal(data.openSystemApp);
            }

            if (data.logout) {
                setTimeout(() => {
                    window.location.href = authenticatedLogoutUrl();
                }, 350);
                return;
            }

            if (data.runApp && data.applicationEffect) {
                const app = data.applicationEffect;
                const consoleEffect = data.consoleEffect || '';
                const id = app.id;
                const levels = app.levels;
                const type = app.interface;

                // 👇 Wyświetl consoleEffect zanim pojawi się nowy input
                const conDiv = document.createElement('div');
                conDiv.innerHTML = consoleEffect.replace(/\n/g, "<br>");
                content.appendChild(conDiv);

                // 👇 Uruchom aplikację
                launchApplicationFromEntry(app, "terminal");
            }

            // 👇 Dopiero teraz tworzysz nową linię terminala
            const newLine = document.createElement('div');
            newLine.className = 'terminal-line';
            newLine.innerHTML = `
                <label class="terminal-label">user@hostname:~$</label>
                <input type="text" class="terminal-input" autocomplete="off" />
            `;
            content.appendChild(newLine);
            const newInput = newLine.querySelector('input');
            setTimeout(() => newInput.focus(), 10);
            attachTerminalInputHandler(newInput, content);
            content.scrollTop = content.scrollHeight;

        } catch (err) {
            content.innerHTML += `<br><span style="color:red;">\u2716 B\u0142\u0105d komunikacji z serwerem</span>`;
        }
    });
}

function appendTerminalPrompt(content) {
    const newLine = document.createElement('div');
    newLine.className = 'terminal-line';
    newLine.innerHTML = `
        <label class="terminal-label">user@hostname:~$</label>
        <input type="text" class="terminal-input" autocomplete="off" />
    `;
    content.appendChild(newLine);
    const newInput = newLine.querySelector('input');
    setTimeout(() => newInput.focus(), 10);
    attachTerminalInputHandler(newInput, content);
    content.scrollTop = content.scrollHeight;
}

function openSystemAppFromTerminal(appKey) {
    const normalized = String(appKey || '').toLowerCase();
    const existingByKey = {
        map: '.terminal[data-app="map"]',
        browser: '.terminal[data-app="browser"]',
        wallet: '.terminal[data-app="wallet"]',
        radio: '.terminal[data-app="ghost-radio"]',
        cyberner: '.terminal[data-app="email"]',
        files: '.terminal[data-app="files"]',
        profile: '.terminal[data-app="profile"]',
        settings: '.terminal[data-app="settings"]',
        devbugs: '.app-window[data-app="dev-bug-reporter"]'
    };
    const existingSelector = existingByKey[normalized];
    const existing = existingSelector ? document.querySelector(existingSelector) : null;
    if (existing) {
        bringWindowToFront(existing);
        return true;
    }

    const launchers = {
        map: createMap,
        browser: createBrowser,
        wallet: openWalletApp,
        radio: () => window.createGhostHackRadioApp && window.createGhostHackRadioApp(),
        cyberner: createEmailClient,
        files: () => createFileManager(),
        profile: createProfile,
        settings: createSettings,
        devbugs: createDevBugReporterApp
    };
    const launcher = launchers[normalized];
    if (typeof launcher !== "function") return false;

    launcher();
    window.setTimeout(() => {
        const opened = existingSelector ? document.querySelector(existingSelector) : null;
        if (opened) bringWindowToFront(opened);
    }, 0);
    return true;
}

function appendSystemTerminalCommand(content, value) {
    const line = document.createElement('div');
    line.className = 'terminal-line system-terminal-entry system-terminal-entry-command';
    line.innerHTML = `
        <span class="terminal-label">user@hostname:~$</span>
        <span class="system-terminal-command-text"></span>
    `;
    line.querySelector('.system-terminal-command-text').textContent = value;
    content.appendChild(line);
    content.scrollTop = content.scrollHeight;
}

function appendSystemTerminalOutput(content, html, className = "") {
    const line = document.createElement('div');
    line.className = `system-terminal-output ${className}`.trim();
    line.innerHTML = html;
    content.appendChild(line);
    content.scrollTop = content.scrollHeight;
}

function appendSystemTerminalLoader(content) {
    const frames = ['.', '..', '...', '..'];
    let index = 0;
    const line = document.createElement('div');
    line.className = 'system-terminal-output system-terminal-loader';
    line.textContent = frames[index];
    content.appendChild(line);
    content.scrollTop = content.scrollHeight;

    const timer = window.setInterval(() => {
        index = (index + 1) % frames.length;
        line.textContent = frames[index];
    }, 220);

    return () => {
        window.clearInterval(timer);
        line.remove();
    };
}

const GHOST_SCRIPT_COMMAND_DELAY_MS = 2000;

function splitGhostScriptCommands(value) {
    return String(value || "")
        .split(";")
        .map(command => command.trim())
        .filter(Boolean);
}

function waitGhostScriptStep(ms = GHOST_SCRIPT_COMMAND_DELAY_MS) {
    return new Promise(resolve => window.setTimeout(resolve, ms));
}

function appendSystemTerminalScriptStatus(content, command, index, total) {
    appendSystemTerminalOutput(
        content,
        `GhostScript ${index + 1}/${total}: uruchamiam <b>${escapeHTML(command)}</b>...`,
        "system-terminal-console-effect"
    );
}

function validateGeneratedAppNameForScripts(payload, status) {
    const name = String(payload?.name || "").trim();
    if (name.includes(";")) {
        if (status) status.textContent = "Nazwa aplikacji nie moze zawierac srednika (;).";
        return false;
    }
    return true;
}

function showGhostDecisionDialog({
    title = "GHOST SYSTEM",
    message = "",
    details = "",
    confirmLabel = "OK",
    cancelLabel = "ANULUJ",
    tone = "lime"
} = {}) {
    return new Promise(resolve => {
        const existing = document.querySelector(".blacknet-decision-backdrop");
        if (existing) existing.remove();

        const backdrop = document.createElement("div");
        backdrop.className = `blacknet-decision-backdrop tone-${String(tone || "lime").toLowerCase()}`;
        backdrop.innerHTML = `
            <section class="blacknet-decision" role="dialog" aria-modal="true" aria-labelledby="ghost-decision-title">
                <div class="blacknet-decision__scanline"></div>
                <header class="blacknet-decision__header">
                    <span class="blacknet-decision__badge">GHOST SYSTEM</span>
                    <h2 id="ghost-decision-title">${escapeHTML(title)}</h2>
                </header>
                <div class="blacknet-decision__body">
                    <p>${escapeHTML(message)}</p>
                    ${details ? `<p class="blacknet-decision__details">${escapeHTML(details)}</p>` : ""}
                </div>
                <footer class="blacknet-decision__actions">
                    <button type="button" class="blacknet-decision__button is-cancel" data-choice="cancel">${escapeHTML(cancelLabel)}</button>
                    <button type="button" class="blacknet-decision__button is-confirm" data-choice="confirm">${escapeHTML(confirmLabel)}</button>
                </footer>
            </section>
        `;

        let settled = false;
        const finish = accepted => {
            if (settled) return;
            settled = true;
            document.removeEventListener("keydown", handleKeydown, true);
            backdrop.remove();
            resolve(Boolean(accepted));
        };
        const handleKeydown = event => {
            if (event.key === "Escape") {
                event.preventDefault();
                finish(false);
            }
            if (event.key === "Enter") {
                event.preventDefault();
                finish(true);
            }
        };

        backdrop.addEventListener("click", event => {
            const button = event.target.closest("[data-choice]");
            if (!button) {
                if (event.target === backdrop) finish(false);
                return;
            }
            finish(button.dataset.choice === "confirm");
        });
        document.addEventListener("keydown", handleKeydown, true);
        document.body.appendChild(backdrop);
        const confirmButton = backdrop.querySelector(".blacknet-decision__button.is-confirm");
        if (confirmButton) requestAnimationFrame(() => confirmButton.focus());
    });
}

async function handleTerminalTeleport(content, teleport) {
    const lat = Number(teleport?.lat);
    const lng = Number(teleport?.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        appendSystemTerminalOutput(content, "teleport: brak poprawnych wspolrzednych.");
        return false;
    }

    const label = teleport?.label || `${lat.toFixed(6)}, ${lng.toFixed(6)}`;
    const accepted = await showGhostDecisionDialog({
        title: "POTWIERDZENIE TELEPORTU",
        message: `Wykonac teleport do: ${label}?`,
        details: "OK zmieni pozycje operatora i odswiezy mape. ANULUJ zostawi obecna pozycje.",
        confirmLabel: "OK",
        cancelLabel: "ANULUJ",
        tone: "lime"
    });
    if (!accepted) {
        appendSystemTerminalOutput(content, "Teleport anulowany.");
        return false;
    }

    const response = await fetch("/api/blacknet/cta/teleport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            source: "terminal",
            lat,
            lng,
            label: "terminal",
            target_label: label
        })
    });
    const data = await response.json();
    if (!response.ok || data.success === false) {
        appendSystemTerminalOutput(content, escapeHTML(data.message || "Teleport odrzucony."));
        return false;
    }

    appendSystemTerminalOutput(content, escapeHTML(data.message || `Teleport wykonany: ${label}.`));
    if (typeof refreshToolbarProfile === "function") {
        refreshToolbarProfile();
    }
    openSystemAppFromTerminal("map");
    notifyOpenMapsBlacknetFocus({
        mode: "teleport",
        label,
        lat: Number(data?.curently_possition?.lat ?? lat),
        lng: Number(data?.curently_possition?.lng ?? lng),
        position_version: data?.position_version,
        position_updated_at: data?.position_updated_at,
        source: "terminal"
    });
    return true;
}

function terminalGeolocationErrorMessage(error) {
    const code = Number(error?.code);
    if (code === 1) {
        return "Lokalizacja odrzucona. Zezwol na dostep w ustawieniach witryny i ponow komende.";
    }
    if (code === 2) {
        return "Nie mozna ustalic aktualnej lokalizacji urzadzenia.";
    }
    if (code === 3) {
        return "Uplynal limit czasu pobierania lokalizacji. Sprobuj ponownie.";
    }
    return "Pobranie lokalizacji urzadzenia nie powiodlo sie.";
}

async function handleTerminalGeolocationRequest(content, request = {}) {
    if (request?.purpose !== "teleport") {
        appendSystemTerminalOutput(content, "Nieobslugiwane zadanie lokalizacji terminala.");
        return false;
    }
    if (!window.isSecureContext || !navigator.geolocation) {
        appendSystemTerminalOutput(
            content,
            "Geolokalizacja jest niedostepna. Wymagane jest bezpieczne polaczenie HTTPS i obsluga lokalizacji w przegladarce."
        );
        return false;
    }

    appendSystemTerminalOutput(content, "Czekam na zgode przegladarki i aktualna lokalizacje...");
    let position;
    try {
        position = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 30000
            });
        });
    } catch (error) {
        appendSystemTerminalOutput(content, terminalGeolocationErrorMessage(error));
        return false;
    }

    const lat = Number(position?.coords?.latitude);
    const lng = Number(position?.coords?.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        appendSystemTerminalOutput(content, "Przegladarka nie zwrocila poprawnych wspolrzednych.");
        return false;
    }
    const accuracy = Number(position?.coords?.accuracy);
    const label = request?.label || "Aktualna lokalizacja urzadzenia";
    if (Number.isFinite(accuracy)) {
        appendSystemTerminalOutput(content, `Lokalizacja pobrana (dokladnosc ok. ${Math.round(accuracy)} m).`);
    }
    return handleTerminalTeleport(content, { lat, lng, label, accuracy });
}

async function executeSystemTerminalCommand(value, input, content, { echo = true } = {}) {
    if (echo) {
        appendSystemTerminalCommand(content, value);
    }
    const stopLoader = appendSystemTerminalLoader(content);

    try {
        if (content.pendingConfirm) {
            const answer = String(value || "").toLowerCase();
            const pending = content.pendingConfirm;

            if (!["y", "yes", "n", "no"].includes(answer)) {
                appendSystemTerminalOutput(content, "Wpisz Y albo N.");
                return false;
            }

            content.pendingConfirm = null;

            if (answer === "n" || answer === "no") {
                appendSystemTerminalOutput(content, "Anulowano.");
                return true;
            }

            if (pending.action === "userdel") {
                const deleteRes = await fetch('/api/users/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: pending.username })
                });
                const deleteData = await deleteRes.json();
                appendSystemTerminalOutput(content, escapeHTML(deleteData.message || "Operacja zakonczona."));
                if (deleteData.logout) {
                    setTimeout(() => {
                        window.location.href = deleteData.redirect || '/';
                    }, 500);
                    return false;
                }
                return true;
            }
        }

        const res = await fetch('/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ input: value })
        });
        const data = await res.json();
        if (data.clear) {
            content.innerHTML = '';
            return true;
        }

        if (data.confirm) {
            content.pendingConfirm = data.confirm;
            appendSystemTerminalOutput(content, escapeHTML(data.confirm.prompt));
            return false;
        }

        if (data.response) {
            appendSystemTerminalOutput(content, data.response.replace(/\n/g, "<br>"));
        }

        if (data.target && applicationResponseMatchesCurrentTarget(context)) {
            updateToolbarAimedTarget(data.target);
        }
        notifyCreatedOperations(data);

        if (data.terminalTeleport) {
            stopLoader();
            return await handleTerminalTeleport(content, data.terminalTeleport);
        }

        if (data.terminalGeolocationRequest) {
            stopLoader();
            return await handleTerminalGeolocationRequest(content, data.terminalGeolocationRequest);
        }

        if (data.closeTerminal) {
            setTimeout(() => {
                content.closest('.terminal')?.remove();
            }, 180);
            return false;
        }

        if (data.openSystemApp) {
            openSystemAppFromTerminal(data.openSystemApp);
        }

        if (data.logout) {
            setTimeout(() => {
                window.location.href = authenticatedLogoutUrl();
            }, 350);
            return false;
        }

        if (data.runApp && data.applicationEffect) {
            const app = data.applicationEffect;
            const consoleEffect = data.consoleEffect || '';
            const id = app.id;
            const levels = app.levels;
            const type = app.interface;

            if (consoleEffect) {
                appendSystemTerminalOutput(content, consoleEffect.replace(/\n/g, "<br>"), "system-terminal-console-effect");
            }

            launchApplicationFromEntry(app, "terminal");
        }

        return true;
    } catch (err) {
        appendSystemTerminalOutput(content, '<span style="color:red;">Blad komunikacji z serwerem</span>');
        return false;
    } finally {
        stopLoader();
        window.requestAnimationFrame(() => {
            input?.focus();
            content.scrollTop = content.scrollHeight;
        });
    }
}

function attachSystemTerminalInputHandler(input, content) {
    const form = input.closest('.system-terminal-composer');
    if (!form || form.dataset.systemTerminalBound === "1") return;
    form.dataset.systemTerminalBound = "1";
    let ghostScriptRunning = false;
    const commandHistory = [];
    let historyIndex = -1;
    let historyDraft = "";

    input.addEventListener("keydown", (event) => {
        if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
        if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
        if (!commandHistory.length) return;

        event.preventDefault();
        if (event.key === "ArrowUp") {
            if (historyIndex === -1) {
                historyDraft = input.value;
                historyIndex = commandHistory.length - 1;
            } else {
                historyIndex = Math.max(0, historyIndex - 1);
            }
            input.value = commandHistory[historyIndex] || "";
        } else {
            if (historyIndex === -1) return;
            historyIndex += 1;
            if (historyIndex >= commandHistory.length) {
                historyIndex = -1;
                input.value = historyDraft;
            } else {
                input.value = commandHistory[historyIndex] || "";
            }
        }

        window.requestAnimationFrame(() => {
            input.setSelectionRange(input.value.length, input.value.length);
        });
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const value = input.value.trim();
        if (!value || ghostScriptRunning) return;

        if (commandHistory[commandHistory.length - 1] !== value) {
            commandHistory.push(value);
            if (commandHistory.length > 80) commandHistory.shift();
        }
        historyIndex = -1;
        historyDraft = "";

        const scriptCommands = content.pendingConfirm ? [value] : splitGhostScriptCommands(value);
        if (!scriptCommands.length) return;

        input.value = '';
        input.disabled = true;

        if (scriptCommands.length === 1) {
            await executeSystemTerminalCommand(scriptCommands[0], input, content, { echo: true });
            input.disabled = false;
            window.requestAnimationFrame(() => input.focus());
            return;
        }

        ghostScriptRunning = true;
        appendSystemTerminalCommand(content, value);
        appendSystemTerminalOutput(
            content,
            `GhostScript: wykryto ${scriptCommands.length} komend. Wykonuje sekwencje co ${GHOST_SCRIPT_COMMAND_DELAY_MS / 1000}s.`,
            "system-terminal-console-effect"
        );

        try {
            for (let index = 0; index < scriptCommands.length; index += 1) {
                const command = scriptCommands[index];
                appendSystemTerminalScriptStatus(content, command, index, scriptCommands.length);
                const canContinue = await executeSystemTerminalCommand(command, input, content, { echo: false });
                if (!canContinue) break;
                if (index < scriptCommands.length - 1) {
                    await waitGhostScriptStep();
                }
            }
        } finally {
            input.disabled = false;
            ghostScriptRunning = false;
            window.requestAnimationFrame(() => {
                input.focus();
                content.scrollTop = content.scrollHeight;
            });
        }
    });
}

function setupSystemTerminalKeyboardGuard(term) {
    if (!term || term.dataset.keyboardGuardBound === "1") return;
    term.dataset.keyboardGuardBound = "1";

    const updateOffset = () => {
        let offset = 0;
        if (isMobileSafeMode() && window.visualViewport) {
            offset = Math.max(0, window.innerHeight - window.visualViewport.height - window.visualViewport.offsetTop);
        }
        term.style.setProperty('--terminal-keyboard-offset', `${Math.round(offset)}px`);

        const content = term.querySelector('.content');
        const input = term.querySelector('.system-terminal-input');
        if (content && input && document.activeElement === input) {
            window.requestAnimationFrame(() => {
                content.scrollTop = content.scrollHeight;
                input.scrollIntoView({ block: "nearest", inline: "nearest" });
            });
        }
    };

    const scheduleUpdate = () => window.requestAnimationFrame(updateOffset);
    term.addEventListener('focusin', scheduleUpdate);
    term.addEventListener('focusout', () => {
        window.setTimeout(scheduleUpdate, 120);
    });
    window.addEventListener('resize', scheduleUpdate);
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', scheduleUpdate);
        window.visualViewport.addEventListener('scroll', scheduleUpdate);
    }

    term.querySelector('.close-btn')?.addEventListener('click', () => {
        window.removeEventListener('resize', scheduleUpdate);
        if (window.visualViewport) {
            window.visualViewport.removeEventListener('resize', scheduleUpdate);
            window.visualViewport.removeEventListener('scroll', scheduleUpdate);
        }
    }, { once: true });

    updateOffset();
}

function addSystemMessage(type, title, text) {
    fetch('/add-system-message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Hack-Flow-Id': window.__lastHackFlowId || ''
        },
        body: JSON.stringify({
            type: type,
            title: title,
            text: text
        })
    })
    .then(res => res.json())
    .then(res => {
        if (res.status !== "success") {
            console.warn("⚠️ Błąd dodawania wiadomości:", res.message || res.error);
        }
    })
    .catch(err => {
        console.error("❌ Błąd połączenia z serwerem", err);
    });
}

function setAppButtonGroupPending(buttons, activeButton, pending, pendingText = "Poczekaj chwilę...") {
    const list = Array.from(buttons || []);
    list.forEach(button => {
        if (!button) return;
        if (pending) {
            if (button.dataset.originalDisabled === undefined) {
                button.dataset.originalDisabled = button.disabled ? "1" : "0";
            }
            if (button === activeButton && button.dataset.originalHtml === undefined) {
                button.dataset.originalHtml = button.innerHTML;
            }
            button.disabled = true;
            if (button === activeButton) {
                button.classList.add("is-loading");
                button.innerHTML = `<span class="app-button-spinner" aria-hidden="true"></span><span>${escapeHTML(pendingText)}</span>`;
            }
            return;
        }

        const wasDisabled = button.dataset.originalDisabled === "1";
        button.disabled = wasDisabled;
        delete button.dataset.originalDisabled;
        if (button.dataset.originalHtml !== undefined) {
            button.innerHTML = button.dataset.originalHtml;
            delete button.dataset.originalHtml;
        }
        button.classList.remove("is-loading");
    });
}

const APP_WAIT_LOG_MESSAGES = [
    "connection=false // retry ghost bus",
    "reconnecting runtime channel",
    "packet retry // target state",
    "waiting for operation receipt",
    "syncing source of truth",
    "network overload // backoff",
    "confirming tool effect",
    "rebuilding local view",
    "handshake timeout // retry route",
    "ghost bus unavailable // probing fallback",
    "runtime channel lost // restoring session",
    "target state pending // await commit",
    "operation receipt missing // rescan queue",
    "source of truth locked // retry later",
    "network jitter detected // stabilizing stream",
    "tool effect pending // verify remote state",
    "local snapshot stale // requesting delta",
    "delta sequence gap // rebuilding cache",
    "world state delayed // hold interface",
    "remote worker busy // waiting slot",
    "packet acknowledged // awaiting apply",
    "command accepted // pending execution",
    "execution delayed // node under load",
    "state mutation queued // wait commit",
    "commit hash pending // verify ledger",
    "ghost relay saturated // applying backoff",
    "route unstable // switching relay",
    "relay switch complete // resuming sync",
    "runtime pulse missing // health check",
    "health check pending // node silent",
    "node recovered // replaying packets",
    "replaying missed deltas // stand by",
    "map snapshot pending // loading world layer",
    "actor registry syncing // partial state",
    "target registry syncing // hold selection",
    "territory state pending // resolving owner",
    "cluster topology syncing // verify pillars",
    "operation lock active // waiting release",
    "operation lock expired // retry command",
    "reservation pending // checking target claim",
    "target claim conflict // resolving priority",
    "ghost marker pending // awaiting projection",
    "teleport receipt missing // verify position",
    "position update pending // prevent rollback",
    "movement stream delayed // holding coordinates",
    "avatar state stale // fetching authority",
    "inventory delta pending // verify balance",
    "wallet delta delayed // awaiting ledger",
    "reward receipt pending // checking payout",
    "loot assignment pending // reserve object",
    "loot state conflict // reconcile ownership",
    "application queue busy // waiting executor",
    "tool runtime cold // warming process",
    "tool runtime ready // sending payload",
    "payload fragmented // reassembling packet",
    "payload checksum pending // verify integrity",
    "checksum mismatch // requesting retransmit",
    "packet retransmit scheduled // hold state",
    "server response delayed // keep channel open",
    "gateway overload // exponential backoff",
    "gateway recovered // resuming requests",
    "session token refresh // keep identity",
    "identity check pending // verify profile",
    "profile snapshot locked // avoid overwrite",
    "profile delta queued // merge pending",
    "session profile syncing // preserve progress",
    "security state pending // await authority",
    "actions_allowed stale // refreshing scope",
    "aimed_target stale // validating selection",
    "current_position stale // validating coordinates",
    "local prediction paused // authority missing",
    "authority response received // applying state",
    "state apply pending // render blocked",
    "render queue saturated // dropping frames",
    "ui projection stale // rebuild requested",
    "desktop runtime syncing // reopen channel",
    "terminal bus busy // queueing message",
    "terminal response pending // no output yet",
    "command pipe blocked // flushing buffer",
    "buffer flush pending // retry write",
    "log stream delayed // reconnecting tail",
    "trace channel unavailable // fallback logger",
    "event stream paused // catch-up required",
    "event backlog detected // draining queue",
    "draining event backlog // keep interface idle",
    "world digest delayed // awaiting publisher",
    "blacknet signal pending // verify facts",
    "radio state syncing // preserve playback",
    "media channel interrupted // restoring buffer",
    "ghostnetwork cycle state pending // reload snapshot",
    "machine part state syncing // verify activation",
    "part reservation pending // await hack result",
    "activation receipt missing // check topology",
    "topology update queued // rebuild circuit",
    "half-line projection pending // calculate endpoint",
    "machine circuit incomplete // waiting second node",
    "ghost signal pending // cycle not closed",
    "cycle lock active // await final commit",
    "cycle archive pending // seal history",
    "territory conflict active // operation blocked",
    "pillar ownership pending // recalculate cluster",
    "cluster boundary stale // rebuild polygon",
    "map layer pending // request markers",
    "marker projection delayed // rendering fallback",
    "victim scan running // collecting nearby nodes",
    "scan results delayed // sorting targets",
    "target list stale // refreshing distance",
    "motorcycle position pending // verify scan origin",
    "operation controller syncing // load context",
    "territory controller syncing // load clusters",
    "ghost suite snapshot pending // wait delta",
    "recovery mode active // rebuilding authoritative view",
    "snapshot version mismatch // request full state",
    "full state requested // pause local writes",
    "full state received // applying snapshot",
    "local writes paused // prevent race condition",
    "race condition detected // reconcile timestamps",
    "late request rejected // newer state exists",
    "rollback prevented // authority version newer",
    "duplicate command ignored // idempotency key",
    "idempotency check pending // await ledger",
    "worker heartbeat delayed // probing process",
    "worker restart detected // restoring queue",
    "process supervisor syncing // verify runtime",
    "service degraded // limited operations",
    "service recovering // gradually reopening channel",
    "operation channel restored // resume interface"
];

function startAppWaitLog(container, options = {}) {
    const root = container && typeof container.querySelector === "function" ? container : null;
    if (!root) return () => {};
    const content = root.querySelector('.operation-feedback-host, .app-content, .map-tool-picker-shell') || root;
    let log = content.querySelector('.app-wait-log');
    if (!log) {
        log = document.createElement('div');
        log.className = 'app-wait-log';
        content.appendChild(log);
    }

    const prefix = options.prefix || "GhostSystem 2108";
    const prefersReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let messageIndex = 0;
    let timerId = null;
    let stopped = false;

    function renderNextMessage() {
        if (stopped) return;
        const msg = APP_WAIT_LOG_MESSAGES[messageIndex % APP_WAIT_LOG_MESSAGES.length];
        messageIndex += 1;
        log.textContent = `${prefix} // ${msg}`;
        log.classList.add('is-active');
        const delay = prefersReducedMotion ? 2800 : 1200 + Math.floor(Math.random() * 1200);
        timerId = window.setTimeout(renderNextMessage, delay);
    }

    renderNextMessage();

    return () => {
        stopped = true;
        if (timerId) {
            window.clearTimeout(timerId);
        }
        log.classList.remove('is-active');
        log.textContent = "";
    };
}

function beginOperationFeedbackRequest(appWindow, appId, { legacyWait = true, receiptScope = "choice:auto" } = {}) {
    if (appWindow?.dataset) appWindow.dataset.ofsPhase = "executing";
    const provisionalSession = appWindow?._provisionalApplicationSession;
    if (provisionalSession && !provisionalSession.disposed) {
        updateProvisionalApplicationSession(provisionalSession, "executing", "Operacja w toku...");
        setApplicationPresentationPhase(provisionalSession, "executing");
    }
    const context = currentApplicationLaunchContext(appWindow);
    const lifecycle = getGonnaWinLifecycle(context, receiptScope);
    const feedbackOwnerKey = gonnaWinLifecycleKey(context, receiptScope);
    const feedbackOwners = appWindow
        ? (appWindow._gonnaWinFeedbackOwners = appWindow._gonnaWinFeedbackOwners || {})
        : null;
    if (feedbackOwners && feedbackOwners[feedbackOwnerKey]) {
        return feedbackOwners[feedbackOwnerKey];
    }
    const ofs = window.OperationFeedbackSystem;
    let session = null;
    let stopLegacy = () => {};
    let legacyStarted = false;
    const startLegacyFallback = () => {
        if (!legacyWait || legacyStarted) return;
        legacyStarted = true;
        stopLegacy = startAppWaitLog(appWindow);
    };

    if (ofs && ofs.isEnabled(context.action_key)) {
        session = ofs.createSession({
            actionKey: context.action_key,
            presentationMode: ofs.presentationModeForAction(
                context.action_key,
                context.application_content?.interface || appWindow?.dataset?.appInterface || ""
            ),
            appId,
            flowId: context.flow_id,
            launchReceipt: context.launch_receipt,
            rendererHost: appWindow?.querySelector?.('.operation-feedback-host')
                || appWindow?.querySelector?.('.app-content')
                || null,
            appWindow,
            securityState: context.security_state,
            applicationContent: context.application_content,
            authorIntroPresented: appWindow?.dataset?.ofsAuthorPresented === "true",
            onProfileUnavailable: startLegacyFallback,
            onTrace: (eventName, details) => appFlowTrace(context.flow_id, eventName, {
                app_id: appId,
                ...details
            })
        });
    }

    if (!session && legacyWait) {
        startLegacyFallback();
    }

    const feedbackOwner = {
        session,
        complete(payload) {
            const semanticPayload = preserveCanonicalGonnaWinSuccess(context, receiptScope, payload);
            if (lifecycle.canonicalSuccess && payload && payload.success !== true) {
                appFlowTrace(context.flow_id, "ofs_false_failure_suppressed", {
                    app_id: appId,
                    receipt_scope: receiptScope,
                    ofs_terminal_state: lifecycle.ofsTerminalState
                });
                return false;
            }
            rememberGonnaWinCanonicalResult(context, receiptScope, semanticPayload || {});
            finishApplicationTitleSequence(appWindow, "payload_received");
            stopLegacy();
            if (session) session.complete(semanticPayload);
            const terminalSysinfo = appWindow?.querySelector?.('[data-terminal-sysinfo]');
            if (terminalSysinfo) {
                const sysinfo = semanticPayload && semanticPayload.success === false ? "FAILED" : "COMPLETE";
                terminalSysinfo.dataset.terminalSysinfo = sysinfo;
                terminalSysinfo.textContent = sysinfo;
            }
            if (provisionalSession && !provisionalSession.disposed) {
                updateProvisionalApplicationSession(provisionalSession, "completing", "Finalizacja wyniku...");
                setApplicationPresentationPhase(provisionalSession, "completing");
            }
            return true;
        },
        presentProgressCompletion(items, success) {
            if (!session || typeof session.presentProgressCompletion !== "function") return false;
            return session.presentProgressCompletion(items, success);
        },
        fail(reason) {
            if (lifecycle.canonicalSuccess) {
                appFlowTrace(context.flow_id, "ofs_transport_failure_suppressed", {
                    app_id: appId,
                    receipt_scope: receiptScope,
                    reason: String(reason || "request_failed"),
                    ofs_terminal_state: lifecycle.ofsTerminalState
                });
                const terminalSysinfo = appWindow?.querySelector?.('[data-terminal-sysinfo]');
                if (terminalSysinfo) {
                    terminalSysinfo.dataset.terminalSysinfo = "COMPLETE";
                    terminalSysinfo.textContent = "COMPLETE";
                }
                return false;
            }
            finishApplicationTitleSequence(appWindow, "request_failed");
            stopLegacy();
            if (session) session.fail(reason);
            const terminalSysinfo = appWindow?.querySelector?.('[data-terminal-sysinfo]');
            if (terminalSysinfo) {
                terminalSysinfo.dataset.terminalSysinfo = "FAILED";
                terminalSysinfo.textContent = "FAILED";
            }
            if (provisionalSession && !provisionalSession.disposed) {
                updateProvisionalApplicationSession(provisionalSession, "failed", "Operacja zakonczona bledem.");
                setApplicationPresentationPhase(provisionalSession, "failed");
            }
            lifecycle.ofsTerminalState = "failed";
            return true;
        }
    };
    if (feedbackOwners) feedbackOwners[feedbackOwnerKey] = feedbackOwner;
    return feedbackOwner;
}

function startLegacyAppWaitUnlessFeedbackEnabled(appWindow) {
    const context = currentApplicationLaunchContext(appWindow);
    const ofs = window.OperationFeedbackSystem;
    if (ofs && ofs.isEnabled(context.action_key)) return () => {};
    if (appWindow) appWindow._legacyAppWaitActive = true;
    const stopWaitLog = startAppWaitLog(appWindow);
    return () => {
        stopWaitLog();
        if (appWindow) appWindow._legacyAppWaitActive = false;
    };
}

function disposeOperationFeedbackWindow(appWindow, reason = "window_closed") {
    if (appWindow?._autoCloseCountdownTimer) {
        window.clearInterval(appWindow._autoCloseCountdownTimer);
        appWindow._autoCloseCountdownTimer = null;
    }
    if (appWindow?._autoCloseTimer) {
        window.clearTimeout(appWindow._autoCloseTimer);
        appWindow._autoCloseTimer = null;
    }
    finishApplicationTitleSequence(appWindow, reason);
    const ofs = window.OperationFeedbackSystem;
    if (ofs) ofs.disposeWindowSession(appWindow, reason);
    disposeProvisionalApplicationSession(appWindow?._provisionalApplicationSession, reason);
}

function formatHackAccessTime(seconds) {
    const safeSeconds = Math.max(0, Number(seconds) || 0);
    const mins = Math.floor(safeSeconds / 60);
    const secs = safeSeconds % 60;
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

function renderSystemLogReaderLogs(container, payload = {}) {
    const logs = Array.isArray(payload.logs) ? payload.logs : [];
    if (!logs.length) {
        container.innerHTML = '<div class="system-log-reader-empty">Brak logow.</div>';
        return;
    }

    container.innerHTML = logs.map(log => `
        <article class="system-log-reader-entry ${escapeHTML(String(log.type || 'info'))}">
            <header>
                <strong>${escapeHTML(String(log.title || 'System'))}</strong>
                <span>${escapeHTML(String(log.type || 'info'))}</span>
            </header>
            <p>${escapeHTML(String(log.text || ''))}</p>
            <footer>
                ${log.status ? `<span>status: ${escapeHTML(String(log.status))}</span>` : ''}
                ${log.created_at ? `<span>${escapeHTML(String(log.created_at))}</span>` : ''}
            </footer>
        </article>
    `).join('');
}

function openSystemLogReaderApp(payload = {}) {
    const app = document.createElement('div');
    app.className = 'app-window system-log-reader-window';
    const position = findAvailablePosition(520, 420);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;

    const access = payload.access || {};
    const victimName = access.victim_nick || access.victim_username || 'unknown';
    const secondsLeft = access.seconds_left ?? playerHackAccessState?.seconds_left ?? 0;
    app.innerHTML = `
        <div class="title-bar">System Log Reader <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="system-log-reader-content">
            <div class="system-log-reader-meta">
                <span>victim: <b>${escapeHTML(String(victimName))}</b></span>
                <span>access: <b data-system-log-reader-countdown>${formatHackAccessTime(secondsLeft)}</b></span>
            </div>
            <div class="system-log-reader-message">${escapeHTML(String(payload.message || ''))}</div>
            <div class="system-log-reader-list"></div>
        </div>
    `;

    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());
    appFlowTrace(app.dataset.appFlowId, "app_window_rendered", { app_id: id, interface: "progressbar_random" });
    appFlowTrace(app.dataset.appFlowId, "app_window_rendered", { app_id: id, interface: "window" });
    renderSystemLogReaderLogs(app.querySelector('.system-log-reader-list'), payload);
}

window.openSystemLogReaderApp = openSystemLogReaderApp;
window.renderSystemLogReaderLogs = renderSystemLogReaderLogs;

function renderFinancialSnifferResult(container, payload = {}) {
    const access = payload.access || {};
    const victimName = access.victim_nick || access.victim_username || 'unknown';
    const stolen = Number(payload.stolen_amount || 0);
    const detected = Boolean(payload.detected);
    container.innerHTML = `
        <div class="financial-sniffer-meta">
            <span>victim: <b>${escapeHTML(String(victimName))}</b></span>
            <span>access: <b>${formatHackAccessTime(access.seconds_left ?? playerHackAccessState?.seconds_left ?? 0)}</b></span>
        </div>
        <div class="financial-sniffer-result ${detected ? 'detected' : 'silent'}">
            <strong>${stolen} ${escapeHTML(String(payload.currency || 'HC'))}</strong>
            <span>${detected ? 'DETECTED' : 'SILENT'}</span>
        </div>
        <p>${escapeHTML(String(payload.message || ''))}</p>
        <div class="financial-sniffer-details">
            <div>Skradziono: <b>${stolen} HC</b></div>
            <div>Detekcja: <b>${detected ? 'tak' : 'nie'}</b></div>
            ${payload.attacker_balance !== undefined ? `<div>Twoje saldo: <b>${Number(payload.attacker_balance || 0)} HC</b></div>` : ''}
            <div>Saldo ofiary: <b>ukryte</b></div>
        </div>
    `;
}

function openFinancialSnifferApp(payload = {}) {
    const app = document.createElement('div');
    app.className = 'app-window financial-sniffer-window';
    const position = findAvailablePosition(460, 340);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.innerHTML = `
        <div class="title-bar">Financial Sniffer <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="financial-sniffer-content"></div>
    `;
    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());
    appFlowTrace(app.dataset.appFlowId, "app_window_rendered", { app_id: id, interface: "terminal" });
    renderFinancialSnifferResult(app.querySelector('.financial-sniffer-content'), payload);
}

window.openFinancialSnifferApp = openFinancialSnifferApp;
window.renderFinancialSnifferResult = renderFinancialSnifferResult;

function renderFriendKickerResult(container, payload = {}) {
    const access = payload.access || {};
    const victimName = access.victim_nick || access.victim_username || 'unknown';
    const removed = Boolean(payload.removed);
    const detected = Boolean(payload.detected);
    container.innerHTML = `
        <div class="friend-kicker-meta">
            <span>victim: <b>${escapeHTML(String(victimName))}</b></span>
            <span>access: <b>${formatHackAccessTime(access.seconds_left ?? playerHackAccessState?.seconds_left ?? 0)}</b></span>
        </div>
        <div class="friend-kicker-result ${removed ? 'removed' : 'failed'}">
            <strong>${removed ? 'CONTACT KICKED' : 'NO CHANGE'}</strong>
            <span>${detected ? 'DETECTED' : 'SILENT'}</span>
        </div>
        <p>${escapeHTML(String(payload.message || ''))}</p>
        <div class="friend-kicker-details">
            <div>Usunieto kontakt: <b>${removed ? 'tak' : 'nie'}</b></div>
            ${payload.kicked_contact_masked ? `<div>Kontakt: <b>${escapeHTML(String(payload.kicked_contact_masked))}</b></div>` : ''}
            <div>Szansa: <b>${Number(payload.chance || 0)}%</b></div>
            <div>Rzut: <b>${Number(payload.roll || 0)}</b></div>
            <div>Lista kontaktow ofiary: <b>ukryta</b></div>
        </div>
    `;
}

function openFriendKickerApp(payload = {}) {
    const app = document.createElement('div');
    app.className = 'app-window friend-kicker-window';
    const position = findAvailablePosition(460, 340);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.innerHTML = `
        <div class="title-bar">Friend Kicker <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="friend-kicker-content"></div>
    `;
    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());
    renderFriendKickerResult(app.querySelector('.friend-kicker-content'), payload);
}

window.openFriendKickerApp = openFriendKickerApp;
window.renderFriendKickerResult = renderFriendKickerResult;

function renderArsenalCleanerResult(container, payload = {}) {
    const access = payload.access || {};
    const victimName = access.victim_nick || access.victim_username || 'unknown';
    const removed = Boolean(payload.removed);
    const detected = Boolean(payload.detected);
    container.innerHTML = `
        <div class="arsenal-cleaner-meta">
            <span>victim: <b>${escapeHTML(String(victimName))}</b></span>
            <span>access: <b>${formatHackAccessTime(access.seconds_left ?? playerHackAccessState?.seconds_left ?? 0)}</b></span>
        </div>
        <div class="arsenal-cleaner-result ${removed ? 'removed' : 'failed'}">
            <strong>${removed ? 'APP REMOVED' : 'NO CHANGE'}</strong>
            <span>${detected ? 'DETECTED' : 'SILENT'}</span>
        </div>
        <p>${escapeHTML(String(payload.message || ''))}</p>
        <div class="arsenal-cleaner-details">
            <div>Usunieto aplikacje: <b>${removed ? 'tak' : 'nie'}</b></div>
            ${payload.removed_app_masked ? `<div>Aplikacja: <b>${escapeHTML(String(payload.removed_app_masked))}</b></div>` : ''}
            ${payload.removed_app_type ? `<div>Typ: <b>${escapeHTML(String(payload.removed_app_type))}</b></div>` : ''}
            <div>Szansa: <b>${Number(payload.chance || 0)}%</b></div>
            <div>Rzut: <b>${Number(payload.roll || 0)}</b></div>
            <div>Lista aplikacji ofiary: <b>ukryta</b></div>
        </div>
    `;
}

function openArsenalCleanerApp(payload = {}) {
    const app = document.createElement('div');
    app.className = 'app-window arsenal-cleaner-window';
    const position = findAvailablePosition(460, 340);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.innerHTML = `
        <div class="title-bar">Arsenal Cleaner <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="arsenal-cleaner-content"></div>
    `;
    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());
    renderArsenalCleanerResult(app.querySelector('.arsenal-cleaner-content'), payload);
}

window.openArsenalCleanerApp = openArsenalCleanerApp;
window.renderArsenalCleanerResult = renderArsenalCleanerResult;

function securityPanelProxySetMessage(container, type, message) {
    const box = container.querySelector('[data-security-proxy-message]');
    if (!box) return;
    box.className = `security-panel-proxy-message ${type || ''}`;
    box.textContent = message || '';
}

function renderSecurityPanelProxy(container, payload = {}) {
    const app = container.closest('.security-panel-proxy-window') || container;
    const security = payload.security || {};
    const victimUsername = payload.victim_username || app.dataset.victimUsername || '';
    const victimNick = payload.victim_nick || app.dataset.victimNick || victimUsername || 'unknown';
    const access = payload.access || {};
    const secondsLeft = access.seconds_left ?? playerHackAccessState?.seconds_left ?? 0;
    const isExpired = Number(secondsLeft) <= 0;
    app.dataset.victimUsername = victimUsername;
    app.dataset.victimNick = victimNick;

    const rows = Object.entries(security)
        .filter(([, value]) => typeof value === 'boolean')
        .map(([key, value]) => `
            <label class="security-panel-proxy-row" title="${escapeHTML(key)}">
                <span>${escapeHTML(key)}</span>
                <input type="checkbox" data-security-key="${escapeHTML(key)}" ${value ? 'checked' : ''} ${isExpired ? 'disabled' : ''}>
                <b>${value ? 'ON' : 'OFF'}</b>
            </label>
        `)
        .join('');

    container.innerHTML = `
        <div class="security-panel-proxy-meta">
            <span>victim: <b>${escapeHTML(String(victimNick))}</b></span>
            <span>access: <b>${formatHackAccessTime(secondsLeft)}</b></span>
        </div>
        <div class="security-panel-proxy-presets">
            ${['open', 'low', 'regular', 'secure', 'all'].map(preset => `
                <button type="button" data-security-preset="${preset}" ${isExpired ? 'disabled' : ''}>${preset}</button>
            `).join('')}
        </div>
        <div class="security-panel-proxy-message ${isExpired ? 'error' : ''}" data-security-proxy-message>
            ${isExpired ? 'Dostep wygasl. Przyciski sa zablokowane.' : escapeHTML(String(payload.message || ''))}
        </div>
        <div class="security-panel-proxy-list">${rows || '<div class="security-panel-proxy-empty">Brak boolean security.</div>'}</div>
    `;

    container.querySelectorAll('[data-security-key]').forEach(toggle => {
        toggle.addEventListener('change', () => {
            updateVictimSecurity(victimUsername, toggle.dataset.securityKey, toggle.checked, container);
        });
    });
    container.querySelectorAll('[data-security-preset]').forEach(btn => {
        btn.addEventListener('click', () => {
            applyVictimSecurityPreset(victimUsername, btn.dataset.securityPreset, container);
        });
    });
}

function openSecurityPanelProxyApp(payload = {}) {
    const app = document.createElement('div');
    app.className = 'app-window security-panel-proxy-window';
    const position = findAvailablePosition(620, 520);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.innerHTML = `
        <div class="title-bar">Security Panel Proxy <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="security-panel-proxy-content"></div>
    `;
    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());
    renderSecurityPanelProxy(app.querySelector('.security-panel-proxy-content'), payload);
}

async function updateVictimSecurity(victimUsername, key, value, container) {
    securityPanelProxySetMessage(container, '', 'Zapisywanie...');
    try {
        const res = await fetch('/api/player-hack/security/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ victim_username: victimUsername, key, value })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || 'Nie udalo sie zapisac zabezpieczenia.');
        }
        renderSecurityPanelProxy(container, {
            ...data,
            victim_username: victimUsername,
            victim_nick: container.closest('.security-panel-proxy-window')?.dataset.victimNick || victimUsername,
            message: data.changed_by_rules && data.changed_by_rules.length
                ? `Reguly konfliktu wylaczyly: ${data.changed_by_rules.join(', ')}`
                : 'Zapisano.'
        });
    } catch (err) {
        securityPanelProxySetMessage(container, 'error', err.message || 'Blad zapisu.');
        container.querySelectorAll('button, input').forEach(el => el.disabled = true);
    }
}

async function applyVictimSecurityPreset(victimUsername, preset, container) {
    securityPanelProxySetMessage(container, '', `Preset ${preset}...`);
    try {
        const res = await fetch('/api/player-hack/security/preset', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ victim_username: victimUsername, preset })
        });
        const data = await res.json();
        if (!res.ok || !data.success) {
            throw new Error(data.error || 'Nie udalo sie zastosowac presetu.');
        }
        renderSecurityPanelProxy(container, {
            ...data,
            victim_username: victimUsername,
            victim_nick: container.closest('.security-panel-proxy-window')?.dataset.victimNick || victimUsername,
            message: `Preset ${preset} zapisany.`
        });
    } catch (err) {
        securityPanelProxySetMessage(container, 'error', err.message || 'Blad presetu.');
        container.querySelectorAll('button, input').forEach(el => el.disabled = true);
    }
}

window.openSecurityPanelProxyApp = openSecurityPanelProxyApp;
window.renderSecurityPanelProxy = renderSecurityPanelProxy;
window.updateVictimSecurity = updateVictimSecurity;
window.applyVictimSecurityPreset = applyVictimSecurityPreset;

function getPlayerHackAccessPanel() {
    let panel = document.getElementById('player-hack-access-panel');
    if (!panel) {
        panel = document.createElement('div');
        panel.id = 'player-hack-access-panel';
        panel.className = 'player-hack-access-panel hidden';
        document.body.appendChild(panel);
    }
    return panel;
}

function renderPlayerHackAccessPanel(access) {
    const panel = getPlayerHackAccessPanel();
    if (!access || !access.active) {
        panel.classList.add('hidden');
        panel.innerHTML = '';
        clearInterval(playerHackAccessTimer);
        playerHackAccessTimer = null;
        playerHackAccessState = null;
        return;
    }

    playerHackAccessState = {
        ...access,
        seconds_left: Math.max(0, Number(access.seconds_left) || 0)
    };

    const tools = Array.isArray(access.tools) ? access.tools : [];
    panel.classList.remove('hidden');
    panel.innerHTML = `
        <div class="player-hack-access-head">
            <span>PLAYER ACCESS</span>
            <strong data-player-hack-countdown>${formatHackAccessTime(playerHackAccessState.seconds_left)}</strong>
        </div>
        <div class="player-hack-access-victim">Dostep do: <b>${escapeHTML(access.victim_nick || access.victim_username || 'unknown')}</b></div>
        <div class="player-hack-access-tools">
            ${tools.map(tool => {
                const installed = tool.installed === true;
                const disabled = !installed || tool.enabled === false;
                const reason = tool.disabled_reason || "Narzedzie nie jest zainstalowane.";
                const price = Number(tool.price || tool.price_hc || 0);
                const title = disabled ? reason : (tool.description || "");
                return `
                <button type="button" class="player-hack-tool-btn" data-tool-id="${escapeHTML(tool.id)}" title="${escapeHTML(title)}" ${disabled ? "disabled" : ""}>
                    <span>${escapeHTML(tool.name || tool.id)}</span>
                    <small>${disabled ? escapeHTML(reason) : `LVL ${Number(tool.required_level || 1)} / ${price} HC`}</small>
                </button>
            `;
            }).join('')}
        </div>
        <div class="player-hack-access-message" data-player-hack-message></div>
    `;

    panel.querySelectorAll('.player-hack-tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            usePlayerHackTool(btn.dataset.toolId);
        });
    });

    clearInterval(playerHackAccessTimer);
    playerHackAccessTimer = setInterval(() => {
        if (!playerHackAccessState) return;
        playerHackAccessState.seconds_left = Math.max(0, playerHackAccessState.seconds_left - 1);
        const countdown = panel.querySelector('[data-player-hack-countdown]');
        if (countdown) countdown.textContent = formatHackAccessTime(playerHackAccessState.seconds_left);
        if (playerHackAccessState.seconds_left <= 0) {
            const msg = panel.querySelector('[data-player-hack-message]');
            if (msg) msg.textContent = 'Dostep wygasl.';
            setTimeout(() => renderPlayerHackAccessPanel(null), 1200);
        }
    }, 1000);
}

async function refreshPlayerHackAccess(prefetched = null) {
    if (prefetched) {
        renderPlayerHackAccessPanel(prefetched);
        return prefetched;
    }
    try {
        const res = await fetch('/api/player-hack/access');
        if (!res.ok) {
            renderPlayerHackAccessPanel(null);
            return null;
        }
        const data = await res.json();
        renderPlayerHackAccessPanel(data);
        return data;
    } catch (err) {
        console.warn('Nie udalo sie pobrac player hack access:', err);
        return null;
    }
}

async function usePlayerHackTool(toolId) {
    if (!playerHackAccessState || !playerHackAccessState.active) return;
    const panel = getPlayerHackAccessPanel();
    const msg = panel.querySelector('[data-player-hack-message]');
    if (msg) msg.textContent = 'Uruchamianie narzedzia...';
    try {
        const res = await fetch('/api/player-hack/tool/use', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                tool_id: toolId,
                victim_username: playerHackAccessState.victim_username
            })
        });
        const data = await res.json();
        if (!res.ok || data.success === false) {
            if (msg) msg.textContent = data.error || 'Narzędzie niedostepne.';
            return;
        }
        if (msg) msg.textContent = data.message || 'Tool placeholder.';
        if (data.result_type === 'system_logs') {
            openSystemLogReaderApp(data);
        }
        if (data.result_type === 'security_panel') {
            openSecurityPanelProxyApp(data);
        }
        if (data.result_type === 'financial_sniffer') {
            openFinancialSnifferApp(data);
            refreshToolbarProfile();
        }
        if (data.result_type === 'friend_kicker') {
            openFriendKickerApp(data);
        }
        if (data.result_type === 'arsenal_cleaner') {
            openArsenalCleanerApp(data);
        }
        if (data.access) refreshPlayerHackAccess(data.access);
    } catch (err) {
        if (msg) msg.textContent = 'Blad komunikacji z narzedziem.';
    }
}

window.refreshPlayerHackAccess = refreshPlayerHackAccess;


const DEV_BUG_CATEGORIES = ["UI", "Map", "Operations", "Files", "Ghost Exchange", "Googleplex", "Login", "Performance", "Other"];
const DEV_BUG_SEVERITIES = ["low", "medium", "high", "blocker"];
const DEV_BUG_STATUSES = ["new", "confirmed", "in_progress", "fixed", "duplicate", "wontfix"];

function getDevBugActiveWindowContext() {
    const active = document.querySelector('.terminal.active, .app-window.active') || document.querySelector('.terminal, .app-window');
    if (!active) return {};
    return {
        title: active.dataset.appTitle || getWindowTitle(active),
        app: active.dataset.app || '',
        window_id: active.dataset.windowId || '',
    };
}

function summarizeDevBugOperations(operations) {
    return (operations || []).slice(0, 20).map(op => ({
        operation_id: op.operation_id,
        operation_type: op.operation_type,
        status: op.status,
        target_label: op.target?.label || op.target?.name || '',
        expires_at: op.expires_at,
        remaining_seconds: op.remaining_seconds,
    }));
}

async function collectDevBugReporterContext() {
    const profile = toolbarProfile || await getUserProfile().catch(() => null) || {};
    let operations = [];
    try {
        const res = await fetch('/api/operations?summary=1');
        const data = await res.json();
        operations = data.active_operations || data.operations || [];
    } catch (err) {
        operations = [];
    }
    return {
        client_timestamp: new Date().toISOString(),
        route: window.location.pathname,
        current_url: window.location.href,
        user_agent: navigator.userAgent,
        viewport: {
            width: window.innerWidth,
            height: window.innerHeight,
        },
        screen: {
            width: window.screen?.width,
            height: window.screen?.height,
        },
        active_window: getDevBugActiveWindowContext(),
        profile: {
            username: profile.username,
            nick: profile.nick,
            level: profile.level,
            hackcoins: profile.hackcoins,
            respect: profile.respect,
            clan: profile.clan,
        },
        aimed_target: profile.aimed_target || {},
        active_operations_summary: summarizeDevBugOperations(operations),
        last_map_action: window.lastMapAction || window.activeMapAction || sessionStorage.getItem('last_map_action') || '',
        last_tool_selection: window.lastToolSelection || sessionStorage.getItem('last_tool_selection') || '',
        TODO_NEXT: "Screenshot upload zostaje osobnym tematem.",
    };
}

function renderDevBugContextSummary(context = {}) {
    const server = context.server || {};
    const session = context.session || context.profile_snapshot || context.profile || {};
    const viewport = context.viewport || {};
    const activeWindow = context.active_window || {};
    const operations = context.active_operations_summary || [];
    const aimed = context.aimed_target || {};
    const rows = [
        ["Build", [server.app_version || context.app_version, server.git_tag, server.commit_hash].filter(Boolean).join(" / ") || "-"],
        ["Env", `${server.app_env || "-"} / dev=${server.dev_mode === undefined ? "-" : server.dev_mode}`],
        ["User", [session.username, session.level ? `LVL ${session.level}` : "", session.hackcoins !== undefined ? `HC ${session.hackcoins}` : "", session.respect !== undefined ? `RSP ${session.respect}` : ""].filter(Boolean).join(" / ") || "-"],
        ["Window", activeWindow.title || "-"],
        ["Route", context.current_url || context.route || "-"],
        ["Viewport", viewport.width && viewport.height ? `${viewport.width}x${viewport.height}` : "-"],
        ["Target", aimed.label || aimed.name || aimed.target_username || "-"],
        ["Operations", operations.length ? operations.map(op => `${op.operation_type}:${op.status}`).join(", ") : "-"],
        ["Last action", context.last_map_action || "-"],
        ["Last tool", context.last_tool_selection || "-"],
    ];
    return `
        <dl class="dev-bug-context dev-bug-context-summary">
            ${rows.map(([label, value]) => `<dt>${escapeHTML(label)}</dt><dd>${escapeHTML(String(value))}</dd>`).join('')}
        </dl>
    `;
}

function createDevBugReporterApp() {
    const app = document.createElement('div');
    app.className = 'app-window dev-bug-reporter';
    app.dataset.app = 'dev-bug-reporter';
    app.dataset.appTitle = 'Dev Bug Reporter';
    app.dataset.appIcon = '\u{1F41E}';
    const position = findAvailablePosition(920, 620);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.style.width = '920px';
    app.style.height = '620px';
    app.innerHTML = `
        <div class="title-bar">Dev Bug Reporter <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content dev-bug-shell" data-dev-bug-view="list">
            <div class="dev-bug-toolbar">
                <input type="search" data-bug-search placeholder="Szukaj zgłoszeń..." />
                <select data-bug-category-filter>
                    <option value="">Wszystkie kategorie</option>
                    ${DEV_BUG_CATEGORIES.map(cat => `<option value="${cat}">${cat}</option>`).join('')}
                </select>
                <select data-bug-status-filter>
                    <option value="">Wszystkie statusy</option>
                    ${DEV_BUG_STATUSES.map(status => `<option value="${status}">${status}</option>`).join('')}
                </select>
                <button type="button" data-bug-show-form>Dodaj zgłoszenie</button>
                <button type="button" data-bug-refresh>Odśwież</button>
            </div>
            <div class="dev-bug-message" data-bug-message></div>
            <div class="dev-bug-layout">
                <aside class="dev-bug-list" data-bug-list>
                    <div class="dev-bug-empty">Ładowanie zgłoszeń...</div>
                </aside>
                <main class="dev-bug-detail">
                    <section class="dev-bug-card" data-bug-detail>
                        <button type="button" class="dev-bug-back" data-bug-back>← Lista zgłoszeń</button>
                        <h3>Wybierz zgłoszenie</h3>
                        <p>Lista jest wspólna dla testerów dev/staging.</p>
                    </section>
                    <section class="dev-bug-card dev-bug-form-card" data-bug-form-card>
                        <button type="button" class="dev-bug-back" data-bug-back>← Lista zgłoszeń</button>
                        <h3>Nowe zgłoszenie</h3>
                        <form data-bug-form>
                            <label>Tytuł
                                <input type="text" name="title" required maxlength="160" placeholder="Krótko: co nie działa?" />
                            </label>
                            <div class="dev-bug-duplicates" data-bug-duplicates hidden></div>
                            <label>Opis
                                <textarea name="description" rows="5" placeholder="Kroki, oczekiwany wynik, aktualny wynik..."></textarea>
                            </label>
                            <div class="dev-bug-form-grid">
                                <label>Kategoria
                                    <select name="category">
                                        ${DEV_BUG_CATEGORIES.map(cat => `<option value="${cat}">${cat}</option>`).join('')}
                                    </select>
                                </label>
                                <label>Severity
                                    <select name="severity">
                                        ${DEV_BUG_SEVERITIES.map(level => `<option value="${level}">${level}</option>`).join('')}
                                    </select>
                                </label>
                            </div>
                            <button type="submit">Dodaj zgłoszenie</button>
                        </form>
                    </section>
                </main>
            </div>
        </div>
    `;
    document.body.appendChild(app);
    makeDraggable(app);
    registerWindowInTaskbar(app);
    bringWindowToFront(app);
    app.querySelector('.close-btn')?.addEventListener('click', () => app.remove());

    const state = {
        reports: [],
        selectedId: null,
        appVersion: '',
        mobileView: 'list',
    };
    const shell = app.querySelector('.dev-bug-shell');

    const isDevBugNarrow = () => app.classList.contains('dev-bug-window-narrow')
        || app.classList.contains('browser-narrow')
        || window.matchMedia('(max-width: 760px), (max-height: 700px)').matches;
    const setDevBugView = (view) => {
        state.mobileView = ["list", "form", "detail"].includes(view) ? view : "list";
        if (shell) shell.dataset.devBugView = state.mobileView;
    };
    const updateDevBugNarrowMode = () => {
        const rect = app.getBoundingClientRect();
        app.classList.toggle('dev-bug-window-narrow', rect.width < 760 || rect.height < 620);
        if (shell) shell.dataset.devBugView = state.mobileView;
    };

    const setMessage = (message, type = 'info') => {
        const box = app.querySelector('[data-bug-message]');
        if (!box) return;
        box.textContent = message || '';
        box.dataset.type = type;
    };

    const renderDetail = (report) => {
        const detail = app.querySelector('[data-bug-detail]');
        if (!detail) return;
        if (!report) {
            detail.innerHTML = `
                <button type="button" class="dev-bug-back" data-bug-back>← Lista zgłoszeń</button>
                <h3>Wybierz zgłoszenie</h3>
                <p>Lista jest wspólna dla testerów dev/staging.</p>
            `;
            detail.querySelector('[data-bug-back]')?.addEventListener('click', () => setDevBugView('list'));
            return;
        }
        detail.innerHTML = `
            <button type="button" class="dev-bug-back" data-bug-back>← Lista zgłoszeń</button>
            <div class="dev-bug-detail-head">
                <h3>#${report.id} ${escapeHTML(report.title)}</h3>
                <select data-bug-status-update>
                    ${DEV_BUG_STATUSES.map(status => `<option value="${status}" ${status === report.status ? 'selected' : ''}>${status}</option>`).join('')}
                </select>
            </div>
            <div class="dev-bug-meta">
                <span>${escapeHTML(report.category)}</span>
                <span>${escapeHTML(report.severity)}</span>
                <span>${escapeHTML(report.status)}</span>
                <span>${escapeHTML(report.app_version || state.appVersion || '')}</span>
            </div>
            <p class="dev-bug-description">${escapeHTML(report.description || 'Brak opisu.')}</p>
            <dl class="dev-bug-context">
                <dt>Autor</dt><dd>${escapeHTML(report.created_by || '-')}</dd>
                <dt>Utworzono</dt><dd>${escapeHTML(report.created_at || '-')}</dd>
                <dt>Aktualizacja</dt><dd>${escapeHTML(report.updated_at || '-')}</dd>
                <dt>URL</dt><dd>${escapeHTML(report.current_url || '-')}</dd>
                <dt>Ekran</dt><dd>${escapeHTML(report.screen || '-')}</dd>
            </dl>
            <h4>Kontekst</h4>
            ${renderDevBugContextSummary(report.context || {})}
            <details class="dev-bug-context-json">
                <summary>Pełny context_json</summary>
                <textarea readonly>${escapeHTML(JSON.stringify(report.context || {}, null, 2))}</textarea>
            </details>
        `;
        detail.querySelector('[data-bug-back]')?.addEventListener('click', () => setDevBugView('list'));
        detail.querySelector('[data-bug-status-update]')?.addEventListener('change', async (event) => {
            await updateBugReportStatus(report.id, event.target.value);
        });
    };

    const renderList = () => {
        const list = app.querySelector('[data-bug-list]');
        if (!list) return;
        if (!state.reports.length) {
            list.innerHTML = '<div class="dev-bug-empty">Brak zgłoszeń dla aktualnych filtrów.</div>';
            renderDetail(null);
            return;
        }
        if (!state.reports.some(item => item.id === state.selectedId)) {
            state.selectedId = state.reports[0]?.id || null;
        }
        list.innerHTML = state.reports.map(report => `
            <button type="button" class="dev-bug-list-item ${report.id === state.selectedId ? 'active' : ''}" data-report-id="${report.id}">
                <strong>${escapeHTML(report.title)}</strong>
                <span>${escapeHTML(report.category)} / ${escapeHTML(report.severity)} / ${escapeHTML(report.status)}</span>
                <small>#${report.id} ${escapeHTML(report.updated_at || report.created_at || '')}</small>
            </button>
        `).join('');
        list.querySelectorAll('[data-report-id]').forEach(button => {
            button.addEventListener('click', () => {
                state.selectedId = Number(button.dataset.reportId);
                renderList();
                setDevBugView('detail');
            });
        });
        renderDetail(state.reports.find(item => item.id === state.selectedId));
    };

    const loadReports = async () => {
        const params = new URLSearchParams();
        const search = app.querySelector('[data-bug-search]')?.value || '';
        const category = app.querySelector('[data-bug-category-filter]')?.value || '';
        const status = app.querySelector('[data-bug-status-filter]')?.value || '';
        if (search) params.set('search', search);
        if (category) params.set('category', category);
        if (status) params.set('status', status);
        setMessage('Ładowanie zgłoszeń...');
        try {
            const res = await fetch(`/api/dev/bug-reports?${params.toString()}`);
            const data = await res.json();
            if (!res.ok || !data.success) {
                setMessage(data.message || 'Dev Bug Reporter jest niedostępny.', 'error');
                return;
            }
            state.reports = data.reports || [];
            state.appVersion = data.app_version || '';
            setMessage(`Zgłoszenia: ${state.reports.length}`, 'success');
            renderList();
        } catch (err) {
            console.error('Dev Bug Reporter load failed:', err);
            setMessage('Błąd połączenia z Dev Bug Reporter.', 'error');
        }
    };

    const updateBugReportStatus = async (reportId, status) => {
        setMessage('Aktualizacja statusu...');
        try {
            const res = await fetch(`/api/dev/bug-reports/${encodeURIComponent(reportId)}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status })
            });
            const data = await res.json();
            if (!res.ok || !data.success) {
                setMessage(data.message || 'Nie udało się zmienić statusu.', 'error');
                return;
            }
            setMessage(data.message || 'Status zmieniony.', 'success');
            await loadReports();
        } catch (err) {
            console.error('Dev Bug Reporter update failed:', err);
            setMessage('Błąd aktualizacji statusu.', 'error');
        }
    };

    const loadSimilar = async (title) => {
        const box = app.querySelector('[data-bug-duplicates]');
        if (!box) return;
        const clean = String(title || '').trim();
        if (clean.length < 4) {
            box.hidden = true;
            box.innerHTML = '';
            return;
        }
        try {
            const res = await fetch(`/api/dev/bug-reports/similar?title=${encodeURIComponent(clean)}`);
            const data = await res.json();
            const reports = (data.reports || []).slice(0, 4);
            if (!reports.length) {
                box.hidden = true;
                box.innerHTML = '';
                return;
            }
            box.hidden = false;
            box.innerHTML = `
                <strong>Możliwe, że taki bug już istnieje.</strong>
                ${reports.map(item => `<span>#${item.id} ${escapeHTML(item.title)}</span>`).join('')}
            `;
        } catch (err) {
            box.hidden = true;
        }
    };

    let debounceTimer = null;
    app.querySelector('[name="title"]')?.addEventListener('input', (event) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => loadSimilar(event.target.value), 280);
    });

    app.querySelector('[data-bug-form]')?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const context = await collectDevBugReporterContext();
        const payload = {
            title: form.title.value,
            description: form.description.value,
            category: form.category.value,
            severity: form.severity.value,
            current_url: window.location.href,
            screen: `${window.innerWidth}x${window.innerHeight}`,
            context
        };
        setMessage('Zapisywanie zgłoszenia...');
        try {
            const res = await fetch('/api/dev/bug-reports', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok || !data.success) {
                setMessage(data.message || 'Nie udało się zapisać zgłoszenia.', 'error');
                return;
            }
            form.reset();
            const dupes = app.querySelector('[data-bug-duplicates]');
            if (dupes) {
                dupes.hidden = true;
                dupes.innerHTML = '';
            }
            state.selectedId = data.report?.id || null;
            setMessage(data.message || 'Zgłoszenie zapisane.', 'success');
            await loadReports();
            setDevBugView('detail');
        } catch (err) {
            console.error('Dev Bug Reporter create failed:', err);
            setMessage('Błąd zapisu zgłoszenia.', 'error');
        }
    });

    app.querySelector('[data-bug-refresh]')?.addEventListener('click', loadReports);
    app.querySelector('[data-bug-show-form]')?.addEventListener('click', () => setDevBugView('form'));
    app.querySelectorAll('[data-bug-back]').forEach(button => {
        button.addEventListener('click', () => setDevBugView('list'));
    });
    app.querySelector('[data-bug-search]')?.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(loadReports, 250);
    });
    app.querySelector('[data-bug-category-filter]')?.addEventListener('change', loadReports);
    app.querySelector('[data-bug-status-filter]')?.addEventListener('change', loadReports);

    updateDevBugNarrowMode();
    const devBugResizeHandler = () => updateDevBugNarrowMode();
    window.addEventListener('resize', devBugResizeHandler);
    let devBugResizeObserver = null;
    if (window.ResizeObserver) {
        devBugResizeObserver = new ResizeObserver(updateDevBugNarrowMode);
        devBugResizeObserver.observe(app);
    }
    app.querySelector('.close-btn')?.addEventListener('click', () => {
        window.removeEventListener('resize', devBugResizeHandler);
        if (devBugResizeObserver) devBugResizeObserver.disconnect();
    }, { once: true });

    loadReports();
}


function createTerminal() {
    terminalCount++;
    const term = document.createElement('div');
    term.className = 'terminal system-terminal-window';
    term.dataset.app = "system-terminal";
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    // term.style.top = `${50 + terminalCount * 20}px`;
    // term.style.left = `${50 + terminalCount * 20}px`;
    const terminalId = `terminal-${terminalCount}`;

    term.innerHTML = `
        <div class="title-bar">Terminal <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="terminal-body">
            <div class="content" id="${terminalId}-content">
                <div class="system-terminal-boot-log">
                    <div>CHAOS Terminal Runtime [v7.09]</div>
                    <div>Copyright Ghost System operators. All routes monitored.</div>
                    <div>Profile loaded. Type <b>help</b> to list commands.</div>
                </div>
            </div>
            <form class="system-terminal-composer">
                <label class="terminal-label" for="${terminalId}-input">user@hostname:~$</label>
                <input id="${terminalId}-input" type="text" class="terminal-input system-terminal-input" autocomplete="off" autocapitalize="off" spellcheck="false" />
            </form>
        </div>
    `;
    document.body.appendChild(term);
    makeDraggable(term);

    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    const content = term.querySelector(`#${terminalId}-content`);
    const input = term.querySelector(`#${terminalId}-input`);
    setTimeout(() => input.focus(), 10);

    term.addEventListener('pointerdown', (event) => {
        if (event.target.closest('.close-btn, input, button, a, select, textarea')) return;
        const selection = window.getSelection?.();
        if (selection && selection.type === "Range") return;
        window.requestAnimationFrame(() => input.focus());
    });

    attachSystemTerminalInputHandler(input, content);
    setupSystemTerminalKeyboardGuard(term);
}

function app_window(id, levels) {
    if (!beginApplicationRenderLaunch(id, "window")) return null;
    const safeLevels = Array.isArray(levels) ? levels : [];
    const level = safeLevels[0] || {};
    const items = Array.isArray(level.list) && level.list.length
        ? level.list
        : [`Aplikacja ${id} uruchomiona.`];
    const windowButtons = Array.isArray(level.buttons) ? level.buttons : [];
    const { app, hydrated, appTitle } = prepareApplicationRenderWindow(id, "window");

    app.innerHTML = `
        <div class="title-bar">${escapeHTML(appTitle)} <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content ofs-author-shell ofs-author-window">
            <header class="ofs-author-header"><span>WINDOW</span><h3>${escapeHTML(level.title || 'Aplikacja')}</h3></header>
            <section class="ofs-author-content"><ul>${items.map(item => `<li>${escapeHTML(String(item || ''))}</li>`).join('')}</ul></section>
            <div class="button-row ofs-author-actions">
                ${windowButtons.map((b, i) => `
                    <button data-action="${escapeHTML(b.action || '')}" data-label="${escapeHTML(b.label || '')}">
                        ${escapeHTML(b.label || '')}
                    </button>
                `).join('')}
            </div>
            <div class="choice-result ofs-author-result" role="status"></div>
            <div class="operation-feedback-host"></div>
        </div>
    `;

    finishApplicationRenderWindow(app, hydrated);
    app.querySelector('.close-btn').addEventListener('click', () => {
        disposeOperationFeedbackWindow(app, "window_closed");
        app.remove();
    });
    appFlowTrace(app.dataset.appFlowId, "app_window_rendered", { app_id: id, interface: "window" });

    const resultBox = app.querySelector('.choice-result');
    const buttons = app.querySelectorAll('.button-row button');

    buttons.forEach(btn => {
        btn.addEventListener('click', async () => {
            if (btn.disabled || btn.classList.contains("is-loading")) return;
            const action = btn.dataset.action;
            const label = btn.dataset.label;
            appFlowTrace(app.dataset.appFlowId, "app_option_click", {
                app_id: id,
                interface: "window",
                choice_id: action,
                label
            });
            if (String(action || "").trim().toLowerCase() === "close") {
                disposeOperationFeedbackWindow(app, "window_action_close");
                app.remove();
                return;
            }
            setAppButtonGroupPending(buttons, btn, true);
            const stopWaitLog = startLegacyAppWaitUnlessFeedbackEnabled(app);
            try {
                const response = await sendGonnaWinRequest(id, action, app);
                const success = response.success === true;
                btn.classList.add("is-selected");

                addSystemMessage('info', '\u25B6 Akcja', `Akcja: ${label} | Wynik: ${success ? "\u2714" : "\u2716"}`);
                resultBox.textContent = success
                    ? "\u2714 Sukces!"
                    : `\u2716 ${response.message || "Niepowodzenie."}`;
                resultBox.style.color = success ? "#0f0" : "#f33";
                if (success) {
                    appFlowTrace(app.dataset.appFlowId, "app_option_success", {
                        app_id: id,
                        interface: "window",
                        choice_id: action
                    });
                    scheduleOperationalAppAutoClose(app);
                }
            } finally {
                stopWaitLog();
                buttons.forEach(button => { button.disabled = true; });
            }
        });
    });
}

async function app_progressbar_random(id, levels) {
    if (!beginApplicationRenderLaunch(id, "progressbar_random")) return null;
    const safeLevels = Array.isArray(levels) ? levels : [];
    const level = safeLevels[0] || {};
    const steps = Array.isArray(level.steps) && level.steps.length
        ? level.steps.slice(0, 12)
        : ["Inicjalizacja modułu...", "Wykonanie operacji...", "Finalizacja..."];
    const { app, hydrated, appTitle } = prepareApplicationRenderWindow(id, "progressbar_random");

    app.innerHTML = `
        <div class="title-bar">${escapeHTML(appTitle)} <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content ofs-author-shell ofs-author-progress">
            <header class="ofs-author-header"><span>EXECUTOR</span><h3>${escapeHTML(level.title || id)}</h3></header>
            <div class="progress-log ofs-progress-list">
                ${steps.map((step, index) => `
                    <div class="ofs-progress-step" data-progress-step="${index}" data-state="running">
                        <div class="ofs-progress-step-head"><span>${escapeHTML(String(step || ''))}</span><b>0%</b></div>
                        <div class="progress-bar"><div class="progress-fill"></div></div>
                    </div>
                `).join('')}
            </div>
            <div class="result-msg ofs-author-result" role="status">RUNNING</div>
            <div class="operation-feedback-host"></div>
        </div>
    `;
    finishApplicationRenderWindow(app, hydrated);
    app.querySelector('.close-btn').addEventListener('click', () => {
        (app._authorProgressTimers || []).forEach(timerId => window.clearTimeout(timerId));
        disposeOperationFeedbackWindow(app, "window_closed");
        app.remove();
    });
    appFlowTrace(app.dataset.appFlowId, "app_window_rendered", { app_id: id, interface: "progressbar_random" });

    const progressRows = Array.from(app.querySelectorAll('.ofs-progress-step'));
    const result = app.querySelector('.result-msg');
    app._authorProgressTimers = [];
    const stopAuthorProgress = () => {
        app._authorProgressTimers.forEach(timerId => window.clearTimeout(timerId));
        app._authorProgressTimers.length = 0;
    };
    const authorProgress = progressRows.map((row, index) => ({
        row,
        fill: row.querySelector('.progress-fill'),
        value: 0,
        cap: [94, 83, 69][index % 3] - Math.floor(index / 3) * 2,
        curve: [0.82, 1.08, 1.48][index % 3],
        index
    }));
    const authorBreathMs = 15000;
    const scheduleProgressTick = (item, startedAt) => {
        const timerId = window.setTimeout(() => {
            if (!app.isConnected) return;
            const elapsedRatio = Math.min(1, Math.max(0, (performance.now() - startedAt) / authorBreathMs));
            item.value = Math.min(item.cap, Math.round(item.cap * Math.pow(elapsedRatio, item.curve)));
            item.fill.style.width = `${item.value}%`;
            item.row.querySelector('b').textContent = `${item.value}%`;
            if (elapsedRatio < 1) scheduleProgressTick(item, startedAt);
        }, 120);
        app._authorProgressTimers.push(timerId);
    };
    const titleRemainingMs = app.dataset.ofsTitleActive === "true"
        ? Math.max(0, Number(app._ofsTitleEndsAt || 0) - performance.now())
        : 0;
    const authorStartTimer = window.setTimeout(() => {
        if (!app.isConnected) return;
        app._ofsAuthorVisibleAt = performance.now();
        const progressStartedAt = performance.now();
        authorProgress.forEach(item => scheduleProgressTick(item, progressStartedAt));
    }, titleRemainingMs);
    app._authorProgressTimers.push(authorStartTimer);
    const requestTimer = window.setTimeout(() => {
        if (!app.isConnected) return;
        result.textContent = "AWAITING PAYLOAD";
        const stopWaitLog = startLegacyAppWaitUnlessFeedbackEnabled(app);
        notifyGonnaWin(id, app, {
            legacyWait: false,
            deferFeedbackStart: false,
            beforeFeedbackComplete: (data, feedback) => {
                stopAuthorProgress();
                const success = data && data.success === true;
                const staleTarget = data && data.blocked && data.reason === 'invalid_target';
                authorProgress.forEach(item => {
                    if (success) item.value = 100;
                    item.fill.style.width = `${item.value}%`;
                    item.row.querySelector('b').textContent = success ? "100%" : `${item.value}%`;
                    item.row.dataset.state = success ? "complete" : "failed";
                });
                result.textContent = success
                    ? (level.result_success || "Operacja zako\u0144czona.")
                    : (staleTarget
                        ? "Cel zmieni\u0142 si\u0119 przed potwierdzeniem. Od\u015bwie\u017c cel i uruchom aplikacj\u0119 ponownie."
                        : (level.result_failure || "Operacja nie powiod\u0142a si\u0119."));
                result.dataset.tone = success ? "success" : (staleTarget ? "warning" : "failure");
                feedback.presentProgressCompletion(authorProgress.map(item => ({
                    label: item.row.querySelector('.ofs-progress-step-head span')?.textContent || `Etap ${item.index + 1}`,
                    value: item.value
                })), success);
                return new Promise(resolve => window.setTimeout(resolve, 1100));
            }
        }).then(success => {
            stopWaitLog();
            if (success) scheduleOperationalAppAutoClose(app);
        }).catch(() => {
            stopWaitLog();
            stopAuthorProgress();
            authorProgress.forEach(item => { item.row.dataset.state = "failed"; });
            result.textContent = "\u2716 B\u0142\u0105d po\u0142\u0105czenia z serwerem.";
            result.dataset.tone = "failure";
        });
    }, titleRemainingMs + authorBreathMs);
    app._authorProgressTimers.push(requestTimer);
}

async function notifyGonnaWin(appId, appWindow = null, {
    legacyWait = false,
    deferFeedbackStart = false,
    beforeFeedbackComplete = null
} = {}) {
    const context = currentApplicationLaunchContext(appWindow);
    const flowId = context.flow_id;
    const receiptScope = "choice:auto";
    let feedback = deferFeedbackStart
        ? null
        : beginOperationFeedbackRequest(appWindow, appId, { legacyWait, receiptScope });
    const ensureFeedback = () => {
        if (!feedback) feedback = beginOperationFeedbackRequest(appWindow, appId, { legacyWait, receiptScope });
        return feedback;
    };
    return enqueueGonnaWinRequest(async () => {
        let response;
        let data;
        try {
            const requestOrdinal = nextGonnaWinRequestOrdinal(context, receiptScope);
            response = await fetch('/gonna-win', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Hack-Flow-Id': flowId
                },
                body: JSON.stringify({
                    app_id: appId,
                    _flow_id: flowId,
                    launch_key: context.launch_key,
                    launch_receipt: context.launch_receipt,
                    launch_source: context.source,
                    expected_target: context.expected_target,
                    request_ordinal: requestOrdinal
                })
            });
            data = await response.json();
            const responseTrace = {
                app_id: appId,
                status: response.status,
                success: data && data.success === true,
                blocked: data && data.blocked === true,
                reason: (data && data.reason) || "",
                error: (data && data.error) || "",
                retryable: data && data.retryable === true,
                expected_target_id: (data && data.expected_target_id) || "",
                current_target_id: (data && data.current_target_id) || "",
                receipt_result: (data && data.operation_lifecycle && data.operation_lifecycle.receipt_result) || "",
                request_ordinal: requestOrdinal
            };
            appFlowTrace(flowId, "gonna_win_response", responseTrace);
            console.info(`[GONNA_WIN_RESPONSE] ${JSON.stringify(responseTrace)}`);
        } catch (error) {
            throw error;
        }
        data = preserveCanonicalGonnaWinSuccess(context, receiptScope, data);
        rememberGonnaWinCanonicalResult(context, receiptScope, data || {});
        if (appWindow) appWindow._lastGonnaWinResult = data;
        if (data.player_hack_access) {
            refreshPlayerHackAccess(data.player_hack_access);
        }
        const responseMatchesCurrentTarget = applicationResponseMatchesCurrentTarget(context);
        if (!responseMatchesCurrentTarget) {
            appFlowTrace(flowId, "stale_target_response_ignored", {
                app_id: appId,
                choice_id: null,
                expected_target: context.expected_target,
                current_target: ((toolbarProfile || {}).aimed_target || {})
            });
        }
        const capturedOnToolbar = responseMatchesCurrentTarget
            ? handleToolbarTargetCapturedResult(data)
            : false;
        if (data.target && !capturedOnToolbar && responseMatchesCurrentTarget) {
            updateToolbarAimedTarget(data.target);
        }
        notifyCreatedOperations(data);
        if (data.success && data.captured_target && !data.semantic_success_preserved) {
            playAuthoritativeCaptureSfx(data.captured_target);
            notifyOpenMapsTargetHacked(data.captured_target);
            refreshToolbarProfile();
        }
        if (typeof beforeFeedbackComplete === "function") {
            await beforeFeedbackComplete(data, ensureFeedback());
        }
        ensureFeedback().complete(data);
        if (response.status === 409 && data.blocked && data.reason === 'invalid_target') {
            console.info('[gonna-win] Cel zmienil sie przed potwierdzeniem runtime', data.target || {});
            refreshToolbarProfile();
            notifyOpenMapsOperationsChanged();
            return false;
        }
        return data.success === true;
    }).catch(err => {
        const preserved = preserveCanonicalGonnaWinSuccess(context, receiptScope, null);
        if (preserved && preserved.success === true) {
            ensureFeedback().complete(preserved);
            appFlowTrace(flowId, "gonna_win_transport_failure_after_canonical_success", {
                app_id: appId,
                receipt_scope: receiptScope,
                ofs_terminal_state: "success"
            });
            return true;
        }
        ensureFeedback().fail(err && err.name ? err.name : "application_result_processing_failed");
        console.error(`❌ Błąd połączenia z /gonna-win dla ${appId}`, err);
        return false; // default przy błędzie
    });
}

function notifyOpenMapsTargetHacked(target) {
    if (!target) return;
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.markMapTargetHacked === 'function') {
                mapWindow.markMapTargetHacked(target);
            }
        } catch (err) {
            console.warn("Nie udało się odświeżyć markera mapy:", err);
        }
    });
}

function authoritativeCaptureSfxVersion(target = {}) {
    return String(
        target.capture_version
        || target.ownership_version
        || target.captured_at
        || target.updated_at
        || "canonical"
    );
}

function playAuthoritativeCaptureSfx(target, options = {}) {
    if (!target || typeof target !== "object" || !window.GameSfx) return false;
    if (options.recovery === true) return false;
    const targetId = String(
        target.target_id || target.id || target.stable_target_id || ""
    ).trim();
    if (!targetId) return false;
    const role = String(target.node_role || target.role || "").toLowerCase();
    const eventKey = role === "pillar"
        ? "capture.conflict_pillar"
        : "capture.target";
    const captureVersion = authoritativeCaptureSfxVersion(target);
    window.GameSfx.play(eventKey, {
        event_id: `target-captured:${targetId}:${captureVersion}`,
        target_id: targetId,
        capture_version: captureVersion,
        node_role: role || "target"
    });
    return true;
}

function playAuthoritativeConflictResolvedSfx(payload = {}) {
    if (!payload || typeof payload !== "object" || !window.GameSfx) return false;
    if (payload.recovery_required === true) return false;
    if (String(payload.status || "").toLowerCase() !== "resolved") return false;
    const conflictId = String(payload.conflict_id || payload.conflict_key || "").trim();
    if (!conflictId) return false;
    const version = String(
        payload.snapshot_version
        || payload.conflict_version
        || payload.geometry_version
        || payload.updated_at
        || "canonical"
    );
    window.GameSfx.play("capture.conflict_resolved", {
        event_id: `conflict-resolved:${conflictId}:${version}`,
        conflict_id: conflictId,
        conflict_version: version
    });
    return true;
}

function notifyOpenMapsOperationsChanged() {
    const refreshes = [];
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.refreshActiveOperations === 'function') {
                refreshes.push(Promise.resolve(mapWindow.refreshActiveOperations()));
            }
        } catch (err) {
            console.warn("Nie udalo sie odswiezyc operacji mapy:", err);
        }
    });
    return Promise.allSettled(refreshes);
}

function notifyOpenMapsBlacknetFocus(focus = {}) {
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const payload = {
                type: 'blacknet-map-focus',
                focus
            };
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.focusBlacknetMapSignal === 'function') {
                mapWindow.focusBlacknetMapSignal(focus);
            } else if (mapWindow && typeof mapWindow.postMessage === 'function') {
                mapWindow.postMessage(payload, window.location.origin);
            }
            frame.addEventListener('load', () => {
                try {
                    if (frame.contentWindow && typeof frame.contentWindow.postMessage === 'function') {
                        frame.contentWindow.postMessage(payload, window.location.origin);
                    }
                } catch (err) {
                    console.warn("Nie udalo sie przekazac fokus BlackNet po ladowaniu mapy:", err);
                }
            }, { once: true });
        } catch (err) {
            console.warn("Nie udalo sie przekazac fokus BlackNet do mapy:", err);
        }
    });
}

function enqueueGonnaWinRequest(task) {
    const queued = gonnaWinRequestQueue.catch(() => {}).then(() => {
        if (!desktopSessionActive) return null;
        return task();
    });
    gonnaWinRequestQueue = queued.catch(() => {});
    return queued;
}

window.HACK_FLOW_DEBUG = window.HACK_FLOW_DEBUG === true;
function hackFlowDebug(flowId, source, step, details = {}) {
    if (!window.HACK_FLOW_DEBUG) return;
    console.debug(`[HACK_FLOW_DEBUG ${flowId || '-'}] ${source} ${step}`, {
        ...details,
        ts: new Date().toISOString()
    });
}

function notifyCreatedOperations(data) {
    if (!data || !Array.isArray(data.created_operations) || !data.created_operations.length) return;
    const now = Date.now();
    for (const [operationId, expiresAt] of notifiedOperationIds.entries()) {
        if (expiresAt <= now) {
            notifiedOperationIds.delete(operationId);
        }
    }
    const freshOperations = data.created_operations.filter(op => {
        const operationId = op && op.operation_id;
        if (!operationId) return true;
        if (notifiedOperationIds.has(operationId)) return false;
        notifiedOperationIds.set(operationId, now + NOTIFIED_OPERATION_TTL_MS);
        return true;
    });
    if (!freshOperations.length) {
        hackFlowDebug(
            data.debug_flow && data.debug_flow.flow_id,
            "desktop",
            "created_operations_skip_duplicate_notify",
            {
                ids: data.created_operations.map(op => op && op.operation_id),
                debug_flow: data.debug_flow || null
            }
        );
        return;
    }
    hackFlowDebug(
        data.debug_flow && data.debug_flow.flow_id,
        "desktop",
        "created_operations_notify",
        {
            ids: freshOperations.map(op => op && op.operation_id),
            debug_flow: data.debug_flow || null
        }
    );
    if (typeof notifyOpenMapsOperationsChanged === "function") {
        notifyOpenMapsOperationsChanged();
    }
}

function victimPickerIcon(path, extra = "") {
    return `<svg class="victim-picker-svg" viewBox="0 0 24 24" aria-hidden="true" focusable="false" ${extra}>${path}</svg>`;
}

const VICTIM_PICKER_ICONS = {
    appText: "⌖",
    app: victimPickerIcon('<circle cx="12" cy="12" r="8"></circle><path d="M12 2v4M12 18v4M2 12h4M18 12h4"></path><circle cx="12" cy="12" r="2"></circle>'),
    scan: victimPickerIcon('<circle cx="12" cy="12" r="8"></circle><path d="M12 12l5-3M4 12h2M18 12h2M12 4v2"></path>'),
    victims: victimPickerIcon('<path d="M8 20v-2a4 4 0 0 1 8 0v2"></path><circle cx="12" cy="9" r="3"></circle><path d="M18 8h3M19.5 6.5v3"></path>'),
    back: victimPickerIcon('<path d="M15 6l-6 6 6 6"></path>'),
    bike: victimPickerIcon('<circle cx="7" cy="17" r="3"></circle><circle cx="17" cy="17" r="3"></circle><path d="M7 17l4-8h3l3 8M11 9l-2-2M14 9l2-2M10 13h5"></path>'),
    range: victimPickerIcon('<path d="M4 12h16M8 8l-4 4 4 4M16 8l4 4-4 4"></path>'),
    refresh: victimPickerIcon('<path d="M20 6v5h-5"></path><path d="M4 18v-5h5"></path><path d="M18 10a6 6 0 0 0-10-4M6 14a6 6 0 0 0 10 4"></path>'),
    clear: victimPickerIcon('<path d="M5 7h14M9 7V5h6v2M8 10l1 9h6l1-9"></path>'),
    map: victimPickerIcon('<path d="M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2z"></path><path d="M9 4v14M15 6v14"></path>'),
    mark: victimPickerIcon('<path d="M12 21s6-5.2 6-11a6 6 0 0 0-12 0c0 5.8 6 11 6 11z"></path><circle cx="12" cy="10" r="2"></circle>'),
    marked: victimPickerIcon('<path d="M12 21s6-5.2 6-11a6 6 0 0 0-12 0c0 5.8 6 11 6 11z"></path><circle cx="12" cy="10" r="2"></circle><path d="M8 4l8 12"></path>'),
    aim: victimPickerIcon('<circle cx="12" cy="12" r="8"></circle><path d="M12 7v10M7 12h10"></path>'),
    aimed: victimPickerIcon('<circle cx="12" cy="12" r="8"></circle><circle cx="12" cy="12" r="3"></circle><path d="M12 2v4M12 18v4M2 12h4M18 12h4"></path>'),
    teleport: victimPickerIcon('<path d="M5 12h12"></path><path d="M13 7l5 5-5 5"></path><circle cx="5" cy="12" r="2"></circle>'),
    inRange: victimPickerIcon('<path d="M5 12l4 4L19 6"></path>'),
    outOfRange: victimPickerIcon('<circle cx="12" cy="12" r="8"></circle><path d="M8 8l8 8M16 8l-8 8"></path>'),
    locked: victimPickerIcon('<rect x="6" y="10" width="12" height="10" rx="2"></rect><path d="M8 10V8a4 4 0 0 1 8 0v2"></path>'),
    loading: victimPickerIcon('<circle cx="12" cy="12" r="8"></circle><path d="M12 4a8 8 0 0 1 8 8"></path>'),
    error: victimPickerIcon('<path d="M12 3l9 16H3z"></path><path d="M12 8v5M12 17h.01"></path>')
};

const VICTIM_PICKER_SOURCE_LABELS = {
    "profile.targets": "Oznaczone",
    "player.friend": "Gracze",
    "player.intruder": "Intruzi",
    "player.aimed": "Gracze",
    "clan_vulnerability": "Podatnosci",
    "territory_conflict": "Konflikty"
};

const VICTIM_PICKER_REASON_LABELS = {
    out_of_range: "Daleki cel",
    missing_position: "Brak pozycji celu",
    missing_player_position: "Brak pozycji motocykla",
    own_vulnerability: "Wlasne zgloszenie podatnosci"
};

const VICTIM_PICKER_REASON_BADGES = {
    out_of_range: "DALEKI CEL",
    missing_position: "BRAK POZYCJI",
    missing_player_position: "BRAK MOTOCYKLA",
    own_vulnerability: "WLASNA PODATNOSC",
    self: "TY",
    friend: "ZNAJOMY",
    clan: "WLASNY KLAN"
};

function formatVictimPickerCoords(position) {
    const lat = Number(position?.lat);
    const lng = Number(position?.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return "--";
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function formatVictimPickerDistance(distance) {
    const value = Number(distance);
    if (!Number.isFinite(value)) return "--";
    if (value >= 1000) return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)} km`;
    return `${Math.round(value)} m`;
}

function getVictimPickerSourceLabel(candidate) {
    const key = String(candidate?.candidate_source || candidate?.source_type || "profile.targets");
    return VICTIM_PICKER_SOURCE_LABELS[key] || key.replace(/[_:.]+/g, " ");
}

function getVictimPickerReason(candidate) {
    const reason = String(candidate?.disabled_reason || "").trim();
    return VICTIM_PICKER_REASON_LABELS[reason] || reason || "";
}

function getVictimPickerReasonBadge(candidate) {
    const reason = String(candidate?.disabled_reason || "").trim();
    if (!reason) return "";
    return VICTIM_PICKER_REASON_BADGES[reason] || "NIEDOSTEPNY";
}

function getVictimPickerRisk(candidate, actionRange) {
    const distance = Number(candidate?.distance_m);
    const range = Number(candidate?.action_range_m ?? actionRange);
    if (!Number.isFinite(distance)) {
        return {
            key: "unknown",
            className: "risk-unknown",
            label: "RYZYKO NIEZNANE",
            title: "Brak dystansu celu"
        };
    }
    if (!Number.isFinite(range) || range <= 0) {
        return {
            key: "safe",
            className: "risk-safe",
            label: "ZDALNY CEL",
            title: "Cel jest oznaczony i moze byc atakowany zdalnie"
        };
    }
    const dangerLimit = Math.max(180, Math.min(650, range * 0.35));
    if (distance <= dangerLimit) {
        return {
            key: "danger",
            className: "risk-danger",
            label: "GORACY CEL",
            title: "Bardzo blisko motocykla: wysokie ryzyko namierzenia"
        };
    }
    if (distance <= range) {
        return {
            key: "warning",
            className: "risk-warning",
            label: "BLISKI CEL",
            title: "Blisko motocykla: podwyzszone ryzyko reakcji"
        };
    }
    return {
        key: "safe",
        className: "risk-safe",
        label: "DALEKI CEL",
        title: "Poza bezposrednim zasiegiem reakcji: bezpieczniejszy cel"
    };
}

function getVictimPickerCandidateIcon(candidate) {
    if (candidate?.is_aimed) return VICTIM_PICKER_ICONS.aimed;
    if (!candidate?.can_aim) return VICTIM_PICKER_ICONS.locked;
    return candidate?.in_range ? VICTIM_PICKER_ICONS.inRange : VICTIM_PICKER_ICONS.aim;
}

function groupVictimPickerCandidates(candidates) {
    return (Array.isArray(candidates) ? candidates : []).reduce((groups, candidate) => {
        const label = getVictimPickerSourceLabel(candidate);
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label).push(candidate);
        return groups;
    }, new Map());
}

function getVictimPickerActiveLabel(state = {}) {
    const target = state.aimed_target || {};
    const fromCandidates = (Array.isArray(state.candidates) ? state.candidates : []).find(item => item.is_aimed);
    return target.label || target.name || fromCandidates?.label || "brak";
}

function getVictimPickerScanId(item = {}) {
    const lat = Number(item.lat);
    const lng = Number(item.lng ?? item.lon);
    const label = item.label || item.name || "scan";
    return `${Number.isFinite(lat) ? lat.toFixed(6) : "x"}:${Number.isFinite(lng) ? lng.toFixed(6) : "y"}:${label}`;
}

function hasUsableGameplayCoordinates(value = {}) {
    const lat = Number(value?.lat);
    const lng = Number(value?.lng ?? value?.lon);
    return Number.isFinite(lat)
        && Number.isFinite(lng)
        && lat >= -90 && lat <= 90
        && lng >= -180 && lng <= 180
        && !(Math.abs(lat) < 0.000001 && Math.abs(lng) < 0.000001);
}

function isVictimPickerMissingDisplayName(value) {
    const text = String(value || "").trim();
    return !text || text === "-" || text.toLowerCase() === "unknown";
}

function victimPickerDisplayLabel(item = {}, fallbackPrefix = "POI") {
    for (const key of ["label", "name", "title", "display_name"]) {
        if (!isVictimPickerMissingDisplayName(item[key])) return String(item[key]).trim();
    }
    const rawId = item.osm_id || item.node_id || item.id || "";
    if (rawId) return `${fallbackPrefix}-${String(rawId).slice(-6).toUpperCase()}`;
    const lat = Number(item.lat);
    const lng = Number(item.lng ?? item.lon);
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
        return `${fallbackPrefix}-${Math.abs(Math.round((lat * 100000 + lng * 100000) % 1000000)).toString(16).toUpperCase()}`;
    }
    return `${fallbackPrefix}-UNKNOWN`;
}

function normalizeVictimPickerScanResult(item = {}) {
    const lat = Number(item.lat);
    const lng = Number(item.lng ?? item.lon);
    const label = victimPickerDisplayLabel({
        ...item,
        target_type: item.target_type || "poi"
    });
    return {
        ...item,
        id: getVictimPickerScanId({ ...item, lat, lng, label }),
        lat,
        lng,
        lon: lng,
        label,
        name: isVictimPickerMissingDisplayName(item.name) ? label : (item.name || label),
        icon: item.icon || VICTIM_PICKER_ICONS.map,
        source_type: item.source_type || "unknown",
        target_type: item.target_type || "poi",
        generated: Boolean(item.generated),
        marked: Boolean(item.marked)
    };
}

function groupVictimPickerScanResults(results) {
    return (Array.isArray(results) ? results : []).reduce((groups, result) => {
        const key = String(result.source_type || "pozostale");
        const label = VICTIM_PICKER_SOURCE_LABELS[key] || key.replace(/[_:.]+/g, " ");
        if (!groups.has(label)) groups.set(label, []);
        groups.get(label).push(result);
        return groups;
    }, new Map());
}

function openVictimPickerMapFocus(focus = {}, label = "Victim Picker") {
    const lat = Number(focus?.lat);
    const lng = Number(focus?.lng);
    if (!hasUsableGameplayCoordinates({ lat, lng })) {
        addSystemMessage("warning", "VICTIM PICKER", "Brak pozycji celu dla mapy.");
        return false;
    }
    createMap();
    const payload = {
        ...focus,
        lat,
        lng,
        label,
        source: "victim_picker",
        mode: focus.mode || "target"
    };
    window.setTimeout(() => notifyOpenMapsBlacknetFocus(payload), 80);
    return true;
}

async function teleportVictimPickerCandidate(candidate, refreshAfter = null) {
    const teleport = candidate?.teleport || candidate?.focus || {};
    const lat = Number(teleport.lat ?? candidate?.lat);
    const lng = Number(teleport.lng ?? candidate?.lng);
    if (!hasUsableGameplayCoordinates({ lat, lng })) {
        addSystemMessage("warning", "VICTIM PICKER", "Brak poprawnych wspolrzednych teleportu.");
        return false;
    }
    const label = candidate?.label || `${lat.toFixed(5)}, ${lng.toFixed(5)}`;

    const accepted = await showGhostDecisionDialog({
        title: "POTWIERDZENIE TELEPORTU",
        message: `Wykonac teleport w okolice celu: ${label}?`,
        details: "OK zmieni pozycje operatora i odswiezy mape. ANULUJ zostawi obecna pozycje.",
        confirmLabel: "OK",
        cancelLabel: "ANULUJ",
        tone: "lime"
    });
    if (!accepted) return false;

    const response = await fetch("/api/blacknet/cta/teleport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            source: "victim_picker",
            lat,
            lng,
            label: "victim_picker",
            target_label: label
        })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.success === false) {
        addSystemMessage("warning", "VICTIM PICKER", data.message || "Teleport odrzucony.");
        return false;
    }

    addSystemMessage("success", "VICTIM PICKER", data.message || `Teleport wykonany: ${label}.`);
    if (typeof refreshToolbarProfile === "function") refreshToolbarProfile();
    openVictimPickerMapFocus({
        ...teleport,
        lat: Number(data?.curently_possition?.lat ?? lat),
        lng: Number(data?.curently_possition?.lng ?? lng),
        position_version: data?.position_version,
        position_updated_at: data?.position_updated_at,
        mode: "teleport"
    }, label);
    if (typeof refreshAfter === "function") {
        await refreshAfter();
    }
    return true;
}

function setVictimPickerBusy(app, busy, message = "") {
    if (!app) return;
    app.classList.toggle("is-loading", Boolean(busy));
    const status = app.querySelector("[data-victim-picker-status]");
    if (status) {
        status.textContent = message || (busy ? "Synchronizacja..." : "");
        status.hidden = !busy && !message;
    }
    app.querySelectorAll("[data-victim-picker-action]").forEach(button => {
        button.disabled = Boolean(busy) || button.dataset.originalDisabled === "1";
    });
}

function renderVictimPickerEmpty(container, message) {
    container.innerHTML = `<div class="victim-picker-empty">${escapeHTML(message || "Brak kandydatow.")}</div>`;
}

function renderVictimPickerFrame(app, state, bodyHtml, options = {}) {
    const root = app.querySelector(".victim-picker-shell");
    if (!root) return null;
    const currentLabel = getVictimPickerActiveLabel(state);
    const position = state.position || {};
    const range = Number(state.action_range_m);
    const view = state.view || "main";
    const back = options.back ? `<button type="button" data-victim-picker-action="${escapeHTML(options.back)}" title="Wroc" aria-label="Wroc">${VICTIM_PICKER_ICONS.back}<span>Wroc</span></button>` : "";
    const screenTitle = options.title || (view === "scan_results" || view === "scan_loading" ? "SCAN" : view === "victims" ? "VICTIMS" : "Victim Picker");

    root.innerHTML = `
        <header class="victim-picker-header">
            <div class="victim-picker-brand">
                <span class="victim-picker-brand-icon">${VICTIM_PICKER_ICONS.app}</span>
                <div>
                    <strong>${escapeHTML(screenTitle)}</strong>
                    <span>Lekki selektor celu bez Leafleta</span>
                </div>
            </div>
            <div class="victim-picker-meta">
                <span title="Aktualny cel"><b>CEL</b> ${escapeHTML(currentLabel)}</span>
                <span title="Pozycja motocykla"><b>${VICTIM_PICKER_ICONS.bike}</b> ${escapeHTML(formatVictimPickerCoords(position))}</span>
                <span title="Zasieg akcji"><b>${VICTIM_PICKER_ICONS.range}</b> ${Number.isFinite(range) ? `${Math.round(range)} m` : "--"}</span>
            </div>
        </header>
        <nav class="victim-picker-toolbar" aria-label="Victim Picker tools">
            ${back}
            <button type="button" data-victim-picker-action="refresh" title="Odswiez" aria-label="Odswiez">${VICTIM_PICKER_ICONS.refresh}</button>
            <button type="button" data-victim-picker-action="open-map" title="Otworz mape" aria-label="Otworz mape">${VICTIM_PICKER_ICONS.map}</button>
            <button type="button" data-victim-picker-action="focus-active" title="Pokaz aktualny cel na mapie" aria-label="Pokaz aktualny cel na mapie">${VICTIM_PICKER_ICONS.aimed}</button>
            <button type="button" data-victim-picker-action="close" title="Zamknij" aria-label="Zamknij">×</button>
        </nav>
        <div class="victim-picker-status" data-victim-picker-status hidden></div>
        <section class="victim-picker-screen victim-picker-screen-${escapeHTML(view)}" data-victim-picker-screen>${bodyHtml || ""}</section>
    `;
    bindVictimPickerCommonActions(app, state);
    return root;
}

function bindVictimPickerCommonActions(app, state) {
    const root = app.querySelector(".victim-picker-shell");
    if (!root) return;
    root.querySelector('[data-victim-picker-action="refresh"]')?.addEventListener("click", () => loadVictimPickerData(app, state, state.view || "main"));
    root.querySelector('[data-victim-picker-action="open-map"]')?.addEventListener("click", () => createMap());
    root.querySelector('[data-victim-picker-action="close"]')?.addEventListener("click", () => app.remove());
    root.querySelector('[data-victim-picker-action="back-main"]')?.addEventListener("click", () => renderVictimPickerMain(app, state));
    root.querySelector('[data-victim-picker-action="back-scan"]')?.addEventListener("click", () => renderVictimPickerScanResults(app, state));
    root.querySelector('[data-victim-picker-action="focus-active"]')?.addEventListener("click", () => {
        const active = (Array.isArray(state.candidates) ? state.candidates : []).find(item => item.is_aimed);
        const target = state.aimed_target;
        const focus = active?.focus || active || target;
        if (!hasUsableGameplayCoordinates(focus)) {
            addSystemMessage("warning", "VICTIM PICKER", "Brak aktywnego celu do pokazania.");
            return;
        }
        openVictimPickerMapFocus(focus, getVictimPickerActiveLabel(state));
    });
}

function renderVictimPickerMain(app, state) {
    state.view = "main";
    renderVictimPickerFrame(app, state, `
        <div class="victim-picker-main">
            <button type="button" class="victim-picker-tile" data-victim-picker-action="scan">
                <span class="victim-picker-tile-icon">${VICTIM_PICKER_ICONS.scan}</span>
                <strong>SCAN</strong>
                <span>Skanuj otoczenie motocykla</span>
            </button>
            <button type="button" class="victim-picker-tile" data-victim-picker-action="victims">
                <span class="victim-picker-tile-icon">${VICTIM_PICKER_ICONS.victims}</span>
                <strong>VICTIMS</strong>
                <span>Wybierz aktywny cel z ${Array.isArray(state.candidates) ? state.candidates.length : 0} kandydatow</span>
            </button>
        </div>
        <div class="victim-picker-legend">
            <span>${VICTIM_PICKER_ICONS.mark} oznacz</span>
            <span>${VICTIM_PICKER_ICONS.aim} ustaw CEL</span>
            <span>${VICTIM_PICKER_ICONS.map} pokaz</span>
            <span>${VICTIM_PICKER_ICONS.teleport} teleport</span>
        </div>
    `, { title: "Victim Picker" });
    const root = app.querySelector(".victim-picker-shell");
    root?.querySelector('[data-victim-picker-action="scan"]')?.addEventListener("click", () => runVictimPickerScan(app, state));
    root?.querySelector('[data-victim-picker-action="victims"]')?.addEventListener("click", () => renderVictimPickerVictims(app, state));
}

function renderVictimPickerScanLoading(app, state) {
    state.view = "scan_loading";
    renderVictimPickerFrame(app, state, `
        <div class="victim-picker-loading">
            <div class="victim-picker-radar" aria-hidden="true">${VICTIM_PICKER_ICONS.scan}</div>
            <div>
                <b>GhostSystem: skan otoczenia motocykla...</b>
                <p>Pozycja i zasieg sa weryfikowane po stronie runtime.</p>
                <ul class="victim-picker-scan-log">
                    <li>kalibracja anteny</li>
                    <li>rekonstrukcja sygnatur</li>
                    <li>grupowanie wedlug source_type</li>
                </ul>
            </div>
        </div>
    `, { back: "back-main", title: "SCAN" });
}

function renderVictimPickerScanResults(app, state) {
    state.view = "scan_results";
    const results = Array.isArray(state.scan_results) ? state.scan_results : [];
    const groups = groupVictimPickerScanResults(results);
    const body = `
        <div class="victim-picker-scan-actions">
            <button type="button" data-victim-picker-action="clear-scan" title="Wyczysc scan" aria-label="Wyczysc scan">${VICTIM_PICKER_ICONS.clear}<span>Wyczysc scan</span></button>
            <button type="button" data-victim-picker-action="go-victims" title="Przejdz do VICTIMS" aria-label="Przejdz do VICTIMS">${VICTIM_PICKER_ICONS.victims}<span>VICTIMS</span></button>
        </div>
        <div class="victim-picker-legend">
            <span>${VICTIM_PICKER_ICONS.mark} oznacz</span>
            <span>${VICTIM_PICKER_ICONS.marked} oznaczony</span>
            <span>${VICTIM_PICKER_ICONS.map} pokaz na mapie</span>
        </div>
        <section class="victim-picker-list" data-victim-picker-list>
            ${results.length ? Array.from(groups.entries()).map(([groupLabel, items]) => `
                <section class="victim-picker-group">
                    <h4>${escapeHTML(groupLabel)} <span>${items.length}</span></h4>
                    ${items.map(result => `
                        <article class="victim-picker-row ${result.marked ? "is-marked" : ""}" data-scan-id="${escapeHTML(result.id)}">
                            <div class="victim-picker-kind">${escapeHTML(result.icon || VICTIM_PICKER_ICONS.map)}</div>
                            <div class="victim-picker-copy">
                                <strong>${escapeHTML(result.label || result.name || "unknown")}</strong>
                                <span>${escapeHTML(result.source_type || "unknown")} / ${escapeHTML(formatVictimPickerDistance(result.distance_m))}</span>
                                <em>${result.marked ? "Oznaczony" : "Wynik skanu"}</em>
                            </div>
                            <div class="victim-picker-state">${result.marked ? VICTIM_PICKER_ICONS.aimed : VICTIM_PICKER_ICONS.inRange}</div>
                            <div class="victim-picker-actions">
                                <button type="button" data-victim-picker-action="mark-scan" data-scan-id="${escapeHTML(result.id)}" title="${result.marked ? "Oznaczony" : "Oznacz"}" aria-label="${result.marked ? "Oznaczony" : "Oznacz"}" ${result.marked ? "disabled data-original-disabled=\"1\"" : ""}>${result.marked ? VICTIM_PICKER_ICONS.marked : VICTIM_PICKER_ICONS.mark}</button>
                                <button type="button" data-victim-picker-action="show-scan-map" data-scan-id="${escapeHTML(result.id)}" title="${result.marked ? "Pokaz na mapie" : "Najpierw oznacz obiekt"}" aria-label="Pokaz na mapie" ${result.marked ? "" : "disabled data-original-disabled=\"1\""}>${VICTIM_PICKER_ICONS.map}</button>
                            </div>
                        </article>
                    `).join("")}
                </section>
            `).join("") : `<div class="victim-picker-empty">Brak nowych obiektow w wyniku skanu.</div>`}
        </section>
    `;
    renderVictimPickerFrame(app, state, body, { back: "back-main", title: "SCAN" });

    const root = app.querySelector(".victim-picker-shell");
    const getScan = id => results.find(item => String(item.id) === String(id));
    root?.querySelector('[data-victim-picker-action="clear-scan"]')?.addEventListener("click", () => {
        state.scan_results = [];
        renderVictimPickerScanResults(app, state);
    });
    root?.querySelector('[data-victim-picker-action="go-victims"]')?.addEventListener("click", async () => {
        await loadVictimPickerData(app, state, "victims");
    });
    root?.querySelectorAll("[data-victim-picker-action][data-scan-id]").forEach(button => {
        button.addEventListener("click", async () => {
            const scan = getScan(button.dataset.scanId);
            if (!scan) return;
            if (button.dataset.victimPickerAction === "show-scan-map") {
                openVictimPickerMapFocus(scan, scan.label);
                return;
            }
            if (button.dataset.victimPickerAction !== "mark-scan" || scan.marked) return;
            setVictimPickerBusy(app, true, "Oznaczam obiekt...");
            try {
                const response = await fetch("/map-action", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        action: "mark_target",
                        lat: scan.lat,
                        lng: scan.lng,
                        label: scan.label,
                        icon: scan.icon,
                        source_type: scan.source_type,
                        name: scan.name || scan.label,
                        generated: Boolean(scan.generated)
                    })
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok || data.error) {
                    addSystemMessage("warning", "VICTIM PICKER", data.error || "Nie udalo sie oznaczyc obiektu.");
                    return;
                }
                scan.marked = true;
                addSystemMessage("success", "VICTIM PICKER", "Obiekt oznaczony. Jest dostepny w VICTIMS.");
                await loadVictimPickerData(app, state, "scan_results", { silent: true });
                renderVictimPickerScanResults(app, state);
            } catch (error) {
                console.warn("Victim Picker mark scan failed", error);
                addSystemMessage("warning", "VICTIM PICKER", "Most oznaczania jest chwilowo niedostepny.");
            } finally {
                setVictimPickerBusy(app, false);
            }
        });
    });
}

async function runVictimPickerScan(app, state) {
    renderVictimPickerScanLoading(app, state);
    setVictimPickerBusy(app, true, "Skan...");
    try {
        await loadVictimPickerData(app, state, "scan_loading", { silent: true });
        const position = state.position || {};
        const lat = Number(position.lat);
        const lng = Number(position.lng);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
            throw new Error("Brak pozycji motocykla.");
        }
        const response = await fetch("/map-action", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action: "scan",
                lat,
                lng,
                label: "Victim Picker scan",
                icon: VICTIM_PICKER_ICONS.app,
                source_type: "victim_picker",
                name: "Victim Picker scan",
                generated: false
            })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(data.message || data.status || "Skan odrzucony.");
        }
        const origin = state.position || {};
        state.scan_results = (Array.isArray(data.markers) ? data.markers : [])
            .map(item => normalizeVictimPickerScanResult(item))
            .filter(item => Number.isFinite(item.lat) && Number.isFinite(item.lng))
            .map(item => ({
                ...item,
                distance_m: victimPickerDistanceFromOrigin(item, origin)
            }))
            .sort((a, b) => (a.distance_m ?? 10 ** 12) - (b.distance_m ?? 10 ** 12));
        renderVictimPickerScanResults(app, state);
    } catch (error) {
        state.view = "error";
        renderVictimPickerFrame(app, state, `
            <div class="victim-picker-error">
                <strong>${VICTIM_PICKER_ICONS.error} Scan offline</strong>
                <p>${escapeHTML(error?.message || "Nie udalo sie wykonac skanu.")}</p>
            </div>
        `, { back: "back-main", title: "SCAN" });
    } finally {
        setVictimPickerBusy(app, false);
    }
}

function victimPickerDistanceFromOrigin(item, origin) {
    const lat1 = Number(item?.lat);
    const lng1 = Number(item?.lng ?? item?.lon);
    const lat2 = Number(origin?.lat);
    const lng2 = Number(origin?.lng ?? origin?.lon);
    if (![lat1, lng1, lat2, lng2].every(Number.isFinite)) return null;
    const toRad = value => value * Math.PI / 180;
    const earth = 6371000;
    const dLat = toRad(lat2 - lat1);
    const dLng = toRad(lng2 - lng1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
    return Math.round(earth * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)));
}

function renderVictimPickerVictims(app, state) {
    state.view = "victims";
    const candidates = Array.isArray(state.candidates) ? state.candidates : [];
    const groups = groupVictimPickerCandidates(candidates);
    const body = `
        <div class="victim-picker-legend">
            <span>${VICTIM_PICKER_ICONS.aim} ustaw CEL</span>
            <span>${VICTIM_PICKER_ICONS.aimed} aktualny CEL</span>
            <span>${VICTIM_PICKER_ICONS.map} pokaz</span>
            <span>${VICTIM_PICKER_ICONS.teleport} teleport</span>
        </div>
        <section class="victim-picker-list" data-victim-picker-list></section>
    `;
    renderVictimPickerFrame(app, state, body, { back: "back-main", title: "VICTIMS" });

    const root = app.querySelector(".victim-picker-shell");
    const list = root?.querySelector("[data-victim-picker-list]");
    if (!list) return;
    if (!candidates.length) {
        renderVictimPickerEmpty(list, "Brak kandydatow w zasiegu aktualnych zrodel.");
    } else {
        list.innerHTML = Array.from(groups.entries()).map(([groupLabel, items]) => `
            <section class="victim-picker-group">
                <h4>${escapeHTML(groupLabel)} <span>${items.length}</span></h4>
                ${items.map(candidate => {
                    const reason = getVictimPickerReason(candidate);
                    const reasonBadge = getVictimPickerReasonBadge(candidate);
                    const risk = getVictimPickerRisk(candidate, state.action_range_m);
                    const classes = [
                        "victim-picker-row",
                        candidate.is_aimed ? "is-aimed" : "",
                        candidate.in_range ? "in-range" : "out-of-range",
                        risk.className,
                        candidate.can_aim ? "" : "is-disabled"
                    ].filter(Boolean).join(" ");
                    return `
                        <article class="${classes}" data-target-id="${escapeHTML(candidate.target_id || "")}">
                            <div class="victim-picker-kind" title="${escapeHTML(candidate.target_type || candidate.source_type || "target")}">${escapeHTML(candidate.icon || "⌖")}</div>
                            <div class="victim-picker-copy">
                                <strong title="${escapeHTML(candidate.label || "")}">${escapeHTML(candidate.label || "unknown")}</strong>
                                <span>${escapeHTML(candidate.target_mode || "standard")} / ${escapeHTML(formatVictimPickerDistance(candidate.distance_m))}</span>
                                <em class="victim-picker-risk" title="${escapeHTML(risk.title)}">${escapeHTML(candidate.can_aim ? risk.label : (reasonBadge || risk.label))}</em>
                                ${candidate.is_aimed ? `<em class="victim-picker-badge-cel">CEL</em>` : ""}
                            </div>
                            <div class="victim-picker-state" title="${candidate.is_aimed ? "Aktywny CEL" : candidate.can_aim ? risk.title : escapeHTML(reason || "Niedostepny")}">${getVictimPickerCandidateIcon(candidate)}</div>
                            <div class="victim-picker-actions">
                                <button type="button" data-victim-picker-action="aim" data-target-id="${escapeHTML(candidate.target_id || "")}" title="${candidate.can_aim ? (candidate.is_aimed ? "Aktualny CEL" : "Oznacz jako CEL") : escapeHTML(reason || "Niedostepny")}" aria-label="${candidate.is_aimed ? "Aktualny CEL" : "Oznacz jako CEL"}" ${candidate.can_aim && !candidate.is_aimed ? "" : "disabled data-original-disabled=\"1\""}>${candidate.is_aimed ? VICTIM_PICKER_ICONS.aimed : VICTIM_PICKER_ICONS.aim}</button>
                                <button type="button" data-victim-picker-action="show-map" data-target-id="${escapeHTML(candidate.target_id || "")}" title="Pokaz na mapie" aria-label="Pokaz na mapie" ${hasUsableGameplayCoordinates(candidate.focus || candidate) ? "" : "disabled data-original-disabled=\"1\""}>${VICTIM_PICKER_ICONS.map}</button>
                                ${candidate.teleport && hasUsableGameplayCoordinates(candidate.teleport) ? `<button type="button" data-victim-picker-action="teleport" data-target-id="${escapeHTML(candidate.target_id || "")}" title="Teleport w okolice celu" aria-label="Teleport w okolice celu">${VICTIM_PICKER_ICONS.teleport}</button>` : ""}
                            </div>
                        </article>
                    `;
                }).join("")}
            </section>
        `).join("");
    }

    const getCandidate = targetId => candidates.find(item => String(item.target_id || "") === String(targetId || ""));
    root.querySelectorAll("[data-victim-picker-action][data-target-id]").forEach(button => {
        button.addEventListener("click", async () => {
            const action = button.dataset.victimPickerAction;
            const candidate = getCandidate(button.dataset.targetId);
            if (!candidate) return;
            if (action === "show-map") {
                openVictimPickerMapFocus(candidate.focus || candidate, candidate.label);
                return;
            }
            if (action === "teleport") {
                setVictimPickerBusy(app, true, "Teleport...");
                try {
                    await teleportVictimPickerCandidate(candidate, () => loadVictimPickerData(app, state));
                } finally {
                    setVictimPickerBusy(app, false);
                }
                return;
            }
            if (action !== "aim") return;
            if (!candidate.can_aim) return;
            setVictimPickerBusy(app, true, "Ustawiam CEL...");
            try {
                const response = await fetch("/api/victim-picker/aim", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ target_id: candidate.target_id })
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok || data.success === false) {
                    addSystemMessage("warning", "VICTIM PICKER", data.message || "Nie udalo sie ustawic celu.");
                    return;
                }
                addSystemMessage("success", "VICTIM PICKER", data.message || "Cel ustawiony.");
                if (data.target && typeof updateToolbarAimedTarget === "function") {
                    updateToolbarAimedTarget(data.target);
                }
                if (typeof refreshToolbarTargetTruth === "function") {
                    refreshToolbarTargetTruth();
                }
                await loadVictimPickerData(app, state, "victims", { silent: true });
                renderVictimPickerVictims(app, state);
            } catch (error) {
                console.warn("Victim Picker aim failed", error);
                addSystemMessage("warning", "VICTIM PICKER", "Most celu jest chwilowo niedostepny.");
            } finally {
                setVictimPickerBusy(app, false);
            }
        });
    });
}

async function loadVictimPickerData(app, state = {}, nextView = null, options = {}) {
    const shell = app.querySelector(".victim-picker-shell");
    if (!shell) return;
    if (!options.silent) setVictimPickerBusy(app, true, "Pobieram stan...");
    if (!shell.dataset.initialized && !options.silent) {
        shell.dataset.initialized = "1";
        shell.innerHTML = `
            <div class="victim-picker-loading">
                <span class="app-button-spinner" aria-hidden="true"></span>
                <b>Synchronizacja Victim Pickera...</b>
            </div>
        `;
    }
    try {
        const response = await fetch("/api/victim-picker/candidates", { headers: { "Accept": "application/json" } });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            state.candidates = [];
            state.position = null;
            state.action_range_m = null;
            shell.innerHTML = `
                <div class="victim-picker-error">
                    <strong>${VICTIM_PICKER_ICONS.error} Victim Picker offline</strong>
                    <p>${escapeHTML(data.message || data.error || "Nie udalo sie pobrac kandydatow.")}</p>
                </div>
            `;
            return;
        }
        state.candidates = Array.isArray(data.candidates) ? data.candidates : [];
        state.position = data.position || null;
        state.action_range_m = data.action_range_m;
        state.aimed_target = data.aimed_target || null;
        if (nextView === "victims") renderVictimPickerVictims(app, state);
        else if (nextView === "scan_results") return;
        else if (nextView === "scan_loading") return;
        else renderVictimPickerMain(app, state);
    } catch (error) {
        console.warn("Victim Picker load failed", error);
        shell.innerHTML = `
            <div class="victim-picker-error">
                <strong>${VICTIM_PICKER_ICONS.error} Victim Picker offline</strong>
                <p>Nie udalo sie polaczyc z endpointem kandydatow.</p>
            </div>
        `;
    } finally {
        if (!options.silent) setVictimPickerBusy(app, false);
    }
}

function createVictimPickerApp() {
    const existing = document.querySelector('.app-window[data-app="victim-picker"]');
    if (existing) {
        bringWindowToFront(existing);
        return existing;
    }

    const app = document.createElement('div');
    app.className = 'app-window victim-picker-window';
    app.dataset.app = "victim-picker";
    app.dataset.appIcon = VICTIM_PICKER_ICONS.appText;
    app.dataset.appTitle = "Victim Picker";
    const position = findAvailablePosition(760, 580);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.style.width = `760px`;
    app.style.height = `580px`;
    app.innerHTML = `
        <div class="title-bar">Victim Picker <span class="close-btn" style="float:right; cursor:pointer;">✖</span></div>
        <div class="victim-picker-shell"></div>
    `;

    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn')?.addEventListener('click', () => app.remove());
    const state = { view: "main", scan_results: [] };
    app._ghostControlPositionRefresh = () => loadVictimPickerData(app, state, state.view || "main", { silent: true });
    loadVictimPickerData(app, state, "main");
    return app;
}

window.createVictimPickerApp = createVictimPickerApp;

const TERRITORY_CONTROL_ICONS = {
    app: "◇",
    cluster: "⬡",
    pillar: "◆",
    inner: "◇",
    alone: "⌖",
    map: "▣",
    teleport: "➜",
    back: "‹",
    refresh: "⟳",
    security: "▦",
    abandon: "×",
    open: "○",
    low: "◔",
    regular: "◑",
    secure: "◕",
    all: "●"
};

const TERRITORY_CONTROL_PRESETS = [
    { id: "open", label: "OP", title: "OPEN" },
    { id: "low", label: "LO", title: "LOW" },
    { id: "regular", label: "RG", title: "REGULAR" },
    { id: "secure", label: "SC", title: "SECURE" },
    { id: "all", label: "AL", title: "ALL" }
];

function territoryControlMeters(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "--";
    if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)} km`;
    return `${Math.round(n)} m`;
}

function territoryControlArea(value) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "--";
    if (n >= 1000000) return `${(n / 1000000).toFixed(2)} km²`;
    return `${Math.round(n).toLocaleString("pl-PL")} m²`;
}

function territoryControlCoords(position) {
    const lat = Number(position?.lat);
    const lng = Number(position?.lng ?? position?.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return "--";
    return `${lat.toFixed(4)}, ${lng.toFixed(4)}`;
}

function territoryControlThreatLabel(value) {
    const key = String(value || "neutral").toLowerCase();
    if (key === "attacked") return "ATAK";
    if (key === "collision") return "KOLIZJA";
    return "NEUTRAL";
}

function territoryControlThreatBadges(cluster = {}) {
    const flags = cluster?.threat_flags || {};
    const badges = [];
    if (flags.attacked || Number(cluster?.attacked_targets_count || 0) > 0 || Number(cluster?.attacked_pillars_count || 0) > 0 || String(cluster?.threat_state || "").toLowerCase() === "attacked") {
        badges.push({ kind: "attacked", label: "ALARM" });
    }
    if (flags.collision || Number(cluster?.conflict_count || 0) > 0) {
        badges.push({ kind: "collision", label: "KOLIZJA" });
    }
    if (!badges.length) badges.push({ kind: "neutral", label: "NEUTRAL" });
    return badges;
}

function renderTerritoryControlThreatBadges(cluster = {}) {
    return territoryControlThreatBadges(cluster)
        .map(badge => `<span class="territory-control-threat territory-control-threat-${escapeHTML(badge.kind)}">${escapeHTML(badge.label)}</span>`)
        .join("");
}

function territoryControlGhostBadge(cluster = {}) {
    if (!cluster.contains_ghost_part) return "";
    const parts = Array.isArray(cluster.parts) ? cluster.parts : [];
    const contested = parts.some(part => part?.contested || part?.conflict_state === "contested");
    const relation = String(cluster.ghost_part_relation || parts[0]?.viewer_relation || "");
    const state = String(cluster.ghost_part_state || parts[0]?.module_state || "");
    let label = "KOMPONENT NIEZIDENTYFIKOWANY // BLOKOWANY";
    if (contested) label = "KOMPONENT // KONFLIKT";
    else if (relation === "self_own_active" || relation === "clan_own_active" || state === "active") label = "CZESC WLASNEGO KLANU // AKTYWNA";
    else if (relation === "self_foreign_blocked" || state === "blocked") label = cluster.ghost_part_identity_visible ? "CZESC OBCEGO KLANU // BLOKOWANA" : label;
    return `<span class="territory-control-ghost-badge state-${escapeHTML(contested ? "contested" : state || "blocked")}" title="GhostNetwork">${TERRITORY_CONTROL_ICONS.app} ${escapeHTML(label)}</span>`;
}

function renderTerritoryControlGhostDetails(cluster = {}) {
    if (!cluster.contains_ghost_part) return "";
    const parts = Array.isArray(cluster.parts) ? cluster.parts : [];
    const rows = parts.map(part => {
        const identity = part?.identity_visible === true;
        return `<article class="territory-control-ghost-part">
            <strong>${escapeHTML(part?.display_label || "NIEZIDENTYFIKOWANY KOMPONENT")}</strong>
            <span>${escapeHTML(String(part?.module_state || "unknown").toUpperCase())}${part?.contested ? " · KONFLIKT" : ""}</span>
            ${identity && (part.machine_name || part.machine_code) ? `<small>MASZYNA: ${escapeHTML(part.machine_name || part.machine_code)}</small>` : ""}
            ${identity && (part.profession_name || part.profession_code) ? `<small>PROFESJA: ${escapeHTML(part.profession_name || part.profession_code)}</small>` : ""}
            ${part?.ability_visible && (part.ability_name || part.ability_code) ? `<small>MOC: ${escapeHTML(part.ability_name || part.ability_code)}</small>` : ""}
            ${part?.clan_name || part?.clan_code ? `<small>KLAN: ${escapeHTML(part.clan_name || part.clan_code)}</small>` : ""}
        </article>`;
    }).join("");
    return `<section class="territory-control-ghost-section"><h4>GHOSTNETWORK <span>${Number(cluster.ghost_part_count || parts.length || 0)}</span></h4><p>${escapeHTML(cluster.ghost_part_summary || "TERYTORIUM PRZECHOWUJE KOMPONENT GHOSTNETWORK")}</p>${rows || `<div class="territory-control-empty">TERYTORIUM PRZECHOWUJE NIEZIDENTYFIKOWANY KOMPONENT</div>`}</section>`;
}

function territoryControlThreatSummary(cluster = {}) {
    return territoryControlThreatBadges(cluster)
        .map(badge => badge.label)
        .join(" + ");
}

function setTerritoryControlBusy(app, busy, message = "") {
    if (!app) return;
    app.classList.toggle("is-loading", Boolean(busy));
    const status = app.querySelector("[data-territory-control-status]");
    if (status) {
        status.textContent = message || (busy ? "Synchronizacja..." : "");
        status.hidden = !busy && !message;
    }
    app.querySelectorAll("[data-territory-control-action]").forEach(button => {
        button.disabled = Boolean(busy) || button.dataset.originalDisabled === "1";
    });
}

function getTerritoryControlObjectById(state, targetId) {
    const id = String(targetId || "");
    const clusters = Array.isArray(state?.clusters) ? state.clusters : [];
    for (const cluster of clusters) {
        const objects = [...(cluster.pillars || []), ...(cluster.inners || [])];
        const found = objects.find(item => String(item.target_id || "") === id);
        if (found) return found;
    }
    return (state?.alone_pillars || []).find(item => String(item.target_id || "") === id) || null;
}

function getTerritoryControlClusterById(state, clusterId) {
    return (Array.isArray(state?.clusters) ? state.clusters : [])
        .find(item => String(item.cluster_id || "") === String(clusterId || "")) || null;
}

function getTerritoryControlClusterByTargetId(state, targetId) {
    const id = String(targetId || "");
    if (!id) return null;
    const clusters = Array.isArray(state?.clusters) ? state.clusters : [];
    return clusters.find(cluster => {
        const objects = [...(cluster.pillars || []), ...(cluster.inners || [])];
        return objects.some(item => String(item.target_id || "") === id);
    }) || null;
}

function openTerritoryControlMapFocus(focus = {}, label = "Territory Control") {
    const lat = Number(focus?.lat);
    const lng = Number(focus?.lng ?? focus?.lon);
    if (!hasUsableGameplayCoordinates({ lat, lng })) {
        addSystemMessage("warning", "TERRITORY CONTROL", "Brak pozycji do pokazania na mapie.");
        return false;
    }
    createMap();
    window.setTimeout(() => notifyOpenMapsBlacknetFocus({
        ...focus,
        lat,
        lng,
        label,
        source: "territory_control",
        mode: focus.mode || "territory_control"
    }), 80);
    return true;
}

async function teleportTerritoryControlObject(item, refreshAfter = null) {
    const teleport = item?.teleport || item?.map_focus || item || {};
    const lat = Number(teleport.lat ?? item?.lat);
    const lng = Number(teleport.lng ?? item?.lng ?? item?.lon);
    if (!hasUsableGameplayCoordinates({ lat, lng })) {
        addSystemMessage("warning", "TERRITORY CONTROL", "Brak poprawnych wspolrzednych teleportu.");
        return false;
    }
    const label = item?.label || `${lat.toFixed(5)}, ${lng.toFixed(5)}`;

    const accepted = await showGhostDecisionDialog({
        title: "POTWIERDZENIE TELEPORTU",
        message: `Wykonac teleport w okolice: ${label}?`,
        details: "OK zmieni pozycje operatora i odswiezy mape. ANULUJ zostawi obecna pozycje.",
        confirmLabel: "OK",
        cancelLabel: "ANULUJ",
        tone: "lime"
    });
    if (!accepted) return false;

    const response = await fetch("/api/blacknet/cta/teleport", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            source: "territory_control",
            lat,
            lng,
            label: "territory_control",
            target_label: label
        })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.success === false) {
        addSystemMessage("warning", "TERRITORY CONTROL", data.message || "Teleport odrzucony.");
        return false;
    }
    addSystemMessage("success", "TERRITORY CONTROL", data.message || `Teleport wykonany: ${label}.`);
    if (typeof refreshToolbarProfile === "function") refreshToolbarProfile();
    openTerritoryControlMapFocus({
        ...teleport,
        lat: Number(data?.curently_possition?.lat ?? lat),
        lng: Number(data?.curently_possition?.lng ?? lng),
        position_version: data?.position_version,
        position_updated_at: data?.position_updated_at,
        mode: "teleport"
    }, label);
    if (typeof refreshAfter === "function") await refreshAfter();
    return true;
}

function renderTerritoryControlFrame(app, state, bodyHtml, options = {}) {
    const root = app.querySelector(".territory-control-shell");
    if (!root) return null;
    const clusters = Array.isArray(state.clusters) ? state.clusters : [];
    const conflictCount = clusters.reduce((sum, cluster) => sum + Number(cluster.conflict_count || 0), 0);
    const attackedCount = clusters.filter(cluster => cluster.threat_state === "attacked").length;
    const back = options.back ? `<button type="button" data-territory-control-action="${escapeHTML(options.back)}" title="Wroc" aria-label="Wroc">${TERRITORY_CONTROL_ICONS.back}<span>Wroc</span></button>` : "";
    root.innerHTML = `
        <header class="territory-control-header">
            <div class="territory-control-brand">
                <span class="territory-control-brand-icon">${TERRITORY_CONTROL_ICONS.app}</span>
                <div>
                    <strong>${escapeHTML(options.title || "TERRITORY CONTROL")}</strong>
                    <span>Zarzadzanie przejetym terenem bez Leafleta</span>
                </div>
            </div>
            <div class="territory-control-meta">
                <span title="Pozycja motocykla"><b>POS</b> ${escapeHTML(territoryControlCoords(state.position))}</span>
                <span title="Klastry"><b>KLASTRY</b> ${clusters.length}</span>
                <span title="Konflikty"><b>KONFLIKTY</b> ${conflictCount}</span>
                <span title="Atakowane"><b>ATAK</b> ${attackedCount}</span>
            </div>
        </header>
        <nav class="territory-control-toolbar" aria-label="Territory Control tools">
            ${back}
            <button type="button" data-territory-control-action="refresh" title="Odswiez" aria-label="Odswiez">${TERRITORY_CONTROL_ICONS.refresh}</button>
            <button type="button" data-territory-control-action="open-map" title="Otworz mape" aria-label="Otworz mape">${TERRITORY_CONTROL_ICONS.map}</button>
            <button type="button" data-territory-control-action="close" title="Zamknij" aria-label="Zamknij">×</button>
        </nav>
        <div class="territory-control-status" data-territory-control-status hidden></div>
        <section class="territory-control-screen" data-territory-control-screen>${bodyHtml || ""}</section>
    `;
    bindTerritoryControlCommonActions(app, state);
    return root;
}

function bindTerritoryControlCommonActions(app, state) {
    const root = app.querySelector(".territory-control-shell");
    if (!root) return;
    root.querySelector('[data-territory-control-action="refresh"]')?.addEventListener("click", () => loadTerritoryControlData(app, state, state.view || "list"));
    root.querySelector('[data-territory-control-action="open-map"]')?.addEventListener("click", () => createMap());
    root.querySelector('[data-territory-control-action="close"]')?.addEventListener("click", () => app.remove());
    root.querySelector('[data-territory-control-action="back-list"]')?.addEventListener("click", () => renderTerritoryControlList(app, state));
}

function renderTerritoryClusterCard(cluster) {
    const threat = String(cluster.threat_state || "neutral").toLowerCase();
    return `
        <article class="territory-control-cluster threat-${escapeHTML(threat)}" data-cluster-id="${escapeHTML(cluster.cluster_id || "")}">
            <div class="territory-control-cluster-main">
                <strong>${escapeHTML(cluster.label || `Klaster ${cluster.cluster_id}`)}</strong>
                <span>${Number(cluster.node_count || 0)} wezlow · ${Number(cluster.pillar_count || 0)} filarow · ${Number(cluster.inner_count || 0)} innerow</span>
                <span>${escapeHTML(territoryControlArea(cluster.area_size))} · ${escapeHTML(territoryControlMeters(cluster.distance_from_bike))} od motocykla</span>
            </div>
            <div class="territory-control-threats">${renderTerritoryControlThreatBadges(cluster)}</div>
            <div class="territory-control-ghost-summary">${territoryControlGhostBadge(cluster)}</div>
            <div class="territory-control-actions">
                <button type="button" data-territory-control-action="cluster-detail" data-cluster-id="${escapeHTML(cluster.cluster_id || "")}" title="Otworz szczegoly">${TERRITORY_CONTROL_ICONS.open}</button>
                <button type="button" data-territory-control-action="cluster-map" data-cluster-id="${escapeHTML(cluster.cluster_id || "")}" title="Pokaz na mapie">${TERRITORY_CONTROL_ICONS.map}</button>
                <button type="button" data-territory-control-action="cluster-teleport" data-cluster-id="${escapeHTML(cluster.cluster_id || "")}" title="Teleport do klastra">${TERRITORY_CONTROL_ICONS.teleport}</button>
            </div>
        </article>
    `;
}

function renderTerritoryControlList(app, state) {
    state.view = "list";
    const clusters = Array.isArray(state.clusters) ? state.clusters : [];
    const alone = Array.isArray(state.alone_pillars) ? state.alone_pillars : [];
    const aloneInfo = alone.length ? `<p class="territory-control-alone-info">${alone.length} / 3 filary - dodaj kolejny filar, aby utworzyc klaster.</p>` : "";
    const body = `
        <section class="territory-control-list">
            ${clusters.length ? clusters.map(renderTerritoryClusterCard).join("") : `<div class="territory-control-empty">Brak aktywnych klastrow. Przejete filary pojawia sie jako samotne do czasu zbudowania trojkata.</div>`}
        </section>
        ${alone.length ? `
            <section class="territory-control-group">
                <h4>SAMOTNE FILARY <span>${alone.length}</span></h4>
                ${aloneInfo}
                <div class="territory-control-object-list">
                    ${alone.map(item => renderTerritoryControlObjectRow(item, { alone: true })).join("")}
                </div>
            </section>
        ` : ""}
    `;
    renderTerritoryControlFrame(app, state, body, { title: "TERRITORY CONTROL" });
    bindTerritoryControlListActions(app, state);
}

function bindTerritoryControlListActions(app, state) {
    const root = app.querySelector(".territory-control-shell");
    if (!root) return;
    root.querySelectorAll("[data-cluster-id][data-territory-control-action]").forEach(button => {
        button.addEventListener("click", async () => {
            const action = button.dataset.territoryControlAction;
            const cluster = getTerritoryControlClusterById(state, button.dataset.clusterId);
            if (!cluster) return;
            if (action === "cluster-detail") {
                await loadTerritoryControlCluster(app, state, cluster.cluster_id);
                return;
            }
            if (action === "cluster-map") {
                openTerritoryControlMapFocus(cluster.map_focus || cluster.centroid, cluster.label);
                return;
            }
            if (action === "cluster-teleport") {
                await teleportTerritoryControlObject(cluster.navigation_target || cluster.map_focus || cluster.centroid, () => loadTerritoryControlData(app, state, "list", { silent: true }));
            }
        });
    });
    bindTerritoryControlObjectActions(app, state);
}

function renderTerritoryControlObjectRow(item, options = {}) {
    const role = String(item.node_role || (options.alone ? "alone" : "inner"));
    const percent = Math.max(0, Math.min(100, Number(item.security_percent || 0)));
    const roleIcon = role === "pillar" ? TERRITORY_CONTROL_ICONS.pillar : role === "alone" ? TERRITORY_CONTROL_ICONS.alone : TERRITORY_CONTROL_ICONS.inner;
    const securityPreview = Object.entries(item.security || {})
        .filter(([, value]) => typeof value === "boolean")
        .slice(0, 8)
        .map(([key, value]) => `<button type="button" data-territory-control-action="security-toggle" data-target-id="${escapeHTML(item.target_id || "")}" data-security-key="${escapeHTML(key)}" title="${escapeHTML(key)}" class="${value ? "is-on" : ""}">${value ? "1" : "0"}</button>`)
        .join("");
    return `
        <article class="territory-control-object role-${escapeHTML(role)} ${item.is_aimed ? "is-aimed" : ""}" data-target-id="${escapeHTML(item.target_id || "")}">
            <div class="territory-control-object-icon">${escapeHTML(item.icon || roleIcon)}</div>
            <div class="territory-control-object-copy">
                <strong title="${escapeHTML(item.label || "")}">${escapeHTML(item.label || "unknown")}</strong>
                <span>${escapeHTML(role.toUpperCase())} · ${escapeHTML(territoryControlMeters(item.distance_from_bike))}</span>
                <div class="territory-control-security-bar" title="Zabezpieczenia ${percent}%">
                    <i style="width:${percent}%"></i>
                    <b>${percent}%</b>
                </div>
            </div>
            <div class="territory-control-presets">
                ${TERRITORY_CONTROL_PRESETS.map(preset => `<button type="button" data-territory-control-action="security-preset" data-target-id="${escapeHTML(item.target_id || "")}" data-preset="${preset.id}" title="${escapeHTML(preset.title || preset.label)}">${preset.label}</button>`).join("")}
            </div>
            <div class="territory-control-security-preview">${securityPreview || `<span>brak flag</span>`}</div>
            <div class="territory-control-actions">
                <button type="button" data-territory-control-action="object-abandon" data-target-id="${escapeHTML(item.target_id || "")}" title="Porzuc">${TERRITORY_CONTROL_ICONS.abandon}</button>
                <button type="button" data-territory-control-action="object-map" data-target-id="${escapeHTML(item.target_id || "")}" title="Pokaz na mapie">${TERRITORY_CONTROL_ICONS.map}</button>
                <button type="button" data-territory-control-action="object-teleport" data-target-id="${escapeHTML(item.target_id || "")}" title="Teleport">${TERRITORY_CONTROL_ICONS.teleport}</button>
            </div>
        </article>
    `;
}

function renderTerritoryControlCluster(app, state, cluster) {
    state.view = "cluster";
    state.currentClusterId = cluster?.cluster_id || state.currentClusterId;
    const pillars = Array.isArray(cluster?.pillars) ? cluster.pillars : [];
    const inners = Array.isArray(cluster?.inners) ? cluster.inners : [];
    const pillarRows = pillars.map(item => renderTerritoryControlObjectRow(item)).join("");
    const innerRows = inners.map(item => renderTerritoryControlObjectRow(item)).join("");
    const body = `
        <section class="territory-control-cluster-detail threat-${escapeHTML(cluster?.threat_state || "neutral")}">
            <div class="territory-control-detail-head">
                <div>
                    <strong>${escapeHTML(cluster?.label || `Klaster ${cluster?.cluster_id || ""}`)}</strong>
                    <span>${escapeHTML(territoryControlThreatSummary(cluster))} · ${escapeHTML(territoryControlArea(cluster?.area_size))} · ${escapeHTML(territoryControlMeters(cluster?.distance_from_bike))}</span>
                </div>
                <div class="territory-control-actions">
                    <button type="button" data-territory-control-action="cluster-map" data-cluster-id="${escapeHTML(cluster?.cluster_id || "")}" title="Pokaz klaster">${TERRITORY_CONTROL_ICONS.map}</button>
                    <button type="button" data-territory-control-action="cluster-teleport" data-cluster-id="${escapeHTML(cluster?.cluster_id || "")}" title="Teleport do klastra">${TERRITORY_CONTROL_ICONS.teleport}</button>
                </div>
            </div>
        </section>
        ${renderTerritoryControlGhostDetails(cluster)}
        <section class="territory-control-object-list territory-control-cluster-nodes">
            <div class="territory-control-category">
                <h4>FILARY <span>${pillars.length}</span></h4>
                ${pillarRows || `<div class="territory-control-empty">Brak filarow.</div>`}
            </div>
            <div class="territory-control-category">
                <h4>INNER NODES <span>${inners.length}</span></h4>
                ${innerRows || `<div class="territory-control-empty">Brak inner nodes.</div>`}
            </div>
        </section>
    `;
    renderTerritoryControlFrame(app, state, body, { back: "back-list", title: cluster?.label || "KLASTER" });
    bindTerritoryControlListActions(app, state);
}

async function applyTerritoryControlPreset(app, state, item, preset) {
    setTerritoryControlBusy(app, true, `Preset ${preset.toUpperCase()}...`);
    const preferredView = state.view;
    const preferredClusterId = state.currentClusterId;
    const preferredTargetId = item?.target_id;
    try {
        const response = await fetch("/api/ghost-control/territory/security-preset", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lat: item.lat, lng: item.lng, label: item.label, preset })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            addSystemMessage("warning", "TERRITORY CONTROL", data.message || data.error || "Nie udalo sie zapisac presetu.");
            return;
        }
        if (data.snapshot) {
            Object.assign(state, data.snapshot);
            state.view = preferredView;
            state.currentClusterId = preferredClusterId;
        }
        addSystemMessage("success", "TERRITORY CONTROL", `Preset ${preset.toUpperCase()} zapisany.`);
        await refreshTerritoryControlAfterMutation(app, state, data.snapshot, { preferredView, preferredClusterId, preferredTargetId });
    } finally {
        setTerritoryControlBusy(app, false);
    }
}

async function toggleTerritoryControlSecurity(app, state, item, action) {
    setTerritoryControlBusy(app, true, "Zmieniam flage...");
    const preferredView = state.view;
    const preferredClusterId = state.currentClusterId;
    const preferredTargetId = item?.target_id;
    try {
        const response = await fetch("/api/ghost-control/territory/security", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ lat: item.lat, lng: item.lng, label: item.label, action })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            addSystemMessage("warning", "TERRITORY CONTROL", data.message || data.error || "Nie udalo sie zapisac flagi.");
            return;
        }
        if (data.snapshot) {
            Object.assign(state, data.snapshot);
            state.view = preferredView;
            state.currentClusterId = preferredClusterId;
        }
        await refreshTerritoryControlAfterMutation(app, state, data.snapshot, { preferredView, preferredClusterId, preferredTargetId });
    } finally {
        setTerritoryControlBusy(app, false);
    }
}

async function abandonTerritoryControlObject(app, state, item) {
    const accepted = await showGhostDecisionDialog({
        title: "PORZUCENIE OBIEKTU",
        message: `Porzucic przejety obiekt: ${item.label || "unknown"}?`,
        details: "Obiekt zniknie z terytorium, a klastry i konflikty zostana przeliczone.",
        confirmLabel: "PORZUC",
        cancelLabel: "ANULUJ",
        tone: "red"
    });
    if (!accepted) return;
    setTerritoryControlBusy(app, true, "Porzucam obiekt...");
    try {
        const response = await fetch("/api/ghost-control/territory/abandon", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                target_id: item.target_id,
                ownership_version: item.ownership_version,
                lat: item.lat,
                lng: item.lng,
                label: item.label,
                confirm: true
            })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            addSystemMessage("warning", "TERRITORY CONTROL", data.message || data.error || "Nie udalo sie porzucic obiektu.");
            return;
        }
        addSystemMessage("success", "TERRITORY CONTROL", "Obiekt porzucony. Przebudowa terytorium zostala zlecona.");
        if (data.snapshot) Object.assign(state, data.snapshot);
        await refreshTerritoryControlAfterMutation(app, state, data.snapshot, { preferListOnMissingCluster: true });
    } finally {
        setTerritoryControlBusy(app, false);
    }
}

async function refreshTerritoryControlAfterMutation(app, state, snapshot = null, options = {}) {
    const preferredView = options.preferredView || state.view;
    const preferredClusterId = options.preferredClusterId || state.currentClusterId;
    const preferredTargetId = options.preferredTargetId;
    if (snapshot) {
        Object.assign(state, snapshot);
        state.view = preferredView;
        state.currentClusterId = preferredClusterId;
    } else {
        await loadTerritoryControlData(app, state, null, { silent: true, noRender: true });
        state.view = preferredView;
        state.currentClusterId = preferredClusterId;
    }
    if (preferredView === "cluster" && preferredClusterId && !options.forceList) {
        const cluster = getTerritoryControlClusterById(state, preferredClusterId)
            || getTerritoryControlClusterByTargetId(state, preferredTargetId);
        if (cluster) {
            state.currentClusterId = cluster.cluster_id;
            renderTerritoryControlCluster(app, state, cluster);
            return;
        }
        if (!options.preferListOnMissingCluster) {
            addSystemMessage("warning", "TERRITORY CONTROL", "Klaster zostal przeliczony. Wracam do listy.");
        }
    }
    renderTerritoryControlList(app, state);
}

function bindTerritoryControlObjectActions(app, state) {
    const root = app.querySelector(".territory-control-shell");
    if (!root) return;
    root.querySelectorAll("[data-territory-control-action][data-target-id]").forEach(button => {
        button.addEventListener("click", async () => {
            const action = button.dataset.territoryControlAction;
            const item = getTerritoryControlObjectById(state, button.dataset.targetId);
            if (!item) return;
            if (action === "security-preset") {
                await applyTerritoryControlPreset(app, state, item, button.dataset.preset || "regular");
                return;
            }
            if (action === "security-toggle") {
                await toggleTerritoryControlSecurity(app, state, item, button.dataset.securityKey);
                return;
            }
            if (action === "object-map") {
                openTerritoryControlMapFocus(item.map_focus || item, item.label);
                return;
            }
            if (action === "object-teleport") {
                setTerritoryControlBusy(app, true, "Teleport...");
                try {
                    await teleportTerritoryControlObject(item, () => loadTerritoryControlData(app, state, null, { silent: true, noRender: true }));
                } finally {
                    setTerritoryControlBusy(app, false);
                }
                return;
            }
            if (action === "object-abandon") {
                await abandonTerritoryControlObject(app, state, item);
            }
        });
    });
}

async function loadTerritoryControlCluster(app, state, clusterId) {
    setTerritoryControlBusy(app, true, "Pobieram klaster...");
    try {
        const response = await fetch(`/api/ghost-control/territory/${encodeURIComponent(clusterId)}`, { headers: { "Accept": "application/json" } });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false || !data.cluster) {
            addSystemMessage("warning", "TERRITORY CONTROL", data.message || data.error || "Klaster juz nie istnieje.");
            await loadTerritoryControlData(app, state, "list");
            return;
        }
        const cluster = data.cluster;
        state.currentClusterId = cluster.cluster_id;
        const existing = getTerritoryControlClusterById(state, cluster.cluster_id);
        if (existing) Object.assign(existing, cluster);
        renderTerritoryControlCluster(app, state, cluster);
    } finally {
        setTerritoryControlBusy(app, false);
    }
}

async function loadTerritoryControlData(app, state = {}, nextView = "list", options = {}) {
    const shell = app.querySelector(".territory-control-shell");
    if (!shell) return;
    if (!options.silent) setTerritoryControlBusy(app, true, "Pobieram terytorium...");
    if (!shell.dataset.initialized && !options.silent) {
        shell.dataset.initialized = "1";
        shell.innerHTML = `
            <div class="territory-control-loading">
                <span class="app-button-spinner" aria-hidden="true"></span>
                <b>Synchronizacja Territory Control...</b>
            </div>
        `;
    }
    try {
        const response = await fetch("/api/ghost-control/territory", { headers: { "Accept": "application/json" } });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            shell.innerHTML = `
                <div class="territory-control-error">
                    <strong>Territory Control offline</strong>
                    <p>${escapeHTML(data.message || data.error || "Nie udalo sie pobrac terytorium.")}</p>
                </div>
            `;
            return;
        }
        Object.assign(state, data);
        if (options.noRender) return;
        if (nextView === "cluster" && state.currentClusterId) {
            const cluster = getTerritoryControlClusterById(state, state.currentClusterId);
            if (cluster) renderTerritoryControlCluster(app, state, cluster);
            else renderTerritoryControlList(app, state);
        } else {
            renderTerritoryControlList(app, state);
        }
    } catch (error) {
        console.warn("Territory Control load failed", error);
        shell.innerHTML = `
            <div class="territory-control-error">
                <strong>Territory Control offline</strong>
                <p>Nie udalo sie polaczyc z endpointem terytorium.</p>
            </div>
        `;
    } finally {
        if (!options.silent) setTerritoryControlBusy(app, false);
    }
}

function createTerritoryControlApp() {
    const existing = document.querySelector('.app-window[data-app="territory-control"]');
    if (existing) {
        bringWindowToFront(existing);
        return existing;
    }

    const app = document.createElement('div');
    app.className = 'app-window territory-control-window';
    app.dataset.app = "territory-control";
    app.dataset.appIcon = TERRITORY_CONTROL_ICONS.app;
    app.dataset.appTitle = "Territory Control";
    const position = findAvailablePosition(860, 620);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.style.width = `860px`;
    app.style.height = `620px`;
    app.innerHTML = `
        <div class="title-bar">Territory Control <span class="close-btn" style="float:right; cursor:pointer;">✖</span></div>
        <div class="territory-control-shell"></div>
    `;

    document.body.appendChild(app);
    makeDraggable(app);
    bringWindowToFront(app);
    app.querySelector('.close-btn')?.addEventListener('click', () => app.remove());
    const state = { view: "list" };
    app._ghostControlPositionRefresh = () => loadTerritoryControlData(app, state, state.view || "list", { silent: true });
    loadTerritoryControlData(app, state, "list");
    return app;
}

window.createTerritoryControlApp = createTerritoryControlApp;
window.territory_control = createTerritoryControlApp;

const OPERATION_CONTROL_ICONS = {
    app: "📟",
    refresh: "⟳",
    map: "▣",
    cancel: "×",
    cancelGroup: "⊘",
    close: "×",
    gps: "⌖",
    recon: "◇",
    camera: "▣",
    network: "⌁",
    atm: "$",
    audio: "♪",
    vehicle: "▱",
    implant: "⌬",
    device: "▤",
    other: "□",
    incident: "!",
    warning: "△",
    file: "▥"
};

const OPERATION_CONTROL_FAMILY_LABELS = {
    gps: "GPS",
    recon: "RECON",
    camera: "CAMERA",
    network: "NETWORK",
    atm: "ATM",
    audio: "AUDIO",
    vehicle: "VEHICLE",
    implant: "IMPLANT",
    device: "DEVICE",
    other: "OTHER"
};

function operationControlFamilyLabel(family) {
    const key = String(family || "other").toLowerCase();
    return OPERATION_CONTROL_FAMILY_LABELS[key] || key.toUpperCase();
}

function operationControlIcon(family) {
    return OPERATION_CONTROL_ICONS[String(family || "other").toLowerCase()] || OPERATION_CONTROL_ICONS.other;
}

function operationControlMeters(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return "-";
    if (num >= 1000) return `${(num / 1000).toFixed(num >= 10000 ? 0 : 1)} km`;
    return `${Math.max(0, Math.round(num))} m`;
}

function operationControlCoords(position) {
    if (!position || !Number.isFinite(Number(position.lat)) || !Number.isFinite(Number(position.lng ?? position.lon))) return "-";
    return `${Number(position.lat).toFixed(4)}, ${Number(position.lng ?? position.lon).toFixed(4)}`;
}

function operationControlTime(seconds) {
    const value = Number(seconds);
    if (!Number.isFinite(value) || value <= 0) return "0:00";
    const total = Math.max(0, Math.round(value));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    return `${m}:${String(s).padStart(2, "0")}`;
}

function operationControlFileLabel(output) {
    output = output && typeof output === "object" ? output : {};
    const category = String(output.file_category || "system");
    const directory = output.directory || "-";
    const size = Number(output.expected_size_mb || 0);
    const status = output.output_status || "pending";
    return {
        title: `${category.toUpperCase()} ${size ? `~${size} MB` : ""}`.trim(),
        detail: `${directory} · ${status}`,
    };
}

function operationControlRiskClass(item) {
    const incident = item?.incident || {};
    const risk = item?.risk || {};
    if (incident.active) return "danger";
    if (incident.warning || risk.warning_crossed || risk.incident_crossed) return "warning";
    return "safe";
}

function operationControlRiskLabel(item) {
    const risk = item?.risk || {};
    const level = risk.level || item?.risk_level || "low";
    const heat = risk.current_heat ?? risk.score;
    return heat !== undefined && heat !== null ? `${level} · ${heat}` : String(level);
}

function setOperationControlBusy(app, busy, message = "") {
    const root = app?.querySelector(".operation-control-shell");
    if (!root) return;
    root.classList.toggle("is-busy", !!busy);
    root.querySelectorAll("button").forEach(button => {
        if (busy) {
            button.dataset.operationControlDisabled = button.disabled ? "1" : "0";
            button.disabled = true;
        } else if (button.dataset.operationControlDisabled === "0") {
            button.disabled = false;
        }
    });
    const status = root.querySelector("[data-operation-control-status]");
    if (status) {
        status.hidden = !busy && !message;
        status.textContent = message || "";
    }
}

function renderOperationControlFrame(app, state, bodyHtml, options = {}) {
    const root = app.querySelector(".operation-control-shell");
    if (!root) return null;
    const groups = Array.isArray(state.groups) ? state.groups : [];
    const activeCount = Number(state.active_count || 0);
    const incidentCount = Number(state.incident_count || 0);
    root.innerHTML = `
        <header class="operation-control-header">
            <div class="operation-control-brand">
                <span class="operation-control-brand-icon">${OPERATION_CONTROL_ICONS.app}</span>
                <div>
                    <strong>${escapeHTML(options.title || "OPERATION CONTROL")}</strong>
                    <span>Aktywne operacje, pliki i incydenty bez Leafleta</span>
                </div>
            </div>
            <div class="operation-control-meta">
                <span title="Aktywne operacje"><b>AKTYWNE</b> ${activeCount}</span>
                <span title="Operacje z incydentem"><b>INCYDENTY</b> ${incidentCount}</span>
                <span title="Grupy operacji"><b>GRUPY</b> ${groups.length}</span>
                <span title="Pozycja motocykla"><b>POS</b> ${escapeHTML(operationControlCoords(state.position))}</span>
            </div>
        </header>
        <nav class="operation-control-toolbar" aria-label="Operation Control tools">
            <button type="button" data-operation-control-action="refresh" title="Odswiez" aria-label="Odswiez">${OPERATION_CONTROL_ICONS.refresh}</button>
            <button type="button" data-operation-control-action="close" title="Zamknij" aria-label="Zamknij">${OPERATION_CONTROL_ICONS.close}</button>
        </nav>
        <div class="operation-control-status" data-operation-control-status hidden></div>
        <section class="operation-control-screen" data-operation-control-screen>${bodyHtml || ""}</section>
    `;
    bindOperationControlCommonActions(app, state);
    return root;
}

function bindOperationControlCommonActions(app, state) {
    const root = app.querySelector(".operation-control-shell");
    if (!root) return;
    root.querySelector('[data-operation-control-action="refresh"]')?.addEventListener("click", () => loadOperationControlData(app, state, { silent: false }));
    root.querySelector('[data-operation-control-action="close"]')?.addEventListener("click", () => app.remove());
}

function renderOperationControlGroup(group, operations) {
    const family = String(group.operation_family || "other");
    const outputTypes = Array.isArray(group.output_types) && group.output_types.length ? group.output_types.join(", ") : "-";
    const incidentCount = Number(group.incident_count || 0);
    const groupOperations = operations.filter(item => String(item.operation_family || "other") === family);
    const expectedMb = groupOperations.reduce((sum, item) => sum + Number(item?.output?.expected_size_mb || 0), 0);
    return `
        <section class="operation-control-group family-${escapeHTML(family)}" data-operation-family="${escapeHTML(family)}">
            <header class="operation-control-group-head">
                <div class="operation-control-group-title">
                    <span>${operationControlIcon(family)}</span>
                    <div>
                        <strong>${escapeHTML(operationControlFamilyLabel(family))}</strong>
                        <em>${Number(group.count || 0)} operacji · ${incidentCount} incydentow · ${expectedMb} MB</em>
                    </div>
                </div>
                <div class="operation-control-group-output" title="Przewidywany output">${escapeHTML(outputTypes)}</div>
                <button type="button" data-operation-control-action="cancel-group" data-operation-family="${escapeHTML(family)}" title="Anuluj cala grupe" aria-label="Anuluj cala grupe">${OPERATION_CONTROL_ICONS.cancelGroup}</button>
            </header>
            <div class="operation-control-rows">
                ${groupOperations.map(renderOperationControlRow).join("")}
            </div>
        </section>
    `;
}

function renderOperationControlRow(item) {
    const family = String(item.operation_family || "other");
    const riskClass = operationControlRiskClass(item);
    const output = operationControlFileLabel(item.output);
    const incident = item.incident || {};
    const incidentBadge = incident.active
        ? `<span class="operation-control-incident danger">${OPERATION_CONTROL_ICONS.incident} INCYDENT L${escapeHTML(incident.level || "-")}</span>`
        : incident.warning
            ? `<span class="operation-control-incident warning">${OPERATION_CONTROL_ICONS.warning} WARNING</span>`
            : `<span class="operation-control-incident safe">czysto</span>`;
    const distance = item.distance_available ? operationControlMeters(item.distance_from_bike) : "brak pozycji";
    return `
        <article class="operation-control-row risk-${escapeHTML(riskClass)}" data-operation-id="${escapeHTML(item.operation_id || "")}">
            <div class="operation-control-row-icon">${operationControlIcon(family)}</div>
            <div class="operation-control-row-main">
                <strong title="${escapeHTML(item.operation_type || "")}">${escapeHTML(item.label || item.operation_type || "operacja")}</strong>
                <span>Target: ${escapeHTML(item.target_label || item.target_id || "-")}</span>
                <span>Dystans: ${escapeHTML(distance)} · Pozostalo: ${escapeHTML(operationControlTime(item.remaining_seconds))}</span>
            </div>
            <div class="operation-control-output">
                <b>${OPERATION_CONTROL_ICONS.file} ${escapeHTML(output.title)}</b>
                <span>${escapeHTML(output.detail)}</span>
            </div>
            <div class="operation-control-risk">
                <b>${escapeHTML(operationControlRiskLabel(item))}</b>
                ${incidentBadge}
                ${incident.active ? `<span>${escapeHTML(incident.status || "active")} ${incident.arrival_at ? `· ETA ${escapeHTML(String(incident.arrival_at))}` : ""}</span>` : ""}
            </div>
            <div class="operation-control-actions">
                <button type="button" data-operation-control-action="cancel-operation" data-operation-id="${escapeHTML(item.operation_id || "")}" title="${item.can_cancel ? "Anuluj operacje" : "Operacja zakonczona"}" aria-label="Anuluj operacje" ${item.can_cancel ? "" : "disabled data-original-disabled=\"1\""}>${OPERATION_CONTROL_ICONS.cancel}</button>
            </div>
        </article>
    `;
}

function renderOperationControl(app, state) {
    const operations = Array.isArray(state.operations) ? state.operations : Array.isArray(state.active_operations) ? state.active_operations : [];
    const groups = Array.isArray(state.groups) ? state.groups.filter(group => Number(group.count || 0) > 0) : [];
    const body = operations.length ? `
        <section class="operation-control-list">
            ${groups.map(group => renderOperationControlGroup(group, operations)).join("")}
        </section>
        ${Array.isArray(state.operation_history) && state.operation_history.length ? `
            <section class="operation-control-history">
                <h4>HISTORIA <span>${state.operation_history.length}</span></h4>
                ${state.operation_history.slice(-8).reverse().map(item => {
                    const output = operationControlFileLabel(item.output);
                    return `<div class="operation-control-history-row"><b>${escapeHTML(item.operation_type || item.operation_id || "-")}</b><span>${escapeHTML(output.title)} · ${escapeHTML(item.status || "-")}</span></div>`;
                }).join("")}
            </section>
        ` : ""}
    ` : `
        <div class="operation-control-empty">
            <strong>Brak aktywnych operacji.</strong>
            <span>Operation Control odswiezy sie po uruchomieniu narzedzia albo recznym odswiezeniu.</span>
        </div>
    `;
    renderOperationControlFrame(app, state, body);
    bindOperationControlActions(app, state);
}

function operationControlGroupByFamily(state, family) {
    const operations = Array.isArray(state.operations) ? state.operations : [];
    return operations.filter(item => String(item.operation_family || "other") === String(family || "other") && item.can_cancel);
}

async function cancelOperationControlItem(app, state, item) {
    const accepted = await showGhostDecisionDialog({
        title: "ANULOWANIE OPERACJI",
        message: `Anulowac operacje ${item.operation_type || item.operation_id || "unknown"}?`,
        details: "Wynik operacji moze zostac utracony, a powiazane ryzyko zostanie przeliczone.",
        confirmLabel: "ANULUJ OPERACJE",
        cancelLabel: "WRÓC",
        tone: "red"
    });
    if (!accepted) return;
    setOperationControlBusy(app, true, "Anuluje operacje...");
    try {
        const response = await fetch("/api/ghost-control/operations/cancel", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ operation_id: item.operation_id })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            addSystemMessage("warning", "OPERATION CONTROL", data.message || data.error || "Nie udalo sie anulowac operacji.");
            return;
        }
        if (data.snapshot) Object.assign(state, data.snapshot);
        addSystemMessage("success", "OPERATION CONTROL", data.message || "Operacja anulowana.");
        renderOperationControl(app, state);
    } finally {
        setOperationControlBusy(app, false);
    }
}

async function cancelOperationControlGroup(app, state, family) {
    const groupItems = operationControlGroupByFamily(state, family);
    if (!groupItems.length) {
        addSystemMessage("warning", "OPERATION CONTROL", "Brak aktywnych operacji w tej grupie.");
        return;
    }
    const outputTypes = Array.from(new Set(groupItems.map(item => item?.output?.file_category).filter(Boolean)));
    const incidentCount = groupItems.filter(item => item?.incident?.active).length;
    const accepted = await showGhostDecisionDialog({
        title: "ANULOWANIE GRUPY",
        message: `Anulowac grupe ${operationControlFamilyLabel(family)} (${groupItems.length} operacji)?`,
        details: `Output: ${outputTypes.join(", ") || "-"} | Incydenty: ${incidentCount}. Wyniki aktywnych operacji moga zostac utracone.`,
        confirmLabel: "ANULUJ GRUPE",
        cancelLabel: "WRÓC",
        tone: "red"
    });
    if (!accepted) return;
    setOperationControlBusy(app, true, "Anuluje grupe...");
    try {
        const response = await fetch("/api/ghost-control/operations/cancel-group", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                operation_family: family,
                operation_ids: groupItems.map(item => item.operation_id)
            })
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            addSystemMessage("warning", "OPERATION CONTROL", data.message || data.error || "Nie udalo sie anulowac grupy.");
            return;
        }
        if (data.snapshot) Object.assign(state, data.snapshot);
        addSystemMessage("success", "OPERATION CONTROL", `Anulowano ${Array.isArray(data.cancelled) ? data.cancelled.length : 0} operacji.`);
        renderOperationControl(app, state);
    } finally {
        setOperationControlBusy(app, false);
    }
}

function bindOperationControlActions(app, state) {
    const root = app.querySelector(".operation-control-shell");
    if (!root) return;
    root.querySelectorAll('[data-operation-control-action="cancel-operation"]').forEach(button => {
        button.addEventListener("click", async () => {
            const operationId = button.dataset.operationId;
            const item = (state.operations || []).find(operation => String(operation.operation_id || "") === String(operationId || ""));
            if (item) await cancelOperationControlItem(app, state, item);
        });
    });
    root.querySelectorAll('[data-operation-control-action="cancel-group"]').forEach(button => {
        button.addEventListener("click", async () => {
            await cancelOperationControlGroup(app, state, button.dataset.operationFamily || "other");
        });
    });
}

async function loadOperationControlData(app, state = {}, options = {}) {
    const shell = app.querySelector(".operation-control-shell");
    if (!shell) return;
    if (!options.silent) setOperationControlBusy(app, true, "Pobieram operacje...");
    if (!shell.dataset.initialized && !options.silent) {
        shell.dataset.initialized = "1";
        shell.innerHTML = `
            <div class="operation-control-loading">
                <span class="app-button-spinner" aria-hidden="true"></span>
                <b>Synchronizacja Operation Control...</b>
            </div>
        `;
    }
    try {
        const response = await fetch("/api/ghost-control/operations", { headers: { "Accept": "application/json" } });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            shell.innerHTML = `
                <div class="operation-control-error">
                    <strong>Operation Control offline</strong>
                    <p>${escapeHTML(data.message || data.error || "Nie udalo sie pobrac operacji.")}</p>
                </div>
            `;
            return;
        }
        Object.assign(state, data);
        renderOperationControl(app, state);
    } catch (error) {
        console.warn("Operation Control load failed", error);
        shell.innerHTML = `
            <div class="operation-control-error">
                <strong>Operation Control offline</strong>
                <p>Nie udalo sie polaczyc z endpointem operacji.</p>
            </div>
        `;
    } finally {
        if (!options.silent) setOperationControlBusy(app, false);
    }
}

function createOperationControlApp() {
    const existing = document.querySelector('.app-window[data-app="operation-control"]');
    if (existing) {
        bringWindowToFront(existing);
        return existing;
    }

    const app = document.createElement('div');
    app.className = 'app-window operation-control-window';
    app.dataset.app = "operation-control";
    app.dataset.appIcon = OPERATION_CONTROL_ICONS.app;
    app.dataset.appTitle = "Operation Control";
    const position = findAvailablePosition(900, 640);
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.style.width = `900px`;
    app.style.height = `640px`;
    app.innerHTML = `
        <div class="title-bar">Operation Control <span class="close-btn" style="float:right; cursor:pointer;">✖</span></div>
        <div class="operation-control-shell"></div>
    `;

    document.body.appendChild(app);
    makeDraggable(app);
    bringWindowToFront(app);
    app.querySelector('.close-btn')?.addEventListener('click', () => app.remove());
    const state = {};
    loadOperationControlData(app, state);
    return app;
}

window.createOperationControlApp = createOperationControlApp;
window.operation_control = createOperationControlApp;

const GHOSTNETWORK_SUITE_ENDPOINT = "/api/ghostnetwork/snapshot?view=suite";
const GHOSTNETWORK_SUITE_SECTIONS = [
    { id: "all", label: "WSZYSTKIE" },
    { id: "public", label: "PUBLICZNE" },
    { id: "blocked", label: "BLOKOWANE" },
    { id: "active", label: "AKTYWNE" },
    { id: "control", label: "MOJA KONTROLA" },
];
const GHOSTNETWORK_SUITE_PART_DELTA_TYPES = new Set([
    "ghost.part_discovered", "ghost.part_contained", "ghost.part_revealed",
    "ghost.part_activated", "ghost.part_deactivated", "ghost.part_contested",
    "ghost.part_conflict_resolved", "ghost.part_anchor_migrated",
    "ghost.part_updated", "ghost.part_consumed", "ghost.part_recovered",
    "ghost.part_defended", "ghost.part_anchor_source_lost",
]);
const GHOSTNETWORK_SUITE_CYCLE_DELTA_TYPES = new Set([
    "ghost.cycle_created", "ghost.cycle_activated", "ghost.cycle_status_changed",
    "ghost.cycle_state_changed",
    "ghost.cycle_locked", "ghost.version_changed", "ghost.restart_required",
    "ghost.signal_sent",
]);
const GHOSTNETWORK_SUITE_RECOVERY_DELTA_TYPES = new Set([
    "ghost.parts_created", "ghost.parts_consumed", "ghost.connections_closed",
    "ghost.topology_created", "ghost.stabilization_started", "ghost.abilities_disabled",
]);

function ghostnetworkSuiteIndex(snapshot = {}) {
    const parts = Array.isArray(snapshot.parts) ? snapshot.parts : [];
    const byId = new Map(parts.map(part => [String(part?.public_entity_id || ""), part]).filter(([id]) => id));
    const groups = snapshot.groups && typeof snapshot.groups === "object" ? snapshot.groups : {};
    const refs = key => (Array.isArray(groups[key]) ? groups[key] : []).map(String).filter(id => byId.has(id));
    const sectionIds = {
        public: refs("public"),
        blocked: refs("blocked"),
        active: refs("clan_active"),
        control: [...refs("self_foreign"), ...refs("self_own")],
    };
    parts.forEach(part => {
        const id = String(part?.public_entity_id || "");
        if (id && part?.viewer_relation === "foreign_active" && !sectionIds.active.includes(id)) sectionIds.active.push(id);
    });
    Object.keys(sectionIds).forEach(key => { sectionIds[key] = [...new Set(sectionIds[key])]; });
    return { parts, byId, sectionIds };
}

function ghostnetworkSuiteVisibleText(part = {}) {
    const owner = part.owner || {};
    const territory = part.territory || {};
    const safe = [
        part.display_label, part.summary, part.status, part.conflict_state, part.viewer_relation,
        owner.owner_alias, owner.owner_clan, territory.territory_id, territory.owner_alias, territory.owner_clan,
    ];
    if (part.identity_visible === true) safe.push(part.name, part.part_code, part.machine_code, part.profession_code);
    if (part.ability_visible === true) safe.push(part.ability_name, part.ability_code);
    return safe.filter(Boolean).join(" ").toLocaleLowerCase("pl");
}

function ghostnetworkSuiteSortValue(part, sort) {
    if (sort === "distance") return Number.isFinite(Number(part?.distance_m)) ? Number(part.distance_m) : Number.MAX_SAFE_INTEGER;
    if (sort === "state") return `${part?.conflict_state === "contested" ? "0" : "1"}:${part?.status || ""}`;
    if (sort === "clan") return String(part?.owner?.owner_clan || part?.territory?.owner_clan || "");
    if (sort === "owner") return String(part?.owner?.owner_alias || "");
    if (sort === "updated") return -Date.parse(part?.updated_at || 0) || 0;
    const priority = part?.conflict_state === "contested" ? 0 : String(part?.viewer_relation || "").startsWith("self_") ? 1 : part?.module_state === "active" ? 2 : 3;
    return `${priority}:${part?.display_label || part?.public_entity_id || ""}`;
}

function ghostnetworkSuiteSelect(snapshot, filter = "all", query = "", sort = "strategic") {
    const index = ghostnetworkSuiteIndex(snapshot);
    const allowed = filter === "all" ? null : new Set(index.sectionIds[filter] || []);
    const needle = String(query || "").trim().toLocaleLowerCase("pl");
    return index.parts
        .filter(part => !allowed || allowed.has(String(part?.public_entity_id || "")))
        .filter(part => !needle || ghostnetworkSuiteVisibleText(part).includes(needle))
        .sort((a, b) => {
            const left = ghostnetworkSuiteSortValue(a, sort);
            const right = ghostnetworkSuiteSortValue(b, sort);
            if (typeof left === "number" && typeof right === "number" && left !== right) return left - right;
            const compared = String(left).localeCompare(String(right), "pl");
            return compared || String(a?.public_entity_id || "").localeCompare(String(b?.public_entity_id || ""), "pl");
        });
}

function ghostnetworkSuiteDeltaPartFromMapProjection(projection = {}, previous = null, cycleActive = true) {
    const item = { ...projection };
    const identity = item.identity_visible === true;
    if (!identity) {
        [
            "part_id", "part_code", "name", "machine_code", "machine_name",
            "profession_code", "profession_name", "ability_code", "ability_name",
            "ability_description", "visual_asset_key", "visual_asset_url", "target_id",
        ].forEach(key => { item[key] = null; });
    }
    const locationVisibility = String(item.location_visibility || item.location?.visibility || "");
    const exact = locationVisibility === "exact";
    const territoryId = String(item.territory_id || item.territory?.territory_id || "") || null;
    const ownerId = String(item.territory_owner_id || item.owner?.owner_id || "") || null;
    const previousOwner = previous?.owner || {};
    const preservedAlias = ownerId && String(previousOwner.owner_id || "") === ownerId
        ? previousOwner.owner_alias || null : null;
    if (!exact) {
        item.latitude = null;
        item.longitude = null;
    }
    const lifecycleStatus = String(item.status || "").toLowerCase();
    const liveStatus = ["public", "contained", "active"].includes(lifecycleStatus);
    let targetType = null;
    let targetId = null;
    if (exact && item.public_entity_id && item.latitude != null && item.longitude != null) {
        targetType = "ghostnetwork_part";
        targetId = String(item.public_entity_id);
    } else if (locationVisibility === "territory_only" && territoryId) {
        targetType = "ghostnetwork_territory";
        targetId = territoryId;
    }
    const enabled = Boolean(cycleActive && liveStatus && targetType && targetId);
    item.owner = {
        owner_id: ownerId,
        owner_alias: item.owner?.owner_alias || preservedAlias,
        owner_clan: item.territory_clan || item.owner?.owner_clan || null,
    };
    item.territory = {
        territory_id: territoryId,
        cluster_id: territoryId,
        owner_id: ownerId,
        owner_alias: item.owner.owner_alias,
        owner_clan: item.territory_clan || item.territory?.owner_clan || null,
        conflict_state: item.conflict_state || "none",
    };
    item.location = {
        visibility: locationVisibility || null,
        latitude: exact ? item.latitude : null,
        longitude: exact ? item.longitude : null,
        map_focus_type: enabled ? targetType : null,
        map_focus_id: enabled ? targetId : null,
    };
    item.actions = {
        can_show_on_map: enabled && item.can_show_on_map === true,
        can_teleport: enabled,
        map_target_type: enabled ? targetType : null,
        map_target_id: enabled ? targetId : null,
        teleport_target_type: enabled ? targetType : null,
        teleport_target_id: enabled ? targetId : null,
    };
    return item;
}

function ghostnetworkSuiteRebuildDerived(snapshot = {}) {
    const seen = new Set();
    snapshot.parts = (Array.isArray(snapshot.parts) ? snapshot.parts : [])
        .filter(part => {
            const id = String(part?.public_entity_id || "");
            if (!id || seen.has(id)) return false;
            seen.add(id);
            return true;
        })
        .slice(0, 20);
    const groups = { public: [], blocked: [], clan_active: [], self_foreign: [], self_own: [] };
    const relationGroups = {
        public_neutral: "public", foreign_blocked: "blocked",
        clan_own_active: "clan_active", self_foreign_blocked: "self_foreign",
        self_own_active: "self_own",
    };
    snapshot.parts.forEach(part => {
        const group = relationGroups[String(part?.viewer_relation || "")];
        if (group) groups[group].push(String(part.public_entity_id));
    });
    Object.keys(groups).forEach(key => { groups[key] = [...new Set(groups[key])].sort(); });
    snapshot.groups = groups;
    snapshot.summary = {
        parts_total: snapshot.parts.length,
        parts_discovered: snapshot.parts.length,
        parts_public: snapshot.parts.filter(part => part?.viewer_relation === "public_neutral").length,
        parts_blocked: snapshot.parts.filter(part => part?.module_state === "blocked").length,
        parts_active: snapshot.parts.filter(part => part?.module_state === "active").length,
        parts_contested: snapshot.parts.filter(part => part?.contested === true).length,
        parts_visible_to_viewer: snapshot.parts.length,
    };
    return snapshot;
}

function ghostnetworkSuiteDisableActions(snapshot = {}) {
    (snapshot.parts || []).forEach(part => {
        part.actions = {
            ...(part.actions || {}),
            can_show_on_map: false, can_teleport: false,
            map_target_type: null, map_target_id: null,
            teleport_target_type: null, teleport_target_id: null,
        };
    });
    return snapshot;
}

function ghostnetworkSuiteApplyDelta(app, state, event = {}) {
    if (!app?.isConnected || state.closed || !state.snapshot) return false;
    const type = String(event.type || "");
    const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
    const eventCycleId = String(payload.cycle_id || event.cycle_id || "");
    const currentCycleId = String(state.snapshot.cycle?.cycle_id || "");
    if (eventCycleId && currentCycleId && eventCycleId !== currentCycleId) return false;
    let handled = false;

    if (GHOSTNETWORK_SUITE_PART_DELTA_TYPES.has(type)) {
        const projection = payload.suite_part_projection || payload.part_projection || null;
        const publicId = String(
            projection?.public_entity_id || payload.public_entity_id || event.entity_id || ""
        );
        if (!publicId) return false;
        const parts = Array.isArray(state.snapshot.parts) ? state.snapshot.parts : [];
        const index = parts.findIndex(part => String(part?.public_entity_id || "") === publicId);
        if (type === "ghost.part_consumed" || payload.removed === true) {
            if (index >= 0) parts.splice(index, 1);
            handled = true;
        } else {
            if (!projection) return false;
            if (index < 0 && type !== "ghost.part_discovered") return false;
            const previous = index >= 0 ? parts[index] : null;
            const cycleActive = !state.restartRequired
                && String(state.snapshot.cycle?.status || "active").toLowerCase() === "active";
            const normalized = ghostnetworkSuiteDeltaPartFromMapProjection(projection, previous, cycleActive);
            if (index >= 0) parts[index] = normalized;
            else parts.push(normalized);
            handled = true;
        }
        ghostnetworkSuiteRebuildDerived(state.snapshot);
    } else if (type.startsWith("ghost.connection_")) {
        const projection = payload.suite_connection_projection || payload.connection_projection || null;
        const publicId = String(projection?.public_connection_id || event.entity_id || "");
        if (!publicId) return false;
        const connections = Array.isArray(state.snapshot.connections) ? state.snapshot.connections : [];
        const index = connections.findIndex(item => String(item?.public_connection_id || "") === publicId);
        if (type === "ghost.connection_removed" || payload.removed === true) {
            if (index >= 0) connections.splice(index, 1);
        } else if (projection) {
            const safeProjection = {
                public_connection_id: publicId,
                state: projection.state,
                state_version: projection.state_version,
                viewer_relation: projection.viewer_relation,
                can_show_on_map: projection.can_show_on_map === true,
            };
            if (index >= 0) connections[index] = safeProjection;
            else connections.push(safeProjection);
        } else return false;
        handled = true;
    } else if (GHOSTNETWORK_SUITE_RECOVERY_DELTA_TYPES.has(type)) {
        return false;
    } else if (type.startsWith("ghost.machine_")) {
        state.snapshot.progress = {
            ...(state.snapshot.progress || {}),
            last_machine_delta: payload.machine_progress || {},
        };
        handled = true;
    } else if (GHOSTNETWORK_SUITE_CYCLE_DELTA_TYPES.has(type)) {
        if (payload.cycle && typeof payload.cycle === "object") {
            state.snapshot.cycle = { ...(state.snapshot.cycle || {}), ...payload.cycle };
        }
        if (payload.progress && typeof payload.progress === "object") {
            state.snapshot.progress = { ...(state.snapshot.progress || {}), ...payload.progress };
        }
        if (type === "ghost.restart_required" || type === "ghost.cycle_locked") {
            state.restartRequired = true;
            ghostnetworkSuiteDisableActions(state.snapshot);
        }
        if (["ghost.cycle_activated", "ghost.version_changed"].includes(type)
                || (["ghost.cycle_status_changed", "ghost.cycle_state_changed"].includes(type)
                    && String(state.snapshot.cycle?.status || "").toLowerCase() === "active")) {
            state.restartRequired = false;
            return false;
        }
        handled = true;
    }
    if (!handled) return false;
    const version = Number(payload.state_version || event.state_version || 0);
    if (Number.isFinite(version) && version > 0) {
        state.snapshot.state_version = Math.max(Number(state.snapshot.state_version || 0), version);
    }
    if (payload.snapshot_checksum) state.snapshot.snapshot_checksum = payload.snapshot_checksum;
    renderGhostNetworkSuite(app, state);
    return true;
}

function ghostnetworkSuiteCard(part = {}) {
    const identity = part.identity_visible === true;
    const ability = part.ability_visible === true;
    const asset = part.visual_asset_url || part.marker_asset_url || "";
    const location = part.location || {};
    const owner = part.owner || {};
    const territory = part.territory || {};
    const actions = part.actions || {};
    const canMap = actions.can_show_on_map === true;
    const canTeleport = actions.can_teleport === true;
    const displayLabel = String(part.display_label || "CZESC GHOSTNETWORK");
    const summary = String(part.summary || "").trim();
    const distinctSummary = summary && summary.toLocaleLowerCase("pl") !== displayLabel.trim().toLocaleLowerCase("pl") ? summary : "";
    const conflictState = String(part.conflict_state || "").trim().toLowerCase();
    const locationLabel = location.visibility === "exact" ? "LOKACJA DOKLADNA" : location.visibility === "territory_only" ? "TYLKO TERYTORIUM" : "LOKACJA UKRYTA";
    return `
        <article class="ghostnetwork-suite-card" data-part-ref="${escapeHTML(part.public_entity_id || "")}">
            <div class="ghostnetwork-suite-card-icon">${asset ? `<img src="${escapeHTML(asset)}" alt="">` : "◈"}</div>
            <div class="ghostnetwork-suite-card-main">
                <strong>${escapeHTML(displayLabel)}</strong>
                ${distinctSummary ? `<span>${escapeHTML(distinctSummary)}</span>` : ""}
                <small>${escapeHTML(locationLabel)} · ${escapeHTML(part.viewer_relation || "public")}</small>
                ${identity && part.profession_code ? `<small>PROFESJA: ${escapeHTML(part.profession_code)}</small>` : ""}
                ${ability && (part.ability_name || part.ability_code) ? `<small>ZDOLNOSC: ${escapeHTML(part.ability_name || part.ability_code)}</small>` : ""}
                <details><summary>SZCZEGOLY</summary>
                    ${identity && part.part_code ? `<small>KOD: ${escapeHTML(part.part_code)}</small>` : ""}
                    ${identity && (part.machine_name || part.machine_code) ? `<small>MASZYNA: ${escapeHTML(part.machine_name || part.machine_code)}</small>` : ""}
                    ${owner.owner_alias ? `<small>WLASCICIEL: ${escapeHTML(owner.owner_alias)}</small>` : ""}
                    ${(owner.owner_clan || territory.owner_clan) ? `<small>KLAN: ${escapeHTML(owner.owner_clan || territory.owner_clan)}</small>` : ""}
                    ${territory.territory_id ? `<small>TERYTORIUM: ${escapeHTML(territory.territory_id)}</small>` : ""}
                    ${part.discovered_at ? `<small>ODKRYTO: ${escapeHTML(part.discovered_at)}</small>` : ""}
                    ${part.updated_at ? `<small>AKTUALIZACJA: ${escapeHTML(part.updated_at)}</small>` : ""}
                </details>
            </div>
            <div class="ghostnetwork-suite-card-state"><b>${escapeHTML(part.status || "unknown")}</b>${conflictState && conflictState !== "none" ? `<span>${escapeHTML(conflictState)}</span>` : ""}</div>
            <div class="ghostnetwork-suite-card-actions">
                <button type="button" data-suite-card-action="map" ${canMap ? "" : "disabled data-original-disabled=\"1\""} title="${canMap ? "Pokaz na mapie" : "Mapa niedostepna dla aktualnej projekcji"}" aria-label="Pokaz czesc GhostNetwork na mapie">${TERRITORY_CONTROL_ICONS.map}</button>
                <button type="button" data-suite-card-action="teleport" ${canTeleport ? "" : "disabled data-original-disabled=\"1\""} title="${canTeleport ? "Teleport" : "Teleport niedostepny dla aktualnej projekcji"}" aria-label="Teleport do czesci GhostNetwork">${TERRITORY_CONTROL_ICONS.teleport}</button>
            </div>
        </article>`;
}

function ghostnetworkSuiteCycleStatus(cycle = {}) {
    const status = String(cycle.status || "active").toLowerCase();
    if (status === "transmitting") return "GHOSTNETWORK ZAMKNIETY · TRANSMISJA W TOKU";
    if (status === "stabilizing") return "NOWY CYKL OCZEKUJE NA STABILIZACJE";
    if (status === "preparing") return "PRZYGOTOWANIE NOWEGO CYKLU";
    if (status === "closed") return "AKTYWNY CYKL ZAKONCZONY";
    return "STABILNIE";
}

function ghostnetworkSuiteOpaqueAction(part = {}, actionName = "map") {
    const actions = part.actions || {};
    const targetType = String(actions[`${actionName}_target_type`] || "");
    const targetId = String(actions[`${actionName}_target_id`] || "");
    if (!targetId || !["ghostnetwork_part", "ghostnetwork_territory"].includes(targetType)) return null;
    return {
        source: "ghostnetwork_suite",
        target_type: targetType,
        public_entity_id: targetType === "ghostnetwork_part" ? targetId : undefined,
        territory_id: targetType === "ghostnetwork_territory" ? targetId : undefined,
    };
}

function openGhostNetworkSuiteMap(part = {}) {
    const target = ghostnetworkSuiteOpaqueAction(part, "map");
    if (!target) {
        addSystemMessage("warning", "GHOSTNETWORK SUITE", "Mapa jest niedostepna dla aktualnej projekcji czesci.");
        return false;
    }
    createMap();
    window.setTimeout(() => notifyOpenMapsBlacknetFocus({
        ...target,
        mode: "ghostnetwork_suite",
        label: part.display_label || "GhostNetwork",
    }), 80);
    if (target.target_type === "ghostnetwork_territory") {
        addSystemMessage("info", "GHOSTNETWORK SUITE", "Dokladna lokalizacja komponentu jest ukryta. Pokazano terytorium przechowujace czesc.");
    }
    return true;
}

function notifyGhostControlPositionChanged(detail = {}) {
    document.querySelectorAll('.app-window[data-app="victim-picker"], .app-window[data-app="territory-control"], .app-window[data-app="ghostnetwork-suite"]').forEach(app => {
        if (typeof app._ghostControlPositionRefresh === "function") app._ghostControlPositionRefresh(detail);
    });
}

async function teleportGhostNetworkSuitePart(app, state, part = {}) {
    if (state.actionPending) return false;
    const target = ghostnetworkSuiteOpaqueAction(part, "teleport");
    if (!target) {
        addSystemMessage("warning", "GHOSTNETWORK SUITE", "Teleport jest niedostepny dla aktualnej projekcji czesci.");
        return false;
    }
    const territoryOnly = target.target_type === "ghostnetwork_territory";
    const conflictWarning = part.contested || part.conflict_state === "contested" ? " Uwaga: komponent znajduje sie w aktywnym konflikcie." : "";
    const accepted = await showGhostDecisionDialog({
        title: territoryOnly ? "TELEPORT DO TERYTORIUM Z KOMPONENTEM" : "TELEPORT DO WEZLA GHOSTNETWORK",
        message: `Wykonac teleport: ${part.display_label || "GhostNetwork"}?`,
        details: `${territoryOnly ? "Cel: bezpieczny punkt terytorium; ukryta kotwica nie zostanie ujawniona." : "Cel: aktualna dokladna pozycja wezla."}${conflictWarning}`,
        confirmLabel: "TELEPORT",
        cancelLabel: "ANULUJ",
        tone: part.contested ? "red" : "lime",
    });
    if (!accepted) return false;
    state.actionPending = true;
    renderGhostNetworkSuite(app, state);
    try {
        const response = await fetch("/api/blacknet/cta/teleport", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(target),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || data.success === false) {
            addSystemMessage("warning", "GHOSTNETWORK SUITE", data.message || "Teleport odrzucony przez aktualna projekcje.");
            await loadGhostNetworkSuite(app, state);
            return false;
        }
        addSystemMessage("success", "GHOSTNETWORK SUITE", data.message || "Teleport wykonany.");
        const position = data.current_position || data.curently_possition || {};
        if (Number.isFinite(Number(position.lat)) && Number.isFinite(Number(position.lng))) {
            createMap();
            window.setTimeout(() => notifyOpenMapsBlacknetFocus({
                mode: "teleport", source: "ghostnetwork_suite",
                lat: Number(position.lat), lng: Number(position.lng),
                position_version: data.position_version,
                position_updated_at: data.position_updated_at,
            }), 80);
        }
        notifyGhostControlPositionChanged({ source: "ghostnetwork_suite", position, position_version: data.position_version });
        return true;
    } catch (error) {
        console.warn("GhostNetwork Suite teleport failed", { reason: String(error?.message || "transport_error") });
        addSystemMessage("warning", "GHOSTNETWORK SUITE", "Nie udalo sie wykonac teleportu.");
        return false;
    } finally {
        state.actionPending = false;
        renderGhostNetworkSuite(app, state);
    }
}

function renderGhostNetworkSuite(app, state) {
    const shell = app?.querySelector(".ghostnetwork-suite-shell");
    if (!shell) return;
    const renderedCards = shell.querySelectorAll("[data-part-ref]");
    const expanded = renderedCards.length ? new Set() : new Set(state.expandedPartIds || []);
    shell.querySelectorAll("[data-part-ref] details[open]").forEach(details => {
        const id = details.closest("[data-part-ref]")?.dataset.partRef || "";
        if (id) expanded.add(id);
    });
    state.expandedPartIds = expanded;
    const previousScrollTop = shell.scrollTop;
    const searchWasFocused = document.activeElement?.matches?.("[data-suite-search]")
        && shell.contains(document.activeElement);
    const searchSelection = searchWasFocused ? {
        start: document.activeElement.selectionStart,
        end: document.activeElement.selectionEnd,
    } : null;
    const snapshot = state.snapshot || {};
    const summary = snapshot.summary || {};
    const cycle = snapshot.cycle || {};
    const selected = ghostnetworkSuiteSelect(snapshot, state.filter, state.query, state.sort);
    const stale = state.error && state.snapshot;
    shell.innerHTML = `
        <header class="ghostnetwork-suite-header"><div><strong>GHOSTNETWORK // CYKL ${escapeHTML(cycle.cycle_id || "-")}</strong><span>${escapeHTML(snapshot.system_version || cycle.system_version || "GHOSTSYSTEM")}</span></div><div class="ghostnetwork-suite-counters"><b>ODKRYTE ${Number(summary.parts_discovered || 0)} / 20</b><b>AKTYWNE ${Number(summary.parts_active || 0)} / 20</b><b>BLOKOWANE ${Number(summary.parts_blocked || 0)}</b><b>PUBLICZNE ${Number(summary.parts_public || 0)}</b></div></header>
        <div class="ghostnetwork-suite-toolbar"><nav>${GHOSTNETWORK_SUITE_SECTIONS.map(section => `<button type="button" data-suite-filter="${section.id}" class="${state.filter === section.id ? "is-active" : ""}">${section.label}</button>`).join("")}</nav><input type="search" data-suite-search value="${escapeHTML(state.query || "")}" placeholder="Szukaj w widocznych danych" aria-label="Szukaj czesci GhostNetwork"><select data-suite-sort aria-label="Sortowanie czesci"><option value="strategic" ${state.sort === "strategic" ? "selected" : ""}>STRATEGICZNE</option><option value="distance" ${state.sort === "distance" ? "selected" : ""}>ODLEGLOSC</option><option value="state" ${state.sort === "state" ? "selected" : ""}>STAN</option><option value="clan" ${state.sort === "clan" ? "selected" : ""}>KLAN</option><option value="owner" ${state.sort === "owner" ? "selected" : ""}>WLASCICIEL</option><option value="updated" ${state.sort === "updated" ? "selected" : ""}>OSTATNIA ZMIANA</option></select><button type="button" data-suite-refresh>ODSWIEZ</button></div>
        <div class="ghostnetwork-suite-status ${state.error ? "is-error" : ""}">${state.loading ? "SYNCHRONIZACJA GHOSTNETWORK · ODCZYT PROJEKCJI WEZLOW" : state.restartRequired ? "RESTART GHOSTSYSTEMU WYMAGANY · AKCJE ZABLOKOWANE" : stale ? `DANE STALE · ${escapeHTML(state.error)}` : state.error ? escapeHTML(state.error) : `${ghostnetworkSuiteCycleStatus(cycle)} · v${escapeHTML(snapshot.state_version || "-")}`}</div>
        <section class="ghostnetwork-suite-list">${selected.length ? selected.map(ghostnetworkSuiteCard).join("") : `<div class="ghostnetwork-suite-empty">${state.loading ? "Synchronizacja GhostNetwork..." : "Brak czesci dla wybranego filtra."}</div>`}</section>`;
    shell.querySelectorAll("[data-part-ref]").forEach(card => {
        const details = card.querySelector("details");
        if (details && expanded.has(card.dataset.partRef || "")) details.open = true;
    });
    shell.scrollTop = previousScrollTop;
    if (searchWasFocused) {
        const input = shell.querySelector("[data-suite-search]");
        input?.focus();
        if (input && searchSelection) {
            input.setSelectionRange(searchSelection.start, searchSelection.end);
        }
    }
    shell.querySelectorAll("[data-suite-filter]").forEach(button => button.addEventListener("click", () => { state.filter = button.dataset.suiteFilter || "all"; renderGhostNetworkSuite(app, state); }));
    shell.querySelector("[data-suite-search]")?.addEventListener("input", event => {
        state.query = event.target.value || "";
        renderGhostNetworkSuite(app, state);
        const input = app.querySelector("[data-suite-search]");
        input?.focus();
        input?.setSelectionRange(state.query.length, state.query.length);
    });
    shell.querySelector("[data-suite-sort]")?.addEventListener("change", event => { state.sort = event.target.value || "strategic"; renderGhostNetworkSuite(app, state); });
    shell.querySelector("[data-suite-refresh]")?.addEventListener("click", () => loadGhostNetworkSuite(app, state));
    shell.querySelectorAll("[data-suite-card-action]").forEach(button => {
        button.addEventListener("pointerdown", event => event.stopPropagation());
        button.addEventListener("click", async event => {
        event.preventDefault();
        event.stopPropagation();
        const partId = button.closest("[data-part-ref]")?.dataset.partRef || "";
        const part = (state.snapshot?.parts || []).find(item => String(item?.public_entity_id || "") === partId);
        if (!part) return;
        if (button.dataset.suiteCardAction === "map") openGhostNetworkSuiteMap(part);
        if (button.dataset.suiteCardAction === "teleport") await teleportGhostNetworkSuitePart(app, state, part);
        });
    });
    if (state.actionPending || state.restartRequired) shell.querySelectorAll("[data-suite-card-action]").forEach(button => { button.disabled = true; });
}

function ghostnetworkSuiteSetBaseline(snapshot = {}) {
    const client = window.GhostNetworkDeltaClient;
    if (!client || typeof client.setBaseline !== "function") return false;
    client.setBaseline({
        view: "suite",
        cycleId: snapshot.cycle?.cycle_id || "",
        stateVersion: snapshot.state_version || snapshot.current_version || 0,
        snapshotChecksum: snapshot.snapshot_checksum || "",
    });
    return true;
}

function scheduleGhostNetworkSuiteRecovery(app, state, reason = "delta_recovery") {
    if (state.closed || !app?.isConnected) return false;
    if (state.recoveryTimer) return true;
    const attempt = Math.min(3, Number(state.recoveryAttempt || 0) + 1);
    state.recoveryAttempt = attempt;
    const delay = attempt === 1 ? 0 : Math.min(2000, 500 * (2 ** (attempt - 2)));
    state.recoveryTimer = window.setTimeout(async () => {
        state.recoveryTimer = null;
        const recovered = await loadGhostNetworkSuite(app, state, { recovery: true, reason });
        if (!recovered && attempt < 3) scheduleGhostNetworkSuiteRecovery(app, state, reason);
    }, delay);
    return true;
}

async function loadGhostNetworkSuite(app, state, options = {}) {
    if (state.closed || !app?.isConnected) return false;
    if (state.loading) {
        if (options.recovery) state.recoveryPending = true;
        return false;
    }
    state.loading = true;
    state.error = "";
    renderGhostNetworkSuite(app, state);
    let loaded = false;
    try {
        const response = await fetch(GHOSTNETWORK_SUITE_ENDPOINT, { credentials: "same-origin", cache: "no-store", headers: { "Accept": "application/json" } });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || payload?.suite_health?.ok === false) throw new Error(payload?.message || payload?.error || "Snapshot GhostNetwork jest niedostepny.");
        state.snapshot = payload;
        state.restartRequired = payload.restart_required === true
            || String(payload.cycle?.status || "").toLowerCase() === "restart_required";
        state.recoveryAttempt = 0;
        ghostnetworkSuiteSetBaseline(payload);
        loaded = true;
    } catch (error) {
        state.error = error?.message || "Nie udalo sie pobrac GhostNetwork Suite.";
        console.warn("GhostNetwork Suite load failed", { reason: state.error });
    } finally {
        state.loading = false;
        if (!state.closed && app?.isConnected) renderGhostNetworkSuite(app, state);
        if (state.recoveryPending && !state.closed) {
            state.recoveryPending = false;
            scheduleGhostNetworkSuiteRecovery(app, state, "delta_during_snapshot");
        }
    }
    return loaded;
}

function connectGhostNetworkSuiteDelta(app, state) {
    const client = window.GhostNetworkDeltaClient;
    if (!client || typeof client.registerAdapter !== "function") return false;
    const adapterName = `suite_${Date.now()}_${Math.random().toString(16).slice(2)}`;
    state.deltaAdapterName = client.registerAdapter(adapterName, {
        accepts(event = {}) {
            const type = String(event.type || "");
            return GHOSTNETWORK_SUITE_PART_DELTA_TYPES.has(type)
                || GHOSTNETWORK_SUITE_CYCLE_DELTA_TYPES.has(type)
                || GHOSTNETWORK_SUITE_RECOVERY_DELTA_TYPES.has(type)
                || type.startsWith("ghost.connection_")
                || type.startsWith("ghost.machine_");
        },
        apply(event) {
            if (state.loading || !state.snapshot) {
                state.recoveryPending = true;
                return true;
            }
            return ghostnetworkSuiteApplyDelta(app, state, event);
        },
        recover(reason) {
            return scheduleGhostNetworkSuiteRecovery(app, state, reason);
        },
    });
    app._ghostNetworkSuiteRecover = reason => scheduleGhostNetworkSuiteRecovery(app, state, reason);
    return Boolean(state.deltaAdapterName);
}

function disconnectGhostNetworkSuiteDelta(app, state) {
    state.closed = true;
    if (state.recoveryTimer) window.clearTimeout(state.recoveryTimer);
    state.recoveryTimer = null;
    const client = window.GhostNetworkDeltaClient;
    if (state.deltaAdapterName && client && typeof client.unregisterAdapter === "function") {
        client.unregisterAdapter(state.deltaAdapterName);
    }
    state.deltaAdapterName = "";
    if (app) {
        app._ghostNetworkSuiteRecover = null;
        app._ghostControlPositionRefresh = null;
    }
    return true;
}

function createGhostNetworkSuiteApp() {
    const existing = document.querySelector('.app-window[data-app="ghostnetwork-suite"]');
    if (existing) { bringWindowToFront(existing); return existing; }
    const app = document.createElement("div");
    app.className = "app-window ghostnetwork-suite-window";
    app.dataset.app = "ghostnetwork-suite";
    app.dataset.appIcon = "◈";
    app.dataset.appTitle = "GhostNetwork Suite";
    const position = findAvailablePosition(920, 650);
    Object.assign(app.style, { top: `${position.top}px`, left: `${position.left}px`, width: "920px", height: "650px" });
    app.innerHTML = `<div class="title-bar">GhostNetwork Suite <span class="close-btn" style="float:right; cursor:pointer;">✖</span></div><div class="ghostnetwork-suite-shell"></div>`;
    document.body.appendChild(app);
    makeDraggable(app);
    bringWindowToFront(app);
    const state = {
        filter: "all", query: "", sort: "strategic", loading: false,
        actionPending: false, error: "", snapshot: null, closed: false,
        restartRequired: false, recoveryPending: false, recoveryAttempt: 0,
        recoveryTimer: null, deltaAdapterName: "", expandedPartIds: new Set(),
    };
    app.querySelector(".close-btn")?.addEventListener("click", () => {
        disconnectGhostNetworkSuiteDelta(app, state);
        app.remove();
    });
    app._ghostControlPositionRefresh = () => loadGhostNetworkSuite(app, state);
    connectGhostNetworkSuiteDelta(app, state);
    loadGhostNetworkSuite(app, state);
    return app;
}

window.createGhostNetworkSuiteApp = createGhostNetworkSuiteApp;
window.ghostnetwork_suite = createGhostNetworkSuiteApp;

function createAgi2108ConsoleApp() {
    const existing = document.querySelector('.app-window[data-app="agi2108-console"]');
    if (existing) { bringWindowToFront(existing); return existing; }

    const app = document.createElement('div');
    app.className = 'app-window agi2108-console-window';
    app.dataset.app = 'agi2108-console';
    app.dataset.appIcon = '⌬';
    app.dataset.appTitle = 'AGI 2108 Console';
    const position = findAvailablePosition(620, 520);
    Object.assign(app.style, {
        top: `${position.top}px`, left: `${position.left}px`,
        width: '620px', height: '520px'
    });
    app.innerHTML = `
        <div class="title-bar">AGI 2108 Console <span class="close-btn" style="float:right; cursor:pointer;">✖</span></div>
        <div class="agi2108-shell">
            <header class="agi2108-header">
                <span class="agi2108-mark" aria-hidden="true">⌬</span>
                <span><strong>AGI 2108 // OWNER ANALYSIS</strong><small>Canonical narrative transport</small></span>
                <i>5 / H</i>
            </header>
            <section class="agi2108-contract">
                <span>TEMPLATE <b>owner-analysis</b></span>
                <span>MEDIUM <b>Cyberner / AGI 2108</b></span>
                <span>COST <b>0 HC</b></span>
            </section>
            <label class="agi2108-topic-label" for="agi2108-topic">TEMAT ANALIZY</label>
            <textarea id="agi2108-topic" class="agi2108-topic" maxlength="120" rows="4" placeholder="Wpisz temat analizy operatorskiej (maks. 120 znaków)"></textarea>
            <div class="agi2108-compose-footer"><span data-agi-count>0 / 120</span><button type="button" data-agi-submit>WYŚLIJ TASK</button></div>
            <section class="agi2108-status" data-agi-status data-state="idle">
                <strong>GOTOWY</strong><span>Brak aktywnego receipt.</span><small></small>
            </section>
            <section class="agi2108-result" data-agi-result hidden>
                <strong></strong><p></p><small></small>
            </section>
            <button type="button" class="agi2108-result-link" disabled>WYNIK W CYBERNER AGI 2108</button>
        </div>`;
    document.body.appendChild(app);
    makeDraggable(app);
    bringWindowToFront(app);

    const topicInput = app.querySelector('.agi2108-topic');
    const count = app.querySelector('[data-agi-count]');
    const submit = app.querySelector('[data-agi-submit]');
    const status = app.querySelector('[data-agi-status]');
    const resultPanel = app.querySelector('[data-agi-result]');
    const resultLink = app.querySelector('.agi2108-result-link');
    const username = String((toolbarProfile || {}).username || (toolbarProfile || {}).nick || 'owner').trim().toLowerCase();
    const receiptStorageKey = `agi2108:receipt:${username}`;
    const pendingStorageKey = `agi2108:pending:${username}`;
    let receiptId = '';
    let pendingAction = null;
    let pollTimer = null;
    let submitting = false;

    const setStatus = (state, title, message, detail = '') => {
        status.dataset.state = state;
        status.querySelector('strong').textContent = title;
        status.querySelector('span').textContent = message;
        status.querySelector('small').textContent = detail;
    };
    const receiptShort = value => String(value || '').slice(0, 22);
    const stopPolling = () => {
        if (pollTimer) window.clearTimeout(pollTimer);
        pollTimer = null;
    };
    const scheduleStatus = () => {
        stopPolling();
        if (app.isConnected && receiptId) pollTimer = window.setTimeout(loadStatus, 5000);
    };
    const loadStatus = async () => {
        if (!receiptId || !app.isConnected) return;
        try {
            const response = await fetch(`/api/googleplex/llm/tasks/${encodeURIComponent(receiptId)}`, {
                credentials: 'same-origin', cache: 'no-store'
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.success === false) {
                setStatus('failed', 'STATUS NIEDOSTĘPNY', data.message || 'Nie udało się odtworzyć receipt.', receiptShort(receiptId));
                return;
            }
            const receipt = data.receipt || {};
            const publication = data.publication && typeof data.publication === 'object' ? data.publication : null;
            const state = String(receipt.status || 'accepted');
            const labels = {
                accepted: ['PRZYJĘTO', 'Task został przyjęty do canonical transportu.'],
                queued: ['W KOLEJCE', 'Task oczekuje na lokalny worker AGI.'],
                processing: ['PRZETWARZANIE', 'AGI 2108 przetwarza bounded package.'],
                completed: ['ZAKOŃCZONO', publication ? 'Wynik AGI 2108 jest gotowy.' : 'Candidate oczekuje na bezpieczną publikację.'],
                failed: ['NIEPOWODZENIE', receipt.user_message || 'Task zakończył się kontrolowanym błędem.']
            };
            const label = labels[state] || labels.accepted;
            setStatus(
                state,
                label[0],
                receipt.user_message || label[1],
                `RECEIPT ${receiptShort(receipt.receipt_id || receiptId)}`
            );
            if (publication && resultPanel && resultLink) {
                resultPanel.querySelector('strong').textContent = String(publication.title || 'AGI 2108');
                resultPanel.querySelector('p').textContent = String(publication.body || '');
                resultPanel.querySelector('small').textContent = `SOURCE ${publication.source || 'canonical'} // ${publication.truth_class || 'canonical'} // RECEIPT ${receiptShort(publication.publication_receipt_id)}`;
                resultPanel.hidden = false;
                resultLink.disabled = false;
            }
            if (state === 'accepted' || state === 'queued' || state === 'processing') scheduleStatus();
        } catch (_error) {
            setStatus('failed', 'BRAK POŁĄCZENIA', 'Status pozostaje zapisany. Ponowimy po otwarciu aplikacji.', receiptShort(receiptId));
        }
    };

    topicInput?.addEventListener('input', () => {
        if (count) count.textContent = `${topicInput.value.length} / 120`;
    });
    resultLink?.addEventListener('click', () => {
        if (!resultPanel || resultLink.disabled) return;
        resultPanel.hidden = !resultPanel.hidden;
    });
    submit?.addEventListener('click', async () => {
        const value = String(topicInput?.value || '').trim();
        if (!value) {
            setStatus('failed', 'BRAK TEMATU', 'Wpisz temat analizy.');
            topicInput?.focus();
            return;
        }
        if (submitting) return;
        submitting = true;
        submit.disabled = true;
        const clientReceipt = (
            pendingAction && pendingAction.topic === value && pendingAction.receipt_id
                ? pendingAction.receipt_id
                : `agi2108:${globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`}`
        );
        pendingAction = {receipt_id: clientReceipt, topic: value};
        try { window.sessionStorage?.setItem(pendingStorageKey, JSON.stringify(pendingAction)); } catch (_error) {}
        setStatus('accepted', 'WYSYŁANIE', 'Walidacja entitlement, template i receipt...');
        try {
            const requestPayload = {
                app_id: 'agi2108Console',
                app_action_id: clientReceipt,
                client_receipt_id: clientReceipt,
                approved_template_id: 'owner-analysis',
                input: {topic: value}
            };
            const response = await fetch('/api/googleplex/llm/tasks', {
                method: 'POST', credentials: 'same-origin',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(requestPayload)
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data.success === false) {
                setStatus('failed', 'TASK ODRZUCONY', data.message || 'Polityka AGI odrzuciła zlecenie.', String(data.reason_code || 'request_rejected'));
                if (response.status < 500) {
                    pendingAction = null;
                    try { window.sessionStorage?.removeItem(pendingStorageKey); } catch (_error) {}
                }
                return;
            }
            receiptId = String(data.receipt_id || '');
            if (receiptId) window.sessionStorage?.setItem(receiptStorageKey, receiptId);
            pendingAction = null;
            try { window.sessionStorage?.removeItem(pendingStorageKey); } catch (_error) {}
            setStatus('accepted', 'PRZYJĘTO', 'Utworzono jeden owner-scoped task.', `RECEIPT ${receiptShort(receiptId)}`);
            topicInput.value = '';
            if (count) count.textContent = '0 / 120';
            scheduleStatus();
        } catch (_error) {
            setStatus('failed', 'BRAK POŁĄCZENIA', 'Task nie został potwierdzony. Spróbuj ponownie.');
        } finally {
            submitting = false;
            submit.disabled = false;
        }
    });

    app.querySelector('.close-btn')?.addEventListener('click', () => {
        stopPolling();
        app.remove();
    });
    try {
        receiptId = String(window.sessionStorage?.getItem(receiptStorageKey) || '');
        const savedPending = JSON.parse(window.sessionStorage?.getItem(pendingStorageKey) || 'null');
        if (savedPending && savedPending.receipt_id && savedPending.topic) {
            pendingAction = savedPending;
            topicInput.value = String(savedPending.topic).slice(0, 120);
            if (count) count.textContent = `${topicInput.value.length} / 120`;
            setStatus('accepted', 'NIEPOTWIERDZONY RECEIPT', 'Ponowienie użyje tej samej tożsamości taska.', receiptShort(savedPending.receipt_id));
        }
    } catch (_error) {
        receiptId = '';
        pendingAction = null;
    }
    if (receiptId && !pendingAction) loadStatus();
    topicInput?.focus();
    return app;
}

window.createAgi2108ConsoleApp = createAgi2108ConsoleApp;
window.agi2108_console = createAgi2108ConsoleApp;

function appHasMapRuntime(appData) {
    if (!appData || typeof appData !== "object") return false;
    const actions = Array.isArray(appData.map_actions) ? appData.map_actions : [];
    const operations = Array.isArray(appData.operation_types) ? appData.operation_types : [];
    return actions.some(Boolean) && operations.some(Boolean);
}

function notifyAppMapOperationStarted(appData) {
    if (!appHasMapRuntime(appData)) return;
    const appId = appData.id;
    if (!appId) return;
    const context = buildApplicationLaunchContext(appData);
    const receiptScope = "operation_only";
    const flowId = getCurrentAppFlowId(context.flow_id || appData.debug_flow?.flow_id || "");
    const queuedAt = performance.now();
    appFlowTrace(flowId, "operation_start_queued_from_app_launch", {
        app_id: appId,
        app_name: appData.name || "",
        launch_key: context.launch_key,
        launch_receipt: context.launch_receipt
    });
    enqueueGonnaWinRequest(async () => {
        appFlowTrace(flowId, "operation_start_request_start", {
            app_id: appId,
            queue_wait_ms: Math.round(performance.now() - queuedAt)
        });
        const startedAt = performance.now();
        const requestOrdinal = nextGonnaWinRequestOrdinal(context, receiptScope);
        const response = await fetch('/gonna-win', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Hack-Flow-Id': flowId
            },
            body: JSON.stringify({
                app_id: appId,
                operation_only: true,
                _flow_id: flowId,
                launch_key: context.launch_key,
                launch_receipt: context.launch_receipt,
                launch_source: context.source,
                expected_target: context.expected_target,
                request_ordinal: requestOrdinal
            })
        });
        const data = await response.json();
        rememberGonnaWinCanonicalResult(context, receiptScope, data || {});
        appFlowTrace(flowId, "operation_start_response", {
            app_id: appId,
            status: response.status,
            elapsed_ms: Math.round(performance.now() - startedAt),
            created_operations: (data.created_operations || []).map(op => op && op.operation_id)
        });
        const responseMatchesCurrentTarget = applicationResponseMatchesCurrentTarget(context);
        if (!responseMatchesCurrentTarget) {
            appFlowTrace(flowId, "stale_operation_start_response_ignored", {
                app_id: appId,
                expected_target: context.expected_target,
                current_target: ((toolbarProfile || {}).aimed_target || {})
            });
        }
        if (data.target && responseMatchesCurrentTarget) {
            updateToolbarAimedTarget(data.target);
            appFlowTrace(flowId, "toolbar_dot_updated_from_operation_start", {
                app_id: appId,
                target_label: data.target.label || data.target.display_label || data.target.name || ""
            });
        }
        notifyCreatedOperations(data);
        return data;
    }).catch(error => {
        console.warn(`Nie udalo sie wystartowac operacji mapy dla ${appId}:`, error);
        return null;
    });
}

async function sendGonnaWinRequest(appId, choiceId = null, appWindow = null) {
    if (typeof choiceId === "string") {
        const normalizedChoiceId = choiceId.trim();
        choiceId = (!normalizedChoiceId || normalizedChoiceId === "run_generated")
            ? null
            : normalizedChoiceId;
    }
    const context = currentApplicationLaunchContext(appWindow);
    const flowId = context.flow_id;
    const receiptScope = `choice:${choiceId !== null ? choiceId : "auto"}`;
    const queuedAt = performance.now();
    appFlowTrace(flowId, "app_option_request_queued", {
        app_id: appId,
        choice_id: choiceId,
        launch_key: context.launch_key
    });
    const feedback = beginOperationFeedbackRequest(appWindow, appId, {
        legacyWait: !(appWindow && appWindow._legacyAppWaitActive),
        receiptScope
    });
    return enqueueGonnaWinRequest(async () => {
        appFlowTrace(flowId, "app_option_request_start", {
            app_id: appId,
            choice_id: choiceId,
            queue_wait_ms: Math.round(performance.now() - queuedAt)
        });
        const startedAt = performance.now();
        let response;
        let data;
        try {
            const requestOrdinal = nextGonnaWinRequestOrdinal(context, receiptScope);
            response = await fetch('/gonna-win', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Hack-Flow-Id': flowId
                },
                body: JSON.stringify({
                    app_id: appId,
                    choice_id: choiceId,
                    _flow_id: flowId,
                    launch_key: context.launch_key,
                    launch_receipt: context.launch_receipt,
                    launch_source: context.source,
                    expected_target: context.expected_target,
                    request_ordinal: requestOrdinal
                })
            });
            data = await response.json();
        } catch (error) {
            throw error;
        }
        data = preserveCanonicalGonnaWinSuccess(context, receiptScope, data);
        rememberGonnaWinCanonicalResult(context, receiptScope, data || {});
        appFlowTrace(flowId, "app_option_response", {
            app_id: appId,
            choice_id: choiceId,
            invocation_id: context.invocation_id,
            launch_receipt: context.launch_receipt,
            expected_target_id: getToolbarTargetStableKey(context.expected_target || {}),
            current_target_id: getToolbarTargetStableKey(((toolbarProfile || {}).aimed_target || {})),
            status: response.status,
            elapsed_ms: Math.round(performance.now() - startedAt),
            success: Boolean(data.success),
            duplicate: Boolean(data.duplicate),
            idempotent_replay: Boolean(data.idempotent_replay),
            captured: Boolean(data.captured_target),
            created_operations: (data.created_operations || []).map(op => op && op.operation_id)
        });
        if (response.status === 409) {
            console.warn('[gonna-win] Kontrolowany konflikt stanu', {
                app_id: appId,
                choice_id: choiceId,
                reason: data.reason || data.error || 'conflict',
                message: data.message || '',
                target_id: data.target_id || '',
                current_owner_username: data.current_owner_username || '',
                ownership_version: data.ownership_version
            });
        }
        if (data.player_hack_access) {
            refreshPlayerHackAccess(data.player_hack_access);
        }
        const responseMatchesCurrentTarget = applicationResponseMatchesCurrentTarget(context);
        if (!responseMatchesCurrentTarget) {
            appFlowTrace(flowId, "stale_target_response_ignored", {
                app_id: appId,
                choice_id: choiceId,
                expected_target: context.expected_target,
                current_target: ((toolbarProfile || {}).aimed_target || {})
            });
        }
        const capturedOnToolbar = responseMatchesCurrentTarget
            ? handleToolbarTargetCapturedResult(data)
            : false;
        if (data.target && !capturedOnToolbar && responseMatchesCurrentTarget) {
            updateToolbarAimedTarget(data.target);
            appFlowTrace(flowId, "toolbar_dot_updated_from_app_option", {
                app_id: appId,
                choice_id: choiceId,
                target_label: data.target.label || data.target.display_label || data.target.name || "",
                actions_allowed: data.target.actions_allowed || null
            });
        }
        notifyCreatedOperations(data);
        if (data.success && data.captured_target && responseMatchesCurrentTarget && !data.semantic_success_preserved) {
            playAuthoritativeCaptureSfx(data.captured_target);
            notifyOpenMapsTargetHacked(data.captured_target);
            refreshToolbarProfile();
            appFlowTrace(flowId, "target_captured_from_app_option", {
                app_id: appId,
                choice_id: choiceId,
                target_label: data.captured_target.label || data.captured_target.display_label || data.captured_target.name || ""
            });
        }
        feedback.complete(data);
        return data;
    }).catch(error => {
        const preserved = preserveCanonicalGonnaWinSuccess(context, receiptScope, null);
        if (preserved && preserved.success === true) {
            feedback.complete(preserved);
            appFlowTrace(flowId, "gonna_win_transport_failure_after_canonical_success", {
                app_id: appId,
                receipt_scope: receiptScope,
                ofs_terminal_state: "success"
            });
            return preserved;
        }
        feedback.fail(error && error.name ? error.name : "application_result_processing_failed");
        console.error("Błąd komunikacji z backendem:", error);
        return { success: false };
    });
}

function app_terminal(id, levels) {
    if (!beginApplicationRenderLaunch(id, "terminal")) return null;
    const safeLevels = Array.isArray(levels) ? levels : [];
    const level = safeLevels.length
        ? safeLevels[Math.floor(Math.random() * safeLevels.length)]
        : {};
    const logs = Array.isArray(level.logs) ? level.logs : [];
    const command = String(level.command || `./${id}.sh`);
    const outputLines = logs.length ? logs : ["Raport zapisany."];

    const { app, hydrated, appTitle } = prepareApplicationRenderWindow(id, "terminal");
    app.innerHTML = `
        <div class="title-bar">${escapeHTML(appTitle)} <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content app-terminal-content ofs-author-shell ofs-author-terminal">
            <div class="ofs-terminal-sysinfo" data-terminal-sysinfo="RUNNING">RUNNING</div>
            <div class="terminal-log app-terminal-log"></div>
            <div class="operation-feedback-host"></div>
        </div>
    `;
    finishApplicationRenderWindow(app, hydrated);
    app.querySelector('.close-btn').addEventListener('click', () => {
        disposeOperationFeedbackWindow(app, "window_closed");
        app.remove();
    });
    appFlowTrace(app.dataset.appFlowId, "app_window_rendered", { app_id: id, interface: "terminal" });

    const log = app.querySelector('.terminal-log');
    function scrollLogToBottom() {
        const content = app.querySelector('.app-terminal-content');
        if (content) content.scrollTop = content.scrollHeight;
    }

    function simulateTyping(command, callback) {
        const safeCommand = String(command || '');
        const line = document.createElement('div');
        line.className = 'terminal-line app-terminal-line';
        const label = document.createElement('span');
        label.className = 'app-terminal-prompt';
        label.textContent = 'remote@host:~$ ';
        const typingSpan = document.createElement('span');
        typingSpan.className = 'app-terminal-command is-typing';
        line.appendChild(label);
        line.appendChild(typingSpan);
        log.appendChild(line);
        scrollLogToBottom();

        let charIndex = 0;
        const typingInterval = setInterval(() => {
            typingSpan.textContent += safeCommand[charIndex] || '';
            charIndex++;
            if (charIndex >= safeCommand.length) {
                clearInterval(typingInterval);
                typingSpan.classList.remove('is-typing');
                setTimeout(() => {
                    callback();
                    scrollLogToBottom();
                }, 260 + Math.floor(Math.random() * 320));
            }
        }, 34 + Math.floor(Math.random() * 28));
    }

    async function confirmTerminalRuntime() {
        const resultLine = document.createElement('div');
        resultLine.className = 'terminal-line app-terminal-line app-terminal-runtime-result';
        resultLine.textContent = '[WAIT] oczekiwanie na potwierdzenie runtime';
        log.appendChild(resultLine);
        scrollLogToBottom();
        const success = await notifyGonnaWin(id, app, { legacyWait: false });
        if (!app.isConnected) return;
        resultLine.textContent = success
            ? '[OK] operacja potwierdzona przez runtime'
            : '[ERROR] runtime odrzucil operacje';
        resultLine.dataset.tone = success ? 'success' : 'failure';
        app.querySelector('[data-terminal-sysinfo]')?.setAttribute(
            'data-terminal-sysinfo',
            success ? 'COMPLETE' : 'FAILED'
        );
        const sysinfo = app.querySelector('[data-terminal-sysinfo]');
        if (sysinfo) sysinfo.textContent = success ? 'COMPLETE' : 'FAILED';
        if (success) scheduleOperationalAppAutoClose(app);
    }

    function emitTerminalOutput(index = 0) {
        if (!app.isConnected) return;
        if (index >= outputLines.length) {
            confirmTerminalRuntime();
            return;
        }
        const line = document.createElement('div');
        line.className = 'terminal-line app-terminal-line app-terminal-output';
        line.textContent = String(outputLines[index] || '');
        log.appendChild(line);
        window.requestAnimationFrame(() => line.classList.add('is-visible'));
        scrollLogToBottom();
        const delay = 420 + Math.floor(Math.random() * 480);
        window.setTimeout(() => emitTerminalOutput(index + 1), delay);
    }

    const titleRemainingMs = app.dataset.ofsTitleActive === "true"
        ? Math.max(0, Number(app._ofsTitleEndsAt || 0) - performance.now())
        : 0;
    window.setTimeout(() => {
        if (app.isConnected) simulateTyping(command, () => emitTerminalOutput(0));
    }, titleRemainingMs);
}

function app_button_choices(id, levels) {
    if (!beginApplicationRenderLaunch(id, "button_choices")) return null;
    const safeLevels = Array.isArray(levels) ? levels : [];
    const lvl = safeLevels[0] || {};
    const options = Array.isArray(lvl.options) && lvl.options.length
        ? lvl.options.map((option, index) => normalizeButtonChoiceOption(option, index))
        : [{ id: 0, label: "Wykonaj", effect: {} }];
    const { app, hydrated, appTitle } = prepareApplicationRenderWindow(id, "button_choices");

    app.innerHTML = `
        <div class="title-bar">${escapeHTML(appTitle)} <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content ofs-author-shell ofs-author-button-choice">
            <header class="ofs-author-header"><span>DECISION</span><h3>${escapeHTML(lvl.title || 'Wybierz opcj\u0119')}</h3></header>
            <section class="ofs-author-content"><p>${escapeHTML(lvl.text || '')}</p></section>
            <div class="button-row ofs-author-actions" data-choice-layout="${options.length === 1 ? 'single' : (options.length <= 4 ? 'grid' : 'list')}" data-choice-count="${options.length}">
                ${options.map((opt, i) => `
                    <button data-opt-id="${escapeHTML(opt.id || i)}" class="choice-btn">
                        ${escapeHTML(opt.label || '')}
                    </button>
                `).join('')}
            </div>
            <div class="choice-result ofs-author-result" role="status"></div>
            <div class="operation-feedback-host"></div>
        </div>
    `;

    finishApplicationRenderWindow(app, hydrated);
    app.querySelector('.close-btn').addEventListener('click', () => {
        disposeOperationFeedbackWindow(app, "window_closed");
        app.remove();
    });

    const buttons = app.querySelectorAll('.choice-btn');
    const resultBox = app.querySelector('.choice-result');

    buttons.forEach(btn => {
        btn.addEventListener('click', async () => {
            if (btn.disabled || btn.classList.contains("is-loading")) return;
            const optId = btn.dataset.optId;
            const choiceLabel = btn.textContent.trim();
            appFlowTrace(app.dataset.appFlowId, "app_option_click", {
                app_id: id,
                interface: "button_choices",
                choice_id: optId,
                label: choiceLabel
            });
            setAppButtonGroupPending(buttons, btn, true);
            const stopWaitLog = startLegacyAppWaitUnlessFeedbackEnabled(app);
            try {
                const response = await sendGonnaWinRequest(id, optId, app);
                const success = response.success === true;
                btn.classList.add("is-selected");

                addSystemMessage('info', '\u2699 Efekt', `Wybrano: ${choiceLabel} | Wynik: ${success ? "\u2714 SUKCES" : "\u2716 PORA\u017bKA"}`);
                resultBox.textContent = success ? "\u2714 Uda\u0142o si\u0119!" : "\u2716 Niestety nie tym razem.";
                resultBox.style.color = success ? "#0f0" : "#f33";
                if (success) {
                    appFlowTrace(app.dataset.appFlowId, "app_option_success", {
                        app_id: id,
                        interface: "button_choices",
                        choice_id: optId
                    });
                    scheduleOperationalAppAutoClose(app);
                }
            } finally {
                stopWaitLog();
                buttons.forEach(button => { button.disabled = true; });
            }
        });
    });
}

function normalizeButtonChoiceOption(option, index = 0) {
    if (option === null || option === undefined) {
        return { id: index, label: `Opcja ${index + 1}`, action: "", effect: {} };
    }
    if (typeof option !== "object") {
        return {
            id: index,
            label: String(option),
            action: "",
            effect: {}
        };
    }
    const label = option.label ?? option.text ?? option.title ?? option.name ?? option.value ?? `Opcja ${index + 1}`;
    return {
        ...option,
        id: option.id ?? option.value ?? index,
        label,
        action: option.action ?? "",
        effect: option.effect || {}
    };
}

function createMap() {
    const existing = document.querySelector(`.terminal[data-app="map"]`);
    if (existing) {
        bringWindowToFront(existing);
        return;
    }
    const term = document.createElement('div');
    term.className = 'terminal map-window';
    term.dataset.app = "map";
    const layout = getInitialMapWindowLayout();
    term.style.top = `${layout.top}px`;
    term.style.left = `${layout.left}px`;
    term.style.width = `${layout.width}px`;
    term.style.height = `${layout.height}px`;

    term.innerHTML = `
        <div class="title-bar">
            Mapa
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div class="map-frame-host">
            <div class="map-window-loader" role="status" aria-live="polite">
                <div class="map-window-loader__title">Ladowanie mapy CHAOS...</div>
                <div class="map-window-loader__bar"><span></span></div>
                <div class="map-window-loader__text">Pobieranie snapshotu swiata...</div>
            </div>
            <iframe class="map-frame" title="Mapa CHAOS" width="100%" height="100%" style="border:none;"></iframe>
        </div>
    `;

    document.body.appendChild(term);
    const frame = term.querySelector('iframe');
    frame?.addEventListener('load', () => {
        term.classList.add('map-frame-loaded');
    }, { once: true });
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            if (frame && term.isConnected && !frame.src) {
                frame.src = `/map?scheme=${encodeURIComponent(desktopSettings.map_tile_scheme || "osm")}${currentSessionGenerationQuery()}`;
            }
        });
    });
    makeDraggable(term);
    term.querySelector('.close-btn')?.addEventListener('click', () => term.remove());
}

function createBrowser() {
    const term = document.createElement('div');
    term.className = 'terminal browser-window';
    term.dataset.app = "browser";
    term.dataset.appTitle = "WebDragons";
    term.style.display = 'flex';
    term.style.flexDirection = 'column';
    const defaultBrowserWidth = Math.min(1180, Math.max(920, window.innerWidth - 80));
    const defaultBrowserHeight = Math.min(760, Math.max(620, window.innerHeight - 92));
    const position = findAvailablePosition(defaultBrowserWidth, defaultBrowserHeight);
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `${defaultBrowserWidth}px`;
    term.style.height = `${defaultBrowserHeight}px`;

    const terminalId = `browser-${Date.now()}`;
    const browserUiIcons = {
        close: '\u2716',
        back: '\u2190',
        forward: '\u2192',
        favorite: '\u2B50',
        app: '\u25A3',
        maximize: '\u26F6',
        restore: '\u2750'
    };
    const googleplexSearchPresentation = window.GoogleplexSearchPresentation || null;

    term.innerHTML = `
    <div class="title-bar browser-title-bar">
        <span class="browser-window-title browser-window-drag-handle" data-window-drag-handle>WebDragons</span>
        <span class="browser-window-controls">
            <button type="button" class="browser-window-control browser-maximize-btn" aria-label="Powiększ WebDragons" title="Pełny ekran WebDragons" aria-pressed="false">${browserUiIcons.maximize}</button>
            <button type="button" class="close-btn browser-window-control" aria-label="Zamknij WebDragons" title="Zamknij">\u2716</button>
        </span>
    </div>
    <div class="browser-nav">
        <button class="nav-btn">${browserUiIcons.back}</button>
        <button class="nav-btn">${browserUiIcons.forward}</button>
        <input type="text" value="xhttp://webdragons.hck" readonly class="url-bar">
        <button class="fav-btn" title="Dodaj do ulubionych">${browserUiIcons.favorite}</button>
    </div>
    <div class="googolplex-shell">
        <div class="googolplex-header">
            <h1 id="${terminalId}-title"><span class="gp-brand-lockup"><img src="/static/images/googleplx/brand/googleplex-news-wordmark.svg" alt="Googleplex News"></span></h1>
            <div id="${terminalId}-wallet" class="googolplex-wallet gp-account-context"><span>HC</span><strong>...</strong></div>
        </div>
        <div class="browser-tabs">
            <button type="button" class="browser-tab is-active" data-browser-tab="googleplex">Googleplex</button>
            <button type="button" class="browser-tab" data-browser-tab="exchange">Ghost Exchange</button>
            <button type="button" class="browser-tab" data-browser-tab="blacknet">BlackNet</button>
        </div>
        <input type="text" id="${terminalId}-search" placeholder="Szukaj aplikacji...  /all - pokaz wszystkie" class="googolplex-search">
        <div id="${terminalId}-results" class="googolplex-grid">
            <div class="app-load-panel">
                <div class="app-load-panel__title">Ladowanie WebDragons...</div>
                <div class="app-load-panel__bar"><span></span></div>
                <div class="app-load-panel__text">Synchronizacja katalogu Googolplex...</div>
            </div>
        </div>
    </div>
    `;

    document.body.appendChild(term);
    const contentWrapper = term.querySelector('div[style*="display: flex"][style*="flex-direction: column"]');
    if (contentWrapper) {
        contentWrapper.style.minHeight = '0';
    }
    makeDraggable(term);

    const maximizeButton = term.querySelector('.browser-maximize-btn');
    let restoreGeometry = null;
    const setBrowserMaximized = (maximized) => {
        if (maximized === term.classList.contains('is-window-maximized')) return;
        if (maximized) {
            const rect = term.getBoundingClientRect();
            restoreGeometry = {
                top: term.style.top || `${rect.top}px`,
                left: term.style.left || `${rect.left}px`,
                width: term.style.width || `${rect.width}px`,
                height: term.style.height || `${rect.height}px`,
                resize: term.style.resize || ''
            };
            term.classList.add('is-window-maximized');
            term.style.top = '0';
            term.style.left = '0';
            term.style.width = '100vw';
            term.style.height = '100vh';
            term.style.resize = 'none';
        } else if (restoreGeometry) {
            term.classList.remove('is-window-maximized');
            term.style.top = restoreGeometry.top;
            term.style.left = restoreGeometry.left;
            term.style.width = restoreGeometry.width;
            term.style.height = restoreGeometry.height;
            term.style.resize = restoreGeometry.resize;
            restoreGeometry = null;
        }
        if (maximizeButton) {
            maximizeButton.textContent = maximized ? browserUiIcons.restore : browserUiIcons.maximize;
            maximizeButton.setAttribute('aria-pressed', maximized ? 'true' : 'false');
            maximizeButton.setAttribute('aria-label', maximized ? 'Przywróć okno WebDragons' : 'Powiększ WebDragons');
            maximizeButton.title = maximized ? 'Przywróć okno WebDragons' : 'Pełny ekran WebDragons';
        }
        bringWindowToFront(term);
    };
    maximizeButton?.addEventListener('click', () => {
        setBrowserMaximized(!term.classList.contains('is-window-maximized'));
    });
    term.querySelector('.browser-title-bar')?.addEventListener('dblclick', event => {
        if (event.target.closest('.browser-window-control')) return;
        setBrowserMaximized(!term.classList.contains('is-window-maximized'));
    });

    // Obsługa wyszukiwania
    const search = term.querySelector(`#${terminalId}-search`);
    const results = term.querySelector(`#${terminalId}-results`);
    const wallet = term.querySelector(`#${terminalId}-wallet`);
    const browserHeader = term.querySelector('.googolplex-header');
    const browserTabs = term.querySelector('.browser-tabs');
    const googleplexShell = term.querySelector('.googolplex-shell');
    let catalog = [];
    let catalogLoaded = false;
    let catalogLoading = null;
    const dedupeGoogleplexCatalog = payload => {
        const deduped = [];
        const positions = new Map();
        (Array.isArray(payload) ? payload : []).forEach(item => {
            if (!item || typeof item !== "object") return;
            const appId = String(item.id || item.app_id || "").trim();
            if (!appId) {
                deduped.push(item);
                return;
            }
            if (positions.has(appId)) {
                // Later code-owned entries override stale resource copies while
                // retaining one stable card position for the canonical app id.
                deduped[positions.get(appId)] = item;
                return;
            }
            positions.set(appId, deduped.length);
            deduped.push(item);
        });
        return deduped;
    };
    let googleplexHomeSnapshot = null;
    let googleplexHomeLoading = null;
    let googleplexHomeError = "";
    let googleplexHomeScrollTop = 0;
    let googleplexRenderedViewKey = "boot";
    let exchangeFiles = [];
    let exchangeDashboard = { summary: {}, sectors: [], recent_transactions: [], history_7d: [] };
    let walletBalance = Number((toolbarProfile || {}).hackcoins || 0);
    let activeBrowserTab = "googleplex";
    const browserQueries = {
        googleplex: "",
        exchange: "",
        blacknet: ""
    };
    let activeBlacknetSignalId = "";
    let blacknetPointerStartX = null;
    let pendingGoogleplexSearch = "";
    const getGoogleplexScrollSurface = () => {
        const resultsOverflow = String(window.getComputedStyle?.(results)?.overflowY || "").toLowerCase();
        if (resultsOverflow === "auto" || resultsOverflow === "scroll") return results;
        const shellOverflow = String(window.getComputedStyle?.(googleplexShell)?.overflowY || "").toLowerCase();
        if (shellOverflow === "auto" || shellOverflow === "scroll") return googleplexShell;
        return results;
    };
    const beginGoogleplexCatalogView = viewKey => {
        const previousSurface = getGoogleplexScrollSurface();
        const previousTop = Number(previousSurface?.scrollTop || 0);
        const previousLeft = Number(previousSurface?.scrollLeft || 0);
        const viewChanged = googleplexRenderedViewKey !== viewKey;
        googleplexRenderedViewKey = viewKey;
        if (viewChanged && previousSurface) {
            previousSurface.scrollTop = 0;
            previousSurface.scrollLeft = 0;
        }
        return () => requestAnimationFrame(() => {
            const surface = getGoogleplexScrollSurface();
            if (!surface) return;
            surface.scrollTop = viewChanged ? 0 : previousTop;
            surface.scrollLeft = viewChanged ? 0 : previousLeft;
        });
    };
    const rememberGoogleplexHomeScroll = () => {
        if (!results.querySelector('.gp-home')) return;
        googleplexHomeScrollTop = Math.max(0, Number(getGoogleplexScrollSurface()?.scrollTop || 0));
    };
    const renderBrowserWallet = () => {
        if (activeBrowserTab === "blacknet") {
            wallet.classList.remove("gp-account-context");
            wallet.textContent = "SIGNAL BUS v0";
            return;
        }
        if (activeBrowserTab === "googleplex") {
            const profile = toolbarProfile || {};
            const nick = String(profile.nick || profile.username || "OPERATOR").trim();
            const rank = String(profile.rank || profile.level || profile.app_level || "ACTIVE").trim();
            wallet.classList.add("gp-account-context");
            wallet.innerHTML = `<span>HC</span><strong>${escapeHTML(Number.isFinite(walletBalance) ? walletBalance : "...")}</strong><span class="gp-account-rank">${escapeHTML(nick)}</span><strong class="gp-account-rank">${escapeHTML(rank)}</strong>`;
            return;
        }
        wallet.classList.remove("gp-account-context");
        wallet.textContent = `HackCoiny: ${Number.isFinite(walletBalance) ? walletBalance : "..."}`;
    };

    const updateBrowserChrome = () => {
        term.classList.toggle('is-browser-googleplex', activeBrowserTab === "googleplex");
        term.classList.toggle('is-browser-exchange', activeBrowserTab === "exchange");
        term.classList.toggle('is-browser-blacknet', activeBrowserTab === "blacknet");
        if (browserHeader) {
            browserHeader.hidden = activeBrowserTab === "blacknet";
        }
        if (browserTabs) {
            browserTabs.hidden = activeBrowserTab === "blacknet";
        }
        search.hidden = activeBrowserTab !== "googleplex";
    };

    const updateBrowserNarrowMode = () => {
        const measuredWidth = term.getBoundingClientRect().width
            || term.offsetWidth
            || window.innerWidth;
        const currentlyNarrow = term.classList.contains('browser-narrow');
        const shouldBeNarrow = currentlyNarrow
            ? measuredWidth < 748
            : measuredWidth < 700;
        if (shouldBeNarrow !== currentlyNarrow) {
            term.classList.toggle('browser-narrow', shouldBeNarrow);
        }
    };

    updateBrowserNarrowMode();
    let browserNarrowObserver = null;
    let appsProjectionListener = null;
    if (window.ResizeObserver) {
        browserNarrowObserver = new ResizeObserver(updateBrowserNarrowMode);
        browserNarrowObserver.observe(term);
    }
    window.addEventListener('resize', updateBrowserNarrowMode);

    const closeBrowser = () => {
        browserNarrowObserver?.disconnect();
        window.removeEventListener('resize', updateBrowserNarrowMode);
        if (appsProjectionListener) {
            window.removeEventListener('chaos:apps-projection-updated', appsProjectionListener);
        }
        term.remove();
    };
    const closeButton = term.querySelector('.close-btn');
    closeButton?.addEventListener('click', closeBrowser);
    closeButton?.addEventListener('keydown', event => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        closeBrowser();
    });

    const googleplexList = (value) => Array.isArray(value)
        ? value.map(item => String(item || '').trim()).filter(Boolean)
        : [];
    const googleplexBreakableText = value => escapeHTML(
        value == null || value === "" ? "-" : String(value)
    ).replace(/([_,])/g, "$1<wbr>");
    const googleplexIconSocketAssets = Object.freeze({
        core: "/static/images/googleplx/icons/app-sockets/01_icon_socket_core.svg",
        side: "/static/images/googleplx/icons/app-sockets/02_icon_socket_side.svg",
        compact: "/static/images/googleplx/icons/app-sockets/03_icon_socket_compact.svg",
        hex: "/static/images/googleplx/icons/app-sockets/04_icon_socket_hex.svg",
        target: "/static/images/googleplx/icons/app-sockets/05_icon_socket_target.svg"
    });
    const googleplexSearchText = (item) => [
        item.name,
        item.description,
        item.type,
        item.category,
        item.app_level,
        item.product_type,
        item.travel_city,
        ...googleplexList(item.effects).map(effect => `${effect?.type || ''} ${effect?.value || effect?.city || ''}`),
        ...googleplexList(item.map_actions),
        ...googleplexList(item.operation_types),
        ...googleplexList(item.resource_types),
        ...googleplexList(item.target_types)
    ].join(' ').toLowerCase();

    const BLACKNET_SIGNAL_SOURCE = "/static/blacknet_signals.json";
    const BLACKNET_WORLD_SIGNAL_SOURCE = "/api/blacknet/world-signals";
    const BLACKNET_SIGNAL_BATCH_LIMIT = 8;
    const BLACKNET_SIGNAL_REFILL_THRESHOLD = 2;
    let blacknetSignals = [];
    let blacknetSignalsLoaded = false;
    let blacknetSignalsLoading = null;
    let blacknetSignalsError = "";
    let blacknetSignalFeedExhausted = false;

    const blacknetCapturedSignals = new Set();
    let activeBlacknetDirection = "right";

    const blacknetIsOutOfSignal = signal => {
        return String(signal?.signal_type || "") === "out_of_signal"
            || signal?.metadata?.out_of_signal === true;
    };

    const blacknetSignalIdentityKeys = signal => {
        if (!signal || typeof signal !== "object") return [];
        return [
            signal.id,
            signal.fact_id,
            signal.entity_id,
            signal.cta_target_id
        ].map(value => String(value || "").trim()).filter(Boolean);
    };

    const blacknetExcludedSignalKeys = () => {
        const keys = new Set(Array.from(blacknetCapturedSignals).map(value => String(value || "").trim()).filter(Boolean));
        blacknetSignals.forEach(signal => {
            blacknetSignalIdentityKeys(signal).forEach(key => keys.add(key));
        });
        return Array.from(keys);
    };

    const blacknetWorldSignalUrl = (append = false) => {
        const params = new URLSearchParams();
        params.set("limit", String(BLACKNET_SIGNAL_BATCH_LIMIT));
        if (append) {
            const excluded = blacknetExcludedSignalKeys();
            if (excluded.length) {
                params.set("exclude", excluded.join(","));
            }
        }
        return `${BLACKNET_WORLD_SIGNAL_SOURCE}?${params.toString()}`;
    };

    const isBlacknetStaticFallbackEnabled = () => {
        try {
            const params = new URLSearchParams(window.location.search || "");
            if (params.get("blacknet_demo") === "1" || params.get("blacknet_static") === "1") return true;
            if (window.BLACKNET_STATIC_SIGNAL_FIXTURE === true) return true;
            return window.localStorage?.getItem("blacknet_static_signals") === "1";
        } catch (error) {
            return false;
        }
    };

    const blacknetClientOutOfSignal = (reason = "world_signal_unavailable") => ({
        id: `client-out-of-signal-${reason}`,
        source: "world_generated",
        signal_type: "out_of_signal",
        channel: "BLACKNET SIGNAL BUS",
        title: "OUT OF SIGNAL",
        label: "BRAK RUCHU",
        value: "0",
        stat: "OCZEKIWANIE NA RUCH SWIATA",
        timer: "00:00",
        cta: "SYGNAL WYCISZONY",
        cta_action: "none",
        cta_target: "",
        cta_target_id: "",
        entity_id: "out_of_signal",
        category: "out_of_signal",
        tone: "lime",
        layout: 1,
        metadata: {
            out_of_signal: true,
            reason
        },
        radar: {
            sides: 1,
            nodes: []
        }
    });

    const normalizeBlacknetSignal = (signal, index) => {
        if (!signal || typeof signal !== "object") return null;
        const id = String(signal.id || `signal-${index + 1}`).trim();
        if (!id) return null;
        const radar = signal.radar && typeof signal.radar === "object" ? signal.radar : {};
        const rawNodes = Array.isArray(radar.nodes) ? radar.nodes : (Array.isArray(signal.nodes) ? signal.nodes : []);
        const nodes = rawNodes
            .map(node => Array.isArray(node) ? node.map(Number).slice(0, 3) : null)
            .filter(node => node && node.length >= 2 && node.every(value => Number.isFinite(value)));
        return {
            id,
            source: String(signal.source || "unknown").trim() || "unknown",
            signal_type: String(signal.signal_type || signal.type || "").trim(),
            fact_id: String(signal.fact_id || "").trim(),
            world_version: String(signal.world_version || "").trim(),
            entity_id: String(signal.entity_id || signal.cta_target_id || signal.target_id || signal.product_id || "").trim(),
            channel: String(signal.channel || "BLACKNET SIGNAL").trim() || "BLACKNET SIGNAL",
            title: String(signal.title || "NIEZNANY SYGNAL").trim() || "NIEZNANY SYGNAL",
            label: String(signal.label || "STATUS").trim() || "STATUS",
            value: String(signal.value || "-").trim() || "-",
            stat: String(signal.stat || "BRAK DANYCH").trim() || "BRAK DANYCH",
            timer: String(signal.timer || "--:--").trim() || "--:--",
            cta: String(signal.cta || "BRAK MOSTU").trim() || "BRAK MOSTU",
            cta_action: String(signal.cta_action || "").trim(),
            cta_target: String(signal.cta_target || "").trim(),
            cta_target_id: String(signal.cta_target_id || signal.target_id || signal.product_id || signal.operation_id || "").trim(),
            cta_query: String(signal.cta_query || signal.query || signal.search || "").trim(),
            target_id: String(signal.target_id || "").trim(),
            region_id: String(signal.region_id || "").trim(),
            category: String(signal.category || "").trim(),
            product_id: String(signal.product_id || "").trim(),
            podcast: String(signal.podcast || signal.podcast_id || "").trim(),
            operation_id: String(signal.operation_id || "").trim(),
            thread_peer: String(signal.thread_peer || signal.peer || "").trim(),
            valid_until: String(signal.valid_until || signal.expires_at || "").trim(),
            metadata: signal.metadata && typeof signal.metadata === "object" ? signal.metadata : {},
            tone: ["lime", "cyan", "amber", "red"].includes(String(signal.tone || "").trim())
                ? String(signal.tone).trim()
                : "lime",
            layout: Math.max(1, Math.min(6, Number(signal.layout || 1))),
            radarSides: Math.max(0, Math.min(12, Number(radar.sides ?? signal.radarSides ?? 0))),
            nodes
        };
    };

    const loadBlacknetSignals = async (options = {}) => {
        const append = options.append === true;
        const force = options.force === true;
        if (blacknetSignalsLoaded && !append && !force) return blacknetSignals;
        if (blacknetSignalsLoading) return blacknetSignalsLoading;
        blacknetSignalsError = "";
        const allowStaticFallback = !append && isBlacknetStaticFallbackEnabled();
        const worldRequest = fetch(blacknetWorldSignalUrl(append || force), { cache: "no-cache" }).then(async response => {
            if (!response.ok) throw new Error(`world HTTP ${response.status}`);
            return response.json();
        });
        const localRequest = allowStaticFallback
            ? fetch(BLACKNET_SIGNAL_SOURCE, { cache: "no-cache" }).then(async response => {
                if (!response.ok) throw new Error(`local HTTP ${response.status}`);
                return response.json();
            })
            : Promise.resolve(null);
        blacknetSignalsLoading = Promise.allSettled([worldRequest, localRequest])
            .then(results => {
                const worldPayload = results[0].status === "fulfilled" ? results[0].value : null;
                const localPayload = results[1].status === "fulfilled" ? results[1].value : null;
                if (results[0].status === "rejected") {
                    console.warn("BlackNet world signal source failed", results[0].reason);
                }
                if (allowStaticFallback && results[1].status === "rejected") {
                    console.warn("BlackNet local signal source failed", results[1].reason);
                }
                const localSignals = Array.isArray(localPayload)
                    ? localPayload
                    : (Array.isArray(localPayload?.signals) ? localPayload.signals : []);
                const worldSignals = Array.isArray(worldPayload?.snapshot?.signals)
                    ? worldPayload.snapshot.signals
                    : (Array.isArray(worldPayload?.signals) ? worldPayload.signals : []);
                const worldOutOfSignal = worldSignals.some(signal => String(signal?.signal_type || "") === "out_of_signal");
                blacknetSignalFeedExhausted = worldOutOfSignal;
                let mergedSignals = append ? [...blacknetSignals, ...worldSignals] : worldSignals;
                if (!mergedSignals.length) {
                    mergedSignals = allowStaticFallback && localSignals.length
                        ? localSignals
                        : [blacknetClientOutOfSignal(results[0].status === "rejected" ? "world_signal_fetch_failed" : "empty_world_signal_feed")];
                } else if (allowStaticFallback && !worldOutOfSignal) {
                    mergedSignals = [...worldSignals, ...localSignals];
                }
                const dedupedSignals = [];
                const seenIds = new Set();
                mergedSignals.forEach((signal, index) => {
                    const normalized = normalizeBlacknetSignal(signal, index);
                    if (!normalized || seenIds.has(normalized.id)) return;
                    if (append && blacknetCapturedSignals.has(normalized.id) && !blacknetIsOutOfSignal(normalized)) return;
                    seenIds.add(normalized.id);
                    dedupedSignals.push(normalized);
                });
                blacknetSignals = dedupedSignals.length
                    ? dedupedSignals
                    : [normalizeBlacknetSignal(blacknetClientOutOfSignal("no_valid_signal_payload"), 0)].filter(Boolean);
                blacknetSignalsLoaded = true;
                const visibleSignals = blacknetVisibleSignals();
                if (!visibleSignals.some(signal => signal.id === activeBlacknetSignalId)) {
                    activeBlacknetSignalId = visibleSignals[0]?.id || blacknetSignals[0]?.id || "";
                }
                return blacknetSignals;
            })
            .catch(error => {
                console.warn("BlackNet signal source failed", error);
                blacknetSignalsError = "World signal feed jest chwilowo niedostepny.";
                blacknetSignals = [normalizeBlacknetSignal(blacknetClientOutOfSignal("world_signal_loader_error"), 0)].filter(Boolean);
                blacknetSignalsLoaded = true;
                return blacknetSignals;
            })
            .finally(() => {
                blacknetSignalsLoading = null;
                if (activeBrowserTab === "blacknet") {
                    renderBlackNet();
                }
            });
        return blacknetSignalsLoading;
    };

    const blacknetVisibleSignals = () => {
        const visible = [];
        const outOfSignals = [];
        blacknetSignals.forEach(signal => {
            if (!signal) return;
            if (blacknetIsOutOfSignal(signal)) {
                outOfSignals.push(signal);
                return;
            }
            if (blacknetCapturedSignals.has(signal.id) || blacknetSignalExpired(signal)) {
                blacknetSignalIdentityKeys(signal).forEach(key => blacknetCapturedSignals.add(key));
                return;
            }
            visible.push(signal);
        });
        return visible.length ? visible : outOfSignals;
    };

    window.expireBlacknetIncidentSignals = event => {
        const payload = event?.payload || {};
        const type = String(event?.type || payload.type || "");
        const incidentId = String(event?.entity_id || payload.incident_id || payload.id || "").trim();
        if (!incidentId) return false;

        if (type === "incident.resolved" || payload.removed || payload.status === "resolved") {
            let removedActive = false;
            const remaining = [];
            blacknetSignals.forEach(signal => {
                const metadata = signal?.metadata || {};
                const matches = String(signal?.signal_type || "") === "incident_hotspot"
                    && [
                        signal.id,
                        signal.fact_id,
                        signal.entity_id,
                        signal.cta_target_id,
                        metadata.incident_id,
                        metadata.hotspot_id,
                        metadata.cta_target_id
                    ].map(value => String(value || "").trim()).includes(incidentId);
                if (matches) {
                    blacknetSignalIdentityKeys(signal).forEach(key => blacknetCapturedSignals.add(key));
                    removedActive = removedActive || signal.id === activeBlacknetSignalId;
                    return;
                }
                remaining.push(signal);
            });
            if (remaining.length !== blacknetSignals.length) {
                blacknetSignals = remaining.length ? remaining : [normalizeBlacknetSignal(blacknetClientOutOfSignal("incident_resolved"), 0)].filter(Boolean);
                if (removedActive || !blacknetSignals.some(signal => signal.id === activeBlacknetSignalId)) {
                    activeBlacknetSignalId = blacknetVisibleSignals()[0]?.id || "";
                }
                if (activeBrowserTab === "blacknet") renderBlackNet();
                return true;
            }
            return false;
        }

        if (type === "incident.created" || type === "incident.updated") {
            blacknetSignalsLoaded = false;
            blacknetSignalFeedExhausted = false;
            if (activeBrowserTab === "blacknet") {
                loadBlacknetSignals({ force: true });
            }
            return true;
        }
        return false;
    };

    const maybeRefillBlacknetSignals = visibleSignals => {
        if (!blacknetSignalsLoaded || blacknetSignalsLoading) return;
        if (blacknetSignalFeedExhausted) return;
        if (visibleSignals.some(blacknetIsOutOfSignal)) return;
        const activeSignals = visibleSignals.filter(signal => !blacknetIsOutOfSignal(signal));
        if (activeSignals.length > BLACKNET_SIGNAL_REFILL_THRESHOLD) return;
        loadBlacknetSignals({ append: true, force: true });
    };

    const stepBlacknetSignal = (delta, direction = "right") => {
        const visibleSignals = blacknetVisibleSignals();
        if (!visibleSignals.length) return;
        const currentIndex = Math.max(0, visibleSignals.findIndex(signal => signal.id === activeBlacknetSignalId));
        const nextIndex = (currentIndex + delta + visibleSignals.length) % visibleSignals.length;
        activeBlacknetDirection = direction;
        activeBlacknetSignalId = visibleSignals[nextIndex].id;
        renderBlackNet();
    };

    const blacknetPolygonPoints = (sides, radius, rotation = -90) => {
        return Array.from({ length: sides }, (_, index) => {
            const angle = ((rotation + index * 360 / sides) * Math.PI) / 180;
            return `${(50 + Math.cos(angle) * radius).toFixed(2)},${(50 + Math.sin(angle) * radius).toFixed(2)}`;
        }).join(" ");
    };

    const blacknetRadarSvg = signal => {
        const nodes = Array.isArray(signal.nodes) ? signal.nodes : [];
        const sides = Number(signal.radarSides || 0);
        const rotation = sides === 4 ? -45 : -90;
        const frame = radius => sides
            ? `<polygon points="${blacknetPolygonPoints(sides, radius, rotation)}"></polygon>`
            : `<circle cx="50" cy="50" r="${radius}"></circle>`;
        const grid = [12, 23, 34, 45].map(radius => frame(radius)).join("");
        const spokes = Array.from({ length: 12 }, (_, index) => index * 30)
            .map(angle => `<line x1="50" y1="50" x2="50" y2="4" transform="rotate(${angle} 50 50)"></line>`)
            .join("");
        const links = nodes.slice(1).map((node, index) => {
            const prev = nodes[index] || node;
            return `<line x1="${prev[0]}" y1="${prev[1]}" x2="${node[0]}" y2="${node[1]}"></line>`;
        }).join("");
        const satellites = nodes.flatMap(([x, y], index) => [
            [Math.max(8, x - 7 + (index % 3) * 2), Math.min(92, y + 8), 0.45],
            [Math.min(92, x + 6), Math.max(8, y - 5 + (index % 2) * 3), 0.3]
        ]);
        const nodeMarkup = nodes.map(([x, y, r], index) => `
            <g class="bn-radar-node" style="animation-delay:${index * 170}ms">
                <circle class="bn-pulse-ring bn-pulse-ring-a" cx="${x}" cy="${y}" r="${r * 1.45}"></circle>
                <circle class="bn-pulse-ring bn-pulse-ring-b" cx="${x}" cy="${y}" r="${r * 2.25}"></circle>
                <circle cx="${x}" cy="${y}" r="${r / 1.9}"></circle>
                ${index % 2 === 0 ? `<path d="M${x - 2.5} ${y - 4} h5 v5 l-2.5 3 -2.5-3z"></path>` : ""}
            </g>
        `).join("");
        const satelliteMarkup = satellites.map(([x, y, r], index) => `
            <circle cx="${x}" cy="${y}" r="${r}" style="animation-delay:${(index % 6) * 130}ms"></circle>
        `).join("");
        return `
            <svg class="bn-radar" viewBox="0 0 100 100" role="img" aria-label="Radar BlackNet ${escapeHTML(signal.title || '')}">
                <g class="bn-radar-grid">
                    ${grid}
                    ${spokes}
                    <path d="M1 42 C20 30 29 55 42 37 S66 24 99 45 M3 66 C27 79 36 58 52 70 S72 80 97 62 M10 18 L31 31 L42 19 L57 35 L90 12"></path>
                </g>
                <g class="bn-radar-frame">${frame(46)}</g>
                <g class="bn-radar-accent">${frame(39)}</g>
                <g class="bn-radar-links">${links}</g>
                ${nodeMarkup}
                <g class="bn-radar-satellites">${satelliteMarkup}</g>
                <g class="bn-radar-core"><circle cx="50" cy="50" r="8"></circle><circle cx="50" cy="50" r="4.5"></circle><circle cx="50" cy="50" r="1.3"></circle></g>
                <path class="bn-radar-sweep" d="M50 50 L50 0 L92 4 Z"></path>
            </svg>
        `;
    };

    const blacknetCtaDiagnostic = (signal, stage, data = {}) => {
        if (!window.BLACKNET_CTA_DEBUG) return;
        try {
            console.info("[BLACKNET_CTA]", {
                stage,
                signal_id: signal?.id || "",
                source: signal?.source || "",
                cta_action: signal?.cta_action || "",
                cta_target: signal?.cta_target || "",
                cta_target_id: signal?.cta_target_id || "",
                ...data
            });
        } catch (error) {
            // Diagnostics must never block the CTA bridge.
        }
    };

    const blacknetCtaResult = (ok, message = "", extra = {}) => ({ ok: Boolean(ok), message, ...extra });

    const blacknetDecisionDialog = ({
        title = "BLACKNET",
        message = "",
        details = "",
        confirmLabel = "OK",
        cancelLabel = "ANULUJ",
        tone = "lime"
    } = {}) => new Promise(resolve => {
        const existing = document.querySelector(".blacknet-decision-backdrop");
        if (existing) {
            existing.remove();
        }

        const backdrop = document.createElement("div");
        backdrop.className = `blacknet-decision-backdrop tone-${String(tone || "lime").toLowerCase()}`;
        backdrop.innerHTML = `
            <section class="blacknet-decision" role="dialog" aria-modal="true" aria-labelledby="blacknet-decision-title">
                <div class="blacknet-decision__scanline"></div>
                <header class="blacknet-decision__header">
                    <span class="blacknet-decision__badge">GHOST SYSTEM</span>
                    <h2 id="blacknet-decision-title">${escapeHTML(title)}</h2>
                </header>
                <div class="blacknet-decision__body">
                    <p>${escapeHTML(message)}</p>
                    ${details ? `<p class="blacknet-decision__details">${escapeHTML(details)}</p>` : ""}
                </div>
                <footer class="blacknet-decision__actions">
                    <button type="button" class="blacknet-decision__button is-cancel" data-choice="cancel">${escapeHTML(cancelLabel)}</button>
                    <button type="button" class="blacknet-decision__button is-confirm" data-choice="confirm">${escapeHTML(confirmLabel)}</button>
                </footer>
            </section>
        `;

        let settled = false;
        const finish = accepted => {
            if (settled) return;
            settled = true;
            document.removeEventListener("keydown", handleKeydown, true);
            backdrop.remove();
            resolve(Boolean(accepted));
        };
        const handleKeydown = event => {
            if (event.key === "Escape") {
                event.preventDefault();
                finish(false);
            }
            if (event.key === "Enter") {
                event.preventDefault();
                finish(true);
            }
        };

        backdrop.addEventListener("click", event => {
            const button = event.target.closest("[data-choice]");
            if (!button) {
                if (event.target === backdrop) finish(false);
                return;
            }
            finish(button.dataset.choice === "confirm");
        });
        document.addEventListener("keydown", handleKeydown, true);
        document.body.appendChild(backdrop);
        const confirmButton = backdrop.querySelector(".blacknet-decision__button.is-confirm");
        if (confirmButton) {
            requestAnimationFrame(() => confirmButton.focus());
        }
    });

    window.blacknetDecisionDialog = blacknetDecisionDialog;

    const blacknetSignalExpired = signal => {
        const expiresAt = String(signal?.valid_until || signal?.metadata?.expires_at || "").trim();
        if (!expiresAt) return false;
        const expiresMs = Date.parse(expiresAt);
        return Number.isFinite(expiresMs) && expiresMs <= Date.now();
    };

    const blacknetCtaQuery = signal => {
        return String(
            signal?.cta_query
            || signal?.metadata?.cta_query
            || signal?.metadata?.product_name
            || signal?.metadata?.product_id
            || signal?.product_id
            || signal?.cta_target_id
            || signal?.metadata?.query
            || ""
        ).trim();
    };

    const blacknetOpenGoogleplex = signal => {
        const query = blacknetCtaQuery(signal);
        pendingGoogleplexSearch = query;
        browserQueries.googleplex = query;
        switchBrowserTab("googleplex");
        if (query) {
            search.value = query;
            renderCatalog();
        }
        addSystemMessage("info", "BlackNet", query
            ? `Googolplex filtruje sygnal: ${escapeHTML(query)}.`
            : "Googolplex otwarty przez most BlackNet.");
        return blacknetCtaResult(true);
    };

    const blacknetOpenExchange = signal => {
        const action = String(signal?.cta_action || "").trim();
        const sector = String(
            signal?.metadata?.sector_key
            || signal?.metadata?.sector_id
            || signal?.metadata?.market_category
            || signal?.metadata?.cta_query
            || signal?.cta_target_id
            || ""
        ).trim();
        if (action === "open_exchange_category" && sector && sector !== "market") {
            browserQueries.exchange = sector;
        } else {
            browserQueries.exchange = "";
        }
        switchBrowserTab("exchange");
        addSystemMessage("info", "BlackNet", sector
            ? `Ghost Exchange otwarty dla sygnalu sektora: ${escapeHTML(sector)}.`
            : "Ghost Exchange otwarty przez most BlackNet.");
        return blacknetCtaResult(true);
    };

    const readBlacknetCoordinate = (...values) => {
        for (const value of values) {
            if (value === null || value === undefined || value === "") continue;
            const number = Number(value);
            if (Number.isFinite(number)) return number;
        }
        return NaN;
    };

    const blacknetOpenMap = (signal, mode = "open") => {
        const opened = openSystemAppFromTerminal("map");
        const metadata = signal?.metadata || {};
        const lat = readBlacknetCoordinate(metadata.lat, metadata.latitude, signal?.lat);
        const lng = readBlacknetCoordinate(metadata.lng, metadata.lon, metadata.longitude, signal?.lng, signal?.lon);
        const hasCoordinates = Number.isFinite(lat) && Number.isFinite(lng);
        const canUseEntityFocus = mode !== "open" || hasCoordinates;
        const rawTarget = String(
            metadata.target_id
            || signal?.target_id
            || metadata.cta_target_id
            || signal?.cta_target_id
            || (canUseEntityFocus ? signal?.entity_id : "")
            || ""
        ).trim();
        const rawRegion = String(metadata.region_id || signal?.region_id || "").trim();
        const genericFocusValues = new Set(["", "global", "world", "map", "open_map", "show_on_map"]);
        const focus = !genericFocusValues.has(rawTarget)
            ? rawTarget
            : (!genericFocusValues.has(rawRegion) ? rawRegion : "");
        if (focus || hasCoordinates) {
            window.__blacknetMapFocus = {
                mode,
                signal_id: signal?.id || "",
                target_id: focus || signal?.target_id || signal?.cta_target_id || "",
                entity_id: signal?.entity_id || "",
                region_id: rawRegion || "",
                lat: hasCoordinates ? lat : null,
                lng: hasCoordinates ? lng : null,
                label: metadata.target_label || signal?.title || ""
            };
            setTimeout(() => notifyOpenMapsBlacknetFocus(window.__blacknetMapFocus), 50);
            addSystemMessage("info", "BlackNet", `Mapa otwarta. Fokus sygnalu: ${escapeHTML(focus || metadata.coordinates || signal?.title || "koordynaty")}.`);
        } else {
            addSystemMessage("info", "BlackNet", "Mapa otwarta. Ten sygnal nie ma punktu do ustawienia fokusu.");
        }
        return blacknetCtaResult(opened);
    };

    const blacknetOpenCybernerThread = signal => {
        const opened = openSystemAppFromTerminal("cyberner");
        const metadata = signal?.metadata || {};
        const scope = String(metadata.thread_scope || signal?.thread_scope || "").trim();
        const channel = String(metadata.thread_channel || signal?.thread_channel || "").trim();
        const peer = String(signal?.thread_peer || metadata.thread_peer || signal?.cta_target || "").trim();
        const isWorld = channel === "world" || peer === "global" || signal?.cta_target === "world";
        if (isWorld && typeof window.openCybernerThread === "function") {
            setTimeout(() => window.openCybernerThread({
                scope: "group",
                peer: "global",
                channel: "world",
                source: "world",
                title: "WORLD",
                subtitle: "Publiczny kanal swiata gry"
            }), 0);
            return blacknetCtaResult(true);
        }
        if (scope && typeof window.openCybernerThread === "function") {
            setTimeout(() => window.openCybernerThread({
                scope,
                peer,
                channel,
                source: metadata.source || channel || "unknown",
                title: metadata.thread_title || signal?.title || peer || channel || "Cyberner",
                subtitle: metadata.thread_subtitle || ""
            }), 0);
            return blacknetCtaResult(true);
        }
        if (peer && typeof window.openEmailChatWith === "function") {
            setTimeout(() => window.openEmailChatWith(peer), 0);
            return blacknetCtaResult(true);
        }
        if (peer) {
            return blacknetCtaResult(false, `Cyberner nie znalazl aktywnego threadu: ${escapeHTML(peer)}.`);
        }
        return blacknetCtaResult(opened);
    };

    const blacknetOpenRadio = async signal => {
        const opened = openSystemAppFromTerminal("radio");
        const radio = window.GhostRadio;
        let channelId = String(
            signal?.metadata?.channel_id
            || signal?.metadata?.channel_path_id
            || signal?.metadata?.channel_meta_id
            || signal?.metadata?.cta_target_id
            || signal?.cta_target_id
            || ""
        ).trim();
        if (channelId.toLowerCase() === "radio") {
            channelId = "";
        }
        if (radio && channelId && typeof radio.loadChannel === "function") {
            try {
                const options = {
                    trackFile: signal?.metadata?.track_file || signal?.track_file || "",
                    trackIndex: signal?.metadata?.track_index || signal?.track_index || null
                };
                if (typeof radio.playTrack === "function" && (options.trackFile || options.trackIndex)) {
                    await radio.playTrack(channelId, options);
                } else {
                    await radio.init();
                    await radio.loadChannel(channelId, options);
                    await radio.play();
                }
                return blacknetCtaResult(true);
            } catch (error) {
                console.warn("BlackNet radio bridge failed", error);
                return blacknetCtaResult(false, "Radio nie moglo zaladowac wskazanego kanalu BlackNet.");
            }
        }
        return blacknetCtaResult(opened);
    };

    const blacknetTeleportToHotspot = async signal => {
        const metadata = signal?.metadata || {};
        const hotspotId = String(
            metadata.hotspot_id
            || signal?.cta_target_id
            || ""
        ).trim();
        const lat = Number(metadata.lat ?? metadata.latitude ?? signal?.lat);
        const lng = Number(metadata.lng ?? metadata.lon ?? metadata.longitude ?? signal?.lng ?? signal?.lon);
        const label = String(metadata.target_label || metadata.label || signal?.title || hotspotId || "target").trim();
        if (!hotspotId && (!Number.isFinite(lat) || !Number.isFinite(lng))) {
            return blacknetCtaResult(false, "Sygnal BlackNet nie zawiera konkretnego celu teleportu.");
        }
        const accepted = await blacknetDecisionDialog({
            title: "BLACKNET TELEPORT",
            message: `Przechwycono cel: ${label}.`,
            details: "Potwierdz wykonanie teleportu. Anulowanie zostawi operatora w obecnej pozycji.",
            confirmLabel: "WYKONAJ",
            cancelLabel: "ANULUJ",
            tone: signal?.tone || "lime"
        });
        if (!accepted) {
            return blacknetCtaResult(false, "Teleport BlackNet anulowany.", { cancelled: true });
        }
        try {
            const response = await fetch("/api/blacknet/cta/teleport", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    hotspot_id: hotspotId,
                    lat: Number.isFinite(lat) ? lat : null,
                    lng: Number.isFinite(lng) ? lng : null,
                    label,
                    signal_id: signal?.id || ""
                })
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
                return blacknetCtaResult(false, data?.message || "Teleport BlackNet nie zostal wykonany.");
            }
            openSystemAppFromTerminal("map");
            window.__blacknetMapFocus = {
                mode: "teleport",
                signal_id: signal?.id || "",
                target_id: signal?.target_id || signal?.cta_target_id || "",
                entity_id: signal?.entity_id || "",
                lat: Number(data?.curently_possition?.lat ?? lat),
                lng: Number(data?.curently_possition?.lng ?? lng),
                position_version: data?.position_version,
                position_updated_at: data?.position_updated_at,
                label
            };
            setTimeout(() => notifyOpenMapsBlacknetFocus(window.__blacknetMapFocus), 50);
            if (typeof refreshToolbarProfile === "function") {
                refreshToolbarProfile();
            }
            addSystemMessage("success", "BlackNet", data?.message || `Teleport BlackNet wykonany: ${escapeHTML(label)}.`);
            return blacknetCtaResult(true, "", {
                confirmed: true,
                hotspot_id: hotspotId,
                position: data?.curently_possition || null
            });
        } catch (error) {
            console.warn("BlackNet teleport bridge failed", error);
            return blacknetCtaResult(false, "Most teleportu BlackNet jest chwilowo niedostepny.");
        }
    };

    const blacknetPlayPodcast = async signal => {
        const channelId = String(
            signal?.metadata?.channel_id
            || signal?.metadata?.channel_path_id
            || signal?.metadata?.channel_meta_id
            || signal?.cta_target_id
            || ""
        ).trim();
        const trackFile = String(signal?.metadata?.track_file || signal?.podcast || signal?.metadata?.podcast || "").trim();
        if (!channelId && !trackFile) {
            return blacknetOpenRadio(signal);
        }
        if (window.GhostRadio && typeof window.GhostRadio.playTrack === "function") {
            try {
                openSystemAppFromTerminal("radio");
                await window.GhostRadio.playTrack(channelId, {
                    trackFile,
                    trackIndex: signal?.metadata?.track_index || null
                });
                return blacknetCtaResult(true);
            } catch (error) {
                console.warn("BlackNet podcast bridge failed", error);
                return blacknetCtaResult(false, "Radio nie moglo zaladowac wskazanego tracku BlackNet.");
            }
        }
        openSystemAppFromTerminal("radio");
        return blacknetCtaResult(false, "Radio wymaga istniejacego mostu GhostRadio.playTrack().");
    };

    const blacknetConfirmControlled = async (signal, prompt, blockedMessage) => {
        const accepted = await blacknetDecisionDialog({
            title: "BLACKNET DECISION",
            message: prompt,
            details: "Ta akcja wymaga decyzji operatora.",
            confirmLabel: "OK",
            cancelLabel: "ANULUJ",
            tone: signal?.tone || "lime"
        });
        if (!accepted) {
            return blacknetCtaResult(false, "Akcja BlackNet anulowana.", { cancelled: true });
        }
        return blacknetCtaResult(false, blockedMessage, { confirmed: true, controlled_block: true });
    };

    const blacknetOpenOperation = (signal, mode = "open") => {
        openSystemAppFromTerminal("map");
        const operationId = String(signal?.operation_id || signal?.cta_target_id || signal?.metadata?.operation_id || "").trim();
        if (operationId) {
            window.__blacknetOperationFocus = { mode, operation_id: operationId, signal_id: signal?.id || "" };
            addSystemMessage("info", "BlackNet", `Centrum Operacji: ${escapeHTML(operationId)}.`);
            return blacknetCtaResult(true);
        }
        if (mode === "open") {
            addSystemMessage("info", "BlackNet", "Centrum Operacji otwarte przez BlackNet.");
            return blacknetCtaResult(true);
        }
        return blacknetConfirmControlled(
            signal,
            "BlackNet chce uruchomic akcje operacyjna. Potwierdzic?",
            "Start operacji wymaga istniejacego kontraktu Operation Core."
        );
    };

    const blacknetInternalDetail = (signal, kind) => {
        const title = signal?.title || "BlackNet";
        const stat = signal?.stat || "";
        const value = signal?.value || "";
        addSystemMessage("info", "BlackNet", `${escapeHTML(kind)}: ${escapeHTML(title)} | ${escapeHTML(stat)} | ${escapeHTML(value)}`);
        return blacknetCtaResult(true);
    };

    const BLACKNET_CTA_HANDLERS = {
        open_googleplex: signal => blacknetOpenGoogleplex(signal),
        open_googleplex_search: signal => blacknetOpenGoogleplex(signal),
        open_ghost_exchange: signal => blacknetOpenExchange(signal),
        open_exchange_market: signal => blacknetOpenExchange(signal),
        open_exchange_category: signal => blacknetOpenExchange(signal),
        open_map: signal => blacknetOpenMap(signal),
        open_map_region: signal => blacknetOpenMap(signal, "region"),
        focus_map_target: signal => blacknetOpenMap(signal, "target"),
        show_hotspot: signal => blacknetOpenMap(signal, "hotspot"),
        open_cyberner: signal => blacknetOpenCybernerThread(signal),
        open_cyberner_thread: signal => blacknetOpenCybernerThread(signal),
        open_radio: signal => blacknetOpenRadio(signal),
        play_radio_podcast: signal => blacknetPlayPodcast(signal),
        open_operation: signal => blacknetOpenOperation(signal, "open"),
        start_operation: signal => blacknetOpenOperation(signal, "start"),
        accept_blacknet_job: signal => blacknetOpenOperation(signal, "accept"),
        teleport_to_hotspot: signal => blacknetTeleportToHotspot(signal),
        open_blacknet_detail: signal => blacknetInternalDetail(signal, "DETAIL"),
        open_blacknet_dossier: signal => blacknetInternalDetail(signal, "DOSSIER"),
        open_blacknet_report: signal => blacknetInternalDetail(signal, "REPORT"),
        none: () => blacknetCtaResult(false, "Ten sygnal jest informacyjny.", { noCapture: true })
    };

    const runBlacknetCta = async signal => {
        const action = String(signal?.cta_action || "").trim().toLowerCase();
        const startedAt = performance.now();
        blacknetCtaDiagnostic(signal, "start", { validation: "pending" });
        if (!action) {
            blacknetCtaDiagnostic(signal, "error", { error: "missing_cta_action", duration_ms: 0 });
            return blacknetCtaResult(false, "Sygnal nie posiada cta_action.");
        }
        if (blacknetSignalExpired(signal)) {
            blacknetCtaDiagnostic(signal, "error", { error: "expired_signal", duration_ms: Math.round(performance.now() - startedAt) });
            return blacknetCtaResult(false, "Sygnal BlackNet wygasl.");
        }
        const handler = BLACKNET_CTA_HANDLERS[action];
        if (typeof handler !== "function") {
            blacknetCtaDiagnostic(signal, "error", { error: "unknown_cta_action", duration_ms: Math.round(performance.now() - startedAt) });
            return blacknetCtaResult(false, `Nieznany most BlackNet: ${escapeHTML(action)}.`);
        }
        try {
            const result = await handler(signal);
            blacknetCtaDiagnostic(signal, result.ok ? "success" : "controlled", {
                validation: result.ok ? "ok" : "blocked",
                confirmation: Boolean(result.confirmed),
                cancelled: Boolean(result.cancelled),
                duration_ms: Math.round(performance.now() - startedAt)
            });
            return result;
        } catch (error) {
            console.warn("BlackNet CTA bridge failed", error);
            blacknetCtaDiagnostic(signal, "error", {
                error: String(error?.message || error),
                duration_ms: Math.round(performance.now() - startedAt)
            });
            return blacknetCtaResult(false, "Most BlackNet zakonczyl sie bledem kontrolowanym.");
        }
    };

    const renderBlackNet = () => {
        if (activeBrowserTab !== "blacknet") return;
        updateBrowserNarrowMode();
        if (!blacknetSignalsLoaded) {
            results.innerHTML = `
                <main class="blacknet-stage tone-lime">
                    <div class="bn-noise"></div>
                    <div class="bn-empty">Synchronizacja lokalnych sygnalow BlackNet...</div>
                </main>
            `;
            loadBlacknetSignals();
            return;
        }
        const visibleSignals = blacknetVisibleSignals();
        maybeRefillBlacknetSignals(visibleSignals);
        const activeIndex = Math.max(0, visibleSignals.findIndex(signal => signal.id === activeBlacknetSignalId));
        const featured = visibleSignals[activeIndex] || visibleSignals[0] || null;
        if (featured?.id) {
            activeBlacknetSignalId = featured.id;
        }
        const featuredCtaAction = String(featured?.cta_action || "").trim();
        const featuredCtaEnabled = Boolean(featuredCtaAction);
        results.innerHTML = `
            <main class="blacknet-stage tone-${escapeHTML(featured?.tone || "lime")}">
                <div class="bn-noise"></div>
                <header class="bn-brand">
                    <div class="bn-brand-mark">BLACKNET</div>
                    <div class="bn-mode-links" aria-label="WebDragons">
                        <button type="button" data-blacknet-open-tab="googleplex">GGPL</button>
                        <button type="button" data-blacknet-open-tab="exchange">GX</button>
                    </div>
                    <div class="bn-channel"><span>&gt;</span> ${escapeHTML(featured?.channel || "BRAK SYGNALU")}</div>
                </header>
                <div class="bn-signal-strength" aria-label="Sila sygnalu: mocna">
                    <div class="bn-bars"><i></i><i></i><i></i><i></i><i></i></div>
                    <span>SYGNAL: MOCNY</span>
                </div>
                <button class="bn-nav bn-nav-up" type="button" data-blacknet-nav="-1:up" aria-label="Poprzedni sygnal">⌃<span>PRZESUN W GORE</span></button>
                <button class="bn-nav bn-nav-down" type="button" data-blacknet-nav="1:down" aria-label="Nastepny sygnal">⌄<span>PRZESUN W DOL</span></button>
                <button class="bn-nav bn-nav-left" type="button" data-blacknet-nav="-1:left" aria-label="Poprzedni sygnal">‹<span>PRZESUN W LEWO</span></button>
                <button class="bn-nav bn-nav-right" type="button" data-blacknet-nav="1:right" aria-label="Nastepny sygnal">›<span>PRZESUN W PRAWO</span></button>
                ${featured ? `
                    <section class="bn-signal bn-layout-${Number(featured.layout || 1)} bn-enter-${escapeHTML(activeBlacknetDirection)}">
                        <div class="bn-signal-inner">
                            <div class="bn-copy">
                                <h2>${escapeHTML(featured.title)}</h2>
                                <div class="bn-stat"><span class="bn-target-icon">⊕</span>${escapeHTML(featured.stat)}</div>
                                <div class="bn-metric-label">${escapeHTML(featured.label)}</div>
                                <div class="bn-metric">${escapeHTML(featured.value)}</div>
                            </div>
                            <div class="bn-visual">${blacknetRadarSvg(featured)}</div>
                            <div class="bn-timer"><span class="bn-hourglass">⌛</span><small>SYGNAL WAZNY</small><strong>${escapeHTML(featured.timer)}</strong></div>
                            <button class="bn-cta ${blacknetCapturedSignals.has(featured.id) ? "captured" : ""}" type="button" data-blacknet-capture="${escapeHTML(featured.id)}" data-blacknet-cta-action="${escapeHTML(featuredCtaAction)}" ${featuredCtaEnabled ? "" : "disabled"}>
                                <span>⊕</span>${blacknetCapturedSignals.has(featured.id) ? "SYGNAL PRZECHWYCONY" : escapeHTML(featured.cta)}
                            </button>
                        </div>
                    </section>
                ` : `<div class="bn-empty">${escapeHTML(blacknetSignalsError || "Brak sygnalow w lokalnym zrodle BlackNet.")}</div>`}
                <footer class="bn-footer">
                    <span>${String(visibleSignals.length ? activeIndex + 1 : 0).padStart(2, "0")} / ${String(visibleSignals.length).padStart(2, "0")}</span>
                    <span>SWIPE · WASD · STRZALKI</span>
                    <span>BLACKNET SIGNAL BUS</span>
                </footer>
            </main>
        `;
        const blacknetStage = results.querySelector('.blacknet-stage');
        results.querySelectorAll('[data-blacknet-nav]').forEach(button => {
            button.addEventListener('click', event => {
                event.stopPropagation();
                const [delta, direction] = String(button.dataset.blacknetNav || "1:right").split(":");
                stepBlacknetSignal(Number(delta || 1), direction || "right");
            });
        });
        results.querySelectorAll('[data-blacknet-open-tab]').forEach(button => {
            button.addEventListener('pointerdown', event => {
                event.stopPropagation();
            });
            button.addEventListener('click', event => {
                event.stopPropagation();
                const tabName = button.dataset.blacknetOpenTab || "googleplex";
                if (["googleplex", "exchange", "blacknet"].includes(tabName)) {
                    switchBrowserTab(tabName);
                }
            });
        });
        results.querySelector('[data-blacknet-capture]')?.addEventListener('click', async event => {
            event.stopPropagation();
            const button = event.currentTarget;
            button.disabled = true;
            const signalId = event.currentTarget.dataset.blacknetCapture;
            const signal = blacknetVisibleSignals().find(item => item.id === signalId);
            const result = await runBlacknetCta(signal);
            if (result?.ok && signalId && !result.noCapture) {
                blacknetCapturedSignals.add(signalId);
                blacknetSignalIdentityKeys(signal).forEach(key => blacknetCapturedSignals.add(key));
                activeBlacknetSignalId = "";
                const remainingSignals = blacknetVisibleSignals().filter(item => !blacknetIsOutOfSignal(item));
                if (remainingSignals.length <= BLACKNET_SIGNAL_REFILL_THRESHOLD && !blacknetSignalFeedExhausted) {
                    loadBlacknetSignals({ append: true, force: true });
                }
                if (activeBrowserTab === "blacknet") renderBlackNet();
            } else {
                button.disabled = false;
                if (result?.message) {
                    addSystemMessage(result.cancelled || result.noCapture ? "info" : "warning", "BlackNet", result.message);
                } else {
                    addSystemMessage("warning", "BlackNet", "Ten sygnal nie ma jeszcze aktywnego mostu.");
                }
            }
        });
        blacknetStage?.addEventListener('pointerdown', event => {
            if (event.target?.closest?.('button, a, input, textarea, select')) return;
            blacknetPointerStartX = [event.clientX, event.clientY];
            if (blacknetStage.setPointerCapture) {
                blacknetStage.setPointerCapture(event.pointerId);
            }
        });
        blacknetStage?.addEventListener('pointerup', event => {
            if (blacknetPointerStartX === null) return;
            const [startX, startY] = blacknetPointerStartX;
            const dx = event.clientX - startX;
            const dy = event.clientY - startY;
            blacknetPointerStartX = null;
            if (Math.max(Math.abs(dx), Math.abs(dy)) < 44) return;
            if (Math.abs(dx) > Math.abs(dy)) {
                stepBlacknetSignal(dx < 0 ? 1 : -1, dx < 0 ? "right" : "left");
            } else {
                stepBlacknetSignal(dy < 0 ? 1 : -1, dy < 0 ? "down" : "up");
            }
        });
        updateBrowserNarrowMode();
    };

    const googleplexHomeUi = window.GoogleplexNewsUI || null;

    const renderGoogleplexHome = () => {
        if (activeBrowserTab !== "googleplex" || search.value.trim()) return;
        rememberGoogleplexHomeScroll();
        googleplexRenderedViewKey = "home";
        if (!googleplexHomeUi) {
            results.innerHTML = '<div class="googolplex-empty">Modul Googleplex News jest niedostepny.</div>';
            return;
        }
        if (googleplexHomeSnapshot) {
            googleplexHomeUi.renderHome(results, googleplexHomeSnapshot, {
                onAction: runGoogleplexNewsAction
            });
            requestAnimationFrame(() => {
                const surface = getGoogleplexScrollSurface();
                if (!surface) return;
                surface.scrollTop = Math.max(0, googleplexHomeScrollTop || 0);
                surface.scrollLeft = 0;
            });
            updateBrowserNarrowMode();
            return;
        }
        if (googleplexHomeError) {
            googleplexHomeUi.renderError(results, googleplexHomeError);
            return;
        }
        googleplexHomeUi.renderLoading(results);
    };

    const loadGoogleplexHome = async ({ force = false } = {}) => {
        if (googleplexHomeSnapshot && !force) {
            renderGoogleplexHome();
            return googleplexHomeSnapshot;
        }
        if (googleplexHomeLoading) return googleplexHomeLoading;
        googleplexHomeError = "";
        renderGoogleplexHome();
        googleplexHomeLoading = (async () => {
            const response = await fetch('/api/googleplex/news?view=home&limit=20', {
                credentials: 'same-origin',
                cache: 'no-store'
            });
            const payload = await response.json().catch(() => null);
            if (!response.ok || !payload || payload.success !== true) {
                throw new Error(payload?.message || `Googleplex News HTTP ${response.status}`);
            }
            const normalized = googleplexHomeUi?.normalizeSnapshot(payload);
            if (!normalized) throw new Error('Nieprawidlowy kontrakt Googleplex News.');
            googleplexHomeSnapshot = payload;
            googleplexHomeError = "";
            if (activeBrowserTab === "googleplex" && !search.value.trim()) {
                renderGoogleplexHome();
            }
            return payload;
        })().catch(error => {
            googleplexHomeError = String(error?.message || 'Nie udalo sie pobrac Googleplex News.');
            if (activeBrowserTab === "googleplex" && !search.value.trim()) {
                renderGoogleplexHome();
            }
            throw error;
        }).finally(() => {
            googleplexHomeLoading = null;
        });
        return googleplexHomeLoading;
    };

    async function runGoogleplexNewsAction(entry) {
        const action = entry?.action || {};
        const actionType = String(action.action_type || "").trim();
        const target = String(action.action_target || "").trim();
        if (action.kind !== "ACTIONABLE") return false;
        if (actionType === "open_googleplex_search") {
            browserQueries.googleplex = target || "/all";
            pendingGoogleplexSearch = browserQueries.googleplex;
            search.value = browserQueries.googleplex;
            renderCatalog();
            return true;
        }
        if (actionType === "open_blacknet") {
            browserQueries.blacknet = "";
            switchBrowserTab("blacknet");
            return true;
        }
        if (actionType === "open_ghost_exchange") {
            browserQueries.exchange = target === "market" ? "" : target;
            switchBrowserTab("exchange");
            return true;
        }
        if (actionType === "open_map") {
            return blacknetOpenMap({
                id: entry?.content?.news_id || "googleplex-news",
                title: entry?.content?.title || "Googleplex News",
                cta_target_id: target || "world",
                metadata: {}
            }).ok;
        }
        if (actionType === "open_cyberner") {
            return blacknetOpenCybernerThread({
                id: entry?.content?.news_id || "googleplex-news",
                title: entry?.content?.title || "Googleplex News",
                cta_target: target || "world",
                metadata: {thread_scope: "group", thread_channel: "world", thread_peer: "global"}
            }).ok;
        }
        if (actionType === "open_operation") {
            return blacknetOpenOperation({
                id: entry?.content?.news_id || "googleplex-news",
                title: entry?.content?.title || "Googleplex News",
                cta_target_id: "",
                metadata: {}
            }, "open").ok;
        }
        addSystemMessage("warning", "Googleplex News", "Nieznany lub niedozwolony most akcji.");
        return false;
    }

    const renderCatalog = () => {
        if (activeBrowserTab !== "googleplex") return;
        updateBrowserNarrowMode();
        const rawQuery = search.value.trim();
        const query = rawQuery.toLowerCase();
        const showAll = query === "/all";
        if (!query) {
            renderGoogleplexHome();
            if (!googleplexHomeSnapshot && !googleplexHomeLoading && !googleplexHomeError) {
                loadGoogleplexHome().catch(() => {});
            }
            updateBrowserNarrowMode();
            return;
        }

        rememberGoogleplexHomeScroll();
        const settleCatalogScroll = beginGoogleplexCatalogView(showAll ? "all" : `query:${query}`);

        if (!catalogLoaded) {
            results.innerHTML = '<div class="googolplex-empty">Synchronizacja katalogu Googleplex...</div>';
            settleCatalogScroll();
            loadCatalog().catch(error => {
                console.warn('Googleplex catalog lazy load failed', error);
                if (activeBrowserTab === "googleplex" && search.value.trim()) {
                    results.innerHTML = '<div class="googolplex-empty">Nie udało się pobrać katalogu.</div>';
                }
            });
            return;
        }

        const filteredMatches = showAll
            ? catalog.filter(item => item && typeof item === "object")
            : catalog.filter(item => googleplexSearchText(item).includes(query));
        const matches = showAll
            ? filteredMatches.slice().sort((left, right) => {
                const downloadsDelta = Number(right.downloads || 0) - Number(left.downloads || 0);
                if (downloadsDelta) return downloadsDelta;
                return String(left.id || left.app_id || "").localeCompare(String(right.id || right.app_id || ""));
            })
            : filteredMatches;
        results.innerHTML = '';
        if (matches.length === 0) {
            results.innerHTML = '<div class="googolplex-empty">Brak aplikacji do pokazania.</div>';
            settleCatalogScroll();
            updateBrowserNarrowMode();
            return;
        }

        results.innerHTML = `<main class="gp-search-view gp-catalog-home" data-search-mode="${showAll ? "all" : "query"}">
            <header class="gp-search-view__bar"><span>${showAll ? "ALL APPLICATIONS" : "SEARCH RESULTS"} // PRODUCT GRID</span><strong>${matches.length} APPS</strong></header>
            <section class="gp-search-results" aria-label="Googleplex applications"></section>
            <footer class="gp-search-view__protocol"><span>SOURCE: PUBLIC CATALOG</span><span>${showAll ? "RANK: DOWNLOADS DESC" : "ORDER: SEARCH RESULT"}</span><span>${showAll ? "TIE: APP_ID" : "QUERY: BOUNDED"}</span><span>PROFILE: NOT READ</span></footer>
        </main>`;
        const cardsRoot = results.querySelector('.gp-search-results');

        const createProductCard = (item, variant, layoutIndex) => {
            const price = Number(item.price || 0);
            const isProduct = !!(item.product_type || (Array.isArray(item.effects) && item.effects.length));
            const projectedApps = Array.isArray((toolbarProfile || {}).apps)
                ? toolbarProfile.apps
                : null;
            const installed = isProduct
                ? item.installed === true
                : projectedApps
                    ? projectedApps.some(app => String(app?.id || app?.app_id || '') === String(item.id || ''))
                    : item.installed === true;
            const travelEffect = Array.isArray(item.effects)
                ? item.effects.find(effect => effect && typeof effect === "object" && effect.type === "travel_city")
                : null;
            const isTravelTicket = item.product_type === "travel_ticket" || Boolean(travelEffect);
            const travelDestination = String(travelEffect?.city || item.travel_city || "").trim();
            const canAfford = walletBalance >= price;
            const staleInstalledProjection = !isProduct
                && projectedApps
                && item.installed === true
                && !installed;
            const installBlockedReason = !isProduct && projectedApps
                ? (installed ? "Aplikacja juz kupiona." : (staleInstalledProjection ? "" : item.install_blocked_reason || ""))
                : item.install_blocked_reason || "";
            const canInstall = !installed && canAfford && !installBlockedReason;
            const buttonLabel = installed ? (isProduct ? "KUPIONO" : "ZAINSTALOWANO") : (canAfford ? (isProduct ? "Kup" : "Zainstaluj") : "Brak \u015brodk\u00f3w");
            const riskLevel = Math.max(0, Math.min(5, Number(item.risk_level || 0)));
            const riskStars = riskLevel ? "&#9733;".repeat(riskLevel) : "brak";
            const fileSize = Number(item.file_size || 0);
            const diskUsage = Number(item.disk_usage || item.install_size || fileSize || 0);
            const qualityScore = Math.max(0, Math.min(100, Number(item.quality_score || 0)));
            const reliability = Math.max(0, Math.min(100, Number(item.reliability || 0)));
            const creatorPower = Math.max(0, Math.min(100, Number(item.creator_power || 0)));
            const powerScore = Math.max(0, Math.min(100, Number(item.power_score || 0)));
            const priceHint = Number(item.price_hint || 0);
            const effectsText = Array.isArray(item.effects)
                ? item.effects.map(effect => {
                    if (!effect || typeof effect !== 'object') return '';
                    if (effect.type === 'travel_city') return `Miasto: ${effect.city || item.travel_city || '-'}`;
                    if (effect.type === 'storage_capacity_bonus') return `Dysk +${formatStorageSize(effect.value || item.storage_capacity_bonus || 0)}`;
                    if (effect.type === 'map_zoom_bonus') return `Zoom +${Number(effect.value || 0)}`;
                    if (effect.type === 'scan_range_bonus') return `Skan +${Number(effect.value || 0)} m`;
                    if (effect.type === 'bike_range_bonus') return `Rower +${Number(effect.value || 0)} m`;
                    return `${effect.type || 'efekt'} ${effect.value || effect.city || ''}`.trim();
                }).filter(Boolean).join(', ')
                : '';
            const requirementsMeta = `
                <div class="gp-app-status-strip gp-search-product__requirements" aria-label="Wymagania aplikacji">
                    <span class="gp-app-status-strip__item">
                        <small>LVL</small>
                        <strong>${Number(item.required_level || 1)}</strong>
                    </span>
                    <span class="gp-app-status-strip__item">
                        <small>RESPECT</small>
                        <strong>${Number(item.required_respect || 0)}</strong>
                    </span>
                    <span class="gp-app-status-strip__item">
                        <small>RISK</small>
                        <strong>${riskStars}</strong>
                    </span>
                </div>
            `;
            const coreParameterRows = [
                { key: "level", label: "Poziom", value: item.app_level || "Basic" },
                { key: "family", label: "Rodzina", value: item.tool_family || item.type || "tool" },
                { key: "mode", label: "Tryb", value: item.tool_mode || item.scanner_mode || "desktop" }
            ];
            if (isProduct) {
                coreParameterRows.push(
                    { key: "product", label: "Produkt", value: item.product_type || "-" },
                    { key: "category", label: "Kategoria", value: item.category || "-" },
                    { key: "effect", label: "Efekt", value: effectsText || "-" }
                );
            }
            coreParameterRows.push({
                key: "tier",
                label: "Tier",
                value: item.balance_tier || item.app_level || "Basic"
            });
            const technicalParameterRows = [
                { key: "map", label: "Map", values: googleplexList(item.map_actions) },
                { key: "ops", label: "Ops", values: googleplexList(item.operation_types) },
                { key: "data", label: "Data", values: googleplexList(item.resource_types) }
            ];
            const metricParameterRows = [
                { key: "weight", label: "Waga", value: formatStorageSize(fileSize) },
                { key: "install", label: "Instalacja", value: formatStorageSize(diskUsage) },
                { key: "quality", label: "Jako\u015b\u0107", value: `${qualityScore}/100` },
                { key: "reliability", label: "Niezawodno\u015b\u0107", value: `${reliability}/100` },
                { key: "creator", label: "Moc tw\u00f3rcy", value: `${creatorPower}/100` },
                { key: "power", label: "Moc", value: `${powerScore}/100` },
                { key: "price-hint", label: "Cena sugerowana", value: priceHint ? `${priceHint} HC` : "-" }
            ];
            const renderSpecRows = (rows, rowClass) => rows.map(({ key, label, value }) => `
                <div class="gp-app-spec ${rowClass}" data-spec-key="${escapeHTML(key)}">
                    <dt>${escapeHTML(label)}</dt>
                    <dd>${googleplexBreakableText(value)}</dd>
                </div>
            `).join("");
            const renderTechnicalRows = rows => rows.map(({ key, label, values }) => {
                const tokens = values.length
                    ? values.map(value => `<span class="gp-app-spec-panel__token">${googleplexBreakableText(value)}</span>`).join("")
                    : '<span class="gp-app-spec-panel__token">-</span>';
                return `
                    <div class="gp-app-spec gp-app-spec--technical" data-spec-key="${escapeHTML(key)}">
                        <dt>${escapeHTML(label)}</dt>
                        <dd>${tokens}</dd>
                    </div>
                `;
            }).join("");
            const coreParametersMeta = renderSpecRows(coreParameterRows, "gp-app-spec--core");
            const technicalParametersMeta = renderTechnicalRows(technicalParameterRows);
            const metricParametersMeta = renderSpecRows(metricParameterRows, "gp-app-spec--metric");
            const purchaseStateText = installed
                ? (installBlockedReason || "Aplikacja juz kupiona.")
                : installBlockedReason;
            const purchaseState = purchaseStateText
                ? `<div class="gp-app-purchase-state gp-search-product__hint" data-purchase-state="${installed ? "owned" : "blocked"}">
                    <span class="gp-app-purchase-state__mark" aria-hidden="true">${installed ? "&#10003;" : "!"}</span>
                    <span>${escapeHTML(purchaseStateText)}</span>
                </div>`
                : "";
            const appId = String(item.id || item.app_id || "");
            const iconValue = String(item.icon || browserUiIcons.app);
            const familyLabel = String(item.tool_family || item.category || item.type || "tool");
            const normalizedFamily = `${familyLabel} ${item.type || ""}`.toLowerCase();
            const iconSocket = variant === "hero" || variant === "single"
                ? "core"
                : variant === "middle"
                    ? (/scanner|tracker|recon/.test(normalizedFamily) ? "target" : "side")
                    : /custom|system|exploit/.test(normalizedFamily)
                        ? "hex"
                        : /scanner|tracker|recon/.test(normalizedFamily)
                            ? "target"
                            : "compact";
            const presentationVariant = variant === "middle"
                ? "side"
                : variant === "small" ? "compact" : variant;
            const iconSocketAsset = googleplexIconSocketAssets[iconSocket]
                || googleplexIconSocketAssets.compact;
            const card = document.createElement('article');
            card.className = `gp-search-product gp-search-product--${variant}${installed ? " is-installed" : ""} gp-app-card gp-app-card--${presentationVariant}`;
            card.dataset.appId = appId;
            card.dataset.layoutIndex = String(layoutIndex);
            card.dataset.assetFamily = "tool";
            card.dataset.assetState = installed ? "victory" : "neutral";
            card.dataset.iconSocket = iconSocket;
            card.innerHTML = `
                <header class="gp-app-card__header gp-search-product__header">
                    <span class="gp-app-card__eyebrow gp-search-product__eyebrow">${escapeHTML(familyLabel)} // APPLICATION</span>
                    <h2 class="gp-app-card__title gp-search-product__title">${escapeHTML(item.name || "Aplikacja")}</h2>
                    <p class="gp-app-card__description gp-search-product__description">${escapeHTML(item.description || "Brak opisu.")}</p>
                </header>
                ${requirementsMeta}
                <div class="gp-app-card__body">
                    <div class="gp-app-icon-stage gp-app-icon-stage--${iconSocket} gp-search-product__icon" aria-hidden="true">
                        <img class="gp-app-icon-stage__socket" src="${escapeHTML(iconSocketAsset)}" alt="" draggable="false">
                        <span class="gp-app-icon-stage__user-icon gp-search-product__icon-symbol">${escapeHTML(iconValue)}</span>
                    </div>
                    <div class="gp-app-spec-panel">
                        <dl class="gp-app-spec-panel__core">${coreParametersMeta}</dl>
                        <dl class="gp-app-spec-panel__technical" aria-label="Dane techniczne aplikacji">${technicalParametersMeta}</dl>
                        <dl class="gp-app-spec-panel__metrics">${metricParametersMeta}</dl>
                    </div>
                </div>
                ${purchaseState}
                <footer class="gp-app-market-footer gp-search-product__footer">
                    <div class="gp-app-market-footer__identity gp-search-product__commerce">
                        <span>${escapeHTML(item.type || "tool")}</span>
                        <span><strong>${Number(item.downloads || 0)}</strong> pobra\u0144</span>
                    </div>
                    <div class="gp-app-market-footer__price">
                        <small>CENA</small>
                        <strong>${price}</strong>
                        <span>HC</span>
                    </div>
                    <button class="gp-app-market-footer__action gp-search-product__action" data-googleplex-install type="button" ${canInstall ? "" : "disabled"}>${buttonLabel}</button>
                </footer>
            `;
            const installButton = card.querySelector('[data-googleplex-install]');
            let installInFlight = false;
            installButton.addEventListener('click', async () => {
                if (!canInstall) return;
                if (installInFlight) return;
                if (isTravelTicket) {
                    const accepted = await blacknetDecisionDialog({
                        title: "POTWIERDZENIE PODROZY",
                        message: travelDestination
                            ? `Kupic ticket i przeniesc operatora do: ${travelDestination}?`
                            : "Kupic ticket i wykonac teleport do wskazanej lokalizacji?",
                        details: `${item.name || "Travel Ticket"} kosztuje ${price} HC. Anulowanie nie pobierze HC i nie zmieni pozycji.`,
                        confirmLabel: "OK",
                        cancelLabel: "ANULUJ",
                        tone: "lime"
                    });
                    if (!accepted) {
                        addSystemMessage("info", "Googleplex", "Teleport anulowany. Ticket nie zostal kupiony.");
                        return;
                    }
                } else if (item.purchase_confirmation === true) {
                    const accepted = await blacknetDecisionDialog({
                        title: "POTWIERDZENIE ZAKUPU",
                        message: `Kupic i zainstalowac: ${item.name || "aplikacja"}?`,
                        details: `${item.name || "Aplikacja"} kosztuje ${price} HC. Anulowanie nie pobierze HC i nie utworzy launchera.`,
                        confirmLabel: "KUP I ZAINSTALUJ",
                        cancelLabel: "ANULUJ",
                        tone: "lime"
                    });
                    if (!accepted) {
                        addSystemMessage("info", "Googleplex", "Zakup aplikacji anulowany.");
                        return;
                    }
                }
                installInFlight = true;
                installButton.disabled = true;
                installButton.textContent = "INSTALACJA...";
                showInstallAppProgress(
                    item,
                    null,
                    success => {
                        installInFlight = false;
                        if (!success && installButton.isConnected) {
                            installButton.disabled = false;
                            installButton.textContent = buttonLabel;
                        }
                    }
                );
            });
            return card;
        };

        try {
            if (!googleplexSearchPresentation || typeof googleplexSearchPresentation.mount !== "function") {
                throw new Error("googleplex_search_presentation_unavailable");
            }
            const renderReport = googleplexSearchPresentation.mount(cardsRoot, matches, createProductCard);
            if (Number(renderReport?.rendered_count || 0) !== matches.length) {
                throw new Error("googleplex_search_render_count_mismatch");
            }
        } catch (error) {
            cardsRoot.replaceChildren();
            const failure = document.createElement("div");
            failure.className = "googolplex-empty";
            failure.textContent = "Nie uda\u0142o si\u0119 zbudowa\u0107 widoku katalogu.";
            cardsRoot.appendChild(failure);
            console.error("Googleplex search presentation failed", {
                reason: String(error?.message || "presentation_error"),
                result_count: matches.length
            });
        }
        settleCatalogScroll();
        updateBrowserNarrowMode();
    };

    appsProjectionListener = () => {
        if (term.isConnected && activeBrowserTab === "googleplex" && search.value.trim()) {
            walletBalance = Number((toolbarProfile || {}).hackcoins ?? walletBalance ?? 0);
            renderBrowserWallet();
            renderCatalog();
        }
    };
    window.addEventListener('chaos:apps-projection-updated', appsProjectionListener);

    const gxSectorLabels = {
        camera: "Kamery",
        atm: "Bankomaty",
        gps: "GPS",
        device: "Dane urzadzen",
        personal: "Dane osobowe",
        credentials: "Dane logowania",
        financial: "Dane finansowe",
        network: "Sieci",
        audio: "Audio",
        vehicle: "Pojazdy",
        unknown: "Inne dane"
    };

    const gxSectorSubtitles = {
        camera: "Rynek kamer i monitoringu",
        atm: "Rynek danych z bankomatow",
        gps: "Rynek lokalizacji i tras",
        device: "Rynek informacji o urzadzeniach",
        personal: "Rynek danych osobowych",
        credentials: "Rynek credentiali i kont",
        financial: "Rynek finansow i transakcji",
        network: "Rynek danych sieciowych",
        audio: "Rynek sygnalow audio",
        vehicle: "Rynek telemetrii pojazdow",
        unknown: "Rynek danych niesklasyfikowanych"
    };

    const gxSectorIcons = {
        camera: "\u25c9",
        atm: "\u25a3",
        gps: "\u2316",
        device: "\u25a1",
        personal: "\u25cb",
        credentials: "\u25c7",
        financial: "\u25b1",
        network: "\u2301",
        audio: "\u266a",
        vehicle: "\u25c8",
        unknown: "\u25a1"
    };

    const gxHistorySeries = [
        { sector: "camera", className: "gx-series-camera" },
        { sector: "atm", className: "gx-series-atm" },
        { sector: "gps", className: "gx-series-gps" },
        { sector: "device", className: "gx-series-device" },
        { sector: "credentials", className: "gx-series-credentials" },
        { sector: "personal", className: "gx-series-personal" },
        { sector: "financial", className: "gx-series-financial" },
        { sector: "network", className: "gx-series-network" },
        { sector: "audio", className: "gx-series-audio" },
        { sector: "vehicle", className: "gx-series-vehicle" }
    ];

    const gxNumber = value => {
        const number = Number(value || 0);
        if (!Number.isFinite(number)) return 0;
        return Math.round(number);
    };

    const gxFormatNumber = value => String(gxNumber(value)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    const gxFormatHc = value => `${gxFormatNumber(value)} HC`;
    const gxFormatMb = value => `${gxFormatNumber(value)} MB`;

    const gxSparklineSvg = (values = [], className = "gx-sparkline") => {
        const points = Array.isArray(values) ? values.map(Number).filter(Number.isFinite) : [];
        const series = points.length ? points : [0, 0, 0, 0, 0, 0, 0];
        const width = 120;
        const height = 38;
        const max = Math.max(...series, 1);
        const step = series.length > 1 ? width / (series.length - 1) : width;
        const polyline = series.map((value, index) => {
            const x = index * step;
            const y = height - ((value / max) * (height - 8)) - 4;
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        }).join(" ");
        const lastX = (series.length - 1) * step;
        const lastY = height - ((series[series.length - 1] / max) * (height - 8)) - 4;
        return `
            <svg class="${className}" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">
                <polyline points="${polyline}"></polyline>
                <circle cx="${lastX.toFixed(1)}" cy="${lastY.toFixed(1)}" r="2"></circle>
            </svg>
        `;
    };

    const gxHistoryChartSvg = history => {
        const rows = Array.isArray(history) ? history : [];
        if (!rows.length) {
            return '<div class="gx-chart-empty">Historia sprzedazy zostanie widoczna po pierwszych transakcjach.</div>';
        }
        const labels = rows.map(item => item.label || item.date || "");
        const width = 640;
        const height = 210;
        const padding = 24;
        const activeSeries = gxHistorySeries.map(series => ({
            ...series,
            label: gxSectorLabels[series.sector] || series.sector,
            values: rows.map(item => gxNumber(item?.sectors?.[series.sector]))
        })).filter(series => series.values.some(value => value > 0));
        const fallbackSeries = [{
            sector: "total",
            className: "gx-series-camera",
            label: "Razem",
            values: rows.map(item => gxNumber(item.hc))
        }];
        const chartSeries = activeSeries.length ? activeSeries : fallbackSeries;
        const max = Math.max(...chartSeries.flatMap(series => series.values), 1);
        const step = rows.length > 1 ? (width - padding * 2) / (rows.length - 1) : width - padding * 2;
        const seriesMarkup = chartSeries.map(series => {
            const points = series.values.map((value, index) => {
                const x = padding + index * step;
                const y = height - padding - ((value / max) * (height - padding * 2));
                return `${x.toFixed(1)},${y.toFixed(1)}`;
            }).join(" ");
            const circles = series.values.map((value, index) => {
                if (value <= 0) return "";
                const x = padding + index * step;
                const y = height - padding - ((value / max) * (height - padding * 2));
                return `<circle class="${series.className}" cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="3"><title>${escapeHTML(labels[index])} / ${escapeHTML(series.label)}: ${gxFormatHc(value)}</title></circle>`;
            }).join("");
            return `
                <polyline class="${series.className}" points="${points}"></polyline>
                ${circles}
            `;
        }).join("");
        const axis = labels.map((label, index) => {
            const x = padding + index * step;
            return `<text x="${x.toFixed(1)}" y="${height - 4}" text-anchor="middle">${escapeHTML(label)}</text>`;
        }).join("");
        return `
            <svg class="gx-sparkline gx-history-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Historia sprzedazy Ghost Exchange">
                <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="rgba(0,255,102,.22)" />
                ${seriesMarkup}
                <g class="gx-history-axis">${axis}</g>
            </svg>
        `;
    };

    const gxMissingText = sector => {
        const missingRecords = gxNumber(sector.missing_records);
        if (missingRecords > 0) return `Brakuje ${missingRecords} rekordow`;
        return `Brakuje ${gxFormatMb(sector.missing_mb)}`;
    };

    const renderExchange = () => {
        if (activeBrowserTab !== "exchange") return;
        updateBrowserNarrowMode();
        const query = search.value.toLowerCase().trim();
        const summary = exchangeDashboard.summary || {};
        const sectors = Array.isArray(exchangeDashboard.sectors) ? exchangeDashboard.sectors : [];
        const recentTransactions = Array.isArray(exchangeDashboard.recent_transactions)
            ? exchangeDashboard.recent_transactions
            : [];
        const history = Array.isArray(exchangeDashboard.history_7d) ? exchangeDashboard.history_7d : [];
        const matchingSectors = sectors.filter(sector => {
            const name = gxSectorLabels[sector.sector] || sector.sector || "";
            return !query ||
                String(sector.sector || "").toLowerCase().includes(query) ||
                String(name).toLowerCase().includes(query) ||
                String(sector.status || "").toLowerCase().includes(query);
        });

        results.innerHTML = '';
        const dashboard = document.createElement('section');
        dashboard.className = 'gx-dashboard';

        if (!matchingSectors.length) {
            dashboard.innerHTML = '<div class="gx-chart-empty">Brak sektorow rynku dla tego filtra.</div>';
            results.appendChild(dashboard);
            updateBrowserNarrowMode();
            return;
        }

        const sectorCards = matchingSectors.map(sector => {
            const sectorKey = sector.sector || "unknown";
            const progress = Math.max(0, Math.min(100, gxNumber(sector.progress_percent)));
            const stateClass = sector.status === "trading" ? "is-trading" : (progress > 0 ? "is-waiting" : "");
            return `
                <article class="gx-sector-card ${stateClass}">
                    <div class="gx-sector-head">
                        <span class="gx-sector-icon">${escapeHTML(gxSectorIcons[sectorKey] || gxSectorIcons.unknown)}</span>
                        <span>
                            <span class="gx-sector-title">${escapeHTML(gxSectorLabels[sectorKey] || sectorKey)}</span>
                            <span class="gx-sector-subtitle">${escapeHTML(gxSectorSubtitles[sectorKey] || gxSectorSubtitles.unknown)}</span>
                        </span>
                    </div>
                    <div class="gx-sector-stats">
                        <span class="gx-stat"><span class="gx-stat-label">Oczekuje</span><b class="gx-stat-value">${gxFormatNumber(sector.pending_files)} plikow</b></span>
                        <span class="gx-stat"><span class="gx-stat-label">Wolumen</span><b class="gx-stat-value">${gxFormatMb(sector.pending_mb)}</b></span>
                        <span class="gx-stat gx-stat-wide"><span class="gx-stat-label">HC dzisiaj</span><b class="gx-stat-value">${gxFormatHc(sector.hc_today)}</b></span>
                    </div>
                    <div class="gx-sector-progress">
                        <div class="gx-progress-meta">
                            <span>${escapeHTML(gxMissingText(sector))}</span>
                            <span>${progress}%</span>
                        </div>
                        <div class="gx-progress-track"><span class="gx-progress-fill" style="--gx-progress:${progress}%"></span></div>
                    </div>
                    ${gxSparklineSvg(sector.sparkline)}
                    <div class="gx-sector-foot">
                        <span>${escapeHTML(sector.status || 'collecting')} · ${gxFormatNumber(sector.listed_batches || 0)} paczek</span>
                        <b>${escapeHTML(sector.estimated_sale_time || '~5 min')}</b>
                    </div>
                </article>
            `;
        }).join("");

        const summaryCards = `
            <div class="gx-summary-card"><span class="gx-summary-label">Oczekujace dane</span><b class="gx-summary-value">${gxFormatNumber(summary.pending_files)} plikow / ${gxFormatMb(summary.pending_mb)}</b></div>
            <div class="gx-summary-card"><span class="gx-summary-label">W obrocie</span><b class="gx-summary-value">${gxFormatNumber(summary.listed_batches)} paczek</b></div>
            <div class="gx-summary-card"><span class="gx-summary-label">Sprzedane dzisiaj</span><b class="gx-summary-value">${gxFormatNumber(summary.sold_today_files)} plikow</b></div>
            <div class="gx-summary-card"><span class="gx-summary-label">Zarobek dzisiaj</span><b class="gx-summary-value">${gxFormatHc(summary.hc_today)}</b></div>
            <div class="gx-summary-card"><span class="gx-summary-label">Zarobek lacznie</span><b class="gx-summary-value">${gxFormatHc(summary.hc_total)}</b></div>
            <div class="gx-summary-card"><span class="gx-summary-label">Srednia cena paczki</span><b class="gx-summary-value">${gxFormatHc(summary.average_price)}</b></div>
        `;

        const transactionRows = recentTransactions.length
            ? recentTransactions.map(transaction => `
                <div class="gx-transaction-row">
                    <span>${escapeHTML(String(transaction.sold_at || '').slice(11, 16) || '--:--')}</span>
                    <span class="gx-transaction-sector">${escapeHTML(gxSectorLabels[transaction.market_sector] || transaction.market_sector || '-')}</span>
                    <span class="gx-transaction-desc">${escapeHTML(transaction.file_name || transaction.batch_id || 'Paczka danych')}</span>
                    <span>${gxFormatMb(transaction.volume_mb)}</span>
                    <span class="gx-transaction-hc">${gxFormatHc(transaction.price)}</span>
                </div>
            `).join("")
            : '<div class="gx-chart-empty">Ostatnie transakcje pojawia sie po pierwszej sprzedazy paczki.</div>';

        dashboard.innerHTML = `
            <div class="gx-sector-grid">${sectorCards}</div>
            <div class="gx-summary-grid">${summaryCards}</div>
            <div class="gx-main-row">
                <section class="gx-transactions-panel">
                    <div class="gx-chart-header">
                        <span class="gx-chart-title">Ostatnie transakcje</span>
                        <span class="gx-chart-subtitle">Ghost Exchange</span>
                    </div>
                    <div class="gx-transactions-list">${transactionRows}</div>
                </section>
                <section class="gx-chart-panel">
                    <div class="gx-chart-header">
                        <span class="gx-chart-title">Historia sprzedazy (7 dni)</span>
                        <span class="gx-chart-subtitle">fallback SVG / uPlot-ready</span>
                    </div>
                    <div class="gx-chart-legend">
                        ${gxHistorySeries.map(series => `
                            <span class="gx-chart-legend-item ${series.className}">${escapeHTML(gxSectorLabels[series.sector] || series.sector)}</span>
                        `).join("")}
                    </div>
                    <div class="gx-chart-body">
                        <div class="gx-chart-uplot">${gxHistoryChartSvg(history)}</div>
                    </div>
                </section>
            </div>
            <div class="gx-dashboard-note">
                <span>Automatyczny rynek danych dziala w tle. File Manager pozostaje miejscem podgladu lootow.</span>
                <b>${gxFormatNumber(summary.transaction_count)} transakcji</b>
            </div>
        `;
        results.appendChild(dashboard);
        updateBrowserNarrowMode();
    };

    ghostExchangeDeltaViews.add({
        isConnected: () => document.body.contains(term),
        update: (payload = {}) => {
            if (payload.summary && typeof payload.summary === "object") {
                exchangeDashboard.summary = {
                    ...(exchangeDashboard.summary || {}),
                    ...payload.summary
                };
            }
            if (Array.isArray(payload.sectors)) {
                exchangeDashboard.sectors = payload.sectors;
            }
            if (Array.isArray(payload.history_7d)) {
                exchangeDashboard.history_7d = payload.history_7d;
            }
            if (Array.isArray(payload.recent_transactions)) {
                exchangeDashboard.recent_transactions = payload.recent_transactions;
            } else if (payload.transaction && typeof payload.transaction === "object") {
                const tx = payload.transaction;
                const txId = String(tx.batch_id || tx.id || "");
                const current = Array.isArray(exchangeDashboard.recent_transactions)
                    ? exchangeDashboard.recent_transactions
                    : [];
                const withoutDuplicate = txId
                    ? current.filter(item => String(item.batch_id || item.id || "") !== txId)
                    : current;
                exchangeDashboard.recent_transactions = [tx, ...withoutDuplicate].slice(0, 8);
            }
            if (activeBrowserTab === "exchange") {
                renderExchange();
            }
        }
    });

    async function loadCatalog() {
        if (catalogLoaded) {
            renderCatalog();
            return catalog;
        }
        if (catalogLoading) return catalogLoading;
        catalogLoading = (async () => {
            const resourcesRes = await fetch('/resources.json', {
                credentials: 'same-origin',
                cache: 'no-store'
            });
            const catalogPayload = await resourcesRes.json().catch(() => null);
            if (!resourcesRes.ok || !Array.isArray(catalogPayload)) {
                throw new Error(`Googleplex catalog HTTP ${resourcesRes.status}`);
            }
            catalog = dedupeGoogleplexCatalog(catalogPayload);
            catalogLoaded = true;
            walletBalance = Number((toolbarProfile || {}).hackcoins ?? walletBalance ?? 0);
            renderBrowserWallet();
            if (pendingGoogleplexSearch) {
                browserQueries.googleplex = pendingGoogleplexSearch;
                if (activeBrowserTab === "googleplex") search.value = pendingGoogleplexSearch;
                pendingGoogleplexSearch = "";
            }
            renderCatalog();
            return catalog;
        })().finally(() => {
            catalogLoading = null;
        });
        return catalogLoading;
    }

    async function loadExchange() {
        results.innerHTML = '<div class="googolplex-empty">Synchronizacja Ghost Exchange...</div>';
        try {
            const res = await fetch('/api/ghost-exchange');
            const data = await res.json();
            if (!res.ok || data.success === false) {
                results.innerHTML = `<div class="googolplex-empty">${escapeHTML(data.message || 'Nie udalo sie pobrac Ghost Exchange.')}</div>`;
                return;
            }
            exchangeFiles = data.files || [];
            exchangeDashboard = {
                summary: data.summary || {},
                sectors: data.sectors || [],
                recent_transactions: data.recent_transactions || [],
                history_7d: data.history_7d || []
            };
            if (Object.prototype.hasOwnProperty.call(data, "balance")) {
                walletBalance = Number(data.balance || 0);
                renderBrowserWallet();
                if (typeof setToolbarProfile === "function") {
                    setToolbarProfile({
                        ...(toolbarProfile || {}),
                        hackcoins: walletBalance
                    });
                }
            }
            renderExchange();
        } catch (err) {
            console.warn('Ghost Exchange load failed', err);
            results.innerHTML = '<div class="googolplex-empty">Brak polaczenia z Ghost Exchange.</div>';
        }
    }

    async function previewGhostExchangeSale(fileId) {
        if (!fileId) return;
        try {
            const res = await fetch('/api/ghost-exchange/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_id: fileId })
            });
            const data = await res.json();
            if (!res.ok || data.success === false) {
                addSystemMessage("warning", "Ghost Exchange", data.message || "Nie udalo sie przygotowac oferty.");
                return;
            }
            exchangeFiles = data.files || exchangeFiles.map(item => item.id === fileId ? data.file : item);
            addSystemMessage("info", "Ghost Exchange", data.message || "Oferta przygotowana w trybie preview.");
            renderExchange();
        } catch (err) {
            console.warn('Ghost Exchange preview failed', err);
            addSystemMessage("danger", "Ghost Exchange", "Brak polaczenia z Ghost Exchange.");
        }
    }

    async function sellGhostExchangeFile(fileId) {
        if (!fileId) return;
        try {
            const res = await fetch('/api/ghost-exchange/sell', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ file_id: fileId })
            });
            const data = await res.json();
            if (!res.ok || data.success === false) {
                addSystemMessage("warning", "Ghost Exchange", data.message || "Nie udalo sie sprzedac pakietu.");
                return;
            }
            exchangeFiles = data.files || exchangeFiles.filter(item => item.id !== fileId);
            walletBalance = Number(Object.prototype.hasOwnProperty.call(data, "balance") ? data.balance : (walletBalance || 0));
            renderBrowserWallet();
            if (typeof setToolbarProfile === "function") {
                setToolbarProfile({
                    ...(toolbarProfile || {}),
                    hackcoins: walletBalance
                });
            }
            addSystemMessage("success", "Ghost Exchange", data.message || "Pakiet danych sprzedany.");
            renderExchange();
        } catch (err) {
            console.warn('Ghost Exchange sell failed', err);
            addSystemMessage("danger", "Ghost Exchange", "Brak polaczenia z Ghost Exchange.");
        }
    }

    function switchBrowserTab(tabName) {
        if (activeBrowserTab === "googleplex") {
            rememberGoogleplexHomeScroll();
        }
        if (tabName !== activeBrowserTab
            && Object.prototype.hasOwnProperty.call(browserQueries, activeBrowserTab)) {
            browserQueries[activeBrowserTab] = search.value;
        }
        activeBrowserTab = tabName;
        if (tabName !== "googleplex") {
            googleplexRenderedViewKey = `tab:${tabName}`;
        }
        search.value = browserQueries[tabName] || "";
        updateBrowserChrome();
        updateBrowserNarrowMode();
        term.querySelectorAll('.browser-tab').forEach(button => {
            button.classList.toggle('is-active', button.dataset.browserTab === tabName);
        });
        const title = term.querySelector(`#${terminalId}-title`);
        if (tabName === "exchange") {
            title.textContent = "Ghost Exchange";
            search.placeholder = "Szukaj danych, kategorii rynku, zasobow...";
            loadExchange();
        } else if (tabName === "blacknet") {
            title.textContent = "BlackNet";
            renderBrowserWallet();
            search.placeholder = "Szukaj sygnalow, zrodel, ryzyka...";
            renderBlackNet();
        } else {
            title.innerHTML = '<span class="gp-brand-lockup"><img src="/static/images/googleplx/brand/googleplex-news-wordmark.svg" alt="Googleplex News"></span>';
            renderBrowserWallet();
            search.placeholder = "Szukaj aplikacji...  /all - pokaz wszystkie";
            renderCatalog();
        }
    }

    term.querySelectorAll('.browser-tab').forEach(button => {
        button.addEventListener('click', () => switchBrowserTab(button.dataset.browserTab || "googleplex"));
    });
    updateBrowserChrome();
    search.addEventListener('input', () => {
        browserQueries[activeBrowserTab] = search.value;
        if (activeBrowserTab === "exchange") {
            renderExchange();
        } else if (activeBrowserTab === "blacknet") {
            renderBlackNet();
        } else {
            renderCatalog();
        }
    });
    term.addEventListener('keydown', event => {
        if (activeBrowserTab !== "blacknet") return;
        if (event.target === search) return;
        if (event.key === "ArrowLeft" || event.key.toLowerCase() === "a") {
            event.preventDefault();
            stepBlacknetSignal(-1, "left");
        } else if (event.key === "ArrowRight" || event.key.toLowerCase() === "d") {
            event.preventDefault();
            stepBlacknetSignal(1, "right");
        } else if (event.key === "ArrowUp" || event.key.toLowerCase() === "w") {
            event.preventDefault();
            stepBlacknetSignal(-1, "up");
        } else if (event.key === "ArrowDown" || event.key.toLowerCase() === "s") {
            event.preventDefault();
            stepBlacknetSignal(1, "down");
        }
    });
    renderBrowserWallet();
    loadGoogleplexHome().catch(() => {});
}

function openWalletApp(options = {}) {
    const existing = document.querySelector(`.terminal[data-app="wallet"]`);
    if (existing) {
        if (options.to) {
            const recipientInput = existing.querySelector('[data-wallet-recipient]');
            if (recipientInput) recipientInput.value = options.to;
        }
        if (typeof bringWindowToFront === "function") {
            bringWindowToFront(existing);
        }
        return existing;
    }

    const term = document.createElement('div');
    term.className = 'terminal';
    term.dataset.app = "wallet";
    term.style.display = 'flex';
    term.style.flexDirection = 'column';
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `520px`;
    term.style.height = `560px`;

    term.innerHTML = `
        <div class="title-bar">
            Wallet HC
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div class="wallet-shell"></div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());
    renderWalletApp(term.querySelector('.wallet-shell'), options);
    return term;
}

function renderWalletApp(container, options = {}) {
    container.innerHTML = `
        <div class="wallet-header">
            <div>
                <div class="wallet-title">Wallet HC</div>
                <div class="wallet-subtitle">Lokalny portfel operatora</div>
            </div>
            <div class="wallet-balance" data-wallet-balance>Saldo: ... HC</div>
        </div>
        <div class="wallet-message" data-wallet-message></div>
        <form class="wallet-transfer-form" data-wallet-form>
            <label>
                <span>Odbiorca</span>
                <input data-wallet-recipient type="text" autocomplete="off" placeholder="username" value="${escapeHTML(String(options.to || ''))}">
            </label>
            <label>
                <span>Kwota HC</span>
                <input data-wallet-amount type="number" min="1" step="1" placeholder="50">
            </label>
            <label>
                <span>Notatka</span>
                <input data-wallet-note type="text" maxlength="240" placeholder="opcjonalnie">
            </label>
            <div class="wallet-actions">
                <button type="submit">Akceptuj</button>
                <button type="button" data-wallet-clear>Anuluj / Wyczysc</button>
            </div>
        </form>
        <div class="wallet-history">
            <div class="wallet-section-title">Historia</div>
            <div data-wallet-history class="wallet-history-list">
                <div class="wallet-empty">Ladowanie historii...</div>
            </div>
        </div>
    `;

    container.querySelector('[data-wallet-form]').addEventListener('submit', (event) => {
        event.preventDefault();
        submitWalletTransfer(container);
    });
    container.querySelector('[data-wallet-clear]').addEventListener('click', () => {
        container.querySelector('[data-wallet-amount]').value = "";
        container.querySelector('[data-wallet-note]').value = "";
        if (!options.to) {
            container.querySelector('[data-wallet-recipient]').value = "";
        }
        setWalletMessage(container, "", "");
    });
    loadWalletState(container);
}

function setWalletMessage(container, type, message) {
    const box = container.querySelector('[data-wallet-message]');
    if (!box) return;
    box.className = `wallet-message ${type ? `is-${type}` : ''}`;
    box.textContent = message || "";
}

async function loadWalletState(container = document.querySelector('.terminal[data-app="wallet"] .wallet-shell')) {
    if (!container) return null;
    setWalletMessage(container, "loading", "Synchronizacja portfela...");
    try {
        const res = await fetch('/api/wallet');
        const data = await res.json();
        if (!res.ok || data.error) {
            setWalletMessage(container, "error", data.error || "Nie udalo sie pobrac portfela.");
            return null;
        }
        container.querySelector('[data-wallet-balance]').textContent = `Saldo: ${Number(data.balance || 0)} ${data.currency || 'HC'}`;
        renderWalletHistory(container, data.ledger || data.transactions || []);
        setWalletMessage(container, "", "");
        return data;
    } catch (err) {
        console.warn('Wallet load failed', err);
        setWalletMessage(container, "error", "Brak polaczenia z portfelem.");
        return null;
    }
}

function renderWalletHistory(container, transactions) {
    const list = container.querySelector('[data-wallet-history]');
    if (!list) return;
    if (!transactions.length) {
        list.innerHTML = `<div class="wallet-empty">Brak historii HC.</div>`;
        return;
    }
    list.innerHTML = transactions.map(tx => {
        const ledgerDelta = Object.prototype.hasOwnProperty.call(tx, "amount_delta")
            ? Number(tx.amount_delta || 0)
            : null;
        const amount = ledgerDelta === null ? Number(tx.amount || 0) : Math.abs(ledgerDelta);
        const outgoing = ledgerDelta === null ? tx.type === "outgoing" : ledgerDelta < 0;
        const sign = outgoing ? "-" : "+";
        const typeLabel = tx.event_type
            ? String(tx.event_type).replace(/^wallet[_:.]?/, '').replace(/_/g, ' ')
            : (outgoing ? "wyslano" : "odebrano");
        const peer = tx.peer_username || tx.peer || tx.source || '';
        const balanceAfter = Object.prototype.hasOwnProperty.call(tx, "balance_after")
            ? `<span>saldo: ${Number(tx.balance_after || 0)} HC</span>`
            : '';
        return `
            <div class="wallet-transaction ${outgoing ? 'is-outgoing' : 'is-incoming'}">
                <div>
                    <strong>${escapeHTML(typeLabel)} ${sign}${amount} HC</strong>
                    <span>${escapeHTML(String(peer || 'system'))}</span>
                    ${balanceAfter}
                </div>
                <small>${escapeHTML(String(tx.created_at || ''))}</small>
                ${tx.note ? `<em>${escapeHTML(String(tx.note))}</em>` : ''}
            </div>
        `;
    }).join('');
}

function walletTransferScopeDigest(value) {
    let first = 0x811c9dc5;
    let second = 0x9e3779b9;
    for (const char of String(value || "")) {
        const code = char.codePointAt(0);
        first = Math.imul(first ^ code, 0x01000193);
        second = Math.imul(second ^ code, 0x85ebca6b);
    }
    return `${(first >>> 0).toString(16).padStart(8, "0")}${(second >>> 0).toString(16).padStart(8, "0")}`;
}

function walletTransferSessionScope() {
    const state = window.ChaosSessionGeneration?.getState?.() || {};
    const username = String(state.username || toolbarProfile?.username || "anonymous")
        .trim()
        .toLowerCase() || "anonymous";
    const sessionMarker = String(state.query_token || state.generation || "legacy-session").trim()
        || "legacy-session";
    // Keep the raw session generation out of the storage key while retaining
    // a stable user/session namespace inside this tab.
    return `${walletTransferScopeDigest(username)}:${walletTransferScopeDigest(sessionMarker)}`;
}

function walletTransferStorageKey() {
    return `chaos:wallet-transfer:v1:${walletTransferSessionScope()}`;
}

function newWalletTransferActionKey() {
    const randomPart = (window.crypto && typeof window.crypto.randomUUID === "function")
        ? window.crypto.randomUUID()
        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
    return `wallet-transfer:${randomPart}`;
}

function acquireWalletTransferAction(payload = {}, container = null) {
    const fingerprint = JSON.stringify({
        to: String(payload.to || "").trim(),
        amount: String(payload.amount ?? ""),
        note: String(payload.note || "").trim(),
    });
    const storageKey = walletTransferStorageKey();
    let key = "";

    if (
        container?.dataset?.walletTransferKey
        && container.dataset.walletTransferFingerprint === fingerprint
    ) {
        key = container.dataset.walletTransferKey;
    }

    if (!key) {
        try {
            const stored = JSON.parse(window.sessionStorage.getItem(storageKey) || "null");
            if (
                stored
                && stored.fingerprint === fingerprint
                && typeof stored.key === "string"
                && stored.key.startsWith("wallet-transfer:")
            ) {
                key = stored.key;
            }
        } catch (_err) {
            // sessionStorage can be unavailable or contain an obsolete record.
        }
    }

    if (!key) key = newWalletTransferActionKey();
    const action = { key, fingerprint, storageKey };
    if (container?.dataset) {
        container.dataset.walletTransferKey = key;
        container.dataset.walletTransferFingerprint = fingerprint;
    }
    try {
        window.sessionStorage.setItem(storageKey, JSON.stringify({
            version: 1,
            key,
            fingerprint,
        }));
    } catch (_err) {
        // The container-local receipt still protects retries before reload.
    }
    return action;
}

function clearWalletTransferActionKey(action = null, container = null) {
    const storageKey = action?.storageKey || walletTransferStorageKey();
    try {
        const stored = JSON.parse(window.sessionStorage.getItem(storageKey) || "null");
        if (!action || !stored || stored.key === action.key) {
            window.sessionStorage.removeItem(storageKey);
        }
    } catch (_err) {
        try {
            window.sessionStorage.removeItem(storageKey);
        } catch (_storageError) {
            // Storage can be unavailable in hardened/private contexts.
        }
    }
    if (container?.dataset && (!action || container.dataset.walletTransferKey === action.key)) {
        delete container.dataset.walletTransferKey;
        delete container.dataset.walletTransferFingerprint;
    }
}

async function submitWalletTransfer(container = document.querySelector('.terminal[data-app="wallet"] .wallet-shell')) {
    if (!container) return;
    const to = container.querySelector('[data-wallet-recipient]').value.trim();
    const amount = container.querySelector('[data-wallet-amount]').value;
    const note = container.querySelector('[data-wallet-note]').value.trim();

    if (!to) {
        setWalletMessage(container, "error", "Podaj odbiorce.");
        return;
    }
    if (!amount || Number(amount) <= 0) {
        setWalletMessage(container, "error", "Podaj dodatnia kwote HC.");
        return;
    }

    setWalletMessage(container, "loading", "Wysylanie przelewu...");
    const transferAction = acquireWalletTransferAction({ to, amount, note }, container);
    const transactionKey = transferAction.key;
    try {
        const res = await fetch('/api/wallet/transfer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Idempotency-Key': transactionKey
            },
            body: JSON.stringify({ to, amount, note, transaction_key: transactionKey })
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            setWalletMessage(container, "error", data.error || "Przelew odrzucony.");
            return;
        }
        container.querySelector('[data-wallet-amount]').value = "";
        container.querySelector('[data-wallet-note]').value = "";
        clearWalletTransferActionKey(transferAction, container);
        container.querySelector('[data-wallet-balance]').textContent = `Saldo: ${Number(data.balance || 0)} ${data.currency || 'HC'}`;
        renderWalletHistory(container, data.ledger || data.transactions || (data.transaction ? [data.transaction] : []));
        setWalletMessage(container, "success", "Przelew wykonany.");
        updateWalletBalanceView(data.balance, data.currency || "HC");
    } catch (err) {
        console.warn('Wallet transfer failed', err);
        setWalletMessage(container, "error", "Brak polaczenia z portfelem.");
    }
}

window.openWalletTransferTo = function(username) {
    if (!username) return false;
    openWalletApp({ to: username });
    return true;
};

function googleplexInstallActionKey(app = {}) {
    const appId = String(app.id || "app").trim() || "app";
    const storageKey = `chaos:googleplex-install:${appId}`;
    try {
        const existing = window.sessionStorage.getItem(storageKey);
        if (existing) return { key: existing, storageKey };
    } catch (_err) {
        // sessionStorage can be unavailable in hardened/private contexts.
    }
    const randomPart = (window.crypto && typeof window.crypto.randomUUID === "function")
        ? window.crypto.randomUUID()
        : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
    const key = `googleplex-install:${appId}:${randomPart}`;
    try {
        window.sessionStorage.setItem(storageKey, key);
    } catch (_err) {
        // The in-memory key still protects retries made by this install window.
    }
    return { key, storageKey };
}

function googleplexInstallErrorDetails(response, data = {}) {
    const httpStatus = Number(response?.status || 0);
    const reasonCode = String(data.reason_code || data.reason || data.error || "unknown_error").trim();
    const canonicalMessage = String(data.message || "").trim();
    let message = canonicalMessage;
    if (!message) {
        if (httpStatus === 401) message = "Sesja wygasla. Zaloguj sie ponownie.";
        else if (httpStatus === 409) message = "Zakup koliduje z aktualnym stanem konta. Odswiez dane i sprobuj ponownie.";
        else if (httpStatus === 422) message = "Dane produktu nie przeszly walidacji.";
        else if (httpStatus === 400) message = "Nie spelniono warunkow zakupu lub instalacji.";
        else message = "Nie udalo sie zakonczyc zakupu lub instalacji.";
    }
    return { httpStatus, reasonCode, message };
}

function applyGoogleplexTravelToOpenMaps(data = {}) {
    const travel = data.travel && typeof data.travel === "object" ? data.travel : null;
    const position = travel?.position && typeof travel.position === "object" ? travel.position : null;
    const lat = Number(position?.lat);
    const lng = Number(position?.lng);
    if (!travel || !Number.isFinite(lat) || !Number.isFinite(lng)) return false;
    const mapWasOpen = Boolean(document.querySelector(
        '.terminal[data-app="map"], .map-window iframe, iframe[src="/map"]'
    ));
    if (!mapWasOpen && typeof createMap === "function") {
        createMap();
    }
    notifyOpenMapsBlacknetFocus({
        mode: "teleport", source: "googleplex_travel", lat, lng,
        receipt: travel.receipt,
        position_version: travel.position_version,
        position_updated_at: travel.position_updated_at
    });
    return true;
}

function showInstallAppProgress(app, onInstalled = null, onSettled = null) {
    // Okno progressbar (symulacja jak instalator Windows/Linux)
    const steps = [
        `Rozpoczynanie instalacji aplikacji: ${app.name || 'aplikacja'}`,
        `Pobieranie plik\u00f3w...`,
        `Instalacja sk\u0142adnik\u00f3w...`,
        `Rejestracja aplikacji w systemie...`,
        `Finalizacja...`
    ];

    const appWindow = document.createElement('div');
    appWindow.className = 'app-window';
    const position = findAvailablePosition();
    appWindow.style.top = `${position.top}px`;
    appWindow.style.left = `${position.left}px`;
    appWindow.innerHTML = `
        <div class="title-bar">${escapeHTML(app.name || 'Aplikacja')} - Instalacja <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content">
            <div class="progress-log" style="font-family: monospace; font-size: 13px; margin-bottom: 10px;"></div>
            <div class="progress-bar" style="position: relative; height: 20px; background: #333;">
                <div class="progress-fill" style="background: #0f0; height: 100%; width: 0%; transition: width 0.2s;"></div>
            </div>
            <div class="result-msg" style="margin-top: 10px; font-weight: bold;"></div>
        </div>
    `;
    document.body.appendChild(appWindow);
    makeDraggable(appWindow);
    appWindow.querySelector('.close-btn').addEventListener('click', () => appWindow.remove());

    const fill = appWindow.querySelector('.progress-fill');
    const log = appWindow.querySelector('.progress-log');
    const result = appWindow.querySelector('.result-msg');
    let stepIndex = 0;
    const progressPerStep = 100 / steps.length;
    const installAction = googleplexInstallActionKey(app);

    function runNextStep() {
        if (stepIndex >= steps.length) {
            // Wysyłka do backendu na końcu
            fetch('/install-app', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Client-Action-Key': installAction.key
                },
                body: JSON.stringify({
                    app_id: app.id,
                    client_action_key: installAction.key
                })
            })
            .then(async response => ({ response, data: await response.json().catch(() => ({})) }))
            .then(({ response, data }) => {
                if (response.ok && data.status === "success") {
                    try {
                        window.sessionStorage.removeItem(installAction.storageKey);
                    } catch (_err) {
                        // A successful server receipt is authoritative.
                    }
                    const storage = data.storage || {};
                    const isProductPurchase = !!data.product;
                    const hasStorageInfo = storage && (
                        Object.prototype.hasOwnProperty.call(storage, "used")
                        || Object.prototype.hasOwnProperty.call(storage, "capacity")
                    );
                    const storageLine = hasStorageInfo
                        ? `<br><span style="color:#8fd6a4;">Dysk: ${escapeHTML(formatStorageSize(storage.used, storage.unit || 'MB'))} / ${escapeHTML(formatStorageSize(storage.capacity, storage.unit || 'MB'))}${storage.over_limit ? ' (ponad limit mi\u0119kki)' : ''}</span>`
                        : '';
                    result.innerHTML = `<span style="color:#0f0;">\u2714 ${isProductPurchase ? 'Produkt kupiony.' : 'Aplikacja zainstalowana.'}</span>${storageLine}`;
                    if (Object.prototype.hasOwnProperty.call(data, "hackcoins")) {
                        setToolbarProfile({
                            ...toolbarProfile,
                            hackcoins: data.hackcoins,
                            storage_capacity: storage.capacity ?? toolbarProfile?.storage_capacity,
                            storage_used: storage.used ?? toolbarProfile?.storage_used,
                            storage_unit: storage.unit || toolbarProfile?.storage_unit || 'MB',
                            storage_over_limit: storage.over_limit === true
                        });
                    }
                    applyGoogleplexTravelToOpenMaps(data);

                    // Zamykamy okno po 4 sekundach i przeładowujemy "pulpit"
                    setTimeout(async () => {
                        // Znajdź i usuń okno instalacji
                        if (appWindow && appWindow.parentNode) appWindow.parentNode.removeChild(appWindow);

                        if (typeof onInstalled === "function") {
                            await onInstalled(data);
                        }

                        if (!isProductPurchase && (Array.isArray(data.apps) || data.files)) {
                            await updateAppsView({
                                apps: data.apps || [],
                                files: data.files || {},
                                app: data.app || null,
                                app_id: app.id,
                                reason: "install_response"
                            });
                        }
                        if (typeof onSettled === "function") onSettled(true, data);
                    }, 4000);
                } else {
                    const diagnostic = googleplexInstallErrorDetails(response, data);
                    result.innerHTML = `<span style="color:#f33;">\u2716 ${escapeHTML(diagnostic.message)}</span>`;
                    addSystemMessage("danger", "Googleplex", diagnostic.message);
                    console.warn("Googleplex purchase/install rejected", {
                        http_status: diagnostic.httpStatus,
                        reason_code: diagnostic.reasonCode,
                        app_id: String(app.id || ""),
                        product_type: String(app.product_type || "app")
                    });
                    if (typeof onSettled === "function") onSettled(false, data);
                }
            })
            .catch(err => {
                result.innerHTML = `<span style="color:#f33;">\u2716 B\u0142\u0105d po\u0142\u0105czenia z serwerem.</span>`;
                if (typeof onSettled === "function") onSettled(false, { reason: "network_error" });
            });
            return;
        }

        log.innerHTML += `<div>\u23F1 ${escapeHTML(String(steps[stepIndex] || ''))}</div>`;
        fill.style.width = `${(stepIndex + 1) * progressPerStep}%`;

        stepIndex++;
        setTimeout(runNextStep, 900 + Math.random() * 700);
    }
    runNextStep();
}

async function refreshDesktop(closeWindows = true) {
    // 1. Czyść wszystkie ikony z pulpitu
    const desktop = document.getElementById('desktop-icons');
    if (desktop) desktop.innerHTML = '';

    // 2. Zamknij wszystkie okna (terminal, app-window, terminal*)
    if (closeWindows) {
        document.querySelectorAll('.terminal, .app-window').forEach(win => win.remove());
    }

    // 3. Pobierz najnowszy profil
    const profileData = await getUserProfile();
    if (!profileData) {
            addSystemMessage("danger", "\u{1F4C1} Profil", "\u2716 Brak danych profilu");
        return;
    }

    // 4. Zbuduj nowe ikony (logika z twojego async init)
    const jsonApps = profileData.apps || [];
    const generatedIcons = await buildIconsFromJsonWithCommand(jsonApps);

    // Połącz własne i systemowe aplikacje
    const allApps = [...generatedIcons, ...getSystemDesktopApps(profileData)];
    setToolbarLaunchers(allApps, profileData);
    applyDesktopSettings(profileData.desktop_settings || {});
    renderDesktopIcons(allApps, desktopSettings);
    return;

    // Od nowa rozmieść ikony na pulpicie
    const iconHeight = 100;
    const topOffset = 10;
    const leftOffset = 10;
    const colSpacing = 100;
    const windowHeight = window.innerHeight;
    const maxPerColumn = Math.floor((windowHeight - topOffset) / iconHeight);

    allApps.forEach((app, index) => {
        const icon = document.createElement('div');
        icon.className = 'icon';
        icon.innerHTML = `<span style="font-size: 3rem">${app.icon}</span> ${app.label}`;

        const row = index % maxPerColumn;
        const col = Math.floor(index / maxPerColumn);
        icon.style.top = `${topOffset + row * iconHeight}px`;
        icon.style.left = `${leftOffset + col * colSpacing}px`;

        icon.addEventListener('dblclick', app.action);

        // Drag & drop obsługa (skopiowana z twojego kodu)
        let isDragging = false;
        let offsetX = 0;
        let offsetY = 0;
        icon.addEventListener('mousedown', (e) => {
            isDragging = true;
            icon.style.zIndex = 999;
            offsetX = e.clientX - icon.offsetLeft;
            offsetY = e.clientY - icon.offsetTop;
            document.body.style.userSelect = 'none';
        });
        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            icon.style.left = `${e.clientX - offsetX}px`;
            icon.style.top = `${e.clientY - offsetY}px`;
        });
        window.addEventListener('mouseup', () => {
            isDragging = false;
            icon.style.zIndex = '';
            document.body.style.userSelect = 'auto';
        });

        desktop.appendChild(icon);
    });
}




function createSettings() {
    const existing = document.querySelector(`.terminal[data-app="settings"]`);
    if (existing) {
        bringWindowToFront(existing);
        return;
    }
    const term = document.createElement('div');
    term.className = 'terminal';
    term.dataset.app = "settings";
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `560px`;
    term.style.height = `620px`;
    term.style.maxWidth = `calc(100vw - 24px)`;
    term.style.maxHeight = `calc(100vh - 24px)`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';

    const wallpaperOptions = [
        { id: "wall-chaos-green", label: "Toxic Green", color: "#26ff6a" },
        { id: "wall-chaos-blue", label: "Blue Grid", color: "#35d7ff" },
        { id: "wall-chaos-red", label: "Red Alert", color: "#ff3b57" },
        { id: "wall-chaos-amber", label: "Amber Net", color: "#ffd34d" },
        { id: "wall-chaos-violet", label: "Violet Trace", color: "#b56cff" },
        { id: "wall-1", label: "Obraz 1", color: "#7dff3c" },
        { id: "wall-2", label: "Obraz 2", color: "#59d6ff" },
        { id: "wall-3", label: "Obraz 3", color: "#d18cff" },
    ];
    const mapSchemeOptions = [
        { id: "osm", label: "OSM", color: "#8bd37f" },
        { id: "carto_light", label: "Carto Light", color: "#d7e3da" },
        { id: "carto_dark", label: "Carto Dark", color: "#15202b" },
        { id: "opentopo", label: "OpenTopo", color: "#d6b46a" },
    ];
    const currentWallpaper = desktopSettings.wallpaper || "";
    const currentMapScheme = desktopSettings.map_tile_scheme || "osm";

    term.innerHTML = `
        <div class="title-bar">
            Ustawienia
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div class="settings-shell">
            <div class="settings-status" data-settings-status></div>

            <section class="settings-section">
                <div class="settings-section__header">
                    <h3>Ekran</h3>
                    <span>Tapeta pulpitu</span>
                </div>
                <div class="settings-wallpaper-grid">
                    <button type="button" class="settings-wallpaper is-none ${currentWallpaper ? '' : 'is-active'}" data-wall="">
                        <span class="settings-wallpaper__swatch"></span>
                        <b>Brak</b>
                    </button>
                    ${wallpaperOptions.map(option => `
                        <button type="button" class="settings-wallpaper ${currentWallpaper === option.id ? 'is-active' : ''}" data-wall="${escapeHTML(option.id)}">
                            <span class="settings-wallpaper__swatch" style="--wall-color:${escapeHTML(option.color)}"></span>
                            <b>${escapeHTML(option.label)}</b>
                        </button>
                    `).join("")}
                </div>
                <div class="settings-subblock">
                    <div class="settings-section__header settings-section__header--sub">
                        <h3>Mapa</h3>
                        <span>Schemat Leaflet</span>
                    </div>
                    <div class="settings-map-scheme-grid">
                        ${mapSchemeOptions.map(option => `
                            <button type="button" class="settings-map-scheme ${currentMapScheme === option.id ? 'is-active' : ''}" data-map-scheme="${escapeHTML(option.id)}" title="Schemat mapy: ${escapeHTML(option.label)}">
                                <span class="settings-map-scheme__swatch" style="--map-scheme-color:${escapeHTML(option.color)}"></span>
                                <b>${escapeHTML(option.label)}</b>
                            </button>
                        `).join("")}
                    </div>
                </div>
            </section>

            <section class="settings-section">
                <div class="settings-section__header">
                    <h3>Konto</h3>
                    <span>Haslo i adres e-mail</span>
                </div>
                <form class="settings-form" data-settings-password-form>
                    <label>
                        <span>Aktualne haslo</span>
                        <input type="password" autocomplete="current-password" data-current-password>
                    </label>
                    <label>
                        <span>Nowe haslo</span>
                        <input type="password" autocomplete="new-password" data-new-password placeholder="min. 8 znakow, litera i cyfra">
                    </label>
                    <button type="submit">Zmien haslo</button>
                </form>
                <form class="settings-form" data-settings-email-form>
                    <label>
                        <span>Adres e-mail</span>
                        <input type="email" autocomplete="email" data-settings-email placeholder="operator@chaos.net">
                    </label>
                    <button type="submit">Zapisz e-mail</button>
                </form>
            </section>

            <section class="settings-section">
                <div class="settings-section__header">
                    <h3>Radio</h3>
                    <span>Ghost Hack Radio</span>
                </div>
                <label class="settings-toggle">
                    <input type="checkbox" data-settings-radio-autoplay ${isGhostRadioAutoplayEnabled() ? 'checked' : ''}>
                    <span>Autostart radia po pierwszej interakcji</span>
                </label>
            </section>

            <section class="settings-section">
                <div class="settings-section__header">
                    <h3>Efekty dzwiekowe</h3>
                    <span>Game SFX</span>
                </div>
                <label class="settings-toggle">
                    <input type="checkbox" data-settings-sfx-enabled ${(!window.GameSfx || window.GameSfx.getState().enabled) ? 'checked' : ''}>
                    <span>Efekty gry i scen lore</span>
                </label>
                <label class="settings-sfx-volume">
                    <span>Glosnosc <b data-settings-sfx-volume-value>${Math.round((window.GameSfx ? window.GameSfx.getState().volume : 0.8) * 100)}%</b></span>
                    <input type="range" min="0" max="100" step="1" value="${Math.round((window.GameSfx ? window.GameSfx.getState().volume : 0.8) * 100)}" data-settings-sfx-volume>
                </label>
                <button type="button" class="settings-sfx-test" data-settings-sfx-test>Test Secret Path</button>
                <span class="settings-sfx-test-status" data-settings-sfx-test-status></span>
            </section>

            <section class="settings-section">
                <div class="settings-section__header">
                    <h3>Tryb ekranu</h3>
                    <span>Runtime gry</span>
                </div>
                <label class="settings-toggle">
                    <input type="checkbox" data-settings-auto-fullscreen ${isAutoFullscreenEnabled() ? 'checked' : ''}>
                    <span>Auto fullscreen po kliknieciu/tapnieciu w gre</span>
                </label>
            </section>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());
    bringWindowToFront(term);

    const status = term.querySelector('[data-settings-status]');
    const setStatus = (message, type = "") => {
        if (!status) return;
        status.textContent = message || "";
        status.className = `settings-status ${type ? `is-${type}` : ''}`;
    };

    term.querySelectorAll('[data-wall]').forEach(btn => {
        btn.addEventListener('click', () => {
            const wall = btn.dataset.wall || "";
            applyDesktopSettings({
                ...desktopSettings,
                wallpaper: wall
            });
            saveDesktopSettingsNow({ wallpaper: wall });
            term.querySelectorAll('[data-wall]').forEach(item => item.classList.toggle('is-active', item === btn));
            setStatus("Tapeta zapisana.", "success");
        });
    });

    term.querySelectorAll('[data-map-scheme]').forEach(btn => {
        btn.addEventListener('click', async () => {
            const mapTileScheme = btn.dataset.mapScheme || "osm";
            setStatus("Zapisuje schemat mapy...", "loading");
            const response = await postDesktopSettings({
                ...desktopSettings,
                map_tile_scheme: mapTileScheme
            });
            if (response && !response.ok) {
                setStatus("Nie udalo sie zapisac schematu mapy.", "error");
                return;
            }
            const savedSettings = response ? await response.json().catch(() => null) : null;
            if (savedSettings?.desktop_settings) {
                applyDesktopSettings(savedSettings.desktop_settings);
            } else {
                setStatus("Serwer nie potwierdzil schematu mapy.", "error");
                return;
            }
            const activeMapScheme = desktopSettings.map_tile_scheme || mapTileScheme;
            term.querySelectorAll('[data-map-scheme]').forEach(item => {
                item.classList.toggle('is-active', item.dataset.mapScheme === activeMapScheme);
            });
            reloadOpenMapWindowsForSettings();
            setStatus("Schemat mapy zapisany. Mapa zostala odswiezona.", "success");
        });
    });

    term.querySelector('[data-settings-radio-autoplay]')?.addEventListener('change', event => {
        setGhostRadioAutoplayEnabled(event.target.checked);
        setStatus(event.target.checked ? "Autostart radia wlaczony." : "Autostart radia wylaczony.", "success");
    });

    term.querySelector('[data-settings-sfx-enabled]')?.addEventListener('change', event => {
        if (window.GameSfx) window.GameSfx.setEnabled(event.target.checked);
        setStatus(event.target.checked ? "Efekty dzwiekowe wlaczone." : "Efekty dzwiekowe wylaczone.", "success");
    });

    term.querySelector('[data-settings-sfx-volume]')?.addEventListener('input', event => {
        const value = Math.max(0, Math.min(100, Number(event.target.value) || 0));
        if (window.GameSfx) window.GameSfx.setVolume(value / 100);
        const output = term.querySelector('[data-settings-sfx-volume-value]');
        if (output) output.textContent = `${Math.round(value)}%`;
    });

    term.querySelector('[data-settings-sfx-test]')?.addEventListener('click', async () => {
        const output = term.querySelector('[data-settings-sfx-test-status]');
        if (!window.GameSfx) {
            if (output) output.textContent = "Silnik SFX niedostepny.";
            return;
        }
        await window.GameSfx.unlock();
        const handle = window.GameSfx.play('secret_path.scene_06', {
            event_id: `settings-sfx-test:${Date.now()}`,
            source: 'settings'
        });
        const result = await handle.started;
        if (output) output.textContent = result.ok ? "Odtwarzanie testowe." : `Test: ${result.reason || 'brak audio'}.`;
    });

    term.querySelector('[data-settings-auto-fullscreen]')?.addEventListener('change', event => {
        setAutoFullscreenEnabled(event.target.checked);
        saveDesktopSettingsNow({ auto_fullscreen: event.target.checked });
        sendDesktopSettingsBeacon({ auto_fullscreen: event.target.checked });
        syncChaosFullscreenRuntime();
        setStatus(event.target.checked ? "Auto fullscreen wlaczony. Kliknij w gre, aby aktywowac." : "Auto fullscreen wylaczony.", "success");
        if (event.target.checked) {
            requestChaosFullscreen();
        } else if (document.fullscreenElement && typeof document.exitFullscreen === "function") {
            document.exitFullscreen().catch(() => {});
        }
    });

    term.querySelector('[data-settings-password-form]')?.addEventListener('submit', async event => {
        event.preventDefault();
        const currentPassword = term.querySelector('[data-current-password]')?.value || "";
        const newPassword = term.querySelector('[data-new-password]')?.value || "";
        setStatus("Zapisuje haslo...", "loading");
        try {
            const res = await fetch('/api/profile/account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok || data.success === false) throw new Error(data.error || "Nie udalo sie zmienic hasla.");
            term.querySelector('[data-current-password]').value = "";
            term.querySelector('[data-new-password]').value = "";
            setStatus("Haslo zmienione.", "success");
        } catch (err) {
            setStatus(err.message || "Nie udalo sie zmienic hasla.", "error");
        }
    });

    term.querySelector('[data-settings-email-form]')?.addEventListener('submit', async event => {
        event.preventDefault();
        const email = term.querySelector('[data-settings-email]')?.value || "";
        setStatus("Zapisuje e-mail...", "loading");
        try {
            const res = await fetch('/api/profile/account', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok || data.success === false) throw new Error(data.error || "Nie udalo sie zapisac e-maila.");
            setStatus("E-mail zapisany.", "success");
        } catch (err) {
            setStatus(err.message || "Nie udalo sie zapisac e-maila.", "error");
        }
    });

    getUserProfile().then(profile => {
        if (!profile) return;
        const input = term.querySelector('[data-settings-email]');
        if (input) input.value = profile.email || "";
    });
}

async function createProfile() {
    if (document.querySelector(`.terminal[data-app="profile"]`)) return;

    const term = document.createElement('div');
    term.className = 'terminal profile-window';
    term.dataset.app = "profile";
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `420px`;
    term.style.height = `580px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';

    term.innerHTML = `
        <div class="title-bar">
            Profil gracza
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div class="profile-content">
            <div class="app-load-panel profile-load-panel">
                <div class="app-load-panel__title">Ladowanie profilu...</div>
                <div class="app-load-panel__bar"><span></span></div>
                <div class="app-load-panel__text">Synchronizuje profil, terytorium i zabezpieczenia.</div>
            </div>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    const content = term.querySelector('.profile-content');
    const profileData = await getUserProfile();
    if (!profileData) {
        content.innerHTML = `<div class="profile-error">Brak danych profilu.</div>`;
        addSystemMessage("danger", "\u{1F4C1} Profil", "\u2716 Brak danych profilu");
        return;
    }

    const booleanSecurityEntries = Object.entries(profileData.security || {})
        .filter(([, value]) => typeof value === 'boolean');
    const securityControls = booleanSecurityEntries
        .map(([key, value]) => `
            <label class="profile-security-tile ${value ? 'is-on' : 'is-off'}" title="${escapeHTML(key)}">
                <input class="profile-security-toggle" type="checkbox" data-security-key="${escapeHTML(key)}" ${value ? 'checked' : ''}>
                <span class="profile-security-name">${escapeHTML(key)}</span>
                <span class="profile-security-state">${value ? 'ON' : 'OFF'}</span>
            </label>
        `)
        .join("");

    const territoryStats = profileData.territory_stats || {};
    const totalArea = Math.round(Number(territoryStats.total_area || 0));
    const effectiveArea = Math.round(Number(territoryStats.effective_area || totalArea));
    const nextLevelArea = Math.round(Number(territoryStats.next_level_area || 0));
    const areaToNext = Math.round(Number(territoryStats.area_to_next_level ?? Math.max(0, nextLevelArea - effectiveArea)));
    const densityMultiplier = Number(territoryStats.density_multiplier || 0);
    const spanDensity = Number(territoryStats.span_density || 0);
    const actionRange = Math.min(3000, Math.round(300 * Math.sqrt(Math.max(1, Number(profileData.level || 1)))));
    const factionNames = {
        "1": "Straznicy Ladu",
        "2": "Echo Wolnosci",
        "3": "VIREX",
        "4": "Siatka Widmo"
    };
    const rawPlayerClan = profileData.clan || (profileData.fraction && profileData.fraction.name) || "brak";
    const playerClan = factionNames[String(rawPlayerClan)] || rawPlayerClan;
    profileData.clan = playerClan;
    const appsCount = Array.isArray(profileData.apps)
        ? profileData.apps.length
        : (Array.isArray(profileData.inventory) ? profileData.inventory.length : 0);
    const currentPosition = profileData.curently_possition || profileData.current_position || {};
    const densityLabel = densityMultiplier > 0 && spanDensity > 0
        ? `x${densityMultiplier.toFixed(2)} (${spanDensity.toFixed(2)} przesel / 100 m)`
        : "brak danych / przeliczane";
    const nextLevelLabel = areaToNext > 0
        ? `${areaToNext} m2`
        : "brak aktywnego progu";
    const territoryDetailsHtml = `
            <p>Efektywna kontrola: <b>${effectiveArea} m2</b></p>
            <p>Gestosc siatki: <b>${densityLabel}</b></p>
    `;

    content.innerHTML = `
            <div class="profile-hero">
                <img class="profile-avatar" src="${escapeHTML(profileData.avatar || '')}" alt="Avatar">
                <h2>${escapeHTML(profileData.nick || profileData.username || 'Ghost')}</h2>
                <p>Poziom: <b>${profileData.level}</b></p>
            </div>

            <hr>

            <p>💰 HackCoiny: <b>${profileData.hackcoins}</b></p>
            <p>🔥 Respect: <b>${profileData.respect}</b> pkt</p>
            <p>👥 Klan: <b>${escapeHTML(profileData.clan)}</b></p>

            <hr>
            <h4>Terytorium:</h4>
            ${territoryDetailsHtml}
            <p>🟩 Klastry: <b>${territoryStats.clusters_count || 0}</b></p>
            <p>📐 Powierzchnia: <b>${totalArea} m2</b></p>
            <p>⬆ Do nastepnego levela: <b>${nextLevelLabel}</b></p>
            <p>🏍️ Zasieg motocykla: <b>${actionRange} m</b></p>

            <hr>

            <p>📦 Aplikacje: <b>${appsCount}</b></p>
            <p>📍 Pozycja: <b>lat: ${currentPosition.lat ?? '-'}, lng: ${currentPosition.lng ?? '-'}</b></p>

            <hr>
            <details class="profile-security-collapse">
                <summary>Zabezpieczenia</summary>
                <div class="profile-security-status"></div>
                <div class="profile-security-list">${securityControls || '<span class="profile-security-empty">Brak boolean security.</span>'}</div>
            </details>
    `;

    term.querySelectorAll('.profile-security-toggle').forEach(toggle => {
        toggle.addEventListener('change', async () => {
            const key = toggle.dataset.securityKey;
            const value = toggle.checked;
            const status = term.querySelector('.profile-security-status');
            status.textContent = 'Zapisywanie...';

            try {
                const res = await fetch('/api/profile/security', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key, value })
                });
                const data = await res.json();

                if (!res.ok || !data.success) {
                    throw new Error(data.error || 'Nie udalo sie zapisac.');
                }

                term.querySelectorAll('.profile-security-toggle').forEach(item => {
                    const itemKey = item.dataset.securityKey;
                    if (typeof data.security[itemKey] === 'boolean') {
                        item.checked = data.security[itemKey];
                        const row = item.closest('.profile-security-tile');
                        row.querySelector('.profile-security-state').textContent = item.checked ? 'ON' : 'OFF';
                        row.classList.toggle('is-on', item.checked);
                        row.classList.toggle('is-off', !item.checked);
                    }
                });

                status.textContent = data.changed_by_rules.length
                    ? `Reguly konfliktu wylaczyly: ${data.changed_by_rules.join(', ')}`
                    : 'Zapisano.';
            } catch (err) {
                toggle.checked = !value;
                status.textContent = err.message;
            }
        });
    });
}


async function getUserProfile() {
    if (!desktopSessionActive) return null;
    if (userProfileRequestPromise) return userProfileRequestPromise;
    const snapshotClientRequestedMs = Date.now();
    userProfileRequestPromise = (async () => {
        try {
            const res = await fetch('/api/profile');
            if (!desktopSessionActive) return null;
            if (res.status === 401) {
                desktopSessionActive = false;
                return null;
            }
            if (!res.ok) throw new Error(`Nieprawidłowy response (${res.status})`);
            const data = await res.json();
            if (!desktopSessionActive) return null;
            data.snapshot_client_requested_ms = snapshotClientRequestedMs;
            data.snapshot_client_received_ms = Date.now();
            // /api/profile is the authoritative player snapshot. The first
            // desktop request may fail or be delayed while the backend boots;
            // a later successful refresh must also repair the persistent
            // toolbar, not only the window that requested the profile.
            setToolbarProfile(data);
            return data;
        } catch (err) {
            console.error("❌ Błąd pobierania profilu użytkownika:", err);
            return null;
        } finally {
            userProfileRequestPromise = null;
        }
    })();
    return userProfileRequestPromise;
}

function rememberProcessedDelta(key) {
    if (!key) return false;
    if (processedDeltaKeys.has(key)) return true;
    processedDeltaKeys.add(key);
    if (processedDeltaKeys.size > 500) {
        const first = processedDeltaKeys.values().next().value;
        processedDeltaKeys.delete(first);
    }
    return false;
}

function updateWalletBalanceView(balance, currency = "HC") {
    const normalizedBalance = Number(balance || 0);
    setToolbarProfile({
        ...(toolbarProfile || {}),
        hackcoins: normalizedBalance
    });

    document.querySelectorAll('[data-wallet-balance]').forEach(node => {
        node.textContent = `Saldo: ${normalizedBalance} ${currency || 'HC'}`;
    });
    document.querySelectorAll('.googolplex-wallet').forEach(node => {
        node.textContent = `HackCoiny: ${normalizedBalance}`;
    });
}

function normalizeStorageDeltaPayload(payload = {}) {
    return {
        used: Number(payload.used || 0),
        capacity: Number(payload.capacity || 0),
        unit: payload.unit || 'MB',
        overLimit: payload.over_limit === true,
        softLimit: payload.soft_limit !== false
    };
}

function renderStorageMeterInner(summary) {
    const capacity = Math.max(1, Number(summary.capacity || 1));
    const used = Math.max(0, Number(summary.used || 0));
    const percent = Math.max(0, Math.min(100, Math.round((used / capacity) * 100)));
    const warning = summary.overLimit ? '<span class="file-manager-storage-warning">ponad limit miękki</span>' : '';
    return `
        <div class="file-manager-storage-top">
            <span>Dysk</span>
            <b data-storage-label>${escapeHTML(formatStorageSize(used, summary.unit))} / ${escapeHTML(formatStorageSize(summary.capacity, summary.unit))}</b>
        </div>
        <div class="file-manager-storage-bar"><span data-storage-fill style="width:${percent}%"></span></div>
        ${warning}
    `;
}

function updateStorageView(payload = {}) {
    const summary = normalizeStorageDeltaPayload(payload);
    setToolbarProfile({
        ...(toolbarProfile || {}),
        storage_capacity: summary.capacity,
        storage_used: summary.used,
        storage_unit: summary.unit,
        storage_over_limit: summary.overLimit,
        storage_soft_limit: summary.softLimit
    });

    document.querySelectorAll('.file-manager-storage[data-storage-meter]').forEach(node => {
        node.dataset.storageUsed = String(summary.used);
        node.dataset.storageCapacity = String(summary.capacity);
        node.dataset.storageUnit = summary.unit;
        node.dataset.storageOverLimit = summary.overLimit ? "1" : "0";
        node.innerHTML = renderStorageMeterInner(summary);
    });
}

async function rebuildDesktopAppsFromProfile(profilePatch = {}) {
    const baseProfile = {
        ...(toolbarProfile || {}),
        ...profilePatch
    };
    const jsonApps = Array.isArray(baseProfile.apps) ? baseProfile.apps : [];
    const generatedIcons = await buildIconsFromJsonWithCommand(jsonApps);
    const allApps = [...generatedIcons, ...getSystemDesktopApps(baseProfile)];
    setToolbarLaunchers(allApps, baseProfile);
    renderDesktopIcons(allApps, desktopSettings);
    return allApps;
}

function refreshOpenFileManagersForApps(payload = {}) {
    const filesPayload = payload.files && typeof payload.files === "object" ? payload.files : {};
    const tools = Array.isArray(filesPayload.tools) ? filesPayload.tools : null;
    const apps = Array.isArray(payload.apps) ? payload.apps : null;

    fileManagerInstances.forEach((state, terminalId) => {
        const container = document.getElementById(`${terminalId}-content`);
        if (!container) {
            fileManagerInstances.delete(terminalId);
            return;
        }
        if (tools) state.files.tools = tools;
        if (apps) {
            state.apps = apps;
            state.installedToolAppsByFile.clear();
            apps.forEach(app => {
                if (!app || typeof app !== "object") return;
                const appName = String(app.name || app.id || "").trim();
                const filename = String(app.file_name || app.project_file || (appName ? `${appName}.sh` : "")).trim();
                if (filename) state.installedToolAppsByFile.set(filename, app);
            });
        }
        if (state.currentFolder === "tools" && typeof window.openFolderInManager === "function") {
            window.openFolderInManager(terminalId, "tools");
        }
    });
}

async function updateAppsView(payload = {}) {
    const filesPayload = payload.files && typeof payload.files === "object" ? payload.files : null;
    const nextProfile = {
        ...(toolbarProfile || {})
    };
    if (Array.isArray(payload.apps)) nextProfile.apps = payload.apps;
    if (filesPayload) {
        nextProfile.files = {
            ...((toolbarProfile || {}).files || {}),
            ...filesPayload
        };
    }
    setToolbarProfile(nextProfile);
    await rebuildDesktopAppsFromProfile(nextProfile);
    refreshOpenFileManagersForApps(payload);
    try {
        window.dispatchEvent(new CustomEvent('chaos:apps-projection-updated', {
            detail: payload
        }));
    } catch (_error) {
        // A missing CustomEvent implementation must not block canonical UI refresh.
    }
}

function updateCybernerDeltaViews(payload = {}) {
    cybernerDeltaClients.forEach(client => {
        if (!client || typeof client.update !== "function" || (typeof client.isConnected === "function" && !client.isConnected())) {
            cybernerDeltaClients.delete(client);
            return;
        }
        client.update(payload);
    });
}

function cybernerSfxCurrentUsername() {
    return String((toolbarProfile || {}).username || "").trim().toLowerCase();
}

function cybernerSfxMessageId(payload = {}) {
    const message = payload.message && typeof payload.message === "object" ? payload.message : {};
    return String(payload.message_id || message.message_id || message.id || "").trim();
}

function playCybernerMessageSfx(payload = {}, options = {}) {
    if (!window.GameSfx || !payload || typeof payload !== "object") return false;
    const message = payload.message && typeof payload.message === "object" ? payload.message : {};
    const messageId = cybernerSfxMessageId(payload);
    if (!messageId) return false;
    const sender = String(message.sender || message.sender_username || payload.sender || "").trim().toLowerCase();
    const currentUser = cybernerSfxCurrentUsername();
    const own = options.own === true || (currentUser && sender === currentUser);
    const channelKey = String(payload.channel_key || payload.channel || message.channel_key || message.channel || "unknown");
    const timestamp = Date.now();
    if (!own) {
        const cooldownUntil = cybernerSfxChannelCooldowns.get(channelKey) || 0;
        if (cooldownUntil > timestamp) return false;
        cybernerSfxChannelCooldowns.set(channelKey, timestamp + 700);
    }
    window.GameSfx.play(own ? "cyberner.message_sent" : "cyberner.message_incoming", {
        event_id: `cyberner:${messageId}`,
        message_id: messageId,
        channel_key: channelKey,
        sender
    });
    return true;
}

function playSystemMessageSfx(message = {}) {
    if (!window.GameSfx || !message || typeof message !== "object") return false;
    const messageId = String(message.message_id || message.id || "").trim();
    if (!messageId) return false;
    const type = String(message.type || "").trim().toLowerCase();
    let eventKey = "";
    if (["critical", "danger", "error"].includes(type)) eventKey = "system.critical";
    else if (["warning", "warn"].includes(type)) eventKey = "system.warning";
    if (!eventKey) return false;
    window.GameSfx.play(eventKey, {
        event_id: `system:${messageId}`,
        message_id: messageId,
        message_type: type
    });
    return true;
}

function updateGhostExchangeDeltaViews(payload = {}) {
    ghostExchangeDeltaViews.forEach(view => {
        if (!view || typeof view.update !== "function" || (typeof view.isConnected === "function" && !view.isConnected())) {
            ghostExchangeDeltaViews.delete(view);
            return;
        }
        view.update(payload);
    });
}

function updateMapPlayerActorDeltaView(event = {}) {
    let applied = false;
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.applyMapPlayerActorDelta === "function") {
                mapWindow.applyMapPlayerActorDelta(event);
                applied = true;
            }
        } catch (err) {
            console.warn("Map player actor delta failed", err);
        }
    });
    return applied;
}

function updateMapTargetDeltaView(event = {}) {
    if (String(event.type || "") === "map.target_captured") {
        const payload = event.payload || {};
        playAuthoritativeCaptureSfx(payload.target || payload.captured_target || {});
    }
    let applied = false;
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.applyMapTargetDelta === "function") {
                mapWindow.applyMapTargetDelta(event);
                applied = true;
            }
        } catch (err) {
            console.warn("Map target delta failed", err);
        }
    });
    return applied;
}

function updateTerritoryDeltaView(event = {}) {
    if (String(event.type || "") === "territory.conflict_changed") {
        playAuthoritativeConflictResolvedSfx(event.payload || {});
    }
    let applied = false;
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.applyTerritoryDelta === "function") {
                applied = mapWindow.applyTerritoryDelta(event) || applied;
            }
        } catch (err) {
            console.warn("Territory delta failed", err);
        }
    });
    return applied;
}

function updateIncidentDeltaView(event = {}) {
    let applied = false;
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.applyIncidentDelta === "function") {
                applied = mapWindow.applyIncidentDelta(event) || applied;
            }
        } catch (err) {
            console.warn("Incident delta failed", err);
        }
    });
    return applied;
}

function updateResponseNpcDeltaView(event = {}) {
    let applied = false;
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.applyResponseNpcDelta === "function") {
                applied = mapWindow.applyResponseNpcDelta(event) || applied;
            }
        } catch (err) {
            console.warn("Response NPC delta failed", err);
        }
    });
    return applied;
}

function updateGhostNetworkDeltaView(event = {}) {
    if (window.GhostNetworkDeltaClient
            && typeof window.GhostNetworkDeltaClient.handle === "function") {
        return window.GhostNetworkDeltaClient.handle(event);
    }
    let applied = false;
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.applyGhostNetworkDelta === "function") {
                applied = mapWindow.applyGhostNetworkDelta(event) || applied;
            } else if (mapWindow && typeof mapWindow.applyGhostPartDelta === "function") {
                applied = mapWindow.applyGhostPartDelta(event) || applied;
            }
        } catch (err) {
            console.warn("GhostNetwork delta failed", err);
        }
    });
    return applied;
}

const GHOSTNETWORK_SFX_BY_EVENT = Object.freeze({
    "ghost.part_discovered": "ghostnetwork.part_discovered",
    "ghost.part_contained": "ghostnetwork.part_contained",
    "ghost.part_activated": "ghostnetwork.part_activated",
    "ghost.part_contested": "ghostnetwork.part_hostile",
    "ghost.part_revealed": "ghostnetwork.part_lost",
    "ghost.part_deactivated": "ghostnetwork.part_lost",
    "ghost.part_anchor_source_lost": "ghostnetwork.part_lost",
    "ghost.machine_progress_changed": "ghostnetwork.module_progress",
    "ghost.machine_online": "ghostnetwork.module_complete",
    "ghost.signal_sent": "ghostnetwork.signal"
});

function isGhostNetworkLifecycleSfxTransition(type, payload = {}) {
    const previousStatus = String(payload.previous_status || "").toLowerCase();
    const status = String(payload.status || "").toLowerCase();
    const previousConflict = String(payload.previous_conflict_state || "none").toLowerCase();
    const conflict = String(payload.conflict_state || "none").toLowerCase();
    if (type === "ghost.part_contained") {
        return status === "contained" && previousStatus !== "contained";
    }
    if (type === "ghost.part_activated") {
        return status === "active" && previousStatus !== "active";
    }
    if (type === "ghost.part_contested") {
        return conflict === "contested" && previousConflict !== "contested";
    }
    if (type === "ghost.part_revealed") {
        return status === "public" && previousStatus !== "public";
    }
    if (type === "ghost.part_deactivated") {
        return previousStatus === "active" && status !== "active";
    }
    return true;
}

function playGhostNetworkDeltaSfx(event = {}) {
    if (!stateDeltaSfxPlaybackAllowed || !window.GameSfx || typeof window.GameSfx.play !== "function") return false;
    const type = String(event.type || "");
    const eventKey = GHOSTNETWORK_SFX_BY_EVENT[type];
    if (!eventKey) return false;
    const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
    if (!isGhostNetworkLifecycleSfxTransition(type, payload)) return false;
    if (type === "ghost.machine_progress_changed"
        && Number(payload.active_parts || 0) === Number(payload.previous_active_parts || 0)) return false;
    const eventId = String(payload.event_id || event.dedupe_key || `${type}:${event.version || payload.state_version || ""}`).trim();
    window.GameSfx.play(eventKey, {
        event_id: `ghostnetwork:${eventId}`,
        source: "state_delta",
        cycle_id: payload.cycle_id || "",
        entity_id: event.entity_id || "",
        event_type: type
    });
    return true;
}

async function applyDelta(event) {
    if (!desktopSessionActive) return false;
    if (!event || typeof event !== "object") return false;
    const dedupeKey = event.dedupe_key || `${event.type || 'event'}:${event.version || ''}`;
    if (rememberProcessedDelta(dedupeKey)) return false;

    if (event.type === "wallet.balance_changed" || (event.scope === "wallet" && event.entity_id === "wallet")) {
        const payload = event.payload || {};
        updateWalletBalanceView(payload.balance, payload.currency || "HC");
        return true;
    }
    if (event.type === "storage.used_changed" || event.type === "storage.capacity_changed" || event.scope === "storage") {
        updateStorageView(event.payload || {});
        return true;
    }
    if (event.scope === "apps" || String(event.type || "").startsWith("apps.")) {
        await updateAppsView(event.payload || {});
        return true;
    }
    if (event.scope === "mail" || String(event.type || "").startsWith("mail.")) {
        if (event.type === "cyberner.message_created" && stateDeltaSfxPlaybackAllowed) {
            playCybernerMessageSfx(event.payload || {});
        }
        updateCybernerDeltaViews({ ...(event.payload || {}), delta_version: event.version || 0 });
        return true;
    }
    if (event.scope === "ghost_exchange" || String(event.type || "").startsWith("ghost_exchange.")) {
        updateGhostExchangeDeltaViews(event.payload || {});
        return true;
    }
    if (String(event.type || "").startsWith("map.player_")) {
        updateMapPlayerActorDeltaView(event);
        return true;
    }
    if (["map.target_updated", "map.target_captured", "map.target_removed"].includes(String(event.type || ""))) {
        updateMapTargetDeltaView(event);
        return true;
    }
    if (event.scope === "territory" || String(event.type || "").startsWith("territory.")) {
        updateTerritoryDeltaView(event);
        return true;
    }
    if (event.scope === "incident" || String(event.type || "").startsWith("incident.")) {
        updateIncidentDeltaView(event);
        if (typeof window.expireBlacknetIncidentSignals === "function") {
            window.expireBlacknetIncidentSignals(event);
        }
        return true;
    }
    if (event.scope === "npc" || String(event.type || "").startsWith("npc.")) {
        updateResponseNpcDeltaView(event);
        return true;
    }
    if (event.scope === "ghostnetwork" || String(event.type || "").startsWith("ghost.")) {
        playGhostNetworkDeltaSfx(event);
        updateGhostNetworkDeltaView(event);
        return true;
    }
    if (event.scope === "map") {
        updateMapPlayerActorDeltaView(event);
        updateMapTargetDeltaView(event);
        return true;
    }
    return false;
}

async function recoverProfileDeltaScopes(scopes) {
    const needsProfile = ["wallet", "profile", "storage", "apps"].some(scope => scopes.has(scope));
    if (!needsProfile) return null;
    const profile = await getUserProfile();
    if (!profile) return null;
    if (scopes.has("wallet") || scopes.has("profile")) {
        updateWalletBalanceView(profile.hackcoins, "HC");
    }
    if (scopes.has("storage") || scopes.has("profile")) {
        updateStorageView({
            used: profile.storage_used,
            capacity: profile.storage_capacity,
            unit: profile.storage_unit || "MB",
            over_limit: profile.storage_over_limit === true,
            soft_limit: profile.storage_soft_limit !== false
        });
    }
    if (scopes.has("apps") || scopes.has("profile")) {
        await updateAppsView({
            apps: profile.apps || [],
            files: {
                tools: ((profile.files || {}).tools || [])
            }
        });
    }
    return profile;
}

async function recoverMailDeltaScope() {
    const res = await fetch('/api/mail/bootstrap');
    if (!res.ok) return null;
    const data = await res.json();
    updateCybernerDeltaViews(data || {});
    return data;
}

async function recoverGhostExchangeDeltaScope() {
    const res = await fetch('/api/ghost-exchange');
    if (!res.ok) return null;
    const data = await res.json();
    if (data && data.success !== false) {
        updateGhostExchangeDeltaViews({
            summary: data.summary || {},
            sectors: data.sectors || [],
            recent_transactions: data.recent_transactions || [],
            history_7d: data.history_7d || []
        });
    }
    return data;
}

async function recoverMapDeltaScope() {
    let recovered = false;
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.refreshMapTargetSnapshot === "function") {
                mapWindow.refreshMapTargetSnapshot();
                recovered = true;
            }
            if (mapWindow && typeof mapWindow.refreshPlayerActors === "function") {
                mapWindow.refreshPlayerActors();
                recovered = true;
            }
        } catch (err) {
            console.warn("Map delta recovery failed", err);
        }
    });
    return recovered || null;
}

async function recoverTerritoryDeltaScope() {
    let recovered = false;
    const tasks = [];
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.refreshPlayerAreas === "function") {
                tasks.push(Promise.resolve(mapWindow.refreshPlayerAreas({ recovery: true, reason: "delta_recovery" })));
                recovered = true;
            }
        } catch (err) {
            console.warn("Territory delta recovery failed", err);
        }
    });
    if (tasks.length) {
        await Promise.allSettled(tasks);
    }
    return recovered || null;
}

async function recoverIncidentDeltaScope() {
    let recovered = false;
    const tasks = [];
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.refreshIncidentHotspots === "function") {
                tasks.push(Promise.resolve(mapWindow.refreshIncidentHotspots({ recovery: true, reason: "delta_recovery" })));
                recovered = true;
            }
        } catch (err) {
            console.warn("Incident delta recovery failed", err);
        }
    });
    if (tasks.length) {
        await Promise.allSettled(tasks);
    }
    return recovered || null;
}

async function recoverResponseNpcDeltaScope() {
    let recovered = false;
    const tasks = [];
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.refreshResponseNpcCapsules === "function") {
                tasks.push(Promise.resolve(mapWindow.refreshResponseNpcCapsules({ recovery: true, reason: "delta_recovery" })));
                recovered = true;
            }
        } catch (err) {
            console.warn("Response NPC delta recovery failed", err);
        }
    });
    if (tasks.length) {
        await Promise.allSettled(tasks);
    }
    return recovered || null;
}

async function recoverGhostNetworkDeltaScope() {
    let recovered = false;
    const tasks = [];
    document.querySelectorAll('.app-window[data-app="ghostnetwork-suite"]').forEach(app => {
        if (typeof app._ghostNetworkSuiteRecover !== "function") return;
        tasks.push(Promise.resolve(app._ghostNetworkSuiteRecover("state_delta_recovery")));
        recovered = true;
    });
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.recoverGhostNetworkLayer === "function") {
                tasks.push(Promise.resolve(mapWindow.recoverGhostNetworkLayer({ reason: "delta_recovery" })));
                recovered = true;
            } else if (mapWindow && typeof mapWindow.loadGhostNetworkSnapshot === "function") {
                tasks.push(Promise.resolve(mapWindow.loadGhostNetworkSnapshot({ recovery: true, reason: "delta_recovery" })));
                recovered = true;
            }
        } catch (err) {
            console.warn("GhostNetwork delta recovery failed", err);
        }
    });
    if (tasks.length) {
        await Promise.allSettled(tasks);
    }
    return recovered || null;
}

async function recoverDeltaScopes(recoveryScopes = [], currentVersion = null) {
    if (!desktopSessionActive) return false;
    const normalizedScopes = Array.isArray(recoveryScopes) && recoveryScopes.length
        ? recoveryScopes
        : STATE_DELTA_DEFAULT_RECOVERY_SCOPES;
    const scopes = new Set(normalizedScopes.map(scope => String(scope || "").trim()).filter(Boolean));

    const recoveryTasks = [];
    recoveryTasks.push(
        recoverProfileDeltaScopes(scopes).catch(err => {
            console.warn("Profile delta recovery failed", err);
            return null;
        })
    );
    if (scopes.has("mail")) {
        recoveryTasks.push(recoverMailDeltaScope().catch(err => {
            console.warn("Mail delta recovery failed", err);
            return null;
        }));
    }
    if (scopes.has("ghost_exchange")) {
        recoveryTasks.push(recoverGhostExchangeDeltaScope().catch(err => {
            console.warn("Ghost Exchange delta recovery failed", err);
            return null;
        }));
    }
    if (scopes.has("map")) {
        recoveryTasks.push(recoverMapDeltaScope().catch(err => {
            console.warn("Map delta recovery failed", err);
            return null;
        }));
    }
    if (scopes.has("territory")) {
        recoveryTasks.push(recoverTerritoryDeltaScope().catch(err => {
            console.warn("Territory delta recovery failed", err);
            return null;
        }));
    }
    if (scopes.has("incident")) {
        recoveryTasks.push(recoverIncidentDeltaScope().catch(err => {
            console.warn("Incident delta recovery failed", err);
            return null;
        }));
    }
    if (scopes.has("npc")) {
        recoveryTasks.push(recoverResponseNpcDeltaScope().catch(err => {
            console.warn("Response NPC delta recovery failed", err);
            return null;
        }));
    }
    if (scopes.has("ghostnetwork")) {
        recoveryTasks.push(recoverGhostNetworkDeltaScope().catch(err => {
            console.warn("GhostNetwork delta recovery failed", err);
            return null;
        }));
    }
    await Promise.all(recoveryTasks);
    if (!desktopSessionActive) return false;
    if (Number.isFinite(Number(currentVersion))) {
        stateDeltaVersion = Math.max(stateDeltaVersion, Number(currentVersion));
    }
    return true;
}

async function pollStateChanges() {
    if (!desktopSessionActive || stateDeltaPollInFlight) return;
    stateDeltaPollInFlight = true;
    try {
        const params = new URLSearchParams({
            since: String(stateDeltaVersion || 0),
            limit: String(STATE_DELTA_LIMIT)
        });
        const res = await fetchDesktopBackground(
            `/api/state/changes?${params.toString()}`,
            {},
            STATE_DELTA_FETCH_TIMEOUT_MS
        );
        if (!desktopSessionActive) return;
        if (res.status === 401) {
            desktopSessionActive = false;
            return;
        }
        if (!res.ok) {
            stateDeltaSfxCatchup = true;
            return;
        }
        const data = await res.json();
        if (!desktopSessionActive) return;
        if (data.recovery_required) {
            stateDeltaSfxCatchup = true;
            await recoverDeltaScopes(data.recovery_scopes || [], data.current_version);
            if (!desktopSessionActive) return;
            stateDeltaSfxLive = true;
            stateDeltaSfxCatchup = false;
            return;
        }
        const changes = Array.isArray(data.changes) ? data.changes : [];
        stateDeltaSfxPlaybackAllowed = stateDeltaSfxLive && !stateDeltaSfxCatchup;
        try {
            for (const change of changes) {
                await applyDelta(change);
                if (!desktopSessionActive) return;
                if (Number.isFinite(Number(change.version))) {
                    stateDeltaVersion = Math.max(stateDeltaVersion, Number(change.version));
                }
            }
        } finally {
            stateDeltaSfxPlaybackAllowed = false;
        }
        if (!desktopSessionActive) return;
        if (Number.isFinite(Number(data.current_version))) {
            stateDeltaVersion = Math.max(stateDeltaVersion, Number(data.current_version));
        }
        stateDeltaSfxLive = true;
        stateDeltaSfxCatchup = false;
    } catch (err) {
        if (isExpectedFetchAbort(err)) {
            hackFlowDebug(window.__lastHackFlowId || "", "desktop", "state_delta_timeout", {
                timeout_ms: STATE_DELTA_FETCH_TIMEOUT_MS,
                since: stateDeltaVersion || 0
            });
        } else {
            stateDeltaSfxCatchup = true;
            console.warn("Delta feed poll failed", err);
        }
    } finally {
        stateDeltaPollInFlight = false;
    }
}

function createAppForgeLegacy() {
    if (document.querySelector(`.terminal[data-app="appforge"]`)) return;

    const term = document.createElement('div');
    term.className = 'terminal';
    term.dataset.app = "appforge";
    const position = findAvailablePosition(560, 560);
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `560px`;
    term.style.height = `620px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';

    term.innerHTML = `
        <div class="title-bar">
            AppForge
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <form class="appforge-form">
            <div class="appforge-grid">
                <label>Nazwa<input name="name" maxlength="32" required placeholder="np. NullTrace"></label>
                <label>Typ<input name="type" value="scanner" placeholder="scanner"></label>
                <label>Ikonka
                    <span class="appforge-icon-row">
                        <input name="icon" maxlength="16" value="\u{1F6E0}\uFE0F" placeholder="\u{1F6E0}\uFE0F">
                        <span class="appforge-icon-preview">\u{1F6E0}\uFE0F</span>
                    </span>
                </label>
                <label>Cena<input name="price" type="number" min="0" step="1" value="100"></label>
                <label>Interface
                    <select name="interface">
                        <option value="progressbar_random">progressbar_random</option>
                        <option value="window">window</option>
                        <option value="terminal">terminal</option>
                        <option value="button_choices">button_choices</option>
                    </select>
                </label>
            </div>
            <label>Opis<textarea name="description" rows="3" placeholder="Co robi aplikacja?"></textarea></label>
            <label>Wymaga OFF<textarea name="requires_off" rows="2" placeholder="np. firewall, scan_detection"></textarea></label>
            <label>Zmienia w celu<textarea name="interferes_with" rows="2" placeholder="np. stealth_mode, vpn_enabled"></textarea></label>
            <label>Wykrywa<textarea name="detects" rows="2" placeholder="np. open_ports, user_location"></textarea></label>
            <label>Efekty gracza<textarea name="affects" rows="2" placeholder="np. traceability"></textarea></label>
            <div class="appforge-level-fields"></div>
            <button class="appforge-submit" type="submit">Publikuj w Googleplex</button>
            <div class="appforge-status"></div>
        </form>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    const iconInput = term.querySelector('input[name="icon"]');
    const iconPreview = term.querySelector('.appforge-icon-preview');
    iconInput.value = '\u{1F6E0}\uFE0F';
    iconPreview.textContent = iconInput.value;
    iconInput.addEventListener('input', () => {
        iconPreview.textContent = iconInput.value.trim() || '\u{1F6E0}\uFE0F';
    });

    const interfaceSelect = term.querySelector('select[name="interface"]');
    const levelFields = term.querySelector('.appforge-level-fields');
    const renderLevelFields = () => {
        const selected = interfaceSelect.value;
        if (selected === "window") {
            levelFields.innerHTML = `
                <h4>Levels: window</h4>
                <label>levels[0].title<input name="level_title" placeholder="Panel aplikacji"></label>
                <label>levels[0].list<textarea name="window_list" rows="4" placeholder="Jedna linia = jeden wpis listy"></textarea></label>
                <label>levels[0].buttons<textarea name="window_buttons" rows="3" placeholder="Label|action&#10;Uruchom modul|run_generated"></textarea></label>
            `;
        } else if (selected === "terminal") {
            levelFields.innerHTML = `
                <h4>Levels: terminal</h4>
                <label>levels[0].command<input name="terminal_command" placeholder="./tool.sh --target current"></label>
                <label>levels[0].logs<textarea name="terminal_logs" rows="5" placeholder="Jedna linia = jeden log terminala"></textarea></label>
            `;
        } else if (selected === "button_choices") {
            levelFields.innerHTML = `
                <h4>Levels: button_choices</h4>
                <label>levels[0].title<input name="level_title" placeholder="Wybierz tryb dzia\u0142ania"></label>
                <label>levels[0].text<textarea name="button_text" rows="3" placeholder="Opis wyboru dla gracza"></textarea></label>
                <label>levels[0].options<textarea name="button_options" rows="5" placeholder="Label|effect|price&#10;Recon|risk_level=10,access_level=1|90&#10;Disable firewall|firewall=false|140"></textarea></label>
            `;
        } else {
            levelFields.innerHTML = `
                <h4>Levels: progressbar_random</h4>
                <label>levels[0].title<input name="level_title" placeholder="Wykonywanie operacji"></label>
                <label>levels[0].steps<textarea name="progress_steps" rows="5" placeholder="Jedna linia = jeden krok progressbara"></textarea></label>
                <label>levels[0].result_success<input name="result_success" placeholder="Operacja zako\u0144czona powodzeniem."></label>
                <label>levels[0].result_failure<input name="result_failure" placeholder="Operacja zablokowana."></label>
            `;
        }
    };
    interfaceSelect.addEventListener('change', renderLevelFields);
    renderLevelFields();

    term.querySelector('.appforge-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const status = term.querySelector('.appforge-status');
        const formData = new FormData(form);
        const payload = Object.fromEntries(formData.entries());
        payload.price = Number(payload.price || 0);
        if (!validateGeneratedAppNameForScripts(payload, status)) return;
        status.textContent = 'Publikowanie...';

        try {
            const res = await fetch('/api/apps/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.message || 'Nie udalo sie opublikowac.');
            }
            status.textContent = `${data.message} Projekt zapisany w files/projects/${data.app.project_file}`;
            form.reset();
        } catch (err) {
            status.textContent = err.message;
        }
    });
}

async function createAppForge() {
    if (document.querySelector(`.terminal[data-app="appforge"]`)) return;

    const keys = await getCreatorSecurityKeys();
    const term = creatorBaseWindow('AppForge', 'progressbar_random');
    const form = term.querySelector('.appforge-form');
    appendCreatorMeta(form, keys, 'progressbar_random');
    form.querySelector('.creator-interface-slot').insertAdjacentHTML('beforeend', `
        <div class="appforge-level-fields">
            <h4>levels[0]</h4>
            <label>title<input name="level_title" placeholder="MemoryOverflow - Przepelnienie pamieci"></label>
            <div class="creator-items" data-kind="progress-steps"></div>
            <button type="button" class="appforge-submit add-progress-step">Dodaj krok</button>
            <label>result_success<input name="result_success" placeholder="Operacja zakonczona powodzeniem."></label>
            <label>result_failure<input name="result_failure" placeholder="Operacja zablokowana."></label>
        </div>
    `);

    const progressSteps = term.querySelector('[data-kind="progress-steps"]');
    const addProgressStep = (value = '') => {
        progressSteps.insertAdjacentHTML('beforeend', `
            <label>step<input class="creator-progress-step" value="${escapeHTML(value)}" placeholder="Wysylanie danych testowych..."></label>
        `);
    };
    term.querySelector('.add-progress-step').addEventListener('click', () => addProgressStep());
    addProgressStep();

    wireCreatorSubmit(term, (root) => ({
        progress_steps: Array.from(root.querySelectorAll('.creator-progress-step'))
            .map(input => input.value)
            .filter(Boolean)
    }));
    wireCreatorWizard(term);
    wireCreatorPreview(term);
}

async function getCreatorSecurityKeys() {
    const profileData = await getUserProfile();
    return Object.entries((profileData && profileData.security) || {})
        .filter(([, value]) => typeof value !== 'object')
        .map(([key]) => key);
}

function creatorCheckboxGroup(keys, fieldName) {
    return `
        <div class="appforge-check-grid" data-appforge-field="${fieldName}">
            ${keys.map(key => `
                <label class="appforge-check creator-toggle" data-state="off">
                    <input type="checkbox" value="${escapeHTML(key)}">
                    <span class="creator-toggle-state">OFF</span>
                    <span class="creator-toggle-label">${escapeHTML(creatorSecurityLabel(key))}</span>
                </label>
            `).join("")}
        </div>
    `;
}

function creatorSecurityLabel(key) {
    const labels = {
        firewall: "Firewall celu",
        firewall_core: "Rdzeń firewalla",
        scan_detection: "Wykrywanie skanowania",
        network_anomaly_detection: "Detekcja anomalii sieci",
        vpn: "Tunel VPN",
        camera_guardian: "Ochrona kamery",
        audio_guardian: "Ochrona audio"
    };
    if (labels[key]) return labels[key];
    return String(key || '')
        .split('_').join(' ')
        .replace(/\b\w/g, letter => letter.toUpperCase());
}

const CREATOR_WIZARD_STEPS = [
    "Nazwa",
    "Rodzina",
    "Cel",
    "Start",
    "Dzialanie",
    "Informacje",
    "Ryzyko",
    "Podglad",
    "Publikacja"
];

const CREATOR_STEP_NARRATIVE = [
    {
        title: "Nadaj narz\u0119dziu to\u017csamo\u015b\u0107",
        subtitle: "Pierwszy sygnal dla gracza i katalogu Googleplex.",
        description: "Nazwa, ikona i opis mowia, czym jest aplikacja zanim ktokolwiek spojrzy w jej kontrakt.",
        educational_note: "Profesjonalne narz\u0119dzia tej klasy s\u0105 rozpoznawalne po celu, zakresie i wiarygodnym opisie.",
        gameplay_hint: "Cena jest punktem startu. Runtime moze pokazac sugerowana wartosc w podgladzie balansu."
    },
    {
        title: "Wybierz rodzin\u0119 narz\u0119dzia",
        subtitle: "Rodzina zawedza dalsze decyzje.",
        description: "Scanner / Recon obejmuje tak\u017ce namierzanie celu (trace). Exploit i Sniffer pozostaj\u0105 osobnymi rodzinami gameplayowymi.",
        educational_note: "Administratorzy i zespoly bezpieczenstwa uzywaja podobnych klas rozwiazan do rozpoznania, kontroli i obserwacji systemow.",
        gameplay_hint: "Dla akcji mapy Namierz cel wybierz Scanner / Recon / Namierzanie, typ Tracer / tracker oraz dzia\u0142anie Namierz cel (trace)."
    },
    {
        title: "Wskaz obiekt zainteresowania",
        subtitle: "Cel decyduje, jakie opcje maja sens.",
        description: "Inaczej projektuje si\u0119 narz\u0119dzie dla pojazdu, inaczej dla kamery, a inaczej dla routera.",
        educational_note: "W swiecie CHAOS kazdy obiekt ma inne cyfrowe zmysly: lokalizacje, obraz, sygnal, logi albo dostep.",
        gameplay_hint: "Po wyborze celu kreator ukrywa niepasujace operacje i informacje."
    },
    {
        title: "Okresl miejsce uruchomienia",
        subtitle: "Mapa, desktop albo oba tryby.",
        description: "Nie ka\u017cde narz\u0119dzie musi by\u0107 widoczne w menu mapy. Desktop mo\u017ce dzia\u0142a\u0107 na oznaczony cel.",
        educational_note: "To rozr\u00f3\u017cnienie przypomina prac\u0119 z kontekstem: czasem dzia\u0142asz na obiekcie w terenie, czasem na ju\u017c wybranym celu.",
        gameplay_hint: "Tryb desktopowy moze nie miec akcji mapy. Tryb mapowy powinien miec jawne map_actions."
    },
    {
        title: "Zdecyduj, co narz\u0119dzie ma zrobi\u0107",
        subtitle: "To jest serce kontraktu operacji.",
        description: "Wybierasz efekt gameplayowy: sledzenie, stream, odczyt, zaklocenie albo implant.",
        educational_note: "Nie chodzi o realne komendy. Chodzi o opis skutku w symulowanym swiecie gry.",
        gameplay_hint: "Operacja moze zyc na mapie, miec timer, produkowac dane albo tylko wspierac inny proces."
    },
    {
        title: "Wybierz informacje, ktorych szuka",
        subtitle: "Dane sa paliwem ekonomii CHAOS.",
        description: "Zasoby okreslaja, jaki typ pliku albo stanu moze powstac po operacji.",
        educational_note: "Podobne klasy narz\u0119dzi w realnym \u015bwiecie pomagaj\u0105 zrozumie\u0107, jakie sygna\u0142y i metadane istniej\u0105 w systemach.",
        gameplay_hint: "Nie ka\u017cdy zas\u00f3b jest sprzedawalny. `internal_recon_state` mo\u017ce tylko przygotowa\u0107 dalsze dzia\u0142anie."
    },
    {
        title: "Ustal ryzyko i zaleznosci",
        subtitle: "Ka\u017cde narz\u0119dzie ma \u015blady i wymagania.",
        description: "Ten krok opisuje, z czym narz\u0119dzie koliduje, co wy\u0142\u0105cza i jakie warunki powinny by\u0107 spe\u0142nione.",
        educational_note: "\u015awiadome projektowanie narz\u0119dzia polega te\u017c na rozumieniu ogranicze\u0144, nie tylko mo\u017cliwo\u015bci.",
        gameplay_hint: "To nadal sa pola kontraktu gry. Nie tworza realnych instrukcji ani nowego systemu ryzyka."
    },
    {
        title: "Sprawdz kontrakt przed publikacja",
        subtitle: "Podglad laczy decyzje w jedna aplikacje.",
        description: "Tutaj widzisz, jak wyb\u00f3r rodziny, celu, dzia\u0142ania i danych zamienia si\u0119 w app contract.",
        educational_note: "Dobry projekt narz\u0119dzia powinien by\u0107 czytelny bez zagl\u0105dania w kod.",
        gameplay_hint: "Waga, jakosc, niezawodnosc i cena sugerowana sa liczone przez runtime."
    },
    {
        title: "Opublikuj w Googleplex",
        subtitle: "Ten sam katalog, ten sam runtime.",
        description: "Publikacja uzywa istniejacego endpointu i trafia do tego samego Googleplexa co inne aplikacje.",
        educational_note: "CHAOS traktuje narz\u0119dzie jak element ekosystemu: projekt, publikacja, instalacja, u\u017cycie i uninstall.",
        gameplay_hint: "Po publikacji aplikacj\u0119 kupujesz i instalujesz tak jak inne narz\u0119dzia."
    }
];

const CREATOR_TOOL_TYPES = [
    ["scanner", "Scanner / recon"],
    ["exploit", "Exploit"],
    ["exploit_suite", "Exploit suite"],
    ["sniffer", "Sniffer"],
    ["tracker", "Tracer / namierzanie celu"],
    ["camera_tool", "Camera tool"],
    ["atm_tool", "ATM tool"],
    ["vehicle_tool", "Vehicle tool"],
    ["custom", "Custom"]
];

const CREATOR_MAP_ACTION_OPTIONS = [
    "scan_ports",
    "exploit",
    "sniff",
    "trace",
    "trace_gps",
    "trace_device",
    "camera_stream",
    "camera_shutdown",
    "atm_logs",
    "install_sniffer",
    "scan_hotspots",
    "audio_hack",
    "car_hack"
];

const CREATOR_OPERATION_OPTIONS = [
    "generic_trace",
    "vehicle_tracking",
    "device_tracking",
    "microphone_sniffer",
    "camera_stream",
    "camera_shutdown",
    "atm_log_extraction",
    "persistent_sniffer",
    "wifi_scanner",
    "audio_interference",
    "vehicle_ecu"
];

const CREATOR_RESOURCE_OPTIONS = [
    "internal_recon_state",
    "gps_logs",
    "location_history",
    "device_logs",
    "personal_records",
    "financial_records",
    "credentials",
    "email_accounts",
    "call_history",
    "messenger_data",
    "audio_transcript",
    "camera_dump",
    "video_material",
    "atm_dump",
    "vehicle_diagnostics",
    "wifi_networks",
    "hotspot_database"
];

const CREATOR_TARGET_TYPE_OPTIONS = [
    "poi",
    "camera",
    "atm",
    "server",
    "router",
    "player",
    "pillar",
    "vehicle",
    "person",
    "phone",
    "venue"
];

const CREATOR_OPTION_LABELS = {
    map_actions: {
        scan_ports: "Przeskanuj porty",
        exploit: "Zainstaluj exploit",
        sniff: "Sledz ruch",
        trace: "Namierz cel",
        trace_gps: "Sledz pojazd GPS",
        trace_device: "Sledz urzadzenie",
        camera_stream: "Ogl\u0105daj obraz z kamery",
        camera_shutdown: "Zakloc kamere",
        atm_logs: "Odczytaj logi ATM",
        install_sniffer: "Zainstaluj implant",
        scan_hotspots: "Szukaj hotspotow",
        audio_hack: "Zakloc audio",
        car_hack: "Diagnozuj ECU"
    },
    operation_types: {
        generic_trace: "Sledzenie celu",
        vehicle_tracking: "Sledzenie pojazdu",
        device_tracking: "Sledzenie urzadzenia",
        microphone_sniffer: "Nasluch mikrofonu",
        camera_stream: "Monitoring kamery",
        camera_shutdown: "Czasowe wylaczenie kamery",
        atm_log_extraction: "Odczyt logow ATM",
        persistent_sniffer: "Implant sieciowy",
        wifi_scanner: "Rozpoznanie sieci",
        audio_interference: "Zaklocenie audio",
        vehicle_ecu: "Diagnostyka ECU"
    },
    resource_types: {
        internal_recon_state: "Stan rozpoznania",
        gps_logs: "Logi GPS",
        location_history: "Historia lokalizacji",
        device_logs: "Logi urzadzenia",
        personal_records: "Dane osobowe",
        financial_records: "Rekordy finansowe",
        credentials: "Dane dostepowe",
        email_accounts: "Konta e-mail",
        call_history: "Historia polaczen",
        messenger_data: "Dane komunikatora",
        audio_transcript: "Transkrypcja audio",
        camera_dump: "Dump kamery",
        video_material: "Material wideo",
        atm_dump: "Dump ATM",
        vehicle_diagnostics: "Diagnostyka pojazdu",
        wifi_networks: "Sieci Wi-Fi",
        hotspot_database: "Baza hotspotow"
    },
    target_types: {
        poi: "Obiekt w swiecie",
        camera: "Kamera",
        atm: "ATM",
        server: "Serwer",
        router: "Router",
        player: "Gracz",
        pillar: "Filar konfliktu",
        vehicle: "Pojazd",
        person: "Osoba",
        phone: "Telefon",
        venue: "Miejsce"
    }
};

const CREATOR_OPTION_GROUPS = {
    map_actions: "Akcja mapy",
    operation_types: "Operacja runtime",
    resource_types: "Informacja",
    target_types: "Cel"
};

const CREATOR_SEMANTIC_GROUPS = {
    location: ["gps_logs", "location_history", "generic_trace", "vehicle_tracking", "device_tracking", "trace", "trace_gps", "trace_device"],
    device: ["internal_recon_state", "device_logs", "vehicle_diagnostics", "wifi_networks", "hotspot_database", "scan_ports", "scan_hotspots", "car_hack", "vehicle_ecu", "wifi_scanner"],
    media: ["audio_transcript", "camera_dump", "video_material", "call_history", "messenger_data", "mic_sniff", "camera_stream", "camera_shutdown", "audio_hack", "microphone_sniffer", "audio_interference"],
    accounts: ["credentials", "email_accounts", "personal_records", "player", "person", "phone"],
    finance: ["financial_records", "atm_dump", "atm", "atm_logs", "atm_log_extraction"],
    access: ["exploit", "sniff", "install_sniffer", "persistent_sniffer"],
    world: ["poi", "camera", "server", "router", "pillar", "vehicle", "venue"]
};

const CREATOR_SEMANTIC_GROUP_LABELS = {
    location: "Lokalizacja i śledzenie",
    device: "Urządzenia i sieć",
    media: "Media i komunikacja",
    accounts: "Konta i tożsamość",
    finance: "Finanse",
    access: "Dostęp i wpływ",
    world: "Obiekty świata"
};

function creatorSemanticGroup(fieldName, key) {
    const matched = Object.entries(CREATOR_SEMANTIC_GROUPS)
        .find(([, keys]) => keys.includes(key));
    return matched ? CREATOR_SEMANTIC_GROUP_LABELS[matched[0]] : CREATOR_OPTION_GROUPS[fieldName];
}

const CREATOR_OPTION_ICONS = {
    scan_ports: "🛠️", exploit: "💥", sniff: "📡", trace: "📍",
    camera: "📷", atm: "🏧", server: "🖥️", router: "📶",
    player: "👤", pillar: "📍", vehicle: "🏍️", person: "👤",
    phone: "📱", venue: "🏢", poi: "📍"
};

const CREATOR_OPTION_KEYS = {
    map_actions: CREATOR_MAP_ACTION_OPTIONS,
    operation_types: CREATOR_OPERATION_OPTIONS,
    resource_types: CREATOR_RESOURCE_OPTIONS,
    target_types: CREATOR_TARGET_TYPE_OPTIONS
};

const CREATOR_OPTION_CATALOG = Object.freeze(Object.fromEntries(
    Object.entries(CREATOR_OPTION_KEYS).map(([fieldName, options]) => [
        fieldName,
        Object.freeze(options.map(key => {
            const label = (CREATOR_OPTION_LABELS[fieldName] || {})[key] || key;
            return Object.freeze({
                key,
                label,
                icon: CREATOR_OPTION_ICONS[key] || "◇",
                description: `${CREATOR_OPTION_GROUPS[fieldName]}: ${label}.`,
                group: creatorSemanticGroup(fieldName, key),
                constraints: Object.freeze({ serialized_value: key })
            });
        }))
    ])
));

function creatorOptionDescriptor(fieldName, key) {
    return (CREATOR_OPTION_CATALOG[fieldName] || []).find(item => item.key === key) || {
        key,
        label: key,
        icon: "◇",
        description: `Opcja kontraktu: ${key}.`,
        group: CREATOR_OPTION_GROUPS[fieldName] || "Kontrakt",
        constraints: { serialized_value: key }
    };
}

const CREATOR_TARGET_FILTERS = {
    poi: {
        map_actions: ["scan_ports", "exploit", "sniff", "trace", "camera_stream", "camera_shutdown", "install_sniffer", "audio_hack"],
        operation_types: ["generic_trace", "wifi_scanner", "persistent_sniffer", "microphone_sniffer", "camera_stream", "camera_shutdown", "audio_interference"],
        resource_types: ["internal_recon_state", "device_logs", "location_history", "credentials", "audio_transcript", "camera_dump", "video_material"]
    },
    pillar: {
        map_actions: ["scan_ports", "exploit", "sniff", "trace", "install_sniffer"],
        operation_types: ["generic_trace", "wifi_scanner", "persistent_sniffer"],
        resource_types: ["internal_recon_state", "device_logs", "location_history", "credentials"]
    },
    vehicle: {
        map_actions: ["trace_gps", "trace", "car_hack", "scan_ports"],
        operation_types: ["vehicle_tracking", "generic_trace", "vehicle_ecu"],
        resource_types: ["gps_logs", "location_history", "vehicle_diagnostics", "internal_recon_state"]
    },
    camera: {
        map_actions: ["camera_stream", "camera_shutdown", "scan_ports", "exploit"],
        operation_types: ["camera_stream", "camera_shutdown", "generic_trace"],
        resource_types: ["camera_dump", "video_material", "internal_recon_state"]
    },
    atm: {
        map_actions: ["atm_logs", "install_sniffer", "scan_ports", "sniff", "exploit"],
        operation_types: ["atm_log_extraction", "persistent_sniffer", "wifi_scanner"],
        resource_types: ["atm_dump", "financial_records", "credentials", "internal_recon_state"]
    },
    router: {
        map_actions: ["scan_ports", "scan_hotspots", "install_sniffer", "sniff", "exploit"],
        operation_types: ["wifi_scanner", "persistent_sniffer", "generic_trace"],
        resource_types: ["wifi_networks", "hotspot_database", "credentials", "device_logs", "internal_recon_state"]
    },
    server: {
        map_actions: ["scan_ports", "install_sniffer", "sniff", "exploit", "trace"],
        operation_types: ["persistent_sniffer", "generic_trace", "wifi_scanner"],
        resource_types: ["credentials", "device_logs", "financial_records", "internal_recon_state"]
    },
    person: {
        map_actions: ["trace_device", "trace", "mic_sniff", "sniff"],
        operation_types: ["device_tracking", "microphone_sniffer", "generic_trace"],
        resource_types: ["location_history", "device_logs", "audio_transcript", "personal_records", "internal_recon_state"]
    },
    phone: {
        map_actions: ["trace_device", "trace", "sniff"],
        operation_types: ["device_tracking", "generic_trace"],
        resource_types: ["location_history", "device_logs", "call_history", "messenger_data", "internal_recon_state"]
    },
    player: {
        map_actions: ["trace_device", "trace", "scan_ports", "sniff", "exploit"],
        operation_types: ["device_tracking", "generic_trace", "persistent_sniffer"],
        resource_types: ["location_history", "device_logs", "personal_records", "credentials", "internal_recon_state"]
    },
    venue: {
        map_actions: ["scan_hotspots", "trace", "mic_sniff", "scan_ports"],
        operation_types: ["wifi_scanner", "generic_trace", "microphone_sniffer"],
        resource_types: ["wifi_networks", "hotspot_database", "audio_transcript", "internal_recon_state"]
    }
};

const CREATOR_ACTION_FILTERS = {
    scan_ports: {
        operation_types: ["wifi_scanner", "generic_trace"],
        resource_types: ["internal_recon_state", "device_logs", "wifi_networks", "hotspot_database"]
    },
    trace: {
        operation_types: ["generic_trace", "vehicle_tracking", "device_tracking"],
        resource_types: ["location_history", "gps_logs", "device_logs", "personal_records", "internal_recon_state"]
    },
    trace_gps: {
        operation_types: ["vehicle_tracking", "generic_trace"],
        resource_types: ["gps_logs", "location_history", "vehicle_diagnostics", "internal_recon_state"]
    },
    trace_device: {
        operation_types: ["device_tracking", "generic_trace"],
        resource_types: ["location_history", "device_logs", "call_history", "messenger_data", "internal_recon_state"]
    },
    scan_hotspots: {
        operation_types: ["wifi_scanner", "generic_trace"],
        resource_types: ["wifi_networks", "hotspot_database", "internal_recon_state"]
    },
    exploit: {
        operation_types: ["persistent_sniffer", "camera_shutdown", "audio_interference", "vehicle_ecu"],
        resource_types: ["internal_recon_state", "credentials", "device_logs", "vehicle_diagnostics"]
    },
    camera_shutdown: {
        operation_types: ["camera_shutdown"],
        resource_types: ["internal_recon_state", "camera_dump", "video_material"]
    },
    audio_hack: {
        operation_types: ["audio_interference"],
        resource_types: ["internal_recon_state", "audio_transcript"]
    },
    car_hack: {
        operation_types: ["vehicle_ecu"],
        resource_types: ["internal_recon_state", "vehicle_diagnostics"]
    },
    sniff: {
        operation_types: ["persistent_sniffer", "microphone_sniffer", "generic_trace"],
        resource_types: ["credentials", "device_logs", "call_history", "messenger_data", "internal_recon_state"]
    },
    mic_sniff: {
        operation_types: ["microphone_sniffer"],
        resource_types: ["audio_transcript", "device_logs", "internal_recon_state"]
    },
    atm_logs: {
        operation_types: ["atm_log_extraction", "persistent_sniffer"],
        resource_types: ["atm_dump", "financial_records", "internal_recon_state"]
    },
    install_sniffer: {
        operation_types: ["persistent_sniffer"],
        resource_types: ["credentials", "device_logs", "financial_records", "internal_recon_state"]
    },
    camera_stream: {
        operation_types: ["camera_stream"],
        resource_types: ["camera_dump", "video_material", "internal_recon_state"]
    }
};

const CREATOR_SCANNER_MODE_PRESETS = {
    map: {
        label: "Scanner mapowy",
        description: "Rozpoznanie uruchamiane z mapy na konkretny obiekt.",
        map_actions: ["scan_ports", "trace", "trace_gps", "trace_device", "scan_hotspots", "camera_stream"],
        operation_types: ["generic_trace", "vehicle_tracking", "device_tracking", "wifi_scanner", "camera_stream"],
        resource_types: ["internal_recon_state", "gps_logs", "location_history", "device_logs", "camera_dump", "wifi_networks", "hotspot_database"],
        target_types: ["poi", "camera", "server", "router", "player", "pillar", "vehicle", "person", "phone", "venue"]
    },
    desktop: {
        label: "Scanner desktopowy na oznaczony cel",
        description: "Rozpoznanie odpalane z pulpitu na aktualny aimed_target.",
        map_actions: [],
        operation_types: ["generic_trace", "device_tracking", "wifi_scanner"],
        resource_types: ["internal_recon_state", "location_history", "device_logs", "wifi_networks", "hotspot_database"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "person", "phone", "venue"]
    },
    hybrid: {
        label: "Scanner hybrydowy",
        description: "Narz\u0119dzie recon dzia\u0142aj\u0105ce z mapy i z desktopu, bez wchodzenia w \u015bcie\u017ck\u0119 exploit/sniffer.",
        map_actions: ["scan_ports", "trace", "trace_gps", "trace_device", "scan_hotspots", "camera_stream"],
        operation_types: ["generic_trace", "vehicle_tracking", "device_tracking", "wifi_scanner", "camera_stream"],
        resource_types: ["internal_recon_state", "gps_logs", "location_history", "device_logs", "camera_dump", "wifi_networks", "hotspot_database"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "person", "phone", "venue"]
    }
};

const CREATOR_EXPLOIT_MODE_PRESETS = {
    map: {
        label: "Exploit mapowy",
        description: "Symulowane wykorzystanie s\u0142abo\u015bci celu uruchamiane z mapy w \u015bwiecie gry.",
        map_actions: ["exploit", "camera_shutdown", "install_sniffer", "audio_hack", "car_hack"],
        operation_types: ["camera_shutdown", "persistent_sniffer", "audio_interference", "vehicle_ecu"],
        resource_types: ["internal_recon_state", "financial_records", "credentials", "vehicle_diagnostics"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "venue"]
    },
    desktop: {
        label: "Exploit desktopowy na oznaczony cel",
        description: "Symulowany wp\u0142yw na aktualny aimed_target bez automatycznego podpinania do menu mapy.",
        map_actions: [],
        operation_types: ["camera_shutdown", "audio_interference", "vehicle_ecu"],
        resource_types: ["internal_recon_state", "vehicle_diagnostics"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "venue"]
    },
    hybrid: {
        label: "Exploit hybrydowy",
        description: "Narz\u0119dzie dzia\u0142aj\u0105ce z mapy i desktopu, nadal w ramach symulowanego \u015bwiata CHAOS.",
        map_actions: ["exploit", "camera_shutdown", "install_sniffer", "audio_hack", "car_hack"],
        operation_types: ["camera_shutdown", "persistent_sniffer", "audio_interference", "vehicle_ecu"],
        resource_types: ["internal_recon_state", "financial_records", "credentials", "vehicle_diagnostics"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "venue"]
    }
};

const CREATOR_SNIFFER_MODE_PRESETS = {
    map: {
        label: "Sniffer mapowy",
        description: "Symulowane zbieranie sygna\u0142\u00f3w lub danych przez operacj\u0119 uruchamian\u0105 z mapy.",
        map_actions: ["sniff", "mic_sniff", "atm_logs", "install_sniffer", "camera_stream"],
        operation_types: ["persistent_sniffer", "microphone_sniffer", "atm_log_extraction", "camera_stream"],
        resource_types: ["credentials", "financial_records", "atm_dump", "audio_transcript", "camera_dump", "video_material", "device_logs", "internal_recon_state"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "person", "phone", "venue"]
    },
    desktop: {
        label: "Sniffer desktopowy na oznaczony cel",
        description: "Symulowany podgl\u0105d sygna\u0142\u00f3w aktualnego aimed_target bez obowi\u0105zkowego menu mapy.",
        map_actions: [],
        operation_types: ["persistent_sniffer", "microphone_sniffer", "atm_log_extraction", "camera_stream"],
        resource_types: ["credentials", "financial_records", "atm_dump", "audio_transcript", "camera_dump", "video_material", "device_logs", "internal_recon_state"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "person", "phone", "venue"]
    },
    hybrid: {
        label: "Sniffer hybrydowy",
        description: "Narz\u0119dzie obserwacji dzia\u0142aj\u0105ce z mapy i z desktopu w ramach operacji gry.",
        map_actions: ["sniff", "mic_sniff", "atm_logs", "install_sniffer", "camera_stream"],
        operation_types: ["persistent_sniffer", "microphone_sniffer", "atm_log_extraction", "camera_stream"],
        resource_types: ["credentials", "financial_records", "atm_dump", "audio_transcript", "camera_dump", "video_material", "device_logs", "internal_recon_state"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "person", "phone", "venue"]
    }
};

const CREATOR_TOOL_FAMILY_PRESETS = {
    scanner_recon: {
        label: "Scanner / Recon / Namierzanie",
        boxTitle: "Gdzie dzia\u0142a rozpoznanie lub namierzanie?",
        defaultType: "scanner",
        allowedTypes: ["scanner", "tracker"],
        safetyText: "Ta rodzina obejmuje skanowanie oraz tracer mapowy. Dla Namierz cel ustaw typ Tracer / namierzanie celu, akcj\u0119 trace i operacj\u0119 generic_trace.",
        desktopMapNote: "Scanner desktopowy mo\u017ce nie mie\u0107 akcji mapy. Dzia\u0142a na aktualny aimed_target.",
        mapNote: "Cztery podstawowe akcje mapy to scan_ports, exploit, sniff i trace. W tej rodzinie utworzysz scan_ports albo Namierz cel (trace).",
        modes: CREATOR_SCANNER_MODE_PRESETS
    },
    exploit: {
        label: "Exploit",
        boxTitle: "Gdzie dzia\u0142a exploit?",
        defaultType: "exploit",
        allowedTypes: ["exploit", "exploit_suite", "camera_tool", "atm_tool", "vehicle_tool"],
        safetyText: "Exploit w CHAOS oznacza symulowany wp\u0142yw na s\u0142abo\u015b\u0107 systemu w \u015bwiecie gry. Opisuj efekt gameplayowy, nie technik\u0119.",
        desktopMapNote: "Exploit desktopowy mo\u017ce nie mie\u0107 akcji mapy. Dzia\u0142a na aktualny aimed_target.",
        mapNote: "Wybierz akcje mapy tylko wtedy, gdy narz\u0119dzie ma by\u0107 widoczne w menu mapy.",
        modes: CREATOR_EXPLOIT_MODE_PRESETS
    },
    sniffer: {
        label: "Sniffer",
        boxTitle: "Gdzie dzia\u0142a sniffer?",
        defaultType: "sniffer",
        allowedTypes: ["sniffer"],
        safetyText: "Sniffer w CHAOS oznacza symulowan\u0105 obserwacj\u0119 sygna\u0142\u00f3w lub danych w ramach operacji gry.",
        desktopMapNote: "Sniffer desktopowy mo\u017ce nie mie\u0107 akcji mapy. Dzia\u0142a na aktualny aimed_target.",
        mapNote: "Wybierz akcje mapy tylko wtedy, gdy sniffer ma by\u0107 uruchamiany z mapy.",
        modes: CREATOR_SNIFFER_MODE_PRESETS
    }
};

function creatorOptionCheckboxGroup(options, fieldName) {
    const groups = [];
    options.forEach(option => {
        const item = creatorOptionDescriptor(fieldName, option);
        let group = groups.find(entry => entry.label === item.group);
        if (!group) {
            group = { label: item.group, items: [] };
            groups.push(group);
        }
        group.items.push(item);
    });
    return `
        <div class="appforge-check-grid creator-contract-grid" data-appforge-field="${fieldName}">
            ${groups.map(group => `
                <section class="creator-option-group" data-creator-option-group="${escapeHTML(group.label)}">
                    <h5>${escapeHTML(group.label)}</h5>
                    ${group.items.map(item => `
                <label class="appforge-check creator-toggle" data-state="off" data-creator-option="${escapeHTML(item.key)}" title="${escapeHTML(item.description)}">
                    <input type="checkbox" value="${escapeHTML(item.key)}">
                    <span class="creator-toggle-state">OFF</span>
                    <span class="creator-toggle-icon" aria-hidden="true">${escapeHTML(item.icon)}</span>
                    <span class="creator-toggle-label">${escapeHTML(item.label)}</span>
                </label>
                    `).join("")}
                </section>
            `).join("")}
        </div>
    `;
}

function creatorWizardNavHtml() {
    return `
        <div class="creator-wizard-nav" role="tablist">
            ${CREATOR_WIZARD_STEPS.map((label, index) => `
                <button type="button" role="tab" class="creator-wizard-tab${index === 0 ? " active" : ""}" data-creator-step="${index}">
                    <span>${index + 1}</span>${escapeHTML(label)}
                </button>
            `).join("")}
        </div>
    `;
}

function creatorStepNarrativeHtml(index) {
    const item = CREATOR_STEP_NARRATIVE[index] || {};
    return `
        <div class="creator-step-narrative">
            <span class="creator-step-kicker">${escapeHTML(item.subtitle || '')}</span>
            <h4>${escapeHTML(item.title || '')}</h4>
            <p>${escapeHTML(item.description || '')}</p>
            <small>${escapeHTML(item.educational_note || '')}</small>
            <em>${escapeHTML(item.gameplay_hint || '')}</em>
        </div>
    `;
}

function syncCreatorToggle(input) {
    const toggle = input && input.closest('.creator-toggle');
    if (!toggle) return;
    const enabled = Boolean(input.checked);
    toggle.dataset.state = enabled ? 'on' : 'off';
    toggle.setAttribute('aria-checked', enabled ? 'true' : 'false');
    const state = toggle.querySelector('.creator-toggle-state');
    if (state) state.textContent = enabled ? 'ON' : 'OFF';
}

function wireCreatorWizard(term) {
    const form = term.querySelector('.appforge-form');
    if (!form) return;
    const tabs = Array.from(form.querySelectorAll('[data-creator-step]'));
    const panels = Array.from(form.querySelectorAll('[data-creator-panel]'));
    const wizardId = `creator-wizard-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    tabs.forEach((tab, index) => {
        tab.id = `${wizardId}-tab-${index}`;
        tab.setAttribute('aria-controls', `${wizardId}-panel-${index}`);
    });
    panels.forEach(panel => {
        const index = Number(panel.dataset.creatorPanel);
        panel.id = `${wizardId}-panel-${index}`;
        panel.setAttribute('aria-labelledby', `${wizardId}-tab-${index}`);
        if (!panel.querySelector('.creator-step-narrative')) {
            panel.insertAdjacentHTML('afterbegin', creatorStepNarrativeHtml(index));
        }
    });
    polishCreatorWizardLabels(term);
    form.querySelectorAll('.creator-toggle input[type="checkbox"]').forEach(input => {
        input.addEventListener('change', () => syncCreatorToggle(input));
        syncCreatorToggle(input);
    });
    form.addEventListener('reset', () => setTimeout(() => {
        form.querySelectorAll('.creator-toggle input[type="checkbox"]').forEach(syncCreatorToggle);
    }, 0));
    const setStep = (step) => {
        const nextStep = Math.max(0, Math.min(panels.length - 1, Number(step) || 0));
        tabs.forEach(tab => {
            const active = Number(tab.dataset.creatorStep) === nextStep;
            tab.classList.toggle('active', active);
            tab.setAttribute('aria-selected', active ? 'true' : 'false');
            tab.tabIndex = active ? 0 : -1;
        });
        panels.forEach(panel => {
            const active = Number(panel.dataset.creatorPanel) === nextStep;
            panel.hidden = !active;
            panel.setAttribute('role', 'tabpanel');
            panel.setAttribute('aria-hidden', active ? 'false' : 'true');
        });
    };
    tabs.forEach(tab => {
        tab.addEventListener('click', () => setStep(tab.dataset.creatorStep));
        tab.addEventListener('keydown', event => {
            const current = tabs.indexOf(tab);
            let next = null;
            if (event.key === 'ArrowRight' || event.key === 'ArrowDown') next = (current + 1) % tabs.length;
            if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') next = (current - 1 + tabs.length) % tabs.length;
            if (event.key === 'Home') next = 0;
            if (event.key === 'End') next = tabs.length - 1;
            if (next === null) return;
            event.preventDefault();
            setStep(next);
            tabs[next].focus();
        });
    });
    form.addEventListener('creator:goto-step', event => setStep(event.detail && event.detail.step));
    form.querySelectorAll('[data-creator-next]').forEach(button => {
        button.addEventListener('click', () => {
            const current = panels.findIndex(panel => !panel.hidden);
            setStep(current + 1);
        });
    });
    form.querySelectorAll('[data-creator-prev]').forEach(button => {
        button.addEventListener('click', () => {
            const current = panels.findIndex(panel => !panel.hidden);
            setStep(current - 1);
        });
    });
    setStep(0);
}

function creatorPanelNav(previous = true, next = true) {
    return `
        <div class="creator-panel-nav">
            ${previous ? '<button type="button" class="appforge-submit" data-creator-prev>Wstecz</button>' : '<span></span>'}
            ${next ? '<button type="button" class="appforge-submit" data-creator-next>Dalej</button>' : ''}
        </div>
    `;
}

function polishCreatorWizardLabels(term) {
    const familySelect = term.querySelector('[name="tool_family"]');
    if (familySelect?.parentElement) {
        familySelect.parentElement.childNodes[0].textContent = "Jaki rodzaj narz\u0119dzia chcesz stworzy\u0107? ";
    }
    const typeSelect = term.querySelector('[name="type"]');
    if (typeSelect?.parentElement) {
        typeSelect.parentElement.childNodes[0].textContent = "Jak ma byc opisane w katalogu? ";
    }
    const detects = term.querySelector('[name="detects"]');
    if (detects?.parentElement) {
        detects.parentElement.childNodes[0].textContent = "Jakie \u015blady lub sygna\u0142y rozpoznaje? ";
        detects.placeholder = "np. otwarte us\u0142ugi, ruch celu";
    }
    const panelHeadings = [
        ["0", ""],
        ["1", ""],
        ["2", ""],
        ["3", ""],
        ["4", ""],
        ["5", ""],
        ["6", ""],
        ["7", ""],
        ["8", ""]
    ];
    panelHeadings.forEach(([panelId, text]) => {
        const heading = term.querySelector(`[data-creator-panel="${panelId}"] > h4`);
        if (heading && text) heading.textContent = text;
        if (heading && !text) heading.remove();
    });
    const friendlyFieldsets = [
        ['[data-creator-panel="2"] .appforge-fieldset h4', "Jakim obiektem chcesz si\u0119 zaj\u0105\u0107?"],
        ['[data-creator-panel="3"] .appforge-fieldset h4', "Sk\u0105d gracz ma uruchamia\u0107 narz\u0119dzie?"],
        ['[data-creator-panel="4"] .appforge-fieldset h4', "Co ma zrobi\u0107 Twoje narz\u0119dzie?"],
        ['[data-creator-panel="5"] .appforge-fieldset h4', "Jakich informacji ma szuka\u0107?"],
        ['[data-creator-panel="6"] .appforge-fieldset:nth-of-type(1) h4', "Z czym mo\u017ce kolidowa\u0107?"],
        ['[data-creator-panel="6"] .appforge-fieldset:nth-of-type(2) h4', "Co powinno by\u0107 wy\u0142\u0105czone?"],
        ['[data-creator-panel="6"] .appforge-fieldset:nth-of-type(3) h4', "Co narz\u0119dzie potrafi wy\u0142\u0105czy\u0107?"],
        ['[data-creator-panel="6"] .appforge-fieldset:nth-of-type(4) h4', "Na co wp\u0142ywa po stronie gracza?"]
    ];
    friendlyFieldsets.forEach(([selector, text]) => {
        const item = term.querySelector(selector);
        if (item) item.textContent = text;
    });
}

function updateCreatorContractPreview(term) {
    const preview = term.querySelector('[data-creator-contract-preview]');
    if (!preview) return;
    const form = term.querySelector('.appforge-form');
    const collect = (fieldName) => Array.from(
        term.querySelectorAll(`[data-appforge-field="${fieldName}"] input:checked`)
    ).map(input => input.value);
    const payload = {
        name: form?.querySelector('[name="name"]')?.value || '',
        icon: form?.querySelector('[name="icon"]')?.value || '',
        tool_family: form?.querySelector('[name="tool_family"]')?.value || 'custom',
        tool_mode: form?.querySelector('[name="tool_mode"]')?.value || '',
        interface: form?.querySelector('input[name="interface"]')?.value || '',
        type: form?.querySelector('[name="type"]')?.value || '',
        map_actions: collect("map_actions"),
        target_types: collect("target_types"),
        operation_types: collect("operation_types"),
        resource_types: collect("resource_types"),
        interferes_with: collect("interferes_with"),
        requires_off: collect("requires_off"),
        disables: collect("disables"),
        affects: collect("affects"),
        price: Number(form?.querySelector('[name="price"]')?.value || 0),
        file_size: "runtime default",
        disk_usage: "runtime default",
        quality_score: "creator profile",
        reliability: "creator profile",
        power_score: "runtime balance preview",
        price_hint: "minimum runtime hint"
    };
    const summary = term.querySelector('[data-creator-player-summary]');
    if (summary) {
        const labels = (fieldName, values) => values.map(value => creatorOptionDescriptor(fieldName, value).label);
        const rows = [
            ["Aplikacja", `${payload.icon || "◇"} ${payload.name || "Bez nazwy"}`],
            ["Rodzina", (CREATOR_TOOL_FAMILY_PRESETS[payload.tool_family] || {}).label || "Ogólne narzędzie"],
            ["Cel", labels("target_types", payload.target_types).join(", ") || "Nie wybrano"],
            ["Start", payload.tool_mode || "ogólny"],
            ["Akcje mapy", labels("map_actions", payload.map_actions).join(", ") || "Brak"],
            ["Operacje", labels("operation_types", payload.operation_types).join(", ") || "Nie wybrano"],
            ["Informacje", labels("resource_types", payload.resource_types).join(", ") || "Brak"],
            ["Kolizje", (payload.interferes_with || []).join(", ") || "Brak"],
            ["Wymaga wyłączenia", (payload.requires_off || []).join(", ") || "Brak"],
            ["Może wyłączyć", (payload.disables || []).join(", ") || "Brak"],
            ["Wpływ na gracza", (payload.affects || []).join(", ") || "Brak"],
            ["Prezentacja", payload.interface || "Nie wybrano"]
        ];
        summary.innerHTML = rows.map(row => `<span>${escapeHTML(row[0])}</span><b>${escapeHTML(row[1])}</b>`).join("");
    }
    preview.textContent = JSON.stringify(payload, null, 2);
}

function validateCreatorContext(term, payload) {
    term.querySelectorAll('[data-creator-context-invalid]').forEach(field => {
        field.removeAttribute('data-creator-context-invalid');
        field.setAttribute('aria-invalid', 'false');
    });
    const invalid = (step, fieldName, message) => {
        const field = term.querySelector(`[data-appforge-field="${fieldName}"]`)
            || term.querySelector(`[name="${fieldName}"]`);
        if (field) {
            field.dataset.creatorContextInvalid = 'true';
            field.setAttribute('aria-invalid', 'true');
        }
        return { step, fieldName, message };
    };
    if (!payload.name || !String(payload.name).trim()) {
        return invalid(0, "name", "Krok 1 · Nazwa: wpisz niepustą nazwę aplikacji.");
    }
    if (payload.tool_family && payload.tool_family !== "custom") {
        if (!payload.target_types.length) {
            return invalid(2, "target_types", "Krok 3 · Cel: wybierz co najmniej jeden rodzaj celu zgodny z rodziną.");
        }
        if (["map", "hybrid"].includes(payload.tool_mode) && !payload.map_actions.length) {
            return invalid(3, "map_actions", "Krok 4 · Start: tryb mapowy lub hybrydowy wymaga akcji mapy; wybierz akcję albo tryb desktopowy.");
        }
        if (!payload.operation_types.length) {
            return invalid(4, "operation_types", "Krok 5 · Działanie: wybierz co najmniej jedną operację zgodną z celem i akcją.");
        }
    }
    return null;
}

function setCreatorCheckboxFilter(term, fieldName, allowedOptions) {
    const allowed = new Set(allowedOptions || []);
    const shouldFilter = Array.isArray(allowedOptions);
    let visibleCount = 0;
    let clearedCount = 0;
    term.querySelectorAll(`[data-appforge-field="${fieldName}"] [data-creator-option]`).forEach(label => {
        const option = label.dataset.creatorOption || "";
        const visible = !shouldFilter || allowed.has(option);
        label.hidden = !visible;
        if (visible) visibleCount += 1;
        const input = label.querySelector('input');
        if (input && !visible) {
            if (input.checked) clearedCount += 1;
            input.checked = false;
            syncCreatorToggle(input);
        }
    });
    term.querySelectorAll(`[data-appforge-field="${fieldName}"] [data-creator-option-group]`).forEach(group => {
        const hasVisibleOption = Array.from(group.querySelectorAll('[data-creator-option]'))
            .some(option => !option.hidden);
        group.hidden = !hasVisibleOption;
    });
    return { visibleCount, clearedCount };
}

function selectedCreatorOptions(term, fieldName) {
    return Array.from(term.querySelectorAll(`[data-appforge-field="${fieldName}"] input:checked`))
        .map(input => input.value)
        .filter(Boolean);
}

function intersectCreatorOptions(baseOptions, targetOptions, constraintActive = false) {
    if (!Array.isArray(baseOptions)) return targetOptions;
    if (!constraintActive) return baseOptions;
    if (!Array.isArray(targetOptions) || targetOptions.length === 0) return [];
    const targetSet = new Set(targetOptions);
    return baseOptions.filter(item => targetSet.has(item));
}

function collectCreatorTargetFilters(selectedTargets, fieldName) {
    const values = [];
    selectedTargets.forEach(targetType => {
        const targetPreset = CREATOR_TARGET_FILTERS[targetType];
        (targetPreset?.[fieldName] || []).forEach(item => {
            if (!values.includes(item)) values.push(item);
        });
    });
    return values;
}

function collectCreatorActionFilters(selectedActions, fieldName) {
    const values = [];
    selectedActions.forEach(action => {
        const actionPreset = CREATOR_ACTION_FILTERS[action];
        ((actionPreset && actionPreset[fieldName]) || []).forEach(item => {
            if (!values.includes(item)) values.push(item);
        });
    });
    return values;
}

function applyCreatorScannerMode(term) {
    const family = term.querySelector('[name="tool_family"]')?.value || "custom";
    const modeSelect = term.querySelector('[name="tool_mode"]');
    const mode = modeSelect?.value || "map";
    const familyBox = term.querySelector('[data-creator-family-box]');
    const familyTitle = term.querySelector('[data-creator-family-title]');
    const familyNote = term.querySelector('[data-creator-family-note]');
    const familySafety = term.querySelector('[data-creator-family-safety]');
    const mapNote = term.querySelector('[data-creator-map-note]');
    const typeInput = term.querySelector('[name="type"]');
    const familyPreset = CREATOR_TOOL_FAMILY_PRESETS[family];
    if (familyBox) familyBox.hidden = !familyPreset;
    const selectedTargets = selectedCreatorOptions(term, "target_types");
    const filterStatus = term.querySelector('[data-creator-filter-status]');
    if (!familyPreset) {
        ["map_actions", "operation_types", "resource_types", "target_types"].forEach(field => {
            setCreatorCheckboxFilter(term, field, null);
        });
        if (familyTitle) familyTitle.textContent = "Tryb narz\u0119dzia";
        if (familyNote) familyNote.textContent = "Wybierz \u015bcie\u017ck\u0119 kreatora, \u017ceby zaw\u0119zi\u0107 kontrakt do sensownych p\u00f3l.";
        if (familySafety) familySafety.textContent = "";
        if (mapNote) mapNote.textContent = "";
        if (filterStatus) filterStatus.textContent = "Tryb ogólny pokazuje cały kontrakt aplikacji.";
        updateCreatorContractPreview(term);
        return;
    }

    const preset = familyPreset.modes[mode] || familyPreset.modes.map;
    if (typeInput && !familyPreset.allowedTypes.includes(typeInput.value)) {
        typeInput.value = familyPreset.defaultType;
    }
    const targetMapActions = collectCreatorTargetFilters(selectedTargets, "map_actions");
    const targetOperations = collectCreatorTargetFilters(selectedTargets, "operation_types");
    const targetResources = collectCreatorTargetFilters(selectedTargets, "resource_types");
    const results = [];
    results.push(setCreatorCheckboxFilter(term, "target_types", preset.target_types));
    const allowedMapActions = intersectCreatorOptions(preset.map_actions, targetMapActions, selectedTargets.length > 0);
    results.push(setCreatorCheckboxFilter(term, "map_actions", allowedMapActions));
    const selectedActions = selectedCreatorOptions(term, "map_actions");
    const actionOperations = collectCreatorActionFilters(selectedActions, "operation_types");
    const actionResources = collectCreatorActionFilters(selectedActions, "resource_types");
    let allowedOperations = intersectCreatorOptions(preset.operation_types, targetOperations, selectedTargets.length > 0);
    let allowedResources = intersectCreatorOptions(preset.resource_types, targetResources, selectedTargets.length > 0);
    if (selectedActions.length) {
        allowedOperations = intersectCreatorOptions(allowedOperations, actionOperations, true);
        allowedResources = intersectCreatorOptions(allowedResources, actionResources, true);
    }
    results.push(setCreatorCheckboxFilter(term, "operation_types", allowedOperations));
    results.push(setCreatorCheckboxFilter(term, "resource_types", allowedResources));
    const clearedCount = results.reduce((total, result) => total + (result ? result.clearedCount : 0), 0);
    if (filterStatus) {
        filterStatus.textContent = clearedCount
            ? `Dopasowano opcje do rodziny, celu i akcji. Wyczyszczono niezgodnych wyborów: ${clearedCount}.`
            : "Opcje są dopasowane do wybranej rodziny, celu i akcji.";
    }
    if (familyTitle) familyTitle.textContent = familyPreset.boxTitle;
    if (familyNote) familyNote.textContent = preset.description;
    if (familySafety) familySafety.textContent = familyPreset.safetyText;
    if (mapNote) {
        mapNote.textContent = mode === "desktop"
            ? familyPreset.desktopMapNote
            : familyPreset.mapNote;
    }
    updateCreatorContractPreview(term);
}

function wireCreatorPreview(term) {
    const form = term.querySelector('.appforge-form');
    if (!form) return;
    form.addEventListener('input', () => updateCreatorContractPreview(term));
    form.addEventListener('change', (event) => {
        const filterSource = event.target && event.target.closest(
            '[name="tool_family"], [name="tool_mode"], '
            + '[data-appforge-field="target_types"] input, '
            + '[data-appforge-field="map_actions"] input'
        );
        if (filterSource) applyCreatorScannerMode(term);
        updateCreatorContractPreview(term);
    });
    applyCreatorScannerMode(term);
    updateCreatorContractPreview(term);
}

function appendCreatorMeta(form, keys, interfaceName) {
    form.innerHTML = `
        <div class="creator-wizard" data-creator-wizard>
            ${creatorWizardNavHtml()}
            <section class="creator-step-panel" data-creator-panel="0">
                <h4>Meta aplikacji</h4>
                <div class="appforge-grid">
                    <label>Nazwa<input name="name" maxlength="32" required placeholder="Nazwa aplikacji"></label>
                    <label>Cena<input name="price" type="number" min="0" step="1" value="100"></label>
                    <label>Ikonka
                        <span class="appforge-icon-row">
                            <input name="icon" maxlength="16" value="">
                            <span class="appforge-icon-preview"></span>
                        </span>
                    </label>
                </div>
                <label>Opis<textarea name="description" rows="3" placeholder="Co robi aplikacja?"></textarea></label>
                ${creatorPanelNav(false, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="1" hidden>
                <h4>Typ narz\u0119dzia</h4>
                <label>\u015acie\u017cka kreatora
                    <select name="tool_family">
                        <option value="custom">Og\u00f3lne narz\u0119dzie</option>
                        ${Object.entries(CREATOR_TOOL_FAMILY_PRESETS).map(([value, preset]) => `
                            <option value="${escapeHTML(value)}">${escapeHTML(preset.label)}</option>
                        `).join("")}
                    </select>
                </label>
                <div class="creator-scanner-box" data-creator-family-box hidden>
                    <label><span data-creator-family-title>Tryb narz\u0119dzia</span>
                        <select name="tool_mode">
                            <option value="map">Mapowy</option>
                            <option value="desktop">Desktopowy na aimed_target</option>
                            <option value="hybrid">Hybrydowy</option>
                        </select>
                    </label>
                    <p class="creator-step-note" data-creator-family-note></p>
                    <p class="creator-step-note" data-creator-family-safety></p>
                </div>
                <label>Typ
                    <select name="type">
                        ${CREATOR_TOOL_TYPES.map(([value, label]) => `
                            <option value="${escapeHTML(value)}" ${value === "exploit" ? "selected" : ""}>${escapeHTML(label)}</option>
                        `).join("")}
                    </select>
                </label>
                <label>Wykrywa<textarea name="detects" rows="2" placeholder="np. open_ports, user_location"></textarea></label>
                <p class="creator-filter-status" data-creator-filter-status role="status" aria-live="polite">Wybierz rodzinę, aby dopasować kontrakt aplikacji.</p>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="2" hidden>
                <h4>\u015arodowisko dzia\u0142ania</h4>
                <input type="hidden" name="interface" value="${escapeHTML(interfaceName)}">
                <div class="creator-readonly-contract">
                    <span>Interface</span>
                    <b>${escapeHTML(interfaceName)}</b>
                </div>
                <div class="appforge-fieldset"><h4>Rodzaj celu</h4><p class="creator-field-help">Wybierz obiekty świata, na których narzędzie może pracować.</p>${creatorOptionCheckboxGroup(CREATOR_TARGET_TYPE_OPTIONS, "target_types")}</div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="3" hidden>
                <h4>Akcje mapy / desktopu</h4>
                <p class="creator-step-note" data-creator-map-note>Wybierz akcje mapy tylko wtedy, gdy narz\u0119dzie ma by\u0107 uruchamiane z menu mapy.</p>
                <div class="appforge-fieldset"><h4>Akcja uruchamiana z mapy</h4><p class="creator-field-help">To wpis widoczny w menu obiektu. Tryb desktopowy może pozostać bez akcji mapy.</p>${creatorOptionCheckboxGroup(CREATOR_MAP_ACTION_OPTIONS, "map_actions")}</div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="4" hidden>
                <h4>Operacje</h4>
                <div class="appforge-fieldset"><h4>Operacja na oznaczonym celu</h4><p class="creator-field-help">Określa gameplayowy skutek aplikacji uruchamianej z desktopu lub terminala.</p>${creatorOptionCheckboxGroup(CREATOR_OPERATION_OPTIONS, "operation_types")}</div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="5" hidden>
                <h4>Zasoby</h4>
                <div class="appforge-fieldset"><h4>Informacje i ślady</h4><p class="creator-field-help">Wybierz dane, które operacja może przygotować w świecie gry.</p>${creatorOptionCheckboxGroup(CREATOR_RESOURCE_OPTIONS, "resource_types")}</div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="6" hidden>
                <h4>Ryzyko i zabezpieczenia</h4>
                <div class="creator-risk-grid">
                    <div class="appforge-fieldset"><h4>Z czym może kolidować?</h4><p class="creator-field-help">Zapis do <code>interferes_with</code>: aktywne zabezpieczenia, które mogą zakłócić pracę.</p>${creatorCheckboxGroup(keys, "interferes_with")}</div>
                    <div class="appforge-fieldset"><h4>Co musi być wyłączone na celu?</h4><p class="creator-field-help">Zapis do <code>requires_off</code>: warunki konieczne przed uruchomieniem.</p>${creatorCheckboxGroup(keys, "requires_off")}</div>
                    <div class="appforge-fieldset"><h4>Co narzędzie może wyłączyć?</h4><p class="creator-field-help">Zapis do <code>disables</code>: zabezpieczenia będące skutkiem działania.</p>${creatorCheckboxGroup(keys, "disables")}</div>
                    <div class="appforge-fieldset"><h4>Na co wpływa po stronie gracza?</h4><p class="creator-field-help">Zapis do <code>affects</code>: lokalny wpływ aplikacji na profil lub rozgrywkę.</p>${creatorCheckboxGroup(keys, "affects")}</div>
                </div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="7" hidden>
                <h4>Storage / quality preview</h4>
                <div class="creator-preview-grid">
                    <span>Waga aplikacji</span><b>runtime default</b>
                    <span>Disk usage</span><b>runtime default</b>
                    <span>Quality</span><b>profil tw\u00f3rcy</b>
                    <span>Reliability</span><b>profil tw\u00f3rcy</b>
                </div>
                <div class="creator-player-summary" data-creator-player-summary></div>
                <details class="creator-technical-preview">
                    <summary>Pokaż techniczny kontrakt JSON</summary>
                    <pre class="creator-contract-preview" data-creator-contract-preview></pre>
                </details>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="8" hidden>
                <h4>Publikacja</h4>
                <p class="creator-step-note">Publikacja u\u017cywa istniej\u0105cego endpointu /api/apps/generate i katalogu Googleplex.</p>
                <div class="creator-interface-slot"></div>
                <button class="appforge-submit" type="submit">Publikuj w Googleplex</button>
                <div class="appforge-status"></div>
                ${creatorPanelNav(true, false)}
            </section>
        </div>
    `;
}

function insertIconAtCursor(input, icon) {
    input.value = icon;
    const nextPosition = icon.length;
    input.focus();
    input.setSelectionRange(nextPosition, nextPosition);
    input.dispatchEvent(new Event('input', { bubbles: true }));
}

function creatorIconGraphemes(value) {
    const text = String(value || '').trim();
    if (!text) return [];
    if (typeof Intl !== 'undefined' && typeof Intl.Segmenter === 'function') {
        const segmenter = new Intl.Segmenter(undefined, { granularity: 'grapheme' });
        return Array.from(segmenter.segment(text), item => item.segment);
    }
    const parts = [];
    Array.from(text).forEach(char => {
        const code = char.codePointAt(0);
        const previous = parts[parts.length - 1] || '';
        const extendsPrevious = code === 0x200d
            || previous.endsWith('\u200d')
            || (code >= 0xfe00 && code <= 0xfe0f)
            || (code >= 0x1f3fb && code <= 0x1f3ff)
            || code === 0x20e3;
        if (extendsPrevious && parts.length) parts[parts.length - 1] += char;
        else parts.push(char);
    });
    if (parts.length === 2 && parts.every(part => {
        const code = part.codePointAt(0);
        return code >= 0x1f1e6 && code <= 0x1f1ff;
    })) return [parts.join('')];
    return parts;
}

function validateCreatorIcon(input, fallbackIcon) {
    const value = String(input.value || '').trim();
    const valid = creatorIconGraphemes(value).length === 1 && value.length <= 16;
    input.setCustomValidity(valid ? '' : 'Wybierz dokładnie jeden widoczny znak lub emoji.');
    input.setAttribute('aria-invalid', valid ? 'false' : 'true');
    return valid ? value : fallbackIcon;
}

function setupIconPicker(term, fallbackIcon = '\u{1F6E0}\uFE0F') {
    const iconInput = term.querySelector('input[name="icon"]');
    const iconPreview = term.querySelector('.appforge-icon-preview');
    const iconRow = term.querySelector('.appforge-icon-row');
    if (!iconInput || !iconPreview || !iconRow) return { iconInput, iconPreview };

    iconInput.value = fallbackIcon;
    iconPreview.textContent = iconInput.value;

    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'appforge-icon-picker-toggle';
    toggle.textContent = '\u25BE';
    toggle.title = 'Wybierz ikon\u0119';

    const picker = document.createElement('div');
    picker.className = 'appforge-icon-picker';
    picker.hidden = true;
    picker.innerHTML = SYSTEM_ICON_LIBRARY.map(icon => `
        <button type="button" class="appforge-icon-choice" data-icon="${escapeHTML(icon)}">${escapeHTML(icon)}</button>
    `).join("");

    iconRow.appendChild(toggle);
    iconRow.appendChild(picker);

    iconInput.addEventListener('input', () => {
        iconPreview.textContent = validateCreatorIcon(iconInput, fallbackIcon);
    });
    toggle.addEventListener('click', (event) => {
        event.preventDefault();
        picker.hidden = !picker.hidden;
    });
    picker.addEventListener('click', (event) => {
        const button = event.target.closest('.appforge-icon-choice');
        if (!button) return;
        insertIconAtCursor(iconInput, button.dataset.icon || '');
        picker.hidden = true;
    });

    return { iconInput, iconPreview };
}

function creatorBaseWindow(appName, interfaceName) {
    const term = document.createElement('div');
    term.className = 'terminal creator-window';
    term.dataset.app = appName.toLowerCase();
    const position = findAvailablePosition(620, 660);
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `620px`;
    term.style.height = `680px`;
    term.style.display = 'block';
    term.innerHTML = `
        <div class="title-bar">
            ${appName}: ${interfaceName}
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div class="creator-workspace">
            <form class="appforge-form"></form>
        </div>
    `;
    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());
    return term;
}

function wireCreatorSubmit(term, buildExtraPayload) {
    const { iconInput, iconPreview } = setupIconPicker(term);

    term.querySelector('.appforge-form').addEventListener('submit', async (event) => {
        event.preventDefault();
        const form = event.currentTarget;
        const status = term.querySelector('.appforge-status');
        const payload = Object.fromEntries(new FormData(form).entries());
        payload.price = Number(payload.price || 0);
        if (!validateGeneratedAppNameForScripts(payload, status)) return;
        if (!validateCreatorIcon(iconInput, '\u{1F6E0}\uFE0F')) {
            status.textContent = 'Wybierz dokładnie jedną ikonę aplikacji.';
            iconInput.reportValidity();
            return;
        }
        ["interferes_with", "requires_off", "disables", "affects"].forEach(fieldName => {
            payload[fieldName] = Array.from(
                term.querySelectorAll(`[data-appforge-field="${fieldName}"] input:checked`)
            ).map(input => input.value);
        });
        ["map_actions", "operation_types", "resource_types", "target_types"].forEach(fieldName => {
            payload[fieldName] = Array.from(
                term.querySelectorAll(`[data-appforge-field="${fieldName}"] input:checked`)
            ).map(input => input.value);
        });
        Object.assign(payload, buildExtraPayload(term));
        const contextError = validateCreatorContext(term, payload);
        if (contextError) {
            status.textContent = contextError.message;
            status.setAttribute('role', 'alert');
            form.dispatchEvent(new CustomEvent('creator:goto-step', { detail: contextError }));
            return;
        }
        status.removeAttribute('role');
        status.textContent = 'Publikowanie...';

        try {
            const res = await fetch('/api/apps/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok || !data.success) throw new Error(data.message || 'Nie udalo sie opublikowac.');
            status.textContent = `${data.message} Projekt zapisany w files/projects/${data.app.project_file}`;
            form.reset();
            iconInput.value = '\u{1F6E0}\uFE0F';
            iconPreview.textContent = iconInput.value;
        } catch (err) {
            status.textContent = err.message;
        }
    });
}

async function createTermCreator() {
    if (document.querySelector(`.terminal[data-app="termcreator"]`)) return;
    const keys = await getCreatorSecurityKeys();
    const term = creatorBaseWindow('TermCreator', 'terminal');
    const form = term.querySelector('.appforge-form');
    appendCreatorMeta(form, keys, 'terminal');
    form.querySelector('.creator-interface-slot').insertAdjacentHTML('beforeend', `
        <div class="appforge-level-fields">
            <h4>levels[]</h4>
            <div class="creator-items" data-kind="terminal-level"></div>
            <button type="button" class="appforge-submit creator-add">Dodaj poziom terminala</button>
        </div>
    `);
    const list = term.querySelector('[data-kind="terminal-level"]');
    const addLevel = () => {
        list.insertAdjacentHTML('beforeend', `
            <div class="creator-item">
                <label>command<input class="creator-terminal-command" placeholder="./tool.sh --target current"></label>
                <label>logs<textarea class="creator-terminal-logs" rows="4" placeholder="Jedna linia = jeden log"></textarea></label>
            </div>
        `);
    };
    term.querySelector('.creator-add').addEventListener('click', addLevel);
    addLevel();
    wireCreatorSubmit(term, (root) => ({
        terminal_levels: Array.from(root.querySelectorAll('.creator-item')).map(item => ({
            command: item.querySelector('.creator-terminal-command').value,
            logs: item.querySelector('.creator-terminal-logs').value
        }))
    }));
    wireCreatorWizard(term);
    wireCreatorPreview(term);
}

async function createWindowMaker() {
    if (document.querySelector(`.terminal[data-app="windowmaker"]`)) return;
    const keys = await getCreatorSecurityKeys();
    const term = creatorBaseWindow('WindowMaker', 'window');
    const form = term.querySelector('.appforge-form');
    appendCreatorMeta(form, keys, 'window');
    form.querySelector('.creator-interface-slot').insertAdjacentHTML('beforeend', `
        <div class="appforge-level-fields">
            <h4>levels[0]</h4>
            <label>title<input name="level_title" placeholder="Panel aplikacji"></label>
            <div class="creator-items" data-kind="window-list"></div>
            <button type="button" class="appforge-submit add-list-item">Dodaj wpis listy</button>
            <div class="creator-items" data-kind="window-buttons"></div>
            <button type="button" class="appforge-submit add-button-item">Dodaj przycisk</button>
        </div>
    `);
    const addList = () => term.querySelector('[data-kind="window-list"]').insertAdjacentHTML('beforeend', `<label>list[]<input class="creator-window-list" placeholder="Linia statusu"></label>`);
    const addButton = () => term.querySelector('[data-kind="window-buttons"]').insertAdjacentHTML('beforeend', `<div class="creator-item"><label>button label<input class="creator-window-button-label" placeholder="Uruchom"></label><label>action<input class="creator-window-button-action" placeholder="run_generated"></label></div>`);
    term.querySelector('.add-list-item').addEventListener('click', addList);
    term.querySelector('.add-button-item').addEventListener('click', addButton);
    addList();
    addButton();
    wireCreatorSubmit(term, (root) => ({
        window_list: Array.from(root.querySelectorAll('.creator-window-list')).map(input => input.value).filter(Boolean),
        window_buttons: Array.from(root.querySelectorAll('.creator-item')).map(item => {
            const label = item.querySelector('.creator-window-button-label')?.value;
            const action = item.querySelector('.creator-window-button-action')?.value;
            return label ? `${label}|${action || 'run_generated'}` : '';
        }).filter(Boolean)
    }));
    wireCreatorWizard(term);
    wireCreatorPreview(term);
}

async function createButtonMaker() {
    if (document.querySelector(`.terminal[data-app="buttonmaker"]`)) return;
    const keys = await getCreatorSecurityKeys();
    const term = creatorBaseWindow('ButtonMaker', 'button_choices');
    const form = term.querySelector('.appforge-form');
    appendCreatorMeta(form, keys, 'button_choices');
    form.querySelector('.creator-interface-slot').insertAdjacentHTML('beforeend', `
        <div class="appforge-level-fields">
            <h4>levels[0]</h4>
            <label>title<input name="level_title" placeholder="Wybierz tryb"></label>
            <label>text<textarea name="button_text" rows="3" placeholder="Opis wyboru dla gracza"></textarea></label>
            <div class="creator-items" data-kind="button-options"></div>
            <button type="button" class="appforge-submit add-option-item">Dodaj opcje</button>
        </div>
    `);
    const addOption = () => term.querySelector('[data-kind="button-options"]').insertAdjacentHTML('beforeend', `
        <div class="creator-item">
            <label>label<input class="creator-option-label" placeholder="Recon"></label>
            <label>effect<input class="creator-option-effect" placeholder="risk_level=10,firewall=false"></label>
            <label>price<input class="creator-option-price" type="number" min="0" step="1" placeholder="90"></label>
        </div>
    `);
    term.querySelector('.add-option-item').addEventListener('click', addOption);
    addOption();
    wireCreatorSubmit(term, (root) => ({
        button_options: Array.from(root.querySelectorAll('.creator-item')).map(item => {
            const label = item.querySelector('.creator-option-label')?.value;
            const effect = item.querySelector('.creator-option-effect')?.value || '';
            const price = item.querySelector('.creator-option-price')?.value || '';
            return label ? `${label}|${effect}|${price}` : '';
        }).filter(Boolean)
    }));
    wireCreatorWizard(term);
    wireCreatorPreview(term);
}

const GHOSTLAB_VERSION = "v1.0";
const GHOSTLAB_VERSION_NAME = "Stable Lab";
const GHOSTLAB_ROADMAP = [
    ["v0.1", "Workspace", "done"],
    ["v0.2", "Projects", "done"],
    ["v0.3", "Templates", "done"],
    ["v0.4", "Editors", "done"],
    ["v0.5", "Compiler", "done"],
    ["v0.6", "Publisher", "done"],
    ["v0.7", "Ghost Exchange", "done"],
    ["v0.8", "Research Foundation", "done"],
    ["v1.0", "Stable Lab / Polish", "current"]
];
const GHOSTLAB_V2_ROADMAP = [
    "Research Tree",
    "Compiler Optimizer",
    "Ghost Exchange Community",
    "AI Templates",
    "Plugin SDK",
    "Blueprint Sharing",
    "AI Assistant",
    "Versioning",
    "Rollback",
    "Dependency Graph"
];
const GHOSTLAB_TAB_TOOLTIPS = {
    Projects: "Tworzenie, otwieranie i porzadkowanie projektow GhostLab.",
    Templates: "Start projektu z gotowego szablonu narzedzia.",
    Research: "Przyszle drzewo badan. Pelne Research Tree jest planowane na v2.0.",
    "Ghost Exchange": "Biblioteka zasobow GhostLab. Community pojawi sie pozniej.",
    Documentation: "Roadmapa, changelog i opis workflow GhostLab."
};
const GHOSTLAB_TEMPLATES = [
    {
        id: "financial_sniffer",
        name: "Financial Sniffer",
        icon: "\u{1F4B8}",
        category: "finance",
        tool_category: "finance",
        recommended_level: 12,
        risk_level: 5,
        status: "Ready",
        description: "Jednorazowa operacja finansowa na aktywnym dostepie do gracza."
    },
    {
        id: "friend_kicker",
        name: "Friend Kicker",
        icon: "\u{1F44B}",
        category: "social",
        tool_category: "social",
        recommended_level: 10,
        risk_level: 4,
        status: "Ready",
        description: "Losowa proba zerwania jednego kontaktu ofiary."
    },
    {
        id: "security_panel_proxy",
        name: "Security Panel Proxy",
        icon: "\u{1F6E1}\uFE0F",
        category: "security",
        tool_category: "security",
        recommended_level: 15,
        risk_level: 3,
        status: "Ready",
        description: "Zdalny panel ustawien zabezpieczen profilu ofiary."
    },
    {
        id: "system_log_reader",
        name: "System Log Reader",
        icon: "\u{1F4DC}",
        category: "intel",
        tool_category: "intel",
        recommended_level: 8,
        risk_level: 2,
        status: "Ready",
        description: "Bezpieczny odczyt ostatnich komunikatow systemowych ofiary."
    },
    {
        id: "arsenal_cleaner",
        name: "Arsenal Cleaner",
        icon: "\u{1F9F9}",
        category: "apps",
        tool_category: "apps",
        recommended_level: 14,
        risk_level: 5,
        status: "Ready",
        description: "Losowa proba usuniecia aplikacji z arsenalu ofiary."
    }
];
const GHOSTLAB_RESEARCH_BRANCHES = [
    {
        id: "finance",
        icon: "$",
        name: "Finance",
        status: "locked",
        progress: 0,
        tier: 0,
        description: "Przyszle badania finansowe rozwina parametry narzedzi typu Financial Sniffer.",
        unlocks: ["stealth transfer", "higher cap", "transaction masking", "wallet anomaly bypass"]
    },
    {
        id: "intel",
        icon: "i",
        name: "Intel",
        status: "locked",
        progress: 0,
        tier: 0,
        description: "Przyszle badania wywiadowcze rozszerza odczyt sladow systemowych i korelacje sygnalow.",
        unlocks: ["deeper logs", "forensic mode", "timeline reconstruction", "signal correlation"]
    },
    {
        id: "security",
        icon: "#",
        name: "Security",
        status: "locked",
        progress: 0,
        tier: 0,
        description: "Przyszle badania security rozbuduja zdalne hartowanie i reguly konfliktow zabezpieczen.",
        unlocks: ["advanced presets", "remote hardening", "conflict rule bypass", "session-only spoofing"]
    },
    {
        id: "social",
        icon: "@",
        name: "Social",
        status: "locked",
        progress: 0,
        tier: 0,
        description: "Przyszle badania social zwieksza mozliwosci zaklocania relacji i maskowania grafu zaufania.",
        unlocks: ["stronger contact disruption", "social graph noise", "trust spoofing", "relation masking"]
    },
    {
        id: "apps",
        icon: "*",
        name: "Apps",
        status: "locked",
        progress: 0,
        tier: 0,
        description: "Przyszle badania aplikacji poprawia czyszczenie arsenalu i analize zaleznosci narzedzi.",
        unlocks: ["safer arsenal cleanup", "dependency scan", "app quarantine", "recovery blocker"]
    }
];
const GHOSTLAB_EXCHANGE_OFFICIAL = [
    {
        name: "Official Tool Templates",
        type: "Templates",
        status: "installed",
        description: "Bazowe szablony GhostLab: Financial, Social, Security, Intel i Apps."
    },
    {
        name: "Validation Profiles",
        type: "Blueprints",
        status: "bundled",
        description: "Reguly walidacji blueprintow uzywane przez Editor Shell i Compiler."
    },
    {
        name: "Publisher Contract",
        type: "Documentation",
        status: "active",
        description: "Standard publikacji artefaktu jako pro-system-tool w Googleplex."
    },
    {
        name: "Runtime Roadmap",
        type: "Documentation",
        status: "planned",
        description: "Mapa przyszlego custom runtime dla narzedzi publikowanych z GhostLab."
    }
];
const GHOSTLAB_TOOL_BLUEPRINT = {};
const GHOSTLAB_EDITOR_FIELDS = {
    financial_sniffer: [
        { key: "steal_percent", label: "Steal %", type: "number" },
        { key: "detection_percent", label: "Detection %", type: "number" },
        { key: "cooldown_minutes", label: "Cooldown", type: "number" },
        { key: "success_message", label: "Success message", type: "textarea" },
        { key: "failure_message", label: "Failure message", type: "textarea" },
        { key: "reward_note", label: "Rewards", type: "text" }
    ],
    friend_kicker: [
        { key: "success_percent", label: "Success %", type: "number" },
        { key: "detection_percent", label: "Detection %", type: "number" },
        { key: "target_policy", label: "Targets", type: "text" },
        { key: "victim_message", label: "Victim system message", type: "textarea" },
        { key: "contact_message", label: "Contact system message", type: "textarea" }
    ],
    security_panel_proxy: [
        { key: "allowed_switches", label: "Allowed switches", type: "text" },
        { key: "presets", label: "Presets", type: "text" },
        { key: "rules", label: "Rules", type: "textarea" },
        { key: "conflict_matrix", label: "Conflict matrix", type: "textarea" }
    ],
    system_log_reader: [
        { key: "log_limit", label: "Log limit", type: "number" },
        { key: "include_type", label: "Include type", type: "checkbox" },
        { key: "include_status", label: "Include status", type: "checkbox" },
        { key: "include_created_at", label: "Include timestamp", type: "checkbox" },
        { key: "redaction_policy", label: "Redaction policy", type: "text" }
    ],
    arsenal_cleaner: [
        { key: "success_percent", label: "Success %", type: "number" },
        { key: "detection_percent", label: "Detection %", type: "number" },
        { key: "target_policy", label: "Targets", type: "text" },
        { key: "protected_apps", label: "Protected apps", type: "textarea" },
        { key: "remove_tools_file", label: "Remove files/tools entry", type: "checkbox" }
    ]
};
const ghostLabState = {
    projects: [],
    selectedProjectId: null,
    activeProjectId: null,
    activeTab: "Projects",
    lastAction: "idle",
    bannerHidden: false,
    working: false
};

function ghostLabProjectStatusLabel(status) {
    const normalized = String(status || "draft").toLowerCase();
    if (normalized === "published") return "published";
    if (normalized === "compiled" || normalized === "built") return "compiled";
    if (normalized === "valid" || normalized === "validated") return "valid";
    return "draft";
}

function updateGhostLabStatusBar(root) {
    const bar = root?.querySelector('[data-ghostlab-status-bar]');
    if (!bar) return;
    const activeProject = ghostLabState.projects.find(project => project.id === ghostLabState.activeProjectId);
    bar.innerHTML = `
        <span>Tab: <b>${escapeHTML(ghostLabState.activeTab || "Projects")}</b></span>
        <span>Version: <b>${escapeHTML(GHOSTLAB_VERSION)}</b></span>
        <span>Projects: <b>${escapeHTML(String(ghostLabState.projects.length || 0))}</b></span>
        <span>Active: <b>${escapeHTML(activeProject?.name || "-")}</b></span>
        <span>State: <b>${ghostLabState.working ? "working" : escapeHTML(ghostLabState.lastAction || "idle")}</b></span>
    `;
}

function setGhostLabMessage(root, message, type = "info") {
    const box = root?.querySelector('[data-ghostlab-message]');
    if (!box) return;
    if (type !== "working") {
        ghostLabState.working = false;
        root?.classList.remove("is-working");
    }
    box.className = `ghostlab-message is-${type}`;
    box.textContent = message || "";
    ghostLabState.lastAction = message || "idle";
    updateGhostLabStatusBar(root);
}

function setGhostLabWorking(root, message = "Working...") {
    ghostLabState.working = true;
    root?.classList.add("is-working");
    setGhostLabMessage(root, message, "working");
}

function clearGhostLabWorking(root, fallback = "idle") {
    ghostLabState.working = false;
    root?.classList.remove("is-working");
    ghostLabState.lastAction = fallback;
    const box = root?.querySelector('[data-ghostlab-message]');
    if (box) {
        box.className = "ghostlab-message is-info";
        box.textContent = fallback === "idle" ? "" : fallback;
    }
    updateGhostLabStatusBar(root);
}

function renderGhostLabWorkspace(root) {
    if (!root) return;
    const tabs = ["Projects", "Templates", "Research", "Ghost Exchange", "Documentation"];
    root.innerHTML = `
        <div class="ghostlab-top">
            <div>
                <span class="ghostlab-kicker">PRO SYSTEM LAB</span>
                <h2>GhostLab <em>${GHOSTLAB_VERSION}</em></h2>
                <p>${GHOSTLAB_VERSION_NAME}</p>
            </div>
            <div class="ghostlab-status">HUB ONLINE</div>
        </div>
        <section class="ghostlab-onboarding" data-ghostlab-onboarding ${ghostLabState.bannerHidden ? 'hidden' : ''}>
            <div>
                <strong>Welcome to GhostLab ${GHOSTLAB_VERSION}</strong>
                <p>Build custom Pro System Tools through a full IDE workflow.</p>
                <ol>
                    <li>Create project</li>
                    <li>Choose template</li>
                    <li>Edit blueprint</li>
                    <li>Validate</li>
                    <li>Compile</li>
                    <li>Publish to Googleplex</li>
                </ol>
            </div>
            <button type="button" data-ghostlab-hide-onboarding title="Hide this banner in the current GhostLab window">Hide</button>
        </section>
        <div class="ghostlab-message" data-ghostlab-message></div>
        <div class="ghostlab-workspace">
            <aside class="ghostlab-sidebar">
                ${tabs.map((tab, index) => `
                    <button type="button" class="${index === 0 ? 'active' : ''}" data-ghostlab-tab="${tab}" title="${escapeHTML(GHOSTLAB_TAB_TOOLTIPS[tab] || tab)}">
                        ${tab}
                    </button>
                `).join("")}
            </aside>
            <main class="ghostlab-main" data-ghostlab-main></main>
        </div>
        <div class="ghostlab-status-bar" data-ghostlab-status-bar></div>
    `;
    root.querySelector('[data-ghostlab-hide-onboarding]')?.addEventListener('click', () => {
        ghostLabState.bannerHidden = true;
        root.querySelector('[data-ghostlab-onboarding]')?.setAttribute('hidden', '');
        setGhostLabMessage(root, "Onboarding hidden for this window.", "info");
    });
    root.querySelectorAll('[data-ghostlab-tab]').forEach(button => {
        button.addEventListener('click', () => {
            root.querySelectorAll('[data-ghostlab-tab]').forEach(item => item.classList.remove('active'));
            button.classList.add('active');
            renderGhostLabTab(button.dataset.ghostlabTab, root);
        });
    });
    updateGhostLabStatusBar(root);
    renderGhostLabTab("Projects", root);
}

function renderGhostLabTab(tabName, root) {
    const main = root?.querySelector('[data-ghostlab-main]');
    if (!main) return;
    ghostLabState.activeTab = tabName || "Projects";
    setGhostLabMessage(root, "", "info");
    updateGhostLabStatusBar(root);

    if (tabName === "Projects") {
        main.innerHTML = `
            <section class="ghostlab-panel">
                <header><h3>Projects</h3><span>v0.2 / v0.3 templates</span></header>
                <p>Projekty GhostLab sa zapisywane osobno w files.pro_system_projects, bez mieszania z projektami AppForge.</p>
                <div class="ghostlab-project-toolbar">
                    <input type="text" data-ghostlab-project-name maxlength="64" placeholder="Nazwa projektu">
                    <button type="button" data-ghostlab-new-project title="Create a new empty GhostLab project.">New Project</button>
                    <button type="button" data-ghostlab-open-project title="Open selected project in the editor.">Open Project</button>
                    <button type="button" data-ghostlab-rename-project title="Rename selected project using the name field.">Rename</button>
                    <button type="button" data-ghostlab-delete-project title="Delete selected GhostLab project.">Delete</button>
                </div>
                <div class="ghostlab-project-list" data-ghostlab-project-list>
                    <div class="ghostlab-empty">Ladowanie projektow...</div>
                </div>
                <div class="ghostlab-project-preview" data-ghostlab-project-preview>
                    Wybierz projekt, zeby zobaczyc status workspace.
                </div>
            </section>
        `;
        wireGhostLabProjects(root);
    } else if (tabName === "Templates") {
        main.innerHTML = `
            <section class="ghostlab-panel">
                <header><h3>Templates</h3><span>v0.3 Ready</span></header>
                <div class="ghostlab-template-grid">
                    ${GHOSTLAB_TEMPLATES.map(item => `
                        <article class="ghostlab-template-card">
                            <div class="ghostlab-template-head">
                                <span class="ghostlab-template-icon">${escapeHTML(item.icon)}</span>
                                <div>
                                    <strong>${escapeHTML(item.name)}</strong>
                                    <small>${escapeHTML(item.category)} / ${escapeHTML(item.status)}</small>
                                </div>
                            </div>
                            <span>${escapeHTML(item.description)}</span>
                            <div class="ghostlab-template-meta">
                                <b>LVL ${escapeHTML(String(item.recommended_level))}</b>
                                <b>Risk ${"★".repeat(item.risk_level)}${"☆".repeat(Math.max(0, 5 - item.risk_level))}</b>
                            </div>
                            <button type="button" data-ghostlab-create-template="${escapeHTML(item.id)}" title="Create a draft project from this template.">Create Project</button>
                        </article>
                    `).join("")}
                    ${GHOSTLAB_TEMPLATES.length ? '' : '<div class="ghostlab-empty">No templates available. Ghost Exchange may provide more later.</div>'}
                </div>
            </section>
        `;
        wireGhostLabTemplates(root);
    } else if (tabName === "Research") {
        renderGhostLabResearch(root);
    } else if (tabName === "Ghost Exchange") {
        main.innerHTML = `
            <section class="ghostlab-panel">
                <header><h3>Ghost Exchange</h3><span>v0.7 Official</span></header>
                <p>Biblioteka zasobow GhostLab. To nie jest sklep i nie publikuje community uploadow.</p>
                <div class="ghostlab-exchange-layout">
                    <div class="ghostlab-exchange-section">
                        <h4>Official</h4>
                        <div class="ghostlab-exchange-grid">
                            ${GHOSTLAB_EXCHANGE_OFFICIAL.map(item => `
                                <article class="ghostlab-exchange-card">
                                    <strong>${escapeHTML(item.name)}</strong>
                                    <small>${escapeHTML(item.type)} / ${escapeHTML(item.status)}</small>
                                    <span>${escapeHTML(item.description)}</span>
                                </article>
                            `).join("")}
                        </div>
                    </div>
                    <div class="ghostlab-exchange-placeholders">
                        ${["Community", "Blueprints", "Templates"].map(section => `
                            <button type="button" title="Coming in GhostLab v2.0." data-ghostlab-disabled="${section} w Ghost Exchange: Coming in GhostLab v2.0.">
                                <strong>${section}</strong>
                                <span>Coming in GhostLab v2.0.</span>
                            </button>
                        `).join("")}
                    </div>
                </div>
            </section>
        `;
    } else {
        main.innerHTML = `
            <section class="ghostlab-panel">
                <header><h3>Documentation</h3><span>${GHOSTLAB_VERSION}</span></header>
                <div class="ghostlab-docs">
                    <p>GhostLab jest laboratorium do przyszlego projektowania narzedzi klasy Pro System Tools.</p>
                    <h4>GhostLab v1.0 - Stable Lab</h4>
                    <p>GhostLab v1.0 domyka pierwszy pelny cykl pracy: Project -> Template -> Editor -> Validate -> Compile -> Publisher -> Googleplex.</p>
                    <p>AppForge sluzy do prostych aplikacji operacyjnych. GhostLab bedzie srodowiskiem dla narzedzi, ktore dzialaja na shackowanym graczu.</p>
                    <p>Pro System Tools uruchamiaja sie tylko po Player Hack Access, bo wymagaja aktywnego, czasowego dostepu do profilu ofiary.</p>
                    <h4>Changelog</h4>
                    <ol>
                        ${GHOSTLAB_ROADMAP.map(([version, name, status]) => `<li class="ghostlab-roadmap-${escapeHTML(status || 'planned')}"><b>${version}</b> ${name} <span>${escapeHTML(status || 'planned')}</span></li>`).join("")}
                    </ol>
                    <h4>GhostLab v2.0 Roadmap</h4>
                    <ul class="ghostlab-v2-roadmap">
                        ${GHOSTLAB_V2_ROADMAP.map(item => `<li>${escapeHTML(item)}</li>`).join("")}
                    </ul>
                </div>
            </section>
        `;
    }

    main.querySelectorAll('[data-ghostlab-disabled]').forEach(item => {
        item.addEventListener('click', () => {
            setGhostLabMessage(root, item.dataset.ghostlabDisabled, "locked");
        });
    });
}

function renderGhostLabResearch(root) {
    const main = root?.querySelector('[data-ghostlab-main]');
    if (!main) return;
    main.innerHTML = `
        <section class="ghostlab-panel ghostlab-research">
            <header><h3>Research</h3><span>v1.0 locked / v2.0 planned</span></header>
            <p>Fundament przyszlego drzewa badan GhostLab. Galazie sa widoczne, ale nie zapisuja progresu i nie odblokowuja funkcji.</p>
            <div class="ghostlab-research-layout">
                <div class="ghostlab-research-grid">
                    ${GHOSTLAB_RESEARCH_BRANCHES.map(branch => `
                        <button type="button" class="ghostlab-research-card is-locked" data-ghostlab-research-branch="${escapeHTML(branch.id)}">
                            <span class="ghostlab-research-icon">${escapeHTML(branch.icon)}</span>
                            <strong>${escapeHTML(branch.name)}</strong>
                            <small>${escapeHTML(branch.status)} / tier ${escapeHTML(String(branch.tier))}</small>
                            <em>${escapeHTML(branch.description)}</em>
                            <span class="ghostlab-research-progress">
                                <i style="width:${Number(branch.progress || 0)}%"></i>
                            </span>
                            <b>${escapeHTML(String(branch.progress))}%</b>
                        </button>
                    `).join("")}
                </div>
                <aside class="ghostlab-research-detail" data-ghostlab-research-detail>
                    Wybierz galaz, zeby zobaczyc przyszle unlocki.
                </aside>
            </div>
        </section>
    `;
    main.querySelectorAll('[data-ghostlab-research-branch]').forEach(button => {
        button.addEventListener('click', () => {
            main.querySelectorAll('[data-ghostlab-research-branch]').forEach(item => item.classList.remove('active'));
            button.classList.add('active');
            renderGhostLabResearchBranchDetail(root, button.dataset.ghostlabResearchBranch);
        });
    });
    renderGhostLabResearchBranchDetail(root, GHOSTLAB_RESEARCH_BRANCHES[0]?.id);
    main.querySelector(`[data-ghostlab-research-branch="${GHOSTLAB_RESEARCH_BRANCHES[0]?.id}"]`)?.classList.add('active');
}

function renderGhostLabResearchBranchDetail(root, branchId) {
    const detail = root?.querySelector('[data-ghostlab-research-detail]');
    if (!detail) return;
    const branch = GHOSTLAB_RESEARCH_BRANCHES.find(item => item.id === branchId);
    if (!branch) {
        detail.textContent = "Brak danych galezi Research.";
        return;
    }
    detail.innerHTML = `
        <div class="ghostlab-research-detail-head">
            <span>${escapeHTML(branch.icon)}</span>
            <div>
                <strong>${escapeHTML(branch.name)}</strong>
                <small>Status: ${escapeHTML(branch.status)} / GhostLab required: v2.0</small>
            </div>
        </div>
        <p>${escapeHTML(branch.description)}</p>
        <div class="ghostlab-research-stats">
            <span>Progress <b>${escapeHTML(String(branch.progress))}%</b></span>
            <span>Tier <b>${escapeHTML(String(branch.tier))}</b></span>
        </div>
        <h4>Future unlocks</h4>
        <ul>
            ${branch.unlocks.map(item => `<li>${escapeHTML(item)}</li>`).join("")}
        </ul>
        <div class="ghostlab-research-locked-note">Research Tree planned for v2.0.</div>
    `;
    setGhostLabMessage(root, "Research Tree planned for v2.0. Brak zapisu progresu i brak unlockow.", "locked");
}

function activateGhostLabTab(root, tabName) {
    if (!root) return;
    root.querySelectorAll('[data-ghostlab-tab]').forEach(button => {
        button.classList.toggle('active', button.dataset.ghostlabTab === tabName);
    });
    renderGhostLabTab(tabName, root);
}

function handleGhostLabKeyboardShortcut(root, event) {
    if (!root || !event) return;
    const host = root.closest('.terminal[data-app="ghostlab"]');
    if (host && !host.contains(document.activeElement) && !host.classList.contains('active')) return;
    const editorOpen = Boolean(root.querySelector('.ghostlab-editor'));
    if (!editorOpen && event.key !== "Escape") return;

    if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === "s") {
        event.preventDefault();
        root.querySelector('[data-ghostlab-save-blueprint]')?.click();
    } else if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        root.querySelector('[data-ghostlab-preview-blueprint]')?.click();
    } else if ((event.ctrlKey || event.metaKey) && String(event.key).toLowerCase() === "b") {
        event.preventDefault();
        root.querySelector('[data-ghostlab-compile-project]')?.click();
    } else if (event.key === "Escape") {
        const message = root.querySelector('[data-ghostlab-message]');
        if (message && message.textContent.trim()) {
            event.preventDefault();
            setGhostLabMessage(root, "", "info");
            return;
        }
        if (editorOpen) {
            event.preventDefault();
            activateGhostLabTab(root, "Projects");
        }
    }
}

function wireGhostLabTemplates(root) {
    const main = root?.querySelector('[data-ghostlab-main]');
    if (!main) return;
    main.querySelectorAll('[data-ghostlab-create-template]').forEach(button => {
        button.addEventListener('click', () => {
            const template = GHOSTLAB_TEMPLATES.find(item => item.id === button.dataset.ghostlabCreateTemplate);
            if (template) createGhostLabProjectFromTemplate(root, template);
        });
    });
}

function wireGhostLabProjects(root) {
    const main = root?.querySelector('[data-ghostlab-main]');
    if (!main) return;
    main.querySelector('[data-ghostlab-new-project]')?.addEventListener('click', () => createGhostLabProject(root));
    main.querySelector('[data-ghostlab-open-project]')?.addEventListener('click', () => openGhostLabProject(root));
    main.querySelector('[data-ghostlab-rename-project]')?.addEventListener('click', () => renameGhostLabProject(root));
    main.querySelector('[data-ghostlab-delete-project]')?.addEventListener('click', () => deleteGhostLabProject(root));
    loadGhostLabProjects(root);
}

async function loadGhostLabProjects(root) {
    const list = root?.querySelector('[data-ghostlab-project-list]');
    if (list) list.innerHTML = `<div class="ghostlab-empty">Ladowanie projektow...</div>`;
    setGhostLabWorking(root, "Loading projects...");
    try {
        const res = await fetch('/api/ghostlab/projects');
        const data = await res.json();
        if (!res.ok || data.success === false) {
            setGhostLabMessage(root, data.message || "Nie udalo sie pobrac projektow.", "error");
            return;
        }
        ghostLabState.projects = Array.isArray(data.projects) ? data.projects : [];
        if (!ghostLabState.projects.some(project => project.id === ghostLabState.selectedProjectId)) {
            ghostLabState.selectedProjectId = ghostLabState.projects[0]?.id || null;
        }
        renderGhostLabProjects(root);
        clearGhostLabWorking(root, "Projects loaded");
    } catch (err) {
        console.warn("GhostLab projects load failed", err);
        setGhostLabMessage(root, "Brak polaczenia z Project Managerem.", "error");
    }
}

function renderGhostLabProjects(root) {
    const list = root?.querySelector('[data-ghostlab-project-list]');
    const preview = root?.querySelector('[data-ghostlab-project-preview]');
    if (!list || !preview) return;
    if (!ghostLabState.projects.length) {
        list.innerHTML = `<div class="ghostlab-empty"><strong>No GhostLab projects yet.</strong><span>Start from Templates or Ghost Exchange.</span></div>`;
        preview.textContent = "files.pro_system_projects jest puste.";
        updateGhostLabStatusBar(root);
        return;
    }
    list.innerHTML = ghostLabState.projects.map(project => `
        <button type="button" class="${project.id === ghostLabState.selectedProjectId ? 'active' : ''}" data-ghostlab-project-id="${escapeHTML(project.id)}">
            <strong>${escapeHTML(project.icon || '🧪')} ${escapeHTML(project.name)}</strong>
            <span>${escapeHTML(project.tool_category || 'custom')} / ${escapeHTML(ghostLabProjectStatusLabel(project.status))}</span>
        </button>
    `).join("");
    list.querySelectorAll('[data-ghostlab-project-id]').forEach(button => {
        button.addEventListener('click', () => {
            ghostLabState.selectedProjectId = button.dataset.ghostlabProjectId;
            renderGhostLabProjects(root);
            setGhostLabMessage(root, `Wybrano projekt ${selectedGhostLabProject()?.name || ''}.`, "info");
        });
    });

    const selected = selectedGhostLabProject();
    preview.innerHTML = selected ? `
        <strong>${escapeHTML(selected.icon || '🧪')} ${escapeHTML(selected.name)}</strong>
        <span>ID: ${escapeHTML(selected.id)}</span>
        <span>Slug: ${escapeHTML(selected.slug)}</span>
        <span>Template: ${escapeHTML(selected.template_name || 'custom project')}</span>
        <span>Kategoria: ${escapeHTML(selected.tool_category || '-')}</span>
        <span>Status: ${escapeHTML(ghostLabProjectStatusLabel(selected.status))}</span>
        <span>Builds: ${escapeHTML(String((selected.builds || []).length))}</span>
        <span>Created: ${escapeHTML(selected.created_at || '-')}</span>
        <span>Updated: ${escapeHTML(selected.updated_at || '-')}</span>
    ` : "Wybierz projekt, zeby zobaczyc status workspace.";
    updateGhostLabStatusBar(root);
}

function renderGhostLabEditor(root, project) {
    const main = root?.querySelector('[data-ghostlab-main]');
    if (!main || !project) return;
    ghostLabState.activeProjectId = project.id;
    const fields = GHOSTLAB_EDITOR_FIELDS[project.template_id] || [
        { key: "notes", label: "Notes", type: "textarea" }
    ];
    const blueprint = project.blueprint && typeof project.blueprint === "object" ? project.blueprint : {};
    main.innerHTML = `
        <section class="ghostlab-panel ghostlab-editor">
            <header>
                <h3>${escapeHTML(project.icon || '[G]')} ${escapeHTML(project.name)}</h3>
                <span>${GHOSTLAB_VERSION} Stable Workflow</span>
            </header>
            <div class="ghostlab-editor-meta">
                <span>Template: ${escapeHTML(project.template_name || 'custom project')}</span>
                <span>Category: ${escapeHTML(project.tool_category || 'custom')}</span>
                <span>Status: ${escapeHTML(ghostLabProjectStatusLabel(project.status))}</span>
                <span>ID: ${escapeHTML(project.id)}</span>
            </div>
            <div class="ghostlab-editor-grid">
                ${fields.map(field => renderGhostLabEditorField(field, blueprint[field.key])).join("")}
            </div>
            <div class="ghostlab-editor-feedback">
                <div class="ghostlab-validation-panel" data-ghostlab-validation-panel></div>
                <div class="ghostlab-preview-panel" data-ghostlab-preview-panel></div>
            </div>
            <div class="ghostlab-build-panel" data-ghostlab-build-panel>
                ${renderGhostLabBuildHistory(project)}
            </div>
            <div class="ghostlab-publisher-panel" data-ghostlab-publisher-panel>
                ${renderGhostLabPublisherPipeline(project)}
            </div>
            <div class="ghostlab-editor-actions">
                <button type="button" data-ghostlab-preview-blueprint title="Validate blueprint and refresh preview. Shortcut: Ctrl+Enter">Validate</button>
                <button type="button" data-ghostlab-preview-blueprint title="Preview compiled blueprint metadata without saving.">Preview</button>
                <button type="button" data-ghostlab-save-blueprint title="Save blueprint draft. Shortcut: Ctrl+S">Save Draft</button>
                <button type="button" data-ghostlab-back-projects title="Return to project manager. Shortcut: Esc">Back to Projects</button>
                <button type="button" data-ghostlab-compile-project title="Compile current validated blueprint. Shortcut: Ctrl+B">Compile</button>
                <button type="button" data-ghostlab-export-project title="Export project snapshot as .glab file.">Export</button>
                <button type="button" data-ghostlab-publish-project title="Run Publisher pipeline and send artifact to Googleplex.">Publisher</button>
            </div>
        </section>
    `;
    main.querySelectorAll('[data-ghostlab-preview-blueprint]').forEach(button => {
        button.addEventListener('click', () => {
            setGhostLabWorking(root, "Validating...");
            const validation = refreshGhostLabEditorFeedback(root, project);
            setGhostLabMessage(root, validation.valid ? "Preview ready. Blueprint valid." : "Preview ready. Blueprint needs fixes.", validation.valid ? "info" : "error");
        });
    });
    main.querySelector('[data-ghostlab-save-blueprint]')?.addEventListener('click', () => saveGhostLabBlueprint(root, project.id));
    main.querySelector('[data-ghostlab-compile-project]')?.addEventListener('click', () => compileGhostLabProject(root, project.id));
    main.querySelector('[data-ghostlab-export-project]')?.addEventListener('click', () => exportGhostLabProject(root, project.id));
    main.querySelector('[data-ghostlab-publish-project]')?.addEventListener('click', () => publishGhostLabProject(root, project.id));
    main.querySelector('[data-ghostlab-back-projects]')?.addEventListener('click', () => activateGhostLabTab(root, "Projects"));
    main.querySelectorAll('[data-ghostlab-disabled]').forEach(item => {
        item.addEventListener('click', () => setGhostLabMessage(root, item.dataset.ghostlabDisabled, "locked"));
    });
    refreshGhostLabEditorFeedback(root, project);
    updateGhostLabStatusBar(root);
}

function renderGhostLabEditorField(field, value) {
    const safeKey = escapeHTML(field.key);
    const safeLabel = escapeHTML(field.label);
    if (field.type === "textarea") {
        return `
            <label class="ghostlab-editor-field">
                <span>${safeLabel}</span>
                <textarea data-ghostlab-blueprint-key="${safeKey}">${escapeHTML(value ?? "")}</textarea>
            </label>
        `;
    }
    if (field.type === "checkbox") {
        return `
            <label class="ghostlab-editor-field is-check">
                <input type="checkbox" data-ghostlab-blueprint-key="${safeKey}" ${value ? "checked" : ""}>
                <span>${safeLabel}</span>
            </label>
        `;
    }
    return `
        <label class="ghostlab-editor-field">
            <span>${safeLabel}</span>
            <input type="${field.type === "number" ? "number" : "text"}" data-ghostlab-blueprint-key="${safeKey}" value="${escapeHTML(value ?? "")}">
        </label>
    `;
}

function renderGhostLabBuildHistory(project) {
    const builds = Array.isArray(project?.builds) ? project.builds : [];
    if (!builds.length) {
        return `
            <strong>Builds</strong>
            <span>Brak buildow. Compile utworzy pierwszy artefakt projektu.</span>
        `;
    }
    return `
        <strong>Builds</strong>
        <div class="ghostlab-build-list">
            ${builds.slice().reverse().map(build => `
                <span>v${escapeHTML(String(build.version || '-'))} / ${escapeHTML(build.status || 'compiled')} / ${escapeHTML(build.created_at || '-')}</span>
            `).join("")}
        </div>
    `;
}

function renderGhostLabPublisherPipeline(project) {
    const hasBlueprint = !!(project?.blueprint && typeof project.blueprint === "object");
    const hasBuild = Array.isArray(project?.builds) && project.builds.length > 0;
    const hasArtifact = !!(project?.artifact && project.artifact.artifact_id);
    const isPublished = project?.status === "published" || !!project?.googleplex_app_id;
    const contract = project?.publisher_contract || {};
    const steps = [
        ["Blueprint", hasBlueprint],
        ["Compile", hasBuild],
        ["Artifact", hasArtifact],
        ["Publisher", isPublished],
        ["Googleplex", isPublished]
    ];
    return `
        <strong>Publisher Pipeline</strong>
        <div class="ghostlab-pipeline">
            ${steps.map(([label, done]) => `
                <span class="${done ? 'done' : ''}">${escapeHTML(label)}</span>
            `).join("")}
        </div>
        <div class="ghostlab-contract-preview">
            <span>type: <b>${escapeHTML(contract.type || 'pro-system-tool')}</b></span>
            <span>family: <b>${escapeHTML(contract.tool_family || '-')}</b></span>
            <span>mode: <b>${escapeHTML(contract.tool_mode || '-')}</b></span>
            <span>map: <b>${escapeHTML((contract.map_actions || []).join(', ') || 'desktop')}</b></span>
            <span>targets: <b>${escapeHTML((contract.target_types || []).join(', ') || '-')}</b></span>
            <span>ops: <b>${escapeHTML((contract.operation_types || []).join(', ') || 'custom runtime')}</b></span>
            <span>data: <b>${escapeHTML((contract.resource_types || []).join(', ') || '-')}</b></span>
        </div>
        <em>${isPublished ? `Googleplex ID: ${escapeHTML(project.googleplex_app_id || '-')}` : 'Publisher zapisze pro-system-tool w Googleplex po poprawnym buildzie.'}</em>
    `;
}

function collectGhostLabBlueprint(root) {
    const blueprint = {};
    root?.querySelectorAll('[data-ghostlab-blueprint-key]').forEach(input => {
        const key = input.dataset.ghostlabBlueprintKey;
        if (!key) return;
        if (input.type === "checkbox") {
            blueprint[key] = input.checked;
        } else if (input.type === "number") {
            const parsed = Number(input.value);
            blueprint[key] = Number.isFinite(parsed) ? parsed : 0;
        } else {
            blueprint[key] = input.value || "";
        }
    });
    return blueprint;
}

function validateGhostLabBlueprint(project, blueprint) {
    const errors = [];
    const warnings = [];
    const numberBetween = (key, label, min, max) => {
        const value = blueprint[key];
        if (typeof value !== "number" || !Number.isFinite(value)) {
            errors.push(`${label} musi byc liczba.`);
            return null;
        }
        if (value < min || value > max) errors.push(`${label} musi byc w zakresie ${min}-${max}.`);
        return value;
    };
    const requiredText = (key, label, max = 240) => {
        const value = String(blueprint[key] || "").trim();
        if (!value) errors.push(`${label} nie moze byc puste.`);
        if (value.length > max) errors.push(`${label} jest za dlugie.`);
        return value;
    };

    switch (project?.template_id) {
        case "financial_sniffer": {
            const steal = numberBetween("steal_percent", "Steal %", 1, 8);
            const detection = numberBetween("detection_percent", "Detection %", 0, 95);
            numberBetween("cooldown_minutes", "Cooldown", 5, 1440);
            requiredText("success_message", "Success message");
            requiredText("failure_message", "Failure message");
            requiredText("reward_note", "Rewards", 160);
            if (steal && steal > 6) warnings.push("Steal % powyzej 6 zwiekszy balansowe ryzyko w compilerze.");
            if (detection !== null && detection < 10) warnings.push("Detection % ponizej 10 moze zostac podbite w compilerze.");
            break;
        }
        case "friend_kicker":
            numberBetween("success_percent", "Success %", 1, 85);
            numberBetween("detection_percent", "Detection %", 0, 95);
            requiredText("target_policy", "Targets", 80);
            requiredText("victim_message", "Victim system message");
            requiredText("contact_message", "Contact system message");
            break;
        case "security_panel_proxy":
            requiredText("allowed_switches", "Allowed switches", 120);
            requiredText("presets", "Presets", 160);
            requiredText("rules", "Rules");
            requiredText("conflict_matrix", "Conflict matrix");
            break;
        case "system_log_reader":
            numberBetween("log_limit", "Log limit", 1, 5);
            ["include_type", "include_status", "include_created_at"].forEach(key => {
                if (typeof blueprint[key] !== "boolean") errors.push(`${key} musi byc boolean.`);
            });
            requiredText("redaction_policy", "Redaction policy", 120);
            break;
        case "arsenal_cleaner":
            numberBetween("success_percent", "Success %", 1, 80);
            numberBetween("detection_percent", "Detection %", 0, 95);
            requiredText("target_policy", "Targets", 100);
            requiredText("protected_apps", "Protected apps");
            if (typeof blueprint.remove_tools_file !== "boolean") errors.push("Remove files/tools entry musi byc boolean.");
            break;
        default:
            requiredText("notes", "Notes");
    }

    return { valid: errors.length === 0, errors, warnings };
}

function buildGhostLabBlueprintPreview(project, blueprint, validation) {
    const lines = [
        `Project: ${project?.name || '-'}`,
        `Template: ${project?.template_name || 'custom project'}`,
        `Category: ${project?.tool_category || 'custom'}`,
        `Status: ${validation.valid ? 'draft valid' : 'needs fixes'}`
    ];
    if (project?.latest_build) {
        lines.push(`Latest build: v${project.latest_build.version} / ${project.latest_build.status}`);
    } else {
        lines.push(`Latest build: none`);
    }
    if (project?.template_id === "financial_sniffer") {
        lines.push(`Effect: steal up to ${blueprint.steal_percent || '?'}% HC`);
        lines.push(`Detection: ${blueprint.detection_percent ?? '?'}%`);
        lines.push(`Cooldown: ${blueprint.cooldown_minutes || '?'} min`);
    } else if (project?.template_id === "friend_kicker") {
        lines.push(`Effect: random contact disruption`);
        lines.push(`Success: ${blueprint.success_percent || '?'}%`);
        lines.push(`Target policy: ${blueprint.target_policy || '-'}`);
    } else if (project?.template_id === "security_panel_proxy") {
        lines.push(`Effect: remote boolean security panel`);
        lines.push(`Presets: ${blueprint.presets || '-'}`);
        lines.push(`Rules: ${blueprint.rules || '-'}`);
    } else if (project?.template_id === "system_log_reader") {
        lines.push(`Effect: read ${blueprint.log_limit || '?'} system logs`);
        lines.push(`Includes status: ${blueprint.include_status ? 'yes' : 'no'}`);
        lines.push(`Policy: ${blueprint.redaction_policy || '-'}`);
    } else if (project?.template_id === "arsenal_cleaner") {
        lines.push(`Effect: random non-core app cleanup`);
        lines.push(`Success: ${blueprint.success_percent || '?'}%`);
        lines.push(`Protected: ${blueprint.protected_apps || '-'}`);
    } else {
        lines.push(`Notes: ${blueprint.notes || '-'}`);
    }
    return lines;
}

function refreshGhostLabEditorFeedback(root, project) {
    const validationPanel = root?.querySelector('[data-ghostlab-validation-panel]');
    const previewPanel = root?.querySelector('[data-ghostlab-preview-panel]');
    if (!validationPanel || !previewPanel) return { valid: true, errors: [], warnings: [] };
    const blueprint = collectGhostLabBlueprint(root);
    const validation = validateGhostLabBlueprint(project, blueprint);
    const preview = buildGhostLabBlueprintPreview(project, blueprint, validation);
    validationPanel.innerHTML = `
        <strong>${validation.valid ? 'VALIDATION OK' : 'VALIDATION ERRORS'}</strong>
        ${validation.errors.length ? `<ul>${validation.errors.map(item => `<li>${escapeHTML(item)}</li>`).join("")}</ul>` : '<span>Blueprint gotowy do zapisu jako draft.</span>'}
        ${validation.warnings.length ? `<em>${validation.warnings.map(escapeHTML).join(" | ")}</em>` : ''}
    `;
    validationPanel.classList.toggle('is-error', !validation.valid);
    previewPanel.innerHTML = `
        <strong>Blueprint Preview</strong>
        <pre>${escapeHTML(preview.join("\n"))}</pre>
    `;
    return validation;
}

async function saveGhostLabBlueprint(root, projectId) {
    if (!projectId) {
        setGhostLabMessage(root, "Nie wybrano projektu.", "error");
        return;
    }
    const project = ghostLabState.projects.find(item => item.id === projectId) || selectedGhostLabProject();
    const validation = refreshGhostLabEditorFeedback(root, project);
    if (!validation.valid) {
        setGhostLabMessage(root, "Popraw bledy walidacji przed zapisem draftu.", "error");
        return;
    }
    setGhostLabWorking(root, "Saving draft...");
    try {
        const res = await fetch(`/api/ghostlab/projects/${encodeURIComponent(projectId)}/blueprint`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blueprint: collectGhostLabBlueprint(root) })
        });
        const data = await res.json();
        if (!res.ok || data.success === false) {
            setGhostLabMessage(root, data.message || "Nie udalo sie zapisac blueprintu.", "error");
            return;
        }
        ghostLabState.projects = data.projects || [];
        ghostLabState.selectedProjectId = data.project?.id || projectId;
        ghostLabState.activeProjectId = data.project?.id || projectId;
        setGhostLabMessage(root, data.message || "Draft zapisany.", "info");
        renderGhostLabEditor(root, data.project);
    } catch (err) {
        console.warn("GhostLab blueprint save failed", err);
        setGhostLabMessage(root, "Brak polaczenia z edytorem blueprintu.", "error");
    }
}

async function compileGhostLabProject(root, projectId) {
    if (!projectId) {
        setGhostLabMessage(root, "Nie wybrano projektu.", "error");
        return;
    }
    const project = ghostLabState.projects.find(item => item.id === projectId) || selectedGhostLabProject();
    const validation = refreshGhostLabEditorFeedback(root, project);
    if (!validation.valid) {
        setGhostLabMessage(root, "Compile zatrzymany. Popraw bledy blueprintu.", "error");
        return;
    }
    setGhostLabWorking(root, "Compiling...");
    try {
        const res = await fetch(`/api/ghostlab/projects/${encodeURIComponent(projectId)}/compile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ blueprint: collectGhostLabBlueprint(root) })
        });
        const data = await res.json();
        if (!res.ok || data.success === false) {
            setGhostLabMessage(root, data.message || "Compile nie powiodl sie.", "error");
            return;
        }
        ghostLabState.projects = data.projects || [];
        ghostLabState.selectedProjectId = data.project?.id || projectId;
        ghostLabState.activeProjectId = data.project?.id || projectId;
        renderGhostLabEditor(root, data.project);
        setGhostLabMessage(root, data.message || "Build skompilowany.", "info");
    } catch (err) {
        console.warn("GhostLab compile failed", err);
        setGhostLabMessage(root, "Brak polaczenia z compilerem.", "error");
    }
}

async function exportGhostLabProject(root, projectId) {
    if (!projectId) {
        setGhostLabMessage(root, "Nie wybrano projektu do exportu.", "error");
        return;
    }
    setGhostLabWorking(root, "Exporting...");
    try {
        const res = await fetch(`/api/ghostlab/projects/${encodeURIComponent(projectId)}/export`);
        if (!res.ok) {
            const data = await res.json().catch(() => ({}));
            setGhostLabMessage(root, data.message || "Export nie powiodl sie.", "error");
            return;
        }
        const blob = await res.blob();
        const disposition = res.headers.get("Content-Disposition") || "";
        const match = disposition.match(/filename=([^;]+)/i);
        const filename = match ? match[1].replace(/"/g, "") : "ghost_project.glab";
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(url);
        setGhostLabMessage(root, `Export gotowy: ${filename}`, "info");
    } catch (err) {
        console.warn("GhostLab export failed", err);
        setGhostLabMessage(root, "Brak polaczenia z exportem.", "error");
    }
}

async function publishGhostLabProject(root, projectId) {
    if (!projectId) {
        setGhostLabMessage(root, "Nie wybrano projektu do Publishera.", "error");
        return;
    }
    const project = ghostLabState.projects.find(item => item.id === projectId) || selectedGhostLabProject();
    const validation = refreshGhostLabEditorFeedback(root, project);
    if (!validation.valid) {
        setGhostLabMessage(root, "Publisher zatrzymany. Popraw blueprint.", "error");
        return;
    }
    setGhostLabWorking(root, "Publishing...");
    try {
        const res = await fetch(`/api/ghostlab/projects/${encodeURIComponent(projectId)}/publisher`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (!res.ok || data.success === false) {
            setGhostLabMessage(root, data.message || "Publisher nie powiodl sie.", "error");
            return;
        }
        ghostLabState.projects = data.projects || [];
        ghostLabState.selectedProjectId = data.project?.id || projectId;
        ghostLabState.activeProjectId = data.project?.id || projectId;
        renderGhostLabEditor(root, data.project);
        setGhostLabMessage(root, data.message || "Publisher zakonczony.", "info");
        if (typeof window.refreshDesktop === "function") window.refreshDesktop();
    } catch (err) {
        console.warn("GhostLab publisher failed", err);
        setGhostLabMessage(root, "Brak polaczenia z Publisherem.", "error");
    }
}

function selectedGhostLabProject() {
    return ghostLabState.projects.find(project => project.id === ghostLabState.selectedProjectId) || null;
}

async function createGhostLabProject(root) {
    const input = root?.querySelector('[data-ghostlab-project-name]');
    const name = (input?.value || "").trim();
    if (!name) {
        setGhostLabMessage(root, "Podaj nazwe projektu.", "error");
        return;
    }
    setGhostLabWorking(root, "Creating project...");
    try {
        const res = await fetch('/api/ghostlab/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (!res.ok || data.success === false) {
            setGhostLabMessage(root, data.message || "Nie udalo sie utworzyc projektu.", "error");
            return;
        }
        if (input) input.value = "";
        ghostLabState.projects = data.projects || [];
        ghostLabState.selectedProjectId = data.project?.id || ghostLabState.selectedProjectId;
        renderGhostLabProjects(root);
        setGhostLabMessage(root, data.message || "Projekt utworzony.", "info");
    } catch (err) {
        console.warn("GhostLab create project failed", err);
        setGhostLabMessage(root, "Brak polaczenia z Project Managerem.", "error");
    }
}

async function createGhostLabProjectFromTemplate(root, template) {
    const payload = {
        name: `${template.name} Project`,
        template_id: template.id,
        template_name: template.name,
        tool_category: template.tool_category || template.category,
        icon: template.icon
    };
    setGhostLabWorking(root, "Creating project from template...");
    try {
        const res = await fetch('/api/ghostlab/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok || data.success === false) {
            setGhostLabMessage(root, data.message || "Nie udalo sie utworzyc projektu z szablonu.", "error");
            return;
        }
        ghostLabState.projects = data.projects || [];
        ghostLabState.selectedProjectId = data.project?.id || ghostLabState.selectedProjectId;
        activateGhostLabTab(root, "Projects");
        setGhostLabMessage(root, "Projekt utworzony z szablonu. Edytor bedzie dostepny w GhostLab v0.4.", "info");
    } catch (err) {
        console.warn("GhostLab template project create failed", err);
        setGhostLabMessage(root, "Brak polaczenia z Project Managerem.", "error");
    }
}

function openGhostLabProject(root) {
    const selected = selectedGhostLabProject();
    if (!selected) {
        setGhostLabMessage(root, "Wybierz projekt do otwarcia.", "error");
        return;
    }
    ghostLabState.activeProjectId = selected.id;
    renderGhostLabEditor(root, selected);
    setGhostLabMessage(root, `Otworzono edytor projektu ${selected.name}.`, "info");
}

async function renameGhostLabProject(root) {
    const selected = selectedGhostLabProject();
    const input = root?.querySelector('[data-ghostlab-project-name]');
    const name = (input?.value || "").trim();
    if (!selected) {
        setGhostLabMessage(root, "Wybierz projekt do zmiany nazwy.", "error");
        return;
    }
    if (!name) {
        setGhostLabMessage(root, "Wpisz nowa nazwe w polu projektu.", "error");
        return;
    }
    setGhostLabWorking(root, "Renaming project...");
    try {
        const res = await fetch(`/api/ghostlab/projects/${encodeURIComponent(selected.id)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (!res.ok || data.success === false) {
            setGhostLabMessage(root, data.message || "Nie udalo sie zmienic nazwy.", "error");
            return;
        }
        if (input) input.value = "";
        ghostLabState.projects = data.projects || [];
        ghostLabState.selectedProjectId = data.project?.id || selected.id;
        renderGhostLabProjects(root);
        setGhostLabMessage(root, data.message || "Projekt zmieniony.", "info");
    } catch (err) {
        console.warn("GhostLab rename project failed", err);
        setGhostLabMessage(root, "Brak polaczenia z Project Managerem.", "error");
    }
}

async function deleteGhostLabProject(root) {
    const selected = selectedGhostLabProject();
    if (!selected) {
        setGhostLabMessage(root, "Wybierz projekt do usuniecia.", "error");
        return;
    }
    if (!confirm(`Usunac projekt ${selected.name}?`)) return;
    setGhostLabWorking(root, "Deleting project...");
    try {
        const res = await fetch(`/api/ghostlab/projects/${encodeURIComponent(selected.id)}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (!res.ok || data.success === false) {
            setGhostLabMessage(root, data.message || "Nie udalo sie usunac projektu.", "error");
            return;
        }
        ghostLabState.projects = data.projects || [];
        ghostLabState.selectedProjectId = ghostLabState.projects[0]?.id || null;
        renderGhostLabProjects(root);
        setGhostLabMessage(root, data.message || "Projekt usuniety.", "info");
    } catch (err) {
        console.warn("GhostLab delete project failed", err);
        setGhostLabMessage(root, "Brak polaczenia z Project Managerem.", "error");
    }
}

function createGhostLabHub() {
    const existing = document.querySelector('.terminal[data-app="ghostlab"]');
    if (existing) {
        bringWindowToFront(existing);
        return existing;
    }

    const term = document.createElement('div');
    term.className = 'terminal ghostlab-window';
    term.tabIndex = 0;
    term.dataset.app = 'ghostlab';
    term.dataset.appTitle = 'GhostLab';
    term.dataset.appIcon = '\u{1F9EA}';
    const position = findAvailablePosition(760, 560);
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `760px`;
    term.style.height = `560px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';
    term.innerHTML = `
        <div class="title-bar">
            GhostLab ${GHOSTLAB_VERSION}
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div class="ghostlab-shell"></div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.addEventListener('mousedown', () => term.focus());
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());
    const shell = term.querySelector('.ghostlab-shell');
    term.addEventListener('keydown', event => handleGhostLabKeyboardShortcut(shell, event));
    renderGhostLabWorkspace(shell);
    bringWindowToFront(term);
    term.focus();
    return term;
}

function normalizeToolSelectionPayload(payload) {
    const apps = Array.isArray(payload?.matching_apps) ? payload.matching_apps : [];
    return {
        ...payload,
        matching_apps: apps,
        pending_action: payload?.pending_action || {},
        app_ids: new Set(apps.map(app => String(app.id || ""))),
        app_names: new Set(apps.map(app => String(app.name || ""))),
        tool_files: new Set(apps.map(app => String(app.tool_file || `${app.name || app.id}.sh`))),
        open_tools: true
    };
}

function getToolSelectionAppForFile(filename) {
    const selection = window.activeToolSelection;
    if (!selection || !Array.isArray(selection.matching_apps)) return null;
    const normalizedFilename = String(filename || "");
    return selection.matching_apps.find(app => {
        const name = String(app.name || app.id || "");
        const toolFile = String(app.tool_file || `${name}.sh`);
        return normalizedFilename === toolFile || normalizedFilename === `${name}.sh` || normalizedFilename === name;
    }) || null;
}

function getHackFlowId(selection = window.activeToolSelection) {
    const pending = selection?.pending_action || {};
    if (pending._flow_id) return String(pending._flow_id);
    const generated = `hf-fe-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
    if (selection && selection.pending_action) {
        selection.pending_action._flow_id = generated;
    }
    return generated;
}

function forEachOpenMapWindow(callback) {
    document.querySelectorAll('.terminal[data-app="map"] iframe').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow) callback(mapWindow);
        } catch (err) {
            console.warn("Nie udało się zsynchronizować okna mapy:", err);
        }
    });
}

function pauseOpenMapOptionalRefresh(reason = "map_tool_picker") {
    forEachOpenMapWindow(mapWindow => {
        if (typeof mapWindow.pauseMapOptionalRefresh === "function") {
            mapWindow.pauseMapOptionalRefresh(reason);
        }
    });
}

function resumeOpenMapOptionalRefresh(delayMs = 1200) {
    forEachOpenMapWindow(mapWindow => {
        if (typeof mapWindow.resumeMapOptionalRefresh === "function") {
            mapWindow.resumeMapOptionalRefresh(delayMs);
        }
    });
}

function notifyOpenMapsHackActionStarted(flowId, payload = {}) {
    forEachOpenMapWindow(mapWindow => {
        if (typeof mapWindow.startHackActionSpinner === "function") {
            mapWindow.startHackActionSpinner(flowId, payload);
        }
    });
}

function notifyOpenMapsHackActionStopped(flowId) {
    forEachOpenMapWindow(mapWindow => {
        if (typeof mapWindow.stopHackActionSpinner === "function") {
            mapWindow.stopHackActionSpinner(flowId);
        }
    });
}

async function selectMapActionTool(appId) {
    const selection = window.activeToolSelection;
    if (!selection || !selection.pending_action) {
        hackFlowDebug("", "desktop", "tool_picker_missing_selection", { appId });
        addSystemMessage("warning", "\u{1F6E0}\uFE0F Narz\u0119dzia", "Brak aktywnej akcji mapy.");
        return;
    }
    if (selection.in_flight) {
        hackFlowDebug(getHackFlowId(selection), "desktop", "tool_picker_skip_in_flight", { appId });
        return;
    }

    const app = selection.matching_apps.find(item => (
        String(item.id || "") === String(appId || "")
        || String(item.name || "") === String(appId || "")
    ));
    if (!app) {
        hackFlowDebug(getHackFlowId(selection), "desktop", "tool_picker_app_not_found", { appId });
        addSystemMessage("warning", "\u{1F6E0}\uFE0F Narz\u0119dzia", "To narz\u0119dzie nie pasuje do aktywnej akcji.");
        return;
    }

    let stopPickerWaitLog = null;
    let provisionalSession = null;
    try {
        selection.in_flight = true;
        const flowId = getHackFlowId(selection);
        const selectionRequestKey = `${flowId}:${String(app.id || app.name || appId || "")}`;
        window.__lastHackFlowId = flowId;
        appFlowTrace(flowId, "tool_picker_use_start", {
            app_id: app.id,
            app_name: app.name,
            action: selection.pending_action && selection.pending_action.action,
            selectionRequestKey
        });
        hackFlowDebug(flowId, "desktop", "tool_picker_use_start", {
            app_id: app.id,
            app_name: app.name,
            action: selection.pending_action && selection.pending_action.action,
            pending_action: selection.pending_action,
            selectionRequestKey
        });
        window.__pendingMapToolSelectionKeys = window.__pendingMapToolSelectionKeys || new Set();
        if (window.__pendingMapToolSelectionKeys.has(selectionRequestKey)) {
            hackFlowDebug(flowId, "desktop", "tool_picker_skip_pending_key", { selectionRequestKey });
            return;
        }
        window.__pendingMapToolSelectionKeys.add(selectionRequestKey);
        selection.pending_request_key = selectionRequestKey;
        try {
            provisionalSession = beginProvisionalLaunch(selection, app);
        } catch (error) {
            console.warn("[app launch] Nie udalo sie utworzyc provisional window", error);
            provisionalSession = null;
        }
        if (provisionalSession?.appWindow?.isConnected) {
            // The provisional window has taken over presentation. Keep the
            // selection object alive for the request, but remove the picker
            // immediately instead of leaving two competing launch windows.
            closeMapToolPicker(false);
            appFlowTrace(flowId, "tool_picker_closed_on_provisional", {
                app_id: app.id,
                app_name: app.name,
                session_key: provisionalSession.sessionKey
            });
        }
        notifyOpenMapsHackActionStarted(flowId, {
            ...selection.pending_action,
            selected_app_id: app.id,
            selected_app_name: app.name
        });
        pauseOpenMapOptionalRefresh("hack_action_tool_use");
        updateMapToolPickerBusyState(true, app.id);
        stopPickerWaitLog = startAppWaitLog(document.querySelector('.terminal[data-app="map-tool-picker"]'), {
            prefix: "GhostSystem 2108"
        });
        const requestStartedAt = performance.now();
        const clientActionHeaderKey = safeHttpHeaderValue(selection.pending_action?._client_action_key || selectionRequestKey);
        const res = await fetch('/hack-action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Hack-Flow-Id': flowId,
                'X-Client-Action-Key': clientActionHeaderKey
            },
            body: JSON.stringify({
                ...selection.pending_action,
                selected_app_id: app.id
            })
        });
        const data = await res.json();
        const queuedApp = (Array.isArray(data.added_apps) ? data.added_apps : []).find(item => {
            const queuedId = String(item?.app_id || item?.id || item?.name || "").trim();
            return normalizeLaunchCorrelation(queuedId) === normalizeLaunchCorrelation(app.id || app.name);
        });
        if (queuedApp) bindProvisionalApplicationReceipt(provisionalSession, {
            receipt: queuedApp.receipt,
            client_action_key: queuedApp.client_action_key || clientActionHeaderKey,
            action: queuedApp.action || selection.pending_action?.action
        });
        appFlowTrace(flowId, "tool_picker_hack_action_response", {
            app_id: app.id,
            app_name: app.name,
            status: res.status,
            elapsed_ms: Math.round(performance.now() - requestStartedAt),
            duplicate: Boolean(data.duplicate),
            added_apps: data.added_apps || [],
            created_operations: (data.created_operations || []).map(op => op && op.operation_id)
        });
        hackFlowDebug(flowId, "desktop", "tool_picker_response", {
            status: res.status,
            ok: res.ok,
            blocked: Boolean(data.blocked),
            duplicate: Boolean(data.duplicate),
            added_apps: data.added_apps || [],
            created_operations: (data.created_operations || []).map(op => op && op.operation_id),
            debug_flow: data.debug_flow || null
        });
        if (!res.ok || data.blocked) {
            updateProvisionalApplicationSession(
                provisionalSession,
                "failed",
                data.status || "Backend odrzucil uruchomienie aplikacji."
            );
            addSystemMessage("warning", "\u{1F6E0}\uFE0F Narz\u0119dzia", data.status || "Nie uda\u0142o si\u0119 uruchomi\u0107 narz\u0119dzia.");
            selection.in_flight = false;
            updateMapToolPickerBusyState(false);
            return;
        }
        if (data.duplicate) {
            updateProvisionalApplicationSession(
                provisionalSession,
                "booting",
                "Oczekiwanie na stan aplikacji..."
            );
            hackFlowDebug(flowId, "desktop", "tool_picker_duplicate_response", {
                idempotent_replay: Boolean(data.idempotent_replay),
                status: data.status || ""
            });
            if (data.target) {
                updateToolbarAimedTarget(data.target);
            }
            window.activeToolSelection = null;
            closeMapToolPicker(false);
            return;
        }

        window.activeToolSelection = null;
        closeMapToolPicker(false);
        updateProvisionalApplicationSession(
            provisionalSession,
            "booting",
            "Aplikacja przyjeta. Oczekiwanie na runtime..."
        );
        if (data.target) {
            updateToolbarAimedTarget(data.target);
            appFlowTrace(flowId, "toolbar_dot_updated_from_tool_picker", {
                target_label: data.target.label || data.target.display_label || data.target.name || "",
                actions_allowed: data.target.actions_allowed || null
            });
        }
        addSystemMessage("success", "\u{1F6E0}\uFE0F Narz\u0119dzie", data.status || `Uruchomiono ${app.name || app.id}.`);
        if (typeof notifyOpenMapsOperationsChanged === "function") {
            await notifyOpenMapsOperationsChanged();
            appFlowTrace(flowId, "operations_refresh_after_tool_picker", {
                app_id: app.id,
                app_name: app.name
            });
        }
        hackFlowDebug(flowId, "desktop", "tool_picker_success", {
            app_id: app.id,
            app_name: app.name
        });
    } catch (err) {
        updateProvisionalApplicationSession(
            provisionalSession,
            "failed",
            "Blad polaczenia podczas uruchamiania aplikacji."
        );
        hackFlowDebug(selection ? getHackFlowId(selection) : "", "desktop", "tool_picker_error", {
            message: err && err.message ? err.message : String(err)
        });
        console.error("Błąd wyboru narzędzia:", err);
        addSystemMessage("danger", "\u{1F6E0}\uFE0F Narz\u0119dzia", "B\u0142\u0105d po\u0142\u0105czenia podczas wyboru narz\u0119dzia.");
        if (selection) {
            selection.in_flight = false;
            updateMapToolPickerBusyState(false);
        }
    } finally {
        if (typeof stopPickerWaitLog === "function") {
            stopPickerWaitLog();
        }
        notifyOpenMapsHackActionStopped(getHackFlowId(selection));
        resumeOpenMapOptionalRefresh(1200);
        if (selection?.pending_request_key && window.__pendingMapToolSelectionKeys) {
            window.__pendingMapToolSelectionKeys.delete(selection.pending_request_key);
            hackFlowDebug(getHackFlowId(selection), "desktop", "tool_picker_pending_key_released", {
                selectionRequestKey: selection.pending_request_key
            });
            delete selection.pending_request_key;
        }
    }
}

function closeMapToolPicker(clearSelection = true) {
    const existing = document.querySelector('.terminal[data-app="map-tool-picker"]');
    if (existing) existing.remove();
    if (clearSelection) {
        window.activeToolSelection = null;
    }
}

function updateMapToolPickerBusyState(isBusy, activeAppId = "") {
    const picker = document.querySelector('.terminal[data-app="map-tool-picker"]');
    if (!picker) return;
    picker.dataset.busy = isBusy ? "1" : "0";
    picker.querySelectorAll('[data-map-tool-use]').forEach(button => {
        const isActive = String(button.dataset.appId || "") === String(activeAppId || "");
        button.disabled = Boolean(isBusy);
        button.textContent = isBusy && isActive ? "Uruchamiam..." : "U\u017cyj";
    });
    picker.querySelectorAll('[data-map-tool-open-files]').forEach(button => {
        button.disabled = Boolean(isBusy);
    });
}

function renderMapToolPickerApp(app) {
    const appId = String(app.id || app.name || "");
    const title = app.name || app.id || "Narzedzie";
    const toolFile = app.tool_file || app.file_name || app.project_file || `${title}.sh`;
    const family = app.tool_family || app.type || app.category || "tool";
    const mode = app.tool_mode || app.scanner_mode || app.operation_mode || "runtime";
    const quality = app.quality_score ?? app.quality ?? "-";
    const power = app.power_score ?? app.power ?? "-";
    const diskUsage = app.disk_usage || app.install_size || app.file_size || 0;
    const diskLine = Number(diskUsage) ? `<span>Dysk ${escapeHTML(formatStorageSize(diskUsage))}</span>` : "";
    return `
        <article class="map-tool-picker-card">
            <div class="map-tool-picker-card__icon">${escapeHTML(app.icon || "\u{1F6E0}\uFE0F")}</div>
            <div class="map-tool-picker-card__body">
                <div class="map-tool-picker-card__title" title="${escapeHTML(title)}">${escapeHTML(title)}</div>
                <div class="map-tool-picker-card__file" title="${escapeHTML(toolFile)}">${escapeHTML(toolFile)}</div>
                <div class="map-tool-picker-card__meta">
                    <span>${escapeHTML(family)}</span>
                    <span>${escapeHTML(mode)}</span>
                    <span>Q ${escapeHTML(String(quality))}</span>
                    <span>P ${escapeHTML(String(power))}</span>
                    ${diskLine}
                </div>
            </div>
            <button class="map-tool-picker-use" data-map-tool-use data-app-id="${escapeHTML(appId)}" type="button">
                U\u017cyj
            </button>
        </article>
    `;
}

function createMapToolPicker(selection) {
    closeMapToolPicker(false);
    const apps = Array.isArray(selection?.matching_apps) ? selection.matching_apps : [];
    if (!apps.length) {
        return createFileManager({ toolSelection: selection });
    }

    const position = findAvailablePosition(520, 420);
    const term = document.createElement('div');
    term.className = 'terminal map-tool-picker-window';
    term.dataset.app = "map-tool-picker";
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `520px`;
    term.style.maxWidth = `calc(100vw - 24px)`;
    term.style.minHeight = `260px`;

    const title = selection.map_action_id || selection.canonical_action || "akcja";
    const label = (selection.pending_action || {}).label || (selection.pending_action || {}).name || "";
    term.innerHTML = `
        <div class="title-bar">Wyb\u00f3r narz\u0119dzia <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="map-tool-picker-shell">
            <div class="map-tool-picker-head">
                <span class="map-tool-picker-kicker">Akcja mapy</span>
                <h3>${escapeHTML(title)}</h3>
                ${label ? `<p title="${escapeHTML(label)}">${escapeHTML(label)}</p>` : ''}
            </div>
            <div class="map-tool-picker-list">
                ${apps.map(renderMapToolPickerApp).join('')}
            </div>
            <div class="map-tool-picker-footer">
                <span>Pokazano tylko pasuj\u0105ce narz\u0119dzia. Pe\u0142ny katalog pozostaje w Plikach.</span>
                <button class="map-tool-picker-files" data-map-tool-open-files type="button">Poka\u017c w plikach</button>
            </div>
        </div>
    `;

    term.querySelector('.close-btn')?.addEventListener('click', () => closeMapToolPicker(true));
    term.querySelectorAll('[data-map-tool-use]').forEach(button => {
        button.addEventListener('click', () => window.selectMapActionTool(button.dataset.appId || ""));
    });
    term.querySelector('[data-map-tool-open-files]')?.addEventListener('click', async () => {
        closeMapToolPicker(false);
        await createFileManager({ toolSelection: window.activeToolSelection });
    });
    document.body.appendChild(term);
    makeDraggable(term);
    bringWindowToFront(term);
    return term;
}

window.openToolSelectionForMapAction = async function(payload) {
    window.activeToolSelection = normalizeToolSelectionPayload(payload || {});
    const flowId = getHackFlowId(window.activeToolSelection);
    window.__lastHackFlowId = flowId;
    appFlowTrace(flowId, "tool_picker_open", {
        action: window.activeToolSelection.map_action_id || window.activeToolSelection.canonical_action || "",
        matching_apps: (window.activeToolSelection.matching_apps || []).map(app => app && (app.id || app.name))
    });
    if (
        provisionalAppLaunchFlags.enabled
        && payload?.auto_select === true
        && window.activeToolSelection.matching_apps.length === 1
    ) {
        const onlyApp = window.activeToolSelection.matching_apps[0];
        appFlowTrace(flowId, "tool_picker_auto_select", {
            action: window.activeToolSelection.map_action_id || window.activeToolSelection.canonical_action || "",
            app_id: onlyApp.id || "",
            app_name: onlyApp.name || ""
        });
        await selectMapActionTool(onlyApp.id || onlyApp.name || "");
        return;
    }
    const title = window.activeToolSelection.map_action_id || window.activeToolSelection.canonical_action || "akcja";
    addSystemMessage("info", "\u{1F6E0}\uFE0F Wyb\u00f3r narz\u0119dzia", `Wybierz narz\u0119dzie dla: ${title}`);
    createMapToolPicker(window.activeToolSelection);
    appFlowTrace(flowId, "tool_picker_rendered", {
        action: title,
        cards: (window.activeToolSelection.matching_apps || []).length
    });
};

async function createFileManager(options = {}) {
    // Jeden FileManager na raz
    const existing = document.querySelector(`.terminal[data-app="files"]`);
    if (existing) {
        if (existing._fileManagerObserver && typeof existing._fileManagerObserver.disconnect === "function") {
            existing._fileManagerObserver.disconnect();
        }
        if (existing.dataset.fileManagerId) {
            fileManagerInstances.delete(existing.dataset.fileManagerId);
        }
        existing.remove();
        return createFileManager(options);
    }

    const term = document.createElement('div');
    term.className = 'terminal';
    term.dataset.app = "files";
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `600px`;
    term.style.height = `450px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';

    const terminalId = `files-${Date.now()}`;
    window.fileManagerTerminalId = terminalId;
    term.dataset.fileManagerId = terminalId;
    if (options.toolSelection) {
        window.activeToolSelection = normalizeToolSelectionPayload(options.toolSelection);
    }
    const systemDirs = [
        'tools',
        'gps',
        'device',
        'audio',
        'camera',
        'atm',
        'credentials',
        'financial',
        'personal',
        'network',
        'vehicle',
        'system',
        'market',
        'projects',
        'download',
        'pictures',
        'social-media',
        'about',
        'tips-tricks'
    ];
    const folderLabels = {
        tools: 'Tools',
        gps: 'Sledzenie',
        device: 'Urzadzenia',
        audio: 'Audio',
        camera: 'Kamery',
        atm: 'ATM',
        credentials: 'Dostepy',
        financial: 'Finanse',
        personal: 'Dane osobowe',
        network: 'Siec',
        vehicle: 'Pojazdy',
        system: 'System',
        market: 'Rynek',
        projects: 'Projekty',
        download: 'Download',
        pictures: 'Obrazy',
        'social-media': 'Social',
        about: 'About',
        'tips-tricks': 'Tips&Tricks'
    };
    const operationTypeLabels = {
        vehicle_tracking: 'sledzenie pojazdu',
        device_tracking: 'sledzenie urzadzenia',
        camera_stream: 'monitoring kamery',
        camera_shutdown: 'wylaczenie kamery',
        atm_log_extraction: 'odczyt logow ATM',
        persistent_sniffer: 'implant sieciowy',
        generic_trace: 'sledzenie celu',
        wifi_scanner: 'skanowanie hotspotow',
        audio_interference: 'audio hack',
        vehicle_ecu: 'hakowanie ECU'
    };
    const fileManagerUiIcons = {
        file: '\u{1F4C4}',
        folder: '\u{1F4C2}',
        tool: '\u{1F527}',
        project: '\u{1F6E0}\uFE0F',
        uninstall: '\u2715',
        back: '\u2190'
    };
    const folderIcons = {
        tools: fileManagerUiIcons.tool,
        gps: 'TRK',
        device: 'DEV',
        audio: 'AUD',
        personal: 'ID',
        camera: 'CAM',
        atm: 'ATM',
        financial: 'FIN',
        credentials: 'KEY',
        network: 'NET',
        vehicle: 'CAR',
        system: 'SYS',
        market: 'MKT',
        projects: 'PRJ',
        pictures: 'IMG',
        download: 'DL',
        'social-media': 'SOC',
        about: 'PTK',
        'tips-tricks': 'TIP'
    };
    const fileManagerStaticDocs = {
        about: [
            {
                name: 'chaos.ptk',
                title: 'ABOUT CHAOS',
                source: '/static/files/about/chaos.ptk',
                format: 'markdown'
            }
        ],
        'tips-tricks': [
            {
                name: 'blacknet.ptk',
                title: 'BLACKNET SIGNALS',
                source: '/static/files/tips-tricks/blacknet.ptk',
                format: 'markdown'
            }
        ]
    };
    const getFolderLabel = (folderName) => folderLabels[folderName] || folderName;
    const getFolderIcon = (folderName) => folderIcons[folderName] || fileManagerUiIcons.file;
    const getStaticDocFile = (folderName, filename) => {
        const docs = fileManagerStaticDocs[folderName] || [];
        return docs.find(item => String(item.name || '') === String(filename || '')) || null;
    };
    const renderMarkdownInline = (text) => {
        return escapeHTML(text)
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/`([^`]+)`/g, '<code>$1</code>');
    };
    const renderFileManagerMarkdown = (markdown) => {
        const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n');
        let html = '';
        let listOpen = false;
        let codeOpen = false;
        const closeList = () => {
            if (listOpen) {
                html += '</ul>';
                listOpen = false;
            }
        };
        const closeCode = () => {
            if (codeOpen) {
                html += '</code></pre>';
                codeOpen = false;
            }
        };

        lines.forEach(rawLine => {
            const line = rawLine || '';
            const trimmed = line.trim();
            if (trimmed.startsWith('```')) {
                closeList();
                if (codeOpen) closeCode();
                else {
                    html += '<pre><code>';
                    codeOpen = true;
                }
                return;
            }
            if (codeOpen) {
                html += `${escapeHTML(line)}\n`;
                return;
            }
            if (!trimmed) {
                closeList();
                return;
            }
            const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
            if (heading) {
                closeList();
                const level = Math.min(4, heading[1].length + 1);
                html += `<h${level}>${renderMarkdownInline(heading[2])}</h${level}>`;
                return;
            }
            const bullet = trimmed.match(/^[-*]\s+(.+)$/);
            if (bullet) {
                if (!listOpen) {
                    html += '<ul>';
                    listOpen = true;
                }
                html += `<li>${renderMarkdownInline(bullet[1])}</li>`;
                return;
            }
            closeList();
            html += `<p>${renderMarkdownInline(trimmed)}</p>`;
        });

        closeList();
        closeCode();
        return html;
    };
    const getFileOperationType = (fileEntry) => {
        if (!fileEntry || typeof fileEntry !== 'object') return '';
        const metadata = fileEntry.metadata || {};
        return fileEntry.source_operation_type || metadata.source_operation_type || fileEntry.operation_type || '';
    };
    const getFileOperationLabel = (fileEntry) => {
        const operationType = getFileOperationType(fileEntry);
        return operationTypeLabels[operationType] || operationType || '-';
    };
    const polishFileManagerText = (root) => {
        if (!root) return;
        const replacements = [
            [/Kompletno[^\s:]*/g, 'Kompletno\u015b\u0107'],
            [/Jako[^\s:]*/g, 'Jako\u015b\u0107'],
            [/warto[^\s:]*/g, 'warto\u015b\u0107'],
            [/Warto[^\s:]*/g, 'Warto\u015b\u0107'],
            [/Dok[^\s:]*/g, 'Dok\u0142adno\u015b\u0107'],
            [/Pewno[^\s:]*/g, 'Pewno\u015b\u0107'],
            [/Brak plik[^\s.]*/g, 'Brak plik\u00f3w'],
            [/Brak zasob[^\s.]*/g, 'Brak zasob\u00f3w'],
            [/Brak checkpoint[^\s.]*/g, 'Brak checkpoint\u00f3w'],
            [/U[^\s]*yj/g, 'U\u017cyj'],
            [/pod[^\s]*wietlone narz[^\s.]*dzie/g, 'pod\u015bwietlone narz\u0119dzie'],
            [/Wr[^\s]*/g, 'Wr\u00f3\u0107'],
            [/Mened[^\s]*er plik[^\s]*/g, 'Mened\u017cer plik\u00f3w']
        ];
        root.querySelectorAll('.file-manager-back-btn').forEach(button => {
            if (button.dataset.polishedBack !== '1') {
                button.innerHTML = '&larr; Wr&oacute;&cacute;';
                button.dataset.polishedBack = '1';
            }
        });
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(node => {
            let value = node.nodeValue || '';
            replacements.forEach(([pattern, replacement]) => {
                value = value.replace(pattern, replacement);
            });
            if (value !== node.nodeValue) node.nodeValue = value;
        });
    };

    term.innerHTML = `
        <div class="title-bar">
            Menedżer plików
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div style="padding: 10px; background: #111; color: #0f0; flex:1; overflow-y:auto; font-family: monospace;" id="${terminalId}-content">
            <div class="app-load-panel">
                <div class="app-load-panel__title">Ladowanie plikow...</div>
                <div class="app-load-panel__bar"><span></span></div>
                <div class="app-load-panel__text">Pobieranie profilu i modelu plikow...</div>
            </div>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    const fileManagerTitle = term.querySelector('.title-bar');
    if (fileManagerTitle && fileManagerTitle.firstChild) fileManagerTitle.firstChild.nodeValue = 'Menedżer plików ';
    const fileManagerClose = term.querySelector('.close-btn');
    if (fileManagerClose) fileManagerClose.textContent = 'x';
    const fileManagerContent = document.getElementById(`${terminalId}-content`);
    const fileManagerObserver = new MutationObserver(() => polishFileManagerText(fileManagerContent));
    term._fileManagerObserver = fileManagerObserver;
    if (fileManagerContent) {
        fileManagerObserver.observe(fileManagerContent, { childList: true, subtree: true, characterData: true });
        polishFileManagerText(fileManagerContent);
    }
    term.querySelector('.close-btn').addEventListener('click', () => {
        fileManagerObserver.disconnect();
        term.remove();
    });

    // Pobierz dane profilu
    const profileData = await getUserProfile();
    if (!profileData || !profileData.files) {
        addSystemMessage("danger", "\u{1F4C2} Pliki", "\u2716 B\u0142\u0105d \u0142adowania plik\u00f3w");
        return;
    }
    const files = profileData.files;
    if (!Array.isArray(files.projects)) files.projects = [];
    systemDirs.forEach(dir => {
        if (!Array.isArray(files[dir])) files[dir] = [];
    });
    const storageSummary = {
        capacity: Number(profileData.storage_capacity || 0),
        used: Number(profileData.storage_used || 0),
        unit: profileData.storage_unit || 'MB',
        overLimit: profileData.storage_over_limit === true,
        softLimit: profileData.storage_soft_limit !== false
    };
    const storageMeterHTML = () => {
        return `
            <div class="file-manager-storage" data-storage-meter data-storage-used="${storageSummary.used}" data-storage-capacity="${storageSummary.capacity}" data-storage-unit="${escapeHTML(storageSummary.unit)}" data-storage-over-limit="${storageSummary.overLimit ? '1' : '0'}">
                ${renderStorageMeterInner(storageSummary)}
            </div>
        `;
    };
    const installedToolAppsByFile = new Map();
    (Array.isArray(profileData.apps) ? profileData.apps : []).forEach(app => {
        if (!app || typeof app !== 'object') return;
        const appName = String(app.name || app.id || '').trim();
        const filename = String(app.file_name || app.project_file || (appName ? `${appName}.sh` : '')).trim();
        if (filename) installedToolAppsByFile.set(filename, app);
    });
    fileManagerInstances.set(terminalId, {
        files,
        apps: Array.isArray(profileData.apps) ? profileData.apps : [],
        installedToolAppsByFile,
        currentFolder: null
    });
    if (fileManagerContent) {
        fileManagerContent.innerHTML = `
            ${storageMeterHTML()}
            <h3>Katalogi:</h3>
            <div id="${terminalId}-folders"></div>
        `;
    }

    renderFolders();

    function renderFolders() {
        const foldersDiv = document.getElementById(`${terminalId}-folders`);
        foldersDiv.innerHTML = '';
        systemDirs.forEach(dir => {
            const folder = document.createElement('div');
            const folderLabel = getFolderLabel(dir);
            folder.innerHTML = `<span style="cursor:pointer;" onclick="window.openFolderInManager('${terminalId}', '${dir}')">📂 <b>${dir}</b></span>`;
            folder.innerHTML = `<span style="cursor:pointer;" onclick="window.openFolderInManager('${terminalId}', '${dir}')">📂 <b>${escapeHTML(folderLabel)}</b> <span style="color:#6fbf89;">/${escapeHTML(dir)}</span></span>`;
            folder.innerHTML = `<span style="cursor:pointer;" onclick="window.openFolderInManager('${terminalId}', '${dir}')">[DIR] <b>${escapeHTML(folderLabel)}</b> <span style="color:#6fbf89;">/${escapeHTML(dir)}</span></span>`;
            foldersDiv.appendChild(folder);
        });
    }

    window.openFolderInManager = (id, folderName) => {
        const container = document.getElementById(`${id}-content`);
        const state = fileManagerInstances.get(id);
        if (state) state.currentFolder = folderName;
        const fileList = files[folderName] || [];
        const renderedToolAppIds = new Set();

        let list = "";
        const staticDocs = fileManagerStaticDocs[folderName] || [];
        staticDocs.forEach(docFile => {
            list += `
                <div class="file-manager-row file-manager-row-dark">
                    <div class="file-manager-file" onclick="window.runFile('${folderName}','${escapeHTML(docFile.name)}')">
                        <span class="file-manager-icon">PTK</span>
                        <span class="file-manager-name">${escapeHTML(docFile.name)}</span>
                        <span class="file-manager-name" style="display:block;color:#6fbf89;font-size:10px;">${escapeHTML(docFile.title || 'Dokument')} | ${escapeHTML(docFile.format || 'text')} | ${escapeHTML(docFile.source || '')}</span>
                    </div>
                </div>
            `;
        });
        fileList.forEach(fileEntry => {
            const filename = typeof fileEntry === "string" ? fileEntry : String(fileEntry.name || fileEntry.filename || "plik");
            const matchingTool = folderName === "tools" ? getToolSelectionAppForFile(filename) : null;
            const installedTool = folderName === "tools" ? installedToolAppsByFile.get(filename) : null;
            const toolMeta = matchingTool || installedTool;
            const isMatchingTool = Boolean(matchingTool);
            if (isMatchingTool) renderedToolAppIds.add(String(matchingTool.id || ""));
            // Ikonka per folder
            let icon = "📄";
            if (folderName === "tools") icon = "🔧";
            if (folderName === "gps") icon = "GPS";
            if (folderName === "device") icon = "DEV";
            if (folderName === "audio") icon = "AUD";
            if (folderName === "personal") icon = "ID";
            if (folderName === "camera") icon = "CAM";
            if (folderName === "atm") icon = "ATM";
            if (folderName === "financial") icon = "FIN";
            if (folderName === "credentials") icon = "KEY";
            if (folderName === "network") icon = "NET";
            if (folderName === "vehicle") icon = "CAR";
            if (folderName === "system") icon = "SYS";
            if (folderName === "market") icon = "MKT";
            if (folderName === "pictures") icon = "🖼️";
            if (folderName === "download") icon = "⬇️";
            if (folderName === "social-media") icon = "💬";

            icon = getFolderIcon(folderName);

            // Klasa pliku
            let fileClass = "file-manager-file";
            if (folderName === "tools") fileClass += " file-manager-tool";
            if (isMatchingTool) fileClass += " file-manager-tool-match";

            // W tools – dodaj Uninstall
            if (folderName === "tools") {
                const toolDiskUsage = Number((toolMeta || {}).disk_usage || (toolMeta || {}).install_size || (toolMeta || {}).file_size || 0);
                const toolAppId = String((toolMeta || {}).id || "");
                const toolSizeLine = toolDiskUsage
                    ? `<span class="file-manager-tool-meta">Dysk: ${escapeHTML(formatStorageSize(toolDiskUsage))}</span>`
                    : '';
                const toolContractLine = toolMeta ? `
                    <span class="file-manager-tool-meta">
                        ${escapeHTML(toolMeta.tool_family || toolMeta.type || 'tool')} / ${escapeHTML(toolMeta.tool_mode || toolMeta.scanner_mode || 'desktop')}
                        | Q ${escapeHTML(String(toolMeta.quality_score || 0))}/100
                        | P ${escapeHTML(String(toolMeta.power_score || 0))}/100
                    </span>
                ` : '';
                list += `
                    <div class="file-manager-row file-manager-row-dark ${isMatchingTool ? 'file-manager-row-match' : ''}">
                        <span class="file-manager-file" onclick="window.runFile('${folderName}','${filename}')">
                            <span class="file-manager-icon">${fileManagerUiIcons.tool}</span>
                            <span class="file-manager-name">${filename}</span>
                            ${toolSizeLine}
                            ${toolContractLine}
                            ${isMatchingTool ? `
                                <button class="file-manager-tool-select" data-app-id="${escapeHTML(matchingTool.id || '')}" onclick="event.stopPropagation();window.selectMapActionTool('${escapeHTML(matchingTool.id || '')}')">
                                    U\u017cyj
                                </button>
                            ` : ''}
                            <button class="file-manager-uninstall-btn" onclick="event.stopPropagation();window.uninstallApp('${escapeHTML(filename)}', '${escapeHTML(toolAppId)}')">
                                ${fileManagerUiIcons.uninstall} <span class="file-manager-uninstall-label">Odinstaluj</span>
                            </button>
                        </span>
                    </div>
                `;
            } else if (folderName === "projects") {
                list += `
                    <div class="file-manager-row file-manager-row-dark">
                        <span class="file-manager-file" onclick="window.runFile('${folderName}','${filename}')">
                            <span class="file-manager-icon">${fileManagerUiIcons.project}</span>
                            <span class="file-manager-name">${filename}</span>
                            <button class="file-manager-uninstall-btn" onclick="event.stopPropagation();window.removeProjectFromGoogleplex('${filename}')">
                                Wycofaj
                            </button>
                        </span>
                    </div>
                `;
            } else {
                let meta = "";
                if (typeof fileEntry === "object" && fileEntry) {
                    const category = fileEntry.file_category || folderName;
                    const previewMode = fileEntry.preview_mode || 'file';
                    const resources = Array.isArray(fileEntry.resource_types) && fileEntry.resource_types.length
                        ? fileEntry.resource_types.join(', ')
                        : '-';
                    const sourceOperation = fileEntry.source_operation_id || fileEntry.operation_id || (fileEntry.metadata || {}).operation_id || '-';
                    const marketStatus = fileEntry.market_status || 'not_listed';
                    const operationLabel = getFileOperationLabel(fileEntry);
                    const sellableLabel = fileEntry.sellable ? 'tak' : 'nie';
                    const completeness = fileEntry.completeness_percent ?? (fileEntry.metadata || {}).completeness_percent ?? 0;
                    const qualityScore = fileEntry.quality_score ?? (fileEntry.metadata || {}).quality_score ?? 0;
                    const fileSize = fileEntry.file_size ?? (fileEntry.metadata || {}).file_size ?? 0;
                    const missingFields = Array.isArray(fileEntry.missing_fields)
                        ? fileEntry.missing_fields
                        : (Array.isArray((fileEntry.metadata || {}).missing_fields) ? (fileEntry.metadata || {}).missing_fields : []);
                    meta = `
                        <span class="file-manager-name" style="display:block;color:#8fd6a4;font-size:11px;">${escapeHTML(fileEntry.directory || folderName)} | ${escapeHTML(category)} | ${escapeHTML(previewMode)}</span>
                        <span class="file-manager-name" style="display:block;color:#6fbf89;font-size:10px;">Zasoby: ${escapeHTML(resources)} | Typ: ${escapeHTML(operationLabel)} | Operacja: ${escapeHTML(sourceOperation)}</span>
                        <span class="file-manager-name" style="display:block;color:#6fbf89;font-size:10px;">Rynek: ${escapeHTML(marketStatus)} | Sprzedawalny: ${escapeHTML(sellableLabel)}</span>
                        <span class="file-manager-name" style="display:block;color:#6fbf89;font-size:10px;">Rozmiar: ${escapeHTML(formatStorageSize(fileSize))}</span>
                        <span class="file-manager-name" style="display:block;color:#6fbf89;font-size:10px;">Kompletno\u015b\u0107: ${escapeHTML(String(completeness))}% | Jako\u015b\u0107: ${escapeHTML(String(qualityScore))}/100 | Braki: ${escapeHTML(missingFields.length ? missingFields.slice(0, 3).join(', ') : 'brak')}</span>
                    `;
                }
                list += `
                    <div class="file-manager-row">
                        <div class="${fileClass}" onclick="window.runFile('${folderName}','${filename}')">
                            <span class="file-manager-icon">${icon}</span>
                            <span class="file-manager-name">${filename}</span>
                            ${meta}
                        </div>
                    </div>
                `;
            }
        });

        if (folderName === "tools" && window.activeToolSelection) {
            window.activeToolSelection.matching_apps.forEach(app => {
                const appId = String(app.id || "");
                if (!appId || renderedToolAppIds.has(appId)) return;
                const name = String(app.name || app.id || "tool");
                const filename = String(app.tool_file || `${name}.sh`);
                const appDiskUsage = Number(app.disk_usage || app.install_size || app.file_size || 0);
                const appSizeLine = appDiskUsage
                    ? `<span class="file-manager-tool-meta">Dysk: ${escapeHTML(formatStorageSize(appDiskUsage))}</span>`
                    : '';
                list += `
                    <div class="file-manager-row file-manager-row-dark file-manager-row-match">
                        <span class="file-manager-file file-manager-tool file-manager-tool-match" onclick="window.runFile('tools','${filename}')">
                            <span class="file-manager-icon">${escapeHTML(app.icon || fileManagerUiIcons.tool)}</span>
                            <span class="file-manager-name">${escapeHTML(filename)}</span>
                            ${appSizeLine}
                            <button class="file-manager-tool-select" data-app-id="${escapeHTML(appId)}" onclick="event.stopPropagation();window.selectMapActionTool('${escapeHTML(appId)}')">
                                    U\u017cyj
                            </button>
                        </span>
                    </div>
                `;
            });
        }

        if (!list) list = `<div class="file-manager-empty">Brak plik\u00f3w</div>`;
        const selectionHeader = folderName === "tools" && window.activeToolSelection ? `
            <div class="file-manager-selection-hint">
                Akcja mapy: <b>${escapeHTML(window.activeToolSelection.map_action_id || window.activeToolSelection.canonical_action || '-')}</b>.
                Wybierz pod\u015bwietlone narz\u0119dzie.
            </div>
        ` : "";

        container.innerHTML = `
            <div class="file-manager-header">
                <button class="file-manager-back-btn" onclick="window.renderFoldersRoot('${id}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                <span class="file-manager-folder-title">${fileManagerUiIcons.folder} ${escapeHTML(getFolderLabel(folderName))} <small style="color:#6fbf89;">/${escapeHTML(folderName)}</small></span>
            </div>
            ${storageMeterHTML()}
            ${selectionHeader}
            <div class="file-manager-list">${list}</div>
        `;
    };

    window.renderFoldersRoot = (id) => {
        const container = document.getElementById(`${id}-content`);
        const state = fileManagerInstances.get(id);
        if (state) state.currentFolder = null;
        container.innerHTML = `
            ${storageMeterHTML()}
            <h3>Katalogi:</h3>
            <div id="${id}-folders"></div>
        `;
        renderFolders();
    };

    // Klik w dowolny plik — symulacja otwarcia/uruchomienia
    window.runFile = async (folderName, filename) => {
        const staticDoc = getStaticDocFile(folderName, filename);
        if (staticDoc) {
            const container = document.getElementById(`${terminalId}-content`);
            container.innerHTML = `
                <div class="file-manager-header">
                    <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                    <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(staticDoc.name)}</span>
                </div>
                <div class="file-manager-row file-manager-row-dark" style="display:block;">
                    <div class="app-load-panel">
                        <div class="app-load-panel__title">Ladowanie dokumentu...</div>
                        <div class="app-load-panel__bar"><span></span></div>
                        <div class="app-load-panel__text">${escapeHTML(staticDoc.source)}</div>
                    </div>
                </div>
            `;
            try {
                const response = await fetch(staticDoc.source, { cache: 'no-cache' });
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const markdown = await response.text();
                container.innerHTML = `
                    <div class="file-manager-header">
                        <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                        <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(staticDoc.name)}</span>
                    </div>
                    <div class="file-manager-row file-manager-row-dark file-manager-document-shell">
                        <div class="file-manager-document-meta">
                            Source: <span>${escapeHTML(staticDoc.source)}</span>
                        </div>
                        <article class="file-manager-markdown">
                            ${renderFileManagerMarkdown(markdown)}
                        </article>
                    </div>
                `;
            } catch (err) {
                container.innerHTML = `
                    <div class="file-manager-header">
                        <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                        <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(staticDoc.name)}</span>
                    </div>
                    <div class="file-manager-row file-manager-row-dark" style="display:block;">
                        <h3>Nie udalo sie wczytac dokumentu</h3>
                        <p>${escapeHTML(err.message || 'Nieznany blad')}</p>
                        <p>Source: <b>${escapeHTML(staticDoc.source)}</b></p>
                    </div>
                `;
            }
            return;
        }
        const fileList = files[folderName] || [];
        const fileEntry = fileList.find(item => {
            const itemName = typeof item === "string" ? item : String(item.name || item.filename || "");
            return itemName === filename;
        });
        if (fileEntry && typeof fileEntry === "object") {
            const container = document.getElementById(`${terminalId}-content`);
            const checkpoints = Array.isArray(fileEntry.checkpoints) ? fileEntry.checkpoints : [];
            const metadata = fileEntry.metadata || {};
            const completeness = metadata.completeness || {};
            const summary = fileEntry.summary || {};
            const resources = Array.isArray(fileEntry.resource_types) ? fileEntry.resource_types : [];
            const records = Array.isArray(fileEntry.records) ? fileEntry.records : [];
            const operationLabel = getFileOperationLabel(fileEntry);
            const completenessPercent = fileEntry.completeness_percent ?? metadata.completeness_percent ?? summary.completeness_percent ?? completeness.percent ?? 0;
            const completenessTier = fileEntry.completeness_tier || metadata.completeness_tier || summary.tier || completeness.tier || 'basic';
            const qualityScore = fileEntry.quality_score ?? metadata.quality_score ?? summary.quality_score ?? completeness.quality_score ?? 0;
            const missingFields = Array.isArray(fileEntry.missing_fields)
                ? fileEntry.missing_fields
                : (Array.isArray(metadata.missing_fields)
                    ? metadata.missing_fields
                    : (Array.isArray(completeness.missing) ? completeness.missing : []));
            const fileValuePreview = metadata.price_preview ? `${metadata.price_preview} HC` : '-';
            if (fileEntry.preview_mode === "card") {
                container.innerHTML = `
                    <div class="file-manager-header">
                        <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                        <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(filename)}</span>
                    </div>
                    <div class="file-manager-row file-manager-row-dark" style="display:block;">
                        <h3>${escapeHTML(summary.label || 'Device Intelligence')}</h3>
                        <p>Plik: <b>${escapeHTML(filename)}</b></p>
                        <p>Katalog: <b>${escapeHTML(fileEntry.directory || folderName)}</b></p>
                        <p>Operacja: <b>${escapeHTML(fileEntry.operation_id || metadata.operation_id || '-')}</b></p>
                        <p>Typ operacji: <b>${escapeHTML(operationLabel)}</b></p>
                        <p>Jakość: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                        <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                        <p>Przewidywana wartość: <b>${escapeHTML(fileValuePreview)}</b></p>
                        <p>Kompletność: <b>${escapeHTML(String(summary.completeness_percent ?? completeness.percent ?? 0))}%</b></p>
                        <p>Tier: <b>${escapeHTML(summary.tier || completeness.tier || 'basic')}</b></p>
                        <div style="height:10px;border:1px solid #0f0;background:#031403;margin:8px 0 12px;">
                            <div style="height:100%;width:${Math.max(0, Math.min(100, Number(summary.completeness_percent ?? completeness.percent ?? 0)))}%;background:#38ff80;"></div>
                        </div>
                        <h4>Zasoby w paczce</h4>
                        <ul>
                            ${resources.map(item => `<li>${escapeHTML(item)}</li>`).join('') || '<li>Brak zasobów.</li>'}
                        </ul>
                        <p>Jakość: <b>${escapeHTML(metadata.quality || '-')}</b></p>
                    </div>
                `;
                return;
            }
            if (fileEntry.preview_mode === "table" && records.length) {
                const recordRows = records.slice(0, 80).map(record => `
                    <tr>
                        <td>${escapeHTML(String(record.index || ''))}</td>
                        <td>${escapeHTML(record.timestamp || record.created_at || '')}</td>
                        <td>${escapeHTML(record.account || '-')}</td>
                        <td>${escapeHTML(record.event || '-')}</td>
                        <td>${escapeHTML(record.amount_hint || '-')}</td>
                        <td>${escapeHTML(record.confidence || '-')}</td>
                    </tr>
                `).join('');
                container.innerHTML = `
                    <div class="file-manager-header">
                        <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                        <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(filename)}</span>
                    </div>
                    <div class="file-manager-row file-manager-row-dark" style="display:block;">
                        <h3>${escapeHTML(filename)}</h3>
                        <p>Kategoria: <b>${escapeHTML(fileEntry.file_category || folderName)}</b></p>
                        <p>Katalog: <b>${escapeHTML(fileEntry.directory || folderName)}</b></p>
                        <p>Operacja: <b>${escapeHTML(fileEntry.operation_id || metadata.operation_id || '-')}</b></p>
                        <p>Kompletność: <b>${escapeHTML(String(completenessPercent))}% / ${escapeHTML(completenessTier)}</b></p>
                        <p>Jakość: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                        <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                        <p>Przewidywana wartość: <b>${escapeHTML(fileValuePreview)}</b></p>
                        <p>Rekordy: <b>${escapeHTML(String(metadata.record_count ?? records.length))}</b></p>
                        <p>Ryzyko: <b>${escapeHTML(metadata.risk_hint || 'high-value/high-risk')}</b></p>
                        <h4>Zasoby</h4>
                        <ul>
                            ${resources.map(item => `<li>${escapeHTML(item)}</li>`).join('') || '<li>Brak zasobow.</li>'}
                        </ul>
                        <table style="width:100%;border-collapse:collapse;margin-top:10px;">
                            <thead>
                                <tr>
                                    <th style="text-align:left;border-bottom:1px solid #0f0;">#</th>
                                    <th style="text-align:left;border-bottom:1px solid #0f0;">Czas</th>
                                    <th style="text-align:left;border-bottom:1px solid #0f0;">Konto</th>
                                    <th style="text-align:left;border-bottom:1px solid #0f0;">Event</th>
                                    <th style="text-align:left;border-bottom:1px solid #0f0;">Kwota</th>
                                    <th style="text-align:left;border-bottom:1px solid #0f0;">Pewnosc</th>
                                </tr>
                            </thead>
                            <tbody>${recordRows || '<tr><td colspan="6">Brak rekordow.</td></tr>'}</tbody>
                        </table>
                    </div>
                `;
                return;
            }
            if (fileEntry.preview_mode === "encrypted_blob") {
                container.innerHTML = `
                    <div class="file-manager-header">
                        <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                        <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(filename)}</span>
                    </div>
                    <div class="file-manager-row file-manager-row-dark" style="display:block;">
                        <h3>${escapeHTML(summary.label || 'Encrypted Data Blob')}</h3>
                        <div style="border:1px solid #0f0;background:#020802;margin:10px 0;padding:14px;color:#8fd6a4;">
                            <div style="font-size:12px;letter-spacing:2px;">ENCRYPTED BLOB</div>
                            <div style="font-size:20px;margin-top:8px;">•••• •••• •••• ••••</div>
                        </div>
                        <p>Plik: <b>${escapeHTML(filename)}</b></p>
                        <p>Katalog: <b>${escapeHTML(fileEntry.directory || folderName)}</b></p>
                        <p>Operacja: <b>${escapeHTML(fileEntry.operation_id || metadata.operation_id || '-')}</b></p>
                        <p>Kompletność: <b>${escapeHTML(String(completenessPercent))}% / ${escapeHTML(completenessTier)}</b></p>
                        <p>Jakość: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                        <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                        <p>Przewidywana wartość: <b>${escapeHTML(fileValuePreview)}</b></p>
                        <p>Zebrane wpisy: <b>${escapeHTML(String(summary.credential_count || metadata.collected_count || 0))}</b></p>
                        <p>Instalacja: <b>${escapeHTML(metadata.installed_at || '-')}</b></p>
                        <p>Koniec: <b>${escapeHTML(metadata.ended_at || '-')}</b></p>
                        <p>Ryzyko: <b>${escapeHTML(metadata.risk_hint || 'long_operation/sniffer_detected/high_value')}</b></p>
                        <p>Dane jawne: <b>NIE</b></p>
                        <h4>Zasoby</h4>
                        <ul>
                            ${resources.map(item => `<li>${escapeHTML(item)}</li>`).join('') || '<li>Brak zasobow.</li>'}
                        </ul>
                    </div>
                `;
                return;
            }
            if (fileEntry.preview_mode === "operation_state") {
                container.innerHTML = `
                    <div class="file-manager-header">
                        <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                        <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(filename)}</span>
                    </div>
                    <div class="file-manager-row file-manager-row-dark" style="display:block;">
                        <h3>${escapeHTML(filename)}</h3>
                        <p>Kategoria: <b>${escapeHTML(fileEntry.file_category || folderName)}</b></p>
                        <p>Katalog: <b>${escapeHTML(fileEntry.directory || folderName)}</b></p>
                        <p>Operacja: <b>${escapeHTML(fileEntry.operation_id || metadata.operation_id || '-')}</b></p>
                        <p>Stan: <b>${escapeHTML(metadata.state || fileEntry.status || '-')}</b></p>
                        <p>Instalacja: <b>${escapeHTML(metadata.installed_at || '-')}</b></p>
                        <p>Koniec: <b>${escapeHTML(metadata.ended_at || '-')}</b></p>
                        <p>Ryzyko: <b>${escapeHTML(metadata.risk_hint || '-')}</b></p>
                        <h4>Zasoby</h4>
                        <ul>
                            ${resources.map(item => `<li>${escapeHTML(item)}</li>`).join('') || '<li>Brak zasobow.</li>'}
                        </ul>
                    </div>
                `;
                return;
            }
            if (fileEntry.preview_mode === "media_placeholder") {
                const durationSeconds = Number(metadata.duration_seconds || summary.duration_seconds || 0);
                const durationLabel = `${Math.floor(durationSeconds / 60)}m ${durationSeconds % 60}s`;
                container.innerHTML = `
                    <div class="file-manager-header">
                        <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                        <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(filename)}</span>
                    </div>
                    <div class="file-manager-row file-manager-row-dark" style="display:block;">
                        <h3>${escapeHTML(summary.label || 'Camera Stream Fragment')}</h3>
                        <div style="height:130px;border:1px solid #0f0;background:linear-gradient(135deg,#020802,#071a10);display:flex;align-items:center;justify-content:center;margin:10px 0;color:#8fd6a4;letter-spacing:2px;">
                            MEDIA PLACEHOLDER
                        </div>
                        <p>Plik: <b>${escapeHTML(filename)}</b></p>
                        <p>Katalog: <b>${escapeHTML(fileEntry.directory || folderName)}</b></p>
                        <p>Operacja: <b>${escapeHTML(fileEntry.operation_id || metadata.operation_id || '-')}</b></p>
                        <p>Kompletność: <b>${escapeHTML(String(completenessPercent))}% / ${escapeHTML(completenessTier)}</b></p>
                        <p>Jakość: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                        <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                        <p>Przewidywana wartość: <b>${escapeHTML(fileValuePreview)}</b></p>
                        <p>Fragment: <b>${escapeHTML(String(fileEntry.fragment_index || metadata.fragment_index || '-'))}</b></p>
                        <p>Czas fragmentu: <b>${escapeHTML(durationLabel)}</b></p>
                        <p>Start: <b>${escapeHTML(metadata.started_at || '-')}</b></p>
                        <p>Koniec: <b>${escapeHTML(metadata.ended_at || '-')}</b></p>
                        <p>Jakosc: <b>${escapeHTML(metadata.frame_quality || metadata.quality || '-')}</b></p>
                        <h4>Zasoby</h4>
                        <ul>
                            ${resources.map(item => `<li>${escapeHTML(item)}</li>`).join('') || '<li>Brak zasobow.</li>'}
                        </ul>
                    </div>
                `;
                return;
            }
            const checkpointRows = checkpoints.slice(0, 80).map(point => `
                <tr>
                    <td>${escapeHTML(String(point.index || ''))}</td>
                    <td>${escapeHTML(point.created_at || '')}</td>
                    <td>${escapeHTML(String(point.lat || ''))}</td>
                    <td>${escapeHTML(String(point.lng || ''))}</td>
                </tr>
            `).join('');
            container.innerHTML = `
                <div class="file-manager-header">
                    <button class="file-manager-back-btn" onclick="window.openFolderInManager('${terminalId}', '${folderName}')">${fileManagerUiIcons.back} Wr\u00f3\u0107</button>
                    <span class="file-manager-folder-title">${fileManagerUiIcons.file} ${escapeHTML(filename)}</span>
                </div>
                <div class="file-manager-row file-manager-row-dark" style="display:block;">
                    <h3>${escapeHTML(filename)}</h3>
                    <p>Kategoria: <b>${escapeHTML(fileEntry.file_category || folderName)}</b></p>
                    <p>Katalog: <b>${escapeHTML(fileEntry.directory || folderName)}</b></p>
                    <p>Operacja: <b>${escapeHTML(fileEntry.operation_id || metadata.operation_id || '-')}</b></p>
                    <p>Typ operacji: <b>${escapeHTML(operationLabel)}</b></p>
                    <p>Kompletność: <b>${escapeHTML(String(completenessPercent))}% / ${escapeHTML(completenessTier)}</b></p>
                    <p>Jakość: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                    <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                    <p>Przewidywana wartość: <b>${escapeHTML(fileValuePreview)}</b></p>
                    <p>Checkpointy: <b>${escapeHTML(String(metadata.checkpoint_count ?? checkpoints.length))}</b></p>
                    <p>Jakość: <b>${escapeHTML(metadata.quality || '-')}</b> | Dokładność: <b>${escapeHTML(metadata.accuracy || '-')}</b></p>
                    <table style="width:100%;border-collapse:collapse;margin-top:10px;">
                        <thead>
                            <tr>
                                <th style="text-align:left;border-bottom:1px solid #0f0;">#</th>
                                <th style="text-align:left;border-bottom:1px solid #0f0;">Czas</th>
                                <th style="text-align:left;border-bottom:1px solid #0f0;">Lat</th>
                                <th style="text-align:left;border-bottom:1px solid #0f0;">Lng</th>
                            </tr>
                        </thead>
                        <tbody>${checkpointRows || '<tr><td colspan="4">Brak checkpointów.</td></tr>'}</tbody>
                    </table>
                </div>
            `;
            return;
        }
        addSystemMessage("info", "\u{1F4C1} Otwieranie pliku", `(Symulacja) Otwierasz plik: ${filename}`);
    };
    window.selectMapActionTool = selectMapActionTool;
    window.uninstallApp = async (appName, appId = "") => {
        try {
            const response = await fetch('/api/apps/uninstall', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    app_id: appId || undefined,
                    tool_file: appName
                })
            });
            const data = await response.json();
            if (!response.ok || data.success === false || data.status === "error") {
                addSystemMessage("danger", "Deinstalacja", data.message || "Nie uda\u0142o si\u0119 odinstalowa\u0107 aplikacji.");
                return;
            }
            if (data.files && Array.isArray(data.files.tools)) {
                files.tools = data.files.tools;
            } else {
                files.tools = (files.tools || []).filter(item => String(item?.name || item) !== String(appName));
            }
            if (appId) {
                for (const [filename, app] of Array.from(installedToolAppsByFile.entries())) {
                    if (String(app?.id || "") === String(appId)) installedToolAppsByFile.delete(filename);
                }
            } else {
                installedToolAppsByFile.delete(appName);
            }
            if (data.storage) {
                storageSummary.capacity = Number(data.storage.capacity || storageSummary.capacity || 0);
                storageSummary.used = Number(data.storage.used || 0);
                storageSummary.unit = data.storage.unit || storageSummary.unit || 'MB';
                storageSummary.overLimit = data.storage.over_limit === true;
                storageSummary.softLimit = data.storage.soft_limit !== false;
            }
            if (fileManagerContent) {
                fileManagerContent.querySelector('.file-manager-storage')?.remove();
                fileManagerContent.insertAdjacentHTML('afterbegin', storageMeterHTML());
            }
            window.openFolderInManager(terminalId, "tools");
            if (Array.isArray(data.apps) || data.files) {
                await updateAppsView({
                    apps: data.apps || [],
                    files: data.files || {},
                    reason: "uninstall_response"
                });
            }
            addSystemMessage("warning", "Deinstalacja", data.message || `Odinstalowano ${appName}`);
        } catch (err) {
            addSystemMessage("danger", "Deinstalacja", err.message || "Nie uda\u0142o si\u0119 odinstalowa\u0107 aplikacji.");
        }
    };
    window.removeProjectFromGoogleplex = async (filename) => {
        const response = await fetch(`/api/apps/generated/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        const data = await response.json();
        addSystemMessage(
            data.success ? "warning" : "danger",
            "Googleplex",
            data.message || "Operacja zakonczona."
        );
        if (data.success) {
            const index = files.projects.indexOf(filename);
            if (index >= 0) files.projects.splice(index, 1);
            window.openFolderInManager(terminalId, "projects");
        }
    };

    if (window.activeToolSelection?.open_tools) {
        window.openFolderInManager(terminalId, "tools");
    }
}


function createEmailClientLegacy() {
    
    if (document.querySelector(`.terminal[data-app="email"]`)) return;

    const term = document.createElement('div');
    term.className = 'terminal';
    term.dataset.app = "email"; // 🔧 TO DODAJ
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `800px`;
    term.style.height = `500px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';

    const terminalId = `email-${Date.now()}`;

    term.innerHTML = `
        <div class="title-bar">
            Cyberner
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div style="display: flex; flex: 1; background: #111; color: #0f0; font-family: monospace;">
            <!-- Wiadomości -->
            <div style="width: 60%; border-right: 1px solid #0f0; padding: 10px; overflow-y:auto;">
                <h3>📥 Odebrane</h3>
                <div id="${terminalId}-message-list"></div>
                <hr>
                <div id="${terminalId}-message-content" style="margin-top:10px; color: #fff;"></div>
            </div>
            <!-- Znajomi -->
            <div style="width: 40%; padding: 10px;">
                <h3>👥 Znajomi</h3>
                <div id="${terminalId}-friends"></div>
            </div>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    // Po osadzeniu HTML – teraz selektory zadziałają
    const msgList = term.querySelector(`#${terminalId}-message-list`);
    const msgContent = term.querySelector(`#${terminalId}-message-content`);
    const friendsList = term.querySelector(`#${terminalId}-friends`);

    // Ładowanie wiadomości
    fetch('/messages.json')
        .then(res => res.json())
        .then(messages => {
            messages.forEach((msg) => {
                const div = document.createElement('div');
                div.innerHTML = `📨 <b>${msg.from}</b>: ${msg.subject}`;
                div.style.cursor = "pointer";
                div.style.marginBottom = "5px";
                div.onclick = () => {
                    msgContent.innerHTML = `
                        <h4>${msg.subject}</h4>
                        <p><i>Od: ${msg.from}</i></p>
                        <p>${msg.content}</p>
                    `;
                };
                msgList.appendChild(div);
            });
        });

    // Ładowanie znajomych
    fetch('/friends.json')
        .then(res => res.json())
        .then(friends => {
            friends.forEach(friend => {
                const div = document.createElement('div');
                const color = friend.status === "online" ? "#0f0" : "#666";
                div.innerHTML = `👤 <span style="color:${color};">${friend.name}</span> (${friend.status})`;
                div.style.marginBottom = "5px";
                friendsList.appendChild(div);
            });
        });
}

function createEmailClient() {
    if (document.querySelector(`.terminal[data-app="email"]`)) return;

    const term = document.createElement('div');
    term.className = 'terminal';
    term.dataset.app = "email";
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `920px`;
    term.style.height = `560px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';

    const terminalId = `email-${Date.now()}`;

    term.innerHTML = `
        <div class="title-bar">
            Cyberner
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <div class="mail-app" data-mobile-view="list">
            <div class="mail-sidebar">
                <div class="mail-sidebar-title">Cyberner</div>
                <form id="${terminalId}-contact-form" class="mail-contact-form mail-add-contact mail-contact-search">
                    <input id="${terminalId}-contact-input" type="text" placeholder="Nick znajomego" autocomplete="off">
                    <button type="submit">Dodaj</button>
                </form>
                <div class="mail-sidebar-scroll">
                    <section class="mail-sidebar-section">
                        <div class="mail-section-title">Kanały</div>
                        <div id="${terminalId}-channels" class="mail-channel-list mail-conversation-list"></div>
                    </section>
                    <section class="mail-sidebar-section">
                        <div class="mail-section-title">Znajomi</div>
                        <div id="${terminalId}-contacts" class="mail-contact-list mail-conversation-list"></div>
                    </section>
                    <section id="${terminalId}-pending-wrap" class="mail-pending-wrap mail-sidebar-section" style="display:none;">
                        <div class="mail-section-title">Nowe</div>
                        <div id="${terminalId}-pending" class="mail-contact-list mail-conversation-list"></div>
                    </section>
                </div>
            </div>
            <div class="mail-main mail-chat">
                <div class="mail-header mail-chat-header">
                    <button id="${terminalId}-back" type="button" class="mail-back-button" aria-label="Wroc do listy">&larr;</button>
                    <div>
                        <div id="${terminalId}-chat-title" class="mail-chat-title">WORLD</div>
                        <div id="${terminalId}-chat-subtitle" class="mail-chat-subtitle">Publiczny kanal swiata gry</div>
                    </div>
                    <div class="mail-header-actions">
                        <button id="${terminalId}-accept-contact" type="button" style="display:none;">Dodaj kontakt</button>
                        <button id="${terminalId}-remove-contact" type="button" class="mail-danger" style="display:none;">Usun kontakt</button>
                    </div>
                </div>
                <div id="${terminalId}-messages" class="mail-messages"></div>
                <form id="${terminalId}-message-form" class="mail-message-form mail-composer">
                    <input id="${terminalId}-message-input" type="text" placeholder="Napisz wiadomosc..." autocomplete="off">
                    <button type="submit" disabled>Wyslij</button>
                </form>
            </div>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    const channelsBox = term.querySelector(`#${terminalId}-channels`);
    const contactsBox = term.querySelector(`#${terminalId}-contacts`);
    const mailApp = term.querySelector('.mail-app');
    const pendingWrap = term.querySelector(`#${terminalId}-pending-wrap`);
    const pendingBox = term.querySelector(`#${terminalId}-pending`);
    const messagesBox = term.querySelector(`#${terminalId}-messages`);
    const chatTitle = term.querySelector(`#${terminalId}-chat-title`);
    const chatSubtitle = term.querySelector(`#${terminalId}-chat-subtitle`);
    const acceptBtn = term.querySelector(`#${terminalId}-accept-contact`);
    const removeBtn = term.querySelector(`#${terminalId}-remove-contact`);
    const backBtn = term.querySelector(`#${terminalId}-back`);
    const contactForm = term.querySelector(`#${terminalId}-contact-form`);
    const contactInput = term.querySelector(`#${terminalId}-contact-input`);
    const messageForm = term.querySelector(`#${terminalId}-message-form`);
    const messageInput = term.querySelector(`#${terminalId}-message-input`);
    const messageButton = messageForm.querySelector('button[type="submit"]');

    let currentUser = "";
    let channels = [];
    let contacts = [];
    let pendingThreads = [];
    let unreadCounts = { group: 0, direct: {}, channel: {} };
    let groupActiveCount = 0;
    let groupMessages = [];
    const threadSummaries = new Map();
    let currentChat = { scope: "group", peer: "global", source: "world", channel: "world", title: "WORLD" };
    let mailMobileView = "list";
    let mailSending = false;
    let mailClosed = false;
    let currentMessages = [];
    let pendingSend = null;
    let mailRefreshTimer = null;
    let latestMailDeltaVersion = 0;
    const messageIds = new Set();
    const requestState = {
        bootstrap: { inFlight: null, controller: null, version: 0 },
        messages: { inFlight: null, controller: null, version: 0, key: "" }
    };
    const teardownMailSessionState = () => {
        mailClosed = true;
        clearTimeout(mailRefreshTimer);
        mailRefreshTimer = null;
        Object.values(requestState).forEach(state => {
            if (state.controller) state.controller.abort();
            state.inFlight = null;
            state.controller = null;
        });
        currentMessages = [];
        pendingSend = null;
        messageIds.clear();
        window.activeCybernerThread = null;
    };
    window.addEventListener(
        "chaos:session-invalidated",
        teardownMailSessionState,
        { once: true }
    );
    const requestedInitialPeer = window.pendingEmailPeer || "";
    const requestedInitialThread = window.pendingCybernerThread;
    window.pendingEmailPeer = "";
    window.pendingCybernerThread = null;

    const isKnownContact = (name) => contacts.some(contact => contact.name === name);
    const unreadFor = (name) => (unreadCounts.direct && unreadCounts.direct[name]) || 0;
    const cybernerIcon = (key) => (CYBERNER_ICON_LIBRARY[key] || CYBERNER_ICON_LIBRARY.unknown).icon;
    const cybernerLabel = (key) => (CYBERNER_ICON_LIBRARY[key] || CYBERNER_ICON_LIBRARY.unknown).label;
    const defaultWorldChannel = () => ({
        source: "world",
        channel: "world",
        scope: "group",
        peer: "global",
        title: "WORLD",
        subtitle: "Publiczny kanal swiata gry",
        preview: "Publiczny kanal online graczy",
        enabled: true,
        meta: `${groupActiveCount} online`
    });
    const normalizeCybernerChannels = (items) => {
        const seen = new Set();
        const normalized = [];
        const list = Array.isArray(items) && items.length ? items : [defaultWorldChannel()];
        list.forEach(item => {
            if (!item || typeof item !== "object") return;
            const channel = item.channel || item.source || "";
            if (!channel || seen.has(channel)) return;
            seen.add(channel);
            normalized.push({
                source: item.source || channel || "unknown",
                channel,
                scope: item.scope || (channel === "world" ? "group" : "channel"),
                peer: item.peer || (channel === "world" ? "global" : channel),
                title: item.title || cybernerLabel(item.source || channel || "unknown"),
                subtitle: item.subtitle || cybernerLabel(item.source || channel || "unknown"),
                preview: item.preview || "",
                enabled: item.enabled !== false,
                disabled_reason: item.disabled_reason || "",
                meta: item.meta || "",
                active_count: item.active_count,
                clan: item.clan || ""
            });
        });
        if (!seen.has("world")) {
            normalized.unshift(defaultWorldChannel());
        }
        return normalized;
    };
    const currentChannel = () => channels.find(item => item.channel === currentChat.channel)
        || (currentChat.channel === "world" ? defaultWorldChannel() : null);
    const channelUnread = (channel) => {
        if (!channel) return 0;
        if (channel.channel === "world") return unreadCounts.group || 0;
        return (unreadCounts.channel && unreadCounts.channel[channel.peer]) || 0;
    };
    const cybernerSourceKeyForName = (name) => {
        const normalized = String(name || "").trim().toLowerCase();
        if (!normalized) return "unknown";
        if (normalized === "ai central" || normalized === "ai" || normalized.includes("ai central")) return "ai";
        if (normalized === "ghost exchange" || normalized.includes("ghost exchange")) return "ghost_exchange";
        if (normalized === "system" || normalized === "ghost system" || normalized.includes("system")) return "system";
        if (normalized === "misje" || normalized === "mission" || normalized.includes("mission")) return "mission";
        if (normalized.includes("blacknet")) return "blacknet";
        if (normalized.includes("marketplace")) return "marketplace";
        if (normalized.includes("frakcja") || normalized.includes("faction")) return "faction";
        if (normalized.includes("dron") || normalized.includes("drone")) return "drone";
        if (normalized.includes("motocykl") || normalized.includes("bike")) return "bike";
        return "unknown";
    };
    const isWorldSourceKey = (key) => !["unknown", "contact", "friend", "stranger", "request", "own"].includes(key);
    const cybernerSourceForThread = (thread, fallbackKey = "contact") => {
        if (thread && typeof thread === "object") {
            if (thread.source && CYBERNER_ICON_LIBRARY[thread.source]) return thread.source;
            if (thread.channel && CYBERNER_ICON_LIBRARY[thread.channel]) return thread.channel;
            if (thread.source_type && CYBERNER_ICON_LIBRARY[thread.source_type]) return thread.source_type;
            if (thread.type && CYBERNER_ICON_LIBRARY[thread.type]) return thread.type;
            if (thread.is_system) return "system";
            const byName = cybernerSourceKeyForName(thread.name || thread.peer || thread.sender);
            if (byName !== "unknown") return byName;
            if (thread.is_pending || thread.status === "pending") return "request";
            if (thread.is_friend === true) return "friend";
            if (thread.is_friend === false) return "stranger";
        }
        return fallbackKey;
    };
    const formatUnread = (count) => {
        const value = Number(count) || 0;
        if (value <= 0) return "";
        return value > 99 ? "99+" : String(value);
    };
    const threadPreview = (thread, fallback) => {
        if (!thread || typeof thread !== "object") return fallback;
        const summaryKey = thread.scope && (thread.peer || thread.name)
            ? `${thread.scope}:${thread.peer || thread.name}`
            : "";
        const summary = summaryKey ? threadSummaries.get(summaryKey) : null;
        const preview = thread.preview || thread.last_message || thread.last_body || thread.body || thread.subject || thread.last_subject || thread.message || summary?.preview || summary?.subject;
        return preview ? String(preview) : fallback;
    };
    const latestGroupPreview = () => {
        const last = Array.isArray(groupMessages) && groupMessages.length
            ? groupMessages[groupMessages.length - 1]
            : null;
        return threadPreview(last, "Publiczny kanal online graczy");
    };
    const relationClassForThread = (thread, fallback = "") => {
        if (!thread || typeof thread !== "object") return fallback;
        const sourceKey = cybernerSourceForThread(thread, "");
        if (isWorldSourceKey(sourceKey)) return "is-system";
        if (thread.is_pending || thread.status === "pending") return "is-pending is-stranger";
        if (thread.is_friend === true) return "is-friend";
        if (thread.is_friend === false) return "is-stranger";
        return fallback;
    };
    const renderThreadItemContent = ({ iconKey = "unknown", name, preview, meta, unread = 0, avatarClass = "", metaClass = "", kind = "" }) => {
        const unreadLabel = formatUnread(unread);
        const kindMarkup = kind ? `<span class="mail-conversation-kind">${escapeHTML(kind)}</span>` : "";
        return `
            <span class="mail-avatar ${avatarClass}">${cybernerIcon(iconKey)}</span>
            <span class="mail-conversation-content">
                <span class="mail-conversation-title-row">
                    <span class="mail-conversation-name">${escapeHTML(name || "Nieznany")}</span>
                    ${kindMarkup}
                </span>
                <span class="mail-conversation-preview">${escapeHTML(preview || "")}</span>
            </span>
            <span class="mail-conversation-side">
                <span class="mail-unread-badge" style="display:${unreadLabel ? "inline-flex" : "none"};">${escapeHTML(unreadLabel)}</span>
                <small class="mail-conversation-meta ${metaClass}">${meta}</small>
            </span>
        `;
    };
    const isNearMessageBottom = () => messagesBox.scrollHeight - messagesBox.scrollTop - messagesBox.clientHeight < 48;
    const messageSenderLabel = (msg) => msg.sender || msg.from || "System";
    const messageStableId = (msg) => {
        if (!msg || typeof msg !== "object") return "";
        if (msg.message_id) return String(msg.message_id);
        return [msg.scope || "", msg.peer_name || msg.peer || "", msg.id || "", msg.sender || "", msg.created_at || ""].join(":");
    };
    const replaceCurrentMessages = (messages) => {
        currentMessages = [];
        messageIds.clear();
        (Array.isArray(messages) ? messages : []).forEach(message => {
            const messageId = messageStableId(message);
            if (messageId && messageIds.has(messageId)) return;
            if (messageId) messageIds.add(messageId);
            currentMessages.push(message);
        });
        return currentMessages;
    };
    const appendCurrentMessage = (message) => {
        const messageId = messageStableId(message);
        if (messageId && messageIds.has(messageId)) return false;
        if (messageId) messageIds.add(messageId);
        currentMessages.push(message);
        return true;
    };
    const mergeMessages = (...collections) => {
        const merged = [];
        const seen = new Set();
        collections.forEach(collection => {
            (Array.isArray(collection) ? collection : []).forEach(message => {
                const messageId = messageStableId(message);
                if (messageId && seen.has(messageId)) return;
                if (messageId) seen.add(messageId);
                merged.push(message);
            });
        });
        return merged;
    };
    const currentChatMatchesMessage = (message) => {
        if (!message || typeof message !== "object") return false;
        const messageChannel = message.channel || (message.scope === "world" || message.scope === "group" ? "world" : null);
        if (currentChat.channel || messageChannel) {
            return String(currentChat.channel || "") === String(messageChannel || "");
        }
        return String(currentChat.scope || "") === String(message.scope || "")
            && String(currentChat.peer || "") === String(message.peer || message.peer_name || "");
    };
    const createClientMessageId = () => {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        return `cyberner-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    };
    const cybernerSourceKeyForMessage = (msg, own = false) => {
        if (own) return "own";
        if (msg && typeof msg === "object") {
            if (msg.source && CYBERNER_ICON_LIBRARY[msg.source]) return msg.source;
            if (msg.channel && CYBERNER_ICON_LIBRARY[msg.channel]) return msg.channel;
            if (msg.source_type && CYBERNER_ICON_LIBRARY[msg.source_type]) return msg.source_type;
            if (msg.type && CYBERNER_ICON_LIBRARY[msg.type]) return msg.type;
        }
        const bySender = cybernerSourceKeyForName(messageSenderLabel(msg || {}));
        return bySender !== "unknown" ? bySender : "contact";
    };
    const isSystemMessage = (msg) => {
        const sender = String(messageSenderLabel(msg)).toLowerCase();
        const sourceKey = cybernerSourceKeyForMessage(msg, false);
        const systemSourceKeys = new Set([
            "system", "ai", "ghost_exchange", "mission", "blacknet",
            "marketplace", "faction", "drone", "bike"
        ]);
        return msg.system === true
            || systemSourceKeys.has(sourceKey)
            || sender === "system"
            || sender === "ghost system";
    };
    const isMailNarrow = () => term.classList.contains('mail-window-narrow')
        || term.classList.contains('browser-narrow')
        || window.matchMedia('(max-width: 760px), (max-height: 700px)').matches;
    const setMailMobileView = (view) => {
        mailMobileView = view === "chat" ? "chat" : "list";
        mailApp.dataset.mobileView = mailMobileView;
    };
    const openMailChatViewIfNarrow = () => {
        if (isMailNarrow()) {
            setMailMobileView("chat");
        }
    };
    const isCurrentChatSendable = () => {
        if (!currentChat || !currentChat.scope || !currentChat.peer) return false;
        if (currentChat.channel) {
            const channel = currentChannel();
            return !!channel && channel.enabled !== false;
        }
        return true;
    };
    const updateComposerState = () => {
        const sendable = isCurrentChatSendable();
        const hasBody = !!messageInput.value.trim();
        messageInput.disabled = !sendable || mailSending;
        messageButton.disabled = !sendable || !hasBody || mailSending;
        messageForm.classList.toggle('is-disabled', !sendable);
        messageForm.classList.toggle('is-sending', mailSending);
        messageInput.placeholder = sendable ? "Napisz wiadomosc..." : "Ten kanal jest niedostepny.";
    };
    const updateMailViewportInset = () => {
        let offset = 0;
        if (window.visualViewport && isMailNarrow()) {
            offset = Math.max(0, window.innerHeight - window.visualViewport.height - window.visualViewport.offsetTop);
        }
        mailApp.style.setProperty('--mail-keyboard-offset', `${Math.round(offset)}px`);
    };
    const updateMailNarrowMode = () => {
        const rect = term.getBoundingClientRect();
        term.classList.toggle('mail-window-narrow', rect.width < 720 || rect.height < 520);
        mailApp.dataset.mobileView = mailMobileView;
        updateMailViewportInset();
    };
    const shouldRefreshVisibleChat = () => !isMailNarrow() || mailMobileView === "chat";
    const publishActiveCybernerThread = () => {
        window.activeCybernerThread = {
            scope: currentChat.scope || "group",
            peer: currentChat.peer || "global",
            channel: currentChat.channel || null,
            source: currentChat.source || null
        };
    };

    const setActiveThread = () => {
        publishActiveCybernerThread();
        term.querySelectorAll('.mail-thread').forEach(el => el.classList.remove('active'));
        if (currentChat.channel) {
            const channel = currentChannel();
            const btn = Array.from(term.querySelectorAll('.mail-thread'))
                .find(el => el.dataset.channel === currentChat.channel);
            if (btn) btn.classList.add('active');
            chatTitle.textContent = (channel && channel.title) || currentChat.title || "WORLD";
            const subtitle = channel && channel.channel === "world"
                ? `${channel.subtitle || "Publiczny kanal swiata gry"} - ${groupActiveCount} online`
                : (channel && (channel.disabled_reason || channel.subtitle)) || currentChat.subtitle || "";
            chatSubtitle.textContent = subtitle;
            acceptBtn.style.display = "none";
            removeBtn.style.display = "none";
            updateComposerState();
            return;
        }

        const btn = Array.from(term.querySelectorAll('.mail-thread'))
            .find(el => el.dataset.contactName === currentChat.peer);
        if (btn) btn.classList.add('active');
        chatTitle.textContent = currentChat.peer;
        const known = isKnownContact(currentChat.peer);
        const sourceKey = cybernerSourceKeyForName(currentChat.peer);
        const worldSource = isWorldSourceKey(sourceKey);
        chatSubtitle.textContent = worldSource ? cybernerLabel(sourceKey) : known ? "Czat indywidualny" : "Nieznany kontakt";
        acceptBtn.style.display = known || worldSource ? "none" : "inline-block";
        removeBtn.style.display = known && !worldSource ? "inline-block" : "none";
        updateComposerState();
    };

    const renderChannels = () => {
        channelsBox.innerHTML = "";
        normalizeCybernerChannels(channels).forEach(channel => {
            const btn = document.createElement('button');
            btn.type = "button";
            btn.className = `mail-thread mail-conversation-item mail-channel-item mail-channel-${channel.channel || "unknown"} ${channel.enabled ? "" : "is-disabled"}`.trim();
            btn.dataset.channel = channel.channel || "";
            btn.dataset.source = channel.source || "";
            btn.dataset.scope = channel.scope || "";
            btn.dataset.peer = channel.peer || "";
            btn.setAttribute("aria-disabled", channel.enabled ? "false" : "true");
            if (!channel.enabled) {
                btn.disabled = true;
                btn.title = channel.disabled_reason || "Kanal czeka na runtime.";
            }
            const unread = channelUnread(channel);
            const preview = channel.channel === "world" ? latestGroupPreview() : channel.preview;
            const meta = channel.channel === "world"
                ? `<span>world</span><span>${escapeHTML(`${groupActiveCount} online`)}</span>`
                : `<span>${escapeHTML(channel.enabled ? (channel.meta || channel.subtitle || "") : "wkrótce")}</span>`;
            btn.innerHTML = renderThreadItemContent({
                iconKey: channel.source || channel.channel || "unknown",
                name: channel.title || cybernerLabel(channel.source || channel.channel || "unknown"),
                preview: preview || channel.disabled_reason || "",
                meta,
                unread,
                avatarClass: `mail-avatar-${channel.source || channel.channel || "unknown"}`,
                metaClass: channel.enabled ? "mail-status-system" : "mail-status-disabled",
                kind: channel.enabled ? "kanał" : "placeholder"
            });
            if (channel.enabled) {
                btn.addEventListener('click', () => {
                    currentChat = {
                        scope: channel.scope || "group",
                        peer: channel.peer || "global",
                        source: channel.source || "world",
                        channel: channel.channel || "world",
                        title: channel.title || "WORLD",
                        subtitle: channel.subtitle || ""
                    };
                    setActiveThread();
                    openMailChatViewIfNarrow();
                    loadMessages();
                });
            }
            channelsBox.appendChild(btn);
        });
    };

    const renderContacts = () => {
        renderChannels();
        contactsBox.innerHTML = "";
        contacts.forEach(contact => {
            const contactName = contact.name || "Nieznany";
            const btn = document.createElement('button');
            btn.type = "button";
            btn.className = `mail-thread mail-conversation-item ${relationClassForThread(contact)}`.trim();
            btn.dataset.contactName = contactName;
            const statusClass = contact.status === "online" ? "online" : "offline";
            const mailStatusClass = contact.status === "online" ? "mail-status-online" : "mail-status-offline";
            const sourceKey = cybernerSourceForThread(contact, "contact");
            const unread = unreadFor(contactName);
            btn.innerHTML = renderThreadItemContent({
                iconKey: sourceKey,
                name: contactName,
                preview: threadPreview(contact, "Czat indywidualny"),
                meta: `<span>${escapeHTML(isWorldSourceKey(sourceKey) ? cybernerLabel(sourceKey) : contact.status || "offline")}</span>`,
                unread,
                avatarClass: isWorldSourceKey(sourceKey) ? `mail-avatar-${sourceKey}` : "mail-avatar-contact",
                metaClass: `${statusClass} ${mailStatusClass}`,
                kind: isWorldSourceKey(sourceKey) ? "źródło" : "prywatne"
            });
            btn.addEventListener('click', () => {
                currentChat = { scope: "direct", peer: contactName };
                setActiveThread();
                openMailChatViewIfNarrow();
                loadMessages();
            });
            contactsBox.appendChild(btn);
        });

        pendingBox.innerHTML = "";
        pendingWrap.style.display = pendingThreads.length ? "grid" : "none";
        pendingWrap.classList.toggle("is-visible", pendingThreads.length > 0);
        pendingThreads.forEach(thread => {
            const threadName = thread.name || "Nieznany";
            const btn = document.createElement('button');
            btn.type = "button";
            btn.className = `mail-thread mail-conversation-item pending ${relationClassForThread(thread, "is-pending is-stranger")}`.trim();
            btn.dataset.contactName = threadName;
            const unread = unreadFor(threadName);
            const sourceKey = cybernerSourceForThread(thread, "request");
            const worldSource = isWorldSourceKey(sourceKey);
            const pendingMeta = thread.last_at
                ? `<span>${escapeHTML(worldSource ? cybernerLabel(sourceKey) : "nowe")}</span><span>${escapeHTML(thread.last_at)}</span>`
                : `<span>${escapeHTML(worldSource ? cybernerLabel(sourceKey) : "nowe")}</span>`;
            btn.innerHTML = renderThreadItemContent({
                iconKey: sourceKey,
                name: threadName,
                preview: threadPreview(thread, worldSource ? "Zrodlo swiata gry" : "Oczekuje na kontakt"),
                meta: pendingMeta,
                unread,
                avatarClass: worldSource ? `mail-avatar-${sourceKey}` : "mail-avatar-pending",
                metaClass: worldSource ? "mail-status-system" : "pending mail-status-pending",
                kind: worldSource ? "źródło" : "nowe"
            });
            btn.addEventListener('click', () => {
                currentChat = { scope: "direct", peer: threadName };
                setActiveThread();
                openMailChatViewIfNarrow();
                loadMessages();
            });
            pendingBox.appendChild(btn);
        });
        setActiveThread();
    };

    const applyMailDeltaPayload = (payload = {}) => {
        latestMailDeltaVersion = Math.max(latestMailDeltaVersion, Number(payload.delta_version || 0));
        if (Array.isArray(payload.channels)) {
            channels = normalizeCybernerChannels(payload.channels);
        }
        if (Array.isArray(payload.contacts)) {
            contacts = payload.contacts;
        }
        if (Array.isArray(payload.pending_threads)) {
            pendingThreads = payload.pending_threads;
        }
        if (Array.isArray(payload.group_messages)) {
            groupMessages = payload.group_messages;
        }
        if (Object.prototype.hasOwnProperty.call(payload, "group_active_count")) {
            groupActiveCount = payload.group_active_count ?? groupActiveCount;
        }
        if (payload.unread_counts && typeof payload.unread_counts === "object") {
            unreadCounts = payload.unread_counts;
        }
        const liveMessage = payload.message && typeof payload.message === "object"
            ? payload.message
            : null;
        if (liveMessage) {
            const isOpen = currentChatMatchesMessage(liveMessage) && shouldRefreshVisibleChat();
            if (isOpen && appendCurrentMessage(liveMessage)) {
                renderMessages(currentMessages, isNearMessageBottom());
                setTimeout(() => loadMessages({ recovery: true, preserveScroll: true }), 0);
            } else if (!isOpen && messageSenderLabel(liveMessage) !== currentUser) {
                if (liveMessage.channel === "world") {
                    unreadCounts.group = Number(unreadCounts.group || 0) + 1;
                } else if (liveMessage.channel === "clan" || liveMessage.channel === "friends") {
                    const peer = liveMessage.peer || payload.peer;
                    unreadCounts.channel = unreadCounts.channel || {};
                    unreadCounts.channel[peer] = Number(unreadCounts.channel[peer] || 0) + 1;
                } else if (liveMessage.channel === "direct") {
                    const peer = liveMessage.peer || liveMessage.sender;
                    unreadCounts.direct = unreadCounts.direct || {};
                    unreadCounts.direct[peer] = Number(unreadCounts.direct[peer] || 0) + 1;
                }
            }
        }
        const thread = payload.thread && typeof payload.thread === "object" ? payload.thread : null;
        if (thread) {
            const scope = thread.scope || payload.scope || "direct";
            const peer = thread.peer || payload.peer || (scope === "group" ? "global" : "");
            const key = `${scope}:${peer}`;
            threadSummaries.set(key, thread);
            if (scope === "group") {
                const threadId = messageStableId(thread);
                const existing = new Set(groupMessages.map(messageStableId));
                if (!threadId || !existing.has(threadId)) groupMessages = [...groupMessages, thread];
            } else if (scope === "channel") {
                channels = normalizeCybernerChannels(channels).map(channel => {
                    if (String(channel.peer || "") !== String(peer || "")) return channel;
                    return {
                        ...channel,
                        preview: thread.preview || thread.subject || channel.preview || "",
                        meta: channel.meta || thread.created_at || ""
                    };
                });
            } else if (scope === "direct") {
                const applyThread = item => {
                    if (!item || String(item.name || item.peer || "") !== String(peer || "")) return item;
                    return {
                        ...item,
                        preview: thread.preview || thread.subject || item.preview || "",
                        last_at: thread.created_at || item.last_at
                    };
                };
                contacts = contacts.map(applyThread);
                pendingThreads = pendingThreads.map(applyThread);
            }
        }
        renderContacts();
    };

    cybernerDeltaClients.add({
        isConnected: () => document.body.contains(term),
        update: applyMailDeltaPayload
    });

    const renderMessages = (messages, forceScroll = false) => {
        const shouldStickToBottom = forceScroll || isNearMessageBottom();
        replaceCurrentMessages(messages);
        messagesBox.innerHTML = "";
        if (!currentMessages.length) {
            messagesBox.innerHTML = `<div class="mail-empty">Brak wiadomosci. Zacznij rozmowe.</div>`;
            return;
        }

        currentMessages.forEach(msg => {
            const item = document.createElement('div');
            const sender = messageSenderLabel(msg);
            const own = sender === currentUser;
            const system = isSystemMessage(msg);
            const unknown = currentChat.scope === "direct" && !own && !system && !isKnownContact(sender);
            item.className = `mail-message ${own ? "own is-own" : ""} ${system ? "system is-system" : ""} ${unknown ? "unknown" : ""}`.trim();
            const subject = msg.subject ? `<div class="mail-message-subject">${escapeHTML(msg.subject)}</div>` : "";
            const sourceKey = cybernerSourceKeyForMessage(msg, own);
            const avatarClass = system ? `mail-avatar-${sourceKey}` : own ? "mail-avatar-own" : "mail-avatar-contact";
            item.innerHTML = `
                <span class="mail-message-avatar ${avatarClass}">${cybernerIcon(sourceKey)}</span>
                <span class="mail-message-content">
                    <span class="mail-message-meta">
                        <span class="mail-message-sender">${escapeHTML(sender)}</span>
                        <span class="mail-message-time">${escapeHTML(msg.created_at || "")}</span>
                    </span>
                    ${subject}
                    <span class="mail-message-body">${escapeHTML(msg.body || "")}</span>
                </span>
            `;
            messagesBox.appendChild(item);
        });
        if (shouldStickToBottom) {
            messagesBox.scrollTop = messagesBox.scrollHeight;
        }
    };

    const loadMessages = async (options = {}) => {
        if (mailClosed || !document.body.contains(term)) return null;
        const requestKey = `${currentChat.scope}:${currentChat.peer}`;
        const state = requestState.messages;
        if (state.inFlight && state.key === requestKey) return state.inFlight;
        if (state.controller) state.controller.abort();
        const controller = new AbortController();
        const version = ++state.version;
        const startedDeltaVersion = latestMailDeltaVersion;
        state.controller = controller;
        state.key = requestKey;
        const params = new URLSearchParams({
            scope: currentChat.scope,
            peer: currentChat.peer
        });
        const task = (async () => {
            try {
                const scrollTop = messagesBox.scrollTop;
                const res = await fetch(`/api/chats/messages?${params.toString()}`, { signal: controller.signal });
                if (!res.ok) throw new Error(`Cyberner messages HTTP ${res.status}`);
                const data = await res.json();
                if (mailClosed || version !== state.version || requestKey !== `${currentChat.scope}:${currentChat.peer}`) return null;
                unreadCounts = data.unread_counts || unreadCounts;
                groupActiveCount = data.group_active_count ?? groupActiveCount;
                const responseMessages = startedDeltaVersion < latestMailDeltaVersion
                    ? mergeMessages(data.messages, currentMessages)
                    : (data.messages || []);
                if (currentChat.scope === "group") groupMessages = responseMessages;
                renderContacts();
                renderMessages(responseMessages);
                if (options.preserveScroll && !isNearMessageBottom()) messagesBox.scrollTop = scrollTop;
                return data;
            } catch (err) {
                if (err && err.name === "AbortError") return null;
                console.warn("Cyberner message recovery failed", err);
                return null;
            } finally {
                if (version === state.version) {
                    state.inFlight = null;
                    state.controller = null;
                }
            }
        })();
        state.inFlight = task;
        return task;
    };

    const openDirectChat = async (name) => {
        if (!name) return;
        currentChat = { scope: "direct", peer: name };
        setActiveThread();
        openMailChatViewIfNarrow();
        await loadMessages();
    };

    const openCybernerThread = async (thread) => {
        if (!thread || typeof thread !== "object") return;
        if (thread.scope === "direct") {
            await openDirectChat(thread.peer || thread.sender || thread.title);
            return;
        }
        const scope = thread.scope || (thread.channel === "world" ? "group" : "channel");
        const peer = thread.peer || (scope === "group" ? "global" : thread.channel);
        const channel = thread.channel || (scope === "group" && peer === "global" ? "world" : null);
        const source = thread.source || channel || "unknown";
        currentChat = {
            scope,
            peer,
            channel,
            source,
            title: thread.title || cybernerLabel(source),
            subtitle: thread.subtitle || ""
        };
        setActiveThread();
        openMailChatViewIfNarrow();
        await loadMessages();
    };

    const refreshThreads = async (initial = false) => {
        if (mailClosed || !document.body.contains(term)) return null;
        const state = requestState.bootstrap;
        if (state.inFlight) return state.inFlight;
        const controller = new AbortController();
        const version = ++state.version;
        const startedDeltaVersion = latestMailDeltaVersion;
        state.controller = controller;
        const task = (async () => {
            try {
                const res = await fetch('/api/mail/bootstrap', { signal: controller.signal });
                if (!res.ok) throw new Error(`Cyberner bootstrap HTTP ${res.status}`);
                const data = await res.json();
                if (mailClosed || version !== state.version) return null;
                currentUser = data.username || currentUser;
                channels = normalizeCybernerChannels(data.channels);
                contacts = data.contacts || [];
                pendingThreads = data.pending_threads || [];
                unreadCounts = data.unread_counts || unreadCounts;
                groupActiveCount = data.group_active_count ?? groupActiveCount;
                groupMessages = startedDeltaVersion < latestMailDeltaVersion
                    ? mergeMessages(data.group_messages, groupMessages)
                    : (data.group_messages || groupMessages);
                renderContacts();
                if (initial && requestedInitialPeer) {
                    await openDirectChat(requestedInitialPeer);
                } else if (initial && requestedInitialThread) {
                    await openCybernerThread(requestedInitialThread);
                } else if (shouldRefreshVisibleChat()) {
                    await loadMessages({ recovery: !initial, preserveScroll: !initial });
                }
                return data;
            } catch (err) {
                if (err && err.name === "AbortError") return null;
                console.warn("Cyberner bootstrap recovery failed", err);
                return null;
            } finally {
                if (version === state.version) {
                    state.inFlight = null;
                    state.controller = null;
                }
            }
        })();
        state.inFlight = task;
        return task;
    };

    const bootstrap = () => refreshThreads(true);

    backBtn.addEventListener('click', () => {
        setMailMobileView("list");
    });

    term.addEventListener('ghost-open-email-chat', (event) => {
        openDirectChat(event.detail && event.detail.peer);
    });

    term.addEventListener('ghost-open-cyberner-thread', (event) => {
        openCybernerThread(event.detail || {});
    });

    contactForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = contactInput.value.trim();
        if (!name) return;

        const res = await fetch('/api/contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (data.error) {
            addSystemMessage("warning", "Kontakt", data.error);
            return;
        }
        if (data.contacts) {
            contacts = data.contacts;
            pendingThreads = (data.pending_threads || pendingThreads).filter(thread => thread.name !== name);
            contactInput.value = "";
            renderContacts();
        }
    });

    acceptBtn.addEventListener('click', async () => {
        if (currentChat.scope !== "direct") return;
        const name = currentChat.peer;
        const res = await fetch('/api/contacts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (data.error) {
            addSystemMessage("warning", "Kontakt", data.error);
            return;
        }
        if (data.contacts) {
            contacts = data.contacts;
            pendingThreads = pendingThreads.filter(thread => thread.name !== name);
            renderContacts();
        }
    });

    removeBtn.addEventListener('click', async () => {
        if (currentChat.scope !== "direct") return;
        const name = currentChat.peer;
        const res = await fetch(`/api/contacts/${encodeURIComponent(name)}`, { method: 'DELETE' });
        const data = await res.json();
        contacts = data.contacts || contacts.filter(c => c.name !== name);
        currentChat = { scope: "group", peer: "global", source: "world", channel: "world", title: "WORLD" };
        renderContacts();
        loadMessages();
    });

    messageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = messageInput.value.trim();
        if (!body || mailSending || !isCurrentChatSendable()) {
            updateComposerState();
            return;
        }

        mailSending = true;
        updateComposerState();
        const sendKey = `${currentChat.scope}:${currentChat.peer}:${body}`;
        if (!pendingSend || pendingSend.key !== sendKey) {
            pendingSend = { key: sendKey, clientMessageId: createClientMessageId() };
        }
        try {
            const res = await fetch('/api/chats/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scope: currentChat.scope,
                    peer: currentChat.peer,
                    body,
                    client_message_id: pendingSend.clientMessageId
                })
            });
            const data = await res.json();
            if (data.error) {
                if (res.status >= 400 && res.status < 500) pendingSend = null;
                addSystemMessage("warning", "Cyberner", data.error);
                return;
            }
            if (data.messages) {
                pendingSend = null;
                contacts = data.contacts || contacts;
                pendingThreads = data.pending_threads || pendingThreads;
                unreadCounts = data.unread_counts || unreadCounts;
                groupActiveCount = data.group_active_count ?? groupActiveCount;
                if (currentChat.scope === "group") {
                    groupMessages = data.messages || groupMessages;
                }
                messageInput.value = "";
                renderContacts();
                renderMessages(data.messages, true);
                playCybernerMessageSfx({
                    message: data.message || {},
                    message_id: data.message_id,
                    channel: data.channel && data.channel.channel,
                    channel_key: data.channel && data.channel.channel_key
                }, { own: true });
            }
        } catch (err) {
            addSystemMessage("danger", "Cyberner", "Nie udalo sie wyslac wiadomosci.");
        } finally {
            mailSending = false;
            updateComposerState();
        }
    });
    messageInput.addEventListener('input', updateComposerState);
    messageInput.addEventListener('focus', updateMailViewportInset);
    messageInput.addEventListener('blur', () => setTimeout(updateMailViewportInset, 80));

    updateMailNarrowMode();
    updateComposerState();
    bootstrap();
    const mailResizeHandler = () => updateMailNarrowMode();
    window.addEventListener('resize', mailResizeHandler);
    if (window.visualViewport) {
        window.visualViewport.addEventListener('resize', updateMailViewportInset);
        window.visualViewport.addEventListener('scroll', updateMailViewportInset);
    }
    let mailResizeObserver = null;
    if (window.ResizeObserver) {
        mailResizeObserver = new ResizeObserver(updateMailNarrowMode);
        mailResizeObserver.observe(term);
    }
    const scheduleMailRefresh = () => {
        if (mailClosed || !desktopSessionActive) return;
        mailRefreshTimer = setTimeout(async () => {
            if (mailClosed || !desktopSessionActive) return;
            await refreshThreads(false);
            scheduleMailRefresh();
        }, CYBERNER_THREAD_REFRESH_INTERVAL_MS);
    };
    scheduleMailRefresh();
    term.querySelector('.close-btn').addEventListener('click', () => {
        window.removeEventListener(
            "chaos:session-invalidated",
            teardownMailSessionState
        );
        teardownMailSessionState();
        window.removeEventListener('resize', mailResizeHandler);
        if (window.visualViewport) {
            window.visualViewport.removeEventListener('resize', updateMailViewportInset);
            window.visualViewport.removeEventListener('scroll', updateMailViewportInset);
        }
        if (mailResizeObserver) {
            mailResizeObserver.disconnect();
        }
    }, { once: true });
}

window.openEmailChatWith = function(peerName) {
    if (!peerName) return false;
    window.pendingEmailPeer = peerName;
    const existing = document.querySelector(`.terminal[data-app="email"]`);
    if (existing) {
        existing.dispatchEvent(new CustomEvent('ghost-open-email-chat', {
            detail: { peer: peerName }
        }));
        if (typeof bringToFront === "function") {
            bringToFront(existing);
        }
        return true;
    }
    createEmailClient();
    return true;
};

window.openCybernerThread = function(thread) {
    if (!thread || typeof thread !== "object") return false;
    window.pendingCybernerThread = thread;
    const existing = document.querySelector(`.terminal[data-app="email"]`);
    if (existing) {
        existing.dispatchEvent(new CustomEvent('ghost-open-cyberner-thread', {
            detail: thread
        }));
        if (typeof bringToFront === "function") {
            bringToFront(existing);
        }
        return true;
    }
    createEmailClient();
    return true;
};

function escapeHTML(value) {
    let str = "";
    if (value === null || value === undefined) {
        str = "";
    } else if (typeof value === "object") {
        const label = value.label ?? value.name ?? value.text ?? value.title ?? value.value;
        if (label !== null && label !== undefined) {
            str = String(label);
        } else {
            try {
                str = JSON.stringify(value);
            } catch (err) {
                str = String(value);
            }
        }
    } else {
        str = String(value);
    }
    return str.replace(/[&<>"']/g, function (m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[m];
    });
}

function sanitizeToastHTML(value) {
    let str = "";
    if (value === null || value === undefined) {
        str = "";
    } else if (typeof value === "object") {
        const label = value.label ?? value.name ?? value.text ?? value.title ?? value.value;
        str = label !== null && label !== undefined ? String(label) : "";
    } else {
        str = String(value);
    }

    const allowedTags = new Set(["B", "STRONG", "I", "EM", "BR", "CODE", "SPAN"]);
    const droppedTags = new Set(["SCRIPT", "STYLE", "IFRAME", "OBJECT", "EMBED", "LINK", "META"]);
    const template = document.createElement("template");
    template.innerHTML = str;

    const cleanNode = (node) => {
        if (node.nodeType === Node.TEXT_NODE) {
            return document.createTextNode(node.textContent || "");
        }
        if (node.nodeType !== Node.ELEMENT_NODE) {
            return document.createDocumentFragment();
        }
        if (droppedTags.has(node.tagName)) {
            return document.createDocumentFragment();
        }

        const target = allowedTags.has(node.tagName)
            ? document.createElement(node.tagName.toLowerCase())
            : document.createDocumentFragment();

        Array.from(node.childNodes || []).forEach(child => {
            target.appendChild(cleanNode(child));
        });
        return target;
    };

    const result = document.createElement("div");
    Array.from(template.content.childNodes || []).forEach(node => {
        result.appendChild(cleanNode(node));
    });
    return result.innerHTML;
}

function formatStorageSize(value, unit = "MB") {
    const number = Number(value || 0);
    if (!Number.isFinite(number) || number <= 0) return `0 ${unit}`;
    return `${Math.round(number)} ${unit}`;
}

function normalizeCybernerNotificationThread(message) {
    if (!message || typeof message !== "object") return null;
    const scope = message.scope || (message.channel === "world" ? "group" : "direct");
    const peer = message.peer || (scope === "group" ? "global" : message.sender || message.title);
    const source = message.source || (scope === "group" ? "world" : "player");
    const channel = scope === "group" && peer === "global"
        ? "world"
        : (scope === "channel" ? source : null);
    return {
        scope,
        peer,
        source,
        channel,
        title: message.title || (CYBERNER_NOTIFICATION_LIBRARY[source] || CYBERNER_NOTIFICATION_LIBRARY.unknown).label
    };
}

function isCybernerThreadCurrentlyOpen(thread) {
    const active = window.activeCybernerThread;
    if (!thread || !active) return false;
    return String(active.scope || "") === String(thread.scope || "")
        && String(active.peer || "") === String(thread.peer || "");
}

document.querySelectorAll('.icon').forEach(icon => {
    let isDragging = false;
    let offsetX = 0;
    let offsetY = 0;

    icon.addEventListener('mousedown', (e) => {
        isDragging = true;
        icon.style.zIndex = 999; // ikona nad innymi ikonami, ale nadal pod oknami
        offsetX = e.clientX - icon.offsetLeft;
        offsetY = e.clientY - icon.offsetTop;
        document.body.style.userSelect = 'none';
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        icon.style.left = `${e.clientX - offsetX}px`;
        icon.style.top = `${e.clientY - offsetY}px`;
    });

    window.addEventListener('mouseup', () => {
        isDragging = false;
        icon.style.zIndex = '';
        document.body.style.userSelect = 'auto';
    });
});

function shouldSuppressDuplicateSystemToast(message, type = 'success') {
    const now = Date.now();
    const ttlMs = 20000;
    window.__systemToastDedupe = window.__systemToastDedupe || new Map();
    for (const [key, expiresAt] of window.__systemToastDedupe.entries()) {
        if (expiresAt <= now) {
            window.__systemToastDedupe.delete(key);
        }
    }
    const key = [
        message && message.id ? `id:${message.id}` : "",
        type || "",
        message && message.title ? String(message.title) : "",
        message && message.text ? String(message.text) : "",
        message && message.notification_type ? String(message.notification_type) : ""
    ].join("|");
    if (window.__systemToastDedupe.has(key)) {
        return true;
    }
    window.__systemToastDedupe.set(key, now + ttlMs);
    return false;
}

function showSystemToast(message, type = 'success') {
    const container = document.getElementById("system-toast-container");
    if (!container || shouldSuppressDuplicateSystemToast(message, type)) {
        return;
    }
    const isCyberner = message && message.notification_type === "cyberner";
    const cybernerThread = isCyberner ? normalizeCybernerNotificationThread(message) : null;
    if (isCyberner && isCybernerThreadCurrentlyOpen(cybernerThread)) {
        return;
    }
    const notificationSource = (message && message.source) || "unknown";
    const notificationConfig = CYBERNER_NOTIFICATION_LIBRARY[notificationSource] || CYBERNER_NOTIFICATION_LIBRARY.unknown;
    const div = document.createElement('div');
    div.className = `system-toast ${type} ${isCyberner ? "cyberner-toast" : ""}`.trim();
    if (isCyberner) {
        div.setAttribute("role", "button");
        div.tabIndex = 0;
        div.innerHTML = `
            <h4><span class="cyberner-toast-icon">${escapeHTML(notificationConfig.icon)}</span>${escapeHTML(message.title || notificationConfig.label)}</h4>
            <div>${sanitizeToastHTML(message.text || notificationConfig.text)}</div>
        `;
        const openToastThread = () => {
            if (cybernerThread && typeof window.openCybernerThread === "function") {
                window.openCybernerThread(cybernerThread);
            }
            div.remove();
        };
        div.addEventListener('click', openToastThread);
        div.addEventListener('keydown', (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openToastThread();
            }
        });
    } else {
        div.innerHTML = `
            <h4>${escapeHTML(message.title || 'Komunikat')}</h4>
            <div>${sanitizeToastHTML(message.text || "")}</div>
        `;
    }
    container.appendChild(div);

    setTimeout(() => {
        div.remove();
    }, 5000);
}

async function pollSystemMessages() {
    if (!desktopSessionActive || systemMessagesPollInFlight) return;
    systemMessagesPollInFlight = true;
    try {
        const res = await fetchDesktopBackground('/system-messages');
        if (!desktopSessionActive) return;
        if (!res.ok) {
            systemMessageSfxCatchup = true;
            return;
        }
        const data = await res.json();
        if (!desktopSessionActive) return;
        const allowSfx = systemMessageSfxLive && !systemMessageSfxCatchup;
        data.forEach((msg, i) => {
            if (allowSfx) playSystemMessageSfx(msg);
            setTimeout(() => {
                if (desktopSessionActive) showSystemToast(msg, msg.type);
            }, i * 2000);
        });
        systemMessageSfxLive = true;
        systemMessageSfxCatchup = false;
    } catch (err) {
        systemMessageSfxCatchup = true;
        if (!err || err.name !== "AbortError") {
            console.error("Błąd pobierania komunikatów systemowych");
        }
    } finally {
        systemMessagesPollInFlight = false;
    }
}

// 🔁 Co 10 sekund sprawdzaj nowe
systemMessagesPollInterval = setInterval(pollSystemMessages, 10000);
stateDeltaStartTimer = setTimeout(pollStateChanges, 1000);
stateDeltaPollInterval = setInterval(pollStateChanges, STATE_DELTA_POLL_INTERVAL_MS);

const LAUNCH_QUEUE_RECENT_TTL_MS = 60000;

function normalizeLaunchQueueItem(rawItem) {
    if (rawItem && typeof rawItem === "object") {
        const name = String(rawItem.name || rawItem.app_name || rawItem.command || "").trim();
        const flowId = getCurrentAppFlowId(rawItem.flow_id || rawItem._flow_id || "");
        const appId = String(rawItem.app_id || rawItem.id || "").trim();
        const action = String(rawItem.action || rawItem.map_action_id || rawItem.action_key || "").trim();
        const explicitReceipt = String(
            rawItem.receipt ||
            rawItem.launch_receipt ||
            rawItem.launch_key ||
            rawItem.idempotency_key ||
            ""
        ).trim();
        const receipt = explicitReceipt || `${flowId || "manual"}:${appId || name}`;
        return {
            name,
            flow_id: flowId,
            app_id: appId,
            action,
            receipt,
            client_action_key: String(rawItem.client_action_key || rawItem.client_key || "").trim(),
            has_explicit_receipt: Boolean(explicitReceipt),
            raw: rawItem
        };
    }
    const name = String(rawItem || "").trim();
    const flowId = getCurrentAppFlowId(window.__lastHackFlowId || "");
    return {
        name,
        flow_id: flowId,
        app_id: "",
        action: "",
        receipt: `${flowId || "manual"}:${name}`,
        client_action_key: "",
        has_explicit_receipt: false,
        raw: rawItem
    };
}

function shouldSkipRecentLaunchQueueApp(name, flowId = "") {
    const key = `${String(flowId || "manual").trim().toLowerCase()}:${String(name || "").trim().toLowerCase()}`;
    if (!key) return true;
    const now = Date.now();
    const expiresAt = recentLaunchQueueApps.get(key) || 0;
    if (expiresAt > now) {
        return true;
    }
    recentLaunchQueueApps.set(key, now + LAUNCH_QUEUE_RECENT_TTL_MS);
    for (const [recentKey, recentExpiresAt] of recentLaunchQueueApps.entries()) {
        if (recentExpiresAt <= now) {
            recentLaunchQueueApps.delete(recentKey);
        }
    }
    return false;
}

async function pollLaunchQueue() {
    if (!desktopSessionActive || launchQueuePollInFlight) {
        hackFlowDebug(window.__lastHackFlowId || "", "desktop", "launch_queue_skip_in_flight", {});
        return;
    }
    launchQueuePollInFlight = true;
    const loadingToken = beginDesktopLoading('Sprawdzam system...');
    try {
        hackFlowDebug(window.__lastHackFlowId || "", "desktop", "launch_queue_poll_start", {});
        const res = await fetchDesktopBackground('/launch-queue', {
            headers: {
                'X-Hack-Flow-Id': window.__lastHackFlowId || ''
            }
        }, LAUNCH_QUEUE_FETCH_TIMEOUT_MS);
        if (!desktopSessionActive) return;
        const appsToLaunch = await res.json();
        if (!desktopSessionActive) return;
        hackFlowDebug(window.__lastHackFlowId || "", "desktop", "launch_queue_response", {
            status: res.status,
            apps: Array.isArray(appsToLaunch) ? appsToLaunch : appsToLaunch
        });

        if (appsToLaunch.logout) {
            window.location.href = '/';
            return;
        }

        if (Array.isArray(appsToLaunch) && appsToLaunch.length > 0) {
            appFlowTrace(window.__lastHackFlowId || "", "launch_queue_received", {
                apps: appsToLaunch
            });
            const uniqueAppsToLaunch = [];
            const seenLegacyLaunchNames = new Set();
            const seenLaunchReceipts = new Set();
            for (const rawItem of appsToLaunch) {
                const item = normalizeLaunchQueueItem(rawItem);
                const name = item.name;
                const flowId = item.flow_id || window.__lastHackFlowId || "";
                const resolution = resolveProvisionalApplicationLaunch(item);
                if (resolution.outcome === "tombstoned") {
                    shouldSkipLaunchQueueReceipt(item.receipt, item);
                    appFlowTrace(flowId, "provisional_app_late_launch_blocked", { name, receipt: item.receipt });
                    continue;
                }
                item.provisionalSession = resolution.session;
                const legacyNameSeen = !item.has_explicit_receipt && seenLegacyLaunchNames.has(name);
                if (
                    !name ||
                    seenLaunchReceipts.has(item.receipt) ||
                    legacyNameSeen ||
                    shouldSkipLaunchQueueReceipt(item.receipt, item) ||
                    (!item.has_explicit_receipt && shouldSkipRecentLaunchQueueApp(name, flowId))
                ) {
                    hackFlowDebug(flowId, "desktop", "launch_queue_skip_app", {
                        name,
                        receipt: item.receipt,
                        seen: seenLaunchReceipts.has(item.receipt) || legacyNameSeen
                    });
                    continue;
                }
                seenLaunchReceipts.add(item.receipt);
                if (!item.has_explicit_receipt) seenLegacyLaunchNames.add(name);
                uniqueAppsToLaunch.push(item);
            }
            for (const item of uniqueAppsToLaunch) {
                const name = item.name;
                const flowId = item.flow_id || window.__lastHackFlowId || "";
                const commandStartedAt = performance.now();
                appFlowTrace(flowId, "launch_queue_command_start", { name, receipt: item.receipt });
                hackFlowDebug(flowId, "desktop", "launch_queue_command_start", { name, receipt: item.receipt });
                const cmdRes = await fetch('/command', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Hack-Flow-Id': flowId
                    },
                    body: JSON.stringify({
                        input: name,
                        source: 'launch_queue',
                        skip_map_runtime: true,
                        _flow_id: flowId,
                        launch_receipt: item.receipt
                    })
                });

                const data = await cmdRes.json();
                appFlowTrace(flowId, "launch_queue_command_response", {
                    name,
                    status: cmdRes.status,
                    elapsed_ms: Math.round(performance.now() - commandStartedAt),
                    runApp: Boolean(data.runApp),
                    app_id: data.applicationEffect && data.applicationEffect.id,
                    interface: data.applicationEffect && data.applicationEffect.interface,
                    created_operations: (data.created_operations || []).map(op => op && op.operation_id)
                });
                hackFlowDebug(flowId, "desktop", "launch_queue_command_response", {
                    name,
                    status: cmdRes.status,
                    runApp: Boolean(data.runApp),
                    app_id: data.applicationEffect && data.applicationEffect.id,
                    interface: data.applicationEffect && data.applicationEffect.interface,
                    created_operations: (data.created_operations || []).map(op => op && op.operation_id)
                });
                notifyCreatedOperations(data);

                if (data.runApp && data.applicationEffect) {
                    const appData = data.applicationEffect;
                    appData._flow_id = flowId;
                    appData._launch_receipt = item.receipt;
                    appData._launch_key = item.receipt;
                    appData._source = 'launch_queue';
                    appData._map_action_id = item.action;
                    appData._client_action_key = item.client_action_key;
                    const id = appData.id;
                    const levels = appData.levels;
                    const type = appData.interface;

                    const action = () => {
                        if (!desktopSessionActive) return;
                        appFlowTrace(flowId, "launch_queue_launch_app", {
                            name,
                            app_id: id,
                            interface: type,
                            receipt: item.receipt
                        });
                        hackFlowDebug(flowId, "desktop", "launch_queue_launch_app", {
                            name,
                            app_id: id,
                            interface: type,
                            receipt: item.receipt
                        });
                        const currentResolution = item.provisionalSession && !item.provisionalSession.disposed
                            ? { outcome: "hydrated", session: item.provisionalSession }
                            : resolveProvisionalApplicationLaunch(item);
                        if (currentResolution.outcome === "tombstoned") {
                            appFlowTrace(flowId, "provisional_app_late_launch_blocked", { name, receipt: item.receipt });
                            return;
                        }
                        if (currentResolution.outcome === "hydrated") {
                            const outcome = hydrateProvisionalApplicationSession(currentResolution.session, appData, item);
                            appFlowTrace(flowId, "provisional_app_hydration", { name, receipt: item.receipt, outcome });
                            return;
                        }
                        launchApplicationEffect(appData);
                    };

                    action();
                }
            }
        }
    } catch (err) {
        hackFlowDebug(window.__lastHackFlowId || "", "desktop", "launch_queue_error", {
            message: err && err.message ? err.message : String(err)
        });
        if (isExpectedFetchAbort(err)) {
            hackFlowDebug(window.__lastHackFlowId || "", "desktop", "launch_queue_timeout", {
                timeout_ms: LAUNCH_QUEUE_FETCH_TIMEOUT_MS
            });
        } else {
            console.error("❌ Błąd podczas pobierania launch-queue:", err);
        }
    } finally {
        // Spróbuj ponownie za 10 sekund
        launchQueuePollInFlight = false;
        endDesktopLoading(loadingToken);
        if (desktopSessionActive) {
            launchQueuePollTimer = setTimeout(pollLaunchQueue, 10000);
        }
    }
}

// Uruchom po załadowaniu strony
document.addEventListener("DOMContentLoaded", () => {
    if (!desktopSessionActive) return;
    pollLaunchQueue();
    refreshPlayerHackAccess();
});
