import unittest
from database import db_connect
from ghostnetwork import narrative_locale_history as history
from ghostnetwork.news_locales import source_version
import test_news_locales as fixtures


class NarrativeLanguageHistoryTest(unittest.TestCase):
    def setUp(self):
        fixture=fixtures.NewsLocalesTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.path,self.read=fixture.path,fixture.read
        self.entry=dict(medium_record_id='record',source_version=source_version(self.read()),locale='pl')

    def test_dry_run_idempotence_and_rollback_touch_only_metadata(self):
        original=self.read()
        self.assertEqual(history.apply_batch(self.path,'batch',[self.entry],'editor')['status'],'dry_run')
        self.assertEqual(original,self.read())
        self.assertEqual(history.apply_batch(self.path,'batch',[self.entry],'editor',dry_run=False)['updated'],1)
        self.assertEqual(history.apply_batch(self.path,'batch',[self.entry],'editor',dry_run=False)['status'],'already_applied')
        self.assertEqual(self.read(),{**original,'output_locale':'pl'})
        history.rollback_batch(self.path,'batch')
        self.assertEqual(self.read()['output_locale'],'pl')
        history.rollback_batch(self.path,'batch',dry_run=False)
        self.assertEqual(original,self.read())

    def test_stale_review_and_rollback_fail_without_overwriting_publication(self):
        history.apply_batch(self.path,'batch',[self.entry],'editor',dry_run=False)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghost_narrative_medium_records SET body='New source'")
        with self.assertRaisesRegex(ValueError,'language_rollback_conflict'):
            history.rollback_batch(self.path,'batch',dry_run=False)
        self.assertEqual(self.read()['body'],'New source')
        with self.assertRaisesRegex(ValueError,'stale_language_source'):
            history.apply_batch(self.path,'batch-2',[self.entry],'editor',dry_run=False)

    def test_inventory_is_bounded_metadata_only_and_any_is_not_a_language(self):
        page=history.inventory(self.path,limit=1)
        self.assertEqual(page['next_after'],'record')
        self.assertTrue(page['records'][0]['review_required'])
        self.assertNotIn('body',page['records'][0])
        self.assertEqual(history.inventory(self.path,after='record')['records'],[])
        with self.assertRaisesRegex(ValueError,'unapproved_language'):
            history.apply_batch(self.path,'batch',[{**self.entry,'locale':'ANY'}],'editor')
