import json
import os
import tempfile
import unittest
from unittest.mock import patch

from database import (InstrumentedConnection, db_connect, reset_hot_path_metrics,
                      get_hot_path_metrics, restore_hot_path_metrics)
from ghostnetwork import GhostNetworkRepository, GhostSignalShowService
from ghostnetwork.show_manifest import build_manifest, SCENES


class ShowManifestTest(unittest.TestCase):
    def test_complete_storyboard_and_canonical_machine_relations(self):
        manifest = build_manifest({})
        scenes = manifest["scenes"]
        self.assertEqual(len({s["id"] for s in scenes}), len(SCENES))
        self.assertEqual(scenes[0]["start"], 0)
        self.assertEqual(scenes[-1]["end"], 900)
        for left, right in zip(scenes, scenes[1:]):
            self.assertEqual(left["end"], right["start"])
        self.assertEqual(len(manifest["catalog"]["parts"]), 20)
        for machine in manifest["catalog"]["machines"]:
            parts = [p for p in manifest["catalog"]["parts"] if p["machine_code"] == machine["code"]]
            self.assertEqual({p["part_code"] for p in parts}, set(machine["part_codes"]))
            self.assertEqual(len(parts), 5)
        self.assertLess(len(json.dumps(manifest).encode()), 32768)
        self.assertFalse(manifest["signal_confirmed"])
        self.assertFalse(manifest["audio"]["replay"])

    def test_polling_projection_has_constant_queries_with_35mb_profile_and_payload(self):
        query_counts = []
        for padding in (8, 35 * 1024 * 1024):
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "manifest.sqlite3")
                repo = GhostNetworkRepository(path)
                cycle = repo.create_cycle(cycle_id="c", signal_number=1, ghostsystem_version=1, status="transmitting")
                signal = repo.create_signal({"signal_id": "s", "cycle_id": "c", "status": "transmitting",
                                             "payload": {"private": "x" * padding}})
                service = GhostSignalShowService(repo)
                service.ensure_for_signal(signal, cycle)
                with db_connect(path) as conn:
                    conn.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, profile_json TEXT)")
                    conn.execute("INSERT INTO users(username, profile_json) VALUES ('viewer', ?)", (json.dumps({"private": "x" * padding}),))
                queries = []
                original = InstrumentedConnection.execute
                def measured(conn, sql, *args, **kwargs):
                    self.assertNotIn("profile_json", sql.lower())
                    self.assertNotIn("payload_json", sql.lower())
                    self.assertNotIn("select * from ghost_signals", sql.lower())
                    queries.append(sql)
                    return original(conn, sql, *args, **kwargs)
                token = reset_hot_path_metrics()
                try:
                    with patch.object(InstrumentedConnection, "execute", measured):
                        manifest = service.projection_for_cycle("c")["show_manifest"]
                    metrics = get_hot_path_metrics()
                finally:
                    restore_hot_path_metrics(token)
                for key in ("profile_full_read", "profile_full_write", "profile_bytes", "all_user_profile_scan"):
                    self.assertEqual(metrics[key], 0, key)
                query_counts.append(len(queries))
                self.assertEqual(sum(sql.lstrip().lower().startswith("select") for sql in queries), 2)
                self.assertFalse(manifest["signal_confirmed"])
                repo.mark_signal_sent("s")
                self.assertFalse(service.projection_for_cycle("c")["show_manifest"]["signal_confirmed"])
                repo.append_event("ghost.signal_sent", cycle_id="c", dedupe_key="ghost:signal_sent:c", entity_id="s")
                confirmed = service.projection_for_cycle("c")["show_manifest"]
                self.assertTrue(confirmed["signal_confirmed"])
                self.assertNotIn("private", json.dumps(confirmed))
                self.assertFalse(confirmed["ranking_available"])
        # Each of the two readers also executes its connection PRAGMAs.
        self.assertEqual(query_counts, [6, 6])


if __name__ == "__main__":
    unittest.main()
