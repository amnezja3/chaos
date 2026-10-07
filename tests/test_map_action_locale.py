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


if __name__ == '__main__': unittest.main()
