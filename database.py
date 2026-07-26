import copy
import hashlib
import hmac
from itertools import combinations
import json
import math
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timedelta


DB_PATH = os.path.join("data", "game.sqlite3")
USERS_SEED_PATH = os.path.join("static", "users.json")
_WAL_CONFIGURED = False


def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds")


def dumps_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def loads_json(value, default=None):
    if value is None:
        return copy.deepcopy(default)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return copy.deepcopy(default)


def merge_launch_queue_values(latest_queue, incoming_queue):
    merged = []
    seen = set()
    for item in list(latest_queue or []) + list(incoming_queue or []):
        if isinstance(item, dict):
            value = str(
                item.get("receipt")
                or item.get("launch_receipt")
                or item.get("launch_key")
                or item.get("name")
                or item.get("app_name")
                or ""
            ).strip()
        else:
            value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        merged.append(item)
    return merged


PASSWORD_HASH_PREFIX = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 240000


def is_password_hash(value):
    return isinstance(value, str) and value.startswith(f"{PASSWORD_HASH_PREFIX}$")


def hash_password(password, salt=None):
    password = str(password or "")
    salt = str(salt or secrets.token_hex(16))
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt}${digest}", salt


def verify_password(password, stored_password):
    if not is_password_hash(stored_password):
        return hmac.compare_digest(str(stored_password or ""), str(password or ""))

    try:
        prefix, iterations, salt, stored_digest = str(stored_password).split("$", 3)
        if prefix != PASSWORD_HASH_PREFIX:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            str(password or "").encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return hmac.compare_digest(digest, stored_digest)
    except (TypeError, ValueError):
        return False


def ensure_password_hash(profile):
    if not isinstance(profile, dict):
        return profile
    password = str(profile.get("password") or "")
    if not password or is_password_hash(password):
        return profile
    hashed_password, salt = hash_password(password)
    profile["password"] = hashed_password
    profile["salt"] = salt
    return profile


@contextmanager
def db_connect(db_path=DB_PATH):
    global _WAL_CONFIGURED
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.execute("PRAGMA synchronous = NORMAL")
    if not _WAL_CONFIGURED:
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            _WAL_CONFIGURED = True
        except sqlite3.OperationalError:
            pass
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path=DB_PATH):
    with db_connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL DEFAULT '',
                salt TEXT NOT NULL DEFAULT '',
                profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS json_resources (
                key TEXT PRIMARY KEY,
                source_path TEXT NOT NULL DEFAULT '',
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                contact_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'offline',
                created_at TEXT NOT NULL,
                UNIQUE(owner_username, contact_name)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                scope TEXT NOT NULL,
                peer_name TEXT NOT NULL DEFAULT '',
                sender TEXT NOT NULL,
                subject TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(chat_messages)").fetchall()
        }
        if "read_at" not in columns:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN read_at TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mail_presence (
                username TEXT PRIMARY KEY,
                last_seen_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_username TEXT NOT NULL,
                to_username TEXT NOT NULL,
                amount INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_hack_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                attacker_username TEXT NOT NULL,
                victim_username TEXT NOT NULL,
                hacked_until TEXT NOT NULL,
                cooldown_until TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(attacker_username, victim_username)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_hack_tool_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                access_id INTEGER,
                attacker_username TEXT NOT NULL,
                victim_username TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                access_key TEXT NOT NULL DEFAULT '',
                result TEXT NOT NULL DEFAULT '',
                amount INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                UNIQUE(attacker_username, victim_username, tool_id, access_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_target_runtime (
                username TEXT PRIMARY KEY,
                target_key TEXT NOT NULL DEFAULT '',
                target_json TEXT NOT NULL DEFAULT '{}',
                security_json TEXT NOT NULL DEFAULT '{}',
                actions_allowed_json TEXT NOT NULL DEFAULT '{}',
                disarm_progress INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'cleared',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_target_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                event_type TEXT NOT NULL,
                target_key TEXT NOT NULL DEFAULT '',
                version INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_player_target_events_username_created
            ON player_target_events(username, created_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_positions (
                username TEXT PRIMARY KEY,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dev_bug_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'Other',
                severity TEXT NOT NULL DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'new',
                created_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                app_version TEXT NOT NULL DEFAULT '',
                current_url TEXT NOT NULL DEFAULT '',
                screen TEXT NOT NULL DEFAULT '',
                context_json TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS captured_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                lat REAL NOT NULL,
                lng REAL NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                icon TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT '',
                generated INTEGER NOT NULL DEFAULT 0,
                stationary INTEGER NOT NULL DEFAULT 1,
                target_json TEXT NOT NULL,
                captured_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(owner_username, lat, lng, label)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                vertices_json TEXT NOT NULL,
                centroid_lat REAL,
                centroid_lng REAL,
                area_size REAL NOT NULL DEFAULT 0,
                max_edge_distance REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS area_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                area_id INTEGER,
                owner_username TEXT NOT NULL,
                actor_username TEXT NOT NULL,
                event_type TEXT NOT NULL,
                lat REAL,
                lng REAL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS territory_conflicts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conflict_key TEXT NOT NULL UNIQUE,
                player_a_username TEXT NOT NULL,
                player_b_username TEXT NOT NULL,
                area_a_id INTEGER,
                area_b_id INTEGER,
                participants_json TEXT NOT NULL DEFAULT '[]',
                area_ids_json TEXT NOT NULL DEFAULT '[]',
                intersection_json TEXT NOT NULL DEFAULT '[]',
                intersections_json TEXT NOT NULL DEFAULT '[]',
                targets_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'active',
                last_actor_username TEXT NOT NULL DEFAULT '',
                source_event TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conflict_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(territory_conflicts)").fetchall()
        }
        if "participants_json" not in conflict_columns:
            conn.execute("ALTER TABLE territory_conflicts ADD COLUMN participants_json TEXT NOT NULL DEFAULT '[]'")
        if "area_ids_json" not in conflict_columns:
            conn.execute("ALTER TABLE territory_conflicts ADD COLUMN area_ids_json TEXT NOT NULL DEFAULT '[]'")
        if "intersections_json" not in conflict_columns:
            conn.execute("ALTER TABLE territory_conflicts ADD COLUMN intersections_json TEXT NOT NULL DEFAULT '[]'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reported_vulnerabilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_lat REAL NOT NULL,
                target_lng REAL NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL DEFAULT '',
                icon TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT '',
                generated INTEGER NOT NULL DEFAULT 0,
                reported_by_username TEXT NOT NULL,
                reported_by_clan TEXT NOT NULL DEFAULT '',
                territory_owner_username TEXT NOT NULL DEFAULT '',
                territory_owner_clan TEXT NOT NULL DEFAULT '',
                security_json TEXT NOT NULL DEFAULT '{}',
                target_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS game_state_deltas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                version INTEGER NOT NULL,
                scope TEXT NOT NULL,
                type TEXT NOT NULL,
                entity_id TEXT NOT NULL DEFAULT '',
                dedupe_key TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                UNIQUE(username, dedupe_key)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_action_receipts (
                receipt_key TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                app_id TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL DEFAULT '',
                target_key TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                response_json TEXT NOT NULL DEFAULT '{}',
                status_code INTEGER NOT NULL DEFAULT 202,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                expires_at REAL NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_operations (
                operation_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                target_key TEXT NOT NULL DEFAULT '',
                operation_type TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL,
                operation_json TEXT NOT NULL DEFAULT '{}',
                risk_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operation_events (
                event_id TEXT PRIMARY KEY,
                operation_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                dedupe_key TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_operation_events_dedupe
            ON operation_events(dedupe_key)
            WHERE dedupe_key != ''
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS system_messages (
                message_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                dedupe_key TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                type TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'pending',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                expires_at REAL NOT NULL DEFAULT 0,
                consumed_at TEXT
            )
            """
        )
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(system_messages)").fetchall()
        }
        if "expires_at" not in columns:
            conn.execute("ALTER TABLE system_messages ADD COLUMN expires_at REAL NOT NULL DEFAULT 0")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_system_messages_dedupe
            ON system_messages(username, dedupe_key)
            WHERE dedupe_key != ''
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_captured_targets_owner ON captured_targets(owner_username)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_areas_owner ON player_areas(owner_username)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_area_events_owner ON area_events(owner_username, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_territory_conflicts_players ON territory_conflicts(player_a_username, player_b_username, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reported_vulnerabilities_clan_status ON reported_vulnerabilities(reported_by_clan, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reported_vulnerabilities_target ON reported_vulnerabilities(target_lat, target_lng, label, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wallet_transactions_users ON wallet_transactions(from_username, to_username, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_hack_access_pair ON player_hack_access(attacker_username, victim_username, hacked_until, cooldown_until)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_hack_tool_usage_pair ON player_hack_tool_usage(attacker_username, victim_username, tool_id, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_dev_bug_reports_status ON dev_bug_reports(status, category, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_game_state_deltas_user_version ON game_state_deltas(username, version)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_game_state_deltas_created_at ON game_state_deltas(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_action_receipts_user_updated ON app_action_receipts(username, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_app_action_receipts_expires_at ON app_action_receipts(expires_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_operations_user_status ON player_operations(username, status, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_operations_target ON player_operations(username, target_key)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_operation_events_operation ON operation_events(operation_id, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_system_messages_user_status ON system_messages(username, status, created_at)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_apps (
                username TEXT NOT NULL,
                app_id TEXT NOT NULL,
                app_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'installed',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(username, app_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_tool_files (
                username TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                app_id TEXT NOT NULL DEFAULT '',
                tool_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(username, tool_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS player_storage (
                username TEXT PRIMARY KEY,
                capacity INTEGER NOT NULL DEFAULT 0,
                used INTEGER NOT NULL DEFAULT 0,
                unit TEXT NOT NULL DEFAULT 'MB',
                modifiers_json TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_balances (
                username TEXT PRIMARY KEY,
                balance INTEGER NOT NULL DEFAULT 0,
                version INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_balance_events (
                event_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                transaction_key TEXT NOT NULL DEFAULT '',
                amount_delta INTEGER NOT NULL DEFAULT 0,
                balance INTEGER NOT NULL DEFAULT 0,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_balance_events_key
            ON wallet_balance_events(username, transaction_key)
            WHERE transaction_key != ''
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wallet_ledger (
                ledger_id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                event_type TEXT NOT NULL,
                amount_delta INTEGER NOT NULL DEFAULT 0,
                balance_after INTEGER NOT NULL DEFAULT 0,
                source TEXT NOT NULL DEFAULT '',
                source_id TEXT NOT NULL DEFAULT '',
                peer_username TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                dedupe_key TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wallet_ledger_dedupe
            ON wallet_ledger(username, dedupe_key)
            WHERE dedupe_key != ''
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_wallet_ledger_user_created ON wallet_ledger(username, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_apps_user_status ON player_apps(username, status, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_tool_files_user_app ON player_tool_files(username, app_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS profile_store_migrations (
                migration_id TEXT NOT NULL,
                username TEXT NOT NULL,
                status TEXT NOT NULL,
                source_checksum TEXT,
                result_checksum TEXT,
                started_at TEXT,
                completed_at TEXT,
                error_json TEXT,
                backup_json TEXT,
                tool_version TEXT NOT NULL,
                PRIMARY KEY(migration_id, username)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_profile_store_migrations_status
            ON profile_store_migrations(migration_id, status)
            """
        )


class UserStore:
    def __init__(self, db_path=DB_PATH, seed_path=USERS_SEED_PATH):
        self.db_path = db_path
        self.seed_path = seed_path
        init_db(self.db_path)
        self.seed_from_json_if_empty()

    def seed_from_json_if_empty(self):
        with db_connect(self.db_path) as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
            if row["count"] > 0 or not os.path.exists(self.seed_path):
                return

            with open(self.seed_path, "r", encoding="utf-8") as f:
                users = json.load(f)

            now = utc_now()
            for profile in users:
                username = profile.get("username")
                if not username:
                    continue
                ensure_password_hash(profile)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users
                        (username, password, salt, profile_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        profile.get("password", ""),
                        profile.get("salt", ""),
                        dumps_json(profile),
                        now,
                        now,
                    ),
                )

    def list_profiles(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute("SELECT profile_json FROM users ORDER BY id").fetchall()
            return [loads_json(row["profile_json"], {}) for row in rows]

    def get_profile(self, username):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return None
            return loads_json(row["profile_json"], {})

    def save_profile(self, profile):
        profile = dict(profile or {})
        username = profile.get("username")
        if not username:
            raise ValueError("Profile must contain username.")

        launch_queue_write_mode = str(profile.pop("_launch_queue_write_mode", "") or "").strip()
        ensure_password_hash(profile)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            current_row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            current_profile = loads_json(current_row["profile_json"], {}) if current_row else {}
            if current_profile:
                if launch_queue_write_mode == "clear":
                    profile["launch_queue"] = []
                elif launch_queue_write_mode == "append":
                    profile["launch_queue"] = merge_launch_queue_values(
                        current_profile.get("launch_queue", []),
                        profile.get("launch_queue", []),
                    )
                else:
                    # launch_queue is a transient app-launch bus. A slow full-profile
                    # write must not resurrect apps that /launch-queue already consumed.
                    profile["launch_queue"] = current_profile.get("launch_queue", [])

            conn.execute(
                """
                INSERT INTO users
                    (username, password, salt, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password = excluded.password,
                    salt = excluded.salt,
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    profile.get("password", ""),
                    profile.get("salt", ""),
                    dumps_json(profile),
                    now,
                    now,
                ),
            )

    def consume_launch_queue(self, username):
        username = str(username or "").strip()
        if not username:
            return None

        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return None

            profile = loads_json(row["profile_json"], {})
            launch_list = merge_launch_queue_values([], profile.get("launch_queue", []))
            if not launch_list:
                return []

            profile["launch_queue"] = []
            ensure_password_hash(profile)
            now = utc_now()
            conn.execute(
                """
                UPDATE users
                SET password = ?, salt = ?, profile_json = ?, updated_at = ?
                WHERE username = ?
                """,
                (
                    profile.get("password", ""),
                    profile.get("salt", ""),
                    dumps_json(profile),
                    now,
                    username,
                ),
            )
            return launch_list

    def username_exists(self, username):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return row is not None

    def authenticate(self, username, password):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT password, profile_json FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return False
            stored_password = row["password"] or ""
            if not verify_password(password, stored_password):
                return False
            if not is_password_hash(stored_password):
                profile = loads_json(row["profile_json"], {})
                profile["password"] = str(password or "")
                ensure_password_hash(profile)
                conn.execute(
                    """
                    UPDATE users
                    SET password = ?, salt = ?, profile_json = ?, updated_at = ?
                    WHERE username = ?
                    """,
                    (
                        profile.get("password", ""),
                        profile.get("salt", ""),
                        dumps_json(profile),
                        utc_now(),
                        username,
                    ),
                )
            return True

    def delete_user(self, username):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not row:
                return False

            conn.execute(
                "DELETE FROM chat_messages WHERE owner_username = ? OR peer_name = ?",
                (username, username),
            )
            conn.execute(
                "DELETE FROM contacts WHERE owner_username = ? OR contact_name = ?",
                (username, username),
            )
            conn.execute("DELETE FROM mail_presence WHERE username = ?", (username,))
            conn.execute("DELETE FROM kv_store WHERE key = ?", (f"mail_seed:{username}",))
            conn.execute("DELETE FROM area_events WHERE owner_username = ? OR actor_username = ?", (username, username))
            conn.execute("DELETE FROM player_areas WHERE owner_username = ?", (username,))
            conn.execute("DELETE FROM captured_targets WHERE owner_username = ?", (username,))
            conn.execute(
                "DELETE FROM reported_vulnerabilities WHERE reported_by_username = ? OR territory_owner_username = ?",
                (username, username),
            )
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
            return True


class JsonResourceStore:
    # Repository JSON files are seed/reference content. Runtime reads from the
    # SQLite json_resources table; changing static/*.json requires an explicit
    # sync/import step and should not silently mutate runtime state.
    SEED_RESOURCE_KEYS = {
        "app_config",
        "user_template",
        "user_security",
        "terminal_command",
        "messages",
        "friends",
        "fractions",
    }

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)
        self.seed_static_directory()

    def _seed_file_if_missing(self, conn, key, seed_path):
        row = conn.execute(
            "SELECT 1 FROM json_resources WHERE key = ?",
            (key,),
        ).fetchone()
        if row or not seed_path or not os.path.exists(seed_path):
            return

        with open(seed_path, "r", encoding="utf-8") as f:
            value = json.load(f)
        conn.execute(
            """
            INSERT INTO json_resources (key, source_path, value_json, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (key, seed_path, dumps_json(value), utc_now()),
        )

    def seed_static_directory(self, static_dir="static"):
        if not os.path.isdir(static_dir):
            return

        with db_connect(self.db_path) as conn:
            for filename in os.listdir(static_dir):
                if not filename.endswith(".json"):
                    continue
                path = os.path.join(static_dir, filename)
                key = os.path.splitext(filename)[0]
                if key not in self.SEED_RESOURCE_KEYS:
                    continue
                self._seed_file_if_missing(conn, key, path)

    def get(self, key, seed_path=None, default=None):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value_json FROM json_resources WHERE key = ?",
                (key,),
            ).fetchone()
            if row:
                return loads_json(row["value_json"], default)

            legacy = conn.execute(
                "SELECT value_json FROM kv_store WHERE key = ?",
                (key,),
            ).fetchone()
            if legacy:
                value = loads_json(legacy["value_json"], default)
                conn.execute(
                    """
                    INSERT INTO json_resources (key, source_path, value_json, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (key, seed_path or "", dumps_json(value), utc_now()),
                )
                return value

            if seed_path and os.path.exists(seed_path):
                self._seed_file_if_missing(conn, key, seed_path)
                row = conn.execute(
                    "SELECT value_json FROM json_resources WHERE key = ?",
                    (key,),
                ).fetchone()
                if row:
                    return loads_json(row["value_json"], default)

            return copy.deepcopy(default)

    def set(self, key, value):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO json_resources (key, source_path, value_json, updated_at)
                VALUES (?, '', ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, dumps_json(value), utc_now()),
            )


class DevBugReportStore:
    VALID_CATEGORIES = {
        "UI", "Map", "Operations", "Files", "Ghost Exchange",
        "Googleplex", "Login", "Performance", "Other"
    }
    VALID_SEVERITIES = {"low", "medium", "high", "blocker"}
    VALID_STATUSES = {"new", "confirmed", "in_progress", "fixed", "duplicate", "wontfix"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def _row_to_report(self, row):
        return {
            "id": row["id"],
            "title": row["title"],
            "description": row["description"],
            "category": row["category"],
            "severity": row["severity"],
            "status": row["status"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "app_version": row["app_version"],
            "current_url": row["current_url"],
            "screen": row["screen"],
            "context": loads_json(row["context_json"], {}),
        }

    def _normalize_category(self, value):
        value = str(value or "Other").strip()
        return value if value in self.VALID_CATEGORIES else "Other"

    def _normalize_severity(self, value):
        value = str(value or "medium").strip().lower()
        return value if value in self.VALID_SEVERITIES else "medium"

    def _normalize_status(self, value):
        value = str(value or "new").strip().lower()
        return value if value in self.VALID_STATUSES else "new"

    def list_reports(self, search="", category="", status="", limit=200):
        search = str(search or "").strip().lower()
        category = str(category or "").strip()
        status = str(status or "").strip().lower()
        limit = max(1, min(int(limit or 200), 500))

        clauses = []
        params = []
        if category:
            clauses.append("category = ?")
            params.append(self._normalize_category(category))
        if status:
            clauses.append("status = ?")
            params.append(self._normalize_status(status))
        if search:
            clauses.append("(lower(title) LIKE ? OR lower(description) LIKE ?)")
            needle = f"%{search}%"
            params.extend([needle, needle])

        sql = "SELECT * FROM dev_bug_reports"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with db_connect(self.db_path) as conn:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_report(row) for row in rows]

    def find_similar(self, title, limit=5):
        words = [
            re_word for re_word in
            [part.strip().lower() for part in str(title or "").replace("-", " ").split()]
            if len(re_word) >= 4
        ]
        if not words:
            return []

        clauses = ["lower(title) LIKE ?" for _ in words[:6]]
        params = [f"%{word}%" for word in words[:6]]
        params.append(max(1, min(int(limit or 5), 10)))
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM dev_bug_reports
                WHERE {" OR ".join(clauses)}
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            return [self._row_to_report(row) for row in rows]

    def create_report(self, data, created_by, app_version=""):
        title = str((data or {}).get("title") or "").strip()
        if not title:
            raise ValueError("Tytul zgloszenia jest wymagany.")

        now = utc_now()
        context = (data or {}).get("context") or {}
        if not isinstance(context, dict):
            context = {"raw": str(context)}

        with db_connect(self.db_path) as conn:
            cur = conn.execute(
                """
                INSERT INTO dev_bug_reports (
                    title, description, category, severity, status, created_by,
                    created_at, updated_at, app_version, current_url, screen, context_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    str((data or {}).get("description") or "").strip(),
                    self._normalize_category((data or {}).get("category")),
                    self._normalize_severity((data or {}).get("severity")),
                    self._normalize_status((data or {}).get("status") or "new"),
                    str(created_by or ""),
                    now,
                    now,
                    str(app_version or (data or {}).get("app_version") or ""),
                    str((data or {}).get("current_url") or ""),
                    str((data or {}).get("screen") or ""),
                    dumps_json(context),
                ),
            )
            row = conn.execute(
                "SELECT * FROM dev_bug_reports WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
            return self._row_to_report(row)

    def update_report(self, report_id, data):
        report_id = int(report_id)
        allowed = {}
        if "status" in (data or {}):
            allowed["status"] = self._normalize_status((data or {}).get("status"))
        if "severity" in (data or {}):
            allowed["severity"] = self._normalize_severity((data or {}).get("severity"))
        if "category" in (data or {}):
            allowed["category"] = self._normalize_category((data or {}).get("category"))
        if "title" in (data or {}):
            title = str((data or {}).get("title") or "").strip()
            if title:
                allowed["title"] = title
        if "description" in (data or {}):
            allowed["description"] = str((data or {}).get("description") or "").strip()

        if not allowed:
            with db_connect(self.db_path) as conn:
                row = conn.execute("SELECT * FROM dev_bug_reports WHERE id = ?", (report_id,)).fetchone()
                return self._row_to_report(row) if row else None

        allowed["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in allowed)
        params = list(allowed.values()) + [report_id]
        with db_connect(self.db_path) as conn:
            conn.execute(
                f"UPDATE dev_bug_reports SET {assignments} WHERE id = ?",
                params,
            )
            row = conn.execute("SELECT * FROM dev_bug_reports WHERE id = ?", (report_id,)).fetchone()
            return self._row_to_report(row) if row else None


class TerritoryStore:
    BASE_AREA_EDGE_METERS = 300
    MIN_TRIANGLE_AREA_SQM = 1
    MAX_EXACT_AREA_TARGETS = int(os.environ.get("CHAOS_TERRITORY_EXACT_TARGET_LIMIT", "32"))
    MAX_EXACT_AREA_TRIANGLES = int(os.environ.get("CHAOS_TERRITORY_EXACT_TRIANGLE_LIMIT", "1200"))

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _distance_meters(a, b):
        lat1 = math.radians(float(a["lat"]))
        lon1 = math.radians(float(a["lng"]))
        lat2 = math.radians(float(b["lat"]))
        lon2 = math.radians(float(b["lng"]))
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        return 6371000 * 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))

    @staticmethod
    def _triangle_area_sqm(edges):
        a, b, c = edges
        semiperimeter = (a + b + c) / 2
        area_value = (
            semiperimeter
            * (semiperimeter - a)
            * (semiperimeter - b)
            * (semiperimeter - c)
        )
        if area_value <= 0:
            return 0
        return math.sqrt(area_value)

    @staticmethod
    def _convex_hull(targets):
        unique = {}
        for target in targets:
            key = (round(float(target.get("lng", target.get("lon"))), 7), round(float(target.get("lat")), 7))
            unique[key] = target

        points = sorted(unique.items())
        if len(points) <= 1:
            return [target for _, target in points]

        def cross(origin, a, b):
            return (
                (a[0][0] - origin[0][0]) * (b[0][1] - origin[0][1])
                - (a[0][1] - origin[0][1]) * (b[0][0] - origin[0][0])
            )

        lower = []
        for point in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
                lower.pop()
            lower.append(point)

        upper = []
        for point in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
                upper.pop()
            upper.append(point)

        return [target for _, target in lower[:-1] + upper[:-1]]

    @staticmethod
    def _polygon_area_sqm(vertices):
        if len(vertices or []) < 3:
            return 0

        center_lat = math.radians(sum(float(v["lat"]) for v in vertices) / len(vertices))
        origin_lat = float(vertices[0]["lat"])
        origin_lng = float(vertices[0]["lng"])
        meters = []
        for vertex in vertices:
            x = math.radians(float(vertex["lng"]) - origin_lng) * 6371000 * math.cos(center_lat)
            y = math.radians(float(vertex["lat"]) - origin_lat) * 6371000
            meters.append((x, y))

        area = 0
        for i, point in enumerate(meters):
            next_point = meters[(i + 1) % len(meters)]
            area += point[0] * next_point[1] - next_point[0] * point[1]
        return abs(area) / 2

    def _connected_target_groups(self, targets, max_edge_distance):
        unvisited = set(range(len(targets)))
        groups = []

        while unvisited:
            start = unvisited.pop()
            stack = [start]
            group_indexes = {start}

            while stack:
                current = stack.pop()
                linked = [
                    other for other in list(unvisited)
                    if self._distance_meters(targets[current], targets[other]) <= max_edge_distance
                ]
                for other in linked:
                    unvisited.remove(other)
                    group_indexes.add(other)
                    stack.append(other)

            groups.append([targets[index] for index in sorted(group_indexes)])

        return groups

    @staticmethod
    def point_in_polygon(lat, lng, vertices):
        if len(vertices or []) < 3:
            return False

        inside = False
        j = len(vertices) - 1
        for i, vertex in enumerate(vertices):
            yi = float(vertex.get("lat"))
            xi = float(vertex.get("lng"))
            yj = float(vertices[j].get("lat"))
            xj = float(vertices[j].get("lng"))
            crosses = (xi > lng) != (xj > lng)
            if crosses:
                slope_lat = (yj - yi) * (lng - xi) / ((xj - xi) or 1e-12) + yi
                if lat < slope_lat:
                    inside = not inside
            j = i
        return inside

    @staticmethod
    def _player_level(value):
        try:
            return max(1, int(value))
        except (TypeError, ValueError):
            return 1

    @staticmethod
    def _area_vertex(target):
        lng = target.get("lng", target.get("lon"))
        return {
            "lat": float(target.get("lat")),
            "lng": float(lng),
            "label": target.get("label", ""),
            "name": target.get("name") or target.get("label", ""),
            "icon": target.get("icon", ""),
            "source_type": target.get("source_type", ""),
            "captured_at": target.get("captured_at", ""),
        }

    def _area_from_hull(self, targets):
        hull = self._convex_hull(targets)
        if len(hull) < 3:
            return None

        vertices = [self._area_vertex(target) for target in hull]
        area_size = self._polygon_area_sqm(vertices)
        if area_size < self.MIN_TRIANGLE_AREA_SQM:
            return None

        hull_edges = [
            self._distance_meters(vertices[i], vertices[(i + 1) % len(vertices)])
            for i in range(len(vertices))
        ]
        return {
            "vertices": vertices,
            "centroid_lat": sum(vertex["lat"] for vertex in vertices) / len(vertices),
            "centroid_lng": sum(vertex["lng"] for vertex in vertices) / len(vertices),
            "area_size": area_size,
            "max_edge_distance": max(hull_edges) if hull_edges else 0,
            "status": "active",
        }

    def _normalize_target(self, username, target):
        now = utc_now()
        normalized = copy.deepcopy(target or {})
        lng = normalized.get("lng", normalized.get("lon"))
        normalized["lng"] = float(lng)
        normalized["lon"] = float(lng)
        normalized["lat"] = float(normalized.get("lat"))
        generated = bool(normalized.get("generated", False))
        stationary = bool(normalized.get("stationary", not generated))
        normalized["owner_username"] = username
        normalized["stationary"] = stationary
        normalized.setdefault("captured_at", now)
        return {
            "owner_username": username,
            "lat": normalized["lat"],
            "lng": normalized["lng"],
            "label": str(normalized.get("label") or ""),
            "name": str(normalized.get("name") or normalized.get("label") or ""),
            "icon": str(normalized.get("icon") or ""),
            "source_type": str(normalized.get("source_type") or ""),
            "generated": 1 if generated else 0,
            "stationary": 1 if stationary else 0,
            "target_json": dumps_json(normalized),
            "captured_at": str(normalized.get("captured_at") or now),
            "updated_at": now,
        }

    def save_captured_target(self, username, target):
        data = self._normalize_target(username, target)
        with db_connect(self.db_path) as conn:
            if data["stationary"]:
                conn.execute(
                    """
                    DELETE FROM captured_targets
                    WHERE owner_username != ?
                        AND ROUND(lat, 5) = ROUND(?, 5)
                        AND ROUND(lng, 5) = ROUND(?, 5)
                    """,
                    (username, data["lat"], data["lng"]),
                )
            conn.execute(
                """
                INSERT INTO captured_targets
                    (owner_username, lat, lng, label, name, icon, source_type,
                     generated, stationary, target_json, captured_at, updated_at)
                VALUES
                    (:owner_username, :lat, :lng, :label, :name, :icon, :source_type,
                     :generated, :stationary, :target_json, :captured_at, :updated_at)
                ON CONFLICT(owner_username, lat, lng, label) DO UPDATE SET
                    name = excluded.name,
                    icon = excluded.icon,
                    source_type = excluded.source_type,
                    generated = excluded.generated,
                    stationary = excluded.stationary,
                    target_json = excluded.target_json,
                    updated_at = excluded.updated_at
                """,
                data,
            )
        return loads_json(data["target_json"], {})

    def remove_captured_target(self, username, lat, lng, label=None):
        query = """
            DELETE FROM captured_targets
            WHERE owner_username = ?
                AND ROUND(lat, 5) = ROUND(?, 5)
                AND ROUND(lng, 5) = ROUND(?, 5)
        """
        params = [username, float(lat), float(lng)]
        if label is not None:
            query += " AND label = ?"
            params.append(str(label))

        with db_connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount > 0

    def sync_profile_hacked_targets(self, username, profile):
        synced = []
        for target in (profile or {}).get("hacked", []):
            if not isinstance(target, dict):
                continue
            if target.get("lat") is None or (target.get("lng") is None and target.get("lon") is None):
                continue
            synced.append(self.save_captured_target(username, target))
        return synced

    def list_captured_targets(self, username, stationary=None):
        query = "SELECT lat, lng, target_json FROM captured_targets WHERE owner_username = ?"
        params = [username]
        if stationary is not None:
            query += " AND stationary = ?"
            params.append(1 if stationary else 0)
        query += " ORDER BY captured_at"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            targets = []
            for row in rows:
                target = loads_json(row["target_json"], {})
                target["lat"] = float(target.get("lat", row["lat"]))
                lng = target.get("lng", target.get("lon", row["lng"]))
                target["lng"] = float(lng)
                target["lon"] = float(lng)
                targets.append(target)
            return targets

    def list_all_captured_targets(self, stationary=None):
        query = "SELECT lat, lng, target_json FROM captured_targets"
        params = []
        if stationary is not None:
            query += " WHERE stationary = ?"
            params.append(1 if stationary else 0)
        query += " ORDER BY owner_username, captured_at"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            targets = []
            for row in rows:
                target = loads_json(row["target_json"], {})
                target["lat"] = float(target.get("lat", row["lat"]))
                lng = target.get("lng", target.get("lon", row["lng"]))
                target["lng"] = float(lng)
                target["lon"] = float(lng)
                targets.append(target)
            return targets

    def build_player_areas(self, username, player_level=1):
        level = self._player_level(player_level)
        max_edge_distance = self.BASE_AREA_EDGE_METERS * level
        targets = [
            target
            for target in self.list_captured_targets(username, stationary=True)
            if target.get("lat") is not None and target.get("lng") is not None
        ]

        areas = []
        for group in self._connected_target_groups(targets, max_edge_distance):
            if len(group) < 3:
                continue
            if len(group) > self.MAX_EXACT_AREA_TARGETS:
                area = self._area_from_hull(group)
                if area:
                    print(
                        "[TERRITORY] large cluster approximated "
                        f"username={username} targets={len(group)} "
                        f"limit={self.MAX_EXACT_AREA_TARGETS}",
                        flush=True,
                    )
                    areas.append(area)
                continue

            valid_triangles = []
            exact_triangle_limit_exceeded = False
            for combo_indexes in combinations(range(len(group)), 3):
                combo = [group[index] for index in combo_indexes]
                vertices = [self._area_vertex(target) for target in combo]
                edges = [
                    self._distance_meters(vertices[i], vertices[(i + 1) % len(vertices)])
                    for i in range(len(vertices))
                ]
                if max(edges) > max_edge_distance:
                    continue

                area_size = self._polygon_area_sqm(vertices)
                if area_size < self.MIN_TRIANGLE_AREA_SQM:
                    continue

                valid_triangles.append(set(combo_indexes))
                if len(valid_triangles) > self.MAX_EXACT_AREA_TRIANGLES:
                    exact_triangle_limit_exceeded = True
                    break

            if exact_triangle_limit_exceeded:
                area = self._area_from_hull(group)
                if area:
                    print(
                        "[TERRITORY] dense cluster approximated "
                        f"username={username} targets={len(group)} "
                        f"triangles>{self.MAX_EXACT_AREA_TRIANGLES}",
                        flush=True,
                    )
                    areas.append(area)
                continue

            unvisited = set(range(len(valid_triangles)))
            while unvisited:
                triangle_index = unvisited.pop()
                stack = [triangle_index]
                cluster_indexes = set(valid_triangles[triangle_index])

                while stack:
                    current = stack.pop()
                    linked = [
                        other for other in list(unvisited)
                        if valid_triangles[current] & valid_triangles[other]
                    ]
                    for other in linked:
                        unvisited.remove(other)
                        cluster_indexes.update(valid_triangles[other])
                        stack.append(other)

                area = self._area_from_hull([group[index] for index in sorted(cluster_indexes)])
                if not area:
                    continue
                areas.append(area)

        areas.sort(key=lambda area: (area["area_size"], area["max_edge_distance"]))
        return areas

    def rebuild_player_areas(self, username, player_level=1):
        areas = self.build_player_areas(username, player_level)
        self.replace_player_areas(username, areas)
        self.refresh_encirclement_statuses()
        return areas

    def replace_player_areas(self, username, areas):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM player_areas WHERE owner_username = ?", (username,))
            for area in areas:
                conn.execute(
                    """
                    INSERT INTO player_areas
                        (owner_username, vertices_json, centroid_lat, centroid_lng,
                         area_size, max_edge_distance, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        username,
                        dumps_json(area.get("vertices", [])),
                        area.get("centroid_lat"),
                        area.get("centroid_lng"),
                        float(area.get("area_size") or 0),
                        float(area.get("max_edge_distance") or 0),
                        area.get("status", "active"),
                        now,
                        now,
                    ),
                )

    def list_player_areas(self, username=None):
        query = "SELECT * FROM player_areas"
        params = []
        if username:
            query += " WHERE owner_username = ?"
            params.append(username)
        query += " ORDER BY owner_username, id"
        with db_connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            return [
                {
                    "id": row["id"],
                    "owner_username": row["owner_username"],
                    "vertices": loads_json(row["vertices_json"], []),
                    "centroid_lat": row["centroid_lat"],
                    "centroid_lng": row["centroid_lng"],
                    "area_size": row["area_size"],
                    "max_edge_distance": row["max_edge_distance"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    def add_area_event(self, owner_username, actor_username, event_type, area_id=None, lat=None, lng=None, payload=None):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO area_events
                    (area_id, owner_username, actor_username, event_type, lat, lng, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    area_id,
                    owner_username,
                    actor_username,
                    event_type,
                    lat,
                    lng,
                    dumps_json(payload or {}),
                    utc_now(),
                ),
            )

    def recent_area_event_exists(self, owner_username, actor_username, event_type, area_id=None, seconds=60):
        threshold = (datetime.utcnow() - timedelta(seconds=seconds)).isoformat(timespec="seconds")
        query = """
            SELECT 1
            FROM area_events
            WHERE owner_username = ?
                AND actor_username = ?
                AND event_type = ?
                AND created_at >= ?
        """
        params = [owner_username, actor_username, event_type, threshold]
        if area_id is not None:
            query += " AND area_id = ?"
            params.append(area_id)
        query += " LIMIT 1"
        with db_connect(self.db_path) as conn:
            return conn.execute(query, params).fetchone() is not None

    def area_event_exists_with_payload_key(self, owner_username, actor_username, event_type, payload_key, payload_value):
        if not payload_key or payload_value is None:
            return False
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM area_events
                WHERE owner_username = ?
                    AND actor_username = ?
                    AND event_type = ?
                ORDER BY id DESC
                """,
                (owner_username, actor_username, event_type),
            ).fetchall()
        for row in rows:
            payload = loads_json(row["payload_json"], {})
            if isinstance(payload, dict) and str(payload.get(payload_key) or "") == str(payload_value):
                return True
        return False

    def list_recent_area_intruders(self, owner_username, seconds=120):
        threshold = (datetime.utcnow() - timedelta(seconds=seconds)).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT area_id, actor_username, lat, lng, payload_json, created_at
                FROM area_events
                WHERE owner_username = ?
                    AND event_type = 'intruder_enter'
                    AND created_at >= ?
                ORDER BY id DESC
                """,
                (owner_username, threshold),
            ).fetchall()

        seen = set()
        intruders = []
        for row in rows:
            key = (row["area_id"], row["actor_username"])
            if key in seen:
                continue
            seen.add(key)
            payload = loads_json(row["payload_json"], {})
            intruders.append({
                "area_id": row["area_id"],
                "username": row["actor_username"],
                "lat": row["lat"],
                "lng": row["lng"],
                "created_at": row["created_at"],
                "payload": payload,
            })
        return intruders

    def refresh_encirclement_statuses(self):
        areas = self.list_player_areas()
        statuses = {area["id"]: "active" for area in areas}

        for smaller in areas:
            for larger in areas:
                if smaller["id"] == larger["id"]:
                    continue
                if smaller["owner_username"] == larger["owner_username"]:
                    continue
                if float(larger.get("area_size") or 0) <= float(smaller.get("area_size") or 0):
                    continue
                if all(
                    self.point_in_polygon(vertex["lat"], vertex["lng"], larger.get("vertices", []))
                    for vertex in smaller.get("vertices", [])
                ):
                    statuses[smaller["id"]] = "encircled"
                    break

        now = utc_now()
        with db_connect(self.db_path) as conn:
            for area_id, status in statuses.items():
                conn.execute(
                    """
                    UPDATE player_areas
                    SET status = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (status, now, area_id),
                )
        return statuses

    def delete_user_data(self, username):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM area_events WHERE owner_username = ? OR actor_username = ?", (username, username))
            conn.execute("DELETE FROM player_areas WHERE owner_username = ?", (username,))
            conn.execute("DELETE FROM captured_targets WHERE owner_username = ?", (username,))
            conn.execute(
                """
                DELETE FROM territory_conflicts
                WHERE player_a_username = ?
                    OR player_b_username = ?
                    OR participants_json LIKE ?
                """,
                (username, username, f'%"{username}"%'),
            )
            conn.execute(
                "DELETE FROM reported_vulnerabilities WHERE reported_by_username = ? OR territory_owner_username = ?",
                (username, username),
            )


class TerritoryConflictStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _row_to_conflict(row):
        if not row:
            return None
        participants = loads_json(row["participants_json"], [])
        if not participants:
            participants = [row["player_a_username"], row["player_b_username"]]
        area_ids = loads_json(row["area_ids_json"], [])
        if not area_ids:
            area_ids = [row["area_a_id"], row["area_b_id"]]
        intersections = loads_json(row["intersections_json"], [])
        if not intersections:
            intersection = loads_json(row["intersection_json"], [])
            intersections = [intersection] if intersection else []
        return {
            "id": row["id"],
            "conflict_key": row["conflict_key"],
            "participant_usernames": participants,
            "primary_participant_usernames": [row["player_a_username"], row["player_b_username"]],
            "player_a_username": row["player_a_username"],
            "player_b_username": row["player_b_username"],
            "participants": participants,
            "primary_area_ids": [row["area_a_id"], row["area_b_id"]],
            "area_a_id": row["area_a_id"],
            "area_b_id": row["area_b_id"],
            "area_ids": area_ids,
            "intersection": loads_json(row["intersection_json"], []),
            "intersections": intersections,
            "targets": loads_json(row["targets_json"], []),
            "status": row["status"],
            "last_actor_username": row["last_actor_username"],
            "source_event": row["source_event"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def upsert_conflict(self, conflict):
        participants = sorted({
            str(participant)
            for participant in (conflict.get("participants") or [
                conflict.get("player_a_username"),
                conflict.get("player_b_username"),
            ])
            if participant
        })
        if len(participants) < 2:
            raise ValueError("Territory conflict requires at least two participants.")

        area_ids = [
            area_id for area_id in (conflict.get("area_ids") or [
                conflict.get("area_a_id"),
                conflict.get("area_b_id"),
            ])
            if area_id is not None
        ]
        intersections = conflict.get("intersections") or []
        if not intersections and conflict.get("intersection"):
            intersections = [conflict.get("intersection")]

        now = utc_now()
        data = {
            "conflict_key": str(conflict.get("conflict_key") or ""),
            "player_a_username": participants[0],
            "player_b_username": participants[1],
            "area_a_id": area_ids[0] if area_ids else None,
            "area_b_id": area_ids[1] if len(area_ids) > 1 else None,
            "participants_json": dumps_json(participants),
            "area_ids_json": dumps_json(area_ids),
            "intersection_json": dumps_json(conflict.get("intersection") or (intersections[0] if intersections else [])),
            "intersections_json": dumps_json(intersections),
            "targets_json": dumps_json(conflict.get("targets") or []),
            "status": str(conflict.get("status") or "active"),
            "last_actor_username": str(conflict.get("last_actor_username") or ""),
            "source_event": str(conflict.get("source_event") or ""),
            "created_at": now,
            "updated_at": now,
        }
        if not data["conflict_key"]:
            raise ValueError("Territory conflict requires conflict_key.")

        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO territory_conflicts
                    (conflict_key, player_a_username, player_b_username, area_a_id, area_b_id,
                     participants_json, area_ids_json, intersection_json, intersections_json,
                     targets_json, status, last_actor_username, source_event, created_at, updated_at)
                VALUES
                    (:conflict_key, :player_a_username, :player_b_username, :area_a_id, :area_b_id,
                     :participants_json, :area_ids_json, :intersection_json, :intersections_json,
                     :targets_json, :status, :last_actor_username, :source_event, :created_at, :updated_at)
                ON CONFLICT(conflict_key) DO UPDATE SET
                    area_a_id = excluded.area_a_id,
                    area_b_id = excluded.area_b_id,
                    participants_json = excluded.participants_json,
                    area_ids_json = excluded.area_ids_json,
                    intersection_json = excluded.intersection_json,
                    intersections_json = excluded.intersections_json,
                    targets_json = excluded.targets_json,
                    status = excluded.status,
                    last_actor_username = excluded.last_actor_username,
                    source_event = excluded.source_event,
                    updated_at = excluded.updated_at
                """,
                data,
            )
            row = conn.execute(
                "SELECT * FROM territory_conflicts WHERE conflict_key = ?",
                (data["conflict_key"],),
            ).fetchone()
            return self._row_to_conflict(row)

    def list_active_for_player(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM territory_conflicts
                WHERE status = 'active'
                    AND (
                        player_a_username = ?
                        OR player_b_username = ?
                        OR participants_json LIKE ?
                    )
                ORDER BY updated_at DESC, id DESC
                """,
                (username, username, f'%"{username}"%'),
            ).fetchall()
            return [self._row_to_conflict(row) for row in rows]

    def get_by_key(self, conflict_key):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM territory_conflicts WHERE conflict_key = ?",
                (conflict_key,),
            ).fetchone()
            return self._row_to_conflict(row) if row else None

    def list_active(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM territory_conflicts
                WHERE status = 'active'
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
            return [self._row_to_conflict(row) for row in rows]

    def deactivate_stale_for_participants(self, participants, active_keys, source_event="conflict_refresh"):
        participants = {str(participant) for participant in (participants or []) if participant}
        if not participants:
            return 0
        active_keys = {str(key) for key in (active_keys or []) if key}

        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM territory_conflicts
                WHERE status = 'active'
                """
            ).fetchall()

            stale_ids = []
            for row in rows:
                conflict = self._row_to_conflict(row)
                conflict_participants = set(conflict.get("participants") or [])
                if not participants & conflict_participants:
                    continue
                if conflict.get("conflict_key") in active_keys:
                    continue
                stale_ids.append(conflict.get("id"))

            if not stale_ids:
                return 0

            placeholders = ",".join("?" for _ in stale_ids)
            conn.execute(
                f"""
                UPDATE territory_conflicts
                SET status = 'resolved',
                    source_event = ?,
                    updated_at = ?
                WHERE id IN ({placeholders})
                """,
                [source_event, utc_now(), *stale_ids],
            )
            return len(stale_ids)

    def delete_user_data(self, username):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM territory_conflicts
                WHERE player_a_username = ?
                    OR player_b_username = ?
                    OR participants_json LIKE ?
                """,
                (username, username, f'%"{username}"%'),
            )


class VulnerabilityStore:
    VALID_STATUSES = {"active", "withdrawn", "hacked"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _normalize_target(target):
        normalized = copy.deepcopy(target or {})
        lat = float(normalized.get("lat"))
        lng = float(normalized.get("lng", normalized.get("lon")))
        label = str(normalized.get("label") or normalized.get("name") or "Cel")
        normalized["lat"] = lat
        normalized["lng"] = lng
        normalized["label"] = label
        normalized["name"] = str(normalized.get("name") or label)
        normalized["icon"] = str(normalized.get("icon") or "📍")
        normalized["source_type"] = str(normalized.get("source_type") or "manual")
        normalized["generated"] = bool(normalized.get("generated", False))
        return normalized

    @staticmethod
    def _row_to_report(row):
        target = loads_json(row["target_json"], {})
        security = loads_json(row["security_json"], {})
        return {
            "id": row["id"],
            "target": target,
            "lat": row["target_lat"],
            "lng": row["target_lng"],
            "label": row["label"],
            "name": row["name"],
            "icon": row["icon"],
            "source_type": row["source_type"],
            "generated": bool(row["generated"]),
            "reported_by_username": row["reported_by_username"],
            "reported_by_clan": row["reported_by_clan"],
            "territory_owner_username": row["territory_owner_username"],
            "territory_owner_clan": row["territory_owner_clan"],
            "security": security,
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def report(self, target, reported_by_username, reported_by_clan, security,
               territory_owner_username="", territory_owner_clan=""):
        normalized = self._normalize_target(target)
        normalized["security"] = copy.deepcopy(security or {})
        now = utc_now()
        with db_connect(self.db_path) as conn:
            existing = conn.execute(
                """
                SELECT id, reported_by_username
                FROM reported_vulnerabilities
                WHERE ROUND(target_lat, 5) = ROUND(?, 5)
                    AND ROUND(target_lng, 5) = ROUND(?, 5)
                    AND label = ?
                    AND status = 'active'
                LIMIT 1
                """,
                (
                    normalized["lat"],
                    normalized["lng"],
                    normalized["label"],
                ),
            ).fetchone()

            if existing:
                if existing["reported_by_username"] != reported_by_username:
                    row = conn.execute(
                        "SELECT * FROM reported_vulnerabilities WHERE id = ?",
                        (existing["id"],),
                    ).fetchone()
                    return self._row_to_report(row)
                conn.execute(
                    """
                    UPDATE reported_vulnerabilities
                    SET name = ?, icon = ?, source_type = ?, generated = ?,
                        reported_by_username = ?, territory_owner_username = ?,
                        territory_owner_clan = ?, security_json = ?, target_json = ?,
                        updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        normalized["name"],
                        normalized["icon"],
                        normalized["source_type"],
                        1 if normalized["generated"] else 0,
                        reported_by_username,
                        territory_owner_username or "",
                        territory_owner_clan or "",
                        dumps_json(security or {}),
                        dumps_json(normalized),
                        now,
                        existing["id"],
                    ),
                )
                report_id = existing["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO reported_vulnerabilities
                        (target_lat, target_lng, label, name, icon, source_type,
                         generated, reported_by_username, reported_by_clan,
                         territory_owner_username, territory_owner_clan,
                         security_json, target_json, status, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                    """,
                    (
                        normalized["lat"],
                        normalized["lng"],
                        normalized["label"],
                        normalized["name"],
                        normalized["icon"],
                        normalized["source_type"],
                        1 if normalized["generated"] else 0,
                        reported_by_username,
                        reported_by_clan or "",
                        territory_owner_username or "",
                        territory_owner_clan or "",
                        dumps_json(security or {}),
                        dumps_json(normalized),
                        now,
                        now,
                    ),
                )
                report_id = cursor.lastrowid

            row = conn.execute(
                "SELECT * FROM reported_vulnerabilities WHERE id = ?",
                (report_id,),
            ).fetchone()
            return self._row_to_report(row)

    def get(self, report_id):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM reported_vulnerabilities WHERE id = ?",
                (report_id,),
            ).fetchone()
            return self._row_to_report(row) if row else None

    def list_active_for_clan(self, clan):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM reported_vulnerabilities
                WHERE reported_by_clan = ?
                    AND status = 'active'
                ORDER BY updated_at DESC, id DESC
                """,
                (clan or "",),
            ).fetchall()
            return [self._row_to_report(row) for row in rows]

    def list_active(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM reported_vulnerabilities
                WHERE status = 'active'
                ORDER BY updated_at DESC, id DESC
                """
            ).fetchall()
            return [self._row_to_report(row) for row in rows]

    def set_status(self, report_id, status):
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid vulnerability status: {status}")
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE reported_vulnerabilities
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, utc_now(), report_id),
            )
        return self.get(report_id)

    def withdraw(self, report_id, username):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT id
                FROM reported_vulnerabilities
                WHERE id = ?
                    AND reported_by_username = ?
                    AND status = 'active'
                """,
                (report_id, username),
            ).fetchone()
            if not row:
                return None
            conn.execute(
                """
                UPDATE reported_vulnerabilities
                SET status = 'withdrawn', updated_at = ?
                WHERE id = ?
                """,
                (utc_now(), report_id),
            )
        return self.get(report_id)

    def mark_hacked_by_target(self, lat, lng, label=None):
        params = [float(lat), float(lng)]
        query = """
            UPDATE reported_vulnerabilities
            SET status = 'hacked', updated_at = ?
            WHERE ROUND(target_lat, 5) = ROUND(?, 5)
                AND ROUND(target_lng, 5) = ROUND(?, 5)
                AND status = 'active'
        """
        params = [utc_now()] + params
        if label:
            query += " AND label = ?"
            params.append(label)
        with db_connect(self.db_path) as conn:
            conn.execute(query, params)


class WalletStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _profile_balance(profile):
        try:
            return int(profile.get("hackcoins", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def get_wallet(self, username, limit=20):
        with db_connect(self.db_path) as conn:
            user_row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            if not user_row:
                raise ValueError("Nie ma takiego uzytkownika.")

            profile = loads_json(user_row["profile_json"], {})
            rows = conn.execute(
                """
                SELECT id, from_username, to_username, amount, note, created_at
                FROM wallet_transactions
                WHERE from_username = ? OR to_username = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (username, username, int(limit)),
            ).fetchall()

            transactions = []
            for row in rows:
                outgoing = row["from_username"] == username
                transactions.append({
                    "id": row["id"],
                    "type": "outgoing" if outgoing else "incoming",
                    "peer": row["to_username"] if outgoing else row["from_username"],
                    "amount": int(row["amount"]),
                    "created_at": row["created_at"],
                    "note": row["note"] or "",
                })

            balance = WalletBalanceStore(self.db_path).get_balance(username, fallback_profile=profile)
            ledger_store = WalletLedgerStore(self.db_path)
            ledger = ledger_store.list_events(username, limit=limit)
            return {
                "balance": balance,
                "currency": "HC",
                "transactions": transactions,
                "ledger": ledger,
                "ledger_audit": ledger_store.audit_balance(username, balance),
            }

    def transfer(self, from_username, to_username, amount, note=""):
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise ValueError("Kwota musi byc liczba calkowita HC.")

        to_username = str(to_username or "").strip()
        note = str(note or "").strip()[:240]
        if amount <= 0:
            raise ValueError("Kwota musi byc dodatnia.")
        if not to_username:
            raise ValueError("Brak odbiorcy.")
        if from_username == to_username:
            raise ValueError("Nie mozna przelac HC samemu sobie.")

        now = utc_now()
        with db_connect(self.db_path) as conn:
            sender_row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (from_username,),
            ).fetchone()
            recipient_row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (to_username,),
            ).fetchone()
            if not sender_row:
                raise ValueError("Nadawca nie istnieje.")
            if not recipient_row:
                raise ValueError("Odbiorca nie istnieje.")

            sender_profile = loads_json(sender_row["profile_json"], {})
            recipient_profile = loads_json(recipient_row["profile_json"], {})
            sender_balance = self._profile_balance(sender_profile)
            recipient_balance = self._profile_balance(recipient_profile)
            if sender_balance < amount:
                raise ValueError("Brak srodkow.")

            sender_profile["hackcoins"] = sender_balance - amount
            recipient_profile["hackcoins"] = recipient_balance + amount
            conn.execute(
                "UPDATE users SET profile_json = ?, updated_at = ? WHERE username = ?",
                (dumps_json(sender_profile), now, from_username),
            )
            conn.execute(
                "UPDATE users SET profile_json = ?, updated_at = ? WHERE username = ?",
                (dumps_json(recipient_profile), now, to_username),
            )
            cursor = conn.execute(
                """
                INSERT INTO wallet_transactions
                    (from_username, to_username, amount, note, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (from_username, to_username, amount, note, now),
            )

            return {
                "balance": sender_profile["hackcoins"],
                "recipient_balance": recipient_profile["hackcoins"],
                "currency": "HC",
                "transaction": {
                    "id": cursor.lastrowid,
                    "type": "outgoing",
                    "peer": to_username,
                    "amount": amount,
                    "created_at": now,
                    "note": note,
                },
            }

    def technical_transfer(self, from_username, to_username, amount, note=""):
        try:
            amount = int(amount)
        except (TypeError, ValueError):
            raise ValueError("Kwota musi byc liczba calkowita HC.")

        from_username = str(from_username or "").strip()
        to_username = str(to_username or "").strip()
        note = str(note or "").strip()[:240]
        if amount < 0:
            raise ValueError("Kwota nie moze byc ujemna.")
        if not from_username or not to_username:
            raise ValueError("Brak stron transferu.")
        if from_username == to_username:
            raise ValueError("Nie mozna transferowac HC samemu sobie.")

        now = utc_now()
        with db_connect(self.db_path) as conn:
            source_row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (from_username,),
            ).fetchone()
            target_row = conn.execute(
                "SELECT profile_json FROM users WHERE username = ?",
                (to_username,),
            ).fetchone()
            if not source_row:
                raise ValueError("Zrodlo transferu nie istnieje.")
            if not target_row:
                raise ValueError("Odbiorca transferu nie istnieje.")

            source_profile = loads_json(source_row["profile_json"], {})
            target_profile = loads_json(target_row["profile_json"], {})
            source_balance = self._profile_balance(source_profile)
            target_balance = self._profile_balance(target_profile)
            amount = min(amount, source_balance)

            source_profile["hackcoins"] = source_balance - amount
            target_profile["hackcoins"] = target_balance + amount
            conn.execute(
                "UPDATE users SET profile_json = ?, updated_at = ? WHERE username = ?",
                (dumps_json(source_profile), now, from_username),
            )
            conn.execute(
                "UPDATE users SET profile_json = ?, updated_at = ? WHERE username = ?",
                (dumps_json(target_profile), now, to_username),
            )

            transaction_id = None
            if amount > 0:
                cursor = conn.execute(
                    """
                    INSERT INTO wallet_transactions
                        (from_username, to_username, amount, note, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (from_username, to_username, amount, note, now),
                )
                transaction_id = cursor.lastrowid

            return {
                "amount": amount,
                "source_balance": source_profile["hackcoins"],
                "target_balance": target_profile["hackcoins"],
                "transaction_id": transaction_id,
                "created_at": now,
            }


class PlayerHackAccessStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _parse_dt(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", ""))
        except ValueError:
            return None

    @classmethod
    def _seconds_until(cls, value):
        dt = cls._parse_dt(value)
        if not dt:
            return 0
        return max(0, int((dt - datetime.utcnow()).total_seconds()))

    @classmethod
    def _row_to_access(cls, row):
        if not row:
            return None
        return {
            "id": row["id"],
            "attacker_username": row["attacker_username"],
            "victim_username": row["victim_username"],
            "hacked_until": row["hacked_until"],
            "cooldown_until": row["cooldown_until"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "seconds_left": cls._seconds_until(row["hacked_until"]),
            "cooldown_seconds_left": cls._seconds_until(row["cooldown_until"]),
        }

    def grant_access(self, attacker_username, victim_username, access_minutes=5, cooldown_hours=3):
        attacker_username = str(attacker_username or "").strip()
        victim_username = str(victim_username or "").strip()
        if not attacker_username or not victim_username:
            raise ValueError("Brak gracza atakujacego albo celu.")
        if attacker_username == victim_username:
            raise ValueError("Nie mozna shackowac samego siebie.")

        now_dt = datetime.utcnow()
        now = now_dt.isoformat(timespec="seconds")
        hacked_until = (now_dt + timedelta(minutes=access_minutes)).isoformat(timespec="seconds")
        cooldown_until = (now_dt + timedelta(hours=cooldown_hours)).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO player_hack_access
                    (attacker_username, victim_username, hacked_until, cooldown_until, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(attacker_username, victim_username) DO UPDATE SET
                    hacked_until = excluded.hacked_until,
                    cooldown_until = excluded.cooldown_until,
                    updated_at = excluded.updated_at
                """,
                (attacker_username, victim_username, hacked_until, cooldown_until, now, now),
            )
            row = conn.execute(
                """
                SELECT * FROM player_hack_access
                WHERE attacker_username = ? AND victim_username = ?
                """,
                (attacker_username, victim_username),
            ).fetchone()
            access = self._row_to_access(row)
            if access and not access.get("id"):
                access["id"] = cursor.lastrowid
            return access

    def get_active_access(self, attacker_username, victim_username=None):
        now = utc_now()
        params = [attacker_username, now]
        where = "attacker_username = ? AND hacked_until > ?"
        if victim_username:
            where += " AND victim_username = ?"
            params.append(victim_username)
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                f"""
                SELECT * FROM player_hack_access
                WHERE {where}
                ORDER BY hacked_until DESC, id DESC
                LIMIT 1
                """,
                params,
            ).fetchone()
            return self._row_to_access(row)

    def get_cooldown(self, attacker_username, victim_username):
        now = utc_now()
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT * FROM player_hack_access
                WHERE attacker_username = ?
                  AND victim_username = ?
                  AND cooldown_until > ?
                LIMIT 1
                """,
                (attacker_username, victim_username, now),
            ).fetchone()
            return self._row_to_access(row)

    @staticmethod
    def access_key(access):
        if not access:
            return ""
        return f"{access.get('id') or ''}:{access.get('hacked_until') or ''}"

    def has_tool_usage(self, access, attacker_username, victim_username, tool_id):
        key = self.access_key(access)
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT 1 FROM player_hack_tool_usage
                WHERE attacker_username = ?
                  AND victim_username = ?
                  AND tool_id = ?
                  AND access_key = ?
                LIMIT 1
                """,
                (attacker_username, victim_username, tool_id, key),
            ).fetchone()
            return row is not None

    def record_tool_usage(self, access, attacker_username, victim_username, tool_id, result="", amount=0):
        key = self.access_key(access)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO player_hack_tool_usage
                    (access_id, attacker_username, victim_username, tool_id, access_key, result, amount, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    access.get("id") if access else None,
                    attacker_username,
                    victim_username,
                    tool_id,
                    key,
                    str(result or ""),
                    int(amount or 0),
                    now,
                ),
            )
            return {
                "id": cursor.lastrowid,
                "access_key": key,
                "created_at": now,
            }


class AppActionReceiptStore:
    STATUS_RECEIVED = "received"
    STATUS_STARTED = "started"
    STATUS_EFFECT_APPLIED = "effect_applied"
    STATUS_FAILED = "failed"

    ACTIVE_STATUSES = {STATUS_RECEIVED, STATUS_STARTED}
    COMPLETED_STATUSES = {STATUS_EFFECT_APPLIED, STATUS_FAILED}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @classmethod
    def _state_for_status(cls, status):
        status = cls._clean_text(status, cls.STATUS_STARTED)
        if status in cls.COMPLETED_STATUSES:
            return "completed"
        return "in_flight"

    @classmethod
    def _receipt_from_row(cls, row):
        if not row:
            return None
        status = row["status"]
        return {
            "state": cls._state_for_status(status),
            "receipt_key": row["receipt_key"],
            "username": row["username"],
            "app_id": row["app_id"],
            "action": row["action"],
            "target_key": row["target_key"],
            "source": row["source"],
            "status": status,
            "payload": loads_json(row["response_json"], {}),
            "status_code": int(row["status_code"] or 202),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "expires_at": float(row["expires_at"] or 0),
            "store": "sqlite",
        }

    def prune_expired(self, conn=None, now_ts=None):
        now_ts = float(now_ts if now_ts is not None else time.time())
        if conn is not None:
            conn.execute(
                "DELETE FROM app_action_receipts WHERE expires_at > 0 AND expires_at <= ?",
                (now_ts,),
            )
            return
        with db_connect(self.db_path) as own_conn:
            self.prune_expired(own_conn, now_ts)

    def begin(
        self,
        receipt_key,
        username="",
        app_id="",
        action="",
        target_key="",
        source="",
        ttl_seconds=90,
    ):
        receipt_key = self._clean_text(receipt_key)
        if not receipt_key:
            return "new", None

        now_text = utc_now()
        now_ts = time.time()
        expires_at = now_ts + max(1, int(ttl_seconds or 90))
        username = self._clean_text(username)
        app_id = self._clean_text(app_id)
        action = self._clean_text(action)
        target_key = self._clean_text(target_key)
        source = self._clean_text(source)

        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.prune_expired(conn, now_ts)
            existing = conn.execute(
                "SELECT * FROM app_action_receipts WHERE receipt_key = ?",
                (receipt_key,),
            ).fetchone()
            if existing:
                receipt = self._receipt_from_row(existing)
                return receipt["state"], receipt

            conn.execute(
                """
                INSERT INTO app_action_receipts
                    (receipt_key, username, app_id, action, target_key, source,
                     status, response_json, status_code, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, '{}', 202, ?, ?, ?)
                """,
                (
                    receipt_key,
                    username,
                    app_id,
                    action,
                    target_key,
                    source,
                    self.STATUS_STARTED,
                    now_text,
                    now_text,
                    expires_at,
                ),
            )
        return "new", None

    def finish(self, receipt_key, payload=None, status_code=200, ttl_seconds=90, status=None):
        receipt_key = self._clean_text(receipt_key)
        if not receipt_key:
            return
        now_text = utc_now()
        expires_at = time.time() + max(1, int(ttl_seconds or 90))
        status = self._clean_text(status, self.STATUS_EFFECT_APPLIED)
        with db_connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE app_action_receipts
                SET status = ?,
                    response_json = ?,
                    status_code = ?,
                    updated_at = ?,
                    expires_at = ?
                WHERE receipt_key = ?
                """,
                (
                    status,
                    dumps_json(payload or {}),
                    int(status_code or 200),
                    now_text,
                    expires_at,
                    receipt_key,
                ),
            )
            if cursor.rowcount == 0:
                conn.execute(
                    """
                    INSERT INTO app_action_receipts
                        (receipt_key, username, status, response_json, status_code, created_at, updated_at, expires_at)
                    VALUES (?, '', ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        receipt_key,
                        status,
                        dumps_json(payload or {}),
                        int(status_code or 200),
                        now_text,
                        now_text,
                        expires_at,
                    ),
                )

    def get(self, receipt_key):
        receipt_key = self._clean_text(receipt_key)
        if not receipt_key:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM app_action_receipts WHERE receipt_key = ?",
                (receipt_key,),
            ).fetchone()
            return self._receipt_from_row(row)

    def metrics(self):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS count
                FROM app_action_receipts
                GROUP BY status
                """
            ).fetchall()
            return {row["status"]: int(row["count"] or 0) for row in rows}

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM app_action_receipts")


class PlayerOperationStore:
    TERMINAL_STATUSES = {"cancelled", "canceled", "done", "completed", "failed", "expired", "timeout", "resolved", "detected"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @classmethod
    def _operation_id(cls, operation):
        operation = operation if isinstance(operation, dict) else {}
        value = cls._clean_text(operation.get("operation_id") or operation.get("id"))
        if value:
            return value
        raw = dumps_json(operation)
        return "op_" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

    @classmethod
    def _status(cls, operation):
        operation = operation if isinstance(operation, dict) else {}
        return cls._clean_text(operation.get("status"), "running").lower()

    @staticmethod
    def _is_expired(operation):
        operation = operation if isinstance(operation, dict) else {}
        value = operation.get("expires_at")
        if not value:
            return False
        try:
            raw = str(value)
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is not None:
                now = datetime.utcnow().replace(tzinfo=parsed.tzinfo)
            else:
                now = datetime.utcnow()
            return parsed <= now
        except (TypeError, ValueError):
            return False

    @classmethod
    def _target_key(cls, operation):
        operation = operation if isinstance(operation, dict) else {}
        target = operation.get("target") if isinstance(operation.get("target"), dict) else {}
        if operation.get("target_id"):
            return cls._clean_text(operation.get("target_id"))
        if target.get("target_id"):
            return cls._clean_text(target.get("target_id"))
        lat = target.get("lat", operation.get("lat"))
        lng = target.get("lng", target.get("lon", operation.get("lng", operation.get("lon"))))
        label = target.get("label") or target.get("name") or operation.get("target_label") or operation.get("target_id") or ""
        if lat is not None and lng is not None:
            return f"map:{lat}:{lng}:{label}"
        return cls._clean_text(label)

    @classmethod
    def _operation_type(cls, operation):
        operation = operation if isinstance(operation, dict) else {}
        return cls._clean_text(operation.get("operation_type") or operation.get("type"), "operation")

    @classmethod
    def _active_logical_key(cls, operation):
        status = cls._status(operation)
        if status in cls.TERMINAL_STATUSES or cls._is_expired(operation):
            return ""
        operation = operation if isinstance(operation, dict) else {}
        parts = (
            cls._target_key(operation),
            cls._clean_text(operation.get("map_action_id")),
            cls._operation_type(operation),
            cls._clean_text(operation.get("source_app_id") or operation.get("source_app_name")),
        )
        return "|".join(parts) if any(parts) else ""

    @staticmethod
    def _risk_json(operation):
        operation = operation if isinstance(operation, dict) else {}
        value = operation.get("operation_risk_meter") or operation.get("risk_state") or operation.get("risk") or {}
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _created_at(operation, now):
        operation = operation if isinstance(operation, dict) else {}
        return str(operation.get("created_at") or operation.get("started_at") or now)

    @classmethod
    def _row_to_operation(cls, row):
        if not row:
            return None
        operation = loads_json(row["operation_json"], {})
        if isinstance(operation, dict):
            operation.setdefault("operation_id", row["operation_id"])
            operation.setdefault("status", row["status"])
            operation.setdefault("operation_type", row["operation_type"])
            operation.setdefault("_runtime_version", int(row["version"] or 0))
            return operation
        return None

    def seed_from_profile(self, username, profile):
        profile = profile if isinstance(profile, dict) else {}
        operations = profile.get("operations", [])
        if not operations:
            return []
        return self.upsert_operations(username, operations, event_type="operation.seed", source="profile")

    def list_operations(self, username, include_terminal=True):
        username = self._clean_text(username)
        if not username:
            return []
        where = "username = ?"
        params = [username]
        if not include_terminal:
            placeholders = ",".join("?" for _ in self.TERMINAL_STATUSES)
            where += f" AND status NOT IN ({placeholders})"
            params.extend(sorted(self.TERMINAL_STATUSES))
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM player_operations
                WHERE {where}
                ORDER BY created_at, updated_at
                """,
                tuple(params),
            ).fetchall()
            return [
                operation for operation in (self._row_to_operation(row) for row in rows)
                if isinstance(operation, dict)
            ]

    def upsert_operations(self, username, operations, event_type="operation.upsert", source="", dedupe_key_prefix=""):
        username = self._clean_text(username)
        if not username:
            return []
        now = utc_now()
        accepted = []
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            active_rows = conn.execute(
                """
                SELECT operation_id, operation_json
                FROM player_operations
                WHERE username = ?
                """,
                (username,),
            ).fetchall()
            active_keys = {}
            for row in active_rows:
                existing_op = loads_json(row["operation_json"], {})
                key = self._active_logical_key(existing_op)
                if key:
                    active_keys[key] = row["operation_id"]

            for incoming in operations or []:
                if not isinstance(incoming, dict):
                    continue
                operation = dict(incoming)
                operation_id = self._operation_id(operation)
                operation["operation_id"] = operation_id
                status = self._status(operation)
                logical_key = self._active_logical_key(operation)
                if logical_key and active_keys.get(logical_key) not in {"", None, operation_id}:
                    continue

                dedupe_key = ""
                if dedupe_key_prefix:
                    dedupe_key = f"{dedupe_key_prefix}:{operation_id}:{status}"
                    if conn.execute(
                        "SELECT 1 FROM operation_events WHERE dedupe_key = ?",
                        (dedupe_key,),
                    ).fetchone():
                        continue

                existing = conn.execute(
                    "SELECT version, created_at FROM player_operations WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()
                version = int(existing["version"] or 0) + 1 if existing else 1
                created_at = existing["created_at"] if existing else self._created_at(operation, now)
                conn.execute(
                    """
                    INSERT INTO player_operations
                        (operation_id, username, target_key, operation_type, status,
                         operation_json, risk_json, version, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(operation_id) DO UPDATE SET
                        username = excluded.username,
                        target_key = excluded.target_key,
                        operation_type = excluded.operation_type,
                        status = excluded.status,
                        operation_json = excluded.operation_json,
                        risk_json = excluded.risk_json,
                        version = excluded.version,
                        updated_at = excluded.updated_at
                    """,
                    (
                        operation_id,
                        username,
                        self._target_key(operation),
                        self._operation_type(operation),
                        status,
                        dumps_json(operation),
                        dumps_json(self._risk_json(operation)),
                        version,
                        created_at,
                        now,
                    ),
                )
                event_id = f"opev_{hashlib.sha1(f'{operation_id}:{event_type}:{now}:{version}'.encode('utf-8')).hexdigest()[:18]}"
                conn.execute(
                    """
                    INSERT OR IGNORE INTO operation_events
                        (event_id, operation_id, event_type, dedupe_key, payload_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        operation_id,
                        self._clean_text(event_type, "operation.upsert"),
                        dedupe_key,
                        dumps_json({"source": source, "status": status, "operation_id": operation_id}),
                        now,
                    ),
                )
                if logical_key:
                    active_keys[logical_key] = operation_id
                accepted.append(operation)
        return accepted

    def cancel_operation(self, username, operation_id, cancelled_by="player"):
        username = self._clean_text(username)
        operation_id = self._clean_text(operation_id)
        if not username or not operation_id:
            return None, "missing_operation_id"
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_operations WHERE username = ? AND operation_id = ?",
                (username, operation_id),
            ).fetchone()
            if not row:
                return None, "not_found"
            operation = self._row_to_operation(row) or {}
            if self._status(operation) in self.TERMINAL_STATUSES:
                return operation, "already_terminal"
            operation["status"] = "cancelled"
            operation["ended_at"] = now
            operation["cancelled_at"] = now
            operation["cancelled_by"] = cancelled_by
            operation["remaining_seconds"] = 0
            operation["expired"] = True
            resource_buffer = operation.setdefault("resource_buffer", {})
            if isinstance(resource_buffer, dict):
                resource_buffer["cancelled"] = True
                resource_buffer.setdefault("files", [])
            version = int(row["version"] or 0) + 1
            conn.execute(
                """
                UPDATE player_operations
                SET status = 'cancelled',
                    operation_json = ?,
                    risk_json = ?,
                    version = ?,
                    updated_at = ?
                WHERE operation_id = ?
                """,
                (
                    dumps_json(operation),
                    dumps_json(self._risk_json(operation)),
                    version,
                    now,
                    operation_id,
                ),
            )
            event_id = f"opev_{hashlib.sha1(f'{operation_id}:cancel:{now}:{version}'.encode('utf-8')).hexdigest()[:18]}"
            conn.execute(
                """
                INSERT OR IGNORE INTO operation_events
                    (event_id, operation_id, event_type, dedupe_key, payload_json, created_at)
                VALUES (?, ?, 'operation.cancelled', ?, ?, ?)
                """,
                (
                    event_id,
                    operation_id,
                    f"cancel:{operation_id}",
                    dumps_json({"cancelled_by": cancelled_by}),
                    now,
                ),
            )
            return operation, "cancelled"

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM operation_events")
            conn.execute("DELETE FROM player_operations")


class SystemMessageStore:
    ACTIVE_STATUSES = {"pending", "delivered"}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @classmethod
    def _message_id(cls, username, message):
        message = message if isinstance(message, dict) else {}
        value = cls._clean_text(message.get("message_id") or message.get("id"))
        if value:
            return f"msg_{username}_{value}"
        raw = dumps_json({
            "username": username,
            "type": message.get("type"),
            "title": message.get("title"),
            "text": message.get("text") or message.get("body"),
            "created_at": message.get("created_at"),
        })
        return "msg_" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:18]

    @classmethod
    def _dedupe_key(cls, username, message):
        message = message if isinstance(message, dict) else {}
        key = cls._clean_text(message.get("dedupe_key"))
        if key:
            return key
        return cls._message_id(username, message)

    @staticmethod
    def _row_to_message(row):
        if not row:
            return None
        payload = loads_json(row["payload_json"], {})
        message = dict(payload) if isinstance(payload, dict) else {}
        message.setdefault("id", row["message_id"])
        message.setdefault("message_id", row["message_id"])
        message.setdefault("type", row["type"])
        message.setdefault("title", row["title"])
        message.setdefault("text", row["body"])
        message.setdefault("status", "new")
        message.setdefault("created_at", row["created_at"])
        return message

    def add_message(self, username, message, source="", ttl_seconds=None):
        username = self._clean_text(username)
        if not username or not isinstance(message, dict):
            return None, False
        now = utc_now()
        expires_at = 0
        if ttl_seconds:
            try:
                expires_at = time.time() + max(1, int(ttl_seconds))
            except (TypeError, ValueError):
                expires_at = 0
        payload = dict(message)
        message_id = self._message_id(username, payload)
        dedupe_key = self._dedupe_key(username, payload)
        title = self._clean_text(payload.get("title"))
        body = self._clean_text(payload.get("text") or payload.get("body"))
        msg_type = self._clean_text(payload.get("type"), "info")
        payload.setdefault("id", message_id)
        payload.setdefault("message_id", message_id)
        payload.setdefault("status", "new")
        payload.setdefault("created_at", now)
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                """
                SELECT * FROM system_messages
                WHERE username = ? AND dedupe_key = ?
                """,
                (username, dedupe_key),
            ).fetchone()
            if existing and existing["status"] in {"pending", "delivered", "consumed"}:
                return self._row_to_message(existing), False
            conn.execute(
                """
                INSERT INTO system_messages
                    (message_id, username, dedupe_key, title, body, type, source,
                     status, payload_json, created_at, expires_at, consumed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, NULL)
                ON CONFLICT(message_id) DO UPDATE SET
                    dedupe_key = excluded.dedupe_key,
                    title = excluded.title,
                    body = excluded.body,
                    type = excluded.type,
                    source = excluded.source,
                    expires_at = excluded.expires_at,
                    status = CASE
                        WHEN system_messages.status = 'consumed' THEN system_messages.status
                        ELSE 'pending'
                    END,
                    payload_json = excluded.payload_json
                """,
                (
                    message_id,
                    username,
                    dedupe_key,
                    title,
                    body,
                    msg_type,
                    self._clean_text(source or payload.get("source"), "system"),
                    dumps_json(payload),
                    str(payload.get("created_at") or now),
                    expires_at,
                ),
            )
        return payload, True

    def add_messages(self, username, messages, source=""):
        added = []
        for message in messages or []:
            payload, created = self.add_message(username, message, source=source)
            if created and payload:
                added.append(payload)
        return added

    def consume_pending(self, username, limit=50):
        username = self._clean_text(username)
        if not username:
            return []
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                UPDATE system_messages
                SET status = 'expired'
                WHERE username = ?
                  AND status IN ('pending', 'delivered')
                  AND expires_at > 0
                  AND expires_at <= ?
                """,
                (username, time.time()),
            )
            rows = conn.execute(
                """
                SELECT * FROM system_messages
                WHERE username = ? AND status IN ('pending', 'delivered')
                ORDER BY created_at, message_id
                LIMIT ?
                """,
                (username, max(1, int(limit or 50))),
            ).fetchall()
            if not rows:
                return []
            ids = [row["message_id"] for row in rows]
            conn.executemany(
                """
                UPDATE system_messages
                SET status = 'consumed', consumed_at = ?
                WHERE message_id = ?
                """,
                [(now, message_id) for message_id in ids],
            )
            return [
                message for message in (self._row_to_message(row) for row in rows)
                if isinstance(message, dict)
            ]

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM system_messages")


class PlayerInventoryStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _app_id(app):
        app = app if isinstance(app, dict) else {}
        value = str(app.get("id") or app.get("app_id") or "").strip()
        if value:
            return value
        name = str(app.get("name") or app.get("label") or "app").strip().lower()
        raw = dumps_json({"name": name, "runtime": app.get("runtime_file") or app.get("file_name")})
        return "app_" + hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]

    @staticmethod
    def _tool_id(tool, app=None):
        if isinstance(tool, dict):
            value = str(tool.get("id") or tool.get("tool_id") or tool.get("file") or tool.get("name") or "").strip()
        else:
            value = str(tool or "").strip()
        if value:
            return value
        app_id = PlayerInventoryStore._app_id(app or {})
        return f"{app_id}.sh"

    @staticmethod
    def _storage_from_profile(profile):
        profile = profile if isinstance(profile, dict) else {}
        try:
            capacity = int(profile.get("storage_capacity") or 0)
        except (TypeError, ValueError):
            capacity = 0
        try:
            used = int(profile.get("storage_used") or 0)
        except (TypeError, ValueError):
            used = 0
        return {
            "capacity": max(0, capacity),
            "used": max(0, used),
            "unit": str(profile.get("storage_unit") or "MB"),
            "modifiers": {
                "storage_upgrades": profile.get("storage_upgrades", []),
                "googleplex_products": profile.get("googleplex_products", []),
                "storage_soft_limit": profile.get("storage_soft_limit", True),
                "storage_over_limit": profile.get("storage_over_limit", False),
            },
        }

    @staticmethod
    def _row_to_app(row):
        if not row:
            return None
        app = loads_json(row["app_json"], {})
        if isinstance(app, dict):
            app.setdefault("id", row["app_id"])
            app.setdefault("status", row["status"])
            return app
        return None

    @staticmethod
    def _row_to_tool(row):
        if not row:
            return None
        tool = loads_json(row["tool_json"], {})
        if isinstance(tool, dict):
            tool.setdefault("id", row["tool_id"])
            tool.setdefault("tool_id", row["tool_id"])
            tool.setdefault("app_id", row["app_id"])
            return tool
        return {"id": row["tool_id"], "tool_id": row["tool_id"], "app_id": row["app_id"], "name": row["tool_id"]}

    def seed_from_profile(self, username, profile):
        username = self._clean_text(username)
        if not username or not isinstance(profile, dict):
            return self.snapshot(username)
        apps = profile.get("apps", [])
        files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
        tools = files.get("tools", []) if isinstance(files, dict) else []
        storage = self._storage_from_profile(profile)
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            for app in apps or []:
                if not isinstance(app, dict):
                    continue
                app_id = self._app_id(app)
                existing = conn.execute(
                    "SELECT version FROM player_apps WHERE username = ? AND app_id = ?",
                    (username, app_id),
                ).fetchone()
                version = int(existing["version"] or 0) + 1 if existing else 1
                conn.execute(
                    """
                    INSERT INTO player_apps
                        (username, app_id, app_json, status, version, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(username, app_id) DO UPDATE SET
                        app_json = excluded.app_json,
                        status = excluded.status,
                        version = excluded.version,
                        updated_at = excluded.updated_at
                    """,
                    (
                        username,
                        app_id,
                        dumps_json(dict(app)),
                        self._clean_text(app.get("status"), "installed"),
                        version,
                        now,
                    ),
                )
            for tool in tools or []:
                tool_id = self._tool_id(tool)
                payload = dict(tool) if isinstance(tool, dict) else {"name": tool_id, "file": tool_id}
                app_id = self._clean_text(payload.get("app_id") or payload.get("source_app_id"))
                existing = conn.execute(
                    "SELECT version FROM player_tool_files WHERE username = ? AND tool_id = ?",
                    (username, tool_id),
                ).fetchone()
                version = int(existing["version"] or 0) + 1 if existing else 1
                conn.execute(
                    """
                    INSERT INTO player_tool_files
                        (username, tool_id, app_id, tool_json, version, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(username, tool_id) DO UPDATE SET
                        app_id = excluded.app_id,
                        tool_json = excluded.tool_json,
                        version = excluded.version,
                        updated_at = excluded.updated_at
                    """,
                    (username, tool_id, app_id, dumps_json(payload), version, now),
                )
            row = conn.execute(
                "SELECT version FROM player_storage WHERE username = ?",
                (username,),
            ).fetchone()
            version = int(row["version"] or 0) + 1 if row else 1
            conn.execute(
                """
                INSERT INTO player_storage
                    (username, capacity, used, unit, modifiers_json, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    capacity = excluded.capacity,
                    used = excluded.used,
                    unit = excluded.unit,
                    modifiers_json = excluded.modifiers_json,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    storage["capacity"],
                    storage["used"],
                    storage["unit"],
                    dumps_json(storage["modifiers"]),
                    version,
                    now,
                ),
            )
        return self.snapshot(username)

    def snapshot(self, username):
        username = self._clean_text(username)
        if not username:
            return {"apps": [], "files": {"tools": []}, "storage": None}
        with db_connect(self.db_path) as conn:
            app_rows = conn.execute(
                """
                SELECT * FROM player_apps
                WHERE username = ? AND status != 'uninstalled'
                ORDER BY updated_at, app_id
                """,
                (username,),
            ).fetchall()
            tool_rows = conn.execute(
                """
                SELECT * FROM player_tool_files
                WHERE username = ?
                ORDER BY updated_at, tool_id
                """,
                (username,),
            ).fetchall()
            storage_row = conn.execute(
                "SELECT * FROM player_storage WHERE username = ?",
                (username,),
            ).fetchone()
        storage = None
        if storage_row:
            storage = {
                "capacity": int(storage_row["capacity"] or 0),
                "used": int(storage_row["used"] or 0),
                "unit": storage_row["unit"] or "MB",
                "modifiers": loads_json(storage_row["modifiers_json"], {}),
                "version": int(storage_row["version"] or 0),
            }
        return {
            "apps": [app for app in (self._row_to_app(row) for row in app_rows) if isinstance(app, dict)],
            "files": {"tools": [tool for tool in (self._row_to_tool(row) for row in tool_rows) if tool is not None]},
            "storage": storage,
        }

    def mirror_profile(self, username, profile):
        snapshot = self.snapshot(username)
        if not snapshot.get("apps") and not (snapshot.get("files") or {}).get("tools") and not snapshot.get("storage"):
            snapshot = self.seed_from_profile(username, profile)
        if not isinstance(profile, dict):
            return profile
        if snapshot.get("apps"):
            profile["apps"] = snapshot["apps"]
        files = profile.get("files") if isinstance(profile.get("files"), dict) else {}
        tools = (snapshot.get("files") or {}).get("tools")
        if tools:
            files["tools"] = tools
            profile["files"] = files
        storage = snapshot.get("storage")
        if storage:
            profile["storage_capacity"] = storage.get("capacity", profile.get("storage_capacity"))
            profile["storage_used"] = storage.get("used", profile.get("storage_used"))
            profile["storage_unit"] = storage.get("unit", profile.get("storage_unit", "MB"))
            modifiers = storage.get("modifiers") if isinstance(storage.get("modifiers"), dict) else {}
            for key in ("storage_upgrades", "googleplex_products", "storage_soft_limit", "storage_over_limit"):
                if key in modifiers:
                    profile[key] = modifiers[key]
        return profile

    def write_from_profile(self, username, profile):
        return self.seed_from_profile(username, profile)

    def uninstall_app(self, username, app_id="", tool_id=""):
        username = self._clean_text(username)
        app_id = self._clean_text(app_id)
        tool_id = self._clean_text(tool_id)
        if not username:
            return False
        now = utc_now()
        changed = False
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if app_id:
                row = conn.execute(
                    "SELECT version FROM player_apps WHERE username = ? AND app_id = ?",
                    (username, app_id),
                ).fetchone()
                if row:
                    conn.execute(
                        """
                        UPDATE player_apps
                        SET status = 'uninstalled', version = ?, updated_at = ?
                        WHERE username = ? AND app_id = ?
                        """,
                        (int(row["version"] or 0) + 1, now, username, app_id),
                    )
                    changed = True
                conn.execute(
                    "DELETE FROM player_tool_files WHERE username = ? AND app_id = ?",
                    (username, app_id),
                )
            if tool_id:
                cursor = conn.execute(
                    "DELETE FROM player_tool_files WHERE username = ? AND tool_id = ?",
                    (username, tool_id),
                )
                changed = changed or cursor.rowcount > 0
        return changed

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM player_tool_files")
            conn.execute("DELETE FROM player_apps")
            conn.execute("DELETE FROM player_storage")


class WalletLedgerStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return default

    def _row_to_event(self, row):
        if not row:
            return None
        payload = loads_json(row["payload_json"], {}) or {}
        return {
            "ledger_id": row["ledger_id"],
            "username": row["username"],
            "event_type": row["event_type"],
            "amount_delta": int(row["amount_delta"] or 0),
            "balance_after": int(row["balance_after"] or 0),
            "source": row["source"] or "",
            "source_id": row["source_id"] or "",
            "peer_username": row["peer_username"] or "",
            "note": row["note"] or "",
            "dedupe_key": row["dedupe_key"] or "",
            "payload": payload,
            "created_at": row["created_at"],
        }

    def has_events(self, username):
        username = self._clean_text(username)
        if not username:
            return False
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM wallet_ledger WHERE username = ? LIMIT 1",
                (username,),
            ).fetchone()
        return bool(row)

    def record_event(
        self,
        username,
        event_type,
        amount_delta,
        balance_after,
        source="",
        source_id="",
        peer_username="",
        note="",
        dedupe_key="",
        payload=None,
        created_at=None,
    ):
        username = self._clean_text(username)
        if not username:
            return None
        event_type = self._clean_text(event_type, "wallet.balance_changed")
        amount_delta = self._safe_int(amount_delta)
        balance_after = max(0, self._safe_int(balance_after))
        source = self._clean_text(source)
        source_id = self._clean_text(source_id)
        peer_username = self._clean_text(peer_username)
        note = self._clean_text(note)[:240]
        dedupe_key = self._clean_text(
            dedupe_key,
            f"wallet_ledger:{username}:{event_type}:{source}:{source_id}:{balance_after}",
        )
        created_at = self._clean_text(created_at, utc_now())
        payload_json = dumps_json(payload if isinstance(payload, dict) else {})
        ledger_id = f"wl_{hashlib.sha1(f'{username}:{dedupe_key}'.encode('utf-8')).hexdigest()[:18]}"

        with db_connect(self.db_path) as conn:
            row = self.record_event_with_conn(
                conn,
                username=username,
                event_type=event_type,
                amount_delta=amount_delta,
                balance_after=balance_after,
                source=source,
                source_id=source_id,
                peer_username=peer_username,
                note=note,
                dedupe_key=dedupe_key,
                payload_json=payload_json,
                created_at=created_at,
                ledger_id=ledger_id,
            )
        return self._row_to_event(row)

    def record_event_with_conn(
        self,
        conn,
        username,
        event_type,
        amount_delta,
        balance_after,
        source="",
        source_id="",
        peer_username="",
        note="",
        dedupe_key="",
        payload_json="{}",
        created_at=None,
        ledger_id=None,
    ):
        username = self._clean_text(username)
        event_type = self._clean_text(event_type, "wallet.balance_changed")
        source = self._clean_text(source)
        source_id = self._clean_text(source_id)
        peer_username = self._clean_text(peer_username)
        note = self._clean_text(note)[:240]
        dedupe_key = self._clean_text(
            dedupe_key,
            f"wallet_ledger:{username}:{event_type}:{source}:{source_id}:{balance_after}",
        )
        created_at = self._clean_text(created_at, utc_now())
        ledger_id = ledger_id or f"wl_{hashlib.sha1(f'{username}:{dedupe_key}'.encode('utf-8')).hexdigest()[:18]}"
        conn.execute(
            """
            INSERT OR IGNORE INTO wallet_ledger
                (ledger_id, username, event_type, amount_delta, balance_after,
                 source, source_id, peer_username, note, dedupe_key, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ledger_id,
                username,
                event_type,
                int(amount_delta or 0),
                max(0, int(balance_after or 0)),
                source,
                source_id,
                peer_username,
                note,
                dedupe_key,
                payload_json or "{}",
                created_at,
            ),
        )
        return conn.execute(
            """
            SELECT ledger_id, username, event_type, amount_delta, balance_after,
                   source, source_id, peer_username, note, dedupe_key, payload_json, created_at
            FROM wallet_ledger
            WHERE username = ? AND dedupe_key = ?
            """,
            (username, dedupe_key),
        ).fetchone()

    def list_events(self, username, limit=50):
        username = self._clean_text(username)
        try:
            limit = max(1, min(200, int(limit or 50)))
        except (TypeError, ValueError):
            limit = 50
        if not username:
            return []
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT ledger_id, username, event_type, amount_delta, balance_after,
                       source, source_id, peer_username, note, dedupe_key, payload_json, created_at
                FROM wallet_ledger
                WHERE username = ?
                ORDER BY created_at DESC, ledger_id DESC
                LIMIT ?
                """,
                (username, limit),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def ledger_balance(self, username):
        username = self._clean_text(username)
        if not username:
            return 0
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(SUM(amount_delta), 0) AS balance FROM wallet_ledger WHERE username = ?",
                (username,),
            ).fetchone()
        return int((row or {})["balance"] or 0)

    def audit_balance(self, username, current_balance):
        current_balance = max(0, self._safe_int(current_balance))
        ledger_balance = self.ledger_balance(username)
        return {
            "ledger_balance": ledger_balance,
            "current_balance": current_balance,
            "difference": current_balance - ledger_balance,
            "ok": ledger_balance == current_balance,
        }


class WalletBalanceStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _profile_balance(profile):
        try:
            return int((profile or {}).get("hackcoins", 0) or 0)
        except (TypeError, ValueError):
            return 0

    def seed_from_profile(self, username, profile):
        return self.set_balance(username, self._profile_balance(profile), transaction_key=f"seed:{username}", reason="profile_seed")

    def get_balance(self, username, fallback_profile=None):
        username = self._clean_text(username)
        if not username:
            return 0
        fallback_has_balance = isinstance(fallback_profile, dict) and "hackcoins" in fallback_profile
        fallback_balance = self._profile_balance(fallback_profile) if fallback_has_balance else None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT balance FROM wallet_balances WHERE username = ?",
                (username,),
            ).fetchone()
        if row:
            stored_balance = int(row["balance"] or 0)
            if fallback_has_balance and stored_balance != fallback_balance:
                return self.set_balance(
                    username,
                    fallback_balance,
                    transaction_key=f"profile_reconcile:{username}:{fallback_balance}",
                    reason="profile_reconcile",
                )
            ledger = WalletLedgerStore(self.db_path)
            if stored_balance > 0 and not ledger.has_events(username):
                ledger.record_event(
                    username,
                    "wallet.seed",
                    stored_balance,
                    stored_balance,
                    source="wallet_balance_store",
                    source_id="existing_balance",
                    dedupe_key=f"wallet:ledger:{username}:seed",
                    note="Stan poczatkowy portfela przed ledgerem.",
                )
            return stored_balance
        if fallback_profile is not None:
            return self.seed_from_profile(username, fallback_profile)
        return 0

    def set_balance(self, username, balance, transaction_key="", reason=""):
        username = self._clean_text(username)
        if not username:
            return 0
        try:
            balance = int(balance or 0)
        except (TypeError, ValueError):
            balance = 0
        balance = max(0, balance)
        now = utc_now()
        ledger = WalletLedgerStore(self.db_path)
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT balance, version FROM wallet_balances WHERE username = ?",
                (username,),
            ).fetchone()
            previous = int(existing["balance"] or 0) if existing else 0
            if transaction_key:
                event_row = conn.execute(
                    "SELECT balance FROM wallet_balance_events WHERE username = ? AND transaction_key = ?",
                    (username, transaction_key),
                ).fetchone()
                if event_row:
                    return int(event_row["balance"] or balance)
            version = int(existing["version"] or 0) + 1 if existing else 1
            has_ledger_events = bool(conn.execute(
                "SELECT 1 FROM wallet_ledger WHERE username = ? LIMIT 1",
                (username,),
            ).fetchone())
            if existing and previous > 0 and not has_ledger_events:
                ledger.record_event_with_conn(
                    conn,
                    username=username,
                    event_type="wallet.seed",
                    amount_delta=previous,
                    balance_after=previous,
                    source="wallet_balance_store",
                    source_id="existing_balance",
                    note="Stan poczatkowy portfela przed ledgerem.",
                    dedupe_key=f"wallet:ledger:{username}:seed",
                    created_at=now,
                )
            conn.execute(
                """
                INSERT INTO wallet_balances(username, balance, version, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    balance = excluded.balance,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (username, balance, version, now),
            )
            event_id = f"wbe_{hashlib.sha1(f'{username}:{transaction_key}:{now}:{balance}'.encode('utf-8')).hexdigest()[:18]}"
            conn.execute(
                """
                INSERT OR IGNORE INTO wallet_balance_events
                    (event_id, username, transaction_key, amount_delta, balance, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    username,
                    self._clean_text(transaction_key),
                    balance - previous,
                    balance,
                    self._clean_text(reason),
                    now,
                ),
            )
            delta = balance - previous
            if delta != 0 or transaction_key:
                ledger.record_event_with_conn(
                    conn,
                    username=username,
                    event_type=self._clean_text(reason, "wallet.balance_changed"),
                    amount_delta=delta,
                    balance_after=balance,
                    source="wallet_balance_store",
                    source_id=self._clean_text(transaction_key),
                    note=self._clean_text(reason),
                    dedupe_key=f"wallet:ledger:{username}:{self._clean_text(transaction_key, f'{reason}:{balance}:{now}')}",
                    payload_json=dumps_json({
                        "reason": self._clean_text(reason),
                        "transaction_key": self._clean_text(transaction_key),
                        "previous_balance": previous,
                    }),
                    created_at=now,
                )
        return balance

    def mirror_profile(self, username, profile):
        if isinstance(profile, dict):
            profile["hackcoins"] = self.get_balance(username, fallback_profile=profile)
        return profile

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM wallet_ledger")
            conn.execute("DELETE FROM wallet_balance_events")
            conn.execute("DELETE FROM wallet_balances")


class PlayerTargetRuntimeStore:
    STATUS_CLEARED = "cleared"
    STATUS_AIMED = "aimed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_CAPTURED = "captured"

    TERMINAL_STATUSES = {STATUS_CLEARED, STATUS_CAPTURED}

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @staticmethod
    def _is_missing_target_name(value):
        if value is None:
            return True
        normalized = str(value).strip().lower()
        return normalized in {
            "",
            "brak",
            "brak nazwy",
            "brak_nazwy",
            "no name",
            "unnamed",
            "unnamed target",
            "unknown",
            "none",
            "null",
        }

    @staticmethod
    def _is_placeholder_target_key(value):
        normalized = str(value or "").strip().lower()
        if not normalized:
            return True
        if normalized in {
            "map:0.0:0.0:target",
            "map:0:0:target",
            "map:unknown:unknown:target",
        }:
            return True
        parts = normalized.split(":")
        if len(parts) >= 4 and parts[0] == "map":
            missing_coord = {"0", "0.0", "0.00", "unknown", "none", "null"}
            missing_label = {"", "target", "brak", "unknown", "none", "null"}
            return parts[1] in missing_coord and parts[2] in missing_coord and ":".join(parts[3:]) in missing_label
        return False

    @staticmethod
    def target_key(target):
        target = target if isinstance(target, dict) else {}
        if target.get("target_id"):
            key = str(target.get("target_id"))
            return "" if PlayerTargetRuntimeStore._is_placeholder_target_key(key) else key
        if target.get("target_mode") == "player" and target.get("target_username"):
            return f"player:{target.get('target_username')}"
        if target.get("vulnerability_id"):
            return f"vulnerability:{target.get('vulnerability_id')}"
        if target.get("foreign_area_id"):
            lat = target.get("lat")
            lng = target.get("lng", target.get("lon"))
            return f"territory_contest:{target.get('foreign_area_id')}:{lat}:{lng}"
        lat = target.get("lat")
        lng = target.get("lng", target.get("lon"))
        label = target.get("label") or target.get("name") or target.get("source_type") or "target"
        key = f"map:{lat}:{lng}:{label}"
        return "" if PlayerTargetRuntimeStore._is_placeholder_target_key(key) else key

    @classmethod
    def _progress_from_target(cls, target):
        target = target if isinstance(target, dict) else {}
        allowed = target.get("actions_allowed") or {}
        if not isinstance(allowed, dict):
            allowed = {}
        security = target.get("security") or {}
        if not isinstance(security, dict):
            security = {}
        allowed_score = sum(1 for value in allowed.values() if value is True)
        disabled_score = sum(1 for value in security.values() if value is False)
        return int(max(allowed_score, disabled_score))

    @staticmethod
    def _merge_actions(current, incoming):
        merged = dict(current or {}) if isinstance(current, dict) else {}
        if isinstance(incoming, dict):
            for key, value in incoming.items():
                if value is True or key not in merged:
                    merged[key] = value
        return merged

    @staticmethod
    def _merge_security(current, incoming):
        merged = dict(current or {}) if isinstance(current, dict) else {}
        if isinstance(incoming, dict):
            for key, value in incoming.items():
                if value is False or key not in merged:
                    merged[key] = value
        return merged

    @classmethod
    def _row_payload(cls, row):
        if not row:
            return None
        target = loads_json(row["target_json"], {})
        security = loads_json(row["security_json"], {})
        actions_allowed = loads_json(row["actions_allowed_json"], {})
        if isinstance(target, dict) and target:
            target["security"] = security if isinstance(security, dict) else {}
            target["actions_allowed"] = actions_allowed if isinstance(actions_allowed, dict) else {}
            target["target_id"] = target.get("target_id") or row["target_key"]
        return {
            "username": row["username"],
            "target_key": row["target_key"],
            "target": target if isinstance(target, dict) else {},
            "security": security if isinstance(security, dict) else {},
            "actions_allowed": actions_allowed if isinstance(actions_allowed, dict) else {},
            "disarm_progress": int(row["disarm_progress"] or 0),
            "status": row["status"],
            "version": int(row["version"] or 0),
            "updated_at": row["updated_at"],
        }

    def _record_event(self, conn, username, event_type, target_key, version, payload=None):
        conn.execute(
            """
            INSERT INTO player_target_events
                (username, event_type, target_key, version, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                username,
                event_type,
                target_key or "",
                int(version or 0),
                dumps_json(payload or {}),
                utc_now(),
            ),
        )

    def get(self, username):
        username = self._clean_text(username)
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            return self._row_payload(row)

    def get_active_target(self, username):
        payload = self.get(username)
        if not payload or payload.get("status") in self.TERMINAL_STATUSES:
            return {}
        return dict(payload.get("target") or {})

    def upsert_aimed(self, username, target, status=STATUS_AIMED, source=""):
        username = self._clean_text(username)
        target = dict(target or {}) if isinstance(target, dict) else {}
        target_key = self.target_key(target)
        if not username or not target_key:
            return {"changed": False, "target": target, "status": "invalid", "version": 0}

        incoming_security = target.get("security") if isinstance(target.get("security"), dict) else {}
        incoming_actions = target.get("actions_allowed") if isinstance(target.get("actions_allowed"), dict) else {}
        incoming_progress = self._progress_from_target(target)
        now = utc_now()

        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            current = self._row_payload(row)
            if current and current.get("target_key") == target_key and current.get("status") == self.STATUS_CAPTURED:
                self._record_event(conn, username, "target.aimed_rejected", target_key, current.get("version"), {"source": source})
                return {
                    "changed": False,
                    "target": {},
                    "status": "captured",
                    "version": current.get("version", 0),
                }

            if current and current.get("target_key") == target_key:
                merged_security = self._merge_security(current.get("security"), incoming_security)
                merged_actions = self._merge_actions(current.get("actions_allowed"), incoming_actions)
                merged_target = dict(current.get("target") or {})
                for key, value in target.items():
                    if key in {"display_label", "label", "name", "title"} and self._is_missing_target_name(value):
                        continue
                    merged_target[key] = value
                merged_target["security"] = merged_security
                merged_target["actions_allowed"] = merged_actions
                progress = max(int(current.get("disarm_progress") or 0), incoming_progress)
                version = int(current.get("version") or 0) + 1
            else:
                merged_security = dict(incoming_security or {})
                merged_actions = dict(incoming_actions or {})
                merged_target = dict(target)
                merged_target["security"] = merged_security
                merged_target["actions_allowed"] = merged_actions
                progress = incoming_progress
                version = int(current.get("version") or 0) + 1 if current else 1

            merged_target["target_id"] = merged_target.get("target_id") or target_key
            conn.execute(
                """
                INSERT INTO player_target_runtime
                    (username, target_key, target_json, security_json, actions_allowed_json,
                     disarm_progress, status, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    target_key = excluded.target_key,
                    target_json = excluded.target_json,
                    security_json = excluded.security_json,
                    actions_allowed_json = excluded.actions_allowed_json,
                    disarm_progress = excluded.disarm_progress,
                    status = excluded.status,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    target_key,
                    dumps_json(merged_target),
                    dumps_json(merged_security),
                    dumps_json(merged_actions),
                    progress,
                    self._clean_text(status, self.STATUS_AIMED),
                    version,
                    now,
                ),
            )
            event_type = "target.progressed" if current and current.get("target_key") == target_key else "target.aimed"
            self._record_event(conn, username, event_type, target_key, version, {"source": source})
            return {
                "changed": True,
                "target": merged_target,
                "status": self._clean_text(status, self.STATUS_AIMED),
                "version": version,
            }

    def mark_captured(self, username, target, source=""):
        return self._terminal_update(username, target, self.STATUS_CAPTURED, "target.captured", source)

    def clear_if_matches(self, username, reference_target, source=""):
        username = self._clean_text(username)
        reference_key = self.target_key(reference_target)
        if not username:
            return False
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            current = self._row_payload(row)
            if not current:
                return False
            if reference_key and current.get("target_key") != reference_key:
                return False
            version = int(current.get("version") or 0) + 1
            now = utc_now()
            conn.execute(
                """
                UPDATE player_target_runtime
                SET target_json = '{}',
                    security_json = '{}',
                    actions_allowed_json = '{}',
                    disarm_progress = 0,
                    status = ?,
                    version = ?,
                    updated_at = ?
                WHERE username = ?
                """,
                (self.STATUS_CLEARED, version, now, username),
            )
            self._record_event(conn, username, "target.cleared", current.get("target_key"), version, {"source": source})
            return True

    def _terminal_update(self, username, target, status, event_type, source=""):
        username = self._clean_text(username)
        target = dict(target or {}) if isinstance(target, dict) else {}
        target_key = self.target_key(target)
        if not username or not target_key:
            return {"changed": False, "target": {}, "status": "invalid", "version": 0}
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_target_runtime WHERE username = ?",
                (username,),
            ).fetchone()
            current = self._row_payload(row)
            version = int((current or {}).get("version") or 0) + 1
            conn.execute(
                """
                INSERT INTO player_target_runtime
                    (username, target_key, target_json, security_json, actions_allowed_json,
                     disarm_progress, status, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    target_key = excluded.target_key,
                    target_json = excluded.target_json,
                    security_json = excluded.security_json,
                    actions_allowed_json = excluded.actions_allowed_json,
                    disarm_progress = excluded.disarm_progress,
                    status = excluded.status,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    target_key,
                    dumps_json(target),
                    dumps_json(target.get("security") if isinstance(target.get("security"), dict) else {}),
                    dumps_json(target.get("actions_allowed") if isinstance(target.get("actions_allowed"), dict) else {}),
                    self._progress_from_target(target),
                    status,
                    version,
                    now,
                ),
            )
            self._record_event(conn, username, event_type, target_key, version, {"source": source})
            return {"changed": True, "target": target, "status": status, "version": version}

    def seed_from_profile(self, username, profile):
        if self.get(username):
            return self.get_active_target(username)
        target = (profile or {}).get("aimed_target") if isinstance(profile, dict) else {}
        if not isinstance(target, dict) or not target:
            return {}
        return self.upsert_aimed(username, target, source="profile_fallback").get("target") or {}

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM player_target_runtime")
            conn.execute("DELETE FROM player_target_events")


class PlayerPositionStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    @staticmethod
    def _normalize(position):
        if not isinstance(position, dict):
            return {}
        try:
            lat = float(position.get("lat"))
            lng = float(position.get("lng", position.get("lon")))
        except (TypeError, ValueError):
            return {}
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return {}
        return {"lat": lat, "lng": lng}

    @staticmethod
    def _row_payload(row):
        if not row:
            return None
        return {
            "username": row["username"],
            "lat": float(row["lat"]),
            "lng": float(row["lng"]),
            "source": row["source"],
            "version": int(row["version"] or 0),
            "updated_at": row["updated_at"],
        }

    def get(self, username):
        username = str(username or "").strip()
        if not username:
            return None
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM player_positions WHERE username = ?",
                (username,),
            ).fetchone()
            return self._row_payload(row)

    def get_position(self, username):
        row = self.get(username)
        if not row:
            return {}
        return {"lat": row["lat"], "lng": row["lng"]}

    def upsert(self, username, position, source="runtime"):
        username = str(username or "").strip()
        normalized = self._normalize(position)
        if not username or not normalized:
            return {"changed": False, "position": {}, "version": 0, "updated_at": ""}
        now = utc_now()
        with db_connect(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM player_positions WHERE username = ?",
                (username,),
            ).fetchone()
            current = self._row_payload(row)
            if current:
                same_lat = abs(float(current.get("lat", 0)) - normalized["lat"]) < 0.0000001
                same_lng = abs(float(current.get("lng", 0)) - normalized["lng"]) < 0.0000001
                if same_lat and same_lng:
                    return {
                        "changed": False,
                        "position": {"lat": float(current["lat"]), "lng": float(current["lng"])},
                        "version": int(current.get("version") or 0),
                        "updated_at": current.get("updated_at") or "",
                    }
            version = int((current or {}).get("version") or 0) + 1
            conn.execute(
                """
                INSERT INTO player_positions
                    (username, lat, lng, source, version, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    lat = excluded.lat,
                    lng = excluded.lng,
                    source = excluded.source,
                    version = excluded.version,
                    updated_at = excluded.updated_at
                """,
                (
                    username,
                    normalized["lat"],
                    normalized["lng"],
                    str(source or "runtime"),
                    version,
                    now,
                ),
            )
            return {
                "changed": True,
                "position": normalized,
                "version": version,
                "updated_at": now,
            }

    def seed_from_profile(self, username, profile, source="profile_fallback"):
        if self.get(username):
            return self.get_position(username)
        profile = profile if isinstance(profile, dict) else {}
        position = profile.get("curently_possition") or profile.get("current_position") or {}
        result = self.upsert(username, position, source=source)
        return result.get("position") or {}

    def clear_all(self):
        with db_connect(self.db_path) as conn:
            conn.execute("DELETE FROM player_positions")


class MailStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        init_db(self.db_path)

    def ensure_seeded(self, username, profile=None, default_contacts=None, default_messages=None):
        seed_key = f"mail_seed:{username}"
        with db_connect(self.db_path) as conn:
            seeded = conn.execute(
                "SELECT 1 FROM kv_store WHERE key = ?",
                (seed_key,),
            ).fetchone()
            if seeded:
                return

            now = utc_now()
            contacts = []
            for friend in (profile or {}).get("friends", []):
                if isinstance(friend, str):
                    contacts.append({"name": friend, "status": "offline"})
                elif isinstance(friend, dict):
                    contacts.append({
                        "name": friend.get("name", ""),
                        "status": friend.get("status", "offline"),
                    })

            seen = set()
            for contact in contacts:
                name = (contact.get("name") or "").strip()
                if not name or name in seen:
                    continue
                user_exists = conn.execute(
                    "SELECT 1 FROM users WHERE username = ?",
                    (name,),
                ).fetchone()
                if not user_exists:
                    continue
                seen.add(name)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO contacts
                        (owner_username, contact_name, status, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (username, name, contact.get("status", "offline"), now),
                )

            for msg in default_messages or []:
                if not isinstance(msg, dict):
                    continue
                sender = msg.get("from", "System")
                subject = msg.get("subject", "")
                body = msg.get("content", "")
                if not body and not subject:
                    continue
                conn.execute(
                    """
                    INSERT INTO chat_messages
                        (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                    VALUES (?, 'group', 'global', ?, ?, ?, ?, ?)
                    """,
                    (username, sender, subject, body, now, now),
                )

            conn.execute(
                """
                INSERT INTO kv_store (key, value_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (seed_key, dumps_json({"seeded": True}), now),
            )

    def list_contacts(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT contact_name, status
                FROM contacts
                WHERE owner_username = ?
                ORDER BY contact_name COLLATE NOCASE
                """,
                (username,),
            ).fetchall()
            return [{"name": row["contact_name"], "status": row["status"]} for row in rows]

    def is_contact(self, username, contact_name):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT 1 FROM contacts
                WHERE owner_username = ? AND contact_name = ?
                """,
                (username, contact_name),
            ).fetchone()
            return row is not None

    def is_accepted_contact(self, username, contact_name):
        if not username or not contact_name:
            return False
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM contacts own
                JOIN contacts reciprocal
                    ON reciprocal.owner_username = own.contact_name
                    AND reciprocal.contact_name = own.owner_username
                WHERE own.owner_username = ?
                    AND own.contact_name = ?
                """,
                (username, contact_name),
            ).fetchone()
            return row is not None

    def list_accepted_contacts(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT own.contact_name, own.status
                FROM contacts own
                JOIN contacts reciprocal
                    ON reciprocal.owner_username = own.contact_name
                    AND reciprocal.contact_name = own.owner_username
                WHERE own.owner_username = ?
                ORDER BY own.contact_name COLLATE NOCASE
                """,
                (username,),
            ).fetchall()
            return [{"name": row["contact_name"], "status": row["status"]} for row in rows]

    def has_direct_thread(self, username, peer_name):
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM chat_messages
                WHERE owner_username = ?
                    AND scope = 'direct'
                    AND peer_name = ?
                LIMIT 1
                """,
                (username, peer_name),
            ).fetchone()
            return row is not None

    def has_pending_contact_request(self, requester, target_name):
        if not requester or not target_name:
            return False
        if self.is_accepted_contact(requester, target_name):
            return False
        if self.is_contact(requester, target_name) or self.is_contact(target_name, requester):
            return True
        return self.has_direct_thread(target_name, requester) or self.has_direct_thread(requester, target_name)

    def add_contact_pair(self, username, contact_name, status="offline"):
        self.add_contact(username, contact_name, status)
        self.add_contact(contact_name, username, status)

    def list_pending_threads(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    m.peer_name,
                    MAX(m.id) AS last_id,
                    MAX(m.created_at) AS last_at
                FROM chat_messages m
                LEFT JOIN contacts c
                    ON c.owner_username = m.owner_username
                    AND c.contact_name = m.peer_name
                WHERE m.owner_username = ?
                    AND m.scope = 'direct'
                    AND c.id IS NULL
                GROUP BY m.peer_name
                ORDER BY last_id DESC
                """,
                (username,),
            ).fetchall()
            return [
                {
                    "name": row["peer_name"],
                    "status": "pending",
                    "last_at": row["last_at"],
                }
                for row in rows
                if row["peer_name"]
            ]

    def unread_counts(self, username):
        with db_connect(self.db_path) as conn:
            group_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM chat_messages
                WHERE owner_username = ?
                    AND scope = 'group'
                    AND read_at IS NULL
                """,
                (username,),
            ).fetchone()
            direct_rows = conn.execute(
                """
                SELECT peer_name, COUNT(*) AS count
                FROM chat_messages
                WHERE owner_username = ?
                    AND scope = 'direct'
                    AND read_at IS NULL
                GROUP BY peer_name
                """,
                (username,),
            ).fetchall()
            channel_rows = conn.execute(
                """
                SELECT peer_name, COUNT(*) AS count
                FROM chat_messages
                WHERE owner_username = ?
                    AND scope = 'channel'
                    AND read_at IS NULL
                GROUP BY peer_name
                """,
                (username,),
            ).fetchall()
            return {
                "group": group_row["count"] if group_row else 0,
                "direct": {
                    row["peer_name"]: row["count"]
                    for row in direct_rows
                    if row["peer_name"]
                },
                "channel": {
                    row["peer_name"]: row["count"]
                    for row in channel_rows
                    if row["peer_name"]
                },
            }

    def mark_thread_read(self, username, scope, peer_name):
        peer_name = "global" if scope == "group" else peer_name
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE chat_messages
                SET read_at = ?
                WHERE owner_username = ?
                    AND scope = ?
                    AND peer_name = ?
                    AND read_at IS NULL
                """,
                (utc_now(), username, scope, peer_name),
            )

    def touch_presence(self, username):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO mail_presence (username, last_seen_at)
                VALUES (?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    last_seen_at = excluded.last_seen_at
                """,
                (username, utc_now()),
            )

    def group_active_count(self, username, seconds=10):
        threshold = (datetime.utcnow() - timedelta(seconds=seconds)).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT contact_name
                FROM contacts
                WHERE owner_username = ?
                """,
                (username,),
            ).fetchall()
            names = {username}
            names.update(row["contact_name"] for row in rows if row["contact_name"])
            active = 0
            for name in names:
                row = conn.execute(
                    """
                    SELECT 1
                    FROM mail_presence
                    WHERE username = ? AND last_seen_at >= ?
                    """,
                    (name, threshold),
                ).fetchone()
                if row:
                    active += 1
            return active

    def add_contact(self, username, contact_name, status="offline"):
        contact_name = (contact_name or "").strip()
        if not contact_name:
            raise ValueError("Contact name is required.")
        if contact_name == username:
            raise ValueError("Nie możesz dodać samego siebie do znajomych.")

        with db_connect(self.db_path) as conn:
            user_exists = conn.execute(
                "SELECT 1 FROM users WHERE username = ?",
                (contact_name,),
            ).fetchone()
            if not user_exists:
                raise ValueError("Nie ma takiego użytkownika.")

            conn.execute(
                """
                INSERT INTO contacts (owner_username, contact_name, status, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(owner_username, contact_name) DO UPDATE SET
                    status = excluded.status
                """,
                (username, contact_name, status, utc_now()),
            )

    def remove_contacts_without_users(self, username):
        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                DELETE FROM contacts
                WHERE owner_username = ?
                    AND contact_name NOT IN (SELECT username FROM users)
                """,
                (username,),
            )

    def remove_contact(self, username, contact_name):
        with db_connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM contacts WHERE owner_username = ? AND contact_name = ?",
                (username, contact_name),
            )
            conn.execute(
                """
                DELETE FROM chat_messages
                WHERE owner_username = ? AND scope = 'direct' AND peer_name = ?
                """,
                (username, contact_name),
            )

    def list_messages(self, username, scope="group", peer_name="global", limit=100):
        with db_connect(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, scope, peer_name, sender, subject, body, created_at
                FROM chat_messages
                WHERE owner_username = ? AND scope = ? AND peer_name = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (username, scope, peer_name, limit),
            ).fetchall()
            messages = [
                {
                    "id": row["id"],
                    "scope": row["scope"],
                    "peer_name": row["peer_name"],
                    "sender": row["sender"],
                    "subject": row["subject"],
                    "body": row["body"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]
            messages.reverse()
            return messages

    def add_message(self, username, scope, peer_name, sender, body, subject="", auto_add_contact=False, channel_recipients=None):
        body = (body or "").strip()
        if not body:
            raise ValueError("Message body is required.")
        if scope not in {"group", "direct", "channel"}:
            raise ValueError("Unsupported chat scope.")

        peer_name = "global" if scope == "group" else (peer_name or "").strip()
        if scope in {"direct", "channel"} and not peer_name:
            raise ValueError("Peer name is required.")

        with db_connect(self.db_path) as conn:
            accept_pending_contact = False
            if scope == "direct" and auto_add_contact:
                pending_row = conn.execute(
                    """
                    SELECT 1
                    FROM chat_messages
                    WHERE owner_username = ?
                        AND scope = 'direct'
                        AND peer_name = ?
                        AND sender = ?
                    LIMIT 1
                    """,
                    (username, peer_name, peer_name),
                ).fetchone()
                accept_pending_contact = pending_row is not None

            conn.execute(
                """
                INSERT INTO chat_messages
                    (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (username, scope, peer_name, sender, subject, body, utc_now(), utc_now()),
            )

            if scope == "group":
                rows = conn.execute(
                    """
                    SELECT contact_name
                    FROM contacts
                    WHERE owner_username = ?
                    """,
                    (username,),
                ).fetchall()
                for row in rows:
                    recipient_name = row["contact_name"]
                    recipient = conn.execute(
                        "SELECT username FROM users WHERE username = ?",
                        (recipient_name,),
                    ).fetchone()
                    if not recipient or recipient_name == username:
                        continue
                    conn.execute(
                        """
                        INSERT INTO chat_messages
                            (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                        VALUES (?, 'group', 'global', ?, ?, ?, ?, NULL)
                        """,
                        (recipient_name, sender, subject, body, utc_now()),
                    )
                return

            if scope == "channel":
                recipients = []
                seen = {username}
                for recipient_name in channel_recipients or []:
                    recipient_name = (recipient_name or "").strip()
                    if not recipient_name or recipient_name in seen:
                        continue
                    recipient = conn.execute(
                        "SELECT username FROM users WHERE username = ?",
                        (recipient_name,),
                    ).fetchone()
                    if not recipient:
                        continue
                    seen.add(recipient_name)
                    recipients.append(recipient_name)
                for recipient_name in recipients:
                    conn.execute(
                        """
                        INSERT INTO chat_messages
                            (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                        VALUES (?, 'channel', ?, ?, ?, ?, ?, NULL)
                        """,
                        (recipient_name, peer_name, sender, subject, body, utc_now()),
                    )
                return

            if scope == "direct" and auto_add_contact:
                conn.execute(
                    """
                    INSERT INTO contacts (owner_username, contact_name, status, created_at)
                    VALUES (?, ?, 'offline', ?)
                    ON CONFLICT(owner_username, contact_name) DO NOTHING
                    """,
                    (username, peer_name, utc_now()),
                )
                if accept_pending_contact:
                    conn.execute(
                        """
                        INSERT INTO contacts (owner_username, contact_name, status, created_at)
                        VALUES (?, ?, 'offline', ?)
                        ON CONFLICT(owner_username, contact_name) DO NOTHING
                        """,
                        (peer_name, username, utc_now()),
                    )

            if scope == "direct":
                recipient = conn.execute(
                    "SELECT username FROM users WHERE username = ?",
                    (peer_name,),
                ).fetchone()
                if recipient and peer_name != username:
                    conn.execute(
                        """
                        INSERT INTO chat_messages
                            (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                        VALUES (?, 'direct', ?, ?, ?, ?, ?, NULL)
                        """,
                        (peer_name, username, sender, subject, body, utc_now()),
                    )

    def add_direct_notification(self, username, peer_name, sender, subject, body):
        body = (body or "").strip()
        if not username or not body:
            return

        with db_connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO chat_messages
                    (owner_username, scope, peer_name, sender, subject, body, created_at, read_at)
                VALUES (?, 'direct', ?, ?, ?, ?, ?, NULL)
                """,
                (
                    username,
                    (peer_name or sender or "System"),
                    sender or "System",
                    subject or "",
                    body,
                    utc_now(),
                ),
            )


class GameStateDeltaBus:
    DEFAULT_RETENTION_LIMIT = 1000
    DEFAULT_QUERY_LIMIT = 100
    RECOVERY_REASONS = {"invalid_since", "outside_retention", "limit_exceeded", "missing_username"}

    def __init__(self, db_path=DB_PATH, retention_limit=DEFAULT_RETENTION_LIMIT):
        self.db_path = db_path
        self.retention_limit = max(1, int(retention_limit or self.DEFAULT_RETENTION_LIMIT))
        init_db(self.db_path)

    @staticmethod
    def _clean_text(value, default=""):
        text = str(value or "").strip()
        return text or default

    @classmethod
    def _default_entity_id(cls, scope, change_type, payload):
        if isinstance(payload, dict):
            for key in (
                "entity_id",
                "id",
                "app_id",
                "operation_id",
                "transaction_id",
                "player_id",
                "target_id",
                "area_id",
            ):
                value = payload.get(key)
                if value not in (None, ""):
                    return cls._clean_text(value)
        if scope:
            return cls._clean_text(scope)
        return cls._clean_text(change_type, "event")

    @classmethod
    def _event_from_row(cls, row):
        if not row:
            return None
        payload = loads_json(row["payload_json"], {})
        event = {
            "version": int(row["version"]),
            "scope": row["scope"],
            "type": row["type"],
            "entity_id": row["entity_id"],
            "dedupe_key": row["dedupe_key"],
            "payload": payload,
            "created_at": row["created_at"],
        }
        if isinstance(payload, dict):
            for key in (
                "event_id",
                "cycle_id",
                "state_version",
                "audience_scope",
                "transaction_id",
                "transaction_index",
                "transaction_size",
            ):
                if key in payload:
                    event[key] = payload.get(key)
        return event

    @staticmethod
    def _payload_size(payload):
        return len(dumps_json(payload if isinstance(payload, dict) else {}))

    @classmethod
    def _diagnostic_event_from_row(cls, row):
        event = cls._event_from_row(row)
        payload = event.get("payload") if isinstance(event, dict) else {}
        event["payload_size"] = cls._payload_size(payload)
        return event

    def _trim_retention(self, conn, username):
        conn.execute(
            """
            DELETE FROM game_state_deltas
            WHERE username = ?
                AND id NOT IN (
                    SELECT id
                    FROM game_state_deltas
                    WHERE username = ?
                    ORDER BY version DESC
                    LIMIT ?
                )
            """,
            (username, username, self.retention_limit),
        )

    def current_version(self, username):
        username = self._clean_text(username)
        if not username:
            return 0
        with db_connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM game_state_deltas WHERE username = ?",
                (username,),
            ).fetchone()
            return int(row["version"] if row else 0)

    def record_change(self, username, scope, change_type, payload=None, entity_id=None, dedupe_key=None, created_at=None):
        username = self._clean_text(username)
        scope = self._clean_text(scope)
        change_type = self._clean_text(change_type)
        if not username:
            raise ValueError("Delta event requires username.")
        if not scope:
            raise ValueError("Delta event requires scope.")
        if not change_type:
            raise ValueError("Delta event requires type.")
        if payload is None:
            payload = {}
        if not isinstance(payload, dict):
            raise ValueError("Delta event payload must be an object.")

        entity_id = self._clean_text(entity_id or self._default_entity_id(scope, change_type, payload))
        created_at = self._clean_text(created_at or utc_now())

        with db_connect(self.db_path) as conn:
            if dedupe_key:
                dedupe_key = self._clean_text(dedupe_key)
            else:
                next_version_row = conn.execute(
                    "SELECT COALESCE(MAX(version), 0) + 1 AS version FROM game_state_deltas WHERE username = ?",
                    (username,),
                ).fetchone()
                next_version = int(next_version_row["version"] if next_version_row else 1)
                dedupe_key = f"{scope}:{change_type}:{entity_id}:{next_version}"

            existing = conn.execute(
                """
                SELECT version, scope, type, entity_id, dedupe_key, payload_json, created_at
                FROM game_state_deltas
                WHERE username = ? AND dedupe_key = ?
                """,
                (username, dedupe_key),
            ).fetchone()
            if existing:
                return self._event_from_row(existing)

            version_row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS version FROM game_state_deltas WHERE username = ?",
                (username,),
            ).fetchone()
            version = int(version_row["version"] if version_row else 1)
            conn.execute(
                """
                INSERT INTO game_state_deltas
                    (username, version, scope, type, entity_id, dedupe_key, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    version,
                    scope,
                    change_type,
                    entity_id,
                    dedupe_key,
                    dumps_json(payload),
                    created_at,
                ),
            )
            self._trim_retention(conn, username)
            return {
                "version": version,
                "scope": scope,
                "type": change_type,
                "entity_id": entity_id,
                "dedupe_key": dedupe_key,
                "payload": copy.deepcopy(payload),
                "created_at": created_at,
            }

    def get_changes_since(self, username, since_version=0, limit=DEFAULT_QUERY_LIMIT):
        username = self._clean_text(username)
        if not username:
            return {
                "current_version": 0,
                "changes": [],
                "recovery_required": True,
                "reason": "missing_username",
            }
        try:
            since_version = int(since_version or 0)
        except (TypeError, ValueError):
            since_version = -1
        limit = max(1, min(int(limit or self.DEFAULT_QUERY_LIMIT), self.retention_limit))

        with db_connect(self.db_path) as conn:
            version_row = conn.execute(
                """
                SELECT
                    COALESCE(MIN(version), 0) AS oldest_version,
                    COALESCE(MAX(version), 0) AS current_version,
                    COUNT(*) AS count
                FROM game_state_deltas
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
            oldest_version = int(version_row["oldest_version"] if version_row else 0)
            current_version = int(version_row["current_version"] if version_row else 0)
            count = int(version_row["count"] if version_row else 0)

            if since_version < 0:
                return {
                    "current_version": current_version,
                    "changes": [],
                    "recovery_required": True,
                    "reason": "invalid_since",
                }
            if count and since_version < oldest_version - 1:
                return {
                    "current_version": current_version,
                    "changes": [],
                    "recovery_required": True,
                    "reason": "outside_retention",
                    "oldest_version": oldest_version,
                }

            total_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM game_state_deltas
                WHERE username = ? AND version > ?
                """,
                (username, since_version),
            ).fetchone()
            available_count = int(total_row["count"] if total_row else 0)
            if available_count > limit:
                return {
                    "current_version": current_version,
                    "changes": [],
                    "recovery_required": True,
                    "reason": "limit_exceeded",
                    "available_count": available_count,
                    "limit": limit,
                }

            rows = conn.execute(
                """
                SELECT version, scope, type, entity_id, dedupe_key, payload_json, created_at
                FROM game_state_deltas
                WHERE username = ? AND version > ?
                ORDER BY version ASC
                LIMIT ?
                """,
                (username, since_version, limit),
            ).fetchall()
            return {
                "current_version": current_version,
                "changes": [self._event_from_row(row) for row in rows],
                "recovery_required": False,
            }

    def diagnostics(self, username, limit=25, pollers_active_count=0, snapshot_recovery_count=0):
        username = self._clean_text(username)
        limit = max(1, min(int(limit or 25), 100))
        if not username:
            return {
                "current_version": 0,
                "events": [],
                "metrics": {
                    "delta_events_per_minute": 0,
                    "delta_payload_size": 0,
                    "recovery_count": 0,
                    "snapshot_recovery_count": int(snapshot_recovery_count or 0),
                    "pollers_active_count": int(pollers_active_count or 0),
                },
            }

        threshold = (datetime.utcnow() - timedelta(minutes=1)).isoformat(timespec="seconds")
        with db_connect(self.db_path) as conn:
            current_row = conn.execute(
                "SELECT COALESCE(MAX(version), 0) AS version FROM game_state_deltas WHERE username = ?",
                (username,),
            ).fetchone()
            current_version = int(current_row["version"] if current_row else 0)
            rows = conn.execute(
                """
                SELECT version, scope, type, entity_id, dedupe_key, payload_json, created_at
                FROM game_state_deltas
                WHERE username = ?
                ORDER BY version DESC
                LIMIT ?
                """,
                (username, limit),
            ).fetchall()
            events = [self._diagnostic_event_from_row(row) for row in rows]
            minute_row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM game_state_deltas
                WHERE username = ? AND created_at >= ?
                """,
                (username, threshold),
            ).fetchone()
            payload_size = sum(event.get("payload_size", 0) for event in events)
            recovery_count = sum(
                1
                for event in events
                if event.get("type") == "state.recovery_required"
                or event.get("payload", {}).get("reason") in self.RECOVERY_REASONS
            )
            return {
                "current_version": current_version,
                "events": events,
                "metrics": {
                    "delta_events_per_minute": int(minute_row["count"] if minute_row else 0),
                    "delta_payload_size": payload_size,
                    "recovery_count": recovery_count,
                    "snapshot_recovery_count": int(snapshot_recovery_count or 0),
                    "pollers_active_count": int(pollers_active_count or 0),
                },
            }
