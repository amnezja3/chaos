from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from .ollama_policy import verify_prompt_registry
from .ollama_worker import active_ollama_worker_policies
from .narrative import (
    GHOST_EVENT_LINEAGE_EPOCH,
    GHOST_EVENT_POLICY,
    GhostNarrativePublisher,
)
from .repository import GhostNetworkRepository
from .narrative_support import NarrativeSupportLayer
from .llm.output_safety import verify_ghost_output_safety


CUTOVER_CONTRACT_VERSION = "canonical-narrative-cutover-v1"
REQUIRED_PUBLICATION_MEDIA = ("blacknet", "googleplex_news", "cyberner")


def build_ghost_event_lineage_report(
    repository, *, since=GHOST_EVENT_LINEAGE_EPOCH, limit=500,
):
    """Bounded event-to-task completeness audit for Sprint 136 ingress."""
    if not hasattr(repository, "list_events") or not hasattr(repository, "list_narrative_outbox"):
        return {
            "since": since,
            "limit": limit,
            "eligible_events": 0,
            "expected_tasks": 0,
            "eligible_without_task": 0,
            "missing_expected_tasks": 0,
            "tasks_with_missing_event": 0,
            "unexpected_medium": 0,
            "wrong_audience": 0,
            "samples": [],
        }

    limit = max(1, min(int(limit or 500), 1000))
    events = [
        event for event in repository.list_events(limit=limit)
        if str(event.get("created_at") or "") >= str(since or "")
        and event.get("event_type") in GHOST_EVENT_POLICY
    ]
    event_ids = {str(event.get("event_id") or "") for event in events}
    expected_tasks = 0
    missing_expected_tasks = 0
    unexpected_medium = 0
    wrong_audience = 0
    eligible_without_task = 0
    samples = []
    publisher = GhostNarrativePublisher(repository=repository)

    for event in events:
        event_id = str(event.get("event_id") or "")
        expected = {
            (
                audience["scope"], audience.get("clan") or "",
                audience.get("owner") or "", medium,
            )
            for audience in publisher.resolve_event_audiences(event)
            for medium in publisher.target_media_for_audience(
                GHOST_EVENT_POLICY[event["event_type"]], audience,
            )
        }
        tasks = repository.list_narrative_outbox(
            source_scope="ghostnetwork", source_event_id=event_id, limit=25,
        )
        actual = {
            (
                str(task.get("audience_scope") or ""),
                str(task.get("audience_clan") or ""),
                str(task.get("audience_owner") or ""),
                str(task.get("target_medium") or ""),
            )
            for task in tasks
        }
        missing = sorted(expected - actual)
        unexpected = sorted(actual - expected)
        wrong = sorted(
            str(task.get("outbox_id") or "") for task in tasks
            if not (
                task.get("audience_scope") == "public"
                and not task.get("audience_clan") and not task.get("audience_owner")
                or task.get("audience_scope") == "clan"
                and bool(task.get("audience_clan")) and not task.get("audience_owner")
                or task.get("audience_scope") == "owner"
                and bool(task.get("audience_owner")) and not task.get("audience_clan")
            )
        )
        expected_tasks += len(expected)
        missing_expected_tasks += len(missing)
        unexpected_medium += len(unexpected)
        wrong_audience += len(wrong)
        if missing:
            eligible_without_task += 1
        if (missing or unexpected or wrong) and len(samples) < 25:
            samples.append({
                "event_id": event_id,
                "event_type": event.get("event_type"),
                "missing_identities": missing,
                "unexpected_identities": unexpected,
                "wrong_audience_task_ids": wrong[:5],
            })

    tasks_with_missing_event = 0
    for task in repository.list_narrative_outbox(
        source_scope="ghostnetwork", limit=1000,
    ):
        if str(task.get("created_at") or "") < str(since or ""):
            continue
        source_event_id = str(task.get("source_event_id") or "")
        if source_event_id not in event_ids and not repository.get_event(source_event_id):
            tasks_with_missing_event += 1
            if len(samples) < 25:
                samples.append({
                    "outbox_id": task.get("outbox_id"),
                    "source_event_id": source_event_id,
                    "reason": "task_source_event_missing",
                })

    return {
        "since": since,
        "limit": limit,
        "eligible_events": len(events),
        "expected_tasks": expected_tasks,
        "eligible_without_task": eligible_without_task,
        "missing_expected_tasks": missing_expected_tasks,
        "tasks_with_missing_event": tasks_with_missing_event,
        "unexpected_medium": unexpected_medium,
        "wrong_audience": wrong_audience,
        "samples": samples,
    }


def _bool_value(value, default=False):
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _positive_int(value, default):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return int(default)


@dataclass(frozen=True)
class NarrativeCutoverConfig:
    ollama_worker_enabled: bool
    publisher_enabled: bool
    legacy_file_queue_enabled: bool
    max_ready_tasks: int = 500
    max_ready_publications: int = 100

    @classmethod
    def from_env(cls, environ=None):
        environ = environ if environ is not None else os.environ
        return cls(
            ollama_worker_enabled=_bool_value(
                environ.get("CHAOS_OLLAMA_WORKER_ENABLED"), False
            ),
            publisher_enabled=_bool_value(
                environ.get("CHAOS_NARRATIVE_PUBLISHER_ENABLED"), False
            ),
            legacy_file_queue_enabled=_bool_value(
                environ.get("CHAOS_NARRATIVE_LEGACY_FILE_QUEUE_ENABLED"), False
            ),
            max_ready_tasks=_positive_int(
                environ.get("CHAOS_NARRATIVE_MAX_READY_TASKS"), 500
            ),
            max_ready_publications=_positive_int(
                environ.get("CHAOS_NARRATIVE_MAX_READY_PUBLICATIONS"), 100
            ),
        )


def build_narrative_cutover_report(
    repository=None, *, config=None, now=None,
):
    """Build a bounded, profile-free readiness report for the final cutover."""
    repository = repository or GhostNetworkRepository()
    config = config or NarrativeCutoverConfig.from_env()
    now = now or datetime.now(timezone.utc)
    policies = active_ollama_worker_policies()
    prompt_registry = verify_prompt_registry()
    narrative_support = NarrativeSupportLayer().verify()
    output_safety = verify_ghost_output_safety()
    task_queue = repository.narrative_task_queue_counts(policies, now=now)
    publication_queue = repository.narrative_publication_queue_counts(now=now)
    ghost_event_lineage = build_ghost_event_lineage_report(repository)
    ghost_event_bridge = (
        repository.narrative_bridge_metrics()
        if hasattr(repository, "narrative_bridge_metrics") else {}
    )
    published_by_medium = publication_queue.get("published_by_medium") or {}

    errors = []
    warnings = []
    if not config.ollama_worker_enabled:
        errors.append("ollama_worker_disabled")
    if not config.publisher_enabled:
        errors.append("narrative_publisher_disabled")
    if config.legacy_file_queue_enabled:
        errors.append("legacy_file_queue_enabled")
    if not prompt_registry.get("ok"):
        errors.append("prompt_registry_invalid")
    if not narrative_support.get("ok"):
        errors.append("narrative_support_invalid")
    if not output_safety.get("ok"):
        errors.append("ghost_output_safety_invalid")
    if task_queue.get("active_legacy_file_tasks"):
        errors.append("active_legacy_file_tasks")
    if task_queue.get("ineligible_ready"):
        errors.append("ineligible_ready_tasks")
    if task_queue.get("expired_leases"):
        errors.append("expired_task_leases")
    if publication_queue.get("expired_claims"):
        errors.append("expired_publication_claims")
    if int(task_queue.get("eligible_ready") or 0) > config.max_ready_tasks:
        errors.append("task_backpressure_limit_exceeded")
    if int(publication_queue.get("ready_now") or 0) > config.max_ready_publications:
        errors.append("publication_backpressure_limit_exceeded")
    missing_media = [
        medium for medium in REQUIRED_PUBLICATION_MEDIA
        if int(published_by_medium.get(medium) or 0) <= 0
    ]
    if missing_media:
        errors.append("publication_medium_coverage_missing")
    if publication_queue.get("unstaged_accepted"):
        warnings.append("unstaged_accepted_candidates")
    if ghost_event_lineage.get("eligible_without_task"):
        errors.append("ghost_eligible_events_without_tasks")
    if ghost_event_lineage.get("tasks_with_missing_event"):
        errors.append("ghost_tasks_without_source_event")
    if ghost_event_lineage.get("unexpected_medium"):
        errors.append("ghost_tasks_with_unexpected_medium")
    if ghost_event_lineage.get("wrong_audience"):
        errors.append("ghost_tasks_with_wrong_audience")

    return {
        "ok": not errors,
        "contract_version": CUTOVER_CONTRACT_VERSION,
        "checked_at": now.astimezone(timezone.utc).isoformat(),
        "errors": errors,
        "warnings": warnings,
        "runtime": {
            "ollama_worker_enabled": config.ollama_worker_enabled,
            "publisher_enabled": config.publisher_enabled,
            "legacy_file_queue_enabled": config.legacy_file_queue_enabled,
        },
        "prompt_registry": prompt_registry,
        "narrative_support": narrative_support,
        "output_safety": output_safety,
        "task_queue": task_queue,
        "publication_queue": publication_queue,
        "ghost_event_lineage": ghost_event_lineage,
        "ghost_event_bridge": ghost_event_bridge,
        "required_publication_media": list(REQUIRED_PUBLICATION_MEDIA),
        "missing_publication_media": missing_media,
        "legacy_file_outbox": {
            "runtime_queue": False,
            "diagnostic_export_only": True,
        },
        "heavy_profile": {
            "profile_full_read": 0,
            "profile_full_write": 0,
            "profile_bytes": 0,
            "account_scan": 0,
        },
    }


def retire_cutover_ineligible_tasks(repository=None, *, limit=500, now=None):
    repository = repository or GhostNetworkRepository()
    return repository.retire_ineligible_narrative_tasks(
        active_ollama_worker_policies(), limit=limit, now=now,
    )
