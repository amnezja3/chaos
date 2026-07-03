import copy
from itertools import combinations
import json
import math
import os
import sqlite3
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
        username = profile.get("username")
        if not username:
            raise ValueError("Profile must contain username.")

        now = utc_now()
        with db_connect(self.db_path) as conn:
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
                "SELECT password FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return bool(row and row["password"] == password)

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

            valid_triangles = []
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

                hull = self._convex_hull([group[index] for index in sorted(cluster_indexes)])
                if len(hull) < 3:
                    continue

                vertices = [self._area_vertex(target) for target in hull]
                hull_edges = [
                    self._distance_meters(vertices[i], vertices[(i + 1) % len(vertices)])
                    for i in range(len(vertices))
                ]
                combo_max_edge = max(hull_edges)
                area_size = self._polygon_area_sqm(vertices)
                if area_size < self.MIN_TRIANGLE_AREA_SQM:
                    continue

                areas.append({
                    "vertices": vertices,
                    "centroid_lat": sum(vertex["lat"] for vertex in vertices) / len(vertices),
                    "centroid_lng": sum(vertex["lng"] for vertex in vertices) / len(vertices),
                    "area_size": area_size,
                    "max_edge_distance": combo_max_edge,
                    "status": "active",
                })

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

            return {
                "balance": self._profile_balance(profile),
                "currency": "HC",
                "transactions": transactions,
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
            return {
                "group": group_row["count"] if group_row else 0,
                "direct": {
                    row["peer_name"]: row["count"]
                    for row in direct_rows
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

    def add_message(self, username, scope, peer_name, sender, body, subject="", auto_add_contact=False):
        body = (body or "").strip()
        if not body:
            raise ValueError("Message body is required.")
        if scope not in {"group", "direct"}:
            raise ValueError("Unsupported chat scope.")

        peer_name = "global" if scope == "group" else (peer_name or "").strip()
        if scope == "direct" and not peer_name:
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
