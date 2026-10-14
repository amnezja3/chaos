"""BlackNet source-language contract. ANY is a declaration, never an output locale."""
import hashlib
import json

from database import db_connect
from ghost_i18n import approved_locales
from radio_locale import language, track_allowed
from .narrative_locale import rollout_locales, supported_locales

POLICY = 'blacknet-source-language-v1'
SCHEMA = '''CREATE TABLE IF NOT EXISTS blacknet_signal_languages (
    signal_id TEXT PRIMARY KEY, contract_json TEXT NOT NULL)'''


class SignalLanguageError(ValueError):
    pass


def declarations():
    return sorted(supported_locales()) + ['ANY']


def validate_declaration(value):
    if not isinstance(value, str) or value not in declarations():
        raise SignalLanguageError('invalid_signal_language')
    return value


def radio_declaration(channel, track):
    """Return a concrete locale or explicit neutrality; unknown is not neutral."""
    channel_locale, track_locale = language(channel.get('language')), language(track.get('language'))
    if not track_allowed(channel, track):
        raise SignalLanguageError('radio_language_conflict')
    if channel_locale in approved_locales('radio'):
        return channel_locale
    if track_locale in approved_locales('radio'):
        return track_locale
    if channel_locale == 'neutral' and track_locale == 'neutral':
        return 'ANY'
    raise SignalLanguageError('radio_language_unknown')


def resolve(signal_id, metadata, *, enabled=None):
    if not signal_id:
        raise SignalLanguageError('missing_signal_identity')
    enabled = tuple(sorted(set(rollout_locales() if enabled is None else enabled)))
    if not enabled or any(item not in supported_locales() for item in enabled):
        raise SignalLanguageError('invalid_signal_language_pool')
    source = 'neutral'
    declaration = 'ANY'
    if metadata.get('channel_id') and metadata.get('track_file'):
        source = 'radio'
        declaration = radio_declaration({'language': metadata.get('channel_language')},
                                        {'language': metadata.get('track_language')})
        explicit = metadata.get('signal_language')
        if explicit not in (None, 'ANY', declaration):
            raise SignalLanguageError('signal_source_language_conflict')
    elif metadata.get('product_id'):
        source = 'product'
        declaration = metadata.get('signal_language', 'unknown')
        if declaration == 'unknown':
            raise SignalLanguageError('product_language_unknown')
        validate_declaration(declaration)
    elif 'signal_language' in metadata:
        declaration = validate_declaration(metadata['signal_language'])
    if declaration != 'ANY' and declaration not in enabled:
        raise SignalLanguageError('source_language_not_enabled')
    locale = declaration if declaration != 'ANY' else enabled[
        int(hashlib.sha256(signal_id.encode()).hexdigest()[:8], 16) % len(enabled)]
    return dict(version=POLICY, output_locale=locale, declaration=declaration,
                source_type=source, source_id=str(metadata.get('channel_id') or metadata.get('product_id') or signal_id),
                source_version=str(metadata.get('source_version') or ''),
                reason='source' if declaration != 'ANY' else 'neutral_rotation')


def pin(db_path, signal_id, metadata):
    """Schema is installed by the migrator, never by a gameplay read."""
    # Public signal/dedupe identity is untouched. Each actual source edition has
    # its own immutable choice; a radio slot may point at another recording later.
    source = [metadata.get('channel_id'), metadata.get('track_file'),
              metadata.get('product_id'), metadata.get('source_version')]
    ledger_id = signal_id + ':' + hashlib.sha256(json.dumps(source).encode()).hexdigest()[:24]
    with db_connect(db_path) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT contract_json FROM blacknet_signal_languages WHERE signal_id=?', (ledger_id,)).fetchone()
        if row:
            return json.loads(row[0])
        contract = resolve(signal_id, metadata)
        conn.execute('INSERT INTO blacknet_signal_languages VALUES (?,?)',
                     (ledger_id, json.dumps(contract, ensure_ascii=False, sort_keys=True)))
        return contract
