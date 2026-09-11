"""Bounded operator migration of existing identity rows; default is read-only."""
import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path


def migrate(db_path, *, apply=False, limit=100):
    if not 1 <= limit <= 1000:
        raise ValueError("limit must be between 1 and 1000")
    path = Path(db_path).resolve()
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        columns = {r[1] for r in conn.execute("PRAGMA table_info(user_identity_projection)")}
        if not columns:
            raise ValueError("identity projection schema missing")
        missing = "desktop_boot_json" not in columns
        condition = "1=1" if missing else """CASE WHEN json_valid(p.desktop_boot_json) THEN (
            COALESCE(json_extract(p.desktop_boot_json, '$.source_profile_revision'), 0) != p.source_profile_revision
            OR COALESCE(json_extract(p.desktop_boot_json, '$.source_profile_checksum'), '') != p.source_profile_checksum
        ) ELSE 1 END"""
        count = conn.execute("SELECT COUNT(*) FROM user_identity_projection p WHERE " + condition).fetchone()[0]
        if not apply:
            return {"ok": True, "apply": False, "schema_change": missing, "pending": count, "limit": limit}
        # JSON extraction is migration-only, prepared before acquiring a writer.
        rows = conn.execute("""SELECT p.username, u.profile_revision, u.profile_checksum,
            COALESCE(json_extract(u.profile_json, '$.desktop_settings'), '{}') AS settings,
            COALESCE(json_extract(u.profile_json, '$.respect'), 0) AS respect
            FROM user_identity_projection p JOIN users u ON u.username=p.username
            WHERE """ + condition + """ AND u.profile_integrity_status='valid'
            AND p.source_profile_revision=u.profile_revision
            AND p.source_profile_checksum=u.profile_checksum
            ORDER BY p.username LIMIT ?""", (limit,)).fetchall()
        prepared = []
        for row in rows:
            settings = json.loads(row["settings"])
            if not isinstance(settings, dict):
                raise ValueError("invalid desktop settings")
            prepared.append((json.dumps({"desktop_settings": settings, "respect": row["respect"],
                                         "source_profile_revision": row["profile_revision"],
                                         "source_profile_checksum": row["profile_checksum"]}, ensure_ascii=False), row["username"],
                             row["profile_revision"], row["profile_checksum"]))
    written = 0
    with closing(sqlite3.connect(path.as_uri() + "?mode=rw", uri=True)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        columns = {r[1] for r in conn.execute("PRAGMA table_info(user_identity_projection)")}
        if "desktop_boot_json" not in columns:
            conn.execute("ALTER TABLE user_identity_projection ADD COLUMN desktop_boot_json TEXT")
        for settings, username, revision, checksum in prepared:
            written += conn.execute("""UPDATE user_identity_projection SET desktop_boot_json=?
                WHERE username=? AND source_profile_revision=? AND source_profile_checksum=?
                AND (""" + condition.replace("p.", "user_identity_projection.") + """) AND EXISTS (
                    SELECT 1 FROM users u WHERE u.username=user_identity_projection.username
                    AND u.profile_revision=user_identity_projection.source_profile_revision
                    AND u.profile_checksum=user_identity_projection.source_profile_checksum
                    AND u.profile_integrity_status='valid')""", (settings, username, revision, checksum)).rowcount
        conn.commit()
    return {"ok": True, "apply": True, "prepared": len(prepared), "written": written,
            "pending_before": count, "retry_or_recovery": count - written}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(migrate(args.db, apply=args.apply, limit=args.limit), sort_keys=True))
