#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.ollama_worker import (  # noqa: E402
    OllamaWorkerConfig,
    active_ollama_worker_policies,
    verify_ollama_runtime_policy,
)
from ghostnetwork.repository import GhostNetworkRepository  # noqa: E402


NARRATIVE_RUNTIME_AUDIT_VERSION = "ghostnetwork-narrative-runtime-audit-v1"


def build_report(repository, *, config=None, now=None):
    now = now or datetime.now(timezone.utc)
    config = config or OllamaWorkerConfig.from_env()
    runtime_safety = verify_ollama_runtime_policy(config)
    health = repository.narrative_runtime_health(
        active_ollama_worker_policies(), now=now,
    )
    queue = health["queue"]
    errors = []
    warnings = []
    if not runtime_safety.get("ok"):
        errors.append("runtime_policy_invalid")
    if queue.get("expired_leases"):
        errors.append("expired_task_leases")
    if queue.get("ineligible_ready"):
        errors.append("ineligible_ready_tasks")
    if health.get("active_without_lease"):
        errors.append("active_tasks_without_lease")
    if health.get("exhausted_nonterminal"):
        errors.append("exhausted_tasks_not_dead_lettered")
    if health.get("retry_schedule_violations"):
        errors.append("retry_schedule_violation")
    if health.get("incomplete_attempts"):
        warnings.append("historical_incomplete_attempts")
    return {
        "ok": not errors,
        "contract_version": NARRATIVE_RUNTIME_AUDIT_VERSION,
        "checked_at": now.astimezone(timezone.utc).isoformat(),
        "errors": errors,
        "warnings": warnings,
        "runtime_safety": runtime_safety,
        "health": health,
        "guarantees": {
            "database_contention": "retryable_without_process_exit",
            "model_transport_failure": "bounded_exponential_backoff",
            "max_attempts": "dead_letter",
            "expired_lease": "atomic_recovery",
            "candidate_after_crash": "complete_without_second_model_call",
            "unknown_database_error": "fail_fast",
        },
        "read_only": True,
        "profiles_loaded": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Sprint 137.3 Ollama runtime/recovery audit"
    )
    parser.add_argument("--db", default="", help="Optional SQLite database path")
    parser.add_argument(
        "--strict", action="store_true", help="Exit non-zero when a runtime gate fails"
    )
    args = parser.parse_args(argv)
    repository = (
        GhostNetworkRepository(db_path=args.db) if args.db else GhostNetworkRepository()
    )
    report = build_report(repository)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("ok") or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
