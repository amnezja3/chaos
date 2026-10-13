"""Small shared control plane. No player profiles or credentials are persisted."""
import json
import time
import uuid
from contextlib import contextmanager

from database import db_connect

DEFAULTS = {"primary": "ollama", "model": "", "remote_seconds": 25,
            "total_seconds": 630, "max_tokens": 256, "daily_token_budget": 0}


class ProviderConfigError(ValueError):
    pass


class ProviderRevisionConflict(ProviderConfigError):
    pass


class ProviderStore:
    def __init__(self, db_path):
        self.db_path = db_path
        with db_connect(db_path) as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS narrative_provider_config (
                    id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL,
                    payload TEXT NOT NULL, updated_by TEXT NOT NULL, updated_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS narrative_provider_config_audit (
                    revision INTEGER PRIMARY KEY, payload TEXT NOT NULL, actor TEXT NOT NULL, created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS narrative_provider_state (
                    key TEXT PRIMARY KEY, until_at REAL NOT NULL, owner TEXT NOT NULL DEFAULT '', code TEXT NOT NULL DEFAULT '');
                CREATE TABLE IF NOT EXISTS narrative_provider_budget (
                    day TEXT PRIMARY KEY, reserved INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS narrative_provider_calls (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, attempt_id TEXT NOT NULL,
                    revision INTEGER NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL,
                    started_at REAL NOT NULL, duration_ms INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL, error_code TEXT NOT NULL DEFAULT '', http_status INTEGER NOT NULL DEFAULT 0,
                    metadata TEXT NOT NULL DEFAULT '{}');
                CREATE INDEX IF NOT EXISTS narrative_provider_calls_time ON narrative_provider_calls(started_at DESC);
            ''')
            conn.execute("INSERT OR IGNORE INTO narrative_provider_config VALUES (1,1,?,'bootstrap',?)",
                         (json.dumps(DEFAULTS), time.time()))

    def config(self):
        with db_connect(self.db_path) as conn:
            row = conn.execute("SELECT * FROM narrative_provider_config WHERE id=1").fetchone()
            return {**json.loads(row['payload']), 'revision': row['revision']}

    def save(self, values, actor):
        if not isinstance(values, dict) or set(values) != set(DEFAULTS) | {'revision'}:
            raise ProviderConfigError('invalid_config_fields')
        if values['primary'] not in {'ollama', 'mistral'}:
            raise ProviderConfigError('invalid_provider')
        model = values['model']
        if not isinstance(model, str) or len(model) > 160 or any(c.isspace() for c in model):
            raise ProviderConfigError('invalid_model')
        if values['primary'] == 'mistral' and not model:
            raise ProviderConfigError('model_required')
        for key, lo, hi in [('revision',1,2**31), ('remote_seconds',5,30), ('total_seconds',250,660),
                            ('max_tokens',64,1024), ('daily_token_budget',0,10**9)]:
            if type(values[key]) is not int or not lo <= values[key] <= hi:
                raise ProviderConfigError('invalid_' + key)
        if values['total_seconds'] < values['remote_seconds'] + 245:
            raise ProviderConfigError('fallback_time_required')
        payload = json.dumps({key: values[key] for key in DEFAULTS}, sort_keys=True)
        with db_connect(self.db_path) as conn:
            cursor = conn.execute("UPDATE narrative_provider_config SET revision=revision+1,payload=?,updated_by=?,updated_at=? WHERE id=1 AND revision=?",
                                  (payload, actor, time.time(), values['revision']))
            if cursor.rowcount != 1:
                raise ProviderRevisionConflict('revision_conflict')
            conn.execute("INSERT INTO narrative_provider_config_audit VALUES (?,?,?,?)",
                         (values['revision']+1, payload, actor, time.time()))
        return self.config()

    @contextmanager
    def slot(self, key, seconds):
        token = uuid.uuid4().hex
        now = time.time()
        with db_connect(self.db_path) as conn:
            cursor = conn.execute('''INSERT INTO narrative_provider_state(key,until_at,owner) VALUES (?,?,?)
                ON CONFLICT(key) DO UPDATE SET until_at=excluded.until_at,owner=excluded.owner
                WHERE narrative_provider_state.until_at <= ?''', (key,now+seconds+5,token,now))
            acquired = cursor.rowcount == 1
        try:
            yield acquired
        finally:
            if acquired:
                with db_connect(self.db_path) as conn:
                    conn.execute("DELETE FROM narrative_provider_state WHERE key=? AND owner=?", (key,token))

    def circuit(self, key):
        with db_connect(self.db_path) as conn:
            row = conn.execute("SELECT until_at,code FROM narrative_provider_state WHERE key=?", (key,)).fetchone()
        return dict(row) if row else {'until_at': 0, 'code': ''}

    def circuit_result(self, key, error=None):
        now = time.time()
        # Auth/billing faults require explicit probe or a new configuration.
        delay = 365 * 86400 if error and (error.http_status in {401,402,403} or error.code in {'mistral_secret_missing','mistral_quota_exhausted'}) else 60
        if error and error.retry_after is not None:
            delay = max(delay, min(float(error.retry_after), 86400))
        with db_connect(self.db_path) as conn:
            if error:
                conn.execute("INSERT OR REPLACE INTO narrative_provider_state(key,until_at,code) VALUES (?,?,?)",
                             (key, now+delay, error.code))
            else:
                conn.execute("DELETE FROM narrative_provider_state WHERE key=?", (key,))

    def reserve_tokens(self, amount, limit):
        if not limit:
            return True
        day = time.strftime('%Y-%m-%d', time.gmtime())
        with db_connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO narrative_provider_budget VALUES (?,0)", (day,))
            return conn.execute("UPDATE narrative_provider_budget SET reserved=reserved+? WHERE day=? AND reserved+?<=?",
                                (amount,day,amount,limit)).rowcount == 1

    def start_call(self, config, provider, task_id, attempt_id, package=None):
        call_id = uuid.uuid4().hex
        package = package or {}
        policy = package.get('policy')
        metadata = {'request_hash':package.get('request_hash',''),
                    'prompt_version':getattr(policy,'prompt_version',''),
                    'schema_version':getattr(policy,'output_schema_version',''),
                    'locale':package.get('model_input',{}).get('locale','')}
        with db_connect(self.db_path) as conn:
            conn.execute('''INSERT INTO narrative_provider_calls(id,task_id,attempt_id,revision,provider,model,started_at,status,metadata)
                            VALUES (?,?,?,?,?,?,?,'started',?)''',
                         (call_id,task_id,attempt_id,config['revision'],provider,
                          config['model'] if provider == 'mistral' else 'llama3.1:8b',time.time(),json.dumps(metadata)))
        return call_id

    def finish_call(self, call_id, duration, result=None, error=None):
        metadata = {} if result is None else {k: getattr(result,k) for k in (
            'model','requested_model','request_id','raw_response_hash','prompt_eval_count','eval_count')}
        with db_connect(self.db_path) as conn:
            conn.execute("UPDATE narrative_provider_calls SET status=?,duration_ms=?,error_code=?,http_status=?,metadata=json_patch(metadata,?) WHERE id=?",
                         ('failed' if error else 'completed', int(duration*1000), error.code if error else '',
                          error.http_status if error else 0, json.dumps(metadata),call_id))

    def recent(self):
        with db_connect(self.db_path) as conn:
            return [dict(row) for row in conn.execute("SELECT * FROM narrative_provider_calls ORDER BY started_at DESC LIMIT 30")]
