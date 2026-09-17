"""Code-owned generation deadlines and queue priority, independent of leases."""
import os
from datetime import datetime, timedelta, timezone


def setting(name, default):
    return max(1, int(os.environ.get('CHAOS_NARRATIVE_' + name, default)))


def instant(value):
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def queue_class(task):
    intent = str(task.get('narrative_intent') or '')
    if 'incident' in intent or 'conflict' in intent:
        return 'URGENT'
    if task.get('source_scope') == 'googleplex_editorial' or 'promo' in intent:
        return 'EDITORIAL'
    return 'NORMAL'


def deadline(task, created_at):
    kind = queue_class(task)
    seconds = setting('TTL_' + kind + '_SECONDS', {'URGENT': 1800, 'NORMAL': 7200, 'EDITORIAL': 21600}[kind])
    end = instant(created_at) + timedelta(seconds=seconds)
    for value in (task.get('expires_at'), (task.get('validation') or {}).get('source_expires_at')):
        if value:
            end = min(end, instant(value))
    return end.isoformat()


def priority(task):
    kind = queue_class(task)
    base = setting('PRIORITY_' + kind, {'URGENT': 300, 'NORMAL': 200, 'EDITORIAL': 100}[kind])
    return base + min(99, max(0, int(task.get('priority') or 0)))
