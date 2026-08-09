import os


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    value = os.environ.get(name)
    if value is None:
        return int(default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def env_float(name, default):
    value = os.environ.get(name)
    if value is None:
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def env_csv(name, default=""):
    value = os.environ.get(name, default)
    return sorted({
        item.strip()
        for item in str(value or "").split(",")
        if item.strip()
    })


APP_VERSION = os.environ.get("APP_VERSION") or os.environ.get("BUILD_TAG") or "v0.3.4-dev"


OPERATION_FEEDBACK_FLAGS = {
    "enabled": env_bool("CHAOS_OPERATION_FEEDBACK_ENABLED", False),
    "scan_ports": env_bool("CHAOS_OPERATION_FEEDBACK_SCAN_PORTS", False),
    "enabled_actions": env_csv("CHAOS_OPERATION_FEEDBACK_ACTIONS"),
}

PROVISIONAL_APP_LAUNCH_ENABLED = env_bool(
    "CHAOS_PROVISIONAL_APP_LAUNCH_ENABLED",
    False,
)


FLASK_SESSION_CONFIG = {
    "SESSION_TYPE": os.environ.get("CHAOS_SESSION_TYPE", "filesystem"),
    "SESSION_FILE_DIR": os.environ.get(
        "CHAOS_SESSION_FILE_DIR",
        os.path.join(os.path.dirname(__file__), "data", "flask_session"),
    ),
    "SESSION_PERMANENT": env_bool("CHAOS_SESSION_PERMANENT", False),
    "SESSION_USE_SIGNER": env_bool("CHAOS_SESSION_USE_SIGNER", True),
    "SESSION_KEY_PREFIX": os.environ.get("CHAOS_SESSION_KEY_PREFIX", "haos_"),
    "SECRET_KEY": os.environ.get("CHAOS_SECRET_KEY", "bardzo-tajny-klucz-123"),
}


PERF_LOG_ENDPOINTS = {
    "/api/operations",
    "/api/map/player-areas",
    "/api/map/player-actors",
    "/api/map/clan-vulnerabilities",
    "/launch-queue",
    "/system-messages",
    "/command",
    "/gonna-win",
}
PERF_LOG_MIN_MS = env_int("CHAOS_PERF_LOG_MIN_MS", 100)
PERF_LOG_MIN_SIZE = env_int("CHAOS_PERF_LOG_MIN_SIZE", 20 * 1024)


RESPONSE_NETWORK_DEPLOYMENT_MODE = os.environ.get("CHAOS_RESPONSE_NETWORK_MODE", "disabled").strip().lower()
RESPONSE_NETWORK_FLAGS = {
    "response_network_enabled": env_bool("CHAOS_RESPONSE_NETWORK_ENABLED", False),
    "response_risk_meter_enabled": env_bool("CHAOS_RESPONSE_RISK_METER_ENABLED", False),
    "response_incidents_enabled": env_bool("CHAOS_RESPONSE_INCIDENTS_ENABLED", False),
    "response_npc_capsules_enabled": env_bool("CHAOS_RESPONSE_NPC_CAPSULES_ENABLED", False),
    "response_detection_enabled": env_bool("CHAOS_RESPONSE_DETECTION_ENABLED", False),
    "response_consequences_enabled": env_bool("CHAOS_RESPONSE_CONSEQUENCES_ENABLED", False),
    "response_tool_confiscation_enabled": env_bool("CHAOS_RESPONSE_TOOL_CONFISCATION_ENABLED", False),
    "response_hc_confiscation_enabled": env_bool("CHAOS_RESPONSE_HC_CONFISCATION_ENABLED", False),
    "response_judgment_enabled": env_bool("CHAOS_RESPONSE_JUDGMENT_ENABLED", False),
    "response_radio_hooks_enabled": env_bool("CHAOS_RESPONSE_RADIO_HOOKS_ENABLED", False),
    "response_cyberner_hooks_enabled": env_bool("CHAOS_RESPONSE_CYBERNER_HOOKS_ENABLED", False),
    "response_incident_history_enabled": env_bool("CHAOS_RESPONSE_INCIDENT_HISTORY_ENABLED", False),
    "response_map_publication_enabled": env_bool("CHAOS_RESPONSE_MAP_PUBLICATION_ENABLED", False),
}
RESPONSE_NETWORK_KILL_SWITCHES = {
    "new_incidents": env_bool("CHAOS_RESPONSE_KILL_NEW_INCIDENTS", True),
    "npc_capsules": env_bool("CHAOS_RESPONSE_KILL_NPC_CAPSULES", True),
    "detection": env_bool("CHAOS_RESPONSE_KILL_DETECTION", True),
    "consequences": env_bool("CHAOS_RESPONSE_KILL_CONSEQUENCES", True),
    "tool_confiscation": env_bool("CHAOS_RESPONSE_KILL_TOOL_CONFISCATION", True),
    "hc_confiscation": env_bool("CHAOS_RESPONSE_KILL_HC_CONFISCATION", True),
    "judgment": env_bool("CHAOS_RESPONSE_KILL_JUDGMENT", True),
    "radio_hooks": env_bool("CHAOS_RESPONSE_KILL_RADIO_HOOKS", True),
    "cyberner_hooks": env_bool("CHAOS_RESPONSE_KILL_CYBERNER_HOOKS", True),
    "incident_history": env_bool("CHAOS_RESPONSE_KILL_INCIDENT_HISTORY", True),
    "map_publication": env_bool("CHAOS_RESPONSE_KILL_MAP_PUBLICATION", True),
}
RESPONSE_NETWORK_AUDIT_LIMIT = env_int("CHAOS_RESPONSE_AUDIT_LIMIT", 250)


VULNERABILITY_MAX_ENABLED_SECURITY = env_int("CHAOS_VULNERABILITY_MAX_ENABLED_SECURITY", 5)
VULNERABILITY_REPORT_THRESHOLD = float(os.environ.get("CHAOS_VULNERABILITY_REPORT_THRESHOLD", "0.30") or 0.30)

PLAYER_HACK_ACCESS_MINUTES = env_int("CHAOS_PLAYER_HACK_ACCESS_MINUTES", 5)
PLAYER_HACK_COOLDOWN_HOURS = env_int("CHAOS_PLAYER_HACK_COOLDOWN_HOURS", 3)


GHOSTNETWORK_DROPS_ENABLED = env_bool("CHAOS_GHOSTNETWORK_DROPS_ENABLED", False)
GHOSTNETWORK_DROP_CHANCE = max(0.0, min(1.0, env_float("CHAOS_GHOSTNETWORK_DROP_CHANCE", 0.0)))
GHOSTNETWORK_RESERVATION_TTL_SECONDS = env_int("CHAOS_GHOSTNETWORK_RESERVATION_TTL_SECONDS", 15 * 60)
GHOSTNETWORK_REWARD_BASE_RSP = env_int("CHAOS_GHOSTNETWORK_REWARD_BASE_RSP", 12)
GHOSTNETWORK_HOLD_REWARD_PERIOD_SECONDS = env_int("CHAOS_GHOSTNETWORK_HOLD_REWARD_PERIOD_SECONDS", 60 * 60)
GHOSTNETWORK_PAUSE_HOLD_REWARDS_DURING_CONFLICT = env_bool(
    "CHAOS_GHOSTNETWORK_PAUSE_HOLD_REWARDS_DURING_CONFLICT",
    True,
)
GHOSTNETWORK_REWARD_MULTIPLIERS = {
    "part_discovered": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_DISCOVERED", 1.0),
    "part_first_contained": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_FIRST_CONTAINED", 1.6),
    "part_first_activated": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_FIRST_ACTIVATED", 2.0),
    "part_recovered": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_RECOVERED", 1.4),
    "part_stable_held": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_STABLE_HELD", 0.5),
    "part_defended": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_DEFENDED", 1.2),
    "defense_support": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_DEFENSE_SUPPORT", 0.8),
    "attack_support": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_ATTACK_SUPPORT", 0.8),
    "territory_repaired": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_TERRITORY_REPAIRED", 0.7),
    "ability_support": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_ABILITY_SUPPORT", 0.6),
    "transmission_node_held": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_TRANSMISSION_NODE_HELD", 1.5),
    "network_closer": env_float("CHAOS_GHOSTNETWORK_REWARD_MULTIPLIER_NETWORK_CLOSER", 3.0),
}
GHOSTNETWORK_CLAN_REPUTATION_WEIGHTS = {
    "part_discovered": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_DISCOVERED", 1),
    "part_first_contained": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_FIRST_CONTAINED", 2),
    "part_first_activated": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_FIRST_ACTIVATED", 3),
    "part_recovered": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_RECOVERED", 2),
    "part_stable_held": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_STABLE_HELD", 1),
    "part_defended": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_DEFENDED", 2),
    "defense_support": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_DEFENSE_SUPPORT", 1),
    "attack_support": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_ATTACK_SUPPORT", 1),
    "territory_repaired": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_TERRITORY_REPAIRED", 1),
    "ability_support": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_ABILITY_SUPPORT", 1),
    "transmission_node_held": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_TRANSMISSION_NODE_HELD", 2),
    "network_closer": env_int("CHAOS_GHOSTNETWORK_CLAN_REP_NETWORK_CLOSER", 5),
}
GHOSTNETWORK_DEFENSE_POLICY = {
    "min_attack_progress": env_int("CHAOS_GHOSTNETWORK_DEFENSE_MIN_ATTACK_PROGRESS", 25),
    "min_integrity_loss": env_int("CHAOS_GHOSTNETWORK_DEFENSE_MIN_INTEGRITY_LOSS", 10),
    "min_offensive_actions": env_int("CHAOS_GHOSTNETWORK_DEFENSE_MIN_OFFENSIVE_ACTIONS", 1),
    "min_defensive_score": env_int("CHAOS_GHOSTNETWORK_DEFENSE_MIN_DEFENSIVE_SCORE", 1),
    "min_conflict_seconds": env_int("CHAOS_GHOSTNETWORK_DEFENSE_MIN_CONFLICT_SECONDS", 60),
    "support_min_score": env_int("CHAOS_GHOSTNETWORK_DEFENSE_SUPPORT_MIN_SCORE", 2),
    "owner_reward_score": env_int("CHAOS_GHOSTNETWORK_DEFENSE_OWNER_SCORE", 14),
    "support_reward_score": env_int("CHAOS_GHOSTNETWORK_DEFENSE_SUPPORT_SCORE", 5),
    "total_rsp_cap": env_int("CHAOS_GHOSTNETWORK_DEFENSE_TOTAL_RSP_CAP", 60),
}
GHOSTNETWORK_RECOVERY_POLICY = {
    "min_previous_control_seconds": env_int("CHAOS_GHOSTNETWORK_RECOVERY_MIN_PREVIOUS_CONTROL_SECONDS", 60 * 60),
    "min_offensive_actions": env_int("CHAOS_GHOSTNETWORK_RECOVERY_MIN_OFFENSIVE_ACTIONS", 1),
    "min_disarm_score": env_int("CHAOS_GHOSTNETWORK_RECOVERY_MIN_DISARM_SCORE", 1),
    "owner_reward_score": env_int("CHAOS_GHOSTNETWORK_RECOVERY_OWNER_SCORE", 18),
    "support_reward_score": env_int("CHAOS_GHOSTNETWORK_RECOVERY_SUPPORT_SCORE", 5),
    "total_rsp_cap": env_int("CHAOS_GHOSTNETWORK_RECOVERY_TOTAL_RSP_CAP", 80),
}
GHOSTNETWORK_REWARD_COOLDOWNS = {
    "same_part_seconds": env_int("CHAOS_GHOSTNETWORK_REWARD_SAME_PART_COOLDOWN_SECONDS", 60 * 60),
    "same_pair_seconds": env_int("CHAOS_GHOSTNETWORK_REWARD_SAME_PAIR_COOLDOWN_SECONDS", 6 * 60 * 60),
    "rapid_transfer_review_seconds": env_int("CHAOS_GHOSTNETWORK_REWARD_RAPID_TRANSFER_REVIEW_SECONDS", 15 * 60),
}


DEFAULT_STORAGE_CAPACITY_MB = env_int("CHAOS_DEFAULT_STORAGE_CAPACITY_MB", 512)
DEFAULT_APP_FILE_SIZE_MB = env_int("CHAOS_DEFAULT_APP_FILE_SIZE_MB", 8)
DEFAULT_APP_DISK_USAGE_MB = env_int("CHAOS_DEFAULT_APP_DISK_USAGE_MB", 12)
DEFAULT_APP_QUALITY_SCORE = env_int("CHAOS_DEFAULT_APP_QUALITY_SCORE", 55)
DEFAULT_APP_RELIABILITY = env_int("CHAOS_DEFAULT_APP_RELIABILITY", 65)
DEFAULT_CREATOR_POWER = env_int("CHAOS_DEFAULT_CREATOR_POWER", 35)
DEFAULT_APP_PRICE_HINT_HC = env_int("CHAOS_DEFAULT_APP_PRICE_HINT_HC", 120)


"""
Kandydaci:

1. Runtime / wydajność
TERRITORY_REBUILD_CACHE_SECONDS
map snapshot interwały z map_template.html:MAP_PLAYER_ACTORS_SNAPSHOT_INTERVAL_MS
MAP_PLAYER_AREAS_SNAPSHOT_INTERVAL_MS
MAP_CLAN_VULNERABILITIES_SNAPSHOT_INTERVAL_MS
MAP_ACTIVE_OPERATIONS_SNAPSHOT_INTERVAL_MS

frontend delta:STATE_DELTA_POLL_INTERVAL_MS
STATE_DELTA_LIMIT
CYBERNER_THREAD_REFRESH_INTERVAL_MS

2. Operacje
DEFAULT_OPERATION_DURATIONS_SECONDS
VEHICLE_TRACKING_CHECKPOINT_INTERVAL_SECONDS
CAMERA_STREAM_FRAGMENT_INTERVAL_SECONDS
OPERATION_ACTIVE_STATUSES
OPERATION_TERMINAL_STATUSES
OPERATION_FINALIZABLE_STATUSES

3. Ghost Exchange balance
MARKET_SECTOR_THRESHOLDS
MARKET_SECTOR_DWELL_SECONDS
MARKET_CATEGORY_BASE_VALUE
QUALITY_SCORE_BY_LABEL
GHOST_EXCHANGE_BLOCKED_RESOURCES

4. Storage / file model
FILE_CATEGORY_SIZE_HINTS_MB
FILE_CATEGORY_DEFAULTS
GAMEPLAY_FILE_FOLDERS
DATA_FILE_FOLDERS
LEGACY_FILE_FOLDERS

5. Map/action mapping
HACK_ACTION_STEP_ALIASES
MAP_ACTION_OPERATION_TYPES
SOURCE_TYPE_TARGET_TYPES
SECURITY_CONFLICTS
LEGACY_MAP_ACTION_SOURCES

6. Product/runtime catalogs
TRAVEL_CITIES
STORAGE_UPGRADE_PRODUCTS
GOOGLEPLEX_EFFECT_PRODUCTS
LEGACY_STORAGE_UPGRADE_PRODUCTS
Tu bym się zastanowił, czy nie lepiej później przenieść je do JSON/resources zamiast config.py, bo to bardziej katalog gry niż konfiguracja runtime.

7. Tools / system apps
PRO_SYSTEM_TOOLS
CREATOR_SYSTEM_APPS
PROTECTED_APP_NAMES
CREATOR_EXPLICIT_TOOL_FAMILIES

8. Risk / gameplay tuning
RISK_EVENT_BASE_SCORES
RISK_EVENT_MESSAGES
UNNAMED_TARGET_VALUES
VULNERABILITY_REPORT_THRESHOLD już przeniesione, ale wokół tego są kolejne parametry balansu.
"""
