import os
import sqlite3
import gc
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ghostnetwork import GhostCycleService, GhostDropPolicy, GhostNetworkRepository, GhostNetworkService
from tools.ghostnetwork_runtime import build_guarded_profile_callbacks, execute


class GhostNetworkRuntimeFoundationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "ghostnetwork.sqlite3")

    def tearDown(self):
        self.tmp.cleanup()

    def service(self, enabled=False, chance=0.0):
        repo = GhostNetworkRepository(db_path=self.db_path)
        return GhostNetworkService(
            repository=repo,
            drop_policy=GhostDropPolicy(enabled=enabled, chance=chance),
        )

    def test_readiness_is_read_only_and_reports_missing_cycle(self):
        service = self.service()
        report = service.get_runtime_readiness()
        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "NOT READY")
        self.assertIn("no_active_cycle", report["errors"])
        self.assertEqual(service.repository.list_cycles(), [])

    def test_bootstrap_dry_run_does_not_create_cycle_then_apply_is_idempotent(self):
        dry, code = execute(SimpleNamespace(command="bootstrap", db_path=self.db_path, apply=False, json=True))
        self.assertEqual(code, 0)
        self.assertTrue(dry["dry_run"])
        self.assertEqual(dry["action"], "create_active_cycle")
        self.assertEqual(GhostNetworkRepository(db_path=self.db_path).list_cycles(), [])

        with patch("ghostnetwork.service.GHOSTNETWORK_DROPS_ENABLED", True), patch(
            "ghostnetwork.service.GHOSTNETWORK_DROP_CHANCE", 0.25
        ):
            first, first_code = execute(SimpleNamespace(command="bootstrap", db_path=self.db_path, apply=True, json=True))
            second, second_code = execute(SimpleNamespace(command="bootstrap", db_path=self.db_path, apply=True, json=True))
        self.assertEqual((first_code, second_code), (0, 0))
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        repo = GhostNetworkRepository(db_path=self.db_path)
        self.assertEqual(len(repo.list_cycles()), 1)
        self.assertEqual(len(repo.list_parts(repo.get_active_cycle()["cycle_id"])), 20)

    def test_invalid_enabled_drop_configuration_blocks_readiness(self):
        repo = GhostNetworkRepository(db_path=self.db_path)
        GhostCycleService(repository=repo).ensure_active_cycle()
        service = GhostNetworkService(repository=repo)
        with patch("ghostnetwork.service.GHOSTNETWORK_DROPS_ENABLED", True), patch(
            "ghostnetwork.service.GHOSTNETWORK_DROP_CHANCE", 0.0
        ):
            report = service.get_runtime_readiness()
        self.assertFalse(report["ready"])
        self.assertIn("drops_enabled_without_valid_chance", report["errors"])

    def test_test_mode_is_rejected_in_production(self):
        repo = GhostNetworkRepository(db_path=self.db_path)
        GhostCycleService(repository=repo).ensure_active_cycle()
        service = GhostNetworkService(repository=repo)
        with patch("ghostnetwork.service.GHOSTNETWORK_DROPS_ENABLED", True), \
                patch("ghostnetwork.service.GHOSTNETWORK_DROP_CHANCE", 1.0), \
                patch("ghostnetwork.service.GHOSTNETWORK_RUNTIME_MODE", "production"), \
                patch("ghostnetwork.service.GHOSTNETWORK_TEST_MODE", True):
            report = service.get_runtime_readiness()
        self.assertFalse(report["ready"])
        self.assertIn("test_mode_forbidden_in_production", report["errors"])

    def test_legacy_raw_telemetry_is_migrated_to_bounded_aggregates(self):
        legacy_path = os.path.join(self.tmp.name, "legacy-telemetry.sqlite3")
        with sqlite3.connect(legacy_path) as conn:
            conn.execute(
                """
                CREATE TABLE ghost_pipeline_telemetry (
                    telemetry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cycle_id TEXT NOT NULL DEFAULT '', phase TEXT NOT NULL,
                    outcome TEXT NOT NULL, created_at TEXT NOT NULL
                )
                """
            )
            conn.executemany(
                "INSERT INTO ghost_pipeline_telemetry(cycle_id, phase, outcome, created_at) VALUES ('c1','aim','reserved',?)",
                [("2026-01-01T00:00:00Z",), ("2026-01-01T00:00:01Z",)],
            )
        repo = GhostNetworkRepository(db_path=legacy_path)
        summary = repo.get_pipeline_telemetry_summary("c1")
        self.assertEqual(summary["aim"]["reserved"], 2)
        with repo._conn() as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(ghost_pipeline_telemetry)")}
        self.assertIn("outcome_count", columns)
        self.assertNotIn("telemetry_id", columns)
        del repo
        gc.collect()

    def test_pipeline_telemetry_counts_outcomes_without_hidden_payload(self):
        service = self.service(enabled=True, chance=1.0)
        GhostCycleService(repository=service.repository).ensure_active_cycle()
        target = {
            "target_id": "map:51.1:17.0:runtime-target",
            "lat": 51.1,
            "lng": 17.0,
            "source_type": "shop",
            "target_mode": "standard",
            "hackable": True,
        }
        player = {"player_id": "alice", "clan_code": "virex"}
        aimed = service.on_target_aimed(player, target)
        self.assertEqual(aimed["status"], "reserved")
        captured = service.on_target_hacked(player, target, result={"target_captured": True})
        self.assertEqual(captured["status"], "discovered")
        summary = service.get_runtime_readiness()["telemetry"]
        self.assertEqual(summary["aim"]["reserved"], 1)
        self.assertEqual(summary["capture"]["discovered"], 1)
        with service.repository._conn() as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(ghost_pipeline_telemetry)").fetchall()}
        self.assertNotIn("part_id", columns)
        self.assertNotIn("payload_json", columns)

    def test_operator_runtime_callbacks_update_existing_profile_with_revision_cas(self):
        class ExistingUserStore:
            def __init__(self):
                self.profile = {"username": "alice", "respect": 9}
                self.revision = 17
                self.guarded_calls = []

            def get_profile_with_revision(self, username):
                self.assert_username = username
                return {
                    "state": "valid",
                    "profile": dict(self.profile),
                    "profile_revision": self.revision,
                }

            def save_profile(self, _profile):
                raise AssertionError("legacy existing-profile writer must not run")

            def save_profile_guarded(self, profile, *, expected_revision, source):
                self.guarded_calls.append((expected_revision, source))
                if expected_revision != self.revision:
                    raise AssertionError("stale revision")
                self.revision += 1
                self.profile = dict(profile)
                return {
                    "applied": True,
                    "profile": dict(self.profile),
                    "profile_revision": self.revision,
                }

        users = ExistingUserStore()
        load_profile, save_profile = build_guarded_profile_callbacks(users)
        profile = load_profile("alice")
        profile["respect"] = 14
        save_profile(profile)

        self.assertEqual(users.profile["respect"], 14)
        self.assertEqual(
            users.guarded_calls,
            [(17, "operator.ghostnetwork_runtime")],
        )


if __name__ == "__main__":
    unittest.main()
