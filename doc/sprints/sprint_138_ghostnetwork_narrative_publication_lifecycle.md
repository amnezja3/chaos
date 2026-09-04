# Sprint 138 — GhostNetwork Narrative Publication Lifecycle

Status: `138.1 COMPLETE — 138.2.pre-endgame REQUIRED / BLOCKING`

Produkcyjna generacja v3 przeszła bramkę techniczną, ale nie ręczną ocenę
treści: model dopisał relacje własności i sprawstwa, a BlackNet brzmiał raportowo.
Sprint 138 nie może utrwalać ani publikować
takich accepted-structurally candidates. V8 przekazał dla odkrycia jedno
audience-safe zdanie canonical i poprawnie odrzucił trzy BlackNety, które
pominęły wymagane nazwy. Aktywny v9 dodaje jedną audience-safe
`required_phrase`, obowiązkową w body, bez ponownego wystawiania technicznych
identyfikatorów. Produkcyjny v9 przeszedł walidację techniczną, lecz nie ręczną
ocenę języka. Aktywny v10 upraszcza prompt, a Narrative Support Layer renderuje
deterministyczny, audience-safe fallback z YAML tylko po odrzuceniu modelu.
Producer-backed v10 oraz read-only replay ostatniego eventu potwierdziły
ścieżki model-pass i support-fallback. Produkcyjna bramka 137.2 potwierdziła
output firewall oparty na dozwolonej wiedzy per audience: worker verify,
adversarial audit czterech rzeczywistych tasków i strict cutover zakończyły się
PASS. Produkcyjna bramka 137.3 potwierdziła runtime contract, obsługę SQLite
contention bez restartu procesu, retry/dead-letter/heartbeat/candidate recovery,
czystą aktywną kolejkę i stabilny proces PM2. Sprint 138 jest odblokowany.

## Audyt stanu wejściowego CHAOS — 2026-09-04

Audyt objął rzeczywisty schemat SQLite, repository, publisher, read modele
BlackNet/Googleplex/Cyberner, backendowe i frontendowe allowlisty CTA oraz testy
regresyjne. Nie zmieniał runtime ani danych. Wynik: obecny pipeline kończy się
poprawnym, trwałym i audience-filtered medium recordem, ale po publikacji nie ma
jeszcze ogólnego lifecycle GhostNetwork. Sprint 138 nie buduje publishera od
zera — rozszerza istniejący read model o aktywność, wygaszanie, ciągłość stanu,
selekcję i działające CTA.

| Obszar | Stan | Dowód / rzeczywista luka |
|---|---|---|
| Candidate -> publication receipt | `COMPLETE` | bounded staging accepted candidates i trwała identity receipt |
| Claim/lease/recovery publishera | `COMPLETE` | CAS lease, odzyskanie expired claim i terminalne odrzucenie |
| Exactly-once medium record | `COMPLETE` | unique `publication_receipt_id`, atomowy insert i acknowledgement |
| Audience isolation | `COMPLETE` | backendowe zapytania public + zgodny clan/owner; brak filtrowania prywatności w UI |
| BlackNet publication bridge | `COMPLETE / BASIC` | narracje są scalane z istniejącym feedem, bounded i deduplikowane po canonical fact refs |
| Googleplex publication bridge | `COMPLETE / SLOT-BASED` | `ghost_narrative_slot_state` wskazuje aktywny medium record, a slot assignment używa CAS |
| Cyberner owner publication | `COMPLETE / NARROW` | owner-scoped rekord jest zwracany wyłącznie dla zgodnego ownera i source receipt |
| Lifecycle medium record | `MISSING` | brak `active_state`, `valid_from/until`, supersession i invalidation metadata |
| Thread head/history | `PARTIAL` | `narrative_thread_id` istnieje w outboxie, lecz nie przechodzi do medium recordu ani zapytań feedu |
| Significance/priority | `PARTIAL` | `priority` i significance metadata istnieją przed publikacją, lecz read model ich nie zachowuje i nie selekcjonuje po nich |
| BlackNet mix/presentation | `MISSING` | każda narracja ma generic `signal_type=narrative_publication`, `importance=1`, `layout=2`; wybór jest newest-first |
| Expiry/state invalidation | `MISSING` | read query nie filtruje aktywności ani TTL; canonical transition nie unieważnia poprzedniego recordu |
| GhostNetwork CTA | `MISSING` | pięć planowanych akcji nie występuje równocześnie w backend allowlist, BlackNet dispatcher i Googleplex action allowlist |
| Failure coverage 138 | `PARTIAL` | istnieją testy lease/crash/idempotency/SQLite classification; brak failure testów nowego lifecycle i invalidation |
| Producer-backed E2E do UI | `MISSING` | nie ma dowodu pełnej linii dla rodzin part/conflict/machine/cycle/signal aż do aktywnej karty i klikniętego CTA |
| Heavy profile | `BASELINE PASS` | publisher/read modele używają bounded projection; 138 musi utrzymać wszystkie liczniki równe zero |

Lokalna regresja audytowa:

```text
python -m unittest \
  tests.test_narrative_publications \
  tests.test_llm_publishers \
  tests.test_blacknet_incident_bridge \
  tests.test_googleplex_news \
  tests.test_googleplex_news_endpoint \
  tests.test_narrative_cutover -q

Ran 56 tests in 47.668s
OK
```

Wniosek wykonawczy: najpierw `138.1` implementuje lifecycle projection, active
head, invalidation, mix/presentation i CTA na obecnym publisherze. Dopiero
`138.2` zamyka producer-backed E2E, failure injection i soak. Historyczne
medium records pozostają historią; audyt nie autoryzuje ich automatycznego
backfillu lub reaktywacji.

## Realizacja 138.1 — 2026-09-04

Dodano `ghostnetwork-publication-lifecycle-v1` jako backend-owned, addytywny
kontrakt nowych medium records. Publisher przenosi z taska, a nie z tekstu
modelu:

```text
narrative_thread_id / event_family / significance / priority
source_state_version / semantic_contract_version
active_state / valid_from / valid_until
supersedes_medium_record_id / invalidated_by_event_id / invalidation_reason
presentation_family / publication_mode
```

Już enqueue lub merge nowszego canonical taska tego samego threadu, medium i
audience atomowo oznacza poprzedni active head jako `invalidated`. Dzięki temu
stara karta znika z read modelu także wtedy, gdy Ollama, validator albo publisher
ulegną awarii przed utworzeniem następcy. Późniejsza publikacja nowej wersji
wiąże ją z poprzednikiem przez `supersedes_medium_record_id`.

Spóźniony task o niższym `world_state_version` kończy się
`lifecycle_state_superseded` i nie może zastąpić nowszego stanu. Dotyczy to także
kandydata oczekującego na publikację w chwili pojawienia się nowszego taska;
backend porównuje canonical task watermark, a nie dostępność wyniku modelu.
Równa wersja jest rozstrzygana przez trwały czas utworzenia taska. Bounded expiry
zmienia dojrzałe rekordy `active -> expired`; active read modele dodatkowo
filtrują TTL, więc nawet przed materializacją expiry nie pokażą przeterminowanej
treści.

Historyczne rekordy po addytywnej migracji otrzymują stan `legacy`. Są dostępne
w zapytaniu historycznym/audytowym, ale nie wracają automatycznie do aktywnego
feedu. Googleplex nadal ma jeden head wskazany przez istniejący slot CAS.
Cyberner AGI czyta wyłącznie aktywne owner records.

BlackNet zachowuje istniejący limit udziału narracji, ale wybiera je według
`critical -> high -> normal -> low`, następnie priority i świeżości. Jeden
thread może zajmować najwyżej jedną kartę. Code-owned `presentation_family`
zastępuje generic `narrative_publication`; significance wyznacza importance,
layout i techniczny tone karty.

Pięć CTA GhostNetwork jest spiętych przez backend allowlist, BlackNet,
Googleplex i frontend dispatcher. Part/territory otwierają GhostNetwork Suite
na canonical `public_entity_id`, suite otwiera istniejącą projekcję, Cyberner
używa istniejącego kanału, a GhostSignal otrzymał mały read-only surface oparty
na istniejących endpointach archiwum. Endpoint archiwum używa lightweight
identity projection i ignoruje próbę podniesienia prywatności przez
`?private=1`.

Dodano read-only audit:

```text
scripts/audit_narrative_publication_lifecycle.py --db data/game.sqlite3 --strict
```

Audit wykrywa aktywny rekord po TTL, brak lifecycle metadata, incomplete
invalidation lineage oraz więcej niż jeden aktywny head threadu. Rekordy
`legacy` są ostrzeżeniem, nie błędem. Ten sam blok jest częścią strict cutover.

Lokalna bramka po implementacji:

```text
Python/JavaScript syntax: PASS
publication/lifecycle/read-model/CTA/producers regression: 119 tests / PASS
git diff --check: PASS
```

138.1 przeszedł wdrożenie i bramkę serwerową. Produkcyjny lifecycle audit,
supersession po kolejnym stanie tego samego threadu oraz ręczne CTA zostały
potwierdzone. 138.2 jest odblokowany.

### Produkcyjna aktywacja i poprawka Support Layer — 2026-09-04

Pierwszy event `part_activated` po wdrożeniu utworzył cztery taski v10. Rekord
`blacknet/owner` przeszedł model validation i został opublikowany z poprawnym
threadem, TTL, significance, priority, presentation family oraz canonical CTA.
Pozostałe trasy (`blacknet/clan`, `blacknet/public`,
`googleplex_news/public`) zakończyły się `voice_semantic_detail_missing`.

Przyczyną nie był lifecycle ani output firewall. Model pominął nazwę obiektu,
a konfiguracja Narrative Support Layer zawierała fallback wyłącznie dla
`part_discovered`. Dodano audience-safe, deterministyczne warianty
`part_activated` dla wszystkich czterech tras. Public/clan/Googleplex renderują
wyłącznie canonical `{location}`, owner może dodatkowo użyć canonical
`{part_name}`. Żadna wartość nie pochodzi z tekstu modelu.

Lokalna walidacja poprawki: 76 testów Support Layer, workera, output safety,
cutover, generation audit i policy — PASS; `git diff --check` — PASS. Historyczny
event może zostać sprawdzony read-only przez support replay, bez ponownej
aktywacji części. Bramka serwerowa pozostaje otwarta do wdrożenia poprawki.

Ręczna próba CTA ujawniła dodatkową granicę: konstruktor GhostNetwork Suite jest
zawsze obecny w głównym bundle, więc samo sprawdzenie funkcji nie dowodzi
instalacji aplikacji. CTA sprawdza teraz canonical `toolbarProfile.apps` (z
fallbackiem do `/api/profile`) przed otwarciem Suite. Brak instalacji kończy się
kontrolowanym blokiem i pojedynczym system message kierującym do Googleplex;
zainstalowana aplikacja zachowuje dotychczasowy fokus części. Regresja CTA,
Googleplex, BlackNet i frontend contracts: 40 testów oraz dedykowany test Node —
PASS.

Produkcyjny test `active -> contained` potwierdził zgodny event, wersję i thread,
ale stary head pozostał aktywny. Przyczyną był proces `chaos-territory-worker`
(PM2 14), który tworzy event i taski, lecz nie został zrestartowany przy
wdrożeniu lifecycle. Dodano również samonaprawę: idempotentny replay istniejącego
taska ponawia teraz canonical invalidation. Dzięki temu restart i kontrolowany
replay naprawią rekord bez ręcznej edycji SQLite. Dedykowany test stale-producer
oraz pełna regresja lifecycle/CTA: 78 testów Python i test Node — PASS.

Poprawkę wdrożono jako `e8666ec` i zrestartowano PM2 13/14/17/18. Kontrolowany
replay `event_7e26b277b1015367` zwrócił cztery istniejące taski jako idempotentne,
bez błędów. Rekord `part_activated` w wersji 951 przeszedł do `invalidated`, ze
źródłem `event_7e26b277b1015367`, powodem `canonical_state_observed` i bez
ręcznej zmiany bazy. Strict lifecycle audit: `ok=true`, zero active-expired,
missing-contract, duplicate-head i broken-lineage; 13 active, 2 expired,
1 invalidated oraz 500 oczekiwanych legacy records. Lifecycle/supersession ma
produkcyjny SERVER PASS. Do pełnego zamknięcia 138.1 pozostaje ręczna próba CTA
na koncie bez zainstalowanego GhostNetwork Suite.

## Fundament odziedziczony z 137.pre.1 — 2026-09-03

Sprint 138 nie publikuje surowego canonical eventu ani tekstu zbudowanego z
technicznych identyfikatorów. Obowiązującym wejściem generation pipeline jest
`chaos-llm-semantic-input-v1`, zaliczony na produkcji dla czterech tasków
`part_discovered` (`ok=true`, `errors=[]`, zero technical identifier leaks).

```text
canonical event
  -> deterministic domain converter
  -> audience projection
  -> semantic facts: statement + allowed labels/location/attributes
  -> bounded model package z task-local aliases
  -> validated candidate z canonical lineage odtworzonym przez backend
  -> publication lifecycle 138
```

`semantic_provenance`, canonical IDs oraz mapowanie `f01 -> canonical fact_id`
pozostają backend-only. Medium record może zachować canonical lineage potrzebne
do dedupe, invalidation i exactly-once, ale read model nie może wystawić tych
identyfikatorów tylko dlatego, że są dostępne publisherowi.

Location z 137.pre.1 pochodzi wyłącznie z zachowanego canonical kontekstu
OSM/target/capture. Sprint 138 może opublikować dozwolone `city/country`, lecz
nie wykonuje geocodingu, nie publikuje surowych współrzędnych i nie odtwarza
lokalizacji z tekstu modelu. Konflikt lub brak canonical dowodu pozostaje
UNKNOWN.

## Korekta po audycie Sprintu 136 — 2026-09-02

Publication lifecycle nie może być zatwierdzony na podstawie candidate
wstawionego ręcznie do środka pipeline'u. Incydent z realnym dropem pokazał,
że downstream może być zdrowy, gdy upstream nie tworzy żadnego taska.

Remediacja 136.1 ma lokalny i serwerowy PASS: historyczny event odzyskał taski,
nowy realny drop utworzył je bezpośrednio, a strict lineage audit jest zielony.
Historyczny blocker zaakceptowanych producer-backed candidates został usunięty
w 137.1/137.1.1, a 137.2 i 137.3 zaliczyły swoje bramki serwerowe. Na dzień
2026-09-04 Sprint 138 jest odblokowany; bieżącą luką jest lifecycle publikacji,
nie semantic package ani walidacja outputu.

Pełny test Sprintu 138 musi zaczynać się od produkcyjnego entrypointu domeny:

```text
runtime action
  -> committed mechanic/capture effect
  -> persisted GhostNetwork event
  -> expected task identities
  -> audience-safe semantic package
  -> model attempt
  -> accepted candidate
  -> publication receipt
  -> medium record
  -> audience-filtered read model
  -> CTA dispatcher
```

Wstrzyknięcie taska, candidate albo receipt jest dozwolone w testach
jednostkowych danego komponentu, lecz nie spełnia E2E ani Definition of Done.

### Bramka kompletności linii pochodzenia

Strict audit przed i po publication soak raportuje bounded liczniki:

```text
eligible_events_without_expected_task
tasks_without_source_event
completed_tasks_without_candidate
accepted_candidates_without_receipt
published_receipts_without_medium_record
medium_records_without_receipt
records_with_wrong_source_or_audience
duplicate_records_by_publication_identity
records_exposing_technical_identifiers
records_with_location_beyond_semantic_projection
```

Każdy licznik wynosi zero poza jasno zdefiniowanym grace period dla aktywnie
przetwarzanego elementu. Globalne historyczne sumy publikacji według medium
nie są dowodem kompletności nowego eventu.

## Kontekst po Sprintach 135.5–135.6

Historyczny Sprint 138 miał podłączyć zwalidowany output do BlackNetu i
utworzyć publisher. Canonical roadmap 135.5–135.6 już dostarczyła:

```text
accepted candidate
  -> publication receipt
  -> claimed publication
  -> medium record
  -> audience-filtered read model
```

Sprint 138 nie tworzy drugiego feedu ani publishera. Domyka lifecycle historii
GhostNetwork po publikacji: dyspozycję CTA, priorytetową rotację, TTL,
supersession, invalidation, thread continuity i pełne E2E.

## Potwierdzony baseline

Obecny system zapewnia:

- bounded staging accepted candidates;
- publication receipt i exactly-once medium record;
- claim/lease oraz kontrolowane odrzucenie unsafe candidate;
- audience scopes `public`, `clan`, `owner` filtrowane backendowo;
- BlackNet read model łączący narracje z deterministic world signals;
- maksymalnie bounded liczbę narracji na snapshot;
- semantic dedupe po canonical `fact_refs`;
- wyciszenie deterministic karty, jeżeli jej fact został już opublikowany
  narracyjnie;
- generic duplicate-content guard;
- Googleplex News slot CAS i `slot_assignment_superseded`;
- brak profilu w publisherze i bounded identity projection w endpointach;
- produkcyjnie zweryfikowany Shared Semantic Input Layer, audience projection,
  canonical label/location retention oraz technical-ID firewall przed modelem;
- backendowe mapowanie task-local fact aliases do canonical lineage przed
  stagingiem candidate.

Historyczny wspólny baseline Sprintów 137–138: `59 tests / PASS`. Bieżący audyt
138 potwierdził dodatkowo właściwy zestaw publication/read-model/cutover:
`56 tests / PASS`.

## Rzeczywista luka Sprintu 138

- `ghost_narrative_medium_records` nie ma canonical TTL, active/inactive state,
  `supersedes` ani `invalidated_by_event_id`;
- brak stabilnego thread identity w medium record;
- BlackNet każdy narrative record mapuje do generic
  `signal_type=narrative_publication`, `importance=1`, `layout=2`;
- obecny selection wybiera najnowsze semantyczne fakty, ale nie rozumie
  significance, critical bypass, cooldown ani udziału GhostNetwork w miksie;
- CTA GhostNetwork istnieją w narrative contract, ale nie należą jeszcze do
  `BLACKNET_ALLOWED_CTA_ACTIONS` i nie mają dispatcherów UI;
- brak state-transition invalidation, np. contested -> resolved lub
  machine_online -> machine_offline;
- brak pełnego E2E dla eventów 136 i candidates 137;
- Narrative Support Layer obsługuje odrzucony output modelu przed candidate;
  osobna polityka publikacji critical eventu po niedostępności modelu albo
  wyczerpaniu retry pozostaje nierozstrzygnięta i nie może być mylona z tym
  działającym fallbackiem walidacyjnym.

## Cel

Zatwierdzona narracja GhostNetwork ma pojawić się dokładnie raz, tylko
właściwym odbiorcom, we właściwej pozycji rotacji i tylko tak długo, jak jej
canonical stan pozostaje aktualny.

```text
candidate 137
  -> existing publication receipt
  -> lifecycle projection
  -> active medium record
  -> BlackNet / GGPL News / Cyberner read model
  -> CTA dispatcher
```

## Bezwzględna bramka heavy profile

Publisher, lifecycle resolver, feed, CTA i invalidation zachowują:

```text
profile_full_read:           0
profile_full_write:          0
profile_bytes:               0
account_scan:                0
all_user_profile_scan:       0
per_recipient_profile_read:  0
```

Audience i CTA pochodzą z taska/candidate/medium record albo bounded canonical
lookup. Frontend nie otrzymuje pełnego wpisu z poleceniem samodzielnego
odfiltrowania. Publisher nie odświeża mapy, operacji, plików, GX ani walleta.
Publisher nie doczytuje również surowego event payloadu w celu „ulepszenia”
tekstu lub lokalizacji; korzysta z zatwierdzonego candidate i backend-owned
lineage/lifecycle metadata.

## Canonical publication lifecycle

Addytywne pola medium record lub osobna lekka tabela lifecycle powinny
przechowywać:

```text
narrative_thread_id
event_family
significance
priority
active_state
valid_from
valid_until
supersedes_medium_record_id
invalidated_by_event_id
invalidation_reason
semantic_contract_version
```

Nie przepisujemy historycznych publications i nie usuwamy receipts. Stary
rekord bez lifecycle metadata pozostaje historyczny, ale nie jest automatycznie
reaktywowany ani backfillowany przy starcie.

## Reguły aktywności

Przykładowy backend-owned kontrakt:

| Event | TTL / zakończenie |
|---|---|
| discovery | bounded medium TTL albo containment |
| containment | reveal, activation lub utrata terytorium |
| contested | conflict resolved |
| activation | deactivation, contest lub kolejny ważniejszy stan |
| machine online | machine offline lub version transition |
| cycle locked | signal sent albo cycle transition |
| signal sent | stabilizacja/version transition |
| low aggregate | krótki TTL |

Nowy event może unieważnić poprzedni record tylko przez canonical
thread/source relation. Podobieństwo tekstu nie jest podstawą zmiany stanu.

## Thread continuity

Read model może oznaczyć kolejny aktywny wpis jako kontynuację, ale nie musi
ładować pełnej historii:

```text
discovery -> containment -> contested -> recovery -> activation
machine progress -> machine online -> machine offline
cycle locked -> signal sent -> stabilization -> version changed
```

Endpoint pobiera bounded aktywny head wątku. Archiwum może czytać bounded
historyczne records osobnym zapytaniem.

## BlackNet mix policy

Istniejący limit narracji pozostaje, ale selection uwzględnia:

1. critical active event;
2. high active event;
3. najnowszy normal event;
4. low aggregate tylko, gdy nie wypiera ważniejszego sygnału;
5. pozostałe deterministic world signals.

Reguły:

- critical może ominąć zwykły cooldown, ale nie dedupe i exactly-once;
- jeden thread nie zajmuje wielu kart tym samym stanem;
- clan/owner record nie zmniejsza publicznego limitu innego odbiorcy;
- intensywny konflikt GhostNetwork nie może wyprzeć całego BlackNetu;
- narrated fact wycisza deterministic odpowiednik, ale nigdy odwrotnie;
- inactive/expired record nie bierze udziału w miksie.

## Typy prezentacji

Backend mapuje `event_family/significance`, nie tekst modelu, na istniejące
warianty karty:

```text
ghost_discovery
ghost_containment
ghost_conflict
ghost_activation
ghost_recovery
ghost_machine
ghost_cycle
ghost_signal
ghost_system_transition
```

Nie wymagamy osobnego CSS dla każdego typu. Nie wolno jednak redukować
wszystkich eventów do `importance=1` i identycznego neutralnego layoutu.

## CTA i dispatchery

Sprint 136 ustala canonical CTA i payload. Sprint 137 zachowuje je podczas
walidacji. Sprint 138 dodaje do allowlisty oraz implementuje istniejącymi
surface'ami:

```text
show_ghostnetwork_part
show_ghostnetwork_territory
open_ghostnetwork_suite
open_ghostsignal_archive
open_cyberner_channel
```

Zasady:

- ukryta część nigdy nie dostaje CTA ujawniającego node;
- CTA nie teleportuje bez decyzji gracza;
- nieznana, wygasła lub niewidoczna capability kończy się read-only;
- frontend nie konstruuje targetu z tytułu ani tekstu modelu;
- payload pochodzi wyłącznie z medium record;
- label i location w CTA pochodzą z canonical target/capability zapisanych
  przed LLM, nigdy z `candidate.body` ani swobodnej interpretacji modelu;
- task-local alias `f01` nie może trafić do payloadu UI — publisher korzysta z
  canonical fact ID odtworzonego przez backend po walidacji.

## Googleplex News i Cyberner

- Googleplex News nadal używa jednego `gp-home-world-grid` oraz slot CAS;
- lifecycle może unieważnić source, ale nie tworzy dodatkowego HERO;
- przegrany slot assignment jest terminalny i audytowalny;
- Cyberner zachowuje audience scope i istniejący kanał;
- model output nie może przekierować publikacji do innego medium.

## Fallback policy

Domyślnie rejected/dead-letter task nie tworzy postu udającego odpowiedź
modelu. Dla critical canonical eventu można włączyć krótki backendowy fallback
wyłącznie gdy:

- model wyczerpał retry albo jest operatorsko wyłączony;
- fakty są nadal aktualne;
- nie istnieje już medium record dla tej publication identity;
- fallback używa tego samego source/audience/thread identity;
- publikacja zostaje oznaczona `publication_mode=deterministic_fallback`;
- późniejsza narracja nie publikuje drugiego wpisu dla tego samego stanu.

Fallback nie dotyczy owner-analysis AGI i nie może udawać odpowiedzi
Cybernera. Decyzja o jego aktywacji wymaga osobnego failure testu w 138.2.

## 138.1 — lifecycle, mix i CTA

1. Dodać addytywny lifecycle contract i bounded indeksy.
2. Przenieść thread/significance/priority z taska do medium record.
3. Wprowadzić active/expired/invalidated filtering.
4. Dodać supersession dla canonical state transitions.
5. Rozszerzyć BlackNet mix policy bez drugiego feedu.
6. Dodać GhostNetwork presentation families.
7. Podłączyć canonical CTA do allowlisty i dispatcherów.
8. Zachować `semantic_contract_version` i audytowalne canonical lineage bez
   ujawnienia provenance ani technicznych ID w read modelu.

## 138.2.pre-endgame — wymagana bramka debiutu cyklu i GhostSignalu

Status: `REQUIRED / BLOCKING — DO NOT TRIGGER 20/20`

### Powód bramki

Cykl i GhostSignal nie miały jeszcze produkcyjnego debiutu. Zebranie następnych
20 części będzie kosztowne, dlatego bieżącego stanu nie wolno zużyć jako testu
integracyjnego, dopóki cały finał nie ma automatycznego recovery i jednoznacznego
runbooka. Istniejące usługi domenowe poprawnie realizują lock, immutable snapshot,
transmisję i idempotencję, ale produkcyjna orkiestracja nie domyka wszystkich
skutków ubocznych.

Bramka obejmuje dokładnie przejście:

```text
ostatnia aktywacja części
  -> machine_progress_changed + machine_online
  -> readiness 20/20, 20 connections, 4/4 machines
  -> cycle_locked + immutable lock snapshot
  -> GhostSignal transmission
  -> rewards / archive / consumed parts / closed connections
  -> signal_sent + version_changed + restart_required
  -> stabilization_started
  -> stabilizing deadline
  -> closed old cycle
  -> new active cycle with 20 pooled parts and valid topology
```

### Ponownie potwierdzony baseline

- readiness jest fail-closed: wymaga dokładnie 20 części, 20 połączeń, czterech
  maszyn po 5/5, poprawnego topology checksum, prawidłowych anchors i territory
  clans oraz braku nierozstrzygniętych konfliktów;
- lock zapisuje atomowy, immutable snapshot i deduplikuje `cycle_locked`;
- transmisja korzysta wyłącznie z lock snapshotu, tworzy jeden signal per cycle,
  jest idempotentna i wewnątrz jednej transakcji tworzy rewards, historical nodes,
  zużywa części, usuwa połączenia, zmienia wersję oraz rozpoczyna stabilizację;
- istnieje jawne `resume_interrupted_transmission(cycle_id)`;
- archive i canonical narrative producers istnieją dla `cycle_locked`,
  `signal_sent`, `version_changed` i `stabilization_started`;
- lokalna regresja closure/transmission/archive/runtime/narrative/module/cycle:
  `53 tests / PASS`;
- rozszerzona regresja delta/audience/reward CAS/readiness/publication/CTA/SFX:
  `63 tests / PASS` oraz frontend Suite live-delta Node `PASS`.

Baseline komponentów nie jest zgodą na produkcyjny trigger. Obecny test runtime
kończy się świadomie na `stabilizing` i asercyjnie nie tworzy następnego cyklu.

### Luki P0 blokujące 20/20

#### P0.1 — trwały endgame reconciler

`maybe_finalize_ghostnetwork_cycle()` obsługuje wyłącznie cykl `active`. Jeżeli
proces zakończy się po commitcie locka, kolejny tick zobaczy `transmitting` i nie
wywoła istniejącego recovery. Job terytorialny może wtedy zakończyć się sukcesem,
chociaż transmisja nie została wznowiona.

Wymagane:

- jeden bounded `advance_ghostnetwork_endgame_once()` uruchamiany z PM2 14 na
  stałej kadencji, niezależnie od pojawienia się kolejnego territory joba;
- `active + ready` wykonuje lock, następnie transmission;
- `transmitting + valid lock` wykonuje `resume_interrupted_transmission`;
- `transmitting` bez poprawnego lock snapshotu zatrzymuje się fail-closed i
  emituje alarm, bez tworzenia sygnału;
- `stabilizing` przed deadline naprawia brakujące post-commit efekty: archive,
  persisted-event narrative/delta enqueue oraz uruchomienie reward projectora;
- `stabilizing + deadline due` atomowo zamyka stary cykl i inicjuje kolejny;
- CAS/lease gwarantuje jednego wykonawcę, a każdy etap może być bezpiecznie
  ponowiony po restarcie procesu lub SQLite contention;
- stan oraz ostatni błąd są widoczne w bounded diagnostyce.

#### P0.2 — durable final rewards projection

Transmisja tworzy w ledgerze nagrody holderów oraz closera, lecz produkcyjny
endgame nie projektuje ich automatycznie do profili. Nie wolno pozostawić ich
bezterminowo jako `pending` ani zapisywać profili w szerokiej transakcji sygnału.

Wymagane:

- bounded kolejka/projektor korzystający z istniejącego guarded profile CAS;
- retry pending reward po awarii przed zapisem i po zapisie profilu;
- dokładnie jeden przyrost RSP per `reward_key`;
- finalizacja ledgera dopiero po trwałym zapisie profilu;
- brak pełnego account scan i brak utrzymywania wielu profili w transakcji
  GhostSignalu;
- diagnostyka pending/applied/rejected oraz oldest pending.

#### P0.3 — delivery eventów finału i trwały restart state

Serwis domenowy dispatchuje narrację, lecz endgame tworzony po normalnym
`apply_ghostnetwork_runtime_result()` nie przechodzi obecnie przez ten sam durable
delta delivery. Otwarty klient może więc nie otrzymać finału. Dodatkowo Suite
ustawia `restartRequired` po live delta, ale viewer snapshot nie utrwala pełnych
pól restartu; odświeżenie strony może zgubić komunikat.

Wymagane:

- enqueue każdego persisted endgame eventu do istniejącej durable delta queue;
- dedupe po canonical event identity oraz snapshot recovery po utracie delty;
- dostarczenie do wszystkich kwalifikujących się odbiorców bez cichego ucięcia
  na obecnym limicie pierwszych 500 kont; batching pozostaje bounded;
- viewer-safe cycle projection zawierająca `restart_required`, wersję source/to,
  `restart_signal_id` lub bezpieczny public alias oraz `stabilization_until`;
- po świeżym wejściu i po reloadzie ten sam stan `RESTART GHOSTSYSTEMU WYMAGANY`;
- pojedynczy system message na signal/version, bez toast stormu;
- wszystkie akcje GhostNetwork wyłączone po locku, również po snapshot recovery;
- test public/clan/owner oraz klienta, który był offline podczas transmisji.

#### P0.4 — rollover po stabilizacji

Po transmisji istnieje `stabilization_until`, lecz nie ma produkcyjnego call-site
dla `stabilizing -> closed -> create_next_cycle`. Bez niego GhostNetwork pozostaje
trwale bez dropów po wykorzystaniu bieżących 20 części.

Wymagane:

- deadline oparty na czasie backendu, nie timerze przeglądarki;
- przed rolloverem hard settlement potwierdza poprawny signal, consumed parts,
  zamknięte connections, historical nodes i utworzone reward rows; awaria Ollamy
  nie blokuje mechaniki następnego cyklu, lecz pozostaje retryable i audytowalna;
- idempotentne zamknięcie starego cyklu;
- dokładnie jeden nowy cykl, 20 pooled parts, rozkład 5/klan i poprawny ring 20;
- nowy `ghost.cycle_activated` oraz durable delty/narracje;
- brak dziedziczenia consumed parts, reservations i aktywnych connections;
- zachowanie terytoriów i archiwum starego cyklu;
- recovery po crashu pomiędzy `closed` i utworzeniem/aktywacją nowego cyklu;
- dropy pozostają wyłączone przed deadline i wracają dopiero dla nowego `active`.

#### P0.5 — publikacja i fallback jednorazowych komunikatów

`signal_sent` kieruje treść do BlackNet, Googleplex News, Cybernera i `radio`, ale
canonical publisher obsługuje tylko trzy pierwsze media. Narrative Support Layer
ma warianty wyłącznie dla `part_discovered` i `part_activated`. Pojedynczy słaby
output modelu może więc odebrać debiutowi kluczową publikację.

Wymagane:

- jawna decyzja kontraktowa: wdrożyć canonical radio publication albo usunąć
  `radio` z targetów pierwszego debiutu; task skazany na
  `unsupported_target_medium` jest niedopuszczalny;
- audience-safe fallbacki YAML dla gwarantowanych komunikatów BlackNet/GGPL:
  `machine_online`, `cycle_locked`, `signal_sent`, `version_changed`,
  `stabilization_started` i nowego `cycle_activated`;
- fallback nie wymyśla odpowiedzi z 2108 ani outcome sygnału;
- Cyberner zachowuje zasadę braku udawanej odpowiedzi AGI: retry ma bounded
  terminal, a brak poprawnej odpowiedzi jest raportowany jako jawny kontrolowany
  outcome i nie blokuje mechaniki ani gwarantowanych komunikatów;
- radio ma canonical, obsługiwany publication/player contract albo zostaje jawnie
  wyłączone z fan-out pierwszego debiutu; nie korzysta z nieistniejącego CTA;
- CTA `open_ghostsignal_archive` działa po publikacji i po reloadzie;
- radio CTA używa rzeczywiście obsługiwanej nazwy akcji i istniejącego playera;
- E2E każdej oczekiwanej trasy kończy się `published` albo udowodnionym,
  kontrolowanym slot supersession — nigdy przypadkowym dead letterem.

### Crash windows wymagające testu

| Punkt awarii | Oczekiwane recovery |
|---|---|
| przed lockiem | cykl pozostaje `active`; następny tick ponawia readiness |
| po lock commit, przed signal | reconciler rozpoznaje `transmitting` i wznawia |
| w środku transakcji signal | rollback mechaniki; lock pozostaje; retry tworzy jeden signal |
| po signal commit, przed delta/narrative | persisted-event sweep uzupełnia delivery bez powtórzenia mechaniki |
| podczas reward profile save | ledger pozostaje retryable; RSP nie nalicza się podwójnie |
| po profile save, przed ledger finalize | receipt/reward key rozpoznaje zapis i finalizuje bez drugiego RSP |
| podczas SQLite busy/locked | bounded backoff, PM2 pozostaje online, brak tight loop |
| restart PM2 14 w `transmitting` | automatyczny resume bez komendy operatora |
| restart PM2 14 w `stabilizing` | zachowany deadline i późniejszy dokładnie jeden rollover |
| dwóch wykonawców równocześnie | CAS/lease: jeden lock, signal, archive i next cycle |
| Ollama/publisher offline | gameplay kończy się; taski retry/support odzyskują publikację |

### Read-only preflight przed ostatnią aktywacją

Musi powstać jeden skrypt `scripts/audit_ghostnetwork_endgame_preflight.py`, który
nie mutuje bazy i w `--strict` failuje przed 20/20, jeżeli nie potwierdzi:

- dokładnie jednego cyklu `active`, bez lock snapshotu i bez istniejącego signal;
- 20 części, 20 połączeń, poprawnego checksumu i czterech maszyn;
- dla stanu 19/20: dokładnie jednej nieaktywnej części oraz wszystkich pozostałych
  anchors/territories/state versions poprawnych;
- zero unresolved strategic conflicts i zero active reservations niezwiązanych
  z planowaną ostatnią częścią;
- brak zaległych endgame jobs oraz brak starych pending final rewards;
- PM2 14, 17 i 18 online, poprawne env i brak crash loop;
- Ollama verify, prompt registry, output safety, narrative cutover i publication
  lifecycle audit `ok=true`;
- obsługę każdego medium/CTA z finalnego fan-out;
- wolne miejsce, poprawny SQLite health i wykonaną bezpieczną kopię `.backup`.

Preflight raportuje również dokładne `cycle_id`, ostatnią część, maszynę,
oczekiwany next version, liczbę przyszłych rewards oraz listę oczekiwanych eventów
i mediów. Nie wolno opierać zgody na ręcznym zestawie luźnych SELECT-ów.

### Zbiorczy postflight

Musi powstać jeden read-only `scripts/audit_ghostnetwork_endgame.py --cycle-id ...
--strict`, który łączy i asercyjnie sprawdza:

- jeden lock snapshot i zgodny checksum;
- jeden signal, właściwy source/next version i immutable payload;
- dokładnie po jednym canonical evencie każdego wymaganego typu;
- 20 consumed parts, zero aktywnych reservations i zero live connections;
- 20 historical nodes oraz komplet archive/achievement finalization;
- oczekiwaną liczbę final rewards, dokładnie jeden reward key, zero osieroconych
  pending po zakończeniu reward projectora;
- durable delta jobs/delivery dla wszystkich endgame events;
- komplet task -> attempt -> candidate -> receipt -> lifecycle record lub jawny
  dozwolony terminal per medium;
- poprawne supersession starych kart cycle/machine oraz brak audience leaks;
- status `stabilizing` przed deadline, a po deadline stary `closed` i dokładnie
  jeden nowy `active` cycle z poprawnym katalogiem/topologią.

Postflight musi dać sensowny wynik również w połowie procesu: `in_progress` z
listą brakujących etapów, a nie fałszywy PASS ani lawinę wtórnych błędów.

### Kontrolowany production runbook

1. Zatrzymać zmiany wdrożeniowe; zapisać HEAD, PM2 status/env i timestamp.
2. Wykonać SQLite online backup bez zatrzymywania aplikacji.
3. Uruchomić strict preflight; wymagane `ok=true`, `ready_after_last_part=true`.
4. Otworzyć równolegle logi PM2 14, 17 i 18 oraz bounded watch kolejki/eventów.
5. Aktywować ostatnią część wyłącznie realnym gameplay entrypointem.
6. Nie wykonywać ręcznych UPDATE/INSERT ani drugiego triggera.
7. Obserwować dokładnie jeden lock, signal i przejście do `stabilizing`.
8. Uruchomić postflight dla machine/cycle/signal oraz narrative E2E wszystkich
   tasków; zapisać identyfikatory całej linii.
9. Sprawdzić system message/restart po live delta i po świeżym logowaniu.
10. Potwierdzić nagrody holderów i closera na kilku profilach oraz zero pending.
11. Po deadline potwierdzić dokładnie jeden nowy `active` cycle i ponowne dropy.
12. Dopiero wtedy oznaczyć cycle/signal family gates 138.2 jako SERVER PASS.

### Procedura awaryjna

- `active` bez locka: nie zmieniać bazy; usunąć przyczynę readiness i pozwolić
  reconcilerowi ponowić;
- `transmitting` z poprawnym lockiem: oczekiwać automatycznego resume; komenda
  serwisowa jest wyłącznie narzędziem break-glass po zapisaniu diagnostyki;
- `transmitting` bez locka lub z błędnym checksumem: stop/fail-closed, backup i
  analiza; zakaz ręcznego tworzenia signal;
- `stabilizing`: nie reaktywować consumed parts i nie tworzyć cyklu ręcznym SQL;
- brak publikacji nie cofa gameplayu; naprawia się event/task replay, nie signal;
- brak nagrody naprawia durable reward projector, nigdy ręczne dodanie RSP.

### Definition of Ready dla produkcyjnego 20/20

```text
durable endgame reconciler:                  PASS
transmitting crash auto-resume:              PASS
endgame delta + offline snapshot recovery:   PASS
persistent restart system message:           PASS
final reward projection exactly-once:        PASS
stabilization rollover + next cycle:          PASS
signal media contract including radio:       PASS / EXPLICITLY DEFERRED
critical narrative support fallbacks:        PASS
preflight strict on production state:         PASS
failure matrix local/integration:             PASS
operator backup and runbook rehearsal:        PASS
```

Każdy nie-PASS powyżej blokuje aktywację ostatniej części. Wyjątkiem jest radio
wyłącznie po jawnej decyzji o jego usunięciu z kontraktu pierwszego debiutu.

## 138.2 — E2E, failure i soak

Status: `BLOCKED BY 138.2.pre-endgame`

Pierwsza bramka implementacyjna dodaje bounded, read-only audit pełnego lineage:

```text
scripts/audit_narrative_e2e.py --db data/game.sqlite3 --event-id EVENT_ID --strict
```

Audit nie uznaje samego `published_by_medium > 0` za dowód. Dla każdego taska
łączy persisted event, aktywny package/attempt, accepted candidate, publication
receipt i lifecycle medium record. Sprawdza tożsamość medium/audience, canonical
fact refs, semantic/lifecycle contract oraz raportuje `event_to_publication_ms`.
Tryb `--task-id` służy do zawężonej diagnostyki; bramka family E2E wymaga
`--event-id`, ponieważ tylko ona sprawdza kompletny producer fan-out.

Pierwszy produkcyjny `part_activated` przeszedł techniczny audit 4/4, ale
ręczna ocena wykryła trzy accepted fragmenty: dwa tytuły BlackNet zakończone w
połowie słowa/frazy oraz body zaczynające się od osieroconej końcówki. Aktywny
kontrakt v11 podnosi limit tytułu BlackNet z 48 do 72 znaków i odrzuca
wysokiej pewności urwane fragmenty. Odrzucenie korzysta z istniejącego
Narrative Support Layer; nie zmienia semantic facts ani audience safety. V10
pozostaje immutable i legacy-compatible, aby retry historycznych tasków nie
zmieniał request hash pod tą samą wersją.

Produkcyjna bramka v11 potwierdziła kompletne i poprawne językowo candidate dla
czterech tras `part_activated`. Trzy rekordy BlackNet zostały opublikowane.
Googleplex zakończył się kontrolowanym `slot_assignment_superseded`: podczas
długiego oczekiwania w kolejce nowsza publikacja zajęła pojedynczy slot HERO, a
starszy task zgodnie z CAS nie nadpisał nowej treści. Audit E2E traktuje taki
wynik jako poprawne terminalne zakończenie wyłącznie wtedy, gdy potrafi połączyć
slot z istniejącym, aktywnym rekordem następcy. Sam `dead_letter` lub sam kod
błędu bez tego dowodu nadal failuje strict gate.
Ta semantyka oraz jawne pole `outcome` podnoszą kontrakt raportu do
`ghostnetwork-narrative-e2e-audit-v2`.

Zaobserwowane czasy event-to-publication dla trzech opublikowanych tras wyniosły
534–761 sekund (średnio 665 sekund). Nie naruszyło to lineage, ale stanowi
baseline wydajnościowy do failure/soak i nie może zostać uznane za docelową
latencję runtime.

Powtórzony na produkcji strict audit v2 zwrócił `ok=true`, `errors=[]` i cztery
poprawne chainy: trzy `published` oraz jeden `controlled_slot_supersession` z
potwierdzonym aktywnym rekordem slotu `gp-home-world-grid`. Family gate
`part_activated` otrzymuje `SERVER PASS`; pozostałe rodziny oraz failure/soak
pozostają otwarte w 138.2.

1. Przeprowadzić pełne part/conflict/machine/cycle/signal E2E, rozpoczynając
   od realnego gameplay/runtime entrypointu, nie od taska lub candidate.
2. Sprawdzić public/clan/owner na kilku kontach.
3. Potwierdzić invalidation poprzedniej karty po zmianie stanu.
4. Sprawdzić mix przy burst low events i critical bypass.
5. Wstrzyknąć crash publishera, expired claim i SQLite contention.
6. Przetestować Ollama disabled z fallbackiem wyłączonym, a następnie
   opcjonalnym critical fallbackiem.
7. Wykonać gameplay/SQLite/heavy-profile soak.

## Obserwowalność

```text
publication_ready / claimed / published / dead_letter
active / expired / invalidated records
superseded_by_event_family
records_by_audience / medium / significance
mix_selected / mix_suppressed / cooldown_suppressed
deterministic_fallback_suppressed
fallback_published
CTA read_only_degraded
event_to_publication_ms
profile and account-scan counters
```

Status i audit są bounded. Nie skanują całej historii przy każdym requestcie.

## Testy

- każdy family E2E zachowuje i asercyjnie łączy wszystkie ID od persisted
  eventu do medium recordu;
- każdy E2E potwierdza canonical event -> semantic projection -> attempt przed
  candidate; task z aliasem bez statement nie może wejść do publikacji;
- read model nie zawiera event/cycle/entity IDs, provenance source paths ani
  task-local aliases; dopuszczone labels/location są podzbiorem semantic
  projection dla danego audience;
- osobne testy realnych entrypointów obejmują capture/drop, territory
  reconciliation, strategic conflict outcome, cycle creation/lock oraz
  transmission/recovery;
- pipeline nie może zaliczyć publication testu, jeśli oczekiwany task nigdy
  nie powstał;
- accepted candidate publikuje się exactly once;
- crash po insert record nie tworzy drugiego wpisu;
- public/clan/owner nie przeciekają między kontami;
- inactive i expired records nie trafiają do feedu;
- state transition unieważnia poprzedni head tego samego threadu;
- retry eventu nie unieważnia nowego stanu starszą wersją;
- critical wygrywa selection bez omijania dedupe;
- burst low events nie zalewa BlackNetu;
- deterministic karta jest wyciszona przez narrated fact;
- narracja nie pojawia się drugi raz pod następną sekcją;
- każde CTA otwiera poprawny istniejący surface;
- hidden node degraduje do territory/read-only;
- GGPL News nadal ma dokładnie jeden active HERO;
- dead letter nie zatrzymuje kolejnych publikacji;
- fixture 35 MB daje wszystkie heavy-profile counters równe zero.

## Walidacja serwerowa

1. Deploy addytywny bez czyszczenia tasków, candidates, receipts i records.
2. Restart wyłącznie procesów dotkniętych kodem.
   Dla 138.1: `pm2 restart 13 17 18 --update-env`.
3. Przed generacją uruchomić `scripts/audit_semantic_input.py --strict` i
   potwierdzić statements, audience projection, location/provenance oraz zero
   technical identifier leaks.
4. Przed wejściem do 138 uruchomić
   `scripts/audit_narrative_generation.py --strict`; każdy wymagany task musi
   mieć zgodny request hash i accepted candidate po ręcznej ocenie głosu.
5. Wygenerować realne przejścia przez produkcyjne entrypointy, nie sztuczne
   eventy, taski ani candidates.
6. Prześledzić i zapisać wszystkie identyfikatory:
   `runtime action/effect -> event -> task -> candidate -> receipt -> active record`.
7. Potwierdzić, że model/read model widzą tylko audience-safe semantic content,
   podczas gdy canonical IDs i provenance pozostają w audycie backendowym.
8. Potwierdzić poprzedni record jako inactive/invalidated po następnym evencie.
9. Kliknąć wszystkie CTA w UI na public/clan/owner.
10. Sprawdzić BlackNet mix i jeden GGPL HERO.
11. Strict cutover audit, heavy-profile audit i soak SQLite muszą przejść.
12. Audit lineage musi przejść zarówno dla nowo utworzonego eventu, jak i po
   retry/crash recovery; globalne `published_by_medium > 0` nie wystarcza.
13. Uruchomić
   `scripts/audit_narrative_publication_lifecycle.py --db data/game.sqlite3 --strict`;
   `legacy` może być warningiem, ale wszystkie cztery liczniki naruszeń muszą
   wynosić zero.

## Definition of Ready

```text
canonical publication service:             COMPLETE
publication receipt / exactly-once:        COMPLETE
audience-filtered medium records:           COMPLETE
BlackNet merge and fact suppression:        COMPLETE
Googleplex slot CAS:                        COMPLETE
baseline worker/publisher tests:            59 / PASS
current 138.1 regression:                    117 / PASS
Sprint 136 event/audience component:        PRESENT
Sprint 136 runtime ingress/lineage:          SERVER PASS
Shared Semantic Input Layer:                SERVER PASS
semantic input technical-ID firewall:       SERVER PASS
Sprint 137.1 producer/support server gate:  PASS
Sprint 137.2 forbidden-knowledge gate:      SERVER PASS
Sprint 137.3 runtime/failure gate:           SERVER PASS
publication baseline audit:                 COMPLETE
138.1 lifecycle implementation:             COMPLETE / SERVER PASS
138.2.pre-endgame production gate:           REQUIRED / BLOCKING
138.2 producer-backed E2E/failure/soak:      BLOCKED BY PRE-ENDGAME
```

## Definition of Done

Sprint 138 jest zakończony, gdy ważne zdarzenia GhostNetwork przechodzą E2E
do aktywnych audience-safe wpisów, kolejne stany deterministycznie wygaszają
poprzednie, mix nie zalewa feedu, CTA otwierają poprawne surface'y, publikacja
pozostaje exactly-once, a awarie modelu/publishera i ciężki profil nie wpływają
na gameplay.
Żaden family nie jest zaliczony na podstawie sztucznego insertu w środku
pipeline'u; wymagany jest dowód kompletnej linii od realnej akcji runtime do
odczytu medium i CTA. Linia musi również zawierać audience-safe semantic
projection; publication nie może naprawiać brakującej semantyki przez analizę
tekstu candidate ani przez ponowne wczytanie surowego payloadu.

## Poza zakresem

- drugi BlackNet feed lub niezależny publisher;
- frontendowe filtrowanie prywatnego payloadu;
- model wybierający TTL, invalidation, priority, layout lub CTA;
- automatyczny backfill całej historii;
- fallback udający odpowiedź AGI/Cybernera;
- zmiana mechaniki GhostNetwork;
- commit, push, deploy i restart w ramach przygotowania.
