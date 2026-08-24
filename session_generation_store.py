"""Durable browser-session lineage guard for authenticated gameplay requests.

Only one-way SHA-256 digests are persisted. Raw lineage and generation secrets
remain in the Flask server-side session and are never written to this table.
"""

import hashlib
from contextlib import contextmanager

from database import DB_PATH, db_connect, utc_now


SESSION_LINEAGE_SCHEMA_VERSION = 2

SESSION_ACTIVE = "active"
SESSION_REPLACED = "replaced"
SESSION_LOGGED_OUT = "logged_out"
SESSION_EXPIRED = "expired"
SESSION_TERMINAL_STATES = {
    SESSION_REPLACED,
    SESSION_LOGGED_OUT,
    SESSION_EXPIRED,
}


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


def login_identity_digest(value):
    return _secret_digest("login_identity", value)


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
            columns = {
                str(row[1])
                for row in conn.execute(
                    "PRAGMA table_info(session_generation_lineages)"
                ).fetchall()
            }
            if "login_id_hash" not in columns:
                conn.execute(
                    "ALTER TABLE session_generation_lineages "
                    "ADD COLUMN login_id_hash TEXT NOT NULL DEFAULT ''"
                )
            if "account_revision" not in columns:
                conn.execute(
                    "ALTER TABLE session_generation_lineages "
                    "ADD COLUMN account_revision INTEGER NOT NULL DEFAULT 0"
                )
            if "lifecycle_status" not in columns:
                conn.execute(
                    "ALTER TABLE session_generation_lineages "
                    "ADD COLUMN lifecycle_status TEXT NOT NULL DEFAULT 'expired'"
                )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS account_login_ownership (
                    username_hash TEXT PRIMARY KEY,
                    active_login_id_hash TEXT NOT NULL DEFAULT '',
                    active_revision INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL CHECK(
                        status IN ('active', 'logged_out', 'expired')
                    ),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
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
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_generation_account_state
                ON session_generation_lineages(
                    username_hash, lifecycle_status, account_revision
                )
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

    def activate(
        self,
        lineage_secret,
        generation_secret,
        username,
        *,
        reason,
        login_identity_secret=None,
        conn=None,
    ):
        lineage_hash = lineage_digest(lineage_secret)
        generation_hash = generation_digest(generation_secret)
        login_id_hash = login_identity_digest(
            login_identity_secret or generation_secret
        )
        user_hash = username_digest(username)
        if not lineage_hash or not generation_hash or not login_id_hash or not user_hash:
            raise ValueError(
                "lineage, generation, login identity and username are required"
            )
        now = utc_now()
        with self._writer(conn) as active_conn:
            ownership = active_conn.execute(
                """
                SELECT active_login_id_hash, active_revision, status
                FROM account_login_ownership
                WHERE username_hash = ?
                """,
                (user_hash,),
            ).fetchone()
            account_revision = (
                int(self._row_value(ownership, "active_revision", 1) or 0) + 1
                if ownership is not None
                else 1
            )

            # A browser lineage may switch accounts. Close its ownership of the
            # previous account only when it still owns that account revision.
            previous = active_conn.execute(
                """
                SELECT username_hash, login_id_hash, account_revision,
                       lifecycle_status
                FROM session_generation_lineages
                WHERE lineage_hash = ?
                """,
                (lineage_hash,),
            ).fetchone()
            if previous is not None:
                previous_user_hash = str(
                    self._row_value(previous, "username_hash", 0) or ""
                )
                previous_login_hash = str(
                    self._row_value(previous, "login_id_hash", 1) or ""
                )
                previous_account_revision = int(
                    self._row_value(previous, "account_revision", 2) or 0
                )
                if previous_user_hash and previous_user_hash != user_hash:
                    active_conn.execute(
                        """
                        UPDATE account_login_ownership
                        SET active_login_id_hash = '', status = 'logged_out',
                            updated_at = ?, last_reason = ?
                        WHERE username_hash = ?
                          AND active_login_id_hash = ?
                          AND active_revision = ?
                          AND status = 'active'
                        """,
                        (
                            now,
                            "account_switch",
                            previous_user_hash,
                            previous_login_hash,
                            previous_account_revision,
                        ),
                    )

            active_conn.execute(
                """
                UPDATE session_generation_lineages
                SET status = 'revoked', lifecycle_status = 'replaced',
                    revision = revision + 1, updated_at = ?,
                    invalidated_at = ?, last_reason = ?
                WHERE username_hash = ? AND lifecycle_status = 'active'
                  AND lineage_hash <> ?
                """,
                (now, now, "new_login_replaced", user_hash, lineage_hash),
            )
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
                        invalidated_at, last_reason, login_id_hash,
                        account_revision, lifecycle_status
                    ) VALUES (?, ?, ?, 'active', ?, ?, ?, ?, NULL, ?, ?, ?, 'active')
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
                        login_id_hash,
                        account_revision,
                    ),
                )
            else:
                revision = int(self._row_value(row, "revision", 0) or 0) + 1
                active_conn.execute(
                    """
                    UPDATE session_generation_lineages
                    SET generation_hash = ?, username_hash = ?, status = 'active',
                        revision = ?, schema_version = ?, updated_at = ?,
                        invalidated_at = NULL, last_reason = ?, login_id_hash = ?,
                        account_revision = ?, lifecycle_status = 'active'
                    WHERE lineage_hash = ?
                    """,
                    (
                        generation_hash,
                        user_hash,
                        revision,
                        SESSION_LINEAGE_SCHEMA_VERSION,
                        now,
                        str(reason or "authenticated"),
                        login_id_hash,
                        account_revision,
                        lineage_hash,
                    ),
                )
            if ownership is None:
                active_conn.execute(
                    """
                    INSERT INTO account_login_ownership (
                        username_hash, active_login_id_hash, active_revision,
                        status, created_at, updated_at, last_reason
                    ) VALUES (?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        user_hash,
                        login_id_hash,
                        account_revision,
                        now,
                        now,
                        str(reason or "authenticated"),
                    ),
                )
            else:
                active_conn.execute(
                    """
                    UPDATE account_login_ownership
                    SET active_login_id_hash = ?, active_revision = ?,
                        status = 'active', updated_at = ?, last_reason = ?
                    WHERE username_hash = ?
                    """,
                    (
                        login_id_hash,
                        account_revision,
                        now,
                        str(reason or "authenticated"),
                        user_hash,
                    ),
                )
        return {
            "active": True,
            "revision": revision,
            "account_revision": account_revision,
            "lineage_hash": lineage_hash,
            "generation_hash": generation_hash,
            "login_id_hash": login_id_hash,
            "username_hash": user_hash,
        }

    def revoke(
        self,
        lineage_secret,
        generation_secret,
        *,
        reason,
        login_identity_secret=None,
        account_revision=None,
        conn=None,
    ):
        lineage_hash = lineage_digest(lineage_secret)
        generation_hash = generation_digest(generation_secret)
        if not lineage_hash or not generation_hash:
            return False
        now = utc_now()
        reason_text = str(reason or "logout")
        lifecycle_status = (
            SESSION_EXPIRED
            if "expir" in reason_text.lower() or "timeout" in reason_text.lower()
            else SESSION_LOGGED_OUT
        )
        with self._writer(conn) as active_conn:
            row = active_conn.execute(
                """
                SELECT username_hash, login_id_hash, account_revision
                FROM session_generation_lineages
                WHERE lineage_hash = ? AND generation_hash = ?
                  AND lifecycle_status = 'active'
                """,
                (lineage_hash, generation_hash),
            ).fetchone()
            if row is None:
                return False
            user_hash = str(self._row_value(row, "username_hash", 0) or "")
            stored_login_hash = str(
                self._row_value(row, "login_id_hash", 1) or ""
            )
            stored_account_revision = int(
                self._row_value(row, "account_revision", 2) or 0
            )
            if login_identity_secret and stored_login_hash != login_identity_digest(
                login_identity_secret
            ):
                return False
            if account_revision is not None and stored_account_revision != int(
                account_revision
            ):
                return False
            result = active_conn.execute(
                """
                UPDATE session_generation_lineages
                SET status = 'revoked', lifecycle_status = ?,
                    revision = revision + 1,
                    updated_at = ?, invalidated_at = ?, last_reason = ?
                WHERE lineage_hash = ? AND generation_hash = ?
                  AND lifecycle_status = 'active'
                """,
                (
                    lifecycle_status,
                    now,
                    now,
                    reason_text,
                    lineage_hash,
                    generation_hash,
                ),
            )
            if result.rowcount == 1:
                active_conn.execute(
                    """
                    UPDATE account_login_ownership
                    SET active_login_id_hash = '', status = ?, updated_at = ?,
                        last_reason = ?
                    WHERE username_hash = ? AND active_login_id_hash = ?
                      AND active_revision = ? AND status = 'active'
                    """,
                    (
                        lifecycle_status,
                        now,
                        reason_text,
                        user_hash,
                        stored_login_hash,
                        stored_account_revision,
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
                SET status = 'revoked', lifecycle_status = 'logged_out',
                    revision = revision + 1,
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
            active_conn.execute(
                """
                UPDATE account_login_ownership
                SET active_login_id_hash = '', status = 'logged_out',
                    updated_at = ?, last_reason = ?
                WHERE username_hash = ? AND status = 'active'
                """,
                (now, str(reason or "account_invalidated"), user_hash),
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
                       invalidated_at, last_reason, login_id_hash,
                       account_revision, lifecycle_status
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
                "invalidated_at", "last_reason", "login_id_hash",
                "account_revision", "lifecycle_status",
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
        if not state or state.get("lifecycle_status") != SESSION_ACTIVE:
            return False
        if not (
            state.get("generation_hash") == generation_digest(generation_secret)
            and state.get("username_hash") == username_digest(username)
        ):
            return False
        try:
            self.assert_current(
                lineage_secret,
                generation_secret,
                username,
                conn=conn,
            )
        except SessionGenerationStateError:
            return False
        return True

    def assert_current(
        self,
        lineage_secret,
        generation_secret,
        username,
        *,
        login_identity_secret=None,
        account_revision=None,
        conn=None,
    ):
        state = self.get_state(lineage_secret, conn=conn)
        if state is None:
            raise SessionGenerationStateError("lineage_missing")
        lifecycle_status = str(state.get("lifecycle_status") or "expired")
        if lifecycle_status != SESSION_ACTIVE:
            raise SessionGenerationStateError(f"lineage_{lifecycle_status}")
        if state.get("generation_hash") != generation_digest(generation_secret):
            raise SessionGenerationStateError("generation_replaced")
        if state.get("username_hash") != username_digest(username):
            raise SessionGenerationStateError("lineage_user_replaced")
        if login_identity_secret and state.get("login_id_hash") != login_identity_digest(
            login_identity_secret
        ):
            raise SessionGenerationStateError("login_identity_replaced")
        if account_revision is not None and int(
            state.get("account_revision") or 0
        ) != int(account_revision):
            raise SessionGenerationStateError("account_revision_replaced")

        def read_ownership(active_conn):
            return active_conn.execute(
                """
                SELECT active_login_id_hash, active_revision, status
                FROM account_login_ownership
                WHERE username_hash = ?
                """,
                (state.get("username_hash"),),
            ).fetchone()

        if conn is not None:
            ownership = read_ownership(conn)
        else:
            with db_connect(
                self.db_path,
                enforce_request_guard=False,
            ) as active_conn:
                ownership = read_ownership(active_conn)
        if ownership is None:
            raise SessionGenerationStateError("account_ownership_missing")
        active_login_hash = str(
            self._row_value(ownership, "active_login_id_hash", 0) or ""
        )
        active_revision = int(
            self._row_value(ownership, "active_revision", 1) or 0
        )
        ownership_status = str(
            self._row_value(ownership, "status", 2) or "expired"
        )
        if ownership_status != SESSION_ACTIVE:
            raise SessionGenerationStateError(f"account_{ownership_status}")
        if active_login_hash != state.get("login_id_hash"):
            raise SessionGenerationStateError("account_login_replaced")
        if active_revision != int(state.get("account_revision") or 0):
            raise SessionGenerationStateError("account_revision_replaced")
        return True

    def build_precommit_guard(
        self,
        lineage_secret,
        generation_secret,
        actor_username,
        login_identity_secret=None,
        account_revision=None,
    ):
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
                login_identity_secret=login_identity_secret,
                account_revision=account_revision,
                conn=conn,
            )

        return precommit_guard

    def build_transaction_precommit_guard(
        self,
        lineage_secret,
        generation_secret,
        actor_username,
        login_identity_secret=None,
        account_revision=None,
    ):
        expected_actor = str(actor_username or "").strip()

        def precommit_guard(*, conn):
            self.assert_current(
                lineage_secret,
                generation_secret,
                expected_actor,
                login_identity_secret=login_identity_secret,
                account_revision=account_revision,
                conn=conn,
            )

        return precommit_guard
