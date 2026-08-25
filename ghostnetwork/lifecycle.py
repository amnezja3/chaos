from __future__ import annotations

from database import dumps_json

from .errors import InvalidPartStateTransition, PartNotFound


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _territory_context(territory=None):
    territory = territory if isinstance(territory, dict) else {}
    return {
        "territory_id": _clean(territory.get("territory_id") or territory.get("id")),
        "territory_owner_id": _clean(territory.get("territory_owner_id") or territory.get("owner_id") or territory.get("owner")),
        "territory_clan": _clean(territory.get("territory_clan") or territory.get("owner_clan") or territory.get("clan")),
        "territory_state_version": int(territory.get("territory_state_version") or territory.get("state_version") or 0),
    }


class GhostPartLifecycleService:
    """Domain state machine for GhostNetwork part instances.

    Repository methods remain persistence primitives. This service owns the
    allowed transitions, immutable anchor/discoverer fields and idempotent
    domain event contract introduced in Sprint 117.
    """

    ALLOWED_CONFLICT_BASE_STATUSES = {"public", "contained", "active"}
    TERMINAL_STATUSES = {"consumed"}

    def __init__(self, repository):
        self.repository = repository

    def reserve_part(self, cycle_id, part_id, target_id, player_id, player_clan="", reservation_id=None, expires_at=None):
        return self.repository.create_reservation(
            cycle_id,
            part_id,
            target_id,
            player_id,
            player_clan,
            reservation_id=reservation_id,
            expires_at=expires_at,
        )

    def release_reservation(self, reservation_id, reason, status="released"):
        return self.repository.release_reservation(reservation_id, status=status, reason=reason)

    def discover_part(self, reservation_id, player=None, target=None, operation_id="", result=None, context=None):
        return self.repository.discover_reserved_part(
            reservation_id,
            player=player,
            target=target,
            operation_id=operation_id,
            result=result,
            context=context,
        )

    def contain_part(self, part_id, territory=None, reason="", source_event_id="", operation_id=""):
        part = self._require_part(part_id)
        self._assert_base_transition(part, {"public", "active", "contained"}, "contained")
        territory = _territory_context(territory)
        if not territory["territory_owner_id"]:
            raise InvalidPartStateTransition("Contained part requires territory owner.")
        now = self.repository.now()
        updates = {
            "status": "contained",
            "territory_id": territory["territory_id"],
            "territory_owner_id": territory["territory_owner_id"],
            "territory_clan": territory["territory_clan"],
            "territory_state_version": territory["territory_state_version"],
            "contained_at": part.get("contained_at") or now,
        }
        return self._transition(
            part,
            updates,
            "ghost.part_contained",
            reason=reason,
            source_event_id=source_event_id,
            operation_id=operation_id,
            territory=territory,
            dedupe_key=f"part:{part_id}:contain:{source_event_id or territory['territory_state_version'] or now}",
            audience_scope="owner",
            audience_clan=territory["territory_clan"],
        )["part"]

    def activate_part(self, part_id, territory=None, player_id="", player_clan="", reason="", source_event_id="", operation_id=""):
        part = self._require_part(part_id)
        self._assert_base_transition(part, {"public", "contained", "active"}, "active")
        territory = _territory_context(territory)
        territory_clan = territory["territory_clan"] or _clean(player_clan)
        if part.get("clan_code") and territory_clan and part.get("clan_code") != territory_clan:
            raise InvalidPartStateTransition("Active part requires matching territory clan.")
        now = self.repository.now()
        updates = {
            "status": "active",
            "territory_id": territory["territory_id"],
            "territory_owner_id": territory["territory_owner_id"],
            "territory_clan": territory_clan,
            "territory_state_version": territory["territory_state_version"],
            "activated_at": part.get("activated_at") or now,
            "last_activated_at": now,
        }
        return self._transition(
            part,
            updates,
            "ghost.part_activated",
            reason=reason,
            source_event_id=source_event_id,
            operation_id=operation_id,
            territory=territory,
            player_id=player_id,
            player_clan=player_clan or territory_clan,
            dedupe_key=f"part:{part_id}:activate:{source_event_id or territory['territory_state_version'] or now}",
            # An active endpoint has exact public location visibility. Its
            # transition can complete an active -> active connection, so every
            # authenticated viewer must receive the state-version edge.
            audience_scope="public",
        )["part"]

    def reveal_part(self, part_id, reason="", source_event_id="", operation_id=""):
        part = self._require_part(part_id)
        self._assert_base_transition(part, {"public", "contained", "active"}, "public")
        now = self.repository.now()
        updates = {
            "status": "public",
            "territory_id": "",
            "territory_owner_id": "",
            "territory_clan": "",
            "territory_state_version": 0,
            "revealed_at": part.get("revealed_at") or now,
        }
        return self._transition(
            part,
            updates,
            "ghost.part_revealed",
            reason=reason,
            source_event_id=source_event_id,
            operation_id=operation_id,
            dedupe_key=f"part:{part_id}:reveal:{source_event_id or now}",
            audience_scope="public",
        )["part"]

    def freeze_for_conflict(self, part_id, conflict_id, reason="", source_event_id=""):
        part = self._require_part(part_id)
        if part.get("status") not in self.ALLOWED_CONFLICT_BASE_STATUSES:
            raise InvalidPartStateTransition(f"Part cannot enter conflict from {part.get('status')}.")
        if part.get("conflict_state") == "contested" and part.get("conflict_id") == _clean(conflict_id):
            return part
        now = self.repository.now()
        updates = {
            "conflict_state": "contested",
            "frozen_status": part.get("status"),
            "conflict_id": conflict_id,
            "contested_at": part.get("contested_at") or now,
        }
        return self._transition(
            part,
            updates,
            "ghost.part_contested",
            reason=reason,
            source_event_id=source_event_id,
            conflict_id=conflict_id,
            dedupe_key=f"part:{part_id}:conflict:{source_event_id or conflict_id}",
            audience_scope="public",
        )["part"]

    def resolve_after_conflict(self, part_id, resolution_status=None, reason="", source_event_id="", conflict_id=""):
        part = self._require_part(part_id)
        if part.get("conflict_state") != "contested":
            raise InvalidPartStateTransition("Part is not contested.")
        resolution_status = _clean(resolution_status or part.get("frozen_status") or part.get("status"))
        if resolution_status not in self.ALLOWED_CONFLICT_BASE_STATUSES:
            raise InvalidPartStateTransition(f"Invalid conflict resolution status: {resolution_status}")
        now = self.repository.now()
        updates = {
            "status": resolution_status,
            "conflict_state": "none",
            "frozen_status": "",
            "conflict_id": "",
            "conflict_resolved_at": now,
        }
        return self._transition(
            part,
            updates,
            "ghost.part_conflict_resolved",
            reason=reason,
            source_event_id=source_event_id,
            conflict_id=conflict_id or part.get("conflict_id"),
            dedupe_key=f"part:{part_id}:conflict_resolved:{source_event_id or conflict_id or part.get('conflict_id')}",
            audience_scope="public",
        )["part"]

    def deactivate_part(self, part_id, next_status="public", territory=None, reason="", source_event_id="", operation_id=""):
        part = self._require_part(part_id)
        if part.get("status") != "active":
            raise InvalidPartStateTransition(f"Only active part can be deactivated, got {part.get('status')}.")
        next_status = _clean(next_status, "public")
        if next_status not in {"public", "contained"}:
            raise InvalidPartStateTransition(f"Invalid deactivation target: {next_status}")
        territory = _territory_context(territory)
        now = self.repository.now()
        updates = {
            "status": next_status,
            "deactivated_at": part.get("deactivated_at") or now,
            "last_deactivated_at": now,
        }
        if next_status == "public":
            updates.update({
                "territory_id": "",
                "territory_owner_id": "",
                "territory_clan": "",
                "territory_state_version": 0,
            })
        else:
            updates.update({
                "territory_id": territory["territory_id"] or part.get("territory_id"),
                "territory_owner_id": territory["territory_owner_id"] or part.get("territory_owner_id"),
                "territory_clan": territory["territory_clan"] or part.get("territory_clan"),
                "territory_state_version": territory["territory_state_version"] or part.get("territory_state_version") or 0,
            })
        return self._transition(
            part,
            updates,
            "ghost.part_deactivated",
            reason=reason,
            source_event_id=source_event_id,
            operation_id=operation_id,
            territory=territory,
            dedupe_key=f"part:{part_id}:deactivate:{source_event_id or now}",
            # Removing an active endpoint can remove a globally visible
            # connection and therefore needs the same public lifecycle edge.
            # Viewer projection still redacts a contained successor.
            audience_scope="public",
        )["part"]

    def consume_part(self, part_id, signal_id, reason="", source_event_id=""):
        part = self._require_part(part_id)
        self._assert_base_transition(part, {"public", "contained", "active"}, "consumed")
        signal_id = _clean(signal_id)
        if not signal_id:
            raise InvalidPartStateTransition("Consuming part requires saved GhostSignal id.")
        now = self.repository.now()
        updates = {
            "status": "consumed",
            "conflict_state": "none",
            "frozen_status": "",
            "conflict_id": "",
            "consumed_at": now,
            "consumed_signal_id": signal_id,
        }
        return self._transition(
            part,
            updates,
            "ghost.part_consumed",
            reason=reason,
            source_event_id=source_event_id,
            dedupe_key=f"part:{part_id}:consume:{signal_id}",
            payload_extra={"signal_id": signal_id},
            audience_scope="internal",
        )["part"]

    def replay_part_history(self, part_id):
        part = self._require_part(part_id)
        events = [
            event for event in self.repository.list_events(part["cycle_id"], limit=1000)
            if event.get("part_id") == part_id
        ]
        inferred_status = {
            "ghost.part_reserved": "reserved",
            "ghost.part_reservation_released": "pooled",
            "ghost.part_reservation_expired": "pooled",
            "ghost.part_discovered": "public",
            "ghost.part_contained": "contained",
            "ghost.part_revealed": "public",
            "ghost.part_activated": "active",
            "ghost.part_deactivated": None,
            "ghost.part_consumed": "consumed",
        }
        status = "pooled"
        conflict_state = "none"
        invalid = []
        for event in events:
            payload = event.get("payload") or {}
            previous_status = payload.get("previous_status") or status
            next_status = payload.get("status")
            if not next_status:
                next_status = inferred_status.get(event.get("event_type"), status)
                if next_status is None:
                    next_status = "contained" if payload.get("territory_owner_id") else "public"
            if previous_status != status:
                invalid.append(event.get("event_id"))
            status = next_status
            if event.get("event_type") == "ghost.part_contested" and not payload.get("conflict_state"):
                conflict_state = "contested"
            elif event.get("event_type") == "ghost.part_conflict_resolved" and not payload.get("conflict_state"):
                conflict_state = "none"
            else:
                conflict_state = payload.get("conflict_state") or conflict_state
        return {
            "part_id": part_id,
            "events": events,
            "status": status,
            "conflict_state": conflict_state,
            "invalid_events": invalid,
            "ok": not invalid,
        }

    def _require_part(self, part_id):
        part = self.repository.get_part(part_id)
        if not part:
            raise PartNotFound(f"Part not found: {part_id}")
        return part

    def _assert_base_transition(self, part, allowed_from, to_status):
        if part.get("status") in self.TERMINAL_STATUSES:
            raise InvalidPartStateTransition("Consumed part is terminal.")
        if part.get("status") == "pooled" and to_status != "reserved":
            raise InvalidPartStateTransition(f"Part cannot move from pooled to {to_status}.")
        if part.get("status") == "reserved" and to_status != "public":
            raise InvalidPartStateTransition(f"Part cannot move from reserved to {to_status}.")
        if part.get("status") not in allowed_from:
            raise InvalidPartStateTransition(f"Part cannot move from {part.get('status')} to {to_status}.")

    def _transition(
        self,
        part,
        updates,
        event_type,
        *,
        reason="",
        source_event_id="",
        source_system="ghostnetwork",
        operation_id="",
        conflict_id="",
        previous_owner="",
        new_owner="",
        territory=None,
        player_id="",
        player_clan="",
        dedupe_key="",
        payload_extra=None,
        audience_scope="internal",
        audience_clan="",
    ):
        previous_status = part.get("status")
        previous_conflict_state = part.get("conflict_state") or "none"
        territory = territory if isinstance(territory, dict) else {}
        next_status = updates.get("status", previous_status)
        next_conflict_state = updates.get("conflict_state", previous_conflict_state)
        payload = {
            "event_type": event_type,
            "cycle_id": part.get("cycle_id"),
            "part_id": part.get("part_id"),
            "part_code": part.get("part_code"),
            "previous_status": previous_status,
            "status": next_status,
            "previous_conflict_state": previous_conflict_state,
            "conflict_state": next_conflict_state,
            "player_id": _clean(player_id),
            "player_clan": _clean(player_clan),
            "territory_id": updates.get("territory_id", territory.get("territory_id") or part.get("territory_id") or ""),
            "territory_owner_id": updates.get("territory_owner_id", territory.get("territory_owner_id") or part.get("territory_owner_id") or ""),
            "territory_clan": updates.get("territory_clan", territory.get("territory_clan") or part.get("territory_clan") or ""),
            "reason": _clean(reason),
            "source_event_id": _clean(source_event_id),
            "source_system": _clean(source_system, "ghostnetwork"),
            "operation_id": _clean(operation_id),
            "conflict_id": _clean(conflict_id or updates.get("conflict_id")),
            "previous_owner": _clean(previous_owner or part.get("territory_owner_id")),
            "new_owner": _clean(new_owner or updates.get("territory_owner_id")),
        }
        if payload_extra:
            payload.update(payload_extra)
        result = self.repository.patch_part_lifecycle(
            part["part_id"],
            updates,
            event_type=event_type,
            payload=payload,
            dedupe_key=dedupe_key,
            player_id=player_id,
            clan_code=player_clan,
            territory_id=payload["territory_id"],
            audience_scope=audience_scope,
            audience_clan=audience_clan,
        )
        event = result.get("event") or {}
        if event:
            payload["event_id"] = event.get("event_id")
            payload["state_version"] = event.get("state_version")
            payload["dedupe_key"] = event.get("dedupe_key")
            # Runtime bridges need the canonical event that caused this
            # mutation. Keep it only on the returned copy; it is not persisted
            # in the ghost_parts row or exposed by viewer projections.
            result["part"]["_domain_event"] = event
        return result

    def migrate_anchor(self, part_id, new_target, reason="", source_event_id=""):
        part = self._require_part(part_id)
        if part.get("status") in {"pooled", "reserved", "consumed"}:
            raise InvalidPartStateTransition("Only discovered live parts can migrate anchor.")
        new_target = new_target if isinstance(new_target, dict) else {}
        target_id = _clean(new_target.get("target_id") or new_target.get("id"))
        lat = new_target.get("lat") or new_target.get("latitude")
        lng = new_target.get("lng") or new_target.get("lon") or new_target.get("longitude")
        if not target_id or lat is None or lng is None:
            raise InvalidPartStateTransition("Anchor migration requires target_id and coordinates.")
        anchor = {
            "target_id": target_id,
            "label": _clean(new_target.get("label") or new_target.get("name") or target_id),
            "latitude": lat,
            "longitude": lng,
            "reason": _clean(reason),
        }
        updates = {
            "target_id": target_id,
            "latitude": lat,
            "longitude": lng,
            "anchor_snapshot_json": dumps_json(anchor),
        }
        return self._transition(
            part,
            updates,
            "ghost.part_anchor_migrated",
            reason=reason,
            source_event_id=source_event_id,
            dedupe_key=f"part:{part_id}:anchor_migrated:{source_event_id or target_id}",
            payload_extra={"anchor": anchor},
            audience_scope="internal",
        )["part"]
