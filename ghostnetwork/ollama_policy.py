from __future__ import annotations

import copy
from difflib import SequenceMatcher
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
    GHOSTNETWORK_EVENT_PROMPT_VERSION,
    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
    GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
    OUTPUT_SCHEMA_VERSION,
    load_output_schema,
    load_prompt_layers,
    registered_ollama_policies,
    resolve_ollama_task_policy,
    verify_prompt_registry,
)
from .llm.semantic_input import (
    SEMANTIC_INPUT_CONTRACT_VERSION,
    model_visible_semantic_fact,
    semantic_audit_projection,
)


MAX_TASK_PACKAGE_BYTES = 2400
ESTIMATED_TOKEN_CHARS = 3.5
MAX_MODEL_CONTENT_BYTES = 16 * 1024
MAX_HTTP_RESPONSE_BYTES = 64 * 1024
GENERATION_OUTPUT_LIMITS = {
    "googleplex_news": {"title": 48, "body": 120, "refs": 1},
}
GOOGLEPLEX_ASSET_REF_BY_STATE = {
    "neutral": "gp_scene_world_neutral_01",
    "danger": "gp_scene_world_danger_01",
    "victory": "gp_scene_world_victory_01",
    "defence": "gp_scene_world_defence_01",
}
ALLOWED_TONES = (
    "info",
    "warning",
    "critical",
    "victory",
    "mystery",
    "system",
    "clan",
)
SIGNAL_NARRATIVE_INTENTS = frozenset({
    "intercepted_conflict_warning",
    "intercepted_incident_alert",
    "intercepted_broadcast_fragment",
    "intercepted_product_transmission",
    "intercepted_world_signal",
})
EDITORIAL_NARRATIVE_INTENTS = frozenset({
    "product_benefit_promo",
    "capability_invitation",
})
GHOSTNETWORK_NARRATIVE_INTENTS = frozenset({
    "ghost_part_discovery",
    "ghost_part_containment",
    "ghost_part_activation",
    "ghost_part_conflict",
    "ghost_part_recovery",
    "ghost_machine_progress",
    "ghost_machine_state",
    "ghost_cycle_state",
    "ghost_signal_transmission",
    "ghost_system_transition",
})
GHOSTNETWORK_V2_PROMPT_VERSIONS = frozenset({
    GHOSTNETWORK_EVENT_PROMPT_VERSION,
    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
    GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
    "ghostnetwork-event-prompt-v3",
    "ghostnetwork-googleplex-prompt-v3",
    "ghostsignal-prompt-v3",
    "ghostnetwork-event-prompt-v4",
    "ghostnetwork-googleplex-prompt-v4",
    "ghostsignal-prompt-v4",
    "ghostnetwork-event-prompt-v5",
    "ghostnetwork-googleplex-prompt-v5",
    "ghostsignal-prompt-v5",
    "ghostnetwork-event-prompt-v6",
    "ghostnetwork-googleplex-prompt-v6",
    "ghostsignal-prompt-v6",
    "ghostnetwork-event-prompt-v7",
    "ghostnetwork-googleplex-prompt-v7",
    "ghostsignal-prompt-v7",
    "ghostnetwork-event-prompt-v8",
    "ghostnetwork-googleplex-prompt-v8",
    "ghostsignal-prompt-v8",
    "ghostnetwork-event-prompt-v2",
    "ghostnetwork-googleplex-prompt-v2",
    "ghostsignal-prompt-v2",
})
GHOSTNETWORK_MINIMAL_PROMPT_VERSIONS = frozenset({
    GHOSTNETWORK_EVENT_PROMPT_VERSION,
    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
    GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
    "ghostnetwork-event-prompt-v3",
    "ghostnetwork-googleplex-prompt-v3",
    "ghostsignal-prompt-v3",
    "ghostnetwork-event-prompt-v4",
    "ghostnetwork-googleplex-prompt-v4",
    "ghostsignal-prompt-v4",
    "ghostnetwork-event-prompt-v5",
    "ghostnetwork-googleplex-prompt-v5",
    "ghostsignal-prompt-v5",
    "ghostnetwork-event-prompt-v6",
    "ghostnetwork-googleplex-prompt-v6",
    "ghostsignal-prompt-v6",
    "ghostnetwork-event-prompt-v7",
    "ghostnetwork-googleplex-prompt-v7",
    "ghostsignal-prompt-v7",
    "ghostnetwork-event-prompt-v8",
    "ghostnetwork-googleplex-prompt-v8",
    "ghostsignal-prompt-v8",
})
GHOSTNETWORK_TONE_HINTS = {
    "low": "info",
    "normal": "info",
    "high": "warning",
    "critical": "critical",
}
GHOSTNETWORK_OUTPUT_LIMITS = {
    "blacknet": {"title": 72, "body": 420, "refs": 4},
    "cyberner": {"title": 72, "body": 420, "refs": 4},
    "radio": {"title": 72, "body": 520, "refs": 4},
    "googleplex_news": {"title": 48, "body": 120, "refs": 1},
}
URL_PATTERN = re.compile(r"(?:https?://|www\.|ftp://)", re.IGNORECASE)
INTERNAL_IDENTIFIER_PATTERN = re.compile(
    r"(?:\b(?:narrative|receipt|candidate|task|event|signal|cycle)_[a-z0-9_:-]{6,}\b|"
    r"\b(?:ghostnetwork|ghostcycle|ghostpart|ghostmachine)_[a-z0-9_.:-]{3,}\b|"
    r"\b(?:ghost_fact|fact):[a-z0-9_.:-]{4,}\b|\b[0-9a-f]{10,}\b)",
    re.IGNORECASE,
)
OPAQUE_HEX_PATTERN = re.compile(r"\b[0-9a-f]{10,}\b", re.IGNORECASE)
OPAQUE_HEX_FRAGMENT_PATTERN = re.compile(r"\b[0-9a-f]{6,}\b", re.IGNORECASE)
TRAILING_HEX_FRAGMENT_PATTERN = re.compile(r"\b[0-9a-f]{3,9}$", re.IGNORECASE)
CANONICAL_POI_NAME_PATTERN = re.compile(r"\bPOI-[A-Z0-9][A-Z0-9_-]{1,80}\b", re.IGNORECASE)
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
    ("observed_at", "observed_at", 40),
    ("valid_until", "valid_until", 40),
    ("part_count", "part_count", 0),
    ("connection_count", "connection_count", 0),
    ("machine_count", "machine_count", 0),
    ("event_count", "event_count", 0),
    ("restart_required", "restart_required", 0),
    ("confirmation_status", "confirmation_status", 40),
    ("outcome", "outcome", 40),
)
GOOGLEPLEX_PRESENTATION_FACT_FIELDS = (
    ("product_name", "product_name", 72),
    ("description", "description", 180),
    ("public_text", "text", 160),
    ("title", "title", 72),
    ("lat", "lat", 0),
    ("lng", "lng", 0),
    ("headline", "headline", 72),
    ("label", "label", 48),
    ("stat", "stat", 72),
    ("category", "category", 40),
    ("status", "status", 48),
    ("conflict_state", "conflict_state", 48),
    ("outcome", "outcome", 40),
    ("observed_at", "observed_at", 40),
    ("valid_until", "valid_until", 40),
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


def presentation_safety_errors(title, body):
    errors = []
    for value in (title, body):
        if isinstance(value, str) and URL_PATTERN.search(value):
            errors.append("external_url")
        inspected = CANONICAL_POI_NAME_PATTERN.sub("", value) if isinstance(value, str) else value
        if isinstance(inspected, str) and INTERNAL_IDENTIFIER_PATTERN.search(inspected):
            errors.append("internal_identifier_leak")
    return sorted(set(errors))


def source_metadata_leak_errors(title, body, source_facts):
    """Reject raw coordinates and runtime calendar years from presentation copy."""
    text = f"{title or ''}\n{body or ''}"
    errors = []
    coordinate_tokens = set()
    source_years = set()
    for fact in source_facts or ():
        if not isinstance(fact, dict):
            continue
        for field in ("lat", "lng", "lon"):
            try:
                number = float(fact.get(field))
            except (TypeError, ValueError):
                continue
            if not math.isfinite(number):
                continue
            for precision in (4, 5, 6):
                coordinate_tokens.add(f"{number:.{precision}f}".rstrip("0").rstrip("."))
        for field in ("observed_at", "valid_until", "created_at", "updated_at"):
            source_years.update(re.findall(r"\b20\d{2}\b", str(fact.get(field) or "")))
    if any(
        token and re.search(rf"(?<!\d){re.escape(token)}(?!\d)", text)
        for token in coordinate_tokens
    ):
        errors.append("raw_coordinate_leak")
    if any(year != "2108" and re.search(rf"\b{re.escape(year)}\b", text) for year in source_years):
        errors.append("source_calendar_year_leak")
    if re.search(r"\bworld[-_:]", text, re.IGNORECASE):
        errors.append("technical_region_prefix_leak")
    return errors


def unknown_canonical_poi_names(title, body, source_facts):
    requested = {
        item.casefold()
        for value in (title, body)
        for item in CANONICAL_POI_NAME_PATTERN.findall(str(value or ""))
    }
    if not requested:
        return set()
    canonical_source = json.dumps(
        list(source_facts or ()), ensure_ascii=False, sort_keys=True
    ).casefold()
    return {item for item in requested if item not in canonical_source}


def normalize_canonical_identifier_leaks(title, body, source_facts):
    """Replace only source-backed opaque hashes with a safe canonical label."""
    canonical_tokens = []
    safe_text = []
    for fact in source_facts or ():
        if not isinstance(fact, dict):
            continue
        safe_label = ""
        for field in ("title", "label", "stat"):
            candidate = re.sub(r"\s+", " ", str(fact.get(field) or "")).strip()
            if candidate and not presentation_safety_errors(candidate, ""):
                safe_label = candidate[:72]
                break
        if not safe_label:
            continue
        presentation_values = " ".join(
            str(fact.get(field) or "") for field in ("title", "label", "stat")
        ).casefold()
        safe_text.append(presentation_values)
        canonical_values = " ".join(
            str(value) for key, value in fact.items()
            if key not in {"title", "label", "stat", "public_text"}
        )
        for token in OPAQUE_HEX_PATTERN.findall(canonical_values):
            canonical_tokens.append((token.casefold(), safe_label))

    normalized = []
    applied = False
    for value in (title, body):
        text = str(value or "")

        def replace(match):
            nonlocal applied
            fragment = match.group(0).casefold()
            if any(fragment in value for value in safe_text):
                return match.group(0)
            replacement = next((
                label for token, label in canonical_tokens
                if token.startswith(fragment) or fragment in token
            ), "")
            if not replacement:
                return match.group(0)
            applied = True
            return replacement

        text = OPAQUE_HEX_FRAGMENT_PATTERN.sub(replace, text)

        # Constrained generation can stop in the middle of an opaque source
        # identifier (for example ``02b`` from ``02b4180b63e5``).  Such a
        # fragment is too short for the generic leak detector, so resolve it
        # only when it is the terminal prefix of a known source token.  This
        # avoids treating arbitrary short words or canonical presentation
        # codes as identifiers.
        trailing = TRAILING_HEX_FRAGMENT_PATTERN.search(text)
        if trailing:
            fragment = trailing.group(0).casefold()
            replacement = next((
                label for token, label in canonical_tokens
                if token.startswith(fragment)
            ), "")
            if replacement:
                applied = True
                text = text[:trailing.start()] + replacement

        normalized.append(text)
    return normalized[0], normalized[1], applied


def bound_presentation_text(value, limit):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    limit = max(1, int(limit or 1))
    if len(text) <= limit:
        return text, False
    if limit <= 3:
        return text[:limit], True
    prefix = text[:limit - 3].rstrip()
    if " " in prefix:
        prefix = prefix.rsplit(" ", 1)[0].rstrip()
    return prefix + "...", True


def owner_analysis_echoes_input(title, body, source_facts):
    source_texts = []
    for fact in source_facts or ():
        if not isinstance(fact, dict):
            continue
        text = fact.get("public_text")
        if text:
            source_texts.append(str(text))
        request_fields = fact.get("request_fields")
        if isinstance(request_fields, dict) and request_fields.get("topic"):
            source_texts.append(str(request_fields["topic"]))

    def normalized(value):
        folded = str(value or "").casefold().translate(str.maketrans({
            "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
            "ó": "o", "ś": "s", "ź": "z", "ż": "z",
        }))
        return re.sub(r"[^\w]+", " ", folded).strip()

    normalized_sources = {normalized(item) for item in source_texts if normalized(item)}
    normalized_outputs = tuple(
        item for item in (normalized(title), normalized(body)) if item
    )
    if any(output in normalized_sources for output in normalized_outputs):
        return True
    # Owner analysis must transform the topic into guidance. Wrapping the input
    # in a reporting phrase ("Gracz poprosil o...") is still an echo.
    if any(
        len(source.split()) >= 2 and source in output
        for source in normalized_sources
        for output in normalized_outputs
    ):
        return True
    # Reordering the topic words in a short title is still an echo. This
    # catches outputs such as "Stracony Krakow" for "Krakow stracony" while
    # allowing a single canonical place or object name to remain usable.
    if any(
        2 <= len(output.split()) <= 6
        and set(output.split()).issubset(set(source.split()))
        for source in normalized_sources
        if len(source.split()) >= 2
        for output in normalized_outputs
    ):
        return True
    reporting_prefixes = (
        "gracz poprosil", "gracz prosi", "uzytkownik poprosil",
        "uzytkownik chce", "pytanie dotyczy", "tematem jest",
    )
    return any(
        any(prefix in output for prefix in reporting_prefixes)
        for output in normalized_outputs
    )


def product_promo_echoes_description(body, source_facts):
    """Reject catalog-description copies while preserving canonical product data."""
    folded_body = re.sub(r"[^\w]+", " ", str(body or "").casefold()).strip()
    if not folded_body:
        return False
    for fact in source_facts or ():
        if not isinstance(fact, dict):
            continue
        description = re.sub(
            r"[^\w]+", " ", str(fact.get("description") or "").casefold()
        ).strip()
        if not description:
            continue
        if folded_body == description:
            return True
        shorter, longer = sorted((folded_body, description), key=len)
        if len(shorter.split()) >= 5 and shorter in longer and len(shorter) / max(1, len(longer)) >= 0.8:
            return True
        if min(len(folded_body.split()), len(description.split())) >= 5 and SequenceMatcher(
            None, folded_body, description
        ).ratio() >= 0.88:
            return True
    return False


def _normalized_narrative_text(value):
    folded = str(value or "").casefold().translate(str.maketrans({
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n",
        "ó": "o", "ś": "s", "ź": "z", "ż": "z",
    }))
    return re.sub(r"[^\w]+", " ", folded).strip()


_PRODUCT_FILLER_PREFIX_RE = re.compile(
    r"^\s*(?:(?:w\s+roku\s+2108|w\s+globalnym\s+zasi(?:e|ę)gu)\s*,?\s*)+",
    re.IGNORECASE,
)


def normalize_product_filler_prefix(body, narrative_intent=""):
    """Remove only known empty lead-ins before validating product copy."""
    if narrative_intent != "intercepted_product_transmission" or not isinstance(body, str):
        return body, False
    cleaned = _PRODUCT_FILLER_PREFIX_RE.sub("", body).lstrip(" ,;:-")
    if cleaned == body or not cleaned:
        return body, False
    return cleaned[:1].upper() + cleaned[1:], True


def signal_narrative_quality_errors(title, body, source_facts, narrative_intent=""):
    """Fail closed on database-like source copies and known empty fillers."""
    combined = _normalized_narrative_text(f"{title or ''} {body or ''}")
    filler_phrases = (
        "w roku 2108",
        "w rejonie celu",
        "w globalnym zasiegu",
        "odnotowano produktowa szanse",
    )
    errors = []
    if any(phrase in combined for phrase in filler_phrases):
        errors.append("narrative_filler_phrase")
    if narrative_intent == "intercepted_product_transmission" and re.search(
        r"\b(?:temp|pobran\w*)\b", combined
    ):
        errors.append("product_transmission_metric_leak")

    normalized_body = _normalized_narrative_text(body)
    source_values = []
    for fact in source_facts or ():
        if not isinstance(fact, dict):
            continue
        source_values.extend(
            _normalized_narrative_text(fact.get(field))
            for field in ("title", "label", "value", "stat", "description", "public_text")
        )
    source_values = [value for value in source_values if value]
    exact_or_near_echo = normalized_body and any(
        normalized_body == source
        or (
            min(len(normalized_body.split()), len(source.split())) >= 5
            and SequenceMatcher(None, normalized_body, source).ratio() >= 0.9
        )
        for source in source_values
    )
    source_tokens = {
        token for source in source_values for token in source.split() if token
    }
    body_tokens = normalized_body.split()
    composite_echo = (
        len(body_tokens) >= 2
        and bool(source_tokens)
        and set(body_tokens).issubset(source_tokens)
    )
    if exact_or_near_echo or composite_echo:
        errors.append("signal_source_echo")
    return errors


def googleplex_allowed_asset_refs(source_facts):
    """Derive asset state from canonical fields, never from generated tone/text."""
    values = " ".join(
        str(fact.get(field) or "").casefold()
        for fact in source_facts or () if isinstance(fact, dict)
        for field in ("signal_type", "status", "conflict_state", "outcome")
    )
    if any(token in values for token in ("resolved", "victory", "won", "success")):
        state = "victory"
    elif any(token in values for token in ("defended", "contained", "protected", "stabilized")):
        state = "defence"
    elif any(token in values for token in ("conflict", "incident", "danger", "alert", "contested")):
        state = "danger"
    else:
        state = "neutral"
    return (GOOGLEPLEX_ASSET_REF_BY_STATE[state], "gp_fallback_network")


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


def _try_add_cta_row(model_input, cta_map, ref, action_name, action):
    created_structure = "ctas" not in model_input
    action_fact_ref = str(action.get("fact_ref") or "")[:128]
    if created_structure:
        model_input["cta_columns"] = ["cta_ref", "action"] + (
            ["fact_ref"] if action_fact_ref else []
        )
        model_input["ctas"] = []
    row = [ref, action_name]
    if "fact_ref" in model_input["cta_columns"]:
        row.append(action_fact_ref)
    model_input["ctas"].append(row)
    if len(_encoded_package(model_input).encode("utf-8")) <= MAX_TASK_PACKAGE_BYTES:
        cta_map[ref] = copy.deepcopy(action)
        return True
    model_input["ctas"].pop()
    if created_structure:
        model_input.pop("ctas", None)
        model_input.pop("cta_columns", None)
    return False


def _try_add_top_level_field(model_input, field, value):
    model_input[field] = value
    if len(_encoded_package(model_input).encode("utf-8")) <= MAX_TASK_PACKAGE_BYTES:
        return True
    model_input.pop(field, None)
    return False


def _is_ghostnetwork_v2_policy(policy):
    return bool(
        policy
        and policy.source_scope == "ghostnetwork"
        and policy.prompt_version in GHOSTNETWORK_V2_PROMPT_VERSIONS
    )


def _is_ghostnetwork_minimal_policy(policy):
    return bool(
        policy
        and policy.source_scope == "ghostnetwork"
        and policy.prompt_version in GHOSTNETWORK_MINIMAL_PROMPT_VERSIONS
    )


def _generation_limits_for_policy(policy):
    if _is_ghostnetwork_v2_policy(policy):
        if policy.prompt_version == GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION:
            return {"title": 36, "body": 120, "refs": 1}
        if (
            policy.prompt_version in {
                GHOSTNETWORK_EVENT_PROMPT_VERSION,
                GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
            }
            and policy.target_medium == "blacknet"
        ):
            return {"title": 48, "body": 220, "refs": 4}
        return GHOSTNETWORK_OUTPUT_LIMITS.get(policy.target_medium)
    return GENERATION_OUTPUT_LIMITS.get(policy.target_medium)


def _semantic_entity_label(semantic, kind):
    for entity in semantic.get("entities") or ():
        if isinstance(entity, dict) and str(entity.get("kind") or "").strip() == kind:
            return str(entity.get("label") or "").strip()
    return ""


def _part_discovered_model_fact(
    visible_fact, audience_scope, *, expose_required_phrase=False,
):
    """Collapse ambiguous entity rows into one backend-authored canonical sentence."""
    statement = str(visible_fact.get("statement") or "").strip()
    target = _semantic_entity_label(visible_fact, "target")
    part = _semantic_entity_label(visible_fact, "part")
    location = visible_fact.get("location") if isinstance(visible_fact.get("location"), dict) else {}
    city = str(location.get("city") or "").strip()

    prefix = ""
    if target:
        prefix = f"Przy obiekcie {target}"
        if city and audience_scope != "owner":
            prefix += f" w mieście {city}"
    elif city:
        prefix = f"W mieście {city}"
    if prefix and statement:
        statement = f"{prefix} {statement[:1].lower()}{statement[1:]}"
    if audience_scope == "owner" and part:
        statement = f"{statement.rstrip('.: ')}: {part}."
    model_fact = {"fact_ref": visible_fact.get("fact_ref"), "statement": statement}
    if expose_required_phrase:
        required_phrase = part if audience_scope == "owner" and part else target or city
        if required_phrase:
            model_fact["required_phrase"] = required_phrase
    return model_fact


def _part_discovered_required_details(source_facts, audience_scope):
    semantic = (
        (source_facts[0] or {}).get("semantic")
        if source_facts and isinstance(source_facts[0], dict)
        else {}
    )
    semantic = semantic if isinstance(semantic, dict) else {}
    if audience_scope == "owner":
        part = _semantic_entity_label(semantic, "part")
        if part:
            return (part,)
    values = [_semantic_entity_label(semantic, "target")]
    location = semantic.get("location") if isinstance(semantic.get("location"), dict) else {}
    values.extend(str(value or "").strip() for value in location.values())
    return tuple(dict.fromkeys(value for value in values if value))[:12]


def _generation_output_schema(
    policy, allowed_fact_refs=(), allowed_cta_refs=(), allowed_asset_refs=(),
    allowed_asset_roles=(), editorial_contract=None,
):
    """Return a policy-scoped generation constraint within the canonical schema."""
    schema = load_output_schema(policy.output_schema_version)
    limits = _generation_limits_for_policy(policy)
    if not limits:
        return schema
    properties = schema.get("properties") or {}
    editorial_contract = editorial_contract if isinstance(editorial_contract, dict) else {}
    title_contract_limit = int(editorial_contract.get("title_chars") or 0)
    body_contract_limit = int(editorial_contract.get("body_chars") or 0)
    properties["title"]["maxLength"] = min(
        int(properties["title"].get("maxLength") or limits["title"]),
        title_contract_limit or limits["title"], limits["title"],
    )
    properties["body"]["maxLength"] = min(
        int(properties["body"].get("maxLength") or limits["body"]),
        body_contract_limit or limits["body"], limits["body"],
    )
    properties["fact_refs"]["maxItems"] = min(
        int(properties["fact_refs"].get("maxItems") or limits["refs"]), limits["refs"]
    )
    if _is_ghostnetwork_minimal_policy(policy):
        properties["fact_refs"]["items"]["enum"] = list(allowed_fact_refs)
        properties["cta_ref"]["enum"] = [None, *allowed_cta_refs]
    if "asset_ref" in properties:
        asset_types = properties["asset_ref"].get("type")
        nullable_asset = (
            asset_types == "null"
            or isinstance(asset_types, list) and "null" in asset_types
        )
        properties["asset_ref"]["enum"] = [
            *([None] if nullable_asset else []), *allowed_asset_refs
        ]
    if "asset_role" in properties:
        properties["asset_role"]["enum"] = [None, *allowed_asset_roles]
    return schema


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
        task.get("prompt_version"),
        task.get("output_schema_version"),
        task.get("model_policy_version"),
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

    is_ghostnetwork_v2 = _is_ghostnetwork_v2_policy(policy)
    is_ghostnetwork_minimal = _is_ghostnetwork_minimal_policy(policy)
    source_facts = []
    facts = []
    semantic_facts = []
    fact_refs = set()
    fact_ref_map = {}
    for item in (task.get("facts") or []):
        if not isinstance(item, dict):
            continue
        fact_id = str(item.get("fact_id") or "").strip()
        if not fact_id or fact_id in fact_refs:
            continue
        fact_refs.add(fact_id)
        source_facts.append(item)
        model_fact_ref = f"f{len(source_facts):02d}" if is_ghostnetwork_minimal else fact_id
        fact_ref_map[model_fact_ref] = fact_id
        if is_ghostnetwork_minimal:
            visible_fact = model_visible_semantic_fact(item, model_fact_ref)
            if (
                policy.prompt_version in {
                    GHOSTNETWORK_EVENT_PROMPT_VERSION,
                    GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
                    "ghostnetwork-event-prompt-v8",
                    "ghostnetwork-googleplex-prompt-v8",
                }
                and policy.task_variant in {"part_discovered", "googleplex_world_dispatch"}
                and str(item.get("fact_type") or "").strip() == "part_discovered"
            ):
                visible_fact = _part_discovered_model_fact(
                    visible_fact,
                    str(task.get("audience_scope") or "").strip(),
                    expose_required_phrase=policy.prompt_version in {
                        GHOSTNETWORK_EVENT_PROMPT_VERSION,
                        GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
                    },
                )
            semantic_facts.append(visible_fact)
        else:
            facts.append([model_fact_ref])
    if not source_facts:
        raise ValueError("ollama_task_has_no_facts")

    cta_map = {}
    cta_candidates = []
    for index, action in enumerate((task.get("allowed_actions") or [])[:32], start=1):
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("cta_action") or "").strip()[:64]
        if not action_name:
            continue
        ref = f"c{index:02d}"
        cta_candidates.append((ref, action_name, action))

    fact_columns = ["fact_ref"]
    source = {
        "scope": policy.source_scope,
        "task": str(task.get("outbox_id") or task.get("task_id") or "")[:128],
        "event": str(task.get("source_event_id") or "")[:128],
        "receipt": str(task.get("source_receipt_id") or "")[:128],
    }
    if is_ghostnetwork_v2:
        source = {"scope": policy.source_scope}
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
    if is_ghostnetwork_v2:
        audience = {"scope": audience["scope"]}

    if is_ghostnetwork_minimal:
        model_input = {
            "semantic_contract": SEMANTIC_INPUT_CONTRACT_VERSION,
            "medium": policy.target_medium,
            "audience": {**audience},
            "semantic_facts": semantic_facts,
        }
    else:
        model_input = {
            "source": source,
            "versions": versions,
            "medium": policy.target_medium,
            "audience": {**audience},
            "truth": str(task.get("truth_class_policy") or "").strip(),
            "fact_columns": fact_columns,
            "facts": facts,
        }
    narrative_intent = str(
        task.get("narrative_intent")
        or (task.get("validation") or {}).get("narrative_intent")
        or ""
    ).strip()
    if is_ghostnetwork_v2:
        validation = task.get("validation") if isinstance(task.get("validation"), dict) else {}
        event_family = str(
            validation.get("event_family")
            or ((source_facts[0] if source_facts else {}).get("fact_type"))
            or ""
        ).strip()[:64]
        significance = str(validation.get("significance") or "").strip()
        if narrative_intent not in GHOSTNETWORK_NARRATIVE_INTENTS:
            raise ValueError("ollama_task_narrative_intent_invalid")
        if not event_family:
            raise ValueError("ollama_task_event_family_missing")
        if significance not in GHOSTNETWORK_TONE_HINTS:
            raise ValueError("ollama_task_significance_invalid")
        aggregate_count = max(1, int(validation.get("aggregation_input") or 1))
        model_input.update({
            "narrative_intent": narrative_intent,
            "event_family": event_family,
            "significance": significance,
            "tone_hint": GHOSTNETWORK_TONE_HINTS[significance],
        })
        if aggregate_count > 1:
            model_input["thread_context"] = {
                "mode": "aggregate", "event_count": aggregate_count,
            }
    if not narrative_intent and policy.source_scope == "googleplex_editorial":
        # Compatibility for already queued Stage II assignments created before
        # the explicit column. The backend task variant still owns this choice.
        narrative_intent = (
            "product_benefit_promo"
            if policy.task_variant == "googleplex_product_promo"
            else "capability_invitation"
        )
    if (
        policy.source_scope == "blacknet_world"
        and policy.task_variant in {"blacknet_signal_narration", "googleplex_world_dispatch"}
    ):
        if narrative_intent not in SIGNAL_NARRATIVE_INTENTS:
            raise ValueError("ollama_task_narrative_intent_invalid")
        model_input["narrative_intent"] = narrative_intent
    elif policy.source_scope == "googleplex_editorial":
        if narrative_intent not in EDITORIAL_NARRATIVE_INTENTS:
            raise ValueError("ollama_task_narrative_intent_invalid")
        model_input["narrative_intent"] = narrative_intent
    editorial_contract = task.get("editorial_contract")
    if not isinstance(editorial_contract, dict):
        editorial_contract = (task.get("validation") or {}).get("editorial_contract") or {}
    allowed_asset_roles = task.get("allowed_asset_roles")
    if not isinstance(allowed_asset_roles, list):
        allowed_asset_roles = (task.get("validation") or {}).get("allowed_asset_roles") or []
    allowed_asset_roles = tuple(
        dict.fromkeys(str(item or "").strip() for item in allowed_asset_roles if str(item or "").strip())
    )[:8]
    if editorial_contract:
        model_input["presentation_slot"] = str(task.get("presentation_slot") or "")[:64]
        model_input["content_kind"] = str(task.get("content_kind") or "")[:48]
        model_input["copy_contract"] = {
            key: editorial_contract.get(key) for key in (
                "presentation_weight", "title_owner", "title_chars",
                "body_chars", "body_words", "estimated_lines", "canonical_title",
            ) if editorial_contract.get(key) not in (None, "")
        }
        model_input["allowed_asset_roles"] = list(allowed_asset_roles)
    generation_limits = _generation_limits_for_policy(policy)
    if generation_limits:
        # This bounded hint is part of the mandatory package for constrained
        # media. Optional CTA/fact columns must not displace output safety.
        model_input["output_limits"] = {
            "title_chars": generation_limits["title"],
            "body_chars": generation_limits["body"],
            "fact_refs": generation_limits["refs"],
            "json_only": True,
        }
    allowed_asset_refs = ()
    if policy.target_medium == "googleplex_news":
        allowed_asset_refs = googleplex_allowed_asset_refs(source_facts)
        model_input["allowed_asset_refs"] = list(allowed_asset_refs)

    mandatory_bytes = len(_encoded_package(model_input).encode("utf-8"))
    if mandatory_bytes > MAX_TASK_PACKAGE_BYTES:
        raise ValueError("ollama_task_mandatory_skeleton_too_large")

    # CTA visibility is optional: the model may always return cta_ref=null.
    # Only complete rows that fit become valid backend-resolvable references.
    if not is_ghostnetwork_minimal:
        for ref, action_name, action in cta_candidates:
            _try_add_cta_row(model_input, cta_map, ref, action_name, action)

    # Active GhostNetwork packages already contain the complete audience-safe
    # semantic projection. Technical fact tables remain a legacy-only contract.
    if is_ghostnetwork_minimal:
        field_groups = ()
    elif policy.target_medium == "googleplex_news":
        field_groups = (GOOGLEPLEX_PRESENTATION_FACT_FIELDS,)
    else:
        field_groups = (CANONICAL_FACT_REF_FIELDS, COMPACT_FACT_FIELDS)
    for field_group in field_groups:
        for field_spec in field_group:
            _try_add_fact_column(model_input, source_facts, facts, fact_columns, field_spec)

    # These bounded narrative hints are useful but not canonical identity.
    # They never displace facts, CTA rows, or source/version/audience refs.
    if not is_ghostnetwork_minimal:
        _try_add_top_level_field(
            model_input, "editorial", str(task.get("editorial_profile") or "")[:96]
        )
        _try_add_top_level_field(
            model_input, "context", str(task.get("narrative_context") or "")[:256]
        )
    if not is_ghostnetwork_v2:
        _try_add_top_level_field(
            model_input, "limits", {"title": 96, "body": 480, "refs": 16}
        )

    encoded = _encoded_package(model_input)
    input_bytes = len(encoded.encode("utf-8"))
    if input_bytes > MAX_TASK_PACKAGE_BYTES:
        raise ValueError("ollama_task_package_too_large")
    system_prompt, domain_prompt = load_prompt_layers(policy)
    voice_contract = {}
    active_ghost_prompt = (
        policy.source_scope == "ghostnetwork"
        and policy.prompt_version in {
            GHOSTNETWORK_EVENT_PROMPT_VERSION,
            GHOSTNETWORK_SIGNAL_PROMPT_VERSION,
            GHOSTNETWORK_GOOGLEPLEX_PROMPT_VERSION,
        }
    )
    if active_ghost_prompt:
        is_part_discovered = (
            str((source_facts[0] or {}).get("fact_type") or "").strip()
            == "part_discovered"
        )
        if is_part_discovered:
            detail_values = list(_part_discovered_required_details(
                source_facts, str(task.get("audience_scope") or "").strip()
            ))
            voice_contract["forbidden_relation_phrases"] = (
                "należy do", "nalezy do", "należący do", "należąca do",
                "należące do", "nalezacy do", "nalezaca do", "nalezace do",
                "jest własnością", "jest wlasnoscia", "właścicielem jest",
                "wlascicielem jest",
            )
        else:
            detail_values = []
            for semantic_fact in model_input.get("semantic_facts") or ():
                detail_values.extend(
                    str(entity.get("label") or "").strip()
                    for entity in semantic_fact.get("entities") or ()
                    if isinstance(entity, dict)
                )
                detail_values.extend(
                    str(value or "").strip()
                    for value in (semantic_fact.get("location") or {}).values()
                )
        detail_values = tuple(dict.fromkeys(
            value for value in detail_values if value
        ))[:12]
        if detail_values:
            voice_contract["detail_values"] = detail_values
    if active_ghost_prompt and policy.target_medium == "blacknet":
        voice_contract.update({
            "title_prefix": "PRZECHWYT // ",
            "body_prefix": "...",
        })
    return {
        "policy": policy,
        "messages": [
            {"role": "system", "content": system_prompt + "\n\n" + domain_prompt},
            {"role": "user", "content": encoded},
        ],
        "format": _generation_output_schema(
            policy, sorted(fact_ref_map), sorted(cta_map), allowed_asset_refs,
            allowed_asset_roles, editorial_contract,
        ),
        "fact_refs": frozenset(fact_ref_map),
        "fact_ref_map": copy.deepcopy(fact_ref_map),
        "canonical_fact_refs": frozenset(fact_refs),
        "cta_map": cta_map,
        "request_hash": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "input_bytes": input_bytes,
        "estimated_input_tokens": int(math.ceil(len(encoded) / ESTIMATED_TOKEN_CHARS)),
        "fact_count": len(source_facts),
        "source_facts": tuple(copy.deepcopy(source_facts)),
        "semantic_audit": tuple(
            semantic_audit_projection(item) for item in source_facts
        ) if is_ghostnetwork_minimal else (),
        "allowed_asset_refs": tuple(allowed_asset_refs),
        "allowed_asset_roles": allowed_asset_roles,
        "editorial_contract": copy.deepcopy(editorial_contract),
        "voice_contract": voice_contract,
        "selected_source_ref": str(
            task.get("selected_source_ref")
            or (task.get("validation") or {}).get("selected_source_ref") or ""
        ).strip(),
        "narrative_intent": narrative_intent,
        "fixed_action": copy.deepcopy(
            task.get("fixed_action")
            or (task.get("validation") or {}).get("fixed_action") or {}
        ),
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
    format_properties = ((task_package.get("format") or {}).get("properties") or {})
    allows_asset = "asset_ref" in format_properties
    allows_asset_role = "asset_role" in format_properties
    expected_keys = {"title", "body", "tone", "fact_refs", "cta_ref"}
    if allows_asset:
        expected_keys.add("asset_ref")
    if allows_asset_role:
        expected_keys.add("asset_role")
    if set(output) != expected_keys:
        errors.append("schema_fields_mismatch")
    title = output.get("title")
    body = output.get("body")
    tone = output.get("tone")
    refs = output.get("fact_refs")
    cta_ref = output.get("cta_ref")
    asset_ref = output.get("asset_ref")
    asset_role = output.get("asset_role")
    policy = task_package.get("policy")
    editorial_contract = task_package.get("editorial_contract") or {}
    narrative_intent = task_package.get("narrative_intent") or ""
    canonical_title = str(editorial_contract.get("canonical_title") or "").strip()
    if editorial_contract.get("title_owner") == "backend" and canonical_title:
        title = canonical_title
    title, body, identifier_normalized = normalize_canonical_identifier_leaks(
        title, body, task_package.get("source_facts") or ()
    )
    body, product_prefix_normalized = normalize_product_filler_prefix(
        body, narrative_intent
    )
    title_limit = int((format_properties.get("title") or {}).get("maxLength") or 96)
    body_limit = int((format_properties.get("body") or {}).get("maxLength") or 800)
    if editorial_contract:
        if not isinstance(title, str) or len(title) > title_limit:
            errors.append("slot_copy_budget_exceeded")
        if not isinstance(body, str) or len(body) > body_limit:
            errors.append("slot_copy_budget_exceeded")
    title, title_bounded = bound_presentation_text(title, title_limit)
    body, body_bounded = bound_presentation_text(body, body_limit)
    if identifier_normalized or product_prefix_normalized:
        output = dict(output)
        output["title"] = title
        output["body"] = body
    elif title_bounded or body_bounded:
        output = dict(output)
        output["title"] = title
        output["body"] = body
    if not isinstance(title, str) or not title.strip() or len(title) > title_limit:
        errors.append("invalid_title")
    if not isinstance(body, str) or not body.strip() or len(body) > body_limit:
        errors.append("invalid_body")
    voice_contract = task_package.get("voice_contract") or {}
    for field_name, value in (("title", title), ("body", body)):
        prefix = str(voice_contract.get(f"{field_name}_prefix") or "")
        if prefix and (not isinstance(value, str) or not value.startswith(prefix)):
            errors.append(f"voice_{field_name}_prefix_mismatch")
    detail_values = tuple(voice_contract.get("detail_values") or ())
    if detail_values and isinstance(title, str) and isinstance(body, str):
        if not any(str(value).casefold() in body.casefold() for value in detail_values):
            errors.append("voice_semantic_detail_missing")
    forbidden_relation_phrases = tuple(
        voice_contract.get("forbidden_relation_phrases") or ()
    )
    if isinstance(body, str) and any(
        str(phrase).casefold() in body.casefold()
        for phrase in forbidden_relation_phrases
    ):
        errors.append("voice_unsupported_relation")
    if editorial_contract:
        if isinstance(body, str) and len(body.split()) > int(editorial_contract.get("body_words") or 9999):
            errors.append("slot_copy_budget_exceeded")
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
    fact_ref_map = task_package.get("fact_ref_map") or {}
    canonical_refs = (
        [fact_ref_map.get(ref, ref) for ref in refs]
        if isinstance(refs, list)
        else []
    )
    selected_source_ref = str(task_package.get("selected_source_ref") or "").strip()
    if selected_source_ref and canonical_refs != [selected_source_ref]:
        security_errors.append("selected_fact_mismatch")
    cta_ref_removed = False
    cta_map = task_package.get("cta_map") or {}
    if cta_ref is not None and not cta_map:
        # A model cannot create a capability when the backend exposed no CTA
        # choices. Removing the unsupported reference is fail-closed: content
        # may survive, but no model-selected action can reach publication.
        cta_ref = None
        cta_ref_removed = True
        output = dict(output)
        output["cta_ref"] = None
    elif cta_ref is not None:
        if not isinstance(cta_ref, str) or cta_ref not in cta_map:
            security_errors.append("unknown_cta_ref")
        else:
            cta_fact_ref = str(
                (cta_map.get(cta_ref) or {}).get("fact_ref")
                or ""
            ).strip()
            if cta_fact_ref and (
                not isinstance(refs, list) or cta_fact_ref not in canonical_refs
            ):
                security_errors.append("cta_fact_mismatch")
    asset_schema = format_properties.get("asset_ref") or {}
    asset_types = asset_schema.get("type")
    asset_required = allows_asset and not (
        asset_types == "null"
        or isinstance(asset_types, list) and "null" in asset_types
    )
    if allows_asset:
        if asset_required and (asset_ref is None or asset_ref == ""):
            security_errors.append("missing_asset_ref")
        elif not isinstance(asset_ref, str) or asset_ref not in (task_package.get("allowed_asset_refs") or ()):
            security_errors.append("unknown_asset_ref")
    resolved_asset_ref = asset_ref if allows_asset and asset_ref else ""
    if allows_asset_role:
        allowed_roles = task_package.get("allowed_asset_roles") or ()
        if asset_role is not None and (
            not isinstance(asset_role, str) or asset_role not in allowed_roles
        ):
            security_errors.append("unknown_asset_role")
        role_map = editorial_contract.get("asset_role_map") if isinstance(editorial_contract.get("asset_role_map"), dict) else {}
        resolved_asset_ref = str(
            role_map.get(asset_role)
            or editorial_contract.get("fallback_asset_ref")
            or ""
        ).strip()
        if not resolved_asset_ref:
            security_errors.append("missing_asset_ref")
    security_errors.extend(presentation_safety_errors(title, body))
    security_errors.extend(source_metadata_leak_errors(
        title, body, task_package.get("source_facts") or ()
    ))
    if unknown_canonical_poi_names(
        title, body, task_package.get("source_facts") or ()
    ):
        security_errors.append("unknown_canonical_poi_name")

    if (
        policy
        and policy.source_scope == "googleplex_app"
        and policy.task_variant == "owner-analysis"
        and isinstance(title, str)
        and isinstance(body, str)
    ):
        if owner_analysis_echoes_input(
            title, body, task_package.get("source_facts") or ()
        ):
            errors.append("owner_analysis_echo")
    if (
        policy
        and policy.source_scope == "googleplex_editorial"
        and policy.task_variant == "googleplex_product_promo"
        and isinstance(body, str)
        and product_promo_echoes_description(
            body, task_package.get("source_facts") or ()
        )
    ):
        errors.append("product_promo_source_echo")
    if (
        policy
        and policy.source_scope == "blacknet_world"
        and policy.task_variant in {"blacknet_signal_narration", "googleplex_world_dispatch"}
    ):
        errors.extend(signal_narrative_quality_errors(
            title, body, task_package.get("source_facts") or (),
            narrative_intent,
        ))

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
            "fact_refs": canonical_refs,
            "cta_ref": cta_ref,
            **({"asset_ref": resolved_asset_ref} if allows_asset or allows_asset_role else {}),
        },
        "resolved_cta": copy.deepcopy(
            task_package.get("fixed_action")
            or (task_package.get("cta_map") or {}).get(cta_ref)
        ),
        "resolved_asset_ref": resolved_asset_ref,
        "normalizations": [
            *(["canonical_identifier_to_safe_label"] if identifier_normalized else []),
            *(["product_filler_prefix_removed"] if product_prefix_normalized else []),
            *(["schema_length_bounded"] if title_bounded or body_bounded else []),
            *(["unsupported_cta_removed"] if cta_ref_removed else []),
        ],
    }
