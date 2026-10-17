"""Explicit additive 157.8 migration; default dry run, no production activation."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import identity_157_migrate as migration
from identity_gateway.store import initialize as identity_initialize
from communication_safety import initialize as safety_initialize


def initialize(conn):
    identity_initialize(conn)
    safety_initialize(conn)


original_check=migration.check
def check(path,baseline=None):
    result=original_check(path,baseline)
    from contextlib import closing
    with closing(migration.connect(path)) as conn:
        for name in ('communication_blocks','communication_invites','communication_limits',
                     'safety_reports','safety_actions','safety_hidden','communication_sanctions',
                     'identity_age_restriction_history','safety_paused_sources'):
            conn.execute('SELECT 1 FROM '+name+' LIMIT 0')
    return result


if __name__=='__main__':
    migration.initialize=initialize
    migration.check=check
    raise SystemExit(migration.main())
