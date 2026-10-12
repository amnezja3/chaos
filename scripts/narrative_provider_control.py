"""Migration, bounded metadata report and emergency local-provider rollback."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))


def main():
    from database import DB_PATH
    from ghostnetwork.llm.provider_store import ProviderStore
    from ghostnetwork.llm.mistral_provider import secret_configured, ENDPOINT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['migrate','status','use-ollama'])
    parser.add_argument('--db',default=DB_PATH)
    args=parser.parse_args()
    if args.command=='migrate':
        from ghostnetwork.repository import GhostNetworkRepository
        GhostNetworkRepository(db_path=args.db)
    store=ProviderStore(args.db)
    if args.command=='use-ollama':
        store.save({**store.config(),'primary':'ollama'},'operator-cli')
    from ghostnetwork.ollama_worker import active_ollama_worker_policies
    calls=store.recent()
    durations=sorted(c['duration_ms'] for c in calls if c['status']=='completed')
    report={'ok':True,'config':store.config(),'secret_configured':secret_configured(),'endpoint':ENDPOINT,
            'sample_size':len(calls),'p50_ms':durations[len(durations)//2] if durations else None,
            'p95_ms':durations[min(len(durations)-1,int(len(durations)*.95))] if durations else None,
            'recent_calls':calls,
            'active_policies':[{'source':p.source_scope,'variant':p.task_variant,'medium':p.target_medium,
                                'prompt':p.prompt_version,'schema':p.output_schema_version} for p in active_ollama_worker_policies()]}
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
