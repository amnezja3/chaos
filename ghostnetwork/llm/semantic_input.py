from __future__ import annotations

import math
import re
import unicodedata
from copy import deepcopy


SEMANTIC_INPUT_CONTRACT_VERSION = "chaos-llm-semantic-input-v1"
SCAN_LOCATION_CONTRACT_VERSION = "chaos-scan-location-v1"

CITY_TAG_KEYS = ("addr:city", "city", "is_in:city")
COUNTRY_TAG_KEYS = ("addr:country", "country", "is_in:country")
COUNTRY_CODE_TAG_KEYS = (
    "addr:country_code", "country_code", "ISO3166-1:alpha2",
)

SEMANTIC_LIMITS = {
    "statement": 280,
    "entities": 6,
    "entity_role": 48,
    "entity_kind": 32,
    "entity_label": 96,
    "location_label": 120,
    "city": 80,
    "country": 80,
    "country_code": 8,
    "attributes": 8,
    "attribute_name": 48,
    "attribute_text": 120,
    "provenance": 24,
    "source_path": 160,
    "semantic_path": 120,
}

_OPAQUE_IDENTIFIER = re.compile(
    r"(?:"
    r"\b(?:event|task|attempt|candidate|receipt|reservation|narrative|cycle)_"
    r"[a-z0-9_.:-]{5,}\b|"
    r"\b(?:ghostnetwork|ghostcycle|ghostpart|ghostmachine)_[a-z0-9_.:-]{3,}\b|"
    r"\b(?:ghost_fact|fact):[a-z0-9_.:-]{4,}\b|"
    r"\bghost-(?:node|link):[a-z0-9_.:-]{5,}\b|"
    r"\bmap:-?\d+(?:\.\d+)?:-?\d+(?:\.\d+)?:|"
    r"\b[0-9a-f]{10,}\b"
    r")",
    re.IGNORECASE,
)


def _bounded_text(value, limit):
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[: max(0, int(limit or 0))]


def _comparison_key(value):
    return _bounded_text(value, 160).casefold()


def contains_opaque_identifier(value):
    return bool(_OPAQUE_IDENTIFIER.search(str(value or "")))


def normalize_location(location):
    """Return the bounded canonical location projection; never infer values."""
    location = location if isinstance(location, dict) else {}
    normalized = {}
    for key, limit in (
        ("label", SEMANTIC_LIMITS["location_label"]),
        ("city", SEMANTIC_LIMITS["city"]),
        ("country", SEMANTIC_LIMITS["country"]),
        ("country_code", SEMANTIC_LIMITS["country_code"]),
    ):
        value = _bounded_text(location.get(key), limit)
        if value and not contains_opaque_identifier(value):
            normalized[key] = value.upper() if key == "country_code" else value
    return normalized


def _first_tag_value(tags, keys):
    tags = tags if isinstance(tags, dict) else {}
    for key in keys:
        value = _bounded_text(tags.get(key), 160)
        if value:
            return value
    return ""


def project_poi_location(tags):
    """Project only location fields needed downstream from an OSM tag map."""
    return normalize_location({
        "city": _first_tag_value(tags, CITY_TAG_KEYS),
        "country": _first_tag_value(tags, COUNTRY_TAG_KEYS),
        "country_code": _first_tag_value(tags, COUNTRY_CODE_TAG_KEYS),
    })


def infer_scan_location(items):
    """Infer conservative field-level agreement inside one scan response.

    Missing values do not vote. A field is accepted only with two unanimous
    observations, or with one observation when the scan has one source POI.
    Any conflict produces UNKNOWN (the field is absent).
    """
    source_items = [
        item for item in (items or [])
        if isinstance(item, dict) and not bool(item.get("generated"))
    ][:60]
    observations = {"city": [], "country": [], "country_code": []}
    for item in source_items:
        location = project_poi_location(item.get("tags"))
        for field in observations:
            value = location.get(field)
            if value:
                observations[field].append(value)

    location = {}
    evidence = {}
    conflicts = []
    for field, values in observations.items():
        groups = {}
        for value in values:
            groups.setdefault(_comparison_key(value), []).append(value)
        evidence[field] = len(values)
        enough = len(values) >= 2 or (len(source_items) == 1 and len(values) == 1)
        if len(groups) == 1 and enough:
            location[field] = next(iter(groups.values()))[0]
        elif len(groups) > 1:
            conflicts.append(field)

    return {
        "contract": SCAN_LOCATION_CONTRACT_VERSION,
        "source_poi_count": len(source_items),
        "location": normalize_location(location),
        "evidence": evidence,
        "conflicts": conflicts,
    }


def _normalize_entity(value):
    value = value if isinstance(value, dict) else {}
    label = _bounded_text(value.get("label"), SEMANTIC_LIMITS["entity_label"])
    if not label or contains_opaque_identifier(label):
        return None
    entity = {
        "role": _bounded_text(value.get("role"), SEMANTIC_LIMITS["entity_role"]),
        "kind": _bounded_text(value.get("kind"), SEMANTIC_LIMITS["entity_kind"]),
        "label": label,
    }
    return {key: item for key, item in entity.items() if item}


def _normalize_attribute(value):
    value = value if isinstance(value, dict) else {}
    name = _bounded_text(value.get("name"), SEMANTIC_LIMITS["attribute_name"])
    raw = value.get("value")
    if not name or raw is None or isinstance(raw, (dict, list, tuple, set)):
        return None
    if isinstance(raw, bool):
        normalized_value = raw
    elif isinstance(raw, int):
        normalized_value = raw
    elif isinstance(raw, float):
        if not math.isfinite(raw):
            return None
        normalized_value = round(raw, 3)
    else:
        normalized_value = _bounded_text(raw, SEMANTIC_LIMITS["attribute_text"])
        if not normalized_value or contains_opaque_identifier(normalized_value):
            return None
    return {"name": name, "value": normalized_value}


def normalize_semantic_content(content):
    """Validate and bound domain-authored, model-visible semantic content."""
    content = content if isinstance(content, dict) else {}
    unknown_fields = set(content) - {"statement", "entities", "location", "attributes"}
    if unknown_fields:
        raise ValueError("semantic_content_has_unknown_fields")
    statement = _bounded_text(content.get("statement"), SEMANTIC_LIMITS["statement"])
    if not statement:
        raise ValueError("semantic_statement_missing")
    if contains_opaque_identifier(statement):
        raise ValueError("semantic_statement_contains_technical_id")
    normalized = {"statement": statement}

    entities = [
        item for item in (
            _normalize_entity(value)
            for value in (content.get("entities") or [])[: SEMANTIC_LIMITS["entities"]]
        ) if item
    ]
    if entities:
        normalized["entities"] = entities

    location = normalize_location(content.get("location"))
    if location:
        normalized["location"] = location

    attributes = [
        item for item in (
            _normalize_attribute(value)
            for value in (content.get("attributes") or [])[: SEMANTIC_LIMITS["attributes"]]
        ) if item
    ]
    if attributes:
        normalized["attributes"] = attributes
    return normalized


def normalize_semantic_provenance(items):
    normalized = []
    for item in (items or [])[: SEMANTIC_LIMITS["provenance"]]:
        if not isinstance(item, dict):
            continue
        semantic_path = _bounded_text(
            item.get("semantic_path"), SEMANTIC_LIMITS["semantic_path"]
        )
        source_path = _bounded_text(
            item.get("source_path"), SEMANTIC_LIMITS["source_path"]
        )
        if semantic_path and source_path:
            normalized.append({
                "semantic_path": semantic_path,
                "source_path": source_path,
            })
    return normalized


def attach_semantic_content(fact, content, provenance=()):
    """Attach a shared semantic projection while retaining backend lineage."""
    result = deepcopy(fact if isinstance(fact, dict) else {})
    result["semantic_contract"] = SEMANTIC_INPUT_CONTRACT_VERSION
    result["semantic"] = normalize_semantic_content(content)
    normalized_provenance = normalize_semantic_provenance(provenance)
    if normalized_provenance:
        result["semantic_provenance"] = normalized_provenance
    return result


def model_visible_semantic_fact(fact, fact_ref):
    """Return exactly one model-visible fact, with no backend identifiers."""
    fact = fact if isinstance(fact, dict) else {}
    if fact.get("semantic_contract") != SEMANTIC_INPUT_CONTRACT_VERSION:
        raise ValueError("semantic_contract_missing_or_unsupported")
    semantic = normalize_semantic_content(fact.get("semantic"))
    return {"fact_ref": str(fact_ref or "")[:16], **semantic}


def semantic_audit_projection(fact):
    """Bounded, value-safe explanation of a canonical fact projection."""
    fact = fact if isinstance(fact, dict) else {}
    semantic = normalize_semantic_content(fact.get("semantic"))
    return {
        "semantic_contract": fact.get("semantic_contract") or "",
        "semantic_fields": sorted(semantic),
        "has_location": bool(semantic.get("location")),
        "entity_count": len(semantic.get("entities") or []),
        "attribute_count": len(semantic.get("attributes") or []),
        "provenance": normalize_semantic_provenance(
            fact.get("semantic_provenance") or []
        ),
    }
