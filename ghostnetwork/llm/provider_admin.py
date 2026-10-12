"""Admin service; secrets are exclusively environment-owned."""
from .mistral_provider import ENDPOINT, secret_configured, token_reservation
from .provider import NarrativeProviderError
from .provider_store import DEFAULTS, ProviderConfigError, ProviderRevisionConflict
from .router import NarrativeRouter


def handle(db_path, action, data, actor):
    router = NarrativeRouter(db_path)
    try:
        if action == 'status':
            calls = router.store.recent()
            return {'success':True,'config':router.config,'secret_configured':secret_configured(),
                    'endpoint':ENDPOINT,'concurrency':1,'circuit':router.store.circuit(router.circuit_key),
                    'calls':calls,'last_provider':next((c['provider'] for c in calls if c['status']=='completed'),None)},200
        if action == 'save':
            if not isinstance(data,dict) or set(data) != set(DEFAULTS) | {'revision'}:
                raise ProviderConfigError('invalid_config_fields')
            if data.get('primary') == 'mistral':
                if not secret_configured():
                    raise ProviderConfigError('mistral_secret_missing')
                if data.get('model') not in router.models():
                    raise ProviderConfigError('mistral_model_unavailable')
            return {'success':True,'config':router.store.save(data,actor)},200
        if action == 'models':
            return {'success':True,'models':router.models()},200
        if action == 'probe':
            return {'success':True,'health':router.probe()},200
        if action == 'health':
            return {'success':True,'health':router.verify()},200
        if action == 'generate':
            # Explicit, bounded diagnostic; never queues or publishes content.
            from ..ollama_policy import assign_ollama_task_policy, build_ollama_task_package, parse_and_validate_ollama_content
            task = assign_ollama_task_policy({'source_scope':'blacknet_world','task_variant':'world_digest',
                'target_medium':'blacknet','audience_scope':'public','truth_class_policy':'canonical_facts_only',
                'facts':[{'fact_id':'diagnostic','fact_type':'runtime_probe','value':'Transport diagnostyczny jest gotowy.'}],
                'allowed_actions':[]})
            package = build_ollama_task_package(task)
            with router.store.slot('generation:mistral',10) as acquired:
                if not acquired:
                    raise NarrativeProviderError('provider_busy',provider='mistral',retryable=True)
                reserve = token_reservation(package, router.config['max_tokens'])
                if not router.store.reserve_tokens(reserve,router.config['daily_token_budget']):
                    raise NarrativeProviderError('mistral_local_budget',provider='mistral',retryable=True)
                result = router.executor('mistral',router.config,'generate',package,package['policy'],seconds=8)
            validation = parse_and_validate_ollama_content(result.content,package)
            return {'success':True,'diagnostic':{'provider':result.provider,'model':result.model,
                'request_id':result.request_id,'validation_status':validation['status'],
                'errors':validation['errors'],'published':False}},200
        return {'success':False,'error':'unknown_action'},404
    except ProviderRevisionConflict as exc:
        return {'success':False,'error':str(exc)},409
    except ProviderConfigError as exc:
        return {'success':False,'error':str(exc)},400
    except NarrativeProviderError as exc:
        return {'success':False,'error':exc.code,'provider':exc.provider,'http_status':exc.http_status},503
