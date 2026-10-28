"""Read-only Paris snapshot/scan-key inspection; no HTTP or freshness changes."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.maplark_region import select, PROFILE
from poi_infrastructure.maplark_profile import PROFILE as EXACT_PROFILE
from poi_infrastructure.world_adapters import plan_maplark
from poi_infrastructure.world_contract import ProviderBatch, batch_key, ContractError
from poi_infrastructure.world_storage import decode_object


def inspect(db, snapshot, scans):
    uri=Path(db).resolve().as_uri()+'?mode=ro'
    with closing(sqlite3.connect(uri,uri=True)) as conn:
        conn.row_factory=sqlite3.Row
        row=conn.execute('SELECT * FROM world_snapshot WHERE id=?',(snapshot,)).fetchone()
        if row is None:
            return dict(status='snapshot_missing',network_calls=0,production_writes=0)
        if len(row['payload'])>8*1024*1024:raise ValueError('snapshot_too_large')
        raw=json.loads(row['payload'])
        config=conn.execute("SELECT config FROM poi_provider_config WHERE id='maplark'").fetchone()
        current=json.loads(config[0]) if config else {}
        result=dict(status='offline_diagnostic',network_calls=0,production_writes=0,
            live_acceptance=False,selection_profile=PROFILE,
            digest_ok=hashlib.sha256(row['payload']).hexdigest()==row['digest'],
            stored_revision=raw['revision'],current_revision=current.get('revision'),
            storage_reference_matches=raw.get('storage_reference')==current.get('evidence',{}).get('reference'),
            fetched=row['fetched'],fresh_until=min(row['fresh_until'],row['fetched']+300),
            context=raw.get('observation_context'),scans=[],positions=[])
        for prefix in scans:
            if len(prefix)!=12 or any(c not in '0123456789abcdef' for c in prefix):
                raise ValueError('scan_key_requires_12_hex')
            found=conn.execute('SELECT query_key,fetched FROM world_snapshot WHERE query_key LIKE ? LIMIT 2',
                               (prefix+'%',)).fetchall()
            # Several snapshots may have the same key; report without assuming uniqueness.
            for scan in found:
                result['scans'].append(dict(key=scan['query_key'][:12],at=scan['fetched'],
                    in_fresh_window=row['fetched']<=scan['fetched']<result['fresh_until']))
        started=time.monotonic()
        batch=ProviderBatch(tuple(decode_object(o) for o in raw['objects']),raw['profile'],
                            raw['completeness'],tuple(raw['reasons']),raw['selection'],raw['order'])
        result['decode_seconds']=round(time.monotonic()-started,4)
        for lon in (2.338,2.3378):
            plan=plan_maplark(48.861,lon,300,limit=1000)
            key=batch_key('maplark',EXACT_PROFILE,plan.profile,EXACT_PROFILE,
                          {'params':plan.params,'revision':raw['revision']})
            point=dict(lat=48.861,lon=lon,radius=300,expected_key=key[:12],
                       matches_supplied_scan=key[:12] in scans)
            started=time.monotonic()
            try:
                data=select(batch,raw['observation_context']['demand_bounds'],48.861,lon,300)
                point['objects']=len(data['elements'])
            except ContractError as exc:point['rejection']=str(exc)
            point['selection_seconds']=round(time.monotonic()-started,4)
            result['positions'].append(point)
        result['note']='Offline geometry timing only; not full reader timing or proof of historical worker state.'
        return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--snapshot',required=True)
    parser.add_argument('--scan-key',action='append',default=[])
    args=parser.parse_args()
    print(json.dumps(inspect(args.db,args.snapshot,args.scan_key)))
