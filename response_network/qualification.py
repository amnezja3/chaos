"""142.4: bounded, server-owned detection qualification; no penalty execution."""
import hashlib
import os
from contextlib import nullcontext
from datetime import datetime, timezone

from database import db_connect
from session_generation_store import username_digest
from .detection_validator import _coerce_datetime, _distance_m, _position
from .npc_capsule_factory import BEHAVIOR_VERSION, position_at
from .npc_capsule_store import ACTIVE_CAPSULE_STATUSES


def qualification_mode():
    # Enforcement is deliberately unavailable until encounter/executor hardening.
    value = os.environ.get('CHAOS_RESPONSE_QUALIFICATION_MODE', 'observe')
    return 'observe' if value == 'observe' else 'disabled'


def actor_snapshot(db_path, username, *, conn=None):
    """Three indexed point reads in one snapshot, never a profile fallback."""
    owned = conn is None
    with (db_connect(db_path) if owned else nullcontext(conn)) as conn:
        if owned:
            conn.execute('BEGIN')
        ownership = conn.execute('SELECT status,updated_at,active_revision FROM account_login_ownership WHERE username_hash=?',
            (username_digest(username),)).fetchone()
        presence = conn.execute('SELECT last_seen_at FROM mail_presence WHERE username=?', (username,)).fetchone()
        position = conn.execute('SELECT lat,lng,version,updated_at FROM player_positions WHERE username=?', (username,)).fetchone()
        return {'session': dict(ownership) if ownership else None,
                'presence': dict(presence) if presence else None,
                'position': dict(position) if position else None}


class DetectionQualification:
    def __init__(self, incidents, capsules, candidates, actor_reader):
        self.incidents, self.capsules, self.candidates = incidents, capsules, candidates
        self.actor_reader = actor_reader

    def qualify(self, payload, observer, now=None, *, record=True):
        now = _coerce_datetime(now or datetime.now(timezone.utc))
        mode = qualification_mode()
        result = {'status': 'rejected', 'reason': '', 'mode': mode,
                  'qualification_version': 'response-142-4', 'qualified': False,
                  'consequence_executed': False, 'penalty_executed': False,
                  'validated_at': now.isoformat()}
        def reject(reason, status='rejected'):
            return {**result, 'status': status, 'reason': reason, 'qualified': False}
        if mode == 'disabled':
            return reject('qualification_disabled', 'disabled')
        if not observer:
            return reject('observer_not_authenticated')
        if not isinstance(payload, dict):
            return reject('invalid_payload')
        candidate = {key: payload.get(key) for key in ('actor_id', 'incident_id', 'capsule_id',
            'tracking_token', 'trajectory_seed', 'behavior_version', 'detected_at',
            'position_version', 'actor_position', 'npc_position')}
        for key in ('actor_id', 'incident_id', 'capsule_id'):
            value = candidate[key]
            if not isinstance(value, str) or not value.strip() or len(value) > 160:
                return reject('missing_or_invalid_identity')
            candidate[key] = value.strip()
        result.update({key: candidate[key] for key in ('actor_id', 'incident_id', 'capsule_id')})
        try:
            if not candidate['detected_at']:
                return reject('missing_detection_time')
            detected = _coerce_datetime(candidate['detected_at'])
            age = (now - detected).total_seconds()
            if age > 15 or age < -3:
                return reject('stale_detection_time' if age > 15 else 'future_detection_time')
            version = int(candidate['position_version'])
            behavior = int(candidate['behavior_version'])
            if version < 1:
                return reject('invalid_position_version')
        except (TypeError, ValueError, OverflowError, OSError):
            return reject('invalid_detection_contract')
        try:
            actor = self.actor_reader(candidate['actor_id'])
            ownership = actor.get('session') or {}
            state = ownership.get('status')
            if state == 'logged_out':
                return reject('actor_offline')
            if state == 'expired':
                return reject('actor_session_expired')
            if state != 'active':
                return reject('session_projection_missing', 'deferred')
            if detected < _coerce_datetime(ownership['updated_at']):
                return reject('detection_before_current_login')
            presence = actor.get('presence') or {}
            if not presence.get('last_seen_at'):
                return reject('presence_projection_missing', 'deferred')
            presence_age = (now - _coerce_datetime(presence['last_seen_at'])).total_seconds()
            if presence_age < -3:
                return reject('presence_time_invalid', 'deferred')
            if presence_age > 90:
                return reject('actor_offline')
            canonical = actor.get('position') or {}
            position = _position(canonical)
            if not position or not (-90 <= position['lat'] <= 90 and -180 <= position['lng'] <= 180):
                return reject('position_projection_missing', 'deferred')
            if version != int(canonical.get('version') or 0):
                return reject('stale_position_version')
            position_age = (now - _coerce_datetime(canonical['updated_at'])).total_seconds()
            if position_age < -3:
                return reject('position_time_invalid', 'deferred')
            # Stationary players keep an old position timestamp. Heartbeat and
            # current revision, not coordinate age alone, establish freshness.
            result['presence_class'] = 'online_inactive' if position_age > 90 else 'online_active'
            error = _distance_m(position, candidate['actor_position'])
            reported = _position(candidate['actor_position'])
            if not reported or not (-90 <= reported['lat'] <= 90 and -180 <= reported['lng'] <= 180):
                return reject('invalid_actor_position')
            if error is None or error > 15:
                return reject('actor_position_mismatch')
            incident = self.incidents.get(candidate['incident_id'])
            if not incident or incident.get('status') not in {'active', 'escalated', 'cooling'}:
                return reject('incident_not_active')
            if incident['status'] == 'cooling' and _coerce_datetime(incident['expires_at']) <= now:
                return reject('incident_cooling_expired')
            capsule = self.capsules.get(candidate['capsule_id'])
            if not capsule or capsule.get('status') not in ACTIVE_CAPSULE_STATUSES:
                return reject('capsule_not_active')
            if capsule.get('incident_id') != candidate['incident_id']:
                return reject('capsule_incident_mismatch')
            if not (_coerce_datetime(capsule['spawn_at']) <= min(detected, now)
                    and max(detected, now) < _coerce_datetime(capsule['expires_at'])):
                return reject('capsule_time_window_closed')
            if candidate['tracking_token'] not in (capsule.get('tracking_tokens') or []):
                return reject('invalid_tracking_token')
            if behavior != int(capsule.get('behavior_version') or BEHAVIOR_VERSION):
                return reject('behavior_version_mismatch')
            if candidate['trajectory_seed'] != capsule.get('trajectory_seed'):
                return reject('trajectory_seed_mismatch')
            npc_error = _distance_m(position_at(capsule, detected), candidate['npc_position'])
            if npc_error is None or npc_error > 45:
                return reject('npc_position_mismatch')
            distance = _distance_m(position_at(capsule, now), position)
            radius = float(capsule.get('detection_radius_m') or 0)
            if distance is None or not 0 < radius < 100000 or distance > radius:
                return reject('actor_outside_detection_radius')
            suspects = {ref.get('actor_id') for ref in incident.get('suspect_refs', []) if isinstance(ref, dict)}
            result.update(actor_role='initiator' if candidate['actor_id'] in suspects else 'bystander',
                position_version=version, incident_version=incident.get('version'),
                distance_m=round(distance, 2), detection_radius_m=radius,
                status='observed', reason='qualified_observation_only', qualified=True)
            key = '|'.join((candidate['actor_id'], candidate['incident_id'], candidate['capsule_id'],
                str(ownership.get('active_revision')), str(version), str(int(now.timestamp() // 10))))
            result['validation_key'] = 'qualification:' + hashlib.sha256(key.encode()).hexdigest()[:32]
            candidate.update(candidate_id=result['validation_key'], validation_key=result['validation_key'],
                observer_username=observer, mode=mode, actor_position=position, operation_id='')
            if not record:
                return result
            stored, created = self.candidates.record(candidate, result, now=now)
            return {**result, 'candidate_id': (stored or candidate)['candidate_id'], 'duplicate': not created}
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            return reject('projection_invalid', 'deferred')
