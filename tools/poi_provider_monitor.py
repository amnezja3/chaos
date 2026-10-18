"""One bounded monitor tick; intended for an operator-controlled scheduler.

At most one interpreter probe per invocation. No polling inside Gunicorn.
"""
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from poi_infrastructure.admin import probe
from poi_infrastructure.providers import Registry
from poi_infrastructure.service import Service,POIError


def tick(service=None):
    if any(os.environ.get(flag,'').strip()!='1' for flag in
           ('CHAOS_POI_PROVIDER_MONITOR_ENABLED','CHAOS_POI_PROVIDER_REGISTRY_ENABLED','CHAOS_POI_INFRASTRUCTURE_ENABLED')):
        return dict(status='disabled',attempted=False)
    service=service or Service()
    registry=Registry(service.repo)
    registry.initialize()
    health=registry.health()
    candidates=registry.list()
    for candidate in candidates:
        if (not candidate['probe_allowed'] or candidate['review_due_at']<=time.time()):
            continue
        # A recent real success is better evidence than another synthetic call.
        if any(h['provider_id']==candidate['id'] and h['kind']=='normal_scan'
               and h['status']=='200' and h['revision']==candidate['revision']
               and time.time()-h['at']<900 for h in health):
            continue
        try:
            result=probe(service,registry,candidate['id'],candidate['revision'],'poi-monitor')
            return dict(status=result['technical_status'],attempted=True,provider=candidate['id'])
        except POIError as exc:
            if str(exc) in ('probe_rate_limited','circuit_open'):
                continue
            return dict(status=str(exc),provider=candidate['id'])
    return dict(status='no_probe_due',attempted=False)


if __name__=='__main__':
    print(json.dumps(tick()))
