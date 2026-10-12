import json
import multiprocessing
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from ghostnetwork.llm import executor
from ghostnetwork.llm.mistral_provider import MistralNarrativeProvider
from ghostnetwork.llm.provider import NarrativeGenerationResult, NarrativeProviderError
from ghostnetwork.llm.provider_store import DEFAULTS, ProviderStore, ProviderRevisionConflict, ProviderConfigError
from ghostnetwork.llm.router import NarrativeRouter
import test_ollama_worker as worker_tests


class Response:
    def __init__(self, data=None, status=200, headers=None):
        self.status_code=status
        self.headers=headers or {}
        self.data=json.dumps(data or {}).encode()
        self.closed=False
    def iter_content(self, size):
        yield self.data
    def close(self):
        self.closed=True


class Session:
    def __init__(self, response):
        self.response=response
        self.calls=[]
    def request(self,*args,**kwargs):
        self.calls.append((args,kwargs))
        return self.response


def slow_child(pipe, *args):
    time.sleep(30)


def successful_child(pipe, *args):
    pipe.send((True, {'ok':True}))
    pipe.close()


class MistralAdapterTest(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'CHAOS_MISTRAL_API_KEY':'secret-test-only'})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.config={**DEFAULTS,'model':'configured-model'}

    def response(self, content='{}', reason='stop'):
        return {'model':'resolved-model','id':'req-1','choices':[{'finish_reason':reason,'message':{'content':content}}],
                'usage':{'prompt_tokens':10,'completion_tokens':4}}

    def test_exact_canonical_messages_and_metadata(self):
        response=Response(self.response())
        session=Session(response)
        result=MistralNarrativeProvider(self.config,session).generate({'messages':[{'role':'user','content':'JSON please'}]},None)
        sent=session.calls[0][1]
        self.assertFalse(sent['allow_redirects'])
        self.assertFalse(sent['json']['stream'])
        self.assertEqual(sent['json']['model'],'configured-model')
        self.assertNotIn('tools',sent['json'])
        self.assertEqual(result.model,'resolved-model')
        self.assertEqual(result.model_digest,'')
        self.assertEqual(result.eval_count,4)
        self.assertTrue(response.closed)
        self.assertNotIn('secret-test-only',repr(result))

    def test_text_chunks_and_invalid_outputs(self):
        adapter=lambda body:MistralNarrativeProvider(self.config,Session(Response(body)))
        self.assertEqual(adapter(self.response([{'type':'text','text':'{}'}])).generate({'messages':[]},None).content,'{}')
        for body in [self.response('', 'stop'),self.response('{}','length'),self.response([{'type':'image','url':'x'}]),{'choices':[]}]:
            with self.subTest(body=body),self.assertRaises(NarrativeProviderError):
                adapter(body).generate({'messages':[]},None)

    def test_diagnostic_package_transmits_canonical_output_schema(self):
        from ghostnetwork.ollama_policy import assign_ollama_task_policy, build_ollama_task_package
        task = assign_ollama_task_policy({
            'source_scope':'blacknet_world', 'task_variant':'world_digest',
            'target_medium':'blacknet', 'audience_scope':'public',
            'truth_class_policy':'canonical_facts_only',
            'facts':[{'fact_id':'diagnostic', 'fact_type':'runtime_probe',
                      'value':'Transport diagnostyczny jest gotowy.'}],
            'allowed_actions':[],
        })
        package = build_ollama_task_package(task)
        original = json.dumps({'messages':package['messages'], 'format':package['format']}, sort_keys=True)
        session = Session(Response(self.response()))
        MistralNarrativeProvider(self.config,session).generate(package,package['policy'])
        payload = session.calls[0][1]['json']
        self.assertEqual(payload['messages'],package['messages'])
        self.assertEqual(payload['response_format']['type'],'json_schema')
        contract = payload['response_format']['json_schema']
        self.assertIs(contract['strict'],True)
        self.assertEqual(contract['schema'],package['format'])
        self.assertTrue({'title','body','fact_refs','tone'}.issubset(contract['schema']['properties']))
        self.assertEqual(original,json.dumps({'messages':package['messages'], 'format':package['format']}, sort_keys=True))

    def test_http_failures_are_redacted_and_not_retried(self):
        for code in (301,400,401,402,403,404,408,409,422,429,500,503):
            session=Session(Response({'error':'secret-test-only'},code,{'Retry-After':'120'}))
            with self.subTest(code=code),self.assertRaises(NarrativeProviderError) as caught:
                MistralNarrativeProvider(self.config,session).generate({'messages':[]},None)
            self.assertEqual(caught.exception.http_status,code)
            self.assertEqual(caught.exception.retry_after,120)
            self.assertNotIn('secret-test-only',str(caught.exception))
            self.assertEqual(len(session.calls),1)

    def test_model_list_filters_nonchat_and_deduplicates(self):
        session=Session(Response({'data':[{'id':'chat','capabilities':{'completion_chat':True}},
                                        {'id':'embedding','capabilities':{'completion_chat':False}}]}))
        self.assertEqual(MistralNarrativeProvider(self.config,session).list_models(),['chat'])

    def test_billing_quota_is_distinct_from_truncated_completion(self):
        session=Session(Response({'error':{'code':'insufficient_quota','message':'secret'}},429))
        with self.assertRaises(NarrativeProviderError) as caught:
            MistralNarrativeProvider(self.config,session).generate({'messages':[]},None)
        self.assertEqual(caught.exception.code,'mistral_quota_exhausted')

    def test_hard_deadline_kills_child_and_leaves_no_background_call(self):
        before={p.pid for p in multiprocessing.active_children()}
        started=time.monotonic()
        with patch.object(executor,'_child',slow_child),self.assertRaises(NarrativeProviderError) as caught:
            executor.execute('mistral',self.config,'generate',seconds=.4)
        self.assertEqual(caught.exception.code,'provider_deadline')
        self.assertLess(time.monotonic()-started,3)
        self.assertEqual({p.pid for p in multiprocessing.active_children()},before)

    def test_cancelled_does_not_start_child(self):
        with patch.object(executor.multiprocessing,'get_context') as context,self.assertRaises(NarrativeProviderError):
            executor.execute('mistral',self.config,'generate',seconds=10,guard=lambda:False)
        context.assert_not_called()

    def test_spawned_result_is_received_and_child_reaped(self):
        before={p.pid for p in multiprocessing.active_children()}
        with patch.object(executor,'_child',successful_child):
            self.assertEqual(executor.execute('mistral',self.config,'verify',seconds=10),{'ok':True})
        self.assertEqual({p.pid for p in multiprocessing.active_children()},before)


class RouterTest(unittest.TestCase):
    setUp=worker_tests.OllamaWorkerTest.setUp
    tearDown=worker_tests.OllamaWorkerTest.tearDown
    task=worker_tests.OllamaWorkerTest.task
    worker=worker_tests.OllamaWorkerTest.worker
    accepted=worker_tests.OllamaWorkerTest.accepted

    def setup_router(self, error=None, content=None):
        self.calls=[]
        self.error=error
        self.content=content
        def execute(provider,config,operation,package=None,policy=None,**kwargs):
            if operation=='verify':return {'ok':True,'errors':[]}
            self.calls.append((provider,package))
            if provider=='mistral' and self.error:raise self.error
            return NarrativeGenerationResult(provider=provider,model=config['model'] if provider=='mistral' else 'llama3.1:8b',
                requested_model=config['model'] if provider=='mistral' else 'llama3.1:8b', content=self.content if provider=='mistral' and self.content is not None else self.accepted(),
                done=True,done_reason='stop',raw_response_hash='hash')
        router=NarrativeRouter(self.db_path,executor=execute)
        router.store.save({**router.config,'primary':'mistral','model':'chosen'},'admin')
        router.refresh()
        return router

    def test_real_worker_path_uses_mistral_and_records_single_candidate(self):
        router=self.setup_router()
        task=self.repo.enqueue_narrative_task(self.task())
        result=self.worker(router).process_once()
        self.assertEqual(result['result'],'completed',result)
        self.assertEqual([c[0] for c in self.calls],['mistral'])
        self.assertEqual(self.repo.get_narrative_candidate_for_task(task['outbox_id'])['provider'],'mistral')
        self.assertEqual(len(router.store.recent()),1)

        candidate=self.repo.get_narrative_candidate_for_task(task['outbox_id'])
        self.repo.ensure_narrative_publication(candidate['candidate_id'])
        claim=self.repo.claim_next_narrative_publication('publisher-test',lease_seconds=60)
        published=self.repo.publish_claimed_narrative_candidate(claim['publication_receipt_id'],'publisher-test',claim['lease_until'])
        self.assertEqual(published['receipt']['status'],'published')
        replay=self.repo.publish_claimed_narrative_candidate(claim['publication_receipt_id'],'publisher-test',claim['lease_until'])
        self.assertTrue(replay['duplicate'])
        self.assertEqual(len(self.repo.list_narrative_medium_records('blacknet',limit=10)),1)

    def test_http_fallback_keeps_same_task_and_package(self):
        for code in (400,401,402,403,404,408,409,422,429,500):
            with self.subTest(code=code):
                router=self.setup_router(NarrativeProviderError('http_'+str(code),provider='mistral',http_status=code,retryable=True))
                task=self.repo.enqueue_narrative_task(self.task(event_id='error-'+str(code)))
                result=self.worker(router).process_once()
                self.assertEqual(result['result'],'completed',result)
                self.assertEqual([c[0] for c in self.calls],['mistral','ollama'])
                self.assertIs(self.calls[0][1],self.calls[1][1])
                candidate=self.repo.get_narrative_candidate_for_task(task['outbox_id'])
                self.assertEqual(candidate['provider'],'ollama')
                records=[c for c in router.store.recent() if c['task_id']==task['outbox_id']]
                self.assertEqual(len(records),2)
                self.assertEqual(len({c['attempt_id'] for c in records}),1)

    def test_invalid_json_falls_back_but_fact_rejection_does_not(self):
        router=self.setup_router(content='broken JSON')
        self.repo.enqueue_narrative_task(self.task())
        self.worker(router).process_once()
        self.assertEqual([c[0] for c in self.calls],['mistral','ollama'])
        router=self.setup_router(content=self.accepted().replace('f01','evil-ref'))
        self.repo.enqueue_narrative_task(self.task(event_id='domain-rejection'))
        self.worker(router).process_once()
        self.assertEqual([c[0] for c in self.calls],['mistral'])

    def test_shared_circuit_and_expiry_probe(self):
        router=self.setup_router(NarrativeProviderError('mistral_http_409',provider='mistral',http_status=409))
        self.repo.enqueue_narrative_task(self.task())
        self.worker(router).process_once()
        self.calls.clear()
        second=NarrativeRouter(self.db_path,executor=router.executor)
        self.repo.enqueue_narrative_task(self.task(event_id='second'))
        self.worker(second).process_once()
        self.assertEqual([c[0] for c in self.calls],['ollama'])
        self.error=None
        second.probe()
        self.calls.clear()
        self.repo.enqueue_narrative_task(self.task(event_id='recovered'))
        self.worker(second).process_once()
        self.assertEqual([c[0] for c in self.calls],['mistral'])

    def test_concurrency_and_budget_are_shared(self):
        router=self.setup_router()
        with router.store.slot('generation:ollama',5) as one:
            with ProviderStore(self.db_path).slot('generation:ollama',5) as two:
                self.assertTrue(one)
                self.assertFalse(two)
        self.assertTrue(router.store.reserve_tokens(8,10))
        self.assertFalse(ProviderStore(self.db_path).reserve_tokens(8,10))

    def test_revision_conflict_and_secret_rejected(self):
        store=ProviderStore(self.db_path)
        old=store.config()
        store.save(old,'admin')
        with self.assertRaises(ProviderRevisionConflict):store.save(old,'admin')
        with self.assertRaises(ProviderConfigError):store.save({**store.config(),'api_key':'no'},'admin')

    def test_loss_of_lease_prevents_fallback(self):
        router=self.setup_router()
        from ghostnetwork.ollama_policy import build_ollama_task_package
        package=build_ollama_task_package(self.task())
        valid=[True]
        def failing(*args,**kwargs):
            valid[0]=False
            raise NarrativeProviderError('provider_deadline',provider='mistral',retryable=True)
        router.executor=failing
        with self.assertRaises(NarrativeProviderError):
            router.generate(package,package['policy'],guard=lambda:valid[0])
        self.assertEqual(len(router.store.recent()),1)

    def test_both_providers_down_do_not_claim_queue(self):
        router=self.setup_router()
        router.executor=lambda *a,**k: {'ok':False,'errors':['offline']}
        task=self.repo.enqueue_narrative_task(self.task())
        result=self.worker(router).process_once()
        self.assertEqual(result['result'],'preflight_failed')
        self.assertEqual(self.repo.get_narrative_outbox(task['outbox_id'])['attempt_count'],0)

    def test_health_degraded_and_configuration_snapshot(self):
        router=self.setup_router()
        router.executor=lambda provider,*a,**k: {'ok':provider=='mistral','errors':[] if provider=='mistral' else ['offline']}
        self.assertTrue(router.verify()['ok'])
        self.assertTrue(router.verify()['degraded'])
        original=router.config.copy()
        router.store.save({**original,'primary':'ollama'},'admin')
        self.assertEqual(router.config,original)
        self.assertTrue(router.refresh())
        self.assertEqual(router.provider,'ollama')

    def test_worker_survives_double_transport_failure(self):
        router=self.setup_router()
        normal=router.executor
        def failing(provider,config,operation,*a,**k):
            if operation=='verify':return {'ok':True,'errors':[]}
            raise NarrativeProviderError('unreachable',provider=provider,retryable=True)
        router.executor=failing
        task=self.repo.enqueue_narrative_task(self.task())
        worker=self.worker(router)
        result=worker.process_once()
        self.assertNotEqual(result['result'],'completed')
        self.assertNotEqual(self.repo.get_narrative_outbox(task['outbox_id'])['status'],'completed')
        router.executor=normal
        self.repo.enqueue_narrative_task(self.task(event_id='next-task'))
        self.assertEqual(worker.process_once()['result'],'completed')

    def test_expired_circuit_allows_recovery_on_next_task(self):
        router=self.setup_router()
        from database import db_connect
        with db_connect(self.db_path) as conn:
            conn.execute('INSERT INTO narrative_provider_state(key,until_at,code) VALUES (?,?,?)',
                         (router.circuit_key,time.time()-1,'old_failure'))
        self.repo.enqueue_narrative_task(self.task())
        self.assertEqual(self.worker(router).process_once()['result'],'completed')
        self.assertEqual([c[0] for c in self.calls],['mistral'])
        self.assertEqual(router.store.circuit(router.circuit_key)['until_at'],0)

    def test_local_budget_routes_without_external_generation(self):
        router=self.setup_router()
        router.store.save({**router.config,'daily_token_budget':1},'admin')
        self.repo.enqueue_narrative_task(self.task())
        self.assertEqual(self.worker(router).process_once()['result'],'completed')
        self.assertEqual([c[0] for c in self.calls],['ollama'])

    def test_worker_checks_lease_before_fallback_without_waiting_for_heartbeat(self):
        router=self.setup_router()
        from database import db_connect
        task=self.repo.enqueue_narrative_task(self.task())
        normal=router.executor
        def lose_lease(provider,config,operation,*a,**k):
            if operation=='verify':return {'ok':True,'errors':[]}
            self.calls.append((provider,None))
            with db_connect(self.db_path) as conn:
                conn.execute("UPDATE ghost_narrative_outbox SET claimed_by='other' WHERE outbox_id=?",(task['outbox_id'],))
            raise NarrativeProviderError('mistral_http_409',provider='mistral',http_status=409,retryable=True)
        router.executor=lose_lease
        self.worker(router).process_once()
        self.assertEqual([c[0] for c in self.calls],['mistral'])
        self.assertIsNone(self.repo.get_narrative_candidate_for_task(task['outbox_id']))

    def test_migration_report_and_rollback_cli(self):
        import contextlib
        import io
        import sys
        from scripts.narrative_provider_control import main
        router=self.setup_router()
        for command in ('migrate','status','use-ollama'):
            output=io.StringIO()
            with patch.object(sys,'argv',['control',command,'--db',self.db_path]),contextlib.redirect_stdout(output):
                main()
            report=json.loads(output.getvalue())
            self.assertTrue(report['ok'])
            self.assertTrue(report['active_policies'])
        self.assertEqual(ProviderStore(self.db_path).config()['primary'],'ollama')
