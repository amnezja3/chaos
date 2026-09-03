#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.narrative import (
    GhostNarrativePublisher,
    resolve_ghost_event_policy,
)
from ghostnetwork.ollama_policy import (
    build_ollama_task_package,
    presentation_safety_errors,
)
from ghostnetwork.repository import GhostNetworkRepository


AUDIT_CONTRACT_VERSION = "ghostnetwork-generation-validation-audit-v1"


def _is_v3_task(task):
    return (
        str((task or {}).get("source_scope") or "") == "ghostnetwork"
        and str((task or {}).get("prompt_version") or "").endswith("-v3")
    )


def _latest_discovery_event(repository):
    return next((
        event for event in repository.list_events(limit=1000)
        if event.get("event_type") == "ghost.part_discovered"
    ), None)


def _select(repository, *, event_id="", task_id=""):
    if task_id:
        task = repository.get_narrative_outbox(task_id)
        event = repository.get_event((task or {}).get("source_event_id")) if task else None
        return event, ([task] if task else [])
    event = repository.get_event(event_id) if event_id else _latest_discovery_event(repository)
    if not event:
        return None, []
    tasks = [
        task for task in repository.list_narrative_outbox(
            source_scope="ghostnetwork",
            source_event_id=event.get("event_id"),
            limit=100,
        )
        if _is_v3_task(task)
    ]
    return event, sorted(tasks, key=lambda item: (
        item.get("target_medium") or "",
        item.get("audience_scope") or "",
        item.get("outbox_id") or "",
    ))


def _expected_identities(repository, event):
    if not event:
        return set()
    policy = resolve_ghost_event_policy(event.get("event_type"))
    if not policy.get("eligible"):
        return set()
    publisher = GhostNarrativePublisher(repository=repository)
    return {
        (
            str(audience.get("scope") or "public"),
            str(audience.get("clan") or ""),
            str(audience.get("owner") or ""),
            str(medium or ""),
        )
        for audience in publisher.resolve_event_audiences(event)
        for medium in publisher.target_media_for_audience(policy, audience)
    }


def _identity(task):
    return (
        str(task.get("audience_scope") or "public"),
        str(task.get("audience_clan") or ""),
        str(task.get("audience_owner") or ""),
        str(task.get("target_medium") or ""),
    )


def _public_identity(identity):
    scope, _clan, _owner, medium = identity
    return {"audience_scope": scope, "target_medium": medium}


def _task_report(repository, task):
    task_id = str(task.get("outbox_id") or "")
    errors = []
    try:
        package = build_ollama_task_package(task)
        model_input = json.loads(package["messages"][1]["content"])
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "errors": [f"package_invalid:{type(exc).__name__}:{exc}"],
            "task": {"task_id": task_id},
        }

    if not _is_v3_task(task):
        errors.append("task_not_active_v3")
    if task.get("status") != "completed":
        errors.append(f"task_not_completed:{task.get('status') or 'missing'}")

    attempts = repository.list_narrative_attempts(task_id=task_id, limit=100)
    latest_attempt = max(
        attempts,
        key=lambda item: (int(item.get("attempt_number") or 0), item.get("created_at") or ""),
        default=None,
    )
    if not latest_attempt:
        errors.append("attempt_missing")
    else:
        if latest_attempt.get("status") != "completed":
            errors.append(f"attempt_not_completed:{latest_attempt.get('status') or 'missing'}")
        if latest_attempt.get("request_hash") != package.get("request_hash"):
            errors.append("attempt_request_hash_mismatch")
        if latest_attempt.get("prompt_version") != task.get("prompt_version"):
            errors.append("attempt_prompt_version_mismatch")

    candidate = repository.get_narrative_candidate_for_task(task_id)
    if not candidate:
        errors.append("candidate_missing")
    else:
        if candidate.get("validation_status") != "accepted":
            errors.append(
                f"candidate_not_accepted:{candidate.get('validation_status') or 'missing'}"
            )
        if latest_attempt and candidate.get("attempt_id") != latest_attempt.get("attempt_id"):
            errors.append("candidate_attempt_mismatch")
        if candidate.get("prompt_version") != task.get("prompt_version"):
            errors.append("candidate_prompt_version_mismatch")
        if candidate.get("target_medium") != task.get("target_medium"):
            errors.append("candidate_medium_mismatch")
        if candidate.get("audience_scope") != task.get("audience_scope"):
            errors.append("candidate_audience_mismatch")
        canonical_fact_refs = {
            str(fact.get("fact_id") or "")
            for fact in task.get("facts") or []
            if isinstance(fact, dict) and fact.get("fact_id")
        }
        if not candidate.get("fact_refs") or not set(candidate.get("fact_refs") or ()).issubset(
            canonical_fact_refs
        ):
            errors.append("candidate_fact_lineage_invalid")
        errors.extend(presentation_safety_errors(
            candidate.get("title"), candidate.get("body")
        ))

    return {
        "ok": not errors,
        "errors": sorted(set(errors)),
        "task": {
            "task_id": task_id,
            "source_event_id": task.get("source_event_id"),
            "target_medium": task.get("target_medium"),
            "audience_scope": task.get("audience_scope"),
            "status": task.get("status"),
            "prompt_version": task.get("prompt_version"),
            "narrative_intent": task.get("narrative_intent"),
            "event_family": (task.get("validation") or {}).get("event_family"),
        },
        "model_input": {
            "semantic_contract": model_input.get("semantic_contract"),
            "medium": model_input.get("medium"),
            "audience": model_input.get("audience"),
            "narrative_intent": model_input.get("narrative_intent"),
            "event_family": model_input.get("event_family"),
            "significance": model_input.get("significance"),
            "tone_hint": model_input.get("tone_hint"),
            "semantic_facts": model_input.get("semantic_facts") or [],
        },
        "package": {
            "request_hash": package.get("request_hash"),
            "input_bytes": package.get("input_bytes"),
            "fact_count": package.get("fact_count"),
        },
        "attempt": ({
            "attempt_id": latest_attempt.get("attempt_id"),
            "attempt_number": latest_attempt.get("attempt_number"),
            "status": latest_attempt.get("status"),
            "request_hash": latest_attempt.get("request_hash"),
            "result": latest_attempt.get("result"),
            "error_code": latest_attempt.get("error_code"),
            "input_bytes": latest_attempt.get("input_bytes"),
            "fact_count": latest_attempt.get("fact_count"),
        } if latest_attempt else None),
        "candidate": ({
            "candidate_id": candidate.get("candidate_id"),
            "attempt_id": candidate.get("attempt_id"),
            "validation_status": candidate.get("validation_status"),
            "validation_errors": candidate.get("validation_errors") or [],
            "quarantine_reason": candidate.get("quarantine_reason") or "",
            "title": candidate.get("title"),
            "body": candidate.get("body"),
            "tone": candidate.get("tone"),
            "fact_refs": candidate.get("fact_refs") or [],
            "cta_action": candidate.get("cta_action") or "",
            "asset_ref": candidate.get("asset_ref") or "",
        } if candidate else None),
    }


def build_report(repository, *, event_id="", task_id=""):
    event, tasks = _select(repository, event_id=event_id, task_id=task_id)
    errors = []
    if task_id and not tasks:
        errors.append("generation_task_missing")
    elif not event:
        errors.append("generation_source_event_missing")
    elif not tasks:
        errors.append("generation_v3_tasks_missing")

    expected = set() if task_id else _expected_identities(repository, event)
    actual = {_identity(task) for task in tasks}
    missing = expected - actual
    if missing:
        errors.append("expected_generation_tasks_missing")

    samples = [_task_report(repository, task) for task in tasks]
    if any(not sample.get("ok") for sample in samples):
        errors.append("generation_chain_incomplete_or_rejected")

    return {
        "ok": not errors,
        "contract_version": AUDIT_CONTRACT_VERSION,
        "errors": sorted(set(errors)),
        "event": ({
            "event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "created_at": event.get("created_at"),
        } if event else None),
        "expected_task_count": len(expected) if expected else len(tasks),
        "sample_count": len(samples),
        "missing_task_identities": [
            _public_identity(identity) for identity in sorted(missing)
        ],
        "samples": samples,
        "manual_voice_review": {
            "required": bool(samples),
            "checks": [
                "title_and_body_are_polish",
                "voice_matches_target_medium",
                "copy_describes_only_semantic_facts",
                "copy_does_not_echo_control_metadata_or_identifiers",
            ],
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Sprint 137.1 event-to-generation audit",
    )
    parser.add_argument("--db", default="", help="Optional SQLite database path")
    selector = parser.add_mutually_exclusive_group()
    selector.add_argument("--event-id", default="", help="Audit every v3 task for one event")
    selector.add_argument("--task-id", default="", help="Audit one narrative outbox task")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    repository = GhostNetworkRepository(db_path=args.db) if args.db else GhostNetworkRepository()
    report = build_report(repository, event_id=args.event_id, task_id=args.task_id)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
