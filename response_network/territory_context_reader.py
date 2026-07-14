from __future__ import annotations

from database import TerritoryConflictStore, TerritoryStore


def _clean_text(value, default=""):
    text = str(value or "").strip()
    return text or default


def _coerce_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_vertices(vertices):
    result = []
    for vertex in vertices or []:
        if isinstance(vertex, dict):
            lat = _coerce_float(vertex.get("lat"))
            lng = _coerce_float(vertex.get("lng", vertex.get("lon")))
        elif isinstance(vertex, (list, tuple)) and len(vertex) >= 2:
            lat = _coerce_float(vertex[0])
            lng = _coerce_float(vertex[1])
        else:
            continue
        if lat is None or lng is None:
            continue
        result.append({"lat": lat, "lng": lng})
    return result


def _bbox_for_vertices(vertices):
    vertices = _normalize_vertices(vertices)
    if not vertices:
        return None
    lats = [vertex["lat"] for vertex in vertices]
    lngs = [vertex["lng"] for vertex in vertices]
    return {
        "min_lat": min(lats),
        "min_lng": min(lngs),
        "max_lat": max(lats),
        "max_lng": max(lngs),
    }


def _bbox_intersects(left, right):
    if not left or not right:
        return False
    return not (
        left["max_lat"] < right["min_lat"]
        or left["min_lat"] > right["max_lat"]
        or left["max_lng"] < right["min_lng"]
        or left["min_lng"] > right["max_lng"]
    )


class TerritoryContextReader:
    """Read-only territory context for Response Network.

    It intentionally reads existing territory snapshots and active conflicts only.
    It does not rebuild geometry, load full user profiles or change gameplay state.
    """

    def __init__(self, territory_store=None, conflict_store=None):
        self.territory_store = territory_store or TerritoryStore()
        self.conflict_store = conflict_store or TerritoryConflictStore()

    @staticmethod
    def _query_bbox(min_lat, min_lng, max_lat, max_lng):
        values = {
            "min_lat": _coerce_float(min_lat),
            "min_lng": _coerce_float(min_lng),
            "max_lat": _coerce_float(max_lat),
            "max_lng": _coerce_float(max_lng),
        }
        if any(value is None for value in values.values()):
            raise ValueError("Territory bbox query requires numeric bounds.")
        if values["min_lat"] > values["max_lat"]:
            values["min_lat"], values["max_lat"] = values["max_lat"], values["min_lat"]
        if values["min_lng"] > values["max_lng"]:
            values["min_lng"], values["max_lng"] = values["max_lng"], values["min_lng"]
        return values

    @staticmethod
    def _area_bbox(area):
        return _bbox_for_vertices((area or {}).get("vertices") or [])

    @staticmethod
    def _context_id(area):
        area_id = area.get("id")
        if area_id not in (None, ""):
            return f"territory_area:{area_id}"
        owner = _clean_text(area.get("owner_username"), "unknown")
        bbox = TerritoryContextReader._area_bbox(area) or {}
        return "territory_area:{owner}:{min_lat}:{min_lng}:{max_lat}:{max_lng}".format(
            owner=owner,
            min_lat=round(float(bbox.get("min_lat", 0)), 5),
            min_lng=round(float(bbox.get("min_lng", 0)), 5),
            max_lat=round(float(bbox.get("max_lat", 0)), 5),
            max_lng=round(float(bbox.get("max_lng", 0)), 5),
        )

    @staticmethod
    def _version(area):
        return _clean_text(area.get("updated_at") or area.get("created_at") or area.get("id"), "0")

    def _conflicts_by_area_id(self):
        conflicts_by_area_id = {}
        for conflict in self.conflict_store.list_active() or []:
            for area_id in conflict.get("area_ids") or []:
                conflicts_by_area_id.setdefault(str(area_id), []).append({
                    "conflict_id": conflict.get("id"),
                    "conflict_key": conflict.get("conflict_key"),
                    "participants": conflict.get("participant_usernames") or conflict.get("participants") or [],
                    "status": conflict.get("status") or "active",
                    "updated_at": conflict.get("updated_at"),
                })
        return conflicts_by_area_id

    def _area_context(self, area, conflicts_by_area_id):
        vertices = _normalize_vertices(area.get("vertices") or [])
        bbox = _bbox_for_vertices(vertices)
        area_id = area.get("id")
        conflicts = conflicts_by_area_id.get(str(area_id), []) if area_id not in (None, "") else []
        owner = _clean_text(area.get("owner_username"), "unknown")
        clan = _clean_text(area.get("owner_clan") or area.get("clan_id"))
        status = _clean_text(area.get("status"), "active")
        return {
            "territory_id": self._context_id(area),
            "area_id": area_id,
            "owner_id": owner,
            "owner_username": owner,
            "clan_id": clan or None,
            "clan_source": "area_snapshot" if clan else "not_available_without_profile",
            "status": status,
            "conflict_id": conflicts[0]["conflict_id"] if conflicts else None,
            "conflict_ids": [item["conflict_id"] for item in conflicts if item.get("conflict_id") is not None],
            "conflicts": conflicts,
            "bbox": bbox,
            "centroid": {
                "lat": _coerce_float(area.get("centroid_lat")),
                "lng": _coerce_float(area.get("centroid_lng")),
            },
            "area_size": _coerce_float(area.get("area_size")) or 0,
            "version": self._version(area),
            "vertices_count": len(vertices),
        }

    def _active_areas(self, include_inactive=False):
        areas = []
        for area in self.territory_store.list_player_areas() or []:
            status = _clean_text(area.get("status"), "active")
            if not include_inactive and status not in {"active", "encircled"}:
                continue
            vertices = _normalize_vertices(area.get("vertices") or [])
            if len(vertices) < 3:
                continue
            normalized = dict(area)
            normalized["vertices"] = vertices
            normalized["status"] = status
            areas.append(normalized)
        return areas

    def for_point(self, lat, lng, actor_username=None, include_inactive=False):
        lat = _coerce_float(lat)
        lng = _coerce_float(lng)
        if lat is None or lng is None:
            raise ValueError("Territory point query requires numeric lat/lng.")

        actor_username = _clean_text(actor_username)
        conflicts_by_area_id = self._conflicts_by_area_id()
        territories = []
        for area in self._active_areas(include_inactive=include_inactive):
            bbox = self._area_bbox(area)
            if bbox and not (bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lng"] <= lng <= bbox["max_lng"]):
                continue
            if not TerritoryStore.point_in_polygon(lat, lng, area.get("vertices") or []):
                continue
            territories.append(self._area_context(area, conflicts_by_area_id))

        owner_ids = sorted({item["owner_id"] for item in territories if item.get("owner_id")})
        return {
            "query": {
                "type": "point",
                "lat": lat,
                "lng": lng,
                "actor_username": actor_username or None,
            },
            "territories": territories,
            "inside_any_territory": bool(territories),
            "inside_own_territory": bool(actor_username and any(item["owner_id"] == actor_username for item in territories)),
            "inside_foreign_territory": bool(actor_username and any(item["owner_id"] != actor_username for item in territories)),
            "owner_ids": owner_ids,
        }

    def for_bbox(self, min_lat, min_lng, max_lat, max_lng, actor_username=None, include_inactive=False, limit=50):
        query_bbox = self._query_bbox(min_lat, min_lng, max_lat, max_lng)
        try:
            limit = max(1, min(int(limit or 50), 200))
        except (TypeError, ValueError):
            limit = 50

        conflicts_by_area_id = self._conflicts_by_area_id()
        territories = []
        for area in self._active_areas(include_inactive=include_inactive):
            if not _bbox_intersects(self._area_bbox(area), query_bbox):
                continue
            territories.append(self._area_context(area, conflicts_by_area_id))
            if len(territories) >= limit:
                break

        return {
            "query": {
                "type": "bbox",
                **query_bbox,
                "actor_username": _clean_text(actor_username) or None,
                "limit": limit,
            },
            "territories": territories,
            "truncated": len(territories) >= limit,
            "owner_ids": sorted({item["owner_id"] for item in territories if item.get("owner_id")}),
        }

    def compare_point_with_legacy_area(self, lat, lng, legacy_area, actor_username=None):
        context = self.for_point(lat, lng, actor_username=actor_username)
        legacy_id = None
        if isinstance(legacy_area, dict) and legacy_area:
            legacy_id = self._context_id(legacy_area)
        context_ids = {item.get("territory_id") for item in context.get("territories") or []}
        return {
            "match": bool(legacy_id and legacy_id in context_ids) or (legacy_id is None and not context_ids),
            "legacy_territory_id": legacy_id,
            "context_territory_ids": sorted(context_ids),
            "context": context,
        }
