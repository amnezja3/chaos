import unittest
from unittest.mock import patch

import run
from database import db_connect
import test_player_hack_read_paths as read_paths


class PlayerHackDisconnectTest(unittest.TestCase):
    setUp = read_paths.PlayerHackReadPathsTest.setUp
    seed = read_paths.PlayerHackReadPathsTest.seed

    def prepare(self, tool):
        self.seed()
        self.inventory.install_app('attacker', {'id': tool, 'name': tool}, purchase_key=tool)

    def test_security_write_rechecks_expiry_and_installation(self):
        self.prepare('securityPanelProxy')
        self.users.patch_profile_guarded('victim', {'security': {'firewall': True}}, source='test.security')
        for route, body in [('update', {'key': 'firewall', 'value': False}),
                            ('preset', {'preset': 'open'})]:
            for revoke in ('expiry', 'uninstall'):
                with self.subTest(route=route, revoke=revoke):
                    self.access.grant_access('attacker', 'victim')
                    if not self.inventory.has_app('attacker', 'securityPanelProxy'):
                        self.inventory.install_app('attacker', {'id': 'securityPanelProxy', 'name': 'Proxy'}, purchase_key=f'{route}:{revoke}')
                    before = self.users.get_profile_with_revision('victim')
                    original = self.users.patch_profile_guarded
                    def changed(*args, **kwargs):
                        if revoke == 'expiry':
                            with db_connect(self.path) as conn:
                                conn.execute("UPDATE player_hack_access SET hacked_until='2000-01-01T00:00:00'")
                        else:
                            self.inventory.uninstall_app('attacker', 'securityPanelProxy')
                        return original(*args, **kwargs)
                    with patch.object(self.users, 'patch_profile_guarded', side_effect=changed):
                        response = self.client.post('/api/player-hack/security/' + route,
                                                    json={'victim_username': 'victim', **body})
                    self.assertEqual(response.status_code, 409, response.json)
                    self.assertEqual(self.users.get_profile_with_revision('victim'), before)
                    with db_connect(self.path) as conn:
                        conn.execute('DELETE FROM player_hack_access')

    def test_cleaner_notification_failure_rolls_back_then_lost_response_is_safe(self):
        self.prepare('arsenalCleaner')
        self.inventory.install_app('victim', {'id': 'remove-me', 'name': 'Remove Me'}, purchase_key='target')
        request = {'tool_id': 'arsenalCleaner', 'victim_username': 'victim'}
        with patch.object(run, 'choice', return_value={'id': 'remove-me', 'name': 'Remove Me'}), \
             patch.object(run, 'randint', return_value=1):
            with patch.object(self.messages, 'add_message', side_effect=RuntimeError('notification failed')):
                self.assertEqual(self.client.post('/api/player-hack/tool/use', json=request).status_code, 500)
            self.assertTrue(self.inventory.has_app('victim', 'remove-me'))
            access = self.access.get_active_access('attacker', 'victim')
            self.assertIsNone(self.access.get_tool_usage(access, 'attacker', 'victim', 'arsenalCleaner'))
            # Fail after commit, while constructing the HTTP response.
            with patch.object(run, 'serialize_player_hack_access', side_effect=RuntimeError('response lost')):
                self.assertEqual(self.client.post('/api/player-hack/tool/use', json=request).status_code, 500)
        self.assertFalse(self.inventory.has_app('victim', 'remove-me'))
        with patch.object(run, 'randint', side_effect=AssertionError('reroll')):
            retry = self.client.post('/api/player-hack/tool/use', json=request)
        self.assertEqual(retry.status_code, 409, retry.json)
        self.assertEqual(retry.json['reason'], 'tool_already_used')
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM system_messages WHERE username='victim' AND source='arsenal_cleaner'").fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM game_state_deltas WHERE username='victim' AND type='apps.app_uninstalled'").fetchone()[0], 1)

    def test_security_cas_preserves_concurrent_victim_change(self):
        self.prepare('securityPanelProxy')
        self.users.patch_profile_guarded('victim', {'security': {'firewall': True}}, source='test.security')
        original = self.users.patch_profile_guarded
        def concurrent(*args, **kwargs):
            original('victim', {'nick': 'New nick'}, source='test.concurrent')
            return original(*args, **kwargs)
        with patch.object(self.users, 'patch_profile_guarded', side_effect=concurrent):
            response = self.client.post('/api/player-hack/security/update', json={
                'victim_username': 'victim', 'key': 'firewall', 'value': False})
        self.assertEqual(response.status_code, 409, response.json)
        current = self.users.get_profile('victim')
        self.assertEqual(current['nick'], 'New nick')
        self.assertTrue(current['security']['firewall'])

    def test_cleaner_rechecks_installation_after_preflight(self):
        self.prepare('arsenalCleaner')
        self.inventory.install_app('victim', {'id': 'remove-me', 'name': 'Remove Me'}, purchase_key='target')
        original = self.inventory.apply_arsenal_cleaner
        def revoked(*args, **kwargs):
            self.inventory.uninstall_app('attacker', 'arsenalCleaner')
            return original(*args, **kwargs)
        with patch.object(self.inventory, 'apply_arsenal_cleaner', side_effect=revoked), \
             patch.object(run, 'choice', return_value={'id': 'remove-me', 'name': 'Remove Me'}), \
             patch.object(run, 'randint', return_value=1):
            response = self.client.post('/api/player-hack/tool/use', json={
                'tool_id': 'arsenalCleaner', 'victim_username': 'victim'})
        self.assertEqual(response.status_code, 409, response.json)
        self.assertEqual(response.json['reason'], 'player_access_changed')
        self.assertTrue(self.inventory.has_app('victim', 'remove-me'))
        access = self.access.get_active_access('attacker', 'victim')
        self.assertIsNone(self.access.get_tool_usage(access, 'attacker', 'victim', 'arsenalCleaner'))
