"""Operator-reviewed content redaction; dry-run by default, no account deletion.

The private case file is also the replay record after restoring a backup.
Never edits IDs, ownership, balances, conflicts or username tombstones.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

FIELDS = {
    'chat_messages': {'body', 'subject', 'system_copy_json'},
    'area_events': {'payload_json'},
    'safety_reports': {'details', 'evidence_json'},
}


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def inventory(db, terms):
    """Read-only literal search; returns locations/counts, never matching content.

    This is a review aid, not a proof of anonymisation: aliases, encodings,
    hashes, files and external services require case-specific review.
    """
    if not isinstance(terms, list) or not terms or len(terms) > 20 or any(
            not isinstance(t, str) or len(t) < 3 for t in terms):
        raise ValueError('search_terms_required')
    conn = sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)
    quote = lambda name: '"' + name.replace('"', '""') + '"'
    found = []
    try:
        for (table,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall():
            for column in conn.execute(f'PRAGMA table_info({quote(table)})').fetchall():
                name = column[1]
                condition = ' OR '.join(f'instr(lower(CAST({quote(name)} AS TEXT)),lower(?))>0' for _ in terms)
                count = conn.execute(f'SELECT count(*) FROM {quote(table)} WHERE {condition}',terms).fetchone()[0]
                if count:
                    found.append({'table':table,'column':name,'matches':count})
        return found
    finally:
        conn.close()


def redact(db, case, *, apply=False):
    if not isinstance(case, dict) or not str(case.get('case_id', '')).strip():
        raise ValueError('case_id_required')
    username = case.get('username')
    if not isinstance(username, str) or not username or username == 'admin':
        raise ValueError('invalid_target')
    if not isinstance(case.get('reason'), str) or len(case['reason'].strip()) < 10:
        raise ValueError('review_reason_required')
    edits = case.get('redactions')
    if not isinstance(edits, list) or not edits or len(edits) > 500:
        raise ValueError('reviewed_redactions_required')
    uri = Path(db).resolve().as_uri() + '?mode=rw'
    conn = sqlite3.connect(uri, uri=True)
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
            raise ValueError('delete_account_through_identity_first')
        if not conn.execute('SELECT 1 FROM deleted_user_tombstones WHERE username=?', (username,)).fetchone():
            raise ValueError('deleted_account_not_found')
        changed = already = 0
        seen = set()
        for edit in edits:
            table, column, row_id = edit.get('table'), edit.get('column'), edit.get('id')
            if table not in FIELDS or column not in FIELDS[table] or type(row_id) is not int or row_id < 1:
                raise ValueError('unsupported_content_field')
            key = (table, column, row_id)
            if key in seen:
                raise ValueError('duplicate_edit')
            seen.add(key)
            replacement = edit.get('replacement')
            if not isinstance(replacement, str) or len(replacement) > 200000:
                raise ValueError('invalid_replacement')
            if column.endswith('_json'):
                json.loads(replacement)
            row = conn.execute(f'SELECT "{column}" FROM "{table}" WHERE id=?', (row_id,)).fetchone()
            if row is None or not isinstance(row[0], str):
                raise ValueError('content_missing')
            if row[0] == replacement:
                already += 1
                continue
            if digest(row[0]) != edit.get('expected_sha256'):
                raise ValueError('content_changed_review_again')
            conn.execute(f'UPDATE "{table}" SET "{column}"=? WHERE id=?', (replacement, row_id))
            changed += 1
        if conn.execute('PRAGMA foreign_key_check').fetchone():
            raise ValueError('foreign_key_check_failed')
        if apply:
            conn.commit()
        else:
            conn.rollback()
        return {'ok': True, 'status': 'applied' if apply else 'dry_run',
                'changed_fields': changed, 'already_redacted': already,
                'scope': 'reviewed_content_only'}
    finally:
        conn.rollback()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--case', required=True, help='Private UTF-8 JSON, never commit to Git')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--inventory', action='store_true', help='Read-only search using case.search_terms')
    parser.add_argument('--confirm-case')
    args = parser.parse_args()
    case = json.loads(Path(args.case).read_text(encoding='utf-8'))
    if args.inventory:
        if args.apply:
            parser.error('--inventory cannot be combined with --apply')
        print(json.dumps({'matches':inventory(args.db,case.get('search_terms'))}))
        return
    if args.apply and args.confirm_case != case.get('case_id'):
        parser.error('--confirm-case must match the reviewed case_id')
    print(json.dumps(redact(args.db, case, apply=args.apply)))


if __name__ == '__main__':
    main()
