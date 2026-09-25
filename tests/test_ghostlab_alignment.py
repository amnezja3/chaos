import json
import unittest
from unittest.mock import patch
from contextlib import ExitStack

import run
import database
from database import db_connect, ProfileWriteConflict, PlayerHackAccessChanged
from ghostlab_store import GhostLabStore
from ghostlab_products import installed_products
from player_security_store import PlayerSecurityStore
from tests import test_player_hack_read_paths as read_paths
from admin_panel import page


class GhostLabAlignmentTest(unittest.TestCase):
    setUp = read_paths.PlayerHackReadPathsTest.setUp
    seed = read_paths.PlayerHackReadPathsTest.seed
    def product(self, name='Child', template='system_log_reader'):
        store = GhostLabStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghostlab_migrations SET status='complete'")
        project = store.create('attacker', dict(name=name, template_id=template, icon='🐍', description='Own description',
            blueprint=run.default_ghostlab_blueprint(template)), 'create-product-' + name)
        project = store.compile('attacker', project['id'], project['revision'], project['blueprint'], run.build_ghostlab_artifact)
        project, app = store.publish('attacker', project['id'], project['revision'], project['artifact']['artifact_id'],
                                    run.build_ghostlab_googleplex_app, dict(level=40, respect=300))
        self.inventory.install_app('attacker', app, purchase_key=name)
        return store, project, app

    def no_heavy(self):
        stack = ExitStack()
        execute = database.InstrumentedConnection.execute
        def guarded(conn, sql, *args, **kwargs):
            if 'profile_json' in sql.lower() or 'select * from users' in sql.lower():
                raise AssertionError('Heavy SQL: ' + sql)
            return execute(conn, sql, *args, **kwargs)
        stack.enter_context(patch.object(database.InstrumentedConnection, 'execute', guarded))
        for method in ('get_profile', 'get_profile_with_revision', 'save_profile', 'patch_profile_guarded'):
            stack.enter_context(patch.object(self.users, method, side_effect=AssertionError(method)))
        stack.enter_context(patch.object(run, 'sync_session_profile', side_effect=AssertionError('sync')))
        return stack

    def test_child_only_withdraw_usage_and_uninstall(self):
        self.seed()
        self.inventory.uninstall_app('attacker', app_id='systemLogReader')
        store, project, app = self.product()
        with self.no_heavy():
            state = self.client.get('/api/player-hack/access').json
            self.assertEqual([t['id'] for t in state['tools']], [app['id']])
            child = state['tools'][0]
            self.assertEqual((child['name'], child['icon'], child['installed_version']), ('Child', '🐍', 1))
            self.assertFalse(child['enabled'])
            self.assertEqual(self.client.post('/api/player-hack/tool/use', json={'tool_id':app['id'], 'victim_username':'victim'}).json['reason'], 'runtime_pending')
            store.withdraw('attacker', project['id'], project['revision'])
            self.assertEqual(len(self.client.get('/api/player-hack/access').json['tools']), 1)
            self.inventory.install_app('attacker', run.get_pro_system_tool('systemLogReader'), purchase_key='parent')
            access = self.access.get_active_access('attacker', 'victim')
            # Legacy parent receipt must disable child too, with no migration resetting usage.
            self.access.record_tool_usage(access, 'attacker', 'victim', 'systemLogReader', result='opened')
            state = self.client.get('/api/player-hack/access').json
            self.assertEqual(len(state['tools']), 2)
            self.assertTrue(all(t['used'] and not t['enabled'] for t in state['tools']))
            self.inventory.uninstall_app('attacker', app_id=app['id'])
            self.assertEqual(self.client.post('/api/player-hack/tool/use',json={'tool_id':app['id'],'victim_username':'victim'}).status_code,403)
            self.inventory.uninstall_app('attacker', app_id='systemLogReader')
            self.assertEqual(self.client.get('/api/player-hack/access').json['tools'], [])

    def test_forged_product_and_branding_cannot_grant_execution(self):
        self.seed()
        store, project, app = self.product()
        forged = dict(app, id='fake', name='Pretend', source_project_id='fake')
        self.inventory.install_app('attacker', forged, purchase_key='fake')
        with self.no_heavy():
            tools = installed_products(self.path, 'attacker', run.PRO_SYSTEM_TOOLS)
            self.assertNotIn('fake', [t['id'] for t in tools])
            self.assertEqual(self.client.post('/api/player-hack/tool/use',json={'tool_id':'fake','victim_username':'victim'}).status_code,403)

    def test_legacy_builtin_copy_cannot_override_code_contract(self):
        legacy = dict(run.get_pro_system_tool('friendKicker'), bounded_install=False,
                      glab_enabled=False, name='Stale', downloads=7)
        with patch.object(run.resources_store, 'get', return_value=[legacy]), self.no_heavy():
            catalog = run.get_app_catalog()
        products = [item for item in catalog if item['id'] == 'friendKicker']
        self.assertEqual(len(products), 1)
        self.assertTrue(products[0]['bounded_install'])
        self.assertTrue(products[0]['glab_enabled'])
        self.assertEqual(products[0]['downloads'], 7)
        self.assertNotEqual(products[0]['name'], 'Stale')

    def open_security(self):
        self.seed()
        self.security = PlayerSecurityStore(self.path)
        self.security.update('victim', lambda _: {'firewall': True, 'vpn_enabled': False})
        self.inventory.install_app('attacker',run.get_pro_system_tool('securityPanelProxy'),purchase_key='proxy')
        response = self.client.post('/api/player-hack/tool/use',json={'tool_id':'securityPanelProxy','victim_username':'victim'})
        self.assertEqual(response.status_code,200,response.json)
        return {'victim_username':'victim','tool_id':'securityPanelProxy',
                'security_version':response.json['security_version'],'security_context':response.json['security_context']}

    def test_security_zero_heavy_cas_and_profile_cannot_restore(self):
        payload = self.open_security()
        stale = self.users.get_profile_with_revision('victim')
        with self.no_heavy():
            response = self.client.post('/api/player-hack/security/update',json=dict(payload,key='firewall',value=False))
            self.assertEqual(response.status_code,200,response.json)
            self.assertFalse(response.json['security']['firewall'])
            self.assertEqual(self.client.post('/api/player-hack/security/update',json=dict(payload,key='firewall',value=True)).status_code,409)
            refreshed=self.client.get('/api/player-hack/security?victim_username=victim')
            self.assertEqual(refreshed.status_code,200,refreshed.json)
            self.assertEqual(refreshed.json['security_version'],response.json['security_version'])
            payload['security_version'] = response.json['security_version']
            response = self.client.post('/api/player-hack/security/preset',json=dict(payload,preset='all'))
            self.assertEqual(response.status_code,200,response.json)
            self.security.update('victim',lambda s: dict(s,firewall=False))
        self.users.save_profile_guarded(stale['profile'], source='test.legacy', expected_revision=stale['profile_revision'])
        self.assertFalse(self.identity.get_player_security('victim')['firewall'])
        self.assertFalse(self.users.get_profile('victim')['security']['firewall'])

    def test_security_second_writer_uninstall_and_revocation(self):
        payload = self.open_security()
        self.security.update('victim',lambda s:dict(s,firewall=False))
        with self.no_heavy():
            self.assertEqual(self.client.post('/api/player-hack/security/preset',json=dict(payload,preset='all')).status_code,409)
            payload['security_version']=self.security.get('victim')['security_version']
            original = self.security.get('victim')
            access = self.access.get_active_access('attacker','victim')
            def revoked(s):
                return dict(s,firewall=True)
            calls=[]
            real_guard=run.player_hack_write_guard('attacker','victim','securityPanelProxy',access)
            def guard(*,conn):
                calls.append(1)
                if len(calls)==2:
                    conn.execute("UPDATE player_apps SET status='uninstalled' WHERE username='attacker' AND app_id='securityPanelProxy'")
                real_guard(conn=conn)
            with self.assertRaises(PlayerHackAccessChanged):
                self.security.update('victim',revoked,guard=guard)
            self.assertEqual(self.security.get('victim'),original)
            self.inventory.uninstall_app('attacker',app_id='securityPanelProxy')
            self.assertEqual(self.client.post('/api/player-hack/security/update',json=dict(payload,key='firewall',value=True)).status_code,403)

    def test_admin_history_filters_and_authorization(self):
        self.seed()
        store,p,app=self.product()
        self.product('Second','friend_kicker')
        with self.no_heavy():
            result=page(self.path,'ghostlab',template_id='system_log_reader')
            self.assertEqual(len(result['items']),1)
            item=result['items'][0]
            self.assertEqual((item['author'],item['name'],item['created_at']),('attacker','Child',p['created_at']))
            store.withdraw('attacker',p['id'],p['revision'])
            self.assertEqual(page(self.path,'ghostlab',search='Child')['items'][0]['status'],'withdrawn')
            self.assertEqual(self.client.get('/api/admin/panel/list?section=ghostlab').status_code,403)
            with patch.object(run,'require_dev_admin',return_value=True):
                admin=self.client.get('/api/admin/panel/list?section=ghostlab&template_id=friend_kicker')
                self.assertEqual(admin.status_code,200,admin.json)
                self.assertEqual(len(admin.json['templates']),6)
                self.assertEqual(len(admin.json['non_glab']),5)
                self.assertEqual([item['name'] for item in admin.json['items']],['Second'])

    def test_security_migration_idempotent_missing_fails_closed(self):
        self.seed()
        store=PlayerSecurityStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute("DELETE FROM player_security WHERE username='victim'")
        with self.assertRaises(database.ProfileRecoveryRequired): store.get('victim')
        before=store.migrate()
        self.assertEqual(before,[{'username':'victim','status':'would_migrate'}])
        self.assertEqual(store.migrate(apply=True)[0]['status'],'migrated')
        self.assertEqual(store.migrate(apply=True),[])

    def test_purchase_child_payment_install_retry_no_heavy(self):
        self.seed()
        store,p,app=self.product()
        record=self.users.get_profile_with_revision('victim')
        profile=dict(record['profile'],level=40,respect=300)
        self.users.save_profile_guarded(profile,source='test.level',expected_revision=record['profile_revision'])
        wallet=database.WalletBalanceStore(self.path)
        wallet.credit('victim',10000,transaction_key='test-fund',source='test')
        self.stack.enter_context(patch.object(run,'wallet_balance_store',wallet))
        self.stack.enter_context(patch.object(run,'resources_store',database.JsonResourceStore(self.path)))
        self.stack.enter_context(patch.object(run,'delta_bus',database.GameStateDeltaBus(self.path)))
        self.generation.authenticate(self.client,'victim')
        before=wallet.get_balance('attacker')
        with self.no_heavy():
            response=self.client.post('/install-app',json={'app_id':app['id']})
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['status'],'success',response.json)
            self.assertEqual(wallet.get_balance('attacker'),before+app['price'])
            replay=self.client.post('/install-app',json={'app_id':app['id']})
            self.assertTrue(replay.json['duplicate'],replay.json)
            self.assertEqual(wallet.get_balance('attacker'),before+app['price'])
            self.assertEqual(self.inventory.catalog_download_counts([app['id']])[app['id']],1)
            self.assertEqual(self.inventory.desktop_apps('victim')[0]['artifact_id'],app['artifact_id'])

    def test_own_security_rules_and_detention(self):
        payload=self.open_security()
        key, conflicts=next((k,v) for k,v in run.SECURITY_CONFLICTS.items() if v)
        state=self.security.update('attacker',lambda _: dict.fromkeys([key,*conflicts],True))
        with self.no_heavy():
            own=self.client.post('/api/profile/security',json={'key':key,'value':True,'security_version':state['security_version']})
            self.assertEqual(own.status_code,200,own.json)
            self.assertTrue(own.json['security'][key])
            self.assertTrue(all(own.json['security'][other] is False for other in conflicts))
        from datetime import datetime,timezone
        from response_network.sanctions import SanctionStore
        from response_network.consequence_table import plan_consequence
        sanctions=SanctionStore(self.path)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            sanctions.impose(conn,encounter_id='test-detention',actor_id='attacker',incident_id='test',
                            plan=plan_consequence(5,0),now=datetime.now(timezone.utc))
        before=self.security.get('victim')
        with self.no_heavy():
            response=self.client.post('/api/player-hack/security/update',json=dict(payload,key='firewall',value=False))
            self.assertIn(response.status_code,(403,409),response.json)
            self.assertEqual(self.security.get('victim'),before)

    def test_legacy_download_baseline_and_registry_audit(self):
        self.seed()
        store,p,app=self.product()
        from tools.audit_glab_catalog import audit
        resource=database.JsonResourceStore(self.path)
        catalog=resource.get('app_config')
        catalog[0]['downloads']=7
        resource.set('app_config',catalog)
        with self.no_heavy():
            self.assertEqual(page(self.path,'ghostlab')['items'][0]['downloads'],7)
            with db_connect(self.path) as conn:
                report=audit(conn,run.PRO_SYSTEM_TOOLS)
            self.assertEqual(report['anomalies'],[])
            self.assertEqual(report['download_baseline_updates'],[])
