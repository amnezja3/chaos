"""Coalescing durable publication heads, bounded delivery and crash recovery."""
import secrets
from datetime import timedelta

from database import db_connect
from .incident_store import _iso


class IncidentPublicationRelay:
    def __init__(self, store):
        self.store = store

    def drain(self, deliver, now, limit=8):
        result = {'delivered': 0, 'failed': 0}
        with db_connect(self.store.db_path) as conn:
            rows = conn.execute('''SELECT incident_id FROM response_incident_publications
                WHERE version > delivered_version AND
                (lease_until IS NULL OR julianday(lease_until)<=julianday(?))
                ORDER BY updated_at, incident_id LIMIT ?''', (_iso(now), min(32, max(1, limit)))).fetchall()
        for row in rows:
            token = secrets.token_hex(16)
            with db_connect(self.store.db_path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                claimed = conn.execute('''UPDATE response_incident_publications
                    SET lease_token=?,lease_until=?,batch_version=CASE WHEN batch_version=0 THEN version ELSE batch_version END
                    WHERE incident_id=? AND version>delivered_version
                    AND (lease_until IS NULL OR julianday(lease_until)<=julianday(?))''',
                    (token, _iso(now + timedelta(seconds=60)), row['incident_id'], _iso(now)))
                if claimed.rowcount != 1:
                    continue
                job = dict(conn.execute('SELECT * FROM response_incident_publications WHERE incident_id=?',
                                        (row['incident_id'],)).fetchone())
                incident = self.store.get(row['incident_id'], conn=conn)
            try:
                cursor, done = deliver(incident, job['viewer_cursor'])
            except Exception:
                result['failed'] += 1
                # Lease expiry is also retry backoff. Nothing acknowledges a failed job.
                continue
            with db_connect(self.store.db_path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                current = conn.execute('SELECT * FROM response_incident_publications WHERE incident_id=?',
                                       (row['incident_id'],)).fetchone()
                if current['lease_token'] != token:
                    continue
                # Complete the viewer page even if a newer head arrived. Then replay the
                # latest version from the first viewer; continuous heat changes cannot
                # starve viewers at the end of the list.
                delivered = job['batch_version'] if done else current['delivered_version']
                conn.execute('''UPDATE response_incident_publications SET delivered_version=?,
                    viewer_cursor=?,batch_version=?,lease_token=NULL,lease_until=NULL WHERE incident_id=?''',
                    (delivered, '' if done else cursor, 0 if done else job['batch_version'], row['incident_id']))
            result['delivered'] += int(done)
        return result
