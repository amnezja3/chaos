"""Pure sentencing plan; this module never executes a consequence."""
import copy
from config import RESPONSE_CONSEQUENCE_TABLE


def plan_consequence(incident_level, previous_executed, *, policy=None):
    policy = policy if policy is not None else RESPONSE_CONSEQUENCE_TABLE
    if type(incident_level) is not int or incident_level not in policy['incident_entry_stage']:
        raise ValueError('invalid_incident_level')
    if type(previous_executed) is not int or previous_executed < 0:
        raise ValueError('invalid_executed_count')
    entry = policy['incident_entry_stage'][incident_level]
    if entry is None:
        return None  # L1 observation; no automatic promotion from history alone.
    stage = min(policy['max_stage'], entry + previous_executed)
    return {'policy_version': policy['version'], 'incident_level': incident_level,
            'previous_executed': previous_executed, 'entry_stage': entry, 'stage': stage,
            **copy.deepcopy(policy['stages'][stage]),
            'detention_rules': copy.deepcopy(policy['detention'])}


def fine_amount(balance, risk, multiplier, *, policy=None):
    """Existing MVP base and protections, multiplied before the wallet cap."""
    policy = policy if policy is not None else RESPONSE_CONSEQUENCE_TABLE
    if any(type(v) is not int or v < 0 for v in (balance, risk, multiplier)):
        raise ValueError('invalid_fine_input')
    if not balance or not multiplier:
        return 0
    fine = policy['fine']
    base = max(fine['minimum_hc'], risk // fine['risk_divisor'])
    reserve = min(fine['reserve_max_hc'], balance * fine['reserve_percent'] // 100)
    cap = max(1, balance * fine['balance_cap_percent'] // 100)
    return min(base * multiplier, cap, max(0, balance - reserve))
