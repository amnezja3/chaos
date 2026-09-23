"""143.5 capabilities from the immutable sentence snapshot, not client claims."""
import json
from database import ProfileWriteError

from .sanctions import SanctionStore


class DetentionDenied(ProfileWriteError):
    def __init__(self, reason, state):
        self.reason, self.state = reason, state
        super().__init__(reason)


def snapshot(conn, actor):
    # Old isolated stores and databases before the migration contain no sentences.
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='response_sanctions'").fetchone():
        return None
    row = SanctionStore.active_for(conn, actor)
    if not row:
        return None
    plan = json.loads(row['plan_json'])
    used = conn.execute('SELECT 1 FROM response_sanction_messages WHERE sanction_id=?',
                        (row['sanction_id'],)).fetchone()
    prison = None
    if conn.execute("SELECT 1 FROM sqlite_master WHERE name='response_detention_transport'").fetchone():
        prison = conn.execute('SELECT prison_json FROM response_detention_transport WHERE sanction_id=?',
                              (row['sanction_id'],)).fetchone()
    return {'sanction_id': row['sanction_id'], 'stage': plan['stage'],
            'prison_name': json.loads(prison['prison_json']).get('name', 'Areszt') if prison else 'Areszt',
            'duration_seconds': (row['duration_ms'] + 999) // 1000,
            'remaining_seconds': (row['remaining_ms'] + 999) // 1000,
            'bail_hc': plan['bail_hc'], **plan['restrictions'],
            'private_messages_remaining': 0 if used else 1}


def require_world(conn, actor, *, sending=False):
    state = snapshot(conn, actor)
    if state and (state['cyberner_world'] == 'blocked' or
                  (sending and state['cyberner_world'] != 'full')):
        raise DetentionDenied('detention_world_blocked' if state['cyberner_world'] == 'blocked'
                              else 'detention_world_read_only', state)


# Explicit essential/browser/radio surface. Unknown/new routes fail closed at 9.
READ_PATHS = frozenset({
    '/', '/desktop', '/logout', '/session/recover', '/resources.json',
    '/api/state/changes', '/api/profile', '/api/profile/desktop',
    '/system-messages', '/api/mail/bootstrap', '/api/chats/messages', '/friends.json',
    '/api/response/detention', '/api/response/detention/bail-quote',
    '/api/catalog', '/api/googleplex/news', '/api/radio/channels',
    '/api/blacknet/world-facts', '/api/blacknet/world-signals',
    '/api/ghost-exchange', '/api/ghostnetwork/show',
})
WRITE_PATHS = frozenset({'/api/response/detention/bail', '/api/chats/messages',
                         '/api/contacts', '/add-system-message', '/api/ghostnetwork/restart/ack',
                         '/api/map/incidents/detection-candidates'})


def require_request(conn, actor, path, method, endpoint=None):
    state = snapshot(conn, actor)
    if not state:
        return
    if path == '/api/ghostnetwork/ability' and method == 'POST':
        raise DetentionDenied('detention_action_blocked', state)
    if method != 'OPTIONS' and path in {
        '/api/map/aim-target', '/api/map/player-targets/mark',
        '/api/victim-picker/aim', '/api/victim-picker/candidates',
        '/map-action', '/hack-action', '/gonna-win', '/api/player-hack/tool/use',
    }:
        if path == '/map-action':
            from flask import has_request_context, request
            payload = request.get_json(silent=True) if has_request_context() else None
            if isinstance(payload, dict) and payload.get('action') == 'travel':
                from .movement_guard import require_movement_allowed
                require_movement_allowed(conn, actor)
        raise DetentionDenied('detention_action_blocked', state)
    # Contact invitations generate private messages outside the send endpoint.
    if path == '/api/player-contact/request':
        raise DetentionDenied('detention_use_private_message', state)
    if state['app_access'] != 'webdragon_radio':
        return
    read = method in {'GET', 'HEAD'}
    if method == 'OPTIONS' or (read and endpoint == 'static'):
        return
    if read and (path in READ_PATHS or path.startswith('/api/radio/channel/')):
        return
    if method == 'POST' and path in WRITE_PATHS:
        return
    raise DetentionDenied('detention_app_blocked', state)


def require_targeting_allowed(conn, actor):
    state = snapshot(conn, actor)
    if state:
        raise DetentionDenied('detention_action_blocked', state)


def world_payload(payload):
    if not isinstance(payload, dict):
        return False
    if payload.get('channel') == 'world' or payload.get('scope') == 'world':
        return True
    if payload.get('scope') == 'group' and payload.get('peer', 'global') == 'global':
        return True
    return any(world_payload(payload.get(key)) for key in ('message', 'thread'))
