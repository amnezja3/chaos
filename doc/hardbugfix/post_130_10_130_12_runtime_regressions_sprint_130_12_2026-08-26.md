# POST 130.10–130.12 — runtime regressions

## Zakres i status

Pakiet naprawia cztery niezależne regresje wykryte manualnie po Sprintach 130.10–130.12. Nie jest nowym feature sprintem. Status implementacji: **READY FOR SERVER VALIDATION**. Nie wykonano deployu, restartu ani mutacji produkcyjnych.

## 1. Operations runtime / incidents / NPC services

### Objaw i reprodukcja

Po uruchomieniu `vehicle_tracking` rekord pozostawał widoczny w Centrum Operacji, ale kapsuła nie zmieniała pozycji. Nie narastał risk meter, nie inicjalizował się incident, nie pojawiały się warningi ani kapsuły służb.

### Evidence i root cause

Ekstrakcja `player_operations` z commitu `afa36a9b` przeniosła źródło danych mapy do `GET /api/operations?summary=1`. Endpoint wywoływał `operations_from_store_or_profile(..., refresh=False)`, więc `refresh_operations_runtime()` nie wykonywał się. Jednocześnie summary nadal hydratowało pełny profil, mimo że store był już canonical source dla mapy.

### Fix

- worker wykonuje bounded `process_operation_runtime_tick()`;
- tick czyta wyłącznie aktywne rekordy `player_operations`, wylicza position/risk/status, utrwala wynik przez version CAS i dopiero dla zaakceptowanej rewizji synchronizuje incident/warning;
- incident/NPC publication pozostaje w istniejących, idempotentnych store/delta bridge'ach;
- terminalny rekord otrzymuje canonical cleanup state;
- summary czyta wyłącznie gotową projekcję store — bez pełnego profile read/write i bez ciężkiego refreshu w pollerze;
- `_runtime_version` przy odczycie zawsze pochodzi z kolumny `version`, nie ze starej kopii JSON.

### Odrzucone rozwiązania

Nie przywrócono `refresh_operations_runtime()` do requestu mapy, pełnego profilu do pollingu ani nowego cache jako source of truth.

### Testy

Regresje obejmują zmianę pozycji w kolejnych tickach, brak profile read na hot path, odrzucenie stale CAS, idempotencję incidentu/warningu, NPC capsule runtime oraz lekki endpoint summary.

Status: **RESOLVED — READY FOR SERVER VALIDATION**.

## 2. Googleplex ticket → canonical teleport → live map

### Objaw i reprodukcja

Zakup biletu poprawnie zmieniał canonical position, ale otwarta mapa pozostawała w poprzednim miejscu. Dopiero ponowne otwarcie mapy pokazywało cel podróży.

### Evidence i root cause

`apply_googleplex_product_effect()` zapisywał pozycję, lecz odpowiedź `/install-app` nie zawierała stabilnego travel receipt. `showInstallAppProgress()` aktualizował wallet/catalog/apps i ignorował travel effect. Publiczny `map.player_moved` nie gwarantuje self-audience, a snapshot aktorów celowo wyklucza viewera.

### Fix

Odpowiedź sukcesu i replay zawiera `travel: {receipt, duplicate, city, position, position_version, position_updated_at}`. Frontend przekazuje canonical position do już otwartych map w trybie `teleport`; mapa aktualizuje własny marker i focus. Zamknięta mapa korzysta z canonical store przy następnym boot. Replay zwraca ten sam receipt i nie wykonuje efektu ani obciążenia walletu ponownie.

### Testy

Test backendowy sprawdza ten sam receipt i pozycję dla pierwszej odpowiedzi oraz replay. Test JS sprawdza bridge do otwartej mapy.

Status: **RESOLVED — READY FOR SERVER VALIDATION**.

## 3. Googleplex — diagnostyka błędów instalacji/zakupu

### Objaw i root cause

Frontend parsował wyłącznie JSON i ignorował `response.ok/status`. Wszystkie 400/409/422 i błędy produktu kończyły jako ogólny „Błąd instalacji”, mimo że backend często zwracał poprawne `reason` i `message`.

### Fix

Frontend zachowuje status HTTP, `reason_code/reason/error` i canonical message. Kontrolowany system message pokazuje komunikat użytkownikowi; bounded `console.warn` zapisuje wyłącznie status, reason, app id i product type — bez payloadu. Brakujące stabilne reason codes dodano dla authentication, catalog miss, recovery, requirements, payment recipient i błędu wewnętrznego. Backendowe statusy HTTP pozostają bez zmian.

### Testy

Test JS pokrywa 409 z canonical reason/message oraz fallback 422; istniejące testy backendowe pokrywają insufficient HC, requirements i konflikty.

Status: **RESOLVED — READY FOR SERVER VALIDATION**.

## 4. GhostNetwork lifecycle SFX

### Objaw i reprodukcja

Poprzedni hotfix poprawnie usunął SFX przy `active → active`, `contained → contained` i `hostile → hostile`, ale prawdziwe przejścia `public → contained`, `contained → active`, `safe → hostile` i utrata części także przestały grać.

### Evidence i root cause

`ghostnetwork/lifecycle.py` nadal tworzył dokładnie jeden canonical event z `previous_status/status`, conflict before/after, `event_id` i `source_event_id`. Collector zachowywał event. Błąd był w `GhostNetworkDeltaPublisher.build_delta_for_viewer()`: live delta kopiowała event id i projekcję, ale usuwała transition envelope. `playGhostNetworkDeltaSfx()` legalnie wymagał before/after, więc odrzucał niepełną deltę. Root cause był w backendowym bridge'u, nie w lifecycle ani rendererze.

### Fix

Delta publisher przenosi centralnie wyłącznie publiczną allowlistę pól transition: `source_event_id`, status/conflict before/after, machine progress before/after i `occurred_at`. Nie kopiuje nazw części, hidden topology ani pozostałych metadata. Renderer/state nadal nie jest źródłem SFX. Dedupe pozostaje oparte o canonical `event_id`; catch-up/recovery nadal wyłącza playback.

### Macierz kontraktu

| Before | After | Przyczyna | Event | SFX |
|---|---|---|---:|---:|
| reserved | public/discovered | discovery | 1 | 1 |
| public | contained | rzeczywiste otoczenie | 1 | 1 |
| contained | contained | rebuild | 0 | 0 |
| contained | active | rzeczywista aktywacja | 1 | 1 |
| active | active | rebuild/snapshot | 0 | 0 |
| safe | hostile/contested | wejście w konflikt | 1 | 1 |
| hostile | hostile | redraw/rebuild | 0 | 0 |
| active/contained | public/lost | rzeczywista utrata | 1 | 1 |
| public/lost | public/lost | rebuild | 0 | 0 |

`machine_progress_changed`, `machine_online` i `signal_sent` pozostają event-driven; snapshot, reopen, catch-up i recovery nie generują ich SFX.

### Testy

Python sprawdza zachowanie transition envelope i brak wycieku internal metadata. Test JS pokrywa pełną macierz, module progress/complete, GhostSignal oraz dedupe tego samego event id. Testy territory/GN potwierdzają brak eventu podczas rebuildu niepowiązanego terytorium.

Status: **RESOLVED — READY FOR SERVER VALIDATION**.

## Powiązane pliki

- `database.py`, `run.py`, `scripts/territory_conflict_worker.py`
- `ghostnetwork/lifecycle.py`, `ghostnetwork/deltas.py`, `static/js/terminal.js`
- `templates/map_template.html`
- `tests/test_operation_risk_meter.py`, `tests/test_incident_initializer.py`, `tests/test_npc_behavior_capsules.py`
- `tests/test_ghostnetwork_delta_publisher.py`, `tests/test_ghostnetwork_post130_bridge.py`
- `tests/js/test_ghostnetwork_sfx_transitions.js`, `tests/js/test_googleplex_runtime_bridge.js`

## Status końcowy

`POST 130.10–130.12 BUGFIX — READY FOR SERVER VALIDATION`
