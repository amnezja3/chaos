# PLAN 0 — Fundament Gameplayu

## Cel

Sprint 0 nie dodaje nowych funkcji do gry.

Jego celem jest zaprojektowanie kompletnego modelu świata i wszystkich zależności, aby od Sprintu 1 każda implementacja była realizacją wcześniej ustalonego projektu, a nie ciągłą zmianą architektury.

Po zakończeniu Sprintu 0 cały zespół (oraz Codex) ma znać pełny kierunek rozwoju systemu.

---

# 0.0 Słownik pojęć i identyfikatorów

## Cel

Ustalić wspólny język dla gameplayu, backendu, mapy, aplikacji i dokumentacji.

Ta sekcja ma zapobiec mieszaniu pól, które dziś bywają podobne znaczeniowo, ale powinny pełnić różne role.

---

## Pojęcia

### map_action_id

Identyfikator akcji wykonywanej z poziomu mapy.

Przykłady:

* `scan_ports`
* `trace_gps`
* `camera_stream`
* `install_sniffer`

Użycie:

* menu mapy
* routing akcji mapy
* `app.map_actions`
* wybór aplikacji zdolnej wykonać akcję

Nie zastępuje:

* `operation_type`
* `app.interface`
* `source_type`

`map_action_id` mówi, co gracz chce zrobić na mapie.

---

### operation_type

Typ operacji uruchamianej po użyciu aplikacji.

Przykłady:

* `vehicle_tracking`
* `device_tracking`
* `atm_sniffer`
* `camera_stream`
* `microphone_sniffer`

Użycie:

* aktywne operacje
* czas życia operacji
* produkcja zasobów
* ryzyko wykrycia

Nie zastępuje:

* `map_action_id`
* `app.type`
* `resource_type`

`map_action_id` może uruchamiać `operation_type`, ale nie jest tym samym. Akcja mapy jest intencją gracza, operacja jest żyjącym stanem gry.

---

### target_type

Gameplayowy typ celu.

Przykłady:

* `camera`
* `atm`
* `shop`
* `person`
* `phone`
* `vehicle`
* `player`
* `server`

Użycie:

* walidacja, czy akcja pasuje do obiektu
* dobór menu mapy
* `app.target_types`
* model świata

Nie zastępuje:

* `source_type`
* `target_mode`

`target_type` opisuje, czym obiekt jest w gameplayu. Może być wyprowadzony z `source_type`, ale powinien być stabilniejszy i niezależny od źródła danych.

---

### resource_type

Typ zasobu produkowanego przez operację.

Przykłady:

* `gps_logs`
* `audio_transcript`
* `atm_dump`
* `camera_dump`
* `credentials`
* `financial_records`

Użycie:

* pliki
* rynek danych
* wycena
* kompletność paczek danych

Nie zastępuje:

* `file_category`
* `market_category`
* `operation_type`

`resource_type` mówi, co powstało jako wartość gameplayowa.

---

### app.interface

Sposób otwierania aplikacji w systemie gracza.

Przykłady:

* `window`
* `terminal`
* `progressbar_random`
* `button_choices`
* `system_launcher`

Użycie:

* desktop
* launcher
* `/command`
* efekt wizualny aplikacji

Nie zastępuje:

* `app.map_actions`
* `operation_type`
* `app.type`

`app.interface` mówi tylko, jak aplikacja się otwiera. Nie mówi, co aplikacja potrafi zrobić na mapie.

---

### app.map_actions

Lista akcji mapy obsługiwanych przez aplikację.

Przykład:

```json
["trace_gps", "trace_device"]
```

Użycie:

* główny router uruchamiania aplikacji z mapy
* wybór narzędzia przy akcji mapy
* walidacja, czy gracz posiada odpowiednią aplikację

Nie zastępuje:

* `app.interface`
* `app.detects`
* `app.affects`
* `app.interferes_with`

To powinno być podstawowe pole decydujące, czy aplikacja może obsłużyć `map_action_id`.

---

### app.type

Ogólny rodzaj aplikacji.

Przykłady:

* `scanner`
* `exploit`
* `sniffer`
* `pro-system-tool`
* `system_lab`

Użycie:

* kategorie Googleplex
* ogólne filtrowanie aplikacji
* balans i wymagania

Nie zastępuje:

* `app.map_actions`
* `app.interface`

`app.type` może pomagać w klasyfikacji, ale nie powinien sam decydować, czy aplikacja obsługuje konkretną akcję mapy.

---

### app.tags

Luźne tagi opisujące aplikację.

Przykłady:

* `finance`
* `intel`
* `gps`
* `camera`
* `social`

Użycie:

* wyszukiwanie
* filtrowanie
* UI
* przyszłe research/gating

Nie zastępuje:

* `app.map_actions`
* `resource_type`
* `operation_type`

Tagi są pomocnicze i nie powinny być głównym routerem gameplayu.

---

### app.detects

Lista rzeczy, które aplikacja potrafi wykrywać.

Przykłady:

* `open_ports`
* `user_location`
* `camera_feed`
* `financial_data`

Użycie:

* jakość wyniku
* kompletność danych
* możliwości poboczne aplikacji

Nie zastępuje:

* `app.map_actions`

`detects` opisuje mechanikę aplikacji, ale nie powinno być głównym routerem uruchamiania z mapy.

---

### app.affects

Lista parametrów lub stanów, które aplikacja zmienia.

Przykłady:

* `risk_level`
* `traceability`
* `system_integrity`

Użycie:

* wpływ aplikacji na cel
* efekty po zakończeniu operacji
* balans zabezpieczeń

Nie zastępuje:

* `app.map_actions`
* `app.interferes_with`

`affects` mówi, co aplikacja zmienia, a nie do jakiej akcji mapy jest przypisana.

---

### app.interferes_with

Lista zabezpieczeń, systemów lub mechanizmów, z którymi aplikacja wchodzi w konflikt.

Przykłady:

* `firewall`
* `camera_system`
* `gps_tracker`
* `vpn_enabled`

Użycie:

* warunki skuteczności
* konflikty zabezpieczeń
* wymagania przed operacją

Nie zastępuje:

* `app.map_actions`
* `app.affects`

`interferes_with` opisuje przeszkody i blokady, a nie główną akcję aplikacji.

---

### source_type

Techniczne lub zewnętrzne źródło obiektu mapy.

Przykłady:

* `overpass_shop`
* `camera`
* `person`
* `manual`
* `generated`

Użycie:

* import z mapy
* heurystyka klasyfikacji
* debugowanie źródeł danych

Nie zastępuje:

* `target_type`

`source_type` mówi, skąd obiekt pochodzi. `target_type` mówi, czym jest w gameplayu.

---

### target_mode

Tryb celu w mechanice hackowania.

Przykłady:

* `poi`
* `player`
* `vulnerability`
* `conflict_pillar`

Użycie:

* rozróżnienie zwykłego celu, gracza, podatności i filaru konfliktu
* walidacja specjalnych ścieżek hackowania

Nie zastępuje:

* `target_type`
* `source_type`

`target_mode` mówi, w jakim trybie system obsługuje cel.

---

### risk_event

Typ zdarzenia ryzyka.

Przykłady:

* `camera_detected`
* `failed_exploit`
* `atm_alarm`
* `long_operation_detected`

Użycie:

* system konsekwencji
* alarmy
* cooldowny
* utrata HC

Nie zastępuje:

* `risk_base`
* `operation_type`

`risk_event` jest zdarzeniem, które może wyniknąć z operacji albo błędu gracza.

---

### market_category

Kategoria zasobu na rynku danych.

Przykłady:

* `financial`
* `credentials`
* `location`
* `surveillance`
* `personal`

Użycie:

* Ghost Exchange
* wycena
* filtrowanie ofert
* preferencje kupujących

Nie zastępuje:

* `resource_type`
* `file_category`

`market_category` mówi, jak rynek traktuje zasób.

---

### file_category

Kategoria pliku w systemie plików gracza.

Przykłady:

* `gps`
* `audio`
* `camera`
* `atm`
* `credentials`

Użycie:

* katalogi
* widok plików
* filtrowanie lokalne

Nie zastępuje:

* `resource_type`
* `market_category`

`file_category` organizuje pliki w systemie gracza, ale nie opisuje pełnej wartości rynkowej zasobu.

---

# 0.1 Model Świata

## Cel

Zdefiniować wszystkie byty występujące w świecie gry.

## Kategorie obiektów

### Statyczne

* Kamery
* Bankomaty
* Routery
* Serwery
* Sklepy
* Restauracje
* Budynki

### Półmobilne

* Telefony
* Osoby
* Pracownicy
* Ochrona
* Klienci

### Mobilne

* Samochody
* Kurierzy
* Taksówki
* Autobusy
* Pojazdy firmowe

---

## Dla każdego typu określić

* sposób poruszania
* promień poruszania
* częstotliwość zmiany pozycji
* czy obiekt może zostać przejęty
* czy może być śledzony
* czy produkuje dane
* czy posiada zabezpieczenia
* czy może zostać wykryty
* czy może zostać naprawiony przez świat gry

## Output

Artefakty:

* `doc/world_objects.md`

Tabela `world_objects`:

* `target_type`
* `label`
* `category` (`static`, `semi_mobile`, `mobile`)
* `source_types`
* `movement_model`
* `movement_radius`
* `movement_frequency`
* `can_be_captured`
* `can_be_traced`
* `produces_data`
* `has_security`
* `can_be_detected`
* `can_be_repaired`
* `default_security_profile`
* `supported_map_actions`

---

# 0.2 Model Akcji Mapy

## Cel

Określić wszystkie możliwe akcje wykonywane z poziomu mapy.

Przykładowo:

* Scan Ports
* Exploit
* Sniff
* Trace
* Trace GPS
* Trace Device
* Camera Stream
* Camera Shutdown
* ATM Logs
* Install Sniffer
* Scan Hotspots
* Audio Hack
* Car Hack

---

## Dla każdej akcji określić

* do jakich obiektów pasuje
* jaka aplikacja może ją obsłużyć
* czy wymaga aktywnej aplikacji
* czy może działać równolegle
* czy tworzy operację
* czy kończy się natychmiast
* czy posiada czas życia

## Output

Artefakty:

* `doc/map_actions.md`
* `doc/gameplay_matrix.md`

Tabela `map_actions`:

* `action_id`
* `label`
* `target_types`
* `requires_app`
* `required_map_action`
* `starts_operation`
* `operation_type`
* `default_duration`
* `risk_base`
* `output_resource_types`
* `support_actions`
* `success_feedback`
* `failure_feedback`

---

# 0.3 Model Aplikacji

## Cel

Rozdzielić odpowiedzialności aplikacji.

Każda aplikacja ma określać:

* sposób uruchomienia
* do jakich akcji mapy pasuje
* jaki typ operacji uruchamia
* jakie dane potrafi pozyskać

---

## Ustalić

* map_actions
* interface
* operation_type
* target_types
* poziomy aplikacji
* możliwość istnienia wielu aplikacji dla jednej akcji

---

## UX

Brak aplikacji

↓

Komunikat systemowy

Jedna aplikacja

↓

Automatyczny start

Kilka aplikacji

↓

Otwarcie katalogu Tools i wybór programu

## Output

Artefakty:

* `doc/app_contract.md`
* `doc/gameplay_matrix.md`

Tabela `app_contract`:

* `app_id`
* `name`
* `app.type`
* `app.interface`
* `app.map_actions`
* `target_types`
* `operation_types`
* `resource_types`
* `tags`
* `detects`
* `affects`
* `interferes_with`
* `required_level`
* `required_respect`
* `risk_level`
* `selection_priority`

---

# 0.4 Model Operacji

## Cel

Oddzielić aplikację od właściwego gameplayu.

Aplikacja uruchamia operację.

Operacja żyje własnym życiem.

---

## Przykładowe operacje

Vehicle Tracking

Device Tracking

Microphone Sniffer

Camera Stream

Camera Shutdown

ATM Sniffer

WiFi Scanner

Vehicle ECU

---

## Dla każdej operacji określić

* sposób uruchomienia
* czas życia
* stan aktywny
* sposób zakończenia
* możliwość wykrycia
* możliwość ponownego uruchomienia
* produkowane zasoby

## Output

Artefakty:

* `doc/operations.md`
* `doc/gameplay_matrix.md`

Tabela `operations`:

* `operation_type`
* `label`
* `started_by_map_actions`
* `target_types`
* `duration`
* `can_run_parallel`
* `active_state`
* `completion_state`
* `failure_state`
* `produces_resource_types`
* `risk_events`
* `support_operations`
* `cooldown`
* `relaunch_rules`

---

# 0.5 Model Ruchu

## Cel

Ustalić sposób działania aktywnych obiektów.

---

Określić

* sposób wyliczania pozycji
* sposób generowania checkpointów
* sposób odświeżania mapy
* czy pozycje są zapisywane
* czy wyliczane proceduralnie
* wpływ czasu na świat

## Output

Artefakty:

* `doc/movement_model.md`
* `doc/world_objects.md`

Tabela `movement_models`:

* `movement_model`
* `target_types`
* `position_source`
* `checkpoint_strategy`
* `refresh_strategy`
* `persist_positions`
* `procedural_seed`
* `time_factor`
* `max_speed`
* `max_radius`

---

# 0.6 Model Danych

## Cel

Określić wszystkie zasoby produkowane przez operacje.

---

Kategorie

GPS Logs

Location History

Financial Records

Personal Records

Credentials

Email Accounts

Call History

Messenger Data

Camera Dumps

ATM Dumps

Vehicle Diagnostics

WiFi Networks

Audio Transcripts

---

## Każdy zasób posiada

* kategorię
* wartość
* rozmiar
* kompletność
* właściciela
* możliwość sprzedaży
* możliwość rozbudowy

## Output

Artefakty:

* `doc/resource_types.md`
* `doc/gameplay_matrix.md`

Tabela `resource_types`:

* `resource_type`
* `label`
* `market_category`
* `file_category`
* `base_value`
* `size`
* `completeness_fields`
* `owner_type`
* `sellable`
* `upgradeable`
* `produced_by_operations`
* `quality_modifiers`

---

# 0.7 Model Plików

## Cel

Połączyć gameplay z systemem plików.

---

Określić

* strukturę katalogów
* sposób tworzenia plików
* sposób grupowania
* sposób podglądu
* sposób usuwania
* sposób sprzedaży

---

Przykładowo

GPS

ATM

Audio

Camera

Credentials

Financial

Personal

## Output

Artefakty:

* `doc/file_model.md`
* `doc/resource_types.md`

Tabela `file_categories`:

* `file_category`
* `directory`
* `resource_types`
* `preview_mode`
* `can_delete`
* `can_sell`
* `grouping_strategy`
* `created_by_operations`
* `market_category`

---

# 0.8 Model Rynku

## Cel

Zaprojektować ekonomię danych.

---

Określić

* Ghost Exchange
* sposób wystawiania danych
* automatyczny skup
* przyszły handel między graczami
* wycenę danych
* zależność ceny od jakości danych

---

Przepływ

Plik

↓

Oferta

↓

Kupujący

↓

HackCoiny

↓

Mail

↓

Usunięcie danych

## Output

Artefakty:

* `doc/market_model.md`
* `doc/resource_types.md`

Tabela `market_model`:

* `market_category`
* `resource_types`
* `base_price_formula`
* `quality_multiplier`
* `completeness_multiplier`
* `buyer_type`
* `instant_buy_enabled`
* `auction_enabled_future`
* `player_trade_enabled_future`
* `mail_notification`
* `remove_file_after_sale`

---

# 0.9 Model Ryzyka

## Cel

Zaprojektować konsekwencje działań gracza.

---

Źródła wykrycia

Kamery

Nieudany exploit

Alarm

ATM

Śledzenie

Za długie operacje

---

Konsekwencje

Identyfikacja

Poszukiwanie

Cooldown

Utrata HC

Więzienie

Konfiskata operacji

---

Operacje wspierające

Camera Shutdown

VPN

Spoofing

Anonymizer

Firewall Bypass

## Output

Artefakty:

* `doc/risk_events.md`
* `doc/gameplay_matrix.md`

Tabela `risk_events`:

* `risk_event`
* `label`
* `source_operations`
* `source_map_actions`
* `base_chance`
* `modified_by_security`
* `modified_by_support_actions`
* `consequence_type`
* `player_feedback`
* `target_feedback`
* `cooldown`
* `penalty`

---

# 0.10 Gameplay Loop

## Cel

Zamknąć całą pętlę gry.

---

Mapa

↓

Skan

↓

Oznaczenie celu

↓

Uruchomienie aplikacji

↓

Start operacji

↓

Świat zaczyna żyć

↓

Operacja produkuje dane

↓

Dane trafiają do plików

↓

Gracz analizuje dane

↓

Ghost Exchange

↓

Sprzedaż

↓

HackCoiny

↓

Zakup nowych aplikacji

↓

Lepsze operacje

↓

Powrót na mapę

## Output

Artefakty:

* `doc/gameplay_loop.md`
* `doc/gameplay_matrix.md`

Tabela `gameplay_loop_steps`:

* `step_id`
* `label`
* `input_state`
* `player_action`
* `system_action`
* `output_state`
* `next_step`
* `failure_path`
* `feedback`

---

# Efekt Sprintu 0

Po zakończeniu Sprintu 0 powstaje kompletna dokumentacja architektury gameplayu.

Każdy kolejny sprint implementuje wyłącznie wcześniej zaprojektowany element.

Sprint 1 nie będzie już projektowaniem gry.

Będzie realizacją gotowego projektu.

Każdy następny sprint powinien być analizowany według tych samych sektorów:

* Gameplay
* UX
* Backend
* Mapa
* Operacje
* Świat
* Pliki
* Ekonomia
* Ryzyko
* Integracja z pozostałymi systemami

Dzięki temu każdy moduł będzie od początku projektowany jako część jednego spójnego świata, a nie jako oddzielna funkcjonalność.

---

# Artefakty Dokumentacyjne Sprintu 0

Po zakończeniu Sprintu 0 powinny istnieć przynajmniej:

* `doc/gameplay_terms.md`
* `doc/gameplay_matrix.md`
* `doc/world_objects.md`
* `doc/map_actions.md`
* `doc/app_contract.md`
* `doc/operations.md`
* `doc/movement_model.md`
* `doc/resource_types.md`
* `doc/file_model.md`
* `doc/risk_events.md`
* `doc/market_model.md`
* `doc/gameplay_loop.md`

Minimalny zestaw wymagany do startu Sprintu 1:

* `doc/gameplay_terms.md`
* `doc/gameplay_matrix.md`
* `doc/world_objects.md`
* `doc/map_actions.md`
* `doc/operations.md`
* `doc/resource_types.md`
* `doc/risk_events.md`
* `doc/market_model.md`

---

# Definition of Done Sprintu 0

Sprint 0 jest zakończony dopiero wtedy, gdy:

* istnieje słownik pojęć,
* istnieje tabela `map_actions`,
* istnieje tabela `operations`,
* istnieje tabela `resource_types`,
* istnieje tabela `world_objects`,
* istnieje tabela `risk_events`,
* wiadomo, które akcje mapy wymagają aplikacji,
* wiadomo, które akcje mapy mogą być wykonane bez aplikacji,
* wiadomo, które akcje mapy tworzą operacje,
* wiadomo, które akcje mapy kończą się natychmiast,
* wiadomo, które operacje tworzą pliki,
* wiadomo, które operacje tylko zmieniają stan świata,
* wiadomo, które pliki można sprzedać,
* wiadomo, które zasoby mają wartość rynkową,
* wiadomo, które operacje mają ryzyko,
* wiadomo, które akcje wspierające zmniejszają ryzyko,
* wiadomo, jak aplikacja deklaruje obsługiwane `map_actions`,
* wiadomo, że `app.interface` nie jest routerem gameplayu,
* wiadomo, że `app.detects`, `app.affects` i `app.interferes_with` opisują mechanikę, ale nie są głównym routerem uruchamiania z mapy,
* Sprint 1 może być rozpoczęty bez zgadywania nazw pól.
