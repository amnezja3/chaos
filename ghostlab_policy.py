"""Validation and preview from the code-owned GhostLab registry."""
from ghostlab_registry import default_blueprint, get_template, validate_fields


def default_ghostlab_blueprint(template_id):
    return default_blueprint(template_id)


def validate_ghostlab_blueprint(template_id, blueprint):
    errors = validate_fields(template_id, blueprint)
    definition = get_template(template_id)
    preview = []
    if not errors:
        if definition:
            preview = [definition['name'], ('Dokument autora: pobranie do File Managera i odczyt zakupionej wersji.'
                       if definition['launch_mode'] == 'document' else 'Jedna podróż od razu przy zakupie. Miejsce deklarowane przez autora.'
                       if definition['launch_mode'] == 'purchase_travel' else
                       'Własny system / uruchomienie z pulpitu' if definition['launch_mode'] == 'own_system' else
                       'Player Hack Access / wymagany zgodny build i aktywacja serwerowa')]
            preview.extend(f'{key}: {value}' for key, value in blueprint.items()
                           if definition['fields'][key]['editable'])
        else:
            preview = ['custom draft bez kompilatora']
    return {'valid': not errors, 'errors': errors, 'warnings': [], 'preview': preview}
