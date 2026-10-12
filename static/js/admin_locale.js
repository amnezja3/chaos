(() => {
    'use strict';
    const config = JSON.parse(document.getElementById('admin-locale-config').textContent);
    const translator = GhostI18n.createTranslator(config.manifest, config.catalogs);
    window.adminLocale = config.locale;
    window.adminT = (key, params = {}) => translator.t('apps.admin.' + key, params, config.locale);
    window.adminCode = value => Object.hasOwn(config.catalogs.pl.messages,'apps.admin.code.'+value) ? window.adminT('code.'+value) : value;
})();
