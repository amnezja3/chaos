from __future__ import annotations

import copy
import hashlib
import json

from .repository import GhostNetworkRepository
from .visibility import VISIBILITY_VERSION, build_viewer_projection


GHOSTNETWORK_DELTA_SCOPE = "ghostnetwork"
DEFAULT_VIEW = "map"
SNAPSHOT_VIEWS = {"map", "suite", "territory_summary", "status"}


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _json_hash(payload):
    raw = json.dumps(payload if isinstance(payload, dict) else {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _public_part_entity_id(cycle_id, part_id):
    raw = f"{_clean(cycle_id)}:{_clean(part_id)}"
    return f"ghost-node:{hashlib.sha1(raw.encode('utf-8')).hexdigest()[:12]}"


def snapshot_checksum(projection):
    projection = projection if isinstance(projection, dict) else {}
    cycle = projection.get("cycle") if isinstance(projection.get("cycle"), dict) else {}
    payload = {
        "cycle_id": cycle.get("cycle_id"),
        "state_version": projection.get("state_version") or cycle.get("state_version") or 0,
        "parts": [
            [
                part.get("public_entity_id"),
                part.get("module_state"),
                part.get("conflict_state"),
                part.get("visibility_level"),
                part.get("location_visibility"),
            ]
            for part in projection.get("parts") or []
            if isinstance(part, dict)
        ],
        "connections": [
            [
                item.get("public_connection_id"),
                item.get("state"),
                item.get("can_show_on_map"),
            ]
            for item in projection.get("connections") or []
            if isinstance(item, dict)
        ],
        "progress": projection.get("progress") or {},
    }
    return _json_hash(payload)


def _suite_owner(owner_aliases, owner_id):
    owner_id = _clean(owner_id)
    raw = (owner_aliases or {}).get(owner_id) if owner_id else None
    if isinstance(raw, dict):
        alias = _clean(raw.get("display_alias") or raw.get("nick") or raw.get("username"))
        revision = int(raw.get("source_profile_revision") or 0)
        checksum = _clean(raw.get("source_profile_checksum"))
    else:
        alias = _clean(raw)
        revision = 0
        checksum = ""
    return {
        "owner_id": owner_id or None,
        "owner_alias": alias or None,
        "source_profile_revision": revision,
        "source_profile_checksum": checksum,
    }


def _suite_actions(part, *, cycle_active=True):
    public_entity_id = _clean(part.get("public_entity_id"))
    territory_id = _clean(part.get("territory_id"))
    location_visibility = _clean(part.get("location_visibility"))
    exact_location_available = (
        part.get("latitude") is not None
        and part.get("longitude") is not None
    )
    if location_visibility == "exact" and public_entity_id and exact_location_available:
        target_type = "ghostnetwork_part"
        target_id = public_entity_id
    elif location_visibility == "territory_only" and territory_id:
        target_type = "ghostnetwork_territory"
        target_id = territory_id
    else:
        target_type = None
        target_id = None
    module_state = _clean(part.get("module_state")).lower()
    lifecycle_status = _clean(part.get("status")).lower() or {
        "neutral": "public",
        "blocked": "contained",
        "active": "active",
    }.get(module_state, "")
    enabled = bool(
        cycle_active
        and lifecycle_status in {"public", "contained", "active"}
        and target_type
        and target_id
    )
    return {
        "can_show_on_map": enabled and bool(part.get("can_show_on_map")),
        "can_teleport": enabled,
        "map_target_type": target_type if enabled else None,
        "map_target_id": target_id if enabled else None,
        "teleport_target_type": target_type if enabled else None,
        "teleport_target_id": target_id if enabled else None,
    }


def _suite_part(part, owner_aliases, *, cycle_active=True):
    item = copy.deepcopy(part if isinstance(part, dict) else {})
    for key in (
        "vertices", "geometry", "polygon", "territory_geometry",
        "active_reservations", "reservation", "reservations", "event_history",
    ):
        item.pop(key, None)
    if not bool(item.get("identity_visible")):
        for key in (
            "part_id", "part_code", "name", "machine_code", "machine_name",
            "profession_code", "profession_name", "ability_code", "ability_name",
            "ability_description", "visual_asset_key", "visual_asset_url", "target_id",
        ):
            item[key] = None
    owner = _suite_owner(owner_aliases, item.get("territory_owner_id"))
    location_visibility = _clean(item.get("location_visibility")) or None
    exact = location_visibility == "exact"
    territory_id = _clean(item.get("territory_id")) or None
    actions = _suite_actions(item, cycle_active=cycle_active)
    item["owner"] = {
        "owner_id": owner["owner_id"],
        "owner_alias": owner["owner_alias"],
        "owner_clan": item.get("territory_clan"),
    }
    item["territory"] = {
        "territory_id": territory_id,
        "cluster_id": territory_id,
        "owner_id": owner["owner_id"],
        "owner_alias": owner["owner_alias"],
        "owner_clan": item.get("territory_clan"),
        "conflict_state": item.get("conflict_state") or "none",
    }
    item["location"] = {
        "visibility": location_visibility,
        "latitude": item.get("latitude") if exact else None,
        "longitude": item.get("longitude") if exact else None,
        "map_focus_type": actions["map_target_type"],
        "map_focus_id": actions["map_target_id"],
    }
    item["actions"] = actions
    return item


def _suite_summary(parts):
    parts = [item for item in parts or [] if isinstance(item, dict)]
    return {
        "parts_total": len(parts),
        "parts_discovered": len(parts),
        "parts_public": sum(1 for item in parts if item.get("viewer_relation") == "public_neutral"),
        "parts_blocked": sum(1 for item in parts if item.get("module_state") == "blocked"),
        "parts_active": sum(1 for item in parts if item.get("module_state") == "active"),
        "parts_contested": sum(1 for item in parts if item.get("contested")),
        "parts_visible_to_viewer": len(parts),
    }


def _suite_groups(parts):
    groups = {
        "public": [],
        "blocked": [],
        "clan_active": [],
        "self_foreign": [],
        "self_own": [],
    }
    relation_to_group = {
        "public_neutral": "public",
        "foreign_blocked": "blocked",
        "clan_own_active": "clan_active",
        "self_foreign_blocked": "self_foreign",
        "self_own_active": "self_own",
    }
    for item in parts or []:
        if not isinstance(item, dict):
            continue
        group = relation_to_group.get(_clean(item.get("viewer_relation")))
        public_entity_id = _clean(item.get("public_entity_id"))
        if group and public_entity_id:
            groups[group].append(public_entity_id)
    return {
        key: sorted(set(values))
        for key, values in groups.items()
    }


def _suite_cache_key(base_key, owner_aliases):
    identities = []
    for owner_id in sorted((owner_aliases or {}).keys()):
        owner = _suite_owner(owner_aliases, owner_id)
        identities.append([
            owner_id,
            owner["source_profile_revision"],
            owner["source_profile_checksum"],
        ])
    identity_version = _json_hash({"owners": identities})
    return f"{_clean(base_key, 'ghostnetwork')}:view=suite:owners={identity_version}"


def _suite_health(parts, groups, duplicate_ids, viewer, source_parts_count):
    errors = []
    if int(source_parts_count or 0) > 20:
        errors.append(f"parts_limit_exceeded:{int(source_parts_count)}")
    grouped = []
    for values in (groups or {}).values():
        grouped.extend(values or [])
    if len(grouped) != len(set(grouped)):
        errors.append("part_in_multiple_base_groups")
    for public_id in sorted(set(duplicate_ids or [])):
        errors.append(f"duplicate_public_entity_id:{public_id}")

    viewer = viewer if isinstance(viewer, dict) else {}
    viewer_id = _clean(viewer.get("viewer_id") or viewer.get("username"))
    viewer_clan = _clean(viewer.get("viewer_clan") or viewer.get("clan_code"))
    for item in parts or []:
        public_id = _clean(item.get("public_entity_id"), "unknown")
        visibility = _clean(item.get("location_visibility"))
        if visibility == "exact" and (
            item.get("latitude") is None or item.get("longitude") is None
        ):
            errors.append(f"exact_location_missing:{public_id}")
        if visibility == "territory_only" and not _clean(item.get("territory_id")):
            errors.append(f"territory_only_missing_territory:{public_id}")
        if not bool(item.get("identity_visible")) and any(
            item.get(key) is not None
            for key in (
                "part_id", "part_code", "name", "machine_code", "profession_code",
                "ability_code", "visual_asset_url", "target_id",
            )
        ):
            errors.append(f"hidden_identity_present:{public_id}")
        relation = _clean(item.get("viewer_relation"))
        if relation in {"self_foreign_blocked", "self_own_active"} and (
            not viewer_id or _clean(item.get("territory_owner_id")) != viewer_id
        ):
            errors.append(f"self_relation_owner_mismatch:{public_id}")
        if relation == "clan_own_active" and (
            not viewer_clan or _clean(item.get("clan_code")) != viewer_clan
        ):
            errors.append(f"clan_relation_mismatch:{public_id}")
    return {
        "ok": not errors,
        "errors": errors,
        "parts_checked": len(parts or []),
    }


def normalize_snapshot_view(projection, view=DEFAULT_VIEW, owner_aliases=None):
    projection = copy.deepcopy(projection if isinstance(projection, dict) else {})
    view = _clean(view, DEFAULT_VIEW)
    if view not in SNAPSHOT_VIEWS:
        view = DEFAULT_VIEW

    projection["view"] = view
    projection["snapshot_checksum"] = snapshot_checksum(projection)

    if view == "map":
        return projection

    if view == "suite":
        cycle = projection.get("cycle") if isinstance(projection.get("cycle"), dict) else {}
        cycle_active = _clean(cycle.get("status"), "active") == "active"
        parts = []
        duplicate_ids = []
        seen_ids = set()
        for raw_part in projection.get("parts") or []:
            if not isinstance(raw_part, dict):
                continue
            public_id = _clean(raw_part.get("public_entity_id"))
            if not public_id:
                continue
            if public_id in seen_ids:
                duplicate_ids.append(public_id)
                continue
            seen_ids.add(public_id)
            parts.append(
                _suite_part(raw_part, owner_aliases or {}, cycle_active=cycle_active)
            )
        source_parts_count = len(parts)
        parts.sort(key=lambda item: _clean(item.get("public_entity_id")))
        parts = parts[:20]
        projection["parts"] = parts
        projection["summary"] = _suite_summary(parts)
        projection["groups"] = _suite_groups(parts)
        projection["suite_health"] = _suite_health(
            parts,
            projection["groups"],
            duplicate_ids,
            projection.get("viewer"),
            source_parts_count,
        )
        projection.pop("suite", None)
        projection["cache_key"] = _suite_cache_key(
            projection.get("cache_key"), owner_aliases or {}
        )
        projection["connections"] = [
            {
                "public_connection_id": item.get("public_connection_id"),
                "state": item.get("state"),
                "state_version": item.get("state_version"),
                "viewer_relation": item.get("viewer_relation"),
                "can_show_on_map": bool(item.get("can_show_on_map")),
            }
            for item in projection.get("connections") or []
            if isinstance(item, dict)
        ]
        return projection

    if view == "territory_summary":
        parts = projection.get("parts") or []
        projection["parts"] = [
            {
                "public_entity_id": part.get("public_entity_id"),
                "territory_id": part.get("territory_id"),
                "territory_summary": part.get("territory_summary"),
                "territory_latitude": part.get("territory_latitude"),
                "territory_longitude": part.get("territory_longitude"),
                "visibility_level": part.get("visibility_level"),
                "module_state": part.get("module_state"),
                "state_version": part.get("state_version"),
                "can_show_on_map": part.get("can_show_on_map"),
            }
            for part in parts
            if isinstance(part, dict)
        ]
        projection["connections"] = []
        projection["machines"] = []
        projection["suite"] = {}
        return projection

    if view == "status":
        return {
            "projection": projection.get("projection"),
            "visibility_version": projection.get("visibility_version"),
            "view": view,
            "state_version": projection.get("state_version") or 0,
            "cycle": projection.get("cycle"),
            "progress": projection.get("progress") or {},
            "machines": projection.get("machines") or [],
            "snapshot_checksum": projection.get("snapshot_checksum"),
        }

    return projection


def rebuild_ghostnetwork_delta_projection(cycle_id, from_version=None, repository=None, limit=1000):
    repository = repository or GhostNetworkRepository()
    cycle_id = _clean(cycle_id)
    events = repository.list_events(cycle_id, limit=limit) if cycle_id else []
    try:
        from_version = int(from_version or 0)
    except (TypeError, ValueError):
        from_version = 0
    filtered = [
        event for event in events
        if int((event or {}).get("state_version") or 0) > from_version
    ]
    return {
        "cycle_id": cycle_id,
        "from_version": from_version,
        "current_version": repository.get_state_version(cycle_id) if cycle_id else 0,
        "events": filtered,
        "event_count": len(filtered),
    }


class GhostNetworkDeltaPublisher:
    """Projects GhostNetwork domain events into the existing state delta bus."""

    def __init__(self, repository=None, delta_bus=None):
        self.repository = repository or GhostNetworkRepository()
        self.delta_bus = delta_bus

    def _projection_for_viewer(self, cycle_id, viewer, snapshot=None):
        snapshot = snapshot or self.repository.build_internal_snapshot(cycle_id)
        return build_viewer_projection(snapshot, viewer=viewer)

    @staticmethod
    def _viewer_username(viewer):
        viewer = viewer if isinstance(viewer, dict) else {}
        return _clean(viewer.get("viewer_id") or viewer.get("username") or viewer.get("player_id"))

    @staticmethod
    def _safe_viewer(viewer):
        viewer = dict(viewer or {}) if isinstance(viewer, dict) else {}
        viewer.setdefault("audience_scope", "player")
        viewer.setdefault("is_authenticated", True)
        if viewer.get("viewer_id") and not viewer.get("username"):
            viewer["username"] = viewer["viewer_id"]
        if viewer.get("username") and not viewer.get("viewer_id"):
            viewer["viewer_id"] = viewer["username"]
        if viewer.get("clan_code") and not viewer.get("viewer_clan"):
            viewer["viewer_clan"] = viewer["clan_code"]
        return viewer

    @staticmethod
    def _find_part(projection, event):
        part_id = _clean(event.get("part_id"))
        cycle_id = _clean(event.get("cycle_id"))
        entity_id = _clean(event.get("entity_id"))
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        public_id = _clean(payload.get("public_entity_id") or payload.get("entity_id"))
        expected_public_id = _public_part_entity_id(cycle_id, part_id) if part_id else ""
        for part in projection.get("parts") or []:
            if not isinstance(part, dict):
                continue
            if public_id and _clean(part.get("public_entity_id")) == public_id:
                return part
            if part_id and _clean(part.get("part_id")) == part_id:
                return part
            if expected_public_id and _clean(part.get("public_entity_id")) == expected_public_id:
                return part
            if entity_id and _clean(part.get("public_entity_id")) == entity_id:
                return part
        return None

    @staticmethod
    def _find_connection(projection, event):
        entity_id = _clean(event.get("entity_id"))
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        public_id = _clean(payload.get("public_connection_id") or payload.get("connection_id"))
        for connection in projection.get("connections") or []:
            if not isinstance(connection, dict):
                continue
            candidate = _clean(connection.get("public_connection_id") or connection.get("connection_id"))
            if candidate and candidate in {entity_id, public_id}:
                return connection
        return None

    @staticmethod
    def _event_entity_id(event, projection=None):
        projection = projection if isinstance(projection, dict) else {}
        return (
            _clean(projection.get("public_entity_id"))
            or _clean(projection.get("public_connection_id"))
            or _clean(event.get("entity_id"))
            or _clean(event.get("part_id"))
            or _clean(event.get("cycle_id"))
            or GHOSTNETWORK_DELTA_SCOPE
        )

    def build_delta_for_viewer(self, event, viewer, transaction=None, snapshot=None):
        event = event if isinstance(event, dict) else {}
        cycle_id = _clean(event.get("cycle_id"))
        event_type = _clean(event.get("event_type") or event.get("type"))
        if not cycle_id or not event_type:
            return None

        viewer = self._safe_viewer(viewer)
        projection = self._projection_for_viewer(cycle_id, viewer, snapshot=snapshot)
        state_version = int(event.get("state_version") or projection.get("state_version") or 0)
        payload = {
            "event_id": event.get("event_id"),
            "cycle_id": cycle_id,
            "state_version": state_version,
            "source_event_type": event_type,
            "visibility_version": projection.get("visibility_version") or VISIBILITY_VERSION,
            "snapshot_checksum": snapshot_checksum(projection),
        }
        # Lifecycle SFX is driven by canonical transitions, never by the
        # projected/rendered state.  Keep only the public transition envelope;
        # internal part metadata remains protected by the viewer projection.
        event_payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        for key in (
            "source_event_id", "previous_status", "status",
            "previous_conflict_state", "conflict_state",
            "previous_active_parts", "active_parts", "occurred_at",
        ):
            value = event_payload.get(key, event.get(key))
            if value is not None:
                payload[key] = copy.deepcopy(value)

        projected_entity = None
        if event_type.startswith("ghost.connection_"):
            projected_entity = self._find_connection(projection, event)
            if projected_entity:
                payload["connection_projection"] = projected_entity
                payload["suite_connection_projection"] = {
                    "public_connection_id": projected_entity.get("public_connection_id"),
                    "state": projected_entity.get("state"),
                    "state_version": projected_entity.get("state_version"),
                    "viewer_relation": projected_entity.get("viewer_relation"),
                    "can_show_on_map": bool(projected_entity.get("can_show_on_map")),
                }
        elif event_type.startswith("ghost.machine_"):
            payload["machine_progress"] = copy.deepcopy(event.get("payload") or {})
        elif event_type.startswith("ghost.cycle_") or event_type in {"ghost.version_changed", "ghost.restart_required", "ghost.signal_sent"}:
            payload["cycle"] = projection.get("cycle")
            payload["progress"] = projection.get("progress") or {}
        else:
            projected_entity = self._find_part(projection, event)
            if projected_entity:
                payload["part_projection"] = projected_entity
                cycle = projection.get("cycle") if isinstance(projection.get("cycle"), dict) else {}
                payload["suite_part_projection"] = _suite_part(
                    projected_entity,
                    {},
                    cycle_active=_clean(cycle.get("status"), "active") == "active",
                )
            elif event_type == "ghost.part_consumed" and _clean(event.get("part_id")):
                # A consumed part no longer belongs to the current viewer
                # projection. Publish only its stable opaque reference so an
                # already-open client can remove the stale card/layer without
                # learning identity, coordinates or topology.
                projected_entity = {
                    "public_entity_id": _public_part_entity_id(
                        cycle_id, event.get("part_id")
                    )
                }
                payload["public_entity_id"] = projected_entity["public_entity_id"]
                payload["removed"] = True
            elif event_type.startswith("ghost.part_"):
                # A viewer without a safe part projection must not receive an
                # internal part id or infer a hidden node from event metadata.
                return None

        if transaction:
            payload.update({
                "transaction_id": transaction.get("transaction_id"),
                "transaction_index": transaction.get("transaction_index"),
                "transaction_size": transaction.get("transaction_size"),
            })

        return {
            "scope": GHOSTNETWORK_DELTA_SCOPE,
            "type": event_type,
            "entity_id": self._event_entity_id(event, projected_entity),
            "payload": payload,
            "created_at": event.get("created_at"),
            "dedupe_key": event.get("dedupe_key") or f"ghostnetwork:{cycle_id}:{event_type}:{payload.get('event_id') or state_version}",
        }

    def publish_event(self, event, recipients, transaction=None):
        if not self.delta_bus:
            return []
        recipients = recipients if isinstance(recipients, (list, tuple)) else [recipients]
        cycle_id = _clean((event or {}).get("cycle_id"))
        snapshot = self.repository.build_internal_snapshot(cycle_id) if cycle_id else None
        published = []
        for recipient in recipients:
            viewer = self._safe_viewer(recipient)
            username = self._viewer_username(viewer)
            if not username:
                continue
            delta = self.build_delta_for_viewer(
                event,
                viewer,
                transaction=transaction,
                snapshot=snapshot,
            )
            if not delta:
                continue
            dedupe_key = f"ghostnetwork:{username}:{delta['dedupe_key']}"
            try:
                published.append(self.delta_bus.record_change(
                    username,
                    delta["scope"],
                    delta["type"],
                    payload=delta["payload"],
                    entity_id=delta["entity_id"],
                    dedupe_key=dedupe_key,
                    created_at=delta.get("created_at"),
                ))
            except Exception as exc:
                print(
                    f"[ghostnetwork] delta publish failed user={username} "
                    f"type={delta.get('type')} error={exc}",
                    flush=True,
                )
        return published
