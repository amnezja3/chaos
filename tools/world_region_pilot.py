"""One-region roads storage pilot. No gameplay activation or background loop.

The operator accepts an empirical selection contract for ONE fresh snapshot.
This is not a provider attestation, a global certificate or an OSM version claim.
An isolated adapter identifier prevents normal readers from selecting this data.
"""
import argparse
from contextlib import closing
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.providers import Registry
from poi_infrastructure.repository import Repository
from poi_infrastructure.service import POIError
from poi_infrastructure.world_adapters import MAPLARK_VERSION,normalize_maplark,plan_maplark_region
from poi_infrastructure.world_contract import ContractError,Provenance
from poi_infrastructure.world_region_candidate import prepare
from poi_infrastructure.world_read import AREA_SELECTION,SelectionProof,WorldReadPlanner
from poi_infrastructure.world_storage import CanonicalWorldRepository
from tools.world_region_probe import BOUNDS,PARTS,capture

KEY='region:roads-2036-5153-storage-pilot-v1'
ADAPTER='maplark-roads-single-region-pilot-v1'
CERTIFICATE='operator-empirical-roads-2036-5153-v1'


class ReadOnlyRepository(Repository):
    def connect(self):
        c=sqlite3.connect(Path(self.path).resolve().as_uri()+'?mode=ro',uri=True,timeout=.5)
        c.row_factory=sqlite3.Row
        return c


def provider(repo):
    p=next((p for p in Registry(repo).list() if p['id']=='maplark'),None)
    if not p or not all(Registry.approved(p,s) for s in ('storage','world_storage')):
        raise ContractError('approved_maplark_world_storage_required')
    return p


def backup_database(db,target):
    source=Path(db).resolve()
    if not source.is_file():raise ContractError('existing_poi_database_required')
    with closing(sqlite3.connect(source.as_uri()+'?mode=ro',uri=True)) as src:
        tables={r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'world_schema','world_snapshot','world_member','world_coverage','leases'}<=tables or 'users' in tables:
            raise ContractError('canonical_poi_database_required')
        if src.execute('SELECT version FROM world_schema').fetchone()[0]!=2:
            raise ContractError('canonical_schema_v2_required')
        # Exclusive creation, including when two invocations race. Never copy a WAL file.
        fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
        with closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or dst.execute('PRAGMA foreign_key_check').fetchall():
                raise ContractError('backup_integrity_failed')


def check(db):
    if not Path(db).is_file():raise ContractError('existing_poi_database_required')
    repo=ReadOnlyRepository(db);p=provider(repo)
    def active():
        try:return provider(repo)['revision']==p['revision']
        except ContractError:return False
    # Reopen storage for every selection, as independent processes would do.
    reads={}
    for name,bounds in PARTS.items():
        reads[name]=WorldReadPlanner(CanonicalWorldRepository(ReadOnlyRepository(db))).read(
            provider='maplark',revision=p['revision'],storage_reference=p['evidence']['reference'],
            profile='roads',selection=AREA_SELECTION,adapter_version=ADAPTER,layer='roads',
            bounds=bounds,still_active=active)
    ids={name:{o.identity for o in r.batch.objects} if r.batch else set() for name,r in reads.items()}
    snapshots={r.snapshot for r in reads.values()}
    passed=(all(r.state=='COMPLETE_FRESH' for r in reads.values()) and len(snapshots)==1
            and ids['left']|ids['right']==ids['parent'])
    if passed:
        parent={o.identity:o.geometry for o in reads['parent'].batch.objects}
        passed=all(parent[o.identity]==o.geometry for name in ('left','right') for o in reads[name].batch.objects)
    return dict(status='local_pilot_pass' if passed else 'local_pilot_not_fresh',network_calls=0,
                production_writes=0,gameplay_changed=False,global_region_certified=False,
                dataset_version_verified=False,adapter=ADAPTER,
                reads={n:dict(state=r.state,reason=r.reason,objects=len(ids[n]) if r.batch else None,
                              snapshot=r.snapshot) for n,r in reads.items()},
                full_geometry_and_union_pass=passed)


def run(db,output=None,backup=None,*,execute=False,approve=False,accept_variable_cost=False,transport=None):
    plan=dict(status='plan',bounds=BOUNDS,profile='roads',adapter=ADAPTER,network_calls=0,
              max_network_calls=1,reservation=20,fresh_seconds=300,usable_seconds=1800,
              gameplay_changed=False,environment_changed=False,registry_changed=False,
              global_region_certified=False,dataset_version_verified=False,
              qualification='operator accepted single-snapshot empirical pilot; no unions of source versions')
    if not execute:return plan
    if not approve:raise ContractError('explicit_single_region_pilot_approval_required')
    if not accept_variable_cost:raise ContractError('variable_credit_cost_acceptance_required')
    if not output or not backup:raise ContractError('new_output_and_backup_required')
    if Path(output).exists():raise ContractError('new_output_directory_required')
    request=plan_maplark_region(BOUNDS);request.authenticated_wire()
    if not Path(db).is_file():raise ContractError('existing_poi_database_required')
    repo=Repository(db);p=provider(repo)
    if not p['enabled'] or p['url']!=request.endpoint:raise ContractError('active_maplark_required')
    backup_database(db,backup)
    owner=repo.acquire(KEY,120)
    if not owner:raise ContractError('regional_pilot_busy')
    try:
        result=capture(db,output,execute=True,approve=True,accept_variable_cost=True,
                       transport=transport,_pilot=True)
        current=provider(repo)
        if current['revision']!=p['revision'] or not current['enabled']:
            raise ContractError('regional_policy_changed')
        destination=Path(output)
        body=json.loads((destination/'body.json').read_text(encoding='utf8'))
        headers=json.loads((destination/'headers.json').read_text(encoding='utf8'))
        fetched=result['fetched_at']
        batch=normalize_maplark(body,headers,Provenance('maplark',MAPLARK_VERSION,KEY,fetched,
                                  license_ref='ODbL-1.0'),profile='roads',maximum=1000)
        candidate=prepare(batch,request)
        if not candidate.batch.objects:raise ContractError('regional_empty_pilot_needs_review')
        # Only this CLI can opt into this isolated experimental adapter/proof pair.
        # Original provider identity, snapshot, license and source time are retained.
        qualified=replace(candidate.batch,selection=AREA_SELECTION,objects=tuple(
            replace(o,provenance=replace(o.provenance,adapter_version=ADAPTER)) for o in candidate.batch.objects))
        proof=SelectionProof('area','roads','roads',AREA_SELECTION,ADAPTER,KEY,BOUNDS,CERTIFICATE)
        snapshot=CanonicalWorldRepository(repo).publish_batch(KEY,owner,qualified,provider='maplark',
            revision=p['revision'],storage_reference=p['evidence']['reference'],
            fresh_until=fetched+300,usable_until=fetched+1800,coverage=proof,
            certified_selections=(('maplark',ADAPTER,'roads',AREA_SELECTION,CERTIFICATE),))
        if not snapshot:raise ContractError('regional_pilot_lease_lost')
        verification=check(db)
        report=dict(plan,status='published_pilot',network_calls=1,snapshot=snapshot,backup=str(backup),
                    billing=result['billing'],raw_objects=candidate.raw_objects,
                    stored_objects=len(qualified.objects),excluded_ids=candidate.excluded_ids,
                    local_verification=verification)
        with os.fdopen(os.open(destination/'pilot.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',encoding='utf8') as f:
            json.dump(report,f,ensure_ascii=False,allow_nan=False)
        return report
    finally:repo.release(KEY,owner)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',default='data/poi_cache.sqlite3')
    p.add_argument('--output');p.add_argument('--backup')
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--execute',action='store_true');mode.add_argument('--check',action='store_true')
    p.add_argument('--approve-single-region-pilot',action='store_true')
    p.add_argument('--accept-variable-credit-cost',action='store_true')
    a=p.parse_args()
    try:
        result=check(a.db) if a.check else run(a.db,a.output,a.backup,execute=a.execute,
            approve=a.approve_single_region_pilot,accept_variable_cost=a.accept_variable_credit_cost)
        print(json.dumps(result));return 0 if result['status'] in ('plan','local_pilot_pass') or result.get('local_verification',{}).get('full_geometry_and_union_pass') else 2
    except Exception as exc:
        print(json.dumps(dict(ok=False,error=str(exc) if isinstance(exc,(ContractError,POIError)) else type(exc).__name__,
                              retry_automatically=False)));return 1


if __name__=='__main__':raise SystemExit(main())
