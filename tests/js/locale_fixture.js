const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const core = require('../../static/js/ghost_i18n.js');
module.exports = function(sandbox, locale='pl') {
    const root = path.resolve(__dirname, '../..');
    const manifest = JSON.parse(fs.readFileSync(path.join(root,'static/locales/manifest.json')));
    const catalogs = {};
    for (const language of ['pl','en']) {
        const messages = {};
        for (const domain of manifest.domains) Object.assign(messages, JSON.parse(fs.readFileSync(path.join(root,`static/locales/${language}/${domain}.json`))).messages);
        catalogs[language] = {locale:language, format_version:1, content_version:manifest.content_version, messages};
    }
    const translator = core.createTranslator(manifest,catalogs);
    sandbox.window ||= sandbox;
    sandbox.window.GhostLocale = {t:(key,params)=>translator.t(key,params,locale),hasKey:key=>Boolean(catalogs.pl.messages[key]),
        formatNumber:(value,options)=>new Intl.NumberFormat(locale,options).format(value)};
    sandbox.ghostText = sandbox.window.GhostLocale.t;
    vm.runInContext(fs.readFileSync(path.join(root,'static/js/ghost_i18n_bindings.js'),'utf8'),sandbox);
    for (const key of ['ghostLabel','ghostSet','ghostNumber','ghostReply']) sandbox[key]=sandbox.window[key];
};
