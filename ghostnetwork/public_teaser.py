"""A deliberately small anonymous projection of an already-public publication."""
import secrets


def select_public_teaser(repository):
    # No viewer identity, generation, language pinning, read receipts or CTA data.
    records = repository.list_narrative_medium_records(
        'blacknet', audience_scope='public', active_only=True, limit=100,
    )
    candidates = [record for record in records
                  if record.get('audience_scope') == 'public'
                  and record.get('active_state') == 'active'
                  and str(record.get('title') or '').strip()
                  and str(record.get('body') or '').strip()]
    if not candidates:
        return None
    record = secrets.choice(candidates)
    body = str(record['body']).strip()
    return {
        'title': str(record['title']).strip()[:160],
        'body': body[:280].rstrip() + ('…' if len(body) > 280 else ''),
        'locale': record.get('output_locale') if record.get('output_locale') in ('pl', 'en') else '',
    }
