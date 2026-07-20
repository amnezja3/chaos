import os
import tempfile
import unittest

from ghostnetwork import (
    GhostCycleService,
    GhostModuleStateService,
    GhostNetworkRepository,
    GhostNetworkService,
)


class GhostModuleStateServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        self.modules = GhostModuleStateService(repository=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def part(self, index=0):
        return self.repo.list_parts(self.cycle["cycle_id"])[index]

    def machine_parts(self):
        first = self.part(0)
        return [
            part for part in self.repo.list_parts(self.cycle["cycle_id"])
            if part["machine_code"] == first["machine_code"]
        ]

    def set_public(self, part):
        return self.repo.update_part(
            part["part_id"],
            status="public",
            target_id=f"target-{part['part_id']}",
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

    def set_contained(self, part, owner="robot", territory_clan="virex", territory_id="territory-foreign"):
        return self.repo.update_part(
            part["part_id"],
            status="contained",
            target_id=f"target-{part['part_id']}",
            latitude=52.25,
            longitude=21.0,
            discovered_by="main",
            discovered_clan="virex",
            conflict_state="none",
            frozen_status="",
            conflict_id="",
            territory_id=territory_id,
            territory_owner_id=owner,
            territory_clan=territory_clan,
        )

    def set_active(self, part, owner="main", territory_id="territory-own"):
        return self.repo.update_part(
            part["part_id"],
            status="active",
            target_id=f"target-{part['part_id']}",
            latitude=52.25,
            longitude=21.0,
            discovered_by="main",
            discovered_clan="virex",
            conflict_state="none",
            frozen_status="",
            conflict_id="",
            territory_id=territory_id,
            territory_owner_id=owner,
            territory_clan=part["clan_code"],
        )

    def test_neutral_blocked_active_and_viewer_relations(self):
        neutral = self.set_public(self.part(0))
        neutral_state = self.modules.resolve_part_module_state(neutral)
        self.assertEqual(neutral_state["module_state"], "neutral")
        self.assertFalse(neutral_state["ability_enabled"])
        self.assertEqual(neutral_state["territory_id"], "")
        self.assertEqual(self.modules.resolve_part_viewer_relation(neutral, {"username": "main"}), "public_neutral")

        blocked = self.set_contained(self.part(1), owner="main", territory_clan="sentinel_order")
        blocked_state = self.modules.resolve_part_module_state(blocked)
        self.assertEqual(blocked_state["module_state"], "blocked")
        self.assertEqual(blocked_state["territory_owner_id"], "main")
        self.assertFalse(blocked_state["ability_enabled"])
        self.assertEqual(
            self.modules.resolve_part_viewer_relation(blocked, {"username": "main", "clan_code": "virex"}),
            "self_foreign_blocked",
        )
        self.assertEqual(
            self.modules.resolve_part_viewer_relation(blocked, {"username": "other", "clan_code": "sentinel_order"}),
            "foreign_blocked",
        )

        active = self.set_active(self.part(2), owner="main")
        active_state = self.modules.resolve_part_module_state(active)
        self.assertEqual(active_state["module_state"], "active")
        self.assertTrue(active_state["ability_enabled"])
        self.assertEqual(
            self.modules.resolve_part_viewer_relation(active, {"username": "main", "clan_code": active["clan_code"]}),
            "self_own_active",
        )
        self.assertEqual(
            self.modules.resolve_part_viewer_relation(active, {"username": "ally", "clan_code": active["clan_code"]}),
            "clan_own_active",
        )
        self.assertEqual(
            self.modules.resolve_part_viewer_relation(active, {"username": "enemy", "clan_code": "sentinel_order"}),
            "foreign_active",
        )

    def test_conflict_preserves_previous_module_state(self):
        active = self.set_active(self.part(0))
        active_frozen = self.repo.update_part(
            active["part_id"],
            conflict_state="contested",
            frozen_status="active",
            conflict_id="conflict-active",
        )
        active_state = self.modules.resolve_part_module_state(active_frozen)
        self.assertEqual(active_state["module_state"], "active")
        self.assertEqual(active_state["conflict_state"], "contested")

        blocked = self.set_contained(self.part(1), territory_clan="sentinel_order")
        blocked_frozen = self.repo.update_part(
            blocked["part_id"],
            conflict_state="contested",
            frozen_status="contained",
            conflict_id="conflict-blocked",
        )
        blocked_state = self.modules.resolve_part_module_state(blocked_frozen)
        self.assertEqual(blocked_state["module_state"], "blocked")
        self.assertEqual(blocked_state["conflict_state"], "contested")

    def test_machine_online_offline_and_network_ready(self):
        parts = self.machine_parts()
        machine_code = parts[0]["machine_code"]
        for part in parts[:4]:
            self.set_active(part)
        four = self.modules.resolve_machine_progress(self.cycle["cycle_id"], machine_code)
        self.assertEqual(four["parts_active"], 4)
        self.assertFalse(four["machine_online"])
        self.modules.record_machine_progress_if_changed(self.cycle["cycle_id"], machine_code)

        self.set_active(parts[4])
        online = self.modules.record_machine_progress_if_changed(self.cycle["cycle_id"], machine_code)
        self.assertTrue(online["progress"]["machine_online"])
        events = self.repo.list_events(self.cycle["cycle_id"], limit=1000)
        self.assertTrue(any(event["event_type"] == "ghost.machine_online" for event in events))

        self.set_public(parts[4])
        offline = self.modules.record_machine_progress_if_changed(self.cycle["cycle_id"], machine_code)
        self.assertFalse(offline["progress"]["machine_online"])
        events = self.repo.list_events(self.cycle["cycle_id"], limit=1000)
        self.assertTrue(any(event["event_type"] == "ghost.machine_offline" for event in events))
        no_duplicate = self.modules.record_machine_progress_if_changed(self.cycle["cycle_id"], machine_code)
        self.assertFalse(no_duplicate["changed"])

        for part in self.repo.list_parts(self.cycle["cycle_id"]):
            self.set_active(part)
        ready = self.modules.resolve_cycle_progress(self.cycle["cycle_id"])
        self.assertEqual(ready["parts_active"], 20)
        self.assertTrue(ready["network_ready"])
        self.set_public(self.part(0))
        not_ready = self.modules.resolve_cycle_progress(self.cycle["cycle_id"])
        self.assertFalse(not_ready["network_ready"])

    def test_cluster_flags_and_service_wrapper(self):
        own = self.set_active(self.part(0), owner="main", territory_id="territory-cluster")
        foreign_part = next(
            part for part in self.repo.list_parts(self.cycle["cycle_id"])
            if part["clan_code"] != own["clan_code"]
        )
        foreign = self.set_contained(
            foreign_part,
            owner="robot",
            territory_clan="sentinel_order",
            territory_id="territory-cluster",
        )
        contract = self.modules.build_cluster_ghost_component_contract(
            self.cycle["cycle_id"],
            "territory-cluster",
            viewer={"username": "main", "clan_code": own["clan_code"]},
        )
        self.assertEqual(contract["ghost_components"]["total"], 2)
        self.assertEqual(contract["ghost_components"]["active"], 1)
        self.assertEqual(contract["ghost_components"]["blocked"], 1)
        self.assertTrue(contract["contains_own_clan_part"])
        self.assertTrue(contract["contains_foreign_clan_part"])
        self.assertTrue(contract["contains_active_part"])
        self.assertTrue(contract["contains_blocked_part"])
        self.assertTrue(contract["contains_ghost_part"])
        self.assertTrue(contract["ghost_anchor_protected"])
        self.assertIsNotNone(self.repo.get_part(foreign["part_id"]))

        service = GhostNetworkService(repository=self.repo)
        wrapped = service.resolve_part_module_state(own["part_id"])
        self.assertEqual(wrapped["module_state"], "active")
        report = service.get_modules_status_report(self.cycle["cycle_id"], include_parts=True)
        self.assertTrue(report["ok"])
        self.assertIn("machines", report)
        self.assertIn("parts", report)


if __name__ == "__main__":
    unittest.main()
