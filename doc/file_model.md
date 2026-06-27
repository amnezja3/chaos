# CHAOS — File Model / System plików jako gameplay inventory

Sprint 0.6 definiuje system plików jako inventory danych gracza.

System plików nie jest dekoracją pulpitu. To miejsce, w którym gracz widzi narzędzia, dane, loot, projekty, stan rynku i artefakty operacji.

Plik może reprezentować:

* paczkę danych,
* log,
* dump,
* transkrypcję,
* materiał z kamery,
* stan operacji zapisany dla gracza,
* aplikację albo narzędzie w katalogu `/tools`.

Nie każdy `resource_type` tworzy plik.
Nie każdy plik jest sprzedawalny.
Nie każdy plik znika po sprzedaży.

---

## Zasady główne

### `file_category` nie jest `resource_type`

`resource_type` opisuje gameplayową wartość danych.

`file_category` opisuje miejsce i sposób prezentacji pliku w systemie plików.

Przykład:

* `gps_logs` to `resource_type`,
* `gps` to `file_category`,
* `/data/gps` to katalog.

### Plik jest widoczną reprezentacją zasobu

Jeżeli zasób jest widoczny dla gracza i ma zostać użyty, sprzedany albo przechowany, powinien mieć plik.

Plik może zawierać:

* jeden `resource_type`,
* kilka powiązanych `resource_types`,
* metadane kompletności,
* pochodzenie operacji,
* status sprzedaży,
* podgląd treści.

### Zasób może nie mieć pliku

Zasoby techniczne mogą istnieć tylko jako stan procesu.

Przykład:

* `internal_recon_state` nie trafia do `/data`.
* Jest stanem hackowania celu.
* Może być pokazany graczowi jako status rozpoznania, ale nie jako loot.

### Plik może zawierać wiele `resource_types`

Jedna operacja albo aplikacja może utworzyć paczkę danych.

Przykład Device Intelligence:

* `location_history`,
* `device_logs`,
* `call_history`,
* `messenger_data`.

Taka paczka może być jednym plikiem w `/data/device`, jeśli pochodzi z tej samej operacji i celu.

### `/tools` jest katalogiem aplikacji i narzędzi

`/tools` nie jest lootem.

To katalog zainstalowanych aplikacji, narzędzi mapy, pro-system-tools i creatorów.

Pliki w `/tools`:

* mogą być uruchamiane,
* mogą być podświetlane jako pasujące do `map_action_id`,
* mogą być usuwane lub instalowane przez mechanikę Googleplex,
* nie są sprzedawane jako dane z operacji.

### Katalogi danych są częścią ekonomii gry

Katalogi `/data/*` są głównym inventory danych.

Pliki z tych katalogów mogą:

* być analizowane,
* być grupowane,
* być sprzedawane,
* być oznaczone jako `sold`,
* znikać po sprzedaży,
* tworzyć historię operacji gracza.

---

## Struktura katalogów

| Directory | Rola |
| --- | --- |
| `/tools` | Aplikacje, narzędzia mapy, pro-system-tools, creatory. |
| `/data/gps` | Logi GPS i historie lokalizacji. |
| `/data/device` | Dane urządzeń, telefony, metadane aktywności. |
| `/data/audio` | Transkrypcje i materiały audio. |
| `/data/camera` | Dumpy kamer i materiały wideo. |
| `/data/atm` | Dumpy ATM i dane terminali finansowych. |
| `/data/credentials` | Dane dostępowe, konta, tokeny, sesje. |
| `/data/financial` | Rekordy finansowe i paczki finansowe. |
| `/data/personal` | Dane osobowe, call history, messenger data. |
| `/data/network` | Wi-Fi, hotspoty, sieci, infrastruktura. |
| `/data/vehicle` | Diagnostyka pojazdów i dane ECU. |
| `/system` | Pliki systemowe, statusy, logi własne gracza. |
| `/market` | Pliki przygotowane do sprzedaży, oferty, statusy sold. |
| `/projects` | Projekty AppForge, GhostLab i inne warsztaty. |

Decision:

* Przyjęto: katalogi danych zaczynają się od `/data/*`, żeby odróżnić loot i zasoby od aplikacji, projektów i plików systemowych.
* Przyjęto: `/market` nie jest miejscem tworzenia zasobu, tylko stagingiem/ofertą sprzedaży.
* Przyjęto: `/projects` zostaje wspólnym korzeniem projektów, ale konkretne narzędzia mogą mieć własne podstruktury, np. `files.pro_system_projects`.

---

## Tabela file_categories

| file_category | directory | resource_types | visible_to_player | can_delete | can_sell | removed_after_sale | preview_mode | grouping_strategy | produced_by_operations | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `tools` | `/tools` | none/app definitions | yes | yes | no | no | `app_shortcut` | by app type / map action | Googleplex install, creator publish | Aplikacje i narzędzia. Nie są lootem danych. |
| `gps` | `/data/gps` | `gps_logs`, `location_history` | yes | yes | yes | yes | `table` | by target + operation | `vehicle_tracking`, `generic_trace` | Trasy, checkpointy, historia lokalizacji. |
| `device` | `/data/device` | `device_logs`, `location_history`, `call_history`, `messenger_data` | yes | yes | yes | yes | `card` | by target device/person | `device_tracking`, app-dependent `sniff` | Paczki Device Intelligence. |
| `audio` | `/data/audio` | `audio_transcript` | yes | yes | yes | yes | `transcript` | by target + recording | `microphone_sniffer`, `audio_interference` | Podsłuchy i transkrypcje. |
| `camera` | `/data/camera` | `camera_dump`, `video_material` | yes | yes | yes | yes | `media_placeholder` | by camera + time window | `camera_stream` | Materiał z kamer. |
| `atm` | `/data/atm` | `atm_dump`, `financial_records` | yes | yes | yes | yes | `table` | by atm + operation | `atm_log_extraction` | Dumpy ATM. |
| `credentials` | `/data/credentials` | `credentials`, `email_accounts` | yes | yes | yes | yes | `encrypted_blob` | by target + scope | `persistent_sniffer`, app-dependent `sniff` | Wysokowartościowe dane dostępowe. |
| `financial` | `/data/financial` | `financial_records`, `atm_dump` | yes | yes | yes | yes | `table` | by account/source | `atm_log_extraction`, `persistent_sniffer` | Dane finansowe. |
| `personal` | `/data/personal` | `personal_records`, `call_history`, `messenger_data`, `email_accounts` | yes | yes | yes | yes | `card` | by identity/person | app-dependent `device_tracking`, app-dependent `sniff` | Dane osobowe i społeczne. |
| `network` | `/data/network` | `wifi_networks`, `hotspot_database` | yes | yes | yes | yes | `table` | by location/coverage | `wifi_scanner`, future aggregation | Sieci i hotspoty. |
| `vehicle` | `/data/vehicle` | `vehicle_diagnostics` | yes | yes | yes | yes | `table` | by vehicle | `vehicle_ecu` | Diagnostyka i ECU. |
| `system` | `/system` | `internal_recon_state`, system logs | yes/optional | no | no | no | `operation_state` | by target/process | `scan_ports`, support actions | Statusy i ślady techniczne. |
| `market` | `/market` | sellable resources | yes | yes | yes | status-dependent | `card` | by offer/status | market flow | Staging rynku, nie źródło danych. |
| `projects` | `/projects` | project files | yes | yes | no | no | `card` | by workspace/tool | AppForge, GhostLab | Projekty nie są lootem danych. |

---

## Tabela resource_to_file_mapping

| resource_type | default_file_category | default_directory | creates_file | can_be_grouped | can_be_sold | default_filename_pattern | preview_mode | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `internal_recon_state` | `system` | `/system` | no | no | no | none | `operation_state` | Stan celu/procesu, nie plik handlowy. |
| `gps_logs` | `gps` | `/data/gps` | yes | yes | yes | `gps_{target}_{timestamp}.log` | `table` | Logi GPS z checkpointami. |
| `location_history` | `gps` | `/data/gps` | yes | yes | yes | `location_{target}_{timestamp}.dat` | `table` | Może też wejść do paczki `device`. |
| `device_logs` | `device` | `/data/device` | yes | yes | yes | `device_{target}_{timestamp}.log` | `card` | Dane aktywności urządzenia. |
| `personal_records` | `personal` | `/data/personal` | yes | yes | yes | `personal_{target}_{timestamp}.dat` | `card` | Dane osobowe. |
| `financial_records` | `financial` | `/data/financial` | yes | yes | yes | `finance_{source}_{timestamp}.dat` | `table` | Dane finansowe, nie HC. |
| `credentials` | `credentials` | `/data/credentials` | yes | yes | yes | `credentials_{target}_{timestamp}.enc` | `encrypted_blob` | Wysokie ryzyko i wartość. |
| `email_accounts` | `credentials` | `/data/credentials` | yes | yes | yes | `email_accounts_{target}_{timestamp}.enc` | `encrypted_blob` | Konta, tokeny i metadane dostępu. |
| `call_history` | `personal` | `/data/personal` | yes | yes | yes | `calls_{target}_{timestamp}.dat` | `table` | Historia połączeń. |
| `messenger_data` | `personal` | `/data/personal` | yes | yes | yes | `messenger_{target}_{timestamp}.dat` | `card` | Dane komunikatorów i metadane. |
| `audio_transcript` | `audio` | `/data/audio` | yes | yes | yes | `audio_{target}_{timestamp}.txt` | `transcript` | Transkrypcja audio. |
| `camera_dump` | `camera` | `/data/camera` | yes | yes | yes | `camera_dump_{target}_{timestamp}.cam` | `media_placeholder` | Krótki dump/fragment kamery. |
| `video_material` | `camera` | `/data/camera` | yes | yes | yes | `video_{target}_{timestamp}.vid` | `media_placeholder` | Bardziej kompletny materiał wideo. |
| `atm_dump` | `atm` | `/data/atm` | yes | yes | yes | `atm_{target}_{timestamp}.dump` | `table` | Dump bankomatu. |
| `vehicle_diagnostics` | `vehicle` | `/data/vehicle` | yes | yes | yes | `vehicle_{target}_{timestamp}.diag` | `table` | Diagnostyka pojazdu. |
| `wifi_networks` | `network` | `/data/network` | yes | yes | yes | `wifi_{location}_{timestamp}.net` | `table` | Lista sieci z lokacji. |
| `hotspot_database` | `network` | `/data/network` | yes | yes | yes | `hotspots_{area}_{timestamp}.db` | `table` | Agregacja hotspotów i coverage. |

Decision:

* Przyjęto: `location_history` domyślnie trafia do `/data/gps`, ale może być zgrupowane z `device_logs` w paczce `/data/device`, jeśli pochodzi z operacji `device_tracking`.
* Przyjęto: pliki handlowe domyślnie znikają po sprzedaży, a historia sprzedaży trafia do `/market` albo logu transakcji.
* Przyjęto: zasoby o wysokim ryzyku (`credentials`, `email_accounts`) używają `encrypted_blob` jako preview, nawet jeśli gracz ma dostęp do podstawowych metadanych.

---

## Preview modes

### `text_log`

Podgląd liniowy.

Pasuje do:

* prostych logów,
* systemowych wpisów,
* krótkich raportów.

### `table`

Podgląd tabelaryczny.

Pasuje do:

* tras,
* checkpointów,
* transakcji,
* sieci,
* rekordów finansowych,
* diagnostyki.

### `card`

Podgląd paczki jako karta danych.

Pasuje do:

* danych osobowych,
* urządzeń,
* paczek intelligence,
* ofert rynku.

### `transcript`

Podgląd rozmowy/transkrypcji.

Pasuje do:

* `audio_transcript`,
* fragmentów podsłuchu.

### `media_placeholder`

Podgląd materiału bez ciężkiego renderowania realnego wideo.

Pasuje do:

* `camera_dump`,
* `video_material`.

### `encrypted_blob`

Podgląd zaszyfrowanej lub wrażliwej paczki.

Pokazuje:

* typ,
* poziom wartości,
* kompletność,
* ryzyko,
* zakres danych,

ale nie pokazuje pełnej zawartości bez odpowiedniego UI/narzędzia.

### `app_shortcut`

Podgląd aplikacji lub narzędzia.

Pasuje do:

* `/tools`,
* launcherów,
* pro-system-tools,
* creatorów.

### `operation_state`

Podgląd stanu procesu.

Pasuje do:

* `internal_recon_state`,
* aktywnych operacji,
* stanów support.

---

## Tools jako wybór aplikacji

Jeżeli wiele aplikacji pasuje do jednej `map_action_id`, system powinien:

1. Otworzyć File Manager w `/tools`.
2. Podświetlić pasujące aplikacje.
3. Pokazać, które narzędzia obsługują daną akcję mapy przez `app.map_actions`.
4. Pozwolić graczowi kliknąć wybrane narzędzie.
5. Pozwolić graczowi wpisać nazwę aplikacji w terminalu.

Decision:

* Przyjęto: podświetlenie narzędzi w `/tools` używa `app.map_actions` jako podstawowego filtra.
* Przyjęto: terminal docelowo powinien obsługiwać dokładną nazwę i kontrolowane aliasy, ale aliasy muszą być częścią kontraktu aplikacji, nie zgadywaniem po fuzzy search.
* Przyjęto: jeśli gracz nie ma żadnej aplikacji dla `map_action_id`, system pokazuje jasny komunikat: `Brak aplikacji obsługującej tę akcję`.

---

## Sprzedaż plików

Pliki handlowe mogą trafić do Ghost Exchange albo innego rynku danych.

Sprzedaż pliku powinna:

* sprawdzić, czy plik jest sprzedawalny,
* sprawdzić, czy plik nie został już sprzedany,
* wyliczyć wartość na podstawie kompletności,
* przelać HC do gracza,
* wygenerować mail lub system message,
* usunąć plik albo oznaczyć go jako `sold`.

Decision:

* Przyjęto: domyślnie plik handlowy po sprzedaży zostaje usunięty z katalogu danych i pojawia się jako wpis historii w `/market`.
* Przyjęto: jeśli projekt gry później będzie wymagał wielokrotnej sprzedaży kopii, będzie to osobna mechanika licencji/dystrybucji, nie domyślna sprzedaż lootu.
* Przyjęto: szczegółowy pricing, popyt i kategorie rynku należą do Sprintu 0.7 / Market Model.

---

## Spójność z istniejącymi dokumentami

Sprawdzone względem:

* `doc/resource_types.md`
* `doc/operations.md`
* `doc/app_contract.md`
* `doc/map_actions.md`
* `doc/gameplay_matrix.md`

### Ustalenia spójności

* `resource_types.md` pozostaje źródłem prawdy dla tego, czy zasób jest plikiem i czy jest sprzedawalny.
* `file_model.md` doprecyzowuje, gdzie taki plik trafia i jak jest widoczny.
* `internal_recon_state` nie tworzy pliku w `/data`.
* `/tools` jest inventory aplikacji, a nie kategorią danych handlowych.
* `camera_dump` i `video_material` trafiają do `/data/camera`.
* `network_scan` nie jest używany w podstawowym file modelu Sprintu 0.6.

---

## Decision

* Przyjęto: `file_category = logs` z wcześniejszych dokumentów zostaje rozbite na bardziej gameplayowe kategorie: `gps`, `device`, `system`.
* Przyjęto: `file_category = intel` z wcześniejszych dokumentów zostaje rozbite na `device`, `personal`, `gps`, zależnie od `resource_type`.
* Przyjęto: `file_category = finance` z wcześniejszych dokumentów mapuje się na `financial` lub `atm`; `financial` jest kategorią danych, `atm` jest kategorią źródła dumpa.
* Przyjęto: `file_category = media` z wcześniejszych dokumentów mapuje się na `camera`.
* Przyjęto: `file_category = secrets` z wcześniejszych dokumentów mapuje się na `credentials`.
* Przyjęto: project files nie są sprzedawalnymi resource files. Publikacja projektów będzie osobnym flow creatorów/GhostLab.

---

## TODO_DECISION

* Rekomendacja: w Sprincie 0.7 zdecydować, czy Ghost Exchange jest jedynym rynkiem danych, czy istnieją też frakcyjne rynki prywatne.
* Rekomendacja: w Sprincie 0.7 zdecydować, czy sprzedaż usuwa dane bezpowrotnie, czy zostawia niehandlowy archived copy dla historii gracza. Domyślnie w Sprincie 0.6 plik znika z `/data` i zostaje wpis w `/market`.
* Rekomendacja: w przyszłym kontrakcie backendu zdecydować, czy pliki są osobną tabelą, czy częścią profilu użytkownika. To wpływa na architekturę backendu i migracje.

---

## Definition of Done Sprintu 0.6

Sprint 0.6 jest zakończony, gdy:

* istnieje `file_model.md`,
* wiadomo, czym różni się `resource_type` od `file_category`,
* wiadomo, które katalogi tworzą gameplay inventory,
* wiadomo, które zasoby tworzą pliki,
* wiadomo, które pliki są sprzedawalne,
* wiadomo, jak działa podgląd plików,
* wiadomo, jak `/tools` służy do wyboru aplikacji,
* wiadomo, jak sprzedaż plików łączy się z przyszłym Market Modelem.
