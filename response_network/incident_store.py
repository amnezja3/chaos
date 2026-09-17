from __future__ import annotations

import copy
import hashlib
import json
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone

from database import DB_PATH, db_connect, dumps_json, loads_json


ACTIVE_INCIDENT_STATUSES = {"candidate", "active", "escalated", "cooling"}
CANCELLED_INCIDENT_STATUSES = {"cancelled", "resolved", "archived"}


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(value=None):
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
    return dt.astimezone(timezone.utc).isoformat()


def _clean(value, default=""):
    text = str(value or "").strip()
    return text or default


class IncidentStore:
    """Minimal invisible incident store for Response Network.

    It stores incidents and audit/replay data only. It does not publish map
    layers, NPC capsules, warnings or consequences.
    """

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._ensure_schema()

    def _ensure_schema(self):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_incidents (
                    incident_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 1,
                    heat INTEGER NOT NULL DEFAULT 0,
                    center_lat REAL,
                    center_lng REAL,
                    search_radius_m INTEGER NOT NULL DEFAULT 0,
                    operation_ids_json TEXT NOT NULL DEFAULT '[]',
                    suspect_refs_json TEXT NOT NULL DEFAULT '[]',
                    territory_refs_json TEXT NOT NULL DEFAULT '[]',
                    npc_capsule_ids_json TEXT NOT NULL DEFAULT '[]',
                    seed TEXT NOT NULL DEFAULT '',
                    last_event_seq INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    incident_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS response_incident_audit (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    incident_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_incidents_status ON response_incidents(status, updated_at)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_response_incident_audit_incident ON response_incident_audit(incident_id, seq)"
            )
            conn.execute('''CREATE TABLE IF NOT EXISTS response_incident_publications (
                incident_id TEXT PRIMARY KEY, version INTEGER NOT NULL,
                delivered_version INTEGER NOT NULL DEFAULT 0,
                batch_version INTEGER NOT NULL DEFAULT 0,
                viewer_cursor TEXT NOT NULL DEFAULT '', lease_until TEXT,
                lease_token TEXT, updated_at TEXT NOT NULL)''')
            conn.execute('''CREATE INDEX IF NOT EXISTS idx_incident_publication_pending
                ON response_incident_publications(updated_at, incident_id) WHERE version>delivered_version''')
            conn.execute('''CREATE TABLE IF NOT EXISTS response_incident_members (
                operation_id TEXT PRIMARY KEY, incident_id TEXT NOT NULL)''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_incident_members_incident ON response_incident_members(incident_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_incident_center ON response_incidents(status, center_lat, center_lng)')

    @staticmethod
    def stable_id(center, operation_id):
        lat = round(float((center or {}).get("lat") or 0), 4)
        lng = round(float((center or {}).get("lng") or 0), 4)
        digest = hashlib.sha1(f"{lat}:{lng}:{operation_id}".encode("utf-8")).hexdigest()[:12]
        return f"incident_{digest}"

    @staticmethod
    def _row_to_incident(row):
        if not row:
            return None
        incident = loads_json(row["incident_json"], {}) or {}
        incident.update({
            "incident_id": row["incident_id"],
            "version": int(row["version"] or 0),
            "status": row["status"],
            "level": int(row["level"] or 1),
            "heat": int(row["heat"] or 0),
            "center": {
                "lat": row["center_lat"],
                "lng": row["center_lng"],
            },
            "search_radius_m": int(row["search_radius_m"] or 0),
            "operation_ids": loads_json(row["operation_ids_json"], []),
            "suspect_refs": loads_json(row["suspect_refs_json"], []),
            "territory_refs": loads_json(row["territory_refs_json"], []),
            "npc_capsule_ids": loads_json(row["npc_capsule_ids_json"], []),
            "seed": row["seed"],
            "last_event_seq": int(row["last_event_seq"] or 0),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "expires_at": row["expires_at"],
        })
        return incident

    def _audit(self, conn, incident_id, event_type, payload=None, created_at=None):
        payload = payload if isinstance(payload, dict) else {}
        created_at = _clean(created_at or _iso())
        cursor = conn.execute(
            """
            INSERT INTO response_incident_audit (incident_id, event_type, event_json, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (incident_id, _clean(event_type, "incident.audit"), dumps_json(payload), created_at),
        )
        return int(cursor.lastrowid)

    @staticmethod
    def _signature(incident):
        incident = incident if isinstance(incident, dict) else {}
        center = incident.get("center") if isinstance(incident.get("center"), dict) else {}
        return {
            "status": incident.get("status"),
            "level": int(incident.get("level") or 0),
            "heat": int(incident.get("heat") or 0),
            "center": {
                "lat": center.get("lat"),
                "lng": center.get("lng"),
            },
            "search_radius_m": int(incident.get("search_radius_m") or 0),
            "operation_ids": sorted(str(item) for item in (incident.get("operation_ids") or [])),
            "operation_refs": sorted(incident.get('operation_refs') or [],
                                     key=lambda ref: ref.get('operation_id', '')),
            "suspect_refs": incident.get("suspect_refs") or [],
            "territory_refs": incident.get("territory_refs") or [],
            "npc_capsule_ids": incident.get("npc_capsule_ids") or [],
            "cooling_since": incident.get('cooling_since'),
            "expires_at": incident.get('expires_at') if incident.get('status') == 'cooling' else None,
        }

    def get(self, incident_id, *, conn=None):
        with (db_connect(self.db_path) if conn is None else nullcontext(conn)) as conn:
            row = conn.execute(
                "SELECT * FROM response_incidents WHERE incident_id = ?",
                (_clean(incident_id),),
            ).fetchone()
            return self._row_to_incident(row)

    def list_active(self, limit=256, *, conn=None):
        with (db_connect(self.db_path) if conn is None else nullcontext(conn)) as conn:
            rows = conn.execute(
                """
                SELECT * FROM response_incidents
                WHERE status IN ('candidate', 'active', 'escalated', 'cooling')
                ORDER BY updated_at DESC
                LIMIT ?
                """, (max(1, min(int(limit), 256)),)
            ).fetchall()
            return [self._row_to_incident(row) for row in rows]

    def related(self, operations, *, conn):
        """Indexed membership/ID and bounded spatial candidates; no world scan."""
        found = {}
        for op in operations:
            assigned = (op.get('operation_risk_meter') or {}).get('incident_id')
            rows = conn.execute('''SELECT i.* FROM response_incidents i
                WHERE i.incident_id=? OR i.incident_id IN
                (SELECT incident_id FROM response_incident_members WHERE operation_id=?)''',
                (assigned or '', op.get('operation_id') or '')).fetchall()
            meter = op.get('operation_risk_meter') or {}
            position = meter.get('position') or op.get('target') or {}
            if meter.get('incident_crossed') and position.get('lat') is not None:
                lat, lng = float(position['lat']), float(position.get('lng', position.get('lon')))
                rows += conn.execute('''SELECT * FROM response_incidents
                    WHERE status IN ('candidate','active','escalated','cooling')
                    AND center_lat BETWEEN ? AND ? AND center_lng BETWEEN ? AND ?
                    ORDER BY updated_at DESC LIMIT 32''',
                    (lat - .003, lat + .003, lng - .1, lng + .1)).fetchall()
            for row in rows:
                item = self._row_to_incident(row)
                if item['status'] in ACTIVE_INCIDENT_STATUSES:
                    found[item['incident_id']] = item
        return list(found.values())

    def lifecycle_batch(self, limit=32):
        with db_connect(self.db_path) as conn:
            rows = conn.execute('''SELECT * FROM response_incidents
                WHERE status IN ('candidate','active','escalated','cooling')
                ORDER BY updated_at, incident_id LIMIT ?''', (max(1, min(limit, 64)),)).fetchall()
        return [self._row_to_incident(row) for row in rows]

    @staticmethod
    def public_payload(incident):
        incident = incident if isinstance(incident, dict) else {}
        center = incident.get("center") if isinstance(incident.get("center"), dict) else {}
        incident_id = _clean(incident.get("incident_id"))
        status = _clean(incident.get("status"), "active")
        if status in CANCELLED_INCIDENT_STATUSES:
            status = "resolved"
        return {
            "incident_id": incident_id,
            "version": int(incident.get("version") or 0),
            "publication_version": int(incident.get('publication_version') or 0),
            "status": status,
            "level": int(incident.get("level") or 0),
            "center": {
                "lat": center.get("lat"),
                "lng": center.get("lng"),
            },
            "search_radius_m": int(incident.get("search_radius_m") or 0),
            "updated_at": incident.get("updated_at"),
            "expires_at": incident.get("expires_at") if status in {'cooling', 'resolved'} else None,
        }

    def list_public(self, now=None, limit=256):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT * FROM response_incidents
                WHERE status IN ('candidate', 'active', 'escalated', 'cooling')
                  AND (status != 'cooling' OR julianday(expires_at) > julianday(?))
                ORDER BY level DESC, updated_at DESC
                LIMIT ?
                """, (_iso(now), max(1, min(int(limit), 256)))
            ).fetchall()
            incidents = []
            for row in rows:
                payload = self.public_payload(self._row_to_incident(row))
                center = payload.get("center") or {}
                if center.get("lat") is None or center.get("lng") is None:
                    continue
                incidents.append(payload)
            return incidents

    def upsert(self, incident, event_type="incident.updated", now=None, *, conn=None):
        incident = copy.deepcopy(incident if isinstance(incident, dict) else {})
        incident_id = _clean(incident.get("incident_id"))
        if not incident_id:
            raise ValueError("Incident requires incident_id.")
        now_iso = _iso(now)
        created_at = _clean(incident.get("created_at") or now_iso)
        updated_at = now_iso
        expires_at = _clean(incident.get("expires_at") or _iso(_utc_now() + timedelta(minutes=30)))
        center = incident.get("center") if isinstance(incident.get("center"), dict) else {}
        operation_ids = list(dict.fromkeys(str(item) for item in (incident.get("operation_ids") or []) if str(item)))
        suspect_refs = incident.get("suspect_refs") if isinstance(incident.get("suspect_refs"), list) else []
        territory_refs = incident.get("territory_refs") if isinstance(incident.get("territory_refs"), list) else []
        npc_capsule_ids = incident.get("npc_capsule_ids") if isinstance(incident.get("npc_capsule_ids"), list) else []

        own_connection = conn is None
        with (db_connect(self.db_path) if own_connection else nullcontext(conn)) as conn:
            if own_connection:
                conn.execute('BEGIN IMMEDIATE')
            existing = conn.execute(
                "SELECT * FROM response_incidents WHERE incident_id = ?",
                (incident_id,),
            ).fetchone()
            if existing:
                existing_incident = self._row_to_incident(existing)
                if self._signature(existing_incident) == self._signature(incident):
                    conn.execute('''INSERT OR IGNORE INTO response_incident_publications
                        (incident_id,version,updated_at) VALUES (?,?,?)''',
                        (incident_id, existing_incident['version'], now_iso))
                    conn.executemany('INSERT OR IGNORE INTO response_incident_members(operation_id,incident_id) VALUES (?,?)',
                                     [(op_id, incident_id) for op_id in operation_ids])
                    return existing_incident
                version = int(existing_incident.get("version") or 0) + 1
                created_at = existing_incident.get("created_at") or created_at
            else:
                version = int(incident.get("version") or 1)

            incident["version"] = version
            public_fields = ('status', 'level', 'center', 'search_radius_m')
            previous_public = existing_incident if existing else {}
            public_changed = any(previous_public.get(key) != incident.get(key) for key in public_fields)
            incident['publication_version'] = int(previous_public.get('publication_version') or 0) + int(public_changed)
            incident["created_at"] = created_at
            incident["updated_at"] = updated_at
            incident["expires_at"] = expires_at
            event_seq = self._audit(conn, incident_id, event_type, incident, created_at=updated_at)
            incident["last_event_seq"] = event_seq

            conn.execute(
                """
                INSERT INTO response_incidents (
                    incident_id, version, status, level, heat, center_lat, center_lng,
                    search_radius_m, operation_ids_json, suspect_refs_json,
                    territory_refs_json, npc_capsule_ids_json, seed, last_event_seq,
                    created_at, updated_at, expires_at, incident_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    version = excluded.version,
                    status = excluded.status,
                    level = excluded.level,
                    heat = excluded.heat,
                    center_lat = excluded.center_lat,
                    center_lng = excluded.center_lng,
                    search_radius_m = excluded.search_radius_m,
                    operation_ids_json = excluded.operation_ids_json,
                    suspect_refs_json = excluded.suspect_refs_json,
                    territory_refs_json = excluded.territory_refs_json,
                    npc_capsule_ids_json = excluded.npc_capsule_ids_json,
                    seed = excluded.seed,
                    last_event_seq = excluded.last_event_seq,
                    updated_at = excluded.updated_at,
                    expires_at = excluded.expires_at,
                    incident_json = excluded.incident_json
                """,
                (
                    incident_id,
                    version,
                    _clean(incident.get("status"), "candidate"),
                    int(incident.get("level") or 1),
                    int(incident.get("heat") or 0),
                    center.get("lat"),
                    center.get("lng"),
                    int(incident.get("search_radius_m") or 0),
                    dumps_json(operation_ids),
                    dumps_json(suspect_refs),
                    dumps_json(territory_refs),
                    dumps_json(npc_capsule_ids),
                    _clean(incident.get("seed") or incident_id),
                    event_seq,
                    created_at,
                    updated_at,
                    expires_at,
                    dumps_json(incident),
                ),
            )
            conn.execute('DELETE FROM response_incident_members WHERE incident_id=?', (incident_id,))
            conn.executemany('INSERT OR REPLACE INTO response_incident_members(operation_id,incident_id) VALUES (?,?)',
                             [(op_id, incident_id) for op_id in operation_ids])
            conn.execute('''INSERT INTO response_incident_publications(incident_id,version,updated_at)
                VALUES (?,?,?) ON CONFLICT(incident_id) DO UPDATE SET
                version=excluded.version, updated_at=excluded.updated_at''',
                (incident_id, version, updated_at))
            return copy.deepcopy(incident)

    def cancel(self, incident_id, reason="no_active_operations", now=None):
        incident = self.get(incident_id)
        if not incident:
            return None
        if incident.get("status") in CANCELLED_INCIDENT_STATUSES:
            return incident
        incident["status"] = "cancelled"
        incident["heat"] = 0
        incident["level"] = 0
        incident["operation_ids"] = []
        incident["cancelled_reason"] = _clean(reason, "cancelled")
        return self.upsert(incident, event_type="incident.cancelled", now=now)

    def replay(self, incident_id, limit=100):
        limit = max(1, min(int(limit or 100), 500))
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT seq, incident_id, event_type, event_json, created_at
                FROM response_incident_audit
                WHERE incident_id = ?
                ORDER BY seq ASC
                LIMIT ?
                """,
                (_clean(incident_id), limit),
            ).fetchall()
            return [
                {
                    "seq": int(row["seq"]),
                    "incident_id": row["incident_id"],
                    "event_type": row["event_type"],
                    "event": loads_json(row["event_json"], {}),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
