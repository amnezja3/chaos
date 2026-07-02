let terminalCount = 3;
let topZIndex = 1000;
let windowSequence = 0;
let toolbarLauncherApps = [];
const runningWindows = new Map();
let desktopSettings = { wallpaper: "", icon_positions: {} };
let desktopSaveTimer = null;
let toolbarProfile = null;
let desktopSessionActive = true;
let playerHackAccessState = null;
let playerHackAccessTimer = null;

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
    if (bootLoader.status) bootLoader.status.textContent = message || "Ĺadowanie systemu...";
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
            updateDesktopLoadingStatus('SieÄ‡ przeciÄ…ĹĽona...');
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

const desktopApps = [
    { icon: '\u{1F5A5}\uFE0F', label: 'Terminal', action: createTerminal },
    { icon: '\u{1F5FA}\uFE0F', label: 'Mapa', action: createMap },
    { icon: '\u{1F310}', label: 'Browser', action: createBrowser },
    { icon: '\u2699\uFE0F', label: 'Ustawienia', action: createSettings },
    { icon: '\u{1F464}', label: 'Profil', action: createProfile },
    { icon: '\u{1F4C1}', label: 'Pliki', action: createFileManager },
    { icon: '\u{1F4E8}', label: 'Email', action: createEmailClient },
    { icon: '\u{1F4B0}', label: 'Wallet HC', action: openWalletApp }
];

const devBugReporterApp = {
    id: 'dev_bug_reporter',
    icon: '\u{1F41E}',
    label: 'Dev Bug Reporter',
    action: createDevBugReporterApp
};

const desktop = document.getElementById('desktop-icons');
const iconSpacing = 100; // odstÄ™p w pionie
const MOBILE_SAFE_MODE_QUERY = '(max-width: 900px), (max-height: 700px)';

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

function applyMobileSafeModeToOpenWindows() {
    document.querySelectorAll('.terminal, .app-window').forEach(applyMobileSafeModeToWindow);
}

function getDesktopIconKey(app) {
    return String(app.id || app.label || app.name || 'app').toLowerCase().replace(/[^a-z0-9_-]+/g, '_');
}

function applyDesktopSettings(settings = {}) {
    desktopSettings = {
        wallpaper: settings.wallpaper || "",
        icon_positions: settings.icon_positions || {}
    };
    document.body.classList.remove('wall-1', 'wall-2', 'wall-3');
    if (desktopSettings.wallpaper) {
        document.body.classList.add(desktopSettings.wallpaper);
    }
}

function collectDesktopIconPositions() {
    const positions = {};
    document.querySelectorAll('#desktop-icons .icon[data-icon-key]').forEach(icon => {
        positions[icon.dataset.iconKey] = {
            left: Math.round(icon.offsetLeft),
            top: Math.round(icon.offsetTop)
        };
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
    }).catch(err => console.warn("Nie udaĹ‚o siÄ™ zapisaÄ‡ pulpitu:", err));
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

window.addEventListener('beforeunload', () => {
    if (!desktop || !desktopSessionActive) return;
    const settings = mergeDesktopSettings({ icon_positions: collectDesktopIconPositions() });
    const payload = JSON.stringify(settings);
    if (navigator.sendBeacon) {
        navigator.sendBeacon('/api/profile/desktop', new Blob([payload], { type: 'application/json' }));
    }
});

function renderDesktopIcons(apps, settings = desktopSettings) {
    if (!desktop) return;
    desktop.innerHTML = '';
    const iconHeight = 100;
    const topOffset = 10;
    const leftOffset = 10;
    const colSpacing = 100;
    const windowHeight = window.innerHeight;
    const maxPerColumn = Math.max(1, Math.floor((windowHeight - topOffset) / iconHeight));
    const savedPositions = (settings && settings.icon_positions) || {};

    apps.forEach((app, index) => {
        const icon = document.createElement('div');
        const key = getDesktopIconKey(app);
        icon.className = 'icon';
        icon.dataset.iconKey = key;
        icon.innerHTML = `<span style="font-size: 3rem">${app.icon}</span> ${app.label}`;

        const row = index % maxPerColumn;
        const col = Math.floor(index / maxPerColumn);
        const saved = savedPositions[key];
        icon.style.top = `${Number.isFinite(Number(saved?.top)) ? Number(saved.top) : topOffset + row * iconHeight}px`;
        icon.style.left = `${Number.isFinite(Number(saved?.left)) ? Number(saved.left) : leftOffset + col * colSpacing}px`;

        icon.addEventListener('dblclick', app.action);

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
            if (!isDragging) return;
            isDragging = false;
            icon.style.zIndex = '';
            document.body.style.userSelect = 'auto';
            saveDesktopSettingsNow({ icon_positions: collectDesktopIconPositions() });
        });

        desktop.appendChild(icon);
    });
}

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
    const hasTarget = Boolean(aimedTarget.lat !== undefined || aimedTarget.lng !== undefined || aimedTarget.label || aimedTarget.name);
    const targetLabel = aimedTarget.label || aimedTarget.name || "brak";
    const arsenalCoverage = calculateToolbarArsenalCoverage(profile);
    const arsenalLabel = arsenalCoverage === null ? "--" : `${arsenalCoverage}%`;
    strip.innerHTML = `
        <span class="system-status-target ${hasTarget ? 'is-aimed' : ''}" title="Cel na celowniku: ${escapeHTML(String(targetLabel))}"><b>CEL</b><em>${escapeHTML(String(targetLabel))}</em></span>
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
                <span>â†»</span>
                <span>Restart</span>
            </button>
            <button class="system-start-item system-action-logout" type="button">
                <span>âŹ»</span>
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
        console.error("BĹ‚Ä…d uruchamiania aplikacji z paska:", err);
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

async function buildIconsFromJsonWithCommand(jsonData) {
    const icons = [];

    for (const app of jsonData) {
        const name = app.name;

        try {
            if (false) {
                if (pending.action === "userdel") {
                    const deleteRes = await fetch('/api/users/delete', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username: pending.username })
                    });
                    const deleteData = await deleteRes.json();
                    content.innerHTML += `<br>${escapeHTML(deleteData.message || "Operacja zakoĹ„czona.")}`;
                    appendTerminalPrompt(content);
                    return;
                }
            }

            const res = await fetch('/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ input: name })
            });

            const data = await res.json();

            if (data.runApp && data.applicationEffect) {
                const appData = data.applicationEffect;
                const id = appData.id;
                const levels = appData.levels;
                const type = appData.interface;

                // đź‘‡ Zbuduj action dokĹ‚adnie jak w terminalu, ale bez logĂłw
                const action = () => {
                    if (runSystemLauncherApp(appData)) return;
                    if (type === "window") app_window(id, levels);
                    else if (type === "progressbar_random") app_progressbar_random(id, levels);
                    else if (type === "terminal") app_terminal(id, levels);
                    else if (type === "button_choices") app_button_choices(id, levels);
                    else console.warn(`Nieznany interface: ${type}`);
                };

                icons.push({
                    icon: app.icon || 'âť“',
                    label: name,
                    action
                });
            } else {
                console.warn(`Brak applicationEffect dla: ${name}`);
            }

        } catch (err) {
            console.error(`BĹ‚Ä…d przy pobieraniu ${name}:`, err);
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
            addSystemMessage("danger", "đź“ Profil", "âťŚ Brak danych profilu");
            finishBootLoader("Nie udaĹ‚o siÄ™ wczytaÄ‡ profilu.");
            return;
        }
        const res = profileData.apps;
        
        setBootProgress(34, `Profil aktywny: ${profileData.nick || profileData.username || "operator"}`);
        console.log(profileData);
        // const jsonApps = await res.json();
        const jsonApps = profileData.apps || []; 

        setBootProgress(58, `Indeksowanie aplikacji: ${jsonApps.length}`);
        const generatedIcons = await buildIconsFromJsonWithCommand(jsonApps);
        const systemApps = profileData.dev_mode ? [...desktopApps, devBugReporterApp] : desktopApps;
        const allApps = [...generatedIcons, ...systemApps]; // dodajesz wĹ‚asne z kodu
        setBootProgress(76, "Montowanie paska systemowego...");
        setToolbarLaunchers(allApps, profileData);
        setBootProgress(88, "Odtwarzanie tapety i pozycji ikon...");
        applyDesktopSettings(profileData.desktop_settings || {});
        renderDesktopIcons(allApps, desktopSettings);
        finishBootLoader("ghost_init.pkg zakoĹ„czony. System gotowy.");
        return;
    } catch (err) {
        console.error("BĹ‚Ä…d startu pulpitu:", err);
        finishBootLoader("Tryb awaryjny: pulpit uruchomiony czÄ™Ĺ›ciowo.");
        return;
    }

    const iconHeight = 100; // wysokoĹ›Ä‡ + padding
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

        // â¬‡ď¸Ź ObsĹ‚uga przeciÄ…gania:
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

            if (data.confirm) {
                content.pendingConfirm = data.confirm;
                content.innerHTML += `<br>${escapeHTML(data.confirm.prompt)}`;
                appendTerminalPrompt(content);
                return;
            }

            if (data.response) {
                content.innerHTML += `<br>${data.response.replace(/\n/g, "<br>")}`;
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

                // đź‘‡ WyĹ›wietl consoleEffect zanim pojawi siÄ™ nowy input
                const conDiv = document.createElement('div');
                conDiv.innerHTML = consoleEffect.replace(/\n/g, "<br>");
                content.appendChild(conDiv);

                // đź‘‡ Uruchom aplikacjÄ™
                if (!runSystemLauncherApp(app)) {
                if (type === "window") app_window(id, levels);
                if (type === "progressbar_random") app_progressbar_random(id, levels);
                if (type === "terminal") app_terminal(id, levels);
                if (type === "button_choices") app_button_choices(id, levels);
                }
            }

            // đź‘‡ Dopiero teraz tworzysz nowÄ… liniÄ™ terminala
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
            content.innerHTML += `<br><span style="color:red;">âťŚ BĹ‚Ä…d komunikacji z serwerem</span>`;
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
        if (res.status === "success") {
            console.log("âś… WiadomoĹ›Ä‡ systemowa dodana");
        } else {
            console.warn("âš ď¸Ź BĹ‚Ä…d dodawania wiadomoĹ›ci:", res.message || res.error);
        }
    })
    .catch(err => {
        console.error("âťŚ BĹ‚Ä…d poĹ‚Ä…czenia z serwerem", err);
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
        <div class="title-bar">System Log Reader <span class="close-btn" style="float:right; cursor:pointer;">x</span></div>
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
        <div class="title-bar">Financial Sniffer <span class="close-btn" style="float:right; cursor:pointer;">x</span></div>
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
        <div class="title-bar">Friend Kicker <span class="close-btn" style="float:right; cursor:pointer;">x</span></div>
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
        <div class="title-bar">Arsenal Cleaner <span class="close-btn" style="float:right; cursor:pointer;">x</span></div>
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
        <div class="title-bar">Security Panel Proxy <span class="close-btn" style="float:right; cursor:pointer;">x</span></div>
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
            if (msg) msg.textContent = data.error || 'NarzÄ™dzie niedostepne.';
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
        <div class="title-bar">Dev Bug Reporter <span class="close-btn" style="float:right; cursor:pointer;">&times;</span></div>
        <div class="app-content dev-bug-shell">
            <div class="dev-bug-toolbar">
                <input type="search" data-bug-search placeholder="Szukaj zgĹ‚oszeĹ„..." />
                <select data-bug-category-filter>
                    <option value="">Wszystkie kategorie</option>
                    ${DEV_BUG_CATEGORIES.map(cat => `<option value="${cat}">${cat}</option>`).join('')}
                </select>
                <select data-bug-status-filter>
                    <option value="">Wszystkie statusy</option>
                    ${DEV_BUG_STATUSES.map(status => `<option value="${status}">${status}</option>`).join('')}
                </select>
                <button type="button" data-bug-refresh>OdĹ›wieĹĽ</button>
            </div>
            <div class="dev-bug-message" data-bug-message></div>
            <div class="dev-bug-layout">
                <aside class="dev-bug-list" data-bug-list>
                    <div class="dev-bug-empty">Ĺadowanie zgĹ‚oszeĹ„...</div>
                </aside>
                <main class="dev-bug-detail">
                    <section class="dev-bug-card" data-bug-detail>
                        <h3>Wybierz zgĹ‚oszenie</h3>
                        <p>Lista jest wspĂłlna dla testerĂłw dev/staging.</p>
                    </section>
                    <section class="dev-bug-card">
                        <h3>Nowe zgĹ‚oszenie</h3>
                        <form data-bug-form>
                            <label>TytuĹ‚
                                <input type="text" name="title" required maxlength="160" placeholder="KrĂłtko: co nie dziaĹ‚a?" />
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
                            <button type="submit">Dodaj zgĹ‚oszenie</button>
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
                <h3>Wybierz zgĹ‚oszenie</h3>
                <p>Lista jest wspĂłlna dla testerĂłw dev/staging.</p>
            `;
            return;
        }
        detail.innerHTML = `
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
                <summary>PeĹ‚ny context_json</summary>
                <textarea readonly>${escapeHTML(JSON.stringify(report.context || {}, null, 2))}</textarea>
            </details>
        `;
        detail.querySelector('[data-bug-status-update]')?.addEventListener('change', async (event) => {
            await updateBugReportStatus(report.id, event.target.value);
        });
    };

    const renderList = () => {
        const list = app.querySelector('[data-bug-list]');
        if (!list) return;
        if (!state.reports.length) {
            list.innerHTML = '<div class="dev-bug-empty">Brak zgĹ‚oszeĹ„ dla aktualnych filtrĂłw.</div>';
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
        setMessage('Ĺadowanie zgĹ‚oszeĹ„...');
        try {
            const res = await fetch(`/api/dev/bug-reports?${params.toString()}`);
            const data = await res.json();
            if (!res.ok || !data.success) {
                setMessage(data.message || 'Dev Bug Reporter jest niedostÄ™pny.', 'error');
                return;
            }
            state.reports = data.reports || [];
            state.appVersion = data.app_version || '';
            setMessage(`ZgĹ‚oszenia: ${state.reports.length}`, 'success');
            renderList();
        } catch (err) {
            console.error('Dev Bug Reporter load failed:', err);
            setMessage('BĹ‚Ä…d poĹ‚Ä…czenia z Dev Bug Reporter.', 'error');
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
                setMessage(data.message || 'Nie udaĹ‚o siÄ™ zmieniÄ‡ statusu.', 'error');
                return;
            }
            setMessage(data.message || 'Status zmieniony.', 'success');
            await loadReports();
        } catch (err) {
            console.error('Dev Bug Reporter update failed:', err);
            setMessage('BĹ‚Ä…d aktualizacji statusu.', 'error');
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
                <strong>MoĹĽliwe, ĹĽe taki bug juĹĽ istnieje.</strong>
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
        setMessage('Zapisywanie zgĹ‚oszenia...');
        try {
            const res = await fetch('/api/dev/bug-reports', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!res.ok || !data.success) {
                setMessage(data.message || 'Nie udaĹ‚o siÄ™ zapisaÄ‡ zgĹ‚oszenia.', 'error');
                return;
            }
            form.reset();
            const dupes = app.querySelector('[data-bug-duplicates]');
            if (dupes) {
                dupes.hidden = true;
                dupes.innerHTML = '';
            }
            state.selectedId = data.report?.id || null;
            setMessage(data.message || 'ZgĹ‚oszenie zapisane.', 'success');
            await loadReports();
        } catch (err) {
            console.error('Dev Bug Reporter create failed:', err);
            setMessage('BĹ‚Ä…d zapisu zgĹ‚oszenia.', 'error');
        }
    });

    app.querySelector('[data-bug-refresh]')?.addEventListener('click', loadReports);
    app.querySelector('[data-bug-search]')?.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(loadReports, 250);
    });
    app.querySelector('[data-bug-category-filter]')?.addEventListener('change', loadReports);
    app.querySelector('[data-bug-status-filter]')?.addEventListener('change', loadReports);

    loadReports();
}


function createTerminal() {
    terminalCount++;
    const term = document.createElement('div');
    term.className = 'terminal';
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    // term.style.top = `${50 + terminalCount * 20}px`;
    // term.style.left = `${50 + terminalCount * 20}px`;
    const terminalId = `terminal-${terminalCount}`;

    term.innerHTML = `
        <div class="title-bar">Terminal <span class="close-btn" style="float:right; cursor:pointer;">âś–</span></div>
        <div class="terminal-body">
            <div class="content" id="${terminalId}-content">
                <div class="terminal-line">
                    <label class="terminal-label">user@hostname:~$</label>
                    <input type="text" class="terminal-input" autocomplete="off" />
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(term);
    makeDraggable(term);

    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    const content = term.querySelector(`#${terminalId}-content`);
    const input = content.querySelector('input');
    setTimeout(() => input.focus(), 10);

    attachTerminalInputHandler(input, content);
}

function app_window(id, levels) {
    const app = document.createElement('div');
    app.className = 'app-window';
    const position = findAvailablePosition();
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;

    app.innerHTML = `
        <div class="title-bar">${id} <span class="close-btn" style="float:right; cursor:pointer;">âś–</span></div>
        <div class="app-content">
            <h3>${levels[0].title || 'Aplikacja'}</h3>
            <ul>${levels[0].list.map(item => `<li>${item}</li>`).join('')}</ul>
            <div class="button-row">
                ${levels[0].buttons.map((b, i) => `
                    <button data-action="${b.action}" data-label="${b.label}">
                        ${b.label}
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
            const action = btn.dataset.action;
            const label = btn.dataset.label;

            const response = await sendGonnaWinRequest(id, action);  // <-- uĹĽycie naszej funkcji
            const success = response.success === true;

            addSystemMessage('info', 'đź•ąď¸Ź Akcja', `Akcja: ${label} | Wynik: ${success ? "âś…" : "âťŚ"}`);
            resultBox.innerHTML = success ? "âś… Sukces!" : "âťŚ Niepowodzenie.";
            resultBox.style.color = success ? "#0f0" : "#f33";
        });
    });
}




async function app_progressbar_random(id, levels) {
    const level = levels[0];
    const steps = level.steps || [];
    const app = document.createElement('div');
    app.className = 'app-window';
    const position = findAvailablePosition();
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;

    app.innerHTML = `
        <div class="title-bar">${level.title || id} <span class="close-btn" style="float:right; cursor:pointer;">âś–</span></div>
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
                result.innerHTML = success ? level.result_success : level.result_failure;
                result.style.color = success ? "#0f0" : "#f33";
            }).catch(() => {
                result.innerHTML = "âťŚ BĹ‚Ä…d poĹ‚Ä…czenia z serwerem.";
                result.style.color = "#f33";
            });
            return;
        }

        const msg = steps[stepIndex];
        log.innerHTML += `<div>đź•“ ${msg}</div>`;
        fill.style.width = `${(stepIndex + 1) * progressPerStep}%`;

        stepIndex++;
        setTimeout(runNextStep, 1000 + Math.random() * 1000); // miÄ™dzy 1â€“2s delay
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
        console.error(`âťŚ BĹ‚Ä…d poĹ‚Ä…czenia z /gonna-win dla ${appId}`, err);
        return false; // default przy bĹ‚Ä™dzie
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
            console.warn("Nie udaĹ‚o siÄ™ odĹ›wieĹĽyÄ‡ markera mapy:", err);
        }
    });
}

function notifyOpenMapsOperationsChanged() {
    document.querySelectorAll('.map-window iframe, iframe[src="/map"]').forEach(frame => {
        try {
            const mapWindow = frame.contentWindow;
            if (mapWindow && typeof mapWindow.refreshActiveOperations === 'function') {
                mapWindow.refreshActiveOperations();
            }
        } catch (err) {
            console.warn("Nie udalo sie odswiezyc operacji mapy:", err);
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
        console.error("BĹ‚Ä…d komunikacji z backendem:", error);
        return { success: false };
    }
}

function app_terminal(id, levels) {
    notifyGonnaWin(id);
    const level = levels[0];
    const commands = level.command ? [level.command, ...level.logs] : level.logs || [];

    const app = document.createElement('div');
    app.className = 'app-window';
    const position = findAvailablePosition();
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;
    app.innerHTML = `
        <div class="title-bar">${id} <span class="close-btn" style="float:right; cursor:pointer;">âś–</span></div>
        <div class="app-content" style="background: black; color: #0f0; font-family: monospace; padding: 10px;">
            <div class="terminal-log" style="min-height: 200px;"></div>
        </div>
    `;
    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());

    const log = app.querySelector('.terminal-log');

    let commandIndex = 0;

    function simulateTyping(command, callback) {
        const line = document.createElement('div');
        line.className = 'terminal-line';
        const label = document.createElement('span');
        label.textContent = 'remote@host:~$ ';
        const typingSpan = document.createElement('span');
        line.appendChild(label);
        line.appendChild(typingSpan);
        log.appendChild(line);

        let charIndex = 0;
        const typingInterval = setInterval(() => {
            typingSpan.textContent += command[charIndex];
            charIndex++;
            if (charIndex >= command.length) {
                clearInterval(typingInterval);
                setTimeout(() => {
                    // PrzenieĹ› wpisane polecenie wyĹĽej jako "executed"
                    line.innerHTML = `> ${command}`;

                    // Dodaj pasek progresu jeĹ›li komenda zawiera sĹ‚owo typu "scan" lub "check"
                    if (/scan|check|report/i.test(command)) {
                        const progress = document.createElement('div');
                        progress.style.cssText = `
                            background: #0f0;
                            height: 2px;
                            width: 0%;
                            margin: 4px 0;
                            transition: width 0.5s;
                        `;
                        log.appendChild(progress);
                        let percent = 0;
                        const barInterval = setInterval(() => {
                            percent += Math.random() * 20;
                            progress.style.width = `${Math.min(percent, 100)}%`;
                            if (percent >= 100) clearInterval(barInterval);
                        }, 200);
                    }

                    callback(); // przejdĹş do kolejnego polecenia
                    log.scrollTop = log.scrollHeight;
                }, 500);
            }
        }, 50);
    }

    function runNextCommand() {
        if (commandIndex >= commands.length) return;
        const current = commands[commandIndex];
        commandIndex++;
        simulateTyping(current, runNextCommand);
    }

    runNextCommand();
}


function app_button_choices(id, levels) {
    const lvl = levels[0];
    const app = document.createElement('div');
    app.className = 'app-window';
    const position = findAvailablePosition();
    app.style.top = `${position.top}px`;
    app.style.left = `${position.left}px`;

    app.innerHTML = `
        <div class="title-bar">${id} <span class="close-btn" style="float:right; cursor:pointer;">âś–</span></div>
        <div class="app-content">
            <h3>${lvl.title}</h3>
            <p>${lvl.text}</p>
            <div class="button-row">
                ${lvl.options.map((opt, i) => `
                    <button data-opt-id="${opt.id || i}" class="choice-btn">
                        ${opt.label}
                    </button>
                `).join('')}
            </div>
            <div class="choice-result" style="margin-top:10px; font-weight:bold;"></div>
        </div>
    `;

    document.body.appendChild(app);
    makeDraggable(app);
    app.querySelector('.close-btn').addEventListener('click', () => app.remove());

    // ObsĹ‚uga klikniÄ™cia kaĹĽdego guzika
    const buttons = app.querySelectorAll('.choice-btn');
    const resultBox = app.querySelector('.choice-result');

    buttons.forEach(btn => {
        btn.addEventListener('click', async () => {
            const optId = btn.dataset.optId;
            const choiceLabel = btn.textContent.trim();

            // WywoĹ‚anie backendu i oczekiwanie na wynik
            const response = await sendGonnaWinRequest(id, optId); // nowa wersja z 2 parametrami
            const success = response.success === true;

            addSystemMessage('info', 'đź§Ş Efekt', `Wybrano: ${choiceLabel} | Wynik: ${success ? "âś… SUKCES" : "âťŚ PORAĹ»KA"}`);
            resultBox.innerHTML = success ? "âś… UdaĹ‚o siÄ™!" : "âťŚ Niestety nie tym razem.";
            resultBox.style.color = success ? "#0f0" : "#f33";
        });
    });
}



function makeDraggable(term) {
    registerWindowInTaskbar(term);
    applyMobileSafeModeToWindow(term);
    const bar = term.querySelector('.title-bar');
    bringWindowToFront(term);
    if (!bar) return;
    let isDragging = false, x = 0, y = 0;

    term.addEventListener('mousedown', () => bringWindowToFront(term));

    bar.addEventListener('mousedown', (e) => {
        bringWindowToFront(term);
        if (isMobileSafeMode()) {
            applyMobileSafeModeToWindow(term);
            return;
        }

        isDragging = true;
        x = e.clientX - term.offsetLeft;
        y = e.clientY - term.offsetTop;
        document.body.style.userSelect = 'none';
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        if (isMobileSafeMode()) {
            isDragging = false;
            document.body.style.userSelect = 'auto';
            applyMobileSafeModeToWindow(term);
            return;
        }
        term.style.left = `${e.clientX - x}px`;
        term.style.top = `${e.clientY - y}px`;
    });

    window.addEventListener('mouseup', () => {
        isDragging = false;
        document.body.style.userSelect = 'auto';
    });
}

window.addEventListener('resize', applyMobileSafeModeToOpenWindows);

// Aktywuj istniejÄ…ce terminale
document.querySelectorAll('.terminal').forEach(makeDraggable);

function createMap() {
    if (document.querySelector(`.terminal[data-app="map"]`)) return;
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
        <iframe src="/map" width="100%" height="100%" style="border:none;"></iframe>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    const closeButton = term.querySelector('.close-btn');
    if (closeButton) closeButton.textContent = 'x';
    closeButton?.addEventListener('click', () => term.remove());
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
        <span class="close-btn" style="float:right; cursor:pointer;">${browserUiIcons.close}</span>
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
        </div>
        <input type="text" id="${terminalId}-search" placeholder="Wyszukaj aplikacj\u0119..." class="googolplex-search">
        <div id="${terminalId}-results" class="googolplex-grid"></div>
    </div>
    `;

    document.body.appendChild(term);
    const contentWrapper = term.querySelector('div[style*="display: flex"][style*="flex-direction: column"]');
    if (contentWrapper) {
        contentWrapper.style.minHeight = '0';
    }
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    // ObsĹ‚uga wyszukiwania
    const search = term.querySelector(`#${terminalId}-search`);
    const results = term.querySelector(`#${terminalId}-results`);
    const wallet = term.querySelector(`#${terminalId}-wallet`);
    let catalog = [];
    let exchangeFiles = [];
    let walletBalance = 0;
    let activeBrowserTab = "googleplex";

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
        ...googleplexList(item.map_actions),
        ...googleplexList(item.operation_types),
        ...googleplexList(item.resource_types),
        ...googleplexList(item.target_types)
    ].join(' ').toLowerCase();

    const renderCatalog = () => {
        if (activeBrowserTab !== "googleplex") return;
        updateBrowserNarrowMode();
        const query = search.value.toLowerCase().trim();
        if (!query) {
            results.innerHTML = "";
            updateBrowserNarrowMode();
            return;
        }

        const matches = catalog.filter(item => googleplexSearchText(item).includes(query));

        results.innerHTML = '';
        if (matches.length === 0) {
            results.innerHTML = '<div class="googolplex-empty">Brak aplikacji do pokazania.</div>';
            updateBrowserNarrowMode();
            return;
        }

        matches.forEach(item => {
            const price = Number(item.price || 0);
            const installed = item.installed === true;
            const canAfford = walletBalance >= price;
            const installBlockedReason = item.install_blocked_reason || "";
            const canInstall = !installed && canAfford && !installBlockedReason;
            const buttonLabel = installed ? "Zainstalowane" : (canAfford ? "Zainstaluj" : "Brak \u015brodk\u00f3w");
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
            card.querySelector('button').addEventListener('click', () => {
                if (!canInstall) return;
                showInstallAppProgress(item, async () => {
                    await loadCatalog();
                });
            });
            results.appendChild(card);
        });
        updateBrowserNarrowMode();
    };

    const renderExchange = () => {
        if (activeBrowserTab !== "exchange") return;
        updateBrowserNarrowMode();
        const query = search.value.toLowerCase().trim();
        const matches = exchangeFiles.filter(item => {
            const resources = Array.isArray(item.resource_types) ? item.resource_types.join(' ') : '';
            return !query ||
                String(item.name || '').toLowerCase().includes(query) ||
                String(item.file_category || '').toLowerCase().includes(query) ||
                String(item.market_category || '').toLowerCase().includes(query) ||
                resources.toLowerCase().includes(query);
        });

        results.innerHTML = '';
        if (matches.length === 0) {
            results.innerHTML = '<div class="googolplex-empty">Brak sprzedawalnych plikow danych.</div>';
            updateBrowserNarrowMode();
            return;
        }

        matches.forEach(item => {
            const status = item.market_status || 'not_listed';
            const prepared = status === 'listed_preview';
            const resources = Array.isArray(item.resource_types) && item.resource_types.length
                ? item.resource_types.join(', ')
                : '-';
            const missingFields = Array.isArray(item.missing_fields) ? item.missing_fields : [];
            const completeness = Number(item.completeness_percent ?? (item.metadata || {}).completeness_percent ?? 0);
            const qualityScore = Number(item.quality_score ?? (item.metadata || {}).quality_score ?? 0);
            const card = document.createElement('article');
            card.className = `googolplex-card ghost-exchange-card ${prepared ? 'is-listed-preview' : ''}`;
            card.innerHTML = `
                <div class="googolplex-card-title">
                    <span class="googolplex-card-icon">${item.icon || browserUiIcons.app}</span>
                    <span>${escapeHTML(item.name || 'Pakiet danych')}</span>
                </div>
                <p>${escapeHTML(item.directory || item.file_category || '/data')} | ${escapeHTML(item.preview_mode || 'preview')}</p>
                <div class="ghost-exchange-meta">
                    <span>Kategoria: <b>${escapeHTML(item.file_category || '-')}</b></span>
                    <span>Rynek: <b>${escapeHTML(item.market_category || '-')}</b></span>
                    <span>Zasoby: <b>${escapeHTML(resources)}</b></span>
                    <span>Status: <b>${escapeHTML(status)}</b></span>
                    <span>Kompletno\u015b\u0107: <b>${Math.max(0, Math.min(100, completeness))}% / ${escapeHTML(item.completeness_tier || (item.metadata || {}).completeness_tier || '-')}</b></span>
                    <span>Jako\u015b\u0107: <b>${qualityScore}/100</b></span>
                    <span>Braki: <b>${escapeHTML(missingFields.length ? missingFields.slice(0, 3).join(', ') : 'brak')}</b></span>
                </div>
                <div class="googolplex-card-footer">
                    <strong>${Number(item.price_preview || 0)} HC</strong>
                    <button type="button" class="ghost-exchange-preview-btn" ${prepared ? 'disabled' : ''}>
                        ${prepared ? 'Preview gotowy' : 'Preview sale'}
                    </button>
                    <button type="button" class="ghost-exchange-sell-btn">Sprzedaj</button>
                </div>
            `;
            card.querySelector('.ghost-exchange-preview-btn').addEventListener('click', async () => {
                if (prepared) return;
                await previewGhostExchangeSale(item.id);
            });
            card.querySelector('.ghost-exchange-sell-btn').addEventListener('click', async () => {
                await sellGhostExchangeFile(item.id);
            });
            results.appendChild(card);
        });
        updateBrowserNarrowMode();
    };

    async function loadCatalog() {
        const [profileRes, resourcesRes] = await Promise.all([
            fetch('/api/profile'),
            fetch('/resources.json')
        ]);
        const profile = await profileRes.json();
        catalog = await resourcesRes.json();
        walletBalance = Number(profile.hackcoins || 0);
        wallet.textContent = `HackCoiny: ${walletBalance}`;
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
            wallet.textContent = `HackCoiny: ${walletBalance}`;
            if (typeof setToolbarProfile === "function") {
                setToolbarProfile({
                    ...(toolbarProfile || {}),
                    hackcoins: walletBalance
                });
            }
            if (typeof refreshToolbarProfile === "function") {
                await refreshToolbarProfile().catch(() => null);
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
        updateBrowserNarrowMode();
        term.querySelectorAll('.browser-tab').forEach(button => {
            button.classList.toggle('is-active', button.dataset.browserTab === tabName);
        });
        const title = term.querySelector(`#${terminalId}-title`);
        if (tabName === "exchange") {
            title.textContent = "Ghost Exchange";
            search.placeholder = "Szukaj danych, kategorii rynku, zasobow...";
            loadExchange();
        } else {
            title.textContent = "Googolplex";
            search.placeholder = "Wyszukaj aplikacje...";
            renderCatalog();
        }
    }

    term.querySelectorAll('.browser-tab').forEach(button => {
        button.addEventListener('click', () => switchBrowserTab(button.dataset.browserTab || "googleplex"));
    });
    search.addEventListener('input', () => {
        if (activeBrowserTab === "exchange") {
            renderExchange();
        } else {
            renderCatalog();
        }
    });
    loadCatalog().catch(() => {
        results.innerHTML = '<div class="googolplex-empty">Nie udaĹ‚o siÄ™ pobraÄ‡ katalogu.</div>';
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
            <span class="close-btn" style="float:right; cursor:pointer;">x</span>
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
        if (typeof refreshToolbarProfile === "function") {
            refreshToolbarProfile();
        }
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
        `Rozpoczynanie instalacji aplikacji: <b>${app.name}</b>`,
        `Pobieranie plikĂłw...`,
        `Instalacja skĹ‚adnikĂłw...`,
        `Rejestracja aplikacji w systemie...`,
        `Finalizacja...`
    ];

    const appWindow = document.createElement('div');
    appWindow.className = 'app-window';
    const position = findAvailablePosition();
    appWindow.style.top = `${position.top}px`;
    appWindow.style.left = `${position.left}px`;
    appWindow.innerHTML = `
        <div class="title-bar">${app.name} â€“ Instalacja <span class="close-btn" style="float:right; cursor:pointer;">âś–</span></div>
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
            // WysyĹ‚ka do backendu na koĹ„cu
            fetch('/install-app', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ app_id: app.id })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    const storage = data.storage || {};
                    const storageLine = storage.used
                        ? `<br><span style="color:#8fd6a4;">Dysk: ${escapeHTML(formatStorageSize(storage.used, storage.unit || 'MB'))} / ${escapeHTML(formatStorageSize(storage.capacity, storage.unit || 'MB'))}${storage.over_limit ? ' (ponad limit miÄ™kki)' : ''}</span>`
                        : '';
                    result.innerHTML = `<span style="color:#0f0;">âś… Aplikacja zainstalowana.</span>${storageLine}`;
                    if (Object.prototype.hasOwnProperty.call(data, "hackcoins")) {
                        setToolbarProfile({
                            ...toolbarProfile,
                            hackcoins: data.hackcoins
                        });
                    }

                    // Zamykamy okno po 4 sekundach i przeĹ‚adowujemy "pulpit"
                    setTimeout(async () => {
                        // ZnajdĹş i usuĹ„ okno instalacji
                        if (appWindow && appWindow.parentNode) appWindow.parentNode.removeChild(appWindow);

                        if (typeof onInstalled === "function") {
                            await onInstalled(data);
                        }

                        // OdĹ›wieĹĽ caĹ‚oĹ›Ä‡ przez przeĹ‚adowanie strony (najproĹ›ciej)
                        // location.reload();

                        // Lub lepiej: przebuduj ikony, menedĹĽer plikĂłw itd. bez reloadu:
                        if (typeof refreshDesktop === "function") {
                            refreshDesktop(false);
                        } else {
                            // fallback: przeĹ‚aduj caĹ‚oĹ›Ä‡
                            location.reload();
                        }
                    }, 4000);
                } else {
                    result.innerHTML = `<span style="color:#f33;">âťŚ BĹ‚Ä…d instalacji: ${data.message}</span>`;
                }
            })
            .catch(err => {
                result.innerHTML = `<span style="color:#f33;">âťŚ BĹ‚Ä…d poĹ‚Ä…czenia z serwerem.</span>`;
            });
            return;
        }

        log.innerHTML += `<div>đź•“ ${steps[stepIndex]}</div>`;
        fill.style.width = `${(stepIndex + 1) * progressPerStep}%`;

        stepIndex++;
        setTimeout(runNextStep, 900 + Math.random() * 700);
    }
    runNextStep();
}

async function refreshDesktop(closeWindows = true) {
    // 1. CzyĹ›Ä‡ wszystkie ikony z pulpitu
    const desktop = document.getElementById('desktop-icons');
    if (desktop) desktop.innerHTML = '';

    // 2. Zamknij wszystkie okna (terminal, app-window, terminal*)
    if (closeWindows) {
        document.querySelectorAll('.terminal, .app-window').forEach(win => win.remove());
    }

    // 3. Pobierz najnowszy profil
    const profileData = await getUserProfile();
    if (!profileData) {
        addSystemMessage("danger", "đź“ Profil", "âťŚ Brak danych profilu");
        return;
    }

    // 4. Zbuduj nowe ikony (logika z twojego async init)
    const jsonApps = profileData.apps || [];
    const generatedIcons = await buildIconsFromJsonWithCommand(jsonApps);

    // PoĹ‚Ä…cz wĹ‚asne i systemowe aplikacje
    const allApps = [...generatedIcons, ...desktopApps];
    setToolbarLaunchers(allApps, profileData);
    applyDesktopSettings(profileData.desktop_settings || {});
    renderDesktopIcons(allApps, desktopSettings);
    return;

    // Od nowa rozmieĹ›Ä‡ ikony na pulpicie
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

        // Drag & drop obsĹ‚uga (skopiowana z twojego kodu)
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
    if (document.querySelector(`.terminal[data-app="settings"]`)) return;
    const term = document.createElement('div');
    term.className = 'terminal';
    term.dataset.app = "settings";
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `400px`;
    term.style.height = `300px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';

    const terminalId = `settings-${Date.now()}`;

    term.innerHTML = `
        <div class="title-bar">
            Ustawienia
            <span class="close-btn" style="float:right; cursor:pointer;">âś–</span>
        </div>
        <div style="padding: 10px; background: #111; color: #0f0; flex:1;">
            <h3>Tapeta</h3>
            <button class="wall-btn" data-wall="wall-1">đźŚ… Tapeta 1</button>
            <button class="wall-btn" data-wall="wall-2">đźŹ™ď¸Ź Tapeta 2</button>
            <button class="wall-btn" data-wall="wall-3">đźŚŚ Tapeta 3</button>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    // ObsĹ‚uga zmiany tapety
    term.querySelectorAll('.wall-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const wall = btn.dataset.wall;
            applyDesktopSettings({
                ...desktopSettings,
                wallpaper: wall
            });
            saveDesktopSettings({ wallpaper: wall });
        });
    });
}

async function createProfile() {
    if (document.querySelector(`.terminal[data-app="profile"]`)) return;

    const term = document.createElement('div');
    term.className = 'terminal';
    term.dataset.app = "profile";
    const position = findAvailablePosition();
    term.style.top = `${position.top}px`;
    term.style.left = `${position.left}px`;
    term.style.width = `420px`;
    term.style.height = `580px`;
    term.style.display = 'flex';
    term.style.flexDirection = 'column';

    const profileData = await getUserProfile();
    if (!profileData) {
        addSystemMessage("danger", "đź“ Profil", "âťŚ Brak danych profilu");
        return;
    }

    const booleanSecurityEntries = Object.entries(profileData.security || {})
        .filter(([, value]) => typeof value === 'boolean');
    const securityControls = booleanSecurityEntries
        .map(([key, value]) => `
            <label class="profile-security-row" title="${escapeHTML(key)}">
                <span class="profile-security-name">${escapeHTML(key)}</span>
                <input class="profile-security-toggle" type="checkbox" data-security-key="${escapeHTML(key)}" ${value ? 'checked' : ''}>
                <span class="profile-security-state">${value ? 'ON' : 'OFF'}</span>
            </label>
        `)
        .join("");

    const securityList = Object.entries(profileData.security || {})
        .map(([key, value]) => `đź” ${key}: <b>${value ? 'ON' : 'OFF'}</b>`)
        .join("<br>");
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
    const territoryDetailsHtml = `
            <p>Efektywna kontrola: <b>${effectiveArea} mÂ˛</b></p>
            <p>GÄ™stoĹ›Ä‡ siatki: <b>x${densityMultiplier.toFixed(2)}</b> (${spanDensity.toFixed(2)} przÄ™seĹ‚ / 100 m)</p>
    `;

    term.innerHTML = `
        <div class="title-bar">
            Profil gracza
            <span class="close-btn" style="float:right; cursor:pointer;">âś–</span>
        </div>
        <div style="padding: 10px; background: #111; color: #0f0; flex:1; font-family: monospace; overflow-y:auto;">
            <div style="text-align: center;">
                <img src="${profileData.avatar}" alt="Avatar" style="width:100px;height:100px;border-radius:50%;margin-bottom:10px;">
                <h2 style="margin:0;">${profileData.nick}</h2>
                <p style="margin:0;">Poziom: <b>${profileData.level}</b></p>
            </div>

            <hr style="border: 1px solid #0f0; margin: 15px 0;">

            <p>đź’° HackCoiny: <b>${profileData.hackcoins}</b></p>
            <p>đź§  DoĹ›wiadczenie: <b>${profileData.exp}</b></p>
            <p>đź”Ą Respect: <b>${profileData.respect}</b> pkt</p>
            <p>đź‘Ą Klan: <b>${profileData.clan}</b></p>

            <hr style="border: 1px solid #0f0; margin: 15px 0;">
            <h4>Terytorium:</h4>
            ${territoryDetailsHtml}
            <p>đźź© Klastry: <b>${territoryStats.clusters_count || 0}</b></p>
            <p>đź“ Powierzchnia: <b>${totalArea} mÂ˛</b></p>
            <p>â¬† Do nastÄ™pnego levela: <b>${areaToNext} mÂ˛</b></p>
            <p>đźŹŤď¸Ź ZasiÄ™g motocykla: <b>${actionRange} m</b></p>
            
            <hr style="border: 1px solid #0f0; margin: 15px 0;">

            <p>đź“¦ Inventory: <b>${profileData.inventory.length}</b> aplikacji</p>
            <p>đź“Ť Pozycja: <b>lat: ${profileData.curently_possition.lat}, lng: ${profileData.curently_possition.lng}</b></p>

            <hr style="border: 1px solid #0f0; margin: 15px 0;">
            <h4>Zabezpieczenia:</h4>
            <div class="profile-security-status"></div>
            <div class="profile-security-list">${securityControls}</div>

            <hr style="border: 1px solid #0f0; margin: 15px 0;">
            <button class="profile-logout-btn" type="button">Logout</button>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());
    term.querySelector('.profile-logout-btn').addEventListener('click', () => {
        window.location.href = '/logout';
    });

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
                        const row = item.closest('.profile-security-row');
                        row.querySelector('.profile-security-state').textContent = item.checked ? 'ON' : 'OFF';
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
        if (!res.ok) throw new Error("NieprawidĹ‚owy response");
        const data = await res.json();
        return data;
    } catch (err) {
        console.error("âťŚ BĹ‚Ä…d pobierania profilu uĹĽytkownika:", err);
        return null;
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
            <span class="close-btn" style="float:right; cursor:pointer;">âś–</span>
        </div>
        <form class="appforge-form">
            <div class="appforge-grid">
                <label>Nazwa<input name="name" maxlength="32" required placeholder="np. NullTrace"></label>
                <label>Typ<input name="type" value="scanner" placeholder="scanner"></label>
                <label>Ikonka
                    <span class="appforge-icon-row">
                        <input name="icon" maxlength="16" value="đź› ď¸Ź" placeholder="đź› ď¸Ź">
                        <span class="appforge-icon-preview">đź› ď¸Ź</span>
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
                <label>levels[0].title<input name="level_title" placeholder="Wybierz tryb dziaĹ‚ania"></label>
                <label>levels[0].text<textarea name="button_text" rows="3" placeholder="Opis wyboru dla gracza"></textarea></label>
                <label>levels[0].options<textarea name="button_options" rows="5" placeholder="Label|effect|price&#10;Recon|risk_level=10,access_level=1|90&#10;Disable firewall|firewall=false|140"></textarea></label>
            `;
        } else {
            levelFields.innerHTML = `
                <h4>Levels: progressbar_random</h4>
                <label>levels[0].title<input name="level_title" placeholder="Wykonywanie operacji"></label>
                <label>levels[0].steps<textarea name="progress_steps" rows="5" placeholder="Jedna linia = jeden krok progressbara"></textarea></label>
                <label>levels[0].result_success<input name="result_success" placeholder="Operacja zakoĹ„czona powodzeniem."></label>
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
        title: "Nadaj narzedziu tozsamosc",
        subtitle: "Pierwszy sygnal dla gracza i katalogu Googleplex.",
        description: "Nazwa, ikona i opis mowia, czym jest aplikacja zanim ktokolwiek spojrzy w jej kontrakt.",
        educational_note: "Profesjonalne narzedzia tej klasy sa rozpoznawalne po celu, zakresie i wiarygodnym opisie.",
        gameplay_hint: "Cena jest punktem startu. Runtime moze pokazac sugerowana wartosc w podgladzie balansu."
    },
    {
        title: "Wybierz rodzine narzedzia",
        subtitle: "Rodzina zawedza dalsze decyzje.",
        description: "Scanner, Exploit i Sniffer opisuja intencje gameplayowa, a nie realna instrukcje dzialania.",
        educational_note: "Administratorzy i zespoly bezpieczenstwa uzywaja podobnych klas rozwiazan do rozpoznania, kontroli i obserwacji systemow.",
        gameplay_hint: "Wybrana rodzina filtruje akcje, operacje i zasoby w kolejnych krokach."
    },
    {
        title: "Wskaz obiekt zainteresowania",
        subtitle: "Cel decyduje, jakie opcje maja sens.",
        description: "Inaczej projektuje sie narzedzie dla pojazdu, inaczej dla kamery, a inaczej dla routera.",
        educational_note: "W swiecie CHAOS kazdy obiekt ma inne cyfrowe zmysly: lokalizacje, obraz, sygnal, logi albo dostep.",
        gameplay_hint: "Po wyborze celu kreator ukrywa niepasujace operacje i informacje."
    },
    {
        title: "Okresl miejsce uruchomienia",
        subtitle: "Mapa, desktop albo oba tryby.",
        description: "Nie kazde narzedzie musi byc widoczne w menu mapy. Desktop moze dzialac na oznaczony cel.",
        educational_note: "To rozroznienie przypomina prace z kontekstem: czasem dzialasz na obiekcie w terenie, czasem na juz wybranym celu.",
        gameplay_hint: "Tryb desktopowy moze nie miec akcji mapy. Tryb mapowy powinien miec jawne map_actions."
    },
    {
        title: "Zdecyduj, co narzedzie ma zrobic",
        subtitle: "To jest serce kontraktu operacji.",
        description: "Wybierasz efekt gameplayowy: sledzenie, stream, odczyt, zaklocenie albo implant.",
        educational_note: "Nie chodzi o realne komendy. Chodzi o opis skutku w symulowanym swiecie gry.",
        gameplay_hint: "Operacja moze zyc na mapie, miec timer, produkowac dane albo tylko wspierac inny proces."
    },
    {
        title: "Wybierz informacje, ktorych szuka",
        subtitle: "Dane sa paliwem ekonomii CHAOS.",
        description: "Zasoby okreslaja, jaki typ pliku albo stanu moze powstac po operacji.",
        educational_note: "Podobne klasy narzedzi w realnym swiecie pomagaja zrozumiec, jakie sygnaly i metadane istnieja w systemach.",
        gameplay_hint: "Nie kazdy zasob jest sprzedawalny. `internal_recon_state` moze tylko przygotowac dalsze dzialanie."
    },
    {
        title: "Ustal ryzyko i zaleznosci",
        subtitle: "Kazde narzedzie ma slady i wymagania.",
        description: "Ten krok opisuje, z czym narzedzie koliduje, co wylacza i jakie warunki powinny byc spelnione.",
        educational_note: "Swiadome projektowanie narzedzia polega tez na rozumieniu ograniczen, nie tylko mozliwosci.",
        gameplay_hint: "To nadal sa pola kontraktu gry. Nie tworza realnych instrukcji ani nowego systemu ryzyka."
    },
    {
        title: "Sprawdz kontrakt przed publikacja",
        subtitle: "Podglad laczy decyzje w jedna aplikacje.",
        description: "Tutaj widzisz, jak wybor rodziny, celu, dzialania i danych zamienia sie w app contract.",
        educational_note: "Dobry projekt narzedzia powinien byc czytelny bez zagladania w kod.",
        gameplay_hint: "Waga, jakosc, niezawodnosc i cena sugerowana sa liczone przez runtime."
    },
    {
        title: "Opublikuj w Googleplex",
        subtitle: "Ten sam katalog, ten sam runtime.",
        description: "Publikacja uzywa istniejacego endpointu i trafia do tego samego Googleplexa co inne aplikacje.",
        educational_note: "CHAOS traktuje narzedzie jak element ekosystemu: projekt, publikacja, instalacja, uzycie i uninstall.",
        gameplay_hint: "Po publikacji aplikacje kupujesz i instalujesz tak jak inne narzedzia."
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
        camera_stream: "Ogladaj obraz z kamery",
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
        description: "NarzÄ™dzie recon dziaĹ‚ajÄ…ce z mapy i z desktopu, bez wchodzenia w Ĺ›cieĹĽkÄ™ exploit/sniffer.",
        map_actions: ["scan_ports", "trace", "trace_gps", "trace_device", "scan_hotspots", "camera_stream"],
        operation_types: ["generic_trace", "vehicle_tracking", "device_tracking", "wifi_scanner", "camera_stream"],
        resource_types: ["internal_recon_state", "gps_logs", "location_history", "device_logs", "camera_dump", "wifi_networks", "hotspot_database"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "person", "phone", "venue"]
    }
};

const CREATOR_EXPLOIT_MODE_PRESETS = {
    map: {
        label: "Exploit mapowy",
        description: "Symulowane wykorzystanie sĹ‚aboĹ›ci celu uruchamiane z mapy w Ĺ›wiecie gry.",
        map_actions: ["exploit", "camera_shutdown", "install_sniffer", "audio_hack", "car_hack"],
        operation_types: ["camera_shutdown", "persistent_sniffer", "audio_interference", "vehicle_ecu"],
        resource_types: ["internal_recon_state", "financial_records", "credentials", "vehicle_diagnostics"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "venue"]
    },
    desktop: {
        label: "Exploit desktopowy na oznaczony cel",
        description: "Symulowany wpĹ‚yw na aktualny aimed_target bez automatycznego podpinania do menu mapy.",
        map_actions: [],
        operation_types: ["camera_shutdown", "audio_interference", "vehicle_ecu"],
        resource_types: ["internal_recon_state", "vehicle_diagnostics"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "venue"]
    },
    hybrid: {
        label: "Exploit hybrydowy",
        description: "NarzÄ™dzie dziaĹ‚ajÄ…ce z mapy i desktopu, nadal w ramach symulowanego Ĺ›wiata CHAOS.",
        map_actions: ["exploit", "camera_shutdown", "install_sniffer", "audio_hack", "car_hack"],
        operation_types: ["camera_shutdown", "persistent_sniffer", "audio_interference", "vehicle_ecu"],
        resource_types: ["internal_recon_state", "financial_records", "credentials", "vehicle_diagnostics"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "vehicle", "venue"]
    }
};

const CREATOR_SNIFFER_MODE_PRESETS = {
    map: {
        label: "Sniffer mapowy",
        description: "Symulowane zbieranie sygnaĹ‚Ăłw lub danych przez operacjÄ™ uruchamianÄ… z mapy.",
        map_actions: ["sniff", "mic_sniff", "atm_logs", "install_sniffer", "camera_stream"],
        operation_types: ["persistent_sniffer", "microphone_sniffer", "atm_log_extraction", "camera_stream"],
        resource_types: ["credentials", "financial_records", "atm_dump", "audio_transcript", "camera_dump", "video_material", "device_logs", "internal_recon_state"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "person", "phone", "venue"]
    },
    desktop: {
        label: "Sniffer desktopowy na oznaczony cel",
        description: "Symulowany podglÄ…d sygnaĹ‚Ăłw aktualnego aimed_target bez obowiÄ…zkowego menu mapy.",
        map_actions: [],
        operation_types: ["persistent_sniffer", "microphone_sniffer", "atm_log_extraction", "camera_stream"],
        resource_types: ["credentials", "financial_records", "atm_dump", "audio_transcript", "camera_dump", "video_material", "device_logs", "internal_recon_state"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "person", "phone", "venue"]
    },
    hybrid: {
        label: "Sniffer hybrydowy",
        description: "NarzÄ™dzie obserwacji dziaĹ‚ajÄ…ce z mapy i z desktopu w ramach operacji gry.",
        map_actions: ["sniff", "mic_sniff", "atm_logs", "install_sniffer", "camera_stream"],
        operation_types: ["persistent_sniffer", "microphone_sniffer", "atm_log_extraction", "camera_stream"],
        resource_types: ["credentials", "financial_records", "atm_dump", "audio_transcript", "camera_dump", "video_material", "device_logs", "internal_recon_state"],
        target_types: ["poi", "camera", "atm", "server", "router", "player", "pillar", "person", "phone", "venue"]
    }
};

const CREATOR_TOOL_FAMILY_PRESETS = {
    scanner_recon: {
        label: "Scanner / Recon",
        boxTitle: "Gdzie dziala rozpoznanie?",
        defaultType: "scanner",
        safetyText: "Narzędzia rozpoznania sluza do poznania powierzchni celu w swiecie gry. Wizard buduje swiadomosc, nie realne instrukcje.",
        desktopMapNote: "Scanner desktopowy moze nie miec akcji mapy. Dziala na aktualny aimed_target.",
        mapNote: "Wybierz tylko te akcje mapy, ktore aplikacja faktycznie obsluzy.",
        modes: CREATOR_SCANNER_MODE_PRESETS
    },
    exploit: {
        label: "Exploit",
        boxTitle: "Gdzie dziala exploit?",
        defaultType: "exploit",
        safetyText: "Exploit w CHAOS oznacza symulowany wplyw na slabosc systemu w swiecie gry. Opisuj efekt gameplayowy, nie technike.",
        desktopMapNote: "Exploit desktopowy moze nie miec akcji mapy. Dziala na aktualny aimed_target.",
        mapNote: "Wybierz akcje mapy tylko wtedy, gdy narzedzie ma byc widoczne w menu mapy.",
        modes: CREATOR_EXPLOIT_MODE_PRESETS
    },
    sniffer: {
        label: "Sniffer",
        boxTitle: "Gdzie dziala sniffer?",
        defaultType: "sniffer",
        safetyText: "Sniffer w CHAOS oznacza symulowana obserwacje sygnalow lub danych w ramach operacji gry.",
        desktopMapNote: "Sniffer desktopowy moze nie miec akcji mapy. Dziala na aktualny aimed_target.",
        mapNote: "Wybierz akcje mapy tylko wtedy, gdy sniffer ma byc uruchamiany z mapy.",
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
        familySelect.parentElement.childNodes[0].textContent = "Jaki rodzaj narzedzia chcesz stworzyc? ";
    }
    const typeSelect = term.querySelector('[name="type"]');
    if (typeSelect?.parentElement) {
        typeSelect.parentElement.childNodes[0].textContent = "Jak ma byc opisane w katalogu? ";
    }
    const detects = term.querySelector('[name="detects"]');
    if (detects?.parentElement) {
        detects.parentElement.childNodes[0].textContent = "Jakie slady lub sygnaly rozpoznaje? ";
        detects.placeholder = "np. otwarte uslugi, ruch celu";
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
        ['[data-creator-panel="2"] .appforge-fieldset h4', "Jakim obiektem chcesz sie zajac?"],
        ['[data-creator-panel="3"] .appforge-fieldset h4', "Skad gracz ma uruchamiac narzedzie?"],
        ['[data-creator-panel="4"] .appforge-fieldset h4', "Co ma zrobic Twoje narzedzie?"],
        ['[data-creator-panel="5"] .appforge-fieldset h4', "Jakich informacji ma szukac?"],
        ['[data-creator-panel="6"] .appforge-fieldset:nth-of-type(1) h4', "Z czym moze kolidowac?"],
        ['[data-creator-panel="6"] .appforge-fieldset:nth-of-type(2) h4', "Co powinno byc wylaczone?"],
        ['[data-creator-panel="6"] .appforge-fieldset:nth-of-type(3) h4', "Co narzedzie potrafi wylaczyc?"],
        ['[data-creator-panel="6"] .appforge-fieldset:nth-of-type(4) h4', "Na co wplywa po stronie gracza?"]
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
        if (familyTitle) familyTitle.textContent = "Tryb narzÄ™dzia";
        if (familyNote) familyNote.textContent = "Wybierz Ĺ›cieĹĽkÄ™ kreatora, ĹĽeby zawÄ™ziÄ‡ kontrakt do sensownych pĂłl.";
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
                <h4>Typ narzÄ™dzia</h4>
                <label>ĹšcieĹĽka kreatora
                    <select name="tool_family">
                        <option value="custom">OgĂłlne narzÄ™dzie</option>
                        ${Object.entries(CREATOR_TOOL_FAMILY_PRESETS).map(([value, preset]) => `
                            <option value="${escapeHTML(value)}">${escapeHTML(preset.label)}</option>
                        `).join("")}
                    </select>
                </label>
                <div class="creator-scanner-box" data-creator-family-box hidden>
                    <label><span data-creator-family-title>Tryb narzÄ™dzia</span>
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
                <h4>Ĺšrodowisko dziaĹ‚ania</h4>
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
                <p class="creator-step-note" data-creator-map-note>Wybierz akcje mapy tylko wtedy, gdy narzÄ™dzie ma byÄ‡ uruchamiane z menu mapy.</p>
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
                    <span>Quality</span><b>profil twĂłrcy</b>
                    <span>Reliability</span><b>profil twĂłrcy</b>
                </div>
                <pre class="creator-contract-preview" data-creator-contract-preview></pre>
                ${creatorPanelNav(true, true)}
            </section>
            <section class="creator-step-panel" data-creator-panel="8" hidden>
                <h4>Publikacja</h4>
                <p class="creator-step-note">Publikacja uĹĽywa istniejÄ…cego endpointu /api/apps/generate i katalogu Googleplex.</p>
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
    toggle.title = 'Wybierz ikonÄ™';

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
            <span class="close-btn" style="float:right; cursor:pointer;">x</span>
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
        icon: "đź’¸",
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
        icon: "đź‘‹",
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
        icon: "đź›ˇď¸Ź",
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
        icon: "đź“ś",
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
        icon: "đź§ą",
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
                                <b>Risk ${"â…".repeat(item.risk_level)}${"â†".repeat(Math.max(0, 5 - item.risk_level))}</b>
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
            <strong>${escapeHTML(project.icon || 'đź§Ş')} ${escapeHTML(project.name)}</strong>
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
        <strong>${escapeHTML(selected.icon || 'đź§Ş')} ${escapeHTML(selected.name)}</strong>
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
            <span class="close-btn" style="float:right; cursor:pointer;">x</span>
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

async function selectMapActionTool(appId) {
    const selection = window.activeToolSelection;
    if (!selection || !selection.pending_action) {
        addSystemMessage("warning", "đź› ď¸Ź NarzÄ™dzia", "Brak aktywnej akcji mapy.");
        return;
    }

    const app = selection.matching_apps.find(item => String(item.id || "") === String(appId || ""));
    if (!app) {
        addSystemMessage("warning", "đź› ď¸Ź NarzÄ™dzia", "To narzÄ™dzie nie pasuje do aktywnej akcji.");
        return;
    }

    try {
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
            addSystemMessage("warning", "đź› ď¸Ź NarzÄ™dzia", data.status || "Nie udaĹ‚o siÄ™ uruchomiÄ‡ narzÄ™dzia.");
            return;
        }

        window.activeToolSelection = null;
        addSystemMessage("success", "đź› ď¸Ź NarzÄ™dzie", data.status || `Uruchomiono ${app.name || app.id}.`);
        if (typeof refreshToolbarProfile === "function") refreshToolbarProfile();
        if (typeof notifyOpenMapsOperationsChanged === "function") notifyOpenMapsOperationsChanged();
    } catch (err) {
        console.error("BĹ‚Ä…d wyboru narzÄ™dzia:", err);
        addSystemMessage("danger", "đź› ď¸Ź NarzÄ™dzia", "BĹ‚Ä…d poĹ‚Ä…czenia podczas wyboru narzÄ™dzia.");
    }
}

window.openToolSelectionForMapAction = async function(payload) {
    window.activeToolSelection = normalizeToolSelectionPayload(payload || {});
    const title = window.activeToolSelection.map_action_id || window.activeToolSelection.canonical_action || "akcja";
    addSystemMessage("info", "đź› ď¸Ź WybĂłr narzÄ™dzia", `Wybierz narzÄ™dzie dla: ${title}`);
    await createFileManager({ toolSelection: window.activeToolSelection });
};

async function createFileManager(options = {}) {
    // Jeden FileManager na raz
    const existing = document.querySelector(`.terminal[data-app="files"]`);
    if (existing) {
        bringWindowToFront(existing);
        if (options.toolSelection) {
            window.activeToolSelection = normalizeToolSelectionPayload(options.toolSelection);
            const managerId = existing.dataset.fileManagerId || window.fileManagerTerminalId;
            if (managerId && typeof window.openFolderInManager === "function") {
                window.openFolderInManager(managerId, "tools");
            }
        }
        return existing;
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
        'social-media'
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
        'social-media': 'Social'
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
        'social-media': 'SOC'
    };
    const getFolderLabel = (folderName) => folderLabels[folderName] || folderName;
    const getFolderIcon = (folderName) => folderIcons[folderName] || fileManagerUiIcons.file;
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
            MenedĹĽer plikĂłw
            <span class="close-btn" style="float:right; cursor:pointer;">âś–</span>
        </div>
        <div style="padding: 10px; background: #111; color: #0f0; flex:1; overflow-y:auto; font-family: monospace;" id="${terminalId}-content">
            <h3>Katalogi:</h3>
            <div id="${terminalId}-folders"></div>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    const fileManagerTitle = term.querySelector('.title-bar');
    if (fileManagerTitle && fileManagerTitle.firstChild) fileManagerTitle.firstChild.nodeValue = 'MenedĹĽer plikĂłw ';
    const fileManagerClose = term.querySelector('.close-btn');
    if (fileManagerClose) fileManagerClose.textContent = 'x';
    const fileManagerContent = document.getElementById(`${terminalId}-content`);
    const fileManagerObserver = new MutationObserver(() => polishFileManagerText(fileManagerContent));
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
        addSystemMessage("danger", "đź“‚ Pliki", "âťŚ BĹ‚Ä…d Ĺ‚adowania plikĂłw");
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
        const capacity = Math.max(1, storageSummary.capacity || 1);
        const used = Math.max(0, storageSummary.used || 0);
        const percent = Math.max(0, Math.min(100, Math.round((used / capacity) * 100)));
        const warning = storageSummary.overLimit ? '<span class="file-manager-storage-warning">ponad limit miÄ™kki</span>' : '';
        return `
            <div class="file-manager-storage">
                <div class="file-manager-storage-top">
                    <span>Dysk</span>
                    <b>${escapeHTML(formatStorageSize(used, storageSummary.unit))} / ${escapeHTML(formatStorageSize(storageSummary.capacity, storageSummary.unit))}</b>
                </div>
                <div class="file-manager-storage-bar"><span style="width:${percent}%"></span></div>
                ${warning}
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
            folder.innerHTML = `<span style="cursor:pointer;" onclick="window.openFolderInManager('${terminalId}', '${dir}')">đź“‚ <b>${dir}</b></span>`;
            folder.innerHTML = `<span style="cursor:pointer;" onclick="window.openFolderInManager('${terminalId}', '${dir}')">Ä‘Ĺşâ€śâ€š <b>${escapeHTML(folderLabel)}</b> <span style="color:#6fbf89;">/${escapeHTML(dir)}</span></span>`;
            folder.innerHTML = `<span style="cursor:pointer;" onclick="window.openFolderInManager('${terminalId}', '${dir}')">[DIR] <b>${escapeHTML(folderLabel)}</b> <span style="color:#6fbf89;">/${escapeHTML(dir)}</span></span>`;
            foldersDiv.appendChild(folder);
        });
    }

    window.openFolderInManager = (id, folderName) => {
        const container = document.getElementById(`${id}-content`);
        const fileList = files[folderName] || [];
        const renderedToolAppIds = new Set();

        let list = "";
        fileList.forEach(fileEntry => {
            const filename = typeof fileEntry === "string" ? fileEntry : String(fileEntry.name || fileEntry.filename || "plik");
            const matchingTool = folderName === "tools" ? getToolSelectionAppForFile(filename) : null;
            const installedTool = folderName === "tools" ? installedToolAppsByFile.get(filename) : null;
            const toolMeta = matchingTool || installedTool;
            const isMatchingTool = Boolean(matchingTool);
            if (isMatchingTool) renderedToolAppIds.add(String(matchingTool.id || ""));
            // Ikonka per folder
            let icon = "đź“„";
            if (folderName === "tools") icon = "đź”§";
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
            if (folderName === "pictures") icon = "đź–Ľď¸Ź";
            if (folderName === "download") icon = "â¬‡ď¸Ź";
            if (folderName === "social-media") icon = "đź’¬";

            icon = getFolderIcon(folderName);

            // Klasa pliku
            let fileClass = "file-manager-file";
            if (folderName === "tools") fileClass += " file-manager-tool";
            if (isMatchingTool) fileClass += " file-manager-tool-match";

            // W tools â€“ dodaj Uninstall
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
        container.innerHTML = `
            ${storageMeterHTML()}
            <h3>Katalogi:</h3>
            <div id="${id}-folders"></div>
        `;
        renderFolders();
    };

    // Klik w dowolny plik â€” symulacja otwarcia/uruchomienia
    window.runFile = (folderName, filename) => {
        console.log(`[RUN] Plik uruchomiony: ${folderName}/${filename}`);
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
                        <p>JakoĹ›Ä‡: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                        <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                        <p>Przewidywana wartoĹ›Ä‡: <b>${escapeHTML(fileValuePreview)}</b></p>
                        <p>KompletnoĹ›Ä‡: <b>${escapeHTML(String(summary.completeness_percent ?? completeness.percent ?? 0))}%</b></p>
                        <p>Tier: <b>${escapeHTML(summary.tier || completeness.tier || 'basic')}</b></p>
                        <div style="height:10px;border:1px solid #0f0;background:#031403;margin:8px 0 12px;">
                            <div style="height:100%;width:${Math.max(0, Math.min(100, Number(summary.completeness_percent ?? completeness.percent ?? 0)))}%;background:#38ff80;"></div>
                        </div>
                        <h4>Zasoby w paczce</h4>
                        <ul>
                            ${resources.map(item => `<li>${escapeHTML(item)}</li>`).join('') || '<li>Brak zasobĂłw.</li>'}
                        </ul>
                        <p>JakoĹ›Ä‡: <b>${escapeHTML(metadata.quality || '-')}</b></p>
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
                        <p>KompletnoĹ›Ä‡: <b>${escapeHTML(String(completenessPercent))}% / ${escapeHTML(completenessTier)}</b></p>
                        <p>JakoĹ›Ä‡: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                        <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                        <p>Przewidywana wartoĹ›Ä‡: <b>${escapeHTML(fileValuePreview)}</b></p>
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
                            <div style="font-size:20px;margin-top:8px;">â€˘â€˘â€˘â€˘ â€˘â€˘â€˘â€˘ â€˘â€˘â€˘â€˘ â€˘â€˘â€˘â€˘</div>
                        </div>
                        <p>Plik: <b>${escapeHTML(filename)}</b></p>
                        <p>Katalog: <b>${escapeHTML(fileEntry.directory || folderName)}</b></p>
                        <p>Operacja: <b>${escapeHTML(fileEntry.operation_id || metadata.operation_id || '-')}</b></p>
                        <p>KompletnoĹ›Ä‡: <b>${escapeHTML(String(completenessPercent))}% / ${escapeHTML(completenessTier)}</b></p>
                        <p>JakoĹ›Ä‡: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                        <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                        <p>Przewidywana wartoĹ›Ä‡: <b>${escapeHTML(fileValuePreview)}</b></p>
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
                        <p>KompletnoĹ›Ä‡: <b>${escapeHTML(String(completenessPercent))}% / ${escapeHTML(completenessTier)}</b></p>
                        <p>JakoĹ›Ä‡: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                        <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                        <p>Przewidywana wartoĹ›Ä‡: <b>${escapeHTML(fileValuePreview)}</b></p>
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
                    <p>KompletnoĹ›Ä‡: <b>${escapeHTML(String(completenessPercent))}% / ${escapeHTML(completenessTier)}</b></p>
                    <p>JakoĹ›Ä‡: <b>${escapeHTML(String(qualityScore))}/100</b></p>
                    <p>Braki: <b>${escapeHTML(missingFields.length ? missingFields.join(', ') : 'brak')}</b></p>
                    <p>Przewidywana wartoĹ›Ä‡: <b>${escapeHTML(fileValuePreview)}</b></p>
                    <p>Checkpointy: <b>${escapeHTML(String(metadata.checkpoint_count ?? checkpoints.length))}</b></p>
                    <p>JakoĹ›Ä‡: <b>${escapeHTML(metadata.quality || '-')}</b> | DokĹ‚adnoĹ›Ä‡: <b>${escapeHTML(metadata.accuracy || '-')}</b></p>
                    <table style="width:100%;border-collapse:collapse;margin-top:10px;">
                        <thead>
                            <tr>
                                <th style="text-align:left;border-bottom:1px solid #0f0;">#</th>
                                <th style="text-align:left;border-bottom:1px solid #0f0;">Czas</th>
                                <th style="text-align:left;border-bottom:1px solid #0f0;">Lat</th>
                                <th style="text-align:left;border-bottom:1px solid #0f0;">Lng</th>
                            </tr>
                        </thead>
                        <tbody>${checkpointRows || '<tr><td colspan="4">Brak checkpointĂłw.</td></tr>'}</tbody>
                    </table>
                </div>
            `;
            return;
        }
        addSystemMessage("info", "đź“ Otwieranie pliku", `(Symulacja) Otwierasz plik: ${filename}`);
    };
    window.selectMapActionTool = selectMapActionTool;
    window.uninstallApp = async (appName, appId = "") => {
        console.log(`[UNINSTALL] Ĺ»Ä…danie odinstalowania: ${appName}`);
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
                throw new Error(data.message || 'Nie udaĹ‚o siÄ™ odinstalowaÄ‡ aplikacji.');
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
            await refreshToolbarProfile().catch(() => null);
            addSystemMessage("warning", "Deinstalacja", data.message || `Odinstalowano ${appName}`);
        } catch (err) {
            addSystemMessage("danger", "Deinstalacja", err.message || "Nie udaĹ‚o siÄ™ odinstalowaÄ‡ aplikacji.");
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
    term.dataset.app = "email"; // đź”§ TO DODAJ
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
            Skrzynka mailowa
            <span class="close-btn" style="float:right; cursor:pointer;">âś–</span>
        </div>
        <div style="display: flex; flex: 1; background: #111; color: #0f0; font-family: monospace;">
            <!-- WiadomoĹ›ci -->
            <div style="width: 60%; border-right: 1px solid #0f0; padding: 10px; overflow-y:auto;">
                <h3>đź“Ą Odebrane</h3>
                <div id="${terminalId}-message-list"></div>
                <hr>
                <div id="${terminalId}-message-content" style="margin-top:10px; color: #fff;"></div>
            </div>
            <!-- Znajomi -->
            <div style="width: 40%; padding: 10px;">
                <h3>đź‘Ą Znajomi</h3>
                <div id="${terminalId}-friends"></div>
            </div>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    // Po osadzeniu HTML â€“ teraz selektory zadziaĹ‚ajÄ…
    const msgList = term.querySelector(`#${terminalId}-message-list`);
    const msgContent = term.querySelector(`#${terminalId}-message-content`);
    const friendsList = term.querySelector(`#${terminalId}-friends`);

    // Ĺadowanie wiadomoĹ›ci
    fetch('/messages.json')
        .then(res => res.json())
        .then(messages => {
            messages.forEach((msg) => {
                const div = document.createElement('div');
                div.innerHTML = `đź“¨ <b>${msg.from}</b>: ${msg.subject}`;
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

    // Ĺadowanie znajomych
    fetch('/friends.json')
        .then(res => res.json())
        .then(friends => {
            friends.forEach(friend => {
                const div = document.createElement('div');
                const color = friend.status === "online" ? "#0f0" : "#666";
                div.innerHTML = `đź‘¤ <span style="color:${color};">${friend.name}</span> (${friend.status})`;
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
            Skrzynka mailowa
            <span class="close-btn" style="float:right; cursor:pointer;">x</span>
        </div>
        <div class="mail-shell">
            <div class="mail-sidebar">
                <div class="mail-section-title">Kontakty</div>
                <form id="${terminalId}-contact-form" class="mail-contact-form">
                    <input id="${terminalId}-contact-input" type="text" placeholder="Nick znajomego" autocomplete="off">
                    <button type="submit">Dodaj</button>
                </form>
                <button id="${terminalId}-group-btn" class="mail-thread active" type="button">
                    <span><span id="${terminalId}-group-dot" class="mail-unread-dot" style="display:none;"></span># grupa</span>
                    <small id="${terminalId}-group-meta">0 online</small>
                </button>
                <div id="${terminalId}-contacts" class="mail-contact-list"></div>
                <div id="${terminalId}-pending-wrap" class="mail-pending-wrap" style="display:none;">
                    <div class="mail-section-title">Oczekujace</div>
                    <div id="${terminalId}-pending" class="mail-contact-list"></div>
                </div>
            </div>
            <div class="mail-main">
                <div class="mail-header">
                    <div>
                        <div id="${terminalId}-chat-title" class="mail-chat-title"># grupa</div>
                        <div id="${terminalId}-chat-subtitle" class="mail-chat-subtitle">Czat grupowy</div>
                    </div>
                    <div class="mail-header-actions">
                        <button id="${terminalId}-accept-contact" type="button" style="display:none;">Dodaj kontakt</button>
                        <button id="${terminalId}-remove-contact" type="button" class="mail-danger" style="display:none;">Usun kontakt</button>
                    </div>
                </div>
                <div id="${terminalId}-messages" class="mail-messages"></div>
                <form id="${terminalId}-message-form" class="mail-message-form">
                    <input id="${terminalId}-message-input" type="text" placeholder="Napisz wiadomosc..." autocomplete="off">
                    <button type="submit">Wyslij</button>
                </form>
            </div>
        </div>
    `;

    document.body.appendChild(term);
    makeDraggable(term);
    term.querySelector('.close-btn').addEventListener('click', () => term.remove());

    const contactsBox = term.querySelector(`#${terminalId}-contacts`);
    const pendingWrap = term.querySelector(`#${terminalId}-pending-wrap`);
    const pendingBox = term.querySelector(`#${terminalId}-pending`);
    const messagesBox = term.querySelector(`#${terminalId}-messages`);
    const chatTitle = term.querySelector(`#${terminalId}-chat-title`);
    const chatSubtitle = term.querySelector(`#${terminalId}-chat-subtitle`);
    const groupBtn = term.querySelector(`#${terminalId}-group-btn`);
    const groupDot = term.querySelector(`#${terminalId}-group-dot`);
    const groupMeta = term.querySelector(`#${terminalId}-group-meta`);
    const acceptBtn = term.querySelector(`#${terminalId}-accept-contact`);
    const removeBtn = term.querySelector(`#${terminalId}-remove-contact`);
    const contactForm = term.querySelector(`#${terminalId}-contact-form`);
    const contactInput = term.querySelector(`#${terminalId}-contact-input`);
    const messageForm = term.querySelector(`#${terminalId}-message-form`);
    const messageInput = term.querySelector(`#${terminalId}-message-input`);

    let currentUser = "";
    let contacts = [];
    let pendingThreads = [];
    let unreadCounts = { group: 0, direct: {} };
    let groupActiveCount = 0;
    let currentChat = { scope: "group", peer: "global" };
    const requestedInitialPeer = window.pendingEmailPeer || "";
    window.pendingEmailPeer = "";

    const isKnownContact = (name) => contacts.some(contact => contact.name === name);
    const unreadFor = (name) => (unreadCounts.direct && unreadCounts.direct[name]) || 0;

    const setActiveThread = () => {
        term.querySelectorAll('.mail-thread').forEach(el => el.classList.remove('active'));
        groupDot.style.display = unreadCounts.group > 0 ? "inline-block" : "none";
        groupMeta.textContent = `${groupActiveCount} online`;
        if (currentChat.scope === "group") {
            groupBtn.classList.add('active');
            chatTitle.textContent = "# grupa";
            chatSubtitle.textContent = `Czat grupowy - ${groupActiveCount} online`;
            acceptBtn.style.display = "none";
            removeBtn.style.display = "none";
            return;
        }

        const btn = Array.from(term.querySelectorAll('.mail-thread'))
            .find(el => el.dataset.contactName === currentChat.peer);
        if (btn) btn.classList.add('active');
        chatTitle.textContent = currentChat.peer;
        const known = isKnownContact(currentChat.peer);
        chatSubtitle.textContent = known ? "Czat indywidualny" : "Nieznany kontakt";
        acceptBtn.style.display = known ? "none" : "inline-block";
        removeBtn.style.display = known ? "inline-block" : "none";
    };

    const renderContacts = () => {
        contactsBox.innerHTML = "";
        contacts.forEach(contact => {
            const btn = document.createElement('button');
            btn.type = "button";
            btn.className = "mail-thread";
            btn.dataset.contactName = contact.name;
            const statusClass = contact.status === "online" ? "online" : "offline";
            const unread = unreadFor(contact.name);
            btn.innerHTML = `
                <span><span class="mail-unread-dot" style="display:${unread ? "inline-block" : "none"};"></span>${escapeHTML(contact.name)}</span>
                <small class="${statusClass}">${escapeHTML(contact.status || "offline")}</small>
            `;
            btn.addEventListener('click', () => {
                currentChat = { scope: "direct", peer: contact.name };
                setActiveThread();
                loadMessages();
            });
            contactsBox.appendChild(btn);
        });

        pendingBox.innerHTML = "";
        pendingWrap.style.display = pendingThreads.length ? "block" : "none";
        pendingThreads.forEach(thread => {
            const btn = document.createElement('button');
            btn.type = "button";
            btn.className = "mail-thread pending";
            btn.dataset.contactName = thread.name;
            const unread = unreadFor(thread.name);
            btn.innerHTML = `
                <span><span class="mail-unread-dot" style="display:${unread ? "inline-block" : "none"};"></span>${escapeHTML(thread.name)}</span>
                <small class="pending">nowa rozmowa</small>
            `;
            btn.addEventListener('click', () => {
                currentChat = { scope: "direct", peer: thread.name };
                setActiveThread();
                loadMessages();
            });
            pendingBox.appendChild(btn);
        });
        setActiveThread();
    };

    const renderMessages = (messages) => {
        messagesBox.innerHTML = "";
        if (!messages.length) {
            messagesBox.innerHTML = `<div class="mail-empty">Brak wiadomosci. Zacznij rozmowe.</div>`;
            return;
        }

        messages.forEach(msg => {
            const item = document.createElement('div');
            const own = msg.sender === currentUser;
            item.className = `mail-message ${own ? "own" : ""}`;
            const subject = msg.subject ? `<div class="mail-message-subject">${escapeHTML(msg.subject)}</div>` : "";
            item.innerHTML = `
                <div class="mail-message-meta">${escapeHTML(msg.sender)} - ${escapeHTML(msg.created_at || "")}</div>
                ${subject}
                <div>${escapeHTML(msg.body)}</div>
            `;
            messagesBox.appendChild(item);
        });
        messagesBox.scrollTop = messagesBox.scrollHeight;
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
        renderContacts();
        renderMessages(data.messages || []);
    };

    const openDirectChat = async (name) => {
        if (!name) return;
        currentChat = { scope: "direct", peer: name };
        setActiveThread();
        await loadMessages();
    };

    const bootstrap = async () => {
        if (!document.body.contains(term)) return;
        const res = await fetch('/api/mail/bootstrap');
        const data = await res.json();
        currentUser = data.username || "";
        contacts = data.contacts || [];
        pendingThreads = data.pending_threads || [];
        unreadCounts = data.unread_counts || unreadCounts;
        groupActiveCount = data.group_active_count ?? groupActiveCount;
        renderContacts();
        if (requestedInitialPeer) {
            await openDirectChat(requestedInitialPeer);
            return;
        }
        await loadMessages();
    };

    const refreshThreads = async () => {
        if (!document.body.contains(term)) return;
        const res = await fetch('/api/mail/bootstrap');
        const data = await res.json();
        contacts = data.contacts || [];
        pendingThreads = data.pending_threads || [];
        unreadCounts = data.unread_counts || unreadCounts;
        groupActiveCount = data.group_active_count ?? groupActiveCount;
        renderContacts();
        if (currentChat.scope === "group") {
            await loadMessages();
        } else {
            await loadMessages();
        }
    };

    groupBtn.addEventListener('click', () => {
        currentChat = { scope: "group", peer: "global" };
        setActiveThread();
        loadMessages();
    });

    term.addEventListener('ghost-open-email-chat', (event) => {
        openDirectChat(event.detail && event.detail.peer);
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
        currentChat = { scope: "group", peer: "global" };
        renderContacts();
        loadMessages();
    });

    messageForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = messageInput.value.trim();
        if (!body) return;

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
        if (data.messages) {
            contacts = data.contacts || contacts;
            pendingThreads = data.pending_threads || pendingThreads;
            unreadCounts = data.unread_counts || unreadCounts;
            groupActiveCount = data.group_active_count ?? groupActiveCount;
            messageInput.value = "";
            renderContacts();
            renderMessages(data.messages);
        }
    });

    bootstrap();
    const mailRefreshTimer = setInterval(refreshThreads, 3000);
    term.querySelector('.close-btn').addEventListener('click', () => clearInterval(mailRefreshTimer), { once: true });
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

function escapeHTML(str) {
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

function formatStorageSize(value, unit = "MB") {
    const number = Number(value || 0);
    if (!Number.isFinite(number) || number <= 0) return `0 ${unit}`;
    return `${Math.round(number)} ${unit}`;
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
    const div = document.createElement('div');
    div.className = `system-toast ${type}`;
    div.innerHTML = `
        <h4>${message.title || 'Komunikat'}</h4>
        <div>${message.text}</div>
    `;
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
        console.error("BĹ‚Ä…d pobierania komunikatĂłw systemowych");
    } finally {
        endDesktopLoading(loadingToken);
    }
}

// đź” Co 10 sekund sprawdzaj nowe
setInterval(pollSystemMessages, 10000);

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
                        else console.warn(`âť“ Nieznany interfejs: ${type}`);
                    };

                    action();
                }
            }
        }
    } catch (err) {
        console.error("âťŚ BĹ‚Ä…d podczas pobierania launch-queue:", err);
    } finally {
        // SprĂłbuj ponownie za 10 sekund
        endDesktopLoading(loadingToken);
        setTimeout(pollLaunchQueue, 10000);
    }
}

// Uruchom po zaĹ‚adowaniu strony
document.addEventListener("DOMContentLoaded", () => {
    pollLaunchQueue();
    refreshPlayerHackAccess();
});
