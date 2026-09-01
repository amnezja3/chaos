"""Code-owned Googleplex Home editorial contracts and Stage II assignments.

This module accepts bounded canonical projections only.  It must never import
the web application or read a player profile.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

from .ollama_policy import assign_ollama_task_policy
from .repository import NARRATIVE_TASK_PROCESSOR, NARRATIVE_TASK_SCHEMA_VERSION, _clean, _hash_id


GOOGLEPLEX_EDITORIAL_SOURCE_SCOPE = "googleplex_editorial"

ASSET_ROLE_REFS = {
    "broadcast": "gp_fallback_network",
    "intercept": "gp_fallback_network",
    "market": "gp_fallback_market",
    "scanner": "gp_fallback_tool",
    "security": "gp_fallback_system",
    "network": "gp_fallback_network",
    "operations": "gp_fallback_system",
    "data": "gp_fallback_package",
    "storage": "gp_fallback_storage",
    "clans": "gp_fallback_clan",
    "neutral": "gp_fallback_stamp",
}

GOOGLEPLEX_HOME_SLOT_REGISTRY = {
    "gp-home-world-grid": {
        "content_kind": "world_dispatch", "presentation_weight": "hero",
        "llm_refresh_enabled": True, "allowed_task_variants": ("googleplex_world_dispatch",),
        "title_owner": "model", "title_chars": 64, "body_chars": 220,
        "body_words": 42, "estimated_lines": 5,
        "allowed_asset_roles": ("neutral", "network"),
        "fallback_asset_ref": "gp_scene_world_neutral_01",
        "minimum_refresh_seconds": 0,
    },
    "gp-home-blacknet": {
        "content_kind": "navigation_promo", "presentation_weight": "large",
        "llm_refresh_enabled": True, "allowed_task_variants": ("googleplex_navigation_promo",),
        "title_owner": "model", "title_chars": 48, "body_chars": 130,
        "body_words": 24, "estimated_lines": 4,
        "allowed_asset_roles": ("intercept", "broadcast", "network"),
        "fallback_asset_ref": "gp_fallback_network",
        "fixed_action": {"cta_action": "open_blacknet", "payload": {"target_id": "world"}},
        "minimum_refresh_seconds": 43200,
        "source": {"ref": "capability:blacknet", "title": "BlackNet", "description": "Publiczny feed przechwyconych sygnalow swiata CHAOS."},
    },
    "gp-home-featured": {
        "content_kind": "product_promo", "presentation_weight": "medium",
        "llm_refresh_enabled": True, "allowed_task_variants": ("googleplex_product_promo",),
        "title_owner": "backend", "title_chars": 32, "body_chars": 90,
        "body_words": 18, "estimated_lines": 3,
        "allowed_asset_roles": ("scanner", "security", "network", "market"),
        "fallback_asset_ref": "gp_fallback_tool", "minimum_refresh_seconds": 21600,
    },
    "gp-home-operations": {
        "content_kind": "capability_card", "presentation_weight": "small",
        "llm_refresh_enabled": True, "allowed_task_variants": ("googleplex_capability_card_refresh",),
        "title_owner": "model", "title_chars": 32, "body_chars": 90,
        "body_words": 18, "estimated_lines": 3,
        "allowed_asset_roles": ("operations", "security"),
        "fallback_asset_ref": "gp_fallback_system",
        "fixed_action": {"cta_action": "open_operation", "payload": {"target_id": "operation-center"}},
        "minimum_refresh_seconds": 86400,
        "source": {"ref": "capability:operations", "title": "Centrum Operacji", "description": "Pozwala sprawdzac aktywne i historyczne operacje."},
    },
    "gp-home-packages": {
        "content_kind": "capability_card", "presentation_weight": "small",
        "llm_refresh_enabled": True, "allowed_task_variants": ("googleplex_capability_card_refresh",),
        "title_owner": "model", "title_chars": 32, "body_chars": 90,
        "body_words": 18, "estimated_lines": 3,
        "allowed_asset_roles": ("data", "market"),
        "fallback_asset_ref": "gp_fallback_package", "fixed_action": {},
        "minimum_refresh_seconds": 86400,
        "source": {"ref": "capability:data", "title": "Pakiety danych", "description": "File Manager pokazuje canonical pliki i pakiety danych."},
    },
    "gp-home-storage": {
        "content_kind": "capability_card", "presentation_weight": "small",
        "llm_refresh_enabled": True, "allowed_task_variants": ("googleplex_capability_card_refresh",),
        "title_owner": "model", "title_chars": 32, "body_chars": 90,
        "body_words": 18, "estimated_lines": 3,
        "allowed_asset_roles": ("storage", "security"),
        "fallback_asset_ref": "gp_fallback_storage", "fixed_action": {},
        "minimum_refresh_seconds": 86400,
        "source": {"ref": "capability:storage", "title": "Pamiec operatora", "description": "Przestrzen przechowuje dane bez ujawniania profilu operatora."},
    },
    "gp-home-clans": {
        "content_kind": "capability_card", "presentation_weight": "small",
        "llm_refresh_enabled": True, "allowed_task_variants": ("googleplex_capability_card_refresh",),
        "title_owner": "model", "title_chars": 32, "body_chars": 90,
        "body_words": 18, "estimated_lines": 3,
        "allowed_asset_roles": ("clans", "network"),
        "fallback_asset_ref": "gp_fallback_clan", "fixed_action": {},
        "minimum_refresh_seconds": 86400,
        "source": {"ref": "capability:clans", "title": "Kanaly klanowe", "description": "Kanaly klanowe lacza operatorow w ograniczonym zasiegu."},
    },
    "gp-home-integrity": {"llm_refresh_enabled": False},
    "gp-home-protocol": {"llm_refresh_enabled": False},
}


def get_googleplex_slot_contract(slot_id):
    contract = GOOGLEPLEX_HOME_SLOT_REGISTRY.get(str(slot_id or "").strip())
    return dict(contract) if isinstance(contract, dict) else None


def _iso_datetime(value):
    try:
        parsed = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _product_price(product):
    for field in ("price_hc", "price", "cost", "hc_price"):
        if product.get(field) in (None, ""):
            continue
        try:
            value = int(product.get(field) or 0)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            return value
    return 0


class GoogleplexEditorialProducer:
    """Create at most one due Stage II assignment from bounded inputs."""

    STAGE_TWO_SLOTS = (
        "gp-home-featured", "gp-home-blacknet", "gp-home-operations",
        "gp-home-packages", "gp-home-storage", "gp-home-clans",
    )

    def __init__(self, repository):
        self.repository = repository

    def _is_due(self, slot_id, now):
        if self.repository.has_open_narrative_slot_assignment("googleplex_news", slot_id):
            return False
        state = self.repository.get_narrative_slot_state("googleplex_news", slot_id)
        if not state:
            return True
        next_refresh = _iso_datetime(state.get("next_refresh_at"))
        if next_refresh:
            return next_refresh <= now
        last_refresh = _iso_datetime(state.get("last_refreshed_at"))
        contract = get_googleplex_slot_contract(slot_id) or {}
        cooldown = max(0, int(contract.get("minimum_refresh_seconds") or 0))
        if not last_refresh:
            return True
        return (now - last_refresh).total_seconds() >= cooldown

    @staticmethod
    def _available_products(catalog):
        products = []
        for raw in catalog or ():
            if not isinstance(raw, dict):
                continue
            product_id = _clean(raw.get("id"))
            name = _clean(raw.get("name"))
            if not product_id or not name or raw.get("published", True) is not True:
                continue
            if raw.get("available") is False or raw.get("disabled") is True:
                continue
            products.append({
                "product_id": product_id,
                "name": name,
                "description": " ".join(str(raw.get("description") or "").split())[:240],
                "category": _clean(raw.get("category") or raw.get("type"))[:48],
                "price_hc": _product_price(raw),
                "downloads": max(0, int(raw.get("downloads") or 0)),
            })
        products.sort(key=lambda item: (-item["downloads"], item["price_hc"], item["name"].casefold(), item["product_id"]))
        return products

    def _choose_product(self, catalog):
        products = self._available_products(catalog)
        if not products:
            return None
        state = self.repository.get_narrative_slot_state("googleplex_news", "gp-home-featured") or {}
        previous = _clean(state.get("active_source_ref"))
        alternative = next((item for item in products if f"googleplex_product:{item['product_id']}" != previous), None)
        return alternative or products[0]

    def _enqueue(self, slot_id, fact, *, variant, content_kind, fixed_action, now):
        contract = get_googleplex_slot_contract(slot_id) or {}
        state = self.repository.get_narrative_slot_state("googleplex_news", slot_id) or {}
        expected_version = int(state.get("version") or 0)
        creative_epoch = int(state.get("creative_epoch") or 0) + 1
        source_ref = _clean(fact.get("fact_id"))
        source_version = hashlib.sha1(json.dumps(
            fact, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")).hexdigest()[:16]
        receipt = _hash_id("googleplex_editorial", slot_id, source_ref, source_version, creative_epoch)
        roles = list(contract.get("allowed_asset_roles") or ())[:8]
        role_map = {role: ASSET_ROLE_REFS[role] for role in roles if role in ASSET_ROLE_REFS}
        editorial_contract = {
            key: contract.get(key) for key in (
                "presentation_weight", "title_owner", "title_chars", "body_chars",
                "body_words", "estimated_lines", "minimum_refresh_seconds",
                "fallback_asset_ref",
            )
        }
        editorial_contract["asset_role_map"] = role_map
        canonical_title = _clean(fact.get("product_name")) if contract.get("title_owner") == "backend" else ""
        narrative_intent = (
            "product_benefit_promo"
            if content_kind == "product_promo"
            else "capability_invitation"
        )
        task = self.repository.enqueue_narrative_task(assign_ollama_task_policy({
            "schema_version": NARRATIVE_TASK_SCHEMA_VERSION,
            "source_scope": GOOGLEPLEX_EDITORIAL_SOURCE_SCOPE,
            "source_receipt_id": receipt,
            "processor": NARRATIVE_TASK_PROCESSOR,
            "target_medium": "googleplex_news",
            "audience_scope": "public",
            "truth_class": "canonical",
            "truth_class_policy": "canonical",
            "facts": [fact], "allowed_actions": [],
            "canon_version": "googleplex-editorial-stage-two-v1",
            "task_variant": variant, "content_kind": content_kind,
            "narrative_intent": narrative_intent,
            "presentation_slot": slot_id,
            "selected_source_ref": source_ref,
            "selected_source_version": source_version,
            "creative_epoch": creative_epoch,
            "expected_slot_version": expected_version,
            "fixed_action": fixed_action or {},
            "editorial_contract": {**editorial_contract, "canonical_title": canonical_title},
            "allowed_asset_roles": roles,
            "priority": 40 if content_kind == "product_promo" else 20,
            "validation": {
                "ok": True, "producer": "googleplex_editorial_stage_two",
                "narrative_intent": narrative_intent,
                "selected_source_ref": source_ref, "selected_source_version": source_version,
                "presentation_slot": slot_id, "content_kind": content_kind,
                "creative_epoch": creative_epoch, "expected_slot_version": expected_version,
                "fixed_action": fixed_action or {},
                "editorial_contract": {**editorial_contract, "canonical_title": canonical_title},
                "allowed_asset_roles": roles,
                "profile_full_read": 0, "profile_full_write": 0, "profile_bytes": 0,
            },
        }))
        return {"ok": True, "status": "deduplicated" if task.get("idempotent") else "created", "task": task, "receipt_id": receipt}

    def enqueue_product(self, catalog, *, now):
        product = self._choose_product(catalog)
        if not product:
            return {"ok": True, "status": "source_unavailable", "task": None}
        fact = {
            "fact_id": f"googleplex_product:{product['product_id']}",
            "truth_class": "canonical", "fact_type": "googleplex_product",
            "product_name": product["name"], "title": product["name"],
            "description": product["description"], "category": product["category"],
            "price_hc": product["price_hc"], "downloads": product["downloads"],
        }
        action = {"cta_action": "open_googleplex_search", "payload": {
            "target_id": product["product_id"], "query": product["name"],
            "product_id": product["product_id"], "product_name": product["name"],
            "price_hc": product["price_hc"], "downloads": product["downloads"],
        }}
        return self._enqueue("gp-home-featured", fact, variant="googleplex_product_promo", content_kind="product_promo", fixed_action=action, now=now)

    def enqueue_evergreen(self, slot_id, *, now):
        contract = get_googleplex_slot_contract(slot_id) or {}
        source = contract.get("source") if isinstance(contract.get("source"), dict) else {}
        if not source:
            return {"ok": True, "status": "source_unavailable", "task": None}
        fact = {
            "fact_id": _clean(source.get("ref")), "truth_class": "canonical",
            "fact_type": "googleplex_capability", "title": _clean(source.get("title")),
            "description": _clean(source.get("description")),
            "category": "navigation" if slot_id == "gp-home-blacknet" else "capability",
        }
        variant = "googleplex_navigation_promo" if slot_id == "gp-home-blacknet" else "googleplex_capability_card_refresh"
        return self._enqueue(slot_id, fact, variant=variant, content_kind=contract.get("content_kind") or "capability_card", fixed_action=contract.get("fixed_action") or {}, now=now)

    def enqueue_next(self, catalog, *, now=None):
        now = now if isinstance(now, datetime) else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        for slot_id in self.STAGE_TWO_SLOTS:
            contract = get_googleplex_slot_contract(slot_id) or {}
            if contract.get("llm_refresh_enabled") is not True or not self._is_due(slot_id, now):
                continue
            if slot_id == "gp-home-featured":
                return self.enqueue_product(catalog, now=now)
            return self.enqueue_evergreen(slot_id, now=now)
        return {"ok": True, "status": "no_change", "task": None}
