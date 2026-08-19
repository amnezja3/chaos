import unittest
from unittest.mock import Mock, patch

from scripts import territory_conflict_worker as worker


class TerritoryWorkerGhostNetworkFairnessTest(unittest.TestCase):
    def setUp(self):
        worker._consecutive_ghostnetwork_jobs = 0
        worker._ghostnetwork_delivery_turn = True

    def common_patches(self):
        return (
            patch.object(worker.run, "retry_pending_strategic_progression", return_value=[]),
            patch.object(worker.run, "process_territory_rebuild_job", return_value=None),
            patch.object(worker.run, "process_territory_reconciliation_set", return_value=None),
        )

    def test_one_ghostnetwork_job_can_run_before_conflict_candidate(self):
        patches = self.common_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        with patch.object(worker, "process_ghostnetwork_once", return_value=True) as ghost, \
                patch.object(worker.run.territory_conflict_store, "list_rebuild_candidates") as conflicts:
            self.assertTrue(worker.process_once())
        ghost.assert_called_once_with()
        conflicts.assert_not_called()
        self.assertEqual(worker._consecutive_ghostnetwork_jobs, 1)

    def test_conflict_job_is_not_starved_by_ghostnetwork_backlog(self):
        patches = self.common_patches()
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        worker._consecutive_ghostnetwork_jobs = 1
        conflict_store = Mock()
        conflict_store.list_rebuild_candidates.return_value = [{"conflict_id": "conflict-1"}]
        with patch.object(worker, "process_ghostnetwork_once", return_value=True) as ghost, \
                patch.object(worker.run, "territory_conflict_store", conflict_store), \
                patch.object(worker.run, "consolidate_conflict_rebuild", return_value={"ok": True}), \
                patch.object(worker.run, "finalize_conflict_rebuild_profiles", return_value=[]):
            self.assertTrue(worker.process_once())
        ghost.assert_not_called()
        self.assertEqual(worker._consecutive_ghostnetwork_jobs, 0)

    def test_delta_delivery_and_territory_jobs_alternate(self):
        delivery = {"job_id": "delta-1", "event_id": "event-1", "ok": True}
        territory = {"job_id": "territory-1", "job_kind": "areas", "ok": True}
        with patch.object(
            worker.run, "process_ghostnetwork_delta_delivery_job", return_value=delivery
        ) as deliver, patch.object(
            worker.run, "process_ghostnetwork_territory_job", return_value=territory
        ) as reconcile:
            self.assertTrue(worker.process_ghostnetwork_once())
            self.assertFalse(worker._ghostnetwork_delivery_turn)
            self.assertTrue(worker.process_ghostnetwork_once())
            self.assertTrue(worker._ghostnetwork_delivery_turn)
        self.assertEqual(deliver.call_count, 1)
        self.assertEqual(reconcile.call_count, 1)


if __name__ == "__main__":
    unittest.main()
