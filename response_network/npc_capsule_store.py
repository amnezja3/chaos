from __future__ import annotations

import copy
from datetime import datetime, timezone

from database import DB_PATH, db_connect, dumps_json, loads_json

from .npc_capsule_factory import capsule_signature, public_capsule_payload


ACTIVE_CAPSULE_STATUSES = {"active", "updated"}
REMOVED_CAPSULE_STATUSES = {"removed", "expired", "cancelled"}


def _utc_now():
    return datetime.now(timezone.utc)


def _coerce_datetime(value=None):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
    elif value:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    else:
        dt = _utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _iso(value=None):
    return _coerce_datetime(value).isoformat()


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


class NPCCapsuleStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_npc_capsules (
                    capsule_id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'active',
                    spawn_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    capsule_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_npc_capsules_incident ON response_npc_capsules(incident_id, status)"
            )

    @staticmethod
    def _row_to_capsule(row):
        if not row:
            return None
        capsule = loads_json(row["capsule_json"], {}) or {}
        capsule.update({
            "capsule_id": row["capsule_id"],
            "incident_id": row["incident_id"],
            "version": int(row["version"] or 0),
            "status": row["status"],
            "spawn_at": row["spawn_at"],
            "expires_at": row["expires_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
        return capsule

    def get(self, capsule_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM response_npc_capsules WHERE capsule_id = ?",
                (_clean(capsule_id),),
            ).fetchone()
            return self._row_to_capsule(row)

    def list_active(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM response_npc_capsules
                WHERE status IN ('active', 'updated')
                ORDER BY updated_at DESC
                """
            ).fetchall()
            return [self._row_to_capsule(row) for row in rows]

    def list_public(self):
        return [
            public_capsule_payload(capsule)
            for capsule in self.list_active()
            if capsule and capsule.get("incident_id") and capsule.get("capsule_id")
        ]

    def list_by_incident(self, incident_id, include_removed=False):
        incident_id = _clean(incident_id)
        if not incident_id:
            return []
        where = "incident_id = ?"
        params = [incident_id]
        if not include_removed:
            where += " AND status IN ('active', 'updated')"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT * FROM response_npc_capsules WHERE {where} ORDER BY capsule_id ASC",
                params,
            ).fetchall()
            return [self._row_to_capsule(row) for row in rows]

    def upsert(self, capsule, now=None):
        capsule = copy.deepcopy(capsule if isinstance(capsule, dict) else {})
        capsule_id = _clean(capsule.get("capsule_id"))
        incident_id = _clean(capsule.get("incident_id"))
        if not capsule_id or not incident_id:
            raise ValueError("NPC capsule requires capsule_id and incident_id.")
        now_iso = _iso(now)
        spawn_at = _clean(capsule.get("spawn_at") or now_iso)
        expires_at = _clean(capsule.get("expires_at") or now_iso)
        status = _clean(capsule.get("status"), "active")

        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM response_npc_capsules WHERE capsule_id = ?",
                (capsule_id,),
            ).fetchone()
            if row:
                existing = self._row_to_capsule(row)
                if capsule_signature(existing) == capsule_signature(capsule) and existing.get("status") == status:
                    return existing, False
                version = int(existing.get("version") or 0) + 1
                created_at = existing.get("created_at") or now_iso
            else:
                version = int(capsule.get("version") or 1)
                created_at = now_iso

            capsule["version"] = version
            capsule["status"] = status
            capsule["created_at"] = created_at
            capsule["updated_at"] = now_iso

            conn.execute(
                """
                INSERT INTO response_npc_capsules (
                    capsule_id, incident_id, version, status, spawn_at, expires_at,
                    capsule_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(capsule_id) DO UPDATE SET
                    incident_id = excluded.incident_id,
                    version = excluded.version,
                    status = excluded.status,
                    spawn_at = excluded.spawn_at,
                    expires_at = excluded.expires_at,
                    capsule_json = excluded.capsule_json,
                    updated_at = excluded.updated_at
                """,
                (
                    capsule_id,
                    incident_id,
                    version,
                    status,
                    spawn_at,
                    expires_at,
                    dumps_json(capsule),
                    created_at,
                    now_iso,
                ),
            )
            return copy.deepcopy(capsule), True

    def remove_incident(self, incident_id, now=None, reason="incident_resolved"):
        removed = []
        now_iso = _iso(now)
        for capsule in self.list_by_incident(incident_id):
            if capsule.get("status") in REMOVED_CAPSULE_STATUSES:
                continue
            capsule["status"] = "removed"
            capsule["removed_reason"] = _clean(reason, "removed")
            capsule["expires_at"] = now_iso
            saved, changed = self.upsert(capsule, now=now_iso)
            if changed:
                removed.append(saved)
        return removed
