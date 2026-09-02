# Sprint 138 — GhostNetwork Narrative Publication Lifecycle

Status: `BLOCKED — AWAITING SERVER 136.1 PROOF AND 137 CANDIDATES`

## Korekta po audycie Sprintu 136 — 2026-09-02

Publication lifecycle nie może być zatwierdzony na podstawie candidate
wstawionego ręcznie do środka pipeline'u. Incydent z realnym dropem pokazał,
że downstream może być zdrowy, gdy upstream nie tworzy żadnego taska.

Remediacja 136.1 jest wdrożona i pokryta lokalnie, ale 138 pozostaje
zablokowany do serwerowego dowodu lineage 136 oraz producer-backed candidates
ze Sprintu 137.

Pełny test Sprintu 138 musi zaczynać się od produkcyjnego entrypointu domeny:

```text
runtime action
  -> committed mechanic/capture effect
  -> persisted GhostNetwork event
  -> expected task identities
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
- brak profilu w publisherze i bounded identity projection w endpointach.

Wspólny baseline Sprintów 137–138: `59 tests / PASS`.

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
- polityka terminalnego fallbacku dla critical eventów nie jest rozstrzygnięta.

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
- payload pochodzi wyłącznie z medium record.

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
Cybernera. Decyzja o jego aktywacji wymaga osobnego failure testu w Etapie II.

## Etap I — lifecycle, mix i CTA

1. Dodać addytywny lifecycle contract i bounded indeksy.
2. Przenieść thread/significance/priority z taska do medium record.
3. Wprowadzić active/expired/invalidated filtering.
4. Dodać supersession dla canonical state transitions.
5. Rozszerzyć BlackNet mix policy bez drugiego feedu.
6. Dodać GhostNetwork presentation families.
7. Podłączyć canonical CTA do allowlisty i dispatcherów.

## Etap II — E2E, failure i soak

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
3. Wygenerować realne przejścia przez produkcyjne entrypointy, nie sztuczne
   eventy, taski ani candidates.
4. Prześledzić i zapisać wszystkie identyfikatory:
   `runtime action/effect -> event -> task -> candidate -> receipt -> active record`.
5. Potwierdzić poprzedni record jako inactive/invalidated po następnym evencie.
6. Kliknąć wszystkie CTA w UI na public/clan/owner.
7. Sprawdzić BlackNet mix i jeden GGPL HERO.
8. Strict cutover audit, heavy-profile audit i soak SQLite muszą przejść.
9. Audit lineage musi przejść zarówno dla nowo utworzonego eventu, jak i po
   retry/crash recovery; globalne `published_by_medium > 0` nie wystarcza.

## Definition of Ready

```text
canonical publication service:             COMPLETE
publication receipt / exactly-once:        COMPLETE
audience-filtered medium records:           COMPLETE
BlackNet merge and fact suppression:        COMPLETE
Googleplex slot CAS:                        COMPLETE
baseline worker/publisher tests:            59 / PASS
Sprint 136 event/audience component:        PRESENT
Sprint 136 runtime ingress/lineage:          LOCAL PASS / SERVER CHECK REQUIRED
Sprint 137 producer-backed candidates:      BLOCKED
publication lifecycle scope:                FROZEN
```

## Definition of Done

Sprint 138 jest zakończony, gdy ważne zdarzenia GhostNetwork przechodzą E2E
do aktywnych audience-safe wpisów, kolejne stany deterministycznie wygaszają
poprzednie, mix nie zalewa feedu, CTA otwierają poprawne surface'y, publikacja
pozostaje exactly-once, a awarie modelu/publishera i ciężki profil nie wpływają
na gameplay.
Żaden family nie jest zaliczony na podstawie sztucznego insertu w środku
pipeline'u; wymagany jest dowód kompletnej linii od realnej akcji runtime do
odczytu medium i CTA.

## Poza zakresem

- drugi BlackNet feed lub niezależny publisher;
- frontendowe filtrowanie prywatnego payloadu;
- model wybierający TTL, invalidation, priority, layout lub CTA;
- automatyczny backfill całej historii;
- fallback udający odpowiedź AGI/Cybernera;
- zmiana mechaniki GhostNetwork;
- commit, push, deploy i restart w ramach przygotowania.
