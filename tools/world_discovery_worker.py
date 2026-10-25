"""Plan by default; explicit --execute --serve runs the bounded discovery process."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.discovery_runtime import cycle
from poi_infrastructure.discovery_worker import PermitExpired


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default=os.environ.get('CHAOS_POI_CACHE_PATH','data/poi_cache.sqlite3'))
    p.add_argument('--permit',default=os.environ.get('CHAOS_POI_DISCOVERY_PERMIT_PATH','data/discovery-permit.json'))
    p.add_argument('--execute',action='store_true')
    p.add_argument('--serve',action='store_true')
    p.add_argument('--interval',type=int,default=30)
    args=p.parse_args()
    if args.serve and not args.execute: p.error('--serve requires --execute')
    if not 10<=args.interval<=300: p.error('interval must be 10..300')
    stop=threading.Event()
    for name in ('SIGINT','SIGTERM'):
        signal.signal(getattr(signal,name),lambda *_:stop.set())
    while not stop.is_set():
        try:
            if args.execute and os.environ.get('CHAOS_POI_DISCOVERY_WORKER_ENABLED')!='1':
                result=dict(status='disabled',network_calls=0)
            else:
                if not Path(args.db).is_file(): raise ValueError('existing_database_required')
                result=cycle(Repository(args.db),args.permit,execute=args.execute,stopping=stop.is_set)
            print(json.dumps(dict(result,pid=os.getpid(),at=time.time())),flush=True)
        except PermitExpired:
            print(json.dumps(dict(status='permit_expired',network_calls=0,automatic_renewal=False,
                                  pid=os.getpid(),at=time.time())),flush=True)
            return 0
        except Exception as exc:
            # No raw exception messages: transport/config errors may include secrets.
            print(json.dumps(dict(status='stopped',error_type=type(exc).__name__)),flush=True)
            return 1
        if not args.serve or result['status']=='disabled': return 0
        stop.wait(args.interval)
    return 0


if __name__=='__main__': raise SystemExit(main())
