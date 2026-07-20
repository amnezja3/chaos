from __future__ import annotations

from .errors import RepositoryIntegrityError


PARTS_PER_MACHINE = 5
PARTS_PER_CYCLE = 20

STRATEGIC_STATUS_TO_MODULE = {
    "public": "neutral",
    "contained": "blocked",
    "active": "active",
}

MACHINE_PROGRESS_EVENTS = {
    "ghost.machine_progress_changed",
    "ghost.machine_online",
    "ghost.machine_offline",
}


def _clean(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def _viewer_id(viewer):
    viewer = viewer if isinstance(viewer, dict) else {}
    return _clean(
        viewer.get("player_id")
        or viewer.get("username")
        or viewer.get("login")
        or viewer.get("id")
    )


def _viewer_clan(viewer):
    viewer = viewer if isinstance(viewer, dict) else {}
    return _clean(viewer.get("clan_code") or viewer.get("ghost_clan") or viewer.get("clan"))


class GhostModuleStateService:
    """Read-only strategic state resolver for GhostNetwork parts."""

    def __init__(self, repository):
        self.repository = repository

    def resolve_part_module_state(self, part):
        part = part if isinstance(part, dict) else {}
        status = _clean(part.get("status"))
        conflict_state = _clean(part.get("conflict_state"), "none") or "none"
        base_status = status
        if conflict_state == "contested":
            frozen_status = _clean(part.get("frozen_status"))
            if frozen_status in STRATEGIC_STATUS_TO_MODULE:
                base_status = frozen_status
        module_state = STRATEGIC_STATUS_TO_MODULE.get(base_status, "")
        strategic_state_available = bool(module_state)
        part_clan = _clean(part.get("clan_code"))
        territory_clan = _clean(part.get("territory_clan"))
        territory_id = _clean(part.get("territory_id"))
        territory_owner_id = _clean(part.get("territory_owner_id"))

        if module_state == "neutral":
            territory_id = ""
            territory_owner_id = ""
            territory_clan = ""

        return {
            "part_id": _clean(part.get("part_id")),
            "cycle_id": _clean(part.get("cycle_id")),
            "part_code": _clean(part.get("part_code")),
            "machine_code": _clean(part.get("machine_code")),
            "profession_code": _clean(part.get("profession_code")),
            "clan_code": part_clan,
            "part_clan": part_clan,
            "status": status,
            "base_status": base_status,
            "module_state": module_state,
            "strategic_state_available": strategic_state_available,
            "conflict_state": conflict_state,
            "territory_id": territory_id,
            "territory_owner_id": territory_owner_id,
            "territory_clan": territory_clan,
            "ability_enabled": module_state == "active",
            "controlled_by_correct_clan": bool(module_state == "active" and territory_clan == part_clan),
            "controlled_by_foreign_clan": bool(module_state == "blocked" and territory_clan and territory_clan != part_clan),
            "is_public": module_state == "neutral",
            "is_blocked": module_state == "blocked",
            "is_active": module_state == "active",
        }

    def resolve_part_viewer_relation(self, part, viewer):
        state = self.resolve_part_module_state(part)
        viewer_id = _viewer_id(viewer)
        viewer_clan = _viewer_clan(viewer)
        module_state = state["module_state"]
        if module_state == "neutral":
            return "public_neutral"
        if module_state == "blocked":
            if viewer_id and state["territory_owner_id"] == viewer_id:
                return "self_foreign_blocked"
            return "foreign_blocked"
        if module_state == "active":
            if viewer_id and state["territory_owner_id"] == viewer_id:
                return "self_own_active"
            if viewer_clan and viewer_clan == state["part_clan"]:
                return "clan_own_active"
            return "foreign_active"
        return ""

    def resolve_machine_progress(self, cycle_id, machine_code):
        cycle_id = _clean(cycle_id)
        machine_code = _clean(machine_code)
        parts = [
            part for part in self.repository.list_parts(cycle_id)
            if _clean(part.get("machine_code")) == machine_code
        ]
        states = [self.resolve_part_module_state(part) for part in parts]
        active_parts = sum(1 for state in states if state["module_state"] == "active")
        progress = {
            "cycle_id": cycle_id,
            "machine_code": machine_code,
            "clan_code": _clean(next((part.get("clan_code") for part in parts if part.get("clan_code")), "")),
            "parts_total": len(parts),
            "parts_pooled": sum(1 for part in parts if part.get("status") == "pooled"),
            "parts_reserved": sum(1 for part in parts if part.get("status") == "reserved"),
            "parts_neutral": sum(1 for state in states if state["module_state"] == "neutral"),
            "parts_blocked": sum(1 for state in states if state["module_state"] == "blocked"),
            "parts_active": active_parts,
            "parts_contested": sum(1 for state in states if state["conflict_state"] == "contested"),
        }
        progress["progress_percent"] = int(round(active_parts / PARTS_PER_MACHINE * 100))
        progress["machine_online"] = active_parts == PARTS_PER_MACHINE
        return progress

    def resolve_clan_machine_progress(self, cycle_id, clan_code):
        cycle_id = _clean(cycle_id)
        clan_code = _clean(clan_code)
        machines = sorted(
            {
                _clean(part.get("machine_code"))
                for part in self.repository.list_parts(cycle_id)
                if _clean(part.get("clan_code")) == clan_code and _clean(part.get("machine_code"))
            }
        )
        machine_progress = [self.resolve_machine_progress(cycle_id, machine) for machine in machines]
        return {
            "cycle_id": cycle_id,
            "clan_code": clan_code,
            "machines": machine_progress,
            "machines_total": len(machine_progress),
            "machines_online": sum(1 for machine in machine_progress if machine["machine_online"]),
        }

    def resolve_cycle_progress(self, cycle_id):
        parts = self.repository.list_parts(cycle_id)
        states = [self.resolve_part_module_state(part) for part in parts]
        machine_codes = sorted({_clean(part.get("machine_code")) for part in parts if _clean(part.get("machine_code"))})
        machines = [self.resolve_machine_progress(cycle_id, machine_code) for machine_code in machine_codes]
        parts_active = sum(1 for state in states if state["module_state"] == "active")
        return {
            "cycle_id": _clean(cycle_id),
            "parts_total": len(parts),
            "parts_discovered": sum(1 for state in states if state["strategic_state_available"]),
            "parts_neutral": sum(1 for state in states if state["module_state"] == "neutral"),
            "parts_blocked": sum(1 for state in states if state["module_state"] == "blocked"),
            "parts_active": parts_active,
            "parts_contested": sum(1 for state in states if state["conflict_state"] == "contested"),
            "machines_online": sum(1 for machine in machines if machine["machine_online"]),
            "network_ready": parts_active == PARTS_PER_CYCLE,
        }

    def resolve_cycle_module_states(self, cycle_id):
        parts = self.repository.list_parts(cycle_id)
        machine_codes = sorted({_clean(part.get("machine_code")) for part in parts if _clean(part.get("machine_code"))})
        return {
            "cycle_id": _clean(cycle_id),
            "state_version": self.repository.get_state_version(cycle_id),
            "parts": [self.resolve_part_module_state(part) for part in parts],
            "machines": [self.resolve_machine_progress(cycle_id, machine_code) for machine_code in machine_codes],
            "cycle_progress": self.resolve_cycle_progress(cycle_id),
        }

    def recompute_after_part_change(self, part_id):
        part = self.repository.get_part(part_id)
        if not part:
            return {"ok": False, "part_id": _clean(part_id), "reason": "part_not_found"}
        return {
            "ok": True,
            "part": self.resolve_part_module_state(part),
            "machine_progress": self.record_machine_progress_if_changed(
                part["cycle_id"],
                part.get("machine_code"),
            ),
            "cycle_progress": self.resolve_cycle_progress(part["cycle_id"]),
            "adjacent_connections": self._adjacent_connections(part),
        }

    def record_machine_progress_if_changed(self, cycle_id, machine_code):
        progress = self.resolve_machine_progress(cycle_id, machine_code)
        last = self._last_machine_progress_event(cycle_id, machine_code)
        previous_payload = (last or {}).get("payload") or {}
        previous_fingerprint = self._progress_fingerprint(previous_payload)
        current_fingerprint = self._progress_fingerprint(progress)
        if previous_fingerprint == current_fingerprint:
            return {"ok": True, "changed": False, "progress": progress, "event": None}

        previous_active = int(previous_payload.get("active_parts") or 0)
        previous_online = bool(previous_payload.get("machine_online"))
        payload = {
            "cycle_id": progress["cycle_id"],
            "machine_code": progress["machine_code"],
            "clan_code": progress["clan_code"],
            "previous_active_parts": previous_active,
            "active_parts": progress["parts_active"],
            "blocked_parts": progress["parts_blocked"],
            "neutral_parts": progress["parts_neutral"],
            "contested_parts": progress["parts_contested"],
            "machine_online": progress["machine_online"],
            "state_version": self.repository.get_state_version(cycle_id) + 1,
        }
        event = self._append_progress_event(
            "ghost.machine_progress_changed",
            progress,
            payload,
            f"ghost:machine_progress:{cycle_id}:{machine_code}:{current_fingerprint}",
        )
        transition_event = None
        if not previous_online and progress["machine_online"]:
            transition_event = self._append_progress_event(
                "ghost.machine_online",
                progress,
                dict(payload, state_version=self.repository.get_state_version(cycle_id) + 1),
                f"ghost:machine_online:{cycle_id}:{machine_code}:{current_fingerprint}",
            )
        elif previous_online and not progress["machine_online"]:
            transition_event = self._append_progress_event(
                "ghost.machine_offline",
                progress,
                dict(payload, state_version=self.repository.get_state_version(cycle_id) + 1),
                f"ghost:machine_offline:{cycle_id}:{machine_code}:{current_fingerprint}",
            )
        return {
            "ok": True,
            "changed": bool(event),
            "progress": progress,
            "event": event,
            "transition_event": transition_event,
        }

    def build_cluster_ghost_component_contract(self, cycle_id, territory_id, viewer=None):
        parts = self.repository.list_parts_by_territory(cycle_id, territory_id)
        states = [self.resolve_part_module_state(part) for part in parts]
        viewer_clan = _viewer_clan(viewer)
        total = len(states)
        return {
            "cycle_id": _clean(cycle_id),
            "territory_id": _clean(territory_id),
            "ghost_components": {
                "total": total,
                "neutral": sum(1 for state in states if state["module_state"] == "neutral"),
                "blocked": sum(1 for state in states if state["module_state"] == "blocked"),
                "active": sum(1 for state in states if state["module_state"] == "active"),
                "contested": sum(1 for state in states if state["conflict_state"] == "contested"),
            },
            "contains_own_clan_part": bool(
                viewer_clan and any(state["part_clan"] == viewer_clan for state in states)
            ),
            "contains_foreign_clan_part": bool(
                viewer_clan and any(state["part_clan"] and state["part_clan"] != viewer_clan for state in states)
            ),
            "contains_active_part": any(state["module_state"] == "active" for state in states),
            "contains_blocked_part": any(state["module_state"] == "blocked" for state in states),
            "contains_ghost_part": total > 0,
            "ghost_anchor_protected": total > 0,
        }

    def get_modules_status_report(self, cycle_id=None, include_parts=False):
        active = self.repository.get_active_cycle()
        cycle_id = _clean(cycle_id or ((active or {}).get("cycle_id")))
        if not cycle_id:
            return {
                "ok": False,
                "cycle_id": "",
                "state_version": 0,
                "parts_by_state": {},
                "machines": [],
                "network_ready": False,
                "conflicts_frozen": 0,
                "integrity_errors": ["no_cycle"],
            }
        resolved = self.resolve_cycle_module_states(cycle_id)
        progress = resolved["cycle_progress"]
        report = {
            "ok": True,
            "cycle_id": cycle_id,
            "state_version": resolved["state_version"],
            "parts_by_state": {
                "neutral": progress["parts_neutral"],
                "blocked": progress["parts_blocked"],
                "active": progress["parts_active"],
                "contested": progress["parts_contested"],
            },
            "machines": resolved["machines"],
            "network_ready": progress["network_ready"],
            "conflicts_frozen": progress["parts_contested"],
            "integrity_errors": self.repository.health_check().get("errors", []),
        }
        if include_parts:
            report["parts"] = resolved["parts"]
        return report

    def _last_machine_progress_event(self, cycle_id, machine_code):
        machine_code = _clean(machine_code)
        for event in reversed(self.repository.list_events(cycle_id, limit=1000)):
            if event.get("event_type") not in MACHINE_PROGRESS_EVENTS:
                continue
            payload = event.get("payload") or {}
            if _clean(payload.get("machine_code")) == machine_code:
                return event
        return None

    @staticmethod
    def _progress_fingerprint(payload):
        active = payload.get("active_parts", payload.get("parts_active", 0))
        blocked = payload.get("blocked_parts", payload.get("parts_blocked", 0))
        neutral = payload.get("neutral_parts", payload.get("parts_neutral", 0))
        contested = payload.get("contested_parts", payload.get("parts_contested", 0))
        return ":".join(str(int(value or 0)) for value in (active, blocked, neutral, contested)) + (
            f":{1 if payload.get('machine_online') else 0}"
        )

    def _append_progress_event(self, event_type, progress, payload, dedupe_key):
        try:
            return self.repository.append_event(
                event_type,
                cycle_id=progress["cycle_id"],
                entity_id=f"ghost-machine:{progress['cycle_id']}:{progress['machine_code']}",
                clan_code=progress["clan_code"],
                audience_scope="internal",
                audience_clan=progress["clan_code"],
                dedupe_key=dedupe_key,
                payload=payload,
            )
        except RepositoryIntegrityError:
            return None

    def _adjacent_connections(self, part):
        part_id = _clean(part.get("part_id"))
        cycle_id = _clean(part.get("cycle_id"))
        adjacent = []
        for connection in self.repository.list_connections(cycle_id):
            if connection.get("part_a_id") == part_id or connection.get("part_b_id") == part_id:
                adjacent.append(connection)
        return adjacent
