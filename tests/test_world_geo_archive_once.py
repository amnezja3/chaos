from contextlib import closing
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import test_world_discovery_worker as fixtures
from test_world_geoapify import response
from tools.world_geo_archive_once import run, IDENTITY
from poi_infrastructure.world_contract import ContractError
from poi_infrastructure.routing import reason


class GeoArchiveOnceTests(unittest.TestCase):
    setUp = fixtures.DiscoveryWorkerTests.setUp
    save_provider = fixtures.DiscoveryWorkerTests.save_provider

    def old_costs(self):
        now = time.time()
        self.ledger.configure_window('geoapify', 'old', now-100, now-10, 20)
        for i in range(4):
            self.ledger.reserve('geoapify', 'old'+str(i), 5, now=now-50)
            self.ledger.settle('geoapify', 'old'+str(i))

    def candidate(self):
        geo = dict(self.provider, id='geoapify', revision=2, enabled=False,
                   url='https://api.geoapify.com/v2/places', operator_group='api.geoapify.com',
                   scopes=['small_probe'], technical_status='untested', probe_allowed=True)
        with self.repo.transaction() as c:
            c.execute('INSERT INTO poi_provider_config VALUES (?,?,?)', ('geoapify',2,json.dumps(geo)))
        env = patch.dict('os.environ', CHAOS_GEOAPIFY_API_KEY='synthetic')
        env.start(); self.addCleanup(env.stop)
        self.transport.return_value = response(2)
        return Path(self.tmp.name)/'archive'

    def test_carry_forward_preserves_uncertain_and_only_adds_five(self):
        self.old_costs()
        now = time.time()
        result = self.ledger.carry_forward('geoapify','new',now,now+3600,5)
        self.assertEqual(result['carried'],20)
        self.assertEqual(self.ledger.status('geoapify')[0]['remaining'],5)
        self.assertTrue(self.ledger.reserve('geoapify','new-call',5))
        self.ledger.settle('geoapify','new-call')
        with self.assertRaises(ContractError):
            self.ledger.reserve('geoapify','extra',1)
        with self.assertRaises(ContractError):
            self.ledger.carry_forward('geoapify','new',now,now+3600,5)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM world_credit_operation WHERE account='geoapify' AND state='uncertain'").fetchone()[0],5)
        self.ledger.settle('geoapify','old0',2)
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],22)

    def test_plain_new_window_still_cannot_bypass_old_unresolved(self):
        self.old_costs()
        now=time.time()
        self.ledger.configure_window('geoapify','plain',now-1,now+100,25)
        with self.assertRaisesRegex(ContractError,'previous_period_unresolved'):
            self.ledger.reserve('geoapify','no-carry',5)

    def test_expired_carry_and_hold_never_allow_a_new_request(self):
        self.old_costs(); now=time.time()
        self.ledger.carry_forward('geoapify','new',now,now+100,5)
        with self.assertRaises(ContractError):
            self.ledger.reserve('geoapify','late',5,now=now+101)
        with self.assertRaises(ContractError):
            self.ledger.configure_window('geoapify','carry:fake',now,now+100,100)
        with self.repo.transaction() as c:
            c.execute('INSERT INTO world_credit_hold VALUES (?,?)',('geoapify','fixture'))
        with self.assertRaisesRegex(ContractError,'held'):
            self.ledger.reserve('geoapify','held',5)

    def test_active_windows_cannot_be_replaced_with_new_allowance(self):
        now=time.time()
        self.ledger.configure_window('geoapify','active',now-1,now+100,5)
        with self.assertRaisesRegex(ContractError,'active_window'):
            self.ledger.carry_forward('geoapify','new',now,now+100,5)

    def test_capture_archives_without_enabling_gameplay_or_second_request(self):
        output=self.candidate(); self.old_costs()
        result=run(self.repo.path,output,execute=True,transport=self.transport)
        self.assertEqual(result['status'],'archived_observations')
        self.assertEqual(result['objects'],2)
        self.assertTrue(result['local_readback_pass'])
        self.assertEqual(result['carry_forward']['carried'],20)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_retention').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM world_coverage').fetchone()[0],0)
            provider=json.loads(c.execute("SELECT config FROM poi_provider_config WHERE id='geoapify'").fetchone()[0])
        self.assertIsNotNone(reason(provider,'poi','live'))
        self.assertIsNotNone(reason(provider,'poi','background'))
        self.assertEqual(run(self.repo.path,output,execute=True)['network_calls'],0)
        self.assertEqual(self.transport.call_count,1)
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],25)
        with self.assertRaises(ValueError):
            run(self.repo.path,output.with_name('other'),execute=True,transport=self.transport)
        self.assertEqual(self.transport.call_count,1)

    def test_failure_does_not_certify_or_retry(self):
        output=self.candidate(); self.old_costs()
        self.transport.return_value=(502,None,{})
        with self.assertRaises(Exception):
            run(self.repo.path,output,execute=True,transport=self.transport)
        result=run(self.repo.path,output,execute=True,transport=self.transport)
        self.assertEqual(result['status'],'already_attempted_inspect_saved_report')
        self.assertEqual(self.transport.call_count,1)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)
            self.assertEqual(c.execute("SELECT revision FROM poi_provider_config WHERE id='geoapify'").fetchone()[0],2)

    def test_revocation_during_request_prevents_publication(self):
        output=self.candidate(); self.old_costs()
        def revoke(*args, **kwargs):
            with self.repo.transaction() as c:
                c.execute("UPDATE poi_provider_config SET revision=3,config=json_set(config,'$.revision',3) WHERE id='geoapify'")
            return response(1)
        self.transport.side_effect=revoke
        with self.assertRaises(Exception):
            run(self.repo.path,output,execute=True,transport=self.transport)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)
        self.assertEqual(self.ledger.status('geoapify')[0]['committed'],25)

    def test_plan_does_not_need_database_secret_or_permissions(self):
        output=Path(self.tmp.name)/'absent'
        self.assertEqual(run('missing',output)['network_calls'],0)
        self.assertFalse(output.exists())
