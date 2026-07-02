MIGRATION_ID = "001"
NAME = "schema_migrations table"


def migrate(conn, apply=False):
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
    ).fetchone()
    if apply:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                script_hash TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'applied',
                notes TEXT NOT NULL DEFAULT ''
            )
            """
        )
    return {"table_exists_before": bool(exists), "will_create": not bool(exists)}
