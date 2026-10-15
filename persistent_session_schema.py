"""Additive session TTL schema, shared by runtime and offline migration."""
COLUMNS = {
    'authenticated_at': 'TEXT', 'last_activity_at': 'TEXT',
    'idle_expires_at': 'TEXT', 'absolute_expires_at': 'TEXT',
    'persistence_policy_version': 'INTEGER NOT NULL DEFAULT 0',
}


def ensure_persistence_schema(conn):
    existing = {row[1] for row in conn.execute('PRAGMA table_info(session_generation_lineages)')}
    if not existing:
        raise ValueError('session_lineage_table_missing')
    added = []
    for name, definition in COLUMNS.items():
        if name not in existing:
            conn.execute(f'ALTER TABLE session_generation_lineages ADD COLUMN {name} {definition}')
            added.append(name)
    return added
