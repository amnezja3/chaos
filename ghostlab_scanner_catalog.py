"""System-owned presentation vocabulary; never arbitrary CSS, URLs or HTTP policy."""
import unicodedata

COLORS = {'green': '#b6ff54', 'cyan': '#65eaff', 'amber': '#ffcd67', 'violet': '#d0a2ff'}
FRAMES = ('solid', 'double', 'dashed')
PATTERNS = ('regular',)  # 146.4.2 adds the other implemented/verified patterns.
SOUNDS = {'regular_sweep': 'scanner.regular.sweep', 'regular_ping': 'scanner.regular.ping'}
LOGS = {
    'start': {'init': 'Inicjalizacja skanera', 'signal': 'Analiza sygnału'},
    'empty': {'quiet': 'Brak nowych sygnałów', 'warning': 'WARNING — sprawdź inny obszar'},
    'success': {'found': 'Znaleziono sygnały', '300': '300 — wiele tropów do sprawdzenia'},
    'error': {'network': 'Problemy z siecią', 'warning': 'WARNING — skan nie został ukończony'},
    'denied': {'system': 'Operacja niedostępna', '403': '403 — dostęp do operacji zablokowany'},
}


def menu_length(value):
    # NFC + Unicode scalars, identical to Array.from(text.normalize('NFC')).
    # The icon is a separate glyph; the label never widens its fixed CSS slot.
    return len(unicodedata.normalize('NFC', value.strip()))


def fields():
    def choice(label, values, default):
        return dict(type='string', label=label, enum=list(values), default=default, editable=True, max_length=40)
    result = {
        'menu_name': dict(type='string', label='Nazwa przycisku (maks. 12 znaków Unicode)', default='DeepScan',
                          editable=True, max_length=12, unicode_scalars=True),
        'pattern_id': choice('Animacja', PATTERNS, 'regular'),
        'sfx_id': choice('Dźwięk skanera', SOUNDS, 'regular_sweep'),
        'frame_id': choice('Ramka', FRAMES, 'solid'),
        'frame_color': choice('Kolor ramki', COLORS, 'green'),
        'button_color': choice('Kolor przycisku', COLORS, 'green'),
        'extra_retries': dict(type='number', label='Dodatkowe próby API', default=0, editable=True, minimum=0, maximum=3, integer=True),
        'extra_timeout': dict(type='number', label='Dodatkowy timeout (s)', default=0, editable=True, minimum=0, maximum=10, integer=True),
    }
    labels = {'start': 'Start', 'empty': 'Brak wykrycia', 'success': 'Wykrycie', 'error': 'Błąd API', 'denied': 'Odmowa'}
    for phase, choices in LOGS.items():
        result[phase + '_log'] = choice(labels[phase] + ' — preset logu', choices, next(iter(choices)))
        result[phase + '_text'] = dict(type='string', label=labels[phase] + ' — własny tekst (opcjonalny)',
                                      default='', editable=True, max_length=180, allow_empty=True)
    return result


def presentation(product):
    blueprint = dict(product['blueprint'])
    blueprint['menu_name'] = unicodedata.normalize('NFC', blueprint['menu_name'].strip())
    return dict(app_id=product['id'], artifact_id=product['artifact_id'], name=product['name'], icon=product['icon'],
                **blueprint, colors=COLORS, sfx_event=SOUNDS[blueprint['sfx_id']],
                logs={phase: blueprint[phase + '_text'].strip() or choices[blueprint[phase + '_log']]
                      for phase, choices in LOGS.items()})
