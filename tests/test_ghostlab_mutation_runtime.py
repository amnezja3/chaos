import json
import os
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

import run
import database
from database import db_connect
from ghostlab_registry import RUNTIME_FLAGS, default_blueprint
from tests import test_ghostlab_alignment as fixture
from tests import test_first_respawn_territory_edge as geometry
from tests.test_player_hack_read_paths import valid_profile


class GhostLabMutationRuntimeTest(unittest.TestCase):
    seed = fixture.GhostLabAlignmentTest.seed
    product = fixture.GhostLabAlignmentTest.product
    no_heavy = fixture.GhostLabAlignmentTest.no_heavy

    def setUp(self):
        fixture.GhostLabAlignmentTest.setUp(self)
        self.seed()
        self.stack.enter_context(patch.dict(os.environ, {**{v: 'true' for v in RUNTIME_FLAGS.values()},
                                                      'CHAOS_GHOSTLAB_RUNTIME_ACTORS': 'attacker'}))
        self.wallet = database.WalletBalanceStore(self.path)
        self.mail = database.MailStore(self.path)
        self.deltas = database.GameStateDeltaBus(self.path)
        self.positions = database.PlayerPositionStore(self.path)
        self.territories = database.TerritoryStore(self.path)
        for name, store in [('wallet_balance_store', self.wallet), ('mail_store', self.mail),
                            ('delta_bus', self.deltas), ('player_position_store', self.positions),
                            ('territory_store', self.territories)]:
            self.stack.enter_context(patch.object(run, name, store))

    def use(self, app, **extra):
        return self.client.post('/api/player-hack/tool/use', json={
            'tool_id': app['id'], 'artifact_id': app.get('artifact_id'), 'victim_username': 'victim', **extra})

    def make(self, template, **fields):
        store, project, app = self.product(name='Child ' + template, template=template)
        if fields:
            project = store.update('attacker', project['id'], project['revision'],
                {'blueprint': dict(project['blueprint'], **fields)})
            project = store.compile('attacker', project['id'], project['revision'], project['blueprint'], run.build_ghostlab_artifact)
            project, app = store.publish('attacker', project['id'], project['revision'],
                project['artifact']['artifact_id'], run.build_ghostlab_googleplex_app, {'level': 40, 'respect': 500})
            self.inventory.uninstall_app('attacker', app_id=app['id'])
            self.inventory.install_app('attacker', app, purchase_key='updated-' + template)
        return app

    def contacts(self):
        self.users.save_profile(valid_profile('contact'))
        self.mail.add_contact('victim', 'contact')
        self.mail.add_contact('contact', 'victim')

    def test_finance_atomic_transfer_policy_receipt_and_family_limit(self):
        app = self.make('financial_sniffer', steal_percent=1, detection_percent=95, reward_note='Own note')
        before = [self.wallet.get_balance(u) for u in ('attacker', 'victim')]
        with self.no_heavy(), patch.object(run, 'randint', return_value=10), patch.object(run, 'random', return_value=0):
            response = self.use(app)
            self.assertEqual(response.status_code, 200, response.json)
            amount = response.json['stolen_amount']
            self.assertEqual(amount, min(10, before[1]//100))
            self.assertEqual(response.json['reward_note'], 'Own note')
            self.assertEqual(self.use(app).status_code, 409)
            self.inventory.install_app('attacker', run.get_pro_system_tool('financialSniffer'), purchase_key='parent')
            self.assertEqual(self.use({'id':'financialSniffer'}).status_code, 409)
        self.assertEqual([self.wallet.get_balance(u) for u in ('attacker', 'victim')], [before[0]+amount, before[1]-amount])
        with db_connect(self.path) as conn:
            receipt = conn.execute("SELECT result FROM player_hack_tool_usage WHERE tool_id='financialSniffer'").fetchone()[0]
        self.assertEqual(json.loads(receipt[9:])['execution']['artifact'], app['artifact_id'])

    def test_finance_failure_rolls_back_wallet_receipt_and_delta(self):
        app = self.make('financial_sniffer', detection_percent=95)
        before = self.wallet.get_balance('attacker')
        with self.no_heavy(), patch.object(run, 'random', return_value=0), patch.object(self.messages, 'add_message', side_effect=RuntimeError('fail')):
            self.assertEqual(self.use(app).status_code, 500)
        self.assertEqual(self.wallet.get_balance('attacker'), before)
        self.assertIsNone(self.access.get_tool_usage(self.access.get_active_access('attacker','victim'), 'attacker','victim','financialSniffer'))
        with self.no_heavy(): self.assertEqual(self.use(app).status_code, 200)

    def test_finance_cooldown_survives_new_access_and_parent_switch(self):
        app = self.make('financial_sniffer', cooldown_minutes=1440)
        self.assertEqual(self.use(app).status_code, 200)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE player_hack_access SET hacked_until='2000-01-01',cooldown_until='2000-01-01'")
        self.access.grant_access('attacker', 'victim', access_minutes=6)
        self.assertEqual(self.use(app).json['reason'], 'family_cooldown')
        self.inventory.install_app('attacker', run.get_pro_system_tool('financialSniffer'), purchase_key='parent')
        self.assertEqual(self.use({'id':'financialSniffer'}).json['reason'], 'family_cooldown')

    def test_friend_policy_messages_reverse_link_and_rollback(self):
        self.contacts()
        app = self.make('friend_kicker', success_percent=85, victim_message='Victim custom', contact_message='Contact custom')
        with self.no_heavy(), patch.object(run, 'randint', return_value=1):
            with patch.object(self.messages, 'add_message', side_effect=RuntimeError('fail')):
                self.assertEqual(self.use(app).status_code, 500)
            self.assertTrue(self.mail.is_contact('victim','contact'))
            response = self.use(app)
            self.assertEqual(response.status_code, 200, response.json)
            self.assertTrue(response.json['removed'])
            self.assertEqual(self.use(app).status_code, 409)
        self.assertFalse(self.mail.is_contact('contact','victim'))
        self.assertEqual(self.messages.consume_pending('contact')[0]['text'], 'Contact custom')

    def test_friend_empty_and_failed_roll_are_real_results(self):
        app = self.make('friend_kicker', success_percent=1, detection_percent=0)
        with self.no_heavy():
            response = self.use(app)
            self.assertEqual(response.status_code, 200, response.json)
            self.assertFalse(response.json['removed'])
            self.assertEqual(response.json['chance'], 0)

    def test_proxy_cas_reopen_artifact_pin_and_uninstall(self):
        app = self.make('security_panel_proxy')
        run.player_security_store().update('victim', lambda _: {'firewall': True, 'vpn_enabled': False})
        with self.no_heavy():
            opened = self.use(app)
            self.assertEqual(opened.status_code, 200, opened.json)
            state = opened.json
            key = next(k for k,v in state['security'].items() if type(v) is bool)
            payload = dict(tool_id=app['id'], artifact_id=app['artifact_id'], victim_username='victim',
                security_version=state['security_version'], security_context=state['security_context'], key=key, value=not state['security'][key])
            response = self.client.post('/api/player-hack/security/update', json=payload)
            self.assertEqual(response.status_code, 200, response.json)
            self.assertEqual(self.client.post('/api/player-hack/security/update',json=payload).status_code, 409)
            url = '/api/player-hack/security?victim_username=victim&tool_id=' + app['id']
            fresh = self.client.get(url)
            self.assertEqual(fresh.status_code, 200, fresh.json)
            payload.update(security_version=fresh.json['security_version'], value=state['security'][key])
            self.assertEqual(self.client.post('/api/player-hack/security/update',json=payload).status_code, 200)
            self.assertEqual(self.client.post('/api/player-hack/security/update',json=dict(payload,artifact_id='forged')).status_code, 409)
            self.inventory.uninstall_app('attacker', app_id=app['id'])
            self.assertEqual(self.client.get(url).status_code, 403)

    def test_cleaner_shared_executor_inventory_storage_and_failure(self):
        app = self.make('arsenal_cleaner', success_percent=80)
        self.inventory.install_app('victim', {'id':'removable', 'name':'Removable','file_size':12,'disk_usage':12},purchase_key='candidate')
        with self.no_heavy(), patch.object(run,'randint',return_value=1), patch.object(
                self.inventory, 'snapshot', side_effect=AssertionError('Unbounded inventory snapshot')):
            with patch.object(self.messages,'add_message',side_effect=RuntimeError('fail')):
                self.assertEqual(self.use(app).status_code, 500)
            self.assertTrue(self.inventory.has_app('victim','removable'))
            response = self.use(app)
            self.assertEqual(response.status_code,200,response.json)
            self.assertTrue(response.json['removed'])
            self.assertFalse(self.inventory.has_app('victim','removable'))
            self.assertEqual(self.use(app).status_code,409)

    def test_intruder_uses_child_without_parent_and_moves_once(self):
        app = self.make('intruder_kicker',success_message='Moved custom')
        self.positions.upsert('victim', {'lat':52.2,'lng':21.0})
        area = geometry.FirstRespawnTerritoryEdgeTest.area(1,'attacker')
        self.territories.replace_player_areas('attacker',[area])
        with self.no_heavy():
            result = self.use(app)
            self.assertEqual(result.status_code,200,result.json)
            self.assertEqual(result.json['message'],'Moved custom')
            self.assertEqual(result.json['tool']['id'], app['id'])
            position = self.positions.get('victim')
            self.assertEqual(self.use(app).status_code,409)
            self.assertEqual(position,self.positions.get('victim'))

    def test_all_family_flags_artifact_forgery_and_no_access(self):
        for family in ('financial_sniffer','friend_kicker','security_panel_proxy','arsenal_cleaner','intruder_kicker'):
            app = self.make(family)
            with self.no_heavy():
                self.assertEqual(self.use(app,artifact_id='forged').status_code,409)
                with patch.dict(os.environ,{RUNTIME_FLAGS[family]:'false'}):
                    self.assertEqual(self.use(app).json['reason'],'runtime_pending')
                self.assertEqual(self.use(app,victim_username='nobody').status_code,403)

    def test_family_concurrency_runs_one_effect(self):
        from ghostlab_runtime import commit_mutation
        app = self.make('friend_kicker')
        product = run.resolve_player_hack_product('attacker', app['id'])
        access = self.access.get_active_access('attacker','victim')
        guard = run.player_hack_write_guard('attacker','victim',app['id'],access)
        calls = []
        def effect(conn):
            calls.append(1)
            return {'success':True,'removed':False,'roll':42}
        def perform(_):
            return commit_mutation('attacker','victim',product,access,self.access,guard,run.PRO_SYSTEM_TOOLS,effect)
        with self.no_heavy(), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(perform,range(2)))
        self.assertEqual(len(calls),1)
        self.assertEqual(sum(bool(r.get('duplicate')) for r in results),1)

    def test_three_accounts_purchase_all_families_and_execute(self):
        self.stack.enter_context(patch.object(run, 'resources_store', database.JsonResourceStore(self.path)))
        self.stack.enter_context(patch.dict(os.environ, CHAOS_GHOSTLAB_RUNTIME_ACTORS='attacker,victim'))
        self.users.patch_profile_guarded('victim', {'level':40,'respect':500}, source='test')
        self.users.save_profile(valid_profile('target'))
        self.inventory.seed_from_profile('target', valid_profile('target'))
        self.inventory.install_app('target', {'id':'removable','name':'Removable'},purchase_key='candidate')
        self.mail.add_contact('target','attacker')
        self.mail.add_contact('attacker','target')
        self.positions.upsert('target', {'lat':52.2,'lng':21.0})
        self.territories.replace_player_areas('victim',[geometry.FirstRespawnTerritoryEdgeTest.area(1,'victim')])
        self.wallet.credit('victim', 100000,transaction_key='fund',source='test')
        self.access.grant_access('victim','target')
        self.generation.authenticate(self.client,'victim')
        for family in ('security_panel_proxy','financial_sniffer','friend_kicker','arsenal_cleaner','intruder_kicker'):
            app = self.make(family)
            before = self.wallet.get_balance('attacker')
            with self.no_heavy(), patch.object(run,'randint',return_value=1):
                response = self.client.post('/install-app',json={'app_id':app['id']})
                self.assertEqual(response.status_code,200,response.json)
                self.assertTrue(self.client.post('/install-app',json={'app_id':app['id']}).json['duplicate'])
                self.assertEqual(self.wallet.get_balance('attacker'),before+app['price'])
                result = self.use(app,victim_username='target')
                self.assertEqual(result.status_code,200,result.json)
                self.assertEqual(result.json['tool']['id'],app['id'])
                self.assertEqual(self.inventory.catalog_download_counts([app['id']])[app['id']],1)

    def test_arrest_blocks_every_child_without_consuming_receipts(self):
        from datetime import datetime, timezone
        from response_network.sanctions import SanctionStore
        from response_network.consequence_table import plan_consequence
        apps = [self.make(f) for f in RUNTIME_FLAGS]
        sanctions = SanctionStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sanctions.impose(conn,encounter_id='arrest',actor_id='attacker',incident_id='i',
                plan=plan_consequence(5,0),now=datetime.now(timezone.utc))
        for app in apps:
            with self.no_heavy():
                response = self.use(app)
            self.assertEqual(response.status_code,403)
            self.assertEqual(response.json['reason'],'detention_action_blocked')
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM player_hack_tool_usage').fetchone()[0],0)

    def test_cleaner_cannot_remove_core_and_locked_policy_is_enforced(self):
        from ghostlab_registry import validate_fields
        self.assertTrue(validate_fields('arsenal_cleaner',dict(default_blueprint('arsenal_cleaner'),remove_tools_file=False)))
        app = self.make('arsenal_cleaner')
        self.inventory.install_app('victim', {'id':'core','name':'Core','category':'core'},purchase_key='core')
        with self.no_heavy():
            response=self.use(app)
        self.assertEqual(response.status_code,200,response.json)
        self.assertFalse(response.json['removed'])
        self.assertTrue(self.inventory.has_app('victim','core'))

    def test_failed_friend_roll_and_legacy_build_stays_disabled(self):
        self.contacts()
        app=self.make('friend_kicker',success_percent=1,detection_percent=0)
        with self.no_heavy(),patch.object(run,'randint',return_value=100),patch.object(run,'random',return_value=.99):
            result=self.use(app)
        self.assertEqual(result.status_code,200,result.json)
        self.assertFalse(result.json['removed'])
        self.assertFalse(result.json['detected'])
        self.assertTrue(self.mail.is_contact('victim','contact'))
        from ghostlab_products import runtime_artifact_ready
        with db_connect(self.path) as conn:
            artifact=json.loads(conn.execute('SELECT artifact_json FROM ghostlab_builds WHERE artifact_id=?',(app['artifact_id'],)).fetchone()[0])
        artifact.pop('runtime_revision')
        self.assertFalse(runtime_artifact_ready(artifact))

    def test_precommit_revocation_rolls_back_child_effect(self):
        from ghostlab_runtime import commit_mutation
        app=self.make('friend_kicker')
        self.contacts()
        access=self.access.get_active_access('attacker','victim')
        product=run.resolve_player_hack_product('attacker',app['id'])
        def effect(conn):
            self.mail.remove_contact('victim','contact',conn=conn)
            conn.execute("UPDATE player_hack_access SET hacked_until='2000-01-01'")
            return {'success':True,'removed':True}
        with self.no_heavy(),self.assertRaises(database.PlayerHackAccessChanged):
            commit_mutation('attacker','victim',product,access,self.access,
                run.player_hack_write_guard('attacker','victim',app['id'],access),run.PRO_SYSTEM_TOOLS,effect)
        self.assertTrue(self.mail.is_contact('victim','contact'))
