"""Shared server-side movement gate. No source string is a bypass capability."""


class MovementBlocked(Exception):
    def __init__(self, remaining_ms, status):
        super().__init__('detention_movement_blocked')
        self.remaining_seconds = max(0, (int(remaining_ms) + 999) // 1000)
        self.sanction_status = status


def require_movement_allowed(conn, actor_id):
    # Before the explicit sanction-store migration there can be no sentences.
    # Other SQLite errors must propagate; never turn a read failure into a bypass.
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='response_sanctions'").fetchone():
        return
    row = conn.execute("""SELECT remaining_ms,status FROM response_sanctions
        WHERE actor_id=? AND status IN ('active','release_pending')""", (actor_id,)).fetchone()
    if row:
        raise MovementBlocked(row['remaining_ms'], row['status'])


def require_profile_position_allowed(conn, actor_id, current, candidate):
    """Legacy aliases may mirror canonical position, never bypass detention."""
    changed = [key for key in ('curently_possition', 'current_position')
               if candidate.get(key) != current.get(key)]
    if not changed:
        return
    canonical = conn.execute('SELECT lat,lng FROM player_positions WHERE username=?', (actor_id,)).fetchone()
    for key in changed:
        incoming = candidate.get(key)
        try:
            mirrors = (canonical is not None and isinstance(incoming, dict)
                       and abs(float(incoming['lat']) - canonical['lat']) < 0.0000001
                       and abs(float(incoming.get('lng', incoming.get('lon'))) - canonical['lng']) < 0.0000001)
        except (KeyError, TypeError, ValueError):
            mirrors = False
        if not mirrors:
            require_movement_allowed(conn, actor_id)
