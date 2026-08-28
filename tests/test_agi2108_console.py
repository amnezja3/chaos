import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import run
from database import (
    PlayerInventoryStore,
    ProfilePrecommitRejected,
    UserStore,
    WalletBalanceStore,
    get_hot_path_metrics,
    reset_hot_path_metrics,
    restore_hot_path_metrics,
    reset_request_transaction_precommit_guard,
    set_request_transaction_precommit_guard,
)
from ghostnetwork.llm.registry import resolve_ollama_task_policy


ROOT = Path(__file__).resolve().parents[1]


def _profile(username, hackcoins):
    return {
        "username": username,
        "password": "test-password",
        "salt": "test-salt",
        "nick": username,
        "email": f"{username}@example.test",
        "level": 1,
        "hackcoins": hackcoins,
        "respect": 0,
        "exp": "0 / 1000",
        "avatar": "/static/images/default_avatar.png",
        "clan": "Alpha",
        "fraction": {"id": "alpha"},
        "inventory": [],
        "apps": [],
        "files": {"tools": [], "download": []},
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
        "operations": [],
        "targets": [],
        "market_history": [],
        "product_purchases": [],
        "storage_upgrades": [],
        "ghostnetwork_reward_history": [],
        "risk_events": [],
        "storage_capacity": 100,
        "storage_used": 0,
        "system_messages": [],
        "launch_queue": [],
    }


class Agi2108ConsoleContractTest(unittest.TestCase):
    def setUp(self):
        self.product = next(
            item for item in run.PRO_SYSTEM_TOOLS
            if item.get("id") == "agi2108Console"
        )

    def test_approved_product_contract_is_exact(self):
        ingress = self.product["llm_ingress"]
        template = ingress["templates"][0]
        self.assertEqual(self.product["name"], "AGI 2108 Console")
        self.assertEqual(self.product["icon"], "⌬")
        self.assertEqual(self.product["price"], 10000)
        self.assertEqual(self.product["purchase_account"], "admin")
        self.assertTrue(self.product["bounded_install"])
        self.assertTrue(self.product["purchase_confirmation"])
        self.assertEqual(ingress["usage_cost_hc"], 0)
        self.assertEqual(ingress["rate_limit"], {"max_tasks": 5, "window_seconds": 3600})
        self.assertEqual(template["id"], "owner-analysis")
        self.assertEqual(template["target_medium"], "cyberner")
        self.assertEqual(template["input_fields"]["topic"]["max_length"], 120)

    def test_prompt_registry_has_only_backend_owned_policy(self):
        policy = resolve_ollama_task_policy(
            "googleplex_app", "owner-analysis", "cyberner"
        )
        self.assertIsNotNone(policy)
        self.assertEqual(policy.prompt_version, "cyberner-agi-2108-prompt-v1")
        self.assertEqual(policy.output_schema_version, "chaos-narrative-output-v1")
        self.assertEqual(policy.model_policy_version, "chaos-local-narrator-v1")

    def test_frontend_is_bounded_owner_console_without_model_body(self):
        source = (ROOT / "static" / "js" / "terminal.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")
        self.assertIn("function createAgi2108ConsoleApp()", source)
        self.assertIn("maxlength=\"120\"", source)
        self.assertIn("approved_template_id: 'owner-analysis'", source)
        self.assertIn("app_id: 'agi2108Console'", source)
        self.assertIn("agi2108:receipt:${username}", source)
        self.assertNotIn("receipt.body", source)
        self.assertNotIn("receipt.raw_output", source)
        self.assertIn(".agi2108-console-window", css)
        self.assertIn("overflow-y: auto", css)


class Agi2108BoundedInstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp.name, "agi2108.sqlite3")
        self.users = UserStore(
            self.db_path,
            seed_path=os.path.join(self.tmp.name, "missing-users.json"),
        )
        profiles = {}
        for username, balance in (("alice", 25000), ("admin", 0), ("bob", 25000)):
            profiles[username] = _profile(username, balance)
            self.users.save_profile_guarded(
                profiles[username],
                expected_revision=0,
                source="test.registration",
                allow_create=True,
            )
        self.wallet = WalletBalanceStore(self.db_path)
        self.inventory = PlayerInventoryStore(self.db_path)
        for username, profile in profiles.items():
            self.inventory.seed_from_profile(username, profile)
        self.app = dict(next(
            item for item in run.PRO_SYSTEM_TOOLS
            if item.get("id") == "agi2108Console"
        ))

    def tearDown(self):
        self.tmp.cleanup()

    def _purchase(self, username="alice"):
        key = f"googleplex:purchase:{username}:agi2108Console"

        def install(conn, transaction):
            del transaction
            return self.inventory.install_app_with_conn(
                conn, username, self.app, purchase_key=key
            )

        return self.wallet.transfer(
            username,
            "admin",
            10000,
            transaction_key=key,
            note="googleplex:agi2108Console",
            source="googleplex.bounded_install",
            transaction_callback=install,
        )

    def test_purchase_retry_and_uninstall_are_bounded_and_idempotent(self):
        first = self._purchase()
        replay = self._purchase()
        snapshot = self.inventory.snapshot("alice")
        locked_catalog = run.googleplex_catalog_payload(self.app, {
            "apps": snapshot["apps"],
            "hackcoins": self.wallet.get_balance("alice"),
            "level": 1,
            "respect": 0,
        })
        self.assertTrue(first["applied"])
        self.assertTrue(replay["duplicate"])
        self.assertEqual(self.wallet.get_balance("alice"), 15000)
        self.assertEqual(self.wallet.get_balance("admin"), 10000)
        self.assertTrue(self.inventory.has_app("alice", "agi2108Console"))
        self.assertEqual(snapshot["storage"]["used"], 16)
        self.assertEqual(len([
            item for item in snapshot["apps"]
            if item.get("id") == "agi2108Console"
        ]), 1)
        self.assertTrue(locked_catalog["installed"])
        self.assertTrue(locked_catalog["install_blocked_reason"])
        self.assertTrue(self.inventory.uninstall_app("alice", app_id="agi2108Console"))
        after = self.inventory.snapshot("alice")
        purchasable_catalog = run.googleplex_catalog_payload(self.app, {
            "apps": after["apps"],
            "hackcoins": 25000,
            "level": 1,
            "respect": 0,
        })
        self.assertFalse(self.inventory.has_app("alice", "agi2108Console"))
        self.assertEqual(after["storage"]["used"], 0)
        self.assertFalse(purchasable_catalog["installed"])
        self.assertEqual(purchasable_catalog["install_blocked_reason"], "")

    def test_precommit_rejection_rolls_back_payment_and_install(self):
        token = set_request_transaction_precommit_guard(
            lambda **_kwargs: (_ for _ in ()).throw(
                ProfilePrecommitRejected("session replaced")
            )
        )
        try:
            with self.assertRaises(ProfilePrecommitRejected):
                self._purchase("bob")
        finally:
            reset_request_transaction_precommit_guard(token)
        self.assertEqual(self.wallet.get_balance("bob"), 25000)
        self.assertEqual(self.wallet.get_balance("admin"), 0)
        self.assertFalse(self.inventory.has_app("bob", "agi2108Console"))

    def test_install_endpoint_does_not_read_or_write_heavy_profile(self):
        heavy_profile = {"username": "alice", "blob": "x" * (35 * 1024 * 1024)}
        messages = Mock()
        run.app.config["TESTING"] = True
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        metrics_token = reset_hot_path_metrics()
        try:
            with patch.object(run, "wallet_balance_store", self.wallet), \
                    patch.object(run, "player_inventory_store", self.inventory), \
                    patch.object(run, "system_message_store", messages), \
                    patch.object(run, "get_app_catalog", return_value=[self.app]), \
                    patch.object(run, "record_storage_delta") as storage_delta, \
                    patch.object(run, "record_apps_delta") as apps_delta, \
                    patch.object(run, "record_wallet_balance_delta") as wallet_delta, \
                    patch.object(run, "sync_session_profile", side_effect=AssertionError("full profile read")) as sync_read, \
                    patch.object(run.user_store, "get_profile", side_effect=AssertionError("full profile read")) as full_read, \
                    patch.object(run.user_store, "list_profiles", side_effect=AssertionError("profile scan")) as full_scan, \
                    patch.object(run.user_store, "save_profile_guarded", side_effect=AssertionError("full profile write")) as full_write:
                self.assertGreater(len(heavy_profile["blob"]), 35_000_000)
                response = client.post("/install-app", json={"app_id": "agi2108Console"})
            metrics = get_hot_path_metrics()
        finally:
            restore_hot_path_metrics(metrics_token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "success")
        sync_read.assert_not_called()
        full_read.assert_not_called()
        full_scan.assert_not_called()
        full_write.assert_not_called()
        for key in (
            "profile_full_read",
            "profile_full_write",
            "profile_bytes",
            "all_user_profile_scan",
            "per_recipient_profile_read",
        ):
            self.assertEqual(metrics[key], 0, key)
        storage_delta.assert_called_once()
        apps_delta.assert_called_once()
        self.assertEqual(wallet_delta.call_count, 2)
        self.assertTrue(self.inventory.has_app("alice", "agi2108Console"))


if __name__ == "__main__":
    unittest.main()
