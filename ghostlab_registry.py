"""Code-owned GhostLab contracts. No database or profile access.

New logic is implemented in code; the registry only describes allowed contracts.
Runtime stays unavailable until a registered executor is integrated in 145/146.
"""
from copy import deepcopy

TEMPLATES = {'financial_sniffer': {'id': 'financial_sniffer',
                       'name': 'Financial Sniffer',
                       'icon': '💸',
                       'category': 'finance',
                       'tool_category': 'finance',
                       'description': 'Jednorazowa operacja finansowa na aktywnym dostępie do gracza.',
                       'recommended_level': 12,
                       'required_respect': 180,
                       'risk_level': 5,
                       'price': 4200,
                       'source_tool_id': 'financialSniffer',
                       'schema_version': 1,
                       'policy_version': 1,
                       'contract_version': 1,
                       'target_kind': 'player',
                       'launch_mode': 'player_hack_access',
                       'result_type': 'financial_sniffer',
                       'executor_id': None,
                       'creation_enabled': True,
                       'publication_enabled': True,
                       'runtime_enabled': False,
                       'presentation_ids': ['default'],
                       'fields': {'steal_percent': {'type': 'number',
                                                    'default': 8,
                                                    'editable': True,
                                                    'minimum': 1,
                                                    'maximum': 8,
                                                    'integer': False},
                                  'detection_percent': {'type': 'number',
                                                        'default': 18,
                                                        'editable': True,
                                                        'minimum': 0,
                                                        'maximum': 95,
                                                        'integer': False},
                                  'cooldown_minutes': {'type': 'number',
                                                       'default': 180,
                                                       'editable': True,
                                                       'minimum': 5,
                                                       'maximum': 1440,
                                                       'integer': True},
                                  'success_message': {'type': 'string',
                                                      'default': 'Financial Sniffer przechwycil drobny '
                                                                 'przeplyw HC.',
                                                      'editable': True,
                                                      'max_length': 240},
                                  'failure_message': {'type': 'string',
                                                      'default': 'Operacja finansowa zostala wygaszona przez '
                                                                 'zabezpieczenia.',
                                                      'editable': True,
                                                      'max_length': 240},
                                  'reward_note': {'type': 'string',
                                                  'default': 'HC transfer draft',
                                                  'editable': True,
                                                  'max_length': 160}},
                       'app_contract': {'tool_family': 'sniffer',
                                        'tool_mode': 'desktop',
                                        'map_actions': [],
                                        'target_types': ['player'],
                                        'operation_types': [],
                                        'resource_types': ['financial_records', 'internal_recon_state']}},
 'friend_kicker': {'id': 'friend_kicker',
                   'name': 'Friend Kicker',
                   'icon': '👋',
                   'category': 'social',
                   'tool_category': 'social',
                   'description': 'Losowa próba zerwania jednego kontaktu ofiary.',
                   'recommended_level': 10,
                   'required_respect': 150,
                   'risk_level': 4,
                   'price': 3600,
                   'source_tool_id': 'friendKicker',
                   'schema_version': 1,
                   'policy_version': 1,
                   'contract_version': 1,
                   'target_kind': 'player',
                   'launch_mode': 'player_hack_access',
                   'result_type': 'friend_kicker',
                   'executor_id': None,
                   'creation_enabled': True,
                   'publication_enabled': True,
                   'runtime_enabled': False,
                   'presentation_ids': ['default'],
                   'fields': {'success_percent': {'type': 'number',
                                                  'default': 45,
                                                  'editable': True,
                                                  'minimum': 1,
                                                  'maximum': 85,
                                                  'integer': False},
                              'detection_percent': {'type': 'number',
                                                    'default': 20,
                                                    'editable': True,
                                                    'minimum': 0,
                                                    'maximum': 95,
                                                    'integer': False},
                              'target_policy': {'type': 'string',
                                                'default': 'random_contact',
                                                'editable': False,
                                                'max_length': 80},
                              'victim_message': {'type': 'string',
                                                 'default': 'Wykryto probe manipulacji kontaktami.',
                                                 'editable': True,
                                                 'max_length': 240},
                              'contact_message': {'type': 'string',
                                                  'default': 'Polaczenie z jednym z graczy zostalo zerwane.',
                                                  'editable': True,
                                                  'max_length': 240}},
                   'app_contract': {'tool_family': 'exploit',
                                    'tool_mode': 'desktop',
                                    'map_actions': [],
                                    'target_types': ['player'],
                                    'operation_types': [],
                                    'resource_types': ['internal_recon_state']}},
 'security_panel_proxy': {'id': 'security_panel_proxy',
                          'name': 'Security Panel Proxy',
                          'icon': '🛡️',
                          'category': 'security',
                          'tool_category': 'security',
                          'description': 'Zdalny panel ustawień zabezpieczeń celu.',
                          'recommended_level': 15,
                          'required_respect': 240,
                          'risk_level': 3,
                          'price': 5200,
                          'source_tool_id': 'securityPanelProxy',
                          'schema_version': 1,
                          'policy_version': 1,
                          'contract_version': 1,
                          'target_kind': 'player',
                          'launch_mode': 'player_hack_access',
                          'result_type': 'security_panel',
                          'executor_id': None,
                          'creation_enabled': True,
                          'publication_enabled': True,
                          'runtime_enabled': False,
                          'presentation_ids': ['default'],
                          'fields': {'allowed_switches': {'type': 'string',
                                                          'default': 'boolean_security_only',
                                                          'editable': False,
                                                          'max_length': 120},
                                     'presets': {'type': 'string',
                                                 'default': 'open, low, regular, secure, all',
                                                 'editable': False,
                                                 'max_length': 160},
                                     'rules': {'type': 'string',
                                               'default': 'apply SECURITY_CONFLICTS',
                                               'editable': False,
                                               'max_length': 240},
                                     'conflict_matrix': {'type': 'string',
                                                         'default': 'locked_until_compiler',
                                                         'editable': False,
                                                         'max_length': 240}},
                          'app_contract': {'tool_family': 'exploit',
                                           'tool_mode': 'desktop',
                                           'map_actions': [],
                                           'target_types': ['player'],
                                           'operation_types': [],
                                           'resource_types': ['internal_recon_state']}},
 'system_log_reader': {'id': 'system_log_reader',
                       'name': 'System Log Reader',
                       'icon': '📜',
                       'category': 'intel',
                       'tool_category': 'intel',
                       'description': 'Bezpieczny odczyt ostatnich komunikatów systemowych celu.',
                       'recommended_level': 8,
                       'required_respect': 90,
                       'risk_level': 2,
                       'price': 2800,
                       'source_tool_id': 'systemLogReader',
                       'schema_version': 1,
                       'policy_version': 1,
                       'contract_version': 1,
                       'target_kind': 'player',
                       'launch_mode': 'player_hack_access',
                       'result_type': 'system_logs',
                       'executor_id': None,
                       'creation_enabled': True,
                       'publication_enabled': True,
                       'runtime_enabled': False,
                       'presentation_ids': ['default'],
                       'fields': {'log_limit': {'type': 'number',
                                                'default': 5,
                                                'editable': True,
                                                'minimum': 1,
                                                'maximum': 5,
                                                'integer': True},
                                  'include_type': {'type': 'boolean', 'default': True, 'editable': True},
                                  'include_status': {'type': 'boolean', 'default': True, 'editable': True},
                                  'include_created_at': {'type': 'boolean',
                                                         'default': True,
                                                         'editable': True},
                                  'redaction_policy': {'type': 'string',
                                                       'default': 'system_messages_only',
                                                       'editable': False,
                                                       'max_length': 120}},
                       'app_contract': {'tool_family': 'scanner_recon',
                                        'tool_mode': 'desktop',
                                        'map_actions': [],
                                        'target_types': ['player'],
                                        'operation_types': [],
                                        'resource_types': ['device_logs', 'internal_recon_state']}},
 'arsenal_cleaner': {'id': 'arsenal_cleaner',
                     'name': 'Arsenal Cleaner',
                     'icon': '🧹',
                     'category': 'apps',
                     'tool_category': 'apps',
                     'description': 'Losowa próba usunięcia aplikacji z arsenału ofiary.',
                     'recommended_level': 14,
                     'required_respect': 220,
                     'risk_level': 5,
                     'price': 4700,
                     'source_tool_id': 'arsenalCleaner',
                     'schema_version': 1,
                     'policy_version': 1,
                     'contract_version': 1,
                     'target_kind': 'player',
                     'launch_mode': 'player_hack_access',
                     'result_type': 'arsenal_cleaner',
                     'executor_id': None,
                     'creation_enabled': True,
                     'publication_enabled': True,
                     'runtime_enabled': False,
                     'presentation_ids': ['default'],
                     'fields': {'success_percent': {'type': 'number',
                                                    'default': 40,
                                                    'editable': True,
                                                    'minimum': 1,
                                                    'maximum': 80,
                                                    'integer': False},
                                'detection_percent': {'type': 'number',
                                                      'default': 22,
                                                      'editable': True,
                                                      'minimum': 0,
                                                      'maximum': 95,
                                                      'integer': False},
                                'target_policy': {'type': 'string',
                                                  'default': 'random_non_core_app',
                                                  'editable': False,
                                                  'max_length': 100},
                                'protected_apps': {'type': 'string',
                                                   'default': 'Terminal, Mapa, Browser, Email, Wallet HC, '
                                                              'Profil, Pliki',
                                                   'editable': False,
                                                   'max_length': 240},
                                'remove_tools_file': {'type': 'boolean', 'default': True, 'editable': True}},
                     'app_contract': {'tool_family': 'exploit',
                                      'tool_mode': 'desktop',
                                      'map_actions': [],
                                      'target_types': ['player'],
                                      'operation_types': [],
                                      'resource_types': ['internal_recon_state']}}}


# Explicit code-owned classification. Intruder contract is prepared in 144.3.
TEMPLATES['intruder_kicker'] = {
    'id': 'intruder_kicker', 'name': 'Intruder Kicker', 'icon': '🚷',
    'category': 'territory', 'tool_category': 'territory',
    'description': 'Usuwa intruza z własnego terytorium przy aktywnym dostępie PvP. Jedno użycie rodziny na dostęp.',
    'recommended_level': 1, 'required_respect': 0, 'risk_level': 0, 'price': 7500,
    'source_tool_id': 'intruderKicker', 'schema_version': 1, 'policy_version': 1, 'contract_version': 1,
    'target_kind': 'player', 'launch_mode': 'player_hack_access', 'result_type': 'intruder_kicker',
    'executor_id': None, 'creation_enabled': True, 'publication_enabled': True, 'runtime_enabled': False,
    'presentation_ids': ['default'],
    'fields': {
        'target_policy': {'type': 'string', 'default': 'intruder_in_own_territory', 'editable': False, 'max_length': 80},
        'usage_policy': {'type': 'string', 'default': 'once_per_access_family', 'editable': False, 'max_length': 80},
        'success_message': {'type': 'string', 'default': 'Intruz został usunięty z terytorium.', 'editable': True, 'max_length': 240},
    },
    'app_contract': {'tool_family': 'exploit', 'tool_mode': 'desktop', 'map_actions': [],
                     'target_types': ['player'], 'operation_types': [], 'resource_types': ['internal_recon_state']},
}

PRO_TOOL_GLAB = {
    'financialSniffer': 'financial_sniffer', 'friendKicker': 'friend_kicker',
    'systemLogReader': 'system_log_reader', 'securityPanelProxy': 'security_panel_proxy',
    'arsenalCleaner': 'arsenal_cleaner', 'intruderKicker': 'intruder_kicker',
    'victimPicker': None, 'territoryControl': None, 'operationControl': None,
    'ghostnetworkSuite': None, 'agi2108Console': None,
}
PLANNED_CONTRACTS = {
    'travel_ticket': {'source_tool_id': None, 'target_kind': 'destination', 'launch_mode': 'desktop'},
    'system_maintenance': {'source_tool_id': None, 'target_kind': 'own_system', 'launch_mode': 'desktop'},
    'storage_extension': {'source_tool_id': None, 'target_kind': 'own_storage', 'launch_mode': 'desktop'},
    'map_marker_scan': {'source_tool_id': None, 'target_kind': 'map_decoration', 'launch_mode': 'map'},
    'deep_scanner': {'source_tool_id': None, 'target_kind': 'player', 'launch_mode': 'map'},
}


def get_template(template_id):
    return deepcopy(TEMPLATES.get(str(template_id or '')))


def default_blueprint(template_id):
    definition = get_template(template_id)
    if not definition:
        return {'notes': ''}
    return {key: field['default'] for key, field in definition['fields'].items()}


def field_schema(template_id):
    definition = get_template(template_id)
    if definition:
        return definition['fields']
    if template_id in ('', 'custom', None):
        return {'notes': {'type': 'string', 'default': '', 'editable': True, 'max_length': 240}}
    return {}


def validate_fields(template_id, blueprint):
    import math
    definition = get_template(template_id)
    if not definition:
        if template_id not in ('', 'custom', None):
            return ['Nieznany szablon.']
        fields = field_schema(template_id)
    else:
        fields = definition['fields']
    if not isinstance(blueprint, dict) or set(blueprint) != set(fields):
        return ['Blueprint musi zawierac dokladnie pola wybranego szablonu.']
    errors = []
    for key, field in fields.items():
        value = blueprint[key]
        if not field['editable'] and value != field['default']:
            errors.append(f'{key}: wymagana polityka serwera.')
        if field['type'] == 'number':
            if type(value) not in (int, float) or (type(value) is float and not math.isfinite(value)):
                errors.append(f'{key}: wymagana skonczona liczba.')
            elif (not field['minimum'] <= value <= field['maximum']
                  or (field.get('integer') and int(value) != value)):
                errors.append(f'{key}: liczba poza zakresem lub niecalkowita.')
        elif field['type'] == 'boolean':
            if type(value) is not bool:
                errors.append(f'{key}: wymagany boolean.')
        elif field['type'] == 'string':
            if not isinstance(value, str) or not value.strip() or len(value) > field['max_length']:
                errors.append(f'{key}: nieprawidlowy tekst.')
        else:
            errors.append(f'{key}: nieobslugiwany typ pola.')
    return errors


def template_available(template_id, action):
    if action not in ('creation', 'publication', 'runtime'):
        return False
    definition = get_template(template_id)
    if not definition or not definition.get(action + '_enabled'):
        return False
    # No executor is integrated in 144.1. A config flag alone cannot grant execution.
    return action != 'runtime'


def public_templates():
    result = []
    for template_id in TEMPLATES:
        if not template_available(template_id, 'creation'):
            continue
        item = get_template(template_id)
        item.pop('executor_id', None)
        item['runtime_enabled'] = template_available(template_id, 'runtime')
        item['status'] = 'Blueprint ready / runtime pending'
        result.append(item)
    return result


def artifact_compatible(artifact, template_id):
    definition = get_template(template_id)
    if not definition or artifact.get('template_id') != template_id:
        return False
    # Legacy 144 artifacts have schema/policy=1 and no contract_version.
    return (artifact.get('schema_version', 1) == definition['schema_version']
            and artifact.get('policy_version', 1) == definition['policy_version']
            and artifact.get('contract_version', 1) == definition['contract_version']
            and artifact.get('runtime_contract') == definition['result_type']
            and artifact.get('presentation_id', 'default') in definition['presentation_ids'])


def validate_pro_tool_assignments(tools):
    ids = {tool['id'] for tool in tools}
    if ids != set(PRO_TOOL_GLAB):
        raise ValueError('Explicit GLab/non-GLab assignment required for every system pro-tool')
    for tool_id, template_id in PRO_TOOL_GLAB.items():
        if template_id is None:
            continue
        definition = get_template(template_id)
        if not definition or definition['source_tool_id'] != tool_id:
            raise ValueError('Invalid GLab source binding: ' + tool_id)


def pro_tool_classification(tool_id):
    if tool_id not in PRO_TOOL_GLAB:
        raise ValueError('Missing GLab classification: ' + tool_id)
    template_id = PRO_TOOL_GLAB[tool_id]
    definition = get_template(template_id) or {}
    return {'glab_enabled': template_id is not None, 'glab_template_id': template_id,
            'glab_contract_version': definition.get('contract_version')}
