"""Bounded, read-only Googleplex Home/News projection.

Sprint 135.4.1 intentionally does not read profiles, Outbox, Inbox or Ollama.
The module owns presentation safety and deterministic foundation entries only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ghostnetwork.ollama_policy import presentation_safety_errors


SCHEMA_VERSION = "googleplex-news-home-v1"
FOUNDATION_PUBLISHED_AT = "2026-08-28T00:00:00Z"
DEFAULT_LIMIT = 20
MIN_LIMIT = 12
MAX_LIMIT = 24

PRESENTATION_LIMITS = {
    "hero": {"title": 72, "summary": 220},
    "large": {"title": 54, "summary": 130},
    "medium": {"title": 44, "summary": 90},
    "small": {"title": 32, "summary": 48},
}
PRESENTATION_WEIGHTS = frozenset(PRESENTATION_LIMITS)
ASSET_FAMILIES = frozenset({
    "scene", "character", "tool", "map", "clan", "package", "storage",
    "market", "network", "system", "stamp",
})
ASSET_STATES = frozenset({"neutral", "danger", "victory", "defence"})
ENTRY_STATES = frozenset({
    "normal", "trending", "hot", "warning", "critical", "new",
    "verified", "stale", "disabled",
})
AUDIENCE_SCOPES = frozenset({"public", "clan", "owner"})
ACTION_ALLOWLIST = frozenset({
    "open_googleplex_search",
    "open_blacknet",
    "open_ghost_exchange",
    "open_map",
    "open_cyberner",
    "open_operation",
})


class GoogleplexNewsConfigurationError(RuntimeError):
    """Raised when the code-owned asset registry is invalid."""


def _utc_text(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)].rstrip() + "…"


def _stable_hash(*values: Any, size: int = 16) -> str:
    payload = "\x1f".join(str(value or "") for value in values)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:size]


def _registry_default_path() -> Path:
    return Path(__file__).resolve().parent / "static" / "images" / "googleplx" / "asset_registry.json"


@lru_cache(maxsize=4)
def load_asset_registry(path: str = "") -> dict[str, dict[str, Any]]:
    registry_path = Path(path) if path else _registry_default_path()
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GoogleplexNewsConfigurationError("googleplex_asset_registry_unavailable") from exc
    records = payload.get("assets") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        raise GoogleplexNewsConfigurationError("googleplex_asset_registry_invalid")
    registry: dict[str, dict[str, Any]] = {}
    for raw in records:
        if not isinstance(raw, dict):
            raise GoogleplexNewsConfigurationError("googleplex_asset_registry_invalid_record")
        record = dict(raw)
        asset_id = str(record.get("asset_id") or "").strip()
        family = str(record.get("asset_family") or "").strip()
        state = str(record.get("asset_state") or "neutral").strip()
        asset_path = str(record.get("path") or "").strip()
        status = str(record.get("status") or "").strip()
        weights = record.get("allowed_presentation_weights")
        asset_kind = str(record.get("asset_kind") or "image").strip()
        mime_type = str(record.get("mime_type") or "").strip().lower()
        clean_path = asset_path.split("#", 1)[0]
        workspace_root = Path(__file__).resolve().parent
        resolved_asset_path = (workspace_root / clean_path.lstrip("/")).resolve()
        static_root = (workspace_root / "static" / "images" / "googleplx").resolve()
        extension = resolved_asset_path.suffix.lower()
        mime_matches = {
            ".webp": "image/webp",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }.get(extension) == mime_type
        try:
            native_width = int(record.get("native_width") or 0)
            native_height = int(record.get("native_height") or 0)
        except (TypeError, ValueError):
            native_width = native_height = 0
        if (
            not asset_id
            or asset_id in registry
            or family not in ASSET_FAMILIES
            or state not in ASSET_STATES
            or status not in {"draft", "review", "ready", "retired"}
            or not asset_path.startswith("/static/images/googleplx/")
            or asset_kind not in {"image", "symbol"}
            or not mime_matches
            or static_root not in resolved_asset_path.parents
            or not resolved_asset_path.is_file()
            or native_width < 1
            or native_height < 1
            or not isinstance(weights, list)
            or not weights
            or any(str(weight) not in PRESENTATION_WEIGHTS for weight in weights)
        ):
            raise GoogleplexNewsConfigurationError("googleplex_asset_registry_invalid_record")
        registry[asset_id] = record
    return registry


def _safe_asset(
    registry: dict[str, dict[str, Any]],
    asset_id: str,
    family: str,
    weight: str,
) -> dict[str, Any]:
    record = registry.get(asset_id) or {}
    if (
        record.get("status") != "ready"
        or record.get("asset_family") != family
        or weight not in (record.get("allowed_presentation_weights") or [])
    ):
        fallback_id = f"gp_fallback_{family}"
        record = registry.get(fallback_id) or {}
        asset_id = fallback_id
    if (
        record.get("status") != "ready"
        or record.get("asset_family") != family
        or weight not in (record.get("allowed_presentation_weights") or [])
    ):
        return {
            "asset_id": "",
            "asset_family": family,
            "asset_state": "neutral",
            "asset_path": "",
            "asset_kind": "css",
            "asset_focus_x": 50,
            "asset_focus_y": 50,
            "asset_scale": 1,
            "asset_rotation": 0,
        }
    preset = dict((record.get("focus_presets") or {}).get(weight) or {})
    return {
        "asset_id": asset_id,
        "asset_family": family,
        "asset_state": str(record.get("asset_state") or "neutral"),
        "asset_path": str(record.get("path") or ""),
        "asset_kind": str(record.get("asset_kind") or "image"),
        "asset_focus_x": float(preset.get("focus_x", 50)),
        "asset_focus_y": float(preset.get("focus_y", 50)),
        "asset_scale": float(preset.get("scale", 1)),
        "asset_rotation": float(preset.get("rotation", 0)),
    }


def _action(action_type: str = "", target: str = "", payload_ref: str = "") -> dict[str, str]:
    action_type = str(action_type or "").strip()
    if action_type not in ACTION_ALLOWLIST:
        return {"kind": "STAMP_ONLY", "action_type": "", "action_target": "", "action_payload_ref": ""}
    return {
        "kind": "ACTIONABLE",
        "action_type": action_type,
        "action_target": _bounded_text(target, 120),
        "action_payload_ref": _bounded_text(payload_ref, 160),
    }


def _entry(
    *,
    news_id: str,
    source: str,
    source_ref: str,
    category: str,
    weight: str,
    title: str,
    summary: str,
    truth_class: str = "canonical",
    audience_scope: str = "public",
    state: str = "normal",
    accent_role: str = "normal",
    asset_id: str,
    asset_family: str,
    registry: dict[str, dict[str, Any]],
    primary_stat: str = "",
    secondary_stat: str = "",
    action_type: str = "",
    action_target: str = "",
    action_payload_ref: str = "",
    published_at: str,
) -> dict[str, Any]:
    if weight not in PRESENTATION_WEIGHTS:
        weight = "small"
    if audience_scope not in AUDIENCE_SCOPES:
        audience_scope = "public"
    if state not in ENTRY_STATES:
        state = "normal"
    if asset_family not in ASSET_FAMILIES:
        asset_family = "stamp"
    limits = PRESENTATION_LIMITS[weight]
    return {
        "content": {
            "news_id": _bounded_text(news_id, 96),
            "source": _bounded_text(source, 48),
            "source_ref": _bounded_text(source_ref, 128),
            "category": _bounded_text(category, 32),
            "title": _bounded_text(title, limits["title"]),
            "summary": _bounded_text(summary, limits["summary"]),
            "published_at": published_at,
            "truth_class": _bounded_text(truth_class, 24),
            "audience_scope": audience_scope,
        },
        "presentation": {
            "weight": weight,
            "state": state,
            "accent_role": _bounded_text(accent_role, 24),
            **_safe_asset(registry, asset_id, asset_family, weight),
            "primary_stat": _bounded_text(primary_stat, 22),
            "secondary_stat": _bounded_text(secondary_stat, 22),
        },
        "action": _action(action_type, action_target, action_payload_ref),
    }


def _catalog_products(catalog: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    products = [
        dict(item)
        for item in catalog
        if isinstance(item, dict) and item.get("published", True) and str(item.get("id") or "").strip()
    ]
    products.sort(key=lambda item: (
        -int(item.get("downloads") or 0),
        str(item.get("name") or "").casefold(),
        str(item.get("id") or ""),
    ))
    return products


def build_googleplex_news_snapshot(
    *,
    catalog: Iterable[dict[str, Any]],
    viewer_key: str,
    session_generation: str,
    limit: int = DEFAULT_LIMIT,
    now: datetime | None = None,
    registry_path: str = "",
) -> dict[str, Any]:
    """Build the deterministic Sprint 135.4.1 public foundation snapshot."""
    try:
        bounded_limit = max(MIN_LIMIT, min(MAX_LIMIT, int(limit or DEFAULT_LIMIT)))
    except (TypeError, ValueError):
        bounded_limit = DEFAULT_LIMIT
    generated_at = _utc_text(now)
    registry = load_asset_registry(registry_path)
    products = _catalog_products(catalog)
    featured = products[0] if products else {}
    featured_id = str(featured.get("id") or "")
    featured_name = str(featured.get("name") or "Katalog narzędzi")
    featured_description = str(featured.get("description") or "Przeglądaj dostępne aplikacje i narzędzia Googleplex.")

    definitions = [
        dict(news_id="gp-home-world-grid", source="ghostsystem", source_ref="world-grid", category="WORLD GRID", weight="hero", title="CHAOS World Grid: kanały operacyjne pozostają aktywne", summary="Googleplex News porządkuje zweryfikowane wejścia do istniejących systemów świata. Otwieranie tej powierzchni nie uruchamia modelu ani mechaniki gameplayowej.", truth_class="system", state="verified", accent_role="normal", asset_id="gp_scene_world_neutral_01", asset_family="scene", primary_stat="READ ONLY"),
        dict(news_id="gp-home-blacknet", source="blacknet", source_ref="world-signals", category="BLACKNET", weight="large", title="BlackNet: przechwyć bieżące sygnały świata", summary="Wejdź do istniejącego feedu BlackNet. News nie kopiuje jego danych ani filtrów.", state="hot", accent_role="underground", asset_id="gp_fallback_network", asset_family="network", primary_stat="LIVE BRIDGE", action_type="open_blacknet", action_target="world"),
        dict(news_id="gp-home-exchange", source="ghost_exchange", source_ref="market", category="GHOST EXCHANGE", weight="large", title="Ghost Exchange: rynek paczek danych", summary="Otwórz istniejący dashboard rynku. Transakcje pozostają wyłącznie w Ghost Exchange.", state="trending", accent_role="commerce", asset_id="gp_fallback_market", asset_family="market", primary_stat="MARKET", action_type="open_ghost_exchange", action_target="market"),
        dict(news_id="gp-home-map", source="map", source_ref="world", category="MAPA", weight="medium", title="Sytuacja świata i regionów", summary="Otwórz mapę bez automatycznego focusu lub teleportu.", state="normal", accent_role="normal", asset_id="gp_fallback_map", asset_family="map", action_type="open_map", action_target="world"),
        dict(news_id="gp-home-cyberner", source="cyberner", source_ref="world", category="CYBERNER", weight="medium", title="Kanał WORLD", summary="Przejdź do istniejącego publicznego kanału Cybernera.", state="new", accent_role="network", asset_id="gp_fallback_network", asset_family="network", action_type="open_cyberner", action_target="world"),
        dict(news_id="gp-home-featured", source="googleplex", source_ref=featured_id or "catalog", category="GOOGLEPLEX", weight="medium", title=featured_name, summary=featured_description, state="trending", accent_role="tool", asset_id="gp_fallback_tool", asset_family="tool", primary_stat=(f"{int(featured.get('downloads') or 0)} DL" if featured else "CATALOG"), action_type="open_googleplex_search", action_target=(featured_name if featured_id else "/all"), action_payload_ref=featured_id),
        dict(news_id="gp-home-operations", source="operations", source_ref="operation-center", category="OPERATIONS", weight="small", title="Centrum Operacji", summary="Sprawdź aktywne i historyczne operacje.", state="normal", accent_role="normal", asset_id="gp_fallback_system", asset_family="system", action_type="open_operation", action_target="operation-center"),
        dict(news_id="gp-home-packages", source="files", source_ref="packages", category="DATA", weight="small", title="Pakiety danych", summary="Pliki pozostają w swoich canonical surfaces.", state="verified", accent_role="commerce", asset_id="gp_fallback_package", asset_family="package"),
        dict(news_id="gp-home-storage", source="storage", source_ref="capacity", category="STORAGE", weight="small", title="Pamięć operatora", summary="Capacity jest prezentowane bez odczytu profilu.", state="normal", accent_role="warning", asset_id="gp_fallback_storage", asset_family="storage"),
        dict(news_id="gp-home-clans", source="clans", source_ref="public", category="CLANS", weight="small", title="Kanały klanowe", summary="Brak publicznego targetu: karta informacyjna.", state="normal", accent_role="normal", asset_id="gp_fallback_clan", asset_family="clan"),
        dict(news_id="gp-home-integrity", source="system", source_ref="integrity", category="INTEGRITY", weight="small", title="Canonical sources", summary="News nie jest source of truth.", truth_class="system", state="verified", accent_role="normal", asset_id="gp_fallback_system", asset_family="system", primary_stat="VERIFIED"),
        dict(news_id="gp-home-protocol", source="system", source_ref="protocol", category="PROTOCOL", weight="small", title="Audience projection", summary="Public, clan i owner są filtrowane po stronie backendu.", truth_class="system", state="verified", accent_role="defence", asset_id="gp_fallback_stamp", asset_family="stamp", primary_stat="FAIL CLOSED"),
    ]
    entries = [
        _entry(registry=registry, published_at=FOUNDATION_PUBLISHED_AT, **definition)
        for definition in definitions[:bounded_limit]
    ]
    action_count = sum(1 for item in entries if item["action"]["kind"] == "ACTIONABLE")
    sources = sorted({item["content"]["source"] for item in entries})
    global_stats = [
        {"key": "entries", "label": "NEWS", "value": len(entries), "state": "neutral"},
        {"key": "sources", "label": "SOURCES", "value": len(sources), "state": "neutral"},
        {"key": "bridges", "label": "BRIDGES", "value": action_count, "state": "neutral"},
        {"key": "catalog", "label": "CATALOG", "value": len(products), "state": "neutral"},
        {"key": "audience", "label": "AUDIENCE", "value": "PUBLIC", "state": "defence"},
        {"key": "mode", "label": "MODE", "value": "READ ONLY", "state": "defence"},
    ]
    protocol_status = {
        "source": "canonical-foundation",
        "integrity": "verified",
        "access_mode": "read-only",
        "ollama_used": False,
        "llm_task_enqueued": False,
        "publication_enabled": False,
    }
    snapshot_signature = json.dumps(
        {"entries": entries, "global_stats": global_stats, "protocol_status": protocol_status},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    state_version = _stable_hash(SCHEMA_VERSION, snapshot_signature)
    viewer_revision = _stable_hash(viewer_key, session_generation, "public")
    return {
        "success": True,
        "schema_version": SCHEMA_VERSION,
        "view": "home",
        "state_version": state_version,
        "generated_at": generated_at,
        "viewer_scope_revision": viewer_revision,
        "entries": entries,
        "global_stats": global_stats,
        "protocol_status": protocol_status,
        "next_cursor": "",
        "has_more": False,
        "diagnostics": {
            "entry_count": len(entries),
            "source_count": len(sources),
            "actionable_count": action_count,
            "profile_full_read": 0,
            "profile_full_write": 0,
            "profile_bytes": 0,
            "ollama_calls": 0,
            "llm_tasks_enqueued": 0,
        },
    }


def merge_googleplex_news_publications(
    snapshot: dict[str, Any], records: Iterable[dict[str, Any]], *,
    limit: int = DEFAULT_LIMIT, registry_path: str = ""
) -> dict[str, Any]:
    """Project publications into stable Home slots without growing the feed."""
    result = dict(snapshot or {})
    try:
        bounded_limit = max(MIN_LIMIT, min(MAX_LIMIT, int(limit or DEFAULT_LIMIT)))
    except (TypeError, ValueError):
        bounded_limit = DEFAULT_LIMIT
    registry = load_asset_registry(registry_path)
    allowed_publication_slots = {"gp-home-world-grid"}
    existing = list(result.get("entries") or [])
    slots = {
        str(item.get("content", {}).get("news_id") or ""): item
        for item in existing if isinstance(item, dict)
    }
    safe_records = []
    semantic_keys = set()
    content_keys = set()
    for record in records or []:
        if not isinstance(record, dict) or record.get("target_medium") != "googleplex_news":
            continue
        presentation_slot = str(record.get("presentation_slot") or "")
        if presentation_slot not in allowed_publication_slots:
            continue
        # The featured Googleplex product is a canonical catalog projection:
        # name, description, downloads and product link are code-owned.  Do
        # not let current or historical LLM product publications replace any
        # editorial slot, especially gp-home-featured.
        fact_refs = [str(item) for item in record.get("fact_refs") or []]
        if any("googleplex_product_signal" in item for item in fact_refs):
            continue
        if presentation_safety_errors(record.get("title"), record.get("body")):
            continue
        semantic_key = tuple(sorted(fact_refs))
        semantic_key = semantic_key or (str(record.get("source_receipt_id") or ""),)
        if semantic_key in semantic_keys:
            continue
        content_key = (
            " ".join(str(record.get("title") or "").split()).casefold(),
            " ".join(str(record.get("body") or "").split()).casefold(),
        )
        if content_key in content_keys:
            continue
        semantic_keys.add(semantic_key)
        content_keys.add(content_key)
        safe_records.append(record)
        if len(safe_records) >= len(allowed_publication_slots):
            break

    replacements = {}
    for record in safe_records:
        slot_id = str(record.get("presentation_slot") or "")
        fallback = slots.get(slot_id)
        if not fallback:
            continue
        presentation = fallback.get("presentation") or {}
        asset = fallback.get("asset") or {}
        payload = record.get("cta_payload") if isinstance(record.get("cta_payload"), dict) else {}
        action = str(record.get("cta_action") or "")
        target = str(
            payload.get("target_id") or payload.get("channel")
            or payload.get("query") or ""
        )
        requested_asset = str(record.get("asset_ref") or "")
        registry_asset = registry.get(requested_asset)
        if (
            registry_asset
            and registry_asset.get("status") == "ready"
            and presentation.get("weight") in registry_asset.get("allowed_presentation_weights", [])
        ):
            asset_id = requested_asset
            asset_family = str(registry_asset.get("asset_family") or "network")
        else:
            asset_id = str(asset.get("asset_id") or "gp_fallback_network")
            asset_family = str(asset.get("asset_family") or "network")
        replacements[slot_id] = _entry(
            news_id=slot_id,
            source="ollama_enriched",
            source_ref=str(record.get("publication_receipt_id") or ""),
            category="WORLD INTELLIGENCE",
            weight=str(presentation.get("weight") or "small"),
            title=str(record.get("title") or ""),
            summary=str(record.get("body") or ""),
            truth_class=str(record.get("truth_class") or "canonical"),
            audience_scope=str(record.get("audience_scope") or "public"),
            state="new",
            accent_role="network",
            asset_id=asset_id,
            asset_family=asset_family,
            registry=registry,
            primary_stat="OLLAMA ENRICHED",
            action_type=action,
            action_target=target,
            action_payload_ref=str(record.get("cta_ref") or ""),
            published_at=str(record.get("published_at") or result.get("generated_at") or ""),
        )
    result["entries"] = [
        replacements.get(str(item.get("content", {}).get("news_id") or ""), item)
        for item in existing
    ][:bounded_limit]
    protocol = dict(result.get("protocol_status") or {})
    if replacements:
        protocol.update({
            "source": "canonical-publication-read-model",
            "ollama_used": True,
            "publication_enabled": True,
        })
    result["protocol_status"] = protocol
    stats = list(result.get("global_stats") or [])
    for item in stats:
        if item.get("key") == "entries":
            item["value"] = len(result["entries"])
        elif item.get("key") == "sources":
            item["value"] = len({entry.get("content", {}).get("source") for entry in result["entries"]})
    result["global_stats"] = stats
    result["state_version"] = _stable_hash(
        SCHEMA_VERSION,
        json.dumps(result["entries"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
    )
    diagnostics = dict(result.get("diagnostics") or {})
    diagnostics["entry_count"] = len(result["entries"])
    diagnostics["published_entry_count"] = len(replacements)
    diagnostics["publication_slot_ids"] = list(replacements)
    result["diagnostics"] = diagnostics
    return result
