from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .llm.semantic_input import SEMANTIC_INPUT_CONTRACT_VERSION


PUBLICATION_LIFECYCLE_CONTRACT_VERSION = "ghostnetwork-publication-lifecycle-v1"
ACTIVE_PUBLICATION_STATES = frozenset({"active"})
TERMINAL_PUBLICATION_STATES = frozenset({"expired", "invalidated", "legacy"})
SIGNIFICANCE_RANK = {"low": 1, "normal": 2, "high": 3, "critical": 4}


EVENT_FAMILY_TTL_SECONDS = {
    "part_discovered": 24 * 60 * 60,
    "part_contained": 12 * 60 * 60,
    "part_revealed": 24 * 60 * 60,
    "part_activated": 24 * 60 * 60,
    "part_deactivated": 6 * 60 * 60,
    "part_defended": 12 * 60 * 60,
    "part_recovered": 12 * 60 * 60,
    "part_contested": 2 * 60 * 60,
    "part_conflict_resolved": 12 * 60 * 60,
    "connection_created": 30 * 60,
    "machine_progress_changed": 30 * 60,
    "machine_online": 24 * 60 * 60,
    "machine_offline": 6 * 60 * 60,
    "cycle_locked": 24 * 60 * 60,
    "signal_sent": 7 * 24 * 60 * 60,
    "version_changed": 24 * 60 * 60,
    "stabilization_started": 6 * 60 * 60,
    "cycle_activated": 24 * 60 * 60,
}


PRESENTATION_FAMILY_BY_EVENT = {
    "part_discovered": "ghost_discovery",
    "part_revealed": "ghost_discovery",
    "part_contained": "ghost_containment",
    "part_activated": "ghost_activation",
    "part_deactivated": "ghost_recovery",
    "part_defended": "ghost_recovery",
    "part_recovered": "ghost_recovery",
    "part_contested": "ghost_conflict",
    "part_conflict_resolved": "ghost_conflict",
    "connection_created": "ghost_machine",
    "machine_progress_changed": "ghost_machine",
    "machine_online": "ghost_machine",
    "machine_offline": "ghost_machine",
    "cycle_locked": "ghost_cycle",
    "cycle_activated": "ghost_cycle",
    "stabilization_started": "ghost_cycle",
    "signal_sent": "ghost_signal",
    "version_changed": "ghost_system_transition",
}


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _iso(value):
    current = value if isinstance(value, datetime) else datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat()


def build_publication_lifecycle(task, *, now=None):
    """Build code-owned lifecycle metadata without consulting model output."""
    task = task if isinstance(task, dict) else {}
    validation = task.get("validation") if isinstance(task.get("validation"), dict) else {}
    source_scope = _clean(task.get("source_scope"))
    thread_id = _clean(task.get("narrative_thread_id") or validation.get("narrative_thread_id"))
    event_family = _clean(validation.get("event_family") or task.get("task_variant"))
    significance = _clean(validation.get("significance"), "normal").lower()
    if significance not in SIGNIFICANCE_RANK:
        significance = "normal"
    try:
        priority = int(task.get("priority") or 0)
    except (TypeError, ValueError):
        priority = 0
    try:
        source_state_version = max(0, int(task.get("world_state_version") or 0))
    except (TypeError, ValueError):
        source_state_version = 0

    valid_from = _iso(now)
    lifecycle_enabled = source_scope == "ghostnetwork" and bool(thread_id)
    ttl_seconds = EVENT_FAMILY_TTL_SECONDS.get(event_family, 6 * 60 * 60) if lifecycle_enabled else 0
    valid_until = ""
    if ttl_seconds:
        start = datetime.fromisoformat(valid_from.replace("Z", "+00:00"))
        valid_until = _iso(start + timedelta(seconds=ttl_seconds))
    return {
        "narrative_thread_id": thread_id,
        "event_family": event_family,
        "significance": significance,
        "priority": priority,
        "active_state": "active",
        "valid_from": valid_from,
        "valid_until": valid_until,
        "supersedes_medium_record_id": "",
        "invalidated_by_event_id": "",
        "invalidation_reason": "",
        "semantic_contract_version": (
            SEMANTIC_INPUT_CONTRACT_VERSION if lifecycle_enabled else ""
        ),
        "lifecycle_contract_version": (
            PUBLICATION_LIFECYCLE_CONTRACT_VERSION if lifecycle_enabled else ""
        ),
        "source_state_version": source_state_version,
        "presentation_family": PRESENTATION_FAMILY_BY_EVENT.get(
            event_family, "ghost_system_transition" if lifecycle_enabled else ""
        ),
        "publication_mode": "model",
    }


def publication_selection_key(record):
    record = record if isinstance(record, dict) else {}
    significance = _clean(record.get("significance"), "normal").lower()
    try:
        priority = int(record.get("priority") or 0)
    except (TypeError, ValueError):
        priority = 0
    published_at = _clean(record.get("published_at"))
    try:
        published_rank = datetime.fromisoformat(
            published_at.replace("Z", "+00:00")
        ).timestamp()
    except (TypeError, ValueError):
        published_rank = 0.0
    return (
        -SIGNIFICANCE_RANK.get(significance, SIGNIFICANCE_RANK["normal"]),
        -priority,
        -published_rank,
        _clean(record.get("medium_record_id")),
    )
