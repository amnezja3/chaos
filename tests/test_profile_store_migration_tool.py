import json
import shutil
import tempfile
import unittest
from pathlib import Path

from database import (
    PlayerInventoryStore,
    PlayerPositionStore,
    PlayerTargetRuntimeStore,
    WalletBalanceStore,
    db_connect,
    dumps_json,
    init_db,
    utc_now,
)
from tools import profile_store_migration as migration


class ProfileStoreMigrationToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="chaos_profile_migration_"))
        self.db_path = str(self.tmpdir / "game.sqlite3")
        init_db(self.db_path)
        self.username = "main"
        self.profile = {
            "username": self.username,
            "password": "test-password",
            "salt": "",
            "level": 1,
            "hackcoins": 1234,
            "respect": 0,
            "exp": "0 / 1000",
            "inventory": [],
            "hacked": [],
            "desktop_settings": {},
            "security": {},
            "territory_stats": {},
            "current_position": {"lat": 52.23, "lng": 21.01},
            "aimed_target": {
                "target_id": "POI-TEST",
                "label": "Test target",
                "lat": 52.24,
                "lng": 21.02,
                "security": {"scan": False},
                "actions_allowed": {"scan_ports": True},
            },
            "operations": [
                {
                    "operation_id": "op-test",
                    "type": "scan_ports",
                    "target_name": "Test target",
                    "status": "running",
                    "file_type": "credentials",
                }
            ],
            "system_messages": [
                {"title": "Legacy message", "message": "queued", "status": "new"}
            ],
            "apps": [{"id": "app-vmap", "name": "V-MAP", "status": "installed"}],
            "files": {
                "tools": [
                    {
                        "id": "tool-vmap",
                        "app_id": "app-vmap",
                        "name": "V-MAP.sh",
                        "size": 12,
                    }
                ]
            },
            "storage_capacity": 512,
            "storage_used": 64,
            "storage_unit": "MB",
        }
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO users(username, password, salt, profile_json, created_at, updated_at)
                VALUES (?, '', '', ?, ?, ?)
                """,
                (self.username, dumps_json(self.profile), utc_now(), utc_now()),
            )

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_migrate_user_seeds_runtime_stores_and_registry(self):
        result = migration.migrate_user(self.db_path, "test-migration", self.username)

        self.assertIn(result["status"], {"verified", "warning"})
        self.assertEqual(
            PlayerTargetRuntimeStore(self.db_path).get_active_target(self.username)["target_id"],
            "POI-TEST",
        )
        self.assertEqual(
            PlayerPositionStore(self.db_path).get_position(self.username),
            {"lat": 52.23, "lng": 21.01},
        )
        self.assertEqual(WalletBalanceStore(self.db_path).get_balance(self.username), 1234)
        inventory = PlayerInventoryStore(self.db_path).snapshot(self.username)
        self.assertEqual(len(inventory["apps"]), 1)
        self.assertEqual(len(inventory["files"]["tools"]), 1)

        registry = migration.get_registry(self.db_path, "test-migration", self.username)
        self.assertIsNotNone(registry)
        self.assertIn(registry["status"], {"verified", "warning"})
        self.assertTrue(registry["source_checksum"])
        self.assertTrue(registry["result_checksum"])

        with db_connect(self.db_path) as conn:
            source = conn.execute(
                "SELECT profile_checksum FROM users WHERE username = ?",
                (self.username,),
            ).fetchone()["profile_checksum"]
            canonical_migration = conn.execute(
                """
                SELECT status FROM profile_store_migrations
                WHERE migration_id = 'wallet_canonical_v1' AND username = ?
                """,
                (self.username,),
            ).fetchone()
        self.assertEqual(source, registry["source_checksum"])
        self.assertEqual("applied", canonical_migration["status"])

    def test_wallet_seed_rejects_profile_without_matching_integrity_evidence(self):
        # First initialize integrity metadata, then simulate an out-of-band
        # profile mutation which deliberately leaves the checksum stale.
        migration.get_user_rows(self.db_path, self.username)
        wallet = WalletBalanceStore(self.db_path)
        before_balance = wallet.get_balance(self.username)
        with db_connect(self.db_path) as conn:
            before_events = conn.execute(
                "SELECT COUNT(*) FROM wallet_balance_events WHERE username = ?",
                (self.username,),
            ).fetchone()[0]
        tampered = dict(self.profile)
        tampered["hackcoins"] = 999999
        with db_connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET profile_json = ? WHERE username = ?",
                (dumps_json(tampered), self.username),
            )

        result = migration.migrate_user(
            self.db_path,
            "test-invalid-wallet-evidence",
            self.username,
        )

        self.assertEqual("failed", result["status"])
        self.assertIn("cannot seed canonical wallet", result["reason"].lower())
        with db_connect(self.db_path) as conn:
            after_events = conn.execute(
                "SELECT COUNT(*) FROM wallet_balance_events WHERE username = ?",
                (self.username,),
            ).fetchone()[0]
        self.assertEqual(1234, before_balance)
        self.assertEqual(before_balance, wallet.get_balance(self.username))
        self.assertEqual(before_events, after_events)

    def test_dry_run_reports_without_writing_registry(self):
        class Args:
            db = self.db_path
            username = self.username

        self.assertEqual(migration.command_dry_run(Args()), 0)
        self.assertIsNone(migration.get_registry(self.db_path, migration.DEFAULT_MIGRATION_ID, self.username))

    def test_write_commands_require_backup_manifest_or_override(self):
        class Args:
            write = True
            backup_manifest = ""
            allow_without_backup = False

        with self.assertRaises(SystemExit):
            migration.require_write(Args())

        Args.backup_manifest = str(self.tmpdir / "manifest.json")
        Path(Args.backup_manifest).write_text("{}", encoding="utf-8")
        migration.require_write(Args())

    def test_rollback_user_restores_pre_migration_runtime_rows(self):
        migration_id = "test-rollback"
        result = migration.migrate_user(self.db_path, migration_id, self.username)
        self.assertIn(result["status"], {"verified", "warning"})
        WalletBalanceStore(self.db_path).credit(
            self.username,
            66,
            transaction_key="test:post-migration-credit",
            reason="test.credit",
        )

        rollback = migration.rollback_user(self.db_path, migration_id, self.username)
        replay = migration.rollback_user(self.db_path, migration_id, self.username)
        self.assertEqual("rolled_back", rollback["status"])
        self.assertFalse(rollback["wallet_duplicate"])
        self.assertTrue(replay["wallet_duplicate"])
        self.assertEqual(PlayerTargetRuntimeStore(self.db_path).get_active_target(self.username), {})
        self.assertEqual(PlayerPositionStore(self.db_path).get_position(self.username), {})
        self.assertEqual(WalletBalanceStore(self.db_path).get_balance(self.username), 1234)
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (self.username,),
            ).fetchone()
            recovery_events = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM wallet_balance_events
                WHERE username = ? AND transaction_key = ?
                """,
                (self.username, rollback["wallet_transaction_key"]),
            ).fetchone()["count"]
        self.assertEqual(json.loads(row["profile_json"])["aimed_target"]["target_id"], "POI-TEST")
        self.assertEqual(1, recovery_events)
        self.assertEqual(
            migration.get_registry(self.db_path, migration_id, self.username)["status"],
            "rolled_back",
        )


if __name__ == "__main__":
    unittest.main()
