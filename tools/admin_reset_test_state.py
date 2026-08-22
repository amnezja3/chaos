import json
import os
import shutil
import sys
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from database import DB_PATH, JsonResourceStore, UserStore, db_connect


ADMIN_USERNAME = "admin"
TEST_APP_PREFIX = "admin_test_"


MAP_ACTIONS = {
    "scan_ports": {
        "label": "Scan Ports",
        "type": "scanner",
        "target_types": ["poi", "camera", "atm", "server", "router", "player", "pillar"],
        "operation_types": [],
        "resource_variants": [["internal_recon_state"], ["internal_recon_state"]],
    },
    "exploit": {
        "label": "Exploit",
        "type": "exploit",
        "target_types": ["poi", "camera", "atm", "server", "router", "player", "pillar"],
        "operation_types": [],
        "resource_variants": [[], []],
    },
    "sniff": {
        "label": "Sniff",
        "type": "sniffer",
        "target_types": ["poi", "server", "router", "player", "pillar"],
        "operation_types": [],
        "resource_variants": [["internal_recon_state"], ["credentials"]],
    },
    "trace": {
        "label": "Trace",
        "type": "tracker",
        "target_types": ["poi", "person", "phone", "player", "vehicle", "pillar"],
        "operation_types": ["generic_trace"],
        "resource_variants": [["location_history"], ["location_history", "device_logs"]],
    },
    "trace_gps": {
        "label": "Trace GPS",
        "type": "tracker",
        "target_types": ["vehicle"],
        "operation_types": ["vehicle_tracking"],
        "resource_variants": [["gps_logs"], ["gps_logs", "location_history"]],
    },
    "trace_device": {
        "label": "Trace Device",
        "type": "tracker",
        "target_types": ["person", "phone", "player"],
        "operation_types": ["device_tracking"],
        "resource_variants": [["location_history", "device_logs"], ["location_history", "device_logs", "personal_records", "call_history"]],
    },
    "mic_sniff": {
        "label": "Mic Sniff",
        "type": "sniffer",
        "target_types": ["person", "venue"],
        "operation_types": ["microphone_sniffer"],
        "resource_variants": [["audio_transcript"], ["audio_transcript"]],
    },
    "camera_stream": {
        "label": "Camera Stream",
        "type": "camera_tool",
        "target_types": ["camera"],
        "operation_types": ["camera_stream"],
        "resource_variants": [["camera_dump"], ["camera_dump", "video_material"]],
    },
    "camera_shutdown": {
        "label": "Camera Shutdown",
        "type": "camera_tool",
        "target_types": ["camera"],
        "operation_types": ["camera_shutdown"],
        "resource_variants": [[], []],
    },
    "atm_logs": {
        "label": "ATM Logs",
        "type": "financial_tool",
        "target_types": ["atm"],
        "operation_types": ["atm_log_extraction"],
        "resource_variants": [["atm_dump"], ["atm_dump", "financial_records"]],
    },
    "install_sniffer": {
        "label": "Install Sniffer",
        "type": "sniffer",
        "target_types": ["atm", "router", "server"],
        "operation_types": ["persistent_sniffer"],
        "resource_variants": [["credentials"], ["financial_records", "credentials", "device_logs", "internal_recon_state"]],
    },
    "scan_hotspots": {
        "label": "Scan Hotspots",
        "type": "scanner",
        "target_types": ["venue"],
        "operation_types": ["wifi_scanner"],
        "resource_variants": [["wifi_networks"], ["wifi_networks", "hotspot_database"]],
    },
    "audio_hack": {
        "label": "Audio Hack",
        "type": "audio_tool",
        "target_types": ["venue"],
        "operation_types": ["audio_interference"],
        "resource_variants": [["audio_transcript"], ["audio_transcript"]],
    },
    "car_hack": {
        "label": "Car Hack",
        "type": "vehicle_tool",
        "target_types": ["vehicle"],
        "operation_types": ["vehicle_ecu"],
        "resource_variants": [["vehicle_diagnostics"], ["vehicle_diagnostics"]],
    },
}


def backup_database():
    os.makedirs("data/backups", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join("data", "backups", f"game_before_admin_reset_{timestamp}.sqlite3")
    with db_connect(DB_PATH) as conn:
        conn.execute("PRAGMA wal_checkpoint(FULL)")
    shutil.copy2(DB_PATH, backup_path)
    for suffix in ["-wal", "-shm"]:
        sidecar = DB_PATH + suffix
        if os.path.exists(sidecar):
            shutil.copy2(sidecar, backup_path + suffix)
    return backup_path


def table_columns(conn, table_name):
    try:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
    except Exception:
        return set()


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def delete_by_columns(conn, table_name, username, columns):
    if not table_exists(conn, table_name):
        return
    available = table_columns(conn, table_name)
    usable = [column for column in columns if column in available]
    if not usable:
        return
    where = " OR ".join(f"{column} = ?" for column in usable)
    conn.execute(f"DELETE FROM {table_name} WHERE {where}", tuple(username for _ in usable))


def delete_conflicts_for_user(conn, username):
    if not table_exists(conn, "territory_conflicts"):
        return
    columns = table_columns(conn, "territory_conflicts")
    clauses = []
    params = []
    for column in ["player_a_username", "player_b_username"]:
        if column in columns:
            clauses.append(f"{column} = ?")
            params.append(username)
    if "participants_json" in columns:
        clauses.append("participants_json LIKE ?")
        params.append(f'%"{username}"%')
    if clauses:
        conn.execute(f"DELETE FROM territory_conflicts WHERE {' OR '.join(clauses)}", tuple(params))


def clear_user_relations(conn, username, delete_account=False):
    delete_by_columns(conn, "chat_messages", username, ["owner_username", "peer_name", "sender_username", "recipient_username"])
    delete_by_columns(conn, "contacts", username, ["owner_username", "contact_name"])
    delete_by_columns(conn, "mail_presence", username, ["username"])
    delete_by_columns(conn, "area_events", username, ["owner_username", "actor_username"])
    delete_by_columns(conn, "player_areas", username, ["owner_username"])
    delete_by_columns(conn, "captured_targets", username, ["owner_username"])
    delete_by_columns(conn, "reported_vulnerabilities", username, ["reported_by_username", "territory_owner_username"])
    delete_by_columns(conn, "wallet_transactions", username, ["from_username", "to_username"])
    delete_by_columns(conn, "player_hack_access", username, ["attacker_username", "victim_username"])
    delete_by_columns(conn, "player_hack_tool_usage", username, ["attacker_username", "victim_username"])
    delete_conflicts_for_user(conn, username)
    if table_exists(conn, "kv_store"):
        conn.execute("DELETE FROM kv_store WHERE key = ?", (f"mail_seed:{username}",))
    if delete_account:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))


def clear_admin_territory(conn, username):
    delete_by_columns(conn, "area_events", username, ["owner_username", "actor_username"])
    delete_by_columns(conn, "player_areas", username, ["owner_username"])
    delete_by_columns(conn, "captured_targets", username, ["owner_username"])
    delete_by_columns(conn, "reported_vulnerabilities", username, ["reported_by_username", "territory_owner_username"])
    delete_conflicts_for_user(conn, username)


def reset_admin_profile():
    store = UserStore()
    record = store.get_profile_with_revision(ADMIN_USERNAME)
    if not record:
        return False
    if record.get("state") != "valid":
        raise RuntimeError("Admin profile requires recovery before reset.")
    profile = record["profile"]

    profile["hacked"] = []
    profile["targets"] = []
    profile["own_places"] = []
    profile["operations"] = []
    profile["captured_targets_source"] = "sqlite"
    profile["territory_stats"] = {
        "total_area": 0,
        "effective_area": 0,
        "area_baseline": 0,
        "next_level_area": 0,
        "area_to_next_level": 0,
        "clusters_count": 0,
        "captured_targets_count": 0,
        "last_area_gain": 0,
        "last_effective_gain": 0,
        "total_perimeter": 0,
        "edges_count": 0,
        "span_density": 0,
        "density_multiplier": 0,
    }
    aimed = profile.get("aimed_target")
    if isinstance(aimed, dict):
        aimed.update({
            "lat": 0.0,
            "lng": 0.0,
            "label": "",
            "name": "",
            "source_type": "",
            "target_mode": "",
        })
        if isinstance(aimed.get("actions_allowed"), dict):
            for key in list(aimed["actions_allowed"].keys()):
                aimed["actions_allowed"][key] = False
    reset_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    store.save_profile_guarded(
        profile,
        expected_revision=int(record["profile_revision"]),
        source="admin.reset_test_state",
        reset_receipt={
            "receipt_id": f"admin-reset-test-state:{reset_at}",
            "reason": "explicit_admin_test_state_reset",
            "authorized_by": ADMIN_USERNAME,
            "created_at": reset_at,
        },
    )
    return True


def make_level(app_name, action_label):
    return [{
        "title": f"{app_name} - {action_label}",
        "steps": [
            "Init test module...",
            "Binding map action...",
            "Running simulated payload...",
            "Writing operation state...",
        ],
        "result_success": f"{app_name}: akcja {action_label} zakonczona powodzeniem.",
        "result_failure": f"{app_name}: akcja {action_label} zablokowana.",
    }]


def build_test_apps():
    apps = []
    for action_id, spec in MAP_ACTIONS.items():
        for variant in [1, 2]:
            resources = spec["resource_variants"][variant - 1]
            suffix = "Lite" if variant == 1 else "Plus"
            app_name = f"Admin {spec['label']} {suffix}"
            apps.append({
                "id": f"{TEST_APP_PREFIX}{action_id}_{variant}",
                "name": app_name,
                "icon": "TST",
                "type": spec["type"],
                "category": "admin-test-map-tools",
                "price": 5 + variant * 5,
                "required_level": 1,
                "required_respect": 0,
                "allowed_fractions": [],
                "purchase_account": ADMIN_USERNAME,
                "creator_username": ADMIN_USERNAME,
                "risk_level": variant,
                "published": True,
                "downloads": 0,
                "interface": "progressbar_random",
                "map_actions": [action_id],
                "map_actions_source": "admin_test_seed",
                "target_types": spec["target_types"],
                "operation_types": spec["operation_types"],
                "resource_types": resources,
                "detects": [],
                "affects": [],
                "interferes_with": [],
                "requires_off": [],
                "disables": [],
                "description": f"Tanie narzedzie testowe admina dla map action: {action_id}. Wariant {suffix}.",
                "levels": make_level(app_name, spec["label"]),
            })
    return apps


def update_app_config_catalog():
    resource_store = JsonResourceStore()
    catalog = resource_store.get("app_config", seed_path="static/app_config.json", default=[]) or []
    kept = [app for app in catalog if not str(app.get("id", "")).startswith(TEST_APP_PREFIX)]
    test_apps = build_test_apps()
    updated = kept + test_apps
    resource_store.set("app_config", updated)

    with open("static/app_config.json", "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return len(catalog), len(test_apps), len(updated)


def main():
    backup_path = backup_database()

    with db_connect(DB_PATH) as conn:
        users = [
            row["username"]
            for row in conn.execute("SELECT username FROM users ORDER BY username").fetchall()
        ]
        removed_users = [username for username in users if username != ADMIN_USERNAME]
        for username in removed_users:
            clear_user_relations(conn, username, delete_account=True)
        clear_admin_territory(conn, ADMIN_USERNAME)

    admin_reset = reset_admin_profile()
    old_count, added_count, new_count = update_app_config_catalog()

    print("Backup:", backup_path)
    print("Removed users:", ", ".join(removed_users) if removed_users else "(none)")
    print("Admin territory reset:", admin_reset)
    print("Googleplex catalog before:", old_count)
    print("Admin test apps added:", added_count)
    print("Googleplex catalog after:", new_count)


if __name__ == "__main__":
    main()
