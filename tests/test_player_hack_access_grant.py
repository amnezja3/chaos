import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Barrier
from unittest.mock import patch

from database import PlayerHackAccessStore, db_connect


class PlayerHackAccessGrantTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = PlayerHackAccessStore(os.path.join(tmp.name, 'game.sqlite3'))

    def test_retry_preserves_deadlines_and_consumed_tool(self):
        first = self.store.grant_access('attacker', 'victim')
        self.store.record_tool_usage(first, 'attacker', 'victim', 'intruderKicker', result='done')
        later = datetime.utcnow() + timedelta(minutes=1)
        with patch('database.datetime', wraps=datetime) as clock:
            clock.utcnow.return_value = later
            retry = self.store.grant_access('attacker', 'victim', access_minutes=30)
        for field in ('id', 'hacked_until', 'cooldown_until', 'created_at', 'updated_at'):
            self.assertEqual(first[field], retry[field], field)
        self.assertEqual(self.store.access_key(first), self.store.access_key(retry))
        self.assertTrue(self.store.has_tool_usage(retry, 'attacker', 'victim', 'intruderKicker'))

    def test_concurrent_grants_share_one_deadline(self):
        barrier = Barrier(2)
        def grant(minutes):
            barrier.wait(timeout=10)
            return self.store.grant_access('attacker', 'victim', access_minutes=minutes)
        with ThreadPoolExecutor(max_workers=2) as pool:
            grants = list(pool.map(grant, (5, 30)))
        self.assertEqual(self.store.access_key(grants[0]), self.store.access_key(grants[1]))
        with db_connect(self.store.db_path) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM player_hack_access').fetchone()[0], 1)

    def test_other_target_has_independent_access(self):
        first = self.store.grant_access('attacker', 'victim')
        second = self.store.grant_access('attacker', 'other')
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(self.store.get_active_access('attacker', 'victim')['id'], first['id'])

    def test_new_grant_after_access_and_cooldown_expire(self):
        first = self.store.grant_access('attacker', 'victim')
        later = datetime.utcnow() + timedelta(hours=4)
        with patch('database.datetime', wraps=datetime) as clock:
            clock.utcnow.return_value = later
            renewed = self.store.grant_access('attacker', 'victim')
        self.assertNotEqual(self.store.access_key(first), self.store.access_key(renewed))


if __name__ == '__main__':
    unittest.main()
