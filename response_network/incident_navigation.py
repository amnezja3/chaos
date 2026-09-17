"""Deterministic navigation outside the current incident search area."""
import hashlib
import math


def safe_incident_entry_point(public_incident):
    incident = public_incident if isinstance(public_incident, dict) else {}
    center = incident.get("center") if isinstance(incident.get("center"), dict) else {}
    try:
        lat = float(center.get("lat"))
        lng = float(center.get("lng"))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(lat) or not math.isfinite(lng):
        return None

    radius_m = max(0, int(incident.get("search_radius_m") or 0))
    distance_m = max(220.0, float(radius_m) + 160.0, float(radius_m) * 1.35)
    seed = str(incident.get("incident_id") or "incident")
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()
    bearing = (int(digest[:8], 16) % 360) * math.pi / 180.0

    meters_per_degree_lat = 111_320.0
    cos_lat = max(0.2, abs(math.cos(math.radians(lat))))
    entry_lat = lat + (math.cos(bearing) * distance_m / meters_per_degree_lat)
    entry_lng = lng + (math.sin(bearing) * distance_m / (meters_per_degree_lat * cos_lat))
    entry_lat = max(-89.999, min(89.999, entry_lat))
    entry_lng = ((entry_lng + 180.0) % 360.0) - 180.0
    return {
        "lat": round(entry_lat, 6),
        "lng": round(entry_lng, 6),
        "center_lat": round(lat, 6),
        "center_lng": round(lng, 6),
        "distance_m": int(round(distance_m)),
        "label": f"{entry_lat:.5f}, {entry_lng:.5f}",
        "center_label": f"{lat:.5f}, {lng:.5f}",
    }


