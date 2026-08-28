# Sprint 135.2 — Canonical LLM Task Transport

Status: `READY FOR SERVER VALIDATION`.

Zależność: `SPRINT 135.1 — COMPLETE`.

## Cel

> Zbudować niezawodny transport tasków LLM, jeszcze bez LLM.

Sprint przekształca istniejący `ghost_narrative_outbox` ze Sprintu 129 w jedną
kanoniczną kolejkę zadań narracyjnych dla całego GhostSystemu. Zakres kończy się
na persistence, concurrency, lease i recovery. Nie powstaje klient Ollamy,
Inbox, producer gameplayowy ani publikacja dla graczy.

## Source of truth

Jedynym source of truth jest trwały rekord w SQLite zarządzany przez
`GhostNetworkRepository` albo wydzielony z niego bounded repository tej samej
bazy. Nie tworzymy równoległej kolejki.

```text
ghost_narrative_outbox
→ canonical task lifecycle
→ diagnostic projections/exports
```

Pliki `instance/blacknet_ollama_outbox/*.json`, cache, logi, UI i proces workera
nie są source of truth.

## Aktualny baseline

Sprint 129 dostarczył:

- tabelę `ghost_narrative_outbox`;
- unikalny `dedupe_key`;
- audience, medium, facts, allowed actions, canon/version i status;
- idempotentny insert oraz prostą zmianę statusu;
- `GhostNarrativePublisher` i pierwszy model input package.

Brakuje atomowego claimu, lease ownera, renew, retry schedule, recovery po
crashu, dead letter, pełnych timestampów oraz rozdzielenia procesora od medium.

## Docelowy rekord

Migracja jest addytywna i zachowuje odczyt rekordów Sprintu 129.

Wymagane pola:

```text
outbox_id / task_id
schema_version
source_scope
source_event_id
source_receipt_id
source_app_id
processor                 ollama
target_medium             blacknet | googleplex_news | cyberner | radio
audience_scope
audience_clan
audience_owner
canon_version
world_state_version
ghostsystem_version
prompt_version
output_schema_version
model_policy_version
truth_class_policy
facts_json
allowed_actions_json
priority
dedupe_key
status
attempt_count
max_attempts
claimed_by
claimed_at
lease_until
next_attempt_at
last_error_code
last_error_at
created_at
updated_at
completed_at
dead_lettered_at
```

`processor=ollama` oznacza planowanego consumera, ale w tym sprincie nie
uruchamia modelu. `target_medium` określa przyszłego publishera. Wartości te nie
mogą być ponownie łączone w `medium=ollama_outbox`.

## Dedupe contract

Semantyczny `dedupe_key` obejmuje:

```text
source_scope
+ source_event_id albo source_receipt_id
+ audience_scope/clan/owner
+ target_medium
```

Ten sam source event może utworzyć osobne taski dla różnych audience lub
mediów. Ten sam `event/receipt + audience + medium` zawsze wskazuje ten sam
task, również po zmianie wersji promptu albo output schema. Jawny replay wymaga
nowej source identity/receipt; nie powstaje przez zmianę caller-controlled
`dedupe_key`.

Concurrent enqueue korzysta z unikalnego indeksu i po konflikcie odczytuje
istniejący rekord. Nie traktuje konfliktu unikalności jako błędu gameplayowego.

## Lifecycle i dozwolone przejścia

```text
READY
  → CLAIMED
  → PROCESSING
  → COMPLETED

CLAIMED/PROCESSING
  → RETRY_WAIT
  → READY

CLAIMED/PROCESSING + expired lease
  → READY

READY/CLAIMED/PROCESSING/RETRY_WAIT
  → DEAD_LETTER
```

W tym sprincie `COMPLETED` jest testowalnym terminalnym wynikiem transportu.
Sprint 135.4 doprecyzuje, że produkcyjny consumer kończy task dopiero po trwałym
zapisie Inbox candidate.

Nie wolno zmieniać statusu dowolnym `UPDATE`. Wszystkie przejścia przechodzą
przez centralny state machine.

## Repository/service API

Wymagane operacje:

```text
enqueue_task(task)
claim_next_task(worker_id, lease_seconds, filters)
renew_task_lease(task_id, worker_id, expected_lease, lease_seconds)
mark_task_processing(task_id, worker_id, expected_lease)
complete_task(task_id, worker_id, expected_lease)
retry_task(task_id, worker_id, expected_lease, reason_code)
dead_letter_task(task_id, worker_id, expected_lease, reason_code)
recover_expired_leases(now, limit)
get_task(task_id)
list_tasks_bounded(filters, limit, cursor)
```

`renew`, `processing`, `complete`, `retry` i `dead_letter` są CAS-safe względem
`task_id + claimed_by + lease_until/status`. Stary owner nie może zakończyć
taska przejętego po wygaśnięciu jego lease.

## Atomowy claim i lease

Claim musi wykonać w jednej transakcji:

1. odzyskanie bounded liczby wygasłych lease albo uwzględnienie ich w selekcji;
2. wybór jednego `READY`, którego `next_attempt_at <= now`;
3. warunkową zmianę statusu, `claimed_by`, `claimed_at`, `lease_until`;
4. zwrot taska tylko wtedy, gdy dokładnie jeden rekord został przejęty.

Dwa procesy mogą równocześnie próbować claimować, ale tylko jeden uzyskuje
ważny lease. Nie opieramy ownership na timestampie bez warunkowej aktualizacji.

## Retry i dead letter

- `attempt_count` wzrasta przy rozpoczęciu kolejnej próby, nie przy samym
  odczycie diagnostycznym;
- backoff jest deterministyczny, bounded i zapisany jako `next_attempt_at`;
- retry zachowuje `task_id`, source identity oraz `dedupe_key`;
- po `max_attempts` task przechodzi do `DEAD_LETTER` dokładnie raz;
- terminalnego taska nie można ponownie claimować;
- ręczny operator replay pozostaje poza tym sprintem i wymaga późniejszego,
  jawnego receipt, a nie cofnięcia statusu w SQL.

## Indeksy

Minimalny zestaw:

- unique `dedupe_key`;
- kolejka gotowa: `processor, status, next_attempt_at, priority, created_at`;
- lease recovery: `status, lease_until`;
- source audit: `source_scope, source_event_id` i `source_receipt_id`;
- bounded diagnostics: `status, updated_at`.

Indeksy mają zostać potwierdzone przez `EXPLAIN QUERY PLAN` dla claimu, recovery
i lookupu dedupe. Nie dodajemy indeksów na całe JSON payloady.

## Legacy BlackNet diagnostic export

Dotychczasowy plikowy outbox staje się wyłącznie projekcją diagnostyczną:

```text
canonical task
→ bounded sanitizer
→ atomic JSON export
```

Kontrakt:

- kierunek wyłącznie DB → plik;
- `diagnostic_export=true` i `ollama_executed=false`;
- eksport nie ma osobnego lifecycle;
- plik nie jest claimowany ani importowany przez workera;
- zmiana/usunięcie pliku nie wpływa na task;
- endpointy admin/dev nie tworzą alternatywnej kolejki i nie zapisują statusu
  wyłącznie w pliku;
- payload pozostaje bounded i nie zawiera profilu, sesji ani ukrytych faktów.

## Telemetria

Do logów trafiają wyłącznie bounded identyfikatory:

```text
task_id
source_scope/source_event_id hash
target_medium/audience_scope
status transition
worker_id
attempt_count
lease age
reason_code
duration_ms
```

Nie logujemy `facts_json`, pełnych outputów, profili ani tokenów sesji.

## Obowiązkowe testy

### Dedupe

- sekwencyjny podwójny enqueue → jeden rekord i ten sam `task_id`;
- równoległy enqueue tego samego klucza → jeden rekord;
- ten sam event, inna audience → osobne taski;
- ten sam event i audience, inne medium → osobne taski;
- kompatybilny rekord Sprintu 129 → poprawny odczyt i bezpieczne defaults.

### Concurrency i lease

- dwa claimy naraz → jeden active lease owner;
- non-owner renew/complete/retry → odrzucone bez zmiany;
- owner renew przed expiry → przedłużony ten sam lease;
- stary owner po expiry i przejęciu → nie może ukończyć taska;
- terminalny task → nigdy ponownie claimowany.

### Crash recovery

- crash po claim przed processing → ten sam task wraca po expiry;
- crash podczas processing → brak utraty i brak duplikatu;
- retry zachowuje identity i zwiększa attempt dokładnie raz;
- przekroczenie limitu → dokładnie jeden `DEAD_LETTER`;
- recovery uruchomione równolegle → jedno skuteczne odzyskanie taska.

### Export i wydajność

- diagnostic export odzwierciedla canonical task i nie zmienia lifecycle;
- uszkodzony/brakujący plik nie wpływa na DB;
- claim/recovery używają oczekiwanych indeksów;
- kolejka z dużą liczbą terminalnych rekordów nadal pobiera bounded batch;
- zero full-profile read/write/bytes.

## Walidacja

Po implementacji:

- celowane testy repository/state machine/concurrency;
- regresja GhostNetwork narrative/transmission;
- regresja BlackNet world facts i admin outbox;
- test migracji istniejącej bazy;
- `EXPLAIN QUERY PLAN` dla hot query;
- fixture z tysiącami terminalnych tasków;
- `py_compile`;
- `git diff --check`.

## Poza zakresem

- request HTTP do Ollamy;
- proces Ollama worker;
- canonical Inbox i output modelu;
- nowi producenci GhostNetwork/BlackNet;
- dedykowana aplikacja Googleplex;
- publikacja do BlackNet, Googleplex News, Cybernera lub Radia;
- deploy, restart PM2 i produkcyjne mutacje.

## Exit gate

`ONE CANONICAL QUEUE / EXACTLY ONE TASK / EXACTLY ONE ACTIVE LEASE / CRASH RECOVERABLE`

Po spełnieniu bramki: `SPRINT 135.2 — READY FOR SERVER VALIDATION`, a po
potwierdzeniu `READY FOR SPRINT 135.3`.

## Wynik implementacji

`ghost_narrative_outbox` jest jedynym source of truth transportu. Migracja jest
addytywna, normalizuje statusy Sprintu 129, rekanonizuje istniejące klucze
dedupe dokładnie raz i wycofuje pseudo-medium `ollama_outbox` bez tworzenia
drugiej kolejki.

Repository i service udostępniają:

- atomowy, idempotentny enqueue z canonical `task_id` i `dedupe_key`;
- bounded list/cursor oraz lookup source/medium/status;
- transakcyjny claim z `BEGIN IMMEDIATE`;
- owner/lease CAS dla renew, processing, complete, retry i dead-letter;
- bounded recovery wygasłych lease oraz deterministyczny retry backoff;
- indeksy hot query potwierdzone przez `EXPLAIN QUERY PLAN`;
- fixture 2000 terminalnych tasków, przy którym claim nadal wybiera gotowy
  rekord przez indeks kolejki.

Stary plik `instance/blacknet_ollama_outbox/*.json` jest wyłącznie atomowym,
sanityzowanym eksportem DB → JSON. Odczyt i status endpointów korzystają z
canonical DB, a zmiana lub usunięcie pliku nie zmienia taska. Endpoint statusu
jest celowo read-only.

Nie dodano klienta Ollamy, workera, Inboxu, nowych producentów, aplikacji
Googleplex ani publisherów.

Walidacja lokalna:

- 243/243 pełnych testów `test_ghostnetwork*.py` — OK;
- 21/21 testów `BlackNetWorldSignalPublisherTest` — OK;
- 16/16 finalnych testów queue/narrative po uszczelnieniu enqueue — OK;
- `py_compile`, kontrola mojibake i `git diff --check` — OK.

Finalna bramka lokalna:

`ONE CANONICAL QUEUE / EXACTLY ONE TASK / EXACTLY ONE ACTIVE LEASE / CRASH RECOVERABLE`

`SPRINT 135.2 — READY FOR SERVER VALIDATION`
