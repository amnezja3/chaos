#!/usr/bin/env python3
"""Read-only Sprint 130.11 diagnosis of trolu2 territory level scaling."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from territory_geometry import (  # noqa: E402
    BASE_AREA_EDGE_METERS,
    build_player_areas,
    connected_target_groups,
    point_in_polygon,
    polygons_intersect,
)


CANONICAL_USERNAME = "trolu2"
LEVELS = (2, 25, 26, 50)
DEFAULT_INCIDENT_AT = "2026-08-21T15:08:32"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def loads_object(raw: Any) -> dict[str, Any]:
    try:
        value = json.loads(raw or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def loads_list(raw: Any) -> list[Any]:
    try:
        value = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def readonly_connection(path: str) -> sqlite3.Connection:
    uri = f"file:{Path(path).resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row["name"])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row["name"]) for row in conn.execute(f'PRAGMA table_info("{table}")')}


def first_text(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def target_position(target: dict[str, Any]) -> tuple[float, float] | None:
    try:
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
    except (TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lng)):
        return None
    return round(lat, 7), round(lng, 7)


def target_id(target: dict[str, Any], fallback: str = "") -> str:
    stable = first_text(
        target.get("target_id"), target.get("target_key"), target.get("id"), fallback
    )
    if stable:
        return stable
    identity = {
        key: target.get(key)
        for key in ("lat", "lng", "lon", "label", "name", "source_type")
        if key in target
    }
    return "derived:" + digest(identity)[:20]


def target_kind(target: dict[str, Any]) -> str:
    role = first_text(
        target.get("node_role"), target.get("target_type"),
        target.get("type"), target.get("source_type"),
    ).lower()
    if role in {"pillar", "inner"}:
        return role
    if "inner" in role:
        return "inner"
    if "pillar" in role or "vulnerab" in role or "territory" in role:
        return "pillar"
    return role or "unknown"


def timestamp_classification(timestamp: str, incident_at: str) -> str:
    timestamp = str(timestamp or "").strip()
    if not timestamp:
        return "UNKNOWN"
    return "PRE_INCIDENT" if timestamp <= incident_at else "POST_INCIDENT"


def load_subject_objects(
    conn: sqlite3.Connection, incident_at: str
) -> dict[str, Any]:
    captured_columns = table_columns(conn, "captured_targets")
    captured_select = [
        name for name in (
            "id", "owner_username", "lat", "lng", "label", "name", "icon",
            "source_type", "generated", "stationary", "target_json",
            "captured_at", "created_at", "updated_at",
        ) if name in captured_columns
    ]
    captured_rows = conn.execute(
        f"SELECT {','.join(captured_select)} FROM captured_targets "
        "WHERE owner_username=? ORDER BY captured_at, id",
        (CANONICAL_USERNAME,),
    ).fetchall()
    ownership_columns = table_columns(conn, "territory_target_ownership")
    ownership_select = [
        name for name in (
            "target_id", "owner_username", "ownership_version", "lat", "lng",
            "label", "target_json", "created_at", "updated_at",
        ) if name in ownership_columns
    ]
    ownership_rows = conn.execute(
        f"SELECT {','.join(ownership_select)} FROM territory_target_ownership "
        "WHERE owner_username=? ORDER BY target_id",
        (CANONICAL_USERNAME,),
    ).fetchall()

    ownership_by_position: dict[tuple[float, float], list[sqlite3.Row]] = {}
    for row in ownership_rows:
        position = target_position(dict(row))
        if position:
            ownership_by_position.setdefault(position, []).append(row)

    captured = []
    stationary_material = []
    captured_ids = set()
    for row in captured_rows:
        raw = dict(row)
        payload = loads_object(raw.get("target_json"))
        payload.setdefault("lat", raw.get("lat"))
        payload.setdefault("lng", raw.get("lng"))
        position = target_position(payload)
        ownership_matches = ownership_by_position.get(position, []) if position else []
        fallback_candidates = [match["target_id"] for match in ownership_matches]
        fallback_candidates.append(f"captured-row:{raw.get('id')}")
        fallback_id = first_text(*fallback_candidates)
        stable_id = target_id(payload, fallback_id)
        captured_ids.add(stable_id)
        created = first_text(
            raw.get("captured_at"), raw.get("created_at"), payload.get("captured_at")
        )
        entry = {
            "target_id": stable_id,
            "kind": target_kind(payload),
            "lat": position[0] if position else None,
            "lng": position[1] if position else None,
            "stationary": bool(raw.get("stationary")),
            "generated": bool(raw.get("generated")),
            "ownership_source": first_text(
                payload.get("ownership_source"), payload.get("source"),
                payload.get("source_type"), raw.get("source_type"),
            ) or "UNKNOWN",
            "canonical_owner": CANONICAL_USERNAME,
            "captured_at": created or None,
            "updated_at": first_text(raw.get("updated_at")) or None,
            "incident_relation": timestamp_classification(created, incident_at),
            "ownership_registry_ids": sorted({
                str(match["target_id"]) for match in ownership_matches
            }),
        }
        captured.append(entry)
        if entry["stationary"] and position:
            material = dict(payload)
            material["lat"], material["lng"] = position
            material["__audit_target_id"] = stable_id
            stationary_material.append(material)

    ownership = []
    for row in ownership_rows:
        raw = dict(row)
        payload = loads_object(raw.get("target_json"))
        payload.setdefault("lat", raw.get("lat"))
        payload.setdefault("lng", raw.get("lng"))
        position = target_position(payload)
        stable_id = target_id(payload, str(raw.get("target_id") or ""))
        created = first_text(raw.get("created_at"), payload.get("captured_at"))
        ownership.append({
            "target_id": stable_id,
            "kind": target_kind(payload),
            "lat": position[0] if position else None,
            "lng": position[1] if position else None,
            "ownership_version": int(raw.get("ownership_version") or 0),
            "ownership_source": first_text(
                payload.get("ownership_source"), payload.get("source"),
                payload.get("source_type"),
            ) or "UNKNOWN",
            "canonical_owner": str(raw.get("owner_username") or ""),
            "created_at": created or None,
            "updated_at": first_text(raw.get("updated_at")) or None,
            "incident_relation": timestamp_classification(created, incident_at),
            "captured_projection_present": stable_id in captured_ids,
        })

    pillars = [item for item in ownership if item["kind"] == "pillar"]
    inners = [item for item in ownership if item["kind"] == "inner"]
    stationary = [item for item in captured if item["stationary"]]
    return {
        "counts": {
            "captured_targets": len(captured),
            "stationary_targets": len(stationary),
            "generated_targets": sum(1 for item in captured if item["generated"]),
            "canonical_pillars": len(pillars),
            "canonical_inners": len(inners),
            "ownership_entries": len(ownership),
        },
        "pillars": pillars,
        "inners": inners,
        "stationary_targets": stationary,
        "captured_targets": captured,
        "ownership_entries": ownership,
        "stationary_material": stationary_material,
    }


def load_world_areas(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    columns = table_columns(conn, "player_areas")
    select = [
        name for name in (
            "id", "owner_username", "vertices_json", "area_size", "status",
            "created_at", "updated_at",
        ) if name in columns
    ]
    rows = conn.execute(
        f"SELECT {','.join(select)} FROM player_areas WHERE status='active' "
        "ORDER BY owner_username,id"
    ).fetchall()
    return [
        {
            **{key: row[key] for key in row.keys() if key != "vertices_json"},
            "vertices": loads_list(row["vertices_json"]),
            "geometry_sha256": digest(loads_list(row["vertices_json"])),
        }
        for row in rows
    ]


def bbox(vertices: list[dict[str, Any]]) -> dict[str, float] | None:
    points = [target_position(vertex) for vertex in vertices]
    points = [point for point in points if point]
    if not points:
        return None
    return {
        "min_lat": min(point[0] for point in points),
        "max_lat": max(point[0] for point in points),
        "min_lng": min(point[1] for point in points),
        "max_lng": max(point[1] for point in points),
    }


def bbox_overlap_ratio(first: dict[str, float] | None, second: dict[str, float] | None) -> float:
    if not first or not second:
        return 0.0
    lat_span = max(0.0, min(first["max_lat"], second["max_lat"]) - max(first["min_lat"], second["min_lat"]))
    lng_span = max(0.0, min(first["max_lng"], second["max_lng"]) - max(first["min_lng"], second["min_lng"]))
    overlap = lat_span * lng_span
    subject = max(
        (first["max_lat"] - first["min_lat"]) * (first["max_lng"] - first["min_lng"]),
        1e-18,
    )
    return round(min(1.0, overlap / subject), 6)


def point_on_boundary(point: dict[str, Any], vertices: list[dict[str, Any]]) -> bool:
    position = target_position(point)
    if not position or len(vertices or []) < 2:
        return False
    py, px = position
    for index, start in enumerate(vertices):
        end = vertices[(index + 1) % len(vertices)]
        a = target_position(start)
        b = target_position(end)
        if not a or not b:
            continue
        ay, ax = a
        by, bx = b
        cross = (px - ax) * (by - ay) - (py - ay) * (bx - ax)
        if abs(cross) > 1e-10:
            continue
        if min(ax, bx) - 1e-10 <= px <= max(ax, bx) + 1e-10 and min(ay, by) - 1e-10 <= py <= max(ay, by) + 1e-10:
            return True
    return False


def supporting_target_ids(
    area: dict[str, Any], targets: list[dict[str, Any]]
) -> list[str]:
    vertices = area.get("vertices") or []
    result = []
    for target in targets:
        position = target_position(target)
        if not position:
            continue
        if point_in_polygon(position[0], position[1], vertices) or point_on_boundary(target, vertices):
            result.append(str(target.get("__audit_target_id") or target_id(target)))
    return sorted(set(result))


def intersection_character(subject: list[dict[str, Any]], foreign: list[dict[str, Any]]) -> list[str]:
    character = []
    if any(
        point_in_polygon(float(vertex["lat"]), float(vertex.get("lng", vertex.get("lon"))), foreign)
        for vertex in subject
    ):
        character.append("subject_vertex_inside_foreign")
    if any(
        point_in_polygon(float(vertex["lat"]), float(vertex.get("lng", vertex.get("lon"))), subject)
        for vertex in foreign
    ):
        character.append("foreign_vertex_inside_subject")
    if not character:
        character.append("boundary_crossing_or_touch")
    return character


def historical_area_state(
    historical_index: dict[tuple[str, str], dict[str, Any]],
    foreign: dict[str, Any],
    incident_at: str,
) -> str:
    if historical_index:
        key = (
            str(foreign.get("owner_username") or ""),
            str(foreign.get("id") or ""),
        )
        previous = historical_index.get(key)
        if not previous:
            return "ABSENT_IN_HISTORICAL_SNAPSHOT"
        if previous["geometry_sha256"] == foreign["geometry_sha256"]:
            return "EXISTED_UNCHANGED_IN_HISTORICAL_SNAPSHOT"
        return "EXISTED_BUT_GEOMETRY_CHANGED"
    created_at = str(foreign.get("created_at") or "").strip()
    if created_at and created_at > incident_at:
        return "CREATED_AFTER_INCIDENT_CUTOFF"
    return "UNKNOWN — historical state unavailable"


def geometry_for_level(
    level: int,
    targets: list[dict[str, Any]],
    world_areas: list[dict[str, Any]],
    historical_index: dict[tuple[str, str], dict[str, Any]],
    incident_at: str,
) -> dict[str, Any]:
    max_edge = BASE_AREA_EDGE_METERS * max(1, int(level))
    components = connected_target_groups(targets, max_edge)
    areas = build_player_areas(targets, level)
    area_reports = []
    for index, area in enumerate(areas):
        vertices = area.get("vertices") or []
        simulated_id = f"sim_trolu2_l{level}_{digest(vertices)[:16]}"
        collisions = []
        for foreign in world_areas:
            if str(foreign.get("owner_username") or "") == CANONICAL_USERNAME:
                continue
            foreign_vertices = foreign.get("vertices") or []
            if not polygons_intersect(vertices, foreign_vertices):
                continue
            historical_state = historical_area_state(
                historical_index, foreign, incident_at
            )
            collisions.append({
                "foreign_owner": foreign.get("owner_username"),
                "foreign_area_id": foreign.get("id"),
                "foreign_created_at": foreign.get("created_at"),
                "foreign_updated_at": foreign.get("updated_at"),
                "foreign_area_size_sqm": round(
                    float(foreign.get("area_size") or 0), 2
                ),
                "foreign_bbox": bbox(foreign_vertices),
                "intersection_character": intersection_character(vertices, foreign_vertices),
                "subject_bbox_overlap_ratio": bbox_overlap_ratio(bbox(vertices), bbox(foreign_vertices)),
                "historical_state": historical_state,
            })
        area_reports.append({
            "simulated_area_id": simulated_id,
            "source_target_ids": supporting_target_ids(area, targets),
            "area_size_sqm": round(float(area.get("area_size") or 0), 2),
            "bbox": bbox(vertices),
            "closed_territory": len(vertices) >= 3 and float(area.get("area_size") or 0) > 0,
            "collision_count": len(collisions),
            "collisions": collisions,
        })
    component_reports = []
    for index, component in enumerate(components):
        ids = sorted(str(item.get("__audit_target_id") or target_id(item)) for item in component)
        component_reports.append({
            "component_id": f"component_l{level}_{index + 1}",
            "target_ids": ids,
            "target_count": len(ids),
            "can_form_closed_territory": len(ids) >= 3,
        })
    return {
        "level": level,
        "max_edge_distance_m": max_edge,
        "stationary_target_count": len(targets),
        "connected_components": component_reports,
        "active_area_count": len(area_reports),
        "closed_territory": bool(area_reports),
        "total_area_sqm": round(sum(item["area_size_sqm"] for item in area_reports), 2),
        "collision_count": sum(item["collision_count"] for item in area_reports),
        "areas": area_reports,
    }


def load_plan_targets(path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not path:
        return {}, []
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    targets = []
    for city in (plan.get("territory_recovery") or {}).get("cities", []):
        for target in city.get("targets") or []:
            item = dict(target)
            item["__audit_target_id"] = target_id(item)
            targets.append(item)
    return plan, targets


def classify_collision(collision: dict[str, Any], level: int) -> str:
    historical = str(collision.get("historical_state") or "")
    scaling = level > 2
    evolution = historical in {
        "ABSENT_IN_HISTORICAL_SNAPSHOT", "EXISTED_BUT_GEOMETRY_CHANGED",
        "CREATED_AFTER_INCIDENT_CUTOFF",
    }
    if scaling and evolution:
        return "A+B — BOTH"
    if evolution:
        return "A — CURRENT WORLD EVOLUTION"
    if scaling:
        return "B — LEVEL-DEPENDENT GEOMETRY EXPANSION"
    return "UNKNOWN"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    conn = readonly_connection(args.db)
    try:
        required = {
            "captured_targets", "territory_target_ownership", "player_areas",
        }
        missing = sorted(required - table_names(conn))
        if missing:
            raise RuntimeError("Missing required tables: " + ", ".join(missing))
        objects = load_subject_objects(conn, args.incident_at)
        world_areas = load_world_areas(conn)
        db_file = Path(args.db).resolve()
        query_only = bool(conn.execute("PRAGMA query_only").fetchone()[0])
    finally:
        conn.close()

    historical_index: dict[tuple[str, str], dict[str, Any]] = {}
    historical_database = None
    if args.historical_db:
        historical_conn = readonly_connection(args.historical_db)
        try:
            historical_areas = load_world_areas(historical_conn)
            historical_database = {
                "path": str(Path(args.historical_db).resolve()),
                "active_area_count": len(historical_areas),
            }
            historical_index = {
                (str(area.get("owner_username") or ""), str(area.get("id") or "")): area
                for area in historical_areas
            }
        finally:
            historical_conn.close()

    stationary = objects.pop("stationary_material")
    geometry = [
        geometry_for_level(
            level, stationary, world_areas, historical_index, args.incident_at
        )
        for level in LEVELS
    ]
    plan, bonus_targets = load_plan_targets(args.plan)
    bonus = None
    if bonus_targets:
        bonus_only = geometry_for_level(
            50, bonus_targets, world_areas, historical_index, args.incident_at
        )
        combined = geometry_for_level(
            50,
            stationary + bonus_targets,
            world_areas,
            historical_index,
            args.incident_at,
        )
        bonus = {
            "plan_id": plan.get("plan_id"),
            "cities": [
                {
                    "city": city.get("city"),
                    "relocation": city.get("relocation"),
                    "pillar_count": len(city.get("targets") or []),
                }
                for city in (plan.get("territory_recovery") or {}).get("cities", [])
            ],
            "bonus_only_level_50": bonus_only,
            "combined_existing_plus_bonus_level_50": combined,
        }

    level2 = next(item for item in geometry if item["level"] == 2)
    level50 = next(item for item in geometry if item["level"] == 50)
    markers_survived = objects["counts"]["stationary_targets"] > 0
    level_scaling_reactivates = (
        level50["active_area_count"] > level2["active_area_count"]
        or level50["total_area_sqm"] > level2["total_area_sqm"]
    )
    conflicts = []
    for level_report in geometry:
        for area in level_report["areas"]:
            for collision in area["collisions"]:
                conflicts.append({
                    "level": level_report["level"],
                    "simulated_area_id": area["simulated_area_id"],
                    "source_target_ids": area["source_target_ids"],
                    "subject_bbox": area["bbox"],
                    **collision,
                    "classification": classify_collision(collision, level_report["level"]),
                })
    classifications = {item["classification"] for item in conflicts}
    if "A+B — BOTH" in classifications:
        verdict = (
            "DIAGNOSIS CONFIRMED — BOTH LEVEL SCALING AND WORLD EVOLUTION "
            "CONTRIBUTE"
        )
    elif classifications == {"A — CURRENT WORLD EVOLUTION"}:
        verdict = (
            "DIAGNOSIS CONFIRMED — CURRENT WORLD EVOLUTION IS PRIMARY "
            "COLLISION SOURCE"
        )
    elif markers_survived and level_scaling_reactivates:
        verdict = "DIAGNOSIS CONFIRMED — OLD MARKERS SURVIVED AND LEVEL SCALING REACTIVATES TERRITORY"
    else:
        verdict = "DIAGNOSIS INCONCLUSIVE"
    return {
        "ok": True,
        "command": "geometry-audit",
        "read_only": True,
        "query_only": query_only,
        "database": {"path": str(db_file), "size_bytes": db_file.stat().st_size},
        "historical_database": historical_database,
        "canonical_username": CANONICAL_USERNAME,
        "incident_cutoff": args.incident_at,
        "subject_objects": objects,
        "geometry_by_level": geometry,
        "existing_geometry_collisions": conflicts,
        "tokio_bonus_diagnosis": bonus,
        "hypotheses": {
            "markers_survived": markers_survived,
            "level_scaling_reactivates_or_expands_geometry": level_scaling_reactivates,
            "current_world_evolution": (
                "ASSESSED_AGAINST_HISTORICAL_SNAPSHOT"
                if historical_index else "UNKNOWN — historical state unavailable"
            ),
        },
        "verdict": verdict,
        "database_writes": 0,
        "ghostnetwork_queries": 0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/game.sqlite3")
    parser.add_argument("--plan", default="")
    parser.add_argument("--historical-db", default="")
    parser.add_argument("--incident-at", default=DEFAULT_INCIDENT_AT)
    parser.add_argument("--output", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(args)
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
