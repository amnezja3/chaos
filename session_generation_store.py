"""Durable browser-session lineage guard for authenticated gameplay requests.

Only one-way SHA-256 digests are persisted. Raw lineage and generation secrets
remain in the Flask server-side session and are never written to this table.
"""

import hashlib
from contextlib import contextmanager

from database import DB_PATH, db_connect, utc_now


SESSION_LINEAGE_SCHEMA_VERSION = 1


class SessionGenerationStateError(RuntimeError):
    """The browser lineage no longer owns the supplied generation."""

    def __init__(self, reason="stale_generation"):
        super().__init__(reason)
        self.reason = str(reason or "stale_generation")


def _secret_digest(kind, value):
    value = str(value or "").strip()
    if not value:
        return ""
    payload = f"chaos.session.{kind}.v1\0{value}".encode(
        "utf-8", errors="strict"
    )
    return hashlib.sha256(payload).hexdigest()


def lineage_digest(value):
    return _secret_digest("lineage", value)


def generation_digest(value):
    return _secret_digest("generation", value)


def username_digest(value):
    return _secret_digest("username", str(value or "").strip().casefold())


class SessionGenerationStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.ensure_schema()

    def ensure_schema(self):
        with db_connect(self.db_path, enforce_request_guard=False) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_generation_lineages (
                    lineage_hash TEXT PRIMARY KEY,
                    generation_hash TEXT NOT NULL,
                    username_hash TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('active', 'revoked')),
                    revision INTEGER NOT NULL DEFAULT 1,
                    schema_version INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    invalidated_at TEXT,
                    last_reason TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_generation_status_updated
                ON session_generation_lineages(status, updated_at)
                """
            )

    @contextmanager
    def _writer(self, conn=None):
        if conn is not None:
            yield conn
            return
        with db_connect(
            self.db_path,
            enforce_request_guard=False,
        ) as owned_conn:
            owned_conn.execute("BEGIN IMMEDIATE")
            yield owned_conn

    @staticmethod
    def _row_value(row, key, index):
        if row is None:
            return None
        try:
            return row[key]
        except (TypeError, KeyError, IndexError):
            return row[index]

    def activate(self, lineage_secret, generation_secret, username, *, reason, conn=None):
        lineage_hash = lineage_digest(lineage_secret)
        generation_hash = generation_digest(generation_secret)
        user_hash = username_digest(username)
        if not lineage_hash or not generation_hash or not user_hash:
            raise ValueError("lineage, generation and username are required")
        now = utc_now()
        with self._writer(conn) as active_conn:
            row = active_conn.execute(
                """
                SELECT revision
                FROM session_generation_lineages
                WHERE lineage_hash = ?
                """,
                (lineage_hash,),
            ).fetchone()
            if row is None:
                revision = 1
                active_conn.execute(
                    """
                    INSERT INTO session_generation_lineages (
                        lineage_hash, generation_hash, username_hash, status,
                        revision, schema_version, created_at, updated_at,
                        invalidated_at, last_reason
                    ) VALUES (?, ?, ?, 'active', ?, ?, ?, ?, NULL, ?)
                    """,
                    (
                        lineage_hash,
                        generation_hash,
                        user_hash,
                        revision,
                        SESSION_LINEAGE_SCHEMA_VERSION,
                        now,
                        now,
                        str(reason or "authenticated"),
                    ),
                )
            else:
                revision = int(self._row_value(row, "revision", 0) or 0) + 1
                active_conn.execute(
                    """
                    UPDATE session_generation_lineages
                    SET generation_hash = ?, username_hash = ?, status = 'active',
                        revision = ?, schema_version = ?, updated_at = ?,
                        invalidated_at = NULL, last_reason = ?
                    WHERE lineage_hash = ?
                    """,
                    (
                        generation_hash,
                        user_hash,
                        revision,
                        SESSION_LINEAGE_SCHEMA_VERSION,
                        now,
                        str(reason or "authenticated"),
                        lineage_hash,
                    ),
                )
        return {
            "active": True,
            "revision": revision,
            "lineage_hash": lineage_hash,
            "generation_hash": generation_hash,
            "username_hash": user_hash,
        }

    def revoke(self, lineage_secret, generation_secret, *, reason, conn=None):
        lineage_hash = lineage_digest(lineage_secret)
        generation_hash = generation_digest(generation_secret)
        if not lineage_hash or not generation_hash:
            return False
        now = utc_now()
        with self._writer(conn) as active_conn:
            result = active_conn.execute(
                """
                UPDATE session_generation_lineages
                SET status = 'revoked', revision = revision + 1,
                    updated_at = ?, invalidated_at = ?, last_reason = ?
                WHERE lineage_hash = ? AND generation_hash = ? AND status = 'active'
                """,
                (
                    now,
                    now,
                    str(reason or "invalidated"),
                    lineage_hash,
                    generation_hash,
                ),
            )
        return result.rowcount == 1

    def revoke_all_by_username(self, username, *, reason, conn=None):
        """Revoke every browser lineage belonging to an account identity."""
        user_hash = username_digest(username)
        if not user_hash:
            return 0
        now = utc_now()
        with self._writer(conn) as active_conn:
            result = active_conn.execute(
                """
                UPDATE session_generation_lineages
                SET status = 'revoked', revision = revision + 1,
                    updated_at = ?, invalidated_at = ?, last_reason = ?
                WHERE username_hash = ? AND status = 'active'
                """,
                (
                    now,
                    now,
                    str(reason or "account_invalidated"),
                    user_hash,
                ),
            )
        return int(result.rowcount or 0)

    def get_state(self, lineage_secret, *, conn=None):
        lineage_hash = lineage_digest(lineage_secret)
        if not lineage_hash:
            return None

        def read(active_conn):
            row = active_conn.execute(
                """
                SELECT lineage_hash, generation_hash, username_hash, status,
                       revision, schema_version, created_at, updated_at,
                       invalidated_at, last_reason
                FROM session_generation_lineages
                WHERE lineage_hash = ?
                """,
                (lineage_hash,),
            ).fetchone()
            if row is None:
                return None
            keys = (
                "lineage_hash", "generation_hash", "username_hash", "status",
                "revision", "schema_version", "created_at", "updated_at",
                "invalidated_at", "last_reason",
            )
            return {
                key: self._row_value(row, key, index)
                for index, key in enumerate(keys)
            }

        if conn is not None:
            return read(conn)
        with db_connect(
            self.db_path,
            enforce_request_guard=False,
        ) as active_conn:
            return read(active_conn)

    def is_current(self, lineage_secret, generation_secret, username, *, conn=None):
        state = self.get_state(lineage_secret, conn=conn)
        if not state or state.get("status") != "active":
            return False
        return (
            state.get("generation_hash") == generation_digest(generation_secret)
            and state.get("username_hash") == username_digest(username)
        )

    def assert_current(self, lineage_secret, generation_secret, username, *, conn=None):
        state = self.get_state(lineage_secret, conn=conn)
        if state is None:
            raise SessionGenerationStateError("lineage_missing")
        if state.get("status") != "active":
            raise SessionGenerationStateError("lineage_revoked")
        if state.get("generation_hash") != generation_digest(generation_secret):
            raise SessionGenerationStateError("generation_replaced")
        if state.get("username_hash") != username_digest(username):
            raise SessionGenerationStateError("lineage_user_replaced")
        return True

    def build_precommit_guard(self, lineage_secret, generation_secret, actor_username):
        expected_actor = str(actor_username or "").strip()

        def precommit_guard(*, conn, username, current_revision):
            # A legitimate actor request can update another profile (victim,
            # payee, reward recipient). Generation ownership belongs to the
            # request actor, not to the profile row being written.
            del username, current_revision
            self.assert_current(
                lineage_secret,
                generation_secret,
                expected_actor,
                conn=conn,
            )

        return precommit_guard

    def build_transaction_precommit_guard(
        self,
        lineage_secret,
        generation_secret,
        actor_username,
    ):
        expected_actor = str(actor_username or "").strip()

        def precommit_guard(*, conn):
            self.assert_current(
                lineage_secret,
                generation_secret,
                expected_actor,
                conn=conn,
            )

        return precommit_guard
