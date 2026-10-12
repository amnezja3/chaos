"""One task, at most one external attempt and one local attempt."""
import hashlib
import os
import time

from .executor import execute
from .provider import NarrativeProviderError
from .provider_store import ProviderStore
from ..ollama_client import OllamaClientConfig


class NarrativeRouter:
    routed = True

    def __init__(self, db_path, executor=execute):
        self.store = ProviderStore(db_path)
        self.executor = executor
        self.refresh()

    def refresh(self):
        previous = getattr(self, 'config', None)
        self.config = self.store.config()
        self.provider = self.config['primary']
        fingerprint = hashlib.sha256(os.environ.get('CHAOS_MISTRAL_API_KEY','').encode()).hexdigest()
        self.circuit_key = f"circuit:mistral:{self.config['revision']}:{fingerprint}"
        return previous != self.config

    @property
    def model_identity(self):
        if self.provider == 'mistral':
            return {'provider':'mistral','model':self.config['model'],'model_digest':''}
        config = OllamaClientConfig.from_env()
        return {'provider':'ollama','model':config.model,'model_digest':config.model_digest}

    def verify(self):
        health = {}
        for provider in (('mistral','ollama') if self.provider == 'mistral' else ('ollama',)):
            if provider == 'mistral' and self.store.circuit(self.circuit_key)['until_at'] > time.time():
                health[provider] = {'ok':False,'errors':['circuit_open']}
                continue
            try:
                health[provider] = self.executor(provider,self.config,'verify',seconds=8)
            except NarrativeProviderError as exc:
                health[provider] = {'ok':False,'errors':[exc.code]}
        ok = any(item.get('ok') for item in health.values())
        return {'ok':ok,'primary':self.provider,'providers':health,
                'degraded':not all(item.get('ok') for item in health.values()),
                'errors':[] if ok else ['all_providers_unavailable']}

    def models(self):
        return self.executor('mistral',self.config,'list_models',seconds=8)

    def probe(self):
        with self.store.slot('generation:mistral',10) as acquired:
            if not acquired:
                raise NarrativeProviderError('provider_busy',provider='mistral',retryable=True)
            try:
                result = self.executor('mistral',self.config,'verify',seconds=8)
                if not result.get('ok'):
                    raise NarrativeProviderError('mistral_model_unavailable',provider='mistral')
                self.store.circuit_result(self.circuit_key)
                return result
            except NarrativeProviderError as exc:
                self.store.circuit_result(self.circuit_key,exc)
                raise

    def generate(self, package, policy, *, guard=lambda: True, task_id='', attempt_id=''):
        end = time.monotonic() + self.config['total_seconds']
        providers = ['mistral','ollama'] if self.provider == 'mistral' else ['ollama']
        for provider in providers:
            if not guard():
                raise NarrativeProviderError('generation_cancelled',provider=provider,retryable=True)
            seconds = min(self.config['remote_seconds'] if provider == 'mistral' else 242, end-time.monotonic())
            if seconds <= 0:
                raise NarrativeProviderError('provider_deadline',provider=provider,retryable=True)
            call_id = self.store.start_call(self.config,provider,task_id,attempt_id,package)
            started = time.monotonic()
            try:
                with self.store.slot('generation:'+provider,self.config['total_seconds']+30) as acquired:
                    if not acquired:
                        raise NarrativeProviderError('provider_busy',provider=provider,retryable=True)
                    if not guard():
                        raise NarrativeProviderError('generation_cancelled',provider=provider,retryable=True)
                    if provider == 'mistral':
                        if self.store.circuit(self.circuit_key)['until_at'] > time.time():
                            raise NarrativeProviderError('circuit_open',provider=provider,retryable=True)
                        reserve = self.config['max_tokens'] + 128 + sum(len(str(m.get('content','')).encode()) for m in package['messages'])
                        if not self.store.reserve_tokens(reserve,self.config['daily_token_budget']):
                            raise NarrativeProviderError('mistral_local_budget',provider=provider,retryable=True)
                    result = self.executor(provider,self.config,'generate',package,policy,seconds=min(seconds,end-time.monotonic()),guard=guard)
                    if provider == 'mistral':
                        from ..ollama_policy import parse_and_validate_ollama_content
                        validation = parse_and_validate_ollama_content(result.content,package)
                        structural = {'output_not_object','schema_fields_mismatch','invalid_title','invalid_body','invalid_tone','invalid_fact_refs','invalid_cta_ref'}
                        if validation['status'] == 'invalid_json' or (validation.get('errors') and set(validation['errors']) <= structural):
                            raise NarrativeProviderError('mistral_invalid_json',provider=provider,retryable=True)
                        # Domain/fact/safety rejection goes to the normal worker.
                        self.store.circuit_result(self.circuit_key)
                    self.store.finish_call(call_id,time.monotonic()-started,result=result)
                    return result
            except NarrativeProviderError as exc:
                self.store.finish_call(call_id,time.monotonic()-started,error=exc)
                if exc.code == 'generation_cancelled' or not guard():
                    raise
                if provider == 'ollama':
                    # External failures must never turn a local outage into a dead worker.
                    raise
                if exc.code not in {'circuit_open','provider_busy','mistral_local_budget'}:
                    self.store.circuit_result(self.circuit_key,exc)
        raise NarrativeProviderError('all_providers_unavailable',retryable=True)
