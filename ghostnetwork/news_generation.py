"""Asynchronous News variants over the existing provider router.

Never used by a feed/read endpoint. Original publications and gameplay receipts
are immutable here. Failed generation leaves the localized system fallback.
"""
import hashlib
import json
import re
import time
import uuid

from database import db_connect
from ghost_i18n import approved_locales
from .news_locales import NewsLocaleStore, source_version
from .ollama_policy import build_ollama_task_package, parse_and_validate_ollama_content
from .llm.registry import ROOT, _read_versioned_prompt
from .llm.provider import NarrativeProviderError
from .narrative_locale import language_registry

SUPPORTED_POLICIES = frozenset({
    'googleplex-world-hero-prompt-v14', 'ghostnetwork-googleplex-prompt-v11',
    'googleplex-navigation-promo-v1', 'googleplex-capability-card-v1',
})


def initialize(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS ghost_news_locale_jobs (
        job_id TEXT PRIMARY KEY, medium_record_id TEXT NOT NULL,
        source_version TEXT NOT NULL, locale TEXT NOT NULL, prompt_version TEXT NOT NULL,
        state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
        next_at REAL NOT NULL DEFAULT 0, lease_owner TEXT NOT NULL DEFAULT '',
        lease_until REAL NOT NULL DEFAULT 0, error_code TEXT NOT NULL DEFAULT '')''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_news_locale_ready ON ghost_news_locale_jobs(state,next_at)')


def news_languages():
    return {locale: config['news'] for locale, config in language_registry().items()
            if locale != 'pl' and locale in approved_locales('narration')
            and isinstance(config, dict) and 'news' in config}


def build_package(task, record, locale='en'):
    config = news_languages().get(locale)
    if not config:
        raise ValueError('unapproved_news_generation_locale')
    if record.get('target_medium') != 'googleplex_news' or record.get('content_kind') == 'product_promo':
        raise ValueError('news_generation_source_excluded')
    package = build_ollama_task_package(task)
    policy = package['policy']
    if policy.target_medium != 'googleplex_news' or policy.prompt_version not in SUPPORTED_POLICIES:
        raise ValueError('news_generation_policy_not_registered')
    expected_refs = set(record.get('fact_refs') or ())
    if not expected_refs or not expected_refs <= package['canonical_fact_refs']:
        raise ValueError('news_generation_facts_changed')
    system = _read_versioned_prompt(ROOT / config['system_prompt'], config['prompt_version'])
    domain = _read_versioned_prompt(ROOT / config['domain_prompt'], config['prompt_version'])
    # Replace BOTH prompt layers. Appending an English request to a Polish-only
    # domain instruction would create contradictory commands.
    package['messages'][0] = {'role':'system', 'content':system + '\n\n' + domain}
    package['output_locale'] = locale
    package['model_input']['output_locale'] = locale
    package['messages'][1]['content'] = json.dumps(package['model_input'], ensure_ascii=False, separators=(',', ':'))
    contract = dict(event_id=record.get('source_event_id'), medium='googleplex_news',
        language_policy='reader_locale', output_locale=locale, prompt_version=config['prompt_version'],
        content_version=source_version(record), facts_version=task.get('world_state_version') or '',
        original_fact_refs=sorted(alias for alias, canonical in package['fact_ref_map'].items()
                                  if canonical in expected_refs))
    package['messages'].append({'role':'user','content':json.dumps({'language_contract':contract}, sort_keys=True)})
    package['request_hash'] = hashlib.sha256(json.dumps(package['messages'], sort_keys=True).encode()).hexdigest()
    package['input_bytes'] = sum(len(m['content'].encode()) for m in package['messages'])
    package['estimated_input_tokens'] = (package['input_bytes'] + 2) // 3
    package['news_language_contract'] = contract
    package['language_contract'] = contract
    # No old Polish backend title may override English model output. Product
    # titles are intentionally excluded above, so these are system labels only.
    if package.get('editorial_contract', {}).get('title_owner') == 'backend':
        package['editorial_contract'] = {**package['editorial_contract'], 'canonical_title':''}
    return package


def validate_variant(content, package, record):
    checked = parse_and_validate_ollama_content(content, package)
    if checked['status'] != 'accepted':
        return checked
    output = checked['output']
    errors = []
    if set(output['fact_refs']) != set(record.get('fact_refs') or ()):
        errors.append('news_variant_fact_refs_changed')
    # This is a conservative language rejection filter, not a semantic review.
    # Live PL/EN sample review is a release gate documented in the runbook.
    config = news_languages()[package['output_locale']]
    words = set(re.findall(r"[^\W\d_]+", output['body'].casefold()))
    expected = words & set(config['language_words'])
    rejected = words & set(config['rejected_words'])
    if len(expected) < config['minimum_language_words'] or len(rejected) > config['maximum_rejected_words']:
        errors.append('news_variant_language_uncertain')
    # Numbers may be reformatted, but a new numeric fact must never appear.
    source = json.dumps(package.get('source_facts') or (), ensure_ascii=False)
    existing = set(re.findall(r'\d+', source))
    if not set(re.findall(r'\d+', output['title'] + ' ' + output['body'])) <= existing:
        errors.append('news_variant_number_added')
    if errors:
        return {'status':'rejected', 'errors':errors, 'output':None}
    return checked


class NewsLocaleWorker:
    def __init__(self, repository, router):
        self.repository = repository
        self.router = router
        self.store = NewsLocaleStore(repository.db_path)

    def enqueue_active(self, limit=50):
        """Only current slot records; bounded and independent of reader locale."""
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError('invalid_news_queue_limit')
        inserted = 0
        with db_connect(self.repository.db_path) as conn:
            # No player content or retired publication backlog is auto-enqueued.
            rows = conn.execute('''SELECT m.* FROM ghost_narrative_medium_records m
                JOIN ghost_narrative_slot_state s ON s.active_medium_record_id=m.medium_record_id
                WHERE m.target_medium='googleplex_news' AND m.active_state='active'
                AND (m.valid_from='' OR m.valid_from<=?)
                AND (m.valid_until='' OR m.valid_until>?)
                AND m.content_kind!='product_promo' ORDER BY m.medium_record_id LIMIT ?''',
                (self.repository.now(), self.repository.now(), limit)).fetchall()
            for row in rows:
                record = self.repository._narrative_medium_record(row)
                task = conn.execute('SELECT prompt_version FROM ghost_narrative_outbox WHERE outbox_id=?', (record['task_id'],)).fetchone()
                if not task or task['prompt_version'] not in SUPPORTED_POLICIES:
                    continue
                version = source_version(record)
                for locale, config in news_languages().items():
                    if conn.execute('SELECT 1 FROM ghost_news_locale_variants WHERE medium_record_id=? AND source_version=? AND locale=?',
                                    (record['medium_record_id'], version, locale)).fetchone():
                        continue
                    prompt_version = config['prompt_version']
                    job = hashlib.sha256(json.dumps([record['medium_record_id'],version,locale,prompt_version]).encode()).hexdigest()
                    inserted += conn.execute('''INSERT OR IGNORE INTO ghost_news_locale_jobs
                        (job_id,medium_record_id,source_version,locale,prompt_version,state)
                        VALUES (?,?,?,?,?,'ready')''', (job,record['medium_record_id'],version,locale,prompt_version)).rowcount
        return inserted

    def _current(self, conn, job):
        row = conn.execute('''SELECT m.* FROM ghost_narrative_medium_records m
            JOIN ghost_narrative_slot_state s ON s.active_medium_record_id=m.medium_record_id
            WHERE m.medium_record_id=? AND m.active_state='active'
            AND (m.valid_from='' OR m.valid_from<=?)
            AND (m.valid_until='' OR m.valid_until>?) ''',
            (job['medium_record_id'], self.repository.now(), self.repository.now())).fetchone()
        record = self.repository._narrative_medium_record(row) if row else None
        if record and source_version(record) == job['source_version']:
            return record
        return None

    def process_once(self):
        owner = uuid.uuid4().hex
        now = time.time()
        with db_connect(self.repository.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('''SELECT * FROM ghost_news_locale_jobs WHERE
                (state='ready' AND next_at<=?) OR (state='running' AND lease_until<=?)
                ORDER BY next_at,job_id LIMIT 1''', (now,now)).fetchone()
            if not row:
                return {'result':'idle'}
            job = dict(row)
            if job['attempts'] >= 3:
                conn.execute("UPDATE ghost_news_locale_jobs SET state='rejected',error_code='attempt_limit' WHERE job_id=?", (job['job_id'],))
                return {'result':'news_variant_rejected'}
            record = self._current(conn, job)
            if not record:
                conn.execute("UPDATE ghost_news_locale_jobs SET state='stale' WHERE job_id=?", (job['job_id'],))
                return {'result':'news_variant_stale'}
            conn.execute("UPDATE ghost_news_locale_jobs SET state='running',attempts=attempts+1,lease_owner=?,lease_until=? WHERE job_id=?",
                (owner, now + float(self.router.config['total_seconds']) + 60, job['job_id']))

        def guard():
            with db_connect(self.repository.db_path) as conn:
                lease = conn.execute("SELECT 1 FROM ghost_news_locale_jobs WHERE job_id=? AND state='running' AND lease_owner=? AND lease_until>?",
                                     (job['job_id'], owner, time.time())).fetchone()
                return bool(lease and self._current(conn, job))

        try:
            task = self.repository.get_narrative_outbox(record['task_id'])
            if not task:
                raise ValueError('news_source_task_missing')
            package = build_package(task, record, job['locale'])
            if package['news_language_contract']['prompt_version'] != job['prompt_version']:
                raise ValueError('news_prompt_version_changed')
            result = self.router.generate(package, package['policy'], guard=guard,
                task_id='news-locale:' + job['job_id'], attempt_id=owner)
            checked = validate_variant(result.content, package, record)
            if checked['status'] != 'accepted':
                raise ValueError('news_variant_validation_failed')
            with db_connect(self.repository.db_path) as conn:
                conn.execute('BEGIN IMMEDIATE')
                lease = conn.execute("SELECT 1 FROM ghost_news_locale_jobs WHERE job_id=? AND state='running' AND lease_owner=? AND lease_until>?",
                                     (job['job_id'], owner, time.time())).fetchone()
                if not lease or not self._current(conn, job):
                    raise ValueError('stale_news_source')
                output = checked['output']
                self.store._save(conn, record['medium_record_id'], job['source_version'], job['locale'],
                    output['title'], output['body'], 'validator:' + job['prompt_version'])
                conn.execute("UPDATE ghost_news_locale_jobs SET state='done',error_code='',lease_until=0 WHERE job_id=? AND lease_owner=?",
                             (job['job_id'],owner))
            return {'result':'news_variant_completed','locale':job['locale']}
        except (ValueError, NarrativeProviderError) as exc:
            code = exc.code if isinstance(exc, NarrativeProviderError) else str(exc)
            # Persist only bounded error codes, not provider responses or source text.
            code = code if re.fullmatch(r'[a-z0-9_]{1,80}', code) else 'news_variant_failed'
            state = 'stale' if code in {'stale_news_source','generation_cancelled','news_prompt_version_changed'} else (
                'rejected' if job['attempts'] + 1 >= 3 else 'ready')
            with db_connect(self.repository.db_path) as conn:
                conn.execute('''UPDATE ghost_news_locale_jobs SET state=?,error_code=?,next_at=?,lease_until=0
                    WHERE job_id=? AND lease_owner=?''', (state,code,time.time()+300,job['job_id'],owner))
            return {'result':'news_variant_' + state, 'error_code':code}
