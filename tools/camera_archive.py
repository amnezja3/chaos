"""Camera archive operator CLI. Default is read-only; no API call on migration/status."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',required=True)
    parser.add_argument('--action',choices=('status','migrate','work-once','withdraw','gc','backup','restore'),default='status')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--source')
    parser.add_argument('--image-id')
    parser.add_argument('--reason')
    parser.add_argument('--directory')
    parser.add_argument('--worker-child',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    from database import db_connect
    from camera_visual_archive import ArchiveStore,SCHEMAS
    from camera_visual import SCHEMA,INDEX
    store=ArchiveStore(args.db)
    if args.action=='migrate':
        if args.apply:
            with db_connect(args.db) as conn:
                for statement in (SCHEMA,INDEX,*SCHEMAS):
                    conn.execute(statement)
        print(json.dumps({'migration':'applied' if args.apply else 'dry-run','additive_tables':4,'destructive':False}))
    elif args.action=='status':
        with db_connect(args.db) as conn:
            rows=conn.execute('SELECT archive_id,source,status,reason,attempts,expires_at FROM camera_visual_archives ORDER BY created_at DESC LIMIT 50').fetchall()
        print(json.dumps([dict(r) for r in rows]))
    elif not args.apply:
        print(json.dumps({'action':args.action,'dry_run':True}))
    elif args.action=='work-once':
        if args.worker_child:
            print(json.dumps(store.process_one()))
        else:
            import subprocess
            try:
                child=subprocess.run([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:],'--worker-child'],
                    capture_output=True,text=True,timeout=90,
                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                print(json.dumps(json.loads(child.stdout)) if child.returncode==0 else json.dumps({'status':'WORKER_FAILED'}))
            except subprocess.TimeoutExpired:
                print(json.dumps({'status':'DEADLINE','recovery':'lease expiry; bounded retry'}))
    elif args.action=='withdraw':
        if not all((args.source,args.image_id,args.reason)):
            parser.error('withdraw requires --source, --image-id, --reason')
        store.withdraw(args.source,args.image_id,args.reason)
        print(json.dumps({'withdrawn':True}))
    elif args.action=='gc':
        print(json.dumps({'removed':store.gc()}))
    elif args.action in ('backup','restore'):
        if not args.directory: parser.error('--directory required')
        print(json.dumps({'archives':getattr(store,args.action)(args.directory)}))


if __name__=='__main__':
    main()
