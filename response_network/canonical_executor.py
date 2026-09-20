"""142.6: atomic canonical effects; never loads or writes a user profile."""
import os
from datetime import datetime, timezone
from types import SimpleNamespace

from config import RESPONSE_CONSEQUENCE_TABLE
from database import db_connect, dumps_json, loads_json
from .qualification import DetectionQualification, actor_snapshot, qualification_mode
from .consequence_table import fine_amount
from .detection_validator import _coerce_datetime
from ghostnetwork.repository import GhostNetworkRepository


def execution_enabled(actor):
    if os.environ.get('CHAOS_RESPONSE_ENCOUNTERS_ENABLED', 'false').lower() != 'true':
        return False
    if qualification_mode() != 'observe' or os.environ.get('CHAOS_RESPONSE_EXECUTION_MODE') != 'enforce':
        return False
    allowed = {name.strip() for name in os.environ.get('CHAOS_RESPONSE_EXECUTION_ACTORS', '').split(',') if name.strip()}
    return '*' in allowed or actor in allowed


class CanonicalConsequenceExecutor:
    def __init__(self, db_path, incidents, capsules, records, wallet, inventory, operations, messages, deltas):
        self.db_path = db_path
        self.incidents, self.capsules, self.records = incidents, capsules, records
        self.wallet, self.inventory, self.operations = wallet, inventory, operations
        self.messages, self.deltas = messages, deltas
        self.world = GhostNetworkRepository(db_path=db_path, ensure_schema=False)
        for store in (incidents, capsules, records, wallet, inventory, operations, messages, deltas):
            if os.path.abspath(store.db_path) != os.path.abspath(db_path):
                raise ValueError('consequence_stores_must_share_database')
        with db_connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS response_judgment (
                actor_id TEXT PRIMARY KEY, points INTEGER NOT NULL, updated_at TEXT NOT NULL)''')

    def execute(self, encounter_id, candidate, observer, *, now=None):
        actor = candidate.get('actor_id')
        if not execution_enabled(actor):
            return {'status': 'disabled', 'reason': 'execution_disabled'}
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            now = now or datetime.now(timezone.utc)
            row = conn.execute('SELECT * FROM response_encounters WHERE encounter_id=? AND actor_id=?',
                               (encounter_id, actor)).fetchone()
            if not row or row['incident_id'] != candidate.get('incident_id'):
                return {'status': 'rejected', 'reason': 'encounter_mismatch'}
            if row['execution_status'] != 'pending':
                return loads_json(row['execution_json'], {}) or {'status': row['execution_status']}
            if row['outcome'] != 'selected':
                raise ValueError('only_selected_encounter_can_execute')
            if self.world.get_gameplay_lock(conn=conn):
                return {'status': 'deferred', 'reason': 'ghostsignal_gameplay_locked'}
            qualifier = DetectionQualification(
                SimpleNamespace(get=lambda key: self.incidents.get(key, conn=conn)),
                SimpleNamespace(get=lambda key: self.capsules.get(key, conn=conn)), None,
                lambda name: actor_snapshot(self.db_path, name, conn=conn))
            decision = qualifier.qualify(candidate, observer, now, record=False)
            if not decision.get('qualified'):
                return {'status': 'deferred', 'reason': decision['reason']}
            incident = self.incidents.get(row['incident_id'], conn=conn)
            plan = self.records.prepare(conn, actor, int(incident['level']))

            def finish(status, reason, effects=None):
                result = {'status': status, 'reason': reason, 'encounter_id': encounter_id,
                          'plan': plan, 'effects': effects or {}, 'executed_at': now.isoformat(),
                          'consequence_executed': status == 'executed', 'penalty_executed': status == 'executed'}
                conn.execute('UPDATE response_encounters SET execution_status=?,execution_json=? WHERE encounter_id=?',
                             (status, dumps_json(result), encounter_id))
                return result

            restart = self.world.get_client_restart(conn=conn)
            if restart and any(_coerce_datetime(stamp) < _coerce_datetime(restart['created_at'])
                               for stamp in (row['created_at'], incident['created_at'])):
                return finish('expired', 'world_epoch_replaced')

            if not plan:
                return finish('no_effect', 'incident_observation_only')
            if plan['detention_minutes']:
                return finish('unsupported', 'detention_requires_sprint_143')

            # Indexed member join, never hydrate every operation or profile.
            related = conn.execute('''SELECT o.operation_id,
                CASE WHEN length(o.operation_json)<=262144 THEN o.operation_json ELSE '{}' END AS operation_json,
                length(o.operation_json) AS bytes
                FROM response_incident_members m JOIN player_operations o ON o.operation_id=m.operation_id
                WHERE m.incident_id=? AND o.username=? AND o.status NOT IN
                ('cancelled','canceled','done','completed','failed','expired','timeout','resolved')
                ORDER BY o.operation_id LIMIT 1''', (row['incident_id'], actor)).fetchone()
            if related and related['bytes'] > 262144:
                return finish('blocked', 'operation_projection_too_large')
            operation = loads_json(related['operation_json'], {}) if related else {}
            risk = max(0, int(incident.get('heat') or 0))
            # No fabricated operation required for a bystander or cooled incident.
            wallet = conn.execute('SELECT balance,version FROM wallet_balances WHERE username=?', (actor,)).fetchone()
            if plan['fine_multiplier'] and wallet is None:
                return finish('blocked', 'wallet_not_initialized')
            amount = fine_amount(max(0, int(wallet['balance'])), risk, plan['fine_multiplier']) if wallet else 0
            chosen = []
            if plan['tools']:
                # Bounded metadata only. Never select descriptions/source code.
                rows = conn.execute('''SELECT app_id,
                    substr(json_extract(app_json,'$.name'),1,200) AS name,
                    length(app_json) AS bytes,
                    CASE WHEN json_array_length(app_json,'$.operation_types')>0
                         OR json_extract(app_json,'$.map_action_id') IS NOT NULL
                         OR json_extract(app_json,'$.operation_type') IS NOT NULL
                         OR lower(COALESCE(json_extract(app_json,'$.category'),json_extract(app_json,'$.family'),''))
                            IN ('tool','tools','pro_tool','hack_tool')
                         OR lower(COALESCE(json_extract(app_json,'$.product_type'),json_extract(app_json,'$.type'),''))
                            IN ('app','tool') THEN 1 ELSE 0 END AS eligible
                    FROM player_apps WHERE username=? AND status!='uninstalled' AND eligible=1
                    ORDER BY CASE WHEN app_id=? THEN 0 ELSE 1 END,app_id LIMIT ?''',
                    (actor, operation.get('source_app_id') or '',
                     plan['tools'] + RESPONSE_CONSEQUENCE_TABLE['minimum_remaining_operation_tools'])).fetchall()
                eligible = [item for item in rows if item['eligible']]
                eligible.sort(key=lambda item: (item['app_id'] != operation.get('source_app_id'), item['app_id']))
                available = max(0, len(eligible) - RESPONSE_CONSEQUENCE_TABLE['minimum_remaining_operation_tools'])
                chosen = eligible[:min(plan['tools'], available)]
                if any(item['bytes'] > 262144 for item in chosen):
                    return finish('blocked', 'app_projection_too_large')
                tool_size = conn.execute('''SELECT count(*) AS n,COALESCE(sum(length(tool_json)),0) AS bytes
                    FROM player_tool_files WHERE username=?''', (actor,)).fetchone()
                if tool_size['n'] > 256 or tool_size['bytes'] > 1048576:
                    return finish('blocked', 'tool_projection_limit')
            if not amount and not chosen:
                return finish('no_effect', 'protected_or_empty_resources')
            effects = {'fine_hc': amount, 'tool_ids': [], 'cancelled_operation_id': None}
            if amount:
                debit = self.wallet.debit(actor, amount, 'consequence:' + encounter_id,
                    reason='response.fine', source='response_network', expected_version=wallet['version'], conn=conn)
                self.deltas.record_change(actor, 'wallet', 'wallet.balance_changed',
                    {'balance': debit['balance'], 'currency': 'HC'}, entity_id='wallet',
                    dedupe_key=encounter_id + ':wallet', conn=conn)
            removed_tools = []
            for item in chosen:
                if not self.inventory.uninstall_app(actor, app_id=item['app_id'], conn=conn, removed_tools=removed_tools):
                    raise RuntimeError('confiscation_changed_before_commit')
                effects['tool_ids'].append(item['app_id'])
            if chosen:
                self.deltas.record_change(actor, 'apps', 'apps.confiscated',
                    {'removed_app_ids': effects['tool_ids'], 'removed_tools': removed_tools},
                    entity_id=encounter_id, dedupe_key=encounter_id + ':apps', conn=conn)
                storage = conn.execute('SELECT capacity,used FROM player_storage WHERE username=?', (actor,)).fetchone()
                if storage:
                    self.deltas.record_change(actor, 'storage', 'storage.used_changed',
                        {**dict(storage), 'unit': 'MB', 'soft_limit': True, 'over_limit': storage['used'] > storage['capacity']},
                        entity_id='storage', dedupe_key=encounter_id + ':storage', conn=conn)
            if related:
                cancelled, status = self.operations.cancel_operation(actor, related['operation_id'],
                    cancelled_by='response_network', conn=conn)
                if status == 'cancelled':
                    effects['cancelled_operation_id'] = related['operation_id']
                    self.deltas.record_change(actor, 'map', 'map.operations_changed',
                        {'operation_id': related['operation_id'], 'status': 'cancelled'},
                        entity_id=related['operation_id'], dedupe_key=encounter_id + ':operation', conn=conn)
            points_added = max(1, risk // 25)
            conn.execute('''INSERT INTO response_judgment(actor_id,points,updated_at) VALUES (?,?,?)
                ON CONFLICT(actor_id) DO UPDATE SET points=points+excluded.points,updated_at=excluded.updated_at''',
                (actor, points_added, now.isoformat()))
            effects['judgment_points_added'] = points_added
            result = finish('executed', 'consequence_applied', effects)
            self.records.record_executed(conn, encounter_id, plan, effects, now.isoformat())
            parts = []
            if amount:
                parts.append(f'Mandat: {amount} HC.')
            if chosen:
                parts.append('Skonfiskowano narzędzia: ' + ', '.join(item['name'] or item['app_id'] for item in chosen) + '.')
            self.messages.add_message(actor, {'id': encounter_id, 'dedupe_key': encounter_id,
                'title': 'Konsekwencje incydentu', 'text': ' '.join(parts), 'type': 'warning',
                'created_at': now.isoformat(), 'encounter_id': encounter_id}, source='response_network', conn=conn)
            return result

    def expire_pending(self, *, now=None, limit=16):
        """Bounded round-robin cleanup; never apply effects from old detections."""
        now = now or datetime.now(timezone.utc)
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            rows = conn.execute('''SELECT e.encounter_id,e.created_at,i.created_at AS incident_created_at,
                i.status,i.expires_at FROM response_encounters e
                LEFT JOIN response_incidents i ON i.incident_id=e.incident_id
                WHERE e.execution_status='pending' ORDER BY e.execution_checked_at,e.encounter_id LIMIT ?''',
                (min(32, max(1, limit)),)).fetchall()
            restart = self.world.get_client_restart(conn=conn) if rows else None
            for row in rows:
                closed = row['status'] not in {'active','escalated','cooling'}
                closed = closed or (row['status'] == 'cooling' and _coerce_datetime(row['expires_at']) <= now)
                closed = closed or bool(restart and any(_coerce_datetime(stamp) < _coerce_datetime(restart['created_at'])
                    for stamp in (row['created_at'], row['incident_created_at']) if stamp))
                conn.execute('UPDATE response_encounters SET execution_checked_at=?,execution_status=? WHERE encounter_id=?',
                    (now.isoformat(), 'expired' if closed else 'pending', row['encounter_id']))
        return len(rows)
