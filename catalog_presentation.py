"""Presentation metadata attached only at code-owned catalog construction sites."""
from functools import lru_cache
import json
from pathlib import Path

from ghost_i18n import approved_locales, manifest, translator


@lru_cache(maxsize=256)
def _presentation(product_id, version):
    fields = {field: {'key': f'catalog.system.{product_id}.{field}', 'params': {}, 'content_version': version}
              for field in ('name', 'description')}
    aliases = [translator().t(value['key'], locale=locale)
               for locale in approved_locales('interface') for value in fields.values()]
    return fields, tuple(aliases)


def builtin_presentation(product):
    fields, aliases = _presentation(product['id'], manifest()['content_version'])
    return {**product, 'presentation_owner': 'system',
            'presentation_i18n': {name: dict(value) for name, value in fields.items()},
            'search_aliases': list(aliases)}


@lru_cache(maxsize=1)
def legacy_sources():
    return json.loads((Path(__file__).resolve().parent / 'static/locales/system_app_sources.json').read_text(encoding='utf8'))


def legacy_presentation(product, *, authored=False):
    """Project only reviewed, unmodified seed fields; never mutate an installed copy."""
    product = dict(product)
    if authored or any(product.get(k) for k in ('generated', 'creator_username', 'ghostlab_generated', 'artifact_id')):
        product = {k: v for k, v in product.items()
                   if k not in ('presentation_owner', 'presentation_i18n', 'search_aliases')}
    if isinstance(product.get('levels'), list):
        product['levels'] = [{k: v for k, v in level.items() if k != '_system_i18n'}
                             if isinstance(level, dict) else level for level in product['levels']]
    source = legacy_sources().get(product.get('id'))
    if authored or not source or any(product.get(k) for k in ('generated', 'creator_username', 'ghostlab_generated', 'artifact_id')):
        return product
    result = dict(product)
    result['presentation_i18n'] = {}
    result['search_aliases'] = []
    levels = [dict(level, _system_i18n={}) if isinstance(level, dict) else level for level in product.get('levels', [])]
    version = manifest()['content_version']
    for path, original in source.items():
        value = product
        try:
            for part in path.split('.'):
                value = value[int(part)] if isinstance(value, list) else value[part]
        except (KeyError, IndexError, TypeError, ValueError):
            continue
        if value != original:
            continue  # An edited field belongs to its author, even on a seed ID.
        key = f"catalog.system.{product['id']}.{path}"
        entry = {'key': key, 'params': {}, 'content_version': version}
        if path.startswith('levels.'):
            _, index, field = path.split('.', 2)
            levels[int(index)]['_system_i18n'][field] = entry
        else:
            result['presentation_i18n'][path] = entry
            result['search_aliases'].extend(translator().t(key, locale=locale) for locale in approved_locales('interface'))
    result['presentation_owner'] = 'system'
    result['levels'] = levels
    return result


def installed_presentation(product, builtins):
    """Read-time presentation for old installations without an inventory rewrite."""
    result = legacy_presentation(product)
    source = builtins.get(product.get('id'))
    if (not source or any(product.get(k) for k in ('generated', 'ghostlab_generated', 'artifact_id'))
            or product.get('creator_username') != source.get('creator_username')):
        return result
    # The code-owned catalog reserves these IDs, but author-edited fields remain literal.
    result.pop('presentation_i18n', None)
    fields = {field: dict(entry) for field, entry in source.get('presentation_i18n', {}).items()
              if product.get(field) == source.get(field)}
    if fields:
        result['presentation_owner'] = 'system'
        result['presentation_i18n'] = fields
    return result
