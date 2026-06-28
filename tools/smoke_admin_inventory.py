import os
import sys
from collections import Counter
from datetime import datetime, timedelta

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from profileManagment import UserProfileManager
from run import app, collect_ghost_exchange_files, ensure_files_inventory, mail_store, runtime_file_now, user_store


ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"
RUN_SALE = "--sell" in sys.argv

APP_IDS = [
    "admin_test_scan_ports_1",
    "admin_test_trace_gps_1",
    "admin_test_camera_shutdown_1",
    "admin_test_camera_stream_1",
    "admin_test_atm_logs_1",
    "admin_test_install_sniffer_1",
]

MAP_ACTIONS = [
    {
        "action": "scan_ports",
        "selected_app_id": "admin_test_scan_ports_1",
        "lat": 52.2294,
        "lng": 21.0118,
        "label": "Smoke Port Target",
        "source_type": "server",
    },
    {
        "action": "trace_gps",
        "selected_app_id": "admin_test_trace_gps_1",
        "lat": 52.2297,
        "lng": 21.0122,
        "label": "Smoke Vehicle",
        "source_type": "car",
    },
    {
        "action": "camera_shutdown",
        "selected_app_id": "admin_test_camera_shutdown_1",
        "lat": 52.2301,
        "lng": 21.013,
        "label": "Smoke Camera",
        "source_type": "camera",
    },
    {
        "action": "camera_stream",
        "selected_app_id": "admin_test_camera_stream_1",
        "lat": 52.2301,
        "lng": 21.013,
        "label": "Smoke Camera",
        "source_type": "camera",
    },
    {
        "action": "atm_logs",
        "selected_app_id": "admin_test_atm_logs_1",
        "lat": 52.2304,
        "lng": 21.0135,
        "label": "Smoke ATM",
        "source_type": "atm",
    },
    {
        "action": "install_sniffer",
        "selected_app_id": "admin_test_install_sniffer_1",
        "lat": 52.2308,
        "lng": 21.014,
        "label": "Smoke Router",
        "source_type": "router",
    },
]

REQUIRED_FOLDERS = ["gps", "camera", "atm", "financial", "credentials"]


def print_section(title):
    print(f"\n== {title} ==")


def safe_text(value):
    return str(value).encode("ascii", "replace").decode("ascii")


def safe_print(*values):
    print(*(safe_text(value) for value in values))


def response_json(response):
    try:
        return response.get_json() or {}
    except Exception:
        return {}


def login(client):
    response = client.post("/", data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    if response.status_code not in {200, 302}:
        raise RuntimeError(f"Login failed: HTTP {response.status_code}")


def install_apps(client):
    results = []
    for app_id in APP_IDS:
        response = client.post("/install-app", json={"app_id": app_id})
        data = response_json(response)
        results.append((app_id, response.status_code, data.get("status"), data.get("message")))
    return results


def run_map_actions(client):
    results = []
    for payload in MAP_ACTIONS:
        response = client.post("/hack-action", json=payload)
        data = response_json(response)
        created = data.get("created_operations") or []
        results.append((payload["action"], response.status_code, data.get("status"), len(created)))
    return results


def expire_admin_operations():
    profile = user_store.get_profile(ADMIN_USERNAME)
    operations = profile.get("operations", []) or []
    if not operations:
        return 0
    ended_at = datetime.utcnow() - timedelta(seconds=2)
    started_at = ended_at - timedelta(minutes=12)
    expired_at = ended_at.isoformat(timespec="seconds") + "Z"
    started_value = started_at.isoformat(timespec="seconds") + "Z"
    changed = 0
    for operation in operations:
        if operation.get("status") == "running":
            operation["started_at"] = started_value
            operation["expires_at"] = expired_at
            operation["duration_seconds"] = max(1, int((ended_at - started_at).total_seconds()))
            changed += 1
    if changed:
        UserProfileManager(ADMIN_USERNAME).update_profile({"operations": operations})
    return changed


def inventory_summary(profile):
    files = ensure_files_inventory(profile)
    return {
        folder: [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "resource_types": item.get("resource_types", []),
                "market_status": item.get("market_status"),
            }
            for item in files.get(folder, [])
            if isinstance(item, dict)
        ]
        for folder in REQUIRED_FOLDERS
    }


def demo_entry(folder, name, resource_types, preview_mode):
    now = runtime_file_now()
    return {
        "name": name,
        "file_category": folder,
        "directory": f"/data/{folder}",
        "preview_mode": preview_mode,
        "resource_types": resource_types,
        "operation_id": f"demo_{folder}_smoke",
        "source_operation_id": f"demo_{folder}_smoke",
        "status": "stored",
        "sellable": False,
        "market_status": "not_listed",
        "created_at": now,
        "metadata": {
            "operation_id": f"demo_{folder}_smoke",
            "created_at": now,
            "record_count": 4,
            "quality": "demo",
            "target": {"label": f"Demo {folder}", "lat": 52.2297, "lng": 21.0122},
        },
        "records": [
            {"index": 1, "timestamp": now, "event": "demo", "confidence": "high"},
            {"index": 2, "timestamp": now, "event": "sample", "confidence": "medium"},
        ],
    }


def seed_demo_files_if_needed():
    profile = user_store.get_profile(ADMIN_USERNAME)
    files = ensure_files_inventory(profile)
    before = inventory_summary(profile)
    seeds = {
        "gps": demo_entry("gps", "demo_gps_route.log", ["gps_logs", "location_history"], "table"),
        "camera": demo_entry("camera", "demo_camera_fragment.cam", ["camera_dump"], "media_placeholder"),
        "atm": demo_entry("atm", "demo_atm_dump.dump", ["atm_dump"], "table"),
        "financial": demo_entry("financial", "demo_financial_records.dat", ["financial_records"], "table"),
        "credentials": demo_entry("credentials", "demo_credentials.enc", ["credentials"], "encrypted_blob"),
    }
    added = []
    for folder, entry in seeds.items():
        if not before.get(folder):
            files[folder].append(entry)
            added.append(folder)
    if added:
        ensure_files_inventory(profile)
        UserProfileManager(ADMIN_USERNAME).update_profile({"files": profile["files"]})
    return added


def main():
    with app.test_client() as client:
        login(client)

        print_section("Install apps")
        for row in install_apps(client):
            safe_print(row)

        print_section("Tools")
        profile = user_store.get_profile(ADMIN_USERNAME)
        tools = profile.get("files", {}).get("tools", [])
        for app_id in APP_IDS:
            print(app_id, "installed:", any(app_id == (app.get("id") if isinstance(app, dict) else None) for app in profile.get("apps", [])))
        print("tools_count:", len(tools))

        print_section("Map actions")
        for row in run_map_actions(client):
            safe_print(row)

        changed = expire_admin_operations()
        print_section("Expire operations")
        print("running_operations_expired:", changed)

        operations_response = client.get("/api/operations")
        operations_data = response_json(operations_response)
        print("api_operations:", operations_response.status_code, operations_data.get("success"), "ops:", len(operations_data.get("operations", [])))

        profile = user_store.get_profile(ADMIN_USERNAME)
        risk_events = profile.get("risk_events", []) or []
        risk_counts = Counter(event.get("event_type") for event in risk_events if isinstance(event, dict))
        modified_events = [
            event for event in risk_events
            if isinstance(event, dict) and event.get("modifiers")
        ]
        print_section("Risk events")
        print("risk_events_count:", len(risk_events))
        print("risk_event_types:", dict(sorted(risk_counts.items())))
        print("risk_modified_events:", len(modified_events))
        if modified_events:
            latest_modified = modified_events[-1]
            print(
                "latest_modifier:",
                latest_modified.get("event_type"),
                latest_modified.get("base_risk_score"),
                "->",
                latest_modified.get("risk_score"),
                latest_modified.get("modifier_summary"),
            )
        for event in risk_events[-8:]:
            print(
                " ",
                event.get("event_type"),
                event.get("risk_score"),
                event.get("risk_level"),
                event.get("primary_consequence"),
                event.get("map_action_id") or event.get("operation_type"),
            )

        profile = user_store.get_profile(ADMIN_USERNAME)
        summary = inventory_summary(profile)
        missing = [folder for folder, entries in summary.items() if folder in {"gps", "camera", "credentials"} and not entries]
        missing_atm_financial = not summary.get("atm") and not summary.get("financial")
        if missing or missing_atm_financial:
            print_section("Demo seed")
            print("missing:", missing, "missing_atm_or_financial:", missing_atm_financial)
            print("seeded:", seed_demo_files_if_needed())
            profile = user_store.get_profile(ADMIN_USERNAME)
            summary = inventory_summary(profile)

        print_section("Inventory")
        for folder, entries in summary.items():
            print(folder, len(entries))
            for entry in entries[-3:]:
                print(" ", entry["name"], entry["resource_types"], entry["market_status"])

        direct_exchange_files = collect_ghost_exchange_files(user_store.get_profile(ADMIN_USERNAME))
        print("direct_ghost_exchange_files:", len(direct_exchange_files))

        exchange_response = client.get("/api/ghost-exchange")
        exchange_data = response_json(exchange_response)
        files = exchange_data.get("files", [])
        print_section("Ghost Exchange")
        print("api_ghost_exchange:", exchange_response.status_code, exchange_data.get("success"), "files:", len(files))
        for item in files[:12]:
            print(" ", item.get("name"), item.get("file_category"), item.get("market_category"), item.get("price_preview"), item.get("market_status"))

        if files:
            preview_response = client.post("/api/ghost-exchange/preview", json={"file_id": files[0].get("id")})
            preview_data = response_json(preview_response)
            print_section("Preview sale")
            print("api_preview:", preview_response.status_code, preview_data.get("success"), preview_data.get("message"))
            print("file:", (preview_data.get("file") or {}).get("name"), (preview_data.get("file") or {}).get("market_status"))

        if RUN_SALE:
            sale_files = (client.get("/api/ghost-exchange").get_json() or {}).get("files", [])
            if sale_files:
                before_profile = user_store.get_profile(ADMIN_USERNAME)
                before_hc = before_profile.get("hackcoins", 0)
                before_count = sum(len(inventory_summary(before_profile).get(folder, [])) for folder in REQUIRED_FOLDERS)
                sale_response = client.post("/api/ghost-exchange/sell", json={"file_id": sale_files[0].get("id")})
                sale_data = response_json(sale_response)
                duplicate_response = client.post("/api/ghost-exchange/sell", json={"file_id": sale_files[0].get("id")})
                duplicate_data = response_json(duplicate_response)
                after_profile = user_store.get_profile(ADMIN_USERNAME)
                after_hc = after_profile.get("hackcoins", 0)
                after_count = sum(len(inventory_summary(after_profile).get(folder, [])) for folder in REQUIRED_FOLDERS)
                market_history = ensure_files_inventory(after_profile).get("market", [])
                profile_market_history = after_profile.get("market_history", []) or []
                latest_mail = mail_store.list_messages(ADMIN_USERNAME, "direct", "Ghost Exchange", limit=1)
                print_section("Sell")
                print("api_sell:", sale_response.status_code, sale_data.get("success"), sale_data.get("message"))
                print("api_sell_duplicate:", duplicate_response.status_code, duplicate_data.get("success"), duplicate_data.get("message"))
                print("hc:", before_hc, "->", after_hc)
                print("required_data_file_count:", before_count, "->", after_count)
                print("market_history_count:", len(market_history))
                print("profile_market_history_count:", len(profile_market_history))
                if market_history:
                    last_sale = market_history[-1]
                    print("last_market_record:", last_sale.get("name"), last_sale.get("market_status"), (last_sale.get("metadata") or {}).get("price"))
                if profile_market_history:
                    last_profile_sale = profile_market_history[-1]
                    print("last_profile_market_record:", last_profile_sale.get("file_name"), last_profile_sale.get("status"), last_profile_sale.get("price"))
                if latest_mail:
                    print("latest_mail:", latest_mail[-1].get("subject"), latest_mail[-1].get("created_at"))


if __name__ == "__main__":
    main()
