"""157.1: inspect local configuration or legacy identity collisions without writes."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from identity_gateway.audit import audit_database
from identity_gateway.config import load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', help='Existing SQLite database; opened read-only')
    parser.add_argument('--config', action='store_true', help='Report configuration, never secret values')
    args = parser.parse_args()
    if not args.db and not args.config:
        parser.error('provide --db or --config')
    try:
        result = {}
        if args.db:
            result['database'] = audit_database(args.db)
        if args.config:
            result['configuration'] = load_config().status()
        print(json.dumps(dict(ok=True, **result)))
        return 0
    except (OSError, sqlite3.Error, ValueError):
        # Avoid echoing environment values, SQL/profile contents or credentials.
        print(json.dumps(dict(ok=False, error='identity_audit_failed')))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
