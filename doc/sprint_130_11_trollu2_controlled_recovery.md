# Sprint 130.11 — Trollu2 Controlled Profile and Territory Recovery

Data planu: 2026-08-21.

Status: `NO-GO — ROLLBACK VERIFIED; CURRENT-WORLD GEOMETRY CAPTURE REQUIRED`.

## Existing geometry / level scaling diagnosis

Diagnoza jest wyłącznie read-only. Dedykowany
`tools/audit_trollu2_geometry.py` otwiera bazę przez `mode=ro`, ustawia
`PRAGMA query_only=ON`, nie importuje runtime store'ow i korzysta bezpośrednio
ze wspólnego kontraktu `territory_geometry.py`, którego używa worker. Raport
wypisuje bez pełnych payloadów wszystkie captured/stationary targets, canonical
pillars/inners i ownership entries wraz z ID, pozycją, ownerem, provenance i
timestampami. `database_writes=0`, `ghostnetwork_queries=0`.

### Dowód historyczny i stan snapshotu

Zabezpieczony evidence capture z `2026-08-21T18:46:44Z` potwierdza:

- `captured_targets=11`, w tym `stationary=10` i `generated=1`;
- `ownership_entries=35`, ostatnia aktualizacja ownership
  `2026-08-14T14:23:50`;
- `player_areas` nie miało ani jednego aktywnego obszaru;
- captured marker został zaktualizowany jeszcze
  `2026-08-21T13:25:41`, a profil po utracie miał LVL 2.

To bezpośrednio potwierdza sekwencję: canonical markery przetrwały, natomiast
aktywna geometria zniknęła. Evidence jest zanonimizowane i nie zawiera
wierzchołków ani area IDs, dlatego samo nie dowodzi, kto zajmował dany obszar
przed incydentem.

Lokalny pełny snapshot produkcyjny `848560128 B`, wykonany już po incydencie,
zawiera `captured=10`, `stationary=9`, `generated=1`, `ownership=35`, w tym 15
rekordów sklasyfikowanych jako pillar i 4 jako inner. Różnica jednego captured
targetu wobec evidence jest dodatkowym powodem, by finalną decyzję oprzeć na
świeżym raporcie live po rollbacku, a nie na lokalnej kopii.

### Symulacja canonical worker geometry

Te same dziewięć stationary targets z lokalnego snapshotu daje:

| Level | Próg połączenia | Komponenty | Aktywne obszary | Powierzchnia | Kolizje |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2 | 600 m | 8 | 0 | 0 m2 | 0 |
| 25 | 7500 m | 2 | 2 | 2638470.30 m2 | 2 |
| 26 | 7800 m | 2 | 2 | 2638470.30 m2 | 2 |
| 50 | 15000 m | 2 | 2 | 2638470.30 m2 | 2 |

Przy LVL 2 jedyną relacją jest para markerów; żaden komponent nie ma
trzech punktów, więc closed territory nie powstaje. Przy LVL 25 domykają się
dwa komponenty i stan pozostaje identyczny dla 26 oraz 50:

- Tokio: 3 markery, `552190.12 m2`, bbox
  `35.3647239..35.3725165 / 139.4461742..139.4613615`, bez kolizji w tym
  snapshotcie;
- Warszawa: 6 markerów, `2086280.18 m2`, bbox
  `52.1485961..52.1710090 / 20.8891974..20.9114969`.

Wzrost LVL rzeczywiście reaktywuje stare pola, ale istotne przejście następuje
już między LVL 2 a LVL 25. LVL 50 nie tworzy na tym zestawie większej
geometrii niż historycznie zbliżone LVL 25/26. Nazwa blockera
`level_50_existing_geometry_conflict` oznacza, że planner sprawdził istniejące
markery przy docelowym recovery level, a nie że konflikt pojawia się dopiero
między 26 a 50.

Warszawski obszar przecina w lokalnym snapshotcie:

- `neo1`, area `448377`, `601722.11 m2`, utworzony
  `2026-08-22T13:49:01`, overlap bbox względem obszaru Trollu2 `0.265829`;
- `iasny`, area `448386`, `1174959.44 m2`, utworzony
  `2026-08-22T16:20:03`, overlap bbox `0.266834`.

W obu przypadkach wierzchołki każdego poligonu wchodzą do drugiego. Oba
przeciwne obszary powstały po cutoffie incydentu `2026-08-21T15:08:32`, zatem
klasyfikacja lokalnego snapshotu brzmi `A+B`: obniżony level wyłączył stare
połączenia, a w czasie ich nieaktywności obecny świat zajął tę przestrzeń.
Wcześniejszy live apply wskazał zamiast nich `pies1`; po rollbacku dokładni
aktualni przeciwnicy i area IDs muszą zostać odczytani ponownie. Nie wolno
przepisać wyniku lokalnego snapshotu na live.

### Tokio i rozdzielenie dwóch blockerów

Stary podpisany plan przesunął osiem bonusowych filarów Tokio o `3000 m` na
północ. Dawne `collisions=[]` dotyczyło jednak kandydata ocenianego niepełnym
kontraktem. Obecne `collision_findings()` buduje jeden preview ze starych i
bonusowych markerów, dlatego etykieta `city_collision:Tokio` może zawierać
kolizję starego komponentu warszawskiego i nie dowodzi sama w sobie, że koliduje
bonusowy ring w Tokio.

Nowy raport pokazuje osobno `bonus_only_level_50` oraz
`combined_existing_plus_bonus_level_50`, korzystając z targetów dokładnie ze
starego planu. Dopóki ten raport nie zostanie uruchomiony na bieżącej bazie i
starym planie, `city_collision:Tokio` pozostaje osobnym, nierozstrzygniętym
blockerem; kolejne arbitralne przesunięcie jest niedozwolone.

### Ocena modeli recovery

1. **A — LVL 50 + aktualna geometria:** najmniej zmian architektonicznych, ale
   obecnie `NO-GO`, ponieważ naturalny rebuild historycznych markerów tworzy
   konflikty z aktualnym światem.
2. **B — progression oddzielony od historycznego reach:** aktualna architektura
   tego naturalnie nie wspiera. Worker przekazuje jeden level gracza do wszystkich
   stationary targets. Per-player/per-marker historyczny level stałby się nowym
   source of truth, który każdy przyszły rebuild musiałby respektować. Nie jest
   to bezpieczny lokalny wyjątek Sprintu 130.11.
3. **C — audytowalny canonical cleanup starych filarów + nowy bonus:** jedyny
   wariant, który zachowuje jeden geometry source of truth i może pogodzić
   `LVL 50 / RSP 2560 / HC 250000` z aktualnym światem. Nie może oznaczać
   bezśladowego DELETE. Ewentualna przyszła implementacja musi zachować immutable
   listę/receipt wycofanych markerów, jawnie zakończyć ownership/captured
   lifecycle, wykonać canonical rebuild, a dopiero potem zaplanować bonus w
   wolnym miejscu. Na etapie diagnozy nic nie jest wycofywane.

`RECOMMENDED FINAL RECOVERY STRATEGY`: wariant C jako osobny, zatwierdzony plan
recovery, po potwierdzeniu semantyki zakończenia historycznego ownership. Wariant
B jest odrzucony jako trwały specjalny kontrakt per-player. Wariant A pozostaje
zablokowany, dopóki symulacja na bieżącym świecie pokazuje jakąkolwiek kolizję.

Każdy przyszły plan musi zapisać fingerprint/revisions wykorzystanego current
world projection, a atomowy apply musi ponownie policzyć pełną geometrię i
kolizje pod writer boundary bezpośrednio przed grantem. Zmiana świata pomiędzy
planem i apply daje stale-plan `NO-GO`, nigdy automatyczny konflikt.

Aktualny werdykt na podstawie evidence oraz pełnego lokalnego snapshotu:

`DIAGNOSIS CONFIRMED — BOTH LEVEL SCALING AND WORLD EVOLUTION CONTRIBUTE`

Finalna lista live obiektów, przeciwników i diagnoza bonus-only pozostaje bramką
read-only przed projektowaniem naprawy. Do tego czasu: bez apply, settlementu,
walletu, LKG, zmian targetów i zmian GhostNetwork.

## Server apply finding i korekta — 2026-08-23

Pierwszy operatorski apply zatrzymał się przed settlementem, ale ujawnił dwie
niezgodności planera z runtime:

- plan sprawdzał wyłącznie obwiednię ośmiu nowych filarów. Worker odbudował
  wszystkie istniejące stationary targets konta przy odzyskanym poziomie 50 i
  utworzył trzy kanoniczne obszary; jeden z nich utworzył konflikt
  `territory_conflict_26409afa48525665` z `pies1`;
- level step zapisał revision 2, a conflict finalizer wykonał kanoniczną
  projekcję `hacked/captured_targets_source/territory_stats/exp`, podnosząc profil
  do revision 3. Receipt nadal wskazywał revision 2 i prawidłowo blokował dalszy
  settlement.

Nie wykonano RSP, wallet settlementu ani promocji LKG. GhostNetwork nie jest
przedmiotem tej poprawki.

Korekta wprowadza jeden lekki, współdzielony `territory_geometry.py`. Zarówno
`TerritoryStore`, jak i recovery planner używają teraz tego samego kontraktu:
connected groups, próg `300 m × level`, triangle clustering, fallback hull oraz
ten sam test przecięcia polygonów. Preview obejmuje stare i nowe filary, jest
checksumowany w planie i ponownie liczony przed apply.

Read-only preview na snapshocie serwerowym wykazał dodatkowy fakt: nawet bez
ośmiu nowych filarów istniejące targety `trolu2` po zmianie levelu z 2 na 50
tworzą dwa obszary, z których warszawski przecina terytoria innych graczy. Nie
jest to problem możliwy do usunięcia relokacją bonusu Tokio. Nowy planner zwraca
więc `level_50_existing_geometry_conflict` i `NO-GO`, zamiast podpisać plan, który
worker zamieni w konflikt.

Rollback obecnego częściowego apply:

- akceptuje revision 3 tylko wtedy, gdy z before-manifestu, canonical stores,
  zakończonego recovery joba i dozwolonych czterech pól można odtworzyć dokładnie
  aktualny checksum; wymaga dokładnie `revision + 1` i niezmienionego walletu;
- każdą inną zmianę profilu traktuje jako późniejszy gameplay i odmawia;
- usuwa wyłącznie granty posiadające exact `recovery_plan_id`, przywraca profil
  przez CAS i zachowuje wallet/LKG w stanie sprzed apply;
- identyfikuje błędny konflikt po source, czasie, aktorze oraz nowych area IDs lub
  recovery targets; captured pillar, action receipt albo aktywny multi-engagement
  blokuje rollback;
- zachowuje historię konfliktu i kieruje go do kanonicznej publikacji
  `no_active_fronts`; `verify-rollback` wymaga statusu resolved/closed, zera
  aktywnych frontów oraz terminalnych jobów;
- recovery-owned conflict i rollback publication są profile-neutralne dla obu
  uczestników. Nie mogą ponownie podbić revision profilu przeciwnika ani subjectu,
  uruchomić encirclement ani utworzyć reward/progression receipt za techniczne
  zamknięcie konfliktu.

`apply` nie może wykonać final settlementu, jeżeli istnieje otwarty konflikt ze
source `sprint_130_11_recovery`. CLI `verify` wymaga teraz signed
`--before-manifest`, aby rozpoznać dokładną projekcję workera i jednocześnie
raportować konflikt jako blocker.

Pierwszy serwerowy preflight poprawionego rollbacku ujawnił jeszcze różnicę
rekonstrukcji `hacked`: conflict finalizer korzysta z
`TerritoryStore.list_captured_targets()`, który sortuje po `captured_at` i
normalizuje `lat/lng/lon`, podczas gdy narzędzie porównywało surowe
`target_json` sortowane po ID. Receipt revision 2 nadal jest odtwarzany starym,
dokładnym kontraktem apply, natomiast oczekiwana revision 3 korzysta teraz z
osobnego runtime projection identycznego z workerem. Przy odmowie verify zwraca
wyłącznie nazwy różniących się pól oraz hashe/counts bez ujawniania profilu.

Drugi serwerowy preflight zawęził różnicę do top-level `targets`. Jest to
canonical overlay wykonywany automatycznie przez `patch_profile_guarded`: jeżeli
istnieje receipt `player_marked_target_state`, worker zastępuje legacy
`profile_json.targets` aktywnymi rekordami `player_marked_targets`, sortowanymi
po `created_at, target_key`. Recovery rekonstruuje teraz ten sam warunek, filtr
`status='active'`, parser JSON i porządek. `targets` pozostaje częścią profilu i
checksumu. Diagnostyka raportuje count, SHA, stabilne ID i kolejność oraz dla
zmienionych wpisów wyłącznie nazwy/type/hash pól — bez payloadów.

Końcowa regresja poprawki: `376/376 OK` dla recovery, territory/control,
conflict identity/cutover/engagement/multi, progression receipts, Target
Persistence oraz GN territory jobs. `py_compile` i `git diff --check`: OK.

Po kontrolowanym rollbacku należy ponownie wykonać `status → audit → plan`.
Oczekiwany wynik na niezmienionej topologii targetów to jawny
`level_50_existing_geometry_conflict`. Dalszy plan wymaga osobnej decyzji o
kanonicznym traktowaniu istniejących filarów przy skoku do levelu 50; recovery
nie może ich usuwać, przenosić ani omijać bez takiej decyzji.

## Stan rozpoczęcia — 2026-08-23

Pierwszy slice Sprintu 130.11 został wykonany bez mutacji bazy:

- dodano `tools/repair_trollu2_profile.py` z komendami `status`, `audit`,
  `plan` i `dry-run`;
- każde polecenie otwiera SQLite przez `mode=ro` i `PRAGMA query_only=ON`;
- exact canonical login został zamrożony jako `trolu2`; nie ma fuzzy match ani
  parsowania profili innych kont;
- lokalny snapshot potwierdził poprawny current checksum/revision, nieużywalny
  LKG zawierający canonical mirror, wallet `1000`, 11 aplikacji, 11 narzędzi,
  20 części aktywnego cyklu `ghostnetwork_0001` oraz kanoniczny bilet do Tokio;
- dwie ostatnie instalacje Googleplex zostały udowodnione receiptami i
  dopasowane do canonical inventory: `Nmap` i `Metasploit`;
- pierwotny pierścień ośmiu filarów kolidował z istniejącym terytorium. Bramka
  zatrzymała plan, po czym deterministyczny resolver wybrał wolny wariant
  przesunięty o 3000 m na północ; ponowny dry-run ma zero kolizji;
- podpisany plan ma stabilne target IDs, wszystkie filary `stationary=true`,
  zero planowanych zapisów GN i zero zapisów innych profili;
- `tests/test_trollu2_recovery_tool.py`: `13/13 OK`; `py_compile`: OK.

Nie wykonano recovery na właściwej bazie, promocji LKG, commita ani deployu.
Lokalny plan w katalogu TEMP jest tylko dowodem implementacyjnym i nie zastępuje
planu wygenerowanego z aktualnej bazy serwera bezpośrednio przed operacją.

## Stan gotowości — 2026-08-23

Pipeline operatorski został domknięty:

- `backup` tworzy podpisany, wrażliwy before-manifest poza repozytorium;
- `apply` wymaga planu i manifestu wraz z ich checksumami, `--write` oraz
  `--authorized-by`; zapisuje durable receipt i receipts etapów;
- poziom 50 jest guarded profile CAS, a grant ośmiu filarów dla miasta zapisuje
  ownership, captured targets, jeden rebuild job i step receipt w jednej
  transakcji `BEGIN IMMEDIATE`;
- pierwszy przebieg `apply` bez gotowego workera kończy się kontrolowanym kodem
  `3` i fazą `AWAITING_TERRITORY_WORKER`; identyczny retry finalizuje settlement
  dopiero po terminalnym sukcesie własnych job IDs;
- final settlement zapisuje dokładnie raz RSP 2560 i saldo 250000 przez canonical
  wallet event/ledger oraz odświeża `territory_stats` i `exp` z geometrii workera;
- LKG nie jest zmieniane przez apply ani worker. `promote-lkg` jest osobnym,
  jawnym krokiem dopiero po pozytywnym verify i manualu;
- rollback jest receipt/revision/version gated i odmawia po późniejszym legalnym
  gameplayu;
- worker ma wąską gałąź tylko dla exact `trolu2` + kontraktu
  `sprint_130_11`: używa przekazanego recovery levelu, tego samego canonical
  territory rebuild/publication, ale nie czyta i nie zapisuje pełnego profilu
  ani LKG. Zwykły worker gameplayowy nie zmienił semantyki.

Na pełnej kopii snapshotu produkcyjnego (`848560128 B`) wykonano real-schema
`plan → dry-run → backup → apply → verify`. Apply utworzył 8 filarów i jeden
pending rebuild job, po czym poprawnie zatrzymał się na
`AWAITING_TERRITORY_WORKER`; wallet pozostał `1000`, RSP `25`, LKG bez zmian,
a verify raportował wyłącznie `territory_jobs_not_complete`. Kopia testowa i
wrażliwy manifest zostały usunięte z TEMP; na roboczym pliku nie wykonano
recovery apply.

Regresja:

- recovery + lekka gałąź workera: `22/22 OK`;
- profile/session/wallet/target/territory/GN: `441/441 OK`;
- `py_compile` oraz `git diff --check`: OK.

## Aktualna sekwencja operatorska — wycofanie partial apply

Po wdrożeniu tej poprawki nie wolno ponawiać starego `apply`, uruchamiać
`promote-lkg` ani wykonywać settlementu. Dla istniejących artefaktów
`/home/johndoe/chaos-recovery-13011-20260823T200943Z` należy wykonać:

```bash
cd /home/johndoe/app/chaos
RECOVERY_DIR='/home/johndoe/chaos-recovery-13011-20260823T200943Z'
PLAN="$RECOVERY_DIR/plan.json"
BEFORE="$RECOVERY_DIR/before-manifest.json"
OPERATOR="$(whoami)"

PLAN_SHA="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["plan_sha256"])' "$PLAN")"
MANIFEST_SHA="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["manifest_sha256"])' "$BEFORE")"

.venv/bin/python tools/repair_trollu2_profile.py verify --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" | tee "$RECOVERY_DIR/verify-pre-rollback.json"
.venv/bin/python tools/repair_trollu2_profile.py rollback --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" --plan-sha256 "$PLAN_SHA" --manifest-sha256 "$MANIFEST_SHA" --write --authorized-by "$OPERATOR" | tee "$RECOVERY_DIR/rollback.json"
pm2 logs chaos-territory-worker --lines 150 --nostream
.venv/bin/python tools/repair_trollu2_profile.py verify-rollback --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" | tee "$RECOVERY_DIR/verify-rollback.json"
```

Pierwszy `verify` ma nadal zakończyć się `NO-GO`, ale musi rozpoznać
`exact_recovery_owned_worker_projection` i wskazać wyłącznie bezpiecznie
atrybuowany recovery conflict. Jeżeli rollback zgłosi gameplay, aktywny
multi-engagement albo obcą zmianę profilu/walletu/ownership, operator kończy
procedurę bez ręcznego czyszczenia. `verify-rollback` uruchamia się ponownie po
zakończeniu obu jobów workera, jeżeli pierwszy odczyt pokaże stan `pending`.

Po zielonym rollback verify wolno wykonać tylko nowy read-only
`status → audit → plan`. Na niezmienionych targetach plan ma zwrócić
`level_50_existing_geometry_conflict`; nie wolno przechodzić do `backup/apply`.

## Sekwencja docelowego recovery — wstrzymana przez blocker geometrii

Po własnym commit/deploy/pull operator przeładowuje oba procesy z wersjonowanych
ecosystemów, zanim wygeneruje plan:

```bash
cd /home/johndoe/app/chaos
pm2 startOrReload ecosystem.web.config.js --only chaos --update-env
pm2 startOrReload ecosystem.territory-worker.config.js --only chaos-territory-worker --update-env
pm2 save
pm2 status
```

Konto `trolu2` ma pozostać wylogowane od początku planu do zakończenia apply.
Fresh plan i before-manifest są tworzone poza repo:

```bash
RECOVERY_DIR="/home/johndoe/chaos-recovery-13011-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$RECOVERY_DIR"
PLAN="$RECOVERY_DIR/plan.json"
BEFORE="$RECOVERY_DIR/before-manifest.json"
OPERATOR="$(whoami)"

.venv/bin/python tools/repair_trollu2_profile.py status --db data/game.sqlite3 | tee "$RECOVERY_DIR/status.json"
.venv/bin/python tools/repair_trollu2_profile.py audit --db data/game.sqlite3 | tee "$RECOVERY_DIR/audit.json"
.venv/bin/python tools/repair_trollu2_profile.py plan --db data/game.sqlite3 --output "$PLAN"
.venv/bin/python tools/repair_trollu2_profile.py dry-run --db data/game.sqlite3 --plan "$PLAN" | tee "$RECOVERY_DIR/dry-run.json"
.venv/bin/python tools/repair_trollu2_profile.py backup --db data/game.sqlite3 --plan "$PLAN" --output "$BEFORE" | tee "$RECOVERY_DIR/backup.json"

PLAN_SHA="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["plan_sha256"])' "$PLAN")"
MANIFEST_SHA="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["manifest_sha256"])' "$BEFORE")"
printf 'RECOVERY_DIR=%s\nPLAN_SHA=%s\nMANIFEST_SHA=%s\n' "$RECOVERY_DIR" "$PLAN_SHA" "$MANIFEST_SHA"
```

`dry-run` musi mieć `ok=true`, `blockers=[]`, exact `trolu2`, 11 apps, 11 tools,
Nmap + Metasploit, Tokio/8 filarów, GN/20 części i zero planowanych GN writes.
Dopiero wtedy operator uruchamia apply:

```bash
.venv/bin/python tools/repair_trollu2_profile.py apply --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" --plan-sha256 "$PLAN_SHA" --manifest-sha256 "$MANIFEST_SHA" --write --authorized-by "$OPERATOR" | tee "$RECOVERY_DIR/apply-1.json"
pm2 logs chaos-territory-worker --lines 100 --nostream
.venv/bin/python tools/repair_trollu2_profile.py apply --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" --plan-sha256 "$PLAN_SHA" --manifest-sha256 "$MANIFEST_SHA" --write --authorized-by "$OPERATOR" | tee "$RECOVERY_DIR/apply-2.json"
.venv/bin/python tools/repair_trollu2_profile.py verify --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" | tee "$RECOVERY_DIR/verify-before-manual.json"
.venv/bin/python tools/repair_trollu2_profile.py report --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" | tee "$RECOVERY_DIR/report-before-manual.json"
```

Pierwszy apply może legalnie zakończyć się kodem `3` z
`AWAITING_TERRITORY_WORKER`. Drugi identyczny przebieg jest wymaganym retry po
terminalnym sukcesie joba; nie dubluje targetów ani HC. `verify` przed manualem
musi mieć `ok=true`, saldo 250000, LVL 50, RSP 2560, kompletny job, 8 recovery
targets, GN/20 części i `lkg_promoted=false`.

Po pozytywnym manualu:

```bash
FINAL_SHA="$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8"))["profile"]["checksum"])' "$RECOVERY_DIR/verify-before-manual.json")"
.venv/bin/python tools/repair_trollu2_profile.py promote-lkg --db data/game.sqlite3 --plan "$PLAN" --plan-sha256 "$PLAN_SHA" --final-checksum "$FINAL_SHA" --write --authorized-by "$OPERATOR" | tee "$RECOVERY_DIR/promote-lkg.json"
.venv/bin/python tools/repair_trollu2_profile.py verify --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" | tee "$RECOVERY_DIR/verify-final.json"
.venv/bin/python tools/repair_trollu2_profile.py report --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" | tee "$RECOVERY_DIR/report-final.json"
```

Rollback nie jest elementem normalnego przebiegu. Jeżeli verify/manual wykryje
blocker i nie było późniejszego gameplayu na profilu, walletcie ani terytorium:

```bash
.venv/bin/python tools/repair_trollu2_profile.py rollback --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE" --plan-sha256 "$PLAN_SHA" --manifest-sha256 "$MANIFEST_SHA" --write --authorized-by "$OPERATOR"
.venv/bin/python tools/repair_trollu2_profile.py verify-rollback --db data/game.sqlite3 --plan "$PLAN" --before-manifest "$BEFORE"
```

Incydent źródłowy:
`doc/Incydent Trollu2 — utrata profilu, błędy sesji i plan odbudowy.md`.

Wiążąca bramka wydajnościowa:
`doc/profile_hot_path_contract_130_11_plus.md`.

Sprint 130.11 jest jedynym planowanym wyjątkiem, w którym pełny profil może być
odczytany i zapisany przez operatorskie narzędzie dla dokładnie jednego,
zamrożonego canonical konta. Heavy path nie może zostać wystawiony jako endpoint,
użyty przez worker ani współdzielony jako wygodny helper runtime. Wszystkie
odczyty innych kont, GN, walletu, inventory, targetów i terytoriów muszą pozostać
w ich canonical stores/projekcjach.

## Cel

Odbudować konto zgłoszone jako `Trollu2` przez wersjonowane, idempotentne
narzędzie, korzystając z kanonicznych store'ów obecnego systemu. Exact
canonical username musi zostać potwierdzony z rekordu `users` przed zamrożeniem
planu. Repair nie może być ręcznym nadpisaniem JSON-u ani skryptem tworzącym
polygon poza territory workerem.

Sprint rozpoczyna się dopiero po GO Sprintu 130.10. Dzięki temu naprawiony profil
nie zostanie ponownie uszkodzony przez fallback, stale writer, odwrócony mirror
walletu albo stan poprzedniej sesji.

## Zasady startowe

Przed pierwszą zmianą:

1. uruchomić `git status --short`;
2. przejrzeć bieżący diff i pliki untracked;
3. nie cofać ani nie nadpisywać zmian użytkownika;
4. potwierdzić GO Sprintu 130.10 i rzeczywisty kontrakt store'ów;
5. pracować read-only aż do zatwierdzenia podpisanego planu i before-manifestu.

Sprint nie daje automatycznej zgody na commit, deploy, restart ani apply.

## Wiążący wynik gameplayowy

Docelowe pola:

```text
reported username: Trollu2
canonical username: potwierdzony i zamrożony w podpisanym planie
level: 50
respect: 2560
hackcoins: 250000
```

`exp` nie jest w obecnym modelu drugą liczbą RSP. Jest tekstową projekcją
powierzchni/progression, dlatego musi zostać przeliczony z kanonicznych
terytoriów po rebuildzie. Skrypt nie zapisuje surowego `exp=2560`.

Inventory:

- zachować wszystkie kanoniczne aplikacje i narzędzia;
- zachować dwie aplikacje pozyskane w Googleplexie podczas ostatniej sesji,
  jeżeli potwierdza je store/purchase history;
- jeżeli ich tożsamości nie da się udowodnić, zatrzymać plan z findingiem zamiast
  zgadywać nazwy.

Terytoria:

- miasta wynikają wyłącznie z udokumentowanej i zdeduplikowanej historii
  podróży; obecnie nie istnieje osobny kanoniczny store ticketów;
- `5–8` filarów na miasto, preferowane `8`, jeżeli geometria jest bezpieczna;
- brak sztucznych konfliktów oraz repair-sourced zmian profili, ownership i
  progression innych graczy; zwykła publikacja map/delta jest dozwolona;
- brak ingerencji w części oraz bieżący cykl GhostNetwork.

## Precondition gate

Przed planem repair potwierdzić:

1. Sprint 130.10 ma GO;
2. mechanizm odczytu raportuje profil i stan LKG osobno, bez fallbacku; brak
   historycznego LKG dla uszkodzonego konta jest jawną luką dowodową, a nie
   samodzielnym blockerem, jeżeli istnieje obowiązkowy before-manifest;
3. wallet writer cutover ze Sprintu 130.10 jest zakończony:
   `wallet_balances` trzyma current balance, ledger audyt/idempotencję, a profil
   jest tylko mirrorem;
4. sesja ma unikalną generation;
5. zachowano stan dowodowy konta sprzed repair;
6. ustalono dokładny canonical login — bez fuzzy match, aliasu i dopasowania
   nazwy markera mapy;
7. cykl GhostNetwork oraz jego 20 części mają zapisany diagnostyczny snapshot
   before z source/version;
8. territory worker i reconciliation są zdrowe, a stan istniejących kolejek jest
   znany.

Niespełnienie któregokolwiek warunku daje `NO-GO` bez częściowego apply.

## Dedykowane narzędzie

Powstaje:

```text
tools/repair_trollu2_profile.py
```

Kontrakt CLI:

```text
status
audit
plan
dry-run
backup
apply
verify
promote-lkg
report
rollback
```

Zasady:

- domyślny tryb jest read-only;
- `apply` wymaga jawnego `--write`;
- audit nie stosuje fuzzy match ani aliasu; po potwierdzeniu rekordu exact
  canonical username zostaje zamrożony w podpisanym planie i allowliście apply;
- plan zawiera DB identity, before revision/checksum i własny SHA-256;
- apply wymaga podania zatwierdzonego planu i jego checksum;
- apply wymaga odtwarzalnego before-manifestu dla dokładnie dotykanych rekordów;
- zmiana stanu pomiędzy planem i apply powoduje odmowę;
- durable receipt gwarantuje idempotencję;
- drugi apply tego samego planu jest raportowany jako no-op;
- crash/retry wznawia etapy bez duplikowania HC, filarów, targetów i area jobs;
- rollback działa wyłącznie przez durable repair/step receipts oraz expected
  post-revision; nie cofa późniejszego legalnego gameplayu ani innych graczy;
- raport nie zawiera credentials, cookies ani pełnych danych innych graczy.

Preferowany model operatorski przed manualem:

```bash
python tools/repair_trollu2_profile.py status --db data/game.sqlite3
python tools/repair_trollu2_profile.py audit --db data/game.sqlite3
python tools/repair_trollu2_profile.py plan --db data/game.sqlite3 --output /tmp/trollu2-recovery-plan.json
python tools/repair_trollu2_profile.py dry-run --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json
python tools/repair_trollu2_profile.py backup --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --output /tmp/trollu2-before-manifest.json
python tools/repair_trollu2_profile.py apply --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --before-manifest /tmp/trollu2-before-manifest.json --plan-sha256 <PLAN_SHA256> --manifest-sha256 <MANIFEST_SHA256> --write --authorized-by <OPERATOR>
python tools/repair_trollu2_profile.py verify --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --before-manifest /tmp/trollu2-before-manifest.json
```

Dopiero po pozytywnym manualu:

```bash
python tools/repair_trollu2_profile.py promote-lkg --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --plan-sha256 <PLAN_SHA256> --final-checksum <FINAL_SHA256> --write --authorized-by <OPERATOR>
python tools/repair_trollu2_profile.py verify --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --before-manifest /tmp/trollu2-before-manifest.json
python tools/repair_trollu2_profile.py report --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --before-manifest /tmp/trollu2-before-manifest.json
```

`rollback` jest osobną akcją awaryjną po analizie nieudanego apply, a nie
normalnym kolejnym krokiem po poprawnym recovery:

```bash
python tools/repair_trollu2_profile.py rollback --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --before-manifest /tmp/trollu2-before-manifest.json --plan-sha256 <PLAN_SHA256> --manifest-sha256 <MANIFEST_SHA256> --write --authorized-by <OPERATOR>
```

To jest kontrakt gotowego narzędzia. Komendy mutujące wykonuje operator dopiero
po deployu kodu i zaakceptowaniu świeżego serwerowego dry-run.

## Etap 1 — audit i manifest stanu

Audit zbiera dla jednego konta:

- profile revision/checksum i LKG;
- `level`, `respect` oraz projekcję `exp`;
- wallet balance i ledger tail;
- aplikacje, narzędzia, storage i zakupy Googleplex;
- dowody podróży oraz listę możliwych miast z podaniem provenance/confidence;
- Target Registry, captured targets, ownership i player areas;
- pending/failed territory jobs oraz progression receipts;
- clan/profession i trwałe achievement/history;
- aktualny cykl GN, liczbę 20 części, lifecycle counts, reservations, topology,
  pending i unreconciled effects.

Raport wskazuje, które wartości pochodzą z dowodu, które z rekompensaty, a które
są tylko projekcją do ponownego wyliczenia.

Nie ma osobnego travel-ticket store. Resolver dowodów miast stosuje kolejność:

1. poprawny pre-incident snapshot/LKG lub zabezpieczony evidence manifest;
2. zgodne wpisy `product_purchases`, `googleplex_products` i `market_history`;
3. wallet ledger, system messages i logi z identyfikatorem produktu/miasta;
4. relacja testera wyłącznie jako jawny finding do zatwierdzenia, nigdy jako
   automatyczny target generator.

Wpisy są deduplikowane po product/ticket ID, mieście i zdarzeniu. Sprzeczność
albo brak potwierdzenia zatrzymuje dane miasto przed apply.

## Etap 2 — plan progression i inventory

Plan definiuje finalny wynik:

```text
level → 50
respect → 2560
wallet balance → 250000 HC
```

`level=50` jest zatwierdzane guarded write przed obliczeniem geometrii, ponieważ
bieżący territory contract może zależeć od levelu. `respect`, `hackcoins` i
projekcja `exp` są finalizowane dopiero po zakończeniu recovery jobs oraz
progression-neutralnym odświeżeniu statystyk.

HC przechodzi przez ujednoliconą w 130.10 atomową granicę walletu. Bieżące
saldo znajduje się w `wallet_balances`; jeden stabilny recovery transaction key
tworzy append-only ledger event, a profil dostaje wyłącznie mirror. Nie wolno
zmieniać surowego mirroru i walletu niezależnymi zapisami.

Inventory jest składane z kanonicznych `player_apps` i `player_tool_files`.
Repair nie kasuje żadnego istniejącego elementu. Zakupy Googleplex są
zachowywane według hierarchii dowodów i bieżącego inventory; nie odtwarza się
produktu jedynie na podstawie pamięci operatora bez jawnego findingu i
zatwierdzenia w podpisanym planie.

Credentials, session generation, aimed target i bieżące operacje nie są
przepisywane z backupu.

## Etap 3 — plan bezpiecznych terytoriów

Dla każdego potwierdzonego miasta:

1. odczytać istniejące terytoria, targety i części GN;
2. wybrać obszar poza cudzym terytorium, aktywnym konfliktem i strefą części GN;
3. wygenerować deterministyczne recovery target IDs związane z planem i miastem;
4. zwalidować geometrię `5–8` filarów, preferencyjnie `8`;
5. zasymulować nową atomową granicę recovery grant i precondition
   `target_unowned`;
6. pokazać w dry-run planowane filary, pole i wszystkie collision reasons;
7. jeżeli teren jest zajęty, deterministycznie przesunąć kandydat albo oznaczyć
   miasto jako wymagające decyzji; nigdy nie tworzyć konfliktu automatycznie.

Obecne `TerritoryTargetOwnershipStore.capture()` służy transferowi istniejącego
ownera, a `save_captured_target()` i `enqueue_rebuild_job()` nie tworzą jednej
transakcji. Nie wolno złożyć z nich na ślepo repair pipeline'u.

Sprint dodaje dedykowaną atomową granicę recovery, korzystającą z tych samych
tabel i workera:

```text
validate signed plan + current collision/GN state
→ create/grant unowned recovery target
→ captured_targets
→ territory rebuild job
→ durable recovery step receipt (w tej samej transakcji)
COMMIT
→ existing worker publication/reconciliation
```

Grant dla jednego miasta w tym samym `BEGIN IMMEDIATE`:

- ponownie sprawdza plan/revision, brak ownera, konfliktu i części GN;
- zapisuje deterministic target IDs i provenance `recovery_plan_id`;
- jawnie ustawia każdy filar `stationary=true`; `generated=true` nie może
  pozostawić domyślnego `stationary=false`, bo taki target nie wejdzie do
  geometrii;
- tworzy ownership/captured target, unikalny rebuild job i step receipt;
- kończy się w całości commit albo rollback;
- nie tworzy zwykłego gameplay progression receipt ani rewardu.

Zakazane:

- bezpośredni zapis polygonu do `player_areas`;
- dopisanie obiektów tylko do `profile["hacked"]`;
- kopiowanie cudzych target IDs;
- usuwanie lub przejmowanie cudzego ownership;
- generowanie conflict/engagement jako efektu rekompensaty;
- wywołanie `save_captured_target()` i `enqueue_rebuild_job()` jako dwóch
  niezależnych commitów;
- synchroniczny geometry rebuild z request path.

Każde miasto jest etapem atomowym i wznawialnym. Awaria przed commitem nie
pozostawia filaru bez joba; awaria workera po commicie pozostawia trwały
recovery job możliwy do bezpiecznego retry, a nie połowiczny polygon.

## Etap 4 — kolejność apply, progression i izolacja GN

Wiążąca kolejność apply:

1. ponownie zweryfikować plan, before-manifest, exact username i wszystkie
   expected revisions;
2. guarded recovery write ustawia `level=50`, zachowując resztę poprawnych pól;
3. wykonać atomowe recovery grants dla zatwierdzonych miast;
4. poczekać na terminalny sukces wyłącznie job IDs należących do planu i
   potwierdzić ich publikację/reconciliation;
5. uruchomić progression-neutralny `refresh_territory_stats_snapshot` po
   workerze; generic worker sam nie przelicza `territory_stats` ani `exp`;
6. potwierdzić brak pending gameplay progression receipts z repair;
7. jednym finalnym settlementem z durable receipt ustawić dokładnie
   `level=50`, `respect=2560`, `hackcoins=250000` oraz wyliczoną projekcję
   `exp`;
8. wykonać pełny verify i manual;
9. dopiero po sukcesie jawnie promować verified final profile do LKG.

Recovery grants są administracyjną rekompensatą i nie generują zwykłych nagród
za capture/otoczenie. Finalny settlement następuje po workerze, więc żadna
oczekująca nagroda nie może później podbić wartości ponad `50/2560/250000`.

Przed i po apply zebrać diagnostyczną projekcję GN:

```text
cycle_id i stan
part count = 20
pooled/reserved/public/contained/active
part anchors i topology version/checksum
reservations
pending/unreconciled effects
event high-water mark
```

Na aktywnym serwerze globalny checksum i event counts mogą legalnie zmienić się
przez gameplay innych testerów. Verify nie wymaga bit-identycznej bazy. Musi
udowodnić, że żaden `ghost_*` write/event/effect nie ma
`recovery_plan_id`, source ani request ID repairu oraz że runtime GN pozostaje
valid z 20 częściami.

Repair nie może:

- wykonać drop roll;
- utworzyć lub zużyć reservation;
- odkryć, zablokować ani aktywować części;
- zmienić anchoru części;
- wygenerować contribution/reward GN;
- uruchomić SFX lub publikację historycznej delty.

Jeżeli kandydat terytorium w chwili atomowego grantu obejmuje część GN, plan
relokuje terytorium albo zatrzymuje się. Nie zmienia części.

Stan incydentowy sprzed repair pozostaje w oddzielnym, immutable evidence
manifest. Nie wolno promować go do LKG. Po zakończeniu własnych jobów,
progression-neutralnym refreshu i pełnym verify wykonywana jest osobna atomowa
operacja `promote verified recovery to LKG`, związana z recovery receipt i
finalnym checksumem. Promocja nie usuwa before-manifestu.

## Etap 5 — dry-run i dwie bramki operatorskie

Po przygotowaniu narzędzia zatrzymać się z wynikiem:

`READY FOR TROLLU2 RECOVERY DRY-RUN — Sprint 130.11`

Dry-run użytkownika musi pokazać:

- reported login, potwierdzony exact canonical username i before checksum;
- before-manifest path/checksum oraz warunki bezpiecznego rollbacku;
- finalne `level=50`, `respect=2560`, `HC=250000`;
- listę zachowanych apps/tools i potwierdzone dwa zakupy;
- listę miast z provenance/confidence, filarów `stationary=true`, kolizji i
  planowanych recovery job IDs;
- brak planowanych zmian profilu, ownership i progression innych graczy;
- brak planowanych write/event/effect GN ze źródłem recovery;
- kolejność level → grants/jobs → neutral stats refresh → final settlement →
  verify/manual → LKG promotion;
- plan SHA-256 wymagany przez apply.

Po akceptacji dry-run status brzmi:

`READY FOR MANUAL RECOVERY APPLY — Sprint 130.11`

Asystent nie wykonuje apply, deployu ani restartu bez osobnego polecenia.

## Etap 6 — verify i manual gameplay

Po operatorskim apply:

1. `verify` potwierdza dokładnie jeden recovery receipt;
2. drugi apply jest no-op;
3. wallet ledger i balance zgadzają się z 250000 HC;
4. profil ma LVL 50 i RSP 2560;
5. progression-neutralny refresh wykonał `territory_stats` i `exp` po workerze;
6. inventory i purchase history są zachowane;
7. Target Registry, ownership i captured targets odpowiadają filarom planu;
8. wszystkie własne recovery job IDs są terminalne i bez błędu; globalna kolejka
   może obsługiwać niezależny gameplay;
9. territory status/reconcile/verify są zielone dla scope'u planu;
10. GN runtime jest valid z 20 częściami i nie ma repair-sourced event/effect;
11. inne profile, ownership i progression nie mają repair-sourced write;
12. po manualu `promote-lkg` zapisuje finalny checksum dokładnie raz i nie usuwa
    before-manifestu;
13. końcowy verify potwierdza promoted LKG oraz durable promotion receipt.

Manual użytkownika:

```text
login canonical_username z podpisanego planu (konto zgłoszone jako Trollu2)
→ profil
→ toolbar
→ Googleplex
→ aplikacje i narzędzia
→ mapa w każdym mieście
→ terytoria i filary
→ logout/login
→ ponowny profil i mapa
```

Manual nie wymaga nowego dropu ani zmiany lifecycle GN.

## Testy automatyczne

Minimum:

1. audit/status/plan/dry-run nie zapisują bazy;
2. zła baza, schema, username, revision lub checksum blokuje apply;
3. alias/fuzzy login nie może zostać zamrożony jako canonical username;
4. plan zachowuje wszystkie canonical apps/tools;
5. brak dowodu dwóch instalacji zatrzymuje plan z czytelnym findingiem;
6. wallet repair ma jeden ledger event i poprawny balance;
7. drugi apply nie dodaje HC;
8. crash/retry nie dubluje żadnego etapu;
9. credentials i session state pozostają nietknięte;
10. target IDs są stabilne i unikalne, a każdy filar ma `stationary=true`;
11. ownership + captured target + rebuild job + step receipt commitują się
    atomowo, a apply drugi raz nie dubluje filarów ani areas;
12. kolizja z cudzym terytorium powoduje relokację/no-go, nie konflikt;
13. kolizja z częścią GN powoduje relokację/no-go;
14. awaria per-city jest atomowa i wznawialna;
15. progression-neutralny refresh po workerze wylicza `territory_stats/exp` bez
    dodania LVL/RSP;
16. final settlement zawsze kończy się dokładnie `50/2560/250000`, również po
    retry i potencjalnych worker callbacks;
17. żaden profil, ownership ani progression innego gracza nie ma write ze
    źródłem recovery; dozwolone są zwykłe publication/delivery;
18. GN pozostaje valid z 20 częściami, a recovery source nie pojawia się w
    żadnym `ghost_*` write/event/effect mimo równoległego gameplayu;
19. before-manifest jest odtwarzalny, a rollback odmawia przy zmianie
    expected post-revision i nie cofa późniejszego gameplayu;
20. invalid pre-repair state nie staje się LKG; verified final state jest
    promowany dokładnie raz, z receipt, bez usunięcia evidence manifestu;
21. raport nie zawiera danych wrażliwych.
22. status/audit/plan/dry-run/verify nie skanują pełnych profili innych kont;
23. implementacja ma jawną allowlistę heavy call sites ograniczoną do exact
    recovery subject oraz zero `list_profiles()`/per-user `get_profile()`;
24. żaden endpoint, worker ani zwykły gameplay request nie importuje lub nie
    wywołuje heavy helperów narzędzia recovery;
25. pełny guarded write przygotowuje walidację, serializację, checksum i LKG
    przed writer-lockiem, a test mierzy jego sekcję krytyczną.

Sugerowany test:

```text
tests/test_trollu2_recovery_tool.py
```

Regresja obejmuje profile/LKG/session, wallet, inventory/Googleplex, Target
Registry, territory CAS/rebuild/reconciliation, progression receipts,
GhostNetwork runtime oraz `test_target_persistence`.

Kontrole końcowe:

```text
python -m py_compile <zmienione pliki Python>
git diff --check
```

## Dokumentacja Sprintu 130.11

Zaktualizować:

- dokument incydentu i root-cause status;
- `doc/game_play_180726.md`;
- `doc/project_journal.md`;
- `doc/profile_store_extraction_audit.md`;
- runbook integrity/recovery utworzony w 130.10;
- zanonimizowany raport before → plan → after.

Nie zapisywać do repo pełnego profilu, planu z danymi lokalizacyjnymi serwera,
credentials ani kopii produkcyjnej bazy.

## Poza zakresem

- naprawa lub nagradzanie innych kont;
- globalna migracja wszystkich profili;
- zmiana cen, progression rules lub drop policy;
- reset lub nowy cykl GhostNetwork;
- ręczne przesuwanie istniejących części GN;
- Sprint 131 GhostNetwork Suite.

## Definition of Done

Sprint dostaje GO dopiero, gdy:

- zatwierdzony dry-run i apply dotyczą exact canonical konta zamrożonego w
  planie jako konto zgłoszone `Trollu2`;
- istnieje checksumowany before-manifest i bezpieczny rollback związany z
  durable receipts/revisions;
- recovery jest idempotentne i ma durable receipt;
- LVL 50, RSP 2560 i 250000 HC są potwierdzone kanonicznie;
- inventory i potwierdzone zakupy są zachowane;
- bonusowe terytoria istnieją przez atomowy recovery grant + istniejący worker,
  wszystkie filary są stationary i nie wywołały konfliktu;
- własne recovery job IDs są terminalne, reconcile/verify zielone;
- territory stats/exp odświeżono progression-neutralnie, a finalne wartości nie
  zostały podbite przez reward pipeline;
- GhostNetwork pozostaje valid, a repair nie utworzył żadnego GN write/event;
- manual po ponownym logowaniu pokazuje ten sam poprawny stan;
- inne profile, ownership i progression nie mają repair-sourced writes;
- verified final state został jawnie promowany do LKG bez utraty before evidence.
- `PROFILE HOT PATH AUDIT` wskazuje zero nowych runtime heavy reads/writes,
  zero skanów wszystkich profili i tylko jawne operatorskie wyjątki exact-account.

Werdykt:

`GO — Sprint 130.11 Trollu2 recovery validated`

albo:

`NO-GO — Sprint 130.11 still has recovery or canonical-state blockers`

Dopiero GO Sprintów 130.10 i 130.11 odblokowuje Sprint 131.
