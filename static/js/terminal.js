let terminalCount = 3;
let topZIndex = 1000;
let windowSequence = 0;
let toolbarLauncherApps = [];
const runningWindows = new Map();
let desktopSettings = { wallpaper: "", icon_positions: {}, auto_fullscreen: false };
let desktopSaveTimer = null;
let toolbarProfile = null;
let toolbarTargetFeedbackState = { targetKey: "", dotSignature: "", progress: 0 };
let desktopSessionActive = true;
let desktopRenderedApps = [];
const fileManagerInstances = new Map();
const cybernerDeltaClients = new Set();
const ghostExchangeDeltaViews = new Set();
let desktopLastSafeMode = null;
let playerHackAccessState = null;
let playerHackAccessTimer = null;
let stateDeltaVersion = 0;
let stateDeltaPollInFlight = false;
const processedDeltaKeys = new Set();
const STATE_DELTA_POLL_INTERVAL_MS = 4000;
const STATE_DELTA_LIMIT = 100;
const STATE_DELTA_DEFAULT_RECOVERY_SCOPES = ["wallet", "storage", "apps", "mail", "ghost_exchange", "map"];
const CYBERNER_THREAD_REFRESH_INTERVAL_MS = 10000;
const APP_TERMINAL_AUTO_CLOSE_MS = 30000;
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
    let isDragging = false;
    let offsetX = 0;
    let offsetY = 0;

    titleBar.addEventListener('mousedown', (e) => {
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
        if (!isDragging) return;
        isDragging = false;
        document.body.style.userSelect = 'auto';
    });

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
        auto_fullscreen: autoFullscreen
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
        const payload = JSON.stringify(settings);
        return navigator.sendBeacon('/api/profile/desktop', new Blob([payload], { type: 'application/json' }));
    } catch (err) {
        console.warn("Nie udało się zapisać pulpitu beaconem:", err);
        return false;
    }
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
        <div id="system-running-apps"></div>
        <div id="system-status-strip"></div>
    `;
    document.body.appendChild(toolbar);

    const startButton = toolbar.querySelector('#system-start-button');
    const startMenu = toolbar.querySelector('#system-start-menu');
    startButton.addEventListener('click', (event) => {
        event.stopPropagation();
        startMenu.hidden = !startMenu.hidden;
    });
    document.addEventListener('click', (event) => {
        if (!toolbar.contains(event.target)) {
            startMenu.hidden = true;
        }
    });

    renderStartMenu();
    renderRunningApps();
    renderToolbarStatus();
    return toolbar;
}

function setToolbarProfile(profile) {
    toolbarProfile = profile || toolbarProfile;
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

function calculateToolbarArsenalCoverage(profile) {
    const targetSecurity = ((profile || {}).aimed_target || {}).security || {};
    const activeKeys = Object.entries(targetSecurity)
        .filter(([, value]) => value === true)
        .map(([key]) => key);

    if (!activeKeys.length) {
        return ((profile || {}).aimed_target || {}).label ? 100 : null;
    }

    const unlockKeys = new Set();
    ((profile || {}).apps || []).forEach(app => {
        extractToolbarUnlockKeys(app).forEach(key => unlockKeys.add(key));
    });

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

function hasToolbarAimedTarget(aimedTarget) {
    const target = aimedTarget || {};
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
    if (backendProgress !== null) return backendProgress;

    const security = target.security && typeof target.security === "object" ? target.security : {};
    const keys = TARGET_FEEDBACK_SECURITY_KEYS.filter(key => typeof security[key] === "boolean");
    if (!keys.length) return 0;

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

function renderToolbarStatus() {
    const strip = document.getElementById('system-status-strip');
    if (!strip) return;

    const profile = toolbarProfile || {};
    const aimedTarget = profile.aimed_target || {};
    const hasTarget = hasToolbarAimedTarget(aimedTarget);
    const targetLabel = aimedTarget.label || aimedTarget.name || "brak";
    const arsenalCoverage = calculateToolbarArsenalCoverage(profile);
    const arsenalLabel = arsenalCoverage === null ? "--" : `${arsenalCoverage}%`;
    const targetFeedback = hasTarget ? resolveTargetBarFeedback(aimedTarget) : resolveTargetBarFeedback(null);
    const targetMarkup = hasTarget ? (() => {
        const targetClasses = [
            "system-status-target",
            "is-aimed",
            targetFeedback ? "has-target-feedback" : "",
            targetFeedback?.changed ? "is-feedback-change" : "",
            targetFeedback?.targetChanged ? "is-target-change" : ""
        ].filter(Boolean).join(" ");
        const targetProgressStyle = targetFeedback ? ` style="--target-disarm-progress: ${targetFeedback.progress}%;"` : "";
        return `<span class="${targetClasses}" title="Cel na celowniku: ${escapeHTML(String(targetLabel))}"${targetProgressStyle}><b>CEL</b><i class="target-status-body"><em>${escapeHTML(String(targetLabel))}</em>${renderTargetBarFeedback(targetFeedback)}</i></span>`;
    })() : '<span class="system-status-target"><b>CEL</b></span>';
    strip.innerHTML = `
        ${targetMarkup}
        <span><b>ARS</b> ${arsenalLabel}</span>
        <span><b>HC</b> ${Number(profile.hackcoins || 0)}</span>
        <span><b>LVL</b> ${Number(profile.level || 1)}</span>
        <span><b>RSP</b> ${Number(profile.respect || 0)}</span>
    `;
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
        window.location.href = '/logout';
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

    for (const [id, win] of runningWindows.entries()) {
        if (!win.isConnected) runningWindows.delete(id);
    }

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
        ghost_lab: createGhostLabHub,
        dev_bug_reporter: createDevBugReporterApp
    };
    if (!launcher || typeof launcherMap[launcher] !== 'function') {
        return false;
    }
    launcherMap[launcher]();
    return true;
}

function launchApplicationEffect(appData) {
    if (runSystemLauncherApp(appData)) return;
    const id = appData.id;
    const levels = appData.levels;
    const type = appData.interface;
    if (type === "window") app_window(id, levels);
    else if (type === "progressbar_random") app_progressbar_random(id, levels);
    else if (type === "terminal") app_terminal(id, levels);
    else if (type === "button_choices") app_button_choices(id, levels);
    else if (type === "system_launcher") console.warn(`Brak system_launcher dla: ${appData.name || id}`);
    else console.warn(`Nieznany interface: ${type}`);
}

function scheduleOperationalAppAutoClose(appWindow) {
    if (!appWindow || !appWindow.isConnected || appWindow.dataset.autoCloseScheduled === "1") return;
    appWindow.dataset.autoCloseScheduled = "1";

    const content = appWindow.querySelector('.app-content');
    if (content && !content.querySelector('.app-auto-close-notice')) {
        const notice = document.createElement('div');
        notice.className = 'app-auto-close-notice';
        notice.textContent = 'Okno zamknie sie automatycznie za 30 sekund.';
        content.appendChild(notice);
    }

    window.setTimeout(() => {
        if (!appWindow.isConnected) return;
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
            const action = () => launchApplicationEffect(app);
            icons.push({
                icon: app.icon || '\u2753',
                label: name,
                action
            });

        } catch (err) {
            console.error(`Błąd przy budowaniu ikony ${name}:`, err);
        }
    }

    return icons;
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

            if (data.terminalTeleport) {
                await handleTerminalTeleport(content, data.terminalTeleport);
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
                    window.location.href = '/logout';
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
                if (!runSystemLauncherApp(app)) {
                if (type === "window") app_window(id, levels);
                if (type === "progressbar_random") app_progressbar_random(id, levels);
                if (type === "terminal") app_terminal(id, levels);
                if (type === "button_choices") app_button_choices(id, levels);
                }
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
        return;
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
        return;
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
        return;
    }

    appendSystemTerminalOutput(content, escapeHTML(data.message || `Teleport wykonany: ${label}.`));
    openSystemAppFromTerminal("map");
    notifyOpenMapsBlacknetFocus({
        mode: "teleport",
        label,
        lat: Number(data?.curently_possition?.lat ?? lat),
        lng: Number(data?.curently_possition?.lng ?? lng),
        source: "terminal"
    });
}

function attachSystemTerminalInputHandler(input, content) {
    const form = input.closest('.system-terminal-composer');
    if (!form || form.dataset.systemTerminalBound === "1") return;
    form.dataset.systemTerminalBound = "1";

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const value = input.value.trim();
        if (!value) return;

        appendSystemTerminalCommand(content, value);
        input.value = '';
        input.disabled = true;
        const stopLoader = appendSystemTerminalLoader(content);

        try {
            if (content.pendingConfirm) {
                const answer = value.toLowerCase();
                const pending = content.pendingConfirm;

                if (!["y", "yes", "n", "no"].includes(answer)) {
                    appendSystemTerminalOutput(content, "Wpisz Y albo N.");
                    return;
                }

                content.pendingConfirm = null;

                if (answer === "n" || answer === "no") {
                    appendSystemTerminalOutput(content, "Anulowano.");
                    return;
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
                    }
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
                return;
            }

            if (data.confirm) {
                content.pendingConfirm = data.confirm;
                appendSystemTerminalOutput(content, escapeHTML(data.confirm.prompt));
                return;
            }

            if (data.response) {
                appendSystemTerminalOutput(content, data.response.replace(/\n/g, "<br>"));
            }

            if (data.terminalTeleport) {
                stopLoader();
                await handleTerminalTeleport(content, data.terminalTeleport);
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
                    window.location.href = '/logout';
                }, 350);
                return;
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

                if (!runSystemLauncherApp(app)) {
                    if (type === "window") app_window(id, levels);
                    if (type === "progressbar_random") app_progressbar_random(id, levels);
                    if (type === "terminal") app_terminal(id, levels);
                    if (type === "button_choices") app_button_choices(id, levels);
                }
            }
        } catch (err) {
            appendSystemTerminalOutput(content, '<span style="color:red;">Blad komunikacji z serwerem</span>');
        } finally {
            stopLoader();
            input.disabled = false;
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
            'Content-Type': 'application/json'
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
    const safeLevels = Array.isArray(levels) ? levels : [];
    const level = safeLevels[0] || {};
    const items = Array.isArray(level.list) && level.list.length
        ? level.list
        : [`Aplikacja ${id} uruchomiona.`];
    const windowButtons = Array.isArray(level.buttons) ? level.buttons : [];
    const app = document.createElement('div');
    app.className = 'app-window';
    const position = findAvailablePosition();
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;

    app.innerHTML = `
        <div class="title-bar">${escapeHTML(id)} <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content">
            <h3>${escapeHTML(level.title || 'Aplikacja')}</h3>
            <ul>${items.map(item => `<li>${escapeHTML(String(item || ''))}</li>`).join('')}</ul>
            <div class="button-row">
                ${windowButtons.map((b, i) => `
                    <button data-action="${escapeHTML(b.action || '')}" data-label="${escapeHTML(b.label || '')}">
                        ${escapeHTML(b.label || '')}
                    </button>
                `).join('')}
            </div>
            <div class="choice-result" style="margin-top:10px; font-weight:bold;"></div>
        </div>
    `;

    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());

    const resultBox = app.querySelector('.choice-result');
    const buttons = app.querySelectorAll('.button-row button');

    buttons.forEach(btn => {
        btn.addEventListener('click', async () => {
            if (btn.disabled || btn.classList.contains("is-loading")) return;
            const action = btn.dataset.action;
            const label = btn.dataset.label;
            setAppButtonGroupPending(buttons, btn, true);
            try {
                const response = await sendGonnaWinRequest(id, action);
                const success = response.success === true;

                addSystemMessage('info', '\u25B6 Akcja', `Akcja: ${label} | Wynik: ${success ? "\u2714" : "\u2716"}`);
                resultBox.textContent = success ? "\u2714 Sukces!" : "\u2716 Niepowodzenie.";
                resultBox.style.color = success ? "#0f0" : "#f33";
                if (success) {
                    scheduleOperationalAppAutoClose(app);
                }
            } finally {
                setAppButtonGroupPending(buttons, btn, false);
            }
        });
    });
}

async function app_progressbar_random(id, levels) {
    const safeLevels = Array.isArray(levels) ? levels : [];
    const level = safeLevels[0] || {};
    const steps = Array.isArray(level.steps) && level.steps.length
        ? level.steps
        : ["Inicjalizacja modułu...", "Wykonanie operacji...", "Finalizacja..."];
    const app = document.createElement('div');
    app.className = 'app-window';
    const position = findAvailablePosition();
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;

    app.innerHTML = `
        <div class="title-bar">${escapeHTML(level.title || id)} <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content">
            <div class="progress-log" style="font-family: monospace; font-size: 13px; margin-bottom: 10px;"></div>
            <div class="progress-bar" style="position: relative; height: 20px; background: #333;">
                <div class="progress-fill" style="background: #0f0; height: 100%; width: 0%; transition: width 0.2s;"></div>
            </div>
            <div class="result-msg" style="margin-top: 10px; font-weight: bold;"></div>
        </div>
    `;
    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());

    const fill = app.querySelector('.progress-fill');
    const log = app.querySelector('.progress-log');
    const result = app.querySelector('.result-msg');

    // Animowane kroki
    let stepIndex = 0;
    const totalSteps = steps.length;
    const progressPerStep = 100 / totalSteps;

    function runNextStep() {
        if (stepIndex >= totalSteps) {
            // <- tutaj korzystamy z odpowiedzi
            notifyGonnaWin(id).then(success => {
                result.textContent = success ? (level.result_success || "Operacja zako\u0144czona.") : (level.result_failure || "Operacja nie powiod\u0142a si\u0119.");
                result.style.color = success ? "#0f0" : "#f33";
                if (success) {
                    scheduleOperationalAppAutoClose(app);
                }
            }).catch(() => {
                result.textContent = "\u2716 B\u0142\u0105d po\u0142\u0105czenia z serwerem.";
                result.style.color = "#f33";
            });
            return;
        }

        const msg = steps[stepIndex];
        log.innerHTML += `<div>\u23F1 ${escapeHTML(String(msg || ''))}</div>`;
        fill.style.width = `${(stepIndex + 1) * progressPerStep}%`;

        stepIndex++;
        setTimeout(runNextStep, 1000 + Math.random() * 1000);
    }


    runNextStep();
}

async function notifyGonnaWin(appId) {
    try {
        const response = await fetch('/gonna-win', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ app_id: appId })
        });
        const data = await response.json();
        if (data.player_hack_access) {
            refreshPlayerHackAccess(data.player_hack_access);
        }
        if (data.success && data.captured_target) {
            notifyOpenMapsTargetHacked(data.captured_target);
            refreshToolbarProfile();
        }
        return data.success === true;
    } catch (err) {
        console.error(`❌ Błąd połączenia z /gonna-win dla ${appId}`, err);
        return false; // default przy błędzie
    }
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

async function sendGonnaWinRequest(appId, choiceId = null) {
    try {
        const response = await fetch('/gonna-win', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                app_id: appId,
                choice_id: choiceId
            })
        });
        const data = await response.json();
        if (data.player_hack_access) {
            refreshPlayerHackAccess(data.player_hack_access);
        }
        if (data.success && data.captured_target) {
            notifyOpenMapsTargetHacked(data.captured_target);
            refreshToolbarProfile();
        }
        return data;
    } catch (error) {
        console.error("Błąd komunikacji z backendem:", error);
        return { success: false };
    }
}

function app_terminal(id, levels) {
    notifyGonnaWin(id);
    const safeLevels = Array.isArray(levels) ? levels : [];
    const level = safeLevels[0] || {};
    const logs = Array.isArray(level.logs) ? level.logs : [];
    const commands = level.command ? [level.command, ...logs] : (logs.length ? logs : [`./${id}.sh`, "Raport zapisany."]);

    const app = document.createElement('div');
    app.className = 'app-window';
    const position = findAvailablePosition();
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.innerHTML = `
        <div class="title-bar">${escapeHTML(id)} <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content app-terminal-content">
            <div class="terminal-log app-terminal-log"></div>
        </div>
    `;
    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());

    const log = app.querySelector('.terminal-log');
    let commandIndex = 0;

    function scrollLogToBottom() {
        const content = app.querySelector('.app-terminal-content');
        if (content) content.scrollTop = content.scrollHeight;
    }

    function showTerminalProcessing(callback) {
        const wait = document.createElement('div');
        wait.className = 'app-terminal-wait';
        wait.innerHTML = `
            <span class="app-terminal-spinner" aria-hidden="true"></span>
            <span>przetwarzanie...</span>
        `;
        log.appendChild(wait);
        scrollLogToBottom();

        const delay = 650 + Math.floor(Math.random() * 1150);
        window.setTimeout(() => {
            wait.remove();
            callback();
        }, delay);
    }

    function simulateTyping(command, callback) {
        const safeCommand = String(command || '');
        const hasNext = commandIndex < commands.length;
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
                    if (hasNext) {
                        showTerminalProcessing(callback);
                    } else {
                        callback();
                    }
                    scrollLogToBottom();
                }, 260 + Math.floor(Math.random() * 320));
            }
        }, 34 + Math.floor(Math.random() * 28));
    }

    function runNextCommand() {
        if (commandIndex >= commands.length) {
            scheduleOperationalAppAutoClose(app);
            return;
        }
        const current = commands[commandIndex];
        commandIndex++;
        simulateTyping(current, runNextCommand);
    }

    runNextCommand();
}

function app_button_choices(id, levels) {
    const safeLevels = Array.isArray(levels) ? levels : [];
    const lvl = safeLevels[0] || {};
    const options = Array.isArray(lvl.options) && lvl.options.length
        ? lvl.options.map((option, index) => normalizeButtonChoiceOption(option, index))
        : [{ id: 0, label: "Wykonaj", effect: {} }];
    const app = document.createElement('div');
    app.className = 'app-window';
    const position = findAvailablePosition();
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;

    app.innerHTML = `
        <div class="title-bar">${escapeHTML(id)} <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span></div>
        <div class="app-content">
            <h3>${escapeHTML(lvl.title || 'Wybierz opcj\u0119')}</h3>
            <p>${escapeHTML(lvl.text || '')}</p>
            <div class="button-row">
                ${options.map((opt, i) => `
                    <button data-opt-id="${escapeHTML(opt.id || i)}" class="choice-btn">
                        ${escapeHTML(opt.label || '')}
                    </button>
                `).join('')}
            </div>
            <div class="choice-result" style="margin-top:10px; font-weight:bold;"></div>
        </div>
    `;

    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());

    const buttons = app.querySelectorAll('.choice-btn');
    const resultBox = app.querySelector('.choice-result');

    buttons.forEach(btn => {
        btn.addEventListener('click', async () => {
            if (btn.disabled || btn.classList.contains("is-loading")) return;
            const optId = btn.dataset.optId;
            const choiceLabel = btn.textContent.trim();
            setAppButtonGroupPending(buttons, btn, true);
            try {
                const response = await sendGonnaWinRequest(id, optId);
                const success = response.success === true;

                addSystemMessage('info', '\u2699 Efekt', `Wybrano: ${choiceLabel} | Wynik: ${success ? "\u2714 SUKCES" : "\u2716 PORA\u017bKA"}`);
                resultBox.textContent = success ? "\u2714 Uda\u0142o si\u0119!" : "\u2716 Niestety nie tym razem.";
                resultBox.style.color = success ? "#0f0" : "#f33";
                if (success) {
                    scheduleOperationalAppAutoClose(app);
                }
            } finally {
                setAppButtonGroupPending(buttons, btn, false);
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
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `1200px`;
    term.style.height = `500px`;

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
                frame.src = "/map";
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
    term.style.display = 'flex';
    term.style.flexDirection = 'column';
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `920px`;
    term.style.height = `560px`;

    const terminalId = `browser-${Date.now()}`;
    const browserUiIcons = {
        close: '\u2716',
        back: '\u2190',
        forward: '\u2192',
        favorite: '\u2B50',
        app: '\u25A3'
    };

    term.innerHTML = `
    <div class="title-bar">
        WebDragons
        <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
    </div>
    <div class="browser-nav">
        <button class="nav-btn">${browserUiIcons.back}</button>
        <button class="nav-btn">${browserUiIcons.forward}</button>
        <input type="text" value="xhttp://webdragons.hck" readonly class="url-bar">
        <button class="fav-btn" title="Dodaj do ulubionych">${browserUiIcons.favorite}</button>
    </div>
    <div class="googolplex-shell">
        <div class="googolplex-header">
            <h1 id="${terminalId}-title">Googolplex</h1>
            <div id="${terminalId}-wallet" class="googolplex-wallet">HackCoiny: ...</div>
        </div>
        <div class="browser-tabs">
            <button type="button" class="browser-tab is-active" data-browser-tab="googleplex">Googleplex</button>
            <button type="button" class="browser-tab" data-browser-tab="exchange">Ghost Exchange</button>
            <button type="button" class="browser-tab" data-browser-tab="blacknet">BlackNet</button>
        </div>
        <input type="text" id="${terminalId}-search" placeholder="Wyszukaj aplikacj\u0119..." class="googolplex-search">
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
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    // Obsługa wyszukiwania
    const search = term.querySelector(`#${terminalId}-search`);
    const results = term.querySelector(`#${terminalId}-results`);
    const wallet = term.querySelector(`#${terminalId}-wallet`);
    const browserHeader = term.querySelector('.googolplex-header');
    const browserTabs = term.querySelector('.browser-tabs');
    let catalog = [];
    let exchangeFiles = [];
    let exchangeDashboard = { summary: {}, sectors: [], recent_transactions: [], history_7d: [] };
    let walletBalance = 0;
    let activeBrowserTab = "googleplex";
    let activeBlacknetSignalId = "";
    let blacknetPointerStartX = null;
    let pendingGoogleplexSearch = "";
    const renderBrowserWallet = () => {
        wallet.textContent = activeBrowserTab === "blacknet"
            ? "SIGNAL BUS v0"
            : `HackCoiny: ${Number.isFinite(walletBalance) ? walletBalance : "..."}`;
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
        const shell = term.querySelector('.googolplex-shell');
        const measuredWidth = (shell?.getBoundingClientRect().width)
            || term.getBoundingClientRect().width
            || term.offsetWidth
            || window.innerWidth;
        term.classList.toggle('browser-narrow', measuredWidth < 720);
    };

    updateBrowserNarrowMode();
    if (window.ResizeObserver) {
        const browserNarrowObserver = new ResizeObserver(updateBrowserNarrowMode);
        browserNarrowObserver.observe(term);
        const shell = term.querySelector('.googolplex-shell');
        if (shell) browserNarrowObserver.observe(shell);
    }
    window.addEventListener('resize', updateBrowserNarrowMode);

    const googleplexList = (value) => Array.isArray(value)
        ? value.map(item => String(item || '').trim()).filter(Boolean)
        : [];
    const googleplexListText = (value) => {
        const list = googleplexList(value);
        return list.length ? list.join(', ') : '-';
    };
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
        if (query) {
            search.value = query;
        }
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
            search.value = sector;
        } else {
            search.value = "";
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
                label
            };
            setTimeout(() => notifyOpenMapsBlacknetFocus(window.__blacknetMapFocus), 50);
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
                await loadBlacknetSignals({ append: true, force: true });
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

    const renderCatalog = () => {
        if (activeBrowserTab !== "googleplex") return;
        updateBrowserNarrowMode();
        const rawQuery = search.value.trim();
        const query = rawQuery.toLowerCase();
        const showAll = query === "/all";
        if (!query) {
            results.innerHTML = "";
            updateBrowserNarrowMode();
            return;
        }

        const matches = showAll
            ? catalog.filter(item => item && typeof item === "object")
            : catalog.filter(item => googleplexSearchText(item).includes(query));

        results.innerHTML = '';
        if (matches.length === 0) {
            results.innerHTML = '<div class="googolplex-empty">Brak aplikacji do pokazania.</div>';
            updateBrowserNarrowMode();
            return;
        }

        matches.forEach(item => {
            const price = Number(item.price || 0);
            const installed = item.installed === true;
            const isProduct = !!(item.product_type || (Array.isArray(item.effects) && item.effects.length));
            const travelEffect = Array.isArray(item.effects)
                ? item.effects.find(effect => effect && typeof effect === "object" && effect.type === "travel_city")
                : null;
            const isTravelTicket = item.product_type === "travel_ticket" || Boolean(travelEffect);
            const travelDestination = String(travelEffect?.city || item.travel_city || "").trim();
            const canAfford = walletBalance >= price;
            const installBlockedReason = item.install_blocked_reason || "";
            const canInstall = !installed && canAfford && !installBlockedReason;
            const buttonLabel = installed ? (isProduct ? "Kupione" : "Zainstalowane") : (canAfford ? (isProduct ? "Kup" : "Zainstaluj") : "Brak \u015brodk\u00f3w");
            const hasInstallRequirements = item.type === "pro-system-tool" || item.category === "pro-system-tools" || item.category === "creators" || item.required_level || item.required_respect;
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
            const proMeta = hasInstallRequirements ? `
                <div class="googolplex-card-requirements">
                    <span>LVL ${Number(item.required_level || 1)}</span>
                    <span>Respect ${Number(item.required_respect || 0)}</span>
                    <span>Risk ${riskStars}</span>
                </div>
            ` : "";
            const contractMeta = `
                <div class="googolplex-contract">
                    <span>Poziom: <b>${escapeHTML(item.app_level || 'Basic')}</b></span>
                    <span>Rodzina: <b>${escapeHTML(item.tool_family || item.type || 'tool')}</b></span>
                    <span>Tryb: <b>${escapeHTML(item.tool_mode || item.scanner_mode || 'desktop')}</b></span>
                    ${isProduct ? `<span>Produkt: <b>${escapeHTML(item.product_type || '-')}</b></span>` : ''}
                    ${isProduct ? `<span>Kategoria: <b>${escapeHTML(item.category || '-')}</b></span>` : ''}
                    ${isProduct ? `<span>Efekt: <b>${escapeHTML(effectsText || '-')}</b></span>` : ''}
                    <span>Tier: <b>${escapeHTML(item.balance_tier || item.app_level || 'Basic')}</b></span>
                    <span>Map: <b>${escapeHTML(googleplexListText(item.map_actions))}</b></span>
                    <span>Ops: <b>${escapeHTML(googleplexListText(item.operation_types))}</b></span>
                    <span>Data: <b>${escapeHTML(googleplexListText(item.resource_types))}</b></span>
                    <span>Waga: <b>${escapeHTML(formatStorageSize(fileSize))}</b></span>
                    <span>Instalacja: <b>${escapeHTML(formatStorageSize(diskUsage))}</b></span>
                    <span>Jako\u015b\u0107: <b>${qualityScore}/100</b></span>
                    <span>Niezawodno\u015b\u0107: <b>${reliability}/100</b></span>
                    <span>Moc tw\u00f3rcy: <b>${creatorPower}/100</b></span>
                    <span>Moc: <b>${powerScore}/100</b></span>
                    <span>Cena sugerowana: <b>${priceHint ? `${priceHint} HC` : '-'}</b></span>
                </div>
            `;
            const blockedHint = installBlockedReason ? `
                <div class="googolplex-card-hint">${escapeHTML(installBlockedReason)}</div>
            ` : "";
            const card = document.createElement('article');
            card.className = 'googolplex-card';
            card.innerHTML = `
                <div class="googolplex-card-title">
                    <span class="googolplex-card-icon">${item.icon || browserUiIcons.app}</span>
                    <span>${escapeHTML(item.name || 'Aplikacja')}</span>
                </div>
                <p>${escapeHTML(item.description || 'Brak opisu.')}</p>
                ${proMeta}
                ${contractMeta}
                ${blockedHint}
                <div class="googolplex-card-meta">
                    <span>${escapeHTML(item.type || 'tool')}</span>
                    <span>${Number(item.downloads || 0)} pobra\u0144</span>
                </div>
                <div class="googolplex-card-footer">
                    <strong>${price} HC</strong>
                    <button type="button" ${canInstall ? "" : "disabled"}>${buttonLabel}</button>
                </div>
            `;
            card.querySelector('button').addEventListener('click', async () => {
                if (!canInstall) return;
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
                }
                showInstallAppProgress(item, async () => {
                    await loadCatalog();
                });
            });
            results.appendChild(card);
        });
        updateBrowserNarrowMode();
    };

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
        const [profileRes, resourcesRes] = await Promise.all([
            fetch('/api/profile'),
            fetch('/resources.json')
        ]);
        const profile = await profileRes.json();
        catalog = await resourcesRes.json();
        walletBalance = Number(profile.hackcoins || 0);
        renderBrowserWallet();
        if (pendingGoogleplexSearch) {
            search.value = pendingGoogleplexSearch;
        }
        renderCatalog();
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
        activeBrowserTab = tabName;
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
            title.textContent = "Googolplex";
            renderBrowserWallet();
            search.placeholder = "Wyszukaj aplikacje...";
            renderCatalog();
        }
    }

    term.querySelectorAll('.browser-tab').forEach(button => {
        button.addEventListener('click', () => switchBrowserTab(button.dataset.browserTab || "googleplex"));
    });
    updateBrowserChrome();
    search.addEventListener('input', () => {
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
    loadCatalog().catch(() => {
        results.innerHTML = '<div class="googolplex-empty">Nie uda\u0142o si\u0119 pobra\u0107 katalogu.</div>';
    });
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
        renderWalletHistory(container, data.transactions || []);
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
        list.innerHTML = `<div class="wallet-empty">Brak przelewow.</div>`;
        return;
    }
    list.innerHTML = transactions.map(tx => {
        const outgoing = tx.type === "outgoing";
        const sign = outgoing ? "-" : "+";
        const typeLabel = outgoing ? "wyslano" : "odebrano";
        return `
            <div class="wallet-transaction ${outgoing ? 'is-outgoing' : 'is-incoming'}">
                <div>
                    <strong>${escapeHTML(typeLabel)} ${sign}${Number(tx.amount || 0)} HC</strong>
                    <span>${escapeHTML(String(tx.peer || 'unknown'))}</span>
                </div>
                <small>${escapeHTML(String(tx.created_at || ''))}</small>
                ${tx.note ? `<em>${escapeHTML(String(tx.note))}</em>` : ''}
            </div>
        `;
    }).join('');
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
    try {
        const res = await fetch('/api/wallet/transfer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ to, amount, note })
        });
        const data = await res.json();
        if (!res.ok || data.error) {
            setWalletMessage(container, "error", data.error || "Przelew odrzucony.");
            return;
        }
        container.querySelector('[data-wallet-amount]').value = "";
        container.querySelector('[data-wallet-note]').value = "";
        container.querySelector('[data-wallet-balance]').textContent = `Saldo: ${Number(data.balance || 0)} ${data.currency || 'HC'}`;
        renderWalletHistory(container, data.transactions || (data.transaction ? [data.transaction] : []));
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

function showInstallAppProgress(app, onInstalled = null) {
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

    function runNextStep() {
        if (stepIndex >= steps.length) {
            // Wysyłka do backendu na końcu
            fetch('/install-app', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app_id: app.id })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
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
                    }, 4000);
                } else {
                    result.innerHTML = `<span style="color:#f33;">\u2716 B\u0142\u0105d instalacji: ${escapeHTML(data.message || '')}</span>`;
                }
            })
            .catch(err => {
                result.innerHTML = `<span style="color:#f33;">\u2716 B\u0142\u0105d po\u0142\u0105czenia z serwerem.</span>`;
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
    const currentWallpaper = desktopSettings.wallpaper || "";

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

    term.querySelector('[data-settings-radio-autoplay]')?.addEventListener('change', event => {
        setGhostRadioAutoplayEnabled(event.target.checked);
        setStatus(event.target.checked ? "Autostart radia wlaczony." : "Autostart radia wylaczony.", "success");
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
    try {
        const res = await fetch('/api/profile');
        if (res.status === 401) {
            desktopSessionActive = false;
            return null;
        }
        if (!res.ok) throw new Error("Nieprawidłowy response");
        const data = await res.json();
        return data;
    } catch (err) {
        console.error("❌ Błąd pobierania profilu użytkownika:", err);
        return null;
    }
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

async function applyDelta(event) {
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
        updateCybernerDeltaViews(event.payload || {});
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

async function recoverDeltaScopes(recoveryScopes = [], currentVersion = null) {
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
    await Promise.all(recoveryTasks);
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
        const res = await fetch(`/api/state/changes?${params.toString()}`);
        if (res.status === 401) {
            desktopSessionActive = false;
            return;
        }
        if (!res.ok) return;
        const data = await res.json();
        if (data.recovery_required) {
            await recoverDeltaScopes(data.recovery_scopes || [], data.current_version);
            return;
        }
        const changes = Array.isArray(data.changes) ? data.changes : [];
        for (const change of changes) {
            await applyDelta(change);
            if (Number.isFinite(Number(change.version))) {
                stateDeltaVersion = Math.max(stateDeltaVersion, Number(change.version));
            }
        }
        if (Number.isFinite(Number(data.current_version))) {
            stateDeltaVersion = Math.max(stateDeltaVersion, Number(data.current_version));
        }
    } catch (err) {
        console.warn("Delta feed poll failed", err);
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
                <label class="appforge-check">
                    <input type="checkbox" value="${escapeHTML(key)}">
                    <span>${escapeHTML(key)}</span>
                </label>
            `).join("")}
        </div>
    `;
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
        description: "Scanner, Exploit i Sniffer opisuj\u0105 intencj\u0119 gameplayow\u0105, a nie realn\u0105 instrukcj\u0119 dzia\u0142ania.",
        educational_note: "Administratorzy i zespoly bezpieczenstwa uzywaja podobnych klas rozwiazan do rozpoznania, kontroli i obserwacji systemow.",
        gameplay_hint: "Wybrana rodzina filtruje akcje, operacje i zasoby w kolejnych krokach."
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
    ["tracker", "Tracker"],
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
        scan_ports: "Rozpoznaj uslugi celu",
        exploit: "Wplyn na zabezpieczenia",
        sniff: "Obserwuj sygnaly",
        trace: "Sledz cel",
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

const CREATOR_TARGET_FILTERS = {
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
        label: "Scanner / Recon",
        boxTitle: "Gdzie dzia\u0142a rozpoznanie?",
        defaultType: "scanner",
        safetyText: "Narz\u0119dzia rozpoznania s\u0142u\u017c\u0105 do poznania powierzchni celu w \u015bwiecie gry. Wizard buduje \u015bwiadomo\u015b\u0107, nie realne instrukcje.",
        desktopMapNote: "Scanner desktopowy mo\u017ce nie mie\u0107 akcji mapy. Dzia\u0142a na aktualny aimed_target.",
        mapNote: "Wybierz tylko te akcje mapy, kt\u00f3re aplikacja faktycznie obs\u0142u\u017cy.",
        modes: CREATOR_SCANNER_MODE_PRESETS
    },
    exploit: {
        label: "Exploit",
        boxTitle: "Gdzie dzia\u0142a exploit?",
        defaultType: "exploit",
        safetyText: "Exploit w CHAOS oznacza symulowany wp\u0142yw na s\u0142abo\u015b\u0107 systemu w \u015bwiecie gry. Opisuj efekt gameplayowy, nie technik\u0119.",
        desktopMapNote: "Exploit desktopowy mo\u017ce nie mie\u0107 akcji mapy. Dzia\u0142a na aktualny aimed_target.",
        mapNote: "Wybierz akcje mapy tylko wtedy, gdy narz\u0119dzie ma by\u0107 widoczne w menu mapy.",
        modes: CREATOR_EXPLOIT_MODE_PRESETS
    },
    sniffer: {
        label: "Sniffer",
        boxTitle: "Gdzie dzia\u0142a sniffer?",
        defaultType: "sniffer",
        safetyText: "Sniffer w CHAOS oznacza symulowan\u0105 obserwacj\u0119 sygna\u0142\u00f3w lub danych w ramach operacji gry.",
        desktopMapNote: "Sniffer desktopowy mo\u017ce nie mie\u0107 akcji mapy. Dzia\u0142a na aktualny aimed_target.",
        mapNote: "Wybierz akcje mapy tylko wtedy, gdy sniffer ma by\u0107 uruchamiany z mapy.",
        modes: CREATOR_SNIFFER_MODE_PRESETS
    }
};

function creatorOptionCheckboxGroup(options, fieldName) {
    const labels = CREATOR_OPTION_LABELS[fieldName] || {};
    return `
        <div class="appforge-check-grid creator-contract-grid" data-appforge-field="${fieldName}">
            ${options.map(option => `
                <label class="appforge-check" data-creator-option="${escapeHTML(option)}">
                    <input type="checkbox" value="${escapeHTML(option)}">
                    <span>${escapeHTML(labels[option] || option)}</span>
                </label>
            `).join("")}
        </div>
    `;
}

function creatorWizardNavHtml() {
    return `
        <div class="creator-wizard-nav" role="tablist">
            ${CREATOR_WIZARD_STEPS.map((label, index) => `
                <button type="button" class="creator-wizard-tab${index === 0 ? " active" : ""}" data-creator-step="${index}">
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

function wireCreatorWizard(term) {
    const form = term.querySelector('.appforge-form');
    if (!form) return;
    const tabs = Array.from(form.querySelectorAll('[data-creator-step]'));
    const panels = Array.from(form.querySelectorAll('[data-creator-panel]'));
    panels.forEach(panel => {
        const index = Number(panel.dataset.creatorPanel);
        if (!panel.querySelector('.creator-step-narrative')) {
            panel.insertAdjacentHTML('afterbegin', creatorStepNarrativeHtml(index));
        }
    });
    polishCreatorWizardLabels(term);
    const setStep = (step) => {
        const nextStep = Math.max(0, Math.min(panels.length - 1, Number(step) || 0));
        tabs.forEach(tab => tab.classList.toggle('active', Number(tab.dataset.creatorStep) === nextStep));
        panels.forEach(panel => {
            panel.hidden = Number(panel.dataset.creatorPanel) !== nextStep;
        });
    };
    tabs.forEach(tab => tab.addEventListener('click', () => setStep(tab.dataset.creatorStep)));
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
        tool_family: form?.querySelector('[name="tool_family"]')?.value || 'custom',
        tool_mode: form?.querySelector('[name="tool_mode"]')?.value || '',
        interface: form?.querySelector('input[name="interface"]')?.value || '',
        type: form?.querySelector('[name="type"]')?.value || '',
        map_actions: collect("map_actions"),
        target_types: collect("target_types"),
        operation_types: collect("operation_types"),
        resource_types: collect("resource_types"),
        price: Number(form?.querySelector('[name="price"]')?.value || 0),
        file_size: "runtime default",
        disk_usage: "runtime default",
        quality_score: "creator profile",
        reliability: "creator profile",
        power_score: "runtime balance preview",
        price_hint: "minimum runtime hint"
    };
    preview.textContent = JSON.stringify(payload, null, 2);
}

function setCreatorCheckboxFilter(term, fieldName, allowedOptions) {
    const allowed = new Set(allowedOptions || []);
    const shouldFilter = Array.isArray(allowedOptions);
    term.querySelectorAll(`[data-appforge-field="${fieldName}"] [data-creator-option]`).forEach(label => {
        const option = label.dataset.creatorOption || "";
        const visible = !shouldFilter || allowed.has(option);
        label.hidden = !visible;
        const input = label.querySelector('input');
        if (input && !visible) input.checked = false;
    });
}

function selectedCreatorOptions(term, fieldName) {
    return Array.from(term.querySelectorAll(`[data-appforge-field="${fieldName}"] input:checked`))
        .map(input => input.value)
        .filter(Boolean);
}

function intersectCreatorOptions(baseOptions, targetOptions) {
    if (!Array.isArray(baseOptions)) return targetOptions;
    if (!Array.isArray(targetOptions) || targetOptions.length === 0) return baseOptions;
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
    if (!familyPreset) {
        ["map_actions", "operation_types", "resource_types", "target_types"].forEach(field => {
            setCreatorCheckboxFilter(term, field, null);
        });
        if (familyTitle) familyTitle.textContent = "Tryb narz\u0119dzia";
        if (familyNote) familyNote.textContent = "Wybierz \u015bcie\u017ck\u0119 kreatora, \u017ceby zaw\u0119zi\u0107 kontrakt do sensownych p\u00f3l.";
        if (familySafety) familySafety.textContent = "";
        if (mapNote) mapNote.textContent = "";
        updateCreatorContractPreview(term);
        return;
    }

    const preset = familyPreset.modes[mode] || familyPreset.modes.map;
    if (typeInput && (!typeInput.value || typeInput.value === "exploit" || typeInput.value === "custom" || typeInput.value === "scanner" || typeInput.value === "sniffer")) {
        typeInput.value = familyPreset.defaultType;
    }
    const targetMapActions = collectCreatorTargetFilters(selectedTargets, "map_actions");
    const targetOperations = collectCreatorTargetFilters(selectedTargets, "operation_types");
    const targetResources = collectCreatorTargetFilters(selectedTargets, "resource_types");
    setCreatorCheckboxFilter(term, "map_actions", intersectCreatorOptions(preset.map_actions, targetMapActions));
    setCreatorCheckboxFilter(term, "operation_types", intersectCreatorOptions(preset.operation_types, targetOperations));
    setCreatorCheckboxFilter(term, "resource_types", intersectCreatorOptions(preset.resource_types, targetResources));
    setCreatorCheckboxFilter(term, "target_types", preset.target_types);
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
    form.addEventListener('change', () => {
        applyCreatorScannerMode(term);
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
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="2" hidden>
                <h4>\u015arodowisko dzia\u0142ania</h4>
                <input type="hidden" name="interface" value="${escapeHTML(interfaceName)}">
                <div class="creator-readonly-contract">
                    <span>Interface</span>
                    <b>${escapeHTML(interfaceName)}</b>
                </div>
                <div class="appforge-fieldset"><h4>target_types</h4>${creatorOptionCheckboxGroup(CREATOR_TARGET_TYPE_OPTIONS, "target_types")}</div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="3" hidden>
                <h4>Akcje mapy / desktopu</h4>
                <p class="creator-step-note" data-creator-map-note>Wybierz akcje mapy tylko wtedy, gdy narz\u0119dzie ma by\u0107 uruchamiane z menu mapy.</p>
                <div class="appforge-fieldset"><h4>map_actions</h4>${creatorOptionCheckboxGroup(CREATOR_MAP_ACTION_OPTIONS, "map_actions")}</div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="4" hidden>
                <h4>Operacje</h4>
                <div class="appforge-fieldset"><h4>operation_types</h4>${creatorOptionCheckboxGroup(CREATOR_OPERATION_OPTIONS, "operation_types")}</div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="5" hidden>
                <h4>Zasoby</h4>
                <div class="appforge-fieldset"><h4>resource_types</h4>${creatorOptionCheckboxGroup(CREATOR_RESOURCE_OPTIONS, "resource_types")}</div>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="6" hidden>
                <h4>Ryzyko i zabezpieczenia</h4>
                <div class="appforge-fieldset"><h4>interferes_with</h4>${creatorCheckboxGroup(keys, "interferes_with")}</div>
                <div class="appforge-fieldset"><h4>requires_off</h4>${creatorCheckboxGroup(keys, "requires_off")}</div>
                <div class="appforge-fieldset"><h4>disables</h4>${creatorCheckboxGroup(keys, "disables")}</div>
                <div class="appforge-fieldset"><h4>affects</h4>${creatorCheckboxGroup(keys, "affects")}</div>
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
                <pre class="creator-contract-preview" data-creator-contract-preview></pre>
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
    const start = typeof input.selectionStart === 'number' ? input.selectionStart : input.value.length;
    const end = typeof input.selectionEnd === 'number' ? input.selectionEnd : input.value.length;
    input.value = `${input.value.slice(0, start)}${icon}${input.value.slice(end)}`;
    const nextPosition = start + icon.length;
    input.focus();
    input.setSelectionRange(nextPosition, nextPosition);
    input.dispatchEvent(new Event('input', { bubbles: true }));
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
        iconPreview.textContent = iconInput.value.trim() || fallbackIcon;
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
    term.className = 'terminal';
    term.dataset.app = appName.toLowerCase();
    const position = findAvailablePosition(620, 660);
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `620px`;
    term.style.height = `680px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';
    term.innerHTML = `
        <div class="title-bar">
            ${appName}: ${interfaceName}
            <span class="close-btn" style="float:right; cursor:pointer;">\u2716</span>
        </div>
        <form class="appforge-form"></form>
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
        addSystemMessage("warning", "\u{1F6E0}\uFE0F Narz\u0119dzia", "Brak aktywnej akcji mapy.");
        return;
    }
    if (selection.in_flight) {
        return;
    }

    const app = selection.matching_apps.find(item => String(item.id || "") === String(appId || ""));
    if (!app) {
        addSystemMessage("warning", "\u{1F6E0}\uFE0F Narz\u0119dzia", "To narz\u0119dzie nie pasuje do aktywnej akcji.");
        return;
    }

    try {
        selection.in_flight = true;
        const flowId = getHackFlowId(selection);
        notifyOpenMapsHackActionStarted(flowId, {
            ...selection.pending_action,
            selected_app_id: app.id,
            selected_app_name: app.name
        });
        pauseOpenMapOptionalRefresh("hack_action_tool_use");
        updateMapToolPickerBusyState(true, app.id);
        const res = await fetch('/hack-action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...selection.pending_action,
                selected_app_id: app.id
            })
        });
        const data = await res.json();
        if (!res.ok || data.blocked) {
            addSystemMessage("warning", "\u{1F6E0}\uFE0F Narz\u0119dzia", data.status || "Nie uda\u0142o si\u0119 uruchomi\u0107 narz\u0119dzia.");
            selection.in_flight = false;
            updateMapToolPickerBusyState(false);
            return;
        }

        window.activeToolSelection = null;
        closeMapToolPicker(false);
        if (data.target) {
            setToolbarProfile({
                ...(toolbarProfile || {}),
                aimed_target: data.target
            });
        }
        addSystemMessage("success", "\u{1F6E0}\uFE0F Narz\u0119dzie", data.status || `Uruchomiono ${app.name || app.id}.`);
        if (typeof notifyOpenMapsOperationsChanged === "function") {
            await notifyOpenMapsOperationsChanged();
        }
    } catch (err) {
        console.error("Błąd wyboru narzędzia:", err);
        addSystemMessage("danger", "\u{1F6E0}\uFE0F Narz\u0119dzia", "B\u0142\u0105d po\u0142\u0105czenia podczas wyboru narz\u0119dzia.");
        if (selection) {
            selection.in_flight = false;
            updateMapToolPickerBusyState(false);
        }
    } finally {
        notifyOpenMapsHackActionStopped(getHackFlowId(selection));
        resumeOpenMapOptionalRefresh(1200);
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
    const title = window.activeToolSelection.map_action_id || window.activeToolSelection.canonical_action || "akcja";
    addSystemMessage("info", "\u{1F6E0}\uFE0F Wyb\u00f3r narz\u0119dzia", `Wybierz narz\u0119dzie dla: ${title}`);
    createMapToolPicker(window.activeToolSelection);
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
                <div class="mail-section-title">Kanały</div>
                <div id="${terminalId}-channels" class="mail-channel-list mail-conversation-list"></div>
                <div class="mail-section-title">Rozmowy</div>
                <form id="${terminalId}-contact-form" class="mail-contact-form mail-add-contact">
                    <input id="${terminalId}-contact-input" type="text" placeholder="Nick znajomego" autocomplete="off">
                    <button type="submit">Dodaj</button>
                </form>
                <div id="${terminalId}-contacts" class="mail-contact-list mail-conversation-list"></div>
                <div id="${terminalId}-pending-wrap" class="mail-pending-wrap" style="display:none;">
                    <div class="mail-section-title">Nowe</div>
                    <div id="${terminalId}-pending" class="mail-contact-list mail-conversation-list"></div>
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
        return msg.system === true || isWorldSourceKey(sourceKey) || sender === "system" || sender === "ghost system";
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
        const thread = payload.thread && typeof payload.thread === "object" ? payload.thread : null;
        if (thread) {
            const scope = thread.scope || payload.scope || "direct";
            const peer = thread.peer || payload.peer || (scope === "group" ? "global" : "");
            const key = `${scope}:${peer}`;
            threadSummaries.set(key, thread);
            if (scope === "group") {
                groupMessages = [thread];
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
        messagesBox.innerHTML = "";
        if (!messages.length) {
            messagesBox.innerHTML = `<div class="mail-empty">Brak wiadomosci. Zacznij rozmowe.</div>`;
            return;
        }

        messages.forEach(msg => {
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

    const loadMessages = async () => {
        if (!document.body.contains(term)) return;
        const params = new URLSearchParams({
            scope: currentChat.scope,
            peer: currentChat.peer
        });
        const res = await fetch(`/api/chats/messages?${params.toString()}`);
        const data = await res.json();
        unreadCounts = data.unread_counts || unreadCounts;
        groupActiveCount = data.group_active_count ?? groupActiveCount;
        if (currentChat.scope === "group") {
            groupMessages = data.messages || groupMessages;
        }
        renderContacts();
        renderMessages(data.messages || []);
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

    const bootstrap = async () => {
        if (!document.body.contains(term)) return;
        const res = await fetch('/api/mail/bootstrap');
        const data = await res.json();
        currentUser = data.username || "";
        channels = normalizeCybernerChannels(data.channels);
        contacts = data.contacts || [];
        pendingThreads = data.pending_threads || [];
        unreadCounts = data.unread_counts || unreadCounts;
        groupActiveCount = data.group_active_count ?? groupActiveCount;
        groupMessages = data.group_messages || groupMessages;
        renderContacts();
        if (requestedInitialPeer) {
            await openDirectChat(requestedInitialPeer);
            return;
        }
        if (requestedInitialThread) {
            await openCybernerThread(requestedInitialThread);
            return;
        }
        if (shouldRefreshVisibleChat()) {
            await loadMessages();
        }
    };

    const refreshThreads = async () => {
        if (!document.body.contains(term)) return;
        const res = await fetch('/api/mail/bootstrap');
        const data = await res.json();
        channels = normalizeCybernerChannels(data.channels);
        contacts = data.contacts || [];
        pendingThreads = data.pending_threads || [];
        unreadCounts = data.unread_counts || unreadCounts;
        groupActiveCount = data.group_active_count ?? groupActiveCount;
        groupMessages = data.group_messages || groupMessages;
        renderContacts();
        if (shouldRefreshVisibleChat()) {
            await loadMessages();
        }
    };

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
        try {
            const res = await fetch('/api/chats/messages', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scope: currentChat.scope,
                    peer: currentChat.peer,
                    body
                })
            });
            const data = await res.json();
            if (data.error) {
                addSystemMessage("warning", "Cyberner", data.error);
                return;
            }
            if (data.messages) {
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
    const mailRefreshTimer = setInterval(refreshThreads, CYBERNER_THREAD_REFRESH_INTERVAL_MS);
    term.querySelector('.close-btn').addEventListener('click', () => {
        clearInterval(mailRefreshTimer);
        window.activeCybernerThread = null;
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

function showSystemToast(message, type = 'success') {
    const container = document.getElementById("system-toast-container");
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
    const loadingToken = beginDesktopLoading('Sprawdzam system...');
    try {
        const res = await fetch('/system-messages');
        const data = await res.json();
        data.forEach((msg, i) => {
            setTimeout(() => {
                showSystemToast(msg, msg.type);
            }, i * 2000);
        });
    } catch (err) {
        console.error("Błąd pobierania komunikatów systemowych");
    } finally {
        endDesktopLoading(loadingToken);
    }
}

// 🔁 Co 10 sekund sprawdzaj nowe
setInterval(pollSystemMessages, 10000);
setTimeout(pollStateChanges, 1000);
setInterval(pollStateChanges, STATE_DELTA_POLL_INTERVAL_MS);

async function pollLaunchQueue() {
    const loadingToken = beginDesktopLoading('Sprawdzam system...');
    try {
        const res = await fetch('/launch-queue');
        const appsToLaunch = await res.json();

        if (appsToLaunch.logout) {
            window.location.href = '/';
            return;
        }

        if (Array.isArray(appsToLaunch) && appsToLaunch.length > 0) {
            for (const name of appsToLaunch) {
                const cmdRes = await fetch('/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ input: name })
                });

                const data = await cmdRes.json();

                if (data.runApp && data.applicationEffect) {
                    const appData = data.applicationEffect;
                    const id = appData.id;
                    const levels = appData.levels;
                    const type = appData.interface;

                    const action = () => {
                        if (runSystemLauncherApp(appData)) return;
                        if (type === "window") app_window(id, levels);
                        else if (type === "progressbar_random") app_progressbar_random(id, levels);
                        else if (type === "terminal") app_terminal(id, levels);
                        else if (type === "button_choices") app_button_choices(id, levels);
                        else console.warn(`❓ Nieznany interfejs: ${type}`);
                    };

                    action();
                }
            }
        }
    } catch (err) {
        console.error("❌ Błąd podczas pobierania launch-queue:", err);
    } finally {
        // Spróbuj ponownie za 10 sekund
        endDesktopLoading(loadingToken);
        setTimeout(pollLaunchQueue, 10000);
    }
}

// Uruchom po załadowaniu strony
document.addEventListener("DOMContentLoaded", () => {
    pollLaunchQueue();
    refreshPlayerHackAccess();
});
