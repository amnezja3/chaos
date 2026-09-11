import hashlib
import json
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from database import db_connect
from ghostnetwork.ranking import GhostSignalRankingService
from tools.build_ghostsignal_show_preview import historical_manifest


class HistoricalPreviewTest(unittest.TestCase):
    def setUp(self):
        from test_ghostnetwork_signal_ranking import GhostSignalRankingTest
        self.fixture = GhostSignalRankingTest()
        self.fixture.setUp()
        self.repo = self.fixture.repo
        self.signal = self.fixture.transmit_cycle()
        GhostSignalRankingService(self.repo).finalize(self.signal["signal_id"])

    def tearDown(self):
        self.fixture.tearDown()

    def test_legacy_reconstruction_read_only_with_real_lineage_and_no_profiles(self):
        with db_connect(self.fixture.db_path) as conn:
            conn.execute("UPDATE ghost_signal_shows SET scene_snapshot_json='{}'")
        before = hashlib.sha256(Path(self.fixture.db_path).read_bytes()).hexdigest()
        with patch.object(type(self.repo), "_ensure_schema", side_effect=AssertionError("schema init forbidden")):
            manifest, report = historical_manifest(self.fixture.db_path, self.signal["cycle_id"])
        self.assertTrue(report["read_only"] and report["projection_reconstructed"])
        self.assertTrue(manifest["signal_confirmed"])
        self.assertEqual(manifest["cycle_history"]["settlement"]["rsp_total"], 180)
        self.assertEqual(len(manifest["cycle_history"]["parts"]), 20)
        self.assertNotIn("future_2108_timestamp", manifest["cycle_history"])
        self.assertNotIn("user_id", json.dumps(manifest))
        self.assertEqual(before, hashlib.sha256(Path(self.fixture.db_path).read_bytes()).hexdigest())
        self.assertEqual(self.repo.get_signal_show_for_signal(self.signal["signal_id"])["scene_snapshot"], {})
        partial = dict(manifest["cycle_history"])
        partial.pop("settlement")
        with db_connect(self.fixture.db_path) as conn:
            conn.execute("UPDATE ghost_signal_shows SET scene_snapshot_json=?", (json.dumps(partial),))
        _, report = historical_manifest(self.fixture.db_path, self.signal["cycle_id"])
        self.assertTrue(report["projection_reconstructed"])

    def test_corrupt_ranking_is_rejected(self):
        with db_connect(self.fixture.db_path) as conn:
            conn.execute("UPDATE ghost_signal_rankings SET snapshot_checksum='invalid'")
        with self.assertRaisesRegex(ValueError, "ranking_checksum_invalid"):
            historical_manifest(self.fixture.db_path, self.signal["cycle_id"])

    def test_inconsistent_cached_projection_is_rejected(self):
        with db_connect(self.fixture.db_path) as conn:
            conn.execute("UPDATE ghost_signal_shows SET scene_snapshot_json=json_set(scene_snapshot_json,'$.settlement.rsp_total',9999)")
        with self.assertRaisesRegex(ValueError, "stored_projection_mismatch:rsp_total"):
            historical_manifest(self.fixture.db_path, self.signal["cycle_id"])

    def test_missing_source_does_not_create_database(self):
        path = Path(self.fixture.tmp.name) / "missing.sqlite3"
        with self.assertRaises(sqlite3.OperationalError):
            historical_manifest(path, "missing")
        self.assertFalse(path.exists())

    def test_missing_sent_event_does_not_fall_back_to_demo(self):
        with db_connect(self.fixture.db_path) as conn:
            conn.execute("DELETE FROM ghost_part_events WHERE event_type='ghost.signal_sent'")
        with self.assertRaisesRegex(ValueError, "canonical_signal_sent_missing"):
            historical_manifest(self.fixture.db_path, self.signal["cycle_id"])
