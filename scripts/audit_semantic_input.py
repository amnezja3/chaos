#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.llm.semantic_input import contains_opaque_identifier
from ghostnetwork.llm.registry import (
    GHOSTNETWORK_EVENT_PROMPT_VERSION,
    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
    GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
)
from ghostnetwork.ollama_policy import build_ollama_task_package
from ghostnetwork.repository import GhostNetworkRepository


ACTIVE_GHOSTNETWORK_PROMPTS = frozenset({
    GHOSTNETWORK_EVENT_PROMPT_VERSION,
    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
    GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
})


def _select_tasks(repository, task_id=""):
    if task_id:
        task = repository.get_narrative_outbox(task_id)
        return [task] if task else []
    latest_event = next((
        event for event in repository.list_events(limit=1000)
        if event.get("event_type") == "ghost.part_discovered"
    ), None)
    if not latest_event:
        return []
    selected = [
        task for task in repository.list_narrative_outbox(
            source_scope="ghostnetwork",
            source_event_id=latest_event.get("event_id"),
            limit=25,
        )
        if str(task.get("prompt_version") or "") in ACTIVE_GHOSTNETWORK_PROMPTS
    ]
    return sorted(selected, key=lambda item: (
        item.get("audience_scope") or "", item.get("target_medium") or "",
    ))


def build_report(repository, task_id=""):
    tasks = _select_tasks(repository, task_id)
    errors = []
    samples = []
    if not tasks:
        errors.append("semantic_part_discovered_sample_missing")
    for task in tasks:
        try:
            package = build_ollama_task_package(task)
            model_input = json.loads(package["messages"][1]["content"])
            semantic_facts = model_input.get("semantic_facts") or []
            presentation_values = [
                value
                for fact in semantic_facts
                for value in (
                    [fact.get("statement")]
                    + [item.get("label") for item in fact.get("entities") or []]
                    + list((fact.get("location") or {}).values())
                    + [item.get("value") for item in fact.get("attributes") or []]
                )
                if value not in (None, "")
            ]
            technical_leaks = [
                str(value) for value in presentation_values
                if contains_opaque_identifier(value)
            ]
            if technical_leaks:
                errors.append("model_visible_technical_identifier")
            samples.append({
                "task": {
                    "task_id": task.get("outbox_id"),
                    "event_type": (repository.get_event(task.get("source_event_id")) or {}).get("event_type"),
                    "audience_scope": task.get("audience_scope"),
                    "target_medium": task.get("target_medium"),
                    "prompt_version": task.get("prompt_version"),
                },
                "canonical_to_semantic": list(package.get("semantic_audit") or []),
                "model_input": model_input,
                "package": {
                    "input_bytes": package.get("input_bytes"),
                    "request_hash": package.get("request_hash"),
                    "technical_identifier_leaks": technical_leaks,
                },
            })
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"semantic_package_invalid:{type(exc).__name__}:{exc}")
    return {
        "ok": not errors,
        "contract_version": "shared-semantic-input-audit-v1",
        "errors": sorted(set(errors)),
        "sample_count": len(samples),
        "samples": samples,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only canonical-to-semantic-to-model package audit",
    )
    parser.add_argument("--db", default="", help="Optional SQLite database path")
    parser.add_argument("--task-id", default="", help="Audit one narrative outbox task")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    repository = GhostNetworkRepository(db_path=args.db) if args.db else GhostNetworkRepository()
    report = build_report(repository, args.task_id)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
