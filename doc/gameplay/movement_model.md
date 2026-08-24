# CHAOS — Movement Model / Active World Refresh

Sprint 0.4 definiuje, jak aktywne operacje i obiekty żyją na mapie bez realtime'owego mielenia świata.

Ten dokument nie opisuje implementacji. To kontrakt projektowy dla przyszłego backendu, mapy, schedulerów, operacji i UI.

---

## Cel

Świat CHAOS ma sprawiać wrażenie żywego, ale nie powinien być symulowany co sekundę.

Aktywne obiekty i operacje aktualizują się na podstawie czasu oraz danych zapisanych w instancji operacji.

Źródłem prawdy są:

* `started_at`
* `last_updated_at`
* `duration`
* `operation_type`
* `target_type`
* `procedural_seed`
* `movement_model`

---

## Zasady główne

### Brak realtime loopa

Nie symulujemy świata w tle co sekundę.

Stan operacji jest wyliczany przy:

* wejściu na mapę,
* odświeżeniu mapy,
* pobraniu aktywnych operacji,
* wykonaniu akcji zależnej od operacji,
* wejściu w profil lub panel operacji.

### Timestampy jako źródło prawdy

Operacja nie musi zapisywać każdej zmiany pozycji ani każdej klatki stanu.

Wystarczy, że ma:

* czas startu,
* czas ostatniego odświeżenia,
* czas końca,
* typ operacji,
* seed proceduralny,
* parametry celu.

Na tej podstawie system może wyliczyć aktualny stan.

### procedural_seed

`procedural_seed` pozwala odtworzyć ruch w powtarzalny sposób.

Jeżeli gracz odświeży mapę dwa razy w tym samym czasie logicznym, powinien zobaczyć ten sam stan.

### Checkpointy tylko jako eventy gameplayowe

Nie zapisujemy każdej klatki ruchu.

Checkpoint zapisujemy tylko, jeśli:

* operacja produkuje historię,
* checkpoint ma wartość gameplayową,
* checkpoint zostanie później użyty do pliku, logu, ryzyka albo sprzedaży danych.

---

## Modele ruchu

### none

Obiekt nie zmienia pozycji.

Pasuje do:

* `camera`
* `atm`
* `router`
* `server`
* `poi`
* `pillar`

Nie tworzy checkpointów, chyba że operacja tworzy log zdarzeń.

### local_walk

Lokalny ruch osoby w małym promieniu.

Pasuje do:

* `person`

Może tworzyć checkpointy, jeśli operacja produkuje historię ruchu.

Ruch może być wyliczany proceduralnie wokół punktu startowego.

### carrier_movement

Ruch urządzenia przenoszonego przez osobę albo gracza.

Pasuje do:

* `phone`
* pochodne urządzenia `person`
* pochodne urządzenia `player`

Może dziedziczyć pozycję z właściciela albo generować lekko przesunięty ślad.

### road_movement

Ruch pojazdu.

Pasuje do:

* `vehicle`

Może być uproszczonym wektorem albo ruchem po drogach.

Dokładny model drogi jest otwartą decyzją.

### player_position

Pozycja realnego gracza.

Pasuje do:

* `player`

Może być odczytywana z profilu/sesji/gracza, a nie proceduralnie.

Śledzenie gracza powinno respektować osobne zasady player target.

### static_active_timer

Statyczny obiekt z aktywnym stanem i licznikiem.

Pasuje do:

* `camera`
* `atm`
* `router`
* `server`
* `poi`

Przykłady:

* aktywny stream kamery,
* wyłączona kamera,
* aktywny stan systemu.

### implant_timer

Statyczny implant lub sniffer z czasem życia.

Pasuje do:

* `atm`
* `router`
* `server`
* `poi`

Zostawia aktywny marker na obiekcie.

Może produkować zasoby w czasie.

### scan_source

Źródło skanu, które nie jest właściwym celem, ale może zwiększać szansę znalezienia celu.

Pasuje do:

* `vehicle_source`

Przykład:

* parking jako źródło potencjalnych pojazdów.

---

## Active object display

Aktywne operacje powinny mieć lekką reprezentację na mapie.

### Tracked vehicle marker

Dla:

* `vehicle_tracking`

Marker pojazdu pokazuje aktualnie wyliczoną pozycję oraz status śledzenia.

Jeśli operacja produkuje historię, checkpointy mogą później tworzyć plik `gps_logs`.

### Tracked device marker

Dla:

* `device_tracking`
* `generic_trace`

Marker pokazuje aktualnie wyliczoną pozycję telefonu, osoby, gracza albo innego celu.

Dla `player` obowiązują osobne reguły player target.

### Camera stream timer

Dla:

* `camera_stream`

Marker kamery pokazuje aktywny stream oraz licznik nagrania, np. `01:35:34`.

Licznik może odświeżać się przy refreshu mapy, np. co 10 sekund.

### Camera shutdown timer

Dla:

* `camera_shutdown`

Marker kamery pokazuje stan zakłócenia/wyłączenia i czas do wygaśnięcia.

### Persistent sniffer marker

Dla:

* `persistent_sniffer`

Marker pokazuje aktywny implant/sniffer na obiekcie oraz czas działania.

### Support operation state

Operacje wspierające nie muszą produkować zasobów.

Mogą zmieniać:

* ryzyko,
* widoczność celu,
* skuteczność innych operacji,
* status obiektu na mapie.

---

## Tabela movement_models

| movement_model | target_types | used_by_operations | position_changes | checkpoint_strategy | history_persisted | refresh_strategy | ui_indicator | default_tick | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `none` | `camera`, `atm`, `router`, `server`, `poi`, `pillar` | `atm_log_extraction` | no | none | no | compute on refresh | static marker | 10 sec | Obiekty statyczne bez aktywnego timera. |
| `local_walk` | `person` | `device_tracking`, `generic_trace`, `microphone_sniffer` | yes | event checkpoints | app-dependent | procedural on refresh | tracked person/device | 10 sec | Lokalny ruch w promieniu celu. |
| `carrier_movement` | `phone` | `device_tracking`, `generic_trace` | yes | event checkpoints | yes | procedural or inherited on refresh | tracked phone | 10 sec | Telefon może być osobnym markerem albo pochodną osoby/gracza. |
| `road_movement` | `vehicle` | `vehicle_tracking`, `generic_trace`, `vehicle_ecu` | yes | route checkpoints | yes | procedural on refresh | tracked vehicle | 10 sec | Docelowo może korzystać z dróg albo uproszczonego wektora. |
| `player_position` | `player` | `device_tracking`, `generic_trace` | yes | event checkpoints | app-dependent | read current position on refresh | tracked player | 10 sec | Wymaga zasad prywatności i player target. |
| `static_active_timer` | `camera`, `poi` | `camera_stream`, `camera_shutdown`, `audio_interference` | no | timer events | app-dependent | compute timer on refresh | active timer / state badge | 10 sec | Streamy i czasowe stany na obiektach. |
| `implant_timer` | `atm`, `router`, `server`, `poi` | `persistent_sniffer` | no | collection events | app-dependent | compute progress on refresh | implant marker / timer | 30 sec | Implant zbiera dane przez czas życia. |
| `scan_source` | `vehicle_source` | future scan/generation operations | optional | scan event | no | compute on scan refresh | source hint | on scan | Parking lub inne źródło potencjalnych celów. |

---

## Tabela operation_refresh_rules

| operation_type | target_type | movement_model | updates_position | updates_timer | creates_checkpoints | creates_resource_progress | expires_by_duration | visible_on_map | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `vehicle_tracking` | `vehicle` | `road_movement` | yes | yes | yes | yes | yes | yes | Pozycja pojazdu wyliczana przy refreshu. |
| `device_tracking` | `person`, `phone`, `player` | `local_walk`, `carrier_movement`, `player_position` | yes | yes | yes | yes | yes | yes | Model zależy od tego, czy śledzimy osobę, telefon czy gracza. |
| `camera_stream` | `camera` | `static_active_timer` | no | yes | no | app-dependent | yes | yes | Aktywny stream z licznikiem czasu. |
| `camera_shutdown` | `camera` | `static_active_timer` | no | yes | no | no | yes | yes | Stan wspierający, zmniejszający ryzyko. |
| `persistent_sniffer` | `atm`, `router`, `server` | `implant_timer` | no | yes | app-dependent | yes | yes | yes | Implant/sniffer z czasem życia. |
| `generic_trace` | `poi`, `person`, `phone`, `player`, `vehicle`, `pillar` | target-dependent | target-dependent | yes | optional | yes | yes | yes | Fallback trace zależny od celu. |
| `microphone_sniffer` | `person`, `venue` | `local_walk`, `static_active_timer` | app-dependent | yes | no | yes | yes | optional | Może być niewidoczny jako marker, ale aktywny w panelu operacji. |
| `atm_log_extraction` | `atm` | `none` | no | optional | no | yes | yes | optional | Krótka operacja odczytu. |
| `wifi_scanner` | `venue`, `shop`, `restaurant`, `bar`, `cafe`, `fast_food` | `none` | no | optional | no | yes | yes | optional | Skan lokacji, zwykle bez aktywnego markera. |
| `audio_interference` | `venue`, `shop`, `restaurant`, `bar`, `cafe`, `fast_food` | `static_active_timer` | no | optional | no | app-dependent | yes | app-dependent | Może być supportem lub źródłem danych, zależnie od aplikacji. |
| `vehicle_ecu` | `vehicle` | `road_movement` | optional | optional | optional | app-dependent | app-dependent | app-dependent | Może zmieniać stan pojazdu albo produkować dane, zależnie od aplikacji. |

---

## Zasady wydajności

### Lekki stan aktywnych operacji

Mapa nie powinna odpytwać ciężkich endpointów przy każdym kliknięciu.

Docelowo aktywne operacje powinny mieć lekki endpoint listujący:

* `operation_id`,
* `operation_type`,
* `status`,
* aktualną pozycję, jeśli potrzebna,
* timer,
* krótki stan UI,
* marker aktywnego obiektu.

### Proceduralne wyliczanie pozycji

Pozycja może być wyliczana proceduralnie na podstawie:

* `started_at`,
* aktualnego czasu,
* `procedural_seed`,
* `movement_model`,
* punktu startowego,
* parametrów operacji.

Nie zapisujemy każdej klatki ruchu.

### Checkpointy jako gameplay events

Checkpoint zapisujemy tylko wtedy, gdy ma znaczenie:

* zasób ma zawierać historię,
* operacja ma udowodnić przebieg,
* ryzyko wymaga śladu,
* gracz później sprzedaje lub analizuje dane.

### Refresh UI

UI może odświeżać widok co 10 sekund, ale backend nie musi w tym czasie przeliczać całego świata.

Backend może zwrócić stan wyliczony z timestampów.

---

## Spójność z istniejącymi dokumentami

Sprawdzone względem:

* `doc/gameplay/world_objects.md`
* `doc/gameplay/operations.md`
* `doc/gameplay/map_actions.md`
* `doc/gameplay/gameplay_matrix.md`

## TODO_DECISION

* Czy `vehicle` porusza się po realnych drogach, czy po uproszczonym wektorze.
* Czy `phone` jest osobnym markerem, czy markerem pochodnym od `person` / `player`.
* Czy `player_position` może być śledzone tak samo jak NPC, czy wymaga osobnych ograniczeń.
* Jak dokładnie liczyć częstotliwość checkpointów dla różnych aplikacji.
* Czy `microphone_sniffer` i `wifi_scanner` mają być widoczne na mapie, czy tylko w panelu aktywnych operacji.
* `world_objects.md` ma `phone` jako rozwijany target_type, ale bez źródła `source_type`; to wymaga decyzji w przyszłym sprincie.
* `vehicle_source` istnieje jako źródło potencjalnych pojazdów, ale nie ma jeszcze operacji generowania konkretnego `vehicle`.

---

## Definition of Done Sprintu 0.4

Sprint 0.4 jest zakończony, gdy:

* istnieje `movement_model.md`,
* wiadomo, że świat nie ma realtime loopa,
* wiadomo, kiedy aktywne operacje są odświeżane,
* wiadomo, jakie movement modele istnieją,
* wiadomo, które operacje aktualizują pozycję,
* wiadomo, które operacje aktualizują licznik,
* wiadomo, które operacje tworzą checkpointy,
* wiadomo, które operacje są widoczne na mapie,
* prawdziwe otwarte decyzje są wpisane w `TODO_DECISION`.
