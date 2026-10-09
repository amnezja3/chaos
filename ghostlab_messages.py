"""Locale-neutral presentation envelopes; never rewrite persisted author content."""
from ghost_i18n import manifest, translator


def message(key, params=None):
    return dict(key=key, params=params or {}, content_version=manifest()['content_version'])


def error_message(reason):
    key = 'lab.error.' + str(reason)
    if key not in translator().catalogs['pl']['messages']:
        return message('lab.error.failed', {'code': str(reason)})
    return message(key)
