import copy
import json
from datetime import datetime, timezone


DEFAULT_STORAGE_CAPACITY = 512
DEFAULT_STORAGE_UNIT = "MB"


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def dumps_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads_json(value, default=None):
    if value is None:
        return copy.deepcopy(default)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return copy.deepcopy(default)


def clamp_int(value, default=0, minimum=0, maximum=None):
    try:
        number = int(round(float(value)))
    except (TypeError, ValueError):
        number = default
    number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def read_profiles(conn):
    return [
        {
            "username": row[0],
            "profile": loads_json(row[1], {}),
        }
        for row in conn.execute(
            "SELECT username, profile_json FROM users ORDER BY username"
        ).fetchall()
    ]


def write_profile(conn, username, profile):
    conn.execute(
        "UPDATE users SET profile_json = ?, updated_at = ? WHERE username = ?",
        (dumps_json(profile), utc_now(), username),
    )


def app_name(app):
    if not isinstance(app, dict):
        return ""
    return str(app.get("name") or app.get("label") or app.get("id") or "").strip()


def app_disk_usage(app):
    if not isinstance(app, dict):
        return 0
    for key in ("disk_usage", "install_size", "file_size"):
        if key in app:
            return clamp_int(app.get(key), default=8, minimum=1)
    return max(8, len(app.get("map_actions") or []) * 3 + len(app.get("operation_types") or []) * 5)


def file_size(item):
    if isinstance(item, dict):
        if "file_size" in item:
            return clamp_int(item.get("file_size"), default=1, minimum=0)
        return max(1, len(item.get("resource_types") or []) * 4)
    if item:
        return 1
    return 0


def calculate_storage_used(profile):
    used = 0
    for app in profile.get("apps") or []:
        used += app_disk_usage(app)
    files = profile.get("files") or {}
    if isinstance(files, dict):
        for entries in files.values():
            if isinstance(entries, dict):
                entries = list(entries.values())
            for item in entries or []:
                used += file_size(item)
    return used


def normalize_storage(profile):
    profile["storage_capacity"] = clamp_int(
        profile.get("storage_capacity"),
        default=DEFAULT_STORAGE_CAPACITY,
        minimum=1,
    )
    profile["storage_unit"] = profile.get("storage_unit") or DEFAULT_STORAGE_UNIT
    profile["storage_soft_limit"] = profile.get("storage_soft_limit", True) is not False
    profile["storage_used"] = calculate_storage_used(profile)
    profile["storage_over_limit"] = profile["storage_used"] > profile["storage_capacity"]
    return profile


def normalize_app_contract_fields(app):
    app = dict(app or {})
    map_actions = app.get("map_actions") or []
    operation_types = app.get("operation_types") or []
    resource_types = app.get("resource_types") or []
    app["map_actions"] = list(map_actions) if isinstance(map_actions, list) else [map_actions]
    app["operation_types"] = list(operation_types) if isinstance(operation_types, list) else [operation_types]
    app["resource_types"] = list(resource_types) if isinstance(resource_types, list) else [resource_types]
    app.setdefault("target_types", [])
    base_size = max(8, len(app["map_actions"]) * 3 + len(app["operation_types"]) * 5 + len(app["resource_types"]) * 2)
    app["file_size"] = clamp_int(app.get("file_size"), default=base_size, minimum=1)
    app["disk_usage"] = clamp_int(app.get("disk_usage"), default=app["file_size"] + 4, minimum=app["file_size"])
    app["install_size"] = clamp_int(app.get("install_size"), default=app["disk_usage"], minimum=app["disk_usage"])
    app["creator_power"] = clamp_int(app.get("creator_power"), default=50, minimum=0, maximum=100)
    app["quality_score"] = clamp_int(app.get("quality_score"), default=55, minimum=0, maximum=100)
    app["reliability"] = clamp_int(app.get("reliability"), default=65, minimum=0, maximum=100)
    power = clamp_int(
        app.get("power_score"),
        default=round(app["quality_score"] * 0.45 + app["reliability"] * 0.35 + len(app["operation_types"]) * 5),
        minimum=1,
        maximum=100,
    )
    app["power_score"] = power
    app.setdefault("price_hint", max(50, power * 10 + app["disk_usage"] * 3))
    app.setdefault("balance_tier", "Pro" if power >= 76 else "Advanced" if power >= 46 else "Basic")
    if "tool_family" in app:
        app.setdefault("map_actions_source", "creator_explicit")
    return app


def tool_file_entry_name(item):
    if isinstance(item, dict):
        return str(
            item.get("name")
            or item.get("filename")
            or item.get("file_name")
            or item.get("project_file")
            or ""
        ).strip()
    return str(item or "").strip()


def app_tool_candidates(app):
    candidates = set()
    name = app_name(app)
    if name:
        candidates.add(f"{name}.sh")
    for key in ("project_file", "file_name"):
        value = str(app.get(key) or "").strip() if isinstance(app, dict) else ""
        if value:
            candidates.add(value)
    return candidates
