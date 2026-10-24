from contextlib import closing
import json
from pathlib import Path
import time
import unittest

import test_world_discovery_worker as fixtures
from poi_infrastructure.discovery_queue import DemandQueue
from poi_infrastructure.providers import Registry
from tools.discovery_pilot_prepare import prepare, PILOT


class PilotPreparationTests(unittest.TestCase):
    save_provider=fixtures.DiscoveryWorkerTests.save_provider

    def setUp(self):
        fixtures.DiscoveryWorkerTests.setUp(self)
        self.provider.update(scopes=['normal_scan','storage'],review_due_at=time.time()+86400,
            evidence=dict(reference='existing',notes='existing',source_url='https://example.org/terms'))
        self.save_provider()
        self.path=Path(self.tmp.name)/'permit.json'
        self.backup=Path(self.tmp.name)/'backup.sqlite3'
        DemandQueue(self.repo).record(20.366130,51.531034,['roads'])

    def test_prepare_preserves_gameplay_and_repeat_does_not_extend_or_reset(self):
        self.ledger.reserve('maplark','previous',20)
        self.ledger.settle('maplark','previous',3)
        result=prepare(self.repo.path,self.path,self.backup)
        self.assertEqual(result['network_calls'],0)
        self.assertEqual(len(result['plan']['jobs']),1)
        original=self.path.read_bytes()
        current=Registry(self.repo).list()[0]
        self.assertTrue(current['enabled'])
        self.assertIn('normal_scan',current['scopes'])
        self.assertIn('background_refresh',current['scopes'])
        self.assertEqual(self.ledger.status('maplark')[0]['committed'],3)
        self.assertEqual(self.ledger.scope_status('maplark','discovery:'+PILOT)['credit_limit'],20)
        self.assertEqual(prepare(self.repo.path,self.path,self.backup)['status'],'already_prepared')
        self.assertEqual(self.path.read_bytes(),original)
        self.assertEqual(Registry(self.repo).list()[0]['revision'],current['revision'])
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_discovery_job').fetchone()[0],1)
        self.transport.assert_not_called()

    def test_expired_permit_is_not_recreated(self):
        prepare(self.repo.path,self.path,self.backup)
        data=json.loads(self.path.read_text());data['until']=time.time()-1
        self.path.write_text(json.dumps(data))
        with self.assertRaises(ValueError): prepare(self.repo.path,self.path,self.backup)

    def test_deleted_permit_cannot_reset_existing_budget(self):
        prepare(self.repo.path,self.path,self.backup)
        self.path.unlink()
        with self.assertRaisesRegex(ValueError,'pilot_already_exists'):
            prepare(self.repo.path,self.path,Path(self.tmp.name)/'another.sqlite3')
