"""Author-owned presentation; no gameplay privileges or profile reads."""
from ghostlab_registry import get_template

MAX_DESCRIPTION = 1000
MAX_SAFE_PRICE = 9007199254740991  # Exact integer in the browser, not an economic price cap.


def project_branding(project):
    definition = get_template(project.get('template_id')) or {}
    return {
        'name': project.get('name') or 'Untitled',
        'icon': project.get('icon') or definition.get('icon') or '🧪',
        'description': project.get('description', definition.get('description', '')),
        'suggested_price': project.get('suggested_price'),
        'presentation_id': project.get('presentation_id') or 'default',
    }


def validate_branding(value, template_id, icon_validator):
    if not isinstance(value, dict) or set(value) != {
        'name', 'icon', 'description', 'suggested_price', 'presentation_id'
    }:
        raise ValueError('Nieprawidlowe pola marki produktu.')
    name, description = value['name'], value['description']
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 64:
        raise ValueError('Nazwa musi miec od 1 do 64 znakow.')
    if not isinstance(description, str) or len(description) > MAX_DESCRIPTION:
        raise ValueError('Opis moze miec maksymalnie 1000 znakow.')
    if not isinstance(value['icon'], str):
        raise ValueError('Ikona musi byc jednym widocznym znakiem.')
    icon = icon_validator(value['icon'])
    price = value['suggested_price']
    if price is not None and (type(price) is not int or not 0 <= price <= MAX_SAFE_PRICE):
        raise ValueError('Sugerowana cena musi byc nieujemna calkowita liczba HC.')
    definition = get_template(template_id) or {}
    if value['presentation_id'] not in definition.get('presentation_ids', ['default']):
        raise ValueError('Prezentacja nie jest dozwolona dla tego szablonu.')
    return dict(value, name=name.strip(), description=description.strip(), icon=icon)
