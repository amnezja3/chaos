"""Pure canonical territory geometry used by runtime and recovery tooling.

This module deliberately has no database or Flask imports.  A recovery plan
must preview the same connected-cluster and hull contract that the territory
worker will later publish.
"""

from __future__ import annotations

import math
from itertools import combinations


EARTH_RADIUS_METERS = 6_371_000.0
BASE_AREA_EDGE_METERS = 300
MIN_TRIANGLE_AREA_SQM = 1
MAX_EXACT_AREA_TARGETS = 32
MAX_EXACT_AREA_TRIANGLES = 1200


def distance_meters(a, b):
    lat1 = math.radians(float(a["lat"]))
    lon1 = math.radians(float(a.get("lng", a.get("lon"))))
    lat2 = math.radians(float(b["lat"]))
    lon2 = math.radians(float(b.get("lng", b.get("lon"))))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return EARTH_RADIUS_METERS * 2 * math.atan2(
        math.sqrt(value), math.sqrt(max(0.0, 1 - value))
    )


def polygon_area_sqm(vertices):
    if len(vertices or []) < 3:
        return 0
    center_lat = math.radians(
        sum(float(vertex["lat"]) for vertex in vertices) / len(vertices)
    )
    origin_lat = float(vertices[0]["lat"])
    origin_lng = float(vertices[0].get("lng", vertices[0].get("lon")))
    points = []
    for vertex in vertices:
        lng = float(vertex.get("lng", vertex.get("lon")))
        x = math.radians(lng - origin_lng) * EARTH_RADIUS_METERS * math.cos(center_lat)
        y = math.radians(float(vertex["lat"]) - origin_lat) * EARTH_RADIUS_METERS
        points.append((x, y))
    area = 0.0
    for index, point in enumerate(points):
        following = points[(index + 1) % len(points)]
        area += point[0] * following[1] - following[0] * point[1]
    return abs(area) / 2


def convex_hull(targets):
    unique = {}
    for target in targets or []:
        key = (
            round(float(target.get("lng", target.get("lon"))), 7),
            round(float(target.get("lat")), 7),
        )
        unique[key] = target
    points = sorted(unique.items())
    if len(points) <= 1:
        return [target for _, target in points]

    def cross(origin, left, right):
        return (
            (left[0][0] - origin[0][0]) * (right[0][1] - origin[0][1])
            - (left[0][1] - origin[0][1]) * (right[0][0] - origin[0][0])
        )

    lower = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return [target for _, target in lower[:-1] + upper[:-1]]


def connected_target_groups(targets, max_edge_distance):
    targets = list(targets or [])
    unvisited = set(range(len(targets)))
    groups = []
    while unvisited:
        start = unvisited.pop()
        stack = [start]
        group_indexes = {start}
        while stack:
            current = stack.pop()
            linked = [
                other
                for other in list(unvisited)
                if distance_meters(targets[current], targets[other]) <= max_edge_distance
            ]
            for other in linked:
                unvisited.remove(other)
                group_indexes.add(other)
                stack.append(other)
        groups.append([targets[index] for index in sorted(group_indexes)])
    return groups


def area_vertex(target):
    lng = target.get("lng", target.get("lon"))
    return {
        "lat": float(target.get("lat")),
        "lng": float(lng),
        "label": target.get("label", ""),
        "name": target.get("name") or target.get("label", ""),
        "icon": target.get("icon", ""),
        "source_type": target.get("source_type", ""),
        "captured_at": target.get("captured_at", ""),
    }


def area_from_hull(targets, minimum_area_sqm=MIN_TRIANGLE_AREA_SQM):
    hull = convex_hull(targets)
    if len(hull) < 3:
        return None
    vertices = [area_vertex(target) for target in hull]
    area_size = polygon_area_sqm(vertices)
    if area_size < minimum_area_sqm:
        return None
    hull_edges = [
        distance_meters(vertices[index], vertices[(index + 1) % len(vertices)])
        for index in range(len(vertices))
    ]
    return {
        "vertices": vertices,
        "centroid_lat": sum(vertex["lat"] for vertex in vertices) / len(vertices),
        "centroid_lng": sum(vertex["lng"] for vertex in vertices) / len(vertices),
        "area_size": area_size,
        "max_edge_distance": max(hull_edges) if hull_edges else 0,
        "status": "active",
    }


def build_player_areas(
    targets,
    player_level=1,
    *,
    base_area_edge_meters=BASE_AREA_EDGE_METERS,
    minimum_area_sqm=MIN_TRIANGLE_AREA_SQM,
    max_exact_area_targets=MAX_EXACT_AREA_TARGETS,
    max_exact_area_triangles=MAX_EXACT_AREA_TRIANGLES,
    on_approximation=None,
):
    """Return the exact area material produced by ``TerritoryStore``."""
    try:
        level = max(1, int(player_level))
    except (TypeError, ValueError):
        level = 1
    max_edge_distance = float(base_area_edge_meters) * level
    normalized_targets = [
        target
        for target in (targets or [])
        if target.get("lat") is not None
        and target.get("lng", target.get("lon")) is not None
    ]
    areas = []
    for group in connected_target_groups(normalized_targets, max_edge_distance):
        if len(group) < 3:
            continue
        if len(group) > int(max_exact_area_targets):
            area = area_from_hull(group, minimum_area_sqm)
            if area:
                if callable(on_approximation):
                    on_approximation(
                        "large_cluster", len(group), int(max_exact_area_targets)
                    )
                areas.append(area)
            continue

        valid_triangles = []
        exact_limit_exceeded = False
        for combo_indexes in combinations(range(len(group)), 3):
            combo = [group[index] for index in combo_indexes]
            vertices = [area_vertex(target) for target in combo]
            edges = [
                distance_meters(vertices[index], vertices[(index + 1) % len(vertices)])
                for index in range(len(vertices))
            ]
            if max(edges) > max_edge_distance:
                continue
            if polygon_area_sqm(vertices) < minimum_area_sqm:
                continue
            valid_triangles.append(set(combo_indexes))
            if len(valid_triangles) > int(max_exact_area_triangles):
                exact_limit_exceeded = True
                break
        if exact_limit_exceeded:
            area = area_from_hull(group, minimum_area_sqm)
            if area:
                if callable(on_approximation):
                    on_approximation(
                        "dense_cluster", len(group), int(max_exact_area_triangles)
                    )
                areas.append(area)
            continue

        unvisited = set(range(len(valid_triangles)))
        while unvisited:
            triangle_index = unvisited.pop()
            stack = [triangle_index]
            cluster_indexes = set(valid_triangles[triangle_index])
            while stack:
                current = stack.pop()
                linked = [
                    other
                    for other in list(unvisited)
                    if valid_triangles[current] & valid_triangles[other]
                ]
                for other in linked:
                    unvisited.remove(other)
                    cluster_indexes.update(valid_triangles[other])
                    stack.append(other)
            area = area_from_hull(
                [group[index] for index in sorted(cluster_indexes)],
                minimum_area_sqm,
            )
            if area:
                areas.append(area)
    areas.sort(key=lambda area: (area["area_size"], area["max_edge_distance"]))
    return areas


def point_in_polygon(lat, lng, vertices):
    if len(vertices or []) < 3:
        return False
    inside = False
    previous = len(vertices) - 1
    for index, vertex in enumerate(vertices):
        yi = float(vertex.get("lat"))
        xi = float(vertex.get("lng", vertex.get("lon")))
        yj = float(vertices[previous].get("lat"))
        xj = float(vertices[previous].get("lng", vertices[previous].get("lon")))
        crosses = (xi > lng) != (xj > lng)
        if crosses:
            crossing = (yj - yi) * (lng - xi) / ((xj - xi) or 1e-12) + yi
            if lat < crossing:
                inside = not inside
        previous = index
    return inside


def _orientation(a, b, c):
    value = (
        (float(b["lng"]) - float(a["lng"])) * (float(c["lat"]) - float(a["lat"]))
        - (float(b["lat"]) - float(a["lat"])) * (float(c["lng"]) - float(a["lng"]))
    )
    if abs(value) < 1e-12:
        return 0
    return 1 if value > 0 else -1


def _point_on_segment(a, b, c):
    return (
        min(float(a["lng"]), float(b["lng"])) - 1e-12
        <= float(c["lng"])
        <= max(float(a["lng"]), float(b["lng"])) + 1e-12
        and min(float(a["lat"]), float(b["lat"])) - 1e-12
        <= float(c["lat"])
        <= max(float(a["lat"]), float(b["lat"])) + 1e-12
    )


def _segments_intersect(a, b, c, d):
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    return bool(
        (o1 == 0 and _point_on_segment(a, b, c))
        or (o2 == 0 and _point_on_segment(a, b, d))
        or (o3 == 0 and _point_on_segment(c, d, a))
        or (o4 == 0 and _point_on_segment(c, d, b))
    )


def polygons_intersect(first, second):
    if len(first or []) < 3 or len(second or []) < 3:
        return False
    if any(point_in_polygon(float(v["lat"]), float(v["lng"]), second) for v in first):
        return True
    if any(point_in_polygon(float(v["lat"]), float(v["lng"]), first) for v in second):
        return True
    for index, start in enumerate(first):
        end = first[(index + 1) % len(first)]
        for other_index, other_start in enumerate(second):
            other_end = second[(other_index + 1) % len(second)]
            if _segments_intersect(start, end, other_start, other_end):
                return True
    return False
