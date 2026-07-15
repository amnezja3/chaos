from __future__ import annotations

import copy
import hashlib
import math
from datetime import datetime, timedelta, timezone


BEHAVIOR_VERSION = 1
SNIKER_DIRECTIONS_8 = (
    "up",
    "up_right",
    "right",
    "down_right",
    "down",
    "down_left",
    "left",
    "up_left",
)
VISUAL_FAMILIES = ("police", "cyberpolice", "secretservice")
TRAJECTORY_TYPES = ("orbital_search", "spiral_sweep", "intercept_loop")


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


def _stable_float(seed, minimum=0.0, maximum=1.0):
    digest = hashlib.sha1(str(seed).encode("utf-8")).hexdigest()[:12]
    ratio = int(digest, 16) / float(0xFFFFFFFFFFFF)
    return minimum + ((maximum - minimum) * ratio)


def _project_point(center, distance_m, bearing_deg):
    lat = math.radians(float(center.get("lat") or 0.0))
    lng = math.radians(float(center.get("lng") or 0.0))
    bearing = math.radians(float(bearing_deg or 0.0))
    angular = float(distance_m or 0.0) / 6371000.0
    target_lat = math.asin(
        math.sin(lat) * math.cos(angular)
        + math.cos(lat) * math.sin(angular) * math.cos(bearing)
    )
    target_lng = lng + math.atan2(
        math.sin(bearing) * math.sin(angular) * math.cos(lat),
        math.cos(angular) - math.sin(lat) * math.sin(target_lat),
    )
    return {
        "lat": round(math.degrees(target_lat), 7),
        "lng": round(math.degrees(target_lng), 7),
    }


def _direction_from_angle(angle_deg):
    normalized = (float(angle_deg or 0.0) + 360.0) % 360.0
    index = int(((normalized + 22.5) % 360.0) // 45.0)
    return SNIKER_DIRECTIONS_8[index]


def _service_plan(level):
    try:
        level = max(1, int(level or 1))
    except (TypeError, ValueError):
        level = 1
    if level >= 4:
        return [
            ("secretservice", 4),
            ("cyberpolice", 3),
            ("cyberpolice", 3),
        ]
    if level == 3:
        return [
            ("cyberpolice", 3),
            ("police", 2),
        ]
    if level == 2:
        return [
            ("police", 2),
            ("cyberpolice", 2),
        ]
    return [("police", 1)]


def _trajectory_for(service_type, index):
    if service_type == "secretservice":
        return "intercept_loop"
    if service_type == "cyberpolice":
        return "spiral_sweep" if index % 2 else "orbital_search"
    return "orbital_search"


def _capsule_signature(capsule):
    capsule = capsule if isinstance(capsule, dict) else {}
    return {
        "incident_id": capsule.get("incident_id"),
        "service_type": capsule.get("service_type"),
        "service_level": capsule.get("service_level"),
        "spawn_at": capsule.get("spawn_at"),
        "expires_at": capsule.get("expires_at"),
        "origin": capsule.get("origin"),
        "incident_center": capsule.get("incident_center"),
        "patrol_radius_m": capsule.get("patrol_radius_m"),
        "detection_radius_m": capsule.get("detection_radius_m"),
        "speed_mps": capsule.get("speed_mps"),
        "trajectory_type": capsule.get("trajectory_type"),
        "trajectory_seed": capsule.get("trajectory_seed"),
        "trajectory_phase_deg": capsule.get("trajectory_phase_deg"),
        "behavior_version": capsule.get("behavior_version"),
        "visual_family": capsule.get("visual_family"),
    }


def public_capsule_payload(capsule):
    capsule = copy.deepcopy(capsule if isinstance(capsule, dict) else {})
    allowed = {
        "capsule_id",
        "incident_id",
        "npc_id",
        "actor_type",
        "service_type",
        "service_level",
        "spawn_at",
        "expires_at",
        "origin",
        "incident_center",
        "patrol_radius_m",
        "detection_radius_m",
        "speed_mps",
        "trajectory_type",
        "trajectory_seed",
        "trajectory_phase_deg",
        "behavior_version",
        "visual_family",
        "warning_until",
        "tracking_tokens",
        "sniker_directions",
        "version",
        "status",
    }
    return {key: value for key, value in capsule.items() if key in allowed}


def position_at(capsule, world_time):
    capsule = capsule if isinstance(capsule, dict) else {}
    center = capsule.get("incident_center") if isinstance(capsule.get("incident_center"), dict) else {}
    origin = capsule.get("origin") if isinstance(capsule.get("origin"), dict) else center
    if center.get("lat") is None or center.get("lng") is None:
        return {
            "lat": None,
            "lng": None,
            "direction": "down",
            "animation_state": "idle",
        }

    now = _coerce_datetime(world_time)
    spawn_at = _coerce_datetime(capsule.get("spawn_at") or now)
    expires_at = _coerce_datetime(capsule.get("expires_at") or (spawn_at + timedelta(minutes=5)))
    if now < spawn_at:
        return {
            "lat": origin.get("lat"),
            "lng": origin.get("lng"),
            "direction": "down",
            "animation_state": "waiting",
        }
    if now >= expires_at:
        return {
            "lat": origin.get("lat"),
            "lng": origin.get("lng"),
            "direction": "down",
            "animation_state": "expired",
        }

    elapsed = (now - spawn_at).total_seconds()
    seed = capsule.get("trajectory_seed") or capsule.get("capsule_id") or capsule.get("incident_id")
    phase = capsule.get("trajectory_phase_deg")
    try:
        base_angle = float(phase)
    except (TypeError, ValueError):
        base_angle = _stable_float(f"{seed}:phase", 0.0, 360.0)
    speed = max(1.0, float(capsule.get("speed_mps") or 6.0))
    patrol_radius = max(25.0, float(capsule.get("patrol_radius_m") or 160.0))
    trajectory_type = _clean(capsule.get("trajectory_type"), "orbital_search")

    angular_speed = (speed / patrol_radius) * (180.0 / math.pi)
    angle = base_angle + (elapsed * angular_speed)
    radius = patrol_radius
    animation_state = "patrol"

    if trajectory_type == "spiral_sweep":
        pulse = (math.sin(elapsed / 18.0) + 1.0) / 2.0
        radius = max(35.0, patrol_radius * (0.45 + 0.55 * pulse))
        animation_state = "scan"
    elif trajectory_type == "intercept_loop":
        pulse = (math.sin(elapsed / 11.0) + 1.0) / 2.0
        radius = max(40.0, patrol_radius * (0.7 + 0.3 * pulse))
        angle = base_angle - (elapsed * angular_speed * 1.25)
        animation_state = "pursuit"

    position = _project_point(center, radius, angle)
    direction = _direction_from_angle(angle + 90.0)
    return {
        "lat": position["lat"],
        "lng": position["lng"],
        "direction": direction,
        "animation_state": animation_state,
    }


class NPCCapsuleFactory:
    def build_for_incident(self, incident, now=None):
        incident = incident if isinstance(incident, dict) else {}
        incident_id = _clean(incident.get("incident_id"))
        center = incident.get("center") if isinstance(incident.get("center"), dict) else {}
        if not incident_id or center.get("lat") is None or center.get("lng") is None:
            return []

        now_dt = _coerce_datetime(now)
        expires_at = _iso(incident.get("expires_at") or (now_dt + timedelta(minutes=12)))
        seed = _clean(incident.get("seed"), incident_id)
        radius = max(120, int(incident.get("search_radius_m") or 220))
        level = max(1, int(incident.get("level") or 1))
        capsules = []

        for index, (service_type, service_level) in enumerate(_service_plan(level)):
            capsule_seed = f"{seed}:{incident_id}:{index}:{BEHAVIOR_VERSION}"
            capsule_id = "capsule_" + hashlib.sha1(capsule_seed.encode("utf-8")).hexdigest()[:16]
            bearing = _stable_float(f"{capsule_seed}:bearing", 0.0, 360.0)
            origin_distance = radius + 120 + (index * 45)
            origin = _project_point(center, origin_distance, bearing)
            trajectory_type = _trajectory_for(service_type, index)
            patrol_radius = radius + (35 * index)
            detection_radius = max(55, min(180, 65 + (level * 18) + (service_level * 8)))
            speed = round(5.5 + service_level + (_stable_float(f"{capsule_seed}:speed", 0.0, 1.6)), 2)
            trajectory_phase = round(_stable_float(f"{capsule_seed}:phase", 0.0, 360.0), 4)
            tracking_token = hashlib.sha1(f"{capsule_id}:tracking".encode("utf-8")).hexdigest()[:24]
            capsules.append({
                "capsule_id": capsule_id,
                "incident_id": incident_id,
                "npc_id": "npc_" + capsule_id.removeprefix("capsule_"),
                "actor_type": "response_npc",
                "service_type": service_type,
                "service_level": service_level,
                "spawn_at": _iso(now_dt + timedelta(seconds=12 + (index * 8))),
                "expires_at": expires_at,
                "origin": origin,
                "incident_center": {
                    "lat": center.get("lat"),
                    "lng": center.get("lng"),
                },
                "patrol_radius_m": patrol_radius,
                "detection_radius_m": detection_radius,
                "speed_mps": speed,
                "trajectory_type": trajectory_type,
                "trajectory_seed": capsule_seed,
                "trajectory_phase_deg": trajectory_phase,
                "behavior_version": BEHAVIOR_VERSION,
                "visual_family": service_type if service_type in VISUAL_FAMILIES else "police",
                "warning_until": _iso(now_dt + timedelta(seconds=45)),
                "tracking_tokens": [tracking_token],
                "sniker_directions": list(SNIKER_DIRECTIONS_8),
                "status": "active",
            })
        return capsules


def capsule_signature(capsule):
    return _capsule_signature(capsule)
