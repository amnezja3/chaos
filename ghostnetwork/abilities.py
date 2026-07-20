from __future__ import annotations

import copy
import hashlib
import json

from .catalog import get_catalog, normalize_ghostnetwork_profile_identity
from .module_state import GhostModuleStateService


ACTIVE_MODULE_STATE = "active"
DEFAULT_PART_LOSS_POLICY = "terminate_on_part_loss"
ABILITY_MECHANICS_STATUSES = {
    "catalog_only",
    "passive_active",
    "active_command",
    "event_reaction",
    "implemented",
    "disabled",
}


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _json_hash(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _player_id(player_context):
    player_context = player_context if isinstance(player_context, dict) else {}
    return _clean(
        player_context.get("player_id")
        or player_context.get("username")
        or player_context.get("login")
        or player_context.get("id")
    )


def _cycle_is_open(cycle):
    cycle = cycle if isinstance(cycle, dict) else {}
    status = _clean(cycle.get("status"))
    if not cycle:
        return False
    if status == "closed":
        return False
    if _clean(cycle.get("closed_at")) or _clean(cycle.get("transmitted_at")):
        return False
    return True


def _ability_mechanics_status(effect_type):
    effect_type = _clean(effect_type)
    if effect_type in {
        "market_demand_preview",
        "hack_threshold_modifier",
        "territory_information_mask",
        "operation_alert_delay",
        "scan_detail_modifier",
    }:
        return "passive_active"
    if effect_type in {
        "territory_attack_window",
        "operation_probability_zone",
        "security_weakness_reveal",
        "full_disclosure",
        "clan_operation_beacon",
        "false_activity_marker",
        "territory_stability_damage",
        "false_tracking_traces",
        "territory_connection_disruption",
        "territory_integrity_scan",
        "territory_defense_layer",
        "territory_repair",
        "trusted_access_corridor",
        "operation_quarantine",
    }:
        return "active_command"
    if effect_type in {"neighbor_security_reduction", "attack_reflection"}:
        return "event_reaction"
    return "catalog_only"


def _adapter_code_for_effect(effect_type):
    effect_type = _clean(effect_type)
    if effect_type == "market_demand_preview":
        return "market"
    if effect_type in {
        "hack_threshold_modifier",
        "scan_detail_modifier",
        "security_weakness_reveal",
        "neighbor_security_reduction",
    }:
        return "hack"
    if effect_type in {
        "territory_defense_layer",
        "territory_repair",
        "territory_stability_damage",
        "territory_attack_window",
        "territory_connection_disruption",
        "trusted_access_corridor",
        "attack_reflection",
    }:
        return "territory"
    if effect_type in {"operation_alert_delay", "operation_probability_zone", "operation_quarantine"}:
        return "operation"
    if effect_type in {"territory_information_mask", "false_activity_marker", "false_tracking_traces"}:
        return "visibility"
    if effect_type == "clan_operation_beacon":
        return "cyberner"
    return "generic"


class GhostAbilityAdapter:
    adapter_code = "generic"

    def collect_effects(self, active_effects, context):
        return list(active_effects or [])

    def apply_modifier(self, effect, context, value):
        return value


class GhostMarketAbilityAdapter(GhostAbilityAdapter):
    adapter_code = "market"


class GhostHackAbilityAdapter(GhostAbilityAdapter):
    adapter_code = "hack"


class GhostTerritoryAbilityAdapter(GhostAbilityAdapter):
    adapter_code = "territory"


class GhostOperationAbilityAdapter(GhostAbilityAdapter):
    adapter_code = "operation"


class GhostVisibilityAbilityAdapter(GhostAbilityAdapter):
    adapter_code = "visibility"


class GhostCybernerAbilityAdapter(GhostAbilityAdapter):
    adapter_code = "cyberner"


def default_ability_adapters():
    adapters = [
        GhostMarketAbilityAdapter(),
        GhostHackAbilityAdapter(),
        GhostTerritoryAbilityAdapter(),
        GhostOperationAbilityAdapter(),
        GhostVisibilityAbilityAdapter(),
        GhostCybernerAbilityAdapter(),
        GhostAbilityAdapter(),
    ]
    return {adapter.adapter_code: adapter for adapter in adapters}


class GhostAbilityRegistry:
    """Central read-only registry for GhostNetwork profession abilities.

    The registry never stores active powers in player profiles. It derives
    access from catalog identity plus the current module state of the matching
    GhostNetwork part.
    """

    def __init__(self, catalog=None, repository=None, module_state_service=None, adapters=None):
        self.catalog = copy.deepcopy(catalog or get_catalog())
        self.repository = repository
        self.modules = module_state_service or (GhostModuleStateService(repository) if repository else None)
        self.adapters = adapters or default_ability_adapters()
        self._effects = {}
        self._effects_by_clan = {}
        self._effects_by_profession = {}
        self._cache = {}
        self._load_catalog_effects()

    def _load_catalog_effects(self):
        abilities = {item["ability_code"]: item for item in self.catalog.get("abilities", [])}
        parts = {item["part_code"]: item for item in self.catalog.get("parts", [])}
        for profession in self.catalog.get("professions", []):
            part = parts.get(profession.get("part_code")) or {}
            ability = abilities.get(profession.get("ability_code")) or {}
            effect = {
                "ability_code": _clean(ability.get("ability_code") or profession.get("ability_code")),
                "ability_name": _clean(ability.get("name")),
                "ability_description": _clean(ability.get("description")),
                "effect_type": _clean(ability.get("effect_type")),
                "activation_scope": _clean(ability.get("activation_scope"), "ghostnetwork_part"),
                "target_scope": _clean(ability.get("target_scope"), "ghostnetwork"),
                "requires_active_part": bool(ability.get("requires_active_part", True)),
                "mechanics_status": _ability_mechanics_status(ability.get("effect_type")),
                "adapter_code": _adapter_code_for_effect(ability.get("effect_type")),
                "part_loss_policy": DEFAULT_PART_LOSS_POLICY,
                "cooldown_seconds": 0,
                "max_active_instances": 0,
                "clan_code": _clean(profession.get("clan_code")),
                "machine_code": _clean(profession.get("machine_code")),
                "profession_code": _clean(profession.get("code")),
                "profession_name": _clean(profession.get("name")),
                "part_code": _clean(profession.get("part_code")),
                "part_name": _clean(part.get("name")),
                "sort_order": int(profession.get("sort_order") or 0),
            }
            self.register(effect)

    def register(self, effect):
        effect = copy.deepcopy(effect if isinstance(effect, dict) else {})
        ability_code = _clean(effect.get("ability_code"))
        if not ability_code:
            raise ValueError("Ghost ability effect requires ability_code")
        mechanics_status = _clean(effect.get("mechanics_status"), "catalog_only")
        if mechanics_status not in ABILITY_MECHANICS_STATUSES:
            raise ValueError(f"Invalid Ghost ability mechanics_status: {mechanics_status}")
        effect["mechanics_status"] = mechanics_status
        effect.setdefault("part_loss_policy", DEFAULT_PART_LOSS_POLICY)
        effect.setdefault("adapter_code", _adapter_code_for_effect(effect.get("effect_type")))
        effect["contract_checksum"] = _json_hash({
            "ability_code": ability_code,
            "effect_type": effect.get("effect_type"),
            "part_code": effect.get("part_code"),
            "profession_code": effect.get("profession_code"),
            "mechanics_status": effect.get("mechanics_status"),
            "part_loss_policy": effect.get("part_loss_policy"),
        })
        self._effects[ability_code] = effect
        self._effects_by_clan.setdefault(_clean(effect.get("clan_code")), []).append(effect)
        self._effects_by_profession[_clean(effect.get("profession_code"))] = effect
        self.clear_cache()
        return copy.deepcopy(effect)

    def clear_cache(self):
        self._cache = {}

    def get(self, ability_code):
        effect = self._effects.get(_clean(ability_code))
        return copy.deepcopy(effect) if effect else None

    def list_for_clan(self, clan_code):
        effects = self._effects_by_clan.get(_clean(clan_code), [])
        return [copy.deepcopy(effect) for effect in sorted(effects, key=lambda item: item.get("sort_order") or 0)]

    def _snapshot_from_context(self, player_context):
        player_context = player_context if isinstance(player_context, dict) else {}
        snapshot = player_context.get("cycle_snapshot") or player_context.get("ghostnetwork_snapshot")
        if isinstance(snapshot, dict):
            return copy.deepcopy(snapshot)
        if not self.repository:
            return {"cycle": None, "parts": [], "state_version": 0}
        active = self.repository.get_active_cycle()
        if not active:
            return {"cycle": None, "parts": [], "state_version": 0}
        return self.repository.build_internal_snapshot(active["cycle_id"])

    def _resolve_part_state(self, part):
        part = part if isinstance(part, dict) else {}
        if part.get("module_state"):
            return part
        if self.modules:
            return self.modules.resolve_part_module_state(part)
        return part

    def _matching_part_state(self, snapshot, effect):
        parts = snapshot.get("parts") if isinstance(snapshot, dict) else []
        for part in parts or []:
            state = self._resolve_part_state(part)
            if _clean(state.get("part_code")) == _clean(effect.get("part_code")):
                return state
        return None

    def _cache_key(self, identity, snapshot):
        cycle = snapshot.get("cycle") if isinstance(snapshot, dict) else {}
        return (
            _clean((cycle or {}).get("cycle_id")),
            int(snapshot.get("state_version") or (cycle or {}).get("state_version") or 0),
            _player_id(identity),
            _clean(identity.get("clan_code")),
            _clean(identity.get("profession_code")),
        )

    def resolve_player_abilities(self, player_context):
        player_context = player_context if isinstance(player_context, dict) else {}
        identity = normalize_ghostnetwork_profile_identity(player_context)
        identity["player_id"] = _player_id(player_context)
        snapshot = self._snapshot_from_context(player_context)
        cycle = snapshot.get("cycle") if isinstance(snapshot, dict) else {}
        cache_key = self._cache_key(identity, snapshot)
        if cache_key in self._cache:
            return copy.deepcopy(self._cache[cache_key])

        effect = self._effects_by_profession.get(_clean(identity.get("profession_code")))
        cycle_open = _cycle_is_open(cycle)
        state = self._matching_part_state(snapshot, effect) if effect else None
        active = bool(
            identity.get("catalog_valid")
            and effect
            and cycle_open
            and _clean(effect.get("clan_code")) == _clean(identity.get("clan_code"))
            and state
            and _clean(state.get("module_state")) == ACTIVE_MODULE_STATE
        )
        reason = "active"
        if not identity.get("catalog_valid"):
            reason = "invalid_player_identity"
        elif not effect:
            reason = "missing_profession_effect"
        elif not cycle_open:
            reason = "cycle_closed_or_transmitted"
        elif not state:
            reason = "matching_part_missing"
        elif _clean(state.get("module_state")) != ACTIVE_MODULE_STATE:
            reason = "module_not_active"

        ability = None
        if effect:
            ability = copy.deepcopy(effect)
            ability.update({
                "active": active,
                "activation_reason": reason,
                "cycle_id": _clean((cycle or {}).get("cycle_id")),
                "state_version": int(snapshot.get("state_version") or (cycle or {}).get("state_version") or 0),
                "source_part_id": _clean((state or {}).get("part_id")),
                "source_part_code": _clean((state or {}).get("part_code") or effect.get("part_code")),
                "module_state": _clean((state or {}).get("module_state")),
                "conflict_state": _clean((state or {}).get("conflict_state"), "none"),
            })

        result = {
            "ok": True,
            "player_id": identity.get("player_id") or "",
            "clan_code": identity.get("clan_code") or "",
            "profession_code": identity.get("profession_code") or "",
            "catalog_valid": bool(identity.get("catalog_valid")),
            "validation_errors": list(identity.get("validation_errors") or []),
            "cycle_id": _clean((cycle or {}).get("cycle_id")),
            "state_version": int(snapshot.get("state_version") or (cycle or {}).get("state_version") or 0),
            "cache_key": ":".join(str(item) for item in cache_key),
            "ability": ability,
            "abilities": [ability] if ability else [],
            "active_abilities": [ability] if ability and active else [],
        }
        self._cache[cache_key] = copy.deepcopy(result)
        return result

    def is_ability_active(self, player_context, ability_code):
        resolved = self.resolve_player_abilities(player_context)
        return any(
            item.get("ability_code") == _clean(ability_code) and item.get("active")
            for item in resolved.get("active_abilities") or []
        )

    def collect_effects(self, effect_type, context):
        context = context if isinstance(context, dict) else {}
        player_context = context.get("player_context") if isinstance(context.get("player_context"), dict) else context
        resolved = self.resolve_player_abilities(player_context)
        effects = [
            effect for effect in resolved.get("active_abilities") or []
            if _clean(effect.get("effect_type")) == _clean(effect_type)
        ]
        if not effects:
            return []
        adapter_code = effects[0].get("adapter_code") or "generic"
        adapter = self.adapters.get(adapter_code) or self.adapters.get("generic") or GhostAbilityAdapter()
        return adapter.collect_effects(effects, context)

    def apply_modifier(self, effect_type, context, value):
        modified = value
        for effect in self.collect_effects(effect_type, context):
            adapter = self.adapters.get(effect.get("adapter_code")) or self.adapters.get("generic") or GhostAbilityAdapter()
            modified = adapter.apply_modifier(effect, context, modified)
        return modified

