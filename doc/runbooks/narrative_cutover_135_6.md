# Narrative pipeline 135.6 — controlled cutover runbook

## Zasady

- nie usuwaj canonical tables ani historycznych receipts;
- nie reaktywuj file outboxa jako kolejki;
- nie wykonuj pełnego odczytu profilu;
- najpierw audit read-only, potem ewentualny bounded retirement;
- retirement jest terminalny i wymaga wcześniejszego backupu SQLite;
- rollback wyłącza claimowanie, ale zachowuje backlog.

## 1. Deploy i restart

```bash
cd ~/app/chaos
git pull
pm2 restart 13 14 17 18 --update-env
```

Potwierdź flagi:

```bash
pm2 env 17 | grep CHAOS_OLLAMA_WORKER_ENABLED
pm2 env 18 | grep CHAOS_NARRATIVE_PUBLISHER_ENABLED
```

Obie muszą mieć wartość `true`. Flaga
`CHAOS_NARRATIVE_LEGACY_FILE_QUEUE_ENABLED` nie może mieć wartości `true`.
Audit działa w osobnym procesie niż PM2, dlatego po potwierdzeniu `pm2 env`
ustaw te same wartości w bieżącej sesji operatorskiej:

```bash
export CHAOS_OLLAMA_WORKER_ENABLED=true
export CHAOS_NARRATIVE_PUBLISHER_ENABLED=true
export CHAOS_NARRATIVE_LEGACY_FILE_QUEUE_ENABLED=false
```

## 2. Pierwszy audit — bez mutacji

```bash
.venv/bin/python scripts/audit_narrative_cutover.py \
  --db data/game.sqlite3
```

Sprawdź szczególnie:

- `active_legacy_file_tasks = 0`;
- `expired_leases = 0`;
- `expired_claims = 0`;
- pokrycie `blacknet`, `googleplex_news`, `cyberner`;
- `profile_full_read/profile_full_write/profile_bytes/account_scan = 0`.

`ineligible_ready_tasks` oznacza historyczne taski nieobsługiwane przez aktualny
registry. Nie będą claimowane i nie wolno ich replayować nowym promptem.

## 3. Bounded retirement — tylko gdy audit go wymaga

Najpierw wykonaj backup zgodnie z serwerową procedurą SQLite. Następnie:

```bash
.venv/bin/python scripts/audit_narrative_cutover.py \
  --db data/game.sqlite3 \
  --retire-ineligible
```

Jedno wywołanie wycofuje maksymalnie 500 `ready/retry_wait` tasków. Nie dotyka
aktywnego lease’u ani legalnej polityki. Przy liczbie większej niż 500 ponów
audit i świadomie uruchom następną partię.

## 4. Bramka strict

```bash
.venv/bin/python scripts/audit_narrative_cutover.py \
  --db data/game.sqlite3 \
  --strict
```

Cutover przechodzi tylko z kodem wyjścia 0 oraz `"ok": true`.

## 5. Smoke test

Utwórz po jednym nowym, legalnym zdarzeniu dla:

1. BlackNet — sygnał świata z canonical CTA;
2. Googleplex News — aktualizacja przypisanego slotu;
3. Cyberner AGI — owner-scoped task i odpowiedź.

Każdy przypadek śledź po ID:

```text
task -> candidate -> publication receipt -> medium record -> gameplay
```

Nie oceniaj starego taska po zmianie prompt policy. Nowy policy epoch wymaga
nowego source version i nowego taska.

## 6. Rollback

```bash
CHAOS_OLLAMA_WORKER_ENABLED=false pm2 restart 17 --update-env
CHAOS_NARRATIVE_PUBLISHER_ENABLED=false pm2 restart 18 --update-env
```

Po rollbacku nie czyść backlogu. Przywrócenie flag `true` uruchamia canonical
recovery. Procesy 13 i 14 pozostają niezależne, o ile przyczyną nie jest producer
lub web read model.
