#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.errors import RepositoryIntegrityError  # noqa: E402
from ghostnetwork.ollama_worker import active_ollama_worker_policies  # noqa: E402
from ghostnetwork.repository import GhostNetworkRepository  # noqa: E402


REPORT_VERSION = "narrative-backlog-retirement-v1"
REASON_CODE = "historical_backlog_operator_cutoff"


def _parse_before(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--before must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("--before must include a timezone")
    return parsed


def _summary(tasks):
    return {
        "count": len(tasks),
        "by_prompt_version": dict(sorted(Counter(
            str(task.get("prompt_version") or "") for task in tasks
        ).items())),
        "by_source_scope": dict(sorted(Counter(
            str(task.get("source_scope") or "") for task in tasks
        ).items())),
        "by_status": dict(sorted(Counter(
            str(task.get("status") or "") for task in tasks
        ).items())),
        "oldest_created_at": min(
            (str(task.get("created_at") or "") for task in tasks), default=""
        ),
        "newest_created_at": max(
            (str(task.get("created_at") or "") for task in tasks), default=""
        ),
        "tasks": [
            {
                key: task.get(key)
                for key in (
                    "outbox_id", "source_scope", "source_event_id", "task_variant",
                    "target_medium", "prompt_version", "status", "attempt_count",
                    "created_at", "last_error_code",
                )
            }
            for task in tasks
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Dry-run or atomically retire a bounded historical narrative backlog"
    )
    parser.add_argument("--db", default="", help="Optional SQLite database path")
    parser.add_argument("--before", required=True, type=_parse_before)
    parser.add_argument(
        "--protect-source-event-id", action="append", default=[],
        help="Canonical event identity that must never be selected (repeatable)",
    )
    parser.add_argument("--expect-count", type=int, default=None)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.apply and args.expect_count is None:
        parser.error("--apply requires --expect-count")
    if args.expect_count is not None and args.expect_count < 0:
        parser.error("--expect-count must not be negative")

    repository = (
        GhostNetworkRepository(db_path=args.db) if args.db else GhostNetworkRepository()
    )
    policies = active_ollama_worker_policies()
    try:
        selected = repository.plan_historical_narrative_backlog_retirement(
            policies,
            before=args.before,
            protected_source_event_ids=args.protect_source_event_id,
            limit=args.limit,
        )
        count_matches = (
            args.expect_count is None or len(selected) == args.expect_count
        )
        if args.apply:
            selected = repository.retire_historical_narrative_backlog(
                policies,
                before=args.before,
                expected_count=args.expect_count,
                protected_source_event_ids=args.protect_source_event_id,
                reason_code=REASON_CODE,
                limit=args.limit,
            )
        report = {
            "ok": count_matches,
            "contract_version": REPORT_VERSION,
            "mode": "apply" if args.apply else "dry_run",
            "before": args.before.isoformat(),
            "protected_source_event_ids": args.protect_source_event_id,
            "expected_count": args.expect_count,
            "count_matches": count_matches,
            "reason_code": REASON_CODE if args.apply else "",
            "selection": _summary(selected),
            "model_calls": 0,
            "records_deleted": 0,
        }
    except (RepositoryIntegrityError, ValueError) as exc:
        report = {
            "ok": False,
            "contract_version": REPORT_VERSION,
            "mode": "apply" if args.apply else "dry_run",
            "error": str(exc),
            "model_calls": 0,
            "records_deleted": 0,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
