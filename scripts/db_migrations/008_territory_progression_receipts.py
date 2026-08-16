MIGRATION_ID = "008"
NAME = "Territory progression receipts"


def _table_exists(conn):
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='territory_progression_receipts'"
    ).fetchone() is not None


def migrate(conn, apply=False):
    existed = _table_exists(conn)
    if apply:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_progression_receipts (
                receipt_id TEXT PRIMARY KEY,
                source_event_id TEXT NOT NULL UNIQUE,
                actor_username TEXT NOT NULL,
                target_id TEXT NOT NULL DEFAULT '',
                conflict_ids_json TEXT NOT NULL DEFAULT '[]',
                baseline_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'pending',
                result_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                applied_at TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_territory_progression_pending "
            "ON territory_progression_receipts(actor_username, status, created_at)"
        )
    return {
        "table_exists_before": bool(existed),
        "will_create": not existed,
        "historical_backfill": False,
        "write_mode": bool(apply),
    }
