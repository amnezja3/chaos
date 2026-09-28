import json
import os
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

import run
import ghostlab_firmware as firmware
from database import db_connect, GameStateDeltaBus, WalletBalanceStore
from ghostlab_registry import default_blueprint, validate_fields
from tests import test_ghostlab_alignment as fixture


class FirmwareTest(unittest.TestCase):
    seed = fixture.GhostLabAlignmentTest.seed
    product = fixture.GhostLabAlignmentTest.product
    no_heavy = fixture.GhostLabAlignmentTest.no_heavy

    def setUp(self):
        fixture.GhostLabAlignmentTest.setUp(self)
        self.seed()
        self.stack.enter_context(patch.dict(os.environ, CHAOS_GHOSTLAB_FIRMWARE_RUNTIME_ENABLED='true', CHAOS_GHOSTLAB_RUNTIME_ACTORS='*'))
        self.stack.enter_context(patch.object(run, 'delta_bus', GameStateDeltaBus(self.path)))
        self.stack.enter_context(patch.object(run, 'wallet_balance_store', WalletBalanceStore(self.path)))
        self.store, self.project, self.app = self.product('Flash', 'firmware_update')
        self.url = '/api/ghostlab/firmware/' + self.app['id']

    def buy(self, key='one'):
        response = self.client.post(self.url + '/purchase', json=dict(client_action_key=key,
            expected_artifact_id=self.app['artifact_id'], expected_price=self.app['price']))
        self.assertEqual(response.status_code, 200, response.json)
        return response.json['receipt']

    def flash(self, receipt):
        return self.client.post(self.url, json=dict(receipt=receipt, disk_mb=999999, success_percent=100))

    def test_schema_bounds(self):
        base = default_blueprint('firmware_update')
        for key, low, high in [('success_percent', 20, 80), ('disk_mb', 50, 200), ('scan_m', 10, 100)]:
            for value in (low, high):
                self.assertFalse(validate_fields('firmware_update', dict(base, **{key: value})))
            for value in (low - 1, high + 1, True, float('nan')):
                self.assertTrue(validate_fields('firmware_update', dict(base, **{key: value})))

    def test_success_canonical_retry_and_cooldown(self):
        before = self.inventory.snapshot('attacker')['storage']
        with self.no_heavy(), patch.object(firmware.secrets, 'randbelow', return_value=0) as roll:
            receipt = self.buy()
            self.assertEqual(self.buy(), receipt)
            result = self.flash(receipt)
            self.assertEqual(result.status_code, 200, result.json)
            self.assertEqual((result.json['disk_mb'], result.json['scan_m']), (100, 50))
            self.assertTrue(self.flash(receipt).json['duplicate'])
            self.assertEqual(roll.call_count, 1)
            self.assertEqual(self.client.post(self.url + '/purchase', json=dict(client_action_key='two',
                expected_artifact_id=self.app['artifact_id'], expected_price=self.app['price'])).status_code, 409)
            self.assertEqual(self.inventory.snapshot('attacker')['storage']['capacity'], before['capacity'] + 100)
            self.assertEqual(self.inventory.snapshot('attacker')['storage']['used'], before['used'])
            with db_connect(self.path) as conn:
                self.assertEqual(firmware.scan_range(conn, 'attacker', 4000), 4050)
                self.assertLessEqual(self.capabilities.get_capabilities('attacker', conn=conn)['action_range'], 4000)

    def test_failure_crash_guard_restart_and_retry(self):
        receipt = self.buy()
        with db_connect(self.path) as conn:
            conn.execute("INSERT INTO ghostlab_scanner_leases VALUES ('attacker','gen','window','token','app','artifact',9999999999)")
        with self.no_heavy(), patch.object(firmware.secrets, 'randbelow', return_value=9999):
            result = self.flash(receipt)
            self.assertEqual(result.status_code, 200, result.json)
            self.assertFalse(result.json['succeeded'])
            with db_connect(self.path) as conn:
                self.assertIsNone(conn.execute("SELECT 1 FROM ghostlab_scanner_leases WHERE username='attacker'").fetchone())
            self.assertEqual(result.json['disk_mb'], 0)
            self.assertTrue(self.flash(receipt).json['duplicate'])
            self.assertEqual(self.client.get('/api/player-hack/access').status_code, 423)
            current = self.client.get('/api/firmware/state').json
            self.assertEqual(self.client.post('/api/firmware/restart', json={'crash_id': current['crash_id']}).status_code, 409)
            with patch.object(firmware.time, 'time', return_value=current['restart_after'] + 1):
                self.assertEqual(self.client.post('/api/firmware/restart', json={'crash_id': 'forged'}).status_code, 409)
                self.assertEqual(self.client.post('/api/firmware/restart', json={'crash_id': current['crash_id']}).status_code, 200)
            self.assertFalse(self.client.get('/api/firmware/state').json['crash_id'])
            self.assertEqual(self.client.get('/api/firmware/state').json['cooldown_until'], current['cooldown_until'])

    def test_limits_partial_and_no_downgrade(self):
        caps = self.capabilities.get_capabilities('attacker')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_storage SET capacity=? WHERE username='attacker'", (firmware.DISK_LIMIT_MB - 10,))
            conn.execute('INSERT INTO ghostlab_firmware_state VALUES (?,?,0,\'\',0)', ('attacker', 30000 - caps['action_range'] - 3))
        with self.no_heavy(), patch.object(firmware.secrets, 'randbelow', return_value=0):
            result = self.flash(self.buy()).json
            self.assertEqual((result['disk_mb'], result['scan_m']), (10, 3))
            with db_connect(self.path) as conn:
                conn.execute("UPDATE ghostlab_firmware_state SET cooldown_until=0 WHERE username='attacker'")
                conn.execute("UPDATE player_storage SET capacity=? WHERE username='attacker'", (firmware.DISK_LIMIT_MB + 1,))
            response = self.client.post(self.url + '/purchase', json=dict(client_action_key='next',
                expected_artifact_id=self.app['artifact_id'], expected_price=self.app['price']))
            self.assertEqual(response.status_code, 409)
            self.assertEqual(self.inventory.snapshot('attacker')['storage']['capacity'], firmware.DISK_LIMIT_MB + 1)

    def test_rollback_preserves_paid_attempt(self):
        receipt = self.buy()
        before = self.inventory.snapshot('attacker')['storage']['capacity']
        with patch.object(run.delta_bus, 'record_change', side_effect=RuntimeError('rollback')), patch.object(firmware.secrets, 'randbelow', return_value=0):
            with self.assertRaises(RuntimeError):
                firmware.execute('attacker', self.app['id'], receipt, vars(run))
        with db_connect(self.path) as conn:
            self.assertIsNone(conn.execute('SELECT result_json FROM ghostlab_firmware_attempts WHERE receipt=?', (receipt,)).fetchone()[0])
            self.assertFalse(firmware.state(conn, 'attacker')['cooldown_until'])
        self.assertEqual(self.inventory.snapshot('attacker')['storage']['capacity'], before)

    def test_concurrent_execute_rolls_once(self):
        receipt = self.buy()
        with patch.object(firmware.secrets, 'randbelow', return_value=0) as roll:
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: firmware.execute('attacker', self.app['id'], receipt, vars(run)), range(2)))
            self.assertEqual(roll.call_count, 1)
            self.assertEqual(sum(r['duplicate'] for r in results), 1)

    def test_uninstall_reinstall_and_free_update_do_not_renew_attempt(self):
        receipt = self.buy()
        with patch.object(firmware.secrets, 'randbelow', return_value=0):
            self.flash(receipt)
        self.inventory.uninstall_app('attacker', app_id=self.app['id'])
        self.inventory.install_app('attacker', self.app, purchase_key='reinstall')
        with self.no_heavy():
            data = self.client.get(self.url).json
            self.assertIsNone(data['pending'])
            self.assertGreater(data['state']['scan_bonus'], 0)
            self.assertGreater(data['state']['cooldown_until'], data['server_time'])

    def test_pending_survives_withdrawal_and_is_pinned(self):
        receipt = self.buy()
        self.store.withdraw('attacker', self.project['id'], self.project['revision'])
        with self.no_heavy(), patch.object(firmware.secrets, 'randbelow', return_value=0):
            self.assertEqual(self.client.get(self.url).json['pending'], receipt)
            self.assertTrue(self.flash(receipt).json['succeeded'])
            self.assertEqual(self.client.post('/api/ghostlab/installed/' + self.app['id'] + '/maintenance', json={}).status_code, 400)

    def test_pending_blocks_second_product_and_wrong_actor(self):
        receipt = self.buy()
        _, _, other = self.product('Second', 'firmware_update')
        response = self.client.post('/api/ghostlab/firmware/' + other['id'] + '/purchase', json=dict(client_action_key='two',
            expected_artifact_id=other['artifact_id'], expected_price=other['price']))
        self.assertEqual(response.status_code, 409)
        with self.assertRaises(firmware.GhostLabError):
            firmware.execute('victim', self.app['id'], receipt, vars(run))

    def test_googleplex_purchase_payment_and_rollback(self):
        self.generation.authenticate(self.client, 'victim')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE wallet_balances SET balance=1000000 WHERE username='victim'")
        before = run.wallet_balance_store.get_balance('attacker')
        body = dict(app_id=self.app['id'], client_action_key='paid', expected_artifact_id=self.app['artifact_id'], expected_price=self.app['price'])
        with self.no_heavy():
            with patch.object(run.delta_bus, 'record_change', side_effect=RuntimeError('payment rollback')):
                with self.assertRaises(RuntimeError):
                    firmware.purchase('victim', self.app['id'], body, vars(run))
            self.assertEqual(run.wallet_balance_store.get_balance('victim'), 1000000)
            self.assertFalse(self.inventory.has_app('victim', self.app['id']))
            response = self.client.post('/install-app', json=body)
            self.assertEqual(response.status_code, 200, response.json)
            self.assertTrue(self.client.post('/install-app', json=body).json['duplicate'])
            self.assertTrue(self.inventory.has_app('victim', self.app['id']))
            self.assertEqual(run.wallet_balance_store.get_balance('victim'), 1000000 - self.app['price'])
            self.assertEqual(run.wallet_balance_store.get_balance('attacker'), before + self.app['price'])
            self.assertEqual(self.client.get(self.url).json['pending'], response.json['receipt'])

    def test_free_update_keeps_purchased_policy_and_does_not_create_entitlement(self):
        receipt = self.buy()
        old = self.app['artifact_id']
        p = self.store.update('attacker', self.project['id'], self.project['revision'],
            {'blueprint': dict(self.project['blueprint'], disk_mb=200, scan_m=100)})
        p = self.store.compile('attacker', p['id'], p['revision'], p['blueprint'], run.build_ghostlab_artifact)
        p, new_app = self.store.publish('attacker', p['id'], p['revision'], p['artifact']['artifact_id'],
                                       run.build_ghostlab_googleplex_app, dict(level=40, respect=500))
        with self.no_heavy(), patch.object(firmware.secrets, 'randbelow', return_value=0):
            result = self.client.post('/api/ghostlab/installed/' + self.app['id'], json=dict(expected_artifact_id=old, artifact_id=new_app['artifact_id']))
            self.assertEqual(result.status_code, 200, result.json)
            self.assertEqual(self.client.get(self.url).json['policy']['disk_mb'], 100)
            self.assertEqual(self.flash(receipt).json['disk_mb'], 100)
            self.assertIsNone(self.client.get(self.url).json['pending'])

    def test_reinstall_pending_attempt_is_free_even_after_withdrawal(self):
        receipt = self.buy()
        self.inventory.uninstall_app('attacker', app_id=self.app['id'])
        self.store.withdraw('attacker', self.project['id'], self.project['revision'])
        with self.no_heavy():
            self.assertEqual(self.buy('restore'), receipt)
            self.assertTrue(self.inventory.has_app('attacker', self.app['id']))
            with db_connect(self.path) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM ghostlab_firmware_attempts').fetchone()[0], 1)

    def test_cooldown_shared_after_success_and_next_paid_attempt(self):
        with patch.object(firmware.secrets, 'randbelow', return_value=0):
            result = self.flash(self.buy()).json
            self.store, self.project, self.app = self.product('Other firmware', 'firmware_update')
            self.url = '/api/ghostlab/firmware/' + self.app['id']
            body = dict(client_action_key='next', expected_artifact_id=self.app['artifact_id'], expected_price=self.app['price'])
            with patch.object(firmware.time, 'time', return_value=result['cooldown_until'] - 1):
                self.assertEqual(self.client.post(self.url + '/purchase', json=body).status_code, 409)
            with patch.object(firmware.time, 'time', return_value=result['cooldown_until']):
                second = self.flash(self.buy('next')).json
                self.assertTrue(second['succeeded'])
                self.assertEqual(second['scan_range_m'], result['scan_range_m'] + 50)

    def test_stale_profile_save_preserves_capacity_and_scan_bonus(self):
        stale = self.users.get_profile_with_revision('attacker')
        with patch.object(firmware.secrets, 'randbelow', return_value=0):
            result = self.flash(self.buy()).json
        self.users.save_profile_guarded(stale['profile'], source='test.firmware', expected_revision=stale['profile_revision'])
        self.assertEqual(self.inventory.snapshot('attacker')['storage']['capacity'], result['storage']['capacity'])
        with db_connect(self.path) as conn:
            self.assertEqual(firmware.state(conn, 'attacker')['scan_bonus'], 50)

    def test_arrest_and_disabled_runtime_do_not_consume(self):
        from datetime import datetime, timezone
        from response_network.sanctions import SanctionStore
        from response_network.consequence_table import plan_consequence
        receipt = self.buy()
        with patch.dict(os.environ, CHAOS_GHOSTLAB_FIRMWARE_RUNTIME_ENABLED='false'):
            self.assertEqual(self.flash(receipt).status_code, 403)
        sanctions = SanctionStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sanctions.impose(conn, encounter_id='firmware-detention', actor_id='attacker', incident_id='test',
                             plan=plan_consequence(5, 0), now=datetime.now(timezone.utc))
        self.assertIn(self.flash(receipt).status_code, (403, 409))
        with db_connect(self.path) as conn:
            self.assertIsNone(conn.execute('SELECT result_json FROM ghostlab_firmware_attempts WHERE receipt=?', (receipt,)).fetchone()[0])

    def test_real_scan_gate_uses_firmware_without_changing_action_radius(self):
        base = self.capabilities.get_capabilities('attacker')['action_range']
        with patch.object(run.player_position_store, 'get_position', return_value={'lat': 52, 'lng': 21}), \
             patch.object(run.Haversine, 'haversine_distance', return_value=base + 25), \
             patch.object(run, 'GHOSTNETWORK_ABILITIES_ENABLED', False), \
             patch.object(run, 'foreign_territory_action_block', return_value=None), \
             patch.object(run.player_marked_target_store, 'list_targets', return_value=[]), \
             patch.object(run.fetcher, 'get_all', side_effect=RuntimeError('test scan reached fetch')) as fetcher, self.no_heavy():
            before = self.client.post('/map-action', json=dict(action='scan', lat=52.01, lng=21))
            self.assertEqual(before.status_code, 200, before.json)
            self.assertEqual(before.json['scan_context']['action_range_m'], base)
            fetcher.assert_not_called()
            with patch.object(firmware.secrets, 'randbelow', return_value=0):
                self.flash(self.buy())
            after = self.client.post('/map-action', json=dict(action='scan', lat=52.01, lng=21))
            self.assertEqual(after.status_code, 200, after.json)
            fetcher.assert_called_once()
            self.assertEqual(self.capabilities.get_capabilities('attacker')['action_range'], base)


if __name__ == '__main__':
    unittest.main()
