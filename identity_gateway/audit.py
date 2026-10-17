"""Read-only legacy identity inventory; output contains IDs, never profile text."""
from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import unicodedata


def nick_key(value):
    return unicodedata.normalize('NFKC', value.strip()).casefold()


def email_key(value):
    # Keep the existing CHAOS case-insensitive convention. No dot/plus alias merging.
    return value.strip().lower()


def audit_database(path):
    path = Path(path).resolve(strict=True)
    conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    try:
        conn.execute('PRAGMA query_only=ON')
        conn.execute('BEGIN')
        groups = {name: defaultdict(list) for name in ('nick', 'email')}
        missing = {name: [] for name in groups}
        malformed, empty_password, legacy_password = [], [], []
        count = 0
        for user_id, password, raw in conn.execute('SELECT id, password, profile_json FROM users ORDER BY id'):
            count += 1
            if not password:
                empty_password.append(user_id)
            elif not password.startswith('pbkdf2_sha256$'):
                legacy_password.append(user_id)
            try:
                profile = json.loads(raw)
                if not isinstance(profile, dict):
                    raise ValueError('profile_not_object')
            except (ValueError, TypeError):
                malformed.append(user_id)
                continue
            for name, normalize in (('nick', nick_key), ('email', email_key)):
                value = profile.get(name)
                if not isinstance(value, str) or not value.strip():
                    missing[name].append(user_id)
                else:
                    groups[name][normalize(value)].append(user_id)
        return dict(ok=True, status='read_only', accounts=count,
                    collisions={name: sorted((ids for ids in values.values() if len(ids) > 1), key=lambda ids: ids[0])
                                for name, values in groups.items()},
                    missing=missing, malformed_profile_ids=malformed,
                    empty_password_ids=empty_password, legacy_password_ids=legacy_password,
                    email_verification='not_inferred_from_legacy_profile')
    finally:
        conn.close()
