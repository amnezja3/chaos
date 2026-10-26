import json
from pathlib import Path
import time
import unittest

import test_world_discovery_worker as fixtures
from poi_infrastructure.providers import Registry
from poi_infrastructure.routing import Routing
from poi_infrastructure.regular_discovery import DEFAULTS
from tools.overpass_collection_enable import configure, PID, URL, LAYERS


class EnableTests(unittest.TestCase):
    setUp = fixtures.DiscoveryWorkerTests.setUp
    save_provider = fixtures.DiscoveryWorkerTests.save_provider

    def setup_vk(self):
        Routing(self.repo).initialize()
        self.path = Path(self.tmp.name)/'policy.json'
        self.path.write_text(json.dumps(dict(DEFAULTS, review_until=time.time()+86400)))
        self.vk = dict(self.provider, id=PID, url=URL, operator_group='maps.mail.ru',
                       enabled=False, scopes=['small_probe'], probe_allowed=True, priority=0)
        self.write_vk()
        return Path(self.tmp.name)/'backup.sqlite3'

    def write_vk(self):
        with self.repo.transaction() as c:
            c.execute('INSERT OR REPLACE INTO poi_provider_config VALUES (?,?,?)',
                      (PID, self.vk['revision'], json.dumps(self.vk)))

    def test_plan_then_apply_preserves_live_and_costs_and_is_repeatable(self):
        backup = self.setup_vk()
        live = Routing(self.repo).get('poi', 'live')
        self.assertEqual(configure(self.repo, self.path)['status'], 'plan')
        self.assertFalse(next(p for p in Registry(self.repo).list() if p['id']==PID)['enabled'])
        result = configure(self.repo, self.path, backup)
        self.assertEqual(result['status'], 'configured')
        self.assertTrue(backup.is_file())
        for layer in LAYERS:
            self.assertEqual(Routing(self.repo).get(layer, 'background')['chain'], [PID, 'maplark'])
        self.assertEqual(Routing(self.repo).get('poi', 'live'), live)
        self.ledger.reserve(PID, 'existing-attempt', 1)
        repeated = configure(self.repo, self.path, backup.with_name('second.sqlite3'))
        self.assertEqual(repeated['revision'], result['revision'])
        self.assertEqual(self.ledger.status(PID)[0]['committed'], 1)
        self.transport.assert_not_called()

    def test_failed_probe_blocks_before_backup_or_enable(self):
        backup = self.setup_vk()
        self.vk['technical_status']='tested_failed'; self.write_vk()
        with self.assertRaisesRegex(ValueError, 'successful_probe_required'):
            configure(self.repo, self.path, backup)
        self.assertFalse(backup.exists())

    def test_existing_backup_is_not_overwritten(self):
        backup = self.setup_vk(); backup.write_bytes(b'preserve')
        with self.assertRaises(FileExistsError):
            configure(self.repo, self.path, backup)
        self.assertEqual(backup.read_bytes(), b'preserve')

    def test_expired_policy_cannot_be_renewed_by_enable(self):
        backup = self.setup_vk()
        self.path.write_text(json.dumps(dict(DEFAULTS, review_until=time.time()-1)))
        with self.assertRaises(ValueError):
            configure(self.repo, self.path, backup)
        self.assertFalse(backup.exists())
