#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.narrative_cutover import (
    build_narrative_cutover_report,
    retire_cutover_ineligible_tasks,
)
from ghostnetwork.repository import GhostNetworkRepository


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Sprint 135.6 canonical narrative cutover audit; read-only unless "
            "--retire-ineligible is explicitly supplied"
        )
    )
    parser.add_argument("--db", default="", help="Optional SQLite database path")
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit non-zero when any cutover gate fails",
    )
    parser.add_argument(
        "--retire-ineligible", action="store_true",
        help=(
            "Terminally retire at most 500 queued tasks that no active policy "
            "can claim, then rerun the audit"
        ),
    )
    args = parser.parse_args(argv)
    repository = (
        GhostNetworkRepository(db_path=args.db)
        if args.db else GhostNetworkRepository()
    )
    retired = []
    if args.retire_ineligible:
        retired = retire_cutover_ineligible_tasks(repository)
    report = build_narrative_cutover_report(repository)
    report["retired_ineligible_task_count"] = len(retired)
    report["retired_ineligible_task_ids"] = retired
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("ok") or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
