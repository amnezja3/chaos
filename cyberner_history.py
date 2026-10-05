"""Bounded World context; storage remains untouched."""
from datetime import datetime, timedelta, timezone


def world_history(messages, *, limit=100, after_id=None, before_id=None, now=None):
    if after_id not in (None, '') and before_id not in (None, ''):
        raise ValueError('Use either after_id or before_id.')
    limit = max(1, min(int(limit or 100), 100))
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=14)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=timezone.utc)
    latest = list(messages)[-100:]

    def recent(message):
        try:
            timestamp = datetime.fromisoformat(str(message.get('created_at') or '').replace('Z', '+00:00'))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            return timestamp >= cutoff
        except (TypeError, ValueError):
            return False

    visible = [message for message in latest if recent(message)] or latest[-10:]
    # Cursors operate inside the same window, never unlock older history or
    # trigger fallback merely because a recovery request has no new messages.
    if after_id not in (None, ''):
        cursor = max(0, int(after_id))
        return [message for message in visible if int(message['id']) > cursor][:limit]
    if before_id not in (None, ''):
        cursor = max(0, int(before_id))
        visible = [message for message in visible if int(message['id']) < cursor]
    return visible[-limit:]
