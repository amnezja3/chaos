import os
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timedelta

from database import (dumps_json, UserStore, reset_hot_path_metrics,
                      get_hot_path_metrics, restore_hot_path_metrics)
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostTransmissionService
from ghostnetwork.closure import GhostNetworkClosureService
from ghostnetwork.errors import InvalidStateTransition
from ghostnetwork.narrative import GhostNarrativePublisher


class GhostNetworkTransmissionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle_service = GhostCycleService(repository=self.repo)
        self.closure = GhostNetworkClosureService(repository=self.repo)
        self.transmission = GhostTransmissionService(repository=self.repo, closure_service=self.closure)

    def tearDown(self):
        self.tmp.cleanup()

    def create_locked_cycle(self):
        cycle = self.cycle_service.create_cycle()["cycle"]
        now = self.repo.now()
        for index, part in enumerate(self.repo.list_parts(cycle["cycle_id"])):
            lat = 52.20 + index * 0.001
            lng = 21.00 + index * 0.001
            self.repo.update_part(
                part["part_id"],
                status="active",
                target_id=f"POI-{part['part_code']}",
                latitude=lat,
                longitude=lng,
                discovered_by=f"operator-{index}",
                discovered_clan=part["clan_code"],
                discovered_at=now,
                anchor_snapshot_json=dumps_json(
                    {
                        "target_id": f"POI-{part['part_code']}",
                        "lat": lat,
                        "lng": lng,
                        "label": part["part_code"],
                    }
                ),
                territory_id=f"territory-{part['part_code']}",
                territory_owner_id=f"operator-{index}",
                territory_clan=part["clan_code"],
                territory_state_version=2000 + index,
                activated_at=now,
                last_activated_at=now,
                conflict_state="none",
                conflict_id="",
            )
        closing_part = self.repo.list_parts(cycle["cycle_id"])[-1]
        closing_event = self.repo.append_event(
            "ghost.part_activated",
            cycle_id=cycle["cycle_id"],
            part_id=closing_part["part_id"],
            entity_id=closing_part["part_id"],
            player_id="closing-operator",
            clan_code=closing_part["clan_code"],
            territory_id=closing_part["territory_id"],
            dedupe_key=f"test:closing:{cycle['cycle_id']}",
            event_id=f"event-closing-{cycle['cycle_id']}",
            payload={"player_id": "closing-operator"},
        )
        lock = self.closure.attempt_cycle_lock(cycle["cycle_id"], closing_event["event_id"])
        self.assertTrue(lock["locked"], lock)
        return self.repo.get_cycle(cycle["cycle_id"]), lock

    def test_locked_cycle_transmits_once_and_starts_restart_window(self):
        cycle, lock = self.create_locked_cycle()
        result = self.transmission.start_transmission(cycle["cycle_id"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "sent")
        signal_event = next(
            event for event in self.repo.list_events(cycle["cycle_id"], limit=1000)
            if event["event_type"] == "ghost.signal_sent"
        )
        self.assertEqual(signal_event["audience_scope"], "public")

        signal = result["signal"]
        self.assertEqual(signal["cycle_id"], cycle["cycle_id"])
        self.assertEqual(signal["signal_number"], cycle["signal_number"])
        self.assertEqual(signal["status"], "sent")
        self.assertEqual(signal["outcome"], "pending")
        self.assertEqual(signal["lock_snapshot_id"], lock["snapshot"]["lock_snapshot_id"])
        self.assertTrue(signal["signal_checksum"])
        self.assertEqual(len(signal["payload"]["machine_progress"]), 4)
        self.assertTrue(all(
            machine["machine_online"] and machine["parts_active"] == 5
            for machine in signal["payload"]["machine_progress"]
        ))
        self.assertEqual(signal["payload"]["machines"], signal["payload"]["machine_progress"])

        updated_cycle = self.repo.get_cycle(cycle["cycle_id"])
        self.assertEqual(updated_cycle["status"], "stabilizing")
        self.assertTrue(updated_cycle["restart_required"])
        self.assertEqual(updated_cycle["restart_signal_id"], signal["signal_id"])
        self.assertEqual(updated_cycle["ghostsystem_version"], cycle["ghostsystem_version"])
        self.assertTrue(updated_cycle["upgrade_pending"])
        self.assertEqual(updated_cycle["next_version"], "1.0.2")
        self.assertIsNotNone(self.repo.get_signal_show_for_signal(signal["signal_id"]))
        self.assertTrue(updated_cycle["stabilization_until"])

        parts = self.repo.list_parts(cycle["cycle_id"])
        self.assertEqual(len(parts), 20)
        self.assertTrue(all(part["status"] == "consumed" for part in parts))
        self.assertTrue(all(part["consumed_signal_id"] == signal["signal_id"] for part in parts))
        self.assertEqual(self.repo.list_connections(cycle["cycle_id"]), [])
        self.assertEqual(len(self.repo.list_historical_nodes_for_signal(signal["signal_id"])), 20)

        rewards = [reward for reward in self.repo.list_pending_rewards(cycle_id=cycle["cycle_id"], limit=100)]
        self.assertEqual(len(rewards), 21)
        self.assertEqual(len(self.repo.list_signals_for_cycle(cycle["cycle_id"])), 1)

    def test_transmission_retry_is_idempotent(self):
        cycle, _lock = self.create_locked_cycle()
        first = self.transmission.start_transmission(cycle["cycle_id"])
        first_show = self.repo.get_signal_show_for_signal(first["signal"]["signal_id"])
        second = self.transmission.start_transmission(cycle["cycle_id"])
        second_show = self.repo.get_signal_show_for_signal(second["signal"]["signal_id"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["signal"]["signal_id"], second["signal"]["signal_id"])
        self.assertEqual(len(self.repo.list_signals_for_cycle(cycle["cycle_id"])), 1)
        self.assertEqual(len(self.repo.list_pending_rewards(cycle_id=cycle["cycle_id"], limit=100)), 21)
        self.assertEqual(len(self.repo.list_historical_nodes_for_signal(first["signal"]["signal_id"])), 20)
        self.assertEqual(self.repo.get_cycle(cycle["cycle_id"])["ghostsystem_version"], cycle["ghostsystem_version"])
        self.assertEqual(first_show["show_id"], second_show["show_id"])
        self.assertEqual(first_show["show_started_at"], second_show["show_started_at"])

    def test_transmission_requires_valid_lock_snapshot(self):
        cycle = self.cycle_service.create_cycle()["cycle"]
        result = self.transmission.start_transmission(cycle["cycle_id"])
        self.assertFalse(result["ok"])
        self.assertIn("cycle_not_transmitting", result["reasons"])
        self.assertIn("lock_snapshot_missing", result["reasons"])
        self.assertEqual(self.repo.list_signals_for_cycle(cycle["cycle_id"]), [])

    def test_signal_uses_immutable_lock_snapshot_not_late_world_mutation(self):
        cycle, lock = self.create_locked_cycle()
        locked_owner = lock["snapshot"]["snapshot"]["parts"][0]["territory_owner_id"]
        locked_part_id = lock["snapshot"]["snapshot"]["parts"][0]["part_id"]
        self.repo.update_part(locked_part_id, territory_owner_id="late-owner")

        result = self.transmission.start_transmission(cycle["cycle_id"])
        signal_id = result["signal"]["signal_id"]
        node = [
            item
            for item in self.repo.list_historical_nodes_for_signal(signal_id)
            if item["part_id"] == locked_part_id
        ][0]
        self.assertEqual(node["owner_id"], locked_owner)
        self.assertNotEqual(node["owner_id"], "late-owner")

    def test_show_is_committed_before_first_effect(self):
        cycle, lock = self.create_locked_cycle()
        observer = GhostNetworkRepository(db_path=self.db_path, ensure_schema=False)

        def interrupt_before_consumption(signal_id):
            show = observer.get_signal_show_for_cycle(cycle["cycle_id"])
            self.assertIsNotNone(show)
            self.assertEqual(show["show_started_at"], lock["snapshot"]["locked_at"])
            self.assertEqual(observer.get_signal(signal_id)["status"], "transmitting")
            self.assertEqual(observer.get_signal(signal_id)["sent_at"], "")
            self.assertIsNotNone(observer.get_event_by_dedupe_key(
                f"ghost:transmission_started:{cycle['cycle_id']}"))
            self.assertIsNone(observer.get_event_by_dedupe_key(
                f"ghost:signal_sent:{cycle['cycle_id']}"))
            raise RuntimeError("interrupted before consumption")

        with patch.object(self.transmission, "consume_signal_territories",
                          side_effect=interrupt_before_consumption):
            with self.assertRaisesRegex(RuntimeError, "interrupted before consumption"):
                self.transmission.start_transmission(cycle["cycle_id"])
        show = observer.get_signal_show_for_cycle(cycle["cycle_id"])
        observer.clock = lambda: datetime.fromisoformat(show["show_ends_at"]) + timedelta(minutes=5)
        fresh = GhostTransmissionService(repository=observer)
        result = fresh.resume_interrupted_transmission(cycle["cycle_id"])
        self.assertTrue(result["ok"])
        self.assertEqual(show, observer.get_signal_show_for_cycle(cycle["cycle_id"]))
        self.assertEqual(observer.get_signal(result["signal"]["signal_id"])["status"], "sent")
        projection = fresh.show.projection_for_cycle(cycle["cycle_id"])
        self.assertTrue(projection["show_active"])
        self.assertTrue(projection["show_time_elapsed"])

    def test_completed_retry_does_not_repeat_effects_or_change_versions(self):
        cycle, _lock = self.create_locked_cycle()
        self.transmission.start_transmission(cycle["cycle_id"])
        before = self.repo.get_cycle(cycle["cycle_id"])
        with patch.object(self.transmission, "consume_signal_territories",
                          side_effect=AssertionError("completed effects replayed")):
            result = self.transmission.resume_interrupted_transmission(cycle["cycle_id"])
        self.assertTrue(result["ok"])
        self.assertEqual(before, self.repo.get_cycle(cycle["cycle_id"]))

    def test_each_interrupted_step_recovers_from_existing_ledgers(self):
        for method in ("consume_signal_territories", "apply_transmission_rewards",
                       "consume_cycle_parts", "archive_historical_nodes",
                       "remove_connections_for_cycle",
                       "disable_superpowers", "advance_ghostsystem_version",
                       "begin_stabilization"):
            with self.subTest(method=method):
                fixture = GhostNetworkTransmissionTest()
                fixture.setUp()
                try:
                    cycle, _lock = fixture.create_locked_cycle()
                    target = fixture.repo if method == "remove_connections_for_cycle" else fixture.transmission
                    original = getattr(target, method)

                    def interrupted(*args, **kwargs):
                        original(*args, **kwargs)
                        raise RuntimeError("process interruption")

                    with patch.object(target, method, side_effect=interrupted):
                        with self.assertRaisesRegex(RuntimeError, "process interruption"):
                            fixture.transmission.start_transmission(cycle["cycle_id"])
                    repo = GhostNetworkRepository(fixture.db_path, ensure_schema=False)
                    before = repo.get_signal_show_for_cycle(cycle["cycle_id"])
                    self.assertIsNotNone(before)
                    self.assertEqual(repo.get_cycle(cycle["cycle_id"])["status"], "transmitting")
                    self.assertIsNone(repo.get_event_by_dedupe_key(
                        f"ghost:signal_sent:{cycle['cycle_id']}"))
                    pending = repo.get_signal_for_cycle(cycle["cycle_id"])
                    with patch.object(GhostNarrativePublisher, "publish_domain_event",
                                      side_effect=AssertionError("premature narrative")):
                        self.assertEqual(GhostNarrativePublisher(repo).publish_signal_transmission(
                            pending["signal_id"])["reason"], "signal_not_sent")
                    result = GhostTransmissionService(repo).resume_interrupted_transmission(cycle["cycle_id"])
                    self.assertTrue(result["ok"])
                    self.assertEqual(before, repo.get_signal_show_for_cycle(cycle["cycle_id"]))
                    self.assertEqual(len(repo.list_signals_for_cycle(cycle["cycle_id"])), 1)
                    self.assertEqual(len(repo.list_rewards(signal_id=pending["signal_id"])), 21)
                    self.assertEqual(len(repo.list_historical_nodes_for_signal(pending["signal_id"])), 20)
                    self.assertTrue(all(p["status"] == "consumed" for p in repo.list_parts(cycle["cycle_id"])))
                    self.assertEqual(repo.list_connections(cycle["cycle_id"]), [])
                    events = repo.list_events_by_types(cycle["cycle_id"], [
                        "ghost.transmission_started", "ghost.signal_show_started", "ghost.signal_sent"])
                    self.assertEqual([e["event_type"] for e in events], [
                        "ghost.transmission_started", "ghost.signal_show_started", "ghost.signal_sent"])
                finally:
                    fixture.tearDown()

    def test_failed_show_commit_leaves_no_signal_or_effects(self):
        cycle, _lock = self.create_locked_cycle()
        with patch.object(self.repo, "create_signal_show", side_effect=RuntimeError("show write failed")):
            with self.assertRaisesRegex(RuntimeError, "show write failed"):
                self.transmission.start_transmission(cycle["cycle_id"])
        self.assertIsNone(self.repo.get_signal_for_cycle(cycle["cycle_id"]))
        self.assertIsNone(self.repo.get_event_by_dedupe_key(f"ghost:signal_created:{cycle['cycle_id']}"))
        self.assertTrue(all(p["status"] == "active" for p in self.repo.list_parts(cycle["cycle_id"])))
        self.assertTrue(self.transmission.resume_interrupted_transmission(cycle["cycle_id"])["ok"])

    def test_transmission_rejects_outer_transaction_that_would_hide_show(self):
        cycle, _lock = self.create_locked_cycle()
        with self.repo.transaction():
            with self.assertRaisesRegex(InvalidStateTransition, "own commit boundary"):
                self.transmission.start_transmission(cycle["cycle_id"])
        self.assertIsNone(self.repo.get_signal_for_cycle(cycle["cycle_id"]))

    def test_two_prepared_workers_converge_without_changing_show_clock(self):
        cycle, _lock = self.create_locked_cycle()
        barrier = Barrier(2)

        def transmit(_index):
            repo = GhostNetworkRepository(self.db_path, ensure_schema=False)
            service = GhostTransmissionService(repo)
            build = service._build_signal_from_lock

            def prepare(lock):
                result = build(lock)
                barrier.wait(timeout=10)
                return result

            with patch.object(service, "_build_signal_from_lock", side_effect=prepare):
                return service.start_transmission(cycle["cycle_id"])

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(transmit, range(2)))
        self.assertTrue(all(r["ok"] for r in results), results)
        self.assertEqual(results[0]["signal"]["signal_id"], results[1]["signal"]["signal_id"])
        self.assertEqual(len(self.repo.list_rewards(cycle_id=cycle["cycle_id"])), 21)
        self.assertEqual(len(self.repo.list_events_by_types(cycle["cycle_id"], [
            "ghost.transmission_started", "ghost.signal_show_started", "ghost.signal_sent"])), 3)

    def test_transmission_and_show_ignore_small_and_35mb_profiles(self):
        # Same canonical UserStore fixture used by the suite hot-path tests.
        from tests.test_ghostnetwork_suite_snapshot import valid_profile
        from database import InstrumentedConnection
        counts = []
        for padding_size in (0, 35_000_000):
            with self.subTest(padding_size=padding_size):
                fixture = GhostNetworkTransmissionTest()
                fixture.setUp()
                try:
                    users = UserStore(fixture.db_path, seed_path=os.path.join(fixture.tmp.name, "absent.json"))
                    users.save_profile_guarded(valid_profile(padding="x" * padding_size),
                        expected_revision=0, source="test.139.transmission", allow_create=True)
                    cycle, _lock = fixture.create_locked_cycle()
                    count = [0]
                    execute = InstrumentedConnection.execute

                    def counted(conn, sql, *args, **kwargs):
                        count[0] += 1
                        self.assertNotIn("profile_json", sql.lower())
                        return execute(conn, sql, *args, **kwargs)

                    token = reset_hot_path_metrics()
                    try:
                        with patch.object(UserStore, "get_profile", side_effect=AssertionError("heavy read")), \
                             patch.object(UserStore, "get_profile_with_revision", side_effect=AssertionError("heavy read")), \
                             patch.object(UserStore, "list_profiles", side_effect=AssertionError("profile scan")), \
                             patch.object(InstrumentedConnection, "execute", new=counted):
                            result = fixture.transmission.start_transmission(cycle["cycle_id"])
                            self.assertTrue(result["ok"])
                            self.assertTrue(fixture.transmission.show.projection_for_cycle(cycle["cycle_id"])["show_active"])
                        metrics = get_hot_path_metrics()
                    finally:
                        restore_hot_path_metrics(token)
                    for key in ("profile_full_read", "profile_full_write", "profile_bytes",
                                "all_user_profile_scan", "per_recipient_profile_read"):
                        self.assertEqual(metrics[key], 0, key)
                    counts.append(count[0])
                finally:
                    fixture.tearDown()
        self.assertEqual(counts[0], counts[1])
        self.assertLess(counts[0], 2500)

    def test_real_transmission_passes_read_only_chronology(self):
        from scripts.audit_ghostnetwork_endgame import audit
        cycle, _lock = self.create_locked_cycle()
        self.transmission.start_transmission(cycle["cycle_id"])
        report = audit(cycle["cycle_id"], self.db_path, require_transmission_timeline=True)
        self.assertTrue(report["transmission_chronology"]["ok"], report["transmission_chronology"])
        self.assertFalse(report["checks"]["required_events_exactly_once"])  # ranking/rollover are later
        self.assertEqual(report["event_counts"]["ghost.transmission_started"], 1)

    def test_existing_signal_cannot_bypass_invalid_lock(self):
        cycle, lock = self.create_locked_cycle()
        self.transmission.create_signal_from_lock(lock["snapshot"])
        with patch.object(self.closure, "validate_locked_snapshot", return_value={"valid": False}):
            result = self.transmission.resume_interrupted_transmission(cycle["cycle_id"])
        self.assertFalse(result["ok"])
        self.assertIn("lock_snapshot_invalid_checksum", result["reasons"])
        self.assertIsNone(self.repo.get_signal_show_for_cycle(cycle["cycle_id"]))

    def test_legacy_interrupted_signal_keeps_original_show_clock(self):
        cycle, lock = self.create_locked_cycle()
        signal = self.transmission.create_signal_from_lock(lock["snapshot"])
        legacy = self.repo.mark_signal_sent(signal["signal_id"])
        result = self.transmission.resume_interrupted_transmission(cycle["cycle_id"])
        self.assertTrue(result["ok"])
        self.assertEqual(self.repo.get_signal_show_for_cycle(cycle["cycle_id"])["show_started_at"],
                         legacy["sent_at"])
        self.assertEqual(result["signal"]["sent_at"], legacy["sent_at"])

    def test_preparation_outside_writer_rechecks_cycle_before_commit(self):
        cycle, _lock = self.create_locked_cycle()
        build = self.transmission._build_signal_from_lock

        def changed_while_preparing(lock):
            self.assertFalse(self.repo.in_transaction)
            result = build(lock)
            self.repo.update_cycle(cycle["cycle_id"], restart_reason="concurrent-change")
            return result

        with patch.object(self.transmission, "_build_signal_from_lock", side_effect=changed_while_preparing):
            result = self.transmission.start_transmission(cycle["cycle_id"])
        self.assertFalse(result["ok"])
        self.assertEqual(result["reasons"], ["transmission_state_changed"])
        self.assertIsNone(self.repo.get_signal_for_cycle(cycle["cycle_id"]))
        self.assertTrue(self.transmission.start_transmission(cycle["cycle_id"])["ok"])

    def test_legacy_partial_version_event_is_repaired_without_rewriting_cycle(self):
        cycle, lock = self.create_locked_cycle()
        signal = self.transmission.create_signal_from_lock(lock["snapshot"])
        append = self.transmission._append_once

        def interrupted(kind, **kwargs):
            if kind == "ghost.version_changed":
                raise RuntimeError("legacy non-atomic version interruption")
            return append(kind, **kwargs)

        with patch.object(self.transmission, "_append_once", side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError, "legacy non-atomic"):
                self.transmission.advance_ghostsystem_version(signal["signal_id"])
        before = self.repo.get_cycle(cycle["cycle_id"])
        self.transmission.advance_ghostsystem_version(signal["signal_id"])
        after = self.repo.get_cycle(cycle["cycle_id"])
        self.assertEqual(before["restart_required_at"], after["restart_required_at"])
        self.assertEqual(len(self.repo.list_events_by_types(cycle["cycle_id"], [
            "ghost.version_prepared", "ghost.version_changed", "ghost.restart_required"])), 3)
        self.assertEqual(after["state_version"] - before["state_version"], 2)


if __name__ == "__main__":
    unittest.main()
