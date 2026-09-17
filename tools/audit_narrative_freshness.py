"""Read-only queue diagnostic, without application initialization or model calls."""
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    args = parser.parse_args()
    path = Path(args.db).resolve()
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        has_expiry = 'expires_at' in {row[1] for row in conn.execute('PRAGMA table_info(ghost_narrative_outbox)')}
        report = {'read_only': True, 'expiry_schema': has_expiry}
        report['queue'] = [dict(row) for row in conn.execute('''SELECT target_medium,source_scope,status,
            count(*) AS count,min(created_at) AS oldest,max(priority) AS highest_priority
            FROM ghost_narrative_outbox WHERE status IN ('ready','retry_wait','claimed','processing')
            GROUP BY target_medium,source_scope,status''')]
        expiry = 'expires_at' if has_expiry else "'' AS expires_at"
        report['next_tasks'] = [dict(row) for row in conn.execute(f'''SELECT outbox_id,target_medium,
            source_scope,narrative_intent,priority,status,created_at,{expiry},last_error_code,
            json_extract(validation_json,'$.incident_context') AS incident_context,
            json_extract(validation_json,'$.conflict_context') AS conflict_context
            FROM ghost_narrative_outbox WHERE status IN ('ready','retry_wait','claimed','processing')
            ORDER BY priority DESC,created_at LIMIT 20''')]
        report['publications'] = [dict(row) for row in conn.execute('''SELECT target_medium,status,
            count(*) AS count,min(created_at) AS oldest FROM ghost_narrative_publication_receipts
            WHERE status IN ('ready','retry_wait','claimed') GROUP BY target_medium,status''')]
        report['recent_world_publications'] = [dict(row) for row in conn.execute('''SELECT m.title,
            m.target_medium,m.published_at,m.active_state,o.outbox_id,o.created_at AS task_created_at,
            o.narrative_intent,o.last_error_code,
            json_extract(o.validation_json,'$.incident_context') AS incident_context,
            json_extract(o.validation_json,'$.conflict_context') AS conflict_context
            FROM ghost_narrative_medium_records m JOIN ghost_narrative_outbox o ON o.outbox_id=m.task_id
            WHERE o.source_scope='blacknet_world' AND m.audience_scope='public'
            ORDER BY m.published_at DESC LIMIT 20''')]
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for task in report['next_tasks'] + report['recent_world_publications']:
            task['canonical_sources'] = []
            for ref in json.loads(task.get('conflict_context') or '[]')[:8]:
                if 'territory_conflicts' in tables:
                    row = conn.execute('SELECT conflict_key,status,conflict_version,updated_at FROM territory_conflicts WHERE conflict_key=?', (ref['key'],)).fetchone()
                    task['canonical_sources'].append(dict(row) if row else {'missing_conflict': ref['key']})
            ref = json.loads(task.get('incident_context') or '{}')
            if ref.get('id') and 'response_incidents' in tables:
                row = conn.execute('SELECT incident_id,status,expires_at FROM response_incidents WHERE incident_id=?', (ref['id'],)).fetchone()
                task['canonical_sources'].append(dict(row) if row else {'missing_incident': ref['id']})
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
