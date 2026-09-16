from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import run
from database import MailStore, WalletStore, db_connect
from test_player_hack_read_paths import PlayerHackReadPathsTest
from test_ghostnetwork_suite_snapshot import valid_profile


class FinalToolTests(PlayerHackReadPathsTest):
    def prepare(self, heavy=False):
        self.seed(big_attacker=heavy, big_victim=heavy)
        self.mail = MailStore(self.path)
        self.users.save_profile(valid_profile('contact'))
        self.stack.enter_context(patch.object(run, 'mail_store', self.mail))
        for tool in ('friendKicker', 'securityPanelProxy'):
            self.inventory.install_app('attacker', {'id': tool, 'name': tool}, purchase_key=tool)
        self.mail.add_contact('victim', 'contact')
        self.mail.add_contact('contact', 'victim')

    def use(self, tool='friendKicker'):
        return self.client.post('/api/player-hack/tool/use', json={'victim_username': 'victim', 'tool_id': tool})

    def test_friend_rollback_and_replay_on_heavy_profiles(self):
        self.prepare(heavy=True)
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')), \
             patch.object(run, 'randint', return_value=1):
            original = self.messages.add_message
            def fail(*args, **kwargs):
                original(*args, **kwargs)
                raise RuntimeError('after notification')
            with patch.object(self.messages, 'add_message', side_effect=fail):
                self.assertEqual(self.use().status_code, 500)
            self.assertTrue(self.mail.is_contact('victim', 'contact'))
            self.assertTrue(self.mail.is_contact('contact', 'victim'))
            grant = self.access.get_active_access('attacker', 'victim')
            self.assertIsNone(self.access.get_tool_usage(grant, 'attacker', 'victim', 'friendKicker'))
            first = self.use()
            self.assertEqual(first.status_code, 200, first.json)
            self.assertTrue(first.json['removed'])
            with patch.object(run, 'randint', side_effect=AssertionError('reroll')):
                retry = self.use()
            self.assertTrue(retry.json['duplicate'])
            self.assertEqual(first.json['roll'], retry.json['roll'])
            self.assertFalse(self.mail.is_contact('victim', 'contact'))
            self.assertFalse(self.mail.is_contact('contact', 'victim'))
            security = self.use('securityPanelProxy')
            self.assertEqual(security.status_code, 200, security.json)
            self.assertEqual(security.json['security'], self.identity.get_player_security('victim'))

    def test_atomic_tool_concurrent_result_and_single_effect(self):
        self.prepare()
        grant = self.access.get_active_access('attacker', 'victim')
        calls = []
        def effect(conn):
            calls.append(1)
            self.mail.remove_contact('victim', 'contact', conn=conn)
            return {'removed': True, 'roll': 12}
        def execute(_):
            return self.access.commit_tool_result(grant, 'attacker', 'victim', 'friendKicker', effect)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(execute, range(2)))
        self.assertEqual(len(calls), 1)
        self.assertEqual(sum(bool(item.get('duplicate')) for item in results), 1)
        self.assertEqual({item['roll'] for item in results}, {12})

    def test_sniffer_recovery_after_transfer_without_reroll_or_heavy_reads(self):
        self.prepare(heavy=True)
        wallet = WalletStore(self.path)
        self.inventory.install_app('attacker', {'id': 'financialSniffer', 'name': 'Financial Sniffer'}, purchase_key='sniffer')
        self.stack.enter_context(patch.object(run, 'wallet_store', wallet))
        self.stack.enter_context(patch.object(run, 'wallet_balance_store', wallet.balance_store))
        self.stack.enter_context(patch.object(run, 'record_wallet_balance_delta'))
        before = wallet.balance_store.get_balance('attacker')
        with patch.object(self.users, 'get_profile', side_effect=AssertionError('heavy read')), \
             patch.object(run, 'randint', return_value=8), patch.object(run, 'random', return_value=0):
            with patch.object(self.messages, 'add_message', side_effect=RuntimeError('notification unavailable')):
                self.assertEqual(self.use('financialSniffer').status_code, 500)
            self.assertEqual(wallet.balance_store.get_balance('attacker'), before + 8)
            with patch.object(run, 'randint', side_effect=AssertionError('reroll')):
                recovered = self.use('financialSniffer')
                replay = self.use('financialSniffer')
            self.assertEqual(recovered.status_code, 200, recovered.json)
            self.assertEqual(replay.status_code, 200, replay.json)
            self.assertTrue(replay.json['duplicate'])
            self.assertEqual(wallet.balance_store.get_balance('attacker'), before + 8)
            with db_connect(self.path) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM system_messages WHERE source='financial_sniffer'").fetchone()[0], 1)
