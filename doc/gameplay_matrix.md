| Operacja        | Wymaga aplikacji | Tworzy aktywny obiekt | Generuje pliki | Trafia na giełdę | Ryzyko wykrycia  | Czas życia |
| --------------- | ---------------- | --------------------- | -------------- | ---------------- | ---------------- | ---------- |
| Trace GPS       | ✅                | ✅                     | GPS Logs       | ✅                | małe             | 2 h        |
| Trace Device    | ✅                | ✅                     | Device Logs    | ✅                | średnie          | 1 h        |
| Mic Sniff       | ✅                | ❌                     | Audio          | ✅                | duże             | 20 min     |
| ATM Sniffer     | ✅                | ✅                     | ATM Dump       | ✅                | średnie          | 3 h        |
| Camera Stream   | ✅                | ✅                     | Camera Dump / Video Material zależnie od aplikacji | ✅ / zależnie od aplikacji | małe             | 30 min     |
| Camera Shutdown | ✅                | ✅ (stan kamery)       | ❌              | ❌                | zmniejsza ryzyko | 15 min     |

---

# Kontrakt map_actions

Ta tabela jest kontraktową warstwą Sprintu 0. Nie zastępuje prostej tabeli powyżej, tylko doprecyzowuje pola, które będą później używane przez backend, mapę, aplikacje i operacje.

| map_action_id | label | target_types | requires_app | app_map_actions | starts_operation | operation_type | produces_resource_types | creates_active_object | sellable | risk_level | default_duration | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `trace_gps` | Trace GPS | `vehicle` | yes | `trace_gps` | yes | `vehicle_tracking` | `gps_logs`, `location_history` | yes | yes | low | 2 h | Śledzenie pojazdu. Docelowo pozycja odświeżana proceduralnie lub checkpointami. |
| `trace_device` | Trace Device | `person`, `phone`, `player` | yes | `trace_device` | yes | `device_tracking` | `device_logs`, `location_history` | yes | yes | medium | 1 h | Dla graczy wymaga osobnych zasad player target. |
| `mic_sniff` | Mic Sniff | `person`, `venue` | yes | `mic_sniff` | yes | `microphone_sniffer` | `audio_transcript` | no | yes | high | 20 min | Podsłuch produkuje transkrypcję, ale nie musi zostawiać aktywnego markera. |
| `atm_logs` | ATM Logs | `atm` | yes | `atm_logs` | yes | `atm_log_extraction` | `atm_dump`, `financial_records` | no | yes | medium | 10 min | Krótka operacja odczytu logów; osobny sniffer ATM to `install_sniffer`. |
| `install_sniffer` | Install Sniffer | `atm`, `router`, `server` | yes | `install_sniffer` | yes | `persistent_sniffer` | `financial_records`, `network_scan` | yes | yes | medium | 3 h | Aktywny obiekt zbierający dane przez czas życia operacji. |
| `camera_stream` | Camera Stream | `camera` | yes | `camera_stream` | yes | `camera_stream` | app-dependent: `camera_dump`, `video_material` | yes | app-dependent | low | 30 min | Aktywna operacja streamu. Na mapie powinna pokazywać licznik czasu nagrania, np. `01:35:34`, odświeżany przy refreshu mapy. Materiał powstaje zależnie od aplikacji. |
| `camera_shutdown` | Camera Shutdown | `camera` | yes | `camera_shutdown` | yes | `camera_shutdown` | none | yes | no | support | 15 min | Operacja wspierająca. Zmniejsza ryzyko innych działań w obszarze. |
| `car_hack` | Car Hack | `vehicle` | yes | `car_hack` | app-dependent | `vehicle_ecu` | app-dependent | app-dependent | app-dependent | high | app-dependent | Narzędzie decyduje o możliwej akcji i wyniku. `car_hack` nie produkuje domyślnie `vehicle_diagnostics`; robi to dopiero aplikacja, która ma taką funkcję. |
| `scan_ports` | Scan Ports | `poi`, `camera`, `atm`, `server`, `router`, `player`, `pillar` | yes | `scan_ports` | no | none | none | no | no | low | instant | Element procesu hackowania. Nie produkuje plików handlowych. Generuje sygnał aktywności na mapie i może zwiększać ryzyko wykrycia. |
| `exploit` | Exploit | `poi`, `camera`, `atm`, `server`, `router`, `player`, `pillar` | yes | `exploit` | no | none | none | no | no | high | instant | Akcja przełamania zabezpieczeń. Po sukcesie zmienia stan celu. |
| `sniff` | Sniff | `poi`, `server`, `router`, `player`, `pillar` | yes | `sniff` | app-dependent | app-dependent | app-dependent | optional | app-dependent | medium | app-dependent | Bazowa akcja procesu hackowania. Może tylko odblokować warunek hackowania albo produkować zasoby, zależnie od aplikacji. Przy wielu snifferach gracz wybiera narzędzie. |
| `trace` | Trace | `poi`, `person`, `phone`, `player`, `vehicle`, `pillar` | yes | `trace` | yes | `generic_trace` | `location_history` | yes | yes | medium | 1 h | Ogólne śledzenie, używane jako fallback dla mniej wyspecjalizowanych celów. |

## Decyzje doprecyzowane

* `scan_ports` nie produkuje zasobów handlowych i nie tworzy plików na sprzedaż. Jest elementem procesu hackowania, generuje sygnał aktywności na mapie, może zwiększać ryzyko wykrycia i jest warunkiem rozpoznania celu.
* `camera_stream` jest aktywną operacją widoczną przy obiekcie. Stream powinien mieć licznik czasu nagrania, np. `01:35:34`, odświeżany przy refreshu mapy. Produkcja `camera_dump` lub materiału wideo zależy od aplikacji.
* `car_hack` nie produkuje domyślnie `vehicle_diagnostics`. O wyniku decyduje konkretna aplikacja i jej kontrakt.
* `sniff` zostaje jako bazowa akcja procesu hackowania. Może być support action albo data-producing action, zależnie od aplikacji.
* Tool selection wybiera aplikacje po `app.map_actions`. Pola `type`,
  `detects`, `affects` i `interferes_with` są tylko fallbackiem migracyjnym.
* `scan_ports` powinno pokazywać scanner/recon tools. `exploit_suite` nie jest
  scannerem tylko dlatego, że wykrywa `open_ports` albo `weak_configs`.
* `map_actions_source: migration_inferred` i `legacy_inferred` są stanami
  przejściowymi. Jawny kontrakt aplikacji jest źródłem prawdy.
* Scanner / Recon po Sprincie 26 jest rodziną narzędzi. Może być mapowy,
  desktopowy na `aimed_target` albo hybrydowy.
* Desktop scanner może nie mieć `map_actions`, ale powinien mieć sensowne
  `target_types`, `operation_types` i `resource_types`.
* Scanner mapowy/hybrydowy może tworzyć operację tylko wtedy, gdy deklaruje
  odpowiedni `operation_type`; `scan_ports` samo w sobie pozostaje support /
  recon state.
* Exploit / Sniffer po Sprincie 27 są rodzinami kreatora. Korzystają z
  istniejących `map_actions`, `operation_types` i `resource_types`.
* Desktop Exploit/Sniffer może nie mieć `map_actions`, ale nie może dostać ich
  przez fallback legacy; musi mieć jawny kontrakt celu, operacji i zasobów.
* `install_sniffer` jest świadomie hybrydowe: może być wybierane przez ścieżkę
  Exploit albo Sniffer, zależnie od intencji aplikacji.
* GhostLab po Sprincie 28 publikuje `pro-system-tool` jako zwykły rekord
  Googleplex z pełnym kontraktem aplikacji.
* GhostLab `pro-system-tool` domyślnie działa w trybie desktop na `player`
  przez Player Hack Access i nie dodaje nowych `map_actions` ani
  `operation_types` bez osobnego runtime.

## TODO_DECISION

* `video_material` jest przyszłym `resource_type`, ale jego kontrakt zostanie doprecyzowany w Sprincie 0.5 / Model Danych.
* `generic_sniffer` nie jest obowiązkowym kontraktem teraz. Jeśli będzie potrzebny, wraca jako TODO_FUTURE.
## Tool Laboratory v1 lifecycle

Sprint 30 domyka lifecycle aplikacji bez dodawania nowych `map_action_id`.

```text
creator / GhostLab
↓
publish to json_resources.app_config
↓
Googleplex install
↓
profile.apps + files.tools
↓
tool selection / desktop runtime
↓
uninstall
↓
profile cleanup + storage recalculation
```

Decision:

* Przyjęto: Tool Laboratory v1 nie zmienia map action matrix. Zamyka cykl
  aplikacji wokół istniejących `map_actions`, `operation_types` i
  `resource_types`.
