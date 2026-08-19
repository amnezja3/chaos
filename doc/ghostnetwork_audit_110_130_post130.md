# GhostNetwork audit sprintow 110-130 i refaktoru post-130

Data audytu: 2026-08-19  
Zakres: contract check, read-only runtime inspection, testy diagnostyczne.  
Runtime produkcyjny nie zostal zmieniony.

## 1. Executive summary

**Werdykt: NO-GO. GhostNetwork nie jest obecnie testowalny end-to-end z poziomu gry.**

Kod domenowy GhostNetwork jest rozbudowany i jego izolowane testy przechodza, ale
aktywny runtime zatrzymuje pipeline przed eligibility i przed rollem:

1. `config.py:131-132` ustawia domyslnie `GHOSTNETWORK_DROPS_ENABLED=False` oraz
   `GHOSTNETWORK_DROP_CHANCE=0.0`.
2. Read-only probe bieżącej bazy (`tools/audit_ghostnetwork_runtime_state.py`)
   zwrocil `cycle=null`, `parts_count=0`, `active_reservations=0` i warning
   `no_active_cycle`.
3. Produkcyjny kod nie wywoluje `ensure_active_cycle()`. Wszystkie wywolania
   bootstrapu sa w testach (`ghostnetwork/cycles.py:90-102,305-306`; call-site
   search poza testami: brak).
4. Hook aim istnieje i jest osiagalny przez `set_player_aimed_target()`
   (`run.py:7175-7213`), lecz `GhostReservationService.on_target_aimed()` zwraca
   `no_active_cycle` przed eligibility i rollem (`ghostnetwork/reservations.py:178-191`).
5. Hook capture nadal istnieje po refaktorze i jest wywolywany po trwalym capture
   (`run.py:25403-25417`), ale bez wczesniejszej rezerwacji zawsze konczy sie
   `no_matching_reservation` (`ghostnetwork/service.py:289-348`).

Objaw 0 czesci po ponad 500 hackach nie jest anomalia statystyczna. W sprawdzonym
runtime liczba realnych RNG comparisons wynosi **0**, a prawdopodobienstwo zera
dropow wynosi **1**.

Refaktor post-130 nie usunal bezposredniego hooka capture, ale rozbudowal granice
receipt/CAS i system terytoriow bez dolaczenia GhostNetwork do nowych producentow
eventow. Adapter terytoriow, module-state progress, abilities, rewards,
strategic conflicts, closure i transmission maja implementacje oraz testy, ale
nie maja aktywnych call-site'ow w `run.py`. Jest to klasyczny przypadek
"feature exists and unit tests pass, but production runtime never reaches it".

## 2. Najwazniejszy werdykt

Klasyfikacja: **MULTIPLE CAUSES**.

Przyczyny glowne:

- **CYCLE STATE BROKEN** - brak bootstrapu aktywnego cyklu i 20 instancji czesci.
- **DROP RATE CONFIGURATION** - dropy sa domyslnie wylaczone, a chance wynosi 0.
- **POST-130 INTEGRATION REGRESSION** - nowe eventy/CAS terytorialne nie wywoluja
  adapterow GhostNetwork; dalszy gameplay loop po discovery jest osierocony.

Przyczyna wtórna:

- **EXACTLY-ONCE LOSS** - in-flight receipt `/gonna-win` nie wznawia brakujacego
  hooka GhostNetwork po crashu miedzy capture a efektem GN.

Nie jest to `UI VISIBILITY ONLY`: deterministyczny test dowodzi, ze snapshot i
delta potrafia pokazac persistowana czesc, ale aktualny runtime nie tworzy tej
czesci.

## 3. Zrodla kontraktu i granice architektury

Przeczytano:

- `doc/clans_machines.md` (cykl 20 czesci, discovery, terytoria, aktywacja,
  transmisja i nagrody);
- `doc/ghostnetwork_architecture.md` (globalny source of truth, profile tylko
  identity/history, event/delta/snapshot boundaries);
- `doc/game_play_180726.md` (kontrakty sprintow 110-130);
- `doc/sprint_110_integration_audit.md` oraz wszystkie
  `doc/sprint_111_...` do `doc/sprint_130_...`;
- `doc/project_journal_13082026.md` i `doc/project_journal.md` dla zmian
  post-130, zwlaszcza 130.8.1-130.8.9;
- audyty receipt/profile/delta powiazane z refaktorem.

Aktualny storage respektuje podstawowa granice: cykle, czesci, rezerwacje,
topologia i eventy pozostaja w tabelach `ghost_*` zarzadzanych przez
`GhostNetworkRepository` (`ghostnetwork/repository.py`). Profil jest uzywany do
identity oraz trwalego RSP/historii (`ghostnetwork/rewards.py:383-394`), a nie
jako source of truth aktywnego cyklu. Nie znaleziono drugiego cache cyklu w
profilu, drugiego magazynu terytoriow ani drugiego runtime mapy.

Problemem nie jest zatem naruszenie storage boundary, lecz brak uruchomienia i
brak producentow eventow integracyjnych.

## 4. Contract matrix 110-130

| Sprint | Zalozenie / kontrakt | Implementacja deklarowana | Aktualna implementacja i dowod | Status |
|---|---|---|---|---|
| 110 | Audyt granic; GN globalnym modulem, nie profile/map cache | kontrakty aim, hacked, territory, delta | Granice storage zachowane; wrappery w `run.py:7064-7172`; `on_territory_event` nadal placeholder w `ghostnetwork/service.py:354-355` | PARTIAL |
| 111 | Izolowane repozytorium, transakcje, wersje i recovery | `GhostNetworkRepository`, `GhostNetworkService` | Kod aktywny i health-check dziala; lokalny probe odczytuje repo bez profilu | OK |
| 112 | Kanoniczny katalog 4/4/20/20 | `ghostnetwork/catalog.py` | Probe: katalog valid, 4 klany, 4 maszyny, 20 profesji i 20 definicji czesci | OK |
| 113 | Aktywny cykl i dokladnie 20 instancji czesci | `GhostCycleService.ensure_active_cycle()` | Serwis/testy dzialaja, lecz brak produkcyjnego call-site; probe: `cycle=null`, 0 czesci | BROKEN |
| 114 | Zamkniety pierscien 20 polaczen przed aktywacja | `GhostTopologyService` | Generator/walidator przechodzi testy, ale bez cyklu nie istnieje runtime topology | PARTIAL |
| 115 | Aim wykonuje eligibility i niewidoczny roll/rezerwacje | `GhostReservationService.on_target_aimed()` | Hook aim osiagalny, lecz brak cyklu zwraca przed eligibility; dodatkowo defaults false/0 | BROKEN |
| 116 | Finalny capture zatwierdza rezerwacje i odkrywa czesc | `on_target_hacked`, `discover_part` | Hook capture pozostaje w `/gonna-win`, lecz zawsze brak matching reservation w bieżącym runtime | PARTIAL |
| 117 | Jawny lifecycle i idempotentne eventy czesci | `GhostPartLifecycleService` | Deterministyczny test potwierdza `reserved -> public` i pojedynczy event; brak naturalnego wejscia | PARTIAL |
| 118 | Reakcja na stabilizacje/conflict/release/owner change terytorium | `GhostTerritoryAdapter` | Metody istnieja tylko w service/tests; brak call-site z nowego runtime terytoriow | BROKEN |
| 119 | Strategiczny module state wyliczany z ghost_parts | `GhostModuleStateService` | Read model dziala izolowanie; automatyczny progress zalezy od osieroconego adaptera 118 | PARTIAL |
| 120 | Jedna bezpieczna projekcja widocznosci | `build_viewer_projection` | Uzywana przez service snapshot i delta publisher; test diagnostyczny widzi publiczna czesc | OK |
| 121 | Read-only endpoint i mapa bez nowego pollera | `/api/ghostnetwork/snapshot`, JS map layer | Endpoint `run.py:17504-17580`, frontend istnieje; z pustym repo pokazuje pusty stan | OK |
| 122 | Projekcja topologii i polaczen na mapie | visibility + `static/js/map/ghostnetwork.js` | Konsument istnieje i testy kontraktowe przechodza; brak instancji topologii | PARTIAL |
| 123 | Delta scope, dedupe, recovery i snapshot | `GhostNetworkDeltaPublisher` | Discovery wrapper publikuje event (`run.py:7095-7122,7164`); territory/later events nie maja producenta | PARTIAL |
| 124 | Ability aktywne tylko z aktywnego modulu | `GhostAbilityRegistry` | Kod/testy istnieja; brak produkcyjnego resolve/apply call-site poza service | BROKEN |
| 125 | Contribution/reward ledger, RSP do profilu exactly-once | `GhostContributionService`, `GhostRewardService` | Ledger/testy istnieja; brak producenta discovery/territory reward w runtime | BROKEN |
| 126 | Obrony/odbicia z potwierdzonych wynikow terytorium | `GhostStrategicConflictService` | Implementacja tylko w service/tests; nowy post-130 engagement/CAS jej nie wywoluje | BROKEN |
| 127 | Atomowy lock kompletnego cyklu | `GhostNetworkClosureService` | Serwis/testy istnieja; brak call-site i brak osiagalnego 20/20 | BROKEN |
| 128 | Transmisja, consume, signal, restart i recovery | `GhostTransmissionService` | `start_transmission()` jest tylko fasada domenowa; brak runtime producenta | BROKEN |
| 129 | Bezpieczny narrative outbox po transmisji | `GhostNarrativePublisher` | Wywolywany jedynie przez nieosiagalne `start_transmission()` | BROKEN |
| 130 | Read-only archive/readiness i achievements | `GhostArchiveService`, endpointy archive | Endpointy `run.py:17606-17680` istnieja; bez cyklu/sygnalu nie domykaja gameplayu | PARTIAL |

`OK` oznacza zgodnosc danego read modelu/fundamentu, nie end-to-end readiness.

## 5. Pre-130 vs post-130

### PRE-130 contract path

```text
set aimed target
  -> GhostNetwork.on_target_aimed
  -> active cycle + eligibility + roll
  -> pooled part reservation
successful /gonna-win capture
  -> territory_store.save_captured_target
  -> GhostNetwork.on_target_hacked
  -> reserved part discovery + event
territory outcome event
  -> GhostTerritoryAdapter
  -> contained/active/conflict lifecycle
  -> module progress / abilities / rewards
  -> closure 20/20 -> transmission -> narrative -> archive
```

### POST-130 active path

```text
Target Registry / aimed runtime / map tool picker
  -> set_player_aimed_target                    [adapter retained]
  -> safe_ghostnetwork_on_target_aimed
  -> no_active_cycle                            [STOP]

/gonna-win launch receipt (started)
  -> expected-target guards
  -> PlayerTargetRuntime / ownership CAS
  -> territory capture / conflict pillar / reconciliation outbox
  -> territory_store.save_captured_target
  -> safe_ghostnetwork_on_target_hacked         [adapter retained]
  -> no_matching_reservation                    [STOP]
  -> finish app receipt

post-130 territory workers/events
  -X-> GhostTerritoryAdapter                    [no adapter call]
  -X-> GhostStrategicConflictService            [no adapter call]
```

Co zostalo zastapione:

- profile-only aimed/capture projection zostala rozszerzona o
  `PlayerTargetRuntimeStore`, ownership CAS, receipts i durable reconciliation;
- synchroniczna przebudowa konfliktow zostala czesciowo przeniesiona do workerow.

Co zostalo opakowane adapterem:

- aim nadal przechodzi przez `set_player_aimed_target()` i safe GN hook;
- finalny capture nadal wywoluje safe GN hook po trwalym zapisie.

Co nadal odwoluje sie do starego kontraktu:

- GN oczekuje rezerwacji utworzonej przed capture;
- territory adapter oczekuje jawnych eventow stabilizacji/contest/release, ale
  nowy konfliktowy CAS/reconciliation ich do niego nie routuje.

Co jest aktywne tylko w testach:

- cycle bootstrap;
- territory lifecycle adapter;
- ability resolution;
- strategic conflict rewards;
- closure/transmission endgame.

## 6. Pelny drop pipeline

| Krok | Istnieje | Osiagalnosc i caller | Warunki / early return | Persistence / retry |
|---|---|---|---|---|
| Target aimed | tak | `set_player_aimed_target`, cztery aktywne call-site'y `run.py:18929,20340,21877,21968` | target musi byc zapisany | target runtime/profile projection |
| Aim hook | tak | `run.py:7125-7145,7212` | exception jest fail-open | brak retry/outbox dla hooka |
| Active cycle check | tak | `reservations.py:182-188` | **obecnie no_active_cycle** | nic nie zapisuje |
| Eligibility | tak | `reservations.py:89-123,189-196` | stable id, coords, nie player/NPC/operation/incident/territory/GN, hackable | czysta decyzja |
| Clan identity | tak | `reservations.py:209-212` | brak poprawnego klanu -> `missing_player_clan` | profil tylko identity |
| Drop roll | tak | `GhostDropPolicy.should_attempt_reservation`, `reservations.py:137-152,214-215` | disabled/chance<=0 -> False bez hash RNG | deterministyczny per cycle/player/target/nonce |
| Part pool lookup | tak | `reservations.py:217-220` | tylko pooled, wyklucza klan gracza; brak -> no_candidate | repo source of truth |
| Reservation | tak | `reservations.py:222-239` | conflict/TTL | atomowe `pooled -> reserved`; idempotent target/player |
| Operation attach | tak | `service.py:216-218` | brak produkcyjnego call-site; discovery toleruje pusty operation id | opcjonalne |
| Hack accepted | tak | `/gonna-win`; capture po progach security/actions | czesciowe skany/operacje nie przechodza | app receipt/CAS |
| Capture committed | tak | `territory_store.save_captured_target`, przed hookiem GN | target/CAS guards | trwały target |
| Capture hook | tak | `run.py:25403-25417` | strict final capture, eligible, active cycle, matching reservation | fail-open; brak effect outbox |
| Part assignment | tak | `lifecycle.discover_part` | own clan, expired/mismatch, duplicate target | atomowe reserved->public |
| Domain event | tak | `ghost.part_discovered` | razem z lifecycle transaction | dedupe key |
| Delta publication | tak | `run.py:7095-7122,7164` | tylko event znaleziony w wyniku; blad wrappera nie cofa capture | delta bus, bez durable retry outbox |
| Snapshot/API | tak | `service.get_snapshot_for_viewer`, `run.py:17504-17580` | visibility per viewer | read-only repo projection |
| UI map | tak | `static/js/map/ghostnetwork.js` | wymaga projected `can_show_on_map` | snapshot + delta consumer |
| Territory containment/activation | kod tak | brak produkcyjnego caller | adapter oczekuje territory event | obecnie osierocone |
| Ability/reward/closure/transmission | kod tak | brak produkcyjnego caller | wymagaja aktywnych czesci i 20/20 | obecnie osierocone |

### Czy kazdy udany hack jest kandydatem?

Nie. Roll jest wykonywany na **aim**, nie na sam capture, i tylko dla targetow
spelniajacych `is_ghostnetwork_eligible_target()`. Wykluczone sa m.in. player,
NPC, operation, incident, territory/area/line/GN, targety z `territory_id`,
`operation_id`, `incident_id`, bez stable id/coords oraz `hackable=False`.
Aktualne zwykle targety mapy przechodza przez helper nadajacy stable id, ale
player/Victim Picker jest swiadomie niekwalifikowalny.

W obecnym runtime nawet kwalifikowalny zwykly target nie dochodzi do eligibility,
poniewaz brak cyklu jest sprawdzany wczesniej.

## 7. Exactly-once i mozliwa utrata efektu

`AppActionReceiptStore.begin()` zapisuje status `started` przed wykonaniem
ciezkiej sciezki (`database.py:5574-5686`; `run.py:24539-24574`). W
`/gonna-win` kazdy `state != "new"`, w tym `in_flight`, natychmiast zwraca replay
(`run.py:24575-24634`). Pusty in-flight receipt dostaje syntetyczny
`success=True`, `status_code=202`.

Mozliwy trace:

```text
receipt started
-> target ownership CAS / territory capture committed
-> process dies before safe_ghostnetwork_on_target_hacked
-> receipt remains started/in_flight
-> retry calls begin(), gets in_flight
-> /gonna-win returns synthetic duplicate 202
-> capture is not re-entered
-> GhostNetwork discovery is never resumed
```

Receipt jest finalizowany dopiero przez `finish_gonna_win_receipt()` po dalszych
efektach. Brakuje durable effect record/outbox lub reconciler'a typu
"captured target with committed GN reservation but no discovery event".

Ta luka moze zgubic pojedyncze efekty przy crash/timeout, ale **nie tlumaczy
calego 0/500**, gdy roll/cycle sa juz zablokowane przedtem.

## 8. Matematyka i realna liczba rolli

Skonfigurowane `p = 0.0`, drops disabled.

Dla 500 niezaleznych eligible rolli:

```text
P(0) = (1 - p)^500 = (1 - 0)^500 = 1
```

Jednak w biezacym runtime:

- hackow obserwowanych: >500 (informacja z zadania);
- aim hook calls: nieustalone z logow;
- eligibility checks: **0 po sciezce bez aktywnego cyklu**;
- RNG/hash comparisons: **0**;
- rezerwacje: **0**;
- discovery attempts z matching reservation: **0**.

Dla realnej liczby `n=0` RNG comparisons `P(0)=1`. Nawet po samym utworzeniu
cyklu, przy `enabled=False`/`p=0`, metoda policy wraca przed obliczeniem hash;
wynik nadal wynosi 0 rezerwacji z prawdopodobienstwem 1.

Kod nie definiuje niezerowej wartosci balansowej w repo. Nie znaleziono pliku
deployment/config z override `CHAOS_GHOSTNETWORK_*`. Jesli zewnetrzny deployment
ustawia inne env, nalezy uruchomic probe w tym konkretnym procesie; nie zmienia to
findingu o braku bootstrap call-site.

## 9. Evidence / findings

| Severity | Finding | Plik / linia / funkcja | Dowod | Konsekwencja |
|---|---|---|---|---|
| CRITICAL | Brak aktywnego cyklu | `ghostnetwork/cycles.py:90-102,305-306`; brak caller poza testami | read-only probe: cycle null, 0 parts | pipeline zatrzymuje sie przed eligibility |
| CRITICAL | Dropy disabled i p=0 | `config.py:131-132`; `reservations.py:137-152` | probe: false/0.0 | brak RNG comparison i rezerwacji |
| HIGH | Territory adapter orphaned | `service.py:228-241`, `territory.py:235-270` | call-site search tylko service/tests | publiczna czesc nie przechodzi do contained/active |
| HIGH | Post-130 conflict integration orphaned | nowe CAS/reconciliation w `database.py`/`run.py`; brak call do GN conflict/territory | call graph | dalszy strategiczny loop nie dziala |
| HIGH | In-flight receipt moze zgubic GN effect | `database.py:5574-5719`; `run.py:24539-24634,25403-25417` | replay nie wznawia hooka | crash po capture moze trwale zgubic discovery |
| MEDIUM | Delta bez durable retry | `run.py:7095-7122` | publish jest synchroniczny i fail-open | persistowana czesc moze wymagac snapshot recovery |
| MEDIUM | Operation attachment nie ma caller | `service.py:216-218`; brak run.py call | discovery fallbackuje po player+target | slabsza korelacja operacji, ale nie blokuje obecnego hooka |
| INFO | Source-of-truth boundary zachowana | `ghostnetwork/repository.py`, `rewards.py:383-394` | brak cycle/parts/topology w profilu | architektura storage jest poprawna |

## 10. Dead / orphaned code

Aktywne tylko domenowo/testowo albo bez producenta runtime:

- `GhostCycleService.ensure_active_cycle()` - nie jest wywolywany przy starcie;
- `GhostTerritoryAdapter.on_territory_*()` i reconciliation;
- module progress uruchamiany przez powyzszy adapter;
- `GhostAbilityRegistry.resolve/apply` - brak gameplay consumer;
- `GhostContributionService` / `GhostRewardService` dla naturalnych eventow;
- `GhostStrategicConflictService` - nowy territory engagement/CAS nie routuje
  wyniku;
- `GhostNetworkClosureService`;
- `GhostTransmissionService.start_transmission()`;
- narrative outbox finalu;
- archive achievements finalizowane po nieosiagalnej transmisji.

Nie sa martwe: repository, catalog, visibility, snapshot endpoint, frontend map,
delta publisher oraz aim/capture wrappers. Sa aktywne, lecz otrzymuja pusty stan
lub wynik bez rezerwacji.

## 11. Test diagnostyczny

Dodano `tests/test_ghostnetwork_drop_pipeline_diagnostic.py`.

Test rozroznia:

1. `roll_missed` przy policy disabled/0 i potwierdza, ze policy zostala wywolana,
   ale rezerwacja nie powstala;
2. wymuszony testowo `enabled=True, chance=1.0`;
3. `reserved` i opcjonalne dolaczenie operation id;
4. finalny capture `discovered`;
5. persistence `status=public`, anchor target id;
6. widocznosc czesci w viewer snapshot;
7. publikacje `ghost.part_discovered` w scope `ghostnetwork`.

Wynik: 2/2 OK. Test nie zmienia produkcyjnej konfiguracji; uzywa tymczasowej
bazy i wstrzyknietej policy.

Dodano tez read-only probe `tools/audit_ghostnetwork_runtime_state.py`, ktory
raportuje config, cykl, pule, rezerwacje i health bez modyfikowania gameplayu.

### Co istniejące testy dowodza

- repository/cycle/topology/lifecycle dzialaja po jawnym bootstrapie;
- chance=1 tworzy rezerwacje i discovery;
- visibility/delta/API potrafia pokazac przygotowany stan;
- rewards/conflicts/closure/transmission sa poprawne dla syntetycznych wejsc.

### Czego nie dowodza

- ze produkcyjny startup tworzy cykl;
- ze produkcyjny env wlacza dropy;
- ze realne post-130 targety generuja rezerwacje;
- ze territory CAS/worker publikuje event do adaptera GN;
- ze retry po crashu wznawia brakujacy efekt;
- ze caly loop od zwyklego klikniecia mapy do transmisji jest osiagalny.

Pelny zestaw `test_ghostnetwork*.py`: **129 testow OK**. To wynik modulowy, nie
end-to-end runtime readiness.

## 12. Root cause

Glowna przyczyna: **GhostNetwork nigdy nie zostal operacyjnie uruchomiony**.
Sprinty zbudowaly repository, katalog i cycle bootstrap, ale startup/deployment
nie wywoluje bootstrapu, a bezpieczne wartosci konfiguracyjne pozostaly
`disabled/0.0`. W konsekwencji hook aim konczy sie na `no_active_cycle`, nie ma
rezerwacji, a capture hook nie ma czego odkryc.

Przyczyna wtórna: refaktor post-130 zachowal aim/capture wrapper, ale nie
przeniosl integracji dalszych eventow GN na nowe territory CAS/reconciliation
boundaries. Nawet po naprawie drop entry point czesc zatrzyma sie na stanie
publicznym bez naturalnej aktywacji i endgame.

Przyczyna odpornosciowa: app receipt moze zatwierdzic/utrzymac capture bez
wznowienia brakujacego efektu GN po crashu.

## 13. Minimal repair boundary (bez implementacji)

Najmniejszy poprawny kolejny sprint powinien objac:

1. Jawny, idempotentny bootstrap aktywnego cyklu w kontrolowanym startup/admin
   boundary, z readiness failure gdy nie ma 20 instancji/topologii.
2. Jawna konfiguracje deploymentu dropów z niezerowym, zatwierdzonym balansem;
   bez zmiany hardcoded chance tylko pod test.
3. Telemetrie wynikow aim hook: `no_cycle`, `not_eligible`, `missing_clan`,
   `roll_missed`, `reserved`, bez ujawniania czesci graczowi.
4. Durable GN effect receipt/outbox skorelowany z kanonicznym capture, aby retry
   mogl reconcile reservation->discovery po crashu.
5. Adapter z nowych post-130 territory publication/CAS events do
   `GhostTerritoryAdapter` i `GhostStrategicConflictService`.
6. Jeden prawdziwy integration test z produkcyjnymi payloadami target registry,
   capture receipt i worker event, konczacy sie snapshotem/API.

Nie jest potrzebna przebudowa repository, katalogu, visibility ani map layer.

## 14. Regression risks

- podwojne rezerwacje lub czesci przy równoleglym aim;
- podwojne discovery/rewards przy retry capture;
- wlasna czesc klanu przy blednej normalizacji identity;
- rezerwacje pozostale po reset/cycle lock;
- ponowne wyplaty RSP przy effect reconciliation;
- aktywacja na niestabilnym lub obcym terytorium;
- konflikt pomiedzy territory ownership CAS a GN lifecycle;
- publikacja delty przed commit albo brak delty po commit;
- przeciek ukrytego part id/topologii w snapshotach;
- automatyczne utworzenie drugiego aktywnego cyklu;
- ponowna transmisja lub podwojny signal;
- zapisywanie biezacego cycle state do profilu podczas naprawy.

Kazdy z tych przypadkow wymaga testu retry/concurrency przed GO.

## 15. GO / NO-GO

**NO-GO - GhostNetwork is not currently testable end-to-end.**

Uzasadnienie: bieżący runtime nie ma aktywnego cyklu ani instancji 20 czesci,
dropy sa disabled z chance 0, a dalsze post-discovery adaptery nie maja
producentow w refaktorowanym runtime. Izolowany pipeline jest sprawny po
wymuszeniu warunkow testowych, co wyklucza persistence/UI jako glowna przyczyne,
ale nie czyni gameplay loop osiagalnym z gry.

## 16. Wykonana walidacja i zmiany

Uruchomiono:

```text
python tools/audit_ghostnetwork_runtime_state.py
python -m unittest tests.test_ghostnetwork_drop_pipeline_diagnostic -v
python -m unittest discover -s tests -p "test_ghostnetwork*.py"
python -m py_compile ghostnetwork/*.py tests/test_ghostnetwork_drop_pipeline_diagnostic.py tools/audit_ghostnetwork_runtime_state.py
```

Wyniki:

- runtime probe: drops false, chance 0.0, cycle null, parts 0, reservations 0;
- test diagnostyczny: 2/2 OK;
- pelny zestaw GhostNetwork: 129/129 OK;
- py_compile: OK.

Utworzone pliki:

- `doc/ghostnetwork_audit_110_130_post130.md`;
- `tests/test_ghostnetwork_drop_pipeline_diagnostic.py`;
- `tools/audit_ghostnetwork_runtime_state.py`.

Stan przed stagingiem (nowe pliki sa untracked, dlatego zwykly `git diff --stat`
jest pusty):

```text
 doc/ghostnetwork_audit_110_130_post130.md        | 443 ++++++++++++++++++++++
 tests/test_ghostnetwork_drop_pipeline_diagnostic.py | 116 ++++++
 tools/audit_ghostnetwork_runtime_state.py        |  39 ++
 3 files changed, 598 insertions(+)
```

Poza artefaktem audytowym i plikami stricte diagnostycznymi nie wprowadzono
zadnych zmian runtime ani konfiguracji drop-rate.
