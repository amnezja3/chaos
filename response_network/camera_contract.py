"""Server-owned camera identities and narrow shutdown authorization."""
import hashlib
import math
from datetime import datetime, timedelta, timezone

from database import db_connect, dumps_json, loads_json, utc_now


def camera_marker(parent, slot=0):
    lat, lng = float(parent['lat']), float(parent.get('lng', parent.get('lon')))
    parent_id = str(parent.get('osm_id') or parent.get('node_id') or
                    f"{parent.get('source_type', 'poi')}:{lat:.7f}:{lng:.7f}")
    digest = hashlib.sha256(f'{parent_id}:{slot}'.encode()).hexdigest()
    angle = int(digest[:8], 16) / 0xffffffff * math.tau
    return {
        'camera_id': 'camera_' + digest[:24], 'parent_target_id': parent_id,
        'target_type': 'camera', 'source_type': 'camera', 'generated': True,
        'name': 'Kamera', 'label': 'Kamera', 'icon': '📷',
        'lat': lat + math.sin(angle) * .00025,
        'lon': lng + math.cos(angle) * .00025,
    }


def eligible_app(app):
    if not isinstance(app, dict):
        return False
    actions = app.get('map_actions')
    targets = app.get('target_types') or []
    operations = app.get('operation_types') or []
    return (isinstance(actions, list) and 'camera_shutdown' in actions
            and isinstance(targets, list) and (not targets or 'camera' in targets)
            and isinstance(operations, list) and (not operations or 'camera_shutdown' in operations))


class CameraContractError(ValueError):
    pass


class CameraContractStore:
    def __init__(self, db_path):
        self.db_path = db_path

    def observed(self, username, scan_id, camera_id, *, conn=None):
        if conn is None:
            with db_connect(self.db_path) as own:
                return self.observed(username, scan_id, camera_id, conn=own)
        row = conn.execute('''SELECT marker_json FROM response_camera_observations
            WHERE username=? AND scan_id=? AND camera_id=? AND expires_at > ?''',
            (username, scan_id, camera_id, datetime.now(timezone.utc).timestamp())).fetchone()
        if not row:
            raise CameraContractError('camera_scan_expired_or_unknown')
        return loads_json(row['marker_json'], {})

    def apps(self, username):
        with db_connect(self.db_path) as conn:
            rows = conn.execute('''SELECT app_id, app_json FROM player_apps WHERE username=?
                AND status!='uninstalled' AND EXISTS
                (SELECT 1 FROM json_each(player_apps.app_json, '$.map_actions')
                 WHERE value='camera_shutdown') ORDER BY app_id LIMIT 65''', (username,)).fetchall()
        if len(rows) > 64:
            raise CameraContractError('camera_app_limit')
        return [{**loads_json(r['app_json'], {}), 'id': r['app_id']} for r in rows
                if eligible_app(loads_json(r['app_json'], {}))]

    def shutdown(self, username, scan_id, camera_id, app_id, *, guard, inventory, messages,
                 deltas, flow_id='', request_key='', operation_template=None, expected_app=None):
        if any(str(store.db_path) != str(self.db_path) for store in (inventory, messages, deltas)):
            raise ValueError('camera_database_mismatch')
        # Stable receipt survives process restarts and different client retry keys.
        operation_id = 'camera_off_' + hashlib.sha256(
            f'{username}:{scan_id}:{camera_id}:{app_id}'.encode()).hexdigest()[:28]
        now = datetime.now(timezone.utc)
        with db_connect(self.db_path) as conn:
            conn.execute('BEGIN IMMEDIATE')
            target = self.observed(username, scan_id, camera_id, conn=conn)
            row = conn.execute('''SELECT app_json FROM player_apps WHERE username=?
                AND app_id=? AND status!='uninstalled' ''', (username, app_id)).fetchone()
            if not row or not eligible_app(loads_json(row['app_json'], {})):
                raise CameraContractError('camera_app_not_authorized')
            app = loads_json(row['app_json'], {})
            if expected_app is not None and {**app, 'id': app_id} != expected_app:
                raise CameraContractError('camera_app_changed')
            guard(conn, target)
            existing = conn.execute('''SELECT operation_json FROM player_operations
                WHERE username=? AND operation_id=?''', (username, operation_id)).fetchone()
            if existing:
                return loads_json(existing['operation_json'], {}), True
            active = conn.execute('''SELECT operation_json FROM player_operations
                WHERE username=? AND target_key=? AND operation_type='camera_shutdown'
                AND status IN ('start','running') ORDER BY updated_at DESC LIMIT 1''',
                (username, camera_id)).fetchone()
            if active:
                prior = loads_json(active['operation_json'], {})
                if str(prior.get('expires_at') or '') > now.isoformat():
                    return prior, True
            if conn.execute('''SELECT count(*) FROM (SELECT 1 FROM player_operations
                WHERE username=? AND status IN ('start','running') LIMIT 32)''', (username,)).fetchone()[0] >= 32:
                raise CameraContractError('camera_operation_limit')
            operation = {
                **(operation_template or {}),
                'operation_id': operation_id, 'owner_username': username,
                'operation_type': 'camera_shutdown', 'map_action_id': 'camera_shutdown',
                'source_app_id': app_id, 'source_app_name': app.get('name') or app_id,
                'status': 'running', 'target_id': camera_id, 'target_type': 'camera',
                'target': {**target, 'scan_id': scan_id, 'target_id': camera_id},
                'started_at': now.isoformat(), 'expires_at': (now + timedelta(minutes=15)).isoformat(),
                'duration_seconds': 900, 'movement_model': 'static_active_timer',
                'support_state': {'type': 'camera_shutdown', 'active': True, 'camera_state': 'offline'},
                'camera_evidence': {'schema': 1, 'camera_id': camera_id, 'scan_id': scan_id,
                                    'parent_target_id': target.get('parent_target_id')},
                'resource_buffer': {'files': [], 'resource_types': []},
            }
            conn.execute('''INSERT INTO player_operations
                (operation_id,username,target_key,operation_type,status,operation_json,risk_json,version,created_at,updated_at)
                VALUES (?,?,?,'camera_shutdown','running',?,?,1,?,?)''',
                (operation_id, username, camera_id, dumps_json(operation),
                 dumps_json(operation.get('operation_risk_meter') or {}), utc_now(), utc_now()))
            conn.execute('''INSERT INTO operation_events
                (event_id,operation_id,event_type,dedupe_key,payload_json,created_at)
                VALUES (?,?,'operation.started',?,?,?)''',
                (operation_id, operation_id, operation_id, dumps_json(operation), utc_now()))
            inventory.commit_launch(username, [{
                'receipt': operation_id, 'app_id': app_id, 'name': app.get('name') or app_id,
                'action': 'camera_shutdown', 'flow_id': flow_id, 'client_action_key': request_key,
            }], [], messages, conn=conn)
            deltas.record_change(username, 'map', 'map.operations_changed',
                                 {'operation': operation}, entity_id=operation_id,
                                 dedupe_key=operation_id, conn=conn)
            return operation, False
