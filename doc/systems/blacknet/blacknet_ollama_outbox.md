# BlackNet Ollama Outbox

## Status po Sprincie 135.2

Historyczny plikowy outbox ze Sprintu 83 nie jest już kolejką. Jedynym source
of truth transportu tasków LLM jest tabela `ghost_narrative_outbox` opisana w
`doc/sprints/sprint_135_2_canonical_llm_task_transport.md`.

Plik w:

```text
instance/blacknet_ollama_outbox/<task_id>.json
```

jest wyłącznie bounded eksportem diagnostycznym jednego canonical taska.

## Flow

```text
ghost_narrative_outbox
→ canonical task
→ sanitizer
→ atomic diagnostic JSON export
```

Nie istnieje flow plik → DB. Plik nie jest claimowany, nie posiada niezależnego
lifecycle i nie będzie inputem produkcyjnego workera Ollamy.

## Endpointy diagnostyczne

```text
POST /api/blacknet/ollama/outbox/generate
GET  /api/blacknet/ollama/outbox/latest
GET  /api/blacknet/ollama/outbox/<task_id>
POST /api/blacknet/ollama/outbox/<task_id>/status
```

Endpointy są dostępne wyłącznie dla admin/dev.

- `generate` eksportuje wskazany `task_id` albo najnowszy canonical task dla
  medium BlackNet;
- `latest` i odczyt po ID budują projekcję z canonical DB, nie z pliku;
- endpoint `status` jest read-only i zwraca kontrolowany konflikt
  `diagnostic_export_read_only`;
- żaden endpoint nie uruchamia Ollamy ani nie mutuje gameplayu.

## Schema diagnostyczna 2.0

Eksport zawiera między innymi:

```text
schema_version = 2.0-diagnostic
diagnostic_export = true
digest_id = task_id
processor = ollama
target_medium
source scope/event/receipt/app
audience scope/clan/owner
wersje task/canon/world/prompt/output/model policy
facts
allowed_actions
task_lifecycle
validation
diagnostics.ollama_executed = false
diagnostics.file_is_source_of_truth = false
```

Sanitizer zachowuje tylko bounded publiczne pola faktów i dozwolonych akcji.
Eksport nie zawiera profilu, sesji, tokenów ani dostępu do bazy.

## Invariants

- zmiana, uszkodzenie albo usunięcie pliku nie zmienia canonical taska;
- status taska może zmienić wyłącznie state machine repository z prawidłowym
  lease/CAS;
- `task_id`, source identity, audience i target medium pochodzą z DB;
- eksport używa pliku tymczasowego i `os.replace()`;
- maksymalny rozmiar paczki i liczba faktów są bounded;
- `ollama_executed=false` pozostaje prawdą przez cały Sprint 135.2.

## Granica Sprintu 135.2

Poza zakresem pozostają:

- request HTTP do Ollamy;
- worker i heartbeat;
- canonical Inbox oraz walidacja outputu;
- publikacja do BlackNet, Googleplex News, Cybernera lub Radia;
- producenci i aplikacja Googleplex.

Historyczny kontrakt Sprintu 83 pozostaje kontekstem audytowym, ale nie jest
już obowiązującym kontraktem runtime.
