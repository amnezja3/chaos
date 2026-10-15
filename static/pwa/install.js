(() => {
    'use strict';
    if (window.ChaosInstall) return;
    let promptEvent = null, installed = false, waiting = false;
    const panels = new Set();
    const words = JSON.parse(document.getElementById('chaos-install-text').textContent);
    function language() {return (window.GhostLocale?.getLocale?.() || document.documentElement.lang || navigator.language).startsWith('pl') ? 'pl' : 'en';}
    function platform() {
        const ua = navigator.userAgent;
        if (/iPad|iPhone|iPod/.test(ua) || (/Mac/.test(ua) && navigator.maxTouchPoints > 1)) return 'iOS';
        if (/Android/.test(ua)) return 'Android';
        if (/Windows/.test(ua)) return 'Windows';
        if (/Linux/.test(ua)) return 'Linux';
        return '';
    }
    function standalone() {return matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;}
    function refresh() {
        for (const panel of panels) {
            if (!panel.isConnected) {panels.delete(panel); continue;}
            const t = words[language()];
            panel.querySelector('[data-install-now]').hidden = !promptEvent || standalone() || installed;
            panel.querySelectorAll('[data-install-word]').forEach(el => {el.textContent = t[el.dataset.installWord];});
            panel.querySelector('[data-install-status]').textContent = t[standalone() ? 'standalone' : installed ? 'installed' : panel.dataset.state || (promptEvent ? 'ready' : 'unavailable')];
            panel.querySelector('[data-install-update]').hidden = !waiting;
            panel.querySelectorAll('[data-platform]').forEach(button => {button.title = button.dataset.platform === platform() ? t.recommend : button.dataset.platform;});
        }
    }
    function mount(host) {
        if (!host || host.dataset.installMounted) return;
        host.dataset.installMounted = '1'; host.classList.add('chaos-install');
        host.innerHTML = '<h3 data-install-word="title"></h3><p data-install-word="optional"></p><div class="chaos-install-grid"></div><p role="status" data-install-status></p><p data-install-instructions hidden></p><a href="/chaos.desktop" download data-install-word="shortcut" hidden></a><p data-install-update data-install-word="update" role="status" hidden></p>';
        const install = document.createElement('button');
        install.type = 'button'; install.dataset.installNow = ''; install.dataset.installWord = 'install_now';
        async function installHere() {
            if (!promptEvent || standalone() || installed) return;
            const pending = promptEvent; promptEvent = null;
            host.querySelector('[data-install-instructions]').hidden = true;
            refresh();
            try {await pending.prompt(); const choice = await pending.userChoice; host.dataset.state = choice.outcome === 'accepted' ? 'accepted' : 'cancelled';}
            catch (_) {host.dataset.state = 'error';}
            refresh();
        }
        install.addEventListener('click', installHere);
        host.querySelector('.chaos-install-grid').before(install);
        for (const name of ['Windows','Linux','Android','iOS']) {
            const button = document.createElement('button'); button.type = 'button'; button.textContent = name;
            button.dataset.platform = name; button.dataset.recommended = String(name === platform());
            button.addEventListener('click', async () => {
                const detail = host.querySelector('[data-install-instructions]');
                detail.dataset.installWord = name === 'iOS' ? 'ios' : 'manual'; detail.hidden = false;
                host.querySelector('a').hidden = name !== 'Linux';
                if (name === platform() && name !== 'iOS' && promptEvent && !standalone() && !installed) {
                    await installHere();
                }
                refresh();
            });
            host.querySelector('.chaos-install-grid').append(button);
        }
        panels.add(host); refresh();
    }
    window.addEventListener('beforeinstallprompt', event => {event.preventDefault(); promptEvent = event; panels.forEach(p=>delete p.dataset.state); refresh();});
    window.addEventListener('appinstalled', () => {installed = true; promptEvent = null; refresh();});
    document.addEventListener('ghost:locale-changed', refresh);
    window.ChaosInstall = {mount, platform};
    document.querySelectorAll('[data-chaos-install]').forEach(mount);
    if ('serviceWorker' in navigator && window.isSecureContext) {
        navigator.serviceWorker.register('/chaos-sw.js', {scope:'/', updateViaCache:'none'}).then(value => {
            waiting = !!value.waiting; refresh();
            value.addEventListener('updatefound', () => {
                const worker = value.installing;
                worker?.addEventListener('statechange', () => {waiting = worker.state === 'installed' && !!navigator.serviceWorker.controller; refresh();});
            });
        }).catch(() => { /* Installation instructions remain usable without SW. */ });
    }
})();
