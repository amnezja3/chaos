"""Inventory/reviewed metadata backfill. No translation, model calls or publication."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    from ghostnetwork import narrative_locale_history as history
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('inventory','import','rollback'))
    parser.add_argument('--db',required=True)
    parser.add_argument('--after',default='')
    parser.add_argument('--limit',type=int,default=100)
    parser.add_argument('--batch')
    parser.add_argument('--reviewed-by')
    parser.add_argument('--input',type=Path)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not Path(args.db).is_file():
        parser.error('Existing database required.')
    try:
        if args.command=='inventory':
            result=history.inventory(args.db,args.after,args.limit)
        elif args.command=='import':
            if not args.input or not args.batch or not args.reviewed_by:
                parser.error('Import requires --input, --batch and --reviewed-by.')
            if args.input.stat().st_size>1024*1024:
                parser.error('Input exceeds 1 MiB.')
            result=history.apply_batch(args.db,args.batch,json.loads(args.input.read_text(encoding='utf-8')),
                args.reviewed_by,dry_run=not args.apply)
        else:
            if not args.batch:
                parser.error('Rollback requires --batch.')
            result=history.rollback_batch(args.db,args.batch,dry_run=not args.apply)
    except (ValueError,OSError):
        print(json.dumps({'ok':False,'error':'language_history_validation_failed'}))
        return 1
    print(json.dumps({'ok':True,**result}))
    return 0


if __name__=='__main__':
    sys.exit(main())
