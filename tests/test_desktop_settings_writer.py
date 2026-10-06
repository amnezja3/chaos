import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import database
import run
from database import db_connect, ProfileRecoveryRequired
from tests import test_player_hack_read_paths as read_tests
from tests import test_ghostlab_alignment as alignment_tests


class DesktopSettingsWriterTest(unittest.TestCase):
    setUp = read_tests.PlayerHackReadPathsTest.setUp
    no_heavy = alignment_tests.GhostLabAlignmentTest.no_heavy

    def seed(self):
        self.users.save_profile(read_tests.valid_profile('attacker'))

    def metadata(self):
        with db_connect(self.path) as conn:
            return tuple(conn.execute('SELECT profile_json,profile_revision,profile_checksum,updated_at FROM users WHERE username=?', ('attacker',)).fetchone())

    def update(self, changes):
        return self.identity.update_desktop_settings('attacker', changes, normalize=run.normalize_desktop_settings)

    def test_http_write_and_retry_are_small_and_do_not_touch_profile(self):
        self.seed()
        before = self.metadata()
        writes = []
        execute = database.InstrumentedConnection.execute

        def count(conn, sql, *args, **kwargs):
            if sql.lstrip().upper().startswith('UPDATE USER_IDENTITY_PROJECTION'):
                writes.append(sql)
            return execute(conn, sql, *args, **kwargs)

        with patch.object(database.InstrumentedConnection, 'execute', count), self.no_heavy():
            for _ in range(3):
                result = self.client.post('/api/profile/desktop', json={'wallpaper': 'wall-1'})
                self.assertEqual(result.status_code, 200, result.json)
                self.assertEqual(result.json['desktop_settings']['wallpaper'], 'wall-1')
            self.assertEqual(self.identity.get_desktop_boot('attacker')['desktop_settings']['wallpaper'], 'wall-1')
        self.assertEqual(len(writes), 1)
        self.assertEqual(self.metadata(), before)

    def test_parallel_partial_updates_preserve_both_changes(self):
        self.seed()
        before = self.metadata()
        with self.no_heavy(), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.update, [{'wallpaper': 'wall-2'}, {'auto_fullscreen': True}]))
        self.assertEqual(len(results), 2)
        settings = self.identity.get_desktop_boot('attacker')['desktop_settings']
        self.assertEqual(settings['wallpaper'], 'wall-2')
        self.assertTrue(settings['auto_fullscreen'])
        self.assertEqual(self.metadata(), before)

    def test_locale_write_normalization_and_boot_use_only_projection(self):
        self.seed()
        before = self.metadata()
        with self.no_heavy():
            response = self.client.post('/api/profile/desktop', json={'locale': 'en-GB'})
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(response.json['desktop_settings']['locale'], 'en')
            self.update({'wallpaper': 'wall-2'})
            self.assertEqual(self.identity.get_desktop_boot('attacker')['desktop_settings']['locale'], 'en')
            for value in ('ANY', 'ru', '', None, ['en']):
                rejected = self.client.post('/api/profile/desktop', json={'locale': value})
                self.assertEqual(rejected.status_code, 400, rejected.json)
                self.assertEqual(rejected.json['reason'], 'invalid_locale')
            self.assertEqual(self.identity.get_desktop_boot('attacker')['desktop_settings']['locale'], 'en')
        self.assertEqual(self.metadata(), before)

    def test_legacy_locale_defaults_to_polish_and_accounts_are_independent(self):
        self.seed()
        self.users.save_profile(read_tests.valid_profile('victim'))
        self.assertEqual(run.normalize_desktop_settings({})['locale'], 'pl')
        with self.no_heavy():
            self.update({'locale': 'en'})
            self.identity.update_desktop_settings('victim', {'wallpaper': 'wall-1'}, normalize=run.normalize_desktop_settings)
            self.assertEqual(self.identity.get_desktop_boot('attacker')['desktop_settings']['locale'], 'en')
            self.assertEqual(self.identity.get_desktop_boot('victim')['desktop_settings']['locale'], 'pl')

    def test_login_bootstrap_and_invalid_credentials_are_localized_without_profile_read(self):
        anonymous = run.app.test_client()
        with self.no_heavy(), patch.object(run, 'authenticate_user', return_value=False):
            response = anonymous.get('/')
            self.assertEqual(response.status_code, 200)
            self.assertIn('ghost-i18n-bootstrap', response.text)
            self.assertIn('data-entry-locale', response.text)
            invalid = anonymous.post('/', data={'username': 'invalid-test', 'password': 'wrong', 'locale': 'en'})
            self.assertEqual(invalid.status_code, 200)
            self.assertIn('Invalid login credentials.', invalid.text)
            self.assertIn('data-ghost-i18n="entry.invalid_credentials"', invalid.text)

    def test_legacy_read_and_projection_rebuild_preserve_canonical_settings(self):
        self.seed()
        stale = self.users.get_profile_with_revision('attacker')
        self.update({'wallpaper': 'wall-3'})
        self.users.patch_profile_guarded('attacker', {'nick': 'New alias', 'desktop_settings': {}},
                                        source='test.desktop.legacy', expected_revision=stale['profile_revision'])
        for profile in (self.users.get_profile('attacker'),
                        self.users.get_profile_with_revision('attacker')['profile'],
                        self.identity.get_desktop_boot('attacker')):
            self.assertEqual(profile['desktop_settings']['wallpaper'], 'wall-3')

    def test_empty_update_does_not_initialize_or_change_profile(self):
        self.seed()
        before = self.metadata()
        with self.no_heavy():
            self.update({})
        with db_connect(self.path) as conn:
            self.assertIsNone(conn.execute('SELECT desktop_settings_json FROM user_identity_projection WHERE username=?', ('attacker',)).fetchone()[0])
        self.assertEqual(self.metadata(), before)

    def test_stale_projection_and_invalid_http_value_are_rejected(self):
        self.seed()
        self.assertEqual(self.client.post('/api/profile/desktop', json={'wallpaper': 'invalid'}).status_code, 400)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE user_identity_projection SET source_profile_revision=0 WHERE username='attacker'")
        with self.no_heavy(), self.assertRaises(ProfileRecoveryRequired):
            self.update({'wallpaper': 'wall-1'})

    def test_session_precommit_rejection_rolls_back_settings(self):
        self.seed()
        def reject(conn):
            raise RuntimeError('session revoked')
        token = database.set_request_transaction_precommit_guard(reject)
        try:
            with self.assertRaises(database.ProfilePrecommitRejected):
                self.update({'wallpaper': 'wall-1'})
        finally:
            database.reset_request_transaction_precommit_guard(token)
        self.assertNotEqual(self.identity.get_desktop_boot('attacker')['desktop_settings'].get('wallpaper'), 'wall-1')
