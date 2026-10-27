import os
from pathlib import Path
from unittest.mock import patch
import unittest
import run
import test_player_hack_read_paths as fixtures


class AdminTests(unittest.TestCase):
    def setUp(self):
        fixtures.PlayerHackReadPathsTest.setUp(self)
        # Keep the actual gate, but read only the isolated test world's state.
        run.GhostNetworkRepository(db_path=self.path)
        self.stack.enter_context(patch.object(run,'ghostsignal_show_db_path',self.path))

    def test_routing_auth_csrf_conflict_and_restore(self):
        route='/api/admin/poi-routing'
        with patch.dict(os.environ,CHAOS_POI_PROVIDER_ADMIN_ENABLED='1',
                        CHAOS_POI_CACHE_PATH=str(Path(self.tmp.name)/'routing.sqlite3')):
            self.assertEqual(self.client.get(route).status_code,403)
            self.generation.authenticate(self.client,'admin')
            self.assertEqual(len(self.client.get(route).json['routes']),12)
            body=dict(action='save',layer='poi',lane='live',revision=0,chain=[])
            self.assertEqual(self.client.post(route,json=body,headers={'X-Chaos-CSRF':'wrong'}).status_code,403)
            with self.client.session_transaction() as session:
                session['session_csrf']='fixture-csrf'
            headers={'Origin':'http://localhost','X-Chaos-CSRF':'fixture-csrf'}
            self.assertEqual(self.client.post(route,json=body,headers=headers).status_code,200)
            self.assertEqual(self.client.post(route,json=body,headers=headers).status_code,409)
            result=self.client.post(route,json=dict(action='restore',layer='poi',lane='live',revision=1),headers=headers)
            self.assertEqual(result.status_code,200,result.json)
            self.assertEqual(len(result.json['history']),2)
            self.assertFalse(result.json['enabled'])
            with patch.dict(os.environ,CHAOS_POI_PROVIDER_ADMIN_ENABLED='0'):
                self.assertEqual(self.client.get(route).status_code,404)

    def test_isolated_world_gate_preserves_epoch_and_admin_checks(self):
        route='/api/admin/poi-providers'
        self.assertEqual(run.ghostsignal_show_db_path,self.path)
        self.assertIsNone(run.get_ghostsignal_show_service().restart_projection())
        with patch.dict(os.environ,CHAOS_POI_PROVIDER_ADMIN_ENABLED='1',
                        CHAOS_POI_CACHE_PATH=str(Path(self.tmp.name)/'poi-admin.sqlite3')):
            with patch.object(run.GhostSignalShowService,'restart_projection',return_value={'epoch':'test-world'}):
                response=self.client.get(route)
                self.assertEqual(response.status_code,423,response.json)
                self.assertEqual(response.json['error'],'ghostsystem_restart_required')
                response=self.client.get(route,headers={'X-Chaos-Ghost-Epoch':'test-world'})
                self.assertEqual(response.status_code,403,response.json)
                self.generation.authenticate(self.client,'admin')
                response=self.client.get(route,headers={'X-Chaos-Ghost-Epoch':'test-world'})
                self.assertEqual(response.status_code,200,response.json)

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

    def test_world_view_and_manual_observation_auth_validation_no_schema_on_get(self):
        from poi_infrastructure.repository import Repository
        from poi_infrastructure.provider_observation import initialize
        import time
        path=Path(self.tmp.name)/'world-view.sqlite3'
        with patch.dict(os.environ,CHAOS_POI_PROVIDER_ADMIN_ENABLED='1',CHAOS_POI_CACHE_PATH=str(path)):
            self.assertEqual(self.client.get('/api/admin/poi-world-view').status_code,403)
            self.generation.authenticate(self.client,'admin')
            self.assertEqual(self.client.get('/api/admin/poi-world-view').status_code,200)
            self.assertFalse(path.exists())
            self.assertEqual(self.client.get('/api/admin/poi-world-view?layer=nope').status_code,400)
            for bbox in ('bad','1,2,3','nan,0,1,2','2,0,1,1'):
                self.assertEqual(self.client.get('/api/admin/poi-world-view',query_string={'bbox':bbox}).status_code,400)
            self.assertEqual(self.client.get('/api/admin/poi-world-view?bbox=20,51,21,52').status_code,200)
            self.assertFalse(path.exists())
            repo=Repository(path);repo.initialize();initialize(repo)
            now=time.time();body=dict(account='maplark',revision=0,credit_limit=30000,used=5,period_start=now-3600,period_end=now+3600,observed_at=now)
            route='/api/admin/poi-provider-observation'
            self.assertEqual(self.client.post(route,json=body,headers={'X-Chaos-CSRF':'wrong'}).status_code,403)
            with self.client.session_transaction() as session:session['session_csrf']='fixture-csrf'
            headers={'Origin':'http://localhost','X-Chaos-CSRF':'fixture-csrf'}
            self.assertEqual(self.client.post(route,json=body,headers=headers).status_code,200)
            self.assertEqual(self.client.post(route,json=body,headers=headers).status_code,409)
            self.assertEqual(self.client.post(route,json=dict(body,revision=1,used=-1),headers=headers).status_code,400)


if __name__=='__main__':unittest.main()
