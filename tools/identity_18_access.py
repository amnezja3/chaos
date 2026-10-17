"""Operator age restriction: no profile deletion, no change to IDs or sessions."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.ghost_content_155_migrate import connect
from identity_gateway.service import event


def change(path, username, restricted, reason='operator_review', threshold=None):
    conn = connect(path, writable=True)
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        if not row:
            raise ValueError('account_missing')
        from identity_gateway.adult_policy import restrict
        restrict(conn,row[0],restricted=restricted,reason=reason,threshold=threshold)
        # Releasing an erroneous restriction never fabricates an adult declaration.
        event(conn, 'age_restricted' if restricted else 'age_restriction_released', None, row[0])
        conn.commit()
        return {'ok': True, 'age_restricted': restricted}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--username', required=True)
    parser.add_argument('--confirm-username', required=True)
    parser.add_argument('--reason', required=True, help='Recorded review justification; do not include identity documents')
    parser.add_argument('--threshold', type=int, choices=(16,18))
    parser.add_argument('action', choices=('restrict', 'release'))
    args = parser.parse_args()
    if args.username != args.confirm_username:
        parser.error('Confirmation must exactly match username')
    print(json.dumps(change(args.db, args.username, args.action == 'restrict',args.reason,args.threshold)))
