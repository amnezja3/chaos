import argparse
import copy
import json
import os
import sys
from datetime import timedelta


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import run
from database import UserStore


def short(value, limit=72):
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def file_summary(entry):
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    return {
        "id": entry.get("id"),
        "name": entry.get("name") or entry.get("filename"),
        "status": entry.get("market_status"),
        "normalized_status": run.normalize_file_market_status(entry),
        "sellable": entry.get("sellable"),
        "eligible": run.is_market_eligible_file(entry),
        "sector": entry.get("market_sector") or run.market_sector_for_file(entry),
        "file_size": entry.get("file_size") or metadata.get("file_size"),
        "records": run.runtime_file_record_count(entry),
        "queued_at": entry.get("queued_at"),
        "listed_at": entry.get("listed_at"),
        "batch_id": entry.get("batch_id"),
        "resources": entry.get("resource_types"),
        "gx_reason": file_exclusion_reason(entry),
    }


def print_section(title):
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


def file_exclusion_reason(entry):
    if not isinstance(entry, dict):
        return "invalid_entry"
    raw_status = str(entry.get("market_status") or "not_listed")
    normalized = run.normalize_file_market_status(entry)
    if raw_status in {"sold", "deleted", "archived"} or normalized in {"sold", "deleted", "archived"}:
        return "terminal_status"
    if normalized not in {"queued_for_market", "listed"}:
        return f"normalized_status:{normalized}"
    if not run.is_market_eligible_file(entry):
        return "not_market_eligible"
    return "included"


def print_files(profile, sector):
    files = run.ensure_files_inventory(profile)
    rows = []
    for folder in sorted(run.GHOST_EXCHANGE_FILE_CATEGORIES):
        for entry in files.get(folder, []):
            if not isinstance(entry, dict):
                continue
            summary = file_summary(entry)
            if summary["sector"] != sector:
                continue
            rows.append((folder, summary))

    if not rows:
        print(f"Brak plikow sektora {sector}.")
        return

    for folder, item in rows:
        print(
            f"{folder:11} {short(item['name'], 42):42} "
            f"raw={item['status']!s:17} norm={item['normalized_status']!s:17} "
            f"sellable={str(item['sellable']):5} eligible={str(item['eligible']):5} "
            f"size={str(item['file_size']):>4} rec={str(item['records']):>3} "
            f"gx={item['gx_reason']}"
        )
        print(
            f"{'':11} id={short(item['id'], 56)} "
            f"queued_at={item['queued_at'] or '-'} listed_at={item['listed_at'] or '-'}"
        )
        print(f"{'':11} batch_id={item['batch_id'] or '-'} resources={item['resources']}")


def print_sector(profile, sector, label):
    sectors = run.build_ghost_exchange_sector_payload(profile)
    payload = next((item for item in sectors if item.get("sector") == sector), None)
    print_section(label)
    print(json.dumps(payload or {}, ensure_ascii=False, indent=2, sort_keys=True))


def print_sector_table(profile, label):
    print_section(label)
    sectors = run.build_ghost_exchange_sector_payload(profile)
    for payload in sectors:
        print(
            f"{payload.get('sector', '-'):12} "
            f"status={payload.get('status', '-'):13} "
            f"pending={payload.get('pending_files', 0):>3} files / {payload.get('pending_mb', 0):>4} MB "
            f"records={payload.get('pending_records', 0):>4} "
            f"missing={payload.get('missing_mb', 0):>4} MB / {payload.get('missing_records', 0):>3} rec "
            f"progress={payload.get('progress_percent', 0):>3}% "
            f"batch={payload.get('batch_id') or '-'}"
        )


def profile_market_sectors(profile, requested_sector):
    if requested_sector and requested_sector != "all":
        return [requested_sector]
    sectors = set(run.MARKET_SECTOR_THRESHOLDS.keys())
    files = run.ensure_files_inventory(profile)
    for folder in run.GHOST_EXCHANGE_FILE_CATEGORIES:
        for entry in files.get(folder, []):
            if isinstance(entry, dict):
                sectors.add(entry.get("market_sector") or run.market_sector_for_file(entry))
    return sorted(sector for sector in sectors if sector)


def diagnose(username, sector, simulate_minutes):
    store = UserStore()
    profile = store.get_profile(username)
    if not profile:
        raise SystemExit(f"Nie znaleziono profilu: {username}")

    profile = copy.deepcopy(profile)
    run.normalize_runtime_profile_defaults(profile)
    run.ensure_files_inventory(profile)

    print_section("Profil / storage")
    print(f"username: {username}")
    print(f"storage: {profile.get('storage_used')} / {profile.get('storage_capacity')} {profile.get('storage_unit', 'MB')}")
    print(f"hackcoins: {profile.get('hackcoins')}")
    print(f"market_history: {len(profile.get('market_history') or [])}")
    print(f"files.market: {len((profile.get('files') or {}).get('market') or [])}")

    sectors_to_report = profile_market_sectors(profile, sector)

    print_sector_table(profile, "Read model wszystkich sektorow przed runtime")
    for item_sector in sectors_to_report:
        print_section(f"Pliki sektora {item_sector} przed runtime")
        print_files(profile, item_sector)
        print_sector(profile, item_sector, f"Read model sektora {item_sector} przed runtime")

    before = copy.deepcopy(profile)
    now = run.market_runtime_now()
    first = run.refresh_market_runtime(username, profile, now=now)
    print_section("Refresh market runtime TERAZ - dry-run na kopii profilu")
    print(json.dumps(first, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print_sector_table(profile, "Read model wszystkich sektorow po refreshu TERAZ")
    for item_sector in sectors_to_report:
        print_files(profile, item_sector)
        print_sector(profile, item_sector, f"Read model sektora {item_sector} po refreshu TERAZ")

    later_profile = copy.deepcopy(before)
    later_now = now + timedelta(minutes=simulate_minutes)
    first_later = run.refresh_market_runtime(username, later_profile, now=now)
    second_later = run.refresh_market_runtime(username, later_profile, now=later_now)
    print_section(f"Symulacja: TERAZ, potem +{simulate_minutes} min - dry-run na kopii profilu")
    print("first:")
    print(json.dumps(first_later, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print("second:")
    print(json.dumps(second_later, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print_sector_table(later_profile, "Read model wszystkich sektorow po symulacji")
    for item_sector in sectors_to_report:
        print_files(later_profile, item_sector)
        print_sector(later_profile, item_sector, f"Read model sektora {item_sector} po symulacji")

    print_section("Diagnoza progow")
    for item_sector in sectors_to_report:
        threshold = run.MARKET_SECTOR_THRESHOLDS.get(item_sector, {})
        dwell = run.MARKET_SECTOR_DWELL_SECONDS.get(item_sector, 5 * 60)
        print(
            f"{item_sector:12} threshold_mb={threshold.get('threshold_mb')} "
            f"threshold_records={threshold.get('threshold_records')} dwell_seconds={dwell}"
        )
    print("UWAGA: skrypt nie zapisuje danych. Jesli symulacja sprzedaje, a produkcja nie, problem jest w persystencji/odswiezaniu profilu.")


def main():
    parser = argparse.ArgumentParser(description="Dry-run diagnostyki Ghost Exchange dla sektorow rynku.")
    parser.add_argument("username", help="Login profilu do sprawdzenia")
    parser.add_argument("--sector", default="network", help="Sektor rynku, albo all. Domyslnie network")
    parser.add_argument("--simulate-minutes", type=int, default=6, help="Ile minut przesunac drugi refresh")
    args = parser.parse_args()
    diagnose(args.username, args.sector, args.simulate_minutes)


if __name__ == "__main__":
    main()
