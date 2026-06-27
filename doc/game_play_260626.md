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
