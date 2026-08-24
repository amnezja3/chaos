# Sprint 130.10 — Profile Integrity and Cross-Account Session Isolation

Data planu: 2026-08-21.

Status: `SPRINT 130.10 — COMPLETE`.

Formalne domknięcie: 2026-08-24. Automatyczne testy celowane i pełna regresja
zostały zakończone powodzeniem, a późniejszy manual A → B → A, test dwóch kart,
retest mapy oraz retest GhostNetwork potwierdziły izolację sesji i poprawne
działanie gameplayu. Etapowe statusy `READY` zachowane niżej opisują historię
wdrożenia i nie są aktualnymi blockerami.

Incydent źródłowy:
`doc/incidents/Incydent Trollu2 — utrata profilu, błędy sesji i plan odbudowy.md`.

## Cel

Najpierw zatrzymać klasę błędów, która mogła zamienić pełny profil w stan
startowy albo pomieszać stan dwóch kolejnych logowań. Sprint nie odbudowuje
jeszcze konta `Trollu2`. Przygotowuje bezpieczny runtime, w którym repair nie
zostanie ponownie nadpisany przez ten sam mechanizm.

Sprint ma dostarczyć:

- jednoznaczne rozróżnienie profilu poprawnego, niepełnego, uszkodzonego i
  nieistniejącego;
- blokadę zapisu fallbacku lub destrukcyjnego stale snapshotu;
- atomowy `last_known_good` dla pól pozostających w `users.profile_json`;
- ochronę pełnych zapisów przez revision/CAS;
- poprawny kierunek synchronizacji compatibility mirrorów;
- izolację kolejnych logowań przez unikalną generację sesji;
- odrzucanie spóźnionych odpowiedzi, delt i requestów poprzedniej sesji;
- telemetrykę i narzędzia pozwalające ustalić faktyczny przebieg incydentu.

## Zasady startowe

Przed pierwszą zmianą:

1. uruchomić `git status --short`;
2. przejrzeć bieżący diff oraz pliki untracked;
3. uznać zastane zmiany za należące do użytkownika i nie cofać ich;
4. sprawdzić realne call sites i source of truth przed zaprojektowaniem guardów;
5. do bramki evidence wykonywać wyłącznie odczyty oraz pracę nad read-only
   narzędziem diagnostycznym.

Sprint nie daje automatycznej zgody na commit, deploy, restart, migrację
serwerową ani mutację profilu.

## Dlaczego ten sprint jest przed odbudową

Audyt Etapu 1 potwierdził jeden deterministyczny destructive-write w kodzie,
który może wyjaśnić starter-like reset po trzecim filarze. Późniejszy exact-user
capture dla canonical loginu `trolu2` sklasyfikował korelację tej ścieżki z
incydentem jako `STRONGLY CONSISTENT / HIGH CONFIDENCE`:

1. `loads_json(..., {})` zaciera różnicę między błędem dekodowania JSON a
   prawidłowym pustym wynikiem.
2. Strukturalnie poprawny, lecz niepełny profil może zostać przyjęty przez
   `UserProfileManager`, uzupełniony template'em i zapisany.
3. `UserStore.save_profile()` zapisuje cały `profile_json` bez ogólnego CAS i
   bez niezależnego `last_known_good`; zachowuje tylko kilka specjalnie
   scalanych zakresów.
4. `apply_ghostnetwork_runtime_result()` buduje cache odbiorców z
   `list_profile_identities()`, czyli ze sparse identity projection. Jeżeli
   first activation reward zmieni taką projekcję, `UserStore.save_profile()`
   zapisuje ją jako cały profil. Późniejszy template sync uzupełnia brakujące
   pola wartościami startowymi. To jest potwierdzony defekt kodu; realne dane
   `trolu2` spełniają jego preconditions i pokazują zgodny phenotype.
5. `PlayerInventoryStore` może ponownie nałożyć aplikacje i narzędzia z
   wydzielonego store. Wyjaśnia to, dlaczego inventory mogło przetrwać reset
   reszty profilu, ale samo nie dowodzi przyczyny resetu.
6. `WalletBalanceStore.get_balance(..., fallback_profile=...)` traktuje
   rozbieżność z profilem jako powód do ustawienia salda store z profilu. Jeżeli
   profil jest fallbackiem, może to rozpropagować błędną wartość HC.
7. Frontend ma globalne cache, pollery, kursory delt, mapę w iframe i obiekty
   presentation state. Samo `session.clear()` na backendzie nie jest dowodem,
   że spóźniona odpowiedź rozpoczęta dla A nie zostanie użyta po zalogowaniu B.

Nie przypisujemy błędu rendererowi Leaflet. Evidence nie zawiera historycznego
LKG ani telemetryki konkretnej próby full-write, dlatego nie deklarujemy
absolutnej atrybucji pojedynczego zapisu mimo wysokiej zgodności korelacji.

## Macierz bieżących i docelowych źródeł prawdy

Audyt ma rozpocząć się od jawnej macierzy, a nie od dodania kolejnego merge'a:

| Zakres | Stan bieżący / właściwy source | Docelowa rola `profile_json` |
| --- | --- | --- |
| login i credentials | kolumny `users.username/password/salt` | nie wolno ich odtwarzać z backupu UI |
| trwałe pola niewydzielone | zwalidowany `users.profile_json` | zapis chroniony revision/CAS i LKG |
| aplikacje, narzędzia, storage | `player_apps`, `player_tool_files`, `player_storage` | compatibility mirror / bootstrap |
| Hack Coiny | obecnie hybryda: `WalletStore` zapisuje `profile_json`, a inne ścieżki używają `wallet_balances` + ledger | po audycie jeden atomowy writer; profil wyłącznie mirror |
| pozycja | `player_positions` | compatibility mirror |
| aimed target | `player_target_runtime` | compatibility mirror |
| operacje | `player_operations` | compatibility mirror |
| terytoria i ownership | Target Registry, `captured_targets`, ownership/CAS, `player_areas` i worker | profil nie jest źródłem polygonu |
| GhostNetwork | tabele `ghost_*` i append-only events | brak prawa do resetowania cyklu z profilu |

Jeżeli audyt realnych call sites wykaże inną obowiązującą relację, artefakt
zostaje poprawiony przed implementacją. Nie tworzymy drugiego source of truth.

Docelowo `wallet_balances` przechowuje bieżące saldo, a ledger jest append-only
źródłem audytu/idempotencji, nie drugim licznikiem salda. Ten status może zostać
ogłoszony dopiero po przeniesieniu lub spięciu wszystkich writerów HC.

## Etap 1 — forensics i mapa zapisów

Przed zmianami runtime:

1. zinwentaryzować wszystkie wywołania `UserStore.save_profile()`,
   `UserProfileManager.update_profile()` i bezpośrednie `UPDATE users`;
2. oznaczyć zapis pełny, częściowy, compatibility mirror i zapis wykonywany z
   kopii sesyjnej;
3. odtworzyć, które ścieżki trzeciego filaru dotykają profilu, walletu,
   progression receipts, Target Registry, territory jobs i eventów GN;
4. porównać `users.updated_at`, ledger walletu, progression receipts, historię
   Googleplexa, inventory store, target ownership, territory jobs i GN events;
5. oddzielić relację testera od faktów potwierdzonych w bazie lub logach;
6. nie logować pełnego profilu, credentials, tokenu sesji, dokładnych
   współrzędnych ani danych innych graczy.

Powstaje read-only narzędzie techniczne, preferencyjnie:

```text
tools/audit_profile_integrity.py
```

Minimalne tryby:

```text
status
audit --username <exact-login>
verify --username <exact-login>
```

Domyślnie narzędzie nie zapisuje bazy. Raportuje source, revision/checksum,
spójność store'ów, podejrzane spadki oraz brakujące dowody, ale nie emituje
sekretów ani pełnego JSON-u profilu.

Po przygotowaniu i lokalnym przetestowaniu narzędzia zatrzymać się ze statusem:

`READY FOR READ-ONLY SERVER FORENSICS — Sprint 130.10`

Użytkownik uruchamia audit/status na serwerze i przekazuje zredagowany wynik.
Dopiero jego analiza kończy evidence gate i pozwala rozpocząć runtime changes.
Jeżeli materiału historycznego nie da się odzyskać, luka pozostaje jawna, a
guardy muszą pokryć wszystkie nadal możliwe drogi destrukcyjnego zapisu.

Przed implementacją zapisać wynik bramki:

`FORENSICS CAPTURED — Sprint 130.10`

Status oznacza zabezpieczenie dostępnego snapshotu i rotujących logów przed
deployem/mutacją. Nie oznacza automatycznie potwierdzonego root cause; brakujący
materiał musi pozostać w evidence manifest.

### Wynik Etapu 1 — 2026-08-21

Zrealizowano:

- pełną mapę writerów profilu, walletu, inventory, territory i GN w
  `doc/audits/profile_integrity_writer_inventory.md`;
- read-only probe `tools/audit_profile_integrity.py` z trybami `status`,
  `audit` i `verify`;
- bezpieczny capture serwerowy w
  `doc/runbooks/profile_integrity_recovery_runbook.md`;
- rozróżnienie powodzenia probe, globalnego health runtime i integralności
  konkretnego konta;
- klasyfikację `valid`, `missing`, `invalid_json`, `invalid_schema` i
  `recovery_required` bez template sync i bez persistence;
- korelacje wallet ledger/balance, inventory stores, territory receipts/jobs,
  GN lifecycle/reward history oraz Googleplex evidence;
- złożony, zredagowany sygnał sparse activation overwrite, który łączy
  `ghost.part_activated`, applied `part_first_activated`, zapis profilu oraz
  zachowany trwały stan bez emitowania event/part/territory IDs;
- testy redakcji, query-only, braku mutacji pliku DB, schema drift, malformed i
  partial profile, wallet invariant, inventory normalization oraz GN reward
  projection.

Potwierdzony w kodzie destructive path:

```text
third pillar / territory publication
→ ghost.part_activated
→ first activation reward
→ sparse list_profile_identities cache
→ full UserStore.save_profile(sparse_profile)
→ template sync do wartości starter-like
```

Status dowodowy przed capture:

- `CONFIRMED CODE DEFECT` — ścieżka zapisu istnieje i jest destrukcyjna;
- korelacja konkretnego incydentu oczekiwała na exact-user capture;
- na tym etapie nie zmieniono runtime i nie wykonano repair.

### Wynik serwerowej bramki evidence — canonical login `trolu2`

Zredagowany pakiet capture z 2026-08-21, pobrany jako
`logs/chaos-13010-trolu2-20260821T184643Z.tar.gz`, przeszedł kontrolę
integralności plików. `status`, `audit` i `verify` wykonały się technicznie
poprawnie, a SQLite `quick_check` zwrócił `ok`. Kod wyjścia probe nie jest
jednak werdyktem integralności konta: materiał historyczny pozostaje częściowy,
ponieważ przed hardeningiem nie istniał profile revision ani zwalidowany LKG.

Stan bieżącego `profile_json` jest formalnie `valid`, lecz semantycznie
reset-like: `LVL 2`, `HC 1000`, `EXP 0.0`, `RSP 25`. Jednocześnie trwałe store'y
potwierdzają dojrzałe konto: 11 captured targets, 35 rekordów ownership,
60 capture receipts, 15 applied progression receipts, 113 wpisów wallet ledger,
5 produktów i 4 zakupy Googleplex, 578 historycznych operacji, 1000 zachowanych
delt oraz 1393 consumed system messages. Inventory store i profil są zgodne
dla 11 aplikacji i 11 narzędzi; to jest spodziewane po compatibility overlay i
nie unieważnia resetu pozostałych zakresów.

Korelacja GN wykazała dwa dokładne łańcuchy
`ghost.part_activated -> part_first_activated/applied`, zgodne exactly-once z
dwoma contributions i dwoma wpisami reward history. Ostatni łańcuch powstał
2026-08-21 około `13:24:45–13:25:01` i obejmuje event, reward, publication,
progression receipt oraz zakończony territory job. Wallet miał następnie saldo
dokładnie `1000` o `13:28:41`, a obecny profil został zapisany o `15:08:32`.

Disposition po capture:

- `CONFIRMED CODE DEFECT` — sparse GN projection może zostać zapisana jako
  pełny profil;
- `INCIDENT CORRELATION: STRONGLY CONSISTENT / HIGH CONFIDENCE` — realne dane
  spełniają preconditions defektu i pokazują odpowiadający mu reset-like
  phenotype przy zachowanych durable stores;
- brak write-attempt telemetry i pre-incident LKG nie pozwala nazwać
  atrybucji historycznej kryptograficznie rozstrzygniętą;
- `FORENSICS CAPTURED — Sprint 130.10`;
- Etap 2 może się rozpocząć, ale repair `trolu2` pozostaje zakazany do GO
  Sprintu 130.10 i osobnego Sprintu 130.11.

## Etap 2 — twarde rozróżnienie błędów od fallbacku

Odczyt profilu musi zwracać rozróżnialne wyniki:

```text
valid
missing
invalid_json
invalid_schema
recovery_required
```

Zasady:

- błąd JSON nie staje się `{}` udającym poprawny profil;
- profil bez wymaganej tożsamości i pól krytycznych nie przechodzi do
  automatycznej synchronizacji template;
- fallback może zasilić tylko ograniczony ekran błędu/recovery;
- fallback nie może być przekazany do `save_profile`, wallet reconciliation,
  inventory seed ani innego trwałego writer path;
- normalne konto startowe LVL 1 pozostaje legalne, jeżeli zostało utworzone
  kanoniczną ścieżką rejestracji;
- jawny reset administracyjny wymaga własnego reason/receipt i nie może być
  mylony z normalizacją profilu.

## Etap 3 — profile write guard, revision/CAS i LKG

Wszystkie pełne zapisy przechodzą przez centralne guarded write API. Writer
odczytujący profil otrzymuje `profile_revision`, zachowuje ją razem z lokalnym
snapshotem i przekazuje jako obowiązkowe `expected_revision` przy zapisie.
Guard nie może sam pobrać wyłącznie najnowszej revision i uznać starego
candidate'a za świeży.

Przed pełnym zapisem:

1. zwalidować tożsamość, schema version, typy i niezmienniki;
2. odczytać bieżącą revision/checksum;
3. sprawdzić, czy writer pracuje na tej samej revision;
4. wykryć destrukcyjny spadek wielu niezależnych zakresów;
5. potwierdzić, czy istnieje kanoniczne zdarzenie uzasadniające reset;
6. zachować ostatni poprawny stan, a dopiero potem zatwierdzić nowy;
7. zapisać nowy stan i revision atomowo.

Bezpośrednie `UPDATE users SET profile_json = ...` są zakazane poza jawnie
allowlistowanymi migracjami/recovery repository. Test kontraktu ma skanować
produkcyjne call sites. Legacy writery trzeba przenieść do guarded boundary,
nie tylko opakować logiem.

Preferowana jest additive migracja przechowująca co najmniej ostatni poprawny
snapshot i jego metadane. Dokładna schema wynika z audytu, ale kontrakt wymaga:

```text
username
profile_revision
schema_version
snapshot_json
checksum
source
created_at
validation_version
```

Snapshot:

- nie zawiera hasła, salt, cookie ani tokenu sesji;
- nie kopiuje polygonów jako alternatywnego źródła terytoriów;
- nie jest aktualizowany wadliwym candidate'em;
- zachowuje przynajmniej jedną ostatnią potwierdzoną wersję;
- ma checksum i pozwala wykazać, z jakiego stanu wykonano recovery.

CAS może użyć monotonicznej revision albo porównania poprzedniego serializowanego
stanu, jeżeli audyt pokaże, że jest to bezpieczniejsze dla bieżącej migracji.
Sam `updated_at` o rozdzielczości sekund nie jest wystarczającym tokenem CAS.

Additive migracja musi idempotentnie nadać schema/revision istniejącym poprawnym
profilom. Bootstrap:

- nie synchronizuje profilu z template'em;
- nie tworzy LKG z invalid/partial candidate'a;
- oznacza wadliwy rekord jako `recovery_required`;
- przy powtórnym uruchomieniu nie zwiększa revision ani nie dubluje snapshotu;
- ma test upgrade starej bazy bez nowych kolumn/metadanych.

Odrzucony zapis zwraca kontrolowany conflict/recovery result. Nie nadpisuje
profilu, LKG ani kanonicznych store'ów.

## Etap 4 — kierunek compatibility mirrorów

Po wydzieleniu zakresu obowiązuje kierunek:

```text
canonical store → read projection / profile mirror
```

Nie wolno automatycznie wykonywać:

```text
fallback profile → canonical store
```

W szczególności:

- rozbieżność `profile.hackcoins` nie może sama obniżyć `wallet_balances`;
- wallet mutation przechodzi przez ledger i dopiero potem aktualizuje mirror;
- legacy `WalletStore.transfer()` i `technical_transfer()` nie mogą nadal
  niezależnie zapisywać salda wyłącznie do dwóch pełnych `profile_json`;
- transfer, technical transfer, Googleplex, Ghost Exchange i pozostałe call
  sites muszą używać jednej atomowej granicy walletu albo zostać jawnie
  utrzymane w bezpiecznym trybie przejściowym; samo odwrócenie
  `get_balance(fallback_profile)` bez naprawy writerów jest niedopuszczalne;
- istniejące apps/tools nie mogą zostać usunięte przez niepełny profil;
- seed z legacy profile jest dozwolony tylko w jawnej migracji z receipt, nie
  podczas zwykłego odczytu profilu;
- territory, aimed target, position i operations nie są cofane przez stale
  pełny zapis.

## Etap 5 — izolacja sesji A → B → A

Po każdym poprawnym loginie/rejestracji backend czyści poprzednią tożsamość,
rotuje identyfikator serwerowej sesji w sposób wspierany przez Flask-Session i
tworzy losowy, unikalny `session_generation`. Nie wystarcza sama nazwa
użytkownika, ponieważ spóźniona odpowiedź z pierwszej sesji A mogłaby trafić do
późniejszej sesji A.

Generation należy do konkretnej uwierzytelnionej sesji przeglądarki, nie do
globalnego rekordu username. Poprawne równoległe logowanie tego samego gracza na
innym urządzeniu/przeglądarce zachowuje własną generation i nie jest
unieważniane przez login pierwszego urządzenia. Stara karta współdzieląca
obrócone cookie, ale wysyłająca poprzednią generation, zostaje odrzucona.

Generation musi objąć co najmniej:

- `/api/profile` i desktop boot;
- `/api/state/changes` i recovery scopes;
- map boot/snapshot, map actors i iframe bridge;
- launch queue, operations i system messages;
- GhostNetwork snapshot/delta;
- user-scoped mutacje wykonywane ze starej karty.

Powstaje kompletna allowlista/inventory endpointów user-scoped z informacją,
czy generation płynie w nagłówku, body, query czy response envelope. Nie wolno
chronić wyłącznie kilku endpointów wymienionych przykładowo powyżej.

`navigator.sendBeacon('/api/profile/desktop')` nie potrafi dodać własnego
nagłówka. Generation musi znaleźć się w walidowanym body beacona albo beacon
zostaje zastąpiony/wyłączony. Beacon bez generation nie może zapisywać profilu.

Backend odrzuca request z nieaktualną generacją. Dla mutacji sprawdza ją na
wejściu oraz ponownie bezpośrednio przed trwałym commit/CAS. Frontend przed
zastosowaniem odpowiedzi ponownie sprawdza generation i użytkownika.

Logout/login wykonuje centralny teardown:

- abort aktywnych fetchy i zatrzymanie pollerów;
- wyzerowanie `toolbarProfile` i request promise;
- wyzerowanie delta version, catch-up state i dedupe sets;
- usunięcie aimed target, operacji, launch queue cache i app state;
- zamknięcie/wyczyszczenie map iframe, markerów, GN layers i recovery promise;
- wyczyszczenie user-scoped `sessionStorage` oraz pamięci modułów;
- reset SFX dedupe bez odtwarzania historycznych eventów;
- `Cache-Control: no-store` dla odpowiedzi zawierających dane użytkownika.

Stara karta nie może po zmianie cookie wykonywać mutacji jako nowo zalogowany
użytkownik. Generation check musi obejmować również requesty zapisujące.

Nieudane logowanie nie może częściowo podmienić tożsamości. Zwykły failed login
nie modyfikuje działającej sesji. Jawny flow „zmień konto” najpierw wykonuje
pełny logout/teardown; jeżeli kolejne logowanie się nie uda, pozostaje sesja
anonimowa, nie mieszanina starej i nowej.

## Etap 6 — obserwowalność

Minimalny event zapisu profilu:

```text
profile.write_attempt
profile.write_applied
profile.write_rejected
profile.recovery_required
profile.lkg_created
session.generation_mismatch
```

Pola techniczne:

```text
username_hash
source
old_revision
candidate_revision
changed_scopes
decision
reason_code
session_generation_hash
request_id
```

Nie logować wartości pól profilu ani surowej generacji sesji.

## Wynik lokalnego hardeningu — 2026-08-21

Zaimplementowano lokalnie systemowy stop-the-bleed:

- guarded profile boundary z walidacją, checksum, monotoniczną revision,
  obowiązkowym CAS i atomowym `last_known_good`; fallback, partial profile i
  destrukcyjny candidate nie mogą zostać utrwalone zwykłą ścieżką;
- kanoniczny wallet i inventory z jednokierunkową projekcją do profilu,
  fail-closed dla niejednoznacznej migracji oraz stabilnymi kluczami
  idempotencji dla transferów i retry po crash/reload;
- `session_generation` z jednokierunkowym hashem, rotacją, wejściowym i
  precommit checkiem, ochroną odpowiedzi oraz frontendowym teardown pollerów,
  cache, map iframe, delt, operacji i SFX;
- sagę rewardów GhostNetwork: pending reward jest idempotentnie projektowany do
  guarded profilu, a ledger/reputation/eventy są finalizowane dopiero po
  poprawnym zapisie; retry nie dubluje RSP ani historii;
- bounded CAS retry dla worker-owned top-level territory projections, w tym
  rebuild, conflict finalize, encirclement i clear aimed target; usunięto też
  błąd niezdefiniowanego `profile_record` w ścieżce clear aimed target.

Zielone testy celowane na moment przekazania bramki:

- Target Registry / persistence: `221/221`;
- canonical wallet i runtime cutover: `30/30`;
- GhostNetwork reward/runtime/drop foundation: `26/26`;
- territory profile projection CAS: `3/3`.

Pełna regresja repozytorium zakończyła się wynikiem `956/956 OK`; sześć
kontraktów JS oraz pięć kontroli składni Node także przeszło. Nie wykonano
commita, deployu, restartu, manuala ani żadnej mutacji lub repair konta
`trolu2`; odbudowa pozostaje zakazana i należy wyłącznie do Sprintu 130.11 po
GO Sprintu 130.10.

## Testy automatyczne

Minimum:

1. invalid/truncated JSON daje `invalid_json`, nie fallback;
2. poprawny, ale niepełny profil nie jest automatycznie zapisywany jako konto
   startowe;
3. destrukcyjny candidate rich → starter jest odrzucony bez reset receipt;
4. legalna rejestracja LVL 1 przechodzi;
5. legalne progression, zakup i wydatek HC przechodzą;
6. zły candidate nie nadpisuje LKG;
7. snapshot LKG nie zawiera credentials;
8. stale writer przegrywa CAS;
9. równoległe częściowe zapisy nie cofają kanonicznych scope'ów;
10. fallback nie może zmienić walletu ani zasiać inventory;
11. transfer/technical transfer/Googleplex/Ghost Exchange używają spójnego
    salda, a wallet ledger pozostaje exactly-once;
12. opóźniony profil A po loginie B nie zmienia DOM/cache;
13. opóźniona delta/map snapshot A po loginie B jest odrzucona;
14. A → B → A nie akceptuje odpowiedzi pierwszej generacji A;
15. stara karta nie wykonuje mutacji jako użytkownik nowej sesji;
16. 401 i generation mismatch zatrzymują właściwe pollery;
17. mapa iframe, toolbar, aimed target, operations i apps pokazują jednego
    aktualnego użytkownika;
18. snapshot/recovery GN nie odtwarza SFX;
19. bieżąca regresja renderera GN nie zgłasza `Bounds.intersects` i nie zostawia
    częściowo dodanej warstwy;
20. test desktop i mobile obejmuje dwa konta oraz dwie karty;
21. dwie niezależne poprawne sesje tego samego konta na dwóch urządzeniach nie
    unieważniają się wzajemnie;
22. mutation rozpoczęta przed zmianą generation przegrywa także wtedy, gdy
    generation zmieni się tuż przed commit/CAS;
23. idempotentny bootstrap starej bazy nadaje revision tylko poprawnym profilom
    i nie zapisuje template ani LKG dla invalid/partial;
24. contract scan nie znajduje bezpośrednich produkcyjnych zapisów
    `users.profile_json` poza allowlistą migracji/recovery;
25. każdy user-scoped endpoint ma generation contract, również desktop beacon;
26. failed login i jawny failed account switch zachowują zdefiniowaną,
    niepomieszaną tożsamość;
27. deterministyczny scenariusz `trzeci filar → rebuild → GN lifecycle →
    profile projection` nie obniża profilu, nie cofa walletu/inventory i nie
    duplikuje eventu/SFX.

Sugerowane nowe testy:

```text
tests/test_profile_integrity_guard.py
tests/test_profile_recovery_snapshot.py
tests/test_session_generation_isolation.py
tests/js/test_session_generation_isolation.js
```

Regresja musi objąć także istniejące testy profilu, migration tool, walletu,
inventory, Googleplexa, Target Registry, territory, `test_target_persistence`,
map loader, delta/snapshot i GhostNetwork.

Kontrole końcowe:

```text
python -m py_compile <zmienione pliki Python>
node --check <zmienione pliki JavaScript>
git diff --check
```

## Bramka manualna po implementacji

Po evidence gate, implementacji lokalnej i zielonych automatach zatrzymać się
ze statusem:

`READY FOR MANUAL ACCOUNT-SWITCH TEST — Sprint 130.10`

Status jest bramką przekazania do użytkownika, nie wynikiem manuala ani GO.
Agent nie wykonał manualnego przełączenia kont, testu dwóch kart ani ścieżki
gameplayowej.

Przed manualem uruchomić monitor w osobnej sesji SSH:

```bash
cd ~/app/chaos
bash tools/monitor_sprint_130_10.sh
```

Skrypt pobiera bieżące `pm_out_log_path` i `pm_err_log_path` dla procesów
`chaos` oraz `chaos-territory-worker` bezpośrednio z `pm2 jlist`; nie zależy od
aktualnego ID procesu ani suffixu pliku logu. Dołącza również faktyczny
`CHAOS_BACKEND_DEBUG_LOG` weba (domyślnie `data/logs/backend_debug.log`), jeżeli
APP FLOW nie jest kopiowany na stdout. Zapisuje od chwili startu filtrowany
strumień profile/session/wallet/GN/territory, istotne requesty i pełne bloki
tracebacków. Każda linia dostaje czas UTC oraz nazwę pliku źródłowego.
Nagłówek i stopka zawierają status, PID oraz liczniki restartów PM2 przed i po
manualu. `Ctrl+C` dopisuje stopkę i wypisuje gotową ścieżkę pliku w
`logs/sprint-130-10-monitor-<UTC>-<PID>.log`.

Nie uruchamiać go przez `source` ani przez wklejanie treści do aktywnej powłoki.
Jeżeli potrzebny jest krótki kontekst sprzed startu, można jawnie ustawić np.
`CHAOS_MONITOR_START_LINES=50`; domyślnie monitor zaczyna od nowych linii.
Monitor jest zbiorem dowodów, nie samodzielnym werdyktem: oczekiwany logout
generuje `session.invalidated`, a celowo opóźniony request może poprawnie
generować `session.generation_mismatch`. Wallet exactly-once i stan trwały nadal
potwierdza końcowe `audit/verify`, nie sam access log `409`. Pole
`db_lock_metrics` w snapshotach PM2 pokazuje, czy `[DB_LOCK]` było w tym
przebiegu faktycznie włączone.
Plik ma prywatne uprawnienia (`umask 077`), ale przed dołączeniem go do
dokumentacji należy nadal zredagować nazwy graczy, target IDs i geometrię.

Użytkownik wykonuje manual:

```text
A login
→ profil / Googleplex / mapa
→ opóźniony request i delta
→ logout
→ B login
→ profil / Googleplex / mapa
→ logout
→ A login
→ desktop i mobile
```

Scenariusz należy powtórzyć również z dwiema kartami. Po każdej zmianie
toolbar, aplikacje, aimed target, operacje, markery, GN projection i profile
muszą należeć wyłącznie do bieżącej generacji.

Osobno potwierdzić, że dwie niezależne sesje tego samego konta na różnych
urządzeniach nadal działają, a teardown jednej nie czyści drugiej.

Na dedykowanym koncie testowym odtworzyć także oryginalną klasę ścieżki:

```text
trzeci filar
→ territory rebuild/publication
→ GhostNetwork lifecycle/delta
→ profil, wallet i inventory pozostają poprawne
```

Jeżeli układ mapy nie pozwala bezpiecznie odtworzyć dokładnej geometrii,
równoważny deterministyczny fixture serwerowy musi przejść przed GO. Nie używać
do tego uszkodzonego konta `Trollu2`.

Manual nie wykonuje repair konta `Trollu2`.

### Manual 2026-08-22 — blocker `/desktop` i disposition

Artefakt `logs/print-130-10-monitor-20260822T082135Z-1540468.log` potwierdził
cztery odpowiedzi `GET /desktop` ze statusem `500`, zero odpowiedzi `200` oraz
cztery identyczne błędy `TypeError: Object of type Undefined is not JSON
serializable` dla `templates/linux.html` i pola `session_generation`.

Przyczyną nie była druga ścieżka renderowania template. Repo zawiera dokładnie
jeden `render_template("linux.html", ...)` w endpointcie `/desktop`. Traceback
oznaczał ramkę jako `desktop` z `run.py:17954`, ale tekst tej linii odczytany z
pliku na dysku (`if token is None`) należał już do innej funkcji. To dowodzi, że
proces Gunicorna wykonywał starszy code object po podmianie plików. Jednocześnie
nowy `linux.html` był już widoczny i wymagał kontekstu Sprintu 130.10. Snapshoty
PM2 przed i po manualu miały ten sam PID weba, `restart_time=11` i brak nowego
restartu. Disposition: `CONFIRMED STALE WEB PROCESS / MIXED DEPLOY STATE`.

Endpoint pobiera teraz `session_generation` jawnie przed renderem przez
kanoniczny `session_generation_client_context()` i przekazuje gotowy kontekst
do `linux.html`. Nie dodano fallbacku `default/null` w template. Regresja wymaga
`200` oraz zgodnego generation, query tokenu, username i nagłówka dla:

```text
A login → /desktop → logout
→ B login → /desktop → logout
→ A login → /desktop
```

oraz dla świeżej sesji tworzącej nowe konto i otwierającej `/desktop`. Testy nie
używają ani nie naprawiają profilu `Trollu2`; profile i user store są mockowane,
a durable session lineage działa na izolowanej tymczasowej bazie.

Po prawidłowym zatrzymaniu i uruchomieniu procesów ujawnił się drugi przypadek:
przeglądarki zachowały pre-rollout cookie z `user`, ale bez lineage/generation.
Chroniony `POST /` zwracał wtedy `generation_bootstrap_required` przed wywołaniem
uwierzytelnienia. Taka niepełna sesja jest teraz kanonicznie unieważniana i ma
obracany SID przed kontynuacją bieżącego credentialed login/register. Dopiero
udane uwierzytelnienie tworzy nowe lineage/generation. Kompletna bieżąca sesja
nadal wymaga poprawnej generation i jawnego logoutu przed zmianą konta.

Regresja session store/precommit/isolation oraz desktop boot zakończyła się
wynikiem `52/52 OK`; celowany `py_compile` i `git diff --check` również przeszły.

### Manual 2026-08-22 — blocker mapy po account switch

Właściwy manual został poprawnie przerwany po selektywnym `500` endpointu
`GET /api/map/player-actors` oraz braku menu pustego pola nad warstwami
terytorium. Evidence:
`logs/sprint-130-10-monitor-20260822T090144Z-1542232.log`.

Traceback wskazał dokładną przyczynę backendową: projekcja aktora zakładała, że
historyczne pole profilu `fraction` zawsze jest obiektem i wykonywała
`(fraction or {}).get("role")`. Jeden z widocznych dla testowanego gracza
profili miał zgodną z legacy danymi postać tekstową. Wyjątek jednego aktora
przerywał cały snapshot. To wyjaśnia selektywność kont: błąd występował tylko u
odbiorców, dla których dany aktor przechodził visibility projection. Dwa `409`
zarejestrowane już po logout były oczekiwanym odrzuceniem odpowiedzi starej
lineage (`durable_response_lineage_revoked`) i nie są błędem endpointu.

Odczyt profilu obsługuje teraz obie historyczne reprezentacje `fraction` bez
zapisu lub migracji profilu. Wspólny normalizator chroni zarówno pełny snapshot
`player-actors`, jak i publikację delty aktora, rozpoznanie klanu/profesji oraz
kontrolę dozwolonych frakcji.

Brak menu był osobnym błędem presentation contract. Warstwy polygonów opierały
się wyłącznie na `bubblingMouseEvents`, którego zachowanie `contextmenu` nie jest
jednolite pomiędzy rendererami SVG i zdarzeniami dotykowymi. Każda kanoniczna
warstwa pola, konfliktu, frontu i multi-conflictu przekazuje teraz jawnie swój
Leaflet `contextmenu` do zwykłego menu pustego pola, używając bezpośrednio
`containerPoint` i `latlng`. Markery interaktywne zachowują własne menu.

Regresja obejmuje scalar/dict `fraction`, pełny endpoint aktorów, deltę/read
path oraz jawne przekazanie menu dla wszystkich rodzajów geometrii. Nie
zmieniono żadnego profilu, terytorium ani danych `Trollu2`.

#### Pierwszy retest poprawki mapy

Retest bez monitora serwerowego potwierdził, że `/api/map/player-actors`
zwraca poprawny payload i frontend dochodzi do `render complete`; poprzedni
`500` nie powtórzył się. Ujawnił jednak dalszy blocker presentation: na kontach,
które wcześniej nie dostawały menu pola, event nad polygonem otwierał menu
jednego z przejętych markerów (`Zabezpiecz / Porzuć`).

Kod markerów zwykłych miał częściową kontrolę DOM rect, ale przejęte i legacy
DOM markery ufały samemu faktowi otrzymania `contextmenu`. Element potomny
ikony mógł przechwycić event poza rzeczywistą ikoną i nadpisać menu pola.
Wszystkie target/captured/legacy handlery weryfikują teraz trafienie względem
projekcji współrzędnych markera oraz ograniczonego rozmiaru i anchora ikony.
Event poza tym hitboxem jest jawnie przekazywany do menu pustego pola. Wizualny
overflow emoji nie jest interaktywny, więc nie rozszerza obszaru trafienia.

Jedyny błąd konsoli w retescie był niezależnym `404` dla historycznej ścieżki
`/static/images/default_avatar.png`. Renderer mapy mapuje ją bez zapisu profilu
na istniejący `/static/images/avatar-default.jpg` i ma ten sam fallback dla
innych niedostępnych avatarów.

Regresja po follow-upie: map cutover `31/31`, captured menu/map loader/GN layer
`78/78`, Target Registry/persistence `221/221`, behawioralny test Node hitboxu
oraz `git diff --check` — OK.

#### Końcowy retest bramki mapy

Użytkownik potwierdził na kontach testowych:

- menu pustego pola działa nad terytoriami;
- bezpośrednie trafienie w marker nadal otwiera właściwe menu markera;
- aktorzy są renderowani poprawnie po zmianach kont;
- części GhostNetwork są widoczne i poprawnie prezentowane na każdym testowanym
  koncie.

Werdykt tej bramki: `MAP BLOCKER RETEST PASSED`.

To odblokowuje rozpoczęcie pełnego manuala Sprintu 130.10, ale nie jest jeszcze
końcowym GO integralności profilu i izolacji sesji.

#### Manual izolacji dwóch sesji przeglądarki

Manual z monitorem
`logs/sprint-130-10-monitor-20260822T113207Z-1548831.log` potwierdził właściwe
zachowanie granicy sesji:

- aktywna gra w pierwszej karcie nie ujawniła danych drugiego konta;
- próba zalogowania drugiego konta w tej samej sesji cookie została trzykrotnie
  odrzucona jako `POST / -> 409`, `reason=missing_generation`;
- niezależny profil/sesja przeglądarki mógł równolegle uruchomić drugą grę;
- aktywne generacje nadal otrzymywały odpowiedzi `200`; odrzucenia starych
  odpowiedzi po logout miały oczekiwane przyczyny
  `durable_precommit_rejected` / `durable_response_lineage_revoked`;
- monitor zawiera `370` odpowiedzi `200`, `6` kontrolowanych odpowiedzi `409`,
  zero `500`, zero tracebacków, zero `OperationalError`, zero
  `database is locked` i zero restartów obu procesów;
- konsola przeglądarki nie pokazała podejrzanych błędów, a użytkownik potwierdził
  brak przecieków między kontami.

Blokada była poprawna, lecz nawigacja formularza HTML pokazywała surowy payload
JSON. Warstwa odpowiedzi rozróżnia teraz dokument HTML od API/fetch: dokument
dostaje ekran `CHAOS // SESSION GATE` ze statusem `409`, natomiast API, polling i
pozostałe fetch zachowują dotychczasowy kontrakt JSON. Poprawka nie wykonuje
redirectu, nie bootstrapuje generacji i nie osłabia fail-closed isolation.

Regresja obejmuje ekran HTML, zachowanie aktywnej pierwszej sesji, brak wycieku
surowej generation w dokumencie, JSON dla `/api/*` oraz JSON dla historycznych
endpointów pollingowych bez prefiksu `/api/`. Pełny
`tests.test_session_generation_isolation`: `30/30 OK`; łącznie store, precommit
i isolation: `42/42 OK`. `py_compile` i `git diff --check`: OK.

Wynik bramki: `SESSION ISOLATION MANUAL PASSED`. Sprint nadal wymaga pozostałych
punktów Etapu 7 i końcowego `status/audit/verify`, zanim otrzyma pełny werdykt GO.

Retest po wyczyszczeniu cache potwierdził poprawne wyświetlenie bramki i dalszy
brak przecieków. Mylący przycisk wywołujący `window.close()` zastąpiono
nieinteraktywnym komunikatem `ZAMKNIJ TĘ KARTĘ RĘCZNIE`; przeglądarka nie zawsze
pozwala stronie zamknąć kartę otwartą przez użytkownika.

#### Selektywny brak warstwy GN na mobile dużego konta

Kolejny manual ujawnił brak warstwy GhostNetwork wyłącznie na mobilnym widoku
konta `main`. Ten sam viewer działał na desktopie, a konta `robot`, `neo1` i
`iasny` działały także na mobile. `main` ma ciężki wariant mapy: efektywna
kontrola `63 798 275 m²`, 5 klastrów i łączna powierzchnia `445 778 521 m²`.

Przyczyna leżała w lifecycle opcjonalnego bootu, nie w visibility ani danych GN.
`loadGhostNetworkSnapshot()` zwracał `false` po skip/abort/timeout, lecz
`bootStep` oznaczał wtedy opcjonalny scope jako załadowany. Parametr `retries`
również działał tylko dla kroków krytycznych. GhostNetwork nie ma ciężkiego
okresowego pollera, więc jednorazowe niepowodzenie po kosztownym renderze mapy
pozostawiało warstwę pustą.

Minimalna poprawka:

- wynik `false` nie oznacza już scope jako załadowanego;
- jawny `retries` działa także dla kroku opcjonalnego;
- wyłącznie boot GN ma dwa ograniczone ponowienia; nie dodano stałego pollingu;
- skip/abort zapisuje diagnostyczne `[ghostnetwork] snapshot deferred`;
- cache key skryptu mapy zmieniono na `mobile-boot-retry-7`.

Regresja zachowania odtwarza `false`, `false`, `true` oraz trwałe niepowodzenie,
sprawdzając liczbę prób i `loadedScopes`. GN/map/read-path/territory:
`55/55 OK`; renderer GN i map target hitbox Node: OK; `node --check` oraz
`git diff --check`: OK.

Status: `READY FOR MOBILE MAIN GN RETEST`.

#### Regresja latency po retry GhostNetwork

Po wlaczeniu ograniczonego retry ujawnil sie drugi problem goracej sciezki.
`/api/ghostnetwork/snapshot` pobieral pelny `profile_json` przez
`load_profile_readonly()`. Dla duzego konta oznaczalo to pelna deserializacje,
walidacje checksum/schema, deepcopy, normalizacje runtime i overlay wszystkich
canonical stores tylko po to, aby odczytac klan oraz profesje viewera. Nieudany
boot mogl powtorzyc ten koszt do trzech razy.

Endpoint korzysta teraz z `UserStore.get_profile_identity()`: waskiej projekcji
SQL zawierajacej tylko login, pola klanu i profesji. Projekcja jest fail-closed:
wymaga poprawnego JSON object oraz durable metadata `valid`, dodatniej rewizji i
checksumy. Nie korzysta z pelnego profilu, runtime overlay ani session cache i nie
mutuje danych. Retry pozostaje ograniczone, ale powtarza juz tylko lekki odczyt.

Regresja: 77 testow endpointu, identity store, GN visibility/publication/map oraz
session isolation przeszlo. Testy obejmuja zakaz `load_profile_readonly()` w
snapshocie, brak ciezkich pol w projekcji oraz kontrolowane fail-closed dla
uszkodzonych metadata i malformed JSON. Renderer Node, `py_compile` i
`git diff --check`: OK.

Status: `READY FOR MOBILE MAIN PERFORMANCE + GN RETEST`.

## Etap 7 — po manualu

Na podstawie wyniku użytkownika:

1. skorelować generation mismatch, request IDs i profile-write decisions;
2. naprawić wyłącznie bugi mieszczące się w integralności/sesji;
3. powtórzyć testy concurrency, A/B i regresję dotkniętych systemów;
4. sprawdzić `status/audit/verify` na serwerze bez mutowania profilu;
5. potwierdzić brak rejected-write storm, stale pollerów i danych innego konta;
6. zaktualizować incident root-cause disposition do `CONFIRMED` albo
   `UNCONFIRMED BUT CONTAINED`, zawsze z listą dowodów i luk;
7. dopiero wtedy wydać GO/NO-GO.

Pojedyncze poprawne przełączenie kont nie wystarcza do GO, jeżeli writer guard,
LKG lub mutacje starej karty nie są zweryfikowane.

## Dokumentacja i handoff operatorski

Sprint aktualizuje:

- dokument incydentu;
- `doc/history/game_play_180726.md`;
- `doc/history/project_journal.md`;
- `doc/audits/profile_store_extraction_audit.md`;
- `doc/runbooks/profile_integrity_recovery_runbook.md` z rzeczywistymi komendami
  read-only `status/audit/verify`; migracja, deploy i manual A/B dostaną osobny
  handoff dopiero po zamknięciu evidence gate.

Handoff ma podać dokładne komendy dla wykrytego ecosystemu/procesów, ale nie
wykonuje deployu ani restartu za użytkownika. Do repo nie trafia pełny profil,
cookie, session ID/generation, baza serwerowa ani niezredagowany log graczy.

## Poza zakresem

- odbudowa progression i terytoriów `Trollu2` — Sprint 130.11;
- przebudowa całego profilu na nowe tabele;
- zmiana mechaniki GhostNetwork, drop chance lub bieżącego cyklu;
- kolejny renderer mapy;
- optymalizacja niezwiązana z integralnością lub izolacją sesji.

## Definition of Done

Sprint dostaje GO, gdy:

- niepoprawny/niepełny profil nie może stać się trwałym fallbackiem;
- destrukcyjny stale writer przegrywa przed zapisem;
- LKG powstaje tylko z poprawnego stanu i może zostać zweryfikowany;
- compatibility mirrory nie nadpisują kanonicznych store'ów fallbackiem;
- wszystkie full-profile writery przekazują `expected_revision`, a produkcyjne
  bezpośrednie `UPDATE users.profile_json` poza allowlistą nie istnieją;
- bootstrap istniejących profili/revision/LKG jest idempotentny i fail-closed;
- każda odpowiedź i mutacja user-scoped jest związana z aktualną generacją;
- manual A → B → A i dwie karty nie pokazują ani nie zapisują cudzego stanu;
- ścieżka trzeciego filaru/rebuild/GN nie obniża ani nie miesza profilu;
- testy profilu, walletu, inventory, mapy, delty, GN i territory są zielone;
- incident evidence oraz runbook integralności zostały zaktualizowane;
- root-cause disposition brzmi `CONFIRMED` albo
  `UNCONFIRMED BUT CONTAINED`, nigdy samo nieopisane `UNCONFIRMED`.

Werdykt:

`GO — Sprint 130.10 profile integrity and session isolation validated`

albo:

`NO-GO — Sprint 130.10 still has profile integrity or session isolation blockers`

Nie commitować, nie deployować i nie wykonywać mutującego recovery bez osobnego
polecenia użytkownika.

## Formalne zamknięcie — 2026-08-24

`SPRINT 130.10 — COMPLETE`

Końcowy audit dokumentacyjno-kontraktowy potwierdził:

- guarded profile writes z revision, checksum, CAS i atomowym LKG;
- session generation dla niezależnych lineage, ochronę odpowiedzi oraz
  wejściowy i transakcyjny precommit guard mutacji;
- canonical wallet i inventory z jednokierunkową projekcją do profilu;
- brak nieallowlistowanych runtime writerów `users.profile_json`;
- manualny brak przecieków pomiędzy kontami i kartami;
- poprawne działanie mapy, actorów i warstwy GhostNetwork po zmianach kont;
- brak pozostawionego blockera integralności profilu lub izolacji sesji.

Regresje hot path ujawnione po pierwotnym hardeningu zostały domknięte przez
Sprinty 130.10.1 i 130.10.2. Obowiązującą bramką dla kolejnych prac pozostaje
`doc/architecture/profile_hot_path_contract_130_11_plus.md`.

Werdykt końcowy:

`GO — Sprint 130.10 profile integrity and session isolation validated`
