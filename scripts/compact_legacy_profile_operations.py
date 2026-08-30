import argparse
import os
import sqlite3
import sys
from datetime import datetime, timezone


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import DB_PATH, UserStore


TERMINAL_STATUSES = {
    "cancelled", "canceled", "done", "completed", "failed",
    "expired", "timeout", "resolved",
}


def canonical_counts(username):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            """
            SELECT COUNT(*),
                   SUM(CASE WHEN status IN (?, ?, ?, ?, ?, ?, ?, ?) THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status NOT IN (?, ?, ?, ?, ?, ?, ?, ?) THEN 1 ELSE 0 END)
            FROM player_operations
            WHERE username = ?
            """,
            (*sorted(TERMINAL_STATUSES), *sorted(TERMINAL_STATUSES), username),
        ).fetchone()
    return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)


def compact(store, username, apply=False):
    record = store.get_profile_with_revision(username)
    if not record or record.get("state") != "valid":
        raise RuntimeError(f"profile unavailable or invalid: {username}")
    profile = record["profile"]
    legacy = profile.get("operations")
    legacy_count = len(legacy) if isinstance(legacy, list) else 0
    canonical, terminal, active = canonical_counts(username)
    if canonical < legacy_count:
        raise RuntimeError(
            f"canonical operation loss guard: user={username} "
            f"canonical={canonical} legacy={legacy_count}"
        )
    before_bytes = len(str(legacy or []).encode("utf-8", errors="ignore"))
    result = {
        "username": username,
        "legacy": legacy_count,
        "canonical": canonical,
        "terminal": terminal,
        "active": active,
        "legacy_bytes": before_bytes,
        "applied": False,
    }
    if not apply or legacy_count == 0:
        return result
    profile["operations"] = []
    now = datetime.now(timezone.utc).isoformat()
    store.save_profile_guarded(
        profile,
        expected_revision=int(record["profile_revision"]),
        source="admin.compact_legacy_profile_operations",
        reset_receipt={
            "receipt_id": f"compact-legacy-operations:{username}:{now}",
            "reason": "canonical_player_operations_verified",
            "authorized_by": "server_operator",
            "created_at": now,
        },
    )
    result["applied"] = True
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("usernames", nargs="+")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    store = UserStore()
    for username in args.usernames:
        print(compact(store, username, apply=args.apply), flush=True)


if __name__ == "__main__":
    main()
