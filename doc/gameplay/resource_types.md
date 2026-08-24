# CHAOS — Resource Types / Model Danych

Sprint 0.5 definiuje zasoby produkowane przez operacje i aplikacje.

`resource_type` opisuje gameplayową wartość danych, stanu albo materiału, który powstaje w wyniku działania aplikacji lub operacji.

Nie każdy zasób jest plikiem.
Nie każdy zasób trafia na rynek.
Nie każdy zasób jest widoczny dla gracza.

Przykład:

* `internal_recon_state` jest stanem procesu hackowania, nie lootem.
* `gps_logs` jest plikiem i może być sprzedawalny.
* `camera_stream` może produkować `camera_dump` albo `video_material`, ale tylko jeśli aplikacja tak deklaruje.

---

## Zasady główne

### `resource_type` nie jest `file_category`

`resource_type` mówi, co powstało z punktu widzenia gameplayu.

`file_category` mówi, gdzie i jak zasób ma być reprezentowany w systemie plików gracza.

Przykład:

* `gps_logs` to `resource_type`,
* `logs` albo `intel` może być `file_category`.

### `resource_type` nie jest `market_category`

`market_category` mówi, w jakim segmencie rynku zasób może być sprzedawany lub wyceniany.

Przykład:

* `financial_records` może mieć `market_category = financial`,
* `audio_transcript` może mieć `market_category = surveillance`,
* `internal_recon_state` nie ma rynku.

### Typy zachowania zasobów

Zasób może być:

| Typ zachowania | Znaczenie |
| --- | --- |
| `internal_state` | Stan techniczny procesu, zwykle niewidoczny jako plik. |
| `file_resource` | Zasób zapisany jako plik w profilu gracza. |
| `trade_resource` | Zasób, który można sprzedać albo wycenić na rynku. |
| `support_resource` | Zasób wspierający inną operację, np. rozpoznanie. |
| `evidence_resource` | Materiał dowodowy: logi, dumpy, nagrania, ślady. |

### Wartość zależy od kompletności

Ta sama operacja może produkować słabszą albo pełniejszą paczkę danych.

Lepsza aplikacja może:

* zebrać więcej pól,
* mieć większą kompletność,
* zmniejszyć ryzyko wykrycia,
* zebrać dane z dłuższego okresu,
* wzbogacić paczkę o metadane.

### Wpływ jakości aplikacji

Od Sprintu 23 aplikacja przekazuje do operacji snapshot:

```text
source_app_quality
```

Obejmuje on:

* `creator_power`,
* `quality_score`,
* `reliability`.

Zasada runtime:

* `quality_score` aplikacji może podnieść `quality_score` pliku,
* wyższa jakość może później zwiększać kompletność paczki,
* `reliability` jest przygotowane pod awarie i ryzyko, ale Sprint 23 nie robi
  jeszcze pełnego rebalance,
* niższa jakość nie usuwa danych, tylko daje słabszy wynik.

Decision:

* Przyjęto: pierwszym efektem jakości narzędzia jest wpływ na `file.quality_score`.
* Przyjęto: szczegółowe mnożniki kompletności zostają do dalszego balansu po playteście.

### Bazowa waga zasobu

Sprint 22 dodaje miękki model pojemności. `resource_type` może mieć bazową
wagę, z której runtime wyprowadza `file.file_size`.

Zasady:

* waga zasobu nie jest jego ceną,
* większy plik nie zawsze jest bardziej wartościowy,
* kompletność i jakość nadal są osobnymi polami,
* `internal_recon_state` może mieć wagę techniczną, ale nie tworzy pliku
  handlowego w `/data`.

Orientacyjne wagi runtime:

| resource_type | base file size |
| --- | ---: |
| `internal_recon_state` | 2 MB |
| `gps_logs` | 4 MB |
| `location_history` | 4 MB |
| `device_logs` | 8 MB |
| `personal_records` | 9 MB |
| `financial_records` | 12 MB |
| `credentials` | 7 MB |
| `email_accounts` | 7 MB |
| `call_history` | 9 MB |
| `messenger_data` | 9 MB |
| `audio_transcript` | 6 MB |
| `camera_dump` | 14 MB |
| `video_material` | 26 MB |
| `atm_dump` | 10 MB |
| `vehicle_diagnostics` | 7 MB |
| `wifi_networks` | 6 MB |
| `hotspot_database` | 8 MB |

Decision:

* Przyjęto: Sprint 22 używa bazowych wag jako miękkiego UI/balansu, nie jako
  twardej symulacji bajtów.

---

## Kategorie zasobów

### location

Dane położenia, trasy, checkpointów i historii lokalizacji.

Przykłady:

* `gps_logs`
* `location_history`

### device_intelligence

Dane o urządzeniach, aktywności użytkownika, aplikacjach, sygnałach i logach.

Przykłady:

* `device_logs`
* `personal_records`
* `call_history`
* `messenger_data`

### financial

Dane finansowe, dumpy bankomatów, rekordy transakcji i pochodne sygnały ekonomiczne.

Przykłady:

* `financial_records`
* `atm_dump`

### credentials

Dane dostępowe, konta, tokeny, sesje i identyfikatory autoryzacyjne.

Przykłady:

* `credentials`
* `email_accounts`

### surveillance

Materiały obserwacyjne i zrzuty z kamer.

Przykłady:

* `camera_dump`
* `video_material`

### audio

Dane audio, transkrypcje, podsłuchy i interpretacje rozmów.

Przykład:

* `audio_transcript`

### vehicle

Dane diagnostyczne pojazdów, ECU, stany systemów pokładowych i telemetria.

Przykład:

* `vehicle_diagnostics`

### network

Dane sieciowe, hotspoty, lista sieci, infrastruktura Wi-Fi i punkty dostępu.

Przykłady:

* `wifi_networks`
* `hotspot_database`

### internal

Stan techniczny procesu hackowania, niewystawiany jako loot.

Przykład:

* `internal_recon_state`

---

## Tabela resource_types

| resource_type | label | category | produced_by_operations | file_category | market_category | is_file | sellable | visible_to_player | completeness_fields | upgradeable_by_apps | base_value_hint | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `internal_recon_state` | Internal Recon State | internal | `scan_ports`, app-dependent `sniff` | none | none | no | no | optional | `ports_known`, `services_known`, `security_hints`, `expires_at` | yes | none | Stan procesu hackowania. Nie jest plikiem handlowym. |
| `gps_logs` | GPS Logs | location | `vehicle_tracking` | `logs` | `location` | yes | yes | yes | `checkpoint_count`, `duration`, `accuracy`, `route_confidence` | yes | medium | Logi śledzenia pojazdu. |
| `location_history` | Location History | location | `vehicle_tracking`, `device_tracking`, `generic_trace` | `intel` | `location` | yes | yes | yes | `checkpoint_count`, `time_span`, `accuracy`, `target_identity_confidence` | yes | medium | Uniwersalna historia położenia celu. |
| `device_logs` | Device Logs | device_intelligence | `device_tracking` | `logs` | `device_intel` | yes | yes | yes | `events_count`, `time_span`, `device_identity`, `signal_quality` | yes | medium | Logi urządzenia lub telefonu. |
| `personal_records` | Personal Records | device_intelligence | app-dependent `device_tracking`, app-dependent `sniff` | `intel` | `personal_data` | yes | yes | yes | `identity_fields`, `profile_depth`, `confidence`, `freshness` | yes | high | Dane osobowe zebrane przez wyspecjalizowane aplikacje. |
| `financial_records` | Financial Records | financial | `atm_log_extraction`, `persistent_sniffer`, app-dependent `sniff` | `finance` | `financial` | yes | yes | yes | `transactions_count`, `time_span`, `account_confidence`, `amount_visibility` | yes | high | Rekordy finansowe, nie bezpośredni przelew HC. |
| `credentials` | Credentials | credentials | `persistent_sniffer`, app-dependent `sniff` | `secrets` | `credentials` | yes | yes | yes | `credential_count`, `validity`, `scope`, `freshness` | yes | very_high | Dane dostępowe. Wymagają wysokiego ryzyka i mocnej kontroli ekonomii. |
| `email_accounts` | Email Accounts | credentials | app-dependent `sniff`, future player/system tools | `secrets` | `credentials` | yes | yes | yes | `account_count`, `domain_quality`, `access_validity`, `metadata_depth` | yes | high | Konta pocztowe jako zasób danych, nie prywatne wiadomości wprost. |
| `call_history` | Call History | device_intelligence | app-dependent `device_tracking`, `microphone_sniffer`, app-dependent `sniff` | `intel` | `personal_data` | yes | yes | yes | `call_count`, `time_span`, `contact_resolution`, `metadata_depth` | yes | medium | Historia połączeń i metadane rozmów. |
| `messenger_data` | Messenger Data | device_intelligence | app-dependent `sniff`, future player/system tools | `intel` | `personal_data` | yes | yes | yes | `thread_count`, `metadata_depth`, `identity_confidence`, `freshness` | yes | high | Dane komunikatorów jako paczka metadanych lub fragmentów, zależnie od aplikacji. |
| `audio_transcript` | Audio Transcript | audio | `microphone_sniffer`, `audio_interference` | `audio` | `surveillance` | yes | yes | yes | `duration`, `speaker_count`, `transcript_quality`, `keyword_hits` | yes | medium | Transkrypcja audio, może być materiałem dowodowym. |
| `camera_dump` | Camera Dump | surveillance | `camera_stream` | `media` | `surveillance` | yes | yes | yes | `duration`, `frame_quality`, `angle_quality`, `event_hits` | yes | medium | Zrzut/fragment materiału z kamery. |
| `video_material` | Video Material | surveillance | app-dependent `camera_stream` | `media` | `surveillance` | yes | yes | yes | `duration`, `resolution`, `event_hits`, `continuity` | yes | high | Rozwinięty materiał wideo. Przyszły zasób, ale dopuszczony w kontrakcie. |
| `atm_dump` | ATM Dump | financial | `atm_log_extraction` | `finance` | `financial` | yes | yes | yes | `record_count`, `time_span`, `account_confidence`, `terminal_identity` | yes | high | Dump z bankomatu lub terminala finansowego. |
| `vehicle_diagnostics` | Vehicle Diagnostics | vehicle | app-dependent `vehicle_ecu`, app-dependent `car_hack` | `vehicle` | `vehicle` | yes | yes | yes | `systems_count`, `fault_depth`, `ecu_access`, `telemetry_quality` | yes | medium | Nie powstaje domyślnie z `car_hack`; wymaga aplikacji z takim zasobem. |
| `wifi_networks` | WiFi Networks | network | `wifi_scanner` | `network` | `network` | yes | yes | yes | `network_count`, `security_types`, `signal_strength`, `geo_accuracy` | yes | low | Lista sieci Wi-Fi w lokacji. |
| `hotspot_database` | Hotspot Database | network | app-dependent `wifi_scanner`, future aggregation operations | `network` | `network` | yes | yes | yes | `hotspot_count`, `coverage_area`, `freshness`, `geo_accuracy` | yes | medium | Zagregowana baza hotspotów. Może wymagać wielu skanów. |

---

## Model kompletności paczki

Paczka danych nie musi być binarna: istnieje albo nie istnieje.

Każdy `resource_type` może mieć kompletność opisaną polami z kolumny `completeness_fields`.

Słabsza aplikacja może zebrać tylko część danych.

Lepsza aplikacja może zebrać:

* więcej rekordów,
* dłuższy zakres czasu,
* dokładniejsze współrzędne,
* większą pewność identyfikacji,
* lepszą jakość materiału,
* bardziej wartościowe metadane.

### Przykład: Device Intelligence

Pakiet Device Intelligence może składać się z wielu zasobów:

* `location_history`
* `device_logs`
* `personal_records`
* `financial_records`
* `credentials`
* `email_accounts`
* `call_history`
* `messenger_data`

Im więcej elementów i im większa kompletność każdego elementu, tym wyższa wartość pakietu.

Przyjęto:

* pojedynczy zasób ma własną wartość,
* zestaw powiązanych zasobów może tworzyć paczkę o wyższej wartości,
* paczka nie musi być osobnym `resource_type` w Sprincie 0.5,
* paczkowanie danych zostanie opisane w przyszłym modelu rynku lub plików.

---

## Zasada app-dependent resources

Jeżeli operacja ma `resource_types = app-dependent`, to konkretna aplikacja decyduje, które zasoby powstaną.

`map_action_id` opisuje intencję z mapy.

`app.map_actions` mówi, że aplikacja może obsłużyć intencję.

`operation_type` opisuje proces.

`resource_types` w kontrakcie aplikacji opisują, co faktycznie może zostać utworzone.

### Przykłady

#### camera_stream

`camera_stream` może produkować:

* `camera_dump`,
* `video_material`,
* albo nic, jeśli aplikacja daje tylko podgląd i nie zapisuje materiału.

#### car_hack

`car_hack` nie produkuje domyślnie `vehicle_diagnostics`.

`vehicle_diagnostics` powstaje tylko wtedy, gdy aplikacja ma ten `resource_type`.

#### sniff

`sniff` może:

* tylko odblokować warunek hackowania,
* utworzyć `internal_recon_state`,
* uruchomić `persistent_sniffer`,
* albo produkować dane takie jak `credentials`, `financial_records`, `device_logs`.

O wyniku decyduje aplikacja.

---

## Spójność z istniejącymi dokumentami

Sprawdzone względem:

* `doc/gameplay/operations.md`
* `doc/gameplay/map_actions.md`
* `doc/gameplay/app_contract.md`
* `doc/gameplay/gameplay_matrix.md`

### Ustalenia spójności

* `scan_ports` pozostaje stanem procesu i nie produkuje zasobów handlowych.
* `internal_recon_state` jest technicznym zasobem/stanem rozpoznania, nie plikiem i nie lootem.
* `camera_stream` może produkować `camera_dump` albo `video_material`, ale tylko zależnie od aplikacji.
* `car_hack` produkuje `vehicle_diagnostics` tylko przez aplikację, która deklaruje ten zasób.
* `sniff` jest app-dependent i może być support action, hack condition albo data-producing action.
* `video_material` zostaje dopuszczony jako pełnoprawny przyszły `resource_type`.

---

## TODO_DECISION

* Przyjęto: wartość bazowa zasobów będzie liczona później przez model rynku na podstawie `category`, `completeness_fields`, ryzyka operacji i świeżości danych. Sprint 0.5 zapisuje tylko orientacyjne `base_value_hint`.
* Przyjęto: `camera_dump` i `video_material` zostają osobnymi `resource_type`. `camera_dump` oznacza krótszy zrzut lub fragment, `video_material` oznacza bardziej kompletny materiał wideo.
* Przyjęto: `internal_recon_state` nie trafia do systemu plików. Jest zapisywany jako stan celu/procesu hackowania, z opcjonalnym podglądem dla gracza.
* Przyjęto: `credentials` pozostają osobnym zasobem, a nie częścią jednego `device_dump`, bo mają osobne ryzyko, wartość i konsekwencje gameplayowe.
* Przyjęto: `hotspot_database` jest sprzedawalny, ale wymaga lepszej aplikacji albo agregacji wielu `wifi_networks`.
* Przyjęto: `network_scan` z wcześniejszych dokumentów zostaje wycofany z podstawowego modelu Sprintu 0.5. Dla skanowania portów używamy `internal_recon_state`, a dla Wi-Fi używamy `wifi_networks` / `hotspot_database`.
* Przyjęto: jeżeli później powstanie `generic_sniffer`, będzie używał tego samego modelu app-dependent resources i nie dostanie osobnego domyślnego lootu.

---

## Sprint 26 — Scanner / Recon resources

Scanner / Recon może produkować zasoby tylko wtedy, gdy aplikacja deklaruje je
w `resource_types`.

Domyślne kierunki:

| Rodzina zasobów | `resource_types` | Uwagi |
| --- | --- | --- |
| Stan rozpoznania | `internal_recon_state` | Nie jest plikiem handlowym i nie trafia do Ghost Exchange. |
| Lokalizacja / śledzenie | `location_history`, `gps_logs`, `device_logs` | Powstaje przez operacje typu `generic_trace`, `vehicle_tracking`, `device_tracking`. |
| Sieć / hotspoty | `wifi_networks`, `hotspot_database` | `hotspot_database` wymaga lepszej aplikacji albo agregacji. |
| Surveillance / kamera | `camera_dump` | Tylko gdy scanner jawnie deklaruje `camera_stream` i zasób kamery. |

Zasady:

* desktop scanner może tworzyć tylko stan/profil celu bez `map_actions`,
* map scanner może być support-only i produkować tylko `internal_recon_state`,
* hybrydowy scanner może mieć pliki, ale tylko zgodnie z `resource_types`,
* Sprint 26 nie dodaje zasobów exploit/sniffer takich jak `credentials` jako
  domyślnego wyniku ścieżki Scanner / Recon.

---

## Sprint 27 — Exploit / Sniffer resources

Exploit i Sniffer mogą produkować pliki tylko zgodnie z jawnym
`resource_types` aplikacji.

Exploit:

| Operacja / efekt | Sensowne `resource_types` | Uwagi |
| --- | --- | --- |
| `camera_shutdown` | none / `internal_recon_state` | Support operation; nie produkuje loot files domyślnie. |
| `persistent_sniffer` | `credentials`, `financial_records`, `device_logs`, `internal_recon_state` | Jeśli exploit instaluje implant, zasób zależy od aplikacji. |
| `audio_interference` | `audio_transcript`, `internal_recon_state` | Tylko gdy aplikacja zapisuje efekt operacji. |
| `vehicle_ecu` | `vehicle_diagnostics`, `internal_recon_state` | Diagnostyka pojazdu powstaje tylko przy jawnym zasobie. |

Sniffer:

| Operacja / efekt | Sensowne `resource_types` | Uwagi |
| --- | --- | --- |
| `persistent_sniffer` | `credentials`, `financial_records`, `device_logs`, `internal_recon_state` | Długotrwały implant. |
| `microphone_sniffer` | `audio_transcript` | Podsłuch jako transkrypcja gameplayowa. |
| `atm_log_extraction` | `atm_dump`, `financial_records` | Wysokowartościowe dane finansowe. |
| `camera_stream` | `camera_dump`, `video_material` | Materiał kamery zależny od aplikacji. |

Decision:

* Przyjęto: Sprint 27 nie dodaje nowych `resource_type`; używa istniejących
  zasobów i jawnego kontraktu aplikacji.
* Przyjęto: `credentials` nie są częścią Scanner / Recon, ale mogą być wynikiem
  Sniffer albo Exploit, jeśli aplikacja to deklaruje.

## Sprint 28 — GhostLab pro-system-tool resources

GhostLab Publisher nie dodaje nowych `resource_type`.

Zasady:

* `pro-system-tool` dostaje `resource_types` z template,
* jeśli template nie produkuje danych, używa `internal_recon_state` jako
  informacyjnego zasobu technicznego,
* `operation_types` pozostaje puste, dopóki przyszły custom runtime nie zacznie
  tworzyć operacji,
* zasoby GhostLab nie omijają File Modelu ani Ghost Exchange.

Decision:

* Przyjęto: Sprint 28 normalizuje kontrakt zasobów GhostLab, ale nie dodaje
  nowych finalizerów i nie publikuje nowych typów danych.

---

## Definition of Done Sprintu 0.5

Sprint 0.5 jest zakończony, gdy:

* istnieje `resource_types.md`,
* każdy podstawowy `resource_type` ma kontrakt danych,
* wiadomo, które zasoby są plikami,
* wiadomo, które zasoby są sprzedawalne,
* wiadomo, które zasoby są tylko stanem technicznym,
* wiadomo, jak działa kompletność paczki,
* wiadomo, kiedy zasób jest app-dependent,
* rozbieżności z wcześniejszymi dokumentami mają przyjętą decyzję domyślną.
