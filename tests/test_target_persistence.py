import unittest
import json
import os
import re
import sqlite3
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from unittest.mock import patch

import run
from database import AppActionReceiptStore, DevBugReportStore, GameStateDeltaBus, JsonResourceStore, MailStore, PlayerInventoryStore, PlayerOperationStore, PlayerTargetRuntimeStore, UserStore, WalletBalanceStore, WalletLedgerStore, WalletStore
from flask.testing import FlaskClient
from profileManagment import UserProfileManager
from session_generation_store import SessionGenerationStore
from werkzeug.datastructures import Headers
from run import (
    active_operations_from_operations,
    append_runtime_file_if_space,
    apply_operation_quality_to_files,
    build_generated_app,
    build_ghost_exchange_dashboard_payload,
    build_ghost_exchange_sector_payload,
    build_blacknet_world_facts_snapshot,
    build_blacknet_world_signals,
    build_blacknet_ollama_outbox,
    BLACKNET_ALLOWED_CTA_ACTIONS,
    build_storage_full_result,
    build_player_actor,
    can_store_runtime_file,
    cancel_profile_operation,
    collect_ghost_exchange_files,
    create_operations_for_app_action,
    display_target_label,
    ensure_files_inventory,
    filter_targets_by_position,
    finalize_vehicle_tracking_file,
    get_apps_for_map_action,
    googleplex_catalog_payload,
    is_market_eligible_file,
    market_sector_for_file,
    normalize_app_contract,
    normalize_file_market_status,
    normalize_profile_storage,
    operation_history_from_operations,
    profile_template_payload,
    queue_market_eligible_files,
    record_map_player_actor_delta,
    record_map_target_delta,
    refresh_market_runtime,
    refresh_operation_runtime,
    refresh_operations_runtime,
    resolve_player_actor_relation,
    resolve_app_required_off_state,
    target_position_key,
    targets_share_position,
    latest_blacknet_ollama_outbox,
    read_blacknet_ollama_outbox,
    update_blacknet_ollama_outbox_status,
    validate_generated_app_icon,
    validate_blacknet_ollama_outbox,
    write_blacknet_ollama_outbox,
)


class IsolatedFixtureSessionGenerationStore(SessionGenerationStore):
    """Keep generation checks authoritative across deliberately split test DBs.

    Production stores share one SQLite database and check the lineage through
    the transaction connection.  This legacy test module intentionally patches
    individual stores to separate temporary databases, so its fixture performs
    the same current-generation assertion against the dedicated fixture store.
    """

    def build_precommit_guard(self, lineage_secret, generation_secret, actor_username):
        expected_actor = str(actor_username or "").strip()

        def precommit_guard(*, conn, username, current_revision):
            del conn, username, current_revision
            self.assert_current(lineage_secret, generation_secret, expected_actor)

        return precommit_guard

    def build_transaction_precommit_guard(
        self,
        lineage_secret,
        generation_secret,
        actor_username,
    ):
        expected_actor = str(actor_username or "").strip()

        def precommit_guard(*, conn):
            del conn
            self.assert_current(lineage_secret, generation_secret, expected_actor)

        return precommit_guard


class SessionGenerationFixtureClient(FlaskClient):
    """Exercise authenticated endpoints with the production generation contract."""

    _DOCUMENT_PATHS = {"/desktop", "/map", "/dev"}

    @staticmethod
    def _bind_authenticated_generation(flask_session):
        username = str(flask_session.get("user") or "").strip()
        if not username:
            return ""
        lineage = str(
            flask_session.get(run.SESSION_LINEAGE_KEY) or ""
        ).strip()
        generation = str(
            flask_session.get(run.SESSION_GENERATION_KEY) or ""
        ).strip()
        if not lineage or not generation:
            fixture_id = uuid.uuid4().hex
            lineage = f"target-persistence-lineage-{fixture_id}"
            generation = f"target-persistence-generation-{fixture_id}"
            run.session_generation_store.activate(
                lineage,
                generation,
                username,
                reason="target_persistence_fixture",
            )
            flask_session[run.SESSION_LINEAGE_KEY] = lineage
            flask_session[run.SESSION_GENERATION_KEY] = generation
        return generation

    @contextmanager
    def session_transaction(self, *args, **kwargs):
        with super().session_transaction(*args, **kwargs) as flask_session:
            yield flask_session
            self._bind_authenticated_generation(flask_session)

    def _ensure_authenticated_generation(self):
        with super().session_transaction() as flask_session:
            return self._bind_authenticated_generation(flask_session)

    @staticmethod
    def _document_url_with_generation(path, generation):
        if not isinstance(path, str):
            return path
        parts = urlsplit(path)
        if parts.path not in SessionGenerationFixtureClient._DOCUMENT_PATHS:
            return path
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.setdefault(
            "_session_generation",
            run._session_generation_query_token(generation),
        )
        return urlunsplit((
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        ))

    def open(self, *args, **kwargs):
        generation = self._ensure_authenticated_generation()
        if generation:
            headers = Headers(kwargs.get("headers") or ())
            if run.SESSION_GENERATION_HEADER not in headers:
                headers[run.SESSION_GENERATION_HEADER] = generation
            kwargs["headers"] = headers

            method = str(kwargs.get("method") or "GET").upper()
            if method in {"GET", "HEAD"}:
                if args:
                    args = (
                        self._document_url_with_generation(args[0], generation),
                        *args[1:],
                    )
                elif "path" in kwargs:
                    kwargs["path"] = self._document_url_with_generation(
                        kwargs["path"],
                        generation,
                    )
        return super().open(*args, **kwargs)


_ORIGINAL_SESSION_GENERATION_STORE = None
_ORIGINAL_TEST_CLIENT_CLASS = None
_SESSION_GENERATION_TMP = None


def setUpModule():
    global _ORIGINAL_SESSION_GENERATION_STORE
    global _ORIGINAL_TEST_CLIENT_CLASS
    global _SESSION_GENERATION_TMP
    _ORIGINAL_SESSION_GENERATION_STORE = run.session_generation_store
    _ORIGINAL_TEST_CLIENT_CLASS = run.app.test_client_class
    _SESSION_GENERATION_TMP = tempfile.TemporaryDirectory(
        prefix="chaos_target_persistence_session_"
    )
    run.session_generation_store = IsolatedFixtureSessionGenerationStore(
        os.path.join(_SESSION_GENERATION_TMP.name, "session-generation.sqlite3")
    )
    run.app.test_client_class = SessionGenerationFixtureClient


def tearDownModule():
    global _SESSION_GENERATION_TMP
    run.app.test_client_class = _ORIGINAL_TEST_CLIENT_CLASS
    run.session_generation_store = _ORIGINAL_SESSION_GENERATION_STORE
    if _SESSION_GENERATION_TMP is not None:
        _SESSION_GENERATION_TMP.cleanup()
        _SESSION_GENERATION_TMP = None


def canonical_wallet_test_profile(username, balance):
    return {
        "username": username,
        "password": "pw",
        "salt": "",
        "level": 1,
        "hackcoins": balance,
        "respect": 0,
        "exp": "0 / 1000",
        "inventory": [],
        "files": {"tools": [], "download": []},
        "apps": [],
        "hacked": [],
        "desktop_settings": {},
        "security": {},
        "territory_stats": {},
    }


def canonical_market_test_payout(profile):
    def payout(settlement):
        balance = int(profile.get("hackcoins", 0) or 0) + int(settlement.get("price", 0) or 0)
        source_id = settlement.get("batch_id") or settlement.get("file_id") or "sale"
        return {
            "balance": balance,
            "transaction_key": f"test:ghost_exchange:{source_id}",
        }

    return payout


class CanonicalWalletTestDouble:
    """Small in-memory publisher/transfer double for endpoint fixtures."""

    def __init__(self, balances):
        self.balances = {
            str(username): int(balance)
            for username, balance in dict(balances or {}).items()
        }
        self.receipts = {}

    def get_balance(self, username):
        return int(self.balances.get(str(username), 0))

    def transfer(
        self,
        from_username,
        to_username,
        amount,
        *,
        transaction_key,
        note="",
        **_kwargs,
    ):
        del note
        sender = str(from_username)
        recipient = str(to_username)
        amount = int(amount)
        if transaction_key in self.receipts:
            result = dict(self.receipts[transaction_key])
            result["duplicate"] = True
            return result
        if self.get_balance(sender) < amount:
            raise run.WalletInsufficientFunds("Za malo HackCoinow.")
        self.balances[sender] = self.get_balance(sender) - amount
        self.balances[recipient] = self.get_balance(recipient) + amount
        result = {
            "balance": self.balances[sender],
            "recipient_balance": self.balances[recipient],
            "duplicate": False,
            "transaction_key": transaction_key,
        }
        self.receipts[transaction_key] = dict(result)
        return result

    def credit(self, username, amount, *, transaction_key, **_kwargs):
        username = str(username)
        if transaction_key in self.receipts:
            result = dict(self.receipts[transaction_key])
            result["duplicate"] = True
            return result
        self.balances[username] = self.get_balance(username) + int(amount)
        result = {
            "balance": self.balances[username],
            "duplicate": False,
            "transaction_key": transaction_key,
        }
        self.receipts[transaction_key] = dict(result)
        return result


@contextmanager
def canonical_wallet_test_runtime(balances):
    wallet = CanonicalWalletTestDouble(balances)
    with patch.object(run, "wallet_balance_store", wallet), \
            patch.object(run, "wallet_store", wallet):
        yield wallet


class AppRequiredOffStateTest(unittest.TestCase):
    def test_missing_optional_security_is_treated_as_not_installed(self):
        state = resolve_app_required_off_state(
            {"firewall": False},
            ["firewall", "audio_guardian"],
        )

        self.assertTrue(state["satisfied"])
        self.assertEqual(state["absent"], ["audio_guardian"])

    def test_only_explicitly_active_security_blocks_application(self):
        state = resolve_app_required_off_state(
            {"firewall": False, "audio_guardian": True},
            ["firewall", "audio_guardian"],
        )

        self.assertFalse(state["satisfied"])
        self.assertEqual(state["active"], ["audio_guardian"])

    def test_malformed_present_security_does_not_fail_open(self):
        state = resolve_app_required_off_state(
            {"audio_guardian": None},
            ["audio_guardian"],
        )

        self.assertFalse(state["satisfied"])
        self.assertEqual(state["invalid"], ["audio_guardian"])


class TargetDisplayLabelTest(unittest.TestCase):
    def test_unnamed_poi_gets_deterministic_node_label(self):
        target = {
            "name": "",
            "label": "Brak nazwy",
            "source_type": "shop",
            "target_type": "poi",
            "osm_id": 123456,
            "lat": 52.2297,
            "lng": 21.0122,
        }

        label = display_target_label(target)

        self.assertTrue(label.startswith("NODE-"))
        self.assertNotEqual(label, "Brak nazwy")
        self.assertEqual(label, display_target_label(dict(target)))

    def test_named_target_keeps_real_name(self):
        target = {
            "name": "Zabka",
            "label": "",
            "source_type": "shop",
            "lat": 52.1,
            "lng": 21.2,
        }

        self.assertEqual(display_target_label(target), "Zabka")

    def test_vehicle_and_person_prefixes_are_readable(self):
        vehicle = {"source_type": "car", "name": "", "lat": 52.1, "lng": 21.2}
        person = {"source_type": "person", "name": "", "lat": 52.1, "lng": 21.2}

        self.assertTrue(display_target_label(vehicle).startswith("ECU-"))
        self.assertTrue(display_target_label(person).startswith("SUBJECT-"))


class MapAimTargetEndpointTest(unittest.TestCase):
    def test_menu_title_aims_without_launching_hack_runtime(self):
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"

        profile = {"username": "alice", "aimed_target": {}, "operations": [], "launch_queue": []}
        canonical = {
            "lat": 52.1, "lng": 21.2, "label": "Bonito", "name": "Bonito",
            "icon": "target", "source_type": "shop", "target_mode": "standard",
            "target_id": "map:bonito", "actions_allowed": {}, "security": {},
        }
        with patch.object(run.user_store, "get_profile_identity", return_value=profile), \
                patch.object(run.player_target_runtime_store, "get_active_target", return_value=profile["aimed_target"]), \
                patch.object(run, "find_contested_target", return_value=None), \
                patch.object(run, "set_player_aimed_target", return_value=canonical) as set_target, \
                patch.object(run, "record_map_target_delta") as record_delta:
            response = client.post("/api/map/aim-target", json={
                "lat": 52.1, "lng": 21.2, "label": "Bonito", "name": "Bonito",
                "icon": "target", "source_type": "shop", "target_id": "map:bonito",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["target"]["target_id"], "map:bonito")
        self.assertEqual(set_target.call_args.kwargs["reason"], "map_menu_title_aim")
        self.assertFalse(set_target.call_args.kwargs["persist_profile_projection"])
        self.assertEqual(profile["operations"], [])
        self.assertEqual(profile["launch_queue"], [])
        record_delta.assert_called_once()

    def test_menu_title_recovers_existing_progress_by_position(self):
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        profile = {
            "username": "alice",
            "aimed_target": {
                "lat": 52.1, "lng": 21.2, "label": "Bonito",
                "target_id": "canonical:bonito",
                "actions_allowed": {"scan_ports": True, "exploit": False, "sniff": True, "trace": False},
                "security": {"firewall": False, "kernel_guard": True},
            },
        }

        def return_requested(_username, _profile, target, **_kwargs):
            return target

        with patch.object(run.user_store, "get_profile_identity", return_value=profile), \
                patch.object(run.player_target_runtime_store, "get_active_target", return_value=profile["aimed_target"]), \
                patch.object(run, "find_contested_target", return_value=None), \
                patch.object(run, "set_player_aimed_target", side_effect=return_requested) as set_target, \
                patch.object(run, "record_map_target_delta"):
            response = client.post("/api/map/aim-target", json={
                "lat": 52.1, "lng": 21.2, "label": "Bonito",
                "target_id": "display:bonito", "source_type": "shop",
            })

        self.assertEqual(response.status_code, 200)
        requested = set_target.call_args.args[2]
        self.assertEqual(requested["target_id"], "canonical:bonito")
        self.assertTrue(requested["actions_allowed"]["scan_ports"])
        self.assertTrue(requested["actions_allowed"]["sniff"])
        self.assertFalse(requested["security"]["firewall"])

    def test_menu_title_initializes_full_standard_target_runtime(self):
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        profile = {"username": "alice", "aimed_target": {}}

        def return_requested(_username, _profile, target, **_kwargs):
            return target

        with patch.object(run.user_store, "get_profile_identity", return_value=profile), \
                patch.object(run, "find_contested_target", return_value=None), \
                patch.object(run.resources_store, "get", return_value={
                    "firewall": True, "risk_score": 50, "description": "ignored"
                }), \
                patch.object(run, "choice", return_value=True), \
                patch.object(run, "randint", return_value=37), \
                patch.object(run, "set_player_aimed_target", side_effect=return_requested) as set_target, \
                patch.object(run, "record_map_target_delta"):
            response = client.post("/api/map/aim-target", json={
                "lat": 52.1, "lng": 21.2, "label": "Bonito",
                "source_type": "shop",
            })

        self.assertEqual(response.status_code, 200)
        requested = set_target.call_args.args[2]
        self.assertEqual(requested["target_id"], "map:52.1:21.2:Bonito")
        self.assertEqual(requested["security"], {"firewall": True, "risk_score": 37})
        self.assertEqual(requested["actions_allowed"], {
            "scan_ports": False, "exploit": False, "sniff": False, "trace": False,
        })

    def test_menu_title_uses_canonical_conflict_target(self):
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        profile = {"username": "alice", "aimed_target": {}}
        canonical = {
            "target_id": "territory:canonical-pillar",
            "lat": 52.1, "lng": 21.2, "label": "Pillar",
            "owner_username": "bob", "foreign_area_id": 44,
            "security": {"firewall": True},
            "actions_allowed": {
                "scan_ports": True, "exploit": True, "sniff": True, "trace": True,
            },
        }

        def return_requested(_username, _profile, target, **_kwargs):
            return target

        with patch.object(run.user_store, "get_profile_identity", return_value=profile), \
                patch.object(run, "find_contested_target", return_value=canonical), \
                patch.object(run, "set_player_aimed_target", side_effect=return_requested) as set_target, \
                patch.object(run, "record_map_target_delta"):
            response = client.post("/api/map/aim-target", json={
                "lat": 52.1, "lng": 21.2, "label": "Pillar",
                "target_mode": "territory_contest", "foreign_area_id": 44,
                "target_id": "display:pillar",
            })

        self.assertEqual(response.status_code, 200)
        requested = set_target.call_args.args[2]
        self.assertEqual(requested["target_id"], "territory:canonical-pillar")
        self.assertEqual(requested["contest_owner_username"], "bob")
        self.assertEqual(requested["security"], {"firewall": True})
        self.assertEqual(requested["actions_allowed"], {
            "scan_ports": False, "exploit": False, "sniff": False, "trace": False,
        })

    def test_menu_title_recovers_conflict_target_without_frontend_conflict_hints(self):
        client = run.app.test_client()
        with client.session_transaction() as flask_session:
            flask_session["user"] = "alice"
        profile = {"username": "alice", "aimed_target": {}}
        canonical = {
            "target_id": "territory:canonical-pillar",
            "lat": 52.1, "lng": 21.2, "label": "Pillar",
            "owner_username": "bob", "foreign_area_id": 44,
            "security": {"firewall": True},
        }

        def return_requested(_username, _profile, target, **_kwargs):
            return target

        with patch.object(run.user_store, "get_profile_identity", return_value=profile), \
                patch.object(run, "find_contested_target", return_value=canonical), \
                patch.object(run, "set_player_aimed_target", side_effect=return_requested) as set_target, \
                patch.object(run, "record_map_target_delta"):
            response = client.post("/api/map/aim-target", json={
                "lat": 52.1, "lng": 21.2, "label": "Pillar",
                "source_type": "shop", "target_id": "display:pillar",
            })

        self.assertEqual(response.status_code, 200)
        requested = set_target.call_args.args[2]
        self.assertEqual(requested["target_id"], "territory:canonical-pillar")
        self.assertEqual(requested["target_mode"], "territory_contest")
        self.assertEqual(requested["contest_owner_username"], "bob")
        self.assertEqual(requested["security"], {"firewall": True})


class PlayerTargetRuntimeIdentityTest(unittest.TestCase):
    def test_runtime_exposes_disarm_progress_as_percentage(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            store = PlayerTargetRuntimeStore(db_path=path)
            store.upsert_aimed("alice", {
                "target_id": "map:52.1:21.2:Target",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Target",
                "actions_allowed": {
                    "scan_ports": True,
                    "exploit": False,
                    "sniff": False,
                    "trace": False,
                },
            })

            target = store.get_active_target("alice")
            self.assertEqual(target["disarm_progress"], 25)
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    os.remove(candidate)

    def test_same_ordinary_poi_merges_progress_across_display_ids(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            store = PlayerTargetRuntimeStore(db_path=path)
            first = store.upsert_aimed("alice", {
                "target_id": "map:52.1:21.2:Bonito",
                "target_mode": "standard",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Bonito",
                "actions_allowed": {"scan_ports": True, "exploit": False},
                "security": {"firewall": False, "kernel_guard": True},
            })
            second = store.upsert_aimed("alice", {
                "target_id": "map:52.10000:21.20000:Salon Bonito",
                "target_mode": "standard",
                "lat": 52.1000001,
                "lng": 21.2000001,
                "label": "Salon Bonito",
                "actions_allowed": {"scan_ports": False, "exploit": True},
                "security": {"firewall": True, "kernel_guard": False},
            }, status="in_progress")

            target = store.get_active_target("alice")
            self.assertEqual(first["target"]["target_id"], target["target_id"])
            self.assertEqual(second["target"]["target_id"], target["target_id"])
            self.assertTrue(target["actions_allowed"]["scan_ports"])
            self.assertTrue(target["actions_allowed"]["exploit"])
            self.assertFalse(target["security"]["firewall"])
            self.assertFalse(target["security"]["kernel_guard"])
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    os.remove(candidate)

    def test_special_targets_are_not_aliased_only_by_position(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            store = PlayerTargetRuntimeStore(db_path=path)
            store.upsert_aimed("alice", {
                "target_id": "territory:first",
                "target_mode": "territory_contest",
                "foreign_area_id": 11,
                "lat": 52.1,
                "lng": 21.2,
                "actions_allowed": {"scan_ports": True},
            })
            store.upsert_aimed("alice", {
                "target_id": "territory:second",
                "target_mode": "territory_contest",
                "foreign_area_id": 12,
                "lat": 52.1,
                "lng": 21.2,
                "actions_allowed": {"scan_ports": False},
            })
            target = store.get_active_target("alice")
            self.assertEqual(target["target_id"], "territory:second")
            self.assertFalse(target["actions_allowed"]["scan_ports"])
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    os.remove(candidate)

    def test_stale_app_progress_cannot_replace_new_selection(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            store = PlayerTargetRuntimeStore(db_path=path)
            previous = {
                "target_id": "map:52.1:21.2:Previous",
                "lat": 52.1, "lng": 21.2, "label": "Previous",
                "actions_allowed": {"scan_ports": False},
            }
            current = {
                "target_id": "map:52.2:21.3:Current",
                "lat": 52.2, "lng": 21.3, "label": "Current",
                "actions_allowed": {"scan_ports": False},
            }
            store.upsert_aimed("alice", previous)
            store.upsert_aimed("alice", current)
            stale_progress = {
                **previous,
                "actions_allowed": {"scan_ports": True},
            }
            result = store.upsert_aimed(
                "alice",
                stale_progress,
                status="in_progress",
                source="late_app",
                expected_target=previous,
            )

            self.assertFalse(result["changed"])
            self.assertEqual(result["status"], "selection_changed")
            self.assertEqual(store.get_active_target("alice")["target_id"], current["target_id"])
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    os.remove(candidate)

class DevBugReportStoreTest(unittest.TestCase):
    def test_dev_mode_gate_uses_environment(self):
        with patch.dict(os.environ, {"APP_ENV": "production", "CHAOS_DEV_MODE": ""}, clear=False):
            self.assertFalse(run.is_dev_mode_enabled())

        with patch.dict(os.environ, {"APP_ENV": "staging", "CHAOS_DEV_MODE": ""}, clear=False):
            self.assertTrue(run.is_dev_mode_enabled())

        with patch.dict(os.environ, {"APP_ENV": "production", "CHAOS_DEV_MODE": "true"}, clear=False):
            self.assertTrue(run.is_dev_mode_enabled())

    def test_dev_bug_report_store_creates_lists_and_updates_status(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            store = DevBugReportStore(db_path=path)
            report = store.create_report(
                {
                    "title": "Camera cards overlap",
                    "description": "Long cards break UI",
                    "category": "UI",
                    "severity": "high",
                    "current_url": "/desktop",
                    "context": {
                        "client_timestamp": "2026-06-29T12:00:00",
                        "active_window": {"title": "Mapa"},
                    },
                },
                created_by="tester",
                app_version="test-build",
            )

            self.assertEqual(report["status"], "new")
            self.assertEqual(report["category"], "UI")
            self.assertEqual(report["context"]["active_window"]["title"], "Mapa")
            self.assertEqual(len(store.list_reports(search="camera")), 1)
            self.assertEqual(len(store.find_similar("Camera overlap")), 1)

            updated = store.update_report(report["id"], {"status": "confirmed"})
            self.assertEqual(updated["status"], "confirmed")
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except PermissionError:
                        pass

    def test_dev_bug_server_context_uses_trusted_profile_username(self):
        fake_profile = {
            "username": "admin",
            "nick": "Admin",
            "level": 6,
            "hackcoins": 123,
            "respect": 7,
            "aimed_target": {"label": "Target A", "target_mode": "standard"},
            "operations": [
                {
                    "operation_id": "op1",
                    "operation_type": "camera_stream",
                    "status": "running",
                    "target": {"label": "Camera"},
                    "expires_at": "2999-06-29T12:30:00+00:00",
                    "remaining_seconds": 1800,
                }
            ],
        }

        with patch.object(
            run,
            "load_profile_write_record",
            return_value={"profile": fake_profile},
        ):
            context = run.build_dev_bug_server_context(
                "admin",
                client_context={"profile": {"username": "spoofed"}, "current_url": "/desktop"},
            )

        self.assertEqual(context["session"]["username"], "admin")
        self.assertEqual(context["profile_snapshot"]["level"], 6)
        self.assertEqual(context["aimed_target"]["label"], "Target A")
        self.assertEqual(context["active_operations_summary"][0]["operation_type"], "camera_stream")
        self.assertIn("server_timestamp", context)


class JsonResourceStoreSeedTest(unittest.TestCase):
    def test_static_seed_uses_resource_whitelist(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            JsonResourceStore(db_path=path)
            conn = sqlite3.connect(path)
            try:
                keys = {
                    row[0]
                    for row in conn.execute("SELECT key FROM json_resources").fetchall()
                }
            finally:
                conn.close()

            self.assertIn("app_config", keys)
            self.assertIn("user_template", keys)
            self.assertIn("user_security", keys)
            self.assertIn("terminal_command", keys)
            self.assertNotIn("targets", keys)
            self.assertNotIn("resources", keys)
            self.assertNotIn("system_status", keys)
            self.assertNotIn("system_messages", keys)
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except PermissionError:
                        pass


class MailStoreFriendshipStatusTest(unittest.TestCase):
    def test_pending_contact_is_not_accepted_friendship(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            store = MailStore(db_path=path)
            now = datetime.now(timezone.utc).isoformat()
            with sqlite3.connect(path) as conn:
                conn.execute(
                    "INSERT INTO users (username, password, salt, profile_json, created_at, updated_at) VALUES (?, '', '', '{}', ?, ?)",
                    ("alice", now, now),
                )
                conn.execute(
                    "INSERT INTO users (username, password, salt, profile_json, created_at, updated_at) VALUES (?, '', '', '{}', ?, ?)",
                    ("bob", now, now),
                )
                conn.commit()

            store.add_contact("alice", "bob")

            self.assertTrue(store.is_contact("alice", "bob"))
            self.assertFalse(store.is_accepted_contact("alice", "bob"))
            self.assertEqual(store.list_accepted_contacts("alice"), [])
            self.assertTrue(store.has_pending_contact_request("alice", "bob"))

            store.add_contact("bob", "alice")

            self.assertTrue(store.is_accepted_contact("alice", "bob"))
            self.assertEqual(store.list_accepted_contacts("alice")[0]["name"], "bob")
            self.assertFalse(store.has_pending_contact_request("alice", "bob"))
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except PermissionError:
                        pass


class GameStateDeltaBusTest(unittest.TestCase):
    def _temp_path(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        return path

    def _cleanup(self, path):
        for suffix in ("", "-wal", "-shm"):
            candidate = f"{path}{suffix}"
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except PermissionError:
                    pass

    def test_record_change_creates_delta_event_contract(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            event = bus.record_change(
                "alice",
                "wallet",
                "wallet.balance_changed",
                {"balance": 120, "currency": "HC"},
                entity_id="wallet",
                dedupe_key="wallet:balance:alice:1",
            )

            self.assertEqual(event["version"], 1)
            self.assertEqual(event["scope"], "wallet")
            self.assertEqual(event["type"], "wallet.balance_changed")
            self.assertEqual(event["entity_id"], "wallet")
            self.assertEqual(event["dedupe_key"], "wallet:balance:alice:1")
            self.assertEqual(event["payload"]["balance"], 120)
            self.assertTrue(event["created_at"])
        finally:
            self._cleanup(path)

    def test_dedupe_key_makes_record_change_idempotent(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            first = bus.record_change(
                "alice",
                "storage",
                "storage.used_changed",
                {"used": 128, "capacity": 512},
                entity_id="storage",
                dedupe_key="storage:used:alice:1",
            )
            second = bus.record_change(
                "alice",
                "storage",
                "storage.used_changed",
                {"used": 256, "capacity": 512},
                entity_id="storage",
                dedupe_key="storage:used:alice:1",
            )
            changes = bus.get_changes_since("alice", 0)["changes"]

            self.assertEqual(first, second)
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]["payload"]["used"], 128)
        finally:
            self._cleanup(path)

    def test_get_changes_since_returns_ordered_events(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            bus.record_change("alice", "wallet", "wallet.balance_changed", {"balance": 1})
            bus.record_change("alice", "storage", "storage.used_changed", {"used": 2})
            bus.record_change("alice", "apps", "apps.app_installed", {"app_id": "xmapper"})

            result = bus.get_changes_since("alice", 1)

            self.assertFalse(result["recovery_required"])
            self.assertEqual(result["current_version"], 3)
            self.assertEqual([event["version"] for event in result["changes"]], [2, 3])
            self.assertEqual(result["changes"][0]["scope"], "storage")
        finally:
            self._cleanup(path)

    def test_record_wallet_balance_delta_uses_wallet_contract(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            with patch.object(run, "delta_bus", bus), \
                    patch.object(run, "canonical_wallet_balance", return_value=777):
                event = run.record_wallet_balance_delta(
                    "alice",
                    777,
                    reason="unit_test",
                    dedupe_key="wallet:balance:alice:test",
                )

            self.assertEqual(event["scope"], "wallet")
            self.assertEqual(event["type"], "wallet.balance_changed")
            self.assertEqual(event["entity_id"], "wallet")
            self.assertEqual(event["payload"]["balance"], 777)
            self.assertEqual(event["payload"]["currency"], "HC")
            self.assertEqual(event["payload"]["reason"], "unit_test")
        finally:
            self._cleanup(path)

    def test_record_map_player_actor_delta_targets_accepted_contact(self):
        class DummyMailStore:
            def list_accepted_contacts(self, username):
                if username != "runner":
                    raise AssertionError(username)
                return [{"name": "viewer", "status": "online"}]

        class DummyUserStore:
            def get_profile(self, username):
                profiles = {
                    "viewer": {
                        "username": "viewer",
                        "nick": "Viewer",
                        "aimed_target": {},
                    },
                    "runner": {
                        "username": "runner",
                        "nick": "Runner",
                        "avatar": "",
                        "curently_possition": {"lat": 52.1, "lng": 21.2},
                        "level": 4,
                    },
                }
                return profiles.get(username)

        class DummyTerritoryStore:
            def list_player_areas(self):
                return []

        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            actor_profile = {
                "username": "runner",
                "nick": "Runner",
                "avatar": "",
                "curently_possition": {"lat": 52.1, "lng": 21.2},
                "level": 4,
            }
            with patch.object(run, "delta_bus", bus), \
                    patch.object(run, "mail_store", DummyMailStore()), \
                    patch.object(run, "user_store", DummyUserStore()), \
                    patch.object(run, "territory_store", DummyTerritoryStore()):
                events = record_map_player_actor_delta(
                    "runner",
                    actor_profile,
                    change_type="map.player_moved",
                    reason="unit_test",
                    dedupe_key_prefix="map:runner:test",
                )

            self.assertEqual(len(events), 1)
            event = events[0]
            self.assertEqual(event["scope"], "map")
            self.assertEqual(event["type"], "map.player_moved")
            self.assertEqual(event["entity_id"], "runner")
            self.assertEqual(event["payload"]["username"], "runner")
            self.assertEqual(event["payload"]["actor"]["username"], "runner")
            self.assertEqual(event["payload"]["actor"]["lat"], 52.1)
            self.assertEqual(event["payload"]["actor"]["context"]["is_friend"], True)
            changes = bus.get_changes_since("viewer", 0)["changes"]
            self.assertEqual(len(changes), 1)
        finally:
            self._cleanup(path)

    def test_static_area_intruder_sync_after_territory_rebuild_records_intruder_delta(self):
        area = {
            "id": 77,
            "owner_username": "owner",
            "status": "active",
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.02},
                {"lat": 52.02, "lng": 21.0},
            ],
        }

        class DummyUserStore:
            def list_profiles(self):
                return [
                    {"username": "owner", "curently_possition": {"lat": 51.0, "lng": 20.0}},
                    {
                        "username": "intruder",
                        "nick": "Intruder",
                        "curently_possition": {"lat": 52.005, "lng": 21.005},
                    },
                ]

        class DummyTerritoryStore:
            def __init__(self):
                self.events = []

            def recent_area_event_exists(self, owner_username, actor_username, event_type, area_id=None, seconds=60):
                return False

            def add_area_event(self, **event):
                self.events.append(event)

        territory = DummyTerritoryStore()
        with patch.object(run, "user_store", DummyUserStore()), \
                patch.object(run, "territory_store", territory), \
                patch.object(run, "record_map_player_actor_delta") as record_delta:
            synced = run.sync_static_area_intruders_for_owner(
                "owner",
                [area],
                reason="territory_rebuild_test",
            )

        self.assertEqual(len(synced), 1)
        self.assertEqual(synced[0]["username"], "intruder")
        self.assertEqual(len(territory.events), 1)
        self.assertEqual(territory.events[0]["event_type"], "intruder_enter")
        self.assertEqual(territory.events[0]["owner_username"], "owner")
        self.assertEqual(territory.events[0]["actor_username"], "intruder")
        self.assertTrue(territory.events[0]["payload"]["static_sync"])
        record_delta.assert_called_once()
        _, kwargs = record_delta.call_args
        self.assertEqual(kwargs["change_type"], "map.player_moved")
        self.assertEqual(kwargs["intrusion_area"]["id"], 77)

    def test_record_map_target_delta_uses_target_id_contract(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            target = {
                "lat": 52.123456,
                "lng": 21.123456,
                "label": "Camera Node",
                "source_type": "camera",
            }
            with patch.object(run, "delta_bus", bus):
                event = record_map_target_delta(
                    "alice",
                    target,
                    change_type="map.target_updated",
                    reason="unit_test",
                    dedupe_key="map:target:alice:test",
                )

            expected_target_id = run.build_operation_target_id(target)
            self.assertEqual(event["scope"], "map")
            self.assertEqual(event["type"], "map.target_updated")
            self.assertEqual(event["entity_id"], expected_target_id)
            self.assertEqual(event["payload"]["target_id"], expected_target_id)
            self.assertEqual(event["payload"]["target"]["label"], "Camera Node")
            self.assertEqual(event["payload"]["reason"], "unit_test")
        finally:
            self._cleanup(path)

    def test_record_storage_delta_emits_used_and_capacity_events_idempotently(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            profile = {
                "storage_used": 80,
                "storage_capacity": 768,
                "storage_unit": "MB",
                "storage_soft_limit": True,
                "storage_over_limit": False,
            }
            previous = {
                "used": 64,
                "capacity": 512,
                "unit": "MB",
                "soft_limit": True,
                "over_limit": False,
            }

            with patch.object(run, "delta_bus", bus):
                first = run.record_storage_delta(
                    "alice",
                    profile,
                    reason="unit_test",
                    previous=previous,
                    dedupe_key_prefix="storage:alice:test",
                )
                second = run.record_storage_delta(
                    "alice",
                    profile,
                    reason="unit_test",
                    previous=previous,
                    dedupe_key_prefix="storage:alice:test",
                )

            changes = bus.get_changes_since("alice", 0)["changes"]
            self.assertEqual(len(first), 2)
            self.assertEqual(len(second), 2)
            self.assertEqual(len(changes), 2)
            self.assertEqual([item["type"] for item in changes], [
                "storage.used_changed",
                "storage.capacity_changed",
            ])
            self.assertEqual(changes[0]["payload"]["used"], 80)
            self.assertEqual(changes[1]["payload"]["capacity"], 768)
        finally:
            self._cleanup(path)

    def test_record_apps_delta_emits_apps_snapshot_idempotently(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            app = normalize_app_contract({
                "id": "xmapper",
                "name": "xmapper",
                "interface": "terminal",
            })
            profile = {
                "apps": [app],
                "files": {
                    "tools": ["xmapper.sh"],
                    "gps": [],
                },
            }

            with patch.object(run, "delta_bus", bus):
                first = run.record_apps_delta(
                    "alice",
                    profile,
                    "apps.app_installed",
                    app=app,
                    app_id="xmapper",
                    reason="unit_test",
                    dedupe_key="apps:installed:alice:xmapper",
                )
                second = run.record_apps_delta(
                    "alice",
                    profile,
                    "apps.app_installed",
                    app=app,
                    app_id="xmapper",
                    reason="unit_test",
                    dedupe_key="apps:installed:alice:xmapper",
                )

            changes = bus.get_changes_since("alice", 0)["changes"]
            self.assertEqual(first, second)
            self.assertEqual(len(changes), 1)
            event = changes[0]
            self.assertEqual(event["scope"], "apps")
            self.assertEqual(event["type"], "apps.app_installed")
            self.assertEqual(event["entity_id"], "xmapper")
            self.assertEqual(event["payload"]["app_id"], "xmapper")
            self.assertEqual(event["payload"]["apps"][0]["id"], "xmapper")
            self.assertEqual(event["payload"]["files"]["tools"], ["xmapper.sh"])
            self.assertEqual(event["payload"]["reason"], "unit_test")
        finally:
            self._cleanup(path)

    def test_record_mail_delta_emits_unread_and_thread_summary(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            message = {
                "id": 7,
                "scope": "direct",
                "peer": "Ghost Exchange",
                "sender": "Ghost Exchange",
                "subject": "Sprzedano pakiet",
                "body": "Nowa transakcja.",
                "created_at": "2026-07-07T07:00:00Z",
            }
            with patch.object(run, "delta_bus", bus), \
                    patch.object(run.mail_store, "unread_counts", return_value={
                        "group": 0,
                        "direct": {"Ghost Exchange": 1},
                        "channel": {},
                    }):
                run.record_mail_thread_update(
                    "alice",
                    "direct",
                    "Ghost Exchange",
                    message=message,
                    reason="unit_test",
                )

            changes = bus.get_changes_since("alice", 0)["changes"]
            self.assertEqual([item["type"] for item in changes], [
                "mail.thread_updated",
                "mail.unread_changed",
            ])
            self.assertEqual(changes[0]["scope"], "mail")
            self.assertEqual(changes[0]["entity_id"], "direct:Ghost Exchange")
            self.assertEqual(changes[0]["payload"]["thread"]["preview"], "Nowa transakcja.")
            self.assertEqual(changes[1]["payload"]["unread_counts"]["direct"]["Ghost Exchange"], 1)
        finally:
            self._cleanup(path)

    def test_record_ghost_exchange_delta_emits_summary_and_transaction(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            sale = {
                "id": "batch-1",
                "batch_id": "batch-1",
                "market_sector": "gps",
                "price": 123,
                "currency": "HC",
                "sold_at": "2026-07-07T07:00:00Z",
                "status": "sold",
                "file_count": 3,
                "volume_mb": 42,
            }
            profile = {
                "files": {"gps": [], "market": []},
                "market_history": [sale],
            }
            with patch.object(run, "delta_bus", bus):
                run.record_ghost_exchange_delta(
                    "alice",
                    profile,
                    sales=[sale],
                    reason="unit_test",
                )

            changes = bus.get_changes_since("alice", 0)["changes"]
            self.assertEqual([item["type"] for item in changes], [
                "ghost_exchange.summary_changed",
                "ghost_exchange.transaction_added",
            ])
            self.assertEqual(changes[0]["scope"], "ghost_exchange")
            self.assertEqual(changes[0]["payload"]["summary"]["hc_total"], 123)
            self.assertEqual(changes[1]["entity_id"], "batch-1")
            self.assertEqual(changes[1]["payload"]["transaction"]["batch_id"], "batch-1")
            self.assertEqual(changes[1]["payload"]["transaction"]["price"], 123)
        finally:
            self._cleanup(path)

    def test_get_changes_since_requires_recovery_when_limit_exceeded(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            bus.record_change("alice", "wallet", "wallet.balance_changed", {"balance": 1})
            bus.record_change("alice", "storage", "storage.used_changed", {"used": 2})
            bus.record_change("alice", "apps", "apps.app_installed", {"app_id": "xmapper"})

            result = bus.get_changes_since("alice", 0, limit=2)

            self.assertTrue(result["recovery_required"])
            self.assertEqual(result["reason"], "limit_exceeded")
            self.assertEqual(result["available_count"], 3)
        finally:
            self._cleanup(path)

    def test_retention_marks_old_since_as_recovery(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path, retention_limit=2)
            bus.record_change("alice", "wallet", "wallet.balance_changed", {"balance": 1})
            bus.record_change("alice", "storage", "storage.used_changed", {"used": 2})
            bus.record_change("alice", "apps", "apps.app_installed", {"app_id": "xmapper"})

            result = bus.get_changes_since("alice", 0)

            self.assertTrue(result["recovery_required"])
            self.assertEqual(result["reason"], "outside_retention")
            self.assertEqual(result["oldest_version"], 2)
        finally:
            self._cleanup(path)


class StateChangesEndpointTest(unittest.TestCase):
    def _temp_path(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        return path

    def _cleanup(self, path):
        for suffix in ("", "-wal", "-shm"):
            candidate = f"{path}{suffix}"
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except PermissionError:
                    pass

    def _client_with_user(self, username="alice"):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = username
        return client

    def test_state_changes_returns_empty_list_without_snapshot(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            client = self._client_with_user()
            with patch.object(run, "delta_bus", bus), \
                    patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
                response = client.get("/api/state/changes?since=0&limit=100")

            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data["current_version"], 0)
            self.assertEqual(data["changes"], [])
            self.assertFalse(data["recovery_required"])
        finally:
            self._cleanup(path)

    def test_state_changes_returns_events_since_version(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            bus.record_change("alice", "wallet", "wallet.balance_changed", {"balance": 10})
            bus.record_change("alice", "storage", "storage.used_changed", {"used": 20})
            client = self._client_with_user()
            with patch.object(run, "delta_bus", bus):
                response = client.get("/api/state/changes?since=1&limit=100")

            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertFalse(data["recovery_required"])
            self.assertEqual(data["current_version"], 2)
            self.assertEqual(len(data["changes"]), 1)
            self.assertEqual(data["changes"][0]["type"], "storage.used_changed")
        finally:
            self._cleanup(path)

    def test_state_changes_requires_recovery_when_limit_exceeded(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            bus.record_change("alice", "wallet", "wallet.balance_changed", {"balance": 1})
            bus.record_change("alice", "storage", "storage.used_changed", {"used": 2})
            bus.record_change("alice", "apps", "apps.app_installed", {"app_id": "xmapper"})
            client = self._client_with_user()
            with patch.object(run, "delta_bus", bus):
                response = client.get("/api/state/changes?since=0&limit=2")

            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(data["recovery_required"])
            self.assertEqual(data["reason"], "limit_exceeded")
            self.assertEqual(data["changes"], [])
            self.assertEqual(data["recovery_scopes"], [
                "wallet",
                "storage",
                "apps",
                "mail",
                "ghost_exchange",
                "map",
                "territory",
                "ghostnetwork",
            ])
        finally:
            self._cleanup(path)

    def test_state_changes_requires_recovery_when_since_outside_retention(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path, retention_limit=2)
            bus.record_change("alice", "wallet", "wallet.balance_changed", {"balance": 1})
            bus.record_change("alice", "storage", "storage.used_changed", {"used": 2})
            bus.record_change("alice", "apps", "apps.app_installed", {"app_id": "xmapper"})
            client = self._client_with_user()
            with patch.object(run, "delta_bus", bus):
                response = client.get("/api/state/changes?since=0&limit=100")

            data = response.get_json()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(data["recovery_required"])
            self.assertEqual(data["reason"], "outside_retention")
            self.assertEqual(data["changes"], [])
            self.assertIn("mail", data["recovery_scopes"])
            self.assertIn("ghost_exchange", data["recovery_scopes"])
            self.assertIn("map", data["recovery_scopes"])
        finally:
            self._cleanup(path)

    def test_state_changes_requires_login(self):
        response = run.app.test_client().get("/api/state/changes?since=0")

        data = response.get_json()
        self.assertEqual(response.status_code, 401)
        self.assertTrue(data["recovery_required"])
        self.assertEqual(data["reason"], "not_logged_in")
        self.assertEqual(data["changes"], [])
        self.assertIn("wallet", data["recovery_scopes"])
        self.assertIn("map", data["recovery_scopes"])


class WalletDeltaEndpointTest(unittest.TestCase):
    def _temp_path(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        return path

    def _cleanup(self, path):
        for suffix in ("", "-wal", "-shm"):
            candidate = f"{path}{suffix}"
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except PermissionError:
                    pass

    def test_wallet_transfer_records_balance_delta_for_sender_and_recipient(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            transfer_result = {
                "balance": 900,
                "recipient_balance": 1100,
                "currency": "HC",
                "transaction": {
                    "id": 42,
                    "type": "outgoing",
                    "peer": "bob",
                    "amount": 100,
                    "created_at": "2026-07-06T12:00:00Z",
                    "note": "test",
                },
            }
            wallet_after = {
                "balance": 900,
                "currency": "HC",
                "transactions": [transfer_result["transaction"]],
            }
            recipient_wallet = {
                "balance": 1100,
                "currency": "HC",
                "transactions": [],
            }

            def fake_get_wallet(username, limit=20):
                return recipient_wallet if username == "bob" else wallet_after

            with patch.object(run, "delta_bus", bus), \
                    patch.object(run.wallet_store, "transfer", return_value=transfer_result), \
                    patch.object(run.wallet_store, "get_wallet", side_effect=fake_get_wallet), \
                    patch.object(run, "canonical_wallet_balance", side_effect=lambda username: 1100 if username == "bob" else 900), \
                    patch.object(run, "sync_session_profile", return_value={"username": "alice", "hackcoins": 900}):
                with run.app.test_request_context("/api/wallet/transfer", method="POST", json={
                        "to": "bob",
                        "amount": 100,
                        "note": "test",
                        "transaction_key": "wallet-test:alice:bob:100",
                }):
                    run.session["user"] = "alice"
                    response = run.api_wallet_transfer()

            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertTrue(data["success"])

            changes_alice = bus.get_changes_since("alice", 0)["changes"]
            changes_bob = bus.get_changes_since("bob", 0)["changes"]
            self.assertEqual(len(changes_alice), 1)
            self.assertEqual(len(changes_bob), 1)
            self.assertEqual(changes_alice[0]["type"], "wallet.balance_changed")
            self.assertEqual(changes_alice[0]["payload"]["balance"], 900)
            self.assertEqual(changes_bob[0]["payload"]["balance"], 1100)
        finally:
            self._cleanup(path)

    def test_wallet_read_is_pure_canonical_and_does_not_reconcile_from_profile(self):
        path = self._temp_path()
        try:
            users = UserStore(db_path=path, seed_path="_missing_wallet_seed.json")
            users.save_profile_guarded(
                canonical_wallet_test_profile("bob", 5242),
                expected_revision=0,
                source="test.registration",
                allow_create=True,
            )
            balance_store = WalletBalanceStore(db_path=path)
            balance_store.recovery_set_balance(
                "bob",
                242,
                transaction_key="recovery:test:canonical-242",
                reason="test.recovery",
            )

            wallet = WalletStore(db_path=path).get_wallet("bob")

            self.assertEqual(wallet["balance"], 242)
            self.assertEqual(balance_store.get_balance("bob"), 242)
            self.assertEqual(users.get_profile("bob")["hackcoins"], 5242)
            audit = wallet.get("ledger_audit", {})
            self.assertEqual(audit.get("ledger_balance"), 242)
            self.assertTrue(audit.get("ok"))
        finally:
            self._cleanup(path)

    def test_wallet_balance_store_records_ledger_seed_and_delta(self):
        path = self._temp_path()
        try:
            users = UserStore(db_path=path, seed_path="_missing_wallet_seed.json")
            users.save_profile_guarded(
                canonical_wallet_test_profile("bob", 242),
                expected_revision=0,
                source="test.registration",
                allow_create=True,
            )
            balance_store = WalletBalanceStore(db_path=path)
            ledger_store = WalletLedgerStore(db_path=path)

            balance_store.credit(
                "bob",
                5000,
                transaction_key="reward:bob:5000",
                reason="test.reward",
            )

            events = ledger_store.list_events("bob", limit=10)
            self.assertEqual(ledger_store.ledger_balance("bob"), 5242)
            deltas = sorted(event["amount_delta"] for event in events)
            self.assertEqual(deltas, [242, 5000])
            self.assertIn(5242, {event["balance_after"] for event in events})
        finally:
            self._cleanup(path)


class DeltaDiagnosticsEndpointTest(unittest.TestCase):
    def _temp_path(self):
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        return path

    def _cleanup(self, path):
        for suffix in ("", "-wal", "-shm"):
            candidate = f"{path}{suffix}"
            if os.path.exists(candidate):
                try:
                    os.remove(candidate)
                except PermissionError:
                    pass

    def _client_with_user(self, username="admin"):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = username
        return client

    def test_delta_diagnostics_requires_admin(self):
        response = self._client_with_user("alice").get("/api/dev/delta-diagnostics")

        self.assertEqual(response.status_code, 403)

    def test_delta_diagnostics_returns_recent_events_and_metrics_without_sync(self):
        path = self._temp_path()
        try:
            bus = GameStateDeltaBus(db_path=path)
            bus.record_change(
                "admin",
                "wallet",
                "wallet.balance_changed",
                {"balance": 120, "currency": "HC"},
                entity_id="wallet",
                dedupe_key="wallet:balance:admin:1",
            )
            bus.record_change(
                "admin",
                "ghost_exchange",
                "ghost_exchange.transaction_added",
                {"transaction_id": "batch-1", "hc": 50},
                entity_id="batch-1",
                dedupe_key="gx:tx:batch-1:2",
            )
            client = self._client_with_user("admin")
            with patch.object(run, "delta_bus", bus), \
                    patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
                response = client.get("/api/dev/delta-diagnostics?limit=10&pollers_active_count=4&snapshot_recovery_count=1")

            data = response.get_json()
            diagnostics = data["diagnostics"]
            metrics = diagnostics["metrics"]
            self.assertEqual(response.status_code, 200)
            self.assertTrue(data["success"])
            self.assertEqual(diagnostics["current_version"], 2)
            self.assertEqual(len(diagnostics["events"]), 2)
            self.assertEqual(diagnostics["events"][0]["type"], "ghost_exchange.transaction_added")
            self.assertIn("payload_size", diagnostics["events"][0])
            self.assertEqual(metrics["pollers_active_count"], 4)
            self.assertEqual(metrics["snapshot_recovery_count"], 1)
            self.assertGreaterEqual(metrics["delta_events_per_minute"], 2)
            self.assertGreater(metrics["delta_payload_size"], 0)
        finally:
            self._cleanup(path)


class BlackNetWorldFactsSnapshotTest(unittest.TestCase):
    def _client_with_user(self, username="alice"):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = username
        return client

    def test_blacknet_world_facts_snapshot_uses_real_aggregates_without_private_fields(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        profiles = [
            {
                "username": "alice",
                "password": "secret",
                "salt": "salt",
                "operations": [{
                    "operation_id": "op1",
                    "operation_type": "sniff",
                    "status": "running",
                    "started_at": "2026-07-11T11:55:00+00:00",
                    "expires_at": "2026-07-11T12:55:00+00:00",
                    "target": {"label": "Zabka", "lat": 52.1, "lng": 21.1},
                }],
                "market_history": [{
                    "batch_id": "batch-gps-1",
                    "market_sector": "gps",
                    "price": 340,
                    "file_count": 2,
                    "volume_mb": 42,
                    "sold_at": "2026-07-11T11:00:00Z",
                }],
                "files": {"market": []},
                "system_messages": [{
                    "title": "Cel osiagniety",
                    "created_at": "2026-07-11T11:30:00Z",
                    "body": "private body should stay out of metadata",
                }],
            }
        ]

        with patch.object(run.user_store, "list_profiles", return_value=profiles), \
                patch.object(run, "get_app_catalog", return_value=[
                    {"id": "xmapper", "name": "xmapper", "price": 100, "category": "tools"},
                    {"id": "vault", "name": "Vault", "price": 250, "product_type": "storage_upgrade"},
                ]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=[]), \
                patch.object(run, "build_blacknet_radio_facts", return_value=[]):
            snapshot = build_blacknet_world_facts_snapshot(now=now)

        self.assertEqual(snapshot["schema"], 1)
        self.assertEqual(snapshot["snapshot_type"], "blacknet_world_facts")
        self.assertEqual(snapshot["source_versions"]["profiles"], 1)
        self.assertGreaterEqual(len(snapshot["facts"]), 4)
        fact_keys = {(fact["source_system"], fact["fact_type"]) for fact in snapshot["facts"]}
        by_type = {fact["fact_type"]: fact for fact in snapshot["facts"]}
        self.assertIn(("operations", "operations_active_count"), fact_keys)
        self.assertIn(("operations", "operation_hotspot_activity"), fact_keys)
        self.assertIn(("ghost_exchange", "market_sales_7d"), fact_keys)
        self.assertIn(("ghost_exchange", "market_top_sector_7d"), fact_keys)
        self.assertIn(("googleplex", "googleplex_product_signal"), fact_keys)
        self.assertEqual(by_type["market_top_sector_7d"]["metadata"]["sector_key"], "gps")
        self.assertEqual(by_type["market_top_sector_7d"]["metadata"]["cta_target_id"], "gps")
        googleplex_facts = [fact for fact in snapshot["facts"] if fact["fact_type"] == "googleplex_product_signal"]
        googleplex_by_product = {fact["metadata"]["product_id"]: fact for fact in googleplex_facts}
        self.assertEqual(set(googleplex_by_product), {"xmapper", "vault"})
        self.assertEqual(googleplex_by_product["vault"]["metadata"]["price"], 250)
        self.assertEqual(googleplex_by_product["vault"]["metadata"]["cta_query"], "Vault")
        serialized = json.dumps(snapshot, ensure_ascii=False)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("salt", serialized)
        self.assertNotIn("private body should stay out of metadata", serialized)
        for fact in snapshot["facts"]:
            for required in (
                "fact_id",
                "fact_type",
                "category",
                "region_id",
                "subject_id",
                "value",
                "previous_value",
                "change_percent",
                "importance",
                "confidence",
                "observed_at",
                "expires_at",
                "source_system",
                "metadata",
            ):
                self.assertIn(required, fact)

    def test_blacknet_world_facts_snapshot_survives_failed_source(self):
        with patch.object(run.user_store, "list_profiles", side_effect=RuntimeError("db offline")), \
                patch.object(run, "get_app_catalog", return_value=[]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=[]), \
                patch.object(run, "build_blacknet_radio_facts", return_value=[]):
            snapshot = build_blacknet_world_facts_snapshot(now=datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc))

        self.assertFalse(snapshot["diagnostics"]["sources"]["profiles"]["ok"])
        self.assertTrue(snapshot["diagnostics"]["sources"]["googleplex"]["ok"])
        self.assertIsInstance(snapshot["facts"], list)

    def test_blacknet_world_facts_endpoint_is_readonly_and_requires_login(self):
        response = run.app.test_client().get("/api/blacknet/world-facts")
        self.assertEqual(response.status_code, 401)

        client = self._client_with_user()
        with patch.object(run.user_store, "list_profiles", return_value=[]), \
                patch.object(run, "get_app_catalog", return_value=[]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=[]), \
                patch.object(run, "build_blacknet_radio_facts", return_value=[]), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
            response = client.get("/api/blacknet/world-facts")

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["snapshot"]["snapshot_type"], "blacknet_world_facts")

    def test_blacknet_radio_facts_point_to_concrete_blacknet_track(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp_dir:
            channel_root = os.path.join(temp_dir, "mp3", "radio", "channel", "blacknet_radio_2")
            os.makedirs(channel_root)
            with open(os.path.join(channel_root, "meta.channel"), "w", encoding="utf-8") as handle:
                json.dump({
                    "schema": 1,
                    "id": "blacknet_radio_2",
                    "name": "BlackNet Radio",
                    "source": "blacknet_radio",
                    "mode": "sort",
                    "exclude": ["ignore.mp3"],
                }, handle)
            for filename in ("001_intro.mp3", "002_signal.mp3", "ignore.mp3"):
                with open(os.path.join(channel_root, filename), "wb") as handle:
                    handle.write(b"")
            original_static = run.app.static_folder
            run.app.static_folder = temp_dir
            try:
                facts = run.build_blacknet_radio_facts(now)
            finally:
                run.app.static_folder = original_static

        self.assertEqual(len(facts), 1)
        metadata = facts[0]["metadata"]
        self.assertEqual(metadata["channel_id"], "blacknet_radio_2")
        self.assertEqual(metadata["track_count"], 2)
        self.assertIn(metadata["track_file"], {"001_intro.mp3", "002_signal.mp3"})
        self.assertTrue(metadata["track_title"])

    def test_blacknet_world_facts_snapshot_builds_real_operation_hotspot(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        profiles = [{
            "username": "alice",
            "operations": [
                {
                    "operation_id": "op-hotspot-1",
                    "operation_type": "sniff",
                    "status": "running",
                    "started_at": "2026-07-11T11:55:00+00:00",
                    "expires_at": "2026-07-11T12:55:00+00:00",
                    "target_id": "poi-putka",
                    "target": {
                        "name": "Piekarnia Putka",
                        "label": "Piekarnia Putka",
                        "lat": 52.22001,
                        "lng": 21.01002,
                        "target_type": "shop",
                    },
                },
                {
                    "operation_id": "op-hotspot-2",
                    "operation_type": "trace",
                    "status": "running",
                    "started_at": "2026-07-11T11:56:00+00:00",
                    "expires_at": "2026-07-11T12:56:00+00:00",
                    "target_id": "poi-putka",
                    "target": {
                        "name": "Piekarnia Putka",
                        "label": "Piekarnia Putka",
                        "lat": 52.22001,
                        "lng": 21.01002,
                        "target_type": "shop",
                    },
                },
            ],
            "market_history": [],
            "files": {"market": []},
            "system_messages": [],
        }]

        with patch.object(run.user_store, "list_profiles", return_value=profiles), \
                patch.object(run, "get_app_catalog", return_value=[]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=[]), \
                patch.object(run, "build_blacknet_radio_facts", return_value=[]):
            snapshot = build_blacknet_world_facts_snapshot(now=now)

        hotspots = [
            fact for fact in snapshot["facts"]
            if fact["fact_type"] == "operation_hotspot_activity"
        ]
        bursts = [
            fact for fact in snapshot["facts"]
            if fact["fact_type"] == "target_operation_burst"
        ]
        teleports = [
            fact for fact in snapshot["facts"]
            if fact["fact_type"] == "operation_hotspot_teleport"
        ]
        self.assertEqual(len(hotspots), 1)
        self.assertEqual(len(bursts), 1)
        self.assertEqual(len(teleports), 1)
        hotspot = hotspots[0]
        self.assertEqual(hotspot["value"], 2)
        self.assertEqual(hotspot["metadata"]["target_label"], "Piekarnia Putka")
        self.assertEqual(hotspot["metadata"]["target_id"], "poi-putka")
        self.assertAlmostEqual(hotspot["metadata"]["lat"], 52.22001)
        self.assertAlmostEqual(hotspot["metadata"]["lng"], 21.01002)
        self.assertEqual(bursts[0]["metadata"]["cta_target_id"], "poi-putka")
        self.assertEqual(teleports[0]["metadata"]["cta_target_id"], "poi-putka")

    def test_blacknet_operation_hotspot_uses_operation_coordinates_when_target_is_partial(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        operation = {
            "operation_id": "op-partial-target",
            "operation_type": "scan",
            "status": "running",
            "started_at": "2026-07-11T11:55:00+00:00",
            "expires_at": "2026-07-11T12:55:00+00:00",
            "lat": 52.280897,
            "lng": 20.997489,
            "target": {
                "label": "POI-00B7D7",
                "target_type": "poi",
            },
        }
        profiles = [{
            "username": "alice",
            "operations": [operation],
            "market_history": [],
            "files": {"market": []},
            "system_messages": [],
        }]

        facts = run.build_blacknet_operations_facts(profiles, now)
        hotspot = next(fact for fact in facts if fact["fact_type"] == "operation_hotspot_activity")
        teleport = next(fact for fact in facts if fact["fact_type"] == "operation_hotspot_teleport")

        self.assertEqual(hotspot["metadata"]["target_label"], "POI-00B7D7")
        self.assertAlmostEqual(hotspot["metadata"]["lat"], 52.280897)
        self.assertAlmostEqual(hotspot["metadata"]["lng"], 20.997489)
        self.assertNotIn("unknown:unknown", hotspot["metadata"]["cta_target_id"])
        self.assertEqual(teleport["metadata"]["target_label"], "POI-00B7D7")
        self.assertAlmostEqual(teleport["metadata"]["lat"], 52.280897)
        self.assertAlmostEqual(teleport["metadata"]["lng"], 20.997489)

    def test_blacknet_world_facts_snapshot_builds_real_conflict_target(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        conflicts = [{
            "id": 7,
            "conflict_key": "conflict:alice:bob",
            "participants": ["alice", "bob"],
            "status": "active",
            "targets": [{
                "target_id": "poi-putka",
                "name": "Piekarnia Putka",
                "label": "Piekarnia Putka",
                "lat": 52.22001,
                "lng": 21.01002,
                "target_type": "shop",
                "status": "contested",
            }],
        }]

        with patch.object(run.user_store, "list_profiles", return_value=[]), \
                patch.object(run, "get_app_catalog", return_value=[]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=conflicts), \
                patch.object(run, "build_blacknet_radio_facts", return_value=[]):
            snapshot = build_blacknet_world_facts_snapshot(now=now)

        conflict_facts = [
            fact for fact in snapshot["facts"]
            if fact["fact_type"] == "conflict_target_alert"
        ]
        self.assertEqual(len(conflict_facts), 1)
        fact = conflict_facts[0]
        self.assertEqual(fact["category"], "Piekarnia Putka")
        self.assertEqual(fact["value"], 1)
        self.assertEqual(fact["metadata"]["target_id"], "poi-putka")
        self.assertEqual(fact["metadata"]["target_label"], "Piekarnia Putka")
        self.assertEqual(fact["metadata"]["status"], "contested")
        self.assertEqual(fact["metadata"]["participants_count"], 2)
        self.assertEqual(fact["metadata"]["cta_target_id"], "poi-putka")
        self.assertAlmostEqual(fact["metadata"]["lat"], 52.22001)
        self.assertAlmostEqual(fact["metadata"]["lng"], 21.01002)

    def test_blacknet_conflict_target_uses_conflict_coordinates_when_target_is_partial(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        conflicts = [{
            "id": 8,
            "conflict_key": "conflict:partial",
            "participants": ["alice", "bob"],
            "status": "active",
            "lat": 52.280897,
            "lng": 20.997489,
            "targets": [{
                "target_id": "poi-00b7d7",
                "label": "Conflict-00B7D7",
                "status": "contested",
            }],
        }]

        with patch.object(run.user_store, "list_profiles", return_value=[]), \
                patch.object(run, "get_app_catalog", return_value=[]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=conflicts), \
                patch.object(run, "build_blacknet_radio_facts", return_value=[]):
            snapshot = build_blacknet_world_facts_snapshot(now=now)

        fact = next(item for item in snapshot["facts"] if item["fact_type"] == "conflict_target_alert")
        self.assertEqual(fact["metadata"]["target_label"], "Conflict-00B7D7")
        self.assertEqual(fact["metadata"]["cta_target_id"], "poi-00b7d7")
        self.assertAlmostEqual(fact["metadata"]["lat"], 52.280897)
        self.assertAlmostEqual(fact["metadata"]["lng"], 20.997489)

    def test_blacknet_conflict_without_coordinates_does_not_emit_unknown_map_target(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        conflicts = [{
            "id": 9,
            "conflict_key": "conflict:unknown",
            "participants": ["alice", "bob"],
            "status": "active",
            "targets": [{
                "label": "Conflict-00B7D7",
                "status": "contested",
            }],
        }]

        with patch.object(run.user_store, "list_profiles", return_value=[]), \
                patch.object(run, "get_app_catalog", return_value=[]), \
                patch.object(run.territory_conflict_store, "list_active", return_value=conflicts), \
                patch.object(run.os.path, "isdir", return_value=False):
            snapshot = build_blacknet_world_facts_snapshot(now=now)

        target_alerts = [
            fact for fact in snapshot["facts"]
            if fact["fact_type"] == "conflict_target_alert"
        ]
        self.assertEqual(target_alerts, [])
        area_alert = next(item for item in snapshot["facts"] if item["fact_type"] == "contested_area_alert")
        self.assertEqual(area_alert["metadata"]["target_count"], 1)
        serialized = json.dumps(snapshot, sort_keys=True)
        self.assertNotIn("unknown:unknown", serialized)


class BlackNetWorldSignalPublisherTest(unittest.TestCase):
    def _client_with_user(self, username="alice"):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = username
        return client

    def test_blacknet_world_signal_publisher_converts_fact_to_signal(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-1",
            "facts": [{
                "fact_id": "fact-market-gps",
                "fact_type": "market_top_sector_7d",
                "category": "gps",
                "region_id": "global",
                "subject_id": "gps",
                "value": 340,
                "previous_value": None,
                "change_percent": 0,
                "importance": 80,
                "confidence": 0.9,
                "observed_at": "2026-07-11T11:00:00Z",
                "expires_at": "2026-07-11T12:10:00Z",
                "source_system": "ghost_exchange",
                "metadata": {
                    "volume_mb": 42,
                    "sector_key": "gps",
                    "cta_target_id": "gps",
                },
            }],
        }

        snapshot = build_blacknet_world_signals(facts, now=now)

        self.assertEqual(snapshot["snapshot_type"], "blacknet_world_signals")
        self.assertEqual(snapshot["source"], "world_generated")
        self.assertFalse(snapshot["diagnostics"]["local_static_allowed"])
        self.assertEqual(snapshot["diagnostics"]["local_static_policy"], "dev_flag_only")
        self.assertEqual(len(snapshot["signals"]), 1)
        signal = snapshot["signals"][0]
        self.assertEqual(signal["source"], "world_generated")
        self.assertEqual(signal["fact_id"], "fact-market-gps")
        self.assertEqual(signal["signal_type"], "data_demand")
        self.assertEqual(signal["cta_action"], "open_exchange_category")
        self.assertEqual(signal["cta_target_id"], "gps")
        self.assertEqual(signal["entity_id"], "gps")
        self.assertEqual(signal["world_version"], "facts-1")
        self.assertIn("radar", signal)

    def test_blacknet_world_signal_publisher_skips_below_threshold_and_is_deterministic(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-2",
            "facts": [
                {
                    "fact_id": "fact-market-small",
                    "fact_type": "market_sales_7d",
                    "category": "market",
                    "region_id": "global",
                    "subject_id": "market",
                    "value": 50,
                    "previous_value": None,
                    "change_percent": 0,
                    "importance": 50,
                    "confidence": 0.9,
                    "observed_at": "2026-07-11T11:00:00Z",
                    "expires_at": "2026-07-11T12:10:00Z",
                    "source_system": "ghost_exchange",
                    "metadata": {},
                },
                {
                    "fact_id": "fact-ops",
                    "fact_type": "operations_active_count",
                    "category": "operations",
                    "region_id": "global",
                    "subject_id": "operations",
                    "value": 3,
                    "previous_value": None,
                    "change_percent": 0,
                    "importance": 70,
                    "confidence": 0.9,
                    "observed_at": "2026-07-11T11:00:00Z",
                    "expires_at": "2026-07-11T12:10:00Z",
                    "source_system": "operations",
                    "metadata": {},
                },
            ],
        }

        first = build_blacknet_world_signals(facts, now=now)
        second = build_blacknet_world_signals(facts, now=now)

        self.assertEqual(len(first["signals"]), 1)
        self.assertEqual(first["signals"][0]["fact_id"], "fact-ops")
        self.assertEqual(first["signals"], second["signals"])
        self.assertEqual(first["version"], second["version"])

    def test_blacknet_world_signal_publisher_can_page_until_out_of_signal(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        base = {
            "previous_value": None,
            "change_percent": 0,
            "importance": 80,
            "confidence": 0.9,
            "observed_at": "2026-07-11T11:00:00Z",
            "expires_at": "2026-07-11T12:10:00Z",
        }
        facts = {"version": "facts-paged", "facts": [
            {**base, "fact_id": "ops-active", "fact_type": "operations_active_count", "category": "operations", "region_id": "global", "subject_id": "operations", "value": 3, "source_system": "operations", "metadata": {}},
            {**base, "fact_id": "market-sector", "fact_type": "market_top_sector_7d", "category": "network", "region_id": "global", "subject_id": "network", "value": 1200, "source_system": "ghost_exchange", "metadata": {"sector_key": "network", "volume_mb": 300, "cta_target_id": "network"}},
            {**base, "fact_id": "googleplex", "fact_type": "googleplex_product_signal", "category": "storage", "region_id": "global", "subject_id": "storage_ghost_vault_basic", "value": 650, "source_system": "googleplex", "metadata": {"product_id": "storage_ghost_vault_basic", "product_name": "Ghost Vault Basic", "product_type": "storage_upgrade", "price": 650, "downloads": 4, "temperature": 72, "cta_target_id": "storage_ghost_vault_basic", "cta_query": "Ghost Vault Basic"}},
            {**base, "fact_id": "radio", "fact_type": "radio_channels_available", "category": "radio", "region_id": "global", "subject_id": "radio", "value": 2, "source_system": "radio", "metadata": {"tracks_total": 25, "channel_id": "blacknet_radio_2", "track_file": "002_signal.mp3"}},
        ]}

        first = build_blacknet_world_signals(facts, now=now, limit=2)
        first_ids = {signal["id"] for signal in first["signals"]}
        second = build_blacknet_world_signals(facts, now=now, limit=4, exclude_ids=first_ids)
        second_ids = {signal["id"] for signal in second["signals"]}
        all_ids = first_ids | second_ids
        empty = build_blacknet_world_signals(facts, now=now, limit=4, exclude_ids=all_ids)

        self.assertEqual(len(first["signals"]), 2)
        self.assertTrue(second_ids)
        self.assertFalse(first_ids.intersection(second_ids))
        self.assertEqual(empty["signals"][0]["signal_type"], "out_of_signal")
        self.assertTrue(empty["diagnostics"]["out_of_signal"])
        self.assertGreaterEqual(empty["diagnostics"]["excluded"], len(all_ids))

    def test_blacknet_world_signal_publisher_keeps_family_diversity_in_first_batch(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        base = {
            "previous_value": None,
            "change_percent": 0,
            "importance": 90,
            "confidence": 0.9,
            "observed_at": "2026-07-11T11:00:00Z",
            "expires_at": "2026-07-11T12:10:00Z",
        }
        googleplex_facts = [
            {
                **base,
                "fact_id": f"googleplex-{index}",
                "fact_type": "googleplex_product_signal",
                "category": f"tool-{index}",
                "region_id": "global",
                "subject_id": f"tool-{index}",
                "value": 650 + index,
                "source_system": "googleplex",
                "metadata": {
                    "product_id": f"tool-{index}",
                    "product_name": f"Tool {index}",
                    "product_type": "system_tool",
                    "price": 650 + index,
                    "downloads": index,
                    "temperature": 80,
                    "cta_target_id": f"tool-{index}",
                    "cta_query": f"Tool {index}",
                },
            }
            for index in range(12)
        ]
        facts = {
            "version": "facts-diverse",
            "facts": googleplex_facts + [
                {**base, "fact_id": "ops-teleport", "fact_type": "operation_hotspot_teleport", "category": "Piekarnia Putka", "region_id": "poi-putka", "subject_id": "poi-putka", "value": 2, "source_system": "operations", "metadata": {"target_id": "poi-putka", "target_label": "Piekarnia Putka", "lat": 52.22, "lng": 21.01, "cta_target_id": "poi-putka"}},
                {**base, "fact_id": "radio", "fact_type": "radio_channels_available", "category": "radio", "region_id": "global", "subject_id": "radio", "value": 2, "source_system": "radio", "metadata": {"tracks_total": 25, "channel_id": "blacknet_radio_2", "track_file": "002_signal.mp3"}},
                {**base, "fact_id": "world", "fact_type": "system_messages_24h", "category": "system", "region_id": "global", "subject_id": "system", "value": 3, "source_system": "system", "metadata": {"thread_scope": "group", "thread_peer": "global", "thread_channel": "world"}},
            ],
        }

        snapshot = build_blacknet_world_signals(facts, now=now, limit=8)
        signal_types = {signal["signal_type"] for signal in snapshot["signals"]}

        self.assertIn("product_opportunity", signal_types)
        self.assertIn("teleport_hotspot", signal_types)
        self.assertIn("radio_promotion", signal_types)
        self.assertIn("system_incident", signal_types)

    def test_blacknet_world_signal_publisher_expires_old_fact(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-3",
            "facts": [{
                "fact_id": "fact-expired",
                "fact_type": "operations_active_count",
                "category": "operations",
                "region_id": "global",
                "subject_id": "operations",
                "value": 12,
                "previous_value": None,
                "change_percent": 0,
                "importance": 80,
                "confidence": 0.9,
                "observed_at": "2026-07-11T10:00:00Z",
                "expires_at": "2026-07-11T11:59:00Z",
                "source_system": "operations",
                "metadata": {},
            }],
        }

        snapshot = build_blacknet_world_signals(facts, now=now)

        self.assertEqual(len(snapshot["signals"]), 1)
        self.assertEqual(snapshot["signals"][0]["signal_type"], "out_of_signal")
        self.assertTrue(snapshot["diagnostics"]["out_of_signal"])
        self.assertFalse(snapshot["diagnostics"]["local_static_allowed"])

    def test_blacknet_world_signal_publisher_converts_operation_hotspot(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-hotspot",
            "facts": [{
                "fact_id": "fact-hotspot-putka",
                "fact_type": "operation_hotspot_activity",
                "category": "Piekarnia Putka",
                "region_id": "poi-putka",
                "subject_id": "poi-putka",
                "value": 2,
                "previous_value": None,
                "change_percent": 0,
                "importance": 80,
                "confidence": 0.9,
                "observed_at": "2026-07-11T11:00:00Z",
                "expires_at": "2026-07-11T12:10:00Z",
                "source_system": "operations",
                "metadata": {
                    "target_id": "poi-putka",
                    "target_label": "Piekarnia Putka",
                    "lat": 52.22001,
                    "lng": 21.01002,
                    "operation_count": 2,
                    "cta_target_id": "poi-putka",
                },
            }],
        }

        snapshot = build_blacknet_world_signals(facts, now=now)

        self.assertEqual(len(snapshot["signals"]), 1)
        signal = snapshot["signals"][0]
        self.assertEqual(signal["signal_type"], "operation_hotspot_activity")
        self.assertEqual(signal["title"], "OPERACJE / PIEKARNIA PUTKA")
        self.assertEqual(signal["stat"], "Piekarnia Putka")
        self.assertEqual(signal["cta_action"], "focus_map_target")
        self.assertEqual(signal["cta_target_id"], "poi-putka")
        self.assertEqual(signal["entity_id"], "poi-putka")

    def test_blacknet_world_signal_publisher_converts_conflict_target(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-conflict",
            "facts": [{
                "fact_id": "fact-conflict-putka",
                "fact_type": "conflict_target_alert",
                "category": "Piekarnia Putka",
                "region_id": "poi-putka",
                "subject_id": "poi-putka",
                "value": 1,
                "previous_value": None,
                "change_percent": 0,
                "importance": 90,
                "confidence": 0.86,
                "observed_at": "2026-07-11T11:00:00Z",
                "expires_at": "2026-07-11T12:10:00Z",
                "source_system": "conflicts",
                "metadata": {
                    "target_id": "poi-putka",
                    "target_label": "Piekarnia Putka",
                    "lat": 52.22001,
                    "lng": 21.01002,
                    "conflict_keys": ["conflict:alice:bob"],
                    "participants_count": 2,
                    "status": "contested",
                    "cta_target_id": "poi-putka",
                },
            }],
        }

        snapshot = build_blacknet_world_signals(facts, now=now)

        self.assertEqual(len(snapshot["signals"]), 1)
        signal = snapshot["signals"][0]
        self.assertEqual(signal["signal_type"], "conflict_target_alert")
        self.assertEqual(signal["title"], "CONFLICT / PIEKARNIA PUTKA")
        self.assertEqual(signal["stat"], "Piekarnia Putka")
        self.assertEqual(signal["tone"], "red")
        self.assertEqual(signal["cta_action"], "focus_map_target")
        self.assertEqual(signal["cta_target_id"], "poi-putka")
        self.assertEqual(signal["entity_id"], "poi-putka")

    def test_blacknet_world_signals_endpoint_is_readonly_and_requires_login(self):
        response = run.app.test_client().get("/api/blacknet/world-signals")
        self.assertEqual(response.status_code, 401)

        client = self._client_with_user()
        fake_facts = {
            "version": "facts-endpoint",
            "facts": [{
                "fact_id": "fact-ops-endpoint",
                "fact_type": "operations_active_count",
                "category": "operations",
                "region_id": "global",
                "subject_id": "operations",
                "value": 2,
                "previous_value": None,
                "change_percent": 0,
                "importance": 70,
                "confidence": 0.9,
                "observed_at": "2026-07-11T11:00:00Z",
                "expires_at": "2999-07-11T12:10:00Z",
                "source_system": "operations",
                "metadata": {},
            }],
        }
        with patch.object(run, "build_blacknet_world_facts_snapshot", return_value=fake_facts), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
            response = client.get("/api/blacknet/world-signals")

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["snapshot"]["snapshot_type"], "blacknet_world_signals")
        self.assertEqual(data["snapshot"]["signals"][0]["fact_id"], "fact-ops-endpoint")

    def test_blacknet_cta_action_contract_covers_bridge_families(self):
        required_actions = {
            "teleport_to_hotspot",
            "open_googleplex_search",
            "open_exchange_market",
            "open_exchange_category",
            "play_radio_podcast",
            "open_map_region",
            "focus_map_target",
            "show_hotspot",
            "open_operation",
            "start_operation",
            "accept_blacknet_job",
            "open_cyberner_thread",
            "open_blacknet_detail",
            "open_blacknet_dossier",
            "open_blacknet_report",
            "none",
        }
        self.assertTrue(required_actions.issubset(BLACKNET_ALLOWED_CTA_ACTIONS))

    def test_blacknet_publisher_emits_only_allowed_cta_actions(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-cta",
            "facts": [
                {
                    "fact_id": f"fact-{fact_type}",
                    "fact_type": fact_type,
                    "category": "gps",
                    "region_id": "global",
                    "subject_id": "gps",
                    "value": 500,
                    "previous_value": None,
                    "change_percent": 0,
                    "importance": 90,
                    "confidence": 0.9,
                    "observed_at": "2026-07-11T11:00:00Z",
                    "expires_at": "2026-07-11T12:10:00Z",
                    "source_system": "test",
                    "metadata": {"volume_mb": 42, "file_count": 3, "products": 2, "tracks_total": 5},
                }
                for fact_type in (
                    "operations_active_count",
                    "operations_top_type",
                    "operation_hotspot_activity",
                    "operation_hotspot_teleport",
                    "target_operation_burst",
                    "conflict_target_alert",
                    "contested_area_alert",
                    "market_sales_7d",
                    "market_top_sector_7d",
                    "googleplex_product_signal",
                    "radio_channels_available",
                    "system_messages_24h",
                )
            ],
        }

        snapshot = build_blacknet_world_signals(facts, now=now)

        self.assertGreaterEqual(len(snapshot["signals"]), 1)
        for signal in snapshot["signals"]:
            self.assertIn(signal["cta_action"], BLACKNET_ALLOWED_CTA_ACTIONS)

    def test_blacknet_publisher_carries_real_cta_targets(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-targets",
            "facts": [
                {
                    "fact_id": "fact-googleplex",
                    "fact_type": "googleplex_product_signal",
                    "category": "storage",
                    "region_id": "global",
                    "subject_id": "storage_ghost_vault_basic",
                    "value": 650,
                    "previous_value": None,
                    "change_percent": 0,
                    "importance": 60,
                    "confidence": 0.9,
                    "observed_at": "2026-07-11T11:00:00Z",
                    "expires_at": "2026-07-11T12:10:00Z",
                    "source_system": "googleplex",
                    "metadata": {
                        "product_id": "storage_ghost_vault_basic",
                        "product_name": "Ghost Vault Basic",
                        "product_type": "storage_upgrade",
                        "price": 650,
                        "downloads": 4,
                        "temperature": 72,
                        "cta_target_id": "storage_ghost_vault_basic",
                        "cta_query": "Ghost Vault Basic",
                    },
                },
                {
                    "fact_id": "fact-radio",
                    "fact_type": "radio_channels_available",
                    "category": "radio",
                    "region_id": "global",
                    "subject_id": "radio",
                    "value": 2,
                    "previous_value": None,
                    "change_percent": 0,
                    "importance": 30,
                    "confidence": 0.9,
                    "observed_at": "2026-07-11T11:00:00Z",
                    "expires_at": "2026-07-11T12:10:00Z",
                    "source_system": "radio",
                    "metadata": {
                        "tracks_total": 9,
                        "channel_id": "blacknet_radio_2",
                        "channel_name": "BlackNet Radio",
                        "track_file": "002_signal.mp3",
                        "track_index": 2,
                        "track_title": "Signal",
                    },
                },
                {
                    "fact_id": "fact-market-sector",
                    "fact_type": "market_top_sector_7d",
                    "category": "network",
                    "region_id": "global",
                    "subject_id": "network",
                    "value": 1200,
                    "previous_value": None,
                    "change_percent": 0,
                    "importance": 80,
                    "confidence": 0.9,
                    "observed_at": "2026-07-11T11:00:00Z",
                    "expires_at": "2026-07-11T12:10:00Z",
                    "source_system": "ghost_exchange",
                    "metadata": {
                        "sector_id": "network",
                        "sector_key": "network",
                        "sector_label": "Sieci",
                        "market_category": "network",
                        "volume_mb": 300,
                        "average_price": 120,
                        "cta_target_id": "network",
                        "cta_query": "network",
                    },
                },
                {
                    "fact_id": "fact-world",
                    "fact_type": "system_messages_24h",
                    "category": "system",
                    "region_id": "global",
                    "subject_id": "system",
                    "value": 3,
                    "previous_value": None,
                    "change_percent": 0,
                    "importance": 70,
                    "confidence": 0.9,
                    "observed_at": "2026-07-11T11:00:00Z",
                    "expires_at": "2026-07-11T12:10:00Z",
                    "source_system": "system",
                    "metadata": {
                        "thread_scope": "group",
                        "thread_peer": "global",
                        "thread_channel": "world",
                        "cta_target_id": "global",
                        "cta_query": "WORLD",
                    },
                },
            ],
        }

        snapshot = build_blacknet_world_signals(facts, now=now)
        by_fact = {signal["fact_id"]: signal for signal in snapshot["signals"]}

        self.assertEqual(by_fact["fact-googleplex"]["cta_action"], "open_googleplex_search")
        self.assertEqual(by_fact["fact-googleplex"]["cta_target_id"], "storage_ghost_vault_basic")
        self.assertEqual(by_fact["fact-googleplex"]["entity_id"], "storage_ghost_vault_basic")
        self.assertEqual(by_fact["fact-googleplex"]["cta_query"], "Ghost Vault Basic")
        self.assertEqual(by_fact["fact-googleplex"]["metadata"]["product_name"], "Ghost Vault Basic")
        self.assertEqual(by_fact["fact-radio"]["cta_action"], "play_radio_podcast")
        self.assertEqual(by_fact["fact-radio"]["cta_target_id"], "blacknet_radio_2")
        self.assertEqual(by_fact["fact-radio"]["entity_id"], "blacknet_radio_2")
        self.assertEqual(by_fact["fact-radio"]["metadata"]["channel_id"], "blacknet_radio_2")
        self.assertEqual(by_fact["fact-radio"]["metadata"]["track_file"], "002_signal.mp3")
        self.assertEqual(by_fact["fact-market-sector"]["cta_action"], "open_exchange_category")
        self.assertEqual(by_fact["fact-market-sector"]["cta_target_id"], "network")
        self.assertEqual(by_fact["fact-market-sector"]["entity_id"], "network")
        self.assertEqual(by_fact["fact-market-sector"]["metadata"]["sector_key"], "network")
        self.assertEqual(by_fact["fact-world"]["cta_action"], "open_cyberner_thread")
        self.assertEqual(by_fact["fact-world"]["cta_target"], "world")
        self.assertEqual(by_fact["fact-world"]["entity_id"], "global")
        self.assertEqual(by_fact["fact-world"]["metadata"]["thread_peer"], "global")

        package = build_blacknet_ollama_outbox(facts, snapshot, now=now)
        outbox_by_fact = {signal["fact_id"]: signal for signal in package["selected_signals"]}

        self.assertEqual(outbox_by_fact["fact-googleplex"]["cta_query"], "Ghost Vault Basic")
        self.assertEqual(outbox_by_fact["fact-googleplex"]["metadata"]["product_name"], "Ghost Vault Basic")
        self.assertEqual(outbox_by_fact["fact-radio"]["cta_target_id"], "blacknet_radio_2")
        self.assertEqual(outbox_by_fact["fact-radio"]["metadata"]["track_file"], "002_signal.mp3")
        self.assertEqual(outbox_by_fact["fact-market-sector"]["cta_query"], "network")
        self.assertEqual(outbox_by_fact["fact-market-sector"]["metadata"]["sector_key"], "network")
        self.assertEqual(outbox_by_fact["fact-world"]["cta_target"], "world")
        self.assertEqual(outbox_by_fact["fact-world"]["metadata"]["thread_channel"], "world")

    def test_blacknet_signal_families_keep_cta_targets_semantic(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        base = {
            "previous_value": None,
            "change_percent": 0,
            "importance": 80,
            "confidence": 0.9,
            "observed_at": "2026-07-11T11:00:00Z",
            "expires_at": "2026-07-11T12:10:00Z",
        }
        facts = {"version": "facts-all-families", "facts": [
            {**base, "fact_id": "ops-active", "fact_type": "operations_active_count", "category": "operations", "region_id": "global", "subject_id": "operations", "value": 3, "source_system": "operations", "metadata": {}},
            {**base, "fact_id": "ops-top", "fact_type": "operations_top_type", "category": "persistent_sniffer", "region_id": "global", "subject_id": "persistent_sniffer", "value": 262, "source_system": "operations", "metadata": {"operation_type": "persistent_sniffer"}},
            {**base, "fact_id": "ops-hotspot", "fact_type": "operation_hotspot_activity", "category": "Piekarnia Putka", "region_id": "poi-putka", "subject_id": "poi-putka", "value": 2, "source_system": "operations", "metadata": {"target_id": "poi-putka", "target_label": "Piekarnia Putka", "lat": 52.22, "lng": 21.01, "cta_target_id": "poi-putka"}},
            {**base, "fact_id": "ops-teleport", "fact_type": "operation_hotspot_teleport", "category": "Piekarnia Putka", "region_id": "poi-putka", "subject_id": "poi-putka", "value": 2, "source_system": "operations", "metadata": {"target_id": "poi-putka", "target_label": "Piekarnia Putka", "lat": 52.22, "lng": 21.01, "cta_target_id": "poi-putka"}},
            {**base, "fact_id": "ops-burst", "fact_type": "target_operation_burst", "category": "Zabka", "region_id": "poi-zabka", "subject_id": "poi-zabka", "value": 4, "source_system": "operations", "metadata": {"target_id": "poi-zabka", "target_label": "Zabka", "lat": 52.23, "lng": 21.02, "cta_target_id": "poi-zabka"}},
            {**base, "fact_id": "conflict-target", "fact_type": "conflict_target_alert", "category": "Conflict-00B7D7", "region_id": "poi-conflict", "subject_id": "poi-conflict", "value": 1, "source_system": "conflicts", "metadata": {"target_id": "poi-conflict", "target_label": "Conflict-00B7D7", "lat": 52.24, "lng": 21.03, "cta_target_id": "poi-conflict"}},
            {**base, "fact_id": "conflict-area", "fact_type": "contested_area_alert", "category": "conflicts", "region_id": "global", "subject_id": "conflicts", "value": 2, "source_system": "conflicts", "metadata": {}},
            {**base, "fact_id": "market-all", "fact_type": "market_sales_7d", "category": "market", "region_id": "global", "subject_id": "market", "value": 500, "source_system": "ghost_exchange", "metadata": {"file_count": 5, "volume_mb": 40}},
            {**base, "fact_id": "market-sector", "fact_type": "market_top_sector_7d", "category": "network", "region_id": "global", "subject_id": "network", "value": 1200, "source_system": "ghost_exchange", "metadata": {"sector_key": "network", "volume_mb": 300, "cta_target_id": "network"}},
            {**base, "fact_id": "googleplex", "fact_type": "googleplex_product_signal", "category": "storage", "region_id": "global", "subject_id": "storage_ghost_vault_basic", "value": 650, "source_system": "googleplex", "metadata": {"product_id": "storage_ghost_vault_basic", "product_name": "Ghost Vault Basic", "product_type": "storage_upgrade", "price": 650, "downloads": 4, "temperature": 72, "cta_target_id": "storage_ghost_vault_basic", "cta_query": "Ghost Vault Basic"}},
            {**base, "fact_id": "radio", "fact_type": "radio_channels_available", "category": "radio", "region_id": "global", "subject_id": "radio", "value": 2, "source_system": "radio", "metadata": {"tracks_total": 25, "channel_id": "blacknet_radio_2", "track_file": "002_signal.mp3"}},
            {**base, "fact_id": "world", "fact_type": "system_messages_24h", "category": "system", "region_id": "global", "subject_id": "system", "value": 3, "source_system": "system", "metadata": {"thread_scope": "group", "thread_peer": "global", "thread_channel": "world"}},
        ]}

        snapshot = build_blacknet_world_signals(facts, now=now, limit=20)
        by_fact = {signal["fact_id"]: signal for signal in snapshot["signals"]}

        self.assertEqual(set(by_fact), {fact["fact_id"] for fact in facts["facts"]})
        self.assertEqual(by_fact["ops-active"]["cta_action"], "open_map")
        self.assertEqual(by_fact["ops-active"]["cta_target_id"], "")
        self.assertEqual(by_fact["ops-top"]["cta_action"], "open_map")
        self.assertEqual(by_fact["ops-top"]["cta_target_id"], "")
        for fact_id in ("ops-hotspot", "ops-burst", "conflict-target"):
            self.assertEqual(by_fact[fact_id]["cta_action"], "focus_map_target")
            self.assertTrue(by_fact[fact_id]["cta_target_id"])
            self.assertIsNotNone(by_fact[fact_id]["metadata"].get("lat"))
            self.assertIsNotNone(by_fact[fact_id]["metadata"].get("lng"))
        self.assertEqual(by_fact["ops-teleport"]["cta_action"], "teleport_to_hotspot")
        self.assertEqual(by_fact["ops-teleport"]["cta_target_id"], "poi-putka")
        self.assertIsNotNone(by_fact["ops-teleport"]["metadata"].get("lat"))
        self.assertIsNotNone(by_fact["ops-teleport"]["metadata"].get("lng"))
        self.assertEqual(by_fact["conflict-area"]["cta_action"], "open_map")
        self.assertEqual(by_fact["conflict-area"]["cta_target_id"], "")
        self.assertEqual(by_fact["market-all"]["cta_action"], "open_exchange_market")
        self.assertEqual(by_fact["market-sector"]["cta_action"], "open_exchange_category")
        self.assertEqual(by_fact["market-sector"]["cta_target_id"], "network")
        self.assertEqual(by_fact["googleplex"]["cta_action"], "open_googleplex_search")
        self.assertEqual(by_fact["googleplex"]["cta_query"], "Ghost Vault Basic")
        self.assertEqual(by_fact["radio"]["cta_action"], "play_radio_podcast")
        self.assertEqual(by_fact["radio"]["cta_target_id"], "blacknet_radio_2")
        self.assertEqual(by_fact["world"]["cta_action"], "open_cyberner_thread")

    def test_blacknet_teleport_bridge_moves_to_whitelisted_hotspot(self):
        client = self._client_with_user("alice")
        position_result = {
            "changed": True,
            "position": {"lat": 52.1934, "lng": 21.0348},
            "version": 7,
            "updated_at": "2026-08-24T10:00:00Z",
        }

        with patch.object(run, "load_profile_readonly", side_effect=AssertionError("profile should not load")), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("profile writer should not run")), \
                patch.object(run.player_position_store, "upsert", return_value=position_result) as position_upsert, \
                patch.object(run.identity_projection_store, "get_identity", return_value={"username": "alice"}), \
                patch.object(run, "notify_area_intrusion", return_value=None), \
                patch.object(run, "record_map_player_actor_delta") as record_delta:
            response = client.post("/api/blacknet/cta/teleport", json={"hotspot_id": "mokotow"})

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["hotspot"]["id"], "mokotow")
        self.assertAlmostEqual(data["curently_possition"]["lat"], 52.1934)
        self.assertAlmostEqual(data["curently_possition"]["lng"], 21.0348)
        position_upsert.assert_called_once_with(
            "alice", {"lat": 52.1934, "lng": 21.0348}, source="blacknet"
        )
        self.assertEqual(data["position_version"], 7)
        record_delta.assert_called_once()

    def test_blacknet_teleport_bridge_moves_to_signal_coordinates(self):
        client = self._client_with_user("alice")
        position_result = {
            "changed": True,
            "position": {"lat": 52.2809, "lng": 20.9974},
            "version": 8,
            "updated_at": "2026-08-24T10:01:00Z",
        }

        with patch.object(run, "load_profile_readonly", side_effect=AssertionError("profile should not load")), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("profile writer should not run")), \
                patch.object(run.player_position_store, "upsert", return_value=position_result) as position_upsert, \
                patch.object(run.identity_projection_store, "get_identity", return_value={"username": "alice"}), \
                patch.object(run, "notify_area_intrusion", return_value=None), \
                patch.object(run, "record_map_player_actor_delta") as record_delta:
            response = client.post("/api/blacknet/cta/teleport", json={
                "lat": 52.2809,
                "lng": 20.9974,
                "label": "POI test",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertIsNone(data["hotspot"])
        self.assertAlmostEqual(data["curently_possition"]["lat"], 52.2809)
        self.assertAlmostEqual(data["curently_possition"]["lng"], 20.9974)
        position_upsert.assert_called_once_with(
            "alice", {"lat": 52.2809, "lng": 20.9974}, source="blacknet"
        )
        self.assertEqual(data["position_version"], 8)
        record_delta.assert_called_once()

    def test_ghostnetwork_teleport_resolves_public_entity_server_side(self):
        client = self._client_with_user("alice")

        class FakeGhostService:
            def get_snapshot_for_viewer(self, viewer):
                self.viewer = viewer
                return {"snapshot": {"parts": [{
                    "public_entity_id": "gn_public_1",
                    "display_label": "Widoczny modul",
                    "location_visibility": "exact",
                    "latitude": 52.25,
                    "longitude": 21.05,
                    "territory_id": "17",
                }]}}

        position_result = {
            "changed": True,
            "position": {"lat": 52.25, "lng": 21.05},
            "version": 9,
            "updated_at": "2026-08-24T10:02:00Z",
        }
        with patch.object(run.identity_projection_store, "get_identity", return_value={
                    "username": "alice", "clan_code": "virex"
                }), \
                patch.object(run, "get_ghostnetwork_service", return_value=FakeGhostService()), \
                patch.object(run.player_position_store, "upsert", return_value=position_result) as position_upsert, \
                patch.object(run, "load_profile_readonly", side_effect=AssertionError("profile should not load")), \
                patch.object(run, "notify_area_intrusion", return_value=None), \
                patch.object(run, "record_map_player_actor_delta"):
            response = client.post("/api/blacknet/cta/teleport", json={
                "source": "ghostnetwork_suite",
                "target_type": "ghostnetwork_part",
                "public_entity_id": "gn_public_1",
            })

        data = response.get_json()
        self.assertEqual(200, response.status_code)
        position_upsert.assert_called_once_with(
            "alice", {"lat": 52.25, "lng": 21.05}, source="ghostnetwork_suite"
        )
        self.assertEqual("exact", data["ghostnetwork_target"]["location_precision"])
        self.assertNotIn("part_id", data["ghostnetwork_target"])

    def test_hidden_ghostnetwork_part_uses_territory_centroid_not_private_anchor(self):
        client = self._client_with_user("alice")

        class FakeGhostService:
            def get_snapshot_for_viewer(self, viewer):
                return {"snapshot": {"parts": [{
                    "public_entity_id": "gn_hidden_1",
                    "display_label": "Sklasyfikowany modul",
                    "location_visibility": "territory_only",
                    "latitude": None,
                    "longitude": None,
                    "territory_id": "17",
                }]}}

        position_result = {
            "changed": True,
            "position": {"lat": 52.2, "lng": 21.1},
            "version": 10,
            "updated_at": "2026-08-24T10:03:00Z",
        }
        with patch.object(run.identity_projection_store, "get_identity", return_value={
                    "username": "alice", "clan_code": "virex"
                }), \
                patch.object(run, "get_ghostnetwork_service", return_value=FakeGhostService()), \
                patch.object(run.territory_store, "get_player_area", return_value={
                    "id": 17, "centroid_lat": 52.2, "centroid_lng": 21.1
                }), \
                patch.object(run.player_position_store, "upsert", return_value=position_result) as position_upsert, \
                patch.object(run, "notify_area_intrusion", return_value=None), \
                patch.object(run, "record_map_player_actor_delta"):
            response = client.post("/api/blacknet/cta/teleport", json={
                "source": "ghostnetwork_suite",
                "target_type": "ghostnetwork_part",
                "public_entity_id": "gn_hidden_1",
            })

        data = response.get_json()
        self.assertEqual(200, response.status_code)
        position_upsert.assert_called_once_with(
            "alice", {"lat": 52.2, "lng": 21.1}, source="ghostnetwork_suite"
        )
        self.assertEqual("territory", data["ghostnetwork_target"]["location_precision"])

    def test_ghostnetwork_teleport_rejects_client_coordinates_before_resolution(self):
        client = self._client_with_user("alice")
        with patch.object(run.player_position_store, "upsert") as position_upsert, \
                patch.object(run, "load_profile_readonly", side_effect=AssertionError("profile should not load")):
            response = client.post("/api/blacknet/cta/teleport", json={
                "source": "ghostnetwork_suite",
                "target_type": "ghostnetwork_part",
                "public_entity_id": "gn_public_1",
                "lat": 10,
                "lng": 20,
            })

        self.assertEqual(400, response.status_code)
        self.assertEqual("client_coordinates_forbidden", response.get_json()["error"])
        position_upsert.assert_not_called()

    def test_blacknet_teleport_bridge_rejects_unknown_hotspot(self):
        client = self._client_with_user("alice")
        with patch.object(run, "load_profile_readonly", side_effect=AssertionError("profile should not load")):
            response = client.post("/api/blacknet/cta/teleport", json={"hotspot_id": "unknown"})

        data = response.get_json()
        self.assertEqual(response.status_code, 404)
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "unknown_hotspot")

    def test_blacknet_ollama_outbox_sanitizes_facts_and_validates_contract(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-outbox",
            "facts": [{
                "fact_id": "fact-hotspot-private",
                "fact_type": "operation_hotspot_activity",
                "category": "Piekarnia Putka",
                "region_id": "poi-putka",
                "subject_id": "poi-putka",
                "value": 2,
                "previous_value": None,
                "change_percent": 0,
                "importance": 90,
                "confidence": 0.9,
                "observed_at": "2026-07-11T11:00:00Z",
                "expires_at": "2026-07-11T12:10:00Z",
                "source_system": "operations",
                "metadata": {
                    "target_id": "poi-putka",
                    "target_label": "Piekarnia Putka",
                    "lat": 52.22001,
                    "lng": 21.01002,
                    "username": "alice",
                    "participants": ["alice", "bob"],
                    "email": "alice@example.test",
                    "secret": "hidden",
                    "cta_target_id": "poi-putka",
                },
            }],
        }
        signals = build_blacknet_world_signals(facts, now=now)

        package = build_blacknet_ollama_outbox(facts, signals, now=now)

        self.assertEqual(package["status"], "ready")
        self.assertTrue(package["validation"]["ok"])
        self.assertFalse(package["diagnostics"]["ollama_executed"])
        self.assertEqual(package["facts"][0]["fact_id"], "fact-hotspot-private")
        self.assertEqual(package["selected_signals"][0]["fact_id"], "fact-hotspot-private")
        exported_metadata = package["facts"][0]["metadata"]
        self.assertEqual(exported_metadata["target_id"], "poi-putka")
        self.assertNotIn("username", exported_metadata)
        self.assertNotIn("participants", exported_metadata)
        self.assertNotIn("email", exported_metadata)
        self.assertNotIn("secret", exported_metadata)
        self.assertTrue(set(package["allowed_actions"]).issubset(BLACKNET_ALLOWED_CTA_ACTIONS))
        self.assertIn("poi-putka", package["existing_identifiers"]["target_ids"])

        invalid = {
            "schema_version": package["schema_version"],
            "digest_id": "empty",
            "facts": [],
            "allowed_actions": [],
        }
        self.assertIn("no_facts", validate_blacknet_ollama_outbox(invalid))

    def test_blacknet_ollama_outbox_file_store_and_status_update(self):
        now = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        facts = {
            "version": "facts-store",
            "facts": [{
                "fact_id": "fact-store-market",
                "fact_type": "market_sales_7d",
                "category": "market",
                "region_id": "global",
                "subject_id": "market",
                "value": 500,
                "previous_value": None,
                "change_percent": 0,
                "importance": 80,
                "confidence": 0.9,
                "observed_at": "2026-07-11T11:00:00Z",
                "expires_at": "2026-07-11T12:10:00Z",
                "source_system": "ghost_exchange",
                "metadata": {"file_count": 5, "volume_mb": 40},
            }],
        }
        package = build_blacknet_ollama_outbox(facts, build_blacknet_world_signals(facts, now=now), now=now)

        with tempfile.TemporaryDirectory() as tmpdir, \
                patch.object(run, "BLACKNET_OLLAMA_OUTBOX_DIR", tmpdir):
            path = write_blacknet_ollama_outbox(package)
            self.assertTrue(os.path.exists(path))
            loaded = read_blacknet_ollama_outbox(package["digest_id"])
            self.assertEqual(loaded["digest_id"], package["digest_id"])
            latest = latest_blacknet_ollama_outbox()
            self.assertEqual(latest["digest_id"], package["digest_id"])

            updated, error = update_blacknet_ollama_outbox_status(
                package["digest_id"],
                "processing",
                message="worker picked package",
            )

            self.assertEqual(error, "")
            self.assertEqual(updated["status"], "processing")
            self.assertIn("status_updated_at", updated)
            self.assertEqual(read_blacknet_ollama_outbox(package["digest_id"])["status"], "processing")

    def test_blacknet_ollama_outbox_endpoints_are_admin_only_and_readonly(self):
        fake_facts = {
            "version": "facts-endpoint",
            "facts": [{
                "fact_id": "fact-endpoint-ops",
                "fact_type": "operations_active_count",
                "category": "operations",
                "region_id": "global",
                "subject_id": "operations",
                "value": 2,
                "previous_value": None,
                "change_percent": 0,
                "importance": 70,
                "confidence": 0.9,
                "observed_at": "2026-07-11T11:00:00Z",
                "expires_at": "2999-07-11T12:10:00Z",
                "source_system": "operations",
                "metadata": {},
            }],
        }
        non_admin = self._client_with_user("alice")
        self.assertEqual(non_admin.get("/api/blacknet/ollama/outbox/latest").status_code, 403)

        client = self._client_with_user("admin")
        with tempfile.TemporaryDirectory() as tmpdir, \
                patch.object(run, "BLACKNET_OLLAMA_OUTBOX_DIR", tmpdir), \
                patch.object(run, "build_blacknet_world_facts_snapshot", return_value=fake_facts), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")):
            generated = client.post("/api/blacknet/ollama/outbox/generate")
            generated_data = generated.get_json()
            digest_id = generated_data["digest_id"]
            latest = client.get("/api/blacknet/ollama/outbox/latest")
            fetched = client.get(f"/api/blacknet/ollama/outbox/{digest_id}")
            updated = client.post(
                f"/api/blacknet/ollama/outbox/{digest_id}/status",
                json={"status": "processing", "message": "taken"},
            )

        self.assertEqual(generated.status_code, 200)
        self.assertTrue(generated_data["success"])
        self.assertTrue(generated_data["validation"]["ok"])
        self.assertEqual(latest.status_code, 200)
        self.assertEqual(latest.get_json()["outbox"]["digest_id"], digest_id)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.get_json()["outbox"]["digest_id"], digest_id)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()["status"], "processing")


class LightweightPollingEndpointTest(unittest.TestCase):
    def test_empty_launch_queue_does_not_write_profile(self):
        profile = {"username": "tester", "launch_queue": [], "system_messages": []}
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run.user_store, "consume_launch_queue", return_value=[]), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("write should not run")):
            response = client.get("/launch-queue")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_system_messages_without_new_messages_does_not_write_profile(self):
        profile = {
            "username": "tester",
            "launch_queue": [],
            "system_messages": [
                {"title": "Old", "text": "Read already", "status": "read"}
            ],
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("write should not run")):
            response = client.get("/system-messages")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), [])

    def test_mail_bootstrap_uses_readonly_profile_without_full_sync(self):
        profile = {
            "username": "tester",
            "nick": "Tester",
            "apps": [],
            "files": {},
            "contacts": [],
            "system_messages": [],
            "storage_capacity": 512,
            "storage_used": 0,
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"

        with patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")), \
                patch.object(run.mail_store, "ensure_seeded", return_value=None), \
                patch.object(run.mail_store, "remove_contacts_without_users", return_value=None), \
                patch.object(run.mail_store, "touch_presence", return_value=None), \
                patch.object(run.mail_store, "list_contacts", return_value=[]), \
                patch.object(run.mail_store, "list_accepted_contacts", return_value=[]), \
                patch.object(run.mail_store, "list_pending_threads", return_value=[]), \
                patch.object(run.mail_store, "list_messages", return_value=[]), \
                patch.object(run.mail_store, "group_active_count", return_value=0), \
                patch.object(run.mail_store, "unread_counts", return_value={}):
            response = client.get("/api/mail/bootstrap")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["username"], "tester")
        self.assertIn("channels", data)
        self.assertEqual(data["contacts"], [])


class MissingProfileAndSessionSafetyTest(unittest.TestCase):
    def setUp(self):
        self.runtime_tmp = tempfile.TemporaryDirectory()
        runtime_db = os.path.join(self.runtime_tmp.name, "target-runtime.sqlite3")
        self.runtime_patches = [
            patch.object(run, "player_target_runtime_store", PlayerTargetRuntimeStore(db_path=runtime_db)),
            patch.object(run, "player_operation_store", PlayerOperationStore(db_path=runtime_db)),
        ]
        for runtime_patch in self.runtime_patches:
            runtime_patch.start()

    def tearDown(self):
        for runtime_patch in reversed(self.runtime_patches):
            runtime_patch.stop()
        self.runtime_tmp.cleanup()

    def test_map_without_profile_redirects_to_login_instead_of_500(self):
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "ghost"

        with patch.object(run, "sync_session_profile", return_value=None):
            response = client.get("/map")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/"))

        follow = client.get("/")
        self.assertEqual(follow.status_code, 200)
        self.assertIn("Brak danych profilu".encode("utf-8"), follow.data)

    def test_root_username_profile_loads_even_when_nick_is_rut(self):
        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [],
            "files": {},
            "own_places": None,
            "captured_targets": None,
            "territory": None,
            "areas": None,
        }

        with patch.object(run.user_store, "get_profile", return_value=profile):
            loaded = run.load_profile_readonly("root", normalize_apps=False, normalize_files=False)

        self.assertEqual(loaded["username"], "root")
        self.assertEqual(loaded["nick"], "Rut")
        self.assertEqual(loaded["own_places"], [])
        self.assertEqual(loaded["captured_targets"], [])
        self.assertEqual(loaded["territory"], [])
        self.assertEqual(loaded["areas"], [])

    def test_map_profile_payload_uses_template_shape(self):
        profile = {
            "username": "tester",
            "nick": "O'Reilly \"Mapa\" Łódź",
            "password": "secret",
            "salt": "salt",
            "apps": [],
            "files": {},
            "targets": [],
            "hacked": [],
            "own_places": None,
            "captured_targets": None,
            "territory": [{"broken": object()}],
            "areas": [{"vertices": "broken"}],
            "system_messages": [
                {"title": "Cytat", "text": "Pole 'A' mówi \"hej\" — Łódź"}
            ],
            "curently_possition": {"lat": 52.2297, "lng": 21.0122},
            "aimed_target": {},
            "field_from_database_bypass": "'}; window.pwned = true; //",
        }

        payload = profile_template_payload(profile)

        self.assertEqual(payload["username"], "tester")
        self.assertEqual(payload["nick"], "O'Reilly \"Mapa\" Łódź")
        self.assertNotIn("password", payload)
        self.assertNotIn("salt", payload)
        self.assertNotIn("field_from_database_bypass", payload)
        self.assertNotIn("territory", payload)
        self.assertNotIn("areas", payload)

    def test_map_embeds_profile_as_json_literal(self):
        profile = {
            "username": "tester",
            "nick": "O'Reilly \"Mapa\" Łódź",
            "apps": [],
            "files": {},
            "targets": [],
            "hacked": [],
            "own_places": None,
            "captured_targets": None,
            "territory": [{"broken": object()}],
            "areas": [{"vertices": "broken"}],
            "system_messages": [
                {"title": "Cytat", "text": "Pole 'A' mówi \"hej\" — Łódź"}
            ],
            "curently_possition": {"lat": 52.2297, "lng": 21.0122},
            "aimed_target": {},
            "field_from_database_bypass": "'}; window.pwned = true; //",
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"

        with patch.object(run, "sync_session_profile", return_value=profile):
            response = client.get("/map")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn("JSON.parse('{{ profile", html)
        self.assertNotIn("field_from_database_bypass", html)
        self.assertNotIn("window.pwned", html)
        match = re.search(
            r'<script id="profile-data" type="application/json">\s*(.*?)\s*</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(match)
        embedded_profile = json.loads(match.group(1))
        self.assertEqual(embedded_profile["nick"], "O'Reilly \"Mapa\" Łódź")
        self.assertNotIn("territory", embedded_profile)
        self.assertNotIn("areas", embedded_profile)

    def test_map_does_not_embed_large_background_profile_collections(self):
        profile = {
            "username": "tester",
            "nick": "Duży payload 'quoted' Łódź",
            "apps": [],
            "files": {},
            "targets": [],
            "hacked": [],
            "system_messages": [
                {
                    "title": f"Alert {index}",
                    "text": "POLE ZOSTAŁO OTOCZONE 'quoted' \"double\" Łódź " + ("x" * 1200),
                }
                for index in range(55)
            ],
            "curently_possition": {"lat": 52.2297, "lng": 21.0122},
            "aimed_target": {},
            "field_from_database_bypass": "'}; window.pwned = true; //",
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"

        with patch.object(run, "sync_session_profile", return_value=profile):
            response = client.get("/map")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertNotIn("JSON.parse('{{ profile", html)
        match = re.search(
            r'<script id="profile-data" type="application/json">\s*(.*?)\s*</script>',
            html,
            re.S,
        )
        self.assertIsNotNone(match)
        self.assertLess(len(match.group(1)), 5000)
        embedded_profile = json.loads(match.group(1))
        self.assertNotIn("system_messages", embedded_profile)
        self.assertEqual(embedded_profile["targets"], [])
        self.assertEqual(embedded_profile["hacked"], [])
        self.assertNotIn("field_from_database_bypass", embedded_profile)

    def test_territory_hack_does_not_replace_session_user_with_owner(self):
        class FakeProfileManager:
            created_for = []

            def __init__(self, username):
                self.username = username
                self.__class__.created_for.append(username)

            def update_profile(self, updates):
                self.updates = updates

        critical_security = {
            key: True
            for key in [
                "stealth_mode", "scan_detection", "exploit_protection", "vpn_enabled",
                "browser_protection", "os_hardening", "log_guardian", "process_monitor",
                "firewall", "log_integrity", "network_anomaly_detection", "spoofing_protection",
                "activity_monitor", "player_tracking", "system_visibility", "firewall_core",
                "kernel_guard", "system_integrity_check", "heap_protection", "memory_lock",
                "background_injection", "memory_guard", "vpn_blocker",
            ]
        }
        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [{
                "id": "noop_tool",
                "name": "Noop Tool",
                "requires_off": [],
                "interferes_with": [],
                "levels": [{"options": []}],
            }],
            "aimed_target": {
                "target_mode": "territory_contest",
                "contest_owner_username": "owner_a",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Foreign pillar",
                "security": critical_security,
                "actions_allowed": {"scan_ports": True},
            },
            "system_messages": [],
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "find_captured_target_for_owner", return_value=None), \
                patch.object(run, "UserProfileManager", FakeProfileManager):
            response = client.post("/gonna-win", json={
                "app_id": "noop_tool",
                "choice_id": "run_generated",
            })

        self.assertEqual(response.status_code, 200)
        with client.session_transaction() as sess:
            self.assertEqual(sess["user"], "root")
        self.assertNotIn("root", FakeProfileManager.created_for)
        self.assertNotIn("owner_a", FakeProfileManager.created_for)

    def test_gonna_win_reports_created_map_operation_as_success(self):
        profile = {
            "username": "root",
            "apps": [{
                "id": "window_map_tool",
                "name": "Window Map Tool",
                "interface": "window",
                "map_actions": ["scan_ports"],
                "operation_types": ["wifi_scanner"],
                "requires_off": ["firewall"],
                "interferes_with": [],
                "levels": [{"buttons": [{"label": "Run", "action": "run_generated"}]}],
            }],
            "aimed_target": {
                "target_id": "map:test-window-runtime",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Runtime target",
                "security": {"firewall": True},
                "actions_allowed": {},
            },
            "operations": [],
            "system_messages": [],
        }
        created = [{"operation_id": "op-window-runtime"}]
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "apply_app_map_actions_to_aimed_target", return_value=(True, ["scan_ports"])), \
                patch.object(run, "create_missing_operations_for_app_target", return_value=created), \
                patch.object(run, "merge_latest_aimed_target_runtime_state"), \
                patch.object(run.player_target_runtime_store, "upsert_aimed", return_value={"status": "in_progress"}), \
                patch.object(run, "UserProfileManager"):
            response = client.post("/gonna-win", json={
                "app_id": "window_map_tool",
                "choice_id": "run_generated",
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["map_runtime_started"])
        self.assertEqual(payload["created_operations"], created)

    def test_gonna_win_treats_late_choice_for_already_captured_target_as_success(self):
        expected_target = {
            "target_id": "map:52.1:21.2:Target",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Target",
        }
        captured_target = {
            **expected_target,
            "owner_username": "root",
            "captured": True,
        }
        profile = {
            "username": "root",
            "apps": [{
                "id": "gps_tool",
                "name": "GPS Tool",
                "map_actions": ["trace_gps"],
                "levels": [{"options": []}],
            }],
            "aimed_target": {},
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(
                    run,
                    "find_owned_captured_target_for_runtime_target",
                    return_value=captured_target,
                ), \
                patch.object(run, "apply_app_map_actions_to_aimed_target") as apply_actions:
            response = client.post("/gonna-win", json={
                "app_id": "gps_tool",
                "choice_id": "late-choice",
                "expected_target": expected_target,
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["superseded_by_capture"])
        self.assertTrue(payload["duplicate"])
        self.assertEqual(payload["captured_target"], captured_target)
        self.assertEqual(payload["created_operations"], [])
        apply_actions.assert_not_called()

    def test_gonna_win_keeps_invalid_target_conflict_without_matching_capture(self):
        expected_target = {"lat": 52.1, "lng": 21.2, "label": "Target"}
        profile = {
            "username": "root",
            "apps": [{
                "id": "gps_tool",
                "name": "GPS Tool",
                "map_actions": ["trace_gps"],
                "levels": [{"options": []}],
            }],
            "aimed_target": {},
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "find_owned_captured_target_for_runtime_target", return_value=None):
            response = client.post("/gonna-win", json={
                "app_id": "gps_tool",
                "expected_target": expected_target,
            })

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()["reason"], "invalid_target")

    def test_gonna_win_rejects_late_window_bound_to_previous_target(self):
        previous_target = {
            "target_id": "map:52.1:21.2:Previous",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Previous",
            "target_mode": "standard",
        }
        current_target = {
            "target_id": "map:52.2:21.3:Current",
            "lat": 52.2,
            "lng": 21.3,
            "label": "Current",
            "target_mode": "standard",
            "actions_allowed": {
                "scan_ports": False, "exploit": False, "sniff": False, "trace": False,
            },
            "security": {"firewall": True},
        }
        profile = {
            "username": "root",
            "apps": [{
                "id": "gps_tool",
                "name": "GPS Tool",
                "map_actions": ["trace_gps"],
                "levels": [{"options": []}],
            }],
            "aimed_target": current_target,
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "apply_app_map_actions_to_aimed_target") as apply_actions:
            response = client.post("/gonna-win", json={
                "app_id": "gps_tool",
                "operation_only": True,
                "expected_target": previous_target,
            })

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertEqual(payload["reason"], "target_selection_changed")
        self.assertEqual(payload["target"]["target_id"], current_target["target_id"])
        apply_actions.assert_not_called()

    def test_gonna_win_rejects_same_launch_receipt_across_targets(self):
        previous_target = {
            "target_id": "map:52.1:21.2:Previous",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Previous",
            "target_mode": "standard",
        }
        current_target = {
            "target_id": "map:52.2:21.3:Current",
            "lat": 52.2,
            "lng": 21.3,
            "label": "Current",
            "target_mode": "standard",
            "security": {"firewall": True},
            "actions_allowed": {
                "scan_ports": False, "exploit": False, "sniff": False, "trace": False,
            },
        }
        profile = {
            "username": "root",
            "apps": [{
                "id": "gps_tool",
                "name": "GPS Tool",
                "map_actions": ["trace_gps"],
                "levels": [{"options": []}],
            }],
            "aimed_target": current_target,
            "operations": [],
        }

        class FakeProfileManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, updates):
                return None

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with tempfile.TemporaryDirectory() as tmpdir:
            receipt_store = AppActionReceiptStore(os.path.join(tmpdir, "receipts.sqlite3"))
            common_payload = {
                "app_id": "gps_tool",
                "operation_only": True,
                "launch_receipt": "same-window-receipt",
            }
            with patch.object(run, "app_action_receipt_store", receipt_store), \
                    patch.object(run, "sync_session_profile", return_value=profile), \
                    patch.object(run, "UserProfileManager", FakeProfileManager), \
                    patch.object(run, "apply_app_map_actions_to_aimed_target", return_value=(False, [])), \
                    patch.object(run, "merge_latest_aimed_target_runtime_state"), \
                    patch.object(run, "create_missing_operations_for_app_target", return_value=[]):
                stale = client.post("/gonna-win", json={
                    **common_payload,
                    "expected_target": previous_target,
                })
                current = client.post("/gonna-win", json={
                    **common_payload,
                    "expected_target": current_target,
                })

        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.get_json()["reason"], "target_selection_changed")
        self.assertEqual(current.status_code, 409)
        self.assertEqual(current.get_json()["reason"], "receipt_target_mismatch")
        self.assertFalse(current.get_json().get("idempotent_replay", False))

    def test_gonna_win_treats_late_captured_previous_target_as_success_without_replacing_current(self):
        previous_target = {
            "target_id": "map:52.1:21.2:Previous",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Previous",
        }
        captured_target = {**previous_target, "owner_username": "root", "captured": True}
        current_target = {
            "target_id": "map:52.2:21.3:Current",
            "lat": 52.2,
            "lng": 21.3,
            "label": "Current",
        }
        profile = {
            "username": "root",
            "apps": [{
                "id": "gps_tool",
                "name": "GPS Tool",
                "map_actions": ["trace_gps"],
                "levels": [{"options": []}],
            }],
            "aimed_target": current_target,
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(
                    run,
                    "find_owned_captured_target_for_runtime_target",
                    return_value=captured_target,
                ), \
                patch.object(run, "apply_app_map_actions_to_aimed_target") as apply_actions:
            response = client.post("/gonna-win", json={
                "app_id": "gps_tool",
                "expected_target": previous_target,
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["superseded_by_capture"])
        self.assertEqual(payload["captured_target"], captured_target)
        self.assertEqual(payload["target"], current_target)
        apply_actions.assert_not_called()

    def test_gonna_win_marks_app_map_actions_on_aimed_target(self):
        class FakeProfileManager:
            updates = []

            def __init__(self, username):
                self.username = username

            def update_profile(self, updates):
                self.__class__.updates.append((self.username, updates))

        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [{
                "id": "gps_tool",
                "name": "GPS Tool",
                "requires_off": ["audio_guardian"],
                "interferes_with": [],
                "map_actions": ["trace_gps", "scan_ports"],
                "map_actions_source": "manual",
                "levels": [{"options": []}],
            }],
            "aimed_target": {
                "target_mode": "standard",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Target",
                "security": {"firewall": True},
                "actions_allowed": {
                    "scan_ports": False,
                    "exploit": False,
                    "sniff": False,
                    "trace": False,
                },
            },
            "system_messages": [],
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeProfileManager):
            response = client.post("/gonna-win", json={"app_id": "gps_tool"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        actions = payload["target"]["actions_allowed"]
        self.assertTrue(actions["scan_ports"])
        self.assertTrue(actions["trace_gps"])
        self.assertTrue(actions["trace"])
        self.assertFalse(actions["exploit"])
        self.assertFalse(actions["sniff"])
        self.assertEqual(payload["actions_allowed_marked"], ["trace_gps", "trace", "scan_ports"])

    def test_gonna_win_preserves_newer_target_action_flags(self):
        class FakeProfileManager:
            updates = []

            def __init__(self, username):
                self.username = username

            def update_profile(self, updates):
                self.__class__.updates.append((self.username, updates))

        stale_target = {
            "target_mode": "standard",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Target",
            "security": {"firewall": True, "vpn": True},
            "actions_allowed": {
                "scan_ports": False,
                "exploit": False,
                "sniff": False,
                "trace": False,
            },
        }
        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [{
                "id": "exploit_tool",
                "name": "Exploit Tool",
                "requires_off": [],
                "interferes_with": ["firewall"],
                "map_actions": ["exploit"],
                "map_actions_source": "manual",
                "levels": [{"options": []}],
            }],
            "aimed_target": dict(stale_target),
            "system_messages": [],
        }
        profile["aimed_target"]["actions_allowed"] = dict(stale_target["actions_allowed"])
        latest_profile = {
            "username": "root",
            "aimed_target": {
                **stale_target,
                "security": {"firewall": True, "vpn": False},
                "actions_allowed": {
                    "scan_ports": True,
                    "exploit": False,
                    "sniff": False,
                    "trace": False,
                },
            },
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.player_target_runtime_store, "get_active_target", return_value=latest_profile["aimed_target"]), \
                patch.object(run.player_target_runtime_store, "get", return_value={"status": "in_progress", "target": latest_profile["aimed_target"]}), \
                patch.object(run, "UserProfileManager", FakeProfileManager):
            response = client.post("/gonna-win", json={"app_id": "exploit_tool"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        actions = payload["target"]["actions_allowed"]
        security = payload["target"]["security"]
        self.assertTrue(actions["scan_ports"])
        self.assertTrue(actions["exploit"])
        self.assertFalse(actions["sniff"])
        self.assertFalse(actions["trace"])
        self.assertFalse(security["vpn"])
        self.assertFalse(security["firewall"])

    def test_gonna_win_preserves_newer_target_flags_when_map_label_differs(self):
        class FakeProfileManager:
            updates = []

            def __init__(self, username):
                self.username = username

            def update_profile(self, updates):
                self.__class__.updates.append((self.username, updates))

        stale_target = {
            "target_mode": "standard",
            "lat": 52.1000003,
            "lng": 21.2000003,
            "label": "Map display label",
            "security": {"firewall": True, "vpn": True},
            "actions_allowed": {
                "scan_ports": False,
                "exploit": False,
                "sniff": False,
                "trace": False,
            },
        }
        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [{
                "id": "exploit_tool",
                "name": "Exploit Tool",
                "requires_off": [],
                "interferes_with": ["firewall"],
                "map_actions": ["exploit"],
                "map_actions_source": "manual",
                "levels": [{"options": []}],
            }],
            "aimed_target": dict(stale_target),
            "system_messages": [],
        }
        profile["aimed_target"]["actions_allowed"] = dict(stale_target["actions_allowed"])
        latest_profile = {
            "username": "root",
            "aimed_target": {
                "target_mode": "standard",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Canonical target label",
                "security": {"firewall": True, "vpn": False},
                "actions_allowed": {
                    "scan_ports": True,
                    "exploit": False,
                    "sniff": True,
                    "trace": False,
                },
            },
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.player_target_runtime_store, "get_active_target", return_value=latest_profile["aimed_target"]), \
                patch.object(run.player_target_runtime_store, "get", return_value={"status": "in_progress", "target": latest_profile["aimed_target"]}), \
                patch.object(run, "UserProfileManager", FakeProfileManager):
            response = client.post("/gonna-win", json={"app_id": "exploit_tool"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        actions = payload["target"]["actions_allowed"]
        security = payload["target"]["security"]
        self.assertTrue(actions["scan_ports"])
        self.assertTrue(actions["sniff"])
        self.assertTrue(actions["exploit"])
        self.assertFalse(actions["trace"])
        self.assertFalse(security["vpn"])
        self.assertFalse(security["firewall"])

    def test_gonna_win_operation_only_starts_map_operation_without_security_effect(self):
        class FakeProfileManager:
            updates = []

            def __init__(self, username):
                self.username = username

            def update_profile(self, updates):
                self.__class__.updates.append((self.username, updates))

        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [{
                "id": "sniff_tool",
                "name": "Sniff Tool",
                "requires_off": [],
                "interferes_with": ["firewall"],
                "map_actions": ["sniff"],
                "map_actions_source": "manual",
                "operation_types": ["persistent_sniffer"],
                "levels": [{"options": []}],
            }],
            "aimed_target": {
                "target_mode": "standard",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Target",
                "security": {"firewall": True},
                "actions_allowed": {
                    "scan_ports": False,
                    "exploit": False,
                    "sniff": False,
                    "trace": False,
                },
            },
            "operations": [],
            "system_messages": [],
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.user_store, "get_profile", return_value=None), \
                patch.object(run, "UserProfileManager", FakeProfileManager):
            response = client.post("/gonna-win", json={"app_id": "sniff_tool", "operation_only": True})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertTrue(payload["operation_only"])
        self.assertEqual(payload["actions_allowed_marked"], ["sniff"])
        self.assertTrue(payload["target"]["actions_allowed"]["sniff"])
        self.assertTrue(payload["target"]["security"]["firewall"])
        self.assertEqual(len(payload["created_operations"]), 1)
        created = payload["created_operations"][0]
        self.assertEqual(created["source_app_id"], "sniff_tool")
        self.assertEqual(created["map_action_id"], "sniff")
        self.assertEqual(created["operation_type"], "persistent_sniffer")
        self.assertEqual(created["status"], "running")
        self.assertEqual(len(profile["operations"]), 1)
        self.assertEqual(FakeProfileManager.updates, [])

    def test_gonna_win_operation_only_deduplicates_running_map_operation(self):
        class FakeProfileManager:
            updates = []

            def __init__(self, username):
                self.username = username

            def update_profile(self, updates):
                self.__class__.updates.append((self.username, updates))

        target = {
            "target_mode": "standard",
            "lat": 52.1,
            "lng": 21.2,
            "label": "Target",
            "security": {"firewall": True},
            "actions_allowed": {
                "scan_ports": False,
                "exploit": False,
                "sniff": False,
                "trace": False,
            },
        }
        profile = {
            "username": "root",
            "nick": "Rut",
            "apps": [{
                "id": "sniff_tool",
                "name": "Sniff Tool",
                "requires_off": [],
                "interferes_with": ["firewall"],
                "map_actions": ["sniff"],
                "map_actions_source": "manual",
                "operation_types": ["persistent_sniffer"],
                "levels": [{"options": []}],
            }],
            "aimed_target": dict(target),
            "operations": [{
                "operation_id": "op_existing",
                "operation_type": "persistent_sniffer",
                "source_app_id": "sniff_tool",
                "source_app_name": "Sniff Tool",
                "map_action_id": "sniff",
                "target_id": run.build_operation_target_id(target),
                "status": "running",
            }],
            "system_messages": [],
        }

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "root"

        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.user_store, "get_profile", return_value=None), \
                patch.object(run, "UserProfileManager", FakeProfileManager):
            response = client.post("/gonna-win", json={"app_id": "sniff_tool", "operation_only": True})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["created_operations"], [])
        self.assertEqual(len(profile["operations"]), 1)

    def test_map_player_areas_skips_invalid_area_and_keeps_owner_encircled_area(self):
        profile = {
            "username": "main",
            "nick": "Main()",
            "level": 4,
            "apps": [],
            "files": {},
        }
        areas = [
            {"id": 1, "owner_username": "main", "status": "active", "vertices": []},
            {
                "id": 2,
                "owner_username": "main",
                "status": "encircled",
                "vertices": [
                    {"lat": 52.0, "lng": 21.0},
                    {"lat": 52.0, "lng": 21.01},
                    {"lat": 52.01, "lng": 21.0},
                ],
                "area_size": 1000,
            },
            {
                "id": 3,
                "owner_username": "other",
                "status": "active",
                "vertices": [
                    {"lat": 53.0, "lng": 22.0},
                    {"lat": 53.0, "lng": 22.01},
                    {"lat": 53.01, "lng": 22.0},
                ],
                "area_size": 2000,
            },
        ]

        class FakeTerritoryStoreForMap:
            def list_player_areas(self):
                return list(areas)

            def list_recent_area_intruders(self, username):
                return []

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "main"

        def fake_profile(username):
            if username == "main":
                return profile
            if username == "other":
                return {"username": "other", "nick": "Other", "level": 3}
            return None

        with patch.object(run, "territory_store", FakeTerritoryStoreForMap()), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run.user_store, "list_profiles", return_value=[]), \
                patch.object(run.user_store, "get_profile", side_effect=fake_profile), \
                patch.object(run.user_store, "get_profile_identity", side_effect=fake_profile), \
                patch.object(run, "refresh_stale_territory_polygons", return_value=False), \
                patch.object(run, "is_territory_conflict_snapshot_read_enabled", return_value=False), \
                patch.object(run, "detect_territory_conflicts", return_value=[]) as detect_mock, \
                patch.object(run, "get_active_conflicts_for_player", return_value=[]), \
                patch.object(run, "contested_targets_from_active_conflicts", return_value=[]) as contested_mock:
            response = client.get("/api/map/player-areas")

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        detect_mock.assert_not_called()
        contested_mock.assert_called_once()
        self.assertEqual(contested_mock.call_args.args[0], "main")
        self.assertEqual(contested_mock.call_args.args[1], [])
        passed_areas = contested_mock.call_args.args[2]
        self.assertEqual([area["id"] for area in passed_areas], [2, 3])
        self.assertEqual(len(data["areas"]), 2)
        own_area = next(item for item in data["areas"] if item["owner_username"] == "main")
        self.assertTrue(own_area["is_mine"])
        self.assertEqual(own_area["status"], "encircled")
        self.assertTrue(own_area["exposed"])

    def test_contested_targets_from_active_conflicts_uses_stored_targets(self):
        conflict = {
            "id": 42,
            "participants": ["main", "other"],
            "targets": [
                {
                    "owner_username": "other",
                    "status": "contested",
                    "target": {
                        "lat": 52.1,
                        "lng": 21.2,
                        "label": "Conflict Pillar",
                        "source_type": "parcel_locker",
                        "security": {"scan_ports": True},
                    },
                },
                {
                    "owner_username": "main",
                    "status": "contested",
                    "target": {"lat": 52.2, "lng": 21.3, "label": "Own Pillar"},
                },
                {
                    "owner_username": "other",
                    "status": "captured",
                    "captured": True,
                    "target": {"lat": 52.3, "lng": 21.4, "label": "Captured Pillar"},
                },
            ],
        }

        with patch.object(run.user_store, "get_profile", return_value={"username": "other", "nick": "Other"}):
            targets = run.contested_targets_from_active_conflicts("main", [conflict])

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["label"], "Conflict Pillar")
        self.assertEqual(targets[0]["target_mode"], "territory_contest")
        self.assertEqual(targets[0]["contest_owner_username"], "other")
        self.assertEqual(targets[0]["conflict_id"], 42)

    def test_contested_target_prefers_stable_conflict_id(self):
        conflict = {
            "id": 42,
            "conflict_id": "conflict-stable-42",
            "participants": ["main", "other"],
            "targets": [{
                "owner_username": "other",
                "status": "contested",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Stable Pillar"},
            }],
        }

        with patch.object(run.user_store, "get_profile", return_value={}):
            targets = run.contested_targets_from_active_conflicts("main", [conflict], areas=[])

        self.assertEqual(targets[0]["conflict_id"], "conflict-stable-42")
        self.assertEqual(targets[0]["legacy_conflict_id"], 42)

    def test_contested_targets_from_active_conflicts_derives_missing_inner_from_area_ids(self):
        conflict = {
            "id": 77,
            "participants": ["main", "other"],
            "area_ids": [1, 2],
            "targets": [],
            "intersections": [[
                [52.01, 21.01], [52.01, 21.02], [52.02, 21.02], [52.02, 21.01],
            ]],
        }
        areas = [
            {
                "id": 1,
                "owner_username": "main",
                "status": "active",
                "vertices": [
                    {"lat": 52.0, "lng": 21.0},
                    {"lat": 52.0, "lng": 21.02},
                    {"lat": 52.02, "lng": 21.02},
                    {"lat": 52.02, "lng": 21.0},
                ],
            },
            {
                "id": 2,
                "owner_username": "other",
                "status": "active",
                "vertices": [
                    {"lat": 52.01, "lng": 21.01},
                    {"lat": 52.01, "lng": 21.03},
                    {"lat": 52.03, "lng": 21.03},
                    {"lat": 52.03, "lng": 21.01},
                ],
            },
        ]

        class FakeTerritoryStore:
            def list_captured_targets(self, owner, stationary=True):
                if owner == "other":
                    return [
                        {
                            "lat": 52.015,
                            "lng": 21.015,
                            "label": "Enemy Inner",
                            "source_type": "inner",
                        }
                    ]
                return []

        with patch.object(run, "territory_store", FakeTerritoryStore()), \
                patch.object(run.user_store, "get_profile", return_value={"username": "other", "nick": "Other"}):
            targets = run.contested_targets_from_active_conflicts("main", [conflict], areas)

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["label"], "Enemy Inner")
        self.assertEqual(targets[0]["target_mode"], "territory_contest")
        self.assertEqual(targets[0]["contest_owner_username"], "other")
        self.assertEqual(targets[0]["foreign_area_id"], 2)
        self.assertEqual(targets[0]["my_area_id"], 1)

    def test_contested_targets_exclude_foreign_cluster_pillar_outside_overlap(self):
        conflict = {
            "id": 78,
            "participants": ["main", "other"],
            "area_ids": [1, 2],
            "targets": [],
            "intersections": [[
                [52.01, 21.01], [52.01, 21.02], [52.02, 21.02], [52.02, 21.01],
            ]],
        }
        areas = [
            {
                "id": 1,
                "owner_username": "main",
                "status": "active",
                "vertices": [
                    {"lat": 52.0, "lng": 21.0},
                    {"lat": 52.0, "lng": 21.02},
                    {"lat": 52.02, "lng": 21.02},
                    {"lat": 52.02, "lng": 21.0},
                ],
            },
            {
                "id": 2,
                "owner_username": "other",
                "status": "active",
                "vertices": [
                    {"lat": 52.01, "lng": 21.01},
                    {"lat": 52.01, "lng": 21.04},
                    {"lat": 52.04, "lng": 21.04},
                    {"lat": 52.04, "lng": 21.01},
                ],
            },
        ]

        class FakeTerritoryStore:
            def list_captured_targets(self, owner, stationary=None):
                if owner == "other":
                    return [
                        {
                            "lat": 52.04,
                            "lng": 21.04,
                            "label": "Enemy Pillar Outside Overlap",
                            "source_type": "parcel_locker",
                        }
                    ]
                return []

        with patch.object(run, "territory_store", FakeTerritoryStore()), \
                patch.object(run.user_store, "get_profile", return_value={"username": "other", "nick": "Other"}):
            targets = run.contested_targets_from_active_conflicts("main", [conflict], areas)

        self.assertEqual(targets, [])

    def test_contested_targets_recover_from_stale_legacy_area_ids(self):
        conflict = {
            "id": 79,
            "participants": ["main", "other"],
            "area_ids": [101, 102],
            "targets": [],
            "intersections": [[
                [52.01, 21.01], [52.01, 21.025], [52.025, 21.025], [52.025, 21.01],
            ]],
        }
        areas = [
            {
                "id": 1, "owner_username": "main", "status": "active",
                "vertices": [
                    {"lat": 52.0, "lng": 21.0}, {"lat": 52.0, "lng": 21.02},
                    {"lat": 52.02, "lng": 21.02}, {"lat": 52.02, "lng": 21.0},
                ],
            },
            {
                "id": 2, "owner_username": "other", "status": "active",
                "vertices": [
                    {"lat": 52.01, "lng": 21.01}, {"lat": 52.01, "lng": 21.03},
                    {"lat": 52.03, "lng": 21.03}, {"lat": 52.03, "lng": 21.01},
                ],
            },
        ]

        class FakeTerritoryStore:
            def list_captured_targets(self, owner, stationary=None):
                return [{"lat": 52.02, "lng": 21.02, "label": "Recovered Inner"}] if owner == "other" else []

        with patch.object(run, "territory_store", FakeTerritoryStore()), \
                patch.object(run.user_store, "get_profile", return_value={}):
            targets = run.contested_targets_from_active_conflicts("main", [conflict], areas)

        self.assertEqual([target["label"] for target in targets], ["Recovered Inner"])

    def test_capture_conflict_pillar_registers_initial_target_missing_from_snapshot(self):
        conflict = {
            "id": 79,
            "participants": ["main", "other"],
            "targets": [],
            "status": "active",
        }

        class FakeConflictStore:
            def __init__(self):
                self.saved = None

            def list_active(self):
                return [conflict]

            def upsert_conflict(self, payload):
                self.saved = payload
                return payload

        conflict_store = FakeConflictStore()
        captured_target = {
            "target_id": "pillar-initial",
            "conflict_id": 79,
            "lat": 52.03,
            "lng": 21.03,
            "label": "Initial Conflict Pillar",
            "source_type": "parcel_locker",
        }

        with patch.object(run, "territory_conflict_store", conflict_store), \
                patch.object(run, "record_territory_conflict_delta") as delta_mock, \
                patch.object(run, "rebuild_conflict_polygons") as rebuild_mock:
            affected = run.capture_conflict_pillar(
                captured_target,
                captured_by_username="main",
                previous_owner_username="other",
            )

        self.assertEqual(len(affected), 1)
        self.assertIsNotNone(conflict_store.saved)
        self.assertEqual(len(conflict_store.saved["targets"]), 1)
        saved = conflict_store.saved["targets"][0]
        self.assertTrue(saved["captured"])
        self.assertEqual(saved["status"], "captured")
        self.assertEqual(saved["captured_by"], "main")
        self.assertEqual(saved["previous_owner"], "other")
        self.assertEqual(saved["target"]["target_id"], "pillar-initial")
        delta_mock.assert_called_once()
        rebuild_mock.assert_called_once()

    def test_encircled_area_notification_uses_stable_area_key(self):
        area_first = {
            "id": 10,
            "owner_username": "main",
            "status": "encircled",
            "centroid_lat": 52.0,
            "centroid_lng": 21.0,
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ],
        }
        area_second = dict(area_first, id=99)

        class FakeTerritoryStoreForEncircled:
            def __init__(self):
                self.calls = 0
                self.events = []

            def list_player_areas(self):
                self.calls += 1
                return [area_first if self.calls == 1 else area_second]

            def area_event_exists_with_payload_key(self, owner_username, actor_username, event_type, payload_key, payload_value):
                return any(
                    event["owner_username"] == owner_username
                    and event["actor_username"] == actor_username
                    and event["event_type"] == event_type
                    and event["payload"].get(payload_key) == payload_value
                    for event in self.events
                )

            def recent_area_event_exists(self, owner_username, actor_username, event_type, area_id=None, seconds=60):
                return False

            def add_area_event(self, **event):
                self.events.append(event)

        fake_store = FakeTerritoryStoreForEncircled()
        messages = []
        with patch.object(run, "territory_store", fake_store), \
                patch.object(run, "add_system_message_to_user", side_effect=lambda *args: messages.append(args) or True):
            run.notify_encircled_area_owners()
            run.notify_encircled_area_owners()

        self.assertEqual(len(fake_store.events), 1)
        self.assertEqual(len(messages), 1)
        self.assertEqual(fake_store.events[0]["payload"]["area_status"], "encircled")
        self.assertIn("area_key", fake_store.events[0]["payload"])

    def test_encircled_area_notification_respects_recent_legacy_event(self):
        area = {
            "id": 10,
            "owner_username": "main",
            "status": "encircled",
            "centroid_lat": 52.0,
            "centroid_lng": 21.0,
            "vertices": [
                {"lat": 52.0, "lng": 21.0},
                {"lat": 52.0, "lng": 21.01},
                {"lat": 52.01, "lng": 21.0},
            ],
        }

        class FakeTerritoryStoreWithLegacyEvent:
            def list_player_areas(self):
                return [area]

            def area_event_exists_with_payload_key(self, owner_username, actor_username, event_type, payload_key, payload_value):
                return False

            def recent_area_event_exists(self, owner_username, actor_username, event_type, area_id=None, seconds=60):
                return (
                    owner_username == "main"
                    and actor_username == "main"
                    and event_type == "area_encircled"
                    and area_id == 10
                )

            def add_area_event(self, **event):
                raise AssertionError("recent legacy event should suppress duplicate area_encircled alert")

        messages = []
        with patch.object(run, "territory_store", FakeTerritoryStoreWithLegacyEvent()), \
                patch.object(run, "add_system_message_to_user", side_effect=lambda *args: messages.append(args) or True):
            run.notify_encircled_area_owners()

        self.assertEqual(messages, [])


class FakeTerritoryStore:
    def __init__(self, targets):
        self.targets = targets
        self.synced = False

    def list_captured_targets(self, username, stationary=None):
        return list(self.targets)

    def sync_profile_hacked_targets(self, username, profile):
        self.synced = True
        return []


class TargetPersistenceHelpersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.operation_tmp = tempfile.TemporaryDirectory()
        operation_db = os.path.join(cls.operation_tmp.name, "operations.sqlite3")
        cls.operation_store_patch = patch.object(
            run,
            "player_operation_store",
            PlayerOperationStore(db_path=operation_db),
        )
        cls.operation_store_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls.operation_store_patch.stop()
        cls.operation_tmp.cleanup()

    def test_generated_app_icon_accepts_one_visible_grapheme(self):
        self.assertEqual(validate_generated_app_icon("X"), "X")
        self.assertEqual(validate_generated_app_icon("🛠️"), "🛠️")
        self.assertEqual(validate_generated_app_icon("👩‍💻"), "👩‍💻")
        self.assertEqual(validate_generated_app_icon("🇵🇱"), "🇵🇱")

    def test_generated_app_icon_rejects_empty_text_and_multiple_glyphs(self):
        for icon in ("", "GL", "🛠️⚡", "A\n"):
            with self.subTest(icon=repr(icon)):
                with self.assertRaises(ValueError):
                    validate_generated_app_icon(icon)

    def test_position_key_uses_lng_or_lon(self):
        left = {"lat": 52.1234567, "lng": 21.1234567}
        right = {"lat": 52.12345671, "lon": 21.12345671}

        self.assertEqual(target_position_key(left), target_position_key(right))
        self.assertTrue(targets_share_position(left, right))

    def test_filter_removes_by_position_without_label_match(self):
        captured = {"lat": 52.1, "lng": 21.2, "label": "AE Woman"}
        targets = [
            {"lat": 52.1, "lng": 21.2, "label": "Punkt kolizyjny: AE Woman"},
            {"lat": 52.2, "lng": 21.3, "label": "Other"},
        ]

        filtered, removed = filter_targets_by_position(targets, captured, match_label=False)

        self.assertEqual(removed, 1)
        self.assertEqual(filtered, [{"lat": 52.2, "lng": 21.3, "label": "Other"}])

    def test_filter_can_require_label_when_needed(self):
        captured = {"lat": 52.1, "lng": 21.2, "label": "AE Woman"}
        targets = [{"lat": 52.1, "lng": 21.2, "label": "Other label"}]

        filtered, removed = filter_targets_by_position(targets, captured, match_label=True)

        self.assertEqual(removed, 0)
        self.assertEqual(filtered, targets)

    def test_sqlite_captured_targets_replace_stale_profile_hacked(self):
        profile = {
            "hacked": [{"lat": 52.1, "lng": 21.2, "label": "Lost pillar"}],
            "captured_targets_source": "sqlite",
        }
        fake_store = FakeTerritoryStore([])

        with patch.object(run, "territory_store", fake_store):
            changed = run.merge_captured_targets_into_profile("defender", profile)

        self.assertTrue(changed)
        self.assertEqual(profile["hacked"], [])
        self.assertEqual(profile["captured_targets_source"], "sqlite")
        self.assertFalse(fake_store.synced)

    def test_player_actor_relation_prefers_crew_over_friend_context(self):
        viewer = {"username": "neo", "clan": "VIREX"}
        actor = {"username": "trinity", "clan": "VIREX"}

        relation = resolve_player_actor_relation(viewer, actor, {"is_friend": True})

        self.assertEqual(relation, "same_clan")

    def test_player_actor_actions_disable_friend_targeting(self):
        actor = build_player_actor(
            "neo",
            {"username": "trinity", "nick": "Trinity", "lat": 52.1, "lng": 21.2},
            relation="friend",
            context={"source": "friend", "sources": ["friend"], "is_friend": True},
        )

        self.assertTrue(actor["actions"]["chat"]["enabled"])
        self.assertFalse(actor["actions"]["add_friend"]["enabled"])
        self.assertFalse(actor["actions"]["mark_target"]["enabled"])
        self.assertTrue(actor["actions"]["transfer_hc"]["enabled"])

    def test_map_action_router_prefers_app_map_actions(self):
        apps = [
            {"id": "legacy_scanner", "name": "Legacy", "type": "scanner", "detects": ["open_ports"]},
            {"id": "gps_tracker", "name": "GPS Tracker", "map_actions": ["trace_gps"], "type": "scanner"},
        ]

        matched, source = get_apps_for_map_action(apps, "trace_gps")

        self.assertEqual(source, "map_actions")
        self.assertEqual([app["id"] for app in matched], ["gps_tracker"])

    def test_legacy_app_contract_gets_runtime_map_actions(self):
        app = normalize_app_contract({
            "id": "scan_probe_v1",
            "name": "ScanProbe",
            "type": "scanner",
            "detects": ["open_ports", "user_location"],
        })

        self.assertIn("scan_ports", app["map_actions"])
        self.assertIn("trace", app["map_actions"])
        self.assertEqual(app["map_actions_source"], "legacy_inferred")

    def test_map_action_router_returns_no_match_for_missing_app(self):
        matched, source = get_apps_for_map_action([], "scan_ports")

        self.assertEqual(matched, [])
        self.assertEqual(source, "none")

    def test_hack_action_tool_selection_uses_readonly_preflight(self):
        profile = {
            "username": "tester",
            "nick": "Tester",
            "apps": [
                {
                    "id": "sniff_a",
                    "name": "Sniff A",
                    "type": "sniffer",
                    "map_actions": ["sniff"],
                    "map_actions_source": "manual",
                },
                {
                    "id": "sniff_b",
                    "name": "Sniff B",
                    "type": "sniffer",
                    "map_actions": ["sniff"],
                    "map_actions_source": "manual",
                },
            ],
            "files": {},
            "curently_possition": {"lat": 52.2297, "lng": 21.0122},
            "aimed_target": {},
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"

        with patch.object(run, "load_profile_readonly", return_value=profile) as readonly, \
             patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")), \
             patch.object(run, "find_contested_target", return_value=None), \
             patch.object(run, "find_foreign_area_for_point", return_value=None), \
             patch.object(run, "create_operations_for_app_action", side_effect=AssertionError("operation should not run")):
            response = client.post("/hack-action", json={
                "action": "sniff",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Target",
                "icon": "X",
                "_flow_id": "test-flow",
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["tool_selection_required"])
        self.assertEqual([app["id"] for app in payload["matching_apps"]], ["sniff_a", "sniff_b"])
        self.assertEqual(payload["pending_action"]["_flow_id"], "test-flow")
        readonly.assert_called_once()

    def test_hack_action_single_tool_discovery_is_readonly_when_provisional_enabled(self):
        profile = {
            "username": "tester",
            "nick": "Tester",
            "apps": [
                {
                    "id": "sniff_only",
                    "name": "Sniff Only",
                    "type": "sniffer",
                    "interface": "button_choices",
                    "description": "Quiet network probe",
                    "map_actions": ["sniff"],
                    "map_actions_source": "manual",
                },
            ],
            "files": {},
            "curently_possition": {"lat": 52.2297, "lng": 21.0122},
            "aimed_target": {},
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"

        with patch.object(run, "PROVISIONAL_APP_LAUNCH_ENABLED", True), \
             patch.object(run, "load_profile_readonly", return_value=profile) as readonly, \
             patch.object(run, "sync_session_profile", side_effect=AssertionError("sync should not run")), \
             patch.object(run, "find_contested_target", return_value=None), \
             patch.object(run, "find_foreign_area_for_point", return_value=None), \
             patch.object(run, "create_operations_for_app_action", side_effect=AssertionError("operation should not run")), \
             patch.object(run, "begin_hack_action_idempotency", side_effect=AssertionError("receipt should not start")):
            response = client.post("/hack-action", json={
                "action": "sniff",
                "lat": 52.1,
                "lng": 21.2,
                "label": "Target",
                "icon": "X",
                "_flow_id": "single-flow",
                "_client_action_key": "single-client-key",
            })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["tool_selection_required"])
        self.assertTrue(payload["auto_select"])
        self.assertEqual([app["id"] for app in payload["matching_apps"]], ["sniff_only"])
        self.assertEqual(payload["matching_apps"][0]["description"], "Quiet network probe")
        self.assertEqual(payload["pending_action"]["_flow_id"], "single-flow")
        self.assertEqual(payload["pending_action"]["_client_action_key"], "single-client-key")
        readonly.assert_called_once()

    def test_legacy_trace_gps_app_gets_operation_type(self):
        app = normalize_app_contract({
            "id": "gps_tracker_v1",
            "name": "GPS Tracker",
            "type": "scanner",
            "detects": ["gps_location", "movement_data"],
        })

        self.assertIn("trace_gps", app["map_actions"])
        self.assertIn("vehicle_tracking", app["operation_types"])
        self.assertEqual(app["operation_types_source"], "legacy_inferred")

    def test_exploit_suite_legacy_inference_does_not_add_scan_ports(self):
        app = normalize_app_contract({
            "id": "pencombo_v1",
            "name": "PenCombo",
            "type": "exploit_suite",
            "detects": ["open_ports", "weak_configs", "inject_points"],
        })

        self.assertIn("exploit", app["map_actions"])
        self.assertNotIn("scan_ports", app["map_actions"])
        self.assertEqual(app["map_actions_source"], "legacy_inferred")

    def test_migration_inferred_pencombo_does_not_match_scan_ports(self):
        pencombo = {
            "id": "pencombo_v1",
            "name": "PenCombo",
            "type": "exploit_suite",
            "map_actions": ["exploit", "scan_ports"],
            "map_actions_source": "migration_inferred",
        }
        scanner = {
            "id": "scan_probe_v1",
            "name": "ScanProbe",
            "type": "scanner",
            "map_actions": ["scan_ports"],
            "map_actions_source": "migration_inferred",
        }

        scan_matches, scan_source = get_apps_for_map_action([pencombo, scanner], "scan_ports")
        exploit_matches, exploit_source = get_apps_for_map_action([pencombo, scanner], "exploit")

        scan_ids = [app["id"] for app in scan_matches]
        self.assertEqual(scan_source, "map_actions")
        self.assertEqual(scan_ids, ["scan_probe_v1"])
        self.assertEqual(exploit_source, "map_actions")
        self.assertEqual([app["id"] for app in exploit_matches], ["pencombo_v1"])

    def test_explicit_exploit_suite_map_actions_still_win(self):
        explicit_hybrid = normalize_app_contract({
            "id": "explicit_hybrid",
            "name": "Explicit Hybrid",
            "type": "exploit_suite",
            "map_actions": ["exploit", "scan_ports"],
        })

        self.assertIn("scan_ports", explicit_hybrid["map_actions"])
        self.assertIn("exploit", explicit_hybrid["map_actions"])

    def test_sniff_action_matches_sniffer_not_exploit_suite(self):
        apps = [
            {
                "id": "deep_sniff_r2",
                "name": "DeepSniff",
                "type": "scanner",
                "map_actions": ["sniff"],
                "map_actions_source": "migration_inferred",
            },
            {
                "id": "pencombo_v1",
                "name": "PenCombo",
                "type": "exploit_suite",
                "map_actions": ["exploit"],
                "map_actions_source": "migration_inferred",
            },
        ]

        matched, source = get_apps_for_map_action(apps, "sniff")

        self.assertEqual(source, "map_actions")
        self.assertEqual([app["id"] for app in matched], ["deep_sniff_r2"])

    def test_legacy_fallback_can_be_disabled_for_dev_tests(self):
        apps = [{
            "id": "legacy_scanner",
            "name": "Legacy Scanner",
            "type": "scanner",
            "detects": ["open_ports"],
        }]

        with patch.dict(os.environ, {"CHAOS_LEGACY_MAP_ACTION_FALLBACK": "false"}):
            matched, source = get_apps_for_map_action(apps, "scan_ports", allow_legacy_fallback=True)

        self.assertEqual(matched, [])
        self.assertEqual(source, "none")

    def test_googleplex_catalog_payload_exposes_runtime_contract(self):
        app = normalize_app_contract({
            "id": "gps_tracker_v1",
            "name": "GPS Tracker",
            "price": 50,
            "map_actions": ["trace_gps"],
            "operation_types": ["vehicle_tracking"],
            "resource_types": ["gps_logs", "location_history"],
            "target_types": ["vehicle"],
        })
        profile = {"hackcoins": 120, "apps": []}

        payload = googleplex_catalog_payload(app, profile)

        self.assertFalse(payload["installed"])
        self.assertTrue(payload["can_afford"])
        self.assertEqual(payload["install_blocked_reason"], "")
        self.assertEqual(payload["map_actions"], ["trace_gps"])
        self.assertEqual(payload["operation_types"], ["vehicle_tracking"])
        self.assertEqual(payload["resource_types"], ["gps_logs", "location_history"])
        self.assertEqual(payload["app_level"], "Advanced")
        self.assertGreater(payload["file_size"], 0)
        self.assertGreater(payload["disk_usage"], 0)
        self.assertEqual(payload["install_size"], payload["disk_usage"])
        self.assertGreater(payload["power_score"], 0)
        self.assertGreater(payload["price_hint"], 0)
        self.assertIn(payload["balance_tier"], {"Basic", "Advanced", "Pro"})

    def test_app_contract_adds_default_storage_fields(self):
        app = normalize_app_contract({
            "id": "camera_tool_v1",
            "name": "Camera Tool",
            "interface": "window",
            "type": "camera_tool",
            "map_actions": ["camera_stream"],
            "operation_types": ["camera_stream"],
            "resource_types": ["camera_dump", "video_material"],
        })

        self.assertGreaterEqual(app["file_size"], 1)
        self.assertGreaterEqual(app["disk_usage"], app["file_size"])
        self.assertEqual(app["install_size"], app["disk_usage"])
        self.assertGreaterEqual(app["quality_score"], 0)
        self.assertGreaterEqual(app["reliability"], 0)
        self.assertGreaterEqual(app["creator_power"], 0)
        self.assertGreater(app["power_score"], 0)
        self.assertGreater(app["price_hint"], 0)
        self.assertIn(app["balance_tier"], {"Basic", "Advanced", "Pro"})

    def test_legacy_app_keeps_explicit_price_but_gets_balance_hint(self):
        app = normalize_app_contract({
            "id": "admin_test_scan_ports_1",
            "name": "Admin Test Scanner",
            "type": "scanner",
            "price": 10,
            "map_actions": ["scan_ports"],
            "map_actions_source": "admin_test_seed",
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
        })

        self.assertEqual(app["price"], 10)
        self.assertGreater(app["price_hint"], app["price"])
        self.assertGreater(app["power_score"], 0)

    def assert_generated_app_install_and_command_preserve_levels(self, payload, assert_levels):
        with patch.object(run.user_store, "get_profile", return_value={"level": 18, "respect": 180, "hackcoins": 5000}):
            app = build_generated_app(payload, "creator", "Creator")

        assert_levels(app["levels"])

        profile = {
            "username": "creator",
            "nick": "Creator",
            "hackcoins": 10000,
            "apps": [],
            "files": {"tools": [], "projects": []},
            "storage_capacity": 512,
            "system_messages": [],
        }
        store = [dict(app)]

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "creator"

        with canonical_wallet_test_runtime({"creator": 10000}), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run.resources_store, "get", return_value=store), \
                patch.object(run.resources_store, "set", return_value=None), \
                patch.object(run, "get_app_catalog", return_value=store):
            install_response = client.post("/install-app", json={"app_id": app["id"]})
            self.assertEqual(install_response.status_code, 200)
            self.assertEqual(install_response.get_json()["status"], "success")

            installed = next(item for item in profile["apps"] if item["id"] == app["id"])
            assert_levels(installed["levels"])
            self.assertIn(f"{app['name']}.sh", profile["files"]["tools"])

            command_response = client.post("/command", json={"input": app["name"].lower()})
            command_data = command_response.get_json()
            self.assertTrue(command_data["runApp"])
            self.assertEqual(command_data["applicationId"], app["id"])
            assert_levels(command_data["applicationEffect"]["levels"])

    def test_button_maker_generated_app_keeps_button_choices_runtime_content(self):
        payload = {
            "name": "Choice Panel",
            "interface": "button_choices",
            "type": "custom",
            "level_title": "Wybierz tryb",
            "button_text": "Wybierz wariant działania.",
            "button_options": "Recon|risk_level=10|90\nShield|firewall=false|120",
            "price": 0,
        }

        def assert_levels(levels):
            self.assertTrue(levels)
            self.assertEqual(levels[0]["title"], "Wybierz tryb")
            self.assertEqual(levels[0]["text"], "Wybierz wariant działania.")
            self.assertEqual(len(levels[0]["options"]), 2)
            self.assertEqual(levels[0]["options"][0]["label"], "Recon")

        self.assert_generated_app_install_and_command_preserve_levels(payload, assert_levels)

    def test_term_creator_generated_app_keeps_terminal_runtime_content(self):
        payload = {
            "name": "Log Runner",
            "interface": "terminal",
            "type": "custom",
            "terminal_levels": [{
                "command": "./log-runner.sh --target current",
                "logs": "Start\nAnaliza\nRaport zapisany",
            }],
            "price": 0,
        }

        def assert_levels(levels):
            self.assertTrue(levels)
            self.assertEqual(levels[0]["command"], "./log-runner.sh --target current")
            self.assertEqual(levels[0]["logs"], ["Start", "Analiza", "Raport zapisany"])

        self.assert_generated_app_install_and_command_preserve_levels(payload, assert_levels)

    def test_window_maker_generated_app_keeps_window_runtime_content(self):
        payload = {
            "name": "Status Window",
            "interface": "window",
            "type": "custom",
            "level_title": "Panel statusu",
            "window_list": "Sygnał stabilny\nKanał gotowy",
            "window_buttons": "Uruchom|run_generated\nZamknij|close",
            "price": 0,
        }

        def assert_levels(levels):
            self.assertTrue(levels)
            self.assertEqual(levels[0]["title"], "Panel statusu")
            self.assertEqual(levels[0]["list"], ["Sygnał stabilny", "Kanał gotowy"])
            self.assertEqual(levels[0]["buttons"][0]["label"], "Uruchom")

        self.assert_generated_app_install_and_command_preserve_levels(payload, assert_levels)

    def test_appforge_generated_app_keeps_progress_runtime_content(self):
        payload = {
            "name": "Progress Tool",
            "interface": "progressbar_random",
            "type": "custom",
            "level_title": "Wykonanie",
            "progress_steps": ["Kalibracja", "Pomiar", "Zapis stanu"],
            "result_success": "Operacja zakończona.",
            "result_failure": "Operacja przerwana.",
            "price": 0,
        }

        def assert_levels(levels):
            self.assertTrue(levels)
            self.assertEqual(levels[0]["title"], "Wykonanie")
            self.assertEqual(levels[0]["steps"], ["Kalibracja", "Pomiar", "Zapis stanu"])
            self.assertEqual(levels[0]["result_success"], "Operacja zakończona.")
            self.assertEqual(levels[0]["result_failure"], "Operacja przerwana.")

        self.assert_generated_app_install_and_command_preserve_levels(payload, assert_levels)

    def test_pro_system_tool_has_higher_balance_than_basic_tool(self):
        basic = normalize_app_contract({
            "id": "basic_ping",
            "name": "Basic Ping",
            "type": "scanner",
            "price": 80,
            "map_actions": ["scan_ports"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
        })
        pro = normalize_app_contract({
            "id": "ghostlab_financial",
            "name": "GhostLab Financial",
            "type": "pro-system-tool",
            "category": "pro-system-tools",
            "price": 3000,
            "required_level": 12,
            "required_respect": 180,
            "tool_family": "sniffer",
            "tool_mode": "desktop",
            "operation_types": [],
            "resource_types": ["financial_records", "internal_recon_state"],
            "ghostlab_generated": True,
        }, infer_legacy=False)

        self.assertGreater(pro["disk_usage"], basic["disk_usage"])
        self.assertGreater(pro["power_score"], basic["power_score"])
        self.assertGreater(pro["price_hint"], basic["price_hint"])

    def test_generated_app_quality_depends_on_creator_power(self):
        payload = {
            "name": "Creator Scanner",
            "interface": "progressbar_random",
            "type": "scanner",
            "detects": "open_ports,user_location",
            "price": 10,
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 1, "respect": 0, "hackcoins": 0}):
            low_app = build_generated_app(payload, "low_creator", "Low")
        with patch.object(run.user_store, "get_profile", return_value={"level": 50, "respect": 1000, "hackcoins": 100000}):
            high_app = build_generated_app(payload, "high_creator", "High")

        self.assertGreater(high_app["creator_power"], low_app["creator_power"])
        self.assertGreater(high_app["quality_score"], low_app["quality_score"])
        self.assertGreater(high_app["reliability"], low_app["reliability"])
        self.assertGreater(high_app["price_hint"], low_app["price_hint"])

    def test_generated_app_price_uses_balance_floor(self):
        payload = {
            "name": "Cheap Creator Tool",
            "interface": "progressbar_random",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "tool_mode": "map",
            "map_actions": ["scan_ports"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["wifi_networks"],
            "target_types": ["router"],
            "price": 1,
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 5, "respect": 10, "hackcoins": 100}):
            app = build_generated_app(payload, "cheap_creator", "Cheap")

        self.assertGreater(app["price_hint"], 1)
        self.assertEqual(app["price"], app["price_hint"])

    def test_generated_app_preserves_explicit_gameplay_contract(self):
        payload = {
            "name": "Wizard Scanner",
            "interface": "progressbar_random",
            "type": "scanner",
            "map_actions": ["scan_ports"],
            "target_types": ["router", "server"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["wifi_networks"],
            "price": 25,
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 12, "respect": 120, "hackcoins": 1000}):
            app = build_generated_app(payload, "wizard_creator", "Wizard")

        self.assertEqual(app["map_actions"], ["scan_ports"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["router", "server"])
        self.assertEqual(app["operation_types"], ["wifi_scanner"])
        self.assertEqual(app["resource_types"], ["wifi_networks"])

    def test_map_scanner_creator_generates_explicit_contract(self):
        payload = {
            "name": "Map Recon",
            "interface": "progressbar_random",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "scanner_mode": "map",
            "map_actions": ["scan_ports", "scan_hotspots"],
            "target_types": ["router", "venue"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["wifi_networks", "internal_recon_state"],
            "detects": ["open_ports"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 10, "respect": 100, "hackcoins": 500}):
            app = build_generated_app(payload, "scanner_creator", "Scanner")

        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["tool_mode"], "map")
        self.assertEqual(app["scanner_mode"], "map")
        self.assertEqual(app["map_actions"], ["scan_ports", "scan_hotspots"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["router", "venue"])
        self.assertEqual(app["operation_types"], ["wifi_scanner"])
        self.assertEqual(app["resource_types"], ["wifi_networks", "internal_recon_state"])

    def test_desktop_scanner_creator_can_omit_map_actions(self):
        payload = {
            "name": "Desktop Recon",
            "interface": "terminal",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "scanner_mode": "desktop",
            "target_types": ["router", "server"],
            "operation_types": ["generic_trace"],
            "resource_types": ["internal_recon_state"],
            "detects": ["open_ports"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 8, "respect": 40, "hackcoins": 200}):
            app = build_generated_app(payload, "scanner_creator", "Scanner")

        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["tool_mode"], "desktop")
        self.assertEqual(app["scanner_mode"], "desktop")
        self.assertEqual(app["map_actions"], [])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["router", "server"])
        self.assertEqual(app["operation_types"], ["generic_trace"])
        self.assertEqual(app["resource_types"], ["internal_recon_state"])

    def test_hybrid_scanner_creator_can_use_map_and_aimed_target_contract(self):
        payload = {
            "name": "Hybrid Recon",
            "interface": "window",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "scanner_mode": "hybrid",
            "map_actions": ["trace", "scan_ports"],
            "target_types": ["poi", "player"],
            "operation_types": ["generic_trace"],
            "resource_types": ["location_history", "internal_recon_state"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 20, "respect": 250, "hackcoins": 5000}):
            app = build_generated_app(payload, "scanner_creator", "Scanner")

        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["tool_mode"], "hybrid")
        self.assertEqual(app["scanner_mode"], "hybrid")
        self.assertEqual(app["map_actions"], ["trace", "scan_ports"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["operation_types"], ["generic_trace"])
        self.assertEqual(app["resource_types"], ["location_history", "internal_recon_state"])

    def test_map_exploit_creator_generates_explicit_contract(self):
        payload = {
            "name": "Map Exploit",
            "interface": "button_choices",
            "type": "exploit",
            "tool_family": "exploit",
            "tool_mode": "map",
            "map_actions": ["exploit", "camera_shutdown"],
            "target_types": ["camera", "router"],
            "operation_types": ["camera_shutdown"],
            "resource_types": ["internal_recon_state"],
            "detects": ["weak_configs"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 18, "respect": 220, "hackcoins": 2000}):
            app = build_generated_app(payload, "exploit_creator", "Exploit")

        self.assertEqual(app["tool_family"], "exploit")
        self.assertEqual(app["tool_mode"], "map")
        self.assertEqual(app["map_actions"], ["exploit", "camera_shutdown"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["camera", "router"])
        self.assertEqual(app["operation_types"], ["camera_shutdown"])
        self.assertEqual(app["resource_types"], ["internal_recon_state"])

    def test_desktop_exploit_creator_can_omit_map_actions(self):
        payload = {
            "name": "Desktop Exploit",
            "interface": "terminal",
            "type": "exploit",
            "tool_family": "exploit",
            "tool_mode": "desktop",
            "target_types": ["server"],
            "operation_types": ["audio_interference"],
            "resource_types": ["internal_recon_state"],
            "detects": ["weak_configs"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 12, "respect": 80, "hackcoins": 300}):
            app = build_generated_app(payload, "exploit_creator", "Exploit")

        self.assertEqual(app["tool_family"], "exploit")
        self.assertEqual(app["tool_mode"], "desktop")
        self.assertEqual(app["map_actions"], [])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["target_types"], ["server"])
        self.assertEqual(app["operation_types"], ["audio_interference"])
        self.assertEqual(app["resource_types"], ["internal_recon_state"])

    def test_map_sniffer_creator_generates_explicit_contract(self):
        payload = {
            "name": "Map Sniffer",
            "interface": "progressbar_random",
            "type": "sniffer",
            "tool_family": "sniffer",
            "tool_mode": "map",
            "map_actions": ["sniff", "atm_logs"],
            "target_types": ["atm", "router"],
            "operation_types": ["atm_log_extraction"],
            "resource_types": ["atm_dump", "financial_records"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 16, "respect": 140, "hackcoins": 1200}):
            app = build_generated_app(payload, "sniffer_creator", "Sniffer")

        self.assertEqual(app["tool_family"], "sniffer")
        self.assertEqual(app["tool_mode"], "map")
        self.assertEqual(app["map_actions"], ["sniff", "atm_logs"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["operation_types"], ["atm_log_extraction"])
        self.assertEqual(app["resource_types"], ["atm_dump", "financial_records"])

    def test_hybrid_sniffer_creator_can_use_map_and_aimed_target_contract(self):
        payload = {
            "name": "Hybrid Sniffer",
            "interface": "window",
            "type": "sniffer",
            "tool_family": "sniffer",
            "tool_mode": "hybrid",
            "map_actions": ["install_sniffer", "camera_stream"],
            "target_types": ["camera", "server"],
            "operation_types": ["persistent_sniffer", "camera_stream"],
            "resource_types": ["credentials", "camera_dump", "internal_recon_state"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 24, "respect": 300, "hackcoins": 7000}):
            app = build_generated_app(payload, "sniffer_creator", "Sniffer")

        self.assertEqual(app["tool_family"], "sniffer")
        self.assertEqual(app["tool_mode"], "hybrid")
        self.assertEqual(app["map_actions"], ["install_sniffer", "camera_stream"])
        self.assertEqual(app["map_actions_source"], "creator_explicit")
        self.assertEqual(app["operation_types"], ["persistent_sniffer", "camera_stream"])
        self.assertEqual(app["resource_types"], ["credentials", "camera_dump", "internal_recon_state"])

    def test_creator_tool_family_disables_legacy_map_action_inference(self):
        payload = {
            "name": "Desktop Family Tool",
            "interface": "terminal",
            "type": "exploit",
            "tool_family": "exploit",
            "tool_mode": "desktop",
            "target_types": ["server"],
            "operation_types": ["audio_interference"],
            "resource_types": ["internal_recon_state"],
            "detects": ["open_ports", "weak_configs"],
        }

        with patch.object(run.user_store, "get_profile", return_value={"level": 10, "respect": 80, "hackcoins": 300}):
            app = build_generated_app(payload, "exploit_creator", "Exploit")

        self.assertEqual(app["map_actions"], [])
        self.assertEqual(app["map_actions_source"], "creator_explicit")

    def test_creator_rejects_unknown_explicit_family(self):
        payload = {
            "name": "Unknown Family",
            "interface": "terminal",
            "type": "tracker",
            "tool_family": "unknown_family",
            "tool_mode": "desktop",
            "target_types": ["server"],
            "operation_types": ["generic_trace"],
        }
        with self.assertRaisesRegex(ValueError, "rodzina"):
            build_generated_app(payload, "creator", "Creator")

    def test_creator_rejects_contract_outside_selected_family(self):
        payload = {
            "name": "Injected Contract",
            "interface": "terminal",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "tool_mode": "desktop",
            "target_types": ["server"],
            "operation_types": ["vehicle_ecu"],
            "resource_types": ["vehicle_diagnostics"],
        }
        with self.assertRaisesRegex(ValueError, "scanner_recon"):
            build_generated_app(payload, "creator", "Creator")

    def test_creator_rejects_map_actions_in_desktop_mode(self):
        payload = {
            "name": "Desktop Injection",
            "interface": "terminal",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "tool_mode": "desktop",
            "map_actions": ["trace"],
            "target_types": ["server"],
            "operation_types": ["generic_trace"],
            "resource_types": ["internal_recon_state"],
        }
        with self.assertRaisesRegex(ValueError, "akcji mapy"):
            build_generated_app(payload, "creator", "Creator")

    def test_creator_rejects_type_from_another_explicit_family(self):
        payload = {
            "name": "Canonical Recon",
            "interface": "window",
            "type": "vehicle_tool",
            "tool_family": "scanner_recon",
            "tool_mode": "hybrid",
            "map_actions": ["trace"],
            "target_types": ["vehicle"],
            "operation_types": ["generic_trace"],
            "resource_types": ["location_history"],
        }
        with self.assertRaisesRegex(ValueError, "nie pasuje"):
            build_generated_app(payload, "creator", "Creator")

    def test_scanner_recon_family_accepts_tracker_for_map_trace(self):
        payload = {
            "name": "Trace Compass",
            "interface": "button_choices",
            "type": "tracker",
            "tool_family": "scanner_recon",
            "tool_mode": "map",
            "map_actions": ["trace"],
            "target_types": ["poi", "pillar"],
            "operation_types": ["generic_trace"],
            "resource_types": ["location_history"],
        }
        with patch.object(run.user_store, "get_profile", return_value={"level": 8, "respect": 30}):
            app = build_generated_app(payload, "creator", "Creator")

        self.assertEqual(app["type"], "tracker")
        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["map_actions"], ["trace"])
        self.assertEqual(app["operation_types"], ["generic_trace"])

    def test_ghostlab_published_tool_has_app_contract(self):
        project = {
            "id": "glp_logs",
            "name": "Log Reader Pro",
            "slug": "log_reader_pro",
            "icon": "GL",
            "template_id": "system_log_reader",
            "template_name": "System Log Reader",
            "tool_category": "intel",
            "blueprint": run.default_ghostlab_blueprint("system_log_reader"),
        }
        project["artifact"] = run.build_ghostlab_artifact(project, project["blueprint"], 1)
        owner_profile = {"nick": "Builder", "level": 30, "respect": 450, "hackcoins": 12000}

        app = run.build_ghostlab_googleplex_app(project, "builder", owner_profile)

        self.assertEqual(app["type"], "pro-system-tool")
        self.assertEqual(app["category"], "pro-system-tools")
        self.assertEqual(app["source"], "ghostlab")
        self.assertEqual(app["tool_family"], "scanner_recon")
        self.assertEqual(app["tool_mode"], "desktop")
        self.assertEqual(app["map_actions"], [])
        self.assertEqual(app["map_actions_source"], "ghostlab_contract")
        self.assertEqual(app["target_types"], ["player"])
        self.assertEqual(app["operation_types"], [])
        self.assertEqual(app["resource_types"], ["device_logs", "internal_recon_state"])
        self.assertGreater(app["file_size"], 0)
        self.assertGreaterEqual(app["disk_usage"], app["file_size"])
        self.assertEqual(app["install_size"], app["disk_usage"])
        self.assertGreater(app["quality_score"], 0)
        self.assertGreater(app["reliability"], 0)

    def test_ghostlab_published_tool_preserves_requirements_and_googleplex_shape(self):
        project = {
            "id": "glp_fin",
            "name": "Financial Lab Tool",
            "slug": "financial_lab_tool",
            "template_id": "financial_sniffer",
            "template_name": "Financial Sniffer",
            "tool_category": "finance",
            "blueprint": run.default_ghostlab_blueprint("financial_sniffer"),
        }
        project["artifact"] = run.build_ghostlab_artifact(project, project["blueprint"], 2)
        owner_profile = {"nick": "Builder", "level": 40, "respect": 700, "hackcoins": 20000}

        app = run.build_ghostlab_googleplex_app(project, "builder", owner_profile)
        payload = googleplex_catalog_payload(app, {"hackcoins": 99999, "apps": []})

        self.assertEqual(app["required_level"], 12)
        self.assertEqual(app["required_respect"], 180)
        self.assertEqual(app["purchase_account"], "builder")
        self.assertEqual(app["tool_family"], "sniffer")
        self.assertEqual(payload["id"], app["id"])
        self.assertEqual(payload["type"], "pro-system-tool")
        self.assertEqual(payload["map_actions"], [])
        self.assertEqual(payload["operation_types"], [])
        self.assertEqual(payload["resource_types"], ["financial_records", "internal_recon_state"])

    def test_operation_quality_can_raise_generated_file_quality(self):
        profile = {
            "files": {
                "gps": [{
                    "name": "quality_demo.log",
                    "source_operation_id": "op_quality",
                    "resource_types": ["gps_logs"],
                    "metadata": {"checkpoint_count": 1, "quality_score": 35},
                }]
            }
        }
        ensure_files_inventory(profile)
        operation = {
            "operation_id": "op_quality",
            "source_app_quality": {
                "creator_power": 90,
                "quality_score": 82,
                "reliability": 88,
            },
        }

        changed = apply_operation_quality_to_files(profile, operation)
        ensure_files_inventory(profile)
        file_entry = profile["files"]["gps"][0]

        self.assertTrue(changed)
        self.assertEqual(file_entry["quality_score"], 82)
        self.assertEqual(file_entry["metadata"]["source_app_quality_score"], 82)
        self.assertEqual(file_entry["metadata"]["source_app_reliability"], 88)

    def test_runtime_files_and_profile_get_soft_storage_usage(self):
        profile = {
            "apps": [
                normalize_app_contract({
                    "id": "gps_tracker_v1",
                    "name": "GPS Tracker",
                    "map_actions": ["trace_gps"],
                    "operation_types": ["vehicle_tracking"],
                    "resource_types": ["gps_logs"],
                    "disk_usage": 20,
                })
            ],
            "files": {
                "gps": [{
                    "name": "gps_demo.log",
                    "resource_types": ["gps_logs", "location_history"],
                    "metadata": {"checkpoint_count": 3},
                }]
            },
        }

        files = ensure_files_inventory(profile)
        normalize_profile_storage(profile)

        self.assertGreater(files["gps"][0]["file_size"], 0)
        self.assertEqual(profile["storage_capacity"], 512)
        self.assertEqual(profile["storage_unit"], "MB")
        self.assertTrue(profile["storage_soft_limit"])
        self.assertGreaterEqual(profile["storage_used"], 20 + files["gps"][0]["file_size"])

    def test_googleplex_catalog_payload_blocks_installed_and_missing_hc(self):
        app = normalize_app_contract({
            "id": "atm_reader_v1",
            "name": "ATM Reader",
            "price": 500,
            "map_actions": ["atm_logs"],
            "operation_types": ["atm_log_extraction"],
            "resource_types": ["atm_dump"],
        })

        installed_payload = googleplex_catalog_payload(app, {
            "hackcoins": 1000,
            "apps": [{"id": "atm_reader_v1"}],
        })
        poor_payload = googleplex_catalog_payload(app, {
            "hackcoins": 10,
            "apps": [],
        })

        self.assertTrue(installed_payload["installed"])
        self.assertEqual(installed_payload["install_blocked_reason"], "Aplikacja juz kupiona.")
        self.assertFalse(poor_payload["can_afford"])
        self.assertIn("Brak HC", poor_payload["install_blocked_reason"])

    def test_uninstall_app_removes_profile_app_tool_and_recalculates_storage(self):
        app = normalize_app_contract({
            "id": "lifecycle_tool",
            "name": "Lifecycle Tool",
            "type": "scanner",
            "price": 100,
            "disk_usage": 30,
            "map_actions": ["scan_ports"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
        })
        profile = {
            "username": "tester",
            "apps": [app],
            "files": {
                "tools": ["Lifecycle Tool.sh"],
                "projects": ["Lifecycle Tool.sh"],
            },
            "storage_capacity": 512,
        }
        updates = {}

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                updates.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager):
            response = client.post("/api/apps/uninstall", json={
                "app_id": "lifecycle_tool",
                "tool_file": "Lifecycle Tool.sh",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["removed_app"])
        self.assertTrue(data["removed_tool"])
        self.assertEqual(data["apps"], [])
        self.assertNotIn("Lifecycle Tool.sh", data["files"]["tools"])
        self.assertIn("Lifecycle Tool.sh", data["files"]["projects"])
        self.assertEqual(updates["apps"], [])
        self.assertNotIn("Lifecycle Tool.sh", updates["files"]["tools"])
        self.assertLess(data["storage"]["used"], 30 + run.FILE_CATEGORY_SIZE_HINTS_MB["projects"])

    def test_uninstall_app_is_idempotent_for_missing_app(self):
        profile = {
            "username": "tester",
            "apps": [],
            "files": {"tools": [], "projects": []},
            "storage_capacity": 512,
        }
        updates = {}

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                updates.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager):
            response = client.post("/api/apps/uninstall", json={
                "app_id": "missing_tool",
                "tool_file": "Missing Tool.sh",
            })

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "noop")
        self.assertTrue(data["success"])
        self.assertFalse(data["removed_app"])
        self.assertFalse(data["removed_tool"])
        self.assertEqual(data["apps"], [])
        self.assertEqual(data["files"]["tools"], [])
        self.assertEqual(updates["apps"], [])

    def test_uninstall_seed_and_ghostlab_apps_only_changes_profile(self):
        seed_app = normalize_app_contract({
            "id": "seed_scan",
            "name": "Seed Scan",
            "type": "scanner",
            "price": 120,
            "map_actions": ["scan_ports"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
        })
        ghostlab_app = normalize_app_contract({
            "id": "ghostlab_tool",
            "name": "GhostLab Tool",
            "type": "pro-system-tool",
            "category": "pro-system-tools",
            "ghostlab_generated": True,
            "price": 3000,
            "project_file": "GhostLab Tool.sh",
            "resource_types": ["internal_recon_state"],
        }, infer_legacy=False)
        profile = {
            "username": "tester",
            "apps": [seed_app, ghostlab_app],
            "files": {
                "tools": ["Seed Scan.sh", "GhostLab Tool.sh"],
                "projects": ["GhostLab Tool.glab"],
            },
            "storage_capacity": 512,
        }
        updates = {}

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)
                updates.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run.resources_store, "set", side_effect=AssertionError("catalog should not change")):
            ghost_response = client.post("/api/apps/uninstall", json={
                "app_id": "ghostlab_tool",
                "tool_file": "GhostLab Tool.sh",
            })
            seed_response = client.post("/api/apps/uninstall", json={
                "app_id": "seed_scan",
                "tool_file": "Seed Scan.sh",
            })

        self.assertEqual(ghost_response.status_code, 200)
        self.assertEqual(seed_response.status_code, 200)
        self.assertEqual(seed_response.get_json()["apps"], [])
        self.assertEqual(updates["files"]["tools"], [])
        self.assertEqual(updates["files"]["projects"], ["GhostLab Tool.glab"])

    def test_googleplex_storage_upgrade_increases_capacity_without_app_or_tool(self):
        profile = {
            "username": "neo",
            "nick": "Neo",
            "hackcoins": 5000,
            "level": 10,
            "respect": 100,
            "apps": [],
            "files": {"tools": []},
            "storage_capacity": 512,
            "storage_used": 100,
            "system_messages": [],
        }
        product = next(item for item in run.storage_upgrade_products_catalog() if item["id"] == "storage_ghost_vault_basic")

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        fd, delta_db_path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        try:
            delta_bus = GameStateDeltaBus(db_path=delta_db_path)
            with canonical_wallet_test_runtime({"neo": profile["hackcoins"], "admin": 0}), \
                    patch.object(run, "delta_bus", delta_bus), \
                    patch.object(run, "sync_session_profile", return_value=profile), \
                    patch.object(run, "UserProfileManager", FakeManager), \
                    patch.object(run, "get_app_catalog", return_value=[product]), \
                    patch.object(run, "ensure_purchase_account_profile", return_value={"username": "admin", "hackcoins": 0}), \
                    patch.object(run.user_store, "save_profile", return_value=None), \
                    patch.object(run.mail_store, "add_direct_notification", return_value=None):
                response = client.post("/install-app", json={"app_id": product["id"]})
            storage_changes = [
                event for event in delta_bus.get_changes_since("neo", 0)["changes"]
                if event["scope"] == "storage"
            ]
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{delta_db_path}{suffix}"
                if os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except PermissionError:
                        pass

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(profile["storage_capacity"], 512 + product["storage_capacity_bonus"])
        self.assertEqual(profile["apps"], [])
        self.assertEqual(profile["files"]["tools"], [])
        self.assertEqual(profile["storage_upgrades"][0]["id"], product["id"])
        self.assertEqual(profile["product_purchases"][0]["id"], product["id"])
        self.assertEqual(profile["product_purchases"][0]["product_type"], "storage_upgrade")
        self.assertEqual(data["storage"]["added"], product["storage_capacity_bonus"])
        self.assertIn("storage.capacity_changed", [event["type"] for event in storage_changes])

    def test_googleplex_legacy_storage_upgrade_without_effects_increases_capacity(self):
        profile = {
            "username": "neo",
            "nick": "Neo",
            "hackcoins": 5000,
            "level": 10,
            "respect": 100,
            "apps": [],
            "files": {"tools": []},
            "storage_capacity": 512,
            "storage_used": 0,
            "system_messages": [],
        }
        product = dict(next(item for item in run.storage_upgrade_products_catalog() if item["id"] == "storage_ghost_vault_basic"))
        product.pop("effects", None)

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"], "admin": 0}), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "get_app_catalog", return_value=[product]), \
                patch.object(run, "ensure_purchase_account_profile", return_value={"username": "admin", "hackcoins": 0}), \
                patch.object(run.user_store, "save_profile", return_value=None), \
                patch.object(run.mail_store, "add_direct_notification", return_value=None):
            response = client.post("/install-app", json={"app_id": product["id"]})

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["status"], "success")
        self.assertEqual(profile["storage_capacity"], 512 + product["storage_capacity_bonus"])
        self.assertEqual(data["storage"]["added"], product["storage_capacity_bonus"])
        self.assertEqual(profile["apps"], [])
        self.assertEqual(profile["files"]["tools"], [])
        self.assertEqual(profile["storage_upgrades"][0]["id"], product["id"])
        self.assertEqual(profile["product_purchases"][0]["id"], product["id"])

    def test_googleplex_storage_upgrade_product_purchases_blocks_duplicate(self):
        profile = {
            "username": "neo",
            "nick": "Neo",
            "hackcoins": 5000,
            "level": 10,
            "respect": 100,
            "apps": [],
            "files": {"tools": []},
            "storage_capacity": 512,
            "storage_used": 0,
            "product_purchases": [{"id": "storage_ghost_vault_basic", "product_type": "storage_upgrade"}],
            "system_messages": [],
        }
        product = next(item for item in run.storage_upgrade_products_catalog() if item["id"] == "storage_ghost_vault_basic")

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"], "admin": 0}), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "get_app_catalog", return_value=[product]), \
                patch.object(run, "ensure_purchase_account_profile", return_value={"username": "admin", "hackcoins": 0}):
            response = client.post("/install-app", json={"app_id": product["id"]})

        data = response.get_json()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(data["reason"], "already_purchased")
        self.assertEqual(profile["storage_capacity"], 512)
        self.assertEqual(profile["hackcoins"], 5000)
        self.assertEqual(profile["apps"], [])
        self.assertEqual(profile["files"]["tools"], [])

    def test_profile_template_sync_is_additive_and_preserves_unknown_fields(self):
        manager = UserProfileManager.__new__(UserProfileManager)
        manager._locked_keys = {"username", "salt", "password"}
        manager._dynamic_profile_keys = {"googleplex_products", "product_purchases", "storage_upgrades"}
        profile = {
            "username": "neo",
            "hackcoins": 100,
            "googleplex_products": [{"id": "storage_ghost_vault_basic"}],
            "product_purchases": [{"id": "storage_ghost_vault_basic"}],
            "storage_upgrades": [{"id": "storage_ghost_vault_basic"}],
            "temporary_debug_field": True,
        }
        template = {"username": "", "hackcoins": 0}

        changed = manager._recursive_sync(profile, template)

        self.assertFalse(changed)
        self.assertIn("googleplex_products", profile)
        self.assertIn("product_purchases", profile)
        self.assertIn("storage_upgrades", profile)
        self.assertTrue(profile["temporary_debug_field"])

    def test_googleplex_storage_reconcile_repairs_purchased_upgrade_capacity(self):
        product = next(item for item in run.storage_upgrade_products_catalog() if item["id"] == "storage_ghost_vault_basic")
        profile = {
            "username": "neo",
            "hackcoins": 1000,
            "storage_capacity": 512,
            "storage_used": 511,
            "googleplex_products": [{"id": product["id"], "product_type": "storage_upgrade"}],
            "files": {"camera": [{"id": "camera_1", "file_size": 511}]},
        }

        changed = run.reconcile_googleplex_storage_products(profile)
        normalize_profile_storage(profile)

        self.assertTrue(changed)
        self.assertEqual(profile["storage_capacity"], 512 + product["storage_capacity_bonus"])
        self.assertEqual(profile["storage_upgrades"][0]["id"], product["id"])
        self.assertEqual(profile["product_purchases"][0]["id"], product["id"])
        self.assertFalse(profile["storage_over_limit"])

    def test_profile_storage_normalize_repairs_legacy_capacity_and_purchased_upgrades(self):
        product = next(item for item in run.storage_upgrade_products_catalog() if item["id"] == "storage_ghost_vault_basic")
        profile = {
            "username": "neo",
            "storage_capacity": 64,
            "storage_used": 0,
            "googleplex_products": [{"id": product["id"], "product_type": "storage_upgrade"}],
            "files": {"camera": []},
        }

        normalize_profile_storage(profile)

        self.assertEqual(profile["storage_capacity"], run.DEFAULT_STORAGE_CAPACITY_MB + product["storage_capacity_bonus"])
        self.assertEqual(profile["storage_upgrades"][0]["id"], product["id"])
        self.assertEqual(profile["product_purchases"][0]["id"], product["id"])
        self.assertFalse(profile["storage_over_limit"])

    def test_record_storage_delta_repairs_stale_inventory_storage_projection(self):
        product = next(item for item in run.storage_upgrade_products_catalog() if item["id"] == "storage_ghost_vault_basic")
        profile = {
            "username": "neo",
            "storage_capacity": 64,
            "storage_used": 0,
            "googleplex_products": [{"id": product["id"], "product_type": "storage_upgrade"}],
            "files": {"tools": []},
            "apps": [],
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            inventory_store = PlayerInventoryStore(os.path.join(tmpdir, "inventory.sqlite3"))
            delta_bus = GameStateDeltaBus(db_path=os.path.join(tmpdir, "delta.sqlite3"), retention_limit=20)
            with patch.object(run, "player_inventory_store", inventory_store), patch.object(run, "delta_bus", delta_bus):
                run.record_storage_delta("neo", profile, reason="test")
                snapshot = inventory_store.snapshot("neo")

        self.assertEqual(profile["storage_capacity"], run.DEFAULT_STORAGE_CAPACITY_MB + product["storage_capacity_bonus"])
        self.assertEqual(snapshot["storage"]["capacity"], profile["storage_capacity"])
        self.assertFalse(snapshot["storage"]["modifiers"]["storage_over_limit"])

    def test_googleplex_storage_upgrade_requires_hackcoins(self):
        profile = {
            "username": "neo",
            "nick": "Neo",
            "hackcoins": 1,
            "level": 10,
            "respect": 100,
            "apps": [],
            "files": {"tools": []},
            "storage_capacity": 512,
            "storage_used": 100,
            "system_messages": [],
        }
        product = next(item for item in run.storage_upgrade_products_catalog() if item["id"] == "storage_ghost_vault_basic")

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"], "admin": 0}), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "get_app_catalog", return_value=[product]), \
                patch.object(run, "ensure_purchase_account_profile", return_value={"username": "admin", "hackcoins": 0}):
            response = client.post("/install-app", json={"app_id": product["id"]})

        data = response.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["reason"], "insufficient_hc")
        self.assertEqual(profile["storage_capacity"], 512)
        self.assertNotIn("storage_upgrades", profile)
        self.assertEqual(profile["apps"], [])
        self.assertEqual(profile["files"]["tools"], [])

    def test_googleplex_travel_ticket_moves_player_to_catalog_city(self):
        profile = {
            "username": "neo",
            "nick": "Neo",
            "hackcoins": 5000,
            "level": 10,
            "respect": 100,
            "apps": [],
            "files": {"tools": []},
            "storage_capacity": 512,
            "curently_possition": {"lat": 0, "lng": 0},
            "system_messages": [],
        }
        product = next(item for item in run.googleplex_product_catalog() if item["id"] == "ticket_warszawa")

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"
        with canonical_wallet_test_runtime({"neo": profile["hackcoins"], "admin": 0}), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "get_app_catalog", return_value=[product]), \
                patch.object(run, "ensure_purchase_account_profile", return_value={"username": "admin", "hackcoins": 0}), \
                patch.object(run.user_store, "save_profile", return_value=None), \
                patch.object(run.mail_store, "add_direct_notification", return_value=None):
            response = client.post("/install-app", json={
                "app_id": product["id"],
                "transaction_key": "test:googleplex:ticket_warszawa:1",
            })

        city = run.TRAVEL_CITIES["Warszawa"]
        data = response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(profile["curently_possition"], {"lat": city["lat"], "lng": city["lng"]})
        self.assertEqual(profile["current_city"], "Warszawa")
        self.assertEqual(profile["apps"], [])
        self.assertEqual(profile["files"]["tools"], [])

    def test_googleplex_product_effects_add_profile_bonuses(self):
        profile = {
            "username": "neo",
            "nick": "Neo",
            "hackcoins": 20000,
            "level": 20,
            "respect": 200,
            "apps": [],
            "files": {"tools": []},
            "storage_capacity": 512,
            "system_messages": [],
        }

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        products = [
            next(item for item in run.googleplex_product_catalog() if item["id"] == "map_zoom_plus_1"),
            next(item for item in run.googleplex_product_catalog() if item["id"] == "scan_range_300"),
            next(item for item in run.googleplex_product_catalog() if item["id"] == "bike_range_500"),
        ]
        with canonical_wallet_test_runtime({"neo": profile["hackcoins"], "admin": 0}), \
                patch.object(run, "sync_session_profile", return_value=profile), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "get_app_catalog", return_value=products), \
                patch.object(run, "ensure_purchase_account_profile", return_value={"username": "admin", "hackcoins": 0}), \
                patch.object(run.user_store, "save_profile", return_value=None), \
                patch.object(run.mail_store, "add_direct_notification", return_value=None):
            for product in products:
                response = client.post("/install-app", json={"app_id": product["id"]})
                self.assertEqual(response.get_json()["status"], "success")

        self.assertEqual(profile["map_zoom_bonus"], 1)
        self.assertEqual(profile["scan_range_bonus"], 300)
        self.assertEqual(profile["bike_range_bonus"], 500)
        self.assertEqual(profile["hackcoins"], 20000 - sum(int(product["price"]) for product in products))
        self.assertEqual(profile["apps"], [])
        self.assertEqual(profile["files"]["tools"], [])

    def test_googleplex_product_requirements_block_level_and_respect(self):
        product = next(item for item in run.googleplex_product_catalog() if item["id"] == "map_zoom_plus_2")

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                pass

        def post_with(profile):
            client = run.app.test_client()
            with client.session_transaction() as sess:
                sess["user"] = "neo"
            with canonical_wallet_test_runtime({"neo": profile["hackcoins"]}), \
                    patch.object(run, "sync_session_profile", return_value=profile), \
                    patch.object(run, "UserProfileManager", FakeManager), \
                    patch.object(run, "get_app_catalog", return_value=[product]):
                return client.post("/install-app", json={"app_id": product["id"]}).get_json()

        low_level = {
            "username": "neo",
            "hackcoins": 99999,
            "level": 1,
            "respect": 100,
            "apps": [],
            "files": {"tools": []},
        }
        low_respect = {
            "username": "neo",
            "hackcoins": 99999,
            "level": 10,
            "respect": 0,
            "apps": [],
            "files": {"tools": []},
        }

        self.assertIn("Wymagany poziom", post_with(low_level)["message"])
        self.assertIn("Wymagany Respect", post_with(low_respect)["message"])

    def test_generated_app_install_tools_uninstall_lifecycle(self):
        payload = {
            "name": "Lifecycle Generated",
            "interface": "progressbar_random",
            "type": "scanner",
            "tool_family": "scanner_recon",
            "tool_mode": "map",
            "map_actions": ["scan_ports"],
            "target_types": ["router"],
            "operation_types": ["wifi_scanner"],
            "resource_types": ["internal_recon_state"],
            "price": 1,
        }
        with patch.object(run.user_store, "get_profile", return_value={"level": 12, "respect": 100, "hackcoins": 1000}):
            app = build_generated_app(payload, "tester", "Tester")
        profile = {
            "username": "tester",
            "nick": "Tester",
            "hackcoins": 10000,
            "apps": [],
            "files": {"tools": [], "projects": []},
            "storage_capacity": 512,
            "system_messages": [],
        }
        store = [dict(app)]
        fd, path = tempfile.mkstemp(suffix=".sqlite3")
        os.close(fd)
        bus = GameStateDeltaBus(db_path=path)

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        try:
            client = run.app.test_client()
            with client.session_transaction() as sess:
                sess["user"] = "tester"
            with canonical_wallet_test_runtime({"tester": 10000}), \
                    patch.object(run, "delta_bus", bus), \
                    patch.object(run, "sync_session_profile", return_value=profile), \
                    patch.object(run, "UserProfileManager", FakeManager), \
                    patch.object(run.resources_store, "get", return_value=store), \
                    patch.object(run.resources_store, "set", side_effect=lambda key, value: store[:] == value), \
                    patch.object(run, "get_app_catalog", return_value=store):
                install_response = client.post("/install-app", json={"app_id": app["id"]})
                install_data = install_response.get_json()
                self.assertEqual(install_response.status_code, 200)
                self.assertEqual(install_data["status"], "success")
                self.assertTrue(any(item.get("id") == app["id"] for item in profile["apps"]))
                self.assertIn(f"{app['name']}.sh", profile["files"]["tools"])
                self.assertTrue(any(item.get("id") == app["id"] for item in install_data["apps"]))
                self.assertIn(f"{app['name']}.sh", install_data["files"]["tools"])
                uninstall_response = client.post("/api/apps/uninstall", json={
                    "app_id": app["id"],
                    "tool_file": f"{app['name']}.sh",
                })

            uninstall_data = uninstall_response.get_json()
            self.assertEqual(uninstall_response.status_code, 200)
            self.assertEqual(uninstall_data["status"], "success")
            self.assertFalse(any(item.get("id") == app["id"] for item in uninstall_data["apps"]))
            self.assertNotIn(f"{app['name']}.sh", uninstall_data["files"]["tools"])

            app_events = [
                item for item in bus.get_changes_since("tester", 0)["changes"]
                if item["scope"] == "apps"
            ]
            self.assertEqual([item["type"] for item in app_events], [
                "apps.app_installed",
                "apps.app_uninstalled",
            ])
            self.assertEqual(app_events[0]["payload"]["app_id"], app["id"])
            self.assertIn(f"{app['name']}.sh", app_events[0]["payload"]["files"]["tools"])
            self.assertNotIn(f"{app['name']}.sh", app_events[1]["payload"]["files"]["tools"])
        finally:
            for suffix in ("", "-wal", "-shm"):
                candidate = f"{path}{suffix}"
                if os.path.exists(candidate):
                    try:
                        os.remove(candidate)
                    except PermissionError:
                        pass

    def test_create_operation_for_app_action_adds_runtime_operation(self):
        profile = {"operations": []}
        app = {
            "id": "gps_tracker_v1",
            "name": "GPS Tracker",
            "operation_types": ["vehicle_tracking"],
            "resource_types": ["gps_logs", "location_history"],
        }
        target = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "Tracked car",
            "source_type": "car",
            "target_mode": "standard",
        }

        created = create_operations_for_app_action(profile, "neo", app, "trace_gps", target)

        self.assertEqual(len(created), 1)
        operation = created[0]
        self.assertEqual(profile["operations"], created)
        self.assertEqual(operation["operation_type"], "vehicle_tracking")
        self.assertEqual(operation["owner_username"], "neo")
        self.assertEqual(operation["source_app_id"], "gps_tracker_v1")
        self.assertEqual(operation["map_action_id"], "trace_gps")
        self.assertEqual(operation["target_type"], "vehicle")
        self.assertEqual(operation["target_mode"], "standard")
        self.assertEqual(operation["status"], "running")
        self.assertIn("operation_id", operation)
        self.assertIn("expires_at", operation)
        self.assertEqual(operation["resource_buffer"]["resource_types"], ["gps_logs", "location_history"])
        self.assertEqual(operation["resource_buffer"]["items"], [])
        self.assertEqual(operation["risk_state"]["level"], "none")
        self.assertEqual(operation["movement_model"], "road_movement")
        self.assertIn("procedural_seed", operation)

    def test_operation_expiry_uses_timezone_aware_utc_durations(self):
        cases = [
            ("trace_gps", "vehicle_tracking", "car", 2 * 60 * 60),
            ("camera_stream", "camera_stream", "camera", 30 * 60),
            ("install_sniffer", "persistent_sniffer", "router", 3 * 60 * 60),
        ]

        for map_action_id, operation_type, source_type, expected_duration in cases:
            with self.subTest(operation_type=operation_type):
                operation = run.build_operation_instance(
                    "neo",
                    {
                        "id": f"{operation_type}_app",
                        "name": operation_type,
                        "resource_types": [],
                    },
                    map_action_id,
                    operation_type,
                    {
                        "lat": 52.1,
                        "lng": 21.2,
                        "label": operation_type,
                        "source_type": source_type,
                        "target_mode": "standard",
                    },
                )
                started_ts = run.parse_operation_timestamp(operation["started_at"])
                expires_ts = run.parse_operation_timestamp(operation["expires_at"])

                self.assertIsNotNone(started_ts)
                self.assertIsNotNone(expires_ts)
                self.assertAlmostEqual(expires_ts - started_ts, expected_duration, delta=1)

                refreshed = refresh_operation_runtime(operation, now_ts=started_ts + 1)
                self.assertEqual(refreshed["status"], "running")
                self.assertGreater(refreshed["remaining_seconds"], 0)
                self.assertTrue(run.operation_is_active(refreshed, now_ts=started_ts + 1))

    def test_refresh_operation_runtime_marks_expired_operation_timeout(self):
        profile = {
            "operations": [{
                "operation_id": "op_expired",
                "operation_type": "camera_stream",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Camera"},
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(profile["operations"][0]["status"], "timeout")
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(refreshed[0]["remaining_seconds"], 0)

    def test_vehicle_tracking_current_position_changes_over_time(self):
        operation = {
            "operation_id": "op_vehicle",
            "operation_type": "vehicle_tracking",
            "owner_username": "neo",
            "target": {"lat": 52.1, "lng": 21.2, "label": "Tracked car"},
            "target_type": "vehicle",
            "status": "running",
            "started_at": "2026-06-27T10:00:00Z",
            "expires_at": "2026-06-27T12:00:00Z",
            "duration_seconds": 7200,
            "movement_model": "road_movement",
            "procedural_seed": 12345,
        }

        early = refresh_operation_runtime(
            operation,
            now_ts=datetime(2026, 6, 27, 10, 10, tzinfo=timezone.utc).timestamp(),
        )
        later = refresh_operation_runtime(
            operation,
            now_ts=datetime(2026, 6, 27, 11, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertNotEqual(early["current_position"], later["current_position"])
        self.assertEqual(early["movement_model"], "road_movement")

    def test_vehicle_tracking_timeout_creates_single_gps_file(self):
        profile = {
            "files": {"gps": []},
            "operations": [{
                "operation_id": "op_vehicle_done",
                "operation_type": "vehicle_tracking",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Tracked car"},
                "target_id": "map:52.1:21.2:Tracked car",
                "target_type": "vehicle",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T12:00:00Z",
                "duration_seconds": 7200,
                "movement_model": "road_movement",
                "procedural_seed": 12345,
                "resource_buffer": {"resource_types": ["gps_logs", "location_history"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 12, 5, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 12, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["operations"][0]["checkpoints"]), 8)
        self.assertEqual(len(profile["files"]["gps"]), 1)

        gps_file = profile["files"]["gps"][0]
        self.assertEqual(gps_file["file_category"], "gps")
        self.assertEqual(gps_file["directory"], "/data/gps")
        self.assertEqual(gps_file["preview_mode"], "table")
        self.assertEqual(gps_file["metadata"]["operation_id"], "op_vehicle_done")
        self.assertEqual(gps_file["metadata"]["checkpoint_count"], 8)
        self.assertEqual(gps_file["resource_types"], ["gps_logs", "location_history"])
        self.assertEqual(len(gps_file["checkpoints"]), 8)

    def test_device_tracking_basic_app_creates_small_device_package(self):
        profile = {
            "files": {"device": [], "personal": []},
            "operations": [{
                "operation_id": "op_device_basic",
                "operation_type": "device_tracking",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Klient"},
                "target_id": "map:52.1:21.2:Klient",
                "target_type": "person",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T11:00:00Z",
                "duration_seconds": 3600,
                "movement_model": "local_walk",
                "procedural_seed": 555,
                "resource_buffer": {"resource_types": [], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 5, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["device"]), 1)
        self.assertEqual(len(profile["files"]["personal"]), 0)

        device_file = profile["files"]["device"][0]
        self.assertEqual(device_file["resource_types"], ["location_history", "device_logs"])
        self.assertEqual(device_file["metadata"]["completeness"]["tier"], "basic")
        self.assertEqual(device_file["metadata"]["completeness"]["percent"], 33)

    def test_device_tracking_better_app_creates_richer_personal_package(self):
        profile = {
            "files": {"device": [], "personal": []},
            "operations": [{
                "operation_id": "op_device_rich",
                "operation_type": "device_tracking",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Smartfon"},
                "target_id": "map:52.1:21.2:Smartfon",
                "target_type": "phone",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T11:00:00Z",
                "duration_seconds": 3600,
                "movement_model": "local_walk",
                "procedural_seed": 777,
                "resource_buffer": {
                    "resource_types": [
                        "location_history",
                        "device_logs",
                        "personal_records",
                        "call_history",
                        "messenger_data",
                    ],
                    "items": [],
                },
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 5, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["device"]), 0)
        self.assertEqual(len(profile["files"]["personal"]), 1)

        personal_file = profile["files"]["personal"][0]
        self.assertEqual(personal_file["file_category"], "personal")
        self.assertEqual(personal_file["directory"], "/data/personal")
        self.assertEqual(personal_file["metadata"]["completeness"]["tier"], "rich")
        self.assertEqual(personal_file["metadata"]["completeness"]["percent"], 83)
        self.assertIn("messenger_data", personal_file["resource_types"])

    def test_camera_stream_creates_fragments_without_duplicates(self):
        profile = {
            "files": {"camera": []},
            "operations": [{
                "operation_id": "op_camera_stream",
                "operation_type": "camera_stream",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera sklepu"},
                "target_id": "map:52.1:21.2:Kamera sklepu",
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:30:00Z",
                "duration_seconds": 1800,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": [], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 12, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 12, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "running")
        self.assertEqual(refreshed[0]["remaining_seconds"], 1080)
        self.assertEqual(len(profile["files"]["camera"]), 2)
        self.assertEqual(len(profile["operations"][0]["fragments"]), 2)

        camera_file = profile["files"]["camera"][0]
        self.assertEqual(camera_file["file_category"], "camera")
        self.assertEqual(camera_file["directory"], "/data/camera")
        self.assertEqual(camera_file["preview_mode"], "media_placeholder")
        self.assertEqual(camera_file["resource_types"], ["camera_dump"])
        self.assertEqual(camera_file["metadata"]["operation_id"], "op_camera_stream")
        self.assertEqual(camera_file["metadata"]["duration_seconds"], 300)
        self.assertEqual(len(profile["files"]["camera"]), len(refreshed_again[0]["fragments"]))

    def test_camera_stream_honors_video_material_resource(self):
        profile = {
            "files": {"camera": []},
            "operations": [{
                "operation_id": "op_camera_video",
                "operation_type": "camera_stream",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera parkingu"},
                "target_id": "map:52.1:21.2:Kamera parkingu",
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:15:00Z",
                "duration_seconds": 900,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": ["video_material"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["camera"]), 3)
        self.assertTrue(profile["files"]["camera"][0]["name"].endswith(".vid"))
        self.assertEqual(profile["files"]["camera"][0]["metadata"]["resource_primary"], "video_material")
        self.assertEqual(profile["files"]["camera"][0]["resource_types"], ["camera_dump", "video_material"])

    def test_camera_shutdown_sets_timed_support_state(self):
        profile = {
            "files": {},
            "operations": [{
                "operation_id": "op_camera_shutdown",
                "operation_type": "camera_shutdown",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera sklepu"},
                "target_id": "map:52.1:21.2:Kamera sklepu",
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": [], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 5, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_late, changed_late = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 11, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["support_state"]["camera_state"], "offline")
        self.assertEqual(refreshed[0]["support_state"]["remaining_seconds"], 300)
        self.assertEqual(refreshed[0]["support_state"]["risk_modifier"], "camera_shutdown")
        self.assertTrue(changed_late)
        self.assertEqual(refreshed_late[0]["status"], "timeout")
        self.assertEqual(profile["operations"][0]["support_state"]["camera_state"], "recovering")

    def test_atm_logs_app_creates_high_risk_operation(self):
        profile = {"operations": []}
        app = {
            "id": "atm_reader_v1",
            "name": "ATM Reader",
            "operation_types": ["atm_log_extraction"],
            "resource_types": ["atm_dump"],
        }
        target = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "ATM",
            "source_type": "atm",
            "target_mode": "standard",
        }

        created = create_operations_for_app_action(profile, "neo", app, "atm_logs", target)

        self.assertEqual(len(created), 1)
        operation = created[0]
        self.assertEqual(operation["operation_type"], "atm_log_extraction")
        self.assertEqual(operation["target_type"], "atm")
        self.assertEqual(operation["risk_state"]["level"], "high")
        self.assertIn("atm_alarm", operation["risk_state"]["events"])
        self.assertFalse(operation["risk_state"]["consequences_enabled"])

    def test_atm_log_extraction_creates_single_atm_dump(self):
        profile = {
            "files": {"atm": [], "financial": []},
            "operations": [{
                "operation_id": "op_atm_dump",
                "operation_type": "atm_log_extraction",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "ATM Rynek"},
                "target_id": "map:52.1:21.2:ATM Rynek",
                "target_type": "atm",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "none",
                "resource_buffer": {"resource_types": [], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 15, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["atm"]), 1)
        self.assertEqual(len(profile["files"]["financial"]), 0)

        atm_file = profile["files"]["atm"][0]
        self.assertEqual(atm_file["file_category"], "atm")
        self.assertEqual(atm_file["directory"], "/data/atm")
        self.assertEqual(atm_file["preview_mode"], "table")
        self.assertEqual(atm_file["resource_types"], ["atm_dump"])
        self.assertEqual(atm_file["metadata"]["operation_id"], "op_atm_dump")
        self.assertEqual(atm_file["metadata"]["record_count"], 5)
        self.assertEqual(len(atm_file["records"]), 5)
        self.assertEqual(profile["operations"][0]["risk_state"]["level"], "high")

    def test_richer_atm_log_extraction_creates_financial_records_file(self):
        profile = {
            "files": {"atm": [], "financial": []},
            "operations": [{
                "operation_id": "op_atm_financial",
                "operation_type": "atm_log_extraction",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "ATM Bank"},
                "target_id": "map:52.1:21.2:ATM Bank",
                "target_type": "atm",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "none",
                "resource_buffer": {"resource_types": ["financial_records"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 15, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["atm"]), 1)
        self.assertEqual(len(profile["files"]["financial"]), 1)

        financial_file = profile["files"]["financial"][0]
        self.assertEqual(financial_file["file_category"], "financial")
        self.assertEqual(financial_file["directory"], "/data/financial")
        self.assertEqual(financial_file["preview_mode"], "table")
        self.assertEqual(financial_file["resource_types"], ["financial_records"])
        self.assertEqual(financial_file["metadata"]["record_count"], 8)
        self.assertEqual(len(financial_file["records"]), 8)

    def test_install_sniffer_creates_persistent_sniffer_operation(self):
        profile = {"operations": []}
        app = {
            "id": "persistent_sniffer_v1",
            "name": "PersistentSniffer",
            "operation_types": ["persistent_sniffer"],
            "resource_types": ["credentials"],
        }
        target = {
            "lat": 52.1,
            "lng": 21.2,
            "label": "Router",
            "source_type": "generated",
            "target_mode": "standard",
        }

        created = create_operations_for_app_action(profile, "neo", app, "install_sniffer", target)

        self.assertEqual(len(created), 1)
        operation = created[0]
        self.assertEqual(operation["operation_type"], "persistent_sniffer")
        self.assertEqual(operation["movement_model"], "implant_timer")
        self.assertEqual(operation["risk_state"]["level"], "medium")
        self.assertIn("long_operation_detected", operation["risk_state"]["events"])
        self.assertIn("sniffer_detected", operation["risk_state"]["events"])
        self.assertFalse(operation["risk_state"]["consequences_enabled"])

    def test_persistent_sniffer_creates_encrypted_credentials_without_duplicates(self):
        profile = {
            "files": {"credentials": [], "financial": [], "device": [], "system": []},
            "operations": [{
                "operation_id": "op_sniffer_credentials",
                "operation_type": "persistent_sniffer",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Router"},
                "target_id": "map:52.1:21.2:Router",
                "target_type": "router",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T13:00:00Z",
                "duration_seconds": 10800,
                "movement_model": "implant_timer",
                "resource_buffer": {"resource_types": ["credentials"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 13, 5, tzinfo=timezone.utc).timestamp(),
        )
        refreshed_again, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 13, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["credentials"]), 1)
        self.assertEqual(len(profile["files"]["financial"]), 0)

        credentials_file = profile["files"]["credentials"][0]
        self.assertEqual(credentials_file["file_category"], "credentials")
        self.assertEqual(credentials_file["directory"], "/data/credentials")
        self.assertEqual(credentials_file["preview_mode"], "encrypted_blob")
        self.assertEqual(credentials_file["resource_types"], ["credentials"])
        self.assertFalse(credentials_file["summary"]["plain_text_visible"])
        self.assertEqual(credentials_file["metadata"]["operation_id"], "op_sniffer_credentials")
        self.assertIn("sniffer_detected", profile["operations"][0]["risk_state"]["events"])

    def test_persistent_sniffer_rich_app_creates_multiple_resource_files(self):
        profile = {
            "files": {"credentials": [], "financial": [], "device": [], "system": []},
            "operations": [{
                "operation_id": "op_sniffer_rich",
                "operation_type": "persistent_sniffer",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "ATM Router"},
                "target_id": "map:52.1:21.2:ATM Router",
                "target_type": "router",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T13:00:00Z",
                "duration_seconds": 10800,
                "movement_model": "implant_timer",
                "resource_buffer": {
                    "resource_types": [
                        "financial_records",
                        "credentials",
                        "device_logs",
                        "internal_recon_state",
                    ],
                    "items": [],
                },
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 13, 5, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["financial"]), 1)
        self.assertEqual(len(profile["files"]["credentials"]), 1)
        self.assertEqual(len(profile["files"]["device"]), 1)
        self.assertEqual(len(profile["files"]["system"]), 1)

        self.assertEqual(profile["files"]["financial"][0]["resource_types"], ["financial_records"])
        self.assertEqual(profile["files"]["credentials"][0]["preview_mode"], "encrypted_blob")
        self.assertEqual(profile["files"]["device"][0]["resource_types"], ["device_logs"])
        self.assertEqual(profile["files"]["system"][0]["resource_types"], ["internal_recon_state"])
        self.assertEqual(profile["operations"][0]["risk_state"]["level"], "high")
        self.assertIn("high_value", profile["operations"][0]["risk_state"]["events"])

    def test_wifi_scanner_timeout_creates_network_file_without_duplicates(self):
        profile = {
            "files": {"network": []},
            "operations": [{
                "operation_id": "op_wifi_scan",
                "operation_type": "wifi_scanner",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Cafe"},
                "target_id": "map:52.1:21.2:Cafe",
                "target_type": "venue",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "none",
                "resource_buffer": {"resource_types": ["wifi_networks", "hotspot_database"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 15, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["network"]), 1)
        network_file = profile["files"]["network"][0]
        self.assertEqual(network_file["file_category"], "network")
        self.assertEqual(network_file["directory"], "/data/network")
        self.assertEqual(network_file["preview_mode"], "table")
        self.assertEqual(network_file["resource_types"], ["wifi_networks", "hotspot_database"])
        self.assertTrue(collect_ghost_exchange_files(profile))

    def test_audio_interference_timeout_creates_audio_transcript_without_duplicates(self):
        profile = {
            "files": {"audio": []},
            "operations": [{
                "operation_id": "op_audio_hack",
                "operation_type": "audio_interference",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Bar"},
                "target_id": "map:52.1:21.2:Bar",
                "target_type": "venue",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:20:00Z",
                "duration_seconds": 1200,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": ["audio_transcript"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 25, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 30, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["audio"]), 1)
        audio_file = profile["files"]["audio"][0]
        self.assertEqual(audio_file["file_category"], "audio")
        self.assertEqual(audio_file["directory"], "/data/audio")
        self.assertEqual(audio_file["preview_mode"], "transcript")
        self.assertEqual(audio_file["resource_types"], ["audio_transcript"])
        self.assertGreaterEqual(len(audio_file["transcript"]), 3)
        self.assertTrue(collect_ghost_exchange_files(profile))

    def test_vehicle_ecu_timeout_creates_vehicle_diagnostics_without_duplicates(self):
        profile = {
            "files": {"vehicle": []},
            "operations": [{
                "operation_id": "op_vehicle_ecu",
                "operation_type": "vehicle_ecu",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Auto"},
                "target_id": "map:52.1:21.2:Auto",
                "target_type": "vehicle",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:10:00Z",
                "duration_seconds": 600,
                "movement_model": "road_movement",
                "resource_buffer": {"resource_types": ["vehicle_diagnostics"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 15, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 20, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["vehicle"]), 1)
        vehicle_file = profile["files"]["vehicle"][0]
        self.assertEqual(vehicle_file["file_category"], "vehicle")
        self.assertEqual(vehicle_file["directory"], "/data/vehicle")
        self.assertEqual(vehicle_file["preview_mode"], "table")
        self.assertEqual(vehicle_file["resource_types"], ["vehicle_diagnostics"])
        self.assertTrue(vehicle_file["records"])
        self.assertTrue(collect_ghost_exchange_files(profile))

    def test_generic_trace_timeout_creates_location_history_without_duplicates(self):
        profile = {
            "files": {"gps": [], "system": []},
            "operations": [{
                "operation_id": "op_generic_trace",
                "operation_type": "generic_trace",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Cel"},
                "target_id": "map:52.1:21.2:Cel",
                "target_type": "poi",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T11:00:00Z",
                "duration_seconds": 3600,
                "movement_model": "local_walk",
                "resource_buffer": {"resource_types": ["location_history", "internal_recon_state"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 5, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 11, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["gps"]), 1)
        self.assertEqual(len(profile["files"]["system"]), 1)
        trace_file = profile["files"]["gps"][0]
        self.assertEqual(trace_file["file_category"], "gps")
        self.assertEqual(trace_file["directory"], "/data/gps")
        self.assertEqual(trace_file["preview_mode"], "table")
        self.assertEqual(trace_file["resource_types"], ["location_history"])
        self.assertTrue(trace_file["checkpoints"])
        listings = collect_ghost_exchange_files(profile)
        self.assertEqual(len([item for item in listings if item["file_category"] == "gps"]), 1)

    def test_camera_stream_timeout_creates_minimal_dump_without_prior_fragments(self):
        profile = {
            "files": {"camera": []},
            "operations": [{
                "operation_id": "op_camera_minimal",
                "operation_type": "camera_stream",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera"},
                "target_id": "map:52.1:21.2:Kamera",
                "target_type": "camera",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:02:00Z",
                "duration_seconds": 120,
                "movement_model": "static_active_timer",
                "resource_buffer": {"resource_types": ["camera_dump"], "items": []},
            }]
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 3, tzinfo=timezone.utc).timestamp(),
        )
        _, changed_again = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 4, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(refreshed[0]["status"], "timeout")
        self.assertEqual(len(profile["files"]["camera"]), 1)
        camera_file = profile["files"]["camera"][0]
        self.assertEqual(camera_file["file_category"], "camera")
        self.assertEqual(camera_file["resource_types"], ["camera_dump"])
        self.assertEqual(camera_file["metadata"]["duration_seconds"], 120)
        self.assertTrue(collect_ghost_exchange_files(profile))

    def test_file_inventory_normalizes_runtime_data_files_and_keeps_tools_compatible(self):
        profile = {
            "files": {
                "tools": ["TraceBike.sh"],
                "gps": [{
                    "name": "old_gps.log",
                    "operation_id": "op_old_gps",
                    "metadata": {
                        "target": {"label": "Old Vehicle"},
                        "ended_at": "2026-06-28T10:00:00Z",
                    },
                }],
            }
        }

        files = ensure_files_inventory(profile)

        for folder in [
            "tools",
            "gps",
            "device",
            "audio",
            "camera",
            "atm",
            "credentials",
            "financial",
            "personal",
            "network",
            "vehicle",
            "system",
            "market",
            "projects",
        ]:
            self.assertIn(folder, files)
            self.assertIsInstance(files[folder], list)

        self.assertEqual(files["tools"], ["TraceBike.sh"])
        gps_file = files["gps"][0]
        self.assertEqual(gps_file["id"], "file_gps_op_old_gps_old_gps_log")
        self.assertEqual(gps_file["file_category"], "gps")
        self.assertEqual(gps_file["directory"], "/data/gps")
        self.assertEqual(gps_file["preview_mode"], "table")
        self.assertEqual(gps_file["resource_types"], ["gps_logs", "location_history"])
        self.assertEqual(gps_file["source_operation_id"], "op_old_gps")
        self.assertEqual(gps_file["created_at"], "2026-06-28T10:00:00Z")
        self.assertEqual(gps_file["target_snapshot"]["label"], "Old Vehicle")
        self.assertTrue(gps_file["sellable"])
        self.assertEqual(gps_file["market_status"], "not_listed")
        self.assertIn("completeness_percent", gps_file)
        self.assertIn("completeness_tier", gps_file)
        self.assertIn("missing_fields", gps_file)
        self.assertIn("quality_score", gps_file)

    def test_file_inventory_sellable_matches_ghost_exchange_eligibility(self):
        profile = {
            "files": {
                "gps": [{
                    "name": "trace_client.log",
                    "operation_id": "op_trace_client",
                    "resource_types": ["location_history"],
                }],
                "system": [{
                    "name": "recon_state.sys",
                    "operation_id": "op_recon",
                    "resource_types": ["internal_recon_state"],
                }],
            }
        }

        files = ensure_files_inventory(profile)
        listings = collect_ghost_exchange_files(profile)

        self.assertTrue(files["gps"][0]["sellable"])
        self.assertFalse(files["system"][0]["sellable"])
        self.assertEqual([item["id"] for item in listings], [files["gps"][0]["id"]])

    def test_market_sector_maps_current_file_categories(self):
        cases = {
            "gps": "gps",
            "device": "device",
            "personal": "personal",
            "camera": "camera",
            "atm": "atm",
            "financial": "financial",
            "credentials": "credentials",
            "network": "network",
            "audio": "audio",
            "vehicle": "vehicle",
        }
        for file_category, expected_sector in cases.items():
            with self.subTest(file_category=file_category):
                self.assertEqual(
                    market_sector_for_file({
                        "file_category": file_category,
                        "resource_types": ["location_history"],
                    }),
                    expected_sector,
                )

        self.assertEqual(
            market_sector_for_file({
                "file_category": "unknown",
                "resource_types": ["camera_dump"],
            }),
            "camera",
        )

    def test_file_market_status_normalizes_legacy_statuses(self):
        base_file = {
            "file_category": "gps",
            "resource_types": ["location_history"],
            "sellable": True,
        }

        self.assertEqual(normalize_file_market_status({**base_file, "market_status": "not_listed"}), "queued_for_market")
        self.assertEqual(normalize_file_market_status({**base_file, "market_status": "ready_to_list"}), "queued_for_market")
        self.assertEqual(normalize_file_market_status({**base_file, "market_status": "listed_preview"}), "queued_for_market")
        self.assertEqual(normalize_file_market_status({**base_file, "market_status": "listed"}), "listed")
        self.assertEqual(normalize_file_market_status({**base_file, "market_status": "sold"}), "sold")
        self.assertEqual(normalize_file_market_status({**base_file, "market_status": "archived"}), "archived")
        self.assertEqual(
            normalize_file_market_status({
                "file_category": "system",
                "resource_types": ["internal_recon_state"],
                "sellable": False,
                "market_status": "not_listed",
            }),
            "created",
        )

    def test_sellable_still_defines_market_eligibility(self):
        sellable_file = {
            "file_category": "gps",
            "resource_types": ["location_history"],
            "sellable": True,
            "market_status": "not_listed",
        }
        blocked_file = {
            "file_category": "gps",
            "resource_types": ["location_history"],
            "sellable": False,
            "market_status": "not_listed",
        }
        sold_file = {
            "file_category": "gps",
            "resource_types": ["location_history"],
            "sellable": True,
            "market_status": "sold",
        }

        self.assertTrue(is_market_eligible_file(sellable_file))
        self.assertFalse(is_market_eligible_file(blocked_file))
        self.assertFalse(is_market_eligible_file(sold_file))

    def test_storage_gate_helpers_report_capacity_without_writing_file(self):
        profile = {
            "storage_capacity": 64,
            "storage_used": 60,
            "storage_unit": "MB",
            "files": {"gps": []},
        }
        small_file = {
            "name": "small_trace.log",
            "file_category": "gps",
            "resource_types": ["location_history"],
            "file_size": 4,
        }
        large_file = {
            "name": "large_trace.log",
            "file_category": "gps",
            "resource_types": ["location_history"],
            "file_size": 8,
        }
        operation = {"operation_id": "op_storage_gate", "operation_type": "generic_trace"}

        self.assertTrue(can_store_runtime_file(profile, small_file))
        self.assertFalse(can_store_runtime_file(profile, large_file))
        result = build_storage_full_result(profile, operation, large_file)
        self.assertEqual(result["status"], "storage_full")
        self.assertEqual(result["result"], "dropped_no_space")
        self.assertEqual(result["storage_required"], 68)
        self.assertEqual(profile["files"]["gps"], [])

    def test_append_runtime_file_if_space_blocks_queue_and_adds_message_once(self):
        profile = {
            "storage_capacity": 64,
            "storage_used": 63,
            "storage_unit": "MB",
            "files": {"gps": []},
            "system_messages": [],
        }
        operation = {"operation_id": "op_storage_block", "operation_type": "generic_trace", "resource_buffer": {}}
        file_entry = {
            "name": "blocked_trace.log",
            "file_category": "gps",
            "directory": "/data/gps",
            "resource_types": ["location_history"],
            "file_size": 4,
            "market_status": "not_listed",
        }

        first = append_runtime_file_if_space(profile, operation, "gps", file_entry)
        second = append_runtime_file_if_space(profile, operation, "gps", file_entry)
        queued_count = queue_market_eligible_files(profile)

        self.assertFalse(first["stored"])
        self.assertTrue(first["changed"])
        self.assertFalse(second["stored"])
        self.assertFalse(second["changed"])
        self.assertEqual(profile["files"]["gps"], [])
        self.assertEqual(queued_count, 0)
        self.assertEqual(len(profile["system_messages"]), 1)
        self.assertEqual(profile["system_messages"][0]["text"], "Brak miejsca na zapis danych.")

    def test_vehicle_finalizer_drops_file_when_storage_is_full(self):
        profile = {
            "storage_capacity": 64,
            "storage_used": 64,
            "storage_unit": "MB",
            "files": {"gps": []},
            "system_messages": [],
        }
        operation = {
            "operation_id": "op_vehicle_no_space",
            "operation_type": "vehicle_tracking",
            "status": "completed",
            "target": {"name": "Bike"},
            "resource_buffer": {},
        }

        changed = finalize_vehicle_tracking_file(profile, operation)
        changed_again = finalize_vehicle_tracking_file(profile, operation)

        self.assertTrue(changed)
        self.assertFalse(changed_again)
        self.assertEqual(profile["files"]["gps"], [])
        self.assertEqual(queue_market_eligible_files(profile), 0)
        self.assertEqual(len(profile["system_messages"]), 1)
        self.assertTrue(operation["resource_buffer"]["storage_full"])

    def test_ghost_exchange_payload_includes_sprint35_market_read_model(self):
        profile = {
            "files": {
                "camera": [{
                    "id": "camera_market_read_model",
                    "name": "camera_market_read_model.cam",
                    "file_category": "camera",
                    "directory": "/data/camera",
                    "resource_types": ["camera_dump"],
                    "file_size": 14,
                    "market_status": "not_listed",
                }]
            }
        }

        queue_market_eligible_files(profile)
        listings = collect_ghost_exchange_files(profile)
        self.assertEqual(len(listings), 1)
        listing = listings[0]
        self.assertEqual(listing["market_sector"], "camera")
        self.assertEqual(listing["market_volume_mb"], 14)
        self.assertEqual(listing["market_status"], "queued_for_market")
        self.assertEqual(listing["normalized_market_status"], "queued_for_market")
        self.assertGreater(listing["price_preview"], 0)

    def test_queue_market_eligible_files_sets_status_sector_and_queued_at_once(self):
        profile = {
            "files": {
                "gps": [{
                    "id": "gps_queue_candidate",
                    "name": "gps_queue_candidate.log",
                    "file_category": "gps",
                    "resource_types": ["location_history"],
                    "file_size": 4,
                    "market_status": "not_listed",
                }]
            }
        }

        changed = queue_market_eligible_files(profile)
        queued_file = profile["files"]["gps"][0]
        first_queued_at = queued_file.get("queued_at")

        self.assertEqual(changed, 1)
        self.assertEqual(queued_file["market_status"], "queued_for_market")
        self.assertEqual(queued_file["market_sector"], "gps")
        self.assertTrue(first_queued_at)

        changed_again = queue_market_eligible_files(profile)
        self.assertEqual(changed_again, 0)
        self.assertEqual(profile["files"]["gps"][0]["queued_at"], first_queued_at)

    def test_queue_market_eligible_files_skips_unsellable_and_sold_files(self):
        profile = {
            "files": {
                "system": [{
                    "id": "recon_state",
                    "name": "recon_state.sys",
                    "file_category": "system",
                    "resource_types": ["internal_recon_state"],
                    "sellable": False,
                    "market_status": "not_listed",
                }],
                "gps": [{
                    "id": "sold_gps",
                    "name": "sold_gps.log",
                    "file_category": "gps",
                    "resource_types": ["location_history"],
                    "sellable": True,
                    "market_status": "sold",
                }],
            }
        }

        changed = queue_market_eligible_files(profile)

        self.assertEqual(changed, 0)
        self.assertEqual(profile["files"]["system"][0]["market_status"], "not_listed")
        self.assertNotIn("queued_at", profile["files"]["system"][0])
        self.assertEqual(profile["files"]["gps"][0]["market_status"], "sold")
        self.assertNotIn("queued_at", profile["files"]["gps"][0])

    def test_ghost_exchange_sector_payload_reports_pending_queue_read_model(self):
        profile = {
            "files": {
                "camera": [{
                    "id": "camera_pending",
                    "name": "camera_pending.cam",
                    "file_category": "camera",
                    "resource_types": ["camera_dump"],
                    "file_size": 14,
                    "metadata": {"record_count": 2},
                    "market_status": "not_listed",
                }]
            }
        }
        queue_market_eligible_files(profile)

        sectors = build_ghost_exchange_sector_payload(profile)
        camera_sector = next(item for item in sectors if item["sector"] == "camera")

        self.assertEqual(camera_sector["pending_files"], 1)
        self.assertEqual(camera_sector["pending_mb"], 14)
        self.assertEqual(camera_sector["threshold_mb"], 50)
        self.assertEqual(camera_sector["missing_mb"], 36)
        self.assertEqual(camera_sector["missing_records"], 0)
        self.assertGreater(camera_sector["progress_percent"], 0)
        self.assertIn("min", camera_sector["estimated_sale_time"])

    def test_ghost_exchange_dashboard_payload_includes_summary_recent_and_history(self):
        profile = {
            "files": {
                "camera": [{
                    "id": "camera_dashboard_pending",
                    "name": "camera_dashboard_pending.cam",
                    "file_category": "camera",
                    "resource_types": ["camera_dump"],
                    "file_size": 14,
                    "market_status": "queued_for_market",
                    "market_sector": "camera",
                    "queued_at": "2026-07-03T09:00:00Z",
                }],
                "market": [],
            },
            "market_history": [{
                "id": "batch_camera_dashboard",
                "batch_id": "batch_camera_dashboard",
                "file_name": "sold_batch_camera.pkg",
                "market_sector": "camera",
                "market_category": "surveillance",
                "price": 120,
                "currency": "HC",
                "sold_at": "2026-07-03T10:00:00Z",
                "status": "sold",
                "file_count": 3,
                "volume_mb": 42,
            }],
        }

        dashboard = build_ghost_exchange_dashboard_payload(
            profile,
            now=datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc),
        )
        camera_sector = next(item for item in dashboard["sectors"] if item["sector"] == "camera")

        self.assertIn("summary", dashboard)
        self.assertIn("sectors", dashboard)
        self.assertIn("recent_transactions", dashboard)
        self.assertIn("history_7d", dashboard)
        self.assertEqual(dashboard["summary"]["pending_files"], 1)
        self.assertEqual(dashboard["summary"]["hc_today"], 120)
        self.assertEqual(camera_sector["progress_percent"], 28)
        self.assertEqual(camera_sector["missing_mb"], 36)
        self.assertIn("estimated_sale_time", camera_sector)
        self.assertEqual(camera_sector["sold_today_files"], 3)
        self.assertEqual(camera_sector["hc_today"], 120)
        self.assertEqual(camera_sector["hc_total"], 120)
        self.assertEqual(camera_sector["average_price"], 120)
        self.assertEqual(dashboard["recent_transactions"][0]["batch_id"], "batch_camera_dashboard")
        self.assertEqual(len(dashboard["history_7d"]), 7)

    def test_api_ghost_exchange_returns_dashboard_payload(self):
        profile = {
            "username": "tester",
            "hackcoins": 500,
            "files": {
                "camera": [{
                    "id": "camera_api_pending",
                    "name": "camera_api_pending.cam",
                    "file_category": "camera",
                    "resource_types": ["camera_dump"],
                    "file_size": 14,
                    "market_status": "queued_for_market",
                    "market_sector": "camera",
                    "queued_at": "2026-07-03T09:00:00Z",
                }],
                "market": [],
            },
            "market_history": [{
                "id": "batch_api_camera",
                "batch_id": "batch_api_camera",
                "file_name": "sold_batch_api_camera.pkg",
                "market_sector": "camera",
                "market_category": "surveillance",
                "price": 77,
                "currency": "HC",
                "sold_at": "2026-07-03T10:00:00Z",
                "status": "sold",
                "file_count": 2,
                "volume_mb": 28,
            }],
            "system_messages": [],
        }
        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "tester"
        with canonical_wallet_test_runtime({"tester": profile["hackcoins"]}), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", return_value=profile), \
                patch.object(run, "UserProfileManager", side_effect=AssertionError("dashboard read should not write")):
            response = client.get("/api/ghost-exchange")

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["balance"], 500)
        self.assertIn("summary", data)
        self.assertIn("sectors", data)
        self.assertIn("recent_transactions", data)
        self.assertIn("history_7d", data)
        self.assertEqual(len(data["history_7d"]), 7)
        camera_sector = next(item for item in data["sectors"] if item["sector"] == "camera")
        self.assertIn("progress_percent", camera_sector)
        self.assertTrue(camera_sector["missing_mb"] >= 0 or camera_sector["missing_records"] >= 0)
        self.assertIn("estimated_sale_time", camera_sector)
        self.assertEqual(data["recent_transactions"][0]["batch_id"], "batch_api_camera")

    def test_ghost_exchange_frontend_renders_dashboard_without_main_sell_button(self):
        with open(os.path.join(os.getcwd(), "static", "js", "terminal.js"), encoding="utf-8") as handle:
            terminal_js = handle.read()
        render_start = terminal_js.index("const renderExchange = () => {")
        render_end = terminal_js.index("async function loadCatalog()", render_start)
        render_exchange_source = terminal_js[render_start:render_end]

        self.assertIn("gx-dashboard", render_exchange_source)
        self.assertIn("gx-sector-grid", render_exchange_source)
        self.assertIn("gx-summary-grid", render_exchange_source)
        self.assertIn("gx-main-row", render_exchange_source)
        self.assertIn("gx-transactions-panel", render_exchange_source)
        self.assertIn("gx-chart-panel", render_exchange_source)
        self.assertNotIn("ghost-exchange-sell-btn", render_exchange_source)
        self.assertNotIn("Sprzedaj</button>", render_exchange_source)

    def test_ghost_exchange_chart_css_supports_mobile_and_narrow_layout(self):
        with open(os.path.join(os.getcwd(), "static", "css", "ghost_exchange_charts.css"), encoding="utf-8") as handle:
            css = handle.read()

        self.assertIn("@media (max-width: 900px)", css)
        self.assertIn("(max-height: 700px)", css)
        self.assertIn(".browser-window.browser-narrow .gx-sector-grid", css)
        self.assertIn("@container (max-width: 720px)", css)
        self.assertIn("grid-template-columns: minmax(0, 1fr)", css)

    def test_queue_market_eligible_files_preserves_listed_batch(self):
        profile = {
            "files": {
                "camera": [{
                    "id": "camera_listed",
                    "name": "camera_listed.cam",
                    "file_category": "camera",
                    "resource_types": ["camera_dump"],
                    "file_size": 50,
                    "market_status": "listed",
                    "listed_at": "2026-07-03T10:00:00Z",
                    "batch_id": "batch_camera_listed",
                    "market_sector": "camera",
                    "sellable": True,
                }]
            }
        }

        changed = queue_market_eligible_files(profile)
        listed_file = profile["files"]["camera"][0]

        self.assertEqual(changed, 0)
        self.assertEqual(listed_file["market_status"], "listed")
        self.assertEqual(listed_file["listed_at"], "2026-07-03T10:00:00Z")
        self.assertEqual(listed_file["batch_id"], "batch_camera_listed")

    def test_market_runtime_does_not_sell_before_sector_threshold(self):
        profile = {
            "hackcoins": 100,
            "files": {
                "camera": [{
                    "id": "camera_small_1",
                    "name": "camera_small_1.cam",
                    "file_category": "camera",
                    "resource_types": ["camera_dump"],
                    "file_size": 20,
                    "market_status": "not_listed",
                }]
            },
            "market_history": [],
            "system_messages": [],
        }
        now = datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)

        result = refresh_market_runtime("neo", profile, now=now, payout_callback=canonical_market_test_payout(profile))

        self.assertTrue(result["changed"])
        self.assertEqual(result["queued"], 1)
        self.assertEqual(result["listed"], 0)
        self.assertEqual(result["settled"], 0)
        self.assertEqual(profile["hackcoins"], 100)
        self.assertEqual(profile["market_history"], [])
        self.assertEqual(profile["files"].get("market", []), [])
        self.assertEqual(profile["files"]["camera"][0]["market_status"], "queued_for_market")

    def test_market_runtime_lists_batch_and_waits_for_dwell_time(self):
        profile = {
            "hackcoins": 100,
            "files": {
                "camera": [
                    {
                        "id": f"camera_ready_{index}",
                        "name": f"camera_ready_{index}.cam",
                        "file_category": "camera",
                        "resource_types": ["camera_dump"],
                        "file_size": 14,
                        "market_status": "not_listed",
                    }
                    for index in range(4)
                ]
            },
            "market_history": [],
            "system_messages": [],
        }
        now = datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)

        listed_result = refresh_market_runtime("neo", profile, now=now, payout_callback=canonical_market_test_payout(profile))
        self.assertEqual(listed_result["queued"], 4)
        self.assertEqual(listed_result["listed"], 4, profile["files"]["camera"])
        self.assertEqual(listed_result["settled"], 0)
        self.assertIn("listed_at", profile["files"]["camera"][0], profile["files"]["camera"])
        listed_at = profile["files"]["camera"][0]["listed_at"]
        batch_id = profile["files"]["camera"][0]["batch_id"]
        waiting_result = refresh_market_runtime("neo", profile, now=now + timedelta(minutes=1), payout_callback=canonical_market_test_payout(profile))

        self.assertEqual(waiting_result["settled"], 0)
        self.assertEqual(profile["hackcoins"], 100)
        self.assertEqual(profile["market_history"], [])
        self.assertEqual(profile["files"].get("market", []), [])
        self.assertTrue(all(item["market_status"] == "listed" for item in profile["files"]["camera"]))
        self.assertTrue(all(item["listed_at"] == listed_at for item in profile["files"]["camera"]))
        self.assertTrue(all(item["batch_id"] == batch_id for item in profile["files"]["camera"]))

        sectors = build_ghost_exchange_sector_payload(profile)
        camera_sector = next(item for item in sectors if item["sector"] == "camera")
        self.assertEqual(camera_sector["status"], "trading")
        self.assertEqual(camera_sector["listed_at"], listed_at)
        self.assertEqual(camera_sector["batch_id"], batch_id)

    def test_market_runtime_settles_batch_after_dwell_once(self):
        profile = {
            "hackcoins": 100,
            "storage_capacity": 256,
            "storage_used": 56,
            "storage_unit": "MB",
            "files": {
                "camera": [
                    {
                        "id": f"camera_sell_{index}",
                        "name": f"camera_sell_{index}.cam",
                        "file_category": "camera",
                        "resource_types": ["camera_dump"],
                        "file_size": 14,
                        "market_status": "not_listed",
                    }
                    for index in range(4)
                ],
                "market": [],
            },
            "market_history": [],
            "system_messages": [],
        }
        now = datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)

        refresh_market_runtime("neo", profile, now=now, payout_callback=canonical_market_test_payout(profile))
        with patch.object(run.mail_store, "add_direct_notification") as mail_mock:
            settled_result = refresh_market_runtime("neo", profile, now=now + timedelta(minutes=6), payout_callback=canonical_market_test_payout(profile))
            hc_after_sale = profile["hackcoins"]
            second_result = refresh_market_runtime("neo", profile, now=now + timedelta(minutes=7), payout_callback=canonical_market_test_payout(profile))

        self.assertEqual(settled_result["settled"], 1)
        self.assertEqual(second_result["settled"], 0)
        self.assertGreater(hc_after_sale, 100)
        self.assertEqual(profile["hackcoins"], hc_after_sale)
        self.assertEqual(len(profile["market_history"]), 1)
        self.assertEqual(len(profile["files"]["market"]), 1)
        self.assertEqual(profile["files"]["camera"], [])
        self.assertLess(profile["storage_used"], 56)
        self.assertEqual(len(profile["system_messages"]), 1)
        self.assertEqual(profile["market_history"][0]["batch_id"], profile["files"]["market"][0]["batch_id"])
        mail_mock.assert_called_once()

    def test_api_ghost_exchange_settles_listed_batch_once(self):
        listed_at = "2026-07-03T10:00:00Z"
        entries = [
            {
                "id": f"camera_api_sell_{index}",
                "name": f"camera_api_sell_{index}.cam",
                "file_category": "camera",
                "resource_types": ["camera_dump"],
                "file_size": 14,
                "market_status": "listed",
                "listed_at": listed_at,
                "market_sector": "camera",
                "sellable": True,
            }
            for index in range(4)
        ]
        batch_id = run.market_batch_id("neo", "camera", entries)
        for entry in entries:
            entry["batch_id"] = batch_id
        profile = {
            "username": "neo",
            "hackcoins": 100,
            "storage_capacity": 256,
            "storage_used": 56,
            "storage_unit": "MB",
            "files": {"camera": entries, "market": []},
            "market_history": [],
            "system_messages": [],
        }

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"]}), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=lambda username, current: current), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "add_cyberner_direct_notification") as notify_mock, \
                patch.object(run, "market_runtime_now", return_value=datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc)):
            first_response = client.get("/api/ghost-exchange")
            first_data = first_response.get_json()
            hc_after_sale = profile["hackcoins"]
            second_response = client.get("/api/ghost-exchange")
            second_data = second_response.get_json()

        self.assertEqual(first_response.status_code, 200)
        self.assertTrue(first_data["success"])
        self.assertEqual(first_data["market_runtime"]["settled"], 1)
        self.assertGreater(hc_after_sale, 100)
        self.assertEqual(profile["hackcoins"], hc_after_sale)
        self.assertEqual(len(profile["market_history"]), 1)
        self.assertEqual(len(profile["files"]["market"]), 1)
        self.assertEqual(profile["files"]["camera"], [])
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_data["market_runtime"]["settled"], 0)
        self.assertEqual(profile["hackcoins"], hc_after_sale)
        self.assertEqual(len(profile["market_history"]), 1)
        notify_mock.assert_called_once()

    def test_market_runtime_cleans_already_sold_orphan_files_without_hc(self):
        entries = [
            {
                "id": f"gps_orphan_sold_{index}",
                "name": f"gps_orphan_sold_{index}.gps",
                "file_category": "gps",
                "resource_types": ["gps_track"],
                "file_size": 10,
                "market_status": "queued_for_market",
                "market_sector": "gps",
                "sellable": True,
            }
            for index in range(3)
        ]
        batch_id = run.market_batch_id("neo", "gps", entries)
        profile = {
            "username": "neo",
            "hackcoins": 500,
            "storage_capacity": 256,
            "storage_used": 30,
            "storage_unit": "MB",
            "files": {"gps": entries, "market": []},
            "market_history": [{
                "id": batch_id,
                "batch_id": batch_id,
                "market_sector": "gps",
                "price": 777,
                "status": "sold",
                "file_ids": [item["id"] for item in entries],
            }],
            "system_messages": [],
        }

        result = refresh_market_runtime("neo", profile, now=datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc), payout_callback=canonical_market_test_payout(profile))

        self.assertTrue(result["changed"])
        self.assertEqual(result["settled"], 0)
        self.assertEqual(profile["hackcoins"], 500)
        self.assertEqual(profile["files"]["gps"], [])
        self.assertEqual(len(profile["market_history"]), 1)
        self.assertEqual(profile["files"].get("market", []), [])
        self.assertEqual(profile["storage_used"], 0)

    def test_market_runtime_sells_listed_network_batch_without_queued_reset(self):
        listed_entries = [
            {
                "id": f"network_listed_{index}",
                "name": f"network_listed_{index}.net",
                "file_category": "network",
                "resource_types": ["wifi_networks"],
                "file_size": 10,
                "market_status": "listed",
                "listed_at": "2026-07-03T10:00:00Z",
                "market_sector": "network",
                "sellable": True,
            }
            for index in range(3)
        ]
        listed_batch_id = run.market_batch_id("neo", "network", listed_entries)
        for entry in listed_entries:
            entry["batch_id"] = listed_batch_id
        queued_entries = [
            {
                "id": f"network_queued_{index}",
                "name": f"network_queued_{index}.net",
                "file_category": "network",
                "resource_types": ["wifi_networks"],
                "file_size": 8,
                "market_status": "queued_for_market",
                "market_sector": "network",
                "sellable": True,
            }
            for index in range(4)
        ]
        profile = {
            "username": "neo",
            "hackcoins": 100,
            "storage_capacity": 256,
            "storage_used": 62,
            "storage_unit": "MB",
            "files": {"network": listed_entries + queued_entries, "market": []},
            "market_history": [],
            "system_messages": [],
        }

        with patch.object(run.mail_store, "add_direct_notification") as mail_mock:
            result = refresh_market_runtime("neo", profile, now=datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc), payout_callback=canonical_market_test_payout(profile))

        remaining_network_ids = {item["id"] for item in profile["files"]["network"]}
        self.assertEqual(result["settled"], 1)
        self.assertEqual(profile["market_history"][0]["batch_id"], listed_batch_id)
        self.assertFalse(any(item["id"] in remaining_network_ids for item in listed_entries))
        self.assertTrue(all(item["id"] in remaining_network_ids for item in queued_entries))
        self.assertTrue(all(item["market_status"] == "listed" for item in profile["files"]["network"]))
        self.assertTrue(all(item["batch_id"] != listed_batch_id for item in profile["files"]["network"]))
        self.assertGreater(profile["hackcoins"], 100)
        mail_mock.assert_called_once()

    def test_market_runtime_sells_legacy_listed_network_batch_without_batch_id(self):
        entries = [
            {
                "id": f"network_legacy_listed_{index}",
                "name": f"network_legacy_listed_{index}.net",
                "file_category": "network",
                "resource_types": ["wifi_networks"],
                "file_size": 11,
                "market_status": "listed",
                "created_at": "2026-07-03T10:00:00Z",
                "market_sector": "network",
                "sellable": True,
            }
            for index in range(3)
        ]
        profile = {
            "username": "neo",
            "hackcoins": 100,
            "storage_capacity": 256,
            "storage_used": 33,
            "storage_unit": "MB",
            "files": {"network": entries, "market": []},
            "market_history": [],
            "system_messages": [],
        }

        with patch.object(run.mail_store, "add_direct_notification") as mail_mock:
            result = refresh_market_runtime("neo", profile, now=datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc), payout_callback=canonical_market_test_payout(profile))

        self.assertEqual(result["settled"], 1)
        self.assertEqual(profile["files"]["network"], [])
        self.assertEqual(len(profile["market_history"]), 1)
        self.assertEqual(profile["market_history"][0]["market_sector"], "network")
        self.assertGreater(profile["hackcoins"], 100)
        mail_mock.assert_called_once()

    def test_market_runtime_lists_and_sells_not_listed_network_batch_near_storage_limit(self):
        entries = [
            {
                "id": f"network_pending_{index}",
                "name": f"wifi_pending_{index}.net",
                "file_category": "network",
                "directory": "/data/network",
                "resource_types": ["wifi_networks"],
                "file_size": 13,
                "market_status": "not_listed",
                "sellable": True,
                "metadata": {
                    "record_count": 8,
                    "network_count": 8,
                    "quality_score": 90,
                    "completeness_percent": 86,
                },
            }
            for index in range(3)
        ]
        profile = {
            "username": "neo",
            "hackcoins": 45,
            "storage_capacity": 512,
            "storage_used": 503,
            "storage_unit": "MB",
            "files": {"network": entries, "market": []},
            "market_history": [],
            "system_messages": [],
        }
        now = datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)

        listed = refresh_market_runtime("neo", profile, now=now, payout_callback=canonical_market_test_payout(profile))
        self.assertEqual(listed["settled"], 0)
        self.assertGreaterEqual(listed["listed"], 3)
        self.assertTrue(all(item["market_status"] == "listed" for item in profile["files"]["network"]))
        self.assertTrue(all(item.get("batch_id") for item in profile["files"]["network"]))
        self.assertTrue(all(item.get("listed_at") for item in profile["files"]["network"]))

        with patch.object(run.mail_store, "add_direct_notification") as mail_mock:
            settled = refresh_market_runtime("neo", profile, now=now + timedelta(minutes=6), payout_callback=canonical_market_test_payout(profile))

        self.assertEqual(settled["settled"], 1)
        self.assertEqual(profile["files"]["network"], [])
        self.assertEqual(len(profile["market_history"]), 1)
        self.assertEqual(profile["market_history"][0]["market_sector"], "network")
        self.assertGreater(profile["hackcoins"], 45)
        self.assertLess(profile["storage_used"], 503)
        mail_mock.assert_called_once()

    def test_api_ghost_exchange_persists_network_listing_then_sells_after_dwell(self):
        entries = [
            {
                "id": f"network_api_pending_{index}",
                "name": f"wifi_api_pending_{index}.net",
                "file_category": "network",
                "directory": "/data/network",
                "resource_types": ["wifi_networks"],
                "file_size": 13,
                "market_status": "not_listed",
                "sellable": True,
                "metadata": {
                    "record_count": 8,
                    "network_count": 8,
                    "quality_score": 90,
                    "completeness_percent": 86,
                },
            }
            for index in range(3)
        ]
        profile = {
            "username": "neo",
            "hackcoins": 45,
            "storage_capacity": 512,
            "storage_used": 503,
            "storage_unit": "MB",
            "files": {"network": entries, "market": []},
            "market_history": [],
            "system_messages": [],
        }

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"]}), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=lambda username, current: current), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "add_cyberner_direct_notification") as notify_mock, \
                patch.object(run, "market_runtime_now", return_value=datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)):
            first_response = client.get("/api/ghost-exchange")
            first_data = first_response.get_json()

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_data["market_runtime"]["queued"], 3)
        self.assertEqual(first_data["market_runtime"]["listed"], 3)
        self.assertEqual(first_data["market_runtime"]["settled"], 0)
        self.assertTrue(all(item["market_status"] == "listed" for item in profile["files"]["network"]))

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"]}), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=lambda username, current: current), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "add_cyberner_direct_notification") as notify_mock, \
                patch.object(run, "market_runtime_now", return_value=datetime(2026, 7, 3, 10, 6, tzinfo=timezone.utc)):
            second_response = client.get("/api/ghost-exchange")
            second_data = second_response.get_json()

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_data["market_runtime"]["settled"], 1)
        self.assertEqual(profile["files"]["network"], [])
        self.assertEqual(len(profile["market_history"]), 1)
        self.assertEqual(profile["market_history"][0]["market_sector"], "network")
        self.assertGreater(profile["hackcoins"], 45)
        self.assertLess(profile["storage_used"], 503)
        notify_mock.assert_called_once()

    def test_api_ghost_exchange_counts_raw_not_listed_sellable_files_as_pending(self):
        entries = [
            {
                "id": f"gps_raw_pending_{index}",
                "name": f"trace_raw_pending_{index}.log",
                "file_category": "gps",
                "directory": "/data/gps",
                "resource_types": ["location_history"],
                "file_size": 11,
                "market_status": "not_listed",
                "sellable": True,
                "metadata": {
                    "record_count": 4,
                    "checkpoint_count": 4,
                    "quality_score": 86,
                    "completeness_percent": 94,
                },
            }
            for index in range(2)
        ]
        profile = {
            "username": "neo",
            "hackcoins": 45,
            "storage_capacity": 512,
            "storage_used": 22,
            "storage_unit": "MB",
            "files": {"gps": entries, "market": []},
            "market_history": [],
            "system_messages": [],
        }

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"]}), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=lambda username, current: current), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "market_runtime_now", return_value=datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)):
            response = client.get("/api/ghost-exchange")
            data = response.get_json()

        self.assertEqual(response.status_code, 200)
        gps_sector = next(item for item in data["sectors"] if item["sector"] == "gps")
        self.assertEqual(gps_sector["pending_files"], 2)
        self.assertEqual(gps_sector["pending_mb"], 22)
        self.assertEqual(gps_sector["missing_mb"], 3)
        self.assertEqual(gps_sector["status"], "collecting")
        self.assertEqual(data["market_runtime"]["settled"], 0)

    def test_api_ghost_exchange_counts_raw_pending_files_when_storage_is_full(self):
        profile = {
            "username": "neo",
            "hackcoins": 45,
            "storage_capacity": 768,
            "storage_used": 768,
            "storage_unit": "MB",
            "files": {
                "gps": [{
                    "id": "gps_full_pending",
                    "name": "trace_full_pending.log",
                    "file_category": "gps",
                    "directory": "/data/gps",
                    "resource_types": ["location_history"],
                    "file_size": 11,
                    "market_status": "not_listed",
                    "sellable": True,
                    "metadata": {"record_count": 4, "checkpoint_count": 4},
                }],
                "device": [{
                    "id": "device_full_pending",
                    "name": "device_full_pending.log",
                    "file_category": "device",
                    "directory": "/data/device",
                    "resource_types": ["device_logs"],
                    "file_size": 13,
                    "market_status": "not_listed",
                    "sellable": True,
                    "metadata": {"record_count": 4, "systems_count": 4},
                }],
                "camera": [{
                    "id": "camera_full_pending",
                    "name": "camera_full_pending.cam",
                    "file_category": "camera",
                    "directory": "/data/camera",
                    "resource_types": ["camera_dump"],
                    "file_size": 14,
                    "market_status": "not_listed",
                    "sellable": True,
                    "metadata": {"record_count": 4},
                }],
                "market": [],
            },
            "market_history": [],
            "system_messages": [],
        }

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"]}), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=lambda username, current: current), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "market_runtime_now", return_value=datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)):
            response = client.get("/api/ghost-exchange")
            data = response.get_json()

        self.assertEqual(response.status_code, 200)
        sectors = {item["sector"]: item for item in data["sectors"]}
        self.assertEqual(sectors["gps"]["pending_files"], 1)
        self.assertEqual(sectors["gps"]["pending_mb"], 11)
        self.assertEqual(sectors["device"]["pending_files"], 1)
        self.assertEqual(sectors["device"]["pending_mb"], 13)
        self.assertEqual(sectors["camera"]["pending_files"], 1)
        self.assertEqual(sectors["camera"]["pending_mb"], 14)
        self.assertEqual(data["market_runtime"]["settled"], 0)

    def test_api_ghost_exchange_cleans_already_sold_orphan_files_without_double_sale(self):
        entries = [
            {
                "id": f"camera_orphan_{index}",
                "name": f"camera_orphan_{index}.cam",
                "file_category": "camera",
                "directory": "/data/camera",
                "resource_types": ["camera_dump"],
                "file_size": 14,
                "market_status": "not_listed",
                "created_at": "2026-07-03T09:00:00Z",
                "sellable": True,
                "metadata": {"record_count": 1},
            }
            for index in range(4)
        ]
        batch_id = run.market_batch_id("neo", "camera", entries)
        profile = {
            "username": "neo",
            "hackcoins": 500,
            "storage_capacity": 768,
            "storage_used": 56,
            "storage_unit": "MB",
            "files": {"camera": entries, "market": []},
            "market_history": [{
                "id": batch_id,
                "batch_id": batch_id,
                "market_sector": "camera",
                "status": "sold",
                "file_ids": [item["id"] for item in entries],
                "file_count": len(entries),
                "volume_mb": 56,
                "price": 123,
                "sold_at": "2026-07-03T10:00:00Z",
            }],
            "system_messages": [],
        }

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"]}), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=lambda username, current: current), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "market_runtime_now", return_value=datetime(2026, 7, 3, 11, 0, tzinfo=timezone.utc)):
            response = client.get("/api/ghost-exchange")
            data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["market_runtime"]["settled"], 0)
        self.assertEqual(profile["hackcoins"], 500)
        self.assertEqual(profile["files"]["camera"], [])
        self.assertEqual(profile["storage_used"], 0)
        camera_sector = next(item for item in data["sectors"] if item["sector"] == "camera")
        self.assertEqual(camera_sector["pending_files"], 0)
        self.assertEqual(camera_sector["pending_mb"], 0)
        self.assertEqual(len(profile["market_history"]), 1)

    def test_append_runtime_file_skips_file_already_sold_in_market_history(self):
        file_entry = {
            "name": "trace_old_sold.log",
            "file_category": "gps",
            "directory": "/data/gps",
            "resource_types": ["location_history"],
            "file_size": 11,
            "operation_id": "op_sold_trace",
            "source_operation_id": "op_sold_trace",
            "market_status": "not_listed",
            "sellable": True,
            "metadata": {"operation_id": "op_sold_trace", "record_count": 4},
        }
        normalized = run.normalize_runtime_file_entry(file_entry, "gps")
        profile = {
            "username": "neo",
            "storage_capacity": 768,
            "storage_used": 0,
            "storage_unit": "MB",
            "files": {"gps": [], "market": []},
            "market_history": [{
                "id": "batch_sold_trace",
                "batch_id": "batch_sold_trace",
                "market_sector": "gps",
                "status": "sold",
                "file_ids": [normalized["id"]],
                "price": 123,
            }],
        }
        operation = {
            "operation_id": "op_sold_trace",
            "operation_type": "generic_trace",
            "resource_buffer": {},
        }

        result = append_runtime_file_if_space(profile, operation, "gps", file_entry)

        self.assertFalse(result["stored"])
        self.assertEqual(result["result"]["status"], "already_sold")
        self.assertEqual(profile["files"]["gps"], [])
        self.assertEqual(profile["storage_used"], 0)

    def test_append_runtime_file_skips_already_sold_files_for_all_market_sectors(self):
        sector_resources = {
            "camera": ["camera_dump"],
            "atm": ["atm_dump"],
            "gps": ["gps_logs"],
            "device": ["device_logs"],
            "personal": ["personal_records"],
            "credentials": ["credentials"],
            "financial": ["financial_records"],
            "network": ["wifi_networks"],
            "audio": ["audio_transcript"],
            "vehicle": ["vehicle_diagnostics"],
        }

        for sector, resources in sector_resources.items():
            with self.subTest(sector=sector):
                file_entry = {
                    "name": f"{sector}_already_sold.dat",
                    "file_category": sector,
                    "directory": f"/data/{sector}",
                    "resource_types": resources,
                    "file_size": 12,
                    "operation_id": f"op_sold_{sector}",
                    "source_operation_id": f"op_sold_{sector}",
                    "market_status": "not_listed",
                    "sellable": True,
                    "metadata": {
                        "operation_id": f"op_sold_{sector}",
                        "record_count": 4,
                        "quality_score": 80,
                    },
                }
                normalized = run.normalize_runtime_file_entry(file_entry, sector)
                profile = {
                    "username": "neo",
                    "storage_capacity": 768,
                    "storage_used": 0,
                    "storage_unit": "MB",
                    "files": {sector: [], "market": []},
                    "market_history": [{
                        "id": f"batch_sold_{sector}",
                        "batch_id": f"batch_sold_{sector}",
                        "market_sector": sector,
                        "status": "sold",
                        "file_ids": [normalized["id"]],
                        "price": 123,
                    }],
                }
                operation = {
                    "operation_id": f"op_sold_{sector}",
                    "operation_type": "sector_regression",
                    "resource_buffer": {},
                }

                result = append_runtime_file_if_space(profile, operation, sector, file_entry)

                self.assertFalse(result["stored"])
                self.assertEqual(result["result"]["status"], "already_sold")
                self.assertEqual(profile["files"][sector], [])
                self.assertEqual(profile["storage_used"], 0)

    def test_ghost_exchange_shows_raw_not_listed_pending_files_for_all_market_sectors(self):
        sector_fixtures = {
            "camera": (["camera_dump"], 14, {"record_count": 1}),
            "atm": (["atm_dump"], 12, {"record_count": 4}),
            "gps": (["gps_logs"], 11, {"checkpoint_count": 4}),
            "device": (["device_logs"], 13, {"record_count": 4}),
            "personal": (["personal_records"], 12, {"record_count": 4}),
            "credentials": (["credentials"], 8, {"credential_count": 2}),
            "financial": (["financial_records"], 12, {"record_count": 4, "transactions_count": 4}),
            "network": (["wifi_networks"], 13, {"network_count": 4}),
            "audio": (["audio_transcript"], 12, {"record_count": 4}),
            "vehicle": (["vehicle_diagnostics"], 14, {"systems_count": 4}),
        }

        for sector, (resources, size_mb, metadata) in sector_fixtures.items():
            with self.subTest(sector=sector):
                profile = {
                    "username": "neo",
                    "hackcoins": 45,
                    "storage_capacity": 512,
                    "storage_used": size_mb,
                    "storage_unit": "MB",
                    "files": {
                        sector: [{
                            "id": f"{sector}_raw_pending",
                            "name": f"{sector}_raw_pending.dat",
                            "file_category": sector,
                            "directory": f"/data/{sector}",
                            "resource_types": resources,
                            "file_size": size_mb,
                            "market_status": "not_listed",
                            "created_at": "2026-07-03T09:00:00Z",
                            "sellable": True,
                            "metadata": {
                                **metadata,
                                "quality_score": 80,
                                "completeness_percent": 70,
                            },
                        }],
                        "market": [],
                    },
                    "market_history": [],
                    "system_messages": [],
                }

                result = refresh_market_runtime(
                    "neo",
                    profile,
                    now=datetime(2026, 7, 3, 9, 5, tzinfo=timezone.utc),
                    payout_callback=canonical_market_test_payout(profile),
                )
                sectors = {
                    item["sector"]: item
                    for item in run.build_ghost_exchange_sector_payload(profile)
                }

                self.assertEqual(result["settled"], 0)
                self.assertIn(profile["files"][sector][0]["market_status"], {"queued_for_market", "listed"})
                self.assertEqual(sectors[sector]["pending_files"], 1)
                self.assertEqual(sectors[sector]["pending_mb"], size_mb)
                self.assertGreater(sectors[sector]["progress_percent"], 0)

    def test_api_ghost_exchange_sells_old_not_listed_network_backlog_on_first_refresh(self):
        entries = [
            {
                "id": f"network_old_pending_{index}",
                "name": f"wifi_old_pending_{index}.net",
                "file_category": "network",
                "directory": "/data/network",
                "resource_types": ["wifi_networks"],
                "file_size": 13,
                "market_status": "not_listed",
                "created_at": "2026-07-03T09:00:00Z",
                "sellable": True,
                "metadata": {
                    "record_count": 8,
                    "network_count": 8,
                    "quality_score": 90,
                    "completeness_percent": 86,
                },
            }
            for index in range(3)
        ]
        profile = {
            "username": "neo",
            "hackcoins": 45,
            "storage_capacity": 512,
            "storage_used": 503,
            "storage_unit": "MB",
            "files": {"network": entries, "market": []},
            "market_history": [],
            "system_messages": [],
        }

        class FakeManager:
            def __init__(self, username):
                self.username = username

            def update_profile(self, data):
                profile.update(data)

        client = run.app.test_client()
        with client.session_transaction() as sess:
            sess["user"] = "neo"
        original_market_runtime_now = run.market_runtime_now

        with canonical_wallet_test_runtime({"neo": profile["hackcoins"]}), \
                patch.object(run.user_store, "get_profile", return_value=profile), \
                patch.object(run, "refresh_and_persist_operations", side_effect=lambda username, current: current), \
                patch.object(run, "UserProfileManager", FakeManager), \
                patch.object(run, "add_cyberner_direct_notification") as notify_mock, \
                patch.object(
                    run,
                    "market_runtime_now",
                    side_effect=lambda value=None: (
                        datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)
                        if value is None
                        else original_market_runtime_now(value)
                    ),
                ):
            response = client.get("/api/ghost-exchange")
            data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["market_runtime"]["settled"], 1)
        self.assertEqual(profile["files"]["network"], [])
        self.assertEqual(len(profile["market_history"]), 1)
        self.assertEqual(profile["market_history"][0]["market_sector"], "network")
        self.assertGreater(profile["hackcoins"], 45)
        self.assertLess(profile["storage_used"], 503)
        notify_mock.assert_called_once()

    def test_market_runtime_sells_old_not_listed_backlog_for_all_market_sectors(self):
        sector_resources = {
            "camera": ["camera_dump"],
            "atm": ["atm_dump"],
            "gps": ["gps_logs"],
            "device": ["device_logs"],
            "personal": ["personal_records"],
            "credentials": ["credentials"],
            "financial": ["financial_records"],
            "network": ["wifi_networks"],
            "audio": ["audio_transcript"],
            "vehicle": ["vehicle_diagnostics"],
        }

        for sector, resources in sector_resources.items():
            with self.subTest(sector=sector):
                entries = [
                    {
                        "id": f"{sector}_old_pending_{index}",
                        "name": f"{sector}_old_pending_{index}.dat",
                        "file_category": sector,
                        "directory": f"/data/{sector}",
                        "resource_types": resources,
                        "file_size": 20,
                        "market_status": "not_listed",
                        "created_at": "2026-07-03T09:00:00Z",
                        "sellable": True,
                        "metadata": {
                            "record_count": 8,
                            "checkpoint_count": 8,
                            "collected_count": 8,
                            "credential_count": 8,
                            "network_count": 8,
                            "systems_count": 8,
                            "quality_score": 90,
                            "completeness_percent": 86,
                        },
                    }
                    for index in range(3)
                ]
                profile = {
                    "username": "neo",
                    "hackcoins": 45,
                    "storage_capacity": 512,
                    "storage_used": 503,
                    "storage_unit": "MB",
                    "files": {sector: entries, "market": []},
                    "market_history": [],
                    "system_messages": [],
                }

                with patch.object(run.mail_store, "add_direct_notification") as mail_mock:
                    result = refresh_market_runtime(
                        "neo",
                        profile,
                        now=datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc),
                        payout_callback=canonical_market_test_payout(profile),
                    )

                self.assertEqual(result["settled"], 1)
                self.assertEqual(profile["files"][sector], [])
                self.assertEqual(len(profile["market_history"]), 1)
                self.assertEqual(profile["market_history"][0]["market_sector"], sector)
                self.assertGreater(profile["hackcoins"], 45)
                self.assertLess(profile["storage_used"], 503)
                mail_mock.assert_called_once()

    def test_ghost_exchange_prices_richer_device_package_higher(self):
        profile = {
            "files": {
                "device": [{
                    "id": "basic_device",
                    "name": "basic_device.pkg",
                    "file_category": "device",
                    "directory": "/data/device",
                    "preview_mode": "card",
                    "resource_types": ["location_history", "device_logs"],
                    "metadata": {
                        "operation_id": "op_basic",
                        "completeness_percent": 33,
                        "completeness_tier": "fragment",
                        "quality_score": 48,
                        "collected_count": 2,
                    },
                }],
                "personal": [{
                    "id": "rich_device",
                    "name": "rich_device.pkg",
                    "file_category": "personal",
                    "directory": "/data/personal",
                    "preview_mode": "card",
                    "resource_types": [
                        "location_history",
                        "device_logs",
                        "personal_records",
                        "call_history",
                        "messenger_data",
                    ],
                    "metadata": {
                        "operation_id": "op_rich",
                        "completeness_percent": 83,
                        "completeness_tier": "rich",
                        "quality_score": 85,
                        "collected_count": 8,
                    },
                }],
            }
        }

        listings = collect_ghost_exchange_files(profile)
        by_id = {item["id"]: item for item in listings}

        self.assertGreater(by_id["rich_device"]["price_preview"], by_id["basic_device"]["price_preview"])
        self.assertEqual(by_id["basic_device"]["completeness_percent"], 33)
        self.assertEqual(by_id["rich_device"]["completeness_tier"], "rich")
        self.assertEqual(by_id["rich_device"]["quality_score"], 85)

    def test_cancelled_operation_moves_to_history_without_final_file(self):
        profile = {
            "files": {"gps": []},
            "operations": [{
                "operation_id": "op_cancel_vehicle",
                "operation_type": "vehicle_tracking",
                "owner_username": "neo",
                "target": {"lat": 52.1, "lng": 21.2, "label": "Tracked car"},
                "target_id": "map:52.1:21.2:Tracked car",
                "target_type": "vehicle",
                "status": "running",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T12:00:00Z",
                "duration_seconds": 7200,
                "movement_model": "road_movement",
                "resource_buffer": {"resource_types": ["gps_logs", "location_history"], "items": []},
            }],
            "risk_events": [],
            "system_messages": [],
        }

        operation, result = cancel_profile_operation(
            profile,
            "op_cancel_vehicle",
            cancelled_by="neo",
            now_ts=datetime(2026, 6, 27, 10, 30, tzinfo=timezone.utc).timestamp(),
        )
        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 12, 30, tzinfo=timezone.utc).timestamp(),
        )

        self.assertEqual(result, "cancelled")
        self.assertEqual(operation["status"], "cancelled")
        self.assertEqual(refreshed[0]["status"], "cancelled")
        self.assertEqual(active_operations_from_operations(refreshed), [])
        self.assertEqual(len(operation_history_from_operations(refreshed)), 1)
        self.assertEqual(profile["files"]["gps"], [])
        self.assertEqual(profile["operations"][0]["cleanup_state"]["active_object_active"], False)
        self.assertEqual(profile["operations"][0]["cleanup_state"]["marker_visible"], False)
        self.assertEqual(profile["risk_events"][0]["event_type"], "abandoned_operation")
        self.assertFalse(changed)

    def test_expired_camera_shutdown_no_longer_reduces_camera_risk(self):
        profile = {
            "operations": [
                {
                    "operation_id": "op_shutdown_expired",
                    "operation_type": "camera_shutdown",
                    "owner_username": "neo",
                    "target": {"lat": 52.1, "lng": 21.2, "label": "Kamera sklepu"},
                    "target_id": "map:52.1:21.2:Kamera sklepu",
                    "target_type": "camera",
                    "status": "timeout",
                    "started_at": "2026-06-27T10:00:00Z",
                    "expires_at": "2026-06-27T10:05:00Z",
                    "ended_at": "2026-06-27T10:05:00Z",
                    "duration_seconds": 300,
                    "support_state": {"active": False, "risk_modifier": "camera_shutdown"},
                },
                {
                    "operation_id": "op_camera_stream_risk",
                    "operation_type": "camera_stream",
                    "owner_username": "neo",
                    "target": {"lat": 52.1001, "lng": 21.2001, "label": "Kamera sklepu"},
                    "target_id": "map:52.1001:21.2001:Kamera sklepu",
                    "target_type": "camera",
                    "status": "timeout",
                    "started_at": "2026-06-27T10:01:00Z",
                    "expires_at": "2026-06-27T10:06:00Z",
                    "ended_at": "2026-06-27T10:06:00Z",
                    "duration_seconds": 300,
                    "risk_state": {"level": "none", "events": ["camera_detected"], "score": 0},
                },
            ],
            "risk_events": [],
            "system_messages": [],
        }

        refreshed, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 10, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        risk_event = next(event for event in profile["risk_events"] if event["event_type"] == "camera_detected")
        self.assertEqual(risk_event["risk_score"], 46)
        self.assertEqual(risk_event["modifiers"], [])
        self.assertEqual(active_operations_from_operations(refreshed), [])

    def test_finalizer_recreates_missing_atm_file_when_created_flag_is_stale(self):
        profile = {
            "files": {
                "atm": [],
                "financial": [],
                "market": [],
            },
            "market_history": [],
            "operations": [{
                "operation_id": "op_atm_missing_file",
                "operation_type": "atm_log_extraction",
                "owner_username": "neo",
                "source_app_id": "atm_reader",
                "map_action_id": "atm_logs",
                "target": {"lat": 52.1, "lng": 21.2, "label": "ATM"},
                "target_id": "map:52.1:21.2:ATM",
                "target_type": "atm",
                "target_mode": "standard",
                "status": "timeout",
                "started_at": "2026-06-27T10:00:00Z",
                "expires_at": "2026-06-27T10:05:00Z",
                "ended_at": "2026-06-27T10:05:00Z",
                "duration_seconds": 300,
                "resource_buffer": {
                    "resource_types": ["atm_dump"],
                    "atm_files_created": True,
                    "files": [{"name": "lost_atm_dump.dump", "file_category": "atm"}],
                },
            }],
            "risk_events": [],
            "system_messages": [],
        }

        _, changed = refresh_operations_runtime(
            profile,
            persist_timeouts=True,
            now_ts=datetime(2026, 6, 27, 10, 6, tzinfo=timezone.utc).timestamp(),
        )

        self.assertTrue(changed)
        self.assertEqual(len(profile["files"]["atm"]), 1)
        self.assertEqual(profile["files"]["atm"][0]["source_operation_id"], "op_atm_missing_file")
        self.assertTrue(profile["operations"][0]["resource_buffer"]["atm_files_created"])


if __name__ == "__main__":
    unittest.main()
