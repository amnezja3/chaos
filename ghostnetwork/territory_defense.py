from __future__ import annotations

import math


MAX_TERRITORY_DEFENSE_SWARM = 8


def _point(marker):
    try:
        lat = float(marker.get("lat"))
        lng = float(marker.get("lng", marker.get("lon")))
    except (AttributeError, TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return lng, lat


def _same_marker(left, right):
    left_point = _point(left)
    right_point = _point(right)
    return bool(
        left_point and right_point
        and round(left_point[0], 5) == round(right_point[0], 5)
        and round(left_point[1], 5) == round(right_point[1], 5)
    )


def _dedupe_markers(markers):
    unique = {}
    for marker in markers or []:
        if not isinstance(marker, dict):
            continue
        point = _point(marker)
        if point is None:
            continue
        key = (round(point[0], 6), round(point[1], 6))
        previous = unique.get(key)
        if previous is None or (
            previous.get("generated") and not marker.get("generated")
        ):
            unique[key] = dict(marker)
    return list(unique.values())


def _cross(origin, left, right):
    ox, oy = _point(origin)
    lx, ly = _point(left)
    rx, ry = _point(right)
    return (lx - ox) * (ry - oy) - (ly - oy) * (rx - ox)


def _convex_hull(markers):
    ordered = sorted(markers, key=lambda item: _point(item))
    if len(ordered) <= 1:
        return ordered
    lower = []
    for marker in ordered:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], marker) <= 0:
            lower.pop()
        lower.append(marker)
    upper = []
    for marker in reversed(ordered):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], marker) <= 0:
            upper.pop()
        upper.append(marker)
    return lower[:-1] + upper[:-1]


def _triangle_area(previous, current, following):
    return abs(_cross(previous, current, following))


def _simplify_hull(hull, limit):
    selected = list(hull)
    while len(selected) > max(1, int(limit)):
        remove_index = min(
            range(len(selected)),
            key=lambda index: (
                _triangle_area(
                    selected[index - 1],
                    selected[index],
                    selected[(index + 1) % len(selected)],
                ),
                index,
            ),
        )
        selected.pop(remove_index)
    return selected


def select_territory_defense_swarm(markers, anchor, limit=MAX_TERRITORY_DEFENSE_SWARM):
    """Select a bounded outline of one trusted scan and always retain the anchor."""
    limit = max(1, min(MAX_TERRITORY_DEFENSE_SWARM, int(limit or 1)))
    candidates = _dedupe_markers(markers)
    anchor_candidate = next(
        (candidate for candidate in candidates if _same_marker(candidate, anchor)),
        None,
    )
    if anchor_candidate is None:
        return []
    if len(candidates) <= 3:
        return candidates

    hull = _convex_hull(candidates)
    anchor_on_hull = any(_same_marker(candidate, anchor_candidate) for candidate in hull)
    selected = _simplify_hull(hull, limit if anchor_on_hull else max(1, limit - 1))
    if not any(_same_marker(candidate, anchor_candidate) for candidate in selected):
        selected.insert(0, anchor_candidate)
    return selected[:limit]


def territory_defense_swarm_span_m(markers):
    """Return a diagnostic-only maximum span without exposing marker payloads."""
    points = [_point(marker) for marker in markers or []]
    points = [point for point in points if point is not None]
    maximum = 0.0
    for index, (lng_a, lat_a) in enumerate(points):
        for lng_b, lat_b in points[index + 1:]:
            mean_lat = math.radians((lat_a + lat_b) / 2)
            dx = (lng_b - lng_a) * 111_320 * math.cos(mean_lat)
            dy = (lat_b - lat_a) * 110_540
            maximum = max(maximum, math.hypot(dx, dy))
    return round(maximum)
