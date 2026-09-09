#!/usr/bin/env python3
"""Read-only strict postflight for one GhostSignal cycle lineage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import DB_PATH  # noqa: E402
from ghostnetwork import GhostNetworkRepository, GhostNetworkService  # noqa: E402


def _signal_checksum(payload):
    encoded = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def audit(cycle_id, db_path=DB_PATH, *, strict=False):
    repository = GhostNetworkRepository(db_path=db_path, ensure_schema=False)
    service = GhostNetworkService(repository=repository)
    cycle_id = str(cycle_id or "").strip()
    cycle = repository.get_cycle(cycle_id)
    signal = repository.get_signal_for_cycle(cycle_id)
    lock = repository.get_cycle_lock_snapshot(cycle_id)
    show = repository.get_signal_show_for_cycle(cycle_id)
    ranking = repository.get_cycle_ranking(cycle_id)
    parts = repository.list_parts(cycle_id) if cycle else []
    connections = repository.list_connections(cycle_id) if cycle else []
    rewards = repository.list_rewards(cycle_id=cycle_id, limit=5000)
    history = repository.list_historical_nodes_for_signal((signal or {}).get("signal_id")) if signal else []
    consumptions = repository.list_signal_territory_consumptions((signal or {}).get("signal_id"), limit=5000) if signal else []
    events = repository.list_events(cycle_id=cycle_id, limit=5000) if cycle else []
    event_counts = {}
    for event in events:
        event_type = str(event.get("event_type") or "")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    lock_validation = service.validate_locked_snapshot(cycle_id) if lock else {"valid": False, "reasons": ["missing"]}
    ranking_validation = service.ranking.validate(ranking) if ranking else {"valid": False, "reasons": ["missing"]}
    all_time = service.rebuild_signal_rankings_all_time()
    signal_checksum_valid = bool(signal) and _signal_checksum((signal or {}).get("payload") or {}) == (signal or {}).get("signal_checksum")
    snapshot = (lock or {}).get("snapshot") or {}
    territory_plan = snapshot.get("territory_consumption_plan") or {}
    expected_territories = {
        str(item.get("territory_id") or "") for item in territory_plan.get("entries") or []
        if str(item.get("territory_id") or "")
    } if territory_plan.get("execution_required") else set()
    actual_territories = {str(item.get("territory_id") or "") for item in consumptions}
    required_once = {
        "ghost.cycle_locked", "ghost.signal_created", "ghost.signal_sent",
        "ghost.version_changed", "ghost.restart_required", "ghost.stabilization_started",
        "ghost.signal_show_started", "ghost.signal_ranking_created",
        "ghost.endgame_postcommit_reconciled", "ghost.endgame_delta_reconciled",
    }
    next_cycles = [
        item for item in repository.list_cycles(limit=100)
        if cycle and int(item.get("signal_number") or 0) == int(cycle.get("signal_number") or 0) + 1
    ]
    active_next = [item for item in next_cycles if item.get("status") == "active"]
    reward_statuses = {}
    for reward in rewards:
        status = str(reward.get("status") or "")
        reward_statuses[status] = reward_statuses.get(status, 0) + 1
    ranking_snapshot = (ranking or {}).get("snapshot") or {}
    ranked_signal_ids = {
        str(item.get("signal_id") or "") for item in repository.list_signal_rankings(limit=1000)
    }

    checks = {
        "cycle_exists": bool(cycle),
        "one_lock": len(repository.list_cycle_lock_snapshots(cycle_id)) == 1 if cycle else False,
        "lock_checksum_valid": bool(lock_validation.get("valid")),
        "one_signal": len(repository.list_signals_for_cycle(cycle_id, limit=100)) == 1 if cycle else False,
        "signal_checksum_valid": signal_checksum_valid,
        "machines_4x5": len((snapshot.get("machine_progress") or [])) == 4 and all(
            int(item.get("parts_active") or 0) == 5 and item.get("machine_online")
            for item in snapshot.get("machine_progress") or []
        ),
        "parts_consumed_20": len(parts) == 20 and bool(signal) and all(
            item.get("status") == "consumed" and item.get("consumed_signal_id") == signal.get("signal_id")
            for item in parts
        ),
        "connections_closed": not connections,
        "historical_nodes_20": len(history) == 20,
        "territory_plan_exact_once": expected_territories == actual_territories,
        "rewards_created": bool(rewards),
        "rewards_projected": bool(rewards) and all(item.get("status") == "applied" for item in rewards),
        "required_events_exactly_once": all(event_counts.get(event_type) == 1 for event_type in required_once),
        "show_exists": bool(show),
        "ranking_exists": bool(ranking),
        "ranking_checksum_valid": bool(ranking_validation.get("valid")),
        "ranking_matches_signal": bool(signal and ranking_snapshot.get("signal_id") == signal.get("signal_id")),
        "all_time_rebuild_contains_signal": bool(signal and signal.get("signal_id") in ranked_signal_ids and all_time.get("ok")),
        "old_cycle_closed": bool(cycle and cycle.get("status") == "closed"),
        "show_completed": bool(show and show.get("status") == "completed"),
        "exactly_one_next_active_cycle": len(active_next) == 1,
    }
    final_checks = {"old_cycle_closed", "show_completed", "exactly_one_next_active_cycle", "rewards_projected"}
    integrity_errors = sorted(key for key, value in checks.items() if not value and key not in final_checks)
    pending = sorted(key for key, value in checks.items() if not value and key in final_checks)
    complete = not integrity_errors and not pending
    status = "complete" if complete else ("blocked" if integrity_errors else "in_progress")
    ok = complete if strict else not integrity_errors
    lineage = {
        "cycle_id": cycle_id,
        "lock_snapshot_id": (lock or {}).get("lock_snapshot_id") or "",
        "signal_id": (signal or {}).get("signal_id") or "",
        "show_id": (show or {}).get("show_id") or "",
        "ranking_id": (ranking or {}).get("ranking_id") or "",
        "reward_ids": [item.get("reward_id") for item in rewards],
        "event_ids": [item.get("event_id") for item in events],
        "next_cycle_id": active_next[0].get("cycle_id") if len(active_next) == 1 else "",
    }
    return {
        "ok": ok, "status": status, "strict": strict, "mode": "read_only",
        "contract": "138.prepare.gn.signal.3.postflight.v1", "cycle_id": cycle_id,
        "checks": checks, "integrity_errors": integrity_errors, "pending": pending,
        "counts": {"parts": len(parts), "connections": len(connections), "historical_nodes": len(history),
                   "rewards": len(rewards), "territories": len(consumptions), "events": len(events),
                   "rankings": int(bool(ranking)), "next_cycles": len(next_cycles)},
        "reward_statuses": reward_statuses, "event_counts": event_counts,
        "lock_validation": lock_validation, "ranking_validation": ranking_validation,
        "settlement": service.validate_rollover_settlement(cycle_id) if cycle else {"ok": False},
        "all_time": {"rebuilt_from_snapshots": all_time.get("rebuilt_from_snapshots", 0),
                     "players": len(all_time.get("players") or []), "clans": len(all_time.get("clans") or [])},
        "lineage": lineage,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycle-id", required=True)
    parser.add_argument("--db", default=DB_PATH)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    report = audit(args.cycle_id, args.db, strict=args.strict)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=None if args.compact else 2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
