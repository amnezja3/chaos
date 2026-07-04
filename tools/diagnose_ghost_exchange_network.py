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
    }


def print_section(title):
    print()
    print("=" * 88)
    print(title)
    print("=" * 88)


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
            f"size={str(item['file_size']):>4} rec={str(item['records']):>3}"
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

    print_section(f"Pliki sektora {sector} przed runtime")
    print_files(profile, sector)
    print_sector(profile, sector, f"Read model sektora {sector} przed runtime")

    before = copy.deepcopy(profile)
    now = run.market_runtime_now()
    first = run.refresh_market_runtime(username, profile, now=now)
    print_section("Refresh market runtime TERAZ - dry-run na kopii profilu")
    print(json.dumps(first, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print_files(profile, sector)
    print_sector(profile, sector, f"Read model sektora {sector} po refreshu TERAZ")

    later_profile = copy.deepcopy(before)
    later_now = now + timedelta(minutes=simulate_minutes)
    first_later = run.refresh_market_runtime(username, later_profile, now=now)
    second_later = run.refresh_market_runtime(username, later_profile, now=later_now)
    print_section(f"Symulacja: TERAZ, potem +{simulate_minutes} min - dry-run na kopii profilu")
    print("first:")
    print(json.dumps(first_later, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print("second:")
    print(json.dumps(second_later, ensure_ascii=False, indent=2, sort_keys=True, default=str))
    print_files(later_profile, sector)
    print_sector(later_profile, sector, f"Read model sektora {sector} po symulacji")

    print_section("Diagnoza progow")
    threshold = run.MARKET_SECTOR_THRESHOLDS.get(sector, {})
    dwell = run.MARKET_SECTOR_DWELL_SECONDS.get(sector, 5 * 60)
    print(f"threshold_mb: {threshold.get('threshold_mb')}")
    print(f"threshold_records: {threshold.get('threshold_records')}")
    print(f"dwell_seconds: {dwell}")
    print("UWAGA: skrypt nie zapisuje danych. Jesli symulacja sprzedaje, a produkcja nie, problem jest w persystencji/odswiezaniu profilu.")


def main():
    parser = argparse.ArgumentParser(description="Dry-run diagnostyki Ghost Exchange dla sektora network.")
    parser.add_argument("username", help="Login profilu do sprawdzenia")
    parser.add_argument("--sector", default="network", help="Sektor rynku, domyslnie network")
    parser.add_argument("--simulate-minutes", type=int, default=6, help="Ile minut przesunac drugi refresh")
    args = parser.parse_args()
    diagnose(args.username, args.sector, args.simulate_minutes)


if __name__ == "__main__":
    main()
