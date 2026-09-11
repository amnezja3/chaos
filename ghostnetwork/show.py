from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from config import GHOSTNETWORK_SIGNAL_SHOW_POLICY

from .repository import GhostNetworkRepository, _clean
from database import ProfilePrecommitRejected


class GhostGameplayLocked(ProfilePrecommitRejected):
    def __init__(self, state):
        super().__init__("Gameplay is locked by GhostSignal.")
        self.state = state


PHASES = (
    ("network_lock", "NETWORK LOCK", 0, 8),
    ("machine_synchronization", "MACHINE SYNCHRONIZATION", 8, 22),
    ("signal_transmission", "SIGNAL TRANSMISSION", 22, 42),
    ("world_consumption", "WORLD CONSUMPTION / ARCHIVE", 42, 62),
    ("results", "RESULTS / REWARDS", 62, 80),
    ("ghostsystem_restart", "GHOSTSYSTEM RESTART / BOOT vNEXT", 80, 100),
)


def _parse_iso(value):
    text = _clean(value)
    if not text:
        return None
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _version_text(value):
    return f"1.0.{int(value or 0)}"


class GhostSignalShowService:
    """Durable, server-clock projection of the one global signal show."""

    def __init__(self, repository=None, policy=None):
        self.repository = repository or GhostNetworkRepository()
        self.policy = dict(GHOSTNETWORK_SIGNAL_SHOW_POLICY)
        self.policy.update(policy or {})

    def gameplay_lock(self, conn=None):
        state = self.repository.get_gameplay_lock(conn=conn)
        if not state:
            return {"gameplay_locked": False}
        return {"gameplay_locked": True, "show_active": True,
                "cycle_id": state["cycle_id"], "cycle_status": state["cycle_status"],
                "cycle_number": state["signal_number"], "state_version": state["state_version"],
                "signal_public_id": state.get("signal_public_id"),
                "show_started_at": state.get("show_started_at") or state.get("locked_at"),
                "show_ends_at": state.get("show_ends_at") or state.get("stabilization_until") or None,
                "stabilization_until": state.get("stabilization_until") or None,
                "refresh_url": "/api/ghostnetwork/show"}

    def assert_gameplay_unlocked(self, conn):
        # Read COMMITTED authority through a separate reader while the caller
        # holds SQLite's writer lock. The transaction creating T0 must not
        # reject its own uncommitted cycle transition. A later writer sees T0
        # and rolls back. Ancillary stores also consult the canonical database.
        reader = GhostSignalShowService(GhostNetworkRepository(
            db_path=self.repository.db_path, ensure_schema=False))
        state = reader.gameplay_lock()
        if state["gameplay_locked"]:
            raise GhostGameplayLocked(state)

    def get_for_viewer(self):
        # No schema init or heavy facade construction on the polling path.
        active = self.repository.get_active_cycle()
        if active:
            cycle_id = active["cycle_id"]
            projection = self.projection_for_cycle(cycle_id)
            if active.get("status") == "transmitting" and not projection.get("signal_public_id"):
                from .transmission import GhostTransmissionService
                GhostTransmissionService(self.repository).prepare_transmission(cycle_id)
                projection = self.projection_for_cycle(cycle_id)
            elif active.get("status") == "stabilizing" and not projection.get("signal_public_id"):
                signal = self.repository.get_signal_for_cycle(cycle_id)
                if signal:
                    self.ensure_for_signal(signal, cycle=active,
                        started_at=signal.get("sent_at"), ends_at=active.get("stabilization_until") or None)
                    projection = self.projection_for_cycle(cycle_id)
            projection.update({"cycle_id": cycle_id, "cycle_number": active.get("signal_number"),
                "state_version": active.get("state_version", 0),
                "restart_required": bool(active.get("restart_required")),
                "upgrade_pending": bool(active.get("upgrade_pending")),
                "current_version": active.get("source_version") or None,
                "next_version": active.get("next_version") or None})
        else:
            projection = {"show_active": False}
        lock = self.gameplay_lock()
        projection.update(lock)
        if not projection.get("show_active"):
            latest = self.repository.get_latest_signal_show()
            if latest and latest.get("status") == "completed":
                projection.update({"completed": True,
                    "last_completed_signal_public_id": latest.get("signal_public_id"),
                    "last_completed_from_system_version": latest.get("from_system_version"),
                    "last_completed_to_system_version": latest.get("to_system_version")})
        projection["server_now"] = self.repository.now()
        projection["client_restart"] = self.restart_projection()
        return projection

    def restart_projection(self):
        event = self.repository.get_client_restart()
        if not event:
            return None
        payload = event.get("payload") or {}
        return {key: payload.get(key) for key in (
            "epoch", "signal_public_id", "closed_cycle_id", "next_cycle_id", "next_cycle_number", "to_system_version")}

    def publish_client_restart(self, closed_cycle, next_cycle):
        """Called inside the validated, atomic rollover transaction."""
        show = self.repository.get_signal_show_for_cycle(closed_cycle["cycle_id"])
        if not show or show.get("status") != "completed" or next_cycle.get("status") != "active":
            raise ValueError("Client restart requires completed show and active successor")
        epoch = hashlib.sha256((show["show_id"] + ":" + next_cycle["cycle_id"]).encode()).hexdigest()
        return self.repository.append_event("ghost.client_restart_required",
            cycle_id=closed_cycle["cycle_id"], entity_id=show["signal_public_id"],
            dedupe_key="ghost:client_restart_required:" + show["signal_id"],
            audience_scope="public", payload={"epoch": epoch,
                "signal_public_id": show["signal_public_id"],
                "closed_cycle_id": closed_cycle["cycle_id"],
                "next_cycle_id": next_cycle["cycle_id"],
                "next_cycle_number": next_cycle["signal_number"],
                "to_system_version": show["to_system_version"]})

    def deliver_start_to_viewer(self, delta_bus, username):
        """Project the committed start into the existing per-user delta feed.

        The requesting viewer is the only recipient; no worker/fan-out is on
        this path. The normal delivery job shares the same dedupe key.
        """
        event = self.repository.get_latest_show_start_event()
        if not event:
            return None
        payload = event.get("payload") or {}
        safe = {key: payload.get(key) for key in (
            "signal_public_id", "show_started_at", "show_ends_at",
            "from_system_version", "to_system_version")}
        safe.update({"cycle_id": event["cycle_id"], "state_version": event["state_version"],
                     "refresh_url": "/api/ghostnetwork/show"})
        return delta_bus.record_change(username, "ghostnetwork", "ghost.signal_show_started",
            payload=safe, entity_id=payload.get("signal_public_id"),
            dedupe_key=f"ghostnetwork:{username}:{event['dedupe_key']}", created_at=event.get("created_at"))

    def ensure_for_signal(self, signal, cycle=None, started_at=None, ends_at=None):
        signal = signal if isinstance(signal, dict) else {}
        cycle = cycle or self.repository.get_cycle(signal.get("cycle_id")) or {}
        existing = self.repository.get_signal_show_for_signal(signal.get("signal_id"))
        if existing:
            existing["idempotent"] = True
            return existing
        start = _parse_iso(started_at or signal.get("sent_at") or self.repository.now())
        duration = max(60, int(self.policy.get("duration_seconds") or 900))
        finish = _parse_iso(ends_at) or (start + timedelta(seconds=duration))
        signal_number = int(signal.get("signal_number") or cycle.get("signal_number") or 0)
        public_id = f"GHOSTSIGNAL-{signal_number:04d}"
        show_id = "ghost_show_" + hashlib.sha1(
            str(signal.get("signal_id") or "").encode("utf-8")
        ).hexdigest()[:20]
        return self.repository.create_signal_show({
            "show_id": show_id,
            "signal_id": signal.get("signal_id"),
            "cycle_id": signal.get("cycle_id"),
            "signal_public_id": public_id,
            "show_started_at": start.isoformat(),
            "show_ends_at": finish.isoformat(),
            "from_system_version": cycle.get("source_version") or _version_text(signal.get("source_version")),
            "to_system_version": cycle.get("next_version") or _version_text(signal.get("next_version")),
            "phase_policy_version": self.policy.get("phase_policy_version") or "ghostsignal-show-v1",
            "status": "active",
        })

    def phase_at(self, show, now=None):
        show = show if isinstance(show, dict) else {}
        current = _parse_iso(now or self.repository.now()) or datetime.now(timezone.utc)
        start = _parse_iso(show.get("show_started_at"))
        end = _parse_iso(show.get("show_ends_at"))
        if not start or not end or end <= start:
            return {"code": "unavailable", "label": "SIGNAL SHOW", "index": 0,
                    "progress_percent": 0, "elapsed_seconds": 0, "remaining_seconds": 0}
        duration = max(1.0, (end - start).total_seconds())
        elapsed = max(0.0, (current - start).total_seconds())
        overall = min(100.0, elapsed * 100.0 / duration)
        selected = PHASES[-1]
        for phase in PHASES:
            if overall < phase[3]:
                selected = phase
                break
        low, high = selected[2], selected[3]
        phase_progress = min(100.0, max(0.0, (overall - low) * 100.0 / max(1, high - low)))
        return {
            "code": selected[0], "label": selected[1], "index": PHASES.index(selected) + 1,
            "progress_percent": int(round(phase_progress)),
            "overall_percent": int(round(overall)),
            "elapsed_seconds": int(elapsed),
            "remaining_seconds": max(0, int((end - current).total_seconds())),
        }

    def projection_for_cycle(self, cycle_id, now=None):
        show = self.repository.get_signal_show_for_cycle(cycle_id)
        if not show:
            return {"show_active": False}
        current = _parse_iso(now or self.repository.now()) or datetime.now(timezone.utc)
        end = _parse_iso(show.get("show_ends_at"))
        elapsed = bool(end and current >= end)
        active = show.get("status") == "active"
        phase = self.phase_at(show, now=current)
        return {
            "show_active": active,
            "show_time_elapsed": elapsed,
            "signal_public_id": show.get("signal_public_id") or None,
            "show_started_at": show.get("show_started_at") or None,
            "show_ends_at": show.get("show_ends_at") or None,
            "server_now": current.isoformat(),
            "show_phase": phase,
            "from_system_version": show.get("from_system_version") or None,
            "to_system_version": show.get("to_system_version") or None,
            "phase_policy_version": show.get("phase_policy_version") or None,
            "upgrade_pending": show.get("status") == "active",
        }

    def complete_for_cycle(self, cycle_id):
        show = self.repository.get_signal_show_for_cycle(cycle_id)
        if not show or show.get("status") == "completed":
            return show
        return self.repository.update_signal_show(show["show_id"], status="completed")
