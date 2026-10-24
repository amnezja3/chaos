from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from poi_infrastructure.repository import Repository


class WalGuardTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Repository(Path(self.directory.name) / 'poi.sqlite3')
        self.repo.initialize()

    def test_wal_disappears_before_stat(self):
        with patch.object(Path, 'stat', side_effect=FileNotFoundError):
            with self.repo.transaction() as conn:
                conn.execute("INSERT INTO providers VALUES ('fixture', 0, 0)")
        conn = self.repo.connect()
        try:
            self.assertEqual(conn.execute('SELECT count(*) FROM providers').fetchone()[0], 1)
        finally:
            conn.close()

    def test_oversized_wal_still_blocks_before_connect(self):
        size = self.repo.max_bytes + 8 * 1024 * 1024 + 1
        with patch.object(Path, 'stat', return_value=SimpleNamespace(st_size=size)), \
                patch.object(self.repo, 'connect') as connect:
            with self.assertRaisesRegex(sqlite3.OperationalError, 'poi_wal_capacity'):
                with self.repo.transaction():
                    self.fail('must not enter transaction')
            connect.assert_not_called()

    def test_permission_failure_is_not_treated_as_missing(self):
        with patch.object(Path, 'stat', side_effect=PermissionError), \
                patch.object(self.repo, 'connect') as connect:
            with self.assertRaises(PermissionError):
                with self.repo.transaction():
                    self.fail('must not enter transaction')
            connect.assert_not_called()
