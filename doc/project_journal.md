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
