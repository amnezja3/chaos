from __future__ import annotations

from database import GameStateDeltaBus

from .territory_context_reader import TerritoryContextReader, _bbox_for_vertices, _clean_text, _coerce_float


TERRITORY_SCOPE = "territory"
TERRITORY_UPDATED = "territory.updated"
TERRITORY_CONFLICT_CHANGED = "territory.conflict_changed"


def _territory_id_for_area(area):
    return TerritoryContextReader._context_id(area or {})


def _area_payload(area, reason=""):
    area = dict(area or {})
    territory_id = _territory_id_for_area(area)
    owner = _clean_text(area.get("owner_username"), "unknown")
    return {
        "territory_id": territory_id,
        "area_id": area.get("id"),
        "owner_id": owner,
        "owner_username": owner,
        "status": _clean_text(area.get("status"), "active"),
        "bbox": _bbox_for_vertices(area.get("vertices") or []),
        "centroid": {
            "lat": _coerce_float(area.get("centroid_lat")),
            "lng": _coerce_float(area.get("centroid_lng")),
        },
        "area_size": _coerce_float(area.get("area_size")) or 0,
        "version": TerritoryContextReader._version(area),
        "reason": _clean_text(reason),
    }


def _conflict_payload(conflict, reason=""):
    conflict = dict(conflict or {})
    snapshot_conflict = dict(conflict.get("conflict") or {})
    conflict_id = (
        conflict.get("conflict_id") or conflict.get("id")
        or snapshot_conflict.get("conflict_id") or snapshot_conflict.get("id")
    )
    participants = [
        _clean_text(item)
        for item in (
            conflict.get("participant_usernames")
            or conflict.get("participants")
            or snapshot_conflict.get("participant_usernames")
            or snapshot_conflict.get("participants")
            or []
        )
        if _clean_text(item)
    ]
    area_ids = [
        item
        for item in (
            conflict.get("area_ids") or conflict.get("primary_area_ids")
            or snapshot_conflict.get("area_ids") or snapshot_conflict.get("primary_area_ids")
            or []
        )
        if item not in (None, "")
    ]
    snapshot_version = int(conflict.get("snapshot_version") or 0)
    conflict_version = int(
        conflict.get("conflict_version") or snapshot_conflict.get("conflict_version") or 0
    )
    geometry_version = int(conflict.get("geometry_version") or snapshot_version or 0)
    payload = {
        "conflict_id": conflict_id,
        "conflict_key": _clean_text(
            conflict.get("conflict_key") or snapshot_conflict.get("conflict_key"), "unknown"
        ),
        "participants": participants,
        "area_ids": area_ids,
        "status": _clean_text(conflict.get("status") or snapshot_conflict.get("status"), "active"),
        "updated_at": _clean_text(
            conflict.get("generated_at") or conflict.get("updated_at")
            or snapshot_conflict.get("updated_at") or conflict.get("created_at")
        ),
        "snapshot_version": snapshot_version,
        "conflict_version": conflict_version,
        "geometry_version": geometry_version,
        "version": snapshot_version or conflict_version or geometry_version,
        "reason": _clean_text(reason),
    }
    if "fronts" in conflict or "pillars" in conflict or snapshot_conflict:
        payload.update({
            "conflict": snapshot_conflict,
            "fronts": [dict(item) for item in (conflict.get("fronts") or []) if isinstance(item, dict)],
            "pillars": [dict(item) for item in (conflict.get("pillars") or []) if isinstance(item, dict)],
            "generated_at": conflict.get("generated_at") or snapshot_conflict.get("updated_at"),
            "complete": conflict.get("complete", True),
            "geometry_status": _clean_text(
                conflict.get("geometry_status") or snapshot_conflict.get("geometry_status"),
                "unknown",
            ),
            "recovery_required": bool(conflict.get("recovery_required", False)),
        })
    return payload


class TerritoryDeltaPublisher:
    """Publishes territory deltas into the existing GameStateDeltaBus."""

    def __init__(self, delta_bus=None, context_reader=None):
        self.delta_bus = delta_bus or GameStateDeltaBus()
        self.context_reader = context_reader or TerritoryContextReader()

    def record_area_updated(self, username, area, reason="", dedupe_key=None):
        username = _clean_text(username)
        if not username:
            return None
        payload = _area_payload(area, reason=reason)
        territory_id = payload["territory_id"]
        key = dedupe_key or "territory:updated:{username}:{territory_id}:{version}:{reason}".format(
            username=username,
            territory_id=territory_id,
            version=payload.get("version") or "0",
            reason=_clean_text(reason, "update"),
        )
        return self.delta_bus.record_change(
            username,
            TERRITORY_SCOPE,
            TERRITORY_UPDATED,
            payload,
            entity_id=territory_id,
            dedupe_key=key,
        )

    def record_areas_updated(self, username, areas, reason=""):
        events = []
        for area in areas or []:
            event = self.record_area_updated(username, area, reason=reason)
            if event:
                events.append(event)
        return events

    def record_conflict_changed(self, conflict, reason=""):
        payload = _conflict_payload(conflict, reason=reason)
        conflict_id = payload.get("conflict_id") or payload.get("conflict_key") or "unknown"
        version = payload.get("version") or "0"
        participants = payload.get("participants") or []
        events = []
        for username in participants:
            key = "territory:conflict:{username}:{conflict_id}:{version}:{reason}".format(
                username=username,
                conflict_id=conflict_id,
                version=version,
                reason=_clean_text(reason, "conflict"),
            )
            events.append(self.delta_bus.record_change(
                username,
                TERRITORY_SCOPE,
                TERRITORY_CONFLICT_CHANGED,
                payload,
                entity_id=str(conflict_id),
                dedupe_key=key,
            ))
        return events

    def recovery_snapshot_for_point(self, lat, lng, actor_username=None):
        return {
            "scope": TERRITORY_SCOPE,
            "recovery_required": False,
            "snapshot_type": "territory.point",
            "snapshot": self.context_reader.for_point(lat, lng, actor_username=actor_username),
        }

    def recovery_snapshot_for_bbox(self, min_lat, min_lng, max_lat, max_lng, actor_username=None, limit=50):
        return {
            "scope": TERRITORY_SCOPE,
            "recovery_required": False,
            "snapshot_type": "territory.bbox",
            "snapshot": self.context_reader.for_bbox(
                min_lat,
                min_lng,
                max_lat,
                max_lng,
                actor_username=actor_username,
                limit=limit,
            ),
        }

    @staticmethod
    def recovery_diagnostics(delta_result):
        delta_result = delta_result or {}
        return {
            "scope": TERRITORY_SCOPE,
            "recovery_required": bool(delta_result.get("recovery_required")),
            "reason": delta_result.get("reason") or "",
            "current_version": int(delta_result.get("current_version") or 0),
            "changes_count": len(delta_result.get("changes") or []),
        }
