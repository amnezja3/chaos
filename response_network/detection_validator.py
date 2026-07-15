from __future__ import annotations

import copy
import hashlib
import math
from datetime import datetime, timezone

from .incident_store import ACTIVE_INCIDENT_STATUSES
from .npc_capsule_factory import BEHAVIOR_VERSION, position_at
from .npc_capsule_store import ACTIVE_CAPSULE_STATUSES


EARTH_RADIUS_M = 6371000.0
TERMINAL_OPERATION_STATUSES = {
    "cancelled",
    "canceled",
    "completed",
    "done",
    "failed",
    "timeout",
    "expired",
    "detected",
}


def _utc_now():
    return datetime.now(timezone.utc)


def _coerce_datetime(value=None):
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


def _number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(result):
        return None
    return result


def _position(value):
    if not isinstance(value, dict):
        return None
    lat = _number(value.get("lat"))
    lng = _number(value.get("lng", value.get("lon")))
    if lat is None or lng is None:
        return None
    return {"lat": lat, "lng": lng}


def _distance_m(left, right):
    left = _position(left)
    right = _position(right)
    if not left or not right:
        return None
    lat1 = math.radians(left["lat"])
    lat2 = math.radians(right["lat"])
    dlat = math.radians(right["lat"] - left["lat"])
    dlng = math.radians(right["lng"] - left["lng"])
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2.0) ** 2
    )
    return EARTH_RADIUS_M * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


class DetectionValidator:
    """Server-side validator for shadow detection feedback.

    The validator reconstructs public NPC movement and compares it with a
    candidate reported by a frontend probe. It records audit decisions only.
    """

    def __init__(self, incident_store, capsule_store, territory_context_reader, candidate_store):
        self.incident_store = incident_store
        self.capsule_store = capsule_store
        self.territory_context_reader = territory_context_reader
        self.candidate_store = candidate_store

    @staticmethod
    def validation_key(candidate, detected_at=None):
        candidate = candidate if isinstance(candidate, dict) else {}
        detected_dt = _coerce_datetime(detected_at or candidate.get("detected_at"))
        bucket = int(detected_dt.timestamp() // 10)
        parts = [
            _clean(candidate.get("incident_id"), "incident"),
            _clean(candidate.get("capsule_id") or candidate.get("npc_id"), "capsule"),
            _clean(candidate.get("actor_id"), "actor"),
            _clean(candidate.get("operation_id"), "operation"),
            str(bucket),
        ]
        digest = hashlib.sha1(":".join(parts).encode("utf-8")).hexdigest()[:16]
        return "detection:" + digest

    def _decision(self, status, candidate, reason="", detected_at=None, **extra):
        candidate = candidate if isinstance(candidate, dict) else {}
        mode = _clean(candidate.get("mode"), "shadow")
        decision = {
            "status": status,
            "result": status,
            "mode": mode,
            "reason": _clean(reason, status),
            "validation_key": self.validation_key(candidate, detected_at=detected_at),
            "incident_id": _clean(candidate.get("incident_id")),
            "capsule_id": _clean(candidate.get("capsule_id") or candidate.get("npc_id")),
            "actor_id": _clean(candidate.get("actor_id")),
            "operation_id": _clean(candidate.get("operation_id")),
            "validated_at": _iso(),
            "shadow_only": mode == "shadow",
            "visible_safe": mode == "visible_safe",
            "limited_enforcement": mode == "limited_enforcement",
            "full": mode == "full",
            "penalty_executed": False,
            "consequence_executed": False,
        }
        decision.update(extra)
        return decision

    @staticmethod
    def _operation_id(operation):
        return _clean(operation.get("operation_id") or operation.get("id"))

    @staticmethod
    def _operation_incident_id(operation):
        meter = operation.get("operation_risk_meter") if isinstance(operation.get("operation_risk_meter"), dict) else {}
        return _clean(meter.get("incident_id"))

    @staticmethod
    def _operation_position(operation):
        meter = operation.get("operation_risk_meter") if isinstance(operation.get("operation_risk_meter"), dict) else {}
        for source in (
            meter.get("position"),
            operation.get("current_position"),
            operation.get("target"),
            operation,
        ):
            pos = _position(source)
            if pos:
                return pos
        return None

    def _find_operation(self, profile, candidate, incident):
        operations = profile.get("operations") if isinstance(profile, dict) else []
        wanted_operation = _clean(candidate.get("operation_id"))
        incident_id = _clean((incident or {}).get("incident_id"))
        incident_operations = {
            _clean(item)
            for item in ((incident or {}).get("operation_ids") or [])
            if _clean(item)
        }
        for operation in operations or []:
            if not isinstance(operation, dict):
                continue
            operation_id = self._operation_id(operation)
            if wanted_operation and operation_id != wanted_operation:
                continue
            if wanted_operation:
                return operation
            if operation_id and operation_id in incident_operations:
                return operation
            if incident_id and self._operation_incident_id(operation) == incident_id:
                return operation
        return None

    @staticmethod
    def _is_operation_active(operation):
        if not isinstance(operation, dict):
            return False
        status = _clean(operation.get("status"), "running").lower()
        if status in TERMINAL_OPERATION_STATUSES:
            return False
        meter = operation.get("operation_risk_meter") if isinstance(operation.get("operation_risk_meter"), dict) else {}
        if meter and int(meter.get("active_contribution") or 0) <= 0 and meter.get("incident_id"):
            return False
        return True

    def _protected_passive_or_offline(self, actor_id, actor_position, operation):
        if operation:
            return False
        if not actor_id or not actor_position:
            return True
        try:
            context = self.territory_context_reader.for_point(
                actor_position["lat"],
                actor_position["lng"],
                actor_username=actor_id,
            )
        except Exception:
            return False
        return bool(context.get("inside_own_territory") and not context.get("inside_foreign_territory"))

    def validate(self, candidate, profile_loader=None, now=None):
        candidate = copy.deepcopy(candidate if isinstance(candidate, dict) else {})
        detected_at = _coerce_datetime(candidate.get("detected_at") or now)
        mode = _clean(candidate.get("mode"), "shadow")
        if mode not in {"shadow", "visible_safe", "limited_enforcement", "full"}:
            mode = "shadow"
        candidate["mode"] = mode
        candidate["detected_at"] = _iso(detected_at)
        candidate["validation_key"] = self.validation_key(candidate, detected_at=detected_at)

        actor_id = _clean(candidate.get("actor_id"))
        capsule_id = _clean(candidate.get("capsule_id") or candidate.get("npc_id"))
        incident_id = _clean(candidate.get("incident_id"))
        if not actor_id or not capsule_id or not incident_id:
            decision = self._decision("rejected", candidate, "missing_identity", detected_at=detected_at)
            return self._record(candidate, decision)

        if self.candidate_store.get_by_validation_key(candidate["validation_key"]):
            decision = self._decision("duplicate", candidate, "duplicate_candidate", detected_at=detected_at)
            return self._record(candidate, decision)

        incident = self.incident_store.get(incident_id)
        if not incident or _clean(incident.get("status")).lower() not in ACTIVE_INCIDENT_STATUSES:
            decision = self._decision("expired", candidate, "incident_not_active", detected_at=detected_at)
            return self._record(candidate, decision)

        capsule = self.capsule_store.get(capsule_id)
        if not capsule or _clean(capsule.get("status"), "active").lower() not in ACTIVE_CAPSULE_STATUSES:
            decision = self._decision("expired", candidate, "capsule_not_active", detected_at=detected_at)
            return self._record(candidate, decision)
        if _clean(capsule.get("incident_id")) != incident_id:
            decision = self._decision("rejected", candidate, "capsule_incident_mismatch", detected_at=detected_at)
            return self._record(candidate, decision)

        tracking_token = _clean(candidate.get("tracking_token"))
        if tracking_token not in {str(token) for token in (capsule.get("tracking_tokens") or [])}:
            decision = self._decision("rejected", candidate, "invalid_tracking_token", detected_at=detected_at)
            return self._record(candidate, decision)

        if int(candidate.get("behavior_version") or 0) != int(capsule.get("behavior_version") or BEHAVIOR_VERSION):
            decision = self._decision("rejected", candidate, "behavior_version_mismatch", detected_at=detected_at)
            return self._record(candidate, decision)
        if _clean(candidate.get("trajectory_seed")) != _clean(capsule.get("trajectory_seed")):
            decision = self._decision("rejected", candidate, "trajectory_seed_mismatch", detected_at=detected_at)
            return self._record(candidate, decision)

        spawn_at = _coerce_datetime(capsule.get("spawn_at"))
        expires_at = _coerce_datetime(capsule.get("expires_at"))
        if detected_at < spawn_at or detected_at >= expires_at:
            decision = self._decision("expired", candidate, "capsule_time_window_closed", detected_at=detected_at)
            return self._record(candidate, decision)

        expected_npc = _position(position_at(capsule, detected_at))
        reported_npc = _position(candidate.get("npc_position"))
        npc_error_m = _distance_m(expected_npc, reported_npc)
        if npc_error_m is None or npc_error_m > 45:
            decision = self._decision(
                "rejected",
                candidate,
                "npc_position_mismatch",
                detected_at=detected_at,
                npc_error_m=round(npc_error_m or 0, 2),
            )
            return self._record(candidate, decision)

        profile = profile_loader(actor_id, strip_sensitive=True, normalize_apps=False, normalize_files=False) if profile_loader else None
        operation = self._find_operation(profile or {}, candidate, incident)
        actor_position = _position(candidate.get("actor_position")) or self._operation_position(operation)
        if self._protected_passive_or_offline(actor_id, actor_position, operation):
            decision = self._decision("rejected", candidate, "passive_or_offline_territory_protected", detected_at=detected_at)
            return self._record(candidate, decision)
        if not self._is_operation_active(operation):
            decision = self._decision("expired", candidate, "operation_not_active", detected_at=detected_at)
            return self._record(candidate, decision)

        operation_id = self._operation_id(operation)
        if operation_id:
            candidate["operation_id"] = operation_id
        operation_incident = self._operation_incident_id(operation)
        incident_operations = {_clean(item) for item in (incident.get("operation_ids") or []) if _clean(item)}
        if operation_incident and operation_incident != incident_id:
            decision = self._decision("rejected", candidate, "operation_incident_mismatch", detected_at=detected_at)
            return self._record(candidate, decision)
        if incident_operations and operation_id not in incident_operations:
            decision = self._decision("rejected", candidate, "operation_not_in_incident", detected_at=detected_at)
            return self._record(candidate, decision)

        detection_radius = max(1.0, float(capsule.get("detection_radius_m") or 65))
        distance_m = _distance_m(expected_npc, actor_position)
        if distance_m is None or distance_m > (detection_radius + 15):
            decision = self._decision(
                "rejected",
                candidate,
                "actor_outside_detection_radius",
                detected_at=detected_at,
                distance_m=round(distance_m or 0, 2),
                detection_radius_m=round(detection_radius, 2),
            )
            return self._record(candidate, decision)

        enforcement_mode = mode in {"visible_safe", "limited_enforcement", "full"}
        status = "accepted" if enforcement_mode else "shadow_only"
        if mode == "full":
            reason = "valid_full_detection"
        elif mode == "limited_enforcement":
            reason = "valid_limited_enforcement_detection"
        elif mode == "visible_safe":
            reason = "valid_visible_safe_detection"
        else:
            reason = "valid_shadow_detection"
        decision = self._decision(
            status,
            candidate,
            reason,
            detected_at=detected_at,
            distance_m=round(distance_m, 2),
            detection_radius_m=round(detection_radius, 2),
            npc_error_m=round(npc_error_m, 2),
            operation_id=operation_id,
            accepted=enforcement_mode,
        )
        return self._record(candidate, decision)

    def _record(self, candidate, decision):
        stored, created = self.candidate_store.record(candidate, decision)
        result = copy.deepcopy(decision)
        if not created and result.get("status") != "duplicate":
            result["status"] = "duplicate"
            result["result"] = "duplicate"
        result["created"] = bool(created)
        result["candidate_id"] = stored.get("candidate_id") if stored else candidate.get("candidate_id")
        return result
