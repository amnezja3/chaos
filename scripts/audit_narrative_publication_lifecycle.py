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

from ghostnetwork.publication_lifecycle import (  # noqa: E402
    PUBLICATION_LIFECYCLE_CONTRACT_VERSION,
)
from ghostnetwork.repository import GhostNetworkRepository  # noqa: E402


PUBLICATION_LIFECYCLE_AUDIT_VERSION = "ghostnetwork-publication-lifecycle-audit-v1"


def build_report(repository, *, now=None, limit=50):
    now = now or datetime.now(timezone.utc)
    health = repository.narrative_publication_lifecycle_health(
        now=now, limit=limit,
    )
    errors = []
    warnings = []
    for count_key, error in (
        ("active_expired", "expired_record_still_active"),
        ("active_missing_contract", "active_record_missing_lifecycle_contract"),
        ("invalidated_missing_lineage", "invalidated_record_missing_lineage"),
        ("duplicate_active_heads", "duplicate_active_thread_heads"),
    ):
        if health.get(count_key):
            errors.append(error)
    if health.get("states", {}).get("legacy"):
        warnings.append("historical_legacy_records_present")
    return {
        "ok": not errors,
        "contract_version": PUBLICATION_LIFECYCLE_AUDIT_VERSION,
        "lifecycle_contract_version": PUBLICATION_LIFECYCLE_CONTRACT_VERSION,
        "checked_at": now.astimezone(timezone.utc).isoformat(),
        "errors": errors,
        "warnings": warnings,
        "health": health,
        "read_only": True,
        "profiles_loaded": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Sprint 138.1 publication lifecycle audit"
    )
    parser.add_argument("--db", default="", help="Optional SQLite database path")
    parser.add_argument("--limit", type=int, default=50, help="Bounded sample limit")
    parser.add_argument(
        "--strict", action="store_true", help="Exit non-zero when a lifecycle gate fails"
    )
    args = parser.parse_args(argv)
    repository = GhostNetworkRepository(db_path=args.db) if args.db else GhostNetworkRepository()
    report = build_report(repository, limit=args.limit)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("ok") or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
