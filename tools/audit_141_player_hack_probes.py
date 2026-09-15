"""Read-only audit probes of d7d477a with synthetic dependencies.

Never imports run/database or opens a game database. Assertions characterize
the audited defects, not desired regression behavior. Current behavior is
covered separately by the player-hack regression tests.
"""
import ast
import copy
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'd7d477a'
tree = ast.parse(subprocess.check_output(
    ['git', 'show', BASELINE + ':run.py'], cwd=ROOT).decode('utf-8-sig'))
functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}


def extract(name, env):
    node = copy.deepcopy(functions[name])
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'run.py', 'exec'), env)
    return env[name]


catalog = next(ast.literal_eval(n.value) for n in tree.body
               if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'PRO_SYSTEM_TOOLS' for t in n.targets))
report = {'baseline': BASELINE, 'scope': 'extracted functions, synthetic dependencies; no Flask middleware, DB or browser',
          'catalog_ids': [t['id'] for t in catalog], 'probes': {}}
access = {'id': 1, 'attacker_username': 'attacker', 'victim_username': 'victim', 'seconds_left': 100}

# All installed catalog entries are exposed as executable tools, including Suite.
env = {'PRO_SYSTEM_TOOLS': catalog, 'app_is_installed': lambda p, i: True}
items = extract('public_pro_system_tools', env)({'username': 'attacker'})
assert len(items) == len(catalog) and all(t['enabled'] for t in items)
report['probes']['catalog_exposes_all'] = len(items)

# Characterize profile reads including a synthetic >=35 MB account in either role.
costs = []
for big_a, big_v in [(False, False), (True, False), (False, True), (True, True)]:
    profiles = {u: json.dumps({'username': u, 'nick': u,
                              'padding': 'x' * (35 * 1024 * 1024 if big else 0)})
                for u, big in [('attacker', big_a), ('victim', big_v)]}
    reads = []
    def get_profile(username):
        reads.append(len(profiles[username].encode('utf-8')))
        return json.loads(profiles[username])
    env = {'user_store': NS(get_profile=get_profile), 'public_pro_system_tools': lambda p=None: []}
    result = extract('serialize_player_hack_access', env)(access)
    assert result['active'] and len(reads) == 2
    costs.append({'large_attacker': big_a, 'large_victim': big_v,
                  'full_profile_provider_calls': len(reads), 'synthetic_json_bytes_decoded': sum(reads)})
report['probes']['access_serialization'] = costs


def tool_env(tool_id):
    victim = {'username': 'victim', 'level': 1, 'apps': [{'id': 'removable', 'name': 'Demo'}], 'files': {}}
    return {
        'session': {'user': 'attacker'}, 'request': NS(get_json=lambda: {'tool_id': tool_id, 'victim_username': 'victim'}),
        'jsonify': lambda p: p, 'get_pro_system_tool': lambda i: next(t for t in catalog if t['id'] == i),
        'player_hack_access_store': Mock(get_active_access=Mock(return_value=access), has_tool_usage=Mock(return_value=False)),
        'user_store': Mock(get_profile=Mock(return_value=victim)), 'app_is_installed': lambda p, i: True,
        'serialize_player_hack_access': lambda a: a,
        'is_cleanable_app': lambda a: True, 'choice': lambda a: a[0], 'app_display_name': lambda a: a['name'],
        'randint': lambda a, b: 1, 'random': lambda: 0,
        'remove_app_tool_files': lambda f, a: f,
        'player_inventory_store': Mock(uninstall_app=Mock(return_value=True), snapshot=Mock(return_value={'apps': [], 'files': {'tools': []}})),
    }

env = tool_env('victimPicker')
result = extract('api_player_hack_tool_use', env)()
assert result['success'] and 'placeholder' in result['message']
report['probes']['unsupported_tool_fake_success'] = result['message']

env = tool_env('arsenalCleaner')
try:
    extract('api_player_hack_tool_use', env)()
    raise AssertionError('expected uninitialized victim_record')
except UnboundLocalError as exc:
    assert 'victim_record' in str(exc)
    assert env['player_inventory_store'].uninstall_app.call_count == 1
    assert env['player_hack_access_store'].record_tool_usage.call_count == 0
    report['probes']['arsenal_cleaner'] = {'exception': str(exc), 'uninstall_called': 1, 'usage_recorded': 0}

env = {'session': {'user': 'attacker'}, 'request': NS(get_json=lambda: {'victim_username': 'victim', 'key': 'firewall', 'value': False}),
       'jsonify': lambda p: p, 'copy': copy, 'SECURITY_CONFLICTS': {},
       'player_hack_access_store': Mock(get_active_access=Mock(return_value=access)),
       'load_profile_write_record': lambda u: {'profile': {'security': {'firewall': True}}, 'profile_revision': 1},
       'user_store': Mock(), 'serialize_player_hack_access': lambda a: a}
# Deliberately no installed tools/capability provider; handler nevertheless writes.
result = extract('api_player_hack_security_update', env)()
assert result['success'] and env['user_store'].patch_profile_guarded.call_count == 1
report['probes']['security_direct_handler_without_installation'] = 'write accepted; global middleware not exercised'

old_position = {'lat': 52.1, 'lng': 21.1}
new_position = {'lat': 50.1, 'lng': 19.1}
env = {'user_store': NS(get_profile=lambda u: {'username': u, 'curently_possition': old_position}),
       'player_position_store': Mock(get_position=Mock(return_value=new_position)),
       'resolve_player_actor_relation': lambda *a: 'intruder',
       'build_player_actor': lambda *a, **kw: {'actions': {'mark_target': {'enabled': True}}},
       'build_victim_picker_candidate': lambda p, t, *a, **kw: t,
       'mail_store': NS(list_accepted_contacts=lambda u: []),
       'territory_store': NS(list_recent_area_intruders=lambda u: [{'username': 'victim'}])}
result = extract('build_victim_picker_player_candidates', env)('attacker', {}, {}, 1000)
assert result[0]['lat'] == old_position['lat']
assert env['player_position_store'].get_position.call_count == 0
report['probes']['picker_stale_position'] = {'returned': old_position, 'canonical_fixture': new_position, 'canonical_reads': 0}

# Reuse actual actor rules: picker omits strategic combat context.
for name in ['player_actor_action', 'resolve_player_actor_actions', 'build_player_actor']:
    extract(name, env)
env['build_victim_picker_candidate'] = lambda p, t, *a, **kw: {**t, 'can_aim': kw['can_aim']}
result = env['build_victim_picker_player_candidates']('attacker', {}, {}, 1000)
assert result[0]['can_aim'] is False
report['probes']['picker_missing_combat_context'] = 'intruder candidate disabled without combat_relation'

env = {'session': {'user': 'attacker'}, 'jsonify': lambda p: p,
       'user_store': NS(get_profile=lambda u: {'username': u}, list_profiles=lambda: [{'username': 'victim', 'current_position': old_position}]),
       'player_position_store': Mock(get_position=Mock(return_value=new_position)),
       'mail_store': NS(list_pending_contact_names=lambda u: [], list_accepted_contacts=lambda u: []),
       'territory_store': NS(list_player_areas=lambda: []), 'normalize_player_area': lambda a: a,
       'get_profile_clan': lambda p: '', 'get_profile_profession': lambda p: '',
       'build_territory_engagement_visibility_context': lambda u: {},
       'project_territory_actor_visibility': lambda *a, **k: {'visible': True, 'combat_relation': 'hostile'},
       'resolve_player_actor_relation': lambda *a: 'intruder'}
for name in ['player_actor_action', 'resolve_player_actor_actions', 'build_player_actor']:
    extract(name, env)
result = extract('map_player_actors', env)()
assert result['player_actors'][0]['lat'] == old_position['lat']
assert env['player_position_store'].get_position.call_count == 0
report['probes']['map_actor_stale_position'] = 'old profile position returned despite newer canonical fixture'
print(json.dumps(report, ensure_ascii=False, indent=2))
