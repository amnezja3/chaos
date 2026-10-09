import unittest

from creator_policy import RECIPES
from ghost_i18n import translator


class MapActionLocaleTest(unittest.TestCase):
    def test_every_creator_action_has_the_same_map_key_in_both_languages(self):
        runtime = translator()
        for locale in ('pl', 'en'):
            action_keys = {key.removeprefix('map.action.') for key in runtime.catalogs[locale]['messages']
                           if key.startswith('map.action.')}
            self.assertEqual(set(RECIPES), action_keys)
            for action in RECIPES:
                self.assertTrue(runtime.t('map.action.' + action, locale=locale))
                caption = runtime.t('map.action_name.' + action, locale=locale)
                self.assertIn('map.action_name.' + action, runtime.catalogs[locale]['messages'])
                self.assertTrue(runtime.t('map.action.' + action, locale=locale).endswith(' ' + caption))

    def test_target_label_is_interpolated_literally(self):
        name = '<b>Własna nazwa {action}</b>'
        for locale in ('pl', 'en'):
            text = translator().t('map.menu.mark', {'name': name}, locale)
            self.assertIn(name, text)

    def test_scan_count_plural_forms_and_target_names(self):
        runtime = translator()
        for count, ending in [(0, 'obiektów.'), (1, 'obiekt.'), (2, 'obiekty.'), (12, 'obiektów.'), (22, 'obiekty.')]:
            self.assertTrue(runtime.t('map.result.scanned', {'count': count}, 'pl').endswith(ending))
        self.assertEqual(runtime.t('map.result.scanned', {'count': 1}, 'en'), '🔍 Scanned 1 new object.')
        self.assertEqual(runtime.t('map.result.scanned', {'count': 12}, 'en'), '🔍 Scanned 12 new objects.')
        for locale in ('pl', 'en'):
            name = "Mike's <keep> {count}"
            self.assertIn(name, runtime.t('map.result.aimed', {'name': name}, locale))


if __name__ == '__main__': unittest.main()
