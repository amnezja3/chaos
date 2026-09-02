from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import time

from .repository import (
    GhostNetworkRepository,
    NARRATIVE_TASK_PROCESSOR,
    NARRATIVE_TASK_SCHEMA_VERSION,
    _clean,
    _hash_id,
    canonical_narrative_task_dedupe_key,
)
from .ollama_policy import assign_ollama_task_policy
from .visibility import GhostVisibilityService, _public_entity_id


CANON_VERSION = "ghostnetwork-narrative-v1"
TRUTH_CLASSES = {"canonical", "interpretation", "rumor", "propaganda", "narrative_deception"}
NARRATIVE_MEDIA = {"blacknet", "cyberner", "radio", "googleplex_news"}
EVENT_POLICY_VERSION = "ghostnetwork-event-policy-v2"
GHOST_EVENT_LINEAGE_EPOCH = "2026-09-02T00:00:00+00:00"
LOW_EVENT_AGGREGATION_WINDOW_SECONDS = 15
TECHNICAL_EVENT_TYPES = frozenset({
    "ghost.part_reserved", "ghost.part_reservation_attached",
    "ghost.part_reservation_released", "ghost.part_reservation_expired",
    "ghost.part_updated", "ghost.part_consumed", "ghost.reward_pending",
    "ghost.delta_published", "ghost.health_check_completed",
    "ghost.cycle_status_changed",
})


def _event_policy(significance, priority, intent, cta_family, *extra_media):
    media = ("blacknet", *extra_media)
    if significance in {"high", "critical"}:
        media = (*media, "googleplex_news")
    return {
        "eligible": True, "significance": significance, "priority": priority,
        "narrative_intent": intent, "target_media": media,
        "cta_family": cta_family, "content_kind": "ghostnetwork_event",
    }


GHOST_EVENT_POLICY = {
    "ghost.part_discovered": _event_policy("high", 80, "ghost_part_discovery", "part"),
    "ghost.part_contained": _event_policy("normal", 50, "ghost_part_containment", "territory"),
    "ghost.part_revealed": _event_policy("normal", 55, "ghost_part_discovery", "part"),
    "ghost.part_activated": _event_policy("high", 80, "ghost_part_activation", "part"),
    "ghost.part_deactivated": _event_policy("normal", 50, "ghost_part_activation", "territory"),
    "ghost.part_defended": _event_policy("high", 75, "ghost_part_conflict", "part"),
    "ghost.part_recovered": _event_policy("high", 85, "ghost_part_recovery", "part"),
    "ghost.part_contested": _event_policy("high", 85, "ghost_part_conflict", "part"),
    "ghost.part_conflict_resolved": _event_policy("high", 90, "ghost_part_conflict", "part"),
    "ghost.connection_created": _event_policy("low", 20, "ghost_machine_progress", "suite"),
    "ghost.machine_progress_changed": _event_policy("low", 20, "ghost_machine_progress", "suite"),
    "ghost.machine_online": _event_policy("high", 85, "ghost_machine_state", "suite", "cyberner"),
    "ghost.machine_offline": _event_policy("normal", 55, "ghost_machine_state", "suite"),
    "ghost.cycle_locked": _event_policy("critical", 100, "ghost_cycle_state", "suite", "cyberner"),
    "ghost.signal_sent": _event_policy("critical", 100, "ghost_signal_transmission", "signal", "cyberner", "radio"),
    "ghost.version_changed": _event_policy("critical", 100, "ghost_system_transition", "suite"),
    "ghost.stabilization_started": _event_policy("normal", 60, "ghost_cycle_state", "suite"),
    "ghost.cycle_activated": _event_policy("high", 85, "ghost_cycle_state", "suite"),
}
for _low_event_type in ("ghost.connection_created", "ghost.machine_progress_changed"):
    GHOST_EVENT_POLICY[_low_event_type].update({
        "aggregation_family": _low_event_type[6:],
        "aggregation_window_seconds": LOW_EVENT_AGGREGATION_WINDOW_SECONDS,
    })


def resolve_ghost_event_policy(event_type):
    event_type = _clean(event_type)
    policy = GHOST_EVENT_POLICY.get(event_type)
    if policy:
        return {"version": EVENT_POLICY_VERSION, "event_type": event_type, **policy}
    reason = "technical" if event_type in TECHNICAL_EVENT_TYPES else "unsupported"
    return {"version": EVENT_POLICY_VERSION, "event_type": event_type,
            "eligible": False, "reason": reason, "target_media": ()}
ALLOWED_CTA_ACTIONS = {
    "show_ghostnetwork_part",
    "show_ghostnetwork_node",
    "show_ghostnetwork_territory",
    "open_ghostnetwork_suite",
    "open_ghostsignal_archive",
    "open_cyberner_channel",
    "play_ghostnetwork_podcast",
}
FORBIDDEN_FACT_KEYS = {
    "password",
    "password_hash",
    "session",
    "sessions",
    "mail",
    "email",
    "profile",
    "raw_profile",
    "hidden_parts",
    "full_topology",
    "owner_only",
}


def _event_kind(event_type):
    event_type = _clean(event_type)
    return event_type[6:] if event_type.startswith("ghost.") else event_type


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _has_forbidden_key(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if _clean(key).lower() in FORBIDDEN_FACT_KEYS:
                return True
            if _has_forbidden_key(child):
                return True
    elif isinstance(value, list):
        return any(_has_forbidden_key(child) for child in value)
    return False


class GhostNarrativePublisher:
    """Build safe GhostNetwork narrative facts and media outbox records.

    The publisher is intentionally not a game-state writer. It reads only the
    domain event and approved immutable GhostNetwork snapshots, then stores
    idempotent publication tasks for existing media surfaces.
    """

    def __init__(self, repository=None, canon_version=CANON_VERSION):
        self.repository = repository or GhostNetworkRepository()
        self.canon_version = canon_version
        self.visibility = GhostVisibilityService(repository=self.repository)

    def publish_signal_transmission(self, signal_id):
        signal = self.repository.get_signal(signal_id)
        if not signal:
            return {"ok": False, "reason": "signal_not_found", "signal_id": _clean(signal_id), "outbox": []}
        event = self.repository.get_event_by_dedupe_key(f"ghost:signal_sent:{signal['cycle_id']}")
        if not event:
            event = {
                "event_id": _hash_id("event", signal["cycle_id"], "ghost.signal_sent", signal["signal_id"]),
                "event_type": "ghost.signal_sent",
                "cycle_id": signal["cycle_id"],
                "entity_id": signal["signal_id"],
                "part_id": "",
                "audience_scope": "public",
                "audience_clan": "",
                "payload": {
                    "signal_id": signal["signal_id"],
                    "signal_number": signal["signal_number"],
                    "lock_snapshot_id": signal.get("lock_snapshot_id"),
                    "signal_checksum": signal.get("signal_checksum"),
                },
                "created_at": signal.get("sent_at") or signal.get("created_at") or self.repository.now(),
            }
        return self.publish_domain_event(event)

    def publish_domain_event(self, event):
        started = time.perf_counter()
        event = event if isinstance(event, dict) else {}
        event_type = _clean(event.get("event_type"))
        if not event_type:
            return {"ok": False, "reason": "missing_event_type", "outbox": []}

        self._metric(event, "events_seen")
        policy = resolve_ghost_event_policy(event_type)
        if not policy["eligible"]:
            self._metric(event, f"events_ignored:{policy['reason']}")
            return {"ok": True, "reason": policy["reason"], "event_id": _clean(event.get("event_id")),
                    "event_type": event_type, "policy_version": policy["version"], "outbox": [], "errors": []}
        self._metric(event, "events_eligible")
        audiences = self.resolve_event_audiences(event)
        outbox = []
        errors = []
        for audience in audiences:
            facts = self.build_facts(event, audience)
            if not facts:
                continue
            for medium in self.target_media_for_audience(policy, audience):
                try:
                    if medium == "blacknet":
                        item = self.enqueue_blacknet(event, audience, facts)
                    elif medium == "cyberner":
                        item = self.enqueue_cyberner(event, audience, facts)
                    elif medium == "radio":
                        item = self.enqueue_radio(event, audience, facts)
                    elif medium == "googleplex_news":
                        item = self._enqueue(event, audience, facts, medium)
                    else:
                        continue
                    outbox.append(item)
                    self._metric(
                        event,
                        f"tasks:{event_type}:{audience['scope']}:{medium}",
                    )
                    if item.get("idempotent"):
                        self._metric(event, "deduplicated_tasks")
                except Exception as exc:  # narrative failures cannot rollback mechanics
                    errors.append({"medium": medium, "error": str(exc)})
                    self._metric(event, "task_errors")
        self._metric(event, "bridge_latency_ms", (time.perf_counter() - started) * 1000)
        return {
            "ok": not errors,
            "event_id": _clean(event.get("event_id")),
            "event_type": event_type,
            "policy_version": policy["version"],
            "outbox": outbox,
            "errors": errors,
        }

    def publish_persisted_event(self, event_id):
        event = self.repository.get_event(event_id)
        if not event:
            return {
                "ok": False,
                "reason": "persisted_event_not_found",
                "event_id": _clean(event_id),
                "outbox": [],
                "errors": [],
            }
        return self.publish_domain_event(event)

    def publish_persisted_events(self, events):
        results = []
        seen = set()
        for item in events or []:
            event_id = _clean(item.get("event_id") if isinstance(item, dict) else item)
            if not event_id or event_id in seen:
                continue
            seen.add(event_id)
            try:
                results.append(self.publish_persisted_event(event_id))
            except Exception as exc:
                results.append({
                    "ok": False,
                    "reason": "producer_failed",
                    "event_id": event_id,
                    "outbox": [],
                    "errors": [{"reason": "producer_failed", "error": str(exc)[:160]}],
                })
        return {
            "ok": all(item.get("ok") for item in results),
            "processed": len(results),
            "results": results,
        }

    def reconcile_persisted_events(self, *, since=GHOST_EVENT_LINEAGE_EPOCH, limit=500):
        limit = max(1, min(int(limit or 500), 1000))
        events = [
            event for event in self.repository.list_events(limit=limit)
            if _clean(event.get("created_at")) >= _clean(since)
            and resolve_ghost_event_policy(event.get("event_type"))["eligible"]
        ]
        incomplete = [
            event for event in reversed(events)
            if not self._has_complete_event_lineage(event)
        ]
        result = self.publish_persisted_events(incomplete)
        result.update({
            "since": _clean(since),
            "scanned": len(events),
            "incomplete": len(incomplete),
            "skipped_complete": len(events) - len(incomplete),
        })
        return result

    def _has_complete_event_lineage(self, event):
        """Return true when every audience/medium projection already exists.

        Reconciliation runs periodically, so it must not republish the entire
        bounded history on every preflight.  Source lookups include aggregate
        source links, which makes this check valid for both direct and merged
        narrative tasks.
        """
        event = event if isinstance(event, dict) else {}
        policy = resolve_ghost_event_policy(event.get("event_type"))
        if not policy.get("eligible"):
            return True
        expected = {
            (
                _clean(audience.get("scope"), "public"),
                _clean(audience.get("clan")),
                _clean(audience.get("owner")),
                _clean(medium),
            )
            for audience in self.resolve_event_audiences(event)
            for medium in self.target_media_for_audience(policy, audience)
        }
        actual = {
            (
                _clean(task.get("audience_scope"), "public"),
                _clean(task.get("audience_clan")),
                _clean(task.get("audience_owner")),
                _clean(task.get("target_medium")),
            )
            for task in self.repository.list_narrative_outbox(
                source_scope="ghostnetwork",
                source_event_id=event.get("event_id"),
                limit=25,
            )
        }
        return expected.issubset(actual)

    def build_facts(self, event, audience):
        event = event if isinstance(event, dict) else {}
        audience = audience if isinstance(audience, dict) else {}
        event_type = _clean(event.get("event_type"))
        policy = resolve_ghost_event_policy(event_type)
        if not policy["eligible"]:
            return []
        kind = _event_kind(event_type)
        if kind == "signal_sent":
            return self._signal_sent_facts(event, audience)
        if kind in {
            "part_discovered",
            "part_contained",
            "part_activated",
            "part_contested",
            "part_conflict_resolved",
            "part_deactivated",
            "part_revealed",
            "part_recovered",
            "part_defended",
            "machine_online",
            "machine_offline",
            "machine_progress_changed",
            "connection_created",
            "cycle_locked",
            "version_changed",
            "stabilization_started",
            "cycle_activated",
        }:
            return [self._generic_domain_fact(event, audience)]
        return []

    def enqueue_blacknet(self, event, audience, facts):
        return self._enqueue(event, audience, facts, "blacknet")

    def enqueue_cyberner(self, event, audience, facts):
        return self._enqueue(event, audience, facts, "cyberner")

    def enqueue_radio(self, event, audience, facts):
        return self._enqueue(event, audience, facts, "radio")

    def retry_failed_publications(self, limit=100):
        candidates = self.repository.list_narrative_outbox(status="retry_wait", limit=limit)
        retried = []
        for item in candidates[: max(1, int(limit or 100))]:
            retried.append(
                self.repository.requeue_narrative_task(
                    item["outbox_id"],
                    validation={**(item.get("validation") or {}), "retry_requested_at": self.repository.now()},
                )
            )
        return {"ok": True, "retried": [item for item in retried if item], "count": len([item for item in retried if item])}

    def validate_model_output(self, outbox_item, output):
        outbox_item = outbox_item if isinstance(outbox_item, dict) else {}
        output = output if isinstance(output, dict) else {}
        errors = []
        if _clean(output.get("medium")) != _clean(outbox_item.get("target_medium") or outbox_item.get("medium")):
            errors.append("medium_mismatch")
        if _clean(output.get("truth_class"), "canonical") not in TRUTH_CLASSES:
            errors.append("invalid_truth_class")
        fact_ids = {fact.get("fact_id") for fact in outbox_item.get("facts") or [] if isinstance(fact, dict)}
        for fact_ref in output.get("fact_refs") or []:
            if fact_ref not in fact_ids:
                errors.append("unknown_fact_ref")
                break
        cta_action = _clean(output.get("cta_action"))
        if cta_action and cta_action not in {
            action.get("cta_action") for action in outbox_item.get("allowed_actions") or [] if isinstance(action, dict)
        }:
            errors.append("cta_not_allowed")
        if _has_forbidden_key(output):
            errors.append("forbidden_data")
        for field in ("title", "body"):
            if len(_clean(output.get(field))) > 4000:
                errors.append(f"{field}_too_long")
        if "http://" in _clean(output.get("body")).lower() or "https://" in _clean(output.get("body")).lower():
            errors.append("external_url")
        return {"ok": not errors, "errors": errors}

    def build_model_input_package(self, outbox_item):
        outbox_item = outbox_item if isinstance(outbox_item, dict) else {}
        return {
            "task_id": outbox_item.get("outbox_id"),
            "canon_version": outbox_item.get("canon_version") or self.canon_version,
            "ghostsystem_version": outbox_item.get("ghostsystem_version"),
            "cycle_id": outbox_item.get("cycle_id"),
            "signal_id": outbox_item.get("signal_id"),
            "processor": outbox_item.get("processor") or NARRATIVE_TASK_PROCESSOR,
            "medium": outbox_item.get("target_medium") or outbox_item.get("medium"),
            "audience": {
                "scope": outbox_item.get("audience_scope"),
                "clan": outbox_item.get("audience_clan"),
                "owner": outbox_item.get("audience_owner"),
            },
            "facts": deepcopy(outbox_item.get("facts") or []),
            "allowed_actions": deepcopy(outbox_item.get("allowed_actions") or []),
            "editorial_rules": {
                "no_new_game_state": True,
                "no_new_entities": True,
                "mechanical_facts_remain_canonical": True,
                "no_external_urls": True,
            },
            "limits": {"title": 96, "body": 900},
        }

    def _enqueue(self, event, audience, facts, medium):
        medium = _clean(medium)
        if medium not in NARRATIVE_MEDIA:
            raise ValueError(f"Invalid GhostNetwork narrative medium: {medium}")
        facts = facts if isinstance(facts, list) else []
        validation = self._validate_publication(event, audience, facts, medium)
        status = "ready" if validation["ok"] else "retry_wait"
        event_id = _clean(event.get("event_id"))
        signal_id = self._resolve_signal_id(event)
        audience_scope = _clean(audience.get("scope"), "public")
        audience_clan = _clean(audience.get("clan"))
        policy = resolve_ghost_event_policy(event.get("event_type"))
        source_ref = _clean(facts[0].get("fact_id")) if facts else ""
        source_version = hashlib.sha1(json.dumps(
            facts, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()[:16]
        fixed_action = self._allowed_actions_for_event(event, medium)[0]
        is_googleplex = medium == "googleplex_news"
        slot_state = self.repository.get_narrative_slot_state(medium, "gp-home-world-grid") if is_googleplex else None
        task = {
                "schema_version": NARRATIVE_TASK_SCHEMA_VERSION,
                "event_id": event_id,
                "source_scope": "ghostnetwork",
                "source_event_id": event_id,
                "cycle_id": _clean(event.get("cycle_id")),
                "signal_id": signal_id,
                "audience_scope": audience_scope,
                "audience_clan": audience_clan,
                "audience_owner": _clean(audience.get("owner")),
                "processor": NARRATIVE_TASK_PROCESSOR,
                "target_medium": medium,
                "truth_class": self._truth_class_for_facts(facts),
                "truth_class_policy": self._truth_class_for_facts(facts),
                "facts": facts,
                 "allowed_actions": [fixed_action],
                "canon_version": self.canon_version,
                "ghostsystem_version": self._ghostsystem_version_for_event(event),
                "world_state_version": str(_safe_int(event.get("state_version"))),
                "prompt_version": "unassigned",
                "output_schema_version": "unassigned",
                "model_policy_version": "unassigned",
                 "task_variant": "googleplex_world_dispatch" if is_googleplex else (_event_kind(event.get("event_type")) or "default"),
                 "narrative_intent": policy["narrative_intent"],
                 "content_kind": "world_dispatch" if is_googleplex else policy["content_kind"],
                 "presentation_slot": "gp-home-world-grid" if is_googleplex else "",
                 "selected_source_ref": source_ref,
                 "selected_source_version": source_version,
                 "expected_slot_version": int((slot_state or {}).get("version") or 0),
                 "fixed_action": fixed_action,
                 "allowed_asset_roles": ["neutral", "network"] if is_googleplex else [],
                 "priority": policy["priority"],
                 "narrative_thread_id": self._narrative_thread_id_for_audience(event, audience),
                 "status": status,
                 "validation": {**validation, "event_policy_version": policy["version"],
                                "significance": policy["significance"],
                                "narrative_thread_id": self._narrative_thread_id_for_audience(event, audience),
                                "profile_full_read": 0, "profile_full_write": 0,
                                "profile_bytes": 0, "account_scan": 0,
                                "all_user_profile_scan": 0, "per_recipient_profile_read": 0},
            }
        task = assign_ollama_task_policy(task)
        task["dedupe_key"] = canonical_narrative_task_dedupe_key(task)
        task["outbox_id"] = _hash_id("narrative_task", task["dedupe_key"])
        if policy.get("aggregation_family"):
            return self._enqueue_low_event_aggregate(task, event)
        return self.repository.enqueue_narrative_task(task)

    def _enqueue_low_event_aggregate(self, task, event):
        policy = resolve_ghost_event_policy(event.get("event_type"))
        family = _clean(policy.get("aggregation_family"))
        window = max(1, int(policy.get("aggregation_window_seconds") or 15))
        now = datetime.fromisoformat(self.repository.now().replace("Z", "+00:00"))
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        threshold = (now - timedelta(seconds=window)).astimezone(timezone.utc).isoformat()
        release_at = (now + timedelta(seconds=window)).astimezone(timezone.utc).isoformat()
        task["next_attempt_at"] = release_at
        task["content_kind"] = "ghostnetwork_event_aggregate"
        task["facts"] = self._aggregate_fact(task.get("facts"), family, 1)
        task["validation"] = {
            **(task.get("validation") or {}),
            "aggregation_family": family,
            "aggregation_input": 1,
            "aggregation_output": 1,
            "aggregation_window_seconds": window,
        }
        task["selected_source_version"] = self._facts_version(task["facts"])
        self._metric(event, f"aggregation_input:{family}")

        with self.repository.transaction():
            existing_for_source = [
                item for item in self.repository.list_narrative_outbox(
                    source_scope="ghostnetwork",
                    source_event_id=event.get("event_id"),
                    limit=25,
                )
                if item.get("target_medium") == task.get("target_medium")
                and item.get("audience_scope") == task.get("audience_scope")
                and item.get("audience_clan") == task.get("audience_clan")
                and item.get("audience_owner") == task.get("audience_owner")
            ]
            if existing_for_source:
                result = existing_for_source[0]
                result["idempotent"] = True
                return result
            aggregate = self.repository.find_open_narrative_aggregate(
                cycle_id=task.get("cycle_id"), task_variant=task.get("task_variant"),
                narrative_thread_id=task.get("narrative_thread_id"),
                target_medium=task.get("target_medium"),
                audience_scope=task.get("audience_scope"),
                audience_clan=task.get("audience_clan"),
                audience_owner=task.get("audience_owner"),
                created_after=threshold,
            )
            if aggregate:
                count = int((aggregate.get("validation") or {}).get("aggregation_input") or 1) + 1
                facts = self._aggregate_fact(aggregate.get("facts"), family, count, event=event)
                validation = {
                    **(aggregate.get("validation") or {}),
                    "aggregation_input": count,
                    "aggregation_output": 1,
                }
                merged = self.repository.merge_narrative_aggregate(
                    aggregate["outbox_id"], event.get("event_id"),
                    facts=facts, validation=validation,
                    world_state_version=str(_safe_int(event.get("state_version"))),
                    selected_source_version=self._facts_version(facts),
                )
                if merged:
                    merged["aggregated"] = True
                    return merged
            self._metric(event, f"aggregation_output:{family}")
            return self.repository.enqueue_narrative_task(task)

    @staticmethod
    def _aggregate_fact(facts, family, count, event=None):
        fact = deepcopy((facts or [{}])[0])
        fact["fact_type"] = f"{family}_aggregate"
        fact["aggregation_family"] = family
        fact["event_count"] = max(1, int(count or 1))
        fact.setdefault("first_state_version", _safe_int(fact.get("state_version")))
        if event:
            fact["last_state_version"] = _safe_int(event.get("state_version"))
        else:
            fact["last_state_version"] = _safe_int(fact.get("state_version"))
        return [fact]

    @staticmethod
    def _facts_version(facts):
        return hashlib.sha1(json.dumps(
            facts or [], ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()[:16]

    def _validate_publication(self, event, audience, facts, medium):
        errors = []
        if not _clean(event.get("event_id")):
            errors.append("missing_event_id")
        if _clean(medium) not in NARRATIVE_MEDIA:
            errors.append("invalid_medium")
        for fact in facts:
            if not isinstance(fact, dict):
                errors.append("invalid_fact")
                continue
            if _clean(fact.get("truth_class")) not in TRUTH_CLASSES:
                errors.append("invalid_truth_class")
            if not _clean(fact.get("fact_id")) or not _clean(fact.get("event_id")):
                errors.append("invalid_fact_identity")
            if _has_forbidden_key(fact):
                errors.append("forbidden_fact_data")
            if _clean(audience.get("scope"), "public") == "public" and "parts" in fact:
                errors.append("public_parts_leak")
        return {"ok": not errors, "errors": sorted(set(errors)), "validated_at": self.repository.now()}

    def _signal_sent_facts(self, event, audience):
        signal_id = self._resolve_signal_id(event)
        signal = self.repository.get_signal(signal_id) if signal_id else None
        if not signal:
            return []
        lock = self.repository.get_cycle_lock_snapshot(signal["cycle_id"])
        snapshot = (lock or {}).get("snapshot") or {}
        if isinstance(snapshot.get("snapshot"), dict):
            snapshot = snapshot["snapshot"]
        parts = snapshot.get("parts") or []
        topology = snapshot.get("topology") or {}
        connections = topology.get("connections") or snapshot.get("connections") or []
        machines = snapshot.get("machines") or []
        cycle = self.repository.get_cycle(signal["cycle_id"]) or {}
        audience_scope = _clean(audience.get("scope"), "public")
        event_id = _clean(event.get("event_id"))
        base = {
            "event_id": event_id,
            "cycle_id": signal["cycle_id"],
            "audience_scope": audience_scope,
            "truth_class": "canonical",
            "signal_id": signal["signal_id"],
            "signal_number": _safe_int(signal.get("signal_number")),
            "ghostsignal_label": f"GHOSTSIGNAL {_safe_int(signal.get('signal_number')):04d}",
            "target_year": _safe_int(signal.get("target_year"), 2108),
            "status": "sent",
            "outcome": _clean(signal.get("outcome"), "pending"),
            "source_version": _safe_int(signal.get("source_version")),
            "next_version": _safe_int(signal.get("next_version") or cycle.get("ghostsystem_version")),
            "lock_snapshot_id": _clean(signal.get("lock_snapshot_id")),
            "lock_snapshot_checksum": _clean((lock or {}).get("snapshot_checksum")),
        }
        return [
            {
                **base,
                "fact_id": f"ghost_fact:{event_id}:signal_sent:{audience_scope}",
                "fact_type": "signal_sent",
                "headline": "GHOSTNETWORK // 20 WEZLOW",
                "public_text": "POLACZENIE ZAMKNIETE / TRANSMISJA DO 2108",
            },
            {
                **base,
                "fact_id": f"ghost_fact:{event_id}:network_closed:{audience_scope}",
                "fact_type": "network_closed",
                "part_count": len(parts) or 20,
                "connection_count": len(connections) or 20,
                "machine_count": len(machines) or 4,
            },
            {
                **base,
                "fact_id": f"ghost_fact:{event_id}:restart_required:{audience_scope}",
                "fact_type": "restart_required",
                "ghostsystem_version": _safe_int(cycle.get("ghostsystem_version") or signal.get("next_version")),
                "restart_required": bool(cycle.get("restart_required", True)),
                "confirmation_status": "no_confirmation",
            },
        ]

    def _generic_domain_fact(self, event, audience):
        kind = _event_kind(event.get("event_type"))
        event_id = _clean(event.get("event_id"))
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        part_id = _clean(event.get("part_id"))
        public_entity_id = _clean(event.get("public_entity_id"))
        if not public_entity_id and part_id:
            public_entity_id = _public_entity_id(event.get("cycle_id"), part_id)
        part = self.repository.get_part(part_id) if part_id else None
        projected = self.visibility.project_event_fact_for_audience({
            "event_type": event.get("event_type"), "public_entity_id": public_entity_id,
            "territory_contains_part": payload.get("territory_contains_part"),
            "previous_status": payload.get("previous_status"), "status": payload.get("status"),
            "previous_conflict_state": payload.get("previous_conflict_state"),
            "conflict_state": payload.get("conflict_state"),
            "owner_clan": (part or {}).get("clan_code") or payload.get("territory_clan"),
            "part_code": (part or {}).get("part_code"),
            "part_name": (part or {}).get("part_name"),
            "target_clan": payload.get("territory_clan") or event.get("clan_code"),
        }, {
            "audience_scope": _clean(audience.get("scope"), "public"),
            "viewer_id": _clean(audience.get("owner")),
            "viewer_clan": _clean(audience.get("clan")),
        })
        fact = {
            "fact_id": f"ghost_fact:{event_id}:{kind}:{_clean(audience.get('scope'), 'public')}",
            "event_id": event_id,
            "cycle_id": _clean(event.get("cycle_id")),
            "audience_scope": _clean(audience.get("scope"), "public"),
            "truth_class": "canonical",
            "fact_type": kind,
            "state_version": _safe_int(event.get("state_version")),
            **projected,
        }
        return fact

    def _allowed_actions_for_event(self, event, medium):
        kind = _event_kind(event.get("event_type"))
        policy = resolve_ghost_event_policy(event.get("event_type"))
        family = policy.get("cta_family")
        public_id = _clean(event.get("public_entity_id")) or (
            _public_entity_id(event.get("cycle_id"), event.get("part_id")) if event.get("part_id") else ""
        )
        if family == "part" and public_id:
            return [{"cta_action": "show_ghostnetwork_part", "payload": {"public_entity_id": public_id}}]
        if family == "territory":
            return [{"cta_action": "show_ghostnetwork_territory", "payload": {"public_entity_id": public_id}}]
        actions = []
        if kind == "signal_sent":
            actions.append({"cta_action": "open_ghostsignal_archive", "payload": {"signal_id": self._resolve_signal_id(event)}})
            if medium == "radio":
                actions.append(
                    {
                        "cta_action": "play_ghostnetwork_podcast",
                        "payload": {"signal_id": self._resolve_signal_id(event), "requires_active_radio": True},
                    }
                )
        else:
            actions.append({"cta_action": "open_ghostnetwork_suite", "payload": {"cycle_id": _clean(event.get("cycle_id"))}})
        return actions

    def _narrative_thread_id(self, event):
        return self._narrative_thread_id_for_audience(event, {"scope": "public"})

    def _narrative_thread_id_for_audience(self, event, audience):
        kind = _event_kind(event.get("event_type"))
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        conflict_id = _clean(payload.get("conflict_id"))
        if conflict_id and kind in {
            "part_contested", "part_conflict_resolved", "part_defended", "part_recovered",
        }:
            return f"ghost-conflict:{conflict_id}"
        if kind == "signal_sent":
            return f"ghost-signal:{self._resolve_signal_id(event)}"
        if kind.startswith("part_"):
            public_id = _clean(event.get("public_entity_id")) or _public_entity_id(event.get("cycle_id"), event.get("part_id"))
            scope = _clean(audience.get("scope"), "public")
            if scope == "public":
                return f"ghost-part:{public_id}"
            private_id = _hash_id(
                "ghost-part-projection", event.get("cycle_id"), event.get("part_id"),
                scope, audience.get("clan"), audience.get("owner"),
            )
            return f"ghost-part:{private_id}"
        if kind.startswith("machine_"):
            machine_code = _clean(payload.get("machine_code"))
            if not machine_code:
                machine_code = _clean(event.get("entity_id")).split(":")[-1]
            return f"ghost-machine:{_clean(event.get('cycle_id'))}:{machine_code}"
        return f"ghost-cycle:{_clean(event.get('cycle_id'))}"

    def _truth_class_for_facts(self, facts):
        classes = [_clean(fact.get("truth_class")) for fact in facts if isinstance(fact, dict)]
        return "canonical" if all(item == "canonical" for item in classes) else (classes[0] if classes else "canonical")

    def _ghostsystem_version_for_event(self, event):
        signal_id = self._resolve_signal_id(event)
        signal = self.repository.get_signal(signal_id) if signal_id else None
        if signal:
            return str(_safe_int(signal.get("next_version") or signal.get("source_version")))
        cycle = self.repository.get_cycle(_clean(event.get("cycle_id")))
        return str(_safe_int((cycle or {}).get("ghostsystem_version")))

    def _resolve_signal_id(self, event):
        if _event_kind(event.get("event_type")) != "signal_sent":
            return ""
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        return _clean(payload.get("signal_id") or event.get("signal_id") or event.get("entity_id"))

    def _audiences_for_event(self, event):
        audiences = [{"scope": "public", "clan": "", "owner": ""}]
        canonical = self.repository.get_event(event.get("event_id"))
        if not canonical:
            return audiences
        payload = canonical.get("payload") if isinstance(canonical.get("payload"), dict) else {}
        clans = {
            _clean(value) for value in (
                canonical.get("audience_clan"), canonical.get("clan_code"),
                payload.get("player_clan"), payload.get("territory_clan"),
                payload.get("previous_clan"), payload.get("new_clan"),
            ) if _clean(value)
        }
        owners = {
            _clean(value) for value in (
                canonical.get("player_id"), payload.get("player_id"),
                payload.get("territory_owner_id"), payload.get("previous_owner"),
                payload.get("new_owner"),
            ) if _clean(value)
        }
        audiences.extend({"scope": "clan", "clan": clan, "owner": ""} for clan in sorted(clans)[:3])
        audiences.extend({"scope": "owner", "clan": "", "owner": owner} for owner in sorted(owners)[:3])
        return audiences

    def resolve_event_audiences(self, event):
        return self._audiences_for_event(event)

    @staticmethod
    def target_media_for_audience(policy, audience):
        media = tuple((policy or {}).get("target_media") or ())
        if _clean((audience or {}).get("scope"), "public") == "public":
            return media
        # Private projections stay in the audience-filtered BlackNet surface.
        # They must never compete with public content for the global GGPL slot.
        return tuple(item for item in media if item == "blacknet")

    def _metric(self, event, metric_key, value=0):
        try:
            self.repository.record_narrative_bridge_metric(
                metric_key, _clean((event or {}).get("cycle_id")), value,
            )
        except Exception:
            return False
        return True
