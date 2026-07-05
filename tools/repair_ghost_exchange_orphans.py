import argparse
import copy
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import run
from database import UserStore
from profileManagment import UserProfileManager


def utc_stamp():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def backup_profile(username, profile, backup_dir):
    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"ghost_exchange_orphans_{username}_{utc_stamp()}.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def collect_sold_file_ids(profile):
    sold_ids = set()
    for entry in profile.get("market_history", []) or []:
        if not isinstance(entry, dict):
            continue
        if isinstance(entry.get("file_ids"), list):
            sold_ids.update(str(item) for item in entry.get("file_ids") if str(item).strip())
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        sale = entry.get("sale") if isinstance(entry.get("sale"), dict) else {}
        for source in (metadata, sale):
            if isinstance(source.get("file_ids"), list):
                sold_ids.update(str(item) for item in source.get("file_ids") if str(item).strip())

    files = run.ensure_files_inventory(profile)
    for entry in files.get("market", []) or []:
        if not isinstance(entry, dict):
            continue
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        sale = entry.get("sale") if isinstance(entry.get("sale"), dict) else {}
        for source in (metadata, sale):
            if isinstance(source.get("file_ids"), list):
                sold_ids.update(str(item) for item in source.get("file_ids") if str(item).strip())
    return sold_ids


def file_size_mb(entry, folder):
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    return run.clamp_storage_number(
        entry.get("file_size") or metadata.get("file_size"),
        default=run.estimate_runtime_file_size(folder, entry),
        minimum=1,
    )


def find_orphans(profile):
    files = run.ensure_files_inventory(profile)
    sold_ids = collect_sold_file_ids(profile)
    report = {
        "sold_file_ids": len(sold_ids),
        "orphans": [],
        "by_sector": {},
        "total_files": 0,
        "total_mb": 0,
    }
    if not sold_ids:
        return report

    for folder in sorted(run.GHOST_EXCHANGE_FILE_CATEGORIES):
        for entry in files.get(folder, []) or []:
            if not isinstance(entry, dict):
                continue
            file_id = str(entry.get("id") or "")
            if not file_id or file_id not in sold_ids:
                continue
            sector = entry.get("market_sector") or run.market_sector_for_file(entry)
            size = file_size_mb(entry, folder)
            item = {
                "id": file_id,
                "name": entry.get("name") or entry.get("filename") or file_id,
                "folder": folder,
                "sector": sector,
                "file_size": size,
                "market_status": entry.get("market_status"),
            }
            report["orphans"].append(item)
            bucket = report["by_sector"].setdefault(sector, {"files": 0, "mb": 0})
            bucket["files"] += 1
            bucket["mb"] += size
            report["total_files"] += 1
            report["total_mb"] += size
    return report


def apply_cleanup(profile, report):
    orphan_ids = {item["id"] for item in report.get("orphans", []) if item.get("id")}
    if not orphan_ids:
        return 0

    files = run.ensure_files_inventory(profile)
    removed = 0
    for folder in sorted(run.GHOST_EXCHANGE_FILE_CATEGORIES):
        kept = []
        for entry in files.get(folder, []) or []:
            if isinstance(entry, dict) and str(entry.get("id") or "") in orphan_ids:
                removed += 1
                continue
            kept.append(entry)
        files[folder] = kept
    run.normalize_profile_storage(profile)
    return removed


def print_report(username, profile_before, report, mode, backup_path=None):
    print(f"user: {username}")
    print(f"mode: {mode}")
    print(
        "storage_before: "
        f"{profile_before.get('storage_used')} / {profile_before.get('storage_capacity')} "
        f"{profile_before.get('storage_unit', 'MB')}"
    )
    print(f"sold_file_ids: {report['sold_file_ids']}")
    print(f"orphan_files: {report['total_files']}")
    print(f"orphan_mb: {report['total_mb']}")
    if backup_path:
        print(f"backup: {backup_path}")
    print()
    print("by_sector:")
    for sector, values in sorted(report["by_sector"].items()):
        print(f"  {sector:12} {values['files']:4} files / {values['mb']:4} MB")
    print()
    print("sample:")
    for item in report["orphans"][:30]:
        print(
            f"  {item['folder']:11} {item['sector']:12} "
            f"{item['file_size']:4} MB {item['id']} {item['name']}"
        )
    if report["total_files"] > 30:
        print(f"  ... and {report['total_files'] - 30} more")


def repair(username, apply=False, backup_dir="data/backups"):
    store = UserStore()
    profile = store.get_profile(username)
    if not profile:
        raise SystemExit(f"Nie znaleziono profilu: {username}")

    profile_before = copy.deepcopy(profile)
    run.normalize_runtime_profile_defaults(profile)
    run.ensure_files_inventory(profile)
    report = find_orphans(profile)

    if not apply:
        print_report(username, profile_before, report, "dry-run")
        print()
        print("No changes written. Re-run with --apply to remove orphan files.")
        return

    backup_path = backup_profile(username, profile_before, backup_dir)
    removed = apply_cleanup(profile, report)
    UserProfileManager(username).update_profile({
        "files": profile.get("files", {}),
        "storage_capacity": profile.get("storage_capacity"),
        "storage_used": profile.get("storage_used"),
        "storage_unit": profile.get("storage_unit", "MB"),
        "storage_soft_limit": True,
        "storage_over_limit": profile.get("storage_over_limit", False),
    })
    print_report(username, profile_before, report, "apply", backup_path=backup_path)
    print()
    print(f"removed_files: {removed}")
    print(
        "storage_after: "
        f"{profile.get('storage_used')} / {profile.get('storage_capacity')} "
        f"{profile.get('storage_unit', 'MB')}"
    )


def main():
    parser = argparse.ArgumentParser(description="Dry-run/apply cleanup sprzedanych orphan files Ghost Exchange.")
    parser.add_argument("username", help="Login profilu")
    parser.add_argument("--apply", action="store_true", help="Zapisz cleanup. Bez tej flagi dziala dry-run.")
    parser.add_argument("--backup-dir", default="data/backups", help="Katalog backupu profilu JSON.")
    args = parser.parse_args()
    repair(args.username, apply=args.apply, backup_dir=args.backup_dir)


if __name__ == "__main__":
    main()
