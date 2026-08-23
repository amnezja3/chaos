# Profile Store Extraction Audit

Data: 2026-07-23

Status: audit / recommendation

Cel: wskazac, ktore fragmenty `users.profile_json` warto przeniesc do
osobnych tabel/store'ow, zeby ograniczyc race condition, cofanie stanu,
ciezkie `sync_session_profile()` i zapis calego profilu przy malych zmianach.

## Bramka po incydencie Trollu2 — Sprint 130.10

Incydent z 2026-08-21 podnosi integralność profilu i kierunek compatibility
mirrorów do P0 przed Sprintem 131. Wiążące artefakty:

```text
doc/Incydent Trollu2 — utrata profilu, błędy sesji i plan odbudowy.md
doc/sprint_130_10_profile_integrity_session_isolation.md
doc/sprint_130_11_trollu2_controlled_recovery.md
doc/profile_integrity_writer_inventory.md
doc/profile_integrity_recovery_runbook.md
```

Potwierdzony destructive-write w bieżącym modelu:

* `apply_ghostnetwork_runtime_result()` może naliczyć first activation reward
  na sparse projection z `list_profile_identities()`, a następnie przekazać ją
  do pełnego `UserStore.save_profile()`. Późniejszy template sync zamienia braki
  w wartości starter-like. Defekt kodu jest `CONFIRMED`. Exact-user capture dla
  canonical `trolu2` pokazał dwa skorelowane activation rewardy, reset-like
  progression oraz zachowane durable stores; korelacja incydentu ma status
  `STRONGLY CONSISTENT / HIGH CONFIDENCE`, przy braku historycznej telemetryki
  pojedynczego profile write i pre-incident LKG.

Pozostałe potwierdzone ryzyka:

* `loads_json(..., {})` nie odróżnia błędu JSON od pustego wyniku;
* strukturalnie poprawny, lecz niepełny profil może zostać zsynchronizowany z
  template'em bez pełnego sanity contract;
* pełny `UserStore.save_profile()` nie ma ogólnej revision/CAS ani LKG;
* `PlayerInventoryStore` prawidłowo może odtworzyć apps/tools z wydzielonego
  store, co tłumaczy częściowe przeżycie danych;
* wallet ma nadal niebezpieczny kierunek reconciliation: rozbieżny
  `fallback_profile.hackcoins` może ustawić `wallet_balances`;
* mimo istnienia `wallet_balances` legacy `WalletStore.transfer()` i
  `technical_transfer()` nadal zapisują oba pełne `profile_json`, więc wallet
  ma obecnie hybrydowy zestaw writerów.

Sprint 130.10 ma najpierw zablokować persistence fallbacku, dodać revision/CAS
i atomowy last-known-good oraz wymusić kierunek:

```text
canonical store -> profile mirror
```

Automatyczny kierunek `fallback profile -> canonical store` nie może działać w
zwykłym read path. Przed odwróceniem mirroru trzeba przenieść lub bezpiecznie
spiąć wszystkie wallet writers, w tym transfery, Googleplex i Ghost Exchange;
inaczej dwa źródła salda rozjadą się. Globalny store-primary cutover pozostałych
scope'ów nadal pozostaje poza zakresem.

## Stan wejściowy Sprintu 130.11 — 2026-08-23

Dedykowane `tools/repair_trollu2_profile.py` utrzymuje pełny profil poza runtime:
odczytuje dokładnie jeden allowlisted rekord `trolu2`, nie używa
`list_profiles()` i nie jest importowane przez web ani worker. Wallet,
inventory, territory i GhostNetwork są odczytywane z canonical tables.

Lokalny read-only audit potwierdził, że current profile jest checksum-valid, ale
bootstrap LKG zawiera canonical mirror (`files`, `hacked`, `operations`) i nie
może być źródłem recovery. Plan zachowuje 11 apps/tools, dowodzi ostatnich
instalacji Nmap/Metasploit i wyprowadza Tokio z receipt-backed travel effect.
Pierwszy wariant geometrii został zatrzymany przez realną kolizję; bezkolizyjna
relokacja została wybrana deterministycznie. Etap zapisujący jest gotowy, ale
pozostaje ograniczony do trzech jawnie allowlistowanych funkcji operatorskich:
`apply_level_step`, `final_settlement` i `rollback_recovery`. Każda jest
exact-account, plan/checksum/CAS/receipt gated; test statyczny nadal odrzuca
każdy inny direct `users.profile_json` write.

Territory worker nie korzysta z wyjątku heavy-profile. Job z kontraktem
`sprint_130_11`, exact subject `trolu2` i recovery plan ID przekazuje tylko
recovery level do canonical geometry rebuild. Worker pomija full-profile read,
compatibility profile projection oraz LKG write. Test behawioralny ustawia te
ciężkie calle jako błędy i potwierdza ich zero. Zwykły worker zachowuje
dotychczasowy kontrakt.

## Status po Sprintach 130.1-130.5

Wydzielone store'y runtime:

* `app_action_receipts`,
* `player_target_runtime`,
* `player_positions`,
* `player_operations`,
* `system_messages`,
* `player_apps`,
* `player_tool_files`,
* `player_storage`,
* `wallet_balances`.

Sprint 130.5 dodal kontrolowany zestaw narzedzi operatorskich:

```text
tools/profile_store_migration.py
doc/profile_store_migration_manual.md
```

Narzędzie obsluguje audit, backup, dry-run, migracje pojedynczego konta,
migracje wszystkich kont, weryfikacje, reconcile, resume, rollback i raport.
Komendy zapisujace wymagaja `--write` oraz manifestu backupu albo jawnej flagi
awaryjnej. Produkcyjna migracja nadal pozostaje decyzja operatorska i nie jest
uruchamiana automatycznie przez runtime gry.

Pola `profile_json` dla tych scope'ow pozostaja tylko compatibility mirror /
bootstrap cache:

* `aimed_target`,
* `current_position`,
* `curently_possition`,
* `operations`,
* `launch_queue`,
* `system_messages`,
* `apps`,
* `files.tools`,
* `storage_capacity`,
* `storage_used`,
* `storage_unit`,
* `hackcoins`.

Ewentualny `store_primary`, usuwanie legacy pol z `profile_json` i migracja
desktop settings pozostaja poza zakresem tej serii.

## Obecny model

Duza czesc runtime nadal dziala wedlug schematu:

```text
read full profile_json
-> mutate one scope
-> write full profile_json
-> return snapshot / delta
```

Ten model byl szybki do budowy gry, ale przy wielu workerach i rownoleglych
requestach tworzy ryzyko:

* pozny request zapisuje stary snapshot profilu,
* `aimed_target` wraca po zhakowaniu,
* `current_position` cofa sie po teleporcie,
* `actions_allowed` i `security` cofaja progress,
* kolejka aplikacji albo system messages moga zostac przetworzone wiecej niz raz,
* nawet duplicate/no-op moze kosztowac pelny sync.

Projekt ma juz czesc dobrych store'ow:

* `captured_targets`,
* `player_areas`,
* `territory_conflicts`,
* `reported_vulnerabilities`,
* `wallet_transactions`,
* `mail_store`,
* `game_state_deltas`,
* `response_incidents`,
* `response_npc_capsules`,
* `response_detection_candidates`,
* `response_warnings`,
* `ghostnetwork` tables.

Audyt dotyczy scope'ow, ktore nadal najczesciej siedza w profilu i sa gorace.

---

## Priorytet P0 - wyciagnac najpierw

### 1. Player Position Store

Zakres:

* `current_position`,
* aliasy pozycji uzywane przez mape/teleport/motocykl,
* timestamp ostatniego ruchu,
* zrodlo zmiany: `travel`, `teleport`, `blacknet`, `terminal`, `map`.

Dlaczego:

* pozycja zmienia sie czesto,
* teleport jest mala zmiana, a dzis moze byc nadpisany przez pozny zapis profilu,
* mapa, BlackNet, terminal i travel dotykaja tego samego stanu.

Proponowana tabela:

```text
player_positions(
  username primary key,
  lat real not null,
  lng real not null,
  source text,
  version integer not null,
  updated_at text not null
)
```

Zasada:

* profil moze miec kopie read-only/cache,
* zrodlem prawdy jest `player_positions`,
* zapisy pozycji musza byc monotoniczne po `version`.

Efekt:

* teleport nie cofa sie po ponownym otwarciu mapy,
* travel nie wymaga zapisu calego profilu,
* player actors moga czytac lekki store.

---

### 2. Aimed Target Runtime Store

Zakres:

* aktualny `aimed_target`,
* `security`,
* `actions_allowed`,
* `disarm_progress`,
* status: `aimed`, `in_progress`, `captured`, `cleared`,
* stabilny `target_key` / `target_id`,
* wersja runtime.

Dlaczego:

* to najczesciej cofajacy sie stan,
* miesza sie miedzy mapa, terminalem, desktopem i victim pickerem,
* pozny request moze przywrocic target po hacku,
* FE merge pomaga, ale nie rozwiazuje zapisu z backendu.

Proponowana tabela:

```text
player_target_runtime(
  username text not null,
  target_key text not null,
  target_json text not null,
  security_json text not null,
  actions_allowed_json text not null,
  disarm_progress integer not null default 0,
  status text not null,
  version integer not null,
  updated_at text not null,
  primary key(username)
)
```

Zasady:

* `security=false` nie moze wrocic na `true` dla tego samego targetu,
* `actions_allowed=true` nie moze wrocic na `false`,
* `disarm_progress` nie moze spasc,
* `captured/cleared` wygrywa ze starym `aimed`.

Efekt:

* koniec cofania kropek na belce,
* koniec powrotu zhakowanego celu jako namierzonego,
* wspolny target dla mapy, desktopu, terminala i victim pickera.

---

### 3. Operation Runtime Store

Zakres:

* `operations`,
* status operacji,
* remaining time,
* operation group,
* linked target,
* incident/risk state,
* history/cancel state.

Dlaczego:

* operacje sa juz osobnym runtime'em logicznie, ale nadal sa czesto zapisywane w
  profilu,
* centrum operacji, mapa, response network i aplikacje dotykaja tego samego
  stanu,
* anulowanie i finalizacja operacji powinny byc atomowe.

Proponowana tabela:

```text
player_operations(
  operation_id primary key,
  username text not null,
  target_key text,
  operation_type text not null,
  status text not null,
  operation_json text not null,
  risk_json text,
  version integer not null,
  created_at text not null,
  updated_at text not null
)
```

Dodatkowo:

```text
operation_events(
  event_id primary key,
  operation_id text not null,
  event_type text not null,
  payload_json text not null,
  created_at text not null
)
```

Efekt:

* lzejsze `/api/operations?summary=1`,
* mniej `refresh_and_persist_operations()` w profilu,
* lepsza idempotencja start/cancel/finalize,
* mniejsza szansa na dublowanie operacji.

---

### 4. App Launch / Command Receipt Store

Zakres:

* request id / flow id / idempotency key,
* app id,
* target key,
* source: `map`, `desktop`, `terminal`, `launch_queue`,
* status: `received`, `started`, `effect_applied`, `duplicate`, `failed`,
* response receipt.

Dlaczego:

* obecne dedupe zatrzymuje czesc objawow, ale duplicate moze dalej kosztowac
  ciezki request,
* najpierw trzeba rozpoznac duplicate, potem dopiero robic profil/sync,
* to laczy problem dubli z mapa, terminalem i desktopem.

Proponowana tabela:

```text
app_action_receipts(
  receipt_key primary key,
  username text not null,
  app_id text,
  action text,
  target_key text,
  source text,
  status text not null,
  response_json text,
  created_at text not null,
  updated_at text not null
)
```

Efekt:

* duplicate path moze konczyc sie przed `sync_session_profile()`,
* FE i BE dostaja jeden receipt,
* latwiej mierzyc: ile bylo prawdziwych dubli.

---

## Priorytet P1 - wyciagnac po P0

### 5. System Messages Store

Zakres:

* `system_messages`,
* read/consumed state,
* dedupe key,
* source event.

Dlaczego:

* toasty bywaja podwojne,
* `/system-messages` zapisuje profil po odczycie,
* wiadomość powinna byc efektem zdarzenia, nie kawalkiem profilu.

Proponowana tabela:

```text
system_messages(
  message_id primary key,
  username text not null,
  dedupe_key text,
  title text,
  body text,
  type text,
  source text,
  status text not null,
  created_at text not null,
  consumed_at text
)
```

Efekt:

* brak podwojnych toastow,
* odczyt system messages nie zapisuje calego profilu,
* latwe kasowanie/TTL.

---

### 6. Installed Apps / Tools Inventory Store

Zakres:

* `apps`,
* `files.tools`,
* app status,
* cooldown,
* generated app metadata.

Dlaczego:

* install/uninstall juz maja delty, ale nadal dotykaja `apps` i `files`,
* katalog narzedzi jest goracym miejscem przy gameplayu mapy,
* File Manager nie powinien byc zrodlem prawdy dla narzedzi.

Proponowane tabele:

```text
player_apps(
  username text not null,
  app_id text not null,
  app_json text not null,
  status text not null,
  version integer not null,
  updated_at text not null,
  primary key(username, app_id)
)

player_tool_files(
  username text not null,
  tool_id text not null,
  app_id text,
  tool_json text not null,
  updated_at text not null,
  primary key(username, tool_id)
)
```

Efekt:

* szybszy picker narzedzi,
* mniej pelnego `/api/profile`,
* prostsze recovery apps/storage.

---

### 7. Storage Runtime Store

Zakres:

* `storage_used`,
* `storage_capacity`,
* storage modifiers,
* over limit state.

Dlaczego:

* storage jest modyfikowany przez install/uninstall/GX/autosale/pro produkty,
* jest juz delta, ale zrodlo nadal czesto jest w profilu.

Proponowana tabela:

```text
player_storage(
  username primary key,
  capacity integer not null,
  used integer not null,
  unit text not null,
  modifiers_json text,
  version integer not null,
  updated_at text not null
)
```

Efekt:

* File Manager, GX i toolbar czytaja jeden lekki stan,
* mniej race przy install/uninstall i produktach storage.

---

### 8. Wallet Balance Store

Status: czesciowo istnieje.

Jest `wallet_transactions`, ale balans nadal jest czytany z profilu jako
`hackcoins`.

Rekomendacja:

* albo `hackcoins` zostaje cachem i jest odbudowywany z ledger/store,
* albo dodac `wallet_balances(username, balance, version, updated_at)`.

Efekt:

* przelewy, GX, Googleplex i konsekwencje response network nie zapisuja calego
  profilu dla samego HC.

---

## Priorytet P2 - zostawic na pozniej

### 9. Desktop Settings Store

Zakres:

* tapeta,
* pozycje ikon,
* fullscreen,
* map tile scheme.

To nie jest goracy runtime, ale jest dobrym kandydatem na osobna tabele, bo:

* ustawienia nie powinny zalezec od pelnego profilu,
* sa male i czesto zapisywane osobnym endpointem.

Niski priorytet, bo nie generuje glownych dubli.

---

### 10. Profile Identity / Progression Split

Zakres:

* nick,
* clan,
* level,
* respect,
* base stats,
* avatar.

To moze zostac w profilu najdluzej. Rzadko sie zmienia i nie jest glownym
zrodlem race condition.

---

## Czego nie wyciagac teraz

Nie migrowac wszystkiego naraz.

Na razie zostawic w profilu:

* dane statyczne postaci,
* kosmetyke profilu,
* stare pola kompatybilnosci,
* cache/recovery snapshots,
* rzadko zmieniane preferencje.

Profil powinien zostac jako:

```text
bootstrap / compatibility / recovery cache
```

a nie jako jedyny runtime store.

---

## Kolejnosc migracji

Najbezpieczniejsza kolejnosc:

1. `app_action_receipts` - early dedupe przed ciezka logika.
2. `player_target_runtime` - koniec cofania celu i kropek.
3. `player_positions` - koniec cofania teleportu/travel.
4. `player_operations` - odchudzenie operation center i incident runtime.
5. `system_messages` - koniec podwojnych toastow i zapisu profilu przy odczycie.
6. `player_apps` / `player_tool_files` - szybszy picker i terminal/desktop flow.
7. `player_storage`.
8. `wallet_balances`.
9. `desktop_settings`.

---

## Zasady migracji

Kazdy wyciagniety scope powinien miec:

* wlasny `version`,
* idempotentny zapis,
* `dedupe_key` dla eventow,
* recovery snapshot,
* delta event,
* brak pelnego `sync_session_profile()` na zwyklym odczycie,
* monotoniczny merge dla progressu,
* zgodnosc wsteczna z `profile_json` przez okres przejsciowy.

Najwazniejsza zasada:

```text
Nowy store jest zrodlem prawdy dla swojego scope.
profile_json moze byc tylko kopia kompatybilnosci.
```

---

## Najwiekszy spodziewany zysk

Najwiekszy zysk daja:

1. `app_action_receipts` przed `sync_session_profile()` - mniej kosztownych dubli.
2. `player_target_runtime` - mniej rollbackow celu.
3. `player_positions` - stabilny teleport/travel.
4. `player_operations` - odciazenie mapy i centrum operacji.
5. `system_messages` - mniej podwojnych toastow i zapisow profilu.

To sa scope'y, ktore bezposrednio odpowiadaja za obecne symptomy:

* duble aplikacji,
* spowolnienie po dedupe,
* cofanie targetu,
* cofanie pozycji,
* opoznione/podwojne toasty,
* ciezkie starty Ghosta.
