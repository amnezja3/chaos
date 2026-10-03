import os
import unittest
from unittest.mock import patch

import run
from creator_store import CreatorStore
from database import (db_connect, JsonResourceStore, PlayerTargetRuntimeStore,
                      PlayerOperationStore, AppActionReceiptStore, GameStateDeltaBus,
                      TerritoryProgressionReceiptStore, TerritoryStore, PlayerMarkedTargetStore, PlayerPositionStore)
from creator_policy import generate_contract, security_effect, SECURITY_KEYS
from tests import test_player_hack_read_paths as read_tests
from tests import test_ghostlab_alignment as alignment_tests


class CreatorRoutesTest(unittest.TestCase):
    setUp = read_tests.PlayerHackReadPathsTest.setUp
    no_heavy = alignment_tests.GhostLabAlignmentTest.no_heavy

    def prepare(self):
        self.users.save_profile(dict(read_tests.valid_profile('attacker'),level=40,respect=500))
        self.inventory.seed_from_profile('attacker', read_tests.valid_profile('attacker'))
        for creator_id in ('termcreator', 'windowmaker', 'buttonmaker', 'appforge'):
            self.inventory.install_app('attacker', {'id': creator_id, 'name': creator_id}, purchase_key=creator_id)
        self.store=CreatorStore(self.path)
        self.stack.enter_context(patch.object(run,'creator_store',self.store))
        self.stack.enter_context(patch.object(run,'resources_store',JsonResourceStore(self.path)))
        self.stack.enter_context(patch.dict(os.environ,CHAOS_CREATORS_V2_ENABLED='true'))
        return dict(name='Creator test',icon='X',action='exploit',interface='terminal',
                    creates_file=False,price=0,request_id='request-zero-heavy')

    def test_create_edit_publish_retry_without_heavy_profile(self):
        data=self.prepare()
        with self.no_heavy():
            policy=self.client.get('/api/creators/policy')
            self.assertEqual(policy.status_code,200,policy.json)
            self.assertEqual(policy.json['power_cap'],100)
            created=self.client.post('/api/creators/projects',json=data)
            self.assertEqual(created.status_code,200,created.json)
            project=created.json['project']
            self.assertEqual(self.client.post('/api/creators/projects',json=data).json['project'],project)
            base='/api/creators/projects/'+project['id']
            published=self.client.post(base+'/publish',json={'revision':1})
            self.assertEqual(published.status_code,200,published.json)
            original=published.json['app']
            for field in ('power','price','effect','action'):
                rejected=self.client.patch(base,json={'revision':1,'presentation':{field:100}})
                self.assertEqual(rejected.status_code,400,rejected.json)
            edited=self.client.patch(base,json={'revision':1,'presentation':{'description':'Correction'}})
            self.assertEqual(edited.status_code,200,edited.json)
            updated=self.client.post(base+'/publish',json={'revision':2})
            self.assertEqual(updated.status_code,200,updated.json)
            self.assertEqual(updated.json['app']['id'],original['id'])
            self.assertEqual(updated.json['app']['creator_contract'],original['creator_contract'])
            self.assertEqual(len(self.store.catalog()),1)
            self.assertIn(original['project_file'],self.client.get('/api/creators/files').json['files'])
            with self.client.session_transaction() as session:
                session['user']='intruder'
            # Store ownership separately, session-generation middleware also guards the HTTP request.
            self.assertEqual(self.store.list('intruder'),[])

    def test_flag_disables_old_payload_and_invalid_new_inputs(self):
        data=self.prepare()
        with self.no_heavy():
            self.assertEqual(self.client.post('/api/apps/generate',json=data).status_code,409)
            self.assertEqual(self.client.post('/api/creators/projects',json=dict(data,power=100)).status_code,400)
            with patch.dict(os.environ,CHAOS_CREATORS_V2_ENABLED='false'):
                self.assertEqual(self.client.post('/api/creators/projects',json=data).status_code,409)

    def test_draft_file_reopen_missing_creator_and_revision_conflict(self):
        data = self.prepare()
        with self.no_heavy():
            project = self.client.post('/api/creators/projects', json=data).json['project']
            base = '/api/creators/projects/' + project['id']
            self.assertIn(project['id'] + '.sh', self.client.get('/api/creators/files').json['files'])
            self.assertEqual(self.client.get(base).json['project'], project)
            update = {'revision': 1, 'presentation': {'description': 'Correction'}}
            self.assertEqual(self.client.patch(base, json=update).status_code, 200)
            self.assertEqual(self.client.patch(base, json=update).status_code, 409)
            self.inventory.uninstall_app('attacker', app_id='termcreator')
            self.assertEqual(self.client.get(base).status_code, 403)
            self.assertEqual(self.client.post('/api/creators/projects', json=data).status_code, 403)
            self.assertEqual(len(self.store.list('attacker')), 1)

    def test_invalid_button_effect_rejected_without_partial_configuration(self):
        data = dict(self.prepare(), interface='button_choices')
        with self.no_heavy():
            project = self.client.post('/api/creators/projects', json=data).json['project']
            base = '/api/creators/projects/' + project['id']
            response = self.client.patch(base + '/configuration', json={'revision': 1,
                'configuration': {'options': [{'effect': 'firewall=false'}, {'effect': 'firewall=bad'}]}})
            self.assertEqual(response.status_code, 400, response.json)
            self.assertIn('Opcja 2', response.json['message'])
            self.assertEqual(self.client.get(base).json['project'], project)
            self.assertEqual(self.store.catalog(), [])

    def test_free_update_preserves_old_edition_retries_and_rejects_confiscation(self):
        import json
        data = self.prepare()
        self.stack.enter_context(patch.object(run, 'delta_bus', GameStateDeltaBus(self.path)))
        with self.no_heavy():
            project = self.client.post('/api/creators/projects', json=data).json['project']
            base = '/api/creators/projects/' + project['id']
            old = self.client.post(base + '/publish', json={'revision': 1}).json['app']
            self.inventory.install_app('attacker', old, purchase_key='original-purchase')
            self.client.patch(base, json={'revision': 1, 'presentation': {'description': 'New description', 'name': 'Renamed'}})
            new = self.client.post(base + '/publish', json={'revision': 2}).json['app']
            def installed():
                with db_connect(self.path) as conn:
                    return json.loads(conn.execute('SELECT app_json FROM player_apps WHERE username=? AND app_id=?', ('attacker', old['id'])).fetchone()[0])
            self.assertEqual(installed()['version'], 1)
            endpoint = '/api/creators/installed/' + old['id']
            self.assertTrue(self.client.get(endpoint).json['update_available'])
            with db_connect(self.path) as conn:
                before = conn.execute('SELECT count(*) FROM wallet_transactions').fetchone()[0]
            self.assertEqual(self.client.post(endpoint, json={'expected_version': 1, 'version': 3}).status_code, 409)
            result = self.client.post(endpoint, json={'expected_version': 1, 'version': 2})
            self.assertEqual(result.status_code, 200, result.json)
            self.assertFalse(result.json['duplicate'])
            self.assertEqual(installed()['version'], 2)
            self.assertEqual(installed()['wallet_transaction_key'], 'original-purchase')
            self.assertEqual(installed()['creator_contract'], old['creator_contract'])
            self.assertTrue(self.client.post(endpoint, json={'expected_version': 1, 'version': 2}).json['duplicate'])
            with db_connect(self.path) as conn:
                self.assertEqual(conn.execute('SELECT count(*) FROM wallet_transactions').fetchone()[0], before)
                self.assertEqual(conn.execute('SELECT count(*) FROM player_tool_files WHERE username=? AND app_id=?', ('attacker', old['id'])).fetchone()[0], 1)
            self.store.withdraw('attacker', new['project_file'])
            self.assertFalse(self.client.get(endpoint).json['update_available'])
            self.assertEqual(installed()['version'], 2)
            self.inventory.uninstall_app('attacker', app_id=old['id'])
            self.assertEqual(self.client.post(endpoint, json={'expected_version': 1, 'version': 2}).status_code, 409)

    def test_maximum_effect_persists_full_security_bar_without_profile(self):
        self.prepare()
        targets=PlayerTargetRuntimeStore(self.path)
        target=dict(target_id='creator-test-target',lat=52.0,lng=21.0,label='Test',
                    source_type='poi',security={key:True for key in SECURITY_KEYS},
                    actions_allowed={'exploit':True})
        targets.upsert_aimed('attacker',target)
        class Maximum:
            def random(self):return 0
        contract=generate_contract(dict(name='Strong',icon='X',action='exploit',
            interface='terminal',creates_file=False),40,Maximum())
        with self.no_heavy():
            current=targets.get_active_target('attacker')
            current['security'].update(security_effect(contract,current['security']))
            targets.upsert_aimed('attacker',current,expected_target=target)
            saved=targets.get_active_target('attacker')
            self.assertTrue(all(saved['security'][key] is False for key in SECURITY_KEYS))
            self.assertTrue(saved['actions_allowed']['exploit'])

    def test_legacy_publication_and_withdrawal_are_profile_free(self):
        self.prepare()
        with patch.dict(os.environ,CHAOS_CREATORS_V2_ENABLED='false'),self.no_heavy():
            response=self.client.post('/api/apps/generate',json={'name':'Legacy new','icon':'X','interface':'terminal'})
            self.assertEqual(response.status_code,200,response.json)
            product=response.json['app']
            withdrawn=self.client.delete('/api/apps/generated/'+product['project_file'])
            self.assertEqual(withdrawn.status_code,200,withdrawn.json)
            self.assertFalse(self.store.catalog()[0]['published'])

    def test_quote_blank_and_zero_and_configuration_freeze(self):
        data=self.prepare()
        with self.no_heavy():
            blank=dict(data,request_id='blank-price',name='Blank')
            blank.pop('price')
            created=self.client.post('/api/creators/projects',json=blank)
            self.assertEqual(created.status_code,200,created.json)
            self.assertGreater(created.json['project']['contract']['price'],0)
            project=self.client.post('/api/creators/projects',json=data).json['project']
            self.assertEqual(project['contract']['price'],0)
            base='/api/creators/projects/'+project['id']
            configured=self.client.patch(base+'/configuration',json={'revision':1,'configuration':{'price':75}})
            self.assertEqual(configured.status_code,200,configured.json)
            self.assertEqual(configured.json['project']['contract']['power'],project['contract']['power'])
            product=self.client.post(base+'/publish',json={'revision':2})
            self.assertEqual(product.status_code,200,product.json)
            self.assertEqual(product.json['app']['price'],75)
            rejected=self.client.patch(base+'/configuration',json={'revision':2,'configuration':{'price':0}})
            self.assertEqual(rejected.status_code,409,rejected.json)

    def test_gonna_win_applies_installed_power_to_real_target(self):
        data=self.prepare()
        data.pop('request_id')
        class Maximum:
            def random(self):return 0
        project=self.store.create('attacker',data,'runtime-request',40,Maximum())
        product=run.build_creator_edition(project,1)
        target=dict(target_id='creator-test-target',lat=52.0,lng=21.0,label='Test',
                    target_mode='standard',source_type='poi',security={key:True for key in SECURITY_KEYS},
                    actions_allowed={'exploit':False,'trace':False,'sniff':False,'scan_ports':False})
        targets=PlayerTargetRuntimeStore(self.path)
        targets.upsert_aimed('attacker',target)
        for key, store in [('player_target_runtime_store',targets),
                           ('player_operation_store',PlayerOperationStore(self.path)),
                           ('app_action_receipt_store',AppActionReceiptStore(self.path)),
                           ('delta_bus',GameStateDeltaBus(self.path))]:
            self.stack.enter_context(patch.object(run,key,store))
        for key, store in [
            ('territory_progression_receipt_store', TerritoryProgressionReceiptStore(self.path)),
            ('territory_store', TerritoryStore(self.path)),
            ('player_marked_target_store', PlayerMarkedTargetStore(self.path)),
            ('player_position_store', PlayerPositionStore(self.path))]:
            self.stack.enter_context(patch.object(run, key, store))
        self.inventory.seed_from_profile('attacker', read_tests.valid_profile('attacker'))
        self.inventory.install_app('attacker', product, purchase_key='creator-runtime')
        run.player_marked_target_store.ensure_seeded('attacker')
        with self.no_heavy():
            rejected=self.client.post('/gonna-win',json={'app_id':product['id'],'choice_id':0})
            self.assertEqual(rejected.status_code,400,rejected.json)
            unchanged=targets.get_active_target('attacker')
            self.assertFalse(unchanged['actions_allowed']['exploit'])
            self.assertTrue(all(unchanged['security'][key] for key in SECURITY_KEYS))
            response=self.client.post('/gonna-win',json={'app_id':product['id'],'target':target})
        self.assertEqual(response.status_code,200,response.json)
        saved=targets.get_active_target('attacker')
        self.assertTrue(all(saved['security'][key] is False for key in SECURITY_KEYS))
        self.assertTrue(saved['actions_allowed']['exploit'])
        self.assertFalse(saved['actions_allowed']['trace'])


if __name__=='__main__':unittest.main()
