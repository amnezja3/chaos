import copy
import unittest
from unittest.mock import Mock, patch

import run
from profileManagment import UserProfileManager
from tests import test_player_hack_read_paths as read_tests


class RegistrationLocaleTest(unittest.TestCase):
    setUp = read_tests.PlayerHackReadPathsTest.setUp

    def payload(self, **changes):
        return dict(username="locale_player", password="secret123", faction="3", role="2",
                    nick="My own nickname", email="locale@example.test", **changes)

    def test_new_account_locale_is_canonical_and_identity_is_language_independent(self):
        template = read_tests.valid_profile('template')
        template['desktop_settings'] = {'wallpaper': 'wall-2', 'icon_positions': {'custom': {'left': 20, 'top': 30}}}
        self.users.save_profile(read_tests.valid_profile('admin'))
        resource = Mock()
        resource.get.side_effect = lambda *args, **kwargs: copy.deepcopy(template)
        def manager(username):
            return UserProfileManager(username, store=self.users, resource_store=resource)
        for index, language in enumerate(({}, {'locale': 'en-GB'}, {'locale': 'pl'})):
            payload = self.payload(**language)
            payload.update(username=f'locale_player_{index}', email=f'locale{index}@example.test')
            with patch.object(run, 'UserProfileManager', side_effect=manager), \
                 patch.object(run, 'get_start_location_by_ip', return_value={'city': 'test', 'lat': 52.2, 'lng': 21.0}), \
                 patch.object(run, 'resolve_first_respawn_outside_controlled_territory', return_value={'position': {'lat': 52.2, 'lng': 21.0}}), \
                 patch.object(run, 'begin_authenticated_session', return_value='generation'):
                response = run.app.test_client().post('/api/register-finalize', json=payload)
            self.assertEqual(response.status_code, 200, response.json)
            self.assertTrue(response.json['success'], response.json)
            settings = self.identity.get_desktop_boot(payload['username'])['desktop_settings']
            self.assertEqual(settings['locale'], 'en' if index == 1 else 'pl')
            self.assertEqual(settings['wallpaper'], 'wall-2')
            self.assertEqual(settings['icon_positions'], template['desktop_settings']['icon_positions'])
            profile = self.users.get_profile(payload['username'])
            identity = run.build_registration_identity_contract('3', '2')
            self.assertEqual(profile['ghost_profession'], identity['profession_code'])
            self.assertEqual(profile['fraction']['role'], '2')
            self.assertEqual(profile['nick'], payload['nick'])
            self.assertEqual(profile['email'], payload['email'])

    def test_invalid_language_is_rejected_before_registration_or_availability_reads(self):
        with patch.object(run, 'UserProfileManager') as manager, \
             patch.object(run.user_store, 'username_exists') as lookup:
            for language in ('ANY', 'ru', '', None, ['en']):
                for endpoint in ('/api/register-check', '/api/register-finalize'):
                    response = run.app.test_client().post(endpoint, json=self.payload(locale=language))
                    self.assertEqual(response.status_code, 400)
                    self.assertEqual(response.json['error_key'], 'locale.invalid')
            manager.assert_not_called()
            lookup.assert_not_called()

    def test_errors_have_stable_keys_and_recipient_language_without_account_mutation(self):
        client = run.app.test_client()
        with patch.object(run.user_store, 'username_exists', return_value=True):
            for language, expected in [('en', 'This username is already taken.'), ('pl', 'Ta nazwa uzytkownika jest juz zajeta.')]:
                response = client.post('/api/register-check', json={'checking_username': 'someone', 'type_data': 'user', 'locale': language})
                self.assertFalse(response.json['success'])
                self.assertEqual(response.json['error_key'], 'onboarding.username_taken')
                self.assertEqual(response.json['error'], expected)
        payload = self.payload(locale='en')
        payload['password'] = 'short'
        response = client.post('/api/register-finalize', json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json['error_key'], 'onboarding.password_short')
        self.assertEqual(response.json['error'], 'Password must contain at least 8 characters.')
        self.assertFalse(self.users.username_exists(payload['username']))


if __name__ == '__main__':
    unittest.main()
