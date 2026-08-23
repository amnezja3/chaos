#!/usr/bin/env python
"""Profile store migration and account repair tool.

Sprint 130.5: move hot runtime scopes from users.profile_json into the
dedicated stores introduced in Sprint 130.1-130.4. The tool is intentionally
conservative: read-only commands are the default, writes require --write, and
production writes require a backup manifest unless explicitly overridden.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from hashlib import sha256
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import (  # noqa: E402
    DB_PATH,
    PROFILE_INTEGRITY_RECOVERY_REQUIRED,
    PROFILE_INTEGRITY_VALID,
    PROFILE_SCHEMA_VERSION,
    PROFILE_VALIDATION_VERSION,
    PlayerInventoryStore,
    PlayerOperationStore,
    PlayerPositionStore,
    PlayerTargetRuntimeStore,
    SystemMessageStore,
    WalletBalanceStore,
    db_connect,
    dumps_json,
    init_db,
    loads_json,
    profile_payload_checksum,
    utc_now,
    validate_profile_candidate,
)


TOOL_VERSION = "130.5.0"
DEFAULT_MIGRATION_ID = "profile-store-130-5"
LOCK_NAME = ".profile_store_migration.lock"
RUNTIME_TABLES = (
    "player_target_runtime",
    "player_target_events",
    "player_marked_targets",
    "player_marked_target_state",
    "player_positions",
    "player_operations",
    "operation_events",
    "system_messages",
    "player_apps",
    "player_tool_files",
    "player_storage",
    "wallet_balances",
    "wallet_balance_events",
)
WALLET_RUNTIME_TABLES = frozenset({"wallet_balances", "wallet_balance_events"})
NON_WALLET_RUNTIME_TABLES = tuple(
    table for table in RUNTIME_TABLES if table not in WALLET_RUNTIME_TABLES
)


def canonical_json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def checksum(value) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def load_profile_json(raw: str):
    try:
        profile = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        return None, f"invalid_json:{exc}"
    if not isinstance(profile, dict):
        return None, "profile_not_object"
    return profile, ""


def get_user_rows(db_path: str, username: str = ""):
    init_db(db_path)
    with db_connect(db_path) as conn:
        select = (
            "SELECT username, profile_json, updated_at, profile_revision, "
            "profile_schema_version, profile_checksum, "
            "profile_integrity_status, profile_validation_version FROM users"
        )
        if username:
            rows = conn.execute(
                select + " WHERE username = ? ORDER BY username",
                (username,),
            ).fetchall()
        else:
            rows = conn.execute(
                select + " ORDER BY username"
            ).fetchall()
    return [dict(row) for row in rows]


def table_columns(conn, table_name: str):
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]


def select_runtime_rows(conn, username: str):
    backup = {}
    operation_ids = [
        row["operation_id"]
        for row in conn.execute(
            "SELECT operation_id FROM player_operations WHERE username = ?",
            (username,),
        ).fetchall()
    ]
    for table in RUNTIME_TABLES:
        cols = table_columns(conn, table)
        if not cols:
            backup[table] = []
            continue
        if table == "operation_events":
            if operation_ids:
                placeholders = ",".join("?" for _ in operation_ids)
                rows = conn.execute(
                    f"SELECT * FROM operation_events WHERE operation_id IN ({placeholders})",
                    tuple(operation_ids),
                ).fetchall()
            else:
                rows = []
        elif "username" in cols:
            rows = conn.execute(f"SELECT * FROM {table} WHERE username = ?", (username,)).fetchall()
        else:
            rows = []
        backup[table] = [dict(row) for row in rows]
    return backup


def delete_non_wallet_runtime_rows(conn, username: str):
    op_ids = [
        row["operation_id"]
        for row in conn.execute(
            "SELECT operation_id FROM player_operations WHERE username = ?",
            (username,),
        ).fetchall()
    ]
    if op_ids:
        placeholders = ",".join("?" for _ in op_ids)
        conn.execute(f"DELETE FROM operation_events WHERE operation_id IN ({placeholders})", tuple(op_ids))
    conn.execute("DELETE FROM player_target_events WHERE username = ?", (username,))
    conn.execute("DELETE FROM player_target_runtime WHERE username = ?", (username,))
    conn.execute("DELETE FROM player_marked_targets WHERE username = ?", (username,))
    conn.execute("DELETE FROM player_marked_target_state WHERE username = ?", (username,))
    conn.execute("DELETE FROM player_positions WHERE username = ?", (username,))
    conn.execute("DELETE FROM player_operations WHERE username = ?", (username,))
    conn.execute("DELETE FROM system_messages WHERE username = ?", (username,))
    conn.execute("DELETE FROM player_tool_files WHERE username = ?", (username,))
    conn.execute("DELETE FROM player_apps WHERE username = ?", (username,))
    conn.execute("DELETE FROM player_storage WHERE username = ?", (username,))


def restore_rows(conn, table: str, rows: list[dict]):
    if not rows:
        return
    cols = table_columns(conn, table)
    if not cols:
        return
    valid_rows = []
    for row in rows:
        filtered = {key: row.get(key) for key in cols if key in row}
        if filtered:
            valid_rows.append(filtered)
    for row in valid_rows:
        keys = list(row.keys())
        placeholders = ",".join("?" for _ in keys)
        columns = ",".join(keys)
        conn.execute(
            f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})",
            tuple(row[key] for key in keys),
        )


def profile_position(profile: dict):
    for key in ("current_position", "curently_possition", "position"):
        value = profile.get(key)
        if not isinstance(value, dict):
            continue
        try:
            lat = float(value.get("lat"))
            lng = float(value.get("lng", value.get("lon")))
        except (TypeError, ValueError):
            continue
        if -90 <= lat <= 90 and -180 <= lng <= 180:
            return {"lat": lat, "lng": lng, "source_field": key}
    return {}


def stable_id(value: dict, prefix: str) -> str:
    raw = canonical_json(value)
    return f"{prefix}_{sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def normalize_profile_for_migration(username: str, profile: dict):
    normalized = dict(profile or {})
    normalized.setdefault("username", username)
    operations = []
    for operation in normalized.get("operations", []) or []:
        if not isinstance(operation, dict):
            continue
        op = dict(operation)
        op.setdefault("operation_id", op.get("id") or stable_id(op, "legacy_op"))
        op.setdefault("id", op["operation_id"])
        operations.append(op)
    normalized["operations"] = operations
    return normalized


def audit_profile(username: str, profile: dict | None, parse_error: str = ""):
    warnings = []
    errors = []
    metrics = {
        "apps": 0,
        "tools": 0,
        "operations": 0,
        "system_messages": 0,
        "storage_capacity": 0,
        "storage_used": 0,
        "hackcoins": 0,
    }
    if parse_error:
        errors.append(parse_error)
        return {"username": username, "level": "FAILED", "errors": errors, "warnings": warnings, "metrics": metrics}
    if not isinstance(profile, dict):
        errors.append("missing_profile_json")
        return {"username": username, "level": "FAILED", "errors": errors, "warnings": warnings, "metrics": metrics}

    apps = profile.get("apps", []) if isinstance(profile.get("apps"), list) else []
    files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
    tools = files.get("tools", []) if isinstance(files, dict) and isinstance(files.get("tools"), list) else []
    operations = profile.get("operations", []) if isinstance(profile.get("operations"), list) else []
    messages = profile.get("system_messages", []) if isinstance(profile.get("system_messages"), list) else []
    metrics.update({
        "apps": len(apps),
        "tools": len(tools),
        "operations": len(operations),
        "system_messages": len(messages),
    })

    if not profile_position(profile):
        warnings.append("missing_or_invalid_position")

    target = profile.get("aimed_target")
    if target and not isinstance(target, dict):
        warnings.append("aimed_target_invalid_type")
    elif isinstance(target, dict) and target and not (target.get("lat") and target.get("lng", target.get("lon"))):
        warnings.append("aimed_target_incomplete")

    app_ids = []
    for app in apps:
        if not isinstance(app, dict):
            warnings.append("app_invalid_type")
            continue
        app_ids.append(str(app.get("id") or app.get("app_id") or app.get("name") or ""))
    if len([item for item in app_ids if item]) != len(set(item for item in app_ids if item)):
        warnings.append("duplicate_apps")

    tool_ids = []
    for tool in tools:
        if isinstance(tool, dict):
            tool_ids.append(str(tool.get("id") or tool.get("tool_id") or tool.get("file") or tool.get("name") or ""))
        else:
            tool_ids.append(str(tool or ""))
    if len([item for item in tool_ids if item]) != len(set(item for item in tool_ids if item)):
        warnings.append("duplicate_tools")

    op_ids = []
    for operation in operations:
        if not isinstance(operation, dict):
            warnings.append("operation_invalid_type")
            continue
        op_id = str(operation.get("operation_id") or operation.get("id") or "")
        if not op_id:
            warnings.append("operation_missing_id")
        op_ids.append(op_id)
    if len([item for item in op_ids if item]) != len(set(item for item in op_ids if item)):
        warnings.append("duplicate_operations")

    try:
        capacity = int(profile.get("storage_capacity") or 0)
    except (TypeError, ValueError):
        capacity = 0
        warnings.append("storage_capacity_invalid")
    try:
        used = int(profile.get("storage_used") or 0)
    except (TypeError, ValueError):
        used = 0
        warnings.append("storage_used_invalid")
    metrics["storage_capacity"] = capacity
    metrics["storage_used"] = used
    if capacity and used > capacity:
        warnings.append("storage_used_over_capacity")
    if not profile.get("storage_unit"):
        warnings.append("storage_unit_missing")

    try:
        metrics["hackcoins"] = int(profile.get("hackcoins") or 0)
    except (TypeError, ValueError):
        warnings.append("hackcoins_invalid")

    level = "FAILED" if errors else ("WARNING" if warnings else "OK")
    return {"username": username, "level": level, "errors": errors, "warnings": warnings, "metrics": metrics}


def build_result_snapshot(db_path: str, username: str):
    inventory = PlayerInventoryStore(db_path).snapshot(username)
    wallet = WalletBalanceStore(db_path).get_balance(username)
    target = PlayerTargetRuntimeStore(db_path).get(username)
    position = PlayerPositionStore(db_path).get(username)
    operations = PlayerOperationStore(db_path).list_operations(username, include_terminal=True)
    with db_connect(db_path) as conn:
        msg_count = conn.execute(
            "SELECT COUNT(*) AS count FROM system_messages WHERE username = ?",
            (username,),
        ).fetchone()["count"]
    return {
        "inventory": inventory,
        "wallet_balance": wallet,
        "target": target,
        "position": position,
        "operations_count": len(operations),
        "system_messages_count": int(msg_count or 0),
    }


def verify_user_state(db_path: str, username: str, profile: dict):
    result = build_result_snapshot(db_path, username)
    warnings = []
    errors = []

    apps = profile.get("apps", []) if isinstance(profile.get("apps"), list) else []
    tools = ((profile.get("files") or {}).get("tools", []) if isinstance(profile.get("files"), dict) else [])
    operations = profile.get("operations", []) if isinstance(profile.get("operations"), list) else []

    if len(result["inventory"].get("apps", [])) < len({str((a or {}).get("id") or (a or {}).get("name") or "") for a in apps if isinstance(a, dict)}):
        warnings.append("apps_count_lower_than_profile")
    if len((result["inventory"].get("files") or {}).get("tools", [])) < len({str(t.get("id") or t.get("tool_id") or t.get("file") or t.get("name")) if isinstance(t, dict) else str(t) for t in tools}):
        warnings.append("tools_count_lower_than_profile")
    storage = result["inventory"].get("storage") or {}
    try:
        if int(storage.get("used") or 0) != int(profile.get("storage_used") or 0):
            warnings.append("storage_used_diff")
    except (TypeError, ValueError):
        warnings.append("storage_used_diff")
    try:
        if int(result["wallet_balance"] or 0) != int(profile.get("hackcoins") or 0):
            warnings.append("wallet_balance_diff")
    except (TypeError, ValueError):
        warnings.append("wallet_balance_diff")
    if operations and result["operations_count"] == 0:
        warnings.append("operations_not_seeded")
    if profile_position(profile) and not result.get("position"):
        errors.append("position_not_seeded")

    level = "FAILED" if errors else ("WARNING" if warnings else "OK")
    return {"username": username, "level": level, "errors": errors, "warnings": warnings, "result": result}


def ensure_registry(db_path: str):
    init_db(db_path)


def get_registry(db_path: str, migration_id: str, username: str):
    with db_connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT * FROM profile_store_migrations
            WHERE migration_id = ? AND username = ?
            """,
            (migration_id, username),
        ).fetchone()
        return dict(row) if row else None


def write_registry(db_path: str, migration_id: str, username: str, **fields):
    ensure_registry(db_path)
    now = utc_now()
    defaults = {
        "status": fields.get("status", "pending"),
        "source_checksum": fields.get("source_checksum"),
        "result_checksum": fields.get("result_checksum"),
        "started_at": fields.get("started_at") or now,
        "completed_at": fields.get("completed_at"),
        "error_json": dumps_json(fields.get("error") or fields.get("error_json") or {}),
        "backup_json": dumps_json(fields.get("backup") or fields.get("backup_json") or {}),
        "tool_version": TOOL_VERSION,
    }
    with db_connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO profile_store_migrations
                (migration_id, username, status, source_checksum, result_checksum,
                 started_at, completed_at, error_json, backup_json, tool_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(migration_id, username) DO UPDATE SET
                status = excluded.status,
                source_checksum = COALESCE(excluded.source_checksum, profile_store_migrations.source_checksum),
                result_checksum = COALESCE(excluded.result_checksum, profile_store_migrations.result_checksum),
                started_at = COALESCE(profile_store_migrations.started_at, excluded.started_at),
                completed_at = excluded.completed_at,
                error_json = excluded.error_json,
                backup_json = CASE
                    WHEN excluded.backup_json != '{}' THEN excluded.backup_json
                    ELSE profile_store_migrations.backup_json
                END,
                tool_version = excluded.tool_version
            """,
            (
                migration_id,
                username,
                defaults["status"],
                defaults["source_checksum"],
                defaults["result_checksum"],
                defaults["started_at"],
                defaults["completed_at"],
                defaults["error_json"],
                defaults["backup_json"],
                TOOL_VERSION,
            ),
        )


@contextmanager
def migration_lock(db_path: str, enabled: bool):
    if not enabled:
        yield
        return
    lock_path = Path(db_path).resolve().parent / LOCK_NAME
    fd = None
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        payload = f"pid={os.getpid()} host={socket.gethostname()} at={utc_now()}\n"
        os.write(fd, payload.encode("utf-8"))
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def require_write(args):
    if not getattr(args, "write", False):
        raise SystemExit("Write command requires --write.")
    if not getattr(args, "allow_without_backup", False) and not getattr(args, "backup_manifest", ""):
        raise SystemExit("Write command requires --backup-manifest or --allow-without-backup.")


def command_audit(args):
    rows = get_user_rows(args.db, args.username)
    reports = []
    for row in rows:
        profile, error = load_profile_json(row["profile_json"])
        reports.append(audit_profile(row["username"], profile, error))
    summary = {
        "command": "audit",
        "db": args.db,
        "users": len(reports),
        "ok": sum(1 for item in reports if item["level"] == "OK"),
        "warning": sum(1 for item in reports if item["level"] == "WARNING"),
        "failed": sum(1 for item in reports if item["level"] == "FAILED"),
        "reports": reports,
    }
    print_json(summary)
    return 1 if summary["failed"] else 0


def command_backup(args):
    init_db(args.db)
    src = Path(args.db).resolve()
    backup_dir = Path(args.backup_dir).resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"{src.stem}.{args.migration_id}.{stamp}{src.suffix}"
    manifest = backup_dir / f"{src.stem}.{args.migration_id}.{stamp}.manifest.json"
    shutil.copy2(src, target)
    rows = get_user_rows(args.db)
    payload = {
        "migration_id": args.migration_id,
        "tool_version": TOOL_VERSION,
        "created_at": utc_now(),
        "source_db": str(src),
        "backup_db": str(target),
        "user_count": len(rows),
        "db_size_bytes": target.stat().st_size,
        "db_checksum": sha256(target.read_bytes()).hexdigest(),
        "operator": os.environ.get("USERNAME") or os.environ.get("USER") or "",
        "host": socket.gethostname(),
    }
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print_json({"command": "backup", "manifest": str(manifest), **payload})
    return 0


def migrate_user(db_path: str, migration_id: str, username: str, force: bool = False):
    rows = get_user_rows(db_path, username)
    if not rows:
        write_registry(db_path, migration_id, username, status="failed", error={"reason": "user_not_found"}, completed_at=utc_now())
        return {"username": username, "status": "failed", "reason": "user_not_found"}

    row = rows[0]
    profile, parse_error = load_profile_json(row["profile_json"])
    if parse_error:
        write_registry(db_path, migration_id, username, status="failed", error={"reason": parse_error}, completed_at=utc_now())
        return {"username": username, "status": "failed", "reason": parse_error}

    existing = get_registry(db_path, migration_id, username)
    if existing and existing.get("status") in {"completed", "verified"} and not force:
        return {"username": username, "status": "skipped", "reason": "already_verified"}

    normalized = normalize_profile_for_migration(username, profile)
    # This is the checksum of the durable source row, not of the normalized
    # projection used by the other legacy-store seeders.  Wallet migration is
    # deliberately allowed only from that exact integrity-verified evidence.
    source_checksum = str(row.get("profile_checksum") or checksum(profile))
    with db_connect(db_path) as conn:
        backup = {
            "profile_json": row["profile_json"],
            "updated_at": row.get("updated_at"),
            "profile_record": {
                key: row.get(key)
                for key in (
                    "profile_revision",
                    "profile_schema_version",
                    "profile_checksum",
                    "profile_integrity_status",
                    "profile_validation_version",
                )
            },
            "runtime_rows": select_runtime_rows(conn, username),
        }
    write_registry(
        db_path,
        migration_id,
        username,
        status="running",
        source_checksum=source_checksum,
        backup=backup,
        started_at=utc_now(),
    )

    try:
        WalletBalanceStore(db_path).seed_from_profile(username, profile)
        PlayerTargetRuntimeStore(db_path).seed_from_profile(username, normalized)
        PlayerPositionStore(db_path).seed_from_profile(username, normalized, source="profile_store_migration")
        PlayerOperationStore(db_path).seed_from_profile(username, normalized)
        messages = normalized.get("system_messages", []) if isinstance(normalized.get("system_messages"), list) else []
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                continue
            status = str(message.get("status") or "new").lower()
            if status in {"consumed", "expired", "read"}:
                continue
            payload = dict(message)
            payload.setdefault("dedupe_key", f"migration:{username}:system_message:{stable_id(payload, 'msg')}:{index}")
            SystemMessageStore(db_path).add_message(username, payload, source="profile_store_migration")
        PlayerInventoryStore(db_path).seed_from_profile(username, normalized)
        verification = verify_user_state(db_path, username, normalized)
        result_checksum = checksum(build_result_snapshot(db_path, username))
        status = "verified" if verification["level"] == "OK" else ("warning" if verification["level"] == "WARNING" else "failed")
        write_registry(
            db_path,
            migration_id,
            username,
            status=status,
            source_checksum=source_checksum,
            result_checksum=result_checksum,
            error=verification,
            completed_at=utc_now(),
        )
        return {"username": username, "status": status, "verification": verification}
    except Exception as exc:  # noqa: BLE001 - migration tool must capture per-user failures.
        write_registry(
            db_path,
            migration_id,
            username,
            status="failed",
            source_checksum=source_checksum,
            error={"reason": str(exc)},
            completed_at=utc_now(),
        )
        return {"username": username, "status": "failed", "reason": str(exc)}


def command_dry_run(args):
    rows = get_user_rows(args.db, args.username)
    plan = []
    for row in rows:
        profile, parse_error = load_profile_json(row["profile_json"])
        audit = audit_profile(row["username"], profile, parse_error)
        plan.append({
            "username": row["username"],
            "level": audit["level"],
            "warnings": audit["warnings"],
            "errors": audit["errors"],
            "would_migrate": audit["level"] != "FAILED",
            "metrics": audit["metrics"],
        })
    print_json({"command": "dry-run", "db": args.db, "users": len(plan), "plan": plan})
    return 1 if any(item["level"] == "FAILED" for item in plan) else 0


def command_migrate_user(args):
    require_write(args)
    with migration_lock(args.db, True):
        result = migrate_user(args.db, args.migration_id, args.username, force=args.force)
    print_json({"command": "migrate-user", "migration_id": args.migration_id, "result": result})
    return 1 if result.get("status") == "failed" else 0


def command_migrate_all(args):
    require_write(args)
    rows = get_user_rows(args.db)
    results = []
    errors = 0
    with migration_lock(args.db, True):
        for offset in range(0, len(rows), max(1, args.batch_size)):
            batch = rows[offset:offset + max(1, args.batch_size)]
            for row in batch:
                result = migrate_user(args.db, args.migration_id, row["username"], force=args.force)
                results.append(result)
                if result.get("status") == "failed":
                    errors += 1
                    if errors >= args.max_errors:
                        print_json({"command": "migrate-all", "stopped": "max_errors", "results": results})
                        return 1
            if args.sleep_seconds and offset + args.batch_size < len(rows):
                time.sleep(max(0, args.sleep_seconds))
    print_json({"command": "migrate-all", "migration_id": args.migration_id, "results": results})
    return 1 if errors else 0


def command_verify(args):
    rows = get_user_rows(args.db, args.username)
    reports = []
    for row in rows:
        profile, parse_error = load_profile_json(row["profile_json"])
        if parse_error:
            reports.append({"username": row["username"], "level": "FAILED", "errors": [parse_error], "warnings": []})
            continue
        reports.append(verify_user_state(args.db, row["username"], normalize_profile_for_migration(row["username"], profile)))
    print_json({"command": "verify", "db": args.db, "users": len(reports), "reports": reports})
    return 1 if any(item["level"] == "FAILED" for item in reports) else 0


def command_reconcile(args):
    require_write(args)
    rows = get_user_rows(args.db, args.username)
    results = []
    with migration_lock(args.db, True):
        for row in rows:
            results.append(migrate_user(args.db, args.migration_id, row["username"], force=True))
    print_json({"command": "reconcile", "migration_id": args.migration_id, "results": results})
    return 1 if any(item.get("status") == "failed" for item in results) else 0


def command_resume(args):
    require_write(args)
    return command_migrate_all(args)


def rollback_user(db_path: str, migration_id: str, username: str):
    record = get_registry(db_path, migration_id, username)
    if not record:
        return {"username": username, "status": "failed", "reason": "migration_record_not_found"}
    backup = loads_json(record.get("backup_json"), {})
    if not backup or not backup.get("profile_json"):
        return {"username": username, "status": "failed", "reason": "backup_missing"}

    runtime_rows = backup.get("runtime_rows") if isinstance(backup.get("runtime_rows"), dict) else {}
    prior_wallet_rows = runtime_rows.get("wallet_balances", [])
    prior_wallet_balance = 0
    if prior_wallet_rows and isinstance(prior_wallet_rows[0], dict):
        try:
            prior_wallet_balance = max(0, int(prior_wallet_rows[0].get("balance") or 0))
        except (TypeError, ValueError):
            return {
                "username": username,
                "status": "failed",
                "reason": "wallet_backup_invalid",
            }

    # A rollback must remain visible in the canonical wallet audit trail.
    # Never delete/reinsert canonical wallet rows: restore the pre-migration
    # value through the explicit recovery boundary and a stable replay key.
    rollback_wallet_key = (
        f"{migration_id}:rollback:wallet:{username}:"
        f"{record.get('source_checksum') or checksum(backup['profile_json'])}"
    )
    try:
        wallet_result = WalletBalanceStore(db_path).recovery_set_balance(
            username,
            prior_wallet_balance,
            transaction_key=rollback_wallet_key,
            reason="profile_store_migration.rollback",
        )
    except Exception as exc:  # noqa: BLE001 - retain backup for a safe retry.
        write_registry(
            db_path,
            migration_id,
            username,
            status="failed",
            error={"reason": "wallet_rollback_failed", "detail": str(exc)},
            completed_at=utc_now(),
        )
        return {
            "username": username,
            "status": "failed",
            "reason": "wallet_rollback_failed",
        }

    backup_profile, parse_error = load_profile_json(backup["profile_json"])
    validation = (
        validate_profile_candidate(backup_profile, username)
        if not parse_error
        else {"valid": False}
    )
    profile_record = (
        backup.get("profile_record")
        if isinstance(backup.get("profile_record"), dict)
        else {}
    )
    backup_integrity = str(profile_record.get("profile_integrity_status") or "")
    if not validation.get("valid"):
        backup_integrity = PROFILE_INTEGRITY_RECOVERY_REQUIRED
    elif backup_integrity not in {
        PROFILE_INTEGRITY_VALID,
        PROFILE_INTEGRITY_RECOVERY_REQUIRED,
    }:
        backup_integrity = PROFILE_INTEGRITY_VALID
    backup_checksum = str(profile_record.get("profile_checksum") or "")
    if validation.get("valid") and not backup_checksum:
        backup_checksum = profile_payload_checksum(backup_profile)
    now = utc_now()
    with db_connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        delete_non_wallet_runtime_rows(conn, username)
        for table in NON_WALLET_RUNTIME_TABLES:
            restore_rows(conn, table, runtime_rows.get(table, []))
        conn.execute(
            """
            UPDATE users
            SET profile_json = ?, updated_at = ?, profile_revision = ?,
                profile_schema_version = ?, profile_checksum = ?,
                profile_integrity_status = ?, profile_validation_version = ?
            WHERE username = ?
            """,
            (
                backup["profile_json"],
                now,
                max(1, int(profile_record.get("profile_revision") or 1)),
                int(profile_record.get("profile_schema_version") or PROFILE_SCHEMA_VERSION),
                backup_checksum,
                backup_integrity,
                int(profile_record.get("profile_validation_version") or PROFILE_VALIDATION_VERSION),
                username,
            ),
        )
        conn.execute(
            """
            UPDATE profile_store_migrations
            SET status = 'rolled_back', completed_at = ?, error_json = ?
            WHERE migration_id = ? AND username = ?
            """,
            (now, dumps_json({"rolled_back_at": now}), migration_id, username),
        )
    return {
        "username": username,
        "status": "rolled_back",
        "wallet_transaction_key": rollback_wallet_key,
        "wallet_duplicate": bool(wallet_result.get("duplicate")),
    }


def command_rollback_user(args):
    require_write(args)
    with migration_lock(args.db, True):
        result = rollback_user(args.db, args.migration_id, args.username)
    print_json({"command": "rollback-user", "migration_id": args.migration_id, "result": result})
    return 1 if result.get("status") == "failed" else 0


def command_rollback_all(args):
    require_write(args)
    with db_connect(args.db) as conn:
        rows = conn.execute(
            "SELECT username FROM profile_store_migrations WHERE migration_id = ? ORDER BY username",
            (args.migration_id,),
        ).fetchall()
    results = []
    with migration_lock(args.db, True):
        for row in rows:
            results.append(rollback_user(args.db, args.migration_id, row["username"]))
    print_json({"command": "rollback-all", "migration_id": args.migration_id, "results": results})
    return 1 if any(item.get("status") == "failed" for item in results) else 0


def command_report(args):
    ensure_registry(args.db)
    with db_connect(args.db) as conn:
        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS count
            FROM profile_store_migrations
            WHERE migration_id = ?
            GROUP BY status
            ORDER BY status
            """,
            (args.migration_id,),
        ).fetchall()
        details = conn.execute(
            """
            SELECT username, status, source_checksum, result_checksum, started_at, completed_at, error_json
            FROM profile_store_migrations
            WHERE migration_id = ?
            ORDER BY username
            """,
            (args.migration_id,),
        ).fetchall()
    report = {
        "command": "report",
        "migration_id": args.migration_id,
        "tool_version": TOOL_VERSION,
        "db": args.db,
        "generated_at": utc_now(),
        "summary": {row["status"]: int(row["count"] or 0) for row in rows},
        "accounts": [dict(row) for row in details],
    }
    print_json(report)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="CHAOS profile store migration tool")
    parser.add_argument("command", choices=[
        "audit",
        "backup",
        "dry-run",
        "migrate-user",
        "migrate-all",
        "verify-user",
        "verify-all",
        "reconcile",
        "resume",
        "rollback-user",
        "rollback-all",
        "report",
    ])
    parser.add_argument("--db", default=os.environ.get("CHAOS_DB_PATH", DB_PATH), help="SQLite DB path")
    parser.add_argument("--migration-id", default=DEFAULT_MIGRATION_ID)
    parser.add_argument("--username", default="")
    parser.add_argument("--write", action="store_true", help="Required for write commands")
    parser.add_argument("--force", action="store_true", help="Re-run already verified accounts")
    parser.add_argument("--backup-dir", default=os.path.join("data", "backups", "profile_store_migration"))
    parser.add_argument("--backup-manifest", default="")
    parser.add_argument("--allow-without-backup", action="store_true")
    parser.add_argument("--batch-size", type=int, default=25)
    parser.add_argument("--sleep-seconds", type=float, default=0)
    parser.add_argument("--max-errors", type=int, default=1)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    command = args.command
    if command in {"migrate-user", "verify-user", "rollback-user"} and not args.username:
        raise SystemExit(f"{command} requires --username.")

    if command == "audit":
        return command_audit(args)
    if command == "backup":
        return command_backup(args)
    if command == "dry-run":
        return command_dry_run(args)
    if command == "migrate-user":
        return command_migrate_user(args)
    if command == "migrate-all":
        return command_migrate_all(args)
    if command in {"verify-user", "verify-all"}:
        if command == "verify-all":
            args.username = ""
        return command_verify(args)
    if command == "reconcile":
        return command_reconcile(args)
    if command == "resume":
        return command_resume(args)
    if command == "rollback-user":
        return command_rollback_user(args)
    if command == "rollback-all":
        return command_rollback_all(args)
    if command == "report":
        return command_report(args)
    raise SystemExit(f"Unsupported command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
