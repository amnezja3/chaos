# Sprint 130.11 — Trollu2 Controlled Profile and Territory Recovery

Data planu: 2026-08-21.

Status: `QUEUED — REQUIRES GO FROM SPRINT 130.10`.

Incydent źródłowy:
`doc/Incydent Trollu2 — utrata profilu, błędy sesji i plan odbudowy.md`.

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
python tools/repair_trollu2_profile.py apply --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --before-manifest /tmp/trollu2-before-manifest.json --plan-sha256 <SHA256> --write
python tools/repair_trollu2_profile.py verify --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json
```

Dopiero po pozytywnym manualu:

```bash
python tools/repair_trollu2_profile.py promote-lkg --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --final-checksum <FINAL_SHA256> --write
python tools/repair_trollu2_profile.py verify --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json
python tools/repair_trollu2_profile.py report --db data/game.sqlite3
```

`rollback` jest osobną akcją awaryjną po analizie nieudanego apply, a nie
normalnym kolejnym krokiem po poprawnym recovery:

```bash
python tools/repair_trollu2_profile.py rollback --db data/game.sqlite3 --plan /tmp/trollu2-recovery-plan.json --before-manifest /tmp/trollu2-before-manifest.json --write
```

To jest kontrakt planowanego narzędzia, nie komenda do wykonania w bieżącym
sprincie dokumentacyjnym.

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

Werdykt:

`GO — Sprint 130.11 Trollu2 recovery validated`

albo:

`NO-GO — Sprint 130.11 still has recovery or canonical-state blockers`

Dopiero GO Sprintów 130.10 i 130.11 odblokowuje Sprint 131.
