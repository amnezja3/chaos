import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from database import db_connect
from ghostnetwork.editorial import GoogleplexEditorialProducer
from ghostnetwork.news_generation import NewsLocaleWorker, build_package, validate_variant
from ghostnetwork.llm.provider import NarrativeProviderError
import test_news_locales as fixtures


class NewsGenerationTests(unittest.TestCase):
    def setUp(self):
        fixture = fixtures.NewsLocalesTest()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.repo, self.path, self.store = fixture.repo, fixture.path, fixture.store
        self.read = fixture.read
        producer = GoogleplexEditorialProducer(self.repo)
        catalog = [{'id':'tool','name':'Original user title','published':True}]
        producer.enqueue_next(catalog)
        self.task = producer.enqueue_next(catalog)['task']
        self.refs = [f['fact_id'] for f in self.task['facts']]
        with db_connect(self.path) as conn:
            conn.execute('''UPDATE ghost_narrative_medium_records SET task_id=?,
                fact_refs_json=?,active_state='active',content_kind='navigation_promo',
                presentation_slot='gp-home-blacknet' ''', (self.task['outbox_id'],json.dumps(self.refs)))
            conn.execute('''INSERT INTO ghost_narrative_slot_state(target_medium,slot_id,active_medium_record_id)
                VALUES ('googleplex_news','gp-home-blacknet','record')
                ON CONFLICT(target_medium,slot_id) DO UPDATE SET active_medium_record_id='record' ''')
        self.record = self.read()
        self.calls = 0
        self.error = None
        self.hook = lambda: None
        self.router = SimpleNamespace(config={'total_seconds':1},generate=self.generate)
        self.worker = NewsLocaleWorker(self.repo, self.router)

    def content(self, **overrides):
        package = build_package(self.task, self.record)
        output = dict(title='Listen to BlackNet', body='Follow the signals of the network.',
            tone='mystery', fact_refs=list(package['fact_refs']), cta_ref=None,
            asset_role=next(iter(package['allowed_asset_roles']), None))
        output.update(overrides)
        return json.dumps(output)

    def generate(self, package, policy, **kwargs):
        self.calls += 1
        self.assertTrue(kwargs['guard']())
        self.hook()
        if self.error:
            raise self.error
        return SimpleNamespace(content=self.content())

    def test_en_prompt_replaces_both_layers_and_preserves_facts_and_identity(self):
        before = copy.deepcopy(self.task)
        package = build_package(self.task, self.record)
        prompt = package['messages'][0]['content']
        self.assertIn('Write English title/body', prompt)
        self.assertNotIn('Napisz', prompt)
        self.assertNotIn('po polsku', prompt)
        self.assertEqual(package['news_language_contract']['output_locale'], 'en')
        self.assertEqual(json.loads(package['messages'][1]['content'])['output_locale'], 'en')
        self.assertEqual(before, self.task)
        for locale in ('ANY','ru','en-US','pl'):
            with self.assertRaisesRegex(ValueError,'unapproved_news_generation_locale'):
                build_package(self.task,self.record,locale)

    def test_generation_writes_variant_once_without_publication_changes(self):
        before = self.read()
        self.assertEqual(self.worker.enqueue_active(),1)
        self.assertEqual(self.worker.enqueue_active(),0)
        result = self.worker.process_once()
        self.assertEqual(result['result'],'news_variant_completed',result)
        self.assertEqual(self.worker.process_once()['result'],'idle')
        self.assertEqual(self.worker.enqueue_active(),0)
        self.assertEqual(self.calls,1)
        self.assertEqual(self.read(),before)
        self.assertIn('en',self.store.for_records([self.record])['record'])

    def test_additional_news_locale_uses_registry_without_application_branch(self):
        from ghostnetwork.narrative_locale import language_registry
        registry = copy.deepcopy(language_registry())
        registry['zz'] = copy.deepcopy(registry['en'])
        with patch('ghostnetwork.news_generation.language_registry', return_value=registry), patch(
                'ghostnetwork.news_generation.approved_locales', return_value=('pl', 'en', 'zz')):
            package = build_package(self.task, self.record, 'zz')
            self.assertEqual(package['output_locale'], 'zz')
            self.assertEqual(package['news_language_contract']['output_locale'], 'zz')
            self.assertEqual(self.worker.enqueue_active(), 2)
            self.assertEqual(self.worker.enqueue_active(), 0)

    def test_queued_prompt_version_never_silently_changes_on_retry(self):
        self.worker.enqueue_active()
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghost_news_locale_jobs SET prompt_version='old-version'")
        self.assertEqual(self.worker.process_once()['result'], 'news_variant_stale')
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.store.for_records([self.record]), {})

    def test_failed_provider_retries_boundedly_without_writing_or_republishing(self):
        self.worker.enqueue_active()
        self.error = NarrativeProviderError('ollama_timeout',retryable=True)
        for expected in ('news_variant_ready','news_variant_ready','news_variant_rejected'):
            result = self.worker.process_once()
            self.assertEqual(result['result'],expected,result)
            with db_connect(self.path) as conn:
                conn.execute('UPDATE ghost_news_locale_jobs SET next_at=0')
        self.assertEqual(self.worker.process_once()['result'],'idle')
        self.assertEqual(self.calls,3)
        self.assertEqual(self.store.for_records([self.record]),{})

    def test_new_source_during_generation_rejects_late_result(self):
        def change():
            with db_connect(self.path) as conn:
                conn.execute('UPDATE ghost_narrative_medium_records SET source_state_version=99')
        self.hook = change
        self.worker.enqueue_active()
        result = self.worker.process_once()
        self.assertEqual(result['result'],'news_variant_stale',result)
        self.assertEqual(self.store.for_records([self.read()]),{})

    def test_second_worker_cannot_claim_live_lease(self):
        self.worker.enqueue_active()
        self.hook = lambda: self.assertEqual(NewsLocaleWorker(self.repo,self.router).process_once()['result'],'idle')
        self.assertEqual(self.worker.process_once()['result'],'news_variant_completed')
        self.assertEqual(self.calls,1)

    def test_expired_record_is_not_queued_or_generated(self):
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghost_narrative_medium_records SET valid_until='2000-01-01T00:00:00+00:00'")
        self.assertEqual(self.worker.enqueue_active(), 0)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghost_narrative_medium_records SET valid_until=''")
        self.assertEqual(self.worker.enqueue_active(), 1)
        with db_connect(self.path) as conn:
            conn.execute("UPDATE ghost_narrative_medium_records SET valid_until='2000-01-01T00:00:00+00:00'")
        self.assertEqual(self.worker.process_once()['result'], 'news_variant_stale')
        self.assertEqual(self.calls, 0)

    def test_polish_and_new_numbers_rejected(self):
        package = build_package(self.task,self.record)
        for body, error in [('To jest sygnał, który się pojawił.', 'news_variant_language_uncertain'),
                            ('The network has 987654 signals.', 'news_variant_number_added')]:
            result = validate_variant(self.content(body=body),package,self.record)
            self.assertNotEqual(result['status'],'accepted')
            self.assertIn(error,result['errors'])

    def test_product_and_blacknet_records_never_translated(self):
        for changes in ({'content_kind':'product_promo'},{'target_medium':'blacknet'}):
            with self.assertRaisesRegex(ValueError,'news_generation_source_excluded'):
                build_package(self.task,{**self.record,**changes})

