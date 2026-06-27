# CHAOS — App Contract

Ten dokument opisuje kontrakt aplikacji w gameplayu CHAOS.

Aplikacja jest narzędziem gracza. Może mieć UI, kategorię, poziomy i efekty mechaniczne, ale uruchamianie z mapy powinno opierać się przede wszystkim na `app.map_actions`.

---

## Zasady główne

### `app.interface`

`app.interface` odpowiada tylko za sposób uruchomienia UI aplikacji.

Przykłady:

* `window`
* `terminal`
* `progressbar_random`
* `button_choices`
* `system_launcher`

To pole mówi desktopowi i launcherowi, jak pokazać aplikację.

Nie powinno decydować, czy aplikacja obsługuje akcję mapy.

---

### `app.map_actions`

`app.map_actions` jest głównym routerem uruchamiania aplikacji z mapy.

Przykład:

```json
{
  "map_actions": ["trace_gps", "trace_device"]
}
```

Jeśli gracz klika akcję mapy `trace_gps`, backend powinien szukać aplikacji, które mają `trace_gps` w `app.map_actions`.

---

### `app.detects`, `app.affects`, `app.interferes_with`

Te pola opisują mechanikę aplikacji:

* `app.detects` mówi, jakie dane aplikacja potrafi wykryć,
* `app.affects` mówi, jakie parametry lub stany aplikacja zmienia,
* `app.interferes_with` mówi, z czym aplikacja wchodzi w konflikt.

Nie powinny same decydować o starcie aplikacji z mapy.

Mogą wpływać na:

* jakość wyniku,
* kompletność zasobów,
* skuteczność operacji,
* konflikty zabezpieczeń,
* ryzyko wykrycia.

---

## Minimalny model aplikacji gameplayowej

| Pole | Znaczenie |
| --- | --- |
| `id` | stabilny identyfikator aplikacji |
| `name` | nazwa widoczna dla gracza |
| `interface` | sposób otwarcia UI |
| `type` | ogólny rodzaj aplikacji |
| `map_actions` | akcje mapy obsługiwane przez aplikację |
| `target_types` | typy celów, na których aplikacja może działać |
| `operation_types` | operacje, które aplikacja może uruchomić |
| `resource_types` | zasoby, które aplikacja może produkować |
| `tags` | tagi wyszukiwania i klasyfikacji |
| `detects` | dane wykrywane przez aplikację |
| `affects` | parametry zmieniane przez aplikację |
| `interferes_with` | zabezpieczenia lub systemy, z którymi aplikacja koliduje |

---

## Przykłady aplikacji

### GPS Tracker

```json
{
  "id": "gps_tracker",
  "name": "GPS Tracker",
  "interface": "progressbar_random",
  "map_actions": ["trace_gps"],
  "target_types": ["vehicle"],
  "operation_types": ["vehicle_tracking"],
  "resource_types": ["gps_logs", "location_history"]
}
```

### Camera Viewer

```json
{
  "id": "camera_viewer",
  "name": "Camera Viewer",
  "interface": "window",
  "map_actions": ["camera_stream"],
  "target_types": ["camera"],
  "operation_types": ["camera_stream"],
  "resource_types": ["camera_dump"]
}
```

### ATM Log Reader

```json
{
  "id": "atm_log_reader",
  "name": "ATM Log Reader",
  "interface": "terminal",
  "map_actions": ["atm_logs"],
  "target_types": ["atm"],
  "operation_types": ["atm_log_extraction"],
  "resource_types": ["atm_dump", "financial_records"]
}
```

### Mic Sniffer

```json
{
  "id": "mic_sniffer",
  "name": "Mic Sniffer",
  "interface": "progressbar_random",
  "map_actions": ["mic_sniff", "audio_hack"],
  "target_types": ["person", "venue"],
  "operation_types": ["microphone_sniffer"],
  "resource_types": ["audio_transcript"]
}
```

### Port Scanner

```json
{
  "id": "port_scanner",
  "name": "Port Scanner",
  "interface": "progressbar_random",
  "map_actions": ["scan_ports"],
  "target_types": ["poi", "camera", "atm", "player", "server", "router"],
  "operation_types": ["recon_scan"],
  "resource_types": ["internal_recon_state"]
}
```

Port Scanner obsługuje `scan_ports`, ale zgodnie z nowszym kontraktem `map_actions` / `operations` nie produkuje zasobów handlowych.

`internal_recon_state` oznacza wewnętrzny stan rozpoznania celu używany w procesie hackowania, a nie plik na sprzedaż.

### ECU Injector

```json
{
  "id": "ecu_injector",
  "name": "ECU Injector",
  "interface": "button_choices",
  "map_actions": ["car_hack"],
  "target_types": ["vehicle"],
  "operation_types": ["vehicle_ecu"],
  "resource_types": ["vehicle_diagnostics"]
}
```

---

## Routing z mapy

Docelowy flow:

```text
map_action_id
↓
znajdź aplikacje z app.map_actions zawierającym map_action_id
↓
brak aplikacji: komunikat systemowy
jedna aplikacja: automatyczny start
kilka aplikacji: wybór narzędzia
↓
uruchom app.interface
↓
aplikacja startuje operation_type albo wykonuje akcję natychmiastową
```

## Decyzje człowieka

* `operation_types` w aplikacji jest zawsze listą, nawet jeśli aplikacja uruchamia tylko jedną operację.
* Aplikacja może obsługiwać `map_action_id`, ale nie tworzyć operacji.
* Fallback po starych polach `detects` i `type` zostaje tylko jako migracja i docelowo znika po sprintach gameplayowych.

## TODO_DECISION

* Czy `internal_recon_state` zostaje nazwą stanu rozpoznania dla wszystkich scannerów, czy powstanie kilka typów stanów rozpoznania.
