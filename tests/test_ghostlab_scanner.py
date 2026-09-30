import os
import unittest
from unittest.mock import patch, Mock
import requests
import run
import ghostlab_scanner as scanner
from database import db_connect, WalletBalanceStore, JsonResourceStore, GameStateDeltaBus
from ghostlab_registry import default_blueprint, validate_fields
from ghostlab_store import GhostLabError
from tests import test_ghostlab_alignment as fixture
from poiFetchClass import POIFetcher


class ScannerTest(unittest.TestCase):
    seed = fixture.GhostLabAlignmentTest.seed
    product = fixture.GhostLabAlignmentTest.product
    no_heavy = fixture.GhostLabAlignmentTest.no_heavy

    def setUp(self):
        fixture.GhostLabAlignmentTest.setUp(self)
        self.seed()
        self.stack.enter_context(patch.dict(os.environ, CHAOS_GHOSTLAB_SCANNER_RUNTIME_ENABLED='true',
                                            CHAOS_GHOSTLAB_RUNTIME_ACTORS='*'))
        self.store, self.project, self.app = self.product('Scanner', 'deep_scanner')
        self.url = '/api/ghostlab/scanner/' + self.app['id'] + '/activate'

    def activate(self, window='window-one'):
        response = self.client.post(self.url, json={'window_id': window, 'extra_retries': 999})
        self.assertEqual(response.status_code, 200, response.json)
        return response.json

    def gen(self):
        with self.client.session_transaction() as session:
            return str(session['session_generation'])

    def test_repeated_scan_text_deduplicates_only_within_one_scan(self):
        payload = dict(type='success', title='Scanner', text='Found 16 objects')
        def send(key=None):
            body = dict(payload, **({'dedupe_key':key} if key else {}))
            response = self.client.post('/add-system-message', json=body)
            self.assertEqual(response.status_code, 200, response.json)
            return response.json.get('duplicate', False)
        with self.no_heavy():
            self.assertFalse(send('scanner:scan-one:success'))
            self.assertTrue(send('scanner:scan-one:success'))
            self.assertFalse(send('scanner:scan-two:success'))
            self.assertFalse(send())
            self.assertTrue(send())

    def test_activation_single_window_release_and_zero_heavy(self):
        with self.no_heavy():
            first = self.activate()
            self.assertEqual(first['token'], self.activate()['token'])
            self.assertEqual(first['presentation']['extra_retries'], 0)
            self.assertEqual(self.client.post(self.url, json={'window_id':'window-two'}).status_code, 409)
            self.assertEqual(self.client.post('/api/ghostlab/scanner/lease', json={'token':first['token']}).status_code, 200)
            self.assertEqual(self.client.post('/api/ghostlab/scanner/lease', json={'token':first['token'],'release':True}).status_code, 200)
            self.assertNotEqual(first['token'], self.activate('window-two')['token'])

    def test_session_actor_expiry_and_installation_revalidated(self):
        token = self.activate()['token']
        gen = self.gen()
        with db_connect(self.path) as conn:
            self.assertIsNotNone(scanner.active(conn, 'attacker', gen, token))
            self.assertIsNone(scanner.active(conn, 'victim', gen, token))
            self.assertIsNone(scanner.active(conn, 'attacker', 'old-generation', token))
        options = scanner.scan_options(self.path, 'attacker', gen, token)
        self.assertTrue(options['still_active']())
        self.inventory.uninstall_app('attacker', app_id=self.app['id'])
        self.assertFalse(options['still_active']())
        self.assertEqual(self.client.post('/api/ghostlab/scanner/lease', json={'token':token}).status_code, 409)
        with self.assertRaises(GhostLabError):
            scanner.scan_options(self.path, 'attacker', gen, token)

    def test_expiry_and_flag_disable(self):
        token = self.activate()['token']
        with db_connect(self.path) as conn:
            conn.execute('UPDATE ghostlab_scanner_leases SET expires=0')
        self.assertEqual(self.client.post('/api/ghostlab/scanner/lease', json={'token':token}).status_code, 409)
        self.activate('window-two')
        with patch.dict(os.environ, CHAOS_GHOSTLAB_SCANNER_RUNTIME_ENABLED='false'):
            self.assertEqual(self.client.post(self.url, json={'window_id':'window-two'}).status_code, 403)

    def test_withdraw_does_not_remove_purchased_overlay(self):
        self.store.withdraw('attacker', self.project['id'], self.project['revision'])
        self.activate()

    def test_map_route_uses_installed_policy_and_rejects_expired_token(self):
        token = self.activate()['token']
        with patch.object(run.player_position_store, 'get_position', return_value={'lat':52,'lng':21}), \
             patch.object(run.Haversine, 'haversine_distance', return_value=1), \
             patch.object(run, 'GHOSTNETWORK_ABILITIES_ENABLED', False), \
             patch.object(run, 'foreign_territory_action_block', return_value=None), \
             patch.object(run.player_marked_target_store, 'list_targets', return_value=[]), \
             patch.object(run.fetcher, 'get_all', side_effect=RuntimeError('test upstream failure')) as fetcher, self.no_heavy():
            payload = dict(action='scan',lat=52,lng=21,deep_scanner_token=token,extra_retries=99,extra_timeout=99)
            response = self.client.post('/map-action', json=payload)
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['scan_outcome'],'api_error')
            options = fetcher.call_args.kwargs['scan_options']
            self.assertEqual((options['extra_retries'],options['extra_timeout']),(0,0))
            self.assertTrue(options['still_active']())
            self.client.post('/api/ghostlab/scanner/lease',json={'token':token,'release':True})
            fetcher.reset_mock()
            self.assertEqual(self.client.post('/map-action',json=payload).status_code,409)
            fetcher.assert_not_called()
            payload.pop('deep_scanner_token')
            self.client.post('/map-action',json=payload)
            self.assertNotIn('scan_options',fetcher.call_args.kwargs)

    def test_purchase_payment_and_free_update_replace_active_artifact(self):
        wallet = WalletBalanceStore(self.path)
        self.stack.enter_context(patch.object(run, 'wallet_balance_store', wallet))
        self.stack.enter_context(patch.object(run, 'resources_store', JsonResourceStore(self.path)))
        self.stack.enter_context(patch.object(run, 'delta_bus', GameStateDeltaBus(self.path)))
        wallet.credit('victim',100000,transaction_key='scanner-fund',source='test')
        self.generation.authenticate(self.client,'victim')
        before = wallet.get_balance('attacker')
        with self.no_heavy():
            response = self.client.post('/install-app',json={'app_id':self.app['id']})
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(response.json['status'],'success')
            self.assertTrue(self.client.post('/install-app',json={'app_id':self.app['id']}).json['duplicate'])
            self.assertEqual(wallet.get_balance('attacker'),before+self.app['price'])
            token = self.activate()['token']
        old = self.app['artifact_id']
        p = self.store.update('attacker',self.project['id'],self.project['revision'],
                              {'blueprint':dict(self.project['blueprint'],menu_name='New',extra_retries=3)})
        p = self.store.compile('attacker',p['id'],p['revision'],p['blueprint'],run.build_ghostlab_artifact)
        p, app = self.store.publish('attacker',p['id'],p['revision'],p['artifact']['artifact_id'],
                                    run.build_ghostlab_googleplex_app,{'level':40,'respect':500})
        with self.no_heavy():
            self.assertEqual(self.activate()['presentation']['menu_name'],'DeepScan')
            balance = wallet.get_balance('victim')
            response = self.client.post('/api/ghostlab/installed/'+app['id'],json={
                'expected_artifact_id':old,'artifact_id':app['artifact_id']})
            self.assertEqual(response.status_code,200,response.json)
            self.assertEqual(wallet.get_balance('victim'),balance)
            self.assertEqual(self.client.post('/api/ghostlab/scanner/lease',json={'token':token}).status_code,409)
            updated = self.activate()['presentation']
            self.assertEqual((updated['menu_name'],updated['extra_retries']),('New',3))

    def test_schema_author_cannot_supply_css_urls_or_unready_effects(self):
        base = default_blueprint('deep_scanner')
        self.assertFalse(validate_fields('deep_scanner', base))
        for key, value in [('pattern_id','pulse'), ('sfx_id','https://example.test/a.wav'),
                           ('frame_color','red;display:none'), ('success_log','500'), ('extra_retries',4),
                           ('extra_timeout',11), ('extra_retries',True), ('menu_name','a'*13), ('menu_name','a\nb')]:
            with self.subTest(key=key, value=value):
                self.assertTrue(validate_fields('deep_scanner', dict(base, **{key:value})))
        for key, value in [('success_log','300'), ('denied_log','403'), ('menu_name','ą'*12),
                           ('extra_retries',3), ('extra_timeout',10), ('success_text','')]:
            self.assertFalse(validate_fields('deep_scanner', dict(base, **{key:value})))


class ScannerUpstreamTest(unittest.TestCase):
    def setUp(self):
        self.fetcher = POIFetcher()
        self.fetcher.request_timeout = 8

    def test_transient_budget_timeout_and_baseline(self):
        for extra, expected in [(0,2),(3,5)]:
            with patch('poiFetchClass.requests.post', side_effect=requests.Timeout) as post:
                with self.assertRaises(Exception):
                    self.fetcher.get_all(1,2,scan_options={'extra_retries':extra,'extra_timeout':10})
                self.assertEqual(post.call_count, expected)
                self.assertTrue(all(c.kwargs['timeout'] == 18 for c in post.call_args_list))

    def test_permanent_denial_never_retries(self):
        with patch('poiFetchClass.requests.post', return_value=Mock(status_code=403)) as post:
            with self.assertRaises(ValueError):
                self.fetcher.get_all(1,2,scan_options={'extra_retries':3})
            self.assertEqual(post.call_count,1)

    def test_empty_success_and_cache_no_extra_attempt(self):
        response = Mock(status_code=200)
        response.json.return_value = {'elements':[]}
        with patch('poiFetchClass.requests.post', return_value=response) as post:
            self.assertEqual(self.fetcher.get_all(1,2,scan_options={'extra_retries':3}), [])
            self.assertEqual(self.fetcher.get_all(1,2), [])
            self.assertEqual(post.call_count,1)

    def test_retry_after_never_shortened_to_fit_budget(self):
        response = Mock(status_code=429, headers={'Retry-After':'120'}, text='slow down')
        with patch('poiFetchClass.requests.post', return_value=response) as post:
            with self.assertRaises(Exception):
                self.fetcher.get_all(1,2,scan_options={'extra_retries':3})
            self.assertEqual(post.call_count,1)

    def test_close_cancels_next_attempt(self):
        live = Mock(side_effect=[True,False])
        with patch('poiFetchClass.requests.post', side_effect=requests.Timeout) as post:
            with self.assertRaises(RuntimeError):
                self.fetcher.get_all(1,2,scan_options={'extra_retries':3,'still_active':live})
            self.assertEqual(post.call_count,1)

    def test_invalid_policy_rejected_before_network(self):
        with patch('poiFetchClass.requests.post') as post:
            for options in ({'extra_retries':4},{'extra_timeout':11},{'extra_retries':True}):
                with self.assertRaises(ValueError):
                    self.fetcher.get_all(1,2,scan_options=options)
            post.assert_not_called()
