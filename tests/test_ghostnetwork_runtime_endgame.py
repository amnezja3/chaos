import copy
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import run
from database import GhostNetworkDeltaDeliveryJobStore, db_connect, dumps_json
from ghostnetwork import (
    GhostCycleService,
    GhostDropPolicy,
    GhostNetworkRepository,
    GhostNetworkService,
)
from ghostnetwork.narrative import GHOST_EVENT_POLICY


class GhostNetworkRuntimeEndgameTest(unittest.TestCase):
    @staticmethod
    def prepare_stabilizing_cycle(db_path, prefix="rollover"):
        repo = GhostNetworkRepository(db_path=db_path)
        cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
        service = GhostNetworkService(repository=repo)
        now = repo.now()
        for index, part in enumerate(repo.list_parts(cycle["cycle_id"])):
            lat = 48.0 + index * 0.001
            lng = 17.0 + index * 0.001
            repo.update_part(
                part["part_id"], status="active", target_id=f"{prefix}-{index}",
                latitude=lat, longitude=lng, discovered_by=f"{prefix}-player-{index}",
                discovered_clan=part["clan_code"], discovered_at=now,
                anchor_snapshot_json=dumps_json({"target_id": f"{prefix}-{index}", "lat": lat, "lng": lng}),
                territory_id=f"{prefix}-territory-{index}",
                territory_owner_id=f"{prefix}-player-{index}",
                territory_clan=part["clan_code"], territory_state_version=index + 1,
                activated_at=now, last_activated_at=now, conflict_state="none",
            )
        locked = service.closure.attempt_cycle_lock(cycle["cycle_id"], f"{prefix}-last")
        if not locked.get("ok"):
            raise AssertionError(locked)
        sent = service.transmission.start_transmission(cycle["cycle_id"])
        if not sent.get("ok"):
            raise AssertionError(sent)
        reconciled = run.advance_ghostnetwork_endgame_once(service=service)
        if not reconciled.get("ok"):
            raise AssertionError(reconciled)
        return repo, service, cycle, sent

    def test_runtime_finalizer_closes_and_transmits_once_without_next_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-endgame.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            service = GhostNetworkService(repository=repo)
            now = repo.now()
            for index, part in enumerate(repo.list_parts(cycle["cycle_id"])):
                lat = 52.0 + index * 0.001
                lng = 21.0 + index * 0.001
                repo.update_part(
                    part["part_id"], status="active",
                    target_id=f"runtime-endgame-{index}",
                    latitude=lat, longitude=lng,
                    discovered_by=f"player-{index}", discovered_clan=part["clan_code"],
                    discovered_at=now,
                    anchor_snapshot_json=dumps_json({"target_id": f"runtime-endgame-{index}", "lat": lat, "lng": lng}),
                    territory_id=f"territory-{index}", territory_owner_id=f"player-{index}",
                    territory_clan=part["clan_code"], territory_state_version=index + 1,
                    activated_at=now, last_activated_at=now, conflict_state="none",
                )

            first = run.maybe_finalize_ghostnetwork_cycle(service)
            self.assertTrue(first["ok"], first)
            self.assertEqual(len(repo.list_signals_for_cycle(cycle["cycle_id"])), 1, first)
            self.assertEqual(repo.get_cycle(cycle["cycle_id"])["status"], "stabilizing")
            events = repo.list_events(cycle["cycle_id"], limit=1000)
            for event_type in (
                "ghost.cycle_locked", "ghost.signal_sent",
                "ghost.version_changed", "ghost.stabilization_started",
            ):
                event = next(item for item in events if item["event_type"] == event_type)
                tasks = repo.list_narrative_outbox(
                    source_scope="ghostnetwork", source_event_id=event["event_id"], limit=10,
                )
                self.assertEqual(
                    {task["target_medium"] for task in tasks},
                    set(GHOST_EVENT_POLICY[event_type]["target_media"]),
                    event_type,
                )
                self.assertTrue(any(task["audience_scope"] == "public" for task in tasks))

            second = run.maybe_finalize_ghostnetwork_cycle(service)
            self.assertEqual(second["status"], "not_ready")
            self.assertEqual(len(repo.list_signals_for_cycle(cycle["cycle_id"])), 1)
            self.assertEqual(len(repo.list_cycles()), 1)

    def test_periodic_endgame_tick_resumes_a_committed_lock_without_another_territory_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-endgame-resume.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            service = GhostNetworkService(repository=repo)
            now = repo.now()
            for index, part in enumerate(repo.list_parts(cycle["cycle_id"])):
                lat = 52.0 + index * 0.001
                lng = 21.0 + index * 0.001
                repo.update_part(
                    part["part_id"], status="active",
                    target_id=f"runtime-resume-{index}",
                    latitude=lat, longitude=lng,
                    discovered_by=f"player-{index}", discovered_clan=part["clan_code"],
                    discovered_at=now,
                    anchor_snapshot_json=dumps_json({"target_id": f"runtime-resume-{index}", "lat": lat, "lng": lng}),
                    territory_id=f"territory-{index}", territory_owner_id=f"player-{index}",
                    territory_clan=part["clan_code"], territory_state_version=index + 1,
                    activated_at=now, last_activated_at=now, conflict_state="none",
                )

            locked = service.attempt_cycle_lock(
                cycle["cycle_id"], trigger_event_id="event-last-part",
            )
            self.assertTrue(locked["ok"], locked)
            self.assertEqual(repo.get_cycle(cycle["cycle_id"])["status"], "transmitting")
            self.assertEqual(repo.list_signals_for_cycle(cycle["cycle_id"]), [])

            # A fresh service instance models PM2 14 restarting after the lock
            # transaction committed but before the signal transaction began.
            service = GhostNetworkService(repository=GhostNetworkRepository(db_path=db_path))
            recovered = run.advance_ghostnetwork_endgame_once(service=service)
            self.assertTrue(recovered["ok"], recovered)
            self.assertEqual(recovered["status"], "resumed")
            self.assertTrue(recovered["recovered"])
            self.assertEqual(repo.get_cycle(cycle["cycle_id"])["status"], "stabilizing")
            self.assertEqual(len(repo.list_signals_for_cycle(cycle["cycle_id"])), 1)

            waiting = run.advance_ghostnetwork_endgame_once(service=service)
            self.assertEqual(waiting["status"], "stabilizing")
            self.assertEqual(len(repo.list_signals_for_cycle(cycle["cycle_id"])), 1)

    def test_periodic_endgame_tick_fails_closed_for_invalid_transmitting_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-endgame-invalid-lock.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            service = GhostNetworkService(repository=repo)
            repo.update_cycle(cycle["cycle_id"], status="transmitting")

            blocked = run.advance_ghostnetwork_endgame_once(service=service)

            self.assertFalse(blocked["ok"], blocked)
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["phase"], "transmitting")
            self.assertIn("lock_snapshot_missing", blocked["reasons"])
            self.assertEqual(repo.list_signals_for_cycle(cycle["cycle_id"]), [])

    def test_stabilizing_tick_repairs_postcommit_archive_and_narrative_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-endgame-postcommit.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            service = GhostNetworkService(repository=repo)
            now = repo.now()
            for index, part in enumerate(repo.list_parts(cycle["cycle_id"])):
                lat = 52.0 + index * 0.001
                lng = 21.0 + index * 0.001
                repo.update_part(
                    part["part_id"], status="active",
                    target_id=f"runtime-postcommit-{index}", latitude=lat, longitude=lng,
                    discovered_by=f"player-{index}", discovered_clan=part["clan_code"],
                    discovered_at=now,
                    anchor_snapshot_json=dumps_json({"target_id": f"runtime-postcommit-{index}", "lat": lat, "lng": lng}),
                    territory_id=f"territory-{index}", territory_owner_id=f"player-{index}",
                    territory_clan=part["clan_code"], territory_state_version=index + 1,
                    activated_at=now, last_activated_at=now, conflict_state="none",
                )
            locked = service.closure.attempt_cycle_lock(
                cycle["cycle_id"], trigger_event_id="event-last-part",
            )
            self.assertTrue(locked["ok"], locked)
            raw = service.transmission.start_transmission(cycle["cycle_id"])
            self.assertTrue(raw["ok"], raw)
            self.assertEqual(repo.list_achievements(cycle_id=cycle["cycle_id"], limit=2000), [])
            signal_event = next(
                event for event in repo.list_events(cycle["cycle_id"], limit=1000)
                if event["event_type"] == "ghost.signal_sent"
            )
            self.assertEqual(
                repo.list_narrative_outbox(source_event_id=signal_event["event_id"], limit=20),
                [],
            )

            repaired = run.advance_ghostnetwork_endgame_once(service=service)
            self.assertTrue(repaired["ok"], repaired)
            self.assertEqual(repaired["status"], "stabilizing")
            self.assertFalse(repaired["postcommit"]["idempotent"])
            self.assertFalse(repaired["delta_delivery"]["idempotent"])
            self.assertTrue(repo.list_achievements(cycle_id=cycle["cycle_id"], limit=2000))
            self.assertTrue(
                repo.list_narrative_outbox(source_event_id=signal_event["event_id"], limit=20)
            )

            repeated = run.advance_ghostnetwork_endgame_once(service=service)
            self.assertTrue(repeated["postcommit"]["idempotent"])
            self.assertTrue(repeated["delta_delivery"]["idempotent"])
            markers = [
                event for event in repo.list_events(cycle["cycle_id"], limit=1000)
                if event["event_type"] == "ghost.endgame_postcommit_reconciled"
            ]
            self.assertEqual(len(markers), 1)
            delta_markers = [
                event for event in repo.list_events(cycle["cycle_id"], limit=1000)
                if event["event_type"] == "ghost.endgame_delta_reconciled"
            ]
            self.assertEqual(len(delta_markers), 1)
            delivery = GhostNetworkDeltaDeliveryJobStore(db_path=db_path)
            self.assertTrue(delivery.has_event(signal_event["event_id"]))

    def test_stabilizing_tick_retries_when_postcommit_narrative_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-endgame-postcommit-retry.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            service = GhostNetworkService(repository=repo)
            now = repo.now()
            for index, part in enumerate(repo.list_parts(cycle["cycle_id"])):
                lat = 50.0 + index * 0.001
                lng = 19.0 + index * 0.001
                repo.update_part(
                    part["part_id"], status="active", target_id=f"retry-{index}",
                    latitude=lat, longitude=lng, discovered_by=f"retry-player-{index}",
                    discovered_clan=part["clan_code"], discovered_at=now,
                    anchor_snapshot_json=dumps_json({"target_id": f"retry-{index}", "lat": lat, "lng": lng}),
                    territory_id=f"retry-territory-{index}", territory_owner_id=f"retry-player-{index}",
                    territory_clan=part["clan_code"], territory_state_version=index + 1,
                    activated_at=now, last_activated_at=now, conflict_state="none",
                )
            service.closure.attempt_cycle_lock(cycle["cycle_id"], "retry-last-part")
            service.transmission.start_transmission(cycle["cycle_id"])

            with patch.object(
                service.narrative, "publish_persisted_events", side_effect=RuntimeError("offline")
            ):
                failed = run.advance_ghostnetwork_endgame_once(service=service)
            self.assertFalse(failed["ok"], failed)
            self.assertEqual(failed["status"], "postcommit_retry")
            self.assertIn("narrative_reconciliation_failed", failed["reasons"])
            self.assertIsNone(repo.get_event_by_dedupe_key(
                f"ghost:endgame_postcommit_reconciled:{cycle['cycle_id']}:archive_narrative:v1"
            ))

            recovered = run.advance_ghostnetwork_endgame_once(service=service)
            self.assertTrue(recovered["ok"], recovered)
            self.assertEqual(recovered["status"], "stabilizing")

    def test_two_endgame_workers_converge_on_one_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-endgame-concurrent.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            service = GhostNetworkService(repository=repo)
            now = repo.now()
            for index, part in enumerate(repo.list_parts(cycle["cycle_id"])):
                lat = 51.0 + index * 0.001
                lng = 20.0 + index * 0.001
                repo.update_part(
                    part["part_id"], status="active", target_id=f"concurrent-{index}",
                    latitude=lat, longitude=lng, discovered_by=f"concurrent-player-{index}",
                    discovered_clan=part["clan_code"], discovered_at=now,
                    anchor_snapshot_json=dumps_json({"target_id": f"concurrent-{index}", "lat": lat, "lng": lng}),
                    territory_id=f"concurrent-territory-{index}",
                    territory_owner_id=f"concurrent-player-{index}",
                    territory_clan=part["clan_code"], territory_state_version=index + 1,
                    activated_at=now, last_activated_at=now, conflict_state="none",
                )
            locked = service.closure.attempt_cycle_lock(cycle["cycle_id"], "concurrent-last")
            self.assertTrue(locked["ok"], locked)

            def advance(_index):
                worker_service = GhostNetworkService(
                    repository=GhostNetworkRepository(db_path=db_path)
                )
                return run.advance_ghostnetwork_endgame_once(service=worker_service)

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(advance, range(2)))

            self.assertTrue(all(item["ok"] for item in results), results)
            self.assertTrue(
                all(item["status"] in {"resumed", "stabilizing"} for item in results),
                results,
            )
            signals = repo.list_signals_for_cycle(cycle["cycle_id"])
            self.assertEqual(len(signals), 1)
            self.assertEqual(len(repo.list_pending_rewards(cycle_id=cycle["cycle_id"], limit=100)), 21)
            self.assertEqual(len(repo.list_historical_nodes_for_signal(signals[0]["signal_id"])), 20)

    def test_due_stabilization_rolls_to_exactly_one_clean_active_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-rollover.sqlite3")
            repo, service, old_cycle, sent = self.prepare_stabilizing_cycle(db_path)
            drop_service = GhostNetworkService(
                repository=repo,
                drop_policy=GhostDropPolicy(enabled=True, chance=1.0),
            )
            before_deadline = drop_service.on_target_aimed(
                {"player_id": "rollover-player", "clan_code": "virex"},
                {
                    "target_id": "map:1:1:before-rollover",
                    "lat": 1.0,
                    "lng": 1.0,
                    "source_type": "shop",
                    "target_mode": "standard",
                },
            )
            self.assertEqual(before_deadline["status"], "cycle_not_active")
            repo.update_cycle(old_cycle["cycle_id"], stabilization_until="2000-01-01T00:00:00+00:00")

            result = run.advance_ghostnetwork_endgame_once(service=service)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["status"], "rolled_over")
            self.assertFalse(result["idempotent"])
            self.assertTrue(result["rollover_postcommit"]["ok"], result)
            self.assertEqual(repo.get_cycle(old_cycle["cycle_id"])["status"], "closed")
            old_parts = repo.list_parts(old_cycle["cycle_id"])
            self.assertTrue(all(part["status"] == "consumed" for part in old_parts))
            self.assertTrue(all(part["territory_id"] for part in old_parts))
            next_cycle = repo.get_active_cycle()
            self.assertEqual(next_cycle["signal_number"], old_cycle["signal_number"] + 1)
            self.assertEqual(next_cycle["ghostsystem_version"], sent["signal"]["next_version"])
            parts = repo.list_parts(next_cycle["cycle_id"])
            self.assertEqual(len(parts), 20)
            self.assertTrue(all(part["status"] == "pooled" for part in parts))
            self.assertTrue(all(not part["target_id"] and not part["territory_id"] for part in parts))
            self.assertEqual(
                sorted({sum(1 for part in parts if part["clan_code"] == clan) for clan in {part["clan_code"] for part in parts}}),
                [5],
            )
            self.assertEqual(len(repo.list_connections(next_cycle["cycle_id"])), 20)
            self.assertEqual(repo.list_active_reservations(old_cycle["cycle_id"]), [])
            self.assertEqual(repo.list_active_reservations(next_cycle["cycle_id"]), [])
            self.assertEqual(len(repo.list_historical_nodes_for_signal(sent["signal"]["signal_id"])), 20)
            delivery = GhostNetworkDeltaDeliveryJobStore(db_path=db_path)
            activated = next(
                event for event in repo.list_events(next_cycle["cycle_id"], limit=100)
                if event["event_type"] == "ghost.cycle_activated"
            )
            self.assertTrue(delivery.has_event(activated["event_id"]))
            self.assertTrue(repo.list_narrative_outbox(source_event_id=activated["event_id"], limit=20))

            after_rollover = drop_service.on_target_aimed(
                {"player_id": "rollover-player", "clan_code": "virex"},
                {
                    "target_id": "map:2:2:after-rollover",
                    "lat": 2.0,
                    "lng": 2.0,
                    "source_type": "shop",
                    "target_mode": "standard",
                },
            )
            self.assertEqual(after_rollover["status"], "reserved")
            reservation = repo.get_reservation(after_rollover["reservation_id"])
            self.assertEqual(reservation["cycle_id"], next_cycle["cycle_id"])

            repeated = run.advance_ghostnetwork_endgame_once(service=service)
            self.assertEqual(repeated["status"], "not_ready")
            self.assertEqual(len(repo.list_cycles()), 2)

    def test_rollover_postcommit_recovers_after_fresh_service_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-rollover-recovery.sqlite3")
            repo, service, old_cycle, _sent = self.prepare_stabilizing_cycle(db_path, "recovery")
            repo.update_cycle(old_cycle["cycle_id"], stabilization_until="2000-01-01T00:00:00+00:00")
            mechanical = service.rollover_stabilized_cycle(old_cycle["cycle_id"])
            self.assertTrue(mechanical["ok"], mechanical)
            next_cycle = mechanical["next_cycle"]
            marker_key = (
                f"ghost:rollover_postcommit_reconciled:{old_cycle['cycle_id']}:"
                f"{next_cycle['cycle_id']}:v1"
            )
            self.assertIsNone(repo.get_event_by_dedupe_key(marker_key))

            fresh = GhostNetworkService(repository=GhostNetworkRepository(db_path=db_path))
            recovered = run.advance_ghostnetwork_endgame_once(service=fresh)

            self.assertTrue(recovered["ok"], recovered)
            self.assertEqual(recovered["status"], "not_ready")
            self.assertTrue(recovered["rollover_postcommit"]["ok"], recovered)
            self.assertIsNotNone(repo.get_event_by_dedupe_key(marker_key))
            self.assertEqual(len(repo.list_cycles()), 2)

    def test_rollover_recovers_after_close_before_successor_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-rollover-close-gap.sqlite3")
            repo, service, old_cycle, _sent = self.prepare_stabilizing_cycle(
                db_path, "close-gap"
            )
            repo.update_cycle(
                old_cycle["cycle_id"],
                stabilization_until="2000-01-01T00:00:00+00:00",
            )

            # Simulate a legacy/crash window after the old close commit but
            # before successor creation. The next bounded worker tick must
            # complete the transition without reopening the old cycle.
            service.cycles.close_cycle(old_cycle["cycle_id"])
            self.assertIsNone(repo.get_active_cycle())
            self.assertEqual(len(repo.list_cycles()), 1)

            fresh = GhostNetworkService(repository=GhostNetworkRepository(db_path=db_path))
            recovered = run.advance_ghostnetwork_endgame_once(service=fresh)

            self.assertTrue(recovered["ok"], recovered)
            self.assertEqual(recovered["status"], "rolled_over")
            self.assertTrue(recovered["recovered"])
            self.assertEqual(len(repo.list_cycles()), 2)
            self.assertEqual(repo.get_cycle(old_cycle["cycle_id"])["status"], "closed")
            self.assertEqual(repo.get_active_cycle()["signal_number"], 2)

    def test_rollover_mechanics_survive_narrative_postcommit_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-rollover-narrative-offline.sqlite3")
            repo, service, old_cycle, _sent = self.prepare_stabilizing_cycle(
                db_path, "narrative-offline"
            )
            repo.update_cycle(
                old_cycle["cycle_id"],
                stabilization_until="2000-01-01T00:00:00+00:00",
            )

            with patch.object(
                service.narrative,
                "publish_persisted_events",
                side_effect=RuntimeError("ollama route offline"),
            ):
                rolled = run.advance_ghostnetwork_endgame_once(service=service)

            self.assertTrue(rolled["ok"], rolled)
            self.assertEqual(rolled["status"], "rolled_over")
            self.assertTrue(rolled["postcommit_pending"])
            self.assertEqual(repo.get_cycle(old_cycle["cycle_id"])["status"], "closed")
            self.assertEqual(repo.get_active_cycle()["signal_number"], 2)

            fresh = GhostNetworkService(repository=GhostNetworkRepository(db_path=db_path))
            recovered = run.advance_ghostnetwork_endgame_once(service=fresh)
            self.assertTrue(recovered["ok"], recovered)
            self.assertTrue(recovered["rollover_postcommit"]["ok"], recovered)
            self.assertEqual(len(repo.list_cycles()), 2)

    def test_rollover_fails_closed_when_final_reward_row_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-rollover-settlement.sqlite3")
            repo, service, old_cycle, sent = self.prepare_stabilizing_cycle(db_path, "blocked")
            reward = repo.list_rewards(signal_id=sent["signal"]["signal_id"], limit=1)[0]
            with db_connect(db_path) as conn:
                conn.execute("DELETE FROM ghost_reward_ledger WHERE reward_id = ?", (reward["reward_id"],))
            repo.update_cycle(old_cycle["cycle_id"], stabilization_until="2000-01-01T00:00:00+00:00")

            blocked = run.advance_ghostnetwork_endgame_once(service=service)

            self.assertFalse(blocked["ok"], blocked)
            self.assertEqual(blocked["status"], "settlement_blocked")
            self.assertIn("final_rewards_incomplete", blocked["reasons"])
            self.assertEqual(repo.get_cycle(old_cycle["cycle_id"])["status"], "stabilizing")
            self.assertEqual(len(repo.list_cycles()), 1)

    def test_two_due_rollover_workers_create_one_successor(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-rollover-concurrent.sqlite3")
            repo, _service, old_cycle, _sent = self.prepare_stabilizing_cycle(db_path, "race")
            repo.update_cycle(old_cycle["cycle_id"], stabilization_until="2000-01-01T00:00:00+00:00")

            def advance(_index):
                return run.advance_ghostnetwork_endgame_once(
                    service=GhostNetworkService(
                        repository=GhostNetworkRepository(db_path=db_path)
                    )
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(advance, range(2)))

            self.assertTrue(all(item.get("ok") for item in results), results)
            self.assertEqual(len(repo.list_cycles()), 2)
            self.assertEqual(repo.get_cycle(old_cycle["cycle_id"])["status"], "closed")
            self.assertEqual(repo.get_active_cycle()["signal_number"], 2)

    def test_pending_reward_projection_recovers_after_profile_save_before_finalize(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-reward-projector.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            service = GhostNetworkService(repository=repo)
            reward = repo.insert_reward({
                "reward_key": "ghost-signal:test:node:one:reward-player",
                "cycle_id": cycle["cycle_id"],
                "signal_id": "ghost-signal-test",
                "player_id": "reward-player",
                "clan_code": "sentinel_order",
                "reward_type": "transmission_node_held",
                "final_rsp": 25,
                "status": "pending",
            })
            stored_profile = {
                "username": "reward-player",
                "respect": 100,
                "ghostnetwork_stats": {},
                "ghostnetwork_reward_history": [],
            }

            def load_profile(_player_id):
                return {"profile": copy.deepcopy(stored_profile), "profile_revision": 1}

            def save_then_crash(_record, profile, _source):
                stored_profile.clear()
                stored_profile.update(copy.deepcopy(profile))
                raise RuntimeError("crash_after_profile_save")

            with self.assertRaisesRegex(RuntimeError, "crash_after_profile_save"):
                run.process_ghostnetwork_pending_reward_projection(
                    service=service,
                    profile_loader=load_profile,
                    profile_saver=save_then_crash,
                    failure_backoff_seconds=0,
                )
            self.assertEqual(repo.get_reward(reward["reward_id"])["status"], "pending")
            self.assertEqual(stored_profile["respect"], 125)
            self.assertEqual(len(stored_profile["ghostnetwork_reward_history"]), 1)

            recovered = run.process_ghostnetwork_pending_reward_projection(
                service=service,
                profile_loader=load_profile,
                profile_saver=lambda *_args: self.fail("receipt recovery must not save twice"),
                failure_backoff_seconds=0,
            )
            self.assertTrue(recovered["ok"], recovered)
            self.assertEqual(recovered["status"], "applied")
            self.assertFalse(recovered["profile_changed"])
            self.assertEqual(repo.get_reward(reward["reward_id"])["status"], "applied")
            self.assertEqual(stored_profile["respect"], 125)

            empty = run.process_ghostnetwork_pending_reward_projection(
                service=service,
                profile_loader=load_profile,
                profile_saver=lambda *_args: None,
            )
            self.assertEqual(empty["status"], "empty")

    def test_reward_projection_claim_backoff_and_expired_lease_recovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-reward-claim.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            reward = repo.insert_reward({
                "reward_key": "ghost-signal:test:node:claim:player",
                "cycle_id": cycle["cycle_id"],
                "player_id": "claim-player",
                "reward_type": "transmission_node_held",
                "final_rsp": 10,
                "status": "pending",
            })
            claimed = repo.claim_pending_reward_projection(
                "worker-a", lease_seconds=10, now="2030-01-01T00:00:00+00:00",
            )
            self.assertEqual(claimed["reward_id"], reward["reward_id"])
            self.assertEqual(claimed["projection_attempt_count"], 1)
            self.assertIsNone(repo.claim_pending_reward_projection(
                "worker-b", lease_seconds=10, now="2030-01-01T00:00:05+00:00",
            ))
            diagnostics = repo.reward_projection_diagnostics(
                now="2030-01-01T00:00:05+00:00"
            )
            self.assertEqual(diagnostics["processing"], 1)
            self.assertEqual(diagnostics["ready_now"], 0)

            self.assertTrue(repo.retry_reward_projection(
                reward["reward_id"], "worker-a", claimed["projection_lease_until"],
                error="database is locked", now="2030-01-01T00:00:05+00:00",
                backoff_seconds=10,
            ))
            waiting = repo.reward_projection_diagnostics(
                now="2030-01-01T00:00:14+00:00"
            )
            self.assertEqual(waiting["retry_wait"], 1)
            self.assertEqual(waiting["pending_with_error"], 1)
            self.assertEqual(waiting["statuses"]["pending"], 1)
            self.assertIsNone(repo.claim_pending_reward_projection(
                "worker-b", lease_seconds=10, now="2030-01-01T00:00:14+00:00",
            ))
            reclaimed = repo.claim_pending_reward_projection(
                "worker-b", lease_seconds=10, now="2030-01-01T00:00:15+00:00",
            )
            self.assertEqual(reclaimed["projection_attempt_count"], 2)
            expired = repo.reward_projection_diagnostics(
                now="2030-01-01T00:00:26+00:00"
            )
            self.assertEqual(expired["expired_claims"], 1)
            takeover = repo.claim_pending_reward_projection(
                "worker-c", lease_seconds=10, now="2030-01-01T00:00:26+00:00",
            )
            self.assertEqual(takeover["projection_attempt_count"], 3)

    def test_reward_projection_loader_failure_releases_claim_with_backoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, "ghost-reward-loader-failure.sqlite3")
            repo = GhostNetworkRepository(db_path=db_path)
            cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
            service = GhostNetworkService(repository=repo)
            reward = repo.insert_reward({
                "reward_key": "ghost-signal:test:loader:player",
                "cycle_id": cycle["cycle_id"], "player_id": "loader-player",
                "reward_type": "transmission_node_held", "final_rsp": 10,
                "status": "pending",
            })
            with self.assertRaisesRegex(RuntimeError, "profile temporarily unavailable"):
                run.process_ghostnetwork_pending_reward_projection(
                    service=service,
                    profile_loader=lambda _player: (_ for _ in ()).throw(
                        RuntimeError("profile temporarily unavailable")
                    ),
                    profile_saver=lambda *_args: None,
                    worker_id="loader-worker",
                    failure_backoff_seconds=30,
                )
            current = repo.get_reward(reward["reward_id"])
            self.assertEqual(current["status"], "pending")
            self.assertEqual(current["projection_claimed_by"], "")
            self.assertEqual(current["failure_reason"], "profile temporarily unavailable")
            self.assertTrue(current["projection_next_attempt_at"])


if __name__ == "__main__":
    unittest.main()
