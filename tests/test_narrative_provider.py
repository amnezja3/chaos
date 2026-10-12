"""Compatibility boundary tests, without a running model or external API."""
import unittest
from dataclasses import asdict
from unittest.mock import patch

import requests

from ghostnetwork.llm.provider import (
    NarrativeGenerationResult, NarrativeProvider, NarrativeProviderError,
    create_narrative_provider,
)
from ghostnetwork.ollama_client import ChaosOllamaClient, OllamaClientError
from ghostnetwork.ollama_worker import OllamaNarrativeWorker
import test_ollama_client as client_tests
import test_ollama_worker as worker_tests


class NarrativeProviderTest(unittest.TestCase):
    def test_adapter_preserves_exact_request_and_legacy_result_fields(self):
        payload = {'model': 'llama3.1:8b', 'message': {'content': '{"title":"sample"}'},
                   'done': True, 'done_reason': 'stop', 'eval_count': 12}
        direct_session = client_tests.FakeSession([client_tests.FakeResponse(payload)])
        adapter_session = client_tests.FakeSession([client_tests.FakeResponse(payload)])
        package, policy = client_tests.OllamaClientTest().package()
        direct = ChaosOllamaClient(session=direct_session).generate(package, policy)
        provider = create_narrative_provider(session=adapter_session)
        self.assertIsInstance(provider, NarrativeProvider)
        result = provider.generate(package, policy)
        self.assertEqual(direct_session.calls, adapter_session.calls)
        self.assertEqual({key: result.as_dict()[key] for key in direct.as_dict()}, direct.as_dict())
        self.assertEqual(result.provider, 'ollama')
        self.assertEqual(result.requested_model, 'llama3.1:8b')

    def test_local_error_keeps_legacy_and_common_catch_contract(self):
        provider = create_narrative_provider(session=client_tests.FakeSession(error=requests.Timeout('slow')))
        package, policy = client_tests.OllamaClientTest().package()
        with self.assertRaises(NarrativeProviderError) as caught:
            provider.generate(package, policy)
        error = caught.exception
        self.assertIsInstance(error, OllamaClientError)
        self.assertEqual(error.provider, 'ollama')
        self.assertEqual(error.code, 'ollama_timeout')
        self.assertTrue(error.retryable)

    def test_external_result_does_not_claim_local_digest_or_runtime(self):
        result = NarrativeGenerationResult(provider='test', model='remote-model',
            content='{}', done=True, done_reason='stop', raw_response_hash='hash')
        self.assertEqual(result.as_dict()['model_digest'], '')
        self.assertEqual(result.as_dict()['runtime_version'], '')
        self.assertIsNone(result.prompt_eval_count)

    def test_unknown_provider_is_not_silently_routed_to_ollama(self):
        with self.assertRaises(NarrativeProviderError) as caught:
            create_narrative_provider('unconfigured')
        self.assertEqual(caught.exception.code, 'provider_not_supported')

    def test_narrative_policy_does_not_select_transport_model(self):
        package, policy = client_tests.OllamaClientTest().package()
        self.assertNotIn('model_name', asdict(policy))
        self.assertNotIn('model_digest', asdict(policy))
        session = client_tests.FakeSession([client_tests.FakeResponse({
            'model': 'llama3.1:8b', 'message': {'content': '{}'},
            'done': True, 'done_reason': 'stop'})])
        result = create_narrative_provider(session=session).generate(package, object())
        self.assertEqual(result.model, 'llama3.1:8b')

    def test_default_worker_uses_provider_factory(self):
        sentinel = object()
        with patch('ghostnetwork.ollama_worker.create_narrative_provider', return_value=sentinel) as factory:
            repository = type('Repository', (), {'db_path': 'unused'})()
            worker = OllamaNarrativeWorker(repository=repository)
        factory.assert_called_once_with(db_path='unused')
        self.assertIs(worker.client, sentinel)


class NarrativeProviderWorkerTest(unittest.TestCase):
    setUp = worker_tests.OllamaWorkerTest.setUp
    tearDown = worker_tests.OllamaWorkerTest.tearDown
    task = worker_tests.OllamaWorkerTest.task
    worker = worker_tests.OllamaWorkerTest.worker
    accepted = worker_tests.OllamaWorkerTest.accepted

    def test_provider_identity_survives_repository_reopen(self):
        task = self.repo.enqueue_narrative_task(self.task())
        result = NarrativeGenerationResult(
            provider='test_remote', model='resolved-model', requested_model='selected-model',
            request_id='request-123', content=self.accepted(), done=True,
            done_reason='stop', raw_response_hash='response-hash')
        client = worker_tests.FakeClient()
        client.model_identity = {'provider': 'test_remote', 'model': 'selected-model'}
        client.generate = lambda package, policy: result
        outcome = self.worker(client).process_once()
        self.assertEqual(outcome['result'], 'completed', outcome)
        reopened = worker_tests.GhostNetworkRepository(db_path=self.db_path, clock=self.clock)
        attempt = reopened.list_narrative_attempts(task_id=task['outbox_id'])[0]
        candidate = reopened.get_narrative_candidate_for_task(task['outbox_id'])
        for record in (attempt, candidate):
            self.assertEqual(record['provider'], 'test_remote')
            self.assertEqual(record['model_name'], 'resolved-model')
            self.assertEqual(record['requested_model'], 'selected-model')
            self.assertEqual(record['provider_request_id'], 'request-123')
            self.assertEqual(record['model_digest'], '')
            self.assertEqual(record['ollama_runtime_version'], '')

    def test_legacy_schema_migrates_without_losing_candidate(self):
        task = self.repo.enqueue_narrative_task(self.task())
        self.assertEqual(self.worker(worker_tests.FakeClient([self.accepted()])).process_once()['result'], 'completed')
        before = self.repo.get_narrative_candidate_for_task(task['outbox_id'])
        with worker_tests.db_connect(self.db_path) as conn:
            for table in ('ghost_narrative_inbox_attempts', 'ghost_narrative_inbox_candidates'):
                for column in ('provider', 'requested_model', 'provider_request_id'):
                    conn.execute(f'ALTER TABLE {table} DROP COLUMN {column}')
        reopened = worker_tests.GhostNetworkRepository(db_path=self.db_path, clock=self.clock)
        after = reopened.get_narrative_candidate_for_task(task['outbox_id'])
        self.assertEqual(after['candidate_id'], before['candidate_id'])
        self.assertEqual(after['body'], before['body'])
        self.assertEqual(after['provider'], 'ollama')
        self.assertEqual(after['requested_model'], before['model_name'])
        attempt = reopened.list_narrative_attempts(task_id=task['outbox_id'])[0]
        self.assertEqual(attempt['provider'], 'ollama')

    def test_failed_provider_attempt_keeps_selected_identity(self):
        task = self.repo.enqueue_narrative_task(self.task())
        client = worker_tests.FakeClient(error=NarrativeProviderError(
            'unavailable', provider='test_remote', retryable=True))
        client.model_identity = {'provider': 'test_remote', 'model': 'selected-model'}
        self.worker(client).process_once()
        attempt = self.repo.list_narrative_attempts(task_id=task['outbox_id'])[0]
        self.assertEqual(attempt['provider'], 'test_remote')
        self.assertEqual(attempt['requested_model'], 'selected-model')
        self.assertEqual(attempt['model_digest'], '')

    def test_common_transport_error_preserves_queue_retry(self):
        task = self.repo.enqueue_narrative_task(self.task())
        client = worker_tests.FakeClient(error=NarrativeProviderError(
            'test_unavailable', provider='test', retryable=True, http_status=503))
        result = self.worker(client).process_once()
        self.assertEqual(result['error_code'], 'test_unavailable')
        self.assertNotEqual(result['result'], 'completed')
        self.assertEqual(client.calls, 1)
        self.assertNotEqual(self.repo.get_narrative_outbox(task['outbox_id'])['status'], 'completed')
