"""Real session lifecycle and document isolation across the new launch transport."""
import json
import re
import unittest
from datetime import timedelta
from unittest.mock import patch

import run
import test_persistent_session_flows as flows


class LaunchTests(unittest.TestCase):
    def setUp(self):
        flows.PersistentFlowTests.setUp(self)
        flags = patch.dict(run.app.config, {'CHAOS_LAUNCH_CONTROLLER_ENABLED': True})
        flags.start()
        self.addCleanup(flags.stop)
        self.launch_headers = {'X-Chaos-Launch': '1', 'Origin': 'http://localhost'}

    def status(self, binding=''):
        return self.client.get('/api/session/status', headers={**self.launch_headers,
            'X-Chaos-Launch-Binding': binding})

    def context(self):
        shell = self.client.get('/launch')
        config = json.loads(re.search(r'id="launch-config"[^>]*>(.*?)</script>', shell.text, re.S)[1])
        state = self.status().get_json()
        return {**self.launch_headers, 'X-Chaos-Launch-CSRF': config['csrf'],
                'X-Chaos-Launch-Binding': state['binding']}

    def login(self, user='victim'):
        with patch.object(run, 'authenticate_user', return_value=True):
            return self.client.post('/', data={'username': user, 'password': 'fixture'})

    def test_public_shell_has_no_identity_and_never_reads_profile(self):
        with patch.object(run.identity_projection_store, 'get_desktop_boot', side_effect=AssertionError('private read')):
            for path in ('/launch', '/desktop', '/map?_embedded=1', '/dev'):
                response = self.client.get(path)
                self.assertEqual(200, response.status_code, response.text)
                self.assertNotIn('alice', response.text)
                self.assertNotIn(self.generation, response.text)
                self.assertNotIn('form', response.text)
                self.assertNotIn('Set-Cookie', response.headers)
                self.assertNotIn(run.SESSION_GENERATION_HEADER, response.headers)
                self.assertIn('no-store', response.headers['Cache-Control'])

    def test_status_is_readonly_and_bootstrap_preserves_ownership(self):
        before = self.store.get_state(self.lineage)
        self.now += timedelta(days=2)
        headers = self.context()
        with patch.object(self.store, 'activate', side_effect=AssertionError('activate forbidden')):
            response = self.client.post('/api/session/bootstrap', headers=headers)
        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(self.generation, response.json['context']['generation'])
        self.assertNotIn('Set-Cookie', response.headers)
        self.assertEqual(before, self.store.get_state(self.lineage))

    def test_status_has_no_identity_or_raw_generation_headers(self):
        response = self.status()
        self.assertTrue(response.json['authenticated'])
        self.assertNotIn(self.generation, response.text)
        self.assertNotIn('alice', response.text)
        self.assertNotIn(run.SESSION_GENERATION_HEADER, response.headers)
        self.assertNotIn(run.SESSION_GENERATION_USER_HEADER, response.headers)

    def test_binding_is_not_a_generation_credential(self):
        binding = self.status().json['binding']
        self.assertNotEqual(run._session_generation_query_token(self.generation), binding)
        response = self.client.get('/api/desktop-shell', headers={run.SESSION_GENERATION_HEADER: binding})
        self.assertEqual(409, response.status_code)

    def test_account_swap_between_status_and_bootstrap_is_rejected(self):
        headers = self.context()
        self.login()
        for response in (self.status(headers['X-Chaos-Launch-Binding']),
                         self.client.post('/api/session/bootstrap', headers=headers)):
            self.assertEqual(409, response.status_code)
            self.assertNotIn('victim', response.text)
            self.assertNotIn(run.SESSION_GENERATION_HEADER, response.headers)
            self.assertNotIn('Set-Cookie', response.headers)

    def test_expiry_between_status_and_bootstrap(self):
        headers = self.context()
        self.now += timedelta(days=30)
        response = self.client.post('/api/session/bootstrap', headers=headers)
        self.assertEqual(401, response.status_code)
        self.assertFalse(self.status().json['authenticated'])
        self.assertNotIn('Set-Cookie', response.headers)

    def test_no_legacy_activation(self):
        with self.client.session_transaction() as current:
            current.clear()
            current['user'] = 'alice'
        with patch.object(self.store, 'activate', side_effect=AssertionError('activate forbidden')):
            self.assertEqual(200, self.client.get('/desktop').status_code)
            self.assertEqual('incomplete_session', self.status().json['reason'])

    def test_missing_user_is_not_recreated(self):
        with patch.object(self.users, 'has_user', return_value=False):
            self.assertEqual('account_missing', self.status().json['reason'])

    def test_network_or_database_failure_is_retry_not_logout(self):
        with patch.object(self.store, 'assert_current', side_effect=RuntimeError('fixture unavailable')):
            response = self.status()
        self.assertEqual(503, response.status_code)
        self.assertNotIn('authenticated', response.json)
        self.assertNotIn('Set-Cookie', response.headers)
        self.assertTrue(self.status().json['authenticated'])

    def test_csrf_origin_and_fetch_metadata(self):
        valid = self.context()
        for bad in ({**valid, 'X-Chaos-Launch-CSRF': 'wrong'},
                    {**valid, 'Origin': 'https://evil.test'},
                    {**valid, 'Sec-Fetch-Site': 'cross-site'},
                    {**valid, 'X-Chaos-Launch': ''}):
            response = self.client.post('/api/session/bootstrap', headers=bad)
            self.assertEqual(403, response.status_code)
        self.assertEqual(403, self.client.get('/api/session/status').status_code)

    def test_protected_desktop_no_redirect_and_same_runtime(self):
        response = self.client.get('/api/desktop-shell', headers=self.headers)
        self.assertEqual(200, response.status_code, response.text)
        self.assertIn('boot-preloader', response.text)
        self.assertIn('session-generation-config', response.text)
        self.assertNotIn('Location', response.headers)
        response = self.client.get('/api/desktop-shell')
        self.assertEqual(409, response.status_code)

    def test_stale_iframe_and_dev_cannot_render_new_account(self):
        self.login()
        for path in ('/map?_embedded=1', '/dev', '/api/desktop-shell'):
            response = self.client.get(path, headers=self.headers)
            self.assertEqual(409, response.status_code)
            self.assertNotIn('boot-preloader', response.text)
        response = self.client.get('/map?_session_generation=' + run._session_generation_query_token(self.generation))
        self.assertEqual(409, response.status_code)

    def test_response_rechecks_ownership(self):
        original = run.session_generation_client_context
        def swap():
            result = original()
            self.store.activate('other', 'other', 'alice', reason='fixture')
            return result
        headers = self.context()
        with patch.object(run, 'session_generation_client_context', side_effect=swap):
            response = self.client.post('/api/session/bootstrap', headers=headers)
        self.assertEqual(409, response.status_code)
        self.assertNotIn(self.generation, response.text)
        self.assertNotIn(run.SESSION_GENERATION_HEADER, response.headers)

    def test_login_entry_and_flag_rollback(self):
        self.assertEqual('/launch', self.client.get('/').headers['Location'])
        self.assertIn('login-form', self.client.get('/?login=1').text)
        response = self.login()
        self.assertEqual(200, response.status_code)
        self.assertIn('launch_authenticated.js', response.text)
        self.assertNotIn('_session_generation', response.text)
        with patch.dict(run.app.config, {'CHAOS_LAUNCH_CONTROLLER_ENABLED': False}):
            self.assertEqual(200, self.client.get('/launch').status_code)
            self.assertTrue(self.status().json['authenticated'])
            self.assertEqual(302, self.login().status_code)

    def test_anonymous_requires_login_without_creating_session(self):
        anonymous = run.app.test_client()
        result = anonymous.get('/api/session/status', headers=self.launch_headers)
        self.assertEqual(200, result.status_code)
        self.assertFalse(result.json['authenticated'])
        self.assertNotIn('Set-Cookie', result.headers)
        self.assertEqual(401, anonymous.get('/api/desktop-shell').status_code)

    def test_public_assets_never_refresh_or_validate_stale_cookie(self):
        self.store.activate('other', 'other', 'alice', reason='fixture')
        with patch.object(self.store, 'assert_current', side_effect=AssertionError('asset checks account')):
            response = self.client.get('/static/images/chaos_favicon.svg')
        self.assertEqual(200, response.status_code)
        self.assertNotIn('Set-Cookie', response.headers)
