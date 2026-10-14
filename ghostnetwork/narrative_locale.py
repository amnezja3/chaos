"""Server-owned, durable language selection; never reselected on retry/read."""
import hashlib
import json
import os
from functools import lru_cache
from pathlib import Path

from ghost_i18n import approved_locales

CONTRACT_VERSION = 'narrative-language-v1'
ROOT = Path(__file__).resolve().parent / 'llm'


@lru_cache(maxsize=1)
def language_registry():
    return json.loads((ROOT / 'narrative_languages.v1.json').read_text(encoding='utf-8'))


def supported_locales():
    return ({'pl'} | (set(language_registry()) - {'version'})) & set(approved_locales('narration'))


def rollout_locales():
    values = tuple(dict.fromkeys(os.environ.get('CHAOS_NARRATIVE_LOCALES', 'pl').split(',')))
    if not values or any(v not in supported_locales() for v in values):
        raise ValueError('unapproved_narrative_rollout_locale')
    return values


def freeze_language(item):
    """Persist in validation_json without changing publication/dedupe identity."""
    from .llm.registry import OLLAMA_TASK_POLICY_REGISTRY
    identity = (item.get('source_scope') or 'ghostnetwork', item.get('task_variant') or 'default',
                item.get('target_medium') or item.get('medium'))
    policy = OLLAMA_TASK_POLICY_REGISTRY.get(identity)
    if not policy or item.get('prompt_version') != policy.prompt_version:
        return dict(item)  # Existing legacy/unassigned contracts remain unchanged.
    enabled = rollout_locales()
    requested = item.get('output_locale')
    medium = identity[2]
    if requested is not None and requested not in supported_locales():
        raise ValueError('unapproved_narrative_output_locale')
    event = str(item.get('source_event_id') or item.get('event_id') or item.get('source_receipt_id') or '')
    # News has one canonical source and reader variants. UGC product copy is
    # never translated. BN picks once per event, shared by all its audiences.
    locale = requested or ('pl' if medium != 'blacknet' else enabled[
        int(hashlib.sha256(event.encode()).hexdigest()[:8], 16) % len(enabled)])
    if medium == 'googleplex_news' and locale != 'pl':
        raise ValueError('news_requires_reader_variant_path')
    contract = dict(version=CONTRACT_VERSION, output_locale=locale, medium=medium,
        language_policy='reader_locale' if medium == 'googleplex_news' else 'original_language',
        event_id=event, content_version=str(item.get('selected_source_version') or item.get('canon_version') or ''),
        facts_version=hashlib.sha256(json.dumps(item.get('facts') or [], sort_keys=True,
            ensure_ascii=False, separators=(',', ':')).encode()).hexdigest(),
        prompt_version=policy.prompt_version, locale_prompt_version=language_registry()[locale]['prompt_version'] if locale != 'pl' else policy.prompt_version)
    source = (item.get('validation') or {}).get('source_language_contract')
    if source:
        if source.get('output_locale') != locale:
            raise ValueError('source_language_contract_mismatch')
        contract['source'] = dict(source)
    if medium == 'blacknet' and os.environ.get('CHAOS_BLACKNET_LANGUAGES_ENABLED', '').lower() in ('1', 'true', 'yes'):
        contract['presentation'] = 'blacknet-prefix-v1'
    return {**item, 'validation': {**(item.get('validation') or {}), 'language_contract': contract}}


def task_language(task):
    contract = (task.get('validation') or {}).get('language_contract')
    if not contract:
        return 'pl', None
    if (not isinstance(contract, dict) or contract.get('version') != CONTRACT_VERSION
            or contract.get('output_locale') not in supported_locales()
            or contract.get('medium') != (task.get('target_medium') or task.get('medium'))
            or contract.get('prompt_version') != task.get('prompt_version')):
        raise ValueError('invalid_narrative_language_contract')
    expected_facts = hashlib.sha256(json.dumps(task.get('facts') or [], sort_keys=True,
        ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    if contract.get('facts_version') != expected_facts:
        raise ValueError('narrative_language_facts_changed')
    locale = contract['output_locale']
    expected_prompt = language_registry()[locale]['prompt_version'] if locale != 'pl' else task.get('prompt_version')
    if contract.get('locale_prompt_version') != expected_prompt:
        raise ValueError('narrative_locale_prompt_version_mismatch')
    return contract['output_locale'], dict(contract)


def english_layers(policy, locale='en'):
    from .llm.registry import _read_versioned_prompt
    config = language_registry()[locale]
    family = config['policies'].get(policy.prompt_version)
    if not family:
        raise ValueError('narrative_locale_prompt_not_registered')
    system = _read_versioned_prompt(ROOT / config['system_prompt'], config['prompt_version'])
    domain = config['families'][family]
    return system, domain


def english_fallback(medium, family, audience, locale='en'):
    config = language_registry()[locale]
    body = config['fallbacks'].get(family)
    if not body:
        return None
    if family == 'part_discovered' and audience == 'owner':
        body = config['owner_part_discovered']
    return {'tone':'warning', 'title':[config['blacknet_fallback_title'] if medium == 'blacknet' else config['fallback_title']],
            'body':[('...' if medium == 'blacknet' else '') + body]}
