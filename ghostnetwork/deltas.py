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


def normalize_snapshot_view(projection, view=DEFAULT_VIEW):
    projection = copy.deepcopy(projection if isinstance(projection, dict) else {})
    view = _clean(view, DEFAULT_VIEW)
    if view not in SNAPSHOT_VIEWS:
        view = DEFAULT_VIEW

    projection["view"] = view
    projection["snapshot_checksum"] = snapshot_checksum(projection)

    if view == "map":
        return projection

    if view == "suite":
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

        projected_entity = None
        if event_type.startswith("ghost.connection_"):
            projected_entity = self._find_connection(projection, event)
            if projected_entity:
                payload["connection_projection"] = projected_entity
        elif event_type.startswith("ghost.machine_"):
            payload["machine_progress"] = copy.deepcopy(event.get("payload") or {})
        elif event_type.startswith("ghost.cycle_") or event_type in {"ghost.version_changed", "ghost.restart_required", "ghost.signal_sent"}:
            payload["cycle"] = projection.get("cycle")
            payload["progress"] = projection.get("progress") or {}
        else:
            projected_entity = self._find_part(projection, event)
            if projected_entity:
                payload["part_projection"] = projected_entity
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
