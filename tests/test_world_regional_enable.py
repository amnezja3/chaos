from contextlib import closing
from pathlib import Path
import unittest
from unittest.mock import patch
import test_overpass_collection_enable as fixtures
from tools.overpass_collection_enable import configure as background,PID
from tools.world_regional_enable import configure
from poi_infrastructure.providers import Registry
from poi_infrastructure.routing import Routing


class RegionalEnableTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.EnableTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        f=self.fixture
        backup=f.setup_vk()
        background(f.repo,f.path,backup)
        # Existing live MapLark is a required fallback.
        f.provider['scopes']+=['normal_scan']
        f.save_provider()

    def test_plan_is_passive_and_apply_retains_budget_background_and_expiry(self):
        f=self.fixture
        before=Registry(f.repo).list()
        budgets=f.ledger.status(PID)
        with closing(f.repo.connect()) as c:dump='\n'.join(c.iterdump())
        self.assertEqual(configure(f.repo)['status'],'plan')
        with closing(f.repo.connect()) as c:self.assertEqual('\n'.join(c.iterdump()),dump)
        backup=Path(f.tmp.name)/'live.sqlite3'
        with patch('socket.create_connection',side_effect=AssertionError('network')):
            result=configure(f.repo,backup,approve=True)
        self.assertEqual(result['status'],'configured')
        self.assertTrue(backup.exists())
        p=next(p for p in Registry(f.repo).list() if p['id']==PID)
        self.assertTrue({'normal_scan','wide_fetch','background_refresh'}<=set(p['scopes']))
        self.assertEqual(p['review_due_at'],next(p for p in before if p['id']==PID)['review_due_at'])
        self.assertEqual(Routing(f.repo).get('poi','live')['chain'],[PID,'maplark'])
        self.assertEqual(Routing(f.repo).get('poi','background')['chain'][0],'maplark')
        self.assertEqual([b['committed'] for b in budgets],[b['committed'] for b in f.ledger.status(PID)])

    def test_apply_requires_decision_before_backup_or_mutation(self):
        f=self.fixture;backup=Path(f.tmp.name)/'no.sqlite3'
        with self.assertRaisesRegex(ValueError,'decision_required'):configure(f.repo,backup)
        self.assertFalse(backup.exists())
