"""Durable 142.5 draws. No wallet, inventory, profile or penalty writes."""
import hashlib
import math
import os
import secrets
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from database import DB_PATH, db_connect, dumps_json, loads_json
from config import RESPONSE_DETECTION_RADIUS_MAX_M
from .canonical_executor import execution_enabled
from .qualification import DetectionQualification, actor_snapshot, qualification_mode
from .npc_capsule_factory import position_at
from .movement_guard import MovementBlocked, require_movement_allowed


def encounters_enabled():
    return qualification_mode() == 'observe' and os.environ.get('CHAOS_RESPONSE_ENCOUNTERS_ENABLED', 'false').lower() == 'true'


class EncounterStore:
    def __init__(self, incidents, capsules, db_path=DB_PATH, roller=None):
        self.incidents, self.capsules, self.db_path = incidents, capsules, db_path
        self.executor = None
        self.roller = roller or (lambda: secrets.randbelow(100) + 1)
        with db_connect(db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('''CREATE TABLE IF NOT EXISTS response_encounters (
                encounter_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, incident_id TEXT NOT NULL,
                occurrence INTEGER NOT NULL DEFAULT 1, actor_role TEXT NOT NULL,
                chance INTEGER NOT NULL, roll INTEGER NOT NULL CHECK(roll BETWEEN 1 AND 100),
                outcome TEXT NOT NULL CHECK(outcome IN ('selected','avoided')),
                execution_status TEXT NOT NULL DEFAULT 'not_enabled',
                policy_version TEXT NOT NULL, capsule_id TEXT NOT NULL,
                qualification_json TEXT NOT NULL, created_at TEXT NOT NULL,
                UNIQUE(actor_id,incident_id,occurrence))''')
            fields = {r[1] for r in conn.execute('PRAGMA table_info(response_encounters)')}
            for name, default in (('execution_json', '{}'), ('execution_checked_at', '')):
                if name not in fields:
                    conn.execute(f"ALTER TABLE response_encounters ADD COLUMN {name} TEXT NOT NULL DEFAULT '{default}'")
            conn.execute('''CREATE INDEX IF NOT EXISTS idx_response_encounter_pending
                ON response_encounters(execution_checked_at,encounter_id) WHERE execution_status='pending' ''')
            # Indexed round-robin patrol scan; never materialize every NPC.
            columns = {r[1] for r in conn.execute('PRAGMA table_info(response_npc_capsules)')}
            for name in ('detection_scanned_at', 'detection_actor_cursor'):
                if name not in columns:
                    conn.execute(f"ALTER TABLE response_npc_capsules ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
            conn.execute('''CREATE INDEX IF NOT EXISTS idx_response_detection_scan
                ON response_npc_capsules(detection_scanned_at,capsule_id)
                WHERE status IN ('active','updated')''')

    def encounter(self, candidate, observer, *, now=None):
        result = self._observe(candidate, observer, now=now)
        receipt = result.get('encounter')
        if receipt and receipt['execution_status'] == 'pending' and self.executor:
            try:
                execution = self.executor.execute(receipt['encounter_id'], candidate, observer, now=now)
            except Exception as exc:
                # The roll is already durable. Next fresh detection retries the
                # transaction; no partial wallet/inventory/history effects survive.
                print(f'[RESPONSE_EXECUTOR] deferred error={type(exc).__name__}', flush=True)
                execution = {'status': 'deferred', 'reason': 'execution_retry_required'}
            result['execution'] = execution
            if execution['status'] in {'executed', 'no_effect', 'unsupported', 'blocked', 'expired'}:
                receipt['execution_status'] = execution['status']
            result['consequence_executed'] = bool(execution.get('consequence_executed'))
            result['penalty_executed'] = bool(execution.get('penalty_executed'))
        return result

    def get_result(self, actor, incident_id):
        """Read-only recovery even after leaving the patrol or closing the source."""
        with db_connect(self.db_path) as conn:
            row = conn.execute('''SELECT encounter_id,actor_role,chance,roll,outcome,execution_status,
                execution_json,created_at FROM response_encounters
                WHERE actor_id=? AND incident_id=? AND occurrence=1''', (actor,incident_id)).fetchone()
        if not row:
            return None
        result = dict(row)
        result['execution'] = loads_json(result.pop('execution_json'), {})
        return result

    def _observe(self, candidate, observer, *, now=None):
        if not encounters_enabled():
            return {'status': 'disabled', 'reason': 'encounters_disabled', 'qualified': False,
                    'consequence_executed': False, 'penalty_executed': False}
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            now = now or datetime.now(timezone.utc)
            try:
                require_movement_allowed(conn, candidate.get('actor_id'))
            except MovementBlocked:
                return {'status': 'rejected', 'reason': 'actor_detained', 'qualified': False,
                        'consequence_executed': False, 'penalty_executed': False}
            qualifier = DetectionQualification(
                SimpleNamespace(get=lambda key: self.incidents.get(key, conn=conn)),
                SimpleNamespace(get=lambda key: self.capsules.get(key, conn=conn)), None,
                lambda actor: actor_snapshot(self.db_path, actor, conn=conn))
            decision = qualifier.qualify(candidate, observer, now, record=False)
            if not decision.get('qualified'):
                return decision
            actor, incident = decision['actor_id'], decision['incident_id']
            # occurrence=1 is the approved MVP unit. Future arrests require an
            # explicit server-owned occurrence policy; never accept it from JSON.
            existing = conn.execute('SELECT * FROM response_encounters WHERE actor_id=? AND incident_id=? AND occurrence=1',
                (actor, incident)).fetchone()
            if existing:
                receipt = dict(existing)
                duplicate = True
            else:
                chance = 80 if decision['actor_role'] == 'initiator' else 30
                roll = int(self.roller())
                if not 1 <= roll <= 100:
                    raise ValueError('Invalid encounter draw')
                receipt = {'encounter_id': 'encounter_' + hashlib.sha256(dumps_json([actor, incident, 1]).encode()).hexdigest()[:32],
                    'actor_id': actor, 'incident_id': incident, 'occurrence': 1,
                    'actor_role': decision['actor_role'], 'chance': chance, 'roll': roll,
                    'outcome': 'selected' if roll <= chance else 'avoided',
                    'execution_status': ('pending' if roll <= chance and self.executor and execution_enabled(actor)
                                         else 'not_enabled'), 'policy_version': 'encounter-142-5-v1',
                    'capsule_id': decision['capsule_id'], 'qualification_json': dumps_json(decision),
                    'created_at': now.isoformat()}
                conn.execute('''INSERT INTO response_encounters (
                    encounter_id,actor_id,incident_id,occurrence,actor_role,chance,roll,
                    outcome,execution_status,policy_version,capsule_id,qualification_json,created_at) VALUES (
                    :encounter_id,:actor_id,:incident_id,:occurrence,:actor_role,:chance,:roll,
                    :outcome,:execution_status,:policy_version,:capsule_id,:qualification_json,:created_at)''', receipt)
                duplicate = False
            execution = loads_json(receipt.get('execution_json', '{}'), {})
            return {**decision, 'execution': execution,
                'consequence_executed': bool(execution.get('consequence_executed')),
                'penalty_executed': bool(execution.get('penalty_executed')),
                'encounter': {key: receipt[key] for key in (
                'encounter_id', 'actor_role', 'chance', 'roll', 'outcome', 'execution_status', 'created_at')},
                'duplicate_encounter': duplicate}

    def scan(self, *, now=None, patrol_limit=4, actor_limit=16):
        """Bounded spatial/presence scan independent of map clients."""
        stats = {'patrols': 0, 'candidates': 0, 'created': 0, 'duplicates': 0}
        if not encounters_enabled():
            return stats
        if self.executor:
            self.executor.expire_pending(now=now)
        now = now or datetime.now(timezone.utc)
        patrol_limit = max(1, min(int(patrol_limit), 8))
        actor_limit = max(1, min(int(actor_limit), 32))
        with db_connect(self.db_path) as conn:
            patrols = conn.execute('''SELECT * FROM response_npc_capsules
                INDEXED BY idx_response_detection_scan
                WHERE status IN ('active','updated') AND expires_at>?
                ORDER BY detection_scanned_at,capsule_id LIMIT ?''', (now.isoformat(), patrol_limit)).fetchall()
        for row in patrols:
            # Advance even a malformed patrol, so it cannot starve healthy ones.
            with db_connect(self.db_path) as conn:
                conn.execute('UPDATE response_npc_capsules SET detection_scanned_at=? WHERE capsule_id=?',
                    (now.isoformat(), row['capsule_id']))
            stats['patrols'] += 1
            capsule = self.capsules._row_to_capsule(row)
            try:
                point = position_at(capsule, now)
                lat, lng = float(point['lat']), float(point['lng'])
                radius = float(capsule.get('detection_radius_m') or 0)
            except (TypeError, ValueError, KeyError, OverflowError):
                continue
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                continue
            if not math.isfinite(radius) or not 0 < radius <= RESPONSE_DETECTION_RADIUS_MAX_M:
                continue
            lat_delta = radius / 110000.0
            lng_delta = min(180, lat_delta / max(.001, abs(math.cos(math.radians(point['lat'])))))
            low, high = point['lng'] - lng_delta, point['lng'] + lng_delta
            if low < -180:
                lng_clause, lng_args = '(p.lng>=? OR p.lng<=?)', (low + 360, high)
            elif high > 180:
                lng_clause, lng_args = '(p.lng>=? OR p.lng<=?)', (low, high - 360)
            else:
                lng_clause, lng_args = 'p.lng BETWEEN ? AND ?', (low, high)
            with db_connect(self.db_path) as conn:
                actors = conn.execute(f'''SELECT p.username,p.lat,p.lng,p.version
                    FROM player_positions p INDEXED BY idx_player_positions_lat_lng
                    JOIN mail_presence h ON h.username=p.username
                    WHERE p.lat BETWEEN ? AND ? AND {lng_clause}
                    AND p.username>? AND julianday(h.last_seen_at)>=julianday(?)
                    AND NOT EXISTS (SELECT 1 FROM response_encounters e
                        WHERE e.actor_id=p.username AND e.incident_id=? AND e.occurrence=1
                        AND e.execution_status!='pending')
                    ORDER BY p.username LIMIT ?''', (point['lat']-lat_delta, point['lat']+lat_delta,
                    *lng_args, row['detection_actor_cursor'], (now-timedelta(seconds=90)).isoformat(),
                    capsule['incident_id'], actor_limit)).fetchall()
            for actor in actors:
                candidate = {'actor_id': actor['username'], 'incident_id': capsule['incident_id'],
                    'capsule_id': capsule['capsule_id'], 'detected_at': now.isoformat(),
                    'actor_position': {'lat': actor['lat'], 'lng': actor['lng']},
                    'position_version': actor['version'], 'npc_position': point,
                    'tracking_token': next(iter(capsule.get('tracking_tokens') or []), ''),
                    'behavior_version': capsule['behavior_version'], 'trajectory_seed': capsule['trajectory_seed']}
                result = self.encounter(candidate, 'server:response-worker', now=now)
                stats['candidates'] += 1
                if result.get('encounter'):
                    stats['duplicates' if result['duplicate_encounter'] else 'created'] += 1
            with db_connect(self.db_path) as conn:
                conn.execute('''UPDATE response_npc_capsules SET detection_scanned_at=?,detection_actor_cursor=?
                    WHERE capsule_id=?''', (now.isoformat(), actors[-1]['username'] if len(actors) == actor_limit else '', row['capsule_id']))
        return stats
