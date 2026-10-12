"""Reviewed News text variants. No generation or publication on reads."""
import hashlib
import json

from database import db_connect
from ghost_i18n import approved_locales


def source_version(record):
    # Include facts, source versions, text and actions: stale translations never
    # silently attach to a changed publication. Locale is not publication identity.
    fields = ('medium_record_id', 'candidate_id', 'task_id', 'title', 'body',
              'fact_refs', 'cta_ref', 'cta_action', 'cta_payload', 'source_event_id',
              'selected_source_ref', 'selected_source_version', 'source_state_version',
              'presentation_slot', 'audience_scope', 'audience_clan', 'audience_owner',
              'truth_class', 'content_kind', 'narrative_intent')
    encoded = json.dumps({key: record.get(key) for key in fields},
                         sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(encoded.encode()).hexdigest()


def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS ghost_news_locale_variants (
        medium_record_id TEXT NOT NULL, source_version TEXT NOT NULL,
        locale TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
        reviewed_by TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY(medium_record_id, source_version, locale))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ghost_news_locale_batches (
        batch_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('applied','rolled_back')),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ghost_news_locale_batch_items (
        batch_id TEXT NOT NULL, medium_record_id TEXT NOT NULL,
        source_version TEXT NOT NULL, locale TEXT NOT NULL,
        title TEXT NOT NULL, body TEXT NOT NULL, reviewed_by TEXT NOT NULL,
        PRIMARY KEY(batch_id, medium_record_id, source_version, locale))''')


class NewsLocaleStore:
    def __init__(self, db_path):
        self.db_path = db_path

    def save_reviewed_variant(self, record_id, expected_version, locale, title, body, *, reviewed_by):
        """Offline editorial write after language/fact review; never a publisher."""
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            return self._save(conn, record_id, expected_version, locale, title, body, reviewed_by)

    @staticmethod
    def _save(conn, record_id, expected_version, locale, title, body, reviewed_by):
        from .repository import GhostNetworkRepository
        from .ollama_policy import presentation_safety_errors
        if locale not in approved_locales('narration'):
            raise ValueError('unapproved_locale')
        if not all(isinstance(value, str) and value.strip() for value in (title, body, reviewed_by)):
            raise ValueError('invalid_variant')
        if len(title) > 96 or len(body) > 800 or presentation_safety_errors(title, body):
            raise ValueError('invalid_variant')
        row = conn.execute('SELECT * FROM ghost_narrative_medium_records WHERE medium_record_id=?', (record_id,)).fetchone()
        if row is None or row['target_medium'] != 'googleplex_news':
            raise ValueError('not_news_publication')
        record = GhostNetworkRepository._narrative_medium_record(row)
        if expected_version != source_version(record):
            raise ValueError('stale_news_source')
        # Product names/descriptions belong to the creator. Editorial variants
        # cannot be used as an indirect translation API for those texts.
        if record.get('content_kind') == 'product_promo':
            raise ValueError('user_content_excluded')
        previous = conn.execute('SELECT title,body FROM ghost_news_locale_variants WHERE medium_record_id=? AND source_version=? AND locale=?',
                                (record_id, expected_version, locale)).fetchone()
        if previous:
            if previous['title'] != title or previous['body'] != body:
                raise ValueError('variant_conflict')
            return False
        conn.execute('INSERT INTO ghost_news_locale_variants (medium_record_id,source_version,locale,title,body,reviewed_by) VALUES (?,?,?,?,?,?)',
                     (record_id, expected_version, locale, title, body, reviewed_by))
        return True

    def inventory(self, *, after='', limit=100):
        """Stable bounded checkpoint; metadata only, including private records."""
        from .repository import GhostNetworkRepository
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError('invalid_batch_limit')
        with db_connect(self.db_path) as conn:
            rows = conn.execute('''SELECT * FROM ghost_narrative_medium_records
                WHERE target_medium='googleplex_news' AND medium_record_id>?
                ORDER BY medium_record_id LIMIT ?''', (after, limit)).fetchall()
            result = []
            for row in rows:
                record = GhostNetworkRepository._narrative_medium_record(row)
                version = source_version(record)
                locales = [r[0] for r in conn.execute('''SELECT locale
                    FROM ghost_news_locale_variants WHERE medium_record_id=?
                    AND source_version=? ORDER BY locale''', (row['medium_record_id'], version))]
                result.append(dict(medium_record_id=row['medium_record_id'],
                    source_version=version, locales=locales,
                    excluded=record.get('content_kind') == 'product_promo'))
        return {'records': result, 'next_after': result[-1]['medium_record_id'] if result else after}

    def apply_batch(self, batch_id, entries, *, reviewed_by, dry_run=True):
        """Atomic, resumable editorial import; dry run validates then rolls back."""
        if (not isinstance(batch_id, str) or not batch_id.strip() or len(batch_id) > 100
                or not isinstance(reviewed_by, str) or not reviewed_by.strip()
                or len(reviewed_by) > 100):
            raise ValueError('invalid_batch_identity')
        if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
            raise ValueError('invalid_batch_size')
        keys = {'medium_record_id', 'source_version', 'locale', 'title', 'body'}
        if any(not isinstance(e, dict) or set(e) != keys
               or any(not isinstance(v, str) for v in e.values()) for e in entries):
            raise ValueError('invalid_batch_entry')
        identities = [(e['medium_record_id'], e['source_version'], e['locale']) for e in entries]
        if len(set(identities)) != len(identities):
            raise ValueError('duplicate_batch_entry')
        payload_hash = hashlib.sha256(json.dumps([reviewed_by, entries],
            sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            previous = conn.execute('SELECT * FROM ghost_news_locale_batches WHERE batch_id=?', (batch_id,)).fetchone()
            if previous:
                if previous['payload_hash'] != payload_hash or previous['state'] != 'applied':
                    raise ValueError('batch_conflict')
                return {'status': 'already_applied', 'inserted': 0}
            conn.execute('INSERT INTO ghost_news_locale_batches(batch_id,payload_hash,state) VALUES (?,?,?)',
                         (batch_id, payload_hash, 'applied'))
            inserted = 0
            for entry in entries:
                args = (entry['medium_record_id'], entry['source_version'], entry['locale'],
                        entry['title'], entry['body'], reviewed_by)
                if self._save(conn, *args):
                    inserted += 1
                    conn.execute('INSERT INTO ghost_news_locale_batch_items VALUES (?,?,?,?,?,?,?)',
                                 (batch_id, *args))
            if dry_run:
                conn.rollback()
        return {'status': 'dry_run' if dry_run else 'applied', 'inserted': inserted}

    def rollback_batch(self, batch_id, *, dry_run=True):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            batch = conn.execute('SELECT state FROM ghost_news_locale_batches WHERE batch_id=?', (batch_id,)).fetchone()
            if not batch:
                raise ValueError('unknown_batch')
            if batch['state'] == 'rolled_back':
                return {'status': 'already_rolled_back', 'deleted': 0}
            rows = conn.execute('SELECT * FROM ghost_news_locale_batch_items WHERE batch_id=?', (batch_id,)).fetchall()
            deleted = 0
            for row in rows:
                deleted += conn.execute('''DELETE FROM ghost_news_locale_variants
                    WHERE medium_record_id=? AND source_version=? AND locale=?
                    AND title=? AND body=? AND reviewed_by=?''',
                    tuple(row[k] for k in ('medium_record_id','source_version','locale','title','body','reviewed_by'))).rowcount
            conn.execute("UPDATE ghost_news_locale_batches SET state='rolled_back' WHERE batch_id=?", (batch_id,))
            if dry_run:
                conn.rollback()
        return {'status': 'dry_run' if dry_run else 'rolled_back', 'deleted': deleted}

    def for_records(self, records):
        records = list(records)
        if not records:
            return {}
        if len(records) > 50:
            raise ValueError('news_read_limit')
        expected = {r['medium_record_id']: source_version(r) for r in records if r.get('target_medium') == 'googleplex_news'}
        if not expected:
            return {}
        with db_connect(self.db_path) as conn:
            # A missing migration is an error, never a write from a read path.
            rows = conn.execute('SELECT * FROM ghost_news_locale_variants WHERE medium_record_id IN (' + ','.join('?' for _ in expected) + ')',tuple(expected)).fetchall()
        result = {}
        for row in rows:
            if row['source_version'] == expected[row['medium_record_id']] and row['locale'] in approved_locales('narration'):
                result.setdefault(row['medium_record_id'], {})[row['locale']] = {'title':row['title'],'summary':row['body']}
        return result

    def for_frozen_publications(self, publications):
        """Only variants tied to the exact public archive snapshot version."""
        allowed = {(p.get('medium_record_id'), p.get('source_version'))
                   for p in list(publications)[:6] if p.get('medium') == 'googleplex_news'
                   and p.get('medium_record_id') and p.get('source_version')}
        if not allowed:
            return {}
        result = {}
        with db_connect(self.db_path) as conn:
            for record_id, version in allowed:
                for row in conn.execute('''SELECT locale,title,body FROM ghost_news_locale_variants
                    WHERE medium_record_id=? AND source_version=?''', (record_id,version)):
                    if row['locale'] in approved_locales('narration'):
                        result.setdefault(record_id,{})[row['locale']] = {'title':row['title'],'body':row['body']}
        return result
