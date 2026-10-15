import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ghostnetwork.public_teaser import select_public_teaser
from ghostnetwork.repository import GhostNetworkRepository


def seed_teaser(db_path, key, scope='public', state='active', expiry='', medium='blacknet'):
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute('''INSERT INTO ghost_narrative_medium_records
            (medium_record_id, publication_receipt_id, candidate_id, task_id,
             target_medium, audience_scope, source_scope, truth_class, title, body,
             active_state, valid_until, created_at, published_at)
            VALUES (?, ?, ?, ?, ?, ?, 'world', 'canonical', ?, ?, ?, ?, ?, ?)''',
            (key, key, key, key, medium, scope, 'Signal ' + key, 'Body ' + key,
             state, expiry, '2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00'))
        connection.commit()


class PublicBlacknetTeaserTests(unittest.TestCase):
    def test_real_repository_excludes_private_expired_and_other_media(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'world.db')
            repository = GhostNetworkRepository(db_path=path)
            seed_teaser(path, 'one')
            seed_teaser(path, 'two')
            seed_teaser(path, 'private', scope='owner')
            seed_teaser(path, 'clan', scope='clan')
            seed_teaser(path, 'inactive', state='expired')
            seed_teaser(path, 'expired', expiry='2000-01-01T00:00:00+00:00')
            seed_teaser(path, 'news', medium='googleplex_news')
            before = Path(path).read_bytes()
            with patch('ghostnetwork.public_teaser.secrets.choice', side_effect=lambda rows: rows[0]) as choose:
                result = select_public_teaser(repository)
                self.assertEqual({r['title'] for r in choose.call_args.args[0]}, {'Signal one', 'Signal two'})
                self.assertEqual(set(result), {'title', 'body', 'locale'})
                select_public_teaser(repository)
                self.assertEqual(choose.call_count, 2)  # fresh draw per rendered gate
            self.assertEqual(Path(path).read_bytes(), before)

    def test_anonymous_gate_escapes_text_and_does_not_expose_metadata(self):
        import run
        record = dict(audience_scope='public', active_state='active',
                      title='<script>alert(1)</script>', body='Public text',
                      cta_payload={'private': 'DO_NOT_EXPOSE'}, output_locale='en')
        repository = SimpleNamespace(list_narrative_medium_records=lambda *a, **k: [record])
        with run.app.test_request_context('/?login=1'), patch.object(
                run, 'get_ghostnetwork_service', return_value=SimpleNamespace(repository=repository)):
            response = run.render_login_gate()
            html = response.get_data(as_text=True)
            self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
            self.assertNotIn('DO_NOT_EXPOSE', html)
            self.assertEqual(html.count('data-public-blacknet'), 1)
            self.assertIn('READ ONLY', html)
            self.assertNotIn('href="#gate-login"', html)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_empty_and_repository_failure_leave_gate_usable(self):
        import run
        self.assertIsNone(select_public_teaser(SimpleNamespace(list_narrative_medium_records=lambda *a, **k: [])))
        with run.app.test_request_context('/?login=1'), patch.object(
                run, 'get_ghostnetwork_service', side_effect=RuntimeError('unavailable')):
            response = run.render_login_gate()
            self.assertEqual(response.status_code, 200)
            self.assertIn('entry.blacknet.quiet', response.get_data(as_text=True))
            self.assertIn('name="password"', response.get_data(as_text=True))
