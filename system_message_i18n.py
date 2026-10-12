"""Versioned system copy; never translate arbitrary player-authored messages."""
import re

# Exact historical templates, scoped by the authoritative producer. A nickname,
# product name or user body is never searched for translation keywords.
TEMPLATES = (
    ('cyberner_system', 'Gest przywitania',
     r'👋 (?P<actor>.+) wysyla Ci gest przywitania\. Odpowiedz, zeby dodac go do znajomych\.', 'mail_greeting'),
    ('cyberner_system', 'Wpłata za aplikację',
     r'(?P<buyer>.+) kupił aplikację (?P<name>.+) za (?P<price>[\d.]+) HackCoinów\.', 'mail_app_sale'),
    ('cyberner_system', 'Sprzedano paczke danych',
     r'Sektor: (?P<sector>[^\n]+)\nLiczba plikow: (?P<count>\d+)\nWolumen: (?P<volume>[^\n]+) MB\nCena: (?P<price>[\d.]+) HC\nBatch: (?P<batch>[^\n]+)\nCzas: (?P<time>[^\n]+)', 'mail_batch_sale'),
    ('cyberner_system', 'Sprzedano pakiet danych',
     r'Pakiet danych: (?P<name>[^\n]+)\nKategoria rynku: (?P<category>[^\n]+)\nCena: (?P<price>[\d.]+) HC\nKupujacy: (?P<buyer>[^\n]+)\nCzas: (?P<time>[^\n]+)\nStatus pliku: sold / removed from data inventory', 'mail_data_sale'),
    ('cyberner_system', 'Atak na punkt kolizyjny',
     r'(?P<actor>[^\n]+) \((?P<username>[^\n]+)\) atakuje twoj obiekt (?P<target>[^\n]+)\.\nAkcja: (?P<action>[^\n]+)\nPozycja: (?P<position>[^\n]+)', 'mail_point_attack'),
    ('cyberner_system', 'Utrata punktu terytorium',
     r'Obiekt (?P<target>[^\n]+) zostal przejety przez (?P<actor>[^\n]+) \((?P<username>[^\n]+)\)\.\nPozycja: (?P<position>[^\n]+)', 'mail_territory_lost'),
    ('cyberner_system', 'Podatnosc zostala zhakowana',
     r'Twoja zgloszona podatnosc zostala zhakowana\.\n\nCel: (?P<target>[^\n]+)\nTyp: (?P<type>[^\n]+)\nPozycja: (?P<position>[^\n]+)\nAtakujacy: (?P<actor>[^\n]+) \((?P<username>[^\n]+)\)\nKlan atakujacego: (?P<clan>[^\n]+)\nCzas: (?P<time>[^\n]+)\nID zgloszenia: (?P<report>[^\n]+)', 'mail_vulnerability_hacked'),
    ('territory_progression', 'Respect za terytorium',
     r'Twoja sieć powiększyła się o (?P<area>[-\d.]+) m² efektywnej kontroli\. \+(?P<respect>\d+) respect\.', 'territory_reward'),
    ('territory_progression', 'Awans poziomu',
     r'Rozszerzyłeś terytorium o kolejne 10%\. Nowy level: (?P<level>\d+)\.', 'level_reward'),
    ('response_network', 'Areszt',
     r'Areszt: (?P<minutes>\d+) min online\. Wiezienie: (?P<prison>.+)\. Kaucja: (?P<bail>[\d.]+) HC\.', 'detention'),
    ('response_network', 'Zwolnienie z aresztu',
     r'Kaucja oplacona\. Powrot do pozycji sprzed aresztu\.', 'release_bail'),
    ('response_network', 'Zwolnienie z aresztu',
     r'Wyrok odbyty\. Powrot do pozycji sprzed aresztu\.', 'release_served'),
    ('response_network', 'Konsekwencje incydentu',
     r'Mandat: (?P<amount>[\d.]+) HC\. Skonfiskowano narzędzia: (?P<names>.+)\.', 'fine_confiscation'),
    ('response_network', 'Konsekwencje incydentu',
     r'Mandat: (?P<amount>[\d.]+) HC\.', 'fine'),
    ('response_network', 'Konsekwencje incydentu',
     r'Skonfiskowano narzędzia: (?P<names>.+)\.', 'confiscation'),
    ('ghostlab.firmware', 'Aktualizacja firmware',
     r'Firmware zainstalowany — trwałe bonusy zapisane\.', 'firmware_success'),
    ('ghostlab.firmware', 'Aktualizacja firmware',
     r'Flashowanie nieudane\. Crash systemu — wymagany restart\.', 'firmware_failed'),
    ('', 'Dokument PTK', r'Pobrano dokument do Pliki → Plexcak\.', 'document_downloaded'),
    ('financial_sniffer', 'Podejrzany ruch finansowy',
     r'Wykryto próbę sniffingu finansowego na twoim koncie\.', 'financial_warning'),
    ('area_intrusion', 'Obcy gracz na twoim terenie',
     r'(?P<actor>.+) wszedł na kontrolowany przez Ciebie obszar\.', 'area_intrusion'),
    ('domain_event', 'Response Network: ostrzezenie',
     r'Response Network wykryl aktywnosc przy (?P<target>.+)\. Poziom ryzyka: (?P<heat>.+)\. Sluzby sa w drodze\. ETA: (?P<eta>.+)\. Tryb visible_safe: brak kar, brak przerwania operacji\.', 'response_warning'),
    ('domain_event', 'Proba hackowania podatnosci',
     r'(?P<actor>.+) uruchomil akcje (?P<action>.+) na zgloszeniu (?P<target>.+)\.', 'vulnerability_attempt'),
    ('domain_event', 'Alarm: atak na roj podatnosci',
     r'(?P<actor>.+) \((?P<username>.+)\) naruszyl roj obronny na celu (?P<target>.+)\. Wrogi atak nie przejmuje pozostalych punktow roju\.', 'swarm_attack'),
    ('googleplex_install', 'Instalacja zakończona',
     r'Aplikacja <b>(?P<name>.*)</b> została poprawnie zainstalowana!', 'install'),
    ('googleplex_product', 'Zakup Googleplex',
     r'Produkt <b>(?P<name>.*)</b> zostal aktywowany\.', 'product'),
    ('financial_sniffer', 'Podejrzany ruch finansowy',
     r'Wykryto probe sniffingu finansowego na twoim koncie\.', 'financial_warning'),
    ('arsenal_cleaner', 'Arsenał naruszony', r'Usunięto jedną aplikację\.', 'arsenal_removed'),
    ('arsenal_cleaner', 'Arsenał naruszony', r'Wykryto próbę czyszczenia arsenału\.', 'arsenal_attempt'),
    ('arsenal_cleaner', 'Arsenal naruszony',
     r'Jedno z narzedzi zostalo usuniete przez nieznana ingerencje\.', 'arsenal_removed'),
    ('arsenal_cleaner', 'Wykryto probe czyszczenia arsenalu',
     r'Wykryto probe czyszczenia arsenalu\.', 'arsenal_attempt'),
    ('friend_kicker', 'Kontakt utracony',
     r'Polaczenie z jednym z graczy zostalo zerwane\.', 'contact_lost'),
    ('friend_kicker', 'Zaklocenie kontaktow',
     r'Jeden z kontaktow zostal zerwany przez nieznana ingerencje\.', 'contact_removed'),
    ('friend_kicker', 'Wykryto probe manipulacji kontaktami',
     r'Wykryto probe manipulacji kontaktami\.', 'contact_attempt'),
    ('domain_event', 'Pole zostało otoczone',
     r'Jedno z Twoich pól zostało pochłonięte przez większy obszar innego gracza\. Jesteś bardziej widoczny i podatny na atak\.', 'area_encircled'),
    ('domain_event', 'Atak na punkt kolizyjny',
     r'(?P<actor>.+) uruchomil akcje (?P<action>.+) na twoim obiekcie (?P<target>.+)\.', 'point_attacked'),
    ('domain_event', 'Podatnosc przejeta',
     r'(?P<actor>.+) przejal cel (?P<target>.+) z twojego zgloszenia\.', 'vulnerability_captured'),
    ('domain_event', 'Utrata punktu terytorium',
     r'(?P<actor>.+) przejal twoj obiekt (?P<target>.+)\. Terytorium jest przebudowywane\.', 'territory_lost'),
    ('ghostnetwork_restart', 'Restart GhostSystemu wymagany',
     r'Transmisja GhostSignal z wersji (?P<from_version>.+) do (?P<to_version>.+) została zakończona\. Uruchom ponownie GhostSystem; do tego czasu akcje GhostNetwork są zablokowane\.', 'restart_versions'),
    ('ghostnetwork_restart', 'Restart GhostSystemu wymagany',
     r'Transmisja GhostSignal została zakończona\. Uruchom ponownie GhostSystem; do tego czasu akcje GhostNetwork są zablokowane\.', 'restart'),
)
RISK_COPY = {
    'suspicious_network_activity': 'Podejrzana aktywnosc sieciowa zostawila slad w systemie.',
    'long_operation_detected': 'Dluga operacja zwiekszyla widocznosc Twojej aktywnosci.',
    'atm_alarm': 'Terminal finansowy wykryl nietypowa probe odczytu danych.',
    'camera_detected': 'System obserwacji zarejestrowal anomalie przy kamerze.',
    'sniffer_detected': 'Implant/sniffer zostawil sygnature w monitoringu celu.',
    'abandoned_operation': 'Porzucona operacja zostawila slaby slad w systemie.',
}
for title, scope in (('Info: roj podatnosci na terytorium', 'allied'), ('Alarm: obcy roj podatnosci', 'hostile')):
    TEMPLATES += (
        ('domain_event', title, r'(?P<actor>.+) wystawil (?P<count>\d+) punktow podatnosci na podstawie jednego skanu\.', 'swarm_' + scope + '_many'),
        ('domain_event', title, r'(?P<actor>.+) wystawil podatnosc celu (?P<target>.+) na twoim terytorium\.', 'swarm_' + scope + '_one'),
    )
TEMPLATES += tuple(('cyberner_system', title, pattern, key)
                   for source, title, pattern, key in TEMPLATES if source == 'domain_event')
TEMPLATES += tuple((source, 'Risk event', re.escape(code + ': ' + text), 'risk_' + code)
                   for source in ('', 'domain_event') for code, text in RISK_COPY.items())
TEMPLATES += tuple((source, 'Risk event', re.escape('camera_detected: ' + RISK_COPY['camera_detected']
                    + ' Modifier: protected_by_camera_shutdown'), 'risk_camera_protected')
                   for source in ('', 'domain_event'))
for authority, key in (('Policja','police'), ('Centrum cyberbezpieczeństwa','cyber_center'),
                       ('Prokuratura cyberbezpieczeństwa','cyber_prosecutor')):
    TEMPLATES += (
        ('response_network', authority, re.escape(authority) + r': dozór zakończony\. Historia wyroków pozostaje w kartotece\.', 'record_' + key + '_clear'),
        ('response_network', authority, re.escape(authority) + r': dozór zredukowany do poziomu (?P<level>\d+)\.', 'record_' + key + '_reduced'),
    )
# SystemMessageStore canonicalizes an omitted source to "system". Keep the
# empty-source form for legacy profile projection and its canonical store form.
TEMPLATES += tuple(('system', title, pattern, key)
                   for source, title, pattern, key in TEMPLATES if source == '')
COMPILED_TEMPLATES = tuple((source, title, re.compile(pattern, re.DOTALL), key)
                           for source, title, pattern, key in TEMPLATES)


def project_system_copy(message, source):
    result = dict(message)
    # The source comes from the authoritative store column, not a client field.
    result.pop('system_copy', None)
    if source == 'cyberner' and message.get('notification_type') == 'cyberner':
        labels = {'world':'WORLD', 'friends':'ZNAJOMI', 'clan':'KLAN',
                  'system':'System', 'mission':'Misje'}
        channel = message.get('source')
        title_key = (f'apps.notifications.cyberner_{channel}_title'
                     if channel in labels and message.get('title') == labels[channel] else '')
        # Only new producer records explicitly distinguish an empty preview
        # from player text which happens to say "Nowa wiadomosc.".
        empty = message.get('system_preview') is True
        text_key = ('apps.notifications.cyberner_world_text' if channel == 'world'
                    else 'apps.notifications.cyberner_system_text') if empty else 'apps.notifications.cyberner_preview_text'
        result['system_copy'] = dict(schema_version=1, title_key=title_key, text_key=text_key,
            params={} if empty else {'preview':str(message.get('text') or '')})
        return result
    for expected_source, title, pattern, key in COMPILED_TEMPLATES:
        if source != expected_source or message.get('title') != title:
            continue
        match = pattern.fullmatch(str(message.get('text') or message.get('body') or ''))
        if match:
            result['system_copy'] = {
                'schema_version': 1,
                'title_key': f'apps.notifications.{key}_title',
                'text_key': f'apps.notifications.{key}_text',
                'params': match.groupdict(),
            }
            break
    return result
