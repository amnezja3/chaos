"""Prepare the operator-approved one-hour roads pilot; never starts HTTP."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.discovery_runtime import load_permit, cycle

PILOT = '163-roads-2036-5153-v1'


def prepare(db, permit_path, backup):
    db, path, backup = Path(db), Path(permit_path), Path(backup)
    if not db.is_file(): raise ValueError('existing_database_required')
    repo = Repository(db)
    if path.exists():
        permit = load_permit(path)
        if (permit.budget_id != PILOT or permit.cells != frozenset({(2036,5153)})
                or permit.acquisition != 'radius-300-v1'
                or permit.retention_seconds != 1800
                or permit.profiles != frozenset({'roads'}) or permit.reservation != 20):
            raise ValueError('existing_permit_differs')
        return dict(status='already_prepared', network_calls=0, plan=cycle(repo,path))
    if backup.exists(): raise ValueError('backup_already_exists')
    registry = Registry(repo)
    candidates = [p for p in registry.list() if p['id']=='maplark']
    if (not candidates or not candidates[0]['enabled']
            or not Registry.approved(candidates[0], 'normal_scan')
            or candidates[0]['url']!='https://api.maplark.com/v3/osm_features'):
        raise ValueError('active_maplark_required')
    old = candidates[0]
    now = time.time()
    until = now + 3600
    if old['review_due_at'] < until: raise ValueError('provider_review_expires_before_pilot')
    scopes = ['discovery:'+PILOT, 'discovery:'+PILOT+':roads']
    with closing(repo.connect()) as c:
        if c.execute('SELECT 1 FROM world_credit_scope WHERE account=? AND scope=?',
                     ('maplark', scopes[0])).fetchone():
            raise ValueError('pilot_already_exists_do_not_reset')
        c.execute('SELECT id FROM world_discovery_job LIMIT 1').fetchall()
    backup.parent.mkdir(parents=True, exist_ok=True)
    # SQLite backup captures committed WAL data without copying live files.
    with closing(repo.connect()) as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            raise ValueError('backup_integrity')
    backup.with_suffix('.provider.json').write_text(json.dumps(old,indent=2),encoding='utf8')
    path.parent.mkdir(parents=True, exist_ok=True)
    data=dict(cells=[[2036,5153]],profiles=['roads'],until=until,reservation=20,budget_id=PILOT)
    # Exclusive creation never replaces an active or expired operator permit.
    with path.open('x',encoding='utf8') as f:
        json.dump(data,f,indent=2)
    with repo.transaction() as c:
        current=registry._load(c,'maplark')
        if current['revision']!=old['revision']: raise ValueError('provider_revision_conflict')
        for scope in scopes:
            c.execute('INSERT INTO world_credit_scope VALUES (?,?,?,?,?)',('maplark',scope,now,until,20))
        evidence=dict(old['evidence'])
        evidence.update(reference='Operator-approved sprint 163 roads pilot',
            notes='One-hour permit, cell 2036/5153, roads only, one job, internal cap 20. Existing gameplay scopes preserved.',
            checked_by='operator:163-pilot',checked_at=now)
        value=dict(old,scopes=sorted(set(old['scopes'])|{'background_refresh','storage','world_storage'}),evidence=evidence)
        registry._write(c,value,old,'operator:163-pilot','bounded_discovery_pilot')
    return dict(status='prepared',network_calls=0,permit=str(path),backup=str(backup),
                until=until,environment_changed=False,plan=cycle(repo,path))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='data/poi_cache.sqlite3')
    p.add_argument('--permit',default='data/discovery-permit.json')
    p.add_argument('--backup',required=True)
    a=p.parse_args()
    print(json.dumps(prepare(a.db,a.permit,a.backup)))


if __name__=='__main__': main()
