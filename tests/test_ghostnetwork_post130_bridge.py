import os
import copy
import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import run
from database import (
    GhostNetworkDeltaDeliveryJobStore,
    GhostNetworkTerritoryJobStore,
    PlayerMarkedTargetStore,
    ProfileWriteConflict, UserStore, TerritoryProgressionReceiptStore, UserIdentityProjectionStore,
)
from ghostnetwork import GhostCycleService, GhostDropPolicy, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ollama_policy import build_ollama_task_package
from ghostnetwork.llm.semantic_input import infer_scan_location
from scripts.audit_semantic_input import build_report as build_semantic_input_report


class FakeIdentityProjection:
    def __init__(self, profiles):
        self.profiles = dict(profiles)

    def get_identity(self, username):
        profile = self.profiles.get(username)
        return {"username": username, **profile} if profile is not None else None

    def get_identities(self, usernames, max_items=500):
        usernames = list(usernames)
        if len(usernames) > max_items:
            raise ValueError("identity batch exceeds bound")
        return [
            {"username": username, **self.profiles[username]}
            for username in usernames if username in self.profiles
        ]

    def list_recipient_ids(self, scope, *, clan_code=None, owner_ids=None, limit=500):
        if scope in {"owner", "owners"}:
            candidates = list(owner_ids or [])
        else:
            candidates = sorted(self.profiles)
        if scope == "clan":
            candidates = [
                username for username in candidates
                if str(
                    self.profiles.get(username, {}).get("clan_code")
                    or self.profiles.get(username, {}).get("clan")
                    or ""
                ).lower() == str(clan_code or "").lower()
            ]
        return [item for item in candidates if item in self.profiles][:limit]


class GhostNetworkPost130BridgeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghost-bridge.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        GhostCycleService(repository=self.repo).ensure_active_cycle()
        self.service = GhostNetworkService(
            repository=self.repo,
            drop_policy=GhostDropPolicy(enabled=True, chance=1.0),
        )
        from tests.test_hot_path_recovery import complete_profile
        self.users = UserStore(self.db_path, seed_path=self.db_path + '.missing')
        for name in ('alice', 'part-owner'):
            self.users.save_profile(dict(complete_profile(name), respect=100))
        self.progression = TerritoryProgressionReceiptStore(self.db_path)
        self.progression_patch = patch.object(run, 'territory_progression_receipt_store', self.progression)
        self.progression_patch.start()
        self.addCleanup(self.progression_patch.stop)
        self.identity_patch = patch.object(run, 'identity_projection_store', UserIdentityProjectionStore(self.db_path))
        self.identity_patch.start()
        self.addCleanup(self.identity_patch.stop)
        self.job_store = GhostNetworkTerritoryJobStore(db_path=self.db_path)
        self.delivery_store = GhostNetworkDeltaDeliveryJobStore(db_path=self.db_path)
        self.player = {"player_id": "alice", "username": "alice", "clan_code": "virex"}
        self.target = {
            "target_id": "map:52.1:21.1:bridge", "lat": 52.1, "lng": 21.1,
            "label": "Bridge", "source_type": "shop", "target_mode": "standard", "hackable": True,
            "location": {"city": "Warszawa", "country": "Polska", "country_code": "pl"},
        }
        self.service.on_target_aimed(self.player, self.target)
        discovered = self.service.on_target_hacked(self.player, self.target, result={"target_captured": True})
        self.assertEqual(discovered["status"], "discovered")
        self.part = self.repo.find_part_by_target(self.repo.get_active_cycle()["cycle_id"], self.target["target_id"])

    def tearDown(self):
        self.tmp.cleanup()

    def test_domain_event_collector_deduplicates_event_and_nested_payload_identity(self):
        event = {
            "event_id": "event-one",
            "event_type": "ghost.part_activated",
            "dedupe_key": "part:one:activate:transition",
            "payload": {
                "event_id": "event-one",
                "event_type": "ghost.part_activated",
                "dedupe_key": "part:one:activate:transition",
            },
        }
        collected = run.collect_ghostnetwork_domain_events({
            "part": {"_domain_event": event},
            "echo": event["payload"],
        })
        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["event_id"], "event-one")

    def test_real_capture_effect_dispatches_discovery_to_public_outbox(self):
        discovered_event = next(
            event for event in self.repo.list_events(limit=1000)
            if event.get("event_type") == "ghost.part_discovered"
            and event.get("part_id") == self.part.get("part_id")
        )
        tasks = self.repo.list_narrative_outbox(
            source_scope="ghostnetwork",
            source_event_id=discovered_event["event_id"],
            limit=10,
        )

        self.assertEqual(
            {task["target_medium"] for task in tasks},
            {"blacknet", "googleplex_news"},
        )
        public_tasks = [task for task in tasks if task["audience_scope"] == "public"]
        self.assertEqual(
            {task["target_medium"] for task in public_tasks},
            {"blacknet", "googleplex_news"},
        )
        before = {task["outbox_id"] for task in tasks}
        retry = self.service.on_target_hacked(
            self.player, self.target, result={"target_captured": True},
        )
        after = {
            task["outbox_id"] for task in self.repo.list_narrative_outbox(
                source_scope="ghostnetwork",
                source_event_id=discovered_event["event_id"],
                limit=10,
            )
        }
        self.assertEqual(retry["status"], "already_discovered")
        self.assertEqual(after, before)

    def test_part_discovered_package_contains_audience_safe_semantics_and_location(self):
        scan_context = infer_scan_location([{
            "lat": 52.1, "lon": 21.1,
            "tags": {
                "name": "Bridge", "addr:city": "Warszawa",
                "addr:country": "Polska", "addr:country_code": "pl",
            },
        }])
        marked = PlayerMarkedTargetStore.normalize_target({
            **self.target, "location": scan_context["location"],
        })
        self.assertEqual(
            run.map_target_client_snapshot(marked)["location"],
            scan_context["location"],
        )
        event = next(
            item for item in self.repo.list_events(limit=1000)
            if item.get("event_type") == "ghost.part_discovered"
            and item.get("part_id") == self.part.get("part_id")
        )
        tasks = self.repo.list_narrative_outbox(
            source_scope="ghostnetwork", source_event_id=event["event_id"], limit=10,
        )
        self.assertEqual({task["audience_scope"] for task in tasks}, {"public", "clan", "owner"})

        packages = {
            (task["audience_scope"], task["target_medium"]): build_ollama_task_package(task)
            for task in tasks
        }
        public = json.loads(packages[("public", "blacknet")]["messages"][1]["content"])
        semantic = public["semantic_facts"][0]
        self.assertIn("ujawniono wcześniej ukryty element", semantic["statement"])
        self.assertIn("Przy obiekcie Bridge", semantic["statement"])
        self.assertIn("w mieście Warszawa", semantic["statement"])
        self.assertEqual(set(semantic), {"fact_ref", "statement"})

        owner = json.loads(packages[("owner", "blacknet")]["messages"][1]["content"])
        owner_statement = owner["semantic_facts"][0]["statement"]
        self.assertIn("Przy obiekcie Bridge", owner_statement)
        self.assertRegex(owner_statement, r"GhostNetwork: .+\.$")
        self.assertEqual(set(owner["semantic_facts"][0]), {"fact_ref", "statement"})

        for package in packages.values():
            encoded = package["messages"][1]["content"]
            for hidden in (
                event["event_id"], event["cycle_id"], self.part["part_id"],
                self.target["target_id"], self.player["player_id"],
            ):
                self.assertNotIn(hidden, encoded)
            self.assertLessEqual(package["input_bytes"], 2400)
        for task in tasks:
            self.assertTrue(all(task["validation"][key] == 0 for key in (
                "profile_full_read", "profile_full_write", "profile_bytes",
                "account_scan", "all_user_profile_scan", "per_recipient_profile_read",
            )))

        audit = build_semantic_input_report(self.repo)
        self.assertTrue(audit["ok"], audit)
        self.assertEqual(audit["sample_count"], 4)
        self.assertTrue(all(
            sample["canonical_to_semantic"] for sample in audit["samples"]
        ))

    def test_capture_narrative_failure_does_not_rollback_discovery(self):
        repo = GhostNetworkRepository(db_path=self.db_path)
        service = GhostNetworkService(
            repository=repo,
            drop_policy=GhostDropPolicy(enabled=True, chance=1.0),
        )
        target = {
            "target_id": "map:53.1:22.1:fail-open",
            "lat": 53.1,
            "lng": 22.1,
            "label": "Fail Open",
            "source_type": "shop",
            "target_mode": "standard",
            "hackable": True,
        }
        player = {
            "player_id": "bob", "username": "bob", "clan_code": "echo_freedom",
        }
        aimed = service.on_target_aimed(player, target)
        with patch.object(
            service.narrative,
            "publish_persisted_events",
            side_effect=RuntimeError("fault-injected narrative failure"),
        ):
            result = service.on_target_hacked(
                player,
                target,
                result={"target_captured": True},
            )

        self.assertEqual(aimed["status"], "reserved")
        self.assertEqual(result["status"], "discovered")
        self.assertFalse(result["narrative_dispatch"]["ok"])
        self.assertEqual(
            repo.find_part_by_target(repo.get_active_cycle()["cycle_id"], target["target_id"])["status"],
            "public",
        )

    @staticmethod
    def area(owner, version=1):
        return {
            "id": "post130-area", "owner_username": owner, "status": "active",
            "updated_at": f"2026-08-19T00:00:0{version}Z",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.2, "lng": 21.0},
                {"lat": 52.2, "lng": 21.2},
                {"lat": 52.0, "lng": 21.2},
            ],
        }

    @staticmethod
    def area_at(area_id, owner, vertices, version=1):
        return {
            "id": area_id,
            "owner_username": owner,
            "status": "active",
            "updated_at": f"2026-08-25T00:00:{version:02d}Z",
            "publication_version": version,
            "vertices": copy.deepcopy(vertices),
        }

    def test_canonical_area_publication_drives_contained_active_and_release(self):
        areas = [self.area("foreign-owner", 1)]
        profiles = {
            "foreign-owner": {"username": "foreign-owner", "clan": "sentinel_order"},
            "part-owner": {"username": "part-owner", "clan": self.part["clan_code"]},
        }
        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run, "ghostnetwork_territory_job_store", self.job_store), \
                patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", side_effect=lambda *_: list(areas)), \
                patch.object(run, "identity_projection_store", FakeIdentityProjection(profiles)), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"):
            run.record_territory_areas_delta("foreign-owner", areas, reason="post130_publication")
            run.process_ghostnetwork_territory_job("test-worker")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "contained")

            areas[:] = [self.area("part-owner", 2)]
            run.record_territory_areas_delta("part-owner", areas, reason="post130_owner_changed")
            run.process_ghostnetwork_territory_job("test-worker")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "active")
            progress = self.service.modules.resolve_machine_progress(
                self.repo.get_active_cycle()["cycle_id"], self.part["machine_code"]
            )
            self.assertEqual(progress["parts_active"], 1)

            areas[:] = []
            run.record_territory_areas_delta("part-owner", areas, reason="post130_release")
            run.process_ghostnetwork_territory_job("test-worker")
            released = self.repo.get_part(self.part["part_id"])
            self.assertEqual(released["status"], "public")
            self.assertEqual(released["territory_id"], "")

    def test_area_publication_carries_live_lifecycle_event_to_delta_bridge(self):
        areas = [self.area("foreign-owner", 1)]
        profiles = {
            "foreign-owner": {"username": "foreign-owner", "clan": "sentinel_order"},
        }
        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run, "ghostnetwork_territory_job_store", self.job_store), \
                patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", return_value=areas), \
                patch.object(run, "identity_projection_store", FakeIdentityProjection(profiles)), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"):
            run.record_territory_areas_delta(
                "foreign-owner",
                areas,
                reason="post130_live_containment",
            )
            run.process_ghostnetwork_territory_job("test-worker")

        event_types = []
        event_ids = []
        while True:
            claim = self.delivery_store.claim("test-delivery-worker")
            if not claim:
                break
            event_types.append(claim["event"].get("event_type"))
            event_ids.append(claim["event"].get("event_id"))
            self.delivery_store.advance(
                claim["job_id"], "test-delivery-worker", len(claim["viewers"]), 0,
                len(claim["viewers"]), complete=True,
            )
        self.assertIn("ghost.part_contained", event_types)
        contained_event_id = event_ids[event_types.index("ghost.part_contained")]
        narrative = self.repo.list_narrative_outbox(
            source_event_id=contained_event_id,
            limit=10,
        )
        public_narrative = [item for item in narrative if item["audience_scope"] == "public"]
        self.assertEqual(len(public_narrative), 1)
        self.assertEqual(public_narrative[0]["source_scope"], "ghostnetwork")

    def test_pies1_warsaw_part_does_not_reactivate_after_tokyo_rebuild(self):
        warsaw = [
            {"lat": 52.0, "lng": 21.0},
            {"lat": 52.2, "lng": 21.0},
            {"lat": 52.2, "lng": 21.2},
            {"lat": 52.0, "lng": 21.2},
        ]
        tokyo = [
            {"lat": 35.60, "lng": 139.60},
            {"lat": 35.80, "lng": 139.60},
            {"lat": 35.80, "lng": 139.80},
            {"lat": 35.60, "lng": 139.80},
        ]
        areas = [self.area_at("warsaw-v1", "pies1", warsaw, 1)]
        profiles = {
            "pies1": {"username": "pies1", "clan": self.part["clan_code"]},
        }
        cycle_id = self.repo.get_active_cycle()["cycle_id"]
        delivered = []

        def enqueue(event, recipients=None):
            delivered.append(copy.deepcopy(event))
            return {"ok": True, "recipients": len(recipients or [])}

        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run, "ghostnetwork_territory_job_store", self.job_store), \
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_store, "list_player_areas", side_effect=lambda *_: list(areas)), \
                patch.object(run.territory_store, "get_area_publication", return_value=None), \
                patch.object(run, "identity_projection_store", FakeIdentityProjection(profiles)), \
                patch.object(run, "load_profile_write_record", return_value={
                    "profile": {"username": "pies1"}, "profile_revision": 1,
                }), \
                patch.object(self.service, "handle_reward_event", return_value={"ok": True}), \
                patch.object(run, "enqueue_ghostnetwork_event_delta", side_effect=enqueue):
            run.record_territory_areas_delta("pies1", areas, reason="warsaw_initial")
            initial_job = run.process_ghostnetwork_territory_job("pies1-worker")
            initial_part = self.repo.get_part(self.part["part_id"])
            self.assertEqual(initial_part["status"], "active")
            initial_activation = [
                event for event in delivered if event.get("event_type") == "ghost.part_activated"
            ]
            self.assertEqual(len(initial_activation), 1)
            initial_event_id = initial_activation[0]["event_id"]
            initial_dedupe = initial_activation[0]["dedupe_key"]

            delivered.clear()
            before_version = self.repo.get_state_version(cycle_id)
            before_timestamp = initial_part["last_activated_at"]
            before_narrative_count = len(self.repo.list_narrative_outbox(limit=100))
            areas[:] = [
                self.area_at("warsaw-v2", "pies1", warsaw, 2),
                self.area_at("tokyo-v1", "pies1", tokyo, 2),
            ]
            run.record_territory_areas_delta("pies1", areas, reason="tokyo_capture")
            tokyo_job = run.process_ghostnetwork_territory_job("pies1-worker")
            rebuilt_part = self.repo.get_part(self.part["part_id"])

            self.assertNotEqual(initial_job["job_id"], tokyo_job["job_id"])
            self.assertEqual(rebuilt_part["status"], "active")
            self.assertEqual(rebuilt_part["territory_owner_id"], "pies1")
            self.assertEqual(rebuilt_part["last_activated_at"], before_timestamp)
            self.assertEqual(rebuilt_part["territory_id"], "warsaw-v2")
            self.assertGreater(self.repo.get_state_version(cycle_id), before_version)
            self.assertFalse(any(
                event.get("event_type") in {
                    "ghost.part_contained", "ghost.part_activated",
                    "ghost.part_contested", "ghost.part_revealed",
                    "ghost.part_deactivated", "ghost.machine_progress_changed",
                    "ghost.machine_online", "ghost.signal_sent",
                }
                for event in delivered
            ))
            self.assertEqual(
                len(self.repo.list_narrative_outbox(limit=100)),
                before_narrative_count,
            )

            second_part = next(
                part for part in self.repo.list_parts(cycle_id)
                if part["part_id"] != self.part["part_id"]
                and part["clan_code"] == self.part["clan_code"]
            )
            self.repo.update_part(
                second_part["part_id"], status="public",
                target_id="map:35.70:139.70:tokyo-gn",
                latitude=35.70, longitude=139.70,
                discovered_by="scanner", discovered_clan="virex",
                discovered_at="2026-08-25T00:00:03Z",
            )
            delivered.clear()
            areas[:] = [
                self.area_at("warsaw-v2", "pies1", warsaw, 3),
                self.area_at("tokyo-v1", "pies1", tokyo, 3),
            ]
            run.record_territory_areas_delta("pies1", areas, reason="tokyo_real_activation")
            run.process_ghostnetwork_territory_job("pies1-worker")
            true_activation = [
                event for event in delivered if event.get("event_type") == "ghost.part_activated"
            ]
            self.assertEqual(len(true_activation), 1)
            self.assertNotEqual(true_activation[0]["event_id"], initial_event_id)
            self.assertNotEqual(true_activation[0]["dedupe_key"], initial_dedupe)

            delivered.clear()
            areas[:] = [
                self.area_at("warsaw-v3", "pies1", warsaw, 4),
                self.area_at("tokyo-v2", "pies1", tokyo, 4),
            ]
            run.record_territory_areas_delta("pies1", areas, reason="tokyo_replay")
            run.process_ghostnetwork_territory_job("pies1-worker")
            self.assertFalse(any(
                event.get("event_type") in {
                    "ghost.part_contained", "ghost.part_activated",
                    "ghost.part_contested", "ghost.part_revealed",
                    "ghost.part_deactivated", "ghost.machine_progress_changed",
                    "ghost.machine_online", "ghost.signal_sent",
                }
                for event in delivered
            ))

    def test_canonical_ghost_clan_profile_is_included_in_territory_publication(self):
        areas = [self.area("foreign-owner", 1)]
        profile = {"ghost_clan_code": "sentinel_order"}
        with patch.object(run.territory_store, "list_player_areas", return_value=areas), \
                patch.object(run, "identity_projection_store", FakeIdentityProjection({"foreign-owner": profile})), \
                patch.object(run.user_store, "get_profile", return_value=profile):
            publication = run.build_ghostnetwork_territory_publication()

        self.assertEqual(len(publication), 1)
        self.assertEqual(publication[0]["owner_username"], "foreign-owner")
        self.assertEqual(publication[0]["owner_clan"], "sentinel_order")

    def test_public_reward_event_preserves_profile_payload(self):
        from database import db_connect
        event = dict(event_id='bounded-public', event_type='ghost.part_activated',
            cycle_id=self.repo.get_active_cycle()['cycle_id'], part_id='bounded-part',
            player_id='alice', clan_code='virex', payload=dict(score=10))
        event = self.repo.append_event(**event)
        with db_connect(self.db_path) as conn:
            before = tuple(conn.execute("SELECT profile_json,profile_checksum FROM users WHERE username='alice'").fetchone())
        with patch.object(run, 'load_profile_write_record', side_effect=AssertionError('heavy')), \
             patch.object(run, 'save_profile_write_record', side_effect=AssertionError('heavy')), \
             patch.object(run, 'enqueue_ghostnetwork_event_delta', return_value={}):
            run.apply_ghostnetwork_runtime_result(self.service, event)
        with db_connect(self.db_path) as conn:
            after = tuple(conn.execute("SELECT profile_json,profile_checksum FROM users WHERE username='alice'").fetchone())
        self.assertEqual(before, after)
        self.assertGreater(self.progression.progression.get('alice')['respect'], 100)

    def test_reward_ledger_failure_stays_pending_and_retry_applies_once(self):
        event = dict(event_id='bounded-failure', event_type='ghost.part_activated',
            cycle_id=self.repo.get_active_cycle()['cycle_id'], part_id='bounded-failure-part',
            player_id='alice', clan_code='virex', payload=dict(score=10))
        event = self.repo.append_event(**event)
        with patch.object(run, 'enqueue_ghostnetwork_event_delta', return_value={}):
            with patch.object(self.progression.progression, 'award', side_effect=ProfileWriteConflict('failure')):
                with self.assertRaises(ProfileWriteConflict):
                    run.apply_ghostnetwork_runtime_result(self.service, event)
            self.assertEqual(self.progression.progression.get('alice')['respect'], 100)
            self.assertEqual(self.repo.list_rewards(player_id='alice', limit=10)[0]['status'], 'pending')
            run.apply_ghostnetwork_runtime_result(self.service, event)
            after = self.progression.progression.get('alice')
            run.apply_ghostnetwork_runtime_result(self.service, event)
        self.assertEqual(after, self.progression.progression.get('alice'))
        self.assertEqual(self.repo.get_clan_reputation('virex')['parts_activated'], 1)

    def test_reward_crash_after_ledger_commit_retries_without_double_rsp(self):
        event = dict(event_id='bounded-crash', event_type='ghost.part_activated',
            cycle_id=self.repo.get_active_cycle()['cycle_id'], part_id='bounded-crash-part',
            player_id='alice', clan_code='virex', payload=dict(score=10))
        event = self.repo.append_event(**event)
        with patch.object(run, 'enqueue_ghostnetwork_event_delta', return_value={}):
            with patch.object(self.service, 'finalize_projected_reward', side_effect=RuntimeError('crash')):
                with self.assertRaises(RuntimeError):
                    run.apply_ghostnetwork_runtime_result(self.service, event)
            after = self.progression.progression.get('alice')
            self.assertGreater(after['respect'], 100)
            run.apply_ghostnetwork_runtime_result(self.service, event)
        self.assertEqual(after, self.progression.progression.get('alice'))
        self.assertEqual(self.repo.get_clan_reputation('virex')['parts_activated'], 1)

    def test_territory_publication_does_not_require_username_inside_profile_json(self):
        areas = [self.area("foreign-owner", 1)]
        profile_without_username = {"ghost_clan_code": "sentinel_order"}
        with patch.object(run.territory_store, "list_player_areas", return_value=areas), \
                patch.object(
                    run,
                    "identity_projection_store",
                    FakeIdentityProjection({"foreign-owner": profile_without_username}),
                ):
            publication = run.build_ghostnetwork_territory_publication()

        self.assertEqual(len(publication), 1)
        self.assertEqual(publication[0]["owner_username"], "foreign-owner")
        self.assertEqual(publication[0]["owner_clan"], "sentinel_order")

    def test_canonical_conflict_publication_freezes_and_resolution_reconciles(self):
        areas = [self.area("part-owner", 1)]
        profiles = {"part-owner": {"username": "part-owner", "clan": self.part["clan_code"]}}
        active_snapshot = {
            "conflict": {"conflict_id": "post130-conflict", "status": "active", "conflict_version": 3},
            "fronts": [{"front_id": "post130-front", "geometry": areas[0]["vertices"]}],
        }
        resolved_snapshot = {
            "conflict": {"conflict_id": "post130-conflict", "status": "resolved", "conflict_version": 4},
            "fronts": active_snapshot["fronts"],
        }
        latest = {"value": active_snapshot}
        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run, "ghostnetwork_territory_job_store", self.job_store), \
                patch.object(run, "ghostnetwork_delta_delivery_job_store", self.delivery_store), \
                patch.object(run.territory_delta_publisher, "record_areas_updated", return_value=[]), \
                patch.object(run.territory_delta_publisher, "record_conflict_changed", return_value=[]), \
                patch.object(run.territory_conflict_store, "latest_snapshot_state", side_effect=lambda *_: latest["value"]), \
                patch.object(run.territory_store, "list_player_areas", side_effect=lambda *_: list(areas)), \
                patch.object(run, "identity_projection_store", FakeIdentityProjection(profiles)), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: profiles.get(username, {})), \
                patch.object(run.user_store, "save_profile"):
            run.record_territory_areas_delta("part-owner", areas, reason="post130_stable")
            run.process_ghostnetwork_territory_job("test-worker")
            self.assertEqual(self.repo.get_part(self.part["part_id"])["status"], "active")

            run.record_territory_conflict_delta(active_snapshot["conflict"], reason="post130_conflict_started")
            run.process_ghostnetwork_territory_job("test-worker")
            contested = self.repo.get_part(self.part["part_id"])
            self.assertEqual(contested["conflict_state"], "contested")

            latest["value"] = resolved_snapshot
            run.record_territory_conflict_delta(resolved_snapshot["conflict"], reason="post130_conflict_resolved")
            run.process_ghostnetwork_territory_job("test-worker")
            resolved = self.repo.get_part(self.part["part_id"])
            self.assertEqual(resolved["conflict_state"], "none")
            self.assertEqual(resolved["status"], "active")

        resolved_event = next(
            event for event in self.repo.list_events(limit=1000)
            if event["event_type"] == "ghost.part_conflict_resolved"
            and event["part_id"] == self.part["part_id"]
        )
        tasks = self.repo.list_narrative_outbox(
            source_scope="ghostnetwork",
            source_event_id=resolved_event["event_id"],
            limit=10,
        )
        self.assertEqual(
            {task["target_medium"] for task in tasks},
            {"blacknet", "googleplex_news"},
        )
        self.assertTrue(any(task["audience_scope"] == "public" for task in tasks))


if __name__ == "__main__":
    unittest.main()
