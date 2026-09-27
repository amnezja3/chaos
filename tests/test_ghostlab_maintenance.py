import json
import os
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

import run
from database import db_connect, GameStateDeltaBus, WalletBalanceStore, JsonResourceStore
from player_security_store import PlayerSecurityStore
from ghostlab_registry import validate_fields, default_blueprint
from tests import test_ghostlab_alignment as fixture


class MaintenanceTest(unittest.TestCase):
    seed = fixture.GhostLabAlignmentTest.seed
    product = fixture.GhostLabAlignmentTest.product
    no_heavy = fixture.GhostLabAlignmentTest.no_heavy

    def setUp(self):
        fixture.GhostLabAlignmentTest.setUp(self)
        self.seed()
        self.stack.enter_context(patch.dict(os.environ, CHAOS_GHOSTLAB_MAINTENANCE_RUNTIME_ENABLED='true',
                                            CHAOS_GHOSTLAB_RUNTIME_ACTORS='*'))
        self.stack.enter_context(patch.object(run, 'delta_bus', GameStateDeltaBus(self.path)))
        self.security = PlayerSecurityStore(self.path)

    def make(self, kind='file_cleanup'):
        self.store, self.project, self.app = self.product(kind, kind)
        self.url = '/api/ghostlab/installed/' + self.app['id'] + '/maintenance'

    def preview(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def execute(self, plan):
        return self.client.post(self.url, json={'token': plan['token']})

    def files(self, *files):
        self.inventory.append_data_files('attacker', files)

    def junk(self, key, **kwargs):
        return dict(id=key, name=key, file_category='camera', sellable=False, file_size=3,
                    resource_types=[], **kwargs)

    def test_cleanup_real_effect_empty_new_files_and_retry(self):
        self.make()
        self.files(self.junk('junk'))
        with self.no_heavy():
            preview = self.preview()
            self.assertEqual(preview['preview']['count'], 1)
            first = self.execute(preview)
            self.assertEqual(first.status_code, 200, first.json)
            self.assertEqual((first.json['count'], first.json['freed_mb']), (1, 3))
            retry = self.execute(preview)
            self.assertTrue(retry.json['duplicate'])
            self.assertEqual(retry.json['storage'], first.json['storage'])
            empty = self.execute(self.preview())
            self.assertEqual(empty.json['count'], 0)
            self.assertIn('już czysty', empty.json['message'])
            self.files(self.junk('junk'))  # A late operation retry cannot resurrect cleaned data.
            self.assertEqual(self.preview()['preview']['count'], 0)
            self.files(self.junk('new'))
            self.assertEqual(self.execute(self.preview()).json['count'], 1)

    def test_protected_market_operation_and_unknown_files(self):
        self.make()
        self.files(self.junk('safe'), self.junk('core', core=True), self.junk('purchase', purchased=True),
                   self.junk('googleplex', googleplex_sellable=True), self.junk('unknown_op', operation_id='missing'),
                   dict(self.junk('market'), resource_types=['camera_dump']),
                   dict(self.junk('sellable'), sellable=True),
                   dict(self.junk('tools'), file_category='tools'),
                   dict(self.junk('system'), file_category='system'), self.junk('listed', market_status='listed'))
        with self.no_heavy():
            preview = self.preview()
            self.assertEqual([f['id'] for f in preview['preview']['files']], ['safe'])
            self.execute(preview)
        self.assertEqual(len(self.inventory.list_data_files('attacker')), 9)

    def test_rechecks_versions_and_sellability_and_does_not_delete_new_files(self):
        self.make()
        self.files(self.junk('changed'), self.junk('sale'))
        plan = self.preview()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_data_files SET version=version+1 WHERE file_id='changed'")
            conn.execute("UPDATE player_data_files SET market_status='listed' WHERE file_id='sale'")
        self.files(self.junk('new'))
        with self.no_heavy():
            result = self.execute(plan)
            self.assertEqual(result.json['count'], 0)
            self.assertEqual(len(self.inventory.list_data_files('attacker')), 3)

    def test_security_presets_conflicts_cas_noop_and_retry(self):
        self.make('security_restore')
        # Existing profile keys only, including a real conflict pair.
        pair = next((key, others[0]) for key, others in run.SECURITY_CONFLICTS.items() if others)
        for preset in ('open', 'low', 'regular', 'all'):
            self.security.update('attacker', lambda _: {pair[0]: True, pair[1]: False, 'firewall': False})
            from ghostlab_maintenance import restore_preset
            values = restore_preset(self.security.get('attacker')['security'], preset,
                                    run.build_security_preset, run.SECURITY_CONFLICTS)
            self.assertFalse(values[pair[0]] and values[pair[1]])
        with self.no_heavy():
            plan = self.preview()
            self.security.update('attacker', lambda s: dict(s, firewall=not s['firewall']))
            self.assertEqual(self.execute(plan).status_code, 409)
            plan = self.preview()
            response = self.execute(plan)
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(response.json['security'], self.security.get('attacker')['security'])
            self.assertTrue(self.execute(plan).json['duplicate'])
            self.assertEqual(self.execute(self.preview()).json['changed'], [])

    def test_presentation_is_only_a_receipt_and_not_pvp(self):
        self.make('system_update')
        before = self.security.get('attacker')
        with db_connect(self.path) as conn:
            storage = tuple(conn.execute('SELECT used,version FROM player_storage WHERE username=?', ('attacker',)).fetchone())
        with self.no_heavy():
            state = self.client.get('/api/ghostlab/installed/' + self.app['id'])
            self.assertEqual(state.status_code, 200, state.json)
            self.assertIsNone(state.json['access'])
            self.assertEqual(state.json['product']['launch_mode'], 'own_system')
            self.assertNotIn(self.app['id'], [t['id'] for t in self.client.get('/api/player-hack/access').json['tools']])
            result = self.execute(self.preview())
            self.assertEqual(result.status_code, 200, result.json)
            self.assertEqual(self.security.get('attacker'), before)
            with db_connect(self.path) as conn:
                self.assertEqual(tuple(conn.execute('SELECT used,version FROM player_storage WHERE username=?', ('attacker',)).fetchone()), storage)

    def test_uninstall_withdraw_flag_and_tampering(self):
        self.make()
        plan = self.preview()
        self.store.withdraw('attacker', self.project['id'], self.project['revision'])
        self.assertEqual(self.execute(plan).status_code, 200)
        self.assertEqual(self.client.post(self.url, json={'token': plan['token'] + 'bad'}).status_code, 409)
        with patch.dict(os.environ, CHAOS_GHOSTLAB_MAINTENANCE_RUNTIME_ENABLED='false'):
            self.assertEqual(self.execute(plan).status_code, 403)
        self.inventory.uninstall_app('attacker', app_id=self.app['id'])
        self.assertEqual(self.execute(plan).status_code, 403)

    def test_transaction_rollback_if_delta_fails(self):
        self.make()
        self.files(self.junk('stay'))
        plan = self.preview()
        with patch.object(run.delta_bus, 'record_change', side_effect=RuntimeError('outbox unavailable')):
            self.assertEqual(self.execute(plan).status_code, 500)
        self.assertEqual(self.preview()['preview']['count'], 1)
        self.assertEqual(self.execute(plan).json['count'], 1)

    def test_schema_and_scope_selection(self):
        self.assertTrue(validate_fields('security_restore', {'preset': 'secure'}))
        fields = default_blueprint('system_update')
        self.assertTrue(validate_fields('system_update', dict(fields, log_1='x' * 181)))
        self.make()
        self.files(self.junk('camera'))
        from ghostlab_maintenance import candidates
        with db_connect(self.path) as conn:
            self.assertEqual(candidates(conn, 'attacker', {'camera': False}, run.is_ghost_exchange_sellable), [])

    def test_concurrent_retries_commit_once(self):
        self.make()
        self.files(self.junk('once'))
        plan = self.preview()
        clients = [run.app.test_client(), run.app.test_client()]
        with self.client.session_transaction() as active_session:
            session_copy = dict(active_session)
        for client in clients:
            with client.session_transaction() as active_session:
                active_session.update(session_copy)
            client.environ_base.update(self.client.environ_base)
        with self.no_heavy(), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda client: client.post(self.url, json={'token': plan['token']}), clients))
        self.assertEqual([r.status_code for r in results], [200, 200])
        self.assertEqual(sorted(r.json['duplicate'] for r in results), [False, True])
        self.assertEqual(self.preview()['preview']['count'], 0)

    def test_completed_recon_and_unused_installer_mapping(self):
        self.make()
        with db_connect(self.path) as conn:
            for key, status in [('done', 'completed'), ('active', 'running')]:
                conn.execute('INSERT INTO player_operations(operation_id,username,status,created_at,updated_at) VALUES (?,?,?,?,?)',
                             (key, 'attacker', status, 'now', 'now'))
        self.files(*[dict(self.junk(key), file_category='system', resource_types=['internal_recon_state'], operation_id=key)
                     for key in ('done', 'active')],
                   dict(self.junk('installer'), file_category='installers', disposable=True),
                   dict(self.junk('system_junk'), file_category='system', disposable=True))
        plan = self.preview()
        self.assertEqual({f['id'] for f in plan['preview']['files']}, {'done', 'installer', 'system_junk'})
        self.assertEqual(self.execute(plan).json['count'], 3)

    def test_stale_profile_mirror_cannot_resurrect_removed_files(self):
        self.make()
        file = self.junk('stale')
        self.files(file)
        stale = {'files': {'camera': [file]}}
        self.assertEqual(self.execute(self.preview()).json['count'], 1)
        mirrored = self.inventory.mirror_profile('attacker', stale)
        self.assertEqual(mirrored['files']['camera'], [])

    def test_detention_denies_execution_and_receipt(self):
        from datetime import datetime, timezone
        from response_network.sanctions import SanctionStore
        from response_network.consequence_table import plan_consequence
        self.make()
        self.files(self.junk('detained'))
        plan = self.preview()
        sanctions = SanctionStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sanctions.impose(conn, encounter_id='maintenance-detention', actor_id='attacker', incident_id='test',
                             plan=plan_consequence(5, 0), now=datetime.now(timezone.utc))
        with self.no_heavy():
            self.assertIn(self.execute(plan).status_code, (403, 409))
        self.assertEqual(len(self.inventory.list_data_files('attacker')), 1)

    def test_explicit_artifact_update_invalidates_old_preview(self):
        self.make('system_update')
        old = self.app['artifact_id']
        plan = self.preview()
        p = self.store.update('attacker', self.project['id'], self.project['revision'],
                              {'blueprint': dict(self.project['blueprint'], log_1='New log')})
        p = self.store.compile('attacker', p['id'], p['revision'], p['blueprint'], run.build_ghostlab_artifact)
        p, app = self.store.publish('attacker', p['id'], p['revision'], p['artifact']['artifact_id'],
                                    run.build_ghostlab_googleplex_app, {'level': 40, 'respect': 500})
        with self.no_heavy():
            response = self.client.post('/api/ghostlab/installed/' + app['id'], json={
                'expected_artifact_id': old, 'artifact_id': app['artifact_id']})
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(response.json['product']['blueprint']['log_1'], 'New log')
            self.assertEqual(self.execute(plan).status_code, 400)

    def test_all_three_products_purchase_and_execute_on_non_author_account(self):
        wallet = WalletBalanceStore(self.path)
        self.stack.enter_context(patch.object(run, 'wallet_balance_store', wallet))
        self.stack.enter_context(patch.object(run, 'resources_store', JsonResourceStore(self.path)))
        wallet.credit('victim', 100000, transaction_key='maintenance-test-fund', source='test')
        products = [self.product(kind, kind)[2] for kind in ('file_cleanup', 'system_update', 'security_restore')]
        self.generation.authenticate(self.client, 'victim')
        before = wallet.get_balance('attacker')
        with self.no_heavy():
            for product in products:
                response = self.client.post('/install-app', json={'app_id': product['id']})
                self.assertEqual(response.status_code, 200, response.json)
                self.assertEqual(response.json['status'], 'success')
                self.assertTrue(self.client.post('/install-app', json={'app_id': product['id']}).json['duplicate'])
                self.url = '/api/ghostlab/installed/' + product['id'] + '/maintenance'
                balance = wallet.get_balance('victim')
                self.assertEqual(self.execute(self.preview()).status_code, 200)
                self.assertEqual(wallet.get_balance('victim'), balance)
            self.assertEqual(wallet.get_balance('attacker'), before + sum(p['price'] for p in products))


if __name__ == '__main__':
    unittest.main()
