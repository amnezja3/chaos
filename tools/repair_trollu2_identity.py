#!/usr/bin/env python3
"""Sprint 130.11 field-level identity repair for the recovered ``trolu2``.

The audit, plan and verify commands are read-only.  Apply and LKG promotion are
explicitly write-gated, CAS protected and receipt-backed.  Only ``nick``,
``profession`` and ``avatar`` may change in the profile document.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.catalog import normalize_ghostnetwork_profile_identity
from tools import repair_trollu2_profile as recovery


TOOL_VERSION = "130.11-identity-repair-v1"
PLAN_VERSION = 1
CANONICAL_USERNAME = "trolu2"
EXPECTED_CLAN_CODE = "echo_freedom"
EXPECTED_PROFESSION_CODE = "social_engineer"
EXPECTED_IDENTITY = {
    "nick": "Trolu 2",
    "profession": "Socjotechnik",
    "avatar": "/static/images/avatar-frakcja-2-player-2.png",
}
CHANGE_PROVENANCE = {
    "nick": "approved_identity_correction",
    "profession": "player_selected_post_recovery",
    "avatar": "derived_from_current_canonical_clan_profession_mapping",
}
MUTABLE_PROFILE_FIELDS = frozenset(EXPECTED_IDENTITY)
RECEIPTS_TABLE = "trollu2_identity_repair_receipts"
REASON = "sprint_130_11_identity_repair"

REQUIRED_TABLES = {
    "users",
    "profile_last_known_good",
    recovery.RECOVERY_RECEIPTS_TABLE,
    "profile_store_migrations",
    "wallet_balances",
    "wallet_ledger",
    "wallet_balance_events",
    "player_apps",
    "player_tool_files",
    "player_storage",
    "captured_targets",
    "territory_target_ownership",
    "player_areas",
    "ghost_cycles",
    "ghost_parts",
}


class IdentityRepairError(RuntimeError):
    """Fail-closed identity repair gate."""


def identity_projection(profile: dict[str, Any]) -> dict[str, Any]:
    fraction = profile.get("fraction")
    operator = profile.get("operator")
    return {
        "username": profile.get("username"),
        "nick": profile.get("nick"),
        "clan": profile.get("clan"),
        "fraction": copy.deepcopy(fraction),
        "fraction_role": fraction.get("role") if isinstance(fraction, dict) else None,
        "profession": profile.get("profession"),
        "role": profile.get("role"),
        "operator_profession": operator.get("profession") if isinstance(operator, dict) else None,
        "ghost_profession": profile.get("ghost_profession"),
        "avatar": profile.get("avatar"),
    }


def profile_invariant(profile: dict[str, Any]) -> dict[str, Any]:
    value = copy.deepcopy(profile)
    for key in MUTABLE_PROFILE_FIELDS:
        value.pop(key, None)
    return value


def require_schema(conn: sqlite3.Connection) -> None:
    missing = sorted(REQUIRED_TABLES - recovery.table_names(conn))
    if missing:
        raise IdentityRepairError("Required identity repair schema missing: " + ", ".join(missing))
    required_user_columns = {
        "username", "profile_json", "profile_revision", "profile_schema_version",
        "profile_checksum", "profile_integrity_status", "profile_validation_version",
    }
    missing_columns = sorted(required_user_columns - recovery.table_columns(conn, "users"))
    if missing_columns:
        raise IdentityRepairError("Profile integrity columns missing: " + ", ".join(missing_columns))


def exact_profile_state(conn: sqlite3.Connection, *, include_profile: bool = True) -> dict[str, Any]:
    row = recovery.exact_user_row(conn)
    state = recovery.profile_state(row, include_profile=include_profile)
    if state["integrity_status"] != "valid" or not state["checksum_valid"]:
        raise IdentityRepairError("Current profile is not integrity-valid")
    if int(state["revision"]) <= 0:
        raise IdentityRepairError("Current profile revision is invalid")
    return state


def latest_completed_recovery(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        f"SELECT plan_id, plan_sha256, status, current_profile_revision, "
        f"current_profile_checksum, promoted_at, updated_at FROM {recovery.RECOVERY_RECEIPTS_TABLE} "
        "WHERE canonical_username=? ORDER BY updated_at DESC LIMIT 1",
        (CANONICAL_USERNAME,),
    ).fetchone()
    if not row:
        raise IdentityRepairError("Completed Sprint 130.11 recovery receipt is missing")
    result = dict(row)
    if result["status"] != "complete" or not result.get("promoted_at"):
        raise IdentityRepairError("Sprint 130.11 recovery is not complete/LKG-promoted")
    return result


def _rows_digest(conn: sqlite3.Connection, table: str, where: str = "", params: tuple = ()) -> dict[str, Any]:
    query = f'SELECT * FROM "{table}"'
    if where:
        query += " WHERE " + where
    rows = [dict(row) for row in conn.execute(query, params).fetchall()]
    rows.sort(key=recovery.canonical_json)
    return {"count": len(rows), "sha256": recovery.digest(rows)}


def external_invariants(conn: sqlite3.Connection) -> dict[str, Any]:
    """Hash exact-account canonical stores; never parse another user's profile."""
    groups = {
        "wallet": {},
        "inventory": {},
        "territory": {},
        "ghostnetwork": {},
    }
    for table in ("wallet_balances", "wallet_ledger", "wallet_balance_events"):
        groups["wallet"][table] = _rows_digest(conn, table, "username=?", (CANONICAL_USERNAME,))
    for table in ("player_apps", "player_tool_files", "player_storage"):
        groups["inventory"][table] = _rows_digest(conn, table, "username=?", (CANONICAL_USERNAME,))
    groups["territory"]["captured_targets"] = _rows_digest(
        conn, "captured_targets", "owner_username=?", (CANONICAL_USERNAME,)
    )
    groups["territory"]["territory_target_ownership"] = _rows_digest(
        conn, "territory_target_ownership", "owner_username=?", (CANONICAL_USERNAME,)
    )
    groups["territory"]["player_areas"] = _rows_digest(
        conn, "player_areas", "owner_username=?", (CANONICAL_USERNAME,)
    )
    # Cycle/part lifecycle is small (one cycle, twenty parts) and is explicitly
    # protected because identity repair must not touch GhostNetwork.
    groups["ghostnetwork"]["ghost_cycles"] = _rows_digest(conn, "ghost_cycles")
    groups["ghostnetwork"]["ghost_parts"] = _rows_digest(conn, "ghost_parts")
    groups["summary_sha256"] = recovery.digest(groups)
    return groups


def canonical_avatar_mapping() -> dict[str, Any]:
    script_path = ROOT / "static" / "js" / "register_scripts.js"
    run_path = ROOT / "run.py"
    script = script_path.read_text(encoding="utf-8")
    runtime = run_path.read_text(encoding="utf-8")

    roles_block = re.search(r"const rolesByFaction\s*=\s*\{(.*?)\n\};", script, re.S)
    avatars_block = re.search(r"const avatarData\s*=\s*\{(.*?)\n\};", script, re.S)
    if not roles_block or not avatars_block:
        raise IdentityRepairError("Registration identity mapping is unreadable")

    def array_for(block: str, faction_id: int) -> list[str]:
        match = re.search(rf"^\s*{faction_id}:\s*(\[[^\n]+\])", block, re.M)
        if not match:
            raise IdentityRepairError(f"Faction {faction_id} mapping is missing")
        value = json.loads(match.group(1))
        if not isinstance(value, list):
            raise IdentityRepairError("Registration mapping is not a list")
        return [str(item) for item in value]

    roles = array_for(roles_block.group(1), 2)
    avatars = array_for(avatars_block.group(1), 2)
    try:
        role_index = roles.index(EXPECTED_IDENTITY["profession"])
    except ValueError as exc:
        raise IdentityRepairError("Socjotechnik is absent from faction 2 mapping") from exc
    if role_index >= len(avatars):
        raise IdentityRepairError("Socjotechnik avatar index is absent")
    mapped_path = "/static/images/" + avatars[role_index]
    asset = ROOT / mapped_path.removeprefix("/")
    formula_present = 'avatar_path = f"/static/images/avatar-frakcja-{faction}-player-{role}.png"' in runtime
    if mapped_path != EXPECTED_IDENTITY["avatar"] or not asset.is_file() or not formula_present:
        raise IdentityRepairError("Canonical Socjotechnik avatar contract does not match runtime/assets")
    return {
        "clan": "Echo Wolności",
        "faction_id": 2,
        "profession": EXPECTED_IDENTITY["profession"],
        "role_id": role_index + 1,
        "avatar": mapped_path,
        "asset_exists": True,
        "asset_sha256": recovery.hashlib.sha256(asset.read_bytes()).hexdigest(),
        "sources": [
            "static/js/register_scripts.js:rolesByFaction/avatarData",
            "run.py:/api/register-finalize avatar_path",
            mapped_path,
        ],
    }


def historical_identity_evidence(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute(
        "SELECT migration_id, status, completed_at, backup_json FROM profile_store_migrations "
        "WHERE username=? AND backup_json IS NOT NULL AND backup_json NOT IN ('', '{}') "
        "ORDER BY completed_at, migration_id",
        (CANONICAL_USERNAME,),
    ).fetchall()
    candidates = []
    for row in rows:
        backup = recovery.loads_object(row["backup_json"])
        raw_profile = backup.get("profile_json")
        profile = recovery.loads_object(raw_profile) if isinstance(raw_profile, str) else (
            raw_profile if isinstance(raw_profile, dict) else {}
        )
        if not profile:
            continue
        identity = identity_projection(profile)
        fraction = identity.get("fraction")
        fraction_name = fraction.get("name") if isinstance(fraction, dict) else fraction
        fraction_role = fraction.get("role") if isinstance(fraction, dict) else None
        normalized_evidence = normalize_ghostnetwork_profile_identity({
            "clan": identity.get("clan") or fraction_name,
            "profession": identity.get("profession") or (
                EXPECTED_IDENTITY["profession"] if str(fraction_role) == "2" else ""
            ),
        })
        candidates.append({
            "migration_id": row["migration_id"],
            "status": row["status"],
            "completed_at": row["completed_at"],
            "backup_profile_sha256": recovery.profile_checksum(profile),
            "identity": identity,
            "nick_matches_contract": identity["nick"] == EXPECTED_IDENTITY["nick"],
            "profession_matches_contract": identity["profession"] == EXPECTED_IDENTITY["profession"],
            "fraction_role_2_maps_to_contract": (
                str(fraction_role) == "2"
                and normalized_evidence.get("clan_code") == EXPECTED_CLAN_CODE
                and normalized_evidence.get("profession_code") == EXPECTED_PROFESSION_CODE
            ),
        })
    nick_confirmed = any(item["nick_matches_contract"] for item in candidates)
    profession_explicit = any(item["profession_matches_contract"] for item in candidates)
    profession_role_mapping = any(item["fraction_role_2_maps_to_contract"] for item in candidates)
    limitations = []
    if not nick_confirmed:
        limitations.append("No captured historical profile explicitly confirms nick='Trolu 2'.")
    if not profession_explicit:
        limitations.append("No captured historical profile has explicit top-level profession='Socjotechnik'.")
    if not profession_role_mapping:
        limitations.append("No captured historical fraction role=2 corroborates Socjotechnik through onboarding mapping.")
    limitations.append(
        "Sprint 130.10 redacted evidence archives do not expose raw identity fields."
    )
    return {
        "source": "profile_store_migrations.backup_json",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "nick_confirmed": nick_confirmed,
        "profession_explicitly_confirmed": profession_explicit,
        "profession_correlated_by_fraction_role_2": profession_role_mapping,
        "profession_evidence_disposition": (
            "observation_only_not_used_as_recovery_source_or_profession_proof"
        ),
        "limitations": limitations,
    }


def audit_identity(conn: sqlite3.Connection) -> dict[str, Any]:
    require_schema(conn)
    mapping = canonical_avatar_mapping()
    state = exact_profile_state(conn)
    profile = state.pop("profile")
    recovery_receipt = latest_completed_recovery(conn)
    normalized = normalize_ghostnetwork_profile_identity(profile)
    lkg = conn.execute(
        "SELECT profile_revision, checksum, source, snapshot_json, created_at "
        "FROM profile_last_known_good WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    lkg_identity = None
    if lkg:
        lkg_identity = identity_projection(recovery.loads_object(lkg["snapshot_json"]))
    evidence = historical_identity_evidence(conn)
    recovery_profile_matches_current = (
        int(recovery_receipt["current_profile_revision"] or 0) == int(state["revision"])
        and str(recovery_receipt["current_profile_checksum"] or "") == state["stored_checksum"]
    )
    return {
        "ok": True,
        "command": "identity-audit",
        "read_only_database": True,
        "tool_version": TOOL_VERSION,
        "canonical_username_column": CANONICAL_USERNAME,
        "current_profile": {
            "revision": state["revision"],
            "checksum": state["stored_checksum"],
            "identity": identity_projection(profile),
            "normalized_gn_identity": normalized,
            "profile_invariant_sha256": recovery.digest(profile_invariant(profile)),
        },
        "approved_identity_change_contract": {
            **EXPECTED_IDENTITY,
            "clan_display": "Echo Wolności",
            "clan_code": EXPECTED_CLAN_CODE,
            "profession_code": EXPECTED_PROFESSION_CODE,
            "field_provenance": copy.deepcopy(CHANGE_PROVENANCE),
            "profession_is_historical_restore": False,
        },
        "canonical_avatar_mapping": mapping,
        "profession_sources": {
            "top_level_profession": profile.get("profession"),
            "top_level_role": profile.get("role"),
            "fraction_role": (
                profile.get("fraction", {}).get("role")
                if isinstance(profile.get("fraction"), dict) else None
            ),
            "operator_profession": (
                profile.get("operator", {}).get("profession")
                if isinstance(profile.get("operator"), dict) else None
            ),
            "ghost_profession": profile.get("ghost_profession"),
        },
        "historical_evidence": evidence,
        "completed_recovery": recovery_receipt,
        "recovery_profile_matches_current": recovery_profile_matches_current,
        "current_lkg": {
            "present": bool(lkg),
            "revision": int(lkg["profile_revision"] or 0) if lkg else None,
            "checksum": lkg["checksum"] if lkg else None,
            "source": lkg["source"] if lkg else None,
            "created_at": lkg["created_at"] if lkg else None,
            "identity": lkg_identity,
        },
        "repair_required": any(profile.get(key) != value for key, value in EXPECTED_IDENTITY.items()),
        "database_writes": 0,
    }


def build_plan(conn: sqlite3.Connection) -> dict[str, Any]:
    audit = audit_identity(conn)
    profile = exact_profile_state(conn)["profile"]
    normalized = normalize_ghostnetwork_profile_identity({
        **profile,
        "profession": EXPECTED_IDENTITY["profession"],
    })
    if normalized != {
        "clan_code": EXPECTED_CLAN_CODE,
        "profession_code": EXPECTED_PROFESSION_CODE,
        "catalog_valid": True,
        "validation_errors": [],
    }:
        raise IdentityRepairError("Current clan representation is not canonical Echo Wolności")
    state = exact_profile_state(conn, include_profile=False)
    external = external_invariants(conn)
    base = latest_completed_recovery(conn)
    if (
        int(base["current_profile_revision"] or 0) != int(state["revision"])
        or str(base["current_profile_checksum"] or "") != state["stored_checksum"]
    ):
        raise IdentityRepairError(
            "Current profile is not the exact completed Sprint 130.11 recovery result"
        )
    core = {
        "format_version": PLAN_VERSION,
        "tool_version": TOOL_VERSION,
        "canonical_username": CANONICAL_USERNAME,
        "reason": REASON,
        "approved_changes": copy.deepcopy(EXPECTED_IDENTITY),
        "change_provenance": copy.deepcopy(CHANGE_PROVENANCE),
        "mutable_profile_fields": sorted(MUTABLE_PROFILE_FIELDS),
        "preconditions": {
            "profile_revision": state["revision"],
            "profile_checksum": state["stored_checksum"],
            "profile_invariant_sha256": audit["current_profile"]["profile_invariant_sha256"],
            "completed_recovery_plan_id": base["plan_id"],
            "completed_recovery_plan_sha256": base["plan_sha256"],
            "completed_recovery_status": base["status"],
            "external_invariants": external,
        },
        "canonical_avatar_mapping": audit["canonical_avatar_mapping"],
    }
    seed = recovery.digest(core)
    core["plan_id"] = "trollu2_identity_" + seed[:24]
    core["plan_sha256"] = recovery.digest(core)
    return core


def validate_plan(plan: dict[str, Any]) -> None:
    if plan.get("format_version") != PLAN_VERSION or plan.get("tool_version") != TOOL_VERSION:
        raise IdentityRepairError("Unsupported identity repair plan")
    if plan.get("canonical_username") != CANONICAL_USERNAME:
        raise IdentityRepairError("Identity plan belongs to another account")
    if plan.get("approved_changes") != EXPECTED_IDENTITY:
        raise IdentityRepairError("Identity plan has unexpected field values")
    if plan.get("change_provenance") != CHANGE_PROVENANCE:
        raise IdentityRepairError("Identity plan has unexpected change provenance")
    if plan.get("mutable_profile_fields") != sorted(MUTABLE_PROFILE_FIELDS):
        raise IdentityRepairError("Identity plan has unexpected mutation scope")
    expected = dict(plan)
    checksum = expected.pop("plan_sha256", "")
    if checksum != recovery.digest(expected):
        raise IdentityRepairError("Identity plan SHA-256 mismatch")


def load_plan(path: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IdentityRepairError(f"Cannot load identity plan: {exc}") from exc
    if not isinstance(value, dict):
        raise IdentityRepairError("Identity plan must be a JSON object")
    validate_plan(value)
    return value


def precondition_blockers(conn: sqlite3.Connection, plan: dict[str, Any]) -> list[str]:
    blockers = []
    state = exact_profile_state(conn)
    profile = state.pop("profile")
    expected = plan["preconditions"]
    if state["revision"] != int(expected["profile_revision"]):
        blockers.append("CURRENT_PROFILE_CHANGED_REPLAN_REQUIRED:revision")
    if state["stored_checksum"] != expected["profile_checksum"]:
        blockers.append("CURRENT_PROFILE_CHANGED_REPLAN_REQUIRED:checksum")
    if recovery.digest(profile_invariant(profile)) != expected["profile_invariant_sha256"]:
        blockers.append("CURRENT_PROFILE_CHANGED_REPLAN_REQUIRED:non_identity_fields")
    base = latest_completed_recovery(conn)
    if (
        base["plan_id"] != expected["completed_recovery_plan_id"]
        or base["plan_sha256"] != expected["completed_recovery_plan_sha256"]
        or base["status"] != "complete"
    ):
        blockers.append("CURRENT_RECOVERY_CHANGED_REPLAN_REQUIRED")
    if external_invariants(conn) != expected["external_invariants"]:
        blockers.append("CURRENT_GAMEPLAY_STATE_CHANGED_REPLAN_REQUIRED")
    if canonical_avatar_mapping() != plan["canonical_avatar_mapping"]:
        blockers.append("CURRENT_IDENTITY_MAPPING_CHANGED_REPLAN_REQUIRED")
    return blockers


def ensure_receipt_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {RECEIPTS_TABLE} (
            plan_id TEXT PRIMARY KEY,
            canonical_username TEXT NOT NULL,
            plan_sha256 TEXT NOT NULL,
            recovery_plan_id TEXT NOT NULL,
            status TEXT NOT NULL,
            expected_revision INTEGER NOT NULL,
            expected_checksum TEXT NOT NULL,
            result_revision INTEGER NOT NULL,
            result_checksum TEXT NOT NULL,
            before_identity_json TEXT NOT NULL,
            after_identity_json TEXT NOT NULL,
            change_provenance_json TEXT NOT NULL,
            invariant_sha256 TEXT NOT NULL,
            external_invariants_sha256 TEXT NOT NULL,
            reason TEXT NOT NULL,
            operator_username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            verified_at TEXT,
            promoted_at TEXT
        )
        """
    )


def receipt(conn: sqlite3.Connection, plan_id: str) -> dict[str, Any] | None:
    if RECEIPTS_TABLE not in recovery.table_names(conn):
        return None
    row = conn.execute(f"SELECT * FROM {RECEIPTS_TABLE} WHERE plan_id=?", (plan_id,)).fetchone()
    return dict(row) if row else None


def receipt_contract_blockers(record: dict[str, Any], plan: dict[str, Any]) -> list[str]:
    expected = plan["preconditions"]
    blockers = []
    checks = {
        "canonical_username": CANONICAL_USERNAME,
        "plan_sha256": plan["plan_sha256"],
        "recovery_plan_id": expected["completed_recovery_plan_id"],
        "expected_revision": int(expected["profile_revision"]),
        "expected_checksum": expected["profile_checksum"],
        "invariant_sha256": expected["profile_invariant_sha256"],
        "external_invariants_sha256": expected["external_invariants"]["summary_sha256"],
        "reason": REASON,
    }
    for field, value in checks.items():
        current = record.get(field)
        if field in {"expected_revision"}:
            current = int(current or 0)
        if current != value:
            blockers.append("identity_receipt_field_mismatch:" + field)
    if recovery.loads_object(record.get("change_provenance_json")) != CHANGE_PROVENANCE:
        blockers.append("identity_receipt_field_mismatch:change_provenance")
    if recovery.loads_object(record.get("after_identity_json")) != {
        **recovery.loads_object(record.get("after_identity_json")),
        **EXPECTED_IDENTITY,
    }:
        blockers.append("identity_receipt_after_identity_mismatch")
    if record.get("status") not in {"applied", "complete"}:
        blockers.append("identity_receipt_status_invalid")
    return blockers


def apply_identity(db_path: str, plan: dict[str, Any], operator: str) -> dict[str, Any]:
    with recovery.write_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        # SQLite DDL is transactional here: a failed precondition rolls back
        # both the receipt schema creation and every gameplay mutation.
        ensure_receipt_schema(conn)
        existing = receipt(conn, plan["plan_id"])
        if existing:
            receipt_blockers = receipt_contract_blockers(existing, plan)
            if receipt_blockers:
                raise IdentityRepairError("Identity receipt invalid: " + ", ".join(receipt_blockers))
            return {"duplicate": True, **existing}
        blockers = precondition_blockers(conn, plan)
        if blockers:
            raise IdentityRepairError("; ".join(blockers))
        state = exact_profile_state(conn)
        profile = state.pop("profile")
        before_identity = identity_projection(profile)
        candidate = copy.deepcopy(profile)
        candidate.update(copy.deepcopy(EXPECTED_IDENTITY))
        if recovery.digest(profile_invariant(candidate)) != plan["preconditions"]["profile_invariant_sha256"]:
            raise IdentityRepairError("Candidate changed a non-identity profile field")
        errors = recovery.validate_profile_contract(candidate, CANONICAL_USERNAME)
        if errors:
            raise IdentityRepairError("Identity candidate invalid: " + ", ".join(errors))
        normalized = normalize_ghostnetwork_profile_identity(candidate)
        if not normalized["catalog_valid"] or normalized["clan_code"] != EXPECTED_CLAN_CODE \
                or normalized["profession_code"] != EXPECTED_PROFESSION_CODE:
            raise IdentityRepairError("Identity candidate violates clan/profession contract")
        candidate_json = recovery.canonical_json(candidate)
        candidate_checksum = recovery.profile_checksum(candidate)
        result_revision = state["revision"] + 1
        now = recovery.utc_now()
        updated = conn.execute(
            "UPDATE users SET profile_json=?, updated_at=?, profile_revision=?, "
            "profile_checksum=?, profile_integrity_status='valid' "
            "WHERE username=? AND profile_revision=? AND profile_checksum=?",
            (
                candidate_json, now, result_revision, candidate_checksum,
                CANONICAL_USERNAME, state["revision"], state["stored_checksum"],
            ),
        )
        if updated.rowcount != 1:
            raise IdentityRepairError("Identity profile CAS failed")
        conn.execute(
            f"INSERT INTO {RECEIPTS_TABLE} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                plan["plan_id"], CANONICAL_USERNAME, plan["plan_sha256"],
                plan["preconditions"]["completed_recovery_plan_id"], "applied",
                state["revision"], state["stored_checksum"], result_revision,
                candidate_checksum, recovery.canonical_json(before_identity),
                recovery.canonical_json(identity_projection(candidate)),
                recovery.canonical_json(CHANGE_PROVENANCE),
                plan["preconditions"]["profile_invariant_sha256"],
                plan["preconditions"]["external_invariants"]["summary_sha256"],
                REASON, operator, now, now, None, None,
            ),
        )
    return {
        "duplicate": False,
        "plan_id": plan["plan_id"],
        "status": "applied",
        "profile_revision": result_revision,
        "profile_checksum": candidate_checksum,
        "changed_fields": sorted(MUTABLE_PROFILE_FIELDS),
    }


def verify_identity(conn: sqlite3.Connection, plan: dict[str, Any]) -> dict[str, Any]:
    require_schema(conn)
    record = receipt(conn, plan["plan_id"])
    blockers = []
    if not record:
        return {"ok": False, "blockers": ["identity_receipt_missing"]}
    blockers.extend(receipt_contract_blockers(record, plan))
    state = exact_profile_state(conn)
    profile = state.pop("profile")
    if state["revision"] != int(record["result_revision"]):
        blockers.append("profile_revision_differs_from_identity_receipt")
    if state["stored_checksum"] != record["result_checksum"]:
        blockers.append("profile_checksum_differs_from_identity_receipt")
    for key, value in EXPECTED_IDENTITY.items():
        if profile.get(key) != value:
            blockers.append("identity_field_mismatch:" + key)
    if recovery.digest(profile_invariant(profile)) != plan["preconditions"]["profile_invariant_sha256"]:
        blockers.append("non_identity_profile_fields_changed")
    current_external = external_invariants(conn)
    if current_external != plan["preconditions"]["external_invariants"]:
        blockers.append("canonical_gameplay_state_changed")
    normalized = normalize_ghostnetwork_profile_identity(profile)
    if not normalized["catalog_valid"] or normalized["clan_code"] != EXPECTED_CLAN_CODE \
            or normalized["profession_code"] != EXPECTED_PROFESSION_CODE:
        blockers.append("canonical_clan_profession_invalid")
    apps = current_external["inventory"]["player_apps"]["count"]
    tools = current_external["inventory"]["player_tool_files"]["count"]
    lkg = conn.execute(
        "SELECT profile_revision, snapshot_json, checksum, source FROM profile_last_known_good WHERE username=?",
        (CANONICAL_USERNAME,),
    ).fetchone()
    lkg_matches = False
    if lkg and record["status"] == "complete":
        snapshot = recovery.loads_object(lkg["snapshot_json"])
        lkg_matches = (
            int(lkg["profile_revision"] or 0) == state["revision"]
            and recovery.digest(snapshot) == str(lkg["checksum"] or "")
            and all(snapshot.get(key) == value for key, value in EXPECTED_IDENTITY.items())
        )
        if not lkg_matches:
            blockers.append("identity_lkg_mismatch")
    return {
        "ok": not blockers,
        "blockers": sorted(set(blockers)),
        "receipt_status": record["status"],
        "profile": {
            "revision": state["revision"],
            "checksum": state["stored_checksum"],
            "identity": identity_projection(profile),
            "level": profile.get("level"),
            "respect": profile.get("respect"),
            "exp": profile.get("exp"),
            "hackcoins": profile.get("hackcoins"),
        },
        "inventory": {"apps": apps, "tools": tools, "expected_11_11": apps == 11 and tools == 11},
        "canonical_state_sha256": current_external["summary_sha256"],
        "ghostnetwork_sha256": recovery.digest(current_external["ghostnetwork"]),
        "lkg_matches_identity_profile": lkg_matches,
    }


def promote_lkg(db_path: str, plan: dict[str, Any], final_checksum: str) -> dict[str, Any]:
    with recovery.readonly_connection(db_path) as conn:
        verification = verify_identity(conn, plan)
        if not verification["ok"]:
            raise IdentityRepairError("Identity verify failed: " + ", ".join(verification["blockers"]))
        record = receipt(conn, plan["plan_id"])
        if record["status"] == "complete":
            return {"duplicate": True, "status": "complete", "profile_checksum": record["result_checksum"]}
        if record["status"] != "applied":
            raise IdentityRepairError("Identity receipt is not ready for LKG promotion")
        state = exact_profile_state(conn)
        profile = state.pop("profile")
        if state["stored_checksum"] != final_checksum:
            raise IdentityRepairError("--final-checksum does not match verified identity profile")
        snapshot = recovery.lkg_snapshot_value(profile, top_level=True)
        snapshot_json = recovery.canonical_json(snapshot)
        snapshot_checksum = recovery.digest(snapshot)
    now = recovery.utc_now()
    with recovery.write_connection(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        record = receipt(conn, plan["plan_id"])
        if record and record["status"] == "complete":
            return {"duplicate": True, "status": "complete", "profile_checksum": record["result_checksum"]}
        state_now = exact_profile_state(conn, include_profile=False)
        if state_now["revision"] != state["revision"] or state_now["stored_checksum"] != state["stored_checksum"]:
            raise IdentityRepairError("Profile changed before identity LKG promotion")
        locked_verification = verify_identity(conn, plan)
        if not locked_verification["ok"]:
            raise IdentityRepairError("Identity changed before LKG promotion")
        conn.execute(
            "INSERT INTO profile_last_known_good "
            "(username, profile_revision, schema_version, snapshot_json, checksum, source, created_at, validation_version) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(username) DO UPDATE SET "
            "profile_revision=excluded.profile_revision, schema_version=excluded.schema_version, "
            "snapshot_json=excluded.snapshot_json, checksum=excluded.checksum, source=excluded.source, "
            "created_at=excluded.created_at, validation_version=excluded.validation_version",
            (
                CANONICAL_USERNAME, state["revision"], state["schema_version"], snapshot_json,
                snapshot_checksum, "sprint_130_11.identity_repair", now, state["validation_version"],
            ),
        )
        conn.execute(
            f"UPDATE {RECEIPTS_TABLE} SET status='complete', verified_at=?, promoted_at=? "
            "WHERE plan_id=? AND status='applied'",
            (now, now, plan["plan_id"]),
        )
    return {
        "duplicate": False,
        "status": "complete",
        "profile_revision": state["revision"],
        "profile_checksum": state["stored_checksum"],
        "lkg_checksum": snapshot_checksum,
    }


def write_plan(path: str, plan: dict[str, Any], overwrite: bool) -> None:
    output = Path(path)
    if output.exists() and not overwrite:
        raise IdentityRepairError(f"Plan already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_write(args: argparse.Namespace) -> str:
    operator = str(getattr(args, "authorized_by", "") or "").strip()
    if not getattr(args, "write", False) or not operator:
        raise IdentityRepairError("Write command requires --write and --authorized-by")
    return operator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=os.environ.get("CHAOS_DB_PATH", "data/game.sqlite3"))
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("--db", default=argparse.SUPPRESS)
    plan = sub.add_parser("plan")
    plan.add_argument("--db", default=argparse.SUPPRESS)
    plan.add_argument("--output", required=True)
    plan.add_argument("--overwrite", action="store_true")
    dry = sub.add_parser("dry-run")
    dry.add_argument("--db", default=argparse.SUPPRESS)
    dry.add_argument("--plan", required=True)
    apply_cmd = sub.add_parser("apply")
    apply_cmd.add_argument("--db", default=argparse.SUPPRESS)
    apply_cmd.add_argument("--plan", required=True)
    apply_cmd.add_argument("--plan-sha256", required=True)
    apply_cmd.add_argument("--write", action="store_true")
    apply_cmd.add_argument("--authorized-by", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--db", default=argparse.SUPPRESS)
    verify.add_argument("--plan", required=True)
    promote = sub.add_parser("promote-lkg")
    promote.add_argument("--db", default=argparse.SUPPRESS)
    promote.add_argument("--plan", required=True)
    promote.add_argument("--plan-sha256", required=True)
    promote.add_argument("--final-checksum", required=True)
    promote.add_argument("--write", action="store_true")
    promote.add_argument("--authorized-by", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "audit":
            with recovery.readonly_connection(args.db) as conn:
                recovery.print_json(audit_identity(conn))
            return 0
        if args.command == "plan":
            with recovery.readonly_connection(args.db) as conn:
                plan = build_plan(conn)
            write_plan(args.output, plan, args.overwrite)
            recovery.print_json({"ok": True, "command": "plan", "read_only_database": True,
                                 "plan_id": plan["plan_id"], "plan_sha256": plan["plan_sha256"],
                                 "output": str(Path(args.output).resolve())})
            return 0
        plan = load_plan(args.plan)
        if getattr(args, "plan_sha256", plan["plan_sha256"]) != plan["plan_sha256"]:
            raise IdentityRepairError("--plan-sha256 mismatch")
        if args.command == "dry-run":
            with recovery.readonly_connection(args.db) as conn:
                blockers = precondition_blockers(conn, plan)
            recovery.print_json({"ok": not blockers, "command": "dry-run", "read_only_database": True,
                                 "plan_id": plan["plan_id"], "blockers": blockers,
                                 "planned_profile_fields": sorted(MUTABLE_PROFILE_FIELDS),
                                 "planned_non_profile_writes": [RECEIPTS_TABLE],
                                 "ghostnetwork_planned_writes": 0})
            return 0 if not blockers else 1
        if args.command == "apply":
            result = apply_identity(args.db, plan, require_write(args))
            recovery.print_json({"ok": True, "command": "apply", "database_writes": True, "result": result})
            return 0
        if args.command == "verify":
            with recovery.readonly_connection(args.db) as conn:
                result = verify_identity(conn, plan)
            recovery.print_json({"command": "verify", "read_only_database": True, **result})
            return 0 if result["ok"] else 1
        operator = require_write(args)
        result = promote_lkg(args.db, plan, args.final_checksum)
        recovery.print_json({"ok": True, "command": "promote-lkg", "database_writes": True,
                             "authorized_by": operator, "result": result})
        return 0
    except (IdentityRepairError, recovery.RecoveryGateError, sqlite3.Error, OSError, ValueError) as exc:
        recovery.print_json({"ok": False, "command": getattr(args, "command", ""),
                             "error": exc.__class__.__name__, "reason": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
