# Sprint 138 — GhostNetwork Narrative Publication Lifecycle

Status: `138.1 CTA/REPAIR LOCAL PASS — DEPLOY REQUIRED`

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

138.1 wymaga teraz wdrożenia i testu serwerowego. 138.2 pozostaje zamrożony do
potwierdzenia migracji, dwóch następujących po sobie stanów jednego threadu,
TTL/read-model audit oraz ręcznego kliknięcia CTA.

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

## 138.2 — E2E, failure i soak

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
138.1 lifecycle implementation:             LOCAL PASS / SERVER GATE REQUIRED
138.2 producer-backed E2E/failure/soak:      BLOCKED BY 138.1 SERVER GATE
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
