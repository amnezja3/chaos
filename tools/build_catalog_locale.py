"""Build reviewed presentation catalogs for code-owned products, without importing run."""
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EN = {
    'intruderKicker': 'Push a hacked intruder outside your territory. One use per PvP access.',
    'financialSniffer': 'A single attempt at a small financial siphon during an active player hack.',
    'friendKicker': 'Attempt to remove a random contact from the victim during an active player hack.',
    'systemLogReader': 'Read the victim’s latest system messages during an active player hack.',
    'arsenalCleaner': 'Attempt to remove a random application from the victim’s arsenal during an active hack.',
    'securityPanelProxy': 'Remotely configure the victim’s profile security during an active hack.',
    'victimPicker': 'Select targets from existing map sources: marked POIs, players, vulnerabilities and conflicts.',
    'territoryControl': 'Manage your clusters, pillars and captured object security without opening the full map.',
    'operationControl': 'Monitor active operations, generated files and Response Network incidents. Cancel individual operations or groups.',
    'ghostnetworkSuite': 'View public, blocked, active and player-controlled GhostNetwork parts.',
    'agi2108Console': 'Submit private AGI 2108 narrative requests using an approved template.',
    'buttonmaker': 'Build button_choices applications and publish them in Googleplex.',
    'termcreator': 'Build terminal applications and publish them in Googleplex.',
    'windowmaker': 'Build window applications and publish them in Googleplex.',
    'appforge': 'Build and publish progressbar_random applications with AppForge.',
    'ghost_lab': 'Design, validate, compile and publish tools using GhostLab system contracts.',
    'storage_ghost_vault_basic': 'A basic data storage expansion.',
    'storage_ghost_vault_plus': 'More storage for longer operations and market packages.',
    'storage_data_vault': 'Data storage for active Ghost Exchange traders.',
    'storage_blackvault': 'High-capacity storage for large sector packages.',
    'storage_encrypted_cluster': 'The largest built-in storage upgrade for advanced data trading.',
    'ticket_warszawa': 'Return to the starting city.',
    'ticket_krakow': 'A single trip to Krakow.',
    'ticket_berlin': 'A single trip to Berlin.',
    'ticket_londyn': 'A single trip to London.',
    'ticket_tokio': 'A single trip to Tokyo.',
    'ticket_nowy_jork': 'A single trip to New York.',
    'map_zoom_plus_1': 'Improved zoom for the operational map.',
    'map_zoom_plus_2': 'Advanced zoom for the operational map.',
    'map_zoom_plus_3': 'The highest built-in map zoom upgrade.',
    'scan_range_100': 'A small increase in reconnaissance range.',
    'scan_range_300': 'A moderate increase in reconnaissance range.',
    'scan_range_500': 'A large increase in reconnaissance range.',
    'scan_range_1000': 'An advanced increase in reconnaissance range.',
    'bike_range_100': 'A small increase in bike range.',
    'bike_range_300': 'A moderate increase in bike range.',
    'bike_range_500': 'A large increase in bike range.',
    'bike_range_1000': 'An advanced increase in bike range.',
}


def source_products():
    result = {}
    for node in ast.parse((ROOT / 'run.py').read_text(encoding='utf8')).body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List):
            continue
        names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        if not names.intersection({'PRO_SYSTEM_TOOLS', 'CREATOR_SYSTEM_APPS', 'STORAGE_UPGRADE_PRODUCTS', 'GOOGLEPLEX_EFFECT_PRODUCTS'}):
            continue
        for item in node.value.elts:
            if isinstance(item, ast.Dict):
                value = ast.literal_eval(item)
            elif isinstance(item, ast.Call):
                product_id, name, description = map(ast.literal_eval, item.args[:3])
                value = {'id': product_id, 'name': name, 'description': description}
            else:
                continue
            result[value['id']] = value
    return result


def main():
    products = source_products()
    if products.keys() != EN.keys():
        raise ValueError(f'Unreviewed products: {products.keys() ^ EN.keys()}')
    manifest_file = ROOT / 'static/locales/manifest.json'
    manifest = json.loads(manifest_file.read_text(encoding='utf8'))
    if 'catalog' not in manifest['domains']:
        manifest['domains'].append('catalog')
    manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    for locale in ('pl', 'en'):
        messages = {}
        for product_id, product in products.items():
            name = product['name']
            if locale == 'en' and product_id.startswith('ticket_'):
                name = {'ticket_warszawa':'Ticket: Warsaw', 'ticket_krakow':'Ticket: Krakow', 'ticket_berlin':'Ticket: Berlin',
                        'ticket_londyn':'Ticket: London', 'ticket_tokio':'Ticket: Tokyo', 'ticket_nowy_jork':'Ticket: New York'}[product_id]
            for field, text in [('name', name), ('description', product['description'] if locale == 'pl' else EN[product_id])]:
                messages[f'catalog.system.{product_id}.{field}'] = {'params': {}, 'text': text}
        payload = {'locale': locale, 'format_version': 1, 'content_version': manifest['content_version'], 'messages': messages}
        (ROOT / f'static/locales/{locale}/catalog.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
    print(f'{len(products)} reviewed system products')
    from build_legacy_catalog_locale import main as legacy_catalog
    legacy_catalog()


if __name__ == '__main__':
    main()
