import os
import inspect
import math
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import run
from database import PlayerScanSnapshotStore, VulnerabilityStore
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService
from ghostnetwork.territory_defense import (
    MAX_TERRITORY_DEFENSE_SWARM,
    select_territory_defense_swarm,
)


def marker(lat, lng, label, generated=False):
    return {
        "lat": lat,
        "lng": lng,
        "name": label,
        "label": label,
        "icon": "!",
        "source_type": "test",
        "generated": generated,
    }


class TerritoryDefenseGeometryTest(unittest.TestCase):
    def test_one_to_three_scan_results_are_all_published(self):
        markers = [marker(52.0, 21.0, "A"), marker(52.01, 21.0, "B"), marker(52.0, 21.01, "C")]
        self.assertEqual(markers, select_territory_defense_swarm(markers, markers[0]))

    def test_dense_rectangular_scan_reduces_to_four_extreme_points(self):
        markers = [
            marker(52.0, 21.0, "NW"), marker(52.0, 21.1, "NE"),
            marker(52.1, 21.1, "SE"), marker(52.1, 21.0, "SW"),
        ]
        markers.extend(
            marker(52.01 + index * 0.001, 21.01 + index * 0.001, f"I{index}")
            for index in range(65)
        )
        selected = select_territory_defense_swarm(markers, markers[0])
        self.assertEqual(4, len(selected))
        self.assertEqual({"NW", "NE", "SE", "SW"}, {item["label"] for item in selected})

    def test_irregular_outline_is_bounded_and_keeps_interior_anchor(self):
        outline = [
            marker(52 + 0.1 * math.sin(index), 21 + 0.1 * math.cos(index), f"E{index}")
            for index in range(20)
        ]
        anchor = marker(52.0, 21.0, "ANCHOR")
        selected = select_territory_defense_swarm(outline + [anchor], anchor)
        self.assertEqual(MAX_TERRITORY_DEFENSE_SWARM, len(selected))
        self.assertIn("ANCHOR", {item["label"] for item in selected})

    def test_untrusted_anchor_outside_snapshot_cannot_create_swarm(self):
        markers = [marker(52.0, 21.0, "A"), marker(52.1, 21.1, "B")]
        self.assertEqual([], select_territory_defense_swarm(markers, marker(51.0, 20.0, "X")))


class TerritoryDefenseRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "game.sqlite3")
        self.scans = PlayerScanSnapshotStore(self.db_path)
        self.vulnerabilities = VulnerabilityStore(self.db_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_snapshot_is_owner_scoped_and_replaced_by_next_scan(self):
        first = self.scans.record("alice", [marker(52, 21, "A")], 52, 21)
        self.assertIsNotNone(self.scans.get("alice", first["scan_id"]))
        self.assertIsNone(self.scans.get("bob", first["scan_id"]))
        second = self.scans.record("alice", [marker(53, 22, "B")], 53, 22)
        self.assertIsNone(self.scans.get("alice", first["scan_id"]))
        self.assertIsNotNone(self.scans.get("alice", second["scan_id"]))

    def test_report_gate_publishes_one_bounded_swarm_and_persists_provenance(self):
        markers = [
            marker(52.0, 21.0, "A"), marker(52.0, 21.1, "B"),
            marker(52.1, 21.1, "C"), marker(52.1, 21.0, "D"),
            marker(52.05, 21.05, "CENTER"),
        ]
        scan = self.scans.record("alice", markers, 52.05, 21.05)
        target = {**markers[-1], "scan_id": scan["scan_id"]}

        class FakeService:
            def active_territory_defense_effect(self, player_context):
                return {
                    "active": True,
                    "ability_code": "reflection",
                    "window_id": "window-p5",
                    "cooldown_until": "2099-09-07T22:00:00+00:00",
                    "swarm_limit": 8,
                }

        with run.app.test_request_context(
            "/api/vulnerabilities/report", method="POST", json={"target": target},
        ):
            run.session["user"] = "alice"
            with (
                patch.object(run, "sync_session_profile", return_value={
                    "username": "alice", "clan": "Siatka Widmo",
                    "profession": "Lustrzany Sędzia", "level": 30,
                }),
                patch.object(run, "player_scan_snapshot_store", self.scans),
                patch.object(run, "vulnerability_store", self.vulnerabilities),
                patch.object(run, "get_ghostnetwork_service", return_value=FakeService()),
                patch.object(run, "find_area_for_point", return_value=None),
                patch.object(run.resources_store, "get", return_value={}),
            ):
                response = run.report_vulnerability()

        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["swarm"]["active"])
        self.assertEqual(5, payload["swarm"]["scan_count"])
        self.assertEqual(5, payload["swarm"]["count"])
        self.assertLessEqual(payload["swarm"]["count"], MAX_TERRITORY_DEFENSE_SWARM)
        stored = self.vulnerabilities.list_active()
        self.assertEqual(payload["swarm"]["count"], len(stored))
        self.assertEqual("2099-09-07T22:00:00+00:00", payload["swarm"]["expires_at"])
        self.assertEqual(1, sum(
            bool(item["target"]["territory_defense_provenance"]["primary"])
            for item in stored
        ))
        for report in stored:
            provenance = report["target"]["territory_defense_provenance"]
            self.assertEqual("territory_defense", provenance["family"])
            self.assertEqual("window-p5", provenance["window_id"])
            self.assertEqual(payload["swarm"]["swarm_id"], provenance["swarm_id"])

    def test_swarm_satellites_expire_after_cooldown_but_primary_survives(self):
        expiry = "2026-09-07T22:00:00+00:00"
        for index, primary in enumerate((True, False, False)):
            item = marker(52 + index * 0.01, 21, f"V{index}")
            item["territory_defense_provenance"] = {
                "family": "territory_defense",
                "swarm_id": "swarm-expiry",
                "primary": primary,
                "ephemeral": not primary,
                "expires_at": expiry,
            }
            self.vulnerabilities.report(item, "alice", "phantom_mesh", {})

        expired = self.vulnerabilities.expire_territory_defense_satellites(
            "2026-09-07T22:00:01+00:00"
        )
        self.assertEqual(2, expired)
        active = self.vulnerabilities.list_active()
        self.assertEqual(1, len(active))
        self.assertTrue(active[0]["target"]["territory_defense_provenance"]["primary"])

    def test_enemy_swarm_alarm_is_claimed_once_per_clan(self):
        self.assertTrue(self.vulnerabilities.claim_swarm_alarm("swarm-1", "virex", "eve"))
        self.assertFalse(self.vulnerabilities.claim_swarm_alarm("swarm-1", "virex", "mallory"))
        self.assertTrue(self.vulnerabilities.claim_swarm_alarm("swarm-1", "echo_freedom", "bob"))

    def test_same_clan_capture_takes_whole_swarm_but_enemy_capture_does_not(self):
        reports = []
        for index in range(3):
            item = marker(52 + index * 0.01, 21, f"S{index}")
            item["territory_defense_provenance"] = {
                "family": "territory_defense",
                "swarm_id": "swarm-capture",
                "primary": index == 0,
                "expires_at": "2099-09-07T22:00:00+00:00",
            }
            reports.append(self.vulnerabilities.report(
                item, "alice", "Siatka Widmo", {}
            ))

        territory = MagicMock()
        territory.save_captured_target.side_effect = lambda username, target: dict(target)
        marked = MagicMock()
        runtime = MagicMock()
        with (
            patch.object(run, "vulnerability_store", self.vulnerabilities),
            patch.object(run, "territory_store", territory),
            patch.object(run, "player_marked_target_store", marked),
            patch.object(run, "player_target_runtime_store", runtime),
            patch.object(run, "record_map_target_delta"),
        ):
            enemy = run.capture_same_clan_territory_defense_swarm(
                reports[0], "eve", {"clan": "VIREX"}
            )
            captured = run.capture_same_clan_territory_defense_swarm(
                reports[0], "bob", {"clan": "Siatka Widmo"}
            )

        self.assertEqual([], enemy)
        self.assertEqual(2, len(captured))
        self.assertEqual(2, territory.save_captured_target.call_count)
        self.assertEqual(1, len(self.vulnerabilities.list_active()))

    def test_p5_maps_to_shared_family_and_activation_only_arms_report_gate(self):
        now = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)
        repo = GhostNetworkRepository(db_path=self.db_path, clock=lambda: now)
        cycle = GhostCycleService(repository=repo).ensure_active_cycle()["cycle"]
        part = next(item for item in repo.list_parts(cycle["cycle_id"]) if item["part_code"] == "P5")
        repo.update_part(
            part["part_id"], status="active", target_id="target-p5",
            latitude=52.2, longitude=21.0, discovered_by="alice",
            discovered_clan="phantom_mesh", conflict_state="none", frozen_status="",
            conflict_id="", territory_id="area-p5", territory_owner_id="alice",
            territory_clan="phantom_mesh", activated_at=now.isoformat(),
            last_activated_at=now.isoformat(),
        )
        player = {
            "username": "alice", "player_id": "alice", "clan": "phantom_mesh",
            "profession": "mirror_judge", "level": 30,
        }
        with patch("ghostnetwork.service.GHOSTNETWORK_ABILITY_ALLOWED_CODES", ("reflection",)):
            service = GhostNetworkService(repository=repo)
            activated = service.activate_player_ability(player, "p5-activate", now=now)
            effect = service.active_territory_defense_effect(player, now=now)
        self.assertEqual("armed", activated["realizer"]["status"])
        self.assertTrue(effect["active"])
        self.assertEqual("reflection", effect["ability_code"])

    def test_scan_and_frontend_contract_carry_trusted_scan_identity(self):
        map_action = inspect.getsource(run.map_action)
        report = inspect.getsource(run.report_vulnerability)
        frontend = Path("templates/map_template.html").read_text(encoding="utf-8")
        for token in (
            "player_scan_snapshot_store.record",
            'marker["scan_id"] = scan_id',
            '"scan_id": scan_id',
        ):
            self.assertIn(token, map_action)
        self.assertIn("select_territory_defense_swarm", report)
        self.assertIn("territory_defense_provenance", report)
        self.assertIn("scan_id: menuObj.scan_id", frontend)
        self.assertIn("scan_id: targetContext?.scan_id", frontend)
        self.assertIn("data.swarm && data.swarm.active", frontend)
        self.assertIn("is-territory-defense", frontend)


if __name__ == "__main__":
    unittest.main()
