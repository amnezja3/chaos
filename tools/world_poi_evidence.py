"""Bounded read-only POI evidence export; no API, approval, or database writes."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.world_storage import FORMAT,decode_object
from poi_infrastructure.world_contract import FILTERS,POI_PROFILE

MAX_BYTES=8*1024*1024
MAX_ROWS=100
MAX_SAMPLES=6


def inspect(path,output=None):
    path=Path(path).resolve()
    if not path.is_file() or path.name=='game.sqlite3':raise ValueError('poi_database_required')
    samples=[];groups=Counter();examined=0;used=0;issues=[];exports=[]
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as c:
        c.row_factory=sqlite3.Row
        deadline=time.monotonic()+5
        c.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
        c.execute('BEGIN')
        rows=c.execute('''SELECT id,provider,digest,length(payload) bytes FROM world_snapshot
            WHERE profile=? AND provider IN ('maplark','geoapify')
            ORDER BY fetched DESC,id LIMIT ?''',(FORMAT,MAX_ROWS+1)).fetchall()
        truncated=len(rows)>MAX_ROWS
        selected=set()
        for row in rows[:MAX_ROWS]:
            if used+row['bytes']>MAX_BYTES:
                truncated=True;break
            raw=c.execute('SELECT payload FROM world_snapshot WHERE id=?',(row['id'],)).fetchone()[0]
            used+=len(raw);examined+=1
            if hashlib.sha256(raw).hexdigest()!=row['digest']:
                issues.append(dict(snapshot=row['id'],reason='digest_mismatch'));continue
            payload=json.loads(raw)
            if payload.get('profile') not in ('poi',POI_PROFILE):continue
            context=payload.get('observation_context') or {}
            selection=payload.get('selection')
            acquisition=context.get('acquisition','exact_or_unspecified')
            group=(row['provider'],selection,acquisition)
            groups[' / '.join(map(str,group))]+=1
            if group in selected or len(samples)>=MAX_SAMPLES:continue
            types=Counter();matches=Counter();features=[]
            for value in payload['objects']:
                obj=decode_object(value)
                types[obj.geometry.kind if obj.geometry else 'missing']+=1
                tags=dict(obj.tags)
                for category in FILTERS:
                    key,sep,expected=category.partition('=')
                    if (tags.get(key)==expected if sep else key in tags):matches[category]+=1
                # Export geography and classifier tags only, no profile/user data,
                # business contact tags, raw provider response, headers or secrets.
                features.append(dict(identity=obj.identity,geometry=obj.geometry.geojson() if obj.geometry else None,
                    marker=obj.marker,marker_method=obj.marker_method,
                    tags={k:tags[k] for k in ('shop','amenity','office','healthcare','atm','man_made') if k in tags}))
            item=dict(snapshot=row['id'],provider=row['provider'],source_digest=row['digest'],
                selection=selection,acquisition=acquisition,revision=payload.get('revision'),
                completeness=payload.get('completeness'),reasons=payload.get('reasons',[]),
                objects=len(features),geometry_types=dict(types),filter_matches=dict(matches),
                unobserved_filters=[f for f in FILTERS if not matches[f]],
                request_params={k:v for k,v in (context.get('request_params') or {}).items()
                    if k in ('bbox','location','radius','tags','limit','clipGeometry','categories')},regional_scan_approved=False)
            exports.append(dict(metadata=item,objects=features))
            samples.append(item);selected.add(group)
        scopes=[]
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if {'world_credit_scope','world_credit_operation','world_credit_allocation'}<=tables:
            from poi_infrastructure.credit_budget import CreditBudget
            for row in c.execute('SELECT * FROM world_credit_scope WHERE ends>? ORDER BY account,scope LIMIT 101',(time.time(),)).fetchall():
                committed=CreditBudget._scope_usage(c,row['account'],row['scope'])
                scopes.append(dict(row,committed=committed,remaining=max(0,row['credit_limit']-committed)))
        result=dict(status='inspected_not_qualified',network_calls=0,production_writes=0,
            active_budget_scopes=scopes[:100],budget_scopes_truncated=len(scopes)>100,
            examined=examined,bytes_examined=used,truncated=truncated,groups=dict(groups),samples=samples,issues=issues,
            required_evidence=['MapLark radius predicate and full-region completeness',
                'Independent same-profile radius response inside a complete POI bbox',
                'Geoapify full CHAOS category mapping and geometry contract'],
            note='Bounded retained samples only. Unobserved tags do not prove provider omissions. No certificate or runtime change.')
    if output is not None:
        target=Path(output);target.mkdir(mode=0o700,exist_ok=False)
        for index,item in enumerate(exports):
            raw=json.dumps(item,ensure_ascii=True,sort_keys=True).encode()
            filename=f'poi-sample-{index+1}.json'
            (target/filename).write_bytes(raw)
            samples[index]['export_file']=filename
            samples[index]['export_sha256']=hashlib.sha256(raw).hexdigest()
        (target/'report.json').write_text(json.dumps(result,ensure_ascii=True,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--output',help='New private directory; existing directories are never overwritten')
    args=parser.parse_args()
    try:
        result=inspect(args.db,args.output)
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as exc:
        print(json.dumps(dict(status='stopped',error_type=type(exc).__name__,network_calls=0)));return 1
    print(json.dumps(result));return 0


if __name__=='__main__':raise SystemExit(main())
