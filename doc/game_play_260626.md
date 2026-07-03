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

Decision:

* Przyjęto: Sprinty 1–20 domykają pierwszą pełną wersję pętli gameplayu.
* Przyjęto: Sprinty 21–30 są podzielone na trzy fazy: Architektura gry, Edukacja gracza i Endgame.
* Przyjęto: Sprint 21.5 domyka Gameplay Contract pomiędzy audytem a implementacją pojemności.
* Przyjęto: Sprinty 21–30 rozwijają narzędzia gracza i Googleplex Tool Laboratory bez tworzenia drugiego sklepu, drugiego systemu plików ani drugiego runtime aplikacji.
* Przyjęto: pojemność i waga stają się częścią kontraktu aplikacji oraz modelu plików.
* Przyjęto: Sprint 31 domyka zasady bezpiecznej aktualizacji bazy na serwerze przez idempotentne migracje.
* Przyjęto: Sprinty 32–33 rozwijają subtelny feedback celu wyłącznie na belce CEL, bez nowego panelu i bez zmiany warunku hackowania.

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
