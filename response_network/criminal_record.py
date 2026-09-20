"""Small canonical record, to be committed with actual effects by 142.6."""
from database import DB_PATH, db_connect, dumps_json
from .consequence_table import plan_consequence


class CriminalRecordStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        with db_connect(db_path) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS response_criminal_records (
                actor_id TEXT PRIMARY KEY, executed_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS response_penalty_history (
                encounter_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL,
                incident_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
                policy_version TEXT NOT NULL, stage INTEGER NOT NULL,
                plan_json TEXT NOT NULL, effects_json TEXT NOT NULL,
                executed_at TEXT NOT NULL, UNIQUE(actor_id,ordinal))''')

    def prepare(self, conn, actor_id, incident_level):
        row = conn.execute('SELECT executed_count FROM response_criminal_records WHERE actor_id=?',
                           (actor_id,)).fetchone()
        return plan_consequence(incident_level, row['executed_count'] if row else 0)

    def record_executed(self, conn, encounter_id, plan, effects, executed_at):
        """Caller holds BEGIN IMMEDIATE and has committed effects in this transaction.

        No inner commit/schema init/profile write. Failure rolls back with effects.
        Never call for avoided, prepared, unsupported detention or zero effects.
        """
        if not conn.in_transaction:
            raise ValueError('penalty_transaction_required')
        existing = conn.execute('SELECT ordinal FROM response_penalty_history WHERE encounter_id=?',
                                (encounter_id,)).fetchone()
        if existing:
            return {'created': False, 'ordinal': existing['ordinal']}
        receipt = conn.execute('SELECT * FROM response_encounters WHERE encounter_id=?',
                               (encounter_id,)).fetchone()
        if not receipt or receipt['outcome'] != 'selected' or receipt['execution_status'] != 'executed':
            raise ValueError('encounter_not_executed')
        if not effects or not (effects.get('fine_hc', 0) > 0 or effects.get('tool_ids')
                               or effects.get('detention_seconds', 0) > 0):
            raise ValueError('no_executed_effect')
        actor = receipt['actor_id']
        expected = self.prepare(conn, actor, plan['incident_level'])
        if not expected or plan != expected:
            raise ValueError('stale_consequence_plan')
        ordinal = plan['previous_executed'] + 1
        conn.execute('''INSERT INTO response_penalty_history
            (encounter_id,actor_id,incident_id,ordinal,policy_version,stage,plan_json,effects_json,executed_at)
            VALUES (?,?,?,?,?,?,?,?,?)''', (encounter_id,actor,receipt['incident_id'],ordinal,
                plan['policy_version'],plan['stage'],dumps_json(plan),dumps_json(effects),executed_at))
        conn.execute('''INSERT INTO response_criminal_records(actor_id,executed_count,updated_at) VALUES (?,?,?)
            ON CONFLICT(actor_id) DO UPDATE SET executed_count=excluded.executed_count,
                updated_at=excluded.updated_at''', (actor,ordinal,executed_at))
        return {'created': True, 'ordinal': ordinal}
