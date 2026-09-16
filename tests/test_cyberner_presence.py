import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import run
from database import MailStore, db_connect


class CybernerPresenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'presence.sqlite3')
        self.store = MailStore(self.path)
        with db_connect(self.path) as conn:
            for name in ('alice', 'bob', 'carol'):
                conn.execute("INSERT INTO users(username,password,salt,profile_json,created_at,updated_at) VALUES (?, '', '', '{}', '', '')", (name,))
            conn.execute("INSERT INTO contacts(owner_username,contact_name,status,created_at) VALUES ('alice','bob','offline','')")

    def test_world_counts_non_contacts_and_contact_status_is_live(self):
        for name in ('alice', 'bob', 'carol', 'deleted-account'):
            self.store.touch_presence(name)
        self.assertEqual(self.store.group_active_count('alice'), 3)
        self.assertEqual(self.store.list_contacts('alice'), [{'name': 'bob', 'status': 'online'}])
        stale = (datetime.utcnow() - timedelta(seconds=91)).isoformat(timespec='seconds')
        with db_connect(self.path) as conn:
            conn.execute("UPDATE mail_presence SET last_seen_at=? WHERE username='bob'", (stale,))
        self.assertEqual(self.store.list_contacts('alice')[0]['status'], 'offline')
        self.assertEqual(self.store.group_active_count('alice'), 2)

    def test_recent_heartbeat_does_not_write_again(self):
        self.store.touch_presence('alice')
        with db_connect(self.path) as conn:
            before = conn.execute("SELECT last_seen_at FROM mail_presence WHERE username='alice'").fetchone()[0]
        with patch('database.utc_now', return_value='2099-01-01T00:00:00'):
            self.store.touch_presence('alice')
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute("SELECT last_seen_at FROM mail_presence WHERE username='alice'").fetchone()[0], before)

    def test_desktop_poll_updates_presence_without_cyberner_or_profile_read(self):
        delta = Mock()
        delta.get_changes_since.return_value = {'changes': [], 'current_version': 0}
        with patch.object(run, 'mail_store', self.store), patch.object(run, 'delta_bus', delta), \
             patch.object(run, 'get_ghostsignal_show_service', return_value=Mock()), \
             patch.object(run.user_store, 'get_profile', side_effect=AssertionError('profile read')), \
             patch.object(run.user_store, 'list_profiles', side_effect=AssertionError('profile scan')):
            for name in ('alice', 'bob', 'carol'):
                with run.app.test_request_context('/api/state/changes'):
                    run.session['user'] = name
                    self.assertEqual(run.api_state_changes().status_code, 200)
            with run.app.test_request_context('/api/state/changes'):
                response, status = run.api_state_changes()
                self.assertEqual(status, 401)
        self.assertEqual(self.store.group_active_count('alice'), 3)
        self.assertEqual(self.store.list_contacts('alice')[0]['status'], 'online')
