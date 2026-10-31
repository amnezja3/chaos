"""Durable 164.0 acceptance harness, NOT a production gameplay service.

Uses the canonical operations/inventory tables in a marked, isolated database.
No profile reads, provider, camera_dump mutation or production migration.
"""
import hashlib
import json
import time
import uuid
from pathlib import Path

from database import db_connect, init_db, PlayerOperationStore, PlayerInventoryStore


DOWNLOAD_SECONDS = 1800
SESSION_CLOSE_SECONDS = 5
LEASE_SECONDS = 8
CAMERA = 'fixture-walowa-01'


class FixtureStore:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = str(path), clock
        # Never turn an arbitrary existing game database into a fixture.
        if Path(path).exists() and Path(path).stat().st_size:
            with db_connect(self.path) as conn:
                if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='cvn_fixture_meta'").fetchone():
                    raise ValueError('not_a_camera_fixture_database')
        init_db(self.path)
        with db_connect(self.path) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS cvn_fixture_meta (id INTEGER PRIMARY KEY, offset REAL NOT NULL DEFAULT 0)')
            conn.execute('INSERT OR IGNORE INTO cvn_fixture_meta(id) VALUES(1)')
            conn.execute('''CREATE TABLE IF NOT EXISTS cvn_fixture_accounts (
                username TEXT PRIMARY KEY, token TEXT NOT NULL DEFAULT '', receipt TEXT NOT NULL DEFAULT '{}')''')
            for user in ('cvn-alice', 'cvn-bob'):
                conn.execute('INSERT OR IGNORE INTO cvn_fixture_accounts(username) VALUES(?)', (user,))
                conn.execute('''INSERT OR IGNORE INTO player_storage(username,capacity,used,unit,updated_at)
                    VALUES(?,100,0,'MB','fixture')''', (user,))

    def now(self):
        with db_connect(self.path) as conn:
            offset = conn.execute('SELECT offset FROM cvn_fixture_meta WHERE id=1').fetchone()[0]
        return self.clock() + offset

    def login(self, username):
        token = uuid.uuid4().hex
        with db_connect(self.path) as conn:
            if not conn.execute('UPDATE cvn_fixture_accounts SET token=? WHERE username=?', (token, username)).rowcount:
                raise PermissionError('unknown_fixture_account')
        return token

    def user(self, token):
        if not token:
            raise PermissionError('login_required')
        with db_connect(self.path) as conn:
            row = conn.execute('SELECT username FROM cvn_fixture_accounts WHERE token=?', (token,)).fetchone()
        if not row:
            raise PermissionError('session_expired')
        return row['username']

    def logout(self, token):
        with db_connect(self.path) as conn:
            conn.execute("UPDATE cvn_fixture_accounts SET token='' WHERE token=?", (token,))

    @staticmethod
    def save(conn, user, receipt):
        conn.execute('UPDATE cvn_fixture_accounts SET receipt=? WHERE username=?',
                     (json.dumps(receipt, separators=(',', ':')), user))

    @staticmethod
    def load(conn, user):
        row = conn.execute('SELECT receipt FROM cvn_fixture_accounts WHERE username=?', (user,)).fetchone()
        if not row:
            raise PermissionError('unknown_fixture_account')
        return json.loads(row['receipt'])

    def result(self, user, success):
        """Fixture-only substitute for an already validated application receipt."""
        now = self.now()
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            receipt = self.load(conn, user)
            if receipt:
                return receipt  # Retry cannot change failure into success or reset time.
            identifier = uuid.uuid4().hex
            receipt = dict(id=identifier, reference_id='reference-'+identifier,
                           camera_id=CAMERA, success=success, result_at=now,
                           state='SESSION_CLOSE' if success else 'FAILED',
                           close_at=now+SESSION_CLOSE_SECONDS if success else None,
                           start_at=now+SESSION_CLOSE_SECONDS if success else None,
                           end_at=now+SESSION_CLOSE_SECONDS+DOWNLOAD_SECONDS if success else None,
                           operation_id='activation-'+identifier, file_id='activation-file-'+identifier,
                           instance_id='preview-'+identifier, closed=False, holder='', lease_until=0)
            self.save(conn, user, receipt)
        return receipt

    @staticmethod
    def payload(user, receipt):
        content = json.dumps(dict(kind='camera_visual_activation', version=1, owner=user,
                                 camera_id=CAMERA, receipt=receipt['id']), sort_keys=True)
        return dict(id=receipt['file_id'], name='Glass Eye.activation', file_category='system',
                    file_size=1, sellable=False, market_status='not_listed',
                    source_operation_id=receipt['operation_id'], content=content,
                    checksum=hashlib.sha256(content.encode()).hexdigest())

    def valid_file(self, conn, user, receipt):
        row = conn.execute('''SELECT file_json FROM player_data_files f
            WHERE username=? AND file_id=? AND operation_id=? AND NOT EXISTS
            (SELECT 1 FROM player_data_file_tombstones t WHERE t.username=f.username AND t.file_id=f.file_id)''',
                           (user, receipt['file_id'], receipt['operation_id'])).fetchone()
        if not row:
            return False
        try:
            file = json.loads(row['file_json'])
            expected = self.payload(user, receipt)
            return file.get('content') == expected['content'] and file.get('checksum') == expected['checksum']
        except (ValueError, TypeError):
            return False

    def tick(self, user, *, fail_write=False):
        now = self.now()
        with db_connect(self.path) as conn:
            receipt = self.load(conn, user)
        if not receipt or not receipt['success'] or now < receipt['start_at']:
            return
        if receipt['state'] in ('READY', 'WRITE_FAILED'):
            return
        if receipt['state']=='DOWNLOADING' and now<receipt['end_at']:
            return  # Progress is a read projection, not one SQLite write per UI poll.
        operation = dict(operation_id=receipt['operation_id'], owner_username=user,
                         operation_type='camera_activation_download', source_app_id='glass-eye-reference',
                         map_action_id='camera_stream', target_id=CAMERA,
                         status='running', duration_seconds=DOWNLOAD_SECONDS,
                         started_at=receipt['start_at'], expires_at=receipt['end_at'],
                         resource_buffer={'files': []})
        prepared = self.payload(user, receipt)
        # Tiny bounded documents prepared before acquiring SQLite writer lock.
        file_json = json.dumps(prepared)
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            receipt = self.load(conn, user)
            if receipt['state'] in ('READY', 'WRITE_FAILED'):
                return
            conn.execute('''INSERT OR IGNORE INTO player_operations
                (operation_id,username,target_key,operation_type,status,operation_json,created_at,updated_at)
                VALUES(?,?,?,'camera_activation_download','running',?,?,?)''',
                         (receipt['operation_id'], user, CAMERA, json.dumps(operation), str(now), str(now)))
            receipt['state'] = 'DOWNLOADING'
            if now >= receipt['end_at']:
                storage = conn.execute('SELECT capacity,used FROM player_storage WHERE username=?', (user,)).fetchone()
                exists = self.valid_file(conn, user, receipt)
                if fail_write or (not exists and storage['used']+1 > storage['capacity']):
                    receipt['state'] = 'WRITE_FAILED'
                    operation['status'] = 'failed'
                else:
                    if not exists:
                        conn.execute('''INSERT INTO player_data_files
                            (username,file_id,folder,operation_id,file_json,created_at,updated_at)
                            VALUES(?,?,'system',?,?,?,?)''',
                                     (user, receipt['file_id'], receipt['operation_id'], file_json, str(now), str(now)))
                        conn.execute('UPDATE player_storage SET used=used+1,version=version+1 WHERE username=?', (user,))
                    # Read-back in the same transaction; READY becomes visible only after COMMIT.
                    if not self.valid_file(conn, user, receipt):
                        raise RuntimeError('activation_write_verification_failed')
                    receipt['state'] = 'READY'
                    operation['status'] = 'completed'
                    operation['resource_buffer']['files'] = [dict(id=prepared['id'], name=prepared['name'])]
                conn.execute('UPDATE player_operations SET status=?,operation_json=?,version=version+1,updated_at=? WHERE operation_id=?',
                             (operation['status'], json.dumps(operation), str(now), receipt['operation_id']))
            self.save(conn, user, receipt)

    def snapshot(self, user):
        self.tick(user)
        now = self.now()
        with db_connect(self.path) as conn:
            receipt = self.load(conn, user)
            verified = bool(receipt and receipt['state']=='READY' and self.valid_file(conn, user, receipt))
        if receipt:
            receipt['progress'] = min(100, max(0, int((now-receipt['start_at'])/DOWNLOAD_SECONDS*100))) if receipt['success'] else 0
            receipt['file_verified'] = verified
        return dict(user=user, now=now, receipt=receipt,
                    operations=PlayerOperationStore(self.path).list_operations(user),
                    files=PlayerInventoryStore(self.path).list_data_files(user))

    def claim(self, user, document, *, explicit=False):
        now = self.clock()  # Test advances affect download time, never browser leases.
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            receipt = self.load(conn, user)
            if not receipt or receipt['state']!='READY' or not self.valid_file(conn, user, receipt):
                raise PermissionError('activation_not_verified')
            if receipt['closed'] and not explicit:
                return None
            if receipt['holder'] and receipt['holder']!=document and receipt['lease_until']>now:
                return None
            receipt.update(holder=document, lease_until=now+LEASE_SECONDS, closed=False)
            self.save(conn, user, receipt)
            return dict(instance_id=receipt['instance_id'], lease_seconds=LEASE_SECONDS)

    def release(self, user, document, *, closed=False):
        with db_connect(self.path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            receipt=self.load(conn,user)
            if receipt and receipt['holder']==document:
                receipt.update(holder='', lease_until=0, closed=closed)
                self.save(conn,user,receipt)

    def advance(self, seconds):
        with db_connect(self.path) as conn:
            conn.execute('UPDATE cvn_fixture_meta SET offset=offset+? WHERE id=1', (seconds,))
