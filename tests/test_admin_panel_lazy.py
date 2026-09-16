import unittest
from unittest.mock import patch
import test_player_hack_read_paths as fixtures
import run
from admin_panel import page
from database import db_connect


class AdminPanelLazyTest(unittest.TestCase):
    setUp = fixtures.PlayerHackReadPathsTest.setUp
    seed = fixtures.PlayerHackReadPathsTest.seed

    def test_list_and_selected_resources_do_not_read_heavy_profiles(self):
        self.seed(big_attacker=True, big_victim=True)
        with patch.object(run, 'require_dev_admin', return_value=True), \
             patch.object(self.users, 'list_profiles', side_effect=AssertionError('all profiles')), \
             patch.object(self.users, 'get_profile', side_effect=AssertionError('full profile')), \
             patch.object(self.users, 'get_profile_with_revision', side_effect=AssertionError('full revision')):
            response = self.client.get('/api/admin/panel/list?section=users')
            self.assertEqual(response.status_code, 200, response.json)
            self.assertLess(len(response.data), 5000)
            self.assertNotIn('apps', response.json['items'][0])
            selected = self.client.get('/api/admin/panel/user?username=victim')
            self.assertEqual(selected.status_code, 200, selected.json)
            self.assertEqual(selected.json['user']['username'], 'victim')
            self.assertNotIn('raw_profile', selected.json)
            tools = self.client.get('/api/admin/panel/list?section=apps&username=victim')
            self.assertEqual(tools.status_code, 200, tools.json)
            self.assertNotIn('systemLogReader', [a['id'] for a in tools.json['items']])
            for section in ('tools', 'files', 'operations', 'captures', 'territories', 'vulnerabilities'):
                resource = self.client.get(f'/api/admin/panel/list?section={section}&username=victim')
                self.assertEqual(resource.status_code, 200, resource.json)
            legacy = self.client.get('/api/admin/dashboard')
            self.assertEqual(legacy.status_code, 200)
            self.assertLess(len(legacy.data), 5000)

    def test_page_bounds_and_literal_search(self):
        self.seed()
        with db_connect(self.path) as conn:
            for number in range(60):
                conn.execute("INSERT INTO users(username,password,salt,profile_json,created_at,updated_at) VALUES (?, '', '', '{}', '', '')", (f'page-{number:03}',))
        first = page(self.path, 'users', search='page-')
        second = page(self.path, 'users', search='page-', offset=50)
        self.assertEqual(len(first['items']), 50)
        self.assertTrue(first['has_more'])
        self.assertEqual(len(second['items']), 10)
        self.assertFalse(second['has_more'])
        self.assertEqual(page(self.path, 'users', search="' OR 1=1 --")['items'], [])

    def test_routes_require_admin(self):
        self.seed()
        for route in ('/api/admin/panel/list?section=users', '/api/admin/panel/user?username=victim'):
            self.assertEqual(self.client.get(route).status_code, 403)

    def test_shell_has_no_embedded_profiles_or_credentials(self):
        with run.app.test_request_context('/admin'):
            run.session['user'] = 'admin'
            with patch.object(run, 'build_admin_dashboard_state', side_effect=AssertionError('eager state')), \
                 patch.object(run, 'session_generation_client_context', return_value={'generation': 'test'}):
                rendered = run.dev_dashboard()
        self.assertIn('admin_panel.js', rendered)
        self.assertIn('Zgłoszenia błędów', rendered)
        self.assertNotIn('admin / 1234', rendered)
        self.assertNotIn('raw_profile', rendered)
        self.assertNotIn('<pre>', rendered)
