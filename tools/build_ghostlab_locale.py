"""Build presentation-only keys from the code-owned template registry."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ghostlab_registry import TEMPLATES

DESCRIPTIONS = {
    'financial_sniffer': 'A single financial operation using active player access.',
    'friend_kicker': 'Attempts to sever one randomly selected contact of the victim.',
    'security_panel_proxy': 'Remote controls for the target security settings.',
    'system_log_reader': 'Read the latest system messages of the target safely.',
    'arsenal_cleaner': 'Attempts to remove a random application from the victim arsenal.',
    'intruder_kicker': 'Remove an intruder from your territory using active PvP access. One family use per access.',
    'travel_ticket': 'One trip to the author destination, performed immediately on purchase.',
    'file_cleanup': 'Remove selected unnecessary, unsellable files from your own system.',
    'system_update': 'An update presentation with author logs; system parameters remain unchanged.',
    'security_restore': 'Apply a system security preset to your own account once.',
    'firmware_update': 'One purchased flash attempt. Success permanently increases disk capacity and scan range; failure requires a restart. Both outcomes trigger a 24-hour cooldown.',
    'deep_scanner': 'An overlay for the default Scan action. Works only while its window is open; one application can be active.',
    'ptk_document': 'Author-created Markdown material to read in File Manager.',
}
FIELDS = {
    'allowed_switches': ('Dozwolone przełączniki', 'Allowed switches'),
    'button_color': ('Kolor przycisku', 'Button color'), 'camera': ('Pozostałości skanów kamer', 'Camera scan remnants'),
    'city': ('Miejscowość', 'City'), 'conflict_matrix': ('Macierz konfliktów', 'Conflict matrix'),
    'contact_message': ('Komunikat kontaktu', 'Contact message'), 'content': ('Treść', 'Content'),
    'cooldown_minutes': ('Odstęp użyć (min)', 'Cooldown (min)'), 'country': ('Kraj', 'Country'),
    'detection_percent': ('Szansa wykrycia (%)', 'Detection chance (%)'), 'disk_mb': ('Przyrost dysku (MB)', 'Disk increase (MB)'),
    'extra_retries': ('Dodatkowe ponowienia', 'Additional retries'), 'extra_timeout': ('Dodatkowy czas oczekiwania', 'Additional timeout'),
    'failure_message': ('Komunikat niepowodzenia', 'Failure message'), 'frame_color': ('Kolor ramki', 'Frame color'),
    'frame_id': ('Ramka', 'Frame'), 'include_created_at': ('Uwzględnij datę utworzenia', 'Include creation date'),
    'include_status': ('Uwzględnij status', 'Include status'), 'include_type': ('Uwzględnij typ', 'Include type'),
    'installers': ('Niepotrzebne instalatory', 'Unneeded installers'), 'lat': ('Szerokość geograficzna (lat)', 'Latitude (lat)'),
    'lng': ('Długość geograficzna (lng)', 'Longitude (lng)'), 'log_limit': ('Limit logów', 'Log limit'),
    'menu_name': ('Nazwa w menu', 'Menu name'), 'objects': ('Pozostałości skanów obiektów', 'Object scan remnants'),
    'pattern_id': ('Wzór', 'Pattern'), 'place_name': ('Nazwa miejsca', 'Place name'),
    'preset': ('Domyślne zabezpieczenia (gracz może zmienić)', 'Default security preset (player can change)'),
    'presets': ('Zestawy zabezpieczeń', 'Security presets'), 'protected_apps': ('Chronione aplikacje', 'Protected applications'),
    'recon': ('Zakończony Recon', 'Completed Recon'), 'redaction_policy': ('Polityka ukrywania danych', 'Redaction policy'),
    'remove_tools_file': ('Usuń plik narzędzia', 'Remove tool file'), 'reward_note': ('Notatka nagrody', 'Reward note'),
    'rules': ('Reguły', 'Rules'), 'scan_m': ('Przyrost zasięgu skanu (m)', 'Scan range increase (m)'),
    'sfx_id': ('Efekt dźwiękowy', 'Sound effect'), 'steal_percent': ('Przechwytywana część (%)', 'Intercepted share (%)'),
    'success_message': ('Komunikat powodzenia', 'Success message'), 'success_percent': ('Szansa powodzenia (%)', 'Success chance (%)'),
    'system': ('Zbędne artefakty systemowe', 'Unneeded system artifacts'), 'target_policy': ('Polityka celu', 'Target policy'),
    'usage_policy': ('Polityka użycia', 'Usage policy'), 'victim_message': ('Komunikat ofiary', 'Victim message'),
    'visibility': ('Widoczność publikacji', 'Publication visibility'),
}
for index in range(1, 5):
    FIELDS[f'log_{index}'] = (f'Komunikat etapu {index}', f'Step {index} message')
for state, pl, en in [('denied', 'odmowy', 'denial'), ('empty', 'braku wyników', 'empty result'),
                      ('error', 'błędu', 'error'), ('start', 'rozpoczęcia', 'start'), ('success', 'powodzenia', 'success')]:
    FIELDS[state + '_text'] = (f'Tekst {pl}', f'{en.capitalize()} text')
    FIELDS[state + '_log'] = (f'Log {pl}', f'{en.capitalize()} log')

def main():
    assert set(DESCRIPTIONS) == set(TEMPLATES), 'Review new template descriptions'
    assert set(FIELDS) == {key for template in TEMPLATES.values() for key in template['fields']}, 'Review new template fields'
    manifest_path = ROOT / 'static/locales/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for index, locale in enumerate(('pl', 'en')):
        path = ROOT / f'static/locales/{locale}/lab.json'
        data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(locale=locale, format_version=1, content_version=manifest['content_version'], messages={})
        messages = data['messages']
        for key, template in TEMPLATES.items():
            messages[f'lab.template.{key}.name'] = dict(params={}, text=('PTK Document' if key == 'ptk_document' and locale == 'en' else template['name']))
            messages[f'lab.template.{key}.description'] = dict(params={}, text=template['description'] if locale == 'pl' else DESCRIPTIONS[key])
        for key, pair in FIELDS.items():
            messages[f'lab.field.{key}'] = dict(params={}, text=pair[index])
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if 'lab' not in manifest['domains']:
        manifest['domains'].append('lab')
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'{len(TEMPLATES)} templates, {len(FIELDS)} fields reviewed; author defaults unchanged')

if __name__ == '__main__':
    main()
