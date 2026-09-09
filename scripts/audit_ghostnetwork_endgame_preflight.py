#!/usr/bin/env python3
"""Strict, read-only production preflight for the first GhostSignal E2E."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import GHOSTNETWORK_ENDGAME_FLAGS, GHOSTNETWORK_RANKING_POLICY  # noqa: E402
from database import DB_PATH, db_connect  # noqa: E402
from ghostnetwork import GhostNetworkRepository  # noqa: E402
from ghostnetwork.catalog import get_catalog_diagnostics  # noqa: E402
from ghostnetwork.closure import resolve_endgame_conflict_gate  # noqa: E402
from ghostnetwork.endgame import build_territory_consumption_plan  # noqa: E402
from ghostnetwork.module_state import GhostModuleStateService  # noqa: E402
from ghostnetwork.narrative_support import NarrativeSupportLayer  # noqa: E402
from ghostnetwork.topology import GhostTopologyService  # noqa: E402


WATCHED_TABLES = (
    "ghost_cycle_lock_snapshots", "ghost_signals", "ghost_signal_rankings",
    "ghost_reward_ledger", "ghost_signal_territory_consumptions", "ghost_signal_shows",
)


def _counts(db_path):
    with db_connect(db_path) as conn:
        known = {row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        return {
            table: int(conn.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()["count"])
            if table in known else None
            for table in WATCHED_TABLES
        }


def _runtime_status():
    try:
        result = subprocess.run(
            ["pm2", "jlist"], check=False, capture_output=True, text=True, timeout=10,
        )
        rows = json.loads(result.stdout or "[]") if result.returncode == 0 else []
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160], "processes": {}}
    wanted = {"chaos", "chaos-territory-worker", "chaos-ollama-worker", "chaos-narrative-publisher"}
    processes = {
        str(item.get("name") or ""): str((item.get("pm2_env") or {}).get("status") or "")
        for item in rows if str(item.get("name") or "") in wanted
    }
    return {"ok": wanted.issubset(processes) and all(value == "online" for value in processes.values()),
            "processes": processes}


def _git_head():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, check=False,
            capture_output=True, text=True, timeout=10,
        )
        value = str(result.stdout or "").strip()
        return {"ok": result.returncode == 0 and len(value) == 40, "head": value}
    except Exception as exc:
        return {"ok": False, "head": "", "error": str(exc)[:160]}


def _database_health(db_path):
    try:
        with db_connect(db_path) as conn:
            result = str(conn.execute("PRAGMA quick_check").fetchone()[0] or "")
        return {"ok": result.lower() == "ok", "quick_check": result}
    except Exception as exc:
        return {"ok": False, "quick_check": "", "error": str(exc)[:160]}


def _pending_endgame_work(db_path):
    result = {"pending_rewards": 0, "delta_jobs": 0}
    try:
        with db_connect(db_path) as conn:
            result["pending_rewards"] = int(conn.execute(
                "SELECT COUNT(*) FROM ghost_reward_ledger WHERE status IN ('pending', 'processing')"
            ).fetchone()[0])
            result["delta_jobs"] = int(conn.execute(
                "SELECT COUNT(*) FROM ghostnetwork_delta_delivery_jobs "
                "WHERE status IN ('pending', 'processing')"
            ).fetchone()[0])
    except Exception as exc:
        result["error"] = str(exc)[:160]
    result["ok"] = not result.get("error") and not result["pending_rewards"] and not result["delta_jobs"]
    return result


def audit(db_path=DB_PATH, *, strict=False, check_runtime=True, backup_path="",
          backup_max_age_minutes=120, expect="entry"):
    expect = str(expect or "entry").strip().lower()
    if expect not in {"entry", "blocked"}:
        raise ValueError("expect must be 'entry' or 'blocked'")
    repository = GhostNetworkRepository(db_path=db_path, ensure_schema=False)
    before = _counts(db_path)
    cycles = repository.list_cycles(limit=100)
    blocking = [cycle for cycle in cycles if cycle.get("status") in {"preparing", "active", "transmitting", "stabilizing"}]
    cycle = repository.get_active_cycle()
    errors = []
    if len(blocking) != 1:
        errors.append("expected_exactly_one_blocking_cycle")
    if not cycle:
        errors.append("active_cycle_missing")
        return {"ok": False, "strict": strict, "mode": "read_only", "errors": errors,
                "before": before, "after": _counts(db_path)}

    cycle_id = cycle["cycle_id"]
    parts = repository.list_parts(cycle_id)
    connections = repository.list_connections(cycle_id)
    active_parts = [part for part in parts if part.get("status") == "active"]
    closing = [part for part in parts if part.get("status") != "active"]
    conflicts = repository.list_strategic_conflicts(cycle_id=cycle_id, limit=1000)
    conflict_gate = resolve_endgame_conflict_gate(parts, conflicts)
    blockers = conflict_gate.get("blocking_conflicts") or []
    modules = GhostModuleStateService(repository).resolve_cycle_module_states(cycle_id)
    topology = repository.get_cycle(cycle_id) or {}
    topology_validation = GhostTopologyService(repository).validate_topology(cycle_id)
    resolved_ids = [item.get("conflict_id") for item in conflicts if item.get("status") in {"resolved", "closed"}]
    production_conflicts = repository.list_endgame_production_conflicts(
        resolved_ids, territory_ids=[item.get("territory_id") for item in parts if item.get("territory_id")], limit=500,
    )
    territory_plan = build_territory_consumption_plan(
        parts, conflicts, repository.list_endgame_territories(limit=1000), production_conflicts,
    )
    catalog = get_catalog_diagnostics()
    narrative = NarrativeSupportLayer().verify()
    locks = repository.list_cycle_lock_snapshots(cycle_id)
    signals = repository.list_signals_for_cycle(cycle_id, limit=100)
    rewards = repository.list_rewards(cycle_id=cycle_id, limit=5000)
    with db_connect(db_path) as conn:
        active_cycle_consumptions = int(conn.execute(
            "SELECT COUNT(*) FROM ghost_signal_territory_consumptions WHERE cycle_id = ?",
            (cycle_id,),
        ).fetchone()[0])
    runtime = _runtime_status() if check_runtime else {"ok": True, "skipped": True, "processes": {}}
    git = _git_head()
    database_health = _database_health(db_path)
    pending_work = _pending_endgame_work(db_path)
    disk = shutil.disk_usage(os.path.dirname(os.path.abspath(db_path)) or ".")
    backup = {"path": os.path.abspath(backup_path) if backup_path else "", "exists": False,
              "readable": False, "fresh": False, "age_seconds": None}
    if backup_path:
        backup["exists"] = os.path.isfile(backup_path)
        if backup["exists"]:
            backup["age_seconds"] = max(0, int(time.time() - os.path.getmtime(backup_path)))
            backup["fresh"] = backup["age_seconds"] <= max(1, int(backup_max_age_minutes)) * 60
            try:
                with db_connect(backup_path) as conn:
                    quick_check = str(conn.execute("PRAGMA quick_check").fetchone()[0] or "")
                backup["quick_check"] = quick_check
                backup["readable"] = quick_check.lower() == "ok"
            except Exception as exc:
                backup["error"] = str(exc)[:160]

    checks = {
        "one_active_cycle": len(blocking) == 1 and cycle.get("status") == "active",
        "catalog_valid": bool((catalog.get("validation") or {}).get("ok")),
        "topology_ring_valid": bool(topology_validation.get("valid"))
        and len(connections) == 20
        and topology_validation.get("topology_checksum") == topology.get("topology_checksum"),
        "no_lock_or_signal": not locks and not signals,
        "no_rewards_for_active_cycle": not rewards,
        "no_pending_endgame_work": bool(pending_work.get("ok")),
        "exactly_one_conflict_blocker": len(blockers) == 1,
        "show_and_ranking_schema_ready": before.get("ghost_signal_shows") is not None and before.get("ghost_signal_rankings") is not None,
        "narrative_fallbacks_ready": bool(narrative.get("ok")),
        "runtime_online": bool(runtime.get("ok")),
        "git_head_available": bool(git.get("ok")),
        "database_quick_check": bool(database_health.get("ok")),
        "disk_space_min_1gb": disk.free >= 1024 ** 3,
        "backup_readable_and_fresh": bool(backup.get("readable") and backup.get("fresh")),
        "territory_executor_enabled": bool(GHOSTNETWORK_ENDGAME_FLAGS.get("territory_consumption_enabled")),
    }
    if expect == "entry":
        checks.update({
            "entry_state_19_of_20": len(parts) == 20 and len(active_parts) == 19 and len(closing) == 1,
            "closing_part_public": len(closing) == 1 and closing[0].get("status") == "public",
        })
    else:
        checks.update({
            "blocked_checkpoint_20_of_20": len(parts) == 20 and len(active_parts) == 20 and not closing,
            "blocked_checkpoint_no_irreversible_effects": not locks and not signals and not rewards
            and active_cycle_consumptions == 0,
            "blocked_checkpoint_gate_blocks": bool(conflict_gate.get("network_complete"))
            and not conflict_gate.get("ready") and len(blockers) == 1,
        })
    if strict:
        errors.extend(sorted(key for key, value in checks.items() if not value))
    after = _counts(db_path)
    mutations = {key: {"before": before[key], "after": after[key]} for key in before if before[key] != after[key]}
    if mutations:
        errors.append("audit_mutated_watched_tables")
    expected_signal_id = f"ghost_signal_{cycle_id}"
    report = {
        "ok": not errors, "strict": strict, "mode": "read_only", "expected_phase": expect,
        "contract": "138.prepare.gn.signal.3.preflight.v1",
        "cycle_id": cycle_id, "phase": cycle.get("status"), "network_complete": len(active_parts) == 20,
        "ready_after_last_part": len(active_parts) == 19 and len(closing) == 1,
        "closing_part": closing[0] if len(closing) == 1 else None,
        "conflict_blockers": blockers, "machine_progress": modules.get("machines") or [],
        "connections": len(connections), "expected_signal_public_id": f"GHOSTSIGNAL-{int(cycle.get('signal_number') or 0):04d}",
        "topology_validation": topology_validation,
        "expected_signal_id": expected_signal_id,
        "expected_next_version": int(cycle.get("ghostsystem_version") or 0) + 1,
        "expected_rewards": {"policy": "immutable_lock_reward_plan"},
        "territory_plan": territory_plan, "expected_events": [
            "ghost.cycle_locked", "ghost.signal_sent", "ghost.signal_show_started",
            "ghost.signal_ranking_created", "ghost.version_changed", "ghost.stabilization_started",
        ],
        "expected_media": ["blacknet", "cyberner", "googleplex_news"],
        "ranking_policy": GHOSTNETWORK_RANKING_POLICY, "checks": checks,
        "runtime": runtime, "git": git, "database_health": database_health,
        "pending_endgame_work": pending_work,
        "active_cycle_territory_consumptions": active_cycle_consumptions,
        "backup": backup, "backup_max_age_minutes": int(backup_max_age_minutes),
        "disk_free_bytes": disk.free,
        "mutations": mutations, "errors": sorted(set(errors)), "before": before, "after": after,
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--backup", default="")
    parser.add_argument("--backup-max-age-minutes", type=int, default=120)
    parser.add_argument("--expect", choices=("entry", "blocked"), default="entry")
    parser.add_argument("--skip-runtime", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = audit(
        args.db, strict=args.strict, check_runtime=not args.skip_runtime,
        backup_path=args.backup, backup_max_age_minutes=args.backup_max_age_minutes,
        expect=args.expect,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=None if args.compact else 2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
