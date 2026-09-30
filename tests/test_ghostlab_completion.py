import os
import unittest
from unittest.mock import patch

import run
from database import db_connect
from ghostlab_documents import DocumentStore, visible
from ghostlab_registry import TEMPLATES, RUNTIME_FLAGS, default_blueprint
from ghostlab_products import resolve
from ghostlab_store import GhostLabError
from tests import test_ghostlab_travel as travel_tests
from terminals.commands import interpret_command


class GhostLabCompletionTest(unittest.TestCase):
    setUp = travel_tests.GhostLabTravelTest.setUp
    no_heavy = travel_tests.GhostLabTravelTest.no_heavy
    publish = travel_tests.GhostLabTravelTest.publish

    def prepare(self, template='ptk_document', price=None, visibility='global'):
        self.docs = DocumentStore(self.path)
        self.stack.enter_context(patch.object(run, 'document_store', self.docs))
        self.stack.enter_context(patch.dict(os.environ, {value:'true' for value in RUNTIME_FLAGS.values()}))
        blueprint = default_blueprint(template)
        if template == 'ptk_document':
            blueprint.update(content='# Test\n\n<script>alert(1)</script>', visibility=visibility)
            if visibility == 'clan':
                with db_connect(self.path) as conn:
                    conn.execute("UPDATE user_identity_projection SET clan_code='TEST' WHERE username='victim'")
        project = self.store.create('victim', dict(name='Test '+template, template_id=template,
            icon='G', suggested_price=price, blueprint=blueprint), 'test-'+template)
        return self.publish_project(project)

    def publish_project(self, project):
        project = self.store.compile('victim', project['id'], project['revision'], project['blueprint'], run.build_ghostlab_artifact)
        return self.store.publish('victim', project['id'], project['revision'], project['artifact']['artifact_id'],
                                  run.build_ghostlab_googleplex_app, dict(level=40,respect=500,clan_code='TEST'))

    def buy_document(self, offer):
        return self.client.post('/install-app', json=dict(app_id=offer['id'],
            expected_artifact_id=offer['artifact_id'], expected_price=offer['price']))

    def test_document_payment_ownership_version_and_withdrawal(self):
        project, offer = self.prepare()
        before = self.wallet.get_balance('attacker')
        author_before = self.wallet.get_balance('victim')
        with self.no_heavy():
            first = self.buy_document(offer)
            self.assertEqual(first.status_code, 200, first.json)
            self.assertFalse(first.json['duplicate'])
            self.assertTrue(self.buy_document(offer).json['duplicate'])
            self.assertEqual(self.wallet.get_balance('attacker'), before-25)
            self.assertEqual(self.wallet.get_balance('victim'), author_before+25)
            self.assertFalse(self.inventory.has_app('attacker', offer['id']))
            catalog = self.client.get('/api/catalog').json
            item = next(a for a in catalog if a['id']==offer['id'])
            self.assertTrue(item['installed'])
            self.assertNotIn('metadata', item)
            self.assertNotIn('content', str(item))
            original = self.docs.read('attacker', offer['artifact_id'])
            self.assertEqual(self.client.post('/command',json={'input':'open '+offer['artifact_id']+'.ptk'}).json['openGhostLabDocument'],offer['artifact_id'])
            project = self.store.update('victim',project['id'],project['revision'],
                {'blueprint':dict(project['blueprint'],content='# New edition')})
            project, updated = self.publish_project(project)
            self.assertEqual(self.docs.read('attacker',offer['artifact_id']), original)
            with self.assertRaises(GhostLabError): self.docs.read('attacker', updated['artifact_id'])
            self.assertEqual(self.buy_document(updated).status_code, 200)
            self.store.withdraw('victim',project['id'],project['revision'])
            self.assertEqual(self.buy_document(updated).status_code, 409)
            self.assertEqual(self.docs.read('attacker',offer['artifact_id']), original)
            self.assertEqual(len(self.docs.files('attacker')), 2)

    def test_clan_visibility_and_direct_purchase_authorization(self):
        project, offer = self.prepare(visibility='clan', price=0)
        self.assertFalse(visible(offer))
        self.assertFalse(visible(offer,'OTHER'))
        self.assertTrue(visible(offer,'TEST'))
        with self.no_heavy():
            self.assertEqual(self.buy_document(offer).status_code, 404)
            self.assertNotIn(offer['id'], [a['id'] for a in self.client.get('/resources.json').json])
            self.assertNotIn(offer['id'], [a['id'] for a in self.client.get('/api/catalog').json])
            with db_connect(self.path) as conn:
                conn.execute("UPDATE user_identity_projection SET clan_code='TEST' WHERE username='attacker'")
            self.assertIn(offer['id'], [a['id'] for a in self.client.get('/api/catalog').json])
            self.assertEqual(self.buy_document(offer).status_code, 200)
            with db_connect(self.path) as conn:
                conn.execute("UPDATE user_identity_projection SET clan_code='' WHERE username='attacker'")
            self.assertTrue(self.docs.read('attacker', offer['artifact_id']))
        with self.assertRaises(GhostLabError): run.build_ghostlab_googleplex_app(project,'victim',{})

    def test_atomic_document_purchase_rollback(self):
        _, offer = self.prepare()
        before = self.wallet.get_balance('attacker')
        with patch.object(self.messages,'add_message',side_effect=RuntimeError('rollback')):
            with self.assertRaises(RuntimeError): self.docs.purchase('attacker',offer['id'],
                dict(expected_artifact_id=offer['artifact_id'],expected_price=25),vars(run))
        self.assertEqual(self.docs.files('attacker'), [])
        self.assertEqual(self.wallet.get_balance('attacker'), before)

    def test_lab_missing_tool_owner_isolation_and_terminal(self):
        project, offer = self.prepare()
        with self.no_heavy():
            self.assertEqual(self.client.get('/api/ghostlab/file-manager').status_code,200)
            self.assertEqual(self.client.get('/api/ghostlab/projects/'+project['id']+'/open').json['reason'], 'ghostlab_not_installed')
            self.assertEqual(self.client.get('/api/ghostlab/files').json['files'], [])
            self.inventory.install_app('attacker', dict(id='ghost_lab',name='GhostLab'),purchase_key='glab')
            self.assertEqual(self.client.get('/api/ghostlab/projects/'+project['id']+'/open').status_code,404)
            mine = self.store.create('attacker',dict(name='Own',template_id='ptk_document',blueprint=default_blueprint('ptk_document')),'own-project')
            self.assertEqual(self.client.get('/api/ghostlab/projects/'+mine['id']+'/open').json['project']['id'],mine['id'])
            self.assertEqual(self.client.post('/command',json={'input':'open '+mine['id']+'.lab'}).json['openGhostLabFile'],mine['id'])
            self.inventory.uninstall_app('attacker',app_id='ghost_lab')
            self.assertEqual(len(self.client.get('/api/ghostlab/files').json['files']),1)
            self.assertIn('Brak narzędzia',self.client.post('/command',json={'input':'open '+mine['id']+'.lab'}).json['response'])

    def test_all_installed_families_survive_withdrawal(self):
        for template, definition in TEMPLATES.items():
            if definition['launch_mode'] not in ('own_system','player_hack_access'):
                continue
            with self.subTest(template=template):
                project, offer = self.prepare(template)
                self.inventory.install_app('attacker',offer,purchase_key=template)
                self.store.withdraw('victim',project['id'],project['revision'])
                with self.no_heavy(), db_connect(self.path) as conn:
                    installed = resolve(conn,'attacker',offer['id'],[],launch_modes=('own_system','player_hack_access'))
                    self.assertIsNotNone(installed)
                    self.assertEqual(installed['artifact_id'],offer['artifact_id'])
                    self.assertTrue(installed['runtime_enabled'])
                    launch = self.client.post('/command', json={'input':'run '+offer['id']})
                    self.assertEqual(launch.status_code,200,launch.json)
                    self.assertEqual(launch.json['applicationEffect']['artifact_id'],offer['artifact_id'])
                response = self.client.post('/install-app',json={'app_id':offer['id'], 'client_action_key':'withdrawn-'+template,
                    'expected_artifact_id':offer['artifact_id'], 'expected_price':offer['price']})
                self.assertEqual(response.status_code,409,response.json)
                self.assertTrue(self.inventory.has_app('attacker',offer['id']))

    def test_zero_prices_only_without_parent(self):
        for template, definition in TEMPLATES.items():
            project, offer = self.prepare(template, price=0)
            if definition.get('source_tool_id'):
                self.assertGreater(offer['price'],0)
            else:
                self.assertEqual(offer['price'],0,template)
                self.assertTrue(offer['open_source'])
                item = run.googleplex_catalog_payload(offer,{})
                self.assertEqual(item['price'],0)

    def test_terminal_ambiguous_names_require_id(self):
        profile = {'apps':[{'id':'a','name':'Same'},{'id':'b','name':'SAME'}]}
        self.assertIn('Niejednoznaczna',interpret_command('same',profile)['response'])
        self.assertEqual(interpret_command('run b',profile),{'runApp':'b'})
        self.assertTrue(interpret_command('clear', {'apps':[{'id':'c','name':'clear'}]})['clear'])

    def test_price_policy_keeps_history_and_caps_documents(self):
        from ghostlab_pricing import apply_price
        _, offer = self.prepare(price=500)
        self.assertEqual(offer['price'],100)
        _, scanner = self.prepare('deep_scanner',price=0)
        scanner.pop('glab_price_policy')
        scanner['price']=2225
        self.assertFalse(apply_price(scanner))
        self.assertEqual(scanner['price'],2225)

    def test_old_free_intent_requires_explicit_new_build(self):
        project = self.store.create('victim',dict(name='Historical free',template_id='deep_scanner',
            suggested_price=0,blueprint=default_blueprint('deep_scanner')),'old-free-intent')
        def old_builder(*args):
            artifact=run.build_ghostlab_artifact(*args)
            artifact.pop('glab_price_policy')
            return artifact
        project=self.store.compile('victim',project['id'],project['revision'],project['blueprint'],old_builder)
        old=run.build_ghostlab_googleplex_app(project,'victim',{})
        self.assertGreater(old['price'],0)
        upgraded=self.store.compile('victim',project['id'],project['revision'],project['blueprint'],run.build_ghostlab_artifact)
        self.assertEqual(upgraded['artifact']['version'],2)
        self.assertEqual(run.build_ghostlab_googleplex_app(upgraded,'victim',{})['price'],0)

    def test_no_money_and_stale_quote_do_not_create_document(self):
        _, offer = self.prepare()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE wallet_balances SET balance=0 WHERE username='attacker'")
        with self.no_heavy():
            self.assertNotEqual(self.buy_document(offer).status_code,200)
            self.assertEqual(self.docs.files('attacker'),[])
            self.assertEqual(self.buy_document(dict(offer,price=0)).json['reason'],'offer_changed')
