from __future__ import annotations

import hashlib

from .catalog import get_catalog
from .module_state import GhostModuleStateService
from .part_assets import CLASSIFIED_MARKER_ASSET_URL, part_visual_asset_contract


VISIBILITY_VERSION = "ghost-visibility-v2"

FULL_VISIBILITY_LEVELS = {"full_public", "full_owner", "full_clan"}

RELATION_TO_VISIBILITY = {
    "public_neutral": "full_public",
    "self_foreign_blocked": "full_owner",
    "self_own_active": "full_owner",
    "clan_own_active": "full_clan",
    "foreign_blocked": "contained_hidden",
    "foreign_active": "active_foreign",
}

RELATION_TO_LOCATION_VISIBILITY = {
    "public_neutral": "exact",
    "self_foreign_blocked": "exact",
    "self_own_active": "exact",
    "clan_own_active": "exact",
    "foreign_blocked": "territory_only",
    "foreign_active": "exact",
}


def _clean(value, default=""):
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _public_entity_id(cycle_id, entity_id):
    raw = f"{_clean(cycle_id)}:{_clean(entity_id)}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"ghost-node:{digest}"


def _public_connection_id(cycle_id, connection_id):
    raw = f"{_clean(cycle_id)}:{_clean(connection_id)}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    return f"ghost-link:{digest}"


def _viewer_value(viewer, *keys):
    if not isinstance(viewer, dict):
        return ""
    for key in keys:
        value = _clean(viewer.get(key))
        if value:
            return value
    return ""


class GhostVisibilityService:
    """Safe GhostNetwork projection builder.

    This service is the only place where raw GhostNetwork part fields are
    filtered for player, clan, public media and internal audiences. It does not
    mutate domain state and does not depend on frontend-side hiding.
    """

    def __init__(self, repository=None, module_state_service=None):
        self.repository = repository
        self.modules = module_state_service or GhostModuleStateService(repository=repository)
        catalog = get_catalog()
        self.clans_by_code = {item["code"]: item for item in catalog.get("clans", [])}
        self.machines_by_code = {item["code"]: item for item in catalog.get("machines", [])}
        self.parts_by_code = {item["part_code"]: item for item in catalog.get("parts", [])}
        self.professions_by_code = {item["code"]: item for item in catalog.get("professions", [])}
        self.abilities_by_code = {item["ability_code"]: item for item in catalog.get("abilities", [])}

    def build_viewer_context(self, viewer=None):
        if viewer is None:
            viewer = {"audience_scope": "internal"}
        if isinstance(viewer, str):
            scope = "internal" if viewer in {"admin", "internal", "system"} else "player"
            viewer = {"viewer_id": viewer, "audience_scope": scope, "is_admin": viewer == "admin"}
        elif not isinstance(viewer, dict):
            viewer = {}

        viewer_id = _viewer_value(viewer, "viewer_id", "player_id", "username", "login", "id")
        viewer_clan = _viewer_value(viewer, "viewer_clan", "clan_code", "ghost_clan", "clan")
        viewer_profession = _viewer_value(
            viewer,
            "viewer_profession",
            "profession_code",
            "ghost_profession",
            "profession",
        )
        is_admin = _as_bool(viewer.get("is_admin") or viewer.get("admin"))
        audience_scope = _clean(viewer.get("audience_scope") or viewer.get("scope"))
        if not audience_scope:
            audience_scope = "internal" if is_admin else ("player" if viewer_id else "public")
        if is_admin:
            audience_scope = "internal"
        is_authenticated = _as_bool(viewer.get("is_authenticated"))
        if viewer_id or is_admin:
            is_authenticated = True

        return {
            "viewer_id": viewer_id,
            "player_id": viewer_id,
            "username": viewer_id,
            "viewer_clan": viewer_clan,
            "clan_code": viewer_clan,
            "clan": viewer_clan,
            "viewer_profession": viewer_profession,
            "profession_code": viewer_profession,
            "is_authenticated": is_authenticated,
            "is_admin": is_admin,
            "audience_scope": audience_scope,
        }

    def is_internal_viewer(self, viewer=None):
        context = self.build_viewer_context(viewer)
        return context["audience_scope"] == "internal" or context["is_admin"]

    def projection_cache_key(self, snapshot, viewer=None):
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        context = self.build_viewer_context(viewer)
        cycle = snapshot.get("cycle") or {}
        return ":".join(
            [
                VISIBILITY_VERSION,
                _clean(cycle.get("cycle_id")) or "cycle",
                str(int(snapshot.get("state_version") or cycle.get("state_version") or 0)),
                _clean(context.get("audience_scope")) or "public",
                _clean(context.get("viewer_id")) or "anonymous",
                _clean(context.get("viewer_clan")) or "no-clan",
            ]
        )

    def project_part_for_viewer(self, part, viewer=None):
        part = part if isinstance(part, dict) else {}
        context = self.build_viewer_context(viewer)
        catalog_part = self.parts_by_code.get(_clean(part.get("part_code")), {})
        visual_asset = part_visual_asset_contract(catalog_part)
        if context["audience_scope"] == "internal" or context["is_admin"]:
            projected = dict(part)
            projected.update({
                "projection": "internal",
                "visibility_level": "internal",
                "identity_visible": True,
                "ability_visible": True,
                "location_visibility": "exact",
                "public_entity_id": _public_entity_id(part.get("cycle_id"), part.get("part_id")),
                **visual_asset,
            })
            return projected

        state = self.modules.resolve_part_module_state(part)
        if not state.get("strategic_state_available"):
            return None

        relation = self.modules.resolve_part_viewer_relation(part, context)
        if not relation:
            return None

        visibility_level = RELATION_TO_VISIBILITY[relation]
        location_visibility = RELATION_TO_LOCATION_VISIBILITY[relation]
        identity_visible = visibility_level in FULL_VISIBILITY_LEVELS
        ability_visible = identity_visible
        exact_location = location_visibility == "exact"
        can_show_on_map = exact_location or location_visibility == "territory_only"

        clan = self.clans_by_code.get(_clean(part.get("clan_code")), {})
        machine = self.machines_by_code.get(_clean(part.get("machine_code")), {})
        profession = self.professions_by_code.get(_clean(part.get("profession_code")), {})
        ability_code = _clean(catalog_part.get("ability_code"))
        ability = self.abilities_by_code.get(ability_code, {})

        public_entity_id = _public_entity_id(part.get("cycle_id"), part.get("part_id"))
        target_id_visible = identity_visible or visibility_level == "full_public"

        projected = {
            "part_id": _clean(part.get("part_id")) if identity_visible else None,
            "public_entity_id": public_entity_id,
            "cycle_id": _clean(part.get("cycle_id")),
            "projection": "viewer_visibility",
            "visibility_version": VISIBILITY_VERSION,
            "visibility_level": visibility_level,
            "viewer_relation": relation,
            "module_state": state.get("module_state") or None,
            "status": state.get("base_status") or part.get("status") or None,
            "conflict_state": state.get("conflict_state") or "none",
            "contested": state.get("conflict_state") == "contested",
            "identity_visible": identity_visible,
            "ability_visible": ability_visible,
            "territory_contains_part": state.get("module_state") == "blocked",
            "location_visibility": location_visibility,
            "can_show_on_map": can_show_on_map,
            "can_teleport": exact_location,
            "target_id": _clean(part.get("target_id")) if target_id_visible else None,
            "latitude": part.get("latitude") if exact_location else None,
            "longitude": part.get("longitude") if exact_location else None,
            "territory_id": _clean(part.get("territory_id")) or None,
            "territory_owner_id": _clean(part.get("territory_owner_id")) or None,
            "territory_clan": _clean(part.get("territory_clan")) or None,
            "discovered_at": _clean(part.get("discovered_at")) or None,
            "updated_at": _clean(part.get("updated_at")) or None,
            "state_version": int(part.get("state_version") or 0),
            "part_code": _clean(part.get("part_code")) if identity_visible else None,
            "visual_asset_key": visual_asset.get("visual_asset_key") if identity_visible else None,
            "visual_asset_url": visual_asset.get("visual_asset_url") if identity_visible else None,
            # A classified projection still needs a proper map glyph.  This
            # generic artwork carries no part identity and therefore does not
            # disclose the hidden node or topology.
            "marker_asset_url": (
                visual_asset.get("visual_asset_url")
                if identity_visible
                else CLASSIFIED_MARKER_ASSET_URL
            ),
            "name": _clean(catalog_part.get("name")) if identity_visible else None,
            "clan_code": _clean(part.get("clan_code")) if visibility_level != "contained_hidden" else None,
            "clan_name": _clean(clan.get("name")) if visibility_level != "contained_hidden" else None,
            "machine_code": _clean(part.get("machine_code")) if identity_visible else None,
            "machine_name": _clean(machine.get("name")) if identity_visible else None,
            "profession_code": _clean(part.get("profession_code")) if identity_visible else None,
            "profession_name": _clean(profession.get("name")) if identity_visible else None,
            "ability_code": ability_code if ability_visible else None,
            "ability_name": _clean(ability.get("name")) if ability_visible else None,
            "ability_description": _clean(ability.get("description")) if ability_visible else None,
            "display_label": self._display_label(part, catalog_part, visibility_level),
            "summary": self._summary_for_part(visibility_level),
        }
        if projected["contested"]:
            projected["frozen_visibility_context"] = {
                "module_state": projected["module_state"],
                "visibility_level": visibility_level,
                "viewer_relation": relation,
            }
        return projected

    def project_parts_for_viewer(self, parts, viewer=None):
        projected = []
        for part in parts or []:
            item = self.project_part_for_viewer(part, viewer)
            if item is not None:
                projected.append(item)
        return projected

    def project_connection_for_viewer(self, connection, viewer=None, projected_parts_by_id=None):
        connection = connection if isinstance(connection, dict) else {}
        projected_parts_by_id = projected_parts_by_id or {}
        part_a = projected_parts_by_id.get(_clean(connection.get("part_a_id")))
        part_b = projected_parts_by_id.get(_clean(connection.get("part_b_id")))
        if not part_a or not part_b:
            return None

        exact_a = bool(part_a and part_a.get("location_visibility") == "exact")
        exact_b = bool(part_b and part_b.get("location_visibility") == "exact")
        if not exact_a or not exact_b:
            return None

        active_a = part_a.get("module_state") == "active"
        active_b = part_b.get("module_state") == "active"
        discovered_a = bool(part_a.get("can_show_on_map"))
        discovered_b = bool(part_b.get("can_show_on_map"))
        if active_a and active_b:
            state = "active"
            flow_direction = "a_to_b"
            integrity = 100
        elif active_a and discovered_b:
            state = "half_from_a"
            flow_direction = "a_to_b"
            integrity = 50
        elif active_b and discovered_a:
            state = "half_from_b"
            flow_direction = "b_to_a"
            integrity = 50
        elif discovered_a and discovered_b:
            state = "inactive"
            flow_direction = "none"
            integrity = 0
        else:
            state = "hidden"
            flow_direction = "none"
            integrity = 0

        if state == "hidden":
            return None

        endpoint_a = self._connection_endpoint(part_a, "a")
        endpoint_b = self._connection_endpoint(part_b, "b")
        contested = bool(part_a.get("contested") or part_b.get("contested"))
        return {
            "connection_id": _clean(connection.get("connection_id")),
            "public_connection_id": _public_connection_id(connection.get("cycle_id"), connection.get("connection_id")),
            "cycle_id": _clean(connection.get("cycle_id")),
            "position_in_ring": connection.get("position_in_ring"),
            "state": state,
            "can_show_on_map": state in {"half_from_a", "half_from_b", "active"},
            "visibility_level": "full" if state == "active" else ("partial" if state.startswith("half_") else "inactive"),
            "endpoint_a": endpoint_a,
            "endpoint_b": endpoint_b,
            "visible_start": endpoint_a if flow_direction == "a_to_b" else endpoint_b if flow_direction == "b_to_a" else None,
            "visible_end": endpoint_b if flow_direction == "a_to_b" else endpoint_a if flow_direction == "b_to_a" else None,
            "from_public_entity_id": endpoint_a["public_entity_id"],
            "to_public_entity_id": endpoint_b["public_entity_id"],
            "from_latitude": endpoint_a["latitude"],
            "from_longitude": endpoint_a["longitude"],
            "to_latitude": endpoint_b["latitude"],
            "to_longitude": endpoint_b["longitude"],
            "flow_direction": flow_direction,
            "integrity": integrity,
            "contested": contested,
            "state_version": max(int(part_a.get("state_version") or 0), int(part_b.get("state_version") or 0)),
            "hidden_endpoint": False,
        }

    @staticmethod
    def _connection_endpoint(part, side):
        return {
            "side": side,
            "public_entity_id": part.get("public_entity_id"),
            "latitude": part.get("latitude"),
            "longitude": part.get("longitude"),
            "module_state": part.get("module_state"),
            "clan_code": part.get("clan_code"),
            "display_label": part.get("display_label"),
            "visibility_level": part.get("visibility_level"),
        }

    def project_machine_for_viewer(self, machine, viewer=None):
        machine = machine if isinstance(machine, dict) else {}
        context = self.build_viewer_context(viewer)
        own_clan = _clean(machine.get("clan_code")) and _clean(machine.get("clan_code")) == context["viewer_clan"]
        internal = context["audience_scope"] == "internal" or context["is_admin"]
        identity_visible = internal or own_clan
        catalog_machine = self.machines_by_code.get(_clean(machine.get("machine_code")), {})
        return {
            "public_entity_id": _public_entity_id(machine.get("cycle_id"), machine.get("machine_code")),
            "cycle_id": _clean(machine.get("cycle_id")),
            "visibility_level": "full_clan" if own_clan else ("internal" if internal else "active_foreign"),
            "machine_code": _clean(machine.get("machine_code")) if identity_visible else None,
            "machine_name": _clean(catalog_machine.get("name")) if identity_visible else None,
            "clan_code": _clean(machine.get("clan_code")) or None,
            "parts_total": machine.get("parts_total"),
            "parts_active": machine.get("parts_active"),
            "parts_neutral": machine.get("parts_neutral"),
            "parts_blocked": machine.get("parts_blocked"),
            "progress_percent": machine.get("progress_percent"),
            "machine_online": bool(machine.get("machine_online")),
        }

    def project_territory_component_for_viewer(self, cluster, viewer=None):
        cluster = cluster if isinstance(cluster, dict) else {}
        parts = cluster.get("parts") or cluster.get("ghost_parts") or []
        projected_parts = self.project_parts_for_viewer(parts, viewer)
        identity_visible = any(part.get("identity_visible") for part in projected_parts)
        relation = next((part.get("viewer_relation") for part in projected_parts if part.get("viewer_relation")), None)
        state = next((part.get("module_state") for part in projected_parts if part.get("module_state")), None)
        return {
            "cluster_id": _clean(cluster.get("cluster_id") or cluster.get("territory_id")) or None,
            "contains_ghost_part": bool(projected_parts),
            "ghost_part_count": len(projected_parts),
            "ghost_part_relation": relation,
            "ghost_part_state": state,
            "ghost_part_identity_visible": identity_visible,
            "ghost_part_summary": self._territory_summary(projected_parts),
            "parts": projected_parts,
        }

    def project_event_fact_for_audience(self, event, audience=None):
        event = event if isinstance(event, dict) else {}
        context = self.build_viewer_context(audience or {"audience_scope": "public"})
        owner_scope = context["audience_scope"] in {"internal", "owner"} or context["is_admin"]
        target_clan = _clean(event.get("target_clan") or event.get("clan_code"))
        clan_scope = (
            context["audience_scope"] == "clan"
            and bool(context.get("viewer_clan"))
            and context["viewer_clan"] == target_clan
        )
        fact = {
            "event_type": _clean(event.get("event_type") or event.get("type")),
            "territory_contains_part": bool(event.get("territory_contains_part")),
            "public_entity_id": _clean(event.get("public_entity_id")) or None,
            "previous_status": _clean(event.get("previous_status")) or None,
            "status": _clean(event.get("status")) or None,
            "previous_conflict_state": _clean(event.get("previous_conflict_state")) or None,
            "conflict_state": _clean(event.get("conflict_state")) or None,
        }
        if owner_scope:
            fact.update({
                "owner_clan": _clean(event.get("owner_clan") or event.get("territory_clan")) or None,
                "part_code": _clean(event.get("part_code")) or None,
                "part_name": _clean(event.get("part_name") or event.get("name")) or None,
                "target_clan": _clean(event.get("target_clan") or event.get("clan_code")) or None,
            })
        elif clan_scope:
            fact.update({
                "part_identity": None,
                "part_code": None,
                "part_name": None,
                "target_clan": target_clan or None,
            })
        else:
            fact.update({
                "part_identity": None,
                "part_code": None,
                "part_name": None,
                "target_clan": None,
            })
        return fact

    def build_snapshot_for_viewer(self, snapshot, viewer=None):
        if self.is_internal_viewer(viewer):
            return {
                "viewer": viewer or "internal",
                "projection": "internal_recovery",
                "snapshot": snapshot,
            }

        context = self.build_viewer_context(viewer)
        parts = []
        projected_by_id = {}
        for raw_part in snapshot.get("parts") or []:
            projected = self.project_part_for_viewer(raw_part, context)
            if projected is not None:
                parts.append(projected)
                projected_by_id[_clean(raw_part.get("part_id"))] = projected
        connections = [
            projected
            for projected in (
                self.project_connection_for_viewer(connection, context, projected_by_id)
                for connection in snapshot.get("connections") or []
            )
            if projected is not None
        ]
        progress = self._progress_from_parts(parts)
        progress.update(self._connection_progress(connections))
        machines = [self.project_machine_for_viewer(machine, context) for machine in progress["machines"]]
        return {
            "projection": "viewer_visibility",
            "visibility_version": VISIBILITY_VERSION,
            "cache_key": self.projection_cache_key(snapshot, context),
            "state_version": int(snapshot.get("state_version") or 0),
            "viewer": context,
            "cycle": self._project_cycle(snapshot.get("cycle") or {}),
            "progress": {key: value for key, value in progress.items() if key != "machines"},
            "machines": machines,
            "parts": parts,
            "connections": connections,
        }

    @staticmethod
    def _connection_progress(connections):
        visible = [item for item in connections or [] if item.get("state") != "hidden"]
        return {
            "connections_total": 20,
            "connections_visible": len(visible),
            "connections_hidden": max(0, 20 - len(visible)),
            "connections_half": sum(1 for item in visible if str(item.get("state")).startswith("half_")),
            "connections_active": sum(1 for item in visible if item.get("state") == "active"),
            "connections_inactive": sum(1 for item in visible if item.get("state") == "inactive"),
            "circuit_complete": sum(1 for item in visible if item.get("state") == "active") >= 20,
        }

    def _display_label(self, part, catalog_part, visibility_level):
        if visibility_level in FULL_VISIBILITY_LEVELS:
            return _clean(catalog_part.get("name")) or _clean(part.get("part_code")) or "GhostNetwork part"
        if visibility_level == "active_foreign":
            return "AKTYWNY WĘZEŁ GHOSTNETWORK"
        return "TERYTORIUM ZAWIERA CZĘŚĆ GHOSTNETWORK"

    @staticmethod
    def _summary_for_part(visibility_level):
        if visibility_level in FULL_VISIBILITY_LEVELS:
            return "PEŁNE DANE KOMPONENTU"
        if visibility_level == "active_foreign":
            return "AKTYWNY WĘZEŁ GHOSTNETWORK"
        return "TERYTORIUM ZAWIERA CZĘŚĆ GHOSTNETWORK"

    @staticmethod
    def _territory_summary(projected_parts):
        if not projected_parts:
            return ""
        if any(part.get("visibility_level") in FULL_VISIBILITY_LEVELS for part in projected_parts):
            return "TERYTORIUM ZAWIERA WIDOCZNE KOMPONENTY GHOSTNETWORK"
        return "TERYTORIUM ZAWIERA CZĘŚĆ GHOSTNETWORK"

    @staticmethod
    def _project_cycle(cycle):
        return {
            "cycle_id": _clean(cycle.get("cycle_id")) or None,
            "signal_number": cycle.get("signal_number"),
            "ghostsystem_version": cycle.get("ghostsystem_version"),
            "status": _clean(cycle.get("status")) or None,
            "catalog_version": _clean(cycle.get("catalog_version")) or None,
            "state_version": int(cycle.get("state_version") or 0),
            "started_at": _clean(cycle.get("started_at")) or None,
            "updated_at": _clean(cycle.get("updated_at")) or None,
        }

    def _progress_from_parts(self, parts):
        machines = {}
        for part in parts:
            machine_code = part.get("machine_code") or f"hidden:{part.get('clan_code') or 'unknown'}"
            machine = machines.setdefault(machine_code, {
                "cycle_id": part.get("cycle_id"),
                "machine_code": part.get("machine_code"),
                "clan_code": part.get("clan_code"),
                "parts_total": 0,
                "parts_active": 0,
                "parts_neutral": 0,
                "parts_blocked": 0,
            })
            machine["parts_total"] += 1
            if part.get("module_state") == "active":
                machine["parts_active"] += 1
            elif part.get("module_state") == "neutral":
                machine["parts_neutral"] += 1
            elif part.get("module_state") == "blocked":
                machine["parts_blocked"] += 1
        for machine in machines.values():
            total = machine["parts_total"] or 1
            machine["progress_percent"] = int(round(machine["parts_active"] / total * 100))
            machine["machine_online"] = machine["parts_active"] >= 5
        return {
            "parts_total": len(parts),
            "parts_neutral": sum(1 for part in parts if part.get("module_state") == "neutral"),
            "parts_blocked": sum(1 for part in parts if part.get("module_state") == "blocked"),
            "parts_active": sum(1 for part in parts if part.get("module_state") == "active"),
            "parts_contested": sum(1 for part in parts if part.get("contested")),
            "machines": list(machines.values()),
        }

def build_viewer_projection(snapshot, viewer=None):
    return GhostVisibilityService().build_snapshot_for_viewer(snapshot, viewer=viewer)
