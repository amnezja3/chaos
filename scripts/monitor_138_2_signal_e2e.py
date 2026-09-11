#!/usr/bin/env python3
"""Persistent, read-only production monitor for the 138.2 GhostSignal E2E.

The monitor avoids profiles; only the restart event's epoch is extracted from JSON. It writes
one baseline, state changes, bounded heartbeats and an atomically refreshed
summary so that an SSH disconnect does not destroy the test evidence.
"""

from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone


DEFAULT_DB = "data/game.sqlite3"
DEFAULT_CYCLE = "ghostnetwork_0001"
DEFAULT_CONFLICT = "territory_conflict_5145c32c3e634c66"
PM2_IDS = {13, 14, 17, 18}
RELEVANT_EVENTS = (
    "ghost.part_conflict_resolved",
    "ghost.cycle_locked",
    "ghost.signal_sent",
    "ghost.signal_ranking_created",
    "ghost.version_changed",
    "ghost.stabilization_started",
    "ghost.cycle_closed",
    "ghost.cycle_activated",
    "ghost.signal_show_started",
    "ghost.client_restart_required",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_hash(value) -> str:
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _rows(conn, sql, params=()):
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _one(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row is not None else None


def _count_groups(conn, table, column, where="", params=()):
    suffix = f" WHERE {where}" if where else ""
    rows = _rows(
        conn,
        f"SELECT {column} AS value, COUNT(*) AS total FROM {table}{suffix} "
        f"GROUP BY {column} ORDER BY {column}",
        params,
    )
    return {str(row["value"] or ""): int(row["total"] or 0) for row in rows}


def _table_exists(conn, table):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def read_client_restart(conn, cycle_id):
    events = _rows(conn, """SELECT event_id, created_at,
        json_extract(payload_json, '$.epoch') AS epoch
        FROM ghost_part_events
        WHERE cycle_id=? AND event_type='ghost.client_restart_required'
        ORDER BY state_version LIMIT 2""", (cycle_id,))
    schema_ready = _table_exists(conn, "session_restart_receipts")
    receipts = []
    if schema_ready and len(events) == 1 and events[0].get("epoch"):
        receipts = _rows(conn, """SELECT username_hash, lineage_hash,
            prepared_at, acknowledged_at FROM session_restart_receipts
            WHERE epoch=? ORDER BY username_hash, lineage_hash LIMIT 1001""",
            (events[0]["epoch"],))
    return {"events": events, "schema_ready": schema_ready,
            "receipts": receipts[:1000], "truncated": len(receipts) > 1000}


def open_readonly(db_path):
    resolved = Path(db_path).resolve()
    uri = resolved.as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def read_pm2():
    try:
        result = subprocess.run(
            ["pm2", "jlist"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8,
            check=False,
        )
        if result.returncode != 0:
            return {"ok": False, "error": (result.stderr or "pm2 jlist failed")[-300:]}
        payload = json.loads(result.stdout or "[]")
        processes = []
        for item in payload:
            pm_id = item.get("pm_id")
            if pm_id not in PM2_IDS:
                continue
            env = item.get("pm2_env") or {}
            processes.append(
                {
                    "id": pm_id,
                    "name": item.get("name", ""),
                    "status": env.get("status", "unknown"),
                    "restarts": int(env.get("restart_time") or 0),
                    "pid": int(item.get("pid") or 0),
                }
            )
        return {"ok": True, "processes": sorted(processes, key=lambda row: row["id"])}
    except Exception as exc:  # monitoring must survive a missing/transient PM2 CLI
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"[-300:]}


def read_snapshot(db_path, cycle_id, conflict_id, include_pm2=True):
    with closing(open_readonly(db_path)) as conn:
        conn.execute("BEGIN")
        known_tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        cycle = _one(
            conn,
            """SELECT cycle_id, signal_number, ghostsystem_version, status,
                      state_version, locked_at, transmitted_at,
                      stabilization_until, closed_at, source_version,
                      next_version, lock_event_id, closing_part_id,
                      restart_required, restart_reason, restart_signal_id,
                      upgrade_pending, updated_at
               FROM ghost_cycles WHERE cycle_id=?""",
            (cycle_id,),
        )
        if cycle is None:
            raise RuntimeError(f"cycle not found: {cycle_id}")

        parts = {
            "by_status": _count_groups(conn, "ghost_parts", "status", "cycle_id=?", (cycle_id,)),
            "by_conflict": _count_groups(
                conn, "ghost_parts", "conflict_state", "cycle_id=?", (cycle_id,)
            ),
            "blocking": _rows(
                conn,
                """SELECT part_id, part_code, status, territory_id,
                          conflict_state, conflict_id, conflict_resolved_at,
                          consumed_signal_id, updated_at
                   FROM ghost_parts
                   WHERE cycle_id=? AND conflict_state NOT IN ('', 'none', 'resolved', 'closed')
                   ORDER BY part_code""",
                (cycle_id,),
            ),
        }
        connections = _one(
            conn,
            """SELECT COUNT(*) AS total,
                      COUNT(DISTINCT position_in_ring) AS distinct_positions,
                      MIN(position_in_ring) AS min_position,
                      MAX(position_in_ring) AS max_position,
                      SUM(CASE WHEN part_a_id=part_b_id THEN 1 ELSE 0 END) AS self_edges,
                      SUM(CASE WHEN a.part_id IS NULL OR b.part_id IS NULL THEN 1 ELSE 0 END) AS missing_endpoints
               FROM ghost_connections c
               LEFT JOIN ghost_parts a ON a.part_id=c.part_a_id AND a.cycle_id=c.cycle_id
               LEFT JOIN ghost_parts b ON b.part_id=c.part_b_id AND b.cycle_id=c.cycle_id
               WHERE c.cycle_id=?""",
            (cycle_id,),
        ) or {}
        conflict = _one(
            conn,
            """SELECT conflict_id, status, player_a_username, player_b_username,
                      area_a_id, area_b_id, resolution_reason,
                      last_actor_username, source_event, updated_at,
                      resolved_at, closed_at
               FROM territory_conflicts WHERE conflict_id=?""",
            (conflict_id,),
        )
        locks = _rows(
            conn,
            """SELECT lock_snapshot_id, state_version, locked_at, lock_event_id,
                      closing_part_id, snapshot_checksum, created_at
               FROM ghost_cycle_lock_snapshots WHERE cycle_id=? ORDER BY created_at""",
            (cycle_id,),
        ) if "ghost_cycle_lock_snapshots" in known_tables else []
        signals = _rows(
            conn,
            """SELECT signal_id, signal_number, status, outcome, integrity,
                      sent_at, resolved_at, next_version, lock_snapshot_id,
                      signal_checksum, created_at
               FROM ghost_signals WHERE cycle_id=? ORDER BY created_at""",
            (cycle_id,),
        ) if "ghost_signals" in known_tables else []
        shows = _rows(
            conn,
            """SELECT show_id, signal_id, signal_public_id, show_started_at,
                      show_ends_at, from_system_version, to_system_version,
                      phase_policy_version, status, updated_at
               FROM ghost_signal_shows WHERE cycle_id=? ORDER BY created_at""",
            (cycle_id,),
        ) if "ghost_signal_shows" in known_tables else []
        rankings = _rows(
            conn,
            """SELECT ranking_id, signal_id, signal_number, snapshot_schema,
                      snapshot_checksum, created_at
               FROM ghost_signal_rankings WHERE cycle_id=? ORDER BY created_at""",
            (cycle_id,),
        ) if "ghost_signal_rankings" in known_tables else []
        events = _rows(
            conn,
            """SELECT event_id, event_type, state_version, part_id, entity_id,
                      audience_scope, audience_clan, created_at
               FROM ghost_part_events
               WHERE cycle_id=? AND event_type IN ({})
               ORDER BY state_version, created_at, event_id""".format(
                ",".join("?" for _ in RELEVANT_EVENTS)
            ),
            (cycle_id, *RELEVANT_EVENTS),
        )
        event_counts = {}
        for row in events:
            event_counts[row["event_type"]] = event_counts.get(row["event_type"], 0) + 1

        tasks = _rows(
            conn,
            """SELECT o.outbox_id, o.source_event_id, e.event_type AS source_event_type,
                      o.processor, o.target_medium, o.audience_scope,
                      o.audience_clan, o.audience_owner, o.status, o.task_variant,
                      o.prompt_version, o.output_schema_version,
                      o.model_policy_version, o.attempt_count, o.max_attempts,
                      o.claimed_by, o.last_error_code, o.created_at, o.updated_at,
                      o.completed_at, o.dead_lettered_at
               FROM ghost_narrative_outbox o
               LEFT JOIN ghost_part_events e ON e.event_id=o.source_event_id
               WHERE o.cycle_id=? AND e.event_type IN ({})
               ORDER BY o.created_at, o.outbox_id""".format(
                ",".join("?" for _ in RELEVANT_EVENTS)
            ),
            (cycle_id, *RELEVANT_EVENTS),
        ) if "ghost_narrative_outbox" in known_tables else []
        task_ids = [row["outbox_id"] for row in tasks]
        signal_task_ids = [
            row["outbox_id"] for row in tasks if row.get("source_event_type") == "ghost.signal_sent"
        ]

        def joined_rows(table, columns):
            if not task_ids or table not in known_tables:
                return []
            placeholders = ",".join("?" for _ in task_ids)
            return _rows(
                conn,
                f"SELECT {columns} FROM {table} WHERE task_id IN ({placeholders}) ORDER BY created_at",
                task_ids,
            )

        attempts = joined_rows(
            "ghost_narrative_inbox_attempts",
            "attempt_id, task_id, attempt_number, worker_id, status, model_name, "
            "error_code, retryable, started_at, completed_at, updated_at",
        )
        candidates = joined_rows(
            "ghost_narrative_inbox_candidates",
            "candidate_id, task_id, attempt_id, target_medium, audience_scope, "
            "validation_status, quarantine_reason, created_at, validated_at, updated_at",
        )
        receipts = joined_rows(
            "ghost_narrative_publication_receipts",
            "publication_receipt_id, candidate_id, task_id, target_medium, "
            "audience_scope, status, medium_record_id, attempt_count, "
            "last_error_code, created_at, updated_at, published_at, dead_lettered_at",
        )
        records = joined_rows(
            "ghost_narrative_medium_records",
            "medium_record_id, publication_receipt_id, candidate_id, task_id, "
            "target_medium, audience_scope, presentation_slot, active_state, "
            "publication_mode, created_at, published_at",
        )
        rewards = (
            {
                "total": int((_one(conn, "SELECT COUNT(*) AS total FROM ghost_reward_ledger WHERE cycle_id=?", (cycle_id,)) or {}).get("total", 0)),
                "by_status": _count_groups(conn, "ghost_reward_ledger", "status", "cycle_id=?", (cycle_id,)),
                "by_type": _count_groups(conn, "ghost_reward_ledger", "reward_type", "cycle_id=?", (cycle_id,)),
            }
            if "ghost_reward_ledger" in known_tables
            else {"total": 0, "by_status": {}, "by_type": {}}
        )
        consumptions = _rows(
            conn,
            """SELECT consumption_id, signal_id, territory_id, owner_id,
                      clan_code, role, reason, source_conflict_id, consumed_at
               FROM ghost_signal_territory_consumptions
               WHERE cycle_id=? ORDER BY consumed_at, consumption_id""",
            (cycle_id,),
        ) if "ghost_signal_territory_consumptions" in known_tables else []
        historical_nodes = (
            int((_one(conn, "SELECT COUNT(*) AS total FROM ghost_historical_nodes WHERE cycle_id=?", (cycle_id,)) or {}).get("total", 0))
            if "ghost_historical_nodes" in known_tables
            else 0
        )
        next_cycles = _rows(
            conn,
            """SELECT cycle_id, signal_number, ghostsystem_version, status,
                      state_version, started_at, created_at, updated_at
               FROM ghost_cycles WHERE signal_number>? ORDER BY signal_number""",
            (int(cycle.get("signal_number") or 0),),
        )
        queues = {}
        for table in ("ghostnetwork_territory_jobs", "ghostnetwork_delta_delivery_jobs"):
            if _table_exists(conn, table):
                queues[table] = {
                    "total": int((_one(conn, f"SELECT COUNT(*) AS total FROM {table}") or {}).get("total", 0)),
                    "by_status": _count_groups(conn, table, "status"),
                }
        if "ghost_narrative_outbox" in known_tables:
            queues["ollama_tasks_global"] = {
                "total": int(
                    (_one(conn, "SELECT COUNT(*) AS total FROM ghost_narrative_outbox WHERE processor='ollama'") or {}).get("total", 0)
                ),
                "by_status": _count_groups(
                    conn, "ghost_narrative_outbox", "status", "processor='ollama'"
                ),
            }
        if "ghost_narrative_publication_receipts" in known_tables:
            queues["publication_receipts_global"] = {
                "total": int(
                    (_one(conn, "SELECT COUNT(*) AS total FROM ghost_narrative_publication_receipts") or {}).get("total", 0)
                ),
                "by_status": _count_groups(
                    conn, "ghost_narrative_publication_receipts", "status"
                ),
            }
        client_restart = read_client_restart(conn, cycle_id)
        conn.execute("COMMIT")

    signal_task_set = set(signal_task_ids)
    snapshot = {
        "cycle": cycle,
        "parts": parts,
        "connections": connections,
        "conflict": conflict,
        "locks": locks,
        "signals": signals,
        "shows": shows,
        "client_restart": client_restart,
        "rankings": rankings,
        "events": {"counts": event_counts, "rows": events},
        "narrative": {
            "tasks": tasks,
            "signal_task_count": len(signal_task_ids),
            "signal_task_statuses": sorted(
                [row["status"] for row in tasks if row["outbox_id"] in signal_task_set]
            ),
            "attempts": attempts,
            "signal_attempt_count": sum(row["task_id"] in signal_task_set for row in attempts),
            "candidates": candidates,
            "signal_candidate_count": sum(row["task_id"] in signal_task_set for row in candidates),
            "signal_candidate_statuses": sorted(
                row["validation_status"]
                for row in candidates if row["task_id"] in signal_task_set
            ),
            "signal_accepted_candidate_count": sum(
                row["task_id"] in signal_task_set
                and row["validation_status"] == "accepted"
                for row in candidates
            ),
            "signal_quarantined_candidate_count": sum(
                row["task_id"] in signal_task_set
                and row["validation_status"] == "quarantined"
                for row in candidates
            ),
            "receipts": receipts,
            "signal_receipt_count": sum(row["task_id"] in signal_task_set for row in receipts),
            "records": records,
            "signal_record_count": sum(row["task_id"] in signal_task_set for row in records),
        },
        "settlement": {
            "rewards": rewards,
            "consumptions": consumptions,
            "historical_nodes": historical_nodes,
            "next_cycles": next_cycles,
        },
        "queues": queues,
        "schema_missing": sorted(
            {
                "ghost_cycle_lock_snapshots",
                "ghost_signals",
                "ghost_signal_shows",
                "ghost_signal_rankings",
                "ghost_narrative_outbox",
                "ghost_narrative_inbox_attempts",
                "ghost_narrative_inbox_candidates",
                "ghost_narrative_publication_receipts",
                "ghost_narrative_medium_records",
                "ghost_reward_ledger",
                "ghost_signal_territory_consumptions",
                "ghost_historical_nodes",
            }
            - known_tables
        ),
    }
    if include_pm2:
        snapshot["pm2"] = read_pm2()
    return snapshot


def milestone_flags(snapshot):
    conflict_status = str((snapshot.get("conflict") or {}).get("status") or "")
    cycle_status = str((snapshot.get("cycle") or {}).get("status") or "")
    narrative = snapshot.get("narrative") or {}
    next_cycles = (snapshot.get("settlement") or {}).get("next_cycles") or []
    restart = snapshot.get("client_restart") or {}
    restart_unique = len(restart.get("events") or []) == 1
    return {
        "conflict_resolved": conflict_status in {"resolved", "closed"},
        "cycle_locked": len(snapshot.get("locks") or []) == 1,
        "signal_sent": len(snapshot.get("signals") or []) == 1
        and (snapshot.get("events") or {}).get("counts", {}).get("ghost.signal_sent", 0) == 1,
        "signal_tasks_3_durable": int(narrative.get("signal_task_count") or 0) == 3,
        "signal_attempt_started": int(narrative.get("signal_attempt_count") or 0) > 0,
        "signal_candidate_created": int(narrative.get("signal_candidate_count") or 0) > 0,
        "signal_candidates_3_accepted": int(
            narrative.get("signal_accepted_candidate_count") or 0
        ) == 3,
        "signal_receipt_created": int(narrative.get("signal_receipt_count") or 0) > 0,
        "signal_record_published": int(narrative.get("signal_record_count") or 0) > 0,
        "ranking_created": len(snapshot.get("rankings") or []) == 1,
        "show_created": len(snapshot.get("shows") or []) == 1,
        "cycle_stabilizing": cycle_status == "stabilizing",
        "cycle_closed": cycle_status == "closed",
        "next_cycle_active": any(row.get("status") == "active" for row in next_cycles),
        "client_restart_requested": restart_unique,
        "client_restart_acknowledged": restart_unique and any(
            row.get("acknowledged_at") for row in restart.get("receipts") or []),
    }


def changed_sections(previous, current):
    if previous is None:
        return sorted(current)
    keys = sorted(set(previous) | set(current))
    return [key for key in keys if previous.get(key) != current.get(key)]


def atomic_json(path, payload):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(str(temporary), str(target))


class Monitor:
    def __init__(self, args):
        self.args = args
        self.started_at = utc_now()
        self.started_monotonic = time.monotonic()
        self.stop_requested = False
        self.samples = 0
        self.changes = 0
        self.errors = 0
        self.last_snapshot = None
        self.last_hash = ""
        self.last_heartbeat = 0.0
        self.last_pm2_read = 0.0
        self.last_pm2 = None
        self.milestones = {}
        self.last_error = ""
        self.log_handle = None

    def request_stop(self, *_args):
        self.stop_requested = True

    def write_record(self, kind, **fields):
        record = {"record_type": kind, "observed_at": utc_now(), **fields}
        self.log_handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        self.log_handle.flush()
        os.fsync(self.log_handle.fileno())

    def update_milestones(self, snapshot, observed_at):
        for name, reached in milestone_flags(snapshot).items():
            if reached and name not in self.milestones:
                self.milestones[name] = observed_at

    def summary(self, status):
        return {
            "schema": "chaos-138.2-monitor-summary-v1",
            "status": status,
            "pid": os.getpid(),
            "db_path": str(Path(self.args.db).resolve()),
            "cycle_id": self.args.cycle_id,
            "conflict_id": self.args.conflict_id,
            "started_at": self.started_at,
            "updated_at": utc_now(),
            "duration_seconds": round(time.monotonic() - self.started_monotonic, 3),
            "samples": self.samples,
            "changes": self.changes,
            "errors": self.errors,
            "last_error": self.last_error,
            "milestones": self.milestones,
            "last_state_hash": self.last_hash,
            "last_snapshot": self.last_snapshot,
            "log_path": str(Path(self.args.output).resolve()),
        }

    def write_summary(self, status="running"):
        atomic_json(self.args.summary, self.summary(status))

    def run(self):
        output = Path(self.args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        self.log_handle = output.open("a" if self.args.resume else "x", encoding="utf-8", buffering=1)
        self.write_record(
            "monitor_started",
            schema="chaos-138.2-monitor-jsonl-v1",
            pid=os.getpid(),
            db_path=str(Path(self.args.db).resolve()),
            cycle_id=self.args.cycle_id,
            conflict_id=self.args.conflict_id,
            interval_seconds=self.args.interval,
            heartbeat_seconds=self.args.heartbeat,
        )
        self.write_summary()
        try:
            while not self.stop_requested:
                loop_started = time.monotonic()
                include_pm2 = self.last_pm2 is None or loop_started - self.last_pm2_read >= self.args.pm2_interval
                try:
                    snapshot = read_snapshot(
                        self.args.db,
                        self.args.cycle_id,
                        self.args.conflict_id,
                        include_pm2=include_pm2,
                    )
                    if include_pm2:
                        self.last_pm2 = snapshot.get("pm2")
                        self.last_pm2_read = loop_started
                    else:
                        snapshot["pm2"] = self.last_pm2
                    self.samples += 1
                    state_hash = canonical_hash(snapshot)
                    observed_at = utc_now()
                    self.update_milestones(snapshot, observed_at)
                    changed = state_hash != self.last_hash
                    heartbeat_due = loop_started - self.last_heartbeat >= self.args.heartbeat
                    if changed:
                        self.changes += 1
                        self.write_record(
                            "baseline" if self.last_snapshot is None else "state_changed",
                            state_hash=state_hash,
                            changed_sections=changed_sections(self.last_snapshot, snapshot),
                            snapshot=snapshot,
                            milestones=self.milestones,
                        )
                        self.last_snapshot = snapshot
                        self.last_hash = state_hash
                    elif heartbeat_due:
                        self.write_record(
                            "heartbeat",
                            state_hash=state_hash,
                            samples=self.samples,
                            milestones=self.milestones,
                        )
                    if changed or heartbeat_due:
                        self.last_heartbeat = loop_started
                        self.write_summary()
                    self.last_error = ""
                except Exception as exc:
                    self.errors += 1
                    error = f"{type(exc).__name__}: {exc}"
                    if error != self.last_error or loop_started - self.last_heartbeat >= self.args.heartbeat:
                        self.last_error = error
                        self.last_heartbeat = loop_started
                        self.write_record("poll_error", error=error, errors=self.errors)
                        self.write_summary("degraded")
                if self.args.max_seconds and time.monotonic() - self.started_monotonic >= self.args.max_seconds:
                    self.stop_requested = True
                    continue
                elapsed = time.monotonic() - loop_started
                time.sleep(max(0.1, self.args.interval - elapsed))
        finally:
            final_status = "stopped" if self.last_snapshot is not None else "failed"
            self.write_record(
                "monitor_stopped",
                status=final_status,
                samples=self.samples,
                changes=self.changes,
                errors=self.errors,
                milestones=self.milestones,
            )
            self.write_summary(final_status)
            self.log_handle.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--cycle-id", default=DEFAULT_CYCLE)
    parser.add_argument("--conflict-id", default=DEFAULT_CONFLICT)
    parser.add_argument("--output", required=True, help="Append-only JSONL evidence file")
    parser.add_argument("--summary", required=True, help="Atomically refreshed compact JSON summary")
    parser.add_argument("--pid-file", default="", help="Optional PID file removed on clean stop")
    parser.add_argument("--resume", action="store_true", help="Append after an interrupted monitor run")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--heartbeat", type=float, default=30.0)
    parser.add_argument("--pm2-interval", type=float, default=10.0)
    parser.add_argument("--max-seconds", type=float, default=0.0, help="0 means run until SIGTERM")
    args = parser.parse_args(argv)
    if args.interval < 0.25:
        parser.error("--interval must be at least 0.25 seconds")
    if args.heartbeat < args.interval:
        parser.error("--heartbeat must be >= --interval")
    if args.pm2_interval < args.interval:
        parser.error("--pm2-interval must be >= --interval")
    return args


def claim_pid_file(path):
    if not path:
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        try:
            existing = int(target.read_text(encoding="ascii").strip())
            os.kill(existing, 0)
        except (ValueError, ProcessLookupError, OSError):
            pass
        else:
            raise RuntimeError(f"monitor already running with pid {existing}")
    target.write_text(f"{os.getpid()}\n", encoding="ascii")


def main(argv=None):
    args = parse_args(argv)
    claim_pid_file(args.pid_file)
    monitor = Monitor(args)
    signal.signal(signal.SIGINT, monitor.request_stop)
    signal.signal(signal.SIGTERM, monitor.request_stop)
    try:
        monitor.run()
    finally:
        if args.pid_file:
            target = Path(args.pid_file)
            try:
                if target.read_text(encoding="ascii").strip() == str(os.getpid()):
                    target.unlink()
            except (FileNotFoundError, OSError):
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
