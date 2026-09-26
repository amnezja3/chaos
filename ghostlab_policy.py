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
            preview = [definition['name'], 'Player Hack Access / wymagany zgodny build i aktywacja serwerowa']
            preview.extend(f'{key}: {value}' for key, value in blueprint.items()
                           if definition['fields'][key]['editable'])
        else:
            preview = ['custom draft bez kompilatora']
    return {'valid': not errors, 'errors': errors, 'warnings': [], 'preview': preview}
