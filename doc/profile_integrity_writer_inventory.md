# Sprint 130.10 — Etap 1: inventory writerów i integralność profilu

> **Dyspozycja po hardeningu (2026-08-21).** Ten dokument zachowuje stan
> wejściowy audytu i numery linii sprzed implementacji, dlatego opisy braku
> CAS/LKG, kanonicznego walletu i generacji sesji poniżej są historycznym
> baseline'em, a nie opisem bieżącego runtime. Capture
> `logs/chaos-13010-trolu2-20260821T184643Z.tar.gz` dla canonical login
> `trolu2` potwierdził profil o kształcie reset-like przy zachowanej dojrzałej
> historii domenowej. Korelacja ze znalezioną destrukcyjną ścieżką GN jest
> `STRONGLY CONSISTENT / HIGH CONFIDENCE`, lecz nie absolutna: przed incydentem
> nie istniały write-attempt telemetry ani zwalidowany LKG.
>
> W Etapach 2–6 wdrożono lokalnie: walidowany profil z revision/CAS i LKG,
> kanoniczny wallet oraz inventory overlay, fail-closed legacy writers,
> trwałą generację sesji z kontrolą pre-commit, tombstones i ochronę przed
> reuse identity oraz exactly-once projekcję nagród GN. Nie wykonano deployu,
> naprawy konta ani manualnego testu A → B → A. Aktualną bramką Sprintu
> 130.10 jest automatyczna regresja, a następnie manualny test izolacji kont.

Status audytu kodu: `CODE_DEFECT_CONFIRMED`.

Status atrybucji incydentu: `STRONGLY CONSISTENT / HIGH CONFIDENCE`.
Zakres: statyczny, read-only audit bieżącego workspace; bez zmian runtime i bez operacji na danych produkcyjnych.

Numery linii odnoszą się do snapshotu workspace z 2026-08-21. Dokument rozdziela dwie różne tezy:

- **potwierdzony defekt kodu** — istnieje osiągalna ścieżka, która zapisuje sparse identity jako pełny profil;
- **atrybucja konkretnego incydentu** — wymaga korelacji z bazą i logami serwera. Samo podobieństwo końcowego profilu nie jest dowodem historycznej przyczyny.

## 1. Wniosek wykonawczy

Najpoważniejszy znaleziony defekt to połączenie trzech poprawnych lokalnie operacji w destrukcyjny łańcuch:

```text
GN public/clan event
  -> sparse identity projection wszystkich graczy
  -> cache uznaje sparse rekord za już załadowany profil
  -> reward mutuje sparse rekord
  -> rekord trafia do dirty_profiles
  -> UserStore.save_profile wykonuje pełne zastąpienie users.profile_json
```

Skutkiem nie jest wyłącznie klasyczny lost update. Zapisywany obiekt od początku nie jest pełnym profilem. Po udanym zapisie pozostają głównie pola identity, pola dodane przez reward oraz trzy specjalnie chronione grupy danych; pozostałe klucze profilu mogą zostać usunięte.

Kod potwierdza możliwość takiego zapisu. Nie potwierdza jeszcze, że właśnie ten zapis dotknął konkretnego konta na serwerze. Do takiej konkluzji potrzebne są co najmniej: wersja wdrożenia, czas zmiany `users.updated_at`, rekord zastosowanej nagrody, zdarzenia wejściowe tego samego przebiegu oraz log wykonania runtime.

## 2. F-01 — potwierdzona destrukcyjna ścieżka GN

Klasyfikacja: `CONFIRMED CODE DEFECT / CRITICAL`.

### 2.1. Łańcuch zapisu

| Krok | Dowód w kodzie | Zachowanie |
|---|---|---|
| 1. Załaduj identity | `database.py:1430-1447`, `UserStore.list_profile_identities()` | SQL wybiera `username` i tylko pola clan/faction/profession przez `json_extract`; wynik nie jest pełnym profilem. |
| 2. Wstaw sparse dane do cache | `run.py:3153-3161`, `apply_ghostnetwork_runtime_result()` | Obecność dowolnego zdarzenia `public` lub `clan` ładuje sparse identity wszystkich użytkowników do `profile_cache`. |
| 3. Nie dociągaj pełnego profilu | `run.py:3166-3172` | `get_profile(player_id)` jest wywołane tylko, gdy gracza nie ma już w cache. Sparse rekord istniejącego gracza blokuje pełny load. |
| 4. Mutuj sparse rekord rewardem | `run.py:3185-3192`; `ghostnetwork/service.py:546-547`; `ghostnetwork/rewards.py:452-460` | Ten sam obiekt jest przekazany do `handle_reward_event(..., apply=True)` i po zastosowaniu nagrody oznaczony jako dirty. |
| 5. Zbuduj pola na brakujących domyślnych wartościach | `ghostnetwork/rewards.py:371-441` | `respect` jest liczony jako `int(profile.get("respect") or 0) + rsp`; tworzone/uzupełniane są `ghostnetwork_stats` i `ghostnetwork_reward_history`. |
| 6. Zapisz jako cały dokument | `run.py:3203-3204`; `database.py:1449-1529` | `save_profile()` wykonuje UPSERT z `profile_json = excluded.profile_json`; nie ma semantyki patch ani kontroli revision/CAS. |

### 2.2. Dlaczego zapis jest destrukcyjny

`list_profile_identities()` zwraca co najwyżej:

- `username`;
- `ghost_clan_code`, `clan_code`, `ghost_clan`, `clan_id`, `clan`, `clan_name`;
- `fraction`, `faction`;
- `ghost_profession`, `profession`.

Po rewardzie sparse słownik dostaje `respect`, `ghostnetwork_stats` i `ghostnetwork_reward_history`. `UserStore.save_profile()` przed pełnym zapisem odtwarza lub scala jedynie:

- `password` i `salt` — `database.py:1463-1477`;
- `launch_queue` — `database.py:1478-1488`;
- `ghostnetwork_reward_history` — `database.py:1490-1506`.

Nie przywraca pozostałych pól aktualnego profilu. W konsekwencji pola takie jak progresja, ustawienia, pliki, aplikacje, storage, stan operacji lub inne domeny obecne wyłącznie w `profile_json` mogą zniknąć. `respect` nie zachowuje wcześniejszej wartości: na sparse wejściu startuje od zera i po zapisie może odpowiadać tylko wartości nowej nagrody.

Zachowanie historii GN, credentials i kolejki nie przeczy temu defektowi — jest bezpośrednim skutkiem wyjątków w `save_profile()`. Podobnie, aplikacje lub storage mogą ponownie pojawić się w odpowiedzi po overlayu z tabel inventory; nie oznacza to, że pełny `profile_json` nie został wcześniej zastąpiony.

### 2.3. Warunki aktywacji

Defekt wymaga jednocześnie:

1. co najmniej jednego zdarzenia `public` lub `clan` w wyniku runtime, aby uruchomić broad identity preload;
2. zdarzenia kwalifikującego do nowej nagrody dla istniejącego gracza w tym samym wyniku runtime; nie musi to być to samo zdarzenie co w punkcie 1;
3. utworzenia nowego, nie-idempotentnego wpisu reward i prawdziwego `reward["applied"]`;
4. dojścia do pętli zapisu `dirty_profiles`.

Nagroda jest oznaczana jako zastosowana w repozytorium GN wewnątrz transakcji `run.py:3178-3194`, natomiast pełny zapis profilu następuje później, w `run.py:3203-3204`. Nie ma jednej transakcji obejmującej ledger GN i `users.profile_json`.

### 2.4. Granica atrybucji incydentu

Poniższe jest potwierdzone przez kod:

- sparse identity może zostać pomylone z pełnym profilem;
- reward mutuje ten sparse obiekt;
- `save_profile()` może nim bezwarunkowo zastąpić cały `profile_json`;
- zapis nie ma revision ani CAS.

Poniższe pozostaje niepotwierdzone bez danych serwera:

- że produkcja wykonywała w chwili incydentu dokładnie tę rewizję kodu;
- że w oknie utraty wystąpił wymagany batch public/clan + nowy reward;
- że zapis z `run.py:3204` był ostatnim writerem profilu;
- że to ten writer, a nie inna ścieżka full-save, endpoint delete albo interleaving sesji, spowodował konkretny incydent.

Końcowy „sparse GN fingerprint” jest mocną poszlaką, ale sam nie wystarcza do statusu `INCIDENT_CORRELATED`.

## 3. Semantyka centralnych writerów

W tym dokumencie:

- `FULL` oznacza zastąpienie całego `users.profile_json` przekazanym dokumentem;
- `PATCH -> FULL` oznacza logiczny patch API, po którym następuje fizyczny full-save snapshotu;
- `RMW` oznacza read-modify-write, zwykle bez ochrony przed równoległym writerem;
- `MIRROR` oznacza kopiowanie danych między `profile_json` i tabelą domenową;
- `CAS` oznacza zapis chroniony porównaniem poprzedniego `profile_json`.

| Writer | Semantyka fizyczna | Istotne zachowanie i ryzyko |
|---|---|---|
| `UserStore.save_profile()` — `database.py:1449-1529` | `FULL`, bez CAS | Zastępuje dokument. Chroni tylko credentials, `launch_queue` i historię GN. Każdy niepełny lub stary snapshot może usunąć nowsze/nieobecne pola. |
| `UserProfileManager.__init__()` / `_sync_with_template()` — `profileManagment.py:6-55` | potencjalny `FULL` już przy konstrukcji | Rekurencyjnie dodaje brakujące pola, ale usuwa pola spoza template, z wyjątkiem locked/dynamic whitelist. Jeśli normalizacja coś zmieni, konstruktor wywołuje `_save_changes()`. Pozornie read-only utworzenie managera może pisać. |
| `UserProfileManager.update_profile()` — `profileManagment.py:87-108` | `PATCH -> FULL` | Patchuje top-level snapshot, po czym `_save_changes()` zapisuje cały profil. Nie jest atomowym patchem SQL/JSON. |
| `update_profile_value()`, `update_hacked_target_by_coords()`, `remove_from_list_by_coords()` — `profileManagment.py:110-169` | `RMW -> FULL` | Każdy helper kończy w `_save_changes()`; ma ten sam stale-write risk. |
| `_save_changes()` — `profileManagment.py:174-176` | `FULL` | Deleguje do `UserStore.save_profile(self.user_profile)` i dopiero potem reloaduje. Reload nie zabezpiecza zapisu, który już nastąpił. |
| `loads_json()` — `database.py:114-120` | read fallback | Malformed JSON jest zamieniany na podany default. Writer pracujący dalej na `{}` może zamaskować uszkodzenie i nadpisać je nowym dokumentem. |

`users.updated_at` ma dokładność do sekundy (`database.py:106-107`). Nie jest revision i nie pozwala uporządkować kilku writerów w tej samej sekundzie.

## 4. Inventory call sites writerów

### 4.1. Bezpośrednie wywołania `UserStore.save_profile()` w runtime

| Moduł i linia | Funkcja / domena | Klasa zapisu | Ocena |
|---|---|---|---|
| `run.py:3204` | `apply_ghostnetwork_runtime_result()` | `FULL` | **Potwierdzony sparse/full defect F-01.** |
| `run.py:6040` | `process_territory_rebuild_job()` | `RMW -> FULL`, mirror | Ryzyko stale snapshot i nadpisania pól spoza territory. |
| `run.py:6096` | `finalize_conflict_rebuild_profiles()` | `RMW -> FULL`, mirror | Jak wyżej. |
| `run.py:7145` | `TerritoryEncirclementResolver._sync_profile_captured_targets()` | `MIRROR -> FULL` | Dedykowany stan territory jest kopiowany do kompatybilnościowego profilu. |
| `run.py:7332` | `clear_aimed_target_if_matches()` | `MIRROR/RMW -> FULL` | Domena target ma też dedykowany store. |
| `run.py:7816` | `set_player_aimed_target()` | `MIRROR/RMW -> FULL` | Jak wyżej. |
| `run.py:15243` | `ensure_purchase_account_profile()` | create/RMW `FULL` | Bootstrap konta zakupowego; bez revision. |
| `run.py:16619` | `ensure_dev_admin_account()` | create/RMW `FULL` | Bootstrap admina; bez revision. |
| `run.py:21887` | `update_profile_account()` | `RMW -> FULL` | Dane konta; bez CAS. |
| `run.py:22347` | `api_player_hack_tool_use()` — profil ofiary | `RMW -> FULL` | Modyfikacja apps/files ofiary; ryzyko stale i mirror drift. |
| `run.py:22439` | `api_player_hack_security_update()` | `RMW -> FULL` | Profil ofiary, bez CAS. |
| `run.py:22478` | `api_player_hack_security_preset()` | `RMW -> FULL` | Profil ofiary, bez CAS. |
| `run.py:24777` | `install_app()` — profil payee | `RMW -> FULL` | Ekonomia/płatność, osobny full-save drugiego konta. |
| `run.py:26270` | `gonna_win()` — profil właściciela | `MIRROR/RMW -> FULL` | Statystyki territory, bez CAS. |
| `run.py:7699` + `ghostnetwork/runtime.py:114-119` | callback `profile_saver` w `GhostNetworkRuntime.process_effect()` | `RMW -> FULL` | Odrębna ścieżka GN; zapisuje profil po applied result. Nie jest sparse loaderem z F-01, lecz nadal jest full-save bez revision. |

### 4.2. Wywołania `UserProfileManager.update_profile()` w runtime

Wszystkie poniższe call sites wyglądają jak częściowe aktualizacje, lecz kończą jako `FULL` przez `profileManagment.py:174-176`.

| Domena / funkcje | Call sites | Główne ryzyko |
|---|---|---|
| Market i operations: `refresh_market_runtime`, `refresh_and_persist_operations`, `persist_operation_control_profile` | `run.py:10975`, `13095`, `13590` | Stary snapshot operations/market może nadpisać niezależne zmiany. |
| Security/captured target: `save_owned_hacked_security` | `run.py:13646`, `13658` | `PATCH -> FULL` plus zapis mirror/source marker. |
| Synchronizacja profilu sesji: `sync_session_profile` | `run.py:17574`, `17617` | Szczególnie wrażliwe na interleaving loginów i stary snapshot. |
| Rejestracja: `api_register_finalize` | `run.py:17919` | Full-save świeżego profilu po bootstrapie. |
| Pozycja i mapa: `api_blacknet_cta_teleport`, `target_security_status`, flow `map_action` | `run.py:18625`, `18886`, `18894`, `19746`, `19954` | Mirror/RMW między profilem i store pozycji/targetu. |
| Operations API | `run.py:21333` | Anulowanie operacji przez `PATCH -> FULL`. |
| Ghost Exchange: `api_ghost_exchange`, preview, sell | `run.py:21572`, `21639`, `21706` | Wallet/profile jest dziś hybrydą; możliwy mirror drift i stale full-save. |
| Ustawienia: `update_profile_security`, `update_profile_desktop` | `run.py:21776`, `21838` | Niewielki logiczny patch zapisuje cały dokument. |
| Konsekwencje network/operations | `run.py:23511` | Aktualizacja profilu aktora po obliczeniu skutku; stale snapshot risk. |
| GhostLab/files: create, rename, blueprint, compile, publish, delete, generate, remove | `run.py:23891`, `23928`, `23967`, `24022`, `24128`, `24152`, `24191`, `24224` | Profilowe `files` są też częścią inventory mirror; full-save może rozjechać źródła. |
| App install/uninstall | `run.py:24852`, `24936`, `25068` | Apps/files/storage są zapisywane do profilu i tabel inventory. |
| Territory capture / `gonna_win` | `run.py:25557`, `25785`, `26171`, `26463`, `26490` | Wiele kont i mirrorów modyfikowanych w długim flow; brak wspólnej revision profilu. |

Dodatkowe implicit full-writes przez helpery managera występują w `run.py:13651`, `25709`, `26147`, `26154`. Każde utworzenie `UserProfileManager(...)` jest też potencjalnym writerem przez automatyczny template sync. Konstrukcje występują m.in. w `run.py:10975`, `13095`, `13590`, `13644`, `17574`, `17589`, `17718`, `17914`, `17918`, `18624`, `18886`, `18894`, `19745`, `19953`, `21333`, `21572`, `21639`, `21706`, `21775`, `21837`, `23511`, `23891`, `23928`, `23967`, `24022`, `24128`, `24152`, `24190`, `24223`, `24723`, `25067`, `25554`, `25707`, `25735`, `26145`.

### 4.3. Writery operatorskie i narzędziowe

| Moduł | Call site | Charakter |
|---|---|---|
| `tools/ghostnetwork_runtime.py` | `:51`, callback w `:152` | Rekonsyliacja historii i runtime CLI; `FULL`, wymaga traktowania jako operator writer. |
| `tools/admin_reset_test_state.py` | `:242` | Kontrolowany reset danych testowych; `FULL`. |
| `scripts/reset_user_password.py` | `:33` | Odczyt profilu, zmiana credentials, `FULL`; ryzyko stale mimo wąskiego celu. |
| `tools/repair_ghost_exchange_orphans.py` | `:170` | `UserProfileManager.update_profile()`, więc `PATCH -> FULL`. |
| `tools/smoke_admin_inventory.py` | `:163`, `:242` | Smoke writer admina przez manager; nie jest read-only. |

Tych ścieżek nie wolno wywoływać z audytora Etapu 1.

## 5. Bezpośrednie SQL writery `users.profile_json`

| Moduł i linia | Funkcja | Semantyka / ochrona |
|---|---|---|
| `database.py:1354` | `UserStore.seed_from_json_if_empty()` | `INSERT OR IGNORE`; pełny seed, nie aktualizuje istniejącego użytkownika. |
| `database.py:1512-1518` | `UserStore.save_profile()` | Pełny UPSERT, bez CAS. |
| `database.py:1571` | `UserStore.consume_launch_queue()` | Pełny RMW `profile_json` przy atomowym konsumowaniu kolejki; serializacja write lockiem nie jest revision całego profilu. |
| `database.py:1610` | `UserStore.authenticate()` | Pełny zapis przy migracji legacy password hash; wąski cel, ale fizycznie cały snapshot. |
| `database.py:3561` | `TerritoryProgressionReceiptStore.settle()` | Pełny zapis z CAS `WHERE profile_json = ?`, retry i receipt w transakcji. To pozytywny wyjątek. |
| `database.py:3683` | `TerritoryProgressionReceiptStore.settle_strategic()` | Jak wyżej: CAS i retry. |
| `database.py:6198`, `6202` | `WalletStore.transfer()` | Dwa pełne profile + wallet transaction, bez CAS profili. |
| `database.py:6268`, `6272` | `WalletStore.technical_transfer()` | Dwa pełne profile, bez CAS. |
| `scripts/db_migrations/migration_helpers.py:52` | helper migracji | Offline/operator full update. |
| `scripts/app_catalog_cleanup.py:150` | cleanup katalogu | Offline/operator full update. |
| `tools/migrate_app_contracts.py:352` | migracja kontraktów apps | Offline/operator full update. |
| `tools/profile_store_migration.py:676` | migracja store | Offline/operator full update; może zapisać backup migracyjny. |
| `tools/prepare_example_db.py:173` | generator example DB | Dotyczy bazy przykładowej, lecz fizycznie jest full update. |

Statyczny search produkcyjnego Pythona nie wykazał innego bezpośredniego `INSERT/UPDATE users.profile_json`. Dynamicznie budowany SQL lub kod spoza tego repo pozostaje poza zakresem tego stwierdzenia.

## 6. Schema i source-of-truth matrix

### 6.1. Potwierdzony model danych

- `users` — `database.py:224-232`: `id`, unikalny `username`, `password`, `salt`, `profile_json`, `created_at`, `updated_at`.
- Nie ma osobnej tabeli `profiles`; trwały dokument profilu to `users.profile_json`.
- Nie ma w `users` kolumn `revision`, `etag`, `checksum`, `schema_version`, `session_generation` ani odwołania do LKG.
- Inventory: `player_apps` (`database.py:1204-1215`), `player_tool_files` (`1217-1228`), `player_storage` (`1230-1238`).
- Wallet: `wallet_transactions` (`database.py:379-386`), `wallet_balances` (`1243-1248`), `wallet_balance_events` (`1253-1269`), `wallet_ledger` (`1273-1297`).
- Pozycja i target: `player_positions` (`database.py:455-462`), `player_target_runtime` (`421-445`).
- Operations/messages: `player_operations` (`database.py:1084-1095`), `system_messages` (`1119-1145`) oraz ich event stores.
- Territory: m.in. `captured_targets` (`database.py:486-500`), `player_areas` (`506-517`), `territory_target_ownership` (`827-836`), `territory_progression_receipts` (`887-899`).
- GhostNetwork: tabele `ghost_*` w `ghostnetwork/repository.py`, w tym `ghost_reward_ledger` (`453-474`).
- Nie ma zawsze aktywnego LKG. `profile_store_migrations.backup_json` (`database.py:1307-1319`) jest backupem konkretnej migracji, może zawierać pełne dane wrażliwe i nie jest bieżącym, atomowym last-known-good profilu.

### 6.2. Macierz autorytetu

| Zakres danych | Bieżące źródło / store | Rola `profile_json` | Obserwowany kierunek | Ocena Etapu 1 |
|---|---|---|---|---|
| Credentials | kolumny `users.username/password/salt` | zawiera legacy/compat kopię | `save_profile()` synchronizuje i chroni brakujące credentials | Kolumny są autorytetem logowania. Nigdy nie odtwarzać credentials z backupu UI lub raportu CLI. |
| Core identity i niewydzielona progresja | `users.profile_json` | canonical document | wielu writerów `FULL` | Jedyny trwały autorytet, bez revision/LKG; najwyższe ryzyko nieodwracalnego overwrite. |
| GN reward, eventy, reputacja | `ghost_reward_ledger` i pozostałe `ghost_*` | historia/statystyki są projekcją kompatybilnościową | repo GN -> mutacja profilu; historia częściowo scalana w `save_profile()` | Ledger jest autorytetem zastosowania nagrody. Profil nie może być źródłem do ponownego awardu. |
| Apps, tools/files, storage | `player_apps`, `player_tool_files`, `player_storage` przez `PlayerInventoryStore` | compatibility mirror | dziś **dwukierunkowo**: seed/profile -> store, zapis delta -> store, snapshot store -> profile | Nie deklarować jeszcze bezwarunkowo store-only authority. Pusty/niezainicjalizowany store i fallback zmieniają kierunek. Rozbieżność to warning, nie automatycznie corruption. |
| Wallet | `wallet_balances`, events, ledger, transactions | `hackcoins` jest nadal fallbackiem i mirrorem | dziś hybryda; `WalletBalanceStore.get_balance(..., fallback_profile=...)` może przepisać balance store z profilu (`database.py:7683-7718`) | Autorytet nie jest jeszcze jednoznaczny. Mismatch nie dowodzi utraty środków bez ledger/transaction correlation. |
| Pozycja | `player_positions` / `PlayerPositionStore` | fallback/compat `curently_possition` | profile seed przy braku; następnie store -> response/profile mirror | Store-primary po bootstrapie, lecz nadal istnieje ścieżka fallback. |
| Aimed target | `player_target_runtime` / `PlayerTargetRuntimeStore` | fallback/compat target | profile seed przy braku oraz mirror full-save | Store-primary po bootstrapie; full-save profilu nadal zwiększa blast radius. |
| Operations | `player_operations` / `PlayerOperationStore` i eventy | compatibility snapshot | występują synchronizacje w obie strony | Hybryda. Do odtworzenia używać tabel/events, nie ślepo profilu. |
| System messages | `system_messages` / `SystemMessageStore` | ewentualna projekcja UI | store -> odczyt/UI | Dedykowana tabela jest autorytetem. |
| Territory/ownership/progression | dedykowane territory stores i receipts | liczne pola kompatybilnościowe/statystyczne | store -> profil przez rebuild/sync; część flow nadal RMW profilu | Dedykowane ownership/receipts są mocniejszym dowodem niż profil. Nie odbudowywać ownership wyłącznie ze sparse profilu. |
| LKG / revision | brak | brak | brak | `NOT_AVAILABLE`; migration backup nie spełnia kontraktu LKG. |

Istotny kierunek mirrorów jest widoczny w `run.py:8009-8055` (`apply_runtime_stores_to_profile()`), `run.py:228-262` (`record_storage_delta()`), `run.py:282-293` (`record_apps_delta()`) oraz `database.py:7259-7413` (`PlayerInventoryStore.seed_from_profile()`, snapshot i mirror). Dlatego obecny model nie jest czystym „tabele są canonical, profil tylko read model”; jest przejściową hybrydą.

## 7. Kontrakt read-only korelacji serwerowej

Audytor Etapu 1 powinien otwierać bazę read-only, włączać `PRAGMA query_only=ON`, najpierw wykrywać tabele i kolumny, a dopiero potem wykonywać zapytania zależne od capabilities. Brak tabeli ze starszej wersji schematu ma dawać `UNAVAILABLE`, nie traceback ani fałszywy `PASS`.

### 7.1. Minimalny zestaw odczytów

| Obszar | Dane do raportu | Znaczenie |
|---|---|---|
| Schema capabilities | obecność `users`, inventory, wallet, position, target, operations, territory, `ghost_reward_ledger`, session generation i LKG | Ustala, które korelacje są w ogóle możliwe. |
| Profil | `json_valid`, `updated_at`, rozmiar bajtowy, liczba kluczy top-level, hash dokumentu, lista brakujących wymaganych grup, sparse-identity fingerprint | Wykrywa phenotype i zachowuje materiał porównawczy bez drukowania JSON. |
| GN | zredagowane counts/status/timelines eventów i rewardów według bezpiecznej listy typów oraz audience scope, a także porównanie applied reward keys z historią profilową przez count/checksum | Sprawdza preconditions F-01 bez ujawniania event/part/territory IDs. Sam applied reward bez clan/public eventu nie wystarcza. |
| Inventory/wallet | wersje/updated_at/counts, sumy/ostatnie eventy i rozbieżność z profilem | Pokazuje, czy dedykowane store przetrwały; mismatch jest sygnałem hybrydowego mirrora, nie samodzielnym dowodem przyczyny. |
| Territory/operations | receipts, ownership, operation events i timestamps | Ustala inne aktywne writery i możliwe źródła odtworzenia. |
| Serwer | deployment revision, request/job logs, worker identity, timestamp start/end `apply_ghostnetwork_runtime_result` | Rozstrzyga, czy kod defect path faktycznie wykonał się dla konta. |

Zapytania JSON muszą osłaniać `json_extract/json_type` warunkiem `json_valid(profile_json)`. Malformed JSON jest osobnym `CRITICAL`; nie należy traktować go jak pustego poprawnego profilu.

### 7.2. Statusy korelacji

| Status | Warunek |
|---|---|
| `CODE_DEFECT_CONFIRMED` | Wynika ze statycznej ścieżki opisanej w F-01; nie zależy od serwera. |
| `INCIDENT_CORRELATED` | Log/batch oraz dane GN potwierdzają wymagane zdarzenia i zapis dla danego konta w oknie zmiany profilu; wersja wdrożenia zawiera defekt. |
| `INCIDENT_CONSISTENT_NOT_PROVEN` | Profil ma zgodny sparse fingerprint i istnieje pobliski applied reward, ale brak dowodu wspólnego batcha albo logu writer call. |
| `INCIDENT_NOT_CORRELATED` | Wiarygodne logi lub wersja wdrożenia wykluczają wykonanie ścieżki w oknie incydentu. |
| `INSUFFICIENT_EVIDENCE` | Brakuje logów, tabel/czasów lub wcześniejszego snapshotu; nie wolno automatycznie awansować do „correlated”. |

Ponieważ `users.updated_at` ma rozdzielczość sekundową, zbieżność czasu w tej samej sekundzie nie ustala kolejności writerów. Preferowane są logi z większą precyzją i identyfikatorem przebiegu.

Implementacja probe raportuje dodatkowo
`ghostnetwork.user.sparse_activation_overwrite_signal`. Łączy bez ujawniania ID:

- clan event `ghost.part_activated` z applied rewardem
  `part_first_activated` przez `source_event_id`;
- czas eventu/rewardu z bieżącym `users.updated_at`;
- rdzeń starter-like (`level=1`, `hackcoins=1000`);
- trwały stan territory oraz co najmniej jeden sygnał inventory/wallet/purchase.

Złożony sygnał ma severity `high` i blokuje uznanie konta za zdrowe, ale nadal
jest oznaczony jako korelacja, nie samodzielny dowód historycznej przyczyny.
Brak zwalidowanego payloadu LKG/backup pozostawia
`historical_drop_detection=unavailable`; samo istnienie tabeli lub backupu
migracyjnego nie daje fałszywego `complete`.

### 7.3. Redakcja i bezpieczny output

Raport CLI całkowicie pomija wartość `username`; identyfikuje podmiot wyłącznie
jako `requested_account` i podaje długość wejścia. Zawiera czasy, counts, wersje
i hashe projekcji. Nie wypisuje:

- `password`, `salt`, e-maila, IP ani pełnego `profile_json`;
- `backup_json` z `profile_store_migrations`;
- treści files/messages, payloadów prywatnych eventów lub tokenów sesji.

Narzędzie nie ma trybu wypisującego login, credentials ani pełne payloady.

## 8. F-02 — brak generacji sesji (skrót)

Klasyfikacja: `CONFIRMED CODE/SCHEMA GAP`; atrybucja incydentu `PENDING_SERVER_CORRELATION`.

Logowanie ustawia jedynie `session["user"] = username` i czyści cache profilu (`run.py:17796-17803`); rejestracja robi to samo (`run.py:17929-17930`), a logout wykonuje `session.clear()` (`run.py:18730-18733`). W runtime/schema nie ma `session_generation`, `session_epoch`, `login_generation` ani tabeli `user_sessions`; jedyne wystąpienia tych pojęć są kontrolą w narzędziu audytowym.

Nie istnieje więc serwerowy identyfikator generacji logowania, którym można opatrzyć i odrzucić spóźnione requesty, wyniki pollera lub delty poprzedniej sesji po zalogowaniu kolejnego konta w tym samym kliencie. To potwierdzona luka izolacji, ale nie dowód, że spowodowała konkretny incydent bez request/session logs.

## 9. F-03 — `/api/users/delete` (skrót)

Klasyfikacja: `CONFIRMED AUTHORIZATION DEFECT / CRITICAL`; atrybucja incydentu `PENDING_SERVER_CORRELATION`.

`run.py:18843-18870` wymaga tylko dowolnej zalogowanej sesji, przyjmuje arbitralne `username` z JSON i blokuje wyłącznie nazwę `admin`. Nie sprawdza, czy caller usuwa własne konto ani czy ma rolę administracyjną. Każdy zalogowany użytkownik może zatem zażądać usunięcia innego nie-adminowego konta.

`UserStore.delete_user()` (`database.py:1623-1650`) usuwa wybrane dane komunikacji i territory oraz wiersz `users`, lecz nie obejmuje jawnie wszystkich nowszych tabel inventory, wallet, position, target, operations i GN. Oprócz nieautoryzowanego delete istnieje więc ryzyko osieroconych danych domenowych. Konkretnego incydentu nie wolno przypisywać temu endpointowi bez access/request logs lub innego śladu wywołania.

## 10. Granice Etapu 1

Etap 1 potwierdza mechanizm destrukcyjnego zapisu i kompletuje mapę writerów/źródeł. Nie wykonuje naprawy, rekonstrukcji ani modyfikacji bazy.

Przed odzyskiwaniem danych należy osobno:

1. zachować bieżący checkout i aktywny zestaw DB/WAL/SHM bez checkpointu,
   kopiowania do handoffu ani restartu;
2. uruchomić wyłącznie read-only korelację zgodną z sekcją 7;
3. ustalić status atrybucji bez wnioskowania z samego kształtu profilu;
4. dopiero w kolejnym etapie zaprojektować guard dla partial/full save, revision/CAS, jednoznaczny authority matrix i generację sesji.

**Werdykt Etapu 1:** destructive GN sparse-identity -> reward mutation -> full-save jest potwierdzonym defektem kodu. Jego udział w konkretnym incydencie pozostaje `PENDING_SERVER_CORRELATION`.
