import os
import unittest
from unittest.mock import patch

import run
import test_player_hack_read_paths as fixtures
from ghostnetwork.llm.router import NarrativeRouter
from ghostnetwork.llm.provider_store import ProviderStore


class NarrativeProviderAdminTest(unittest.TestCase):
    setUp=fixtures.PlayerHackReadPathsTest.setUp

    def admin(self):
        self.generation.authenticate(self.client,'admin')

    def test_authorization_and_read_only_secret_status(self):
        route='/api/admin/narrative-providers'
        self.assertEqual(self.client.get(route).status_code,403)
        self.admin()
        with patch.dict(os.environ,{'CHAOS_MISTRAL_API_KEY':'must-never-leak'}):
            result=self.client.get(route)
        self.assertEqual(result.status_code,200,result.json)
        self.assertTrue(result.json['secret_configured'])
        self.assertNotIn('must-never-leak',result.text)
        self.assertEqual(result.json['config']['primary'],'ollama')

    def test_save_conflict_origin_and_secret_injection(self):
        self.admin()
        route='/api/admin/narrative-providers'
        config=self.client.get(route).json['config']
        result=self.client.post(route,json={'action':'save','config':config})
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(self.client.post(route,json={'action':'save','config':config}).status_code,409)
        self.assertEqual(self.client.post(route,json={'action':'save','config':config},headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(self.client.post(route,json={'action':'save','config':{**config,'api_key':'not-accepted'}}).status_code,400)

    def test_mistral_model_validation_and_health_diagnostic(self):
        self.admin()
        route='/api/admin/narrative-providers'
        config=self.client.get(route).json['config']
        with patch.dict(os.environ,{'CHAOS_MISTRAL_API_KEY':'test-only'}),patch.object(NarrativeRouter,'models',return_value=['available']):
            self.assertEqual(self.client.post(route,json={'action':'save','config':{**config,'primary':'mistral','model':'missing'}}).status_code,400)
            result=self.client.post(route,json={'action':'save','config':{**config,'primary':'mistral','model':'available'}})
            self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(ProviderStore(self.path).config()['primary'],'mistral')

    def test_page_is_lazy_and_contains_no_credentials(self):
        with run.app.test_request_context('/dev?tab=narrative'):
            run.session['user']='admin'
            with patch.object(run,'session_generation_client_context',return_value={'query_token':'test'}),patch.object(run,'request_ui_locale',return_value='en'):
                page=run.dev_dashboard()
        self.assertIn('admin_narrative.js',page)
        self.assertIn('data-locale="en"',page)
        self.assertNotIn('type="password"',page)
