"""Canonical player security. No runtime migration or legacy profile writes."""
from contextlib import nullcontext
from database import db_connect, loads_json, dumps_json, utc_now, ProfileRecoveryRequired, ProfileWriteConflict, _bounded_player_security


class PlayerSecurityStore:
    def __init__(self, db_path):
        self.db_path = db_path

    def get(self, username, *, conn=None):
        with (db_connect(self.db_path) if conn is None else nullcontext(conn)) as active:
            row = active.execute('SELECT security_json,version FROM player_security WHERE username=?', (username,)).fetchone()
        if not row:
            raise ProfileRecoveryRequired('Player security migration required')
        security = loads_json(row['security_json'], None)
        if not isinstance(security, dict) or _bounded_player_security({'security': security}) is None:
            raise ProfileRecoveryRequired('Invalid canonical player security')
        return {'security': security, 'security_version': row['version']}

    def update(self, username, transform, *, expected_version=None, guard=None):
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            current = self.get(username, conn=conn)
            if expected_version is not None and (type(expected_version) is not int or expected_version != current['security_version']):
                raise ProfileWriteConflict('Security changed; reopen the panel.')
            if guard:
                guard(conn=conn)
            security = transform(dict(current['security']))
            if _bounded_player_security({'security': security}) is None:
                raise ValueError('Invalid security payload')
            if security != current['security']:
                conn.execute('UPDATE player_security SET security_json=?,version=version+1,updated_at=? WHERE username=? AND version=?',
                             (dumps_json(security), utc_now(), username, current['security_version']))
            # Guard again after transformation: uninstall/revocation must abort the effect.
            if guard:
                guard(conn=conn)
            return self.get(username, conn=conn)

    def migrate(self, *, apply=False):
        """Operator-only, bounded existing projection; never overwrite canonical state."""
        report = []
        with db_connect(self.db_path) as conn:
            if apply:
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('''CREATE TABLE IF NOT EXISTS player_security (
                    username TEXT PRIMARY KEY, security_json TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL)''')
            exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='player_security'").fetchone()
            rows = conn.execute('''SELECT u.username, json_extract(p.desktop_boot_json,'$.player_security') AS security,
                p.source_profile_revision,u.profile_revision,p.source_profile_checksum,u.profile_checksum
                FROM users u LEFT JOIN user_identity_projection p ON p.username=u.username
                ''' + ('''LEFT JOIN player_security s ON s.username=u.username WHERE s.username IS NULL ''' if exists else '') + 'ORDER BY u.username')
            for row in rows:
                security = loads_json(row['security'], None)
                valid = (isinstance(security, dict) and _bounded_player_security({'security': security}) is not None
                         and row['source_profile_revision'] == row['profile_revision']
                         and row['source_profile_checksum'] == row['profile_checksum'])
                status = 'invalid_projection' if not valid else ('migrated' if apply else 'would_migrate')
                if valid and apply:
                    conn.execute('INSERT OR IGNORE INTO player_security VALUES (?,?,1,?)', (row['username'], dumps_json(security), utc_now()))
                report.append({'username': row['username'], 'status': status})
        return report
