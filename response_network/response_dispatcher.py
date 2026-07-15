from __future__ import annotations

from datetime import datetime, timezone

from .npc_capsule_factory import NPCCapsuleFactory
from .npc_capsule_store import NPCCapsuleStore


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


def _coerce_datetime(value=None):
    if isinstance(value, datetime):
        dt = value
    elif value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _capsule_runtime_active(capsule, now=None):
    capsule = capsule if isinstance(capsule, dict) else {}
    if str(capsule.get("status") or "").strip().lower() not in {"active", "updated"}:
        return False
    try:
        expires_at = _coerce_datetime(capsule.get("expires_at"))
        return expires_at > _coerce_datetime(now)
    except (TypeError, ValueError):
        return False


class ResponseDispatcher:
    """Creates deterministic NPC capsule actions for active incidents.

    The dispatcher does not move NPCs and does not evaluate detection. It only
    issues complete behavior capsules that a later frontend runtime can replay.
    """

    def __init__(self, capsule_store=None, capsule_factory=None):
        self.capsule_store = capsule_store or NPCCapsuleStore()
        self.capsule_factory = capsule_factory or NPCCapsuleFactory()

    def dispatch_incident(self, incident, now=None):
        incident = incident if isinstance(incident, dict) else {}
        incident_id = _clean(incident.get("incident_id"))
        if not incident_id:
            return []
        if str(incident.get("status") or "").lower() in {"cancelled", "resolved", "archived"}:
            return self.cancel_incident(incident_id, now=now, reason="incident_not_active")

        expected = self.capsule_factory.build_for_incident(incident, now=now)
        expected_ids = {capsule.get("capsule_id") for capsule in expected if capsule.get("capsule_id")}
        actions = []

        for capsule in expected:
            existing = self.capsule_store.get(capsule.get("capsule_id"))
            if existing and _capsule_runtime_active(existing, now=now):
                capsule["spawn_at"] = existing.get("spawn_at") or capsule.get("spawn_at")
                capsule["expires_at"] = existing.get("expires_at") or capsule.get("expires_at")
                capsule["warning_until"] = existing.get("warning_until") or capsule.get("warning_until")
            saved, changed = self.capsule_store.upsert(capsule, now=now)
            if not changed:
                continue
            actions.append({
                "action": "updated" if existing else "spawned",
                "capsule_id": saved.get("capsule_id"),
                "incident_id": incident_id,
                "capsule": saved,
            })

        for capsule in self.capsule_store.list_by_incident(incident_id):
            capsule_id = capsule.get("capsule_id")
            if capsule_id in expected_ids:
                continue
            removed, changed = self.capsule_store.upsert({
                **capsule,
                "status": "removed",
                "removed_reason": "dispatcher_superseded",
            }, now=now)
            if changed:
                actions.append({
                    "action": "removed",
                    "capsule_id": removed.get("capsule_id"),
                    "incident_id": incident_id,
                    "capsule": removed,
                })

        return actions

    def cancel_incident(self, incident_id, now=None, reason="incident_resolved"):
        actions = []
        for capsule in self.capsule_store.remove_incident(incident_id, now=now, reason=reason):
            actions.append({
                "action": "removed",
                "capsule_id": capsule.get("capsule_id"),
                "incident_id": incident_id,
                "capsule": capsule,
            })
        return actions
