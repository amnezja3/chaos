# Sprint 135.6 — Narrative Hardening and Controlled Cutover

Status: `IN PROGRESS — ETAP I SERVER PASS / SMOKE AND SOAK PENDING`

## Cel

Uznać canonical transport narracyjny za jedyną produkcyjną ścieżkę runtime:

```text
canonical source
  -> ghost_narrative_outbox
  -> Ollama worker
  -> validated candidate
  -> publication receipt
  -> BlackNet / Googleplex News / Cyberner
```

Sprint nie dodaje nowych funkcji ani nowych decyzji modelu. Legacy file outbox
pozostaje wyłącznie ręcznym, adminowym eksportem diagnostycznym i nie może być
źródłem statusu, claima, retry ani publikacji.

## Bezwzględna bramka heavy profile

Każdy producer, worker, publisher, audit i read model musi zachować:

```text
profile_full_read:  0
profile_full_write: 0
profile_bytes:      0
account_scan:       0
```

Zakazane są `users.profile_json`, per-recipient profile I/O, skan kont oraz
pośrednie wywołanie synchronizacji mapy, operacji, plików, walleta lub Ghost
Exchange. Fixture 35 MB jest bramką fail-closed.

## Etap I — canonical readiness gate

Zaimplementowano:

- wspólny kontrakt `canonical-narrative-cutover-v1`;
- bounded status task queue i publication queue;
- liczniki wygasłych task leases i publication claims;
- licznik accepted candidates bez publication receiptu;
- wykrywanie aktywnych rekordów legacy `medium=ollama_outbox`;
- kontrolę pokrycia BlackNet, Googleplex News i Cyberner;
- backpressure limits dla tasków i receipts;
- fail-closed kontrolę flag worker/publisher oraz prompt registry;
- jawną, limitowaną operację terminalnego wycofania wyłącznie queued tasków,
  których nie może claimować żadna aktywna polityka;
- CLI `scripts/audit_narrative_cutover.py`.

Retirement nie dotyka `claimed`, `processing`, `completed`, legalnych
`ready/retry_wait`, candidates, receipts ani medium records. Każdy wycofany
task otrzymuje `dead_letter / policy_superseded_cutover`.

## Etap II — failure and load validation

- lease expiry i pojedynczy recovery po crashu;
- retry Ollamy bez utraty taska;
- candidate recovery bez drugiej generacji;
- publication exactly-once po crashu;
- CAS slot assignment przy równoległej publikacji;
- public/clan/owner visibility bez przecieku;
- bounded staging i brak ponownego skanowania staged candidates;
- kontrola `database_contention / sqlite_busy`;
- backpressure bez blokowania Flask i workerów gameplayowych.

## Etap III — controlled server cutover

1. Deploy kodu bez czyszczenia canonical tables.
2. Restart procesów 13, 14, 17 i 18 z zachowaniem flag enabled.
3. Read-only audit bez `--strict`.
4. Osobna decyzja o terminalnym retirement historycznych ineligible tasks.
5. Audit `--strict` musi zwrócić `ok=true`.
6. Fizyczny smoke test wszystkich trzech mediów.
7. Soak backlogu, SQLite i gameplay latency.

## Rollback

Rollback zatrzymuje wyłącznie claimowanie i publikację:

```text
CHAOS_OLLAMA_WORKER_ENABLED=false
CHAOS_NARRATIVE_PUBLISHER_ENABLED=false
```

Nie usuwa się tasków, candidates, receipts ani medium records. Nie wolno
reaktywować legacy file outboxa jako kolejki. Po naprawie canonical workers
odzyskują wygasłe lease’y i kontynuują backlog.

## Definition of Done

```text
canonical queue is sole runtime queue:       SERVER PASS
legacy file outbox diagnostic only:          SERVER PASS
prompt registry:                             SERVER PASS
replay/crash/exactly-once tests:              LOCAL PASS
audience isolation:                          LOCAL PASS
bounded backpressure observability:          LOCAL PASS
worker and publisher enabled:                SERVER PASS
ineligible queued tasks:                     0 / SERVER PASS
expired leases/claims:                       0 / SERVER PASS
BlackNet/GGPL News/Cyberner coverage:         SERVER PASS
heavy-profile metrics:                       0 / SERVER PASS
gameplay and SQLite soak:                    PENDING SERVER
```

## Wynik pierwszego cutoveru serwerowego

Audit wykrył `49` nieclaimowalnych tasków `world_digest` z historycznych prompt
epochs. Wszystkie były w `ready/retry_wait`; żaden nie miał aktywnego lease’u.
Po online backupie SQLite bounded retirement oznaczył dokładnie 49 rekordów jako
`dead_letter / policy_superseded_cutover`. Nie zmieniono legalnych tasków,
candidates, receipts ani medium records.

Ponowna bramka `--strict` zakończyła się `ok=true`: `ineligible_ready=0`,
`expired_leases=0`, `expired_claims=0`, `unstaged_accepted=0`, wszystkie trzy
media mają publikacje, prompt registry ma 31 legalnych polityk, legacy file
queue jest wyłączona, a wszystkie metryki heavy profile są równe zero.

Pierwszy smoke AGI potwierdził retry po `ollama_timeout`, a następnie
kontrolowaną kwarantannę odpowiedzi zawierającej echo topicu i wymyślone
`cta_ref`. Echo nadal blokuje publikację. Gdy backend nie udostępnia żadnego
CTA, modelowy ref jest teraz redukowany do `null` z audytem
`unsupported_cta_removed`; nieznany ref przy istniejącej allowliście nadal
kończy się kwarantanną. Redukcja usuwa capability i nie rozszerza uprawnień
modelu.
