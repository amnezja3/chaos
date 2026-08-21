import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork import (
    GhostCycleService,
    GhostNetworkRepository,
    GhostNetworkService,
    GhostVisibilityService,
    VISIBILITY_VERSION,
)


def future_iso(minutes=10):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class GhostVisibilityServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        self.visibility = GhostVisibilityService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def part(self, code):
        for part in self.repo.list_parts(self.cycle["cycle_id"]):
            if part["part_code"] == code:
                return part
        raise AssertionError(f"Missing part {code}")

    def set_public(self, code="V1"):
        part = self.part(code)
        return self.repo.update_part(
            part["part_id"],
            status="public",
            target_id=f"target-{code}",
            latitude=52.25,
            longitude=21.0,
            discovered_by="main",
            discovered_clan="virex",
            conflict_state="none",
            frozen_status="",
            conflict_id="",
            territory_id="",
            territory_owner_id="",
            territory_clan="",
        )

    def set_contained(self, code="P3", owner="main", territory_clan="virex"):
        part = self.part(code)
        return self.repo.update_part(
            part["part_id"],
            status="contained",
            target_id=f"target-{code}",
            latitude=52.26,
            longitude=21.01,
            discovered_by="robot",
            discovered_clan="sentinel_order",
            conflict_state="none",
            frozen_status="",
            conflict_id="",
            territory_id="territory-blocking",
            territory_owner_id=owner,
            territory_clan=territory_clan,
        )

    def set_active(self, code="E1", owner="ally"):
        part = self.part(code)
        return self.repo.update_part(
            part["part_id"],
            status="active",
            target_id=f"target-{code}",
            latitude=52.27,
            longitude=21.02,
            discovered_by="ally",
            discovered_clan=part["clan_code"],
            conflict_state="none",
            frozen_status="",
            conflict_id="",
            territory_id="territory-active",
            territory_owner_id=owner,
            territory_clan=part["clan_code"],
        )

    def encoded(self, value):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def connected_pair(self):
        parts_by_id = {part["part_id"]: part for part in self.repo.list_parts(self.cycle["cycle_id"])}
        connection = self.repo.list_connections(self.cycle["cycle_id"])[0]
        return parts_by_id[connection["part_a_id"]]["part_code"], parts_by_id[connection["part_b_id"]]["part_code"], connection

    def test_neutral_part_is_full_public(self):
        part = self.set_public("V1")
        projected = self.visibility.project_part_for_viewer(
            part,
            {"viewer_id": "stranger", "viewer_clan": "sentinel_order", "audience_scope": "player"},
        )
        self.assertEqual(projected["visibility_level"], "full_public")
        self.assertEqual(projected["viewer_relation"], "public_neutral")
        self.assertTrue(projected["identity_visible"])
        self.assertEqual(projected["part_code"], "V1")
        self.assertEqual(projected["name"], "Ledger Nexus")
        self.assertEqual(projected["ability_code"], "insider_feed")
        self.assertEqual(projected["target_id"], "target-V1")
        self.assertEqual(projected["location_visibility"], "exact")
        self.assertEqual(projected["visual_asset_key"], "ghostnetwork.part.ledger_nexus")
        self.assertEqual(
            projected["visual_asset_url"],
            "/static/images/ghostnetwork/parts/v1_ledger_nexus.png",
        )

    def test_blocked_part_is_full_only_for_territory_owner(self):
        part = self.set_contained("P3", owner="main", territory_clan="virex")
        owner = self.visibility.project_part_for_viewer(
            part,
            {"viewer_id": "main", "viewer_clan": "virex", "audience_scope": "player"},
        )
        self.assertEqual(owner["visibility_level"], "full_owner")
        self.assertEqual(owner["viewer_relation"], "self_foreign_blocked")
        self.assertEqual(owner["part_code"], "P3")
        self.assertEqual(owner["name"], "Paranoia Loop")
        self.assertEqual(owner["location_visibility"], "exact")

        clanmate = self.visibility.project_part_for_viewer(
            part,
            {"viewer_id": "other_virex", "viewer_clan": "virex", "audience_scope": "player"},
        )
        self.assertEqual(clanmate["visibility_level"], "contained_hidden")
        self.assertEqual(clanmate["viewer_relation"], "foreign_blocked")
        self.assertFalse(clanmate["identity_visible"])
        self.assertIsNone(clanmate["part_id"])
        self.assertIsNone(clanmate["part_code"])
        self.assertIsNone(clanmate["name"])
        self.assertIsNone(clanmate["target_id"])
        self.assertIsNone(clanmate["visual_asset_key"])
        self.assertIsNone(clanmate["visual_asset_url"])
        self.assertEqual(clanmate["location_visibility"], "territory_only")
        leaked = self.encoded(clanmate)
        self.assertNotIn("P3", leaked)
        self.assertNotIn("Paranoia Loop", leaked)
        self.assertNotIn("false_tracking", leaked)
        self.assertNotIn("target-P3", leaked)
        self.assertNotIn("p3_paranoia_loop.png", leaked)

        target_clan = self.visibility.project_part_for_viewer(
            part,
            {"viewer_id": "phantom", "viewer_clan": "phantom_mesh", "audience_scope": "player"},
        )
        self.assertEqual(target_clan["visibility_level"], "contained_hidden")
        self.assertFalse(target_clan["identity_visible"])

    def test_active_part_is_full_for_target_clan_and_limited_for_others(self):
        part = self.set_active("E1", owner="echo_owner")
        clan_view = self.visibility.project_part_for_viewer(
            part,
            {"viewer_id": "echo_ally", "viewer_clan": "echo_freedom", "audience_scope": "player"},
        )
        self.assertEqual(clan_view["visibility_level"], "full_clan")
        self.assertEqual(clan_view["viewer_relation"], "clan_own_active")
        self.assertEqual(clan_view["part_code"], "E1")
        self.assertEqual(clan_view["ability_code"], "expose")

        foreign = self.visibility.project_part_for_viewer(
            part,
            {"viewer_id": "virex", "viewer_clan": "virex", "audience_scope": "player"},
        )
        self.assertEqual(foreign["visibility_level"], "active_foreign")
        self.assertEqual(foreign["viewer_relation"], "foreign_active")
        self.assertEqual(foreign["module_state"], "active")
        self.assertEqual(foreign["location_visibility"], "exact")
        self.assertEqual(foreign["clan_code"], "echo_freedom")
        self.assertIsNone(foreign["part_id"])
        self.assertIsNone(foreign["part_code"])
        self.assertIsNone(foreign["name"])
        self.assertIsNone(foreign["machine_code"])
        self.assertIsNone(foreign["profession_code"])
        self.assertIsNone(foreign["ability_code"])
        leaked = self.encoded(foreign)
        self.assertNotIn("E1", leaked)
        self.assertNotIn("Breach Voice", leaked)
        self.assertNotIn("expose", leaked)

    def test_conflict_preserves_frozen_visibility(self):
        blocked = self.set_contained("P4", owner="main", territory_clan="virex")
        contested = self.repo.update_part(
            blocked["part_id"],
            conflict_state="contested",
            frozen_status="contained",
            conflict_id="conflict-1",
        )
        projected = self.visibility.project_part_for_viewer(
            contested,
            {"viewer_id": "robot", "viewer_clan": "sentinel_order", "audience_scope": "player"},
        )
        self.assertTrue(projected["contested"])
        self.assertEqual(projected["module_state"], "blocked")
        self.assertEqual(projected["visibility_level"], "contained_hidden")
        self.assertIn("frozen_visibility_context", projected)

    def test_player_snapshot_omits_internal_recovery_data_and_hidden_values(self):
        public = self.set_public("V1")
        hidden = self.set_contained("P3", owner="main", territory_clan="virex")
        active = self.set_active("E1", owner="echo_owner")
        pooled = self.part("S1")
        self.repo.create_reservation(
            self.cycle["cycle_id"],
            pooled["part_id"],
            "target-reserved",
            "operator",
            "virex",
            expires_at=future_iso(),
        )
        snapshot = self.repo.build_internal_snapshot(self.cycle["cycle_id"])
        projected = self.visibility.build_snapshot_for_viewer(
            snapshot,
            {"viewer_id": "other_virex", "viewer_clan": "virex", "audience_scope": "player"},
        )
        self.assertEqual(projected["projection"], "viewer_visibility")
        self.assertEqual(projected["visibility_version"], VISIBILITY_VERSION)
        self.assertNotIn("active_reservations", projected)
        self.assertNotIn("topology", projected)
        self.assertEqual(len(projected["parts"]), 3)
        serialized = self.encoded(projected)
        self.assertNotIn("target-reserved", serialized)
        self.assertNotIn("ring_order", serialized)
        self.assertNotIn("anchor_snapshot_json", serialized)
        self.assertNotIn("P3", serialized)
        self.assertNotIn("Paranoia Loop", serialized)
        self.assertNotIn("false_tracking", serialized)

    def test_connection_projection_hides_active_to_undiscovered_neighbor(self):
        code_a, code_b, _connection = self.connected_pair()
        self.set_active(code_a)
        snapshot = self.repo.build_internal_snapshot(self.cycle["cycle_id"])
        projected = self.visibility.build_snapshot_for_viewer(
            snapshot,
            {"viewer_id": "main", "viewer_clan": "virex", "audience_scope": "player"},
        )
        serialized = self.encoded(projected["connections"])
        self.assertNotIn(code_b, serialized)
        self.assertFalse([item for item in projected["connections"] if item.get("state") != "inactive"])

    def test_connection_projection_renders_half_and_full_states(self):
        code_a, code_b, connection = self.connected_pair()
        self.set_active(code_a)
        self.set_public(code_b)
        snapshot = self.repo.build_internal_snapshot(self.cycle["cycle_id"])
        projected = self.visibility.build_snapshot_for_viewer(
            snapshot,
            {"viewer_id": "main", "viewer_clan": "virex", "audience_scope": "player"},
        )
        half = next(item for item in projected["connections"] if item["connection_id"] == connection["connection_id"])
        self.assertEqual(half["state"], "half_from_a")
        self.assertTrue(half["can_show_on_map"])
        self.assertEqual(half["integrity"], 50)
        self.assertIn("public_connection_id", half)
        self.assertIsNotNone(half["from_latitude"])
        self.assertIsNotNone(half["to_longitude"])

        self.set_active(code_b)
        snapshot = self.repo.build_internal_snapshot(self.cycle["cycle_id"])
        projected = self.visibility.build_snapshot_for_viewer(
            snapshot,
            {"viewer_id": "main", "viewer_clan": "virex", "audience_scope": "player"},
        )
        active = next(item for item in projected["connections"] if item["connection_id"] == connection["connection_id"])
        self.assertEqual(active["state"], "active")
        self.assertEqual(active["integrity"], 100)
        self.assertEqual(active["flow_direction"], "a_to_b")

    def test_connection_projection_keeps_inactive_technical_state_off_map(self):
        code_a, code_b, connection = self.connected_pair()
        self.set_public(code_a)
        self.set_public(code_b)
        snapshot = self.repo.build_internal_snapshot(self.cycle["cycle_id"])
        projected = self.visibility.build_snapshot_for_viewer(
            snapshot,
            {"viewer_id": "main", "viewer_clan": "virex", "audience_scope": "player"},
        )
        inactive = next(item for item in projected["connections"] if item["connection_id"] == connection["connection_id"])
        self.assertEqual(inactive["state"], "inactive")
        self.assertFalse(inactive["can_show_on_map"])
        self.assertEqual(inactive["integrity"], 0)

    def test_territory_control_summary_does_not_leak_hidden_part_identity(self):
        hidden = self.set_contained("P3", owner="main", territory_clan="virex")
        projected = self.visibility.project_territory_component_for_viewer(
            {"territory_id": "territory-blocking", "parts": [hidden]},
            {"viewer_id": "other_virex", "viewer_clan": "virex", "audience_scope": "player"},
        )
        self.assertTrue(projected["contains_ghost_part"])
        self.assertEqual(projected["ghost_part_count"], 1)
        self.assertFalse(projected["ghost_part_identity_visible"])
        serialized = self.encoded(projected)
        self.assertNotIn("P3", serialized)
        self.assertNotIn("Paranoia Loop", serialized)

    def test_media_event_fact_hides_owner_only_identity(self):
        public_fact = self.visibility.project_event_fact_for_audience(
            {
                "event_type": "ghostnetwork.part_blocked",
                "territory_contains_part": True,
                "owner_clan": "virex",
                "part_code": "P3",
                "part_name": "Paranoia Loop",
                "target_clan": "phantom_mesh",
                "public_entity_id": "ghost-node:abc",
            },
            {"audience_scope": "public"},
        )
        self.assertTrue(public_fact["territory_contains_part"])
        self.assertIsNone(public_fact["part_code"])
        self.assertIsNone(public_fact["part_name"])
        self.assertIsNone(public_fact["target_clan"])
        self.assertNotIn("Paranoia Loop", self.encoded(public_fact))

        owner_fact = self.visibility.project_event_fact_for_audience(
            {
                "event_type": "ghostnetwork.part_blocked",
                "territory_contains_part": True,
                "owner_clan": "virex",
                "part_code": "P3",
                "part_name": "Paranoia Loop",
                "target_clan": "phantom_mesh",
            },
            {"audience_scope": "owner"},
        )
        self.assertEqual(owner_fact["part_code"], "P3")
        self.assertEqual(owner_fact["part_name"], "Paranoia Loop")

    def test_projection_cache_key_is_viewer_scoped(self):
        self.set_public("V1")
        snapshot = self.repo.build_internal_snapshot(self.cycle["cycle_id"])
        one = self.visibility.build_snapshot_for_viewer(
            snapshot,
            {"viewer_id": "main", "viewer_clan": "virex", "audience_scope": "player"},
        )
        two = self.visibility.build_snapshot_for_viewer(
            snapshot,
            {"viewer_id": "other", "viewer_clan": "sentinel_order", "audience_scope": "player"},
        )
        self.assertNotEqual(one["cache_key"], two["cache_key"])

    def test_service_keeps_internal_recovery_for_admin_and_player_projection_for_viewer(self):
        self.set_public("V1")
        service = GhostNetworkService(repository=self.repo)
        self.assertEqual(service.get_snapshot_for_viewer("admin")["projection"], "internal_recovery")
        player_projection = service.get_snapshot_for_viewer(
            {"viewer_id": "main", "viewer_clan": "virex", "audience_scope": "player"}
        )
        self.assertEqual(player_projection["projection"], "viewer_visibility")
        self.assertIn("parts", player_projection)


if __name__ == "__main__":
    unittest.main()
