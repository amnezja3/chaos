from __future__ import annotations

import copy
from datetime import datetime, timezone

from database import DB_PATH, db_connect, dumps_json, loads_json


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


class DetectionCandidateStore:
    """Audit-only store for local detection feedback.

    The store records client feedback and backend validation decisions. It does
    not publish warnings, penalties, or gameplay consequences.
    """

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_detection_candidates (
                    candidate_id TEXT PRIMARY KEY,
                    validation_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    mode TEXT NOT NULL DEFAULT 'shadow',
                    incident_id TEXT NOT NULL DEFAULT '',
                    capsule_id TEXT NOT NULL DEFAULT '',
                    actor_id TEXT NOT NULL DEFAULT '',
                    operation_id TEXT NOT NULL DEFAULT '',
                    candidate_json TEXT NOT NULL DEFAULT '{}',
                    decision_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_detection_candidate_audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    candidate_id TEXT NOT NULL,
                    validation_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    event_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_response_detection_validation_key ON response_detection_candidates(validation_key)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_detection_incident ON response_detection_candidates(incident_id, updated_at)"
            )

    @staticmethod
    def _row_to_item(row):
        if not row:
            return None
        item = loads_json(row["candidate_json"], {}) or {}
        item.update({
            "candidate_id": row["candidate_id"],
            "validation_key": row["validation_key"],
            "status": row["status"],
            "mode": row["mode"],
            "incident_id": row["incident_id"],
            "capsule_id": row["capsule_id"],
            "actor_id": row["actor_id"],
            "operation_id": row["operation_id"],
            "decision": loads_json(row["decision_json"], {}),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
        return item

    def get(self, candidate_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM response_detection_candidates WHERE candidate_id = ?",
                (_clean(candidate_id),),
            ).fetchone()
            return self._row_to_item(row)

    def get_by_validation_key(self, validation_key):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM response_detection_candidates WHERE validation_key = ?",
                (_clean(validation_key),),
            ).fetchone()
            return self._row_to_item(row)

    def record(self, candidate, decision, now=None):
        candidate = copy.deepcopy(candidate if isinstance(candidate, dict) else {})
        decision = copy.deepcopy(decision if isinstance(decision, dict) else {})
        candidate_id = _clean(candidate.get("candidate_id"))
        validation_key = _clean(decision.get("validation_key") or candidate.get("validation_key"))
        if not candidate_id:
            raise ValueError("Detection candidate requires candidate_id.")
        if not validation_key:
            raise ValueError("Detection candidate requires validation_key.")

        now_iso = _iso(now)
        status = _clean(decision.get("status") or decision.get("result"), "rejected")
        mode = _clean(decision.get("mode") or candidate.get("mode"), "shadow")
        incident_id = _clean(candidate.get("incident_id") or decision.get("incident_id"))
        capsule_id = _clean(candidate.get("capsule_id") or candidate.get("npc_id") or decision.get("capsule_id"))
        actor_id = _clean(candidate.get("actor_id") or decision.get("actor_id"))
        operation_id = _clean(candidate.get("operation_id") or decision.get("operation_id"))

        with db_connect(self.db_path) as conn:
            existing = conn.execute(
                """
                SELECT * FROM response_detection_candidates
                WHERE validation_key = ? OR candidate_id = ?
                """,
                (validation_key, candidate_id),
            ).fetchone()
            if existing:
                existing_item = self._row_to_item(existing)
                duplicate_decision = copy.deepcopy(decision)
                duplicate_decision["status"] = "duplicate"
                duplicate_decision["result"] = "duplicate"
                duplicate_decision["duplicate_of"] = existing_item.get("candidate_id")
                conn.execute(
                    """
                    INSERT INTO response_detection_candidate_audit (
                        candidate_id, validation_key, status, event_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        candidate_id,
                        validation_key,
                        "duplicate",
                        dumps_json({"candidate": candidate, "decision": duplicate_decision}),
                        now_iso,
                    ),
                )
                existing_item["decision"] = duplicate_decision
                existing_item["status"] = "duplicate"
                return existing_item, False

            conn.execute(
                """
                INSERT INTO response_detection_candidates (
                    candidate_id, validation_key, status, mode, incident_id, capsule_id,
                    actor_id, operation_id, candidate_json, decision_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    validation_key,
                    status,
                    mode,
                    incident_id,
                    capsule_id,
                    actor_id,
                    operation_id,
                    dumps_json(candidate),
                    dumps_json(decision),
                    now_iso,
                    now_iso,
                ),
            )
            conn.execute(
                """
                INSERT INTO response_detection_candidate_audit (
                    candidate_id, validation_key, status, event_json, created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    candidate_id,
                    validation_key,
                    status,
                    dumps_json({"candidate": candidate, "decision": decision}),
                    now_iso,
                ),
            )
            return self.get(candidate_id), True

    def recent(self, limit=50):
        try:
            limit = max(1, min(int(limit or 50), 200))
        except (TypeError, ValueError):
            limit = 50
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM response_detection_candidates
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._row_to_item(row) for row in rows]
