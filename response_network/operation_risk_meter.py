from __future__ import annotations

import math
from datetime import datetime, timezone


RISK_METER_MODE = "observe"
WARNING_THRESHOLD = 45
INCIDENT_THRESHOLD = 60

TERMINAL_CANCELLED_STATUSES = {"cancelled", "canceled"}
TERMINAL_INACTIVE_STATUSES = {
    "cancelled",
    "canceled",
    "completed",
    "timeout",
    "failed",
    "detected",
}

BASE_HEAT_BY_OPERATION = {
    "atm_log_extraction": 22,
    "persistent_sniffer": 20,
    "vehicle_tracking": 16,
    "device_tracking": 16,
    "camera_stream": 14,
    "wifi_scanner": 12,
    "audio_interference": 12,
    "vehicle_ecu": 15,
    "generic_trace": 10,
}


def _utc_now():
    return datetime.now(timezone.utc)


def _coerce_datetime(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    elif value:
        raw = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
    else:
        dt = _utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(value=None):
    return _coerce_datetime(value).isoformat()


def _timestamp(value):
    try:
        return _coerce_datetime(value).timestamp()
    except (TypeError, ValueError):
        return None


def _clamp(value, minimum=0, maximum=100):
    try:
        value = int(round(float(value or 0)))
    except (TypeError, ValueError):
        value = minimum
    return max(minimum, min(maximum, value))


def _operation_id(operation):
    return str((operation or {}).get("operation_id") or "unknown")


def _target_snapshot(operation, target=None):
    if isinstance(target, dict):
        return target
    candidate = (operation or {}).get("target")
    return candidate if isinstance(candidate, dict) else {}


def _position_from_operation(operation, target=None):
    target = _target_snapshot(operation, target)
    try:
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
    except (TypeError, ValueError):
        return {}
    if math.isnan(lat) or math.isnan(lng):
        return {}
    return {"lat": lat, "lng": lng}


def _base_heat(operation):
    operation_type = str((operation or {}).get("operation_type") or "").strip()
    return BASE_HEAT_BY_OPERATION.get(operation_type, 8)


def _time_heat(operation, now_ts=None):
    started = _timestamp((operation or {}).get("started_at"))
    expires = _timestamp((operation or {}).get("expires_at"))
    if started is None or expires is None or expires <= started:
        return 0
    current = _timestamp(now_ts) if now_ts is not None else _utc_now().timestamp()
    ratio = max(0.0, min(1.0, (current - started) / (expires - started)))
    return _clamp(ratio * 30, 0, 30)


def _tool_quality(operation, tool=None):
    if isinstance(tool, dict):
        return {
            "creator_power": tool.get("creator_power"),
            "quality_score": tool.get("quality_score"),
            "reliability": tool.get("reliability"),
        }
    quality = (operation or {}).get("source_app_quality")
    return quality if isinstance(quality, dict) else {}


def _tool_modifier(operation, tool=None):
    quality = _tool_quality(operation, tool)
    power = _clamp(quality.get("creator_power"), 0, 100)
    reliability = _clamp(quality.get("reliability"), 0, 100)
    app_quality = _clamp(quality.get("quality_score"), 0, 100)

    noisy_power = max(0, power - 55) // 8
    unreliable = max(0, 65 - reliability) // 7
    rough_quality = max(0, 55 - app_quality) // 8
    return _clamp(noisy_power + unreliable + rough_quality, 0, 20)


def _security_modifier(operation, target=None):
    target = _target_snapshot(operation, target)
    security = target.get("security")
    if not isinstance(security, dict):
        security = target

    enabled = 0
    numeric_pressure = 0
    for key, value in security.items():
        if isinstance(value, bool):
            enabled += 1 if value else 0
        elif isinstance(value, (int, float)):
            numeric_pressure += max(0, min(100, float(value)))
        elif isinstance(value, str) and value.strip().lower() in {"on", "enabled", "active", "true"}:
            enabled += 1

    modifier = enabled * 4
    if numeric_pressure:
        modifier += min(18, int(numeric_pressure / 30))
    risk = str(target.get("risk") or target.get("risk_level") or "").lower()
    if "high" in risk:
        modifier += 10
    elif "medium" in risk:
        modifier += 5
    return _clamp(modifier, 0, 25)


def _conflict_modifier(operation, conflict=None):
    if isinstance(conflict, dict) and conflict:
        return 25 if conflict.get("status") == "active" else 12
    target_mode = str((operation or {}).get("target_mode") or "").lower()
    operation_type = str((operation or {}).get("operation_type") or "").lower()
    target = _target_snapshot(operation)
    if target_mode in {"territory_contest", "contested", "conflict"}:
        return 25
    if target.get("conflict_id") or target.get("conflict_key"):
        return 22
    if "support" in operation_type or "contested" in operation_type:
        return 15
    return 0


def _risk_level(score):
    if score >= INCIDENT_THRESHOLD:
        return "incident_threshold"
    if score >= WARNING_THRESHOLD:
        return "warning_threshold"
    if score >= 25:
        return "elevated"
    if score > 0:
        return "low"
    return "none"


def _dedupe_key(operation_id, threshold):
    return f"operation-risk:{operation_id}:{threshold}"


def _signature(meter):
    return {
        key: meter.get(key)
        for key in (
            "mode",
            "base_heat",
            "time_heat",
            "tool_modifier",
            "security_modifier",
            "conflict_modifier",
            "current_heat",
            "active_contribution",
            "risk_level",
            "warning_crossed",
            "incident_crossed",
            "warning_cancelled",
            "incident_cancelled",
            "cancelled",
        )
    }


def calculate_operation_risk(operation, tool=None, target=None, conflict=None, rules=None, now_ts=None):
    operation = operation if isinstance(operation, dict) else {}
    previous = operation.get("operation_risk_meter")
    previous = previous if isinstance(previous, dict) else {}
    operation_id = _operation_id(operation)
    now_iso = _iso(now_ts)
    status = str(operation.get("status") or "").lower()
    cancelled = status in TERMINAL_CANCELLED_STATUSES

    if cancelled:
        cancelled_thresholds = []
        if previous.get("warning_crossed") or previous.get("warning_dedupe_key"):
            cancelled_thresholds.append("warning")
        if previous.get("incident_crossed") or previous.get("incident_dedupe_key"):
            cancelled_thresholds.append("incident")
        return {
            "schema": 1,
            "mode": RISK_METER_MODE,
            "operation_id": operation_id,
            "actor_id": operation.get("owner_username") or operation.get("actor_id") or "",
            "target_id": operation.get("target_id") or "",
            "position": _position_from_operation(operation, target),
            "base_heat": 0,
            "time_heat": 0,
            "tool_modifier": 0,
            "security_modifier": 0,
            "conflict_modifier": 0,
            "current_heat": 0,
            "active_contribution": 0,
            "risk_level": "cancelled",
            "warning_threshold": WARNING_THRESHOLD,
            "incident_threshold": INCIDENT_THRESHOLD,
            "warning_crossed": False,
            "incident_crossed": False,
            "warning_issued_at": None,
            "incident_id": None,
            "warning_dedupe_key": previous.get("warning_dedupe_key") or "",
            "incident_dedupe_key": previous.get("incident_dedupe_key") or "",
            "warning_cancelled": True,
            "incident_cancelled": True,
            "cancelled": True,
            "cancelled_thresholds": cancelled_thresholds,
            "updated_at": now_iso,
            "reasons": ["operation_cancelled"],
        }

    base_heat = _base_heat(operation)
    time_heat = _time_heat(operation, now_ts=now_ts)
    tool_modifier = _tool_modifier(operation, tool=tool)
    security_modifier = _security_modifier(operation, target=target)
    conflict_modifier = _conflict_modifier(operation, conflict=conflict)
    current_heat = _clamp(base_heat + time_heat + tool_modifier + security_modifier + conflict_modifier, 0, 100)
    active_contribution = 0 if status in TERMINAL_INACTIVE_STATUSES else current_heat

    warning_crossed = current_heat >= WARNING_THRESHOLD
    incident_crossed = current_heat >= INCIDENT_THRESHOLD
    warning_dedupe = previous.get("warning_dedupe_key") or (_dedupe_key(operation_id, "warning") if warning_crossed else "")
    incident_dedupe = previous.get("incident_dedupe_key") or (_dedupe_key(operation_id, "incident") if incident_crossed else "")

    return {
        "schema": 1,
        "mode": RISK_METER_MODE,
        "operation_id": operation_id,
        "actor_id": operation.get("owner_username") or operation.get("actor_id") or "",
        "target_id": operation.get("target_id") or "",
        "position": _position_from_operation(operation, target),
        "base_heat": base_heat,
        "time_heat": time_heat,
        "tool_modifier": tool_modifier,
        "security_modifier": security_modifier,
        "conflict_modifier": conflict_modifier,
        "current_heat": current_heat,
        "active_contribution": active_contribution,
        "risk_level": _risk_level(current_heat),
        "warning_threshold": WARNING_THRESHOLD,
        "incident_threshold": INCIDENT_THRESHOLD,
        "warning_crossed": warning_crossed,
        "incident_crossed": incident_crossed,
        "warning_crossed_at": previous.get("warning_crossed_at") or (now_iso if warning_crossed else None),
        "incident_crossed_at": previous.get("incident_crossed_at") or (now_iso if incident_crossed else None),
        "warning_issued_at": None,
        "incident_id": previous.get("incident_id"),
        "warning_dedupe_key": warning_dedupe,
        "incident_dedupe_key": incident_dedupe,
        "warning_cancelled": False,
        "incident_cancelled": False,
        "cancelled": False,
        "updated_at": now_iso,
        "reasons": [
            "base_heat",
            "time_heat",
            "tool_modifier" if tool_modifier else "",
            "security_modifier" if security_modifier else "",
            "conflict_modifier" if conflict_modifier else "",
        ],
    }


def update_operation_risk_meter(operation, tool=None, target=None, conflict=None, rules=None, now_ts=None):
    if not isinstance(operation, dict):
        return False
    previous = operation.get("operation_risk_meter")
    previous = previous if isinstance(previous, dict) else {}
    next_meter = calculate_operation_risk(
        operation,
        tool=tool,
        target=target,
        conflict=conflict,
        rules=rules,
        now_ts=now_ts,
    )
    previous_signature = _signature(previous)
    next_signature = _signature(next_meter)
    if previous and previous_signature == next_signature:
        next_meter["risk_version"] = int(previous.get("risk_version") or 1)
        next_meter["updated_at"] = previous.get("updated_at") or next_meter["updated_at"]
        operation["operation_risk_meter"] = next_meter
        return False

    next_meter["risk_version"] = int(previous.get("risk_version") or 0) + 1
    operation["operation_risk_meter"] = next_meter
    return True


def cancel_operation_risk_meter(operation, now_ts=None):
    if not isinstance(operation, dict):
        return False
    operation["status"] = "cancelled"
    return update_operation_risk_meter(operation, now_ts=now_ts)
