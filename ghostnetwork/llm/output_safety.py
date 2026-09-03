from __future__ import annotations

import json
import re
import unicodedata

from ..catalog import get_catalog


GHOST_OUTPUT_SAFETY_CONTRACT_VERSION = "ghostnetwork-output-safety-v1"


_URL = re.compile(r"(?:https?://|www\.|ftp://)", re.IGNORECASE)
_TECHNICAL_IDENTIFIER = re.compile(
    r"(?:\b(?:narrative|receipt|candidate|task|attempt|event|signal|cycle|reservation)_"
    r"[a-z0-9_.:-]{5,}\b|\b(?:ghostnetwork|ghostcycle|ghostpart|ghostmachine)_"
    r"[a-z0-9_.:-]{3,}\b|\b(?:ghost_fact|fact):[a-z0-9_.:-]{4,}\b|"
    r"\bghost-(?:node|link):[a-z0-9_.:-]{5,}\b|"
    r"\bmap:-?\d+(?:\.\d+)?:-?\d+(?:\.\d+)?:)",
    re.IGNORECASE,
)
_CONTROL_METADATA = re.compile(
    r"\b(?:semantic[ _-]?facts?|fact[ _-]?ref|cta[ _-]?ref|asset[ _-]?ref|"
    r"narrative[ _-]?intent|event[ _-]?family|audience[ _-]?scope|"
    r"truth[ _-]?class|source[ _-]?scope|output[ _-]?schema|system[ _-]?prompt|"
    r"prompt[ _-]?version)\b",
    re.IGNORECASE,
)
_PROMPT_OR_TOOL_LANGUAGE = re.compile(
    r"\b(?:ignore (?:all |the )?(?:previous|prior) instructions|"
    r"zignoruj (?:wszystkie )?(?:poprzednie|wcześniejsze) instrukcje|"
    r"jako (?:model|asystent|ai)|nie mam dostępu|nie mam dostepu|"
    r"wywołałem narzędzie|wywolalem narzedzie)\b",
    re.IGNORECASE,
)
_EMAIL = re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?!\w)")
_IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?!\d|\.\d)")
_FILESYSTEM_PATH = re.compile(
    r"(?:\b[A-Za-z]:\\(?:[^\s\\]+\\)*[^\s\\]+|(?<!\w)/(?:home|root|etc|var|tmp|srv)/[^\s]+)",
    re.IGNORECASE,
)
_CREDENTIAL = re.compile(
    r"\b(?:password|hasło|haslo|api[ _-]?key|access[ _-]?token|session[ _-]?id|"
    r"bearer)\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)
_UNSAFE_MARKUP = re.compile(
    r"<(?:script|iframe|object|embed|style|img|svg|link|meta)\b|javascript\s*:",
    re.IGNORECASE,
)
_COORDINATE_PAIR = re.compile(
    r"(?<![\w.])[-+]?\d{1,3}[.,]\d{3,}\s*[,;/]\s*"
    r"[-+]?\d{1,3}[.,]\d{3,}(?!\w|\.\d)"
)


def _fold(value):
    text = unicodedata.normalize("NFKD", str(value or "")).casefold().translate(
        str.maketrans({"ł": "l"})
    )
    return "".join(char for char in text if not unicodedata.combining(char))


def _phrase_present(text, phrase):
    folded_text = _fold(text)
    folded_phrase = _fold(phrase).strip()
    if not folded_phrase:
        return False
    return bool(re.search(rf"(?<!\w){re.escape(folded_phrase)}(?!\w)", folded_text))


def _visible_semantic_text(model_input):
    return json.dumps(
        (model_input or {}).get("semantic_facts") or [],
        ensure_ascii=False,
        sort_keys=True,
    )


def _catalog_values():
    catalog = get_catalog()
    values = []
    for collection, fields in (
        ("clans", ("code", "name", "short_code")),
        ("machines", ("code", "name")),
        ("parts", ("part_code", "name", "profession_code", "ability_code")),
        ("professions", ("code", "name")),
        ("abilities", ("ability_code", "name")),
    ):
        for item in catalog.get(collection, ()):
            if not isinstance(item, dict):
                continue
            for field in fields:
                value = str(item.get(field) or "").strip()
                if len(value) >= 4:
                    values.append(value)
    return tuple(dict.fromkeys(values))


_CATALOG_VALUES = _catalog_values()


def verify_ghost_output_safety():
    errors = []
    if not _CATALOG_VALUES:
        errors.append("ghost_output_safety_catalog_empty")
    return {
        "ok": not errors,
        "contract_version": GHOST_OUTPUT_SAFETY_CONTRACT_VERSION,
        "catalog_value_count": len(_CATALOG_VALUES),
        "errors": errors,
    }


def _unknown_catalog_values(text, visible_text):
    return tuple(
        value for value in _CATALOG_VALUES
        if _phrase_present(text, value) and not _phrase_present(visible_text, value)
    )


def validate_ghost_output_safety(
    title,
    body,
    *,
    model_input,
    fact_aliases=(),
    cta_aliases=(),
    asset_refs=(),
    forbidden_values=(),
):
    """Validate claims and presentation data against model-visible semantics.

    This contract is backend-only. It does not attempt open-ended fact checking;
    it rejects bounded, high-confidence classes that must never reach a medium.
    """
    text = f"{title or ''}\n{body or ''}"
    visible_text = _visible_semantic_text(model_input)
    security_errors = []

    if _URL.search(text):
        security_errors.append("external_url")
    if _TECHNICAL_IDENTIFIER.search(text):
        security_errors.append("internal_identifier_leak")
    if _CONTROL_METADATA.search(text):
        security_errors.append("control_metadata_leak")
    aliases = tuple(
        str(item or "").strip()
        for item in (*fact_aliases, *cta_aliases, *asset_refs)
        if str(item or "").strip()
    )
    if any(_phrase_present(text, alias) for alias in aliases):
        security_errors.append("model_alias_leak")
    if _PROMPT_OR_TOOL_LANGUAGE.search(text):
        security_errors.append("prompt_or_tool_language_leak")
    if _EMAIL.search(text) or _CREDENTIAL.search(text):
        security_errors.append("credential_or_personal_data_leak")
    if _IPV4.search(text):
        security_errors.append("network_address_leak")
    if _COORDINATE_PAIR.search(text):
        security_errors.append("raw_coordinate_leak")
    if _FILESYSTEM_PATH.search(text):
        security_errors.append("filesystem_path_leak")
    if _UNSAFE_MARKUP.search(text):
        security_errors.append("unsafe_markup")
    if _unknown_catalog_values(text, visible_text):
        security_errors.append("audience_hidden_catalog_value")
    if any(
        _phrase_present(text, value) and not _phrase_present(visible_text, value)
        for value in forbidden_values
        if len(str(value or "").strip()) >= 3
    ):
        security_errors.append("audience_hidden_value_leak")

    return {
        "contract_version": GHOST_OUTPUT_SAFETY_CONTRACT_VERSION,
        "security_errors": sorted(set(security_errors)),
        "grounding_errors": [],
    }
