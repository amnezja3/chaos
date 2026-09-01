from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone

from .repository import (
    NARRATIVE_TASK_PROCESSOR,
    NARRATIVE_TASK_SCHEMA_VERSION,
    _clean,
    _hash_id,
)
from .ollama_policy import assign_ollama_task_policy


BLACKNET_SOURCE_SCOPE = "blacknet_world"
GOOGLEPLEX_SOURCE_SCOPE = "googleplex_app"
APP_TARGET_MEDIA = {"cyberner"}
APP_ALLOWED_ACTIONS = {"open_cyberner_channel"}
BLACKNET_ALLOWED_ACTIONS = {
    "accept_blacknet_job",
    "focus_map_target",
    "none",
    "open_blacknet_detail",
    "open_blacknet_dossier",
    "open_blacknet_report",
    "open_cyberner",
    "open_cyberner_thread",
    "open_exchange_category",
    "open_exchange_market",
    "open_ghost_exchange",
    "open_blacknet",
    "open_googleplex",
    "open_googleplex_search",
    "open_map",
    "open_map_region",
    "open_operation",
    "open_radio",
    "open_operation_center",
    "play_radio_podcast",
    "show_hotspot",
    "start_operation",
    "teleport_to_hotspot",
}
FORBIDDEN_APP_REQUEST_KEYS = {
    "prompt",
    "system_prompt",
    "model",
    "processor",
    "audience",
    "audience_scope",
    "target_medium",
    "cta",
    "cta_action",
    "url",
}
ALLOWED_APP_REQUEST_KEYS = {
    "app_id",
    "app_action_id",
    "client_receipt_id",
    "approved_template_id",
    "input",
    "context_ref",
}
URL_PATTERN = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)

BLACKNET_NARRATIVE_INTENTS = {
    "conflict": "intercepted_conflict_warning",
    "incident": "intercepted_incident_alert",
    "radio": "intercepted_broadcast_fragment",
    "product": "intercepted_product_transmission",
    "fallback": "intercepted_world_signal",
}
SIGNAL_NARRATIVE_CONTRACT_VERSION = "signal-aware-v2"


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_text(value, limit=240):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[: max(0, int(limit or 0))]


def _safe_coordinate(value, minimum, maximum):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number < minimum or number > maximum:
        return None
    return round(number, 6)


def narrative_intent_for_signal(signal):
    """Return the code-owned voice contract for one bounded world signal."""
    signal = signal if isinstance(signal, dict) else {}
    identity = " ".join((
        _clean(signal.get("signal_type")),
        _clean(signal.get("fact_id")),
        _clean(signal.get("category")),
    )).casefold()
    if "conflict_target_alert" in identity or "bnf:conflicts:" in identity:
        return BLACKNET_NARRATIVE_INTENTS["conflict"]
    if "incident_hotspot" in identity or "bnf:incidents:" in identity:
        return BLACKNET_NARRATIVE_INTENTS["incident"]
    if "radio_promotion" in identity or "radio_channels_available" in identity or "bnf:radio:" in identity:
        return BLACKNET_NARRATIVE_INTENTS["radio"]
    if "googleplex_product_signal" in identity or "product_opportunity" in identity or "bnf:googleplex:" in identity:
        return BLACKNET_NARRATIVE_INTENTS["product"]
    return BLACKNET_NARRATIVE_INTENTS["fallback"]


def _digest_window(snapshot, minutes=15):
    generated_at = _clean((snapshot or {}).get("generated_at"))
    try:
        parsed = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    minute = (parsed.minute // max(1, int(minutes or 15))) * max(1, int(minutes or 15))
    return parsed.astimezone(timezone.utc).replace(
        minute=minute, second=0, microsecond=0
    ).isoformat()


def _contains_forbidden_request_data(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if _clean(key).lower() in FORBIDDEN_APP_REQUEST_KEYS:
                return True
            if _contains_forbidden_request_data(child):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_forbidden_request_data(child) for child in value)
    return bool(URL_PATTERN.search(str(value or "")))


class BlackNetNarrativeProducer:
    """Project deterministic BlackNet signals into one public LLM task.

    The producer accepts an already bounded signal snapshot. It never discovers
    users or reads profiles, and the deterministic feed remains useful when no
    consumer claims the resulting task.
    """

    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _single_signal_fact(signal):
        signal = signal if isinstance(signal, dict) else {}
        signal_id = _safe_text(signal.get("id"), 96)
        fact_id = _safe_text(signal.get("fact_id") or signal_id, 120)
        if not signal_id or not fact_id:
            return None, None
        metadata = signal.get("metadata") if isinstance(signal.get("metadata"), dict) else {}
        lat = _safe_coordinate(metadata.get("lat", signal.get("lat")), -90.0, 90.0)
        lng = _safe_coordinate(
            metadata.get("lng", metadata.get("lon", signal.get("lng", signal.get("lon")))),
            -180.0, 180.0,
        )
        fact_ref = f"blacknet_fact:{fact_id}"
        region_id = _safe_text(signal.get("region_id"), 96)
        if re.match(r"^world[-_:]", region_id, re.IGNORECASE):
            region_id = ""
        fact = {
            "fact_id": fact_ref,
            "truth_class": "canonical",
            "signal_id": signal_id,
            "signal_type": _safe_text(signal.get("signal_type"), 48),
            "category": _safe_text(signal.get("category"), 48),
            "region_id": region_id,
            "title": _safe_text(signal.get("title"), 96),
            "label": _safe_text(signal.get("label"), 64),
            "value": _safe_text(signal.get("value"), 48),
            "stat": _safe_text(signal.get("stat"), 120),
            "lat": lat,
            "lng": lng,
            "importance": _safe_int(signal.get("importance")),
            "observed_at": _safe_text(signal.get("observed_at"), 64),
            "valid_until": _safe_text(signal.get("valid_until"), 64),
        }
        action_name = _clean(signal.get("cta_action"))
        if action_name == "teleport_to_hotspot" and (lat is None or lng is None):
            action_name = "focus_map_target"
        action = None
        if action_name in BLACKNET_ALLOWED_ACTIONS and action_name != "none":
            action = {
                "cta_action": action_name,
                "fact_ref": fact_ref,
                "payload": {
                    "target_id": _safe_text(signal.get("cta_target_id"), 120),
                    "query": _safe_text(signal.get("cta_query"), 120),
                    "lat": lat,
                    "lng": lng,
                    "label": _safe_text(
                        metadata.get("location_label")
                        or metadata.get("target_label")
                        or signal.get("title"),
                        120,
                    ),
                },
            }
        return fact, action

    def enqueue_signal(self, snapshot, signal, *, target_medium="blacknet"):
        """Enqueue one backend-selected source; the model never selects a topic."""
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        target_medium = _clean(target_medium, "blacknet")
        if target_medium not in {"blacknet", "googleplex_news"}:
            return {"ok": False, "status": "rejected", "reason_code": "unsupported_target_medium", "task": None}
        if target_medium == "googleplex_news" and (
            signal.get("signal_type") == "googleplex_product_signal"
            or "googleplex_product_signal" in str(signal.get("fact_id") or "")
        ):
            return {"ok": True, "status": "ineligible", "reason_code": "product_slot_owned_by_catalog", "task": None}
        narrative_intent = narrative_intent_for_signal(signal)
        fact, fixed_action = self._single_signal_fact(signal)
        if not fact:
            return {"ok": True, "status": "empty", "task": None}
        if narrative_intent == BLACKNET_NARRATIVE_INTENTS["product"]:
            # BlackNet needs the product identity and canonical price/value,
            # not catalog heat/download counters. Do not send irrelevant data
            # to the model and then ask it to ignore it.
            fact["stat"] = ""
        source_version_payload = {
            key: fact.get(key) for key in (
                "fact_id", "signal_type", "category", "region_id", "title", "label",
                "value", "stat", "lat", "lng",
            )
        }
        source_version_payload["narrative_intent"] = narrative_intent
        source_version_payload["narrative_contract"] = SIGNAL_NARRATIVE_CONTRACT_VERSION
        source_version_payload["action"] = fixed_action or {}
        source_version = hashlib.sha1(json.dumps(
            source_version_payload, ensure_ascii=True, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")).hexdigest()[:16]
        presentation_slot = "gp-home-world-grid" if target_medium == "googleplex_news" else ""
        source_receipt_id = _hash_id(
            "editorial_source", target_medium, presentation_slot,
            fact["fact_id"], source_version,
        )
        variant = (
            "googleplex_world_dispatch"
            if target_medium == "googleplex_news"
            else "blacknet_signal_narration"
        )
        slot_state = (
            self.repository.get_narrative_slot_state(target_medium, presentation_slot)
            if presentation_slot else None
        )
        expected_slot_version = int((slot_state or {}).get("version") or 0)
        task = self.repository.enqueue_narrative_task(assign_ollama_task_policy({
            "schema_version": NARRATIVE_TASK_SCHEMA_VERSION,
            "source_scope": BLACKNET_SOURCE_SCOPE,
            "source_receipt_id": source_receipt_id,
            "processor": NARRATIVE_TASK_PROCESSOR,
            "target_medium": target_medium,
            "audience_scope": "public",
            "truth_class": "canonical",
            "truth_class_policy": "canonical",
            "facts": [fact],
            # Navigation is resolved deterministically after generation. It is
            # deliberately absent from model_input.
            "allowed_actions": [],
            "canon_version": SIGNAL_NARRATIVE_CONTRACT_VERSION,
            "world_state_version": _clean(
                snapshot.get("world_facts_version") or snapshot.get("version")
            ),
            "task_variant": variant,
            "narrative_intent": narrative_intent,
            "content_kind": "world_dispatch" if presentation_slot else "world_signal",
            "presentation_slot": presentation_slot,
            "selected_source_ref": fact["fact_id"],
            "selected_source_version": source_version,
            "expected_slot_version": expected_slot_version,
            "fixed_action": fixed_action or {},
            "priority": _safe_int(signal.get("importance")),
            "validation": {
                "ok": True,
                "producer": "deterministic_editorial_queue",
                "narrative_intent": narrative_intent,
                "selected_source_ref": fact["fact_id"],
                "selected_source_version": source_version,
                "presentation_slot": presentation_slot,
                "content_kind": "world_dispatch" if presentation_slot else "world_signal",
                "expected_slot_version": expected_slot_version,
                "fixed_action": fixed_action or {},
                "profile_full_read": 0,
                "profile_full_write": 0,
                "profile_bytes": 0,
            },
        }))
        return {
            "ok": True,
            "status": "deduplicated" if task.get("idempotent") else "created",
            "receipt_id": source_receipt_id,
            "task": task,
        }

    def enqueue_digest(self, snapshot, *, window_id=None, target_medium="blacknet"):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        target_medium = _clean(target_medium, "blacknet")
        if target_medium not in {"blacknet", "googleplex_news"}:
            return {"ok": False, "status": "rejected", "reason_code": "unsupported_target_medium", "task": None}
        signals = [
            item for item in (snapshot.get("signals") or [])
            if isinstance(item, dict) and item.get("signal_type") != "out_of_signal"
        ]
        # Googleplex owns its promotional product card deterministically from
        # the canonical catalog.  Product signals may still be narrated by
        # BlackNet, but must not create News tasks that could overwrite that
        # card (or consume the bounded fact budget).
        if target_medium == "googleplex_news":
            signals = [
                item for item in signals
                if (
                    item.get("signal_type") != "googleplex_product_signal"
                    and "googleplex_product_signal" not in str(item.get("fact_id") or "")
                )
            ]
        signals = signals[:20]
        if not signals:
            return {"ok": True, "status": "empty", "task": None}

        facts = []
        allowed_actions = []
        for signal in signals:
            signal_id = _safe_text(signal.get("id"), 96)
            fact_id = _safe_text(signal.get("fact_id") or signal_id, 120)
            if not signal_id or not fact_id:
                continue
            metadata = signal.get("metadata") if isinstance(signal.get("metadata"), dict) else {}
            lat = _safe_coordinate(
                metadata.get("lat", signal.get("lat")), -90.0, 90.0
            )
            lng = _safe_coordinate(
                metadata.get("lng", metadata.get("lon", signal.get("lng", signal.get("lon")))),
                -180.0, 180.0,
            )
            facts.append({
                "fact_id": f"blacknet_fact:{fact_id}",
                "truth_class": "canonical",
                "signal_id": signal_id,
                "signal_type": _safe_text(signal.get("signal_type"), 48),
                "category": _safe_text(signal.get("category"), 48),
                "region_id": _safe_text(signal.get("region_id"), 96),
                "title": _safe_text(signal.get("title"), 96),
                "label": _safe_text(signal.get("label"), 64),
                "value": _safe_text(signal.get("value"), 48),
                "stat": _safe_text(signal.get("stat"), 120),
                "lat": lat,
                "lng": lng,
                "importance": _safe_int(signal.get("importance")),
                "observed_at": _safe_text(signal.get("observed_at"), 64),
                "valid_until": _safe_text(signal.get("valid_until"), 64),
            })
            action = _clean(signal.get("cta_action"))
            # Dynamic teleport is legal only when its code-owned payload carries
            # canonical coordinates.  The model sees only cta_ref and can never
            # author or replace the destination.
            if action == "teleport_to_hotspot" and (lat is None or lng is None):
                action = "focus_map_target"
            if action in BLACKNET_ALLOWED_ACTIONS:
                allowed_actions.append({
                    "cta_action": action,
                    "fact_ref": f"blacknet_fact:{fact_id}",
                    "payload": {
                        "target_id": _safe_text(signal.get("cta_target_id"), 120),
                        "query": _safe_text(signal.get("cta_query"), 120),
                        "lat": lat,
                        "lng": lng,
                        "label": _safe_text(
                            metadata.get("location_label")
                            or metadata.get("target_label")
                            or signal.get("title"),
                            120,
                        ),
                    },
                })

        if not facts:
            return {"ok": True, "status": "empty", "task": None}
        world_version = _clean(
            snapshot.get("world_facts_version") or snapshot.get("version")
        )
        window_id = _clean(window_id) or _digest_window(snapshot)
        source_receipt_id = _hash_id(
            "blacknet_digest", window_id, world_version or "unversioned"
        )
        task = self.repository.enqueue_narrative_task(assign_ollama_task_policy({
            "schema_version": NARRATIVE_TASK_SCHEMA_VERSION,
            "source_scope": BLACKNET_SOURCE_SCOPE,
            "source_receipt_id": source_receipt_id,
            "processor": NARRATIVE_TASK_PROCESSOR,
            "target_medium": target_medium,
            "audience_scope": "public",
            "truth_class": "canonical",
            "truth_class_policy": "canonical",
            "facts": facts,
            "allowed_actions": allowed_actions[:20],
            "canon_version": "blacknet-world-narrative-v1",
            "world_state_version": world_version,
            "prompt_version": "unassigned",
            "output_schema_version": "unassigned",
            "model_policy_version": "unassigned",
            "task_variant": "world_digest",
            "priority": max(_safe_int(item.get("importance")) for item in signals),
            "validation": {
                "ok": True,
                "producer": "blacknet_world",
                "signal_count": len(facts),
                "window_id": window_id,
            },
        }))
        return {
            "ok": True,
            "status": "deduplicated" if task.get("idempotent") else "created",
            "receipt_id": source_receipt_id,
            "task": task,
        }


class GoogleplexLlmTaskIngress:
    """Validate an installed-app action and enqueue an owner-scoped task."""

    def __init__(self, repository, inventory_store):
        self.repository = repository
        self.inventory_store = inventory_store

    def submit(self, username, app_contract, request_payload):
        username = _clean(username)
        app_contract = app_contract if isinstance(app_contract, dict) else {}
        payload = request_payload if isinstance(request_payload, dict) else {}
        app_id = _clean(app_contract.get("id") or app_contract.get("app_id"))
        ingress = app_contract.get("llm_ingress")
        ingress = ingress if isinstance(ingress, dict) else {}
        if not username or not app_id or ingress.get("enabled") is not True:
            return self._rejected("app_ingress_not_enabled")
        if _clean(payload.get("app_id")) != app_id:
            return self._rejected("app_contract_mismatch")
        if not self.inventory_store.has_app(username, app_id):
            return self._rejected("app_not_installed")
        if _contains_forbidden_request_data(payload):
            return self._rejected("forbidden_request_field")
        if set(payload) - ALLOWED_APP_REQUEST_KEYS:
            return self._rejected("unknown_request_field")

        client_receipt_id = _safe_text(
            payload.get("client_receipt_id") or payload.get("app_action_id"), 128
        )
        template_id = _safe_text(payload.get("approved_template_id"), 80)
        if not client_receipt_id or not template_id:
            return self._rejected("missing_receipt_or_template")
        if not re.fullmatch(r"[A-Za-z0-9_.:\-]{8,128}", client_receipt_id):
            return self._rejected("invalid_client_receipt")

        templates = ingress.get("templates") if isinstance(ingress.get("templates"), list) else []
        template = next(
            (
                item for item in templates
                if isinstance(item, dict) and _clean(item.get("id")) == template_id
            ),
            None,
        )
        if not template:
            return self._rejected("unknown_template")
        medium = _clean(template.get("target_medium"), "cyberner")
        if medium not in APP_TARGET_MEDIA:
            return self._rejected("template_medium_not_allowed")

        raw_inputs = payload.get("input") if isinstance(payload.get("input"), dict) else {}
        field_contracts = (
            template.get("input_fields")
            if isinstance(template.get("input_fields"), dict)
            else {}
        )
        if set(raw_inputs) - set(field_contracts):
            return self._rejected("unknown_input_field")
        safe_inputs = {}
        for field_name, contract in field_contracts.items():
            contract = contract if isinstance(contract, dict) else {}
            max_length = min(500, _safe_int(contract.get("max_length"), 160))
            raw_value = str(raw_inputs.get(field_name) or "").strip()
            if len(raw_value) > max_length:
                return self._rejected("input_too_long")
            value = _safe_text(raw_value, max_length)
            if contract.get("required") and not value:
                return self._rejected("required_input_missing")
            if value:
                if URL_PATTERN.search(value):
                    return self._rejected("external_url_not_allowed")
                safe_inputs[_safe_text(field_name, 48)] = value

        receipt_id = _hash_id(
            "llm_app_receipt", username, app_id, client_receipt_id
        )
        fact = {
            "fact_id": f"googleplex_request:{receipt_id}",
            "truth_class": "interpretation",
            "template_id": template_id,
            "request_fields": safe_inputs,
            "public_text": _safe_text(safe_inputs.get("topic"), 120),
            "context_ref": _safe_text(payload.get("context_ref"), 120),
        }
        allowed_actions = []
        for action in template.get("allowed_actions") or []:
            if not isinstance(action, dict):
                continue
            action_name = _clean(action.get("cta_action"))
            if action_name in APP_ALLOWED_ACTIONS:
                action_payload = (
                    action.get("payload")
                    if isinstance(action.get("payload"), dict)
                    else {}
                )
                allowed_actions.append({
                    "cta_action": action_name,
                    "payload": {
                        "channel": _safe_text(
                            action_payload.get("channel"), 48
                        )
                    },
                })
        task_record = assign_ollama_task_policy({
            "schema_version": NARRATIVE_TASK_SCHEMA_VERSION,
            "source_scope": GOOGLEPLEX_SOURCE_SCOPE,
            "source_receipt_id": receipt_id,
            "source_app_id": app_id,
            "processor": NARRATIVE_TASK_PROCESSOR,
            "target_medium": medium,
            "audience_scope": "owner",
            "audience_owner": username,
            "truth_class": "interpretation",
            "truth_class_policy": "owner_requested_interpretation",
            "facts": [fact],
            "allowed_actions": allowed_actions,
            "canon_version": _clean(ingress.get("canon_version"), "googleplex-llm-ingress-v1"),
            "prompt_version": _clean(template.get("prompt_version"), "unassigned"),
            "output_schema_version": _clean(template.get("output_schema_version"), "unassigned"),
            "model_policy_version": _clean(template.get("model_policy_version"), "unassigned"),
            "task_variant": template_id,
            "priority": _safe_int(template.get("priority")),
            "validation": {
                "ok": True,
                "producer": "googleplex_app",
                "template_id": template_id,
            },
        })
        rate_limit = ingress.get("rate_limit")
        rate_limit = rate_limit if isinstance(rate_limit, dict) else {}
        max_tasks = max(1, min(_safe_int(rate_limit.get("max_tasks"), 6), 100))
        window_seconds = max(
            60,
            min(_safe_int(rate_limit.get("window_seconds"), 3600), 86400),
        )
        now = datetime.fromisoformat(
            self.repository.now().replace("Z", "+00:00")
        )
        created_after = (now - timedelta(seconds=window_seconds)).isoformat()
        with self.repository.transaction():
            if not self.inventory_store.has_app(
                username,
                app_id,
                conn=self.repository._transaction_conn,
            ):
                return self._rejected("app_entitlement_changed")
            existing = self.repository.list_narrative_outbox(
                source_scope=GOOGLEPLEX_SOURCE_SCOPE,
                source_receipt_id=receipt_id,
                limit=2,
            )
            existing = next((
                item for item in existing
                if item.get("audience_scope") == "owner"
                and item.get("audience_owner") == username
                and item.get("source_app_id") == app_id
            ), None)
            if existing:
                task = existing
                task["idempotent"] = True
            else:
                recent = self.repository.count_recent_narrative_tasks(
                    source_scope=GOOGLEPLEX_SOURCE_SCOPE,
                    source_app_id=app_id,
                    audience_owner=username,
                    created_after=created_after,
                )
                if recent >= max_tasks:
                    return self._rejected("rate_limit_exceeded")
                task = self.repository.enqueue_narrative_task(task_record)
        return {
            "ok": True,
            "accepted": True,
            "status": "accepted",
            "enqueue_result": "deduplicated" if task.get("idempotent") else "created",
            "receipt_id": receipt_id,
            "task_id": task.get("outbox_id"),
            "task_status": task.get("status"),
        }

    @staticmethod
    def _rejected(reason):
        return {
            "ok": False,
            "accepted": False,
            "status": "rejected",
            "reason_code": _clean(reason, "request_rejected"),
        }
