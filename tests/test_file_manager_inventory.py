import unittest
from unittest.mock import patch

import run
from database import db_connect
from inventory_bootstrap import repair_missing_inventory
from tests import test_player_hack_read_paths as read_tests
from tests import test_ghostlab_alignment as alignment


class FileManagerInventoryTest(unittest.TestCase):
    setUp = read_tests.PlayerHackReadPathsTest.setUp
    no_heavy = alignment.GhostLabAlignmentTest.no_heavy

    def seed(self):
        profile = read_tests.valid_profile('attacker')
        profile.update(storage_capacity=2048, storage_used=17, storage_unit='MB',
                       apps=[{'id': 'owned', 'name': 'Owned', 'file_size': 17}],
                       files={'tools': [{'id': 'owned.sh', 'name': 'Owned.sh', 'app_id': 'owned'}]})
        self.users.save_profile_guarded(profile, source='profile_manager.registration',
                                        expected_revision=0, allow_create=True)

    def make_legacy(self):
        with db_connect(self.path) as conn:
            for table in ('player_storage', 'player_apps', 'player_tool_files'):
                conn.execute(f'DELETE FROM {table} WHERE username=?', ('attacker',))

    def test_new_account_opens_fm_without_profile_fallback(self):
        self.seed()
        with self.no_heavy():
            result = self.client.get('/api/ghostlab/file-manager')
        self.assertEqual(result.status_code, 200, result.json)
        self.assertEqual(result.json['storage_capacity'], 2048)
        self.assertEqual(result.json['storage_used'], 17)
        self.assertEqual(result.json['apps'][0]['id'], 'owned')
        self.assertEqual(result.json['files']['tools'][0]['id'], 'owned.sh')

    def test_legacy_missing_inventory_reproduces_409_and_exact_repair_fixes_it(self):
        self.seed()
        self.make_legacy()
        with self.no_heavy():
            broken = self.client.get('/api/ghostlab/file-manager')
        self.assertEqual(broken.status_code, 409)
        self.assertEqual(broken.json['reason'], 'inventory_unavailable')
        with db_connect(self.path) as conn:
            before = tuple(conn.execute('SELECT profile_json,profile_revision,profile_checksum FROM users WHERE username=?', ('attacker',)).fetchone())
        self.assertEqual(repair_missing_inventory(self.path, 'attacker')['status'], 'ready')
        self.assertEqual(repair_missing_inventory(self.path, 'attacker', apply=True)['status'], 'applied')
        self.assertEqual(repair_missing_inventory(self.path, 'attacker', apply=True)['status'], 'already_initialized')
        with self.no_heavy():
            self.assertEqual(self.client.get('/api/ghostlab/file-manager').status_code, 200)
        with db_connect(self.path) as conn:
            after = tuple(conn.execute('SELECT profile_json,profile_revision,profile_checksum FROM users WHERE username=?', ('attacker',)).fetchone())
        self.assertEqual(before, after)

    def test_partial_inventory_is_not_overwritten(self):
        self.seed()
        with db_connect(self.path) as conn:
            conn.execute('DELETE FROM player_storage WHERE username=?', ('attacker',))
        result = repair_missing_inventory(self.path, 'attacker', apply=True)
        self.assertEqual(result['reason'], 'partial_inventory_requires_review')
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM player_apps WHERE username=?', ('attacker',)).fetchone()[0], 1)

    def test_missing_and_stale_generation_still_rejected(self):
        self.seed()
        for generation, reason in [('', 'missing_generation'), ('obsolete', 'stale_generation')]:
            response = self.client.get('/api/ghostlab/file-manager', headers={run.SESSION_GENERATION_HEADER: generation})
            self.assertEqual(response.status_code, 409)
            self.assertEqual(response.json['reason'], reason)

    def test_inventory_failure_rolls_back_registration(self):
        with patch('inventory_bootstrap.insert_inventory', side_effect=RuntimeError('forced rollback')):
            with self.assertRaises(RuntimeError):
                self.seed()
        self.assertFalse(self.users.username_exists('attacker'))

    def test_integrity_failure_blocks_offline_repair(self):
        self.seed()
        self.make_legacy()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE users SET profile_checksum='corrupt' WHERE username='attacker'")
        self.assertEqual(repair_missing_inventory(self.path, 'attacker', apply=True)['reason'], 'profile_integrity')
