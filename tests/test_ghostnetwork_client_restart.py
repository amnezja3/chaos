import os
import tempfile
import unittest
from unittest.mock import patch, Mock

import run
from database import (db_connect, UserStore, UserIdentityProjectionStore,
    UserCapabilityProjectionStore, PlayerInventoryStore, WalletBalanceStore,
    InstrumentedConnection, reset_hot_path_metrics, get_hot_path_metrics, restore_hot_path_metrics)
from ghostnetwork.show import GhostSignalShowService, GhostGameplayLocked
from session_generation_store import SessionGenerationStore, SessionGenerationStateError
from scripts.migrate_desktop_boot_projection import migrate
import test_ghostnetwork_runtime_endgame as runtime_fixture
from test_ghostnetwork_suite_snapshot import valid_profile


class GhostClientRestartTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "game.sqlite3")

    def rollover(self, path=None):
        repo, service, cycle, _ = runtime_fixture.GhostNetworkRuntimeEndgameTest.prepare_stabilizing_cycle(path or self.path)
        repo.update_cycle(cycle["cycle_id"], stabilization_until="2000-01-01T00:00:00+00:00")
        show = repo.get_signal_show_for_cycle(cycle["cycle_id"])
        repo.update_signal_show(show["show_id"], show_ends_at="2000-01-01T00:00:00+00:00")
        result = service.rollover_stabilized_cycle(cycle["cycle_id"])
        self.assertTrue(result["ok"], result)
        return repo, service, cycle

    def test_epoch_commits_with_successor_and_retry_does_not_duplicate(self):
        repo, service, cycle = self.rollover()
        first = repo.get_client_restart()
        self.assertTrue(first)
        self.assertEqual(first["payload"]["next_cycle_id"], repo.get_active_cycle()["cycle_id"])
        service.rollover_stabilized_cycle(cycle["cycle_id"])
        self.assertEqual(repo.get_client_restart(), first)
        self.assertEqual(len(repo.list_events_by_types(cycle["cycle_id"], ["ghost.client_restart_required"])), 1)

    def test_rollover_failure_does_not_publish_epoch(self):
        repo, service, cycle, _ = runtime_fixture.GhostNetworkRuntimeEndgameTest.prepare_stabilizing_cycle(self.path)
        self.assertFalse(service.rollover_stabilized_cycle(cycle["cycle_id"])["ok"])
        self.assertIsNone(repo.get_client_restart())

    def test_crash_publishing_epoch_rolls_back_successor_and_show_completion(self):
        repo, service, cycle, _ = runtime_fixture.GhostNetworkRuntimeEndgameTest.prepare_stabilizing_cycle(self.path)
        repo.update_cycle(cycle["cycle_id"], stabilization_until="2000-01-01T00:00:00+00:00")
        with patch.object(service.show, "publish_client_restart", side_effect=RuntimeError("crash")):
            with self.assertRaises(RuntimeError):
                service.rollover_stabilized_cycle(cycle["cycle_id"])
        self.assertEqual(repo.get_active_cycle()["cycle_id"], cycle["cycle_id"])
        self.assertEqual(repo.get_signal_show_for_cycle(cycle["cycle_id"])["status"], "active")
        self.assertIsNone(repo.get_client_restart())
        self.assertTrue(service.rollover_stabilized_cycle(cycle["cycle_id"])["ok"])

    def test_receipt_requires_boot_and_current_lineage_and_is_idempotent(self):
        store = SessionGenerationStore(self.path)
        store.activate("lineage", "generation", "alice", reason="test")
        with self.assertRaises(SessionGenerationStateError):
            store.acknowledge_restart("lineage", "generation", "alice", "epoch", "token")
        store.prepare_restart_boot("lineage", "generation", "alice", "epoch", "token")
        with self.assertRaises(SessionGenerationStateError):
            store.acknowledge_restart("lineage", "generation", "alice", "epoch", "wrong")
        self.assertFalse(store.acknowledge_restart("lineage", "generation", "alice", "epoch", "token")["idempotent"])
        self.assertTrue(store.acknowledge_restart("lineage", "generation", "alice", "epoch", "token")["idempotent"])
        store.activate("other-lineage", "other-generation", "alice", reason="replaced")
        with self.assertRaises(SessionGenerationStateError):
            store.acknowledge_restart("lineage", "generation", "alice", "epoch", "token")
        store.activate("lineage", "bob-generation", "bob", reason="account switch")
        store.prepare_restart_boot("lineage", "bob-generation", "bob", "epoch", "bob-token")
        self.assertFalse(store.acknowledge_restart("lineage", "bob-generation", "bob", "epoch", "bob-token")["idempotent"])

    def test_old_document_is_rejected_even_after_another_tab_acknowledges(self):
        repo, service, cycle = self.rollover()
        epoch = service.show.restart_projection()["epoch"]
        store = SessionGenerationStore(self.path)
        store.activate("lineage", "generation", "alice", reason="test")
        store.prepare_restart_boot("lineage", "generation", "alice", epoch, "token")
        store.acknowledge_restart("lineage", "generation", "alice", epoch, "token")
        with patch.object(run, "get_ghostsignal_show_service", return_value=service.show):
            for provided in ("", "old"):
                with run.app.test_request_context("/hack-action", method="POST", headers={"X-Chaos-Ghost-Epoch": provided}):
                    run.session["user"] = "alice"
                    self.assertEqual(run.block_gameplay_writes_during_ghostsignal_show().status_code, 423)
                    with self.assertRaises(GhostGameplayLocked):
                        run.assert_ghostsystem_epoch()
            with run.app.test_request_context("/hack-action", method="POST", headers={"X-Chaos-Ghost-Epoch": epoch}):
                run.session["user"] = "alice"
                self.assertIsNone(run.block_gameplay_writes_during_ghostsignal_show())
            with run.app.test_request_context("/", method="POST"):
                # Identity was established by login, not by an old document.
                run.session["user"] = "alice"
                self.assertEqual(run.reject_old_ghostsystem_response(run.redirect("/desktop")).status_code, 302)
            with run.app.test_request_context("/map"):
                run.session["user"] = "alice"
                run.g.session_generation_user = "alice"
                self.assertEqual(run.reject_old_ghostsystem_response(run.jsonify(ok=True)).status_code, 302)

    def test_desktop_snapshot_is_bounded_for_small_and_35mb_profiles(self):
        from ghostnetwork import GhostNetworkRepository
        counts = []
        for padding in (0, 35_000_000):
            path = os.path.join(self.tmp.name, str(padding) + ".sqlite3")
            users = UserStore(path, seed_path=os.path.join(self.tmp.name, "absent"))
            profile = valid_profile(padding="x" * padding)
            profile["desktop_settings"] = {"wallpaper": "wall-1", "icon_positions": {"mapa": {"x": 40, "y": 60}}}
            username = profile["username"]
            users.save_profile_guarded(profile, expected_revision=0, source="test.boot", allow_create=True)
            identity = UserIdentityProjectionStore(path)
            capabilities = UserCapabilityProjectionStore(path)
            inventory = PlayerInventoryStore(path)
            wallet = WalletBalanceStore(path)
            repo, service, _ = self.rollover(path)
            show = service.show
            sessions = SessionGenerationStore(path)
            sessions.activate("lineage", "generation", username, reason="test.boot")
            execute = InstrumentedConnection.execute
            count = [0]
            def counted(conn, sql, *args, **kwargs):
                self.assertNotIn("profile_json", sql.lower())
                count[0] += 1
                return execute(conn, sql, *args, **kwargs)
            token = reset_hot_path_metrics()
            try:
                with patch.object(run, "identity_projection_store", identity), \
                     patch.object(run, "capability_projection_store", capabilities), \
                     patch.object(run, "player_inventory_store", inventory), \
                     patch.object(run, "wallet_balance_store", wallet), \
                     patch.object(run, "session_generation_store", sessions), \
                     patch.object(run, "get_ghostsignal_show_service", return_value=show), \
                     patch.object(run, "sync_session_profile", side_effect=AssertionError("heavy profile")), \
                     patch.object(InstrumentedConnection, "execute", counted), \
                     run.app.test_request_context("/api/profile/desktop"):
                    run.session["user"] = username
                    run.session[run.SESSION_LINEAGE_KEY] = "lineage"
                    run.session[run.SESSION_GENERATION_KEY] = "generation"
                    data = run.update_profile_desktop().get_json()
                    self.assertEqual(data["desktop_settings"]["wallpaper"], "wall-1")
                    self.assertNotIn("padding", data)
                    self.assertTrue(data["signal_registry_available"])
                    self.assertTrue(data["restart_boot_token"])
                    ack = sessions.acknowledge_restart("lineage", "generation", username,
                        data["client_restart"]["epoch"], data["restart_boot_token"])
                    self.assertTrue(ack["acknowledged"])
                metrics = get_hot_path_metrics()
            finally:
                restore_hot_path_metrics(token)
            for key in ("profile_full_read", "profile_full_write", "profile_bytes", "all_user_profile_scan"):
                self.assertEqual(metrics[key], 0, key)
            counts.append(count[0])
        self.assertEqual(counts[0], counts[1])
        self.assertLess(counts[0], 35)

    def test_request_started_before_rollover_cannot_commit_or_return_old_response(self):
        from concurrent.futures import ThreadPoolExecutor
        from ghostnetwork import GhostNetworkRepository
        show = GhostSignalShowService(GhostNetworkRepository(self.path))
        with db_connect(self.path) as conn:
            conn.execute("CREATE TABLE late_gameplay (value TEXT)")
        with patch.object(run, "get_ghostsignal_show_service", return_value=show), \
             patch.object(run, "current_request_profile_precommit_guard", return_value=Mock()), \
             patch.object(run.session_generation_store, "build_transaction_precommit_guard", return_value=Mock()), \
             run.app.test_request_context("/hack-action", method="POST", json={}):
            run.session["user"] = "alice"
            self.assertIsNone(run.block_gameplay_writes_during_ghostsignal_show())
            run.g.session_generation_user = "alice"
            run.bind_request_profile_precommit_guard()
            # Worker has no request ContextVar. It commits a complete rollover
            # while this older request is still doing work outside its writer.
            with ThreadPoolExecutor(max_workers=1) as worker:
                worker.submit(self.rollover).result()
            with self.assertRaises(GhostGameplayLocked):
                with db_connect(self.path) as conn:
                    conn.execute("INSERT INTO late_gameplay VALUES ('old world')")
            response = run.reject_old_ghostsystem_response(run.jsonify(ok=True))
            self.assertEqual(response.status_code, 423)
            self.assertEqual(response.get_json()["error"], "ghostsystem_restart_required")
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM late_gameplay").fetchone()[0], 0)

    def test_operator_migration_is_readonly_by_default_and_repeatable(self):
        users = UserStore(self.path, seed_path=os.path.join(self.tmp.name, "absent"))
        profile = valid_profile()
        users.save_profile_guarded(profile, expected_revision=0, source="test.migration", allow_create=True)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE user_identity_projection SET desktop_boot_json=NULL")
        self.assertEqual(migrate(self.path)["pending"], 1)
        self.assertEqual(migrate(self.path)["pending"], 1)
        self.assertEqual(migrate(self.path, apply=True)["written"], 1)
        self.assertEqual(migrate(self.path, apply=True)["written"], 0)
        # An old process may update identity after the first migration batch.
        # Its stale boot payload must be detected, not silently accepted.
        with db_connect(self.path) as conn:
            conn.execute("UPDATE user_identity_projection SET desktop_boot_json=json_set(desktop_boot_json, '$.source_profile_revision', 0)")
        from database import ProfileRecoveryRequired
        with self.assertRaises(ProfileRecoveryRequired):
            UserIdentityProjectionStore(self.path).get_desktop_boot(profile["username"])
        self.assertEqual(migrate(self.path)["pending"], 1)
        self.assertEqual(migrate(self.path, apply=True)["written"], 1)

    def test_operator_migration_upgrades_old_schema_without_changing_profile(self):
        import sqlite3
        import json
        from contextlib import closing
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute("CREATE TABLE users (username TEXT, profile_json TEXT, profile_revision INT, profile_checksum TEXT, profile_integrity_status TEXT)")
            conn.execute("CREATE TABLE user_identity_projection (username TEXT PRIMARY KEY, source_profile_revision INT, source_profile_checksum TEXT)")
            source = json.dumps({"desktop_settings": {"wallpaper": "wall-2"}, "respect": 17})
            conn.execute("INSERT INTO users VALUES ('alice', ?, 1, 'checksum', 'valid')", (source,))
            conn.execute("INSERT INTO user_identity_projection VALUES ('alice', 1, 'checksum')")
            conn.commit()
        self.assertTrue(migrate(self.path)["schema_change"])
        self.assertEqual(migrate(self.path, apply=True)["written"], 1)
        with closing(sqlite3.connect(self.path)) as conn:
            self.assertEqual(conn.execute("SELECT profile_json FROM users").fetchone()[0], source)
            projection = json.loads(conn.execute("SELECT desktop_boot_json FROM user_identity_projection").fetchone()[0])
            self.assertEqual(projection["respect"], 17)
            self.assertEqual(projection["desktop_settings"]["wallpaper"], "wall-2")


if __name__ == "__main__":
    unittest.main()
