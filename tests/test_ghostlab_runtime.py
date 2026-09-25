import json
import os
import unittest
from unittest.mock import patch

import run
import database
from database import db_connect
from tests.test_ghostlab_alignment import GhostLabAlignmentTest
from tests.test_player_hack_read_paths import valid_profile


class GhostLabRuntimeTest(unittest.TestCase):
    setUp = GhostLabAlignmentTest.setUp
    seed = GhostLabAlignmentTest.seed
    product = GhostLabAlignmentTest.product
    no_heavy = GhostLabAlignmentTest.no_heavy

    def prepare(self):
        self.seed()
        self.stack.enter_context(patch.dict(os.environ, CHAOS_GHOSTLAB_LOG_RUNTIME_ENABLED='true',
                                           CHAOS_GHOSTLAB_RUNTIME_ACTORS='victim,attacker'))
        self.wallet = database.WalletBalanceStore(self.path)
        self.stack.enter_context(patch.object(run, 'wallet_balance_store', self.wallet))
        self.stack.enter_context(patch.object(run, 'resources_store', database.JsonResourceStore(self.path)))
        self.stack.enter_context(patch.object(run, 'delta_bus', database.GameStateDeltaBus(self.path)))
        record = self.users.get_profile_with_revision('victim')
        self.users.save_profile_guarded(dict(record['profile'], level=40, respect=500),
                                       source='test', expected_revision=record['profile_revision'])
        self.wallet.credit('victim', 10000, transaction_key='fund', source='test')
        self.users.save_profile(valid_profile('target'))
        self.inventory.seed_from_profile('target', valid_profile('target'))
        self.store, self.project, self.app = self.product(name='Own Logs')
        self.access.grant_access('victim', 'target')
        self.generation.authenticate(self.client, 'victim')

    def buy(self):
        response = self.client.post('/install-app', json={'app_id': self.app['id']})
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def use(self, **extra):
        product = run.resolve_player_hack_product('victim', self.app['id']) or {}
        return self.client.post('/api/player-hack/tool/use', json={
            'tool_id': self.app['id'], 'artifact_id':product.get('artifact_id'), 'victim_username': 'target', **extra})

    def new_build(self, **blueprint):
        project = self.store.get('attacker', self.project['id'])
        project = self.store.update('attacker', project['id'], project['revision'],
                                    {'blueprint': dict(project['blueprint'], **blueprint)})
        project = self.store.compile('attacker', project['id'], project['revision'], project['blueprint'], run.build_ghostlab_artifact)
        self.project, self.app = self.store.publish('attacker', project['id'], project['revision'],
            project['artifact']['artifact_id'], run.build_ghostlab_googleplex_app, {'level':40,'respect':500})

    def test_three_accounts_purchase_read_policy_and_family_retry(self):
        self.prepare()
        self.new_build(log_limit=2, include_type=False, include_status=False, include_created_at=False)
        for i in range(7):
            self.messages.add_message('target', {'id': str(i), 'text': 'safe' + str(i), 'created_at':f'2026-09-25T01:00:0{i}'})
        self.messages.add_message('attacker', {'text':'OTHER_SECRET'})
        before = self.wallet.get_balance('attacker')
        with self.no_heavy():
            self.buy()
            self.assertTrue(self.buy()['duplicate'])
            self.assertEqual(self.wallet.get_balance('attacker'), before + self.app['price'])
            response = self.use(blueprint={'log_limit':100, 'redaction_policy':'all'}, victim_override='attacker')
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual([r['text'] for r in response.json['logs']], ['safe5','safe6'])
            self.assertFalse(any(k in r for r in response.json['logs'] for k in ('type','status','created_at')))
            self.assertEqual(response.json['tool']['name'], 'Own Logs')
            self.assertEqual(response.json['tool']['artifact_id'], self.app['artifact_id'])
            self.assertEqual(self.use().status_code, 409)
            self.inventory.install_app('victim', run.get_pro_system_tool('systemLogReader'), purchase_key='parent')
            self.assertEqual(self.use(tool_id='systemLogReader').status_code, 409)
            self.assertEqual(self.inventory.catalog_download_counts([self.app['id']])[self.app['id']], 1)

    def test_explicit_update_is_atomic_free_and_does_not_reset_usage(self):
        self.prepare()
        with self.no_heavy(): self.buy()
        old = self.app['artifact_id']
        self.new_build(log_limit=1)
        url = '/api/ghostlab/installed/' + self.app['id']
        balance = self.wallet.get_balance('victim')
        with self.no_heavy():
            state = self.client.get(url).json
            self.assertEqual(state['product']['artifact_id'], old)
            self.assertTrue(state['update_available'])
            self.assertEqual(self.use().status_code, 200)  # Empty is a real successful result.
            payload = {'expected_artifact_id': old, 'artifact_id': self.app['artifact_id']}
            result = self.client.post(url, json=payload)
            self.assertEqual(result.status_code, 200, result.json)
            self.assertEqual(result.json['product']['artifact_id'], self.app['artifact_id'])
            self.assertTrue(self.client.post(url, json=payload).json['duplicate'])
            self.assertEqual(self.wallet.get_balance('victim'), balance)
            self.assertEqual(self.inventory.catalog_download_counts([self.app['id']])[self.app['id']], 1)
            self.assertEqual(self.use().status_code, 409)
            self.assertEqual(len([a for a in self.inventory.desktop_apps('victim') if a['id']==self.app['id']]), 1)
            for i in range(3):
                self.messages.add_message('target', {'id':'after-update-'+str(i),'text':'new'+str(i),'created_at':f'2026-09-25T02:00:0{i}'})
            with db_connect(self.path) as conn:
                conn.execute("UPDATE player_hack_access SET hacked_until='2000-01-01',cooldown_until='2000-01-01' WHERE attacker_username='victim'")
            self.access.grant_access('victim','target',access_minutes=6)
            read = self.use()
            self.assertEqual(read.status_code,200,read.json)
            self.assertEqual([item['text'] for item in read.json['logs']], ['new2'])

    def test_disabled_legacy_missing_access_and_uninstall(self):
        self.prepare()
        with self.no_heavy():
            self.buy()
            with patch.dict(os.environ, CHAOS_GHOSTLAB_RUNTIME_ACTORS='nobody'):
                self.assertEqual(self.use().status_code, 409)
            with patch.dict(os.environ, CHAOS_GHOSTLAB_LOG_RUNTIME_ENABLED='false'):
                self.assertEqual(self.use().status_code, 409)
            self.assertEqual(self.use(victim_username='attacker').status_code, 403)
            self.assertEqual(self.use(artifact_id='forged').status_code, 409)
            with db_connect(self.path) as conn:
                artifact = json.loads(conn.execute('SELECT artifact_json FROM ghostlab_builds WHERE artifact_id=?', (self.app['artifact_id'],)).fetchone()[0])
                artifact.pop('runtime_revision')
                conn.execute('UPDATE ghostlab_builds SET artifact_json=? WHERE artifact_id=?', (json.dumps(artifact), self.app['artifact_id']))
            self.assertEqual(self.use().status_code, 409)
            self.inventory.uninstall_app('victim', app_id=self.app['id'])
            self.assertEqual(self.use().status_code, 403)

    def test_read_failure_rolls_back_receipt(self):
        self.prepare()
        self.buy()
        access = self.access.get_active_access('victim', 'target')
        with self.no_heavy(), patch.object(self.messages, 'recent_player_hack_logs', side_effect=RuntimeError('storage unavailable')):
            response = self.use()
            self.assertGreaterEqual(response.status_code, 500)
        self.assertIsNone(self.access.get_tool_usage(access, 'victim','target','systemLogReader'))

    def test_detention_and_expired_access_do_not_read(self):
        self.prepare()
        self.buy()
        from datetime import datetime, timezone
        from response_network.sanctions import SanctionStore
        from response_network.consequence_table import plan_consequence
        sanctions = SanctionStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sanctions.impose(conn, encounter_id='detain', actor_id='victim', incident_id='test',
                plan=plan_consequence(5, 0), now=datetime.now(timezone.utc))
        with self.no_heavy(), patch.object(self.messages, 'recent_player_hack_logs', side_effect=AssertionError('must not read')):
            self.assertIn(self.use().status_code, (403,409))

    def test_update_failure_rolls_back_inventory_and_storage(self):
        self.prepare()
        self.buy()
        old = self.app['artifact_id']
        self.new_build(log_limit=1)
        url = '/api/ghostlab/installed/' + self.app['id']
        with db_connect(self.path) as conn:
            before = dict(conn.execute("SELECT * FROM player_storage WHERE username='victim'").fetchone())
        with self.no_heavy(), patch.object(run.delta_bus, 'record_change', side_effect=RuntimeError('delta down')):
            response = self.client.post(url, json={'expected_artifact_id':old, 'artifact_id':self.app['artifact_id']})
            self.assertGreaterEqual(response.status_code,500)
        self.assertEqual(self.client.get(url).json['product']['artifact_id'], old)
        with db_connect(self.path) as conn:
            self.assertEqual(before, dict(conn.execute("SELECT * FROM player_storage WHERE username='victim'").fetchone()))

    def test_revocation_during_read_rolls_back_receipt(self):
        self.prepare()
        self.buy()
        access = self.access.get_active_access('victim', 'target')
        def revoked(username, *, conn):
            conn.execute("UPDATE player_hack_access SET hacked_until='2000-01-01' WHERE attacker_username='victim'")
            return [{'text':'must not escape'}]
        with self.no_heavy(), patch.object(self.messages, 'recent_player_hack_logs', side_effect=revoked):
            response = self.use()
            self.assertEqual(response.status_code,409,response.json)
            self.assertNotIn('logs', response.json)
        self.assertIsNone(self.access.get_tool_usage(access,'victim','target','systemLogReader'))

    def test_concurrent_family_reads_return_one_result(self):
        self.prepare()
        self.buy()
        from concurrent.futures import ThreadPoolExecutor
        from ghostlab_runtime import execute_logs
        product = run.resolve_player_hack_product('victim', self.app['id'])
        access = self.access.get_active_access('victim','target')
        guard = run.player_hack_write_guard('victim','target', self.app['id'], access)
        def execute():
            return execute_logs('victim','target',product,access,self.access,self.messages,guard,run.PRO_SYSTEM_TOOLS)
        with self.no_heavy(), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: execute(), range(2)))
        self.assertEqual(sum(bool(result.get('success')) for result in results),1)
        self.assertEqual(sum(bool(result.get('duplicate')) for result in results),1)

    def test_update_requires_space_and_expected_build(self):
        self.prepare()
        self.buy()
        old = self.app['artifact_id']
        self.new_build(log_limit=1)
        url = '/api/ghostlab/installed/' + self.app['id']
        with db_connect(self.path) as conn:
            available = json.loads(conn.execute('SELECT app_json FROM ghostlab_publications WHERE app_id=?', (self.app['id'],)).fetchone()[0])
            available['disk_usage'] = 999999
            conn.execute('UPDATE ghostlab_publications SET app_json=? WHERE app_id=?', (json.dumps(available), self.app['id']))
        with self.no_heavy():
            self.assertEqual(self.client.post(url, json={'expected_artifact_id':'forged','artifact_id':self.app['artifact_id']}).status_code,409)
            response = self.client.post(url, json={'expected_artifact_id':old,'artifact_id':self.app['artifact_id']})
            self.assertEqual(response.status_code,400,response.json)
            self.assertEqual(self.client.get(url).json['product']['artifact_id'],old)

    def test_expired_access_refuses_before_logs(self):
        self.prepare()
        self.buy()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_hack_access SET hacked_until='2000-01-01' WHERE attacker_username='victim'")
        with self.no_heavy(), patch.object(self.messages,'recent_player_hack_logs',side_effect=AssertionError('must not read')):
            self.assertEqual(self.use().status_code,403)

    def test_compile_upgrades_legacy_without_editing_blueprint(self):
        self.prepare()
        with db_connect(self.path) as conn:
            project = json.loads(conn.execute('SELECT project_json FROM ghostlab_projects WHERE id=?', (self.project['id'],)).fetchone()[0])
            project['artifact'].pop('runtime_revision')
            conn.execute('UPDATE ghostlab_projects SET project_json=? WHERE id=?', (json.dumps(project), project['id']))
            conn.execute('UPDATE ghostlab_builds SET artifact_json=? WHERE artifact_id=?', (json.dumps(project['artifact']), self.app['artifact_id']))
        with self.no_heavy():
            compiled = self.store.compile('attacker',project['id'],project['revision'],project['blueprint'],run.build_ghostlab_artifact)
            self.assertEqual(compiled['artifact']['runtime_revision'],1)
            self.assertNotEqual(compiled['artifact']['artifact_id'],self.app['artifact_id'])
            retry = self.store.compile('attacker',project['id'],project['revision'],project['blueprint'],run.build_ghostlab_artifact)
            self.assertEqual(retry['artifact']['artifact_id'],compiled['artifact']['artifact_id'])
