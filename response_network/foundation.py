from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from config import (
    RESPONSE_NETWORK_AUDIT_LIMIT,
    RESPONSE_NETWORK_DEPLOYMENT_MODE,
    RESPONSE_NETWORK_FLAGS,
    RESPONSE_NETWORK_KILL_SWITCHES,
)


RESPONSE_NETWORK_MODES = (
    "disabled",
    "observe",
    "shadow",
    "visible_safe",
    "limited_enforcement",
    "full",
)

RESPONSE_MAP_ENDPOINTS = {
    "/api/map/player-areas": "map.player_areas",
    "/api/map/clan-vulnerabilities": "map.clan_vulnerabilities",
    "/api/operations": "map.operations_summary",
    "/api/map/player-actors": "map.player_actors",
}


class ResponseNetworkClock:
    """Tiny injectable clock for deterministic Response Network tests."""

    def __init__(self, fixed_now=None):
        self._fixed_now = self._coerce_datetime(fixed_now) if fixed_now else None

    @staticmethod
    def _coerce_datetime(value):
        if isinstance(value, datetime):
            dt = value
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def now(self):
        return self._fixed_now or datetime.now(timezone.utc)

    def iso_now(self):
        return self.now().isoformat()


@dataclass(frozen=True)
class ResponseNetworkSafetyConfig:
    mode: str
    flags: dict
    kill_switches: dict

    @classmethod
    def from_runtime(cls):
        mode = (RESPONSE_NETWORK_DEPLOYMENT_MODE or "disabled").strip().lower()
        if mode not in RESPONSE_NETWORK_MODES:
            mode = "disabled"
        return cls(
            mode=mode,
            flags=dict(RESPONSE_NETWORK_FLAGS),
            kill_switches=dict(RESPONSE_NETWORK_KILL_SWITCHES),
        )

    @property
    def active(self):
        return self.mode != "disabled" and bool(self.flags.get("response_network_enabled"))

    @property
    def safe_to_publish(self):
        return self.active and not bool(self.kill_switches.get("map_publication", True))

    def as_dict(self):
        return {
            "mode": self.mode,
            "active": self.active,
            "safe_to_publish": self.safe_to_publish,
            "flags": dict(self.flags),
            "kill_switches": dict(self.kill_switches),
        }


class ResponseNetworkAuditLog:
    def __init__(self, limit=RESPONSE_NETWORK_AUDIT_LIMIT, clock=None):
        self.limit = max(1, int(limit or RESPONSE_NETWORK_AUDIT_LIMIT))
        self.clock = clock or ResponseNetworkClock()
        self._events = deque(maxlen=self.limit)
        self._metrics = {}
        self._lock = Lock()

    def record(self, event_type, payload=None, scope="response_network", actor_id=None):
        payload = payload if isinstance(payload, dict) else {}
        event = {
            "created_at": self.clock.iso_now(),
            "scope": str(scope or "response_network"),
            "type": str(event_type or "response.audit"),
            "actor_id": str(actor_id or "-"),
            "payload": dict(payload),
        }
        with self._lock:
            self._events.append(event)
        return event

    def record_map_endpoint(self, path, elapsed_ms, status_code=None, payload_size=None, method="GET"):
        endpoint = RESPONSE_MAP_ENDPOINTS.get(path)
        if not endpoint:
            return None
        try:
            elapsed_ms = int(elapsed_ms or 0)
        except (TypeError, ValueError):
            elapsed_ms = 0
        try:
            payload_size = int(payload_size or 0)
        except (TypeError, ValueError):
            payload_size = 0

        with self._lock:
            metric = self._metrics.setdefault(endpoint, {
                "path": path,
                "count": 0,
                "total_ms": 0,
                "max_ms": 0,
                "last_ms": 0,
                "last_status": None,
                "last_payload_size": 0,
            })
            metric["count"] += 1
            metric["total_ms"] += elapsed_ms
            metric["max_ms"] = max(metric["max_ms"], elapsed_ms)
            metric["last_ms"] = elapsed_ms
            metric["last_status"] = status_code
            metric["last_payload_size"] = payload_size

        return self.record(
            "response.map_endpoint_measured",
            {
                "endpoint": endpoint,
                "path": path,
                "method": method,
                "elapsed_ms": elapsed_ms,
                "status_code": status_code,
                "payload_size": payload_size,
            },
            scope="response_network.measurement",
        )

    def recent_events(self, limit=25):
        try:
            limit = max(1, int(limit or 25))
        except (TypeError, ValueError):
            limit = 25
        with self._lock:
            return list(self._events)[-limit:]

    def map_metrics(self):
        with self._lock:
            result = {}
            for endpoint, metric in self._metrics.items():
                count = int(metric.get("count") or 0)
                result[endpoint] = {
                    **metric,
                    "avg_ms": int(round(metric["total_ms"] / count)) if count else 0,
                }
            return result


response_audit_log = ResponseNetworkAuditLog()


def record_response_audit_event(event_type, payload=None, scope="response_network", actor_id=None):
    return response_audit_log.record(event_type, payload=payload, scope=scope, actor_id=actor_id)


def record_response_map_endpoint_measurement(path, elapsed_ms, status_code=None, payload_size=None, method="GET"):
    return response_audit_log.record_map_endpoint(
        path,
        elapsed_ms,
        status_code=status_code,
        payload_size=payload_size,
        method=method,
    )


def get_response_map_endpoint_metrics():
    return response_audit_log.map_metrics()


def build_response_network_safety_snapshot(limit=25):
    config = ResponseNetworkSafetyConfig.from_runtime()
    return {
        "success": True,
        "response_network": config.as_dict(),
        "clock": {
            "now": ResponseNetworkClock().iso_now(),
            "testable": True,
        },
        "map_endpoint_measurements": get_response_map_endpoint_metrics(),
        "observed_map_endpoints": dict(RESPONSE_MAP_ENDPOINTS),
        "recent_audit_events": response_audit_log.recent_events(limit=limit),
        "runtime_active": False,
        "incidents_enabled": False,
        "npc_enabled": False,
        "detection_enabled": False,
        "consequences_enabled": False,
    }
