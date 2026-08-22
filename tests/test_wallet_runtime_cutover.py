import copy
import unittest
from unittest.mock import Mock, call, patch

import run
from database import WalletNotInitialized


class WalletRuntimeCutoverTests(unittest.TestCase):
    def test_wallet_dashboard_reports_blocked_canonical_migration_as_recovery(self):
        with run.app.test_request_context("/api/wallet"):
            run.session["user"] = "alice"
            with patch.object(
                run.wallet_store,
                "get_wallet",
                side_effect=WalletNotInitialized(
                    "Canonical wallet migration is blocked.",
                    reason="migration_blocked",
                ),
            ):
                response, status = run.api_wallet()

        self.assertEqual(409, status)
        self.assertEqual("wallet_not_initialized", response.get_json()["reason"])

    def test_wallet_delta_is_a_pure_canonical_publisher(self):
        event = {"version": 1}
        with patch.object(run.wallet_balance_store, "get_balance", return_value=321) as get_balance, \
                patch.object(run.wallet_balance_store, "set_balance", side_effect=AssertionError("legacy writer")), \
                patch.object(run.delta_bus, "record_change", return_value=event) as publish:
            result = run.record_wallet_balance_delta(
                "alice",
                999999,
                reason="test",
                dedupe_key="wallet:test:alice",
            )

        self.assertEqual(result, event)
        get_balance.assert_called_once_with("alice")
        self.assertEqual(publish.call_args.args[3]["balance"], 321)

    def test_wallet_transfer_requires_and_forwards_client_transaction_key(self):
        transfer_result = {
            "balance": 90,
            "recipient_balance": 10,
            "currency": "HC",
            "duplicate": False,
            "transaction": {"id": 1, "amount": 10, "peer": "bob"},
        }
        wallet_after = {"transactions": [], "ledger": [], "ledger_audit": {}}
        with patch.object(run.wallet_store, "transfer", return_value=transfer_result) as transfer, \
                patch.object(run.wallet_store, "get_wallet", return_value=wallet_after), \
                patch.object(run.wallet_balance_store, "get_balance", side_effect=lambda username: 90 if username == "alice" else 10), \
                patch.object(run, "sync_session_profile", return_value={"username": "alice", "hackcoins": 90}), \
                patch.object(run.delta_bus, "record_change", return_value={"version": 1}):
            with run.app.test_request_context(
                "/api/wallet/transfer",
                method="POST",
                json={"to": "bob", "amount": 10},
            ):
                run.session["user"] = "alice"
                missing, missing_status = run.api_wallet_transfer()
                missing.status_code = missing_status
            with run.app.test_request_context(
                "/api/wallet/transfer",
                method="POST",
                json={"to": "bob", "amount": 10, "transaction_key": "wallet-ui:one"},
                headers={"X-Idempotency-Key": "wallet-ui:one"},
            ):
                run.session["user"] = "alice"
                response = run.api_wallet_transfer()

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["transaction_key"], "wallet-ui:one")
        transfer.assert_called_once_with(
            "alice",
            "bob",
            10,
            "",
            transaction_key="wallet-ui:one",
        )

    def test_manual_ghost_exchange_pays_before_removing_file(self):
        file_entry = {
            "id": "file-1",
            "name": "dump.net",
            "file_category": "network",
            "sellable": True,
            "metadata": {"quality_score": 80},
        }
        profile = {
            "hackcoins": 1,
            "files": {"network": [file_entry], "market": []},
            "market_history": [],
        }
        observed = []

        def payout(settlement):
            observed.append([item["id"] for item in profile["files"]["network"]])
            return {
                "balance": 77,
                "transaction_key": "ghost_exchange:manual:alice:file-1",
            }

        sale = run.sell_ghost_exchange_file(profile, "alice", "file-1", payout_callback=payout)

        self.assertEqual(observed, [["file-1"]])
        self.assertEqual(profile["files"]["network"], [])
        self.assertEqual(profile["hackcoins"], 77)
        self.assertEqual(
            profile["market_history"][0]["wallet_transaction_key"],
            "ghost_exchange:manual:alice:file-1",
        )
        self.assertEqual(sale["wallet"]["balance"], 77)

    def test_ghost_exchange_dashboard_uses_canonical_balance_without_file_id(self):
        profile = {
            "username": "alice",
            "hackcoins": 9999,
            "files": {"network": [], "market": []},
            "market_history": [],
            "operations": [],
        }
        with run.app.test_request_context("/api/ghost-exchange"):
            run.session["user"] = "alice"
            with patch.object(run.user_store, "get_profile", return_value=profile), \
                    patch.object(run, "refresh_and_persist_operations", side_effect=lambda _username, current: current), \
                    patch.object(run, "canonical_wallet_balance", return_value=44):
                response = run.api_ghost_exchange()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["balance"], 44)

    def test_ghost_exchange_sell_retry_reuses_file_receipt_and_credit_key(self):
        profile = {
            "username": "alice",
            "hackcoins": 10,
            "files": {
                "network": [{
                    "id": "file-retry",
                    "name": "retry.net",
                    "file_category": "network",
                    "sellable": True,
                    "metadata": {"quality_score": 80},
                }],
                "market": [],
            },
            "market_history": [],
            "operations": [],
            "storage_capacity": 512,
            "storage_used": 1,
        }
        balance = {"value": 10}
        credits = {}

        def credit(_username, amount, transaction_key, **_kwargs):
            duplicate = transaction_key in credits
            if not duplicate:
                credits[transaction_key] = int(amount)
                balance["value"] += int(amount)
            return {
                "balance": balance["value"],
                "transaction_key": transaction_key,
                "duplicate": duplicate,
            }

        class FakeManager:
            def __init__(self, _username):
                pass

            def update_profile(self, updates):
                profile.update(copy.deepcopy(updates))

        common_patches = (
            patch.object(run.user_store, "get_profile", return_value=profile),
            patch.object(run, "refresh_and_persist_operations", side_effect=lambda _username, current: current),
            patch.object(run, "canonical_wallet_balance", side_effect=lambda _username: balance["value"]),
            patch.object(run.wallet_balance_store, "credit", side_effect=credit),
            patch.object(run, "UserProfileManager", FakeManager),
            patch.object(run, "record_wallet_balance_delta", return_value=None),
            patch.object(run, "record_storage_delta", return_value=[]),
            patch.object(run, "record_ghost_exchange_delta", return_value=None),
            patch.object(run, "add_cyberner_direct_notification", return_value=None),
        )
        for item in common_patches:
            item.start()
        try:
            with run.app.test_request_context(
                "/api/ghost-exchange/sell",
                method="POST",
                json={"file_id": "file-retry"},
            ):
                run.session["user"] = "alice"
                first = run.api_ghost_exchange_sell()
            with run.app.test_request_context(
                "/api/ghost-exchange/sell",
                method="POST",
                json={"file_id": "file-retry"},
            ):
                run.session["user"] = "alice"
                second = run.api_ghost_exchange_sell()
        finally:
            for item in reversed(common_patches):
                item.stop()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.get_json()["duplicate"])
        self.assertEqual(list(credits), ["ghost_exchange:manual:alice:file-retry"])
        self.assertEqual(len(profile["market_history"]), 1)

    def test_financial_sniffer_reserves_usage_before_canonical_transfer(self):
        access = {"id": 7, "hacked_until": "2099-01-01T00:00:00"}
        order = []
        pending = {"result": "pending:silent", "amount": 8, "duplicate": False}
        access_store = Mock()
        access_store.get_active_access.return_value = access
        access_store.access_key.return_value = "7:2099-01-01T00:00:00"
        access_store.get_tool_usage.return_value = None
        access_store.record_tool_usage.side_effect = lambda *args, **kwargs: order.append("reserve") or pending
        access_store.complete_tool_usage.side_effect = lambda *args, **kwargs: order.append("complete") or {"amount": 8}
        wallet = Mock()
        wallet.technical_transfer.side_effect = lambda *args, **kwargs: order.append("transfer") or {
            "amount": 8,
            "source_balance": 92,
            "target_balance": 28,
            "transaction_id": 3,
            "duplicate": False,
        }
        profiles = {
            "attacker": {"username": "attacker", "level": 10, "respect": 20, "apps": [{"id": "financialSniffer"}]},
            "victim": {"username": "victim", "level": 5, "respect": 5},
        }

        with run.app.test_request_context(
            "/api/player-hack/tool/use",
            method="POST",
            json={"tool_id": "financialSniffer", "victim_username": "victim"},
        ):
            run.session["user"] = "attacker"
            with patch.object(run, "player_hack_access_store", access_store), \
                    patch.object(run, "wallet_store", wallet), \
                    patch.object(run.user_store, "get_profile", side_effect=lambda username: copy.deepcopy(profiles.get(username))), \
                    patch.object(run, "canonical_wallet_balance", side_effect=lambda username: 100 if username == "victim" else 20), \
                    patch.object(run, "app_is_installed", return_value=True), \
                    patch.object(run, "randint", return_value=8), \
                    patch.object(run, "random", return_value=1.0), \
                    patch.object(run, "record_wallet_balance_delta", return_value=None):
                response = run.api_player_hack_tool_use()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(order, ["reserve", "transfer", "complete"])
        transaction_key = wallet.technical_transfer.call_args.kwargs["transaction_key"]
        self.assertTrue(transaction_key.startswith("financial_sniffer:"))

    def test_googleplex_replay_does_not_charge_twice_or_write_profile_hc(self):
        app = {
            "id": "unit_tool",
            "name": "Unit Tool",
            "price": 30,
            "interface": "terminal",
            "type": "scanner",
            "file_size": 1,
            "disk_usage": 1,
        }
        profile = {
            "username": "alice",
            "nick": "Alice",
            "hackcoins": 9999,
            "level": 10,
            "respect": 10,
            "apps": [],
            "files": {"tools": []},
            "storage_capacity": 512,
            "storage_used": 0,
            "storage_unit": "MB",
            "system_messages": [],
        }
        balances = {"alice": 100, "admin": 0}
        manager_updates = []

        class FakeManager:
            def __init__(self, _username):
                pass

            def update_profile(self, updates):
                manager_updates.append(copy.deepcopy(updates))
                profile.update(copy.deepcopy(updates))

        def transfer(_source, _target, amount, note="", transaction_key=""):
            balances["alice"] -= int(amount)
            balances["admin"] += int(amount)
            return {
                "balance": balances["alice"],
                "recipient_balance": balances["admin"],
                "currency": "HC",
                "duplicate": False,
                "transaction": {"id": 1, "transaction_key": transaction_key},
            }

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "get_app_catalog", return_value=[app]), \
                patch.object(run.resources_store, "get", return_value=[]), \
                patch.object(run.resources_store, "set", return_value=None), \
                patch.object(run, "ensure_purchase_account_profile", return_value={"username": "admin"}), \
                patch.object(run.user_store, "get_profile", return_value={"username": "admin"}), \
                patch.object(run.wallet_store, "transfer", side_effect=transfer) as transfer_mock, \
                patch.object(run, "canonical_wallet_balance", side_effect=lambda username: balances.get(username, 0)), \
                patch.object(run, "record_storage_delta", return_value=[]), \
                patch.object(run, "record_apps_delta", return_value=None), \
                patch.object(run, "record_wallet_balance_delta", return_value=None), \
                patch.object(run, "add_cyberner_direct_notification", return_value=None), \
                patch.object(run.system_message_store, "add_message", return_value=({}, True)):
            with run.app.test_request_context("/install-app", method="POST", json={"app_id": "unit_tool"}):
                run.session["user"] = "alice"
                first = run.install_app()
            with run.app.test_request_context("/install-app", method="POST", json={"app_id": "unit_tool"}):
                run.session["user"] = "alice"
                second = run.install_app()

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.get_json()["duplicate"])
        self.assertEqual(balances, {"alice": 70, "admin": 30})
        self.assertEqual(transfer_mock.call_count, 1)
        self.assertTrue(manager_updates)
        self.assertNotIn("hackcoins", manager_updates[0])
        self.assertEqual(profile["apps"][0]["wallet_transaction_key"], "googleplex:purchase:alice:unit_tool")


if __name__ == "__main__":
    unittest.main()
