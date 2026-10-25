from contextlib import closing
from dataclasses import replace
import json
import os
import time
import unittest
from unittest.mock import patch

import test_world_discovery_worker as fixtures
from test_world_geoapify import response
from poi_infrastructure.discovery_producer import prepare_jobs
from poi_infrastructure.discovery_queue import DemandQueue
from poi_infrastructure.routing import capability


class GeoapifyCollectionTests(unittest.TestCase):
    save_provider = fixtures.DiscoveryWorkerTests.save_provider

    def setUp(self):
        fixtures.DiscoveryWorkerTests.setUp(self)
        self.geo = dict(self.provider,id='geoapify',url='https://api.geoapify.com/v2/places',
                        operator_group='api.geoapify.com')
        self.save_geo()
        self.permit = replace(self.permit, profiles=frozenset({'poi'}), reservation=5,
                              acquisition='geoapify-commercial-v1')
        self.worker.permit = self.permit
        self.ledger.configure_window('geoapify','collection',time.time()-1,self.permit.until,20)
        for scope in self.permit.budget_scopes('poi'):
            self.ledger.configure_scope('geoapify',scope,time.time()-1,self.permit.until,20)
        DemandQueue(self.repo).record(21,52,['poi'])
        env=patch.dict(os.environ,CHAOS_GEOAPIFY_API_KEY='fixture-geo')
        env.start();self.addCleanup(env.stop)
        self.transport.return_value=response(2)

    def save_geo(self):
        with self.repo.transaction() as c:
            c.execute('INSERT OR REPLACE INTO poi_provider_config VALUES (?,?,?)',
                      ('geoapify',1,json.dumps(self.geo)))

    def test_collection_stores_unknown_points_and_reserves_unknown_cost_once(self):
        key=prepare_jobs(self.repo,self.permit,apply=True)['jobs'][0]
        result=self.worker.run_one()
        self.assertEqual(result['status'],'committed')
        self.assertEqual(result['coverage'],'UNKNOWN')
        self.assertEqual(result['response_completeness'],'unknown')
        self.assertEqual(result['billing']['billing_state'],'uncertain')
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],5)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],0)
        with closing(self.repo.connect()) as c:
            payload=json.loads(c.execute('SELECT payload FROM world_snapshot').fetchone()[0])
        self.assertEqual(len(payload['objects']),2)
        self.assertNotIn('coverage',payload)
        self.assertEqual(payload['observation_context']['request_params']['categories'],'commercial')
        self.assertEqual(self.jobs.get(key)['state'],'COMMITTED')
        self.assertEqual(self.worker.run_one()['status'],'idle')
        self.assertEqual(self.jobs.get(self.key)['attempts'],0)
        self.transport.assert_called_once()

    def test_empty_unknown_is_not_claim_of_empty_region(self):
        prepare_jobs(self.repo,self.permit,apply=True)
        self.transport.return_value=response(0)
        result=self.worker.run_one()
        self.assertEqual(result['status'],'committed')
        self.assertEqual(result['coverage'],'UNKNOWN')
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_coverage').fetchone()[0],0)

    def test_small_probe_does_not_authorize_collection(self):
        self.geo['scopes']=['small_probe']
        self.save_geo()
        self.assertEqual(prepare_jobs(self.repo,self.permit,apply=True)['status'],'policy_blocked')
        self.transport.assert_not_called()

    def test_revocation_inflight_keeps_cost_but_does_not_publish(self):
        prepare_jobs(self.repo,self.permit,apply=True)
        def revoke(*a,**kw):
            self.geo['enabled']=False
            self.save_geo()
            return response(2)
        self.transport.side_effect=revoke
        self.assertEqual(self.worker.run_one()['status'],'reconciliation_required')
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],5)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)

    def test_routing_support_does_not_enable_live_or_non_poi(self):
        self.assertIsNone(capability(self.geo,'poi','background'))
        self.assertEqual(capability(self.geo,'poi','live'),'geoapify_contract_unverified')
        self.assertEqual(capability(self.geo,'roads','background'),'unsupported_layer')
        with self.assertRaises(ValueError):
            replace(self.permit,profiles=frozenset({'roads'})).validate()
