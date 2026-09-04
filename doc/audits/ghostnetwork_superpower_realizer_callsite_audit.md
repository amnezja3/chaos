# 138.getway.0.1 — audyt call-site realizerów supermocy

Status: `COMPLETE / SCOPE REDUCED AFTER REVIEW`

Data: 2026-09-05

Zakres: stan kodu przed implementacją wspólnego okna aktywacji. Audyt odpowiada
na cztery pytania dla każdej z 12 rodzin: gdzie powstaje wynik, jaki canonical
store go przechowuje, jaki jest najwęższy bezpieczny hook oraz czy obecna ścieżka
spełnia zakaz heavy profile i nieograniczonego fan-out.

## 1. Werdykt

Żaden realizer nie jest obecnie zaimplementowany. Istniejący
`GhostAbilityRegistry` rozwiązuje katalog, profesję i stan części, ale adaptery
`market`, `hack`, `territory`, `operation`, `visibility` i `cyberner` są
pass-through/no-op. Nie wolno uznać samego istnienia adaptera za działającą moc.

| Stan | Liczba | Znaczenie |
| --- | ---: | --- |
| `IN GATE / SMALL HOOK` | 7 | istnieje narrow store i bezpieczny punkt integracji; potrzebna jest mała, typowana metoda |
| `IN GATE / LIGHT-READ PREREQUISITE` | 2 | `scan_range` i `map_zoom` zostają po przywróceniu narrow read path |
| `DEFERRED OUT OF GATE` | 3 | `file_value`, `actor_visibility`, `incident_decoy`; ryzyko nie jest uzasadnione efektem |
| `READY WITHOUT CODE` | 0 | brak — wszystkie adaptery gameplayowe są dziś no-op |

Po przeglądzie produktowym bramka została świadomie zawężona do `9/9` rodzin.
Nie implementujemy trzech ryzykownych ścieżek tylko po to, aby zachować pierwotną
liczbę. Nadrzędnym wynikiem gatewaya ma być lekki runtime, a dopiero potem efekt.

## 2. Wspólne źródła prawdy

### Eligibility

- `ghostnetwork/abilities.py::GhostAbilityRegistry.resolve_player_abilities()`
  jest właściwym resolverem: łączy klan, profesję, aktywny cykl i stan modułu
  odpowiadającej części;
- `user_identity_projection` jest indeksowana po `username` i klanie oraz zawiera
  alias, klan i profesję;
- projekcja identity **nie zawiera** poziomu, `scan_range_bonus` ani
  `map_zoom_bonus`; obecny `get_profile_identity()` także wyciąga tylko pola
  identity z `profile_json`;
- poziom i bonusy nie mogą być doraźnie pobierane przez `get_profile()` podczas
  aktywacji. `.0.2` musi najpierw dostarczyć małą projekcję capability/progression
  aktualizowaną w tej samej chronionej ścieżce zapisu profilu.

### Aktywne okno

Brakuje canonical rekordu aktywacji. `.0.2` dodaje pojedynczy typ rekordu okna,
odczytywany po graczu, z `ability_code`, `source_part_id`, `activated_at`,
`expires_at`, `cooldown_until`, `level_snapshot`, opcjonalnym canonical
`target_id`, wersją i dedupe key. Nie wolno przechowywać w nim dowolnego skryptu,
nazwy pola bazy ani parametrów przesłanych przez klienta.

### Bounded oznacza limit w SQL

Odfiltrowanie listy w Pythonie po pobraniu wszystkich rekordów nie jest bounded.
Każda metoda wykorzystywana podczas aktywacji lub ticku ma mieć `LIMIT` w SQL,
stabilny porządek i indeks zaczynający się od klucza gracza/scope.

## 3. Macierz 12 rodzin po redukcji zakresu

### 3.1 `operation_speed` — `SMALL HOOK`

- Producer/kalkulacja: `run.py::build_operation_instance()`,
  `operation_remaining_seconds()` i `refresh_operation_runtime()`.
- Store: `player_operations`; indeks
  `idx_player_operations_user_status(username,status,updated_at)`.
- Bezpieczny write: `PlayerOperationStore.compare_and_swap_runtime()` z wersją
  rekordu i krótkim `BEGIN IMMEDIATE`.
- Hook:
  1. przy aktywacji — pobrać maksymalnie ustaloną liczbę aktywnych operacji
     gracza i jednorazowo skorygować pozostały `expires_at`;
  2. przy starcie nowej operacji — policzyć krótszy duration/expiry z aktywnego
     okna przed `upsert_operations()`.
- Wymagane: nowa metoda `list_active_operations(username, limit)`, ponieważ
  obecne `list_operations(..., include_terminal=False)` nie ma `LIMIT`; marker
  `ability_application_key` w operacji/event dedupe chroniący retry i każdy tick.
- Zakazane: ponowne dzielenie czasu na każdym ticku oraz zmiana `started_at`.

### 3.2 `file_yield` — `SMALL HOOK`

- Producer: `run.py::finalize_operation_files_bounded()`.
- Store: `player_data_files`, PK `(username,file_id)`, indeks operacji
  `(username,operation_id)`.
- Bezpieczny write: `PlayerInventoryStore.append_data_files()`, który atomowo
  dodaje pliki i oznacza operację jako sfinalizowaną.
- Hook: po domenowych finalizerach, przed `append_data_files()`, utworzyć bounded
  liczbę dodatkowych plików dozwolonej kategorii.
- Dedupe: stabilne `file_id` wyprowadzone z `operation_id + activation_id + slot`;
  istniejący PK czyni replay no-op.
- Limit do zamrożenia w `.0.4`: maksymalna liczba bonusowych plików na jedną
  operację i aktywację.

### 3.3 `file_value` — `DEFERRED OUT OF GATE`

- Kalkulator: `ghost_exchange_price_preview()` i `market_batch_price()`;
  canonical wypłata używa idempotentnego `WalletBalanceStore.credit()`.
- Problem: manualna i automatyczna sprzedaż nadal operują na pełnym profilu,
  zapisują `files`, `market_history` i storage przez `UserProfileManager`, a
  dopiero potem synchronizują `player_data_files`.
- Bezpieczny docelowy hook: wejściowy, bounded mnożnik w kalkulatorze ceny,
  pochodzący z immutable provenance pliku utworzonego podczas aktywnego okna.
- Warunek ewentualnego powrotu: narrow settlement pliku/batcha musi atomowo zmienić
  `player_data_files`, storage i wallet bez pełnego profilu. Do czasu tego
  cut-overu realizer nie może wejść na ścieżkę produkcyjną.
- Zakazane: sprawdzanie mocy dopiero w chwili sprzedaży — plik wyprodukowany w
  oknie zachowuje provenance, a plik stary nie zyskuje bonusu tylko dlatego, że
  gracz uruchomił moc przed kliknięciem „sprzedaj”.

### 3.4 `data_quality` — `SMALL HOOK`

- Producer: `apply_operation_quality_to_files()` wykonywany wewnątrz
  `finalize_operation_files_bounded()`.
- Store: `player_data_files`.
- Hook: typowany bonus do `quality_score` i/lub `completeness_percent` przed
  normalizacją i zapisem, tylko dla allowlisty kategorii.
- Granice: clamp `0–100`; brak bezpośredniego ustawiania ceny; istniejący
  kalkulator ceny nadal konsumuje jakość i kompletność.
- Dedupe: finalizacja operacji i stabilne file IDs; provenance aktywacji zapisane
  w metadanych pliku.

### 3.5 `hack_actions` — `SMALL HOOK`

- Store: `player_target_runtime`, jeden rekord na `username`, PK po graczu;
  eventy mają indeks `(username,created_at)`.
- Odczyt: `PlayerTargetRuntimeStore.get()` / `get_active_target()`.
- Obecna aktualizacja: `upsert_aimed()` zachowuje identity celu, monotonicznie
  scala akcje i wykonuje kontrolę wersji po ponownym odczycie.
- Hook: dedykowana metoda CAS przyjmująca `username`, canonical `target_key`,
  `expected_version`, allowlistę czterech action keys i `activation_id`.
- Efekt `Wejście Serwisowe`: action dots mogą stać się wykonane, ale security,
  capture i wynik hacku pozostają nietknięte.
- Zakazane: target/akcje z DOM oraz wywołanie ogólnego `upsert_aimed()` z pełnym
  payloadem klienta jako realizera.

### 3.6 `target_security` — `SMALL HOOK`

- Bieżący cel gracza: `player_target_runtime` i wersja rekordu.
- Własny captured target: `TerritoryStore.update_captured_target_security()`;
  owner check, `security_version` i unikalny klucz
  `(owner_username,lat,lng,label)`.
- Hook: zamknięta transformacja znanych boolean security keys z expected version;
  maksymalna liczba zmienionych kluczy jest częścią konfiguracji rodziny.
- Wymagane: realizer wybiera dokładnie jeden z dwóch kontraktów celu i zapisuje
  event/dedupe; nie przyjmuje mapy security od klienta.
- Zakazane: `run.py::save_owned_hacked_security()`, bo czyta i zapisuje pełny
  profil jako kompatybilnościowe źródło.

### 3.7 `operation_risk` — `SMALL HOOK`

- Kalkulator: `response_network/operation_risk_meter.py::calculate_operation_risk()`.
- Istniejące wejścia: base heat, czas, narzędzie, security i conflict; dopiero ich
  suma przechodzi przez progi warning/incident.
- Hook: wykorzystać obecny argument `rules` jako serwerowy, bounded
  `ability_heat_modifier`, uwzględniany przed clamp i progami.
- Runtime: `refresh_operation_runtime()` już przelicza meter; aktywne okno należy
  odczytać raz na gracza/tick, nie raz na operację.
- Zakazane: bezpośrednie ustawienie `risk_level`, `warning_crossed`,
  `incident_crossed` albo statusu incydentu.

### 3.8 `scan_range` — `IN GATE / LIGHT-READ PREREQUISITE`

- Konsument: `/map-action` dla `action == "scan"`; dystans jest porównywany z
  `get_player_action_range()`.
- Problem: `/map-action` ładuje pełny profil przez `sync_session_profile()`, a
  `get_player_action_range()` czyta z niego `level` i `scan_range_bonus`.
- Prerekwizyt: capability/progression projection z sekcji 2 oraz wąski getter
  efektywnego zasięgu.
- Hook: modyfikować tylko branch skanu. Wariant „niezależnie od motocykla” jest
  jawnym server-side bypass `scan_distance_check`, nie nieskończoną liczbą i nie
  zmianą wspólnego action range dla hacku/terytorium.
- Position: istniejący `PlayerPositionStore.get()` daje narrow pozycję po PK.

### 3.9 `map_zoom` — `IN GATE / LIGHT-READ PREREQUISITE`

- Konsument: payload `/api/map/player-areas` przez `get_player_map_zoom()`.
- Problem: endpoint ładuje profil viewera, wszystkie obszary, a następnie robi
  `user_store.list_profiles()` dla ownerów. Getter czyta `map_zoom_bonus` z
  pełnego profilu.
- Prerekwizyt: capability/progression projection i viewer-only capability
  snapshot niezależny od ciężkiego endpointu obszarów.
- Hook: `effective_zoom = clamp(base + active_modifier)` w backendowym
  viewer snapshot; frontend tylko stosuje otrzymany limit.

### 3.10 `actor_visibility` — `DEFERRED OUT OF GATE`

- Konsument: `/api/map/player-actors` i istniejący renderer markerów.
- Krytyczny problem: endpoint iteruje po `user_store.list_profiles()` oraz
  `territory_store.list_player_areas()` bez ownera; dodatkowo czyta profile
  viewera i kontaktów.
- Warunek ewentualnego powrotu: narrow actor projection obejmująca position, public identity i
  minimalny relation/audience context oraz bounded spatial/relationship query.
- Hook po cut-overze: filtr widoczności na już ograniczonym zbiorze kandydatów.
- Zakazane: „moc widzi wszystkich” realizowana przez account scan. `Wszyscy`
  oznacza wszystkich audience-safe aktorów zwróconych przez bounded query.

### 3.11 `incident_decoy` — `DEFERRED OUT OF GATE`

- Store/renderer istnieją: `IncidentStore`, `NPCCapsuleStore`, endpointy mapy.
- Problemy:
  - `IncidentStore.list_active()/list_public()` nie mają limitu ani filtra scope;
  - `NPCCapsuleStore.list_active()/list_public()` również są globalne i
    nielimitowane;
  - GET `/api/map/incident-npc-capsules` uruchamia backfill/zapis przez
    `ensure_response_npc_capsules_for_active_incidents()`;
  - obecny schema/policy nie gwarantuje, że synthetic decoy jest wyłączony z kar,
    nagród, detekcji i statystyk realnych zdarzeń.
- Warunek ewentualnego powrotu: jawne `synthetic`, `source`, owner/audience scope, indeksowane
  bounded listy, TTL 15 min i policy exclusion; tworzenie ma nastąpić przy
  aktywacji w ograniczonym fan-out, nigdy w GET i bez nowego workera.
- Geometria: wyłącznie `TerritoryStore.list_player_areas(username)` z twardym
  limitem klastrów/decoyów; nie globalne `list_player_areas()`.

### 3.12 `territory_defense` — `SMALL HOOK`

- Store: `captured_targets`; owner-specific odczyt i
  `update_captured_target_security()` z `security_version`.
- Hook: jeden canonical własny target albo mały jawny batch target IDs, każdy z
  owner check, expected version i activation dedupe.
- Wymagane: bezpośredni bounded lookup targetu. Obecny `get_captured_target()`
  wywołuje `list_captured_targets(username)` i przeszukuje całą listę w Pythonie;
  należy zastąpić go zapytaniem `SELECT ... LIMIT 1` po istniejącym unikalnym
  kluczu lub nowym indeksowanym canonical target key.
- Zakazane: globalne wzmacnianie wszystkich celów/terytoriów oraz zapis do
  profilu `hacked`.

## 4. Obowiązkowa ścieżka przywrócenia lekkiego runtime

Kolejność jest zamrożona, bo kolejne kroki wykorzystują wcześniejsze:

1. **Narrow player capability/progression projection** — `level`, bazowy
   `scan_range_bonus`, `map_zoom_bonus`; writer w tej samej chronionej ścieżce co
   profil, integrity/version gate, odczyt po `username`.
2. **Bounded store methods** — aktywne operacje z SQL `LIMIT`, captured target z
   bezpośrednim lookupem oraz twarde limity fan-out.
3. **Scan branch cut-over** — pozycja z `PlayerPositionStore`, level i bonus z
   projekcji; żadnego `sync_session_profile()` tylko po to, aby sprawdzić zasięg.
4. **Map capability snapshot** — zoom i dane przycisku z viewer-only projection,
   niezależnie od ciężkiego payloadu `/api/map/player-areas`.
5. **Player-areas identity cut-over** — alias i klan ownerów przez bounded batch
   `UserIdentityProjectionStore`, bez `list_profiles()` i per-owner profile read.

Pierwsze cztery punkty należą do `.0.2`; piąty jest osobnym checkpointem light-read
przed `.0.3`, ponieważ został ujawniony przez audyt tej samej mapowej ścieżki.
`file_value`, aktorzy i syntetyczne incydenty nie blokują już gatewaya i nie mogą
otrzymać ciężkiego fallbacku.

## 5. Budżety do testów `.0.4`

| Obszar | Zamrożony warunek bezpieczeństwa |
| --- | --- |
| profile | `profile_full_read=0`, `profile_full_write=0`, `account_scan=0` |
| aktywacja | 1 eligibility snapshot + 1 window CAS + bounded realizer writes |
| operacje | limit w SQL; każda operacja zmieniona najwyżej raz na activation |
| pliki | limit bonusowych plików; stabilne IDs; jedna atomowa finalizacja |
| target/security | dokładny target key + owner + expected version |
| deferred families | zero wywołań Ghost Exchange settlement, actor scan i incident/NPC runtime |
| SQLite | brak zewnętrznej pracy w transakcji; raport writer wait/lock |

## 6. Decyzja dla następnego checkpointa

`138.getway.0.1` jest zamknięty. Następny checkpoint to `.0.2`:

1. schema/repository małego okna aktywacji;
2. narrow capability/progression projection z poziomem;
3. backendowy activate/snapshot z eligibility, cooldown, CAS i dedupe;
4. na tym etapie bez właściwego gameplay realizera i bez frontendu;
5. testy potwierdzające reload/expiry oraz zero heavy profile;
6. odłożone rodziny zwracają `realizer_unavailable` i nie mają fallbacku.

Pierwszy efekt gameplayowy pozostaje w `.0.5`: V1 / `Insider Feed` wyłącznie z
`operation_speed`. Operator harness obejmuje 9 dopuszczonych rodzin i nie może
ominąć prerekwizytów z tej macierzy.
