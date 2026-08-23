"""Read-only evidence probe for Sprint 130.10 profile/session forensics.

The tool deliberately does not import ``database`` or ``run``.  Both modules
initialise runtime stores, while this probe must be safe to execute before the
incident evidence is captured.  SQLite is opened with ``mode=ro`` and
``PRAGMA query_only=ON``; no schema bootstrap, template sync, profile mirror or
repair path is invoked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TOOL_VERSION = "130.10-evidence-v3"

CORE_TABLES = (
    "users",
    "player_apps",
    "player_tool_files",
    "player_storage",
    "wallet_balances",
    "wallet_balance_events",
    "wallet_ledger",
    "wallet_transactions",
    "profile_store_migrations",
    "player_positions",
    "player_target_runtime",
    "player_marked_targets",
    "player_marked_target_state",
    "player_operations",
    "system_messages",
    "game_state_deltas",
    "captured_targets",
    "player_areas",
    "territory_area_publications",
    "territory_target_ownership",
    "territory_target_capture_receipts",
    "territory_progression_receipts",
    "territory_rebuild_jobs",
    "ghostnetwork_territory_jobs",
    "ghostnetwork_delta_delivery_jobs",
    "ghost_cycles",
    "ghost_parts",
    "ghost_part_reservations",
    "ghost_part_events",
    "ghost_capture_effects",
    "ghost_contributions",
    "ghost_reward_ledger",
    "ghost_achievements",
)

PROFILE_CRITICAL_TYPES = {
    "username": str,
    "level": int,
    "hackcoins": int,
    "respect": int,
    "exp": str,
    "apps": list,
    "files": dict,
    "hacked": list,
    "desktop_settings": dict,
    "security": dict,
    "territory_stats": dict,
}

LKG_TABLE_CANDIDATES = (
    "profile_last_known_good",
    "profile_lkg",
    "user_profile_snapshots",
    "profile_integrity_snapshots",
)

SESSION_GENERATION_TABLE = "session_generation_lineages"
SESSION_GENERATION_REQUIRED_COLUMNS = {
    "lineage_hash",
    "generation_hash",
    "username_hash",
    "status",
    "revision",
    "schema_version",
    "created_at",
    "updated_at",
}

LKG_REQUIRED_COLUMNS = {
    "username",
    "profile_revision",
    "schema_version",
    "snapshot_json",
    "checksum",
    "source",
    "created_at",
    "validation_version",
}

PROFILE_REVISION_COLUMNS = (
    "profile_revision",
    "profile_version",
    "revision",
)

SAFE_STATUS_VALUES = {
    "", "active", "applied", "available", "cancelled", "canceled", "cleared",
    "complete", "completed", "consumed", "contained", "done", "expired",
    "failed", "hacked", "installed", "new", "online", "pending", "pooled",
    "public", "ready", "rejected", "reserved", "resolved", "running", "sent",
    "spent", "stable", "timeout", "uninstalled", "verified", "warning",
    "withdrawn",
}

SAFE_GHOST_EVENT_TYPES = {
    "ghost.part_discovered", "ghost.part_contained", "ghost.part_first_contained",
    "ghost.part_activated", "ghost.part_first_activated", "ghost.part_recovered",
    "ghost.part_lost", "ghost.part_revealed", "ghost.part_contested",
    "ghost.part_released", "ghost.reward_pending", "ghost.reward_applied",
    "ghost.reward_failed", "ghost.machine_progress_changed", "ghost.signal_sent",
}

SAFE_GHOST_REWARD_TYPES = {
    "part_discovered", "part_first_contained", "part_first_activated",
    "part_recovered", "part_stable_held", "part_defended", "defense_support",
    "attack_support", "territory_repaired", "ability_support",
    "transmission_node_held", "network_closer",
}

SAFE_GHOST_AUDIENCE_SCOPES = {"public", "clan", "owner", "player", "internal", "system"}

LKG_FORBIDDEN_SENSITIVE_KEYS = {
    "password", "salt", "cookie", "cookies", "session", "session_id",
    "session_token", "token", "access_token", "refresh_token",
}
LKG_FORBIDDEN_GEOMETRY_KEYS = {
    "geometry", "polygon", "polygons", "coordinates",
}
LKG_FORBIDDEN_TOP_LEVEL_KEYS = {
    "launch_queue", "areas", "player_areas", "territory",
}
LKG_CANONICAL_MIRROR_TOP_LEVEL_KEYS = {
    "apps", "hackcoins", "storage_capacity", "storage_used", "storage_unit",
    "storage_upgrades", "googleplex_products", "storage_soft_limit",
    "storage_over_limit", "targets",
}
LKG_SNAPSHOT_REQUIRED_TYPES = {
    "username": str,
    "level": int,
    "respect": (int, float),
    "desktop_settings": dict,
    "security": dict,
    "territory_stats": dict,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: Any) -> str:
    return hashlib.sha256(str(value if value is not None else "").encode("utf-8")).hexdigest()


def redacted_username(username: str) -> dict[str, Any]:
    clean = str(username or "").strip()
    return {
        "reference": "requested_account",
        "username_length": len(clean),
        "raw_username_included": False,
    }


def safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def timestamp_distance_seconds(left: Any, right: Any) -> float | None:
    """Return an absolute UTC distance for ISO timestamps, without guessing."""

    def parse(value: Any) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    left_dt = parse(left)
    right_dt = parse(right)
    if left_dt is None or right_dt is None:
        return None
    return abs((left_dt - right_dt).total_seconds())


def json_list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def json_dict_count(value: Any) -> int:
    return len(value) if isinstance(value, dict) else 0


def id_set_checksum(items: Iterable[Any]) -> str:
    values = sorted({str(item or "").strip() for item in items if str(item or "").strip()})
    return sha256_text(canonical_json(values))


def inventory_app_id(app: Any) -> str:
    if not isinstance(app, dict):
        return ""
    value = str(app.get("id") or app.get("app_id") or "").strip()
    if value:
        return value
    name = str(app.get("name") or app.get("label") or "app").strip().lower()
    raw = json.dumps(
        {"name": name, "runtime": app.get("runtime_file") or app.get("file_name")},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return "app_" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def inventory_tool_id(tool: Any) -> str:
    if isinstance(tool, dict):
        return str(
            tool.get("id") or tool.get("tool_id") or tool.get("file") or tool.get("name") or ""
        ).strip()
    return str(tool or "").strip()


@contextmanager
def open_read_only_database(db_path: str | os.PathLike[str]):
    """Open one consistent read transaction and assert that it changed nothing."""

    path = Path(db_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"database_not_found:{path.name}")

    uri = f"{path.as_uri()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA query_only=ON")
    before_changes = conn.total_changes
    conn.execute("BEGIN")
    try:
        yield conn, path
    finally:
        conn.rollback()
        after_changes = conn.total_changes
        conn.close()
        if after_changes != before_changes:
            raise RuntimeError("read_only_probe_changed_database")


def table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {str(row["name"]) for row in rows}


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if table not in table_names(conn):
        return set()
    return {str(row["name"]) for row in conn.execute(f'PRAGMA table_info("{table}")')}


def schema_support(
    conn: sqlite3.Connection,
    tables: set[str],
    table: str,
    required_columns: Iterable[str],
) -> dict[str, Any]:
    if table not in tables:
        return {"schema_supported": False, "table_present": False, "missing_columns": []}
    missing = sorted(set(required_columns) - table_columns(conn, table))
    return {
        "schema_supported": not missing,
        "table_present": True,
        "missing_columns": missing,
    }


def one(conn: sqlite3.Connection, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    return conn.execute(query, params).fetchone()


def grouped_counts(
    conn: sqlite3.Connection,
    tables: set[str],
    table: str,
    group_column: str,
    where_sql: str = "",
    params: tuple[Any, ...] = (),
    allowed_values: set[str] | None = SAFE_STATUS_VALUES,
) -> dict[str, int]:
    if table not in tables or group_column not in table_columns(conn, table):
        return {}
    query = f'SELECT "{group_column}" AS value, COUNT(*) AS count FROM "{table}"'
    if where_sql:
        query += f" WHERE {where_sql}"
    query += f' GROUP BY "{group_column}" ORDER BY "{group_column}"'
    result: dict[str, int] = {}
    for row in conn.execute(query, params).fetchall():
        value = str(row["value"] or "")
        key = value if allowed_values is None or value in allowed_values else "__other__"
        result[key] = result.get(key, 0) + int(row["count"] or 0)
    return result


def count_where(
    conn: sqlite3.Connection,
    tables: set[str],
    table: str,
    where_sql: str = "",
    params: tuple[Any, ...] = (),
) -> int:
    if table not in tables:
        return 0
    query = f'SELECT COUNT(*) AS count FROM "{table}"'
    if where_sql:
        query += f" WHERE {where_sql}"
    row = one(conn, query, params)
    return int(row["count"] or 0) if row else 0


def finding(code: str, severity: str, scope: str, **details: Any) -> dict[str, Any]:
    result = {"code": code, "severity": severity, "scope": scope}
    result.update(details)
    return result


def classify_profile(row_username: str, raw_profile: Any) -> tuple[str, dict[str, Any] | None, list[str]]:
    if raw_profile is None:
        return "missing", None, ["profile_json_missing"]
    try:
        profile = json.loads(raw_profile)
    except (json.JSONDecodeError, TypeError, ValueError):
        return "invalid_json", None, ["profile_json_decode_failed"]
    if not isinstance(profile, dict):
        return "invalid_schema", None, ["profile_root_not_object"]

    invalid: list[str] = []
    missing: list[str] = []
    for key, expected_type in PROFILE_CRITICAL_TYPES.items():
        if key not in profile:
            missing.append(f"missing:{key}")
            continue
        value = profile.get(key)
        if expected_type is int:
            if isinstance(value, bool) or not isinstance(value, int):
                invalid.append(f"invalid_type:{key}")
        elif not isinstance(value, expected_type):
            invalid.append(f"invalid_type:{key}")

    if profile.get("username") != row_username:
        invalid.append("identity_mismatch")
    if isinstance(profile.get("level"), int) and not isinstance(profile.get("level"), bool):
        if profile["level"] < 1:
            invalid.append("invalid_range:level")
    for key in ("hackcoins", "respect"):
        value = profile.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value < 0:
            invalid.append(f"invalid_range:{key}")
    files = profile.get("files")
    if isinstance(files, dict) and "tools" in files and not isinstance(files.get("tools"), list):
        invalid.append("invalid_type:files.tools")

    if invalid:
        return "invalid_schema", profile, invalid + missing
    if missing:
        return "recovery_required", profile, missing
    return "valid", profile, []


def classify_lkg_snapshot(
    row_username: str,
    raw_snapshot: Any,
) -> tuple[str, dict[str, Any] | None, list[str]]:
    """Validate the deliberately reduced, non-canonical LKG payload shape."""

    try:
        snapshot = json.loads(raw_snapshot)
    except (json.JSONDecodeError, TypeError, ValueError):
        return "invalid_json", None, ["snapshot_json_decode_failed"]
    if not isinstance(snapshot, dict):
        return "invalid_schema", None, ["snapshot_root_not_object"]

    invalid: list[str] = []
    missing: list[str] = []
    for key, expected_type in LKG_SNAPSHOT_REQUIRED_TYPES.items():
        if key not in snapshot:
            missing.append(f"missing:{key}")
            continue
        value = snapshot.get(key)
        if isinstance(value, bool) or not isinstance(value, expected_type):
            invalid.append(f"invalid_type:{key}")

    if snapshot.get("username") != row_username:
        invalid.append("identity_mismatch")
    level = snapshot.get("level")
    if isinstance(level, int) and not isinstance(level, bool) and level < 1:
        invalid.append("invalid_range:level")
    respect = snapshot.get("respect")
    if (
        isinstance(respect, (int, float))
        and not isinstance(respect, bool)
        and (not math.isfinite(float(respect)) or respect < 0)
    ):
        invalid.append("invalid_range:respect")
    exp = snapshot.get("exp")
    if exp is None:
        missing.append("missing:exp")
    elif isinstance(exp, bool) or not (
        (isinstance(exp, str) and bool(exp.strip()))
        or (
            isinstance(exp, (int, float))
            and math.isfinite(float(exp))
        )
    ):
        invalid.append("invalid_type:exp")

    files = snapshot.get("files")
    if files is not None and not isinstance(files, dict):
        invalid.append("invalid_type:files")
    if invalid:
        return "invalid_schema", snapshot, sorted(set(invalid + missing))
    if missing:
        return "recovery_required", snapshot, sorted(set(missing))
    return "valid", snapshot, []


def schema_capabilities(conn: sqlite3.Connection, tables: set[str]) -> dict[str, Any]:
    user_columns = table_columns(conn, "users")
    revision_columns = sorted(user_columns.intersection(PROFILE_REVISION_COLUMNS))
    lkg_tables = sorted(set(LKG_TABLE_CANDIDATES).intersection(tables))
    lkg_contracts = {
        table: schema_support(conn, tables, table, LKG_REQUIRED_COLUMNS)
        for table in lkg_tables
    }
    supported_lkg_tables = sorted(
        table
        for table, contract in lkg_contracts.items()
        if contract["schema_supported"]
    )
    session_generation_contract = schema_support(
        conn,
        tables,
        SESSION_GENERATION_TABLE,
        SESSION_GENERATION_REQUIRED_COLUMNS,
    )
    legacy_session_generation_present = (
        "session_generation" in user_columns or "user_sessions" in tables
    )
    return {
        "users_columns_checksum": sha256_text(canonical_json(sorted(user_columns))),
        "profile_revision_columns": revision_columns,
        "profile_revision_present": bool(revision_columns),
        # A similarly named table is only a candidate.  Runtime guard presence
        # requires the documented per-user payload/revision/checksum contract;
        # record validity is evaluated separately by ``lkg_summary``.
        "lkg_table_candidates": lkg_tables,
        "lkg_tables": lkg_tables,
        "lkg_contracts": lkg_contracts,
        "lkg_contract_tables": supported_lkg_tables,
        "lkg_schema_present": bool(supported_lkg_tables),
        "lkg_present": bool(supported_lkg_tables),
        "session_generation_table": SESSION_GENERATION_TABLE,
        "session_generation_contract": session_generation_contract,
        "session_generation_legacy_schema_present": legacy_session_generation_present,
        "session_generation_schema_present": bool(
            session_generation_contract["schema_supported"]
            or legacy_session_generation_present
        ),
    }


def runtime_guard_status(
    capabilities: dict[str, Any],
    *,
    lkg_record_validated: bool | None = None,
) -> str:
    """Describe guard availability without treating planned guards as incident proof."""

    guards = (
        bool(capabilities.get("profile_revision_present")),
        (
            bool(capabilities.get("lkg_present"))
            if lkg_record_validated is None
            else bool(lkg_record_validated)
        ),
        bool(capabilities.get("session_generation_schema_present")),
    )
    if all(guards):
        return "present"
    if any(guards):
        return "partial"
    return "missing"


def database_metadata(conn: sqlite3.Connection, path: Path, tables: set[str]) -> dict[str, Any]:
    schema_rows = conn.execute(
        """
        SELECT type, name, tbl_name, COALESCE(sql, '') AS sql
        FROM sqlite_master
        WHERE name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    ).fetchall()
    schema_projection = [dict(row) for row in schema_rows]
    stat = path.stat()
    query_only = int(one(conn, "PRAGMA query_only")[0])
    journal_mode = str(one(conn, "PRAGMA journal_mode")[0])
    sidecars = {}
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(path) + suffix)
        sidecars[suffix.removeprefix("-")] = {
            "present": sidecar.is_file(),
            "size_bytes": int(sidecar.stat().st_size) if sidecar.is_file() else 0,
            "mtime_utc": (
                datetime.fromtimestamp(sidecar.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")
                if sidecar.is_file() else None
            ),
        }
    live_wal_present = bool(sidecars["wal"]["present"])
    return {
        "database_name": path.name,
        "database_size_bytes": int(stat.st_size),
        "database_mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
        "sqlite_version": sqlite3.sqlite_version,
        "user_version": int(one(conn, "PRAGMA user_version")[0]),
        "data_version": int(one(conn, "PRAGMA data_version")[0]),
        "journal_mode": journal_mode,
        "query_only": bool(query_only),
        "schema_checksum_sha256": sha256_text(canonical_json(schema_projection)),
        "table_count": len(tables),
        "sidecars": sidecars,
        # The report is a logical SQLite read-transaction snapshot.  In WAL
        # mode SQLite resolves committed pages from the main file and WAL for
        # the reader, but this tool does not create/copy a physical DB bundle.
        # A main-file-only copy made by somebody else while WAL is live would
        # therefore not be a self-contained forensic snapshot.
        "read_transaction_snapshot_scope": "sqlite_committed_state_at_first_read",
        "logical_reader_resolves_committed_wal": journal_mode.lower() == "wal",
        "live_wal_sidecar_present_at_metadata_check": live_wal_present,
        "live_database_may_advance_after_snapshot": True,
        "physical_database_bundle_created": False,
        "physical_copy_assessment": (
            "main_database_file_alone_not_sufficient_while_wal_present"
            if live_wal_present
            else "not_assessed"
        ),
        # Compatibility field: this means reader visibility, not that WAL/SHM
        # files were copied into the evidence archive.
        "snapshot_includes_live_wal": bool(
            journal_mode.lower() == "wal" and live_wal_present
        ),
        "snapshot_includes_live_wal_is_logical_not_physical": True,
        "filesystem_bitwise_immutability_claimed": False,
    }


def _forbidden_lkg_key_counts(value: Any, *, top_level: bool = True) -> dict[str, int]:
    counts = {
        "sensitive": 0,
        "geometry": 0,
        "top_level_runtime": 0,
        "canonical_mirror": 0,
    }

    def walk(item: Any, is_top_level: bool = False) -> None:
        if isinstance(item, dict):
            for raw_key, child in item.items():
                key = str(raw_key).lower()
                if key in LKG_FORBIDDEN_SENSITIVE_KEYS:
                    counts["sensitive"] += 1
                if key in LKG_FORBIDDEN_GEOMETRY_KEYS:
                    counts["geometry"] += 1
                if is_top_level and key in LKG_FORBIDDEN_TOP_LEVEL_KEYS:
                    counts["top_level_runtime"] += 1
                if is_top_level and key in LKG_CANONICAL_MIRROR_TOP_LEVEL_KEYS:
                    counts["canonical_mirror"] += 1
                if is_top_level and key == "files" and isinstance(child, dict) and "tools" in child:
                    counts["canonical_mirror"] += 1
                walk(child, False)
        elif isinstance(item, list):
            for child in item:
                walk(child, False)

    walk(value, top_level)
    return counts


def lkg_summary(
    conn: sqlite3.Connection,
    tables: set[str],
    username: str,
    current_profile: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate an exact user's LKG contract without returning its payload."""

    contracts = {
        table: schema_support(conn, tables, table, LKG_REQUIRED_COLUMNS)
        for table in LKG_TABLE_CANDIDATES
        if table in tables
    }
    supported_tables = [
        table
        for table in LKG_TABLE_CANDIDATES
        if contracts.get(table, {}).get("schema_supported")
    ]
    result: dict[str, Any] = {
        "table_candidates": contracts,
        "contract_table": supported_tables[0] if supported_tables else None,
        "record_status": "unavailable" if not contracts else "schema_unsupported",
        "record_present": False,
        "record_validated": False,
        "payload_included": False,
        "checksum_included": False,
    }
    findings: list[dict[str, Any]] = []
    if not supported_tables:
        code = "profile_lkg_missing" if not contracts else "profile_lkg_schema_unsupported"
        findings.append(finding(code, "warning", "runtime_guard"))
        return result, findings

    table = supported_tables[0]
    row = one(
        conn,
        f'''SELECT username, profile_revision, schema_version, snapshot_json,
                   checksum, source, created_at, validation_version
            FROM "{table}" WHERE username = ?''',
        (username,),
    )
    if not row:
        result["record_status"] = "missing"
        findings.append(finding("profile_lkg_record_missing", "warning", "runtime_guard"))
        return result, findings

    result["record_present"] = True
    issues: list[str] = []
    snapshot = None
    raw_snapshot = row["snapshot_json"]
    try:
        snapshot = json.loads(raw_snapshot)
    except (TypeError, ValueError, json.JSONDecodeError):
        issues.append("snapshot_json_decode_failed")
    if not isinstance(snapshot, dict):
        if snapshot is not None:
            issues.append("snapshot_root_not_object")
        snapshot = None

    revision = safe_int(row["profile_revision"])
    schema_version = safe_int(row["schema_version"])
    validation_version = safe_int(row["validation_version"])
    if revision is None or revision < 1:
        issues.append("profile_revision_invalid")
    if schema_version is None or schema_version < 1:
        issues.append("schema_version_invalid")
    if validation_version is None or validation_version < 1:
        issues.append("validation_version_invalid")
    if not str(row["source"] or "").strip():
        issues.append("source_missing")
    if not str(row["created_at"] or "").strip():
        issues.append("created_at_missing")
    elif timestamp_distance_seconds(row["created_at"], row["created_at"]) is None:
        issues.append("created_at_invalid")

    checksum_matches = False
    canonical_serialization = False
    forbidden_counts = {
        "sensitive": 0,
        "geometry": 0,
        "top_level_runtime": 0,
        "canonical_mirror": 0,
    }
    snapshot_state = "unavailable"
    if snapshot is not None:
        canonical_snapshot = canonical_json(snapshot)
        checksum_matches = bool(
            str(row["checksum"] or "")
            and str(row["checksum"]) == sha256_text(canonical_snapshot)
        )
        canonical_serialization = str(raw_snapshot) == canonical_snapshot
        snapshot_state, _profile, snapshot_issues = classify_lkg_snapshot(
            username, raw_snapshot
        )
        if snapshot_state != "valid":
            issues.extend(f"snapshot:{item}" for item in snapshot_issues)
        forbidden_counts = _forbidden_lkg_key_counts(snapshot)
        if forbidden_counts["sensitive"]:
            issues.append("snapshot_contains_sensitive_keys")
        if forbidden_counts["geometry"] or forbidden_counts["top_level_runtime"]:
            issues.append("snapshot_contains_runtime_or_geometry_keys")
        if forbidden_counts["canonical_mirror"]:
            issues.append("snapshot_contains_canonical_mirror_keys")
    if not checksum_matches:
        issues.append("checksum_mismatch")

    user_columns = table_columns(conn, "users")
    current_revision = None
    current_schema_version = None
    current_checksum_matches = None
    metadata_columns = {
        "profile_revision", "profile_schema_version", "profile_checksum",
    }
    if metadata_columns.issubset(user_columns):
        current_row = one(
            conn,
            """
            SELECT profile_revision, profile_schema_version, profile_checksum
            FROM users WHERE username = ?
            """,
            (username,),
        )
        if current_row:
            current_revision = safe_int(current_row["profile_revision"])
            current_schema_version = safe_int(current_row["profile_schema_version"])
            if current_profile is not None:
                current_checksum_matches = (
                    str(current_row["profile_checksum"] or "")
                    == sha256_text(canonical_json(current_profile))
                )
                if not current_checksum_matches:
                    issues.append("current_profile_checksum_mismatch")
            if revision is not None and current_revision is not None and revision > current_revision:
                issues.append("lkg_revision_ahead_of_current")
            if (
                schema_version is not None
                and current_schema_version is not None
                and current_schema_version > 0
                and schema_version != current_schema_version
            ):
                issues.append("lkg_schema_version_mismatch")

    issues = sorted(set(issues))
    valid = not issues
    result.update({
        "record_status": "valid" if valid else "invalid",
        "record_validated": valid,
        "profile_revision": revision,
        "schema_version": schema_version,
        "validation_version": validation_version,
        "created_at": row["created_at"],
        "snapshot_profile_state": snapshot_state,
        "checksum_matches": checksum_matches,
        "canonical_serialization": canonical_serialization,
        "forbidden_key_counts": forbidden_counts,
        "current_profile_revision": current_revision,
        "current_profile_schema_version": current_schema_version,
        "current_profile_checksum_matches": current_checksum_matches,
        "revision_not_ahead_of_current": (
            None
            if revision is None or current_revision is None
            else revision <= current_revision
        ),
        "issues": issues,
    })
    if not valid:
        findings.append(finding(
            "profile_lkg_record_invalid",
            "high",
            "profile",
            issues=issues,
        ))
    return result, findings


def profile_summary(row: sqlite3.Row | None) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any] | None]:
    if not row:
        return (
            {"state": "missing", "issues": ["user_not_found"]},
            [finding("user_not_found", "blocker", "profile")],
            None,
        )

    raw = row["profile_json"]
    state, profile, issues = classify_profile(str(row["username"]), raw)
    result: dict[str, Any] = {
        "state": state,
        "issues": issues,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "profile_json_bytes": len(str(raw or "").encode("utf-8")),
        "profile_checksum_sha256": sha256_text(raw),
        "credential_columns": {
            "password_present": bool(row["password"]),
            "salt_present": bool(row["salt"]),
        },
    }
    findings: list[dict[str, Any]] = []
    if state != "valid":
        findings.append(finding(f"profile_{state}", "blocker", "profile", issues=issues))
    if profile is None:
        return result, findings, None

    profile_password = profile.get("password")
    profile_salt = profile.get("salt")
    result["credential_projection"] = {
        "password_present": bool(profile_password),
        "salt_present": bool(profile_salt),
        "password_matches_column_if_present": (
            profile_password == row["password"] if profile_password else None
        ),
        "salt_matches_column_if_present": profile_salt == row["salt"] if profile_salt else None,
    }
    shape = {key: type(value).__name__ for key, value in sorted(profile.items())}
    files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
    result.update({
        "profile_shape_checksum_sha256": sha256_text(canonical_json(shape)),
        "top_level_key_count": len(profile),
        "progression": {
            "level": safe_int(profile.get("level")),
            "respect": safe_int(profile.get("respect")),
            "hackcoins": safe_int(profile.get("hackcoins")),
            "exp": profile.get("exp") if isinstance(profile.get("exp"), str) else None,
        },
        "profile_scope_counts": {
            "apps": json_list_count(profile.get("apps")),
            "tools": json_list_count(files.get("tools")),
            "hacked": json_list_count(profile.get("hacked")),
            "operations": json_list_count(profile.get("operations")),
            "launch_queue": json_list_count(profile.get("launch_queue")),
            "googleplex_products": json_list_count(profile.get("googleplex_products")),
            "product_purchases": json_list_count(profile.get("product_purchases")),
            "market_history": json_list_count(profile.get("market_history")),
            "ghostnetwork_reward_history": json_list_count(profile.get("ghostnetwork_reward_history")),
        },
        "starter_signature": (
            safe_int(profile.get("level")) == 1
            and safe_int(profile.get("respect")) == 0
            and safe_int(profile.get("hackcoins")) == 1000
        ),
    })
    return result, findings, profile


def wallet_summary(
    conn: sqlite3.Connection,
    tables: set[str],
    username: str,
    profile: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result: dict[str, Any] = {
        "source_authority": "ambiguous_hybrid",
        "schema": {},
        "profile_balance": safe_int((profile or {}).get("hackcoins")),
        "balance_store": None,
        "ledger": {"event_count": 0},
        "balance_events": {"event_count": 0},
        "legacy_transactions": {"outgoing_count": 0, "incoming_count": 0},
    }
    findings: list[dict[str, Any]] = []

    balance_support = schema_support(
        conn, tables, "wallet_balances", {"username", "balance", "version", "updated_at"}
    )
    ledger_support = schema_support(
        conn, tables, "wallet_ledger",
        {"ledger_id", "username", "amount_delta", "balance_after", "dedupe_key", "created_at"},
    )
    event_support = schema_support(
        conn, tables, "wallet_balance_events",
        {"username", "amount_delta", "balance", "created_at"},
    )
    transaction_support = schema_support(
        conn, tables, "wallet_transactions",
        {"from_username", "to_username", "amount", "created_at"},
    )
    result["schema"] = {
        "balance_store": balance_support,
        "ledger": ledger_support,
        "balance_events": event_support,
        "legacy_transactions": transaction_support,
    }

    if balance_support["schema_supported"]:
        row = one(
            conn,
            "SELECT balance, version, updated_at FROM wallet_balances WHERE username = ?",
            (username,),
        )
        if row:
            result["balance_store"] = {
                "balance": int(row["balance"] or 0),
                "version": int(row["version"] or 0),
                "updated_at": row["updated_at"],
            }

    if ledger_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT COUNT(*) AS event_count,
                   COALESCE(SUM(amount_delta), 0) AS delta_sum,
                   MAX(created_at) AS latest_created_at
            FROM wallet_ledger WHERE username = ?
            """,
            (username,),
        )
        latest = one(
            conn,
            """
            SELECT balance_after, created_at
            FROM wallet_ledger WHERE username = ?
            ORDER BY created_at DESC, ledger_id DESC LIMIT 1
            """,
            (username,),
        )
        duplicate_row = one(
            conn,
            """
            SELECT COUNT(*) AS count FROM (
                SELECT dedupe_key FROM wallet_ledger
                WHERE username = ? AND dedupe_key != ''
                GROUP BY dedupe_key HAVING COUNT(*) > 1
            )
            """,
            (username,),
        )
        tail_row = one(
            conn,
            """
            SELECT COUNT(*) AS count FROM wallet_ledger
            WHERE username = ? AND created_at = (
                SELECT MAX(created_at) FROM wallet_ledger WHERE username = ?
            )
            """,
            (username, username),
        )
        result["ledger"] = {
            "event_count": int(row["event_count"] or 0),
            "delta_sum": int(row["delta_sum"] or 0),
            "latest_balance_after": int(latest["balance_after"] or 0) if latest else None,
            "latest_created_at": latest["created_at"] if latest else None,
            "latest_timestamp_event_count": int(tail_row["count"] or 0),
            "tail_order_ambiguous": int(tail_row["count"] or 0) > 1,
            "duplicate_dedupe_keys": int(duplicate_row["count"] or 0),
        }

    if event_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT COUNT(*) AS event_count, COALESCE(SUM(amount_delta), 0) AS delta_sum,
                   MAX(created_at) AS latest_created_at
            FROM wallet_balance_events WHERE username = ?
            """,
            (username,),
        )
        result["balance_events"] = {
            "event_count": int(row["event_count"] or 0),
            "delta_sum": int(row["delta_sum"] or 0),
            "latest_created_at": row["latest_created_at"],
        }

    if transaction_support["schema_supported"]:
        outgoing = one(
            conn,
            "SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total, MAX(created_at) AS latest_created_at FROM wallet_transactions WHERE from_username = ?",
            (username,),
        )
        incoming = one(
            conn,
            "SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total, MAX(created_at) AS latest_created_at FROM wallet_transactions WHERE to_username = ?",
            (username,),
        )
        result["legacy_transactions"] = {
            "outgoing_count": int(outgoing["count"] or 0),
            "outgoing_total": int(outgoing["total"] or 0),
            "outgoing_latest_created_at": outgoing["latest_created_at"],
            "incoming_count": int(incoming["count"] or 0),
            "incoming_total": int(incoming["total"] or 0),
            "incoming_latest_created_at": incoming["latest_created_at"],
        }

    profile_balance = result["profile_balance"]
    store_balance = (result["balance_store"] or {}).get("balance")
    ledger_latest = result["ledger"].get("latest_balance_after")
    ledger_sum = result["ledger"].get("delta_sum")
    if store_balance is None and profile_balance is not None:
        findings.append(finding(
            "wallet_store_missing",
            "warning",
            "wallet",
            authority="ambiguous_hybrid",
        ))
    if store_balance is not None and profile_balance is not None and store_balance != profile_balance:
        findings.append(finding(
            "wallet_profile_store_mismatch",
            "warning",
            "wallet",
            authority="ambiguous_hybrid",
            profile_balance=profile_balance,
            store_balance=store_balance,
        ))
    if (
        store_balance is not None
        and result["ledger"].get("event_count", 0) > 0
        and ledger_sum is not None
        and store_balance != ledger_sum
    ):
        findings.append(finding(
            "wallet_store_ledger_sum_mismatch",
            "high",
            "wallet",
            store_balance=store_balance,
            ledger_delta_sum=ledger_sum,
        ))
    if (
        store_balance is not None
        and ledger_latest is not None
        and store_balance != ledger_latest
    ):
        findings.append(finding(
            "wallet_store_ledger_tail_mismatch",
            "warning",
            "wallet",
            tail_order_ambiguous=bool(result["ledger"].get("tail_order_ambiguous")),
        ))
    if result["ledger"].get("duplicate_dedupe_keys"):
        findings.append(finding("wallet_ledger_duplicate_dedupe", "high", "wallet"))
    result["scope_status"] = (
        "unknown"
        if not all(item["schema_supported"] for item in result["schema"].values())
        else "divergent"
        if any(item["severity"] in {"high", "blocker"} for item in findings)
        else "hybrid_consistent" if not findings else "hybrid_with_findings"
    )
    return result, findings


def inventory_summary(
    conn: sqlite3.Connection,
    tables: set[str],
    username: str,
    profile: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile = profile or {}
    profile_apps = profile.get("apps") if isinstance(profile.get("apps"), list) else []
    files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
    profile_tools = files.get("tools") if isinstance(files.get("tools"), list) else []
    profile_app_ids = {inventory_app_id(item) for item in profile_apps}
    profile_tool_ids = {inventory_tool_id(item) for item in profile_tools}
    profile_app_ids.discard("")
    profile_tool_ids.discard("")

    app_support = schema_support(
        conn, tables, "player_apps", {"username", "app_id", "status", "updated_at"}
    )
    tool_support = schema_support(
        conn, tables, "player_tool_files", {"username", "tool_id", "updated_at"}
    )
    storage_support = schema_support(
        conn, tables, "player_storage",
        {"username", "capacity", "used", "unit", "version", "updated_at"},
    )
    app_rows = (
        conn.execute(
            "SELECT app_id, status, updated_at FROM player_apps WHERE username = ?",
            (username,),
        ).fetchall()
        if app_support["schema_supported"] else []
    )
    tool_rows = (
        conn.execute(
            "SELECT tool_id, updated_at FROM player_tool_files WHERE username = ?",
            (username,),
        ).fetchall()
        if tool_support["schema_supported"] else []
    )
    active_app_rows = [row for row in app_rows if row["status"] != "uninstalled"]
    store_app_ids = {str(row["app_id"] or "") for row in active_app_rows}
    store_tool_ids = {str(row["tool_id"] or "") for row in tool_rows}
    storage = None
    if storage_support["schema_supported"]:
        row = one(
            conn,
            "SELECT capacity, used, unit, version, updated_at FROM player_storage WHERE username = ?",
            (username,),
        )
        if row:
            storage = {
                "capacity": int(row["capacity"] or 0),
                "used": int(row["used"] or 0),
                "unit": row["unit"],
                "version": int(row["version"] or 0),
                "updated_at": row["updated_at"],
            }

    migration_statuses = {}
    migration_completed_at = None
    backup_present = False
    migration_support = schema_support(
        conn, tables, "profile_store_migrations",
        {"username", "status", "completed_at", "backup_json"},
    )
    if migration_support["schema_supported"]:
        migration_statuses = grouped_counts(
            conn, tables, "profile_store_migrations", "status", "username = ?", (username,)
        )
        row = one(
            conn,
            """
            SELECT MAX(completed_at) AS completed_at,
                   COALESCE(SUM(CASE WHEN backup_json IS NOT NULL AND backup_json != '' THEN 1 ELSE 0 END), 0) AS backups
            FROM profile_store_migrations WHERE username = ?
            """,
            (username,),
        )
        migration_completed_at = row["completed_at"]
        backup_present = int(row["backups"] or 0) > 0
    migrated = any(migration_statuses.get(value, 0) for value in ("verified", "completed"))
    migration_state = "verified" if migrated else ("known_not_verified" if migration_statuses else "unknown")

    result = {
        "profile": {
            "apps_count": len(profile_apps),
            "tools_count": len(profile_tools),
            "app_ids_checksum_sha256": id_set_checksum(profile_app_ids),
            "tool_ids_checksum_sha256": id_set_checksum(profile_tool_ids),
            "storage_capacity": safe_int(profile.get("storage_capacity")),
            "storage_used": safe_int(profile.get("storage_used")),
            "googleplex_products_count": json_list_count(profile.get("googleplex_products")),
            "product_purchases_count": json_list_count(profile.get("product_purchases")),
        },
        "canonical_store": {
            "schema": {
                "apps": app_support,
                "tools": tool_support,
                "storage": storage_support,
            },
            "apps_count": len(store_app_ids),
            "installed_apps_count": sum(1 for row in active_app_rows if row["status"] == "installed"),
            "uninstalled_apps_count": sum(1 for row in app_rows if row["status"] == "uninstalled"),
            "tools_count": len(store_tool_ids),
            "app_ids_checksum_sha256": id_set_checksum(store_app_ids),
            "tool_ids_checksum_sha256": id_set_checksum(store_tool_ids),
            "storage": storage,
            "apps_latest_updated_at": max((row["updated_at"] for row in app_rows), default=None),
            "tools_latest_updated_at": max((row["updated_at"] for row in tool_rows), default=None),
        },
        "migration_evidence": {
            "state": migration_state,
            "statuses": migration_statuses,
            "latest_completed_at": migration_completed_at,
            "backup_candidate_present": backup_present,
            "backup_candidate_is_lkg": False,
        },
        "differences": {
            "profile_only_apps": len(profile_app_ids - store_app_ids),
            "store_only_apps": len(store_app_ids - profile_app_ids),
            "profile_only_tools": len(profile_tool_ids - store_tool_ids),
            "store_only_tools": len(store_tool_ids - profile_tool_ids),
        },
    }
    findings: list[dict[str, Any]] = []
    if any(result["differences"].values()):
        findings.append(finding(
            "inventory_profile_store_mismatch",
            "warning" if migrated else "info",
            "inventory",
            authority="store_after_verified_migration" if migrated else "ambiguous_unmigrated",
            **result["differences"],
        ))
    if migrated and storage and (
        storage["capacity"] != safe_int(profile.get("storage_capacity"))
        or storage["used"] != safe_int(profile.get("storage_used"))
    ):
        findings.append(finding("storage_profile_store_mismatch", "warning", "inventory"))
    result["scope_status"] = (
        "unknown"
        if not all(
            item["schema_supported"]
            for item in result["canonical_store"]["schema"].values()
        )
        else "with_findings" if findings else "consistent"
    )
    return result, findings


def googleplex_summary(
    conn: sqlite3.Connection,
    tables: set[str],
    username: str,
    profile: dict[str, Any] | None,
) -> dict[str, Any]:
    profile = profile or {}
    products = profile.get("googleplex_products") if isinstance(profile.get("googleplex_products"), list) else []
    purchases = profile.get("product_purchases") if isinstance(profile.get("product_purchases"), list) else []
    timestamps = []
    for item in purchases:
        if not isinstance(item, dict):
            continue
        timestamp = item.get("purchased_at") or item.get("created_at")
        if isinstance(timestamp, str) and timestamp:
            timestamps.append(timestamp)
    result: dict[str, Any] = {
        "profile_products_count": len(products),
        "profile_purchases_count": len(purchases),
        "profile_purchase_earliest_at": min(timestamps, default=None),
        "profile_purchase_latest_at": max(timestamps, default=None),
        "atomic_purchase_receipt_present": False,
        "evidence_status": "partial",
        "sources": {},
    }
    ledger_support = schema_support(
        conn, tables, "wallet_ledger", {"username", "event_type", "source", "created_at"}
    )
    if ledger_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT COUNT(*) AS count, MIN(created_at) AS earliest_at, MAX(created_at) AS latest_at
            FROM wallet_ledger
            WHERE username = ? AND (
                lower(event_type) LIKE 'googleplex%' OR lower(source) LIKE 'googleplex%'
            )
            """,
            (username,),
        )
        result["sources"]["wallet_ledger"] = dict(row)
    event_support = schema_support(
        conn, tables, "wallet_balance_events", {"username", "reason", "created_at"}
    )
    if event_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT COUNT(*) AS count, MIN(created_at) AS earliest_at, MAX(created_at) AS latest_at
            FROM wallet_balance_events
            WHERE username = ? AND lower(reason) LIKE 'googleplex%'
            """,
            (username,),
        )
        result["sources"]["wallet_balance_events"] = dict(row)
    message_support = schema_support(
        conn, tables, "system_messages", {"username", "source", "created_at"}
    )
    if message_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT COUNT(*) AS count, MIN(created_at) AS earliest_at, MAX(created_at) AS latest_at
            FROM system_messages
            WHERE username = ? AND source IN ('googleplex_product', 'googleplex_install')
            """,
            (username,),
        )
        result["sources"]["system_messages"] = dict(row)
    delta_support = schema_support(
        conn, tables, "game_state_deltas", {"username", "type", "dedupe_key", "created_at"}
    )
    if delta_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT COUNT(*) AS count, MIN(created_at) AS earliest_at, MAX(created_at) AS latest_at
            FROM game_state_deltas
            WHERE username = ? AND (
                lower(type) LIKE '%googleplex%' OR lower(dedupe_key) LIKE '%googleplex%'
            )
            """,
            (username,),
        )
        result["sources"]["state_deltas"] = dict(row)
    result["source_schema"] = {
        "wallet_ledger": ledger_support,
        "wallet_balance_events": event_support,
        "system_messages": message_support,
        "state_deltas": delta_support,
    }
    return result


def runtime_scope_summary(conn: sqlite3.Connection, tables: set[str], username: str) -> dict[str, Any]:
    target_support = schema_support(
        conn, tables, "player_target_runtime", {"username", "target_key", "status", "version", "updated_at"}
    )
    position_support = schema_support(
        conn, tables, "player_positions", {"username", "source", "version", "updated_at"}
    )
    operations_support = schema_support(
        conn, tables, "player_operations", {"username", "status", "updated_at"}
    )
    messages_support = schema_support(
        conn, tables, "system_messages", {"username", "status", "created_at"}
    )
    deltas_support = schema_support(
        conn, tables, "game_state_deltas", {"username", "version", "created_at"}
    )
    migrations_support = schema_support(
        conn, tables, "profile_store_migrations", {"username", "status"}
    )
    result: dict[str, Any] = {
        "schema": {
            "target": target_support,
            "position": position_support,
            "operations": operations_support,
            "system_messages": messages_support,
            "state_deltas": deltas_support,
            "migrations": migrations_support,
        }
    }
    if target_support["schema_supported"]:
        row = one(
            conn,
            "SELECT target_key, status, version, updated_at FROM player_target_runtime WHERE username = ?",
            (username,),
        )
        result["target_runtime"] = {
            "present": bool(row),
            "target_key_sha256": sha256_text(row["target_key"]) if row and row["target_key"] else None,
            "status": row["status"] if row else None,
            "version": int(row["version"] or 0) if row else None,
            "updated_at": row["updated_at"] if row else None,
        }
    if position_support["schema_supported"]:
        row = one(
            conn,
            "SELECT source, version, updated_at FROM player_positions WHERE username = ?",
            (username,),
        )
        result["position"] = {
            "present": bool(row),
            "source": row["source"] if row else None,
            "version": int(row["version"] or 0) if row else None,
            "updated_at": row["updated_at"] if row else None,
            "coordinates_redacted": True,
        }
    result["operations_by_status"] = (
        grouped_counts(conn, tables, "player_operations", "status", "username = ?", (username,))
        if operations_support["schema_supported"] else {}
    )
    result["system_messages_by_status"] = (
        grouped_counts(conn, tables, "system_messages", "status", "username = ?", (username,))
        if messages_support["schema_supported"] else {}
    )
    if deltas_support["schema_supported"]:
        row = one(
            conn,
            "SELECT COUNT(*) AS count, MAX(version) AS max_version, MAX(created_at) AS latest_created_at FROM game_state_deltas WHERE username = ?",
            (username,),
        )
        result["state_deltas"] = {
            "count": int(row["count"] or 0),
            "max_version": int(row["max_version"] or 0),
            "latest_created_at": row["latest_created_at"],
        }
    if migrations_support["schema_supported"]:
        result["profile_store_migrations_by_status"] = grouped_counts(
            conn, tables, "profile_store_migrations", "status", "username = ?", (username,)
        )
    return result


def territory_summary(
    conn: sqlite3.Connection, tables: set[str], username: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    captured_support = schema_support(
        conn, tables, "captured_targets",
        {"owner_username", "stationary", "generated", "updated_at"},
    )
    areas_support = schema_support(
        conn, tables, "player_areas", {"owner_username", "status", "created_at", "updated_at"}
    )
    ownership_support = schema_support(
        conn, tables, "territory_target_ownership",
        {"owner_username", "ownership_version", "updated_at"},
    )
    publication_support = schema_support(
        conn, tables, "territory_area_publications",
        {"owner_username", "publication_version", "geometry_hash", "updated_at"},
    )
    capture_receipt_support = schema_support(
        conn, tables, "territory_target_capture_receipts",
        {"attacker_username", "expected_owner_username", "winner_username", "result", "created_at", "updated_at"},
    )
    progression_support = schema_support(
        conn, tables, "territory_progression_receipts",
        {"actor_username", "status", "created_at", "updated_at", "applied_at"},
    )
    rebuild_support = schema_support(
        conn, tables, "territory_rebuild_jobs",
        {"owner_username", "status", "attempts", "error", "created_at", "updated_at", "finished_at"},
    )
    result: dict[str, Any] = {
        "schema": {
            "captured_targets": captured_support,
            "areas": areas_support,
            "ownership": ownership_support,
            "publication": publication_support,
            "capture_receipts": capture_receipt_support,
            "progression_receipts": progression_support,
            "rebuild_jobs": rebuild_support,
        },
        "captured_targets_count": (
            count_where(conn, tables, "captured_targets", "owner_username = ?", (username,))
            if captured_support["schema_supported"] else None
        ),
        "areas_by_status": (
            grouped_counts(conn, tables, "player_areas", "status", "owner_username = ?", (username,))
            if areas_support["schema_supported"] else {}
        ),
        "ownership_count": (
            count_where(conn, tables, "territory_target_ownership", "owner_username = ?", (username,))
            if ownership_support["schema_supported"] else None
        ),
        "progression_receipts_by_status": (
            grouped_counts(conn, tables, "territory_progression_receipts", "status", "actor_username = ?", (username,))
            if progression_support["schema_supported"] else {}
        ),
        "rebuild_jobs_by_status": (
            grouped_counts(conn, tables, "territory_rebuild_jobs", "status", "owner_username = ?", (username,))
            if rebuild_support["schema_supported"] else {}
        ),
    }
    if captured_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT COALESCE(SUM(CASE WHEN stationary = 1 THEN 1 ELSE 0 END), 0) AS stationary_count,
                   COALESCE(SUM(CASE WHEN generated = 1 THEN 1 ELSE 0 END), 0) AS generated_count,
                   MAX(updated_at) AS latest_updated_at
            FROM captured_targets WHERE owner_username = ?
            """,
            (username,),
        )
        result["captured_targets"] = {
            "count": result["captured_targets_count"],
            "stationary_count": int(row["stationary_count"] or 0),
            "generated_count": int(row["generated_count"] or 0),
            "latest_updated_at": row["latest_updated_at"],
            "coordinates_and_labels_redacted": True,
        }
    if areas_support["schema_supported"]:
        row = one(
            conn,
            "SELECT MIN(created_at) AS earliest_created_at, MAX(updated_at) AS latest_updated_at FROM player_areas WHERE owner_username = ?",
            (username,),
        )
        result["areas_timeline"] = dict(row) if row else {}
    if ownership_support["schema_supported"]:
        row = one(
            conn,
            "SELECT MAX(ownership_version) AS max_version, MAX(updated_at) AS latest_updated_at FROM territory_target_ownership WHERE owner_username = ?",
            (username,),
        )
        result["ownership_timeline"] = {
            "max_version": int(row["max_version"] or 0),
            "latest_updated_at": row["latest_updated_at"],
        }
    if publication_support["schema_supported"]:
        row = one(
            conn,
            "SELECT publication_version, geometry_hash, updated_at FROM territory_area_publications WHERE owner_username = ?",
            (username,),
        )
        result["publication"] = {
            "present": bool(row),
            "version": int(row["publication_version"] or 0) if row else None,
            "geometry_hash_sha256": sha256_text(row["geometry_hash"]) if row and row["geometry_hash"] else None,
            "updated_at": row["updated_at"] if row else None,
        }
    if capture_receipt_support["schema_supported"]:
        where = "attacker_username = ? OR expected_owner_username = ? OR winner_username = ?"
        params = (username, username, username)
        row = one(
            conn,
            f"SELECT COUNT(*) AS count, MIN(created_at) AS earliest_created_at, MAX(updated_at) AS latest_updated_at FROM territory_target_capture_receipts WHERE {where}",
            params,
        )
        result["capture_receipts"] = {
            "count": int(row["count"] or 0),
            "earliest_created_at": row["earliest_created_at"],
            "latest_updated_at": row["latest_updated_at"],
            "results": grouped_counts(
                conn, tables, "territory_target_capture_receipts", "result", where, params,
                allowed_values={"captured", "duplicate", "lost", "rejected", "stale", "won"},
            ),
        }
    if progression_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT MIN(created_at) AS earliest_created_at, MAX(updated_at) AS latest_updated_at,
                   MAX(applied_at) AS latest_applied_at,
                   MIN(CASE WHEN status = 'pending' THEN updated_at END) AS oldest_pending_updated_at
            FROM territory_progression_receipts WHERE actor_username = ?
            """,
            (username,),
        )
        result["progression_timeline"] = dict(row) if row else {}
    if rebuild_support["schema_supported"]:
        row = one(
            conn,
            """
            SELECT MIN(created_at) AS earliest_created_at, MAX(updated_at) AS latest_updated_at,
                   MAX(finished_at) AS latest_finished_at, MAX(attempts) AS max_attempts,
                   COALESCE(SUM(CASE WHEN error IS NOT NULL AND error != '' THEN 1 ELSE 0 END), 0) AS error_present_count
            FROM territory_rebuild_jobs WHERE owner_username = ?
            """,
            (username,),
        )
        result["rebuild_timeline"] = {
            **dict(row),
            "max_attempts": int(row["max_attempts"] or 0),
            "error_present_count": int(row["error_present_count"] or 0),
        }
    findings: list[dict[str, Any]] = []
    failed_rebuilds = int(result["rebuild_jobs_by_status"].get("failed", 0))
    rejected_receipts = int(result["progression_receipts_by_status"].get("rejected", 0))
    if failed_rebuilds:
        findings.append(finding("territory_rebuild_jobs_failed", "high", "territory", count=failed_rebuilds))
    if rejected_receipts:
        findings.append(finding("territory_progression_receipts_rejected", "warning", "territory", count=rejected_receipts))
    result["scope_status"] = (
        "unknown" if not all(item["schema_supported"] for item in result["schema"].values())
        else "divergent" if any(item["severity"] == "high" for item in findings)
        else "consistent_with_findings" if findings else "consistent"
    )
    return result, findings


def ghostnetwork_summary(
    conn: sqlite3.Connection,
    tables: set[str],
    username: str | None = None,
    profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    result: dict[str, Any] = {
        "cycle": None,
        "parts_by_status": {},
        "global_territory_jobs_by_status": grouped_counts(conn, tables, "ghostnetwork_territory_jobs", "status"),
        "global_delta_delivery_jobs_by_status": grouped_counts(conn, tables, "ghostnetwork_delta_delivery_jobs", "status"),
    }
    findings: list[dict[str, Any]] = []
    cycle = None
    cycle_support = schema_support(
        conn, tables, "ghost_cycles", {"cycle_id", "status", "created_at", "updated_at"}
    )
    result["schema"] = {"cycle": cycle_support}
    if cycle_support["schema_supported"]:
        cycle_columns = table_columns(conn, "ghost_cycles")
        version_column = "state_version" if "state_version" in cycle_columns else "0"
        cycle = one(
            conn,
            f"SELECT cycle_id, status, {version_column} AS state_version, created_at, updated_at "
            "FROM ghost_cycles WHERE status = 'active' ORDER BY updated_at DESC LIMIT 1",
        )
        active_count = count_where(conn, tables, "ghost_cycles", "status = 'active'")
        result["active_cycle_count"] = active_count
        if cycle:
            result["cycle"] = {
                "cycle_ref_sha256": sha256_text(cycle["cycle_id"]),
                "status": cycle["status"],
                "state_version": int(cycle["state_version"] or 0),
                "created_at": cycle["created_at"],
                "updated_at": cycle["updated_at"],
            }
        if active_count != 1:
            findings.append(finding("ghostnetwork_active_cycle_count", "high", "ghostnetwork", count=active_count))
    parts_support = schema_support(
        conn, tables, "ghost_parts", {"cycle_id", "status", "discovered_by", "discovered_at", "updated_at"}
    )
    result["schema"]["parts"] = parts_support
    if cycle and parts_support["schema_supported"]:
        result["parts_by_status"] = grouped_counts(
            conn, tables, "ghost_parts", "status", "cycle_id = ?", (cycle["cycle_id"],)
        )
        part_count = sum(result["parts_by_status"].values())
        result["part_count"] = part_count
        if part_count != 20:
            findings.append(finding("ghostnetwork_part_count_not_20", "high", "ghostnetwork", count=part_count))

    if username:
        reservations_support = schema_support(
            conn,
            tables,
            "ghost_part_reservations",
            {"player_id", "status", "reserved_at", "released_at"},
        )
        events_support = schema_support(
            conn,
            tables,
            "ghost_part_events",
            {"event_id", "player_id", "event_type", "audience_scope", "created_at"},
        )
        effects_support = schema_support(
            conn, tables, "ghost_capture_effects", {"player_id", "status", "created_at", "updated_at"}
        )
        contribution_support = schema_support(
            conn, tables, "ghost_contributions", {"player_id", "contribution_type", "source_event_id", "created_at"}
        )
        reward_support = schema_support(
            conn, tables, "ghost_reward_ledger",
            {
                "player_id", "reward_key", "reward_type", "source_event_id",
                "status", "created_at", "applied_at",
            },
        )
        achievement_support = schema_support(
            conn, tables, "ghost_achievements", {"player_id", "awarded_at"}
        )
        territory_job_support = schema_support(
            conn,
            tables,
            "ghostnetwork_territory_jobs",
            {
                "job_kind", "reference_id", "status", "created_at",
                "updated_at", "finished_at",
            },
        )
        result["schema"].update({
            "reservations": reservations_support,
            "events": events_support,
            "capture_effects": effects_support,
            "contributions": contribution_support,
            "rewards": reward_support,
            "achievements": achievement_support,
            "territory_jobs": territory_job_support,
        })
        result["user"] = {
            "discovered_parts": (
                count_where(conn, tables, "ghost_parts", "discovered_by = ?", (username,))
                if parts_support["schema_supported"] else None
            ),
            "reservations_by_status": grouped_counts(
                conn, tables, "ghost_part_reservations", "status", "player_id = ?", (username,)
            ) if reservations_support["schema_supported"] else {},
            "events_by_type": grouped_counts(
                conn, tables, "ghost_part_events", "event_type", "player_id = ?", (username,),
                allowed_values=SAFE_GHOST_EVENT_TYPES,
            ) if events_support["schema_supported"] else {},
            "events_by_audience_scope": grouped_counts(
                conn, tables, "ghost_part_events", "audience_scope", "player_id = ?", (username,),
                allowed_values=SAFE_GHOST_AUDIENCE_SCOPES,
            ) if events_support["schema_supported"] else {},
            "capture_effects_by_status": grouped_counts(
                conn, tables, "ghost_capture_effects", "status", "player_id = ?", (username,)
            ) if effects_support["schema_supported"] else {},
            "contributions_count": (
                count_where(conn, tables, "ghost_contributions", "player_id = ?", (username,))
                if contribution_support["schema_supported"] else None
            ),
            "contributions_by_type": grouped_counts(
                conn, tables, "ghost_contributions", "contribution_type", "player_id = ?", (username,),
                allowed_values=SAFE_GHOST_REWARD_TYPES,
            ) if contribution_support["schema_supported"] else {},
            "rewards_by_status": grouped_counts(
                conn, tables, "ghost_reward_ledger", "status", "player_id = ?", (username,)
            ) if reward_support["schema_supported"] else {},
            "rewards_by_type": grouped_counts(
                conn, tables, "ghost_reward_ledger", "reward_type", "player_id = ?", (username,),
                allowed_values=SAFE_GHOST_REWARD_TYPES,
            ) if reward_support["schema_supported"] else {},
            "achievements_count": (
                count_where(conn, tables, "ghost_achievements", "player_id = ?", (username,))
                if achievement_support["schema_supported"] else None
            ),
            "territory_jobs_by_status": grouped_counts(
                conn,
                tables,
                "ghostnetwork_territory_jobs",
                "status",
                "job_kind = 'areas' AND reference_id = ?",
                (username,),
            ) if territory_job_support["schema_supported"] else {},
        }
        if parts_support["schema_supported"]:
            row = one(
                conn,
                "SELECT MIN(discovered_at) AS earliest_discovered_at, MAX(updated_at) AS latest_updated_at FROM ghost_parts WHERE discovered_by = ?",
                (username,),
            )
            result["user"]["parts_timeline"] = dict(row) if row else {}
        if events_support["schema_supported"]:
            event_timelines: dict[str, dict[str, Any]] = {}
            for row in conn.execute(
                """
                SELECT event_type, COUNT(*) AS count,
                       MIN(created_at) AS earliest_at, MAX(created_at) AS latest_at
                FROM ghost_part_events
                WHERE player_id = ?
                GROUP BY event_type
                """,
                (username,),
            ):
                event_type = str(row["event_type"] or "")
                key = event_type if event_type in SAFE_GHOST_EVENT_TYPES else "__other__"
                current = event_timelines.setdefault(
                    key,
                    {"count": 0, "earliest_at": row["earliest_at"], "latest_at": row["latest_at"]},
                )
                current["count"] += int(row["count"] or 0)
                if row["earliest_at"] and (
                    not current["earliest_at"] or row["earliest_at"] < current["earliest_at"]
                ):
                    current["earliest_at"] = row["earliest_at"]
                if row["latest_at"] and (
                    not current["latest_at"] or row["latest_at"] > current["latest_at"]
                ):
                    current["latest_at"] = row["latest_at"]
            result["user"]["event_timelines_by_type"] = event_timelines
        timeline_specs = (
            ("events_timeline", "ghost_part_events", events_support, "created_at", "player_id"),
            ("capture_effects_timeline", "ghost_capture_effects", effects_support, "updated_at", "player_id"),
            ("contributions_timeline", "ghost_contributions", contribution_support, "created_at", "player_id"),
            ("achievements_timeline", "ghost_achievements", achievement_support, "awarded_at", "player_id"),
        )
        for key, table, support, timestamp_column, player_column in timeline_specs:
            if support["schema_supported"]:
                row = one(
                    conn,
                    f'SELECT MIN("{timestamp_column}") AS earliest_at, MAX("{timestamp_column}") AS latest_at FROM "{table}" WHERE "{player_column}" = ?',
                    (username,),
                )
                result["user"][key] = dict(row) if row else {}
        if territory_job_support["schema_supported"]:
            row = one(
                conn,
                """
                SELECT COUNT(*) AS count,
                       MIN(created_at) AS earliest_created_at,
                       MAX(updated_at) AS latest_updated_at,
                       MAX(finished_at) AS latest_finished_at
                FROM ghostnetwork_territory_jobs
                WHERE job_kind = 'areas' AND reference_id = ?
                """,
                (username,),
            )
            result["user"]["territory_jobs_timeline"] = dict(row) if row else {}
        if reward_support["schema_supported"]:
            row = one(
                conn,
                """
                SELECT MIN(created_at) AS earliest_created_at, MAX(created_at) AS latest_created_at,
                       MAX(applied_at) AS latest_applied_at
                FROM ghost_reward_ledger WHERE player_id = ?
                """,
                (username,),
            )
            result["user"]["rewards_timeline"] = dict(row) if row else {}
            reward_timelines: dict[str, dict[str, Any]] = {}
            for row in conn.execute(
                """
                SELECT reward_type, COUNT(*) AS count,
                       MIN(created_at) AS earliest_created_at,
                       MAX(created_at) AS latest_created_at,
                       MAX(applied_at) AS latest_applied_at
                FROM ghost_reward_ledger
                WHERE player_id = ?
                GROUP BY reward_type
                """,
                (username,),
            ):
                reward_type = str(row["reward_type"] or "")
                key = reward_type if reward_type in SAFE_GHOST_REWARD_TYPES else "__other__"
                current = reward_timelines.setdefault(key, {
                    "count": 0,
                    "earliest_created_at": row["earliest_created_at"],
                    "latest_created_at": row["latest_created_at"],
                    "latest_applied_at": row["latest_applied_at"],
                })
                current["count"] += int(row["count"] or 0)
                if row["earliest_created_at"] and (
                    not current["earliest_created_at"]
                    or row["earliest_created_at"] < current["earliest_created_at"]
                ):
                    current["earliest_created_at"] = row["earliest_created_at"]
                if row["latest_created_at"] and (
                    not current["latest_created_at"]
                    or row["latest_created_at"] > current["latest_created_at"]
                ):
                    current["latest_created_at"] = row["latest_created_at"]
                if row["latest_applied_at"] and (
                    not current["latest_applied_at"]
                    or row["latest_applied_at"] > current["latest_applied_at"]
                ):
                    current["latest_applied_at"] = row["latest_applied_at"]
            result["user"]["reward_timelines_by_type"] = reward_timelines
            ledger_keys = {
                str(row["reward_key"] or "")
                for row in conn.execute(
                    "SELECT reward_key FROM ghost_reward_ledger WHERE player_id = ? AND status = 'applied'",
                    (username,),
                )
                if row["reward_key"]
            }
            profile_history = (profile or {}).get("ghostnetwork_reward_history") or []
            profile_keys = {
                str(item.get("reward_key") or "")
                for item in profile_history if isinstance(item, dict) and item.get("reward_key")
            }
            result["user"]["reward_history_projection"] = {
                "ledger_applied_count": len(ledger_keys),
                "profile_history_count": len(profile_keys),
                "ledger_keys_checksum_sha256": id_set_checksum(ledger_keys),
                "profile_keys_checksum_sha256": id_set_checksum(profile_keys),
                "ledger_only_count": len(ledger_keys - profile_keys),
                "profile_only_count": len(profile_keys - ledger_keys),
            }
            if ledger_keys != profile_keys:
                findings.append(finding(
                    "ghostnetwork_reward_history_projection_mismatch",
                    "high",
                    "ghostnetwork_account",
                    ledger_only_count=len(ledger_keys - profile_keys),
                    profile_only_count=len(profile_keys - ledger_keys),
                ))
        if events_support["schema_supported"] and reward_support["schema_supported"]:
            row = one(
                conn,
                """
                SELECT COUNT(*) AS matched_count,
                       MIN(events.created_at) AS earliest_event_at,
                       MAX(events.created_at) AS latest_event_at,
                       MIN(rewards.created_at) AS earliest_reward_created_at,
                       MAX(rewards.created_at) AS latest_reward_created_at,
                       MAX(rewards.applied_at) AS latest_reward_applied_at
                FROM ghost_part_events AS events
                JOIN ghost_reward_ledger AS rewards
                  ON rewards.source_event_id = events.event_id
                WHERE events.player_id = ?
                  AND rewards.player_id = ?
                  AND events.event_type = 'ghost.part_activated'
                  AND events.audience_scope = 'clan'
                  AND rewards.reward_type = 'part_first_activated'
                  AND rewards.status = 'applied'
                """,
                (username, username),
            )
            result["user"]["activation_reward_correlation"] = {
                "matched_count": int(row["matched_count"] or 0),
                "earliest_event_at": row["earliest_event_at"],
                "latest_event_at": row["latest_event_at"],
                "earliest_reward_created_at": row["earliest_reward_created_at"],
                "latest_reward_created_at": row["latest_reward_created_at"],
                "latest_reward_applied_at": row["latest_reward_applied_at"],
                "event_and_reward_ids_redacted": True,
            }
        failed_effects = int(result["user"]["capture_effects_by_status"].get("failed", 0))
        failed_rewards = int(result["user"]["rewards_by_status"].get("failed", 0))
        if failed_effects:
            findings.append(finding(
                "ghostnetwork_capture_effects_failed", "high", "ghostnetwork_account",
                count=failed_effects,
            ))
        if failed_rewards:
            findings.append(finding(
                "ghostnetwork_rewards_failed", "high", "ghostnetwork_account",
                count=failed_rewards,
            ))
        result["user"]["scope_status"] = (
            "unknown" if not all(item["schema_supported"] for item in result["schema"].values())
            else "divergent" if any(item["scope"] == "ghostnetwork_account" for item in findings)
            else "consistent"
        )
    return result, findings


def aggregate_profile_states(conn: sqlite3.Connection, tables: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    if "users" not in tables:
        return counts
    for row in conn.execute("SELECT username, profile_json FROM users"):
        state, _profile, _issues = classify_profile(str(row["username"]), row["profile_json"])
        counts[state] = counts.get(state, 0) + 1
    return dict(sorted(counts.items()))


def status_report(db_path: str, scan_all_profiles: bool = False) -> dict[str, Any]:
    with open_read_only_database(db_path) as (conn, path):
        tables = table_names(conn)
        missing_tables = [table for table in CORE_TABLES if table not in tables]
        ghost, ghost_findings = ghostnetwork_summary(conn, tables)
        capabilities = schema_capabilities(conn, tables)
        users_support = schema_support(conn, tables, "users", {"username", "profile_json"})
        findings = list(ghost_findings)
        if "users" not in tables:
            findings.append(finding("users_table_missing", "blocker", "schema"))
        elif not users_support["schema_supported"]:
            findings.append(finding(
                "users_schema_unsupported",
                "blocker",
                "schema",
                missing_columns=users_support["missing_columns"],
            ))
        if not capabilities["profile_revision_present"]:
            findings.append(finding("profile_revision_missing", "warning", "runtime_guard"))
        if not capabilities["lkg_present"]:
            findings.append(finding(
                "profile_lkg_schema_unsupported"
                if capabilities["lkg_table_candidates"]
                else "profile_lkg_missing",
                "warning",
                "runtime_guard",
            ))
        if not capabilities["session_generation_schema_present"]:
            findings.append(finding("session_generation_missing", "warning", "runtime_guard"))

        profile_states = (
            aggregate_profile_states(conn, tables)
            if scan_all_profiles and users_support["schema_supported"] else {}
        )
        health_findings = [
            item for item in findings
            if item["scope"] != "runtime_guard"
            and item["severity"] in {"high", "blocker"}
        ]
        return {
            "tool_version": TOOL_VERSION,
            "command": "status",
            "generated_at": utc_now(),
            "read_only": True,
            "probe_status": "complete",
            "evidence_snapshot": "logical_read_only",
            "runtime_guard_status": runtime_guard_status(capabilities),
            "database": database_metadata(conn, path, tables),
            "tables": {
                "required_count": len(CORE_TABLES),
                "present_count": len(CORE_TABLES) - len(missing_tables),
                "missing": missing_tables,
            },
            "capabilities": capabilities,
            "users_schema": users_support,
            "total_users": count_where(conn, tables, "users") if "users" in tables else None,
            "profile_scan": {
                "performed": bool(scan_all_profiles and users_support["schema_supported"]),
                "requested": bool(scan_all_profiles),
                "states": profile_states,
            },
            # Kept as a compact compatibility alias for the targeted unit tests
            # and operator scripts written during the evidence-gate iteration.
            "profile_states": profile_states,
            "global_queues": {
                "territory_rebuild_jobs": grouped_counts(conn, tables, "territory_rebuild_jobs", "status"),
                "territory_progression_receipts": grouped_counts(conn, tables, "territory_progression_receipts", "status"),
                "ghostnetwork_territory_jobs": grouped_counts(conn, tables, "ghostnetwork_territory_jobs", "status"),
                "ghostnetwork_delta_delivery_jobs": grouped_counts(conn, tables, "ghostnetwork_delta_delivery_jobs", "status"),
            },
            "ghostnetwork": ghost,
            "findings": findings,
            "runtime_health_status": "blocked" if health_findings else (
                "warning" if findings else "clear"
            ),
            # ``ok`` describes successful probe execution, not account health.
            "ok": True,
        }


def audit_report(db_path: str, username: str, verify: bool = False) -> dict[str, Any]:
    username = str(username or "").strip()
    if not username:
        raise ValueError("exact_username_required")
    with open_read_only_database(db_path) as (conn, path):
        tables = table_names(conn)
        users_support = schema_support(
            conn,
            tables,
            "users",
            {"username", "password", "salt", "profile_json", "created_at", "updated_at"},
        )
        row = None
        if users_support["schema_supported"]:
            row = one(
                conn,
                """
                SELECT username, password, salt, profile_json, created_at, updated_at
                FROM users WHERE username = ?
                """,
                (username,),
            )
            profile_data, profile_findings, profile = profile_summary(row)
        else:
            profile_data = {
                "state": "unavailable",
                "issues": ["users_schema_unsupported"],
            }
            profile_findings = [finding(
                "users_schema_unsupported",
                "blocker",
                "tool_schema",
                missing_columns=users_support["missing_columns"],
            )]
            profile = None

        wallet_data, wallet_findings = wallet_summary(conn, tables, username, profile)
        inventory_data, inventory_findings = inventory_summary(conn, tables, username, profile)
        territory_data, territory_findings = territory_summary(conn, tables, username)
        ghost_data, ghost_findings = ghostnetwork_summary(
            conn, tables, username=username, profile=profile
        )
        googleplex_data = googleplex_summary(conn, tables, username, profile)
        runtime_scopes = runtime_scope_summary(conn, tables, username)
        capabilities = schema_capabilities(conn, tables)
        lkg_data, lkg_findings = lkg_summary(
            conn, tables, username, profile
        )

        activation = ghost_data.get("user", {}).get("activation_reward_correlation", {})
        profile_progression = profile_data.get("progression", {})
        activation_times = [
            activation.get("latest_event_at"),
            activation.get("latest_reward_created_at"),
            activation.get("latest_reward_applied_at"),
        ]
        distances = [
            distance
            for distance in (
                timestamp_distance_seconds(profile_data.get("updated_at"), timestamp)
                for timestamp in activation_times
            )
            if distance is not None
        ]
        territory_prior_state = bool(
            int(territory_data.get("captured_targets_count") or 0) > 0
            or int(territory_data.get("ownership_count") or 0) > 0
            or sum(int(value or 0) for value in territory_data.get("areas_by_status", {}).values()) > 0
        )
        inventory_prior_state = bool(
            int(inventory_data.get("canonical_store", {}).get("apps_count") or 0) > 0
            or int(inventory_data.get("canonical_store", {}).get("tools_count") or 0) > 0
        )
        wallet_prior_state = bool(
            int(wallet_data.get("ledger", {}).get("event_count") or 0) > 1
            or (
                wallet_data.get("balance_store") is not None
                and wallet_data["balance_store"].get("balance") not in {None, 1000}
            )
        )
        purchase_prior_state = bool(
            int(googleplex_data.get("profile_purchases_count") or 0) > 0
            or int(googleplex_data.get("profile_products_count") or 0) > 0
        )
        exact_starter_core = bool(
            profile_progression.get("level") == 1
            and profile_progression.get("hackcoins") == 1000
        )
        exp_value = str(profile_progression.get("exp") or "").strip().lower()
        zero_like_exp = bool(
            exp_value
            and (
                exp_value == "0"
                or exp_value.startswith("0.0")
                or exp_value.startswith("0 ")
            )
        )
        # A sparse overwrite is not guaranteed to remain an exact LVL-1
        # template.  Compatibility/template sync and later gameplay can move
        # level/respect while the destructive HC/EXP reset remains visible.
        # The incident classifier therefore also recognises a low-progression
        # post-template phenotype, but only in the presence of several durable
        # signals proving that this was an established account.
        post_template_reset_like_core = bool(
            profile_progression.get("level") in {1, 2}
            and profile_progression.get("hackcoins") == 1000
            and zero_like_exp
            and int(profile_progression.get("respect") or 0) <= 50
        )
        operations_count = sum(
            int(value or 0)
            for value in runtime_scopes.get("operations_by_status", {}).values()
        )
        system_messages_count = sum(
            int(value or 0)
            for value in runtime_scopes.get("system_messages_by_status", {}).values()
        )
        established_account_signals = {
            "inventory": inventory_prior_state,
            "wallet_history": int(wallet_data.get("ledger", {}).get("event_count") or 0) >= 10,
            "purchases": purchase_prior_state,
            "operations": operations_count >= 20,
            "state_deltas": int(runtime_scopes.get("state_deltas", {}).get("count") or 0) >= 100,
            "system_messages": system_messages_count >= 100,
            "target_runtime": int(runtime_scopes.get("target_runtime", {}).get("version") or 0) >= 100,
            "position_history": int(runtime_scopes.get("position", {}).get("version") or 0) >= 20,
        }
        established_signal_count = sum(bool(value) for value in established_account_signals.values())
        sparse_overwrite_signature = bool(
            int(activation.get("matched_count") or 0) > 0
            and territory_prior_state
            and (
                (
                    exact_starter_core
                    and (inventory_prior_state or wallet_prior_state or purchase_prior_state)
                )
                or (
                    post_template_reset_like_core
                    and established_signal_count >= 3
                )
            )
        )
        if "user" in ghost_data:
            ghost_data["user"]["sparse_activation_overwrite_signal"] = {
                "matched_activation_reward_count": int(activation.get("matched_count") or 0),
                "profile_starter_like_core": exact_starter_core,
                "profile_post_template_reset_like_core": post_template_reset_like_core,
                "durable_prior_state": {
                    "territory": territory_prior_state,
                    "inventory": inventory_prior_state,
                    "wallet": wallet_prior_state,
                    "purchases": purchase_prior_state,
                },
                "established_account_signals": established_account_signals,
                "established_account_signal_count": established_signal_count,
                "nearest_profile_update_distance_seconds": min(distances) if distances else None,
                "strong_signature": sparse_overwrite_signature,
                "signature_version": "post-template-v2",
                "signature_is_incident_correlation_not_causal_proof": True,
            }
        if sparse_overwrite_signature:
            ghost_findings.append(finding(
                "ghostnetwork_sparse_activation_overwrite_signature",
                "high",
                "ghostnetwork_account",
                matched_activation_reward_count=int(activation.get("matched_count") or 0),
                nearest_profile_update_distance_seconds=min(distances) if distances else None,
            ))
            ghost_data["user"]["scope_status"] = "divergent"
        findings = (
            profile_findings
            + wallet_findings
            + inventory_findings
            + territory_findings
            + ghost_findings
            + lkg_findings
        )
        if not capabilities["profile_revision_present"]:
            findings.append(finding("profile_revision_missing", "warning", "runtime_guard"))
        if not capabilities["session_generation_schema_present"]:
            findings.append(finding("session_generation_missing", "warning", "runtime_guard"))

        quick_check = None
        if verify:
            rows = conn.execute("PRAGMA quick_check").fetchall()
            values = [str(item[0]) for item in rows]
            quick_check = {
                "ok": values == ["ok"],
                "result_count": len(values),
                "first_result": values[0] if values else "missing",
            }
            if not quick_check["ok"]:
                findings.append(finding("sqlite_quick_check_failed", "blocker", "database"))

        account_scopes = {
            "profile", "wallet", "inventory", "territory",
            "ghostnetwork_account", "runtime_scope", "googleplex", "database",
        }
        account_findings = [item for item in findings if item["scope"] in account_scopes]
        global_findings = [item for item in findings if item["scope"] not in account_scopes]
        blocking = [
            item for item in account_findings
            if item["severity"] in {"blocker", "high"}
        ]
        tool_schema_blocked = any(
            item["scope"] == "tool_schema" and item["severity"] == "blocker"
            for item in findings
        )

        scope_schema_groups = (
            wallet_data.get("schema", {}).values(),
            inventory_data.get("canonical_store", {}).get("schema", {}).values(),
            territory_data.get("schema", {}).values(),
            ghost_data.get("schema", {}).values(),
            googleplex_data.get("source_schema", {}).values(),
        )
        optional_schema_complete = all(
            item.get("schema_supported", False)
            for group in scope_schema_groups
            for item in group
        )
        backup_candidate = bool(
            inventory_data.get("migration_evidence", {}).get("backup_candidate_present")
        )
        # A migration backup remains only a recovery candidate.  Historical
        # comparison becomes available solely from an exact-user LKG record
        # whose schema, JSON, identity and checksum have all been validated.
        historical_drop_detection = (
            "available"
            if lkg_data.get("record_validated") and profile_data.get("state") == "valid"
            else "unavailable"
        )
        if not users_support["schema_supported"]:
            evidence_status = "unavailable"
        elif optional_schema_complete and historical_drop_detection == "available":
            evidence_status = "complete"
        else:
            evidence_status = "partial"

        if blocking:
            account_integrity_status = "blocked"
        elif not row or evidence_status != "complete":
            account_integrity_status = "unknown"
        else:
            account_integrity_status = "clear"

        if tool_schema_blocked or evidence_status == "unavailable":
            verification_outcome = "probe_unavailable"
        elif account_integrity_status == "blocked":
            verification_outcome = "blocked"
        elif account_integrity_status != "clear" or evidence_status != "complete":
            verification_outcome = "inconclusive"
        else:
            verification_outcome = "passed"
        verification_exit_code = {
            "passed": 0,
            "blocked": 1,
            "probe_unavailable": 2,
            "inconclusive": 3,
        }[verification_outcome]

        inventory_scope_findings = [
            item for item in account_findings if item["scope"] == "inventory"
        ]
        scope_statuses = {
            "profile": "unavailable" if profile_data["state"] == "unavailable" else (
                "blocked" if profile_data["state"] != "valid" else "consistent"
            ),
            "wallet": wallet_data.get("scope_status", "unknown"),
            "inventory": inventory_data.get(
                "scope_status",
                "with_findings" if inventory_scope_findings else "unknown",
            ),
            "runtime_scopes": "unknown" if not all(
                item.get("schema_supported", False)
                for item in runtime_scopes.get("schema", {}).values()
            ) else "observed",
            "territory": territory_data.get("scope_status", "unknown"),
            "ghostnetwork_account": ghost_data.get("user", {}).get("scope_status", "unknown"),
            "googleplex": googleplex_data.get("evidence_status", "unavailable"),
        }
        report = {
            "tool_version": TOOL_VERSION,
            "command": "verify" if verify else "audit",
            "generated_at": utc_now(),
            "read_only": True,
            "probe_status": "complete",
            "evidence_snapshot": "logical_read_only",
            "evidence_status": evidence_status,
            "verification_outcome": verification_outcome,
            "verification_passed": verification_outcome == "passed",
            "verification_exit_code": verification_exit_code,
            "current_profile_state": profile_data["state"],
            "historical_drop_detection": {
                "status": historical_drop_detection,
                "starter_signature_is_signal_not_proof": bool(profile_data.get("starter_signature")),
                "migration_backup_candidate_present": backup_candidate,
                "lkg_table_candidate_present": bool(capabilities["lkg_table_candidates"]),
                "lkg_contract_schema_present": bool(capabilities["lkg_schema_present"]),
                "candidate_payloads_validated": bool(lkg_data.get("record_validated")),
            },
            "runtime_guard_status": runtime_guard_status(
                capabilities,
                lkg_record_validated=bool(lkg_data.get("record_validated")),
            ),
            "account_integrity_status": account_integrity_status,
            "subject": redacted_username(username),
            "exact_match": bool(row) if users_support["schema_supported"] else None,
            "database": database_metadata(conn, path, tables),
            "capabilities": capabilities,
            "last_known_good": lkg_data,
            "users_schema": users_support,
            "profile": profile_data,
            "wallet": wallet_data,
            "inventory": inventory_data,
            "runtime_scopes": runtime_scopes,
            "territory": territory_data,
            "ghostnetwork": ghost_data,
            "googleplex": googleplex_data,
            "scope_statuses": scope_statuses,
            "redaction": {
                "raw_username_included": False,
                "credentials_included": False,
                "full_profile_json_included": False,
                "coordinates_included": False,
                "target_ids_and_topology_included": False,
            },
            "findings": findings,
            "account_findings": account_findings,
            "global_findings": global_findings,
            "blocking_findings": len(blocking),
            "tool_schema_blocked": tool_schema_blocked,
            # ``ok`` describes successful probe execution; see account status.
            "ok": True,
        }
        if quick_check is not None:
            report["sqlite_quick_check"] = quick_check
        return report


def build_parser() -> argparse.ArgumentParser:
    default_db = os.environ.get("CHAOS_DB_PATH", os.path.join("data", "game.sqlite3"))
    parser = argparse.ArgumentParser(
        description="Read-only Sprint 130.10 profile integrity evidence probe."
    )
    parser.add_argument(
        "--db",
        default=default_db,
        help="SQLite database path (opened with mode=ro).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    status = subparsers.add_parser("status", help="Aggregate schema/runtime status without user data.")
    audit = subparsers.add_parser("audit", help="Redacted exact-user evidence report.")
    verify = subparsers.add_parser(
        "verify",
        help=(
            "Audit plus SQLite quick_check; exits 0 passed, 1 blocked, "
            "2 unavailable/tool failure, or 3 inconclusive."
        ),
    )

    for command_parser in (status, audit, verify):
        command_parser.add_argument(
            "--db",
            default=argparse.SUPPRESS,
            help="SQLite database path (may also be supplied before the command).",
        )
    status.add_argument(
        "--scan-all-profiles",
        action="store_true",
        help="Opt in to parsing every profile JSON; disabled by default on live databases.",
    )
    audit.add_argument("--username", required=True, help="Exact canonical login; output omits it.")
    verify.add_argument("--username", required=True, help="Exact canonical login; output omits it.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            report = status_report(args.db, scan_all_profiles=args.scan_all_profiles)
        elif args.command == "audit":
            report = audit_report(args.db, args.username, verify=False)
        else:
            report = audit_report(args.db, args.username, verify=True)
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        payload = {
            "tool_version": TOOL_VERSION,
            "command": getattr(args, "command", ""),
            "generated_at": utc_now(),
            "read_only": True,
            "probe_status": "failed",
            "evidence_snapshot": "unavailable",
            "ok": False,
            "error": str(exc),
        }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
        return 2

    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    if args.command == "verify":
        return int(report.get("verification_exit_code", 2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
