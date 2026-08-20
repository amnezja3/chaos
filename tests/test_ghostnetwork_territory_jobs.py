import os
import tempfile
import unittest
from unittest.mock import Mock, patch

import run
import database
from database import GhostNetworkDeltaDeliveryJobStore, GhostNetworkTerritoryJobStore, TerritoryStore
from tools.ghostnetwork_runtime import build_parser, enqueue_territory_reconcile


class GhostNetworkTerritoryJobStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "territory-jobs.sqlite3")
        self.store = GhostNetworkTerritoryJobStore(self.db_path)
        self.delivery_store = GhostNetworkDeltaDeliveryJobStore(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_enqueue_is_idempotent_and_claim_has_single_owner(self):
        first = self.store.enqueue("areas", "alice", "version-1", reason="capture")
        duplicate = self.store.enqueue("areas", "alice", "version-1", reason="capture")
        self.assertTrue(first["enqueued"])
        self.assertFalse(duplicate["enqueued"])

        claim = self.store.claim("worker-a", lease_seconds=30)
        self.assertEqual(claim["job_id"], first["job_id"])
        self.assertIsNone(self.store.claim("worker-b", lease_seconds=30))
        self.assertTrue(self.store.finish(claim["job_id"], "worker-a", ok=True))
        self.assertEqual(self.store.status_counts(), {"complete": 1})

    def test_request_path_enqueues_without_running_ghostnetwork_bridge(self):
        areas = [{"id": 7, "owner_username": "alice", "status": "active", "vertices": []}]
        publisher = Mock()
        publisher.record_areas_updated.return_value = [{"type": "territory.updated"}]
        bridge = Mock(side_effect=AssertionError("bridge must not run in web publication"))
        with patch.object(run, "territory_delta_publisher", publisher), \
                patch.object(run, "ghostnetwork_territory_job_store", self.store), \
                patch.object(run, "bridge_ghostnetwork_territory_publication", bridge):
            result = run.record_territory_areas_delta("alice", areas, reason="capture")

        self.assertEqual(result, [{"type": "territory.updated"}])
        self.assertFalse(bridge.called)
        claim = self.store.claim("worker")
        self.assertEqual(claim["job_kind"], "areas")
        self.assertEqual(claim["reference_id"], "alice")

    def test_worker_loads_canonical_conflict_snapshot(self):
        self.store.enqueue("conflict", "conflict-7", "4", reason="resolved")
        snapshot = {"conflict": {"conflict_id": "conflict-7", "conflict_version": 4}}
        conflict_store = Mock()
        conflict_store.latest_snapshot_state.return_value = snapshot
        bridge = Mock(return_value={"ok": True})
        with patch.object(run, "ghostnetwork_territory_job_store", self.store), \
                patch.object(run, "territory_conflict_store", conflict_store), \
                patch.object(run, "bridge_ghostnetwork_conflict_publication", bridge):
            result = run.process_ghostnetwork_territory_job("worker")

        self.assertTrue(result["ok"])
        conflict_store.latest_snapshot_state.assert_called_once_with("conflict-7")
        bridge.assert_called_once()
        args, kwargs = bridge.call_args
        self.assertEqual(args[0], snapshot)
        self.assertEqual(kwargs["reason"], "resolved")
        self.assertIsNotNone(kwargs["service"])
        self.assertIsInstance(kwargs["timings"], dict)
        self.assertEqual(self.store.status_counts(), {"complete": 1})

    def test_pending_area_jobs_are_coalesced_to_latest_snapshot(self):
        first = self.store.enqueue("areas", "alice", "version-1")
        second = self.store.enqueue("areas", "bob", "version-2")
        claim = self.store.claim("worker")

        self.assertEqual(claim["job_id"], second["job_id"])
        self.assertEqual(claim["coalesced_jobs"], 1)
        self.assertTrue(self.store.finish(claim["job_id"], "worker", ok=True))
        self.assertEqual(self.store.status_counts(), {"complete": 2})

    def test_poison_job_stops_after_five_attempts(self):
        self.store.enqueue("areas", "alice", "broken-version")
        clock = {"value": 1_800_000_000.0}
        with patch.object(database.time, "time", side_effect=lambda: clock["value"]):
            for attempt in range(5):
                claim = self.store.claim(f"worker-{attempt}")
                self.assertIsNotNone(claim)
                self.store.finish(claim["job_id"], f"worker-{attempt}", ok=False, error="broken")
                clock["value"] += 61
            self.assertIsNone(self.store.claim("worker-final"))
        self.assertEqual(self.store.status_counts(), {"failed": 1})

    def test_operator_reconcile_dry_run_is_read_only_and_apply_enqueues(self):
        territory = TerritoryStore(self.db_path)
        dry_run = enqueue_territory_reconcile(territory, self.store, apply=False)
        self.assertTrue(dry_run["dry_run"])
        self.assertEqual(self.store.status_counts(), {})

        applied = enqueue_territory_reconcile(territory, self.store, apply=True)
        self.assertTrue(applied["enqueued"])
        claim = self.store.claim("worker")
        self.assertEqual(claim["reference_id"], "__full__")

    def test_operator_reconcile_commands_have_separate_names(self):
        parser = build_parser()
        self.assertEqual(parser.parse_args(["capture-reconcile"]).command, "capture-reconcile")
        self.assertEqual(
            parser.parse_args(["reward-history-reconcile"]).command,
            "reward-history-reconcile",
        )
        self.assertEqual(parser.parse_args(["territory-reconcile"]).command, "territory-reconcile")

    def test_identical_geometry_keeps_ids_and_publication_version(self):
        territory = TerritoryStore(self.db_path)
        area = {
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.1, "lng": 21.0},
                {"lat": 52.0, "lng": 21.1},
            ],
            "centroid_lat": 52.033,
            "centroid_lng": 21.033,
            "area_size": 100.0,
            "max_edge_distance": 200.0,
            "status": "active",
        }
        first = territory.replace_player_areas("alice", [area])
        first_id = territory.list_player_areas("alice")[0]["id"]
        duplicate = territory.replace_player_areas("alice", [area])
        second_id = territory.list_player_areas("alice")[0]["id"]
        changed = territory.replace_player_areas(
            "alice", [{**area, "area_size": 101.0}]
        )

        self.assertEqual(first["publication_version"], 1)
        self.assertTrue(first["changed"])
        self.assertFalse(duplicate["changed"])
        self.assertEqual(duplicate["publication_version"], 1)
        self.assertEqual(first_id, second_id)
        self.assertTrue(changed["changed"])
        self.assertEqual(changed["publication_version"], 2)

    def test_encirclement_status_bumps_publication_only_once(self):
        territory = TerritoryStore(self.db_path)
        outer = {
            "vertices": [
                {"lat": 51.9, "lng": 20.9}, {"lat": 52.2, "lng": 20.9},
                {"lat": 52.2, "lng": 21.2}, {"lat": 51.9, "lng": 21.2},
            ],
            "centroid_lat": 52.05, "centroid_lng": 21.05,
            "area_size": 1000.0, "max_edge_distance": 500.0, "status": "active",
        }
        inner = {
            "vertices": [
                {"lat": 52.0, "lng": 21.0}, {"lat": 52.1, "lng": 21.0},
                {"lat": 52.1, "lng": 21.1}, {"lat": 52.0, "lng": 21.1},
            ],
            "centroid_lat": 52.05, "centroid_lng": 21.05,
            "area_size": 100.0, "max_edge_distance": 100.0, "status": "active",
        }
        territory.replace_player_areas("outer", [outer])
        territory.replace_player_areas("inner", [inner])
        territory.refresh_encirclement_statuses()
        first_version = territory.get_area_publication("inner")["publication_version"]
        self.assertEqual(territory.list_player_areas("inner")[0]["status"], "encircled")

        territory.refresh_encirclement_statuses()
        second_version = territory.get_area_publication("inner")["publication_version"]
        self.assertEqual(first_version, 2)
        self.assertEqual(second_version, first_version)

    def test_delta_delivery_uses_bounded_cursor_and_shared_snapshot(self):
        event = {
            "event_id": "event-1", "cycle_id": "cycle-1",
            "event_type": "ghost.part_contained", "state_version": 3,
        }
        viewers = [{"viewer_id": name} for name in ("alice", "bob", "carol")]
        self.delivery_store.enqueue(event, viewers)
        publisher = Mock()
        publisher.repository.build_internal_snapshot.return_value = {"cycle": {"cycle_id": "cycle-1"}}
        publisher._viewer_username.side_effect = lambda viewer: viewer["viewer_id"]
        publisher.build_delta_for_viewer.side_effect = lambda _event, viewer, snapshot=None: {
            "scope": "ghostnetwork", "type": "ghost.part_contained",
            "entity_id": "public-part", "payload": {"viewer": viewer["viewer_id"]},
            "dedupe_key": "event-1", "created_at": None,
        }
        bus = Mock()
        with patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run, "GhostNetworkDeltaPublisher", return_value=publisher), \
                patch.object(run, "delta_bus", bus):
            first = run.process_ghostnetwork_delta_delivery_job("worker", batch_size=2)
            second = run.process_ghostnetwork_delta_delivery_job("worker", batch_size=2)

        self.assertFalse(first["complete"])
        self.assertTrue(second["complete"])
        self.assertEqual(bus.record_change.call_count, 3)
        self.assertEqual(publisher.repository.build_internal_snapshot.call_count, 1)
        diagnostics = self.delivery_store.diagnostics()
        self.assertEqual(diagnostics["counts"], {"complete": 1})
        self.assertEqual(diagnostics["published"], 3)

    def test_delta_delivery_retry_does_not_advance_cursor(self):
        event = {
            "event_id": "event-retry", "cycle_id": "cycle-1",
            "event_type": "ghost.part_contained",
        }
        self.delivery_store.enqueue(event, [{"viewer_id": "alice"}])
        publisher = Mock()
        publisher.repository.build_internal_snapshot.return_value = {}
        publisher._viewer_username.return_value = "alice"
        publisher.build_delta_for_viewer.return_value = {
            "scope": "ghostnetwork", "type": "ghost.part_contained",
            "entity_id": "public-part", "payload": {}, "dedupe_key": "event-retry",
        }
        with patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run, "GhostNetworkDeltaPublisher", return_value=publisher), \
                patch.object(run.delta_bus, "record_change", side_effect=RuntimeError("busy")):
            failed = run.process_ghostnetwork_delta_delivery_job("worker")

        self.assertFalse(failed["ok"])
        diagnostics = self.delivery_store.diagnostics()
        self.assertEqual(diagnostics["counts"], {"pending": 1})
        self.assertEqual(diagnostics["published"], 0)

    def test_internal_event_receipt_completes_without_snapshot_or_client_delta(self):
        event = {
            "event_id": "event-internal", "cycle_id": "cycle-1",
            "event_type": "ghost.internal_audit", "audience_scope": "internal",
        }
        self.delivery_store.enqueue(event, [])
        with patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run, "GhostNetworkDeltaPublisher") as publisher, \
                patch.object(run.delta_bus, "record_change") as record:
            result = run.process_ghostnetwork_delta_delivery_job("worker")
        self.assertTrue(result["complete"])
        publisher.assert_not_called()
        record.assert_not_called()


if __name__ == "__main__":
    unittest.main()
