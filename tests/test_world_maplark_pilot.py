import copy
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from poiFetchClass import POIFetcher
from poi_infrastructure.credit_budget import CreditBudget
from poi_infrastructure.maplark_pilot import pilot_user
from poi_infrastructure.maplark_profile import ENDPOINT, export_maplark
from poi_infrastructure.providers import Registry
from poi_infrastructure.service import Service, Config, POIError
from poi_infrastructure.world_contract import FILTERS, ContractError, Provenance
from poi_infrastructure.world_adapters import MAPLARK_VERSION, normalize_maplark


def normalized(features):
    return normalize_maplark({'type': 'FeatureCollection', 'features': features},
        {'X-Returned': str(len(features)), 'X-Has-More': 'false'},
        Provenance('maplark', MAPLARK_VERSION, 'test', 1))


def point(identity=1):
    return dict(type='Feature', id=f'node/{identity}',
        geometry=dict(type='Point', coordinates=[21+identity*.00001,52]),
        properties=dict(tags={'amenity':'bank','atm':'yes','internet_access':'wlan'}))


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.service=Service(path=Path(self.tmp.name)/'poi.db', config=Config(join_wait=0))
        self.registry=Registry(self.service.repo); self.registry.initialize()
        ledger=CreditBudget(self.service.repo); ledger.initialize()
        ledger.configure_window('maplark','pilot',time.time()-1,time.time()+3600,100)
        v=self.registry.save('maplark',0,dict(name='MapLark',url=ENDPOINT,
            operator_group='api.maplark.com',priority=0),'test')
        v=self.registry.decision(v['id'],v['revision'],'approved_for_defined_use',
            ['normal_scan','storage'],dict(source_url='https://maplark.com/terms-of-service',
            reference='isolated fixture',notes='test only'),time.time()+3600,'test')
        v=self.registry.tested(v['id'],v['revision'],True,'test')
        self.registry.enable(v['id'],v['revision'],True,'test')
        env=patch.dict(os.environ,CHAOS_POI_MAPLARK_PILOT_ENABLED='1',
            CHAOS_POI_MAPLARK_PILOT_USERS='tester',CHAOS_MAPLARK_CREDIT_RESERVATION='20',
            CHAOS_MAPLARK_ACCEPT_VARIABLE_COST='1',CHAOS_POI_INFRASTRUCTURE_ENABLED='1')
        env.start();self.addCleanup(env.stop)
        self.options={'_maplark_pilot':True,'_spatial':dict(lat=52,lon=21,radius=300,filters=list(FILTERS))}

    def fetch(self):
        return self.service.fetch('irrelevant legacy query',[],8,300,1800,self.options)

    def test_allowlist_default_off_and_exact_match(self):
        self.assertTrue(pilot_user('tester'))
        self.assertFalse(pilot_user('other')); self.assertFalse(pilot_user('test'))
        with patch.dict(os.environ,CHAOS_POI_MAPLARK_PILOT_ENABLED='0'):
            self.assertFalse(pilot_user('tester'))
            with self.assertRaisesRegex(POIError,'disabled'): self.fetch()

    def test_fetch_cache_and_actual_fasade(self):
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(normalized([point()]),{})) as acquire:
            a=self.fetch(); b=self.fetch()
            self.assertEqual(a,b); acquire.assert_called_once()
            fetcher=POIFetcher(tag_filters=list(FILTERS)); fetcher._poi_service=self.service
            rows=fetcher.get_all(52,21,scan_options={'_maplark_pilot':True})
            self.assertEqual(len(rows),1); self.assertEqual(rows[0]['osm_id'],1)
            acquire.assert_called_once()

    def test_disabling_provider_also_blocks_cached_results(self):
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',return_value=(normalized([point()]),{})):
            self.fetch()
        v=self.registry.list()[0]
        self.registry.enable(v['id'],v['revision'],False,'test')
        with self.assertRaisesRegex(POIError,'not_approved'): self.fetch()

    def test_disable_during_request_prevents_cache_write(self):
        def acquire(*args,**kwargs):
            v=self.registry.list()[0]; self.registry.enable(v['id'],v['revision'],False,'test')
            return normalized([point()]),{}
        with patch('poi_infrastructure.maplark_pilot.acquire_maplark',side_effect=acquire):
            with self.assertRaises(POIError): self.fetch()
        c=self.service.repo.connect()
        try: self.assertEqual(c.execute('SELECT COUNT(*) FROM cache').fetchone()[0],0)
        finally: c.close()

    def test_profile_has_relation_marker_and_preserves_boundary_point(self):
        f=point(); f['geometry']['coordinates']=[.0027,0]
        relation=dict(type='Feature',id='relation/9',properties=dict(tags={'amenity':'school'}),
            geometry=dict(type='MultiPolygon',coordinates=[[[[0,0],[.001,0],[.001,.001],[0,0]]]]))
        result=export_maplark(normalized([relation,f]))
        self.assertEqual([e['type'] for e in result['elements']],['node','relation'])
        self.assertEqual(result['elements'][1]['center'],{'lat':.0005,'lon':.0005})
        self.assertEqual(result['elements'][0]['id'],1)

    def test_partial_batch_never_exported(self):
        from dataclasses import replace
        with self.assertRaises(ContractError):
            export_maplark(replace(normalized([point()]),completeness='partial'))
