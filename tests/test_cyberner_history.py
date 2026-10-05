import unittest
from datetime import datetime, timedelta, timezone
from cyberner_history import world_history


class WorldHistoryTests(unittest.TestCase):
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)

    def messages(self, count, days=0):
        return [dict(id=i, created_at=(self.now - timedelta(days=days)).isoformat())
                for i in range(1, count + 1)]

    def test_count_and_cursor_cannot_escape_window(self):
        rows = self.messages(150)
        self.assertEqual(len(world_history(rows, now=self.now, limit=999)), 100)
        self.assertEqual(world_history(rows, now=self.now)[0]['id'], 51)
        self.assertEqual(world_history(rows, now=self.now, before_id=51), [])
        self.assertEqual(world_history(rows, now=self.now, after_id=150), [])

    def test_old_history_falls_back_to_ten(self):
        rows = self.messages(120, days=15)
        self.assertEqual([m['id'] for m in world_history(rows, now=self.now)], list(range(111, 121)))
        self.assertEqual(len(world_history(rows, now=self.now, limit=1)), 1)
        self.assertEqual(world_history(rows, now=self.now, after_id=120), [])

    def test_recent_messages_do_not_get_old_padding(self):
        rows = self.messages(20, days=15) + [dict(id=21, created_at=self.now.isoformat())]
        self.assertEqual([m['id'] for m in world_history(rows, now=self.now)], [21])

    def test_boundary_utc_empty_and_short_history(self):
        self.assertEqual(len(world_history(self.messages(3, days=14), now=self.now)), 3)
        self.assertEqual(len(world_history(self.messages(3, days=20), now=self.now)), 3)
        self.assertEqual(world_history([], now=self.now), [])
        rows = [dict(id=1, created_at='2026-09-21T00:00:00Z'),
                dict(id=2, created_at='2026-09-20T23:59:59'),
                dict(id=3, created_at='bad date')]
        self.assertEqual([m['id'] for m in world_history(rows, now=self.now)], [1])

    def test_conflicting_cursors_rejected(self):
        with self.assertRaises(ValueError):
            world_history([], after_id=1, before_id=3)


if __name__ == '__main__':
    unittest.main()
