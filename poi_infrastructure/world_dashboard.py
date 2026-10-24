"""Passive, bounded world evidence projection. No upstream or inferred coverage."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from .world_storage import FORMAT, LAYER_BITS
from .world_read import READ_FORMAT, SelectionProof


def coverage(repo, layer='all', show_empty=False):
    if layer not in ('all', *LAYER_BITS): raise ValueError('invalid_layer')
    result=dict(network_calls=0, layer=layer, items=[], truncated=False, hidden_empty=0,
                snapshot_limit=100, byte_limit=8*1024*1024, examined=0,
                scope='bounded_snapshot_observations_not_planet_coverage')
    if not Path(repo.path).is_file(): return result
    with closing(sqlite3.connect(Path(repo.path).resolve().as_uri()+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'world_schema','world_snapshot','world_member','world_coverage','poi_provider_config'}<=tables:
            return result
        if c.execute('SELECT version FROM world_schema').fetchone()[0]!=2: return result
        deadline=time.monotonic()+2
        c.set_progress_handler(lambda:int(time.monotonic()>deadline),10000)
        try:
            c.execute('BEGIN')
            providers={r['id']:dict(revision=r['revision'],config=json.loads(r['config']))
                       for r in c.execute('SELECT id,revision,config FROM poi_provider_config')}
            rows=c.execute('''SELECT s.id,s.provider,s.fetched,s.fresh_until,s.usable_until,
                length(s.payload) payload_size,s.digest,c.bounds proof
                FROM world_snapshot s LEFT JOIN world_coverage c
                ON c.snapshot_id=s.id AND c.profile=? WHERE s.profile=?
                ORDER BY s.fetched DESC,s.id LIMIT 101''',(READ_FORMAT,FORMAT)).fetchall()
            result['truncated']=len(rows)>100
            used=0
            now=time.time()
            for row in rows[:100]:
                used+=row['payload_size']
                if used>result['byte_limit']:
                    result['truncated']=True;break
                result['examined']+=1
                payload=c.execute('SELECT payload FROM world_snapshot WHERE id=?',(row['id'],)).fetchone()[0]
                if hashlib.sha256(payload).hexdigest()!=row['digest']: continue
                try:
                    raw=json.loads(payload)
                    profile=raw['profile']; objects=raw['objects']
                    counts={name:0 for name in LAYER_BITS}
                    # Membership counts from the persisted canonical index, not provider labels.
                    members=c.execute('SELECT layer_mask,spatial_valid,west,south,east,north FROM world_member WHERE snapshot_id=?',(row['id'],)).fetchall()
                    for m in members:
                        for name,bit in LAYER_BITS.items():
                            if m['layer_mask'] & bit: counts[name]+=1
                    proof=SelectionProof(**json.loads(row['proof'])) if row['proof'] else None
                    selected=proof.layer if proof else (profile if profile in LAYER_BITS else 'poi')
                    if layer!='all' and not counts[layer] and selected!=layer: continue
                    valid=[m for m in members if m['spatial_valid'] and (layer=='all' or m['layer_mask'] & LAYER_BITS[layer])]
                    bounds=([min(m['west'] for m in valid),min(m['south'] for m in valid),
                             max(m['east'] for m in valid),max(m['north'] for m in valid)] if valid else None)
                    area=bool(proof and proof.mode=='area' and (layer=='all' or proof.layer==layer))
                    proof_matches=bool(proof and raw.get('coverage')==json.loads(json.dumps(proof.document()))
                        and raw.get('completeness')=='complete' and not raw.get('reasons'))
                    policy=providers.get(row['provider'],{})
                    conf=policy.get('config',{})
                    permitted=(policy.get('revision')==raw.get('revision')
                        and conf.get('policy_status')=='approved_for_defined_use'
                        and {'storage','world_storage'}<=set(conf.get('scopes',[]))
                        and conf.get('review_due_at',0)>now
                        and (conf.get('evidence') or {}).get('reference')==raw.get('storage_reference'))
                    state='UNKNOWN'
                    if area and proof_matches:
                        state=('COMPLETE_FRESH' if now<row['fresh_until'] else
                               'COMPLETE_STALE' if now<row['usable_until'] else 'EXPIRED')
                    elif raw.get('completeness')=='partial': state='PARTIAL'
                    count=len(objects) if layer=='all' else counts[layer]
                    if count==0 and area and proof_matches and not show_empty:
                        result['hidden_empty']+=1;continue
                    result['items'].append(dict(id=row['id'],provider=row['provider'],profile=profile,
                        layers=counts,objects=count,state=state,scope='area' if area else 'observations',
                        bounds=list(proof.bounds) if area else bounds,
                        reason='area_proof' if area and proof_matches else 'no_regional_selection_proof',
                        policy_allowed=permitted,local_read_allowed=bool(permitted and area and proof_matches and now<row['fresh_until']),
                        fetched=row['fetched'],fresh_until=row['fresh_until'],usable_until=row['usable_until'],
                        bytes=row['payload_size'],empty=count==0,
                        proof_mode=proof.mode if proof else None,
                        certificate=proof.certificate if proof else None))
                except (ValueError,TypeError,KeyError):
                    continue
        except sqlite3.OperationalError as exc:
            if 'interrupt' not in str(exc).lower(): raise
            result['truncated']=True
    return result


def budget_projection(repo):
    """Internal usage only. No fake provider balance or automatic reconciliation."""
    from .credit_budget import CreditBudget
    accounts=[]
    with closing(repo.connect()) as c:
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'world_credit_operation','world_credit_window'}<=tables: return accounts
        for account in ('maplark','geoapify'):
            windows=CreditBudget(repo).status(account)
            for w in windows:
                percent=100*w['committed']/w['credit_limit'] if w['credit_limit'] else None
                w['percent']=percent
                w['warning_threshold']=next((t for t in (95,85,70) if percent is not None and percent>=t),None)
            row=c.execute('''SELECT count(*) operations,
                coalesce(sum(CASE WHEN state IN ('reserved','uncertain') THEN reserved ELSE 0 END),0) uncertain_reserved,
                coalesce(sum(charged),0) reported_credits,
                coalesce(sum(state IN ('reserved','uncertain')),0) unresolved
                FROM world_credit_operation WHERE account=?''',(account,)).fetchone()
            from .provider_observation import read as read_observation
            observation=read_observation(repo,account)
            accounts.append(dict(account=account,windows=windows,provider_observation=observation,provider_balance=None,
                provider_balance_source='unknown',lifetime_operations=dict(row)))
    return accounts
