from __future__ import annotations

import math

from .lifecycle import GhostPartLifecycleService


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _event_id(event):
    event = event if isinstance(event, dict) else {}
    return _clean(event.get("territory_event_id") or event.get("event_id") or event.get("id"))


def _normalise_vertices(source):
    source = source if isinstance(source, dict) else {}
    raw_vertices = source.get("vertices") or source.get("polygon") or []
    vertices = []
    for item in raw_vertices:
        if isinstance(item, dict):
            lat = _float(item.get("lat") or item.get("latitude"))
            lng = _float(item.get("lng") or item.get("lon") or item.get("longitude"))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            lat = _float(item[0])
            lng = _float(item[1])
        else:
            continue
        if lat is not None and lng is not None:
            vertices.append({"lat": lat, "lng": lng})
    return vertices


def _bounds_from_vertices(vertices):
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


def _normalise_bounds(source):
    source = source if isinstance(source, dict) else {}
    bounds = source.get("bounds") if isinstance(source.get("bounds"), dict) else source
    min_lat = _float(bounds.get("min_lat") or bounds.get("south"))
    min_lng = _float(bounds.get("min_lng") or bounds.get("west"))
    max_lat = _float(bounds.get("max_lat") or bounds.get("north"))
    max_lng = _float(bounds.get("max_lng") or bounds.get("east"))
    if None in {min_lat, min_lng, max_lat, max_lng}:
        return None
    return {
        "min_lat": min(min_lat, max_lat),
        "min_lng": min(min_lng, max_lng),
        "max_lat": max(min_lat, max_lat),
        "max_lng": max(min_lng, max_lng),
    }


def _contains_bounds(bounds, lat, lng):
    if not bounds:
        return False
    return (
        bounds["min_lat"] <= lat <= bounds["max_lat"]
        and bounds["min_lng"] <= lng <= bounds["max_lng"]
    )


def _point_in_polygon(lat, lng, vertices):
    inside = False
    if len(vertices) < 3:
        return False
    j = len(vertices) - 1
    for i, vertex in enumerate(vertices):
        yi = vertex["lat"]
        xi = vertex["lng"]
        yj = vertices[j]["lat"]
        xj = vertices[j]["lng"]
        crosses = (xi > lng) != (xj > lng)
        if crosses:
            slope_lat = (yj - yi) * (lng - xi) / ((xj - xi) or 1e-12) + yi
            if lat < slope_lat:
                inside = not inside
        j = i
    return inside


def _territory_context(event):
    event = event if isinstance(event, dict) else {}
    return {
        "territory_id": _clean(event.get("territory_id") or event.get("id")),
        "territory_owner_id": _clean(
            event.get("territory_owner_id")
            or event.get("owner_username")
            or event.get("owner_id")
            or event.get("owner")
        ),
        "territory_clan": _clean(event.get("territory_clan") or event.get("owner_clan") or event.get("clan")),
        "territory_state_version": int(event.get("territory_state_version") or event.get("state_version") or 0),
    }


def normalise_territory_event(event):
    if (
        isinstance(event, dict)
        and "raw" in event
        and "territory_id" in event
        and "territory_owner_id" in event
        and "territory_clan" in event
        and "bounds" in event
        and "vertices" in event
    ):
        return event
    event = event if isinstance(event, dict) else {}
    vertices = _normalise_vertices(event)
    bounds = _normalise_bounds(event) or _bounds_from_vertices(vertices)
    context = _territory_context(event)
    pillar_count = int(event.get("pillar_count") or event.get("pillars_count") or len(vertices) or 0)
    conflict_id = _clean(event.get("conflict_id"))
    status = _clean(event.get("status") or event.get("territory_status") or event.get("state"), "stable")
    return {
        **context,
        "event_id": _event_id(event),
        "previous_owner": _clean(event.get("previous_owner") or event.get("previous_owner_id")),
        "previous_clan": _clean(event.get("previous_clan")),
        "conflict_id": conflict_id,
        "status": status,
        "vertices": vertices,
        "bounds": bounds,
        "pillar_count": pillar_count,
        "has_polygon": bool(event.get("has_polygon", True) and len(vertices) >= 3),
        "created_at": _clean(event.get("created_at")),
        "raw": event,
    }


class GhostTerritoryAdapter:
    """Bridge between stable territory events and GhostNetwork part lifecycle.

    Territories remain the source of truth. This adapter only evaluates
    discovered GhostNetwork anchors against provided territory snapshots/events
    and applies lifecycle transitions to parts.
    """

    LIVE_STATUSES = {"public", "contained", "active"}

    def __init__(self, repository, lifecycle=None, territory_reader=None):
        self.repository = repository
        self.lifecycle = lifecycle or GhostPartLifecycleService(repository)
        self.territory_reader = territory_reader

    def is_stable_territory(self, event):
        event = normalise_territory_event(event)
        return bool(
            event["territory_id"]
            and event["territory_owner_id"]
            and event["territory_clan"]
            and event["status"] in {"stable", "active", "captured", "owned"}
            and event["pillar_count"] >= 3
            and event["has_polygon"]
            and event["bounds"]
            and not event["conflict_id"]
        )

    def resolve_part_territory(self, part, territories=None):
        part = part if isinstance(part, dict) else {}
        lat = _float(part.get("latitude"))
        lng = _float(part.get("longitude"))
        if lat is None or lng is None or part.get("status") not in self.LIVE_STATUSES:
            return {"outcome": "ignored", "reason": "not_live_discovered", "part_id": part.get("part_id")}

        matches = []
        for territory in territories or []:
            event = normalise_territory_event(territory)
            if not self.is_stable_territory(event):
                continue
            if not _contains_bounds(event["bounds"], lat, lng):
                continue
            if not _point_in_polygon(lat, lng, event["vertices"]):
                continue
            matches.append(event)

        if not matches:
            return {"outcome": "public", "territory": None, "part_id": part.get("part_id")}

        owner_keys = {(match["territory_owner_id"], match["territory_clan"]) for match in matches}
        if len(owner_keys) > 1:
            return {
                "outcome": "contested",
                "reason": "overlapping_territories",
                "territories": matches,
                "part_id": part.get("part_id"),
            }

        selected = sorted(
            matches,
            key=lambda item: (int(item.get("territory_state_version") or 0), item.get("territory_id") or ""),
            reverse=True,
        )[0]
        if selected["territory_clan"] == _clean(part.get("clan_code")):
            return {"outcome": "active", "territory": selected, "part_id": part.get("part_id")}
        return {"outcome": "contained", "territory": selected, "part_id": part.get("part_id")}

    def resolve_parts_in_changed_area(self, event):
        event = normalise_territory_event(event)
        cycle_id = _clean(event["raw"].get("cycle_id") if isinstance(event.get("raw"), dict) else "")
        if not cycle_id:
            active = self.repository.get_active_cycle()
            cycle_id = (active or {}).get("cycle_id", "")
        if not cycle_id:
            return []

        parts_by_id = {}
        bounds = event.get("bounds")
        if bounds:
            for part in self.repository.list_discovered_parts_in_bounds(
                cycle_id,
                bounds["min_lat"],
                bounds["min_lng"],
                bounds["max_lat"],
                bounds["max_lng"],
            ):
                parts_by_id[part["part_id"]] = part
        if event.get("territory_id"):
            for part in self.repository.list_parts_by_territory(cycle_id, event["territory_id"]):
                parts_by_id[part["part_id"]] = part
        return list(parts_by_id.values())

    def on_territory_stabilized(self, event):
        territory = normalise_territory_event(event)
        if not self.is_stable_territory(territory):
            return self._apply_public_decay(territory, reason="territory_not_stable")
        return self._apply_resolution([territory], territory, reason="territory_stabilized")

    def on_territory_owner_changed(self, event):
        territory = normalise_territory_event(event)
        if not self.is_stable_territory(territory):
            return self._apply_public_decay(territory, reason="territory_owner_unstable")
        return self._apply_resolution([territory], territory, reason="territory_owner_changed")

    def on_territory_contested(self, event):
        territory = normalise_territory_event(event)
        conflict_id = territory["conflict_id"] or f"territory:{territory['territory_id']}:contested"
        changed = []
        skipped = []
        for part in self.resolve_parts_in_changed_area(territory):
            if part.get("status") not in self.LIVE_STATUSES:
                skipped.append({"part_id": part.get("part_id"), "reason": "not_live"})
                continue
            changed.append(
                self.lifecycle.freeze_for_conflict(
                    part["part_id"],
                    conflict_id,
                    reason="territory_contested",
                    source_event_id=territory["event_id"] or conflict_id,
                )
            )
        return self._report("territory_contested", territory, changed, skipped)

    def on_territory_released(self, event):
        territory = normalise_territory_event(event)
        return self._apply_public_decay(territory, reason="territory_released")

    def reconcile_parts_with_territories(self, cycle_id=None, territories=None, apply=False):
        cycle_id = _clean(cycle_id or ((self.repository.get_active_cycle() or {}).get("cycle_id")))
        if not cycle_id:
            return {"ok": False, "cycle_id": "", "apply": bool(apply), "changes": [], "reason": "no_cycle"}
        territories = [
            normalise_territory_event(item)
            for item in (territories if territories is not None else self._read_territories())
        ]
        changes = []
        for part in self.repository.list_parts(cycle_id):
            if part.get("status") not in self.LIVE_STATUSES:
                continue
            outcome = self.resolve_part_territory(part, territories=territories)
            desired = outcome.get("outcome")
            if not self._needs_change(part, outcome):
                continue
            change = {
                "part_id": part["part_id"],
                "from_status": part["status"],
                "from_territory_id": part.get("territory_id"),
                "outcome": desired,
                "territory_id": (outcome.get("territory") or {}).get("territory_id", ""),
            }
            if apply:
                from_version = self.repository.get_state_version(cycle_id)
                transition_id = (
                    f"reconcile:{cycle_id}:{part['part_id']}:{desired}:"
                    f"from:{int(from_version or 0)}"
                )
                change["part"] = self._apply_part_outcome(
                    part,
                    outcome,
                    source_event_id=transition_id,
                )
            changes.append(change)
        return {"ok": True, "cycle_id": cycle_id, "apply": bool(apply), "changes": changes, "count": len(changes)}

    def _read_territories(self):
        if not self.territory_reader:
            return []
        if callable(self.territory_reader):
            return list(self.territory_reader() or [])
        if hasattr(self.territory_reader, "list_stable_territories"):
            return list(self.territory_reader.list_stable_territories() or [])
        return []

    def _apply_resolution(self, territories, changed_event, reason):
        changed_event = normalise_territory_event(changed_event)
        changed = []
        skipped = []
        for part in self.resolve_parts_in_changed_area(changed_event):
            outcome = self.resolve_part_territory(part, territories=territories)
            if not self._needs_change(part, outcome):
                skipped.append({"part_id": part.get("part_id"), "reason": "already_current"})
                continue
            changed.append(
                self._apply_part_outcome(
                    part,
                    outcome,
                    reason=reason,
                    source_event_id=changed_event["event_id"] or changed_event["territory_id"],
                )
            )
        return self._report(reason, changed_event, changed, skipped)

    def _apply_public_decay(self, territory, reason):
        territory = normalise_territory_event(territory)
        changed = []
        skipped = []
        for part in self.resolve_parts_in_changed_area(territory):
            if part.get("status") == "public" and not part.get("territory_id") and part.get("conflict_state") != "contested":
                skipped.append({"part_id": part.get("part_id"), "reason": "already_public"})
                continue
            outcome = {"outcome": "public", "territory": None}
            changed.append(
                self._apply_part_outcome(
                    part,
                    outcome,
                    reason=reason,
                    source_event_id=territory["event_id"] or territory["territory_id"],
                )
            )
        return self._report(reason, territory, changed, skipped)

    def _apply_part_outcome(self, part, outcome, reason="", source_event_id=""):
        part = part if isinstance(part, dict) else {}
        outcome_name = outcome.get("outcome")
        territory = outcome.get("territory") or {}
        if part.get("conflict_state") == "contested" and outcome_name in {"public", "contained", "active"}:
            self.lifecycle.resolve_after_conflict(
                part["part_id"],
                resolution_status=part.get("frozen_status") or part.get("status"),
                reason=reason or "territory_conflict_resolved",
                source_event_id=f"{source_event_id}:resolve",
                conflict_id=part.get("conflict_id"),
            )
            part = self.repository.get_part(part["part_id"])
        if outcome_name == "public":
            return self.lifecycle.reveal_part(part["part_id"], reason=reason, source_event_id=source_event_id)
        if outcome_name == "contained":
            return self.lifecycle.contain_part(part["part_id"], territory=territory, reason=reason, source_event_id=source_event_id)
        if outcome_name == "active":
            return self.lifecycle.activate_part(
                part["part_id"],
                territory=territory,
                player_id=territory.get("territory_owner_id"),
                player_clan=territory.get("territory_clan"),
                reason=reason,
                source_event_id=source_event_id,
            )
        if outcome_name == "contested":
            conflict_id = f"ghostnetwork:overlap:{part.get('part_id')}:{source_event_id}"
            return self.lifecycle.freeze_for_conflict(
                part["part_id"],
                conflict_id,
                reason=outcome.get("reason") or reason or "territory_overlap",
                source_event_id=source_event_id or conflict_id,
            )
        return part

    def _needs_change(self, part, outcome):
        desired = outcome.get("outcome")
        territory = outcome.get("territory") or {}
        if desired == "ignored":
            return False
        if desired == "contested":
            return part.get("conflict_state") != "contested"
        if part.get("conflict_state") == "contested":
            return True
        if desired == "public":
            return part.get("status") != "public" or bool(part.get("territory_id"))
        if desired in {"contained", "active"}:
            return (
                part.get("status") != desired
                or part.get("territory_id") != territory.get("territory_id")
                or part.get("territory_owner_id") != territory.get("territory_owner_id")
                or part.get("territory_clan") != territory.get("territory_clan")
            )
        return False

    @staticmethod
    def _report(action, territory, changed, skipped):
        return {
            "ok": True,
            "action": action,
            "territory_id": territory.get("territory_id", ""),
            "changed": changed,
            "changed_count": len(changed),
            "skipped": skipped,
            "skipped_count": len(skipped),
        }
