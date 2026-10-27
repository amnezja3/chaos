"""Admin-only provider control. GET is passive; probes use the shared slot."""
from dataclasses import replace
import os
import time

from .providers import Registry
from .service import Service, POIError, UpstreamUnavailable, bounded_http, validate, retry_delay

PROBE_TIMEOUT = 25
PROBE_DEADLINE = 35


def enabled():
    return os.environ.get('CHAOS_POI_PROVIDER_ADMIN_ENABLED','').strip()=='1'


def probe(service, registry, provider_id, revision, actor):
    candidate=next((v for v in registry.list() if v['id']==provider_id),None)
    if not candidate or candidate['revision']!=revision:
        raise POIError('provider_revision_conflict')
    if candidate['url'] in ('https://api.maplark.com/v3/osm_features','https://api.geoapify.com/v2/places'):
        raise POIError('feature_budgeted_probe_required')
    if (not candidate['probe_allowed'] or candidate['review_due_at']<=time.time()):
        raise POIError('provider_probe_not_approved')
    group=candidate['operator_group']
    if not service.repo.allowed(group):
        raise POIError('circuit_open')
    # A durable rate lease is intentionally retained, even if the probe fails.
    if not service.repo.acquire('@health-rate:'+group,900):
        raise POIError('probe_rate_limited')
    slot=service.repo.acquire('@upstream',PROBE_DEADLINE+7,probe_group=group)
    if not slot:
        raise POIError('upstream_busy')
    started=time.monotonic()
    result='error'
    success=False
    try:
        if not service.repo.allowed(group):
            raise POIError('circuit_open')
        # Always secure, including candidate tests before registry rollout.
        # HTTP is executed in the existing killable child with explicit mode.
        config=replace(service.config,deadline=PROBE_DEADLINE,max_response=65536,max_elements=100)
        status,retry,data=bounded_http(config,candidate['url'],
            f'[out:json][timeout:{PROBE_TIMEOUT}];node(1);out;',
            PROBE_TIMEOUT,started+PROBE_DEADLINE,secure=True)
        result=str(status)
        if status==200:
            validate(data,config)
            success=True
            service.repo.outcome(group,True)
        elif status in (429,500,502,503,504):
            service.repo.outcome(group,False,retry_delay(retry) or (30 if status==429 else 0))
        return registry.tested(provider_id,revision,success,actor)
    except POIError as exc:
        result=str(exc)
        if isinstance(exc,UpstreamUnavailable):
            service.repo.outcome(group,False)
        if result!='provider_revision_conflict':
            try:
                registry.tested(provider_id,revision,False,actor)
            except POIError:
                pass  # A configuration edit owns the newer revision.
        raise
    finally:
        try:
            registry.record_health(provider_id,revision,'probe',result,time.monotonic()-started)
        finally:
            try:
                service.repo.release('@probe:'+group,slot)
            finally:
                service.repo.release('@upstream',slot)


def register(app, authorize, csrf_failure):
    from flask import jsonify,request,session
    app.jinja_env.globals['poi_admin_enabled'] = enabled

    @app.route('/api/admin/poi-provider-observation',methods=['POST'])
    def poi_provider_observation():
        if not authorize(): return jsonify(ok=False,error='admin_required'),403
        if not enabled(): return jsonify(ok=False,error='poi_admin_disabled'),404
        failure=csrf_failure()
        if failure:return failure
        if not request.is_json or not request.content_length or request.content_length>2048:
            return jsonify(ok=False,error='invalid_request'),400
        body=request.get_json(silent=True)
        fields={'account','revision','credit_limit','used','period_start','period_end','observed_at'}
        if not isinstance(body,dict) or set(body)!=fields:return jsonify(ok=False,error='invalid_request'),400
        from .repository import Repository
        from .provider_observation import save
        import sqlite3
        try:
            data=save(Repository(os.environ.get('CHAOS_POI_CACHE_PATH','data/poi_cache.sqlite3')),**body)
            return jsonify(ok=True,observation=data)
        except ValueError as exc:
            return jsonify(ok=False,error=str(exc)),409 if 'conflict' in str(exc) else 400
        except sqlite3.OperationalError:
            return jsonify(ok=False,error='observation_storage_unavailable'),503

    @app.route('/api/admin/poi-world-view',methods=['GET'])
    def poi_world_view():
        if not authorize(): return jsonify(ok=False,error='admin_required'),403
        if not enabled(): return jsonify(ok=False,error='poi_admin_disabled'),404
        from .world_dashboard import coverage, budget_projection
        from .repository import Repository
        from pathlib import Path
        layer=request.args.get('layer','all')
        empty=request.args.get('empty','0')
        if empty not in ('0','1'): return jsonify(ok=False,error='invalid_filter'),400
        repo=Repository(os.environ.get('CHAOS_POI_CACHE_PATH','data/poi_cache.sqlite3'))
        try:
            raw_bounds=request.args.get('bbox')
            if raw_bounds is not None and len(raw_bounds)>160:raise ValueError('invalid_filter')
            bounds=tuple(map(float,raw_bounds.split(','))) if raw_bounds is not None else None
            data=coverage(repo,layer,empty=='1',bounds=bounds)
            from .scan_metrics import summary
            from .world_inventory_metrics import summary as inventory
            return jsonify(ok=True,coverage=data,inventory=inventory(repo),metrics=summary(repo),budgets=budget_projection(repo) if Path(repo.path).is_file() else [])
        except ValueError:
            return jsonify(ok=False,error='invalid_filter'),400

    @app.route('/api/admin/poi-routing',methods=['GET','POST'])
    def poi_routing_admin():
        if not authorize():
            return jsonify(ok=False,error='admin_required'),403
        if not enabled():
            return jsonify(ok=False,error='poi_admin_disabled'),404
        if request.method=='POST':
            failure=csrf_failure()
            if failure:
                return failure
            if not request.is_json or not request.content_length or request.content_length>4096:
                return jsonify(ok=False,error='invalid_request'),400
        from .routing import Routing
        import sqlite3
        service=Service(); registry=Registry(service.repo)
        try:
            registry.initialize()
            routing=Routing(service.repo); routing.initialize()
            if request.method=='POST':
                body=request.get_json(silent=True)
                if not isinstance(body,dict) or set(body)-{'action','layer','lane','revision','chain'}:
                    raise POIError('invalid_request')
                args=(body.get('layer'),body.get('lane'),body.get('revision'))
                if body.get('action')=='save':
                    routing.save(*args,body.get('chain'),session['user'])
                elif body.get('action')=='restore':
                    routing.restore(*args,session['user'])
                else:
                    raise POIError('invalid_action')
            data=routing.describe()
            from .credit_budget import CreditBudget
            data['budgets']={}
            for account in ('maplark','geoapify'):
                try:
                    data['budgets'][account]=CreditBudget(service.repo).status(account)
                except sqlite3.OperationalError:
                    data['budgets'][account]=[]
            return jsonify(ok=True,**data)
        except POIError as exc:
            return jsonify(ok=False,error=str(exc)),409 if 'conflict' in str(exc) else 400

    @app.route('/api/admin/poi-providers',methods=['GET','POST'])
    def poi_provider_admin():
        if not authorize():
            return jsonify(ok=False,error='admin_required'),403
        if not enabled():
            return jsonify(ok=False,error='poi_admin_disabled'),404
        if request.method=='POST':
            failure=csrf_failure()
            if failure:
                return failure
            if not request.is_json or not request.content_length or request.content_length>12000:
                return jsonify(ok=False,error='invalid_request'),400
        service=Service()
        registry=Registry(service.repo)
        try:
            registry.initialize()
            if request.method=='GET':
                from .world_operations import status as world_status
                return jsonify(ok=True,providers=registry.list(),health=registry.health(),audit=registry.audit(),
                               world=world_status(service.repo))
            body=request.get_json(silent=True)
            if not isinstance(body,dict) or set(body)-{'action','id','revision','fields','policy','scopes','evidence','review_due_at','enabled'}:
                raise POIError('invalid_request')
            action=body.get('action')
            identity=(body.get('id'),body.get('revision'))
            actor=session['user']
            if action=='save':
                value=registry.save(*identity,body.get('fields'),actor)
            elif action=='decision':
                value=registry.decision(*identity,body.get('policy'),body.get('scopes'),body.get('evidence'),body.get('review_due_at'),actor)
            elif action=='enable':
                value=registry.enable(*identity,body.get('enabled'),actor)
            elif action=='probe':
                value=probe(service,registry,*identity,actor)
            else:
                raise POIError('invalid_action')
            return jsonify(ok=True,provider=value)
        except POIError as exc:
            return jsonify(ok=False,error=str(exc)),409 if 'conflict' in str(exc) else 400
