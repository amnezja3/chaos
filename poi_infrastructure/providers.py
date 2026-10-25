"""Versioned provider candidates and explicit, scope-bound approvals.

The registry is separate from the existing `providers` circuit-breaker table.
Reads never perform network requests. Saving a candidate never activates it.
"""
import json
import re
import time
from urllib.parse import urlsplit

from .service import POIError

SCOPES = frozenset(('small_probe', 'normal_scan', 'wide_fetch', 'background_refresh', 'storage', 'world_storage'))
POLICIES = frozenset(('unknown', 'public_declaration_only', 'operator_confirmation_pending',
                      'approved_for_defined_use', 'restricted', 'rejected', 'expired_review'))


def endpoint_host(url):
    if not isinstance(url, str) or len(url) > 300 or any(ord(c) < 33 for c in url):
        raise POIError('provider_invalid_url')
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError as exc:
        raise POIError('provider_invalid_url') from exc
    host = parsed.hostname or ''
    if (parsed.scheme != 'https' or parsed.username or parsed.password or parsed.query or parsed.fragment
            or port not in (None,443) or not parsed.path.endswith('/api/interpreter')
            or '..' in parsed.path or '%' in parsed.path or '\\' in url
            or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',host)
            or '.' not in host or host.endswith('.local') or host.replace('.','').isdigit()):
        raise POIError('provider_invalid_url')
    return host


class Registry:
    def __init__(self, repository):
        self.repo = repository

    def initialize(self):
        self.repo.initialize()
        with self.repo.transaction() as c:
            c.execute('CREATE TABLE IF NOT EXISTS poi_provider_epoch (id INTEGER PRIMARY KEY CHECK(id=1), value INTEGER NOT NULL)')
            c.execute('INSERT OR IGNORE INTO poi_provider_epoch VALUES (1,0)')
            c.execute('''CREATE TABLE IF NOT EXISTS poi_provider_config (
                id TEXT PRIMARY KEY, revision INTEGER NOT NULL, config TEXT NOT NULL)''')
            c.execute('''CREATE TABLE IF NOT EXISTS poi_provider_audit (
                id INTEGER PRIMARY KEY, provider_id TEXT NOT NULL, actor TEXT NOT NULL,
                action TEXT NOT NULL, before_json TEXT, after_json TEXT, at REAL NOT NULL)''')
            c.execute('''CREATE TABLE IF NOT EXISTS poi_provider_health (
                id INTEGER PRIMARY KEY, provider_id TEXT NOT NULL, revision INTEGER NOT NULL,
                kind TEXT NOT NULL, status TEXT NOT NULL, latency REAL NOT NULL, at REAL NOT NULL)''')

    def _load(self, c, provider_id):
        row = c.execute('SELECT config FROM poi_provider_config WHERE id=?',(provider_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def _write(self, c, value, old, actor, action):
        if not isinstance(actor,str) or not actor or len(actor)>120:
            raise POIError('provider_invalid_actor')
        value['revision'] = (old['revision'] if old else 0) + 1
        raw = json.dumps(value,ensure_ascii=False,allow_nan=False)
        c.execute('INSERT OR REPLACE INTO poi_provider_config VALUES (?,?,?)',
                  (value['id'],value['revision'],raw))
        c.execute('UPDATE poi_provider_epoch SET value=value+1 WHERE id=1')
        c.execute('INSERT INTO poi_provider_audit(provider_id,actor,action,before_json,after_json,at) VALUES (?,?,?,?,?,?)',
                  (value['id'],actor,action,json.dumps(old,ensure_ascii=False),raw,time.time()))
        return value

    def list(self):
        c = self.repo.connect()
        try:
            return [json.loads(r[0]) for r in c.execute('SELECT config FROM poi_provider_config ORDER BY id')]
        finally:
            c.close()

    def save(self, provider_id, revision, fields, actor):
        if not isinstance(provider_id,str) or not re.fullmatch('[a-z0-9_-]{1,60}',provider_id):
            raise POIError('provider_invalid_id')
        if not isinstance(fields,dict) or set(fields) != {'name','url','operator_group','priority'}:
            raise POIError('provider_invalid_fields')
        # Feature API has a separate authenticated transport; never allow
        # arbitrary feature URLs or query-string credentials into the registry.
        feature_hosts = {'https://api.maplark.com/v3/osm_features': 'api.maplark.com',
                         'https://api.geoapify.com/v2/places': 'api.geoapify.com'}
        if fields['url'] not in feature_hosts:
            endpoint_host(fields['url'])
        elif fields['operator_group'] != feature_hosts[fields['url']]:
            raise POIError('provider_invalid_fields')
        if (not isinstance(fields['name'],str) or not 1 <= len(fields['name']) <= 80
                or not isinstance(fields['operator_group'],str)
                or not re.fullmatch('[a-z0-9.-]{1,100}',fields['operator_group'])
                or type(fields['priority']) is not int or not 0 <= fields['priority'] <= 100):
            raise POIError('provider_invalid_fields')
        with self.repo.transaction() as c:
            old = self._load(c,provider_id)
            if revision != (old['revision'] if old else 0):
                raise POIError('provider_revision_conflict')
            value = dict(old or {}, id=provider_id, **fields)
            changed = not old or any(old[k] != fields[k] for k in ('url','operator_group'))
            if changed:
                value.update(enabled=False,technical_status='untested',policy_status='unknown',
                             scopes=[],evidence=None,review_due_at=0,probe_allowed=False)
            return self._write(c,value,old,actor,'save')

    def decision(self, provider_id, revision, policy, scopes, evidence, review_due_at, actor):
        if (not isinstance(policy,str) or policy not in POLICIES or not isinstance(scopes,list)
                or any(not isinstance(s,str) for s in scopes) or not set(scopes) <= SCOPES
                or len(set(scopes)) != len(scopes) or not isinstance(evidence,dict)
                or set(evidence) != {'source_url','reference','notes'}):
            raise POIError('provider_invalid_decision')
        if any(not isinstance(v,str) or not 1 <= len(v) <= 2000 for v in evidence.values()):
            raise POIError('provider_invalid_evidence')
        url = urlsplit(evidence['source_url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise POIError('provider_invalid_evidence')
        if (type(review_due_at) not in (int,float) or not time.time() < review_due_at <= time.time()+366*86400):
            raise POIError('provider_invalid_review_date')
        with self.repo.transaction() as c:
            old = self._load(c,provider_id)
            if not old or old['revision'] != revision:
                raise POIError('provider_revision_conflict')
            value = dict(old, policy_status=policy, scopes=scopes, evidence=dict(evidence,checked_by=actor,checked_at=time.time()),
                         review_due_at=review_due_at,enabled=False,
                         probe_allowed=policy=='approved_for_defined_use' and 'small_probe' in scopes)
            return self._write(c,value,old,actor,'decision')

    def tested(self, provider_id, revision, success, actor):
        """Internal transport callback only: never exposed as a client action."""
        with self.repo.transaction() as c:
            old = self._load(c,provider_id)
            if not old or old['revision'] != revision:
                raise POIError('provider_revision_conflict')
            value = dict(old, technical_status='tested_ok' if success else 'tested_failed',enabled=old['enabled'] if success else False)
            return self._write(c,value,old,actor,'technical_test')

    def enable(self, provider_id, revision, enabled, actor):
        if type(enabled) is not bool:
            raise POIError('provider_invalid_enabled')
        with self.repo.transaction() as c:
            old = self._load(c,provider_id)
            if not old or old['revision'] != revision:
                raise POIError('provider_revision_conflict')
            background=all(self.approved(old,scope) for scope in ('background_refresh','storage','world_storage'))
            if enabled and not (self.approved(old,'normal_scan') or background):
                raise POIError('provider_not_approved')
            return self._write(c,dict(old,enabled=enabled),old,actor,'enable' if enabled else 'disable')

    @staticmethod
    def approved(value,scope):
        return (value['technical_status']=='tested_ok'
                and value['policy_status']=='approved_for_defined_use'
                and value['review_due_at']>time.time() and scope in value['scopes'])

    def eligible(self,scope):
        return sorted((v for v in self.list() if v['enabled'] and self.approved(v,scope)),
                      key=lambda v:(v['priority'],v['id']))

    def record_health(self, provider_id, revision, kind, status, latency):
        with self.repo.transaction() as c:
            c.execute('INSERT INTO poi_provider_health(provider_id,revision,kind,status,latency,at) VALUES (?,?,?,?,?,?)',
                      (provider_id,revision,kind,str(status)[:80],latency,time.time()))
            c.execute('DELETE FROM poi_provider_health WHERE id NOT IN (SELECT id FROM poi_provider_health ORDER BY id DESC LIMIT 1000)')

    def health(self):
        c = self.repo.connect()
        try:
            return [dict(r) for r in c.execute('SELECT * FROM poi_provider_health ORDER BY id DESC LIMIT 100')]
        finally:
            c.close()

    def audit(self):
        c=self.repo.connect()
        try:
            return [dict(r) for r in c.execute('SELECT id,provider_id,actor,action,at FROM poi_provider_audit ORDER BY id DESC LIMIT 100')]
        finally:
            c.close()
