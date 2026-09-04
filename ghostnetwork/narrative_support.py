from __future__ import annotations

import hashlib
import json
from pathlib import Path
from string import Formatter

try:
    import yaml
except ImportError:  # pragma: no cover - reported by verify() on the host
    yaml = None

from .llm.semantic_input import model_visible_semantic_fact


SUPPORT_CONTRACT_VERSION = "chaos-narrative-support-v1"
REQUIRED_ENDGAME_FALLBACK_FAMILIES = (
    "machine_online",
    "cycle_locked",
    "signal_sent",
    "version_changed",
    "stabilization_started",
    "cycle_activated",
)
REQUIRED_ENDGAME_FALLBACK_MEDIA = ("blacknet", "googleplex_news")
DEFAULT_SUPPORT_PATH = (
    Path(__file__).resolve().parent / "llm" / "narrative_support.v1.yaml"
)


class NarrativeSupportLayer:
    """Deterministic, audience-safe fallback after model validation fails."""

    def __init__(self, path=None):
        self.path = Path(path) if path else DEFAULT_SUPPORT_PATH
        self.config = {}
        self.errors = []
        self._load()

    def _load(self):
        if yaml is None:
            self.errors.append("narrative_support_yaml_unavailable")
            return
        try:
            loaded = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, yaml.YAMLError):
            self.errors.append("narrative_support_config_invalid")
            return
        if not isinstance(loaded, dict):
            self.errors.append("narrative_support_config_invalid")
            return
        if loaded.get("contract_version") != SUPPORT_CONTRACT_VERSION:
            self.errors.append("narrative_support_contract_mismatch")
        versions = loaded.get("enabled_prompt_versions")
        fallbacks = loaded.get("fallbacks")
        if not isinstance(versions, list) or not all(
            isinstance(item, str) and item.strip() for item in versions
        ):
            self.errors.append("narrative_support_prompt_versions_invalid")
        if not isinstance(fallbacks, dict):
            self.errors.append("narrative_support_fallbacks_invalid")
        if not self.errors:
            self.config = loaded

    def verify(self):
        fallbacks = self.config.get("fallbacks") or {}
        variants = 0
        for families in fallbacks.values():
            if not isinstance(families, dict):
                continue
            for audiences in families.values():
                if not isinstance(audiences, dict):
                    continue
                for definition in audiences.values():
                    if isinstance(definition, dict):
                        variants += sum(
                            len(definition.get(field) or [])
                            for field in ("title", "body")
                            if isinstance(definition.get(field), list)
                        )
        missing_required_endgame_routes = []
        for medium in REQUIRED_ENDGAME_FALLBACK_MEDIA:
            for event_family in REQUIRED_ENDGAME_FALLBACK_FAMILIES:
                definition = self._definition(medium, event_family, "public")
                if not isinstance(definition, dict) or any(
                    not isinstance(definition.get(field), list)
                    or not definition.get(field)
                    for field in ("title", "body")
                ):
                    missing_required_endgame_routes.append(
                        f"{medium}:{event_family}:public"
                    )
        errors = list(self.errors)
        errors.extend(
            f"narrative_support_required_endgame_fallback_missing:{route}"
            for route in missing_required_endgame_routes
        )
        return {
            "ok": not errors,
            "contract_version": self.config.get("contract_version") or "",
            "errors": errors,
            "variants": variants,
            "required_endgame_routes": (
                len(REQUIRED_ENDGAME_FALLBACK_MEDIA)
                * len(REQUIRED_ENDGAME_FALLBACK_FAMILIES)
            ),
            "missing_required_endgame_routes": missing_required_endgame_routes,
        }

    @staticmethod
    def _model_input(package):
        try:
            return json.loads(package["messages"][1]["content"])
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _context(package, model_input):
        semantic_facts = model_input.get("semantic_facts") or []
        first_model_fact = semantic_facts[0] if semantic_facts else {}
        context = {
            "statement": str(first_model_fact.get("statement") or "").strip(),
            "required_phrase": str(
                first_model_fact.get("required_phrase") or ""
            ).strip(),
        }
        source_facts = package.get("source_facts") or ()
        if source_facts and isinstance(source_facts[0], dict):
            visible = model_visible_semantic_fact(source_facts[0], "f01")
            for entity in visible.get("entities") or ():
                if not isinstance(entity, dict):
                    continue
                kind = str(entity.get("kind") or "").strip()
                label = str(entity.get("label") or "").strip()
                if kind == "target" and label:
                    context["location"] = label
                elif kind == "part" and label:
                    context["part_name"] = label
            location = visible.get("location")
            if isinstance(location, dict):
                for key in ("region", "city", "country"):
                    value = str(location.get(key) or "").strip()
                    if value:
                        context.setdefault("region", value)
                        context[f"location_{key}"] = value
        context.setdefault("location", context.get("region") or "")
        return context

    @staticmethod
    def _render_variant(variants, context, seed):
        if not isinstance(variants, list) or not variants:
            raise ValueError("narrative_support_variants_missing")
        index = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16], 16)
        template = variants[index % len(variants)]
        if not isinstance(template, str) or not template.strip():
            raise ValueError("narrative_support_template_invalid")
        fields = {
            field_name
            for _, field_name, format_spec, conversion in Formatter().parse(template)
            if field_name and not format_spec and not conversion
        }
        if any(not context.get(field) for field in fields):
            raise ValueError("narrative_support_value_missing")
        return template.format_map(context)

    def _definition(self, medium, event_family, audience):
        audiences = (
            ((self.config.get("fallbacks") or {}).get(medium) or {})
            .get(event_family, {})
        )
        if not isinstance(audiences, dict):
            return None
        # A public template contains the least audience knowledge and is safe
        # to reuse for clan/owner when no richer scoped variant exists.
        return audiences.get(audience) or audiences.get("public")

    @staticmethod
    def _payload(package, definition, title, body):
        aliases = sorted((package.get("fact_ref_map") or {}).keys())
        if not aliases:
            raise ValueError("narrative_support_fact_ref_missing")
        payload = {
            "title": title,
            "body": body,
            "tone": str(definition.get("tone") or "warning"),
            "fact_refs": [aliases[0]],
            "cta_ref": None,
        }
        properties = (package.get("format") or {}).get("properties") or {}
        if "asset_ref" in properties:
            assets = package.get("allowed_asset_refs") or ()
            if not assets:
                raise ValueError("narrative_support_asset_ref_missing")
            payload["asset_ref"] = assets[0]
        return payload

    def apply(self, task, package, model_validation, validate):
        if self.errors or (model_validation or {}).get("status") == "accepted":
            return None
        prompt_version = str(task.get("prompt_version") or "")
        if prompt_version not in set(self.config.get("enabled_prompt_versions") or ()):
            return None
        model_input = self._model_input(package)
        medium = str(model_input.get("medium") or task.get("target_medium") or "")
        event_family = str(model_input.get("event_family") or "")
        audience = str((model_input.get("audience") or {}).get("scope") or "public")
        definition = self._definition(medium, event_family, audience)
        if not isinstance(definition, dict):
            return None
        context = self._context(package, model_input)
        seed = "\0".join((
            str(task.get("source_event_id") or ""), medium, event_family, audience,
        ))
        try:
            fallback_title = self._render_variant(
                definition.get("title"), context, seed + "\0title"
            )
            fallback_body = self._render_variant(
                definition.get("body"), context, seed + "\0body"
            )
        except (KeyError, ValueError):
            return None

        model_output = (
            model_validation.get("output")
            if isinstance(model_validation.get("output"), dict)
            else {}
        )
        variants = []
        if medium == "googleplex_news":
            if model_output.get("body"):
                variants.append(("title", fallback_title, model_output["body"]))
            if model_output.get("title"):
                variants.append(("body", model_output["title"], fallback_body))
        variants.append(("full", fallback_title, fallback_body))

        for mode, title, body in variants:
            try:
                payload = self._payload(package, definition, title, body)
            except ValueError:
                return None
            content = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            validation = validate(content, package)
            if validation.get("status") == "accepted":
                return {
                    "mode": mode,
                    "content": content,
                    "validation": validation,
                    "model_errors": list(model_validation.get("errors") or ()),
                }
        return None
