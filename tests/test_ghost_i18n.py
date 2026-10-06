import copy
import json
from pathlib import Path
import unittest

from ghost_i18n import CATALOG_ROOT, Translator, manifest, resolve_locale, translator

FIXTURE = Path(__file__).parent / 'fixtures' / 'i18n_conformance.json'


class GhostI18nTest(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads(FIXTURE.read_text(encoding='utf-8'))
        self.runtime = translator()

    def test_shared_translations_and_locale_resolution(self):
        for case in self.cases['translations']:
            with self.subTest(case=case):
                self.assertEqual(self.runtime.t(case['key'], case['params'], case['locale']), case['expected'])
        for case in self.cases['resolution']:
            self.assertEqual(resolve_locale(**case['input']), case['expected'])

    def test_strict_parameter_contract_and_non_finite_numbers(self):
        for params in self.cases['invalid_params'] + [{'count': float('nan')}, {'count': float('inf')}]:
            with self.assertRaisesRegex(ValueError, 'invalid_message_params'):
                self.runtime.t('shell.files.count', params)

    def test_fallback_uses_source_plural_rules_and_reports_missing_key(self):
        bundles = copy.deepcopy(self.runtime.catalogs)
        del bundles['en']['messages']['shell.files.count']
        diagnostics = []
        runtime = Translator(manifest(), bundles, lambda *args: diagnostics.append(args))
        self.assertEqual(runtime.t('shell.files.count', {'count': 22}, 'en'), '22 pliki')
        self.assertEqual(diagnostics, [('missing_key', 'shell.files.count', 'en')])
        self.assertEqual(runtime.t('unknown', locale='en'), 'Message unavailable.')

    def test_catalog_keys_parameters_forms_and_versions_match(self):
        bundles = self.runtime.catalogs
        self.assertEqual(set(bundles['pl']['messages']), set(bundles['en']['messages']))
        for locale, bundle in bundles.items():
            for key, entry in bundle['messages'].items():
                self.assertEqual(entry['params'], bundles['pl']['messages'][key]['params'])
                params = {name: 2 if kind == 'number' else '<b>UGC</b>' for name, kind in entry['params'].items()}
                self.runtime.t(key, params, locale)
                if 'plural' in entry:
                    self.assertEqual(entry['params'][entry['plural']], 'number')
                    categories = {rule['category'] for rule in manifest()['locales'][locale]['plural_rules']} | {'other'}
                    self.assertEqual(set(entry['forms']), categories)
        broken = copy.deepcopy(bundles)
        broken['en']['content_version'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'catalog_version_mismatch'):
            Translator(manifest(), broken)

    def test_versioned_message_and_independent_recipients(self):
        envelope = {'key': 'shell.desktop.files', 'params': {}, 'content_version': manifest()['content_version']}
        self.assertEqual(self.runtime.message(envelope, 'en'), 'Files')
        self.assertEqual(self.runtime.message(envelope, 'pl'), 'Pliki')
        self.assertEqual(self.runtime.message(envelope, 'en'), 'Files')
        envelope['content_version'] = 'old'
        with self.assertRaisesRegex(ValueError, 'message_version_mismatch'):
            self.runtime.message(envelope)

    def test_extra_language_requires_only_data(self):
        registry = copy.deepcopy(manifest())
        registry['locales']['zz'] = {**registry['locales']['en'], 'name': 'Pseudo', 'status': 'test'}
        bundles = copy.deepcopy(self.runtime.catalogs)
        bundles['zz'] = {**copy.deepcopy(bundles['en']), 'locale': 'zz'}
        bundles['zz']['messages']['shell.desktop.files']['text'] = '[Файлы — extended label]'
        runtime = Translator(registry, bundles)
        self.assertEqual(runtime.t('shell.desktop.files', locale='zz'), '[Файлы — extended label]')
        self.assertEqual(runtime.t('shell.files.count', {'count': 2}, 'zz'), '2 files')


if __name__ == '__main__':
    unittest.main()
