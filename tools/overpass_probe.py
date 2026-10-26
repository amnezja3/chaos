"""One approved probe from a spawn-safe file; default is read-only status."""
import argparse
from contextlib import closing
import json
import math
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def inspect(path, provider):
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)) as c:
        row=c.execute('SELECT config FROM poi_provider_config WHERE id=?',(provider,)).fetchone()
        if not row:raise ValueError('provider_missing')
        value=json.loads(row[0])
        group=value['operator_group']
        rate=c.execute('SELECT until_at FROM leases WHERE key=?',('@health-rate:'+group,)).fetchone()
        circuit=c.execute('SELECT until_at FROM providers WHERE name=?',(group,)).fetchone()
    wait=max(0, math.ceil(max(rate[0] if rate else 0,circuit[0] if circuit else 0)-time.time()))
    return dict(status='read_only',provider=provider,revision=value['revision'],
        technical_status=value['technical_status'],enabled=value['enabled'],
        probe_allowed=bool(value['probe_allowed'] and value['review_due_at']>time.time()),
        retry_after_seconds=wait,network_calls=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--provider',required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    state=inspect(args.db,args.provider)
    if not args.execute:
        print(json.dumps(state));return 0
    if not state['probe_allowed'] or state['retry_after_seconds']:
        print(json.dumps(dict(state,status='not_ready')));return 1
    from poi_infrastructure.service import Service,POIError
    from poi_infrastructure.providers import Registry
    from poi_infrastructure.admin import probe
    service=Service(path=args.db)
    try:
        result=probe(service,Registry(service.repo),args.provider,state['revision'],'operator:file-probe')
    except POIError as exc:
        print(json.dumps(dict(status='probe_failed',error=str(exc),retry_automatically=False)))
        return 1
    print(json.dumps(dict(status='probe_completed',provider=args.provider,
        technical_status=result['technical_status'],enabled=result['enabled'],max_network_calls=1)))
    return 0 if result['technical_status']=='tested_ok' else 1


if __name__=='__main__':
    raise SystemExit(main())
