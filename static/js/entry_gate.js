(() => {
    'use strict';
    const button = document.querySelector('[data-password-toggle]');
    const input = document.querySelector('[name="password"]');
    button?.addEventListener('click', () => {
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        button.setAttribute('aria-pressed', String(show));
    });
    // Installation stays optional and its real availability comes from Chrome.
    // Collapse only the secondary platform instructions, never the native prompt.
    const host = document.querySelector('.entry-page [data-chaos-install]');
    if (host && window.ChaosInstall) {
        window.ChaosInstall.mount(host);
        const details = document.createElement('details'); details.className = 'install-options';
        const summary = document.createElement('summary');
        summary.dataset.ghostI18n = 'entry.gate.install_options';
        summary.textContent = window.GhostLocale?.t('entry.gate.install_options') || 'Installation options';
        details.append(summary);
        for (const selector of ['[data-install-word="optional"]','.chaos-install-grid','[data-install-instructions]','a[href="/chaos.desktop"]']) {
            const element = host.querySelector(selector); if (element) details.append(element);
        }
        host.append(details);
        window.GhostLocale?.render(host);
    }
})();
