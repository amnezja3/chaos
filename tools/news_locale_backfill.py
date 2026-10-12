"""Bounded reviewed News imports. Defaults to dry-run; never invokes a model."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from database import db_connect
    from ghostnetwork.news_locales import NewsLocaleStore, initialize
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('migrate', 'inventory', 'import', 'rollback'))
    parser.add_argument('--db', required=True)
    parser.add_argument('--after', default='')
    parser.add_argument('--limit', type=int, default=100)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--batch')
    parser.add_argument('--reviewed-by')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    if not Path(args.db).is_file():
        parser.error('Database must already exist; check --db.')
    store = NewsLocaleStore(args.db)
    try:
        if args.command == 'migrate':
            if not args.apply:
                result = {'status': 'dry_run', 'migration': 'news_locale_variants_and_batches'}
            else:
                with db_connect(args.db) as conn:
                    initialize(conn)
                    from ghostnetwork.news_generation import initialize as initialize_jobs
                    initialize_jobs(conn)
                result = {'status': 'migrated'}
        elif args.command == 'inventory':
            result = store.inventory(after=args.after, limit=args.limit)
        elif args.command == 'import':
            if not args.input or not args.batch or not args.reviewed_by:
                parser.error('Import requires --input, --batch and --reviewed-by.')
            if args.input.stat().st_size > 1024 * 1024:
                parser.error('Input exceeds 1 MiB.')
            entries = json.loads(args.input.read_text(encoding='utf-8'))
            result = store.apply_batch(args.batch, entries, reviewed_by=args.reviewed_by,
                                       dry_run=not args.apply)
        else:
            if not args.batch:
                parser.error('Rollback requires --batch.')
            result = store.rollback_batch(args.batch, dry_run=not args.apply)
    except ValueError as exc:
        # ValueError here contains only validation codes, never raw publication text.
        print(json.dumps({'ok': False, 'error': str(exc)}))
        return 1
    print(json.dumps({'ok': True, **result}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
