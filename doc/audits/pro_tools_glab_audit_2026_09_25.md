# Audyt pro-toolsów i przypisania GLab — 25 IX 2026

Zakres: statyczny audyt lokalnego kodu, nie odczyt katalogu produkcyjnego ani
potwierdzenie wykonania wszystkich narzędzi na serwerze.
W `run.py:PRO_SYSTEM_TOOLS` jest 11 wbudowanych produktów. Produkty graczy
również mogą mieć type=pro-system-tool; sam typ nie oznacza systemowego rodzica.

## Inwentaryzacja i proponowane przypisanie

| ID | Logika / uruchomienie | Przypisanie na ten etap |
|---|---|---|
| systemLogReader | odczyt komunikatów systemowych przez Player Hack Access | GLab → system_log_reader; runtime 145 |
| financialSniffer | transfer HC podczas dostępu PvP | GLab → financial_sniffer; runtime 146 |
| friendKicker | próba usunięcia kontaktu i relacji | GLab → friend_kicker; runtime 146 |
| securityPanelProxy | odczyt i aktualizacja dozwolonych zabezpieczeń celu | GLab → security_panel_proxy; runtime 146 |
| arsenalCleaner | próba usunięcia narzędzia z inventory ofiary | GLab → arsenal_cleaner; runtime 146 |
| intruderKicker | wypchnięcie intruza z własnego terytorium, raz na dostęp | GLab — decyzja użytkownika; przygotować nowy kontrakt intruder_kicker |
| victimPicker | selektor istniejących celów mapy | nie-GLab; systemowy interfejs wyboru celu |
| territoryControl | zarządzanie terytorium, filarami i zabezpieczeniami | nie-GLab; konsola zarządzająca |
| operationControl | operacje, pliki, incydenty, anulowanie | nie-GLab; konsola zarządzająca |
| ghostnetworkSuite | publiczna projekcja i nawigacja GhostNetwork | nie-GLab; konsola systemowa |
| agi2108Console | ograniczone zlecenia narracyjne właściciela | nie-GLab; osobny kontrakt LLM ingress |

To proponowana klasyfikacja do wdrożenia, nie już istniejące flagi ani trwały
zakaz przyszłego udostępnienia pozostałych narzędzi.
GhostLab ma type=system_lab; cztery kreatory type=creator. Nie zaliczamy ich
do tych 11 produktów. Bilet, cleaner własnych plików, rozszerzenie dysku i nowe
skanery nie są dodatkowymi pozycjami w tym rejestrze; ich przyszłe kontrakty
mogą istnieć samodzielnie, bez pro-toolsa źródłowego.

## Ustalenia i dowody

1. `run.py:PRO_SYSTEM_TOOLS` zawiera opis, cenę, wymagania i launcher, ale brak
   jawnej klasyfikacji GLab/nie-GLab oraz powiązania do wersjonowanego kontraktu.
2. Pięć kontraktów jest rozproszonych między `ghostlab_policy.py`
   (`default_ghostlab_blueprint`, `validate_ghostlab_blueprint`), listą dopuszczeń
   w `ghostlab_routes.py` i opisami/formularzami w `static/js/terminal.js`.
3. `run.py:api_player_hack_tool_use` rozpoznaje wbudowane tool_id. Odczyt logów
   korzysta z system_message_store, finanse z walletu, Friend Kicker z contacts,
   Arsenal Cleaner z player_inventory_store; to źródła do ponownego użycia.
   Nie należy kierować potomka na wykonawcę tylko przez podmianę tool_id:
   trzeba sprawdzić instalację potomka, jego artefakt, kontrakt i uprawnienia.
4. Parametry blueprintu nie są dowodem podłączenia do wykonania: np. limity
   SystemLogReader i procenty innych szablonów muszą zostać jawnie odwzorowane
   w 145–146. Brak pozornego sukcesu ani domyślnego włączenia wszystkich rodzin.
5. `ghostlab_store.py` zachowuje template_id w projekcie i downloads przy
   ponownej publikacji. To podstawa relacji, ale potrzebna jest projekcja admina
   łącząca szablon, produkt i autora; nie relacja oparta na nazwie.
6. `admin_panel.py` zawiera projekcje kont, nie listę szablonów i potomstwa.
   Trzeba dodać osobny, stronicowany odczyt; autor z małej projekcji tożsamości.
7. Arsenal Cleaner jest atakiem na inventory ofiary. Nie zastępuje planowanej
   funkcji porządkowania własnych zbędnych plików. AGI templates w llm_ingress
   też nie są automatycznie szablonami GhostLaba.

## Granice audytu

Pogłębienie 25 IX: potwierdzono ciężki odczyt i zapis profilu w
api_player_hack_security_update oraz api_player_hack_security_preset
(load_profile_write_record, patch_profile_guarded). Wcześniejszy odczyt panelu
z projekcji nie oznaczał zgodności ścieżki mutacji. Brak canonical writera security
w przejrzanym IdentityProjectionStore: get_player_security jest odczytem projekcji.
To otwarta wada i obowiązkowa naprawa w 144.3 przed PASS, nie wykonana poprawka.
Drugi problem: update/preset sprawdzają literalne securityPanelProxy,
a okna wyników (np. openIntruderKickerApp) mają branding rodzica.

Dodatkowe ustalenie: `run.py:serialize_player_hack_access` sprawdza instalację
tylko ID z PLAYER_HACK_TOOL_IDS, a `static/js/terminal.js` renderuje access.tools
także dla installed=false. Panel obecnie nie jest listą zainstalowanego potomstwa.
Przebudowa listy wpisana do 144.3, podłączenie wykonania do 145–146.

Nie wykonano pełnego pomiaru SQL wszystkich launcherów, zakupów i skutków.
Użycie projekcji w przejrzanych gałęziach nie daje całościowego certyfikatu
zero-heavy. Testy całej ścieżki i naprawa każdego znalezionego naruszenia są
bramką implementacji; nie wolno zastępować brakującego store pełnym profilem.
Przed wdrożeniem należy porównać lokalny rejestr z katalogiem serwera, oddzielając
wbudowane produkty, potomstwo graczy i legacy bez pewnego pochodzenia.

Realizacja: [144.3 — aktualizacja pro-toolsów](../sprints/sprint_144_3_pro_tools_glab_alignment.md).
