"""Reviewed language metadata for existing publications; never translate text."""
import hashlib
import json
import re

from database import db_connect
from ghost_i18n import approved_locales
from .news_locales import source_version
from .repository import GhostNetworkRepository


def _schema(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS ghost_narrative_language_batches (
        batch_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL, reviewer TEXT NOT NULL,
        state TEXT NOT NULL)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ghost_narrative_language_items (
        batch_id TEXT NOT NULL, record_id TEXT NOT NULL, source_version TEXT NOT NULL,
        old_locale TEXT NOT NULL, new_locale TEXT NOT NULL,
        PRIMARY KEY(batch_id,record_id))''')


def _record(conn, record_id):
    row = conn.execute('SELECT * FROM ghost_narrative_medium_records WHERE medium_record_id=?', (record_id,)).fetchone()
    if not row:
        raise ValueError('publication_not_found')
    return GhostNetworkRepository._narrative_medium_record(row)


def inventory(db_path, after='', limit=100):
    if type(limit) is not int or not 1 <= limit <= 500:
        raise ValueError('invalid_inventory_limit')
    with db_connect(db_path) as conn:
        rows = conn.execute('''SELECT * FROM ghost_narrative_medium_records
            WHERE medium_record_id>? ORDER BY medium_record_id LIMIT ?''', (after,limit)).fetchall()
        records = [GhostNetworkRepository._narrative_medium_record(row) for row in rows]
    return {'records':[dict(medium_record_id=r['medium_record_id'], source_version=source_version(r),
        medium=r['target_medium'], output_locale=r.get('output_locale') or None,
        review_required=not bool(r.get('output_locale'))) for r in records],
        'next_after':records[-1]['medium_record_id'] if records else None}


def apply_batch(db_path, batch, entries, reviewer, *, dry_run=True):
    if not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', str(batch or '')) or not re.fullmatch(r'[A-Za-z0-9_.:@-]{1,128}', str(reviewer or '')):
        raise ValueError('invalid_batch_or_reviewer')
    if not isinstance(entries,list) or not 1 <= len(entries) <= 100:
        raise ValueError('invalid_batch_size')
    seen = set()
    for entry in entries:
        if not isinstance(entry,dict) or set(entry) != {'medium_record_id','source_version','locale'} or any(not isinstance(v,str) for v in entry.values()):
            raise ValueError('invalid_language_entry')
        if entry['medium_record_id'] in seen:
            raise ValueError('duplicate_language_entry')
        seen.add(entry['medium_record_id'])
        if entry['locale'] not in approved_locales('narration'):
            raise ValueError('unapproved_language')
    digest = hashlib.sha256(json.dumps([entries,reviewer],sort_keys=True).encode()).hexdigest()
    with db_connect(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        _schema(conn)
        previous = conn.execute('SELECT * FROM ghost_narrative_language_batches WHERE batch_id=?',(batch,)).fetchone()
        if previous:
            if previous['payload_hash'] != digest or previous['state'] != 'applied':
                raise ValueError('language_batch_conflict')
            return {'status':'already_applied','updated':0}
        count = 0
        for entry in entries:
            record = _record(conn, entry['medium_record_id'])
            if source_version(record) != entry['source_version']:
                raise ValueError('stale_language_source')
            previous_locale = record.get('output_locale') or ''
            if previous_locale == entry['locale']:
                continue
            if previous_locale:
                raise ValueError('language_already_known')
            conn.execute('INSERT INTO ghost_narrative_language_items VALUES (?,?,?,?,?)',
                (batch,record['medium_record_id'],entry['source_version'],previous_locale,entry['locale']))
            conn.execute('UPDATE ghost_narrative_medium_records SET output_locale=? WHERE medium_record_id=?',
                (entry['locale'],record['medium_record_id']))
            count += 1
        conn.execute('INSERT INTO ghost_narrative_language_batches VALUES (?,?,?,?)',(batch,digest,reviewer,'applied'))
        if dry_run:
            conn.rollback()
    return {'status':'dry_run' if dry_run else 'applied','updated':count}


def rollback_batch(db_path, batch, *, dry_run=True):
    with db_connect(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        _schema(conn)
        previous = conn.execute('SELECT * FROM ghost_narrative_language_batches WHERE batch_id=?',(batch,)).fetchone()
        if not previous:
            raise ValueError('language_batch_not_found')
        if previous['state'] == 'rolled_back':
            return {'status':'already_rolled_back','updated':0}
        rows = conn.execute('SELECT * FROM ghost_narrative_language_items WHERE batch_id=?',(batch,)).fetchall()
        for row in rows:
            record = _record(conn,row['record_id'])
            if source_version(record) != row['source_version'] or record.get('output_locale') != row['new_locale']:
                raise ValueError('language_rollback_conflict')
            conn.execute('UPDATE ghost_narrative_medium_records SET output_locale=? WHERE medium_record_id=?',
                (row['old_locale'],row['record_id']))
        conn.execute("UPDATE ghost_narrative_language_batches SET state='rolled_back' WHERE batch_id=?",(batch,))
        if dry_run:
            conn.rollback()
    return {'status':'dry_run' if dry_run else 'rolled_back','updated':len(rows)}
