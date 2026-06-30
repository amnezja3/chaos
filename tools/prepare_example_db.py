import argparse
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RUNTIME_DB = DATA_DIR / "game.sqlite3"
EXAMPLE_DB = DATA_DIR / "game.example.sqlite3"
BACKUP_DIR = DATA_DIR / "backups"
USER_TEMPLATE = ROOT / "static" / "user_template.json"


RUNTIME_TABLES_TO_CLEAR = [
    "contacts",
    "chat_messages",
    "mail_presence",
    "wallet_transactions",
    "player_hack_access",
    "player_hack_tool_usage",
    "dev_bug_reports",
    "captured_targets",
    "player_areas",
    "area_events",
    "territory_conflicts",
    "reported_vulnerabilities",
]

FILE_CATEGORIES = [
    "download",
    "pictures",
    "social-media",
    "projects",
    "pro_system_projects",
    "gps",
    "device",
    "audio",
    "personal",
    "camera",
    "atm",
    "financial",
    "credentials",
    "network",
    "vehicle",
    "system",
    "market",
    "tools",
]


def utc_now():
    return datetime.utcnow().isoformat(timespec="seconds")


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def clean_admin_profile(profile, row_password="", row_salt=""):
    template = load_json(USER_TEMPLATE, {})
    cleaned = dict(template)

    cleaned["username"] = "admin"
    cleaned["password"] = profile.get("password") or row_password or cleaned.get("password", "")
    cleaned["salt"] = profile.get("salt") or row_salt or cleaned.get("salt", "")
    cleaned["avatar"] = profile.get("avatar") or cleaned.get("avatar") or "/static/images/default_avatar.png"
    cleaned["nick"] = profile.get("nick") or "Admin"
    cleaned["email"] = profile.get("email") or "admin@chaos.local"
    cleaned["clan"] = profile.get("clan") or ""
    cleaned["fraction"] = profile.get("fraction") or cleaned.get("fraction") or {"name": "", "role": ""}
    cleaned["curently_possition"] = profile.get("curently_possition") or cleaned.get("curently_possition") or {
        "lat": 52.2297,
        "lng": 21.0122,
    }
    cleaned["security"] = profile.get("security") or cleaned.get("security") or {}

    cleaned["level"] = 77
    cleaned["hackcoins"] = 100000
    cleaned["respect"] = 1000
    cleaned["exp"] = "DEV / 100000"

    cleaned["inventory"] = []
    cleaned["apps"] = []
    cleaned["operations"] = []
    cleaned["targets"] = []
    cleaned["hacked"] = []
    cleaned["own_places"] = []
    cleaned["market_history"] = []
    cleaned["risk_events"] = []
    cleaned["system_messages"] = []
    cleaned["messages"] = []
    cleaned["friends"] = []
    cleaned["launch_queue"] = []
    cleaned["aimed_target"] = {}
    cleaned["captured_targets_source"] = "sqlite"

    cleaned["files"] = {category: [] for category in FILE_CATEGORIES}
    cleaned["desktop_settings"] = {
        "wallpaper": "",
        "icon_positions": {},
    }
    cleaned["territory_stats"] = {
        "total_area": 0,
        "effective_area": 0,
        "area_baseline": 0,
        "next_level_area": 0,
        "area_to_next_level": 0,
        "clusters_count": 0,
        "captured_targets_count": 0,
        "last_area_gain": 0,
        "last_effective_gain": 0,
        "total_perimeter": 0,
        "edges_count": 0,
        "span_density": 0,
        "density_multiplier": 0,
    }
    return cleaned


def prepare_example_db(runtime_db=RUNTIME_DB, example_db=EXAMPLE_DB):
    if not runtime_db.exists():
        raise FileNotFoundError(f"Runtime database not found: {runtime_db}")

    DATA_DIR.mkdir(exist_ok=True)
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"game_before_example_{timestamp}.sqlite3"
    shutil.copy2(runtime_db, backup_path)
    shutil.copy2(runtime_db, example_db)

    now = utc_now()
    with sqlite3.connect(example_db) as conn:
        conn.row_factory = sqlite3.Row

        for table_name in RUNTIME_TABLES_TO_CLEAR:
            if table_exists(conn, table_name):
                conn.execute(f"DELETE FROM {table_name}")

        if table_exists(conn, "kv_store"):
            conn.execute("DELETE FROM kv_store")

        admin_row = conn.execute(
            "SELECT username, password, salt, profile_json FROM users WHERE username = ?",
            ("admin",),
        ).fetchone()
        if not admin_row:
            raise RuntimeError("Cannot prepare example DB: admin user is missing.")

        admin_profile = json.loads(admin_row["profile_json"] or "{}")
        clean_profile = clean_admin_profile(
            admin_profile,
            row_password=admin_row["password"] or "",
            row_salt=admin_row["salt"] or "",
        )

        conn.execute("DELETE FROM users WHERE username != ?", ("admin",))
        conn.execute(
            """
            UPDATE users
            SET password = ?, salt = ?, profile_json = ?, updated_at = ?
            WHERE username = ?
            """,
            (
                clean_profile.get("password", ""),
                clean_profile.get("salt", ""),
                json.dumps(clean_profile, ensure_ascii=False, separators=(",", ":")),
                now,
                "admin",
            ),
        )
        conn.commit()
        conn.execute("VACUUM")

    return backup_path, example_db


def main():
    parser = argparse.ArgumentParser(description="Prepare clean CHAOS example SQLite database.")
    parser.add_argument("--runtime-db", default=str(RUNTIME_DB))
    parser.add_argument("--example-db", default=str(EXAMPLE_DB))
    args = parser.parse_args()

    backup_path, example_path = prepare_example_db(
        runtime_db=Path(args.runtime_db),
        example_db=Path(args.example_db),
    )
    print(f"Backup: {backup_path}")
    print(f"Example DB: {example_path}")


if __name__ == "__main__":
    main()
