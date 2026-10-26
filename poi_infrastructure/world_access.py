"""Explicit general access, independent of the unchanged bounded pilot."""
import os

from .world_pilot import allowed as pilot_allowed


def allowed(user, spatial):
    mode = os.environ.get('CHAOS_POI_WORLD_ACCESS_MODE', 'pilot')
    if mode == 'global':
        return True
    if mode == 'pilot':
        return pilot_allowed(user, spatial)
    # 'off', typos and unknown future modes must not grant access.
    return False


def network_paused():
    return os.environ.get('CHAOS_POI_SCAN_NETWORK_PAUSED') == '1'
