"""Audit/apply missing inventory for one account; default is read-only."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inventory_bootstrap import repair_missing_inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--username', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not Path(args.db).is_file():
        parser.error('Database does not exist')
    result = repair_missing_inventory(args.db, args.username, apply=args.apply)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result['status'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
