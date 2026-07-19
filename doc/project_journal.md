# CHAOS — Project Journal

Project Journal jest kroniką rozwoju projektu CHAOS.

To nie jest changelog i nie jest dokumentacją techniczną. Jego rolą jest szybkie przekazanie historii projektu: skąd wzięły się obecne decyzje, dlaczego powstały kolejne systemy i w jakim stanie jest roadmapa.

CHAOS:

```text
Cyber Hacking Adventure Of Senses
Hack the digital senses of the modern world.
Hakuj cyfrowe zmysły współczesnego świata.
```

---

## Zasady prowadzenia dziennika

Po zakończeniu każdego sprintu implementacyjnego należy dopisać jeden wpis.

Każdy wpis sprintowy ma zawierać:

* Data
* Sprint
* Cel
* Co zostało wykonane
* Najważniejsze decyzje
* Problemy
* Zmienione pliki
* Wynik testów
* Status
* Następny sprint

Journal nie powiela dokumentacji kontraktowej i nie opisuje implementacji linia po linii. Ma zachować historię projektu w formie czytelnej dla nowego czatu, nowego członka zespołu albo przyszłego powrotu do projektu po przerwie.

---

## 20.06.2026

### Etap

Player actors i menu gracza na mapie.

### Cel

Ujednolicić sposób, w jaki mapa widzi innych graczy: znajomych, intruzów, członków klanu, graczy wrogich i neutralnych.

### Najważniejsze decyzje

* Wprowadzono kierunek `player_actors` jako wspólnej warstwy danych dla avatarów graczy na mapie.
* Backend ma rozstrzygać relację gracza względem obserwatora i zwracać gotowe `actions`.
* Frontend nie powinien sam zgadywać, czy wolno dodać znajomego, rozpocząć rozmowę, przelać HC albo oznaczyć cel.
* Self/motocykl został świadomie wyłączony z pierwszej wersji `player_actors`, żeby nie mieszać go z mechaniką ruchu kursora i kierunków.

### Efekt

Powstał fundament pod menu gracza na mapie. Projekt przeszedł od osobnych ścieżek renderowania znajomych i intruzów do modelu jednego payloadu `player_actor`.

### Status

Zamknięte jako etap architektoniczny.

---

## 21.06.2026

### Etap

Social flow, Wallet HC i player target.

### Cel

Podłączyć pierwsze realne akcje z menu gracza na mapie.

### Najważniejsze decyzje

* Dodawanie znajomych ma wykorzystywać istniejący mail/contact flow, a nie tworzyć drugi system kontaktów.
* Wallet HC ma być osobną aplikacją desktopową, nie modalem mapy.
* Oznaczenie gracza jako celu ma używać `target_mode: "player"`.
* Player target ma korzystać z tej samej ścieżki hackowania co zwykłe targety, ale bez mieszania post-hack panelu z menu mapy.

### Efekt

Menu gracza zaczęło prowadzić do realnych systemów: kontaktów, rozmowy, portfela i targetowania gracza. Powstał fundament pod osobną gałąź hackowania profilu gracza.

### Status

Zamknięte jako etap integracji player actions.

---

## 22.06.2026

### Etap

Pro-system-tools i Player Hack Access.

### Cel

Zbudować pierwsze narzędzia działające po udanym hacku gracza.

### Najważniejsze decyzje

* Pro-system-tools to osobne aplikacje/narzędzia, a nie zakładki jednego kombajnu.
* Dostęp po hacku gracza jest czasowy i ograniczony.
* Każde narzędzie powinno mieć własne okno albo własny panel wynikowy.
* `systemLogReader`, `securityPanelProxy`, `financialSniffer`, `friendKicker` i `arsenalCleaner` rozwijano jako osobne realne narzędzia.

### Efekt

Powstał model czasowego dostępu do shackowanego gracza oraz pierwsze realne narzędzia ingerujące w logi systemowe, zabezpieczenia, HC, kontakty i arsenał aplikacji.

### Status

Zamknięte jako etap player hack tools.

---

## 23.06.2026

### Etap

Googleplex, Creator Economy i GhostLab.

### Cel

Przenieść narzędzia i creatory do ekonomii aplikacji oraz rozpocząć budowę GhostLaba jako laboratorium narzędzi systemowych.

### Najważniejsze decyzje

* Pro-system-tools mają być pełnoprawnymi aplikacjami Googleplex.
* Creatory nie są już darmowym wyposażeniem startowym, tylko warsztatem kupowanym przez gracza.
* GhostLab ma być osobnym hubem/laboratorium, a nie rozszerzeniem AppForge.
* Workflow GhostLaba ma przypominać IDE: templates → projects → editor → compiler → publisher.

### Efekt

Googleplex stał się centralnym sklepem aplikacji. GhostLab dostał ścieżkę rozwoju od workspace przez project manager, templates, editor, build system, publisher, Ghost Exchange i research foundation.

### Status

Zamknięte jako etap ekonomii narzędzi i IDE.

---

## 26.06.2026

### Etap

Narodziny nowego modelu gameplayu.

### Cel

Odejść od prostego hackowania obiektów jako serii kliknięć i przejść do pełnej pętli gameplayu opartej o aktywne operacje i ekonomię danych.

### Najważniejsze decyzje

* Proste hackowanie celu przestało być wystarczającym modelem rozgrywki.
* Powstał kierunek:

```text
World Object
↓
Map Action
↓
Application
↓
Operation
↓
Resource
↓
Economy
```

* Nazwa CHAOS została domknięta jako:

```text
Cyber Hacking Adventure Of Senses
```

* Hasło projektu zostało ustalone jako:

```text
Hack the digital senses of the modern world.
```

* Operacja stała się centralnym bytem gameplayu: aplikacja nie jest efektem końcowym, tylko narzędziem tworzącym operację.
* Aktywne operacje mają żyć na mapie bez kosztownego realtime loopa.

### Efekt

Projekt dostał nową tożsamość i nowy rdzeń gameplayu: hakowanie cyfrowych zmysłów świata, a nie tylko pojedynczych komputerów. Od tego momentu dalsze sprinty zaczęły wymagać kontraktów, a nie improwizowania systemów bez wspólnej osi.

### Status

Zamknięte jako punkt zwrotny projektu.

---

## Sprint 0

### Etap

Fundament kontraktów gameplayu.

### Cel

Zatrzymać rozrastanie się mechanik bokiem i stworzyć wspólny kontrakt dla świata, mapy, aplikacji, operacji, zasobów, plików, ekonomii oraz ryzyka.

### Najważniejsze decyzje

* Źródłami prawdy stały się dokumenty Sprintu 0.
* `app.interface` mówi tylko, jak aplikacja się otwiera.
* `app.map_actions` jest docelowym routerem uruchamiania aplikacji z mapy.
* `detects`, `type` i `interferes_with` mogą być tylko fallbackiem migracyjnym.
* `operation_type` opisuje żyjący proces, a nie kliknięcie z mapy.
* `resource_type`, `file_category` i `market_category` są oddzielnymi pojęciami.
* Nie każdy resource jest plikiem i nie każdy plik jest towarem.
* Ghost Exchange jest rynkiem danych.
* Ryzyko jest liczone jako pipeline zdarzeń, a nie losowanie co sekundę.

### Efekt

Powstał kompletny zestaw dokumentów projektowych, który pozwala implementować gameplay bez zgadywania nazw pól i bez tworzenia drugiego routera aplikacji, drugiego modelu operacji, drugiego rynku albo drugiego systemu plików.

Najważniejsze źródła prawdy:

* `doc/gameplay_terms.md`
* `doc/source_type_mapping.md`
* `doc/world_objects.md`
* `doc/map_actions.md`
* `doc/app_contract.md`
* `doc/operations.md`
* `doc/movement_model.md`
* `doc/resource_types.md`
* `doc/file_model.md`
* `doc/data_economy.md`
* `doc/risk_events.md`
* `doc/gameplay_loop.md`
* `doc/sprint0_summary.md`

### Status

Sprint 0 zamknięty. Projekt gotowy do implementacji Sprintu 1.

27.06.2026

Projekt odnaleziony.

Hackers Odyssey Cybernetic Challenge (2023)

Analiza wykazała, że obecny CHAOS nie jest nowym projektem.

Jest ewolucją wcześniejszej koncepcji.

Najważniejsze elementy zachowane:

- browser
- mail
- aplikacje
- ekonomia
- player vs player
- system operacyjny
- narzędzia

Największa zmiana:

Przejście z modelu "funkcji gry" do modelu:

World → Action → Application → Operation → Resource → Economy

---

## 27.06.2026

### Etap

Sprint 1 — Map Action Router + App Contract Runtime.

### Cel

Wprowadzić nowy router akcji mapy oparty o `app.map_actions`.

### Najważniejsze decyzje

* Sprint 1 zaczyna implementację gameplayu po zamkniętym Sprincie 0.
* Główna ścieżka ma iść po `app.map_actions`.
* Stary fallback po `detects`, `type` i `interferes_with` może zostać tylko jako `TODO_MIGRATION`.
* Brak aplikacji ma dawać jasny komunikat, a nie cichy sukces.
* Pełny wybór wielu narzędzi zostaje na Sprint 2.

### Efekt

Router `app.map_actions` został wdrożony jako główna ścieżka runtime dla akcji mapy. Stary fallback po `detects/type/interferes_with` pozostał jako `TODO_MIGRATION`.

### Status

Zamknięty.

---

## Format wpisów od Sprintu 2

Od Sprintu 2 każdy wpis powinien mieć format:

```text
## Data

### Sprint

Cel

Co zostało wykonane

Najważniejsze decyzje

Problemy

Zmienione pliki

Wynik testów

Status

Następny sprint
```

Project Journal jest od teraz obowiązkowym dokumentem przekazania projektu.

---

## 27.06.2026

### Sprint

Sprint 2 — Tool Selection UX.

### Cel

Gracz ma świadomie wybierać narzędzie z własnego arsenału, jeśli dana akcja mapy jest obsługiwana przez więcej niż jedną aplikację.

### Co zostało wykonane

* `/hack-action` rozróżnia pojedynczą aplikację i wiele pasujących aplikacji.
* Przy jednej aplikacji zachowano automatyczne uruchomienie przez istniejący `launch_queue`.
* Przy wielu aplikacjach backend nie uruchamia ich automatycznie, tylko zwraca `tool_selection_required`.
* Frontend mapy przekazuje payload wyboru narzędzia do desktopu.
* File Manager otwiera katalog `/tools`, pokazuje kontekst akcji mapy i podświetla pasujące narzędzia.
* Kliknięcie `Użyj` przy pasującym narzędziu ponownie wywołuje `/hack-action` z `selected_app_id`.
* Wybrana aplikacja wraca do istniejącego flow `launch_queue` i `/command`.

### Najważniejsze decyzje

* Nie tworzono osobnego modala wyboru narzędzia. Wybór odbywa się w istniejącym File Managerze, zgodnie z kontraktem Sprintu 0.
* Zwykłe kliknięcie pliku w `/tools` nadal działa jak dotychczasowa symulacja. Akcję mapy uruchamia dopiero przycisk `Użyj` przy podświetlonym narzędziu.
* Aliasów terminalowych jeszcze nie implementowano. Architektura jest przygotowana przez `selected_app_id` i istniejący `/command`.

### Problemy

* Istniejące aplikacje nadal używają częściowo danych migracyjnych z `detects/type/interferes_with`. Docelowo trzeba uzupełniać fizyczne `app.map_actions` w katalogu aplikacji.
* `launch_queue` jest nadal odbierany przez istniejący polling, więc po wyborze narzędzia aplikacja może wystartować z krótkim opóźnieniem.

### Zmienione pliki

* `run.py`
* `templates/map_template.html`
* `static/js/terminal.js`
* `static/css/style.css`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 9 testów

### Status

Sprint 2 zamknięty.

### Następny sprint

Sprint 3 — Operation Core.

---

## 27.06.2026

### Sprint

Sprint 3 — Operation Core.

### Cel

Aplikacja przestaje być końcem akcji mapy. Po skutecznym użyciu aplikacji system tworzy instancję operacji zgodną z kontraktem Sprintu 0.

### Co zostało wykonane

* Dodano runtime `operation_types` do kontraktu aplikacji.
* Stare rekordy aplikacji mogą dostać migracyjne `operation_types` wyprowadzone z `map_actions`.
* `/hack-action` po udanym użyciu narzędzia tworzy operacje w `profile.operations`, jeśli aplikacja deklaruje `operation_types`.
* Operacja zapisuje `operation_id`, `operation_type`, właściciela, aplikację źródłową, `map_action_id`, snapshot celu, `target_type`, `target_mode`, status, czas startu, czas wygaśnięcia, `resource_buffer` i `risk_state`.
* Dodano lekki endpoint `GET /api/operations` do odczytu operacji i aktywnych operacji.
* Utrzymano dotychczasowy `launch_queue` i zachowanie starszych aplikacji bez `operation_types`.

### Najważniejsze decyzje

* Nowe operacje startują w statusie `running`. Status `start` pozostaje w kontrakcie, ale bez schedulera byłby stanem chwilowym bez praktycznej wartości.
* Sprint 3 zapisuje tylko instancję operacji. Ruch, aktywne markery mapy, ticki, pliki i ekonomia pozostają na kolejne sprinty.
* `resource_buffer` przechowuje deklarowane `resource_types`, ale nie generuje jeszcze plików.
* `risk_state` jest zerowym szkieletem pod Sprint ryzyka, bez losowania i konsekwencji.

### Problemy

* Część aplikacji nadal wymaga migracyjnego inferowania z `detects/type/interferes_with`, dopóki katalog aplikacji nie dostanie pełnych `map_actions` i `operation_types`.
* Testy Pythona dotykają śledzonych plików `__pycache__`, które nie są częścią zmian gameplayowych.

### Zmienione pliki

* `run.py`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 11 testów

### Status

Sprint 3 zamknięty.

### Następny sprint

Sprint 4 — Active Operations Read Model / aktywny świat na mapie.

---

## 27.06.2026

### Sprint

Sprint 4 — Active Operations Panel + Active Map Objects.

### Cel

Gracz ma widzieć, że operacje utworzone po użyciu aplikacji nie są jednorazowym efektem, tylko żyją dalej jako aktywny stan świata.

### Co zostało wykonane

* Mapa pobiera aktywne operacje z `GET /api/operations`.
* Dodano lekki panel `Aktywne operacje` pokazujący typ operacji, cel, status, start, koniec i pozostały czas.
* Dodano prostą warstwę markerów aktywnych operacji na mapie.
* `camera_stream`, `camera_shutdown`, `vehicle_tracking` i `persistent_sniffer` mają osobne oznaczenia wizualne.
* Po udanym `hackingAction()` mapa odświeża aktywne operacje.
* Przy wejściu na mapę i w timerze odświeżania aktywne operacje są odtwarzane z `profile.operations`.

### Najważniejsze decyzje

* Sprint 4 jest tylko read mode. Nie dodano movement engine, checkpointów, generowania plików ani rynku.
* Pozycja markera aktywnej operacji pochodzi ze snapshotu targetu zapisanego w operacji.
* Timer jest liczony po stronie frontendu z `expires_at`, a backend pozostaje źródłem prawdy dla listy operacji.
* Warstwa aktywnych operacji jest czyszczona i rysowana ponownie przy refreshu, żeby nie nakładać markerów.

### Problemy

* Status `timeout` nie jest jeszcze automatycznie zapisywany przez scheduler. W Sprincie 4 timer wizualnie dobiega do zera, ale pełne odświeżanie statusów należy do kolejnych sprintów.
* Markery trackingowe są statyczne. Ruch pojazdów, telefonów i graczy zaczyna się dopiero w Sprincie 5.
* Embedded JS w `map_template.html` nie ma osobnego checkera składni jak `terminal.js`.

### Zmienione pliki

* `templates/map_template.html`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 11 testów

### Status

Sprint 4 zamknięty.

### Następny sprint

Sprint 5 — Movement Refresh Engine.

---

## 27.06.2026

### Sprint

Sprint 5 — Movement Refresh Engine.

### Cel

Aktywne operacje zaczynają odświeżać swój stan bez realtime loopa. Backend wylicza stan przy odczycie na podstawie timestampów, typu operacji, typu celu, modelu ruchu i seeda proceduralnego.

### Co zostało wykonane

* Dodano runtime refresh operacji po stronie backendu.
* Nowe operacje dostają `duration_seconds`, `movement_model` i `procedural_seed`.
* `GET /api/operations` zwraca operacje z `remaining_seconds`, `expired`, `movement_model` i `current_position`.
* Operacje `start/running`, którym minął `expires_at`, są zapisywane jako `timeout`.
* `vehicle_tracking` i `vehicle_ecu` używają prostego `road_movement`.
* `device_tracking` i `generic_trace` używają lokalnego ruchu w małym promieniu.
* `camera_stream`, `camera_shutdown` i `persistent_sniffer` pozostają timerami bez ruchu.
* Mapa używa `operation.current_position`, jeśli backend ją zwróci.

### Najważniejsze decyzje

* Nie ma backendowej pętli świata. Stan jest liczony przy odczycie `/api/operations`.
* Nie zapisujemy każdej pozycji ruchu. Zapisywany jest tylko realny stan gameplayowy, czyli przejście operacji w `timeout`.
* Ruch pojazdu jest na tym etapie uproszczonym wektorem proceduralnym, nie jazdą po realnych drogach.
* Ruch telefonu/osoby jest lokalnym przesunięciem wokół punktu startowego.

### Problemy

* Ruch jest jeszcze modelem wizualnym/read-model, bez checkpointów i bez generowania historii GPS.
* `player_position` jest przygotowany w modelu, ale nie podłączono jeszcze osobnych zasad śledzenia graczy.
* Embedded JS mapy nadal nie ma osobnego parsera składni poza testem ręcznym w przeglądarce.

### Zmienione pliki

* `run.py`
* `templates/map_template.html`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 13 testów

### Status

Sprint 5 zamknięty.

### Następny sprint

Sprint 6 — Vehicle Tracking + GPS Logs.

---

## 27.06.2026

### Sprint

Sprint 6 — Vehicle Tracking + GPS Logs.

### Cel

Domknąć pierwszą pełną ścieżkę operacji mobilnej: `vehicle -> trace_gps -> vehicle_tracking -> gps_logs/location_history -> plik w /data/gps`.

### Co zostało wykonane

* `vehicle_tracking` generuje gameplayowe checkpointy ruchu przy refreshu operacji.
* Checkpointy są zapisywane jako eventy co 15 minut logicznego czasu operacji, bez zapisu każdej klatki ruchu.
* Po `timeout` albo `completed` operacji `vehicle_tracking` powstaje plik GPS.
* Plik trafia do `files.gps` jako reprezentacja katalogu `/data/gps`.
* Plik zawiera `file_category: gps`, `preview_mode: table`, `gps_logs`, `location_history`, metadane operacji i listę checkpointów.
* Dodano minimalny podgląd pliku GPS w File Managerze.
* Dodano ochronę przed wielokrotnym tworzeniem tego samego pliku przy kolejnych refreshach.

### Najważniejsze decyzje

* Sprint 6 nie dodaje rynku, maili, pricingu ani HC.
* `files.gps` jest kompatybilnym katalogiem runtime dla `/data/gps`, bez budowania pełnego drzewa katalogów.
* Plik GPS jest oznaczony jako `market_status: not_listed` i `sellable: false` na czas Sprintu 6, mimo że kontrakt docelowo dopuszcza sprzedaż danych.
* Jakość i dokładność pliku są placeholderami, bo realny model jakości będzie zależał od aplikacji i kolejnych sprintów.

### Problemy

* Checkpointy są proceduralne i uproszczone. Nie ma jeszcze jazdy po realnych drogach.
* File Manager ma minimalny podgląd tabeli GPS, ale nie ma jeszcze pełnego systemu `/data/*`.
* Nie ma jeszcze sprzedaży danych ani notyfikacji mailowej po sprzedaży.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/user_template.json`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 14 testów

### Status

Sprint 6 zamknięty.

### Następny sprint

Sprint 7 — Device Tracking + Device Intelligence.

---

## 27.06.2026

### Sprint

Sprint 7 — Device Tracking + Device Intelligence.

### Cel

Telefon, osoba i gracz stają się źródłem pakietów Device Intelligence. `device_tracking` po zakończeniu tworzy plik z paczką danych, której kompletność zależy od aplikacji.

### Co zostało wykonane

* `device_tracking` po `timeout/completed` tworzy pakiet Device Intelligence.
* Basic aplikacja bez jawnych `resource_types` tworzy mały pakiet: `location_history` i `device_logs`.
* Lepsza aplikacja może utworzyć bogatszą paczkę z `personal_records`, `financial_records`, `call_history` i `messenger_data`.
* Pakiet trafia do `files.device` albo `files.personal`, reprezentując `/data/device` i `/data/personal`.
* Dodano model kompletności paczki: liczba zasobów, procent, tier `basic/enhanced/rich`, brakujące zasoby.
* File Manager pokazuje katalogi `device` i `personal` oraz prosty preview karty kompletności.
* Dodano ochronę przed duplikowaniem pliku przy kolejnych refreshach.

### Najważniejsze decyzje

* Sprint 7 nie dodaje rynku, maili, pricingu ani HC.
* `files.device` i `files.personal` są kompatybilnymi katalogami runtime dla `/data/device` i `/data/personal`.
* O tym, jak bogaty jest pakiet, decydują `resource_types` aplikacji zapisane w operacji.
* Basic fallback jest celowo mały, żeby gracz odczuł różnicę między aplikacjami.

### Problemy

* Kompletność nie wpływa jeszcze na cenę, bo rynek zacznie działać w późniejszych sprintach.
* Preview pokazuje strukturę pakietu, ale nie ma jeszcze pełnego eksploratora danych.
* Player target korzysta z tego samego mechanizmu danych, ale dodatkowe zasady PvP pozostają na późniejsze sprinty.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/user_template.json`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 16 testów

### Status

Sprint 7 zamknięty.

### Następny sprint

Sprint 8 — Camera Stream + Camera Shutdown.

---

## 27.06.2026

### Sprint

Sprint 8 — Camera Stream + Camera Shutdown.

### Cel

Kamery zaczynają działać jak oczy świata: stream jest aktywną operacją z timerem, tworzy małe fragmenty materiału, a shutdown zostawia czasowy stan kamery bez budowania AI Vision ani rynku.

### Co zostało wykonane

* `camera_stream` tworzy fragmenty co 5 minut logicznego czasu operacji.
* Fragmenty trafiają do `files.camera`, czyli runtime odpowiednika `/data/camera`.
* Fragmenty mają `preview_mode: media_placeholder`, metadane operacji, czas fragmentu i listę `resource_types`.
* Domyślny stream tworzy `camera_dump`.
* Aplikacja deklarująca `video_material` tworzy fragmenty zawierające `camera_dump` i `video_material`.
* Dodano ochronę przed duplikowaniem fragmentów przy kolejnych refreshach.
* File Manager pokazuje katalog `camera` oraz prosty placeholder podglądu materiału.
* `camera_shutdown` zapisuje w operacji `support_state` z czasowym stanem kamery: `offline` / `recovering`.
* `support_state` zawiera pole `risk_modifier`, przygotowane pod późniejszy Sprint 15.

### Najważniejsze decyzje

* Fragment streamu ma 5 minut logicznego czasu. To daje naturalne małe paczki zamiast jednego dużego pliku.
* `camera_dump` jest domyślnym zasobem streamu.
* `video_material` powstaje tylko wtedy, gdy aplikacja deklaruje ten resource.
* `camera_shutdown` nie produkuje plików. Zostawia tylko stan operacji, który może później zmniejszać ryzyko.
* Nie dodano AI Vision, wykrywania obiektów, rynku, maili ani sprzedaży.

### Problemy

* Podgląd kamery jest tylko placeholderem, bez realnego wideo.
* Stan `risk_modifier` jest przygotowany, ale nie wpływa jeszcze na kalkulację ryzyka.
* Fragmenty powstają przy refreshu operacji, więc nie ma niezależnego background workera.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/user_template.json`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 19 testów

### Status

Sprint 8 zamknięty.

### Następny sprint

Sprint 9 — ATM Log Extraction.

---

## 28.06.2026

### Sprint

Sprint 9 — ATM Log Extraction.

### Cel

ATM zaczyna produkować pierwsze wartościowe paczki finansowe wysokiego ryzyka: `atm_log_extraction` po zakończeniu tworzy dump bankomatu, a bogatsza aplikacja może dołożyć rekordy finansowe.

### Co zostało wykonane

* Dodano risk hint dla operacji `atm_log_extraction`: `level: high`, `atm_alarm`, bez konsekwencji i bez pełnego Risk MVP.
* Po `timeout/completed` operacja tworzy plik `atm_dump` w `files.atm`.
* Jeżeli aplikacja deklaruje `financial_records`, powstaje dodatkowy plik w `files.financial`.
* Pliki ATM/financial mają `preview_mode: table`, metadane operacji i syntetyczne rekordy do podglądu.
* Dodano ochronę przed duplikowaniem plików przy kolejnych refreshach.
* File Manager pokazuje katalogi `atm` i `financial`.
* Dodano aplikację katalogową `ATMLogReader` z `map_actions: ["atm_logs"]` i `operation_types: ["atm_log_extraction"]`.

### Najważniejsze decyzje

* Basic ATM reader produkuje tylko `atm_dump`.
* `financial_records` są traktowane jako bogatszy wynik aplikacji, nie domyślny efekt każdego odczytu ATM.
* Pliki są jeszcze niesprzedawalne (`sellable: false`, `market_status: not_listed`), bo Ghost Exchange i pricing są poza Sprintem 9.
* Risk hint jest informacyjny i nie uruchamia konsekwencji.

### Problemy

* Rekordy ATM są syntetycznym placeholderem gameplayowym.
* Nie ma jeszcze sprzedaży, maili, HC ani automatycznego skupu.
* Nie ma jeszcze pełnego scoringu ryzyka ani konsekwencji alarmu ATM.

### Zmienione pliki

* `run.py`
* `static/app_config.json`
* `static/js/terminal.js`
* `static/user_template.json`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 22 testy
* `node -e "JSON.parse(... static/app_config.json ...)"` — OK

### Status

Sprint 9 zamknięty.

### Następny sprint

Sprint 10 — Persistent Sniffer.

---

## 28.06.2026

### Sprint

Sprint 10 — Persistent Sniffer.

### Cel

Gracz może zainstalować aktywny implant na ATM/router/server i po czasie odebrać dane z operacji `persistent_sniffer`.

### Co zostało wykonane

* `install_sniffer` tworzy operację `persistent_sniffer` z modelem `implant_timer`.
* `persistent_sniffer` dostaje risk hint: `long_operation_detected`, `sniffer_detected`, bez konsekwencji i bez pełnego Risk MVP.
* Po `timeout/completed` operacja tworzy pliki zależnie od `resource_types` aplikacji.
* `credentials` trafiają do `files.credentials` jako `encrypted_blob`.
* `financial_records` trafiają do `files.financial` jako tabela.
* `device_logs` trafiają opcjonalnie do `files.device`.
* `internal_recon_state` trafia opcjonalnie do `files.system` jako `operation_state`.
* File Manager pokazuje katalogi `credentials` i `system`.
* Preview `encrypted_blob` nie pokazuje plain-textu, tylko zaszyfrowany placeholder i metadane.
* Dodano ochronę przed duplikowaniem plików przy kolejnych refreshach.
* Dodano aplikację katalogową `PersistentSniffer` z `map_actions: ["install_sniffer"]` i `operation_types: ["persistent_sniffer"]`.

### Najważniejsze decyzje

* Domyślnym wynikiem basic implantu są `credentials`.
* Bogatsze dane (`financial_records`, `device_logs`, `internal_recon_state`) powstają tylko, jeśli aplikacja je deklaruje.
* Credentials nigdy nie są pokazywane jako plain-text w File Managerze.
* Pliki pozostają niesprzedawalne (`sellable: false`, `market_status: not_listed`) do sprintów rynku.
* Risk hint jest informacyjny i nie uruchamia konsekwencji.

### Problemy

* Dane implantu są jeszcze placeholderami gameplayowymi.
* Nie ma cleanupu implantu, maili, HC, sprzedaży ani automatycznego skupu.
* Nie ma jeszcze pełnego scoringu ryzyka ani konsekwencji wykrycia sniffera.

### Zmienione pliki

* `run.py`
* `static/app_config.json`
* `static/js/terminal.js`
* `static/user_template.json`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` — OK
* `python -m py_compile run.py database.py profileManagment.py poiFetchClass.py Haversine.py terminals\commands.py` — OK
* `python -m unittest tests.test_target_persistence` — OK, 25 testów
* `node -e "JSON.parse(... static/app_config.json ...)"` — OK

### Status

Sprint 10 zamknięty.

### Następny sprint

Sprint 11 — Microphone Sniffer + Audio Transcript.
---

## 28.06.2026

### Sprint

Sprint 11 — File Inventory v1.

### Cel

File Manager przestaje być tylko listą katalogów i staje się gameplay inventory danych gracza. Pliki runtime dostają wspólny format, a katalogi danych są widoczne nawet wtedy, gdy są jeszcze puste.

### Co zostało wykonane

* Dodano wspólny zestaw katalogów gameplay inventory: `tools`, `gps`, `device`, `audio`, `camera`, `atm`, `credentials`, `financial`, `personal`, `network`, `vehicle`, `system`, `market`, `projects`.
* Backend normalizuje katalogi danych przez `ensure_files_inventory()` / `normalize_files_inventory()`.
* Pliki runtime dostają podstawowy kontrakt: `id`, `file_category`, `resource_types`, `preview_mode`, `created_at`, `source_operation_id`, `target_snapshot`, `metadata`, `sellable`, `market_status`.
* Zachowano kompatybilność `tools` i `projects`, żeby nie złamać uruchamiania aplikacji, Googleplexa i projektów creatorów.
* `/api/profile` i `/api/operations` zwracają profil z uporządkowanym inventory.
* File Manager pokazuje kategorię, tryb preview, resource types, operation id i market status na liście plików.
* Szablon nowego użytkownika dostał brakujące katalogi: `audio`, `network`, `vehicle`, `market`.
* Dodano test regresyjny normalizacji inventory.

### Najważniejsze decyzje

* `tools` i `projects` pozostają kompatybilne ze starszym formatem stringów, bo są katalogami aplikacji/projektów, a nie paczek danych.
* Normalizacja obejmuje katalogi danych, nie wymusza przebudowy całego File Managera.
* `source_operation_id` jest nowym polem kontraktu, ale `operation_id` zostaje jako kompatybilny alias dla starszych preview i testów.
* `market_status` pozostaje `not_listed`, a `sellable` domyślnie `false`, bo Sprint 11 nie uruchamia jeszcze rynku.

### Problemy

* File Manager nadal ma część starszych napisów z mojibake w istniejącym UI, ale Sprint 11 nie obejmował porządkowania kodowania całego frontendu.
* `audio`, `network`, `vehicle` i `market` są przygotowane jako katalogi, ale nie mają jeszcze pełnych generatorów danych.
* Preview jest nadal lekkie i kompatybilne, a nie docelowy eksplorator danych.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/user_template.json`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testów

* `python -m py_compile run.py database.py profileManagment.py` — OK
* `node --check static/js/terminal.js` — OK
* `python -m unittest tests.test_target_persistence` — OK, 26 testów

### Status

Sprint 11 zamknięty.

### Następny sprint

Sprint 12 — Microphone Sniffer + Audio Transcript.

---

## 28.06.2026

### Sprint

Sprint 12 — Ghost Exchange MVP.

### Cel

Browser dostaje Ghost Exchange jako miejsce przygotowania sprzedawalnych plików danych do przyszłej sprzedaży. Sprint nie wykonuje jeszcze finalnej transakcji, nie wysyła maili i nie przelewa HC.

### Co zostało wykonane

* Dodano backendowe API `GET /api/ghost-exchange`, które zwraca sprzedawalne pliki z inventory gracza.
* Dodano backendowe API `POST /api/ghost-exchange/preview`, które oznacza plik statusem `listed_preview`.
* Ghost Exchange filtruje tylko katalogi danych: `gps`, `device`, `personal`, `camera`, `atm`, `financial`, `credentials`, `network`, `vehicle`, `audio`.
* Pliki typu `tools`, `projects`, `market`, `system` oraz zasoby `internal_recon_state` nie trafiają do listy sprzedaży.
* Dodano deterministyczny price preview oparty o kategorię rynku, resource types, wolumen/metadane i kompletność.
* Browser dostał zakładki `Googleplex` i `Ghost Exchange`.
* Karty Ghost Exchange pokazują nazwę pliku, kategorię pliku, resource types, market category, preview ceny i status.
* Przycisk `Preview sale` przełącza ofertę w stan `listed_preview` bez usuwania pliku i bez transferu HC.

### Najważniejsze decyzje

* Ghost Exchange jest częścią Browsera, obok Googleplexa, zgodnie z kontraktem Data Economy.
* Sprint 12 nie mutuje ekonomii gracza poza statusem preview oferty.
* Pliki kwalifikujące się do rynku pokazują w Ghost Exchange status `ready_to_list`, nawet jeśli surowy stan inventory to jeszcze `not_listed`.
* Finalna sprzedaż, mail i transfer HC zostają w Sprincie 13.

### Problemy

* Price preview jest celowo prosty i deterministyczny, bez pełnej ekonomii popytu.
* Nie ma jeszcze historii rynku ani katalogu `/market/sold`.
* Część starszego UI Browsera/File Managera nadal ma stare napisy z mojibake, ale nie była częścią zakresu sprintu.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `doc/project_journal.md`

### Wynik testów

* `python -m py_compile run.py database.py profileManagment.py` — OK
* `node --check static/js/terminal.js` — OK
* `python -m unittest tests.test_target_persistence` — OK, 26 testów

### Status

Sprint 12 zamknięty.

### Następny sprint

Sprint 13 — Ghost Exchange Sale Flow.
---

## 28.06.2026

### Sprint

Sprint 13 — Sale Flow + Mail + HC.

### Cel

Domknąć pierwszą pełną pętlę ekonomii danych: plik danych z Ghost Exchange może zostać sprzedany, gracz dostaje HackCoiny i mail systemowy, a plik znika z katalogu danych.

### Co zostało wykonane

* Dodano finalny endpoint `POST /api/ghost-exchange/sell`.
* Sprzedaż używa istniejącego `price_preview` jako ceny finalnej Sprintu 13.
* Po sprzedaży plik jest usuwany z katalogu danych (`gps`, `camera`, `atm`, `credentials` itd.).
* Dodano rekord sprzedaży do historii rynku: `files.market` oraz trwałe `profile.market_history`.
* Sprzedaż zwiększa `profile.hackcoins`.
* Ghost Exchange wysyła mail systemowy z nazwą paczki, kategorią rynku, ceną, typem kupującego, timestampem i statusem pliku.
* Druga próba sprzedaży tego samego pliku jest blokowana.
* Browser dostał przycisk `Sprzedaj` obok istniejącego `Preview sale`.
* Smoke helper `tools/smoke_admin_inventory.py` dostał tryb `--sell`, który sprawdza sprzedaż, duplikat, HC, mail i historię.

### Najważniejsze decyzje

* Plik widoczny w Ghost Exchange jako `ready_to_list` może zostać sprzedany bez obowiązkowego wcześniejszego kliknięcia Preview.
* `Preview sale` zostaje etapem przygotowania oferty, ale nie jest twardym warunkiem sprzedaży.
* Historia sprzedaży jest utrwalana w `profile.market_history`, bo to stabilniejsze źródło niż sam runtime katalog `/market`.
* `files.market` zostaje jako katalog runtime dla rekordów sprzedaży i przyszłego UI historii.
* Kupujący jest systemowy i deterministycznie opisany przez `market_category`; player-to-player trading zostaje poza zakresem.

### Problemy

* `files.market` w obecnej architekturze inventory jest mniej pewne jako jedyne źródło historii, dlatego dodano równoległe `profile.market_history`.
* Cena finalna jest nadal prostym wynikiem `price_preview`, bez dynamicznego popytu i bez pełnego pricingu.
* Mail trafia do istniejącego komunikatora jako wiadomość od `Ghost Exchange`; osobny widok historii rynku może powstać później.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/user_template.json`
* `tools/smoke_admin_inventory.py`
* `doc/project_journal.md`

### Wynik testów

* `python -m py_compile run.py database.py profileManagment.py tools\smoke_admin_inventory.py` — OK
* `node --check static/js/terminal.js` — OK
* `python -m unittest tests.test_target_persistence` — OK, 26 testów
* `python tools\smoke_admin_inventory.py --sell` — OK:
  * sprzedaż `200`,
  * duplikat `404`,
  * HC wzrosły,
  * liczba plików danych spadła,
  * powstał rekord w `profile.market_history`,
  * pojawił się mail `Sprzedano pakiet danych`.

### Status

Sprint 13 zamknięty.

### Następny sprint

Sprint 14 — Pricing v1 / Data Value Tuning.
---

## 28.06.2026

### Sprint

Sprint 14 - Risk MVP.

### Cel

Dodac pierwszy koszt ryzyka do operacji i agresywnych akcji mapy, bez realtime loopa i bez ciezkich kar.

### Co zostalo wykonane

* Dodano runtime store `profile.risk_events`.
* Dodano podstawowy risk pipeline: risk signal -> score -> event -> lekkie consequences.
* `scan_ports` moze zapisac `suspicious_network_activity` jako event akcji mapy.
* Operacje po `completed` albo `timeout` sa oceniane pod katem ryzyka podczas kontrolowanego refreshu `/api/operations`.
* Obsluzono eventy MVP: `suspicious_network_activity`, `long_operation_detected`, `atm_alarm`, `camera_detected`, `sniffer_detected`.
* Konsekwencje Sprintu 14 sa lekkie: `warning`, `partial_detection`, `cooldown_placeholder`.
* Event ryzyka tworzy tez `system_message`, zeby gracz dostal ostrzezenie w istniejacym kanale komunikacji.
* Smoke helper admina raportuje teraz ostatnie risk eventy.

### Najwazniejsze decyzje

* Ryzyko nie jest losowane co sekunde. Jest liczone przy akcji mapy albo przy finalizacji/timeout operacji.
* `scan_ports` nie tworzy operacji ani loot, ale zostawia risk signal.
* ATM ma minimalny wysoki score przez `atm_alarm`.
* Sniffer generuje `long_operation_detected` i `sniffer_detected`.
* `cooldown_placeholder` jest tylko zapisem konsekwencji, bez realnej blokady gameplayowej w tym sprincie.

### Problemy

* UI nie ma jeszcze osobnego panelu Risk. Feedback idzie przez `system_messages` i profil.
* Balans liczbowy jest MVP i bedzie wymagal strojenia po kilku sprintach testow.
* Support operations nie zmniejszaja jeszcze ryzyka; to zakres Sprintu 15.

### Zmienione pliki

* `run.py`
* `static/user_template.json`
* `tools/smoke_admin_inventory.py`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py tools\smoke_admin_inventory.py` - OK
* `node --check static/js/terminal.js` - OK
* `python -m unittest tests.test_target_persistence` - OK, 26 testow
* `python tools\smoke_admin_inventory.py` - OK:
  * `scan_ports` wykonuje sie i moze zapisac risk event,
  * `atm_log_extraction` zapisuje `atm_alarm`,
  * `persistent_sniffer` zapisuje `long_operation_detected` oraz `sniffer_detected`,
  * eventy sa widoczne w profilu admina.

### Status

Sprint 14 zamkniety.

### Nastepny sprint

Sprint 15 - Support Operations / risk reducers.

---

## 28.06.2026

### Sprint

Sprint 15 - Support Operations + Risk Reducers.

### Cel

Wprowadzic pierwsze operacje wspierajace, ktore zmniejszaja ryzyko glownych dzialan, bez ciezkich kar i bez pelnego balansu.

### Co zostalo wykonane

* Dodano risk modifiers do pipeline'u ryzyka.
* `camera_shutdown` redukuje `camera_detected` dla pasujacej operacji na tym samym target albo w poblizu.
* Event ryzyka zapisuje `base_risk_score`, `risk_score`, `modifiers` oraz `modifier_summary`.
* `risk_state.support_effects` zapisuje informacje o uzytym support operation.
* Feedback systemowy dopisuje informacje `protected_by_camera_shutdown`.
* `camera_shutdown` sam nadal generuje wlasny risk event i nie chroni samego siebie.
* Ograniczono stackowanie reducerow: dla jednego eventu uzywany jest jeden najlepiej pasujacy `camera_shutdown`.
* Konto `admin` zostalo utrwalone jako konto developerskie z wyzszym poziomem, respectem, HC i flaga `dev_account`.
* Gameplay Smoke zostal rozszerzony o zakup i uzycie `camera_shutdown`.

### Najwazniejsze decyzje

* MVP reducera dziala na tym samym obiekcie albo w promieniu 80 m.
* Redukcja `camera_shutdown` wynosi -18 punktow risk score.
* Reducery nie stackuja sie wielokrotnie, zeby stare operacje testowe nie zbijaly ryzyka do zera.
* `camera_shutdown` nie redukuje ryzyka samego `camera_shutdown`; support operation ma wlasny koszt ryzyka.
* Typy `stealth`, `low_noise`, `anonymizer`, `spoofing` zostaja przygotowane kontraktowo, ale bez mechaniki w tym sprincie.

### Problemy

* Nie ma jeszcze UI panelu pokazujacego support effects poza danymi eventu i system message.
* Balans `-18` jest wartoscia MVP, do strojenia po pelniejszym Risk UI.
* Smoke admin kumuluje operacje i pliki testowe; to swiadome zachowanie runtime smoke, ale warto okresowo resetowac stan dev.

### Zmienione pliki

* `run.py`
* `tools/smoke_admin_inventory.py`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py tools\smoke_admin_inventory.py` - OK
* `node --check static/js/terminal.js` - OK
* `python -m unittest tests.test_target_persistence` - OK, 26 testow
* Gameplay Smoke `python tools\smoke_admin_inventory.py` - OK:
  * login admin,
  * instalacja/posiadanie aplikacji testowych,
  * `/tools` zawiera wymagane aplikacje,
  * akcje mapy tworza operacje,
  * `/api/operations` finalizuje operacje,
  * powstaja pliki GPS/Camera/ATM/Credentials,
  * Ghost Exchange widzi sprzedawalne pliki,
  * `camera_shutdown` sam generuje `camera_detected`,
  * `camera_stream` dostaje reducer `camera_shutdown`: `46 -> 28`.

### Status

Sprint 15 zamkniety.

### Nastepny sprint

Sprint 16 - Risk UI / tuning albo kolejny zakres z `game_play_260626.md`.

---

## 28.06.2026

### Sprint

Sprint 16 - Operation Lifecycle + Cleanup.

### Cel

Domknac cykl zycia operacji tak, zeby zakonczone, timeoutowane i anulowane operacje nie zostawialy aktywnych markerow, nie produkowaly duplikatow plikow i nie dawaly wygaslych efektow support.

### Co zostalo wykonane

* Dodano wspolne stale lifecycle: active, terminal, finalizable i risk-assessable statuses.
* Dodano cleanup state dla operacji terminalnych.
* `completed`, `timeout`, `failed`, `detected` i `cancelled` nie sa juz traktowane jako aktywne operacje.
* `persistent_sniffer` po zakonczeniu dostaje stan zakonczonego implantu.
* `camera_shutdown` po wygasnieciu przestaje byc aktywnym risk reducerem.
* Dodano risk event `abandoned_operation` dla operacji anulowanych.
* Dodano backendowy helper i endpoint `POST /api/operations/cancel`.
* Active Operations Panel dostal przycisk anulowania aktywnej operacji.
* `/api/operations` zwraca teraz osobno `active_operations` oraz `operation_history`.
* Dodano regresje dla anulowania operacji i wygaslego support reducera.

### Najwazniejsze decyzje

* `cancelled` nie jest sukcesem i nie uruchamia finalizerow plikow.
* Anulowanie zapisuje historie i lekki risk event, ale nie usuwa operacji z profilu.
* Support reducer dziala tylko wtedy, gdy operacja wspierajaca jest nadal aktywna.
* Historia operacji zostaje w profilu; cleanup dotyczy aktywnych markerow i efektow runtime.

### Problemy

* Gameplay Smoke admina pokazuje historyczne risk modifiers z poprzednich przebiegow, bo konto dev kumuluje stan. Aktualne zachowanie wygaslego supportu zabezpiecza test regresyjny.
* UI historii operacji jest jeszcze minimalne; panel mapy pokazuje aktywne operacje, a historia jest dostepna w payloadzie.

### Zmienione pliki

* `run.py`
* `templates/map_template.html`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py tools\smoke_admin_inventory.py` - OK
* `node --check static/js/terminal.js` - OK
* `python -m unittest tests.test_target_persistence` - OK, 28 testow
* Gameplay Smoke `python tools\smoke_admin_inventory.py` - OK:
  * admin ma wymagane aplikacje testowe,
  * akcje mapy tworza operacje,
  * `/api/operations` finalizuje/odswieza stan,
  * powstaja pliki GPS/Camera/ATM/Credentials,
  * Ghost Exchange widzi sprzedawalne pliki,
  * preview sale dziala.

### Status

Sprint 16 zamkniety.

### Nastepny sprint

Sprint 17 - kolejny zakres z `doc/game_play_260626.md`.

---

## 28.06.2026

### Sprint

Sprint 17 - Resource Completeness + Pricing.

### Cel

Sprawic, zeby lepsze aplikacje i bogatsze paczki danych mialy widoczna kompletność, jakosc oraz wyzsza wycene w Ghost Exchange.

### Co zostalo wykonane

* Dodano centralna normalizacje kompletności plikow runtime.
* Kazdy plik danych moze miec teraz `completeness_percent`, `completeness_tier`, `missing_fields` i `quality_score`.
* Ujednolicono kompletność dla GPS, Device, Camera, ATM, Financial i Credentials.
* Buildery nowych plikow dopisuja metadane kompletności i jakosci.
* Ghost Exchange liczy `price_preview` z base value, kompletności, jakosci, liczby zasobow i wolumenu.
* Listing Ghost Exchange pokazuje kompletność, tier, jakosc i brakujace pola.
* File Manager pokazuje kompletność/jakosc/braki w liscie plikow oraz w podgladach danych.
* Dodano regresje sprawdzajace normalizacje kompletności oraz wyzsza cene bogatszej paczki Device Intelligence.

### Najwazniejsze decyzje

* Kompletność jest normalizowana centralnie przy inventory, zeby stare pliki tez dostaly sensowne wartosci.
* `quality_score` jest liczba 0-100, a opisowe `quality` zostaje kompatybilnym dodatkiem.
* Dynamiczny popyt nie zostal dodany; losowy/deterministyczny multiplier zostal zachowany jako lekka wariacja preview.
* Finalny sale flow korzysta z tego samego `price_preview`, ale mechanika sprzedazy nie zostala przebudowana.

### Problemy

* Czesc tekstow File Managera nadal ma historyczne mojibake z wczesniejszego kodowania; Sprint 17 nie naprawial globalnie kodowania UI.
* Gameplay Smoke na koncie admin kumuluje pliki testowe i historie sprzedazy. To swiadome zachowanie konta developerskiego.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py tools\smoke_admin_inventory.py` - OK
* `node --check static/js/terminal.js` - OK
* `python -m unittest tests.test_target_persistence` - OK, 29 testow
* Gameplay Smoke `python tools\smoke_admin_inventory.py` - OK:
  * admin ma wymagane aplikacje,
  * akcje mapy tworza operacje,
  * `/api/operations` finalizuje dane,
  * powstaja pliki GPS/Camera/ATM/Credentials,
  * Ghost Exchange pokazuje nowe `price_preview`.
* Gameplay Smoke sale `python tools\smoke_admin_inventory.py --sell` - OK:
  * sprzedaz zwieksza HC,
  * duplicate sale jest blokowany,
  * plik znika z danych,
  * powstaje historia rynku i mail.

### Status

Sprint 17 zamkniety.

### Nastepny sprint

Sprint 18 - kolejny zakres z `doc/game_play_260626.md`.

---

## 28.06.2026

### Sprint

Sprint 18 - Googleplex Progression Integration.

### Cel

Domknac powrot HC z Ghost Exchange do gameplayu przez Googleplex: sprzedaz danych daje HC, a HC pozwala kupic aplikacje, ktore trafiaja do `/tools` i dzialaja z runtime map actions.

### Co zostalo wykonane

* Rozszerzono payload `/resources.json` o kontrakt aplikacji dla Googleplex:
  * `map_actions`,
  * `operation_types`,
  * `resource_types`,
  * `target_types`,
  * `app_level`,
  * `can_afford`,
  * `install_blocked_reason`.
* Ujednolicono normalizacje aplikacji tak, zeby kupione kopie mialy listowe `resource_types` i `target_types`.
* Googleplex pokazuje teraz podglad:
  * poziomu aplikacji Basic / Advanced / Pro,
  * akcji mapy,
  * typow operacji,
  * produkowanych zasobow.
* Wyszukiwarka Googleplex znajduje aplikacje rowniez po polach kontraktu, np. `trace_gps`, `vehicle_tracking`, `gps_logs`.
* Instalator blokuje duplikat jako `already_installed` zamiast udawac sukces.
* Instalator zwraca czytelny blad braku HC.
* Po zakupie backend zwraca komunikat `Aplikacja została zainstalowana.`
* Dodano dev smoke `tools/smoke_googleplex_progression.py`, ktory sprawdza swiezy zakup aplikacji i wpis w `/tools`.
* Dodano regresje dla payloadu Googleplex i blokad katalogu.

### Najwazniejsze decyzje

* `app_level` jest wyliczany runtime jako Basic / Advanced / Pro z ceny, wymagan i bogactwa kontraktu; nie zmieniamy ekonomii cen.
* Googleplex korzysta dalej z tego samego `/install-app`, bez nowego sklepu i bez drugiego instalatora.
* Aplikacje admin test seed moga miec `purchase_account: admin`; gdy kupuje je admin, smoke potwierdza instalacje, ale saldo netto admina moze sie nie zmienic.

### Problemy

* Czesc UI w `terminal.js` nadal ma historyczne mojibake, dlatego nie przebudowywano globalnie tekstow instalatora.
* Smoke Googleplex dla admina trafil na aplikacje z platnoscia do admina, wiec HC po zakupie zostaly netto bez zmian. Dla zwyklego gracza instalator nadal pobiera HC i przekazuje je odbiorcy.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `tests/test_target_persistence.py`
* `tools/smoke_googleplex_progression.py`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py tools\smoke_admin_inventory.py tools\smoke_googleplex_progression.py` - OK
* `node --check static/js/terminal.js` - OK
* `python -m unittest tests.test_target_persistence` - OK, 31 testow
* Gameplay Smoke `python tools\smoke_admin_inventory.py --sell` - OK:
  * admin ma aplikacje w `/tools`,
  * akcje mapy tworza operacje,
  * operacje finalizuja pliki,
  * Ghost Exchange pokazuje pliki,
  * preview i sprzedaz dzialaja,
  * duplicate sale jest blokowany.
* Googleplex Progression Smoke `python tools\smoke_googleplex_progression.py` - OK:
  * znaleziono niekupiona aplikacje z `map_actions`,
  * zakup przeszedl,
  * aplikacja trafila do `profile.apps`,
  * wpis `.sh` trafil do `files.tools`.

### Status

Sprint 18 zamkniety.

### Nastepny sprint

Sprint 19 - kolejny zakres z `doc/game_play_260626.md`.

---

## 28.06.2026

### Sprint

Sprint 19 - Integration Playtest + Balance Pass.

### Cel

Sprawdzic, czy pętla `mapa -> aplikacja -> operacja -> plik -> Ghost Exchange -> sprzedaz -> mail -> HC -> Googleplex -> /tools -> mapa` dziala jako jedna gra, a nie zestaw osobnych systemow.

### Co zostalo wykonane

* Przeprowadzono pelny playtest integracyjny kontem `admin`.
* Rozszerzono `tools/smoke_admin_inventory.py` o:
  * akcje `trace_device`,
  * pelny tryb `--full-loop`,
  * audyt spójnosci plikow danych,
  * kontrole liczby aktywnych operacji po cleanup,
  * guard przeciw nadmiernemu spamowi risk eventow,
  * sprzedaz po jednej paczce z glownych sciezek operacji.
* Smoke obejmuje teraz sciezki:
  * `vehicle_tracking -> gps -> sale`,
  * `device_tracking -> personal/device -> sale`,
  * `camera_stream -> camera -> sale`,
  * `atm_log_extraction -> atm/financial -> sale`,
  * `persistent_sniffer -> credentials/financial -> sale`,
  * `camera_shutdown -> risk reducer`.
* Potwierdzono, ze terminalne operacje nie zostaja jako aktywne po wymuszonym timeout/refresh.
* Potwierdzono, ze pliki maja `operation_id`, `source_operation_id`, `market_status` i `sellable`.
* Potwierdzono, ze duplicate sale jest blokowany przez istniejacy sale flow.
* Potwierdzono, ze Googleplex Progression Smoke instaluje kolejna aplikacje i dodaje ja do `/tools`.

### Najwazniejsze decyzje

* Sprint 19 nie dodaje nowej mechaniki; rozszerza testy smoke i naprawia tylko widocznosc playtestu.
* `risk_delta` w pelnym smoke jest traktowany jako wazniejszy wskaznik niz calkowita liczba `risk_events`, bo konto admin kumuluje historie.
* Przyjeto prosty guard smoke: risk delta powyzej 12 eventow na pelna petle oznacza potencjalny spam.
* Ceny preview w aktualnym loopie sa akceptowalne dla MVP: ok. 40-180 HC za paczke, z wyraznie wyzsza wartoscia credentials i ATM.

### Problemy

* Konto admin ma narastajacy runtime: pliki, market history, risk events i maile kumuluja sie po smoke. To zgodne z rola konta developerskiego, ale przed testami balansu warto okresowo resetowac swiat.
* Smoke Googleplex instalowal aplikacje z `purchase_account: admin`, wiec saldo netto admina nie spadlo. Instalacja, `/tools` i kontrakt aplikacji zostaly potwierdzone.
* Czesc komunikatow konsolowych nadal pokazuje mojibake z historycznego kodowania.

### Zmienione pliki

* `tools/smoke_admin_inventory.py`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py tools\smoke_admin_inventory.py tools\smoke_googleplex_progression.py` - OK
* `node --check static/js/terminal.js` - OK
* `python -m unittest tests.test_target_persistence` - OK, 31 testow
* Gameplay Smoke `python tools\smoke_admin_inventory.py --full-loop` - OK:
  * instalowane aplikacje sa w `/tools`,
  * akcje mapy tworza operacje,
  * po timeout active operations = 0,
  * risk delta = 9,
  * data consistency issues = 0,
  * Ghost Exchange widzi sprzedawalne pliki,
  * sprzedaz przeszla dla GPS, device/personal, camera, ATM i credentials.
* Googleplex Progression Smoke `python tools\smoke_googleplex_progression.py` - OK:
  * kupiono kolejna aplikacje z `map_actions`,
  * aplikacja trafila do `profile.apps`,
  * plik `.sh` trafil do `files.tools`.

### Status

Sprint 19 zamkniety.

### Nastepny sprint

Sprint 20 - Gameplay Loop Closure v1.

---

## 28.06.2026

### Sprint

Sprint 20 - Gameplay Loop Closure v1 / Release Candidate.

### Cel

Zamknac pierwsza grywalna wersje petli CHAOS v1:
`mapa -> aplikacja -> operacja -> aktywny swiat -> plik -> Ghost Exchange -> sprzedaz -> mail/HC -> Googleplex -> nowa aplikacja -> mapa`.

### Co zostalo wykonane

* Wykonano release candidate pass bez dodawania nowych mechanik.
* Uruchomiono walidacje skladni backendu i frontendu.
* Uruchomiono regresje `tests.test_target_persistence`.
* Uruchomiono pelny Gameplay Smoke kontem `admin` w trybie `--full-loop`.
* Uruchomiono Googleplex Progression Smoke.
* Potwierdzono spojnosc runtime:
  * po cleanup active operations = 0,
  * `operation_history` istnieje i narasta,
  * `market_history` istnieje przez sale flow,
  * `risk_events` istnieja i nie spamuja ponad guard smoke,
  * pliki danych maja `source_operation_id`,
  * sprzedane pliki nie zostaja w katalogach `/data`,
  * kupione aplikacje trafiaja do `/tools`.
* Przygotowano checkpoint repo pod tag `v0.3-gameplay-loop-v1`.

### Gameplay Loop v1 Status

#### Co dziala

* Router map actions korzysta z `app.map_actions`.
* Wybor narzedzia przechodzi przez `/tools`, gdy do akcji pasuje wiele aplikacji.
* Aplikacje tworza operacje runtime.
* Aktywne operacje odswiezaja stan bez realtime loopa.
* `vehicle_tracking`, `device_tracking`, `camera_stream`, `atm_log_extraction` i `persistent_sniffer` tworza pliki danych.
* File Manager obsluguje runtime inventory danych.
* Ghost Exchange pokazuje sprzedawalne pliki, robi preview i finalna sprzedaz.
* Sprzedaz dodaje HC, tworzy mail/system feedback i zabezpiecza przed duplicate sale.
* Googleplex pozwala wydac HC na kolejne aplikacje.
* Risk MVP i support reducer `camera_shutdown` dzialaja jako lekka warstwa kosztu ryzyka.

#### MVP / placeholder

* Konsekwencje ryzyka sa lekkie: warning, partial detection i cooldown placeholder.
* Brak jeszcze ciezkich kar typu jail, wanted level, HC loss.
* Brak dynamicznego rynku, frakcji, AI buyerow i player-to-player trading.
* Konto `admin` jest kontem developerskim i kumuluje runtime smoke.
* Czesc starych komunikatow konsolowych nadal ma historyczne problemy kodowania.

#### Sprint 21+

* Blacknet / AI / frakcje / research tree.
* Dynamiczny popyt i pelniejsze balansowanie ekonomii.
* Ciezsze konsekwencje ryzyka.
* Dalszy polish UI i czyszczenie historycznego kodowania.
* Nowe operacje tylko po domknieciu balansu v1.

### Najwazniejsze decyzje

* Sprint 20 nie dodaje nowych systemow; zamyka release candidate przez testy, smoke i porzadek repo.
* Full Gameplay Smoke jest brama zamkniecia sprintu.
* Runtime konta `admin`, SQLite, sesje i cache nie wchodza do commita.
* Googleplex smoke moze nie zmieniac salda netto admina, jesli `purchase_account` kupowanej aplikacji to `admin`; akceptujemy to jako ceche konta developerskiego.

### Problemy

* Nie znaleziono blokujacych regresji w RC pass.
* Runtime admina jest narastajacy; do czystych testow balansu nalezy uzyc resetu dev state.
* Mojibake w niektorych logach pozostaje znanym dlugiem polish.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `tests/test_target_persistence.py`
* `tools/smoke_admin_inventory.py`
* `tools/smoke_googleplex_progression.py`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py tools\smoke_admin_inventory.py tools\smoke_googleplex_progression.py` - OK
* `node --check static/js/terminal.js` - OK
* `python -m unittest tests.test_target_persistence` - OK, 31 testow
* Gameplay Smoke `python tools\smoke_admin_inventory.py --full-loop` - OK:
  * all required test apps are installed,
  * `/tools` contains installed apps,
  * map actions create operations,
  * forced timeout leaves active operations = 0,
  * operation history = 113,
  * risk delta = 9,
  * data consistency issues = 0,
  * Ghost Exchange files = 20,
  * sale passed for GPS, device/personal, camera, ATM and credentials.
* Googleplex Progression Smoke `python tools\smoke_googleplex_progression.py` - OK:
  * bought `admin_test_mic_sniff_2`,
  * app was added to `profile.apps`,
  * `Admin Mic Sniff Plus.sh` was added to `/tools`.

### Status

Sprint 20 zamkniety.

### Nastepny sprint

Sprint 21 - kolejny zakres po release candidate v1.

---

## 29.06.2026

### Sprint

v0.3.3 - Inventory Semantics Polish.

### Cel

Ujednolicic semantyke inventory po audycie routingu plikow:
`sellable` ma oznaczac kwalifikacje pliku do Ghost Exchange, a katalog `gps` ma byc czytelniejszy UX-owo dla `generic_trace`.

### Co zostalo wykonane

* Zmieniono normalizacje runtime files tak, zeby `sellable` bylo liczone tym samym filtrem co eligibility Ghost Exchange.
* Stare pliki po normalizacji dostaja spojny status `sellable` bez migracji katalogow.
* File Manager pokazuje katalog `gps` jako szersze `Sledzenie`, pozostawiajac techniczne `/gps`.
* Lista plikow pokazuje typ operacji w ludzkiej nazwie oraz status sprzedawalnosci.
* Podglad pliku pokazuje typ operacji w glownych widokach trackingowych.

### Najwazniejsze decyzje

* `sellable` oznacza eligibility do Ghost Exchange, a nie fakt przygotowania oferty.
* `market_status` zostaje osobnym stanem flow rynku: `not_listed`, `ready_to_list`, `listed_preview`, `sold`.
* `file_category = gps` zostaje bez migracji; UX label to `Sledzenie`, zeby `generic_trace` nie wygladal jak wylacznie GPS pojazdu.

### Problemy

* File Manager nadal ma historyczne mojibake w czesci tekstow UI; nie bylo to zakresem v0.3.3.
* Runtime admina narasta po smoke testach i nie powinien byc commitowany jako stan gry.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py` - OK
* `node --check static/js/terminal.js` - OK
* `python -m unittest tests.test_target_persistence` - OK, 38 testow
* Gameplay Smoke `python tools\smoke_admin_inventory.py --full-loop` - OK:
  * map actions create operations,
  * forced timeout leaves active operations = 0,
  * generated files are visible in Ghost Exchange,
  * full-loop sale passed for GPS, device/personal, camera, ATM and credentials.

### Status

v0.3.3 Inventory Semantics Polish zamkniety.

---

## 29.06.2026

### Phase 1 Complete

Pierwsza wersja gameplay loop zostala ukonczona.

Pelna sciezka gry dziala jako jedna petla:

Mapa

↓

Aplikacja

↓

Operacja

↓

Aktywny swiat

↓

Pliki

↓

Ghost Exchange

↓

Sprzedaz

↓

HackCoins

↓

Googleplex

↓

Nowe aplikacje

↓

Powrot na mape

### Efekt

CHAOS przechodzi z budowy silnika gameplayu do rozbudowy swiata gry i przygotowania pierwszych testow multiplayer na serwerze.

### Status

Phase 1 zamkniete. Wersja developerska v0.3.4-stable gotowa do wystawienia po commicie, tagu i pushu.

---

## 30.06.2026

### Sprint

Static JSON Resource Cleanup - Sprint A/B/C.

### Cel

Domknac architekture JSON -> SQLite i usunac niejasnosc, czy `static/*.json`
jest runtime source of truth.

### Co zostalo wykonane

* Dodano dokument `doc/resource_architecture.md` opisujacy warstwy:
  repository content, static JSON, `JsonResourceStore`, SQLite `json_resources`,
  backend runtime i profile runtime.
* Dodano `static/README.md` z podzialem plikow JSON na active seed,
  legacy/demo/reference, mail legacy/dev seed oraz future/reference.
* Dodano `tools/sync_static_json_resources.py` z trybem dry-run i `--apply`.
* Ograniczono automatyczny seed `JsonResourceStore.seed_static_directory()` do
  jawnej whitelisty runtime resources.
* Dodano test regresyjny pilnujacy, ze legacy JSON-y nie sa seedowane jako
  runtime resources.

### Najwazniejsze decyzje

* `static/*.json` jest contentem repozytorium i seed/reference, nie live runtime.
* Runtime source of truth dla JSON resources to SQLite `json_resources`.
* Runtime player state pozostaje w tabeli `users` / `profile_json`.
* Sync statycznych JSON-ow do SQLite jest jawna operacja developerska.

### Problemy

* Istniejace bazy moga nadal miec legacy klucze w `json_resources`; nowa
  whitelista blokuje ich automatyczne seedowanie, ale nie usuwa starych rekordow.

### Zmienione pliki

* `database.py`
* `doc/resource_architecture.md`
* `doc/project_journal.md`
* `static/README.md`
* `tests/test_target_persistence.py`
* `tools/sync_static_json_resources.py`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py tools/sync_static_json_resources.py` - OK
* `python -m unittest tests.test_target_persistence` - OK, 46 testow
* `python tools/sync_static_json_resources.py` - dry-run OK:
  * `changed`: `user_template`
  * `unchanged`: `app_config`, `fractions`, `friends`, `messages`, `terminal_command`, `user_security`
  * `extra_in_db`: legacy/reference keys pozostawione w istniejacej bazie runtime
* `python tools/sync_static_json_resources.py --apply --key app_config` - OK, backup poprzedniej wartosci zapisany w `data/backups/json_resources_sync_*`.
* `/resources.json` po syncu zwraca katalog Googleplex z SQLite.

### Status

Static JSON Resource Cleanup zamkniety.

---

## 30.06.2026

### Sprint

PM2 ecosystem configuration cleanup.

### Cel

Oddzielic lokalna konfiguracje PM2 konkretnego serwera od repozytorium,
podobnie jak runtime `data/game.sqlite3`.

### Co zostalo wykonane

* Dodano `ecosystem.config.example.js` jako wersjonowany template PM2.
* Dodano instrukcje kopiowania lokalnej konfiguracji:
  `cp ecosystem.config.example.js ecosystem.config.js`.
* Dodano `ecosystem.config.js` do `.gitignore`.

### Najwazniejsze decyzje

* `ecosystem.config.js` jest lokalnym plikiem serwera i nie powinien byc
  sledzony przez Git.
* `ecosystem.config.example.js` pozostaje w repo jako dokumentowany punkt startu
  dla nowych serwerow.

### Problemy

* Obecny `run.py` nadal uruchamia Flask przez `app.run(debug=True)`, wiec `PORT`
  w template jest przygotowany jako standard konfiguracji srodowiska, ale sama
  aplikacja musi go respektowac dopiero w osobnym tasku, jesli bedzie taka
  potrzeba.

### Zmienione pliki

* `.gitignore`
* `ecosystem.config.example.js`
* `doc/project_journal.md`

### Wynik testow

* `node --check ecosystem.config.example.js` - OK
* `git ls-files ecosystem.config.js` - pusty wynik, plik nie jest sledzony.

### Status

PM2 config cleanup zamkniety.

---

## 02.07.2026

### Sprint

Map context menu stabilization - player actors / territory / scan menu bug hunt.

### Cel

Ustabilizowac prawy klik na mapie po refaktorach player actors, player areas
i scan targetow. Objawem bylo otwieranie menu gracza albo obcego targetu po
kliknieciu w pozornie puste pole mapy.

### Co zostalo wykonane

* Przesledzono flow `map.on('contextmenu')`, marker contextmenu, tooltipow,
  legacy Folium polygonow i registry layerow.
* Dodano czyszczenie starych player area polygonow oraz defensywne registry
  cleanup dla warstw mapy.
* Usunieto popupy z player actor markerow i zamieniono ich zachowanie na menu
  pod prawym klikiem.
* Ograniczono hitbox player actor markerow: staly wrapper, `overflow:hidden`,
  brak elementow wychodzacych poza ikone.
* Dodano walidacje geometryczna `getBoundingClientRect()` przed otwarciem
  `showPlayerActorMenu()`.
* Dodano proteze dla false-positive Leaflet event: gdy Leaflet odpali handler
  player actora poza prawdziwym hitboxem markera, klik jest przeliczany z
  oryginalnego DOM eventu przez `map.mouseEventToContainerPoint()` i otwierane
  jest zwykle menu mapy.
* Usunieto tooltipy z player actorow, bo nick jest juz widoczny jako label nad
  avatarem.
* Dodano `doc/map_interactions.md` jako lekcje architektoniczna dla przyszlych
  sprintow mapy.
* Rozszerzono ten sam model ochrony na scan target markery: staly hitbox,
  kontrolowany wrapper HTML i walidacja `getBoundingClientRect()` przed
  otwarciem `showMarkerContextMenu()`.

### Najwazniejsze decyzje

* Player actor menu moze otwierac sie tylko po kliknieciu w realny rect markera.
* Pusty klik mapy ma pokazywac menu mapy: Skanuj / Podrozuj / Wyczysc scan.
* Proteza false-positive eventu zostaje jako defensywny airbag przy blednym
  routingu eventu Leafleta, ale nie zmienia mechaniki gry.
* Player actor tooltipy sa zbedne i zostaly usuniete z UI.
* Kazdy interaktywny obiekt mapy powinien byc samodzielny: wlasny registry,
  cleanup, snapshot danych, hitbox, menu i sciezka eventow.
* Obiekt mapy nie powinien udawac klikniecia w mape ani w inny obiekt. Protezy
  moga istniec tylko jako defensywny airbag, nie jako glowny routing.
* Scan target marker, interactive target marker i legacy scan marker uzywaja
  teraz tej samej zasady: menu targetu otwiera sie tylko, gdy klik lezy w
  realnym hitboxie markera.

### Problemy

* Leaflet potrafil odpalic marker `contextmenu` mimo klikniecia poza realnym
  rect markera. Przyczyna wydaje sie lezec w interakcji divIcon/hitbox/layerow
  po wielu refreshach mapy.
* W kodzie mapy pozostaja tymczasowe logi diagnostyczne `console.warn` i
  `console.trace` dodane podczas dochodzenia. Trzeba je usunac w osobnym polish
  tasku, gdy bug zostanie potwierdzony jako zamkniety.

### Zmienione pliki

* `templates/map_template.html`
* `doc/project_journal.md`
* `doc/map_interactions.md`

### Wynik testow

* Reczny test gracza potwierdzil, ze menu przy player actors zaczelo pokazywac
  sie poprawnie.
* Reczny test gracza potwierdzil, ze menu scan markerow nie miesza sie juz z
  innymi obiektami po zastosowaniu hitbox guardow.
* `/map` renderuje sie poprawnie w Flask test client.
* `git diff --check -- templates/map_template.html` - OK.

### Status

Map context menu stabilization w toku, ale glowny problem z menu player actorow
i scan markerow zostal praktycznie opanowany.

---

## 02.07.2026

### Sprint

Roadmap Sprint 21-30 - Googleplex Tool Laboratory.

### Cel

Rozpisac kolejna faze rozwoju po zamknieciu gameplay loop v1: kreatory,
kontrakt aplikacji, pojemnosc dysku, waga plikow, jakosc narzedzi i
Googleplex Tool Laboratory.

### Co zostalo wykonane

* Rozwinieto `doc/game_play_260626.md` o Sprinty 21-30.
* Sprinty 21-30 prowadza od audytu kreatorow do Googleplex Tool Laboratory v1.
* Dodano wprost pojemnosc i wage jako element kontraktu aplikacji oraz modelu
  plikow.
* Dodano wymagania dokumentacyjne przy sprintach: `app_contract.md`,
  `file_model.md`, `resource_types.md`, `data_economy.md`,
  `resource_architecture.md` i `map_interactions.md`.

### Najwazniejsze decyzje

* Nie budujemy drugiego sklepu ani drugiego publishera.
* Kreatory maja korzystac z istniejacego Googleplex i `json_resources.app_config`.
* AppForge, ButtonMaker, TermCreator, WindowMaker i GhostLab maja prowadzic do
  tego samego kontraktu aplikacji.
* Pojemnosc dysku, waga narzedzia, jakosc, niezawodnosc i moc twórcy staja sie
  czescia dalszej progresji.
* Roadmapa Sprintow 21-30 zostala podzielona na trzy fazy:
  Architektura gry, Edukacja gracza i Endgame.
* Dodano Sprint 21.5 jako Gameplay Contract pomiedzy audytem a implementacja
  storage.

### Problemy

* Obecne kreatory nadal opieraja sie mocno o stare pola `detects`,
  `interferes_with` i `affects`.
* `map_actions_source: migration_inferred` wymaga osobnego cleanupu, zeby
  narzedzia nie podswietlaly sie przy zlych akcjach mapy.

### Zmienione pliki

* `doc/game_play_260626.md`
* `doc/project_journal.md`

### Wynik testow

* Zmiana dokumentacyjna, bez uruchamiania testow runtime.

### Status

Roadmap Sprint 21-30 gotowy jako kierunek kolejnej fazy.

---

## 02.07.2026

### Sprint

Roadmap Sprint 31 - Database Migration & Server Upgrade Scripts.

### Cel

Dopisac do roadmapy zasade bezpiecznych migracji bazy danych na serwerze,
poniewaz runtime `data/game.sqlite3` jest gitignored i nie moze byc
aktualizowany przez commit.

### Co zostalo wykonane

* Dodano Sprint 31 do `doc/game_play_260626.md`.
* Opisano katalog migracji `migrations/` albo `scripts/db_migrations/`.
* Opisano numerowane migracje typu `001_add_storage_fields.py`.
* Dodano zasady: dry-run domyslnie, zapis tylko z `--apply`, backup przed
  migracja i idempotentnosc.
* Dodano koncepcje tabeli `schema_migrations`.
* Dodano checklist deploy: `git pull`, backup DB, migracja, restart app,
  gameplay smoke i wpis w journalu.

### Najwazniejsze decyzje

* Kazda zmiana struktury bazy danych ma miec wlasny skrypt migracyjny.
* Migracje musza byc idempotentne i bezpieczne do ponownego uruchomienia.
* Rollback robimy tylko wtedy, gdy jest prosty i bezpieczny; w innym przypadku
  rollbackiem jest przywrocenie backupu bazy.
* Kazda migracja po wykonaniu na serwerze dostaje wpis w `project_journal.md`.

### Problemy

* Migracje nie zostaly jeszcze zaimplementowane. To jest plan sprintu, nie
  runtime change.

### Zmienione pliki

* `doc/game_play_260626.md`
* `doc/project_journal.md`

### Wynik testow

* Zmiana dokumentacyjna, bez uruchamiania testow runtime.

### Status

Sprint 31 dopisany do roadmapy jako fundament bezpiecznych upgrade'ow serwera.

---

## 02.07.2026

### Sprint

Sprint 21 - Audit.

### Cel

Zrobic audyt kontraktu aplikacji, kreatorow, Googleplexa, File Managera
`/tools` i map tool selection przed budowa Googleplex Tool Laboratory.

### Co zostalo wykonane

* Sprawdzono runtime flow aplikacji: `json_resources.app_config` ->
  `get_app_catalog()` -> Googleplex -> `/install-app` -> `profile.apps` i
  `files.tools` -> `/hack-action`.
* Sprawdzono seed katalog `static/app_config.json`: 50 aplikacji, w tym 15 z
  `map_actions_source: migration_inferred`, 28 aplikacji admin-test i 7 bez
  `map_actions`.
* Wskazano mylace klasyfikacje narzedzi, szczegolnie PenCombo / `exploit_suite`
  przy `scan_ports`.
* Sprawdzono Googleplex cards i File Manager `/tools`: oba korzystaja juz z
  `map_actions`, ale nie pokazuja jeszcze zrodla kontraktu ani statusu
  support-only.
* Sprawdzono istniejace kreatory: AppForge, TermCreator, WindowMaker,
  ButtonMaker i GhostLab. Kreatory nadal opieraja sie glownie o stare pola
  `type/detects/affects/interferes_with`.
* Dodano raport `doc/sprint21_app_creator_audit.md`.
* Uzupelniono dokumentacje o `file_size`, `disk_usage`, `quality_score`,
  `reliability`, `creator_power` i zasady tool selection z mapy.

### Najwazniejsze decyzje

* Sprint 21 nie zmienia runtime i nie naprawia jeszcze klasyfikacji aplikacji.
* `migration_inferred` zostaje jako jawny dlug do Sprintu 24.
* Aplikacja bez `operation_types/resource_types` moze byc support-only, ale
  przyszly UI powinien to komunikowac graczowi.
* `file_size` opisuje artefakt aplikacji, a `disk_usage` koszt instalacji.
* `quality_score` i `reliability` sa czescia kontraktu aplikacji, ale nie sa
  routerem mapy.

### Problemy

* PenCombo moze podswietlac sie przy `scan_ports`, bo pochodzi ze starej
  migracji `exploit_suite`.
* Kilka exploitow ma `map_actions`, ale nie ma jeszcze jawnych
  `operation_types/resource_types`.
* Googleplex i File Manager nie pokazuja jeszcze, czy kontrakt aplikacji jest
  jawny czy migracyjny.

### Zmienione pliki

* `doc/sprint21_app_creator_audit.md`
* `doc/app_contract.md`
* `doc/file_model.md`
* `doc/map_interactions.md`
* `doc/project_journal.md`

### Wynik testow

* Audit seed katalogu przez Node - OK.
* `git diff --check` - OK.

### Status

Sprint 21 mozna uznac za zamkniety jako audyt i dokumentacyjny kontrakt wejscia
do Sprintu 21.5.

---

## 02.07.2026

### Sprint

Sprint 21.5 - Gameplay Contract.

### Cel

Zamienic audyt Sprintu 21 w jawny kontrakt aplikacji gameplayowej, zanim
kreatory zaczna generowac nowe narzedzia.

### Co zostalo wykonane

* Uporzadkowano pola aplikacji na grupy: UI / launcher, gameplay routing,
  ekonomia / progresja oraz legacy / migracja.
* Opisano pola wymagane dla kazdej aplikacji oraz dodatkowe pola wymagane dla
  narzedzi mapy.
* Doprecyzowano, ze `app.map_actions` pozostaje jedynym docelowym routerem
  wyboru narzedzia z mapy.
* Opisano fallback legacy po `type/detects/affects/interferes_with` jako
  migracje, nie glowna sciezke projektowa.
* Dodano checklist przyszlego kreatora aplikacji.
* Dopisano do slownika pojęcia: `file_size`, `disk_usage`, `quality_score`,
  `reliability`, `creator_power`.
* Doprecyzowano w File Model roznice miedzy waga aplikacji, kosztem instalacji
  i waga pliku danych.

### Najwazniejsze decyzje

* Tylko pola gameplay routing decyduja, czy aplikacja pasuje do akcji mapy.
* `interface` otwiera UI, ale nie decyduje o gameplayu.
* `quality_score` mowi o jakosci wyniku, a `reliability` o stabilnosci
  dzialania.
* `file_size` opisuje paczke/artefakt, a `disk_usage` miejsce zajete po
  instalacji.
* Sprint 21.5 nie wprowadza enforcementu pojemnosci, storage ani wizard UI.

### Problemy

* Katalog nadal zawiera aplikacje z `migration_inferred`; to pozostaje zakresem
  Sprintu 24.
* Stare kreatory nadal moga tworzyc aplikacje bez pelnego kontraktu gameplayu;
  wizard naprawi to dopiero w Sprincie 25.

### Zmienione pliki

* `doc/app_contract.md`
* `doc/gameplay_terms.md`
* `doc/file_model.md`
* `doc/project_journal.md`

### Wynik testow

* `git diff --check` - OK.

### Status

Sprint 21.5 mozna uznac za zamkniety jako kontrakt projektowy. Projekt jest
gotowy do Sprintu 22 - Disk Capacity + Tool File Size.

---

## 02.07.2026

### Sprint

Sprint 22 - Disk Capacity + Tool File Size.

### Cel

Dodac miękki model pojemnosci dysku oraz wagi aplikacji i plikow bez blokowania
gameplayu.

### Co zostalo wykonane

* Dodano domyslne pola profilu: `storage_capacity`, `storage_used`,
  `storage_unit`, `storage_soft_limit`, `storage_over_limit`.
* Dodano normalizacje aplikacji: `file_size`, `disk_usage`, `install_size`.
* Dodano domyslne `file_size` dla nowych i normalizowanych plikow gameplayowych.
* Googleplex pokazuje wage aplikacji i przewidywany koszt instalacji.
* File Manager pokazuje pasek uzycia dysku oraz rozmiar plikow/narzedzi.
* `/install-app` zwraca informacje o storage po instalacji i zapisuje
  przeliczone uzycie dysku.
* Sprzedaz pliku w Ghost Exchange przelicza storage, bo plik znika z `/data`.
* Uzupelniono dokumentacje `app_contract.md`, `file_model.md` i
  `resource_types.md`.

### Najwazniejsze decyzje

* Pojemnosc jest miękka: przekroczenie limitu jest informacja, nie blokada.
* Jednostka Sprintu 22 to umowne `MB`.
* `install_size` jest aliasem runtime dla `disk_usage`.
* Stare aplikacje i stare pliki dostaja wartosci domyslne przez normalizacje,
  bez migracji bazy.

### Problemy

* Wagi sa jeszcze heurystyczne i beda wymagaly balansu po realnym playtescie.
* Twarda blokada braku miejsca nie jest zaimplementowana celowo.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `static/user_template.json`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/file_model.md`
* `doc/resource_types.md`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence`
* `node --check static/js/terminal.js`

### Status

Sprint 22 mozna uznac za zamkniety jako miękki model storage. Projekt jest
gotowy do Sprintu 23 - Tool Quality + Creator Power.

---

## 02.07.2026

### Sprint

Sprint 23 - Tool Quality + Creator Power.

### Cel

Dodac jakosc, niezawodnosc i moc twórcy jako czesc kontraktu aplikacji, bez
budowania pelnego kreatora krokowego.

### Co zostalo wykonane

* Dodano normalizacje `creator_power`, `quality_score` i `reliability` dla
  aplikacji.
* Aplikacje generowane przez kreatory dostaja jakosc wyliczana z profilu
  twórcy: level, respect i HC.
* Operacja zapisuje snapshot jakosci aplikacji w `source_app_quality`.
* Finalizacja operacji moze podniesc `file.quality_score` do jakosci uzytego
  narzedzia.
* Googleplex pokazuje jakosc, niezawodnosc i moc twórcy.
* Tool selection payload dostaje metadane jakosci narzedzia.
* Uzupelniono dokumentacje `app_contract.md`, `resource_types.md` i
  `data_economy.md`.

### Najwazniejsze decyzje

* `quality_score` wplywa teraz na `file.quality_score`, a Ghost Exchange juz
  uwzglednia ten parametr w price preview.
* `reliability` jest zapisana w runtime, ale pelne awarie i rebalance ryzyka
  zostaja na pozniej.
* Stare aplikacje dostaja wartosci domyslne przez normalizacje, bez migracji
  bazy.
* Lepszy twórca tworzy lepsze narzedzie, ale nie tworzymy jeszcze nowego wizard
  UI.

### Problemy

* Wzory jakosci sa heurystyczne i beda wymagaly playtestu.
* Jakość podnosi wynik pliku, ale nie przebudowuje jeszcze kompletności danych.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/resource_types.md`
* `doc/data_economy.md`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence`
* `node --check static/js/terminal.js`

### Status

Sprint 23 mozna uznac za zamkniety jako runtime kontrakt jakosci narzedzi.
Projekt jest gotowy do Sprintu 24 - Map Tool Classification Cleanup.

---

## 02.07.2026

### Sprint

Sprint 24 - Map Tool Classification Cleanup.

### Cel

Wyczyścić klasyfikację narzędzi mapy tak, żeby wybór narzędzia pokazywał
aplikacje zgodne z `app.map_actions`, a nie przypadkowe dopasowania z pól
legacy.

### Co zostało wykonane

* Uporządkowano `get_apps_for_map_action()` tak, żeby uwzględniał flagę
  `CHAOS_LEGACY_MAP_ACTION_FALLBACK`.
* Dodano cleanup migracyjnych `map_actions` dla `exploit_suite`, żeby PenCombo
  nie pojawiało się przy `scan_ports`.
* Zostawiono jawne kontrakty jako źródło prawdy: hybrydowe narzędzie nadal może
  obsługiwać `scan_ports`, jeśli ma jawne `map_actions` bez źródła legacy.
* Zaktualizowano katalog `static/app_config.json`: PenCombo zostało jako
  narzędzie `exploit`, nie scanner.
* Dodano testy dla `scan_ports`, `exploit`, `sniff`, PenCombo /
  `exploit_suite` i wyłączania legacy fallbacku.
* Uzupełniono `app_contract.md`, `map_actions.md` i `gameplay_matrix.md`.

### Najważniejsze decyzje

* `scan_ports` jest akcją scanner/recon.
* `exploit_suite` nie dostaje `scan_ports` tylko dlatego, że wykrywa
  `open_ports` albo `weak_configs`.
* `migration_inferred` i `legacy_inferred` są kompatybilnością migracyjną, którą
  można wyłączyć w dev/test.
* `app.interface` nadal nie bierze udziału w gameplayowym routingu mapy.

### Problemy

* Część katalogu aplikacji nadal ma `map_actions_source: migration_inferred`.
  To jest świadomie zostawione jako stan przejściowy do kolejnych sprintów.
* Runtime SQLite może mieć starszy katalog aplikacji; cleanup w normalizacji
  zabezpiecza ten przypadek bez wymuszania migracji bazy.

### Zmienione pliki

* `run.py`
* `static/app_config.json`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/map_actions.md`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testów

* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence`
* `node --check static/js/terminal.js`

### Status

Sprint 24 można uznać za zamknięty. Projekt jest gotowy do Sprintu 25 -
Step-by-Step Tool Creator UX.

---

## 02.07.2026

### Sprint

Sprint 25 - Step-by-Step Tool Creator UX.

### Cel

Przekształcić istniejące kreatory aplikacji z dużego formularza w krokowy
wizard, bez tworzenia nowego kreatora, nowego sklepu ani nowego publish flow.

### Co zostało wykonane

* Dodano wspólny model kroków kreatora w `static/js/terminal.js`.
* AppForge, TermCreator, WindowMaker i ButtonMaker korzystają z jednego wizard
  shell.
* Formularz został podzielony na kroki: meta, typ narzędzia, środowisko,
  `map_actions`, `operation_types`, `resource_types`, ryzyko, storage/quality
  preview i publikacja.
* Publikacja nadal idzie przez istniejące `/api/apps/generate`.
* Backend zapisuje jawne pola kontraktu wybrane w kreatorze:
  `map_actions`, `target_types`, `operation_types`, `resource_types`.
* Aplikacje wygenerowane z jawnych `map_actions` dostają
  `map_actions_source: creator_explicit`.
* Dodano test regresyjny potwierdzający zachowanie jawnego kontraktu po
  publikacji.
* Uzupełniono dokumentację `app_contract.md`, `gameplay_terms.md`,
  `file_model.md` i `resource_architecture.md`.

### Najważniejsze decyzje

* Sprint 25 zmienia UX kreatorów, a nie tworzy nowy runtime.
* Istniejące kreatory pozostają osobnymi wejściami do tego samego procesu.
* Storage i quality są pokazane jako preview; twarde limity i balans pozostają
  poza zakresem tego sprintu.
* Ścieżki Scanner/Exploit/Sniffer ze Sprintów 26-27 nie zostały jeszcze
  zaimplementowane.

### Problemy

* Wizard nadal pozwala zostawić puste `map_actions`, żeby nie złamać prostych
  aplikacji UI/support.
* Preview storage/quality pokazuje źródła wartości, ale nie symuluje jeszcze
  pełnego kosztu ani ryzyka.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/gameplay_terms.md`
* `doc/file_model.md`
* `doc/resource_architecture.md`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js`
* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence`

### Status

Sprint 25 można uznać za zamknięty jako krokowy UX kreatorów. Projekt jest
gotowy do Sprintu 26 - Scanner Path.

---

## 02.07.2026

### Sprint

Sprint 26 - Scanner Creator Path.

### Cel

Dodać do istniejącego wizardu kreatorów świadomą ścieżkę Scanner / Recon,
traktowaną jako rodzinę narzędzi rozpoznania, a nie jedno `scan_ports`.

### Co zostało wykonane

* Rozszerzono wizard kreatorów o `tool_family: scanner_recon`.
* Dodano wybór trybu scanner/recon:
  `map`, `desktop`, `hybrid`.
* Wizard filtruje sensowne `map_actions`, `target_types`, `operation_types` i
  `resource_types` zależnie od trybu.
* Scanner desktopowy może mieć puste `map_actions` i działać jako narzędzie na
  aktualny `aimed_target`.
* Scanner mapowy i hybrydowy zapisują jawny kontrakt mapy przez
  `map_actions_source: creator_explicit`.
* Backend zapisuje `tool_family` i `scanner_mode` dla aplikacji generowanych.
* Dla `tool_family: scanner_recon` wyłączono inferencję legacy, żeby desktop
  scanner nie dostał `scan_ports` tylko przez `type/detects`.
* Dodano edukacyjne opisy w UI bez instrukcji ofensywnych.
* Dodano testy dla scannerów mapowych, desktopowych i hybrydowych.
* Uzupełniono dokumentację `app_contract.md`, `map_actions.md`,
  `resource_types.md` i `gameplay_matrix.md`.

### Najważniejsze decyzje

* Scanner / Recon to rodzina narzędzi: mapowe, desktopowe i hybrydowe.
* Desktop scanner nie musi mieć `map_actions`, ale musi mieć sensowny kontrakt
  celu, operacji i zasobów.
* Hybrydy zostawiają miejsce pod PenCombo-like tools, ale Sprint 26 nie
  implementuje ścieżki Exploit/Sniffer.
* `scan_ports` pozostaje support/recon state, nie domyślnym lootem.

### Problemy

* Filtrowanie opcji jest świadomie konserwatywne i będzie wymagało playtestu.
* Wizard nie waliduje jeszcze pełnej spójności wszystkich kombinacji; backend
  zachowuje kompatybilność ze starszymi aplikacjami.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/map_actions.md`
* `doc/resource_types.md`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js`
* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence`

### Status

Sprint 26 można uznać za zamknięty jako Scanner / Recon Creator Path. Projekt
jest gotowy do Sprintu 27 - Exploit Path.

---

## 02.07.2026

### Sprint

Sprint 27 - Exploit / Sniffer Creator Path.

### Cel

Dodać do istniejącego wizardu kreatorów świadome ścieżki Exploit i Sniffer,
analogicznie do Scanner / Recon, bez nowego kreatora i bez nowego publish flow.

### Co zostało wykonane

* Dodano `tool_family: exploit` i `tool_family: sniffer`.
* Dodano wspólne `tool_mode`: `map`, `desktop`, `hybrid`.
* Wizard filtruje sensowne `map_actions`, `target_types`, `operation_types` i
  `resource_types` dla Exploit oraz Sniffer.
* Dodano edukacyjne opisy: Exploit jako symulowany wpływ na słabości systemu w
  świecie gry, Sniffer jako symulowane zbieranie sygnałów/danych.
* Preview kontraktu pokazuje `tool_family`, `tool_mode`, środowisko, akcje,
  targety, operacje, zasoby, storage i quality.
* Backend zapisuje `tool_mode` dla nowych rodzin i wyłącza legacy inference dla
  `scanner_recon`, `exploit` i `sniffer`.
* Desktop Exploit/Sniffer może mieć puste `map_actions`, ale zachowuje jawny
  kontrakt celu, operacji i zasobów.
* Dodano testy dla mapowego i desktopowego Exploit oraz mapowego i hybrydowego
  Sniffer.
* Uzupełniono dokumentację `app_contract.md`, `map_actions.md`,
  `resource_types.md` i `gameplay_matrix.md`.

### Najważniejsze decyzje

* Exploit i Sniffer są rodzinami kreatora, nie nowym runtime.
* `install_sniffer` może należeć do Exploit albo Sniffer, bo gameplayowo łączy
  wpływ na cel z późniejszą obserwacją.
* `camera_stream` w Sniffer oznacza obserwację/surveillance.
* Nie dodano realnych komend ani instrukcji ofensywnych.

### Problemy

* Filtrowanie jest konserwatywne i może wymagać dopracowania po playtestach.
* Wizard nadal nie robi pełnej walidacji wszystkich kombinacji kontraktu.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/map_actions.md`
* `doc/resource_types.md`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js`
* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence`

### Status

Sprint 27 można uznać za zamknięty jako Exploit / Sniffer Creator Path. Projekt
jest gotowy do Sprintu 28 - GhostLab Pro Tools Contract.

---

## 02.07.2026

### Sprint

Sprint 28 - GhostLab Pro Tools Contract.

### Cel

Dopasować GhostLab i publikowane `pro-system-tool` do nowego kontraktu aplikacji
po Sprintach 25-27, bez przepisywania GhostLaba i bez tworzenia drugiego
publish flow.

### Co zostało wykonane

* Przejrzano obecny flow GhostLab: projekt, blueprint, compile, artifact,
  Publisher i zapis do Googleplex.
* Dodano mapowanie template GhostLab na kontrakt aplikacji:
  `tool_family`, `tool_mode`, `map_actions`, `target_types`,
  `operation_types`, `resource_types`.
* Publisher GhostLab zapisuje `map_actions_source: ghostlab_contract`.
* Publikowane `pro-system-tool` przechodzi przez normalizację storage i quality:
  `file_size`, `disk_usage`, `install_size`, `creator_power`,
  `quality_score`, `reliability`.
* Zachowano `required_level` i `required_respect` z template GhostLab.
* Dodano preview kontraktu w istniejącym panelu Publisher.
* Dodano testy dla kontraktu publikowanego narzędzia i kształtu payloadu
  Googleplex.
* Uzupełniono dokumentację `app_contract.md`, `gameplay_matrix.md` i
  `resource_types.md`.

### Najważniejsze decyzje

* GhostLab pozostaje cięższym IDE dla `pro-system-tool`, ale publikuje do tego
  samego `json_resources.app_config`.
* Nie powstał drugi sklep ani drugi publisher runtime.
* `pro-system-tool` domyślnie działa desktopowo na `player` przez Player Hack
  Access.
* Custom pro-system-tools nie tworzą nowych `operation_types` bez przyszłego
  runtime.

### Problemy

* `runtime_status: pending_custom_runtime` pozostaje świadomym ograniczeniem.
* Preview pokazuje kontrakt aplikacji, ale nie wykonuje custom runtime.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/gameplay_matrix.md`
* `doc/resource_types.md`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js`
* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence`

### Status

Sprint 28 można uznać za zamknięty jako GhostLab Pro Tools Contract. Projekt
jest gotowy do Sprintu 29 - Tool Balance Pass + Pricing.

---

## 02.07.2026

### Sprint

Sprint 29 - Tool Balance Pass + Pricing.

### Cel

Ujednolicić miękki balans ceny, wagi, jakości i wymagań narzędzi po Sprintach
21-28 bez tworzenia nowego sklepu, nowego pricing engine i bez twardego storage
enforcement.

### Co zostało wykonane

* Dodano normalizację pól `power_score`, `price_hint`, `balance_tier`,
  `recommended_level` i `recommended_respect`.
* Googleplex pokazuje teraz nie tylko cenę i wagę, ale też miękki `power_score`
  oraz `price_hint`.
* Kreatory pokazują w preview, że cena i moc narzędzia będą liczone przez
  runtime balance pass.
* Aplikacje generowane przez kreatory nie publikują się poniżej własnego
  `price_hint`.
* GhostLab `pro-system-tool` przechodzi przez ten sam balance pass i zostaje
  droższy oraz cięższy od zwykłego narzędzia.
* Seed/legacy aplikacje zachowują ręczne ceny, ale dostają `price_hint` dla UI i
  audytu.
* Dodano testy regresyjne dla pól balansu, cen aplikacji generowanych,
  kompatybilności legacy i różnicy między basic tool a pro-system-tool.
* Uzupełniono `app_contract.md`, `data_economy.md` i `file_model.md`.

### Najważniejsze decyzje

* `price_hint` jest sugestią balansu, nie drugim systemem cen.
* Istniejące seed/legacy ceny nie są automatycznie nadpisywane.
* Twarde wymagania `required_level` i `required_respect` zostają tylko tam, gdzie
  już były używane; dla reszty runtime dodaje miękkie rekomendacje.

### Problemy

* To pierwszy balance pass, więc liczby są heurystyczne i wymagają playtestów.
* Nie ma jeszcze dynamicznego popytu, frakcji kupujących ani finalnego pricingu
  narzędzi.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/data_economy.md`
* `doc/file_model.md`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js`
* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence` - 75 testów OK.
* `git diff --check` - brak błędów whitespace; tylko ostrzeżenia CRLF/LF dla
  istniejących plików roboczych, w tym `static/js/terminal.js`.

### Status

Sprint 29 można uznać za zamknięty jako Tool Balance Pass + Pricing. Sprint 30
nie został rozpoczęty.

---

## 02.07.2026

### Sprint

Sprint 30 - Googleplex Tool Laboratory v1.

### Cel

Domknąć pierwszy pełny lifecycle aplikacji: kreator albo GhostLab tworzy
kontrakt, publikuje go do Googleplex, gracz instaluje narzędzie, widzi je w
`/tools`, używa w runtime mapy/desktopu i może je odinstalować bez usuwania
projektu ani katalogu Googleplex.

### Co zostało wykonane

* Spięto Googleplex Tool Laboratory v1 jako lifecycle istniejących systemów:
  AppForge, TermCreator, WindowMaker, ButtonMaker, GhostLab, Googleplex,
  File Manager i runtime mapy.
* Googleplex pokazuje pełniejszy kontrakt narzędzia: rodzinę, tryb działania,
  map actions, operacje, zasoby, wagę, koszt instalacji, jakość,
  niezawodność, moc i cenę sugerowaną.
* File Manager `/tools` pokazuje po instalacji krótki opis kontraktu narzędzia:
  family/mode, jakość i power score.
* Dodano realny endpoint `POST /api/apps/uninstall`.
* Odinstalowanie usuwa aplikację z `profile.apps`, usuwa wpis z `files.tools`,
  przelicza `storage_used` i zwraca aktualny storage.
* Uninstall jest idempotentny dla brakującej aplikacji.
* Uninstall nie usuwa `files.projects` i nie modyfikuje katalogu
  `json_resources.app_config`.
* Dodano testy dla uninstall seed app, generated/runtime app i GhostLab app.
* Uzupełniono dokumentację lifecycle w `app_contract.md`, `file_model.md`,
  `data_economy.md` i `gameplay_matrix.md`.

### Najważniejsze decyzje

* Tool Laboratory v1 nie jest nowym sklepem ani nowym kreatorem. To wspólny
  cykl życia istniejących kreatorów, GhostLaba, Googleplexa i File Managera.
* Publikacja i instalacja są rozdzielone. Odinstalowanie usuwa instalację z
  profilu gracza, ale nie wycofuje publikacji z Googleplex.
* Brak miejsca na dysku nadal nie blokuje instalacji; storage pozostaje miękkim
  modelem UX.

### Problemy

* Kreatory nadal są lekkim wizardem, nie finalnym edytorem wizualnym.
* Refundy, odsprzedaż aplikacji i wtórny rynek narzędzi zostają poza v1.
* GhostLab custom runtime nadal pozostaje `pending_custom_runtime`.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `tests/test_target_persistence.py`
* `doc/app_contract.md`
* `doc/file_model.md`
* `doc/data_economy.md`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js`
* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence` - 79 testów OK.
* `git diff --check` - brak błędów whitespace; tylko ostrzeżenia CRLF/LF dla
  istniejących plików roboczych.

### Status

Sprint 30 można uznać za zamknięty jako Googleplex Tool Laboratory v1.

---

## 02.07.2026

### Sprint

Sprint 30.5 - Guided Tool Laboratory Experience.

### Cel

Zmienić istniejące kreatory z technicznego formularza w prowadzone doświadczenie
projektowania narzędzia, bez zmiany kontraktu aplikacji, publish flow, runtime,
ekonomii, storage i mapy.

### Co zostało wykonane

* Dodano strukturalną narrację kroków kreatora: `title`, `subtitle`,
  `description`, `educational_note`, `gameplay_hint`.
* Każdy panel wizardów dostaje opis decyzji, edukacyjne skojarzenie i gameplay
  hint.
* Zmieniono język widoczny dla gracza: zamiast `target_types`,
  `operation_types` i `resource_types` kreator pyta o obiekt, działanie i
  informacje.
* Listy wyboru pokazują przyjazne nazwy, ale nadal wysyłają te same wartości
  kontraktu do `/api/apps/generate`.
* Wybór `tool_family`, `tool_mode` i `target_types` zawęża kolejne decyzje:
  `map_actions`, `operation_types` i `resource_types`.
* Dodano style dla narracyjnego panelu kroku.
* Uzupełniono `game_play_260626.md`, `app_contract.md` i `gameplay_terms.md`.

### Najważniejsze decyzje

* Guided UX jest warstwą tłumaczącą istniejący kontrakt, nie nowym modelem.
* Narracja nie podaje nazw realnych narzędzi ani instrukcji ofensywnych.
* Wartości techniczne zostają w payloadzie i runtime, a UI pokazuje je językiem
  gracza.

### Problemy

* To nadal lekki wizard HTML/JS. Pełny visual builder zostaje poza Sprintem
  30.5.
* Tryb `custom` nadal może pokazać szeroki zestaw opcji, bo nie ma jednej
  bezpiecznej domeny filtrującej.

### Zmienione pliki

* `static/js/terminal.js`
* `static/css/style.css`
* `doc/game_play_260626.md`
* `doc/app_contract.md`
* `doc/gameplay_terms.md`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js`
* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence` - 79 testów OK.
* `git diff --check` - brak błędów whitespace; tylko ostrzeżenia CRLF/LF dla
  istniejących plików roboczych.

### Status

Sprint 30.5 można uznać za zamknięty jako Guided Tool Laboratory Experience.

---

## 02.07.2026

### Sprint

Sprint 30.9 - Release Candidate Preparation.

### Cel

Przygotować projekt do pierwszego dużego wdrożenia po Sprintach 21-30.5:
commit, push, pull na serwerze, migracje, restart PM2 i gameplay smoke.

### Co zostało wykonane

* Przeprowadzono audyt gotowości po Sprintach 21-30.5 dla backendu,
  frontendu, Googleplexa, GhostLaba, kreatorów, File Managera, storage,
  uninstallu, map tool selection i dokumentacji.
* Utworzono `doc/release_candidate_30_9.md` jako instrukcję Release Candidate.
* Wypisano potencjalne migracje dla Sprintu 31:
  `schema_migrations`, storage defaults, normalizacja zainstalowanych aplikacji,
  reconciliation `files.tools` i świadomy sync `app_config`.
* Przygotowano checklisty deployu, rollbacku, smoke testów i obserwacji po
  pierwszym uruchomieniu.
* Potwierdzono, że Sprint 30.9 nie wykonuje migracji i nie zmienia runtime
  gameplayu.

### Najważniejsze decyzje

* Release Candidate 30.9 jest materiałem wdrożeniowym, nie nową funkcją.
* Właściwy runner migracji i tabela `schema_migrations` należą do Sprintu 31.
* Runtime normalizatory chronią stare profile, ale migracja utrwalająca nowe
  pola jest zalecana przed większym playtestem na serwerze.
* Sync `static/app_config.json` do `json_resources.app_config` wymaga backupu i
  dry-run, bo serwerowy katalog może zawierać aplikacje opublikowane przez
  graczy/GhostLab.

### Problemy

* Serwerowa baza jest gitignored, więc prawdziwa walidacja migracji wymaga kopii
  runtime DB.
* GhostLab custom runtime nadal pozostaje `pending_custom_runtime`.
* Storage jest miękki i nie blokuje przepełnienia.
* Balance cen/wagi/jakości jest pierwszą heurystyką i wymaga playtestów.

### Zmienione pliki

* `doc/release_candidate_30_9.md`
* `doc/project_journal.md`

### Wynik testów

Do uzupełnienia po uruchomieniu walidacji Sprintu 30.9:

* `python -m py_compile run.py database.py profileManagment.py`
* `python -m unittest tests.test_target_persistence`
* `node --check static/js/terminal.js`
* `git diff --check`

### Status

Sprint 30.9 jest przygotowany dokumentacyjnie. Commit, push, migracje i deploy
nie zostały wykonane.

### Wynik testów - aktualizacja Sprintu 30.9

* `python -m py_compile run.py database.py profileManagment.py` - OK.
* `python -m unittest tests.test_target_persistence` - 79 testów OK.
* `node --check static/js/terminal.js` - OK.
* `git diff --check` - brak błędów whitespace; tylko ostrzeżenia CRLF/LF dla
  istniejących plików roboczych `static/app_config.json`,
  `static/css/style.css` i `static/user_template.json`.

---

## 02.07.2026

### Sprint

Sprint 31 - App Catalog Cleanup & Server Seed Tools.

### Cel

Dodać etap porządkowania katalogu aplikacji przed standardowymi migracjami
serwerowymi: wyczyścić stare narzędzia testowe, dodać produkcyjny zestaw
`admin_seed_v1` i przygotować bezpieczny runner migracji SQLite.

### Co zostało wykonane

* Dodano `scripts/app_catalog_cleanup.py`.
* Skrypt działa domyślnie jako dry-run i zapisuje dopiero z `--apply`.
* Przy `--apply` skrypt robi backup bazy do `data/backups`.
* Cleanup działa na `json_resources.app_config`.
* Skrypt usuwa/raportuje `admin_test_seed`, `migration_inferred` i rekordy bez
  sensownego kontraktu.
* Skrypt zachowuje aplikacje generated/player-created i GhostLab published.
* Dodano produkcyjny zestaw narzędzi `admin_seed_v1` dla istotnych map actions.
* Cleanup profili usuwa testowe aplikacje, czyści orphan `files.tools`,
  zachowuje `files.projects` i przelicza `storage_used`.
* Dodano runner migracji `scripts/db_migrations/run_migrations.py`.
* Dodano migracje:
  * `001_schema_migrations.py`,
  * `002_profile_storage_defaults.py`,
  * `003_installed_apps_normalization.py`,
  * `004_files_tools_reconciliation.py`.
* Dodano dokument `doc/database_migrations.md`.
* Uzupełniono `release_candidate_30_9.md`, `game_play_260626.md` i
  `app_contract.md`.
* Dodano testy jednostkowe cleanupu katalogu w `tests/test_app_catalog_cleanup.py`.

### Najważniejsze decyzje

* `admin_seed_v1` zastępuje developerski `admin_test_seed` jako produkcyjny
  zestaw startowy narzędzi Googleplexa.
* Aplikacje generated/player-created i GhostLab published są chronione przed
  cleanupem.
* Stare `migration_inferred` nie jest finalnym źródłem klasyfikacji narzędzi i
  może zostać usunięte albo ręcznie zatwierdzone przed deployem.
* Migracje są idempotentne, domyślnie dry-run i zapisują stan w
  `schema_migrations`.

### Problemy

* Nie wykonano migracji produkcyjnej ani lokalnego apply na runtime DB.
* Po pierwszym udanym `py_compile` lokalny alias `python.exe` zaczął zwracać
  błąd Windows: "Określona sesja logowania nie istnieje". Z tego powodu pełne
  testy Pythona trzeba powtórzyć po naprawie/interpreterze lokalnym.
* `admin_seed_v1` jest pierwszym produkcyjnym zestawem seed narzędzi i wymaga
  playtestu cen/opisów przed publicznym balansem.

### Zmienione pliki

* `scripts/app_catalog_cleanup.py`
* `scripts/db_migrations/run_migrations.py`
* `scripts/db_migrations/001_schema_migrations.py`
* `scripts/db_migrations/002_profile_storage_defaults.py`
* `scripts/db_migrations/003_installed_apps_normalization.py`
* `scripts/db_migrations/004_files_tools_reconciliation.py`
* `scripts/db_migrations/migration_helpers.py`
* `tests/test_app_catalog_cleanup.py`
* `doc/database_migrations.md`
* `doc/release_candidate_30_9.md`
* `doc/game_play_260626.md`
* `doc/app_contract.md`
* `doc/project_journal.md`

### Wynik testów

* `python -m py_compile run.py database.py profileManagment.py scripts/app_catalog_cleanup.py scripts/db_migrations/run_migrations.py scripts/db_migrations/001_schema_migrations.py scripts/db_migrations/002_profile_storage_defaults.py scripts/db_migrations/003_installed_apps_normalization.py scripts/db_migrations/004_files_tools_reconciliation.py` - OK.
* `node --check static/js/terminal.js` - OK.
* `git diff --check` - brak błędów whitespace; tylko ostrzeżenia CRLF/LF dla
  istniejących plików roboczych.
* `python -m unittest tests.test_app_catalog_cleanup` - 3 testy OK.
* `python -m unittest tests.test_target_persistence` - 79 testów OK.

### Status

Sprint 31 jest przygotowany jako zestaw narzędzi i dokumentacji. Testy
regresyjne przeszły na działającym interpreterze uruchomionym poza sandboxem.

---

## 03.07.2026

### Sprint

Sprint 32 - Target Bar Feedback Audit & Plan.

### Cel

Przygotować plan subtelnego feedbacku hackowania na belce CEL bez implementacji
mechaniki, UI ani zmian runtime.

### Co zostało wykonane

* Sprawdzono renderowanie górnej belki statusu w `static/js/terminal.js`.
* Potwierdzono, że belka CEL korzysta z `toolbarProfile.aimed_target`.
* Sprawdzono, że `/api/profile` zwraca pełny profil po `sync_session_profile()`
  i `refresh_and_persist_operations()`.
* Sprawdzono, że `/hack-action` aktualizuje `profile.aimed_target.security`
  oraz `profile.aimed_target.actions_allowed`.
* Potwierdzono, że `templates/map_template.html` odświeża toolbar po akcji przez
  `refreshParentToolbarProfile()`.
* Przygotowano plan Sprintu 33 dla kropek `actions_allowed` i cienkiego paska
  rozbrojenia celu.

### Najważniejsze decyzje

* Feedback ma pozostać wyłącznie w sekcji CEL.
* Kropki reprezentują tylko `scan_ports`, `exploit`, `sniff`, `trace`.
* Pasek pokazuje rozbrojenie celu, nie poziom zabezpieczenia.
* Obliczenia można wykonać po stronie frontendu na podstawie `aimed_target`,
  bez nowego endpointu.

### Problemy

* Lista boolean security keys jest obecnie zduplikowana logicznie: backend ma
  `CRITICAL_SECURITY_KEYS`, a frontend nie ma jeszcze wspólnego read modelu dla
  belki CEL.
* Trzeba pilnować, aby subtelny feedback nie rozpychał dolnego paska na mobile.

### Zmienione pliki

* `doc/project_journal.md`

### Wynik testów

Nie uruchamiano testów, bo Sprint 32 jest audytem i planem bez zmian runtime.

### Status

Sprint 32 jest gotowy jako raport i plan implementacji Sprintu 33.

---

## 03.07.2026

### Sprint

Sprint 33 - Target Bar Micro Feedback.

### Cel

Dodać subtelny, animowany feedback postępu hackowania wyłącznie w sekcji CEL,
bez nowego panelu, bez backendu i bez zmiany mechaniki gameplayu.

### Co zostało wykonane

* Dodano frontendowy read model dla kropek `actions_allowed`.
* Dodano frontendowe liczenie poziomu rozbrojenia z boolean security keys.
* Dodano preferencję przyszłego backendowego read modelu
  `aimed_target.disarm_progress` / `aimed_target.feedback.disarm_progress`.
* Dodano monotoniczny progress paska w obrębie tego samego celu.
* Dodano stan poprzedniego feedbacku, żeby zwykły refresh nie powodował migania.
* Rozszerzono `renderToolbarStatus()` o mikro-feedback w istniejącej belce CEL.
* Dodano CSS dla czterech stałych kropek, cienkiego paska i subtelnych animacji.
* Rozszerzono test helperów terminala o target bar feedback.

### Najważniejsze decyzje

* Feedback jest wyłącznie wizualizacją stanu, nie mechaniką.
* Kropki mają stałą kolejność: `scan_ports`, `exploit`, `sniff`, `trace`.
* Pasek nie cofa się dla tego samego celu, żeby starszy snapshot profilu nie
  dawał wrażenia regresu.
* Frontend nie pokazuje liczby zabezpieczeń, procentów ani pełnego stanu celu.

### Problemy

* Lista security keys jest lokalnym read modelem frontendu i powinna zostać
  zastąpiona backendowym `aimed_target.feedback`, jeśli backend zacznie go
  udostępniać.

### Zmienione pliki

* `static/js/terminal.js`
* `static/css/style.css`
* `tools/test_terminal_runtime_helpers.js`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` - OK.
* `node --check tools/test_terminal_runtime_helpers.js` - OK.
* `node tools/test_terminal_runtime_helpers.js` - OK.
* `python -m py_compile run.py database.py profileManagment.py` - OK.
* `python -m unittest tests.test_target_persistence` - 83 testy OK.

### Status

Sprint 33 można uznać za zamknięty jako frontendowy micro feedback belki CEL.

---

## 03.07.2026

### Sprint

Sprint 34 - Target Bar UX Polish.

### Cel

Domknąć wizualnie sekcję CEL tak, aby stan bez celu wyglądał jak zwykły element
statusbara, a oznaczony cel aktywował rozszerzony tryb hackowania.

### Co zostało wykonane

* Uproszczono markup neutralnego stanu CEL do takiego samego układu jak pozostałe
  pola statusbara.
* Rozszerzony wrapper feedbacku renderuje się tylko wtedy, gdy istnieje
  oznaczony cel.
* Dodano płynne przejścia dla koloru, ramki, tła, cienia, paddingu i wysokości
  sekcji CEL.
* Zachowano rozszerzoną wysokość tylko dla stanu z oznaczonym celem.
* Dostosowano CSS mobile tak, aby neutralny CEL miał standardową wysokość, a
  rozszerzenie dotyczyło tylko sekcji CEL.

### Najważniejsze decyzje

* Stan neutralny nie ma kropek, paska, czerwonego tła ani dodatkowego wrappera.
* Sprint 34 nie zmienia read modelu, algorytmu progressu ani danych backendowych.

### Problemy

* Powrót z celu do braku celu animuje głównie kontener belki CEL. Sam feedback
  znika wraz ze zmianą markup, bo nie dodano osobnego systemu exit animation.

### Zmienione pliki

* `static/js/terminal.js`
* `static/css/style.css`
* `doc/project_journal.md`

### Wynik testów

* `node --check static/js/terminal.js` - OK.
* `python -m py_compile run.py database.py profileManagment.py` - OK.
* `python -m unittest tests.test_target_persistence` - 83 testy OK.
* `node tools/test_terminal_runtime_helpers.js` - OK.

### Status

Sprint 34 można uznać za zamknięty jako UX polish belki CEL.

---

## 03.07.2026

### Sprint

Faza D - Finalny plan Sprintów 35-39.

### Cel

Zamknąć plan implementacji Ghost Exchange jako automatycznego rynku danych oraz
Storage Economy bez tworzenia drugiego rynku, drugiego systemu plików, drugiego
storage ani drugiej ekonomii.

### Co zostało wykonane

* Uporządkowano Sprinty 35-39 w `doc/game_play_260626.md` do formatu
  implementacyjnego.
* Doprecyzowano, że Ghost Exchange rozwija istniejące `profile.files`,
  `sellable`, `market_status`, `files.market`, `profile.market_history`,
  `storage_capacity`, `storage_used`, `file_size` i `price_preview`.
* Rozpisano Storage Economy od początku Fazy D: dane zajmują miejsce, pełny dysk
  blokuje zapis danych, a auto sale zwalnia storage.
* Doprecyzowano, że Storage Upgrade jest produktem Googleplexa, nie aplikacją i
  nie osobnym sklepem.
* Doprecyzowano, że auto sale następuje po osiągnięciu progu sektora oraz po
  minimalnym czasie przebywania paczki na rynku.
* Dodano `estimated_sale_time` jako metrykę read modelu Ghost Exchange.
* Dodano finalną architekturę Fazy D z pełnym przepływem:
  operacja -> finalizer -> storage -> market queue -> sector batch -> auto
  settlement -> HC -> Googleplex.

### Najważniejsze decyzje

* File Manager pozostaje miejscem przeglądania lootów.
* Ghost Exchange jest dashboardem rynku danych i read modelem istniejącego
  profilu.
* Googleplex pozostaje jedynym miejscem wydawania HC.
* Auto sale ma być kontrolowanym refreshem, nie realtime loopem.
* Stan `listed` / `trading` ma budować poczucie żywego rynku zamiast
  natychmiastowej sprzedaży po przekroczeniu progu.
* Manual sell może zostać tylko jako legacy/dev/debug.

### Problemy

* Brak implementacji w tym wpisie. To świadomie tylko finalny plan wykonawczy
  przed rozpoczęciem Sprintu 35.

### Zmienione pliki

* `doc/game_play_260626.md`
* `doc/project_journal.md`

### Wynik testów

* `git diff --check -- doc/game_play_260626.md` - OK.

### Status

Plan Sprintów 35-39 można uznać za zamknięty i gotowy do implementacji sprint po
sprincie.

---

## 03.07.2026

### Sprint

Sprint 35 - Ghost Exchange Market Model + Storage Gate Foundation.

### Cel

Wdrożyć fundament modelu rynku danych i storage gate bez dashboardu, bez
auto-sale, bez batchy, bez nowych endpointów i bez przebudowy UI.

### Co zostało wykonane

* Dodano helper `market_sector_for_file(file_entry)` mapujący istniejące
  `file_category` i `resource_types` na sektor rynku.
* Dodano helper `normalize_file_market_status(file_entry)` dla statusów:
  `not_listed`, `ready_to_list`, `listed_preview`, `listed`, `sold`,
  `archived`.
* Dodano helper `is_market_eligible_file(file_entry)` oparty o istniejące
  znaczenie `sellable`.
* Dodano helper `can_store_runtime_file(profile, file_entry)` sprawdzający
  `storage_capacity`, `storage_used` i `file_size`.
* Dodano helper `build_storage_full_result(profile, operation, file_entry)`
  zwracający kontrolowany wynik `storage_full` / `dropped_no_space`.
* Rozszerzono payload Ghost Exchange o read-model pola:
  `market_sector`, `market_volume_mb`, `normalized_market_status` i
  `market_lifecycle_status`.
* Zachowano kompatybilność istniejącego `market_status` w payloadzie, żeby nie
  zepsuć legacy preview/sell UI.
* Zaktualizowano smoke admin inventory tylko o wypisywanie pól Sprintu 35.

### Najważniejsze decyzje

* Sprint 35 nie uruchamia queue, batchy ani auto-sale.
* Sprint 35 nie zmienia `POST /api/ghost-exchange/sell` ani preview.
* Storage gate jest helperem przygotowawczym; finalizery nie zostały jeszcze
  przełączone na twarde enforcement.
* `profile.files` pozostaje jedynym źródłem danych.

### Problemy

* Smoke `tools/smoke_admin_inventory.py` nie uruchomił się w lokalnej sesji
  PowerShell z błędem uruchomienia procesu `python.exe`: `Określona sesja
  logowania nie istnieje`. Ten sam interpreter działa dla `py_compile` i testów
  unittest, więc problem dotyczy uruchomienia skryptu smoke w tej sesji.

### Zmienione pliki

* `run.py`
* `tests/test_target_persistence.py`
* `tools/smoke_admin_inventory.py`
* `doc/file_model.md`
* `doc/data_economy.md`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testów

* `python -m py_compile run.py database.py profileManagment.py tools/smoke_admin_inventory.py` - OK.
* `python -m unittest tests.test_target_persistence` - 88 testów OK.
* `git diff --check` - OK.
* `python tools/smoke_admin_inventory.py --real-ui-check` - nie wystartował z
  powodu błędu środowiska procesu `python.exe`.
* `python tools/smoke_admin_inventory.py --no-seed --no-sale` - nie wystartował
  z tego samego powodu.

### Status

Implementacja Sprintu 35 jest gotowa kodowo i przeszła testy regresyjne.
Gameplay smoke wymaga ponownego uruchomienia w działającej sesji procesu przed
formalnym zamknięciem sprintu.

---

## 03.07.2026

### Sprint

Sprint 36 - Market Queue + File Lifecycle.

### Cel

Wprowadzić automatyczne kolejkowanie sprzedawalnych plików jako stan istniejących
plików w `profile.files`, bez tworzenia osobnej kolejki, batchy, auto-sale,
dashboardu ani storage upgrade.

### Co zostało wykonane

* Dodano helper `queue_market_eligible_files(profile)`.
* Helper przechodzi po istniejących `profile.files`, korzysta z helperów
  Sprintu 35 i działa idempotentnie.
* Pliki market eligible dostają:
  * `market_status: queued_for_market`,
  * `queued_at`,
  * `market_sector`.
* `queued_at` jest ustawiane tylko raz i nie resetuje się przy kolejnym
  refreshu.
* `GET /api/ghost-exchange` wywołuje kolejkowanie i zapisuje zmienione pliki do
  profilu tylko wtedy, gdy faktycznie coś się zmieniło.
* Dodano sektorowy read model Ghost Exchange:
  * `sector`,
  * `pending_files`,
  * `pending_mb`,
  * `threshold_mb`,
  * `missing_mb`,
  * `missing_records`,
  * `progress_percent`,
  * `estimated_sale_time`.
* Rozszerzono smoke admin inventory o wypisywanie sektorów pending i liczby
  plików `queued_for_market`.

### Najważniejsze decyzje

* Kolejka rynku jest stanem pliku w `profile.files`, nie osobnym magazynem.
* `collect_ghost_exchange_files()` pozostaje read-only, żeby nie zmieniać
  zachowania legacy preview/sell.
* Sprint 36 nie dotyka `profile.market_history`, nie dodaje HC i nie usuwa
  plików z `/data`.
* `estimated_sale_time` jest tylko placeholderem read modelu, nie licznikiem
  settlementu.

### Problemy

* Smoke `tools/smoke_admin_inventory.py` nadal nie startuje w lokalnej sesji
  PowerShell z błędem procesu `python.exe`: `Określona sesja logowania nie
  istnieje`. Testy `py_compile` i `unittest` działają poprawnie.

### Zmienione pliki

* `run.py`
* `tests/test_target_persistence.py`
* `tools/smoke_admin_inventory.py`
* `doc/file_model.md`
* `doc/data_economy.md`
* `doc/project_journal.md`

### Wynik testów

* `python -m py_compile run.py database.py profileManagment.py tools/smoke_admin_inventory.py` - OK.
* `python -m unittest tests.test_target_persistence` - 91 testów OK.
* `python tools/smoke_admin_inventory.py --no-seed --no-sale` - nie wystartował
  z powodu błędu środowiska procesu `python.exe`.

### Status

Implementacja Sprintu 36 jest gotowa kodowo i przeszła testy regresyjne.
Formalne zamknięcie wymaga ponownego uruchomienia smoke w działającej sesji.
---

## 03.07.2026

### Sprint

Sprint 37 - Auto Sale Settlement Engine.

### Cel

Uruchomic kontrolowany settlement Ghost Exchange: pliki z kolejki rynku tworza
paczki sektorowe, paczka po osiagnieciu progu przechodzi w `listed`, a po
minimalnym czasie na rynku sprzedaje sie automatycznie bez recznego klikania
`Sprzedaj`.

### Co zostalo wykonane

* Dodano `MARKET_SECTOR_DWELL_SECONDS` z minimalnym czasem przebywania paczki na
  rynku per sektor.
* Dodano helper `refresh_market_runtime(username, profile, now=None,
  persist=False)`.
* Dodano stabilne `batch_id` dla paczki sektorowej oparte o gracza, sektor i
  identyfikatory plikow.
* Po osiagnieciu progu sektora pliki dostaja `market_status: listed`,
  `listed_at` i `batch_id`.
* Auto-sale uruchamia sie dopiero po uplywie minimalnego czasu na rynku.
* Settlement sprawdza idempotencje przez `profile.market_history` i
  `files.market`, nalicza HC raz, dodaje rekord rynku, usuwa sprzedane pliki z
  katalogow `/data/*`, przelicza storage oraz dodaje system message i mail.
* `GET /api/ghost-exchange` wywoluje settlement jako kontrolowany refresh
  istniejacego endpointu.
* Smoke admin inventory wypisuje `market_runtime`, status sektorow, `listed_at`
  i `batch_id`.

### Najwazniejsze decyzje

* Nie powstal realtime loop, scheduler, worker ani nowy endpoint.
* Kolejka i listing pozostaja stanem plikow w `profile.files`.
* `files.market` przechowuje rekord sprzedazy paczki, a nie nowe looty.
* Manual sell zostaje kompatybilnoscia legacy/dev i nie zostal przebudowany.
* Dashboard Ghost Exchange nie zostal zaimplementowany; nalezy do Sprintu 38.

### Problemy

* W trakcie testow wykryto, ze `refresh_market_runtime()` uzywal referencji do
  inventory sprzed normalizacji kolejki. Naprawiono to przez ponowne pobranie
  aktualnego `profile.files` po `queue_market_eligible_files(profile)` oraz
  zapis `listed_at` / `batch_id` po stabilnych `id` plikow.
* Smoke nadal moze wymagac ponownego uruchomienia w dzialajacej sesji procesu,
  jesli lokalny PowerShell zwroci blad `python.exe` znany ze Sprintow 35-36.

### Zmienione pliki

* `run.py`
* `tests/test_target_persistence.py`
* `tools/smoke_admin_inventory.py`
* `doc/file_model.md`
* `doc/data_economy.md`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testow

* `python -m unittest tests.test_target_persistence.TargetPersistenceHelpersTest.test_queue_market_eligible_files_preserves_listed_batch tests.test_target_persistence.TargetPersistenceHelpersTest.test_market_runtime_does_not_sell_before_sector_threshold tests.test_target_persistence.TargetPersistenceHelpersTest.test_market_runtime_lists_batch_and_waits_for_dwell_time tests.test_target_persistence.TargetPersistenceHelpersTest.test_market_runtime_settles_batch_after_dwell_once` - OK.
* `python -m py_compile run.py database.py profileManagment.py tools/smoke_admin_inventory.py` - OK.
* `python -m unittest tests.test_target_persistence` - 95 testow OK.
* `git diff --check` - OK.
* `python tools/smoke_admin_inventory.py --no-seed --no-sale` - nie wystartowal
  z powodu bledu srodowiska procesu `python.exe`: `Okreslona sesja logowania nie
  istnieje`.

### Status

Sprint 37 jest zaimplementowany kodowo i przeszedl testy regresyjne. Gameplay
smoke wymaga ponownego uruchomienia w dzialajacej sesji procesu.
---

## 03.07.2026

### Sprint

Sprint 38 - Ghost Exchange Dashboard v1.

### Cel

Zastapic glowny widok Ghost Exchange lista pojedynczych plikow dashboardem
sektorowego rynku danych, bez nowego endpointu, bez drugiego rynku i bez
liczenia settlementu w JavaScript.

### Co zostalo wykonane

* Rozszerzono `GET /api/ghost-exchange` o payload:
  * `summary`,
  * `sectors`,
  * `recent_transactions`,
  * `history_7d`,
  * aktualny `balance`.
* Dodano backendowy read model dashboardu oparty o:
  * `profile.files`,
  * `market_status`,
  * `market_sector`,
  * `files.market`,
  * `profile.market_history`.
* `renderExchange()` w `static/js/terminal.js` renderuje teraz dashboard na
  klasach `gx-*`:
  * `gx-dashboard`,
  * `gx-sector-grid`,
  * `gx-summary-grid`,
  * `gx-main-row`,
  * `gx-transactions-panel`,
  * `gx-chart-panel`.
* Głowny widok Ghost Exchange nie renderuje juz `Preview sale` ani `Sprzedaj`.
* Dodano lekkie inline SVG sparkline na kartach sektorow i fallback SVG dla
  historii 7 dni.
* Podlaczono `static/css/ghost_exchange_charts.css` przez import w `style.css`.
* Dodano testy kontraktu API, frontendowego renderera i responsywnego CSS.

### Najwazniejsze decyzje

* JavaScript nie zna progow rynku i nie liczy settlementu. Renderuje tylko read
  model z backendu.
* Legacy `preview` i `sell` endpointy zostaja w backendzie jako kompatybilnosc,
  ale nie sa glownym flow UI.
* File Manager pozostaje miejscem podgladu lootow.
* Sprint 38 nie dodaje storage upgrade i nie rozpoczyna Sprintu 39.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `static/css/ghost_exchange_charts.css`
* `tests/test_target_persistence.py`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py tests/test_target_persistence.py` - OK.
* `node --check static/js/terminal.js` - OK.
* Testy jednostkowe Sprintu 38 - OK.
* `python -m py_compile run.py database.py profileManagment.py tools/smoke_admin_inventory.py` - OK.
* `python -m unittest tests.test_target_persistence` - 99 testow OK.
* `git diff --check` - OK; Git pokazal tylko ostrzezenie CRLF/LF dla
  `static/css/style.css`.
* `python tools/smoke_admin_inventory.py --no-seed --no-sale` - nie wystartowal
  z powodu bledu srodowiska procesu `python.exe`: `Okreslona sesja logowania nie
  istnieje`.

### Status

Sprint 38 jest zaimplementowany kodowo i przeszedl testy regresyjne. Gameplay
smoke wymaga ponownego uruchomienia w dzialajacej sesji procesu.

---

## 03.07.2026

### Sprint

Sprint 39 - Storage Economy + Market Migration + Balance.

### Cel

Domknac Faze D przez wlaczenie storage jako realnego ograniczenia zapisu danych,
dodanie produktow Storage Upgrade do istniejacego Googleplexa i zachowanie
automatycznego rynku danych bez tworzenia drugiego marketu, storage engine ani
sklepu.

### Co zostalo wykonane

* Dodano wspolny helper `append_runtime_file_if_space(profile, operation, folder,
  file_entry)`.
* Wszystkie finalizery tworzace runtime data files zapisują pliki przez storage
  gate zamiast bezposredniego `files[folder].append(...)`.
* Przy braku miejsca plik nie trafia do `/data/*`, operacja dostaje wynik
  `storage_full` / `dropped_no_space`, a gracz dostaje system message:
  `Brak miejsca na zapis danych.`.
* Brak miejsca jest idempotentny: ten sam odrzucony plik nie spamuje wiadomościami
  przy kolejnym refreshu.
* Dodano seed produkty Googleplexa typu `storage_upgrade`:
  * `Ghost Vault Basic`,
  * `Ghost Vault Plus`,
  * `Data Vault`,
  * `BlackVault`,
  * `Encrypted Cluster`.
* `/install-app` obsluguje storage products w istniejacym flow zakupu:
  * odejmuje HC,
  * zwieksza `storage_capacity`,
  * zapisuje `storage_upgrades`,
  * nie dodaje produktu do `profile.apps`,
  * nie dodaje produktu do `files.tools`.
* Smoke admin inventory pokazuje aktualny storage i dostepne storage products.

### Najwazniejsze decyzje

* Storage Upgrade jest produktem Googleplexa, nie aplikacja i nie tool.
* Storage Gate jest wspolnym helperem dla finalizerow, a nie osobnym storage
  engine.
* Dane niezapisane przez brak miejsca nie trafiaja do market queue.
* Auto-sale ze Sprintu 37 pozostaje odpowiedzialne za zwalnianie storage po
  sprzedazy paczki.

### Zmienione pliki

* `run.py`
* `tests/test_target_persistence.py`
* `tools/smoke_admin_inventory.py`
* `doc/file_model.md`
* `doc/data_economy.md`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testow

* `python -m py_compile run.py database.py profileManagment.py` - OK.
* `python -m unittest tests.test_target_persistence` - 103 testy OK.
* `node --check static/js/terminal.js` - OK.
* Smoke wymaga uruchomienia po lokalnym sprawdzeniu srodowiska procesu, jesli
  PowerShell zwroci znany blad `python.exe` z poprzednich sprintow.

### Status

Sprint 39 jest zaimplementowany kodowo. Faza D jest domknieta na poziomie
Storage Economy, Googleplex storage products i market/storage lifecycle.

---

## 03.07.2026

### Sprint

Sprint 39.1 - Googleplex Product Effects Runtime v1.

### Cel

Rozszerzyc istniejacy Googleplex o produkty zmieniajace parametry profilu bez
tworzenia drugiego sklepu, osobnego inventory, osobnego storage ani nowej
ekonomii.

### Co zostalo wykonane

* Dodano centralny katalog `TRAVEL_CITIES`.
* Dodano wspolny router efektow `apply_googleplex_product_effect(profile,
  product)`.
* Produkty Googleplexa korzystaja z pol:
  * `product_type`,
  * `effects`,
  * `category`,
  * `consumable`,
  * `required_level`,
  * `required_respect`.
* Storage Upgrade ze Sprintu 39 zostal podlaczony pod wspolny runtime efektow.
* Dodano produkty v1:
  * storage / HDD,
  * travel tickets,
  * map zoom bonus,
  * scan range bonus,
  * bike range bonus.
* Travel Ticket trzyma tylko `travel_city`; wspolrzedne pochodza z katalogu
  miast.
* `/install-app` obsluguje produkty przez ten sam flow platnosci HC, ale nie
  dodaje produktow do `profile.apps` ani `files.tools`.
* Googleplex UI pokazuje produkty jako produkty systemowe, z przyciskiem `Kup`
  i opisem efektow.

### Najwazniejsze decyzje

* Nie powstal nowy sklep ani inventory itemow.
* Produkty nieaplikacyjne sa historia zakupu i efektem profilu, nie narzedziem
  runtime.
* Warszawa jest dostepna jako tani bilet powrotu do miasta startowego.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `tests/test_target_persistence.py`
* `doc/data_economy.md`
* `doc/file_model.md`
* `doc/gameplay_matrix.md`
* `doc/project_journal.md`

### Wynik testow

* Testy punktowe produktow Googleplex - OK.

### Status

Sprint 39.1 jest zaimplementowany kodowo i czeka na pelna walidacje regresyjna.

---

## 03.07.2026

### Sprint

Hotfix - territory encirclement / map profile regression.

### Cel

Zdiagnozowac regresje profilu i mapy po mechanice otoczenia pola: znikajace
terytorium wlasciciela, ryzyko blokowania payloadu mapy przez uszkodzony rekord
oraz spam komunikatow `Pole zostalo otoczone`.

### Co zostalo wykonane

* Dodano defensywna normalizacje area payloadu:
  * `normalize_player_area(area)`,
  * `safe_player_areas(areas)`.
* `/api/map/player-areas` pomija pojedyncze uszkodzone pola, ale nadal zwraca
  poprawne pozostale terytoria.
* Wlasciciel widzi swoje pole takze w statusie `encircled`.
* Alert otoczenia pola nie opiera sie juz na nietrwalej wartosci `area_id`.
* Alert `area_encircled` dostaje stabilny `area_key` wyliczony z ownera i
  geometrii pola.
* `TerritoryStore` dostal read-only helper
  `area_event_exists_with_payload_key(...)`.
* Dodano read-only skrypt diagnostyczny `tools/diagnose_territory_state.py` do
  sprawdzania produkcyjnych profili/terytoriow bez modyfikowania danych.

### Przyczyna

`rebuild_player_areas()` kasuje i tworzy rekordy `player_areas` od nowa. Dla
pola otoczonego zmienial sie `area_id`, a idempotencja alertu uzywala wlasnie
`area_id`. Ten sam obszar mogl wiec wygladac jak nowe zdarzenie po rebuildzie,
co powodowalo spam komunikatu.

Drugi problem byl defensywny: endpoint mapy budowal payload z `player_areas`
bez izolowania uszkodzonego wpisu. Pojedyncze puste/niepelne pole moglo
zaburzyc render albo profil.

### Zmienione pliki

* `run.py`
* `database.py`
* `tests/test_target_persistence.py`
* `tools/diagnose_territory_state.py`
* `doc/project_journal.md`

### Wynik testow

* Test regresyjny uszkodzonego area + encircled owner area - OK.
* Test regresyjny idempotencji alertu `area_encircled` po zmianie `area_id` -
  OK.
* `python -m unittest tests.test_target_persistence` - 108 testow OK.
* `python -m unittest tests.test_app_catalog_cleanup` - 4 testy OK.
* `node --check static/js/terminal.js` - OK.

### Status

Hotfix jest gotowy kodowo. Do analizy produkcyjnej mozna uruchomic read-only:

```text
python tools/diagnose_territory_state.py --username <login>
```

---

## 04.07.2026

### Sprint

Faza E - Messenger / Skrzynka mailowa, plan Sprintow 40-44.

### Cel

Rozpisac nowa serie sprintow dla przebudowy Skrzynki mailowej w komunikator
CHAOS, bez tworzenia drugiego backendu wiadomosci, drugiego contact flow ani
osobnego systemu powiadomien.

### Co zostalo wykonane

* Dodano do `doc/game_play_260626.md` nowa Faze E.
* Rozpisano Sprint 40 - Mailbox Architecture Audit + UX Contract.
* Rozpisano Sprint 41 - Messenger Layout v1.
* Rozpisano Sprint 42 - Conversation List Polish + Thread States.
* Rozpisano Sprint 43 - Chat View Polish + Composer UX.
* Rozpisano Sprint 44 - Messenger Integration + Notification Hygiene.
* Dopisano finalna architekture Fazy E:
  * `mail_store`,
  * `/api/mail/bootstrap`,
  * `/api/chats/messages`,
  * `/api/contacts`,
  * `system_messages`,
  * `openEmailChatWith()`.

### Najwazniejsze decyzje

* Skrzynka mailowa jest jedynym messengerem gracza.
* Mobile/narrow to zmiana prezentacji: lista rozmow -> czat -> lista.
* `mailMobileView` jest stanem UI, nie gameplayu.
* Backend wiadomosci pozostaje zrodlem prawdy.
* Nie powstaje drugi inbox, drugi system kontaktow ani drugi system notyfikacji.

### Zmienione pliki

* `doc/game_play_260626.md`
* `doc/project_journal.md`

### Status

Plan Fazy E jest gotowy do implementacji sprint po sprincie.

---

## 04.07.2026

### Sprint

Faza E - decyzja namingowa Cyberner.

### Cel

Ustalic filozofie nazwy komunikatora CHAOS i odejsc od widocznej nazwy
Email/Skrzynka mailowa na rzecz nazwy Cyberner.

### Co zostalo wykonane

* Dodano dokument `doc/cyberner.md`.
* Opisano inspiracje neologizmem Stanislawa Lema z Cyberiady.
* Zaadaptowano Cybernera jako komunikator Ghost Systemu:
  * nie zwykla poczte,
  * nie tylko czat,
  * nerw komunikacyjny swiata gry.
* Zaktualizowano Faze E w `doc/game_play_260626.md`.
* Ustalono, ze techniczne identyfikatory legacy moga zostac, jesli zmiana app-id
  bylaby ryzykowna, ale widoczna nazwa UI przechodzi na Cyberner.

### Najwazniejsze decyzje

* Email / Skrzynka mailowa zmienia nazwe uzytkowa na Cyberner.
* Cyberner jest warstwa swiata, UX i dokumentacji.
* Backend mailowy pozostaje zrodlem prawdy.
* Implementacja nazwy w UI ma nastepowac stopniowo, bez lamania legacy runtime.

### Zmienione pliki

* `doc/cyberner.md`
* `doc/game_play_260626.md`
* `doc/project_journal.md`

### Status

Decyzja namingowa jest udokumentowana i gotowa do wdrozenia w UI Sprintow Fazy E.

---

## 04.07.2026

### Sprint

Sprint 41 - Cyberner Layout v1.

### Cel

Przebudowac istniejaca aplikacje Email/Skrzynka mailowa wizualnie w Cybernera:
komunikator swiata CHAOS, bez zmian backendu wiadomosci, endpointow, modelu
danych, kontaktow ani profilu gracza.

### Co zostalo wykonane

* Podpieto `static/css/mobile_messenger.css` w szablonach desktopu.
* Zmieniono widoczna nazwe launchera i okienka z Email/Skrzynka mailowa na
  `Cyberner`.
* Przebudowano markup `createEmailClient()` pod klasy messengerowe:
  `mail-app`, `mail-sidebar`, `mail-conversation-list`, `mail-chat`,
  `mail-chat-header`, `mail-messages`, `mail-message`, `mail-composer`.
* Dodano stan UI `mailMobileView` oraz `data-mobile-view="list/chat"` na
  kontenerze `.mail-app`.
* Desktop zachowuje uklad dwupanelowy: lista rozmow + czat.
* Mobile/narrow przechodzi w model komunikatora: lista rozmow -> czat -> lista.
* Dodano przycisk powrotu w naglowku czatu.
* `openEmailChatWith(peer)` nadal korzysta z istniejacego flow i otwiera czat
  bez tworzenia drugiego inboxa.
* Globalny `# grupa` zostal opisany w UI jako globalny czat online graczy.

### Najwazniejsze decyzje

* Techniczne identyfikatory `email/mail` zostaja jako legacy runtime.
* Cyberner jest widoczna nazwa UI i warstwa klimatu.
* `mailMobileView` jest stanem prezentacji, nie stanem gameplayu.
* Sprint 41 nie implementuje jeszcze realnych avatarow, pelnych unread countow,
  online/offline logic ani nowych typow wiadomosci.

### Problemy

Brak blokera. Manualna walidacja desktop/mobile pozostaje wymagana w
przegladarce, bo sprint dotyczy ukladu okna.

### Zmienione pliki

* `static/js/terminal.js`
* `static/css/mobile_messenger.css`
* `templates/index.html`
* `templates/linux.html`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK, tylko ostrzezenia Git o przyszlej normalizacji CRLF
  w szablonach HTML.

### Status

Sprint 41 jest gotowy do walidacji.

### Nastepny sprint

Sprint 42 - Conversation List Polish + Thread States.

---

## 04.07.2026

### Sprint

Sprint 42 - Conversation List Polish + Thread States.

### Cel

Uporzadkowac liste rozmow Cybernera tak, zeby wygladala jak centrum
komunikacji swiata gry, a nie techniczna lista kontaktow, bez zmian backendu
wiadomosci, endpointow i modelu danych.

### Co zostalo wykonane

* Uporzadkowano rendering glownego kanalu `# grupa`, kontaktow i watkow
  oczekujacych.
* `# grupa` zostala oznaczona jako globalny/publiczny kanal online graczy.
* Kazdy item rozmowy dostal strukture pod:
  * avatar/symbol,
  * nazwe,
  * preview/fallback,
  * status,
  * unread badge,
  * aktywny stan.
* Dodano defensywne fallbacki UI:
  * `Czat indywidualny` dla kontaktow bez preview,
  * `Oczekuje na kontakt` dla pending threads,
  * `Publiczny kanal online graczy` dla globalnego kanalu bez ostatniej
    wiadomosci.
* Przygotowano klasy stanu:
  * `is-friend`,
  * `is-stranger`,
  * `is-system`,
  * `is-pending`,
  * `mail-status-pending`.
* Unread badge zostal przeniesiony do stalego miejsca w itemie i nie powinien
  rozpychac listy.
* Aktywna rozmowa pozostaje aktywna po `refreshThreads()`, a `mailMobileView`
  nie jest resetowany przez odswiezenie listy.

### Najwazniejsze decyzje

* Nie dodano endpointow ani nowych pol do backendu.
* Klasy `is-friend` / `is-stranger` sa uzywane tylko wtedy, gdy obecny payload
  faktycznie dostarcza taka informacje albo gdy watek jest pending.
* Preview jest warstwa prezentacji, nie nowym modelem danych.

### Problemy

Brak blokera. Pelna walidacja wizualna wymaga sprawdzenia w oknie desktop oraz
mobile/narrow.

### Zmienione pliki

* `static/js/terminal.js`
* `static/css/mobile_messenger.css`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK, tylko ostrzezenia Git o przyszlej normalizacji CRLF
  w szablonach HTML.

### Status

Sprint 42 jest gotowy do walidacji manualnej.

### Nastepny sprint

Sprint 43 - Chat View Polish + Composer UX.

---

## 04.07.2026

### Sprint

Sprint 43 - Chat View Polish + Composer UX.

### Cel

Dopolerowac widok czatu Cybernera: wiadomosci maja miec rytm komunikatora,
wlasne/systemowe wpisy osobny ton, composer ma zostac zawsze na dole, a
mobile/narrow ma pozostac wygodne.

### Co zostalo wykonane

* Uporzadkowano markup pojedynczej wiadomosci:
  * avatar/symbol nadawcy,
  * sender,
  * czas,
  * opcjonalny subject/highlight,
  * tresc.
* Utrzymano i rozwinieto klasy:
  * `mail-message`,
  * `mail-message-meta`,
  * `mail-message-body`,
  * `own` / `is-own`,
  * `system` / `is-system`,
  * `unknown`.
* Wiadomosci wlasne sa wyróżnione i ustawione po prawej.
* Wiadomosci systemowe dostaly osobny ton i avatar `SYS`.
* Dlugie wiadomosci zawijaja sie przez `overflow-wrap` / `word-break`, bez
  poziomego scrolla.
* Composer zostal dopasowany do dolnej krawedzi czatu i mobile/narrow:
  * stabilny grid,
  * kompaktowy przycisk,
  * input bez rozpychania okna.
* Scroll wiadomosci stal sie mniej agresywny:
  * jesli gracz jest na dole, nowe wiadomosci przewijaja do dolu,
  * jesli czyta starsze wpisy, refresh nie zrywa pozycji,
  * po wyslaniu wiadomosci aktywny czat przewija do dolu.
* Drobny cleanup po Sprincie 42:
  * status/unread listy rozmow przeniesiono do osobnego prawego slotu,
  * nazwa i preview maja ellipsis,
  * pending threads nie powinny rozpychac kart data/czasem.

### Najwazniejsze decyzje

* Nie zmieniono backendu, endpointow ani modelu wiadomosci.
* `unknown` jest tylko defensywna klasa UI dla nadawcow spoza znanych kontaktow.
* Scroll pozostaje frontendowym zachowaniem prezentacji, nie stanem gameplayu.

### Problemy

Brak blokera. Manualnie trzeba jeszcze obejrzec dlugie wiadomosci, wlasne
wiadomosci, system message i composer na mobile/narrow.

### Zmienione pliki

* `static/js/terminal.js`
* `static/css/mobile_messenger.css`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK, tylko ostrzezenia Git o przyszlej normalizacji CRLF
  w szablonach HTML.

### Status

Sprint 43 jest gotowy do walidacji manualnej.

### Nastepny sprint

Sprint 44 - Messenger Integration + Notification Hygiene.

---

## 04.07.2026

### Sprint

Sprint 44 - Cyberner Integration + World Communication.

### Cel

Domknac Faze E: Cyberner przestaje byc tylko aplikacja mailowa i staje sie
wspolna warstwa komunikacji swiata gry, nadal oparta o istniejace `mail_store`,
`system_messages`, endpointy mail/contact i `openEmailChatWith()`.

### Co zostalo wykonane

* Dodano `CYBERNER_ICON_LIBRARY` jako osobna biblioteke ikon komunikatora.
* Renderer Cybernera przestal korzystac z ikon wpisanych lokalnie w watkach i
  wiadomosciach.
* Dodano identyfikacje zrodel rozmow po obecnym payloadzie/nazwie:
  * `# grupa`,
  * gracze/kontakty,
  * pending request,
  * AI Central,
  * Ghost Exchange,
  * System,
  * Misje,
  * przyszle NPC/frakcje/Marketplace/BlackNet/dron/motocykl.
* Watki Ghost Exchange, System i AI Central sa traktowane jako zrodla swiata,
  a nie zwykle kontakty do akceptacji.
* Ukryty czat na mobile/narrow nie jest odswiezany przez `loadMessages()`,
  dzieki czemu refresh listy nie oznacza ukrytej rozmowy jako przeczytanej.
* Player actors nadal korzystaja z istniejacego `openEmailChatWith(peer)`.
* Sekcje listy rozmow przeszly z jezyka poczty na jezyk komunikatora:
  `Rozmowy` i `Nowe`.
* Zaktualizowano dokumentacje Fazy E i `doc/cyberner.md` o filozofie zrodel
  komunikacji.

### Najwazniejsze decyzje

* Nie powstal drugi backend wiadomosci.
* Nie powstal drugi inbox.
* Nie powstal drugi contact flow.
* Nie powstal drugi system powiadomien.
* Cyberner jest jedynym komunikatorem swiata gry; frontend nadaje rozmowom
  tozsamosc, ale backend pozostaje zrodlem prawdy.

### Problemy

Podczas walidacji jedna komenda `rg` zostala uruchomiona z blednym znakiem
przekierowania i wyzerowala `static/js/terminal.js`. Plik zostal natychmiast
przywrocony z `HEAD`, a zmiany Cybernera nalozono ponownie kontrolowanym
patchem. `node --check` potwierdzil poprawna skladnie po naprawie.

### Zmienione pliki

* `static/js/terminal.js`
* `doc/game_play_260626.md`
* `doc/cyberner.md`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK, tylko ostrzezenia Git o przyszlej normalizacji CRLF
  w plikach roboczych.

### Status

Sprint 44 zamyka Faze E od strony implementacyjnej i dokumentacyjnej.

### Nastepny sprint

Do decyzji: kolejne prace powinny traktowac Cybernera jako wspolny kanal
komunikacji systemow gry, nie jako osobna skrzynke mailowa.

---

## 04.07.2026

### Sprint

Plan Sprintow 45-47 - Cyberner Channels.

### Cel

Przygotowac kolejny etap Fazy E: Cyberner ma przejsc od komunikatora
watkow/kontaktow do kanalowej warstwy komunikacji swiata gry, nadal bez
drugiego `mail_store`, drugiego inboxa i drugiego contact flow.

### Co zostalo wykonane

* Dopisano Sprint 45 - Cyberner Channels Audit + UX Contract.
* Dopisano Sprint 46 - Cyberner Channels Runtime.
* Dopisano Sprint 47 - Cyberner Social Polish.
* Ustalono, ze docelowy kanal publiczny nie powinien nazywac sie `# grupa`,
  tylko `WORLD` z ikona z `CYBERNER_ICON_LIBRARY.world`.
* Dopisano znaczenie gameplayowe Sprintow 45-47: Cyberner rozpoczyna spoleczna
  galaz CHAOS i jest pierwszym systemem, ktory ma uzyc przynaleznosci klanowej
  w realnym runtime komunikacji.
* Ustalono rozroznienie:
  * kanal komunikacji,
  * prywatna rozmowa,
  * thread systemowy,
  * pending request.
* Dopisano zasade, ze lista Cybernera jest lista kanalow i rozmow, a nie lista
  folderow poczty.
* Dopisano zasade, ze kanaly `WORLD`, `ZNAJOMI`, `KLAN` i przyszle kanaly
  typu `WOJNA`, `FRAKCJA`, `OPERACJA`, `RAID` korzystaja z modelu
  `CYBERNER_ICON_LIBRARY + label`, bez ikon wpisywanych na sztywno w rendererze.

### Najwazniejsze decyzje

* Sprint 45 jest audytem i kontraktem UX, bez implementacji runtime kanalow.
* Sprint 46 moze dodac minimalne pole `channel` albo `source` tylko jesli audyt
  pokaze taka potrzebe.
* Kanal `KLAN` jest pierwszym krokiem multiplayera gameplayowego: klan przestaje
  byc tylko informacja w profilu i zaczyna wplywac na komunikacje swiata gry.
* Sprint 47 jest polish sprintem: avatary, online, typing, favorite, mute i
  animacje nie zmieniaja architektury wiadomosci.
* Wszystko nadal ma isc przez istniejace `mail_store`, `system_messages`,
  `/api/mail/bootstrap`, `/api/chats/messages` i `openEmailChatWith()`.

### Zmienione pliki

* `doc/game_play_260626.md`
* `doc/project_journal.md`

### Wynik testow

Nie uruchamiano testow runtime. Zmiana dotyczyla wylacznie dokumentacji
roadmapy.

### Status

Plan Sprintow 45-47 jest dopisany i gotowy jako nastepny etap prac nad
Cybernerem.

---

## 04.07.2026

### Sprint

Sprint 45 - Cyberner Channels Audit + UX Contract.

### Cel

Przygotowac architekture Cybernera pod kanaly komunikacyjne swiata gry bez
implementowania runtime kanalow, bez nowych endpointow i bez drugiego
`mail_store`.

### Co zostalo wykonane

* Przeprowadzono audyt `MailStore`, `chat_messages`, `contacts`,
  `/api/mail/bootstrap`, `/api/chats/messages` i `openEmailChatWith()`.
* Utworzono `doc/cyberner_channels_audit.md` jako kontrakt architektoniczny
  Sprintu 45.
* Zaktualizowano `doc/game_play_260626.md`:
  * docelowy kanal publiczny to `WORLD`, nie techniczne `GLOBAL`,
  * kanaly nie sa kontaktami,
  * ikony sa wybierane po `source` / `channel`, nie po nazwie rozmowy,
  * `WORLD`, `ZNAJOMI`, `KLAN` sa projektowane jako singletony.
* Zaktualizowano `doc/cyberner.md` o kanaly, singletony i znaczenie klanow.

### Wnioski audytu

* Obecny `scope = group`, `peer_name = global` wystarcza jako baza dla kanalu
  `WORLD`.
* Prywatne rozmowy i pending requests juz dzialaja przez `scope = direct`,
  `contacts` i `pending_threads`.
* System/Ghost Exchange/AI Central moga korzystac z obecnego direct flow, ale
  potrzebuja jawniejszego `source` w read modelu, zeby renderer nie zgadywal po
  nazwie.
* `ZNAJOMI` i `KLAN` nie powinny byc kontaktami. Jesli beda aktywne w Sprincie
  46, potrzebuja minimalnego `channel` / `source` jako singletonowy read/runtime
  model nad istniejacym `mail_store`.

### Najwazniejsze decyzje

* `source` opisuje typ zrodla i wybor ikony.
* `channel` opisuje singletonowy kanal komunikacji.
* Kanaly nie trafiaja do `contacts`.
* Sprint 46 nie powinien tworzyc `channel_store`.
* `KLAN` jest pierwszym krokiem multiplayera gameplayowego: przynaleznosc
  klanowa zaczyna miec znaczenie komunikacyjne.

### Zmienione pliki

* `doc/game_play_260626.md`
* `doc/cyberner.md`
* `doc/cyberner_channels_audit.md`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK.

### Status

Sprint 45 zakonczony jako audyt i kontrakt architektoniczny. Architektura jest
gotowa do implementacji Sprintu 46 bez drugiego systemu wiadomosci.

---

## 04.07.2026

### Sprint

Sprint 46 - Cyberner Channels Runtime.

### Cel

Dodac minimalny runtime kanalow Cybernera jako singletonowy read model nad
istniejacym `mail_store`, bez drugiego systemu wiadomosci, bez `channel_store`
i bez zapisywania kanalow jako kontaktow.

### Co zostalo wykonane

* Rozszerzono `/api/mail/bootstrap` o pole `channels`.
* Dodano helper `build_cyberner_channels()` w `run.py`.
* Dodano klucze `world`, `friends`, `clan` do `CYBERNER_ICON_LIBRARY`.
* Zmieniono publiczny kanal UI z `# grupa` na `WORLD`.
* Dodano osobna sekcje kanalow nad prywatnymi rozmowami w Cybernerze.
* `WORLD` mapuje sie na istniejacy thread `scope = group`, `peer = global`.
* `ZNAJOMI` jest disabled placeholderem opartym o liczbe istniejacych kontaktow.
* `KLAN` jest disabled placeholderem widocznym tylko przy profilu z `clan`.
* Dodano style kanalow w `static/css/mobile_messenger.css`.
* Zaktualizowano dokumentacje Sprintu 46 i kontrakt audytu.

### Najwazniejsze decyzje

* `source` wybiera tozsamosc i ikone z `CYBERNER_ICON_LIBRARY`.
* `channel` identyfikuje singleton kanalu.
* Kanaly nie trafiaja do `contacts`.
* Disabled placeholder kanalu nie wywoluje `/api/chats/messages`, nie tworzy
  pending request i nie zapisuje kontaktu.
* Backend zostal rozszerzony tylko o read model bootstrapu.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/mobile_messenger.css`
* `doc/game_play_260626.md`
* `doc/cyberner.md`
* `doc/cyberner_channels_audit.md`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `python -m py_compile run.py` - OK.
* `git diff --check` - OK.

### Status

Sprint 46 zakonczony. Cyberner ma minimalny runtime kanalow `WORLD`, `ZNAJOMI`
i `KLAN` bez drugiego systemu wiadomosci. Sprint 47 moze zajac sie social
polishem.

---

## 04.07.2026

### Sprint

Sprint 47 - Cyberner Social Polish.

### Cel

Dopolerowac Cybernera jako spoleczne centrum gry po dodaniu kanalow, bez zmiany
architektury wiadomosci i bez udawania funkcji, ktorych backend jeszcze nie
obsluguje.

### Co zostalo wykonane

* Dopolerowano liste rozmow i kanalow w `static/css/mobile_messenger.css`.
* Dodano wizualne rozroznienie:
  * kanal,
  * placeholder,
  * prywatne,
  * nowe,
  * zrodlo.
* Wzmocniono aktywny stan rozmowy i kanalow.
* Poprawiono hover/focus, unread badges, status dots i ellipsis dla dlugich
  nazw oraz preview.
* Disabled kanaly `ZNAJOMI` i `KLAN` pozostaja nieaktywne i nie uruchamiaja
  runtime wiadomosci.
* Mobile/narrow zachowuje model lista -> czat -> lista.
* Zaktualizowano dokumentacje o zasade: placeholder nie jest aktywna funkcja.

### Najwazniejsze decyzje

* Nie dodano aktywnego `typing`, `last seen`, `pin`, `favorite` ani `mute`,
  poniewaz nie maja jeszcze backendowego zrodla prawdy.
* Polish dotyczy tylko prezentacji istniejacych stanow.
* Backend i endpointy pozostaly nietkniete w tym sprincie.

### Zmienione pliki

* `static/js/terminal.js`
* `static/css/mobile_messenger.css`
* `doc/game_play_260626.md`
* `doc/cyberner.md`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK.

### Status

Sprint 47 zakonczony. Cyberner ma domkniety polish spoleczny po kanalach
`WORLD`, `ZNAJOMI` i `KLAN`.

---

## 04.07.2026

### Sprint

Sprint 48 - Cyberner Active Social Channels.

### Cel

Aktywowac kanaly `ZNAJOMI` i `KLAN` jako realne kanaly Cybernera bez drugiego
messengera, drugiego inboxa, `channel_store` ani drugiego contact flow.

### Co zostalo wykonane

* Rozszerzono `MailStore` o obsluge `scope = channel`.
* Dodano unread counts dla kanalow po `peer_name`.
* `ZNAJOMI` dziala jako singleton `scope = channel`, `peer = friends`.
* `KLAN` dziala jako singleton `scope = channel`, `peer = clan:<clan_name>`,
  jesli profil ma klan.
* Wiadomosci `ZNAJOMI` sa rozsyłane do zaakceptowanych kontaktow.
* Wiadomosci `KLAN` sa rozsyłane do profili z tym samym klanem.
* Kanaly nie trafiaja do `contacts` i nie tworza pending request.
* Frontend liczy unread kanalow osobno od `WORLD` i rozmow prywatnych.

### Najwazniejsze decyzje

* `WORLD` pozostaje kompatybilnie `scope = group`, `peer = global`.
* `source` nadal wybiera ikone i tozsamosc zrodla.
* `channel` nadal identyfikuje singleton kanalu.
* Brak klanu oznacza brak aktywnego kanalu `KLAN` w read modelu.

### Zmienione pliki

* `database.py`
* `run.py`
* `static/js/terminal.js`
* `doc/game_play_260626.md`
* `doc/cyberner.md`
* `doc/cyberner_channels_audit.md`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `python -m py_compile run.py database.py profileManagment.py` - OK.
* `git diff --check` - OK.
* `python -m unittest tests.test_target_persistence` - FAIL na dwoch testach
  map payload:
  * `test_map_embeds_profile_as_json_literal`,
  * `test_map_embeds_large_profile_payload_as_json_literal`.

### Status

Sprint 48 zaimplementowany. Walidacja funkcjonalna Cybernera jest gotowa do
manualnego smoke, ale pelna suite `tests.test_target_persistence` wymaga osobnej
naprawy `/map` JSON payload poza zakresem Sprintu 48.

---

## 04.07.2026

### Sprint

Sprint 49 - Cyberner Notification Bridge.

### Cel

Polaczyc nowe wiadomosci Cybernera z istniejacym `system_messages`, tak aby
toast byl tylko sygnalem, a pelna rozmowa pozostawala w Cybernerze.

### Co zostalo wykonane

* Dodano backendowy most `mail_store -> system_messages` dla nowych wiadomosci
  Cybernera.
* Dodano `notification_type = cyberner` oraz minimalny payload `source/scope/peer`.
* Dodano frontendowa `CYBERNER_NOTIFICATION_LIBRARY`.
* Rozszerzono renderer toastow o cybernerowy wariant bez tworzenia drugiego
  toast systemu.
* Klik toasta otwiera Cybernera na odpowiednim threadzie.
* Toast nie pokazuje sie, jesli ten thread jest aktualnie otwarty.
* Kanaly `WORLD`, `ZNAJOMI` i `KLAN` korzystaja z tego samego mostu.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/style.css`
* `doc/game_play_260626.md`
* `doc/cyberner.md`
* `doc/project_journal.md`

### Wynik testow

* `node --check static/js/terminal.js` - OK.
* `python -m py_compile run.py database.py profileManagment.py` - OK.
* `git diff --check` - OK.
* `python -m unittest tests.test_target_persistence` - FAIL na znanych testach
  `/map` JSON payload:
  * `test_map_embeds_profile_as_json_literal`,
  * `test_map_embeds_large_profile_payload_as_json_literal`.

### Status

Sprint 49 zaimplementowany. Pelna suite `tests.test_target_persistence` nadal
wymaga osobnej naprawy `/map` JSON payload poza zakresem Cybernera.

---

## 04.07.2026

### Sprint

Sprint 50 - Runtime Stabilization Audit + Critical Fixes.

### Cel

Zatrzymac dokladanie nowych funkcji i ustabilizowac trzy krytyczne sciezki:
Ghost Exchange auto-sale, Googleplex product effects oraz Cyberner composer na
mobile.

### Przyczyny regresji

* Ghost Exchange: runtime dziala dwuetapowo (`queued/listed` -> dwell time ->
  `sold`), ale profil mogl zawierac batch juz zapisany w `market_history` jako
  sprzedany, podczas gdy jego pliki nadal lezaly w `profile.files`. Idempotencja
  slusznie blokowala drugie naliczenie HC, ale sektor zostawal wiecznie gotowy
  do sprzedazy i zajmowal storage.
* Googleplex products: starsze wpisy katalogu storage moga miec
  `storage_capacity_bonus` bez nowego pola `effects`. Runtime efektow wymagal
  listy `effects`, wiec taki legacy product mogl nie zwiekszac
  `storage_capacity`.
* Cyberner: composer nie mial centralnego stanu aktywnosci. Przycisk `Wyslij`
  mogl pozostac aktywny dla pustego inputu albo w trakcie wysylania, a mobile
  nie uwzglednial klawiatury ekranowej przez `visualViewport`.

### Co zostalo wykonane

* Potwierdzono, ze `GET /api/ghost-exchange` wywoluje runtime rynku i dodano
  regresje endpointowa: listed batch po dwell time sprzedaje sie raz, HC rosnie
  raz, a drugi refresh nie dubluje sprzedazy.
* Dodano recovery dla osieroconych plikow batcha, ktory jest juz rozliczony w
  `market_history` albo `files.market`: runtime usuwa tylko pliki nalezace do
  tego batcha, przelicza storage i nie nalicza HC drugi raz.
* Dodano fallback `storage_capacity_bonus -> effects` dla legacy storage
  products w `apply_googleplex_product_effect`.
* Potwierdzono testami produkty Googleplexa:
  * storage upgrade zwieksza `storage_capacity`,
  * legacy storage upgrade bez `effects` zwieksza `storage_capacity`,
  * travel ticket zmienia pozycje na miasto z katalogu,
  * map zoom, scan range i bike range dopisuja bonusy,
  * HC spada zgodnie z cena produktow.
* Cyberner composer blokuje wysylanie, gdy:
  * brak aktywnego threadu,
  * kanal jest disabled,
  * input jest pusty,
  * request wysylania jest w toku.
* Dodano minimalny `visualViewport` offset dla narrow/mobile, aby composer nie
  wpadal pod klawiature ekranowa.

### Zmienione pliki

* `run.py`
* `static/js/terminal.js`
* `static/css/mobile_messenger.css`
* `tests/test_target_persistence.py`
* `doc/project_journal.md`

### Wynik testow

* Punktowe testy Ghost Exchange runtime - OK.
* Punktowe testy Googleplex product effects - OK.
* `node --check static/js/terminal.js` - OK.
* `python -m py_compile run.py database.py profileManagment.py tools/smoke_admin_inventory.py` - OK.
* `python -m unittest tests.test_app_catalog_cleanup` - OK.
* `python tools/smoke_admin_inventory.py --no-seed --no-sale` - OK; Ghost
  Exchange wyczyscil osierocony sprzedany batch bez recznego sell.
* `git diff --check` - OK.
* `python -m unittest tests.test_target_persistence` - FAIL na znanych testach
  `/map` JSON payload:
  * `test_map_embeds_profile_as_json_literal`,
  * `test_map_embeds_large_profile_payload_as_json_literal`.

### Status

Sprint 50 zakonczony w zakresie runtime stabilization. Znany problem `/map` JSON
payload pozostaje osobnym dlugiem technicznym poza zakresem tej stabilizacji.

---

## 04.07.2026

### Hotfix

Ghost Exchange - backlog danych sieciowych po Storage Gate.

### Przyczyna

Profil produkcyjny mial wiele plikow `/data/network` w stanie legacy
`market_status: not_listed`. Pliki byly sprzedawalne i przekraczaly prog sektora,
ale nigdy nie dostaly `queued_at`, `listed_at` ani `batch_id`.

Runtime potrafil je wystawic, ale przy pierwszym listingu nadawal paczce
`listed_at` z chwili wejscia do Ghost Exchange. Dla starych plikow backlogu
oznaczalo to sztuczne rozpoczecie zegara rynku dopiero teraz, mimo ze pliki
powstaly w operacjach wiele minut albo godzin wczesniej.

### Poprawka

Dodano wybor najstarszego sensownego czasu z `listed_at`, `queued_at` albo
`created_at` paczki. Jesli timestamp nie jest z przyszlosci, runtime uzywa go
jako czasu wejscia paczki na rynek. Swieze pliki nadal czekaja normalny dwell
time, a stare backlogowe paczki moga zostac rozliczone przy pierwszym refreshu
Ghost Exchange.

### Walidacja

* Dodano diagnostyczny skrypt dry-run `tools/diagnose_ghost_exchange_network.py`.
* Dodano regresje API dla starego backlogu `network/not_listed`.
* Dodano regresje API dla normalnej sciezki `not_listed -> listed -> sold`.
* Punktowe testy Ghost Exchange network - OK.

---

## 05.07.2026

### Hotfix

Ghost Exchange - orphan files, storage cleanup i odrastanie sprzedanych plikow.

### Kontekst

Po uruchomieniu automatycznego rynku danych Ghost Exchange sprzedawal paczki i
naliczal HC, ale czesc plikow pozostawala widoczna w File Managerze w katalogach
`/gps`, `/device` i `/camera`. Powodowalo to trzy mylace objawy:

* dysk pozostawal zapchany mimo wpisow sprzedazy w `market_history`,
* Ghost Exchange pokazywal brak nowych pending danych, bo pliki byly juz
  rozliczone,
* File Manager nadal pokazywal stare looty jako `not_listed / sellable: tak`.

### Ustalenia

Diagnostyka `tools/diagnose_ghost_exchange_network.py main --sector all`
pokazala, ze pliki w katalogach danych mialy `id` obecne juz w
`market_history.file_ids` sprzedanych batchy:

* `camera`: 18 plikow / 252 MB,
* `device`: 15 plikow / 195 MB,
* `gps`: 5 plikow / 55 MB.

Byly to wiec orphan files po sprzedanych paczkach, a nie nowe dane oczekujace na
sprzedaz. Runtime poprawnie blokowal drugie naliczenie HC, ale storage nadal
liczyl pozostawione pliki.

Po pierwszym cleanupie wyszlo drugie zjawisko: stare zakonczone operacje
potrafily odtworzyc te same pliki ponownie. Finalizery generuja pliki
deterministycznie, a wspolny helper zapisu nie sprawdzal jeszcze, czy dany
`file_id` byl juz sprzedany.

### Poprawka

* Dodano skrypt `tools/repair_ghost_exchange_orphans.py`.
* Skrypt dziala domyslnie jako dry-run.
* Tryb `--apply`:
  * robi backup profilu do `data/backups`,
  * usuwa tylko pliki, ktorych `id` jest juz w `market_history` albo
    `files.market`,
  * przelicza `storage_used`,
  * nie nalicza HC,
  * nie dodaje nowych transakcji,
  * nie usuwa nowych/pending danych.
* Dodano helper `sold_market_file_ids(profile)`.
* `append_runtime_file_if_space()` blokuje teraz ponowny zapis pliku, ktory
  zostal juz sprzedany przez Ghost Exchange.
* Taki przypadek zwraca kontrolowany wynik `already_sold`, nie zapisuje pliku i
  nie zwieksza storage.

### Wynik produkcyjnego cleanupu profilu `main`

Dry-run wykryl:

```text
storage_before: 768 / 768 MB
orphan_files: 38
orphan_mb: 502
```

Po `--apply`:

```text
removed_files: 38
storage_after: 266 / 768 MB
backup: data/backups/ghost_exchange_orphans_main_20260705_073932.json
```

Po dodaniu blokady `already_sold` finalizery przestaly odtwarzac sprzedane
pliki. Kolejny smoke pokazal, ze:

* File Manager i Ghost Exchange znowu pokazuja ten sam stan danych,
* nowe dane trafiaja do File Managera,
* GX widzi je w odpowiednim sektorze jako pending,
* po osiagnieciu progu i dwell time batch sprzedaje sie,
* `storage_used` spada po cleanupie/sprzedazy,
* HC rosnie tylko przy realnej nowej sprzedazy.

### Zasada runtime po hotfixie

File Manager jest miejscem podgladu lootow zapisanych w `profile.files`.

Ghost Exchange jest read/runtime modelem tych samych plikow:

```text
profile.files
↓
sellable + market_status
↓
sector payload Ghost Exchange
↓
batch sale
↓
market_history
↓
usuniecie plikow z /data/*
↓
storage_used recalculated
```

Jezeli plik jest juz w `market_history.file_ids`, nie moze zostac ponownie
zapisany przez finalizer i nie moze drugi raz naliczyc HC.

### Dodatkowe obserwacje

* Pliki w `/system` sa niesprzedawalne i nadal zajmuja storage.
* To wymaga osobnego, swiadomego narzedzia maintenance/cleanup kupowanego w
  Googleplexie, zamiast automatycznego usuwania danych systemowych.
* Otwarte okno File Managera moze trzymac stary snapshot profilu. Klikniecie
  ikony `Pliki` powinno odswiezyc okno i pobrac nowy `/api/profile`.

### Walidacja

* `python -m unittest` dla punktowych testow Ghost Exchange/orphan cleanup - OK.
* `python -m unittest` dla market/storage/queue - OK.
* `python -m py_compile run.py database.py profileManagment.py
  tools/repair_ghost_exchange_orphans.py
  tools/diagnose_ghost_exchange_network.py` - OK.
* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK.

### Status

Ghost Exchange, File Manager i Storage Economy sa ponownie spojne dla danych
sprzedawalnych. Pozostaje zaplanowac osobny flow czyszczenia plikow
niesprzedawalnych, zwlaszcza `/system`.

---

## 05.07.2026

### Audyt

Ghost Exchange - pelna petla sektorow rynku danych.

### Cel

Upewnic sie, ze poprawka po orphan files nie dziala tylko dla ostatnich
przypadkow produkcyjnych (`network`, `gps`, `device`, `camera`), ale dla calej
petli rynku danych:

```text
profile.files
↓
storage_used
↓
queue_market_eligible_files()
↓
sector payload Ghost Exchange
↓
refresh_market_runtime()
↓
listed / dwell time
↓
sold
↓
files.market + market_history
↓
storage recalculated
```

### Sprawdzone sektory

Audyt i testy objely wszystkie sektory sprzedawalne Ghost Exchange:

* `camera`,
* `atm`,
* `gps`,
* `device`,
* `personal`,
* `credentials`,
* `financial`,
* `network`,
* `audio`,
* `vehicle`.

Katalog `system` pozostaje swiadomie poza Ghost Exchange, bo jego pliki sa
wewnetrznym stanem operacji (`internal_recon_state`) i maja `sellable: false`.
Nie powinny byc automatycznie sprzedawane. Ich czyszczenie wymaga osobnego,
swiadomego narzedzia maintenance.

### Ustalenia

* Wszystkie sprzedawalne katalogi danych maja mapowanie
  `file_category -> market_sector`.
* Wszystkie sektory maja prog sprzedazy w `MARKET_SECTOR_THRESHOLDS`.
* Wszystkie finalizery zapisujace dane przechodza przez wspolny helper
  `append_runtime_file_if_space()`.
* `queue_market_eligible_files()` konwertuje surowe pliki `not_listed` na
  `queued_for_market`, bez tworzenia osobnej kolejki.
* `build_ghost_exchange_sector_payload()` liczy tylko pliki
  `queued_for_market` i `listed`, wiec wejscie przez `GET /api/ghost-exchange`
  albo `refresh_market_runtime()` jest wymagane do synchronizacji File Managera
  z GX.
* `refresh_market_runtime()` potrafi sprzedac stary backlog `not_listed` po
  wszystkich sektorach, jesli prog sektora i dwell time sa spelnione.
* `append_runtime_file_if_space()` blokuje ponowne zapisanie sprzedanego
  `file_id` po wszystkich sektorach.

### Testy dodane

* `test_ghost_exchange_shows_raw_not_listed_pending_files_for_all_market_sectors`
  sprawdza, ze surowy plik widoczny w File Managerze jako `not_listed` zostaje
  po runtime refreshu pokazany w Ghost Exchange jako pending dla kazdego
  sektora.
* `test_append_runtime_file_skips_already_sold_files_for_all_market_sectors`
  sprawdza, ze deterministyczne finalizery nie odtworza juz sprzedanych plikow
  w zadnym katalogu danych.
* Istniejacy test
  `test_market_runtime_sells_old_not_listed_backlog_for_all_market_sectors`
  potwierdza sprzedaz batcha, zapis historii, wzrost HC i spadek storage dla
  kazdego sektora.

### Wynik

Petla Ghost Exchange jest pokryta testami dla wszystkich sprzedawalnych typow
plikow. Jesli plik jest `sellable: true`, ma poprawna kategorie i nie byl juz
sprzedany, GX powinien go zobaczyc, skolejkowac, pokazac w sektorze i sprzedac
po spelnieniu progu oraz dwell time.

### Walidacja

* Punktowe testy sektorowe Ghost Exchange - OK.
* `python -m py_compile run.py database.py profileManagment.py
  tools/repair_ghost_exchange_orphans.py
  tools/diagnose_ghost_exchange_network.py` - OK.
* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK.

Pelny `python -m unittest tests.test_target_persistence` ujawnia niezalezna
regresje w testach `/map` JSON payload (`test_map_embeds_profile_as_json_literal`
i `test_map_embeds_large_profile_payload_as_json_literal`). Nie dotyczy ona
Ghost Exchange i wymaga osobnego fixu map template/test matcher.

---

## 05.07.2026

### Plan

Faza F - Ghost Hack Radio / Audio Narrative Layer.

### Cel

Rozpisano kolejna mala faze sprintow po stabilizacji runtime: lokalny player MP3
oparty o kontrakt `meta.channel`, gotowy pod przyszle kanaly BlackNet bez
tworzenia backendu radia.

### Najwazniejsze decyzje

* Radio czyta jawny manifest `meta.channel`, a nie skanuje katalogow na slepo.
* Pierwszy kanal ma mieszkac w `static/mp3/radio/channel/ghost_streem_1/`.
* `RADIO_BASE_PATH = "/static/mp3/radio/channel"` i `DEFAULT_CHANNEL = "1"` sa
  fundamentem runtime.
* Autoplay jest lokalnym ustawieniem gracza w `localStorage`.
* Ghost Hack Radio nie jest Cybernerem, systemem misji ani drugim komunikatorem.
* BlackNet w przyszlosci ma dokladac kanaly przez `meta.channel + mp3`, bez
  przebudowy playera.

### Sprinty

* Sprint 51 - Ghost Hack Radio v0.1:
  * jeden kanal,
  * play/pause,
  * progress,
  * volume,
  * autoplay domyslnie ON z mozliwoscia wylaczenia,
  * loop po playliscie.
* Sprint 52 - Ghost Hack Radio Desktop App:
  * radio jako aplikacja desktopowa,
  * okno systemowe,
  * sterowanie playerem bez zatrzymywania audio po zamknieciu okna.
* Sprint 53 - Radio Channel Contract for Future BlackNet:
  * pierwszy kontrakt kanalow audio pod przyszly BlackNet,
  * bez zakladania, ze BlackNet istnieje juz fizycznie,
  * bez mieszania radia z Cybernerem i misjami.

### Zmienione pliki

* `doc/game_play_260626.md`,
* `doc/project_journal.md`.

### Status

Plan Fazy F jest gotowy do rozpoczecia Sprintu 51. Nie zaimplementowano jeszcze
runtime radia ani plikow MP3.

---

## 05.07.2026

### Sprint

Sprint 50 - Ghost Hack Radio Foundation.

### Cel

Przygotowac strukture plikow, kontrakt kanalu i miejsce aplikacji desktopowej
pod Ghost Hack Radio, bez implementacji playera audio.

### Co zostalo wykonane

* Dodano katalog pierwszego kanalu:
  `static/mp3/radio/channel/ghost_streem_1/`.
* Dodano kontrakt `meta.channel` ze `schema: 1`.
* Dodano lokalny `.gitignore`, zeby Sprint 50 nie wciagnal przypadkowo plikow
  `.mp3` do commita.
* Kontrakt zawiera pola:
  * `id`,
  * `name`,
  * `slug`,
  * `description`,
  * `autoplay`,
  * `loop`,
  * `tracks[]`.
* Dodano szkielet `static/js/ghost_radio.js`.
* Dodano szkielet `static/css/ghost_radio.css`.
* Dodano placeholder ikony `static/icons/ghost_hack_radio.svg`.
* Podpieto CSS i JS do szablonow desktopu.
* Dodano systemowa ikone desktopowa `Ghost Hack Radio`.
* Ikona otwiera tylko okno foundation/placeholder.

### Najwazniejsze decyzje

* `meta.channel` jest jedynym zrodlem prawdy playlisty.
* Aplikacja nie skanuje katalogu MP3.
* Sprint 50 nie uzywa `Audio`, nie odtwarza MP3 i nie implementuje kontrolek
  playera.
* Sprint 51 ma zaczac od gotowego kontraktu i skupic sie na runtime odtwarzania.

### Zmienione pliki

* `static/mp3/radio/channel/ghost_streem_1/meta.channel`,
* `static/mp3/radio/channel/ghost_streem_1/.gitignore`,
* `static/js/ghost_radio.js`,
* `static/css/ghost_radio.css`,
* `static/icons/ghost_hack_radio.svg`,
* `static/js/terminal.js`,
* `templates/index.html`,
* `templates/linux.html`,
* `templates/linux_old.html`,
* `doc/game_play_260626.md`,
* `doc/project_journal.md`.

### Status

Sprint 50 zakonczony jako foundation. Brak backendu i brak playera audio zgodnie
z zakresem.

---

## 05.07.2026

### Sprint

Sprint 51 - Ghost Hack Radio Player v0.1.

### Cel

Uruchomic pierwszy lokalny player MP3 oparty wylacznie o kontrakt
`meta.channel`.

### Co zostalo wykonane

* Zaimplementowano modul `GhostRadio` w `static/js/ghost_radio.js`.
* Publiczne API modulu:
  * `GhostRadio.init()`,
  * `GhostRadio.loadChannel(id)`,
  * `GhostRadio.play()`,
  * `GhostRadio.pause()`,
  * `GhostRadio.next()`,
  * `GhostRadio.previous()`.
* Player wczytuje:
  `static/mp3/radio/channel/{id}/meta.channel`.
* Playlista powstaje wylacznie z `tracks[]`.
* Sciezki MP3 sa budowane z katalogu kanalu i nazwy pliku z manifestu.
* Dodano HTML5 Audio API po stronie klienta.
* Dodano podstawowy UI:
  * nazwa kanalu,
  * aktualny utwor,
  * numer utworu,
  * liczba utworow,
  * Play,
  * Pause,
  * Next,
  * Previous,
  * pasek postepu.
* Po zakonczeniu utworu player przechodzi do nastepnego.
* Po ostatnim utworze wraca do pierwszego, jesli `loop = true`.
* `meta.channel` kanalu `ghost_streem_1` wskazuje istniejace lokalne pliki MP3.

### Poza zakresem

Nie dodano:

* wyboru kanalow,
* equalizera,
* Cybernera,
* BlackNet,
* streamingu,
* backendu,
* autoplay runtime.

### Zmienione pliki

* `static/js/ghost_radio.js`,
* `static/css/ghost_radio.css`,
* `static/mp3/radio/channel/ghost_streem_1/meta.channel`,
* `doc/project_journal.md`.

### Status

Sprint 51 zakonczony jako lokalny player v0.1. Radio dziala po stronie klienta i
jest gotowe pod przyszle kanaly BlackNet.

---

## 05.07.2026

### Sprint

Sprint 52 - Ghost Hack Radio Desktop App.

### Cel

Dodac Ghost Hack Radio jako pelnoprawna aplikacje desktopowa CHAOS, osadzajac
istniejacy modul `GhostRadio` w standardowym oknie systemowym.

### Co zostalo wykonane

* Rozszerzono aplikacje `Ghost Hack Radio` o pelny UI okna desktopowego.
* Player pokazuje:
  * nazwe kanalu,
  * aktualny utwor,
  * status sygnalu,
  * numer utworu,
  * czas odtwarzania,
  * pasek postepu,
  * Play / Pause,
  * Previous / Next,
  * Mute,
  * regulator glosnosci.
* Dodano prosty fake equalizer w stylistyce terminal/cyberpunk.
* `GhostRadio.init()` nie resetuje juz kanalu przy ponownym otwarciu okna, jesli
  radio ma juz zaladowany stan.
* Zamkniecie okna usuwa tylko UI. Obiekt `Audio` i stan `GhostRadio` zostaja w
  module, wiec muzyka moze dzialac w tle.
* Ponowne otwarcie okna podpina nowy DOM do istniejacego stanu playera.
* Dodano `GhostRadio.mute()` i `GhostRadio.setVolume(value)` jako kontrolki
  istniejacego odtwarzacza, bez tworzenia drugiej logiki audio.
* Dodano `ghost_hack_radio` do stalego zestawu ikon desktopu mobilnego.
* Start Menu korzysta z istniejacego `desktopApps`, wiec aplikacja pozostaje w
  tym samym systemie launcherow co reszta desktopu.

### Najwazniejsze decyzje

* Radio jest usluga dzialajaca w tle, a okno jest tylko kontrolerem UI.
* Nie dodano wyboru wielu kanalow, ustawien, autoplay, backendu ani BlackNet.
* Equalizer jest wylacznie wizualizacja, bez analizy dzwieku.
* Desktop i desktop mobilny korzystaja z istniejacego systemu ikon i okien.

### Zmienione pliki

* `static/js/ghost_radio.js`,
* `static/css/ghost_radio.css`,
* `static/js/terminal.js`,
* `doc/game_play_260626.md`,
* `doc/project_journal.md`.

### Wynik testow

* `node --check static/js/ghost_radio.js` - OK.
* `node --check static/js/terminal.js` - OK.
* `git diff --check` - OK; tylko ostrzezenia CRLF/LF dla istniejacych plikow
  roboczych.

### Status

Sprint 52 gotowy jako integracja desktopowa Ghost Hack Radio. Kolejne sprinty
moga rozwijac discovery kanalow, ustawienia albo BlackNet hooks bez przebudowy
modulu audio.

---

## 05.07.2026

### Sprint

Sprint 53 - Radio Channel Contract for Future BlackNet.

### Cel

Wyprowadzic pierwszy kontrakt kanalow Ghost Hack Radio pod przyszly BlackNet,
bez implementowania BlackNet, backendu, streamingu ani discovery kanalow.

### Co zostalo wykonane

* Dodano dokument `doc/radio_channel_contract.md`.
* Udokumentowano `meta.channel` jako jedyne zrodlo prawdy playlisty.
* Opisano strukture katalogu kanalu:
  `static/mp3/radio/channel/{channel_id}/meta.channel`.
* Opisano minimalny kontrakt `schema = 1`.
* Doprecyzowano wymagane pola:
  * `id`,
  * `name`,
  * `slug`,
  * `source`,
  * `tracks[]`.
* Doprecyzowano, ze `source = blacknet` jest wartoscia kontraktowa przyszlosci,
  a nie dowodem istnienia runtime BlackNet.
* Ustawiono `source: "ghost_radio"` w pierwszym kanale
  `ghost_streem_1/meta.channel`.
* Uzupelniono roadmape Sprintu 53 w `doc/game_play_260626.md`.

### Najwazniejsze decyzje

* Sprint 53 nie integruje z BlackNet, bo BlackNet jeszcze fizycznie nie istnieje.
* Przyszly BlackNet ma dokladac kanaly przez `meta.channel + pliki audio`, bez
  przebudowy playera.
* Radio nadal nie zna logiki misji, Cybernera ani backendu.
* Player nie skanuje katalogow na slepo i nadal buduje playliste wylacznie z
  `tracks[]`.

### Zmienione pliki

* `doc/radio_channel_contract.md`,
* `static/mp3/radio/channel/ghost_streem_1/meta.channel`,
* `doc/game_play_260626.md`,
* `doc/project_journal.md`.

### Wynik testow

* Walidacja JSON `meta.channel` - OK:
  `schema=1`, `source=ghost_radio`, `tracks=5`, brak brakujacych plikow.
* `node --check static/js/ghost_radio.js` - OK.
* `git diff --check -- doc/radio_channel_contract.md doc/game_play_260626.md doc/project_journal.md static/mp3/radio/channel/ghost_streem_1/meta.channel` - OK.

### Status

Sprint 53 gotowy jako kontrakt kanalow pod przyszly BlackNet. Nie dodano
runtime BlackNet, backendu ani discovery kanalow.

---

## 05.07.2026

### Sprint

Sprint 54 - Ghost Hack Radio UX Lift + First Interaction Autostart.

### Cel

Dopolerowac UI Ghost Hack Radio i podpiac start audio pod pierwsza interakcje
gracza z runtime gry, bez backendu, BlackNet i zmian kontraktu `meta.channel`.

### Co zostalo wykonane

* Przebudowano layout okna radia tak, aby `.ghost-radio-shell` wypelnial
  dostepna wysokosc okna.
* Okno radia dostalo staly, resizable layout z `flex` i pelnowysokosciowym
  panelem playera.
* Sekcje channel/track, equalizer, progress, controls, volume i source tworza
  spojny modul UI zamiast malego panelu przyklejonego do gory.
* Fake equalizer rozciaga sie wraz z wysokoscia okna.
* Mobile/narrow layout dostal osobne ograniczenia wysokosci i gestosci.
* Dodano first-interaction autostart:
  * `pointerdown`,
  * `keydown`.
* Autostart respektuje `localStorage.ghost_radio_autoplay = "0"` jako twarde
  wylaczenie.
* Jesli browser zablokuje autoplay, status przechodzi w `CLICK TO START`, a
  player pozostaje gotowy do startu przyciskiem Play.

### Najwazniejsze decyzje

* Autostart jest jednorazowo uzbrajany w module `GhostRadio`, bez nowego backendu
  i bez drugiego systemu audio.
* Mechanizm jest analogiczny do wzorca muzyki onboardingowej: pierwsza interakcja
  gracza jest sygnalem do proby `audio.play()`.
* `ghost_radio_autoplay = "0"` ma pierwszenstwo nad manifestem kanalu i nad
  pierwsza interakcja.

### Zmienione pliki

* `static/js/ghost_radio.js`,
* `static/css/ghost_radio.css`,
* `doc/game_play_260626.md`,
* `doc/project_journal.md`.

### Wynik testow

* `node --check static/js/ghost_radio.js`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `git diff --check`,
  OK; tylko ostrzezenia CRLF/LF dla istniejacych plikow roboczych.

### Status

Sprint 54 zamkniety jako UX lift i first-interaction autostart. Nie dodano
backendu, BlackNet ani nowych kanalow.

---

## 06.07.2026

### Etap

Faza G - State Snapshot + Delta Feed.

### Cel

Zamknac kierunek migracji runtime z agresywnego pollingu snapshotow na model
snapshot start/recovery + lekki delta feed.

### Najwazniejsze decyzje

Dopisano zabezpieczenia architektury delta-feed:

* zrodlo prawdy zostaje w obecnych modelach i snapshotach,
* delta bus dziala wylacznie jako dziennik zmian,
* delta bus nie liczy stanu gry,
* eventy sa idempotentne,
* eventy maja `entity_id` i `dedupe_key`,
* delta log ma retencje,
* endpoint zmian ma limit pobierania,
* za stary `since` albo przekroczony limit zwraca `recovery_required`,
* diagnostics ma pokazywac metryki przed/po dla wygaszania pollerow.

### Status

Faza G jest rozpisana jako bezpieczna seria Sprintow 55-69: audyt, kontrakt,
backend rownolegle do starego flow, pierwsze male scope'y, recovery, mapa na
koncu i dopiero potem wygaszanie pollerow.

### Doprecyzowanie Sprintu 55

Sprint 55 zmieniono z prostego `Polling Audit` na `Runtime Synchronization
Audit`.

Audyt ma mapowac caly cykl zycia danych per scope:

* co wywoluje zmiane,
* kto zapisuje zmiane,
* kto dzis ja wykrywa,
* kto ja renderuje,
* czy potrzebny jest pelny snapshot.

Dodano wymog tabeli przeplywu danych oraz szacowania spodziewanych oszczednosci
per scope: request count, payload, CPU i render cost.

Decyzja: przed budowa delta-feed trzeba najpierw sprawdzic, czy czesc pollerow
da sie ograniczyc albo usunac juz przez lepsze triggerowanie odswiezania po
akcjach gracza i zdarzeniach gry.

---

## 06.07.2026

### Etap

Sprint 55 - Runtime Synchronization Audit.

### Cel

Rozpoczac audyt synchronizacji runtime bez przebudowy endpointow, pollerow ani
renderow.

### Co zostalo wykonane

* Utworzono `doc/runtime_synchronization_audit.md`.
* Zebrano pierwsza inwentaryzacje scope'ow:
  * toolbar / wallet / profile,
  * desktop / apps,
  * storage / File Manager,
  * Googleplex,
  * Ghost Exchange,
  * Cyberner,
  * system messages,
  * launch queue,
  * operations,
  * map player actors,
  * map player areas,
  * map clan vulnerabilities.
* Dodano karty per scope z pytaniami:
  * co wywoluje zmiane,
  * kto zapisuje zmiane,
  * kto ja dzis wykrywa,
  * kto ja renderuje,
  * czy potrzebny jest pelny snapshot.
* Dodano ranking kosztow v0 dla backendu, frontendu, payloadu i czestotliwosci.

### Najwazniejsze obserwacje

* `/api/profile` jest wspolnym ciezkim snapshotem dla wielu niezaleznych
  widokow: toolbar, wallet, storage, apps, File Manager i profil.
* Cyberner uzywa juz lekkiego readonly profilu, ale odswieza liste rozmow co
  3000 ms.
* Mapa ma osobne pollery dla aktorow, terytoriow, podatnosci klanowych i
  operacji.
* `refreshPlayerAreas()` po stronie frontendu czysci i renderuje wiele warstw
  Leaflet od nowa.
* Ghost Exchange jest kontrolowanym refresh runtime rynku, nie tylko prostym
  odczytem dashboardu.

### Status

Sprint 55 trwa. Na tym etapie nie wprowadzono zmian runtime ani optymalizacji.

---

## 06.07.2026

### Etap

Sprint 56 - State Version Contract.

### Cel

Opisac wersjonowanie obecnych modeli stanu bez tworzenia nowego magazynu stanu,
bez delta busa i bez migracji frontendu.

### Co zostalo wykonane

* Utworzono `doc/state_version_contract.md`.
* Zdefiniowano globalne `state_version`.
* Zdefiniowano wersje per scope:
  * `wallet_version`,
  * `profile_version`,
  * `storage_version`,
  * `apps_version`,
  * `mail_version`,
  * `ghost_exchange_version`,
  * `operations_version`,
  * `map_version`.
* Dopisano do planu Sprintu 56 brakujace scope'y `operations_version` i
  `map_version`.
* Opisano, ktore snapshot endpointy moga w przyszlosci zwracac wersje.

### Najwazniejsze decyzje

* Wersje opisuja istniejace modele i snapshoty.
* Wersje nie tworza nowego zrodla prawdy.
* Wersje nie sa liczone z delta busa.
* `state_version` jest globalna informacja, ze cos w runtime moglo sie zmienic.
* Wersje per scope sluza do pozniejszego recovery i selektywnego odswiezania.

### Status

Sprint 56 zamkniety jako kontrakt dokumentacyjny. Nie zmieniono zachowania
frontendu, nie wylaczono pollerow i nie dodano nowego endpointu.

---

## 06.07.2026

### Etap

Sprint 57 - Delta Event Schema.

### Cel

Zdefiniowac stabilny format eventow delta v0 przed implementacja
`GameStateDeltaBus`.

### Co zostalo wykonane

* Utworzono `doc/delta_event_schema.md`.
* Opisano wspolna strukture eventu:
  * `version`,
  * `scope`,
  * `type`,
  * `entity_id`,
  * `dedupe_key`,
  * `payload`,
  * `created_at`.
* Ustalono nazewnictwo typow w formacie `scope.action`.
* Opisano minimalne payloady v0 dla:
  * wallet,
  * storage,
  * apps,
  * mail,
  * Ghost Exchange,
  * operations,
  * map.
* Dopisano zasade idempotencji przez `dedupe_key`.
* Dopisano zasade, ze `payload` nie jest pelnym snapshotem.

### Najwazniejsze decyzje

* Event delta opisuje zmiane, ktora juz zaszla w istniejacym zrodle prawdy.
* Event delta nie jest zrodlem prawdy.
* Event delta nie przechowuje pelnego profilu, mapy, maila ani dashboardu GX.
* Snapshoty pozostaja sciezka startu i recovery.

### Status

Sprint 57 zamkniety jako kontrakt dokumentacyjny. Nie powstal jeszcze
`GameStateDeltaBus`, nie dodano endpointu delt i nie zmieniono frontendu.

---

## 06.07.2026

### Etap

Sprint 58 - Backend Delta Bus v0.

### Cel

Dodac backendowy dziennik zmian rownolegle do starego runtime, bez podpinania
frontendu i bez tworzenia nowego magazynu stanu gry.

### Co zostalo wykonane

* Dodano tabele `game_state_deltas`.
* Dodano `GameStateDeltaBus` w `database.py`.
* Dodano instancje `delta_bus` w `run.py` obok istniejacych store'ow.
* Dodano zapis eventu przez:
  * `record_change(username, scope, change_type, payload, entity_id, dedupe_key)`.
* Dodano odczyt eventow przez:
  * `get_changes_since(username, since_version, limit)`.
* Dodano retencje po liczbie eventow.
* Dodano idempotencje przez `dedupe_key`.
* Dodano sygnal `recovery_required` dla:
  * niepoprawnego `since`,
  * wersji poza retencja,
  * przekroczonego limitu odczytu.

### Najwazniejsze decyzje

* Delta bus jest dziennikiem powiadomien o zmianach.
* Delta bus nie liczy stanu gry.
* Delta bus nie zastapil profilu, mapy, maila, Ghost Exchange ani snapshotow.
* Stary runtime dziala bez zmian, bo zaden endpoint nie zostal przepiety na
  delty.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest`,
  OK.
* `python -m unittest tests.test_app_catalog_cleanup`,
  OK.
* `git diff --check`,
  OK; ostrzezenie CRLF/LF dotyczy istniejacego stylu pliku `run.py`.
* `python -m unittest tests.test_target_persistence`,
  FAIL na znanych testach `/map` JSON payload:
  * `test_map_embeds_profile_as_json_literal`,
  * `test_map_embeds_large_profile_payload_as_json_literal`.

Te regresje byly juz oznaczone w journalu jako osobny dlug techniczny map
payload i nie wynikaja z `GameStateDeltaBus`.

### Status

Sprint 58 zamkniety jako backendowy fundament delta bus v0. Nie dodano jeszcze
`/api/state/changes`, nie zmieniono frontendu i nie wylaczono pollerow.

---

## 06.07.2026

### Etap

Sprint 59 - Read-only Delta Endpoint.

### Cel

Udostepnic delty do podgladu i testow bez podpinania UI produkcyjnego.

### Co zostalo wykonane

* Dodano endpoint `GET /api/state/changes?since=...&limit=...`.
* Endpoint korzysta wylacznie z `delta_bus.get_changes_since(...)`.
* Endpoint zwraca:
  * `current_version`,
  * `changes`,
  * `recovery_required`,
  * `reason`.
* Brak zmian zwraca pusta liste `changes`, nie blad.
* Przekroczony limit zwraca `recovery_required`.
* Wersja poza retencja zwraca `recovery_required`.
* Brak sesji zwraca `401` oraz `reason = not_logged_in`.

### Najwazniejsze decyzje

* Endpoint jest read-only.
* Endpoint nie liczy stanu gry.
* Endpoint nie odpala snapshotow.
* Endpoint nie wywoluje `sync_session_profile()`.
* Frontend produkcyjny nadal nie korzysta z delta endpointu.
* Stare pollery pozostaja wlaczone.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest`,
  OK.

### Status

Sprint 59 zamkniety jako read-only endpoint do podgladu delt. Nie podlaczono UI,
nie dodano `applyDelta()` i nie wylaczono zadnego pollera.

### Checkpoint 59 live

Baseline potwierdza ranking kosztow v0.

Najwiekszy koszt generuja:

* map player actors,
* map player areas,
* clan vulnerabilities,
* operations summary.

Lekkie endpointy `system-messages` i `launch-queue` bywaja opoznione
prawdopodobnie przez kolejke za ciezkimi requestami mapy.

Sprint 59 nie zmienil runtime UI, wiec brak poprawy wydajnosci jest oczekiwany.

---

## 06.07.2026

### Etap

Sprint 60 - Delta Diagnostics Panel.

### Cel

Dodac dev/admin podglad delt, wersji i recovery przed podpieciem
`applyDelta()`.

### Co zostalo wykonane

* Dodano endpoint `GET /api/dev/delta-diagnostics`.
* Endpoint jest dostepny tylko dla admina/dev.
* Endpoint zwraca:
  * `current_version`,
  * ostatnie eventy,
  * `scope`,
  * `type`,
  * `entity_id`,
  * `dedupe_key`,
  * `payload_size`,
  * `recovery_count`,
  * `delta_events_per_minute`,
  * `delta_payload_size`,
  * `snapshot_recovery_count`,
  * `pollers_active_count`.
* Dodano metody diagnostyczne w `GameStateDeltaBus`.
* Dodano testy admin-only i braku pelnego sync profilu.

### Najwazniejsze decyzje

* Diagnostyka jest obserwacyjna.
* Endpoint nie odpala `sync_session_profile()`.
* Endpoint nie robi recovery w UI.
* Endpoint nie podpina `applyDelta()`.
* Runtime zwyklego gracza pozostaje bez zmian.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest tests.test_target_persistence.DeltaDiagnosticsEndpointTest`,
  OK.

### Status

Sprint 60 zamkniety jako dev/admin diagnostyka delta feed. Nie podlaczono
frontendu produkcyjnego, nie wylaczono pollerow i nie dodano recovery UI.

### Doprecyzowanie po Sprincie 60

Do planu Fazy G dopisano dwa sprinty pomostowe:

* Sprint 60.5 - Async Operation Runner Audit,
* Sprint 60.6 - Async Operation Runner v0.

Decyzja: zanim pierwsze ciezkie akcje zaczna korzystac z pracy w tle, trzeba
najpierw wskazac endpointy trwajace dluzej niz 1000 ms i rozdzielic akcje, ktore
musza zwracac natychmiastowy payload, od akcji, ktore moga zwrocic tylko
`operation_id`.

Pierwotnie runner v0 mial objac jedna bezpieczna akcje, statusy
`queued/running/done/failed` i wynik przez system message albo delta event. Nie
ma przerabiac calego runtime ani tworzyc drugiego systemu operacji.

---

## 06.07.2026

### Etap

Sprint 60.5 - Async Operation Runner Audit.

### Cel

Wskazac akcje runtime, ktore moga szybko zwracac `operation_id`, a wlasciwa
praca moze konczyc sie w tle.

### Co zostalo wykonane

* Dodano dokument `doc/async_operation_runner_audit.md`.
* Przejrzano ciezkie endpointy mapy, operacji, Ghost Exchange, Googleplex,
  GhostLab i generatora aplikacji.
* Rozdzielono ciezkie odczyty od akcji nadajacych sie do runnera.
* Potwierdzono, ze map player actors, map player areas, clan vulnerabilities,
  operations summary i Ghost Exchange sa problemem synchronizacji/delta-feed,
  a nie kandydatem do Async Runnera.
* Przejrzano akcje:
  * `/map-action`,
  * `/hack-action`,
  * `/api/operations/cancel`,
  * `/install-app`,
  * `/api/apps/uninstall`,
  * `/api/apps/generate`,
  * `/api/ghostlab/projects/<project_id>/compile`.

### Najwazniejsze decyzje

* Async Runner nie ma obslugiwac ciezkich snapshotow ani polling endpointow.
* `/hack-action`, `/map-action`, `/install-app` i uninstall aplikacji nie sa
  dobrym kandydatem v0, bo potrzebuja natychmiastowego payloadu albo dotykaja
  ekonomii/storage.
* Najbezpieczniejszy kandydat na Sprint 60.6 to compile projektu GhostLab:
  `POST /api/ghostlab/projects/<project_id>/compile`.
* Kandydat zapasowy to `/api/apps/generate`, ale ma wieksze ryzyko, bo dotyka
  katalogu Googleplex i plikow projektu.

### Testy

* Sprint 60.5 byl audytem dokumentacyjnym.
* Nie zmieniono kodu runtime.

### Status

Sprint 60.5 zamkniety jako audyt. Audyt wskazal GhostLab compile project jako
najbezpieczniejszego kandydata technicznego, ale decyzja planistyczna po audycie
wstrzymala implementacje runnera na tym etapie.

---

## 06.07.2026

### Etap

Sprint 60.6 - Async Operation Runner Decision.

### Status

Cancelled / postponed.

### Decyzja

Po audycie Sprintu 60.5 zrezygnowano z implementacji Async Operation Runner v0
na obecnym etapie.

### Powod

Jedynym bezpiecznym kandydatem v0 okazal sie
`POST /api/ghostlab/projects/<project_id>/compile`.

Dla jednej samodzielnej akcji koszt dodania runnera, statusow, deduplikacji,
obslugi bledow i utrzymania osobnego przeplywu async jest wiekszy niz aktualny
zysk runtime.

### Wnioski

* Ciezkie endpointy odczytu pozostaja tematem snapshot + delta-feed.
* `/hack-action`, `/map-action`, install/uninstall, Ghost Exchange i polling
  mapy nie sa kandydatami do runnera v0.
* Temat runnera mozna wznowic, gdy pojawi sie wiecej akcji typu queued job.
* Runtime pozostaje bez zmian.
* Faza G kontynuuje glowna sciezke od Sprintu 61 - First Safe Delta: Wallet.

---

## 06.07.2026

### Etap

Sprint 61 - First Safe Delta: Wallet.

### Cel

Pierwsza realna migracja malego elementu UI na delta-feed: saldo HC.

### Co zostalo wykonane

* Dodano helper `record_wallet_balance_delta(...)`.
* Backend emituje `wallet.balance_changed` po realnych zmianach HC w:
  * Ghost Exchange auto-sale po zapisaniu profilu,
  * legacy Ghost Exchange manual sell,
  * Wallet transfer,
  * Financial Sniffer technical transfer,
  * Googleplex product purchase,
  * Googleplex app install.
* `/api/state/changes` zwraca eventy wallet przez istniejacy delta bus.
* Frontend dostal lekki delta poller oparty o `/api/state/changes`.
* `applyDelta()` obsluguje tylko `wallet.balance_changed`.
* Saldo aktualizuje sie w toolbarze, Wallet HC i widocznym panelu Googleplex.
* `/api/profile` zostaje recovery tylko dla rozjazdu delta feed.

### Najwazniejsze decyzje

* Nie migrowano mapy, maila, apps ani Ghost Exchange dashboardu.
* `refresh_market_runtime()` nie emituje delty podczas samej symulacji.
  Delta wallet powstaje dopiero po sciezce, ktora zapisuje profil.
* Delta nie liczy salda. Zawiera tylko saldo zapisane juz w zrodle prawdy.
* Ten sam event jest idempotentny po `dedupe_key`.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest tests.test_target_persistence.WalletDeltaEndpointTest`,
  OK.
* `python -m unittest tests.test_target_persistence`,
  uruchomiony; zatrzymal sie na dwoch istniejacych testach map template JSON
  embed (`MissingProfileAndSessionSafetyTest`), poza zakresem Sprintu 61.

### Status

Sprint 61 zamkniety jako pierwsza bezpieczna delta wallet. Snapshot profilu
pozostaje sciezka recovery.

---

## 07.07.2026

### Etap

Sprint 62 - Storage Delta.

### Cel

Przeniesc podstawowe zmiany storage na delta-feed, zeby File Manager i toolbar
mogly widziec aktualny stan dysku bez pelnego `/api/profile`.

### Co zostalo wykonane

* Dodano helper `record_storage_delta(...)`.
* Backend emituje:
  * `storage.used_changed`,
  * `storage.capacity_changed`.
* Eventy storage powstaja po:
  * finalizacji operacji zapisujacej pliki przez `refresh_and_persist_operations`,
  * Ghost Exchange auto-sale po zapisaniu profilu,
  * legacy Ghost Exchange manual sell,
  * Googleplex storage/product purchase,
  * instalacji aplikacji,
  * uninstall aplikacji.
* Frontend `applyDelta()` obsluguje scope `storage`.
* Otwarty File Manager aktualizuje pasek dysku bez przebudowy listy plikow.
* Toolbar profile dostaje aktualne `storage_used`, `storage_capacity`,
  `storage_unit` i `storage_over_limit`.
* Snapshot `/api/profile` zostaje sciezka recovery dla rozjazdu delta feed.

### Najwazniejsze decyzje

* Nie migrowano apps.
* Nie migrowano Ghost Exchange dashboardu.
* Nie ruszano mapy.
* `append_runtime_file_if_space()` nie emituje eventu samodzielnie, bo nie zna
  username ani nie zapisuje profilu. Event powstaje dopiero w sciezce persist.
* `refresh_market_runtime()` nie emituje eventu podczas symulacji. Event storage
  powstaje dopiero po endpointowym zapisie profilu.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest tests.test_target_persistence.WalletDeltaEndpointTest`,
  OK.
* `python -m unittest tests.test_target_persistence.TargetPersistenceHelpersTest.test_googleplex_storage_upgrade_increases_capacity_without_app_or_tool`,
  OK.

### Status

Sprint 62 zamkniety jako storage delta v0. File Manager aktualizuje pasek dysku z
delta-feed, a pelny profil pozostaje recovery.

---

## 07.07.2026

### Etap

Sprint 63 - Apps Delta.

### Cel

Aktualizowac stan aplikacji przez delta-feed po install/uninstall/status change,
bez pelnego odswiezania desktopu z `/api/profile`.

### Co zostalo wykonane

* Dodano helper `record_apps_delta(...)`.
* Backend obsluguje eventy:
  * `apps.app_installed`,
  * `apps.app_uninstalled`,
  * `apps.status_changed`,
  * `apps.cooldown_changed`.
* Eventy aplikacji powstaja po:
  * instalacji aplikacji z Googleplex,
  * uninstall aplikacji.
* Nie znaleziono osobnego runtime status/cooldown aplikacji do podpiecia w tym
  sprincie. Helper jest gotowy na te typy, ale nie generuje sztucznych eventow.
* Payload aplikacji niesie aktualne:
  * `apps`,
  * `files.tools`.
* Frontend `applyDelta()` obsluguje scope `apps`.
* Desktop i menu Start przebudowuja launchery z payloadu delta, bez
  `refreshDesktop(false)` po install/uninstall.
* Otwarty File Manager odswieza folder `/tools`, jesli jest aktualnie otwarty.
* `/api/profile` zostaje sciezka recovery dla rozjazdu delta feed.

### Najwazniejsze decyzje

* `profile.apps` pozostaje zrodlem prawdy.
* `files.tools` pozostaje zrodlem prawdy dla folderu narzedzi.
* Delta apps jest powiadomieniem i payloadem do odswiezenia widoku, nie drugim
  cache aplikacji.
* Nie migrowano katalogu Googleplex.
* Nie ruszano mapy.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.TargetPersistenceHelpersTest.test_generated_app_install_tools_uninstall_lifecycle`,
  OK.

### Checkpoint 63

Install/uninstall aplikacji dziala wyraznie szybciej po przeniesieniu
wallet/storage/apps na delta-feed. Log instalacji pokazuje szybkie wykonanie
akcji i brak serii ciezkich `/api/profile` po instalacji.

Nadal widoczny jest pojedynczy wolniejszy `/system-messages`, ale wyglada to
bardziej jak efekt kolejki/runtime niz koszt samego install flow.

### Status

Sprint 63 zamkniety jako apps delta v0. Install/uninstall aplikacji emituja
eventy `apps.*`, a desktop, menu Start i File Manager `/tools` moga odswiezyc
widok bez pelnego `/api/profile`.

---

## 07.07.2026

### Etap

Sprint 64 - Mail / Ghost Exchange Summary Delta.

### Cel

Aktualizowac male elementy Cybernera i Ghost Exchange przez delta-feed, bez
pelnych bootstrapow tam, gdzie wystarczy licznik, thread summary albo summary
rynku.

### Co zostalo wykonane

* Dodano helpery:
  * `record_mail_delta(...)`,
  * `record_mail_thread_update(...)`,
  * `record_ghost_exchange_delta(...)`.
* Backend emituje:
  * `mail.unread_changed`,
  * `mail.thread_updated`,
  * `ghost_exchange.summary_changed`,
  * `ghost_exchange.transaction_added`.
* Eventy mail powstaja po:
  * odczycie aktywnego watku,
  * wyslaniu wiadomosci,
  * otrzymaniu wiadomosci przez odbiorcow,
  * systemowym/direct powiadomieniu Cybernera.
* Eventy Ghost Exchange powstaja po:
  * auto-sale,
  * legacy manual sale.
* Frontend `applyDelta()` obsluguje scope `mail` i `ghost_exchange`.
* Otwarty Cyberner aktualizuje unread badge i podstawowy preview watku z delty.
* Otwarty Ghost Exchange aktualizuje summary i ostatnie transakcje z delty.

### Najwazniejsze decyzje

* `/api/mail/bootstrap` pozostaje snapshot/recovery.
* `/api/chats/messages` pozostaje zrodlem dla aktywnego watku.
* `/api/ghost-exchange` pozostaje snapshot/recovery dashboardu.
* Nie migrowano pelnej listy maili.
* Nie migrowano pelnego dashboardu Ghost Exchange.
* Nie ruszano mapy.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.TargetPersistenceHelpersTest.test_generated_app_install_tools_uninstall_lifecycle`,
  OK.

### Status

Sprint 64 zamkniety jako mail/Ghost Exchange summary delta v0. Male liczniki i
summary moga odswiezac sie przez delta-feed, a pelne snapshoty pozostaja
recovery.

---

## 07.07.2026

### Etap

Sprint 65 - Delta Recovery.

### Cel

Utwardzic recovery delta-feed przed wejsciem w mape.

### Co zostalo wykonane

* `/api/state/changes` zwraca `recovery_scopes`, gdy `recovery_required=true`.
* Frontend rozdziela recovery per scope:
  * wallet/profile przez `/api/profile`,
  * storage przez `/api/profile`,
  * apps przez `/api/profile`,
  * mail przez `/api/mail/bootstrap`,
  * Ghost Exchange przez `/api/ghost-exchange`.
* Recovery aktualizuje tylko istniejace widoki i dane runtime.
* Po recovery frontend zapisuje `stateDeltaVersion` z `current_version`.
* Brak panic reloadu strony.

### Najwazniejsze decyzje

* Przy `limit_exceeded` i `outside_retention` endpoint zwraca wspolny zestaw
  scope'ow recovery dla dotychczas zmigrowanych modulow, bo po utracie eventow
  nie wolno zgadywac, ktory scope faktycznie wypadl z retencji.
* Snapshoty pozostaja zrodlem recovery, nie drugim delta systemem.
* Nie ruszano mapy.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest`,
  OK.

### Status

Sprint 65 zamkniety. Delta-feed ma scope'owane recovery dla dotychczas
zmigrowanych modulow i nie wymaga globalnego reloadu.

---

## 07.07.2026

### Etap

Sprint 66 - Map Delta Audit.

### Cel

Przygotowac mape pod delty bez migracji runtime mapy.

### Co zostalo wykonane

* Dodano dokument audytu `doc/map_delta_audit.md`.
* Spisano wymagane eventy mapy:
  * `map.player_moved`,
  * `map.player_actor_updated`,
  * `map.player_actor_removed`,
  * `map.target_updated`,
  * `map.target_captured`,
  * `map.target_removed`,
  * `map.area_claimed`,
  * `map.area_contested`,
  * `map.vulnerability_added`,
  * `map.vulnerability_removed`.
* Przypisano zrodla prawdy:
  * profil,
  * `mail_store`,
  * territory store,
  * territory conflict store,
  * target store,
  * vulnerability store,
  * operations runtime.
* Sprawdzono obecne endpointy mapy:
  * `/api/map/player-actors`,
  * `/api/map/friends`,
  * `/api/map/player-areas`,
  * `/api/map/clan-vulnerabilities`.
* Sprawdzono obecne warstwy Leaflet:
  * `playerActorMarkers`,
  * `friendMarkers`,
  * `clanVulnerabilityLayers`,
  * `playerAreaLayers`,
  * `conflictAreaLayers`,
  * `contestedTargetLayers`,
  * `capturedConflictPillarLayers`.

### Najwazniejsze wnioski

* `playerActorMarkers` sa najlepszym pierwszym kandydatem na delty, bo sa juz
  kluczowane po uzytkowniku i aktualizowane punktowo przez `setLatLng` oraz
  `setIcon`.
* `friendMarkers` tez sa technicznie punktowe, ale moga dublowac informacje z
  `player-actors`; przed migracja trzeba zdecydowac, czy zostaja osobna warstwa.
* `clanVulnerabilityLayers` maja pomocniczy registry, ale obecny refresh nadal
  czysci cala warstwe. Delty sa mozliwe po ustaleniu stabilnego `entity_id`.
* `playerAreaLayers`, `conflictAreaLayers`, `contestedTargetLayers` i
  `capturedConflictPillarLayers` sa dzis czyszczone i renderowane od zera.
  Zostaja snapshot/recovery do czasu wprowadzenia stabilnych kluczy polygonow i
  konfliktow.
* Targety bazowe wymagaja osobnego registry po `target_id`, zanim wejda do
  `map.target_*`.

### Decyzje

* Sprint 66 nie zmienil runtime mapy.
* Nie podpieto `applyDelta()` dla mapy.
* Nie wylaczono zadnego pollera mapy.
* Sprint 67 powinien zaczac tylko od:
  * `map.player_moved`,
  * `map.player_actor_updated`,
  * `map.player_actor_removed`.

### Testy

* `git diff --check`,
  OK.

### Status

Sprint 66 zamkniety jako audyt. Mapa ma kontrakt delt i znane granice migracji,
ale nadal dziala po staremu.

---

## 07.07.2026

### Etap

Sprint 67 - Map Actor Delta v0.

### Cel

Aktualizowac wylacznie markery graczy przez delta-feed, bez ruszania targetow,
area layers, konfliktow, vulnerabilities i `friendMarkers`.

### Co zostalo wykonane

* Dodano helpery backendowe:
  * `build_map_player_actor_delta_payload(...)`,
  * `record_map_player_actor_delta(...)`.
* Backend emituje eventy scope `map` dla player actors:
  * `map.player_moved`,
  * `map.player_actor_updated`,
  * `map.player_actor_removed`.
* `entity_id` dla eventu map actor to `username` aktora.
* Eventy sa emitowane per viewer:
  * zaakceptowane kontakty aktora,
  * wlasciciel pola, jesli ruch gracza tworzy intruder context.
* Akcja `travel` emituje `map.player_moved`.
* Travel ticket Googleplex emituje `map.player_moved`.
* `/api/state/changes` uwzglednia scope `map` w recovery.
* Frontend `applyDelta()` rozpoznaje scope `map`.
* Dodano recovery mapy przez istniejace `refreshPlayerActors()`.
* W `map_template.html` wyciagnieto punktowy renderer:
  * `upsertPlayerActorMarker(...)`,
  * `removePlayerActorMarker(...)`,
  * `applyMapPlayerActorDelta(...)`.
* Snapshotowy `renderPlayerActors(...)` nadal dziala po staremu, ale korzysta z
  tego samego punktowego upsert/remove.

### Najwazniejsze decyzje

* Nie ruszano `friendMarkers`.
* Nie ruszano targetow.
* Nie ruszano area layers.
* Nie ruszano konfliktow.
* Nie ruszano vulnerability layers.
* Delta bus nie jest zrodlem prawdy mapy; tylko powiadamia widzow o zmianie
  aktora.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest`,
  OK.
* `git diff --check`,
  OK.

### Status

Sprint 67 zamkniety jako Map Actor Delta v0. Pierwsza warstwa mapy korzysta z
delta-feed, a `/api/map/player-actors` zostaje snapshot/recovery.

### Checkpoint 67

Map actor delta v0 dziala poprawnie. Markery graczy moga byc aktualizowane
punktowo przez delta-feed, a snapshot `/api/map/player-actors` pozostaje
recovery.

Brak widocznego przyspieszenia calej mapy jest oczekiwany, poniewaz glowne
obciazenie nadal generuja map player areas, clan vulnerabilities oraz operations
summary.

---

## 07.07.2026

### Etap

Sprint 68 - Map Target Registry / Delta Prep.

### Cel

Przygotowac targety pod przyszle delty przez stabilny registry po `target_id`,
bez migracji pelnych warstw mapy.

### Co zostalo wykonane

* Dodano stabilny helper JS `targetStableId(...)`.
* `normalizeMapMenuTarget(...)` uzupelnia `target_id`.
* Dodano registry:

```text
window.targetMarkers[target_id]
```

* Dodano helpery:
  * `registerTargetMarker(...)`,
  * `unregisterTargetMarker(...)`.
* Markery bazowe renderowane przez Folium dostaja `data-target-id` z
  `build_operation_target_id(...)`.
* Rejestrowane sa target markery:
  * DOM `.marker-label`,
  * interaktywne targety,
  * scan target markers,
  * legacy scan target markers,
  * hacked target markers tworzone runtime.
* Przy ukrywaniu DOM targetu registry usuwa nieaktualny wpis.
* Uaktualniono `doc/map_delta_audit.md` o kontrakt `targetMarkers[target_id]`.

### Najwazniejsze decyzje

* Sprint 68 nie wlacza jeszcze `map.target_*` w delta-feed.
* Nie ruszano `playerAreaLayers`.
* Nie ruszano `conflictAreaLayers`.
* Nie ruszano `contestedTargetLayers`.
* Nie ruszano `capturedConflictPillarLayers`.
* Snapshoty mapy pozostaja aktywne.
* `.marker-hacked` DOM pozostaje legacy/snapshotowo; runtime hacked targety
  tworzone przez JS sa rejestrowane w `targetMarkers`.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `git diff --check`,
  OK.

### Status

Sprint 68 zamkniety jako target registry prep. Targety maja przygotowany
stabilny registry pod przyszle `map.target_*`, ale runtime delt targetow nie
zostal jeszcze wlaczony.

---

## 07.07.2026

### Etap

Sprint 68.5 - Map Target Delta v0.

### Cel

Aktualizowac konkretne target markery po `target_id` przez delta-feed, dopiero
po przygotowaniu `targetMarkers[target_id]`.

### Co zostalo wykonane

* Dodano backendowy helper `record_map_target_delta(...)`.
* Backend emituje:
  * `map.target_updated` po ustawieniu/aktualizacji targetu przez
    `/hack-action`,
  * `map.target_captured` po udanym przejeciu targetu,
  * `map.target_removed` jest obslugiwany kontraktowo przez helper i frontend.
* `entity_id` eventu targetu to stabilny `target_id` z
  `build_operation_target_id(...)`.
* Frontend `applyDelta()` rozpoznaje target delty mapy.
* Desktopowy delta poller przekazuje target delty do otwartych iframe mapy.
* `map_template.html` obsluguje `applyMapTargetDelta(...)` tylko przez
  `targetMarkers[target_id]`.
* Target recovery dla mapy korzysta ze snapshotu mapy przez reload iframe.

### Najwazniejsze decyzje

* Nie ruszano `playerAreaLayers`.
* Nie ruszano `conflictAreaLayers`.
* Nie ruszano `area_claimed` / `area_contested`.
* Nie ruszano contested/captured pillar layers.
* Jesli targetu nie ma w `targetMarkers[target_id]`, delta nie zgaduje stanu i
  zostawia recovery snapshotowi.
* Przy okazji poprawiono most map delta tak, aby wolal funkcje w iframe mapy,
  a nie w oknie desktopu.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest`,
  OK.
* `git diff --check`,
  OK.

### Status

Sprint 68.5 zamkniety jako Map Target Delta v0. Target delty dzialaja tylko po
registry `targetMarkers[target_id]`, a warstwy obszarow i konfliktow pozostaja
snapshotowe.

---

## 07.07.2026

### Etap

Sprint 69 - Poller Thinning / Retirement.

### Cel

Zmniejszyc liczbe cyklicznych requestow po potwierdzeniu, ze wallet, storage,
apps, mail/Ghost Exchange summary, player actors i target registry dzialaja
bezpiecznie z delta-feed/recovery.

### Co zostalo wykonane

* Dodano raport `doc/poller_retirement_report.md`.
* Rozrzedzono Cyberner bootstrap:
  * bylo `3000 ms`,
  * jest `10000 ms`.
* Rozrzedzono snapshot map player actors:
  * bylo `5000 ms`,
  * jest `30000 ms`.
* Snapshoty pozostaja:
  * `/api/mail/bootstrap`,
  * `/api/map/player-actors`.
* Endpointy snapshotowe nie zostaly usuniete.
* Recovery mapy i maila pozostaje dostepne.

### Pollery zostawione bez zmian

* `/api/map/player-areas` - nadal bez area delta.
* `/api/map/clan-vulnerabilities` - vulnerability layers nadal bez delt.
* `/api/operations?summary=1` - operations summary nadal bez delt.
* `/system-messages` - notification bridge nie zastapil jeszcze pollera.
* `/launch-queue` - pozostaje action/snapshot flow.
* `/api/state/changes` - glowny lekki delta feed.

### Request count przed/po

Szacunek statyczny dla jednego otwartego okna mapy i jednego otwartego
Cybernera:

```text
przed: 68 requestow / min
po:    44 requesty / min
```

Zmiana dotyczy tylko:

* `/api/mail/bootstrap`: 20/min -> 6/min,
* `/api/map/player-actors`: 12/min -> 2/min.

### Najwazniejsze decyzje

* Nie wylaczono jeszcze ciezkich pollerow map player areas, clan vulnerabilities
  ani operations summary, bo nadal nie maja bezpiecznego delta replacement.
* Nie ma globalnego reloadu jako normalnej sciezki.
* Sprint 69 jest thinning v0, nie koncowe usuniecie pollingu.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest`,
  OK.
* `git diff --check`,
  OK.

### Status

Sprint 69 zamkniety jako poller thinning v0. Liczba cyklicznych requestow spada
w obszarach objetych delta-feed, a snapshoty zostaja jako start/recovery.

---

## 07.07.2026

### Etap

Sprint 70 - Delta Refactor Integrity Audit.

### Cel

Przejsc jeszcze raz miejsca zmienione w Fazie G i potwierdzic, ze delta-feed,
recovery, snapshoty oraz stare pollery sa spojne, bez protez, podwojnych
refreshy i ukrytego legacy.

### Co zostalo sprawdzone

* Helpery:
  * `record_wallet_balance_delta(...)`,
  * `record_storage_delta(...)`,
  * `record_apps_delta(...)`,
  * `record_mail_delta(...)`,
  * `record_ghost_exchange_delta(...)`,
  * `record_map_player_actor_delta(...)`,
  * `record_map_target_delta(...)`.
* Kontrakt eventow:
  * `scope`,
  * `type`,
  * `entity_id`,
  * `dedupe_key`,
  * `payload`,
  * `created_at`.
* Frontend:
  * `applyDelta()`,
  * `processedDeltaKeys`,
  * recovery per scope,
  * update wallet/storage/apps/mail/GX/map actors/map targets.
* Snapshoty:
  * `/api/profile`,
  * `/api/mail/bootstrap`,
  * `/api/ghost-exchange`,
  * `/api/map/player-actors`.
* Dokumentacja Fazy G.

### Poprawki runtime

* Poprawiono recovery mapy:
  * bylo `recoverMapPlayerActorsDeltaScope()`,
  * jest `recoverMapDeltaScope()`.
* Recovery scope `map` probuje teraz odswiezyc:
  * target snapshot,
  * player actors snapshot.
* Usunieto zbedne pelne refreshy `/api/profile` z:
  * `loadExchange()` po otrzymaniu `balance`,
  * legacy `sellGhostExchangeFile(...)` po otrzymaniu `balance`,
  * wallet transfer po otrzymaniu `balance`.
* Wallet transfer aktualizuje teraz saldo przez `updateWalletBalanceView(...)`.

### Wynik audytu

* Delta bus pozostaje dziennikiem zmian, nie drugim magazynem stanu.
* Eventy maja spojny kontrakt.
* `applyDelta()` aktualizuje punktowo.
* Recovery jest per scope.
* Snapshot endpointy nadal istnieja.
* Stare ciezkie pollery nie zostaly usuniete bez replacement.
* Dodano raport `doc/delta_refactor_integrity_audit.md`.

### Ograniczenia

* `refreshMapTargetSnapshot()` nadal jest snapshotem iframe mapy jako recovery,
  nie lekkim dedykowanym endpointem targetow.
* `map player areas`, `clan vulnerabilities` i `operations summary` nadal sa
  poza delta replacement.
* Czesc akcji narzedzi/operacji nadal moze korzystac z pelnego profilu, bo nie
  zostala jeszcze objeta migracja delta-feed.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `node --check static/js/terminal.js`,
  OK.
* `python -m unittest tests.test_target_persistence.GameStateDeltaBusTest tests.test_target_persistence.StateChangesEndpointTest tests.test_target_persistence.WalletDeltaEndpointTest tests.test_target_persistence.DeltaDiagnosticsEndpointTest`,
  OK, 20 testow.
* `git diff --check`,
  OK.

### Status

Sprint 70 zamyka audyt integralnosci refactoru delta-feed. Wykryte niespojnosci
zostaly naprawione minimalnie, bez dodawania nowych endpointow i bez usuwania
snapshotow.

---

## 07.07.2026

### Etap

Plan Sprintu 71 - Map Initial Load Gate.

### Cel

Przygotowac kolejny sprint mapowy jako bramke pierwszego ladowania mapy.

Sprint 71 nie ma jeszcze przyspieszac mapy. Ma zagwarantowac, ze gracz nie
zaczyna gry na niepelnym stanie swiata.

### Najwazniejsza decyzja

Mapa nie jest gotowa, dopoki krytyczne warstwy nie zglosza `loaded`.

Leaflet widoczny na ekranie nie oznacza gotowej mapy gameplayowej.

### Critical scopes

Critical scopes blokuja interakcje mapowe:

* mapa bazowa,
* pozycja gracza,
* target snapshot,
* terytoria graczy,
* przejete cele.

### Optional scopes

Optional scopes moga dosynchronizowac sie po zdjeciu glownej bramki:

* gracze online,
* podatnosci klanow,
* aktywne operacje,
* live delta status.

### Zasada UX/runtime

Preloader mapy nie jest ozdoba. Jest czescia kontraktu runtime. Dopoki critical
map scopes nie sa `loaded`, interakcje gameplayowe mapy sa zablokowane.

### Status

Sprint 71 zostal rozpisany w `doc/game_play_260626.md`. Implementacja jeszcze
nie zostala rozpoczeta.

---

## 07.07.2026

### Etap

Sprint 71 - Map Initial Load Gate.

### Cel

Dodac jawna bramke pierwszego ladowania mapy, zeby gracz nie mogl odpalac
akcji mapowych na niepelnym stanie swiata.

### Co zostalo wykonane

* Dodano overlay `chaos-map-boot-overlay`.
* Dodano `window.mapBootState`:
  * `loading`,
  * `ready`,
  * `failed`,
  * `loadedScopes`.
* Dodano helpery bootu:
  * `showMapPreloader(...)`,
  * `hideMapPreloader()`,
  * `disableMapGameplay()`,
  * `enableMapGameplay()`,
  * `bootStep(...)`,
  * `bootMapInitialState()`.
* Przeniesiono pierwszy start refreshy mapy za critical boot.
* Timery snapshotow startuja dopiero po zakonczeniu critical boot.
* Critical boot obejmuje:
  * inicjalizacje mapy,
  * pozycje gracza,
  * target snapshot,
  * terytoria graczy,
  * przejete cele.
* Optional scopes laduja sie po zdjeciu glownej bramki:
  * podatnosci klanow,
  * aktywne operacje,
  * gracze na mapie.
* Zablokowano akcje mapowe przed `mapBootState.ready=true`:
  * context menu mapy,
  * menu markerow,
  * menu hackowania,
  * `hackingAction(...)`,
  * `mapAction(...)`,
  * `markerMenuAction(...)`.
* Funkcje refresh mapy zwracaja teraz `true/false`, aby boot mogl rozpoznac
  realnie zaladowany critical scope.

### Najwazniejsza decyzja

Preloader mapy jest czescia kontraktu runtime, nie ozdoba. Dopoki critical map
scopes nie sa zaladowane, interakcje gameplayowe mapy pozostaja zablokowane.

### Ograniczenia

* Sprint 71 nie przyspiesza jeszcze endpointow mapy.
* Target snapshot na pierwszym bootcie korzysta z pierwszego renderu HTML/Folium
  i target registry, bez nowego backendu.
* Optional scopes moga dosynchronizowac sie chwile pozniej.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`,
  OK.
* `python -c "from run import app; c=app.test_client(); c.post('/', data={'username':'admin','password':'1234'}); r=c.get('/map'); print(r.status_code); print(len(r.get_data()))"`,
  OK, `/map` zwrocilo `200`.
* `git diff --check`,
  OK.

### Status

Sprint 71 zaimplementowany. Mapa ma teraz critical boot gate i blokade akcji do
czasu zaladowania krytycznych scope'ow.

---

## 07.07.2026

### Etap

Ghost Hack Radio - stream contract correction.

### Cel

Zmienic `ghost_streem_1` z recznej playlisty na radiowy stream budowany z plikow
MP3 lezacych w katalogu kanalu.

### Co zostalo wykonane

* `meta.channel` pierwszego kanalu nie trzyma juz `tracks[]`.
* Dodano pola:
  * `mode: "random"`,
  * `sort: "name"`,
  * `exclude: []`.
* Dodano lekki resolver:
  * `GET /api/radio/channel/<channel_id>`.
* Resolver:
  * czyta `meta.channel`,
  * listuje lokalne pliki `.mp3` z katalogu kanalu,
  * pomija pliki z `exclude`,
  * sortuje wedlug `sort`,
  * zwraca read model dla frontendu.
* `GhostRadio.loadChannel(...)` korzysta z resolvera, a nie z recznego
  `tracks[]`.
* Dla `mode = random` kolejka jest mieszana, a startowy utwor wybierany losowo.
* Przyciski playera zostaly zmienione na ikony.
* Przyciski poprzedni/nastepny sa traktowane jako przyszle przelaczanie kanalow,
  a nie jako reczne skipowanie piosenek.

### Najwazniejsza decyzja

Ghost Hack Radio nie jest klasycznym playerem playlisty. `ghost_streem_1` dziala
jak stream radiowy: kanal definiuje zasady, a utwory pochodza z katalogu kanalu.

### Status

Hotfix kontraktu radia gotowy. Kolejne kanaly moga korzystac z tego samego
modelu `meta.channel + katalog MP3`.

---

## 07.07.2026

### Etap

Sprint 72 - Hack Action Flow Lifting.

### Cel

Skrocic sciezke:

```text
klik na mapie
↓
wybor narzedzia
↓
Uzyj
↓
wynik
```

bez przebudowy backendu i bez ruszania algorytmu `/hack-action`.

### Przyczyna

Audyt pokazal, ze przy wielu pasujacych aplikacjach backend juz zwraca
`matching_apps`, ale frontend otwieral pelny File Manager. To powodowalo
dodatkowy pelny `/api/profile`, `sync_session_profile()`, render katalogu
`/tools` i dopiero potem klik `Uzyj`.

### Co zostalo wykonane

* Dodano lekki picker narzedzia dla `tool_selection_required`.
* `openToolSelectionForMapAction(...)` korzysta teraz z pickera opartego o
  `matching_apps`, a nie z domyslnego `createFileManager(...)`.
* File Manager zostal zachowany jako opcja pomocnicza `Pokaz w plikach`.
* `Uzyj` nadal wysyla istniejacy `/hack-action` z `selected_app_id`.
* Klik `Uzyj` blokuje przyciski na czas requestu, zeby uniknac double-click.
* Po sukcesie target bar jest aktualizowany z payloadu `target`, bez
  wymuszonego pelnego `refreshToolbarProfile()`.
* Dodano style `map-tool-picker-*` dla desktopu i mobile/narrow.

### Najwazniejsza decyzja

File Manager pozostaje miejscem przegladania plikow, ale nie jest juz domyslnym
pickerem narzedzia dla akcji mapowej. Jesli backend zwrocil `matching_apps`,
frontend ma wystarczajacy read model do szybkiego wyboru narzedzia.

### Testy

* `node --check static/js/terminal.js`,
  OK.
* `git diff --check`,
  OK, tylko ostrzezenia CRLF/LF dla edytowanych plikow.

### Status

Sprint 72 zaimplementowany. Domyslna sciezka wyboru narzedzia nie powinna juz
czekac na pelny File Manager ani pelny profil.

---

## 08.07.2026

### Etap

Plan Sprintu 72.1 - Hack Action Lightweight Preflight.

### Powod

Pomiary `HACK_FLOW` pokazaly, ze frontendowy picker Sprintu 72 renderuje sie w
kilka milisekund, ale pierwszy `/hack-action` nadal traci ok. 4-5 sekund na
`sync_session_profile()`, mimo ze przy `tool_selection_required` endpoint ma
tylko zwrocic liste `matching_apps`.

Po zmianie Gunicorna z 1 na 3 workery zniknal najwiekszy korek requestow, ale
pozostal koszt samego read-only preflightu.

### Decyzja

Dopisano Sprint 72.1 jako maly sprint optymalizacyjny:

* bez nowego endpointu,
* bez zmiany kontraktu frontendu,
* bez przebudowy backendu,
* z lekkim readonly preflightem dla `/hack-action` bez `selected_app_id`,
* z pelna sciezka wykonania zachowana dla `/hack-action` z `selected_app_id`.

### Oczekiwany efekt

Pierwszy request pokazujacy picker narzedzi ma omijac kosztowny pelny sync, jesli
nie jest potrzebny do samego wyboru narzedzia.

### Implementacja

Sprint 72.1 zostal zaimplementowany w `/hack-action`.

Dodano readonly preflight dla requestu bez `selected_app_id`:

* uzywa `load_profile_readonly(..., normalize_files=False)`,
* sprawdza podstawowe blokady celu,
* matchuje aplikacje przez `get_apps_for_map_action(...)`,
* przy wielu aplikacjach zwraca `tool_selection_required` bez
  `sync_session_profile()`,
* nie tworzy operacji,
* nie dopisuje `launch_queue`,
* nie zapisuje profilu.

Sciezka z `selected_app_id` pozostaje realnym wykonaniem akcji i nadal zapisuje
profil/operacje jak dotychczas.

### Testy

* Dodano test regresyjny `test_hack_action_tool_selection_uses_readonly_preflight`.
* Test potwierdza, ze preflight:
  * zwraca `tool_selection_required`,
  * uzywa readonly profilu,
  * nie wywoluje `sync_session_profile()`,
  * nie tworzy operacji.
* `python -m unittest tests.test_target_persistence.TargetPersistenceHelpersTest.test_hack_action_tool_selection_uses_readonly_preflight ...`,
  OK.
* `python -m py_compile run.py`,
  OK.
* `git diff --check`,
  OK, tylko ostrzezenie CRLF/LF dla `run.py`.

### Status

Sprint 72.1 gotowy. Pierwszy request wyboru narzedzia powinien teraz pokazywac
picker bez pelnego kosztownego syncu profilu.

---

## 08.07.2026

### Etap

Sprint 73 - Map Poller Guard + Hack Action Priority.

### Powod

Po optymalizacji `/hack-action` i przejsciu produkcji na wiecej workerow nadal
widac bylo, ze ciezkie snapshoty mapy potrafia wejsc w kolejke w tym samym
momencie co akcja gracza:

* `/api/map/player-areas`,
* `/api/map/clan-vulnerabilities`,
* `/api/operations?summary=1`,
* `/api/map/player-actors`.

To nie byl juz problem samego pickera, tylko synchronizacji runtime mapy:
pollery mogly nakladac sie na siebie i na klikniecie akcji.

### Implementacja

Dodano lekka warstwe kontroli snapshotow mapy po stronie frontendu:

* wspolny `mapRefreshState` z `inFlight`, `controllers`, `paused`,
  `pauseReason`,
* `fetchMapSnapshot(...)` z guardem przed rownoleglym requestem tego samego
  scope,
* timeout/abort dla opcjonalnych snapshotow,
* `pauseMapOptionalRefresh(...)` i `resumeMapOptionalRefresh(...)`,
* staggerowany start pollerow po boot mapy,
* pauze opcjonalnych snapshotow podczas pierwszego `/hack-action`,
* pauze opcjonalnych snapshotow podczas `Uzyj` z lekkiego pickera narzedzia.

Zmieniono tez interwaly najciezszych snapshotow:

* player actors: 30 s,
* player areas: 20 s,
* clan vulnerabilities: 20 s,
* active operations: 15 s.

### Decyzja

Sprint 73 nie migruje `player areas`, `clan vulnerabilities` ani `operations`
na delty. Snapshoty zostaja jako start/recovery. Zmiana dotyczy tylko tego, aby
snapshoty nie blokowaly akcji gracza i nie dublowaly sie, gdy poprzedni request
jeszcze trwa.

### Status

Sprint 73 gotowy do walidacji live. Kolejny checkpoint powinien sprawdzic, czy
podczas klikniecia akcji mapowej w logach nie pojawia sie nowa fala ciezkich
snapshotow startujaca rownolegle z `/hack-action`.

---

## 08.07.2026

### Etap

Sprint 73.1 - Map Hack Action Spinner.

### Powod

Po przyspieszeniu sciezki map action brakowalo malego, natychmiastowego sygnalu
wizualnego na samym obiekcie w czasie uruchamiania narzedzia. Aktywne operacje
maja juz wlasne dobre markery z ikona, glow i czasem, wiec spinner nie powinien
byc podpinany do lifecycle operacji.

### Implementacja

Dodano lekka warstwe spinnerow hack-action przy targetach mapy:

* przy starcie `/hack-action` mapa pokazuje spinner przy markerze celu,
* przy `Uzyj` z pickera desktop przekazuje do mapy start spinnera dla tego
  samego flow,
* spinner znika w `finally` requestu `/hack-action`,
* jesli backend zwroci `tool_selection_required`, spinner znika przed pokazaniem
  pickera,
* kilka rownoleglych requestow na jednym celu rozklada sie jako kilka malych
  spinnerow wokol
  markera,
* markery aktywnych operacji nie dostaja dodatkowych spinnerow.

### Decyzja

Spinner nie jest nowym systemem operacji i nie jest wizualizacja
`active_operations`. To tylko krotki sygnal UX: request narzedzia jest w toku.
Zrodlem prawdy dla dlugich operacji pozostaja istniejace markery operacji.

### Status

Sprint 73.1 gotowy do walidacji live. Test reczny powinien obejmowac klikniecie
akcji bez pickera oraz `Uzyj` z pickera. Spinner powinien pojawic sie na czas
requestu i zniknac, gdy gracz dostanie wynik `Udalo sie`, blad albo ekran wyboru
narzedzia.

---

## 08.07.2026

### Etap

Checkpoint refactoru wydajnosciowego po 23 sprintach.

### Obserwacja

Po 23 sprintach refactoryzacji pojawil sie pierwszy wyraznie odczuwalny efekt
wydajnosciowy w gameplayu.

Gra reaguje szybciej, mapa mniej blokuje akcje gracza, a wczesniejsze
porzadkowanie backendu, endpointow i synchronizacji zaczelo przekladac sie na
realna responsywnosc.

### Wniosek

Checkpoint potwierdza, ze kierunek refactoru byl wlasciwy. Dalsze optymalizacje
mapy i pollerow maja juz sens, bo system stal sie wystarczajaco uporzadkowany,
zeby zyski byly widoczne w live gameplayu.

---

## 08.07.2026

### Etap

Sprint 73.2 - Map Scan Overlay.

### Powod

Po przyspieszeniu map action i dodaniu spinnerow hack-action brakowalo jeszcze
czytelnego, ale subtelnego feedbacku dla zwyklego skanu mapy. Gracz po kliknieciu
`Skanuj` powinien widziec, ze mapa czeka na odpowiedz `/map-action` i zaraz
wyrenderuje markery.

### Implementacja

Dodano lekki overlay skanowania mapy:

* overlay startuje tylko dla `mapAction('scan')`,
* efekt uzywa delikatnej siatki i cienkiego przechodzacego gradientu,
* overlay ma `pointer-events: none`, wiec nie blokuje mapy,
* wygaszenie jest opoznione do kolejnych klatek renderu, zeby markery skanu
  zdazyly pojawic sie przed zniknieciem efektu,
* nie zmieniono backendu, algorytmu skanu ani markerow aktywnych operacji.

### Status

Sprint 73.2 gotowy do walidacji live. Test reczny: kliknac `Skanuj`, sprawdzic
czy overlay pojawia sie podczas requestu i znika dopiero po pojawieniu sie
markerow skanu.

---

## 09.07.2026

### Etap

CHAOS Terminal - system terminal polish.

### Implementacja

Dostosowano terminal systemowy do poziomu CHAOS:

* terminal mobile ma dolny composer podnoszony nad klawiature ekranowa,
* klikniecie w okno terminala ustawia fokus w inputcie,
* komendy maja jednolity font i poprawne zawijanie dlugiego tekstu,
* dodano animowany loader odpowiedzi terminala,
* dodano podstawowy zestaw komend systemowych i sieciowych,
* `exit` zamyka aktywne okno terminala,
* `logout` wylogowuje z gry.

### Status

Temat terminala systemowego zamkniety na obecny etap. Terminal jest teraz
narzedziem gameplayowym, a nie tylko launcherem aplikacji.

---

## 09.07.2026

### Etap

ABOUT CHAOS - opis gry w File Managerze.

### Implementacja

Podpieto opis gry jako aktualizowalny dokument czytany bezposrednio z pliku:

* dodano statyczny plik `static/files/about/chaos.ptk`,
* File Manager pokazuje katalog `/about`,
* katalog `/about` zawiera dokument `chaos.ptk`,
* dokument jest ladowany z pliku przez frontend,
* zawartosc Markdown renderuje sie w grze jako naglowki, listy, pogrubienia i
  bloki kodu,
* backend pozostal bez zmian.

### Status

Opis CHAOS moze byc aktualizowany przez podmiane pliku
`static/files/about/chaos.ptk`. Po odswiezeniu gry File Manager renderuje nowa
wersje dokumentu.

---

## 09.07.2026

### Etap

Login/Register polish + password hardening.

### Implementacja

Wykonano ogolny lifting wejscia do gry:

* dodano favicon CHAOS,
* odswiezono tytuly stron wejscia, mapy i terminala,
* przebudowano bramke logowania na responsywny widok Ghost Gate,
* dodano backendowa walidacje loginu, e-maila, nicku i hasla,
* zsynchronizowano frontendowa walidacje rejestracji z backendem,
* nowe hasla sa zapisywane jako `pbkdf2_sha256` z per-user salt,
* stare plaintext hasla pozostaja kompatybilne i sa migrowane do hasha przy
  pierwszym poprawnym logowaniu.

### Status

Wejscie do gry jest czytelniejsze na desktop/mobile, a nowe konta nie zapisuja
juz hasel jako surowego tekstu.

---

## 10.07.2026

### Etap

Faza H - BlackNet Prototype Runtime plan.

### Dokumentacja

Rozpisano plan Sprintow 74-80 w `doc/game_play_260626.md` na podstawie
prototypu:

* `static/js/bn_page.tsx`,
* `static/css/globals.css`.

Plan zaklada, ze BlackNet powstaje jako warstwa sygnalow swiata CHAOS, a nie
jako drugi system misji, drugi market, drugi feed powiadomien ani osobny frontend
runtime.

### Decyzje

* Prototyp trzeba przepisac do architektury CHAOS, nie wklejac jako obcy
  Next/React runtime.
* Najpierw powstaje audyt i kontrakt `blacknet_signal`.
* Dopiero pozniej shell aplikacji, signal UI, CTA bridge, lokalne zrodlo danych,
  read model swiata i polish.
* Kazdy sprint Fazy H ma obowiazkowa aktualizacje dokumentacji.

### Status

Faza H jest gotowa do rozpoczecia od Sprintu 74.

---

## 10.07.2026

### Etap

Sprint 74 - BlackNet Prototype Audit + Contract.

### Dokumentacja

Wykonano audyt prototypu BlackNet:

* `static/js/bn_page.tsx`,
* `static/css/globals.css`.

Dodano artefakt:

* `doc/blacknet_prototype_audit.md`.

Zaktualizowano:

* `doc/blacknet.md`,
* `doc/game_play_260626.md`,
* `doc/project_journal.md`.

### Ustalenia

* BlackNet v0 jest signal bus, nie forum, nie drugi market i nie drugi system
  misji.
* Prototyp trzeba przepisac do natywnej architektury CHAOS zamiast wklejac
  Next/React runtime.
* Dane opisuje kontrakt `blacknet_signal`.
* CTA moga prowadzic tylko do istniejacych systemow: mapa, Ghost Exchange,
  Googleplex, Cyberner i Ghost Hack Radio.
* W prototypie wykryto mojibake w copy, globalny CSS oraz hardcoded signals.

### Status

Sprint 74 zakonczony dokumentacyjnie. Runtime BlackNet nie zostal wdrozony.
Kolejny krok: Sprint 75 - BlackNet Static App Shell.

---

## 10.07.2026

### Etap

Sprint 75 - BlackNet Static App Shell.

### Zmiany

Dodano pierwszy fizyczny shell BlackNetu w runtime gry:

* BlackNet jest trzecim tabem WebDragons obok Googleplex i Ghost Exchange.
* Widok jest statyczny, oparty o natywny HTML/CSS/JS CHAOS.
* Zachowano elementy prototypu: radar, signal cards, timer, stat/value i CTA.
* CTA pozostaja nieaktywne do Sprintu 77.
* CSS zostal scopingowany klasami `blacknet-*`.

### Decyzje

Nie dodano osobnej aplikacji desktopowej ani wpisu do `app_contract.md`.
Na tym etapie najbezpieczniejszym miejscem wejscia jest WebDragons.

Nie dodano backendu, endpointow, AI, lokalnego zrodla danych ani drugiego
frontend runtime.

### Status

Sprint 75 zakonczony. BlackNet ma miejsce w WebDragons i moze byc rozwijany w
Sprint 76 jako signal UI v0.

---

## 10.07.2026

### Etap

Sprint 76 - BlackNet Signal UI v0.

### Zmiany

Dopolerowano BlackNet jako frontendowy signal carousel:

* dodano aktywny sygnal w hero panelu,
* dodano nawigacje strzalkami w UI,
* dodano obsluge `ArrowLeft` / `ArrowRight`,
* dodano pointer swipe / drag,
* aktywna karta sygnalu ma wyrozniony stan,
* radar ma subtelny sweep i pulsujace node'y,
* dodano signal strength,
* search filtruje lokalne sygnaly bez requestow backendowych.

### Decyzje

CTA pozostaja widoczne, ale disabled. Aktywne przejscia do mapy, Ghost
Exchange, Googleplex, Cybernera i radia zostaja dla Sprintu 77.

Nie dodano backendu, AI, lokalnego zrodla danych ani osobnego runtime.

### Status

Sprint 76 zakonczony. BlackNet ma pierwszy czytelny signal UI w WebDragons.

---

## 10.07.2026

### Etap

Sprint 76.1 - BlackNet Prototype Mechanics Alignment.

### Zmiany

Skorygowano BlackNet zgodnie z prototypem:

* widok dziala jak signal roll, a nie lista kart,
* sygnaly przesuwaja sie w cztery strony,
* dziala swipe / drag we wszystkich kierunkach,
* dziala klawiatura WASD i strzalki,
* radar, layouty i CTA zostaly przepisane na natywny JS/CSS CHAOS wedlug
  prototypu.
* usunieto wyszukiwarke z widoku Ghost Exchange,
* BlackNet ukrywa stary header WebDragons, wallet, taby i search,
* przejscia do Googleplexa i Ghost Exchange sa teraz malymi przyciskami pod
  logo BlackNetu.

### Decyzje

BlackNet nie jest drugim Googleplexem, drugim Ghost Exchange ani katalogiem
ofert. Na tym etapie jest frontendowym signal bus z lokalnymi sygnalami.

CTA tylko oznacza lokalne przechwycenie sygnalu. Mosty do mapy, Ghost Exchange,
Googleplexa, Cybernera i radia zostaja w Sprincie 77.

### Status

Sprint 76.1 zakonczony. Runtime zostal dopasowany do prototypu bez zmian
backendu.

---

## 11.07.2026

### Etap

Sprint 77 - BlackNet CTA Bridge v0.

### Zmiany

Podpieto CTA aktywnego sygnalu BlackNetu do istniejacych systemow gry:

* sygnaly dostaly pole `cta_action`,
* `open_googleplex` przelacza na istniejacy tab Googleplex,
* `open_ghost_exchange` przelacza na istniejacy tab Ghost Exchange,
* `open_map`, `open_cyberner` i `open_radio` korzystaja z istniejacego
  launchera aplikacji systemowych,
* male przyciski `GGPL` i `GX` pod logo nadal dzialaja jako szybkie przejscia
  w WebDragons,
* CTA bez bezpiecznego targetu pokazuje warning/disabled state zamiast udawac
  aktywna funkcje.

### Decyzje

CTA wybiera akcje po kontraktowym `cta_action`, nie po tekscie przycisku.
BlackNet nadal nie tworzy misji, zadan, endpointow, drugiego rynku ani drugiego
notification flow.

### Status

Sprint 77 zakonczony. BlackNet potrafi prowadzic do istniejacych systemow CHAOS,
ale pozostaje signal bus, a nie osobnym systemem gameplayu.

---

## 11.07.2026

### Etap

Sprint 78 - BlackNet Local Signal Source.

### Zmiany

Przeniesiono sygnaly BlackNetu z `terminal.js` do lokalnego kontraktu:

* dodano `static/blacknet_signals.json`,
* plik ma `schema: 1` i liste `signals[]`,
* sygnal zawiera `cta_action`, `cta_target`, `tone`, `layout` oraz `radar`,
* `radar.sides` i `radar.nodes` zastepuja dane radarowe zaszyte w rendererze,
* `terminal.js` laduje i normalizuje lokalne zrodlo przy wejsciu w tab BlackNet,
* blad wczytania pokazuje pusty stan BlackNetu zamiast rozbijac WebDragons.

### Decyzje

BlackNet nadal nie ma backendu, AI, endpointu ani pollera. Sprint 78 zmienia
tylko zrodlo danych sygnalow, nie silnik layoutu 76.1 i nie CTA bridge 77.

### Status

Sprint 78 zakonczony. BlackNet ma lokalny kontrakt danych gotowy pod przyszly
read model Sprintu 79.

---

## 11.07.2026

### Etap

Sprint 79 - BlackNet World Read Model Prep.

### Zmiany

Opisano przyszly read model `blacknet_world_digest`:

* dodano `doc/blacknet_world_read_model.md`,
* wskazano zrodla faktow: Ghost Exchange, operacje, mapa/regiony, PvP,
  Cyberner/System Messages i radio channels,
* opisano kontrakt `digest fact`,
* opisano mapowanie `digest fact -> blacknet_signal`,
* opisano mapowanie `source -> tone/CTA` oraz `severity -> priority`,
* dopisano zasady retencji i fallback do lokalnego
  `static/blacknet_signals.json`.

### Decyzje

`blacknet_world_digest` jest read modelem, nie zrodlem prawdy i nie drugim
magazynem stanu. BlackNet nie liczy statystyk swiata w requestcie, nie odpala
`sync_session_profile()`, nie dostaje pollera i nie generuje tresci AI w tym
sprincie.

### Status

Sprint 79 zakonczony dokumentacyjnie. BlackNet jest gotowy koncepcyjnie na
przyszle zasilanie faktami swiata bez psucia stabilnego silnika 76.1-78.

---

## 11.07.2026

### Etap

Sprint 80 - BlackNet Polish + Readiness Check.

### Zmiany

Domknieto pierwszy etap BlackNetu jako stabilny lokalny front informacyjny:

* dodano `doc/blacknet_readiness_check.md`,
* opisano aktualny przeplyw lokalnych sygnalow,
* opisano checkpointy responsive dla WebDragons,
* opisano zasady CTA bridge i fallbackow,
* usunieto martwy blok starego `.blacknet-*` shell/carousel ze `style.css`,
* zostawiono `blacknet.css` jako jedyne aktywne zrodlo styli `.blacknet-stage`
  i `.bn-*`.

### Decyzje

BlackNet v0 nie jest misjami, drugim marketem, drugim Googleplexem ani drugim
Ghost Exchange. Jest lokalnym signal frontem, ktory w przyszlosci moze dostac
fakty swiata przez digest/cache/delta-feed.

### Status

Sprint 80 zakonczony. Faza H ma stabilny BlackNet v0 gotowy pod przyszle
mini-sprinty: AI Digest, Radio Hooks, Cyberner Thread i Market Rumors.

---

## 11.07.2026

### Etap

Sprint 81 - BlackNet World Facts Snapshot.

### Zmiany

Dodano pierwszy runtime read model faktow swiata dla BlackNetu:

* endpoint `GET /api/blacknet/world-facts`,
* builder `build_blacknet_world_facts_snapshot()`,
* kontrakt `blacknet_world_facts` z `schema`, `version`, `generated_at`,
  `expires_at`, `source_versions`, `facts[]` i `diagnostics`,
* osobny dokument `doc/blacknet_world_facts.md`,
* testy regresyjne kontraktu, odpornosci na awarie zrodla i braku
  `sync_session_profile()` w endpointzie.

Snapshot agreguje lekkie fakty z:

* zapisanych operacji profili,
* historii sprzedazy Ghost Exchange,
* katalogu Googleplex,
* lokalnych kontraktow Ghost Hack Radio,
* licznikow system messages.

### Decyzje

`blacknet_world_facts` jest read-only snapshotem i nie jest zrodlem prawdy.

Nie generuje sygnalow BlackNetu, nie uruchamia Ollamy, nie odpala settlementu
Ghost Exchange, nie finalizuje operacji, nie przebudowuje mapy i nie czyta
pelnych prywatnych danych graczy do payloadu.

Awaria jednego zrodla trafia do `diagnostics.sources`, ale nie blokuje calego
snapshotu.

### Status

Sprint 81 zakonczony jako fundament pod Sprint 82. BlackNet UI nadal korzysta z
lokalnego `static/blacknet_signals.json`; nowy snapshot faktow jest gotowy dla
przyszlego deterministycznego publishera.

---

## 11.07.2026

### Etap

Sprint 82 - Deterministic World Signal Publisher.

### Zmiany

Dodano deterministyczny publisher sygnalow BlackNetu:

* endpoint `GET /api/blacknet/world-signals`,
* builder `build_blacknet_world_signals()`,
* reguly `fact_type -> signal_type`,
* progi publikacji,
* ranking po waznosci,
* deduplikacje w ramach snapshotu,
* wygaszanie faktow po `expires_at`,
* bezpieczne CTA przez allowliste `cta_action`,
* `source: world_generated` dla sygnalow z faktow swiata,
* merge `world_generated + static/blacknet_signals.json` w rendererze BlackNetu.

### Decyzje

Publisher nie jest nowym store i nie jest zrodlem prawdy. Czyta snapshot
`blacknet_world_facts` ze Sprintu 81 i generuje prezentacyjny kontrakt
`blacknet_world_signals`.

Nie uzyto Ollamy, nie dodano outboxa, nie utworzono misji, nie zmieniono
Ghost Exchange, Googleplexa ani mapy.

Brak faktow powyzej progu nie generuje sztucznego ruchu. W takim przypadku UI
dalej dziala na lokalnych sygnalach statycznych.

### Status

Sprint 82 zakonczony jako pierwszy moment, w ktorym BlackNet moze opisywac
rzeczywisty stan swiata gry deterministycznymi sygnalami.

---

## 11.07.2026

### Etap

Sprint 82.5 - BlackNet CTA Triggers + Gameplay Bridges.

### Zmiany

Dodano centralny router CTA dla sygnalow BlackNetu:

* routing po `cta_action`, bez parsowania tekstu przycisku,
* rozszerzona allowlista `BLACKNET_ALLOWED_CTA_ACTIONS`,
* diagnostyka CTA w konsoli z `signal_id`, `source`, `cta_action`,
  `cta_target`, walidacja, potwierdzeniem i czasem obslugi,
* most do Googleplexa z wypelnieniem wyszukiwarki,
* most do Ghost Exchange,
* most do mapy z lekkim hintem fokusu,
* most do Cybernera przez istniejace `openEmailChatWith(peer)`,
* most do Ghost Hack Radio,
* kontrolowane szczegoly wewnetrzne BlackNetu przez istniejace system messages,
* kontrolowane potwierdzenia dla teleportu, startu operacji i przyjecia joba.

Dodano dokument:

```text
doc/blacknet_cta_bridges.md
```

### Decyzje

BlackNet nie tworzy drugiego routera zakupow, rynku, operacji, mapy, Cybernera
ani audio.

Akcje mutujace stan swiata wymagaja potwierdzenia. Jezeli obecny runtime nie ma
bezpiecznego backendowego mostu, akcja konczy sie kontrolowanym komunikatem i nie
zmienia swiata.

`play_radio_podcast` uzywa `GhostRadio.playPodcast()` tylko wtedy, gdy taki
istniejacy most bedzie dostepny. W przeciwnym razie otwiera radio i zwraca
kontrolowany komunikat.

### Hotfix po walidacji

Po pierwszej walidacji CTA okazalo sie, ze czesc akcji nadal korzystala z
ogolnych targetow albo fallbackowych hasel sygnalu:

* radio traktowalo `cta_target=radio` jak identyfikator kanalu,
* Googleplex mogl szukac plakatowego tytulu sygnalu zamiast realnej nazwy
  produktu,
* teleport otwieral mape bez potwierdzenia i bez zmiany pozycji,
* lokalny fallback `static/blacknet_signals.json` mial jeszcze mockowe akcje
  typu `open_map`.

Poprawiono kontrakt CTA:

* publisher dodaje `cta_target_id`, `cta_query` i bezpieczne `metadata`,
* fakty Googleplexa niosa realny `product_id` / `product_name`,
* fakty radia niosa realny `channel_id`,
* lokalny fallback dostal konkretne targety,
* dodano whitelistowany most `POST /api/blacknet/cta/teleport`, ktory po
  potwierdzeniu aktualizuje istniejace `profile.curently_possition` i emituje
  istniejacy delta event map actor.

### Status

Sprint 82.5 domyka bezpieczne przejscie z sygnalu BlackNetu do istniejacych
systemow CHAOS przed rozpoczeciem kontraktow Ollamy ze Sprintu 83.

---

## 11.07.2026

### Etap

BlackNet - Signal Generation Audit.

### Zmiany

Dodano dokument:

```text
doc/blacknet_signal_generation_audit.md
```

Audyt opisuje, jak obecnie powstaja sygnaly BlackNetu:

* lokalny fallback `static/blacknet_signals.json`,
* runtime facts `blacknet_world_facts`,
* deterministic publisher `blacknet_world_signals`,
* mapowanie rodzin sygnalow,
* pochodzenie `title`, `label`, `value`, `stat`, `timer`, `radar`, `cta`,
* roznice miedzy statycznym `HOTSPOT / MOKOTOW` a sygnalami runtime.

### Decyzje

`HOTSPOT / MOKOTOW` ze screena jest obecnie sygnalem fallbackowym. Jego wartosci
`240%`, `17 AKTYWNYCH OPERACJI` i `04:32` sa wpisane w statycznym kontrakcie,
nie liczone jeszcze z regionalnego runtime.

Runtime ma juz globalne rodziny operacji, rynku, Googleplexa, radia i system
messages, ale nie ma jeszcze modelu `regional_hotspot_activity`.

### Status

Dokument wskazuje kolejny naturalny krok: dodac runtime read model regionalnych
hotspotow, zeby BlackNet mogl generowac `HOTSPOT / MOKOTOW` z realnych danych
zamiast lokalnego fallbacku.

---

## 11.07.2026

### Etap

BlackNet - Sprinty 82.6-82.9 real signal cutover plan.

### Zmiany

Uzupełniono `doc/game_play_260626.md` o cztery minisprinty pomiędzy Sprintem
82.5 a Sprintem 83:

* Sprint 82.6 - BlackNet Real Activity Snapshot + Out Of Signal Gate,
* Sprint 82.7 - BlackNet Map + Conflict Signal Generators,
* Sprint 82.8 - BlackNet Entity CTA Fixes: Radio, Googleplex, GX, Cyberner,
* Sprint 82.9 - BlackNet Real Signal Cutover + Mock Retirement.

### Decyzje

BlackNet nie powinien już produkować sygnałów z mockowych dzielnic, stałych
procentów ani plakatowych wartości, jeśli brak realnych danych gry.

Zamiast mapować ręcznie miasta i dzielnice albo używać zewnętrznego API,
sygnały mapowe mają korzystać z istniejących obiektów CHAOS:

* aktywnych operacji,
* targetów / filarów emitujących operacje,
* konfliktów,
* contested areas,
* realnych współrzędnych targetu, jeśli są dostępne.

Jeżeli rodzina sygnałów nie ma realnych faktów, BlackNet ma pokazać
`out_of_signal` i czekać na ruch świata zamiast podstawiać lokalny mock.

CTA po Sprintach 82.6-82.9 mają prowadzić do realnych encji:

* radio - konkretny kanał i konkretny MP3,
* Googleplex - realny produkt z katalogu i jego cenę,
* Ghost Exchange - poprawny sektor rynku,
* Cyberner - kanał `WORLD`, nie fikcyjny kontakt `cyberner`.

### Status

Sprint 83 z kontraktem Ollamy powinien startować dopiero po domknięciu realnych
generatorów i odcięciu produkcyjnych mocków. Ollama ma dostać realny feed
świata, a nie statyczne plakaty z `static/blacknet_signals.json`.

---

## 11.07.2026

### Etap

Sprint 82.6 - BlackNet Real Activity Snapshot + Out Of Signal Gate.

### Zmiany

Dodano pierwszy realny fakt aktywności targetów dla BlackNetu:

```text
operation_hotspot_activity
```

Fakt powstaje z aktywnych operacji przypiętych do realnego targetu mapy. Używa
nazwy targetu, `target_id`, współrzędnych oraz liczby aktywnych operacji.

Dodano krótki cache TTL dla `blacknet_world_facts`, dzięki czemu BlackNet działa
jak lekki daemon/read model pobudzany ruchem, a nie jak ciężki rebuild przy
każdym otwarciu taba.

Publisher `blacknet_world_signals` dostał jawny stan:

```text
out_of_signal
```

Jeżeli nie ma publikowalnych realnych faktów, BlackNet pokazuje brak sygnału
zamiast mieszać lokalne mocki.

Frontend nie dokleja `static/blacknet_signals.json`, gdy world feed świadomie
zwróci `out_of_signal`.

### Decyzje

Mockowe dzielnice typu `MOKOTOW` nie są już kierunkiem dla nowych sygnałów
runtime. BlackNet ma opisywać realne obiekty CHAOS: targety, operacje,
konflikty i istniejące encje świata.

Stary whitelistowany teleport do `BLACKNET_HOTSPOTS` pozostaje kompatybilnie do
czasu Sprintów 82.7-82.8, ale nowe fakty 82.6 nie korzystają z tych mockowych
hotspotów.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`
* `node --check static/js/terminal.js`
* `python -m unittest tests.test_target_persistence.BlackNetWorldFactsSnapshotTest tests.test_target_persistence.BlackNetWorldSignalPublisherTest`

### Status

Sprint 82.6 zakończony. BlackNet ma realny fundament aktywności operacyjnej i
kontrolowany stan braku sygnału. Sprint 82.7 może budować na tym pełne generatory
map/conflict bez dokładania mockowych regionów.

---

## 11.07.2026

### Etap

Sprint 82.7 - BlackNet Map + Conflict Signal Generators.

### Zmiany

Dodano mapowe rodziny faktow i sygnalow BlackNetu:

```text
target_operation_burst
conflict_target_alert
contested_area_alert
```

`target_operation_burst` powstaje z wielu aktywnych operacji przypietych do tego
samego realnego targetu mapy.

`conflict_target_alert` powstaje z aktywnych konfliktow w
`territory_conflict_store`, jesli konflikt ma bezpieczny konkretny target.

`contested_area_alert` jest fallbackiem dla aktywnego konfliktu bez targetu i
nie zgaduje wspolrzednych.

### Decyzje

BlackNet nie tworzy katalogu dzielnic, nie odpytuje zewnetrznych API i nie
generuje lokalizacji z tekstu. Target label, `target_id` i wspolrzedne pochodza
z istniejacych danych gry.

Mapowe CTA uzywaja istniejacej akcji:

```text
focus_map_target
```

albo `open_map`, jesli nie ma bezpiecznego konkretnego targetu.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`
* `node --check static/js/terminal.js`
* `python -m unittest tests.test_target_persistence.BlackNetWorldFactsSnapshotTest tests.test_target_persistence.BlackNetWorldSignalPublisherTest`

### Status

Sprint 82.7 zakonczony. BlackNet ma realne generatory map/conflict v0. Poprawki
CTA dla Radio, Googleplex, Ghost Exchange i Cybernera zostaja w Sprincie 82.8.

---

## 11.07.2026

### Etap

Sprint 82.8 - BlackNet Entity CTA Fixes: Radio, Googleplex, GX, Cyberner.

### Zmiany

Poprawiono rodziny CTA, ktore po Sprintach 81-82 nadal dzialaly zbyt blisko
mockowych tytulow sygnalow.

Radio BlackNet wskazuje teraz konkretne:

```text
channel_id
track_file
track_index
track_title
track_count
```

Googleplex wskazuje realny produkt z katalogu:

```text
product_id
product_name
product_type
price
category
```

Ghost Exchange wskazuje realny sektor rynku i publikuje top-sector tylko dla
sektorow znanych w kontrakcie GX.

Cyberner otwiera kanal `WORLD` przez `open_cyberner_thread`, zamiast tworzyc
albo otwierac kontakt `cyberner`.

### Decyzje

Mockowy tytul sygnalu nie moze byc parametrem akcji. CTA BlackNetu musi miec
konkretna encje runtime albo nie powinno byc publikowane.

Radio korzysta z istniejacego `GhostRadio`, Googleplex z istniejacej
wyszukiwarki katalogu, Ghost Exchange z istniejacego dashboardu sektorow, a
Cyberner z istniejacego kanalu WORLD.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`
* `node --check static/js/terminal.js static/js/ghost_radio.js`
* `python -m unittest tests.test_target_persistence.BlackNetWorldFactsSnapshotTest tests.test_target_persistence.BlackNetWorldSignalPublisherTest`
* `git diff --check`

### Status

Sprint 82.8 zakonczony. BlackNet ma gotowe mosty CTA dla encji Radio,
Googleplex, Ghost Exchange i Cyberner. Sprint 82.9 moze zajac sie real signal
cutover i emerytura mockow.

---

## 11.07.2026

### Etap

Sprint 82.9 - BlackNet Real Signal Cutover + Mock Retirement.

### Zmiany

Przelaczono normalny runtime BlackNetu na realny feed:

```text
/api/blacknet/world-signals
```

Frontend nie pobiera juz domyslnie `static/blacknet_signals.json`.

Lokalny plik sygnalow pozostaje tylko jako fixture dev/demo i wymaga jawnej
flagi:

```text
?blacknet_demo=1
?blacknet_static=1
localStorage.blacknet_static_signals = "1"
window.BLACKNET_STATIC_SIGNAL_FIXTURE = true
```

Jezeli world feed jest pusty, niedostepny albo nie zawiera poprawnych sygnalow,
UI pokazuje `OUT OF SIGNAL`, zamiast mieszac plakatowe mocki z realnym runtime.

### Decyzje

Mocki nie sa juz produkcyjnym zrodlem sygnalow BlackNetu.

Kazdy realny sygnal dostaje `entity_id`, ktore opisuje konkretna encje runtime:
target, produkt, kanal radia, sektor Ghost Exchange albo kanal Cybernera.

`entity_id` nie jest tytulem wizualnym i nie moze byc zgadywane z naglowka
sygnalu.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`
* `node --check static/js/terminal.js`
* `node --check static/js/ghost_radio.js`
* `python -m unittest tests.test_target_persistence.BlackNetWorldFactsSnapshotTest tests.test_target_persistence.BlackNetWorldSignalPublisherTest`
* `git diff --check`

### Status

Sprint 82.9 zakonczony. BlackNet jest gotowy na Sprint 83 jako realny,
deterministyczny feed sygnalow dla przyszlego kontraktu Ollamy.

---

## 11.07.2026

### Etap

Audyt fix po Sprintach 82.6-82.9 - BlackNet CTA bridge integrity.

### Zmiany

Domknieto rozjazdy miedzy realnym feedem BlackNetu a starymi mockowymi mostami
CTA:

* radio laduje wskazany kanal i konkretny plik MP3 bez posredniego startu
  domyslnego kanalu,
* kanal radia w sygnale uzywa stabilnego identyfikatora katalogu, a `meta_id`
  pozostaje informacja kontraktowa,
* Googleplex dostaje query przed przelaczeniem zakladki i ponownie po
  doczytaniu katalogu,
* `POKAZ NA MAPIE` przekazuje fokus do iframe mapy i centruje mape po
  `target_id` albo po wspolrzednych z metadanych,
* teleport BlackNetu nadal obsluguje stare whitelistowane hotspoty, ale moze
  tez pracowac na realnych wspolrzednych z sygnalu.

### Decyzje

CTA BlackNetu nie moze zakladac, ze encja jest lokalnym mockiem. Mosty musza
akceptowac realne metadane `blacknet_world_facts`: `target_id`, `lat/lng`,
`product_name`, `sector_key`, `channel_id` i `track_file`.

`POKAZ NA MAPIE` nie zmienia pozycji gracza. Tylko centruje widok mapy.

Teleport zmienia pozycje profilu dopiero po potwierdzeniu w oknie decyzyjnym i
korzysta z istniejacego endpointu `/api/blacknet/cta/teleport`.

### Testy

* `python -m py_compile run.py database.py profileManagment.py`
* `node --check static/js/terminal.js`
* `node --check static/js/ghost_radio.js`
* `python -m unittest tests.test_target_persistence.BlackNetWorldFactsSnapshotTest tests.test_target_persistence.BlackNetWorldSignalPublisherTest`
* `git diff --check`

### Status

Audyt fix zakonczony. Mosty CTA sa spojne z realnym feedem 82.6-82.9 i gotowe
do dalszego etapu BlackNetu bez powrotu do produkcyjnych mockow.

### Hotfix

Naprawiono przypadek, w ktorym sygnal mapy BlackNetu mogl dostac
`map:unknown:unknown:*` jako `cta_target_id`.

Przyczyna: czesc operacji trzymala `lat/lng` na poziomie operacji, a nie w
wewnetrznym `operation.target`. Generator BlackNetu budowal wtedy target id z
niepelnego obiektu targetu.

Poprawka: `blacknet_operation_target_snapshot()` scala teraz dane celu z
operacji i uzywa wspolrzednych z operacji jako fallback. Link `POKAZ NA MAPIE`
ma dzieki temu realne `lat/lng` w metadanych i moze wycentrowac iframe mapy na
celu bez teleportu.

### Hotfix 2

Naprawiono drugi wariant problemu z fokusem mapy BlackNetu.

Przyczyny:

* sygnaly konfliktow mogly miec wspolrzedne na rekordzie konfliktu, ale nie w
  skroconym wpisie targetu,
* frontend traktowal `null` jako liczbe `0`, wiec brak `lat/lng` mogl
  przypadkowo wysylac mape na `(0, 0)`,
* sygnaly ogolne z `region_id=global` byly traktowane jak realny punkt fokusu.

Poprawka:

* target konfliktu dziedziczy teraz `lat/lng` z rekordu konfliktu,
* most BlackNet -> mapa odrzuca `null`, puste wartosci i techniczne fokusy typu
  `global`,
* Googleplex dostal kontrolowany filtr `/all`, ktory pokazuje pelny katalog bez
  wpisywania sztucznej nazwy produktu.

### Hotfix 3

Przejrzano wszystkie rodziny sygnalow BlackNetu i doprecyzowano kontrakt CTA.

Najwazniejsza poprawka: sygnaly analityczne typu `operations_active_count`,
`operations_top_type` i `contested_area_alert` otwieraja mape bez fokusu na
encje. Nie wystawiaja juz technicznych wartosci typu `persistent_sniffer` jako
`cta_target_id`.

Sygnaly punktowe pozostaja bez zmian:

* `operation_hotspot_activity`,
* `target_operation_burst`,
* `conflict_target_alert`.

Te rodziny nadal wymagaja konkretnego targetu i wspolrzednych albo markera mapy.
Dodano test kontraktu, ktory potwierdza, ze wszystkie glowne rodziny sygnalow
maja szanse sie wygenerowac i posiadaja poprawne CTA.

### Tips&Tricks

Dodano katalog `Tips&Tricks` w File Managerze, obok `About`, oparty o ten sam
mechanizm statycznych dokumentow `.ptk` renderowanych jako Markdown.

Pierwszy dokument `blacknet.ptk` opisuje, jak czytac sygnaly BlackNetu, czego
spodziewac sie po rodzinach mapy, Ghost Exchange, Googleplexa, radia, Cybernera
i teleportu oraz co oznacza stan `OUT OF SIGNAL`.

To domyka Sprint 82.9 od strony edukacji gracza: BlackNet ma teraz wbudowana
krotka instrukcje obslugi w samym systemie plikow CHAOS.

## Sprint 83 - Ollama Digest Outbox Contract

Zaimplementowano kontrolowany outbox dla przyszlego procesu Ollamy.

Dodano:

* builder `build_blacknet_ollama_outbox()`,
* walidator `validate_blacknet_ollama_outbox()`,
* atomowy zapis paczek w katalogu instancji,
* odczyt najnowszej paczki po statusie,
* jawna zmiane statusu paczki,
* endpointy:
  * `POST /api/blacknet/ollama/outbox/generate`,
  * `GET /api/blacknet/ollama/outbox/latest`,
  * `GET /api/blacknet/ollama/outbox/<digest_id>`,
  * `POST /api/blacknet/ollama/outbox/<digest_id>/status`.

Outbox powstaje z `blacknet_world_facts` i `blacknet_world_signals`. Nie jest
nowym zrodlem prawdy, nie uruchamia Ollamy i nie daje modelowi dostepu do bazy,
profilu, mapy ani systemow gry.

Paczka usuwa prywatne metadane, zachowuje `fact_id`, niesie whitelistowane
`allowed_actions`, limity tekstu, osobowosci autorow, zakazane twierdzenia i
diagnostyke walidacji.

Dokument kontraktu:

```text
doc/blacknet_ollama_outbox.md
```

Sprint 83 zamkniety jako kontrakt wyjsciowy. Sprint 84 nie startuje od razu:
przed ingestem odpowiedzi modelu trzeba domknac kanoniczny rejestr rodzin
sygnalow, stabilny kontrakt odpowiedzi Ollamy i daemonowy feedback loop.

### Hotfix - BlackNet unknown map targets

Sprawdzono zrodlo `map:unknown:unknown:*` w outboxie Ollamy.

Przyczyna: rekord konfliktu mogl zawierac target bez `lat/lng` i bez stabilnego
`target_id`. BlackNet probowal mimo to zbudowac punktowy `conflict_target_alert`
i fallback `build_operation_target_id()` skladal techniczne
`map:unknown:unknown:<label>`.

Poprawka: BlackNet nie tworzy juz punktowych target snapshotow dla operacji ani
konfliktow, jezeli nie ma ani jawnego `target_id`, ani wspolrzednych pozwalajacych
bezpiecznie zbudowac mapowy identyfikator. Taki konflikt zostaje widoczny jako
ogolny `contested_area_alert`, ale nie dostaje klikalnego fokusu mapy.

Dodano test regresyjny potwierdzajacy, ze konflikt bez wspolrzednych nie emituje
`unknown:unknown` do snapshotu faktow.

### Hotfix - BlackNet infinite signal feed

BlackNet nie zatrzymuje sie juz na jednorazowym buforze top 8 sygnalow.

Endpoint `GET /api/blacknet/world-signals` przyjmuje teraz `limit` oraz
`exclude`, dzieki czemu WebDragons moze dociagac kolejne realne sygnaly po
przechwyceniu albo wygasnieciu aktualnych.

Po stronie UI przechwycone i wygasle sygnaly wypadaja z widocznej kolejki, a
BlackNet automatycznie uzupelnia bufor nastepna paczka. Jedynym poprawnym
koncem strumienia jest sygnal `out_of_signal`.

### Hotfix - BlackNet Googleplex product signals

Googleplex w BlackNecie nie emituje juz pojedynczego syntetycznego sygnalu
katalogu jako glownej sciezki runtime.

`blacknet_world_facts` tworzy teraz osobny fakt `googleplex_product_signal` dla
kazdej opublikowanej pozycji katalogu Googleplex/pro-tools/system products.
Cena pozostaje glowna liczba sygnalu, a pobrania, swiezosc i typ produktu
buduja temperature/importance sygnalu.

Travel tickets, storage products i pro-tools sa dzieki temu zwyklymi elementami
niekonczacego sie feedu BlackNetu. CTA nadal korzysta z istniejacego Googleplexa
i wpisuje realna nazwe pozycji do wyszukiwarki.

### Hotfix - BlackNet signal family visibility

Po rozbiciu Googleplexa na osobne sygnaly produktowe katalog mogl zdominowac
pierwsza paczke `world-signals` i praktycznie schowac rodziny o nizszej wadze,
np. radio, system albo teleport.

Publisher wybiera teraz pierwsza paczke z zachowaniem roznorodnosci rodzin
`signal_type`, a dopiero potem wypelnia pozostale miejsca rankingiem waznosci.
Dzieki temu duza liczba pozycji Googleplexa nie ukrywa radia, teleportu,
Cybernera/systemu ani map/conflict signals, jezeli maja realne fakty.

Dodano tez osobna realna rodzine:

```text
operation_hotspot_teleport -> teleport_hotspot
```

Teleport nie wraca do mockowych dzielnic. Powstaje z aktywnego hotspotu operacji
z realnymi wspolrzednymi targetu i korzysta z istniejacego mostu
`teleport_to_hotspot`.

### Decision - Sprint 84 frozen

Sprint 83 zostaje zamkniety w obecnej formie jako bezpieczny outbox dla Ollamy.

Sprint 84 zostaje zamrozony / odlozony. Powod: BlackNet ma juz realny feed i
outbox, ale przed przyjeciem narracji modelu trzeba uporzadkowac kontrakt
wejsciowy, zeby Ollama nie stala sie drugim ukrytym systemem sygnalow.

Najpierw do zrobienia:

* kanoniczny rejestr rodzin `signal_type`,
* aliasowanie albo wygaszenie historycznych nazw rodzin,
* stabilny kontrakt odpowiedzi Ollamy,
* walidator kandydatow,
* kwarantanna odrzuconych kandydatow,
* daemon Ollamy pobierajacy outbox i oddajacy feedback,
* insert zaakceptowanych kandydatow do strumienia BlackNet jako
  `source: ollama_enriched`.

Zasada pozostaje twarda: Ollama nie zmienia mapy, profilu, ekonomii, Googleplexa,
Ghost Exchange ani Cybernera. Model moze proponowac narracje, ale tylko backend
CHAOS waliduje kandydatow i decyduje, czy sygnal trafi do BlackNetu.

### Sprint 85 - Response Network Safety Foundation

Przeczytano artefakty:

* `doc/incidents_npc_technical_architecture.md`,
* `doc/incidents_npc_gameplay.md`,
* `doc/runtime_slowdown_audit_blacknet.md`.

Wdrozono fundament bezpieczeństwa Response Network bez uruchamiania gameplayu
incydentow:

* tryb wdrozenia startuje jako `disabled`,
* feature flagi Response Network sa domyslnie wylaczone,
* kill switche incydentow, NPC, detekcji, konsekwencji i publikacji mapowej sa
  domyslnie zamkniete,
* dodano testowalny zegar `ResponseNetworkClock`,
* dodano lekki audit log pod decyzje i pomiary Sprintu 85,
* dodano fixture `sprint85_safety_foundation.json`,
* pomiary krytycznych endpointow mapy sa rejestrowane pasywnie przez istniejacy
  hook `PERF`, bez nowego pollingu.

Dodano dev-only endpoint:

```text
GET /api/dev/response-network-safety
```

Endpoint wymaga konta `admin`, nie odpala `sync_session_profile()` i sluzy tylko
do podgladu konfiguracji, kill switchy, fixture-ready clocka oraz metryk mapy.

Pozostaje wylaczone:

* tworzenie incydentow,
* kapsuly NPC,
* detekcja kandydatow,
* konsekwencje dla graczy,
* publikacja incydentow na mapie,
* nowy polling mapy.

### Sprint 86 - Territory Read Model

Przeczytano:

* opis Sprintu 86 w `doc/game_play_260626.md`,
* kontrakt `territory_context_reader` w
  `doc/incidents_npc_technical_architecture.md`,
* aktualny audyt wydajnosci mapy w `doc/runtime_slowdown_audit_blacknet.md`.

Wdrozono lekki, read-only `TerritoryContextReader` dla Response Network:

* `for_point(lat, lng, actor_username)` zwraca terytoria zawierajace punkt,
  wlasciciela, status, bbox i informacje o aktywnych konfliktach;
* `for_bbox(min_lat, min_lng, max_lat, max_lng)` zwraca ograniczony zestaw
  terytoriow przecinajacych podany obszar;
* `compare_point_with_legacy_area(...)` pozwala porownac wynik read modelu ze
  starym odczytem terytorium dla punktu.

Reader korzysta z istniejacych snapshotow `TerritoryStore.list_player_areas()`
oraz `TerritoryConflictStore.list_active()`. Nie wywoluje
`sync_session_profile()`, nie pobiera pelnych profili i nie przebudowuje
geometrii terytoriow.

Zgodnosc potwierdzono testami:

* punkt we wlasnym terytorium,
* punkt w obcym terytorium,
* aktywny konflikt podpiety po `area_id`,
* ograniczony bbox bez zwracania pelnych `vertices`,
* porownanie z legacy area dla tego samego punktu.

Poza zakresem pozostaje:

* wersjonowanie terytoriow,
* delty territory,
* migracja endpointu `/api/map/player-areas`,
* publikacja incydentow,
* NPC, detekcja i konsekwencje.

### Sprint 87 - Territory Versioning + Delta

Przeczytano:

* opis Sprintu 87 w `doc/game_play_260626.md`,
* sekcje territory/delta/recovery w
  `doc/incidents_npc_technical_architecture.md`,
* read model `TerritoryContextReader` wdrozony w Sprincie 86.

Wdrozono wersjonowanie i delty terytoriow przez istniejacy
`GameStateDeltaBus`, bez tworzenia osobnego feedu:

* `territory.updated` dla przebudowanych obszarow gracza;
* `territory.conflict_changed` dla aktywnych konfliktow terytorialnych;
* deduplikacje przez `dedupe_key`;
* minimalny payload bez pelnych `vertices`;
* helper `rebuild_player_areas_with_territory_delta(...)`, ktory zachowuje stara
  geometrie i tylko dopisuje event delta po istniejacym rebuildzie;
* dev-only recovery snapshot:

```text
GET /api/dev/territory-context/recovery
```

Endpoint wymaga konta `admin`, obsluguje punkt albo bbox i nie wywoluje
`sync_session_profile()`. Recovery jest per scope `territory`, a
`/api/state/changes` ma teraz `territory` na liscie recovery scopes.

Sprawdzono:

* idempotencje `territory.updated`,
* emisje `territory.conflict_changed` dla kazdego uczestnika konfliktu,
* recovery snapshot przez `TerritoryContextReader`,
* diagnostyke luki/recovery,
* brak `sync_session_profile()` w dev endpointzie recovery.

Poza zakresem pozostaje:

* przelaczenie frontendu mapy na delty terytoriow,
* migracja `/api/map/player-areas`,
* delta geometrii area/conflict layers po stronie UI,
* incydenty, NPC, detekcja i konsekwencje.

### Sprint 88 - Territory Map Migration

Przeczytano:

* opis Sprintu 88 w `doc/game_play_260626.md`,
* aktualny frontend mapy w `templates/map_template.html`,
* istniejacy delta poller w `static/js/terminal.js`,
* wyniki Sprintow 86-87.

Wdrozono pierwsza migracje mapy terytoriow na model snapshot + delta:

* startowy snapshot `/api/map/player-areas` zostaje i buduje warstwy mapy;
* snapshot tworzy registry `territoryAreaLayers` po stabilnym `territory_id`;
* `territory.updated` jest obslugiwane przez `applyTerritoryDelta()` i aktualizuje
  istniejacy polygon bez czyszczenia calej warstwy;
* `territory.conflict_changed` odpala throttlowany recovery snapshot
  `refreshPlayerAreas()`, bo geometria konfliktu nie jest payloadem delty;
* brakujacy polygon po delcie rowniez prowadzi do kontrolowanego recovery;
* globalny `applyDelta()` obsluguje scope `territory` osobno od `map`;
* recovery scope `territory` odswieza tylko terytoria, bez globalnego reloadu;
* cykliczny poller `/api/map/player-areas` po boot mapy zostal wylaczony.

Stary snapshot pozostaje sciezka startowa i awaryjna. Nie ruszano geometrii
terytoriow, zasad przejec, incydentow, NPC ani konsekwencji.

Sprawdzono:

* skladnie `static/js/terminal.js`,
* kompilacje Pythona dla `run.py`, `config.py` i modulow `response_network`,
* testy safety/read model/territory delta/delta bus,
* `git diff --check`.

Pozostaje do kolejnych sprintow:

* pelna delta geometrii konfliktow, jesli payload zostanie rozszerzony,
* porownanie live `p95` i payloadow przed/po,
* dalsze zdejmowanie ciezkich mapowych snapshotow przed incydentami.

### Sprint 89 - Operation Risk Meter

Przeczytano:

* opis Sprintu 89 w `doc/game_play_260626.md`,
* sekcje `operation_risk_meter` w
  `doc/incidents_npc_technical_architecture.md`,
* aktualny runtime operacji, finalizacji i anulowania w `run.py`.

Wdrozono wersjonowany miernik ryzyka bezposrednio na operacji:

* nowy modul `response_network.operation_risk_meter`;
* `operation_risk_meter` dodawany przy tworzeniu operacji;
* aktualizacja metera przy odswiezaniu runtime operacji;
* podstawowe skladowe: `base_heat`, `time_heat`, `tool_modifier`,
  `security_modifier`, `conflict_modifier`;
* progi `warning_threshold` i `incident_threshold`;
* idempotentne `warning_dedupe_key` i `incident_dedupe_key`;
* `risk_version` zwiekszany tylko przy realnej zmianie stanu metera;
* tryb `observe` bez publikowania incydentow, NPC, ostrzezen ani konsekwencji;
* anulowanie operacji zeruje `current_heat` i `active_contribution` oraz oznacza
  powiazany stan progow jako anulowany.

Stary `risk_state` pozostaje jako legacy mechanizm finalizacji operacji. Nowy
meter jest osobnym read model na operacji, nie drugim systemem incydentow.

Sprawdzono:

* naliczanie heat z czasu, narzedzia, zabezpieczen celu i konfliktu;
* idempotencje przekroczenia progow;
* anulowanie operacji i wyzerowanie aktywnego wkladu;
* integracje tworzenia operacji;
* selektywne testy starego flow operacji.

Poza zakresem pozostaje:

* publikacja warningow;
* tworzenie incydentow;
* NPC;
* konsekwencje dla gracza;
* BlackNet incident bridge.

### Sprint 90 - Incident Initializer + Store

Przeczytano:

* opis Sprintu 90 w `doc/game_play_260626.md`,
* sekcje incydentow w `doc/incidents_npc_technical_architecture.md`,
* raport Sprintu 89 i aktualny miernik ryzyka operacji.

Przed zmianami potwierdzono znany baseline awarii
`tests.test_target_persistence`:

* embedding profilu w mapie nadal ma legacy problem JSON,
* generated app runtime nadal ma legacy brak `runApp`,
* recovery scopes nadal roznia sie przez `territory`.

Nie naprawiano tych problemow w Sprincie 90.

Wdrozono niewidoczny runtime incydentow:

* nowy `response_network.incident_store` jako magazyn incydentow i audytu;
* nowy `response_network.incident_initializer` tworzacy incydenty z operacji,
  ktore przekroczyly prog `incident`;
* scalanie pobliskich operacji w jeden incydent;
* wersjonowanie incydentu tylko przy realnej zmianie;
* poziomy reakcji i eskalacje na podstawie lacznego heat;
* `suspect_refs` z aktorow operacji;
* lekkie `territory_refs` przez read-only territory context;
* audit oraz replay zdarzen incydentu;
* anulowanie incydentu, gdy nie ma juz aktywnych operacji;
* przeliczanie incydentu laczonego po anulowaniu albo wygasnieciu jednej z
  operacji.

Incydenty pozostaja niewidoczne i nie publikuja niczego do gracza. Nie dodano
NPC, kapsul, snikersow, warningow, toastow, Cybernera ani konsekwencji.

Sprawdzono:

* tworzenie incydentu po przekroczeniu progu;
* scalanie pobliskich operacji;
* idempotencje powtornego syncu;
* anulowanie pustego incydentu;
* replay audytu;
* integracje `refresh_operations_runtime()` bez publikacji.

Poza zakresem pozostaje:

* publiczna mapa incydentow;
* delty incydentow dla UI;
* BlackNet incident bridge;
* NPC i kapsuly zachowan;
* konsekwencje oraz ostrzezenia graczy.

### Sprint 91 - Public Incident Map

Przeczytano:

* opis Sprintu 91 w `doc/game_play_260626.md`,
* architekture incydentow w `doc/incidents_npc_technical_architecture.md`,
* raporty Sprintow 89-90,
* aktualny runtime mapy, delt i recovery.

Wdrozono publiczny, ograniczony widok incydentow:

* endpoint `GET /api/map/incidents`;
* publiczny payload incydentu z `incident_id`, `version`, `status`, `level`,
  `center`, `search_radius_m`, `updated_at` i `expires_at`;
* brak ujawniania `operation_ids`, `suspect_refs`, `territory_refs`,
  `operation_refs` i prywatnych danych;
* publikacje delt `incident.created`, `incident.updated` i
  `incident.resolved`;
* `incident.resolved` usuwa incydent z mapy po anulowaniu ostatniej operacji;
* frontendowy handler `applyIncidentDelta()`;
* recovery scope incydentow przez snapshot `/api/map/incidents`;
* warstwe mapy pokazujaca centrum, promien, poziom i status incydentu;
* aktualizacje punktowe tylko zmienionego incydentu.

Nie wlaczono NPC, kapsul, snikersow, BlackNet bridge, wykrywania,
ostrzezen ani konsekwencji.

Sprawdzono:

* `python -m py_compile run.py response_network\incident_store.py
  response_network\incident_initializer.py response_network\operation_risk_meter.py`;
* `node --check static/js/terminal.js`;
* `python -m unittest tests.test_public_incident_map
  tests.test_incident_initializer tests.test_operation_risk_meter`;
* `python -m unittest tests.test_response_network_safety
  tests.test_territory_context_reader tests.test_territory_delta
  tests.test_target_persistence.GameStateDeltaBusTest`;
* `git diff --check`.

Znany baseline legacy `tests.test_target_persistence` pozostaje bez nowych
awarii funkcjonalnych Sprintu 91:

* embedding profilu w mapie nadal ma legacy problem JSON;
* generated app runtime nadal ma legacy brak `runApp`;
* recovery scopes nadal roznia sie przez `territory`.

Poza zakresem pozostaje:

* NPC i zachowania reakcji;
* BlackNet incident bridge;
* ostrzezenia do graczy;
* konsekwencje i wykrywanie.

### Sprint 92 - BlackNet Incident Bridge

Przeczytano:

* opis Sprintu 92 w `doc/game_play_260626.md`,
* `doc/incidents_npc_technical_architecture.md`,
* raport Sprintu 91,
* aktualny publiczny `incident_store`,
* deterministyczny publisher BlackNetu.

Wdrozono most incydentow do BlackNetu:

* publiczne incydenty sa zrodlem sygnalow `incident_hotspot`;
* sygnal publikuje tylko dane publiczne: lokalizacje, poziom reakcji, trend,
  czas waznosci i stan publiczny;
* CTA uzywa stabilnego `cta_action`, nie tekstu przycisku;
* CTA mapy prowadzi do publicznego punktu incydentu;
* CTA teleportu uzywa bezpiecznego punktu wejscia poza bezposrednim centrum
  zagrozenia i korzysta z istniejacego potwierdzenia `OK/ANULUJ`;
* `incident.resolved` oraz anulowanie ostatniej operacji wygasza sygnal przez
  czyszczenie cache BlackNetu i usuniecie lokalnego sygnalu z feedu;
* dodano deduplikacje przez `incident_id` / `entity_id` / `cta_target_id`;
* incydenty mieszaja sie z obecnym feedem BlackNetu bez osobnego systemu.

Nie wlaczono NPC, kapsul, snikersow, wykrywania, ostrzezen, konsekwencji ani
Ollamy.

Sprawdzono:

* `python -m py_compile run.py response_network\incident_store.py
  response_network\incident_initializer.py response_network\operation_risk_meter.py`;
* `node --check static/js/terminal.js`;
* `python -m unittest tests.test_blacknet_incident_bridge`;
* `python -m unittest tests.test_public_incident_map
  tests.test_incident_initializer tests.test_operation_risk_meter
  tests.test_blacknet_incident_bridge`;
* `python -m unittest tests.test_target_persistence.BlackNetWorldSignalPublisherTest
  tests.test_target_persistence.BlackNetWorldFactsSnapshotTest`;
* `python -m unittest tests.test_response_network_safety
  tests.test_territory_context_reader tests.test_territory_delta
  tests.test_target_persistence.GameStateDeltaBusTest`.

Znany baseline legacy pozostaje bez nowych regresji Sprintu 92:

* embedding duzego profilu w mapie nadal ma legacy problem JSON;
* wybrany test generated app runtime przeszedl w walidacji punktowej;
* recovery scopes nadal roznia sie przez obecny scope `territory`.

Poza zakresem pozostaje:

* NPC i zachowania reakcji;
* kapsuly oraz snikersy;
* wykrywanie i konsekwencje;
* ostrzezenia graczy;
* integracja Ollamy.

### Sprint 93 - NPC Behavior Capsules

Przeczytano:

* opis Sprintu 93 w `doc/game_play_260626.md`,
* `doc/incidents_npc_technical_architecture.md`,
* raport Sprintu 92,
* aktualne moduly `incident_store`, `incident_initializer` i delta-feed.

Wdrozono backendowy kontrakt kapsul NPC bez renderowania mapy:

* nowy `response_network.npc_capsule_factory`;
* nowy `response_network.npc_capsule_store`;
* nowy `response_network.response_dispatcher`;
* kompletne kapsuly `response_npc` z typem sluzby, poziomem, czasem spawnu,
  wygasnieciem, centrum incydentu, promieniami, predkoscia, seedem i typem
  trajektorii;
* rodziny wizualne `police`, `cyberpolice`, `secretservice`;
* kontrakt osmiu kierunkow snikersow;
* deterministyczna funkcja `position_at(capsule, world_time)`;
* delty `npc.spawned`, `npc.updated` i `npc.removed`;
* recovery snapshot `GET /api/map/incident-npc-capsules`;
* usuniecie kapsul po anulowaniu incydentu albo `incident.resolved`;
* wersjonowanie i deduplikacje kapsul.

Nie dodano renderowania NPC na mapie, plikow PNG, wykrywania, feedbacku,
ostrzezen ani konsekwencji. Backend nie przesyla cyklicznych pozycji NPC.

Sprawdzono:

* `python -m py_compile run.py response_network\incident_store.py
  response_network\incident_initializer.py response_network\operation_risk_meter.py
  response_network\npc_capsule_factory.py response_network\npc_capsule_store.py
  response_network\response_dispatcher.py`;
* `node --check static/js/terminal.js`;
* `python -m unittest tests.test_npc_behavior_capsules`;
* `python -m unittest tests.test_public_incident_map
  tests.test_incident_initializer tests.test_operation_risk_meter
  tests.test_blacknet_incident_bridge`;
* `python -m unittest tests.test_response_network_safety
  tests.test_territory_context_reader tests.test_territory_delta
  tests.test_target_persistence.GameStateDeltaBusTest`;
* `python -m unittest tests.test_target_persistence.BlackNetWorldSignalPublisherTest
  tests.test_target_persistence.BlackNetWorldFactsSnapshotTest`.

Znany baseline legacy pozostaje bez nowych regresji Sprintu 93:

* embedding duzego profilu w mapie nadal ma legacy problem JSON;
* wybrany test generated app runtime przeszedl w walidacji punktowej;
* recovery scopes nadal roznia sie przez obecny scope `territory`.

Poza zakresem pozostaje:

* renderowanie NPC jako snikersow na mapie;
* pliki PNG i skiny sluzb;
* lokalny detection probe;
* backendowy feedback wykrycia;
* ostrzezenia graczy;
* konsekwencje i egzekucja kar.

### Sprint 94 - Response Actors on Snikers

Przeczytano:

* opis Sprintu 94 w `doc/game_play_260626.md`,
* `doc/incidents_npc_technical_architecture.md`,
* raport Sprintu 93,
* aktualny kontrakt kapsul NPC i warstwe player actors na mapie.

Wdrozono wizualizacje NPC reakcji na istniejacej warstwie snikersow:

* kapsuly uzywaja kierunkow zgodnych z plikami
  `npc_{visual_family}_{direction}.png`;
* `actor_type: response_npc` pozostaje w kontrakcie kapsuly;
* rodziny `police`, `cyberpolice`, `secretservice` mapuja sie na pliki PNG;
* mapa pobiera snapshot `GET /api/map/incident-npc-capsules` jako optional scope;
* delta-feed routuje `npc.spawned`, `npc.updated` i `npc.removed` do otwartej mapy;
* recovery scope `npc` odswieza tylko kapsuly NPC;
* pozycja NPC jest liczona lokalnie przez frontendowa funkcje zgodna z
  `position_at(capsule, world_time)`;
* po uspieniu karty pozycja wynika z aktualnego czasu, bez nadrabiania klatek;
* anulowanie incydentu usuwa aktorow przez `npc.removed`;
* nie dodano `npc.moved` ani cyklicznych zapisow pozycji backendu.

Nie wdrozono wykrywania, `detection_candidate`, ostrzezen, feedbacku ani
konsekwencji. NPC w Sprincie 94 tylko pojawiaja sie, poruszaja lokalnie i
znikaja.

Sprawdzono:

* `python -m py_compile run.py response_network\npc_capsule_factory.py
  response_network\npc_capsule_store.py response_network\response_dispatcher.py`;
* `node --check static/js/terminal.js`;
* `python -m unittest tests.test_npc_behavior_capsules`;
* `python -m unittest tests.test_response_npc_frontend_contract`;
* `python -m unittest tests.test_public_incident_map
  tests.test_incident_initializer tests.test_operation_risk_meter
  tests.test_blacknet_incident_bridge`;
* `python -m unittest tests.test_response_network_safety
  tests.test_territory_context_reader tests.test_territory_delta
  tests.test_target_persistence.GameStateDeltaBusTest`;
* `python -m unittest tests.test_target_persistence.BlackNetWorldSignalPublisherTest
  tests.test_target_persistence.BlackNetWorldFactsSnapshotTest`;
* punktowy baseline legacy `tests.test_target_persistence`.

Znany baseline legacy pozostaje bez nowych regresji Sprintu 94:

* embedding duzego profilu w mapie nadal ma legacy problem JSON;
* generated app runtime pozostaje w znanym baseline;
* recovery scopes nadal roznia sie przez obecny scope `territory`.

Poza zakresem pozostaje:

* lokalne wykrywanie gracza przez NPC;
* `detection_candidate`;
* ostrzezenia i Cyberner feedback;
* konsekwencje gameplayowe;
* balans widocznosci NPC na mapie po realnych testach mobile/desktop.

### Sprint 95 - Detection Feedback Shadow

Przeczytano:

* opis Sprintu 95 w `doc/game_play_260626.md`,
* `doc/incidents_npc_technical_architecture.md`,
* raport Sprintu 94,
* aktualny kontrakt kapsul NPC i mapowy renderer snikersow.

Wdrozono shadow feedback wykrywania bez konsekwencji gameplayowych:

* dodano `response_network.detection_candidate_store`;
* dodano `response_network.detection_validator`;
* dodano endpoint `POST /api/map/incidents/detection-candidates`;
* frontend mapy ma `local_detection_probe`, ktory porownuje lokalna pozycje
  NPC z dostepnymi pozycjami aktorow graczy;
* probe wysyla tylko kandydata `detection_candidate` z `tracking_token`;
* backend odtwarza trajektorie przez `position_at(capsule, world_time)`;
* walidacja sprawdza czas, seed, `behavior_version`, pozycje NPC, promien,
  aktywny incydent, aktywna kapsule i aktywna operacje;
* bierny albo offline gracz na wlasnym, niezwiązanym terytorium jest
  odrzucany jako chroniony;
* anulowana operacja, anulowany incydent albo wygasla kapsula daja wynik
  `expired`;
* zgloszenia wielu obserwatorow sa deduplikowane przez `validation_key`;
* wszystkie wyniki sa zapisywane w audycie;
* calosc dziala w trybie `shadow`.

Nie wdrozono:

* ostrzezen dla graczy;
* przerywania operacji;
* konfiskaty narzedzi albo HC;
* `Judgment`;
* konsekwencji gameplayowych;
* publicznego ujawniania sprawcow.

Sprawdzono:

* `python -m py_compile run.py response_network\detection_candidate_store.py
  response_network\detection_validator.py response_network\npc_capsule_factory.py
  response_network\npc_capsule_store.py response_network\response_dispatcher.py`;
* `node --check static/js/terminal.js`;
* `python -m unittest tests.test_detection_feedback_shadow`;
* `python -m unittest tests.test_npc_behavior_capsules
  tests.test_response_npc_frontend_contract`;
* `python -m unittest tests.test_public_incident_map
  tests.test_incident_initializer tests.test_operation_risk_meter
  tests.test_blacknet_incident_bridge`;
* `python -m unittest tests.test_response_network_safety
  tests.test_territory_context_reader tests.test_territory_delta
  tests.test_target_persistence.GameStateDeltaBusTest`.

Uwaga walidacyjna:

* podczas testow Windows zglosil jednorazowy warning blokady pliku
  `flask_session`; testy zakonczyly sie statusem OK.

Znany baseline legacy pozostaje bez zmian:

* pelny `tests.test_target_persistence` nadal ma znane awarie spoza tej galęzi;
* Sprint 95 nie naprawia ani nie zmienia tych legacy przypadkow.

### Sprint 96 - Warning + Visible Safe

Przeczytano:

* opis Sprintu 96 w `doc/game_play_260626.md`;
* `doc/incidents_npc_technical_architecture.md`;
* raport Sprintu 95 i aktualny kod detection feedback.

Wdrozono tryb `visible_safe` bez konsekwencji gameplayowych:

* dodano domenowy store ostrzezen `response_network.warning_store`;
* dodano zdarzenie `response_warning_issued` jako zrodlo prawdy ostrzezenia;
* system-message jest emitowany dopiero po zapisaniu zdarzenia warning;
* `refresh_operations_runtime()` synchronizuje ostrzezenia z risk meterem;
* przekroczenie progu ostrzezenia zapisuje `warning_id`,
  `warning_issued_at` i `warning_arrival_at` w mierniku operacji;
* anulowanie operacji anuluje aktywne ostrzezenie przez warning store;
* endpoint `POST /api/map/incidents/detection-candidates` dziala w trybie
  `visible_safe`;
* poprawny feedback detekcji zwraca `accepted`, odrzucony zwraca `rejected`,
  a po anulowaniu pozostaje `expired`;
* odpowiedz walidatora jawnie zwraca `penalty_executed: false` i
  `consequence_executed: false`;
* marker NPC na mapie pokazuje odliczanie oraz krotki status accepted/rejected;
* dodano testy visible-safe warningow, detekcji i frontowego kontraktu markerow.

Nie wdrozono:

* przerywania operacji;
* konfiskaty narzedzi albo HC;
* kasowania postepu;
* `Judgment`;
* kar gameplayowych;
* pelnego balansu UI ostrzezen.

Sprawdzono:

* `python -m py_compile run.py response_network\warning_store.py
  response_network\detection_validator.py response_network\detection_candidate_store.py
  response_network\npc_capsule_factory.py response_network\npc_capsule_store.py
  response_network\response_dispatcher.py`;
* `node --check static/js/terminal.js`;
* `python -m unittest tests.test_response_warning_visible_safe
  tests.test_detection_feedback_shadow tests.test_response_npc_frontend_contract`;
* `python -m unittest tests.test_npc_behavior_capsules
  tests.test_public_incident_map tests.test_incident_initializer
  tests.test_operation_risk_meter tests.test_blacknet_incident_bridge`;
* `python -m unittest tests.test_response_network_safety
  tests.test_territory_context_reader tests.test_territory_delta
  tests.test_target_persistence.GameStateDeltaBusTest`;
* `python -m unittest tests.test_target_persistence` jako baseline legacy.

Znany baseline legacy pozostaje bez nowych regresji:

* embedding profilu w mapie nadal ma znany problem JSON;
* generated app runtime nadal ma znany brak `runApp`;
* recovery scopes nadal roznia sie przez obecny scope `territory`.

### Sprint 97 - Limited Enforcement

Przeczytano:

* opis Sprintu 97 w `doc/game_play_260626.md`;
* `doc/incidents_npc_technical_architecture.md`;
* raport Sprintu 96 i aktualny flow `visible_safe`.

Wdrozono ograniczone konsekwencje w trybie `limited_enforcement`:

* dodano `response_network.consequence_policy`;
* dodano `response_network.consequence_executor`;
* policy tworzy intent wyłącznie dla zaakceptowanego wykrycia;
* executor jest idempotentny przez `consequence_id` i osobny audit table;
* po zaakceptowanym detection feedback anulowana jest tylko powiązana operacja;
* postęp i bufor nagrody anulowanej operacji są czyszczone;
* operacja oznaczana jest jako `reward_blocked`, bez przyznania nagrody;
* `refresh_operations_runtime()` usuwa wkład anulowanej operacji z incydentu;
* incydent bez aktywnych operacji może zostać rozwiązany przez istniejący
  `incident_initializer`, co wygasza NPC i sygnał BlackNetu istniejącym flow;
* obsłużono wyścig anulowania przez status `superseded` bez wykonania kary;
* kill switch executora blokuje wykonanie bez restartu procesu;
* endpoint `POST /api/map/incidents/detection-candidates` pracuje teraz w trybie
  `limited_enforcement`;
* frontend mapy wysyła `mode: limited_enforcement`.

Nie wdrozono:

* konfiskaty narzędzi;
* konfiskaty HC;
* `Judgment`;
* kar niezwiązanych bezpośrednio z wykrytą operacją;
* pełnego trybu enforcement.

Sprawdzono:

* `python -m py_compile run.py response_network\consequence_policy.py
  response_network\consequence_executor.py response_network\detection_validator.py`;
* `node --check static/js/terminal.js`;
* `python -m unittest tests.test_consequence_limited_enforcement
  tests.test_detection_feedback_shadow tests.test_response_npc_frontend_contract`;
* `python -m unittest tests.test_npc_behavior_capsules
  tests.test_public_incident_map tests.test_incident_initializer
  tests.test_operation_risk_meter tests.test_blacknet_incident_bridge
  tests.test_response_warning_visible_safe`;
* `python -m unittest tests.test_target_persistence` jako baseline legacy.

Wyniki:

* testy celowane Sprintu 97: OK;
* testy sąsiednie incydentów/NPC/BlackNet/warning: OK;
* pełny `tests.test_target_persistence` nadal kończy się znanym baseline:
  2 failures i 3 errors.

Znany baseline legacy bez zmian:

* embedding profilu w mapie nadal ma znany problem JSON;
* generated app runtime nadal ma znany brak `runApp`;
* recovery scopes nadal roznia się przez obecny scope `territory`.
### Sprint 98 - Full Response Network + Readiness

Przeczytano:

* opis Sprintu 98 w `doc/game_play_260626.md`;
* `doc/incidents_npc_technical_architecture.md`;
* raport Sprintu 97 w dzienniku projektu.

Wdrozono pelny tryb Response Network nad istniejacym flow `limited_enforcement`:

* dodano tryb `full` w `response_network.consequence_policy`;
* dodano osobne feature flagi i kill switche dla konfiskaty narzedzia, HC,
  `Judgment`, hookow Radia, hookow Cybernera i historii incydentow;
* endpoint `POST /api/map/incidents/detection-candidates` przechodzi teraz przez
  tryb `full`;
* frontendowy local detection probe wysyla `mode: full`;
* `consequence_executor` po zaakceptowanym wykryciu:
  * anuluje tylko powiazana operacje,
  * usuwa jej postep i blokuje nagrode,
  * konfiskuje uzyte narzedzie, jesli nie powoduje softlocka,
  * konfiskuje skalowana kwote HC z rezerwa bezpieczenstwa,
  * nadaje status `Judgment`,
  * zapisuje historie zakonczonego incydentu,
  * dodaje hook Cybernera przez `system_messages`,
  * dodaje hook Radia przez `radio_events`;
* replay tego samego `consequence_id` jest idempotentny i nie powiela kar,
  wiadomosci, historii ani zdarzen Radia;
* po karze emitowane sa delty wallet/apps/storage, z `/api/profile` jako recovery;
* zachowano stary tryb `limited_enforcement` jako testowalny, bez konfiskat i
  bez `Judgment`.

Zabezpieczenia:

* softlock protection nie pozwala zabrac ostatniego narzedzia zdolnego do
  operacji;
* globalny kill switch executora nadal blokuje wykonanie konsekwencji;
* pojedyncze kary mozna wylaczyc osobno na poziomie policy;
* walidator nadal nie wykonuje kar - tylko akceptuje feedback;
* konsekwencje sa wykonywane dopiero przez `consequence_executor`.

Nie wdrozono:

* GhostNetworku;
* maszyn klanowych;
* integracji z Ollama;
* cyklicznych zapisow pozycji NPC;
* nowych endpointow gameplayowych poza rozszerzeniem istniejacego detection
  endpointu.

Sprawdzono:

* `python -m py_compile run.py response_network\consequence_policy.py
  response_network\consequence_executor.py response_network\detection_validator.py`;
* `node --check static/js/terminal.js`;
* `python -m unittest tests.test_consequence_limited_enforcement
  tests.test_consequence_full_response tests.test_detection_feedback_shadow
  tests.test_response_npc_frontend_contract`;
* `python -m unittest tests.test_operation_risk_meter
  tests.test_incident_initializer tests.test_public_incident_map
  tests.test_blacknet_incident_bridge tests.test_npc_behavior_capsules
  tests.test_response_warning_visible_safe`.

Wyniki w trakcie wdrozenia:

* testy pelnych konsekwencji potwierdzily konfiskate narzedzia, HC, `Judgment`,
  hook Cybernera, hook Radia, historie incydentu i idempotencje replay;
* test softlock potwierdzil, ze ostatnie narzedzie operacyjne zostaje u gracza;
* testy sasiednie incydentow/NPC/BlackNet/warning: OK.

Walidacja koncowa:

* `python -m unittest tests.test_response_network_safety
  tests.test_territory_context_reader tests.test_territory_delta
  tests.test_operation_risk_meter tests.test_incident_initializer
  tests.test_public_incident_map tests.test_blacknet_incident_bridge
  tests.test_npc_behavior_capsules tests.test_response_warning_visible_safe`: OK;
* `python -m unittest tests.test_target_persistence`: znany baseline legacy,
  2 failures i 3 errors;
* `git diff --check`: OK, tylko ostrzezenie CRLF dla `run.py`;
* dodatkowy smoke pomiarow mapowych przez test client nie zostal wykonany,
  poniewaz po testach lokalny `python.exe` przestal byc dostepny w sesji
  narzedziowej (`Okreslona sesja logowania nie istnieje`).

Znany baseline legacy bez zmian:

* embedding profilu w mapie nadal ma znany problem JSON;
* generated app runtime nadal ma znany brak `runApp`;
* recovery scopes nadal roznia sie przez obecny scope `territory`.

Readiness:

* Response Network ma kompletna sciezke konsekwencji `full` zabezpieczona
  feature flagami, kill switchami, idempotencja i softlock protection;
* GhostNetwork, maszyny i Ollama pozostaja poza zakresem i nie zostaly
  uruchomione.

## Map Glitch Loader Refactor

Zastapiono lekki status spinnera mapy glitch overlayem GhostSystem 2108.

Wdrozone:

* overlay pokrywa powierzchnie mapy podczas aktywnej synchronizacji;
* overlay blokuje interakcje mapy i ogranicza spamowanie kolejnych akcji;
* intensywnosc efektu rosnie wraz z czasem oczekiwania: normal, slow, heavy;
* pseudologi informuja o synchronizacji mapy, rekonstrukcji osi czasu,
  polaczeniu z 2108 i przeciazeniu sieci;
* boot overlay mapy dostal ten sam jezyk statusow i obsluge slow/heavy/error;
* po zakonczeniu synchronizacji overlay znika natychmiast i mapa wraca do
  interakcji;
* zachowano obsluge bledu i timeoutu;
* dodano wsparcie `prefers-reduced-motion`;
* nie dodano pollerow, backendu ani zmian gameplayu.

Walidacja:

* dodano test kontraktu `tests.test_map_loader_frontend_contract`;
* `python -m unittest tests.test_map_loader_frontend_contract
  tests.test_response_npc_frontend_contract`: OK;
* `node --check static/js/terminal.js`: OK;
* `git diff --check`: OK, tylko ostrzezenie CRLF dla
  `templates/map_template.html`;
* grep po typowych sladach mojibake w plikach silnika: brak trafien.

Update:

* dopracowano sam charakter glitch overlayu: dominujace scanline'y i
  przesuwajace sie pasy zastapiono losowymi blokami RGB;
* bloki maja losowa pozycje, rozmiar, opoznienie, kolor i przezroczystosc;
* `slow` i `overloaded/heavy` zwiekszaja czestotliwosc oraz powierzchnie
  zaklocen bez dodawania pollera;
* `ready` natychmiast zdejmuje klasy intensywnosci i chowa overlay.

## Target Action Flow - CEL Progress Sync

Domknieto problem kropek progresu `CEL` na styku mapa / terminal / desktop.

Problem:

* aplikacje uruchamiane z terminala i pulpitu zaczely poprawnie dzialac na
  aktualnym `aimed_target`, ale szybkie mieszanie z akcjami mapy potrafilo
  cofac `actions_allowed`;
* mapa mogla zapisac starszy snapshot targetu po tym, jak terminal albo desktop
  zdazyl juz potwierdzic kolejny krok;
* frontend zapalal kropke szybciej niz zrodlo prawdy zdazylo zapisac stan, co
  dawalo mylace wrazenie postepu;
* dodatkowo ten sam obiekt mapy mogl miec inna etykiete w roznych flow, wiec
  backend traktowal go jak inny target i nie scalal progresu.

Rozwiazanie:

* `actions_allowed` stalo sie monotoniczne dla tego samego targetu: raz
  potwierdzone `true` nie jest cofane przez pozniejszy request;
* merge targetu nie opiera sie juz wylacznie na labelu w `target_id`, tylko na
  runtime identity: gracz po `target_username`, vulnerability po
  `vulnerability_id`, konflikt po `foreign_area_id` + pozycja, zwykly POI po
  wspolrzednych;
* desktop i terminal uruchamiaja brakujace operacje mapowe tym samym
  kontraktem co mapa;
* klik w segment `CEL` odswieza prawde z backendu i pozwala sprawdzic aktualny
  stan bez restartu calego Ghosta;
* usunieto frontendowe zgadywanie postepu jako zrodlo prawdy - UI ma pokazywac
  stan potwierdzony przez backend.

Efekt:

* hackowanie celu jest czytelniejsze i mniej zalezne od otwartej mapy;
* mapa jest odciazona, bo gracz moze oznaczyc cel na mapie, a potem pracowac z
  terminala albo pulpitu;
* pasek `CEL` stal sie praktycznym checkpointem prawdy targetu;
* mix mapa / terminal / desktop jest stabilniejszy i mniej podatny na race
  condition spoznionych requestow.

Walidacja:

* dodano regresje dla zachowania nowszych flag targetu mimo innej etykiety mapy;
* punktowe testy target flow / `gonna-win`: OK;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `git diff --check`: OK.

## Sprint 99 - Victim Picker Source Contract Audit

Wykonano audyt zrodel i kontraktow pod przyszly Victim Picker.

Wynik:

* dodano dokument `doc/victim_picker_audit.md`;
* potwierdzono, ze `VICTIMS` ma byc tylko agregowanym widokiem, nie nowym
  magazynem targetow;
* opisano zrodla kandydatow: `profile.targets`, player actors, clan
  vulnerabilities i territory conflict targets;
* wskazano istniejace sciezki ustawiania celu: `/map-action`,
  `/hack-action`, `/api/map/player-targets/mark`;
* potwierdzono uzycie `get_player_action_range(profile)` jako jedynego wzoru
  zasiegu;
* opisano kontrakt kandydata, zasady ikon UI, focus mapy i teleport przez
  istniejace potwierdzenie;
* wskazano miejsca wymagajace refaktoru przed budowa okna.

Poza zakresem:

* brak zmian runtime;
* brak endpointow;
* brak wpisu Googleplex;
* brak okna Victim Pickera.

## Sprint 100 - Victim Picker Backend Foundation

Zbudowano lekka warstwe backendowa Victim Pickera bez okna desktopowego.

Wdrozone:

* dodano Victim Picker do `PRO_SYSTEM_TOOLS` jako platna aplikacje Googleplex
  za `100 000 HC`;
* dodano endpoint `GET /api/victim-picker/candidates`;
* dodano endpoint `POST /api/victim-picker/aim`;
* kandydaci powstaja z istniejacych zrodel: oznaczone POI, zaakceptowani
  gracze/kontakty, intruzi terytorium, podatnosci klanowe i konflikty;
* zasieg opiera sie na istniejacym `get_player_action_range(profile)`;
* ustawienie celu zapisuje zwykly `aimed_target`, bez tworzenia nowego
  magazynu `profile.victims`;
* endpoint `aim` emituje istniejaca delte map target, zeby pasek `CEL` mogl
  zostac odswiezony obecnym mechanizmem.

Celowo poza zakresem:

* brak okna Victim Pickera;
* brak ikon UI Victim Pickera;
* brak integracji pulpitu i menu Start;
* brak Leafleta w pickerze;
* brak uruchamiania operacji, ryzyka i incydentow.

Walidacja:

* `rg` potwierdzil obecne punkty integracji Victim Pickera;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `git diff --check`: OK;
* punktowy smoke endpointow przygotowano jako tymczasowy skrypt, ale lokalna
  sesja PowerShell blokuje uruchomienie `python.exe` jako programu
  (`Okreslona sesja logowania nie istnieje`), mimo ze `py_compile` dziala;
* smoke endpointow Victim Pickera po instalacji aplikacji zostaje do
  potwierdzenia na serwerze/runtime.

## Sprint 101 - Victim Picker Desktop App

Podpieto widoczna warstwe Victim Pickera do istniejacego runtime okien
desktopowych.

Wdrozone:

* dodano `createVictimPickerApp()` w `static/js/terminal.js`;
* podpieto `createVictimPickerApp` do `runSystemLauncherApp()`;
* aplikacja dziala jako jedna instancja okna i korzysta z obecnego taskbara,
  `makeDraggable()` oraz mobile safe mode;
* okno pobiera kandydatow z `GET /api/victim-picker/candidates`;
* lista `VICTIMS` grupuje kandydatow wedlug zrodla i sortowanie pozostaje po
  stronie backendu;
* kazdy kandydat ma trzy male akcje ikonowe:
  * oznacz jako `CEL`,
  * pokaz na mapie,
  * teleport w okolice celu;
* oznaczenie celu uzywa `POST /api/victim-picker/aim`, a po sukcesie odswieza
  pasek `CEL` przez istniejacy mechanizm prawdy targetu;
* pokazanie celu na mapie uruchamia mape dopiero po kliknieciu;
* teleport uzywa istniejacego systemowego potwierdzenia `OK/ANULUJ` i
  istniejacego endpointu teleportu.

Styl:

* dodano namespacowane style `.victim-picker-*` w `static/css/style.css`;
* okno ma zwarty terminalowy layout, ikonowe przyciski, status zasiegu,
  wyroznienie aktywnego celu i wariant mobile;
* brak Leafleta w oknie Victim Pickera.

Poza zakresem:

* brak nowych endpointow;
* brak nowego store;
* brak uruchamiania operacji z Victim Pickera;
* brak zmian mechaniki mapy, ryzyka i incydentow.

Walidacja:

* `node --check static/js/terminal.js`: OK;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `git diff --check`: OK, tylko ostrzezenie CRLF dla `static/css/style.css`;
* `rg` potwierdzil integracje launchera, stylow i endpointow.

## Sprint 102 - Victim Picker: flow, scan i CEL

Przebudowano Victim Pickera z jednego widoku listy na jawny przeplyw
`MAIN -> SCAN -> VICTIMS`.

Wdrozone:

* ekran `MAIN` pokazuje pozycje motocykla, zasieg, aktualny `CEL` i tylko dwie
  glowne akcje: `SCAN` oraz `VICTIMS`;
* `SCAN` korzysta z istniejacego `/map-action` z `action: scan`, bez ladowania
  mapy i bez nowego algorytmu skanowania;
* wyniki skanu sa grupowane po istniejacym `source_type`, sortowane po
  odleglosci od motocykla i maja akcje `Oznacz`;
* `Oznacz` korzysta z istniejacego `/map-action` z `action: mark_target`, czyli
  zapisuje obiekt do obecnego mechanizmu oznaczonych celow;
* `Pokaż na mapie` dla wyniku skanu aktywuje sie dopiero po oznaczeniu;
* ekran `VICTIMS` pokazuje kandydatow z obecnych zrodel i pozwala ustawic
  `aimed_target` przez `POST /api/victim-picker/aim`;
* backend `GET /api/victim-picker/candidates` zwraca teraz kanoniczny
  `aimed_target`, zeby aplikacja i pasek `CEL` korzystaly z tej samej prawdy;
* po ustawieniu celu aplikacja odswieza liste i pasek `CEL` kontrolowanym
  refresh target truth.

Celowo poza zakresem:

* brak finalnego polish GUI ze Sprintu 103;
* brak nowych modeli `victims`;
* brak uruchamiania narzedzi, operacji, ryzyka i incydentow z Victim Pickera;
* brak zmian katalogu Googleplex i instalacji produktu.

Walidacja:

* `node --check static/js/terminal.js`: OK;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `python -m unittest tests.test_target_persistence`: FAIL na znanym baseline
  legacy: embedding profilu w mapie, generated app runtime oraz oczekiwana lista
  recovery bez `territory`;
* `git diff --check`: OK po usunieciu whitespace z dokumentacji, z pozostajacym
  ostrzezeniem CRLF dla `static/css/style.css`.

## Sprint 103 - Victim Picker: finalne GUI i jezyk ikon

Dopolerowano Victim Pickera po przebudowie flow ze Sprintu 102. Mechanika
pozostala bez zmian, a praca dotyczyla czytelnosci, ikon i stanow UI.

Wdrozone:

* dodano spojny zestaw `VICTIM_PICKER_ICONS` jako inline SVG z `currentColor`;
* MAIN pokazuje dwa glowne kafle `SCAN` i `VICTIMS`, status `CEL`, pozycje
  motocykla, zasieg oraz mala legende akcji;
* SCAN dostal osobny ekran ladowania z impulsem radaru i logami GhostSystemu;
* wyniki SCAN maja kompaktowe wiersze, akcje `Oznacz` / `Oznaczony` oraz
  `Pokaz na mapie` aktywny dopiero po oznaczeniu;
* VICTIMS pokazuje aktywny `CEL`, status zasiegu, skrotowe powody blokady i
  male akcje ikonowe: ustaw cel, pokaz na mapie, teleport;
* aktywny cel ma klase `is-aimed`, aktywny celownik i badge `CEL`;
* przyciski maja `title`, `aria-label`, hover, focus, active i disabled;
* style `.victim-picker-*` zostaly uzupelnione o responsywny layout, legendy,
  stany ikon i radar scan.

Poza zakresem:

* brak zmian endpointow;
* brak zmian mechaniki skanu, oznaczania i ustawiania celu;
* brak nowych modeli danych;
* brak zmian mapy, ryzyka, incydentow i operacji.

Walidacja:

* `node --check static/js/terminal.js`: OK;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `python -m unittest tests.test_target_persistence`: uruchomiono jako baseline
  legacy, znane awarie pozostaja bez zmian;
* `git diff --check`: OK, tylko znane ostrzezenie CRLF dla
  `static/css/style.css`.

## Sprint 104 - Ghost Control Suite: audyt i wspolny kontrakt

Rozpoczeto Faze J w `doc/game_play_180726.md`. Sprint 104 zostal wykonany jako
audytowy kontrakt dla rodziny Ghost Control Suite, bez budowania nowych okien i
bez zmian runtime gameplayu.

Wdrozone:

* dodano `doc/ghost_control_suite_contract_audit.md`;
* opisano istniejace zrodla prawdy dla klastrow terytorium, przejetych celow,
  zabezpieczen, konfliktow, operacji, plikow wynikowych i incydentow;
* potwierdzono, ze klaster jest obecnym rekordem `player_areas.id`, a nie nowym
  modelem aplikacji;
* opisano kontrakt `pillar`, `inner` i `alone`;
* opisano backendowy kontrakt `threat_state`: `neutral`, `collision`,
  `attacked`;
* wskazano, ze presety `open`, `low`, `regular`, `secure`, `all` maja korzystac
  z obecnej sciezki mapy;
* opisano lifecycle porzucenia obiektu, anulowania operacji, mapowania rodzin
  operacji i wspolnego zestawu ikon `GHOST_CONTROL_ICONS`.

Poza zakresem:

* brak nowych endpointow;
* brak aplikacji Territory Control i Operation Control;
* brak zmian mapy, delt, terytoriow, operacji i incydentow;
* brak zmian Googleplex poza przyszlym kontraktem produktow.

Walidacja:

* sprint spelnia DoD audytowe: nie ma potrzeby tworzenia drugiego systemu
  terytoriow, zabezpieczen, incydentow ani anulowania operacji;
* kolejne sprinty 105-108 maja jasno wskazane miejsca podpiecia do obecnego
  silnika.
* `git diff --check`: OK, tylko istniejace ostrzezenie CRLF/LF dla
  `static/css/style.css`;
* testow runtime nie uruchamiano, bo Sprint 104 zmienil wylacznie dokumentacje.

## Sprint 105 - Territory Control: backend i mechanika

Dodano backendowy fundament Territory Control jako produkt Ghost Control Suite i
lekki kontrakt API do zarzadzania wlasnymi klastrami bez otwierania mapy.

Wdrozone:

* dodano produkt Googleplex `territoryControl` za `50000 HC` w
  `PRO_SYSTEM_TOOLS`;
* dodano read-only snapshot `/api/ghost-control/territory` oraz alias
  `/api/pro-system/territory-control`;
* dodano endpoint szczegolow klastra po `cluster_id`;
* snapshot zwraca `clusters` oraz `alone_pillars`;
* filary bez minimum trzech punktow pozostaja jako `alone`, bez sztucznego
  `cluster_id`, powierzchni, obwodu ani stanu konfliktu klastra;
* klaster zwraca filary, innery, centroid, perimeter, najblizszy
  `navigation_target`, dystans od motocykla i `map_focus`;
* dodano zapis security przez istniejace presety `open`, `low`, `regular`,
  `secure`, `all`;
* `security_percent` liczy aktywne booleanowe zabezpieczenia, czyli poziom
  uzbrojenia obiektu;
* dodano porzucenie wlasnego obiektu z wymaganym `confirm: true`, przebudowa
  obszarow, przeliczeniem konfliktow, wyczyszczeniem targetu i swiezym
  snapshotem;
* dodano testy cyklu `alone -> cluster -> dissolve`, security summary oraz
  lekkiego endpointu bez `sync_session_profile()`.

Poza zakresem:

* brak okna Territory Control;
* brak finalnego GUI, ikon i interakcji desktopowych;
* brak zmian geometrii terytoriow;
* brak nowych zasad konfliktow, incydentow, NPC i mapy.

Walidacja:

* `python -m unittest tests.test_territory_control`: OK;
* `python -m unittest tests.test_territory_control tests.test_territory_context_reader tests.test_territory_delta`: OK;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `git diff --check`: OK, tylko istniejace ostrzezenie CRLF/LF dla
  `static/css/style.css`.

## Sprint 106 - Territory Control: okno i finalny interfejs

Domknieto frontend Territory Control jako okno systemowe Ghost Control Suite
korzystajace z endpointow Sprintu 105. Aplikacja nie tworzy drugiego modelu
terytorium: listy klastrow, samotne filary, role `pillar` / `inner` / `alone`,
`threat_state`, presety zabezpieczen i porzucanie obiektow pochodza z backendu.

Wdrozone:

* dodano launcher `territory_control` dla produktu Territory Control;
* dodano okno z lista klastrow, sekcja samotnych filarow i ekranem szczegolow
  klastra;
* ekran listy pokazuje pozycje motocykla, liczbe klastrow, aktywne konflikty,
  odleglosci, powierzchnie i stany zagrozenia;
* ekran szczegolow rozdziela filary i inner nodes oraz pokazuje zabezpieczenia
  z paskiem procentowym;
* podpieto akcje mapa i teleport przez istniejace mosty mapy oraz system
  potwierdzen teleportu `OK/ANULUJ`;
* podpieto presety `OPEN`, `LOW`, `REGULAR`, `SECURE`, `ALL` oraz pojedyncze
  flagi zabezpieczen do endpointow Ghost Control;
* podpieto porzucanie obiektu z odswiezeniem listy i powrotem do listy, jezeli
  klaster zniknal po zmianie;
* dodano responsywny styl okna desktop/mobile, w tym dwurzedowy uklad akcji na
  waskim ekranie.

Poza zakresem:

* brak Operation Control;
* brak nowej logiki mapy;
* brak nowego backendu poza mechanika Sprintu 105;
* brak zmian geometrii terytoriow, konfliktow, incydentow i NPC.

Walidacja:

* `node --check static/js/terminal.js`: OK;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `python -m unittest tests.test_territory_control tests.test_territory_context_reader tests.test_territory_delta`: OK;
* `git diff --check`: OK, tylko istniejace ostrzezenie CRLF/LF dla
  `static/css/style.css`.

## Sprint 106.1 - Territory Control Cluster List Fix

Poprawiono ekran szczegolow klastra Territory Control. Wczesniej `FILARY` i
`INNER NODES` byly renderowane jako dwie osobne sekcje z wlasnymi listami, co
przy wiekszej liczbie filarow powodowalo ucinanie pierwszej sekcji i wrazenie
rozbitego okna.

Wdrozone:

* filary i inner nodes sa teraz jedna wspolna przewijana lista;
* `FILARY` i `INNER NODES` zostaly separatorami kategorii w tej samej liscie;
* nie zmieniono endpointow, modelu klastra ani presetow zabezpieczen;
* zachowano uklad mobile/narrow z akcjami w czytelnym przeplywie.

Walidacja:

* `node --check static/js/terminal.js`: OK;
* `python -m unittest tests.test_territory_control tests.test_territory_context_reader tests.test_territory_delta`: OK;
* `git diff --check`: OK, tylko istniejace ostrzezenie CRLF/LF dla
  `static/css/style.css`;
* backend pozostaje bez zmian.

## Sprint 106.2 - Territory Control Preset Mini Palette

Zmniejszono presety zabezpieczen w wierszu obiektu Territory Control. Przyciski
`OPEN`, `LOW`, `REGULAR`, `SECURE`, `ALL` byly zbyt szerokie i konkurowaly z
paleta flag oraz akcjami mapy/teleportu. Teraz dzialaja jako mini-paleta w dwoch
liniach, z pelnymi nazwami dostepnymi w tooltipach.

Wdrozone:

* skrocono etykiety presetow w UI do `OP`, `LO`, `RG`, `SC`, `AL`;
* pelne nazwy presetow zostaly w `title`;
* presety sa ulozone w zwartej siatce 3 + 2;
* wiersz obiektu ma wasza kolumne presetow i nie rozpycha listy klastra;
* backend i kontrakt presetow pozostaly bez zmian.

Walidacja:

* `node --check static/js/terminal.js`: OK;
* `python -m unittest tests.test_territory_control tests.test_territory_context_reader tests.test_territory_delta`: OK;
* `git diff --check`: OK, tylko istniejace ostrzezenie CRLF/LF dla
  `static/css/style.css`;
* backend pozostaje bez zmian.

## Sprint 106.3 - Territory Control Threat Labels Fix

Poprawiono etykiety zagrozen na liscie klastrow Territory Control. Wczesniej
aktywny konflikt z udzialem gracza mogl oznaczyc jako `KOLIZJA` rowniez klaster,
ktory nie nalezal do konfliktu. Od teraz `KOLIZJA` wynika z dopasowania
konkretnego `area_id`, a `ALARM` z atakowanego filara danego klastra.

Wdrozone:

* backend zwraca `threat_flags.collision` i `threat_flags.attacked` per klaster;
* konflikt nie rozlewa sie na wszystkie klastry uczestnika;
* konflikt po przebudowie klastra moze zostac dopasowany po targetach lezacych
  w aktualnym polygonie, nawet jesli zapisany `area_id` jest juz historyczny;
* `ALARM` wynika z atakowanych targetow klastra, nie tylko z trzech filarow;
* frontend renderuje wiele etykiet obok siebie, np. `ALARM` + `KOLIZJA`;
* po zmianie presetu zabezpieczen aktualny widok klastra odswieza sie na miejscu
  zamiast wracac do listy, rowniez gdy `cluster_id` zmieni sie po przebudowie;
* dodano testy regresyjne dla konfliktu z innym `area_id` i dla dopasowania
  konfliktu po targetach w polygonie.

Walidacja:

* `node --check static/js/terminal.js`: OK;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `python -m unittest tests.test_territory_control tests.test_territory_context_reader tests.test_territory_delta`: OK.

## Sprint 107 - Operation Control: backend, pliki i incydenty

Dodano backendowy fundament Operation Control bez budowania finalnego GUI. Nowa
warstwa korzysta z istniejacego runtime operacji, `summarize_operation_for_client`
oraz `cancel_profile_operation`, wiec nie powstaje drugi system operacji ani
drugi mechanizm anulowania.

Wdrozone:

* dodano produkt Googleplex `operationControl` za `20000 HC` w rodzinie
  `ghost_control_suite`;
* dodano lekki snapshot `GET /api/ghost-control/operations` oraz alias
  `/api/pro-system/operation-control`;
* snapshot rozszerza operacje o rodzine, aktualna pozycje, dystans od motocykla,
  podsumowanie pliku wynikowego, ryzyko i publiczne powiazanie z incydentem;
* dodano pojedyncze anulowanie przez
  `POST /api/ghost-control/operations/cancel`;
* dodano grupowe anulowanie przez
  `POST /api/ghost-control/operations/cancel-group` i alias
  `/api/pro-system/operation-control/cancel-group`;
* grupowe anulowanie laduje profil raz, odswieza operacje raz, sprawdza rodzine,
  anuluje istniejacym helperem i zapisuje profil raz;
* dodano testy regresyjne dla snapshotu, dystansu, outputu, incydentu,
  read-only endpointu i grupowego anulowania.

Pozostaje poza zakresem:

* finalne okno Operation Control;
* osobny poller UI;
* zmiana mechaniki operacji, incydentow i plikow.

Walidacja:

* `python -m unittest tests.test_operation_control`: OK.

## Sprint 107.1 - Operation Control audit po disconnectach

Sprawdzono zakres Sprintu 107 po przerwanych sesjach. Nie znaleziono duplikatow
endpointow, produktu Googleplex ani pomocniczych helperow. Zmiany pozostaja
ograniczone do backendu Operation Control, dokumentacji oraz testow.

Domknieto brakujace testy kontraktowe:

* historia operacji zwracana w snapshocie;
* pojedyncze anulowanie przez istniejacy helper;
* ponowna walidacja grupowego anulowania i Territory Control.

Walidacja:

* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `python -m unittest tests.test_operation_control tests.test_territory_control`: OK, 12 testow;
* `git diff --check`: OK.

## Sprint 108 - Operation Control GUI i Ghost Control Suite

Domknieto finalne okno Operation Control jako trzecia aplikacje rodziny Ghost
Control Suite. Aplikacja korzysta z backendowego snapshotu i endpointow
anulowania ze Sprintow 107-107.1, bez drugiego runtime operacji i bez nowego
ciezkiego pollera.

Wdrozone:

* launcher `operation_control` w systemowym uruchamianiu aplikacji;
* jedno okno Operation Control z wpisem taskbara i ponownym podnoszeniem
  istniejacej instancji;
* naglowek z aktywnymi operacjami, incydentami, grupami i pozycja motocykla;
* grupowanie po rodzinach operacji z ikonami, outputem i anulowaniem calej
  grupy;
* wiersze operacji z targetem, dystansem, czasem, outputem, ryzykiem,
  incydentem i anulowaniem pojedynczym;
* stany loading, empty, error, busy oraz mobile safe mode;
* CSS dopasowany do Victim Picker i Territory Control.

Poza zakresem:

* automatyczny poller Operation Control;
* zmiany mechaniki operacji, incydentow, plikow albo mapy.

Walidacja:

* `node --check static/js/terminal.js`: OK;
* `python -m py_compile run.py database.py profileManagment.py`: OK;
* `python -m unittest tests.test_operation_control tests.test_territory_control`: OK, 12 testow;
* `git diff --check`: OK, tylko istniejace ostrzezenie CRLF/LF dla
  `static/css/style.css`.

## Sprint 109 - Ghost Control Suite polish

Domknieto drobny UX polish rodziny Victim Picker / Territory Control /
Operation Control.

Wdrozone:

* Victim Picker dostal unikalna ikone `⌖` w katalogu produktu i w renderowaniu
  ikon istniejących instalacji;
* Victim Picker zostal dopiety do rodziny `ghost_control_suite`;
* okna Victim Picker, Territory Control i Operation Control dostaly desktopowy
  resize corner;
* mobile safe mode wylacza natywny resize dla tych okien;
* akcje kasujace, porzucajace i anulujace sa pomaranczowo-czerwone, z osobnym
  hoverem alarmowym.

Poza zakresem:

* zmiana mechaniki skanu, terytoriow, operacji i incydentow;
* nowe endpointy albo nowe magazyny danych.

## Sprint 109.5 - Territory Control: pelne otoczenie klastra

Domknieto luke pomiedzy statusem `encircled` a realnym przejeciem klastra.
Pelne otoczenie nie jest juz tylko flaga UI: resolver potrafi wykryc stabilny
atakujacy klaster, ktory obejmuje caly klaster obroncy, i wykonac jedna
domenowa operacje przejecia.

Wdrozone:

* `TerritoryEncirclementResolver` z rewalidacja geometrii i aktualnych punktow
  klastra przed przejeciem;
* przeniesienie tylko kanonicznych punktow nalezacych do otoczonego klastra:
  filarow i inner nodes;
* pozostawienie punktow obroncy poza przejmowanym klastrem;
* zamykanie aktywnych konfliktow statusem `resolved_by_encirclement`;
* event/delta `territory.encirclement_resolved` z dedupe key;
* dry-run helper `reconcile_territory_encirclements()`;
* bezpieczne wpiecie po rebuildzie terytorium, bez nowego runtime mapy.

Poza zakresem:

* GhostNetwork i maszyny klanowe;
* osobne UI dla historii otoczen;
* automatyczna migracja historycznie otoczonych klastrow.

Walidacja:

* `python -m unittest tests.test_territory_control`: OK, 8 testow.
