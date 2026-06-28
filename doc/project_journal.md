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
