from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from tools.ghost_content_155_migrate import backup, connect, migrate, snapshot
from contextlib import closing


class Content155MigrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'game.sqlite3'
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.executescript('''
                CREATE TABLE chat_messages(id INTEGER PRIMARY KEY,body TEXT,read_at TEXT);
                INSERT INTO chat_messages VALUES(7,'Player text',NULL);
                CREATE TABLE ghost_narrative_medium_records(medium_record_id TEXT PRIMARY KEY,body TEXT);
                INSERT INTO ghost_narrative_medium_records VALUES('original-id','Original news');
                CREATE TABLE rewards(id TEXT PRIMARY KEY,hc INTEGER,rsp INTEGER,receipt BLOB);
                INSERT INTO rewards VALUES('same-receipt',50,20,X'0012');
            ''')
        with closing(connect(self.path)) as conn:
            self.before = snapshot(conn)

    def test_dry_run_does_not_write_then_apply_preserves_every_original_field(self):
        original = self.path.read_bytes()
        self.assertEqual(migrate(self.path)['status'], 'dry_run')
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(migrate(self.path, True)['status'], 'migrated')
        self.assertEqual(migrate(self.path, True)['status'], 'already_migrated')
        with closing(connect(self.path)) as conn:
            self.assertEqual(snapshot(conn, self.before), self.before)
            self.assertEqual(conn.execute('SELECT system_copy_json FROM chat_messages').fetchone()[0], '{}')
            self.assertEqual(conn.execute('SELECT output_locale FROM ghost_narrative_medium_records').fetchone()[0], '')

    def test_failure_rolls_back_all_schema_changes(self):
        with patch('ghostnetwork.news_generation.initialize', side_effect=ValueError('failure')):
            with self.assertRaisesRegex(ValueError, 'failure'):
                migrate(self.path, True)
        with closing(connect(self.path)) as conn:
            self.assertEqual(snapshot(conn), self.before)

    def test_backup_captures_wal_and_refuses_overwrite(self):
        target = Path(self.tmp.name) / 'backup.sqlite3'
        with closing(sqlite3.connect(self.path)) as writer:
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute("UPDATE rewards SET hc=100 WHERE id='same-receipt'")
            writer.commit()
            self.assertEqual(backup(self.path, target)['status'], 'backed_up')
            with closing(connect(target)) as conn:
                self.assertEqual(conn.execute('SELECT hc FROM rewards').fetchone()[0], 100)
            with self.assertRaises(FileExistsError):
                backup(self.path, target)

    def test_baseline_detects_value_change_not_only_count(self):
        with closing(connect(self.path, True)) as conn, conn:
            conn.execute('UPDATE rewards SET hc=999')
        with closing(connect(self.path)) as conn:
            self.assertNotEqual(snapshot(conn, self.before), self.before)

    def test_missing_required_table_does_not_initialize_game(self):
        with closing(connect(self.path, True)) as conn, conn:
            conn.execute('DROP TABLE ghost_narrative_medium_records')
        with self.assertRaisesRegex(ValueError, 'required_table_missing'):
            migrate(self.path, True)
        with closing(connect(self.path)) as conn:
            self.assertNotIn('system_copy_json', [r[1] for r in conn.execute('PRAGMA table_info(chat_messages)')])

    def test_full_application_schema_can_be_rehearsed_without_copying_game_rows(self):
        from ghostnetwork.repository import GhostNetworkRepository
        from database import init_db
        path = Path(self.tmp.name) / 'full.sqlite3'
        init_db(str(path))
        GhostNetworkRepository(str(path))
        with closing(connect(path)) as conn:
            before = snapshot(conn)
        self.assertEqual(migrate(path)['status'], 'dry_run')
        migrate(path, True)
        with closing(connect(path)) as conn:
            self.assertEqual(snapshot(conn, before), before)
