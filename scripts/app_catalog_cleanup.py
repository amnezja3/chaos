#!/usr/bin/env python3
"""Clean the CHAOS app catalog before server migrations.

Default mode is dry-run. Use --apply to write changes. The script edits only:

* SQLite json_resources.app_config
* users.profile_json apps/files.tools/storage fields

It does not delete projects, operations, files outside tools or market data.
"""

import argparse
import copy
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


APP_CONFIG_KEY = "app_config"
ADMIN_SEED_SOURCE = "admin_seed_v1"
PRICE_ADJUSTMENT_MARK = "sprint31_x2"
DEFAULT_STORAGE_CAPACITY = 512
DEFAULT_STORAGE_UNIT = "MB"

IMPORTANT_MAP_ACTIONS = [
    "scan_ports",
    "exploit",
    "sniff",
    "trace",
    "camera_stream",
    "camera_shutdown",
    "trace_device",
    "mic_sniff",
    "car_hack",
    "trace_gps",
    "atm_logs",
    "install_sniffer",
    "scan_hotspots",
    "audio_hack",
]


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


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def ensure_core_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS json_resources (
            key TEXT PRIMARY KEY,
            source_path TEXT NOT NULL DEFAULT '',
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL DEFAULT '',
            salt TEXT NOT NULL DEFAULT '',
            profile_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )


def backup_database(db_path, backup_dir, label="app_catalog_cleanup"):
    db_path = Path(db_path)
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"{db_path.stem}_{timestamp}_{label}{db_path.suffix}"
    shutil.copy2(db_path, target)
    return str(target)


def read_app_config(conn):
    row = conn.execute(
        "SELECT value_json FROM json_resources WHERE key = ?",
        (APP_CONFIG_KEY,),
    ).fetchone()
    return loads_json(row[0], []) if row else []


def write_app_config(conn, apps):
    conn.execute(
        """
        INSERT INTO json_resources (key, source_path, value_json, updated_at)
        VALUES (?, '', ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at = excluded.updated_at
        """,
        (APP_CONFIG_KEY, dumps_json(apps), utc_now()),
    )


def read_user_profiles(conn):
    return [
        {
            "username": row[0],
            "profile": loads_json(row[1], {}),
            "raw": row[1],
        }
        for row in conn.execute(
            "SELECT username, profile_json FROM users ORDER BY username"
        ).fetchall()
    ]


def write_user_profile(conn, username, profile):
    conn.execute(
        "UPDATE users SET profile_json = ?, updated_at = ? WHERE username = ?",
        (dumps_json(profile), utc_now(), username),
    )


def app_id(app):
    if not isinstance(app, dict):
        return ""
    return str(app.get("id") or app.get("app_id") or "").strip()


def app_name(app):
    if not isinstance(app, dict):
        return ""
    return str(app.get("name") or app.get("label") or app_id(app)).strip()


def is_generated_app(app):
    aid = app_id(app)
    return (
        bool(app.get("generated"))
        or str(app.get("source") or "") == "creator"
        or aid.startswith("user_")
    )


def is_ghostlab_app(app):
    return (
        bool(app.get("ghostlab_generated"))
        or str(app.get("source") or "") == "ghostlab"
        or str(app.get("type") or "") == "pro-system-tool"
        or str(app.get("category") or "") == "pro-system-tools"
    )


def is_system_creator_or_lab(app):
    return str(app.get("type") or "") in {"creator", "system_lab"} or str(app.get("category") or "") in {
        "creators",
        "pro-system-lab",
    }


def has_meaningful_contract(app):
    return bool(app.get("target_types") or app.get("operation_types") or app.get("resource_types"))


def is_test_or_dev_app(app):
    aid = app_id(app).lower()
    name = app_name(app).lower()
    source = str(app.get("map_actions_source") or "").strip()
    if source == "admin_test_seed":
        return True
    if aid.startswith("admin_test_"):
        return True
    if "admin test" in name or "test seed" in name:
        return True
    if str(app.get("source") or "") in {"smoke", "dev_seed", "test_seed"}:
        return True
    return False


def should_remove_catalog_app(app):
    if not isinstance(app, dict):
        return True, "invalid_record"
    if is_generated_app(app) or is_ghostlab_app(app) or is_system_creator_or_lab(app):
        return False, "protected_generated_or_system"
    if str(app.get("map_actions_source") or "") == ADMIN_SEED_SOURCE:
        return False, "admin_seed_v1"
    if is_test_or_dev_app(app):
        return True, "test_or_dev_app"
    if str(app.get("map_actions_source") or "") in {"migration_inferred", "legacy_inferred"}:
        return True, "migration_inferred"
    if app.get("map_actions") and not has_meaningful_contract(app):
        return True, "missing_contract"
    return False, "kept"


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


def app_tool_file_candidates(app):
    candidates = set()
    name = app_name(app)
    if name:
        candidates.add(f"{name}.sh")
    for key in ["project_file", "file_name"]:
        value = str(app.get(key) or "").strip()
        if value:
            candidates.add(value)
    return candidates


def estimate_app_disk_usage(app):
    for key in ("disk_usage", "install_size", "file_size"):
        if key in app:
            return clamp_int(app.get(key), default=8, minimum=1)
    return max(8, len(app.get("map_actions") or []) * 3 + len(app.get("operation_types") or []) * 5)


def estimate_file_size(file_entry):
    if isinstance(file_entry, dict):
        if "file_size" in file_entry:
            return clamp_int(file_entry.get("file_size"), default=1, minimum=0)
        resources = file_entry.get("resource_types") or []
        return max(1, len(resources) * 4)
    if file_entry:
        return 1
    return 0


def calculate_storage_used(profile):
    used = 0
    for app in profile.get("apps") or []:
        if isinstance(app, dict):
            used += estimate_app_disk_usage(app)
    files = profile.get("files") or {}
    if isinstance(files, dict):
        for category, entries in files.items():
            if category == "projects":
                entries = entries or []
            if isinstance(entries, dict):
                entries = list(entries.values())
            for item in entries or []:
                used += estimate_file_size(item)
    return used


def normalize_profile_storage(profile):
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


def double_existing_seed_price(app):
    app = copy.deepcopy(app)
    if (
        app.get("price_adjustment") == PRICE_ADJUSTMENT_MARK
        or is_generated_app(app)
        or is_ghostlab_app(app)
        or is_system_creator_or_lab(app)
        or str(app.get("map_actions_source") or "") == ADMIN_SEED_SOURCE
    ):
        return app, False
    if "price" not in app:
        return app, False
    original = clamp_int(app.get("price"), default=0, minimum=0)
    if original <= 0:
        return app, False
    app["price"] = original * 2
    app["price_adjustment"] = PRICE_ADJUSTMENT_MARK
    app["price_before_adjustment"] = original
    return app, True


def level_for_risk(risk):
    return max(1, int(risk) * 2)


def respect_for_risk(risk):
    return max(0, int(risk) * 30)


def build_level(title, steps, success):
    return [{
        "title": title,
        "steps": steps,
        "result_success": success,
        "result_failure": "Operacja przerwana albo zablokowana przez warunki celu.",
    }]


def seed_tool(spec, admin_nick="CyberPhoenix"):
    risk = int(spec["risk_level"])
    quality = int(spec.get("quality_score", 86))
    reliability = int(spec.get("reliability", 88))
    disk_usage = int(spec.get("disk_usage", spec.get("file_size", 20) + 4))
    app = {
        "id": f"admin_seed_{spec['map_action']}_v1",
        "name": spec["name"],
        "icon": spec["icon"],
        "type": spec["type"],
        "category": "tools",
        "tool_family": spec["tool_family"],
        "tool_mode": spec.get("tool_mode", "map"),
        "description": spec["description"],
        "price": int(spec["price"]),
        "allowed_fractions": [],
        "risk_level": risk,
        "purchase_account": "admin",
        "creator_username": "admin",
        "creator_nick": admin_nick or "CyberPhoenix",
        "creator_level_at_publish": 80,
        "creator_power": int(spec.get("creator_power", 92)),
        "quality_score": quality,
        "reliability": reliability,
        "power_score": int(spec.get("power_score", min(100, quality * 0.45 + reliability * 0.35 + risk * 5))),
        "price_hint": int(spec.get("price_hint", spec["price"])),
        "balance_tier": spec.get("balance_tier", "Advanced"),
        "file_size": int(spec.get("file_size", max(8, disk_usage - 4))),
        "disk_usage": disk_usage,
        "install_size": disk_usage,
        "required_level": int(spec.get("required_level", level_for_risk(risk))),
        "required_respect": int(spec.get("required_respect", respect_for_risk(risk))),
        "interface": spec.get("interface", "progressbar_random"),
        "levels": build_level(spec["name"], spec["steps"], spec["success"]),
        "map_actions": [spec["map_action"]],
        "map_actions_source": ADMIN_SEED_SOURCE,
        "target_types": spec["target_types"],
        "operation_types": spec["operation_types"],
        "resource_types": spec["resource_types"],
        "generated": False,
        "published": True,
        "admin_seed_version": 1,
    }
    return app


ADMIN_SEED_SPECS = [
    {
        "map_action": "scan_ports",
        "name": "Port Sentinel",
        "icon": "🔍",
        "type": "scanner",
        "tool_family": "scanner_recon",
        "description": "Profesjonalna sonda rozpoznania uslug celu w swiecie CHAOS. Tworzy stan recon, nie loot handlowy.",
        "target_types": ["router", "server", "poi", "atm", "camera", "player", "pillar"],
        "operation_types": ["recon_scan"],
        "resource_types": ["internal_recon_state"],
        "risk_level": 2,
        "price": 520,
        "file_size": 14,
        "disk_usage": 18,
        "steps": ["Kalibracja sondy...", "Mapowanie powierzchni celu...", "Zapis stanu recon..."],
        "success": "Recon celu zostal zaktualizowany.",
    },
    {
        "map_action": "exploit",
        "name": "Vector Key",
        "icon": "💥",
        "type": "exploit",
        "tool_family": "exploit",
        "description": "Symulowane narzedzie wplywu na cel. Przygotowuje warunki pod dalsze operacje bez realnych instrukcji.",
        "target_types": ["router", "server", "camera", "atm", "player", "pillar"],
        "operation_types": [],
        "resource_types": ["internal_recon_state"],
        "risk_level": 4,
        "price": 1100,
        "file_size": 24,
        "disk_usage": 30,
        "balance_tier": "Advanced",
        "steps": ["Analiza wektora...", "Symulacja podatnosci...", "Ocena skutku w grze..."],
        "success": "Cel zostal oznaczony jako przygotowany do dalszych dzialan.",
    },
    {
        "map_action": "sniff",
        "name": "Signal Lattice",
        "icon": "📡",
        "type": "sniffer",
        "tool_family": "sniffer",
        "description": "Lekki sniffer grywalny do obserwacji sygnalow celu i odblokowania kolejnych krokow.",
        "target_types": ["router", "server", "atm", "player", "pillar"],
        "operation_types": ["persistent_sniffer"],
        "resource_types": ["internal_recon_state", "device_logs"],
        "risk_level": 3,
        "price": 980,
        "file_size": 22,
        "disk_usage": 28,
        "steps": ["Strojenie odbiornika...", "Czytanie sygnalu...", "Budowanie profilu ruchu..."],
        "success": "Sygnal celu zostal przeanalizowany.",
    },
    {
        "map_action": "trace",
        "name": "Trace Compass",
        "icon": "🎯",
        "type": "tracker",
        "tool_family": "scanner_recon",
        "description": "Uniwersalny tracker celu, laczacy lokalne slady z mapa operacji.",
        "target_types": ["person", "phone", "player", "poi", "pillar"],
        "operation_types": ["generic_trace"],
        "resource_types": ["location_history", "internal_recon_state"],
        "risk_level": 2,
        "price": 760,
        "file_size": 16,
        "disk_usage": 21,
        "steps": ["Ustalanie punktu odniesienia...", "Skladanie sladow...", "Zapis historii pozycji..."],
        "success": "Historia pozycji zostala przygotowana.",
    },
    {
        "map_action": "camera_stream",
        "name": "Glass Eye",
        "icon": "👁️",
        "type": "camera_tool",
        "tool_family": "sniffer",
        "description": "Monitor kamery z buforowaniem fragmentow materialu dla File Managera.",
        "target_types": ["camera"],
        "operation_types": ["camera_stream"],
        "resource_types": ["camera_dump", "video_material"],
        "risk_level": 3,
        "price": 1350,
        "file_size": 32,
        "disk_usage": 40,
        "steps": ["Otwieranie kanalu...", "Stabilizacja streamu...", "Dzielnie materialu na fragmenty..."],
        "success": "Stream kamery zostal uruchomiony.",
    },
    {
        "map_action": "camera_shutdown",
        "name": "Blindfold Relay",
        "icon": "🛡️",
        "type": "camera_tool",
        "tool_family": "exploit",
        "description": "Czasowe zaklocenie kamery jako support operation zmniejszajaca ryzyko obserwacji.",
        "target_types": ["camera"],
        "operation_types": ["camera_shutdown"],
        "resource_types": [],
        "risk_level": 2,
        "price": 1250,
        "file_size": 26,
        "disk_usage": 34,
        "steps": ["Ustalanie rytmu kamery...", "Zaklocanie obrazu...", "Ustawianie timera powrotu..."],
        "success": "Kamera zostala czasowo zaklocona.",
    },
    {
        "map_action": "trace_device",
        "name": "Device Threader",
        "icon": "📶",
        "type": "tracker",
        "tool_family": "scanner_recon",
        "description": "Tracker urzadzen i telefonow, budujacy pakiet device intelligence.",
        "target_types": ["phone", "person", "player"],
        "operation_types": ["device_tracking"],
        "resource_types": ["location_history", "device_logs", "personal_records"],
        "risk_level": 3,
        "price": 1480,
        "file_size": 28,
        "disk_usage": 35,
        "steps": ["Laczenie identyfikatorow...", "Odczyt sladow urzadzenia...", "Budowanie paczki danych..."],
        "success": "Pakiet device intelligence zostal przygotowany.",
    },
    {
        "map_action": "mic_sniff",
        "name": "Quiet Room",
        "icon": "📡",
        "type": "audio_tool",
        "tool_family": "sniffer",
        "description": "Operacja mikrofonowa tworzaca transkrypcje audio jako placeholder gameplayowy.",
        "target_types": ["person", "venue", "player"],
        "operation_types": ["microphone_sniffer"],
        "resource_types": ["audio_transcript"],
        "risk_level": 3,
        "price": 1320,
        "file_size": 24,
        "disk_usage": 31,
        "steps": ["Strojenie progu sygnalu...", "Zbieranie probek audio...", "Tworzenie transkrypcji..."],
        "success": "Transkrypcja audio zostala przygotowana.",
    },
    {
        "map_action": "car_hack",
        "name": "ECU Prism",
        "icon": "🚗",
        "type": "vehicle_tool",
        "tool_family": "exploit",
        "description": "Diagnostyczne narzedzie ECU dla pojazdow w swiecie gry.",
        "target_types": ["vehicle"],
        "operation_types": ["vehicle_ecu"],
        "resource_types": ["vehicle_diagnostics"],
        "risk_level": 4,
        "price": 2100,
        "file_size": 34,
        "disk_usage": 44,
        "balance_tier": "Pro",
        "steps": ["Otwieranie magistrali ECU...", "Czytanie diagnostyki...", "Zapis raportu pojazdu..."],
        "success": "Diagnostyka pojazdu zostala wygenerowana.",
    },
    {
        "map_action": "trace_gps",
        "name": "Route Weaver",
        "icon": "🗺️",
        "type": "tracker",
        "tool_family": "scanner_recon",
        "description": "Tracker GPS pojazdow zapisujacy checkpointy i historie lokalizacji.",
        "target_types": ["vehicle"],
        "operation_types": ["vehicle_tracking"],
        "resource_types": ["gps_logs", "location_history"],
        "risk_level": 2,
        "price": 1150,
        "file_size": 22,
        "disk_usage": 29,
        "steps": ["Zakladanie sledzenia...", "Probkowanie trasy...", "Zapis checkpointow..."],
        "success": "Historia GPS zostala przygotowana.",
    },
    {
        "map_action": "atm_logs",
        "name": "Vault Ledger",
        "icon": "💳",
        "type": "financial_tool",
        "tool_family": "sniffer",
        "description": "Wysokowartosciowy czytnik logow ATM dla paczek finansowych wysokiego ryzyka.",
        "target_types": ["atm"],
        "operation_types": ["atm_log_extraction"],
        "resource_types": ["atm_dump", "financial_records"],
        "risk_level": 5,
        "price": 2800,
        "file_size": 38,
        "disk_usage": 50,
        "balance_tier": "Pro",
        "steps": ["Synchronizacja z ATM...", "Odczyt dziennika...", "Pakowanie rekordow finansowych..."],
        "success": "Paczka ATM zostala przygotowana.",
    },
    {
        "map_action": "install_sniffer",
        "name": "Needle Implant",
        "icon": "🧲",
        "type": "sniffer",
        "tool_family": "sniffer",
        "description": "Trwaly implant danych dla routerow, serwerow i ATM. Zbiera dane po czasie.",
        "target_types": ["router", "server", "atm"],
        "operation_types": ["persistent_sniffer"],
        "resource_types": ["credentials", "financial_records", "device_logs"],
        "risk_level": 5,
        "price": 3200,
        "file_size": 42,
        "disk_usage": 55,
        "balance_tier": "Pro",
        "steps": ["Instalacja implantu...", "Ukrywanie znacznika...", "Zbieranie danych..."],
        "success": "Implant zostal aktywowany.",
    },
    {
        "map_action": "scan_hotspots",
        "name": "Hotspot Cartographer",
        "icon": "📶",
        "type": "scanner",
        "tool_family": "scanner_recon",
        "description": "Skaner sieci bezprzewodowych i hotspotow na mapie.",
        "target_types": ["router", "venue", "poi"],
        "operation_types": ["wifi_scanner"],
        "resource_types": ["wifi_networks", "hotspot_database"],
        "risk_level": 2,
        "price": 920,
        "file_size": 20,
        "disk_usage": 27,
        "steps": ["Nasluch pasma...", "Grupowanie hotspotow...", "Tworzenie tabeli sieci..."],
        "success": "Lista hotspotow zostala przygotowana.",
    },
    {
        "map_action": "audio_hack",
        "name": "Echo Needle",
        "icon": "🎙️",
        "type": "audio_tool",
        "tool_family": "exploit",
        "description": "Zaklocenie audio tworzace transkrypcje lub stan wsparcia zalezne od celu.",
        "target_types": ["venue", "person", "player"],
        "operation_types": ["audio_interference"],
        "resource_types": ["audio_transcript"],
        "risk_level": 4,
        "price": 1750,
        "file_size": 30,
        "disk_usage": 38,
        "steps": ["Wejscie w kanal audio...", "Zaklocanie sygnalu...", "Zapis sladu operacji..."],
        "success": "Operacja audio zostala zakonczona.",
    },
]


def build_admin_seed_tools(admin_nick="CyberPhoenix"):
    return [seed_tool(spec, admin_nick=admin_nick) for spec in ADMIN_SEED_SPECS]


def get_admin_nick(profiles):
    for item in profiles:
        if item["username"] == "admin":
            profile = item.get("profile") or {}
            return profile.get("nick") or "CyberPhoenix"
    return "CyberPhoenix"


def clean_catalog(apps, admin_nick):
    kept = []
    removed = []
    price_doubled = []
    admin_seed_ids = {f"admin_seed_{action}_v1" for action in IMPORTANT_MAP_ACTIONS}

    for app in apps or []:
        remove, reason = should_remove_catalog_app(app)
        if remove:
            removed.append({"id": app_id(app), "name": app_name(app), "reason": reason})
            continue
        if app_id(app) in admin_seed_ids and str(app.get("map_actions_source") or "") == ADMIN_SEED_SOURCE:
            continue
        adjusted, changed = double_existing_seed_price(app)
        if changed:
            price_doubled.append({
                "id": app_id(app),
                "name": app_name(app),
                "old_price": app.get("price"),
                "new_price": adjusted.get("price"),
            })
        kept.append(adjusted)

    seed_tools = build_admin_seed_tools(admin_nick)
    existing_ids = {app_id(app) for app in kept}
    added = [app for app in seed_tools if app_id(app) not in existing_ids]
    updated = [app for app in seed_tools if app_id(app) in existing_ids]
    final_apps = kept + added
    return final_apps, {
        "catalog_removed": removed,
        "catalog_kept": len(kept),
        "seed_added": len(added),
        "seed_updated": len(updated),
        "price_doubled": price_doubled,
        "final_catalog_count": len(final_apps),
    }


def should_remove_profile_app(app, removed_catalog_ids):
    if not isinstance(app, dict):
        return True
    if is_generated_app(app) or is_ghostlab_app(app):
        return False
    if str(app.get("map_actions_source") or "") == ADMIN_SEED_SOURCE:
        return False
    if is_test_or_dev_app(app):
        return True
    if app_id(app) in removed_catalog_ids:
        return True
    return False


def clean_profile(profile, removed_catalog_ids, valid_catalog_apps):
    profile = copy.deepcopy(profile or {})
    files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
    tools = list(files.get("tools") or [])
    old_apps = list(profile.get("apps") or [])
    kept_apps = []
    removed_apps = []
    removed_tool_names = set()

    for app in old_apps:
        if should_remove_profile_app(app, removed_catalog_ids):
            removed_apps.append({"id": app_id(app), "name": app_name(app)})
            removed_tool_names.update(app_tool_file_candidates(app))
        else:
            kept_apps.append(app)

    valid_tool_names = set()
    for app in kept_apps:
        valid_tool_names.update(app_tool_file_candidates(app))
    for app in valid_catalog_apps:
        if str(app.get("map_actions_source") or "") == ADMIN_SEED_SOURCE:
            valid_tool_names.update(app_tool_file_candidates(app))

    cleaned_tools = []
    orphan_tools_removed = 0
    for item in tools:
        name = tool_file_entry_name(item)
        if name in removed_tool_names:
            orphan_tools_removed += 1
            continue
        if name and name.endswith(".sh") and valid_tool_names and name not in valid_tool_names:
            orphan_tools_removed += 1
            continue
        cleaned_tools.append(item)

    files["tools"] = cleaned_tools
    profile["files"] = files
    profile["apps"] = kept_apps
    before_storage = clamp_int(profile.get("storage_used"), default=0, minimum=0)
    normalize_profile_storage(profile)
    after_storage = profile["storage_used"]

    return profile, {
        "removed_apps": removed_apps,
        "removed_tool_entries": len(tools) - len(cleaned_tools),
        "orphan_tools_removed": orphan_tools_removed,
        "storage_before": before_storage,
        "storage_after": after_storage,
        "storage_delta": after_storage - before_storage,
    }


def cleanup_database(conn, apply=False):
    ensure_core_tables(conn)
    original_apps = read_app_config(conn)
    profiles = read_user_profiles(conn)
    admin_nick = get_admin_nick(profiles)
    final_apps, catalog_report = clean_catalog(original_apps, admin_nick)
    removed_catalog_ids = {
        item["id"] for item in catalog_report["catalog_removed"] if item.get("id")
    }
    valid_catalog_apps = final_apps

    profile_reports = []
    profile_updates = []
    for item in profiles:
        new_profile, report = clean_profile(item["profile"], removed_catalog_ids, valid_catalog_apps)
        changed = canonical_json(new_profile) != canonical_json(item["profile"])
        if changed:
            profile_updates.append((item["username"], new_profile))
        report["username"] = item["username"]
        report["changed"] = changed
        profile_reports.append(report)

    report = {
        "mode": "apply" if apply else "dry-run",
        "catalog_before": len(original_apps or []),
        **catalog_report,
        "profiles_scanned": len(profiles),
        "profiles_modified": len(profile_updates),
        "profile_reports": profile_reports,
        "map_action_coverage": map_action_coverage(final_apps),
    }

    if apply:
        write_app_config(conn, final_apps)
        for username, profile in profile_updates:
            write_user_profile(conn, username, profile)
    return report


def map_action_coverage(apps):
    coverage = {action: 0 for action in IMPORTANT_MAP_ACTIONS}
    for app in apps or []:
        for action in app.get("map_actions") or []:
            if action in coverage:
                coverage[action] += 1
    return coverage


def print_report(report, backup_path=""):
    print("App catalog cleanup")
    print(f"mode: {report['mode']}")
    if backup_path:
        print(f"backup: {backup_path}")
    print("")
    print(f"catalog_before: {report['catalog_before']}")
    print(f"catalog_removed: {len(report['catalog_removed'])}")
    print(f"catalog_kept: {report['catalog_kept']}")
    print(f"seed_added: {report['seed_added']}")
    print(f"seed_updated: {report['seed_updated']}")
    print(f"price_doubled: {len(report['price_doubled'])}")
    print(f"final_catalog_count: {report['final_catalog_count']}")
    print(f"profiles_scanned: {report['profiles_scanned']}")
    print(f"profiles_modified: {report['profiles_modified']}")
    print("")
    print("removed catalog apps:")
    for item in report["catalog_removed"]:
        print(f"  - {item['id'] or '<no-id>'}: {item['name']} ({item['reason']})")
    print("")
    print("map action coverage:")
    for action, count in report["map_action_coverage"].items():
        print(f"  - {action}: {count}")
    print("")
    print("profile changes:")
    for item in report["profile_reports"]:
        if item["changed"]:
            print(
                f"  - {item['username']}: apps_removed={len(item['removed_apps'])} "
                f"tools_removed={item['removed_tool_entries']} "
                f"storage_delta={item['storage_delta']}"
            )
    if report["mode"] != "apply":
        print("")
        print("No writes performed. Use --apply to update SQLite.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/game.sqlite3", help="SQLite database path.")
    parser.add_argument("--backup-dir", default="data/backups", help="Backup directory.")
    parser.add_argument("--apply", action="store_true", help="Write cleanup changes.")
    parser.add_argument("--json-report", help="Optional path for full JSON report.")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    backup_path = ""
    if args.apply:
        backup_path = backup_database(db_path, args.backup_dir)

    with sqlite3.connect(db_path) as conn:
        report = cleanup_database(conn, apply=args.apply)
        if args.apply:
            conn.commit()

    if args.json_report:
        target = Path(args.json_report)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print_report(report, backup_path=backup_path)


if __name__ == "__main__":
    main()
