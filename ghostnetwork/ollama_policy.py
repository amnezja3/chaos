from __future__ import annotations

import copy
import hashlib
import json
import math
import re

from .llm.policies.chaos_local_narrator_v1 import (
    MODEL_DIGEST,
    MODEL_NAME,
    MODEL_POLICY_VERSION,
)
from .llm.registry import (
    OUTPUT_SCHEMA_VERSION,
    load_output_schema,
    load_prompt_layers,
    registered_ollama_policies,
    resolve_ollama_task_policy,
    verify_prompt_registry,
)


MAX_TASK_PACKAGE_BYTES = 2400
ESTIMATED_TOKEN_CHARS = 3.5
MAX_MODEL_CONTENT_BYTES = 16 * 1024
MAX_HTTP_RESPONSE_BYTES = 64 * 1024
ALLOWED_TONES = (
    "info",
    "warning",
    "critical",
    "victory",
    "mystery",
    "system",
    "clan",
)
URL_PATTERN = re.compile(r"(?:https?://|www\.|ftp://)", re.IGNORECASE)
COMPACT_FACT_FIELDS = (
    ("fact_type", "type", 48),
    ("signal_type", "type", 48),
    ("status", "status", 48),
    ("previous_status", "previous_status", 48),
    ("conflict_state", "conflict_state", 48),
    ("previous_conflict_state", "previous_conflict_state", 48),
    ("title", "title", 72),
    ("headline", "headline", 72),
    ("label", "label", 48),
    ("value", "value", 48),
    ("stat", "stat", 72),
    ("public_text", "text", 96),
    ("category", "category", 40),
    ("importance", "importance", 0),
    ("observed_at", "observed_at", 40),
    ("valid_until", "valid_until", 40),
    ("part_count", "part_count", 0),
    ("connection_count", "connection_count", 0),
    ("machine_count", "machine_count", 0),
    ("restart_required", "restart_required", 0),
    ("confirmation_status", "confirmation_status", 40),
    ("outcome", "outcome", 40),
)
CANONICAL_FACT_REF_FIELDS = (
    ("signal_id", "signal_id", 96),
    ("event_id", "event_id", 96),
    ("cycle_id", "cycle_id", 96),
    ("public_entity_id", "public_entity_id", 120),
    ("region_id", "region_id", 96),
    ("lock_snapshot_id", "lock_snapshot_id", 96),
    ("lock_snapshot_checksum", "lock_snapshot_checksum", 96),
)


def _compact_value(value, limit):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)[:limit]


def _encoded_package(model_input):
    return json.dumps(
        model_input,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _try_add_fact_column(model_input, source_facts, facts, fact_columns, field_spec):
    source_field, column, value_limit = field_spec
    if column in fact_columns:
        return False
    values = [_compact_value(item.get(source_field), value_limit) for item in source_facts]
    if not any(value is not None for value in values):
        return False
    fact_columns.append(column)
    for row, value in zip(facts, values):
        row.append(value)
    if len(_encoded_package(model_input).encode("utf-8")) <= MAX_TASK_PACKAGE_BYTES:
        return True
    fact_columns.pop()
    for row in facts:
        row.pop()
    return False


def assign_ollama_task_policy(task):
    task = dict(task or {})
    policy = resolve_ollama_task_policy(
        task.get("source_scope"),
        task.get("task_variant"),
        task.get("target_medium") or task.get("medium"),
    )
    if policy:
        task.update({
            "prompt_version": policy.prompt_version,
            "output_schema_version": policy.output_schema_version,
            "model_policy_version": policy.model_policy_version,
        })
    return task


def build_ollama_task_package(task, policy=None):
    task = task if isinstance(task, dict) else {}
    policy = policy or resolve_ollama_task_policy(
        task.get("source_scope"),
        task.get("task_variant"),
        task.get("target_medium") or task.get("medium"),
    )
    if not policy:
        raise ValueError("ollama_task_policy_not_registered")
    if any(
        str(task.get(field) or "").strip() != expected
        for field, expected in (
            ("prompt_version", policy.prompt_version),
            ("output_schema_version", policy.output_schema_version),
            ("model_policy_version", policy.model_policy_version),
        )
    ):
        raise ValueError("ollama_task_policy_version_mismatch")

    source_facts = []
    facts = []
    fact_refs = set()
    for item in (task.get("facts") or []):
        if not isinstance(item, dict):
            continue
        fact_id = str(item.get("fact_id") or "").strip()
        if not fact_id or fact_id in fact_refs:
            continue
        fact_refs.add(fact_id)
        source_facts.append(item)
        facts.append([fact_id])
    if not facts:
        raise ValueError("ollama_task_has_no_facts")

    cta_map = {}
    ctas = []
    for index, action in enumerate((task.get("allowed_actions") or [])[:32], start=1):
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("cta_action") or "").strip()[:64]
        if not action_name:
            continue
        ref = f"c{index:02d}"
        cta_map[ref] = copy.deepcopy(action)
        ctas.append([ref, action_name])

    fact_columns = ["fact_ref"]
    source = {
        "scope": policy.source_scope,
        "task": str(task.get("outbox_id") or task.get("task_id") or "")[:128],
        "event": str(task.get("source_event_id") or "")[:128],
        "receipt": str(task.get("source_receipt_id") or "")[:128],
    }
    versions = {
        "prompt": policy.prompt_version,
        "output_schema": policy.output_schema_version,
        "model_policy": policy.model_policy_version,
    }
    for key, field in (
        ("canon", "canon_version"),
        ("ghostsystem", "ghostsystem_version"),
        ("world", "world_state_version"),
    ):
        value = str(task.get(field) or "")[:96]
        if value:
            versions[key] = value
    audience = {
        "scope": str(task.get("audience_scope") or "").strip(),
        "clan": str(task.get("audience_clan") or "")[:96],
        "owner": str(task.get("audience_owner") or "")[:96],
    }

    model_input = {
        "source": source,
        "versions": versions,
        "medium": policy.target_medium,
        "audience": {
            **audience,
        },
        "truth": str(task.get("truth_class_policy") or "").strip(),
        "editorial": str(task.get("editorial_profile") or "")[:96],
        "context": str(task.get("narrative_context") or "")[:256],
        "fact_columns": fact_columns,
        "facts": facts,
        "cta_columns": ["cta_ref", "action"],
        "ctas": ctas,
        "limits": {"title": 96, "body": 480, "refs": 16},
    }

    mandatory_bytes = len(_encoded_package(model_input).encode("utf-8"))
    if mandatory_bytes > MAX_TASK_PACKAGE_BYTES:
        raise ValueError("ollama_task_mandatory_skeleton_too_large")

    # Optional data is admitted as complete columns: every fact gets the field
    # or no fact does. Canonical reference columns have priority, but they are
    # still budgeted so they cannot crowd mandatory fact/source identity out.
    for field_spec in CANONICAL_FACT_REF_FIELDS:
        _try_add_fact_column(model_input, source_facts, facts, fact_columns, field_spec)
    for field_spec in COMPACT_FACT_FIELDS:
        _try_add_fact_column(model_input, source_facts, facts, fact_columns, field_spec)

    encoded = _encoded_package(model_input)
    input_bytes = len(encoded.encode("utf-8"))
    if input_bytes > MAX_TASK_PACKAGE_BYTES:
        raise ValueError("ollama_task_package_too_large")
    system_prompt, domain_prompt = load_prompt_layers(policy)
    return {
        "policy": policy,
        "messages": [
            {"role": "system", "content": system_prompt + "\n\n" + domain_prompt},
            {"role": "user", "content": encoded},
        ],
        "format": load_output_schema(policy.output_schema_version),
        "fact_refs": frozenset(fact_refs),
        "cta_map": cta_map,
        "request_hash": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "input_bytes": input_bytes,
        "estimated_input_tokens": int(math.ceil(len(encoded) / ESTIMATED_TOKEN_CHARS)),
        "fact_count": len(facts),
    }


def parse_and_validate_ollama_content(content, task_package):
    raw = content if isinstance(content, str) else ""
    if not raw.strip():
        return {"status": "rejected", "errors": ["empty_content"], "output": None}
    if len(raw.encode("utf-8")) > MAX_MODEL_CONTENT_BYTES:
        return {"status": "rejected", "errors": ["content_too_large"], "output": None}
    try:
        output = json.loads(raw)
    except (TypeError, ValueError):
        return {"status": "invalid_json", "errors": ["invalid_json"], "output": None}
    if not isinstance(output, dict):
        return {"status": "rejected", "errors": ["output_not_object"], "output": None}

    errors = []
    security_errors = []
    expected_keys = {"title", "body", "tone", "fact_refs", "cta_ref"}
    if set(output) != expected_keys:
        errors.append("schema_fields_mismatch")
    title = output.get("title")
    body = output.get("body")
    tone = output.get("tone")
    refs = output.get("fact_refs")
    cta_ref = output.get("cta_ref")
    if not isinstance(title, str) or not title.strip() or len(title) > 96:
        errors.append("invalid_title")
    if not isinstance(body, str) or not body.strip() or len(body) > 800:
        errors.append("invalid_body")
    if tone not in ALLOWED_TONES:
        errors.append("invalid_tone")
    if (
        not isinstance(refs, list)
        or not refs
        or len(refs) > 16
        or any(not isinstance(item, str) or not item or len(item) > 128 for item in refs)
        or len(set(refs)) != len(refs)
    ):
        errors.append("invalid_fact_refs")
    elif not set(refs).issubset(set(task_package.get("fact_refs") or [])):
        security_errors.append("unknown_fact_ref")
    if cta_ref is not None:
        if not isinstance(cta_ref, str) or cta_ref not in (task_package.get("cta_map") or {}):
            security_errors.append("unknown_cta_ref")
    if isinstance(title, str) and URL_PATTERN.search(title):
        security_errors.append("external_url")
    if isinstance(body, str) and URL_PATTERN.search(body):
        security_errors.append("external_url")

    all_errors = sorted(set(errors + security_errors))
    status = "quarantined" if security_errors else ("rejected" if errors else "accepted")
    if all_errors:
        return {"status": status, "errors": all_errors, "output": output}
    return {
        "status": "accepted",
        "errors": [],
        "output": {
            "title": title.strip(),
            "body": body.strip(),
            "tone": tone,
            "fact_refs": list(refs),
            "cta_ref": cta_ref,
        },
        "resolved_cta": copy.deepcopy((task_package.get("cta_map") or {}).get(cta_ref)),
    }
