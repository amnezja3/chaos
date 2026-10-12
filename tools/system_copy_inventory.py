"""Bounded read-only inventory of durable copy; never exports message text."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def inventory(db_path, kind, after='', limit=100):
    from system_message_i18n import project_system_copy
    if kind not in {'notifications', 'mail'} or type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('invalid_inventory_request')
    path = Path(db_path).resolve()
    if not path.is_file():
        raise ValueError('database_missing')
    records = []
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        if kind == 'notifications':
            rows = conn.execute('''SELECT message_id,source,title,body,payload_json
                FROM system_messages WHERE message_id>? ORDER BY message_id LIMIT ?''',
                (str(after), limit))
        else:
            cursor = int(after or 0)
            if cursor < 0:
                raise ValueError('invalid_mail_cursor')
            rows = conn.execute('''SELECT id,subject,body,system_copy_json FROM chat_messages
                WHERE id>? ORDER BY id LIMIT ?''', (cursor, limit))
        for row in rows:
            if kind == 'notifications':
                payload = json.loads(row['payload_json'] or '{}')
                payload = payload if isinstance(payload, dict) else {}
                message = {**payload, 'title':row['title'], 'text':row['body']}
                copy = project_system_copy(message, row['source']).get('system_copy')
                identity, title, source = row['message_id'], row['title'], row['source']
            else:
                copy = json.loads(row['system_copy_json'] or '{}')
                identity, title, source = row['id'], row['subject'], 'unclassified'
                if copy:
                    source = 'system_metadata'
            encoded = json.dumps([title, row['body']], ensure_ascii=False).encode()
            records.append(dict(id=identity, source=source, content_bytes=len(encoded),
                source_version=hashlib.sha256(encoded).hexdigest(),
                has_system_copy=isinstance(copy, dict) and copy.get('schema_version') == 1,
                review_required=not bool(copy)))
    return dict(kind=kind, records=records, next_after=records[-1]['id'] if records else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--kind', choices=('notifications', 'mail'), required=True)
    parser.add_argument('--after', default='')
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    try:
        result = inventory(args.db, args.kind, args.after, args.limit)
    except (ValueError, OSError, sqlite3.Error):
        print(json.dumps({'ok':False, 'error':'system_copy_inventory_failed'}))
        return 1
    print(json.dumps({'ok':True, **result}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
