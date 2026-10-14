"""System label descriptors, distinct from the one original narrative publication."""
from ghost_i18n import translator


def descriptors(fact, rule, value):
    metadata = fact.get('metadata') or {}
    category = str(fact.get('category') or '')
    values = {**metadata, 'value': value, 'category': category,
              'target_label': metadata.get('target_label') or category,
              'product_name': metadata.get('product_name') or category,
              'public_state': metadata.get('public_state') or metadata.get('status') or '',
              'trend': metadata.get('trend') or ''}
    fields = dict(channel=rule.get('channel', ''), label=rule.get('label', ''),
                  stat=rule.get('stat_template', ''), title=rule.get('title_template') or rule.get('title', ''))
    result = {}
    catalog = translator().catalogs['pl']['messages']
    for field, text in fields.items():
        key = 'apps.blacknet.rule.' + fact['fact_type'] + '.' + field
        spec = catalog[key]['params']
        result[field] = {'key': key, 'params': {
            name: int(values.get(name) or 0) if kind == 'number' else str(values.get(name, 0))
            for name, kind in spec.items()}}
    return result


def render(copy, locale):
    catalog = translator()
    return {field: catalog.t(item['key'], item['params'], locale=locale)
            for field, item in copy.items()}
