import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from database import (
    PlayerInventoryStore,
    PlayerOperationStore,
    PlayerTargetRuntimeStore,
    TerritoryStore,
    UserCapabilityProjectionStore,
    UserStore,
    get_hot_path_metrics,
    hash_password,
    reset_hot_path_metrics,
    restore_hot_path_metrics,
)
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.ability_realizers import (
    ALLOWED_REALIZER_FAMILIES,
    GhostAbilityCanonicalPilotHarness,
)


def player_profile(username):
    password_hash, salt = hash_password("pilot-secret")
    return {
        "username": username,
        "password": password_hash,
        "salt": salt,
        "nick": "Pilot",
        "level": 71,
        "hackcoins": 1000,
        "respect": 0,
        "exp": "0 / 1000",
        "inventory": [],
        "files": {"tools": []},
        "apps": [],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
        "ghost_clan_code": "virex",
        "ghost_profession": "broker",
    }


class GhostAbilityCanonicalStoreCertificationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.now = datetime(2026, 9, 5, 12, 0, tzinfo=timezone.utc)
        self.username = "alice"
        self.repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: self.now)
        cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        part = next(
            item for item in self.repo.list_parts(cycle["cycle_id"])
            if item["part_code"] == "V1"
        )
        self.repo.update_part(
            part["part_id"], status="active", target_id="target-v1",
            latitude=52.2, longitude=21.0, discovered_by=self.username,
            discovered_clan="virex", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-v1", territory_owner_id=self.username,
            territory_clan="virex",
        )
        users = UserStore(self.db_path, seed_path=os.path.join(self.tmp.name, "missing.json"))
        users.save_profile_guarded(
            player_profile(self.username), expected_revision=0,
            source="test.ability.canonical", allow_create=True,
        )
        self.operations = PlayerOperationStore(self.db_path)
        self.inventory = PlayerInventoryStore(self.db_path)
        self.targets = PlayerTargetRuntimeStore(self.db_path)
        self.territory = TerritoryStore(self.db_path)
        self.capabilities = UserCapabilityProjectionStore(self.db_path)
        self.operation_id = "pilot-operation"
        self.operations.upsert_operations(self.username, [{
            "operation_id": self.operation_id,
            "owner_username": self.username,
            "target_id": "map:52.1:21.1:PILOT",
            "operation_type": "generic_trace",
            "status": "running",
            "started_at": (self.now - timedelta(minutes=1)).isoformat(),
            "expires_at": (self.now + timedelta(minutes=10)).isoformat(),
            "source_app_quality": {
                "creator_power": 50, "quality_score": 50, "reliability": 50,
            },
            "target": {"security": {"firewall": True, "ids": True}},
        }])
        self.inventory.append_data_files(self.username, [
            {
                "id": "camera-1", "file_category": "camera",
                "quality_score": 90, "completeness_percent": 70,
                "source_operation_id": self.operation_id,
            },
            {
                "id": "audio-1", "file_category": "audio",
                "quality_score": 40, "completeness_percent": 40,
                "source_operation_id": self.operation_id,
            },
            {
                "id": "document-1", "file_category": "document",
                "quality_score": 10, "completeness_percent": 10,
                "source_operation_id": self.operation_id,
            },
        ], operation_id=self.operation_id)
        aimed = self.targets.upsert_aimed(self.username, {
            "target_id": "map:52.1:21.1:PILOT",
            "lat": 52.1,
            "lng": 21.1,
            "label": "PILOT",
            "actions_allowed": {
                "scan_ports": False, "exploit": False,
                "sniff": False, "trace": False,
            },
            "security": {
                "firewall": True, "ids": True,
                "encryption": True, "vpn": False,
            },
        })
        self.target_key = aimed["target"]["target_id"]
        self.captured = self.territory.save_captured_target(self.username, {
            "target_id": "map:52.3:21.3:OWNED",
            "lat": 52.3,
            "lng": 21.3,
            "label": "OWNED",
            "name": "OWNED",
            "stationary": True,
            "security": {
                "firewall": False, "ids": False,
                "encryption": False, "vpn": True,
            },
            "security_version": 0,
        })
        self.player = {
            "username": self.username, "player_id": self.username,
            "clan": "virex", "profession": "broker", "level": 71,
        }

    def tearDown(self):
        self.tmp.cleanup()

    def harness(self, family):
        return GhostAbilityCanonicalPilotHarness(
            family,
            self.username,
            stores={
                "operations": self.operations,
                "inventory": self.inventory,
                "targets": self.targets,
                "territory": self.territory,
                "capabilities": self.capabilities,
            },
            selection={
                "operation_id": self.operation_id,
                "target_key": self.target_key,
                "captured_target_id": self.captured["target_id"],
                "captured_lat": self.captured["lat"],
                "captured_lng": self.captured["lng"],
                "captured_label": self.captured["label"],
            },
        )

    def activate(self, family):
        service = GhostNetworkService(
            repository=self.repo,
            ability_pilot_harness=self.harness(family),
        )
        result = service.activate_player_ability(
            self.player, f"canonical-{family}", now=self.now,
        )
        self.assertTrue(result["ok"])
        self.assertEqual("canonical_store_certification", result["pilot_evidence"]["mode"])
        return result["pilot_evidence"]["evidence"]

    def test_all_nine_families_touch_only_their_canonical_boundary(self):
        for family in ALLOWED_REALIZER_FAMILIES:
            with self.subTest(family=family):
                evidence = self.activate(family)
                self.assertIsInstance(evidence, dict)
                self.now += timedelta(hours=1, seconds=1)

    def test_operation_speed_is_persisted_once_with_bounded_query(self):
        before = self.operations.list_active_operations(self.username, limit=8)[0]
        evidence = self.activate("operation_speed")
        after = self.operations.list_active_operations(self.username, limit=8)[0]
        self.assertEqual([self.operation_id], evidence["persisted"])
        self.assertLess(after["expires_at"], before["expires_at"])
        self.assertEqual(1, len(after["ability_application_keys"]))

    def test_file_realizers_persist_dedupe_and_category_limits(self):
        yielded = self.activate("file_yield")
        self.assertEqual(2, len(yielded["persisted"]))
        self.now += timedelta(hours=1, seconds=1)
        quality = self.activate("data_quality")
        files = {
            item["id"]: item
            for item in self.inventory.list_data_files(
                self.username, operation_id=self.operation_id, limit=20,
            )
        }
        self.assertEqual(4, len(quality["changed"]))
        self.assertEqual(100, files["camera-1"]["quality_score"])
        self.assertEqual(10, files["document-1"]["quality_score"])

    def test_target_actions_and_security_use_versioned_selected_target(self):
        before = self.targets.get(self.username)
        actions = self.activate("hack_actions")
        after_actions = self.targets.get(self.username)
        self.assertTrue(actions["security_unchanged"])
        self.assertTrue(all(after_actions["actions_allowed"].values()))
        self.assertGreater(after_actions["version"], before["version"])
        self.now += timedelta(hours=1, seconds=1)
        security = self.activate("target_security")
        self.assertLessEqual(len(security["changed"]), 2)
        self.assertEqual(after_actions["version"] + 1, self.targets.get(self.username)["version"])

    def test_risk_range_zoom_and_owned_defense_use_real_calculators_and_stores(self):
        risk = self.activate("operation_risk")
        self.assertTrue(risk["persisted"])
        self.assertEqual(-15, risk["modifier"])
        self.assertLess(risk["after_heat"], risk["before_heat"])
        self.now += timedelta(hours=1, seconds=1)
        scan = self.activate("scan_range")
        self.assertGreater(scan["effective"], scan["base"])
        self.now += timedelta(hours=1, seconds=1)
        zoom = self.activate("map_zoom")
        self.assertEqual(20, zoom["effective"])
        self.now += timedelta(hours=1, seconds=1)
        defense = self.activate("territory_defense")
        self.assertTrue(defense["persisted"])
        self.assertTrue(defense["owner_checked"])
        stored = self.territory.get_captured_target(
            self.username,
            lat=self.captured["lat"], lng=self.captured["lng"],
            label=self.captured["label"],
        )
        self.assertEqual(1, stored["security_version"])

    def test_canonical_harness_records_zero_heavy_profile_activity(self):
        token = reset_hot_path_metrics()
        try:
            for family in ALLOWED_REALIZER_FAMILIES:
                self.activate(family)
                self.now += timedelta(hours=1, seconds=1)
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(token)
        for key in (
            "profile_full_read", "profile_full_write", "profile_bytes",
            "all_user_profile_scan", "per_recipient_profile_read",
        ):
            self.assertEqual(0, metrics[key], key)

    def test_captured_target_lookup_does_not_enumerate_owner_inventory(self):
        with patch.object(
            self.territory,
            "list_captured_targets",
            side_effect=AssertionError("unbounded owner inventory read"),
        ):
            target = self.territory.get_captured_target(
                self.username,
                lat=self.captured["lat"], lng=self.captured["lng"],
                label=self.captured["label"],
            )
        self.assertEqual(self.captured["target_id"], target["target_id"])


if __name__ == "__main__":
    unittest.main()
