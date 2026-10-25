from contextlib import closing
import time
from pathlib import Path
import unittest
from unittest.mock import patch

import test_world_discovery_worker as fixtures
from poi_infrastructure.archive_retention import retain_saved
from poi_infrastructure.world_storage import CanonicalWorldRepository


class SavedRetentionTests(unittest.TestCase):
    setUp = fixtures.DiscoveryWorkerTests.setUp
    save_provider = fixtures.DiscoveryWorkerTests.save_provider

    def snapshot(self):
        self.provider['review_due_at'] = time.time()+8*86400
        self.save_provider()
        return self.worker.run_one()['snapshot']

    def test_archive_after_cache_expiry_preserves_payload_freshness_and_cost(self):
        snapshot = self.snapshot()
        with closing(self.repo.connect()) as c:
            before = tuple(c.execute('SELECT * FROM world_snapshot WHERE id=?',(snapshot,)).fetchone())
        later = time.time()+3600
        with patch('time.time', return_value=later):
            result = retain_saved(self.repo, [snapshot], apply=True)
            self.assertIsNone(CanonicalWorldRepository(self.repo).read_batch(snapshot, allow_stale=True))
            self.assertEqual(CanonicalWorldRepository(self.repo).prune_expired(), 0)
            again = retain_saved(self.repo, [snapshot], apply=True)
        self.assertTrue(again['items'][0]['already_retained'])
        self.assertEqual(result['items'][0]['retain_until'], again['items'][0]['retain_until'])
        with closing(self.repo.connect()) as c:
            self.assertEqual(before, tuple(c.execute('SELECT * FROM world_snapshot WHERE id=?',(snapshot,)).fetchone()))
        self.assertEqual(self.transport.call_count, 1)
        self.assertEqual(self.ledger.status('maplark')[0]['committed'], 3)
        with patch('time.time', return_value=result['items'][0]['retain_until']+1):
            self.assertEqual(CanonicalWorldRepository(self.repo).prune_expired(), 1)

    def test_missing_member_of_batch_rolls_back_all(self):
        snapshot = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'snapshot_missing'):
            retain_saved(self.repo, [snapshot, 'a'*64], apply=True)
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_retention').fetchone()[0], 0)

    def test_plan_writes_no_retention(self):
        snapshot = self.snapshot()
        self.assertEqual(retain_saved(self.repo,[snapshot])['status'], 'plan')
        with closing(self.repo.connect()) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM world_retention').fetchone()[0],0)

    def test_changed_revision_and_bad_digest_are_rejected(self):
        snapshot = self.snapshot()
        self.provider['revision'] += 1; self.save_provider()
        with self.assertRaisesRegex(ValueError,'revision_changed'):
            retain_saved(self.repo,[snapshot],apply=True)
        self.provider['revision'] -= 1; self.save_provider()
        with self.repo.transaction() as c:
            c.execute('UPDATE world_snapshot SET digest=? WHERE id=?',('bad',snapshot))
        with self.assertRaisesRegex(ValueError,'digest_invalid'):
            retain_saved(self.repo,[snapshot],apply=True)

    def test_old_data_and_short_approval_cannot_extend_retention(self):
        snapshot = self.snapshot()
        with patch('time.time',return_value=time.time()+7*86400+1):
            with self.assertRaisesRegex(ValueError,'deadline_not_allowed'):
                retain_saved(self.repo,[snapshot],apply=True)
        self.provider['review_due_at']=time.time()+3600; self.save_provider()
        with self.assertRaisesRegex(ValueError,'deadline_not_allowed'):
            retain_saved(self.repo,[snapshot],apply=True)

    def test_cli_plan_then_backup_and_apply_never_overwrites_backup(self):
        from tools.world_maplark_retain import run
        snapshot=self.snapshot()
        backup=Path(self.tmp.name)/'backup.sqlite3'
        with patch('tools.world_maplark_retain.SNAPSHOTS',[snapshot]):
            self.assertEqual(run(self.repo.path)['status'],'plan')
            self.assertFalse(backup.exists())
            self.assertEqual(run(self.repo.path,backup)['status'],'retained')
            data=backup.read_bytes()
            with self.assertRaises(FileExistsError): run(self.repo.path,backup)
            self.assertEqual(data,backup.read_bytes())

    def test_absent_snapshot_does_not_create_backup_or_retention(self):
        from tools.world_maplark_retain import run
        backup=Path(self.tmp.name)/'backup.sqlite3'
        with self.assertRaisesRegex(ValueError,'snapshot_missing'):
            run(self.repo.path,backup)
        self.assertFalse(backup.exists())
