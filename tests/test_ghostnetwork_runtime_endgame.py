import os
import tempfile
import unittest

import run
from database import dumps_json
from ghostnetwork import GhostCycleService, GhostNetworkRepository, GhostNetworkService


class GhostNetworkRuntimeEndgameTest(unittest.TestCase):
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

            second = run.maybe_finalize_ghostnetwork_cycle(service)
            self.assertEqual(second["status"], "not_ready")
            self.assertEqual(len(repo.list_signals_for_cycle(cycle["cycle_id"])), 1)
            self.assertEqual(len(repo.list_cycles()), 1)


if __name__ == "__main__":
    unittest.main()
