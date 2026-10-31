"""One real camera pilot, backed by the game's canonical operations and disk.

No profile access, provider requests, schema creation on reads, or second worker.
"""
import hashlib
import json
import os
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timezone

SCHEMA = """CREATE TABLE IF NOT EXISTS camera_visual_sessions (
 username TEXT NOT NULL, receipt TEXT NOT NULL, target_key TEXT NOT NULL,
 app_id TEXT NOT NULL, operation_id TEXT, payload_json TEXT NOT NULL,
 created_at REAL NOT NULL, lease_owner TEXT NOT NULL DEFAULT '',
 lease_until REAL NOT NULL DEFAULT 0, viewer_closed INTEGER NOT NULL DEFAULT 0,
 reference_closed INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(username, receipt))"""
INDEX = "CREATE INDEX IF NOT EXISTS camera_visual_target ON camera_visual_sessions(username,target_key,created_at DESC)"
LAT, LNG = 48.864173348628704, 2.330499567661377
TARGET_KEY = 'map:48.86417:2.3305:Kamera sklepu'
IMAGES = ('paris-01-dusk.png', 'paris-02-night.png', 'paris-03-dawn.png')
LEASE_SECONDS = 60
RENEW_BEFORE = 20


def generate_motion(previous=None):
    """Persisted per grant/player, never shared by camera coordinates."""
    start = [5 + secrets.randbelow(41), 5 + secrets.randbelow(41)]
    while True:
        end = [5 + secrets.randbelow(41), 5 + secrets.randbelow(41)]
        previous = previous or {}
        old_vector = [b-a for a,b in zip(previous.get('start',[]),previous.get('end',[]))]
        if sum((a - b) ** 2 for a, b in zip(start, end)) >= 400 and [b-a for a,b in zip(start,end)] != old_vector:
            break
    # Quadratic Bezier control point: a gentle perpendicular bow. All points
    # remain inside the valid crop, so the entire curve is inside it as well.
    dx, dy = end[0] - start[0], end[1] - start[1]
    bend = (1 if secrets.randbelow(2) else -1) * .18
    control = [round(max(0, min(50, (start[0]+end[0])/2 - dy*bend)), 3),
               round(max(0, min(50, (start[1]+end[1])/2 + dx*bend)), 3)]
    return dict(version=2, image=secrets.randbelow(len(IMAGES)), scale=2,
                mode='ping-pong', start=start, control=control, end=end,
                seconds=180 + secrets.randbelow(121))


def enabled(username):
    return bool(username) and (os.environ.get('CHAOS_CAMERA_STREET_VIEW') == '1' or (os.environ.get('CHAOS_CAMERA_VISUAL_PILOT') == '1'
            and username == os.environ.get('CHAOS_CAMERA_VISUAL_PILOT_USER', 'main')))


def accepts_target(target):
    return pilot_target(target) or (os.environ.get('CHAOS_CAMERA_STREET_VIEW') == '1'
                                   and bool(target.get('camera_id')))


def pilot_target(target):
    try:
        return (abs(float(target.get('lat')) - LAT) < 1e-9
                and abs(float(target.get('lng', target.get('lon'))) - LNG) < 1e-9
                and target.get('target_mode', 'standard') == 'standard')
    except (TypeError, ValueError, AttributeError):
        return False


def eligible(app):
    return all(value in (app.get(key) or []) for key, value in (
        ('map_actions', 'camera_stream'), ('operation_types', 'camera_stream'),
        ('target_types', 'camera')))


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


class PilotError(ValueError):
    pass


@contextmanager
def transaction(path):
    # Paid creator choices already own a gameplay transaction. Join it through
    # db_connect's guarded savepoint rather than committing independently.
    from database import _runtime_transaction, atomic_runtime_transaction, db_connect
    with (db_connect(path) if _runtime_transaction.get() else atomic_runtime_transaction(path)) as conn:
        yield conn


class CameraVisual:
    def __init__(self, runtime):
        self.rt = runtime
        self.path = runtime.player_inventory_store.db_path

    def app(self, conn, username, app_id):
        row = conn.execute("SELECT app_json FROM player_apps WHERE username=? AND app_id=? AND status='installed'",
                           (username, app_id)).fetchone()
        app = self.rt.normalize_app_contract(json.loads(row['app_json'])) if row else {}
        if not eligible(app):
            raise PilotError('camera_app_not_authorized')
        return app

    def target(self, conn, username, requested=None):
        target = self.rt.player_target_runtime_store.get_active_target(username) or {}
        if requested and requested.get('camera_id') and os.environ.get('CHAOS_CAMERA_STREET_VIEW') == '1':
            from response_network.camera_contract import CameraContractStore, CameraContractError
            try:
                observed = CameraContractStore(self.path).observed(username, requested.get('scan_id'), requested['camera_id'], conn=conn)
            except CameraContractError as exc:
                raise PilotError(str(exc)) from exc
            if target.get('camera_id') == requested['camera_id']:
                return target
            return {**observed, 'scan_id': requested['scan_id']}
        if os.environ.get('CHAOS_CAMERA_STREET_VIEW') == '1' and not (
                os.environ.get('CHAOS_CAMERA_VISUAL_PILOT') == '1' and username == os.environ.get('CHAOS_CAMERA_VISUAL_PILOT_USER','main')):
            raise PilotError('camera_scan_required')
        if pilot_target(target) and self.rt.infer_target_type_from_target(target) == 'camera':
            return target
        # The operator's legacy camera exists in canonical operation history.
        # This is identity evidence for selecting it, never a successful grant.
        row = conn.execute("""SELECT operation_json FROM player_operations
            WHERE username=? AND target_key=? AND operation_type='camera_stream'
            ORDER BY updated_at DESC LIMIT 1""", (username, TARGET_KEY)).fetchone()
        target = json.loads(row['operation_json']).get('target', {}) if row else {}
        if not pilot_target(target) or self.rt.infer_target_type_from_target(target) != 'camera':
            raise PilotError('camera_target_unavailable')
        return target

    def guard(self, conn, username, target):
        position = self.rt.player_position_store.get(username, conn=conn)
        capability = self.rt.capability_projection_store.get_capabilities(username, conn=conn)
        if not position or not capability:
            raise PilotError('camera_position_unavailable')
        lat, lng = float(target['lat']), float(target.get('lng', target.get('lon')))
        distance = self.rt.Haversine.haversine_distance(position['lat'], position['lng'], lat, lng)
        if distance > capability['action_range']:
            raise PilotError('camera_out_of_range')
        if self.rt.foreign_territory_action_block(username, lat, lng):
            raise PilotError('camera_foreign_territory')

    def launch(self, username, data):
        with transaction(self.path) as conn:
            target = self.target(conn, username, data)
            self.guard(conn, username, target)
            app_id = str(data.get('selected_app_id') or '')[:160]
            if not app_id:
                rows = conn.execute("""SELECT app_json FROM player_apps WHERE username=? AND status='installed'
                    AND EXISTS (SELECT 1 FROM json_each(app_json,'$.map_actions') WHERE value='camera_stream')
                    LIMIT 64""", (username,)).fetchall()
                apps = [self.rt.normalize_app_contract(json.loads(row['app_json'])) for row in rows]
                return dict(success=True, tool_selection_required=True, auto_select=False,
                    matching_apps=[self.rt.serialize_tool_selection_app(a) for a in apps if eligible(a)],
                    pending_action={**target, 'action': 'camera_stream', '_flow_id': data.get('_flow_id'),
                                    '_client_action_key': data.get('_client_action_key')},
                    map_action_id='camera_stream', canonical_action='scan_ports')
            app = self.app(conn, username, app_id)
            key = str(data.get('_client_action_key') or data.get('_flow_id') or '')[:160]
            if not key:
                raise PilotError('camera_launch_key_required')
            receipt = 'cvn_' + hashlib.sha256(f'{username}:{app_id}:{key}'.encode()).hexdigest()[:32]
            target = self.rt.player_target_runtime_store.upsert_aimed(username, target, conn=conn).get('target') or target
            launch = dict(receipt=receipt, app_id=app_id, name=app.get('name'), action='camera_stream',
                          flow_id=data.get('_flow_id') or '', expected_target=target)
            self.rt.player_inventory_store.commit_launch(username, [launch], [], self.rt.system_message_store, conn=conn)
            return dict(success=True, target=target, added_apps=[launch], created_operations=[],
                        map_action_id='camera_stream', status='Uruchomiono aplikację kamery.')

    def result(self, username, data):
        from creator_policy import runtime_effect, fileless_data_operation, supports_target_type
        receipt = str(data.get('launch_receipt') or data.get('launch_key') or '')[:160]
        app_id = str(data.get('app_id') or '')[:160]
        if not receipt:
            raise PilotError('camera_launch_key_required')
        with transaction(self.path) as conn:
            app = self.app(conn, username, app_id)
            row = conn.execute('SELECT * FROM camera_visual_sessions WHERE username=? AND receipt=?',
                               (username, receipt)).fetchone()
            if row:
                expected = json.loads(row['payload_json'])['target']
                if row['app_id'] != app_id or self.rt.build_operation_target_id(expected) != self.rt.build_operation_target_id(data.get('expected_target') or {}):
                    raise PilotError('camera_receipt_mismatch')
                return self.reply(conn, row, duplicate=True)
            target = self.rt.player_target_runtime_store.get_active_target(username) or {}
            if (not accepts_target(target) or self.rt.infer_target_type_from_target(target) != 'camera'
                    or self.rt.build_operation_target_id(target) != self.rt.build_operation_target_id(data.get('expected_target') or {})):
                raise PilotError('target_selection_changed')
            if target.get('camera_id'):
                self.target(conn, username, target)  # Revalidate canonical scan evidence.
            elif os.environ.get('CHAOS_CAMERA_STREET_VIEW') == '1':
                self.target(conn, username, target)
            self.guard(conn, username, target)
            # A desktop launch is allowed, but its target must be the canonical aim.
            # Queue receipts, when present, must belong to this installed app.
            launch = conn.execute('SELECT payload_json FROM player_launch_entries WHERE username=? AND receipt=?',
                                  (username, receipt)).fetchone()
            if data.get('launch_source') == 'launch_queue' and not launch:
                raise PilotError('camera_receipt_unknown')
            if launch and json.loads(launch['payload_json']).get('app_id') != app_id:
                raise PilotError('camera_receipt_mismatch')
            if data.get('operation_only'):
                return dict(success=True, operation_only=True, created_operations=[])
            if fileless_data_operation(app):
                raise PilotError('camera_file_contract_required')
            choice_id = data.get('choice_id')
            if choice_id in ('', 'run_generated'):
                choice_id = None
            security = dict(target.get('security') or {})
            effect = runtime_effect(app, security, choice_id, operation_only=False)
            if app.get('creator_contract_version') and not supports_target_type(app.get('creator_contract') or {}, 'camera'):
                raise PilotError('camera_app_not_authorized')
            required = self.rt.resolve_app_required_off_state(security, app.get('requires_off', []))
            success = bool(required['satisfied'])
            if effect is None and choice_id is not None:
                try:
                    if isinstance(choice_id, bool) or int(choice_id) < 0:
                        raise ValueError()
                    effect = app['levels'][0]['options'][int(choice_id)].get('effect', {})
                except (KeyError, IndexError, ValueError, TypeError):
                    raise PilotError('invalid_choice')
            now = time.time()
            target_key = self.rt.build_operation_target_id(target)
            state = dict(success=success, reference_id=receipt, app_id=app_id,
                         app_name=app.get('name') or app_id, target=target,
                         state='session_close' if success else 'failure',
                         close_at=now + 5 if success else None, operation_id=None)
            if success:
                existing = conn.execute('''SELECT * FROM camera_visual_sessions WHERE username=? AND target_key=?
                    AND operation_id IS NOT NULL AND viewer_closed=0
                    AND json_extract(payload_json,'$.reference_id')=receipt
                    ORDER BY created_at DESC LIMIT 1''', (username, target_key)).fetchone()
                if existing and self.project(conn, existing)['state'] not in ('cancelled', 'failed', 'consumed'):
                    previous = json.loads(existing['payload_json'])
                    state.update(operation_id=previous['operation_id'], instance_id=previous['instance_id'],
                                 download_at=previous['download_at'], ready_at=previous['ready_at'])
                    # Persist the new invocation as an alias: retries still resolve
                    # to this grant even if its operation is later cancelled.
                    conn.execute('''INSERT INTO camera_visual_sessions
                        (username,receipt,target_key,app_id,operation_id,payload_json,created_at)
                        VALUES (?,?,?,?,?,?,?)''', (username, receipt, target_key, app_id,
                        previous['operation_id'], existing['payload_json'], now))
                    return self.reply(conn, existing, duplicate=True)
                security.update(effect or {k: False for k in app.get('interferes_with', []) if k in security})
                target['security'] = security
                self.rt.player_target_runtime_store.upsert_aimed(username, target)
                operation = self.rt.build_operation_instance(username, app, 'camera_stream', 'camera_stream', target)
                duration = max(1, self.rt.parse_operation_timestamp(operation['expires_at']) - self.rt.parse_operation_timestamp(operation['started_at']))
                start, end = now + 5, now + 5 + duration
                operation.update(started_at=iso(start), expires_at=iso(end), duration_seconds=duration,
                                 camera_visual={'receipt': receipt, 'download_at': start, 'ready_at': end})
                accepted = self.rt.player_operation_store.upsert_operations(username, [operation],
                    event_type='operation.started', source='camera_visual')
                if not accepted:
                    raise PilotError('camera_operation_conflict')
                last = conn.execute('SELECT payload_json FROM camera_visual_sessions WHERE username=? AND target_key=? AND operation_id IS NOT NULL ORDER BY created_at DESC LIMIT 1', (username,target_key)).fetchone()
                previous_motion = json.loads(last['payload_json']).get('motion') if last else None
                state.update(operation_id=operation['operation_id'], download_at=start, ready_at=end,
                             instance_id='camera-view-' + hashlib.sha256(f'{username}:{receipt}'.encode()).hexdigest()[:24],
                             motion=generate_motion(previous_motion), target_key=target_key)
                from camera_visual_archive import ArchiveStore
                state['archive_id'] = ArchiveStore(self.path).enqueue(conn, target)
            conn.execute('''INSERT INTO camera_visual_sessions
                (username,receipt,target_key,app_id,operation_id,payload_json,created_at) VALUES (?,?,?,?,?,?,?)''',
                (username, receipt, target_key, app_id, state['operation_id'], encoded(state), now))
            row = conn.execute('SELECT * FROM camera_visual_sessions WHERE username=? AND receipt=?', (username, receipt)).fetchone()
            return self.reply(conn, row)

    def activation(self, state):
        content = encoded(dict(version=1, operation_id=state['operation_id'], instance_id=state['instance_id'], target_key=state.get('target_key', TARGET_KEY)))
        return dict(id='activation-' + state['operation_id'], name='Glass Eye.activation',
                    file_category='system', file_size=1, resource_type='camera_activation',
                    sellable=False, market_status='not_listed', source_operation_id=state['operation_id'],
                    content=content, checksum=hashlib.sha256(content.encode()).hexdigest(), created_at=iso(time.time()))

    def verified(self, conn, username, state):
        expected = self.activation(state)
        row = conn.execute('SELECT file_json FROM player_data_files WHERE username=? AND file_id=? AND operation_id=?',
                           (username, expected['id'], state['operation_id'])).fetchone()
        actual = json.loads(row['file_json']) if row else {}
        return all(actual.get(k) == expected[k] for k in ('id', 'content', 'checksum', 'resource_type'))

    def project(self, conn, row):
        state = json.loads(row['payload_json'])
        state.update(viewer_closed=bool(row['viewer_closed']), reference_closed=bool(row['reference_closed']))
        if not state['success']:
            return state
        now = time.time()
        op = conn.execute('SELECT status,operation_json FROM player_operations WHERE username=? AND operation_id=?',
                          (row['username'], state['operation_id'])).fetchone()
        operation = json.loads(op['operation_json']) if op else {}
        # Gameplay may accelerate an already running operation. Its timestamps
        # are the only clock; the original payload is not a second countdown.
        state['download_at'] = self.rt.parse_operation_timestamp(operation.get('started_at')) or state['download_at']
        state['ready_at'] = self.rt.parse_operation_timestamp(operation.get('expires_at')) or state['ready_at']
        duration = max(1, state['ready_at'] - state['download_at'])
        state['progress'] = max(0, min(100, int((now - state['download_at']) / duration * 100)))
        if not op or op['status'] in ('cancelled', 'canceled', 'failed', 'expired', 'detected'):
            state['state'] = 'cancelled'
        elif operation.get('creator_payment_pending') or (operation.get('creator_payment_settled') or {}).get('success') is False:
            state['state'] = 'payment_pending'
        elif now < state['close_at']:
            state['state'] = 'session_close'
        elif now < state['ready_at'] or op['status'] not in ('completed', 'timeout', 'done'):
            state['state'] = 'downloading'
        else:
            state['state'] = 'ready' if self.verified(conn, row['username'], state) else 'save_pending'
        if row['viewer_closed']:
            state['state'] = 'consumed'
        if state.get('archive_id'):
            from camera_visual_archive import ArchiveStore
            manifest = ArchiveStore(self.path).manifest(conn, state['archive_id'])
            state['visual_status'] = manifest['status']
            material = next((i for i in manifest['images'] if i['image_id'] == state.get('image_id')), None)
            state['material'] = {k:v for k,v in material.items() if k not in ('file',)} if material else None
        return state

    def reply(self, conn, row, duplicate=False):
        state = self.project(conn, row)
        operations = []
        if state.get('operation_id'):
            op = conn.execute('SELECT operation_json FROM player_operations WHERE username=? AND operation_id=?',
                              (row['username'], state['operation_id'])).fetchone()
            operations = [json.loads(op['operation_json'])] if op else []
        return dict(success=state['success'], duplicate=duplicate, camera_visual=state,
                    created_operations=operations, target=state['target'],
                    message='Połączenie przyjęte.' if state['success'] else 'Operacja kamery nie powiodła się.')

    def finalize(self, username, operation):
        if not operation.get('camera_visual'):
            return
        # Completed grants are visited by the existing worker. Do not acquire
        # a write lock every tick when their activation is already present.
        from database import db_connect
        with db_connect(self.path) as conn:
            row = conn.execute('SELECT * FROM camera_visual_sessions WHERE username=? AND operation_id=? LIMIT 1',
                               (username, operation['operation_id'])).fetchone()
            if not row or self.project(conn, row)['state'] != 'save_pending':
                return
        with transaction(self.path) as conn:
            row = conn.execute('SELECT * FROM camera_visual_sessions WHERE username=? AND operation_id=? LIMIT 1',
                               (username, operation['operation_id'])).fetchone()
            if not row or self.project(conn, row)['state'] != 'save_pending':
                return
            state = json.loads(row['payload_json'])
            file = self.activation(state)
            if conn.execute('SELECT 1 FROM player_data_file_tombstones WHERE username=? AND file_id=?', (username, file['id'])).fetchone():
                return
            storage = conn.execute('SELECT capacity,used FROM player_storage WHERE username=?', (username,)).fetchone()
            if not storage or storage['capacity'] - storage['used'] < file['file_size']:
                return
            self.rt.player_inventory_store.append_data_files(username, [file], operation_id=operation['operation_id'])
            if not self.verified(conn, username, state):
                raise PilotError('camera_activation_verification_failed')

    def snapshot(self, username):
        from database import db_connect
        with db_connect(self.path) as conn:
            rows = conn.execute('''SELECT * FROM camera_visual_sessions WHERE username=?
                AND json_extract(payload_json,'$.reference_id')=receipt
                ORDER BY viewer_closed ASC, (operation_id IS NULL) ASC, created_at DESC LIMIT 64''', (username,)).fetchall()
            result = []
            for row in rows:
                try:
                    self.app(conn, username, row['app_id'])
                except PilotError:
                    continue
                result.append(self.project(conn, row))
            return result

    def window(self, username, data):
        owner = str(data.get('owner') or '')
        if not 16 <= len(owner) <= 100:
            raise PilotError('camera_window_owner_invalid')
        # Most heartbeats are read-only. Renew only near expiry, under the
        # same serialized transaction used for ownership changes.
        from database import db_connect
        if data.get('action', 'claim') == 'claim':
            with db_connect(self.path) as conn:
                row = conn.execute('SELECT * FROM camera_visual_sessions WHERE username=? AND receipt=?',
                                   (username, data.get('receipt'))).fetchone()
                if row and row['lease_owner'] == owner and not row['viewer_closed'] and row['lease_until'] > time.time() + RENEW_BEFORE:
                    state = self.project(conn, row)
                    self.app(conn, username, row['app_id'])
                    needs_image = state.get('archive_id') and not state.get('image_id') and state.get('visual_status') == 'READY'
                    if state['reference_id'] == row['receipt'] and state['state'] == 'ready' and (state.get('motion') or {}).get('version') == 2 and not needs_image:
                        return dict(success=True, granted=True, lease_until=row['lease_until'], camera_visual=state)
        with transaction(self.path) as conn:
            row = conn.execute('''SELECT * FROM camera_visual_sessions WHERE username=? AND receipt=?
                AND json_extract(payload_json,'$.reference_id')=receipt''',
                (username, data.get('receipt'))).fetchone()
            if not row:
                raise PilotError('camera_session_unknown')
            self.app(conn, username, row['app_id'])
            action = data.get('action', 'claim')
            if action == 'reopen':
                raise PilotError('camera_new_hack_required')
            if action == 'close_reference':
                conn.execute('UPDATE camera_visual_sessions SET reference_closed=1 WHERE username=? AND receipt=?', (username, row['receipt']))
                return dict(success=True)
            if action == 'release':
                conn.execute('UPDATE camera_visual_sessions SET lease_until=0 WHERE username=? AND receipt=? AND lease_owner=?',
                             (username, row['receipt'], owner))
                return dict(success=True, granted=False)
            if row['viewer_closed']:
                return dict(success=True, granted=False, closed=True)
            state = self.project(conn, row)
            if state['state'] != 'ready':
                raise PilotError('camera_activation_not_ready')
            now = time.time()
            if row['lease_owner'] != owner and row['lease_until'] > now:
                return dict(success=True, granted=False)
            if action == 'close':
                if row['lease_owner'] != owner:
                    raise PilotError('camera_window_owner_changed')
                conn.execute('UPDATE camera_visual_sessions SET viewer_closed=1,lease_until=0 WHERE username=? AND receipt=?', (username, row['receipt']))
                return dict(success=True, granted=False, closed=True)
            if row['viewer_closed']:
                return dict(success=True, granted=False)
            if action != 'claim':
                raise PilotError('camera_window_action_invalid')
            if (state.get('motion') or {}).get('version') != 2:
                # Upgrade old pilot grants once; snapshot/media reads never write.
                payload = json.loads(row['payload_json'])
                payload['motion'] = state['motion'] = generate_motion()
                conn.execute('UPDATE camera_visual_sessions SET payload_json=? WHERE username=? AND receipt=?',
                             (encoded(payload), username, row['receipt']))
            if state.get('archive_id') and not state.get('image_id'):
                from camera_visual_archive import ArchiveStore
                manifest = ArchiveStore(self.path).manifest(conn, state['archive_id'])
                if manifest['images']:
                    payload = json.loads(row['payload_json'])
                    payload['motion'] = state['motion']
                    payload['image_id'] = manifest['images'][state['motion']['image'] % len(manifest['images'])]['image_id']
                    conn.execute('UPDATE camera_visual_sessions SET payload_json=? WHERE username=? AND receipt=?',
                                 (encoded(payload),username,row['receipt']))
                    row = conn.execute('SELECT * FROM camera_visual_sessions WHERE username=? AND receipt=?',(username,row['receipt'])).fetchone()
                    state = self.project(conn,row)
            until = now + LEASE_SECONDS
            conn.execute('UPDATE camera_visual_sessions SET lease_owner=?,lease_until=?,viewer_closed=0 WHERE username=? AND receipt=?',
                         (owner, until, username, row['receipt']))
            return dict(success=True, granted=True, lease_until=until, camera_visual=state)
