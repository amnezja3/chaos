#!/usr/bin/env python3
"""Read-only strict postflight for one GhostSignal cycle lineage."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import DB_PATH  # noqa: E402
from ghostnetwork import GhostNetworkRepository, GhostNetworkService  # noqa: E402
from ghostnetwork.transmission import signal_payload_checksum  # noqa: E402


def _signal_checksum(payload):
    return signal_payload_checksum(payload or {})


def _parse_iso(value):
    text = str(value or "").strip()
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _production_conflict_chronology(repository, snapshot):
    parts = snapshot.get("parts") or []
    territory_ids = sorted({
        str(item.get("territory_id") or "").strip()
        for item in parts if str(item.get("territory_id") or "").strip()
    })
    conflict_ids = sorted({
        str(item.get("conflict_id") or "").strip()
        for item in parts if str(item.get("conflict_id") or "").strip()
    })
    lock_at = _parse_iso(snapshot.get("locked_at"))
    conflicts = repository.list_endgame_production_conflicts(
        conflict_ids,
        territory_ids=territory_ids,
        limit=500,
        include_unresolved=True,
    )
    violations = []
    for conflict in conflicts:
        status = str(conflict.get("status") or "").lower()
        resolved_at = _parse_iso(conflict.get("resolved_at") or conflict.get("closed_at"))
        if status not in {"resolved", "closed"}:
            reason = "still_unresolved"
        elif not resolved_at:
            reason = "missing_resolution_timestamp"
        elif not lock_at or resolved_at > lock_at:
            reason = "resolved_after_cycle_lock"
        else:
            continue
        violations.append({
            "conflict_id": conflict.get("conflict_id") or "",
            "status": status,
            "reason": reason,
            "resolved_at": conflict.get("resolved_at") or conflict.get("closed_at") or "",
            "lock_at": snapshot.get("locked_at") or "",
            "territory_ids": conflict.get("territory_ids") or [],
            "resolution_reason": conflict.get("resolution_reason") or "",
        })
    return {"ok": not violations, "checked": len(conflicts), "violations": violations}


def _transmission_reward_times(rewards, signal):
    # A cycle also contains discovery/activation rewards predating its finale.
    # Only this signal's rewards are effects of the audited transmission.
    signal_id = (signal or {}).get("signal_id")
    return [reward.get("created_at") for reward in rewards
            if signal_id and reward.get("signal_id") == signal_id]


def _transmission_chronology(show, signal, events, effect_times, *, required=False):
    """Check stored chronology; independent-reader tests prove the commit boundary.

    Historical 138 signals are reported as legacy, never rewritten or silently
    certified against the 139 contract. Operators can explicitly require 139.
    """
    by_type = {event["event_type"]: event for event in events}
    start = by_type.get("ghost.transmission_started")
    enforced = required or bool(start)
    if not enforced:
        return {"enforced": False, "ok": None, "status": "legacy", "violations": []}
    violations = []
    show_event = by_type.get("ghost.signal_show_started")
    sent = by_type.get("ghost.signal_sent")
    stabilized = by_type.get("ghost.stabilization_started")
    created = _parse_iso((show or {}).get("created_at"))
    timestamps = [_parse_iso(value) for value in effect_times if value]
    first_effect = min(timestamps) if timestamps else None
    if not start or not show_event or not sent or not stabilized:
        violations.append("missing_timeline_milestone")
    if not created or not first_effect or created > first_effect:
        violations.append("show_not_created_before_effects")
    if show and signal and (show.get("cycle_id") != signal.get("cycle_id")
                            or show.get("signal_id") != signal.get("signal_id")):
        violations.append("show_signal_lineage_mismatch")
    if start and show:
        payload = start.get("payload") or {}
        if (payload.get("signal_id") != (signal or {}).get("signal_id")
                or payload.get("lock_snapshot_id") != (signal or {}).get("lock_snapshot_id")
                or payload.get("started_at") != show.get("show_started_at")
                or payload.get("ends_at") != show.get("show_ends_at")
                or payload.get("phase_policy_version") != show.get("phase_policy_version")):
            violations.append("timeline_lineage_or_clock_changed")
    if start and show_event and sent and stabilized:
        versions = [int(e.get("state_version") or 0) for e in (start, show_event, sent, stabilized)]
        if not all(a < b for a, b in zip(versions, versions[1:])):
            violations.append("milestone_order_invalid")
        if any(int(e.get("state_version") or 0) >= versions[2]
               or int(e.get("state_version") or 0) <= versions[1]
               for e in events if e["event_type"] in {
                   "ghost.territories_consumed", "ghost.final_rewards_created", "ghost.parts_consumed",
                   "ghost.connections_closed", "ghost.abilities_disabled", "ghost.version_prepared"}):
            violations.append("effects_outside_show_to_sent_window")
        sent_at = _parse_iso((signal or {}).get("sent_at"))
        if not sent_at or any(t > sent_at for t in timestamps):
            violations.append("signal_sent_before_effects")
    return {"enforced": True, "ok": not violations,
            "status": "valid" if not violations else "invalid", "violations": violations,
            "show_created_at": (show or {}).get("created_at"),
            "first_effect_at": first_effect.isoformat() if first_effect else None,
            "signal_sent_at": (signal or {}).get("sent_at")}


def audit(cycle_id, db_path=DB_PATH, *, strict=False, require_transmission_timeline=False):
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
    lock_validation = service.validate_locked_snapshot(cycle_id) if lock else {"valid": False, "reasons": ["missing"]}
    ranking_validation = service.ranking.validate(ranking) if ranking else {"valid": False, "reasons": ["missing"]}
    all_time = service.rebuild_signal_rankings_all_time()
    signal_checksum_valid = bool(signal) and _signal_checksum((signal or {}).get("payload") or {}) == (signal or {}).get("signal_checksum")
    snapshot = (lock or {}).get("snapshot") or {}
    production_conflict_chronology = _production_conflict_chronology(repository, snapshot) if lock else {
        "ok": False, "checked": 0, "violations": [{"reason": "missing_lock_snapshot"}],
    }
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
    if require_transmission_timeline or repository.get_event_by_dedupe_key(
        f"ghost:transmission_started:{cycle_id}"
    ):
        required_once.update({"ghost.transmission_started", "ghost.final_rewards_created",
                              "ghost.parts_consumed", "ghost.connections_closed",
                              "ghost.abilities_disabled", "ghost.version_prepared"})
        if territory_plan.get("execution_required"):
            required_once.add("ghost.territories_consumed")
    timeline_types = {"ghost.transmission_started", "ghost.territories_consumed",
                      "ghost.final_rewards_created", "ghost.parts_consumed",
                      "ghost.connections_closed", "ghost.abilities_disabled", "ghost.version_prepared"}
    # The general event feed is capped at 1000 rows. Integrity must query the
    # required types directly or a busy first cycle loses its closing events.
    timeline_events = repository.list_events_by_types(cycle_id, required_once | timeline_types) if cycle else []
    required_events = [e for e in timeline_events if e["event_type"] in required_once]
    chronology = _transmission_chronology(show, signal, timeline_events,
        [p.get("consumed_at") for p in parts] + _transmission_reward_times(rewards, signal)
        + [t.get("consumed_at") for t in consumptions]
        + [e.get("created_at") for e in timeline_events
           if e["event_type"] in timeline_types - {"ghost.transmission_started"}],
        required=require_transmission_timeline)
    event_counts = {event_type: 0 for event_type in sorted(required_once)}
    for event in required_events:
        event_type = str(event.get("event_type") or "")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
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
        "production_conflicts_resolved_before_lock": bool(production_conflict_chronology.get("ok")),
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
    if chronology["enforced"]:
        checks["transmission_timeline_valid"] = chronology["ok"]
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
        "event_ids": [item.get("event_id") for item in required_events],
        "next_cycle_id": active_next[0].get("cycle_id") if len(active_next) == 1 else "",
    }
    return {
        "ok": ok, "status": status, "strict": strict, "mode": "read_only",
        "contract": "139.1.ghostsignal.postflight.v3", "cycle_id": cycle_id,
        "checks": checks, "integrity_errors": integrity_errors, "pending": pending,
        "counts": {"parts": len(parts), "connections": len(connections), "historical_nodes": len(history),
                   "rewards": len(rewards), "territories": len(consumptions),
                   "events": repository.count_events(cycle_id) if cycle else 0,
                   "required_events": len(required_events),
                   "rankings": int(bool(ranking)), "next_cycles": len(next_cycles)},
        "reward_statuses": reward_statuses, "event_counts": event_counts,
        "lock_validation": lock_validation, "ranking_validation": ranking_validation,
        "production_conflict_chronology": production_conflict_chronology,
        "transmission_chronology": chronology,
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
    parser.add_argument("--require-transmission-timeline", action="store_true",
                        help="Require Sprint 139 show-before-effects chronology, including on legacy cycles")
    args = parser.parse_args()
    report = audit(args.cycle_id, args.db, strict=args.strict,
                   require_transmission_timeline=args.require_transmission_timeline)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=None if args.compact else 2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
