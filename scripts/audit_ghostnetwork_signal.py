#!/usr/bin/env python3
"""Read-only production preflight for 138.prepare.gn.signal.1.

The command never calls cycle lock or transmission methods. It reports the
canonical conflict gate, machines, immutable-plan inputs and mutation guards.
"""

from __future__ import annotations

import argparse
import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import GHOSTNETWORK_ENDGAME_FLAGS, GHOSTNETWORK_ENDGAME_REWARD_POLICY  # noqa: E402
from database import DB_PATH, db_connect  # noqa: E402
from ghostnetwork import GhostNetworkRepository  # noqa: E402
from ghostnetwork.closure import resolve_endgame_conflict_gate  # noqa: E402
from ghostnetwork.endgame import build_territory_consumption_plan  # noqa: E402
from ghostnetwork.module_state import GhostModuleStateService  # noqa: E402


WATCHED_TABLES = (
    "ghost_cycle_lock_snapshots",
    "ghost_signals",
    "ghost_reward_ledger",
    "ghost_signal_territory_consumptions",
    "captured_targets",
    "player_areas",
)


def table_counts(db_path):
    result = {}
    with db_connect(db_path) as conn:
        known = {
            row["name"] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        for table in WATCHED_TABLES:
            result[table] = (
                int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])
                if table in known else None
            )
    return result


def audit(db_path):
    repository = GhostNetworkRepository(db_path=db_path, ensure_schema=False)
    before = table_counts(db_path)
    cycle = repository.get_active_cycle()
    errors = []
    if not cycle:
        errors.append("active_cycle_missing")
        return {
            "ok": False,
            "mode": "read_only",
            "errors": errors,
            "before": before,
            "after": table_counts(db_path),
        }

    cycle_id = cycle["cycle_id"]
    parts = repository.list_parts(cycle_id)
    conflicts = repository.list_strategic_conflicts(cycle_id=cycle_id, limit=1000)
    conflict_gate = resolve_endgame_conflict_gate(parts, conflicts)
    modules = GhostModuleStateService(repository).resolve_cycle_module_states(cycle_id)
    territories = repository.list_endgame_territories(limit=1000)
    resolved_conflict_ids = [
        item.get("conflict_id") for item in conflicts
        if str(item.get("status") or "").strip().lower() in {"resolved", "closed"}
    ]
    production_conflicts = repository.list_endgame_production_conflicts(
        resolved_conflict_ids,
        territory_ids=[part.get("territory_id") for part in parts if part.get("territory_id")],
        limit=500,
    )
    plan = build_territory_consumption_plan(
        parts,
        conflicts,
        territories,
        production_conflicts,
    )
    plan["execution_required_if_locked_now"] = bool(
        GHOSTNETWORK_ENDGAME_FLAGS.get("territory_consumption_enabled")
    )
    locks = repository.list_cycle_lock_snapshots(cycle_id)
    signals = repository.list_signals_for_cycle(cycle_id, limit=100)
    after = table_counts(db_path)
    mutations = {
        table: {"before": before.get(table), "after": after.get(table)}
        for table in WATCHED_TABLES
        if before.get(table) != after.get(table)
    }
    if mutations:
        errors.append("audit_mutated_watched_tables")
    return {
        "ok": not errors,
        "mode": "read_only",
        "contract": "138.prepare.gn.signal.1",
        "cycle": {
            "cycle_id": cycle_id,
            "signal_number": cycle.get("signal_number"),
            "status": cycle.get("status"),
            "parts": len(parts),
            "active_parts": sum(item.get("status") == "active" for item in parts),
            "locks": len(locks),
            "signals": len(signals),
        },
        "conflict_gate": conflict_gate,
        "machines": modules.get("machines") or [],
        "cycle_progress": modules.get("cycle_progress") or {},
        "territory_plan": plan,
        "production_conflicts": production_conflicts,
        "reward_policy": GHOSTNETWORK_ENDGAME_REWARD_POLICY,
        "territory_consumption_enabled": bool(
            GHOSTNETWORK_ENDGAME_FLAGS.get("territory_consumption_enabled")
        ),
        "production_signal_triggered_by_audit": False,
        "mutations": mutations,
        "errors": errors,
        "before": before,
        "after": after,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DB_PATH, help="SQLite database path")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Include vertices and captured target snapshots in the report",
    )
    args = parser.parse_args()
    report = audit(args.db)
    if not args.full:
        plan = report.get("territory_plan") or {}
        plan["entries"] = [
            {
                "territory_id": item.get("territory_id"),
                "owner_id": item.get("owner_id"),
                "clan_code": item.get("clan_code"),
                "role": item.get("role"),
                "reason": item.get("reason"),
                "source_conflict_id": item.get("source_conflict_id"),
                "area_size": item.get("area_size"),
                "publication_version": item.get("publication_version"),
                "target_count": len(item.get("targets") or []),
                "geometry_vertices": len(item.get("vertices") or []),
            }
            for item in plan.get("entries") or []
        ]
    print(json.dumps(
        report,
        ensure_ascii=False,
        sort_keys=True,
        indent=None if args.compact else 2,
    ))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
