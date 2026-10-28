"""Loopback-only admin UI fixture with real routes and isolated account/storage."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]


def main():
    import os
    import tempfile
    from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
    import threading
    from unittest.mock import patch
    with tempfile.TemporaryDirectory(prefix='poi-admin-browser-') as directory:
        os.chdir(directory)
        os.environ.update(CHAOS_SESSION_FILE_DIR=str(Path(directory)/'sessions'),CHAOS_SECRET_KEY='fixture-only',
                          CHAOS_POI_PROVIDER_ADMIN_ENABLED='1',CHAOS_POI_CACHE_PATH=str(Path(directory)/'poi.sqlite3'))
        import run
        from test_player_hack_read_paths import PlayerHackReadPathsTest
        fixture=PlayerHackReadPathsTest()
        fixture.setUp()
        fixture.generation.authenticate(fixture.client,'admin')
        if '--routing' in sys.argv:
            from poi_infrastructure.repository import Repository
            from poi_infrastructure.providers import Registry
            from poi_infrastructure.routing import MAPLARK,GEOAPIFY,Routing
            import time
            registry=Registry(Repository(os.environ['CHAOS_POI_CACHE_PATH']));registry.initialize()
            for name,url,group in [('maplark',MAPLARK,'api.maplark.com'),('geoapify',GEOAPIFY,'api.geoapify.com'),
                                   ('overpass','https://fixture.invalid/api/interpreter','fixture.invalid')]:
                p=registry.save(name,0,dict(name=name,url=url,operator_group=group,priority=0),'fixture')
                if name!='geoapify':
                    p=registry.decision(name,p['revision'],'approved_for_defined_use',['normal_scan','storage'],
                        dict(source_url='https://example.org/terms',reference='fixture',notes='offline only'),time.time()+3600,'fixture')
                    p=registry.tested(name,p['revision'],True,'fixture')
                    registry.enable(name,p['revision'],True,'fixture')
            Routing(registry.repo).initialize()
        if '--world' in sys.argv:
            from poi_infrastructure.repository import Repository
            from poi_infrastructure.world_storage import CanonicalWorldRepository
            from poi_infrastructure.discovery_queue import DemandQueue
            from poi_infrastructure.credit_budget import CreditBudget
            repo=Repository(os.environ['CHAOS_POI_CACHE_PATH'])
            CanonicalWorldRepository(repo).initialize_canonical()
            queue=DemandQueue(repo);queue.initialize()
            from poi_infrastructure.discovery_jobs import DiscoveryJobs
            DiscoveryJobs(repo).initialize()
            for lon,lat in ((21.001,52.001),(21.021,52.011),(21.031,52.031)):
                queue.record(lon,lat)
            ledger=CreditBudget(repo);ledger.initialize();ledger.configure_recurring('maplark',800,24000)
            import time
            day=int(time.time()//86400)*86400
            scope=f'discovery:regular-maplark-{day}'
            ledger.configure_scope('maplark',scope,day,day+86400,200)
            ledger.reserve('maplark','synthetic-background-fixture',20,scopes=(scope,))
            ledger.settle('maplark','synthetic-background-fixture',3)
            ledger.reserve('maplark','synthetic-warning-fixture',760)
            ledger.settle('maplark','synthetic-warning-fixture',760)
            os.environ['CHAOS_POI_DISCOVERY_MODE']='passive'
            from world_dashboard_fixture import seed
            seed(repo)
            from poi_infrastructure import scan_metrics
            scan_metrics.initialize(repo)
            from poi_infrastructure.provider_observation import initialize as init_observations
            init_observations(repo)
            for source in ('world','fresh','upstream'):
                scan_metrics.record(repo,{source},int(source=='upstream'),'success',.5)
        client_lock=threading.Lock()
        class Handler(BaseHTTPRequestHandler):
            def route(self):
                if self.path == '/favicon.ico':
                    self.send_response(204)
                    self.end_headers()
                    return
                path='/dev?tab=poi' if self.path.startswith('/?') or self.path=='/' else self.path
                raw=self.rfile.read(int(self.headers.get('Content-Length',0)))
                headers={}
                if self.command=='POST':
                    headers={'Origin':'http://localhost','X-Chaos-CSRF':self.headers.get('X-Chaos-CSRF','')}
                with client_lock,patch.object(run,'request_ui_locale',return_value='en' if 'fixture_locale=en' in self.path else 'pl'):
                    response=fixture.client.open(path,method=self.command,data=raw or None,content_type='application/json',headers=headers)
                self.send_response(response.status_code)
                for key,value in response.headers:
                    if key.lower() not in ('content-length','connection','transfer-encoding','set-cookie'):
                        self.send_header(key,value)
                self.end_headers()
                try:
                    self.wfile.write(response.data)
                except (BrokenPipeError,ConnectionError):
                    pass  # Browser navigation can cancel a previous refresh.
            do_GET=do_POST=route
        class Server(ThreadingHTTPServer):
            request_queue_size=32
        server=Server(('127.0.0.1',8997),Handler)
        try:
            print('READY http://127.0.0.1:8997',flush=True)
            server.serve_forever()
        finally:
            server.server_close();fixture.doCleanups();os.chdir(ROOT)


if __name__=='__main__':main()
