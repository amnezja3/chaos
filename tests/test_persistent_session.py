"""Durable expiry and Flask-Session cookie/storage integration, without game data."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import Flask, session
from flask_session import Session

from persistent_session import install_persistent_session_interface
from session_generation_store import SessionGenerationStore, SessionGenerationStateError


class PersistentSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / 'sessions.sqlite3')
        self.now = datetime.now(timezone.utc).replace(microsecond=0)
        self.store = SessionGenerationStore(self.path, clock=lambda: self.now)

    def activate(self, **kwargs):
        return self.store.activate('lineage', 'generation', 'alice', reason='test',
                                   persistence_days=(30, 90), **kwargs)

    def test_idle_boundary_and_expired_renewal_fail_closed(self):
        self.activate()
        self.now += timedelta(days=30) - timedelta(seconds=1)
        self.assertTrue(self.store.is_current('lineage', 'generation', 'alice'))
        self.now += timedelta(seconds=1)
        self.assertFalse(self.store.is_current('lineage', 'generation', 'alice'))
        with self.assertRaises(SessionGenerationStateError):
            self.store.renew('lineage', 'generation', 'alice')

    def test_renewal_throttles_without_extending_absolute_lifetime(self):
        self.activate()
        start = self.now
        self.now += timedelta(seconds=299)
        self.assertFalse(self.store.renew('lineage', 'generation', 'alice'))
        self.now += timedelta(seconds=1)
        self.assertTrue(self.store.renew('lineage', 'generation', 'alice'))
        for day in (20, 40, 60, 80, 89):
            self.now = start + timedelta(days=day)
            self.assertTrue(self.store.renew('lineage', 'generation', 'alice'))
        state = self.store.get_state('lineage')
        self.assertEqual(state['absolute_expires_at'], state['idle_expires_at'])
        self.now = start + timedelta(days=90)
        self.assertFalse(self.store.is_current('lineage', 'generation', 'alice'))

    def test_restart_preserves_expiry_and_read_does_not_renew(self):
        self.activate()
        before = self.store.get_state('lineage')
        self.now += timedelta(days=29)
        restarted = SessionGenerationStore(self.path, clock=lambda: self.now)
        self.assertTrue(restarted.is_current('lineage', 'generation', 'alice'))
        self.assertEqual(before, restarted.get_state('lineage'))
        self.now += timedelta(days=1)
        self.assertFalse(restarted.is_current('lineage', 'generation', 'alice'))

    def test_legacy_is_not_silently_granted_persistence(self):
        self.store.activate('lineage', 'generation', 'alice', reason='legacy')
        self.assertFalse(self.store.renew('lineage', 'generation', 'alice'))
        self.assertIsNone(self.store.get_state('lineage')['absolute_expires_at'])

    def test_replaced_and_revoked_sessions_cannot_renew(self):
        self.activate()
        self.store.activate('other', 'new', 'alice', reason='login', persistence_days=(30, 90))
        with self.assertRaises(SessionGenerationStateError):
            self.store.renew('lineage', 'generation', 'alice')
        self.store.revoke_all_by_username('alice', reason='security')
        with self.assertRaises(SessionGenerationStateError):
            self.store.renew('other', 'new', 'alice')

    def test_invalid_expiry_and_unknown_policy_fail_closed(self):
        self.activate()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("UPDATE session_generation_lineages SET idle_expires_at='broken'")
        self.assertFalse(self.store.is_current('lineage', 'generation', 'alice'))
        self.activate()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('UPDATE session_generation_lineages SET persistence_policy_version=99')
        self.assertFalse(self.store.is_current('lineage', 'generation', 'alice'))

    def test_expiry_rejects_precommit_and_rolls_back(self):
        self.activate()
        guard = self.store.build_transaction_precommit_guard('lineage', 'generation', 'alice')
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('CREATE TABLE actions (value TEXT)')
        with self.assertRaises(SessionGenerationStateError):
            with closing(sqlite3.connect(self.path)) as conn, conn:
                conn.execute("INSERT INTO actions VALUES ('reward')")
                self.now += timedelta(days=30)
                guard(conn=conn)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            self.assertEqual(0, conn.execute('SELECT count(*) FROM actions').fetchone()[0])

    def app(self):
        app = Flask(__name__)
        app.config.update(TESTING=True, SECRET_KEY='isolated-test-only', SESSION_TYPE='filesystem',
                          SESSION_FILE_DIR=str(Path(self.temp.name) / 'cookies'),
                          SESSION_PERMANENT=False, SESSION_REFRESH_EACH_REQUEST=False,
                          SESSION_COOKIE_SAMESITE='Lax', SESSION_FILE_THRESHOLD=0)
        Session(app)
        install_persistent_session_interface(app, lambda: self.store)

        @app.post('/login')
        def login():
            result = self.activate(login_identity_secret='identity')
            session.update(user='alice', session_lineage='lineage', session_generation='generation',
                           session_login_identity='identity', session_account_revision=result['account_revision'])
            return 'ok'

        @app.get('/read')
        def read():
            return session.get('user', 'anonymous')

        @app.get('/replace')
        def replace():
            self.store.activate('other', 'new', 'alice', reason='concurrent_login')
            session['modified'] = True
            return 'private content'

        @app.get('/old-recovery')
        def recovery():
            self.store.activate('other', 'new', 'alice', reason='concurrent_login')
            session.clear()
            session['login_error'] = 'old recovery'
            return 'recovery'

        @app.get('/old-logout')
        def logout():
            self.store.revoke('lineage', 'generation', reason='logout')
            session.clear()
            self.store.activate('other', 'new', 'alice', reason='concurrent_login')
            return 'logged out'
        return app

    def test_cookie_and_restart_and_polling(self):
        app = self.app()
        client = app.test_client()
        response = client.post('/login', base_url='https://localhost')
        cookie = response.headers['Set-Cookie']
        for flag in ('Secure', 'HttpOnly', 'SameSite=Lax', 'Expires='):
            self.assertIn(flag, cookie)
        sid = client.get_cookie('session').value
        # A new app object shares only durable DB and session files.
        restarted = self.app().test_client()
        restarted.set_cookie('session', sid)
        response = restarted.get('/read', base_url='https://localhost')
        self.assertEqual(b'alice', response.data)
        self.assertNotIn('Set-Cookie', response.headers)
        self.now += timedelta(days=30)
        response = restarted.get('/read', base_url='https://localhost')
        self.assertEqual(409, response.status_code)
        self.assertNotIn('Set-Cookie', response.headers)
        self.assertNotIn(b'alice', response.data)

    def test_stale_response_and_recovery_never_emit_cookie(self):
        client = self.app().test_client()
        for path in ('/replace', '/old-recovery', '/old-logout'):
            client.post('/login', base_url='https://localhost')
            response = client.get(path, base_url='https://localhost')
            self.assertNotIn('Set-Cookie', response.headers)
            if path == '/replace':
                self.assertEqual(409, response.status_code)
                self.assertNotIn(b'private content', response.data)


if __name__ == '__main__':
    unittest.main()
