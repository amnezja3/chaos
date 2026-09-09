from __future__ import annotations

import copy

from territory_geometry import point_in_polygon, polygons_intersect


ROLE_PRIORITY = {"allied_overlap": 1, "conflict": 2, "primary": 3}


def _clean(value):
    return str(value or "").strip()


def _territory_id(value):
    return _clean(value)


def _valid_vertices(value):
    result = []
    for item in value or []:
        if not isinstance(item, dict):
            continue
        try:
            result.append({"lat": float(item.get("lat")), "lng": float(item.get("lng", item.get("lon")))})
        except (TypeError, ValueError):
            continue
    return result if len(result) >= 3 else []


def _positive_overlap(left, right):
    """Reject a boundary-only touch while accepting ordinary polygon overlap."""
    left = _valid_vertices(left)
    right = _valid_vertices(right)
    if not left or not right or not polygons_intersect(left, right):
        return False
    if any(point_in_polygon(item["lat"], item["lng"], right) for item in left):
        return True
    if any(point_in_polygon(item["lat"], item["lng"], left) for item in right):
        return True
    # Convex territory hulls can cross with every vertex outside the opposite
    # polygon. In that case the intersection is still positive unless all
    # coordinates only meet on a shared boundary. A tiny centroid probe keeps
    # this deterministic without adding a geometry dependency.
    for polygon, other in ((left, right), (right, left)):
        center = {
            "lat": sum(item["lat"] for item in polygon) / len(polygon),
            "lng": sum(item["lng"] for item in polygon) / len(polygon),
        }
        if point_in_polygon(center["lat"], center["lng"], other):
            return True
    return False


def build_territory_consumption_plan(parts, conflicts, territories, production_conflicts=None):
    """Build a bounded, immutable one-hop territory plan.

    The caller supplies narrow territory and identity projections. The planner
    is pure: it never reads profiles or mutates the world.
    """
    parts = [item for item in (parts or []) if isinstance(item, dict)]
    conflicts = [item for item in (conflicts or []) if isinstance(item, dict)]
    territories = [item for item in (territories or []) if isinstance(item, dict)]
    production_conflicts = [
        item for item in (production_conflicts or []) if isinstance(item, dict)
    ]
    by_id = {_territory_id(item.get("territory_id") or item.get("id")): item for item in territories}
    selected = {}
    warnings = []

    def include(territory_id, role, reason, source_conflict_id="", fallback=None):
        territory_id = _territory_id(territory_id)
        territory = by_id.get(territory_id)
        if not territory:
            warnings.append({
                "reason": "territory_snapshot_missing",
                "territory_id": territory_id,
                "role": role,
                "source_conflict_id": _clean(source_conflict_id),
                # A primary territory is part of the live 20/20 authority and
                # must exist at lock time. A resolved conflict participant may
                # already have disappeared during canonical conflict rebuild;
                # it remains auditable, but there is no live area to consume.
                "blocking": role == "primary",
            })
            return
        current = selected.get(territory_id)
        if current and ROLE_PRIORITY[current["role"]] >= ROLE_PRIORITY[role]:
            return
        clan = _clean(territory.get("clan_code") or (fallback or {}).get("territory_clan"))
        selected[territory_id] = {
            "territory_id": territory_id,
            "owner_id": _clean(territory.get("owner_id") or territory.get("owner_username")),
            "clan_code": clan,
            "role": role,
            "reason": reason,
            "source_conflict_id": _clean(source_conflict_id),
            "area_size": float(territory.get("area_size") or 0),
            "publication_version": int(territory.get("publication_version") or 0),
            "vertices": _valid_vertices(territory.get("vertices")),
            "targets": copy.deepcopy(territory.get("targets") or []),
        }

    for part in parts:
        include(
            part.get("territory_id"), "primary", "ghostnetwork_part_territory",
            source_conflict_id=part.get("conflict_id"), fallback=part,
        )

    relevant_conflicts = [
        item for item in conflicts
        if _clean(item.get("status")).lower() in {"resolved", "closed"}
    ]
    for conflict in relevant_conflicts:
        include(
            conflict.get("territory_id"), "conflict", "resolved_conflict_participant",
            source_conflict_id=conflict.get("conflict_id"),
        )
    for conflict in production_conflicts:
        identity = _clean(conflict.get("conflict_id") or conflict.get("id"))
        if _clean(conflict.get("status")).lower() not in {"resolved", "closed"}:
            continue
        for territory_id in conflict.get("territory_ids") or []:
            include(
                territory_id, "conflict", "resolved_conflict_participant",
                source_conflict_id=identity,
            )

    direct = list(selected.values())
    for candidate in territories:
        candidate_id = _territory_id(candidate.get("territory_id") or candidate.get("id"))
        if not candidate_id or candidate_id in selected:
            continue
        candidate_clan = _clean(candidate.get("clan_code"))
        candidate_vertices = candidate.get("vertices") or []
        for base in direct:
            if not candidate_clan or candidate_clan != _clean(base.get("clan_code")):
                continue
            if _positive_overlap(candidate_vertices, base.get("vertices") or []):
                include(
                    candidate_id, "allied_overlap", "same_clan_direct_overlap",
                    source_conflict_id=base.get("source_conflict_id"),
                )
                break

    entries = sorted(
        selected.values(),
        key=lambda item: (-ROLE_PRIORITY[item["role"]], item["territory_id"]),
    )
    return {
        "schema": 1,
        "kind": "ghost_signal_territory_consumption_plan",
        "entries": entries,
        "warnings": warnings,
        "counts": {
            "total": len(entries),
            "primary": sum(item["role"] == "primary" for item in entries),
            "conflict": sum(item["role"] == "conflict" for item in entries),
            "allied_overlap": sum(item["role"] == "allied_overlap" for item in entries),
            "missing": len(warnings),
        },
    }
