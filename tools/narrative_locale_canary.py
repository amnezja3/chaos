"""Synthetic PL/EN canary through the shared router. Never queues or publishes."""
import argparse
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def package_for(locale, medium):
    from ghostnetwork.llm.semantic_input import attach_semantic_content
    from ghostnetwork.ollama_policy import assign_ollama_task_policy, build_ollama_task_package
    from ghostnetwork.narrative_locale import freeze_language
    fact = attach_semantic_content({'fact_id':'canary:discovery','fact_type':'part_discovered'},
        {'statement':'Ujawniono wcześniej ukryty element sieci GhostNetwork.',
         'entities':[{'role':'miejsce','kind':'target','label':'Canary Station'}]})
    task=assign_ollama_task_policy(dict(source_scope='ghostnetwork',source_event_id='canary-only',
        target_medium=medium,audience_scope='public',truth_class_policy='canonical_facts_only',
        facts=[fact],allowed_actions=[],narrative_intent='ghost_part_discovery',
        task_variant='googleplex_world_dispatch' if medium=='googleplex_news' else 'part_discovered',
        validation={'event_family':'part_discovered','significance':'high'}))
    if medium=='googleplex_news' and locale!='pl':
        from ghostnetwork.news_generation import build_package
        record=dict(medium_record_id='canary-only',source_event_id='canary-only',
            target_medium=medium,content_kind='world_dispatch',fact_refs=['canary:discovery'])
        package=build_package(task,record,locale)
        package['canary_record']=record
        return package
    return build_ollama_task_package(freeze_language({**task,'output_locale':locale}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True)
    parser.add_argument('--locale',choices=('pl','en'),required=True)
    parser.add_argument('--medium',choices=('blacknet','cyberner','googleplex_news'),default='blacknet')
    parser.add_argument('--provider',choices=('configured','mistral','ollama'),default='configured')
    parser.add_argument('--generate',action='store_true')
    parser.add_argument('--show-text',action='store_true')
    args=parser.parse_args()
    if not Path(args.db).is_file():
        parser.error('Existing database required.')
    package=package_for(args.locale,args.medium)
    from ghostnetwork.llm.prompt_metrics import prompt_metrics
    from ghostnetwork.ollama_client import OllamaClientConfig
    report=dict(ok=True,published=False,locale=args.locale,medium=args.medium,
        prompt=package['policy'].prompt_version,generated=False,
        input_metrics=prompt_metrics(package),
        ollama_stream=OllamaClientConfig.from_env().stream)
    if args.generate:
        from ghostnetwork.llm.router import NarrativeRouter
        from ghostnetwork.llm.provider import NarrativeProviderError
        from ghostnetwork.ollama_policy import parse_and_validate_ollama_content
        router=NarrativeRouter(args.db)
        report['generation_budget_seconds'] = router.config['total_seconds']
        report['ollama_read_timeout_seconds'] = OllamaClientConfig.from_env().read_timeout_sec
        if args.provider!='configured':
            router.provider=args.provider  # In-memory override; leaves admin config unchanged.
        started = time.monotonic()
        try:
            result=router.generate(package,package['policy'],task_id='locale-canary')
            if package.get('canary_record'):
                from ghostnetwork.news_generation import validate_variant
                validation=validate_variant(result.content,package,package['canary_record'])
            else:
                validation=parse_and_validate_ollama_content(result.content,package)
            report.update(generated=True,provider=result.provider,model=result.model,
                validation=validation['status'],errors=validation['errors'])
            if result.provider == 'ollama':
                report['runtime_metrics'] = {
                    key: getattr(result, key, None) for key in (
                        'total_duration_ns', 'load_duration_ns',
                        'prompt_eval_count', 'eval_count',
                    )
                }
            report['ok']=validation['status']=='accepted'
            if args.provider == 'mistral' and result.provider != 'mistral':
                report.update(ok=False, error='mistral_canary_used_fallback')
            if args.show_text and validation.get('output'):
                report['sample']={k:validation['output'][k] for k in ('title','body')}
        except NarrativeProviderError as exc:
            report.update(ok=False,error=exc.code)
        finally:
            report['elapsed_seconds'] = round(time.monotonic() - started, 2)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if report['ok'] else 1


if __name__=='__main__':
    sys.exit(main())
