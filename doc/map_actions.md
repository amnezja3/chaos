# CHAOS — Map Actions

Ten dokument opisuje akcje wykonywane z poziomu mapy.

`map_action_id` opisuje intencję gracza na mapie.

`app.map_actions` mówi, że aplikacja może obsłużyć tę intencję.

`operation_type` i `resource_types` określają dalszy efekt, ale efekt zależy od kontraktu konkretnej aplikacji.

---

## Zasada ogólna

To aplikacja i jej kontrakt decydują, czy dana akcja:

* produkuje pliki,
* tworzy aktywną operację,
* tworzy dane handlowe,
* tylko spełnia warunek hackowania,
* tylko zmienia stan celu.

Menu mapy nie powinno zakładać efektu końcowego wyłącznie po `map_action_id`.

---

## Klasyfikacja narzędzi mapy

Tool selection używa `app.map_actions` jako głównego routera. Pola legacy
takie jak `type`, `detects`, `affects` i `interferes_with` mogą pomagać tylko
w migracji starych aplikacji.

Zasady po Sprincie 24:

* jawny kontrakt aplikacji wygrywa z inferencją legacy,
* `map_actions_source: migration_inferred` jest oznaczeniem wymagającym review,
* `map_actions_source: legacy_inferred` jest runtime fallbackiem dla starych
  aplikacji,
* fallback legacy można wyłączyć w dev/test przez
  `CHAOS_LEGACY_MAP_ACTION_FALLBACK=false`,
* `scan_ports` pokazuje narzędzia scanner/recon,
* `exploit` pokazuje exploity i exploit suites,
* `sniff` pokazuje sniffery i narzędzia czytające ruch,
* `trace_gps` pokazuje trackery GPS,
* `exploit_suite` nie powinno być pokazywane przy `scan_ports`, jeśli ta akcja
  pochodzi tylko z migracji albo domysłu.

Decision:

* Przyjęto: PenCombo / `exploit_suite` nie jest scannerem dla `scan_ports`.
* Przyjęto: hybrydowe narzędzie może obsługiwać `scan_ports` i `exploit` tylko
  wtedy, gdy ma jawne `map_actions` bez źródła legacy.

### Scanner / Recon actions po Sprincie 26

Scanner / Recon nie jest równy `scan_ports`. Kreator scannerów może proponować
różne akcje rozpoznania, zależnie od trybu:

| Tryb | Sensowne akcje mapy | Uwaga |
| --- | --- | --- |
| Scanner mapowy | `scan_ports`, `trace`, `trace_gps`, `trace_device`, `scan_hotspots`, `camera_stream` | Działa z menu mapy i wymaga jawnego `app.map_actions`. |
| Scanner desktopowy | brak wymaganych `map_actions` | Działa na aktualny `aimed_target`; nie powinien dostać akcji z fallbacku legacy. |
| Scanner hybrydowy | jak scanner mapowy, ale z możliwością działania z desktopu | Nadal używa jawnych `map_actions`, jeśli ma być widoczny na mapie. |

Zasady:

* `scan_ports` pozostaje rozpoznaniem procesu, nie lootem danych,
* `trace` / `trace_gps` / `trace_device` mogą tworzyć operacje śledzenia,
* `scan_hotspots` może tworzyć `wifi_scanner`,
* `camera_stream` może być użyte jako recon/surveillance tylko wtedy, gdy
  aplikacja jawnie deklaruje ten kontrakt,
* `exploit`, `sniff` i `install_sniffer` należą do kolejnej ścieżki kreatora,
  nie do podstawowego Scanner / Recon Path.

### Exploit / Sniffer actions po Sprincie 27

Exploit i Sniffer są osobnymi rodzinami kreatora. Nie powinny wracać do
scannerów przez fallback migracyjny.

| Rodzina | Sensowne akcje mapy | Uwagi |
| --- | --- | --- |
| Exploit | `exploit`, `camera_shutdown`, `install_sniffer`, `audio_hack`, `car_hack` | Symulowany wpływ na cel, support operation albo operacja produkująca dane zależnie od kontraktu. |
| Sniffer | `sniff`, `mic_sniff`, `atm_logs`, `install_sniffer`, `camera_stream` | Obserwacja, podsłuch, implant albo zbieranie danych przez operację gry. |

Tryb desktopowy:

* może mieć puste `map_actions`,
* działa na aktualny `aimed_target`,
* nadal powinien mieć jawne `target_types`, `operation_types` i
  `resource_types`,
* nie powinien dostawać akcji z `type/detects`.

Decision:

* Przyjęto: `install_sniffer` może pojawić się w rodzinie Exploit i Sniffer,
  bo gameplayowo jest hybrydą wpływu na cel i późniejszej obserwacji.
* Przyjęto: `camera_stream` w rodzinie Sniffer oznacza obserwację/surveillance,
  nie exploit.

---

## Tabela map_actions

| map_action_id | label | menu_group | target_types | requires_app | default_operation_type | default_resource_types | active_operation | trade_resources | risk_signal | notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `scan_ports` | Scan Ports | generic | `poi`, `camera`, `atm`, `server`, `router`, `player`, `pillar` | yes | none | none | no | no | yes | Element procesu hackowania. Warunek rozpoznania i dalszego hackowania celu. Nie produkuje plików handlowych. |
| `exploit` | Exploit | generic | `poi`, `camera`, `atm`, `server`, `router`, `player`, `pillar` | yes | none | none | no | no | yes | Akcja przełamania zabezpieczeń. Po sukcesie zmienia stan celu. |
| `sniff` | Sniff | generic | `poi`, `server`, `router`, `player`, `pillar` | yes | app-dependent | app-dependent | optional | app-dependent | yes | Bazowa akcja procesu hackowania. Może tylko odblokować warunek albo zbierać zasoby, zależnie od aplikacji. |
| `trace` | Trace | generic | `poi`, `person`, `phone`, `player`, `vehicle`, `pillar` | yes | `generic_trace` | `location_history` | yes | yes | yes | Ogólne śledzenie celu, fallback dla mniej wyspecjalizowanych akcji. |
| `trace_gps` | Trace GPS | vehicle | `vehicle` | yes | `vehicle_tracking` | `gps_logs`, `location_history` | yes | yes | yes | Śledzenie pojazdu. |
| `trace_device` | Trace Device | person | `person`, `phone`, `player` | yes | `device_tracking` | `device_logs`, `location_history` | yes | yes | yes | Śledzenie urządzenia lub gracza. Dla graczy obowiązują zasady player target. |
| `mic_sniff` | Mic Sniff | person | `person`, `venue` | yes | `microphone_sniffer` | `audio_transcript` | app-dependent | yes | yes | Podsłuch rozmów lub mikrofonów. |
| `camera_stream` | Camera Stream | camera | `camera` | yes | `camera_stream` | app-dependent: `camera_dump`, `video_material` | yes | app-dependent | yes | Aktywny stream kamery z licznikiem czasu nagrania przy obiekcie. |
| `camera_shutdown` | Camera Shutdown | camera | `camera` | yes | `camera_shutdown` | none | yes | no | support | Operacja wspierająca. Zmniejsza ryzyko innych działań. |
| `atm_logs` | ATM Logs | atm | `atm` | yes | `atm_log_extraction` | `atm_dump`, `financial_records` | no | yes | yes | Krótki odczyt danych finansowych z bankomatu. |
| `install_sniffer` | Install Sniffer | atm | `atm`, `router`, `server` | yes | `persistent_sniffer` | app-dependent | yes | app-dependent | yes | Instalacja aktywnego sniffera na obiekcie. |
| `scan_hotspots` | Scan Hotspots | venue | `venue` | yes | `wifi_scanner` | `wifi_networks` | optional | yes | yes | Skanowanie sieci w lokacji. |
| `audio_hack` | Audio Hack | venue | `venue` | yes | `audio_interference` | app-dependent | app-dependent | app-dependent | yes | Akcja audio dla lokacji. Może wspierać podsłuch albo produkować transkrypcję zależnie od aplikacji. |
| `car_hack` | Car Hack | vehicle | `vehicle` | yes | app-dependent | app-dependent | app-dependent | app-dependent | yes | Narzędzie decyduje o wyniku. Brak odpowiedniego narzędzia oznacza komunikat systemowy. |

---

## Decyzje człowieka

### scan_ports

`scan_ports`:

* nie produkuje zasobów handlowych,
* nie tworzy plików na sprzedaż,
* jest elementem procesu hackowania obiektów na mapie,
* generuje sygnał aktywności na mapie,
* może zwiększać ryzyko wykrycia i konsekwencje,
* jest warunkiem rozpoznania lub dalszego hackowania celu.

### camera_stream

`camera_stream`:

* jest aktywną operacją na czas działania,
* jest widoczny jako aktywna kamera / aktywny stream,
* powinien mieć licznik czasu nagrania, np. `01:35:34`,
* licznik może odświeżać się przy refreshu mapy, np. co 10 sekund,
* może produkować `camera_dump` lub materiał wideo, zależnie od aplikacji.

### car_hack

`car_hack`:

* nie produkuje domyślnie `vehicle_diagnostics`,
* nie zakłada jednego domyślnego wyniku,
* zależy od konkretnego narzędzia,
* przy braku odpowiedniego narzędzia zwraca komunikat systemowy,
* może produkować dane pojazdu dopiero wtedy, gdy aplikacja ma taką funkcję.

### sniff

`sniff`:

* zostaje jako bazowa akcja procesu hackowania,
* jest warunkiem hackowania podobnie jak scanery, trackery i exploity,
* przy wielu snifferach system powinien pokazać lub podświetlić pasujące narzędzia w katalogu Tools,
* gracz wybiera, którego sniffera użyć,
* część snifferów może zbierać pliki lub zasoby,
* część snifferów może tylko czytać ruch i odblokowywać warunek hackowania obiektu,
* może być support action albo data-producing action, zależnie od aplikacji.

### risk scoring dla scan_ports

Ryzyko sygnału aktywności przy `scan_ports` ma być liczone proporcjonalnie do zasięgu gracza.

Zasięg oznacza tu gameplayowy zasięg wynikający między innymi z:

* motocykla,
* zoomu,
* levelu,
* mechaniki używanej już do liczenia progresu gracza.

Docelowo warto wydzielić osobny moduł albo klasę scoringu, która liczy ryzyko według ustalonego algorytmu.

### efekt aplikacji po uruchomieniu akcji

Gracz uruchamia akcję mapy.

Akcja wybiera lub uruchamia aplikację.

Aplikacja wykonuje cały dalszy efekt zgodnie ze swoim kontraktem:

* startuje operację,
* tworzy pliki,
* nie tworzy plików,
* zapisuje dump,
* tylko spełnia warunek hackowania.

Gracz nie wykonuje osobnego ręcznego kroku po zakończeniu aplikacji, jeśli kontrakt aplikacji mówi, że wynik ma zostać zapisany automatycznie.

### wiele aplikacji dla jednej akcji

Jeżeli wiele aplikacji obsługuje ten sam `map_action_id`, system powinien:

* otworzyć `Pliki` w katalogu `/tools/*`,
* podświetlić pasujące narzędzia, np. na zielono,
* pozwolić graczowi kliknąć wybraną aplikację,
* pozwolić graczowi wpisać nazwę aplikacji w terminalu i uruchomić właściwe narzędzie.

---

## TODO_DECISION

* Dokładny wzór scoringu ryzyka dla `scan_ports`.
* Dokładny wygląd podświetlenia pasujących narzędzi w `/tools/*`.
* Czy terminal ma uruchamiać pasującą aplikację tylko po dokładnej nazwie, czy również po aliasach.
