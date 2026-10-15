import hashlib
import sqlite3
import struct
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from tools.session_156_maintenance import migrate, cleanup


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_migration_dry_run_then_idempotent_apply_preserves_data(self):
        db = self.root / 'game.sqlite3'
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute('CREATE TABLE session_generation_lineages (lineage_hash TEXT PRIMARY KEY, revision INTEGER)')
            conn.execute("INSERT INTO session_generation_lineages VALUES ('old',7)")
            conn.execute('CREATE TABLE rewards(id INTEGER PRIMARY KEY, value TEXT)')
            conn.execute("INSERT INTO rewards VALUES (42,'keep')")
        before = hashlib.sha256(db.read_bytes()).digest()
        result = migrate(db)
        self.assertEqual(5, len(result['added_columns']))
        self.assertEqual(before, hashlib.sha256(db.read_bytes()).digest())
        self.assertTrue(migrate(db, True)['original_data_unchanged'])
        self.assertEqual([], migrate(db, True)['added_columns'])
        with closing(sqlite3.connect(db)) as conn:
            self.assertEqual(('old', 7, 0), conn.execute(
                'SELECT lineage_hash,revision,persistence_policy_version FROM session_generation_lineages').fetchone())
            self.assertEqual((42, 'keep'), conn.execute('SELECT * FROM rewards').fetchone())

    def test_cleanup_expired_only_no_deserialization_and_offline_gate(self):
        for name, expiry in [('a', 10), ('b', 999), ('c', 0)]:
            (self.root / (name * 32)).write_bytes(struct.pack('I', expiry) + b'not-a-pickle')
        (self.root / ('d' * 32)).write_bytes(b'bad')
        (self.root / 'game.sqlite3').write_bytes(b'keep')
        result = cleanup(self.root, now=100)
        self.assertEqual(1, result['expired'])
        self.assertEqual(0, result['removed'])
        with self.assertRaises(ValueError):
            cleanup(self.root, apply=True, now=100)
        result = cleanup(self.root, apply=True, writers_stopped=True, now=100)
        self.assertEqual(1, result['removed'])
        self.assertFalse((self.root / ('a' * 32)).exists())
        for name in ('b' * 32, 'c' * 32, 'd' * 32, 'game.sqlite3'):
            self.assertTrue((self.root / name).exists())
        self.assertLessEqual(cleanup(self.root, limit=1)['checked'], 1)


if __name__ == '__main__':
    unittest.main()
