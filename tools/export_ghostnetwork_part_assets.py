"""Read-only GhostNetwork part-to-PNG asset report.

The command reads the canonical catalog and, when available, the selected
runtime cycle. It never creates, resets, or updates a cycle.
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import DB_PATH
from ghostnetwork import GhostNetworkService
from ghostnetwork.catalog import get_catalog, get_catalog_checksum, validate_catalog
from ghostnetwork.part_assets import ASSET_ROOT, RECOMMENDED_DIMENSIONS, part_visual_asset_contract


def build_asset_report(catalog, cycle=None, runtime_parts=None):
    cycle = dict(cycle or {})
    runtime_parts = [dict(item) for item in (runtime_parts or [])]
    runtime_by_code = {str(item.get("part_code") or ""): item for item in runtime_parts}
    rows = []
    for definition in sorted(catalog.get("parts") or [], key=lambda item: int(item.get("sort_order") or 0)):
        part_code = str(definition.get("part_code") or "").strip()
        icon_key = str(definition.get("icon_key") or "").strip()
        runtime = runtime_by_code.get(part_code, {})
        visual_asset = part_visual_asset_contract(definition)
        filename = visual_asset["visual_asset_filename"]
        rows.append({
            "cycle_id": runtime.get("cycle_id") or cycle.get("cycle_id") or None,
            "part_id": runtime.get("part_id") or None,
            "part_code": part_code,
            "part_name": definition.get("name"),
            "clan_code": definition.get("clan_code"),
            "machine_code": definition.get("machine_code"),
            "profession_code": definition.get("profession_code"),
            "icon_key": icon_key,
            "logical_asset_key": visual_asset["visual_asset_key"],
            "filename": filename,
            "target_path": visual_asset["visual_asset_path"],
            "format": "PNG",
            "recommended_dimensions": RECOMMENDED_DIMENSIONS,
            "transparency_required": True,
            "state_variants_required": False,
        })
    validation = validate_catalog(catalog)
    errors = list(validation.get("errors") or [])
    if len(rows) != 20:
        errors.append(f"asset_row_count_{len(rows)}_not_20")
    if len({item["logical_asset_key"] for item in rows}) != len(rows):
        errors.append("duplicate_logical_asset_key")
    if len({item["target_path"] for item in rows}) != len(rows):
        errors.append("duplicate_target_path")
    if runtime_parts and set(runtime_by_code) != {item["part_code"] for item in rows}:
        errors.append("runtime_parts_do_not_match_catalog")
    return {
        "ok": not errors,
        "read_only": True,
        "catalog_version": catalog.get("catalog_version"),
        "catalog_checksum": get_catalog_checksum(catalog),
        "cycle_id": cycle.get("cycle_id") or None,
        "parts_count": len(rows),
        "runtime_parts_count": len(runtime_parts),
        "asset_root": ASSET_ROOT,
        "errors": errors,
        "parts": rows,
    }


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-path", default=DB_PATH, help="SQLite database path")
    parser.add_argument("--cycle-id", default="", help="Cycle to project; defaults to active cycle")
    return parser.parse_args()


def main():
    args = parse_args()
    service = GhostNetworkService(db_path=args.db_path)
    cycle = (
        service.repository.get_cycle(args.cycle_id)
        if args.cycle_id else service.get_active_cycle()
    )
    runtime_parts = service.repository.list_parts(cycle["cycle_id"]) if cycle else []
    report = build_asset_report(get_catalog(), cycle=cycle, runtime_parts=runtime_parts)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
