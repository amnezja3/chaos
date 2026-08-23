import copy
import hashlib
import hmac
from itertools import combinations
import json
import math
import os
import secrets
import sqlite3
import inspect
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta


DB_PATH = os.path.join("data", "game.sqlite3")
USERS_SEED_PATH = os.path.join("static", "users.json")
_WAL_CONFIGURED = False


PROFILE_SCHEMA_VERSION = 1
PROFILE_VALIDATION_VERSION = 1
PROFILE_INTEGRITY_VALID = "valid"
PROFILE_INTEGRITY_RECOVERY_REQUIRED = "recovery_required"
PROFILE_INTEGRITY_UNINITIALIZED = "uninitialized"
WALLET_CANONICAL_MIGRATION_ID = "wallet_canonical_v1"
_PROFILE_PRECOMMIT_GUARD = ContextVar(
    "chaos_profile_precommit_guard",
    default=None,
)
_REQUEST_TRANSACTION_PRECOMMIT_GUARD = ContextVar(
    "chaos_request_transaction_precommit_guard",
    default=None,
)
_PROFILE_WRITE_REQUEST_METADATA = ContextVar(
    "chaos_profile_write_request_metadata",
    default=None,
)
_HOT_PATH_METRICS = ContextVar(
    "chaos_hot_path_metrics",
    default=None,
)


def reset_hot_path_metrics():
    """Start request-local counters without changing runtime behavior."""
    return _HOT_PATH_METRICS.set({
        "profile_full_read": 0,
        "profile_full_write": 0,
        "profile_bytes": 0,
        "sqlite_writer_wait_ms": 0,
    })


def restore_hot_path_metrics(token):
    if token is not None:
        _HOT_PATH_METRICS.reset(token)


def record_hot_path_metric(name, value=1):
    metrics = _HOT_PATH_METRICS.get()
    if not isinstance(metrics, dict) or name not in metrics:
        return
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        amount = 0
    metrics[name] = int(metrics.get(name) or 0) + max(0, amount)


def get_hot_path_metrics():
    metrics = _HOT_PATH_METRICS.get()
    return dict(metrics) if isinstance(metrics, dict) else {
        "profile_full_read": 0,
        "profile_full_write": 0,
        "profile_bytes": 0,
        "sqlite_writer_wait_ms": 0,
    }


class ProfileWriteError(RuntimeError):
    """Base class for controlled profile write failures."""


class ProfileWriteConflict(ProfileWriteError):
    """Raised when a profile writer presents a stale revision."""


class ProfileValidationError(ProfileWriteError):
    """Raised when a candidate cannot be accepted as a complete profile."""

    def __init__(self, errors):
        self.errors = tuple(str(item) for item in (errors or ()))
        super().__init__("Invalid profile candidate: " + ", ".join(self.errors))


class ProfileRecoveryRequired(ProfileWriteError):
    """Raised when the current durable profile is not safe to mutate normally."""


class ProfileDestructiveWriteRejected(ProfileWriteError):
    """Raised when a multi-scope destructive write has no reset receipt."""


class ProfilePrecommitRejected(ProfileWriteError):
    """Raised when a durable request/session guard rejects a profile commit."""


class WalletWriteError(ValueError):
    """Base class for controlled canonical-wallet failures."""


class WalletNotInitialized(WalletWriteError):
    """Raised when an account has no canonical wallet row."""

    def __init__(self, message="Canonical wallet is not initialized.", reason="wallet_not_initialized"):
        self.reason = str(reason or "wallet_not_initialized")
        super().__init__(message)


class WalletInsufficientFunds(WalletWriteError):
    """Raised when a strict debit would make a wallet negative."""


class WalletIdempotencyConflict(WalletWriteError):
    """Raised when a transaction key is reused for different semantics."""


class WalletMutationRejected(WalletWriteError):
    """Raised for legacy absolute-balance writers outside recovery."""


def set_profile_precommit_guard(precommit_guard):
    if precommit_guard is not None and not callable(precommit_guard):
        raise TypeError("precommit_guard must be callable or None.")
    return _PROFILE_PRECOMMIT_GUARD.set(precommit_guard)


def reset_profile_precommit_guard(token):
    _PROFILE_PRECOMMIT_GUARD.reset(token)


def get_profile_precommit_guard():
    return _PROFILE_PRECOMMIT_GUARD.get()


def set_request_transaction_precommit_guard(precommit_guard):
    if precommit_guard is not None and not callable(precommit_guard):
        raise TypeError("precommit_guard must be callable or None.")
    return _REQUEST_TRANSACTION_PRECOMMIT_GUARD.set(precommit_guard)


def reset_request_transaction_precommit_guard(token):
    _REQUEST_TRANSACTION_PRECOMMIT_GUARD.reset(token)


def get_request_transaction_precommit_guard():
    return _REQUEST_TRANSACTION_PRECOMMIT_GUARD.get()


def _profile_telemetry_digest(value):
    """Return a bounded one-way correlation value, never the source secret."""
    value = str(value or "").strip()
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


def set_profile_write_request_metadata(*, session_generation, request_id=""):
    """Bind safe request correlation metadata for central profile telemetry.

    The ContextVar deliberately contains only bounded SHA-256 digests. Raw
    generation/request values remain in the request/session layer and cannot
    leak through profile writer events.
    """
    metadata = {
        "session_generation_hash": _profile_telemetry_digest(
            session_generation
        ),
        "request_id": _profile_telemetry_digest(request_id),
    }
    return _PROFILE_WRITE_REQUEST_METADATA.set(metadata)


def reset_profile_write_request_metadata(token):
    _PROFILE_WRITE_REQUEST_METADATA.reset(token)


def get_profile_write_request_metadata():
    metadata = _PROFILE_WRITE_REQUEST_METADATA.get()
    return dict(metadata) if isinstance(metadata, dict) else {}


def _run_request_transaction_precommit_guard(conn):
    guard = get_request_transaction_precommit_guard()
    if guard is None:
        return
    if not callable(guard):
        raise TypeError("request transaction precommit guard must be callable.")
    try:
        guard(conn=conn)
    except ProfileWriteError:
        raise
    except Exception as exc:
        raise ProfilePrecommitRejected(
            "Request transaction precommit guard rejected the commit."
        ) from exc


_PROFILE_SENSITIVE_SNAPSHOT_KEYS = {
    "password", "salt", "cookie", "cookies", "session", "session_id",
    "session_token", "token", "access_token", "refresh_token",
}
_PROFILE_TRANSIENT_SNAPSHOT_KEYS = {
    "launch_queue",
}
_PROFILE_CANONICAL_MIRROR_SNAPSHOT_KEYS = {
    "apps", "hackcoins", "storage_capacity", "storage_used", "storage_unit",
    "storage_upgrades", "googleplex_products", "storage_soft_limit",
    "storage_over_limit",
}
_PROFILE_TERRITORY_SNAPSHOT_KEYS = {
    "areas", "player_areas", "territory",
}
_PROFILE_GEOMETRY_SNAPSHOT_KEYS = {
    "geometry", "polygon", "polygons", "coordinates",
}
_PROFILE_INTERNAL_KEYS = {
    "_launch_queue_write_mode", "_profile_revision", "_profile_checksum",
    "_profile_schema_version", "_profile_integrity_status",
}


def _canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )


def profile_payload_checksum(profile):
    return hashlib.sha256(_canonical_json(profile).encode("utf-8")).hexdigest()


def _profile_snapshot_value(value, *, top_level=False):
    if isinstance(value, dict):
        snapshot = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if lowered in _PROFILE_SENSITIVE_SNAPSHOT_KEYS:
                continue
            if top_level and lowered in _PROFILE_TRANSIENT_SNAPSHOT_KEYS:
                continue
            if top_level and lowered in _PROFILE_CANONICAL_MIRROR_SNAPSHOT_KEYS:
                continue
            if top_level and lowered in _PROFILE_TERRITORY_SNAPSHOT_KEYS:
                continue
            if lowered in _PROFILE_GEOMETRY_SNAPSHOT_KEYS:
                continue
            if key in _PROFILE_INTERNAL_KEYS:
                continue
            snapshot[key] = _profile_snapshot_value(item)
            if top_level and lowered == "files" and isinstance(snapshot[key], dict):
                snapshot[key].pop("tools", None)
        return snapshot
    if isinstance(value, list):
        return [_profile_snapshot_value(item) for item in value]
    return copy.deepcopy(value)


def profile_last_known_good_snapshot(profile):
    """Return a credential-free profile snapshot without territory geometry."""
    return _profile_snapshot_value(profile if isinstance(profile, dict) else {}, top_level=True)


def _is_profile_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_profile_candidate(profile, expected_username=None):
    """Validate the minimum durable full-profile contract without using a template."""
    errors = []
    if not isinstance(profile, dict):
        return {
            "valid": False,
            "errors": ("profile_not_object",),
            "schema_version": PROFILE_SCHEMA_VERSION,
            "validation_version": PROFILE_VALIDATION_VERSION,
        }

    username = profile.get("username")
    if not isinstance(username, str) or not username.strip():
        errors.append("username_missing")
    elif expected_username is not None and username != expected_username:
        errors.append("username_mismatch")

    required_types = {
        "level": lambda value: isinstance(value, int) and not isinstance(value, bool) and value >= 1,
        "hackcoins": lambda value: _is_profile_number(value) and value >= 0,
        "respect": lambda value: _is_profile_number(value) and value >= 0,
        "exp": lambda value: (
            (isinstance(value, str) and bool(value.strip())) or _is_profile_number(value)
        ),
        "inventory": lambda value: isinstance(value, list),
        "files": lambda value: isinstance(value, dict),
        "apps": lambda value: isinstance(value, list),
        "hacked": lambda value: isinstance(value, list),
        "desktop_settings": lambda value: isinstance(value, dict),
        "security": lambda value: isinstance(value, dict),
        "territory_stats": lambda value: isinstance(value, dict),
    }
    for key, validator in required_types.items():
        if key not in profile:
            errors.append(f"{key}_missing")
        elif not validator(profile.get(key)):
            errors.append(f"{key}_invalid")

    files = profile.get("files")
    if isinstance(files, dict):
        invalid_file_scopes = sorted(
            str(key) for key, value in files.items() if not isinstance(value, list)
        )
        if invalid_file_scopes:
            errors.append("files_scope_invalid:" + ",".join(invalid_file_scopes))

    try:
        _canonical_json(profile)
    except (TypeError, ValueError):
        errors.append("profile_not_json_serializable")

    return {
        "valid": not errors,
        "errors": tuple(errors),
        "schema_version": PROFILE_SCHEMA_VERSION,
        "validation_version": PROFILE_VALIDATION_VERSION,
    }


def _profile_collection_size(profile, keys):
    total = 0
    for key in keys:
        value = (profile or {}).get(key)
        if isinstance(value, (list, dict)):
            total += len(value)
    return total


def _profile_files_size(profile):
    files = (profile or {}).get("files")
    if not isinstance(files, dict):
        return 0
    return sum(len(value) for value in files.values() if isinstance(value, list))


def _profile_exp_value(profile):
    value = (profile or {}).get("exp", 0)
    if _is_profile_number(value):
        return float(value)
    text = str(value or "").strip().replace(" ", "")
    head = text.split("/", 1)[0]
    filtered = "".join(char for char in head if char.isdigit() or char in ".,-")
    try:
        return float(filtered.replace(",", ".")) if filtered else 0.0
    except ValueError:
        return 0.0


def assess_profile_destructive_drop(current_profile, candidate_profile):
    """Detect a reset-shaped loss across independent durable profile scopes."""
    current_profile = current_profile if isinstance(current_profile, dict) else {}
    candidate_profile = candidate_profile if isinstance(candidate_profile, dict) else {}
    dropped_scopes = []

    current_level = int(current_profile.get("level", 1) or 1)
    candidate_level = int(candidate_profile.get("level", 1) or 1)
    current_respect = float(current_profile.get("respect", 0) or 0)
    candidate_respect = float(candidate_profile.get("respect", 0) or 0)
    if (
        candidate_level < current_level
        or candidate_respect < current_respect
        or _profile_exp_value(candidate_profile) < _profile_exp_value(current_profile)
    ):
        dropped_scopes.append("progression")

    current_inventory = _profile_collection_size(current_profile, ("inventory", "apps")) + _profile_files_size(current_profile)
    candidate_inventory = _profile_collection_size(candidate_profile, ("inventory", "apps")) + _profile_files_size(candidate_profile)
    if current_inventory >= 3 and candidate_inventory <= max(0, current_inventory // 4):
        dropped_scopes.append("inventory")

    history_keys = (
        "operations", "hacked", "targets", "market_history", "product_purchases",
        "ghostnetwork_reward_history", "risk_events", "system_messages",
    )
    current_history = _profile_collection_size(current_profile, history_keys)
    candidate_history = _profile_collection_size(candidate_profile, history_keys)
    if current_history >= 3 and candidate_history <= max(0, current_history // 4):
        dropped_scopes.append("history")

    current_storage = float(current_profile.get("storage_capacity", 0) or 0)
    candidate_storage = float(candidate_profile.get("storage_capacity", 0) or 0)
    current_upgrades = _profile_collection_size(current_profile, ("storage_upgrades",))
    candidate_upgrades = _profile_collection_size(candidate_profile, ("storage_upgrades",))
    if candidate_storage < current_storage or candidate_upgrades < current_upgrades:
        dropped_scopes.append("storage")

    identity_fields = ("nick", "email", "clan", "fraction")
    identity_loss = sum(
        1 for key in identity_fields
        if current_profile.get(key) not in (None, "", {}, [])
        and candidate_profile.get(key) in (None, "", {}, [])
    )
    if identity_loss >= 2:
        dropped_scopes.append("identity")

    starter_like = (
        candidate_level <= 2
        and float(candidate_profile.get("hackcoins", 0) or 0) <= 1000
        and candidate_respect <= 25
        and _profile_exp_value(candidate_profile) <= 0
    )
    destructive = len(dropped_scopes) >= 3 or (starter_like and len(dropped_scopes) >= 2)
    return {
        "destructive": destructive,
        "starter_like": starter_like,
        "dropped_scopes": tuple(sorted(set(dropped_scopes))),
    }


def _valid_reset_receipt(reset_receipt):
    if not isinstance(reset_receipt, dict):
        return False
    return all(
        isinstance(reset_receipt.get(key), str) and reset_receipt.get(key).strip()
        for key in ("receipt_id", "reason", "authorized_by", "created_at")
    )


def _run_profile_precommit_guard(precommit_guard, conn, username, current_revision):
    context_guard = get_profile_precommit_guard()
    guards = []
    for guard in (context_guard, precommit_guard):
        if guard is None or any(guard is existing for existing in guards):
            continue
        if not callable(guard):
            raise TypeError("precommit_guard must be callable.")
        guards.append(guard)
    for guard in guards:
        try:
            guard(
                conn=conn,
                username=username,
                current_revision=int(current_revision),
            )
        except ProfileWriteError:
            raise
        except Exception as exc:
            raise ProfilePrecommitRejected(
                "Profile precommit guard rejected the write."
            ) from exc


def _profile_event(event_type, username, source, **fields):
    metrics_enabled = str(
        os.environ.get("CHAOS_PROFILE_WRITE_METRICS") or ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    if not metrics_enabled and str(event_type) not in {
        "profile.write_rejected", "profile.recovery_required",
    }:
        return
    payload = {
        "event": str(event_type),
        "username_hash": hashlib.sha256(str(username or "").encode("utf-8")).hexdigest()[:16],
        "source": str(source or "unknown")[:80],
    }
    request_metadata = get_profile_write_request_metadata()
    for field_name in ("session_generation_hash", "request_id"):
        if not str(fields.get(field_name) or "").strip():
            fields[field_name] = str(
                request_metadata.get(field_name) or ""
            )[:80]
    payload.update(fields)
    print("[PROFILE_WRITE] " + dumps_json(payload), flush=True)


def db_lock_metrics_enabled():
    return str(os.environ.get("CHAOS_DB_LOCK_METRICS") or "").strip().lower() in {
        "1", "true", "yes", "on",
    }


class InstrumentedConnection(sqlite3.Connection):
    """Opt-in writer wait/hold telemetry; it does not alter transaction behavior."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._writer_started_at = None
        self._writer_wait_ms = 0
        self._writer_origin = "unknown"
        self._writer_statements = 0
        self._enforce_request_guard = True

    def execute(self, sql, parameters=(), /):
        statement = str(sql or "").lstrip().upper()
        if db_lock_metrics_enabled() and statement.startswith("BEGIN IMMEDIATE"):
            started = time.perf_counter()
            try:
                result = super().execute(sql, parameters)
            except sqlite3.OperationalError as exc:
                wait_ms = int(round((time.perf_counter() - started) * 1000))
                record_hot_path_metric("sqlite_writer_wait_ms", wait_ms)
                try:
                    origin = inspect.currentframe().f_back.f_code.co_name
                except Exception:
                    origin = "unknown"
                if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                    print(
                        "[DB_LOCK] "
                        f"at={utc_now()} pid={os.getpid()} thread={threading.get_ident()} "
                        f"origin={origin} outcome=busy wait_ms={wait_ms} "
                        "hold_ms=0 commit_ms=0 statements=0",
                        flush=True,
                    )
                raise
            self._writer_wait_ms = int(round((time.perf_counter() - started) * 1000))
            record_hot_path_metric("sqlite_writer_wait_ms", self._writer_wait_ms)
            self._writer_started_at = time.perf_counter()
            self._writer_statements = 0
            try:
                self._writer_origin = inspect.currentframe().f_back.f_code.co_name
            except Exception:
                self._writer_origin = "unknown"
            return result
        result = super().execute(sql, parameters)
        if self._writer_started_at is not None:
            self._writer_statements += 1
        return result

    def _finish_writer_metric(self, outcome, commit_ms=0):
        if self._writer_started_at is None:
            return
        hold_ms = int(round((time.perf_counter() - self._writer_started_at) * 1000))
        minimum = max(0, int(os.environ.get("CHAOS_DB_LOCK_METRICS_MIN_MS", "25")))
        if self._writer_wait_ms >= minimum or hold_ms >= minimum:
            print(
                "[DB_LOCK] "
                f"at={utc_now()} pid={os.getpid()} thread={threading.get_ident()} "
                f"origin={self._writer_origin} outcome={outcome} "
                f"wait_ms={self._writer_wait_ms} hold_ms={hold_ms} "
                f"commit_ms={commit_ms} statements={self._writer_statements}",
                flush=True,
            )
        self._writer_started_at = None
        self._writer_wait_ms = 0
        self._writer_origin = "unknown"
        self._writer_statements = 0

    def commit(self):
        started = time.perf_counter()
        try:
            if self.in_transaction and self._enforce_request_guard:
                _run_request_transaction_precommit_guard(self)
            result = super().commit()
        except Exception:
            try:
                super().rollback()
            finally:
                self._finish_writer_metric("rollback")
            raise
        else:
            commit_ms = int(round((time.perf_counter() - started) * 1000))
            self._finish_writer_metric("commit", commit_ms=commit_ms)
            return result

    def rollback(self):
        try:
            return super().rollback()
        finally:
            self._finish_writer_metric("rollback")

    def __exit__(self, exc_type, exc_value, traceback):
        # sqlite3's native context manager does not dispatch through an
        # overridden commit() on every supported Python build. Keep the same
        # commit/rollback semantics while enforcing the request guard here too.
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        return False


def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds")


def dumps_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads_json(value, default=None):
    if value is None:
        return copy.deepcopy(default)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return copy.deepcopy(default)


def merge_launch_queue_values(latest_queue, incoming_queue):
    merged = []
    seen = set()
    for item in list(latest_queue or []) + list(incoming_queue or []):
        if isinstance(item, dict):
            value = str(
                item.get("receipt")
                or item.get("launch_receipt")
                or item.get("launch_key")
                or item.get("name")
                or item.get("app_name")
                or ""
            ).strip()
        else:
            value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        merged.append(item)
    return merged


def _prepare_full_profile_candidate(profile, current_row=None):
    candidate = copy.deepcopy(profile if isinstance(profile, dict) else {})
    launch_queue_write_mode = str(
        candidate.pop("_launch_queue_write_mode", "") or ""
    ).strip()
    for key in _PROFILE_INTERNAL_KEYS:
        candidate.pop(key, None)

    current_profile = {}
    if current_row is not None:
        current_profile, _ = _parse_profile_json_strict(current_row["profile_json"])
        current_profile = current_profile or {}
    if current_profile:
        incoming_password = str(candidate.get("password") or "")
        if not incoming_password:
            candidate["password"] = str(
                current_row["password"]
                or current_profile.get("password")
                or ""
            )
            candidate["salt"] = str(
                current_row["salt"]
                or current_profile.get("salt")
                or ""
            )
        if launch_queue_write_mode == "clear":
            candidate["launch_queue"] = []
        elif launch_queue_write_mode == "append":
            candidate["launch_queue"] = merge_launch_queue_values(
                current_profile.get("launch_queue", []),
                candidate.get("launch_queue", []),
            )
        else:
            candidate["launch_queue"] = current_profile.get("launch_queue", [])

        current_ghost_history = current_profile.get("ghostnetwork_reward_history") or []
        incoming_ghost_history = candidate.get("ghostnetwork_reward_history") or []
        merged_ghost_history = []
        seen_ghost_reward_keys = set()
        for item in list(current_ghost_history) + list(incoming_ghost_history):
            if not isinstance(item, dict):
                continue
            reward_key = str(item.get("reward_key") or "").strip()
            if not reward_key or reward_key in seen_ghost_reward_keys:
                continue
            seen_ghost_reward_keys.add(reward_key)
            merged_ghost_history.append(dict(item))
        if merged_ghost_history:
            candidate["ghostnetwork_reward_history"] = merged_ghost_history

    ensure_password_hash(candidate)
    return candidate


def profile_changed_scopes(current_profile, candidate_profile):
    scope_keys = {
        "identity": {"username", "nick", "email", "avatar", "clan", "fraction"},
        "progression": {"level", "respect", "exp", "territory_stats"},
        "wallet": {"hackcoins", "market_history"},
        "inventory": {
            "inventory", "files", "apps", "googleplex_products",
            "product_purchases", "storage_upgrades", "storage_capacity",
            "storage_used",
        },
        "history": {
            "operations", "hacked", "targets", "risk_events", "system_messages",
            "ghostnetwork_reward_history",
        },
        "presentation": {"desktop_settings", "friends", "messages"},
    }
    changed_keys = {
        key for key in set(current_profile or {}) | set(candidate_profile or {})
        if (current_profile or {}).get(key) != (candidate_profile or {}).get(key)
    }
    scopes = {
        scope for scope, keys in scope_keys.items() if changed_keys.intersection(keys)
    }
    if changed_keys.difference(set().union(*scope_keys.values())):
        scopes.add("other")
    return tuple(sorted(scopes))


def overlay_canonical_profile_scopes_with_conn(conn, username, profile):
    """Overlay existing canonical wallet/inventory rows without ever seeding them."""
    username = str(username or "").strip()
    candidate = copy.deepcopy(profile if isinstance(profile, dict) else {})
    overlaid_scopes = []

    wallet_row = conn.execute(
        "SELECT balance FROM wallet_balances WHERE username = ?",
        (username,),
    ).fetchone()
    if wallet_row is not None:
        candidate["hackcoins"] = int(wallet_row["balance"] or 0)
        overlaid_scopes.append("wallet")

    inventory_exists = conn.execute(
        """
        SELECT 1
        FROM (
            SELECT username FROM player_apps WHERE username = ?
            UNION ALL
            SELECT username FROM player_tool_files WHERE username = ?
            UNION ALL
            SELECT username FROM player_storage WHERE username = ?
        )
        LIMIT 1
        """,
        (username, username, username),
    ).fetchone()
    if inventory_exists is not None:
        app_rows = conn.execute(
            """
            SELECT app_id, app_json, status
            FROM player_apps
            WHERE username = ? AND status != 'uninstalled'
            ORDER BY updated_at, app_id
            """,
            (username,),
        ).fetchall()
        apps = []
        for row in app_rows:
            app = loads_json(row["app_json"], {})
            if not isinstance(app, dict):
                continue
            app.setdefault("id", row["app_id"])
            app.setdefault("status", row["status"])
            apps.append(app)
        candidate["apps"] = apps

        tool_rows = conn.execute(
            """
            SELECT tool_id, app_id, tool_json
            FROM player_tool_files
            WHERE username = ?
            ORDER BY updated_at, tool_id
            """,
            (username,),
        ).fetchall()
        tools = []
        for row in tool_rows:
            tool = loads_json(row["tool_json"], {})
            if not isinstance(tool, dict):
                tool = {"name": row["tool_id"], "file": row["tool_id"]}
            tool.setdefault("id", row["tool_id"])
            tool.setdefault("tool_id", row["tool_id"])
            tool.setdefault("app_id", row["app_id"])
            tools.append(tool)
        files = (
            copy.deepcopy(candidate.get("files"))
            if isinstance(candidate.get("files"), dict)
            else {}
        )
        files["tools"] = tools
        candidate["files"] = files

        storage_row = conn.execute(
            "SELECT * FROM player_storage WHERE username = ?",
            (username,),
        ).fetchone()
        if storage_row is not None:
            candidate["storage_capacity"] = int(storage_row["capacity"] or 0)
            candidate["storage_used"] = int(storage_row["used"] or 0)
            candidate["storage_unit"] = str(storage_row["unit"] or "MB")
            modifiers = loads_json(storage_row["modifiers_json"], {})
            if isinstance(modifiers, dict):
                for key in (
                    "storage_upgrades", "googleplex_products",
                    "storage_soft_limit", "storage_over_limit",
                ):
                    if key in modifiers:
                        candidate[key] = copy.deepcopy(modifiers[key])
        overlaid_scopes.append("inventory")

    marked_targets_seeded = conn.execute(
        "SELECT 1 FROM player_marked_target_state WHERE username = ?",
        (username,),
    ).fetchone()
    if marked_targets_seeded is not None:
        target_rows = conn.execute(
            """
            SELECT target_json
            FROM player_marked_targets
            WHERE username = ? AND status = 'active'
            ORDER BY created_at, target_key
            """,
            (username,),
        ).fetchall()
        candidate["targets"] = [
            target
            for target in (loads_json(row["target_json"], {}) for row in target_rows)
            if isinstance(target, dict) and target
        ]
        overlaid_scopes.append("marked_targets")

    return candidate, tuple(overlaid_scopes)


PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 240000


def is_password_hash(value):
    return isinstance(value, str) and value.startswith(f"{PASSWORD_HASH_PREFIX}$")


def hash_password(password, salt=None):
    password = str(password or "")
    salt = str(salt or secrets.token_hex(16))
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt}${digest}", salt


def verify_password(password, stored_password):
    if not is_password_hash(stored_password):
        return hmac.compare_digest(str(stored_password or ""), str(password or ""))

    try:
        prefix, iterations, salt, stored_digest = str(stored_password).split("$", 3)
        if prefix != PASSWORD_HASH_PREFIX:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, stored_digest)
    except (TypeError, ValueError):
        return False


def ensure_password_hash(profile):
    if not isinstance(profile, dict):
        return profile
    password = str(profile.get("password") or "")
    if not password or is_password_hash(password):
        return profile
    hashed_password, salt = hash_password(password)
    profile["password"] = hashed_password
    profile["salt"] = salt
    return profile


@contextmanager
def db_connect(db_path=DB_PATH, *, enforce_request_guard=True):
    global _WAL_CONFIGURED
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=15, factory=InstrumentedConnection)
    conn._enforce_request_guard = bool(enforce_request_guard)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA synchronous = NORMAL")
    if not _WAL_CONFIGURED:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            _WAL_CONFIGURED = True
        except sqlite3.OperationalError:
            pass
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _parse_profile_json_strict(raw_value):
    try:
        value = json.loads(raw_value)
    except (TypeError, json.JSONDecodeError):
        return None, ("invalid_json",)
    if not isinstance(value, dict):
        return None, ("profile_not_object",)
    return value, ()


def _validate_persisted_profile_row(row, username):
    if row is None:
        return None, ("profile_not_found",)
    profile, parse_errors = _parse_profile_json_strict(row["profile_json"])
    if profile is None:
        return None, tuple(parse_errors)
    validation = validate_profile_candidate(profile, username)
    errors = list(validation["errors"])
    if str(row["profile_integrity_status"] or "") != PROFILE_INTEGRITY_VALID:
        errors.append("profile_integrity_status_invalid")
    stored_checksum = str(row["profile_checksum"] or "")
    if not stored_checksum or profile_payload_checksum(profile) != stored_checksum:
        errors.append("profile_checksum_mismatch")
    return profile, tuple(sorted(set(errors)))


def _prepare_profile_lkg(profile):
    snapshot = profile_last_known_good_snapshot(profile)
    snapshot_json = _canonical_json(snapshot)
    checksum = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
    return snapshot_json, checksum


def _write_profile_lkg(conn, username, profile, revision, source, created_at=None,
                       prepared=None):
    snapshot_json, checksum = prepared or _prepare_profile_lkg(profile)
    conn.execute(
        """
        INSERT INTO profile_last_known_good (
            username, profile_revision, schema_version, snapshot_json,
            checksum, source, created_at, validation_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET
            profile_revision = excluded.profile_revision,
            schema_version = excluded.schema_version,
            snapshot_json = excluded.snapshot_json,
            checksum = excluded.checksum,
            source = excluded.source,
            created_at = excluded.created_at,
            validation_version = excluded.validation_version
        """,
        (
            username,
            int(revision),
            PROFILE_SCHEMA_VERSION,
            snapshot_json,
            checksum,
            str(source or "unknown")[:80],
            created_at or utc_now(),
            PROFILE_VALIDATION_VERSION,
        ),
    )
    return checksum


def _bootstrap_profile_integrity_rows(conn):
    rows = conn.execute(
        """
        SELECT username, profile_json, profile_revision, profile_checksum,
               profile_integrity_status
        FROM users
        WHERE profile_integrity_status = ?
           OR (
                profile_integrity_status = ?
                AND (profile_revision <= 0 OR profile_checksum = '')
           )
        ORDER BY id
        """,
        (PROFILE_INTEGRITY_UNINITIALIZED, PROFILE_INTEGRITY_VALID),
    ).fetchall()
    for row in rows:
        profile, parse_errors = _parse_profile_json_strict(row["profile_json"])
        validation = validate_profile_candidate(profile, row["username"]) if profile is not None else {
            "valid": False,
            "errors": parse_errors,
        }
        if not validation["valid"]:
            conn.execute(
                """
                UPDATE users
                SET profile_integrity_status = ?, profile_validation_version = ?
                WHERE username = ?
                """,
                (
                    PROFILE_INTEGRITY_RECOVERY_REQUIRED,
                    PROFILE_VALIDATION_VERSION,
                    row["username"],
                ),
            )
            continue

        revision = max(1, int(row["profile_revision"] or 0))
        checksum = profile_payload_checksum(profile)
        conn.execute(
            """
            UPDATE users
            SET profile_revision = ?, profile_schema_version = ?,
                profile_checksum = ?, profile_integrity_status = ?,
                profile_validation_version = ?
            WHERE username = ?
            """,
            (
                revision,
                PROFILE_SCHEMA_VERSION,
                checksum,
                PROFILE_INTEGRITY_VALID,
                PROFILE_VALIDATION_VERSION,
                row["username"],
            ),
        )
        existing_lkg = conn.execute(
            "SELECT 1 FROM profile_last_known_good WHERE username = ?",
            (row["username"],),
        ).fetchone()
        if not existing_lkg:
            _write_profile_lkg(
                conn,
                row["username"],
                profile,
                revision,
                "bootstrap",
            )


def _wallet_int(value, default=0):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return int(default)


def _wallet_record_ledger_with_conn(
    conn,
    *,
    username,
    event_type,
    amount_delta,
    balance_after,
    source="",
    source_id="",
    peer_username="",
    note="",
    dedupe_key="",
    payload_json="{}",
    created_at=None,
    ledger_id=None,
):
    username = str(username or "").strip()
    if not username:
        raise WalletWriteError("Wallet ledger username is required.")
    event_type = str(event_type or "wallet.balance_changed").strip()
    source = str(source or "").strip()
    source_id = str(source_id or "").strip()
    peer_username = str(peer_username or "").strip()
    note = str(note or "").strip()[:240]
    dedupe_key = str(dedupe_key or "").strip()
    if not dedupe_key:
        raise WalletWriteError("Wallet ledger dedupe_key is required.")
    created_at = str(created_at or utc_now()).strip()
    ledger_id = ledger_id or (
        "wl_" + hashlib.sha1(
            f"{username}:{dedupe_key}".encode("utf-8")
        ).hexdigest()[:18]
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO wallet_ledger
            (ledger_id, username, event_type, amount_delta, balance_after,
             source, source_id, peer_username, note, dedupe_key,
             payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ledger_id,
            username,
            event_type,
            int(amount_delta),
            max(0, int(balance_after)),
            source,
            source_id,
            peer_username,
            note,
            dedupe_key,
            payload_json or "{}",
            created_at,
        ),
    )
    return conn.execute(
        """
        SELECT ledger_id, username, event_type, amount_delta, balance_after,
               source, source_id, peer_username, note, dedupe_key,
               payload_json, created_at
        FROM wallet_ledger
        WHERE username = ? AND dedupe_key = ?
        """,
        (username, dedupe_key),
    ).fetchone()


def _wallet_record_balance_event_with_conn(
    conn,
    *,
    username,
    transaction_key,
    amount_delta,
    balance,
    version,
    reason,
    created_at,
):
    transaction_key = str(transaction_key or "").strip()
    if not transaction_key:
        raise WalletWriteError("Wallet transaction_key is required.")
    event_id = "wbe_" + hashlib.sha1(
        f"{username}:{transaction_key}".encode("utf-8")
    ).hexdigest()[:18]
    conn.execute(
        """
        INSERT INTO wallet_balance_events
            (event_id, username, transaction_key, amount_delta, balance,
             version, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            username,
            transaction_key,
            int(amount_delta),
            max(0, int(balance)),
            max(0, int(version)),
            str(reason or "").strip(),
            str(created_at or utc_now()),
        ),
    )
    return event_id


def _wallet_record_migration_with_conn(
    conn,
    username,
    source_checksum,
    balance,
    completed_at,
):
    result_checksum = hashlib.sha256(
        _canonical_json({"balance": int(balance)}).encode("utf-8")
    ).hexdigest()
    conn.execute(
        """
        INSERT INTO profile_store_migrations
            (migration_id, username, status, source_checksum,
             result_checksum, started_at, completed_at, error_json,
             backup_json, tool_version)
        VALUES (?, ?, 'applied', ?, ?, ?, ?, NULL, NULL, ?)
        ON CONFLICT(migration_id, username) DO UPDATE SET
            status = 'applied',
            source_checksum = excluded.source_checksum,
            result_checksum = excluded.result_checksum,
            completed_at = excluded.completed_at,
            error_json = NULL,
            tool_version = excluded.tool_version
        """,
        (
            WALLET_CANONICAL_MIGRATION_ID,
            username,
            str(source_checksum or ""),
            result_checksum,
            completed_at,
            completed_at,
            "database.wallet_canonical.v1",
        ),
    )


def _wallet_record_migration_blocked_with_conn(
    conn,
    username,
    source_checksum,
    reason,
    details,
    created_at=None,
):
    now = str(created_at or utc_now())
    conn.execute(
        """
        INSERT INTO profile_store_migrations
            (migration_id, username, status, source_checksum,
             result_checksum, started_at, completed_at, error_json,
             backup_json, tool_version)
        VALUES (?, ?, 'blocked', ?, NULL, ?, NULL, ?, NULL, ?)
        ON CONFLICT(migration_id, username) DO UPDATE SET
            status = 'blocked',
            source_checksum = excluded.source_checksum,
            result_checksum = NULL,
            completed_at = NULL,
            error_json = excluded.error_json,
            tool_version = excluded.tool_version
        """,
        (
            WALLET_CANONICAL_MIGRATION_ID,
            username,
            str(source_checksum or ""),
            now,
            dumps_json({
                "reason": str(reason or "wallet_evidence_conflict"),
                "details": details if isinstance(details, dict) else {},
            }),
            "database.wallet_canonical.v1",
        ),
    )


def _wallet_seed_with_conn(
    conn,
    username,
    balance,
    *,
    source_checksum,
    source,
    reset_existing=False,
    created_at=None,
    initial_version=1,
):
    username = str(username or "").strip()
    if not username:
        raise WalletWriteError("Wallet username is required.")
    balance = max(0, _wallet_int(balance))
    now = str(created_at or utc_now())
    if reset_existing:
        conn.execute(
            "DELETE FROM wallet_balance_events WHERE username = ?",
            (username,),
        )
        conn.execute("DELETE FROM wallet_ledger WHERE username = ?", (username,))
        conn.execute("DELETE FROM wallet_balances WHERE username = ?", (username,))
        conn.execute(
            "DELETE FROM wallet_transactions "
            "WHERE from_username = ? OR to_username = ?",
            (username, username),
        )

    existing = conn.execute(
        "SELECT balance, version FROM wallet_balances WHERE username = ?",
        (username,),
    ).fetchone()
    if existing is None:
        canonical_balance = balance
        version = max(1, _wallet_int(initial_version, 1))
        conn.execute(
            """
            INSERT INTO wallet_balances(username, balance, version, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (username, canonical_balance, version, now),
        )
    else:
        canonical_balance = max(0, int(existing["balance"] or 0))
        version = max(1, int(existing["version"] or 0))

    event_stats = conn.execute(
        """
        SELECT COUNT(*) AS event_count,
               COALESCE(SUM(amount_delta), 0) AS event_total
        FROM wallet_balance_events WHERE username = ?
        """,
        (username,),
    ).fetchone()
    event_count = int(event_stats["event_count"] or 0)
    event_total = int(event_stats["event_total"] or 0)
    event_reconcile_delta = canonical_balance - event_total
    if event_reconcile_delta != 0:
        event_kind = "seed" if event_count == 0 else "reconcile"
        event_key = f"wallet.bootstrap.v1:{username}:{event_kind}"
        _wallet_record_balance_event_with_conn(
            conn,
            username=username,
            transaction_key=event_key,
            amount_delta=event_reconcile_delta,
            balance=canonical_balance,
            version=version,
            reason=(
                str(source or "wallet.bootstrap")
                if event_count == 0
                else "wallet.bootstrap.reconcile"
            ),
            created_at=now,
        )
    ledger_stats = conn.execute(
        """
        SELECT COUNT(*) AS event_count,
               COALESCE(SUM(amount_delta), 0) AS event_total
        FROM wallet_ledger WHERE username = ?
        """,
        (username,),
    ).fetchone()
    ledger_count = int(ledger_stats["event_count"] or 0)
    ledger_total = int(ledger_stats["event_total"] or 0)
    ledger_reconcile_delta = canonical_balance - ledger_total
    if ledger_reconcile_delta != 0:
        ledger_kind = "seed" if ledger_count == 0 else "reconcile"
        _wallet_record_ledger_with_conn(
            conn,
            username=username,
            event_type=(
                "wallet.seed" if ledger_count == 0 else "wallet.reconcile"
            ),
            amount_delta=ledger_reconcile_delta,
            balance_after=canonical_balance,
            source=str(source or "wallet.bootstrap"),
            source_id=WALLET_CANONICAL_MIGRATION_ID,
            dedupe_key=f"wallet:ledger:{username}:bootstrap:v1:{ledger_kind}",
            note="Canonical wallet bootstrap reconciliation.",
            payload_json=dumps_json({
                "profile_checksum": str(source_checksum or ""),
                "previous_ledger_total": ledger_total,
            }),
            created_at=now,
        )
    _wallet_record_migration_with_conn(
        conn,
        username,
        source_checksum,
        canonical_balance,
        now,
    )
    return {
        "username": username,
        "balance": canonical_balance,
        "version": version,
    }


def _wallet_bootstrap_user_with_conn(conn, row):
    username = str(row["username"] or "").strip()
    profile, errors = _validate_persisted_profile_row(row, username)
    if errors or profile is None:
        return {"status": "skipped", "reason": "profile_not_valid"}

    balance_row = conn.execute(
        "SELECT balance, version FROM wallet_balances WHERE username = ?",
        (username,),
    ).fetchone()
    ledger_stats = conn.execute(
        """
        SELECT COUNT(*) AS event_count,
               COALESCE(SUM(amount_delta), 0) AS event_total
        FROM wallet_ledger WHERE username = ?
        """,
        (username,),
    ).fetchone()
    event_stats = conn.execute(
        """
        SELECT COUNT(*) AS event_count,
               COALESCE(SUM(amount_delta), 0) AS event_total,
               COALESCE(MAX(version), 0) AS max_version
        FROM wallet_balance_events WHERE username = ?
        """,
        (username,),
    ).fetchone()
    ledger_count = int(ledger_stats["event_count"] or 0)
    ledger_total = int(ledger_stats["event_total"] or 0)
    event_count = int(event_stats["event_count"] or 0)
    event_total = int(event_stats["event_total"] or 0)
    event_version = int(event_stats["max_version"] or 0)
    details = {
        "balance_present": balance_row is not None,
        "balance": (
            int(balance_row["balance"] or 0) if balance_row is not None else None
        ),
        "ledger_count": ledger_count,
        "ledger_total": ledger_total,
        "balance_event_count": event_count,
        "balance_event_total": event_total,
        "profile_balance": _wallet_int(profile.get("hackcoins", 0)),
    }

    if balance_row is not None:
        canonical_balance = int(balance_row["balance"] or 0)
        evidence_conflict = (
            canonical_balance < 0
            or (ledger_count > 0 and ledger_total != canonical_balance)
            or (event_count > 0 and event_total != canonical_balance)
        )
        initial_version = max(1, int(balance_row["version"] or 0))
    elif ledger_count or event_count:
        evidence_conflict = (
            ledger_count == 0
            or event_count == 0
            or ledger_total != event_total
            or ledger_total < 0
        )
        canonical_balance = ledger_total if not evidence_conflict else 0
        initial_version = max(1, event_version)
    else:
        evidence_conflict = False
        canonical_balance = max(0, _wallet_int(profile.get("hackcoins", 0)))
        initial_version = 1

    if evidence_conflict:
        _wallet_record_migration_blocked_with_conn(
            conn,
            username,
            row["profile_checksum"],
            "wallet_canonical_evidence_conflict",
            details,
        )
        return {
            "status": "blocked",
            "reason": "wallet_canonical_evidence_conflict",
            "details": details,
        }

    result = _wallet_seed_with_conn(
        conn,
        username,
        canonical_balance,
        source_checksum=row["profile_checksum"],
        source="wallet.bootstrap",
        initial_version=initial_version,
    )
    return {"status": "applied", **result}


def _wallet_register_with_conn(conn, username, profile, profile_checksum, created_at=None):
    balance = _wallet_int((profile or {}).get("hackcoins", 0))
    return _wallet_seed_with_conn(
        conn,
        username,
        balance,
        source_checksum=profile_checksum,
        source="wallet.registration",
        reset_existing=True,
        created_at=created_at,
    )


def _bootstrap_wallet_canonical_rows(conn):
    """One-way idempotent profile-to-wallet migration; never a read fallback."""
    rows = conn.execute(
        """
        SELECT u.username, u.profile_json, u.profile_revision,
               u.profile_checksum, u.profile_integrity_status
        FROM users AS u
        LEFT JOIN profile_store_migrations AS migration
          ON migration.migration_id = ?
         AND migration.username = u.username
         AND migration.status = 'applied'
        WHERE migration.username IS NULL
        ORDER BY u.id
        """,
        (WALLET_CANONICAL_MIGRATION_ID,),
    ).fetchall()
    for row in rows:
        _wallet_bootstrap_user_with_conn(conn, row)


def init_db(db_path=DB_PATH):
    with db_connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL DEFAULT '',
                salt TEXT NOT NULL DEFAULT '',
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS deleted_user_tombstones (
                username TEXT PRIMARY KEY,
                deleted_at TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT 'account_deleted',
                profile_revision INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        user_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        user_integrity_columns = {
            "profile_revision": "INTEGER NOT NULL DEFAULT 0",
            "profile_schema_version": "INTEGER NOT NULL DEFAULT 0",
            "profile_checksum": "TEXT NOT NULL DEFAULT ''",
            "profile_integrity_status": "TEXT NOT NULL DEFAULT 'uninitialized'",
            "profile_validation_version": "INTEGER NOT NULL DEFAULT 0",
        }
        for column_name, column_sql in user_integrity_columns.items():
            if column_name not in user_columns:
                conn.execute(
                    f"ALTER TABLE users ADD COLUMN {column_name} {column_sql}"
                )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_last_known_good (
                username TEXT PRIMARY KEY,
                profile_revision INTEGER NOT NULL,
                schema_version INTEGER NOT NULL,
                snapshot_json TEXT NOT NULL,
                checksum TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                validation_version INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_profile_lkg_revision
            ON profile_last_known_good(profile_revision, created_at)
            """
        )
        _bootstrap_profile_integrity_rows(conn)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS json_resources (
                key TEXT PRIMARY KEY,
                source_path TEXT NOT NULL DEFAULT '',
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'offline',
                created_at TEXT NOT NULL,
                UNIQUE(owner_username, contact_name)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                scope TEXT NOT NULL,
                peer_name TEXT NOT NULL DEFAULT '',
                sender TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
        }
        if "read_at" not in columns:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN read_at TEXT")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_messages_thread
            ON chat_messages(owner_username, scope, peer_name, id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_chat_messages_unread
            ON chat_messages(owner_username, scope, peer_name, read_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cyberner_world_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL UNIQUE,
                sender_username TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                client_message_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cyberner_world_messages_created
            ON cyberner_world_messages(id, created_at)
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_cyberner_world_messages_client
            ON cyberner_world_messages(sender_username, client_message_id)
            WHERE client_message_id IS NOT NULL
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cyberner_clan_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL UNIQUE,
                clan_key TEXT NOT NULL,
                sender_username TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                client_message_id TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cyberner_clan_messages_channel
            ON cyberner_clan_messages(clan_key, id)
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_cyberner_clan_messages_client
            ON cyberner_clan_messages(clan_key, sender_username, client_message_id)
            WHERE client_message_id IS NOT NULL
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cyberner_channel_cursors (
                username TEXT NOT NULL,
                channel_type TEXT NOT NULL,
                channel_key TEXT NOT NULL,
                last_read_message_id INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(username, channel_type, channel_key)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cyberner_channel_cursors_channel
            ON cyberner_channel_cursors(channel_type, channel_key, username)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mail_presence (
                username TEXT PRIMARY KEY,
                last_seen_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_username TEXT NOT NULL,
                to_username TEXT NOT NULL,
                amount INTEGER NOT NULL,
                transaction_key TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        wallet_transaction_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(wallet_transactions)"
            ).fetchall()
        }
        if "transaction_key" not in wallet_transaction_columns:
            conn.execute(
                "ALTER TABLE wallet_transactions "
                "ADD COLUMN transaction_key TEXT NOT NULL DEFAULT ''"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_hack_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_username TEXT NOT NULL,
                victim_username TEXT NOT NULL,
                hacked_until TEXT NOT NULL,
                cooldown_until TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(attacker_username, victim_username)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_hack_tool_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_id INTEGER,
                attacker_username TEXT NOT NULL,
                victim_username TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                access_key TEXT NOT NULL DEFAULT '',
                result TEXT NOT NULL DEFAULT '',
                amount INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(attacker_username, victim_username, tool_id, access_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_target_runtime (
                username TEXT PRIMARY KEY,
                target_key TEXT NOT NULL DEFAULT '',
                target_json TEXT NOT NULL DEFAULT '{}',
                security_json TEXT NOT NULL DEFAULT '{}',
                actions_allowed_json TEXT NOT NULL DEFAULT '{}',
                disarm_progress INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'cleared',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_target_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                event_type TEXT NOT NULL,
                target_key TEXT NOT NULL DEFAULT '',
                version INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_marked_targets (
                username TEXT NOT NULL,
                target_key TEXT NOT NULL,
                target_json TEXT NOT NULL DEFAULT '{}',
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                version INTEGER NOT NULL DEFAULT 1,
                source TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(username, target_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_marked_target_state (
                username TEXT PRIMARY KEY,
                source_revision INTEGER NOT NULL DEFAULT 0,
                migrated_count INTEGER NOT NULL DEFAULT 0,
                seeded_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_player_target_events_username_created
            ON player_target_events(username, created_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_player_marked_targets_user_status
            ON player_marked_targets(username, status, updated_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_positions (
                username TEXT PRIMARY KEY,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dev_bug_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'Other',
                severity TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'new',
                created_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                app_version TEXT NOT NULL DEFAULT '',
                current_url TEXT NOT NULL DEFAULT '',
                screen TEXT NOT NULL DEFAULT '',
                context_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS captured_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                icon TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT '',
                generated INTEGER NOT NULL DEFAULT 0,
                stationary INTEGER NOT NULL DEFAULT 1,
                target_json TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(owner_username, lat, lng, label)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                vertices_json TEXT NOT NULL,
                centroid_lat REAL,
                centroid_lng REAL,
                area_size REAL NOT NULL DEFAULT 0,
                max_edge_distance REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_area_publications (
                owner_username TEXT PRIMARY KEY,
                publication_version INTEGER NOT NULL DEFAULT 0,
                geometry_hash TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS area_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area_id INTEGER,
                owner_username TEXT NOT NULL,
                actor_username TEXT NOT NULL,
                event_type TEXT NOT NULL,
                lat REAL,
                lng REAL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conflict_key TEXT NOT NULL UNIQUE,
                conflict_id TEXT,
                legacy_conflict_key TEXT NOT NULL DEFAULT '',
                participant_key TEXT NOT NULL DEFAULT '',
                player_a_username TEXT NOT NULL,
                player_b_username TEXT NOT NULL,
                area_a_id INTEGER,
                area_b_id INTEGER,
                participants_json TEXT NOT NULL DEFAULT '[]',
                area_ids_json TEXT NOT NULL DEFAULT '[]',
                intersection_json TEXT NOT NULL DEFAULT '[]',
                intersections_json TEXT NOT NULL DEFAULT '[]',
                targets_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'active',
                conflict_version INTEGER NOT NULL DEFAULT 1,
                geometry_version INTEGER NOT NULL DEFAULT 1,
                geometry_status TEXT NOT NULL DEFAULT 'published',
                resolution_reason TEXT NOT NULL DEFAULT '',
                last_actor_username TEXT NOT NULL DEFAULT '',
                source_event TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                closed_at TEXT
            )
            """
        )
        conflict_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(territory_conflicts)").fetchall()
        }
        if "participants_json" not in conflict_columns:
            conn.execute("ALTER TABLE territory_conflicts ADD COLUMN participants_json TEXT NOT NULL DEFAULT '[]'")
        if "area_ids_json" not in conflict_columns:
            conn.execute("ALTER TABLE territory_conflicts ADD COLUMN area_ids_json TEXT NOT NULL DEFAULT '[]'")
        if "intersections_json" not in conflict_columns:
            conn.execute("ALTER TABLE territory_conflicts ADD COLUMN intersections_json TEXT NOT NULL DEFAULT '[]'")
        conflict_migration_columns = {
            "conflict_id": "TEXT",
            "legacy_conflict_key": "TEXT NOT NULL DEFAULT ''",
            "participant_key": "TEXT NOT NULL DEFAULT ''",
            "conflict_version": "INTEGER NOT NULL DEFAULT 1",
            "geometry_version": "INTEGER NOT NULL DEFAULT 1",
            "geometry_status": "TEXT NOT NULL DEFAULT 'published'",
            "resolution_reason": "TEXT NOT NULL DEFAULT ''",
            "resolved_at": "TEXT",
            "closed_at": "TEXT",
        }
        for column_name, column_sql in conflict_migration_columns.items():
            if column_name not in conflict_columns:
                conn.execute(
                    f"ALTER TABLE territory_conflicts ADD COLUMN {column_name} {column_sql}"
                )

        legacy_conflicts = conn.execute(
            """
            SELECT id, conflict_key, conflict_id, legacy_conflict_key,
                   participant_key, participants_json,
                   player_a_username, player_b_username, status,
                   resolution_reason, resolved_at, updated_at
            FROM territory_conflicts
            """
        ).fetchall()
        for row in legacy_conflicts:
            participants = loads_json(row["participants_json"], []) or [
                row["player_a_username"],
                row["player_b_username"],
            ]
            participants = sorted({str(item) for item in participants if item})
            participant_key = "::".join(participants)
            status = str(row["status"] or "active")
            resolution_reason = str(row["resolution_reason"] or "")
            if status == "resolved_by_encirclement":
                status = "resolved"
                resolution_reason = resolution_reason or "encirclement"
            resolved_at = row["resolved_at"]
            if status in {"resolved", "closed"} and not resolved_at:
                resolved_at = row["updated_at"]
            conn.execute(
                """
                UPDATE territory_conflicts
                SET conflict_id = ?,
                    legacy_conflict_key = ?,
                    participant_key = ?,
                    status = ?,
                    resolution_reason = ?,
                    resolved_at = ?
                WHERE id = ?
                """,
                (
                    str(row["conflict_id"] or row["id"]),
                    str(row["legacy_conflict_key"] or row["conflict_key"]),
                    str(row["participant_key"] or participant_key),
                    status,
                    resolution_reason,
                    resolved_at,
                    row["id"],
                ),
            )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_territory_conflicts_conflict_id "
            "ON territory_conflicts(conflict_id) WHERE conflict_id IS NOT NULL AND conflict_id != ''"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_territory_conflicts_participant_status "
            "ON territory_conflicts(participant_key, status, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_territory_conflicts_legacy_key "
            "ON territory_conflicts(legacy_conflict_key)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_pillars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conflict_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                front_id TEXT NOT NULL DEFAULT '',
                owner_username TEXT NOT NULL DEFAULT '',
                previous_owner_username TEXT NOT NULL DEFAULT '',
                attacker_username TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'contested',
                captured INTEGER NOT NULL DEFAULT 0,
                captured_by TEXT NOT NULL DEFAULT '',
                last_changed_version INTEGER NOT NULL DEFAULT 1,
                geometry_applied_version INTEGER NOT NULL DEFAULT 0,
                public_target_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                captured_at TEXT,
                UNIQUE(conflict_id, target_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflict_pillars_conflict "
            "ON territory_conflict_pillars(conflict_id, updated_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_events (
                event_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                conflict_id TEXT NOT NULL,
                target_id TEXT NOT NULL DEFAULT '',
                action_id TEXT NOT NULL DEFAULT '',
                conflict_version INTEGER NOT NULL,
                geometry_version INTEGER NOT NULL,
                actor_username TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflict_events_conflict "
            "ON territory_conflict_events(conflict_id, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_rebuilds (
                conflict_id TEXT PRIMARY KEY,
                requested_version INTEGER NOT NULL DEFAULT 0,
                processing_version INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                reason TEXT NOT NULL DEFAULT '',
                lease_owner TEXT NOT NULL DEFAULT '',
                lease_until TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                requested_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflict_rebuilds_status "
            "ON territory_conflict_rebuilds(status, lease_until, updated_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_fronts (
                front_id TEXT PRIMARY KEY,
                conflict_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                geometry_version INTEGER NOT NULL DEFAULT 0,
                participant_key TEXT NOT NULL DEFAULT '',
                area_ids_json TEXT NOT NULL DEFAULT '[]',
                pillar_ids_json TEXT NOT NULL DEFAULT '[]',
                geometry_json TEXT NOT NULL DEFAULT '[]',
                parent_front_ids_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                closed_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflict_fronts_conflict_status "
            "ON territory_conflict_fronts(conflict_id, status, updated_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                conflict_id TEXT NOT NULL,
                snapshot_version INTEGER NOT NULL,
                conflict_version INTEGER NOT NULL,
                geometry_version INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                UNIQUE(conflict_id, snapshot_version),
                UNIQUE(conflict_id, geometry_version)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflict_snapshots_latest "
            "ON territory_conflict_snapshots(conflict_id, snapshot_version DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_engagements (
                engagement_id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'detected',
                member_conflict_ids_json TEXT NOT NULL DEFAULT '[]',
                member_front_ids_json TEXT NOT NULL DEFAULT '[]',
                participant_usernames_json TEXT NOT NULL DEFAULT '[]',
                hostile_clan_groups_json TEXT NOT NULL DEFAULT '{}',
                geometry_json TEXT NOT NULL DEFAULT '[]',
                overlap_bbox_json TEXT NOT NULL DEFAULT '{}',
                engagement_version INTEGER NOT NULL DEFAULT 1,
                geometry_version INTEGER NOT NULL DEFAULT 1,
                snapshot_version INTEGER NOT NULL DEFAULT 1,
                missed_publications INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                resolved_at TEXT,
                closed_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflict_engagements_status "
            "ON territory_conflict_engagements(status, updated_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_engagement_members (
                engagement_id TEXT NOT NULL,
                conflict_id TEXT NOT NULL,
                front_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                joined_at TEXT NOT NULL,
                left_at TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (engagement_id, conflict_id, front_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conflict_engagement_members_source "
            "ON territory_conflict_engagement_members(conflict_id, front_id, status)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_engagement_coordinator (
                coordinator_key TEXT PRIMARY KEY,
                lease_owner TEXT NOT NULL DEFAULT '',
                lease_until TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_target_ownership (
                target_id TEXT PRIMARY KEY,
                owner_username TEXT NOT NULL,
                ownership_version INTEGER NOT NULL DEFAULT 1,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                target_json TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_target_capture_receipts (
                action_id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                attacker_username TEXT NOT NULL,
                expected_owner_username TEXT NOT NULL DEFAULT '',
                expected_version INTEGER,
                result TEXT NOT NULL,
                winner_username TEXT NOT NULL DEFAULT '',
                ownership_version INTEGER NOT NULL DEFAULT 0,
                set_id TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflict_reconciliation_sets (
                set_id TEXT PRIMARY KEY,
                target_id TEXT NOT NULL,
                winner_username TEXT NOT NULL,
                ownership_version INTEGER NOT NULL,
                conflict_ids_json TEXT NOT NULL DEFAULT '[]',
                engagement_ids_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                requested_version INTEGER NOT NULL DEFAULT 1,
                processing_version INTEGER NOT NULL DEFAULT 0,
                lease_owner TEXT NOT NULL DEFAULT '',
                lease_until REAL NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at REAL NOT NULL DEFAULT 0,
                processing_ms INTEGER NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                published_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_target_capture_receipts_target "
            "ON territory_target_capture_receipts(target_id, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_progression_receipts (
                receipt_id TEXT PRIMARY KEY,
                source_event_id TEXT NOT NULL UNIQUE,
                actor_username TEXT NOT NULL,
                target_id TEXT NOT NULL DEFAULT '',
                conflict_ids_json TEXT NOT NULL DEFAULT '[]',
                baseline_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                result_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                applied_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_territory_progression_pending "
            "ON territory_progression_receipts(actor_username, status, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reconciliation_sets_status "
            "ON territory_conflict_reconciliation_sets(status, lease_until, updated_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_rebuild_jobs (
                job_id TEXT PRIMARY KEY,
                owner_username TEXT NOT NULL,
                reason TEXT NOT NULL,
                target_id TEXT NOT NULL DEFAULT '',
                target_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                lease_owner TEXT NOT NULL DEFAULT '',
                lease_until REAL NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finished_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_territory_rebuild_jobs_status "
            "ON territory_rebuild_jobs(status, lease_until, updated_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ghostnetwork_territory_jobs (
                job_id TEXT PRIMARY KEY,
                job_kind TEXT NOT NULL,
                reference_id TEXT NOT NULL,
                source_version TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                lease_owner TEXT NOT NULL DEFAULT '',
                lease_until REAL NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finished_at TEXT
            )
            """
        )
        ghost_job_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(ghostnetwork_territory_jobs)").fetchall()
        }
        if "next_attempt_at" not in ghost_job_columns:
            conn.execute(
                "ALTER TABLE ghostnetwork_territory_jobs "
                "ADD COLUMN next_attempt_at REAL NOT NULL DEFAULT 0"
            )
        if "processing_ms" not in ghost_job_columns:
            conn.execute(
                "ALTER TABLE ghostnetwork_territory_jobs "
                "ADD COLUMN processing_ms INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ghostnetwork_territory_jobs_ready "
            "ON ghostnetwork_territory_jobs(status, next_attempt_at, lease_until, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ghostnetwork_delta_delivery_jobs (
                job_id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                cycle_id TEXT NOT NULL,
                event_json TEXT NOT NULL,
                viewers_json TEXT NOT NULL DEFAULT '[]',
                snapshot_json TEXT NOT NULL DEFAULT '{}',
                next_index INTEGER NOT NULL DEFAULT 0,
                published_count INTEGER NOT NULL DEFAULT 0,
                skipped_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                lease_owner TEXT NOT NULL DEFAULT '',
                lease_until REAL NOT NULL DEFAULT 0,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at REAL NOT NULL DEFAULT 0,
                processing_ms INTEGER NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                finished_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ghostnetwork_delta_delivery_ready "
            "ON ghostnetwork_delta_delivery_jobs(status, next_attempt_at, lease_until, created_at)"
        )
        ghost_delivery_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(ghostnetwork_delta_delivery_jobs)"
            ).fetchall()
        }
        if "snapshot_json" not in ghost_delivery_columns:
            conn.execute(
                "ALTER TABLE ghostnetwork_delta_delivery_jobs "
                "ADD COLUMN snapshot_json TEXT NOT NULL DEFAULT '{}'"
            )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_reconciliation_snapshot_gates (
                set_id TEXT NOT NULL,
                conflict_id TEXT NOT NULL,
                public_snapshot_version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                PRIMARY KEY(set_id, conflict_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reconciliation_snapshot_gates_conflict "
            "ON territory_reconciliation_snapshot_gates(conflict_id, set_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reported_vulnerabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_lat REAL NOT NULL,
                target_lng REAL NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                icon TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT '',
                generated INTEGER NOT NULL DEFAULT 0,
                reported_by_username TEXT NOT NULL,
                reported_by_clan TEXT NOT NULL DEFAULT '',
                territory_owner_username TEXT NOT NULL DEFAULT '',
                territory_owner_clan TEXT NOT NULL DEFAULT '',
                security_json TEXT NOT NULL DEFAULT '{}',
                target_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_state_deltas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                version INTEGER NOT NULL,
                scope TEXT NOT NULL,
                type TEXT NOT NULL,
                entity_id TEXT NOT NULL DEFAULT '',
                dedupe_key TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(username, dedupe_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_action_receipts (
                receipt_key TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                app_id TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL DEFAULT '',
                target_key TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                response_json TEXT NOT NULL DEFAULT '{}',
                status_code INTEGER NOT NULL DEFAULT 202,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at REAL NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_operations (
                operation_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                target_key TEXT NOT NULL DEFAULT '',
                operation_type TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                operation_json TEXT NOT NULL DEFAULT '{}',
                risk_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_events (
                event_id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                dedupe_key TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_operation_events_dedupe
            ON operation_events(dedupe_key)
            WHERE dedupe_key != ''
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_messages (
                message_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                dedupe_key TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                type TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                expires_at REAL NOT NULL DEFAULT 0,
                consumed_at TEXT
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(system_messages)").fetchall()
        }
        if "expires_at" not in columns:
            conn.execute("ALTER TABLE system_messages ADD COLUMN expires_at REAL NOT NULL DEFAULT 0")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_system_messages_dedupe
            ON system_messages(username, dedupe_key)
            WHERE dedupe_key != ''
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_captured_targets_owner ON captured_targets(owner_username)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_areas_owner ON player_areas(owner_username)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_area_events_owner ON area_events(owner_username, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_territory_conflicts_players ON territory_conflicts(player_a_username, player_b_username, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reported_vulnerabilities_clan_status ON reported_vulnerabilities(reported_by_clan, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reported_vulnerabilities_target ON reported_vulnerabilities(target_lat, target_lng, label, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wallet_transactions_users ON wallet_transactions(from_username, to_username, created_at)"
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_transactions_key
            ON wallet_transactions(transaction_key)
            WHERE transaction_key != ''
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_hack_access_pair ON player_hack_access(attacker_username, victim_username, hacked_until, cooldown_until)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_hack_tool_usage_pair ON player_hack_tool_usage(attacker_username, victim_username, tool_id, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_dev_bug_reports_status ON dev_bug_reports(status, category, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_game_state_deltas_user_version ON game_state_deltas(username, version)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_game_state_deltas_created_at ON game_state_deltas(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_action_receipts_user_updated ON app_action_receipts(username, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_action_receipts_expires_at ON app_action_receipts(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_operations_user_status ON player_operations(username, status, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_operations_target ON player_operations(username, target_key)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_operation_events_operation ON operation_events(operation_id, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_system_messages_user_status ON system_messages(username, status, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_apps (
                username TEXT NOT NULL,
                app_id TEXT NOT NULL,
                app_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'installed',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(username, app_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_tool_files (
                username TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                app_id TEXT NOT NULL DEFAULT '',
                tool_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(username, tool_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_storage (
                username TEXT PRIMARY KEY,
                capacity INTEGER NOT NULL DEFAULT 0,
                used INTEGER NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'MB',
                modifiers_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_balances (
                username TEXT PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_balance_events (
                event_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                transaction_key TEXT NOT NULL DEFAULT '',
                amount_delta INTEGER NOT NULL DEFAULT 0,
                balance INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 0,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        wallet_balance_event_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(wallet_balance_events)"
            ).fetchall()
        }
        if "version" not in wallet_balance_event_columns:
            conn.execute(
                "ALTER TABLE wallet_balance_events "
                "ADD COLUMN version INTEGER NOT NULL DEFAULT 0"
            )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_balance_events_key
            ON wallet_balance_events(username, transaction_key)
            WHERE transaction_key != ''
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_ledger (
                ledger_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                event_type TEXT NOT NULL,
                amount_delta INTEGER NOT NULL DEFAULT 0,
                balance_after INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT '',
                source_id TEXT NOT NULL DEFAULT '',
                peer_username TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                dedupe_key TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_ledger_dedupe
            ON wallet_ledger(username, dedupe_key)
            WHERE dedupe_key != ''
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_created ON wallet_ledger(username, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_apps_user_status ON player_apps(username, status, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_tool_files_user_app ON player_tool_files(username, app_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_store_migrations (
                migration_id TEXT NOT NULL,
                username TEXT NOT NULL,
                status TEXT NOT NULL,
                source_checksum TEXT,
                result_checksum TEXT,
                started_at TEXT,
                completed_at TEXT,
                error_json TEXT,
                backup_json TEXT,
                tool_version TEXT NOT NULL,
                PRIMARY KEY(migration_id, username)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_profile_store_migrations_status
            ON profile_store_migrations(migration_id, status)
            """
        )
        _bootstrap_wallet_canonical_rows(conn)


_IDENTITY_ORPHAN_COLUMNS = {
    # Canonical economy/inventory rows must never be inherited by a newly
    # registered account which happens to reuse an old login.
    "wallet_balances": ("username",),
    "wallet_balance_events": ("username",),
    "wallet_ledger": ("username", "peer_username"),
    "wallet_transactions": ("from_username", "to_username"),
    "player_apps": ("username",),
    "player_tool_files": ("username",),
    "player_storage": ("username",),
    # Durable gameplay ownership and runtime projections.
    "captured_targets": ("owner_username",),
    "player_areas": ("owner_username",),
    "territory_area_publications": ("owner_username",),
    "player_target_runtime": ("username",),
    "player_target_events": ("username",),
    "player_positions": ("username",),
    "player_operations": ("username",),
    "system_messages": ("username",),
    "game_state_deltas": ("username",),
    # GhostNetwork history is deliberately retained across account deletion;
    # its presence therefore blocks identity reuse instead of being cleaned.
    "ghost_part_reservations": ("player_id",),
    "ghost_part_events": ("player_id",),
    "ghost_capture_effects": ("player_id",),
    "ghost_contributions": ("player_id",),
    "ghost_reward_ledger": ("player_id",),
    "ghost_achievements": ("player_id",),
}


def _identity_reuse_block_reason_with_conn(conn, username, *, include_user=True):
    username = str(username or "").strip()
    if not username:
        return "username_missing"
    if include_user and conn.execute(
        "SELECT 1 FROM users WHERE username = ?",
        (username,),
    ).fetchone():
        return "identity_exists"
    if conn.execute(
        "SELECT 1 FROM deleted_user_tombstones WHERE username = ?",
        (username,),
    ).fetchone():
        return "identity_tombstoned"

    existing_tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    for table_name, candidate_columns in _IDENTITY_ORPHAN_COLUMNS.items():
        if table_name not in existing_tables:
            continue
        available_columns = {
            row["name"]
            for row in conn.execute(
                f'PRAGMA table_info("{table_name}")'
            ).fetchall()
        }
        columns = [
            column for column in candidate_columns if column in available_columns
        ]
        if not columns:
            continue
        where = " OR ".join(f'"{column}" = ?' for column in columns)
        if conn.execute(
            f'SELECT 1 FROM "{table_name}" WHERE {where} LIMIT 1',
            tuple(username for _column in columns),
        ).fetchone():
            return f"canonical_orphan:{table_name}"
    return ""


class UserStore:
    def __init__(self, db_path=DB_PATH, seed_path=USERS_SEED_PATH):
        self.db_path = db_path
        self.seed_path = seed_path
        init_db(self.db_path)
        self.seed_from_json_if_empty()

    def seed_from_json_if_empty(self):
        with db_connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
            if row["count"] > 0 or not os.path.exists(self.seed_path):
                return

            with open(self.seed_path, "r", encoding="utf-8") as f:
                users = json.load(f)

            now = utc_now()
            for profile in users:
                username = profile.get("username")
                if not username:
                    continue
                if _identity_reuse_block_reason_with_conn(conn, username):
                    continue
                ensure_password_hash(profile)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users
                        (username, password, salt, profile_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        profile.get("password", ""),
                        profile.get("salt", ""),
                        dumps_json(profile),
                        now,
                        now,
                    ),
                )
            _bootstrap_profile_integrity_rows(conn)
            _bootstrap_wallet_canonical_rows(conn)

    def _record_recovery_required(self, username, revision, source, errors):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE users
                SET profile_integrity_status = ?, profile_validation_version = ?
                WHERE username = ? AND profile_revision = ?
                """,
                (
                    PROFILE_INTEGRITY_RECOVERY_REQUIRED,
                    PROFILE_VALIDATION_VERSION,
                    username,
                    int(revision or 0),
                ),
            )
        _profile_event(
            "profile.recovery_required",
            username,
            source,
            old_revision=int(revision or 0),
            candidate_revision=None,
            changed_scopes=[],
            decision="rejected",
            reason_code=":".join(str(item) for item in (errors or ())),
            session_generation_hash="",
            request_id="",
        )

    def list_profiles(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute("SELECT profile_json FROM users ORDER BY id").fetchall()
            return [loads_json(row["profile_json"], {}) for row in rows]

    def list_profile_entries(self):
        """Return profile identities without requiring one query per user."""
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT username, profile_json FROM users ORDER BY id"
            ).fetchall()
            return [
                (row["username"], loads_json(row["profile_json"], {}))
                for row in rows
                if row["username"]
            ]

    def list_usernames(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute("SELECT username FROM users ORDER BY id").fetchall()
            return [row["username"] for row in rows if row["username"]]

    def has_user(self, username):
        if not username:
            return False
        with db_connect(self.db_path) as conn:
            return conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,),
            ).fetchone() is not None

    def list_usernames_by_clan(self, clan_key):
        clan_key = str(clan_key or "").strip()
        if not clan_key:
            return []
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT username, profile_json FROM users ORDER BY id"
            ).fetchall()
        usernames = []
        for row in rows:
            profile = loads_json(row["profile_json"], {})
            profile_clan = str(
                profile.get("clan_id")
                or profile.get("clan")
                or profile.get("clan_name")
                or ""
            ).strip()
            if profile_clan == clan_key and row["username"]:
                usernames.append(row["username"])
        return usernames

    def get_profile(self, username):
        """Return the runtime profile without running the forensic integrity pass.

        Guarded writers establish the revision/checksum/LKG contract. Runtime
        readers still fail closed for malformed JSON, a wrong identity or a row
        explicitly marked for recovery, but checksum and full schema validation
        remain the responsibility of get_profile_with_revision().
        """
        username = str(username or "").strip()
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT profile_json, profile_revision, profile_integrity_status
                FROM users WHERE username = ?
                """,
                (username,),
            ).fetchone()
        if not row:
            return None
        raw_profile = row["profile_json"]
        record_hot_path_metric(
            "profile_bytes",
            len(str(raw_profile or "").encode("utf-8", errors="ignore")),
        )
        profile, parse_errors = _parse_profile_json_strict(raw_profile)
        errors = list(parse_errors)
        if str(row["profile_integrity_status"] or "") != PROFILE_INTEGRITY_VALID:
            errors.append("profile_integrity_status_invalid")
        if isinstance(profile, dict) and str(profile.get("username") or "").strip() != username:
            errors.append("username_mismatch")
        if errors:
            _profile_event(
                "profile.recovery_required",
                username,
                "get_profile",
                old_revision=int(row["profile_revision"] or 0),
                candidate_revision=None,
                changed_scopes=[],
                decision="rejected",
                reason_code=":".join(sorted(set(errors))),
                session_generation_hash="",
                request_id="",
            )
            raise ProfileRecoveryRequired(
                f"User '{username}' requires profile recovery."
            )
        return profile

    def get_profile_with_revision(self, username):
        """Return the durable profile and the CAS metadata read with it."""
        username = str(username or "").strip()
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT profile_json, profile_revision, profile_schema_version,
                       profile_checksum, profile_integrity_status,
                       profile_validation_version, updated_at
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        if not row:
            return None
        record_hot_path_metric("profile_full_read")
        record_hot_path_metric(
            "profile_bytes",
            len(str(row["profile_json"] or "").encode("utf-8", errors="ignore")),
        )
        profile, parse_errors = _parse_profile_json_strict(row["profile_json"])
        validation = (
            validate_profile_candidate(profile, username)
            if profile is not None
            else {"valid": False, "errors": parse_errors}
        )
        stored_checksum = str(row["profile_checksum"] or "")
        checksum_valid = bool(profile is not None and stored_checksum) and (
            profile_payload_checksum(profile) == stored_checksum
        )
        errors = list(validation.get("errors") or parse_errors)
        integrity_status = str(row["profile_integrity_status"] or "")
        if "invalid_json" in parse_errors:
            state = "invalid_json"
        elif profile is None or errors:
            state = "invalid_schema"
        elif integrity_status != PROFILE_INTEGRITY_VALID or not checksum_valid:
            state = "recovery_required"
        else:
            state = "valid"
        if integrity_status != PROFILE_INTEGRITY_VALID:
            errors.append("profile_integrity_status_invalid")
        if not checksum_valid:
            errors.append("profile_checksum_mismatch")
        return {
            "state": state,
            "profile": copy.deepcopy(profile) if profile is not None else None,
            "profile_revision": int(row["profile_revision"] or 0),
            "schema_version": int(row["profile_schema_version"] or 0),
            "checksum": stored_checksum,
            "checksum_valid": checksum_valid,
            "integrity_status": integrity_status,
            "validation_version": int(row["profile_validation_version"] or 0),
            "updated_at": row["updated_at"],
            "errors": tuple(sorted(set(errors))),
        }

    def get_last_known_good(self, username):
        username = str(username or "").strip()
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT username, profile_revision, schema_version, snapshot_json,
                       checksum, source, created_at, validation_version
                FROM profile_last_known_good
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        if not row:
            return None
        snapshot, parse_errors = _parse_profile_json_strict(row["snapshot_json"])
        computed_checksum = ""
        if snapshot is not None:
            computed_checksum = hashlib.sha256(
                _canonical_json(snapshot).encode("utf-8")
            ).hexdigest()
        stored_checksum = str(row["checksum"] or "")
        return {
            "username": row["username"],
            "profile_revision": int(row["profile_revision"]),
            "schema_version": int(row["schema_version"]),
            "snapshot": copy.deepcopy(snapshot) if snapshot is not None else None,
            "checksum": stored_checksum,
            "checksum_valid": bool(stored_checksum) and stored_checksum == computed_checksum,
            "source": row["source"],
            "created_at": row["created_at"],
            "validation_version": int(row["validation_version"]),
            "errors": tuple(parse_errors),
        }

    def patch_profile_guarded(
        self,
        username,
        updates,
        source,
        expected_revision=None,
        precommit_guard=None,
        reset_receipt=None,
        request_id="",
        session_generation_hash="",
    ):
        """Apply a validated top-level patch with a short CAS writer section."""
        username = str(username or "").strip()
        source = str(source or "").strip()
        if not username:
            raise ProfileValidationError(("username_missing",))
        if not source:
            raise ValueError("A guarded profile patch requires source.")
        if not isinstance(updates, dict):
            raise TypeError("updates must be a top-level mapping.")
        record_hot_path_metric("profile_full_write")
        if expected_revision is not None and (
            isinstance(expected_revision, bool) or not isinstance(expected_revision, int)
        ):
            raise ValueError("expected_revision must be an integer or None.")
        forbidden_keys = {
            "username", "password", "salt",
        }.union(_PROFILE_INTERNAL_KEYS)
        rejected_keys = sorted(str(key) for key in set(updates).intersection(forbidden_keys))
        if rejected_keys:
            raise ProfileValidationError(
                tuple(f"protected_patch_key:{key}" for key in rejected_keys)
            )

        telemetry = {
            "old_revision": None,
            "candidate_revision": None,
            "changed_scopes": [],
            "decision": "attempt",
            "reason_code": "",
            "request_id": str(request_id or "")[:80],
            "session_generation_hash": str(session_generation_hash or "")[:80],
        }
        _profile_event("profile.write_attempt", username, source, **telemetry)
        recovery_errors = ()
        try:
            prepared = None
            max_attempts = 3 if expected_revision is None else 1
            for attempt in range(max_attempts):
                # Parse, overlay, validate, checksum and serialize before taking
                # SQLite's process-wide writer lock. The revision/checksum pair
                # observed here is rechecked under BEGIN IMMEDIATE below.
                with db_connect(self.db_path) as read_conn:
                    row = read_conn.execute(
                        """
                        SELECT username, password, salt, profile_json,
                               profile_revision, profile_checksum,
                               profile_integrity_status
                        FROM users WHERE username = ?
                        """,
                        (username,),
                    ).fetchone()
                    if row is None:
                        raise ProfileWriteConflict("Profile does not exist.")
                    current_revision = int(row["profile_revision"] or 0)
                    telemetry["old_revision"] = current_revision
                    if expected_revision is not None and expected_revision != current_revision:
                        raise ProfileWriteConflict(
                            f"Expected profile revision {expected_revision}, current is {current_revision}."
                        )
                    record_hot_path_metric("profile_full_read")
                    record_hot_path_metric(
                        "profile_bytes",
                        len(str(row["profile_json"] or "").encode("utf-8", errors="ignore")),
                    )
                    current_profile, recovery_errors = _validate_persisted_profile_row(
                        row, username
                    )
                    if recovery_errors:
                        raise ProfileRecoveryRequired(
                            "Current profile requires recovery: "
                            + ",".join(recovery_errors)
                        )

                    candidate = copy.deepcopy(current_profile)
                    for key, value in updates.items():
                        candidate[str(key)] = copy.deepcopy(value)
                    candidate, canonical_overlays = overlay_canonical_profile_scopes_with_conn(
                        read_conn, username, candidate
                    )

                validation = validate_profile_candidate(candidate, username)
                if not validation["valid"]:
                    raise ProfileValidationError(validation["errors"])
                changed_scopes = profile_changed_scopes(current_profile, candidate)
                telemetry["changed_scopes"] = list(changed_scopes)
                destructive = assess_profile_destructive_drop(current_profile, candidate)
                reset_authorized_source = source.startswith(("admin.", "recovery."))
                if destructive["destructive"] and not (
                    reset_authorized_source and _valid_reset_receipt(reset_receipt)
                ):
                    raise ProfileDestructiveWriteRejected(
                        "Destructive profile patch requires an explicit reset receipt; "
                        "scopes=" + ",".join(destructive["dropped_scopes"])
                    )

                now = utc_now()
                revision = current_revision + 1
                checksum = profile_payload_checksum(candidate)
                candidate_json = dumps_json(candidate)
                prepared_lkg = _prepare_profile_lkg(current_profile)
                observed_checksum = str(row["profile_checksum"] or "")
                retry = False

                with db_connect(self.db_path) as conn:
                    conn.execute("BEGIN IMMEDIATE")
                    locked_row = conn.execute(
                        """
                        SELECT profile_revision, profile_checksum,
                               profile_integrity_status
                        FROM users WHERE username = ?
                        """,
                        (username,),
                    ).fetchone()
                    locked_revision = int(locked_row["profile_revision"] or 0) if locked_row else -1
                    if (
                        locked_row is None
                        or locked_revision != current_revision
                        or str(locked_row["profile_checksum"] or "") != observed_checksum
                        or str(locked_row["profile_integrity_status"] or "")
                           != PROFILE_INTEGRITY_VALID
                    ):
                        retry = expected_revision is None and attempt + 1 < max_attempts
                        if not retry:
                            raise ProfileWriteConflict(
                                "Profile revision changed before the guarded patch committed."
                            )
                    else:
                        _run_profile_precommit_guard(
                            precommit_guard, conn, username, current_revision
                        )
                        updated = conn.execute(
                            """
                            UPDATE users
                            SET password = ?, salt = ?, profile_json = ?, updated_at = ?,
                                profile_revision = ?, profile_schema_version = ?,
                                profile_checksum = ?, profile_integrity_status = ?,
                                profile_validation_version = ?
                            WHERE username = ? AND profile_revision = ?
                            """,
                            (
                                candidate.get("password", ""),
                                candidate.get("salt", ""),
                                candidate_json,
                                now,
                                revision,
                                PROFILE_SCHEMA_VERSION,
                                checksum,
                                PROFILE_INTEGRITY_VALID,
                                PROFILE_VALIDATION_VERSION,
                                username,
                                current_revision,
                            ),
                        )
                        if updated.rowcount != 1:
                            raise ProfileWriteConflict(
                                "Profile revision changed before the guarded patch committed."
                            )
                        _write_profile_lkg(
                            conn,
                            username,
                            current_profile,
                            current_revision,
                            f"prewrite:{source}",
                            now,
                            prepared=prepared_lkg,
                        )
                if retry:
                    continue
                prepared = (
                    candidate, revision, checksum, canonical_overlays, destructive
                )
                break

            if prepared is None:
                raise ProfileWriteConflict(
                    "Profile kept changing while the guarded patch was prepared."
                )
            candidate, revision, checksum, canonical_overlays, destructive = prepared
            telemetry.update({
                "candidate_revision": revision,
                "decision": "applied",
                "reason_code": (
                    "reset_receipt" if destructive["destructive"] else "validated_patch"
                ),
            })
            _profile_event("profile.write_applied", username, source, **telemetry)
            _profile_event("profile.lkg_created", username, source, **telemetry)
            return {
                "applied": True,
                "profile": copy.deepcopy(candidate),
                "profile_revision": revision,
                "schema_version": PROFILE_SCHEMA_VERSION,
                "checksum": checksum,
                "integrity_status": PROFILE_INTEGRITY_VALID,
                "changed_scopes": tuple(telemetry["changed_scopes"]),
                "canonical_overlays": tuple(canonical_overlays),
            }
        except ProfileWriteError as exc:
            telemetry.update({
                "decision": "rejected",
                "reason_code": exc.__class__.__name__,
            })
            _profile_event("profile.write_rejected", username, source, **telemetry)
            if isinstance(exc, ProfileRecoveryRequired):
                self._record_recovery_required(
                    username,
                    telemetry.get("old_revision"),
                    source,
                    recovery_errors or ("profile_recovery_required",),
                )
            raise

    def save_profile_guarded(
        self,
        profile,
        *,
        expected_revision,
        source,
        allow_create=False,
        reset_receipt=None,
        request_id="",
        session_generation_hash="",
        precommit_guard=None,
    ):
        """Atomically validate and save a complete profile under revision CAS."""
        candidate_input = copy.deepcopy(profile if isinstance(profile, dict) else {})
        username = str(candidate_input.get("username") or "").strip()
        source = str(source or "").strip()
        if not source:
            raise ValueError("A guarded profile write requires source.")
        record_hot_path_metric("profile_full_write")
        if not username:
            raise ProfileValidationError(("username_missing",))
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int):
            raise ValueError("expected_revision must be an integer.")

        telemetry = {
            "old_revision": None,
            "candidate_revision": None,
            "changed_scopes": [],
            "decision": "attempt",
            "reason_code": "",
            "request_id": str(request_id or "")[:80],
            "session_generation_hash": str(session_generation_hash or "")[:80],
        }
        _profile_event("profile.write_attempt", username, source, **telemetry)

        try:
            canonical_overlays = ()
            with db_connect(self.db_path) as read_conn:
                current_row = read_conn.execute(
                    """
                    SELECT username, password, salt, profile_json,
                           profile_revision, profile_schema_version,
                           profile_checksum, profile_integrity_status
                    FROM users
                    WHERE username = ?
                    """,
                    (username,),
                ).fetchone()

                if current_row is not None:
                    record_hot_path_metric("profile_full_read")
                    record_hot_path_metric(
                        "profile_bytes",
                        len(str(current_row["profile_json"] or "").encode("utf-8", errors="ignore")),
                    )
                    current_revision = int(current_row["profile_revision"] or 0)
                    telemetry["old_revision"] = current_revision
                    if expected_revision != current_revision:
                        raise ProfileWriteConflict(
                            f"Expected profile revision {expected_revision}, current is {current_revision}."
                        )
                    if current_row["profile_integrity_status"] != PROFILE_INTEGRITY_VALID:
                        raise ProfileRecoveryRequired(
                            "Current profile is not marked valid; normal writes are disabled."
                        )
                    current_profile, parse_errors = _parse_profile_json_strict(
                        current_row["profile_json"]
                    )
                    current_validation = (
                        validate_profile_candidate(current_profile, username)
                        if current_profile is not None
                        else {"valid": False, "errors": parse_errors}
                    )
                    if not current_validation["valid"]:
                        raise ProfileRecoveryRequired(
                            "Current profile failed validation: "
                            + ", ".join(current_validation["errors"])
                        )
                    actual_checksum = profile_payload_checksum(current_profile)
                    observed_checksum = str(current_row["profile_checksum"] or "")
                    if actual_checksum != observed_checksum:
                        raise ProfileRecoveryRequired(
                            "Current profile checksum does not match its metadata."
                        )

                    candidate = _prepare_full_profile_candidate(
                        candidate_input, current_row=current_row
                    )
                    candidate, canonical_overlays = overlay_canonical_profile_scopes_with_conn(
                        read_conn, username, candidate
                    )
                else:
                    if not allow_create or expected_revision != 0:
                        raise ProfileWriteConflict(
                            "Profile does not exist; guarded creation requires "
                            "allow_create=True and expected_revision=0."
                        )
                    current_revision = 0
                    current_profile = None
                    observed_checksum = ""
                    candidate = _prepare_full_profile_candidate(candidate_input)

            validation = validate_profile_candidate(candidate, username)
            if not validation["valid"]:
                raise ProfileValidationError(validation["errors"])
            changed_scopes = profile_changed_scopes(current_profile or {}, candidate)
            telemetry["changed_scopes"] = list(changed_scopes)
            destructive = assess_profile_destructive_drop(current_profile or {}, candidate)
            reset_authorized_source = source.startswith(("admin.", "recovery."))
            if current_profile is not None and destructive["destructive"] and not (
                reset_authorized_source and _valid_reset_receipt(reset_receipt)
            ):
                raise ProfileDestructiveWriteRejected(
                    "Destructive profile drop requires an explicit reset receipt; "
                    "scopes=" + ",".join(destructive["dropped_scopes"])
                )

            now = utc_now()
            revision = current_revision + 1
            checksum = profile_payload_checksum(candidate)
            candidate_json = dumps_json(candidate)
            prepared_lkg = _prepare_profile_lkg(
                current_profile if current_profile is not None else candidate
            )

            with db_connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                locked_row = conn.execute(
                    """
                    SELECT profile_revision, profile_checksum,
                           profile_integrity_status
                    FROM users WHERE username = ?
                    """,
                    (username,),
                ).fetchone()

                if current_profile is None:
                    if locked_row is not None:
                        raise ProfileWriteConflict(
                            "Profile was created before the guarded insert committed."
                        )
                    reuse_block = _identity_reuse_block_reason_with_conn(
                        conn,
                        username,
                        include_user=False,
                    )
                    if reuse_block:
                        raise ProfileWriteConflict(
                            "Identity cannot be reused: " + reuse_block
                        )
                    # Registration never inherits orphan canonical rows from a
                    # previously deleted account with the same login. Canonical
                    # stores are seeded by their explicit registration/migration
                    # path after the identity row has been created.
                    _run_profile_precommit_guard(
                        precommit_guard, conn, username, 0
                    )
                    conn.execute(
                        """
                        INSERT INTO users (
                            username, password, salt, profile_json, created_at, updated_at,
                            profile_revision, profile_schema_version, profile_checksum,
                            profile_integrity_status, profile_validation_version
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            username,
                            candidate.get("password", ""),
                            candidate.get("salt", ""),
                            candidate_json,
                            now,
                            now,
                            revision,
                            PROFILE_SCHEMA_VERSION,
                            checksum,
                            PROFILE_INTEGRITY_VALID,
                            PROFILE_VALIDATION_VERSION,
                        ),
                    )
                    _write_profile_lkg(
                        conn, username, candidate, revision, f"create:{source}", now,
                        prepared=prepared_lkg,
                    )
                    _wallet_register_with_conn(
                        conn, username, candidate, checksum, created_at=now
                    )
                    telemetry.update({
                        "old_revision": 0,
                        "candidate_revision": revision,
                        "changed_scopes": list(profile_changed_scopes({}, candidate)),
                        "decision": "applied",
                        "reason_code": "created",
                    })
                else:
                    locked_revision = int(locked_row["profile_revision"] or 0) if locked_row else -1
                    if (
                        locked_row is None
                        or locked_revision != current_revision
                        or str(locked_row["profile_checksum"] or "") != observed_checksum
                    ):
                        raise ProfileWriteConflict(
                            "Profile revision changed before the guarded write committed."
                        )
                    if locked_row["profile_integrity_status"] != PROFILE_INTEGRITY_VALID:
                        raise ProfileRecoveryRequired(
                            "Current profile is not marked valid; normal writes are disabled."
                        )
                    _run_profile_precommit_guard(
                        precommit_guard, conn, username, current_revision
                    )
                    _write_profile_lkg(
                        conn,
                        username,
                        current_profile,
                        current_revision,
                        f"prewrite:{source}",
                        now,
                        prepared=prepared_lkg,
                    )
                    updated = conn.execute(
                        """
                        UPDATE users
                        SET password = ?, salt = ?, profile_json = ?, updated_at = ?,
                            profile_revision = ?, profile_schema_version = ?,
                            profile_checksum = ?, profile_integrity_status = ?,
                            profile_validation_version = ?
                        WHERE username = ? AND profile_revision = ?
                        """,
                        (
                            candidate.get("password", ""),
                            candidate.get("salt", ""),
                            candidate_json,
                            now,
                            revision,
                            PROFILE_SCHEMA_VERSION,
                            checksum,
                            PROFILE_INTEGRITY_VALID,
                            PROFILE_VALIDATION_VERSION,
                            username,
                            expected_revision,
                        ),
                    )
                    if updated.rowcount != 1:
                        raise ProfileWriteConflict(
                            "Profile revision changed before the guarded write committed."
                        )
                    telemetry.update({
                        "candidate_revision": revision,
                        "decision": "applied",
                        "reason_code": (
                            "reset_receipt" if destructive["destructive"] else "validated"
                        ),
                    })

            _profile_event("profile.write_applied", username, source, **telemetry)
            _profile_event(
                "profile.lkg_created",
                username,
                source,
                old_revision=telemetry["old_revision"],
                candidate_revision=telemetry["candidate_revision"],
                changed_scopes=telemetry["changed_scopes"],
                decision="applied",
                reason_code=telemetry["reason_code"],
                request_id=telemetry["request_id"],
                session_generation_hash=telemetry["session_generation_hash"],
            )
            return {
                "applied": True,
                "profile": copy.deepcopy(candidate),
                "profile_revision": int(telemetry["candidate_revision"]),
                "schema_version": PROFILE_SCHEMA_VERSION,
                "checksum": checksum,
                "integrity_status": PROFILE_INTEGRITY_VALID,
                "changed_scopes": tuple(telemetry["changed_scopes"]),
                "canonical_overlays": tuple(canonical_overlays),
            }
        except ProfileWriteError as exc:
            telemetry.update({
                "decision": "rejected",
                "reason_code": exc.__class__.__name__,
            })
            _profile_event("profile.write_rejected", username, source, **telemetry)
            if isinstance(exc, ProfileRecoveryRequired):
                try:
                    with db_connect(self.db_path) as recovery_conn:
                        recovery_conn.execute(
                            """
                            UPDATE users
                            SET profile_integrity_status = ?,
                                profile_validation_version = ?
                            WHERE username = ? AND profile_revision = ?
                            """,
                            (
                                PROFILE_INTEGRITY_RECOVERY_REQUIRED,
                                PROFILE_VALIDATION_VERSION,
                                username,
                                telemetry.get("old_revision"),
                            ),
                        )
                except sqlite3.Error:
                    # The original controlled failure remains authoritative;
                    # observability must not hide it behind a metadata retry.
                    pass
                _profile_event("profile.recovery_required", username, source, **telemetry)
            raise

    def list_profile_identities(self):
        """Return only identity fields needed by territory publication."""
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT username,
                          json_extract(profile_json, '$.ghost_clan_code') AS ghost_clan_code,
                          json_extract(profile_json, '$.clan_code') AS clan_code,
                          json_extract(profile_json, '$.ghost_clan') AS ghost_clan,
                          json_extract(profile_json, '$.clan_id') AS clan_id,
                          json_extract(profile_json, '$.clan') AS clan,
                          json_extract(profile_json, '$.clan_name') AS clan_name,
                          json_extract(profile_json, '$.fraction') AS fraction,
                          json_extract(profile_json, '$.faction') AS faction,
                          json_extract(profile_json, '$.ghost_profession') AS ghost_profession,
                          json_extract(profile_json, '$.profession') AS profession
                   FROM users"""
            ).fetchall()
        return [(row["username"], dict(row)) for row in rows]

    def get_profile_identity(self, username):
        """Return the small, integrity-gated identity projection for hot read paths.

        The durable integrity metadata is established by guarded profile writes.
        Snapshot endpoints must not parse, validate, copy and overlay the complete
        profile merely to learn the viewer's clan and profession.
        """
        username = str(username or "").strip()
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT username, profile_revision, profile_checksum,
                       profile_integrity_status,
                       json_valid(profile_json) AS profile_json_valid,
                       CASE WHEN json_valid(profile_json)
                            THEN json_type(profile_json) END AS profile_json_type,
                       CASE WHEN json_valid(profile_json)
                            THEN json_extract(
                                profile_json,
                                '$.ghost_clan_code', '$.clan_code',
                                '$.ghost_clan', '$.clan', '$.fraction',
                                '$.faction', '$.ghost_profession', '$.profession',
                                '$.nick'
                            ) END AS identity_json
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        if not row:
            return None

        errors = []
        if not bool(row["profile_json_valid"]):
            errors.append("invalid_json")
        elif str(row["profile_json_type"] or "") != "object":
            errors.append("profile_not_object")
        if str(row["profile_integrity_status"] or "") != PROFILE_INTEGRITY_VALID:
            errors.append("profile_integrity_status_invalid")
        if int(row["profile_revision"] or 0) <= 0:
            errors.append("profile_revision_invalid")
        if not str(row["profile_checksum"] or ""):
            errors.append("profile_checksum_missing")
        if errors:
            _profile_event(
                "profile.recovery_required",
                username,
                "get_profile_identity",
                old_revision=int(row["profile_revision"] or 0),
                candidate_revision=None,
                changed_scopes=[],
                decision="rejected",
                reason_code=":".join(sorted(set(errors))),
                session_generation_hash="",
                request_id="",
            )
            raise ProfileRecoveryRequired(
                f"User '{username}' requires profile recovery."
            )

        try:
            identity_values = json.loads(row["identity_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            identity_values = []
        if not isinstance(identity_values, list) or len(identity_values) != 9:
            _profile_event(
                "profile.recovery_required",
                username,
                "get_profile_identity",
                old_revision=int(row["profile_revision"] or 0),
                candidate_revision=None,
                changed_scopes=[],
                decision="rejected",
                reason_code="identity_projection_invalid",
                session_generation_hash="",
                request_id="",
            )
            raise ProfileRecoveryRequired(
                f"User '{username}' requires profile recovery."
            )

        (ghost_clan_code, clan_code, ghost_clan, clan, fraction, faction,
         ghost_profession, profession, nick) = identity_values
        if isinstance(fraction, dict):
            fraction = fraction.get("name") or fraction.get("code") or ""

        return {
            "username": row["username"],
            "ghost_clan_code": ghost_clan_code,
            "clan_code": clan_code,
            "ghost_clan": ghost_clan,
            "clan": clan,
            "fraction": fraction,
            "faction": faction,
            "ghost_profession": ghost_profession,
            "profession": profession,
            "nick": nick,
        }

    def save_profile(self, profile):
        profile = copy.deepcopy(profile if isinstance(profile, dict) else {})
        username = profile.get("username")
        if not username:
            raise ValueError("Profile must contain username.")

        source = "legacy.save_profile"
        _profile_event(
            "profile.write_attempt",
            username,
            source,
            old_revision=None,
            candidate_revision=None,
            changed_scopes=[],
            decision="legacy_unversioned",
            reason_code="expected_revision_missing",
            session_generation_hash="",
            request_id="",
        )
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            current_row = conn.execute(
                """
                SELECT password, salt, profile_json, profile_revision,
                       profile_integrity_status
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
            if current_row is not None:
                current_revision = int(current_row["profile_revision"] or 0)
                _profile_event(
                    "profile.write_rejected",
                    username,
                    source,
                    old_revision=current_revision,
                    candidate_revision=None,
                    changed_scopes=[],
                    decision="rejected",
                    reason_code="expected_revision_required",
                    session_generation_hash="",
                    request_id="",
                )
                raise ProfileWriteConflict(
                    "Legacy save_profile cannot update an existing profile; "
                    "use save_profile_guarded with the revision read alongside the profile."
                )
            reuse_block = _identity_reuse_block_reason_with_conn(
                conn,
                username,
                include_user=False,
            )
            if reuse_block:
                raise ProfileWriteConflict(
                    "Identity cannot be reused: " + reuse_block
                )
            current_profile, _ = (
                _parse_profile_json_strict(current_row["profile_json"])
                if current_row else ({}, ())
            )
            current_profile = current_profile or {}
            old_revision = int(current_row["profile_revision"] or 0) if current_row else 0
            profile = _prepare_full_profile_candidate(profile, current_row=current_row)
            validation = validate_profile_candidate(profile, username)
            if not validation["valid"]:
                _profile_event(
                    "profile.write_rejected",
                    username,
                    source,
                    old_revision=0,
                    candidate_revision=None,
                    changed_scopes=[],
                    decision="rejected",
                    reason_code="candidate_invalid:" + ",".join(validation["errors"]),
                    session_generation_hash="",
                    request_id="",
                )
                raise ProfileValidationError(validation["errors"])
            next_revision = old_revision + 1
            checksum = profile_payload_checksum(profile)
            integrity_status = PROFILE_INTEGRITY_VALID
            schema_version = PROFILE_SCHEMA_VERSION

            current_validation = validate_profile_candidate(current_profile, username)
            if current_row and current_validation["valid"]:
                _write_profile_lkg(
                    conn,
                    username,
                    current_profile,
                    old_revision,
                    "prewrite:legacy.save_profile",
                    now,
                )
            elif not current_row:
                _write_profile_lkg(
                    conn,
                    username,
                    profile,
                    next_revision,
                    "create:legacy.save_profile",
                    now,
                )

            conn.execute(
                """
                INSERT INTO users
                    (username, password, salt, profile_json, created_at, updated_at,
                     profile_revision, profile_schema_version, profile_checksum,
                     profile_integrity_status, profile_validation_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password = excluded.password,
                    salt = excluded.salt,
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at,
                    profile_revision = excluded.profile_revision,
                    profile_schema_version = excluded.profile_schema_version,
                    profile_checksum = excluded.profile_checksum,
                    profile_integrity_status = excluded.profile_integrity_status,
                    profile_validation_version = excluded.profile_validation_version
                """,
                (
                    username,
                    profile.get("password", ""),
                    profile.get("salt", ""),
                    dumps_json(profile),
                    now,
                    now,
                    next_revision,
                    schema_version,
                    checksum,
                    integrity_status,
                    PROFILE_VALIDATION_VERSION,
                ),
            )
            if current_row is None:
                _wallet_register_with_conn(
                    conn,
                    username,
                    profile,
                    checksum,
                    created_at=now,
                )
        changed_scopes = profile_changed_scopes(current_profile, profile)
        _profile_event(
            "profile.write_applied",
            username,
            source,
            old_revision=old_revision,
            candidate_revision=next_revision,
            changed_scopes=list(changed_scopes),
            decision="legacy_unversioned",
            reason_code=(
                "validated_without_cas"
            ),
            session_generation_hash="",
            request_id="",
        )
        return {
            "applied": True,
            "profile_revision": next_revision,
            "integrity_status": integrity_status,
            "legacy_unversioned": True,
        }

    def consume_launch_queue(self, username):
        username = str(username or "").strip()
        if not username:
            return None

        # Empty polling is the dominant path. Check it without taking the
        # global writer lock, then re-read under BEGIN IMMEDIATE only when a
        # queue may actually need to be consumed.
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT profile_json, profile_revision, profile_checksum,
                       profile_integrity_status
                FROM users WHERE username = ?
                """,
                (username,),
            ).fetchone()
            if not row:
                return None
            profile, errors = _validate_persisted_profile_row(row, username)
            observed_revision = int(row["profile_revision"] or 0)
        if errors:
            self._record_recovery_required(
                username, observed_revision, "consume_launch_queue", errors
            )
            raise ProfileRecoveryRequired(
                "Launch queue profile requires recovery: " + ",".join(errors)
            )
        if not merge_launch_queue_values([], profile.get("launch_queue", [])):
            return []

        try:
            with db_connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    """
                    SELECT profile_json, profile_revision, profile_checksum,
                           profile_integrity_status
                    FROM users WHERE username = ?
                    """,
                    (username,),
                ).fetchone()
                if not row:
                    return None

                profile, errors = _validate_persisted_profile_row(row, username)
                old_revision = int(row["profile_revision"] or 0)
                if errors:
                    raise ProfileRecoveryRequired(
                        "Launch queue profile requires recovery: " + ",".join(errors)
                    )
                launch_list = merge_launch_queue_values(
                    [], profile.get("launch_queue", [])
                )
                if not launch_list:
                    return []

                original_profile = copy.deepcopy(profile)
                profile["launch_queue"] = []
                ensure_password_hash(profile)
                validation = validate_profile_candidate(profile, username)
                if not validation["valid"]:
                    raise ProfileRecoveryRequired(
                        "Launch queue candidate requires recovery: "
                        + ",".join(validation["errors"])
                    )
                now = utc_now()
                updated = conn.execute(
                    """
                    UPDATE users
                    SET password = ?, salt = ?, profile_json = ?, updated_at = ?,
                        profile_revision = ?, profile_schema_version = ?,
                        profile_checksum = ?, profile_integrity_status = ?,
                        profile_validation_version = ?
                    WHERE username = ? AND profile_revision = ?
                    """,
                    (
                        profile.get("password", ""),
                        profile.get("salt", ""),
                        dumps_json(profile),
                        now,
                        old_revision + 1,
                        PROFILE_SCHEMA_VERSION,
                        profile_payload_checksum(profile),
                        PROFILE_INTEGRITY_VALID,
                        PROFILE_VALIDATION_VERSION,
                        username,
                        old_revision,
                    ),
                )
                if updated.rowcount != 1:
                    raise ProfileWriteConflict(
                        "Launch queue profile revision changed before commit."
                    )
                _write_profile_lkg(
                    conn,
                    username,
                    original_profile,
                    old_revision,
                    "prewrite:consume_launch_queue",
                    now,
                )
                return launch_list
        except ProfileRecoveryRequired:
            self._record_recovery_required(
                username, old_revision, "consume_launch_queue", errors
            )
            raise

    def username_exists(self, username):
        with db_connect(self.db_path) as conn:
            return bool(
                _identity_reuse_block_reason_with_conn(conn, username)
            )

    def identity_reuse_block_reason(self, username):
        with db_connect(self.db_path) as conn:
            return _identity_reuse_block_reason_with_conn(conn, username)

    def authenticate(self, username, password):
        recovery = None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT password, profile_json, profile_revision,
                       profile_integrity_status, profile_checksum
                FROM users WHERE username = ?
                """,
                (username,),
            ).fetchone()
            if not row:
                return False
            stored_password = row["password"] or ""
            if not verify_password(password, stored_password):
                return False
            old_revision = int(row["profile_revision"] or 0)
            old_profile, errors = _validate_persisted_profile_row(row, username)
            if errors:
                recovery = (old_revision, errors)
            elif not is_password_hash(stored_password):
                profile = copy.deepcopy(old_profile)
                profile["password"] = str(password or "")
                ensure_password_hash(profile)
                validation = validate_profile_candidate(profile, username)
                if not validation["valid"]:
                    recovery = (old_revision, validation["errors"])
                if recovery is None:
                    now = utc_now()
                    updated = conn.execute(
                        """
                        UPDATE users
                        SET password = ?, salt = ?, profile_json = ?, updated_at = ?,
                            profile_revision = ?, profile_schema_version = ?,
                            profile_checksum = ?, profile_integrity_status = ?,
                            profile_validation_version = ?
                        WHERE username = ? AND profile_revision = ?
                        """,
                        (
                            profile.get("password", ""),
                            profile.get("salt", ""),
                            dumps_json(profile),
                            now,
                            old_revision + 1,
                            PROFILE_SCHEMA_VERSION,
                            profile_payload_checksum(profile),
                            PROFILE_INTEGRITY_VALID,
                            PROFILE_VALIDATION_VERSION,
                            username,
                            old_revision,
                        ),
                    )
                    if updated.rowcount != 1:
                        raise ProfileWriteConflict(
                            "Password upgrade profile revision changed before commit."
                        )
                    _write_profile_lkg(
                        conn,
                        username,
                        old_profile,
                        old_revision,
                        "prewrite:authenticate_password_upgrade",
                        now,
                    )
        if recovery is not None:
            revision, errors = recovery
            self._record_recovery_required(
                username, revision, "authenticate", errors
            )
            raise ProfileRecoveryRequired(
                "Authenticated profile requires recovery: " + ",".join(errors)
            )
        return True

    def delete_user(self, username, reason="account_deleted"):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT profile_revision FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return False

            conn.execute(
                """
                INSERT INTO deleted_user_tombstones (
                    username, deleted_at, reason, profile_revision
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    deleted_at = excluded.deleted_at,
                    reason = excluded.reason,
                    profile_revision = MAX(
                        deleted_user_tombstones.profile_revision,
                        excluded.profile_revision
                    )
                """,
                (
                    username,
                    utc_now(),
                    str(reason or "account_deleted"),
                    int(row["profile_revision"] or 0),
                ),
            )

            conn.execute(
                "DELETE FROM chat_messages WHERE owner_username = ? OR peer_name = ?",
                (username, username),
            )
            conn.execute(
                "DELETE FROM contacts WHERE owner_username = ? OR contact_name = ?",
                (username, username),
            )
            conn.execute("DELETE FROM mail_presence WHERE username = ?", (username,))
            conn.execute("DELETE FROM kv_store WHERE key = ?", (f"mail_seed:{username}",))
            conn.execute("DELETE FROM area_events WHERE owner_username = ? OR actor_username = ?", (username, username))
            conn.execute("DELETE FROM player_areas WHERE owner_username = ?", (username,))
            conn.execute("DELETE FROM captured_targets WHERE owner_username = ?", (username,))
            conn.execute("DELETE FROM player_marked_targets WHERE username = ?", (username,))
            conn.execute("DELETE FROM player_marked_target_state WHERE username = ?", (username,))
            conn.execute("DELETE FROM profile_last_known_good WHERE username = ?", (username,))
            conn.execute(
                "DELETE FROM reported_vulnerabilities WHERE reported_by_username = ? OR territory_owner_username = ?",
                (username, username),
            )
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
            return True


class JsonResourceStore:
    # Repository JSON files are seed/reference content. Runtime reads from the
    # SQLite json_resources table; changing static/*.json requires an explicit
    # sync/import step and should not silently mutate runtime state.
    SEED_RESOURCE_KEYS = {
        "app_config",
        "user_template",
        "user_security",
        "terminal_command",
        "messages",
        "friends",
        "fractions",
    }

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)
        self.seed_static_directory()

    def _seed_file_if_missing(self, conn, key, seed_path):
        row = conn.execute(
            "SELECT 1 FROM json_resources WHERE key = ?",
            (key,),
        ).fetchone()
        if row or not seed_path or not os.path.exists(seed_path):
            return

        with open(seed_path, "r", encoding="utf-8") as f:
            value = json.load(f)
        conn.execute(
            """
            INSERT INTO json_resources (key, source_path, value_json, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, seed_path, dumps_json(value), utc_now()),
        )

    def seed_static_directory(self, static_dir="static"):
        if not os.path.isdir(static_dir):
            return

        with db_connect(self.db_path) as conn:
            for filename in os.listdir(static_dir):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(static_dir, filename)
                key = os.path.splitext(filename)[0]
                if key not in self.SEED_RESOURCE_KEYS:
                    continue
                self._seed_file_if_missing(conn, key, path)

    def get(self, key, seed_path=None, default=None):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value_json FROM json_resources WHERE key = ?",
                (key,),
            ).fetchone()
            if row:
                return loads_json(row["value_json"], default)

            legacy = conn.execute(
                "SELECT value_json FROM kv_store WHERE key = ?",
                (key,),
            ).fetchone()
            if legacy:
                value = loads_json(legacy["value_json"], default)
                conn.execute(
                    """
                    INSERT INTO json_resources (key, source_path, value_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, seed_path or "", dumps_json(value), utc_now()),
                )
                return value

            if seed_path and os.path.exists(seed_path):
                self._seed_file_if_missing(conn, key, seed_path)
                row = conn.execute(
                    "SELECT value_json FROM json_resources WHERE key = ?",
                    (key,),
                ).fetchone()
                if row:
                    return loads_json(row["value_json"], default)

            return copy.deepcopy(default)

    def set(self, key, value):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO json_resources (key, source_path, value_json, updated_at)
                VALUES (?, '', ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, dumps_json(value), utc_now()),
            )


class DevBugReportStore:
    VALID_CATEGORIES = {
        "UI", "Map", "Operations", "Files", "Ghost Exchange",
        "Googleplex", "Login", "Performance", "Other"
    }
    VALID_SEVERITIES = {"low", "medium", "high", "blocker"}
    VALID_STATUSES = {"new", "confirmed", "in_progress", "fixed", "duplicate", "wontfix"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def _row_to_report(self, row):
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "category": row["category"],
            "severity": row["severity"],
            "status": row["status"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "app_version": row["app_version"],
            "current_url": row["current_url"],
            "screen": row["screen"],
            "context": loads_json(row["context_json"], {}),
        }

    def _normalize_category(self, value):
        value = str(value or "Other").strip()
        return value if value in self.VALID_CATEGORIES else "Other"

    def _normalize_severity(self, value):
        value = str(value or "medium").strip().lower()
        return value if value in self.VALID_SEVERITIES else "medium"

    def _normalize_status(self, value):
        value = str(value or "new").strip().lower()
        return value if value in self.VALID_STATUSES else "new"

    def list_reports(self, search="", category="", status="", limit=200):
        search = str(search or "").strip().lower()
        category = str(category or "").strip()
        status = str(status or "").strip().lower()
        limit = max(1, min(int(limit or 200), 500))

        clauses = []
        params = []
        if category:
            clauses.append("category = ?")
            params.append(self._normalize_category(category))
        if status:
            clauses.append("status = ?")
            params.append(self._normalize_status(status))
        if search:
            clauses.append("(lower(title) LIKE ? OR lower(description) LIKE ?)")
            needle = f"%{search}%"
            params.extend([needle, needle])

        sql = "SELECT * FROM dev_bug_reports"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with db_connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_report(row) for row in rows]

    def find_similar(self, title, limit=5):
        words = [
            re_word for re_word in
            [part.strip().lower() for part in str(title or "").replace("-", " ").split()]
            if len(re_word) >= 4
        ]
        if not words:
            return []

        clauses = ["lower(title) LIKE ?" for _ in words[:6]]
        params = [f"%{word}%" for word in words[:6]]
        params.append(max(1, min(int(limit or 5), 10)))
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM dev_bug_reports
                WHERE {" OR ".join(clauses)}
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [self._row_to_report(row) for row in rows]

    def create_report(self, data, created_by, app_version=""):
        title = str((data or {}).get("title") or "").strip()
        if not title:
            raise ValueError("Tytul zgloszenia jest wymagany.")

        now = utc_now()
        context = (data or {}).get("context") or {}
        if not isinstance(context, dict):
            context = {"raw": str(context)}

        with db_connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO dev_bug_reports (
                    title, description, category, severity, status, created_by,
                    created_at, updated_at, app_version, current_url, screen, context_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    str((data or {}).get("description") or "").strip(),
                    self._normalize_category((data or {}).get("category")),
                    self._normalize_severity((data or {}).get("severity")),
                    self._normalize_status((data or {}).get("status") or "new"),
                    str(created_by or ""),
                    now,
                    now,
                    str(app_version or (data or {}).get("app_version") or ""),
                    str((data or {}).get("current_url") or ""),
                    str((data or {}).get("screen") or ""),
                    dumps_json(context),
                ),
            )
            row = conn.execute(
                "SELECT * FROM dev_bug_reports WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
            return self._row_to_report(row)

    def update_report(self, report_id, data):
        report_id = int(report_id)
        allowed = {}
        if "status" in (data or {}):
            allowed["status"] = self._normalize_status((data or {}).get("status"))
        if "severity" in (data or {}):
            allowed["severity"] = self._normalize_severity((data or {}).get("severity"))
        if "category" in (data or {}):
            allowed["category"] = self._normalize_category((data or {}).get("category"))
        if "title" in (data or {}):
            title = str((data or {}).get("title") or "").strip()
            if title:
                allowed["title"] = title
        if "description" in (data or {}):
            allowed["description"] = str((data or {}).get("description") or "").strip()

        if not allowed:
            with db_connect(self.db_path) as conn:
                row = conn.execute("SELECT * FROM dev_bug_reports WHERE id = ?", (report_id,)).fetchone()
                return self._row_to_report(row) if row else None

        allowed["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in allowed)
        params = list(allowed.values()) + [report_id]
        with db_connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE dev_bug_reports SET {assignments} WHERE id = ?",
                params,
            )
            row = conn.execute("SELECT * FROM dev_bug_reports WHERE id = ?", (report_id,)).fetchone()
            return self._row_to_report(row) if row else None


class GhostNetworkTerritoryJobStore:
    """Durable handoff from territory publication to the single GN worker."""

    VALID_KINDS = {"areas", "conflict"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def enqueue(self, job_kind, reference_id, source_version, reason=""):
        kind = str(job_kind or "").strip().lower()
        reference = str(reference_id or "").strip()
        version = str(source_version or "").strip()
        if kind not in self.VALID_KINDS:
            raise ValueError(f"unsupported GhostNetwork territory job kind: {kind}")
        if not reference or not version:
            raise ValueError("GhostNetwork territory job requires reference_id and source_version")
        seed = f"{kind}|{reference}|{version}"
        job_id = "ghost-territory-" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:24]
        now = utc_now()
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO ghostnetwork_territory_jobs
                    (job_id, job_kind, reference_id, source_version, reason,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                ON CONFLICT(job_id) DO NOTHING
                """,
                (job_id, kind, reference, version, str(reason or ""), now, now),
            )
        return {"job_id": job_id, "enqueued": cursor.rowcount == 1}

    def claim(self, lease_owner, lease_seconds=300):
        now_ts = time.time()
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM ghostnetwork_territory_jobs
                WHERE (status = 'pending' AND attempts < 5 AND next_attempt_at <= ?)
                   OR (status = 'processing' AND lease_until < ? AND attempts < 5)
                ORDER BY created_at, job_id LIMIT 1
                """,
                (now_ts, now_ts),
            ).fetchone()
            if not row:
                return None
            coalesced_jobs = 0
            if row["job_kind"] == "areas":
                latest_area = conn.execute(
                    """SELECT * FROM ghostnetwork_territory_jobs
                       WHERE status = 'pending' AND job_kind = 'areas'
                         AND attempts < 5 AND next_attempt_at <= ?
                       ORDER BY created_at DESC, job_id DESC LIMIT 1""",
                    (now_ts,),
                ).fetchone()
                if latest_area:
                    row = latest_area
                superseded = conn.execute(
                    """UPDATE ghostnetwork_territory_jobs
                       SET status = 'complete', error = ?, updated_at = ?, finished_at = ?
                       WHERE status = 'pending' AND job_kind = 'areas'
                         AND attempts < 5 AND next_attempt_at <= ? AND job_id != ?""",
                    (f"coalesced_into:{row['job_id']}", now, now, now_ts, row["job_id"]),
                )
                coalesced_jobs = int(superseded.rowcount or 0)
            cursor = conn.execute(
                """
                UPDATE ghostnetwork_territory_jobs
                SET status = 'processing', lease_owner = ?, lease_until = ?,
                    attempts = attempts + 1, updated_at = ?
                WHERE job_id = ? AND (status = 'pending' OR lease_until < ?)
                """,
                (str(lease_owner), now_ts + float(lease_seconds), now, row["job_id"], now_ts),
            )
            if cursor.rowcount != 1:
                return None
            claimed = conn.execute(
                "SELECT * FROM ghostnetwork_territory_jobs WHERE job_id = ?", (row["job_id"],)
            ).fetchone()
            return {**dict(claimed), "coalesced_jobs": coalesced_jobs}

    def finish(self, job_id, lease_owner, ok=True, error="", processing_ms=0):
        now = utc_now()
        try:
            processing_ms = max(0, int(processing_ms or 0))
        except (TypeError, ValueError):
            processing_ms = 0
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE ghostnetwork_territory_jobs
                SET status = CASE WHEN ? = 1 THEN 'complete'
                                  WHEN attempts >= 5 THEN 'failed'
                                  ELSE 'pending' END,
                    error = ?, lease_owner = '', lease_until = 0,
                    next_attempt_at = CASE WHEN ? = 1 THEN 0
                                           ELSE ? + MIN(60, (1 << MIN(attempts, 5))) END,
                    processing_ms = ?, updated_at = ?, finished_at = ?
                WHERE job_id = ? AND lease_owner = ? AND status = 'processing'
                """,
                (1 if ok else 0, str(error or '')[:1000], 1 if ok else 0,
                 time.time(), processing_ms, now, now if ok else None,
                 str(job_id), str(lease_owner)),
            )
            return cursor.rowcount == 1

    def status_counts(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM ghostnetwork_territory_jobs GROUP BY status"
            ).fetchall()
        return {str(row["status"]): int(row["count"] or 0) for row in rows}

    def diagnostics(self):
        now_ts = time.time()
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT status, attempts, created_at, processing_ms "
                "FROM ghostnetwork_territory_jobs ORDER BY created_at"
            ).fetchall()
        counts = {}
        processing = []
        oldest_pending_age = 0
        for row in rows:
            status = str(row["status"] or "")
            counts[status] = counts.get(status, 0) + 1
            if status in {"pending", "processing"}:
                try:
                    created_ts = datetime.fromisoformat(str(row["created_at"])).timestamp()
                    oldest_pending_age = max(oldest_pending_age, int(now_ts - created_ts))
                except (TypeError, ValueError):
                    pass
            if status == "complete" and int(row["processing_ms"] or 0) >= 0:
                processing.append(int(row["processing_ms"] or 0))
        processing.sort()

        def percentile(values, fraction):
            if not values:
                return 0
            return values[min(len(values) - 1, max(0, math.ceil(len(values) * fraction) - 1))]

        return {
            "counts": counts,
            "depth": int(counts.get("pending", 0) + counts.get("processing", 0)),
            "oldest_pending_age_seconds": oldest_pending_age,
            "processing_ms": {
                "samples": len(processing),
                "p50": percentile(processing, 0.50),
                "p95": percentile(processing, 0.95),
                "max": max(processing) if processing else 0,
            },
        }


class GhostNetworkDeltaDeliveryJobStore:
    """Durable, cursor-based fan-out for canonical GhostNetwork events."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def enqueue(self, event, viewers):
        event = event if isinstance(event, dict) else {}
        event_id = str(event.get("event_id") or "").strip()
        cycle_id = str(event.get("cycle_id") or "").strip()
        if not event_id or not cycle_id:
            raise ValueError("GhostNetwork delivery requires event_id and cycle_id")
        safe_viewers = [dict(item) for item in (viewers or []) if isinstance(item, dict)]
        job_id = "ghost-delta-" + hashlib.sha1(event_id.encode("utf-8")).hexdigest()[:24]
        now = utc_now()
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO ghostnetwork_delta_delivery_jobs
                    (job_id, event_id, cycle_id, event_json, viewers_json,
                     status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                (job_id, event_id, cycle_id, dumps_json(event), dumps_json(safe_viewers), now, now),
            )
        return {"job_id": job_id, "event_id": event_id, "enqueued": cursor.rowcount == 1,
                "recipients": len(safe_viewers)}

    def claim(self, lease_owner, lease_seconds=300):
        now_ts = time.time()
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM ghostnetwork_delta_delivery_jobs
                WHERE (status = 'pending' AND attempts < 5 AND next_attempt_at <= ?)
                   OR (status = 'processing' AND lease_until < ? AND attempts < 5)
                ORDER BY created_at, job_id LIMIT 1
                """,
                (now_ts, now_ts),
            ).fetchone()
            if not row:
                return None
            cursor = conn.execute(
                """
                UPDATE ghostnetwork_delta_delivery_jobs
                SET status = 'processing', lease_owner = ?, lease_until = ?,
                    attempts = attempts + 1, updated_at = ?
                WHERE job_id = ? AND (status = 'pending' OR lease_until < ?)
                """,
                (str(lease_owner), now_ts + float(lease_seconds), now, row["job_id"], now_ts),
            )
            if cursor.rowcount != 1:
                return None
            claimed = conn.execute(
                "SELECT * FROM ghostnetwork_delta_delivery_jobs WHERE job_id = ?",
                (row["job_id"],),
            ).fetchone()
        return {
            **dict(claimed),
            "event": loads_json(claimed["event_json"], {}),
            "viewers": loads_json(claimed["viewers_json"], []),
            "snapshot": loads_json(claimed["snapshot_json"], {}),
        }

    def store_snapshot(self, job_id, lease_owner, snapshot):
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE ghostnetwork_delta_delivery_jobs
                SET snapshot_json = ?, updated_at = ?
                WHERE job_id = ? AND lease_owner = ? AND status = 'processing'
                  AND snapshot_json = '{}'
                """,
                (dumps_json(snapshot if isinstance(snapshot, dict) else {}), utc_now(),
                 str(job_id), str(lease_owner)),
            )
        return cursor.rowcount == 1

    def advance(self, job_id, lease_owner, next_index, published, skipped,
                processing_ms=0, complete=False):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE ghostnetwork_delta_delivery_jobs
                SET next_index = ?, published_count = published_count + ?,
                    skipped_count = skipped_count + ?, processing_ms = processing_ms + ?,
                    status = ?, lease_owner = '', lease_until = 0, attempts = 0,
                    next_attempt_at = 0, error = '', updated_at = ?, finished_at = ?
                WHERE job_id = ? AND lease_owner = ? AND status = 'processing'
                """,
                (int(next_index), int(published), int(skipped), max(0, int(processing_ms or 0)),
                 'complete' if complete else 'pending', now, now if complete else None,
                 str(job_id), str(lease_owner)),
            )
        return cursor.rowcount == 1

    def fail(self, job_id, lease_owner, error="", processing_ms=0):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE ghostnetwork_delta_delivery_jobs
                SET status = CASE WHEN attempts >= 5 THEN 'failed' ELSE 'pending' END,
                    error = ?, lease_owner = '', lease_until = 0,
                    next_attempt_at = ? + MIN(60, (1 << MIN(attempts, 5))),
                    processing_ms = processing_ms + ?, updated_at = ?
                WHERE job_id = ? AND lease_owner = ? AND status = 'processing'
                """,
                (str(error or '')[:1000], time.time(), max(0, int(processing_ms or 0)),
                 now, str(job_id), str(lease_owner)),
            )
        return cursor.rowcount == 1

    def has_event(self, event_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM ghostnetwork_delta_delivery_jobs WHERE event_id = ?",
                (str(event_id or ""),),
            ).fetchone()
        return bool(row)

    def diagnostics(self):
        now_ts = time.time()
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT status, created_at, processing_ms, published_count, skipped_count "
                "FROM ghostnetwork_delta_delivery_jobs ORDER BY created_at"
            ).fetchall()
        counts = {}
        processing = []
        oldest = 0
        published = 0
        skipped = 0
        for row in rows:
            status = str(row["status"] or "")
            counts[status] = counts.get(status, 0) + 1
            published += int(row["published_count"] or 0)
            skipped += int(row["skipped_count"] or 0)
            if status in {"pending", "processing"}:
                try:
                    oldest = max(oldest, int(now_ts - datetime.fromisoformat(row["created_at"]).timestamp()))
                except (TypeError, ValueError):
                    pass
            if status == "complete":
                processing.append(int(row["processing_ms"] or 0))
        processing.sort()
        p95_index = max(0, math.ceil(len(processing) * 0.95) - 1) if processing else 0
        return {
            "counts": counts,
            "depth": int(counts.get("pending", 0) + counts.get("processing", 0)),
            "oldest_pending_age_seconds": oldest,
            "published": published,
            "skipped": skipped,
            "processing_ms": {
                "samples": len(processing),
                "p95": processing[p95_index] if processing else 0,
                "max": max(processing) if processing else 0,
            },
        }


class TerritoryStore:
    BASE_AREA_EDGE_METERS = 300
    MIN_TRIANGLE_AREA_SQM = 1
    MAX_EXACT_AREA_TARGETS = int(os.environ.get("CHAOS_TERRITORY_EXACT_TARGET_LIMIT", "32"))
    MAX_EXACT_AREA_TRIANGLES = int(os.environ.get("CHAOS_TERRITORY_EXACT_TRIANGLE_LIMIT", "1200"))

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _distance_meters(a, b):
        lat1 = math.radians(float(a["lat"]))
        lon1 = math.radians(float(a["lng"]))
        lat2 = math.radians(float(b["lat"]))
        lon2 = math.radians(float(b["lng"]))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        return 6371000 * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))

    @staticmethod
    def _triangle_area_sqm(edges):
        a, b, c = edges
        semiperimeter = (a + b + c) / 2
        area_value = (
            semiperimeter
            * (semiperimeter - a)
            * (semiperimeter - b)
            * (semiperimeter - c)
        )
        if area_value <= 0:
            return 0
        return math.sqrt(area_value)

    @staticmethod
    def _convex_hull(targets):
        unique = {}
        for target in targets:
            key = (round(float(target.get("lng", target.get("lon"))), 7), round(float(target.get("lat")), 7))
            unique[key] = target

        points = sorted(unique.items())
        if len(points) <= 1:
            return [target for _, target in points]

        def cross(origin, a, b):
            return (
                (a[0][0] - origin[0][0]) * (b[0][1] - origin[0][1])
                - (a[0][1] - origin[0][1]) * (b[0][0] - origin[0][0])
            )

        lower = []
        for point in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
                lower.pop()
            lower.append(point)

        upper = []
        for point in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
                upper.pop()
            upper.append(point)

        return [target for _, target in lower[:-1] + upper[:-1]]

    @staticmethod
    def _polygon_area_sqm(vertices):
        if len(vertices or []) < 3:
            return 0

        center_lat = math.radians(sum(float(v["lat"]) for v in vertices) / len(vertices))
        origin_lat = float(vertices[0]["lat"])
        origin_lng = float(vertices[0]["lng"])
        meters = []
        for vertex in vertices:
            x = math.radians(float(vertex["lng"]) - origin_lng) * 6371000 * math.cos(center_lat)
            y = math.radians(float(vertex["lat"]) - origin_lat) * 6371000
            meters.append((x, y))

        area = 0
        for i, point in enumerate(meters):
            next_point = meters[(i + 1) % len(meters)]
            area += point[0] * next_point[1] - next_point[0] * point[1]
        return abs(area) / 2

    def _connected_target_groups(self, targets, max_edge_distance):
        unvisited = set(range(len(targets)))
        groups = []

        while unvisited:
            start = unvisited.pop()
            stack = [start]
            group_indexes = {start}

            while stack:
                current = stack.pop()
                linked = [
                    other for other in list(unvisited)
                    if self._distance_meters(targets[current], targets[other]) <= max_edge_distance
                ]
                for other in linked:
                    unvisited.remove(other)
                    group_indexes.add(other)
                    stack.append(other)

            groups.append([targets[index] for index in sorted(group_indexes)])

        return groups

    @staticmethod
    def point_in_polygon(lat, lng, vertices):
        if len(vertices or []) < 3:
            return False

        inside = False
        j = len(vertices) - 1
        for i, vertex in enumerate(vertices):
            yi = float(vertex.get("lat"))
            xi = float(vertex.get("lng"))
            yj = float(vertices[j].get("lat"))
            xj = float(vertices[j].get("lng"))
            crosses = (xi > lng) != (xj > lng)
            if crosses:
                slope_lat = (yj - yi) * (lng - xi) / ((xj - xi) or 1e-12) + yi
                if lat < slope_lat:
                    inside = not inside
            j = i
        return inside

    @staticmethod
    def _player_level(value):
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _area_vertex(target):
        lng = target.get("lng", target.get("lon"))
        return {
            "lat": float(target.get("lat")),
            "lng": float(lng),
            "label": target.get("label", ""),
            "name": target.get("name") or target.get("label", ""),
            "icon": target.get("icon", ""),
            "source_type": target.get("source_type", ""),
            "captured_at": target.get("captured_at", ""),
        }

    def _area_from_hull(self, targets):
        hull = self._convex_hull(targets)
        if len(hull) < 3:
            return None

        vertices = [self._area_vertex(target) for target in hull]
        area_size = self._polygon_area_sqm(vertices)
        if area_size < self.MIN_TRIANGLE_AREA_SQM:
            return None

        hull_edges = [
            self._distance_meters(vertices[i], vertices[(i + 1) % len(vertices)])
            for i in range(len(vertices))
        ]
        return {
            "vertices": vertices,
            "centroid_lat": sum(vertex["lat"] for vertex in vertices) / len(vertices),
            "centroid_lng": sum(vertex["lng"] for vertex in vertices) / len(vertices),
            "area_size": area_size,
            "max_edge_distance": max(hull_edges) if hull_edges else 0,
            "status": "active",
        }

    def _normalize_target(self, username, target):
        now = utc_now()
        normalized = copy.deepcopy(target or {})
        lng = normalized.get("lng", normalized.get("lon"))
        normalized["lng"] = float(lng)
        normalized["lon"] = float(lng)
        normalized["lat"] = float(normalized.get("lat"))
        generated = bool(normalized.get("generated", False))
        stationary = bool(normalized.get("stationary", not generated))
        normalized["owner_username"] = username
        normalized["stationary"] = stationary
        normalized.setdefault("captured_at", now)
        return {
            "owner_username": username,
            "lat": normalized["lat"],
            "lng": normalized["lng"],
            "label": str(normalized.get("label") or ""),
            "name": str(normalized.get("name") or normalized.get("label") or ""),
            "icon": str(normalized.get("icon") or ""),
            "source_type": str(normalized.get("source_type") or ""),
            "generated": 1 if generated else 0,
            "stationary": 1 if stationary else 0,
            "target_json": dumps_json(normalized),
            "captured_at": str(normalized.get("captured_at") or now),
            "updated_at": now,
        }

    def save_captured_target(self, username, target):
        data = self._normalize_target(username, target)
        with db_connect(self.db_path) as conn:
            if data["stationary"]:
                conn.execute(
                    """
                    DELETE FROM captured_targets
                    WHERE owner_username != ?
                        AND ROUND(lat, 5) = ROUND(?, 5)
                        AND ROUND(lng, 5) = ROUND(?, 5)
                    """,
                    (username, data["lat"], data["lng"]),
                )
            conn.execute(
                """
                INSERT INTO captured_targets
                    (owner_username, lat, lng, label, name, icon, source_type,
                     generated, stationary, target_json, captured_at, updated_at)
                VALUES
                    (:owner_username, :lat, :lng, :label, :name, :icon, :source_type,
                     :generated, :stationary, :target_json, :captured_at, :updated_at)
                ON CONFLICT(owner_username, lat, lng, label) DO UPDATE SET
                    name = excluded.name,
                    icon = excluded.icon,
                    source_type = excluded.source_type,
                    generated = excluded.generated,
                    stationary = excluded.stationary,
                    target_json = excluded.target_json,
                    updated_at = excluded.updated_at
                """,
                data,
            )
        return loads_json(data["target_json"], {})

    def remove_captured_target(self, username, lat, lng, label=None):
        query = """
            DELETE FROM captured_targets
            WHERE owner_username = ?
                AND ROUND(lat, 5) = ROUND(?, 5)
                AND ROUND(lng, 5) = ROUND(?, 5)
        """
        params = [username, float(lat), float(lng)]
        if label is not None:
            query += " AND label = ?"
            params.append(str(label))

        with db_connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def sync_profile_hacked_targets(self, username, profile):
        synced = []
        for target in (profile or {}).get("hacked", []):
            if not isinstance(target, dict):
                continue
            if target.get("lat") is None or (target.get("lng") is None and target.get("lon") is None):
                continue
            synced.append(self.save_captured_target(username, target))
        return synced

    def list_captured_targets(self, username, stationary=None):
        query = "SELECT lat, lng, target_json FROM captured_targets WHERE owner_username = ?"
        params = [username]
        if stationary is not None:
            query += " AND stationary = ?"
            params.append(1 if stationary else 0)
        query += " ORDER BY captured_at"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            targets = []
            for row in rows:
                target = loads_json(row["target_json"], {})
                target["lat"] = float(target.get("lat", row["lat"]))
                lng = target.get("lng", target.get("lon", row["lng"]))
                target["lng"] = float(lng)
                target["lon"] = float(lng)
                targets.append(target)
            return targets

    def list_all_captured_targets(self, stationary=None):
        query = "SELECT lat, lng, target_json FROM captured_targets"
        params = []
        if stationary is not None:
            query += " WHERE stationary = ?"
            params.append(1 if stationary else 0)
        query += " ORDER BY owner_username, captured_at"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            targets = []
            for row in rows:
                target = loads_json(row["target_json"], {})
                target["lat"] = float(target.get("lat", row["lat"]))
                lng = target.get("lng", target.get("lon", row["lng"]))
                target["lng"] = float(lng)
                target["lon"] = float(lng)
                targets.append(target)
            return targets

    def get_captured_target(self, username, target_id=None, lat=None, lng=None, label=None):
        """Read one canonical captured target without touching the player profile."""
        target_id = str(target_id or "").strip()
        for target in self.list_captured_targets(username):
            stored_id = str(target.get("target_id") or "").strip()
            if target_id and stored_id == target_id:
                return target
            if lat is None or lng is None:
                continue
            try:
                same_position = (
                    round(float(target.get("lat")), 5) == round(float(lat), 5)
                    and round(float(target.get("lng", target.get("lon"))), 5) == round(float(lng), 5)
                )
            except (TypeError, ValueError):
                same_position = False
            if same_position and (label is None or str(target.get("label") or "") == str(label)):
                return target
        return None

    def update_captured_target_security(self, username, target, security, expected_version=None):
        """CAS update of security in captured_targets; geometry remains untouched."""
        lat = float((target or {}).get("lat"))
        lng = float((target or {}).get("lng", (target or {}).get("lon")))
        label = str((target or {}).get("label") or "")
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT target_json FROM captured_targets
                WHERE owner_username = ? AND ROUND(lat, 5) = ROUND(?, 5)
                  AND ROUND(lng, 5) = ROUND(?, 5) AND label = ?
                """,
                (username, lat, lng, label),
            ).fetchone()
            if not row:
                return {"ok": False, "reason": "not_found"}
            current = loads_json(row["target_json"], {})
            current_version = int(current.get("security_version") or 0)
            if expected_version not in (None, "") and int(expected_version) != current_version:
                return {"ok": False, "reason": "stale_version", "security_version": current_version}
            current["security"] = dict(security or {})
            current["security_version"] = current_version + 1
            conn.execute(
                """
                UPDATE captured_targets SET target_json = ?, updated_at = ?
                WHERE owner_username = ? AND ROUND(lat, 5) = ROUND(?, 5)
                  AND ROUND(lng, 5) = ROUND(?, 5) AND label = ?
                """,
                (dumps_json(current), utc_now(), username, lat, lng, label),
            )
            return {
                "ok": True,
                "target": current,
                "security": dict(current.get("security") or {}),
                "security_version": int(current.get("security_version") or 0),
            }

    def abandon_captured_target(self, username, target, target_id, expected_version=None):
        """Atomically remove a captured target and enqueue durable geometry recovery."""
        target_id = str(target_id or target.get("target_id") or "").strip()
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
        label = str(target.get("label") or "")
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            captured_row = conn.execute(
                """
                SELECT id, captured_at FROM captured_targets
                WHERE owner_username = ? AND ROUND(lat, 5) = ROUND(?, 5)
                  AND ROUND(lng, 5) = ROUND(?, 5) AND label = ?
                """,
                (username, lat, lng, label),
            ).fetchone()
            if not captured_row:
                return {"ok": False, "reason": "not_found", "ownership_version": 0}
            ownership = conn.execute(
                "SELECT owner_username, ownership_version FROM territory_target_ownership WHERE target_id = ?",
                (target_id,),
            ).fetchone() if target_id else None
            ownership_version = int(ownership["ownership_version"] or 0) if ownership else 0
            if ownership and str(ownership["owner_username"] or "") != str(username):
                return {"ok": False, "reason": "stale_owner", "ownership_version": ownership_version}
            if expected_version not in (None, "") and ownership and int(expected_version) != ownership_version:
                return {"ok": False, "reason": "stale_version", "ownership_version": ownership_version}
            cursor = conn.execute(
                """
                DELETE FROM captured_targets
                WHERE owner_username = ? AND ROUND(lat, 5) = ROUND(?, 5)
                  AND ROUND(lng, 5) = ROUND(?, 5) AND label = ?
                """,
                (username, lat, lng, label),
            )
            if cursor.rowcount == 0:
                return {"ok": False, "reason": "not_found", "ownership_version": ownership_version}
            if ownership:
                conn.execute(
                    "DELETE FROM territory_target_ownership WHERE target_id = ? AND owner_username = ?",
                    (target_id, username),
                )
            # The captured row is a durable capture incarnation. Using only
            # target_id/version reused a completed job when an ordinary target
            # (version 0) was captured, abandoned, captured and abandoned again.
            # The second delete then committed without any pending rebuild.
            seed = f"abandon|{username}|{target_id}|{ownership_version}|{captured_row['id']}"
            job_id = "territory_rebuild_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]
            inserted = conn.execute(
                """
                INSERT INTO territory_rebuild_jobs
                    (job_id, owner_username, reason, target_id, target_json, status,
                     created_at, updated_at)
                VALUES (?, ?, 'captured_object_abandoned', ?, ?, 'pending', ?, ?)
                ON CONFLICT(job_id) DO NOTHING
                """,
                (job_id, username, target_id, dumps_json(target), now, now),
            )
            if inserted.rowcount != 1:
                raise RuntimeError(f"territory rebuild job collision: {job_id}")
            return {
                "ok": True, "job_id": job_id, "target": copy.deepcopy(target),
                "target_id": target_id, "ownership_version": ownership_version,
                "capture_record_id": int(captured_row["id"]),
            }

    def enqueue_rebuild_job(self, username, reason="operator_recovery", source_key=""):
        """Enqueue a bounded worker-owned geometry rebuild for explicit recovery."""
        username = str(username or "").strip()
        if not username:
            raise ValueError("territory rebuild requires owner username")
        reason = str(reason or "operator_recovery").strip()
        now = utc_now()
        unique_source = str(source_key or f"{now}:{time.time_ns()}")
        seed = f"rebuild|{username}|{reason}|{unique_source}"
        job_id = "territory_rebuild_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:20]
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO territory_rebuild_jobs
                    (job_id, owner_username, reason, status, created_at, updated_at)
                VALUES (?, ?, ?, 'pending', ?, ?)
                """,
                (job_id, username, reason, now, now),
            )
        return {"ok": True, "job_id": job_id, "owner_username": username, "reason": reason}

    def claim_rebuild_job(self, lease_owner, lease_seconds=300):
        now_ts = time.time()
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM territory_rebuild_jobs
                WHERE status = 'pending' OR (status = 'processing' AND lease_until < ?)
                ORDER BY created_at LIMIT 1
                """,
                (now_ts,),
            ).fetchone()
            if not row:
                return None
            cursor = conn.execute(
                """
                UPDATE territory_rebuild_jobs
                SET status = 'processing', lease_owner = ?, lease_until = ?,
                    attempts = attempts + 1, updated_at = ?
                WHERE job_id = ? AND (status = 'pending' OR lease_until < ?)
                """,
                (str(lease_owner), now_ts + float(lease_seconds), now, row["job_id"], now_ts),
            )
            if cursor.rowcount != 1:
                return None
            claimed = conn.execute(
                "SELECT * FROM territory_rebuild_jobs WHERE job_id = ?", (row["job_id"],)
            ).fetchone()
            return {
                **dict(claimed),
                "target": loads_json(claimed["target_json"], {}),
            }

    def finish_rebuild_job(self, job_id, lease_owner, ok=True, error=""):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE territory_rebuild_jobs
                SET status = ?, error = ?, lease_owner = '', lease_until = 0,
                    updated_at = ?, finished_at = ?
                WHERE job_id = ? AND lease_owner = ?
                """,
                ('complete' if ok else 'pending', str(error or ''), now,
                 now if ok else None, str(job_id), str(lease_owner)),
            )
            return cursor.rowcount == 1

    def build_player_areas(self, username, player_level=1):
        level = self._player_level(player_level)
        max_edge_distance = self.BASE_AREA_EDGE_METERS * level
        targets = [
            target
            for target in self.list_captured_targets(username, stationary=True)
            if target.get("lat") is not None and target.get("lng") is not None
        ]

        areas = []
        for group in self._connected_target_groups(targets, max_edge_distance):
            if len(group) < 3:
                continue
            if len(group) > self.MAX_EXACT_AREA_TARGETS:
                area = self._area_from_hull(group)
                if area:
                    print(
                        "[TERRITORY] large cluster approximated "
                        f"username={username} targets={len(group)} "
                        f"limit={self.MAX_EXACT_AREA_TARGETS}",
                        flush=True,
                    )
                    areas.append(area)
                continue

            valid_triangles = []
            exact_triangle_limit_exceeded = False
            for combo_indexes in combinations(range(len(group)), 3):
                combo = [group[index] for index in combo_indexes]
                vertices = [self._area_vertex(target) for target in combo]
                edges = [
                    self._distance_meters(vertices[i], vertices[(i + 1) % len(vertices)])
                    for i in range(len(vertices))
                ]
                if max(edges) > max_edge_distance:
                    continue

                area_size = self._polygon_area_sqm(vertices)
                if area_size < self.MIN_TRIANGLE_AREA_SQM:
                    continue

                valid_triangles.append(set(combo_indexes))
                if len(valid_triangles) > self.MAX_EXACT_AREA_TRIANGLES:
                    exact_triangle_limit_exceeded = True
                    break

            if exact_triangle_limit_exceeded:
                area = self._area_from_hull(group)
                if area:
                    print(
                        "[TERRITORY] dense cluster approximated "
                        f"username={username} targets={len(group)} "
                        f"triangles>{self.MAX_EXACT_AREA_TRIANGLES}",
                        flush=True,
                    )
                    areas.append(area)
                continue

            unvisited = set(range(len(valid_triangles)))
            while unvisited:
                triangle_index = unvisited.pop()
                stack = [triangle_index]
                cluster_indexes = set(valid_triangles[triangle_index])

                while stack:
                    current = stack.pop()
                    linked = [
                        other for other in list(unvisited)
                        if valid_triangles[current] & valid_triangles[other]
                    ]
                    for other in linked:
                        unvisited.remove(other)
                        cluster_indexes.update(valid_triangles[other])
                        stack.append(other)

                area = self._area_from_hull([group[index] for index in sorted(cluster_indexes)])
                if not area:
                    continue
                areas.append(area)

        areas.sort(key=lambda area: (area["area_size"], area["max_edge_distance"]))
        return areas

    def rebuild_player_areas(self, username, player_level=1):
        areas = self.build_player_areas(username, player_level)
        self.replace_player_areas(username, areas)
        self.refresh_encirclement_statuses()
        return areas

    def replace_player_areas(self, username, areas):
        now = utc_now()
        material = [
            {
                "vertices": area.get("vertices") or [],
                "centroid_lat": area.get("centroid_lat"),
                "centroid_lng": area.get("centroid_lng"),
                "area_size": float(area.get("area_size") or 0),
                "max_edge_distance": float(area.get("max_edge_distance") or 0),
            }
            for area in (areas or []) if isinstance(area, dict)
        ]
        geometry_hash = hashlib.sha1(
            dumps_json(material).encode("utf-8")
        ).hexdigest()
        with db_connect(self.db_path) as conn:
            publication = conn.execute(
                "SELECT * FROM territory_area_publications WHERE owner_username = ?",
                (username,),
            ).fetchone()
            if publication and str(publication["geometry_hash"] or "") == geometry_hash:
                return {
                    "changed": False,
                    "publication_version": int(publication["publication_version"] or 0),
                    "geometry_hash": geometry_hash,
                }
            next_version = int(publication["publication_version"] or 0) + 1 if publication else 1
            conn.execute("DELETE FROM player_areas WHERE owner_username = ?", (username,))
            for area in areas:
                conn.execute(
                    """
                    INSERT INTO player_areas
                        (owner_username, vertices_json, centroid_lat, centroid_lng,
                         area_size, max_edge_distance, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        dumps_json(area.get("vertices", [])),
                        area.get("centroid_lat"),
                        area.get("centroid_lng"),
                        float(area.get("area_size") or 0),
                        float(area.get("max_edge_distance") or 0),
                        area.get("status", "active"),
                        now,
                        now,
                    ),
                )
            conn.execute(
                """
                INSERT INTO territory_area_publications
                    (owner_username, publication_version, geometry_hash, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(owner_username) DO UPDATE SET
                    publication_version = excluded.publication_version,
                    geometry_hash = excluded.geometry_hash,
                    updated_at = excluded.updated_at
                """,
                (username, next_version, geometry_hash, now),
            )
            return {
                "changed": True,
                "publication_version": next_version,
                "geometry_hash": geometry_hash,
            }

    def get_area_publication(self, username):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM territory_area_publications WHERE owner_username = ?",
                (username,),
            ).fetchone()
        return dict(row) if row else None

    def list_player_areas(self, username=None):
        query = (
            "SELECT player_areas.*, "
            "COALESCE(territory_area_publications.publication_version, 0) AS publication_version "
            "FROM player_areas LEFT JOIN territory_area_publications "
            "ON territory_area_publications.owner_username = player_areas.owner_username"
        )
        params = []
        if username:
            query += " WHERE player_areas.owner_username = ?"
            params.append(username)
        query += " ORDER BY player_areas.owner_username, player_areas.id"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": row["id"],
                    "owner_username": row["owner_username"],
                    "vertices": loads_json(row["vertices_json"], []),
                    "centroid_lat": row["centroid_lat"],
                    "centroid_lng": row["centroid_lng"],
                    "area_size": row["area_size"],
                    "max_edge_distance": row["max_edge_distance"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "publication_version": int(row["publication_version"] or 0),
                }
                for row in rows
            ]

    def add_area_event(self, owner_username, actor_username, event_type, area_id=None, lat=None, lng=None, payload=None):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO area_events
                    (area_id, owner_username, actor_username, event_type, lat, lng, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    area_id,
                    owner_username,
                    actor_username,
                    event_type,
                    lat,
                    lng,
                    dumps_json(payload or {}),
                    utc_now(),
                ),
            )

    def recent_area_event_exists(self, owner_username, actor_username, event_type, area_id=None, seconds=60):
        threshold = (datetime.utcnow() - timedelta(seconds=seconds)).isoformat(timespec="seconds")
        query = """
            SELECT 1
            FROM area_events
            WHERE owner_username = ?
                AND actor_username = ?
                AND event_type = ?
                AND created_at >= ?
        """
        params = [owner_username, actor_username, event_type, threshold]
        if area_id is not None:
            query += " AND area_id = ?"
            params.append(area_id)
        query += " LIMIT 1"
        with db_connect(self.db_path) as conn:
            return conn.execute(query, params).fetchone() is not None

    def area_event_exists_with_payload_key(self, owner_username, actor_username, event_type, payload_key, payload_value):
        if not payload_key or payload_value is None:
            return False
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM area_events
                WHERE owner_username = ?
                    AND actor_username = ?
                    AND event_type = ?
                ORDER BY id DESC
                """,
                (owner_username, actor_username, event_type),
            ).fetchall()
        for row in rows:
            payload = loads_json(row["payload_json"], {})
            if isinstance(payload, dict) and str(payload.get(payload_key) or "") == str(payload_value):
                return True
        return False

    def list_recent_area_intruders(self, owner_username, seconds=120):
        threshold = (datetime.utcnow() - timedelta(seconds=seconds)).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT area_id, actor_username, lat, lng, payload_json, created_at
                FROM area_events
                WHERE owner_username = ?
                    AND event_type = 'intruder_enter'
                    AND created_at >= ?
                ORDER BY id DESC
                """,
                (owner_username, threshold),
            ).fetchall()

        seen = set()
        intruders = []
        for row in rows:
            key = (row["area_id"], row["actor_username"])
            if key in seen:
                continue
            seen.add(key)
            payload = loads_json(row["payload_json"], {})
            intruders.append({
                "area_id": row["area_id"],
                "username": row["actor_username"],
                "lat": row["lat"],
                "lng": row["lng"],
                "created_at": row["created_at"],
                "payload": payload,
            })
        return intruders

    def refresh_encirclement_statuses(self):
        areas = self.list_player_areas()
        statuses = {area["id"]: "active" for area in areas}
        owners_by_id = {area["id"]: area["owner_username"] for area in areas}

        for smaller in areas:
            for larger in areas:
                if smaller["id"] == larger["id"]:
                    continue
                if smaller["owner_username"] == larger["owner_username"]:
                    continue
                if float(larger.get("area_size") or 0) <= float(smaller.get("area_size") or 0):
                    continue
                if all(
                    self.point_in_polygon(vertex["lat"], vertex["lng"], larger.get("vertices", []))
                    for vertex in smaller.get("vertices", [])
                ):
                    statuses[smaller["id"]] = "encircled"
                    break

        now = utc_now()
        with db_connect(self.db_path) as conn:
            changed_owners = set()
            for area_id, status in statuses.items():
                cursor = conn.execute(
                    """
                    UPDATE player_areas
                    SET status = ?, updated_at = ?
                    WHERE id = ? AND status != ?
                    """,
                    (status, now, area_id, status),
                )
                if cursor.rowcount:
                    owner = owners_by_id.get(area_id, "")
                    if owner:
                        changed_owners.add(owner)
            for owner in changed_owners:
                conn.execute(
                    """
                    INSERT INTO territory_area_publications
                        (owner_username, publication_version, geometry_hash, updated_at)
                    VALUES (?, 1, '', ?)
                    ON CONFLICT(owner_username) DO UPDATE SET
                        publication_version = publication_version + 1,
                        updated_at = excluded.updated_at
                    """,
                    (owner, now),
                )
        return statuses

    def delete_user_data(self, username):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM area_events WHERE owner_username = ? OR actor_username = ?", (username, username))
            conn.execute("DELETE FROM player_areas WHERE owner_username = ?", (username,))
            conn.execute("DELETE FROM captured_targets WHERE owner_username = ?", (username,))
            conn.execute(
                """
                DELETE FROM territory_conflicts
                WHERE player_a_username = ?
                    OR player_b_username = ?
                    OR participants_json LIKE ?
                """,
                (username, username, f'%"{username}"%'),
            )
            conn.execute(
                "DELETE FROM reported_vulnerabilities WHERE reported_by_username = ? OR territory_owner_username = ?",
                (username, username),
            )


class TerritoryConflictEngagementStore:
    OPEN_STATUSES = ("detected", "active", "changing", "resolving")

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _row(row):
        if not row:
            return None
        return {
            "engagement_id": row["engagement_id"],
            "status": row["status"],
            "member_conflict_ids": loads_json(row["member_conflict_ids_json"], []),
            "member_front_ids": loads_json(row["member_front_ids_json"], []),
            "participant_usernames": loads_json(row["participant_usernames_json"], []),
            "hostile_clan_groups": loads_json(row["hostile_clan_groups_json"], {}),
            "geometry": loads_json(row["geometry_json"], []),
            "overlap_bbox": loads_json(row["overlap_bbox_json"], {}),
            "engagement_version": int(row["engagement_version"] or 0),
            "geometry_version": int(row["geometry_version"] or 0),
            "snapshot_version": int(row["snapshot_version"] or 0),
            "missed_publications": int(row["missed_publications"] or 0),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "resolved_at": row["resolved_at"],
            "closed_at": row["closed_at"],
        }

    @staticmethod
    def _bbox_overlap_area(left, right):
        if not isinstance(left, dict) or not isinstance(right, dict):
            return 0.0
        try:
            lat_span = min(float(left["max_lat"]), float(right["max_lat"])) - max(
                float(left["min_lat"]), float(right["min_lat"])
            )
            lng_span = min(float(left["max_lng"]), float(right["max_lng"])) - max(
                float(left["min_lng"]), float(right["min_lng"])
            )
        except (KeyError, TypeError, ValueError):
            return 0.0
        return max(0.0, lat_span) * max(0.0, lng_span)

    @staticmethod
    def _candidate_values(candidate):
        return {
            "member_conflict_ids": sorted({
                str(item) for item in (candidate.get("member_conflict_ids") or []) if item
            }),
            "member_front_ids": sorted({
                str(item) for item in (candidate.get("member_front_ids") or []) if item
            }),
            "participant_usernames": sorted({
                str(item) for item in (candidate.get("participant_usernames") or []) if item
            }),
            "hostile_clan_groups": candidate.get("hostile_clan_groups") or {},
            "geometry": candidate.get("overlap_geometry") or candidate.get("geometry") or [],
            "overlap_bbox": candidate.get("overlap_bbox") or {},
            "memberships": sorted(
                [
                    {
                        "conflict_id": str(item.get("conflict_id") or ""),
                        "front_id": str(item.get("front_id") or ""),
                    }
                    for item in (candidate.get("member_front_memberships") or [])
                    if isinstance(item, dict) and item.get("conflict_id") and item.get("front_id")
                ],
                key=lambda item: (item["conflict_id"], item["front_id"]),
            ),
        }

    def list_active(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM territory_conflict_engagements "
                "WHERE status IN ('detected','active','changing','resolving') "
                "ORDER BY created_at, engagement_id"
            ).fetchall()
            return [self._row(row) for row in rows]

    def get(self, engagement_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM territory_conflict_engagements WHERE engagement_id = ?",
                (str(engagement_id),),
            ).fetchone()
            return self._row(row)

    def list_members(self, engagement_id, active_only=False):
        with db_connect(self.db_path) as conn:
            sql = (
                "SELECT * FROM territory_conflict_engagement_members "
                "WHERE engagement_id = ?"
            )
            params = [str(engagement_id)]
            if active_only:
                sql += " AND status = 'active'"
            sql += " ORDER BY conflict_id, front_id"
            return [dict(row) for row in conn.execute(sql, tuple(params)).fetchall()]

    def _claim_coordinator(self, conn, lease_owner, lease_seconds):
        now = utc_now()
        lease_until = (
            datetime.utcnow() + timedelta(seconds=max(10, int(lease_seconds)))
        ).isoformat(timespec="seconds")
        conn.execute(
            "INSERT OR IGNORE INTO territory_conflict_engagement_coordinator "
            "(coordinator_key, lease_owner, lease_until, updated_at) VALUES ('global', '', NULL, ?)",
            (now,),
        )
        cursor = conn.execute(
            """
            UPDATE territory_conflict_engagement_coordinator
            SET lease_owner = ?, lease_until = ?, updated_at = ?
            WHERE coordinator_key = 'global'
              AND (lease_owner = ? OR lease_until IS NULL OR lease_until <= ?)
            """,
            (str(lease_owner), lease_until, now, str(lease_owner), now),
        )
        return cursor.rowcount == 1

    def reconcile_candidates(self, candidates, lease_owner, lease_seconds=120,
                             protected_conflict_ids=None):
        """Publish one detector batch under a durable global coordinator lease."""
        candidates = [self._candidate_values(item) for item in (candidates or [])]
        protected_conflict_ids = {
            str(item) for item in (protected_conflict_ids or []) if item
        }
        now = utc_now()
        with db_connect(self.db_path) as conn:
            if not self._claim_coordinator(conn, lease_owner, lease_seconds):
                return {"ok": False, "reason": "lease_busy", "changed": []}
            open_rows = conn.execute(
                "SELECT * FROM territory_conflict_engagements "
                "WHERE status IN ('detected','active','changing','resolving')"
            ).fetchall()
            open_engagements = [self._row(row) for row in open_rows]
            available = {item["engagement_id"]: item for item in open_engagements}
            changed = []

            for candidate in candidates:
                candidate_conflicts = set(candidate["member_conflict_ids"])
                candidate_fronts = set(candidate["member_front_ids"])
                matches = []
                for engagement in available.values():
                    conflict_overlap = len(
                        candidate_conflicts & set(engagement["member_conflict_ids"])
                    )
                    if not conflict_overlap:
                        continue
                    spatial_overlap = self._bbox_overlap_area(
                        candidate["overlap_bbox"], engagement["overlap_bbox"]
                    )
                    if spatial_overlap <= 0:
                        continue
                    front_overlap = len(candidate_fronts & set(engagement["member_front_ids"]))
                    matches.append((conflict_overlap, front_overlap, spatial_overlap, engagement))
                matches.sort(
                    key=lambda item: (item[0], item[1], item[2], item[3]["engagement_id"]),
                    reverse=True,
                )
                previous = matches[0][3] if matches else None
                engagement_id = (
                    previous["engagement_id"]
                    if previous else f"territory_engagement_{secrets.token_hex(8)}"
                )
                if previous:
                    available.pop(engagement_id, None)
                domain_changed = bool(previous and (
                    previous["status"] != "active"
                    or previous["member_conflict_ids"] != candidate["member_conflict_ids"]
                    or previous["member_front_ids"] != candidate["member_front_ids"]
                    or previous["participant_usernames"] != candidate["participant_usernames"]
                    or previous["hostile_clan_groups"] != candidate["hostile_clan_groups"]
                ))
                geometry_changed = bool(previous and (
                    previous["geometry"] != candidate["geometry"]
                    or previous["overlap_bbox"] != candidate["overlap_bbox"]
                ))
                is_new = previous is None
                if (previous and not domain_changed and not geometry_changed
                        and previous["missed_publications"] == 0):
                    continue
                engagement_version = 1 if is_new else previous["engagement_version"] + int(domain_changed)
                geometry_version = 1 if is_new else previous["geometry_version"] + int(geometry_changed)
                snapshot_version = 1 if is_new else previous["snapshot_version"] + int(
                    domain_changed or geometry_changed
                )
                created_at = now if is_new else previous["created_at"]
                conn.execute(
                    """
                    INSERT INTO territory_conflict_engagements
                        (engagement_id, status, member_conflict_ids_json,
                         member_front_ids_json, participant_usernames_json,
                         hostile_clan_groups_json, geometry_json, overlap_bbox_json,
                         engagement_version, geometry_version, snapshot_version,
                         missed_publications, created_at, updated_at, resolved_at, closed_at)
                    VALUES (?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, NULL, NULL)
                    ON CONFLICT(engagement_id) DO UPDATE SET
                        status = excluded.status,
                        member_conflict_ids_json = excluded.member_conflict_ids_json,
                        member_front_ids_json = excluded.member_front_ids_json,
                        participant_usernames_json = excluded.participant_usernames_json,
                        hostile_clan_groups_json = excluded.hostile_clan_groups_json,
                        geometry_json = excluded.geometry_json,
                        overlap_bbox_json = excluded.overlap_bbox_json,
                        engagement_version = excluded.engagement_version,
                        geometry_version = excluded.geometry_version,
                        snapshot_version = excluded.snapshot_version,
                        missed_publications = 0, updated_at = excluded.updated_at,
                        resolved_at = NULL, closed_at = NULL
                    """,
                    (
                        engagement_id, dumps_json(candidate["member_conflict_ids"]),
                        dumps_json(candidate["member_front_ids"]),
                        dumps_json(candidate["participant_usernames"]),
                        dumps_json(candidate["hostile_clan_groups"]),
                        dumps_json(candidate["geometry"]), dumps_json(candidate["overlap_bbox"]),
                        engagement_version, geometry_version, snapshot_version,
                        created_at, now,
                    ),
                )
                active_members = {
                    (item["conflict_id"], item["front_id"]) for item in candidate["memberships"]
                }
                stored_members = conn.execute(
                    "SELECT * FROM territory_conflict_engagement_members WHERE engagement_id = ?",
                    (engagement_id,),
                ).fetchall()
                for member in stored_members:
                    key = (member["conflict_id"], member["front_id"])
                    if key not in active_members and member["status"] == "active":
                        conn.execute(
                            "UPDATE territory_conflict_engagement_members "
                            "SET status = 'left', left_at = ?, updated_at = ? "
                            "WHERE engagement_id = ? AND conflict_id = ? AND front_id = ?",
                            (now, now, engagement_id, *key),
                        )
                for conflict_id, front_id in active_members:
                    conn.execute(
                        """
                        INSERT INTO territory_conflict_engagement_members
                            (engagement_id, conflict_id, front_id, status,
                             joined_at, left_at, updated_at)
                        VALUES (?, ?, ?, 'active', ?, NULL, ?)
                        ON CONFLICT(engagement_id, conflict_id, front_id) DO UPDATE SET
                            status = 'active', left_at = NULL, updated_at = excluded.updated_at
                        """,
                        (engagement_id, conflict_id, front_id, now, now),
                    )
                if is_new or domain_changed or geometry_changed:
                    changed.append(self._row(conn.execute(
                        "SELECT * FROM territory_conflict_engagements WHERE engagement_id = ?",
                        (engagement_id,),
                    ).fetchone()))

            for engagement in available.values():
                if protected_conflict_ids & set(engagement["member_conflict_ids"]):
                    continue
                missed = engagement["missed_publications"] + 1
                status = "changing" if missed == 1 else "resolved"
                engagement_version = engagement["engagement_version"] + 1
                snapshot_version = engagement["snapshot_version"] + 1
                resolved_at = now if status == "resolved" else None
                conn.execute(
                    """
                    UPDATE territory_conflict_engagements
                    SET status = ?, missed_publications = ?, engagement_version = ?,
                        snapshot_version = ?, updated_at = ?, resolved_at = ?
                    WHERE engagement_id = ?
                    """,
                    (status, missed, engagement_version, snapshot_version,
                     now, resolved_at, engagement["engagement_id"]),
                )
                if status == "resolved":
                    conn.execute(
                        "UPDATE territory_conflict_engagement_members "
                        "SET status = 'left', left_at = ?, updated_at = ? "
                        "WHERE engagement_id = ? AND status = 'active'",
                        (now, now, engagement["engagement_id"]),
                    )
                changed.append(self._row(conn.execute(
                    "SELECT * FROM territory_conflict_engagements WHERE engagement_id = ?",
                    (engagement["engagement_id"],),
                ).fetchone()))

            conn.execute(
                "UPDATE territory_conflict_engagement_coordinator "
                "SET lease_owner = '', lease_until = NULL, updated_at = ? "
                "WHERE coordinator_key = 'global' AND lease_owner = ?",
                (now, str(lease_owner)),
            )
            return {"ok": True, "changed": changed, "candidates": len(candidates)}


class TerritoryProgressionReceiptStore:
    """Durable, idempotent boundary for territory LVL/RSP progression."""

    STATUS_PENDING = "pending"
    STATUS_APPLIED = "applied"

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _row(row):
        if not row:
            return None
        return {
            "receipt_id": row["receipt_id"],
            "source_event_id": row["source_event_id"],
            "actor_username": row["actor_username"],
            "target_id": row["target_id"],
            "conflict_ids": loads_json(row["conflict_ids_json"], []),
            "baseline": loads_json(row["baseline_json"], {}),
            "status": row["status"],
            "result": loads_json(row["result_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "applied_at": row["applied_at"],
        }

    def ensure(self, source_event_id, actor_username, baseline, target_id="",
               conflict_ids=None):
        source_event_id = str(source_event_id or "").strip()
        actor_username = str(actor_username or "").strip()
        if not source_event_id or not actor_username:
            raise ValueError("source_event_id and actor_username are required")
        receipt_id = "territory_progression:" + hashlib.sha1(
            source_event_id.encode("utf-8")
        ).hexdigest()[:32]
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO territory_progression_receipts
                    (receipt_id, source_event_id, actor_username, target_id,
                     conflict_ids_json, baseline_json, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    receipt_id, source_event_id, actor_username,
                    str(target_id or ""),
                    dumps_json(sorted({str(value) for value in (conflict_ids or []) if value})),
                    dumps_json(baseline or {}), now, now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM territory_progression_receipts WHERE source_event_id = ?",
                (source_event_id,),
            ).fetchone()
            return self._row(row)

    def get(self, receipt_id):
        with db_connect(self.db_path) as conn:
            return self._row(conn.execute(
                "SELECT * FROM territory_progression_receipts WHERE receipt_id = ?",
                (str(receipt_id or ""),),
            ).fetchone())

    def list_pending(self, actor_username=None, conflict_id=None,
                     include_strategic=False, strategic_only=False):
        query = "SELECT * FROM territory_progression_receipts WHERE status = 'pending'"
        params = []
        if actor_username:
            query += " AND actor_username = ?"
            params.append(str(actor_username))
        query += " ORDER BY created_at, receipt_id"
        with db_connect(self.db_path) as conn:
            receipts = [self._row(row) for row in conn.execute(query, params).fetchall()]
        if strategic_only:
            receipts = [
                receipt for receipt in receipts
                if str((receipt.get("baseline") or {}).get("reward_type") or "")
                in {"territory_strategic", "conflict_resolution"}
            ]
        elif not include_strategic:
            receipts = [
                receipt for receipt in receipts
                if str((receipt.get("baseline") or {}).get("reward_type") or "")
                not in {"territory_strategic", "conflict_resolution"}
            ]
        if conflict_id:
            conflict_id = str(conflict_id)
            receipts = [
                receipt for receipt in receipts
                if conflict_id in set(receipt.get("conflict_ids") or [])
            ]
        return receipts

    def reject(self, receipt_id, reason):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE territory_progression_receipts
                SET status = 'rejected', result_json = ?, updated_at = ?
                WHERE receipt_id = ? AND status = 'pending'
                """,
                (dumps_json({"reason": str(reason or "capture_rejected")}),
                 now, str(receipt_id or "")),
            )
            return self._row(conn.execute(
                "SELECT * FROM territory_progression_receipts WHERE receipt_id = ?",
                (str(receipt_id or ""),),
            ).fetchone())

    def settle(self, receipt_id, progression, territory_stats, exp_value,
               system_messages=None):
        """Apply reward deltas and receipt state in one SQLite transaction."""
        receipt_id = str(receipt_id or "").strip()
        for _attempt in range(3):
            with db_connect(self.db_path) as conn:
                receipt = conn.execute(
                "SELECT * FROM territory_progression_receipts WHERE receipt_id = ?",
                (receipt_id,),
                ).fetchone()
            if not receipt:
                return {"ok": False, "reason": "receipt_not_found"}
            if receipt["status"] == self.STATUS_APPLIED:
                return {
                    "ok": True, "duplicate": True,
                    "result": loads_json(receipt["result_json"], {}),
                }
            if receipt["status"] != self.STATUS_PENDING:
                return {"ok": False, "reason": "receipt_not_pending"}
            with db_connect(self.db_path) as conn:
                user_row = conn.execute(
                    """
                    SELECT profile_json, profile_revision, profile_checksum,
                           profile_integrity_status
                    FROM users WHERE username = ?
                    """,
                    (receipt["actor_username"],),
                ).fetchone()
            if not user_row:
                return {"ok": False, "reason": "profile_not_found"}
            original_profile_json = user_row["profile_json"]
            original_profile, parse_errors = _parse_profile_json_strict(
                original_profile_json
            )
            original_validation = (
                validate_profile_candidate(original_profile, receipt["actor_username"])
                if original_profile is not None
                else {"valid": False, "errors": parse_errors}
            )
            if (
                user_row["profile_integrity_status"] != PROFILE_INTEGRITY_VALID
                or not original_validation["valid"]
                or profile_payload_checksum(original_profile)
                != str(user_row["profile_checksum"] or "")
            ):
                return {"ok": False, "reason": "profile_recovery_required"}
            original_revision = int(user_row["profile_revision"] or 0)
            profile = copy.deepcopy(original_profile)
            profile["respect"] = int(profile.get("respect", 0) or 0) + int(
                (progression or {}).get("respect_gain") or 0
            )
            profile["level"] = int(profile.get("level", 1) or 1) + int(
                (progression or {}).get("levels_gained") or 0
            )
            profile["territory_stats"] = copy.deepcopy(territory_stats or {})
            profile["exp"] = str(exp_value or profile.get("exp") or "")
            if system_messages:
                profile.setdefault("system_messages", []).extend(
                    copy.deepcopy(system_messages)
                )
            result_json = dumps_json(progression or {})
            now = utc_now()
            with db_connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                current = conn.execute(
                    "SELECT status, result_json FROM territory_progression_receipts WHERE receipt_id = ?",
                    (receipt_id,),
                ).fetchone()
                if not current:
                    return {"ok": False, "reason": "receipt_not_found"}
                if current["status"] == self.STATUS_APPLIED:
                    return {"ok": True, "duplicate": True, "result": loads_json(current["result_json"], {})}
                if current["status"] != self.STATUS_PENDING:
                    return {"ok": False, "reason": "receipt_not_pending"}
                profile, canonical_overlays = overlay_canonical_profile_scopes_with_conn(
                    conn, receipt["actor_username"], profile
                )
                validation = validate_profile_candidate(
                    profile, receipt["actor_username"]
                )
                if not validation["valid"]:
                    return {"ok": False, "reason": "profile_recovery_required"}
                profile_json = dumps_json(profile)
                profile_checksum = profile_payload_checksum(profile)
                _run_profile_precommit_guard(
                    None, conn, receipt["actor_username"], original_revision
                )
                updated = conn.execute(
                    """
                    UPDATE users
                    SET profile_json = ?, updated_at = ?, profile_revision = ?,
                        profile_schema_version = ?, profile_checksum = ?,
                        profile_integrity_status = ?, profile_validation_version = ?
                    WHERE username = ? AND profile_revision = ? AND profile_json = ?
                    """,
                    (
                        profile_json,
                        now,
                        original_revision + 1,
                        PROFILE_SCHEMA_VERSION,
                        profile_checksum,
                        PROFILE_INTEGRITY_VALID,
                        PROFILE_VALIDATION_VERSION,
                        receipt["actor_username"],
                        original_revision,
                        original_profile_json,
                    ),
                )
                if updated.rowcount != 1:
                    continue
                _write_profile_lkg(
                    conn,
                    receipt["actor_username"],
                    original_profile,
                    original_revision,
                    "prewrite:territory_progression.settle",
                    now,
                )
                applied = conn.execute(
                """
                UPDATE territory_progression_receipts
                SET status = 'applied', result_json = ?, updated_at = ?, applied_at = ?
                WHERE receipt_id = ? AND status = 'pending'
                """,
                    (result_json, now, now, receipt_id),
                )
                if applied.rowcount != 1:
                    raise RuntimeError("territory receipt CAS failed after profile update")
            return {
                "ok": True, "duplicate": False,
                "result": copy.deepcopy(progression or {}),
                "profile": profile,
                "profile_revision": original_revision + 1,
                "canonical_overlays": tuple(canonical_overlays),
            }
        return {"ok": False, "reason": "profile_changed"}

    def settle_strategic(self, receipt_id, encirclement=None,
                         conflict_resolutions=None, system_messages=None):
        """Atomically settle strategic territory rewards from the current LVL."""
        receipt_id = str(receipt_id or "").strip()
        encirclement = copy.deepcopy(encirclement or {})
        conflict_resolutions = copy.deepcopy(conflict_resolutions or [])
        for _attempt in range(3):
            with db_connect(self.db_path) as conn:
                receipt = conn.execute(
                "SELECT * FROM territory_progression_receipts WHERE receipt_id = ?",
                (receipt_id,),
                ).fetchone()
            if not receipt:
                return {"ok": False, "reason": "receipt_not_found"}
            if receipt["status"] == self.STATUS_APPLIED:
                return {
                    "ok": True, "duplicate": True,
                    "result": loads_json(receipt["result_json"], {}),
                }
            if receipt["status"] != self.STATUS_PENDING:
                return {"ok": False, "reason": "receipt_not_pending"}
            with db_connect(self.db_path) as conn:
                user_row = conn.execute(
                    """
                    SELECT profile_json, profile_revision, profile_checksum,
                           profile_integrity_status
                    FROM users WHERE username = ?
                    """,
                    (receipt["actor_username"],),
                ).fetchone()
            if not user_row:
                return {"ok": False, "reason": "profile_not_found"}

            original_profile_json = user_row["profile_json"]
            original_profile, parse_errors = _parse_profile_json_strict(
                original_profile_json
            )
            original_validation = (
                validate_profile_candidate(original_profile, receipt["actor_username"])
                if original_profile is not None
                else {"valid": False, "errors": parse_errors}
            )
            if (
                user_row["profile_integrity_status"] != PROFILE_INTEGRITY_VALID
                or not original_validation["valid"]
                or profile_payload_checksum(original_profile)
                != str(user_row["profile_checksum"] or "")
            ):
                return {"ok": False, "reason": "profile_recovery_required"}
            original_revision = int(user_row["profile_revision"] or 0)
            profile = copy.deepcopy(original_profile)
            level_before = max(1, int(profile.get("level", 1) or 1))
            transferred_pillars = max(
                0, int(encirclement.get("transferred_pillar_count") or 0)
            )
            encirclement_levels = 1 if encirclement.get("awarded") else 0
            encirclement_respect = transferred_pillars if encirclement_levels else 0
            normalized_resolutions = []
            seen_resolution_keys = set()
            for item in conflict_resolutions:
                conflict_id = str((item or {}).get("conflict_id") or "").strip()
                resolution_version = int((item or {}).get("resolution_version") or 0)
                reward_key = f"conflict:{conflict_id}:{resolution_version}"
                if not conflict_id or reward_key in seen_resolution_keys:
                    continue
                seen_resolution_keys.add(reward_key)
                normalized_resolutions.append({
                    "reward_key": reward_key,
                    "conflict_id": conflict_id,
                    "resolution_version": resolution_version,
                    "level_before": level_before,
                    "levels_gained": 1,
                    "respect_gain": level_before,
                })

            levels_gained = encirclement_levels + len(normalized_resolutions)
            respect_gain = encirclement_respect + sum(
                item["respect_gain"] for item in normalized_resolutions
            )
            result = {
                "territory_progression": {
                    "respect_gain": 0,
                    "levels_gained": 0,
                },
                "encirclement": {
                    "reward_key": str(encirclement.get("reward_key") or "encirclement"),
                    "levels_gained": encirclement_levels,
                    "transferred_pillar_count": transferred_pillars,
                    "respect_gain": encirclement_respect,
                },
                "conflict_resolutions": normalized_resolutions,
                "totals": {
                    "respect_gain": respect_gain,
                    "levels_gained": levels_gained,
                    "level_before": level_before,
                    "level_after": level_before + levels_gained,
                },
            }
            profile["respect"] = int(profile.get("respect", 0) or 0) + respect_gain
            profile["level"] = level_before + levels_gained
            if system_messages:
                profile.setdefault("system_messages", []).extend(
                    copy.deepcopy(system_messages)
                )
            result_json = dumps_json(result)
            now = utc_now()
            with db_connect(self.db_path) as conn:
                conn.execute("BEGIN IMMEDIATE")
                current = conn.execute(
                    "SELECT status, result_json FROM territory_progression_receipts WHERE receipt_id = ?",
                    (receipt_id,),
                ).fetchone()
                if not current:
                    return {"ok": False, "reason": "receipt_not_found"}
                if current["status"] == self.STATUS_APPLIED:
                    return {"ok": True, "duplicate": True, "result": loads_json(current["result_json"], {})}
                if current["status"] != self.STATUS_PENDING:
                    return {"ok": False, "reason": "receipt_not_pending"}
                profile, canonical_overlays = overlay_canonical_profile_scopes_with_conn(
                    conn, receipt["actor_username"], profile
                )
                validation = validate_profile_candidate(
                    profile, receipt["actor_username"]
                )
                if not validation["valid"]:
                    return {"ok": False, "reason": "profile_recovery_required"}
                profile_json = dumps_json(profile)
                profile_checksum = profile_payload_checksum(profile)
                _run_profile_precommit_guard(
                    None, conn, receipt["actor_username"], original_revision
                )
                updated = conn.execute(
                    """
                    UPDATE users
                    SET profile_json = ?, updated_at = ?, profile_revision = ?,
                        profile_schema_version = ?, profile_checksum = ?,
                        profile_integrity_status = ?, profile_validation_version = ?
                    WHERE username = ? AND profile_revision = ? AND profile_json = ?
                    """,
                    (
                        profile_json,
                        now,
                        original_revision + 1,
                        PROFILE_SCHEMA_VERSION,
                        profile_checksum,
                        PROFILE_INTEGRITY_VALID,
                        PROFILE_VALIDATION_VERSION,
                        receipt["actor_username"],
                        original_revision,
                        original_profile_json,
                    ),
                )
                if updated.rowcount != 1:
                    continue
                _write_profile_lkg(
                    conn,
                    receipt["actor_username"],
                    original_profile,
                    original_revision,
                    "prewrite:territory_progression.settle_strategic",
                    now,
                )
                applied = conn.execute(
                """
                UPDATE territory_progression_receipts
                SET status = 'applied', result_json = ?, updated_at = ?, applied_at = ?
                WHERE receipt_id = ? AND status = 'pending'
                """,
                    (result_json, now, now, receipt_id),
                )
                if applied.rowcount != 1:
                    raise RuntimeError("strategic territory receipt CAS failed after profile update")
            return {
                "ok": True, "duplicate": False,
                "result": copy.deepcopy(result),
                "profile": profile,
                "profile_revision": original_revision + 1,
                "canonical_overlays": tuple(canonical_overlays),
            }
        return {"ok": False, "reason": "profile_changed"}


class TerritoryTargetOwnershipStore:
    """Canonical CAS boundary for stationary territory target ownership."""

    RESULT_CAPTURED = "captured"
    RESULT_TARGET_STATE_CHANGED = "target_state_changed"
    RESULT_CANONICAL_OWNER_MISSING = "canonical_owner_missing"

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _row_payload(row):
        if not row:
            return None
        return {
            "target_id": row["target_id"],
            "owner_username": row["owner_username"],
            "ownership_version": int(row["ownership_version"] or 0),
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "label": row["label"],
            "target": loads_json(row["target_json"], {}),
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _receipt_payload(row):
        if not row:
            return None
        payload = loads_json(row["payload_json"], {})
        payload.update({
            "duplicate": True,
            "idempotent_replay": True,
            "result": row["result"],
            "target_id": row["target_id"],
            "winner_username": row["winner_username"],
            "ownership_version": int(row["ownership_version"] or 0),
            "set_id": row["set_id"],
        })
        return payload

    def get(self, target_id):
        with db_connect(self.db_path) as conn:
            return self._row_payload(conn.execute(
                "SELECT * FROM territory_target_ownership WHERE target_id = ?",
                (str(target_id),),
            ).fetchone())

    def list_map(self):
        """Return one request-scoped ownership snapshot without per-target reads."""
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM territory_target_ownership ORDER BY target_id"
            ).fetchall()
            return {
                row["target_id"]: self._row_payload(row)
                for row in rows
            }

    def capture(self, action_id, target_id, attacker_username, expected_owner_username,
                target, expected_version=None, conflict_ids=None, engagement_ids=None):
        """Capture once and durably enqueue the exact reconciliation scope."""
        action_id = str(action_id or "").strip()
        target_id = str(target_id or "").strip()
        attacker_username = str(attacker_username or "").strip()
        expected_owner_username = str(expected_owner_username or "").strip()
        if not action_id or not target_id or not attacker_username:
            raise ValueError("action_id, target_id and attacker_username are required")
        normalized = copy.deepcopy(target or {})
        lat = float(normalized.get("lat"))
        lng = float(normalized.get("lng", normalized.get("lon")))
        label = str(normalized.get("label") or "")
        conflict_ids = sorted({str(value) for value in (conflict_ids or []) if value})
        engagement_ids = sorted({str(value) for value in (engagement_ids or []) if value})
        now = utc_now()

        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            receipt = conn.execute(
                "SELECT * FROM territory_target_capture_receipts WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if receipt:
                return self._receipt_payload(receipt)

            current = conn.execute(
                "SELECT * FROM territory_target_ownership WHERE target_id = ?",
                (target_id,),
            ).fetchone()
            if not current:
                source_row = conn.execute(
                    """
                    SELECT owner_username, target_json
                    FROM captured_targets
                    WHERE ROUND(lat, 5) = ROUND(?, 5)
                      AND ROUND(lng, 5) = ROUND(?, 5)
                    ORDER BY updated_at DESC, id DESC
                    LIMIT 1
                    """,
                    (lat, lng),
                ).fetchone()
                initial_owner = str(
                    (source_row["owner_username"] if source_row else "") or ""
                )
                if not initial_owner:
                    payload = {
                        "ok": False,
                        "result": self.RESULT_CANONICAL_OWNER_MISSING,
                        "target_id": target_id,
                        "expected_owner_username": expected_owner_username,
                        "current_owner_username": "",
                        "ownership_version": 0,
                        "winner_username": "",
                        "set_id": "",
                        "duplicate": False,
                    }
                    conn.execute(
                        """
                        INSERT INTO territory_target_capture_receipts
                            (action_id, target_id, attacker_username,
                             expected_owner_username, expected_version, result,
                             winner_username, ownership_version, set_id,
                             payload_json, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, '', 0, '', ?, ?, ?)
                        """,
                        (action_id, target_id, attacker_username,
                         expected_owner_username,
                         int(expected_version) if expected_version not in (None, "") else None,
                         self.RESULT_CANONICAL_OWNER_MISSING,
                         dumps_json(payload), now, now),
                    )
                    return payload
                initial_target = (
                    loads_json(source_row["target_json"], normalized)
                    if source_row else normalized
                )
                conn.execute(
                    """
                    INSERT INTO territory_target_ownership
                        (target_id, owner_username, ownership_version, lat, lng,
                         label, target_json, updated_at)
                    VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                    """,
                    (target_id, initial_owner, lat, lng, label,
                     dumps_json(initial_target), now),
                )
                current = conn.execute(
                    "SELECT * FROM territory_target_ownership WHERE target_id = ?",
                    (target_id,),
                ).fetchone()

            current_owner = str(current["owner_username"] or "")
            current_version = int(current["ownership_version"] or 0)
            if current_owner == attacker_username:
                # A late final application step may arrive after an earlier
                # request from the same attacker already committed capture.
                # This is an idempotent success, not a multi-attacker CAS loss.
                set_seed = f"{target_id}|{current_version}"
                set_id = "territory_reconcile_" + hashlib.sha1(
                    set_seed.encode("utf-8")
                ).hexdigest()[:20]
                current_target = loads_json(current["target_json"], normalized)
                payload = {
                    "ok": True,
                    "result": self.RESULT_CAPTURED,
                    "target_id": target_id,
                    "current_owner_username": current_owner,
                    "ownership_version": current_version,
                    "winner_username": current_owner,
                    "set_id": set_id,
                    "target": current_target,
                    "duplicate": True,
                    "idempotent_replay": False,
                }
                conn.execute(
                    """
                    INSERT INTO territory_target_capture_receipts
                        (action_id, target_id, attacker_username,
                         expected_owner_username, expected_version, result,
                         winner_username, ownership_version, set_id, payload_json,
                         created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (action_id, target_id, attacker_username, expected_owner_username,
                     int(expected_version) if expected_version not in (None, "") else None,
                     self.RESULT_CAPTURED, current_owner, current_version, set_id,
                     dumps_json(payload), now, now),
                )
                return payload
            version_matches = expected_version in (None, "") or int(expected_version) == current_version
            owner_matches = current_owner == expected_owner_username
            if not owner_matches or not version_matches:
                payload = {
                    "ok": False,
                    "result": self.RESULT_TARGET_STATE_CHANGED,
                    "target_id": target_id,
                    "expected_owner_username": expected_owner_username,
                    "current_owner_username": current_owner,
                    "ownership_version": current_version,
                    "winner_username": current_owner,
                    "set_id": "",
                    "duplicate": False,
                }
                conn.execute(
                    """
                    INSERT INTO territory_target_capture_receipts
                        (action_id, target_id, attacker_username,
                         expected_owner_username, expected_version, result,
                         winner_username, ownership_version, set_id, payload_json,
                         created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?)
                    """,
                    (action_id, target_id, attacker_username, expected_owner_username,
                     int(expected_version) if expected_version not in (None, "") else None,
                     self.RESULT_TARGET_STATE_CHANGED, current_owner, current_version,
                     dumps_json(payload), now, now),
                )
                return payload

            next_version = current_version + 1
            normalized["owner_username"] = attacker_username
            normalized["ownership_version"] = next_version
            normalized["target_id"] = target_id
            normalized["lat"] = lat
            normalized["lng"] = lng
            normalized["lon"] = lng
            set_seed = f"{target_id}|{next_version}"
            set_id = "territory_reconcile_" + hashlib.sha1(set_seed.encode("utf-8")).hexdigest()[:20]
            cursor = conn.execute(
                """
                UPDATE territory_target_ownership
                SET owner_username = ?, ownership_version = ?, lat = ?, lng = ?,
                    label = ?, target_json = ?, updated_at = ?
                WHERE target_id = ? AND owner_username = ? AND ownership_version = ?
                """,
                (attacker_username, next_version, lat, lng, label,
                 dumps_json(normalized), now, target_id, current_owner, current_version),
            )
            if cursor.rowcount != 1:
                raise sqlite3.IntegrityError("territory ownership CAS lost")

            conn.execute(
                "DELETE FROM captured_targets WHERE ROUND(lat, 5) = ROUND(?, 5) "
                "AND ROUND(lng, 5) = ROUND(?, 5)",
                (lat, lng),
            )
            conn.execute(
                """
                INSERT INTO captured_targets
                    (owner_username, lat, lng, label, name, icon, source_type,
                     generated, stationary, target_json, captured_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (attacker_username, lat, lng, label,
                 str(normalized.get("name") or label), str(normalized.get("icon") or ""),
                 str(normalized.get("source_type") or ""),
                 1 if normalized.get("generated") else 0,
                 1 if normalized.get("stationary", not normalized.get("generated")) else 0,
                 dumps_json(normalized), str(normalized.get("captured_at") or now), now),
            )
            conn.execute(
                """
                INSERT INTO territory_conflict_reconciliation_sets
                    (set_id, target_id, winner_username, ownership_version,
                     conflict_ids_json, engagement_ids_json, status,
                     requested_version, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                ON CONFLICT(set_id) DO UPDATE SET
                    conflict_ids_json = excluded.conflict_ids_json,
                    engagement_ids_json = excluded.engagement_ids_json,
                    requested_version = MAX(requested_version, excluded.requested_version),
                    updated_at = excluded.updated_at
                """,
                (set_id, target_id, attacker_username, next_version,
                 dumps_json(conflict_ids), dumps_json(engagement_ids),
                 next_version, now, now),
            )
            for conflict_id in conflict_ids:
                latest = conn.execute(
                    "SELECT MAX(snapshot_version) AS version "
                    "FROM territory_conflict_snapshots WHERE conflict_id = ?",
                    (conflict_id,),
                ).fetchone()
                conn.execute(
                    """
                    INSERT OR IGNORE INTO territory_reconciliation_snapshot_gates
                        (set_id, conflict_id, public_snapshot_version, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (set_id, conflict_id, int((latest or {})["version"] or 0), now),
                )
            payload = {
                "ok": True,
                "result": self.RESULT_CAPTURED,
                "target_id": target_id,
                "winner_username": attacker_username,
                "previous_owner_username": current_owner,
                "ownership_version": next_version,
                "set_id": set_id,
                "target": normalized,
                "duplicate": False,
            }
            conn.execute(
                """
                INSERT INTO territory_target_capture_receipts
                    (action_id, target_id, attacker_username,
                     expected_owner_username, expected_version, result,
                     winner_username, ownership_version, set_id, payload_json,
                     created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (action_id, target_id, attacker_username, expected_owner_username,
                 int(expected_version) if expected_version not in (None, "") else None,
                 self.RESULT_CAPTURED, attacker_username, next_version, set_id,
                 dumps_json(payload), now, now),
            )
            return payload

    def capture_batch(self, action_id, attacker_username, transfers):
        """Atomically transfer a complete gameplay set after validating every CAS."""
        action_id = str(action_id or "").strip()
        attacker_username = str(attacker_username or "").strip()
        transfers = [copy.deepcopy(item) for item in (transfers or [])]
        if not action_id or not attacker_username or not transfers:
            raise ValueError("action_id, attacker_username and transfers are required")
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            plans = []
            seen = set()
            for index, item in enumerate(transfers):
                target_id = str(item.get("target_id") or "").strip()
                expected_owner = str(item.get("expected_owner_username") or "").strip()
                target = copy.deepcopy(item.get("target") or {})
                item_action_id = f"{action_id}:{target_id}"
                if not target_id or target_id in seen or not expected_owner:
                    return {
                        "ok": False, "result": self.RESULT_TARGET_STATE_CHANGED,
                        "reason": "invalid_batch_member", "index": index,
                        "target_id": target_id,
                    }
                seen.add(target_id)
                lat = float(target.get("lat"))
                lng = float(target.get("lng", target.get("lon")))
                receipt = conn.execute(
                    "SELECT * FROM territory_target_capture_receipts WHERE action_id = ?",
                    (item_action_id,),
                ).fetchone()
                if receipt:
                    replay = self._receipt_payload(receipt)
                    if replay.get("ok") and replay.get("winner_username") == attacker_username:
                        plans.append({"replay": replay})
                        continue
                    return {
                        "ok": False, "result": self.RESULT_TARGET_STATE_CHANGED,
                        "reason": "batch_receipt_conflict", "index": index,
                        "target_id": target_id,
                    }
                current = conn.execute(
                    "SELECT * FROM territory_target_ownership WHERE target_id = ?",
                    (target_id,),
                ).fetchone()
                if current:
                    current_owner = str(current["owner_username"] or "")
                    current_version = int(current["ownership_version"] or 0)
                    expected_version = item.get("expected_version")
                    version_matches = (
                        expected_version in (None, "")
                        or int(expected_version) == current_version
                    )
                else:
                    source = conn.execute(
                        "SELECT owner_username FROM captured_targets "
                        "WHERE ROUND(lat, 5) = ROUND(?, 5) AND ROUND(lng, 5) = ROUND(?, 5) "
                        "ORDER BY updated_at DESC, id DESC LIMIT 1",
                        (lat, lng),
                    ).fetchone()
                    current_owner = str((source["owner_username"] if source else "") or "")
                    current_version = 1 if current_owner else 0
                    expected_version = item.get("expected_version")
                    version_matches = (
                        expected_version in (None, "")
                        or int(expected_version) == current_version
                    )
                if current_owner != expected_owner or not version_matches:
                    return {
                        "ok": False, "result": self.RESULT_TARGET_STATE_CHANGED,
                        "reason": "batch_cas_mismatch", "index": index,
                        "target_id": target_id,
                        "expected_owner_username": expected_owner,
                        "current_owner_username": current_owner,
                        "ownership_version": current_version,
                    }
                plans.append({
                    "target_id": target_id, "target": target,
                    "lat": lat, "lng": lng,
                    "label": str(target.get("label") or ""),
                    "current_owner": current_owner,
                    "current_version": current_version,
                    "next_version": current_version + 1,
                    "action_id": item_action_id,
                    "conflict_ids": sorted({str(v) for v in item.get("conflict_ids") or [] if v}),
                    "engagement_ids": sorted({str(v) for v in item.get("engagement_ids") or [] if v}),
                })

            results = []
            for plan in plans:
                if plan.get("replay"):
                    results.append(plan["replay"])
                    continue
                target = plan["target"]
                target.update({
                    "target_id": plan["target_id"],
                    "owner_username": attacker_username,
                    "ownership_version": plan["next_version"],
                    "lat": plan["lat"], "lng": plan["lng"], "lon": plan["lng"],
                })
                set_seed = f"{plan['target_id']}|{plan['next_version']}"
                set_id = "territory_reconcile_" + hashlib.sha1(
                    set_seed.encode("utf-8")
                ).hexdigest()[:20]
                conn.execute(
                    """INSERT INTO territory_target_ownership
                       (target_id, owner_username, ownership_version, lat, lng, label,
                        target_json, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(target_id) DO UPDATE SET
                         owner_username=excluded.owner_username,
                         ownership_version=excluded.ownership_version,
                         lat=excluded.lat, lng=excluded.lng, label=excluded.label,
                         target_json=excluded.target_json, updated_at=excluded.updated_at""",
                    (plan["target_id"], attacker_username, plan["next_version"],
                     plan["lat"], plan["lng"], plan["label"], dumps_json(target), now),
                )
                conn.execute(
                    "DELETE FROM captured_targets WHERE ROUND(lat, 5) = ROUND(?, 5) "
                    "AND ROUND(lng, 5) = ROUND(?, 5)",
                    (plan["lat"], plan["lng"]),
                )
                conn.execute(
                    """INSERT INTO captured_targets
                       (owner_username, lat, lng, label, name, icon, source_type,
                        generated, stationary, target_json, captured_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (attacker_username, plan["lat"], plan["lng"], plan["label"],
                     str(target.get("name") or plan["label"]), str(target.get("icon") or ""),
                     str(target.get("source_type") or ""), 1 if target.get("generated") else 0,
                     1 if target.get("stationary", not target.get("generated")) else 0,
                     dumps_json(target), str(target.get("captured_at") or now), now),
                )
                conn.execute(
                    """INSERT INTO territory_conflict_reconciliation_sets
                       (set_id, target_id, winner_username, ownership_version,
                        conflict_ids_json, engagement_ids_json, status,
                        requested_version, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)
                       ON CONFLICT(set_id) DO UPDATE SET updated_at=excluded.updated_at""",
                    (set_id, plan["target_id"], attacker_username, plan["next_version"],
                     dumps_json(plan["conflict_ids"]), dumps_json(plan["engagement_ids"]),
                     plan["next_version"], now, now),
                )
                payload = {
                    "ok": True, "result": self.RESULT_CAPTURED,
                    "target_id": plan["target_id"],
                    "winner_username": attacker_username,
                    "previous_owner_username": plan["current_owner"],
                    "ownership_version": plan["next_version"],
                    "set_id": set_id, "target": target, "duplicate": False,
                }
                conn.execute(
                    """INSERT INTO territory_target_capture_receipts
                       (action_id, target_id, attacker_username,
                        expected_owner_username, expected_version, result,
                        winner_username, ownership_version, set_id, payload_json,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (plan["action_id"], plan["target_id"], attacker_username,
                     plan["current_owner"], plan["current_version"], self.RESULT_CAPTURED,
                     attacker_username, plan["next_version"], set_id,
                     dumps_json(payload), now, now),
                )
                results.append(payload)
            return {"ok": True, "result": self.RESULT_CAPTURED, "items": results}

    def extend_reconciliation_scope(self, set_id, conflict_ids=None, engagement_ids=None):
        conflict_ids = sorted({str(value) for value in (conflict_ids or []) if value})
        engagement_ids = sorted({str(value) for value in (engagement_ids or []) if value})
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM territory_conflict_reconciliation_sets WHERE set_id = ?",
                (str(set_id),),
            ).fetchone()
            if not row:
                return False
            merged_conflicts = sorted(set(loads_json(row["conflict_ids_json"], [])) | set(conflict_ids))
            merged_engagements = sorted(set(loads_json(row["engagement_ids_json"], [])) | set(engagement_ids))
            for conflict_id in merged_conflicts:
                latest = conn.execute(
                    "SELECT MAX(snapshot_version) AS version "
                    "FROM territory_conflict_snapshots WHERE conflict_id = ?",
                    (conflict_id,),
                ).fetchone()
                conn.execute(
                    """
                    INSERT OR IGNORE INTO territory_reconciliation_snapshot_gates
                        (set_id, conflict_id, public_snapshot_version, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (str(set_id), conflict_id, int((latest or {})["version"] or 0), now),
                )
            conn.execute(
                """
                UPDATE territory_conflict_reconciliation_sets
                SET conflict_ids_json = ?, engagement_ids_json = ?, updated_at = ?
                WHERE set_id = ?
                """,
                (dumps_json(merged_conflicts), dumps_json(merged_engagements), now, str(set_id)),
            )
            return True

    def public_snapshot_version(self, conflict_id):
        """Return a snapshot cap while any reconciliation set is unpublished."""
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT MIN(g.public_snapshot_version) AS version
                FROM territory_reconciliation_snapshot_gates g
                JOIN territory_conflict_reconciliation_sets s ON s.set_id = g.set_id
                WHERE g.conflict_id = ? AND s.status IN ('pending', 'processing')
                """,
                (str(conflict_id),),
            ).fetchone()
            if not row or row["version"] is None:
                return None
            return int(row["version"] or 0)

    def unpublished_snapshot_caps(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT g.conflict_id, MIN(g.public_snapshot_version) AS version
                FROM territory_reconciliation_snapshot_gates g
                JOIN territory_conflict_reconciliation_sets s ON s.set_id = g.set_id
                WHERE s.status IN ('pending', 'processing')
                GROUP BY g.conflict_id
                """
            ).fetchall()
            return {row["conflict_id"]: int(row["version"] or 0) for row in rows}

    def claim_reconciliation_set(self, lease_owner, lease_seconds=300):
        now_ts = time.time()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM territory_conflict_reconciliation_sets
                WHERE status IN ('pending', 'processing')
                  AND (status = 'pending' OR lease_until <= ?)
                ORDER BY created_at, set_id LIMIT 1
                """,
                (now_ts,),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE territory_conflict_reconciliation_sets
                SET status = 'processing', processing_version = requested_version,
                    lease_owner = ?, lease_until = ?, attempts = attempts + 1,
                    updated_at = ? WHERE set_id = ?
                """,
                (str(lease_owner), now_ts + max(1, int(lease_seconds)), utc_now(), row["set_id"]),
            )
            claimed = conn.execute(
                "SELECT * FROM territory_conflict_reconciliation_sets WHERE set_id = ?",
                (row["set_id"],),
            ).fetchone()
            return self._reconciliation_payload(claimed)

    @staticmethod
    def _reconciliation_payload(row):
        if not row:
            return None
        return {
            "set_id": row["set_id"], "target_id": row["target_id"],
            "winner_username": row["winner_username"],
            "ownership_version": int(row["ownership_version"] or 0),
            "conflict_ids": loads_json(row["conflict_ids_json"], []),
            "engagement_ids": loads_json(row["engagement_ids_json"], []),
            "status": row["status"],
            "requested_version": int(row["requested_version"] or 0),
            "processing_version": int(row["processing_version"] or 0),
            "attempts": int(row["attempts"] or 0),
        }

    def finish_reconciliation_set(self, set_id, lease_owner, ok=True, error=""):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE territory_conflict_reconciliation_sets
                SET status = ?, lease_owner = '', lease_until = 0, error = ?,
                    updated_at = ?, published_at = CASE WHEN ? THEN ? ELSE published_at END
                WHERE set_id = ? AND lease_owner = ?
                """,
                ("published" if ok else "pending", str(error or ""), now,
                 1 if ok else 0, now, str(set_id), str(lease_owner)),
            )
            return cursor.rowcount == 1


class TerritoryConflictStore:
    OPEN_STATUSES = ("detected", "active", "changing", "resolving")

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)
        self._migrate_legacy_pillars()

    @staticmethod
    def _row_to_conflict(row):
        if not row:
            return None
        participants = loads_json(row["participants_json"], [])
        if not participants:
            participants = [row["player_a_username"], row["player_b_username"]]
        area_ids = loads_json(row["area_ids_json"], [])
        if not area_ids:
            area_ids = [row["area_a_id"], row["area_b_id"]]
        intersections = loads_json(row["intersections_json"], [])
        if not intersections:
            intersection = loads_json(row["intersection_json"], [])
            intersections = [intersection] if intersection else []
        return {
            "id": row["id"],
            "conflict_id": str(row["conflict_id"] or row["id"]),
            "conflict_key": row["conflict_key"],
            "legacy_conflict_key": row["legacy_conflict_key"] or row["conflict_key"],
            "participant_key": row["participant_key"] or "::".join(sorted(participants)),
            "participant_usernames": participants,
            "primary_participant_usernames": [row["player_a_username"], row["player_b_username"]],
            "player_a_username": row["player_a_username"],
            "player_b_username": row["player_b_username"],
            "participants": participants,
            "primary_area_ids": [row["area_a_id"], row["area_b_id"]],
            "area_a_id": row["area_a_id"],
            "area_b_id": row["area_b_id"],
            "area_ids": area_ids,
            "intersection": loads_json(row["intersection_json"], []),
            "intersections": intersections,
            "targets": loads_json(row["targets_json"], []),
            "status": row["status"],
            "conflict_version": int(row["conflict_version"] or 1),
            "geometry_version": int(row["geometry_version"] or 1),
            "geometry_status": row["geometry_status"] or "published",
            "resolution_reason": row["resolution_reason"] or "",
            "last_actor_username": row["last_actor_username"],
            "source_event": row["source_event"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "resolved_at": row["resolved_at"],
            "closed_at": row["closed_at"],
        }

    @staticmethod
    def participant_key(participants):
        return "::".join(sorted({str(item) for item in (participants or []) if item}))

    @staticmethod
    def _same_json(left, right):
        return loads_json(dumps_json(left), None) == loads_json(dumps_json(right), None)

    def _pillar_domain_signature(self, targets):
        """Compare pillar gameplay state without treating geometry as identity."""
        signature = []
        for item in targets or []:
            item = item or {}
            target = item.get("target") if isinstance(item.get("target"), dict) else {}
            signature.append({
                "target_id": self.stable_target_id(item),
                "front_id": str(item.get("front_id") or target.get("front_id") or ""),
                "owner_username": str(
                    item.get("owner_username") or item.get("owner") or
                    target.get("owner_username") or ""
                ),
                "previous_owner_username": str(
                    item.get("previous_owner_username") or item.get("previous_owner") or ""
                ),
                "status": str(item.get("status") or "contested"),
                "captured": bool(item.get("captured") or item.get("status") == "captured"),
                "captured_by": str(item.get("captured_by") or item.get("hacked_by") or ""),
            })
        return sorted(signature, key=lambda item: item["target_id"])

    def _effective_targets(self, existing_targets, incoming_targets):
        """Refresh public target data while preserving monotonic capture state."""
        existing_by_id = {
            self.stable_target_id(item): copy.deepcopy(item or {})
            for item in (existing_targets or [])
        }
        effective = []
        seen = set()
        for incoming in incoming_targets or []:
            incoming = copy.deepcopy(incoming or {})
            target_id = self.stable_target_id(incoming)
            stored = existing_by_id.get(target_id)
            if stored and bool(stored.get("captured") or stored.get("status") == "captured"):
                refreshed_target = incoming.get("target") if isinstance(incoming.get("target"), dict) else {}
                stored_target = stored.get("target") if isinstance(stored.get("target"), dict) else {}
                incoming.update({
                    "target_id": target_id,
                    "owner": stored.get("owner_username") or stored.get("owner") or "",
                    "owner_username": stored.get("owner_username") or stored.get("owner") or "",
                    "previous_owner": stored.get("previous_owner_username") or stored.get("previous_owner") or "",
                    "previous_owner_username": stored.get("previous_owner_username") or stored.get("previous_owner") or "",
                    "status": stored.get("status") or "captured",
                    "captured": True,
                    "captured_by": stored.get("captured_by") or stored.get("hacked_by") or "",
                    "hacked_by": stored.get("captured_by") or stored.get("hacked_by") or "",
                })
                incoming["target"] = {
                    **stored_target,
                    **refreshed_target,
                    "target_id": target_id,
                    "owner_username": incoming["owner_username"],
                }
            else:
                incoming["target_id"] = target_id
                if isinstance(incoming.get("target"), dict):
                    incoming["target"]["target_id"] = target_id
            effective.append(incoming)
            seen.add(target_id)
        for target_id, stored in existing_by_id.items():
            if target_id not in seen:
                effective.append(stored)
        return effective

    @staticmethod
    def stable_target_id(item):
        item = item or {}
        target = item.get("target") if isinstance(item.get("target"), dict) else item
        explicit_target_id = target.get("target_id") or item.get("target_id")
        if explicit_target_id not in (None, ""):
            return str(explicit_target_id)
        for key, prefix in (
            ("vulnerability_id", "vulnerability"),
            ("captured_target_id", "captured"),
            ("poi_id", "poi"),
            ("source_target_id", "source"),
            ("source_id", "source"),
            ("id", "target"),
        ):
            value = target.get(key) or item.get(key)
            if value not in (None, ""):
                value = str(value)
                return value if ":" in value else f"{prefix}:{value}"
        legacy = {
            "source_type": target.get("source_type") or item.get("source_type") or "unknown",
            "label": target.get("label") or target.get("name") or item.get("label") or "",
            "lat": target.get("lat"),
            "lng": target.get("lng", target.get("lon")),
        }
        digest = hashlib.sha256(dumps_json(legacy).encode("utf-8")).hexdigest()[:20]
        return f"legacy:{digest}"

    def _migrate_legacy_pillars(self):
        """Populate the pillar registry from the legacy targets projection once."""
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM territory_conflicts ORDER BY id"
            ).fetchall()
            for row in rows:
                conflict = self._row_to_conflict(row)
                legacy_targets = conflict.get("targets") or []
                if not legacy_targets:
                    continue
                self._sync_pillars(
                    conn,
                    conflict["conflict_id"],
                    legacy_targets,
                    conflict["conflict_version"],
                    conflict["geometry_version"],
                    actor_username=conflict.get("last_actor_username") or "migration",
                )
                projected = self._project_targets(
                    conn, conflict["conflict_id"], legacy_targets
                )
                conn.execute(
                    "UPDATE territory_conflicts SET targets_json = ? WHERE id = ?",
                    (dumps_json(projected), conflict["id"]),
                )

    @staticmethod
    def _row_to_pillar(row):
        if not row:
            return None
        return {
            "id": row["id"],
            "conflict_id": row["conflict_id"],
            "target_id": row["target_id"],
            "front_id": row["front_id"],
            "owner_username": row["owner_username"],
            "previous_owner_username": row["previous_owner_username"],
            "attacker_username": row["attacker_username"],
            "status": row["status"],
            "captured": bool(row["captured"]),
            "captured_by": row["captured_by"],
            "last_changed_version": int(row["last_changed_version"] or 1),
            "geometry_applied_version": int(row["geometry_applied_version"] or 0),
            "public_target": loads_json(row["public_target_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "captured_at": row["captured_at"],
        }

    def _project_targets(self, conn, conflict_id, fallback=None):
        rows = conn.execute(
            "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? ORDER BY id",
            (str(conflict_id),),
        ).fetchall()
        if not rows:
            return list(fallback or [])
        return [loads_json(row["public_target_json"], {}) for row in rows]

    def _conflict_from_row(self, conn, row):
        conflict = self._row_to_conflict(row)
        if conflict:
            conflict["targets"] = self._project_targets(
                conn, conflict["conflict_id"], conflict.get("targets")
            )
        return conflict

    def _record_event(self, conn, event_type, conflict_id, target_id,
                      conflict_version, geometry_version, actor_username="",
                      action_id="", payload=None, event_id=None):
        event_id = event_id or (
            f"{event_type}:{conflict_id}:{target_id}:{conflict_version}"
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO territory_conflict_events
                (event_id, event_type, conflict_id, target_id, action_id,
                 conflict_version, geometry_version, actor_username,
                 payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_id, event_type, str(conflict_id), str(target_id or ""),
             str(action_id or ""), int(conflict_version), int(geometry_version),
             str(actor_username or ""), dumps_json(payload or {}), utc_now()),
        )
        return event_id

    def _sync_pillars(self, conn, conflict_id, targets, conflict_version,
                      geometry_version, actor_username=""):
        now = utc_now()
        for item in targets or []:
            target_id = self.stable_target_id(item)
            normalized = copy.deepcopy(item or {})
            normalized["target_id"] = target_id
            target = normalized.get("target")
            if isinstance(target, dict):
                target["target_id"] = target_id
            existing = conn.execute(
                "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? AND target_id = ?",
                (str(conflict_id), target_id),
            ).fetchone()
            owner = str(normalized.get("owner_username") or normalized.get("owner") or "")
            captured = bool(normalized.get("captured") or normalized.get("status") == "captured")
            if existing:
                stored = self._row_to_pillar(existing)
                if stored["captured"]:
                    normalized.update({
                        "owner": stored["owner_username"],
                        "owner_username": stored["owner_username"],
                        "previous_owner": stored["previous_owner_username"],
                        "status": stored["status"],
                        "captured": True,
                        "captured_by": stored["captured_by"],
                        "hacked_by": stored["captured_by"],
                    })
                    if isinstance(normalized.get("target"), dict):
                        normalized["target"]["owner_username"] = stored["owner_username"]
                    conn.execute(
                        "UPDATE territory_conflict_pillars SET public_target_json = ?, updated_at = ? "
                        "WHERE id = ?",
                        (dumps_json(normalized), now, existing["id"]),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE territory_conflict_pillars SET
                            front_id = ?, owner_username = ?, previous_owner_username = ?,
                            attacker_username = ?, status = ?, captured = ?, captured_by = ?,
                            last_changed_version = ?, public_target_json = ?, updated_at = ?,
                            captured_at = ?
                        WHERE id = ?
                        """,
                        (str(normalized.get("front_id") or ""), owner,
                         str(normalized.get("previous_owner_username") or normalized.get("previous_owner") or ""),
                         str(actor_username or ""), str(normalized.get("status") or "contested"),
                         int(captured), str(normalized.get("captured_by") or normalized.get("hacked_by") or ""),
                         int(conflict_version), dumps_json(normalized), now,
                         now if captured else None, existing["id"]),
                    )
                continue
            conn.execute(
                """
                INSERT INTO territory_conflict_pillars
                    (conflict_id, target_id, front_id, owner_username,
                     previous_owner_username, attacker_username, status, captured,
                     captured_by, last_changed_version, geometry_applied_version,
                     public_target_json, created_at, updated_at, captured_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (str(conflict_id), target_id, str(normalized.get("front_id") or ""), owner,
                 str(normalized.get("previous_owner") or ""), str(actor_username or ""),
                 str(normalized.get("status") or "contested"), int(captured),
                 str(normalized.get("captured_by") or ""), int(conflict_version),
                 int(geometry_version), dumps_json(normalized), now, now,
                 now if captured else None),
            )
            self._record_event(
                conn, "conflict.pillar_registered", conflict_id, target_id,
                conflict_version, geometry_version, actor_username=actor_username,
            )

    def _find_reference_row(self, conn, reference):
        if reference in (None, ""):
            return None
        value = str(reference)
        return conn.execute(
            """
            SELECT * FROM territory_conflicts
            WHERE conflict_id = ? OR conflict_key = ? OR legacy_conflict_key = ?
               OR CAST(id AS TEXT) = ?
            ORDER BY CASE WHEN conflict_id = ? THEN 0 WHEN conflict_key = ? THEN 1 ELSE 2 END,
                     id DESC
            LIMIT 1
            """,
            (value, value, value, value, value, value),
        ).fetchone()

    def get_open_by_participant_key(self, participant_key):
        conflicts = self.list_open_by_participant_key(participant_key)
        return conflicts[0] if conflicts else None

    def list_open_by_participant_key(self, participant_key):
        placeholders = ",".join("?" for _ in self.OPEN_STATUSES)
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM territory_conflicts
                WHERE participant_key = ? AND status IN ({placeholders})
                ORDER BY updated_at DESC, id DESC
                """,
                (participant_key, *self.OPEN_STATUSES),
            ).fetchall()
            return [self._conflict_from_row(conn, row) for row in rows]

    def select_open_conflict(self, participant_key, conflict_key=None, area_ids=None):
        """Find the current cycle without treating participants as its identity."""
        candidates = self.list_open_by_participant_key(participant_key)
        if not candidates:
            return None

        # A single open cycle is unambiguous. Geometry is mutable and may be
        # temporarily absent or completely replaced during consolidation, so
        # requiring an alias/area overlap here would create a new conflict_id
        # for the same continuing participant cycle.
        if len(candidates) == 1:
            return candidates[0]

        geometry_reference = str(conflict_key or "")
        if geometry_reference:
            for candidate in candidates:
                aliases = {
                    str(candidate.get("conflict_key") or ""),
                    str(candidate.get("legacy_conflict_key") or ""),
                }
                if geometry_reference in aliases:
                    return candidate

        incoming_area_ids = {
            str(area_id) for area_id in (area_ids or []) if area_id is not None
        }
        if not incoming_area_ids:
            return None

        ranked = []
        for candidate in candidates:
            candidate_area_ids = {
                str(area_id)
                for area_id in (candidate.get("area_ids") or [])
                if area_id is not None
            }
            overlap = len(incoming_area_ids & candidate_area_ids)
            if overlap:
                ranked.append((overlap, candidate))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (item[0], int(item[1].get("id") or 0)), reverse=True)
        return ranked[0][1]

    def upsert_conflict(self, conflict):
        participants = sorted({
            str(participant)
            for participant in (conflict.get("participants") or [
                conflict.get("player_a_username"),
                conflict.get("player_b_username"),
            ])
            if participant
        })
        if len(participants) < 2:
            raise ValueError("Territory conflict requires at least two participants.")

        area_ids = [
            area_id for area_id in (conflict.get("area_ids") or [
                conflict.get("area_a_id"),
                conflict.get("area_b_id"),
            ])
            if area_id is not None
        ]
        intersections = conflict.get("intersections") or []
        if not intersections and conflict.get("intersection"):
            intersections = [conflict.get("intersection")]

        now = utc_now()
        participant_key = self.participant_key(participants)
        geometry_key = str(
            conflict.get("legacy_conflict_key") or conflict.get("conflict_key") or ""
        )
        if not geometry_key:
            raise ValueError("Territory conflict requires conflict_key.")

        with db_connect(self.db_path) as conn:
            explicit_reference = conflict.get("conflict_id") or conflict.get("id")
            row = self._find_reference_row(conn, explicit_reference)
            if row is None:
                candidate = self.select_open_conflict(
                    participant_key,
                    conflict_key=conflict.get("conflict_key"),
                    area_ids=area_ids,
                )
                if candidate:
                    row = self._find_reference_row(conn, candidate.get("conflict_id"))

            existing = self._conflict_from_row(conn, row) if row else None
            requested_status = str(conflict.get("status") or "active")
            resolution_reason = str(conflict.get("resolution_reason") or "")
            if requested_status == "resolved_by_encirclement":
                requested_status = "resolved"
                resolution_reason = resolution_reason or "encirclement"

            if existing and existing["status"] in {"resolved", "closed"}:
                # Explicit legacy references may inspect a closed cycle, but never reopen it.
                if requested_status in self.OPEN_STATUSES:
                    existing = None
                    row = None

            incoming_targets = list(conflict.get("targets") or [])
            effective_targets = self._effective_targets(
                existing.get("targets") if existing else [], incoming_targets
            )

            data = {
                "conflict_key": existing["conflict_key"] if existing else geometry_key,
                "conflict_id": existing["conflict_id"] if existing else f"territory_conflict_{secrets.token_hex(8)}",
                "legacy_conflict_key": existing["legacy_conflict_key"] if existing else geometry_key,
                "participant_key": participant_key,
                "player_a_username": participants[0],
                "player_b_username": participants[1],
                "area_a_id": area_ids[0] if area_ids else None,
                "area_b_id": area_ids[1] if len(area_ids) > 1 else None,
                "participants_json": dumps_json(participants),
                "area_ids_json": dumps_json(area_ids),
                "intersection_json": dumps_json(conflict.get("intersection") or (intersections[0] if intersections else [])),
                "intersections_json": dumps_json(intersections),
                "targets_json": dumps_json(effective_targets),
                "status": requested_status,
                "geometry_status": str(conflict.get("geometry_status") or "published"),
                "resolution_reason": resolution_reason,
                "last_actor_username": str(conflict.get("last_actor_username") or ""),
                "source_event": str(conflict.get("source_event") or ""),
                "created_at": existing["created_at"] if existing else now,
                "updated_at": now,
                "resolved_at": existing.get("resolved_at") if existing else None,
                "closed_at": existing.get("closed_at") if existing else None,
            }

            if data["status"] in {"resolved", "closed"} and not data["resolved_at"]:
                data["resolved_at"] = now
            if data["status"] == "closed" and not data["closed_at"]:
                data["closed_at"] = now

            geometry_changed = not existing or any((
                existing.get("area_ids") != area_ids,
                not self._same_json(existing.get("intersections") or [], intersections),
                existing.get("geometry_status") != data["geometry_status"],
            ))
            domain_changed = not existing or any((
                existing.get("participants") != participants,
                self._pillar_domain_signature(existing.get("targets") or []) !=
                self._pillar_domain_signature(effective_targets),
                existing.get("status") != data["status"],
                existing.get("resolution_reason") != data["resolution_reason"],
            ))
            data["conflict_version"] = (
                (existing.get("conflict_version", 1) + 1) if existing and domain_changed
                else (existing.get("conflict_version", 1) if existing else 1)
            )
            data["geometry_version"] = (
                (existing.get("geometry_version", 1) + 1) if existing and geometry_changed
                else (existing.get("geometry_version", 1) if existing else 1)
            )

            if existing and not domain_changed and not geometry_changed:
                self._sync_pillars(
                    conn, existing["conflict_id"], incoming_targets,
                    existing["conflict_version"], existing["geometry_version"],
                    actor_username=data["last_actor_username"],
                )
                projected = self._project_targets(conn, existing["conflict_id"], existing["targets"])
                conn.execute(
                    "UPDATE territory_conflicts SET targets_json = ? WHERE id = ?",
                    (dumps_json(projected), existing["id"]),
                )
                existing["targets"] = projected
                return existing

            if not existing:
                base_key = data["conflict_key"]
                suffix = 1
                while conn.execute(
                    "SELECT 1 FROM territory_conflicts WHERE conflict_key = ?", (data["conflict_key"],)
                ).fetchone():
                    suffix += 1
                    data["conflict_key"] = f"{base_key}:cycle:{suffix}"
                conn.execute(
                """
                INSERT INTO territory_conflicts
                    (conflict_key, conflict_id, legacy_conflict_key, participant_key,
                     player_a_username, player_b_username, area_a_id, area_b_id,
                     participants_json, area_ids_json, intersection_json, intersections_json,
                     targets_json, status, conflict_version, geometry_version, geometry_status,
                     resolution_reason, last_actor_username, source_event, created_at, updated_at,
                     resolved_at, closed_at)
                VALUES
                    (:conflict_key, :conflict_id, :legacy_conflict_key, :participant_key,
                     :player_a_username, :player_b_username, :area_a_id, :area_b_id,
                     :participants_json, :area_ids_json, :intersection_json, :intersections_json,
                     :targets_json, :status, :conflict_version, :geometry_version, :geometry_status,
                     :resolution_reason, :last_actor_username, :source_event, :created_at, :updated_at,
                     :resolved_at, :closed_at)
                """,
                    data,
                )
            else:
                data["id"] = existing["id"]
                conn.execute(
                """
                UPDATE territory_conflicts SET
                    participant_key = :participant_key,
                    player_a_username = :player_a_username,
                    player_b_username = :player_b_username,
                    area_a_id = :area_a_id,
                    area_b_id = :area_b_id,
                    participants_json = :participants_json,
                    area_ids_json = :area_ids_json,
                    intersection_json = :intersection_json,
                    intersections_json = :intersections_json,
                    targets_json = :targets_json,
                    status = :status,
                    conflict_version = :conflict_version,
                    geometry_version = :geometry_version,
                    geometry_status = :geometry_status,
                    resolution_reason = :resolution_reason,
                    last_actor_username = :last_actor_username,
                    source_event = :source_event,
                    updated_at = :updated_at,
                    resolved_at = :resolved_at,
                    closed_at = :closed_at
                WHERE id = :id
                """,
                    data,
                )
            row = conn.execute(
                "SELECT * FROM territory_conflicts WHERE conflict_id = ?",
                (data["conflict_id"],),
            ).fetchone()
            self._sync_pillars(
                conn, data["conflict_id"], incoming_targets,
                data["conflict_version"], data["geometry_version"],
                actor_username=data["last_actor_username"],
            )
            projected = self._project_targets(conn, data["conflict_id"], effective_targets)
            conn.execute(
                "UPDATE territory_conflicts SET targets_json = ? WHERE conflict_id = ?",
                (dumps_json(projected), data["conflict_id"]),
            )
            row = conn.execute(
                "SELECT * FROM territory_conflicts WHERE conflict_id = ?",
                (data["conflict_id"],),
            ).fetchone()
            return self._conflict_from_row(conn, row)

    def list_active_for_player(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM territory_conflicts
                WHERE status IN ('detected', 'active', 'changing', 'resolving')
                    AND (
                        player_a_username = ?
                        OR player_b_username = ?
                        OR participants_json LIKE ?
                    )
                ORDER BY updated_at DESC, id DESC
                """,
                (username, username, f'%"{username}"%'),
            ).fetchall()
            return [self._conflict_from_row(conn, row) for row in rows]

    def get_by_key(self, conflict_key):
        with db_connect(self.db_path) as conn:
            row = self._find_reference_row(conn, conflict_key)
            return self._conflict_from_row(conn, row) if row else None

    def list_pillars(self, conflict_reference):
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return []
            rows = conn.execute(
                "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? ORDER BY id",
                (str(conflict_row["conflict_id"] or conflict_row["id"]),),
            ).fetchall()
            return [self._row_to_pillar(row) for row in rows]

    def reconcile_rebuild_pillars(self, conflict_reference, targets,
                                  conflict_version, actor_username=""):
        """Apply pillars discovered from the same geometry used by publication."""
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return []
            conflict = self._conflict_from_row(conn, conflict_row)
            conflict_id = conflict["conflict_id"]
            effective_version = max(
                int(conflict.get("conflict_version") or 0),
                int(conflict_version or 0),
            )
            incoming = list(targets or [])
            self._sync_pillars(
                conn, conflict_id, incoming, effective_version,
                int(conflict.get("geometry_version") or 0),
                actor_username=actor_username,
            )
            incoming_ids = {self.stable_target_id(item) for item in incoming}
            participants = set(conflict.get("participants") or [])
            stale_rows = conn.execute(
                "SELECT * FROM territory_conflict_pillars "
                "WHERE conflict_id = ? AND captured = 0",
                (conflict_id,),
            ).fetchall()
            for row in stale_rows:
                if str(row["target_id"]) in incoming_ids:
                    continue
                stored = self._row_to_pillar(row)
                public_target = loads_json(row["public_target_json"], {})
                target = public_target.get("target") or public_target.get("public_target") or public_target
                try:
                    lat = float(target.get("lat"))
                    lng = float(target.get("lng", target.get("lon")))
                except (AttributeError, TypeError, ValueError):
                    continue
                owner_row = conn.execute(
                    """
                    SELECT owner_username, target_json FROM captured_targets
                    WHERE ROUND(lat, 5) = ROUND(?, 5)
                      AND ROUND(lng, 5) = ROUND(?, 5)
                    ORDER BY updated_at DESC LIMIT 1
                    """,
                    (lat, lng),
                ).fetchone()
                current_owner = str(owner_row["owner_username"] or "") if owner_row else ""
                if (
                    not current_owner
                    or current_owner == stored["owner_username"]
                    or current_owner not in participants
                ):
                    continue
                current_target = loads_json(owner_row["target_json"], {})
                public_target.update({
                    "owner": current_owner,
                    "owner_username": current_owner,
                    "previous_owner": stored["owner_username"],
                    "status": "captured",
                    "captured": True,
                    "captured_by": current_owner,
                    "hacked_by": current_owner,
                })
                public_target["target"] = {
                    **target,
                    **current_target,
                    "target_id": stored["target_id"],
                    "owner_username": current_owner,
                }
                conn.execute(
                    """
                    UPDATE territory_conflict_pillars SET
                        owner_username = ?, previous_owner_username = ?,
                        attacker_username = ?, status = 'captured', captured = 1,
                        captured_by = ?, last_changed_version = ?,
                        public_target_json = ?, updated_at = ?, captured_at = ?
                    WHERE id = ?
                    """,
                    (current_owner, stored["owner_username"], current_owner,
                     current_owner, effective_version, dumps_json(public_target),
                     now, now, row["id"]),
                )
                self._record_event(
                    conn, "conflict.pillar_captured", conflict_id,
                    stored["target_id"], effective_version,
                    int(conflict.get("geometry_version") or 0),
                    actor_username=current_owner,
                    action_id=f"reconcile_owner:{conflict_id}:{stored['target_id']}:{effective_version}",
                    payload={"recovered_from_owner_store": True},
                )
            projected = self._project_targets(conn, conflict_id, incoming)
            conn.execute(
                "UPDATE territory_conflicts SET targets_json = ?, updated_at = ? WHERE conflict_id = ?",
                (dumps_json(projected), now, conflict_id),
            )
            return [self._row_to_pillar(row) for row in conn.execute(
                "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? ORDER BY id",
                (conflict_id,),
            ).fetchall()]

    def detach_rebuild_pillars(self, conflict_reference, target_ids,
                               conflict_version, reason="consistency_reconcile"):
        """Detach explicitly invalid geometry anchors without deleting objects."""
        target_ids = sorted({str(item or "").strip() for item in target_ids if str(item or "").strip()})
        if not target_ids:
            return []
        now = utc_now()
        detached = []
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return []
            conflict = self._conflict_from_row(conn, conflict_row)
            conflict_id = conflict["conflict_id"]
            effective_version = max(
                int(conflict.get("conflict_version") or 0),
                int(conflict_version or 0),
            )
            for target_id in target_ids:
                row = conn.execute(
                    "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? AND target_id = ?",
                    (conflict_id, target_id),
                ).fetchone()
                if not row or bool(row["captured"]):
                    continue
                public_target = loads_json(row["public_target_json"], {})
                public_target["status"] = "detached"
                public_target["removed"] = True
                public_target["detach_reason"] = str(reason or "consistency_reconcile")
                conn.execute(
                    """
                    UPDATE territory_conflict_pillars SET
                        status = 'detached', last_changed_version = ?,
                        public_target_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (effective_version, dumps_json(public_target), now, row["id"]),
                )
                self._record_event(
                    conn, "conflict.pillar_detached", conflict_id, target_id,
                    effective_version, int(conflict.get("geometry_version") or 0),
                    payload={"reason": str(reason or "consistency_reconcile")},
                )
                detached.append(target_id)
            if detached:
                projected = self._project_targets(conn, conflict_id, conflict.get("targets"))
                conn.execute(
                    "UPDATE territory_conflicts SET targets_json = ?, updated_at = ? WHERE conflict_id = ?",
                    (dumps_json(projected), now, conflict_id),
                )
        return detached

    def list_events(self, conflict_reference, event_type=None):
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return []
            conflict_id = str(conflict_row["conflict_id"] or conflict_row["id"])
            sql = "SELECT * FROM territory_conflict_events WHERE conflict_id = ?"
            params = [conflict_id]
            if event_type:
                sql += " AND event_type = ?"
                params.append(str(event_type))
            sql += " ORDER BY created_at, event_id"
            rows = conn.execute(sql, tuple(params)).fetchall()
            return [{
                "event_id": row["event_id"],
                "type": row["event_type"],
                "conflict_id": row["conflict_id"],
                "target_id": row["target_id"],
                "action_id": row["action_id"],
                "conflict_version": int(row["conflict_version"]),
                "geometry_version": int(row["geometry_version"]),
                "actor_username": row["actor_username"],
                "payload": loads_json(row["payload_json"], {}),
                "created_at": row["created_at"],
            } for row in rows]

    def _request_rebuild_in_conn(self, conn, conflict_id, reason, requested_version, now=None):
        now = now or utc_now()
        conflict_id = str(conflict_id)
        requested_version = max(1, int(requested_version or 1))
        row = conn.execute(
                "SELECT * FROM territory_conflict_rebuilds WHERE conflict_id = ?",
                (conflict_id,),
            ).fetchone()
        if row:
            highest = max(int(row["requested_version"] or 0), requested_version)
            status = "running" if row["status"] == "running" else "pending"
            conn.execute(
                    """
                    UPDATE territory_conflict_rebuilds
                    SET requested_version = ?, status = ?, reason = ?,
                        requested_at = ?, updated_at = ?
                    WHERE conflict_id = ?
                    """,
                    (highest, status, str(reason or "conflict_change"), now, now, conflict_id),
                )
        else:
            conn.execute(
                    """
                    INSERT INTO territory_conflict_rebuilds
                        (conflict_id, requested_version, status, reason,
                         requested_at, updated_at)
                    VALUES (?, ?, 'pending', ?, ?, ?)
                    """,
                    (conflict_id, requested_version, str(reason or "conflict_change"), now, now),
                )
        return {
            "conflict_id": conflict_id,
            "requested_version": highest if row else requested_version,
            "status": status if row else "pending",
        }

    def request_rebuild(self, conflict_reference, reason, requested_version):
        """Persist the highest requested input version for a conflict."""
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return None
            conflict_id = str(conflict_row["conflict_id"] or conflict_row["id"])
            return self._request_rebuild_in_conn(
                conn, conflict_id, reason, requested_version
            )

    def claim_rebuild(self, conflict_reference, lease_owner, lease_seconds=120):
        """Claim a durable rebuild lease; expired leases are safe to take over."""
        now = utc_now()
        lease_until = (datetime.utcnow() + timedelta(seconds=max(10, int(lease_seconds)))).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return None
            conflict_id = str(conflict_row["conflict_id"] or conflict_row["id"])
            row = conn.execute(
                "SELECT * FROM territory_conflict_rebuilds WHERE conflict_id = ?",
                (conflict_id,),
            ).fetchone()
            if not row:
                return None
            lease_active = (
                row["status"] == "running" and row["lease_until"] and
                str(row["lease_until"]) > now and row["lease_owner"] != str(lease_owner)
            )
            if lease_active:
                return None
            processing_version = int(row["requested_version"] or 0)
            cursor = conn.execute(
                """
                UPDATE territory_conflict_rebuilds
                SET status = 'running', processing_version = ?, lease_owner = ?,
                    lease_until = ?, attempts = attempts + 1,
                    started_at = ?, updated_at = ?, last_error = ''
                WHERE conflict_id = ?
                  AND (status != 'running' OR lease_until IS NULL OR lease_until <= ? OR lease_owner = ?)
                """,
                (processing_version, str(lease_owner), lease_until, now, now,
                 conflict_id, now, str(lease_owner)),
            )
            if cursor.rowcount != 1:
                return None
            conflict = self._conflict_from_row(conn, conflict_row)
            self._record_event(
                conn, "conflict.rebuild_started", conflict_id, "",
                processing_version, conflict["geometry_version"],
                payload={"lease_owner": str(lease_owner), "reason": row["reason"]},
                event_id=f"conflict.rebuild_started:{conflict_id}:{processing_version}",
            )
            return {
                "conflict": conflict,
                "processing_version": processing_version,
                "lease_owner": str(lease_owner),
                "lease_until": lease_until,
                "reason": row["reason"],
            }

    def list_rebuild_candidates(self, limit=10, min_age_seconds=0):
        """Return settled pending or expired rebuilds without claiming them."""
        now = utc_now()
        ready_before = (
            datetime.utcnow() - timedelta(seconds=max(0, float(min_age_seconds or 0)))
        ).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT conflict_id, requested_version, status, reason, lease_until,
                       attempts, updated_at
                FROM territory_conflict_rebuilds
                WHERE requested_at <= ?
                  AND (status = 'pending'
                   OR (status = 'running' AND (lease_until IS NULL OR lease_until <= ?)))
                ORDER BY requested_at, updated_at, conflict_id
                LIMIT ?
                """,
                (ready_before, now, max(1, int(limit or 1))),
            ).fetchall()
            return [dict(row) for row in rows]

    @staticmethod
    def _front_row(row):
        return {
            "front_id": row["front_id"],
            "conflict_id": row["conflict_id"],
            "status": row["status"],
            "geometry_version": int(row["geometry_version"] or 0),
            "participant_key": row["participant_key"],
            "area_ids": loads_json(row["area_ids_json"], []),
            "pillar_ids": loads_json(row["pillar_ids_json"], []),
            "geometry": loads_json(row["geometry_json"], []),
            "parent_front_ids": loads_json(row["parent_front_ids_json"], []),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "closed_at": row["closed_at"],
        }

    @staticmethod
    def _front_signature(front):
        """Canonical shape used to detect a geometry publication no-op."""
        return (
            str(front.get("participant_key") or ""),
            tuple(sorted(str(item) for item in (front.get("area_ids") or []))),
            tuple(sorted(str(item) for item in (front.get("pillar_ids") or []))),
            json.dumps(front.get("geometry") or [], ensure_ascii=False,
                       sort_keys=True, separators=(",", ":")),
        )

    def list_fronts(self, conflict_reference, active_only=False):
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return []
            conflict_id = str(conflict_row["conflict_id"] or conflict_row["id"])
            sql = "SELECT * FROM territory_conflict_fronts WHERE conflict_id = ?"
            params = [conflict_id]
            if active_only:
                sql += " AND status = 'active'"
            sql += " ORDER BY created_at, front_id"
            return [self._front_row(row) for row in conn.execute(sql, tuple(params)).fetchall()]

    def latest_snapshot(self, conflict_reference):
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return None
            conflict_id = str(conflict_row["conflict_id"] or conflict_row["id"])
            row = conn.execute(
                """SELECT * FROM territory_conflict_snapshots
                   WHERE conflict_id = ? ORDER BY snapshot_version DESC LIMIT 1""",
                (conflict_id,),
            ).fetchone()
            return loads_json(row["payload_json"], {}) if row else None

    def snapshot_at_or_before(self, conflict_reference, snapshot_version):
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return None
            conflict_id = str(conflict_row["conflict_id"] or conflict_row["id"])
            row = conn.execute(
                """
                SELECT * FROM territory_conflict_snapshots
                WHERE conflict_id = ? AND snapshot_version <= ?
                ORDER BY snapshot_version DESC LIMIT 1
                """,
                (conflict_id, int(snapshot_version or 0)),
            ).fetchone()
            return loads_json(row["payload_json"], {}) if row else None

    def latest_snapshot_state(self, conflict_reference):
        """Overlay live domain freshness on the last immutable geometry snapshot."""
        snapshot = self.latest_snapshot(conflict_reference)
        conflict = self.get_by_key(conflict_reference)
        if not isinstance(conflict, dict):
            return snapshot

        published_snapshot = isinstance(snapshot, dict)
        fallback_fronts = self.list_fronts(conflict.get("conflict_id"), active_only=True)
        if not fallback_fronts:
            fallback_fronts = [
                {
                    "front_id": "front_legacy_" + hashlib.sha1(
                        f"{conflict.get('conflict_id')}:{index}".encode("utf-8")
                    ).hexdigest()[:16],
                    "conflict_id": conflict.get("conflict_id"),
                    "status": "active",
                    "geometry_version": int(conflict.get("geometry_version") or 0),
                    "participant_key": conflict.get("participant_key"),
                    "area_ids": conflict.get("area_ids") or [],
                    "pillar_ids": [],
                    "geometry": geometry,
                    "parent_front_ids": [],
                }
                for index, geometry in enumerate(conflict.get("intersections") or [])
                if isinstance(geometry, list) and len(geometry) >= 3
            ]
        state = dict(snapshot) if published_snapshot else {
            "fronts": fallback_fronts,
            "geometries": [],
            "snapshot_version": max(1, int(conflict.get("geometry_version") or 0)),
            "geometry_version": int(conflict.get("geometry_version") or 0),
            "generated_at": conflict.get("updated_at"),
        }
        geometry_status = str(conflict.get("geometry_status") or "").lower()
        snapshot_conflict_version = int(state.get("conflict_version") or 0)
        current_conflict_version = int(conflict.get("conflict_version") or 0)
        complete = published_snapshot and (
            geometry_status in {"clean", "published"}
            and snapshot_conflict_version >= current_conflict_version
        )
        pillars = self.list_pillars(conflict.get("conflict_id"))
        if not pillars:
            pillars = [dict(item) for item in (conflict.get("targets") or []) if isinstance(item, dict)]
        state.update({
            "conflict": conflict,
            "pillars": pillars,
            "conflict_version": current_conflict_version,
            "geometry_status": geometry_status or "unknown",
            "complete": complete,
            "recovery_required": geometry_status == "rebuild_failed",
        })
        return state

    def list_latest_snapshots_for_player(self, username):
        """Return one immutable, latest snapshot for each active player conflict."""
        snapshots = []
        for conflict in self.list_active_for_player(username):
            snapshot = self.latest_snapshot_state(
                conflict.get("conflict_id") or conflict.get("conflict_key")
            )
            if isinstance(snapshot, dict):
                snapshots.append(snapshot)
        return sorted(
            snapshots,
            key=lambda item: (
                str(item.get("generated_at") or ""),
                str((item.get("conflict") or {}).get("conflict_id") or ""),
            ),
            reverse=True,
        )

    def publish_rebuild(self, conflict_reference, lease_owner, processing_version, front_plans,
                        resolve=False, resolution_reason=""):
        """Atomically publish fronts, conflict geometry and one immutable snapshot."""
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return {"ok": False, "reason": "conflict_not_found"}
            conflict = self._conflict_from_row(conn, conflict_row)
            conflict_id = conflict["conflict_id"]
            request_row = conn.execute(
                "SELECT * FROM territory_conflict_rebuilds WHERE conflict_id = ?",
                (conflict_id,),
            ).fetchone()
            if (not request_row or request_row["status"] != "running" or
                    request_row["lease_owner"] != str(lease_owner) or
                    int(request_row["processing_version"] or 0) != int(processing_version)):
                return {"ok": False, "reason": "lease_lost"}

            old_rows = conn.execute(
                "SELECT * FROM territory_conflict_fronts WHERE conflict_id = ? AND status = 'active'",
                (conflict_id,),
            ).fetchall()
            old_fronts = [self._front_row(row) for row in old_rows]
            latest_snapshot_row = conn.execute(
                """SELECT payload_json FROM territory_conflict_snapshots
                   WHERE conflict_id = ? ORDER BY snapshot_version DESC LIMIT 1""",
                (conflict_id,),
            ).fetchone()
            latest_snapshot_payload = (
                loads_json(latest_snapshot_row["payload_json"], {})
                if latest_snapshot_row else {}
            )
            old_signatures = sorted(self._front_signature(front) for front in old_fronts)
            plan_signatures = sorted(self._front_signature({
                "participant_key": plan.get("participant_key") or conflict["participant_key"],
                "area_ids": plan.get("area_ids") or [],
                "pillar_ids": plan.get("pillar_ids") or [],
                "geometry": plan.get("geometry") or [],
            }) for plan in (front_plans or []))
            live_pillars = [self._row_to_pillar(row) for row in conn.execute(
                "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? ORDER BY id",
                (conflict_id,),
            ).fetchall()]

            def pillar_state_signature(pillar):
                return (
                    str((pillar or {}).get("target_id") or ""),
                    str((pillar or {}).get("status") or ""),
                    bool((pillar or {}).get("captured")),
                    str((pillar or {}).get("owner_username") or ""),
                    str((pillar or {}).get("captured_by") or ""),
                )

            live_pillar_signatures = sorted(pillar_state_signature(item) for item in live_pillars)
            snapshot_pillar_signatures = sorted(
                pillar_state_signature(item)
                for item in (latest_snapshot_payload.get("pillars") or [])
            )
            same_pillar_state = live_pillar_signatures == snapshot_pillar_signatures
            same_resolution = bool(resolve) == (conflict.get("status") == "resolved")
            snapshot_covers_processing_version = (
                int(latest_snapshot_payload.get("conflict_version") or 0)
                >= int(processing_version)
            )
            live_geometry_is_clean = str(
                conflict.get("geometry_status") or ""
            ).lower() in {"clean", "published"}
            if (latest_snapshot_row and same_resolution
                    and old_signatures == plan_signatures
                    and same_pillar_state
                    and snapshot_covers_processing_version
                    and live_geometry_is_clean):
                latest_request_row = conn.execute(
                    "SELECT requested_version FROM territory_conflict_rebuilds WHERE conflict_id = ?",
                    (conflict_id,),
                ).fetchone()
                pending_newer = int(latest_request_row["requested_version"] or 0) > int(processing_version)
                conn.execute(
                    """
                    UPDATE territory_conflict_rebuilds
                    SET status = ?, lease_owner = '', lease_until = NULL,
                        completed_at = ?, updated_at = ?
                    WHERE conflict_id = ?
                    """,
                    ("pending" if pending_newer else "complete", now, now, conflict_id),
                )
                return {
                    "ok": True,
                    "changed": False,
                    "snapshot": latest_snapshot_payload,
                    "pending_newer": pending_newer,
                }
            unmatched_old = {front["front_id"]: front for front in old_fronts}
            geometry_version = int(conflict["geometry_version"] or 0) + 1
            published_fronts = []

            planned_fronts = []
            parent_usage = {front["front_id"]: 0 for front in old_fronts}
            for plan in front_plans or []:
                plan_areas = {str(item) for item in (plan.get("area_ids") or [])}
                plan_pillars = {str(item) for item in (plan.get("pillar_ids") or [])}
                candidates = []
                for old in old_fronts:
                    area_overlap = len(plan_areas & {str(item) for item in old["area_ids"]})
                    pillar_overlap = len(plan_pillars & {str(item) for item in old["pillar_ids"]})
                    if old["participant_key"] == plan.get("participant_key") and (area_overlap or pillar_overlap):
                        candidates.append((area_overlap + pillar_overlap, old))
                candidates.sort(key=lambda item: (item[0], item[1]["front_id"]), reverse=True)
                parent_ids = [item[1]["front_id"] for item in candidates]
                for parent_id in parent_ids:
                    parent_usage[parent_id] += 1
                planned_fronts.append((plan, candidates, parent_ids))

            for plan, candidates, parent_ids in planned_fronts:
                matched = None
                if len(parent_ids) == 1 and parent_usage[parent_ids[0]] == 1:
                    matched = candidates[0][1]
                front_id = matched["front_id"] if matched else f"front_{secrets.token_hex(8)}"
                if matched:
                    unmatched_old.pop(front_id, None)
                created_at = matched["created_at"] if matched else now
                conn.execute(
                    """
                    INSERT OR REPLACE INTO territory_conflict_fronts
                        (front_id, conflict_id, status, geometry_version, participant_key,
                         area_ids_json, pillar_ids_json, geometry_json,
                         parent_front_ids_json, created_at, updated_at, closed_at)
                    VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    (front_id, conflict_id, geometry_version,
                     str(plan.get("participant_key") or conflict["participant_key"]),
                     dumps_json(plan.get("area_ids") or []), dumps_json(plan.get("pillar_ids") or []),
                     dumps_json(plan.get("geometry") or []), dumps_json(parent_ids),
                     created_at, now),
                )
                event_type = "conflict.front_updated" if matched else "conflict.front_created"
                if len(parent_ids) > 1:
                    event_type = "conflict.front_merged"
                elif len(parent_ids) == 1 and parent_usage[parent_ids[0]] > 1:
                    event_type = "conflict.front_split"
                self._record_event(
                    conn, event_type, conflict_id, front_id, processing_version, geometry_version,
                    payload={"parent_front_ids": parent_ids},
                    event_id=f"{event_type}:{conflict_id}:{front_id}:{geometry_version}",
                )
                published_fronts.append(self._front_row(conn.execute(
                    "SELECT * FROM territory_conflict_fronts WHERE front_id = ?", (front_id,)
                ).fetchone()))

            for old in unmatched_old.values():
                child_count = sum(
                    1 for front in published_fronts
                    if old["front_id"] in front["parent_front_ids"]
                )
                status = "split" if child_count > 1 else ("merged" if child_count == 1 else "closed")
                conn.execute(
                    "UPDATE territory_conflict_fronts SET status = ?, updated_at = ?, closed_at = ? WHERE front_id = ?",
                    (status, now, now, old["front_id"]),
                )
                event_type = {
                    "split": "conflict.front_split",
                    "merged": "conflict.front_merged",
                    "closed": "conflict.front_closed",
                }[status]
                self._record_event(
                    conn, event_type, conflict_id, old["front_id"], processing_version, geometry_version,
                    event_id=f"{event_type}:{conflict_id}:{old['front_id']}:{geometry_version}",
                )

            status = "resolved" if resolve else "active"
            geometry_status = "clean"
            resolved_at = now if resolve else conflict.get("resolved_at")
            conn.execute(
                """
                UPDATE territory_conflicts
                SET status = ?, geometry_version = ?, geometry_status = ?,
                    resolution_reason = ?, resolved_at = ?, updated_at = ?
                WHERE conflict_id = ?
                """,
                (status, geometry_version, geometry_status,
                 str(resolution_reason or ("geometry_disappeared" if resolve else "")),
                 resolved_at, now, conflict_id),
            )
            updated = self._conflict_from_row(conn, conn.execute(
                "SELECT * FROM territory_conflicts WHERE conflict_id = ?", (conflict_id,)
            ).fetchone())
            snapshot_version = geometry_version
            payload = {
                "conflict": updated,
                "fronts": published_fronts,
                "geometries": [front["geometry"] for front in published_fronts],
                "pillars": [self._row_to_pillar(row) for row in conn.execute(
                    "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? ORDER BY id", (conflict_id,)
                ).fetchall()],
                "conflict_version": int(processing_version),
                "geometry_version": geometry_version,
                "snapshot_version": snapshot_version,
                "generated_at": now,
            }
            conn.execute(
                """INSERT INTO territory_conflict_snapshots
                   (snapshot_id, conflict_id, snapshot_version, conflict_version,
                    geometry_version, payload_json, generated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (f"snapshot:{conflict_id}:{snapshot_version}", conflict_id, snapshot_version,
                 int(processing_version), geometry_version, dumps_json(payload), now),
            )
            event_type = "conflict.resolved" if resolve else "conflict.geometry_rebuilt"
            self._record_event(
                conn, event_type, conflict_id, "", processing_version, geometry_version,
                payload={"snapshot_version": snapshot_version},
                event_id=f"{event_type}:{conflict_id}:{geometry_version}",
            )
            latest_request_row = conn.execute(
                "SELECT requested_version FROM territory_conflict_rebuilds WHERE conflict_id = ?",
                (conflict_id,),
            ).fetchone()
            pending_newer = int(latest_request_row["requested_version"] or 0) > int(processing_version)
            conn.execute(
                """
                UPDATE territory_conflict_rebuilds
                SET status = ?, lease_owner = '', lease_until = NULL,
                    completed_at = ?, updated_at = ?
                WHERE conflict_id = ?
                """,
                ("pending" if pending_newer else "complete", now, now, conflict_id),
            )
            return {"ok": True, "changed": True, "snapshot": payload, "pending_newer": pending_newer}

    def fail_rebuild(self, conflict_reference, lease_owner, processing_version, error):
        """Release the lease without replacing the last valid geometry snapshot."""
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return False
            conflict = self._conflict_from_row(conn, conflict_row)
            request_row = conn.execute(
                "SELECT * FROM territory_conflict_rebuilds WHERE conflict_id = ?",
                (conflict["conflict_id"],),
            ).fetchone()
            if not request_row or request_row["lease_owner"] != str(lease_owner):
                return False
            conn.execute(
                """UPDATE territory_conflict_rebuilds
                   SET status = 'pending', lease_owner = '', lease_until = NULL,
                       last_error = ?, updated_at = ? WHERE conflict_id = ?""",
                (str(error)[:1000], now, conflict["conflict_id"]),
            )
            conn.execute(
                "UPDATE territory_conflicts SET status = 'changing', geometry_status = 'rebuild_failed', updated_at = ? WHERE conflict_id = ?",
                (now, conflict["conflict_id"]),
            )
            self._record_event(
                conn, "conflict.rebuild_failed", conflict["conflict_id"], "",
                processing_version, conflict["geometry_version"],
                payload={"error": str(error)[:1000]},
                event_id=f"conflict.rebuild_failed:{conflict['conflict_id']}:{processing_version}:{request_row['attempts']}",
            )
            return True

    def capture_pillar(self, conflict_reference, target_id, captured_target,
                       captured_by_username, previous_owner_username=None,
                       action_id=None):
        target_id = str(target_id or self.stable_target_id(captured_target))
        actor = str(captured_by_username or "")
        action_id = str(action_id or "").strip()
        receipt_id = f"conflict.pillar_capture.receipt:{action_id}" if action_id else None
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conflict_row = self._find_reference_row(conn, conflict_reference)
            if not conflict_row:
                return {"ok": False, "reason": "conflict_not_found", "target_id": target_id}
            conflict = self._conflict_from_row(conn, conflict_row)
            if conflict["status"] not in self.OPEN_STATUSES:
                return {"ok": False, "reason": "conflict_not_active", "target_id": target_id}

            duplicate = None
            if receipt_id:
                duplicate = conn.execute(
                    "SELECT 1 FROM territory_conflict_events WHERE event_id = ?",
                    (receipt_id,),
                ).fetchone()
            if duplicate:
                return {
                    "ok": True, "duplicate": True, "changed": False,
                    "conflict": conflict, "target_id": target_id,
                }

            pillar_row = conn.execute(
                "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? AND target_id = ?",
                (conflict["conflict_id"], target_id),
            ).fetchone()
            if not pillar_row:
                seed_item = copy.deepcopy(captured_target or {})
                if "target" not in seed_item:
                    seed_item = {
                        "owner": previous_owner_username or seed_item.get("owner_username") or "",
                        "owner_username": previous_owner_username or seed_item.get("owner_username") or "",
                        "status": "contested",
                        "captured": False,
                        "target": seed_item,
                    }
                self._sync_pillars(
                    conn, conflict["conflict_id"], [seed_item],
                    conflict["conflict_version"], conflict["geometry_version"], actor,
                )
                pillar_row = conn.execute(
                    "SELECT * FROM territory_conflict_pillars WHERE conflict_id = ? AND target_id = ?",
                    (conflict["conflict_id"], target_id),
                ).fetchone()
            if not pillar_row:
                return {"ok": False, "reason": "pillar_not_found", "target_id": target_id}

            pillar = self._row_to_pillar(pillar_row)
            if pillar["captured"] and pillar["captured_by"] == actor:
                if receipt_id:
                    self._record_event(
                        conn, "conflict.pillar_capture.receipt", conflict["conflict_id"],
                        target_id, conflict["conflict_version"], conflict["geometry_version"],
                        actor_username=actor, action_id=action_id, event_id=receipt_id,
                        payload={"changed": False, "reason": "already_captured"},
                    )
                return {
                    "ok": True, "duplicate": False, "changed": False,
                    "reason": "already_captured", "conflict": conflict,
                    "pillar": pillar, "target_id": target_id,
                }

            next_version = int(conflict["conflict_version"]) + 1
            previous_owner = str(
                previous_owner_username or pillar["owner_username"] or
                pillar["previous_owner_username"] or ""
            )
            recaptured = bool(pillar["captured"] and pillar["captured_by"] and pillar["captured_by"] != actor)
            public_target = copy.deepcopy(pillar["public_target"] or {})
            if "target" not in public_target:
                public_target = {"target": public_target}
            public_target.update({
                "target_id": target_id,
                "owner": actor,
                "owner_username": actor,
                "previous_owner": previous_owner,
                "status": "captured",
                "captured": True,
                "captured_by": actor,
                "hacked_by": actor,
            })
            public_target["target"] = {
                **(public_target.get("target") or {}),
                **((captured_target or {}).get("target") or captured_target or {}),
                "target_id": target_id,
                "owner_username": actor,
            }
            conn.execute(
                """
                UPDATE territory_conflict_pillars SET
                    owner_username = ?, previous_owner_username = ?,
                    attacker_username = ?, status = 'captured', captured = 1,
                    captured_by = ?, last_changed_version = ?,
                    public_target_json = ?, updated_at = ?, captured_at = ?
                WHERE id = ?
                """,
                (actor, previous_owner, actor, actor, next_version,
                 dumps_json(public_target), now, now, pillar["id"]),
            )
            projected = self._project_targets(conn, conflict["conflict_id"], [])
            conn.execute(
                """
                UPDATE territory_conflicts SET targets_json = ?, status = 'changing',
                    conflict_version = ?, geometry_status = 'dirty',
                    last_actor_username = ?, source_event = 'pillar_captured', updated_at = ?
                WHERE id = ?
                """,
                (dumps_json(projected), next_version, actor, now, conflict["id"]),
            )
            event_type = "conflict.pillar_recaptured" if recaptured else "conflict.pillar_captured"
            payload = {"previous_owner_username": previous_owner, "captured_by": actor}
            self._record_event(conn, event_type, conflict["conflict_id"], target_id,
                               next_version, conflict["geometry_version"], actor, action_id, payload)
            self._record_event(conn, "conflict.updated", conflict["conflict_id"], target_id,
                               next_version, conflict["geometry_version"], actor, action_id,
                               {"geometry_status": "dirty"})
            self._record_event(conn, "conflict.rebuild_requested", conflict["conflict_id"], target_id,
                               next_version, conflict["geometry_version"], actor, action_id,
                               {"reason": "pillar_captured"})
            self._request_rebuild_in_conn(
                conn,
                conflict["conflict_id"],
                reason="pillar_captured",
                requested_version=next_version,
                now=now,
            )
            if receipt_id:
                self._record_event(conn, "conflict.pillar_capture.receipt", conflict["conflict_id"],
                                   target_id, next_version, conflict["geometry_version"], actor,
                                   action_id, {"changed": True}, event_id=receipt_id)
            updated_row = conn.execute(
                "SELECT * FROM territory_conflicts WHERE id = ?", (conflict["id"],)
            ).fetchone()
            return {
                "ok": True, "duplicate": False, "changed": True,
                "conflict": self._conflict_from_row(conn, updated_row),
                "pillar": self._row_to_pillar(conn.execute(
                    "SELECT * FROM territory_conflict_pillars WHERE id = ?", (pillar["id"],)
                ).fetchone()),
                "target_id": target_id,
            }

    def list_active(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM territory_conflicts
                WHERE status IN ('detected', 'active', 'changing', 'resolving')
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
            return [self._conflict_from_row(conn, row) for row in rows]

    def deactivate_stale_for_participants(self, participants, active_keys, source_event="conflict_refresh"):
        participants = {str(participant) for participant in (participants or []) if participant}
        if not participants:
            return 0
        active_keys = {str(key) for key in (active_keys or []) if key}

        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM territory_conflicts
                WHERE status IN ('detected', 'active', 'changing', 'resolving')
                """
            ).fetchall()

            stale_ids = []
            for row in rows:
                conflict = self._conflict_from_row(conn, row)
                conflict_participants = set(conflict.get("participants") or [])
                if not participants & conflict_participants:
                    continue
                if ({str(conflict.get("conflict_id")), str(conflict.get("conflict_key")),
                     str(conflict.get("legacy_conflict_key"))} & active_keys):
                    continue
                stale_ids.append(conflict.get("id"))

            if not stale_ids:
                return []

            placeholders = ",".join("?" for _ in stale_ids)
            conn.execute(
                f"""
                UPDATE territory_conflicts
                SET status = 'resolved',
                    conflict_version = conflict_version + 1,
                    resolution_reason = CASE
                        WHEN resolution_reason IS NULL OR resolution_reason = ''
                        THEN 'geometry_disappeared'
                        ELSE resolution_reason
                    END,
                    resolved_at = COALESCE(resolved_at, ?),
                    source_event = ?,
                    updated_at = ?
                WHERE id IN ({placeholders})
                """,
                [utc_now(), source_event, utc_now(), *stale_ids],
            )
            resolved_rows = conn.execute(
                f"SELECT * FROM territory_conflicts WHERE id IN ({placeholders})",
                stale_ids,
            ).fetchall()
            return [self._conflict_from_row(conn, row) for row in resolved_rows]

    def delete_user_data(self, username):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM territory_conflicts
                WHERE player_a_username = ?
                    OR player_b_username = ?
                    OR participants_json LIKE ?
                """,
                (username, username, f'%"{username}"%'),
            )


class VulnerabilityStore:
    VALID_STATUSES = {"active", "withdrawn", "hacked"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _normalize_target(target):
        normalized = copy.deepcopy(target or {})
        lat = float(normalized.get("lat"))
        lng = float(normalized.get("lng", normalized.get("lon")))
        label = str(normalized.get("label") or normalized.get("name") or "Cel")
        normalized["lat"] = lat
        normalized["lng"] = lng
        normalized["label"] = label
        normalized["name"] = str(normalized.get("name") or label)
        normalized["icon"] = str(normalized.get("icon") or "📍")
        normalized["source_type"] = str(normalized.get("source_type") or "manual")
        normalized["generated"] = bool(normalized.get("generated", False))
        return normalized

    @staticmethod
    def _row_to_report(row):
        target = loads_json(row["target_json"], {})
        security = loads_json(row["security_json"], {})
        return {
            "id": row["id"],
            "target": target,
            "lat": row["target_lat"],
            "lng": row["target_lng"],
            "label": row["label"],
            "name": row["name"],
            "icon": row["icon"],
            "source_type": row["source_type"],
            "generated": bool(row["generated"]),
            "reported_by_username": row["reported_by_username"],
            "reported_by_clan": row["reported_by_clan"],
            "territory_owner_username": row["territory_owner_username"],
            "territory_owner_clan": row["territory_owner_clan"],
            "security": security,
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def report(self, target, reported_by_username, reported_by_clan, security,
               territory_owner_username="", territory_owner_clan=""):
        normalized = self._normalize_target(target)
        normalized["security"] = copy.deepcopy(security or {})
        now = utc_now()
        with db_connect(self.db_path) as conn:
            existing = conn.execute(
                """
                SELECT id, reported_by_username
                FROM reported_vulnerabilities
                WHERE ROUND(target_lat, 5) = ROUND(?, 5)
                    AND ROUND(target_lng, 5) = ROUND(?, 5)
                    AND label = ?
                    AND status = 'active'
                LIMIT 1
                """,
                (
                    normalized["lat"],
                    normalized["lng"],
                    normalized["label"],
                ),
            ).fetchone()

            if existing:
                if existing["reported_by_username"] != reported_by_username:
                    row = conn.execute(
                        "SELECT * FROM reported_vulnerabilities WHERE id = ?",
                        (existing["id"],),
                    ).fetchone()
                    return self._row_to_report(row)
                conn.execute(
                    """
                    UPDATE reported_vulnerabilities
                    SET name = ?, icon = ?, source_type = ?, generated = ?,
                        reported_by_username = ?, territory_owner_username = ?,
                        territory_owner_clan = ?, security_json = ?, target_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        normalized["name"],
                        normalized["icon"],
                        normalized["source_type"],
                        1 if normalized["generated"] else 0,
                        reported_by_username,
                        territory_owner_username or "",
                        territory_owner_clan or "",
                        dumps_json(security or {}),
                        dumps_json(normalized),
                        now,
                        existing["id"],
                    ),
                )
                report_id = existing["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO reported_vulnerabilities
                        (target_lat, target_lng, label, name, icon, source_type,
                         generated, reported_by_username, reported_by_clan,
                         territory_owner_username, territory_owner_clan,
                         security_json, target_json, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        normalized["lat"],
                        normalized["lng"],
                        normalized["label"],
                        normalized["name"],
                        normalized["icon"],
                        normalized["source_type"],
                        1 if normalized["generated"] else 0,
                        reported_by_username,
                        reported_by_clan or "",
                        territory_owner_username or "",
                        territory_owner_clan or "",
                        dumps_json(security or {}),
                        dumps_json(normalized),
                        now,
                        now,
                    ),
                )
                report_id = cursor.lastrowid

            row = conn.execute(
                "SELECT * FROM reported_vulnerabilities WHERE id = ?",
                (report_id,),
            ).fetchone()
            return self._row_to_report(row)

    def get(self, report_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM reported_vulnerabilities WHERE id = ?",
                (report_id,),
            ).fetchone()
            return self._row_to_report(row) if row else None

    def list_active_for_clan(self, clan):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM reported_vulnerabilities
                WHERE reported_by_clan = ?
                    AND status = 'active'
                ORDER BY updated_at DESC, id DESC
                """,
                (clan or "",),
            ).fetchall()
            return [self._row_to_report(row) for row in rows]

    def list_active(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM reported_vulnerabilities
                WHERE status = 'active'
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
            return [self._row_to_report(row) for row in rows]

    def set_status(self, report_id, status):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid vulnerability status: {status}")
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE reported_vulnerabilities
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, utc_now(), report_id),
            )
        return self.get(report_id)

    def withdraw(self, report_id, username):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id
                FROM reported_vulnerabilities
                WHERE id = ?
                    AND reported_by_username = ?
                    AND status = 'active'
                """,
                (report_id, username),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE reported_vulnerabilities
                SET status = 'withdrawn', updated_at = ?
                WHERE id = ?
                """,
                (utc_now(), report_id),
            )
        return self.get(report_id)

    def mark_hacked_by_target(self, lat, lng, label=None):
        params = [float(lat), float(lng)]
        query = """
            UPDATE reported_vulnerabilities
            SET status = 'hacked', updated_at = ?
            WHERE ROUND(target_lat, 5) = ROUND(?, 5)
                AND ROUND(target_lng, 5) = ROUND(?, 5)
                AND status = 'active'
        """
        params = [utc_now()] + params
        if label:
            query += " AND label = ?"
            params.append(label)
        with db_connect(self.db_path) as conn:
            conn.execute(query, params)


class WalletStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)
        self.balance_store = WalletBalanceStore(self.db_path)
        self.ledger_store = WalletLedgerStore(self.db_path)

    def get_wallet(self, username, limit=20):
        username = str(username or "").strip()
        with db_connect(self.db_path) as conn:
            user_row = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not user_row:
                raise ValueError("Nie ma takiego uzytkownika.")

            rows = conn.execute(
                """
                SELECT id, from_username, to_username, amount,
                       transaction_key, note, created_at
                FROM wallet_transactions
                WHERE from_username = ? OR to_username = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (username, username, int(limit)),
            ).fetchall()

        transactions = []
        for row in rows:
            outgoing = row["from_username"] == username
            transactions.append({
                "id": row["id"],
                "type": "outgoing" if outgoing else "incoming",
                "peer": row["to_username"] if outgoing else row["from_username"],
                "amount": int(row["amount"]),
                "created_at": row["created_at"],
                "note": row["note"] or "",
                "transaction_key": row["transaction_key"] or "",
            })

        balance = self.balance_store.get_balance(username)
        ledger = self.ledger_store.list_events(username, limit=limit)
        return {
            "balance": balance,
            "currency": "HC",
            "transactions": transactions,
            "ledger": ledger,
            "ledger_audit": self.ledger_store.audit_balance(username, balance),
        }

    def transfer(
        self,
        from_username,
        to_username,
        amount,
        note="",
        transaction_key="",
    ):
        result = self.balance_store.transfer(
            from_username,
            to_username,
            amount,
            transaction_key=transaction_key,
            note=note,
            debit_up_to=False,
            source="wallet.transfer",
        )
        transaction = result.get("transaction") or {}
        return {
            "balance": result["source_balance"],
            "recipient_balance": result["target_balance"],
            "currency": "HC",
            "duplicate": bool(result.get("duplicate")),
            "transaction": {
                "id": transaction.get("id"),
                "type": "outgoing",
                "peer": str(to_username or "").strip(),
                "amount": result["amount"],
                "created_at": transaction.get("created_at", ""),
                "note": transaction.get("note", ""),
                "transaction_key": transaction.get("transaction_key", ""),
            },
        }

    def technical_transfer(
        self,
        from_username,
        to_username,
        amount,
        note="",
        transaction_key="",
    ):
        result = self.balance_store.transfer(
            from_username,
            to_username,
            amount,
            transaction_key=transaction_key,
            note=note,
            debit_up_to=True,
            source="wallet.technical_transfer",
        )
        transaction = result.get("transaction") or {}
        return {
            "amount": result["amount"],
            "source_balance": result["source_balance"],
            "target_balance": result["target_balance"],
            "transaction_id": transaction.get("id"),
            "transaction_key": transaction.get("transaction_key", ""),
            "duplicate": bool(result.get("duplicate")),
            "created_at": transaction.get("created_at", ""),
        }


class PlayerHackAccessStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _parse_dt(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", ""))
        except ValueError:
            return None

    @classmethod
    def _seconds_until(cls, value):
        dt = cls._parse_dt(value)
        if not dt:
            return 0
        return max(0, int((dt - datetime.utcnow()).total_seconds()))

    @classmethod
    def _row_to_access(cls, row):
        if not row:
            return None
        return {
            "id": row["id"],
            "attacker_username": row["attacker_username"],
            "victim_username": row["victim_username"],
            "hacked_until": row["hacked_until"],
            "cooldown_until": row["cooldown_until"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "seconds_left": cls._seconds_until(row["hacked_until"]),
            "cooldown_seconds_left": cls._seconds_until(row["cooldown_until"]),
        }

    def grant_access(self, attacker_username, victim_username, access_minutes=5, cooldown_hours=3):
        attacker_username = str(attacker_username or "").strip()
        victim_username = str(victim_username or "").strip()
        if not attacker_username or not victim_username:
            raise ValueError("Brak gracza atakujacego albo celu.")
        if attacker_username == victim_username:
            raise ValueError("Nie mozna shackowac samego siebie.")

        now_dt = datetime.utcnow()
        now = now_dt.isoformat(timespec="seconds")
        hacked_until = (now_dt + timedelta(minutes=access_minutes)).isoformat(timespec="seconds")
        cooldown_until = (now_dt + timedelta(hours=cooldown_hours)).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO player_hack_access
                    (attacker_username, victim_username, hacked_until, cooldown_until, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(attacker_username, victim_username) DO UPDATE SET
                    hacked_until = excluded.hacked_until,
                    cooldown_until = excluded.cooldown_until,
                    updated_at = excluded.updated_at
                """,
                (attacker_username, victim_username, hacked_until, cooldown_until, now, now),
            )
            row = conn.execute(
                """
                SELECT * FROM player_hack_access
                WHERE attacker_username = ? AND victim_username = ?
                """,
                (attacker_username, victim_username),
            ).fetchone()
            access = self._row_to_access(row)
            if access and not access.get("id"):
                access["id"] = cursor.lastrowid
            return access

    def get_active_access(self, attacker_username, victim_username=None):
        now = utc_now()
        params = [attacker_username, now]
        where = "attacker_username = ? AND hacked_until > ?"
        if victim_username:
            where += " AND victim_username = ?"
            params.append(victim_username)
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                f"""
                SELECT * FROM player_hack_access
                WHERE {where}
                ORDER BY hacked_until DESC, id DESC
                LIMIT 1
                """,
                params,
            ).fetchone()
            return self._row_to_access(row)

    def get_cooldown(self, attacker_username, victim_username):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT * FROM player_hack_access
                WHERE attacker_username = ?
                  AND victim_username = ?
                  AND cooldown_until > ?
                LIMIT 1
                """,
                (attacker_username, victim_username, now),
            ).fetchone()
            return self._row_to_access(row)

    @staticmethod
    def access_key(access):
        if not access:
            return ""
        return f"{access.get('id') or ''}:{access.get('hacked_until') or ''}"

    def has_tool_usage(self, access, attacker_username, victim_username, tool_id):
        return self.get_tool_usage(access, attacker_username, victim_username, tool_id) is not None

    def get_tool_usage(self, access, attacker_username, victim_username, tool_id):
        key = self.access_key(access)
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id, access_id, attacker_username, victim_username,
                       tool_id, access_key, result, amount, created_at
                FROM player_hack_tool_usage
                WHERE attacker_username = ?
                  AND victim_username = ?
                  AND tool_id = ?
                  AND access_key = ?
                LIMIT 1
                """,
                (attacker_username, victim_username, tool_id, key),
            ).fetchone()
            return dict(row) if row else None

    def record_tool_usage(self, access, attacker_username, victim_username, tool_id, result="", amount=0):
        key = self.access_key(access)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """
                SELECT id, access_id, attacker_username, victim_username,
                       tool_id, access_key, result, amount, created_at
                FROM player_hack_tool_usage
                WHERE attacker_username = ?
                  AND victim_username = ?
                  AND tool_id = ?
                  AND access_key = ?
                LIMIT 1
                """,
                (attacker_username, victim_username, tool_id, key),
            ).fetchone()
            if existing:
                payload = dict(existing)
                payload["duplicate"] = True
                return payload
            cursor = conn.execute(
                """
                INSERT INTO player_hack_tool_usage
                    (access_id, attacker_username, victim_username, tool_id, access_key, result, amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    access.get("id") if access else None,
                    attacker_username,
                    victim_username,
                    tool_id,
                    key,
                    str(result or ""),
                    int(amount or 0),
                    now,
                ),
            )
            return {
                "id": cursor.lastrowid,
                "access_key": key,
                "created_at": now,
                "result": str(result or ""),
                "amount": int(amount or 0),
                "duplicate": False,
            }

    def complete_tool_usage(self, access, attacker_username, victim_username, tool_id, result="", amount=0):
        key = self.access_key(access)
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            updated = conn.execute(
                """
                UPDATE player_hack_tool_usage
                SET result = ?, amount = ?
                WHERE attacker_username = ?
                  AND victim_username = ?
                  AND tool_id = ?
                  AND access_key = ?
                  AND (result LIKE 'pending:%' OR (result = ? AND amount = ?))
                """,
                (
                    str(result or ""),
                    int(amount or 0),
                    attacker_username,
                    victim_username,
                    tool_id,
                    key,
                    str(result or ""),
                    int(amount or 0),
                ),
            )
            row = conn.execute(
                """
                SELECT id, access_id, attacker_username, victim_username,
                       tool_id, access_key, result, amount, created_at
                FROM player_hack_tool_usage
                WHERE attacker_username = ?
                  AND victim_username = ?
                  AND tool_id = ?
                  AND access_key = ?
                LIMIT 1
                """,
                (attacker_username, victim_username, tool_id, key),
            ).fetchone()
            if not row:
                raise ValueError("Brak rezerwacji uzycia narzedzia.")
            payload = dict(row)
            payload["updated"] = updated.rowcount == 1
            return payload


class AppActionReceiptStore:
    STATUS_RECEIVED = "received"
    STATUS_STARTED = "started"
    STATUS_EFFECT_APPLIED = "effect_applied"
    STATUS_FAILED = "failed"

    ACTIVE_STATUSES = {STATUS_RECEIVED, STATUS_STARTED}
    COMPLETED_STATUSES = {STATUS_EFFECT_APPLIED, STATUS_FAILED}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._last_prune_at = 0.0
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @classmethod
    def _state_for_status(cls, status):
        status = cls._clean_text(status, cls.STATUS_STARTED)
        if status in cls.COMPLETED_STATUSES:
            return "completed"
        return "in_flight"

    @classmethod
    def _receipt_from_row(cls, row):
        if not row:
            return None
        status = row["status"]
        return {
            "state": cls._state_for_status(status),
            "receipt_key": row["receipt_key"],
            "username": row["username"],
            "app_id": row["app_id"],
            "action": row["action"],
            "target_key": row["target_key"],
            "source": row["source"],
            "status": status,
            "payload": loads_json(row["response_json"], {}),
            "status_code": int(row["status_code"] or 202),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "expires_at": float(row["expires_at"] or 0),
            "store": "sqlite",
        }

    def prune_expired(self, conn=None, now_ts=None):
        now_ts = float(now_ts if now_ts is not None else time.time())
        if conn is not None:
            conn.execute(
                "DELETE FROM app_action_receipts WHERE expires_at > 0 AND expires_at <= ?",
                (now_ts,),
            )
            return
        with db_connect(self.db_path) as own_conn:
            self.prune_expired(own_conn, now_ts)

    def begin(
        self,
        receipt_key,
        username="",
        app_id="",
        action="",
        target_key="",
        source="",
        ttl_seconds=90,
    ):
        receipt_key = self._clean_text(receipt_key)
        if not receipt_key:
            return "new", None

        now_text = utc_now()
        now_ts = time.time()
        expires_at = now_ts + max(1, int(ttl_seconds or 90))
        username = self._clean_text(username)
        app_id = self._clean_text(app_id)
        action = self._clean_text(action)
        target_key = self._clean_text(target_key)
        source = self._clean_text(source)
        should_prune = now_ts - self._last_prune_at >= 60.0

        # Duplicate requests dominate retries. Resolve the common case without
        # joining the global writer queue; the transaction rechecks for races.
        with db_connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT * FROM app_action_receipts WHERE receipt_key = ?",
                (receipt_key,),
            ).fetchone()
        if existing:
            receipt = self._receipt_from_row(existing)
            return receipt["state"], receipt

        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if should_prune:
                self.prune_expired(conn, now_ts)
                self._last_prune_at = now_ts
            existing = conn.execute(
                "SELECT * FROM app_action_receipts WHERE receipt_key = ?",
                (receipt_key,),
            ).fetchone()
            if existing:
                receipt = self._receipt_from_row(existing)
                return receipt["state"], receipt

            conn.execute(
                """
                INSERT INTO app_action_receipts
                    (receipt_key, username, app_id, action, target_key, source,
                     status, response_json, status_code, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, '{}', 202, ?, ?, ?)
                """,
                (
                    receipt_key,
                    username,
                    app_id,
                    action,
                    target_key,
                    source,
                    self.STATUS_STARTED,
                    now_text,
                    now_text,
                    expires_at,
                ),
            )
        return "new", None

    def finish(self, receipt_key, payload=None, status_code=200, ttl_seconds=90, status=None):
        receipt_key = self._clean_text(receipt_key)
        if not receipt_key:
            return
        now_text = utc_now()
        expires_at = time.time() + max(1, int(ttl_seconds or 90))
        status = self._clean_text(status, self.STATUS_EFFECT_APPLIED)
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE app_action_receipts
                SET status = ?,
                    response_json = ?,
                    status_code = ?,
                    updated_at = ?,
                    expires_at = ?
                WHERE receipt_key = ?
                """,
                (
                    status,
                    dumps_json(payload or {}),
                    int(status_code or 200),
                    now_text,
                    expires_at,
                    receipt_key,
                ),
            )
            if cursor.rowcount == 0:
                conn.execute(
                    """
                    INSERT INTO app_action_receipts
                        (receipt_key, username, status, response_json, status_code, created_at, updated_at, expires_at)
                    VALUES (?, '', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt_key,
                        status,
                        dumps_json(payload or {}),
                        int(status_code or 200),
                        now_text,
                        now_text,
                        expires_at,
                    ),
                )

    def get(self, receipt_key):
        receipt_key = self._clean_text(receipt_key)
        if not receipt_key:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM app_action_receipts WHERE receipt_key = ?",
                (receipt_key,),
            ).fetchone()
            return self._receipt_from_row(row)

    def metrics(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM app_action_receipts
                GROUP BY status
                """
            ).fetchall()
            return {row["status"]: int(row["count"] or 0) for row in rows}

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM app_action_receipts")


class PlayerOperationStore:
    TERMINAL_STATUSES = {"cancelled", "canceled", "done", "completed", "failed", "expired", "timeout", "resolved", "detected"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @classmethod
    def _operation_id(cls, operation):
        operation = operation if isinstance(operation, dict) else {}
        value = cls._clean_text(operation.get("operation_id") or operation.get("id"))
        if value:
            return value
        raw = dumps_json(operation)
        return "op_" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

    @classmethod
    def _status(cls, operation):
        operation = operation if isinstance(operation, dict) else {}
        return cls._clean_text(operation.get("status"), "running").lower()

    @staticmethod
    def _is_expired(operation):
        operation = operation if isinstance(operation, dict) else {}
        value = operation.get("expires_at")
        if not value:
            return False
        try:
            raw = str(value)
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is not None:
                now = datetime.utcnow().replace(tzinfo=parsed.tzinfo)
            else:
                now = datetime.utcnow()
            return parsed <= now
        except (TypeError, ValueError):
            return False

    @classmethod
    def _target_key(cls, operation):
        operation = operation if isinstance(operation, dict) else {}
        target = operation.get("target") if isinstance(operation.get("target"), dict) else {}
        if operation.get("target_id"):
            return cls._clean_text(operation.get("target_id"))
        if target.get("target_id"):
            return cls._clean_text(target.get("target_id"))
        lat = target.get("lat", operation.get("lat"))
        lng = target.get("lng", target.get("lon", operation.get("lng", operation.get("lon"))))
        label = target.get("label") or target.get("name") or operation.get("target_label") or operation.get("target_id") or ""
        if lat is not None and lng is not None:
            return f"map:{lat}:{lng}:{label}"
        return cls._clean_text(label)

    @classmethod
    def _operation_type(cls, operation):
        operation = operation if isinstance(operation, dict) else {}
        return cls._clean_text(operation.get("operation_type") or operation.get("type"), "operation")

    @classmethod
    def _active_logical_key(cls, operation):
        status = cls._status(operation)
        if status in cls.TERMINAL_STATUSES or cls._is_expired(operation):
            return ""
        operation = operation if isinstance(operation, dict) else {}
        parts = (
            cls._target_key(operation),
            cls._clean_text(operation.get("map_action_id")),
            cls._operation_type(operation),
            cls._clean_text(operation.get("source_app_id") or operation.get("source_app_name")),
        )
        return "|".join(parts) if any(parts) else ""

    @staticmethod
    def _risk_json(operation):
        operation = operation if isinstance(operation, dict) else {}
        value = operation.get("operation_risk_meter") or operation.get("risk_state") or operation.get("risk") or {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _created_at(operation, now):
        operation = operation if isinstance(operation, dict) else {}
        return str(operation.get("created_at") or operation.get("started_at") or now)

    @classmethod
    def _row_to_operation(cls, row):
        if not row:
            return None
        operation = loads_json(row["operation_json"], {})
        if isinstance(operation, dict):
            operation.setdefault("operation_id", row["operation_id"])
            operation.setdefault("status", row["status"])
            operation.setdefault("operation_type", row["operation_type"])
            operation.setdefault("_runtime_version", int(row["version"] or 0))
            return operation
        return None

    def seed_from_profile(self, username, profile):
        profile = profile if isinstance(profile, dict) else {}
        operations = profile.get("operations", [])
        if not operations:
            return []
        return self.upsert_operations(username, operations, event_type="operation.seed", source="profile")

    def list_operations(self, username, include_terminal=True):
        username = self._clean_text(username)
        if not username:
            return []
        where = "username = ?"
        params = [username]
        if not include_terminal:
            placeholders = ",".join("?" for _ in self.TERMINAL_STATUSES)
            where += f" AND status NOT IN ({placeholders})"
            params.extend(sorted(self.TERMINAL_STATUSES))
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM player_operations
                WHERE {where}
                ORDER BY created_at, updated_at
                """,
                tuple(params),
            ).fetchall()
            return [
                operation for operation in (self._row_to_operation(row) for row in rows)
                if isinstance(operation, dict)
            ]

    def upsert_operations(self, username, operations, event_type="operation.upsert", source="", dedupe_key_prefix=""):
        username = self._clean_text(username)
        if not username:
            return []
        now = utc_now()
        accepted = []
        prepared = []
        for incoming in operations or []:
            if not isinstance(incoming, dict):
                continue
            operation = dict(incoming)
            operation_id = self._operation_id(operation)
            operation["operation_id"] = operation_id
            status = self._status(operation)
            prepared.append({
                "operation": operation,
                "operation_id": operation_id,
                "status": status,
                "logical_key": self._active_logical_key(operation),
                "target_key": self._target_key(operation),
                "operation_type": self._operation_type(operation),
                "operation_json": dumps_json(operation),
                "risk_json": dumps_json(self._risk_json(operation)),
            })
        with db_connect(self.db_path) as conn:
            active_rows = conn.execute(
                """
                SELECT operation_id, operation_json, version
                FROM player_operations
                WHERE username = ?
                """,
                (username,),
            ).fetchall()
        active_keys = {}
        for row in active_rows:
            existing_op = loads_json(row["operation_json"], {})
            key = self._active_logical_key(existing_op)
            if key:
                active_keys[key] = row["operation_id"]
        observed_versions = sorted(
            (row["operation_id"], int(row["version"] or 0)) for row in active_rows
        )

        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            latest_versions = sorted(
                (row["operation_id"], int(row["version"] or 0))
                for row in conn.execute(
                    "SELECT operation_id, version FROM player_operations WHERE username = ?",
                    (username,),
                ).fetchall()
            )
            if latest_versions != observed_versions:
                active_keys = {}
                for row in conn.execute(
                    "SELECT operation_id, operation_json FROM player_operations WHERE username = ?",
                    (username,),
                ).fetchall():
                    existing_op = loads_json(row["operation_json"], {})
                    key = self._active_logical_key(existing_op)
                    if key:
                        active_keys[key] = row["operation_id"]

            for item in prepared:
                operation = item["operation"]
                operation_id = item["operation_id"]
                status = item["status"]
                logical_key = item["logical_key"]
                if logical_key and active_keys.get(logical_key) not in {"", None, operation_id}:
                    continue

                dedupe_key = ""
                if dedupe_key_prefix:
                    dedupe_key = f"{dedupe_key_prefix}:{operation_id}:{status}"
                    if conn.execute(
                        "SELECT 1 FROM operation_events WHERE dedupe_key = ?",
                        (dedupe_key,),
                    ).fetchone():
                        continue

                existing = conn.execute(
                    "SELECT version, created_at FROM player_operations WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()
                version = int(existing["version"] or 0) + 1 if existing else 1
                created_at = existing["created_at"] if existing else self._created_at(operation, now)
                conn.execute(
                    """
                    INSERT INTO player_operations
                        (operation_id, username, target_key, operation_type, status,
                         operation_json, risk_json, version, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(operation_id) DO UPDATE SET
                        username = excluded.username,
                        target_key = excluded.target_key,
                        operation_type = excluded.operation_type,
                        status = excluded.status,
                        operation_json = excluded.operation_json,
                        risk_json = excluded.risk_json,
                        version = excluded.version,
                        updated_at = excluded.updated_at
                    """,
                    (
                        operation_id,
                        username,
                        item["target_key"],
                        item["operation_type"],
                        status,
                        item["operation_json"],
                        item["risk_json"],
                        version,
                        created_at,
                        now,
                    ),
                )
                event_id = f"opev_{hashlib.sha1(f'{operation_id}:{event_type}:{now}:{version}'.encode('utf-8')).hexdigest()[:18]}"
                conn.execute(
                    """
                    INSERT OR IGNORE INTO operation_events
                        (event_id, operation_id, event_type, dedupe_key, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        operation_id,
                        self._clean_text(event_type, "operation.upsert"),
                        dedupe_key,
                        dumps_json({"source": source, "status": status, "operation_id": operation_id}),
                        now,
                    ),
                )
                if logical_key:
                    active_keys[logical_key] = operation_id
                accepted.append(operation)
        return accepted

    def cancel_operation(self, username, operation_id, cancelled_by="player"):
        username = self._clean_text(username)
        operation_id = self._clean_text(operation_id)
        if not username or not operation_id:
            return None, "missing_operation_id"
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_operations WHERE username = ? AND operation_id = ?",
                (username, operation_id),
            ).fetchone()
            if not row:
                return None, "not_found"
            operation = self._row_to_operation(row) or {}
            if self._status(operation) in self.TERMINAL_STATUSES:
                return operation, "already_terminal"
            operation["status"] = "cancelled"
            operation["ended_at"] = now
            operation["cancelled_at"] = now
            operation["cancelled_by"] = cancelled_by
            operation["remaining_seconds"] = 0
            operation["expired"] = True
            resource_buffer = operation.setdefault("resource_buffer", {})
            if isinstance(resource_buffer, dict):
                resource_buffer["cancelled"] = True
                resource_buffer.setdefault("files", [])
            version = int(row["version"] or 0) + 1
            conn.execute(
                """
                UPDATE player_operations
                SET status = 'cancelled',
                    operation_json = ?,
                    risk_json = ?,
                    version = ?,
                    updated_at = ?
                WHERE operation_id = ?
                """,
                (
                    dumps_json(operation),
                    dumps_json(self._risk_json(operation)),
                    version,
                    now,
                    operation_id,
                ),
            )
            event_id = f"opev_{hashlib.sha1(f'{operation_id}:cancel:{now}:{version}'.encode('utf-8')).hexdigest()[:18]}"
            conn.execute(
                """
                INSERT OR IGNORE INTO operation_events
                    (event_id, operation_id, event_type, dedupe_key, payload_json, created_at)
                VALUES (?, ?, 'operation.cancelled', ?, ?, ?)
                """,
                (
                    event_id,
                    operation_id,
                    f"cancel:{operation_id}",
                    dumps_json({"cancelled_by": cancelled_by}),
                    now,
                ),
            )
            return operation, "cancelled"

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM operation_events")
            conn.execute("DELETE FROM player_operations")


class SystemMessageStore:
    ACTIVE_STATUSES = {"pending", "delivered"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @classmethod
    def _message_id(cls, username, message):
        message = message if isinstance(message, dict) else {}
        value = cls._clean_text(message.get("message_id") or message.get("id"))
        if value:
            return f"msg_{username}_{value}"
        raw = dumps_json({
            "username": username,
            "type": message.get("type"),
            "title": message.get("title"),
            "text": message.get("text") or message.get("body"),
            "created_at": message.get("created_at"),
        })
        return "msg_" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:18]

    @classmethod
    def _dedupe_key(cls, username, message):
        message = message if isinstance(message, dict) else {}
        key = cls._clean_text(message.get("dedupe_key"))
        if key:
            return key
        return cls._message_id(username, message)

    @staticmethod
    def _row_to_message(row):
        if not row:
            return None
        payload = loads_json(row["payload_json"], {})
        message = dict(payload) if isinstance(payload, dict) else {}
        message.setdefault("id", row["message_id"])
        message.setdefault("message_id", row["message_id"])
        message.setdefault("type", row["type"])
        message.setdefault("title", row["title"])
        message.setdefault("text", row["body"])
        message.setdefault("status", "new")
        message.setdefault("created_at", row["created_at"])
        return message

    def add_message(self, username, message, source="", ttl_seconds=None):
        username = self._clean_text(username)
        if not username or not isinstance(message, dict):
            return None, False
        now = utc_now()
        expires_at = 0
        if ttl_seconds:
            try:
                expires_at = time.time() + max(1, int(ttl_seconds))
            except (TypeError, ValueError):
                expires_at = 0
        payload = dict(message)
        message_id = self._message_id(username, payload)
        dedupe_key = self._dedupe_key(username, payload)
        title = self._clean_text(payload.get("title"))
        body = self._clean_text(payload.get("text") or payload.get("body"))
        msg_type = self._clean_text(payload.get("type"), "info")
        payload.setdefault("id", message_id)
        payload.setdefault("message_id", message_id)
        payload.setdefault("status", "new")
        payload.setdefault("created_at", now)
        source_text = self._clean_text(source or payload.get("source"), "system")
        payload_json = dumps_json(payload)
        duplicate = None
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """
                SELECT * FROM system_messages
                WHERE username = ? AND dedupe_key = ?
                """,
                (username, dedupe_key),
            ).fetchone()
            if existing and existing["status"] in {"pending", "delivered", "consumed"}:
                duplicate = dict(existing)
            else:
                conn.execute(
                """
                INSERT INTO system_messages
                    (message_id, username, dedupe_key, title, body, type, source,
                     status, payload_json, created_at, expires_at, consumed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, NULL)
                ON CONFLICT(message_id) DO UPDATE SET
                    dedupe_key = excluded.dedupe_key,
                    title = excluded.title,
                    body = excluded.body,
                    type = excluded.type,
                    source = excluded.source,
                    expires_at = excluded.expires_at,
                    status = CASE
                        WHEN system_messages.status = 'consumed' THEN system_messages.status
                        ELSE 'pending'
                    END,
                    payload_json = excluded.payload_json
                """,
                    (
                    message_id,
                    username,
                    dedupe_key,
                    title,
                    body,
                    msg_type,
                    source_text,
                    payload_json,
                    str(payload.get("created_at") or now),
                    expires_at,
                    ),
                )
        if duplicate is not None:
            return self._row_to_message(duplicate), False
        return payload, True

    def add_messages(self, username, messages, source=""):
        added = []
        for message in messages or []:
            payload, created = self.add_message(username, message, source=source)
            if created and payload:
                added.append(payload)
        return added

    def consume_pending(self, username, limit=50):
        username = self._clean_text(username)
        if not username:
            return []
        now = utc_now()
        now_ts = time.time()
        consumed_rows = []
        with db_connect(self.db_path) as conn:
            # Empty desktop polls are the common case. Check without taking a
            # global SQLite writer lock; claim under BEGIN IMMEDIATE only when
            # there is deliverable work.
            available = conn.execute(
                """
                SELECT 1 FROM system_messages
                WHERE username = ?
                  AND status IN ('pending', 'delivered')
                  AND (expires_at <= 0 OR expires_at > ?)
                LIMIT 1
                """,
                (username, now_ts),
            ).fetchone()
            if not available:
                return []
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                """
                SELECT * FROM system_messages
                WHERE username = ? AND status IN ('pending', 'delivered')
                  AND (expires_at <= 0 OR expires_at > ?)
                ORDER BY created_at, message_id
                LIMIT ?
                """,
                (username, now_ts, max(1, int(limit or 50))),
            ).fetchall()
            if not rows:
                return []
            ids = [row["message_id"] for row in rows]
            placeholders = ",".join("?" for _ in ids)
            conn.execute(
                f"""
                UPDATE system_messages
                SET status = 'consumed', consumed_at = ?
                WHERE message_id IN ({placeholders})
                """,
                (now, *ids),
            )
            consumed_rows = [dict(row) for row in rows]
        return [
            message for message in (self._row_to_message(row) for row in consumed_rows)
            if isinstance(message, dict)
        ]

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM system_messages")


class PlayerInventoryStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _app_id(app):
        app = app if isinstance(app, dict) else {}
        value = str(app.get("id") or app.get("app_id") or "").strip()
        if value:
            return value
        name = str(app.get("name") or app.get("label") or "app").strip().lower()
        raw = dumps_json({"name": name, "runtime": app.get("runtime_file") or app.get("file_name")})
        return "app_" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

    @staticmethod
    def _tool_id(tool, app=None):
        if isinstance(tool, dict):
            value = str(tool.get("id") or tool.get("tool_id") or tool.get("file") or tool.get("name") or "").strip()
        else:
            value = str(tool or "").strip()
        if value:
            return value
        app_id = PlayerInventoryStore._app_id(app or {})
        return f"{app_id}.sh"

    @staticmethod
    def _storage_from_profile(profile):
        profile = profile if isinstance(profile, dict) else {}
        try:
            capacity = int(profile.get("storage_capacity") or 0)
        except (TypeError, ValueError):
            capacity = 0
        try:
            used = int(profile.get("storage_used") or 0)
        except (TypeError, ValueError):
            used = 0
        return {
            "capacity": max(0, capacity),
            "used": max(0, used),
            "unit": str(profile.get("storage_unit") or "MB"),
            "modifiers": {
                "storage_upgrades": profile.get("storage_upgrades", []),
                "googleplex_products": profile.get("googleplex_products", []),
                "storage_soft_limit": profile.get("storage_soft_limit", True),
                "storage_over_limit": profile.get("storage_over_limit", False),
            },
        }

    @staticmethod
    def _row_to_app(row):
        if not row:
            return None
        app = loads_json(row["app_json"], {})
        if isinstance(app, dict):
            app.setdefault("id", row["app_id"])
            app.setdefault("status", row["status"])
            return app
        return None

    @staticmethod
    def _row_to_tool(row):
        if not row:
            return None
        tool = loads_json(row["tool_json"], {})
        if isinstance(tool, dict):
            tool.setdefault("id", row["tool_id"])
            tool.setdefault("tool_id", row["tool_id"])
            tool.setdefault("app_id", row["app_id"])
            return tool
        return {"id": row["tool_id"], "tool_id": row["tool_id"], "app_id": row["app_id"], "name": row["tool_id"]}

    def seed_from_profile(self, username, profile):
        username = self._clean_text(username)
        if not username or not isinstance(profile, dict):
            return self.snapshot(username)
        apps = profile.get("apps", [])
        files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
        tools = files.get("tools", []) if isinstance(files, dict) else []
        storage = self._storage_from_profile(profile)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for app in apps or []:
                if not isinstance(app, dict):
                    continue
                app_id = self._app_id(app)
                existing = conn.execute(
                    "SELECT version FROM player_apps WHERE username = ? AND app_id = ?",
                    (username, app_id),
                ).fetchone()
                version = int(existing["version"] or 0) + 1 if existing else 1
                conn.execute(
                    """
                    INSERT INTO player_apps
                        (username, app_id, app_json, status, version, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(username, app_id) DO UPDATE SET
                        app_json = excluded.app_json,
                        status = excluded.status,
                        version = excluded.version,
                        updated_at = excluded.updated_at
                    """,
                    (
                        username,
                        app_id,
                        dumps_json(dict(app)),
                        self._clean_text(app.get("status"), "installed"),
                        version,
                        now,
                    ),
                )
            for tool in tools or []:
                tool_id = self._tool_id(tool)
                payload = dict(tool) if isinstance(tool, dict) else {"name": tool_id, "file": tool_id}
                app_id = self._clean_text(payload.get("app_id") or payload.get("source_app_id"))
                existing = conn.execute(
                    "SELECT version FROM player_tool_files WHERE username = ? AND tool_id = ?",
                    (username, tool_id),
                ).fetchone()
                version = int(existing["version"] or 0) + 1 if existing else 1
                conn.execute(
                    """
                    INSERT INTO player_tool_files
                        (username, tool_id, app_id, tool_json, version, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(username, tool_id) DO UPDATE SET
                        app_id = excluded.app_id,
                        tool_json = excluded.tool_json,
                        version = excluded.version,
                        updated_at = excluded.updated_at
                    """,
                    (username, tool_id, app_id, dumps_json(payload), version, now),
                )
            row = conn.execute(
                "SELECT version FROM player_storage WHERE username = ?",
                (username,),
            ).fetchone()
            version = int(row["version"] or 0) + 1 if row else 1
            conn.execute(
                """
                INSERT INTO player_storage
                    (username, capacity, used, unit, modifiers_json, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    capacity = excluded.capacity,
                    used = excluded.used,
                    unit = excluded.unit,
                    modifiers_json = excluded.modifiers_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    storage["capacity"],
                    storage["used"],
                    storage["unit"],
                    dumps_json(storage["modifiers"]),
                    version,
                    now,
                ),
            )
        return self.snapshot(username)

    def snapshot(self, username):
        username = self._clean_text(username)
        if not username:
            return {
                "initialized": False,
                "apps": [],
                "files": {"tools": []},
                "storage": None,
            }
        with db_connect(self.db_path) as conn:
            app_rows = conn.execute(
                """
                SELECT * FROM player_apps
                WHERE username = ? AND status != 'uninstalled'
                ORDER BY updated_at, app_id
                """,
                (username,),
            ).fetchall()
            tool_rows = conn.execute(
                """
                SELECT * FROM player_tool_files
                WHERE username = ?
                ORDER BY updated_at, tool_id
                """,
                (username,),
            ).fetchall()
            storage_row = conn.execute(
                "SELECT * FROM player_storage WHERE username = ?",
                (username,),
            ).fetchone()
            initialized = storage_row is not None
            if not initialized:
                initialized = bool(conn.execute(
                    """
                    SELECT 1 FROM player_apps WHERE username = ?
                    UNION ALL
                    SELECT 1 FROM player_tool_files WHERE username = ?
                    LIMIT 1
                    """,
                    (username, username),
                ).fetchone())
        storage = None
        if storage_row:
            storage = {
                "capacity": int(storage_row["capacity"] or 0),
                "used": int(storage_row["used"] or 0),
                "unit": storage_row["unit"] or "MB",
                "modifiers": loads_json(storage_row["modifiers_json"], {}),
                "version": int(storage_row["version"] or 0),
            }
        return {
            "initialized": initialized,
            "apps": [app for app in (self._row_to_app(row) for row in app_rows) if isinstance(app, dict)],
            "files": {"tools": [tool for tool in (self._row_to_tool(row) for row in tool_rows) if tool is not None]},
            "storage": storage,
        }

    def mirror_profile(self, username, profile):
        snapshot = self.snapshot(username)
        if not isinstance(profile, dict):
            return profile
        if snapshot.get("initialized"):
            # Once the canonical inventory exists, an empty list is a real
            # authoritative state (for example after the final uninstall), not
            # a signal to resurrect stale profile_json mirrors.
            profile["apps"] = copy.deepcopy(snapshot.get("apps") or [])
            files = (
                copy.deepcopy(profile.get("files"))
                if isinstance(profile.get("files"), dict)
                else {}
            )
            tools = (snapshot.get("files") or {}).get("tools")
            files["tools"] = copy.deepcopy(tools or [])
            profile["files"] = files
        storage = snapshot.get("storage")
        if storage:
            profile["storage_capacity"] = storage.get("capacity", profile.get("storage_capacity"))
            profile["storage_used"] = storage.get("used", profile.get("storage_used"))
            profile["storage_unit"] = storage.get("unit", profile.get("storage_unit", "MB"))
            modifiers = storage.get("modifiers") if isinstance(storage.get("modifiers"), dict) else {}
            for key in ("storage_upgrades", "googleplex_products", "storage_soft_limit", "storage_over_limit"):
                if key in modifiers:
                    profile[key] = modifiers[key]
        return profile

    def write_from_profile(self, username, profile):
        return self.seed_from_profile(username, profile)

    def uninstall_app(self, username, app_id="", tool_id=""):
        username = self._clean_text(username)
        app_id = self._clean_text(app_id)
        tool_id = self._clean_text(tool_id)
        if not username:
            return False
        now = utc_now()
        changed = False
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if app_id:
                row = conn.execute(
                    "SELECT version FROM player_apps WHERE username = ? AND app_id = ?",
                    (username, app_id),
                ).fetchone()
                if row:
                    conn.execute(
                        """
                        UPDATE player_apps
                        SET status = 'uninstalled', version = ?, updated_at = ?
                        WHERE username = ? AND app_id = ?
                        """,
                        (int(row["version"] or 0) + 1, now, username, app_id),
                    )
                    changed = True
                conn.execute(
                    "DELETE FROM player_tool_files WHERE username = ? AND app_id = ?",
                    (username, app_id),
                )
            if tool_id:
                cursor = conn.execute(
                    "DELETE FROM player_tool_files WHERE username = ? AND tool_id = ?",
                    (username, tool_id),
                )
                changed = changed or cursor.rowcount > 0
        return changed

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM player_tool_files")
            conn.execute("DELETE FROM player_apps")
            conn.execute("DELETE FROM player_storage")


class WalletLedgerStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return default

    def _row_to_event(self, row):
        if not row:
            return None
        payload = loads_json(row["payload_json"], {}) or {}
        return {
            "ledger_id": row["ledger_id"],
            "username": row["username"],
            "event_type": row["event_type"],
            "amount_delta": int(row["amount_delta"] or 0),
            "balance_after": int(row["balance_after"] or 0),
            "source": row["source"] or "",
            "source_id": row["source_id"] or "",
            "peer_username": row["peer_username"] or "",
            "note": row["note"] or "",
            "dedupe_key": row["dedupe_key"] or "",
            "payload": payload,
            "created_at": row["created_at"],
        }

    def has_events(self, username):
        username = self._clean_text(username)
        if not username:
            return False
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM wallet_ledger WHERE username = ? LIMIT 1",
                (username,),
            ).fetchone()
        return bool(row)

    def record_event(
        self,
        username,
        event_type,
        amount_delta,
        balance_after,
        source="",
        source_id="",
        peer_username="",
        note="",
        dedupe_key="",
        payload=None,
        created_at=None,
    ):
        username = self._clean_text(username)
        if not username:
            return None
        event_type = self._clean_text(event_type, "wallet.balance_changed")
        amount_delta = self._safe_int(amount_delta)
        balance_after = max(0, self._safe_int(balance_after))
        source = self._clean_text(source)
        source_id = self._clean_text(source_id)
        peer_username = self._clean_text(peer_username)
        note = self._clean_text(note)[:240]
        dedupe_key = self._clean_text(
            dedupe_key,
            f"wallet_ledger:{username}:{event_type}:{source}:{source_id}:{balance_after}",
        )
        created_at = self._clean_text(created_at, utc_now())
        payload_json = dumps_json(payload if isinstance(payload, dict) else {})
        ledger_id = f"wl_{hashlib.sha1(f'{username}:{dedupe_key}'.encode('utf-8')).hexdigest()[:18]}"

        with db_connect(self.db_path) as conn:
            row = self.record_event_with_conn(
                conn,
                username=username,
                event_type=event_type,
                amount_delta=amount_delta,
                balance_after=balance_after,
                source=source,
                source_id=source_id,
                peer_username=peer_username,
                note=note,
                dedupe_key=dedupe_key,
                payload_json=payload_json,
                created_at=created_at,
                ledger_id=ledger_id,
            )
        return self._row_to_event(row)

    def record_event_with_conn(
        self,
        conn,
        username,
        event_type,
        amount_delta,
        balance_after,
        source="",
        source_id="",
        peer_username="",
        note="",
        dedupe_key="",
        payload_json="{}",
        created_at=None,
        ledger_id=None,
    ):
        dedupe_key = self._clean_text(
            dedupe_key,
            f"wallet_ledger:{username}:{event_type}:{source}:{source_id}:{balance_after}",
        )
        return _wallet_record_ledger_with_conn(
            conn,
            username=username,
            event_type=event_type,
            amount_delta=amount_delta,
            balance_after=balance_after,
            source=source,
            source_id=source_id,
            peer_username=peer_username,
            note=note,
            dedupe_key=dedupe_key,
            payload_json=payload_json,
            created_at=created_at,
            ledger_id=ledger_id,
        )

    def list_events(self, username, limit=50):
        username = self._clean_text(username)
        try:
            limit = max(1, min(200, int(limit or 50)))
        except (TypeError, ValueError):
            limit = 50
        if not username:
            return []
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT ledger_id, username, event_type, amount_delta, balance_after,
                       source, source_id, peer_username, note, dedupe_key, payload_json, created_at
                FROM wallet_ledger
                WHERE username = ?
                ORDER BY created_at DESC, ledger_id DESC
                LIMIT ?
                """,
                (username, limit),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def ledger_balance(self, username):
        username = self._clean_text(username)
        if not username:
            return 0
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount_delta), 0) AS balance FROM wallet_ledger WHERE username = ?",
                (username,),
            ).fetchone()
        return int((row or {})["balance"] or 0)

    def audit_balance(self, username, current_balance):
        current_balance = max(0, self._safe_int(current_balance))
        ledger_balance = self.ledger_balance(username)
        return {
            "ledger_balance": ledger_balance,
            "current_balance": current_balance,
            "difference": current_balance - ledger_balance,
            "ok": ledger_balance == current_balance,
        }


class WalletBalanceStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _profile_balance(profile):
        return max(0, _wallet_int((profile or {}).get("hackcoins", 0)))

    @staticmethod
    def _assert_migration_not_blocked_with_conn(conn, username):
        migration = conn.execute(
            """
            SELECT status
            FROM profile_store_migrations
            WHERE migration_id = ? AND username = ?
            """,
            (WALLET_CANONICAL_MIGRATION_ID, username),
        ).fetchone()
        if migration and migration["status"] == "blocked":
            raise WalletNotInitialized(
                "Canonical wallet migration is blocked.",
                reason="migration_blocked",
            )
        return migration

    def seed_from_profile(self, username, profile):
        """Explicit migration only; the supplied profile must match durable metadata."""
        username = self._clean_text(username)
        if not username:
            raise WalletWriteError("Wallet username is required.")
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT username, profile_json, profile_revision, profile_checksum,
                       profile_integrity_status
                FROM users WHERE username = ?
                """,
                (username,),
            ).fetchone()
            durable_profile, errors = _validate_persisted_profile_row(row, username)
            if errors or durable_profile is None:
                raise ProfileRecoveryRequired(
                    "Profile cannot seed canonical wallet: " + ",".join(errors)
                )
            if (
                isinstance(profile, dict)
                and profile_payload_checksum(profile)
                != str(row["profile_checksum"] or "")
            ):
                raise WalletMutationRejected(
                    "Stale profile cannot seed canonical wallet."
                )
            result = _wallet_bootstrap_user_with_conn(conn, row)
            if result.get("status") == "blocked":
                raise WalletMutationRejected(
                    "Canonical wallet migration is blocked by conflicting evidence."
                )
            if result.get("status") != "applied":
                raise WalletMutationRejected(
                    "Canonical wallet migration could not be applied."
                )
            return int(result["balance"])

    def get_balance(self, username, fallback_profile=None):
        """Pure canonical read. fallback_profile is ignored for compatibility."""
        del fallback_profile
        username = self._clean_text(username)
        if not username:
            return 0
        with db_connect(self.db_path) as conn:
            migration = self._assert_migration_not_blocked_with_conn(
                conn, username
            )
            row = conn.execute(
                """
                SELECT balances.balance
                FROM wallet_balances AS balances
                JOIN users ON users.username = balances.username
                WHERE balances.username = ?
                """,
                (username,),
            ).fetchone()
            if row:
                return max(0, int(row["balance"] or 0))
            user_exists = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not user_exists:
                return 0
        if migration and migration["status"] == "blocked":
            # Kept as a defensive assertion if the helper contract changes.
            raise WalletNotInitialized(
                "Canonical wallet migration is blocked.",
                reason="migration_blocked",
            )
        raise WalletNotInitialized()

    def get_state(self, username):
        username = self._clean_text(username)
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            self._assert_migration_not_blocked_with_conn(conn, username)
            row = conn.execute(
                """
                SELECT balances.balance, balances.version, balances.updated_at
                FROM wallet_balances AS balances
                JOIN users ON users.username = balances.username
                WHERE balances.username = ?
                """,
                (username,),
            ).fetchone()
        if not row:
            return None
        return {
            "username": username,
            "balance": max(0, int(row["balance"] or 0)),
            "version": max(0, int(row["version"] or 0)),
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _canonical_row_with_conn(conn, username):
        WalletBalanceStore._assert_migration_not_blocked_with_conn(
            conn, username
        )
        row = conn.execute(
            """
            SELECT balances.balance, balances.version, balances.updated_at
            FROM users
            JOIN wallet_balances AS balances
              ON balances.username = users.username
            WHERE users.username = ?
            """,
            (username,),
        ).fetchone()
        if row:
            return row
        user_exists = conn.execute(
            "SELECT 1 FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if not user_exists:
            raise WalletNotInitialized("Wallet owner does not exist.")
        raise WalletNotInitialized("Canonical wallet is not initialized.")

    @staticmethod
    def _event_result(row, username, transaction_key):
        return {
            "applied": False,
            "duplicate": True,
            "username": username,
            "transaction_key": transaction_key,
            "amount_delta": int(row["amount_delta"] or 0),
            "balance": max(0, int(row["balance"] or 0)),
            "version": max(0, int(row["version"] or 0)),
        }

    def _apply_delta(
        self,
        username,
        delta,
        *,
        transaction_key,
        reason,
        source,
        peer_username="",
        expected_version=None,
        debit_up_to=False,
    ):
        username = self._clean_text(username)
        transaction_key = self._clean_text(transaction_key)
        reason = self._clean_text(reason, "wallet.balance_changed")
        source = self._clean_text(source, "wallet_balance_store")
        peer_username = self._clean_text(peer_username)
        if not username:
            raise WalletWriteError("Wallet username is required.")
        try:
            requested_delta = int(delta)
        except (TypeError, ValueError) as exc:
            raise WalletWriteError("Wallet delta must be an integer.") from exc

        if requested_delta == 0 and not debit_up_to and not transaction_key:
            state = self.get_state(username)
            if state is None:
                raise WalletNotInitialized("Canonical wallet is not initialized.")
            return {
                "applied": False,
                "duplicate": False,
                "username": username,
                "transaction_key": transaction_key,
                "amount_delta": 0,
                "balance": state["balance"],
                "version": state["version"],
                "reason": "zero_delta",
            }
        if not transaction_key:
            raise WalletWriteError("Wallet transaction_key is required.")
        if expected_version is not None:
            try:
                expected_version = int(expected_version)
            except (TypeError, ValueError) as exc:
                raise WalletWriteError("expected_version must be an integer.") from exc

        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            replay = conn.execute(
                """
                SELECT amount_delta, balance, version
                FROM wallet_balance_events
                WHERE username = ? AND transaction_key = ?
                """,
                (username, transaction_key),
            ).fetchone()
            if replay:
                replay_delta = int(replay["amount_delta"] or 0)
                if not debit_up_to and replay_delta != requested_delta:
                    raise WalletIdempotencyConflict(
                        "Wallet transaction key was reused with another delta."
                    )
                return self._event_result(replay, username, transaction_key)

            current = self._canonical_row_with_conn(conn, username)
            balance_before = max(0, int(current["balance"] or 0))
            version_before = max(0, int(current["version"] or 0))
            if expected_version is not None and expected_version != version_before:
                raise WalletIdempotencyConflict(
                    f"Expected wallet version {expected_version}, current is {version_before}."
                )
            applied_delta = requested_delta
            if requested_delta < 0 and balance_before + requested_delta < 0:
                if not debit_up_to:
                    raise WalletInsufficientFunds("Brak srodkow.")
                applied_delta = -balance_before
            if applied_delta == 0:
                _wallet_record_balance_event_with_conn(
                    conn,
                    username=username,
                    transaction_key=transaction_key,
                    amount_delta=0,
                    balance=balance_before,
                    version=version_before,
                    reason=reason + ".zero",
                    created_at=now,
                )
                _wallet_record_ledger_with_conn(
                    conn,
                    username=username,
                    event_type=reason + ".zero",
                    amount_delta=0,
                    balance_after=balance_before,
                    source=source,
                    source_id=transaction_key,
                    peer_username=peer_username,
                    note=reason,
                    dedupe_key=f"wallet:ledger:{username}:{transaction_key}",
                    payload_json=dumps_json({
                        "transaction_key": transaction_key,
                        "zero_value_receipt": True,
                        "version": version_before,
                    }),
                    created_at=now,
                )
                return {
                    "applied": False,
                    "duplicate": False,
                    "username": username,
                    "transaction_key": transaction_key,
                    "amount_delta": 0,
                    "balance": balance_before,
                    "version": version_before,
                    "reason": "zero_available",
                }

            balance_after = balance_before + applied_delta
            version_after = version_before + 1
            updated = conn.execute(
                """
                UPDATE wallet_balances
                SET balance = ?, version = ?, updated_at = ?
                WHERE username = ? AND version = ?
                """,
                (
                    balance_after,
                    version_after,
                    now,
                    username,
                    version_before,
                ),
            )
            if updated.rowcount != 1:
                raise WalletIdempotencyConflict(
                    "Canonical wallet version changed before commit."
                )
            _wallet_record_balance_event_with_conn(
                conn,
                username=username,
                transaction_key=transaction_key,
                amount_delta=applied_delta,
                balance=balance_after,
                version=version_after,
                reason=reason,
                created_at=now,
            )
            _wallet_record_ledger_with_conn(
                conn,
                username=username,
                event_type=reason,
                amount_delta=applied_delta,
                balance_after=balance_after,
                source=source,
                source_id=transaction_key,
                peer_username=peer_username,
                note=reason,
                dedupe_key=f"wallet:ledger:{username}:{transaction_key}",
                payload_json=dumps_json({
                    "transaction_key": transaction_key,
                    "previous_balance": balance_before,
                    "version": version_after,
                }),
                created_at=now,
            )
            return {
                "applied": True,
                "duplicate": False,
                "username": username,
                "transaction_key": transaction_key,
                "amount_delta": applied_delta,
                "balance": balance_after,
                "version": version_after,
            }

    def apply_delta(
        self,
        username,
        delta,
        transaction_key,
        reason="wallet.balance_changed",
        *,
        source="wallet_balance_store",
        peer_username="",
        expected_version=None,
    ):
        return self._apply_delta(
            username,
            delta,
            transaction_key=transaction_key,
            reason=reason,
            source=source,
            peer_username=peer_username,
            expected_version=expected_version,
            debit_up_to=False,
        )

    def credit(
        self,
        username,
        amount,
        transaction_key,
        reason="wallet.credit",
        **kwargs,
    ):
        amount = _wallet_int(amount)
        if amount < 0:
            raise WalletWriteError("Credit amount cannot be negative.")
        return self._apply_delta(
            username,
            amount,
            transaction_key=transaction_key,
            reason=reason,
            source=kwargs.pop("source", "wallet.credit"),
            **kwargs,
        )

    def debit(
        self,
        username,
        amount,
        transaction_key,
        reason="wallet.debit",
        **kwargs,
    ):
        amount = _wallet_int(amount)
        if amount < 0:
            raise WalletWriteError("Debit amount cannot be negative.")
        return self._apply_delta(
            username,
            -amount,
            transaction_key=transaction_key,
            reason=reason,
            source=kwargs.pop("source", "wallet.debit"),
            **kwargs,
        )

    def debit_up_to(
        self,
        username,
        amount,
        transaction_key,
        reason="wallet.debit_up_to",
        **kwargs,
    ):
        amount = _wallet_int(amount)
        if amount < 0:
            raise WalletWriteError("Debit amount cannot be negative.")
        return self._apply_delta(
            username,
            -amount,
            transaction_key=transaction_key,
            reason=reason,
            source=kwargs.pop("source", "wallet.debit_up_to"),
            debit_up_to=True,
            **kwargs,
        )

    def transfer(
        self,
        from_username,
        to_username,
        amount,
        *,
        transaction_key,
        note="",
        debit_up_to=False,
        source="wallet.transfer",
    ):
        from_username = self._clean_text(from_username)
        to_username = self._clean_text(to_username)
        transaction_key = self._clean_text(transaction_key)
        note = self._clean_text(note)[:240]
        source = self._clean_text(source, "wallet.transfer")
        try:
            requested_amount = int(amount)
        except (TypeError, ValueError) as exc:
            raise WalletWriteError("Kwota musi byc liczba calkowita HC.") from exc
        if requested_amount < 0 or (requested_amount == 0 and not debit_up_to):
            raise WalletWriteError("Kwota musi byc dodatnia.")
        if not from_username or not to_username:
            raise WalletWriteError("Brak stron transferu.")
        if from_username == to_username:
            raise WalletWriteError("Nie mozna przelac HC samemu sobie.")

        if not transaction_key:
            raise WalletWriteError("Wallet transfer transaction_key is required.")

        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            replay = conn.execute(
                """
                SELECT id, from_username, to_username, amount,
                       transaction_key, note, created_at
                FROM wallet_transactions WHERE transaction_key = ?
                """,
                (transaction_key,),
            ).fetchone()
            if replay:
                same_amount = (
                    int(replay["amount"] or 0) == requested_amount
                    if not debit_up_to
                    else int(replay["amount"] or 0) <= requested_amount
                )
                if (
                    replay["from_username"] != from_username
                    or replay["to_username"] != to_username
                    or not same_amount
                    or str(replay["note"] or "") != note
                ):
                    raise WalletIdempotencyConflict(
                        "Wallet transfer key was reused with different semantics."
                    )
                outgoing = conn.execute(
                    """
                    SELECT balance, version FROM wallet_balance_events
                    WHERE username = ? AND transaction_key = ?
                    """,
                    (from_username, transaction_key + ":out"),
                ).fetchone()
                incoming = conn.execute(
                    """
                    SELECT balance, version FROM wallet_balance_events
                    WHERE username = ? AND transaction_key = ?
                    """,
                    (to_username, transaction_key + ":in"),
                ).fetchone()
                if not outgoing or not incoming:
                    raise WalletWriteError(
                        "Canonical transfer exists without complete balance events."
                    )
                return {
                    "applied": False,
                    "duplicate": True,
                    "amount": int(replay["amount"] or 0),
                    "source_balance": int(outgoing["balance"] or 0),
                    "target_balance": int(incoming["balance"] or 0),
                    "source_version": int(outgoing["version"] or 0),
                    "target_version": int(incoming["version"] or 0),
                    "transaction": dict(replay),
                }

            source_row = self._canonical_row_with_conn(conn, from_username)
            target_row = self._canonical_row_with_conn(conn, to_username)
            source_before = max(0, int(source_row["balance"] or 0))
            target_before = max(0, int(target_row["balance"] or 0))
            actual_amount = requested_amount
            if actual_amount > source_before:
                if not debit_up_to:
                    raise WalletInsufficientFunds("Brak srodkow.")
                actual_amount = source_before
            if actual_amount == 0:
                source_version = int(source_row["version"] or 0)
                target_version = int(target_row["version"] or 0)
                _wallet_record_balance_event_with_conn(
                    conn,
                    username=from_username,
                    transaction_key=transaction_key + ":out",
                    amount_delta=0,
                    balance=source_before,
                    version=source_version,
                    reason=source + ".outgoing.zero",
                    created_at=now,
                )
                _wallet_record_ledger_with_conn(
                    conn,
                    username=from_username,
                    event_type=source + ".outgoing.zero",
                    amount_delta=0,
                    balance_after=source_before,
                    source=source,
                    source_id=transaction_key,
                    peer_username=to_username,
                    note=note,
                    dedupe_key=f"wallet:ledger:{from_username}:{transaction_key}:out",
                    payload_json=dumps_json({
                        "transaction_key": transaction_key,
                        "zero_value_receipt": True,
                    }),
                    created_at=now,
                )
                _wallet_record_balance_event_with_conn(
                    conn,
                    username=to_username,
                    transaction_key=transaction_key + ":in",
                    amount_delta=0,
                    balance=target_before,
                    version=target_version,
                    reason=source + ".incoming.zero",
                    created_at=now,
                )
                _wallet_record_ledger_with_conn(
                    conn,
                    username=to_username,
                    event_type=source + ".incoming.zero",
                    amount_delta=0,
                    balance_after=target_before,
                    source=source,
                    source_id=transaction_key,
                    peer_username=from_username,
                    note=note,
                    dedupe_key=f"wallet:ledger:{to_username}:{transaction_key}:in",
                    payload_json=dumps_json({
                        "transaction_key": transaction_key,
                        "zero_value_receipt": True,
                    }),
                    created_at=now,
                )
                cursor = conn.execute(
                    """
                    INSERT INTO wallet_transactions
                        (from_username, to_username, amount, transaction_key,
                         note, created_at)
                    VALUES (?, ?, 0, ?, ?, ?)
                    """,
                    (from_username, to_username, transaction_key, note, now),
                )
                return {
                    "applied": False,
                    "duplicate": False,
                    "amount": 0,
                    "source_balance": source_before,
                    "target_balance": target_before,
                    "source_version": source_version,
                    "target_version": target_version,
                    "transaction": {
                        "id": cursor.lastrowid,
                        "from_username": from_username,
                        "to_username": to_username,
                        "amount": 0,
                        "transaction_key": transaction_key,
                        "note": note,
                        "created_at": now,
                    },
                    "reason": "zero_available",
                }

            source_version = int(source_row["version"] or 0) + 1
            target_version = int(target_row["version"] or 0) + 1
            source_after = source_before - actual_amount
            target_after = target_before + actual_amount
            conn.execute(
                """
                UPDATE wallet_balances
                SET balance = ?, version = ?, updated_at = ?
                WHERE username = ?
                """,
                (source_after, source_version, now, from_username),
            )
            _wallet_record_balance_event_with_conn(
                conn,
                username=from_username,
                transaction_key=transaction_key + ":out",
                amount_delta=-actual_amount,
                balance=source_after,
                version=source_version,
                reason=source + ".outgoing",
                created_at=now,
            )
            _wallet_record_ledger_with_conn(
                conn,
                username=from_username,
                event_type=source + ".outgoing",
                amount_delta=-actual_amount,
                balance_after=source_after,
                source=source,
                source_id=transaction_key,
                peer_username=to_username,
                note=note,
                dedupe_key=f"wallet:ledger:{from_username}:{transaction_key}:out",
                payload_json=dumps_json({"transaction_key": transaction_key}),
                created_at=now,
            )
            conn.execute(
                """
                UPDATE wallet_balances
                SET balance = ?, version = ?, updated_at = ?
                WHERE username = ?
                """,
                (target_after, target_version, now, to_username),
            )
            _wallet_record_balance_event_with_conn(
                conn,
                username=to_username,
                transaction_key=transaction_key + ":in",
                amount_delta=actual_amount,
                balance=target_after,
                version=target_version,
                reason=source + ".incoming",
                created_at=now,
            )
            _wallet_record_ledger_with_conn(
                conn,
                username=to_username,
                event_type=source + ".incoming",
                amount_delta=actual_amount,
                balance_after=target_after,
                source=source,
                source_id=transaction_key,
                peer_username=from_username,
                note=note,
                dedupe_key=f"wallet:ledger:{to_username}:{transaction_key}:in",
                payload_json=dumps_json({"transaction_key": transaction_key}),
                created_at=now,
            )
            cursor = conn.execute(
                """
                INSERT INTO wallet_transactions
                    (from_username, to_username, amount, transaction_key,
                     note, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    from_username,
                    to_username,
                    actual_amount,
                    transaction_key,
                    note,
                    now,
                ),
            )
            return {
                "applied": True,
                "duplicate": False,
                "amount": actual_amount,
                "source_balance": source_after,
                "target_balance": target_after,
                "source_version": source_version,
                "target_version": target_version,
                "transaction": {
                    "id": cursor.lastrowid,
                    "from_username": from_username,
                    "to_username": to_username,
                    "amount": actual_amount,
                    "transaction_key": transaction_key,
                    "note": note,
                    "created_at": now,
                },
            }

    def recovery_set_balance(
        self,
        username,
        balance,
        transaction_key,
        reason="wallet.recovery",
        *,
        expected_version=None,
    ):
        username = self._clean_text(username)
        transaction_key = self._clean_text(transaction_key)
        if not username or not transaction_key:
            raise WalletMutationRejected(
                "Recovery balance writes require username and transaction_key."
            )
        balance = max(0, _wallet_int(balance))
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            # This API can restore a known balance for an otherwise attested
            # wallet (for example a profile-store rollback), but it is not an
            # evidence-repair/unlock operation.  A blocked canonical migration
            # needs a separate forensic reconciliation proving ledger/event
            # consistency; never make an absolute write silently attest it.
            self._assert_migration_not_blocked_with_conn(conn, username)
            replay = conn.execute(
                """
                SELECT amount_delta, balance, version
                FROM wallet_balance_events
                WHERE username = ? AND transaction_key = ?
                """,
                (username, transaction_key),
            ).fetchone()
            if replay:
                if int(replay["balance"] or 0) != balance:
                    raise WalletIdempotencyConflict(
                        "Recovery transaction key was reused for another balance."
                    )
                return self._event_result(replay, username, transaction_key)
            if not conn.execute(
                "SELECT 1 FROM users WHERE username = ?", (username,)
            ).fetchone():
                raise WalletNotInitialized("Wallet owner does not exist.")
            current = conn.execute(
                "SELECT balance, version FROM wallet_balances WHERE username = ?",
                (username,),
            ).fetchone()
            previous = max(0, int(current["balance"] or 0)) if current else 0
            current_version = max(0, int(current["version"] or 0)) if current else 0
            if expected_version is not None and int(expected_version) != current_version:
                raise WalletIdempotencyConflict(
                    f"Expected wallet version {expected_version}, current is {current_version}."
                )
            if previous == balance and current is not None:
                _wallet_record_balance_event_with_conn(
                    conn,
                    username=username,
                    transaction_key=transaction_key,
                    amount_delta=0,
                    balance=balance,
                    version=current_version,
                    reason=self._clean_text(reason, "wallet.recovery") + ".zero",
                    created_at=now,
                )
                _wallet_record_ledger_with_conn(
                    conn,
                    username=username,
                    event_type=self._clean_text(reason, "wallet.recovery") + ".zero",
                    amount_delta=0,
                    balance_after=balance,
                    source="wallet.recovery",
                    source_id=transaction_key,
                    dedupe_key=f"wallet:ledger:{username}:{transaction_key}",
                    note=reason,
                    payload_json=dumps_json({
                        "previous_balance": previous,
                        "zero_value_receipt": True,
                    }),
                    created_at=now,
                )
                return {
                    "applied": False,
                    "duplicate": False,
                    "username": username,
                    "transaction_key": transaction_key,
                    "amount_delta": 0,
                    "balance": balance,
                    "version": current_version,
                    "reason": "zero_delta",
                }
            version = current_version + 1
            conn.execute(
                """
                INSERT INTO wallet_balances(username, balance, version, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    balance = excluded.balance,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (username, balance, version, now),
            )
            delta = balance - previous
            _wallet_record_balance_event_with_conn(
                conn,
                username=username,
                transaction_key=transaction_key,
                amount_delta=delta,
                balance=balance,
                version=version,
                reason=reason,
                created_at=now,
            )
            _wallet_record_ledger_with_conn(
                conn,
                username=username,
                event_type=self._clean_text(reason, "wallet.recovery"),
                amount_delta=delta,
                balance_after=balance,
                source="wallet.recovery",
                source_id=transaction_key,
                dedupe_key=f"wallet:ledger:{username}:{transaction_key}",
                note=reason,
                payload_json=dumps_json({"previous_balance": previous}),
                created_at=now,
            )
            return {
                "applied": True,
                "duplicate": False,
                "username": username,
                "transaction_key": transaction_key,
                "amount_delta": delta,
                "balance": balance,
                "version": version,
            }

    def set_balance(self, username, balance, transaction_key="", reason=""):
        del username, balance, transaction_key, reason
        raise WalletMutationRejected(
            "set_balance is disabled; use apply_delta/credit/debit/transfer "
            "or recovery_set_balance for an explicit recovery."
        )

    def mirror_profile(self, username, profile):
        if isinstance(profile, dict):
            profile["hackcoins"] = self.get_balance(username)
        return profile

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM wallet_transactions")
            conn.execute("DELETE FROM wallet_ledger")
            conn.execute("DELETE FROM wallet_balance_events")
            conn.execute("DELETE FROM wallet_balances")


class PlayerTargetRuntimeStore:
    STATUS_CLEARED = "cleared"
    STATUS_AIMED = "aimed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CAPTURED = "captured"

    TERMINAL_STATUSES = {STATUS_CLEARED, STATUS_CAPTURED}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _is_missing_target_name(value):
        if value is None:
            return True
        normalized = str(value).strip().lower()
        return normalized in {
            "",
            "brak",
            "brak nazwy",
            "brak_nazwy",
            "no name",
            "unnamed",
            "unnamed target",
            "unknown",
            "none",
            "null",
        }

    @staticmethod
    def _is_placeholder_target_key(value):
        normalized = str(value or "").strip().lower()
        if not normalized:
            return True
        if normalized in {
            "map:0.0:0.0:target",
            "map:0:0:target",
            "map:unknown:unknown:target",
        }:
            return True
        parts = normalized.split(":")
        if len(parts) >= 4 and parts[0] == "map":
            missing_coord = {"0", "0.0", "0.00", "unknown", "none", "null"}
            missing_label = {"", "target", "brak", "unknown", "none", "null"}
            return parts[1] in missing_coord and parts[2] in missing_coord and ":".join(parts[3:]) in missing_label
        return False

    @staticmethod
    def target_key(target):
        target = target if isinstance(target, dict) else {}
        if target.get("target_id"):
            key = str(target.get("target_id"))
            return "" if PlayerTargetRuntimeStore._is_placeholder_target_key(key) else key
        if target.get("target_mode") == "player" and target.get("target_username"):
            return f"player:{target.get('target_username')}"
        if target.get("vulnerability_id"):
            return f"vulnerability:{target.get('vulnerability_id')}"
        if target.get("foreign_area_id"):
            lat = target.get("lat")
            lng = target.get("lng", target.get("lon"))
            return f"territory_contest:{target.get('foreign_area_id')}:{lat}:{lng}"
        lat = target.get("lat")
        lng = target.get("lng", target.get("lon"))
        label = target.get("label") or target.get("name") or target.get("source_type") or "target"
        key = f"map:{lat}:{lng}:{label}"
        return "" if PlayerTargetRuntimeStore._is_placeholder_target_key(key) else key

    @staticmethod
    def _ordinary_map_position_key(target, precision=5):
        """Return a coordinate identity only for ordinary map POIs.

        Map labels are presentation data and can differ between the lightweight
        title click, the picker and an installed app. Special targets keep their
        strict domain identity and must never be aliased by coordinates.
        """
        target = target if isinstance(target, dict) else {}
        if (
            str(target.get("target_mode") or "").strip() in {"player", "territory_contest", "vulnerability"}
            or target.get("target_username")
            or target.get("vulnerability_id")
            or target.get("foreign_area_id")
            or target.get("stable_conflict_id")
            or target.get("conflict_id")
        ):
            return None
        try:
            return (
                round(float(target.get("lat")), precision),
                round(float(target.get("lng", target.get("lon"))), precision),
            )
        except (TypeError, ValueError):
            return None

    @classmethod
    def _same_ordinary_map_target(cls, current_target, incoming_target):
        current_position = cls._ordinary_map_position_key(current_target)
        incoming_position = cls._ordinary_map_position_key(incoming_target)
        return bool(current_position and current_position == incoming_position)

    @classmethod
    def _progress_from_target(cls, target):
        target = target if isinstance(target, dict) else {}
        allowed = target.get("actions_allowed") or {}
        if not isinstance(allowed, dict):
            allowed = {}
        security = target.get("security") or {}
        if not isinstance(security, dict):
            security = {}
        # Runtime and frontend share a percentage contract here. Older code
        # persisted the raw number of completed actions (1..4), which made the
        # toolbar render a nearly invisible 1-4% line despite lit action dots.
        action_keys = ("scan_ports", "exploit", "sniff", "trace")
        action_values = [allowed.get(key) for key in action_keys]
        action_progress = round(
            (sum(1 for value in action_values if value is True) / len(action_keys)) * 100
        )
        security_values = [value for value in security.values() if isinstance(value, bool)]
        security_progress = (
            round(
                (sum(1 for value in security_values if value is False) / len(security_values)) * 100
            )
            if security_values
            else 0
        )
        explicit_progress = target.get("disarm_progress")
        try:
            explicit_progress = max(0, min(100, int(explicit_progress)))
        except (TypeError, ValueError):
            explicit_progress = 0
        return int(max(action_progress, security_progress, explicit_progress))

    @staticmethod
    def _merge_actions(current, incoming):
        merged = dict(current or {}) if isinstance(current, dict) else {}
        if isinstance(incoming, dict):
            for key, value in incoming.items():
                if value is True or key not in merged:
                    merged[key] = value
        return merged

    @staticmethod
    def _merge_security(current, incoming):
        merged = dict(current or {}) if isinstance(current, dict) else {}
        if isinstance(incoming, dict):
            for key, value in incoming.items():
                if value is False or key not in merged:
                    merged[key] = value
        return merged

    @classmethod
    def _row_payload(cls, row):
        if not row:
            return None
        target = loads_json(row["target_json"], {})
        security = loads_json(row["security_json"], {})
        actions_allowed = loads_json(row["actions_allowed_json"], {})
        if isinstance(target, dict) and target:
            target["security"] = security if isinstance(security, dict) else {}
            target["actions_allowed"] = actions_allowed if isinstance(actions_allowed, dict) else {}
            target["target_id"] = target.get("target_id") or row["target_key"]
            target["disarm_progress"] = int(row["disarm_progress"] or 0)
        return {
            "username": row["username"],
            "target_key": row["target_key"],
            "target": target if isinstance(target, dict) else {},
            "security": security if isinstance(security, dict) else {},
            "actions_allowed": actions_allowed if isinstance(actions_allowed, dict) else {},
            "disarm_progress": int(row["disarm_progress"] or 0),
            "status": row["status"],
            "version": int(row["version"] or 0),
            "updated_at": row["updated_at"],
        }

    def _record_event(self, conn, username, event_type, target_key, version, payload=None):
        conn.execute(
            """
            INSERT INTO player_target_events
                (username, event_type, target_key, version, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                event_type,
                target_key or "",
                int(version or 0),
                dumps_json(payload or {}),
                utc_now(),
            ),
        )

    def get(self, username):
        username = self._clean_text(username)
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            return self._row_payload(row)

    def get_active_target(self, username):
        payload = self.get(username)
        if not payload or payload.get("status") in self.TERMINAL_STATUSES:
            return {}
        return dict(payload.get("target") or {})

    def upsert_aimed(self, username, target, status=STATUS_AIMED, source="", expected_target=None):
        username = self._clean_text(username)
        target = dict(target or {}) if isinstance(target, dict) else {}
        target_key = self.target_key(target)
        if not username or not target_key:
            return {"changed": False, "target": target, "status": "invalid", "version": 0}

        incoming_security = target.get("security") if isinstance(target.get("security"), dict) else {}
        incoming_actions = target.get("actions_allowed") if isinstance(target.get("actions_allowed"), dict) else {}
        incoming_progress = self._progress_from_target(target)
        now = utc_now()

        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            current = self._row_payload(row)
            if current and isinstance(expected_target, dict) and expected_target:
                expected_key = self.target_key(expected_target)
                expected_matches_current = bool(
                    current.get("target_key") == expected_key
                    or self._same_ordinary_map_target(current.get("target"), expected_target)
                )
                if not expected_matches_current:
                    self._record_event(
                        conn,
                        username,
                        "target.progress_rejected",
                        current.get("target_key"),
                        current.get("version"),
                        {"source": source, "reason": "selection_changed", "expected_target_key": expected_key},
                    )
                    return {
                        "changed": False,
                        "target": dict(current.get("target") or {}),
                        "status": "selection_changed",
                        "version": current.get("version", 0),
                    }
            same_runtime_target = bool(
                current
                and (
                    current.get("target_key") == target_key
                    or self._same_ordinary_map_target(current.get("target"), target)
                )
            )
            if same_runtime_target and current.get("status") == self.STATUS_CAPTURED:
                self._record_event(conn, username, "target.aimed_rejected", target_key, current.get("version"), {"source": source})
                return {
                    "changed": False,
                    "target": {},
                    "status": "captured",
                    "version": current.get("version", 0),
                }

            if same_runtime_target:
                merged_security = self._merge_security(current.get("security"), incoming_security)
                merged_actions = self._merge_actions(current.get("actions_allowed"), incoming_actions)
                merged_target = dict(current.get("target") or {})
                for key, value in target.items():
                    if key in {"display_label", "label", "name", "title"} and self._is_missing_target_name(value):
                        continue
                    merged_target[key] = value
                merged_target["security"] = merged_security
                merged_target["actions_allowed"] = merged_actions
                # Keep the identity already handed to the application window.
                # A later payload may carry another display-derived map id for
                # the same coordinates; changing it would split progress.
                target_key = current.get("target_key") or target_key
                merged_target["target_id"] = target_key
                progress = max(int(current.get("disarm_progress") or 0), incoming_progress)
                version = int(current.get("version") or 0) + 1
            else:
                merged_security = dict(incoming_security or {})
                merged_actions = dict(incoming_actions or {})
                merged_target = dict(target)
                merged_target["security"] = merged_security
                merged_target["actions_allowed"] = merged_actions
                progress = incoming_progress
                version = int(current.get("version") or 0) + 1 if current else 1

            merged_target["target_id"] = merged_target.get("target_id") or target_key
            target_json = dumps_json(merged_target)
            security_json = dumps_json(merged_security)
            actions_json = dumps_json(merged_actions)
            observed_version = int(row["version"] or 0) if row else 0
            conn.execute("BEGIN IMMEDIATE")
            latest = conn.execute(
                "SELECT version FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            latest_version = int(latest["version"] or 0) if latest else 0
            if latest_version != observed_version:
                return {
                    "changed": False,
                    "target": dict(current.get("target") or {}) if current else {},
                    "status": "concurrent_change",
                    "version": latest_version,
                }
            conn.execute(
                """
                INSERT INTO player_target_runtime
                    (username, target_key, target_json, security_json, actions_allowed_json,
                     disarm_progress, status, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    target_key = excluded.target_key,
                    target_json = excluded.target_json,
                    security_json = excluded.security_json,
                    actions_allowed_json = excluded.actions_allowed_json,
                    disarm_progress = excluded.disarm_progress,
                    status = excluded.status,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    target_key,
                    target_json,
                    security_json,
                    actions_json,
                    progress,
                    self._clean_text(status, self.STATUS_AIMED),
                    version,
                    now,
                ),
            )
            event_type = "target.progressed" if same_runtime_target else "target.aimed"
            self._record_event(conn, username, event_type, target_key, version, {"source": source})
            return {
                "changed": True,
                "target": merged_target,
                "status": self._clean_text(status, self.STATUS_AIMED),
                "version": version,
            }

    def mark_captured(self, username, target, source=""):
        return self._terminal_update(username, target, self.STATUS_CAPTURED, "target.captured", source)

    def clear_if_matches(self, username, reference_target, source=""):
        username = self._clean_text(username)
        reference_key = self.target_key(reference_target)
        if not username:
            return False
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            current = self._row_payload(row)
            if not current:
                return False
            if reference_key and current.get("target_key") != reference_key:
                return False
            version = int(current.get("version") or 0) + 1
            now = utc_now()
            conn.execute(
                """
                UPDATE player_target_runtime
                SET target_json = '{}',
                    security_json = '{}',
                    actions_allowed_json = '{}',
                    disarm_progress = 0,
                    status = ?,
                    version = ?,
                    updated_at = ?
                WHERE username = ?
                """,
                (self.STATUS_CLEARED, version, now, username),
            )
            self._record_event(conn, username, "target.cleared", current.get("target_key"), version, {"source": source})
            return True

    def _terminal_update(self, username, target, status, event_type, source=""):
        username = self._clean_text(username)
        target = dict(target or {}) if isinstance(target, dict) else {}
        target_key = self.target_key(target)
        if not username or not target_key:
            return {"changed": False, "target": {}, "status": "invalid", "version": 0}
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            current = self._row_payload(row)
            version = int((current or {}).get("version") or 0) + 1
            conn.execute(
                """
                INSERT INTO player_target_runtime
                    (username, target_key, target_json, security_json, actions_allowed_json,
                     disarm_progress, status, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    target_key = excluded.target_key,
                    target_json = excluded.target_json,
                    security_json = excluded.security_json,
                    actions_allowed_json = excluded.actions_allowed_json,
                    disarm_progress = excluded.disarm_progress,
                    status = excluded.status,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    target_key,
                    dumps_json(target),
                    dumps_json(target.get("security") if isinstance(target.get("security"), dict) else {}),
                    dumps_json(target.get("actions_allowed") if isinstance(target.get("actions_allowed"), dict) else {}),
                    self._progress_from_target(target),
                    status,
                    version,
                    now,
                ),
            )
            self._record_event(conn, username, event_type, target_key, version, {"source": source})
            return {"changed": True, "target": target, "status": status, "version": version}

    def seed_from_profile(self, username, profile):
        if self.get(username):
            return self.get_active_target(username)
        target = (profile or {}).get("aimed_target") if isinstance(profile, dict) else {}
        if not isinstance(target, dict) or not target:
            return {}
        return self.upsert_aimed(username, target, source="profile_fallback").get("target") or {}

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM player_target_runtime")
            conn.execute("DELETE FROM player_target_events")


class PlayerMarkedTargetStore:
    """Canonical collection of durable map markers owned by one player.

    ``player_target_runtime`` intentionally models one active hacking target.
    This store models the independent, potentially larger collection previously
    embedded in ``profile_json.targets``.  The legacy list is imported once per
    account and is never consulted again after the state receipt is written.
    """

    STATUS_ACTIVE = "active"
    STATUS_REMOVED = "removed"

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_username(value):
        return str(value or "").strip()

    @classmethod
    def normalize_target(cls, target):
        target = dict(target or {}) if isinstance(target, dict) else {}
        try:
            lat = float(target.get("lat"))
            lng = float(target.get("lng", target.get("lon")))
        except (TypeError, ValueError):
            return None
        if not (
            math.isfinite(lat) and math.isfinite(lng)
            and -90 <= lat <= 90 and -180 <= lng <= 180
        ):
            return None

        label = str(
            target.get("label") or target.get("name")
            or target.get("source_type") or "TARGET"
        ).strip()
        if not label:
            return None
        normalized = dict(target)
        normalized.update({
            "lat": lat,
            "lng": lng,
            "label": label,
            "name": str(target.get("name") or label),
            "icon": str(target.get("icon") or "\U0001F3AF"),
            "source_type": str(target.get("source_type") or "manual"),
            "generated": bool(target.get("generated", False)),
        })
        normalized.pop("lon", None)
        target_key = PlayerTargetRuntimeStore.target_key(normalized)
        if not target_key:
            return None
        normalized["target_id"] = target_key
        return normalized

    @staticmethod
    def _list_with_conn(conn, username):
        rows = conn.execute(
            """
            SELECT target_json
            FROM player_marked_targets
            WHERE username = ? AND status = 'active'
            ORDER BY created_at, target_key
            """,
            (username,),
        ).fetchall()
        return [
            target
            for target in (loads_json(row["target_json"], {}) for row in rows)
            if isinstance(target, dict) and target
        ]

    def is_seeded(self, username):
        username = self._clean_username(username)
        if not username:
            return False
        with db_connect(self.db_path) as conn:
            return conn.execute(
                "SELECT 1 FROM player_marked_target_state WHERE username = ?",
                (username,),
            ).fetchone() is not None

    def ensure_seeded(self, username):
        """One-way, idempotent import of the compact legacy ``targets`` list."""
        username = self._clean_username(username)
        if not username:
            raise ValueError("Marked target seed requires username.")
        if self.is_seeded(username):
            return {"seeded": False, "already_seeded": True, "migrated_count": 0}

        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT profile_revision, profile_checksum, profile_integrity_status,
                       json_valid(profile_json) AS profile_json_valid,
                       CASE WHEN json_valid(profile_json)
                            THEN json_type(profile_json) END AS profile_json_type,
                       CASE WHEN json_valid(profile_json)
                            THEN json_extract(profile_json, '$.targets') END AS targets_json
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
        if row is None:
            raise ValueError(f"User '{username}' not found.")
        if (
            not bool(row["profile_json_valid"])
            or str(row["profile_json_type"] or "") != "object"
            or str(row["profile_integrity_status"] or "") != PROFILE_INTEGRITY_VALID
            or int(row["profile_revision"] or 0) <= 0
            or not str(row["profile_checksum"] or "")
        ):
            raise ProfileRecoveryRequired(
                f"User '{username}' requires profile recovery before marked target migration."
            )

        try:
            legacy_targets = json.loads(row["targets_json"] or "[]")
        except (TypeError, json.JSONDecodeError) as exc:
            raise ProfileRecoveryRequired(
                f"User '{username}' has an invalid legacy targets projection."
            ) from exc
        if not isinstance(legacy_targets, list):
            raise ProfileRecoveryRequired(
                f"User '{username}' has a non-list legacy targets projection."
            )
        normalized_targets = [
            normalized
            for normalized in (self.normalize_target(item) for item in legacy_targets)
            if normalized is not None
        ]
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing_state = conn.execute(
                "SELECT 1 FROM player_marked_target_state WHERE username = ?",
                (username,),
            ).fetchone()
            if existing_state is not None:
                return {"seeded": False, "already_seeded": True, "migrated_count": 0}
            for target in normalized_targets:
                target_key = target["target_id"]
                conn.execute(
                    """
                    INSERT OR IGNORE INTO player_marked_targets
                        (username, target_key, target_json, lat, lng, label,
                         status, version, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'active', 1, 'legacy_profile_seed', ?, ?)
                    """,
                    (
                        username, target_key, dumps_json(target), target["lat"],
                        target["lng"], target["label"], now, now,
                    ),
                )
            conn.execute(
                """
                INSERT INTO player_marked_target_state
                    (username, source_revision, migrated_count, seeded_at)
                VALUES (?, ?, ?, ?)
                """,
                (username, int(row["profile_revision"] or 0), len(normalized_targets), now),
            )
        return {
            "seeded": True,
            "already_seeded": False,
            "migrated_count": len(normalized_targets),
        }

    def list_targets(self, username, ensure_seeded=True):
        username = self._clean_username(username)
        if not username:
            return []
        if ensure_seeded:
            self.ensure_seeded(username)
        with db_connect(self.db_path) as conn:
            return self._list_with_conn(conn, username)

    def upsert(self, username, target, source="map.mark_target"):
        username = self._clean_username(username)
        normalized = self.normalize_target(target)
        if not username or normalized is None:
            raise ValueError("A marked target requires username and valid target data.")
        self.ensure_seeded(username)
        target_key = normalized["target_id"]
        target_json = dumps_json(normalized)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT target_json, status, version, created_at
                FROM player_marked_targets
                WHERE username = ? AND target_key = ?
                """,
                (username, target_key),
            ).fetchone()
            if (
                row is not None
                and row["status"] == self.STATUS_ACTIVE
                and str(row["target_json"] or "") == target_json
            ):
                return {
                    "changed": False,
                    "duplicate": True,
                    "target": normalized,
                    "version": int(row["version"] or 1),
                }
            version = int(row["version"] or 0) + 1 if row else 1
            created_at = row["created_at"] if row else now
            conn.execute(
                """
                INSERT INTO player_marked_targets
                    (username, target_key, target_json, lat, lng, label,
                     status, version, source, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
                ON CONFLICT(username, target_key) DO UPDATE SET
                    target_json = excluded.target_json,
                    lat = excluded.lat,
                    lng = excluded.lng,
                    label = excluded.label,
                    status = 'active',
                    version = excluded.version,
                    source = excluded.source,
                    updated_at = excluded.updated_at
                """,
                (
                    username, target_key, target_json, normalized["lat"],
                    normalized["lng"], normalized["label"], version,
                    str(source or "map.mark_target"), created_at, now,
                ),
            )
        return {
            "changed": True,
            "duplicate": False,
            "target": normalized,
            "version": version,
        }

    def remove_matching(self, username, target, match_label=False, source="target.captured"):
        username = self._clean_username(username)
        normalized = self.normalize_target(target)
        if not username or normalized is None:
            return 0
        self.ensure_seeded(username)
        wanted_key = normalized["target_id"]
        wanted_lat = round(float(normalized["lat"]), 5)
        wanted_lng = round(float(normalized["lng"]), 5)
        wanted_label = str(normalized.get("label") or "")
        now = utc_now()
        removed = 0
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT target_key, target_json, version
                FROM player_marked_targets
                WHERE username = ? AND status = 'active'
                """,
                (username,),
            ).fetchall()
            matches = []
            for row in rows:
                item = loads_json(row["target_json"], {})
                try:
                    same_position = (
                        round(float(item.get("lat")), 5) == wanted_lat
                        and round(float(item.get("lng", item.get("lon"))), 5) == wanted_lng
                    )
                except (TypeError, ValueError):
                    same_position = False
                same_label = str(item.get("label") or item.get("name") or "") == wanted_label
                if row["target_key"] == wanted_key or (same_position and (not match_label or same_label)):
                    matches.append((row["target_key"], int(row["version"] or 0) + 1))
            if matches:
                conn.execute("BEGIN IMMEDIATE")
                for target_key, version in matches:
                    updated = conn.execute(
                        """
                        UPDATE player_marked_targets
                        SET status = 'removed', version = ?, source = ?, updated_at = ?
                        WHERE username = ? AND target_key = ? AND status = 'active'
                        """,
                        (version, str(source or "target.captured"), now, username, target_key),
                    )
                    removed += int(updated.rowcount or 0)
        return removed

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM player_marked_targets")
            conn.execute("DELETE FROM player_marked_target_state")


class PlayerPositionStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _normalize(position):
        if not isinstance(position, dict):
            return {}
        try:
            lat = float(position.get("lat"))
            lng = float(position.get("lng", position.get("lon")))
        except (TypeError, ValueError):
            return {}
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return {}
        return {"lat": lat, "lng": lng}

    @staticmethod
    def _row_payload(row):
        if not row:
            return None
        return {
            "username": row["username"],
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "source": row["source"],
            "version": int(row["version"] or 0),
            "updated_at": row["updated_at"],
        }

    def get(self, username):
        username = str(username or "").strip()
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM player_positions WHERE username = ?",
                (username,),
            ).fetchone()
            return self._row_payload(row)

    def get_position(self, username):
        row = self.get(username)
        if not row:
            return {}
        return {"lat": row["lat"], "lng": row["lng"]}

    def upsert(self, username, position, source="runtime"):
        username = str(username or "").strip()
        normalized = self._normalize(position)
        if not username or not normalized:
            return {"changed": False, "position": {}, "version": 0, "updated_at": ""}
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_positions WHERE username = ?",
                (username,),
            ).fetchone()
            current = self._row_payload(row)
            if current:
                same_lat = abs(float(current.get("lat", 0)) - normalized["lat"]) < 0.0000001
                same_lng = abs(float(current.get("lng", 0)) - normalized["lng"]) < 0.0000001
                if same_lat and same_lng:
                    return {
                        "changed": False,
                        "position": {"lat": float(current["lat"]), "lng": float(current["lng"])},
                        "version": int(current.get("version") or 0),
                        "updated_at": current.get("updated_at") or "",
                    }
            version = int((current or {}).get("version") or 0) + 1
            conn.execute(
                """
                INSERT INTO player_positions
                    (username, lat, lng, source, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    lat = excluded.lat,
                    lng = excluded.lng,
                    source = excluded.source,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    normalized["lat"],
                    normalized["lng"],
                    str(source or "runtime"),
                    version,
                    now,
                ),
            )
            return {
                "changed": True,
                "position": normalized,
                "version": version,
                "updated_at": now,
            }

    def seed_from_profile(self, username, profile, source="profile_fallback"):
        if self.get(username):
            return self.get_position(username)
        profile = profile if isinstance(profile, dict) else {}
        position = profile.get("curently_possition") or profile.get("current_position") or {}
        result = self.upsert(username, position, source=source)
        return result.get("position") or {}

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM player_positions")


CYBERNER_MESSAGE_PAGE_LIMIT = 100
CYBERNER_MESSAGE_PAGE_LIMIT_MAX = 200


def _cyberner_message_page_limit(limit):
    try:
        normalized = int(limit or CYBERNER_MESSAGE_PAGE_LIMIT)
    except (TypeError, ValueError):
        normalized = CYBERNER_MESSAGE_PAGE_LIMIT
    return max(1, min(CYBERNER_MESSAGE_PAGE_LIMIT_MAX, normalized))


def _cyberner_message_id(prefix):
    return f"{prefix}_{secrets.token_hex(16)}"


def _cyberner_message_payload(row, channel, channel_key):
    if not row:
        return None
    payload = {
        "id": int(row["id"]),
        "message_id": row["message_id"],
        "channel": channel,
        "channel_key": channel_key,
        "sender": row["sender_username"],
        "sender_username": row["sender_username"],
        "subject": row["subject"],
        "body": row["body"],
        "created_at": row["created_at"],
    }
    if row["client_message_id"]:
        payload["client_message_id"] = row["client_message_id"]
    return payload


class CybernerWorldStore:
    CHANNEL = "world"
    CHANNEL_KEY = "global"

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def add_message(self, sender_username, body, subject="", client_message_id=None,
                    message_id=None, created_at=None):
        sender_username = str(sender_username or "").strip()
        body = str(body or "").strip()
        if not sender_username:
            raise ValueError("Sender username is required.")
        if not body:
            raise ValueError("Message body is required.")
        subject = str(subject or "").strip()
        client_message_id = str(client_message_id or "").strip() or None
        message_id = str(message_id or "").strip() or _cyberner_message_id("cyberner_world")
        created_at = str(created_at or "").strip() or utc_now()

        with db_connect(self.db_path) as conn:
            if client_message_id:
                existing = conn.execute(
                    """
                    SELECT id, message_id, sender_username, subject, body, created_at, client_message_id
                    FROM cyberner_world_messages
                    WHERE sender_username = ? AND client_message_id = ?
                    """,
                    (sender_username, client_message_id),
                ).fetchone()
                if existing:
                    return _cyberner_message_payload(existing, self.CHANNEL, self.CHANNEL_KEY), False
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO cyberner_world_messages
                        (message_id, sender_username, subject, body, created_at, client_message_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (message_id, sender_username, subject, body, created_at, client_message_id),
                )
            except sqlite3.IntegrityError:
                if not client_message_id:
                    raise
                existing = conn.execute(
                    """
                    SELECT id, message_id, sender_username, subject, body, created_at, client_message_id
                    FROM cyberner_world_messages
                    WHERE sender_username = ? AND client_message_id = ?
                    """,
                    (sender_username, client_message_id),
                ).fetchone()
                if not existing:
                    raise
                return _cyberner_message_payload(existing, self.CHANNEL, self.CHANNEL_KEY), False
            row = conn.execute(
                """
                SELECT id, message_id, sender_username, subject, body, created_at, client_message_id
                FROM cyberner_world_messages WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            return _cyberner_message_payload(row, self.CHANNEL, self.CHANNEL_KEY), True

    def list_messages(self, after_id=None, before_id=None, limit=CYBERNER_MESSAGE_PAGE_LIMIT):
        if after_id not in (None, "") and before_id not in (None, ""):
            raise ValueError("Use either after_id or before_id.")
        limit = _cyberner_message_page_limit(limit)
        where = ""
        params = []
        descending = before_id not in (None, "") or after_id in (None, "")
        if after_id not in (None, ""):
            where = "WHERE id > ?"
            params.append(max(0, int(after_id)))
            descending = False
        elif before_id not in (None, ""):
            where = "WHERE id < ?"
            params.append(max(0, int(before_id)))
        params.append(limit)
        order = "DESC" if descending else "ASC"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT id, message_id, sender_username, subject, body, created_at, client_message_id
                FROM cyberner_world_messages
                {where}
                ORDER BY id {order}
                LIMIT ?
                """,
                params,
            ).fetchall()
        if descending:
            rows = list(reversed(rows))
        return [_cyberner_message_payload(row, self.CHANNEL, self.CHANNEL_KEY) for row in rows]

    def latest_message_id(self):
        with db_connect(self.db_path) as conn:
            row = conn.execute("SELECT MAX(id) AS latest_id FROM cyberner_world_messages").fetchone()
            return int(row["latest_id"] or 0)

    def count_after(self, message_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM cyberner_world_messages WHERE id > ?",
                (max(0, int(message_id or 0)),),
            ).fetchone()
            return int(row["count"] or 0)


class CybernerClanStore:
    CHANNEL = "clan"

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def normalize_clan_key(clan_key):
        normalized = str(clan_key or "").strip()
        if not normalized:
            raise ValueError("Clan key is required.")
        return normalized

    def add_message(self, clan_key, sender_username, body, subject="", client_message_id=None,
                    message_id=None, created_at=None):
        clan_key = self.normalize_clan_key(clan_key)
        sender_username = str(sender_username or "").strip()
        body = str(body or "").strip()
        if not sender_username:
            raise ValueError("Sender username is required.")
        if not body:
            raise ValueError("Message body is required.")
        subject = str(subject or "").strip()
        client_message_id = str(client_message_id or "").strip() or None
        message_id = str(message_id or "").strip() or _cyberner_message_id("cyberner_clan")
        created_at = str(created_at or "").strip() or utc_now()

        with db_connect(self.db_path) as conn:
            if client_message_id:
                existing = conn.execute(
                    """
                    SELECT id, message_id, clan_key, sender_username, subject, body, created_at, client_message_id
                    FROM cyberner_clan_messages
                    WHERE clan_key = ? AND sender_username = ? AND client_message_id = ?
                    """,
                    (clan_key, sender_username, client_message_id),
                ).fetchone()
                if existing:
                    return _cyberner_message_payload(existing, self.CHANNEL, clan_key), False
            try:
                cursor = conn.execute(
                    """
                    INSERT INTO cyberner_clan_messages
                        (message_id, clan_key, sender_username, subject, body, created_at, client_message_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (message_id, clan_key, sender_username, subject, body, created_at, client_message_id),
                )
            except sqlite3.IntegrityError:
                if not client_message_id:
                    raise
                existing = conn.execute(
                    """
                    SELECT id, message_id, clan_key, sender_username, subject, body, created_at, client_message_id
                    FROM cyberner_clan_messages
                    WHERE clan_key = ? AND sender_username = ? AND client_message_id = ?
                    """,
                    (clan_key, sender_username, client_message_id),
                ).fetchone()
                if not existing:
                    raise
                return _cyberner_message_payload(existing, self.CHANNEL, clan_key), False
            row = conn.execute(
                """
                SELECT id, message_id, clan_key, sender_username, subject, body, created_at, client_message_id
                FROM cyberner_clan_messages WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
            return _cyberner_message_payload(row, self.CHANNEL, clan_key), True

    def list_messages(self, clan_key, after_id=None, before_id=None, limit=CYBERNER_MESSAGE_PAGE_LIMIT):
        clan_key = self.normalize_clan_key(clan_key)
        if after_id not in (None, "") and before_id not in (None, ""):
            raise ValueError("Use either after_id or before_id.")
        limit = _cyberner_message_page_limit(limit)
        clauses = ["clan_key = ?"]
        params = [clan_key]
        descending = before_id not in (None, "") or after_id in (None, "")
        if after_id not in (None, ""):
            clauses.append("id > ?")
            params.append(max(0, int(after_id)))
            descending = False
        elif before_id not in (None, ""):
            clauses.append("id < ?")
            params.append(max(0, int(before_id)))
        params.append(limit)
        order = "DESC" if descending else "ASC"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT id, message_id, clan_key, sender_username, subject, body, created_at, client_message_id
                FROM cyberner_clan_messages
                WHERE {' AND '.join(clauses)}
                ORDER BY id {order}
                LIMIT ?
                """,
                params,
            ).fetchall()
        if descending:
            rows = list(reversed(rows))
        return [_cyberner_message_payload(row, self.CHANNEL, clan_key) for row in rows]

    def latest_message_id(self, clan_key):
        clan_key = self.normalize_clan_key(clan_key)
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT MAX(id) AS latest_id FROM cyberner_clan_messages WHERE clan_key = ?",
                (clan_key,),
            ).fetchone()
            return int(row["latest_id"] or 0)

    def count_after(self, clan_key, message_id):
        clan_key = self.normalize_clan_key(clan_key)
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count FROM cyberner_clan_messages
                WHERE clan_key = ? AND id > ?
                """,
                (clan_key, max(0, int(message_id or 0))),
            ).fetchone()
            return int(row["count"] or 0)


class CybernerChannelCursorStore:
    CHANNEL_TYPES = {"world", "clan"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @classmethod
    def normalize_identity(cls, username, channel_type, channel_key):
        username = str(username or "").strip()
        channel_type = str(channel_type or "").strip().lower()
        channel_key = str(channel_key or "").strip()
        if not username:
            raise ValueError("Username is required.")
        if channel_type not in cls.CHANNEL_TYPES:
            raise ValueError("Unsupported shared Cyberner channel type.")
        if not channel_key:
            raise ValueError("Channel key is required.")
        return username, channel_type, channel_key

    def get(self, username, channel_type, channel_key):
        username, channel_type, channel_key = self.normalize_identity(username, channel_type, channel_key)
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT username, channel_type, channel_key, last_read_message_id, updated_at
                FROM cyberner_channel_cursors
                WHERE username = ? AND channel_type = ? AND channel_key = ?
                """,
                (username, channel_type, channel_key),
            ).fetchone()
        if not row:
            return {
                "username": username,
                "channel_type": channel_type,
                "channel_key": channel_key,
                "last_read_message_id": 0,
                "updated_at": None,
            }
        return {
            "username": row["username"],
            "channel_type": row["channel_type"],
            "channel_key": row["channel_key"],
            "last_read_message_id": int(row["last_read_message_id"] or 0),
            "updated_at": row["updated_at"],
        }

    def advance(self, username, channel_type, channel_key, message_id):
        username, channel_type, channel_key = self.normalize_identity(username, channel_type, channel_key)
        message_id = max(0, int(message_id or 0))
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO cyberner_channel_cursors
                    (username, channel_type, channel_key, last_read_message_id, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(username, channel_type, channel_key) DO UPDATE SET
                    last_read_message_id = MAX(last_read_message_id, excluded.last_read_message_id),
                    updated_at = CASE
                        WHEN excluded.last_read_message_id > last_read_message_id THEN excluded.updated_at
                        ELSE updated_at
                    END
                """,
                (username, channel_type, channel_key, message_id, now),
            )
        return self.get(username, channel_type, channel_key)


class MailStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def ensure_seeded(self, username, profile=None, default_contacts=None, default_messages=None):
        seed_key = f"mail_seed:{username}"
        with db_connect(self.db_path) as conn:
            seeded = conn.execute(
                "SELECT 1 FROM kv_store WHERE key = ?",
                (seed_key,),
            ).fetchone()
            if seeded:
                return

            now = utc_now()
            contacts = []
            for friend in (profile or {}).get("friends", []):
                if isinstance(friend, str):
                    contacts.append({"name": friend, "status": "offline"})
                elif isinstance(friend, dict):
                    contacts.append({
                        "name": friend.get("name", ""),
                        "status": friend.get("status", "offline"),
                    })

            seen = set()
            for contact in contacts:
                name = (contact.get("name") or "").strip()
                if not name or name in seen:
                    continue
                user_exists = conn.execute(
                    "SELECT 1 FROM users WHERE username = ?",
                    (name,),
                ).fetchone()
                if not user_exists:
                    continue
                seen.add(name)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO contacts
                        (owner_username, contact_name, status, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, name, contact.get("status", "offline"), now),
                )

            for msg in default_messages or []:
                if not isinstance(msg, dict):
                    continue
                sender = msg.get("from", "System")
                subject = msg.get("subject", "")
                body = msg.get("content", "")
                if not body and not subject:
                    continue
                conn.execute(
                    """
                    INSERT INTO chat_messages
                        (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                    VALUES (?, 'group', 'global', ?, ?, ?, ?, ?)
                    """,
                    (username, sender, subject, body, now, now),
                )

            conn.execute(
                """
                INSERT INTO kv_store (key, value_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (seed_key, dumps_json({"seeded": True}), now),
            )

    def list_contacts(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT contact_name, status
                FROM contacts
                WHERE owner_username = ?
                ORDER BY contact_name COLLATE NOCASE
                """,
                (username,),
            ).fetchall()
            return [{"name": row["contact_name"], "status": row["status"]} for row in rows]

    def is_contact(self, username, contact_name):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT 1 FROM contacts
                WHERE owner_username = ? AND contact_name = ?
                """,
                (username, contact_name),
            ).fetchone()
            return row is not None

    def is_accepted_contact(self, username, contact_name):
        if not username or not contact_name:
            return False
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM contacts own
                JOIN contacts reciprocal
                    ON reciprocal.owner_username = own.contact_name
                    AND reciprocal.contact_name = own.owner_username
                WHERE own.owner_username = ?
                    AND own.contact_name = ?
                """,
                (username, contact_name),
            ).fetchone()
            return row is not None

    def list_accepted_contacts(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT own.contact_name, own.status
                FROM contacts own
                JOIN contacts reciprocal
                    ON reciprocal.owner_username = own.contact_name
                    AND reciprocal.contact_name = own.owner_username
                WHERE own.owner_username = ?
                ORDER BY own.contact_name COLLATE NOCASE
                """,
                (username,),
            ).fetchall()
            return [{"name": row["contact_name"], "status": row["status"]} for row in rows]

    def has_direct_thread(self, username, peer_name):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM chat_messages
                WHERE owner_username = ?
                    AND scope = 'direct'
                    AND peer_name = ?
                LIMIT 1
                """,
                (username, peer_name),
            ).fetchone()
            return row is not None

    def has_pending_contact_request(self, requester, target_name):
        if not requester or not target_name:
            return False
        if self.is_accepted_contact(requester, target_name):
            return False
        if self.is_contact(requester, target_name) or self.is_contact(target_name, requester):
            return True
        return self.has_direct_thread(target_name, requester) or self.has_direct_thread(requester, target_name)

    def list_pending_contact_names(self, username):
        """Bulk equivalent of has_pending_contact_request for map projections."""
        if not username:
            return []
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                WITH candidates(name) AS (
                    SELECT contact_name FROM contacts WHERE owner_username = ?
                    UNION
                    SELECT owner_username FROM contacts WHERE contact_name = ?
                    UNION
                    SELECT peer_name FROM chat_messages
                    WHERE owner_username = ? AND scope = 'direct'
                    UNION
                    SELECT owner_username FROM chat_messages
                    WHERE peer_name = ? AND scope = 'direct'
                )
                SELECT candidates.name
                FROM candidates
                WHERE candidates.name != ?
                  AND NOT EXISTS (
                    SELECT 1 FROM contacts own
                    JOIN contacts reciprocal
                      ON reciprocal.owner_username = own.contact_name
                     AND reciprocal.contact_name = own.owner_username
                    WHERE own.owner_username = ?
                      AND own.contact_name = candidates.name
                  )
                ORDER BY candidates.name COLLATE NOCASE
                """,
                (username, username, username, username, username, username),
            ).fetchall()
        return [str(row["name"]) for row in rows if row["name"]]

    def add_contact_pair(self, username, contact_name, status="offline"):
        self.add_contact(username, contact_name, status)
        self.add_contact(contact_name, username, status)

    def list_pending_threads(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    m.peer_name,
                    MAX(m.id) AS last_id,
                    MAX(m.created_at) AS last_at
                FROM chat_messages m
                LEFT JOIN contacts c
                    ON c.owner_username = m.owner_username
                    AND c.contact_name = m.peer_name
                WHERE m.owner_username = ?
                    AND m.scope = 'direct'
                    AND c.id IS NULL
                GROUP BY m.peer_name
                ORDER BY last_id DESC
                """,
                (username,),
            ).fetchall()
            return [
                {
                    "name": row["peer_name"],
                    "status": "pending",
                    "last_at": row["last_at"],
                }
                for row in rows
                if row["peer_name"]
            ]

    def unread_counts(self, username):
        with db_connect(self.db_path) as conn:
            group_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM chat_messages
                WHERE owner_username = ?
                    AND scope = 'group'
                    AND read_at IS NULL
                """,
                (username,),
            ).fetchone()
            direct_rows = conn.execute(
                """
                SELECT peer_name, COUNT(*) AS count
                FROM chat_messages
                WHERE owner_username = ?
                    AND scope = 'direct'
                    AND read_at IS NULL
                GROUP BY peer_name
                """,
                (username,),
            ).fetchall()
            channel_rows = conn.execute(
                """
                SELECT peer_name, COUNT(*) AS count
                FROM chat_messages
                WHERE owner_username = ?
                    AND scope = 'channel'
                    AND read_at IS NULL
                GROUP BY peer_name
                """,
                (username,),
            ).fetchall()
            return {
                "group": group_row["count"] if group_row else 0,
                "direct": {
                    row["peer_name"]: row["count"]
                    for row in direct_rows
                    if row["peer_name"]
                },
                "channel": {
                    row["peer_name"]: row["count"]
                    for row in channel_rows
                    if row["peer_name"]
                },
            }

    def mark_thread_read(self, username, scope, peer_name):
        peer_name = "global" if scope == "group" else peer_name
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE chat_messages
                SET read_at = ?
                WHERE owner_username = ?
                    AND scope = ?
                    AND peer_name = ?
                    AND read_at IS NULL
                """,
                (utc_now(), username, scope, peer_name),
            )

    def touch_presence(self, username):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO mail_presence (username, last_seen_at)
                VALUES (?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at
                """,
                (username, utc_now()),
            )

    def group_active_count(self, username, seconds=10):
        threshold = (datetime.utcnow() - timedelta(seconds=seconds)).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT contact_name
                FROM contacts
                WHERE owner_username = ?
                """,
                (username,),
            ).fetchall()
            names = {username}
            names.update(row["contact_name"] for row in rows if row["contact_name"])
            active = 0
            for name in names:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM mail_presence
                    WHERE username = ? AND last_seen_at >= ?
                    """,
                    (name, threshold),
                ).fetchone()
                if row:
                    active += 1
            return active

    def add_contact(self, username, contact_name, status="offline"):
        contact_name = (contact_name or "").strip()
        if not contact_name:
            raise ValueError("Contact name is required.")
        if contact_name == username:
            raise ValueError("Nie możesz dodać samego siebie do znajomych.")

        with db_connect(self.db_path) as conn:
            user_exists = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (contact_name,),
            ).fetchone()
            if not user_exists:
                raise ValueError("Nie ma takiego użytkownika.")

            conn.execute(
                """
                INSERT INTO contacts (owner_username, contact_name, status, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(owner_username, contact_name) DO UPDATE SET
                    status = excluded.status
                """,
                (username, contact_name, status, utc_now()),
            )

    def remove_contacts_without_users(self, username):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM contacts
                WHERE owner_username = ?
                    AND contact_name NOT IN (SELECT username FROM users)
                """,
                (username,),
            )

    def remove_contact(self, username, contact_name):
        with db_connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM contacts WHERE owner_username = ? AND contact_name = ?",
                (username, contact_name),
            )
            conn.execute(
                """
                DELETE FROM chat_messages
                WHERE owner_username = ? AND scope = 'direct' AND peer_name = ?
                """,
                (username, contact_name),
            )

    def list_messages(self, username, scope="group", peer_name="global", limit=100):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, scope, peer_name, sender, subject, body, created_at
                FROM chat_messages
                WHERE owner_username = ? AND scope = ? AND peer_name = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (username, scope, peer_name, limit),
            ).fetchall()
            messages = [
                {
                    "id": row["id"],
                    "scope": row["scope"],
                    "peer_name": row["peer_name"],
                    "sender": row["sender"],
                    "subject": row["subject"],
                    "body": row["body"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
            messages.reverse()
            return messages

    def add_message(self, username, scope, peer_name, sender, body, subject="", auto_add_contact=False, channel_recipients=None):
        body = (body or "").strip()
        if not body:
            raise ValueError("Message body is required.")
        if scope not in {"group", "direct", "channel"}:
            raise ValueError("Unsupported chat scope.")

        peer_name = "global" if scope == "group" else (peer_name or "").strip()
        if scope in {"direct", "channel"} and not peer_name:
            raise ValueError("Peer name is required.")

        with db_connect(self.db_path) as conn:
            accept_pending_contact = False
            if scope == "direct" and auto_add_contact:
                pending_row = conn.execute(
                    """
                    SELECT 1
                    FROM chat_messages
                    WHERE owner_username = ?
                        AND scope = 'direct'
                        AND peer_name = ?
                        AND sender = ?
                    LIMIT 1
                    """,
                    (username, peer_name, peer_name),
                ).fetchone()
                accept_pending_contact = pending_row is not None

            conn.execute(
                """
                INSERT INTO chat_messages
                    (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (username, scope, peer_name, sender, subject, body, utc_now(), utc_now()),
            )

            if scope == "group":
                rows = conn.execute(
                    """
                    SELECT contact_name
                    FROM contacts
                    WHERE owner_username = ?
                    """,
                    (username,),
                ).fetchall()
                for row in rows:
                    recipient_name = row["contact_name"]
                    recipient = conn.execute(
                        "SELECT username FROM users WHERE username = ?",
                        (recipient_name,),
                    ).fetchone()
                    if not recipient or recipient_name == username:
                        continue
                    conn.execute(
                        """
                        INSERT INTO chat_messages
                            (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                        VALUES (?, 'group', 'global', ?, ?, ?, ?, NULL)
                        """,
                        (recipient_name, sender, subject, body, utc_now()),
                    )
                return

            if scope == "channel":
                recipients = []
                seen = {username}
                for recipient_name in channel_recipients or []:
                    recipient_name = (recipient_name or "").strip()
                    if not recipient_name or recipient_name in seen:
                        continue
                    recipient = conn.execute(
                        "SELECT username FROM users WHERE username = ?",
                        (recipient_name,),
                    ).fetchone()
                    if not recipient:
                        continue
                    seen.add(recipient_name)
                    recipients.append(recipient_name)
                for recipient_name in recipients:
                    conn.execute(
                        """
                        INSERT INTO chat_messages
                            (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                        VALUES (?, 'channel', ?, ?, ?, ?, ?, NULL)
                        """,
                        (recipient_name, peer_name, sender, subject, body, utc_now()),
                    )
                return

            if scope == "direct" and auto_add_contact:
                conn.execute(
                    """
                    INSERT INTO contacts (owner_username, contact_name, status, created_at)
                    VALUES (?, ?, 'offline', ?)
                    ON CONFLICT(owner_username, contact_name) DO NOTHING
                    """,
                    (username, peer_name, utc_now()),
                )
                if accept_pending_contact:
                    conn.execute(
                        """
                        INSERT INTO contacts (owner_username, contact_name, status, created_at)
                        VALUES (?, ?, 'offline', ?)
                        ON CONFLICT(owner_username, contact_name) DO NOTHING
                        """,
                        (peer_name, username, utc_now()),
                    )

            if scope == "direct":
                recipient = conn.execute(
                    "SELECT username FROM users WHERE username = ?",
                    (peer_name,),
                ).fetchone()
                if recipient and peer_name != username:
                    conn.execute(
                        """
                        INSERT INTO chat_messages
                            (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                        VALUES (?, 'direct', ?, ?, ?, ?, ?, NULL)
                        """,
                        (peer_name, username, sender, subject, body, utc_now()),
                    )

    def add_direct_notification(self, username, peer_name, sender, subject, body):
        body = (body or "").strip()
        if not username or not body:
            return

        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO chat_messages
                    (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                VALUES (?, 'direct', ?, ?, ?, ?, ?, NULL)
                """,
                (
                    username,
                    (peer_name or sender or "System"),
                    sender or "System",
                    subject or "",
                    body,
                    utc_now(),
                ),
            )


class GameStateDeltaBus:
    DEFAULT_RETENTION_LIMIT = 1000
    DEFAULT_QUERY_LIMIT = 100
    RECOVERY_REASONS = {"invalid_since", "outside_retention", "limit_exceeded", "missing_username"}

    def __init__(self, db_path=DB_PATH, retention_limit=DEFAULT_RETENTION_LIMIT):
        self.db_path = db_path
        self.retention_limit = max(1, int(retention_limit or self.DEFAULT_RETENTION_LIMIT))
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @classmethod
    def _default_entity_id(cls, scope, change_type, payload):
        if isinstance(payload, dict):
            for key in (
                "entity_id",
                "id",
                "app_id",
                "operation_id",
                "transaction_id",
                "player_id",
                "target_id",
                "area_id",
            ):
                value = payload.get(key)
                if value not in (None, ""):
                    return cls._clean_text(value)
        if scope:
            return cls._clean_text(scope)
        return cls._clean_text(change_type, "event")

    @classmethod
    def _event_from_row(cls, row):
        if not row:
            return None
        payload = loads_json(row["payload_json"], {})
        event = {
            "version": int(row["version"]),
            "scope": row["scope"],
            "type": row["type"],
            "entity_id": row["entity_id"],
            "dedupe_key": row["dedupe_key"],
            "payload": payload,
            "created_at": row["created_at"],
        }
        if isinstance(payload, dict):
            for key in (
                "event_id",
                "cycle_id",
                "state_version",
                "audience_scope",
                "transaction_id",
                "transaction_index",
                "transaction_size",
            ):
                if key in payload:
                    event[key] = payload.get(key)
        return event

    @staticmethod
    def _payload_size(payload):
        return len(dumps_json(payload if isinstance(payload, dict) else {}))

    @classmethod
    def _diagnostic_event_from_row(cls, row):
        event = cls._event_from_row(row)
        payload = event.get("payload") if isinstance(event, dict) else {}
        event["payload_size"] = cls._payload_size(payload)
        return event

    def _trim_retention(self, conn, username):
        conn.execute(
            """
            DELETE FROM game_state_deltas
            WHERE username = ?
                AND id NOT IN (
                    SELECT id
                    FROM game_state_deltas
                    WHERE username = ?
                    ORDER BY version DESC
                    LIMIT ?
                )
            """,
            (username, username, self.retention_limit),
        )

    def current_version(self, username):
        username = self._clean_text(username)
        if not username:
            return 0
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM game_state_deltas WHERE username = ?",
                (username,),
            ).fetchone()
            return int(row["version"] if row else 0)

    def record_change(self, username, scope, change_type, payload=None, entity_id=None, dedupe_key=None, created_at=None):
        username = self._clean_text(username)
        scope = self._clean_text(scope)
        change_type = self._clean_text(change_type)
        if not username:
            raise ValueError("Delta event requires username.")
        if not scope:
            raise ValueError("Delta event requires scope.")
        if not change_type:
            raise ValueError("Delta event requires type.")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("Delta event payload must be an object.")

        entity_id = self._clean_text(entity_id or self._default_entity_id(scope, change_type, payload))
        created_at = self._clean_text(created_at or utc_now())

        with db_connect(self.db_path) as conn:
            if dedupe_key:
                dedupe_key = self._clean_text(dedupe_key)
            else:
                next_version_row = conn.execute(
                    "SELECT COALESCE(MAX(version), 0) + 1 AS version FROM game_state_deltas WHERE username = ?",
                    (username,),
                ).fetchone()
                next_version = int(next_version_row["version"] if next_version_row else 1)
                dedupe_key = f"{scope}:{change_type}:{entity_id}:{next_version}"

            existing = conn.execute(
                """
                SELECT version, scope, type, entity_id, dedupe_key, payload_json, created_at
                FROM game_state_deltas
                WHERE username = ? AND dedupe_key = ?
                """,
                (username, dedupe_key),
            ).fetchone()
            if existing:
                return self._event_from_row(existing)

            version_row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS version FROM game_state_deltas WHERE username = ?",
                (username,),
            ).fetchone()
            version = int(version_row["version"] if version_row else 1)
            conn.execute(
                """
                INSERT INTO game_state_deltas
                    (username, version, scope, type, entity_id, dedupe_key, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    version,
                    scope,
                    change_type,
                    entity_id,
                    dedupe_key,
                    dumps_json(payload),
                    created_at,
                ),
            )
            self._trim_retention(conn, username)
            return {
                "version": version,
                "scope": scope,
                "type": change_type,
                "entity_id": entity_id,
                "dedupe_key": dedupe_key,
                "payload": copy.deepcopy(payload),
                "created_at": created_at,
            }

    def get_changes_since(self, username, since_version=0, limit=DEFAULT_QUERY_LIMIT):
        username = self._clean_text(username)
        if not username:
            return {
                "current_version": 0,
                "changes": [],
                "recovery_required": True,
                "reason": "missing_username",
            }
        try:
            since_version = int(since_version or 0)
        except (TypeError, ValueError):
            since_version = -1
        limit = max(1, min(int(limit or self.DEFAULT_QUERY_LIMIT), self.retention_limit))

        with db_connect(self.db_path) as conn:
            version_row = conn.execute(
                """
                SELECT
                    COALESCE(MIN(version), 0) AS oldest_version,
                    COALESCE(MAX(version), 0) AS current_version,
                    COUNT(*) AS count
                FROM game_state_deltas
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
            oldest_version = int(version_row["oldest_version"] if version_row else 0)
            current_version = int(version_row["current_version"] if version_row else 0)
            count = int(version_row["count"] if version_row else 0)

            if since_version < 0:
                return {
                    "current_version": current_version,
                    "changes": [],
                    "recovery_required": True,
                    "reason": "invalid_since",
                }
            if count and since_version < oldest_version - 1:
                return {
                    "current_version": current_version,
                    "changes": [],
                    "recovery_required": True,
                    "reason": "outside_retention",
                    "oldest_version": oldest_version,
                }

            total_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM game_state_deltas
                WHERE username = ? AND version > ?
                """,
                (username, since_version),
            ).fetchone()
            available_count = int(total_row["count"] if total_row else 0)
            if available_count > limit:
                return {
                    "current_version": current_version,
                    "changes": [],
                    "recovery_required": True,
                    "reason": "limit_exceeded",
                    "available_count": available_count,
                    "limit": limit,
                }

            rows = conn.execute(
                """
                SELECT version, scope, type, entity_id, dedupe_key, payload_json, created_at
                FROM game_state_deltas
                WHERE username = ? AND version > ?
                ORDER BY version ASC
                LIMIT ?
                """,
                (username, since_version, limit),
            ).fetchall()
            return {
                "current_version": current_version,
                "changes": [self._event_from_row(row) for row in rows],
                "recovery_required": False,
            }

    def diagnostics(self, username, limit=25, pollers_active_count=0, snapshot_recovery_count=0):
        username = self._clean_text(username)
        limit = max(1, min(int(limit or 25), 100))
        if not username:
            return {
                "current_version": 0,
                "events": [],
                "metrics": {
                    "delta_events_per_minute": 0,
                    "delta_payload_size": 0,
                    "recovery_count": 0,
                    "snapshot_recovery_count": int(snapshot_recovery_count or 0),
                    "pollers_active_count": int(pollers_active_count or 0),
                },
            }

        threshold = (datetime.utcnow() - timedelta(minutes=1)).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            current_row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM game_state_deltas WHERE username = ?",
                (username,),
            ).fetchone()
            current_version = int(current_row["version"] if current_row else 0)
            rows = conn.execute(
                """
                SELECT version, scope, type, entity_id, dedupe_key, payload_json, created_at
                FROM game_state_deltas
                WHERE username = ?
                ORDER BY version DESC
                LIMIT ?
                """,
                (username, limit),
            ).fetchall()
            events = [self._diagnostic_event_from_row(row) for row in rows]
            minute_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM game_state_deltas
                WHERE username = ? AND created_at >= ?
                """,
                (username, threshold),
            ).fetchone()
            payload_size = sum(event.get("payload_size", 0) for event in events)
            recovery_count = sum(
                1
                for event in events
                if event.get("type") == "state.recovery_required"
                or event.get("payload", {}).get("reason") in self.RECOVERY_REASONS
            )
            return {
                "current_version": current_version,
                "events": events,
                "metrics": {
                    "delta_events_per_minute": int(minute_row["count"] if minute_row else 0),
                    "delta_payload_size": payload_size,
                    "recovery_count": recovery_count,
                    "snapshot_recovery_count": int(snapshot_recovery_count or 0),
                    "pollers_active_count": int(pollers_active_count or 0),
                },
            }
