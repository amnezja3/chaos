from __future__ import annotations

from copy import deepcopy

from .repository import GhostNetworkRepository, _clean, _hash_id


CANON_VERSION = "ghostnetwork-narrative-v1"
OUTBOX_STATUSES = {"created", "ready", "processing", "processed", "failed", "expired", "archived"}
TRUTH_CLASSES = {"canonical", "interpretation", "rumor", "propaganda", "narrative_deception"}
NARRATIVE_MEDIA = {"blacknet", "cyberner", "radio", "ollama_outbox"}
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
        event = event if isinstance(event, dict) else {}
        event_type = _clean(event.get("event_type"))
        if not event_type:
            return {"ok": False, "reason": "missing_event_type", "outbox": []}

        audiences = self._audiences_for_event(event)
        outbox = []
        errors = []
        for audience in audiences:
            facts = self.build_facts(event, audience)
            if not facts:
                continue
            for medium in self._media_for_event(event, audience):
                try:
                    if medium == "blacknet":
                        item = self.enqueue_blacknet(event, audience, facts)
                    elif medium == "cyberner":
                        item = self.enqueue_cyberner(event, audience, facts)
                    elif medium == "radio":
                        item = self.enqueue_radio(event, audience, facts)
                    elif medium == "ollama_outbox":
                        item = self.enqueue_ollama_outbox(event, audience, facts)
                    else:
                        continue
                    outbox.append(item)
                except Exception as exc:  # narrative failures cannot rollback mechanics
                    errors.append({"medium": medium, "error": str(exc)})
        return {
            "ok": not errors,
            "event_id": _clean(event.get("event_id")),
            "event_type": event_type,
            "outbox": outbox,
            "errors": errors,
        }

    def build_facts(self, event, audience):
        event = event if isinstance(event, dict) else {}
        audience = audience if isinstance(audience, dict) else {}
        event_type = _clean(event.get("event_type"))
        kind = _event_kind(event_type)
        if kind == "signal_sent":
            return self._signal_sent_facts(event, audience)
        if kind in {
            "part_discovered",
            "part_contained",
            "part_activated",
            "part_revealed",
            "part_recovered",
            "part_defended",
            "machine_online",
            "connection_completed",
            "cycle_locked",
            "version_changed",
            "stabilization_started",
        }:
            return [self._generic_domain_fact(event, audience)]
        return []

    def enqueue_blacknet(self, event, audience, facts):
        return self._enqueue(event, audience, facts, "blacknet")

    def enqueue_cyberner(self, event, audience, facts):
        return self._enqueue(event, audience, facts, "cyberner")

    def enqueue_radio(self, event, audience, facts):
        return self._enqueue(event, audience, facts, "radio")

    def enqueue_ollama_outbox(self, event, audience, facts):
        return self._enqueue(event, audience, facts, "ollama_outbox")

    def retry_failed_publications(self, limit=100):
        candidates = []
        for status in ("created", "failed"):
            candidates.extend(self.repository.list_narrative_outbox(status=status, limit=limit))
        retried = []
        for item in candidates[: max(1, int(limit or 100))]:
            retried.append(
                self.repository.update_narrative_outbox_status(
                    item["outbox_id"],
                    "ready",
                    processed_at="",
                    validation={**(item.get("validation") or {}), "retry_requested_at": self.repository.now()},
                )
            )
        return {"ok": True, "retried": [item for item in retried if item], "count": len([item for item in retried if item])}

    def validate_model_output(self, outbox_item, output):
        outbox_item = outbox_item if isinstance(outbox_item, dict) else {}
        output = output if isinstance(output, dict) else {}
        errors = []
        if _clean(output.get("medium")) != _clean(outbox_item.get("medium")):
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
            "medium": outbox_item.get("medium"),
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
        status = "ready" if validation["ok"] else "failed"
        event_id = _clean(event.get("event_id"))
        signal_id = self._resolve_signal_id(event)
        audience_scope = _clean(audience.get("scope"), "public")
        audience_clan = _clean(audience.get("clan"))
        dedupe_key = f"ghost:narrative:{event_id}:{medium}:{audience_scope}:{audience_clan}:{signal_id}"
        return self.repository.insert_narrative_outbox(
            {
                "outbox_id": _hash_id("narrative", event_id, medium, audience_scope, audience_clan, signal_id),
                "event_id": event_id,
                "cycle_id": _clean(event.get("cycle_id")),
                "signal_id": signal_id,
                "audience_scope": audience_scope,
                "audience_clan": audience_clan,
                "audience_owner": _clean(audience.get("owner")),
                "medium": medium,
                "truth_class": self._truth_class_for_facts(facts),
                "facts": facts,
                "allowed_actions": self._allowed_actions_for_event(event, medium),
                "canon_version": self.canon_version,
                "ghostsystem_version": self._ghostsystem_version_for_event(event),
                "status": status,
                "validation": validation,
                "dedupe_key": dedupe_key,
            }
        )

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
        return {
            "fact_id": f"ghost_fact:{event_id}:{kind}:{_clean(audience.get('scope'), 'public')}",
            "event_id": event_id,
            "cycle_id": _clean(event.get("cycle_id")),
            "audience_scope": _clean(audience.get("scope"), "public"),
            "truth_class": "canonical",
            "fact_type": kind,
            "entity_id": _clean(event.get("entity_id") or event.get("part_id")),
            "state_version": _safe_int(event.get("state_version")),
        }

    def _allowed_actions_for_event(self, event, medium):
        kind = _event_kind(event.get("event_type"))
        actions = []
        if kind == "signal_sent":
            actions.extend(
                [
                    {"cta_action": "open_ghostnetwork_suite", "payload": {"cycle_id": _clean(event.get("cycle_id"))}},
                    {"cta_action": "open_ghostsignal_archive", "payload": {"signal_id": self._resolve_signal_id(event)}},
                    {"cta_action": "open_cyberner_channel", "payload": {"channel": "world"}},
                ]
            )
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
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        return _clean(payload.get("signal_id") or event.get("signal_id") or event.get("entity_id"))

    def _audiences_for_event(self, event):
        return [{"scope": "public", "clan": "", "owner": ""}]

    def _media_for_event(self, event, audience):
        kind = _event_kind(event.get("event_type"))
        if kind == "signal_sent":
            return ["blacknet", "cyberner", "radio", "ollama_outbox"]
        if kind in {"cycle_locked", "connection_completed", "part_discovered", "machine_online"}:
            return ["blacknet", "cyberner", "ollama_outbox"]
        return ["blacknet", "ollama_outbox"]
