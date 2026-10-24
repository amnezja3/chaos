import json
from contextlib import closing
from pathlib import Path
import sqlite3
import time
import unittest
from unittest.mock import patch

import test_world_region_probe
from poi_infrastructure.providers import Registry
from poi_infrastructure.world_storage import CanonicalWorldRepository
from poi_infrastructure.world_read import WorldReadPlanner,AREA_SELECTION
from poi_infrastructure.world_adapters import MAPLARK_VERSION
from poi_infrastructure.world_contract import ContractError
from tools.world_region_pilot import run,check,BOUNDS,KEY,ADAPTER


class RegionPilotTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_world_region_probe.RegionProbeTests()
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.repo=self.fixture.repo
        CanonicalWorldRepository(self.repo).initialize_canonical()
        with self.repo.transaction() as c:
            p=Registry(self.repo)._load(c,'maplark');p['scopes'].append('world_storage')
            c.execute('UPDATE poi_provider_config SET config=? WHERE id=?',(json.dumps(p),'maplark'))
        self.output=Path(self.fixture.tmp.name)/'pilot'
        self.backup=Path(self.fixture.tmp.name)/'backup.sqlite3'

    def call(self):
        return run(self.repo.path,self.output,self.backup,execute=True,approve=True,
                   accept_variable_cost=True,transport=self.fixture.transport)

    def test_plan_and_missing_approval_do_not_write(self):
        missing=self.output/'absent.sqlite3'
        self.assertEqual(run(missing)['network_calls'],0)
        self.assertFalse(missing.exists())
        with self.assertRaisesRegex(ContractError,'approval_required'):
            run(self.repo.path,self.output,self.backup,execute=True)
        self.fixture.transport.assert_not_called();self.assertFalse(self.backup.exists())

    def test_real_geometry_fresh_publication_and_independent_local_reads(self):
        base=Path(__file__).parent/'fixtures/poi/maplark_roads_bbox_20261024'
        body=json.loads(base.with_suffix('.json').read_text(encoding='utf8'))
        meta=json.loads(base.with_suffix('.metadata.json').read_text(encoding='utf8'))
        self.fixture.transport.return_value=(200,None,dict(body=body,response_headers=meta['headers']))
        before=Registry(self.repo).list()
        result=self.call()
        self.assertEqual((result['raw_objects'],result['stored_objects']),(76,75))
        self.assertEqual(result['excluded_ids'],('osm:way:201343570',))
        self.assertTrue(result['local_verification']['full_geometry_and_union_pass'])
        self.assertEqual(Registry(self.repo).list(),before)
        with patch('socket.create_connection',side_effect=AssertionError('no HTTP')):
            verified=check(self.repo.path)
        self.assertEqual(verified['status'],'local_pilot_pass')
        self.assertEqual([verified['reads'][k]['objects'] for k in ('parent','left','right')],[75,33,54])
        self.fixture.transport.assert_called_once()
        p=Registry(self.repo).list()[0]
        reader=WorldReadPlanner(CanonicalWorldRepository(self.repo))
        options=dict(provider='maplark',revision=p['revision'],storage_reference=p['evidence']['reference'],
                     profile='roads',layer='roads',selection=AREA_SELECTION,bounds=BOUNDS)
        # A normal MapLark reader cannot consume the experimental pilot proof.
        self.assertEqual(reader.read(**options,adapter_version=MAPLARK_VERSION).state,'MISS')
        options['bounds']=(20.35,51.53,20.37,51.54)
        self.assertEqual(reader.read(**options,adapter_version=ADAPTER).state,'MISS')
        c=sqlite3.connect(self.backup)
        try:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)
        finally:c.close()

    def test_existing_backup_never_overwritten(self):
        self.backup.write_bytes(b'preserve')
        with self.assertRaises(FileExistsError):self.call()
        self.assertEqual(self.backup.read_bytes(),b'preserve')
        self.fixture.transport.assert_not_called()

    def test_world_storage_scope_required_before_backup_or_request(self):
        with self.repo.transaction() as c:
            p=Registry(self.repo)._load(c,'maplark');p['scopes']=['storage']
            c.execute('UPDATE poi_provider_config SET config=? WHERE id=?',(json.dumps(p),'maplark'))
        with self.assertRaisesRegex(ContractError,'world_storage_required'):self.call()
        self.assertFalse(self.backup.exists());self.fixture.transport.assert_not_called()

    def test_partial_response_charged_without_snapshot_or_retry(self):
        self.fixture.headers['X-Has-More']='true'
        with self.assertRaisesRegex(ContractError,'incomplete'):self.call()
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)
        self.assertEqual(self.fixture.ledger.status('maplark')[0]['committed'],3)
        self.output=self.output.with_name('second');self.backup=self.backup.with_name('second.sqlite3')
        with self.assertRaisesRegex(ContractError,'already_used'):self.call()
        self.fixture.transport.assert_called_once()

    def test_expiry_and_policy_revision_are_misses_without_network(self):
        self.call()
        self.assertEqual(check(self.repo.path)['status'],'local_pilot_pass')
        with patch('poi_infrastructure.world_read.time.time',return_value=time.time()+1801):
            self.assertEqual(check(self.repo.path)['status'],'local_pilot_not_fresh')
        with self.repo.transaction() as c:
            p=Registry(self.repo)._load(c,'maplark');p['revision']+=1
            c.execute('UPDATE poi_provider_config SET revision=?,config=? WHERE id=?',
                      (p['revision'],json.dumps(p),'maplark'))
        self.assertEqual(check(self.repo.path)['status'],'local_pilot_not_fresh')
        self.fixture.transport.assert_called_once()

    def test_changed_policy_during_request_preserves_charge_without_publish(self):
        response=self.fixture.transport.return_value
        def change(*args,**kwargs):
            with self.repo.transaction() as c:
                p=Registry(self.repo)._load(c,'maplark');p['revision']+=1
                c.execute('UPDATE poi_provider_config SET revision=?,config=? WHERE id=?',
                          (p['revision'],json.dumps(p),'maplark'))
            return response
        self.fixture.transport.side_effect=change
        with self.assertRaisesRegex(Exception,'scanner_inactive'):self.call()
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_snapshot').fetchone()[0],0)
        self.assertEqual(self.fixture.ledger.status('maplark')[0]['committed'],3)
        self.assertFalse(self.repo.owns(KEY,'anything'))

    def test_empty_pilot_does_not_qualify_region(self):
        self.fixture.body['features']=[]
        self.fixture.headers['X-Returned']='0'
        with self.assertRaisesRegex(ContractError,'empty_pilot_needs_review'):self.call()
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_coverage').fetchone()[0],0)
        self.fixture.transport.assert_called_once()
