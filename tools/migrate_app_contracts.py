import argparse
import copy
import json
import os
import shutil
import sqlite3
from datetime import datetime


DB_PATH = os.path.join("data", "game.sqlite3")
APP_CONFIG_PATH = os.path.join("static", "app_config.json")


ACTION_CONTRACTS = {
    "scan_ports": {
        "target_types": ["poi", "camera", "atm", "server", "router", "player", "pillar"],
        "operation_types": [],
        "resource_types": ["internal_recon_state"],
    },
    "exploit": {
        "target_types": ["poi", "camera", "atm", "server", "router", "player", "pillar"],
        "operation_types": [],
        "resource_types": [],
    },
    "sniff": {
        "target_types": ["poi", "server", "router", "player", "pillar"],
        "operation_types": [],
        "resource_types": [],
    },
    "trace": {
        "target_types": ["poi", "person", "phone", "player", "vehicle", "pillar"],
        "operation_types": ["generic_trace"],
        "resource_types": ["location_history"],
    },
    "trace_gps": {
        "target_types": ["vehicle"],
        "operation_types": ["vehicle_tracking"],
        "resource_types": ["gps_logs", "location_history"],
    },
    "trace_device": {
        "target_types": ["person", "phone", "player"],
        "operation_types": ["device_tracking"],
        "resource_types": ["device_logs", "location_history"],
    },
    "mic_sniff": {
        "target_types": ["person", "venue"],
        "operation_types": ["microphone_sniffer"],
        "resource_types": ["audio_transcript"],
    },
    "camera_stream": {
        "target_types": ["camera"],
        "operation_types": ["camera_stream"],
        "resource_types": ["camera_dump"],
    },
    "camera_shutdown": {
        "target_types": ["camera"],
        "operation_types": ["camera_shutdown"],
        "resource_types": [],
    },
    "atm_logs": {
        "target_types": ["atm"],
        "operation_types": ["atm_log_extraction"],
        "resource_types": ["atm_dump", "financial_records"],
    },
    "install_sniffer": {
        "target_types": ["atm", "router", "server"],
        "operation_types": ["persistent_sniffer"],
        "resource_types": [],
        "review": "persistent_sniffer has app-dependent resource output",
    },
    "scan_hotspots": {
        "target_types": ["venue", "shop", "restaurant", "bar", "cafe", "fast_food"],
        "operation_types": ["wifi_scanner"],
        "resource_types": ["wifi_networks"],
    },
    "audio_hack": {
        "target_types": ["venue", "shop", "restaurant", "bar", "cafe", "fast_food"],
        "operation_types": ["audio_interference"],
        "resource_types": [],
        "review": "audio_hack has app-dependent resource output",
    },
    "car_hack": {
        "target_types": ["vehicle"],
        "operation_types": ["vehicle_ecu"],
        "resource_types": ["vehicle_diagnostics"],
    },
}


NON_MAP_TYPES = {"creator", "pro-system-tool", "system_lab"}
NON_MAP_CATEGORIES = {"creators", "pro-system-tools", "pro-system-lab"}


def unique(values):
    result = []
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in result:
            result.append(text)
    return result


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def has_any(values, keywords):
    return bool({str(item).strip() for item in as_list(values)}.intersection(keywords))


def infer_map_actions(app):
    actions = set()
    app_type = str(app.get("type") or "").strip()
    detects = app.get("detects", [])
    interferes = app.get("interferes_with", [])
    effects = app.get("effects", [])

    if app_type == "scanner" and has_any(detects, {"open_ports"}):
        actions.add("scan_ports")
    if app_type in {"exploit", "exploit_suite"}:
        actions.add("exploit")
    if app_type == "exploit_suite" and has_any(detects, {"open_ports", "weak_configs"}):
        actions.add("scan_ports")
    if app_type in {"scanner", "os_component"} and has_any(detects, {"processes", "active_tasks", "security_logs"}):
        actions.add("sniff")
    if has_any(detects, {"user_location", "device_presence", "ip_leaks"}):
        actions.add("trace")
    if has_any(detects, {"camera_feed", "video_stream"}):
        actions.add("camera_stream")
    if has_any(interferes, {"camera", "video_stream"}):
        actions.add("camera_shutdown")
    if has_any(detects, {"microphone_activity", "audio_stream"}):
        actions.add("mic_sniff")
    if has_any(detects, {"bluetooth_device", "bluetooth_devices", "device_location", "device_presence"}):
        actions.add("trace_device")
    if has_any(interferes, {"vehicle_ecu", "car_system", "gps_tracker"}):
        actions.add("car_hack")
    if has_any(detects, {"gps_location", "car_signal", "movement_data"}):
        actions.add("trace_gps")
    if has_any(detects, {"atm_logs", "financial_data"}):
        actions.add("atm_logs")
    if app_type == "sniffer" or has_any(effects, {"network_capture"}):
        actions.add("install_sniffer")
    if has_any(detects, {"wifi", "ssid", "access_points"}):
        actions.add("scan_hotspots")
    if has_any(interferes, {"speaker", "audio_output"}):
        actions.add("audio_hack")

    return sorted(actions)


def derive_contract_from_actions(actions):
    target_types = []
    operation_types = []
    resource_types = []
    review_reasons = []
    for action in actions:
        contract = ACTION_CONTRACTS.get(action)
        if not contract:
            review_reasons.append(f"unknown map_action: {action}")
            continue
        target_types.extend(contract.get("target_types", []))
        operation_types.extend(contract.get("operation_types", []))
        resource_types.extend(contract.get("resource_types", []))
        if contract.get("review"):
            review_reasons.append(contract["review"])
    return unique(target_types), unique(operation_types), unique(resource_types), unique(review_reasons)


def should_skip_review_for_empty_app(app):
    app_type = str(app.get("type") or "").strip()
    category = str(app.get("category") or "").strip()
    return app_type in NON_MAP_TYPES or category in NON_MAP_CATEGORIES


def migrate_app(app):
    migrated = copy.deepcopy(app)
    changes = {}
    review_reasons = []

    current_actions = unique(migrated.get("map_actions"))
    inferred_actions = current_actions or infer_map_actions(migrated)
    if not current_actions:
        migrated["map_actions"] = inferred_actions
        changes["map_actions"] = inferred_actions
        if inferred_actions:
            migrated["map_actions_source"] = "migration_inferred"
            changes["map_actions_source"] = "migration_inferred"

    target_types, operation_types, resource_types, action_reviews = derive_contract_from_actions(migrated.get("map_actions", []))
    review_reasons.extend(action_reviews)

    for field, inferred in (
        ("target_types", target_types),
        ("operation_types", operation_types),
        ("resource_types", resource_types),
    ):
        current = unique(migrated.get(field))
        if current:
            migrated[field] = current
            continue
        migrated[field] = inferred
        changes[field] = inferred

    if not migrated.get("map_actions") and not should_skip_review_for_empty_app(migrated):
        review_reasons.append("no map_actions inferred")

    if review_reasons:
        migrated["contract_review"] = {
            "needs_review": True,
            "reasons": review_reasons,
        }
        changes["contract_review"] = migrated["contract_review"]

    changed = migrated != app
    return migrated, changed, bool(review_reasons), review_reasons, changes


def migrate_app_list(apps):
    migrated_apps = []
    report = {
        "found": 0,
        "changed": 0,
        "auto": 0,
        "review": 0,
        "examples": [],
    }
    for app in apps or []:
        if not isinstance(app, dict):
            migrated_apps.append(app)
            continue
        report["found"] += 1
        migrated, changed, needs_review, reasons, changes = migrate_app(app)
        migrated_apps.append(migrated)
        if changed:
            report["changed"] += 1
            if needs_review:
                report["review"] += 1
            else:
                report["auto"] += 1
            if len(report["examples"]) < 8:
                report["examples"].append({
                    "id": app.get("id"),
                    "name": app.get("name"),
                    "needs_review": needs_review,
                    "review_reasons": reasons,
                    "changes": changes,
                })
    return migrated_apps, report


def merge_reports(reports):
    summary = {"found": 0, "changed": 0, "auto": 0, "review": 0, "examples": []}
    for report in reports:
        for key in ("found", "changed", "auto", "review"):
            summary[key] += report.get(key, 0)
        for example in report.get("examples", []):
            if len(summary["examples"]) < 12:
                summary["examples"].append(example)
    return summary


def load_json_file(path, default):
    if not os.path.exists(path):
        return copy.deepcopy(default)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_file(path, value):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def db_connect(path):
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn


def backup_sources(db_path, app_config_path):
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join("data", "backups", f"app_contract_migration_{stamp}")
    os.makedirs(backup_dir, exist_ok=True)

    copied = []
    if os.path.exists(db_path):
        for suffix in ("", "-wal", "-shm"):
            source = db_path + suffix
            if os.path.exists(source):
                target = os.path.join(backup_dir, os.path.basename(source))
                shutil.copy2(source, target)
                copied.append(target)
    if os.path.exists(app_config_path):
        target = os.path.join(backup_dir, os.path.basename(app_config_path))
        shutil.copy2(app_config_path, target)
        copied.append(target)
    return backup_dir, copied


def migrate_static_app_config(apply_changes):
    apps = load_json_file(APP_CONFIG_PATH, [])
    migrated, report = migrate_app_list(apps)
    if apply_changes and migrated != apps:
        write_json_file(APP_CONFIG_PATH, migrated)
    report["source"] = "static/app_config.json"
    return report


def migrate_db_app_config(conn, apply_changes):
    row = conn.execute("SELECT value_json FROM json_resources WHERE key = ?", ("app_config",)).fetchone()
    if not row:
        return {"source": "json_resources.app_config", "found": 0, "changed": 0, "auto": 0, "review": 0, "examples": []}

    apps = json.loads(row["value_json"])
    migrated, report = migrate_app_list(apps)
    if apply_changes and migrated != apps:
        conn.execute(
            "UPDATE json_resources SET value_json = ?, updated_at = ? WHERE key = ?",
            (json.dumps(migrated, ensure_ascii=False, separators=(",", ":")), datetime.utcnow().isoformat(timespec="seconds"), "app_config"),
        )
    report["source"] = "json_resources.app_config"
    return report


def migrate_user_apps(conn, apply_changes):
    rows = conn.execute("SELECT username, profile_json FROM users ORDER BY username").fetchall()
    aggregate = {"source": "users.profile_json.apps", "found": 0, "changed": 0, "auto": 0, "review": 0, "examples": []}
    changed_profiles = []

    for row in rows:
        profile = json.loads(row["profile_json"])
        apps = profile.get("apps") or []
        migrated, report = migrate_app_list(apps)
        aggregate = merge_reports([aggregate, report])
        aggregate["source"] = "users.profile_json.apps"
        if migrated != apps:
            profile["apps"] = migrated
            changed_profiles.append((row["username"], profile))
            for example in report.get("examples", []):
                example["username"] = row["username"]

    if apply_changes:
        now = datetime.utcnow().isoformat(timespec="seconds")
        for username, profile in changed_profiles:
            conn.execute(
                "UPDATE users SET profile_json = ?, updated_at = ? WHERE username = ?",
                (json.dumps(profile, ensure_ascii=False, separators=(",", ":")), now, username),
            )

    return aggregate


def print_report(mode, backup_dir, backup_files, reports):
    summary = merge_reports(reports)
    print(f"Mode: {mode}")
    print(f"Applications found: {summary['found']}")
    print(f"Changed automatically: {summary['auto']}")
    print(f"Needs review: {summary['review']}")
    print(f"Total changed: {summary['changed']}")
    if backup_dir:
        print(f"Backup directory: {backup_dir}")
        for path in backup_files:
            print(f"  - {path}")
    else:
        print("Backup directory: not created in dry-run")

    print("\nSources:")
    for report in reports:
        print(
            f"  - {report.get('source')}: found={report.get('found', 0)}, "
            f"changed={report.get('changed', 0)}, auto={report.get('auto', 0)}, review={report.get('review', 0)}"
        )

    print("\nExamples:")
    for example in summary["examples"]:
        print(json.dumps(example, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Migrate CHAOS app records to app contract fields.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Show migration report without writing changes.")
    mode.add_argument("--apply", action="store_true", help="Backup and apply migration.")
    args = parser.parse_args()

    apply_changes = bool(args.apply)
    backup_dir = None
    backup_files = []
    if apply_changes:
        backup_dir, backup_files = backup_sources(DB_PATH, APP_CONFIG_PATH)

    reports = [migrate_static_app_config(apply_changes)]
    if os.path.exists(DB_PATH):
        conn = db_connect(DB_PATH)
        try:
            reports.append(migrate_db_app_config(conn, apply_changes))
            reports.append(migrate_user_apps(conn, apply_changes))
            if apply_changes:
                conn.commit()
        finally:
            conn.close()

    print_report("apply" if apply_changes else "dry-run", backup_dir, backup_files, reports)


if __name__ == "__main__":
    main()
