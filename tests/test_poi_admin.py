import os
from pathlib import Path
from unittest.mock import patch
import unittest
import run
import test_player_hack_read_paths as fixtures


class AdminTests(unittest.TestCase):
    setUp=fixtures.PlayerHackReadPathsTest.setUp

    def test_auth_csrf_candidates_and_page(self):
        route='/api/admin/poi-providers'
        path=str(Path(self.tmp.name)/'poi-admin.sqlite3')
        with patch.dict(os.environ,CHAOS_POI_PROVIDER_ADMIN_ENABLED='1',CHAOS_POI_CACHE_PATH=path):
            self.assertEqual(self.client.get(route).status_code,403)
            self.generation.authenticate(self.client,'admin')
            self.assertTrue(self.client.get(route).json['ok'])
            fields=dict(name='Fixture',url='https://example.org/api/interpreter',operator_group='example.org',priority=0)
            body=dict(action='save',id='fixture',revision=0,fields=fields)
            self.assertEqual(self.client.post(route,json=body,headers={'X-Chaos-CSRF':'wrong'}).status_code,403)
            with self.client.session_transaction() as session:
                session['session_csrf']='fixture-csrf'
            headers={'Origin':'http://localhost','X-Chaos-CSRF':'fixture-csrf'}
            result=self.client.post(route,json=body,headers=headers)
            self.assertEqual(result.status_code,200,result.json)
            self.assertFalse(result.json['provider']['enabled'])
            revision=result.json['provider']['revision']
            denied=self.client.post(route,json=dict(action='enable',id='fixture',revision=revision,enabled=True),headers=headers)
            self.assertEqual(denied.status_code,400,denied.json)
            invalid=self.client.post(route,json=dict(body,revision=revision,fields=dict(fields,url='http://127.0.0.1/api/interpreter')),headers=headers)
            self.assertEqual(invalid.status_code,400,invalid.json)
            page=self.client.get('/dev?tab=poi')
            self.assertEqual(page.status_code,200)
            self.assertIn('admin_poi.js',page.text)
            with patch.dict(os.environ,CHAOS_POI_PROVIDER_ADMIN_ENABLED='0'):
                self.assertEqual(self.client.get(route).status_code,404)


if __name__=='__main__':unittest.main()
