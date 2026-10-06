import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from unittest.mock import patch

from ghost_i18n import approved_locales, radio_locale_filters, format_number, format_date, format_unit, translator
from terminals.commands import interpret_command
import run


class ShellLocaleTest(unittest.TestCase):
    def test_presentation_formats_do_not_change_canonical_values(self):
        amount = 12345.625
        self.assertEqual('1234,5', format_number(1234.5, 'pl'))
        self.assertEqual('1,234.5', format_number(1234.5, 'en'))
        self.assertEqual('12\u00a0345,63', format_number(amount, 'pl', maximum_fraction_digits=2))
        self.assertEqual('12,345.63', format_number(amount, 'en', maximum_fraction_digits=2))
        self.assertEqual('12\u00a0345,625 HC', format_unit(amount, 'hackcoin', 'pl'))
        self.assertEqual(amount, 12345.625)
        instant = datetime(2026, 10, 6, 23, 30, tzinfo=timezone.utc)
        self.assertEqual('06.10.2026', format_date(instant, 'pl'))
        self.assertEqual('10/06/2026', format_date(instant, 'en'))
        self.assertEqual(instant.hour, 23)
        with self.assertRaises(ValueError): format_date('2026-10-06', 'en')
        with self.assertRaises(ValueError): format_unit(1, 'invalid', 'en')

    def test_approved_languages_and_radio_filter_are_separate(self):
        for purpose in ('interface', 'radio', 'narration'):
            self.assertEqual(('pl', 'en'), approved_locales(purpose))
            self.assertNotIn('ANY', approved_locales(purpose))
        self.assertEqual(('pl', 'en', 'ANY'), radio_locale_filters())
        with self.assertRaises(ValueError): approved_locales('arbitrary')

    def test_terminal_actions_match_for_independent_language_contexts(self):
        profile = {'username':'UGC <keep>', 'apps':[]}
        commands = ['map', 'profile', 'files', 'settings', 'teleport 12:23', 'focus cur:loc', 'help', 'bad_command', 'cat /readme.txt']
        for command in commands:
            with ThreadPoolExecutor(max_workers=2) as pool:
                pl, en = list(pool.map(lambda locale: interpret_command(command, profile, locale=locale), ['pl','en']))
            self.assertEqual({k:v for k,v in pl.items() if k not in ('response','response_i18n')},
                             {k:v for k,v in en.items() if k not in ('response','response_i18n')})
            if 'response_i18n' in en:
                self.assertEqual(en['response'], translator().message(en['response_i18n'], 'en'))
        for locale in ('pl','en'):
            echo = interpret_command('echo Tekst autora <b>bez zmian</b>', profile, locale=locale)
            self.assertEqual('Tekst autora <b>bez zmian</b>', echo['response'])
            self.assertNotIn('response_i18n', echo)

    def test_request_locale_is_small_cached_and_recovery_retains_it(self):
        with run.app.test_request_context('/'):
            run.session['user'] = 'locale-test'
            with patch.object(run.identity_projection_store, 'get_desktop_boot', return_value={'desktop_settings':{'locale':'en'}}) as reader, \
                    patch.object(run.user_store, 'get_profile', side_effect=AssertionError('heavy profile read')):
                self.assertEqual('en', run.request_ui_locale())
                self.assertEqual('en', run.request_ui_locale())
                self.assertIn('sign in', run.session_recovery_message('missing_generation'))
                self.assertEqual('en', run.session['recovery_locale'])
                reader.assert_called_once_with('locale-test')


if __name__ == '__main__': unittest.main()
