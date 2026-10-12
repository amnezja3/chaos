import tempfile
import unittest
from pathlib import Path

from database import db_connect
from ghostnetwork.repository import GhostNetworkRepository
from ghostnetwork.news_locales import NewsLocaleStore, source_version
from googleplex_news import build_googleplex_news_snapshot, merge_googleplex_news_publications


class NewsLocalesTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = str(Path(temporary.name) / 'news.sqlite3')
        self.repo = GhostNetworkRepository(self.path)
        self.store = NewsLocaleStore(self.path)
        fields = dict(medium_record_id='record', publication_receipt_id='receipt',
            candidate_id='candidate',task_id='task',target_medium='googleplex_news',
            audience_scope='public',source_scope='blacknet_world',truth_class='canonical',
            title='Wiadomość',body='Informacja o świecie.',fact_refs_json='["fact:one"]',
            presentation_slot='gp-home-world-grid',created_at='2026-10-12',published_at='2026-10-12')
        with db_connect(self.path) as conn:
            conn.execute('INSERT INTO ghost_narrative_medium_records ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',tuple(fields.values()))
        self.record = self.read()

    def read(self):
        with db_connect(self.path) as conn:
            return self.repo._narrative_medium_record(conn.execute('SELECT * FROM ghost_narrative_medium_records WHERE medium_record_id="record"').fetchone())

    def save(self, **changes):
        args=dict(record_id='record',expected_version=source_version(self.record),locale='en',title='World update',body='Information about the world.',reviewed_by='test-editor')
        args.update(changes)
        return self.store.save_reviewed_variant(**args)

    def test_reviewed_variant_is_idempotent_and_never_republishes(self):
        self.assertTrue(self.save())
        self.assertFalse(self.save())
        self.assertEqual(self.record,self.read())
        with db_connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM ghost_narrative_medium_records').fetchone()[0],1)
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM ghost_news_locale_variants').fetchone()[0],1)
        variants = self.store.for_records([self.record])
        base=build_googleplex_news_snapshot(catalog=[],viewer_key='test',session_generation='test')
        pl=merge_googleplex_news_publications(base,[self.record],locale='pl',locale_variants=variants)['entries'][0]
        en=merge_googleplex_news_publications(base,[self.record],locale='en',locale_variants=variants)['entries'][0]
        self.assertEqual(en['content']['title'],'World update')
        for key in ('news_id','source_ref','published_at'):
            self.assertEqual(pl['content'][key],en['content'][key])
        self.assertEqual(pl['action'],en['action'])

    def test_stale_variants_are_not_read_or_written(self):
        self.save()
        with db_connect(self.path) as conn:
            conn.execute('UPDATE ghost_narrative_medium_records SET source_state_version=2')
        self.assertEqual(self.store.for_records([self.read()]),{})
        with self.assertRaisesRegex(ValueError,'stale_news_source'):
            self.save(locale='pl')

    def test_archive_uses_frozen_version_and_never_translates_blacknet(self):
        self.save()
        snapshot = dict(medium='googleplex_news', medium_record_id='record',
                        source_version=source_version(self.record))
        expected = self.store.for_frozen_publications([snapshot])
        self.assertEqual(expected['record']['en']['title'], 'World update')
        with db_connect(self.path) as conn:
            conn.execute('UPDATE ghost_narrative_medium_records SET source_state_version=2')
        self.assertEqual(self.store.for_frozen_publications([snapshot]), expected)
        self.assertEqual(self.store.for_frozen_publications([
            {**snapshot, 'source_version': source_version(self.read())}]), {})
        self.assertEqual(self.store.for_frozen_publications([
            {**snapshot, 'medium': 'blacknet'}, {'medium':'googleplex_news'}]), {})

    def test_conflict_unapproved_locale_and_other_medium_rejected(self):
        self.save()
        with self.assertRaisesRegex(ValueError,'variant_conflict'):
            self.save(body='Changed prose.')
        with self.assertRaisesRegex(ValueError,'unapproved_locale'):
            self.save(locale='ANY')
        with db_connect(self.path) as conn:
            conn.execute('UPDATE ghost_narrative_medium_records SET target_medium="blacknet"')
        with self.assertRaisesRegex(ValueError,'not_news_publication'):
            self.save()

    def test_missing_english_is_explicit_not_polish_prose(self):
        base=build_googleplex_news_snapshot(catalog=[],viewer_key='test',session_generation='test')
        en=merge_googleplex_news_publications(base,[self.record],locale='en')['entries'][0]['content']
        self.assertNotEqual(en['title'],self.record['title'])
        self.assertIn('not available yet',en['summary'])
        self.assertEqual(en['locale_fallbacks'],['en'])

    def entry(self, **changes):
        return dict(medium_record_id='record', source_version=source_version(self.record),
                    locale='en', title='World update', body='Information about the world.', **changes)

    def test_batch_dry_run_apply_retry_rollback_preserves_publication(self):
        entries = [self.entry()]
        before = self.read()
        result = self.store.apply_batch('batch-1', entries, reviewed_by='editor')
        self.assertEqual(result, {'status':'dry_run','inserted':1})
        self.assertEqual(self.store.for_records([self.record]), {})
        self.assertEqual(self.store.apply_batch('batch-1', entries, reviewed_by='editor', dry_run=False)['inserted'], 1)
        self.assertEqual(self.store.apply_batch('batch-1', entries, reviewed_by='editor', dry_run=False)['status'], 'already_applied')
        self.assertEqual(self.store.rollback_batch('batch-1')['deleted'], 1)
        self.assertTrue(self.store.for_records([self.record]))
        self.assertEqual(self.store.rollback_batch('batch-1', dry_run=False)['deleted'], 1)
        self.assertEqual(self.store.rollback_batch('batch-1', dry_run=False)['status'], 'already_rolled_back')
        self.assertEqual(self.store.for_records([self.record]), {})
        self.assertEqual(before, self.read())

    def test_batch_failure_is_atomic_and_can_resume_after_correction(self):
        bad = {**self.entry(), 'locale':'ANY'}
        with self.assertRaisesRegex(ValueError, 'unapproved_locale'):
            self.store.apply_batch('atomic', [self.entry(), bad], reviewed_by='editor', dry_run=False)
        self.assertEqual(self.store.for_records([self.record]), {})
        self.assertEqual(self.store.apply_batch('atomic', [self.entry()], reviewed_by='editor', dry_run=False)['inserted'], 1)
        with self.assertRaisesRegex(ValueError, 'batch_conflict'):
            self.store.apply_batch('atomic', [{**self.entry(),'body':'Changed.'}], reviewed_by='editor')

    def test_rollback_does_not_remove_preexisting_variant(self):
        self.save()
        self.assertEqual(self.store.apply_batch('preexisting', [self.entry()], reviewed_by='editor', dry_run=False)['inserted'], 0)
        self.assertEqual(self.store.rollback_batch('preexisting', dry_run=False)['deleted'], 0)
        self.assertTrue(self.store.for_records([self.record]))

    def test_inventory_checkpoint_is_metadata_only_and_source_visibility_invalidates_variant(self):
        self.save()
        page = self.store.inventory(limit=1)
        self.assertEqual(page['next_after'], 'record')
        self.assertEqual(page['records'][0]['locales'], ['en'])
        self.assertNotIn('body', page['records'][0])
        self.assertEqual(self.store.inventory(after=page['next_after'])['records'], [])
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghost_narrative_medium_records SET audience_scope='owner'")
        self.assertEqual(self.store.for_records([self.read()]), {})

    def test_product_promo_is_excluded(self):
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghost_narrative_medium_records SET content_kind='product_promo'")
        self.record = self.read()
        self.assertTrue(self.store.inventory()['records'][0]['excluded'])
        with self.assertRaisesRegex(ValueError, 'user_content_excluded'):
            self.save()
