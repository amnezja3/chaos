# Sprint 135.4 — Ollama Worker and Canonical Inbox

Status: `PLANNED / BLOCKED BY SPRINT 135.3`.

## Cel

Uruchomić pierwszy rzeczywisty, lokalny worker Ollamy i trwale zapisywać jego
ustrukturyzowane odpowiedzi jako kandydatów canonical Inbox. Sprint działa w
trybie dry-run: żadna odpowiedź modelu nie jest jeszcze publikowana graczom.

## Warunek wejścia

- Sprint 135.2 gwarantuje queue/lease/crash invariants.
- Sprint 135.3 dostarcza bezpieczne, audience-projected taski.
- Worker nie otrzymuje alternatywnego endpointu ani ścieżki omijającej outbox.

## Source of truth

- fakty i outcome: canonical domeny gry wskazane przez task;
- transport i ownership: canonical Outbox;
- odpowiedź modelu: immutable/bounded Inbox candidate;
- decyzja o dopuszczeniu: backend validator;
- Ollama i surowy tekst modelu nie są source of truth.

## Call chain

```text
READY task
→ atomic claim + lease
→ build immutable model input package
→ local Ollama request
→ structured JSON response
→ atomic Inbox candidate insert
→ validation
→ ACCEPTED | QUARANTINED | REJECTED
→ complete Outbox task
```

Jeżeli zapis Inboxu nie został potwierdzony, task nie może zostać oznaczony jako
completed.

## Worker runtime

Worker jest osobnym procesem ecosystem, niezależnym od Flask requestów,
territory workera i map pollera.

Wymagania:

- wyłącznie lokalny, konfigurowalny endpoint Ollamy;
- allowlista modelu oraz wersjonowany `model_policy_version`;
- bounded concurrency, input bytes, context, output bytes i timeout;
- heartbeat przez `renew_task_lease` podczas dłuższego requestu;
- graceful shutdown nie claimuje kolejnych tasków i zwalnia/pozwala wygasnąć
  bieżącemu lease zgodnie z kontraktem;
- retry tylko przez kolejkę 135.2;
- brak bezpośredniego dostępu modelu do bazy, sieci zewnętrznej, plików profilu
  i narzędzi wykonujących akcje;
- gameplay pozostaje fail-open przy niedostępnej Ollamie.

## Model input package

Pakiet jest tworzony deterministycznie z taska:

```text
task_id
canon/source/state versions
target_medium
audience
facts[]
allowed_actions[]
truth_class_policy
editorial_profile
bounded narrative_context
prompt_version
output_schema_version
limits
```

Worker nie rozszerza facts przez query do domen gameplayowych. Prompt systemowy
jest wersjonowany w kodzie/zasobach i wybierany przez allowlistę, nie przez dane
użytkownika.

## Canonical Inbox schema

Nowy trwały store przechowuje:

```text
candidate_id
task_id / outbox_id
output_schema_version
model_name
model_version
model_policy_version
prompt_version
target_medium
audience_scope/clan/owner
source
truth_class
title
body
tone
fact_refs_json
cta_action
cta_payload_json
bounded_raw_output
output_hash
validation_status
validation_errors_json
quarantine_reason
created_at
validated_at
```

Unique `task_id` albo jawny `task_id + generation` uniemożliwia utworzenie dwóch
kandydatów po retry tego samego completed model call. Wybór zależy od tego, czy
retry po invalid output tworzy nową attempt history; w obu wariantach dokładnie
jeden kandydat może zostać oznaczony jako accepted dla taska.

Inbox nie zawiera jeszcze publication receipt — ten kontrakt należy do 135.5.

## Validator

Walidacja jest backendowa i obejmuje:

- poprawny JSON i zgodność `output_schema_version`;
- zgodność task/audience/target medium;
- title/body/tone w limitach;
- truth class dozwoloną przez task;
- wszystkie `fact_refs` obecne w tasku;
- CTA pochodzące z `allowed_actions` wraz z dozwolonym payloadem;
- brak nowych encji, gameplay outcome, nagród, lokalizacji i autorytatywnych
  twierdzeń niewspartych facts;
- brak profilu, sesji, hidden topology, owner-only leak i zewnętrznych URL;
- oznaczenie źródła treści narracyjnej.

Model nie może podnieść `rumor` do `canonical`, zmienić audience ani dopisać
CTA. Niepoprawny wynik nie jest automatycznie „naprawiany” i publikowany.

## Statusy Inboxu

```text
RECEIVED
→ VALIDATING
→ ACCEPTED
   lub QUARANTINED
   lub REJECTED
```

- `QUARANTINED` zachowuje bounded materiał diagnostyczny do audytu;
- `REJECTED` może być użyty dla odpowiedzi technicznie niespełniającej schema;
- status jest terminalny w 135.4;
- ręczna akceptacja lub edycja treści pozostaje poza zakresem;
- accepted candidate nie jest jeszcze widoczny w BlackNet/Cyberner/UI.

## Error contract

| Przypadek | Outbox | Inbox | Gameplay |
| --- | --- | --- | --- |
| Ollama offline/timeout | retry/dead letter | brak candidate | bez zmian |
| invalid JSON | retry lub rejected candidate według policy | audit | bez zmian |
| schema/fact/CTA violation | complete po trwałym quarantine | quarantined | bez zmian |
| crash przed Inbox insert | lease recovery | brak/ten sam candidate | bez zmian |
| crash po Inbox insert przed complete | dedupe znajduje candidate i domyka task | jeden candidate | bez zmian |
| stale lease owner zapisuje wynik | CAS reject | brak nowego accepted | bez zmian |

## Audit i privacy

Audit przechowuje task ID, fact refs, audience, model/prompt/schema versions,
output hash, validation i timings. Logi runtime nie zawierają pełnego promptu,
pełnego raw outputu ani danych profilu. Raw output w Inboxie jest bounded i
dostępny wyłącznie w kontrolowanej diagnostyce admin/dev.

## Twarda bramka heavy-profile

Każdy nowy endpoint, worker, producer, publisher i read model tego sprintu musi
spełniać kontrakt
`doc/architecture/profile_hot_path_contract_130_11_plus.md`.

Zakazane w hot path:

- `load_profile*`, `get_profile()`, `list_profiles()` i skan wszystkich kont;
- parsowanie `profile_json` per task, odbiorca, karta, news albo publikacja;
- pełny profile read/write jako sposób odczytu identity, entitlement, walletu,
  inventory, sesji, audience albo statusu aplikacji;
- cache pełnego profilu jako nowy source of truth.

Dozwolone są wyłącznie canonical bounded stores, receipts, lekkie identity i
audience projections oraz indeksowane batch lookupy. Obowiązkowa regresja z
profilem syntetycznym co najmniej 35 MB musi wykazać:

```text
profile_full_read = 0
profile_full_write = 0
profile_bytes = 0
all_user_profile_scan = 0
per_recipient_profile_read = 0
```

## Obowiązkowe testy

### Worker/lease

- jeden task → jeden model call przy normalnym flow;
- dwa workery → tylko lease owner wywołuje model;
- długi call → renew zachowuje ownership;
- Ollama timeout → bounded retry, brak Inbox accepted;
- crash przed/po model call i przed/po Inbox insert → brak utraty i duplikatu;
- stale worker po lease takeover → wynik odrzucony.

### Inbox/validator

- poprawny structured output → dokładnie jeden accepted candidate;
- invalid JSON/schema → controlled rejected/quarantine;
- unknown fact ref/CTA → quarantine;
- audience lub medium mismatch → quarantine;
- truth class escalation → quarantine;
- hidden data/external URL/oversize → quarantine;
- retry tego samego taska → najwyżej jeden accepted candidate;
- response 2108 nie zmienia canonical sender/authenticity/outcome.

### Isolation/performance

- Ollama offline przez dłuższy czas → aplikacja i gameplay pozostają zdrowe;
- backlog i backpressure są bounded;
- worker nie czyta pełnych profili ani domen poza taskiem;
- fixture dużej liczby terminalnych tasków nie degraduje claim query;
- graceful shutdown/restart odzyskuje task przez lease.

## Walidacja

- testy transportu Sprintu 135.2;
- testy producerów Sprintu 135.3;
- testy worker/timeout/crash/lease;
- testy schema/validator/quarantine;
- test z kontrolowanym lokalnym stubem Ollamy;
- `py_compile`;
- konfiguracja ecosystem syntax check;
- `git diff --check`.

## Poza zakresem

- publikacja do BlackNet, Googleplex News, Cybernera i Radia;
- UI accepted candidates;
- wykonywanie CTA przez model;
- manual moderation UI;
- zewnętrzny/cloud LLM;
- pełne profile i synchroniczne wywołanie LLM z requestu gracza;
- deploy i produkcyjne mutacje bez osobnej zgody.

## Exit gate

`OUTBOX → OLLAMA → ONE VALIDATED INBOX CANDIDATE / ZERO PLAYER PUBLICATION`

Po spełnieniu bramki: `SPRINT 135.4 — READY FOR SERVER VALIDATION`, a po
potwierdzeniu `READY FOR SPRINT 135.5`.


