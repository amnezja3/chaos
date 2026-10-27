"""Explicit VK live/wide scope and routing decision; no network or env change."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from poi_infrastructure.repository import Repository
from poi_infrastructure.providers import Registry
from poi_infrastructure.routing import Routing,reason
from poi_infrastructure.credit_budget import CreditBudget
from tools.overpass_collection_enable import PID,URL


def configure(repo,backup=None,approve=False):
    registry=Registry(repo)
    providers={p['id']:p for p in registry.list()}
    p=providers.get(PID)
    if (not p or p['url']!=URL or not p['enabled'] or p['technical_status']!='tested_ok'
            or not all(Registry.approved(p,s) for s in ('background_refresh','storage','world_storage'))):
        raise ValueError('approved_tested_vk_collection_required')
    fallback=providers.get('maplark')
    if not fallback or reason(fallback,'poi','live'):raise ValueError('working_maplark_fallback_required')
    windows=CreditBudget(repo).status(PID)
    if not windows or any(w['remaining']<1 for w in windows):raise ValueError('configured_attempt_budget_required')
    route=Routing(repo).get('poi','live')
    background=Routing(repo).get('poi','background')
    if reason(fallback,'poi','background'):raise ValueError('maplark_archive_approval_required')
    archive_chain=['maplark']+[pid for pid in background['chain'] if pid!='maplark']
    archive_chain=archive_chain[:3]
    scopes=sorted(set(p['scopes'])|{'normal_scan','wide_fetch'})
    result=dict(status='plan',network_calls=0,provider=PID,revision=p['revision'],
        scopes=scopes,chain=[PID,'maplark'],previous_chain=route['chain'],
        environment_changed=False,review_until=p['review_due_at'],budgets_unchanged=True,
        background_chain=archive_chain,previous_background_chain=background['chain'])
    if backup is None:return result
    if not approve:raise ValueError('explicit_live_wide_decision_required')
    backup=Path(backup)
    with backup.open('xb'):pass
    with closing(sqlite3.connect(Path(repo.path).resolve().as_uri()+'?mode=ro',uri=True)) as src:
        with closing(sqlite3.connect(backup)) as dest:
            src.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('backup_integrity_failed')
    actor='operator:regional-live-vk'
    if set(p['scopes'])!=set(scopes):
        evidence={k:p['evidence'][k] for k in ('source_url','reference','notes')}
        evidence['reference']='163.5 VK live/wide operator decision'
        evidence['notes']='Operator accepts live scans and bounded 1500m closure fills. Shared existing attempt budget; MapLark fallback. Public declaration, no individual provider confirmation.'
        p=registry.decision(PID,p['revision'],'approved_for_defined_use',scopes,evidence,p['review_due_at'],actor)
    if route['chain']!=result['chain']:
        Routing(repo).save('poi','live',route['revision'],result['chain'],actor)
    if background['chain']!=archive_chain:
        Routing(repo).save('poi','background',background['revision'],archive_chain,actor)
    return dict(result,status='configured',revision=p['revision'],backup=str(backup))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default='data/poi_cache.sqlite3')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--approve-live-wide',action='store_true')
    parser.add_argument('--backup')
    a=parser.parse_args()
    try:
        if not Path(a.db).is_file() or Path(a.db).name=='game.sqlite3':raise ValueError('poi_database_required')
        if a.apply!=bool(a.backup):raise ValueError('apply_requires_backup')
        print(json.dumps(configure(Repository(a.db),a.backup,a.approve_live_wide)))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status='stopped',error_type=type(exc).__name__,network_calls=0)))
        return 1


if __name__=='__main__':raise SystemExit(main())
