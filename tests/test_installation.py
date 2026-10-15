import unittest
from unittest.mock import patch
import run
import test_persistent_session_flows as flows


class InstallationTests(unittest.TestCase):
    def setUp(self):
        flows.PersistentFlowTests.setUp(self)
        flags = patch.dict(run.app.config, {key: True for key in (
            'CHAOS_INSTALL_UI_ENABLED', 'CHAOS_LAUNCH_CONTROLLER_ENABLED',
            'CHAOS_PERSISTENT_SESSION_ENABLED')})
        flags.start()
        self.addCleanup(flags.stop)

    def test_manifest_public_stable_and_no_identity(self):
        for client in (self.client, run.app.test_client()):
            response = client.get('/chaos.webmanifest')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'application/manifest+json')
            self.assertEqual(response.json['start_url'], '/launch')
            self.assertEqual(response.json['id'], '/chaos')
            for header in ('Set-Cookie', 'X-Chaos-Session-Generation', 'X-Chaos-Session-User'):
                self.assertNotIn(header, response.headers)
            self.assertNotIn('alice', response.text)

    def test_public_assets_and_shortcut(self):
        for path in ('/chaos-sw.js', '/chaos.desktop', '/static/pwa/offline.html', '/static/pwa/icon-192.png'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertNotIn('Set-Cookie', response.headers)
            self.assertNotIn('X-Chaos-Session-Generation', response.headers)
        text = self.client.get('/chaos.desktop').text
        self.assertIn('Type=Link', text)
        self.assertIn('URL=https://chaos.re/launch', text)
        self.assertNotIn('Exec=', text)

    def test_disabled_dependencies_and_retirement(self):
        for flag in ('CHAOS_INSTALL_UI_ENABLED', 'CHAOS_LAUNCH_CONTROLLER_ENABLED', 'CHAOS_PERSISTENT_SESSION_ENABLED'):
            with patch.dict(run.app.config, {flag: False}):
                self.assertEqual(self.client.get('/chaos.webmanifest').status_code, 404)
                response = self.client.get('/chaos-sw.js')
                self.assertEqual(response.status_code, 200)
                self.assertIn('unregister()', response.text)
                self.assertIn("startsWith('chaos-install-')", response.text)
                self.assertNotIn('location.reload', response.text)

    def test_login_panel_and_launch_manifest(self):
        client = run.app.test_client()
        self.assertIn('data-chaos-install', client.get('/?login=1').text)
        self.assertIn('/chaos.webmanifest', client.get('/launch').text)
