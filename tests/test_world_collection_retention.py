from contextlib import closing
from dataclasses import replace
import json
import time
import unittest
from unittest.mock import patch

import test_world_discovery_worker as fixtures
from poi_infrastructure.world_storage import CanonicalWorldRepository


class CollectionRetentionTests(unittest.TestCase):
    setUp = fixtures.DiscoveryWorkerTests.setUp
    save_provider = fixtures.DiscoveryWorkerTests.save_provider

    def test_worker_archive_restart_expiry_and_cleanup_do_not_refetch(self):
        now = time.time()
        self.provider['review_due_at'] = now + 8 * 86400
        self.save_provider()
        self.worker.permit = replace(self.permit, retention_seconds=7 * 86400)
        self.transport.return_value[2]['response_headers']['X-Returned'] = '1'
        self.transport.return_value[2]['body']['features'] = [dict(type='Feature', id='way/2',
            geometry=dict(type='LineString', coordinates=[[21, 52], [21.001, 52.001]]),
            properties=dict(tags={'highway': 'residential'}))]
        result = self.worker.run_one()
        self.assertEqual(result['status'], 'committed')
        snapshot = result['snapshot']
        world = CanonicalWorldRepository(self.repo)
        with closing(self.repo.connect()) as c:
            deadline = c.execute('SELECT retain_until FROM world_retention WHERE snapshot_id=?',
                                 (snapshot,)).fetchone()[0]
            original = c.execute('SELECT payload FROM world_snapshot WHERE id=?', (snapshot,)).fetchone()[0]
            self.assertEqual(len(json.loads(original)['objects']), 1)
        # Reopen from disk as a restarted process would, without another request.
        from poi_infrastructure.repository import Repository
        reopened = CanonicalWorldRepository(Repository(self.repo.path))
        with patch('time.time', return_value=now + 86400):
            self.assertIsNone(reopened.read_batch(snapshot, allow_stale=True))
            self.assertEqual(reopened.prune_expired(), 0)
            with closing(self.repo.connect()) as c:
                self.assertEqual(c.execute('SELECT payload FROM world_snapshot WHERE id=?',
                                           (snapshot,)).fetchone()[0], original)
        with patch('time.time', return_value=deadline + 1):
            self.assertEqual(world.prune_expired(), 1)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_retention').fetchone()[0], 0)
            self.assertEqual(c.execute('SELECT count(*) FROM world_member').fetchone()[0], 0)
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 3)

    def test_short_review_stops_before_network_or_charge(self):
        self.worker.permit = replace(self.permit, retention_seconds=7 * 86400)
        result = self.worker.run_one()
        self.assertNotEqual(result['status'], 'committed')
        self.transport.assert_not_called()
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 0)
