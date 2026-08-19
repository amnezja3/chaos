import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import TerritoryConflictStore, TerritoryStore, UserStore, db_connect, loads_json
from run import normalize_player_area


def load_raw_area_rows(username):
    with db_connect() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM player_areas
            WHERE owner_username = ?
            ORDER BY id
            """,
            (username,),
        ).fetchall()
    return [dict(row) for row in rows]


def row_to_area(row):
    return {
        "id": row.get("id"),
        "owner_username": row.get("owner_username"),
        "vertices": loads_json(row.get("vertices_json"), []),
        "centroid_lat": row.get("centroid_lat"),
        "centroid_lng": row.get("centroid_lng"),
        "area_size": row.get("area_size"),
        "max_edge_distance": row.get("max_edge_distance"),
        "status": row.get("status"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def backup_snapshot(username, current_rows, proposed_areas, conflicts, captured_targets):
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"territory_visibility_{username}_{timestamp}.json"
    path.write_text(
        json.dumps(
            {
                "username": username,
                "created_at": timestamp,
                "current_player_areas": current_rows,
                "proposed_areas": proposed_areas,
                "active_conflicts": conflicts,
                "captured_targets": captured_targets,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run first territory visibility repair. Rebuilds owner player_areas "
            "from captured_targets through the worker with --enqueue; legacy direct "
            "write remains available only when --apply is explicit."
        )
    )
    parser.add_argument("--username", required=True, help="Owner username to diagnose.")
    parser.add_argument("--apply", action="store_true", help="Write repaired player_areas.")
    parser.add_argument(
        "--enqueue",
        action="store_true",
        help="Enqueue the canonical worker-owned rebuild instead of writing in this process.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Allow apply even when valid player_areas already exist.",
    )
    args = parser.parse_args()
    if args.apply and args.enqueue:
        parser.error("use either --apply or --enqueue")

    username = args.username.strip()
    user_store = UserStore()
    territory_store = TerritoryStore()
    conflict_store = TerritoryConflictStore()

    profile = user_store.get_profile(username)
    if not profile:
        raise SystemExit(f"Profile not found: {username}")

    level = int(profile.get("level") or 1)
    raw_rows = load_raw_area_rows(username)
    raw_areas = [row_to_area(row) for row in raw_rows]
    valid_areas = [area for area in (normalize_player_area(area) for area in raw_areas) if area]
    invalid_areas = [area for area in raw_areas if not normalize_player_area(area)]
    captured_targets = territory_store.list_captured_targets(username, stationary=True)
    proposed_areas = territory_store.build_player_areas(username, level)
    conflicts = conflict_store.list_active_for_player(username)

    current_area_ids = {area.get("id") for area in raw_areas if area.get("id") is not None}
    missing_conflict_area_ids = []
    for conflict in conflicts:
        for area_id in conflict.get("area_ids") or []:
            if area_id not in current_area_ids:
                missing_conflict_area_ids.append({
                    "conflict_key": conflict.get("conflict_key"),
                    "missing_area_id": area_id,
                })

    print("Territory visibility diagnostic")
    print("username:", username)
    print("level:", level)
    print("captured_targets:", len(captured_targets))
    print("current_player_areas:", len(raw_areas))
    print("valid_player_areas:", len(valid_areas))
    print("invalid_player_areas:", len(invalid_areas))
    print("proposed_rebuilt_areas:", len(proposed_areas))
    print("active_conflicts:", len(conflicts))
    print("missing_conflict_area_ids:", len(missing_conflict_area_ids))

    if invalid_areas:
        print("\nInvalid current areas:")
        for area in invalid_areas[:20]:
            print(" ", {
                "id": area.get("id"),
                "status": area.get("status"),
                "vertices_count": len(area.get("vertices") or []),
            })

    if missing_conflict_area_ids:
        print("\nConflicts referencing missing area ids:")
        for item in missing_conflict_area_ids[:20]:
            print(" ", item)

    if proposed_areas:
        print("\nProposed rebuilt areas:")
        for area in proposed_areas[:20]:
            print(" ", {
                "vertices_count": len(area.get("vertices") or []),
                "area_size": round(float(area.get("area_size") or 0), 2),
                "max_edge_distance": round(float(area.get("max_edge_distance") or 0), 2),
                "status": area.get("status", "active"),
            })
    else:
        print("\nNo reconstructable area from captured_targets.")
        print("Controlled gameplay fallback: mark the territory as compromised and send a single non-spam system message.")

    if not args.apply and not args.enqueue:
        print("\nDRY-RUN only. Re-run with --enqueue for the canonical worker repair.")
        return

    if args.enqueue:
        queued = territory_store.enqueue_rebuild_job(
            username,
            reason="operator_visibility_recovery",
        )
        print("\nENQUEUED")
        print("job_id:", queued["job_id"])
        print("owner_username:", queued["owner_username"])
        return

    if valid_areas and not args.replace_existing:
        raise SystemExit(
            "Valid player_areas already exist. Use --replace-existing if you intentionally want to rebuild them."
        )
    if not proposed_areas:
        raise SystemExit("Nothing to restore: captured_targets do not produce a valid area.")

    backup_path = backup_snapshot(username, raw_rows, proposed_areas, conflicts, captured_targets)
    territory_store.replace_player_areas(username, proposed_areas)
    territory_store.refresh_encirclement_statuses()
    print("\nAPPLIED")
    print("backup:", backup_path)
    print("restored_player_areas:", len(proposed_areas))


if __name__ == "__main__":
    main()
