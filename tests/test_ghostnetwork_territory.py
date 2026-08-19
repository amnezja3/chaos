import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostPartLifecycleService, GhostTerritoryAdapter


def future_iso(minutes=10):
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


class GhostTerritoryAdapterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")
        self.repo = GhostNetworkRepository(db_path=self.db_path)
        self.cycle = GhostCycleService(repository=self.repo).ensure_active_cycle()["cycle"]
        self.lifecycle = GhostPartLifecycleService(repository=self.repo)
        self.adapter = GhostTerritoryAdapter(repository=self.repo, lifecycle=self.lifecycle)

    def tearDown(self):
        self.tmp.cleanup()

    def player(self, clan="virex"):
        return {
            "player_id": "main",
            "username": "main",
            "clan_code": clan,
        }

    def target(self, target_id, lat=52.25, lng=21.0):
        return {
            "target_id": target_id,
            "lat": lat,
            "lng": lng,
            "label": target_id,
            "source_type": "shop",
            "target_mode": "standard",
        }

    def reserve_and_discover(self, target_id, lat=52.25, lng=21.0, player_clan="virex"):
        part = self.repo.list_reservable_parts(self.cycle["cycle_id"], excluded_clan=player_clan)[0]
        reservation = self.lifecycle.reserve_part(
            self.cycle["cycle_id"],
            part["part_id"],
            target_id,
            "main",
            player_clan,
            expires_at=future_iso(),
        )
        result = self.lifecycle.discover_part(
            reservation["reservation_id"],
            player=self.player(player_clan),
            target=self.target(target_id, lat=lat, lng=lng),
            operation_id=f"op-{target_id}",
            result={"target_captured": True},
        )
        self.assertEqual(result["status"], "discovered")
        return result["part"]

    def territory(self, owner_clan, territory_id="territory-a", owner="owner-a", version=1, conflict_id="", pillar_count=3):
        return {
            "territory_event_id": f"event-{territory_id}-{version}",
            "territory_id": territory_id,
            "owner_username": owner,
            "owner_clan": owner_clan,
            "status": "stable",
            "vertices": [
                {"lat": 52.20, "lng": 20.90},
                {"lat": 52.20, "lng": 21.10},
                {"lat": 52.30, "lng": 21.10},
                {"lat": 52.30, "lng": 20.90},
            ],
            "pillar_count": pillar_count,
            "conflict_id": conflict_id,
            "territory_state_version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def test_foreign_stable_territory_contains_part(self):
        part = self.reserve_and_discover("target-foreign")
        report = self.adapter.on_territory_stabilized(self.territory("sentinel_order", version=3))

        self.assertEqual(report["changed_count"], 1)
        updated = self.repo.get_part(part["part_id"])
        self.assertEqual(updated["status"], "contained")
        self.assertEqual(updated["territory_clan"], "sentinel_order")
        self.assertEqual(updated["territory_state_version"], 3)

    def test_matching_clan_stable_territory_activates_part_and_is_idempotent(self):
        part = self.reserve_and_discover("target-own")
        own_territory = self.territory(part["clan_code"], owner="main", version=4)

        first = self.adapter.on_territory_stabilized(own_territory)
        version_after_first = self.repo.get_state_version(self.cycle["cycle_id"])
        second = self.adapter.on_territory_stabilized(own_territory)
        version_after_second = self.repo.get_state_version(self.cycle["cycle_id"])

        self.assertEqual(first["changed_count"], 1)
        self.assertEqual(second["changed_count"], 0)
        self.assertEqual(version_after_second, version_after_first)
        updated = self.repo.get_part(part["part_id"])
        self.assertEqual(updated["status"], "active")
        self.assertEqual(updated["territory_clan"], part["clan_code"])

    def test_too_few_pillars_keeps_part_public_without_territory_fields(self):
        part = self.reserve_and_discover("target-small")
        report = self.adapter.on_territory_stabilized(self.territory("sentinel_order", pillar_count=2))

        self.assertEqual(report["changed_count"], 0)
        updated = self.repo.get_part(part["part_id"])
        self.assertEqual(updated["status"], "public")
        self.assertEqual(updated["territory_id"], "")
        self.assertEqual(updated["territory_clan"], "")

    def test_contest_preserves_base_status_and_resolution_updates_status(self):
        part = self.reserve_and_discover("target-contest")
        self.adapter.on_territory_stabilized(self.territory("sentinel_order", version=5))

        contested = self.territory("sentinel_order", version=6, conflict_id="conflict-a")
        contested["status"] = "contested"
        contest_report = self.adapter.on_territory_contested(contested)
        frozen = self.repo.get_part(part["part_id"])
        self.assertEqual(contest_report["changed_count"], 1)
        self.assertEqual(frozen["status"], "contained")
        self.assertEqual(frozen["conflict_state"], "contested")
        self.assertEqual(frozen["frozen_status"], "contained")

        resolved = self.territory(part["clan_code"], owner="main", version=7)
        resolution_report = self.adapter.on_territory_stabilized(resolved)
        updated = self.repo.get_part(part["part_id"])
        self.assertEqual(resolution_report["changed_count"], 1)
        self.assertEqual(updated["status"], "active")
        self.assertEqual(updated["conflict_state"], "none")

    def test_released_territory_decays_previous_parts_to_public(self):
        part = self.reserve_and_discover("target-release")
        terr = self.territory("sentinel_order", territory_id="territory-release", version=8)
        self.adapter.on_territory_stabilized(terr)
        self.assertEqual(self.repo.get_part(part["part_id"])["status"], "contained")

        released = dict(terr)
        released["territory_event_id"] = "event-release"
        released["status"] = "released"
        report = self.adapter.on_territory_released(released)

        self.assertEqual(report["changed_count"], 1)
        updated = self.repo.get_part(part["part_id"])
        self.assertEqual(updated["status"], "public")
        self.assertEqual(updated["territory_id"], "")

    def test_overlapping_stable_territories_mark_part_contested_without_random_owner(self):
        part = self.reserve_and_discover("target-overlap")
        foreign = self.territory("sentinel_order", territory_id="territory-foreign", owner="robot", version=9)
        own = self.territory(part["clan_code"], territory_id="territory-own", owner="main", version=10)

        outcome = self.adapter.resolve_part_territory(part, territories=[foreign, own])
        self.assertEqual(outcome["outcome"], "contested")

        report = self.adapter._apply_resolution([foreign, own], own, reason="test_overlap")
        updated = self.repo.get_part(part["part_id"])
        self.assertEqual(report["changed_count"], 1)
        self.assertEqual(updated["conflict_state"], "contested")
        self.assertEqual(updated["territory_owner_id"], "")

    def test_recovery_dry_run_and_apply_reconcile_only_when_requested(self):
        part = self.reserve_and_discover("target-reconcile")
        terr = self.territory("sentinel_order", territory_id="territory-reconcile", version=11)

        dry = self.adapter.reconcile_parts_with_territories(
            self.cycle["cycle_id"],
            territories=[terr],
            apply=False,
        )
        self.assertEqual(dry["count"], 1)
        self.assertEqual(self.repo.get_part(part["part_id"])["status"], "public")

        applied = self.adapter.reconcile_parts_with_territories(
            self.cycle["cycle_id"],
            territories=[terr],
            apply=True,
        )
        self.assertEqual(applied["count"], 1)
        self.assertEqual(self.repo.get_part(part["part_id"])["status"], "contained")

    def test_reconcile_records_each_real_status_oscillation_once(self):
        part = self.reserve_and_discover("target-oscillation")
        terr = self.territory(
            "sentinel_order",
            territory_id="territory-oscillation",
            version=12,
        )

        self.adapter.reconcile_parts_with_territories(territories=[terr], apply=True)
        self.adapter.reconcile_parts_with_territories(territories=[], apply=True)
        self.adapter.reconcile_parts_with_territories(territories=[terr], apply=True)

        events = self.repo.list_events(self.cycle["cycle_id"], limit=1000)
        contained = [event for event in events if event["event_type"] == "ghost.part_contained"]
        revealed = [event for event in events if event["event_type"] == "ghost.part_revealed"]
        self.assertEqual(len(contained), 2)
        self.assertEqual(len(revealed), 1)
        self.assertEqual(len({event["dedupe_key"] for event in contained}), 2)
        self.assertEqual(self.repo.get_part(part["part_id"])["status"], "contained")


if __name__ == "__main__":
    unittest.main()
