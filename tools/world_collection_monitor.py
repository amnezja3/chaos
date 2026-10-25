"""Independent read-only collection/budget monitoring, never a provider probe."""
import argparse
import json
from pathlib import Path
import signal
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.regular_discovery import report


class ReadOnlyRepository(Repository):
    def connect(self):
        import sqlite3
        connection=sqlite3.connect(Path(self.path).resolve().as_uri()+'?mode=ro',uri=True,timeout=2)
        connection.row_factory=sqlite3.Row
        return connection


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--serve',action='store_true')
    parser.add_argument('--since',type=float)
    args=parser.parse_args()
    stop=threading.Event()
    for name in ('SIGINT','SIGTERM'):signal.signal(getattr(signal,name),lambda *_:stop.set())
    deadline=time.monotonic()+100
    while not stop.is_set():
        try:
            result=report(ReadOnlyRepository(args.db))
            if args.since is not None and result['last'].get('at',0)<args.since:
                if time.monotonic()>=deadline:
                    print(json.dumps(dict(status='fresh_cycle_missing',network_calls=0)));return 1
                stop.wait(2);continue
            print(json.dumps(result),flush=True)
        except Exception as exc:
            print(json.dumps(dict(status='monitor_error',error_type=type(exc).__name__,network_calls=0)),flush=True)
            if not args.serve:return 1
        if not args.serve:return 0
        stop.wait(300)
    return 0


if __name__=='__main__':raise SystemExit(main())
