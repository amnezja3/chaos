#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.publication_lifecycle import (  # noqa: E402
    PUBLICATION_LIFECYCLE_CONTRACT_VERSION,
)
from ghostnetwork.repository import GhostNetworkRepository  # noqa: E402
from scripts.audit_narrative_generation import build_report as build_generation_report  # noqa: E402


NARRATIVE_E2E_AUDIT_VERSION = "ghostnetwork-narrative-e2e-audit-v2"
TERMINAL_RECORD_STATES = frozenset({"active", "expired", "invalidated"})


def _iso_datetime(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _lineage_report(repository, sample, rows):
    task = sample.get("task") or {}
    candidate = sample.get("candidate") or {}
    task_id = str(task.get("task_id") or "")
    candidate_id = str(candidate.get("candidate_id") or "")
    errors = []
    matching = [row for row in rows if row.get("task_id") == task_id]
    if not matching:
        errors.append("publication_receipt_missing")
        return {
            "ok": False,
            "errors": errors,
            "task_id": task_id,
            "candidate_id": candidate_id,
            "receipt": None,
            "record": None,
            "event_to_publication_ms": None,
        }
    if len(matching) != 1:
        errors.append("publication_identity_not_unique")
    row = matching[0]
    if row.get("candidate_id") != candidate_id:
        errors.append("receipt_candidate_mismatch")
    expected_identity = (
        str(task.get("target_medium") or ""),
        str(task.get("audience_scope") or ""),
    )
    if (row.get("target_medium"), row.get("audience_scope")) != expected_identity:
        errors.append("receipt_task_identity_mismatch")
    controlled_slot_supersession = (
        row.get("receipt_status") == "dead_letter"
        and row.get("last_error_code") == "slot_assignment_superseded"
    )
    if controlled_slot_supersession:
        if not row.get("presentation_slot"):
            errors.append("superseding_presentation_slot_missing")
        if not row.get("slot_active_medium_record_id"):
            errors.append("superseding_slot_record_missing")
        if row.get("slot_active_state") != "active":
            errors.append("superseding_slot_record_not_active")
        return {
            "ok": not errors,
            "errors": sorted(set(errors)),
            "outcome": "controlled_slot_supersession",
            "task_id": task_id,
            "candidate_id": candidate_id,
            "receipt": {
                "publication_receipt_id": row.get("publication_receipt_id"),
                "status": row.get("receipt_status"),
                "last_error_code": row.get("last_error_code") or "",
            },
            "record": None,
            "superseding_record": {
                "medium_record_id": row.get("slot_active_medium_record_id") or "",
                "source_event_id": row.get("slot_active_source_event_id") or "",
                "active_state": row.get("slot_active_state") or "",
                "source_state_version": row.get("slot_active_source_state_version") or 0,
                "presentation_slot": row.get("presentation_slot") or "",
            },
            "event_to_publication_ms": None,
        }
    if row.get("receipt_status") != "published":
        errors.append(f"receipt_not_published:{row.get('receipt_status') or 'missing'}")
    if not row.get("medium_record_id"):
        errors.append("medium_record_missing")
    if (row.get("record_medium"), row.get("record_audience_scope")) != expected_identity:
        errors.append("record_task_identity_mismatch")
    if row.get("source_event_id") != task.get("source_event_id"):
        errors.append("record_source_event_mismatch")
    if row.get("lifecycle_contract_version") != PUBLICATION_LIFECYCLE_CONTRACT_VERSION:
        errors.append("record_lifecycle_contract_missing")
    if not row.get("semantic_contract_version"):
        errors.append("record_semantic_contract_missing")
    if row.get("active_state") not in TERMINAL_RECORD_STATES:
        errors.append(f"record_state_invalid:{row.get('active_state') or 'missing'}")
    candidate_refs = set(candidate.get("fact_refs") or ())
    record_refs = set(row.get("record_fact_refs") or ())
    if not record_refs or not record_refs.issubset(candidate_refs):
        errors.append("record_fact_lineage_invalid")
    event_created = _iso_datetime((sample.get("source_event") or {}).get("created_at"))
    published = _iso_datetime(row.get("record_published_at"))
    latency_ms = None
    if event_created and published:
        latency_ms = max(0.0, round((published - event_created).total_seconds() * 1000, 3))
    return {
        "ok": not errors,
        "errors": sorted(set(errors)),
        "outcome": "published",
        "task_id": task_id,
        "candidate_id": candidate_id,
        "receipt": {
            "publication_receipt_id": row.get("publication_receipt_id"),
            "status": row.get("receipt_status"),
            "last_error_code": row.get("last_error_code") or "",
        },
        "record": {
            "medium_record_id": row.get("medium_record_id"),
            "active_state": row.get("active_state"),
            "event_family": row.get("event_family"),
            "narrative_thread_id": row.get("narrative_thread_id"),
            "source_state_version": row.get("source_state_version"),
            "publication_mode": row.get("publication_mode"),
        },
        "superseding_record": None,
        "event_to_publication_ms": latency_ms,
    }


def build_report(repository, *, event_id="", task_id=""):
    generation = build_generation_report(
        repository, event_id=event_id, task_id=task_id,
    )
    task_ids = [
        str((sample.get("task") or {}).get("task_id") or "")
        for sample in generation.get("samples") or []
    ]
    rows = repository.list_narrative_publication_lineage(task_ids, limit=500)
    event = generation.get("event") or {}
    chains = []
    for sample in generation.get("samples") or []:
        enriched = dict(sample)
        enriched["source_event"] = event
        chains.append(_lineage_report(repository, enriched, rows))
    errors = list(generation.get("errors") or ())
    if any(not chain.get("ok") for chain in chains):
        errors.append("publication_chain_incomplete")
    latencies = [
        chain["event_to_publication_ms"] for chain in chains
        if chain.get("event_to_publication_ms") is not None
    ]
    return {
        "ok": not errors,
        "contract_version": NARRATIVE_E2E_AUDIT_VERSION,
        "errors": sorted(set(errors)),
        "event": event or None,
        "generation_ok": bool(generation.get("ok")),
        "generation": generation,
        "expected_task_count": generation.get("expected_task_count", 0),
        "chain_count": len(chains),
        "chains": chains,
        "event_to_publication_ms": {
            "samples": len(latencies),
            "average": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "maximum": max(latencies) if latencies else None,
        },
        "read_only": True,
        "bounded_limit": 500,
        "profiles_loaded": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Sprint 138.2 event-to-publication lineage audit",
    )
    parser.add_argument("--db", default="", help="Optional SQLite database path")
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--event-id", default="", help="Audit full producer fanout for an event")
    selector.add_argument("--task-id", default="", help="Audit one task publication chain")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    repository = GhostNetworkRepository(db_path=args.db) if args.db else GhostNetworkRepository()
    report = build_report(repository, event_id=args.event_id, task_id=args.task_id)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
