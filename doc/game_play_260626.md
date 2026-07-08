# CHAOS — Gameplay Implementation Roadmap

Dokument po Sprincie 0.

Sprint 0 zamknął kontrakty projektowe. Ten dokument jest roadmapą implementacji kolejnych sprintów gameplayu.

CHAOS:

```text
Cyber Hacking Adventure Of Senses
```

Hasło:

```text
Hack the digital senses of the modern world.
Hakuj cyfrowe zmysły współczesnego świata.
```

---

## Status dokumentu

To nie jest już luźna koncepcja.

To jest plan implementacyjny oparty o kontrakty:

| Dokument | Rola |
| --- | --- |
| `gameplay_terms.md` | Słownik pojęć. |
| `source_type_mapping.md` | Mapowanie źródeł mapy na targety. |
| `world_objects.md` | Obiekty świata. |
| `map_actions.md` | Akcje mapy. |
| `app_contract.md` | Kontrakt aplikacji. |
| `operations.md` | Operacje jako centralny byt gameplayu. |
| `movement_model.md` | Aktywny świat i refresh bez realtime loopa. |
| `resource_types.md` | Model zasobów. |
| `file_model.md` | Pliki jako inventory. |
| `data_economy.md` | Ghost Exchange i ekonomia danych. |
| `risk_events.md` | Ryzyko, eventy i konsekwencje. |
| `gameplay_loop.md` | Pełna pętla gameplayu. |
| `sprint0_summary.md` | Zamknięcie Sprintu 0. |
Decision:

* Przyjęto: ten dokument jest roadmapą Sprintu 1+.
* Przyjęto: źródłem prawdy dla pól, nazw i kontraktów są dokumenty Sprintu 0.
* Przyjęto: jeśli roadmapa skraca opis, wygrywa dokument kontraktowy.

---

## Główna pętla implementacji

Roadmapa realizuje pętlę:

```text
World Object
↓
Map Action
↓
Application
↓
Operation
↓
Movement
↓
Resource
↓
File
↓
Ghost Exchange
↓
Mail
↓
HackCoins
↓
New Apps
↓
Back to Map
```

Każdy sprint powinien kończyć się ręcznym sprawdzeniem tej pętli albo jej fragmentu.

---

## Zasada prowadzenia sprintów

Każdy sprint powinien mieć:

1. Cel gameplayowy.
2. UX gracza.
3. Przepływ danych.
4. Wpływ na systemy.
5. Kryteria akceptacji.

Nie dopisujemy dużych mechanik bokiem.

Nie tworzymy drugiego routera aplikacji, drugiego rynku, drugiego systemu plików ani drugiego modelu operacji.

---

# Sprint 1 — Map Action Router + App Contract Runtime

## Cel gameplayowy

Gracz klika akcję na mapie, a system szuka aplikacji po `app.map_actions`, nie po zgadywaniu typu, nazwy albo `detects`.

## UX

* Klik akcji mapy.
* Jeśli brak aplikacji: jasny komunikat.
* Jeśli jedna aplikacja: start.
* Jeśli kilka aplikacji: przygotowanie do Sprintu 2.

## Przepływ danych

```text
map_action_id
↓
installed apps
↓
app.map_actions
↓
matching apps
↓
launch app
```

## Systemy

* mapa,
* backend `/hack-action` lub przyszły router map actions,
* `profile.apps`,
* launch queue,
* `/command`,
* desktop launcher.

## Kryteria akceptacji

* `scan_ports` szuka aplikacji z `map_actions: ["scan_ports"]`.
* `trace_gps` szuka aplikacji z `map_actions: ["trace_gps"]`.
* Brak aplikacji daje: `Brak aplikacji obsługującej tę akcję`.
* Stary fallback po `detects/type` może działać tylko jako migracja.

---

# Sprint 2 — Tool Selection UX

## Cel gameplayowy

Gracz zaczyna rozumieć, że jego arsenał ma znaczenie.

## UX

Jeśli wiele aplikacji obsługuje tę samą akcję:

* otwiera się File Manager w `/tools`,
* pasujące narzędzia są podświetlone,
* gracz wybiera narzędzie,
* terminal może odpalić narzędzie po nazwie lub aliasie z kontraktu.

## Przepływ danych

```text
map_action_id
↓
matching apps
↓
/tools highlight
↓
player selects app
↓
launch selected app
```

## Systemy

* File Manager,
* `/tools`,
* terminal command,
* app launcher,
* map action router.

## Kryteria akceptacji

* Dwie aplikacje do `sniff` pokazują wybór.
* Podświetlenie bazuje na `app.map_actions`.
* Brak narzędzi nie otwiera pustego katalogu, tylko pokazuje komunikat.

---

# Sprint 3 — Operation Core

## Cel gameplayowy

Aplikacja przestaje być końcem akcji. Aplikacja tworzy operację.

## UX

Po uruchomieniu aplikacji gracz widzi:

* start operacji,
* status,
* czas,
* target,
* potencjalny wynik.

## Przepływ danych

```text
Application
↓
operation instance
↓
status: start/running/completed/failed
```

## Systemy

* operation store,
* profile/user store,
* app launcher,
* map action router.

## Kryteria akceptacji

* Powstaje instancja operacji z `operation_id`.
* Operacja ma `operation_type`, `owner_username`, `source_app_id`, `map_action_id`, `target_type`, `status`, `started_at`, `expires_at`.
* Operacje można odczytać z lekkiego endpointu lub panelu.

---

# Sprint 4 — Active Operations Panel + Active Map Objects

## Cel gameplayowy

Gracz widzi, że operacje żyją po starcie aplikacji.

## UX

Na mapie lub w panelu pojawiają się:

* aktywny stream kamery,
* aktywny tracking,
* aktywny sniffer,
* timer operacji.

## Przepływ danych

```text
operation running
↓
active_object
↓
map / panel display
```

## Systemy

* mapa,
* operation store,
* active operations endpoint,
* desktop toast/status.

## Kryteria akceptacji

* `camera_stream` pokazuje licznik.
* `persistent_sniffer` pokazuje implant/timer.
* `vehicle_tracking` pokazuje aktywny marker.
* Zamknięcie i otwarcie mapy odtwarza aktywne operacje.

---

# Sprint 5 — Movement Refresh Engine

## Cel gameplayowy

Świat zaczyna się poruszać bez realtime loopa.

## UX

Przy refreshu mapy gracz widzi zaktualizowane pozycje lub timery.

## Przepływ danych

```text
started_at + duration + procedural_seed + movement_model
↓
computed current state
↓
map refresh
```

## Systemy

* `movement_model`,
* operation refresh,
* mapa,
* active object display.

## Kryteria akceptacji

* Brak pętli liczącej świat co sekundę.
* Pozycja pojazdu lub telefonu jest wyliczana przy refreshu.
* Timer streamu kamery działa po reloadzie mapy.
* Checkpointy powstają tylko jako eventy gameplayowe.

---

# Sprint 6 — Vehicle Tracking + GPS Logs

## Cel gameplayowy

Pierwsza kompletna ścieżka operacji mobilnej:

```text
vehicle → trace_gps → vehicle_tracking → gps_logs → file
```

## UX

Gracz śledzi pojazd i po zakończeniu dostaje plik GPS.

## Przepływ danych

```text
vehicle target
↓
trace_gps
↓
GPS Tracker
↓
vehicle_tracking
↓
gps_logs / location_history
↓
/data/gps
```

## Systemy

* mapa,
* `road_movement`,
* operation store,
* resource generation,
* file inventory.

## Kryteria akceptacji

* Vehicle tracking trwa określony czas.
* Marker pojazdu aktualizuje się przy refreshu.
* Po zakończeniu powstaje plik w `/data/gps`.
* Plik ma kompletność i metadane operacji.

---

# Sprint 7 — Device Tracking + Device Intelligence

## Cel gameplayowy

Telefon/osoba/gracz stają się źródłem paczek wywiadowczych.

## UX

Gracz widzi, że różne aplikacje produkują różny zakres danych.

Przykładowe paczki:

* lokalizacja,
* device logs,
* call history,
* messenger data,
* personal records.

## Przepływ danych

```text
person/phone/player
↓
trace_device
↓
device_tracking
↓
resource package
↓
/data/device or /data/personal
```

## Systemy

* `device_tracking`,
* `local_walk`,
* `carrier_movement`,
* resource completeness,
* file grouping.

## Kryteria akceptacji

* Basic app produkuje małą paczkę.
* Lepsza app produkuje bogatszą paczkę.
* Wartość paczki zależy od kompletności.
* Player target używa tych samych zasad, ale respektuje bezpieczeństwo PvP.

---

# Sprint 8 — Camera Stream + Camera Shutdown

## Cel gameplayowy

Kamery stają się oczami świata: można je oglądać, zakłócać i wyciągać materiał.

## UX

* `camera_stream` pokazuje licznik nagrania.
* `camera_shutdown` pokazuje czas wyłączenia/zakłócenia.
* Stream może produkować `camera_dump` albo `video_material`.

## Przepływ danych

```text
camera
↓
camera_stream / camera_shutdown
↓
active timer
↓
camera_dump or video_material
↓
/data/camera
```

## Systemy

* camera target menu,
* active object timer,
* risk reducer,
* resource generation.

## Kryteria akceptacji

* Stream przeżywa reload mapy.
* Shutdown wpływa na ryzyko innych działań.
* Materiał kamery trafia do `/data/camera`, jeśli aplikacja go zapisuje.

---

# Sprint 9 — Audio + Microphone Sniffer

## Cel gameplayowy

Mikrofony i lokacje stają się uszami świata.

## UX

Gracz uruchamia podsłuch i dostaje transkrypcję.

## Przepływ danych

```text
person/venue
↓
mic_sniff / audio_hack
↓
microphone_sniffer / audio_interference
↓
audio_transcript
↓
/data/audio
```

## Systemy

* person/venue target menu,
* audio operations,
* transcript file,
* risk.

## Kryteria akceptacji

* Podsłuch tworzy `audio_transcript`.
* Transkrypcja ma preview mode `transcript`.
* Audio może być sprzedane w kategorii `audio`.

---

# Sprint 10 — ATM + Persistent Sniffer

## Cel gameplayowy

ATM i infrastruktura finansowa produkują pierwsze wartościowe paczki wysokiego ryzyka.

## UX

Gracz może:

* odczytać logi ATM,
* zainstalować sniffer,
* poczekać na dane,
* odebrać dump.

## Przepływ danych

```text
atm/router/server
↓
atm_logs / install_sniffer
↓
atm_log_extraction / persistent_sniffer
↓
atm_dump / financial_records / credentials
↓
/data/atm / /data/financial / /data/credentials
```

## Systemy

* ATM target menu,
* implant timer,
* resource buffer,
* file generation,
* risk.

## Kryteria akceptacji

* `atm_log_extraction` jest krótką operacją.
* `persistent_sniffer` jest aktywnym obiektem.
* Dane wysokiej wartości generują wyższe ryzyko.

---

# Sprint 11 — File Inventory v1

## Cel gameplayowy

Pliki przestają być listą tekstową. Stają się inventory danych.

## UX

File Manager pokazuje:

* `/tools`,
* `/data/gps`,
* `/data/device`,
* `/data/audio`,
* `/data/camera`,
* `/data/atm`,
* `/data/credentials`,
* `/data/financial`,
* `/data/personal`,
* `/data/network`,
* `/data/vehicle`,
* `/market`,
* `/projects`.

## Przepływ danych

```text
resource
↓
file_category
↓
directory
↓
preview mode
```

## Systemy

* File Manager,
* file store,
* resource-to-file mapping,
* previews.

## Kryteria akceptacji

* Pliki mają kategorie.
* Pliki mają preview mode.
* `/tools` działa jako katalog aplikacji.
* `/data/*` działa jako katalog lootu.

---

# Sprint 12 — Ghost Exchange MVP

## Cel gameplayowy

Gracz ma gdzie sprzedać dane.

## UX

W Browserze pojawia się Ghost Exchange obok Googleplexa.

## Przepływ danych

```text
sellable file
↓
Ghost Exchange
↓
market category
↓
price preview
```

## Systemy

* Browser,
* market view,
* file inventory,
* data economy.

## Kryteria akceptacji

* Ghost Exchange pokazuje sprzedawalne pliki.
* Pliki niesprzedawalne nie trafiają do sprzedaży.
* Kategorie rynku są zgodne z `data_economy.md`.

---

# Sprint 13 — Sale Flow + Mail + HC

## Cel gameplayowy

Pierwsze pełne domknięcie pętli:

```text
file → sale → mail → HC
```

## UX

Gracz sprzedaje plik, dostaje mail i widzi wzrost HC.

## Przepływ danych

```text
File
↓
Listing
↓
Buyer simulation
↓
Sale
↓
HackCoin transfer
↓
Mail
↓
File removed from /data
```

## Systemy

* Ghost Exchange,
* wallet/profile HC,
* mail,
* file lifecycle,
* market history.

## Kryteria akceptacji

* Sprzedaż generuje mail.
* HC trafiają do gracza.
* Plik znika z `/data`.
* Wpis zostaje w `/market/history` albo `/market/sold`.

---

# Sprint 14 — Risk MVP

## Cel gameplayowy

Operacje zaczynają mieć koszt ryzyka.

## UX

Gracz dostaje ostrzeżenia, cooldowny albo konsekwencje.

## Przepływ danych

```text
Action
↓
Risk signal
↓
Risk score
↓
Risk event
↓
Consequence
```

## Systemy

* risk event store,
* operations,
* map actions,
* mail/toasts,
* profile status.

## Kryteria akceptacji

* Nie ma losowania co sekundę.
* Ryzyko liczy się po zakończeniu albo w kontrolowanych punktach.
* `scan_ports` może generować risk signal.
* `atm_alarm`, `camera_detected`, `long_operation_detected` działają jako eventy.

---

# Sprint 15 — Support Operations + Risk Reducers

## Cel gameplayowy

Gracz zaczyna planować operacje, a nie tylko klikać najbardziej dochodową akcję.

## UX

Operacje wspierające:

* wyłącz kamerę,
* spoofing,
* anonymizer,
* low noise mode,
* stealth app.

## Przepływ danych

```text
support operation
↓
support_effects
↓
risk modifier
↓
main operation
```

## Systemy

* operations,
* risk modifiers,
* app contract,
* active operation state.

## Kryteria akceptacji

* `camera_shutdown` obniża ryzyko `camera_detected`.
* Support operation sama może mieć ryzyko.
* Gracz widzi efekt wsparcia przed główną operacją.

---

# Sprint 16 — Operation Lifecycle + Cleanup

## Cel gameplayowy

Operacje mają konsekwencje, jeśli zostaną porzucone albo wygasną.

## UX

Gracz widzi:

* running,
* completed,
* failed,
* detected,
* cancelled,
* timeout.

## Przepływ danych

```text
operation status
↓
expiry / cancel / detect
↓
cleanup
↓
file/resource/risk result
```

## Systemy

* operation scheduler / refresh,
* risk,
* file generation,
* active object cleanup.

## Kryteria akceptacji

* Wygasła operacja nie zostawia martwego markera.
* Porzucona operacja może generować `abandoned_operation`.
* Timeout generuje poprawny status.

---

# Sprint 17 — Resource Completeness + Pricing

## Cel gameplayowy

Lepsze aplikacje realnie dają lepsze dane i większy zarobek.

## UX

Plik pokazuje kompletność:

```text
Device Dump
✓ location_history
✓ device_logs
✓ personal_records
✕ credentials
✕ messenger_data
```

## Przepływ danych

```text
app quality
↓
resource completeness
↓
file metadata
↓
market price
```

## Systemy

* resource model,
* file model,
* data economy,
* Ghost Exchange pricing.

## Kryteria akceptacji

* Cena zależy od kompletności.
* Dwie aplikacje tego samego typu mogą dawać różne wyniki.
* File preview pokazuje kompletność paczki.

---

# Sprint 18 — Googleplex Progression Integration

## Cel gameplayowy

HC wracają do progresu przez zakup nowych aplikacji.

## UX

Gracz po sprzedaży danych kupuje lepsze aplikacje w Googleplex.

## Przepływ danych

```text
HackCoins
↓
Googleplex
↓
buy app
↓
/tools
↓
new map actions/resources
```

## Systemy

* Googleplex,
* install app,
* profile apps,
* `/tools`,
* app contract.

## Kryteria akceptacji

* Nowa aplikacja pojawia się w `/tools`.
* Aplikacja ma `app.map_actions`.
* Nowa aplikacja odblokowuje nowe lub lepsze wyniki.

---

# Sprint 19 — Integration Playtest + Balance Pass

## Cel gameplayowy

Cała pętla działa jako jedna gra, a nie zbiór osobnych mechanik.

## UX

Scenariusz testowy:

```text
wejdź na mapę
↓
wybierz target
↓
uruchom aplikację
↓
operacja działa
↓
powstaje plik
↓
sprzedaj plik
↓
dostań mail i HC
↓
kup nową aplikację
↓
wróć na mapę
```

## Przepływ danych

Pełna pętla od `World Object` do `Back to Map`.

## Systemy

Wszystkie.

## Kryteria akceptacji

* Nie ma martwych końców.
* Każdy plik ma źródło.
* Każda sprzedaż ma mail i HC.
* Każda aplikacja ma kontrakt.
* Każda operacja ma status i koniec.

---

# Sprint 20 — Gameplay Loop Closure v1

## Cel gameplayowy

Pierwsza grywalna wersja pętli danych.

## UX

Gracz rozumie:

* po co skanuje,
* po co kupuje aplikacje,
* po co uruchamia operacje,
* po co zbiera pliki,
* po co sprzedaje dane,
* po co wraca na mapę.

## Przepływ danych

```text
World Object
↓
Map Action
↓
Application
↓
Operation
↓
Movement
↓
Resource
↓
File
↓
Ghost Exchange
↓
Mail
↓
HackCoins
↓
New Apps
↓
Back to Map
```

## Systemy

* mapa,
* aplikacje,
* operacje,
* movement,
* zasoby,
* pliki,
* Ghost Exchange,
* mail,
* Wallet/HC,
* Googleplex,
* risk.

## Kryteria akceptacji

* Pętla jest grywalna od początku do końca.
* Każdy element ma feedback dla gracza.
* Ryzyko nie jest dekoracją, tylko wpływa na decyzje.
* Dane są realnym towarem.
* Googleplex jest realnym progressem.

---

# Sprint 21+ — Rozszerzenia po domknięciu pętli

Te sprinty są poza pierwszą pętlą implementacyjną.

## Możliwe kierunki

* player-to-player trading,
* rynki frakcyjne,
* dynamiczny popyt Ghost Exchange,
* zaawansowane konsekwencje ryzyka,
* jail loop,
* wanted level per miasto/frakcja,
* research tree GhostLab,
* custom pro-system-tools runtime,
* AI/NPC buyers,
* kontrakty frakcyjne,
* data laundering,
* odzyskiwanie sprzedanych danych,
* archiwum historyczne gracza.

Decision:

* Przyjęto: Sprinty 1–20 domykają pierwszą pełną wersję pętli gameplayu.
* Przyjęto: Sprint 21+ nie powinien wyprzedzać domknięcia pętli danych.

---

# Faza A — Architektura gry

Faza A porządkuje fundamenty po gameplay loop v1. Nie chodzi jeszcze o pełny kreator dla gracza, tylko o to, żeby runtime, katalog aplikacji, pojemność, waga i jakość mówiły jednym językiem.

---

# Sprint 21 — Audit

## Cel gameplayowy

Gracz i projektant systemu widzą, które aplikacje są tylko UI, które są narzędziami mapy, a które tworzą operacje i dane.

Ten sprint porządkuje fundament pod Googleplex Tool Laboratory bez przebudowy kreatorów.

## UX

Googleplex i File Manager zaczynają pokazywać aplikację jako kontrakt:

```text
interface
↓
map_actions
↓
operation_types
↓
resource_types
↓
file_size / disk_usage
↓
quality / reliability
```

## Przepływ danych

```text
app_config / json_resources
↓
app contract audit
↓
Googleplex card
↓
files.tools
↓
map action runtime
```

## Systemy

* Googleplex,
* app contract,
* File Manager,
* `/tools`,
* `map_actions`,
* `operation_types`,
* `resource_types`,
* `target_types`.

## Dokumentacja

Uzupełnić:

* `doc/app_contract.md` — `file_size`, `disk_usage`, `quality_score`, `reliability`.
* `doc/file_model.md` — aplikacje i pliki jako obiekty z wagą.
* `doc/map_interactions.md` — wybór narzędzia nie może mieszać targetów ani globalnego stanu.

## Kryteria akceptacji

* Wiadomo, które aplikacje mają jawne `map_actions`.
* Wiadomo, które aplikacje są tylko `migration_inferred`.
* Googleplex pokazuje kontrakt aplikacji czytelnie.
* File Manager `/tools` pokazuje, dlaczego narzędzie pasuje do akcji mapy.
* Runtime mapy nie zostaje przebudowany.

---

# Sprint 21.5 — Gameplay Contract

## Cel gameplayowy

Zanim kreatory zaczną tworzyć nowe narzędzia, gra musi mieć spójny kontrakt tego, czym jest aplikacja gameplayowa.

Sprint 21.5 zamienia audyt ze Sprintu 21 w jawny kontrakt projektowy i runtime checklistę.

## UX

Gracz jeszcze nie dostaje dużej nowej funkcji, ale Googleplex, File Manager i przyszły kreator zaczynają używać tych samych pojęć:

```text
narzędzie
↓
środowisko działania
↓
akcja mapy
↓
operacja
↓
zasób
↓
plik
↓
waga
↓
jakość
↓
ryzyko
```

## Przepływ danych

```text
doc/app_contract.md
↓
runtime app normalization
↓
Googleplex metadata
↓
File Manager metadata
↓
tool selection
```

## Systemy

* `normalize_app_contract()`,
* `googleplex_catalog_payload()`,
* `serialize_tool_selection_app()`,
* File Manager preview,
* Googleplex cards,
* app creator payload.

## Dokumentacja

Uzupełnić:

* `doc/app_contract.md` — finalna lista pól wymaganych dla gameplay tool.
* `doc/gameplay_terms.md` — dopisać `file_size`, `disk_usage`, `quality_score`, `reliability`, `creator_power`.
* `doc/file_model.md` — rozróżnić wagę aplikacji i wagę pliku danych.

## Kryteria akceptacji

* Wiadomo, które pola są obowiązkowe dla runtime, a które są tylko opisowe.
* Wiadomo, które pola tworzą UI, a które gameplay.
* Fallback legacy jest opisany jako migracja.
* Przyszły wizard nie musi zgadywać nazw pól.
* Nie ma zmian w mechanice mapy ani ekonomii.

---

# Sprint 22 — Disk Capacity + Tool File Size

## Cel gameplayowy

Pulpit gracza zaczyna mieć ograniczenia zasobów. Aplikacje i pliki danych mają wagę, więc arsenał nie jest nieskończony.

## UX

Gracz widzi:

* pojemność dysku,
* zajęte miejsce,
* wagę aplikacji przed zakupem,
* wagę pliku danych,
* ostrzeżenie, gdy instalacja lub zapis pliku zbliża się do limitu.

Na start limit może być miękki: ostrzeżenie zamiast blokady.

## Przepływ danych

```text
app.file_size / app.disk_usage
↓
install preview
↓
profile.storage_used
↓
files.* file_size
↓
File Manager usage bar
```

## Systemy

* `profile.storage_capacity`,
* `profile.storage_used`,
* `app.file_size`,
* `file.file_size`,
* Googleplex,
* File Manager,
* `/install-app`.

## Dokumentacja

Uzupełnić:

* `doc/file_model.md` — `file_size`, `disk_usage`, `storage_capacity`, `storage_used`.
* `doc/app_contract.md` — `install_size` / `disk_usage` jako część kontraktu aplikacji.
* `doc/resource_types.md` — bazowe wagi typów danych.

## Kryteria akceptacji

* Każda aplikacja w Googleplex ma wagę albo domyślną wagę.
* Każdy nowy plik gameplayowy ma `file_size`.
* File Manager pokazuje użycie dysku.
* Instalacja aplikacji pokazuje wpływ na pojemność.
* Brak regresji sprzedaży i generowania plików.

---

# Sprint 23 — Tool Quality + Creator Power

## Cel gameplayowy

Poziom i reputacja twórcy zaczynają mieć znaczenie. Dwie aplikacje tego samego typu mogą mieć inną jakość, niezawodność i wagę.

## UX

Gracz w Googleplex widzi:

* poziom narzędzia,
* jakość,
* niezawodność,
* ryzyko awarii,
* twórcę,
* przewidywaną jakość danych.

Twórca widzi w kreatorze, że jego poziom wpływa na wynik publikacji.

## Przepływ danych

```text
creator level / respect
↓
creator_power
↓
quality_score
↓
reliability
↓
operation quality
↓
file completeness / price preview
```

## Systemy

* profile level/respect,
* `creator_username`,
* `creator_nick`,
* `creator_power`,
* `quality_score`,
* `reliability`,
* operation finalizers,
* Ghost Exchange price preview.

## Dokumentacja

Uzupełnić:

* `doc/app_contract.md` — `quality_score`, `reliability`, `creator_power`.
* `doc/resource_types.md` — wpływ jakości aplikacji na kompletność zasobów.
* `doc/data_economy.md` — jakość jako mnożnik ceny.

## Kryteria akceptacji

* Aplikacje mają `quality_score` i `reliability`.
* Lepszy twórca tworzy lepsze narzędzie.
* Jakość aplikacji wpływa na kompletność pliku albo `quality_score` pliku.
* Googleplex pokazuje jakość narzędzia.
* Ghost Exchange uwzględnia jakość danych.

---

# Faza B — Edukacja gracza

Faza B zmienia kreatory z formularzy w proces uczenia gracza. Gracz ma zrozumieć, że narzędzie jest decyzją projektową: do czego działa, co produkuje, ile waży, jak ryzykuje i jaką ma jakość.

---

# Sprint 24 — Map Tool Classification Cleanup

## Cel gameplayowy

Arsenał gracza staje się zrozumiały. Narzędzia nie podświetlają się przy złej akcji mapy tylko dlatego, że stare pola `detects/type` coś zasugerowały.

## UX

Przy wyborze narzędzia z mapy gracz widzi tylko sensowne narzędzia.

Przykład:

* `scan_ports` pokazuje skanery/recon.
* `exploit` pokazuje exploity.
* `sniff` pokazuje sniffery.
* `trace_gps` pokazuje trackery GPS.

PenCombo / exploit_suite nie powinno być pokazywane jako `scan_ports`, jeśli kontrakt nie mówi tego jawnie.

## Przepływ danych

```text
map_action_id
↓
explicit app.map_actions
↓
tool selection
↓
selected_app_id
↓
operation
```

## Systemy

* `get_apps_for_map_action()`,
* `infer_legacy_map_actions()`,
* `map_actions_source`,
* migracja katalogu aplikacji,
* File Manager `/tools`.

## Dokumentacja

Uzupełnić:

* `doc/app_contract.md` — fallback legacy jako `TODO_MIGRATION`, nie główny router.
* `doc/map_actions.md` — lista dozwolonych klas narzędzi dla każdej akcji.
* `doc/gameplay_matrix.md` — support-only vs data-producing.

## Kryteria akceptacji

* Jawne `app.map_actions` wygrywa zawsze.
* Fallback legacy można wyłączyć flagą dev/test.
* Aplikacje `migration_inferred` są oznaczone w Googleplex.
* Narzędzia podświetlane w `/tools` odpowiadają akcji mapy.
* Testy obejmują PenCombo / exploit_suite i `scan_ports`.

---

# Sprint 25 — Step-by-Step Tool Creator UX

## Cel gameplayowy

Kreator aplikacji przestaje być formularzem JSON. Gracz projektuje narzędzie świadomie, krok po kroku.

## UX

Wizard:

```text
1. Typ narzędzia
2. Środowisko działania
3. Akcje mapy / desktopu
4. Operacje
5. Zasoby
6. Ryzyko
7. Waga / pojemność
8. Jakość / niezawodność
9. Podsumowanie
10. Publikacja
```

To nadal wykorzystuje istniejące ButtonMaker, TermCreator, WindowMaker i AppForge. Nie tworzymy drugiego sklepu ani drugiego publishera.

## Przepływ danych

```text
creator wizard
↓
draft app contract
↓
validation
↓
/api/apps/generate
↓
json_resources.app_config
↓
Googleplex
```

## Systemy

* kreatory UI w `terminal.js`,
* `/api/apps/generate`,
* `build_generated_app()`,
* Googleplex,
* `profile.files.projects`.

## Dokumentacja

Uzupełnić:

* `doc/app_contract.md` — minimalny kontrakt aplikacji tworzonej przez gracza.
* `doc/file_model.md` — projekty i pliki tools jako inventory.
* `doc/resource_architecture.md` — publikacja zmienia SQLite `json_resources`, nie statyczny JSON.

## Kryteria akceptacji

* Kreator prowadzi przez jawne `map_actions`.
* Kreator pokazuje wagę, jakość i ryzyko przed publikacją.
* Opublikowana aplikacja ma pełny kontrakt.
* Stare kreatory nadal działają jako uproszczone tryby.

---

# Sprint 26 — Scanner Path

## Cel gameplayowy

Gracz może stworzyć własne narzędzie skanujące/recon, które działa w istniejącym runtime mapy.

## UX

Ścieżka Scanner:

* wybór targetów,
* wybór `map_actions`: `scan_ports`, `trace`, `trace_device`, `scan_hotspots`,
* wybór, czy wynik jest tylko `internal_recon_state`, czy tworzy plik,
* wybór jakości i zasięgu,
* podgląd ryzyka.

## Przepływ danych

```text
scanner blueprint
↓
app.map_actions
↓
operation_types
↓
resource_types
↓
quality/reliability
↓
Googleplex app
```

## Systemy

* AppForge / Tool Creator wizard,
* `scan_ports`,
* `trace`,
* `trace_device`,
* `scan_hotspots`,
* operation core,
* File Manager.

## Dokumentacja

Uzupełnić:

* `doc/map_actions.md` — scanner actions.
* `doc/operations.md` — które skanery tworzą operacje, a które tylko stan rozpoznania.
* `doc/resource_types.md` — `internal_recon_state` i dane sieciowe.

## Kryteria akceptacji

* Custom scanner instaluje się z Googleplex.
* Custom scanner pojawia się w `/tools`.
* Custom scanner podświetla się tylko dla swoich `map_actions`.
* Custom scanner może tworzyć operację albo tylko stan support.
* Nie powstają sprzedawalne pliki, jeśli aplikacja ich nie deklaruje.

---

# Sprint 27 — Exploit Path

## Cel gameplayowy

Gracz może stworzyć narzędzie ofensywne: exploit albo sniffer, z jasnym kosztem ryzyka.

## UX

Ścieżka Exploit/Sniffer:

* wybór celu: router, server, ATM, camera, player target,
* wybór `map_actions`: `exploit`, `sniff`, `install_sniffer`,
* wybór czasu działania,
* wybór typów zasobów,
* wybór hałasu/ryzyka,
* podgląd skuteczności i wykrywalności.

## Przepływ danych

```text
offensive blueprint
↓
map action
↓
operation
↓
risk_state
↓
resource buffer
↓
file
```

## Systemy

* exploit runtime,
* persistent sniffer,
* risk MVP,
* support operations,
* operation finalizers,
* Ghost Exchange.

## Dokumentacja

Uzupełnić:

* `doc/risk_events.md` — wpływ jakości i hałasu aplikacji na ryzyko.
* `doc/operations.md` — custom exploit/sniffer jako wariant istniejących operacji.
* `doc/app_contract.md` — `noise_level`, `failure_rate`, `risk_modifier`.

## Kryteria akceptacji

* Custom exploit/sniffer ma jawne `operation_types`.
* Narzędzie może generować pliki tylko zgodnie z `resource_types`.
* Ryzyko uwzględnia jakość i hałas.
* Tool selection nie miesza exploitów ze scannerami.

---

# Faza C — Endgame

Faza C domyka endgame narzędzi: GhostLab, balans ekonomii aplikacji i Googleplex Tool Laboratory v1 jako pełny warsztat tworzenia narzędzi.

---

# Sprint 28 — GhostLab Pro Tools Contract

## Cel gameplayowy

GhostLab staje się ścieżką dla zaawansowanych narzędzi pro-system-tools, ale nadal korzysta z tego samego modelu aplikacji Googleplex.

## UX

GhostLab pokazuje pipeline:

```text
Project
↓
Template
↓
Blueprint
↓
Validate
↓
Compile
↓
Artifact
↓
Publisher
↓
Googleplex
```

Custom pro-system-tool może być kupiony i zainstalowany, ale jego runtime nie może omijać Player Hack Access.

## Przepływ danych

```text
files.pro_system_projects
↓
compiled artifact
↓
pro-system-tool app contract
↓
json_resources.app_config
↓
Googleplex
↓
profile.apps
```

## Systemy

* GhostLab,
* Publisher,
* Googleplex,
* Player Hack Access,
* pro-system-tools.

## Dokumentacja

Uzupełnić:

* `doc/app_contract.md` — pro-system-tool jako zwykła aplikacja z dodatkowymi wymaganiami.
* `doc/operations.md` — custom pro-tools nie tworzą nowych operacji bez osobnego runtime.
* `doc/resource_architecture.md` — Publisher zapisuje do SQLite runtime catalog.

## Kryteria akceptacji

* GhostLab publikuje pełny kontrakt aplikacji.
* Custom pro-system-tool instaluje się jak każda aplikacja.
* Tool nie działa bez aktywnego Player Hack Access.
* Googleplex pokazuje wymagania, wagę, jakość i ryzyko.

---

# Sprint 29 — Tool Balance Pass + Pricing

## Cel gameplayowy

Rynek aplikacji zaczyna być czytelny ekonomicznie. Cena narzędzia wynika z jego mocy, jakości, ryzyka, wagi i poziomu wymagań.

## UX

Googleplex pokazuje:

* cena,
* poziom,
* respect,
* waga,
* jakość,
* ryzyko,
* przewidywany typ wyniku.

Gracz rozumie, dlaczego droższe narzędzie jest lepsze.

## Przepływ danych

```text
app contract
↓
power score
↓
price hint
↓
Googleplex price
↓
install decision
```

## Systemy

* Googleplex,
* app pricing,
* creator app generation,
* quality/reliability,
* storage/disk usage,
* Ghost Exchange economy.

## Dokumentacja

Uzupełnić:

* `doc/data_economy.md` — relacja ceny aplikacji do potencjalnego zwrotu z danych.
* `doc/app_contract.md` — `price_hint`, `power_score`.
* `doc/file_model.md` — waga aplikacji a decyzja instalacji.

## Kryteria akceptacji

* Cena aplikacji nie jest ręczną liczbą bez kontekstu.
* Aplikacja o większej jakości/zakresie ma większy koszt.
* Waga aplikacji wpływa na decyzję instalacji.
* Testowe ceny nie psują pętli HC -> Googleplex -> lepsze dane.

---

# Sprint 30 — Googleplex Tool Laboratory v1

## Cel gameplayowy

Googleplex Tool Laboratory domyka pierwszą wersję warsztatu tworzenia narzędzi. Gracz nie edytuje JSON-a, tylko projektuje aplikację jako realny element gameplayu.

## UX

Laboratorium łączy:

* AppForge,
* ButtonMaker,
* TermCreator,
* WindowMaker,
* GhostLab,
* Googleplex Publisher,
* app contract preview.

Gracz wybiera ścieżkę:

```text
Simple Tool
Map Tool
Data Tool
Offensive Tool
Pro System Tool
```

Każda ścieżka prowadzi przez te same pojęcia:

```text
interface
map_actions
target_types
operation_types
resource_types
risk
file_size
quality
reliability
price
publish
```

## Przepływ danych

```text
laboratory wizard
↓
validated app contract
↓
generated project
↓
publish
↓
json_resources.app_config
↓
Googleplex
↓
install
↓
/tools
↓
map runtime
↓
uninstall
```

## Systemy

* wszystkie kreatory,
* GhostLab,
* Googleplex,
* app contract,
* storage model,
* quality model,
* map tool selection.

## Dokumentacja

Uzupełnić:

* `doc/app_contract.md` — finalny kontrakt aplikacji tworzonej przez gracza.
* `doc/file_model.md` — aplikacja jako plik/narzędzie z wagą.
* `doc/resource_architecture.md` — publikacja i sync katalogu.
* `doc/project_journal.md` — podsumowanie zamknięcia Tool Laboratory v1.

## Kryteria akceptacji

* Gracz tworzy aplikację bez ręcznej edycji JSON.
* Aplikacja ma pełny kontrakt.
* Aplikacja pojawia się w Googleplex.
* Można ją kupić, zainstalować i zobaczyć w `/tools`.
* Jeśli ma `map_actions`, działa z wyborem narzędzia na mapie.
* Pojemność dysku, waga, jakość, ryzyko i cena są widoczne przed publikacją i instalacją.

---

# Sprint 30.5 — Guided Tool Laboratory Experience

## Cel gameplayowy

Kreatory przestają wyglądać jak techniczny formularz. Gracz jest prowadzony
krok po kroku przez decyzje projektowe i rozumie, dlaczego każda z nich ma
znaczenie.

Sprint 30.5 nie zmienia kontraktu aplikacji, runtime, ekonomii, storage ani
publish flow. To warstwa UX i narracji nad istniejącym Tool Laboratory v1.

## UX

Każdy krok kreatora ma:

* tytuł,
* subtitle,
* opis,
* edukacyjną notkę,
* gameplay hint.

Nazwy techniczne zostają w kontrakcie, ale UI mówi językiem gracza:

```text
target_types      -> Jakim obiektem chcesz się zająć?
map_actions       -> Skąd gracz ma uruchamiać narzędzie?
operation_types   -> Co ma zrobić Twoje narzędzie?
resource_types    -> Jakich informacji ma szukać?
tool_mode         -> Gdzie będzie działało?
quality_score     -> Jak dopracowane jest narzędzie?
```

## Przepływ decyzji

```text
rodzina narzędzia
↓
tryb działania
↓
typ celu
↓
sensowne akcje / operacje / zasoby
↓
preview kontraktu
↓
publish
```

## Systemy

* AppForge,
* TermCreator,
* WindowMaker,
* ButtonMaker,
* GhostLab jako kompatybilny publish path,
* Googleplex Tool Laboratory v1.

## Dokumentacja

Uzupełnić:

* `doc/app_contract.md` — guided UX nie zmienia pól kontraktu.
* `doc/gameplay_terms.md` — pojęcia `guided_step`, `educational_note`,
  `gameplay_hint`.
* `doc/project_journal.md` — wpis Sprintu 30.5.

## Kryteria akceptacji

* Kreator pokazuje jeden etap decyzji naraz.
* Każdy etap ma narrację i wyjaśnienie konsekwencji.
* Wybór rodziny/trybu/celu zawęża kolejne listy.
* UI nie używa nagłówków typu `operation_types` jako głównego języka gracza.
* Nie zmieniono backendowego kontraktu aplikacji.
* Nie dodano nowego kreatora ani publish flow.

---

# Sprint 31 — Database Migration & Server Upgrade Scripts

## Cel gameplayowy

Gra wchodzi w etap, w którym baza produkcyjna/testowa żyje na serwerze i nie jest wersjonowana w Git. Każda zmiana struktury danych musi mieć własną, bezpieczną migrację.

Ten sprint nie dodaje nowych mechanik. Chroni istniejący świat graczy przed ręcznymi zmianami w SQLite.

## UX

Gracz nie widzi nowego ekranu, ale zyskuje stabilność:

* aktualizacje gry nie kasują profilu,
* nowe pola pojawiają się bez resetu kont,
* storage, jakość i nowe kontrakty aplikacji mogą być dodawane bez ręcznego grzebania w bazie,
* deploy serwera ma powtarzalną procedurę.

## Przepływ danych

```text
git pull
↓
backup DB
↓
run migration
↓
schema_migrations
↓
restart app
↓
gameplay smoke
```

## Systemy

* SQLite runtime DB,
* `json_resources`,
* `users.profile_json`,
* przyszłe pola storage/quality,
* PM2/server deploy,
* `project_journal.md`.

## Etap 0 — App Catalog Cleanup

Przed standardowymi migracjami Sprint 31 porządkuje katalog aplikacji i narzędzi.

Cel:

* wyczyścić `json_resources.app_config` ze starych narzędzi testowych/dev,
* usunąć `admin_test_seed`,
* usunąć albo zastąpić stare `migration_inferred`,
* zachować aplikacje wytworzone przez grę,
* zachować GhostLab published apps,
* dodać produkcyjny zestaw `admin_seed_v1`,
* wyczyścić profile graczy z testowych aplikacji,
* wyczyścić orphan `files.tools`,
* przeliczyć `storage_used`,
* nie usuwać `files.projects`.

Skrypt:

```text
scripts/app_catalog_cleanup.py
```

Tryby:

```bash
python scripts/app_catalog_cleanup.py --db data/game.sqlite3
python scripts/app_catalog_cleanup.py --db data/game.sqlite3 --apply
```

Wymagania:

* dry-run jako domyślny tryb,
* `--apply` jako jedyna ścieżka zapisu,
* backup przed zmianą,
* raport różnic,
* brak destrukcyjnych zmian bez jawnego apply.

Po tym etapie w systemie powinny zostać:

* produkcyjne narzędzia seed/admin_seed_v1,
* narzędzia wytworzone przez grę,
* narzędzia GhostLab,
* narzędzia dopisane świadomie w kolejnych sprintach.

## Struktura migracji

Przyjęty kierunek:

```text
migrations/
  001_add_storage_fields.py
  002_add_app_quality_fields.py
  003_normalize_tool_contracts.py
```

Alternatywnie dopuszczalne:

```text
scripts/db_migrations/
```

Ważne jest jedno stałe miejsce, numeracja i jawna kolejność.

## Zasady migracji

Każda migracja musi być:

* numerowana,
* opisana,
* idempotentna,
* możliwa do uruchomienia drugi raz bez szkody,
* ograniczona do jednego celu,
* testowana lokalnie przed deployem,
* poprzedzona backupem DB,
* zapisana w stanie migracji.

Migracja nie może:

* usuwać danych bez wyraźnej decyzji,
* nadpisywać runtime smoke przypadkiem,
* zakładać, że `data/game.sqlite3` jest w Git,
* mieszać zmian struktury z refaktorem gameplayu.

## Stan migracji

Docelowo dodać tabelę:

```text
schema_migrations
```

Minimalne pola:

* `id`,
* `name`,
* `applied_at`,
* `checksum` albo `script_hash`,
* `status`,
* `notes`.

Jeżeli tabela jeszcze nie istnieje, pierwszy migrator tworzy ją sam.

## Komenda serwerowa

Przykład:

```bash
python migrations/001_add_storage_fields.py --db data/game.sqlite3 --apply
```

Tryby:

* domyślnie `dry-run`,
* zapis tylko z `--apply`,
* opcjonalnie `--backup`,
* opcjonalnie `--rollback`, tylko jeśli rollback jest prosty i bezpieczny.

## Backup

Przed migracją:

```bash
cp data/game.sqlite3 data/backups/game_YYYYMMDD_HHMMSS_before_001.sqlite3
```

Backup jest runtime i nie trafia do Git.

## Rollback

Rollback jest wymagany tylko wtedy, gdy jest prosty i bezpieczny.

Jeżeli migracja dodaje pola domyślne do JSON profili, rollback może być ryzykowny i nie powinien usuwać danych graczy. W takim przypadku rollbackiem jest przywrócenie backupu bazy.

## Checklist deploy

```text
1. git pull
2. sprawdź APP_ENV / branch / tag
3. zatrzymaj albo wycisz ruch, jeśli trzeba
4. backup data/game.sqlite3
5. dry-run migracji
6. run migration --apply
7. sprawdź schema_migrations
8. restart app / pm2 restart
9. gameplay smoke admina
10. sprawdź logi PERF / error
11. dopisz wpis do project_journal.md
```

## Dokumentacja

Uzupełnić:

* `doc/resource_architecture.md` — baza runtime nie jest wersjonowana, migrujemy ją skryptami.
* `doc/project_journal.md` — każda migracja dostaje wpis z datą, nazwą, wynikiem i backupem.
* `README.md` — krótka komenda deploy/migration dla serwera.

## Kryteria akceptacji

* Istnieje katalog migracji.
* Istnieje pierwszy przykład migracji w trybie dry-run/apply.
* Istnieje `schema_migrations` albo równoważny stan migracji.
* Migracja tworzy backup przed zmianą.
* Migracja jest idempotentna.
* Lokalny test migracji przechodzi na kopii bazy.
* Deploy checklist jest opisany.
* `project_journal.md` jest aktualizowany po każdej migracji.

---

# Sprint 32 — Target Bar Feedback Audit & Plan

## Cel gameplayowy

Gracz zaczyna dostawać subtelną informację, czy sekwencja działań na celu
posuwa hack do przodu, ale bez dużego panelu, tutoriala, procentów i dodatkowego
UI poza belką CEL.

Sprint 32 jest audytem i planem. Nie implementuje jeszcze zmian w runtime.

## UX

Belka CEL pozostaje częścią górnego/dolnego statusu systemu.

Stany:

* brak oznaczonego celu:
  * belka CEL zwykła/zielona jak pozostałe statusy,
  * tekst: `CEL brak`,
  * bez kropek,
  * bez progressbara.
* oznaczony cel:
  * belka CEL czerwona jak obecnie,
  * tekst celu zostaje,
  * pod nazwą celu pojawiają się cztery bardzo małe kropki,
  * pod kropkami pojawia się bardzo cienki progressbar rozbrojenia.

Kropki reprezentują:

```text
scan_ports
exploit
sniff
trace
```

Kropka świeci, jeśli odpowiadające `actions_allowed` ma wartość `true`.
Kropka jest wygaszona, jeśli wartość jest `false` albo jej brakuje.

Progressbar pokazuje poziom rozbrojenia celu, nie poziom zabezpieczenia.

## Przepływ danych

```text
/hack-action
↓
profile.aimed_target.actions_allowed
profile.aimed_target.security
↓
/api/profile
↓
toolbarProfile.aimed_target
↓
renderToolbarStatus()
↓
subtelny feedback w sekcji CEL
```

## Systemy

* `profile.aimed_target`,
* `actions_allowed`,
* `security`,
* `/hack-action`,
* `/api/profile`,
* `refreshToolbarProfile()`,
* `renderToolbarStatus()`,
* `system-status-strip`.

## Algorytm planowany

Aktywne kropki:

* użyć kolejności `scan_ports`, `exploit`, `sniff`, `trace`,
* odczytać `profile.aimed_target.actions_allowed`,
* `true` = aktywna kropka,
* `false` / brak = wygaszona kropka,
* brak celu = nie renderować kropek.

Poziom rozbrojenia:

* liczyć tylko booleanowe pola zabezpieczeń zgodne z gameplayowym progiem
  rozbrojenia,
* `true` oznacza aktywne zabezpieczenie,
* `false` oznacza zdjęte zabezpieczenie,
* progress = liczba pól `false` / liczba pól booleanowych w read modelu,
* brak danych = progress 0.

Uwaga architektoniczna:

* jeżeli w przyszłości backend zacznie udostępniać
  `aimed_target.disarm_progress` albo `aimed_target.feedback`, frontend powinien
  automatycznie przejść na backendowy read model,
* lokalne liczenie w Sprincie 33 jest tylko tymczasowym read modelem UI,
* backend pozostaje źródłem prawdy dla tego, co jest zabezpieczeniem.

Nie traktować jako boolean security:

* `anonymity_score`,
* `system_compromise_level`,
* `player_risk_level`,
* `traceability`,
* `system_integrity`,
* `exploit_success_rate`,
* `risk_level`,
* `access_level`.

## Dokumentacja

Uzupełnić:

* `doc/project_journal.md` — wpis audytu Sprintu 32.

## Kryteria akceptacji

* Wiadomo, gdzie renderowana jest belka CEL.
* Wiadomo, skąd frontend bierze `aimed_target`.
* Wiadomo, że `actions_allowed` i `security` są dostępne przez `/api/profile`.
* Wiadomo, że po `/hack-action` toolbar może zostać odświeżony bez nowego
  endpointu.
* Istnieje plan Sprintu 33.
* Nie zmieniono gameplayu, map runtime, operacji ani ekonomii.

---

# Sprint 33 — Target Bar Micro Feedback

## Cel gameplayowy

Gracz widzi na belce CEL bardzo dyskretny sygnał postępu hackowania:
które podstawowe akcje zostały wykonane i czy zabezpieczenia celu są zdejmowane.

To ma być informacja dla spostrzegawczych graczy, nie tutorial.

Feedback pokazuje wyłącznie postęp działań gracza. Nie zdradza pełnej wiedzy o
celu, liczby zabezpieczeń, brakujących kroków ani dokładnego procentu.

## UX

W sekcji CEL dodać:

* cztery małe kropki 5-6px,
* cienki pasek rozbrojenia 2-3px,
* brak tekstu pomocniczego,
* brak legendy,
* brak tooltipów na start,
* brak procentów,
* brak nowego panelu.

Animacje:

* kropka nie zapala się skokowo, tylko przechodzi subtelnie przez stan pośredni
  w 200-300 ms,
* pasek rozbrojenia rośnie płynnie, zamiast przeskakiwać natychmiast,
* przy zmianie celu feedback robi krótki fade out / fade in w 100-150 ms,
* jeśli `actions_allowed` i progress się nie zmieniły, toolbar nie animuje się
  ponownie i nie miga przy zwykłym refreshu.

Zasady kropek:

* kolejność kropek jest stała: `scan_ports`, `exploit`, `sniff`, `trace`,
* pojedyncza kropka nigdy nie znika,
* pojedyncza kropka nigdy nie zmienia pozycji,
* zmienia się wyłącznie stan kropki: wygaszona, animowana, aktywna.

Zasady paska:

* w obrębie jednego oznaczonego celu pasek nie może się cofać,
* cofnięcie paska jest dozwolone wyłącznie po zmianie celu, utracie celu,
  ponownym oznaczeniu celu albo świadomym resecie gameplayowym,
* zwykły refresh profilu, polling i odświeżenie toolbaru nie mogą powodować
  cofania progressu.

Belka nie może rozpychać:

* `ARS`,
* `HC`,
* `LVL`,
* `RSP`,
* trybu mobile.

## Przepływ danych

```text
toolbarProfile.aimed_target
↓
target action dots
↓
target disarm progress
↓
renderToolbarStatus()
↓
CSS micro feedback
```

## Systemy

* `static/js/terminal.js`,
* `static/css/style.css`,
* `renderToolbarStatus()`,
* `calculateToolbarArsenalCoverage()`,
* `system-status-target`.

## Zakres implementacji

1. Dodać małe helpery frontendowe:
   * `getTargetActionDots(aimedTarget)`,
   * `calculateTargetDisarmProgress(aimedTarget)`,
   * opcjonalnie `renderTargetBarFeedback(aimedTarget)`.
2. Rozszerzyć markup `system-status-target` w `renderToolbarStatus()`.
3. Dodać CSS dla kropek i paska.
4. Dodać lekki stan poprzedniego feedbacku, żeby animować tylko realną zmianę.
5. Dodać animację kropek, animację paska i fade przy zmianie celu.
6. Zachować monotoniczny progress paska dla aktualnego celu.
7. Zachować obecny czerwony stan belki dla aktywnego celu.
8. Nie dodawać nowego endpointu.
9. Nie zmieniać `/hack-action`.
10. Nie zmieniać warunku przejęcia celu.
11. Nie zmieniać map runtime.

## Testy ręczne

* Brak celu:
  * `CEL brak`,
  * brak kropek,
  * brak progressbara.
* Oznaczony cel:
  * czerwona belka CEL,
  * widoczne cztery kropki,
  * widoczny cienki pasek.
* Po `scan_ports` świeci pierwsza kropka.
* Po `exploit`, `sniff`, `trace` świecą kolejne kropki.
* Po zdjęciu zabezpieczeń pasek rośnie.
* Kropka i pasek animują się tylko wtedy, gdy postęp realnie się zmienił.
* Odświeżenie profilu bez zmiany celu ani postępu nie powoduje migania.
* Zmiana celu robi subtelny fade out / fade in sekcji feedbacku.
* Na małym ekranie belka nie nachodzi na ARS/HC/LVL/RSP.

## Testy automatyczne

Jeśli możliwe dodać test pure helperów:

* brak `aimed_target` zwraca stan neutralny,
* `actions_allowed` mapuje się na cztery kropki,
* pola liczbowe `security` są ignorowane,
* progress liczy tylko boolean security,
* brak `security` daje progress 0,
* ten sam stan feedbacku nie wymusza ponownej animacji,
* zmiana celu resetuje stan animacji.

## Dokumentacja

Uzupełnić:

* `doc/project_journal.md` — wpis po implementacji Sprintu 33.

## Kryteria akceptacji

* Feedback jest widoczny tylko przy oznaczonym celu.
* Feedback działa bez nowego endpointu.
* Kropki odpowiadają `actions_allowed`.
* Pasek odpowiada rozbrojeniu boolean security.
* Brak procentów, legendy i tutoriala.
* Feedback jest animowany subtelnie i tylko przy realnej zmianie postępu.
* Feedback nie zdradza liczby zabezpieczeń ani pełnego stanu celu.
* Pasek nie cofa się w obrębie tego samego celu.
* Brak regresji w mapie, `/hack-action`, operacjach i ekonomii.

## UI Contract

Feedback nie jest elementem mechaniki.

Feedback jest wyłącznie wizualizacją aktualnego stanu gameplayu.

Frontend nigdy nie podejmuje decyzji o stanie celu.

Frontend wyłącznie renderuje dane otrzymane z backendu albo policzone lokalnie
zgodnie z read modelem Sprintu 32.

---

# Sprint 34 — Target Bar UX Polish

## Cel gameplayowy

Domknąć wizualnie sekcję CEL tak, żeby neutralny stan był zwykłym elementem
statusbara, a oznaczony cel uruchamiał rozszerzony tryb hackowania.

## UX

Brak celu:

* kafel wygląda jak `ARS`, `HC`, `LVL`, `RSP`,
* pokazuje tylko `CEL`,
* nie pokazuje `brak`,
* nie renderuje kropek,
* nie renderuje progressbara,
* nie ma czerwieni, glow ani podwyższonej sekcji.

Cel oznaczony:

* kafel dostaje czerwony stan,
* pokazuje nazwę celu,
* pokazuje cztery kropki,
* pokazuje cienki pasek rozbrojenia.

## Systemy

* `renderToolbarStatus()`,
* `system-status-target`,
* CSS statusbara.

## Kryteria akceptacji

* Brak celu renderuje osobny, neutralny markup.
* Aktywny layout celu renderuje się tylko przy realnym `aimed_target`.
* `is-aimed` nie występuje przy braku celu.
* Nie zmieniono backendu, algorytmu progressu ani map runtime.

---

# Faza D — Ghost Exchange jako automatyczny rynek danych

Faza D zamienia Ghost Exchange z ręcznego panelu sprzedaży pojedynczych plików w
automatyczny rynek danych oparty o istniejący File Model, Storage Model,
Googleplex i profil gracza.

Nie powstaje drugi rynek, drugi system plików, drugi storage ani drugi economy
engine. Wszystkie zmiany rozwijają istniejące:

* `profile.files`,
* `sellable`,
* `market_status`,
* `files.market`,
* `profile.market_history`,
* `storage_capacity`,
* `storage_used`,
* `file_size`,
* `price_preview`,
* Ghost Exchange,
* File Manager,
* Googleplex.

Nowa pętla gameplayu:

```text
Mapa
↓
Operacja
↓
Plik
↓
Storage
↓
Market Queue
↓
Ghost Exchange
↓
Auto Sale
↓
HackCoins
↓
Googleplex
↓
Lepsze narzędzia
↓
Więcej operacji
```

Decision:

* Przyjęto: Ghost Exchange jest rynkiem wyników operacji, nie sklepem z ręcznym
  klikaniem `Sprzedaj`.
* Przyjęto: File Manager pozostaje miejscem przeglądania lootów.
* Przyjęto: Googleplex pozostaje miejscem wydawania HC.
* Przyjęto: Storage Economy działa od początku Fazy D jako realne ograniczenie
  zapisu danych.
* Przyjęto: Storage Upgrade jest produktem Googleplexa, nie osobnym sklepem i
  nie aplikacją uruchamialną.
* Przyjęto: ręczna sprzedaż może zostać wyłącznie jako legacy/dev/debug.

---

# Sprint 35 — Ghost Exchange Market Model + Storage Gate Foundation

## Cel gameplayowy

Ustalić i wdrożyć fundament modelu rynku danych: plik jest lootem w
`profile.files`, zajmuje miejsce na dysku, ma sektor rynku i może trafić do
automatycznej kolejki Ghost Exchange.

Gracz nie sprzedaje jeszcze paczek automatycznie, ale gra zaczyna mówić jednym
językiem: plik, storage, eligibility, sektor, status rynku.

## Architektura

Sprint 35 rozszerza istniejące normalizacje, nie finalizery jako osobne systemy.

Nowe helpery powinny mieszkać obok obecnych funkcji Ghost Exchange i File Modelu
w `run.py`:

* `market_sector_for_file(file_entry)`,
* `normalize_file_market_status(file_entry)`,
* `is_market_eligible_file(file_entry)`,
* `can_store_runtime_file(profile, file_entry)`,
* `build_storage_full_result(profile, operation, file_entry)`.

`sellable` pozostaje znaczeniem eligibility do Ghost Exchange. `market_status`
pozostaje lifecycle pliku względem rynku.

## Systemy

* `profile.files`,
* `normalize_runtime_file_entry()`,
* `is_ghost_exchange_sellable()`,
* `ghost_exchange_price_preview()`,
* `calculate_profile_storage_used()`,
* `normalize_profile_storage()`,
* File Manager,
* Ghost Exchange.

## Flow danych

```text
finalizer builds file object
↓
normalize_runtime_file_entry()
↓
file_size / sellable / price_preview
↓
market_sector
↓
storage check
↓
profile.files[category]
```

## Backend

1. Dodać centralne mapowanie `file_category -> market_sector`.
2. Dodać normalizację nowych statusów:
   * `created`,
   * `queued_for_market`,
   * `listed`,
   * `sold`,
   * `archived`.
3. Zmapować stare statusy:
   * `not_listed` -> `queued_for_market`, jeśli `sellable == true`,
   * `ready_to_list` -> `queued_for_market`,
   * `listed_preview` -> `queued_for_market`, jeśli nie istnieje batch,
   * `sold` -> `sold`,
   * `archived` -> `archived`.
4. Dodać read-only pola do payloadu Ghost Exchange:
   * `market_sector`,
   * `market_volume_mb`,
   * `market_status`,
   * `price_preview`.
5. Nie usuwać jeszcze starego endpointu `sell`.

## Frontend

1. Ghost Exchange może nadal renderować stary widok, ale ma dostać dane
   sektorowe w payloadzie.
2. File Manager pokazuje istniejące pola:
   * `market_status`,
   * `sellable`,
   * `file_size`.
3. Nie dodawać jeszcze dashboardu.
4. Nie dodawać nowego panelu rynku.

## Storage

1. Storage zaczyna być traktowany jako realny warunek zapisu danych.
2. Sprint 35 przygotowuje helpery, ale finalizery można przełączać etapami.
3. Jeśli helper wykryje brak miejsca, powinien zwracać wynik typu:
   * `storage_full`,
   * `dropped_no_space`.
4. Brak miejsca nie cofa operacji, ale blokuje zapis danych.

## Ghost Exchange

Ghost Exchange nadal czyta istniejące pliki z `profile.files`. W Sprincie 35
nie powstaje osobna kolejka poza plikami. Sektor rynku jest właściwością pliku,
nie nowym magazynem.

## Googleplex

Bez zmian w UI. Sprint 35 tylko potwierdza, że przyszłe Storage Upgrade mają być
produktami w istniejącym katalogu Googleplexa.

## Migracje

Brak wymaganej migracji produkcyjnej na tym etapie, jeśli normalizacja przy
odczycie wystarczy.

Przygotować opis migracji na Sprint 39:

* normalizacja starych `market_status`,
* uzupełnienie `market_sector`,
* uzupełnienie brakujących `file_size`.

## Testy

* `market_sector_for_file()` mapuje wszystkie aktualne `file_category`.
* Stare statusy mapują się do nowego modelu.
* `sellable` nadal odpowiada eligibility Ghost Exchange.
* `price_preview` nadal działa po normalizacji.
* Brak miejsca zwraca kontrolowany wynik helpera, bez zapisu pliku.

## Smoke

Smoke tylko obserwacyjny:

* wygenerować plik GPS/camera/ATM,
* sprawdzić `file_size`,
* sprawdzić `sellable`,
* sprawdzić `market_sector`,
* sprawdzić `market_status`.

## Ryzyka

* Zrobienie osobnej kolejki rynku zamiast użycia `profile.files`.
* Zrobienie osobnego storage checka w każdym finalizerze.
* Zmiana znaczenia `sellable`.
* Ukrycie starych statusów bez migracji/normalizacji.

## Dokumentacja

Uzupełnić:

* `doc/file_model.md`,
* `doc/data_economy.md`,
* `doc/gameplay_matrix.md`,
* `doc/project_journal.md`.

## Kryteria akceptacji

* Istnieje jednoznaczny model `file -> storage -> market_sector`.
* Stare statusy są opisane i normalizowane.
* Każdy sellable file ma możliwy sektor rynku.
* Storage gate ma wspólny helper.
* Nie powstał drugi rynek ani drugi storage.

---

# Sprint 36 — Market Queue + File Lifecycle

## Cel gameplayowy

Sprzedawalne pliki po utworzeniu automatycznie trafiają do kolejki rynku.
Gracz widzi, że dane czekają na skup sektorowy, ale nie klika pojedynczych
przycisków sprzedaży.

## Architektura

Kolejka rynku jest stanem plików w `profile.files`, nie osobnym systemem.

Helper:

```text
queue_market_eligible_files(profile)
```

ma być idempotentny i działać na istniejących plikach.

## Systemy

* `profile.files`,
* `market_status`,
* `sellable`,
* `market_sector`,
* `collect_ghost_exchange_files()`,
* `GET /api/ghost-exchange`,
* File Manager.

## Flow danych

```text
profile.files[category]
↓
sellable == true
↓
market_status: queued_for_market
↓
queued_at
↓
market_sector bucket
```

## Backend

1. Dodać `queue_market_eligible_files(profile)`.
2. Wywołać helper w:
   * `GET /api/ghost-exchange`,
   * profilu po `refresh_and_persist_operations()`,
   * normalizacji plików, jeśli profil jest zapisywany.
3. Ustawić:
   * `market_status: queued_for_market`,
   * `queued_at`,
   * `market_sector`.
4. Nie wypłacać jeszcze HC automatycznie.
5. Nie usuwać jeszcze plików z `/data`.
6. Ręczny `sell` zostaje legacy/dev/debug.

## Frontend

1. Ghost Exchange pokazuje sektorowe oczekujące dane.
2. Zamiast zachęty do sprzedaży pojedynczego pliku, UI pokazuje:
   * `uzbierano X MB`,
   * `brakuje Y MB`,
   * `brakuje N rekordów`, jeśli sektor tego wymaga.
3. File Manager nadal pokazuje loot w katalogach.

## Storage

1. Pliki w kolejce nadal zajmują miejsce.
2. `storage_used` nie maleje po kolejkowaniu.
3. Pełny dysk blokuje powstanie nowych danych, nie samo kolejkowanie danych już
   zapisanych.

## Ghost Exchange

Ghost Exchange pokazuje read model kolejki:

```text
sector
pending_files
pending_mb
threshold_mb
missing_mb
missing_records
progress_percent
estimated_sale_time
```

## Googleplex

Bez zmian funkcjonalnych. Googleplex korzysta z HC dopiero po auto-sale w
Sprincie 37.

## Migracje

Migracja nie jest obowiązkowa, jeśli queue może być ustawiane przez normalizację.

Przygotować dry-run:

* ile plików stanie się `queued_for_market`,
* ile ma brakujące `market_sector`,
* ile ma brakujące `file_size`.

## Testy

* Plik GPS trafia do `queued_for_market`.
* Plik camera trafia do `queued_for_market`.
* Plik ATM trafia do `queued_for_market`.
* Plik credentials/financial trafia do `queued_for_market`.
* `system/internal_recon_state` nie trafia do kolejki.
* Drugi refresh nie zmienia `queued_at` i nie dubluje wpisów.

## Smoke

Gameplay smoke:

* operacja,
* plik,
* File Manager widzi loot,
* Ghost Exchange widzi sektor pending,
* HC jeszcze się nie zmienia.

## Ryzyka

* Kolejka jako nowa lista obok `profile.files`.
* Modyfikowanie `files.market` przed sprzedażą.
* Usuwanie pliku z File Managera już po dodaniu do queue.

## Dokumentacja

Uzupełnić:

* `doc/file_model.md`,
* `doc/data_economy.md`,
* `doc/project_journal.md`.

## Kryteria akceptacji

* Sellable files automatycznie trafiają do kolejki.
* Kolejkowanie jest idempotentne.
* File Manager nadal pokazuje loot.
* Ghost Exchange pokazuje oczekujące sektory.
* Storage nadal liczy pliki w kolejce.

---

# Sprint 37 — Auto Sale Settlement Engine

## Cel gameplayowy

Rynek danych sam rozlicza paczki sektorowe po osiągnięciu progów. Gracz zarabia
HC dzięki operacjom i magazynowaniu danych, a nie dzięki klikaniu `Sprzedaj`.

## Architektura

Settlement jest kontrolowanym refreshem, nie realtime loopem.

Helper:

```text
refresh_market_runtime(username, profile, now=None, persist=False)
```

może być wywoływany przez istniejące ścieżki:

* `GET /api/ghost-exchange`,
* `/api/profile`,
* ewentualnie po `refresh_and_persist_operations()`.

Rozliczenie musi być idempotentne.

## Systemy

* `profile.files`,
* `files.market`,
* `profile.market_history`,
* `profile.hackcoins`,
* mail/system messages,
* `price_preview`,
* `storage_used`.

## Flow danych

```text
queued_for_market files
↓
group by market_sector
↓
sector threshold reached
↓
listed_at / minimum market dwell time
↓
stable batch_id
↓
batch valuation
↓
HC transfer
↓
market_history
↓
files.market sale record
↓
remove files from /data
↓
storage_used recalculated
```

## Backend

1. Dodać batch builder sektorowy.
2. Dodać stabilny `batch_id`, np. z:
   * username,
   * sector,
   * sorted file ids.
3. Dodać progi sektorów:
   * `camera`: MB,
   * `atm`: MB + liczba rekordów,
   * `gps`: wolumen tras / MB,
   * `device`: MB + liczba plików,
   * `personal`: liczba rekordów / MB,
   * `credentials`: liczba credentiali,
   * `financial`: rekordy + MB,
   * `network`, `audio`, `vehicle`: MB + liczba plików.
4. Po osiągnięciu progu paczka przechodzi w stan `listed` i dostaje `listed_at`.
5. Auto sale następuje dopiero po osiągnięciu progu oraz po minimalnym czasie
   przebywania paczki na rynku.
6. Minimalny czas może być różny per sektor, np.:
   * `camera`: 5 minut,
   * `credentials`: 3 minuty,
   * `financial`: 6 minut,
   * pozostałe sektory: 4-5 minut jako MVP.
7. Cena paczki bazuje na istniejącym:
   * `price_preview`,
   * `quality_score`,
   * `completeness_percent`,
   * `file_size`,
   * liczbie plików/rekordów.
8. Przed wypłatą HC sprawdzić, czy `batch_id` nie istnieje w:
   * `profile.market_history`,
   * `files.market`.
9. Po sprzedaży:
   * usunąć pliki z ich katalogów `/data/*`,
   * dodać rekord do `files.market`,
   * dodać wpis do `profile.market_history`,
   * dodać HC,
   * dodać mail/system message,
   * przeliczyć storage.

## Frontend

1. Ghost Exchange pokazuje, że sektor został rozliczony.
2. Wallet i system toolbar odświeżają HC.
3. Nie pokazywać ręcznego `Sprzedaj` jako głównego CTA.

## Storage

1. Pliki w kolejce zajmują miejsce.
2. Sprzedaż paczki zwalnia miejsce.
3. Jeśli brakuje danych do progu, storage nadal jest zajęty i gracz widzi, ile
   brakuje do rozliczenia.

## Ghost Exchange

Pokazuje:

* progress do paczki,
* `brakuje X MB`,
* `brakuje N rekordów`,
* `estimated_sale_time`,
* stan `listed` / `trading`,
* ostatnią transakcję sektora,
* HC z rozliczenia.

## Googleplex

Po auto-sale HC może zostać wydane w obecnym Googleplexie. Nie zmieniać flow
zakupu aplikacji w tym sprincie.

## Migracje

Brak migracji strukturalnej, jeśli `batch_id` i batch records są przechowywane w
`profile.market_history` oraz `files.market`.

Jeśli potrzebne jest `market_state`, musi być częścią profilu i nie może stać się
drugim magazynem plików.

## Testy

* Batch sprzedaje się po osiągnięciu progu.
* Batch nie sprzedaje się przed progiem.
* Batch nie sprzedaje się przed minimalnym czasem przebywania na rynku.
* `listed_at` jest stabilne i nie resetuje się przy zwykłym refreshu.
* Drugi refresh nie dodaje HC drugi raz.
* `market_history` ma jeden wpis dla `batch_id`.
* `files.market` ma jeden rekord sprzedaży.
* Pliki znikają z `/data`.
* `storage_used` maleje po sprzedaży.
* Mail/system message powstaje raz.

## Smoke

Pełny smoke:

* wygenerować kilka plików sektora,
* osiągnąć próg,
* wejść w Ghost Exchange,
* zobaczyć stan `listed` / `trading`,
* zobaczyć szacowany czas sprzedaży,
* auto-sale rozlicza batch,
* HC rosną,
* File Manager nie pokazuje sprzedanych plików w `/data`,
* historia rynku pokazuje batch.

## Ryzyka

* Settlement wywołany z wielu endpointów bez idempotencji.
* Liczenie ceny paczki inną ekonomią niż `price_preview`.
* Zostawienie sprzedanych plików w `/data`, co zablokuje storage.
* Usunięcie plików bez wpisu historii.

## Dokumentacja

Uzupełnić:

* `doc/data_economy.md`,
* `doc/file_model.md`,
* `doc/gameplay_matrix.md`,
* `doc/project_journal.md`.

## Kryteria akceptacji

* Auto-sale działa bez ręcznego kliknięcia.
* Settlement jest idempotentny.
* HC, mail/system message i market history są spójne.
* Storage zwalnia się po sprzedaży.
* Nie powstał realtime loop.

---

# Sprint 38 — Ghost Exchange Dashboard v1

## Cel gameplayowy

Ghost Exchange staje się dashboardem rynku danych: gracz widzi sektory,
postęp do paczek, wolumen, brakujące dane, historię sprzedaży i HC.

## Architektura

Dashboard jest read modelem istniejących danych:

* `profile.files`,
* `market_status`,
* `market_sector`,
* `files.market`,
* `profile.market_history`.

Nie przechowuje własnej prawdy o rynku.

## Systemy

* `GET /api/ghost-exchange`,
* Browser / Ghost Exchange tab,
* File Manager,
* market history,
* toolbar HC.

## Flow danych

```text
profile.files + market_history
↓
build_ghost_exchange_dashboard_payload()
↓
sector cards
↓
recent transactions
↓
history chart
```

## Backend

1. Rozszerzyć `GET /api/ghost-exchange` o dashboard payload:
   * `summary`,
   * `sectors`,
   * `recent_transactions`,
   * `history_7d`.
2. Zostawić stare `files` tylko jako compatibility/dev, jeśli potrzebne.
3. Dashboard powinien korzystać z tych samych helperów co settlement.

## Frontend

1. Zastąpić główną listę ofert sektorowym dashboardem.
2. Ukryć przyciski `Sprzedaj` z normalnego flow.
3. Każdy sektor pokazuje:
   * oczekujące dane,
   * w obrocie,
   * sprzedane dzisiaj,
   * HC dzisiaj,
   * HC łącznie,
   * średnią cenę paczki,
   * progress do następnej paczki,
   * brakujące MB/pliki/rekordy,
   * ostatnie transakcje.
4. Wykresy lekkie: CSS/SVG/canvas inline, bez ciężkiej biblioteki.
5. Mobile: jedna kolumna.

## Storage

Dashboard pokazuje presję storage pośrednio:

* ile danych czeka,
* ile brakuje do sprzedaży,
* kiedy potencjalnie zwolni się miejsce.

Nie dodawać osobnego storage panelu w Ghost Exchange.

## Ghost Exchange

To główny sprint UX rynku. Ghost Exchange ma wyglądać jak giełda/skup danych,
nie jak sklep z plikami.

## Googleplex

Bez zmian mechanicznych. Dashboard może sugerować, że większy storage pomaga
zbierać większe paczki, ale zakup nadal dzieje się w Googleplexie.

## Migracje

Brak migracji danych. To read model i UI.

## Testy

* `GET /api/ghost-exchange` zwraca `summary`.
* `GET /api/ghost-exchange` zwraca sektory.
* Sektor pokazuje `missing_mb` albo `missing_records`.
* Sektor pokazuje `estimated_sale_time`.
* Recent transactions pochodzą z `profile.market_history`.
* Główny UI nie renderuje ręcznego `Sprzedaj`.
* Mobile nie ma poziomego scrolla.

## Smoke

Smoke:

* dane poniżej progu pokazują progress i brakujące MB,
* dane po progu pokazują stan `listed` / `trading` i szacowany czas sprzedaży,
* dane po progu rozliczają batch,
* dashboard pokazuje transakcję,
* HC na toolbarze jest aktualne.

## Ryzyka

* Dashboard oparty o mocki zamiast profilu.
* Duplikacja logiki progów w JS i Pythonie.
* Za ciężki wykres spowalniający Browser.
* Zostawienie starej listy plików jako głównego widoku.

## Dokumentacja

Uzupełnić:

* `doc/data_economy.md`,
* `doc/gameplay_terms.md`,
* `doc/project_journal.md`.

## Kryteria akceptacji

* Ghost Exchange pokazuje dashboard sektorowy.
* Gracz widzi, ile już uzbierał i ile jeszcze brakuje.
* Nie ma setek przycisków `Sprzedaj`.
* File Manager nadal pokazuje loot.
* Dashboard nie jest nowym źródłem prawdy.

---

# Sprint 39 — Storage Economy + Market Migration + Balance

## Cel gameplayowy

Domknąć Fazę D: storage staje się realnym ograniczeniem, Ghost Exchange sprzedaje
paczki w regularnym tempie, a Googleplex pozwala inwestować HC w większy dysk.

Mały dysk ogranicza tempo zarabiania. Większy dysk pozwala zbierać większe paczki
danych i sprawniej domykać rynek.

## Architektura

Sprint 39 scala:

* twardy storage gate w finalizerach,
* migrację starych statusów rynku,
* Storage Upgrade jako produkt Googleplexa,
* balance progów sektorowych,
* smoke pełnej pętli.

Nie tworzy osobnego sklepu storage.

## Systemy

* finalizery operacji,
* `profile.files`,
* `storage_capacity`,
* `storage_used`,
* Ghost Exchange settlement,
* Googleplex `/install-app`,
* `json_resources.app_config`,
* smoke tools.

## Flow danych

```text
operation finalizer
↓
storage gate
↓
file saved or dropped_no_space
↓
market queue
↓
sector batch
↓
auto sale
↓
storage freed
↓
HC
↓
Googleplex storage product
↓
storage_capacity increased
```

## Backend

1. Finalizery zapisują pliki przez wspólny helper:
   * `append_runtime_file_if_space(profile, operation, folder, file_entry)`.
2. Przy braku miejsca:
   * nie zapisywać pliku,
   * oznaczyć wynik jako `storage_full` / `dropped_no_space`,
   * dodać system message,
   * nie dodawać danych do rynku.
3. Dodać obsługę produktu Googleplex:
   * `product_type: storage_upgrade`,
   * `storage_capacity_bonus`.
4. `/install-app` dla storage product:
   * odejmuje HC,
   * zwiększa `storage_capacity`,
   * nie dodaje produktu do `profile.apps`,
   * nie dodaje produktu do `files.tools`,
   * zapisuje historię/system message.
5. Zostawić zwykłe aplikacje bez zmian.

## Frontend

1. Googleplex pokazuje storage products jako produkty, nie aplikacje.
2. Przycisk zakupu storage mówi o zwiększeniu pojemności.
3. File Manager pokazuje nowe `storage_capacity`.
4. Ghost Exchange pokazuje wpływ rynku na zwalnianie storage.

## Storage

1. Storage jest twardym ograniczeniem zapisu nowych danych.
2. Storage full nie przerywa operacji, ale blokuje powstanie pliku.
3. Dane niezapisane nie są sprzedawane.
4. Auto-sale zwalnia miejsce.
5. Storage upgrade zwiększa limit.

## Ghost Exchange

1. Progi sektorów zostają zbalansowane po pierwszym smoke:
   * Camera: głównie MB,
   * Financial: rekordy + MB,
   * Credentials: liczba credentiali,
   * GPS: wolumen tras / MB,
   * Device/Personal: pliki + MB,
   * ATM: rekordy + MB.
2. Ghost Exchange pokazuje brakujące MB/rekordy jako informację gameplayową.

## Googleplex

Storage Upgrade jest produktem Googleplexa:

```text
Googleplex product
↓
purchase with HC
↓
storage_capacity bonus
↓
File Manager storage updated
```

Produkt nie jest aplikacją, nie ma runtime window i nie trafia do `/tools`.

## Migracje

Przygotować i uruchamiać przez Sprint 31 migration runner:

1. Backup DB.
2. Dry-run statusów:
   * `not_listed`,
   * `ready_to_list`,
   * `listed_preview`,
   * `sold`.
3. Uzupełnienie:
   * `market_sector`,
   * `queued_at`,
   * `file_size`,
   * `storage_capacity`,
   * `storage_used`.
4. Dodanie seed produktów storage do `json_resources.app_config`.
5. Walidacja:
   * brak utraty `profile.market_history`,
   * brak usunięcia plików bez statusu `sold`,
   * brak wpisów storage product w `/tools`.

## Testy

* Pełny dysk blokuje zapis pliku.
* Operacja przy pełnym dysku kończy się bez crasha.
* `dropped_no_space` nie trafia do Ghost Exchange.
* Auto-sale zwalnia storage.
* Storage product zwiększa `storage_capacity`.
* Storage product nie trafia do `profile.apps`.
* Storage product nie trafia do `files.tools`.
* Stare profile zachowują historię rynku.
* Manual sale endpoint, jeśli zostaje, działa tylko jako legacy/dev i nie dubluje
  auto-sale.

## Smoke

Finalny smoke Fazy D:

* login admin,
* wygenerowanie danych z operacji,
* File Manager pokazuje loot i zajęty storage,
* Ghost Exchange pokazuje sektor i progress,
* auto-sale rozlicza batch,
* HC rosną,
* market history ma batch,
* mail/system message istnieje,
* storage maleje po sprzedaży,
* zakup storage product w Googleplex zwiększa pojemność,
* nowe operacje mogą zapisać więcej danych.

## Ryzyka

* Storage product jako aplikacja w `/tools`.
* Twardy storage gate bez feedbacku dla gracza.
* Migracja usuwająca stare pliki zamiast tylko normalizować statusy.
* Balance progów zbyt wysoki, przez co mały dysk blokuje early game.
* Balance progów zbyt niski, przez co rynek sprzedaje wszystko natychmiast.

## Dokumentacja

Uzupełnić:

* `doc/file_model.md`,
* `doc/data_economy.md`,
* `doc/app_contract.md`,
* `doc/gameplay_matrix.md`,
* `doc/resource_types.md`,
* `doc/project_journal.md`,
* dokument migracyjny Sprintu 31, jeśli wymaga nowych kroków.

## Kryteria akceptacji

* Storage jest realnym ograniczeniem zapisu danych.
* Dane niezapisane nie trafiają do rynku.
* Ghost Exchange sprzedaje paczki automatycznie.
* Storage zwalnia się po sprzedaży paczki.
* Googleplex ma storage products bez tworzenia osobnego sklepu.
* Stare profile są kompatybilne.
* Pełny gameplay smoke Fazy D przechodzi.

---

# Finalna architektura Fazy D

Pełny docelowy przepływ:

```text
operacja
↓
finalizer
↓
storage gate
↓
profile.files
↓
storage_used / storage_capacity
↓
market queue przez market_status
↓
sector batch
↓
Ghost Exchange dashboard
↓
auto settlement
↓
files.market + profile.market_history
↓
HackCoins
↓
Googleplex
↓
storage products / lepsze narzędzia
↓
kolejne operacje
```

Zasady integracji:

* `profile.files` pozostaje jedynym źródłem plików danych gracza.
* `sellable` oznacza eligibility do Ghost Exchange.
* `market_status` opisuje lifecycle pliku względem rynku.
* `files.market` przechowuje rekordy sprzedaży/staging historii, nie nowe looty.
* `profile.market_history` jest historią transakcji.
* `storage_capacity`, `storage_used` i `file_size` są jedynym modelem storage.
* `price_preview`, completeness i quality są bazą wyceny.
* Ghost Exchange jest jedynym rynkiem danych Fazy D.
* Googleplex jest jedynym miejscem wydawania HC.
* Storage Upgrade jest produktem Googleplexa.
* Frontend Ghost Exchange jest dashboardem read modelu, nie źródłem prawdy.
* Auto-sale jest kontrolowanym refreshem, nie realtime loopem.

---

# Faza E — Cyberner / Messenger

Faza E zmienia istniejącą Skrzynkę mailową w Cybernera: komunikator świata gry.

Cyberner jest nową nazwą użytkową i diegetyczną aplikacji znanej wcześniej jako
Email / Skrzynka mailowa. Techniczne identyfikatory legacy mogą pozostać bez
zmian, jeśli ich zmiana byłaby ryzykowna dla runtime.

Filozofia nazwy jest opisana w:

* `doc/cyberner.md`.

Nie powstaje drugi system wiadomości, drugi contact flow ani osobny backend
messengera. Wszystkie zmiany rozwijają istniejące:

* `mail_store`,
* `/api/mail/bootstrap`,
* `/api/chats/messages`,
* `/api/contacts`,
* `system_messages`,
* kontakty i pending threads,
* desktopową aplikację Cyberner.

Nowy kierunek UX:

```text
lista rozmów
↓
wybrany czat
↓
odpowiedź
↓
powrót do listy
```

Decision:

* Przyjęto: Cyberner na mobile/narrow działa jak klasyczny komunikator.
* Przyjęto: widoczna nazwa aplikacji i komunikatora przechodzi z Email /
  Skrzynka mailowa na Cyberner.
* Przyjęto: desktop zachowuje układ dwukolumnowy.
* Przyjęto: mobile pokazuje tylko jeden ekran naraz: lista albo czat.
* Przyjęto: backend wiadomości i model danych pozostają bez zmian w pierwszych
  sprintach Fazy E.
* Przyjęto: style messengera mieszkają w `static/css/mobile_messenger.css`, a
  `style.css` może co najwyżej importować albo linkować ten plik.

---

# Sprint 40 — Cyberner Architecture Audit + UX Contract

## Cel gameplayowy

Ustalić, czym Cyberner jest w CHAOS-ie: komunikatorem gracza,
powiadomieniami systemowymi i kanałem kontaktów, ale bez tworzenia nowego
systemu wiadomości.

## Architektura

Sprint 40 jest audytem i kontraktem UX. Nie przebudowuje backendu.

Sprawdzić:

* `createEmailClient()`,
* `createEmailClientLegacy()`,
* widoczna nazwa Email / Skrzynka mailowa -> Cyberner,
* `/api/mail/bootstrap`,
* `/api/chats/messages`,
* `/api/contacts`,
* `system_messages`,
* pending conversations,
* unread counts,
* integracje z mapą i player actors przez `openEmailChatWith()`.

## UX

Zdefiniować docelowe pojęcia:

* rozmowa grupowa,
* rozmowa indywidualna,
* rozmowa oczekująca,
* kontakt,
* status online/offline,
* unread badge,
* system thread,
* Ghost Exchange / system notifications jako nadawcy świata gry.
* Cyberner jako diegetyczny nerw komunikacyjny Ghost Systemu.

## Systemy

* Mailbox frontend,
* kontakty,
* system messages,
* player actors,
* Ghost Exchange notifications,
* desktop app runtime.

## Backend

Bez zmian. Audyt ma potwierdzić, które endpointy wystarczają dla Fazy E.

## Frontend

Ustalić minimalny kontrakt DOM:

* `.mail-app`,
* `.mail-sidebar`,
* `.mail-chat`,
* `.mail-conversation-list`,
* `.mail-conversation-item`,
* `.mail-chat-header`,
* `.mail-back-button`,
* `.mail-messages`,
* `.mail-message`,
* `.mail-composer`.

## Testy

* Desktop nadal otwiera Cybernera.
* `openEmailChatWith(peer)` nadal otwiera wybraną rozmowę.
* Bootstrap zwraca kontakty, pending threads i unread counts.

## Dokumentacja

Uzupełnić:

* `doc/game_play_260626.md`,
* `doc/project_journal.md`.

## Kryteria akceptacji

* Istnieje spis obecnych przepływów mail/contact.
* Wiadomo, które dane są potrzebne do layoutu messengera.
* Wiadomo, czego nie zmieniamy w backendzie.
* Istnieje plan Sprintów 41-44.

---

# Sprint 41 — Cyberner Layout v1

## Cel gameplayowy

Cyberner na mobile/narrow zaczyna działać jak komunikator:
gracz widzi listę rozmów, wybiera czat i może wrócić do listy.

## Architektura

Nie zmieniać backendu wiadomości ani modelu danych.

Frontend utrzymuje tylko stan widoku:

```text
mailMobileView = "list" | "chat"
```

Na `.mail-app` ustawiać:

```text
data-mobile-view="list"
data-mobile-view="chat"
```

## Desktop

Desktop zostaje dwukolumnowy:

* kontakty/rozmowy po lewej,
* wybrany czat po prawej.

## Mobile / Narrow

* startowo lista rozmów,
* kliknięcie rozmowy przełącza na czat,
* czat pokazuje przycisk powrotu,
* input wiadomości jest na dole,
* brak poziomego scrolla.

## Frontend

1. Przebudować markup `createEmailClient()` pod klasy `mail-*`.
2. Dodać `mailMobileView`.
3. Dodać `mail-back-button`.
4. Dodać detekcję narrow po rozmiarze okna aplikacji i viewportu.
5. Po resize desktop pokazuje oba panele, mobile zachowuje aktualny stan
   `list/chat`.

## CSS

Style trzymać w:

* `static/css/mobile_messenger.css`.

Nie wrzucać layoutu messengera do `style.css` poza linkiem/importem.

## Testy

* `node --check static/js/terminal.js`.
* `git diff --check`.
* Manual desktop: dwa panele.
* Manual mobile/narrow: jeden ekran naraz.
* Manual: klik rozmowy otwiera czat.
* Manual: back wraca do listy.
* Manual: input jest dostępny.

## Kryteria akceptacji

* Desktop nie traci starego flow.
* Mobile nie pokazuje listy i czatu naraz.
* Back działa bez reloadu aplikacji.
* Nie zmieniono backendu.

---

# Sprint 42 — Conversation List Polish + Thread States

## Cel gameplayowy

Lista rozmów zaczyna wyglądać jak centrum komunikacji świata gry, a nie lista
technicznych przycisków.

## UX

Każda rozmowa pokazuje:

* avatar albo symbol nadawcy,
* nazwę,
* status online/offline/system,
* unread badge,
* wyróżnienie aktywnej rozmowy,
* stan pending/request,
* krótki opis albo ostatni sygnał, jeśli backend już go dostarcza.

## Architektura

Nie dodawać nowego endpointu, jeśli obecny bootstrap wystarcza.

Jeśli brakuje danych preview, użyć defensywnych fallbacków w UI zamiast
rozszerzać model danych na siłę.

## Frontend

1. Uporządkować rendering `contacts`, `pending_threads` i `group`.
2. Dodać spójne klasy dla aktywnej rozmowy, unread i pending.
3. Rozdzielić sekcje:
   * kontakty,
   * oczekujące,
   * system/group.
4. Zachować `openEmailChatWith(peer)`.

## CSS

1. Dopasować aktywny item do klimatu CHAOS.
2. Unikać poziomego scrolla.
3. Przy długich nickach używać ellipsis.
4. Badge unread nie może rozpychać listy.

## Testy

* Kontakt online/offline renderuje status.
* Pending thread jest widoczny w sekcji oczekujących.
* Unread badge nie znika po samym refreshu listy.
* Aktywna rozmowa pozostaje aktywna po `refreshThreads()`.

## Kryteria akceptacji

* Lista rozmów jest czytelna na desktop i mobile.
* Pending conversations nie mieszają się z kontaktami.
* Nie powstał drugi contact system.

---

# Sprint 43 — Chat View Polish + Composer UX

## Cel gameplayowy

Widok czatu staje się czytelny i szybki w użyciu: wiadomości mają rytm
komunikatora, a composer zawsze jest dostępny.

## UX

Czat pokazuje:

* nagłówek z nazwą rozmowy,
* status rozmowy,
* akcje po prawej jako małe kontrolki,
* wiadomości z nadawcą i czasem,
* wiadomości własne po prawej,
* wiadomości systemowe jako osobny ton,
* composer przy dolnej krawędzi.

## Frontend

1. Uporządkować markup pojedynczej wiadomości.
2. Dodać klasy:
   * own,
   * system,
   * pending/unknown sender, jeśli istnieje.
3. Po wysłaniu wiadomości zachować aktualny czat.
4. Po refreshu nie przewijać agresywnie, jeśli użytkownik czyta starsze
   wiadomości, chyba że jest na dole.

## CSS

* Długie wiadomości zawijają się bez poziomego scrolla.
* Composer nie nachodzi na wiadomości.
* Mobile zachowuje wysokość inputa i przycisku wysyłania.

## Backend

Bez zmian, chyba że istniejący endpoint nie zwraca wymaganej informacji o
nadawcy/czasie. Wtedy przerwać i zgłosić decyzję.

## Testy

* Wysłanie wiadomości odświeża czat.
* Długa wiadomość nie rozpycha okna.
* Własna wiadomość ma osobny styl.
* System message ma osobny styl, jeśli występuje w tym flow.

## Kryteria akceptacji

* Czat jest używalny na desktop i mobile.
* Composer jest zawsze dostępny.
* Nie zmieniono modelu wiadomości.

---

# Sprint 44 — Cyberner Integration + World Communication

## Cel gameplayowy

Cyberner staje się jednym miejscem komunikacji ze światem gry: kontakty,
system, Ghost Exchange, AI, mapa, player actors i przyszłe źródła świata
korzystają z jednego mail/contact flow.

Cyberner nie jest już tylko aplikacją pocztową. Jest warstwą komunikacji świata.

## Architektura

Nie tworzyć drugiego systemu notyfikacji.

Integracje mają używać istniejących:

* `mail_store`,
* `system_messages`,
* `openEmailChatWith()`,
* `/api/mail/bootstrap`,
* `/api/chats/messages`.

Nie myśleć o folderach. Myśleć o źródłach komunikacji.

Podstawowe źródła:

* `# grupa` — globalny czat online graczy,
* gracze / znajomi / nieznajomi,
* AI Central,
* Ghost Exchange,
* System,
* Misje,
* przyszłe NPC,
* przyszłe frakcje,
* przyszły Marketplace,
* przyszłe usługi świata.

Frontend nadaje rozmowom tożsamość źródła, ale backend pozostaje ten sam.

## Zakres

1. Sprawdzić wejścia do messengera z mapy/player actors.
2. Sprawdzić wiadomości Ghost Exchange i systemowe.
3. Uporządkować unread counts.
4. Upewnić się, że odczyt rozmowy nie kasuje niepowiązanych alertów.
5. Upewnić się, że pending request nie tworzy duplikatu kontaktu.
6. Dodać `CYBERNER_ICON_LIBRARY` jako centralne źródło ikon komunikatora.
7. Renderer Cybernera ma korzystać z `CYBERNER_ICON_LIBRARY`, nie z
   `SYSTEM_ICON_LIBRARY` i nie z ikon wpisanych na sztywno.
8. Nieznany typ rozmowy używa ikony `unknown`.

## Frontend

* Ikony/akcje w headerze czatu mogą być tylko UI, jeśli backend nie ma jeszcze
  funkcji.
* Nie pokazywać niedziałających akcji jako aktywnych komend.
* Source identity jest warstwą prezentacji:
  * Ghost Exchange wygląda jak rozmowa Ghost Exchange,
  * System wygląda jak rozmowa System,
  * AI Central wygląda jak rozmowa AI,
  * player actors nadal otwierają rozmowy przez `openEmailChatWith(peer)`.

## Testy

* `openEmailChatWith(peer)` otwiera istniejące okno maila albo tworzy nowe.
* Player actor może otworzyć rozmowę bez duplikowania kontaktu.
* Pending conversation pozostaje pending do akcji użytkownika.
* System/Ghost Exchange messages nie mieszają się z prywatnym czatem.
* Ukryty czat na mobile nie oznacza rozmowy jako przeczytanej samym refreshem
  listy.
* Renderer korzysta z `CYBERNER_ICON_LIBRARY`.

## Kryteria akceptacji

* Messenger jest spójny z istniejącymi kontaktami.
* Nie ma drugiego inboxa.
* Nie ma drugiego systemu powiadomień.
* Mobile/narrow nadal działa jako lista -> czat -> lista.
* Cyberner jest traktowany jako jedyny komunikator świata gry.

---

# Sprint 45 — Cyberner Channels Audit + UX Contract

## Cel gameplayowy

Ustalić finalny model kanałów komunikacji w Cybernerze bez zmiany backendu i bez
implementacji runtime kanałów.

Sprint 45 jest audytem i kontraktem UX. Nie dodaje jeszcze `# global`,
`# znajomi` ani `# klan` jako nowych kanałów runtime.

## Filozofia

Cyberner nie pokazuje folderów poczty.

Cyberner pokazuje źródła komunikacji świata:

```text
CYBERNER_ICON_LIBRARY.world   WORLD
CYBERNER_ICON_LIBRARY.friends ZNAJOMI
CYBERNER_ICON_LIBRARY.clan    KLAN
AI Central
Ghost Exchange
System
Misje
Marketplace
BlackNet
NPC
gracze prywatni
```

Kanał jest wspólnym źródłem rozmowy. Prywatna rozmowa jest threadem z graczem
albo kontaktem. Thread systemowy jest rozmową prowadzoną przez system gry.

## Znaczenie gameplayowe

Sprinty 45–47 rozpoczynają społeczną gałąź projektu CHAOS.

Do tej pory przynależność do klanu była przygotowana głównie jako dane profilu.
Po zakończeniu Fazy E klan zaczyna mieć realne znaczenie gameplayowe.

Cyberner staje się pierwszym systemem korzystającym z przynależności klanowej.

To początek przyszłych mechanik:

* komunikacji klanowej,
* współpracy podczas operacji,
* wymiany informacji,
* koordynacji działań,
* przyszłych wojen klanów,
* przyszłych terytoriów klanowych,
* przyszłych wydarzeń i misji frakcyjnych.

Sprinty 45–47 nie implementują jeszcze tych mechanik.

Ich celem jest przygotowanie architektury komunikacji tak, aby kolejne systemy
mogły korzystać z istniejącego Cybernera zamiast budować własne kanały.

## Pytania do audytu

Sprawdzić, które źródła istnieją już w danych albo UI:

* `WORLD` — publiczny czat online całej gry,
* `ZNAJOMI` — kanał znajomych online,
* `KLAN` — kanał klanu,
* AI Central,
* Ghost Exchange,
* System,
* Misje,
* Marketplace,
* BlackNet,
* NPC,
* prywatne rozmowy z graczami.

## Audyt backendu

Sprawdzić istniejące:

* `mail_store`,
* `system_messages`,
* `contacts`,
* pending requests,
* `/api/mail/bootstrap`,
* `/api/chats/messages`,
* `openEmailChatWith()`.

Odpowiedzieć:

* czy obecna architektura pozwala zrobić kanały bez drugiego systemu wiadomości,
* czy wystarczy pole prezentacyjne `channel` / `source`,
* które kanały mogą być tylko frontendową tożsamością istniejącego threadu,
* gdzie grozi duplikacja contact flow,
* czego nie ruszać w backendzie.

## UX

Lista rozmów nie jest listą kontaktów. Jest listą kanałów i rozmów.

Docelowy porządek:

```text
ROZMOWY

CYBERNER_ICON_LIBRARY.world   WORLD
183 online

CYBERNER_ICON_LIBRARY.friends ZNAJOMI
7 online

CYBERNER_ICON_LIBRARY.clan    KLAN
2 online

Ghost Exchange
System
AI Central
Misje

Jan
Adam
Piotr
```

Nie używać nazwy `# grupa` jako docelowej nazwy kanału publicznego. Docelowo
kanał świata nazywa się `WORLD`, a jego ikonę dostarcza
`CYBERNER_ICON_LIBRARY.world`.

Kanały nie są kontaktami. Kanał jest trwałym źródłem komunikacji świata.
Kontakt jest prywatną rozmową z graczem. Thread systemowy jest rozmową
prowadzoną przez system gry. Nie wolno mieszać tych pojęć w UI ani w przyszłym
read modelu.

Nie wpisywać ikon kanałów na sztywno w rendererze. `WORLD`, `ZNAJOMI`, `KLAN`
i przyszłe kanały typu `WOJNA`, `FRAKCJA`, `OPERACJA`, `RAID` mają korzystać z
tego samego modelu `CYBERNER_ICON_LIBRARY + label`.

Ikona nie identyfikuje konkretnej rozmowy. Ikona identyfikuje typ źródła.
Renderer powinien wybierać ikonę po `source` / `channel`, np.
`source = clan -> CYBERNER_ICON_LIBRARY.clan`, a nie po nazwie rozmowy.

## Zakres

1. Zrobić mapę istniejących threadów do typów:
   * kanał,
   * prywatna rozmowa,
   * thread systemowy,
   * pending request.
2. Opisać minimalny read model dla kanału.
3. Opisać fallback dla danych, których backend jeszcze nie dostarcza.
4. Nie implementować runtime kanałów.
5. Nie dodawać endpointów.
6. Nie tworzyć drugiego inboxa.

## Kryteria akceptacji

* Wiadomo, co jest kanałem.
* Wiadomo, co jest prywatną rozmową.
* Wiadomo, co jest threadem systemowym.
* Wiadomo, czego backend już potrafi użyć.
* Wiadomo, czy Sprint 46 wymaga minimalnego pola `channel` / `source`.
* Nie zmieniono backendu, endpointów ani modelu wiadomości.

---

# Sprint 46 — Cyberner Channels Runtime

## Cel gameplayowy

Dodać podstawowe kanały Cybernera jako część istniejącego mail/contact flow:

```text
CYBERNER_ICON_LIBRARY.world   WORLD
CYBERNER_ICON_LIBRARY.friends ZNAJOMI
CYBERNER_ICON_LIBRARY.clan    KLAN
```

Kanały mają działać przez jeden `mail_store` i jeden Cyberner, bez osobnego
systemu czatów.

## Architektura

Nie tworzyć drugiego backendu wiadomości.

Jeżeli Sprint 45 pokaże, że backend potrzebuje minimalnego rozszerzenia, dodać
tylko jedno pole read/runtime, np.:

```text
channel
```

albo:

```text
source
```

Pole ma klasyfikować thread, nie tworzyć osobnego magazynu.

## Najważniejsze decyzje

Kanały Cybernera są pierwszym runtime wykorzystującym przynależność do klanu.

Od tego momentu klan przestaje być wyłącznie informacją w profilu.

Przynależność klanowa staje się elementem wpływającym na komunikację świata gry.

Kolejne systemy, takie jak wojny klanów, operacje grupowe, wspólne terytoria i
wydarzenia, powinny korzystać z istniejącego kanału `KLAN`, a nie tworzyć
własnych systemów komunikacji.

## Systemy

* `mail_store`,
* `system_messages`,
* `/api/mail/bootstrap`,
* `/api/chats/messages`,
* `openEmailChatWith()`,
* `CYBERNER_ICON_LIBRARY`,
* Cyberner conversation list.

## Flow danych

```text
channel event / player message
↓
mail_store albo system_messages
↓
bootstrap threads
↓
Cyberner conversation list
↓
chat view
```

## Backend

1. Użyć istniejących endpointów.
2. Dodać minimalną klasyfikację kanału tylko jeśli audyt Sprintu 45 tego wymaga.
3. Nie dodawać osobnego `channel_store`.
4. Nie dodawać drugiego pending/contact flow.
5. Nie duplikować wiadomości między kanałem a prywatną rozmową.
6. Kanały `WORLD`, `ZNAJOMI` i `KLAN` traktować jako singletony w profilu:
   jeden profil nie może mieć dwóch rozmów tego samego typu kanału.

## Frontend

1. Zmienić widoczną nazwę publicznego kanału z `# grupa` na `WORLD`.
2. Dodać sekcję kanałów nad prywatnymi rozmowami.
3. Pokazać `ZNAJOMI` i `KLAN` tylko wtedy, gdy istnieją dane albo bezpieczny
   fallback UX z audytu.
4. Wszystkie wejścia do rozmów nadal używają `openEmailChatWith()`.
5. Ikony kanałów pobierać z `CYBERNER_ICON_LIBRARY`.

## Testy

* `WORLD` otwiera istniejący globalny thread.
* Prywatna rozmowa nadal otwiera się przez `openEmailChatWith(peer)`.
* Pending request nie tworzy drugiego kontaktu.
* Kanał nie duplikuje wiadomości w prywatnym threadzie.
* Mobile/narrow nadal działa jako lista -> czat -> lista.

## Kryteria akceptacji

* Cyberner ma kanał `WORLD` zamiast docelowej nazwy `# grupa`.
* Kanały korzystają z istniejącego mail/contact flow.
* Kanał `KLAN` korzysta z przynależności klanowej, jeśli profil ją posiada.
* Kanały `WORLD`, `ZNAJOMI` i `KLAN` są projektowane jako singletony.
* Nie powstał drugi system wiadomości.
* Nie powstał drugi inbox.
* Backend został rozszerzony tylko minimalnie, jeśli było to konieczne.

## Decyzje implementacyjne

* `WORLD` jest aktywnym kanałem i mapuje się na istniejące `scope = group`,
  `peer = global`.
* `ZNAJOMI` jest singletonowym placeholderem opartym o istniejące kontakty.
  Nie zapisuje się jako kontakt i nie uruchamia jeszcze osobnego runtime
  wiadomości.
* `KLAN` jest singletonowym placeholderem widocznym tylko przy profilu z klanem.
  Nie implementuje jeszcze mechaniki klanowej.
* `/api/mail/bootstrap` zwraca minimalny read model `channels`.
* Nie dodano nowego endpointu, `channel_store`, inboxa ani contact flow.

---

# Sprint 47 — Cyberner Social Polish

## Cel gameplayowy

Dopolerować Cybernera jako społeczne centrum gry po tym, jak kanały mają już
ustalony model i podstawowy runtime.

Sprint 47 jest polish sprintem. Nie zmienia architektury wiadomości.

## UX

Dodać albo dopracować:

* avatary / symbole rozmów,
* status online,
* typing indicator,
* `ostatnio widziany`,
* przypięte rozmowy,
* favorite,
* mute,
* rozwijanie i zwijanie sekcji,
* subtelne animacje przejść,
* lepsze unread badges.

## Architektura

Polish korzysta z danych istniejących po Sprintach 45–46.

Jeśli jakiejś informacji nie ma w backendzie, UI nie udaje jej jako aktywnej
funkcji. Może pokazać defensywny fallback albo zostawić miejsce pod przyszły
runtime.

## Frontend

1. Uporządkować sekcje:
   * `ROZMOWY`,
   * `NOWE`,
   * opcjonalnie `ARCHIWUM`, jeśli istnieje realny stan.
2. Zastąpić urzędowe `Oczekujące` lżejszą nazwą UX, jeśli nie psuje flow.
3. Dodać animacje tylko tam, gdzie nie powodują utraty czytelności.
4. Nie rozpychać listy rozmów na mobile.

## Testy

* Unread badge nie znika po zwykłym refreshu.
* Przypięte/favorite rozmowy nie duplikują threadów.
* Mobile nadal nie pokazuje listy i czatu naraz.
* Długie nicki, statusy i preview mają ellipsis.

## Kryteria akceptacji

* Cyberner wygląda jak żywy komunikator świata gry.
* Kanały, system i prywatne rozmowy są czytelne.
* Polish nie tworzy nowych źródeł prawdy.
* Nie zmieniono mail/contact flow.

## Decyzje implementacyjne

* Sprint 47 dopolerowuje wizualnie istniejące stany: kanał, placeholder,
  rozmowa prywatna, pending i źródło świata.
* `WORLD`, `ZNAJOMI` i `KLAN` są wizualnie odróżnione od prywatnych kontaktów.
* Placeholdery `ZNAJOMI` i `KLAN` pozostają disabled, dopóki backend nie ma
  runtime wiadomości tych kanałów.
* Nie dodano aktywnych funkcji `typing`, `last seen`, `pin`, `favorite` ani
  `mute`, bo nie mają jeszcze źródła prawdy w backendzie.
* Unread badge, długie nazwy, preview i statusy mają być kompaktowe i nie
  rozpychać listy rozmów.

---

# Sprint 48 - Cyberner Active Social Channels

## Cel gameplayowy

Aktywowac kanaly `ZNAJOMI` i `KLAN` jako realne kanaly Cybernera, bez tworzenia
drugiego messengera, drugiego inboxa, `channel_store` ani drugiego contact flow.

## Architektura

Kanaly sa singletonowym runtime/read modelem nad istniejacym `mail_store`.

* `WORLD` pozostaje kompatybilnie `scope = group`, `peer = global`.
* `ZNAJOMI` uzywa `scope = channel`, `peer = friends`.
* `KLAN` uzywa `scope = channel`, `peer = clan:<clan_name>`.
* Kanal nie jest kontaktem i nie trafia do `/api/contacts`.
* Kontakt pozostaje prywatna rozmowa.
* Pending request pozostaje osobnym contact flow.

## Backend

1. Rozszerzyc istniejacy `mail_store` o obsluge `scope = channel`.
2. Nie dodawac endpointow.
3. Nie tworzyc osobnego storage kanalow.
4. Wiadomosc `ZNAJOMI` rozsyla sie do zaakceptowanych kontaktow gracza.
5. Wiadomosc `KLAN` rozsyla sie do profili z tym samym klanem.
6. Brak klanu oznacza brak aktywnego kanalu `KLAN` w read modelu.
7. Unread kanalu liczy sie per `scope = channel` i `peer_name`.

## Frontend

1. Usunac placeholder `wkrotce` z aktywnego `ZNAJOMI`.
2. Usunac placeholder `wkrotce` z `KLAN`, jesli profil ma klan.
3. Composer dziala w aktywnych kanalach.
4. Ikony nadal pochodza z `CYBERNER_ICON_LIBRARY` po `source` / `channel`.
5. Mobile/narrow nadal dziala jako lista -> czat -> lista.

## Kryteria akceptacji

* `WORLD` dziala jak dotad.
* `ZNAJOMI` otwiera aktywny kanal znajomych.
* `KLAN` otwiera aktywny kanal, jesli profil ma klan.
* Brak klanu nie wywala UI.
* Kanaly nie pojawiaja sie w contacts.
* Pending request nadal dziala osobno.
* Prywatne rozmowy nadal dzialaja przez `openEmailChatWith(peer)`.
* Nie powstal `channel_store`, drugi inbox ani drugi contact flow.

---

# Sprint 49 - Cyberner Notification Bridge

## Cel gameplayowy

Domknac komunikacje swiata gry przez most pomiedzy Cybernerem i istniejacym
systemem `system_messages`.

Nowe wiadomosci Cybernera moga generowac toast, ale toast jest tylko sygnalem.
Pelna rozmowa zawsze znajduje sie w Cybernerze.

## Architektura

Nie tworzyc:

* drugiego toast systemu,
* drugiego notification center,
* drugiego unread managera.

Rozwijane systemy:

* `mail_store`,
* `system_messages`,
* renderer toastow,
* Cyberner.

Przeplyw:

```text
mail_store
↓
system_messages
↓
toast
↓
Cyberner thread
```

## Backend

1. Nowa wiadomosc Cybernera moze dopisac lekki `system_message`.
2. `system_message` dostaje `notification_type = cyberner`.
3. Payload zawiera tylko:
   * `source`,
   * `scope`,
   * `peer`,
   * `sender`,
   * `title`,
   * krotki `text`.
4. Nie zapisywac pelnej tresci rozmowy w toascie.
5. Nie dodawac nowych endpointow.

## Frontend

1. Dodac `CYBERNER_NOTIFICATION_LIBRARY` jako osobna biblioteke wygladu toastow.
2. Renderer toastow rozroznia `notification_type = cyberner`.
3. Cybernerowy toast ma wlasny delikatny styl.
4. Klik toasta otwiera Cybernera i odpowiedni thread.
5. Nie pokazywac toasta, jesli ten thread jest aktualnie otwarty.
6. Zwykle systemowe toasty pozostaja bez zmiany.

## Kryteria akceptacji

* Cyberner korzysta z istniejacego `system_messages`.
* Nie powstal drugi system toastow.
* Toast otwiera wlasciwa rozmowe.
* Toast nie pokazuje pelnej tresci rozmowy.
* Kanaly `WORLD`, `ZNAJOMI` i `KLAN` korzystaja z tego samego mostu.
* Backend pozostaje spojny z `mail_store`.

---

# Finalna architektura Fazy E

Docelowy przepływ komunikacji:

```text
zdarzenie gry / gracz / system
↓
mail_store albo system_messages
↓
/api/mail/bootstrap
↓
lista rozmów
↓
/api/chats/messages
↓
widok czatu
↓
odpowiedź / akcja kontaktu
↓
ten sam contact/mail flow
```

Zasady integracji:

* Cyberner jest jedynym messengerem gracza.
* Kontakty i pending threads korzystają z istniejącego contact flow.
* Mobile/narrow to zmiana prezentacji, nie osobny runtime.
* `mailMobileView` jest stanem UI, nie stanem gameplayowym.
* Backend wiadomości pozostaje źródłem prawdy.
* Frontend nie tworzy wiadomości ani kontaktów poza istniejącymi endpointami.
* System/Ghost Exchange/player messages mają trafiać do istniejących kanałów,
  nie do nowego inboxa.
* Cyberner pokazuje źródła rozmów, nie foldery poczty.
* `CYBERNER_ICON_LIBRARY` jest centralnym źródłem ikon dla rozmów i źródeł
  komunikacji.


---

# Faza F - Ghost Hack Radio / Audio Narrative Layer

Faza F dodaje do CHAOS prosty lokalny system radia MP3 jako warstwe klimatu i
przyszlej narracji BlackNet.

Radio nie jest drugim komunikatorem, drugim Cybernerem ani systemem misji. Jest
lokalnym playerem audio opartym o jawny kontrakt kanalu `meta.channel`.

Docelowy kierunek:

```text
static/mp3/radio/channel/{id}/meta.channel
↓
playlist tracks
↓
Ghost Hack Radio player
↓
audio atmosphere / BlackNet narrative
```

Podstawowa struktura katalogow:

```text
static/mp3/radio/
└── channel/
    └── ghost_streem_1/
        ├── meta.channel
        ├── 001_intro.mp3
        ├── 002_loop.mp3
        └── 003_noise.mp3
```

`meta.channel` jest kontraktem kanalu. Dla `ghost_streem_1` nie trzyma recznej
playlisty. Opisuje zasady streamu, a runtime buduje kolejke z plikow MP3
lezacych w katalogu kanalu.

Przykladowy kontrakt:

```json
{
  "schema": 1,
  "id": "ghost_streem_1",
  "name": "Ghost Hack Radio",
  "slug": "ghost-streem-1",
  "description": "Pierwszy piracki kanal systemowy GhostNet.",
  "autoplay": true,
  "loop": true,
  "mode": "random",
  "sort": "name",
  "exclude": []
}
```

Architektura frontendowa:

```javascript
const RADIO_BASE_PATH = "/static/mp3/radio/channel";
const DEFAULT_CHANNEL = "ghost_streem_1";
```

Flow:

```text
loadChannel("ghost_streem_1")
↓
fetch /api/radio/channel/ghost_streem_1
↓
parse meta.channel + resolved mp3 list
↓
track.url = /static/mp3/radio/channel/ghost_streem_1/{file}
↓
play losowy track z kolejki, jesli mode = random
↓
ended -> next track
↓
last track -> first track, jesli loop = true
```

Autoplay jest lokalnym ustawieniem gracza:

```javascript
localStorage.setItem("ghost_radio_autoplay", "0");
localStorage.setItem("ghost_radio_autoplay", "1");
```

Domyslnie radio moze startowac automatycznie, ale gracz musi miec prosta opcje
wylaczenia autoplay bez zmiany kodu.

---

# Sprint 50 - Ghost Hack Radio Foundation

## Cel gameplayowy

Przygotowac fundament pod Ghost Hack Radio bez implementacji playera audio.

Sprint konczy sie gotowa struktura aplikacji i kontraktem danych, aby Sprint 51
mogl skupic sie wylacznie na odtwarzaniu muzyki.

## Zakres

1. Utworzyc strukture katalogow:
   * `static/mp3/radio/`,
   * `static/mp3/radio/channel/`.
2. Przygotowac pierwszy kanal:
   * `static/mp3/radio/channel/ghost_streem_1/`.
3. Dodac pierwszy kontrakt:
   * `meta.channel`.
4. Zdefiniowac schema kontraktu:
   * `schema: 1`.
5. Dodac podstawowe pola:
   * `id`,
   * `name`,
   * `slug`,
   * `description`,
   * `autoplay`,
   * `loop`,
   * `mode`,
   * `sort`,
   * `exclude`.
6. Nie trzymac recznej playlisty `ghost_streem_1` w `meta.channel`.
7. Kolejka ma powstawac z plikow MP3 katalogu kanalu wedlug zasad
   `meta.channel`.
8. Przygotowac miejsce na przyszla aplikacje desktopowa `Ghost Hack Radio`.
9. Dodac podstawowa ikone aplikacji albo placeholder.
10. Przygotowac strukture JS:
    * `static/js/ghost_radio.js`,
    * bez logiki odtwarzania.
11. Przygotowac strukture CSS:
    * `static/css/ghost_radio.css`,
    * bez finalnego wygladu.
12. Udokumentowac kontrakt `meta.channel` jako jedyne zrodlo prawdy zasad
    streamu.

## Poza zakresem

* Brak odtwarzania MP3.
* Brak HTML playera.
* Brak Audio API.
* Brak play/pause.
* Brak progress.
* Brak volume.
* Brak autoplay runtime.
* Brak backendu.

## Kryteria akceptacji

* Istnieje katalog radio.
* Istnieje pierwszy kanal.
* Istnieje `meta.channel`.
* Kontrakt posiada `schema = 1`.
* Struktura JS zostala utworzona.
* Struktura CSS zostala utworzona.
* Aplikacja Ghost Hack Radio ma przygotowane miejsce w desktopie.
* Brak regresji desktopu.
* Brak backendu.

---

# Sprint 51 - Ghost Hack Radio v0.1

## Cel gameplayowy

Dodac pierwszy prosty lokalny player MP3, ktory wnosi do desktopu CHAOS zywy
sygnal audio i przygotowuje fundament pod przyszle kanaly BlackNet.

## Zakres

1. Uzyc struktury i kontraktu przygotowanego w Sprincie 50.
2. Player czyta resolver kanalu oparty o `meta.channel`.
3. Zbudowac kolejke z plikow MP3 katalogu kanalu.
4. Dla `mode = random` startowac z losowego utworu.
5. Po `ended` przechodzic do kolejnego utworu w kolejce streamu.
6. Po ostatnim utworze wracac do poczatku kolejki, jesli `loop = true`.
7. Dodac `play/pause`.
8. Dodac pasek postepu.
9. Dodac volume.
10. Dodac lokalne ustawienie autoplay:
    * `ghost_radio_autoplay = "1"` domyslnie,
    * `ghost_radio_autoplay = "0"` wylacza start automatyczny.

## UX

Player ma byc stylizowany na stary Winamp, ale w klimacie CHAOS:

* nazwa kanalu,
* tytul aktualnego tracka,
* status `SIGNAL ONLINE`,
* play/pause,
* progress,
* volume,
* prosty fake equalizer,
* przelacznik autoplay.

## Architektura

Nie tworzyc backendu streamingu.

Lekki resolver kanalu moze zwracac read model plikow MP3 z katalogu, ale nie
moze odtwarzac, streamowac ani zapisywac stanu radia.

Nie laczyc jeszcze z Cybernerem, BlackNet ani misjami.

To jest lokalny player oparty o statyczny manifest kanalu.

## Kryteria akceptacji

* Radio laduje kanal `ghost_streem_1` przez `meta.channel`.
* Kolejka streamu powstaje z katalogu kanalu wedlug `mode/sort/exclude`.
* Play/pause dziala.
* Radio nie odpala zawsze tego samego utworu po wejsciu do gry.
* Loop dziala po calej kolejce streamu.
* Autoplay mozna wylaczyc przez localStorage/UI.
* Jesli autoplay zostanie zablokowany przez przegladarke, UI pokazuje gotowy
  player i pozwala uruchomic radio pierwszym kliknieciem.
* Brak regresji desktopu i mobile.

---

# Sprint 52 - Ghost Hack Radio Desktop App

## Cel gameplayowy

Dodac Ghost Hack Radio jako pelnoprawna aplikacje desktopowa CHAOS
wykorzystujaca istniejaca architekture okien systemowych.

Player ze Sprintu 51 zostaje osadzony w oknie aplikacji. Radio dziala jako
usluga w tle: zamkniecie okna nie zatrzymuje muzyki, a ponowne otwarcie pokazuje
aktualny stan playera.

## Zakres

1. Dodac aplikacje `Ghost Hack Radio` do desktopu.
2. Dodac ikone aplikacji:
   * na desktopie,
   * w menu Start,
   * na desktopie mobilnym.
3. Otwierac radio w standardowym oknie systemowym CHAOS.
4. Osadzic istniejacy modul `GhostRadio` w oknie.
5. Pokazac:
   * nazwe kanalu,
   * aktualny utwor,
   * status `SIGNAL ONLINE`,
   * Play / Pause,
   * Previous / Next,
   * Mute,
   * pasek postepu,
   * regulator glosnosci,
   * prosty fake equalizer bez analizy dzwieku.
6. Ponowne otwarcie okna nie moze resetowac playlisty ani stanu audio.
7. Przycisk Mute dziala natychmiast i zachowuje poprzedni poziom glosnosci.
8. Nie dodawac nowych kanalow, ustawien, backendu, streamingu ani BlackNet.

## Poza zakresem

* wybor kanalow,
* ustawienia,
* autoplay,
* backend,
* streaming,
* BlackNet,
* dynamiczne komunikaty.

## Kryteria akceptacji

* Ghost Hack Radio jest widoczne jako aplikacja desktopowa.
* Ghost Hack Radio jest widoczne w menu Start.
* Ghost Hack Radio jest widoczne w stalym zestawie ikon mobile.
* Radio otwiera sie w standardowym oknie systemowym CHAOS.
* Zamkniecie okna nie zatrzymuje muzyki.
* Ponowne otwarcie pokazuje aktualny kanal, utwor, czas i stan play/pause.
* Mute i volume dzialaja bez nowej logiki odtwarzania.
* Fake equalizer jest tylko wizualizacja UI.
* Nie powstal backend radia.

---

# Sprint 53 - Radio Channel Contract for Future BlackNet

## Cel gameplayowy

Wyprowadzic kontrakt kanalow Ghost Hack Radio pod przyszly BlackNet, bez
zakladania, ze BlackNet istnieje juz fizycznie w runtime.

Sprint 53 nie integruje radia z BlackNet. Sprint 53 definiuje pierwszy kontrakt,
ktory pozwoli przyszlemu BlackNet dokladac kanaly audio bez przebudowy playera.

## Zakres

1. Doprecyzowac `meta.channel` jako kontrakt kanalu audio.
2. Przygotowac zasady katalogow kanalow:
   * kanal ma wlasny katalog,
   * kanal ma wlasny `meta.channel`,
   * pliki audio leza w tym samym katalogu co kontrakt.
3. Przygotowac minimalny model przyszlego kanalu BlackNet:
   * `id`,
   * `slug`,
   * `name`,
   * `description`,
   * `source`,
   * `mode`,
   * `sort`,
   * `exclude`.
4. Przyszly BlackNet bedzie mogl dodawac kanaly jako:
   * `meta.channel`,
   * pliki audio w katalogu kanalu.
5. Radio nadal czyta tylko kontrakt kanalu i read model resolvera katalogu.
6. Nie trzymac recznej playlisty w UI.
7. Nie robic dynamicznego generowania audio w runtime.
8. Nie dodawac backendu BlackNet.
9. Nie mieszac radia z Cybernerem:
   * Cyberner jest rozmowa,
   * radio jest sygnalem audio.
10. Opcjonalnie opisac przyszle eventy UI, ale ich nie implementowac:
   * nowy kanal wykryty,
   * zaklocenia,
   * `SIGNAL LOST`,
   * `BLACKNET SIGNAL`.
11. Udokumentowac kontrakt w `doc/radio_channel_contract.md`.
12. Ustawic jawne `source` w pierwszym kanale `ghost_streem_1`.

## Poza zakresem

* implementacja BlackNet,
* endpointy BlackNet,
* automatyczne wykrywanie kanalow,
* dynamiczny download MP3,
* system misji audio,
* laczenie radia z Cybernerem.

## Kryteria akceptacji

* Istnieje jasny kontrakt kanalu audio dla przyszlego BlackNet.
* BlackNet nie jest traktowany jako istniejacy runtime.
* Przyszly BlackNet bedzie mogl dodac kanal bez zmiany kodu playera.
* Pierwszy kanal ma jawne `source`.
* Radio nie zna logiki misji.
* `meta.channel` pozostaje jedynym kontraktem zasad streamu.
* System jest gotowy pod narracje audio, ale nie wymaga backendu streamingu.

---

# Sprint 54 - Ghost Hack Radio UX Lift + First Interaction Autostart

## Cel gameplayowy

Dopolerowac UI Ghost Hack Radio i podpiac start audio pod pierwsza interakcje
gracza z runtime gry.

Radio ma pozostac lokalnym playerem klientowym. Sprint 54 nie dodaje backendu,
BlackNet, streamingu ani zmian kontraktu `meta.channel`.

## Zakres

1. Okno radia po resize wypelnia dostepna przestrzen.
2. Glowny panel playera rozciaga sie na wysokosc okna.
3. Sekcja source/playlist nie zostawia duzej pustej martwej przestrzeni.
4. Status, equalizer, progress, controls i volume wygladaja jak jeden spojny
   modul systemowy CHAOS.
5. Mobile nie dostaje regresji layoutu.
6. Radio uzbraja autostart po pierwszej interakcji gracza:
   * `pointerdown`,
   * `keydown`.
7. `ghost_radio_autoplay = "0"` twardo wylacza autostart.
8. Jesli browser zablokuje autoplay:
   * player zostaje gotowy,
   * UI pokazuje `CLICK TO START`,
   * radio startuje po kliknieciu Play.
9. Nie dodawac backendu, BlackNet ani nowych kanalow.

## Kryteria akceptacji

* Resize okna nie zostawia playera jako malego panelu przyklejonego do gory.
* Player zachowuje czytelnosc w malym i duzym oknie.
* First interaction autostart dziala tylko, jesli lokalne ustawienie go nie
  wylaczylo.
* `ghost_radio_autoplay = "0"` blokuje autostart.
* Play / Pause / Mute / Volume / Next / Previous nadal dzialaja.
* Brak regresji desktopu mobilnego.
* Brak backendu i brak BlackNet.

---

# Faza G - State Snapshot + Delta Feed

Faza G porzadkuje odswiezanie runtime CHAOS. Celem nie jest zastapienie wszystkich
endpointow jednym monolitem, tylko przejscie z agresywnego pollingu pelnych
snapshotow na model:

```text
snapshot na start / recovery
↓
lekki delta feed dla zmian
↓
applyDelta() po stronie frontendu
```

Snapshot endpointy zostaja jako bezpieczna sciezka startowa i awaryjna.
Delta endpoint ma sluzyc do biezacego odswiezania malych zmian.

Najwazniejsza zasada Fazy G:

```text
Najpierw audyt i kontrakt.
Potem backend rownolegle do starego flow.
Potem pojedyncze male scope'y.
Mapa dopiero na koncu.
```

Nie zaczynamy od WebSocketow. Najpierw powstaje model wersji, schema eventow i
delta bus. WebSocket moze w przyszlosci uzyc tego samego kontraktu jako innego
transportu.

## Zasady bezpieczenstwa Fazy G

Zrodlem prawdy nadal pozostaja obecne modele runtime:

* profil gracza,
* `profile.files`,
* modele mapy,
* `mail_store`,
* `system_messages`,
* Ghost Exchange,
* Googleplex,
* istniejace snapshot endpointy.

Delta bus nie liczy stanu gry.

Delta bus jest tylko dziennikiem powiadomien o zmianach, ktore juz zaszly w
zrodlach prawdy.

Frontend moze uzyc delty do aktualizacji widoku, ale przy rozjezdzie musi wrocic
do snapshotu danego scope.

Delta eventy musza byc idempotentne. Zastosowanie tego samego eventu drugi raz
nie moze zepsuc UI ani podwoic efektu.

Delta log musi miec retencje. Nie moze rosnac bez konca.

## Checkpointy testowe Fazy G

Faza G idzie sprintami. Nie dopisujemy kolejnych warstw planu przed rozpoczeciem
implementacji. Po wiekszych krokach robimy live checkpoint i porownujemy
zalozenia z realnym zachowaniem gry.

Checkpointy:

* Po Sprincie 55:
  * baseline live,
  * request count,
  * najwolniejsze endpointy,
  * subiektywne lagi i szarpniecia UI.
* Po Sprincie 59:
  * read-only delta endpoint,
  * czy eventy wygladaja poprawnie,
  * czy delta endpoint nie obciaza runtime.
* Po Sprincie 61:
  * pierwsza realna delta wallet,
  * czy saldo zmienia sie bez pelnego profilu,
  * czy event wallet jest idempotentny.
* Po Sprincie 62:
  * storage delta,
  * czy Ghost Exchange i File Manager widza spojny storage,
  * czy `storage_used` i `storage_capacity` nie rozjezdzaja sie po akcjach.
* Po Sprincie 64:
  * mail / Ghost Exchange summary,
  * czy spadla liczba odswiezen,
  * czy spadly payloady,
  * czy unread i GX summary nadal sa aktualne.
* Po Sprincie 65:
  * recovery,
  * czy rozjazdy naprawiaja sie per scope,
  * czy frontend nie robi panic reloadu.
* Po Sprincie 67:
  * map actors,
  * czy mapa przestala szarpac przy markerach,
  * czy ruch aktorow nie wymusza rerenderu calej mapy.
* Po Sprincie 69:
  * final before/after,
  * request count przed i po,
  * najwolniejsze endpointy przed i po,
  * subiektywne lagi przed i po,
  * liczba recovery po migracji.

---

# Sprint 55 - Runtime Synchronization Audit

## Cel gameplayowy

Zrobic techniczny audyt synchronizacji runtime bez przebudowy gry.

Sprint 55 nie zmienia endpointow, nie wylacza pollerow i nie dodaje delta feedu.
Ma dac mape przeplywu danych od backendu do ekranu: co wywoluje zmiane, kto ja
zapisuje, kto ja dzis wykrywa, kto ja renderuje i czy naprawde trzeba
odswiezac caly obiekt.

Audyt nie dotyczy samego pollingu. Dotyczy calego cyklu zycia danych.

## Zakres

1. Spisac wszystkie frontendowe pollery.
2. Spisac endpointy odpytywane cyklicznie.
3. Zmierzyc czestotliwosc odpytywania.
4. Wskazac endpointy wywolujace ciezkie funkcje, np. pelny sync profilu.
5. Wskazac miejsca pelnego rerenderu UI.
6. Dla kazdego odswiezanego scope przygotowac karte:
   * scope,
   * snapshot endpoint,
   * polling / trigger odswiezania,
   * ciezkie operacje backendowe,
   * render frontendowy,
   * kandydat na delte.
7. Dla kazdego scope odpowiedziec:
   * co wywoluje zmiane,
   * kto zapisuje zmiane,
   * kto dzis ja wykrywa,
   * kto ja renderuje,
   * czy naprawde trzeba odswiezyc caly obiekt.
8. Oznaczyc scope'y:
   * map,
   * profile,
   * wallet,
   * storage,
   * apps,
   * mail,
   * Ghost Exchange,
   * operations,
   * terminal.
9. Oszacowac spodziewane oszczednosci:
   * request count,
   * payload size,
   * CPU,
   * render cost.
10. Wskazac pollery, ktore mozna usunac albo ograniczyc jeszcze przed delta
    feedem, bo odswiezanie moze wynikac z konkretnej akcji uzytkownika albo
    zdarzenia gry.
11. Nie zmieniac runtime.

## Kryteria akceptacji

* Istnieje lista pollerow i endpointow.
* Wiadomo, ktore requesty sa najciezsze.
* Wiadomo, ktore elementy UI robia pelny rerender.
* Istnieje tabela przeplywu danych per scope.
* Dla kazdego scope wiadomo: trigger, writer, detector, renderer i potrzeba
  snapshotu.
* Istnieje szacunek expected savings per scope.
* Wiadomo, ktore pollery sa potencjalnie zbedne nawet przed delta-feedem.
* Wiadomo, ktore scope'y nadaja sie na pierwsze delty.
* Nie zmieniono zachowania gry.

---

# Sprint 56 - State Version Contract

## Cel gameplayowy

Wprowadzic kontrakt wersji stanu bez migracji UI na delty.

## Zakres

1. Zdefiniowac `state_version`.
2. Zdefiniowac wersje per scope, np.:
   * `wallet_version`,
   * `profile_version`,
   * `storage_version`,
   * `apps_version`,
   * `mail_version`,
   * `ghost_exchange_version`,
   * `operations_version`,
   * `map_version`.
3. Opisac, gdzie wersje sa zwracane:
   * w snapshotach,
   * albo w lekkim read modelu wersji.
4. Nie wymuszac jeszcze dzialania na deltach.
5. Nie wylaczac starych endpointow.
6. Dopisac zasade, ze wersje opisuja snapshoty obecnych modeli, a nie nowy
   magazyn stanu.

## Kryteria akceptacji

* Istnieje kontrakt wersjonowania stanu.
* Wiadomo, ktory scope ma ktora wersje.
* Snapshoty moga zwrocic wersje bez zmiany znaczenia payloadu.
* Frontend nie musi jeszcze korzystac z delt.
* Zrodlem prawdy pozostaja dotychczasowe modele i snapshoty.
* Wersje nie sa nowym magazynem stanu i nie sa liczone z delta busa.

---

# Sprint 57 - Delta Event Schema

## Cel gameplayowy

Ustalic format eventow zmian v0, zanim powstanie backendowy delta bus.

## Zakres

1. Zdefiniowac event:

```json
{
  "version": 1845,
  "scope": "wallet",
  "type": "wallet.balance_changed",
  "entity_id": "wallet",
  "dedupe_key": "wallet:balance:root:1845",
  "payload": {},
  "created_at": "2026-07-06T12:00:00Z"
}
```

2. Ustalic pola:
   * `version`,
   * `scope`,
   * `type`,
   * `entity_id`,
   * `dedupe_key`,
   * `payload`,
   * `created_at`.
3. Ustalic nazewnictwo typow:
   * `wallet.balance_changed`,
   * `storage.used_changed`,
   * `storage.capacity_changed`,
   * `apps.app_installed`,
   * `mail.unread_changed`,
   * `ghost_exchange.summary_changed`,
   * `ghost_exchange.transaction_added`,
   * `operations.operation_updated`,
   * `map.player_moved`.
4. Ustalic minimalne payloady v0 dla pierwszych scope'ow.
5. Dopisac zasade idempotencji:
   * `dedupe_key` identyfikuje event,
   * ponowne zastosowanie tego samego eventu nie zmienia stanu UI drugi raz.
6. Dopisac zasade, ze `payload` nie jest pelnym snapshotem profilu, mapy,
   poczty ani Ghost Exchange.
7. Nie implementowac jeszcze zapisu eventow.

## Kryteria akceptacji

* Istnieje schema eventu delta.
* Istnieje lista typow v0.
* Eventy sa scope'owane.
* Eventy maja `entity_id` do aktualizacji konkretnego obiektu.
* Eventy maja `dedupe_key` do idempotencji.
* Payload nie jest pelnym profilem.
* Istnieje opis minimalnych payloadow v0.
* Nie powstal jeszcze `GameStateDeltaBus`.

---

# Sprint 58 - Backend Delta Bus v0

## Cel gameplayowy

Dodac backendowy dziennik zmian rownolegle do starego systemu.

## Zakres

1. Dodac `GameStateDeltaBus`.
2. Dodac helper:

```text
record_change(scope, change_type, payload)
```

3. Dodac helper:

```text
get_changes_since(user_id, since_version)
```

4. Zapisywac delty bez wplywu na frontend.
5. Nie wylaczac starych endpointow.
6. Nie wymagac WebSocketow.
7. Ustalic retencje delta logu:
   * limit liczby eventow, np. 500-2000,
   * albo limit czasu, np. ostatnie X minut.
8. Nie liczyc stanu gry na podstawie delta busa.

## Kryteria akceptacji

* Backend potrafi zapisac event delta.
* Eventy maja wersje rosnaca monotonicznie.
* Stary runtime gry dziala bez zmian.
* Delta bus nie jest drugim systemem profilu.
* Delta bus nie jest drugim magazynem stanu.
* Istnieje retencja eventow.

---

# Sprint 59 - Read-only Delta Endpoint

## Cel gameplayowy

Udostepnic delty do podgladu i testow bez podpinania UI.

## Zakres

1. Dodac endpoint:

```text
GET /api/state/changes?since=1842&limit=100
```

2. Endpoint zwraca:
   * `current_version`,
   * `changes`,
   * `recovery_required`,
   * `reason`.
3. Endpoint jest read-only.
4. Frontend produkcyjny moze jeszcze go nie uzywac.
5. Endpoint ma limit eventow.
6. Jesli liczba eventow przekracza limit albo wersja jest poza retencja,
   backend zwraca `recovery_required`.
7. Endpoint nie liczy stanu gry.
8. Endpoint nie odpala snapshotow.

## Kryteria akceptacji

* Endpoint zwraca delty od wersji.
* Endpoint nie przebudowuje profilu ani mapy.
* Endpoint nie uruchamia snapshotow.
* Brak delty zwraca pusta liste, nie blad.
* Stary polling nadal dziala.
* Endpoint nie zwraca nieograniczonej historii eventow.
* Za stary `since` prowadzi do recovery, nie do wielkiego payloadu.

---

# Sprint 60 - Delta Diagnostics Panel

## Cel gameplayowy

Dac narzedzie diagnostyczne do obserwacji delt, wersji i rozjazdow.

## Zakres

1. Dodac debug panel albo lekki log dev, np.:

```text
GET /api/dev/delta-diagnostics
```

2. Pokazac:
   * ostatnia wersje,
   * ostatnie eventy,
   * scope,
   * typ eventu,
   * `entity_id`,
   * `dedupe_key`,
   * `payload_size`,
   * liczbe zgubionych/recovery.
3. Pokazac metryki:
   * `delta_events_per_minute`,
   * `delta_payload_size`,
   * `recovery_count`,
   * `pollers_active_count`,
   * `snapshot_recovery_count`.
4. Nie zmieniac runtime gracza.
5. Panel moze byc dostepny tylko w dev/admin mode.
6. Endpoint/panel nie moze wywolywac `sync_session_profile()`.
7. Nie podpinac `applyDelta()`.
8. Nie robic recovery w UI.

## Kryteria akceptacji

* Developer widzi ostatnie delty.
* Widac rozjazdy wersji.
* Widac, czy backend generuje eventy.
* Widac metryki pozwalajace porownac stary polling i delta feed.
* Debug nie jest czescia zwyklego UI gracza.
* Zwykly gracz nie widzi diagnostyki.
* Stary runtime dziala bez zmian.

---

# Sprint 60.5 - Async Operation Runner Audit

## Cel gameplayowy

Wskazac akcje runtime, ktore moga szybko zwracac `operation_id`, a wlasciwa
praca moze konczyc sie w tle.

Sprint 60.5 jest audytem. Nie przerabia jeszcze calego runtime.

## Zakres

1. Spisac endpointy akcji trwajace dluzej niz 1000 ms.
2. Dla kazdej akcji oznaczyc, czy potrzebuje natychmiastowego payloadu.
3. Dla kazdej akcji oznaczyc, czy moze dzialac jako queued operation.
4. Wskazac akcje ryzykowne dla UX przez blokowanie requestu.
5. Wskazac akcje ryzykowne dla backendu przez dlugie trzymanie requestu.
6. Nie dodawac jeszcze workera.
7. Nie przerabiac endpointow na async w tym sprincie.
8. Nie zmieniac gameplayu.

## Kryteria akceptacji

* Istnieje lista ciezkich endpointow akcji.
* Wiadomo, ktore akcje musza zwracac natychmiastowy wynik.
* Wiadomo, ktore akcje moga zwrocic tylko `operation_id`.
* Wiadomo, ktora akcja jest najlepszym kandydatem na v0.
* Nie zmieniono runtime.

---

# Sprint 60.6 - Async Operation Runner v0

## Cel gameplayowy

Status: cancelled / postponed.

Po audycie Sprintu 60.5 zrezygnowano z implementacji Async Operation Runner v0
na tym etapie.

## Powod

Jedynym bezpiecznym kandydatem v0 okazal sie:

```text
POST /api/ghostlab/projects/<project_id>/compile
```

Dla jednej samodzielnej akcji koszt dodania runnera, statusow, deduplikacji,
obslugi bledow i utrzymania osobnego przeplywu async jest wiekszy niz aktualny
zysk runtime.

## Decyzja

Nie wdrazac Async Operation Runnera w Fazie G na obecnym etapie.

Kontynuowac zgodnie z planem od Sprintu 61:

```text
First Safe Delta - Wallet
```

## Wnioski

* Ciezkie endpointy odczytu pozostaja tematem snapshot + delta-feed.
* `/hack-action`, `/map-action`, install/uninstall, Ghost Exchange i polling
  mapy nie sa kandydatami do runnera v0.
* Temat runnera mozna wznowic, gdy pojawi sie wiecej akcji typu queued job.
* Runtime pozostaje bez zmian.

## Kryteria akceptacji

* Runner nie zostal wdrozony.
* Nie dodano `ThreadPoolExecutor`.
* Nie dodano nowych statusow async.
* Nie dodano nowego przeplywu operacji.
* Runtime pozostaje bez zmian.
* Faza G wraca do glownej sciezki delta-feed od Sprintu 61.

---

# Sprint 61 - First Safe Delta: Wallet

## Cel gameplayowy

Pierwsza realna migracja jednego malego elementu UI na delty: saldo HC.

## Zakres

1. Backend zapisuje `wallet.balance_changed`.
2. Frontend odbiera delte.
3. `applyDelta()` aktualizuje tylko saldo.
4. Snapshot wallet zostaje jako recovery.
5. Nie migrowac jeszcze mapy, maila ani aplikacji.
6. Dodac test idempotencji eventu wallet.

## Kryteria akceptacji

* Zmiana HC generuje event.
* Frontend aktualizuje saldo bez pelnego rerenderu.
* Zgubiona wersja odpala snapshot recovery wallet.
* Stary flow HC nie jest zepsuty.
* Ten sam event zastosowany dwa razy nie psuje salda.

---

# Sprint 62 - Storage Delta

## Cel gameplayowy

Przeniesc zmiany storage na delty po sprawdzeniu prostego flow wallet.

## Zakres

1. Dodac eventy:
   * `storage.used_changed`,
   * `storage.capacity_changed`.
2. Aktualizowac File Manager storage bar przez delte.
3. Pokryc:
   * zapis pliku,
   * auto-sale,
   * install aplikacji,
   * uninstall aplikacji,
   * storage upgrade.
4. Snapshot storage zostaje jako recovery.
5. Dodac test idempotencji eventow storage.

## Kryteria akceptacji

* `storage_used` aktualizuje sie bez pelnego bootstrapu.
* `storage_capacity` aktualizuje sie po produkcie Googleplex.
* Recovery snapshot naprawia rozjazd.
* Ghost Exchange i File Manager widza spojny storage.
* Ten sam event storage zastosowany dwa razy nie psuje paska dysku.

---

# Sprint 63 - Apps Delta

## Cel gameplayowy

Przeniesc male zmiany aplikacji na delty bez przebudowy katalogu Googleplex.

## Zakres

1. Dodac eventy:
   * `apps.app_installed`,
   * `apps.app_uninstalled`,
   * `apps.cooldown_changed`,
   * `apps.status_changed`.
2. Aktualizowac ikony, menu Start i File Manager `/tools`.
3. Snapshot apps zostaje jako recovery.
4. Nie zmieniac kontraktu aplikacji.
5. Dodac test idempotencji eventow apps.

## Kryteria akceptacji

* Install/uninstall odswieza UI bez pelnego reloadu.
* `profile.apps` pozostaje zrodlem prawdy.
* `files.tools` pozostaje spojne.
* Brak duplikacji app cache.
* Ten sam event apps zastosowany dwa razy nie tworzy duplikatu ikony/aplikacji.

---

# Sprint 64 - Mail / Ghost Exchange Summary Delta

## Cel gameplayowy

Zmniejszyc polling maila i Ghost Exchange przez migracje licznikow oraz summary.

## Zakres

1. Dodac eventy:
   * `mail.unread_changed`,
   * `mail.thread_updated`,
   * `ghost_exchange.summary_changed`,
   * `ghost_exchange.transaction_added`.
2. Nie migrowac jeszcze pelnego bootstrapu maila.
3. Nie migrowac calego dashboardu GX.
4. Aktualizowac tylko liczniki, badge, summary i ostatnie transakcje.
5. Dodac test idempotencji eventow mail/GX.

## Kryteria akceptacji

* Unread badge aktualizuje sie z delty.
* GX summary aktualizuje sie z delty.
* Pelny mail bootstrap zostaje jako recovery.
* Pelny `/api/ghost-exchange` zostaje jako recovery.
* Ten sam event unread/GX zastosowany dwa razy nie dubluje badge ani transakcji.

---

# Sprint 65 - Delta Recovery

## Cel gameplayowy

Dac twarde mechanizmy naprawy rozjazdu wersji.

## Zakres

1. Frontend wykrywa brakujace albo zbyt stare wersje.
2. Backend moze zwrocic `recovery_required`.
3. Frontend odpala snapshot konkretnego scope, np.:
   * wallet,
   * storage,
   * apps,
   * mail,
   * ghost_exchange.
4. Nie robic globalnego reloadu strony jako domyslnej reakcji.

## Kryteria akceptacji

* Zgubiona delta nie psuje UI.
* Recovery dotyka tylko potrzebnego scope.
* Frontend zapisuje nowa wersje po recovery.
* Brak panic reloadu.

---

# Sprint 66 - Map Delta Audit

## Cel gameplayowy

Przygotowac mape pod delty bez migracji mapy.

## Zakres

1. Spisac typy zmian mapy:
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
2. Okreslic zrodla prawdy dla kazdego typu.
3. Przypisac zrodla prawdy:
   * profil,
   * territory store,
   * target store,
   * vulnerability store,
   * operations runtime.
4. Okreslic, ktore warstwy Leaflet mozna latac punktowo.
5. Okreslic, ktore warstwy dzis sa czyszczone i renderowane od zera.
6. Nie migrowac mapy w tym sprincie.
7. Nie podpinac `applyDelta()` dla mapy.

## Kryteria akceptacji

* Wiadomo, jakie map events sa potrzebne.
* Wiadomo, ktore zrodlo prawdy emituje dany typ zdarzenia.
* Wiadomo, ktore warstwy mapy moga dostac applyDelta.
* Wiadomo, gdzie nadal wymagany jest snapshot.
* Nie zmieniono runtime mapy.

---

# Sprint 67 - Map Actor Delta v0

## Cel gameplayowy

Pierwsza bezpieczna migracja mapy: tylko player actors.

Delta-feed aktualizuje w tym sprincie wylacznie markery graczy. Targety,
terytoria, konflikty, vulnerability layers i friendMarkers zostaja poza
zakresem.

## Zakres

1. Dodac eventy:
   * `map.player_moved`,
   * `map.player_actor_updated`,
   * `map.player_actor_removed`.
2. Backend emituje delty tylko dla player actors.
3. `entity_id` eventu mapy to `username` aktora.
4. Frontend `applyDelta()` aktualizuje tylko `playerActorMarkers`.
5. Jesli marker istnieje:
   * zaktualizowac pozycje,
   * zaktualizowac status/ikone/snapshot menu.
6. Jesli marker nie istnieje:
   * dodac marker gracza.
7. Jesli event to `map.player_actor_removed`:
   * usunac marker gracza.
8. Snapshot `/api/map/player-actors` zostaje jako recovery.
9. `friendMarkers` zostaja poza zakresem v0.
10. Targety, area layers, konflikty i vulnerabilities pozostaja poza zakresem.

## Kryteria akceptacji

* Ruch gracza aktualizuje marker bez rerenderu calej mapy.
* Znikniecie gracza usuwa tylko jego marker.
* Recovery przywraca liste actors.
* Targety i obszary pozostaja poza zakresem.
* `friendMarkers` nie sa migrowane w tym sprincie.

---

# Sprint 68 - Map Target Registry / Delta Prep

## Cel gameplayowy

Przygotowac targety pod przyszle delty przez stabilny registry po `target_id`,
bez migracji pelnych warstw mapy.

Sprint 68 nie wlacza jeszcze `map.target_*` w delta-feed. To sprint
przygotowawczy: targety bazowe dostaja stabilny identyfikator i centralny
registry, ale snapshoty nadal zostaja aktywne.

## Zakres

1. Ustalic stabilne `target_id` dla targetow bazowych.
2. Opisac i przygotowac registry:

```text
targetMarkers[target_id]
```

3. Rozdzielic target marker od warstw:
   * `playerAreaLayers`,
   * `conflictAreaLayers`,
   * `contestedTargetLayers`,
   * `capturedConflictPillarLayers`.
4. Nie ruszac `playerAreaLayers`.
5. Nie ruszac `conflictAreaLayers`.
6. Nie ruszac contested/captured pillar layers.
7. Nie wylaczac snapshotow.
8. Nie wlaczac jeszcze `map.target_updated`, `map.target_captured` ani
   `map.target_removed` w runtime delta-feed.

## Kryteria akceptacji

* Target bazowy ma stabilny `target_id`.
* Istnieje registry `targetMarkers[target_id]`.
* Registry obejmuje target markery, nie area/conflict layers.
* Snapshoty mapy nadal dzialaja.
* Target delta runtime nie zostal jeszcze wlaczony.
* Warstwy terytoriow i konfliktow pozostaja bez zmian.

---

# Sprint 68.5 - Map Target Delta v0

## Cel gameplayowy

Dopiero po registry aktualizowac konkretne targety po `target_id` przez
delta-feed.

Sprint 68.5 wlacza tylko target markery obecne w `targetMarkers[target_id]`.
Nie migruje obszarow, konfliktow ani contested/captured pillar layers.

## Zakres

1. Backend emituje:
   * `map.target_updated`,
   * `map.target_captured`,
   * `map.target_removed`.
2. `entity_id` eventu to stabilny `target_id`.
3. Frontend `applyDelta()` obsluguje target delty tylko przez
   `targetMarkers[target_id]`.
4. Jesli target marker istnieje:
   * `map.target_updated` aktualizuje pozycje/snapshot/tooltip,
   * `map.target_captured` aktualizuje marker jako przejety,
   * `map.target_removed` usuwa marker z registry.
5. Jesli target marker nie istnieje, recovery pozostaje snapshot mapy.
6. Nie ruszac `playerAreaLayers`.
7. Nie ruszac `conflictAreaLayers`.
8. Nie ruszac `area_claimed` / `area_contested`.
9. Nie ruszac contested/captured pillar layers.

## Kryteria akceptacji

* Target delta dziala tylko dla `targetMarkers[target_id]`.
* Capture targetu nie przebudowuje warstw obszarow.
* Snapshot targetow pozostaje recovery.
* `area_claimed` i `area_contested` nadal sa poza zakresem.
* Target delta runtime nie tworzy drugiego stanu mapy.

---

# Sprint 69 - Poller Thinning / Retirement

## Cel gameplayowy

Zmniejszyc liczbe cyklicznych requestow po potwierdzeniu, ze wallet, storage,
apps, mail/Ghost Exchange summary, player actors i target registry dzialaja
bezpiecznie z delta-feed/recovery.

## Zakres

1. Spisac pollery zastapione deltami.
2. Ograniczac albo wylaczac je po jednym.
3. Zostawic snapshoty jako start/recovery.
4. Nie usuwac endpointow snapshotowych.
5. Nie robic globalnego reloadu jako normalnej sciezki.
6. Mierzyc request count przed/po.
7. Mierzyc srednie i maksymalne czasy odpowiedzi przed/po.
8. Mierzyc `recovery_count`.
9. Udokumentowac porownanie przed/po:
   * request count przed,
   * request count po,
   * sredni czas odpowiedzi przed,
   * sredni czas odpowiedzi po,
   * max czas odpowiedzi przed,
   * max czas odpowiedzi po,
   * liczba recovery.

## Kryteria akceptacji

* Liczba cyklicznych requestow spada.
* UI nadal aktualizuje wallet, storage, apps, mail/GX i mape.
* Snapshot recovery nadal dziala.
* Nie ma globalnego reloadu jako normalnej sciezki odswiezania.
* Istnieje raport przed/po pokazujacy realny zysk albo brak zysku.

---

# Sprint 70 - Delta Refactor Integrity Audit

## Cel gameplayowy

Przejsc jeszcze raz wszystkie miejsca zmienione w Fazie G i potwierdzic, ze
delta-feed, recovery, snapshoty i stare pollery sa spojne.

Sprint 70 nie dodaje nowych funkcji. To audyt integralnosci po migracji
wallet/storage/apps/mail/Ghost Exchange/player actors/target registry na
delta-feed.

## Zakres

1. Przejrzec wszystkie helpery `record_*_delta`.
2. Przejrzec wszystkie `event type`.
3. Przejrzec `applyDelta()`.
4. Sprawdzic recovery per scope.
5. Sprawdzic, czy `/api/profile` nie jest wolane po akcji, ktora ma juz delte.
6. Sprawdzic, czy snapshoty sa tylko start/recovery.
7. Sprawdzic, czy nie ma podwojnych aktualizacji UI.
8. Sprawdzic, czy stare pollery nie dubluja delta-feed.
9. Sprawdzic testy wallet/storage/apps/mail/GX/map actors/targets.
10. Porownac dokumentacje z kodem.

## Kryteria akceptacji

* Nie ma ukrytych pelnych refreshy po akcjach objetych deltami.
* Eventy maja spojne `scope`, `type`, `entity_id`, `dedupe_key`.
* `applyDelta()` nie robi pelnych rerenderow bez potrzeby.
* Recovery dziala per scope.
* Snapshot endpointy nadal dzialaja.
* Stare endpointy nie zostaly przypadkiem usuniete.
* Dokumentacja zgadza sie z runtime.

---

# Sprint 71 - Map Initial Load Gate

## Cel gameplayowy

Dodac jawna bramke pierwszego ladowania mapy, zanim gracz zacznie klikac cele i
odpalac akcje.

Sprint 71 nie przyspiesza jeszcze samej mapy. Jego celem jest kontrolowane
wejscie na mape: gracz nie powinien grac na niepelnym stanie swiata.

## Glowna zasada

Mapa nie jest gotowa, dopoki krytyczne warstwy nie zglosza `loaded`.

Leaflet widoczny na ekranie nie oznacza jeszcze gotowej mapy gameplayowej.
Mapa jest gotowa dopiero wtedy, gdy zaladowaly sie warstwy potrzebne do
poprawnej gry.

Preloader mapy nie jest ozdoba. Jest czescia kontraktu runtime: dopoki critical
map scopes nie sa `loaded`, interakcje gameplayowe mapy sa zablokowane.

## UX

Przy pierwszym wejsciu na mape pokazac overlay:

```text
Ladowanie mapy CHAOS...

[████████░░░░░░] 58%

Ladowanie terytoriow graczy...
```

Overlay ma jasno komunikowac, ze mapa sklada ciezki stan swiata, a nie zawiesila
sie.

Podczas bootu akcje mapowe sa zablokowane komunikatem:

```text
Mapa synchronizuje stan swiata.
Akcje beda dostepne po zakonczeniu ladowania.
```

## Architektura

Dodac stan bootu mapy po stronie map template:

```javascript
const mapBootState = {
  loading: false,
  ready: false,
  failed: false,
  loadedScopes: new Set()
};
```

Boot ma miec jawne kroki, np.:

```javascript
async function bootMapInitialState() {
  showMapPreloader();
  disableMapGameplay();

  await bootStep("Pozycja gracza", refreshOwnPlayerPosition);
  await bootStep("Oznaczone cele", refreshMapTargetSnapshot);
  await bootStep("Terytoria graczy", refreshPlayerAreas);
  await bootStep("Podatnosci klanow", refreshClanVulnerabilities);
  await bootStep("Aktywne operacje", refreshActiveOperations);
  await bootStep("Gracze na mapie", refreshPlayerActors);

  enableMapGameplay();
  hideMapPreloader();
}
```

Implementacja moze ladowac czesc krokow sekwencyjnie albo kontrolowana paczka,
ale stan bootu musi byc jawny.

## Critical scopes

Critical scopes blokuja interakcje gameplayowe mapy:

* mapa bazowa,
* pozycja gracza,
* target snapshot,
* terytoria graczy,
* przejete cele.

## Optional scopes

Optional scopes moga dosynchronizowac sie po zdjeciu glownej bramki:

* gracze online,
* podatnosci klanow,
* aktywne operacje,
* live delta status.

Optional scope nie powinien blokowac calej mapy, jesli ma chwilowy blad.

## Systemy

* `templates/map_template.html`,
* Leaflet map runtime,
* `refreshPlayerAreas()`,
* `refreshPlayerActors()`,
* `refreshClanVulnerabilities()`,
* `refreshActiveOperations()`,
* target registry / target snapshot,
* map delta recovery.

## Flow danych

```text
open map
↓
show map preloader
↓
load critical scopes
↓
block map gameplay actions
↓
critical scopes loaded
↓
enable map gameplay
↓
load optional scopes / start pollers / delta-feed
```

## Frontend

1. Dodac overlay pierwszego ladowania mapy.
2. Dodac `mapBootState`.
3. Dodac helper `bootStep(label, fn, options)`.
4. Dodac `disableMapGameplay()` i `enableMapGameplay()`.
5. W czasie bootu blokowac:
   * context menu akcji,
   * hack actions,
   * territory/capture actions,
   * akcje zalezne od target/area layers.
6. Po critical boot wlaczyc gameplay.
7. Optional scopes moga pokazywac status "dosynchronizowanie".
8. Przy recovery mapy mozna pokazac krotki overlay synchronizacji.
9. Nie robic globalnego reloadu strony.

## Backend

Bez nowego backendu.

Sprint 71 korzysta z istniejacych endpointow snapshot/recovery i istniejacych
funkcji map template.

## Testy

* Preloader pojawia sie przy pierwszym wejsciu na mape.
* Preloader pokazuje aktualny scope.
* `mapBootState.ready` jest `false` przed critical boot.
* Akcje mapowe sa zablokowane przed critical boot.
* Terytoria sa widoczne przed rozpoczeciem gry na mapie.
* Przejete cele sa widoczne przed rozpoczeciem gry na mapie.
* Optional scope failure nie blokuje calej mapy.
* Recovery mapy moze pokazac krotki overlay synchronizacji.
* Brak globalnego reloadu strony.

## Kryteria akceptacji

* Przy pierwszym wejsciu na mape pojawia sie preloader.
* Preloader pokazuje aktualnie ladowany scope.
* Mapa nie pozwala klikac akcji przed zakonczeniem critical boot.
* Terytoria sa widoczne przed rozpoczeciem gry na mapie.
* Przejete cele sa widoczne przed rozpoczeciem gry na mapie.
* Gracze/podatnosci/operacje moga doladowac sie jako optional.
* Po recovery mapy mozna ponownie pokazac krotki overlay synchronizacji.
* Nie ma globalnego reloadu strony jako normalnej sciezki bootu.

---

# Sprint 72 - Hack Action Flow Lifting

## Cel gameplayowy

Skrocic najgoretsza sciezke klikniecia na mapie:

```text
klik na mapie
↓
wybor narzedzia
↓
Uzyj
↓
wynik
```

Sprint 72 nie przebudowuje duzej architektury backendu. Celem jest usuniecie
najdrozszego objazdu przez pelny File Manager, pelny `/api/profile` i pelny
render katalogu `/tools`, gdy backend juz zwrocil gotowy `matching_apps`.

## Problem

Obecnie przy wielu pasujacych aplikacjach `/hack-action` zwraca:

```text
tool_selection_required
matching_apps
pending_action
```

Frontend zamiast pokazac lekki wybor narzedzia otwiera pelny File Manager.
To powoduje dodatkowy pelny odczyt profilu i render katalogu plikow tylko po to,
zeby gracz kliknal `Uzyj`.

## Zasada

File Manager pozostaje miejscem przegladania plikow i narzedzi.

File Manager nie jest domyslnym pickerem narzedzia dla akcji mapowej.

Jesli backend zwrocil `matching_apps`, frontend ma wystarczajace dane, zeby
pokazac szybki picker narzedzia bez pobierania calego profilu.

## Zakres

1. Dodac lekki picker narzedzia dla `tool_selection_required`.
2. Picker korzysta wylacznie z:
   * `matching_apps`,
   * `pending_action`,
   * `map_action_id`,
   * `canonical_action`.
3. Nie otwierac pelnego File Managera jako domyslnej sciezki wyboru narzedzia.
4. File Manager moze zostac jako opcja pomocnicza, np. `Pokaz w plikach`.
5. Klikniecie `Uzyj` nadal korzysta z istniejacego `/hack-action`.
6. Po kliknieciu `Uzyj` nie wolac pelnego `/api/profile`, jesli odpowiedz
   `/hack-action` albo delta-feed wystarcza do aktualizacji UI.
7. Ograniczyc zbedne `refreshToolbarProfile()` po uzyciu narzedzia.
8. Nie odpalac pelnego renderu `/tools`, jesli gracz nie otworzyl File Managera
   swiadomie.
9. Nie dodawac jeszcze duzego cache File Managera.
10. Nie przebudowywac DOM polish File Managera w tym sprincie.

## Systemy

* `templates/map_template.html`,
* `openToolSelectionForMapAction()`,
* `selectMapActionTool()`,
* `/hack-action`,
* toolbar / target status,
* delta-feed wallet/storage/apps/map target, jesli dostarcza wystarczajacy
  update.

## Flow danych

```text
/hack-action
↓
tool_selection_required + matching_apps
↓
lekki picker narzedzia
↓
Uzyj
↓
/hack-action selected_app_id
↓
wynik + delty / lokalny update
↓
bez pelnego File Managera i bez pelnego /api/profile
```

## Frontend

1. `openToolSelectionForMapAction(payload)` pokazuje lekki picker zamiast
   `createFileManager({ toolSelection })`.
2. Picker pokazuje tylko pasujace aplikacje.
3. Picker ma jasny tytul akcji i krotkie parametry narzedzia.
4. `Uzyj` blokuje sie na czas requestu, zeby uniknac double-click.
5. Po sukcesie picker sie zamyka albo pokazuje wynik.
6. Mobile/narrow pokazuje picker na wierzchu i bez poziomego scrolla.
7. File Manager zostaje dostepny jako osobna aplikacja.

## Backend

Bez przebudowy backendu.

Sprint 72 korzysta z istniejacego kontraktu `/hack-action`:

* `tool_selection_required`,
* `matching_apps`,
* `pending_action`,
* `selected_app_id`.

Backend moze zostac bez zmian, o ile odpowiedz `/hack-action` wystarcza do
aktualizacji target/toolbar przez istniejace delty albo lokalny payload.

## Poza zakresem

* duzy cache File Managera,
* przebudowa File Managera,
* przebudowa `/api/profile`,
* zmiana algorytmu wyboru aplikacji,
* zmiana ekonomii operacji,
* zmiana map target/area runtime.

## Testy

* Przy wielu pasujacych aplikacjach pojawia sie szybki picker, nie File Manager.
* Picker pokazuje wszystkie `matching_apps`.
* `Uzyj` wysyla `selected_app_id`.
* Double-click `Uzyj` nie dubluje requestu.
* Po sukcesie toolbar/target status aktualizuje sie bez pelnego `/api/profile`,
  jesli delta/payload wystarcza.
* File Manager nadal otwiera sie normalnie jako osobna aplikacja.
* Mobile/narrow picker jest na wierzchu.

## Kryteria akceptacji

* Przy wielu pasujacych apkach gracz widzi szybki picker narzedzia.
* Domyslna sciezka wyboru narzedzia nie pobiera pelnego profilu.
* Domyslna sciezka wyboru narzedzia nie renderuje pelnego katalogu `/tools`.
* Klik `Uzyj` pozostaje zgodny z istniejacym `/hack-action`.
* Brak regresji File Managera.
* Brak regresji map action flow.

---

# Sprint 72.1 - Hack Action Lightweight Preflight

## Cel gameplayowy

Skrocic pierwszy request `/hack-action`, ktory sluzy tylko do wyboru narzedzia.

Sprint 72 pokazal, ze picker frontendowy jest szybki, ale pierwszy request nadal
traci kilka sekund na pelnym `sync_session_profile()`, mimo ze w przypadku
`tool_selection_required` backend nie musi jeszcze tworzyc operacji ani zapisywac
profilu.

## Problem z pomiarow

Dla akcji mapowej z wieloma pasujacymi aplikacjami log pokazuje:

```text
/hack-action selected=False
↓
sync_session_profile ~4-5 s
↓
app_match ~1 ms
↓
return_tool_selection
```

Czyli koszt pierwszego kroku nie wynika z matchowania aplikacji ani z pickera,
tylko z pelnego syncu profilu przed read-only odpowiedzia.

## Zasada

Ten sam endpoint `/hack-action` moze miec dwie wewnetrzne sciezki:

```text
bez selected_app_id
↓
lightweight preflight / wybor narzedzia
```

oraz:

```text
z selected_app_id
↓
real action / zapis profilu / operacja
```

Nie tworzymy nowego endpointu.

Nie zmieniamy kontraktu frontendu.

## Zakres

1. W `/hack-action` wykryc sciezke preflight:
   * brak `selected_app_id`,
   * akcja mapowa moze wymagac wyboru narzedzia.
2. Dla preflight uzyc lekkiego odczytu profilu, jesli wystarcza:
   * `load_profile_readonly(username, strip_sensitive=True)`,
   * albo inny istniejacy readonly helper.
3. Preflight ma odczytac tylko dane potrzebne do wyboru narzedzia:
   * `apps`,
   * minimalny kontekst celu,
   * minimalne blokady wymagane przed pokazaniem pickera.
4. Jesli `matched_apps > 1`, zwrocic:
   * `tool_selection_required`,
   * `matching_apps`,
   * `pending_action`.
5. Preflight nie moze:
   * tworzyc operacji,
   * dopisywac `launch_queue`,
   * zapisywac profilu,
   * odpalac `refresh_and_persist_operations()`,
   * robic pelnego rebuild/session sync, jesli nie jest konieczny.
6. Sciezka z `selected_app_id` pozostaje realnym wykonaniem akcji i nadal moze
   uzyc pelniejszego profilu oraz zapisu.
7. Zachowac debug logi `HACK_FLOW`, aby porownac przed/po.

## Systemy

* `/hack-action`,
* `load_profile_readonly(...)`,
* `get_apps_for_map_action(...)`,
* `serialize_tool_selection_app(...)`,
* lightweight picker Sprintu 72.

## Flow danych

```text
klik akcji mapy
↓
/hack-action bez selected_app_id
↓
readonly profile/apps
↓
matched_apps > 1
↓
tool_selection_required
↓
picker Sprintu 72
```

Po wyborze:

```text
Uzyj
↓
/hack-action z selected_app_id
↓
real action
↓
profile update / operations / delty
```

## Poza zakresem

* nowy endpoint,
* zmiana algorytmu map action,
* przebudowa `sync_session_profile()`,
* optymalizacja map pollerow,
* delta dla warstw mapy,
* zmiana File Managera.

## Testy

* Preflight z wieloma aplikacjami zwraca `tool_selection_required`.
* Preflight nie zapisuje profilu.
* Preflight nie tworzy operacji.
* Preflight nie dodaje `launch_queue`.
* Real action z `selected_app_id` nadal tworzy operacje.
* Debug `HACK_FLOW` pokazuje nizszy czas pierwszego requestu.
* Brak regresji pickera Sprintu 72.

## Kryteria akceptacji

* Pierwszy `/hack-action` dla wyboru narzedzia nie wykonuje pelnego kosztownego
  syncu, jesli nie jest konieczny.
* Picker pojawia sie szybciej niz przed sprintem.
* Realne uzycie narzedzia nadal dziala jak przed sprintem.
* Nie powstal nowy endpoint.
* Nie powstala druga sciezka map action poza `/hack-action`.

Decision:

* Przyjęto: Sprinty 1–20 domykają pierwszą pełną wersję pętli gameplayu.
* Przyjęto: Sprinty 21–30 są podzielone na trzy fazy: Architektura gry, Edukacja gracza i Endgame.
* Przyjęto: Sprint 21.5 domyka Gameplay Contract pomiędzy audytem a implementacją pojemności.
* Przyjęto: Sprinty 21–30 rozwijają narzędzia gracza i Googleplex Tool Laboratory bez tworzenia drugiego sklepu, drugiego systemu plików ani drugiego runtime aplikacji.
* Przyjęto: pojemność i waga stają się częścią kontraktu aplikacji oraz modelu plików.
* Przyjęto: Sprint 31 domyka zasady bezpiecznej aktualizacji bazy na serwerze przez idempotentne migracje.
* Przyjęto: Sprinty 32–33 rozwijają subtelny feedback celu wyłącznie na belce CEL, bez nowego panelu i bez zmiany warunku hackowania.
* Przyjęto: Sprinty 35–39 zmieniają Ghost Exchange z ręcznego panelu sprzedaży plików w automatyczny rynek danych oparty o kolejkę, sektory i idempotentne rozliczenia.
* Przyjęto: Sprinty 40–44 rozwijają Skrzynkę mailową w Cybernera / Messenger CHAOS bez tworzenia drugiego systemu wiadomości, kontaktów ani powiadomień.
* Przyjęto: Sprinty 45–47 rozwijają Cybernera z komunikatora w kanałową warstwę komunikacji świata: audyt kanałów, minimalny runtime i social polish bez drugiego `mail_store`.
* Przyjeto: Sprinty 51-53 rozwijaja Ghost Hack Radio jako lokalna warstwe audio
  oparta o `meta.channel`, bez backendu, bez nowego systemu misji i bez
  przebudowy Cybernera.

---

# Podsumowanie projektowe

CHAOS nie jest tylko grą o hakowaniu.

To gra o prowadzeniu cyfrowego imperium wywiadowczego.

Hakowanie jest początkiem.

Prawdziwa pętla zaczyna się wtedy, gdy:

* obiekt świata staje się celem,
* aplikacja uruchamia operację,
* operacja żyje na mapie,
* dane zamieniają się w pliki,
* pliki zamieniają się w HC,
* HC zamieniają się w nowe aplikacje,
* nowe aplikacje otwierają nowe sposoby hakowania świata.

Mapa nie jest ekranem.
Mapa jest wejściem do świata.

Pliki nie są magazynem.
Pliki są towarem.

Aplikacje nie są efektami.
Aplikacje są narzędziami do uruchamiania operacji.

Googleplex nie jest tylko sklepem.
Googleplex jest silnikiem progresu.

Ghost Exchange nie jest tylko giełdą.
Ghost Exchange jest gospodarką informacji.

To jest kręgosłup implementacji po Sprincie 0.
