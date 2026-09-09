from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from config import GHOSTNETWORK_SIGNAL_SHOW_POLICY

from .repository import GhostNetworkRepository, _clean


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
