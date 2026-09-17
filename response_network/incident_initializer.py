from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from .incident_store import IncidentStore
from database import db_connect, loads_json


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
        "heat": int(meter.get("active_contribution", meter.get("current_heat")) or 0),
        "expires_at": operation.get('expires_at'),
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
        "expires_at": (previous or {}).get('expires_at') or _iso(now_dt + timedelta(minutes=INCIDENT_TTL_MINUTES)),
        "operation_ids": operation_ids,
        "operation_refs": refs,
        "suspect_refs": [{"actor_id": actor_id} for actor_id in sorted(set(suspect_ids) |
            {ref['actor_id'] for ref in (previous or {}).get('suspect_refs', [])})],
        "territory_refs": _territory_refs(refs, territory_context_reader=territory_context_reader),
        "npc_capsule_ids": (previous or {}).get('npc_capsule_ids') or [],
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
        with db_connect(self.incident_store.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            return self._sync_operations(operations, now, conn)

    def _sync_operations(self, operations, now, conn, incidents=None):
        operations = [item for item in (operations or []) if isinstance(item, dict)]
        now = _iso(now)
        incidents = incidents if incidents is not None else self.incident_store.related(operations, conn=conn)
        for incident in incidents:
            if incident.get('status') == 'cooling' and _coerce_datetime(incident['expires_at']) <= _coerce_datetime(now):
                incident.update(status='resolved', lifecycle_reason='cooling_elapsed')
                self.incident_store.upsert(incident, event_type='incident.resolved', now=now, conn=conn)
        incidents = [i for i in incidents if i.get('status') != 'resolved']
        # Refresh other actors from canonical rows while holding the incident write lock.
        incoming_ids = {op.get('operation_id') for op in operations}
        has_operations = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='player_operations'").fetchone()
        if has_operations:
            for operation in operations:
                row = conn.execute('SELECT operation_json, version FROM player_operations WHERE operation_id=?',
                                   (operation.get('operation_id'),)).fetchone()
                if row and operation.get('_runtime_version') is not None and int(row['version']) > int(operation['_runtime_version']):
                    operation.clear()
                    operation.update(loads_json(row['operation_json'], {}))
                    operation['_runtime_version'] = int(row['version'])
            for incident in incidents:
                for op_id in incident.get('operation_ids') or []:
                    if op_id in incoming_ids:
                        continue
                    row = conn.execute('SELECT operation_json FROM player_operations WHERE operation_id=?', (op_id,)).fetchone()
                    if row:
                        operations.append(loads_json(row['operation_json'], {}))
                        incoming_ids.add(op_id)
        candidates = [operation for operation in operations if _is_active_incident_candidate(operation)]
        by_operation_id = {
            _clean(operation.get("operation_id")): operation
            for operation in operations
            if _clean(operation.get("operation_id"))
            and str(operation.get('status') or '').lower() not in {'cancelled','canceled','completed','timeout','failed','detected','expired','done','resolved'}
            and (not operation.get('expires_at') or _coerce_datetime(operation['expires_at']) > _coerce_datetime(now))
        }
        known_operation_ids = {
            _clean(operation.get("operation_id"))
            for operation in operations
            if _clean(operation.get("operation_id"))
        }
        candidates = [op for op in candidates if op.get('operation_id') in by_operation_id]
        active_incidents = incidents
        touched_incident_ids = set()
        actions = []

        for operation in candidates:
            operation_id = _clean(operation.get("operation_id"))
            if not operation_id:
                continue
            position = _operation_position(operation)
            assigned_id = _clean(_operation_meter(operation).get("incident_id"))
            incident = self.incident_store.get(assigned_id, conn=conn) if assigned_id else None
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
                saved = self.incident_store.upsert(incident, event_type="incident.created", now=now, conn=conn)
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

        for incident_entry in active_incidents:
            incident = self.incident_store.get(incident_entry['incident_id'], conn=conn)
            incident_operation_ids = {str(item) for item in (incident.get("operation_ids") or [])}
            if operations and incident.get("incident_id") not in touched_incident_ids and not (incident_operation_ids & known_operation_ids):
                continue
            refs = []
            previous_refs = {ref['operation_id']: ref for ref in incident.get('operation_refs', [])}
            for operation_id in incident.get("operation_ids") or []:
                operation = by_operation_id.get(str(operation_id))
                if operation:
                    refs.append(_operation_ref(operation))
                elif operation_id not in known_operation_ids and operation_id in previous_refs:
                    ref = previous_refs[operation_id]
                    deadline = ref.get('expires_at') or incident.get('expires_at')
                    if deadline and _coerce_datetime(deadline) > _coerce_datetime(now):
                        refs.append(ref)
            for operation in candidates:
                meter_incident_id = _clean(_operation_meter(operation).get("incident_id"))
                operation_id = _clean(operation.get("operation_id"))
                if meter_incident_id == incident.get("incident_id") and operation_id not in {ref["operation_id"] for ref in refs}:
                    refs.append(_operation_ref(operation))

            if not refs:
                cooling = dict(incident)
                if cooling.get('status') != 'cooling':
                    deadlines = [ref.get('expires_at') for ref in previous_refs.values() if ref.get('expires_at')]
                    ended = max(deadlines, key=_coerce_datetime) if deadlines else now
                    ended = min(_coerce_datetime(ended), _coerce_datetime(now))
                    cooling.update(status='cooling', cooling_since=_iso(ended),
                        expires_at=_iso(ended + timedelta(minutes=30)),
                        operation_ids=[], operation_refs=[], heat=0,
                        lifecycle_reason='last_operation_ended')
                if _coerce_datetime(cooling['expires_at']) <= _coerce_datetime(now):
                    cooling.update(status='resolved', lifecycle_reason='cooling_elapsed')
                saved = self.incident_store.upsert(cooling, event_type='incident.' + cooling['status'], now=now, conn=conn)
                if saved['version'] != incident['version']:
                    actions.append({'action': 'cancelled' if cooling['status'] == 'resolved' else 'recalculated',
                                    'incident_id': incident['incident_id']})
                continue

            recalculated = _build_incident_from_refs(
                incident["incident_id"],
                refs,
                now=now,
                previous=incident,
                territory_context_reader=self.territory_context_reader,
            )
            saved = self.incident_store.upsert(recalculated, event_type="incident.recalculated", now=now, conn=conn)
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

    def tick_lifecycle(self, now=None, limit=32):
        actions = []
        for selected in self.incident_store.lifecycle_batch(limit):
            with db_connect(self.incident_store.db_path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                incident = self.incident_store.get(selected['incident_id'], conn=conn)
                if incident['status'] not in {'candidate', 'active', 'escalated', 'cooling'}:
                    continue
                result = self._sync_operations([], now, conn, incidents=[incident])
                actions.extend(result['actions'])
                # Fair round-robin even when the material state did not change.
                conn.execute('UPDATE response_incidents SET updated_at=? WHERE incident_id=?',
                             (_iso(now), incident['incident_id']))
        return actions
