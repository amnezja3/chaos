from __future__ import annotations

import copy
import hashlib
from datetime import datetime, timedelta, timezone

from database import DB_PATH, db_connect, dumps_json, loads_json


WARNING_STATUS_ACTIVE = "active"
WARNING_STATUS_CANCELLED = "cancelled"
WARNING_EVENT_ISSUED = "response_warning_issued"


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


def _warning_id(dedupe_key):
    digest = hashlib.sha1(_clean(dedupe_key, "warning").encode("utf-8")).hexdigest()[:16]
    return f"warning_{digest}"


def _operation_id(operation):
    return _clean((operation or {}).get("operation_id") or (operation or {}).get("id"))


def _operation_meter(operation):
    meter = (operation or {}).get("operation_risk_meter")
    return meter if isinstance(meter, dict) else {}


class ResponseWarningStore:
    """Domain store for visible-safe Response Network warnings.

    The warning is the source of truth. System messages are only a player-facing
    notification emitted after a warning event is recorded.
    """

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_warnings (
                    warning_id TEXT PRIMARY KEY,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    username TEXT NOT NULL DEFAULT '',
                    operation_id TEXT NOT NULL DEFAULT '',
                    incident_id TEXT NOT NULL DEFAULT '',
                    issued_at TEXT NOT NULL,
                    arrival_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    cancelled_at TEXT,
                    warning_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_warning_audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    warning_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_warnings_operation ON response_warnings(operation_id, status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_warnings_incident ON response_warnings(incident_id, status)"
            )

    @staticmethod
    def _row_to_warning(row):
        if not row:
            return None
        warning = loads_json(row["warning_json"], {}) or {}
        warning.update({
            "warning_id": row["warning_id"],
            "dedupe_key": row["dedupe_key"],
            "status": row["status"],
            "username": row["username"],
            "operation_id": row["operation_id"],
            "incident_id": row["incident_id"],
            "issued_at": row["issued_at"],
            "arrival_at": row["arrival_at"],
            "expires_at": row["expires_at"],
            "cancelled_at": row["cancelled_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })
        return warning

    def _audit(self, conn, warning_id, event_type, payload=None, created_at=None):
        conn.execute(
            """
            INSERT INTO response_warning_audit (warning_id, event_type, event_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                _clean(warning_id),
                _clean(event_type, "warning.audit"),
                dumps_json(payload if isinstance(payload, dict) else {}),
                _clean(created_at or _iso()),
            ),
        )

    def get(self, warning_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM response_warnings WHERE warning_id = ?",
                (_clean(warning_id),),
            ).fetchone()
            return self._row_to_warning(row)

    def get_by_operation(self, operation_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT * FROM response_warnings
                WHERE operation_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (_clean(operation_id),),
            ).fetchone()
            return self._row_to_warning(row)

    def issue_warning(self, username, operation, incident=None, now=None):
        operation = copy.deepcopy(operation if isinstance(operation, dict) else {})
        incident = incident if isinstance(incident, dict) else {}
        meter = _operation_meter(operation)
        operation_id = _operation_id(operation)
        if not username or not operation_id:
            return None, False

        risk_version = int(meter.get("risk_version") or meter.get("version") or 0)
        dedupe_key = _clean(
            meter.get("warning_dedupe_key"),
            f"response-warning:{username}:{operation_id}:{risk_version}",
        )
        warning_id = _warning_id(dedupe_key)
        issued_at_dt = _coerce_datetime(now)
        arrival_at_dt = issued_at_dt + timedelta(seconds=45)
        expires_at_dt = issued_at_dt + timedelta(minutes=12)
        now_iso = _iso(issued_at_dt)
        warning = {
            "schema": 1,
            "event_type": WARNING_EVENT_ISSUED,
            "warning_id": warning_id,
            "dedupe_key": dedupe_key,
            "status": WARNING_STATUS_ACTIVE,
            "mode": "visible_safe",
            "username": _clean(username),
            "operation_id": operation_id,
            "incident_id": _clean(meter.get("incident_id") or incident.get("incident_id")),
            "target_id": _clean(operation.get("target_id") or meter.get("target_id")),
            "heat": int(meter.get("current_heat") or 0),
            "risk_level": _clean(meter.get("risk_level"), "warning_threshold"),
            "issued_at": now_iso,
            "arrival_at": _iso(arrival_at_dt),
            "expires_at": _iso(expires_at_dt),
            "penalty_enabled": False,
            "consequence_enabled": False,
        }

        with db_connect(self.db_path) as conn:
            existing = conn.execute(
                "SELECT * FROM response_warnings WHERE dedupe_key = ? OR warning_id = ?",
                (dedupe_key, warning_id),
            ).fetchone()
            if existing:
                return self._row_to_warning(existing), False

            conn.execute(
                """
                INSERT INTO response_warnings (
                    warning_id, dedupe_key, status, username, operation_id, incident_id,
                    issued_at, arrival_at, expires_at, cancelled_at, warning_json,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
                """,
                (
                    warning_id,
                    dedupe_key,
                    WARNING_STATUS_ACTIVE,
                    _clean(username),
                    operation_id,
                    warning["incident_id"],
                    warning["issued_at"],
                    warning["arrival_at"],
                    warning["expires_at"],
                    dumps_json(warning),
                    now_iso,
                    now_iso,
                ),
            )
            self._audit(conn, warning_id, WARNING_EVENT_ISSUED, warning, created_at=now_iso)
            return copy.deepcopy(warning), True

    def cancel_for_operation(self, operation_id, reason="operation_cancelled", now=None):
        operation_id = _clean(operation_id)
        if not operation_id:
            return []
        return self._cancel_where("operation_id", operation_id, reason, now=now)

    def cancel_for_incident(self, incident_id, reason="incident_cancelled", now=None):
        incident_id = _clean(incident_id)
        if not incident_id:
            return []
        return self._cancel_where("incident_id", incident_id, reason, now=now)

    def _cancel_where(self, column, value, reason, now=None):
        now_iso = _iso(now)
        cancelled = []
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT * FROM response_warnings WHERE {column} = ? AND status = ?",
                (value, WARNING_STATUS_ACTIVE),
            ).fetchall()
            for row in rows:
                warning = self._row_to_warning(row)
                warning["status"] = WARNING_STATUS_CANCELLED
                warning["cancelled_at"] = now_iso
                warning["cancel_reason"] = _clean(reason, "cancelled")
                conn.execute(
                    """
                    UPDATE response_warnings
                    SET status = ?, cancelled_at = ?, warning_json = ?, updated_at = ?
                    WHERE warning_id = ?
                    """,
                    (
                        WARNING_STATUS_CANCELLED,
                        now_iso,
                        dumps_json(warning),
                        now_iso,
                        warning["warning_id"],
                    ),
                )
                self._audit(conn, warning["warning_id"], "response_warning_cancelled", warning, created_at=now_iso)
                cancelled.append(warning)
        return cancelled

    def recent(self, limit=50):
        try:
            limit = max(1, min(int(limit or 50), 200))
        except (TypeError, ValueError):
            limit = 50
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM response_warnings
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._row_to_warning(row) for row in rows]
