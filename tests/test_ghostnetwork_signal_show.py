import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from ghostnetwork import GhostNetworkRepository, GhostSignalShowService


class GhostSignalShowTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = GhostNetworkRepository(db_path=os.path.join(self.tmp.name, "show.sqlite3"))
        self.cycle = self.repo.create_cycle(
            cycle_id="ghostnetwork_0007", signal_number=7, ghostsystem_version=7,
            status="active", source_version="1.0.7", next_version="1.0.8",
        )
        self.signal = self.repo.create_signal({
            "signal_id": "internal-signal-seven", "cycle_id": self.cycle["cycle_id"],
            "signal_number": 7, "source_version": 7, "next_version": 8,
            "sent_at": "2026-09-09T10:00:00+00:00",
        })
        self.show = GhostSignalShowService(self.repo, {
            "duration_seconds": 900, "phase_policy_version": "test-v1",
        })

    def tearDown(self):
        self.tmp.cleanup()

    def test_show_is_durable_and_idempotent(self):
        first = self.show.ensure_for_signal(self.signal, self.cycle)
        second = self.show.ensure_for_signal(
            self.signal, self.cycle, started_at="2099-01-01T00:00:00+00:00"
        )
        self.assertEqual(first["show_id"], second["show_id"])
        self.assertEqual(first["show_started_at"], second["show_started_at"])
        self.assertTrue(second["idempotent"])

    def test_phase_policy_uses_server_time(self):
        stored = self.show.ensure_for_signal(self.signal, self.cycle)
        start = datetime.fromisoformat(stored["show_started_at"])
        expected = [
            (1, "network_lock"), (90, "machine_synchronization"),
            (240, "signal_transmission"), (450, "world_consumption"),
            (600, "results"), (800, "ghostsystem_restart"),
        ]
        for seconds, code in expected:
            phase = self.show.phase_at(stored, start + timedelta(seconds=seconds))
            self.assertEqual(phase["code"], code)

    def test_viewer_projection_contains_no_internal_ids(self):
        stored = self.show.ensure_for_signal(self.signal, self.cycle)
        projection = self.show.projection_for_cycle(
            self.cycle["cycle_id"], now=stored["show_started_at"]
        )
        self.assertTrue(projection["show_active"])
        self.assertEqual(projection["signal_public_id"], "GHOSTSIGNAL-0007")
        self.assertNotIn("signal_id", projection)
        self.assertNotIn("show_id", projection)

    def test_elapsed_show_holds_final_phase_until_settlement(self):
        stored = self.show.ensure_for_signal(self.signal, self.cycle)
        after = datetime.fromisoformat(stored["show_ends_at"]) + timedelta(seconds=1)
        projection = self.show.projection_for_cycle(self.cycle["cycle_id"], after)
        self.assertTrue(projection["show_active"])
        self.assertTrue(projection["show_time_elapsed"])
        self.assertEqual(projection["show_phase"]["code"], "ghostsystem_restart")

    def test_closed_cycle_does_not_release_unfinished_show(self):
        self.show.ensure_for_signal(self.signal, self.cycle)
        self.repo.update_cycle(self.cycle["cycle_id"], status="closed")
        self.assertTrue(self.show.get_for_viewer()["gameplay_locked"])
        self.show.complete_for_cycle(self.cycle["cycle_id"])
        self.assertTrue(self.show.get_for_viewer()["gameplay_locked"])
        self.repo.create_cycle(cycle_id="ghostnetwork_0008", signal_number=8,
            ghostsystem_version=8, status="active")
        self.assertFalse(self.show.get_for_viewer()["gameplay_locked"])
        self.assertFalse(self.show.get_for_viewer()["show_active"])


if __name__ == "__main__":
    unittest.main()
