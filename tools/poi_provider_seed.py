"""Import the four existing scanner endpoints as disabled candidates. No HTTP."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository

CANDIDATES=[
    ('overpass-de','Overpass DE','https://overpass-api.de/api/interpreter','overpass-api.de',10),
    ('overpass-de-lz4','Overpass DE / LZ4','https://lz4.overpass-api.de/api/interpreter','overpass-api.de',20),
    ('overpass-kumi','Overpass Kumi','https://overpass.kumi.systems/api/interpreter','overpass.kumi.systems',30),
    ('overpass-nchc','Overpass NCHC','https://overpass.nchc.org.tw/api/interpreter','overpass.nchc.org.tw',40),
]


def seed(path, apply=False):
    path=Path(path).resolve()
    if not path.is_file() or path.name=='game.sqlite3':
        raise ValueError('Use an existing, migrated POI database')
    c=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)
    try:
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'users' in tables or not {'cache','leases','poi_provider_config','poi_provider_audit','poi_provider_epoch'}<=tables:
            raise ValueError('Not a migrated POI database')
        existing=[json.loads(r[0]) for r in c.execute('SELECT config FROM poi_provider_config')]
    finally:c.close()
    registry=Registry(Repository(path))
    added,skipped=[],[]
    for ident,name,url,group,priority in CANDIDATES:
        # Preserve all admin edits, approvals and enabled states on rerun.
        if any(v['id']==ident or v['url']==url for v in existing):
            skipped.append(ident)
            continue
        if apply:
            registry.save(ident,0,dict(name=name,url=url,operator_group=group,priority=priority),'cli:legacy-seed')
        added.append(ident)
    return dict(ok=True,status='seeded' if apply else 'dry_run',
                added=added,skipped=skipped,network_calls=0,
                new_candidates_enabled=False,existing_entries_unchanged=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default=os.environ.get('CHAOS_POI_CACHE_PATH') or str(ROOT/'data/poi_cache.sqlite3'))
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    print(json.dumps(seed(args.db,args.apply)))


if __name__=='__main__':main()
