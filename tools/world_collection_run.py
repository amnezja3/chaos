"""Explicit three-job acceptance. Stops on deferral/error; no automatic retries."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.discovery_runtime import cycle, load_permit
from tools.world_collection_prepare import IDENTITY, PROFILES


def run(db,permit_path,*,transport=None):
    permit=load_permit(permit_path)
    if (permit.budget_id!=IDENTITY or permit.acquisition!='sector-bbox-v1'
            or permit.profiles!=frozenset(PROFILES) or permit.cells!=frozenset({(2036,5153)})):
        raise ValueError('acceptance_permit_mismatch')
    calls=0
    for _ in range(3):
        result=cycle(Repository(db),permit_path,execute=True,transport=transport)
        calls+=result['network_calls']
        print(json.dumps(result),flush=True)
        if result['status']=='idle':
            print(json.dumps(dict(status='collection_idle',network_calls=calls,
                                  automatic_retries=False,environment_changed=False)))
            return 0
        if result['status']!='committed':
            return 2
    print(json.dumps(dict(status='collection_batch_complete',network_calls=calls,
                          automatic_retries=False,environment_changed=False)))
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='data/poi_cache.sqlite3')
    p.add_argument('--permit',default='data/collection-sector-2036-5153-v1/permit.json')
    args=p.parse_args()
    try:
        return run(args.db,args.permit)
    except Exception as exc:
        print(json.dumps(dict(status='stopped',error_type=type(exc).__name__)))
        return 1


if __name__=='__main__':raise SystemExit(main())
