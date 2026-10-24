"""Versioned per-layer/lane routing policy. Reads and edits never fetch data."""
import json
import os
import time

from .providers import Registry, endpoint_host
from .service import POIError

LAYERS = ('poi', 'roads', 'waterways', 'inland_water', 'coastline', 'land_water')
LANES = ('live', 'background')
MAPLARK = 'https://api.maplark.com/v3/osm_features'
GEOAPIFY = 'https://api.geoapify.com/v2/places'


def adapter(provider):
    if provider['url'] == MAPLARK:
        return 'maplark'
    if provider['url'] == GEOAPIFY:
        return 'geoapify'
    endpoint_host(provider['url'])
    return 'overpass'


def capability(provider, layer, lane):
    kind = adapter(provider)
    if kind == 'geoapify':
        return 'geoapify_contract_unverified' if layer == 'poi' else 'unsupported_layer'
    if layer == 'land_water' or (kind == 'overpass' and layer != 'poi'):
        return 'unsupported_layer'
    if lane == 'live' and layer != 'poi':
        return 'observation_only'
    if lane == 'background' and (kind != 'maplark' or layer == 'poi'):
        return 'unsupported_background_profile'
    return None


def reason(provider, layer, lane):
    unsupported = capability(provider, layer, lane)
    if unsupported:
        return unsupported
    if not provider.get('enabled'):
        return 'disabled'
    scope = 'normal_scan' if lane == 'live' else 'background_refresh'
    if not Registry.approved(provider, scope) or not Registry.approved(provider, 'storage'):
        return 'approval_required'
    if lane == 'background' and not Registry.approved(provider, 'world_storage'):
        return 'world_storage_required'
    return None


class Routing:
    def __init__(self, repo):
        self.repo = repo

    def initialize(self):
        # Explicit admin/setup use only, never in a scan.
        with self.repo.transaction() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS poi_routing (
                layer TEXT NOT NULL, lane TEXT NOT NULL, revision INTEGER NOT NULL,
                chain TEXT NOT NULL, PRIMARY KEY(layer,lane))''')
            c.execute('''CREATE TABLE IF NOT EXISTS poi_routing_audit (
                id INTEGER PRIMARY KEY, layer TEXT NOT NULL, lane TEXT NOT NULL,
                revision INTEGER NOT NULL, chain TEXT NOT NULL, previous TEXT NOT NULL,
                actor TEXT NOT NULL, at REAL NOT NULL)''')

    def get(self, layer, lane):
        if layer not in LAYERS or lane not in LANES:
            raise POIError('routing_invalid_profile')
        c = self.repo.connect()
        try:
            exists = c.execute("SELECT 1 FROM sqlite_master WHERE name='poi_routing'").fetchone()
            row = c.execute('SELECT revision,chain FROM poi_routing WHERE layer=? AND lane=?',
                            (layer,lane)).fetchone() if exists else None
        finally:
            c.close()
        # Match the existing MapLark selection, not arbitrary Overpass priorities.
        default = [p['id'] for p in Registry(self.repo).eligible('normal_scan')
                   if p['url'] == MAPLARK and Registry.approved(p, 'storage')][:1]
        return dict(layer=layer, lane=lane, revision=row['revision'] if row else 0,
                    chain=json.loads(row['chain']) if row else default if (layer,lane)==('poi','live') else [])

    def save(self, layer, lane, revision, chain, actor):
        if layer not in LAYERS or lane not in LANES or type(revision) is not int:
            raise POIError('routing_invalid_profile')
        providers = {p['id']: p for p in Registry(self.repo).list()}
        if (not isinstance(chain,list) or len(chain)>3 or any(not isinstance(p,str) for p in chain)
                or len(set(chain)) != len(chain) or any(p not in providers for p in chain)
                or not isinstance(actor,str) or not 1<=len(actor)<=120):
            raise POIError('routing_invalid_chain')
        for p in chain:
            adapter(providers[p])
        previous = self.get(layer,lane)
        with self.repo.transaction() as c:
            row = c.execute('SELECT revision FROM poi_routing WHERE layer=? AND lane=?',(layer,lane)).fetchone()
            if revision != (row[0] if row else 0) or previous['revision'] != revision:
                raise POIError('routing_revision_conflict')
            raw = json.dumps(chain)
            c.execute('INSERT OR REPLACE INTO poi_routing VALUES (?,?,?,?)',(layer,lane,revision+1,raw))
            c.execute('INSERT INTO poi_routing_audit(layer,lane,revision,chain,previous,actor,at) VALUES (?,?,?,?,?,?,?)',
                      (layer,lane,revision+1,raw,json.dumps(previous['chain']),actor,time.time()))
        return self.get(layer,lane)

    def restore(self, layer, lane, revision, actor):
        c = self.repo.connect()
        try:
            row = c.execute('SELECT previous FROM poi_routing_audit WHERE layer=? AND lane=? AND revision=?',
                            (layer,lane,revision)).fetchone()
        finally:
            c.close()
        if not row:
            raise POIError('routing_no_previous')
        # Revalidates IDs. Never restores provider approvals, secrets or enable flags.
        return self.save(layer,lane,revision,json.loads(row[0]),actor)

    def describe(self):
        providers = {p['id']:p for p in Registry(self.repo).list()}
        rows = []
        for layer in LAYERS:
            for lane in LANES:
                route = self.get(layer,lane)
                route['candidates'] = [dict(id=p, reason=reason(providers[p],layer,lane)
                    if p in providers else 'provider_missing') for p in route['chain']]
                rows.append(route)
        c = self.repo.connect()
        try:
            history = [dict(r) for r in c.execute('SELECT layer,lane,revision,actor,at FROM poi_routing_audit ORDER BY id DESC LIMIT 30')]
        finally:
            c.close()
        return dict(enabled=os.environ.get('CHAOS_POI_ROUTING_ENABLED')=='1', routes=rows,
                    history=history, background_running=False,
                    capabilities={p: {layer: capability(v,layer,'live') for layer in LAYERS}
                                  for p,v in providers.items()})
