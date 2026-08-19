import copy
import os
import tempfile
import unittest
from unittest.mock import patch

import run
from ghostnetwork import GhostCycleService, GhostDropPolicy, GhostNetworkRepository, GhostNetworkService


class MemoryReceiptStore:
    def __init__(self):
        self.rows = {}

    def begin(self, key, **metadata):
        if key in self.rows:
            row = self.rows[key]
            return ("completed" if row.get("payload") else "in_flight"), copy.deepcopy(row)
        self.rows[key] = {"receipt_key": key, "state": "started", **metadata, "payload": {}}
        return "new", copy.deepcopy(self.rows[key])

    def finish(self, key, payload=None, status_code=200, **_kwargs):
        self.rows[key].update({"payload": copy.deepcopy(payload or {}), "status_code": status_code, "state": "completed"})
        return copy.deepcopy(self.rows[key])


class GhostNetworkPost130E2ETest(unittest.TestCase):
    SECURITY_KEYS = [
        "stealth_mode", "scan_detection", "exploit_protection", "vpn_enabled",
        "browser_protection", "os_hardening", "log_guardian", "process_monitor",
        "firewall", "log_integrity", "network_anomaly_detection", "spoofing_protection",
        "activity_monitor", "player_tracking", "system_visibility", "firewall_core",
        "kernel_guard", "system_integrity_check", "heap_protection", "memory_lock",
        "background_injection", "memory_guard", "vpn_blocker",
    ]
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghost-e2e.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        GhostCycleService(repository=self.repo).ensure_active_cycle()
        self.service = GhostNetworkService(
            repository=self.repo,
            drop_policy=GhostDropPolicy(enabled=True, chance=1.0),
        )
        self.target = {
            "target_id": "map:52.1:21.2:e2e", "target_mode": "standard",
            "lat": 52.1, "lng": 21.2, "label": "E2E target",
            "source_type": "shop", "hackable": True,
            "security": {key: False for key in self.SECURITY_KEYS},
            "actions_allowed": {"scan_ports": True, "exploit": True, "sniff": True, "trace": True},
        }
        self.profile = {
            "username": "alice", "nick": "Alice", "ghost_clan_code": "virex",
            "level": 1, "respect": 0, "exp": 0, "territory_stats": {},
            "hacked": [], "system_messages": [],
            "apps": [{
                "id": "ghost-e2e-tool", "name": "Ghost E2E Tool",
                "requires_off": [], "interferes_with": [],
                "levels": [{"options": []}],
            }],
            "aimed_target": copy.deepcopy(self.target),
        }

    def tearDown(self):
        self.tmp.cleanup()

    def test_target_registry_to_gonna_win_receipt_and_durable_discovery(self):
        receipt_store = MemoryReceiptStore()
        profiles = {"alice": copy.deepcopy(self.profile)}
        captured = []

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, updates):
                profiles[self.username].update(copy.deepcopy(updates or {}))

        def save_profile(profile):
            profiles[profile["username"]] = copy.deepcopy(profile)

        def save_capture(_username, target):
            value = copy.deepcopy(target)
            captured[:] = [value]
            return value

        with patch.object(run, "GhostNetworkService", return_value=self.service), \
                patch.object(run, "app_action_receipt_store", receipt_store), \
                patch.object(run, "sync_session_profile", side_effect=lambda *_, **_kwargs: copy.deepcopy(profiles["alice"])), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run.user_store, "get_profile", side_effect=lambda username: copy.deepcopy(profiles.get(username, {}))), \
                patch.object(run.user_store, "save_profile", side_effect=save_profile), \
                patch.object(run.player_target_runtime_store, "upsert_aimed", side_effect=lambda _u, target, **_kwargs: {"target": target, "status": "aimed"}), \
                patch.object(run.player_target_runtime_store, "mark_captured", return_value={"status": "captured"}), \
                patch.object(run.territory_store, "save_captured_target", side_effect=save_capture), \
                patch.object(run.territory_store, "list_captured_targets", side_effect=lambda _u: copy.deepcopy(captured)), \
                patch.object(run.territory_store, "list_player_areas", return_value=[]), \
                patch.object(run, "find_owned_captured_target_for_runtime_target", return_value=None), \
                patch.object(run, "find_captured_target_for_owner", return_value=None), \
                patch.object(run, "rebuild_player_areas_with_territory_delta", return_value=[]), \
                patch.object(run, "finalize_territory_progression_receipt", return_value={"levels_gained": 0, "respect_gain": 0}), \
                patch.object(run.territory_progression_receipt_store, "ensure", return_value={"receipt_id": "progress:e2e", "status": "applied"}):
            aimed_profile = copy.deepcopy(profiles["alice"])
            run.set_player_aimed_target("alice", aimed_profile, copy.deepcopy(self.target), reason="e2e_target_registry")
            profiles["alice"] = aimed_profile
            self.assertEqual(self.service.get_reservation_status()["active"], 1)

            client = run.app.test_client()
            with client.session_transaction() as session:
                session["user"] = "alice"
            payload = {
                "app_id": "ghost-e2e-tool", "launch_receipt": "e2e-launch-1",
                "expected_target": copy.deepcopy(self.target),
            }
            first = client.post("/gonna-win", json=payload)
            self.assertEqual(first.status_code, 200, first.get_json())
            self.assertTrue(first.get_json()["success"])
            second = client.post("/gonna-win", json=payload)
            self.assertEqual(second.status_code, 200)
            self.assertTrue(second.get_json()["idempotent_replay"])

        part = self.repo.find_part_by_target(self.repo.get_active_cycle()["cycle_id"], self.target["target_id"])
        self.assertIsNotNone(part)
        self.assertEqual(part["status"], "public")
        self.assertEqual(
            self.repo.get_capture_effect_summary()["applied"], 1,
            self.repo.list_capture_effects(limit=10),
        )
        self.assertEqual(len(self.repo.list_player_contributions("alice", cycle_id=self.repo.get_active_cycle()["cycle_id"])), 1)
        self.assertEqual(profiles["alice"]["ghostnetwork_reward_history"].__len__(), 1)


if __name__ == "__main__":
    unittest.main()
