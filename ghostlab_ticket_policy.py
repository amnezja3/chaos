"""Shared ticket pricing and public projection; coordinates stay server-side."""

TICKET_MAX_PRICE = 150


def is_ticket(app):
    return app.get('template_id') == 'travel_ticket' or app.get('product_type') == 'travel_ticket'


def ticket_price(app, artifact=None):
    if app.get('template_id') == 'travel_ticket':
        artifact = artifact or (app.get('metadata') or {}).get('artifact') or {}
        suggested = (artifact.get('branding_snapshot') or {}).get('suggested_price')
        value = (100 if suggested is None else suggested) if artifact else app.get('price', 100)
    else:
        value = app.get('price', 100)
    return min(TICKET_MAX_PRICE, max(5, int(value)))


def public_ticket(app):
    # Allowlist instead of recursively publishing metadata/artifacts/blueprints.
    fields = ('id', 'name', 'icon', 'description', 'system_description', 'type', 'category',
        'product_type', 'consumable', 'price', 'price_hint', 'creator_username', 'creator_nick',
        'required_level', 'required_respect', 'allowed_fractions', 'published', 'generated',
        'ghostlab_generated', 'system_catalog', 'template_id', 'template_name', 'artifact_id',
        'source_build_version', 'runtime_status', 'purchase_confirmation', 'installed', 'can_afford',
        'install_blocked_reason', 'destination_revision', 'travel_city', 'downloads')
    result = {key: app[key] for key in fields if key in app}
    result['price'] = min(TICKET_MAX_PRICE, max(5, int(app.get('price', 100))))
    result['price_hint'] = result['price']
    destination = app.get('destination') or {}
    result['destination'] = {key: destination[key] for key in ('place_name','city','country') if key in destination}
    return result
