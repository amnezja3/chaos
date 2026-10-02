import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from database import _ensure_desktop_projection_columns


class DesktopSchemaStartupTest(unittest.TestCase):
    def test_two_workers_observe_missing_column_before_either_adds_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / 'test.sqlite3')
            with closing(sqlite3.connect(path, isolation_level=None)) as conn:
                conn.execute('CREATE TABLE user_identity_projection (username TEXT PRIMARY KEY, desktop_boot_json TEXT)')
                conn.execute("INSERT INTO user_identity_projection VALUES ('alice', 'preserved')")
            barrier = threading.Barrier(2)

            def worker():
                with closing(sqlite3.connect(path, timeout=10, isolation_level=None)) as conn:
                    class RacingConnection:
                        reads = 0

                        def execute(self, sql):
                            result = conn.execute(sql)
                            if sql.startswith('PRAGMA'):
                                rows = result.fetchall()
                                self.reads += 1
                                if self.reads == 2:
                                    barrier.wait(timeout=10)
                                return rows
                            return result

                    _ensure_desktop_projection_columns(RacingConnection())

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(worker) for _ in range(2)]
                for future in futures:
                    future.result(timeout=20)
            with closing(sqlite3.connect(path, isolation_level=None)) as conn:
                _ensure_desktop_projection_columns(conn)
                columns = [r[1] for r in conn.execute('PRAGMA table_info(user_identity_projection)')]
                self.assertEqual(columns.count('desktop_settings_json'), 1)
                self.assertEqual(conn.execute('SELECT desktop_boot_json FROM user_identity_projection').fetchone()[0], 'preserved')

    def test_non_duplicate_error_is_not_swallowed(self):
        class LockedConnection:
            def execute(self, sql):
                if sql.startswith('PRAGMA'):
                    return []
                raise sqlite3.OperationalError('database is locked')
        with self.assertRaisesRegex(sqlite3.OperationalError, 'database is locked'):
            _ensure_desktop_projection_columns(LockedConnection())

    def test_duplicate_requires_matching_column_in_database(self):
        class BrokenConnection:
            def execute(self, sql):
                if sql.startswith('PRAGMA'):
                    return []
                raise sqlite3.OperationalError('duplicate column name: desktop_boot_json')
        with self.assertRaisesRegex(sqlite3.OperationalError, 'duplicate column'):
            _ensure_desktop_projection_columns(BrokenConnection())
