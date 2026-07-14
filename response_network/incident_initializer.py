from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .incident_store import IncidentStore


MERGE_RADIUS_M = 260
DEFAULT_SEARCH_RADIUS_M = 220
INCIDENT_TTL_MINUTES = 30


def _utc_now():
    return datetime.now(timezone.utc)


def _coerce_datetime(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    elif value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        dt = _utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(value=None):
    return _coerce_datetime(value).isoformat()


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _distance_m(left, right):
    if not left or not right:
        return float("inf")
    try:
        lat1 = math.radians(float(left.get("lat")))
        lng1 = math.radians(float(left.get("lng", left.get("lon"))))
        lat2 = math.radians(float(right.get("lat")))
        lng2 = math.radians(float(right.get("lng", right.get("lon"))))
    except (TypeError, ValueError):
        return float("inf")
    d_lat = lat2 - lat1
    d_lng = lng2 - lng1
    a = math.sin(d_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    return 6371000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _operation_meter(operation):
    meter = (operation or {}).get("operation_risk_meter")
    return meter if isinstance(meter, dict) else {}


def _operation_position(operation):
    meter = _operation_meter(operation)
    position = meter.get("position") if isinstance(meter.get("position"), dict) else {}
    if position:
        return position
    target = (operation or {}).get("target")
    target = target if isinstance(target, dict) else {}
    try:
        return {
            "lat": float(target.get("lat")),
            "lng": float(target.get("lng", target.get("lon"))),
        }
    except (TypeError, ValueError):
        return {}


def _is_active_incident_candidate(operation):
    meter = _operation_meter(operation)
    if not meter.get("incident_crossed"):
        return False
    if int(meter.get("active_contribution") or 0) <= 0:
        return False
    status = str((operation or {}).get("status") or "").lower()
    if status in {"cancelled", "canceled", "completed", "timeout", "failed", "detected"}:
        return False
    return bool(_operation_position(operation))


def _operation_ref(operation):
    meter = _operation_meter(operation)
    return {
        "operation_id": _clean(operation.get("operation_id")),
        "actor_id": _clean(meter.get("actor_id") or operation.get("owner_username")),
        "target_id": _clean(meter.get("target_id") or operation.get("target_id")),
        "operation_type": _clean(operation.get("operation_type")),
        "heat": int(meter.get("active_contribution") or meter.get("current_heat") or 0),
        "risk_version": int(meter.get("risk_version") or 0),
        "position": _operation_position(operation),
    }


def _level_for_heat(heat):
    if heat >= 90:
        return 4
    if heat >= 75:
        return 3
    if heat >= 60:
        return 2
    return 1


def _status_for_heat(heat):
    if heat >= 85:
        return "escalated"
    return "active"


def _weighted_center(refs):
    total = sum(max(1, int(ref.get("heat") or 0)) for ref in refs)
    if not total:
        total = len(refs) or 1
    lat = 0.0
    lng = 0.0
    for ref in refs:
        weight = max(1, int(ref.get("heat") or 0))
        position = ref.get("position") or {}
        lat += float(position.get("lat") or 0) * weight
        lng += float(position.get("lng") or 0) * weight
    return {
        "lat": round(lat / total, 7),
        "lng": round(lng / total, 7),
    }


def _territory_refs(refs, territory_context_reader=None):
    if not territory_context_reader:
        return []
    refs_by_id = {}
    for ref in refs:
        position = ref.get("position") or {}
        try:
            context = territory_context_reader.for_point(
                position.get("lat"),
                position.get("lng"),
                actor_username=ref.get("actor_id"),
            )
        except (TypeError, ValueError):
            continue
        for territory in context.get("territories") or []:
            territory_id = territory.get("territory_id")
            if not territory_id:
                continue
            refs_by_id[territory_id] = {
                "territory_id": territory_id,
                "owner_id": territory.get("owner_id"),
                "conflict_ids": territory.get("conflict_ids", []),
            }
    return list(refs_by_id.values())


def _build_incident_from_refs(incident_id, refs, now=None, previous=None, territory_context_reader=None):
    now_dt = _coerce_datetime(now)
    heat = min(100, sum(int(ref.get("heat") or 0) for ref in refs))
    center = _weighted_center(refs)
    operation_ids = [ref["operation_id"] for ref in refs if ref.get("operation_id")]
    suspect_ids = sorted({ref.get("actor_id") for ref in refs if ref.get("actor_id")})
    incident = {
        "incident_id": incident_id,
        "status": _status_for_heat(heat),
        "level": _level_for_heat(heat),
        "heat": heat,
        "center": center,
        "search_radius_m": DEFAULT_SEARCH_RADIUS_M + (40 * max(0, len(operation_ids) - 1)),
        "created_at": (previous or {}).get("created_at") or _iso(now_dt),
        "updated_at": _iso(now_dt),
        "expires_at": _iso(now_dt + timedelta(minutes=INCIDENT_TTL_MINUTES)),
        "operation_ids": operation_ids,
        "operation_refs": refs,
        "suspect_refs": [{"actor_id": actor_id} for actor_id in suspect_ids],
        "territory_refs": _territory_refs(refs, territory_context_reader=territory_context_reader),
        "npc_capsule_ids": [],
        "seed": (previous or {}).get("seed") or incident_id,
        "visible": False,
        "publication_enabled": False,
        "npc_enabled": False,
        "warning_enabled": False,
        "consequences_enabled": False,
    }
    return incident


class IncidentInitializer:
    """Creates and maintains invisible incidents from operation risk meters."""

    def __init__(self, incident_store=None, territory_context_reader=None):
        self.incident_store = incident_store or IncidentStore()
        self.territory_context_reader = territory_context_reader

    def _find_merge_target(self, position, active_incidents):
        best = None
        best_distance = float("inf")
        for incident in active_incidents:
            distance = _distance_m(position, incident.get("center") or {})
            if distance <= MERGE_RADIUS_M and distance < best_distance:
                best = incident
                best_distance = distance
        return best

    @staticmethod
    def _assign_incident(operation, incident_id):
        meter = _operation_meter(operation)
        if not meter:
            return
        meter["incident_id"] = incident_id
        operation["operation_risk_meter"] = meter

    @staticmethod
    def _clear_incident(operation):
        meter = _operation_meter(operation)
        if not meter:
            return
        meter["incident_id"] = None
        operation["operation_risk_meter"] = meter

    def sync_operations(self, operations, now=None):
        operations = [item for item in (operations or []) if isinstance(item, dict)]
        candidates = [operation for operation in operations if _is_active_incident_candidate(operation)]
        by_operation_id = {
            _clean(operation.get("operation_id")): operation
            for operation in candidates
            if _clean(operation.get("operation_id"))
        }
        known_operation_ids = {
            _clean(operation.get("operation_id"))
            for operation in operations
            if _clean(operation.get("operation_id"))
        }
        active_incidents = self.incident_store.list_active()
        touched_incident_ids = set()
        actions = []

        for operation in candidates:
            operation_id = _clean(operation.get("operation_id"))
            if not operation_id:
                continue
            position = _operation_position(operation)
            assigned_id = _clean(_operation_meter(operation).get("incident_id"))
            incident = self.incident_store.get(assigned_id) if assigned_id else None
            if not incident or incident.get("status") not in {"candidate", "active", "escalated", "cooling"}:
                incident = self._find_merge_target(position, active_incidents)
            if not incident:
                incident_id = self.incident_store.stable_id(position, operation_id)
                incident = _build_incident_from_refs(
                    incident_id,
                    [_operation_ref(operation)],
                    now=now,
                    territory_context_reader=self.territory_context_reader,
                )
                saved = self.incident_store.upsert(incident, event_type="incident.created", now=now)
                active_incidents.append(saved)
                self._assign_incident(operation, saved["incident_id"])
                touched_incident_ids.add(saved["incident_id"])
                actions.append({"action": "created", "incident_id": saved["incident_id"], "operation_id": operation_id})
                continue
            previous_incident_id = _clean(_operation_meter(operation).get("incident_id"))
            self._assign_incident(operation, incident["incident_id"])
            touched_incident_ids.add(incident["incident_id"])
            if previous_incident_id != incident["incident_id"]:
                actions.append({"action": "linked", "incident_id": incident["incident_id"], "operation_id": operation_id})

        for incident in self.incident_store.list_active():
            incident_operation_ids = {str(item) for item in (incident.get("operation_ids") or [])}
            if incident.get("incident_id") not in touched_incident_ids and not (incident_operation_ids & known_operation_ids):
                continue
            refs = []
            for operation_id in incident.get("operation_ids") or []:
                operation = by_operation_id.get(str(operation_id))
                if operation:
                    refs.append(_operation_ref(operation))
            for operation in candidates:
                meter_incident_id = _clean(_operation_meter(operation).get("incident_id"))
                operation_id = _clean(operation.get("operation_id"))
                if meter_incident_id == incident.get("incident_id") and operation_id not in {ref["operation_id"] for ref in refs}:
                    refs.append(_operation_ref(operation))

            if not refs:
                cancelled = self.incident_store.cancel(incident["incident_id"], reason="no_active_operations", now=now)
                for operation in operations:
                    if _clean(_operation_meter(operation).get("incident_id")) == incident["incident_id"]:
                        self._clear_incident(operation)
                actions.append({"action": "cancelled", "incident_id": incident["incident_id"]})
                continue

            recalculated = _build_incident_from_refs(
                incident["incident_id"],
                refs,
                now=now,
                previous=incident,
                territory_context_reader=self.territory_context_reader,
            )
            saved = self.incident_store.upsert(recalculated, event_type="incident.recalculated", now=now)
            for ref in refs:
                operation = by_operation_id.get(ref.get("operation_id"))
                if operation:
                    self._assign_incident(operation, saved["incident_id"])
            if int(saved.get("version") or 0) != int(incident.get("version") or 0):
                actions.append({
                    "action": "recalculated",
                    "incident_id": saved["incident_id"],
                    "operations": saved.get("operation_ids", []),
                })

        return {
            "candidates": len(candidates),
            "actions": actions,
        }
