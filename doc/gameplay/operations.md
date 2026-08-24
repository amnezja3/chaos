# CHAOS — Operations Contract

Sprint 0.3 definiuje operację jako centralny byt gameplayu.

Aplikacja nie jest już końcowym efektem kliknięcia. Aplikacja tworzy instancję operacji, a operacja żyje w świecie gry.

Operacja może:

* trwać,
* produkować dane,
* zostawić aktywny obiekt,
* aktualizować marker,
* zostać wykryta,
* wygasnąć,
* zmienić stan świata,
* pośrednio prowadzić do sprzedaży zasobów.

---

## Model instancji operacji

Każda instancja operacji powinna docelowo posiadać:

| Pole | Znaczenie |
| --- | --- |
| `operation_id` | unikalny identyfikator instancji |
| `operation_type` | typ operacji z tego dokumentu |
| `owner_username` | gracz, który uruchomił operację |
| `source_app_id` | aplikacja, która utworzyła operację |
| `map_action_id` | akcja mapy, która doprowadziła do uruchomienia |
| `target_id` | identyfikator celu, jeśli istnieje |
| `target_type` | gameplayowy typ celu |
| `target_mode` | tryb celu, np. `poi`, `player`, `vulnerability`, `conflict_pillar` |
| `status` | aktualny stan cyklu życia |
| `started_at` | czas startu |
| `expires_at` | czas wygaśnięcia |
| `last_tick_at` | ostatnie odświeżenie operacji |
| `active_object` | dane aktywnego obiektu na mapie, jeśli istnieje |
| `resource_buffer` | zasoby zbierane podczas operacji |
| `risk_state` | aktualny stan ryzyka |
| `support_effects` | aktywne operacje wspierające wpływające na ryzyko lub wynik |

---

## Stany cyklu życia

| Status | Znaczenie |
| --- | --- |
| `start` | operacja została utworzona, ale nie wykonała jeszcze pierwszego ticka |
| `running` | operacja działa |
| `paused` | operacja zatrzymana czasowo przez mechanikę gry |
| `completed` | operacja zakończyła się sukcesem |
| `failed` | operacja zakończyła się niepowodzeniem |
| `detected` | operacja została wykryta przez świat gry lub cel |
| `cancelled` | gracz lub system przerwał operację |
| `timeout` | operacja wygasła po czasie życia |

---

## Zasada produkcji danych

Operacja może produkować `resource_types`, ale ostateczny zakres danych zależy od aplikacji, która ją uruchomiła.

Przykład:

* `camera_stream` może produkować `camera_dump`,
* ale tylko jeśli aplikacja ma odpowiedni kontrakt `resource_types`.

`map_action_id` opisuje intencję.

`app.map_actions` mówi, że aplikacja może obsłużyć intencję.

`operation_type` opisuje żyjący proces.

`resource_types` opisują wynik procesu.

---

# Kontrakty operacji

## vehicle_tracking

### Tożsamość

* `operation_type`: `vehicle_tracking`
* Nazwa: Vehicle Tracking
* Opis: Śledzenie pojazdu w świecie gry.

### Uruchomienie

* `map_action_id`: `trace_gps`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `trace_gps`
* Wymaga celu: tak
* `target_types`: `vehicle`

### Cykl życia

* `start`: aplikacja inicjuje śledzenie pojazdu
* `running`: pojazd jest śledzony
* `paused`: TODO_DECISION, czy gracze mogą pauzować tracking
* `completed`: operacja zakończona i logi zapisane
* `failed`: brak sygnału lub utrata celu
* `detected`: pojazd/cel wykrył śledzenie
* `cancelled`: gracz przerwał tracking
* `timeout`: upłynął czas życia

### Czas

* Czas życia: 2 h
* Odświeżanie: przy refreshu mapy albo ticku świata
* Wygasanie: po `expires_at`

### Aktywny świat

* Zostawia aktywny obiekt: tak
* Porusza obiekt: tak
* Aktualizuje marker: tak
* Generuje checkpointy: tak
* Aktualizuje licznik czasu: tak

### Produkcja danych

* Pliki: tak
* Logi: tak
* Dumpy: nie
* Zasoby: `gps_logs`, `location_history`

### Ryzyko

* `risk_events`: `tracking_detected`, `long_operation_detected`, `signal_lost`
* Zależności: zasięg gracza, czas trwania, zabezpieczenia celu, jakość aplikacji
* Operacje wspierające: `camera_shutdown`, przyszłe `spoofing`, przyszłe `anonymizer`

### Zakończenie

Kończy ją:

* timeout,
* ręczne zatrzymanie,
* wykrycie,
* utrata sygnału,
* sukces po zakończeniu czasu.

### Wynik

* Powstają pliki: tak
* Zmienia stan świata: może zostawić historię trasy
* Mail: opcjonalny komunikat systemowy
* Ghost Exchange: zasoby mogą trafić na rynek po sprzedaży pliku
* HC: nie bezpośrednio, dopiero po sprzedaży danych

---

## device_tracking

### Tożsamość

* `operation_type`: `device_tracking`
* Nazwa: Device Tracking
* Opis: Śledzenie urządzenia powiązanego z osobą, telefonem albo graczem.

### Uruchomienie

* `map_action_id`: `trace_device`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `trace_device`
* Wymaga celu: tak
* `target_types`: `person`, `phone`, `player`

### Cykl życia

* `start`: aplikacja uzyskuje sygnał urządzenia
* `running`: urządzenie jest śledzone
* `paused`: TODO_DECISION
* `completed`: dane lokalizacyjne zapisane
* `failed`: brak dostępu do urządzenia
* `detected`: cel wykrył śledzenie
* `cancelled`: gracz przerwał operację
* `timeout`: koniec czasu życia

### Czas

* Czas życia: 1 h
* Odświeżanie: tick świata / refresh mapy
* Wygasanie: po `expires_at`

### Aktywny świat

* Zostawia aktywny obiekt: tak
* Porusza obiekt: tak, jeśli cel jest mobilny
* Aktualizuje marker: tak
* Generuje checkpointy: tak
* Aktualizuje licznik czasu: tak

### Produkcja danych

* Pliki: tak
* Logi: tak
* Dumpy: nie domyślnie
* Zasoby: `device_logs`, `location_history`

### Ryzyko

* `risk_events`: `device_tracking_detected`, `signal_lost`, `long_operation_detected`
* Zależności: poziom zabezpieczeń urządzenia, relacja z celem, zasięg gracza
* Operacje wspierające: przyszłe `spoofing`, przyszłe `vpn`, przyszłe `anonymizer`

### Zakończenie

Kończy ją:

* timeout,
* ręczne zatrzymanie,
* wykrycie,
* utrata sygnału,
* sukces po zapisaniu historii.

### Wynik

* Powstają pliki: tak
* Zmienia stan świata: może ujawnić trasę celu
* Mail: opcjonalny komunikat systemowy
* Ghost Exchange: dane sprzedawalne po trafieniu do plików
* HC: nie bezpośrednio

---

## microphone_sniffer

### Tożsamość

* `operation_type`: `microphone_sniffer`
* Nazwa: Microphone Sniffer
* Opis: Podsłuch rozmów albo mikrofonów w pobliżu celu.

### Uruchomienie

* `map_action_id`: `mic_sniff`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `mic_sniff`
* Wymaga celu: tak
* `target_types`: `person`, `venue`

### Cykl życia

* `start`: aplikacja otwiera kanał audio
* `running`: audio jest przechwytywane
* `paused`: TODO_DECISION
* `completed`: transkrypcja gotowa
* `failed`: brak źródła audio
* `detected`: podsłuch wykryty
* `cancelled`: gracz przerwał operację
* `timeout`: koniec czasu nagrania

### Czas

* Czas życia: 20 min
* Odświeżanie: tick świata
* Wygasanie: po limicie czasu lub utracie sygnału

### Aktywny świat

* Zostawia aktywny obiekt: nie domyślnie
* Porusza obiekt: nie
* Aktualizuje marker: opcjonalnie
* Generuje checkpointy: nie
* Aktualizuje licznik czasu: tak, jeśli UI pokazuje aktywne nagranie

### Produkcja danych

* Pliki: tak
* Logi: opcjonalnie
* Dumpy: nie
* Zasoby: `audio_transcript`

### Ryzyko

* `risk_events`: `audio_sniff_detected`, `long_operation_detected`
* Zależności: czas nagrania, zabezpieczenia celu, jakość aplikacji
* Operacje wspierające: `camera_shutdown`, przyszłe `noise_masking`

### Zakończenie

Kończy ją:

* timeout,
* ręczne zatrzymanie,
* wykrycie,
* brak sygnału,
* sukces po utworzeniu transkrypcji.

### Wynik

* Powstają pliki: tak
* Zmienia stan świata: nie domyślnie
* Mail: opcjonalny komunikat systemowy
* Ghost Exchange: transkrypcja może być sprzedana
* HC: nie bezpośrednio

---

## camera_stream

### Tożsamość

* `operation_type`: `camera_stream`
* Nazwa: Camera Stream
* Opis: Aktywny stream z kamery.

### Uruchomienie

* `map_action_id`: `camera_stream`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `camera_stream`
* Wymaga celu: tak
* `target_types`: `camera`

### Cykl życia

* `start`: aplikacja przejmuje podgląd kamery
* `running`: stream trwa
* `paused`: TODO_DECISION
* `completed`: stream kończy się i aplikacja zapisuje wynik, jeśli ma taki kontrakt
* `failed`: brak dostępu do kamery
* `detected`: kamera/system wykrył ingerencję
* `cancelled`: gracz przerwał stream
* `timeout`: koniec czasu streamu

### Czas

* Czas życia: 30 min
* Odświeżanie: licznik może odświeżać się przy refreshu mapy, np. co 10 sekund
* Wygasanie: po `expires_at` albo utracie dostępu

### Aktywny świat

* Zostawia aktywny obiekt: tak
* Porusza obiekt: nie
* Aktualizuje marker: tak
* Generuje checkpointy: nie
* Aktualizuje licznik czasu: tak, np. `01:35:34`

### Produkcja danych

* Pliki: zależnie od aplikacji
* Logi: opcjonalnie
* Dumpy: zależnie od aplikacji
* Zasoby: app-dependent: `camera_dump`, `video_material`

### Ryzyko

* `risk_events`: `camera_stream_detected`, `long_operation_detected`
* Zależności: czas streamu, zabezpieczenia kamery, wsparcie `camera_shutdown`
* Operacje wspierające: `camera_shutdown`, przyszłe `spoofing`

### Zakończenie

Kończy ją:

* timeout,
* ręczne zatrzymanie,
* wykrycie,
* utrata dostępu,
* sukces po zakończeniu streamu.

### Wynik

* Powstają pliki: zależnie od aplikacji
* Zmienia stan świata: może zostawić aktywny stan kamery
* Mail: opcjonalny komunikat systemowy
* Ghost Exchange: tylko jeśli powstał sprzedawalny dump/materiał
* HC: nie bezpośrednio

---

## camera_shutdown

### Tożsamość

* `operation_type`: `camera_shutdown`
* Nazwa: Camera Shutdown
* Opis: Tymczasowe wyłączenie albo zakłócenie kamery.

### Uruchomienie

* `map_action_id`: `camera_shutdown`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `camera_shutdown`
* Wymaga celu: tak
* `target_types`: `camera`

### Cykl życia

* `start`: kamera zostaje zakłócona
* `running`: kamera pozostaje wyłączona/zakłócona
* `paused`: nie dotyczy
* `completed`: kamera wraca do normalnego stanu
* `failed`: nie udało się zakłócić kamery
* `detected`: system zauważył manipulację
* `cancelled`: efekt cofnięty
* `timeout`: koniec czasu zakłócenia

### Czas

* Czas życia: 15 min
* Odświeżanie: przy ticku świata
* Wygasanie: automatyczne po czasie

### Aktywny świat

* Zostawia aktywny obiekt: tak, jako stan kamery
* Porusza obiekt: nie
* Aktualizuje marker: tak
* Generuje checkpointy: nie
* Aktualizuje licznik czasu: tak

### Produkcja danych

* Pliki: nie
* Logi: opcjonalnie systemowe
* Dumpy: nie
* Zasoby: none

### Ryzyko

* `risk_events`: `camera_shutdown_detected`
* Zależności: zabezpieczenia kamery, czas działania
* Operacje wspierające: to jest operacja wspierająca dla innych działań

### Zakończenie

Kończy ją:

* timeout,
* wykrycie,
* ręczne cofnięcie,
* awaria aplikacji.

### Wynik

* Powstają pliki: nie
* Zmienia stan świata: tak, kamera jest czasowo nieaktywna
* Mail: opcjonalnie alert/komunikat
* Ghost Exchange: nie
* HC: nie

---

## atm_log_extraction

### Tożsamość

* `operation_type`: `atm_log_extraction`
* Nazwa: ATM Log Extraction
* Opis: Krótka operacja odczytu danych z bankomatu.

### Uruchomienie

* `map_action_id`: `atm_logs`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `atm_logs`
* Wymaga celu: tak
* `target_types`: `atm`

### Cykl życia

* `start`: aplikacja rozpoczyna odczyt
* `running`: dane są pobierane
* `paused`: nie dotyczy
* `completed`: dump gotowy
* `failed`: odczyt zablokowany
* `detected`: bankomat/system finansowy wykrył ingerencję
* `cancelled`: gracz przerwał odczyt
* `timeout`: krótki limit odczytu minął

### Czas

* Czas życia: 10 min
* Odświeżanie: progress aplikacji lub tick operacji
* Wygasanie: po czasie albo wykryciu

### Aktywny świat

* Zostawia aktywny obiekt: nie
* Porusza obiekt: nie
* Aktualizuje marker: opcjonalnie
* Generuje checkpointy: nie
* Aktualizuje licznik czasu: opcjonalnie

### Produkcja danych

* Pliki: tak
* Logi: tak
* Dumpy: tak
* Zasoby: `atm_dump`, `financial_records`

### Ryzyko

* `risk_events`: `atm_alarm`, `financial_intrusion_detected`
* Zależności: zabezpieczenia ATM, jakość aplikacji
* Operacje wspierające: przyszłe `camera_shutdown`, przyszłe `spoofing`

### Zakończenie

Kończy ją:

* sukces pobrania,
* timeout,
* wykrycie,
* przerwanie.

### Wynik

* Powstają pliki: tak
* Zmienia stan świata: nie domyślnie
* Mail: opcjonalnie komunikat systemowy
* Ghost Exchange: dump może być sprzedany
* HC: nie bezpośrednio

---

## persistent_sniffer

### Tożsamość

* `operation_type`: `persistent_sniffer`
* Nazwa: Persistent Sniffer
* Opis: Aktywne urządzenie lub implant zbierający dane przez określony czas.

### Uruchomienie

* `map_action_id`: `install_sniffer`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `install_sniffer`
* Wymaga celu: tak
* `target_types`: `atm`, `router`, `server`

### Cykl życia

* `start`: sniffer zostaje zainstalowany
* `running`: sniffer zbiera dane
* `paused`: TODO_DECISION
* `completed`: sniffer kończy zbieranie
* `failed`: instalacja nieudana
* `detected`: sniffer wykryty
* `cancelled`: gracz usuwa/przerywa sniffer
* `timeout`: koniec czasu działania

### Czas

* Czas życia: 3 h
* Odświeżanie: tick świata
* Wygasanie: po czasie, wykryciu albo usunięciu

### Aktywny świat

* Zostawia aktywny obiekt: tak
* Porusza obiekt: nie
* Aktualizuje marker: tak
* Generuje checkpointy: nie
* Aktualizuje licznik czasu: tak

### Produkcja danych

* Pliki: zależnie od aplikacji
* Logi: tak
* Dumpy: zależnie od aplikacji
* Zasoby: app-dependent: `financial_records`, `network_scan`, `credentials`

### Ryzyko

* `risk_events`: `sniffer_detected`, `long_operation_detected`
* Zależności: czas działania, zabezpieczenia celu, liczba zebranych danych
* Operacje wspierające: `camera_shutdown`, przyszłe `spoofing`, przyszłe `vpn`

### Zakończenie

Kończy ją:

* timeout,
* wykrycie,
* ręczne zatrzymanie,
* awaria,
* sukces po zebraniu danych.

### Wynik

* Powstają pliki: zależnie od aplikacji
* Zmienia stan świata: aktywny implant/sniffer znika albo zostawia ślad
* Mail: opcjonalnie komunikat systemowy
* Ghost Exchange: tylko dla sprzedawalnych zasobów
* HC: nie bezpośrednio

---

## wifi_scanner

### Tożsamość

* `operation_type`: `wifi_scanner`
* Nazwa: WiFi Scanner
* Opis: Skanowanie sieci i hotspotów w lokacji.

### Uruchomienie

* `map_action_id`: `scan_hotspots`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `scan_hotspots`
* Wymaga celu: tak
* `target_types`: `venue`, `shop`, `restaurant`, `bar`, `cafe`, `fast_food`

### Cykl życia

* `start`: skaner rozpoczyna pracę
* `running`: sieci są wykrywane
* `paused`: nie dotyczy
* `completed`: lista sieci gotowa
* `failed`: brak sygnału
* `detected`: wykryto aktywny skan
* `cancelled`: gracz przerwał skan
* `timeout`: limit skanu minął

### Czas

* Czas życia: 10 min
* Odświeżanie: progress aplikacji / tick
* Wygasanie: po zakończeniu skanu

### Aktywny świat

* Zostawia aktywny obiekt: opcjonalnie
* Porusza obiekt: nie
* Aktualizuje marker: opcjonalnie
* Generuje checkpointy: nie
* Aktualizuje licznik czasu: opcjonalnie

### Produkcja danych

* Pliki: tak
* Logi: tak
* Dumpy: nie
* Zasoby: `wifi_networks`

### Ryzyko

* `risk_events`: `wifi_scan_detected`, `signal_anomaly`
* Zależności: liczba sieci, poziom zabezpieczeń lokacji, zasięg gracza
* Operacje wspierające: przyszłe `spoofing`

### Zakończenie

Kończy ją:

* sukces skanu,
* timeout,
* wykrycie,
* ręczne zatrzymanie.

### Wynik

* Powstają pliki: tak
* Zmienia stan świata: może ujawnić hotspoty
* Mail: opcjonalnie komunikat systemowy
* Ghost Exchange: dane WiFi mogą być sprzedawalne
* HC: nie bezpośrednio

---

## audio_interference

### Tożsamość

* `operation_type`: `audio_interference`
* Nazwa: Audio Interference
* Opis: Akcja audio na lokacji, zależnie od aplikacji może wspierać podsłuch albo zakłócać systemy.

### Uruchomienie

* `map_action_id`: `audio_hack`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `audio_hack`
* Wymaga celu: tak
* `target_types`: `venue`, `shop`, `restaurant`, `bar`, `cafe`, `fast_food`

### Cykl życia

* `start`: aplikacja rozpoczyna ingerencję audio
* `running`: efekt audio trwa
* `paused`: TODO_DECISION
* `completed`: efekt zakończony
* `failed`: brak dostępu do systemu audio
* `detected`: ingerencja wykryta
* `cancelled`: gracz przerwał efekt
* `timeout`: koniec czasu działania

### Czas

* Czas życia: app-dependent
* Odświeżanie: tick świata
* Wygasanie: po czasie albo wykryciu

### Aktywny świat

* Zostawia aktywny obiekt: app-dependent
* Porusza obiekt: nie
* Aktualizuje marker: opcjonalnie
* Generuje checkpointy: nie
* Aktualizuje licznik czasu: opcjonalnie

### Produkcja danych

* Pliki: app-dependent
* Logi: opcjonalnie
* Dumpy: nie domyślnie
* Zasoby: app-dependent: `audio_transcript`

### Ryzyko

* `risk_events`: `audio_interference_detected`, `signal_anomaly`
* Zależności: czas, typ lokacji, zabezpieczenia audio
* Operacje wspierające: `camera_shutdown`, przyszłe `noise_masking`

### Zakończenie

Kończy ją:

* timeout,
* ręczne zatrzymanie,
* wykrycie,
* sukces aplikacji.

### Wynik

* Powstają pliki: zależnie od aplikacji
* Zmienia stan świata: może zmienić warunki ryzyka dla innych działań
* Mail: opcjonalnie
* Ghost Exchange: tylko jeśli powstał sprzedawalny zasób
* HC: nie bezpośrednio

---

## vehicle_ecu

### Tożsamość

* `operation_type`: `vehicle_ecu`
* Nazwa: Vehicle ECU
* Opis: Ingerencja w elektronikę pojazdu.

### Uruchomienie

* `map_action_id`: `car_hack`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `car_hack`
* Wymaga celu: tak
* `target_types`: `vehicle`

### Cykl życia

* `start`: aplikacja łączy się z systemem pojazdu
* `running`: ingerencja trwa
* `paused`: TODO_DECISION
* `completed`: efekt aplikacji wykonany
* `failed`: pojazd odrzuca ingerencję
* `detected`: system pojazdu wykrył atak
* `cancelled`: gracz przerwał operację
* `timeout`: limit działania minął

### Czas

* Czas życia: app-dependent
* Odświeżanie: tick świata / progress aplikacji
* Wygasanie: po czasie, wykryciu albo sukcesie

### Aktywny świat

* Zostawia aktywny obiekt: app-dependent
* Porusza obiekt: może wpływać na pojazd, ale nie porusza go samodzielnie
* Aktualizuje marker: opcjonalnie
* Generuje checkpointy: nie domyślnie
* Aktualizuje licznik czasu: opcjonalnie

### Produkcja danych

* Pliki: app-dependent
* Logi: app-dependent
* Dumpy: app-dependent
* Zasoby: app-dependent, np. `vehicle_diagnostics`

### Ryzyko

* `risk_events`: `vehicle_intrusion_detected`, `system_anomaly`
* Zależności: zabezpieczenia pojazdu, jakość aplikacji, czas działania
* Operacje wspierające: przyszłe `spoofing`, przyszłe `gps_masking`

### Zakończenie

Kończy ją:

* sukces aplikacji,
* timeout,
* wykrycie,
* ręczne zatrzymanie,
* awaria.

### Wynik

* Powstają pliki: tylko jeśli aplikacja ma taki kontrakt
* Zmienia stan świata: może zmienić stan pojazdu
* Mail: opcjonalnie
* Ghost Exchange: tylko dla sprzedawalnych danych
* HC: nie bezpośrednio

---

## generic_trace

### Tożsamość

* `operation_type`: `generic_trace`
* Nazwa: Generic Trace
* Opis: Ogólna operacja śledzenia celu, używana jako fallback lub podstawowy trace.

### Uruchomienie

* `map_action_id`: `trace`
* Wymagane aplikacje: aplikacja z `app.map_actions` zawierającym `trace`
* Wymaga celu: tak
* `target_types`: `poi`, `person`, `phone`, `player`, `vehicle`, `pillar`

### Cykl życia

* `start`: aplikacja ustawia śledzenie
* `running`: cel jest obserwowany
* `paused`: TODO_DECISION
* `completed`: ślad gotowy
* `failed`: brak sygnału
* `detected`: wykryto śledzenie
* `cancelled`: gracz przerwał operację
* `timeout`: koniec czasu działania

### Czas

* Czas życia: 1 h
* Odświeżanie: tick świata / refresh mapy
* Wygasanie: po czasie albo utracie celu

### Aktywny świat

* Zostawia aktywny obiekt: tak
* Porusza obiekt: zależnie od celu
* Aktualizuje marker: tak
* Generuje checkpointy: opcjonalnie
* Aktualizuje licznik czasu: tak

### Produkcja danych

* Pliki: tak
* Logi: tak
* Dumpy: nie
* Zasoby: `location_history`

### Ryzyko

* `risk_events`: `trace_detected`, `signal_lost`, `long_operation_detected`
* Zależności: typ celu, zasięg gracza, zabezpieczenia celu
* Operacje wspierające: przyszłe `spoofing`, przyszłe `anonymizer`

### Zakończenie

Kończy ją:

* timeout,
* ręczne zatrzymanie,
* wykrycie,
* utrata sygnału,
* sukces po zapisaniu historii.

### Wynik

* Powstają pliki: tak
* Zmienia stan świata: może ujawnić położenie lub historię celu
* Mail: opcjonalnie
* Ghost Exchange: dane mogą być sprzedane po utworzeniu pliku
* HC: nie bezpośrednio

---

# Tabela referencyjna

| operation_type | resource_types | risk_events | support_operations | active_object | default_duration |
| --- | --- | --- | --- | --- | --- |
| `vehicle_tracking` | `gps_logs`, `location_history` | `tracking_detected`, `long_operation_detected`, `signal_lost` | `camera_shutdown`, future: `spoofing`, `anonymizer` | yes | 2 h |
| `device_tracking` | `device_logs`, `location_history` | `device_tracking_detected`, `signal_lost`, `long_operation_detected` | future: `spoofing`, `vpn`, `anonymizer` | yes | 1 h |
| `microphone_sniffer` | `audio_transcript` | `audio_sniff_detected`, `long_operation_detected` | `camera_shutdown`, future: `noise_masking` | no | 20 min |
| `camera_stream` | app-dependent: `camera_dump`, `video_material` | `camera_stream_detected`, `long_operation_detected` | `camera_shutdown`, future: `spoofing` | yes | 30 min |
| `camera_shutdown` | none | `camera_shutdown_detected` | self/support operation | yes | 15 min |
| `atm_log_extraction` | `atm_dump`, `financial_records` | `atm_alarm`, `financial_intrusion_detected` | future: `camera_shutdown`, `spoofing` | no | 10 min |
| `persistent_sniffer` | app-dependent: `financial_records`, `network_scan`, `credentials` | `sniffer_detected`, `long_operation_detected` | `camera_shutdown`, future: `spoofing`, `vpn` | yes | 3 h |
| `wifi_scanner` | `wifi_networks` | `wifi_scan_detected`, `signal_anomaly` | future: `spoofing` | optional | 10 min |
| `audio_interference` | app-dependent: `audio_transcript` | `audio_interference_detected`, `signal_anomaly` | `camera_shutdown`, future: `noise_masking` | app-dependent | app-dependent |
| `vehicle_ecu` | app-dependent: `vehicle_diagnostics` | `vehicle_intrusion_detected`, `system_anomaly` | future: `spoofing`, `gps_masking` | app-dependent | app-dependent |
| `generic_trace` | `location_history` | `trace_detected`, `signal_lost`, `long_operation_detected` | future: `spoofing`, `anonymizer` | yes | 1 h |

---

# Spójność z istniejącymi dokumentami

Sprawdzone względem:

* `doc/gameplay/gameplay_terms.md`
* `doc/gameplay/app_contract.md`
* `doc/gameplay/map_actions.md`
* `doc/gameplay/world_objects.md`
* `doc/gameplay/gameplay_matrix.md`

## TODO_DECISION

* `generic_sniffer` nie jest obowiązkowym kontraktem teraz. Jeśli okaże się potrzebny dla spójności sniffingu, dopisać go jako TODO_FUTURE.
* `resource_type` `video_material` jest przyszłym typem zasobu. Jego kontrakt zostanie doprecyzowany w Sprincie 0.5 / Model Danych.

## Źródło prawdy po Sprincie 0.3

Nowszy kontrakt `doc/gameplay/map_actions.md` i ten dokument są źródłem prawdy dla:

* `scan_ports`: nie produkuje zasobów handlowych; może tworzyć tylko wewnętrzny stan rozpoznania.
* `camera_stream`: tworzy aktywną operację / aktywny obiekt na mapie z licznikiem czasu.
* `sniff`: jest app-dependent i może być warunkiem hackowania, `persistent_sniffer` albo data-producing action zależnie od aplikacji.
* `video_material`: dopuszczony jako przyszły `resource_type`, ale bez domkniętego kontraktu danych.

---

# Definition of Done Sprintu 0.3

Sprint 0.3 jest zakończony, gdy:

* istnieje `operations.md`,
* każda operacja ma kontrakt,
* wiadomo, jak operacja jest uruchamiana,
* wiadomo, kiedy operacja się kończy,
* wiadomo, co operacja produkuje,
* wiadomo, jakie ryzyko generuje,
* wiadomo, jakie operacje wspierające na nią wpływają,
* wiadomo, które elementy świata zmienia,
* rozbieżności z innymi dokumentami są wypisane w `TODO_DECISION`.
