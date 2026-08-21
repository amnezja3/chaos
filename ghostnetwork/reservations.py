from __future__ import annotations

import hashlib
import math
from datetime import datetime, timedelta, timezone

from config import (
    GHOSTNETWORK_DROP_CHANCE,
    GHOSTNETWORK_DROPS_ENABLED,
    GHOSTNETWORK_MIN_PART_DISTANCE_KM,
    GHOSTNETWORK_RESERVATION_TTL_SECONDS,
)

from .catalog import normalize_ghostnetwork_profile_identity
from .errors import GhostNetworkError, ReservationConflict, SpatialSeparationConflict
from .repository import _clean, _iso


ACTIVE_CYCLE_STATUS = "active"
RESERVABLE_PART_STATUS = "pooled"
RESERVED_PART_STATUS = "reserved"

RELEASE_REASONS = {
    "target_abandoned",
    "operation_cancelled",
    "operation_failed",
    "reservation_expired",
    "cycle_locked",
    "technical_recovery",
}

BLOCKED_TARGET_MODES = {
    "player",
    "npc",
    "response_npc",
    "operation",
    "incident",
    "territory",
    "territory_area",
    "line",
    "ghostnetwork",
    "ghostnetwork_part",
}

BLOCKED_SOURCE_TYPES = {
    "player",
    "npc",
    "response_npc",
    "operation",
    "incident",
    "territory",
    "territory_area",
    "line",
    "ghostnetwork",
    "ghostnetwork_part",
    "technical",
    "duplicate",
}


def _stable_hash(*parts):
    raw = ":".join(str(part or "") for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _hash_float(*parts):
    value = int(_stable_hash(*parts)[:16], 16)
    return value / float(0xFFFFFFFFFFFFFFFF)


def _target_id(target):
    if not isinstance(target, dict):
        return ""
    return _clean(target.get("target_id") or target.get("id") or target.get("stable_id"))


def _coords(target):
    try:
        lat = float(target.get("lat"))
        lng = float(target.get("lng", target.get("lon")))
    except (AttributeError, TypeError, ValueError):
        return None
    if not (math.isfinite(lat) and math.isfinite(lng)):
        return None
    if lat < -90 or lat > 90 or lng < -180 or lng > 180:
        return None
    return lat, lng


def is_ghostnetwork_eligible_target(target):
    """Return a stable eligibility verdict for invisible GhostNetwork drops."""
    if not isinstance(target, dict):
        return {"eligible": False, "reason": "invalid_target", "target_id": ""}

    target_id = _target_id(target)
    if not target_id or "unknown" in target_id:
        return {"eligible": False, "reason": "missing_stable_target_id", "target_id": target_id}

    if _coords(target) is None:
        return {"eligible": False, "reason": "invalid_coordinates", "target_id": target_id}

    mode = _clean(target.get("target_mode")).lower()
    source_type = _clean(target.get("source_type") or target.get("candidate_source")).lower()
    if mode in BLOCKED_TARGET_MODES or source_type in BLOCKED_SOURCE_TYPES:
        return {"eligible": False, "reason": "blocked_target_family", "target_id": target_id}

    blocked_flags = (
        "is_player",
        "is_npc",
        "operation_id",
        "incident_id",
        "territory_id",
        "line_id",
        "ghost_part_id",
        "ghostnetwork_part_id",
        "technical_duplicate",
    )
    if any(target.get(key) for key in blocked_flags):
        return {"eligible": False, "reason": "blocked_target_marker", "target_id": target_id}

    if target.get("hackable") is False or target.get("can_hack") is False:
        return {"eligible": False, "reason": "not_hackable", "target_id": target_id}

    return {"eligible": True, "reason": "eligible", "target_id": target_id}


class GhostDropPolicy:
    """Deterministic reservation policy.

    Production defaults to disabled. Tests can pass enabled=True/chance=1.0
    without changing gameplay flags.
    """

    def __init__(self, enabled=None, chance=None, reservation_ttl_seconds=None):
        self.enabled = GHOSTNETWORK_DROPS_ENABLED if enabled is None else bool(enabled)
        self.chance = GHOSTNETWORK_DROP_CHANCE if chance is None else max(0.0, min(1.0, float(chance)))
        self.ttl_seconds = int(reservation_ttl_seconds or GHOSTNETWORK_RESERVATION_TTL_SECONDS)

    def should_attempt_reservation(self, player, target, cycle, context=None):
        if not self.enabled or self.chance <= 0:
            return False
        if self.chance >= 1:
            return True
        context = context if isinstance(context, dict) else {}
        player_id = _clean((player or {}).get("player_id") or (player or {}).get("username"))
        seed = (
            (cycle or {}).get("cycle_id"),
            player_id,
            _target_id(target),
            context.get("attempt_nonce") or "aim",
        )
        return _hash_float(*seed) < self.chance

    def choose_candidate(self, parts, player, target, cycle, context=None):
        context = context if isinstance(context, dict) else {}
        player_id = _clean((player or {}).get("player_id") or (player or {}).get("username"))
        seed = (
            (cycle or {}).get("cycle_id"),
            player_id,
            _target_id(target),
            context.get("attempt_nonce") or "aim",
        )
        candidates = list(parts or [])
        candidates.sort(key=lambda part: _stable_hash(*seed, part.get("part_id")))
        return candidates[0] if candidates else None


class GhostReservationService:
    """Invisible reservation workflow for Sprint 115.

    The service never mutates player profile state and never returns reservation
    details to public endpoints. It only records an internal candidate drop.
    """

    def __init__(self, repository, policy=None):
        self.repository = repository
        self.policy = policy or GhostDropPolicy()

    def on_target_aimed(self, player, target, context=None):
        context = context if isinstance(context, dict) else {}
        self.expire_due_reservations()

        cycle = self.repository.get_active_cycle()
        if not cycle:
            return {"ok": True, "status": "no_active_cycle"}
        cycle_id = cycle["cycle_id"]
        if cycle.get("status") != ACTIVE_CYCLE_STATUS:
            return {"ok": True, "status": "cycle_not_active", "cycle_id": cycle_id}

        eligibility = is_ghostnetwork_eligible_target(target)
        target_id = eligibility["target_id"]
        if not eligibility["eligible"]:
            return {"ok": True, "status": "not_eligible", "reason": eligibility["reason"], "cycle_id": cycle_id}

        emitted_part = self.repository.find_part_by_target(cycle_id, target_id)
        if emitted_part and emitted_part.get("status") != RESERVED_PART_STATUS:
            return {"ok": True, "status": "target_already_emitted", "cycle_id": cycle_id}

        player = player if isinstance(player, dict) else {}
        player_id = _clean(player.get("player_id") or player.get("username") or player.get("login"))
        if not player_id:
            return {"ok": True, "status": "missing_player_id", "cycle_id": cycle_id}

        existing = self.repository.get_active_reservation(cycle_id, target_id=target_id)
        if existing:
            if existing.get("player_id") == player_id:
                return {"ok": True, "status": "existing_reservation", "cycle_id": cycle_id}
            return {"ok": True, "status": "target_reserved", "cycle_id": cycle_id}

        identity = normalize_ghostnetwork_profile_identity(player)
        player_clan = _clean(identity.get("clan_code"))
        if not player_clan:
            return {"ok": True, "status": "missing_player_clan", "cycle_id": cycle_id}

        if not self.policy.should_attempt_reservation(player, target, cycle, context=context):
            return {"ok": True, "status": "roll_missed", "cycle_id": cycle_id}

        candidates = self.repository.list_reservable_parts(cycle_id, excluded_clan=player_clan)
        candidate = self.policy.choose_candidate(candidates, player, target, cycle, context=context)
        if not candidate:
            return {"ok": True, "status": "no_candidate_parts", "cycle_id": cycle_id}

        now_dt = datetime.fromisoformat(_iso(self.repository.now()).replace("Z", "+00:00"))
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        expires_at = _iso(now_dt)
        if self.policy.ttl_seconds > 0:
            expires_at = _iso(now_dt + timedelta(seconds=self.policy.ttl_seconds))
        reservation_id = "reservation_" + _stable_hash(cycle_id, candidate["part_id"], target_id, player_id)[:16]
        try:
            target_lat, target_lng = _coords(target)
            reservation = self.repository.create_reservation(
                cycle_id,
                candidate["part_id"],
                target_id,
                player_id,
                player_clan,
                reservation_id=reservation_id,
                expires_at=expires_at,
                latitude=target_lat,
                longitude=target_lng,
                min_distance_km=GHOSTNETWORK_MIN_PART_DISTANCE_KM,
            )
        except SpatialSeparationConflict:
            # Externally this is deliberately indistinguishable from a normal
            # unsuccessful roll.  The reason is for internal telemetry only.
            return {
                "ok": True,
                "status": "roll_missed",
                "cycle_id": cycle_id,
                "internal_reason": "part_too_close",
            }
        except ReservationConflict:
            return {"ok": True, "status": "reservation_conflict", "cycle_id": cycle_id}
        return {"ok": True, "status": "reserved", "cycle_id": cycle_id, "reservation_id": reservation["reservation_id"]}

    def attach_reservation_to_operation(self, player_id, target_id, operation_id):
        cycle = self.repository.get_active_cycle()
        if not cycle or cycle.get("status") != ACTIVE_CYCLE_STATUS:
            return {"ok": True, "status": "no_active_cycle"}
        reservation = self.repository.get_active_reservation(cycle["cycle_id"], target_id=target_id)
        if not reservation or reservation.get("player_id") != _clean(player_id):
            return {"ok": True, "status": "no_matching_reservation", "cycle_id": cycle["cycle_id"]}
        updated = self.repository.attach_reservation_to_operation(reservation["reservation_id"], operation_id)
        return {"ok": True, "status": "attached", "cycle_id": cycle["cycle_id"], "reservation_id": updated["reservation_id"]}

    def expire_due_reservations(self, now=None):
        expired = self.repository.expire_reservations(now=now)
        released = self.repository.release_inactive_cycle_reservations(reason="cycle_locked")
        return [*expired, *released]

    def release_reservation(self, reservation_id, reason):
        reason = _clean(reason)
        if reason not in RELEASE_REASONS:
            raise GhostNetworkError(f"Invalid reservation release reason: {reason}")
        return self.repository.release_reservation(reservation_id, reason=reason)

    def get_reservation_status(self):
        active = self.repository.get_active_cycle()
        cycle_id = (active or {}).get("cycle_id")
        return self.repository.get_reservation_status(cycle_id=cycle_id)
