"""Persisted presentation choices; never authorizes gameplay or changes cameras."""
import secrets

VERSION = 1
SCENARIOS = ('grain', 'scan', 'tracking', 'chroma', 'blocks', 'dropout')


def presentation():
    return dict(scenario=secrets.choice(SCENARIOS), intensity=round(.65 + secrets.randbelow(36)/100, 2),
                period=45 + secrets.randbelow(46), phase=secrets.randbelow(45000)/1000,
                offline_seconds=2 + secrets.randbelow(4))


def instance(state, username, *, legacy=False):
    """Called only in the grant transaction, never from snapshot reads."""
    return dict(version=VERSION, instance_id=state['instance_id'], username=username,
                camera_key=state.get('target_key'), operation_id=state['operation_id'],
                activation_id='activation-' + state['operation_id'], image_id=state.get('image_id'),
                motion=state['motion'], visual=(dict(scenario='legacy', intensity=1, period=67,
                phase=0, offline_seconds=3) if legacy else presentation()))


def bind_material(state, materials):
    """Uniform draw from the actual allowed set, bound once even on late arrival."""
    if not materials or state.get('image_id'):
        return False
    selected = secrets.choice(materials)
    state['image_id'] = selected['image_id']
    state['feed']['image_id'] = selected['image_id']
    return True
