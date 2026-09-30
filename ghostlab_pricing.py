"""Explicit free pricing applies only to GhostLab templates without a parent tool."""
from ghostlab_registry import get_template


def independent_price(app):
    definition = get_template(app.get('template_id'))
    if not app.get('ghostlab_generated') or not definition or definition.get('source_tool_id'):
        return None
    artifact = (app.get('metadata') or {}).get('artifact') or {}
    suggested = (artifact.get('branding_snapshot') or {}).get('suggested_price')
    if app.get('glab_price_policy') == 1 and type(suggested) is int and suggested == 0:
        return 0
    if app.get('template_id') == 'ptk_document':
        return min(100, max(1, 25 if suggested is None else suggested))
    return None


def apply_price(app):
    price = independent_price(app)
    if price is None:
        return False
    app.update(price=price, price_hint=price, open_source=price == 0)
    return True
