'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const core = require('../../static/js/ghost_i18n.js');
const root = path.resolve(__dirname, '../..');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'static/locales/manifest.json')));
const catalogs = {};
for (const locale of ['pl', 'en']) {
  const messages = {};
  for (const domain of manifest.domains) Object.assign(messages, JSON.parse(fs.readFileSync(path.join(root, `static/locales/${locale}/${domain}.json`))).messages);
  catalogs[locale] = {format_version: manifest.format_version, content_version: manifest.content_version, locale, messages};
}
const missing = [];
const translator = core.createTranslator(manifest, catalogs, (...args) => missing.push(args));
let locale = 'pl';
const context = vm.createContext({document: {addEventListener() {}}, window: {GhostLocale: {t: (key, params) => translator.t(key, params, locale)}}});
vm.runInContext(fs.readFileSync(path.join(root, 'static/js/register_scripts.js'), 'utf8'), context);
const canonical = vm.runInContext('JSON.stringify(rolesByFaction)', context);
for (locale of ['pl', 'en']) {
  for (let faction = 1; faction <= 4; faction++) {
    for (let role = 1; role <= 5; role++) {
      vm.runInContext(`formData.faction=${faction};formData.role=${role};formData.username='<img src=x onerror=alert(1)>';formData.email='UGC@example.test';`, context);
      for (let step = 0; step < 6; step++) {
        const html = vm.runInContext(`steps[${step}]()`, context);
        assert(!html.includes('<img src=x'), 'user text must remain escaped');
        if (step === 5) {
          assert(html.includes('&lt;img src=x onerror=alert(1)&gt;'));
          assert(html.includes('UGC@example.test'));
        }
      }
      const state = JSON.parse(vm.runInContext('JSON.stringify(formData)', context));
      assert.equal(state.faction, faction);
      assert.equal(state.role, role);
    }
  }
  assert.equal(vm.runInContext('JSON.stringify(rolesByFaction)', context), canonical);
  assert.equal(vm.runInContext('validatePassword("short")', context), 'onboarding.password_short');
  assert.equal(vm.runInContext('validatePassword("Valid123")', context), '');
}
assert.deepEqual(missing, []);
console.log('Registration locale: PASS (all faction/role/step labels, stable IDs, escaped UGC, validation keys)');
