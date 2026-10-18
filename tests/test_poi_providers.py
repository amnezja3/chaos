import os
import multiprocessing
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from poi_infrastructure.providers import Registry, endpoint_host
from poi_infrastructure.repository import Repository
from poi_infrastructure.secure_transport import public_addresses
from poi_infrastructure.service import Service, POIError


def observe_registry(path,ready,changed,results):
    registry=Registry(Repository(path))
    ready.put(len(registry.eligible('normal_scan')))
    if changed.wait(10):
        results.put(len(registry.eligible('normal_scan')))


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Repository(Path(self.tmp.name)/'poi.sqlite3')
        self.registry = Registry(self.repo)
        self.registry.initialize()
        self.fields = dict(name='Fixture',url='https://example.org/api/interpreter',operator_group='example.org',priority=0)
        self.value = self.registry.save('fixture',0,self.fields,'admin')

    def approve(self):
        self.value = self.registry.decision('fixture',self.value['revision'],'approved_for_defined_use',
            ['normal_scan','storage','small_probe'],dict(source_url='https://example.org/terms',reference='test evidence',notes='local fixture only'),time.time()+86400,'admin')
        self.value = self.registry.tested('fixture',self.value['revision'],True,'probe')
        self.value = self.registry.enable('fixture',self.value['revision'],True,'admin')

    def test_pending_technical_success_never_enables_gameplay(self):
        self.value = self.registry.tested('fixture',self.value['revision'],True,'probe')
        with self.assertRaisesRegex(POIError,'not_approved'):
            self.registry.enable('fixture',self.value['revision'],True,'admin')
        self.assertEqual(self.registry.eligible('normal_scan'),[])

    def test_scopes_revision_conflicts_and_url_edit_reset(self):
        self.approve()
        self.assertEqual(len(self.registry.eligible('normal_scan')),1)
        self.assertEqual(self.registry.eligible('wide_fetch'),[])
        with self.assertRaisesRegex(POIError,'revision_conflict'):
            self.registry.save('fixture',1,self.fields,'admin')
        changed = self.registry.save('fixture',self.value['revision'],dict(self.fields,url='https://other.example/api/interpreter'),'admin')
        self.assertEqual(changed['technical_status'],'untested')
        self.assertEqual(changed['policy_status'],'unknown')
        self.assertFalse(changed['enabled'])
        self.assertEqual(self.registry.eligible('normal_scan'),[])

    def test_registry_replaces_static_and_shadow_is_readable_after_cache_loss(self):
        self.approve()
        transport = Mock(return_value=(200,None,{'elements':[]}))
        service = Service(self.repo.path,transport=transport)
        flags=dict(CHAOS_POI_PROVIDER_REGISTRY_ENABLED='1',CHAOS_POI_WORLD_INGEST_ENABLED='1',CHAOS_POI_WORLD_REPOSITORY_ENABLED='1')
        with patch.dict(os.environ,flags):
            self.assertEqual(service.fetch('q',['https://must-not-be-used'],1,300,1800),{'elements':[]})
            self.assertEqual(transport.call_args.args[0],self.fields['url'])
            with self.repo.transaction() as c:
                c.execute('DELETE FROM cache')
            self.registry.enable('fixture',self.value['revision'],False,'admin')
            transport.reset_mock()
            self.assertEqual(service.fetch('q',['https://must-not-be-used'],1,300,1800),{'elements':[]})
            transport.assert_not_called()
            with self.assertRaisesRegex(POIError,'configuration_unavailable'):
                service.fetch('unknown',['https://must-not-be-used'],1,300,1800)
            transport.assert_not_called()

    def test_url_and_dns_security(self):
        for url in ['http://example.org/api/interpreter','https://u:p@example.org/api/interpreter',
                    'https://127.0.0.1/api/interpreter','https://[::1]/api/interpreter',
                    'https://example.org:123/api/interpreter','https://example.org/api/interpreter?x=1',
                    'https://example.org/../api/interpreter']:
            with self.assertRaises(POIError): endpoint_host(url)
        for ip in ('127.0.0.1','10.0.0.1','169.254.169.254','::1','fe80::1','::ffff:127.0.0.1'):
            row=(socket.AF_INET6 if ':' in ip else socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443))
            with patch('socket.getaddrinfo',return_value=[row]),self.assertRaisesRegex(POIError,'nonpublic'):
                public_addresses('example.org')

    def test_probe_budget_and_invalid_json_not_healthy(self):
        from poi_infrastructure.admin import probe
        self.approve()
        service=Service(self.repo.path)
        with patch('poi_infrastructure.admin.bounded_http',return_value=(200,None,{'remark':'partial','elements':[]})) as http:
            with self.assertRaisesRegex(POIError,'invalid_response'):
                probe(service,self.registry,'fixture',self.value['revision'],'admin')
            current=self.registry.list()[0]
            self.assertEqual(current['technical_status'],'tested_failed')
            self.assertFalse(current['enabled'])
            with self.assertRaisesRegex(POIError,'rate_limited'):
                probe(service,self.registry,'fixture',current['revision'],'admin')
            self.assertEqual(http.call_count,1)
            self.assertEqual(self.registry.health()[0]['status'],'invalid_response')
            self.assertIsNotNone(self.repo.acquire('@upstream',1))

    def test_disable_seen_by_four_existing_processes(self):
        self.approve()
        ctx=multiprocessing.get_context('spawn')
        ready,results,changed=ctx.Queue(),ctx.Queue(),ctx.Event()
        processes=[ctx.Process(target=observe_registry,args=(self.repo.path,ready,changed,results)) for _ in range(4)]
        try:
            for process in processes:process.start()
            self.assertEqual([ready.get(timeout=10) for _ in processes],[1]*4)
            self.registry.enable('fixture',self.value['revision'],False,'admin')
            changed.set()
            self.assertEqual([results.get(timeout=10) for _ in processes],[0]*4)
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode,0)
        finally:
            for process in processes:
                if process.is_alive():process.terminate()
                process.join();process.close()
            ready.close();ready.join_thread();results.close();results.join_thread()


if __name__=='__main__':unittest.main()
