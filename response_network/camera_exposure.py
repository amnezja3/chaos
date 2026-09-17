"""Bounded, server-owned scan evidence and per-player camera mitigation."""
from datetime import datetime, timezone

from database import db_connect, loads_json
from response_network.camera_contract import camera_parent_key


def capture_exposure(db_path, username, target):
    """Freeze evidence once; client camera counts/off flags are never evidence."""
    unknown = {"schema": 1, "known": False, "camera_ids": []}
    try:
        lat = float(target['lat'])
        lng = float(target.get('lng', target.get('lon')))
    except (KeyError, TypeError, ValueError):
        return unknown
    with db_connect(db_path) as conn:
        row = conn.execute('''SELECT scan_id, markers_json FROM player_scan_snapshots
            WHERE username=? AND expires_at>? AND (?='' OR scan_id=?)
            ORDER BY created_at DESC LIMIT 1''',
            (username, datetime.now(timezone.utc).timestamp(),
             str(target.get('scan_id') or ''), str(target.get('scan_id') or ''))).fetchone()
    if not row:
        return unknown
    markers = loads_json(row['markers_json'], [])[:512]
    matches = [m for m in markers if abs(m['lat'] - lat) < 1e-8
               and abs(m['lng'] - lng) < 1e-8]
    # Ambiguous co-located objects must not share a neighbouring object's cover.
    if len(matches) != 1:
        matches = [m for m in matches if str(m.get('osm_id') or m.get('node_id') or '')
                   == str(target.get('osm_id') or target.get('node_id') or '')
                   and m.get('label') == (target.get('label') or target.get('name'))]
    if len(matches) != 1:
        return unknown
    marker = matches[0]
    scope = marker.get('parent_target_id') or camera_parent_key(marker)
    cameras = sorted({m['camera_id'] for m in markers if m.get('camera_id')
                      and m.get('target_type') == 'camera'
                      and m.get('parent_target_id') == scope})
    return {"schema": 1, "known": True, "owner_username": username,
            "scan_id": row['scan_id'], "scope": scope, "camera_ids": cameras}


def shutdown_windows(db_path, username):
    """One indexed read per actor batch; no profiles or terminal history."""
    with db_connect(db_path) as conn:
        rows = conn.execute('''SELECT
            json_extract(operation_json, '$.camera_evidence.camera_id') AS camera_id,
            json_extract(operation_json, '$.camera_evidence.parent_target_id') AS scope,
            json_extract(operation_json, '$.expires_at') AS expires_at
            FROM player_operations WHERE username=? AND status IN ('start','running')
            AND operation_type='camera_shutdown'
            AND json_extract(operation_json, '$.camera_evidence.schema')=1
            ORDER BY updated_at DESC LIMIT 512''', (username,)).fetchall()
    return [dict(row) for row in rows]


def bind_windows(operation, windows):
    exposure = operation.get('camera_exposure') or {}
    ids = set(exposure.get('camera_ids') or [])
    operation['camera_shutdown_windows'] = [dict(w) for w in windows
        if w.get('camera_id') in ids and w.get('scope') == exposure.get('scope')]


def camera_state(operation, now_ts):
    exposure = operation.get('camera_exposure') or {}
    if (not exposure.get('known') or exposure.get('schema') != 1
            or exposure.get('owner_username') != operation.get('owner_username')):
        return {"known": False, "detected": 0, "disabled": 0, "modifier": 0}
    ids = set(exposure.get('camera_ids') or [])
    disabled = set()
    for window in operation.get('camera_shutdown_windows') or []:
        try:
            end = datetime.fromisoformat(window['expires_at'].replace('Z', '+00:00'))
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            if (end.timestamp() > now_ts and window.get('camera_id') in ids
                    and window.get('scope') == exposure.get('scope')):
                disabled.add(window['camera_id'])
        except (KeyError, TypeError, ValueError):
            continue
    return {"known": True, "detected": len(ids), "disabled": len(disabled),
            "modifier": 4 if ids and not disabled else 0}
