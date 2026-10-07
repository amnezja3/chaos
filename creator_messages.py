"""Typed creator validation and creation-time text defaults; no profile access."""
from ghost_i18n import translator, normalize_locale


class CreatorValidationError(ValueError):
    def __init__(self, code, legacy_message, params=None, option_index=None):
        super().__init__(legacy_message)
        self.locale_key = 'creator.validation.' + code
        self.params = params or {}
        self.option_index = option_index

    def in_option(self, index):
        self.option_index = index
        self.args = (f'Opcja {index}: {self}',)
        return self


def presentation_defaults(interface, locale='pl'):
    """Snapshot editable defaults once. Existing authored presentation wins."""
    locale = normalize_locale(locale)
    def text(key):
        return translator().t('creator.editor.' + key, locale=locale)
    return {
        'terminal': lambda: {'commands': [{'command': 'run', 'logs': [text('default_start')]}]},
        'window': lambda: {'logs': [], 'button_labels': [text('default_run')]},
        'button_choices': lambda: {'prompt': '', 'option_labels': [text('default_execute')]},
        'progressbar_random': lambda: {'steps': [text('default_start')],
            'result_success': text('default_success'), 'result_failure': text('default_failure')},
    }[interface]()
