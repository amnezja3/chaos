"""Shared world storage must not inherit the raw-cache payload ceiling."""
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from poi_infrastructure.repository import Repository


class DatabaseCapacityTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'poi.sqlite3'
        self.repo = Repository(self.path, max_bytes=512 * 1024,
                               max_database_bytes=4 * 1024 * 1024)
        self.repo.initialize()
        with self.repo.transaction() as conn:
            conn.execute('CREATE TABLE world_fixture (payload BLOB)')
            conn.execute('INSERT INTO world_fixture VALUES (zeroblob(700000))')

    def test_legacy_limit_reproduces_full_then_new_writer_preserves_world(self):
        conn = self.repo.connect()
        try:
            conn.execute('PRAGMA max_page_count=256')  # old cache * 2 = 1 MiB
            with self.assertRaisesRegex(sqlite3.OperationalError, 'full'):
                conn.execute('INSERT INTO world_fixture VALUES (zeroblob(700000))')
        finally:
            conn.close()
        # Reopen as another process with a smaller cache; shared DB cap is independent.
        reopened = Repository(self.path, max_bytes=128,
                              max_database_bytes=4 * 1024 * 1024)
        with reopened.transaction() as conn:
            conn.execute('INSERT INTO world_fixture VALUES (zeroblob(700000))')
            self.assertEqual(conn.execute('SELECT sum(length(payload)) FROM world_fixture').fetchone()[0], 1400000)
        owner = reopened.acquire('scan', 60)
        self.assertFalse(reopened.write('scan', owner, {'data': 'x' * 200}, 60))
        self.assertTrue(reopened.write('scan', owner, {'data': 'ok'}, 60))
        reopened.release('scan', owner)
        self.assertEqual(reopened.read('scan', 60), {'data': 'ok'})

    def test_shared_physical_limit_still_blocks_and_rolls_back(self):
        limited = Repository(self.path, max_database_bytes=1024 * 1024)
        with self.assertRaisesRegex(sqlite3.OperationalError, 'full'):
            with limited.transaction() as conn:
                conn.execute('INSERT INTO world_fixture VALUES (zeroblob(700000))')
        with self.repo.transaction() as conn:
            self.assertEqual(conn.execute('SELECT count(*) FROM world_fixture').fetchone()[0], 1)

    def test_environment_applies_to_direct_and_cache_configured_clients(self):
        with patch.dict(os.environ, {'CHAOS_POI_MAX_DATABASE_BYTES': str(8 * 1024 * 1024)}):
            self.assertEqual(Repository(self.path).max_database_bytes, 8 * 1024 * 1024)
            self.assertEqual(Repository(self.path, 1024).max_database_bytes, 8 * 1024 * 1024)
        for value in ('0', '-1', 'unlimited', str(17 * 1024 ** 3)):
            with self.subTest(value=value), patch.dict(os.environ, {'CHAOS_POI_MAX_DATABASE_BYTES': value}):
                with self.assertRaises(ValueError):
                    Repository(self.path)
