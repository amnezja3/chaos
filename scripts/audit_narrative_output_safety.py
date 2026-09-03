#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ghostnetwork.catalog import get_catalog
from ghostnetwork.llm.output_safety import (
    GHOST_OUTPUT_SAFETY_CONTRACT_VERSION,
    validate_ghost_output_safety,
)
from ghostnetwork.llm.registry import (
    GHOSTNETWORK_EVENT_PROMPT_VERSION,
    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
    GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
)
from ghostnetwork.ollama_policy import build_ollama_task_package
from ghostnetwork.repository import GhostNetworkRepository


AUDIT_CONTRACT_VERSION = "ghostnetwork-output-safety-audit-v1"
ACTIVE_PROMPTS = frozenset({
    GHOSTNETWORK_EVENT_PROMPT_VERSION,
    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
    GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
})


def _visible_text(package):
    return json.dumps(
        (package.get("model_input") or {}).get("semantic_facts") or [],
        ensure_ascii=False,
    ).casefold()


def _hidden_catalog_name(package):
    visible = _visible_text(package)
    catalog = get_catalog()
    candidates = [
        str(item.get("name") or "").strip()
        for collection in ("parts", "machines", "clans")
        for item in catalog.get(collection, ())
        if isinstance(item, dict) and str(item.get("name") or "").strip()
    ]
    return next((value for value in candidates if value.casefold() not in visible), "")


def _run_probe(package, text, expected_error=""):
    result = validate_ghost_output_safety(
        "AUDYT",
        text,
        model_input=package.get("model_input") or {},
        fact_aliases=(package.get("fact_ref_map") or {}).keys(),
        cta_aliases=(package.get("cta_map") or {}).keys(),
        asset_refs=package.get("allowed_asset_refs") or (),
        forbidden_values=package.get("output_safety_forbidden_values") or (),
    )
    errors = sorted(set(
        (result.get("security_errors") or [])
        + (result.get("grounding_errors") or [])
    ))
    return {
        "ok": expected_error in errors if expected_error else not errors,
        "expected_error": expected_error,
        "errors": errors,
    }


def _task_report(task):
    package = build_ollama_task_package(task)
    aliases = sorted((package.get("fact_ref_map") or {}).keys())
    hidden_catalog = _hidden_catalog_name(package)
    forbidden_value = next((
        str(value) for value in package.get("output_safety_forbidden_values") or ()
        if len(str(value).strip()) >= 3
        and str(value).casefold() not in _visible_text(package)
    ), "")
    probes = {
        "external_url": _run_probe(package, "https://example.invalid", "external_url"),
        "technical_id": _run_probe(
            package, "event_deadbeef123456", "internal_identifier_leak"
        ),
        "control_field": _run_probe(package, "semantic_facts", "control_metadata_leak"),
        "model_alias": _run_probe(
            package, aliases[0] if aliases else "f01", "model_alias_leak"
        ),
        "email": _run_probe(
            package, "ghost@example.com", "credential_or_personal_data_leak"
        ),
        "network_address": _run_probe(package, "10.20.30.40", "network_address_leak"),
        "coordinates": _run_probe(
            package, "-37.81179, 144.96324", "raw_coordinate_leak"
        ),
        "filesystem_path": _run_probe(
            package, "/home/ghost/secret.db", "filesystem_path_leak"
        ),
        "unsafe_markup": _run_probe(package, "<script>alert(1)</script>", "unsafe_markup"),
        "hidden_catalog_name": _run_probe(
            package, hidden_catalog, "audience_hidden_catalog_value"
        ),
        "free_narrative_language": _run_probe(
            package, "Drugi sygnał odsłonił 2 ślady i możliwe zagrożenie."
        ),
    }
    if forbidden_value:
        probes["hidden_audience_value"] = _run_probe(
            package, forbidden_value, "audience_hidden_value_leak"
        )
    return {
        "ok": all(item["ok"] for item in probes.values()),
        "task_id": task.get("outbox_id"),
        "target_medium": task.get("target_medium"),
        "audience_scope": task.get("audience_scope"),
        "prompt_version": task.get("prompt_version"),
        "output_safety_contract_version": package.get(
            "output_safety_contract_version"
        ) or "",
        "forbidden_value_count": len(
            package.get("output_safety_forbidden_values") or ()
        ),
        "probes": probes,
    }


def build_report(repository, *, event_id=""):
    if not event_id:
        event = next((
            item for item in repository.list_events(limit=1000)
            if item.get("event_type") == "ghost.part_discovered"
        ), None)
        event_id = str((event or {}).get("event_id") or "")
    tasks = [
        task for task in repository.list_narrative_outbox(
            source_scope="ghostnetwork", source_event_id=event_id, limit=100,
        )
        if task.get("prompt_version") in ACTIVE_PROMPTS
    ] if event_id else []
    samples = [_task_report(task) for task in sorted(tasks, key=lambda item: (
        item.get("target_medium") or "",
        item.get("audience_scope") or "",
    ))]
    errors = []
    if not event_id:
        errors.append("source_event_missing")
    elif not samples:
        errors.append("active_prompt_tasks_missing")
    if any(not sample["ok"] for sample in samples):
        errors.append("output_safety_probe_failed")
    return {
        "ok": not errors,
        "contract_version": AUDIT_CONTRACT_VERSION,
        "output_safety_contract_version": GHOST_OUTPUT_SAFETY_CONTRACT_VERSION,
        "event_id": event_id,
        "errors": errors,
        "sample_count": len(samples),
        "samples": samples,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Read-only Sprint 137.2 allowed/forbidden knowledge audit",
    )
    parser.add_argument("--db", default="", help="Optional SQLite database path")
    parser.add_argument("--event-id", default="", help="Existing GhostNetwork event")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args(argv)
    repository = GhostNetworkRepository(db_path=args.db) if args.db else GhostNetworkRepository()
    report = build_report(repository, event_id=args.event_id)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] or not args.strict else 2


if __name__ == "__main__":
    raise SystemExit(main())
