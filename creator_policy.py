"""Server-owned creator recipes. No profile IO and no user-provided runtime flags."""
import copy
import math
import secrets

import config

INTERFACES = {'progressbar_random', 'terminal', 'window', 'button_choices'}
SECURITY_KEYS = (
    'stealth_mode', 'scan_detection', 'exploit_protection', 'vpn_enabled',
    'browser_protection', 'os_hardening', 'log_guardian', 'process_monitor',
    'firewall', 'log_integrity', 'network_anomaly_detection', 'spoofing_protection',
    'activity_monitor', 'player_tracking', 'system_visibility', 'firewall_core',
    'kernel_guard', 'system_integrity_check', 'heap_protection', 'memory_lock',
    'background_injection', 'memory_guard', 'vpn_blocker',
)
WORLD = ['poi', 'server', 'router', 'pillar']


def recipe(action, family, kind, targets, operation=None, resources=(), keys=()):
    return dict(action=action, tool_family=family, type=kind, tool_mode='hybrid',
                map_actions=[action], target_types=targets,
                operation_types=[operation] if operation else [],
                resource_types=list(resources), security_keys=list(keys))


RECIPES = {
    'exploit': recipe('exploit', 'exploit', 'exploit', WORLD, keys=SECURITY_KEYS),
    'scan_ports': recipe('scan_ports', 'scanner_recon', 'scanner', WORLD,
                         resources=['internal_recon_state']),
    'trace': recipe('trace', 'scanner_recon', 'tracker', WORLD, 'generic_trace', ['gps_logs']),
    'trace_gps': recipe('trace_gps', 'scanner_recon', 'tracker', ['vehicle'], 'vehicle_tracking', ['gps_logs']),
    'trace_device': recipe('trace_device', 'scanner_recon', 'tracker', ['person', 'phone'], 'device_tracking', ['device_logs']),
    'scan_hotspots': recipe('scan_hotspots', 'scanner_recon', 'scanner', ['venue'], 'wifi_scanner', ['wifi_networks']),
    'camera_stream': recipe('camera_stream', 'scanner_recon', 'scanner', ['camera'], 'camera_stream', ['camera_dump']),
    'camera_shutdown': recipe('camera_shutdown', 'exploit', 'camera_tool', ['camera'], 'camera_shutdown'),
    'install_sniffer': recipe('install_sniffer', 'sniffer', 'sniffer', WORLD, 'persistent_sniffer', ['credentials']),
    'sniff': recipe('sniff', 'sniffer', 'sniffer', WORLD, 'persistent_sniffer', ['credentials']),
    'mic_sniff': recipe('mic_sniff', 'sniffer', 'sniffer', ['person', 'phone', 'venue'], 'microphone_sniffer', ['audio_transcript']),
    'atm_logs': recipe('atm_logs', 'sniffer', 'sniffer', ['atm'], 'atm_log_extraction', ['atm_dump']),
    'audio_hack': recipe('audio_hack', 'exploit', 'exploit', ['venue'], 'audio_interference'),
    'car_hack': recipe('car_hack', 'exploit', 'vehicle_tool', ['vehicle'], 'vehicle_ecu', ['vehicle_diagnostics']),
}


def power_cap(level):
    if type(level) is not int or level < 1:
        raise ValueError('Brak prawidlowego poziomu autora.')
    points = config.CREATOR_POWER_CAPS
    for (lo, a), (hi, b) in zip(points, points[1:]):
        if level <= hi:
            return int(a + (b - a) * (level - lo) / (hi - lo))
    return points[-1][1]


def roll_power(level, rng=None):
    rng = rng or secrets.SystemRandom()
    cap = power_cap(level)
    maximum = rng.random() < config.CREATOR_MAX_POWER_CHANCE
    value = cap if maximum else rng.randint(min(config.CREATOR_MIN_POWER, cap - 1), cap - 1)
    return dict(power=value, power_cap=cap, maximum_roll=maximum,
                creator_level=level, policy_version=config.CREATOR_POLICY_VERSION)


def price(value, default=0):
    if value is None:
        return default
    if type(value) is not int or not 0 <= value <= config.CREATOR_MAX_PRICE:
        raise ValueError('Cena musi byc calkowita kwota w dozwolonym zakresie.')
    return value


def validate_effect(value, *, action, interface, level):
    if interface != 'button_choices':
        if value:
            raise ValueError('Reczny effect jest dostepny tylko w Button Choice.')
        return {}
    if level < config.CREATOR_EFFECT_MIN_LEVEL:
        return {}  # Visible draft text has no authority below the unlock level.
    if not value:
        return {}
    if action != 'exploit':
        raise ValueError('Ten profil nie obsluguje recznej zmiany zabezpieczen.')
    if value == 'security.clear':
        return {key: False for key in SECURITY_KEYS}
    if not isinstance(value, dict) or not value:
        raise ValueError('Nieznany effect. Uzyj security.clear lub zatwierdzonych kluczy.')
    if any(key not in SECURITY_KEYS or val is not False for key, val in value.items()):
        raise ValueError('Effect moze wylaczac tylko zatwierdzone zabezpieczenia.')
    return dict(value)


def generate_contract(data, level, rng=None):
    allowed = {'name', 'icon', 'action', 'creates_file', 'interface', 'effect', 'price'}
    if not isinstance(data, dict) or set(data) - allowed:
        raise ValueError('Niedozwolone pola generatora.')
    action, interface = data.get('action'), data.get('interface')
    if action not in RECIPES or interface not in INTERFACES:
        raise ValueError('Nieznana akcja lub kreator.')
    if type(data.get('creates_file')) is not bool:
        raise ValueError('Wybierz czy tworzyc plik.')
    result = copy.deepcopy(RECIPES[action])
    if data['creates_file'] and not result['resource_types']:
        raise ValueError('Ta akcja nie tworzy pliku.')
    result.update(interface=interface, creates_file=data['creates_file'],
                  price=price(data.get('price')), effect=validate_effect(data.get('effect'),
                    action=action, interface=interface, level=level))
    result.update(roll_power(level, rng))
    if not result['creates_file']:
        result['resource_types'] = []
    return result


def security_effect(contract, security):
    """Deterministic target-relative influence; rendering/retries cannot reroll it."""
    if contract['action'] != 'exploit':
        return {}
    if contract.get('effect'):
        return {key: value for key, value in contract['effect'].items() if key in security}
    keys = [key for key in contract['security_keys'] if type(security.get(key)) is bool]
    # A partial tool never silently gets 100% due to rounding on a small target.
    count = len(keys) if contract['power'] == 100 else math.floor(len(keys) * contract['power'] / 100)
    return {key: False for key in keys[:count]}


def configure_draft(contract, changes, level):
    """Final editor may configure commercial terms/effects before publication.

    The generated purpose and random power are never regenerated by this call.
    """
    if not isinstance(changes, dict) or set(changes) - {'price', 'effect', 'options'}:
        raise ValueError('Niedozwolona zmiana mechaniki.')
    result = copy.deepcopy(contract)
    if 'price' in changes:
        result['price'] = price(changes['price'], default=contract['price'])
    if 'effect' in changes:
        result['effect'] = validate_effect(changes['effect'], action=contract['action'],
            interface=contract['interface'], level=level)
    if 'options' in changes:
        options = changes['options']
        if contract['interface'] != 'button_choices' or not isinstance(options, list) or not 1 <= len(options) <= 32:
            raise ValueError('Opcje sa dostepne tylko w Button Choice (1 do 32).')
        validated = []
        for index, option in enumerate(options):
            if not isinstance(option, dict) or set(option) - {'effect', 'price'}:
                raise ValueError('Opcja moze okreslac tylko effect i cene uzycia.')
            validated.append(dict(id=index, price=price(option.get('price')),
                effect=validate_effect(option.get('effect'), action=contract['action'],
                    interface=contract['interface'], level=level)))
        result['options'] = validated
    return result


def runtime_effect(app, security, choice_id=None, *, operation_only=False):
    """Resolve the installed edition, never the latest catalog or author's level.

    None means historical executor semantics; an empty dict is a valid v1
    operation with no immediate security mutation.
    """
    if not app.get('creator_contract_version'):
        return None
    if app['creator_contract_version'] != config.CREATOR_POLICY_VERSION:
        raise ValueError('Nieobslugiwana wersja kontraktu aplikacji.')
    contract = app.get('creator_contract')
    if not isinstance(contract, dict) or contract.get('policy_version') != config.CREATOR_POLICY_VERSION:
        raise ValueError('Nieprawidlowy kontrakt zainstalowanej aplikacji.')
    if operation_only:
        return {}
    if contract.get('interface') == 'button_choices':
        # DOM dataset values are strings; accept only canonical option indices.
        if isinstance(choice_id, str) and choice_id in {str(i) for i in range(32)}:
            choice_id = int(choice_id)
        if type(choice_id) is not int or choice_id < 0:
            raise ValueError('Wybierz prawidlowa opcje aplikacji.')
        options = app.get('levels', [{}])[0].get('options', [])
        if choice_id >= len(options):
            raise ValueError('Nieprawidlowy choice_id.')
        if 'options' in contract:
            if choice_id >= len(contract['options']):
                raise ValueError('Opcja nie nalezy do kontraktu.')
            contract = dict(contract, effect=contract['options'][choice_id]['effect'])
    elif choice_id is not None:
        raise ValueError('Ten interfejs nie obsluguje choice_id.')
    return security_effect(contract, security)


def validate_presentation(interface, value):
    """Only presentation fields: option effects, prices and action IDs are not text."""
    common = {'name', 'icon', 'description', 'title'}
    fields = {
        'terminal': {'commands'}, 'window': {'logs', 'button_labels'},
        'button_choices': {'prompt', 'option_labels'},
        'progressbar_random': {'steps', 'result_success', 'result_failure'},
    }
    if not isinstance(value, dict) or set(value) - common - fields[interface]:
        raise ValueError('Po publikacji mozna zmieniac tylko prezentacje.')
    def text(item, limit=6000, required=False):
        if not isinstance(item, str) or len(item) > limit or '\x00' in item:
            raise ValueError('Nieprawidlowy tekst prezentacji.')
        if required and not item.strip():
            raise ValueError('Wymagany niepusty tekst.')

    def texts(items, required=False, limit=6000):
        if not isinstance(items, list) or len(items) > 32 or (required and not items):
            raise ValueError('Wymagana lista maksymalnie 32 pozycji.')
        for item in items:
            text(item, limit, required)

    for key, item in value.items():
        if key == 'commands':
            if not isinstance(item, list) or not 1 <= len(item) <= 32:
                raise ValueError('Wymagane 1 do 32 komend.')
            seen = set()
            for command in item:
                if not isinstance(command, dict) or set(command) != {'command', 'logs'}:
                    raise ValueError('Komenda wymaga tekstu command i listy logs.')
                text(command['command'], 120, True)
                normalized = command['command'].strip().casefold()
                if normalized in seen:
                    raise ValueError('Komendy musza byc unikalne.')
                seen.add(normalized)
                texts(command['logs'])
        elif key in {'logs', 'steps', 'button_labels', 'option_labels'}:
            labels = key in {'button_labels', 'option_labels'}
            texts(item, required=key != 'logs', limit=120 if labels else 6000)
        else:
            text(item, 80 if key == 'name' else 128 if key == 'icon' else 6000,
                 key in {'name', 'icon'})
            if key == 'name' and (';' in item or '\n' in item or '\r' in item):
                raise ValueError('Nieprawidlowa nazwa aplikacji.')
    return copy.deepcopy(value)
