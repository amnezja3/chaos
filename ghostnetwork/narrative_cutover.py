from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from .ollama_policy import verify_prompt_registry
from .ollama_worker import active_ollama_worker_policies
from .repository import GhostNetworkRepository


CUTOVER_CONTRACT_VERSION = "canonical-narrative-cutover-v1"
REQUIRED_PUBLICATION_MEDIA = ("blacknet", "googleplex_news", "cyberner")


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
    task_queue = repository.narrative_task_queue_counts(policies, now=now)
    publication_queue = repository.narrative_publication_queue_counts(now=now)
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
        "task_queue": task_queue,
        "publication_queue": publication_queue,
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
