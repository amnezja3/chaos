#!/usr/bin/env python3
"""Sprint 130.11 exact-account controlled recovery tool.

Read commands create an exact-subject audit, signed plan and before-manifest.
Write commands are explicitly gated, CAS protected, receipt-backed and limited
to canonical ``trolu2``.  Runtime does not import this tool and the tool never
scans or parses profiles belonging to other users.
"""

from __future__ import annotations

import argparse
import copy
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

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from territory_geometry import (
    build_player_areas as build_canonical_player_areas,
    point_in_polygon as canonical_point_in_polygon,
    polygons_intersect as canonical_polygons_intersect,
)


TOOL_VERSION = "130.11.1-controlled-recovery"
REPORTED_LOGIN = "Trollu2"
CANONICAL_USERNAME = "trolu2"
RECOVERY_LEVEL = 50
RECOVERY_RESPECT = 2560
RECOVERY_BALANCE = 250_000
PILLARS_PER_CITY = 8
PILLAR_RING_RADIUS_M = 1_200.0
TARGET_CLEARANCE_M = 100.0
GN_CLEARANCE_M = 500.0
TERRITORY_MAX_EXACT_AREA_TARGETS = int(
    os.environ.get("CHAOS_TERRITORY_EXACT_TARGET_LIMIT", "32")
)
TERRITORY_MAX_EXACT_AREA_TRIANGLES = int(
    os.environ.get("CHAOS_TERRITORY_EXACT_TRIANGLE_LIMIT", "1200")
)
RECOVERY_RECEIPTS_TABLE = "trollu2_recovery_receipts"
RECOVERY_STEPS_TABLE = "trollu2_recovery_steps"


class RecoveryGateError(RuntimeError):
    """Fail-closed operator gate."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest(value: Any) -> str:
    return sha256_text(canonical_json(value))


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def loads_object(raw: Any) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def loads_list(raw: Any) -> list[Any]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def profile_checksum(profile: dict[str, Any]) -> str:
    return digest(profile)


def database_uri(db_path: str) -> str:
    return Path(db_path).resolve().as_uri() + "?mode=ro"


@contextmanager
def readonly_connection(db_path: str):
    db = Path(db_path).resolve()
    if not db.is_file():
        raise RecoveryGateError(f"Database does not exist: {db}")
    conn = sqlite3.connect(database_uri(str(db)), uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def write_connection(db_path: str):
    db = Path(db_path).resolve()
    if not db.is_file():
        raise RecoveryGateError(f"Database does not exist: {db}")
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_recovery_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RECOVERY_RECEIPTS_TABLE} (
            plan_id TEXT PRIMARY KEY,
            canonical_username TEXT NOT NULL,
            plan_sha256 TEXT NOT NULL,
            before_manifest_sha256 TEXT NOT NULL,
            status TEXT NOT NULL,
            expected_before_revision INTEGER NOT NULL,
            expected_before_checksum TEXT NOT NULL,
            current_profile_revision INTEGER NOT NULL DEFAULT 0,
            current_profile_checksum TEXT NOT NULL DEFAULT '',
            current_wallet_version INTEGER NOT NULL DEFAULT 0,
            result_json TEXT NOT NULL DEFAULT '{{}}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            applied_at TEXT,
            verified_at TEXT,
            promoted_at TEXT,
            rolled_back_at TEXT
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RECOVERY_STEPS_TABLE} (
            plan_id TEXT NOT NULL,
            step_key TEXT NOT NULL,
            status TEXT NOT NULL,
            receipt_json TEXT NOT NULL DEFAULT '{{}}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            applied_at TEXT,
            PRIMARY KEY(plan_id, step_key)
        )
        """
    )


def require_write_flag(args: argparse.Namespace) -> None:
    if not bool(getattr(args, "write", False)):
        raise RecoveryGateError("Write command requires explicit --write")
    if not str(getattr(args, "authorized_by", "") or "").strip():
        raise RecoveryGateError("Write command requires --authorized-by")


def validate_profile_contract(profile: dict[str, Any], username: str) -> list[str]:
    errors = []
    if not isinstance(profile, dict):
        return ["profile_not_object"]
    if profile.get("username") != username:
        errors.append("username_mismatch")
    rules = {
        "level": lambda value: isinstance(value, int) and not isinstance(value, bool) and value >= 1,
        "hackcoins": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0,
        "respect": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0,
        "exp": lambda value: (isinstance(value, str) and bool(value.strip())) or isinstance(value, (int, float)),
        "inventory": lambda value: isinstance(value, list),
        "files": lambda value: isinstance(value, dict),
        "apps": lambda value: isinstance(value, list),
        "hacked": lambda value: isinstance(value, list),
        "desktop_settings": lambda value: isinstance(value, dict),
        "security": lambda value: isinstance(value, dict),
        "territory_stats": lambda value: isinstance(value, dict),
    }
    for key, validator in rules.items():
        if key not in profile:
            errors.append(f"{key}_missing")
        elif not validator(profile.get(key)):
            errors.append(f"{key}_invalid")
    files = profile.get("files")
    if isinstance(files, dict):
        invalid = sorted(str(key) for key, value in files.items() if not isinstance(value, list))
        if invalid:
            errors.append("files_scope_invalid:" + ",".join(invalid))
    try:
        canonical_json(profile)
    except (TypeError, ValueError):
        errors.append("profile_not_json_serializable")
    return errors


def canonical_profile_overlay(
    conn: sqlite3.Connection, username: str, profile: dict[str, Any], wallet_balance: int,
    *, exclude_recovery_plan_id: str = "",
) -> dict[str, Any]:
    candidate = copy.deepcopy(profile)
    candidate["hackcoins"] = int(wallet_balance)
    app_columns = table_columns(conn, "player_apps")
    app_query = "SELECT * FROM player_apps WHERE username=?"
    if "status" in app_columns:
        app_query += " AND status != 'uninstalled'"
    app_query += " ORDER BY app_id"
    apps = []
    for row in conn.execute(app_query, (username,)):
        app = decode_store_payload(row, ("app_json", "payload_json"))
        if not app:
            app = {"id": row["app_id"], "name": row["app_id"]}
        app.setdefault("id", row["app_id"])
        if "status" in row.keys():
            app.setdefault("status", row["status"])
        apps.append(app)
    candidate["apps"] = apps
    tools = []
    for row in conn.execute(
        "SELECT * FROM player_tool_files WHERE username=? ORDER BY tool_id", (username,)
    ):
        item = decode_store_payload(row, ("tool_json", "file_json", "payload_json"))
        if not item:
            item = {"id": row["tool_id"], "name": row["tool_id"], "file": row["tool_id"]}
        item.setdefault("id", row["tool_id"])
        item.setdefault("tool_id", row["tool_id"])
        if "app_id" in row.keys():
            item.setdefault("app_id", row["app_id"])
        tools.append(item)
    files = copy.deepcopy(candidate.get("files") if isinstance(candidate.get("files"), dict) else {})
    files["tools"] = tools
    candidate["files"] = files
    captured = []
    for row in conn.execute(
        "SELECT target_json FROM captured_targets WHERE owner_username=? ORDER BY id",
        (username,),
    ):
        target = loads_object(row["target_json"])
        if (
            exclude_recovery_plan_id
            and target.get("recovery_plan_id") == exclude_recovery_plan_id
        ):
            continue
        if target:
            captured.append(target)
    candidate["hacked"] = captured
    storage = conn.execute("SELECT * FROM player_storage WHERE username=?", (username,)).fetchone()
    if storage:
        candidate["storage_capacity"] = int(storage["capacity"] or 0)
        candidate["storage_used"] = int(storage["used"] or 0)
        candidate["storage_unit"] = str(storage["unit"] or "MB")
        if "modifiers_json" in storage.keys():
            modifiers = loads_object(storage["modifiers_json"])
            for key in ("storage_upgrades", "googleplex_products", "storage_soft_limit", "storage_over_limit"):
                if key in modifiers:
                    candidate[key] = copy.deepcopy(modifiers[key])
    return candidate


def runtime_captured_targets_projection(
    conn: sqlite3.Connection, username: str
) -> list[dict[str, Any]]:
    """Mirror ``TerritoryStore.list_captured_targets`` byte-for-byte logically."""
    targets = []
    for row in conn.execute(
        "SELECT lat, lng, target_json FROM captured_targets "
        "WHERE owner_username=? ORDER BY captured_at",
        (username,),
    ):
        target = loads_object(row["target_json"])
        target["lat"] = float(target.get("lat", row["lat"]))
        lng = target.get("lng", target.get("lon", row["lng"]))
        target["lng"] = float(lng)
        target["lon"] = float(lng)
        targets.append(target)
    return targets


def table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row["name"])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f'PRAGMA table_info("{table}")')}


def schema_checksum(conn: sqlite3.Connection) -> str:
    rows = conn.execute(
        "SELECT type, name, tbl_name, COALESCE(sql, '') AS sql "
        "FROM sqlite_master WHERE tbl_name NOT IN (?, ?) AND name NOT IN (?, ?) "
        "ORDER BY type, name",
        (
            RECOVERY_RECEIPTS_TABLE, RECOVERY_STEPS_TABLE,
            RECOVERY_RECEIPTS_TABLE, RECOVERY_STEPS_TABLE,
        ),
    ).fetchall()
    return digest([dict(row) for row in rows])


def db_identity(conn: sqlite3.Connection, db_path: str) -> dict[str, Any]:
    db = Path(db_path).resolve()
    return {
        "database_name": db.name,
        "database_size_bytes": db.stat().st_size,
        "schema_sha256": schema_checksum(conn),
        "sqlite_version": sqlite3.sqlite_version,
        "query_only": bool(conn.execute("PRAGMA query_only").fetchone()[0]),
    }


def require_schema(conn: sqlite3.Connection) -> None:
    required = {
        "users", "profile_last_known_good", "wallet_balances", "wallet_ledger",
        "wallet_balance_events", "player_apps", "player_tool_files", "player_storage",
        "system_messages", "captured_targets", "territory_target_ownership",
        "player_areas", "territory_rebuild_jobs", "territory_conflicts",
        "ghost_cycles", "ghost_parts", "ghost_capture_effects",
        "ghostnetwork_territory_jobs", "ghostnetwork_delta_delivery_jobs",
    }
    missing = sorted(required - table_names(conn))
    if missing:
        raise RecoveryGateError("Required Sprint 130.11 schema missing: " + ", ".join(missing))
    user_columns = table_columns(conn, "users")
    required_user_columns = {
        "username", "profile_json", "profile_revision", "profile_schema_version",
        "profile_checksum", "profile_integrity_status", "profile_validation_version",
    }
    missing_user = sorted(required_user_columns - user_columns)
    if missing_user:
        raise RecoveryGateError("Profile integrity columns missing: " + ", ".join(missing_user))


def exact_user_row(conn: sqlite3.Connection) -> sqlite3.Row:
    row = conn.execute(
        "SELECT username, profile_json, profile_revision, profile_schema_version, "
        "profile_checksum, profile_integrity_status, profile_validation_version, "
        "created_at, updated_at FROM users WHERE username = ?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    if row is None:
        candidates = conn.execute(
            "SELECT username FROM users WHERE lower(username)=lower(?) ORDER BY username",
            (REPORTED_LOGIN,),
        ).fetchall()
        raise RecoveryGateError(
            "Exact canonical account missing; case-insensitive matches="
            + canonical_json([item["username"] for item in candidates])
        )
    if row["username"] != CANONICAL_USERNAME:
        raise RecoveryGateError("Canonical username mismatch")
    return row


def profile_state(row: sqlite3.Row, include_profile: bool = False) -> dict[str, Any]:
    profile = loads_object(row["profile_json"])
    computed = profile_checksum(profile) if profile else ""
    result = {
        "revision": int(row["profile_revision"] or 0),
        "schema_version": int(row["profile_schema_version"] or 0),
        "stored_checksum": str(row["profile_checksum"] or ""),
        "computed_checksum": computed,
        "checksum_valid": bool(computed) and computed == str(row["profile_checksum"] or ""),
        "integrity_status": str(row["profile_integrity_status"] or ""),
        "validation_version": int(row["profile_validation_version"] or 0),
        "profile_json_bytes": len(str(row["profile_json"] or "").encode("utf-8")),
        "updated_at": row["updated_at"],
    }
    if include_profile:
        result["profile"] = profile
    return result


def lkg_state(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        "SELECT profile_revision, schema_version, snapshot_json, checksum, source, "
        "created_at, validation_version FROM profile_last_known_good WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    if row is None:
        return {"present": False, "usable_as_recovery_source": False}
    snapshot = loads_object(row["snapshot_json"])
    forbidden_mirrors = sorted(
        key for key in ("apps", "files", "hackcoins", "hacked", "operations") if key in snapshot
    )
    checksum_valid = bool(snapshot) and digest(snapshot) == str(row["checksum"] or "")
    return {
        "present": True,
        "revision": int(row["profile_revision"] or 0),
        "schema_version": int(row["schema_version"] or 0),
        "checksum_valid": checksum_valid,
        "forbidden_canonical_mirror_keys": forbidden_mirrors,
        "source": row["source"],
        "created_at": row["created_at"],
        "validation_version": int(row["validation_version"] or 0),
        "usable_as_recovery_source": checksum_valid and not forbidden_mirrors,
    }


def decode_store_payload(row: sqlite3.Row, candidates: Iterable[str]) -> dict[str, Any]:
    keys = set(row.keys())
    for key in candidates:
        if key in keys:
            payload = loads_object(row[key])
            if payload:
                return payload
    return {}


def inventory_evidence(conn: sqlite3.Connection) -> dict[str, Any]:
    apps = []
    for row in conn.execute(
        "SELECT * FROM player_apps WHERE username=? ORDER BY app_id", (CANONICAL_USERNAME,)
    ):
        payload = decode_store_payload(row, ("app_json", "payload_json"))
        app_id = str(row["app_id"] or payload.get("id") or payload.get("app_id") or "")
        apps.append({
            "app_id": app_id,
            "name": str(payload.get("name") or payload.get("title") or app_id),
            "installed": bool(row["installed"]) if "installed" in row.keys() else True,
        })
    tools = []
    for row in conn.execute(
        "SELECT * FROM player_tool_files WHERE username=? ORDER BY tool_id", (CANONICAL_USERNAME,)
    ):
        payload = decode_store_payload(row, ("file_json", "tool_json", "payload_json"))
        tool_id = str(row["tool_id"] or payload.get("id") or payload.get("tool_id") or "")
        tools.append({"tool_id": tool_id, "name": str(payload.get("name") or tool_id)})
    storage = conn.execute(
        "SELECT * FROM player_storage WHERE username=?", (CANONICAL_USERNAME,)
    ).fetchone()
    storage_summary = {}
    if storage:
        for key in ("capacity", "used", "unit", "version", "updated_at"):
            if key in storage.keys():
                storage_summary[key] = storage[key]
    return {
        "apps": apps,
        "tools": tools,
        "storage": storage_summary,
        "app_ids_sha256": digest([item["app_id"] for item in apps]),
        "tool_ids_sha256": digest([item["tool_id"] for item in tools]),
    }


def googleplex_evidence(conn: sqlite3.Connection, inventory: dict[str, Any]) -> dict[str, Any]:
    installed_ids = {item["app_id"] for item in inventory["apps"] if item["installed"]}
    rows = conn.execute(
        "SELECT message_id, dedupe_key, source, payload_json, created_at "
        "FROM system_messages WHERE username=? "
        "AND source IN ('googleplex_install','googleplex_product') ORDER BY created_at DESC",
        (CANONICAL_USERNAME,),
    ).fetchall()
    installs = []
    cities: dict[tuple[str, str], dict[str, Any]] = {}
    products = []
    for row in rows:
        payload = loads_object(row["payload_json"])
        dedupe_key = str(row["dedupe_key"] or payload.get("dedupe_key") or "")
        if row["source"] == "googleplex_install":
            prefix = f"googleplex_app_install:{CANONICAL_USERNAME}:"
            app_id = dedupe_key[len(prefix):] if dedupe_key.startswith(prefix) else ""
            installs.append({
                "app_id": app_id,
                "message_id": row["message_id"],
                "created_at": row["created_at"],
                "canonical_inventory_match": app_id in installed_ids,
            })
        else:
            product_id = str(payload.get("product_id") or "")
            products.append({
                "product_id": product_id,
                "message_id": row["message_id"],
                "created_at": row["created_at"],
            })
            for effect in payload.get("effects") or []:
                if not isinstance(effect, dict) or effect.get("type") != "travel_city":
                    continue
                try:
                    lat, lng = float(effect["lat"]), float(effect["lng"])
                except (KeyError, TypeError, ValueError):
                    continue
                city = str(effect.get("city") or "").strip()
                if city and -90 <= lat <= 90 and -180 <= lng <= 180:
                    cities[(product_id, city)] = {
                        "city": city, "lat": lat, "lng": lng,
                        "product_id": product_id,
                        "message_id": row["message_id"],
                        "created_at": row["created_at"],
                        "provenance": "system_messages.googleplex_product.effects.travel_city",
                        "confidence": "canonical_receipt",
                    }
    return {
        "recent_installs": installs[:2],
        "all_install_count": len(installs),
        "products": products,
        "cities": sorted(cities.values(), key=lambda item: (item["city"], item["product_id"])),
    }


def wallet_evidence(conn: sqlite3.Connection) -> dict[str, Any]:
    balance = conn.execute(
        "SELECT balance, version, updated_at FROM wallet_balances WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    ledger = conn.execute(
        "SELECT COUNT(*) AS count, COALESCE(SUM(amount_delta),0) AS delta_sum, "
        "MAX(created_at) AS latest_created_at FROM wallet_ledger WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    events = conn.execute(
        "SELECT COUNT(*) AS count, MAX(version) AS max_version, MAX(created_at) AS latest_created_at "
        "FROM wallet_balance_events WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    return {
        "balance": int(balance["balance"] or 0) if balance else None,
        "balance_version": int(balance["version"] or 0) if balance else None,
        "balance_updated_at": balance["updated_at"] if balance else None,
        "ledger_count": int(ledger["count"] or 0),
        "ledger_delta_sum": int(ledger["delta_sum"] or 0),
        "ledger_latest_created_at": ledger["latest_created_at"],
        "balance_event_count": int(events["count"] or 0),
        "balance_event_max_version": int(events["max_version"] or 0),
        "balance_event_latest_created_at": events["latest_created_at"],
    }


def grouped_counts(conn: sqlite3.Connection, table: str, column: str = "status") -> dict[str, int]:
    return {
        str(row["key"] or "__empty__"): int(row["count"] or 0)
        for row in conn.execute(
            f'SELECT "{column}" AS key, COUNT(*) AS count FROM "{table}" GROUP BY "{column}"'
        )
    }


def ghostnetwork_evidence(conn: sqlite3.Connection) -> dict[str, Any]:
    cycles = conn.execute(
        "SELECT * FROM ghost_cycles WHERE status='active' ORDER BY updated_at DESC"
    ).fetchall()
    cycle = cycles[0] if cycles else None
    cycle_id = str(cycle["cycle_id"] or "") if cycle else ""
    parts = conn.execute(
        "SELECT part_id, status, latitude, longitude, target_id, territory_id, "
        "territory_owner_id, conflict_id, updated_at FROM ghost_parts "
        "WHERE cycle_id=? ORDER BY part_id", (cycle_id,),
    ).fetchall() if cycle_id else []
    part_projection = [dict(row) for row in parts]
    return {
        "active_cycle_count": len(cycles),
        "cycle": {
            "cycle_id": cycle_id,
            "status": cycle["status"] if cycle else None,
            "state_version": int(cycle["state_version"] or 0) if cycle and "state_version" in cycle.keys() else 0,
            "updated_at": cycle["updated_at"] if cycle else None,
        },
        "part_count": len(parts),
        "parts_by_status": {
            status: sum(1 for row in parts if str(row["status"]) == status)
            for status in ("pooled", "reserved", "public", "contained", "active", "consumed")
        },
        "topology_sha256": digest(part_projection),
        "capture_effects_by_status": grouped_counts(conn, "ghost_capture_effects"),
        "territory_jobs_by_status": grouped_counts(conn, "ghostnetwork_territory_jobs"),
        "delta_jobs_by_status": grouped_counts(conn, "ghostnetwork_delta_delivery_jobs"),
        "anchors": [
            {"lat": row["latitude"], "lng": row["longitude"]}
            for row in parts if row["latitude"] is not None and row["longitude"] is not None
        ],
    }


def territory_evidence(conn: sqlite3.Connection) -> dict[str, Any]:
    captured = conn.execute(
        "SELECT COUNT(*) AS count, SUM(CASE WHEN stationary=1 THEN 1 ELSE 0 END) AS stationary, "
        "MAX(updated_at) AS updated_at FROM captured_targets WHERE owner_username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    ownership = conn.execute(
        "SELECT COUNT(*) AS count, MAX(ownership_version) AS max_version, MAX(updated_at) AS updated_at "
        "FROM territory_target_ownership WHERE owner_username=?", (CANONICAL_USERNAME,)
    ).fetchone()
    areas = conn.execute(
        "SELECT COUNT(*) AS count, COALESCE(SUM(area_size),0) AS area_size, MAX(updated_at) AS updated_at "
        "FROM player_areas WHERE owner_username=? AND status='active'", (CANONICAL_USERNAME,)
    ).fetchone()
    return {
        "captured_targets": int(captured["count"] or 0),
        "stationary_targets": int(captured["stationary"] or 0),
        "captured_updated_at": captured["updated_at"],
        "ownership_count": int(ownership["count"] or 0),
        "ownership_max_version": int(ownership["max_version"] or 0),
        "ownership_updated_at": ownership["updated_at"],
        "active_area_count": int(areas["count"] or 0),
        "active_area_size": float(areas["area_size"] or 0),
        "areas_updated_at": areas["updated_at"],
        "rebuild_jobs_by_status": {
            str(row["status"]): int(row["count"])
            for row in conn.execute(
                "SELECT status, COUNT(*) AS count FROM territory_rebuild_jobs "
                "WHERE owner_username=? GROUP BY status", (CANONICAL_USERNAME,)
            )
        },
        "active_conflicts_global": int(conn.execute(
            "SELECT COUNT(*) FROM territory_conflicts WHERE status NOT IN ('resolved','closed')"
        ).fetchone()[0]),
    }


def session_evidence(conn: sqlite3.Connection) -> dict[str, Any]:
    tables = table_names(conn)
    if "session_generation_lineages" not in tables:
        return {
            "schema_present": False, "row_present": False,
            "row_count": 0, "projection_sha256": digest([]),
        }
    columns = table_columns(conn, "session_generation_lineages")
    user_column = "username" if "username" in columns else "canonical_username"
    rows = conn.execute(
        f'SELECT * FROM session_generation_lineages WHERE "{user_column}"=?',
        (CANONICAL_USERNAME,),
    ).fetchall()
    return {
        "schema_present": True,
        "row_present": bool(rows),
        "row_count": len(rows),
        "projection_sha256": digest([dict(row) for row in rows]),
    }


def audit_snapshot(conn: sqlite3.Connection, db_path: str) -> dict[str, Any]:
    require_schema(conn)
    user = exact_user_row(conn)
    profile = profile_state(user, include_profile=True)
    raw_profile = profile.pop("profile")
    inventory = inventory_evidence(conn)
    googleplex = googleplex_evidence(conn, inventory)
    wallet = wallet_evidence(conn)
    territory = territory_evidence(conn)
    ghost = ghostnetwork_evidence(conn)
    blockers = []
    if profile["integrity_status"] != "valid" or not profile["checksum_valid"]:
        blockers.append("current_profile_integrity_invalid")
    if wallet["balance"] is None:
        blockers.append("canonical_wallet_missing")
    if len(googleplex["recent_installs"]) != 2 or not all(
        item["canonical_inventory_match"] for item in googleplex["recent_installs"]
    ):
        blockers.append("two_recent_googleplex_installs_not_proven")
    if not googleplex["cities"]:
        blockers.append("no_canonical_travel_city_evidence")
    if ghost["active_cycle_count"] != 1 or ghost["part_count"] != 20:
        blockers.append("ghostnetwork_readiness_invalid")
    return {
        "tool_version": TOOL_VERSION,
        "command": "audit",
        "generated_at": utc_now(),
        "read_only": True,
        "reported_login": REPORTED_LOGIN,
        "canonical_username": CANONICAL_USERNAME,
        "exact_match": user["username"] == CANONICAL_USERNAME,
        "database": db_identity(conn, db_path),
        "profile": {
            **profile,
            "progression": {
                "level": raw_profile.get("level"),
                "respect": raw_profile.get("respect"),
                "exp": raw_profile.get("exp"),
            },
            "credentials_included": False,
            "full_profile_included": False,
        },
        "last_known_good": lkg_state(conn),
        "wallet": wallet,
        "inventory": inventory,
        "googleplex": googleplex,
        "territory": territory,
        "ghostnetwork": {key: value for key, value in ghost.items() if key != "anchors"},
        "session_generation": session_evidence(conn),
        "blockers": blockers,
        "ready_for_plan": not blockers,
        "heavy_profile_audit": {
            "exact_subject_full_profile_reads": 1,
            "other_profile_full_reads": 0,
            "all_profile_scans": 0,
        },
    }


def radians(value: float) -> float:
    return value * math.pi / 180.0


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6_371_000.0
    d_lat = radians(lat2 - lat1)
    d_lng = radians(lng2 - lng1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(radians(lat1)) * math.cos(radians(lat2)) * math.sin(d_lng / 2) ** 2
    return 2 * radius * math.asin(min(1.0, math.sqrt(a)))


def destination(lat: float, lng: float, distance_m: float, bearing_deg: float) -> tuple[float, float]:
    radius = 6_371_000.0
    angular = distance_m / radius
    bearing = radians(bearing_deg)
    lat1, lng1 = radians(lat), radians(lng)
    lat2 = math.asin(math.sin(lat1) * math.cos(angular) + math.cos(lat1) * math.sin(angular) * math.cos(bearing))
    lng2 = lng1 + math.atan2(math.sin(bearing) * math.sin(angular) * math.cos(lat1), math.cos(angular) - math.sin(lat1) * math.sin(lat2))
    return math.degrees(lat2), math.degrees(lng2)


def point_in_polygon(lat: float, lng: float, vertices: list[dict[str, Any]]) -> bool:
    try:
        return canonical_point_in_polygon(float(lat), float(lng), vertices)
    except (KeyError, TypeError, ValueError):
        return False


def normalized_polygon(vertices: list[dict[str, Any]]) -> list[tuple[float, float]]:
    result = []
    for vertex in vertices:
        try:
            result.append((float(vertex["lat"]), float(vertex.get("lng", vertex.get("lon")))))
        except (KeyError, TypeError, ValueError):
            return []
    return result if len(result) >= 3 else []


def orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])


def segments_intersect(
    a: tuple[float, float], b: tuple[float, float],
    c: tuple[float, float], d: tuple[float, float],
) -> bool:
    return orientation(a, b, c) * orientation(a, b, d) <= 0 and orientation(c, d, a) * orientation(c, d, b) <= 0


def polygons_overlap(first: list[dict[str, Any]], second: list[dict[str, Any]]) -> bool:
    try:
        return canonical_polygons_intersect(first, second)
    except (KeyError, TypeError, ValueError):
        return False


def recovery_targets(plan_id: str, city: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    city_key = str(city["city"]).strip().lower().replace(" ", "_")
    for index in range(PILLARS_PER_CITY):
        lat, lng = destination(float(city["lat"]), float(city["lng"]), PILLAR_RING_RADIUS_M, index * 45.0)
        target_id = "recovery_" + sha256_text(f"{plan_id}|{city_key}|{index}")[:24]
        result.append({
            "target_id": target_id,
            "lat": round(lat, 7),
            "lng": round(lng, 7),
            "label": f"RECOVERY-{city['city']}-{index + 1}",
            "name": f"Recovery pillar {city['city']} {index + 1}",
            "source_type": "sprint_130_11_recovery",
            "generated": True,
            "stationary": True,
            "recovery_plan_id": plan_id,
        })
    return result


def canonical_subject_area_preview(
    conn: sqlite3.Connection, targets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Preview the worker result from all existing and proposed pillars."""
    material = []
    for row in conn.execute(
        "SELECT lat, lng, target_json FROM captured_targets "
        "WHERE owner_username=? AND stationary=1 ORDER BY id",
        (CANONICAL_USERNAME,),
    ):
        target = loads_object(row["target_json"])
        target.setdefault("lat", float(row["lat"]))
        target.setdefault("lng", float(row["lng"]))
        material.append(target)
    material.extend(copy.deepcopy(targets or []))
    return build_canonical_player_areas(
        material,
        RECOVERY_LEVEL,
        max_exact_area_targets=TERRITORY_MAX_EXACT_AREA_TARGETS,
        max_exact_area_triangles=TERRITORY_MAX_EXACT_AREA_TRIANGLES,
    )


def canonical_area_preview_summary(areas: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "area_count": len(areas or []),
        "geometry_sha256": digest([
            {
                "vertices": area.get("vertices") or [],
                "area_size": area.get("area_size"),
                "max_edge_distance": area.get("max_edge_distance"),
            }
            for area in (areas or [])
        ]),
    }


def collision_findings(conn: sqlite3.Connection, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    existing_targets = list(conn.execute(
        "SELECT owner_username, lat, lng FROM territory_target_ownership"
    ).fetchall())
    existing_targets.extend(conn.execute(
        "SELECT owner_username, lat, lng FROM captured_targets"
    ).fetchall())
    areas = conn.execute(
        "SELECT owner_username, vertices_json FROM player_areas WHERE status='active'"
    ).fetchall()
    conflicts = conn.execute(
        "SELECT conflict_id, intersections_json, intersection_json FROM territory_conflicts "
        "WHERE status NOT IN ('resolved','closed')"
    ).fetchall()
    ghost = ghostnetwork_evidence(conn)
    planned_areas = canonical_subject_area_preview(conn, targets)
    for target in targets:
        for row in existing_targets:
            if haversine_m(target["lat"], target["lng"], float(row["lat"]), float(row["lng"])) < TARGET_CLEARANCE_M:
                findings.append({"target_id": target["target_id"], "reason": "existing_target_clearance"})
                break
        for row in areas:
            if point_in_polygon(target["lat"], target["lng"], loads_list(row["vertices_json"])):
                findings.append({"target_id": target["target_id"], "reason": "existing_territory"})
                break
        for row in conflicts:
            polygons = loads_list(row["intersections_json"]) or [loads_list(row["intersection_json"])]
            if any(point_in_polygon(target["lat"], target["lng"], polygon) for polygon in polygons if isinstance(polygon, list)):
                findings.append({"target_id": target["target_id"], "reason": "active_conflict"})
                break
        for anchor in ghost["anchors"]:
            if haversine_m(target["lat"], target["lng"], float(anchor["lat"]), float(anchor["lng"])) < GN_CLEARANCE_M:
                findings.append({"target_id": target["target_id"], "reason": "ghost_part_clearance"})
                break
    for row in existing_targets:
        if str(row["owner_username"] or "") == CANONICAL_USERNAME:
            continue
        if any(
            point_in_polygon(
                float(row["lat"]), float(row["lng"]), area.get("vertices") or []
            )
            for area in planned_areas
        ):
            findings.append({
                "target_id": "__city__",
                "reason": "foreign_target_inside_canonical_worker_area",
            })
            break
    for row in areas:
        if str(row["owner_username"] or "") == CANONICAL_USERNAME:
            continue
        vertices = loads_list(row["vertices_json"])
        if any(
            polygons_overlap(area.get("vertices") or [], vertices)
            for area in planned_areas
        ):
            findings.append({
                "target_id": "__city__",
                "reason": "canonical_worker_area_conflict:" + str(row["owner_username"] or "unknown"),
            })
            break
    for row in conflicts:
        polygons = loads_list(row["intersections_json"]) or [loads_list(row["intersection_json"])]
        if any(
            polygons_overlap(area.get("vertices") or [], polygon)
            for area in planned_areas
            for polygon in polygons
            if isinstance(polygon, list)
        ):
            findings.append({"target_id": "__city__", "reason": "active_conflict_polygon_overlap"})
            break
    for anchor in ghost["anchors"]:
        if any(
            point_in_polygon(
                float(anchor["lat"]), float(anchor["lng"]), area.get("vertices") or []
            )
            for area in planned_areas
        ):
            findings.append({
                "target_id": "__city__",
                "reason": "ghost_part_inside_canonical_worker_area",
            })
            break
    unique = {(item["target_id"], item["reason"]): item for item in findings}
    return [unique[key] for key in sorted(unique)]


def choose_recovery_city(
    conn: sqlite3.Connection, plan_id: str, evidence: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    offsets = [(0.0, 0.0)]
    for distance_m in (
        3_000.0, 6_000.0, 9_000.0, 12_000.0, 15_000.0,
        20_000.0, 30_000.0, 45_000.0, 60_000.0,
    ):
        offsets.extend((distance_m, bearing) for bearing in range(0, 360, 45))
    last_targets = []
    last_collisions = []
    for distance_m, bearing in offsets:
        if distance_m:
            center_lat, center_lng = destination(
                float(evidence["lat"]), float(evidence["lng"]), distance_m, bearing
            )
        else:
            center_lat, center_lng = float(evidence["lat"]), float(evidence["lng"])
        candidate = dict(evidence)
        candidate["lat"], candidate["lng"] = center_lat, center_lng
        targets = recovery_targets(plan_id, candidate)
        collisions = collision_findings(conn, targets)
        if not collisions:
            relocation = {
                "applied": bool(distance_m),
                "distance_m": int(distance_m),
                "bearing_deg": int(bearing),
                "evidence_center": {"lat": evidence["lat"], "lng": evidence["lng"]},
                "selected_center": {"lat": round(center_lat, 7), "lng": round(center_lng, 7)},
            }
            return relocation, targets, []
        last_targets, last_collisions = targets, collisions
    return {
        "applied": False,
        "search_exhausted": True,
        "evidence_center": {"lat": evidence["lat"], "lng": evidence["lng"]},
    }, last_targets, last_collisions


def recovery_job_id(plan_id: str, city: str) -> str:
    return "territory_rebuild_" + sha256_text(
        f"sprint_130_11|{plan_id}|{str(city).strip().lower()}"
    )[:20]


def build_plan(conn: sqlite3.Connection, db_path: str) -> dict[str, Any]:
    audit = audit_snapshot(conn, db_path)
    if audit["blockers"]:
        raise RecoveryGateError("Audit blockers: " + ", ".join(audit["blockers"]))
    identity_seed = {
        "incident": "sprint_130_11_trollu2_controlled_recovery",
        "canonical_username": CANONICAL_USERNAME,
        "before_revision": audit["profile"]["revision"],
        "before_checksum": audit["profile"]["stored_checksum"],
        "city_evidence": [
            {key: city[key] for key in ("city", "product_id", "message_id")}
            for city in audit["googleplex"]["cities"]
        ],
    }
    plan_id = "trollu2_recovery_" + digest(identity_seed)[:20]
    cities = []
    all_targets = []
    level_only_collisions = collision_findings(conn, [])
    for evidence in audit["googleplex"]["cities"]:
        if level_only_collisions:
            targets = recovery_targets(plan_id, evidence)
            collisions = collision_findings(conn, targets)
            relocation = {
                "applied": False,
                "blocked": True,
                "reason": "level_50_existing_geometry_conflict",
                "evidence_center": {
                    "lat": evidence["lat"], "lng": evidence["lng"],
                },
            }
        else:
            relocation, targets, collisions = choose_recovery_city(
                conn, plan_id, evidence
            )
        canonical_preview = canonical_subject_area_preview(conn, targets)
        cities.append({
            "city": evidence["city"],
            "center": {"lat": evidence["lat"], "lng": evidence["lng"]},
            "evidence": {key: evidence[key] for key in ("product_id", "message_id", "created_at", "provenance", "confidence")},
            "relocation": relocation,
            "pillar_count": len(targets),
            "rebuild_job_id": recovery_job_id(plan_id, evidence["city"]),
            "targets": targets,
            "canonical_worker_preview": canonical_area_preview_summary(canonical_preview),
            "collisions": collisions,
            "ready": not collisions,
        })
        all_targets.extend(targets)
    blockers = [f"city_collision:{city['city']}" for city in cities if city["collisions"]]
    if level_only_collisions:
        blockers.append("level_50_existing_geometry_conflict")
    plan = {
        "tool_version": TOOL_VERSION,
        "plan_version": 1,
        "plan_id": plan_id,
        "generated_at": utc_now(),
        "reported_login": REPORTED_LOGIN,
        "canonical_username": CANONICAL_USERNAME,
        "database_identity": audit["database"],
        "preconditions": {
            "profile_revision": audit["profile"]["revision"],
            "profile_checksum": audit["profile"]["stored_checksum"],
            "profile_integrity_status": audit["profile"]["integrity_status"],
            "wallet_balance": audit["wallet"]["balance"],
            "wallet_version": audit["wallet"]["balance_version"],
            "inventory_app_ids_sha256": audit["inventory"]["app_ids_sha256"],
            "inventory_tool_ids_sha256": audit["inventory"]["tool_ids_sha256"],
            "ghost_cycle_id": audit["ghostnetwork"]["cycle"]["cycle_id"],
            "ghost_part_count": audit["ghostnetwork"]["part_count"],
            "ghost_topology_sha256": audit["ghostnetwork"]["topology_sha256"],
            "session_generation_sha256": audit["session_generation"]["projection_sha256"],
        },
        "last_known_good_policy": {
            "use_as_recovery_source": False,
            "reason": "current_lkg_contains_canonical_mirror_keys",
            "observed": audit["last_known_good"],
        },
        "final_state": {
            "level": RECOVERY_LEVEL,
            "respect": RECOVERY_RESPECT,
            "wallet_balance": RECOVERY_BALANCE,
            "exp": "recompute_after_territory_worker",
        },
        "preserve": {
            "apps": audit["inventory"]["apps"],
            "tools": audit["inventory"]["tools"],
            "storage": audit["inventory"]["storage"],
            "recent_googleplex_installs": audit["googleplex"]["recent_installs"],
            "credentials": "unchanged",
            "session_generation": "unchanged",
            "aimed_target": "unchanged",
            "active_operations": "unchanged",
        },
        "territory_recovery": {
            "cities": cities,
            "total_pillars": len(all_targets),
            "level_50_existing_geometry_collisions": level_only_collisions,
            "grant_contract": "ownership+captured_target+rebuild_job+step_receipt_one_transaction",
            "polygon_write": False,
            "gameplay_progression_receipt": False,
        },
        "ghostnetwork_isolation": {
            "writes": 0, "events": 0, "effects": 0,
            "before": audit["ghostnetwork"],
        },
        "apply_order": [
            "validate_plan_and_before_manifest",
            "guarded_level_50",
            "atomic_city_grants_and_rebuild_jobs",
            "wait_for_plan_jobs",
            "progression_neutral_territory_stats_refresh",
            "final_settlement_50_2560_250000",
            "verify_and_manual",
            "explicit_lkg_promotion",
        ],
        "blockers": blockers,
        "ready_for_dry_run": not blockers,
        "heavy_profile_audit": audit["heavy_profile_audit"],
    }
    plan["plan_sha256"] = digest(plan)
    return plan


def load_plan(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryGateError(f"Cannot load plan: {exc}") from exc
    if not isinstance(value, dict):
        raise RecoveryGateError("Plan must be a JSON object")
    claimed = str(value.get("plan_sha256") or "")
    unsigned = dict(value)
    unsigned.pop("plan_sha256", None)
    actual = digest(unsigned)
    if not claimed or claimed != actual:
        raise RecoveryGateError("Plan SHA-256 mismatch")
    if value.get("canonical_username") != CANONICAL_USERNAME:
        raise RecoveryGateError("Plan canonical username is not allowlisted")
    if int(value.get("plan_version") or 0) != 1:
        raise RecoveryGateError("Unsupported recovery plan version")
    if value.get("tool_version") != TOOL_VERSION:
        raise RecoveryGateError("Plan was generated by a different recovery tool version")
    return value


def rows_as_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]


def plan_targets(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        target
        for city in (plan.get("territory_recovery") or {}).get("cities", [])
        for target in city.get("targets", [])
    ]


def select_by_values(
    conn: sqlite3.Connection, table: str, column: str, values: list[str]
) -> list[dict[str, Any]]:
    if not values:
        return []
    placeholders = ",".join("?" for _ in values)
    return rows_as_dicts(conn.execute(
        f'SELECT * FROM "{table}" WHERE "{column}" IN ({placeholders}) ORDER BY "{column}"',
        tuple(values),
    ).fetchall())


def build_before_manifest(
    conn: sqlite3.Connection, db_path: str, plan: dict[str, Any]
) -> dict[str, Any]:
    blockers = validate_plan_against_current(conn, db_path, plan)
    if blockers:
        raise RecoveryGateError("Cannot capture before-manifest: " + ", ".join(blockers))
    targets = plan_targets(plan)
    target_ids = [str(target["target_id"]) for target in targets]
    job_ids = [
        str(city["rebuild_job_id"])
        for city in plan["territory_recovery"]["cities"]
    ]
    captured = []
    for target in targets:
        captured.extend(rows_as_dicts(conn.execute(
            "SELECT * FROM captured_targets WHERE ROUND(lat,7)=ROUND(?,7) "
            "AND ROUND(lng,7)=ROUND(?,7)",
            (float(target["lat"]), float(target["lng"])),
        ).fetchall()))
    tables = table_names(conn)
    user_rows = rows_as_dicts(conn.execute(
        "SELECT * FROM users WHERE username=?", (CANONICAL_USERNAME,)
    ).fetchall())
    lkg_rows = rows_as_dicts(conn.execute(
        "SELECT * FROM profile_last_known_good WHERE username=?", (CANONICAL_USERNAME,)
    ).fetchall())
    wallet_rows = rows_as_dicts(conn.execute(
        "SELECT * FROM wallet_balances WHERE username=?", (CANONICAL_USERNAME,)
    ).fetchall())
    ledger_projection = rows_as_dicts(conn.execute(
        "SELECT ledger_id, event_type, amount_delta, balance_after, source, source_id, "
        "dedupe_key, created_at FROM wallet_ledger WHERE username=? ORDER BY created_at, ledger_id",
        (CANONICAL_USERNAME,),
    ).fetchall())
    event_projection = rows_as_dicts(conn.execute(
        "SELECT event_id, transaction_key, amount_delta, balance, version, reason, created_at "
        "FROM wallet_balance_events WHERE username=? ORDER BY created_at, event_id",
        (CANONICAL_USERNAME,),
    ).fetchall())
    session_rows = []
    if "session_generation_lineages" in tables:
        columns = table_columns(conn, "session_generation_lineages")
        user_column = "username" if "username" in columns else "canonical_username"
        session_rows = rows_as_dicts(conn.execute(
            f'SELECT * FROM session_generation_lineages WHERE "{user_column}"=?',
            (CANONICAL_USERNAME,),
        ).fetchall())
    manifest = {
        "tool_version": TOOL_VERSION,
        "manifest_version": 1,
        "generated_at": utc_now(),
        "sensitive": True,
        "canonical_username": CANONICAL_USERNAME,
        "plan_id": plan["plan_id"],
        "plan_sha256": plan["plan_sha256"],
        "database_identity": db_identity(conn, db_path),
        "expected_preconditions": plan["preconditions"],
        "records": {
            "users": user_rows,
            "profile_last_known_good": lkg_rows,
            "wallet_balances": wallet_rows,
            "wallet_ledger_projection_sha256": digest(ledger_projection),
            "wallet_balance_events_projection_sha256": digest(event_projection),
            "captured_targets_at_planned_coordinates": captured,
            "territory_target_ownership_for_planned_ids": select_by_values(
                conn, "territory_target_ownership", "target_id", target_ids
            ),
            "territory_rebuild_jobs_for_plan": select_by_values(
                conn, "territory_rebuild_jobs", "job_id", job_ids
            ),
            "player_areas": rows_as_dicts(conn.execute(
                "SELECT * FROM player_areas WHERE owner_username=? ORDER BY id",
                (CANONICAL_USERNAME,),
            ).fetchall()),
            "territory_area_publications": rows_as_dicts(conn.execute(
                "SELECT * FROM territory_area_publications WHERE owner_username=?",
                (CANONICAL_USERNAME,),
            ).fetchall()) if "territory_area_publications" in tables else [],
            "session_generation_lineages": session_rows,
        },
        "restore_policy": {
            "profile_revision_must_equal_receipt_revision": True,
            "wallet_version_must_equal_receipt_version": True,
            "recovery_targets_must_still_be_owned_by_subject": True,
            "later_gameplay_blocks_rollback": True,
            "wallet_rollback_is_compensating_append_only": True,
        },
    }
    if len(user_rows) != 1 or len(wallet_rows) != 1:
        raise RecoveryGateError("Before-manifest requires exactly one user and wallet row")
    if captured or manifest["records"]["territory_target_ownership_for_planned_ids"] or manifest["records"]["territory_rebuild_jobs_for_plan"]:
        raise RecoveryGateError("Planned recovery identities already exist before apply")
    manifest["manifest_sha256"] = digest(manifest)
    return manifest


def load_manifest(path: str, plan: dict[str, Any]) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecoveryGateError(f"Cannot load before-manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise RecoveryGateError("Before-manifest must be a JSON object")
    claimed = str(value.get("manifest_sha256") or "")
    unsigned = dict(value)
    unsigned.pop("manifest_sha256", None)
    if not claimed or claimed != digest(unsigned):
        raise RecoveryGateError("Before-manifest SHA-256 mismatch")
    if value.get("plan_id") != plan.get("plan_id") or value.get("plan_sha256") != plan.get("plan_sha256"):
        raise RecoveryGateError("Before-manifest belongs to another plan")
    if value.get("canonical_username") != CANONICAL_USERNAME:
        raise RecoveryGateError("Before-manifest canonical username mismatch")
    if int(value.get("manifest_version") or 0) != 1:
        raise RecoveryGateError("Unsupported before-manifest version")
    if value.get("tool_version") != TOOL_VERSION:
        raise RecoveryGateError("Before-manifest was generated by a different recovery tool version")
    records = value.get("records") or {}
    if len(records.get("users") or []) != 1 or len(records.get("wallet_balances") or []) != 1:
        raise RecoveryGateError("Before-manifest exact-account records are incomplete")
    return value


def refuse_repo_output(path: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError:
        return
    raise RecoveryGateError("Sensitive recovery artifacts must be written outside the repository")


def validate_plan_against_current(conn: sqlite3.Connection, db_path: str, plan: dict[str, Any]) -> list[str]:
    current = audit_snapshot(conn, db_path)
    expected = plan.get("preconditions") or {}
    expected_identity = plan.get("database_identity") or {}
    checks = {
        "database_name_changed": current["database"]["database_name"] != expected_identity.get("database_name"),
        "database_schema_changed": current["database"]["schema_sha256"] != expected_identity.get("schema_sha256"),
        "profile_revision_changed": current["profile"]["revision"] != expected.get("profile_revision"),
        "profile_checksum_changed": current["profile"]["stored_checksum"] != expected.get("profile_checksum"),
        "wallet_balance_changed": current["wallet"]["balance"] != expected.get("wallet_balance"),
        "wallet_version_changed": current["wallet"]["balance_version"] != expected.get("wallet_version"),
        "inventory_apps_changed": current["inventory"]["app_ids_sha256"] != expected.get("inventory_app_ids_sha256"),
        "inventory_tools_changed": current["inventory"]["tool_ids_sha256"] != expected.get("inventory_tool_ids_sha256"),
        "ghost_cycle_changed": current["ghostnetwork"]["cycle"]["cycle_id"] != expected.get("ghost_cycle_id"),
        "ghost_part_count_changed": current["ghostnetwork"]["part_count"] != expected.get("ghost_part_count"),
        "ghost_topology_changed": current["ghostnetwork"]["topology_sha256"] != expected.get("ghost_topology_sha256"),
        "session_generation_changed": current["session_generation"]["projection_sha256"] != expected.get("session_generation_sha256"),
    }
    blockers = list(current["blockers"])
    blockers.extend(key for key, failed in checks.items() if failed)
    for city in (plan.get("territory_recovery") or {}).get("cities", []):
        preview = canonical_area_preview_summary(
            canonical_subject_area_preview(conn, city.get("targets", []))
        )
        if preview != (city.get("canonical_worker_preview") or {}):
            blockers.append(f"canonical_worker_preview_changed:{city['city']}")
        blockers.extend(
            f"collision:{item['target_id']}:{item['reason']}"
            for item in collision_findings(conn, city.get("targets", []))
        )
    return sorted(set(blockers))


def recovery_receipt(conn: sqlite3.Connection, plan_id: str) -> dict[str, Any] | None:
    if RECOVERY_RECEIPTS_TABLE not in table_names(conn):
        return None
    row = conn.execute(
        f"SELECT * FROM {RECOVERY_RECEIPTS_TABLE} WHERE plan_id=?", (plan_id,)
    ).fetchone()
    if not row:
        return None
    value = dict(row)
    value["result"] = loads_object(value.pop("result_json", "{}"))
    return value


def recovery_step(conn: sqlite3.Connection, plan_id: str, step_key: str) -> dict[str, Any] | None:
    if RECOVERY_STEPS_TABLE not in table_names(conn):
        return None
    row = conn.execute(
        f"SELECT * FROM {RECOVERY_STEPS_TABLE} WHERE plan_id=? AND step_key=?",
        (plan_id, step_key),
    ).fetchone()
    if not row:
        return None
    value = dict(row)
    value["receipt"] = loads_object(value.pop("receipt_json", "{}"))
    return value


def insert_step(
    conn: sqlite3.Connection, plan_id: str, step_key: str, receipt: dict[str, Any],
    status: str = "applied",
) -> None:
    now = utc_now()
    conn.execute(
        f"""
        INSERT INTO {RECOVERY_STEPS_TABLE}
            (plan_id, step_key, status, receipt_json, created_at, updated_at, applied_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (plan_id, step_key, status, canonical_json(receipt), now, now,
         now if status == "applied" else None),
    )


def initialize_recovery_receipt(
    db_path: str, plan: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    with write_connection(db_path) as conn:
        ensure_recovery_schema(conn)
    with write_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = recovery_receipt(conn, plan["plan_id"])
        if existing:
            if (
                existing["plan_sha256"] != plan["plan_sha256"]
                or existing["before_manifest_sha256"] != manifest["manifest_sha256"]
                or existing["canonical_username"] != CANONICAL_USERNAME
            ):
                raise RecoveryGateError("Recovery plan ID already has a different durable receipt")
            return existing
        blockers = validate_plan_against_current(conn, db_path, plan)
        if blockers:
            raise RecoveryGateError("Apply preconditions changed: " + ", ".join(blockers))
        now = utc_now()
        expected = plan["preconditions"]
        conn.execute(
            f"""
            INSERT INTO {RECOVERY_RECEIPTS_TABLE}
                (plan_id, canonical_username, plan_sha256, before_manifest_sha256,
                 status, expected_before_revision, expected_before_checksum,
                 current_profile_revision, current_profile_checksum,
                 current_wallet_version, result_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, 'applying', ?, ?, ?, ?, ?, '{{}}', ?, ?)
            """,
            (
                plan["plan_id"], CANONICAL_USERNAME, plan["plan_sha256"],
                manifest["manifest_sha256"], int(expected["profile_revision"]),
                expected["profile_checksum"], int(expected["profile_revision"]),
                expected["profile_checksum"], int(expected["wallet_version"]),
                now, now,
            ),
        )
        return recovery_receipt(conn, plan["plan_id"])


def prepared_profile_update(
    conn: sqlite3.Connection, updates: dict[str, Any], wallet_balance: int
) -> dict[str, Any]:
    row = exact_user_row(conn)
    state = profile_state(row, include_profile=True)
    profile = state.pop("profile")
    if state["integrity_status"] != "valid" or not state["checksum_valid"]:
        raise RecoveryGateError("Current profile failed guarded recovery validation")
    candidate = canonical_profile_overlay(
        conn, CANONICAL_USERNAME, profile, wallet_balance
    )
    for key, value in updates.items():
        candidate[key] = copy.deepcopy(value)
    errors = validate_profile_contract(candidate, CANONICAL_USERNAME)
    if errors:
        raise RecoveryGateError("Recovery candidate invalid: " + ", ".join(errors))
    return {
        "old_revision": state["revision"],
        "old_checksum": state["stored_checksum"],
        "candidate": candidate,
        "candidate_json": canonical_json(candidate),
        "candidate_checksum": profile_checksum(candidate),
        "schema_version": state["schema_version"],
        "validation_version": state["validation_version"],
    }


def apply_level_step(db_path: str, plan: dict[str, Any]) -> dict[str, Any]:
    step_key = "profile_level_50"
    with readonly_connection(db_path) as conn:
        existing = recovery_step(conn, plan["plan_id"], step_key)
        if existing:
            return {**existing["receipt"], "duplicate": True}
        receipt = recovery_receipt(conn, plan["plan_id"])
        if not receipt or receipt["status"] not in {"applying", "awaiting_territory_jobs"}:
            raise RecoveryGateError("Recovery receipt is not writable")
        prepared = prepared_profile_update(
            conn, {"level": RECOVERY_LEVEL}, int(plan["preconditions"]["wallet_balance"])
        )
        if (
            prepared["old_revision"] != int(receipt["current_profile_revision"])
            or prepared["old_checksum"] != receipt["current_profile_checksum"]
        ):
            raise RecoveryGateError("Profile changed before level recovery step")
    now = utc_now()
    result = {
        "level": RECOVERY_LEVEL,
        "profile_revision": prepared["old_revision"] + 1,
        "profile_checksum": prepared["candidate_checksum"],
    }
    with write_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if recovery_step(conn, plan["plan_id"], step_key):
            replay = recovery_step(conn, plan["plan_id"], step_key)["receipt"]
            return {**replay, "duplicate": True}
        updated = conn.execute(
            """
            UPDATE users SET profile_json=?, updated_at=?, profile_revision=?,
                profile_schema_version=?, profile_checksum=?,
                profile_integrity_status='valid', profile_validation_version=?
            WHERE username=? AND profile_revision=? AND profile_checksum=?
            """,
            (
                prepared["candidate_json"], now, result["profile_revision"],
                prepared["schema_version"], prepared["candidate_checksum"],
                prepared["validation_version"], CANONICAL_USERNAME,
                prepared["old_revision"], prepared["old_checksum"],
            ),
        )
        if updated.rowcount != 1:
            raise RecoveryGateError("Profile CAS failed during level recovery step")
        insert_step(conn, plan["plan_id"], step_key, result)
        conn.execute(
            f"UPDATE {RECOVERY_RECEIPTS_TABLE} SET current_profile_revision=?, "
            "current_profile_checksum=?, updated_at=? WHERE plan_id=?",
            (result["profile_revision"], result["profile_checksum"], now, plan["plan_id"]),
        )
    return {**result, "duplicate": False}


def atomic_city_grant(
    db_path: str, plan: dict[str, Any], city: dict[str, Any]
) -> dict[str, Any]:
    step_key = "territory_city:" + str(city["city"]).strip().lower()
    with readonly_connection(db_path) as conn:
        existing = recovery_step(conn, plan["plan_id"], step_key)
        if existing:
            return {**existing["receipt"], "duplicate": True}
        receipt = recovery_receipt(conn, plan["plan_id"])
        level_step = recovery_step(conn, plan["plan_id"], "profile_level_50")
        if not receipt or receipt["status"] not in {"applying", "awaiting_territory_jobs"}:
            raise RecoveryGateError("Recovery receipt is not writable for city grant")
        if not level_step:
            raise RecoveryGateError("Level recovery step must precede city grant")
        collisions = collision_findings(conn, city["targets"])
        if collisions:
            raise RecoveryGateError(
                "Territory collision before city grant: " + canonical_json(collisions)
            )
    now = utc_now()
    job_id = str(city["rebuild_job_id"])
    result = {
        "city": city["city"],
        "target_ids": [target["target_id"] for target in city["targets"]],
        "rebuild_job_id": job_id,
        "pillar_count": len(city["targets"]),
    }
    with write_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if recovery_step(conn, plan["plan_id"], step_key):
            replay = recovery_step(conn, plan["plan_id"], step_key)["receipt"]
            return {**replay, "duplicate": True}
        receipt = recovery_receipt(conn, plan["plan_id"])
        if not receipt or receipt["status"] not in {"applying", "awaiting_territory_jobs"}:
            raise RecoveryGateError("Recovery receipt changed before city grant commit")
        if not recovery_step(conn, plan["plan_id"], "profile_level_50"):
            raise RecoveryGateError("Level recovery receipt missing under writer lock")
        collisions = collision_findings(conn, city["targets"])
        if collisions:
            raise RecoveryGateError(
                "Territory collision under writer lock: " + canonical_json(collisions)
            )
        for target in city["targets"]:
            payload = copy.deepcopy(target)
            payload.update({
                "owner_username": CANONICAL_USERNAME,
                "ownership_version": 1,
                "captured_at": now,
            })
            conn.execute(
                """
                INSERT INTO territory_target_ownership
                    (target_id, owner_username, ownership_version, lat, lng,
                     label, target_json, updated_at)
                VALUES (?, ?, 1, ?, ?, ?, ?, ?)
                """,
                (
                    target["target_id"], CANONICAL_USERNAME, float(target["lat"]),
                    float(target["lng"]), target["label"], canonical_json(payload), now,
                ),
            )
            conn.execute(
                """
                INSERT INTO captured_targets
                    (owner_username, lat, lng, label, name, icon, source_type,
                     generated, stationary, target_json, captured_at, updated_at)
                VALUES (?, ?, ?, ?, ?, '', 'sprint_130_11_recovery', 1, 1, ?, ?, ?)
                """,
                (
                    CANONICAL_USERNAME, float(target["lat"]), float(target["lng"]),
                    target["label"], target["name"], canonical_json(payload), now, now,
                ),
            )
        job_payload = {
            "recovery_contract": "sprint_130_11",
            "recovery_plan_id": plan["plan_id"],
            "recovery_subject": CANONICAL_USERNAME,
            "recovery_city": city["city"],
            "recovery_level": RECOVERY_LEVEL,
            "target_ids": result["target_ids"],
        }
        conn.execute(
            """
            INSERT INTO territory_rebuild_jobs
                (job_id, owner_username, reason, target_id, target_json, status,
                 created_at, updated_at)
            VALUES (?, ?, 'sprint_130_11_recovery', '', ?, 'pending', ?, ?)
            """,
            (job_id, CANONICAL_USERNAME, canonical_json(job_payload), now, now),
        )
        insert_step(conn, plan["plan_id"], step_key, result)
        conn.execute(
            f"UPDATE {RECOVERY_RECEIPTS_TABLE} SET status='awaiting_territory_jobs', "
            "updated_at=? WHERE plan_id=?",
            (now, plan["plan_id"]),
        )
    return {**result, "duplicate": False}


def plan_job_status(conn: sqlite3.Connection, plan: dict[str, Any]) -> dict[str, Any]:
    job_ids = [city["rebuild_job_id"] for city in plan["territory_recovery"]["cities"]]
    rows = select_by_values(conn, "territory_rebuild_jobs", "job_id", job_ids)
    by_id = {row["job_id"]: row for row in rows}
    missing = sorted(set(job_ids) - set(by_id))
    incomplete = [
        {"job_id": job_id, "status": by_id[job_id]["status"], "error": by_id[job_id].get("error", "")}
        for job_id in job_ids if job_id in by_id and by_id[job_id]["status"] != "complete"
    ]
    return {"job_ids": job_ids, "missing": missing, "incomplete": incomplete, "complete": not missing and not incomplete}


def territory_stats_snapshot(
    conn: sqlite3.Connection, level: int, base_profile: dict[str, Any] | None = None
) -> tuple[dict[str, Any], str]:
    rows = conn.execute(
        "SELECT id, vertices_json, area_size FROM player_areas "
        "WHERE owner_username=? AND status='active' ORDER BY id",
        (CANONICAL_USERNAME,),
    ).fetchall()
    if not rows:
        raise RecoveryGateError("Recovery territory worker produced no active areas")
    total_area = sum(float(row["area_size"] or 0) for row in rows)
    perimeter = 0.0
    edges = 0
    for row in rows:
        vertices = loads_list(row["vertices_json"])
        edges += len(vertices)
        for index, vertex in enumerate(vertices):
            next_vertex = vertices[(index + 1) % len(vertices)] if vertices else {}
            try:
                perimeter += haversine_m(
                    float(vertex["lat"]), float(vertex.get("lng", vertex.get("lon"))),
                    float(next_vertex["lat"]), float(next_vertex.get("lng", next_vertex.get("lon"))),
                )
            except (KeyError, TypeError, ValueError):
                raise RecoveryGateError("Worker published malformed recovery geometry")
    span_density = edges / max(perimeter / 100.0, 1.0)
    density_multiplier = max(0.05, min(1.0, span_density * max(1, int(level)) * 0.1))
    effective_area = total_area * density_multiplier
    profile = copy.deepcopy(base_profile) if base_profile is not None else loads_object(
        exact_user_row(conn)["profile_json"]
    )
    stats = copy.deepcopy(profile.get("territory_stats") if isinstance(profile.get("territory_stats"), dict) else {})
    baseline = float(stats.get("area_baseline") or 0)
    if ("effective_area" not in stats or baseline <= 0 or baseline > max(effective_area * 3, 1)) and effective_area > 0:
        baseline = effective_area
    next_level_area = baseline * 1.10 if baseline > 0 else 0
    captured_count = len(profile.get("hacked") or [])
    stats.update({
        "total_area": round(total_area, 2),
        "effective_area": round(effective_area, 2),
        "area_baseline": round(baseline, 2),
        "next_level_area": round(next_level_area, 2),
        "area_to_next_level": round(max(0, next_level_area - effective_area), 2),
        "clusters_count": len(rows),
        "captured_targets_count": captured_count,
        "last_area_gain": float(stats.get("last_area_gain") or 0),
        "last_effective_gain": float(stats.get("last_effective_gain") or 0),
        "total_perimeter": round(perimeter, 2),
        "edges_count": edges,
        "span_density": round(span_density, 4),
        "density_multiplier": round(density_multiplier, 4),
    })
    return stats, f"{round(effective_area, 2)} m² efektywne"


def recovery_worker_projection_assessment(
    conn: sqlite3.Connection,
    plan: dict[str, Any],
    manifest: dict[str, Any],
    receipt: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recognize one exact worker-owned profile projection after recovery."""
    receipt = receipt or recovery_receipt(conn, plan["plan_id"])
    if not receipt:
        return {"recognized": False, "reason": "recovery_receipt_missing"}
    current_state = profile_state(exact_user_row(conn), include_profile=True)
    current_profile = current_state.pop("profile")
    if (
        current_state["revision"] == int(receipt["current_profile_revision"])
        and current_state["stored_checksum"] == receipt["current_profile_checksum"]
        and current_state["checksum_valid"]
    ):
        return {
            "recognized": False,
            "reason": "profile_already_matches_receipt",
            "current": current_state,
        }
    if receipt["status"] != "awaiting_territory_jobs":
        return {"recognized": False, "reason": "receipt_not_awaiting_territory_jobs"}
    if recovery_step(conn, plan["plan_id"], "final_settlement"):
        return {"recognized": False, "reason": "final_settlement_already_exists"}
    if not plan_job_status(conn, plan)["complete"]:
        return {"recognized": False, "reason": "territory_jobs_not_complete"}
    if current_state["revision"] != int(receipt["current_profile_revision"]) + 1:
        return {"recognized": False, "reason": "projection_revision_delta_not_one"}
    if not current_state["checksum_valid"] or current_state["integrity_status"] != "valid":
        return {"recognized": False, "reason": "current_profile_integrity_invalid"}
    wallet = conn.execute(
        "SELECT balance, version FROM wallet_balances WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    if (
        not wallet
        or int(wallet["version"] or 0) != int(receipt["current_wallet_version"])
        or int(wallet["balance"] or 0) != int(plan["preconditions"]["wallet_balance"])
    ):
        return {"recognized": False, "reason": "wallet_changed_during_worker_projection"}
    pending_progression = int(conn.execute(
        "SELECT COUNT(*) FROM territory_progression_receipts "
        "WHERE actor_username=? AND status='pending'",
        (CANONICAL_USERNAME,),
    ).fetchone()[0])
    if pending_progression:
        return {"recognized": False, "reason": "pending_gameplay_progression_receipts"}

    before_user = dict(manifest["records"]["users"][0])
    before_profile = loads_object(before_user.get("profile_json"))
    if profile_checksum(before_profile) != str(before_user.get("profile_checksum") or ""):
        return {"recognized": False, "reason": "before_manifest_profile_invalid"}
    receipt_profile = canonical_profile_overlay(
        conn,
        CANONICAL_USERNAME,
        before_profile,
        int(wallet["balance"] or 0),
        exclude_recovery_plan_id=plan["plan_id"],
    )
    receipt_profile["level"] = RECOVERY_LEVEL
    reconstructed_checksum = profile_checksum(receipt_profile)
    if reconstructed_checksum != receipt["current_profile_checksum"]:
        return {
            "recognized": False,
            "reason": "receipt_profile_cannot_be_reconstructed",
            "reconstructed_checksum": reconstructed_checksum,
        }

    expected_profile = copy.deepcopy(receipt_profile)
    expected_profile["hacked"] = runtime_captured_targets_projection(
        conn, CANONICAL_USERNAME
    )
    expected_profile["captured_targets_source"] = "sqlite"
    stats, exp = territory_stats_snapshot(
        conn, RECOVERY_LEVEL, base_profile=expected_profile
    )
    expected_profile["territory_stats"] = stats
    expected_profile["exp"] = exp
    expected_checksum = profile_checksum(expected_profile)
    if expected_checksum != current_state["stored_checksum"] or expected_profile != current_profile:
        differing_fields = sorted({
            key
            for key in set(expected_profile) | set(current_profile)
            if expected_profile.get(key) != current_profile.get(key)
        })
        return {
            "recognized": False,
            "reason": "profile_is_not_exact_recovery_worker_projection",
            "expected_checksum": expected_checksum,
            "current_checksum": current_state["stored_checksum"],
            "differing_top_level_fields": differing_fields,
            "projection_diagnostics": {
                "expected_exp": expected_profile.get("exp"),
                "current_exp": current_profile.get("exp"),
                "expected_hacked_count": len(expected_profile.get("hacked") or []),
                "current_hacked_count": len(current_profile.get("hacked") or []),
                "expected_hacked_sha256": digest(expected_profile.get("hacked") or []),
                "current_hacked_sha256": digest(current_profile.get("hacked") or []),
                "expected_territory_stats_sha256": digest(
                    expected_profile.get("territory_stats") or {}
                ),
                "current_territory_stats_sha256": digest(
                    current_profile.get("territory_stats") or {}
                ),
            },
        }
    return {
        "recognized": True,
        "reason": "exact_recovery_owned_worker_projection",
        "source": "territory.conflict_finalize_profile",
        "allowed_fields": ["hacked", "captured_targets_source", "territory_stats", "exp"],
        "receipt_revision": int(receipt["current_profile_revision"]),
        "receipt_checksum": receipt["current_profile_checksum"],
        "profile_revision": current_state["revision"],
        "profile_checksum": current_state["stored_checksum"],
    }


def wallet_event_ids(plan_id: str) -> dict[str, str]:
    transaction_key = f"sprint_130_11:{plan_id}:final_wallet"
    return {
        "transaction_key": transaction_key,
        "event_id": "wallet_event_" + sha256_text(transaction_key)[:24],
        "ledger_id": "wallet_ledger_" + sha256_text(transaction_key)[:24],
        "dedupe_key": f"wallet:ledger:{CANONICAL_USERNAME}:{transaction_key}",
    }


def open_recovery_conflict_ids(
    conn: sqlite3.Connection, receipt: dict[str, Any]
) -> list[str]:
    columns = table_columns(conn, "territory_conflicts")
    required = {
        "conflict_id", "status", "source_event", "last_actor_username", "created_at",
    }
    if not required <= columns:
        return []
    return [
        str(row["conflict_id"])
        for row in conn.execute(
            "SELECT conflict_id FROM territory_conflicts "
            "WHERE status NOT IN ('resolved','closed') "
            "AND source_event='sprint_130_11_recovery' "
            "AND last_actor_username=? AND created_at>=? ORDER BY conflict_id",
            (CANONICAL_USERNAME, str(receipt["created_at"] or "")),
        )
    ]


def final_settlement(db_path: str, plan: dict[str, Any]) -> dict[str, Any]:
    step_key = "final_settlement"
    with readonly_connection(db_path) as conn:
        existing = recovery_step(conn, plan["plan_id"], step_key)
        if existing:
            return {**existing["receipt"], "duplicate": True}
        receipt = recovery_receipt(conn, plan["plan_id"])
        if not receipt:
            raise RecoveryGateError("Recovery receipt missing")
        jobs = plan_job_status(conn, plan)
        if not jobs["complete"]:
            raise RecoveryGateError("Recovery territory jobs are not complete")
        recovery_conflicts = open_recovery_conflict_ids(conn, receipt)
        if recovery_conflicts:
            raise RecoveryGateError(
                "Recovery-created conflict blocks final settlement: "
                + ", ".join(recovery_conflicts)
            )
        pending_progression = int(conn.execute(
            "SELECT COUNT(*) FROM territory_progression_receipts "
            "WHERE actor_username=? AND status='pending'", (CANONICAL_USERNAME,)
        ).fetchone()[0])
        if pending_progression:
            raise RecoveryGateError("Pending gameplay territory progression receipts block settlement")
        wallet = conn.execute(
            "SELECT balance, version FROM wallet_balances WHERE username=?",
            (CANONICAL_USERNAME,),
        ).fetchone()
        if not wallet or int(wallet["version"] or 0) != int(receipt["current_wallet_version"]):
            raise RecoveryGateError("Wallet changed before final settlement")
        stats, exp_value = territory_stats_snapshot(conn, RECOVERY_LEVEL)
        areas_sha256 = subject_areas_checksum(conn)
        prepared = prepared_profile_update(
            conn,
            {"level": RECOVERY_LEVEL, "respect": RECOVERY_RESPECT,
             "territory_stats": stats, "exp": exp_value},
            RECOVERY_BALANCE,
        )
        if (
            prepared["old_revision"] != int(receipt["current_profile_revision"])
            or prepared["old_checksum"] != receipt["current_profile_checksum"]
        ):
            raise RecoveryGateError("Profile changed before final settlement")
        wallet_before = int(wallet["balance"] or 0)
        wallet_version = int(wallet["version"] or 0)
    now = utc_now()
    ids = wallet_event_ids(plan["plan_id"])
    result = {
        "profile_revision": prepared["old_revision"] + 1,
        "profile_checksum": prepared["candidate_checksum"],
        "wallet_version": wallet_version + (0 if wallet_before == RECOVERY_BALANCE else 1),
        "wallet_balance": RECOVERY_BALANCE,
        "wallet_delta": RECOVERY_BALANCE - wallet_before,
        "level": RECOVERY_LEVEL,
        "respect": RECOVERY_RESPECT,
        "exp": exp_value,
        "territory_stats_sha256": digest(stats),
        "player_areas_sha256": areas_sha256,
        "transaction_key": ids["transaction_key"],
    }
    with write_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if recovery_step(conn, plan["plan_id"], step_key):
            replay = recovery_step(conn, plan["plan_id"], step_key)["receipt"]
            return {**replay, "duplicate": True}
        jobs = plan_job_status(conn, plan)
        if not jobs["complete"]:
            raise RecoveryGateError("Recovery jobs changed before settlement commit")
        locked_receipt = recovery_receipt(conn, plan["plan_id"])
        recovery_conflicts = open_recovery_conflict_ids(conn, locked_receipt)
        if recovery_conflicts:
            raise RecoveryGateError(
                "Recovery-created conflict blocks settlement commit: "
                + ", ".join(recovery_conflicts)
            )
        current_wallet = conn.execute(
            "SELECT balance, version FROM wallet_balances WHERE username=?",
            (CANONICAL_USERNAME,),
        ).fetchone()
        if (
            not current_wallet
            or int(current_wallet["balance"] or 0) != wallet_before
            or int(current_wallet["version"] or 0) != wallet_version
        ):
            raise RecoveryGateError("Wallet CAS failed during final settlement")
        if conn.execute(
            "SELECT 1 FROM wallet_balance_events WHERE username=? AND transaction_key=?",
            (CANONICAL_USERNAME, ids["transaction_key"]),
        ).fetchone():
            raise RecoveryGateError("Wallet receipt exists without recovery step receipt")
        if wallet_before != RECOVERY_BALANCE:
            wallet_update = conn.execute(
                "UPDATE wallet_balances SET balance=?, version=?, updated_at=? "
                "WHERE username=? AND balance=? AND version=?",
                (RECOVERY_BALANCE, result["wallet_version"], now, CANONICAL_USERNAME,
                 wallet_before, wallet_version),
            )
            if wallet_update.rowcount != 1:
                raise RecoveryGateError("Wallet CAS failed during final settlement")
        conn.execute(
            """
            INSERT INTO wallet_balance_events
                (event_id, username, transaction_key, amount_delta, balance,
                 version, reason, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'sprint_130_11.recovery', ?)
            """,
            (
                ids["event_id"], CANONICAL_USERNAME, ids["transaction_key"],
                result["wallet_delta"], RECOVERY_BALANCE, result["wallet_version"], now,
            ),
        )
        conn.execute(
            """
            INSERT INTO wallet_ledger
                (ledger_id, username, event_type, amount_delta, balance_after,
                 source, source_id, peer_username, note, dedupe_key,
                 payload_json, created_at)
            VALUES (?, ?, 'profile_recovery', ?, ?, 'sprint_130_11', ?, '',
                    'Controlled Trollu2 recovery', ?, ?, ?)
            """,
            (
                ids["ledger_id"], CANONICAL_USERNAME, result["wallet_delta"],
                RECOVERY_BALANCE, plan["plan_id"], ids["dedupe_key"],
                canonical_json({"plan_id": plan["plan_id"], "previous_balance": wallet_before}),
                now,
            ),
        )
        updated = conn.execute(
            """
            UPDATE users SET profile_json=?, updated_at=?, profile_revision=?,
                profile_schema_version=?, profile_checksum=?,
                profile_integrity_status='valid', profile_validation_version=?
            WHERE username=? AND profile_revision=? AND profile_checksum=?
            """,
            (
                prepared["candidate_json"], now, result["profile_revision"],
                prepared["schema_version"], prepared["candidate_checksum"],
                prepared["validation_version"], CANONICAL_USERNAME,
                prepared["old_revision"], prepared["old_checksum"],
            ),
        )
        if updated.rowcount != 1:
            raise RecoveryGateError("Profile CAS failed during final settlement")
        insert_step(conn, plan["plan_id"], step_key, result)
        conn.execute(
            f"""
            UPDATE {RECOVERY_RECEIPTS_TABLE}
            SET status='applied', current_profile_revision=?,
                current_profile_checksum=?, current_wallet_version=?,
                result_json=?, updated_at=?, applied_at=? WHERE plan_id=?
            """,
            (
                result["profile_revision"], result["profile_checksum"],
                result["wallet_version"], canonical_json(result), now, now,
                plan["plan_id"],
            ),
        )
    return {**result, "duplicate": False}


def subject_areas_checksum(conn: sqlite3.Connection) -> str:
    rows = rows_as_dicts(conn.execute(
        "SELECT * FROM player_areas WHERE owner_username=? ORDER BY id",
        (CANONICAL_USERNAME,),
    ).fetchall())
    return digest(rows)


def ghost_repair_reference_count(conn: sqlite3.Connection, plan_id: str) -> int:
    total = 0
    for table in sorted(name for name in table_names(conn) if name.startswith("ghost_")):
        text_columns = [
            row["name"] for row in conn.execute(f'PRAGMA table_info("{table}")')
            if str(row["type"] or "").upper().startswith("TEXT")
        ]
        for column in text_columns:
            total += int(conn.execute(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" LIKE ?',
                (f"%{plan_id}%",),
            ).fetchone()[0])
    return total


def verify_recovery(
    conn: sqlite3.Connection,
    plan: dict[str, Any],
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = []
    receipt = recovery_receipt(conn, plan["plan_id"])
    if not receipt:
        blockers.append("recovery_receipt_missing")
        return {"ok": False, "blockers": blockers, "receipt": None}
    if receipt["plan_sha256"] != plan["plan_sha256"]:
        blockers.append("receipt_plan_checksum_mismatch")
    if receipt["canonical_username"] != CANONICAL_USERNAME:
        blockers.append("receipt_username_mismatch")
    jobs = plan_job_status(conn, plan)
    if not jobs["complete"]:
        blockers.append("territory_jobs_not_complete")
    profile_row = exact_user_row(conn)
    state = profile_state(profile_row, include_profile=True)
    profile = state.pop("profile")
    projection = None
    receipt_profile_matches = (
        state["revision"] == int(receipt["current_profile_revision"])
        and state["stored_checksum"] == receipt["current_profile_checksum"]
        and state["checksum_valid"]
    )
    if not receipt_profile_matches and manifest is not None:
        projection = recovery_worker_projection_assessment(
            conn, plan, manifest, receipt
        )
        receipt_profile_matches = bool(projection.get("recognized"))
    if not receipt_profile_matches and state["revision"] != int(receipt["current_profile_revision"]):
        blockers.append("profile_revision_differs_from_receipt")
    if not receipt_profile_matches and (
        state["stored_checksum"] != receipt["current_profile_checksum"]
        or not state["checksum_valid"]
    ):
        blockers.append("profile_checksum_differs_from_receipt")
    conflict_analysis = None
    if manifest is not None:
        conflict_analysis = recovery_conflict_cleanup_analysis(
            conn, plan, manifest, receipt
        )
        blockers.extend(conflict_analysis.get("blockers") or [])
        blockers.extend(
            "recovery_created_conflict:" + conflict_id
            for conflict_id in (conflict_analysis.get("conflict_ids") or [])
        )
    expected_final = receipt["status"] in {"applied", "promoted"}
    if expected_final:
        if int(profile.get("level") or 0) != RECOVERY_LEVEL:
            blockers.append("level_not_50")
        if int(profile.get("respect") or 0) != RECOVERY_RESPECT:
            blockers.append("respect_not_2560")
        if str(profile.get("exp") or "") != str((receipt["result"] or {}).get("exp") or ""):
            blockers.append("exp_projection_mismatch")
    wallet = conn.execute(
        "SELECT balance, version FROM wallet_balances WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    if not wallet:
        blockers.append("wallet_missing")
    else:
        if int(wallet["version"] or 0) != int(receipt["current_wallet_version"]):
            blockers.append("wallet_version_differs_from_receipt")
        if expected_final and int(wallet["balance"] or 0) != RECOVERY_BALANCE:
            blockers.append("wallet_not_250000")
        if int(profile.get("hackcoins") or 0) != int(wallet["balance"] or 0):
            blockers.append("wallet_profile_mirror_mismatch")
    ids = wallet_event_ids(plan["plan_id"])
    if expected_final:
        event_count = int(conn.execute(
            "SELECT COUNT(*) FROM wallet_balance_events WHERE username=? AND transaction_key=?",
            (CANONICAL_USERNAME, ids["transaction_key"]),
        ).fetchone()[0])
        ledger_count = int(conn.execute(
            "SELECT COUNT(*) FROM wallet_ledger WHERE username=? AND dedupe_key=?",
            (CANONICAL_USERNAME, ids["dedupe_key"]),
        ).fetchone()[0])
        if event_count != 1 or ledger_count != 1:
            blockers.append("wallet_exactly_once_failed")
    for target in plan_targets(plan):
        ownership = conn.execute(
            "SELECT owner_username, ownership_version FROM territory_target_ownership WHERE target_id=?",
            (target["target_id"],),
        ).fetchone()
        captured = conn.execute(
            "SELECT stationary, target_json FROM captured_targets WHERE owner_username=? "
            "AND ROUND(lat,7)=ROUND(?,7) AND ROUND(lng,7)=ROUND(?,7)",
            (CANONICAL_USERNAME, float(target["lat"]), float(target["lng"])),
        ).fetchone()
        if not ownership or ownership["owner_username"] != CANONICAL_USERNAME or int(ownership["ownership_version"] or 0) != 1:
            blockers.append("recovery_ownership_invalid:" + target["target_id"])
        if not captured or int(captured["stationary"] or 0) != 1:
            blockers.append("recovery_captured_target_invalid:" + target["target_id"])
        elif loads_object(captured["target_json"]).get("recovery_plan_id") != plan["plan_id"]:
            blockers.append("recovery_target_provenance_missing:" + target["target_id"])
    pending_progression = int(conn.execute(
        "SELECT COUNT(*) FROM territory_progression_receipts "
        "WHERE actor_username=? AND status='pending'", (CANONICAL_USERNAME,)
    ).fetchone()[0])
    if pending_progression:
        blockers.append("pending_gameplay_progression_receipts")
    ghost = ghostnetwork_evidence(conn)
    if ghost["active_cycle_count"] != 1 or ghost["part_count"] != 20:
        blockers.append("ghostnetwork_readiness_invalid")
    ghost_refs = ghost_repair_reference_count(conn, plan["plan_id"])
    if ghost_refs:
        blockers.append("ghostnetwork_recovery_source_detected")
    promoted = recovery_step(conn, plan["plan_id"], "lkg_promotion")
    if receipt["status"] == "promoted":
        lkg = lkg_state(conn)
        if not promoted or not lkg.get("usable_as_recovery_source"):
            blockers.append("verified_lkg_promotion_invalid")
        elif lkg.get("revision") != state["revision"]:
            blockers.append("lkg_revision_mismatch")
    return {
        "ok": not blockers,
        "blockers": sorted(set(blockers)),
        "receipt_status": receipt["status"],
        "profile": {
            "revision": state["revision"], "checksum": state["stored_checksum"],
            "level": profile.get("level"), "respect": profile.get("respect"),
            "exp": profile.get("exp"),
        },
        "wallet": {
            "balance": int(wallet["balance"] or 0) if wallet else None,
            "version": int(wallet["version"] or 0) if wallet else None,
        },
        "territory_jobs": jobs,
        "recovery_targets": len(plan_targets(plan)),
        "pending_gameplay_progression_receipts": pending_progression,
        "ghostnetwork": {
            "cycle_id": ghost["cycle"]["cycle_id"],
            "part_count": ghost["part_count"],
            "recovery_reference_count": ghost_refs,
        },
        "lkg_promoted": bool(promoted),
        "recognized_worker_projection": projection,
        "recovery_conflicts": conflict_analysis,
    }


_LKG_SENSITIVE = {"password", "salt", "cookie", "cookies", "session", "session_id", "session_token", "token", "access_token", "refresh_token"}
_LKG_TRANSIENT = {"launch_queue"}
_LKG_CANONICAL = {
    "apps", "files", "hackcoins", "hacked", "operations",
    "storage_capacity", "storage_used", "storage_unit", "storage_upgrades",
    "googleplex_products", "storage_soft_limit", "storage_over_limit",
}
_LKG_TERRITORY = {"areas", "player_areas", "territory"}
_LKG_GEOMETRY = {"geometry", "polygon", "polygons", "coordinates"}


def lkg_snapshot_value(value: Any, top_level: bool = False) -> Any:
    if isinstance(value, dict):
        snapshot = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            lowered = key.lower()
            if lowered in _LKG_SENSITIVE or lowered in _LKG_GEOMETRY:
                continue
            if top_level and (lowered in _LKG_TRANSIENT or lowered in _LKG_CANONICAL or lowered in _LKG_TERRITORY):
                continue
            snapshot[key] = lkg_snapshot_value(item)
        return snapshot
    if isinstance(value, list):
        return [lkg_snapshot_value(item) for item in value]
    return copy.deepcopy(value)


def promote_lkg(db_path: str, plan: dict[str, Any], final_checksum: str) -> dict[str, Any]:
    with readonly_connection(db_path) as conn:
        verification = verify_recovery(conn, plan)
        if not verification["ok"]:
            raise RecoveryGateError("Cannot promote LKG: " + ", ".join(verification["blockers"]))
        receipt = recovery_receipt(conn, plan["plan_id"])
        if receipt["status"] not in {"applied", "promoted"}:
            raise RecoveryGateError("Recovery is not fully applied")
        existing = recovery_step(conn, plan["plan_id"], "lkg_promotion")
        if existing:
            return {**existing["receipt"], "duplicate": True}
        row = exact_user_row(conn)
        state = profile_state(row, include_profile=True)
        profile = state.pop("profile")
        if state["stored_checksum"] != str(final_checksum or ""):
            raise RecoveryGateError("--final-checksum does not match verified profile")
        snapshot = lkg_snapshot_value(profile, top_level=True)
        snapshot_json = canonical_json(snapshot)
        snapshot_checksum = sha256_text(snapshot_json)
    now = utc_now()
    result = {
        "profile_revision": state["revision"],
        "profile_checksum": state["stored_checksum"],
        "lkg_checksum": snapshot_checksum,
    }
    with write_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if recovery_step(conn, plan["plan_id"], "lkg_promotion"):
            replay = recovery_step(conn, plan["plan_id"], "lkg_promotion")["receipt"]
            return {**replay, "duplicate": True}
        current = profile_state(exact_user_row(conn))
        if current["revision"] != state["revision"] or current["stored_checksum"] != state["stored_checksum"]:
            raise RecoveryGateError("Profile changed before LKG promotion")
        conn.execute(
            """
            INSERT INTO profile_last_known_good
                (username, profile_revision, schema_version, snapshot_json,
                 checksum, source, created_at, validation_version)
            VALUES (?, ?, ?, ?, ?, 'sprint_130_11.verified_recovery', ?, ?)
            ON CONFLICT(username) DO UPDATE SET
                profile_revision=excluded.profile_revision,
                schema_version=excluded.schema_version,
                snapshot_json=excluded.snapshot_json,
                checksum=excluded.checksum,
                source=excluded.source,
                created_at=excluded.created_at,
                validation_version=excluded.validation_version
            """,
            (
                CANONICAL_USERNAME, state["revision"], state["schema_version"],
                snapshot_json, snapshot_checksum, now, state["validation_version"],
            ),
        )
        insert_step(conn, plan["plan_id"], "lkg_promotion", result)
        conn.execute(
            f"UPDATE {RECOVERY_RECEIPTS_TABLE} SET status='promoted', promoted_at=?, "
            "updated_at=? WHERE plan_id=?",
            (now, now, plan["plan_id"]),
        )
    return {**result, "duplicate": False}


def insert_rows(conn: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    available = table_columns(conn, table)
    for row in rows:
        filtered = {key: value for key, value in row.items() if key in available}
        if not filtered:
            continue
        columns = list(filtered)
        placeholders = ",".join("?" for _ in columns)
        conn.execute(
            f'INSERT INTO "{table}" ({",".join(columns)}) VALUES ({placeholders})',
            tuple(filtered[column] for column in columns),
        )


def recovery_conflict_cleanup_analysis(
    conn: sqlite3.Connection,
    plan: dict[str, Any],
    manifest: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Find only untouched conflict artifacts caused by this recovery plan."""
    columns = table_columns(conn, "territory_conflicts")
    required = {
        "conflict_id", "participants_json", "targets_json", "status",
        "source_event", "last_actor_username", "created_at",
    }
    if not required <= columns:
        return {
            "conflict_ids": [],
            "blockers": ["recovery_conflict_cleanup_schema_unsupported"],
            "schema_supported": False,
        }
    planned_targets = plan_targets(plan)
    plan_target_ids = {str(item["target_id"]) for item in planned_targets}
    before_area_ids = {
        str(item.get("id"))
        for item in (manifest.get("records") or {}).get("player_areas", [])
        if item.get("id") is not None
    }
    current_area_ids = {
        str(row["id"])
        for row in conn.execute(
            "SELECT id FROM player_areas WHERE owner_username=?",
            (CANONICAL_USERNAME,),
        )
    }
    recovery_area_ids = current_area_ids - before_area_ids

    def recovery_target_match(payload: dict[str, Any]) -> str:
        target = payload.get("target") if isinstance(payload.get("target"), dict) else payload
        target_id = str(payload.get("target_id") or target.get("target_id") or "")
        if target_id in plan_target_ids:
            return target_id
        try:
            lat = round(float(target.get("lat")), 7)
            lng = round(float(target.get("lng", target.get("lon"))), 7)
        except (TypeError, ValueError):
            return ""
        label = str(target.get("label") or target.get("name") or "")
        for planned in planned_targets:
            if (
                lat == round(float(planned["lat"]), 7)
                and lng == round(float(planned["lng"]), 7)
                and label in {str(planned["label"]), str(planned["name"])}
            ):
                return str(planned["target_id"])
        return ""
    open_rows = conn.execute(
        "SELECT * FROM territory_conflicts "
        "WHERE status NOT IN ('resolved','closed') ORDER BY created_at, conflict_id"
    ).fetchall()
    candidates = []
    blockers = []
    for row in open_rows:
        participants = set(loads_list(row["participants_json"]))
        if CANONICAL_USERNAME not in participants:
            continue
        conflict_id = str(row["conflict_id"] or "")
        linked_area_ids = {
            str(item) for item in loads_list(row["area_ids_json"])
            if str(item) in recovery_area_ids
        } if "area_ids_json" in row.keys() else set()
        source_event = str(row["source_event"] or "")
        created_after_receipt = (
            str(row["created_at"] or "") >= str(receipt["created_at"] or "")
        )
        if source_event != "sprint_130_11_recovery" and not created_after_receipt:
            # A conflict predating the signed recovery receipt is outside this
            # cleanup's authority and remains untouched.
            continue
        provenance_ok = (
            source_event == "sprint_130_11_recovery"
            and str(row["last_actor_username"] or "") == CANONICAL_USERNAME
            and created_after_receipt
        )
        pillar_rows = []
        if "territory_conflict_pillars" in table_names(conn):
            pillar_rows = conn.execute(
                "SELECT * FROM territory_conflict_pillars WHERE conflict_id=? ORDER BY id",
                (conflict_id,),
            ).fetchall()
        linked_ids = {
            str(item["target_id"])
            for item in pillar_rows
            if str(item["target_id"] or "") in plan_target_ids
        }
        for pillar in pillar_rows:
            matched = recovery_target_match(loads_object(pillar["public_target_json"]))
            if matched:
                linked_ids.add(matched)
        if not linked_ids:
            for item in loads_list(row["targets_json"]):
                if not isinstance(item, dict):
                    continue
                matched = recovery_target_match(item)
                if matched:
                    linked_ids.add(matched)
        if not provenance_ok or not (linked_ids or linked_area_ids):
            blockers.append("unattributed_open_conflict:" + (conflict_id or "unknown"))
            continue
        if any(
            int(item["captured"] or 0)
            or str(item["status"] or "") not in {"", "contested", "active"}
            for item in pillar_rows
        ):
            blockers.append("recovery_conflict_has_gameplay:" + conflict_id)
            continue
        if "territory_conflict_events" in table_names(conn):
            event_rows = conn.execute(
                "SELECT event_type, action_id, actor_username FROM territory_conflict_events "
                "WHERE conflict_id=?",
                (conflict_id,),
            ).fetchall()
            if any(
                str(item["action_id"] or "").strip()
                or "captur" in str(item["event_type"] or "").lower()
                or "reward" in str(item["event_type"] or "").lower()
                for item in event_rows
            ):
                blockers.append("recovery_conflict_has_player_event:" + conflict_id)
                continue
        if {
            "territory_conflict_engagements", "territory_conflict_engagement_members"
        } <= table_names(conn):
            engagement = conn.execute(
                "SELECT e.engagement_id FROM territory_conflict_engagement_members m "
                "JOIN territory_conflict_engagements e ON e.engagement_id=m.engagement_id "
                "WHERE m.conflict_id=? AND e.status NOT IN ('resolved','closed') LIMIT 1",
                (conflict_id,),
            ).fetchone()
            if engagement:
                blockers.append(
                    "recovery_conflict_joined_engagement:"
                    + conflict_id + ":" + str(engagement["engagement_id"])
                )
                continue
        candidates.append({
            "conflict_id": conflict_id,
            "participants": sorted(str(item) for item in participants if item),
            "recovery_target_ids": sorted(linked_ids),
            "recovery_area_ids": sorted(linked_area_ids),
            "conflict_version": int(row["conflict_version"] or 0)
                if "conflict_version" in row.keys() else 0,
        })
    return {
        "conflict_ids": [item["conflict_id"] for item in candidates],
        "conflicts": candidates,
        "blockers": sorted(set(blockers)),
        "schema_supported": True,
    }


def queue_recovery_conflict_cleanup(
    conn: sqlite3.Connection, conflicts: list[dict[str, Any]], now: str
) -> None:
    """Queue canonical no-front publication; retain immutable conflict history."""
    for item in conflicts or []:
        conflict_id = str(item["conflict_id"])
        next_version = max(1, int(item.get("conflict_version") or 0) + 1)
        conn.execute(
            "UPDATE territory_conflicts SET status='changing', conflict_version=?, "
            "geometry_status='dirty', resolution_reason='controlled_recovery_rollback', "
            "last_actor_username=?, source_event='sprint_130_11_rollback', "
            "resolved_at=NULL, updated_at=? WHERE conflict_id=?",
            (next_version, CANONICAL_USERNAME, now, conflict_id),
        )
        existing = conn.execute(
            "SELECT status, requested_version FROM territory_conflict_rebuilds "
            "WHERE conflict_id=?",
            (conflict_id,),
        ).fetchone()
        if existing:
            if str(existing["status"] or "") == "running":
                raise RecoveryGateError(
                    "Recovery conflict rebuild is currently running: " + conflict_id
                )
            conn.execute(
                "UPDATE territory_conflict_rebuilds SET requested_version=?, status='pending', "
                "reason='sprint_130_11_rollback', lease_owner='', lease_until=NULL, "
                "requested_at=?, updated_at=? WHERE conflict_id=?",
                (max(next_version, int(existing["requested_version"] or 0)), now, now, conflict_id),
            )
        else:
            conn.execute(
                "INSERT INTO territory_conflict_rebuilds "
                "(conflict_id, requested_version, status, reason, requested_at, updated_at) "
                "VALUES (?, ?, 'pending', 'sprint_130_11_rollback', ?, ?)",
                (conflict_id, next_version, now, now),
            )


def rollback_recovery(
    db_path: str, plan: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    with readonly_connection(db_path) as conn:
        receipt = recovery_receipt(conn, plan["plan_id"])
        if not receipt:
            raise RecoveryGateError("Recovery receipt missing")
        existing = recovery_step(conn, plan["plan_id"], "rollback")
        if existing:
            return {**existing["receipt"], "duplicate": True}
        if receipt["status"] == "rolled_back":
            raise RecoveryGateError("Receipt is rolled back without rollback step")
        current = profile_state(exact_user_row(conn))
        worker_projection = None
        if (
            current["revision"] != int(receipt["current_profile_revision"])
            or current["stored_checksum"] != receipt["current_profile_checksum"]
        ):
            worker_projection = recovery_worker_projection_assessment(
                conn, plan, manifest, receipt
            )
            if not worker_projection.get("recognized"):
                raise RecoveryGateError(
                    "Later profile gameplay blocks rollback: "
                    + str(worker_projection.get("reason") or "projection_not_recognized")
                )
        wallet = conn.execute(
            "SELECT balance, version FROM wallet_balances WHERE username=?", (CANONICAL_USERNAME,)
        ).fetchone()
        if not wallet or int(wallet["version"] or 0) != int(receipt["current_wallet_version"]):
            raise RecoveryGateError("Later wallet gameplay blocks rollback")
        for target in plan_targets(plan):
            row = conn.execute(
                "SELECT owner_username, ownership_version FROM territory_target_ownership WHERE target_id=?",
                (target["target_id"],),
            ).fetchone()
            if row and (row["owner_username"] != CANONICAL_USERNAME or int(row["ownership_version"] or 0) != 1):
                raise RecoveryGateError("Later territory gameplay blocks rollback")
            captured = conn.execute(
                "SELECT target_json FROM captured_targets WHERE owner_username=? "
                "AND ROUND(lat,7)=ROUND(?,7) AND ROUND(lng,7)=ROUND(?,7)",
                (CANONICAL_USERNAME, float(target["lat"]), float(target["lng"])),
            ).fetchone()
            if not captured or loads_object(captured["target_json"]).get("recovery_plan_id") != plan["plan_id"]:
                raise RecoveryGateError("Recovery target provenance changed before rollback")
        final_step = recovery_step(conn, plan["plan_id"], "final_settlement")
        if final_step and final_step["receipt"].get("player_areas_sha256"):
            if subject_areas_checksum(conn) != final_step["receipt"]["player_areas_sha256"]:
                raise RecoveryGateError("Later territory geometry blocks rollback")
        conflict_cleanup = recovery_conflict_cleanup_analysis(
            conn, plan, manifest, receipt
        )
        if conflict_cleanup["blockers"]:
            raise RecoveryGateError(
                "Recovery conflict cleanup blocked: "
                + ", ".join(conflict_cleanup["blockers"])
            )
        before_user = dict(manifest["records"]["users"][0])
        before_profile = loads_object(before_user.get("profile_json"))
        before_wallet = dict(manifest["records"]["wallet_balances"][0])
        errors = validate_profile_contract(before_profile, CANONICAL_USERNAME)
        if errors or profile_checksum(before_profile) != str(before_user.get("profile_checksum") or ""):
            raise RecoveryGateError("Before-manifest profile cannot be restored")
        rollback_revision = current["revision"] + 1
        rollback_checksum = profile_checksum(before_profile)
        rollback_wallet_balance = int(before_wallet["balance"] or 0)
        rollback_wallet_version = int(wallet["version"] or 0) + (
            0 if int(wallet["balance"] or 0) == rollback_wallet_balance else 1
        )
    now = utc_now()
    rollback_key = f"sprint_130_11:{plan['plan_id']}:rollback_wallet"
    rollback_event_id = "wallet_event_" + sha256_text(rollback_key)[:24]
    rollback_ledger_id = "wallet_ledger_" + sha256_text(rollback_key)[:24]
    rollback_job_id = "territory_rebuild_" + sha256_text(
        f"sprint_130_11|{plan['plan_id']}|rollback"
    )[:20]
    result = {
        "profile_revision": rollback_revision,
        "profile_checksum": rollback_checksum,
        "wallet_balance": rollback_wallet_balance,
        "wallet_version": rollback_wallet_version,
        "territory_rebuild_job_id": rollback_job_id,
        "recognized_worker_projection": worker_projection,
        "conflict_cleanup": conflict_cleanup,
    }
    with write_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if recovery_step(conn, plan["plan_id"], "rollback"):
            replay = recovery_step(conn, plan["plan_id"], "rollback")["receipt"]
            return {**replay, "duplicate": True}
        locked = profile_state(exact_user_row(conn))
        if locked["revision"] != current["revision"] or locked["stored_checksum"] != current["stored_checksum"]:
            raise RecoveryGateError("Profile changed before rollback commit")
        if worker_projection and worker_projection.get("recognized"):
            locked_projection = recovery_worker_projection_assessment(
                conn, plan, manifest, recovery_receipt(conn, plan["plan_id"])
            )
            if not locked_projection.get("recognized"):
                raise RecoveryGateError(
                    "Recovery worker projection changed before rollback commit"
                )
            if not recovery_step(conn, plan["plan_id"], "worker_profile_projection"):
                insert_step(
                    conn,
                    plan["plan_id"],
                    "worker_profile_projection",
                    locked_projection,
                )
            conn.execute(
                f"UPDATE {RECOVERY_RECEIPTS_TABLE} SET current_profile_revision=?, "
                "current_profile_checksum=?, updated_at=? WHERE plan_id=?",
                (
                    locked["revision"], locked["stored_checksum"], now,
                    plan["plan_id"],
                ),
            )
        locked_wallet = conn.execute(
            "SELECT balance, version FROM wallet_balances WHERE username=?", (CANONICAL_USERNAME,)
        ).fetchone()
        if int(locked_wallet["version"] or 0) != int(wallet["version"] or 0):
            raise RecoveryGateError("Wallet changed before rollback commit")
        for target in plan_targets(plan):
            conn.execute("DELETE FROM territory_target_ownership WHERE target_id=?", (target["target_id"],))
            conn.execute(
                "DELETE FROM captured_targets WHERE owner_username=? "
                "AND ROUND(lat,7)=ROUND(?,7) AND ROUND(lng,7)=ROUND(?,7)",
                (CANONICAL_USERNAME, float(target["lat"]), float(target["lng"])),
            )
        conn.execute("DELETE FROM player_areas WHERE owner_username=?", (CANONICAL_USERNAME,))
        insert_rows(conn, "player_areas", manifest["records"].get("player_areas") or [])
        if "territory_area_publications" in table_names(conn):
            conn.execute("DELETE FROM territory_area_publications WHERE owner_username=?", (CANONICAL_USERNAME,))
            insert_rows(conn, "territory_area_publications", manifest["records"].get("territory_area_publications") or [])
        queue_recovery_conflict_cleanup(
            conn, conflict_cleanup.get("conflicts") or [], now
        )
        wallet_before = int(locked_wallet["balance"] or 0)
        if wallet_before != rollback_wallet_balance:
            conn.execute(
                "UPDATE wallet_balances SET balance=?, version=?, updated_at=? "
                "WHERE username=? AND balance=? AND version=?",
                (rollback_wallet_balance, rollback_wallet_version, now,
                 CANONICAL_USERNAME, wallet_before, int(locked_wallet["version"] or 0)),
            )
            conn.execute(
                "INSERT INTO wallet_balance_events "
                "(event_id, username, transaction_key, amount_delta, balance, version, reason, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, 'sprint_130_11.rollback', ?)",
                (rollback_event_id, CANONICAL_USERNAME, rollback_key,
                 rollback_wallet_balance - wallet_before, rollback_wallet_balance,
                 rollback_wallet_version, now),
            )
            conn.execute(
                "INSERT INTO wallet_ledger "
                "(ledger_id, username, event_type, amount_delta, balance_after, source, source_id, "
                "peer_username, note, dedupe_key, payload_json, created_at) "
                "VALUES (?, ?, 'profile_recovery_rollback', ?, ?, 'sprint_130_11', ?, '', "
                "'Controlled recovery rollback', ?, ?, ?)",
                (rollback_ledger_id, CANONICAL_USERNAME, rollback_wallet_balance - wallet_before,
                 rollback_wallet_balance, plan["plan_id"],
                 f"wallet:ledger:{CANONICAL_USERNAME}:{rollback_key}",
                 canonical_json({"plan_id": plan["plan_id"]}), now),
            )
        restored = conn.execute(
            "UPDATE users SET profile_json=?, updated_at=?, profile_revision=?, "
            "profile_schema_version=?, profile_checksum=?, profile_integrity_status='valid', "
            "profile_validation_version=? WHERE username=? AND profile_revision=? AND profile_checksum=?",
            (
                canonical_json(before_profile), now, rollback_revision,
                int(before_user.get("profile_schema_version") or 1), rollback_checksum,
                int(before_user.get("profile_validation_version") or 1), CANONICAL_USERNAME,
                current["revision"], current["stored_checksum"],
            ),
        )
        if restored.rowcount != 1:
            raise RecoveryGateError("Profile CAS failed during rollback")
        conn.execute("DELETE FROM profile_last_known_good WHERE username=?", (CANONICAL_USERNAME,))
        insert_rows(conn, "profile_last_known_good", manifest["records"].get("profile_last_known_good") or [])
        conn.execute(
            "INSERT INTO territory_rebuild_jobs "
            "(job_id, owner_username, reason, target_id, target_json, status, created_at, updated_at) "
            "VALUES (?, ?, 'sprint_130_11_rollback', '', ?, 'pending', ?, ?)",
            (rollback_job_id, CANONICAL_USERNAME,
             canonical_json({
                 "recovery_contract": "sprint_130_11",
                 "recovery_plan_id": plan["plan_id"],
                 "recovery_subject": CANONICAL_USERNAME,
                 "recovery_level": int(before_profile["level"]),
                 "rollback": True,
             }),
             now, now),
        )
        insert_step(conn, plan["plan_id"], "rollback", result)
        conn.execute(
            f"UPDATE {RECOVERY_RECEIPTS_TABLE} SET status='rolled_back', "
            "current_profile_revision=?, current_profile_checksum=?, current_wallet_version=?, "
            "updated_at=?, rolled_back_at=? WHERE plan_id=?",
            (rollback_revision, rollback_checksum, rollback_wallet_version, now, now, plan["plan_id"]),
        )
    return {**result, "duplicate": False}


def verify_rollback(
    conn: sqlite3.Connection, plan: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    blockers = []
    receipt = recovery_receipt(conn, plan["plan_id"])
    step = recovery_step(conn, plan["plan_id"], "rollback")
    if not receipt or receipt["status"] != "rolled_back":
        blockers.append("recovery_receipt_not_rolled_back")
    if not step:
        blockers.append("rollback_step_missing")
        return {"ok": False, "blockers": blockers}
    result = step["receipt"]
    state = profile_state(exact_user_row(conn), include_profile=True)
    profile = state.pop("profile")
    before_user = dict(manifest["records"]["users"][0])
    before_profile = loads_object(before_user.get("profile_json"))
    if profile != before_profile:
        blockers.append("profile_not_restored_from_before_manifest")
    if (
        not state["checksum_valid"]
        or state["stored_checksum"] != result.get("profile_checksum")
        or state["revision"] != int(result.get("profile_revision") or -1)
    ):
        blockers.append("rollback_profile_receipt_mismatch")
    before_wallet = dict(manifest["records"]["wallet_balances"][0])
    wallet = conn.execute(
        "SELECT balance, version FROM wallet_balances WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    if (
        not wallet
        or int(wallet["balance"] or 0) != int(before_wallet["balance"] or 0)
        or int(wallet["version"] or 0) != int(result.get("wallet_version") or -1)
    ):
        blockers.append("rollback_wallet_mismatch")
    for target in plan_targets(plan):
        ownership = conn.execute(
            "SELECT 1 FROM territory_target_ownership WHERE target_id=?",
            (target["target_id"],),
        ).fetchone()
        captured = conn.execute(
            "SELECT 1 FROM captured_targets WHERE owner_username=? "
            "AND ROUND(lat,7)=ROUND(?,7) AND ROUND(lng,7)=ROUND(?,7)",
            (CANONICAL_USERNAME, float(target["lat"]), float(target["lng"])),
        ).fetchone()
        if ownership or captured:
            blockers.append("recovery_grant_still_present:" + target["target_id"])
    rollback_job_id = str(result.get("territory_rebuild_job_id") or "")
    rollback_job = conn.execute(
        "SELECT status, error FROM territory_rebuild_jobs WHERE job_id=?",
        (rollback_job_id,),
    ).fetchone() if rollback_job_id else None
    if not rollback_job or str(rollback_job["status"] or "") != "complete":
        blockers.append("rollback_territory_job_not_complete")
    conflict_ids = list(
        ((result.get("conflict_cleanup") or {}).get("conflict_ids") or [])
    )
    conflict_statuses = []
    for conflict_id in conflict_ids:
        conflict = conn.execute(
            "SELECT status, geometry_status FROM territory_conflicts WHERE conflict_id=?",
            (conflict_id,),
        ).fetchone()
        active_fronts = int(conn.execute(
            "SELECT COUNT(*) FROM territory_conflict_fronts "
            "WHERE conflict_id=? AND status='active'",
            (conflict_id,),
        ).fetchone()[0]) if "territory_conflict_fronts" in table_names(conn) else 0
        rebuild = conn.execute(
            "SELECT status FROM territory_conflict_rebuilds WHERE conflict_id=?",
            (conflict_id,),
        ).fetchone() if "territory_conflict_rebuilds" in table_names(conn) else None
        conflict_statuses.append({
            "conflict_id": conflict_id,
            "status": conflict["status"] if conflict else None,
            "geometry_status": conflict["geometry_status"] if conflict else None,
            "active_fronts": active_fronts,
            "rebuild_status": rebuild["status"] if rebuild else None,
        })
        if (
            not conflict
            or str(conflict["status"] or "") not in {"resolved", "closed"}
            or active_fronts
            or not rebuild
            or str(rebuild["status"] or "") != "complete"
        ):
            blockers.append("recovery_conflict_not_clean:" + conflict_id)
    ghost = ghostnetwork_evidence(conn)
    ghost_refs = ghost_repair_reference_count(conn, plan["plan_id"])
    if ghost["active_cycle_count"] != 1 or ghost["part_count"] != 20:
        blockers.append("ghostnetwork_readiness_invalid")
    if ghost_refs:
        blockers.append("ghostnetwork_recovery_source_detected")
    return {
        "ok": not blockers,
        "blockers": sorted(set(blockers)),
        "receipt_status": receipt["status"] if receipt else None,
        "profile": {
            "revision": state["revision"],
            "checksum": state["stored_checksum"],
            "restored": profile == before_profile,
        },
        "wallet": {
            "balance": int(wallet["balance"] or 0) if wallet else None,
            "version": int(wallet["version"] or 0) if wallet else None,
        },
        "territory_job": dict(rollback_job) if rollback_job else None,
        "conflicts": conflict_statuses,
        "ghostnetwork": {
            "cycle_id": ghost["cycle"]["cycle_id"],
            "part_count": ghost["part_count"],
            "recovery_reference_count": ghost_refs,
        },
    }


def command_status(args: argparse.Namespace) -> int:
    with readonly_connection(args.db) as conn:
        require_schema(conn)
        row = exact_user_row(conn)
        profile = profile_state(row)
        tables = table_names(conn)
        report = {
            "tool_version": TOOL_VERSION,
            "command": "status",
            "generated_at": utc_now(),
            "read_only": True,
            "reported_login": REPORTED_LOGIN,
            "canonical_username": CANONICAL_USERNAME,
            "exact_match": row["username"] == CANONICAL_USERNAME,
            "database": db_identity(conn, args.db),
            "profile": profile,
            "last_known_good": lkg_state(conn),
            "session_generation": session_evidence(conn),
            "recovery_receipt_schema_present": "trollu2_recovery_receipts" in tables,
            "phase": "readonly_dry_run_gate",
        }
    print_json(report)
    return 0


def command_audit(args: argparse.Namespace) -> int:
    with readonly_connection(args.db) as conn:
        report = audit_snapshot(conn, args.db)
    print_json(report)
    return 0 if report["ready_for_plan"] else 1


def command_plan(args: argparse.Namespace) -> int:
    with readonly_connection(args.db) as conn:
        plan = build_plan(conn, args.db)
    output = Path(args.output).resolve()
    if output.exists() and not args.overwrite:
        raise RecoveryGateError(f"Plan already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    try:
        os.chmod(output, 0o600)
    except OSError:
        pass
    print_json({
        "ok": plan["ready_for_dry_run"],
        "command": "plan",
        "read_only_database": True,
        "plan_path": str(output),
        "plan_id": plan["plan_id"],
        "plan_sha256": plan["plan_sha256"],
        "blockers": plan["blockers"],
    })
    return 0 if plan["ready_for_dry_run"] else 1


def command_dry_run(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    with readonly_connection(args.db) as conn:
        blockers = validate_plan_against_current(conn, args.db, plan)
    report = {
        "ok": not blockers,
        "command": "dry-run",
        "generated_at": utc_now(),
        "database_writes": 0,
        "plan_id": plan["plan_id"],
        "plan_sha256": plan["plan_sha256"],
        "canonical_username": CANONICAL_USERNAME,
        "final_state": plan["final_state"],
        "preserved_apps": len(plan["preserve"]["apps"]),
        "preserved_tools": len(plan["preserve"]["tools"]),
        "proven_recent_googleplex_installs": plan["preserve"]["recent_googleplex_installs"],
        "territory_cities": [
            {"city": city["city"], "pillar_count": city["pillar_count"], "collisions": city["collisions"]}
            for city in plan["territory_recovery"]["cities"]
        ],
        "ghostnetwork_planned_writes": plan["ghostnetwork_isolation"]["writes"],
        "other_profile_planned_writes": 0,
        "blockers": blockers,
        "verdict": "READY FOR TROLLU2 RECOVERY DRY-RUN" if not blockers else "NO-GO",
    }
    print_json(report)
    return 0 if not blockers else 1


def require_artifact_hashes(
    args: argparse.Namespace, plan: dict[str, Any], manifest: dict[str, Any] | None = None
) -> None:
    if str(getattr(args, "plan_sha256", "") or "") != plan["plan_sha256"]:
        raise RecoveryGateError("--plan-sha256 does not match the signed plan")
    if manifest is not None and str(getattr(args, "manifest_sha256", "") or "") != manifest["manifest_sha256"]:
        raise RecoveryGateError("--manifest-sha256 does not match the before-manifest")


def command_backup(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    output = Path(args.output).resolve()
    refuse_repo_output(output)
    if output.exists() and not args.overwrite:
        raise RecoveryGateError(f"Before-manifest already exists: {output}")
    with readonly_connection(args.db) as conn:
        manifest = build_before_manifest(conn, args.db, plan)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(output, 0o600)
    except OSError:
        pass
    print_json({
        "ok": True,
        "command": "backup",
        "read_only_database": True,
        "sensitive": True,
        "before_manifest_path": str(output),
        "manifest_sha256": manifest["manifest_sha256"],
        "plan_id": plan["plan_id"],
    })
    return 0


def command_apply(args: argparse.Namespace) -> int:
    require_write_flag(args)
    plan = load_plan(args.plan)
    manifest = load_manifest(args.before_manifest, plan)
    require_artifact_hashes(args, plan, manifest)
    receipt = initialize_recovery_receipt(args.db, plan, manifest)
    if receipt["status"] == "rolled_back":
        raise RecoveryGateError("Rolled-back recovery plan cannot be applied again")
    level = apply_level_step(args.db, plan)
    cities = [atomic_city_grant(args.db, plan, city) for city in plan["territory_recovery"]["cities"]]
    with readonly_connection(args.db) as conn:
        jobs = plan_job_status(conn, plan)
    if not jobs["complete"]:
        print_json({
            "ok": True,
            "command": "apply",
            "phase": "AWAITING_TERRITORY_WORKER",
            "plan_id": plan["plan_id"],
            "profile_level_step": level,
            "city_grants": cities,
            "territory_jobs": jobs,
            "database_writes": True,
            "next": "Allow the existing territory worker to complete the listed jobs, then rerun the identical apply command.",
        })
        return 3
    settlement = final_settlement(args.db, plan)
    print_json({
        "ok": True,
        "command": "apply",
        "phase": "APPLIED_READY_FOR_VERIFY",
        "plan_id": plan["plan_id"],
        "profile_level_step": level,
        "city_grants": cities,
        "territory_jobs": jobs,
        "final_settlement": settlement,
        "database_writes": True,
    })
    return 0


def command_verify(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    manifest = (
        load_manifest(args.before_manifest, plan)
        if getattr(args, "before_manifest", None) else None
    )
    with readonly_connection(args.db) as conn:
        verification = verify_recovery(conn, plan, manifest=manifest)
    print_json({
        "command": "verify",
        "read_only_database": True,
        "plan_id": plan["plan_id"],
        **verification,
    })
    return 0 if verification["ok"] else 1


def command_promote_lkg(args: argparse.Namespace) -> int:
    require_write_flag(args)
    plan = load_plan(args.plan)
    require_artifact_hashes(args, plan)
    result = promote_lkg(args.db, plan, args.final_checksum)
    print_json({
        "ok": True,
        "command": "promote-lkg",
        "plan_id": plan["plan_id"],
        "result": result,
        "database_writes": True,
    })
    return 0


def command_report(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    manifest = load_manifest(args.before_manifest, plan)
    with readonly_connection(args.db) as conn:
        receipt = recovery_receipt(conn, plan["plan_id"])
        steps = []
        if RECOVERY_STEPS_TABLE in table_names(conn):
            steps = [
                {
                    "step_key": row["step_key"],
                    "status": row["status"],
                    "receipt_sha256": sha256_text(str(row["receipt_json"] or "{}")),
                    "applied_at": row["applied_at"],
                }
                for row in conn.execute(
                    f"SELECT step_key, status, receipt_json, applied_at FROM {RECOVERY_STEPS_TABLE} "
                    "WHERE plan_id=? ORDER BY created_at, step_key",
                    (plan["plan_id"],),
                )
            ]
        verification = verify_recovery(conn, plan, manifest=manifest) if receipt else {
            "ok": False, "blockers": ["recovery_receipt_missing"]
        }
    print_json({
        "ok": bool(verification.get("ok")),
        "command": "report",
        "read_only_database": True,
        "plan_id": plan["plan_id"],
        "receipt": {
            "status": receipt["status"],
            "created_at": receipt["created_at"],
            "applied_at": receipt["applied_at"],
            "promoted_at": receipt["promoted_at"],
            "rolled_back_at": receipt["rolled_back_at"],
        } if receipt else None,
        "steps": steps,
        "verification": verification,
    })
    return 0 if verification.get("ok") else 1


def command_rollback(args: argparse.Namespace) -> int:
    require_write_flag(args)
    plan = load_plan(args.plan)
    manifest = load_manifest(args.before_manifest, plan)
    require_artifact_hashes(args, plan, manifest)
    result = rollback_recovery(args.db, plan, manifest)
    print_json({
        "ok": True,
        "command": "rollback",
        "plan_id": plan["plan_id"],
        "result": result,
        "database_writes": True,
    })
    return 0


def command_verify_rollback(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    manifest = load_manifest(args.before_manifest, plan)
    with readonly_connection(args.db) as conn:
        verification = verify_rollback(conn, plan, manifest)
    print_json({
        "command": "verify-rollback",
        "read_only_database": True,
        "plan_id": plan["plan_id"],
        **verification,
    })
    return 0 if verification["ok"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=os.environ.get("CHAOS_DB_PATH", "data/game.sqlite3"))
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "audit"):
        sub = subs.add_parser(name)
        sub.add_argument("--db", default=argparse.SUPPRESS)
    plan = subs.add_parser("plan")
    plan.add_argument("--db", default=argparse.SUPPRESS)
    plan.add_argument("--output", required=True)
    plan.add_argument("--overwrite", action="store_true")
    dry = subs.add_parser("dry-run")
    dry.add_argument("--db", default=argparse.SUPPRESS)
    dry.add_argument("--plan", required=True)
    backup = subs.add_parser("backup")
    backup.add_argument("--db", default=argparse.SUPPRESS)
    backup.add_argument("--plan", required=True)
    backup.add_argument("--output", required=True)
    backup.add_argument("--overwrite", action="store_true")
    apply_cmd = subs.add_parser("apply")
    apply_cmd.add_argument("--db", default=argparse.SUPPRESS)
    apply_cmd.add_argument("--plan", required=True)
    apply_cmd.add_argument("--before-manifest", required=True)
    apply_cmd.add_argument("--plan-sha256", required=True)
    apply_cmd.add_argument("--manifest-sha256", required=True)
    apply_cmd.add_argument("--write", action="store_true")
    apply_cmd.add_argument("--authorized-by", required=True)
    verify = subs.add_parser("verify")
    verify.add_argument("--db", default=argparse.SUPPRESS)
    verify.add_argument("--plan", required=True)
    verify.add_argument("--before-manifest", required=True)
    promote = subs.add_parser("promote-lkg")
    promote.add_argument("--db", default=argparse.SUPPRESS)
    promote.add_argument("--plan", required=True)
    promote.add_argument("--plan-sha256", required=True)
    promote.add_argument("--final-checksum", required=True)
    promote.add_argument("--write", action="store_true")
    promote.add_argument("--authorized-by", required=True)
    report = subs.add_parser("report")
    report.add_argument("--db", default=argparse.SUPPRESS)
    report.add_argument("--plan", required=True)
    report.add_argument("--before-manifest", required=True)
    rollback = subs.add_parser("rollback")
    rollback.add_argument("--db", default=argparse.SUPPRESS)
    rollback.add_argument("--plan", required=True)
    rollback.add_argument("--before-manifest", required=True)
    rollback.add_argument("--plan-sha256", required=True)
    rollback.add_argument("--manifest-sha256", required=True)
    rollback.add_argument("--write", action="store_true")
    rollback.add_argument("--authorized-by", required=True)
    verify_rollback_cmd = subs.add_parser("verify-rollback")
    verify_rollback_cmd.add_argument("--db", default=argparse.SUPPRESS)
    verify_rollback_cmd.add_argument("--plan", required=True)
    verify_rollback_cmd.add_argument("--before-manifest", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "status":
            return command_status(args)
        if args.command == "audit":
            return command_audit(args)
        if args.command == "plan":
            return command_plan(args)
        if args.command == "dry-run":
            return command_dry_run(args)
        if args.command == "backup":
            return command_backup(args)
        if args.command == "apply":
            return command_apply(args)
        if args.command == "verify":
            return command_verify(args)
        if args.command == "promote-lkg":
            return command_promote_lkg(args)
        if args.command == "report":
            return command_report(args)
        if args.command == "rollback":
            return command_rollback(args)
        return command_verify_rollback(args)
    except (RecoveryGateError, sqlite3.Error, OSError, ValueError) as exc:
        print_json({
            "ok": False,
            "command": getattr(args, "command", ""),
            "tool_version": TOOL_VERSION,
            "error": str(exc),
        })
        return 2


if __name__ == "__main__":
    sys.exit(main())
