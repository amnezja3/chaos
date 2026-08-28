# Sprint 135.4 — Ollama Worker and Canonical Inbox

Status: `SPRINT 135.4 — READY FOR SERVER VALIDATION`.

## Wynik implementacji

Zaimplementowany przepływ kończy się na trwałym, zwalidowanym kandydacie Inbox:

```text
eligible canonical Outbox task
→ atomic claim + lease
→ periodic runtime/model/digest/prompt-registry preflight
→ code-owned SYSTEM + DOMAIN prompt + bounded task package
→ local Ollama /api/chat
→ strict backend validation
→ durable Inbox candidate
→ Outbox completed
→ zero player publication
```

Kod promptów ma logiczny podział wymagany przez kontrakt:

```text
ghostnetwork/llm/prompts/    versioned system/domain prompt assets
ghostnetwork/llm/schemas/    versioned JSON Schema
ghostnetwork/llm/policies/   pinned local model policy
ghostnetwork/llm/registry.py sole source_scope/variant/medium registry
```

Moduł `ghostnetwork/ollama_policy.py` pozostaje małą warstwą składania bounded
task package i walidacji outputu. Nie posiada własnych promptów. Klient HTTP,
worker i repository nie zawierają promptów oraz nie przyjmują ich z taska.

Powstały addytywne stores `ghost_narrative_inbox_attempts` i
`ghost_narrative_inbox_candidates`. Candidate jest zapisywany przed domknięciem
Outboxa; retry po crashu między tymi operacjami odnajduje candidate i nie woła
modelu ponownie. Zapis candidate oraz complete wymagają aktualnego ownera lease.

Proces `chaos-ollama-worker` jest oddzielony od Flask/territory i domyślnie ma
`CHAOS_OLLAMA_WORKER_ENABLED=false`. Tryb disabled pozostaje zdrowym procesem,
ale nie wykonuje claimów. `status`, `verify`, `dry-run`, `run-once` i `run` są
dostępne przez `scripts/ollama_narrative_worker.py`.

Walidacja lokalna objęła transport 135.2, producentów 135.3, policy registry,
klienta HTTP, worker/lease/crash, Inbox/dedupe/quarantine, historyczne
`unassigned`, tysiące rekordów kolejki oraz istniejącą fixture profilu 35 MiB.
Nie uruchomiono lokalnej Ollamy, procesu PM2, deployu ani publikacji.

### Korekta po pierwszej walidacji produkcyjnej

Pierwszy synthetic package miał 2513 tokenów i wymagał około 259 sekund samego
prompt evaluation; trzy realne taski przekroczyły nawet 240 sekund. Timeout nie
został zwiększony. Deterministyczny TASK PACKAGE ma teraz twardy limit 2400
bajtów, odpowiadający budżetowi około 500–700 tokenów dla realnego 20-fact
digestu. Każdy canonical `fact_id`, source/task/receipt, audience i wersje
pozostają obecne. Payload facts jest allowlistowany oraz dokładany sprawiedliwie
w ramach pozostałego budżetu; arbitrary instructions i nieznane pola nie mogą
powiększać ani zmieniać warstwy promptu.

`num_predict` został ograniczony do 192, przy zachowaniu timeoutu 2s/120s.
Attempt audit zapisuje teraz `input_bytes` i `fact_count`; dry-run raportuje
dodatkowo estymowany input tokens oraz rzeczywisty `prompt_eval_count` zwrócony
przez Ollamę.

Wiążący handoff runtime:
`doc/sprints/sprint_135_4_codex_ollama_server_runtime_brief.md`.

## Potwierdzony baseline produkcyjny

Sprint implementuje adapter wyłącznie dla potwierdzonego lokalnego runtime:

```text
host                  CPU-only, x86_64, 8 vCPU, ~11 GiB RAM
Ollama                0.15.4, systemd active/enabled
base URL              http://127.0.0.1:11434
model                 llama3.1:8b
model digest          46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e
quantization          Q4_K_M
concurrency           1
num_ctx               4096
num_predict           192
temperature           0
keep_alive            5m
connect/read timeout  2s / 120s
lease/heartbeat       180s / 30s
stream/think/tools    false / false / none
```

Nie wolno uruchamiać `ollama serve` z PM2, zmieniać istniejącej usługi systemd,
pobierać innego modelu ani przełączać się na Ollama Cloud. Konfiguracja inna niż
jawne `127.0.0.1:11434` nie przechodzi `verify`.

## Wiążące doprecyzowania implementacyjne

### Jeden adapter transportowy

Jedynym interfejsem domeny z runtime modelu jest:

```text
ChaosOllamaClient.generate(task_package, policy)
→ OllamaGenerationResult
```

Adapter używa `POST /api/chat`, `stream=false`, `think=false`, JSON Schema w
`format` i nie przekazuje `tools`. `GET /api/version`, `GET /api/tags` oraz
`POST /api/show` służą wyłącznie do preflightu i obserwowalności. Model, prompt,
schema, audience i medium nie mogą pochodzić z dowolnego requestu użytkownika.

Odpowiedź HTTP jest czytana z limitem bajtów również przy `stream=false`.
`message.content` jest osobnym, bounded JSON-em i przechodzi niezależny parser
oraz backend validator. Pełny prompt i pełna odpowiedź nie trafiają do logów.

### Model generuje tylko prezentację

Model output `chaos-narrative-output-v1` zawiera wyłącznie:

```text
title
body
tone
fact_refs[]
cta_ref
```

`additionalProperties=false`. Model nie generuje ani nie echo'uje `task_id`,
source, audience, medium, truth class, wersji policy, gameplay outcome,
authenticity, canonical sender ani CTA payloadu. Backend kopiuje pola canonical
z Outboxa, a `cta_ref` rozwiązuje do jednego wpisu `allowed_actions`; model nigdy
nie konstruuje payloadu akcji.

### Dokładny lifecycle istniejącego Outboxa

135.4 nie dodaje konkurencyjnych statusów transportowych. Obowiązuje istniejący
kontrakt repository:

```text
ready | retry_wait
→ claimed
→ processing
→ completed | retry_wait | dead_letter
```

`MODEL_COMPLETED`, `INBOX_RECORDED`, parse i validation są stanami Attempt/Inbox,
nie nowymi statusami `ghost_narrative_outbox`. `completed` oznacza, że trwały
candidate otrzymał terminalną decyzję validatora (`accepted`, `quarantined` lub
`rejected`). Awaria operacyjna bez trwałego terminalnego candidate kończy się
`retry_wait` albo `dead_letter`.

### Eligibility musi być częścią atomic claim

`claim_next_narrative_task()` musi zostać rozszerzony tak, aby wybierał wyłącznie
task spełniający jednocześnie:

```text
processor = ollama
status claimable i retry due
prompt_version registered
output_schema_version registered
model_policy_version registered
source_scope + task_variant + target_medium registered
audience identity valid dla scope
```

Nie wolno claimować taska `unassigned`, a następnie dopiero odrzucać go w
workerze. Historyczne taski `unassigned` pozostają nieclaimowalne i są jawnie
raportowane jako `queue_ineligible`; nie są backfillowane SQL-em ani cichym
fallbackiem. Nowi producenci przypisują wersje registry przed enqueue.

Pierwszy registry obejmuje wyłącznie zatwierdzone kombinacje:

```text
blacknet_world + world_digest + blacknet
ghostnetwork + registered lifecycle variant + blacknet
ghostnetwork + registered signal/event variant + cyberner
ghostnetwork + registered signal variant + radio
```

`googleplex_app` pozostaje nieclaimowalne do czasu zatwierdzenia template/product
contract w Sprincie 135.4.2.

Wersje początkowe:

```text
blacknet-world-prompt-v1
ghostnetwork-event-prompt-v1
ghostsignal-prompt-v1
chaos-narrative-output-v1
chaos-local-narrator-v1
```

### Canonical Inbox i Attempt history

Powstają dwa addytywne bounded stores:

```text
ghost_narrative_inbox_attempts
ghost_narrative_inbox_candidates
```

Attempt jest trwałym audytem jednego model call. Candidate jest wynikiem
przetwarzania jednego attemptu. Wymagane constraints:

```text
UNIQUE(task_id, attempt_id)
at most one validation_status=accepted per task_id
deterministic candidate identity from task_id + attempt_id
```

Przed nowym model call worker sprawdza trwały candidate dla taska. Crash po
Inbox insert i przed Outbox complete prowadzi do idempotentnego domknięcia tego
samego candidate, a nie do ponownego wywołania modelu.

### Heartbeat i utrata lease

Blokujący lokalny request HTTP posiada niezależny bounded heartbeat co 30 s.
Każde renew używa aktualnego `expected_lease_until`. Utrata CAS ustawia lokalny
stan `lease_lost`; zakończona później odpowiedź Ollamy może zostać zhashowana w
attempt audit, ale nie może utworzyć candidate ani sfinalizować Outboxa.

### Tryby procesu

`scripts/ollama_narrative_worker.py` udostępnia:

```text
status   — bez claimu i bez model call
verify   — runtime/model/digest/schema/DB, bez claimu
dry-run  — synthetic bounded call + walidacja in-memory, bez production DB write
run      — normalne zużycie kolejki, tylko przy explicit enabled
run-once — jeden kontrolowany eligible task do walidacji serwerowej
```

Domyślnie `CHAOS_OLLAMA_WORKER_ENABLED=false`. Osobny
`ecosystem.ollama-worker.config.js` uruchamia dokładnie jedną instancję w trybie
fork i nigdy nie startuje ani nie konfiguruje samej usługi Ollamy.

### Bounded transport i retry policy

Początkowe limity procesu są jawne i konfigurowalne:

```text
poll interval                  1.5s + bounded jitter do 0.25s
max deterministic TASK PACKAGE 2400 B (~500–700 est. tokens)
num_predict                    192
max HTTP response              64 KiB
max bounded_raw_output         16 KiB
max bounded error message      240 znaków
max attempts                   5
operational retry backoff      5s, 10s, 20s, 40s, 80s; cap 300s
invalid JSON retry             najwyżej 1 dodatkowa próba
```

HTTP `200` nie oznacza sukcesu domenowego. Adapter wymaga `done=true`,
niepustego `message.content`, zgodnego modelu oraz odpowiedzi mieszczącej się w
limicie. `requests` jest już zależnością projektu; worker nie potrzebuje SDK
Ollamy ani drugiego klienta transportowego.

### Izolacja importów i indeksów

Worker nie importuje `run.py`, Flask app, mapy, profili, territory runtime ani
producerów. Korzysta wyłącznie z lekkich modułów policy/client/validator oraz
bounded repository nad `data/game.sqlite3`.

Atomic eligible claim zachowuje istniejący indeks zwykłej ready-queue. Osobny
partial index zawiera tylko rekordy posiadające przypisane wersje prompt/schema/
model policy, więc tysiące historycznych `unassigned` nie wchodzą do indeksu
workera. Mały jawny registry jest następnie dokładany jako ścisły predykat
semantyczny. Test z tysiącami terminalnych i historycznych `unassigned` tasków
potwierdza bounded claim i brak skanu pełnych payloadów.

### Historyczne `unassigned` i dedupe

Canonical dedupe nie obejmuje wersji prompt/schema/model policy. Replay starego
eventu lub receipt zwraca więc istniejący task i nie może służyć jako migracja
`unassigned`. Jest to zachowanie poprawne: worker go nie claimuje, a `status`
raportuje osobno. Pierwszy produkcyjny `run-once` musi użyć nowego taska
utworzonego po wdrożeniu registry. `dry-run` używa synthetic package i nie
zmienia kolejki.

Doprecyzowanie do Sprintu 135.4 — PROMPT ENGINEERING / PROMPT REGISTRY

W trakcie implementacji przyjmij dodatkowo jawny, wersjonowany kontrakt dla promptów LLM.

Prompty nie mogą być porozrzucane po workerze, kliencie HTTP ani repository. Mają być code-owned, wersjonowane i wybierane wyłącznie przez registry.

Proponowana struktura:

ghostnetwork/
└── llm/
├── prompts/
│   ├── system/
│   │   └── chaos-narrator-v1.md
│   ├── blacknet/
│   │   └── world-digest-v1.md
│   ├── ghostnetwork/
│   │   └── event-v1.md
│   ├── ghostsignal/
│   │   └── signal-v1.md
│   └── cyberner/
│       └── agi-2108-v1.md
├── schemas/
│   └── chaos-narrative-output-v1.json
├── policies/
│   └── chaos-local-narrator-v1.py
└── registry.py

Jeżeli istniejąca struktura modułów uzasadnia inną lokalizację, zachowaj ten sam logiczny podział i opisz decyzję w dokumencie sprintu. Nie twórz promptów jako dużych stringów rozsianych po Pythonie.

Registry ma mapować:

source_scope

* task_variant
* target_medium
  → prompt_version
  → output_schema_version
  → model_policy_version

Pierwsze wersje:

blacknet-world-prompt-v1
ghostnetwork-event-prompt-v1
ghostsignal-prompt-v1
chaos-narrative-output-v1
chaos-local-narrator-v1

Prompt ma być składany warstwowo:

1. SYSTEM PROMPT
   Stałe zasady narratora CHAOS:

* jesteś wyłącznie warstwą narracyjną;
* używasz tylko dostarczonych facts;
* nie tworzysz nowych faktów;
* nie zmieniasz audience, truth class, source ani gameplay outcome;
* nie wykonujesz działań;
* nie korzystasz z narzędzi;
* nie masz dostępu do bazy, profili ani internetu;
* zwracasz wyłącznie output zgodny ze wskazanym JSON Schema.

2. DOMAIN / MEDIUM PROMPT
   Nadaje styl i sposób interpretacji dla konkretnego źródła/medium, np.:

* BlackNet — informacyjny/reporterski, dopuszczający niepewność tylko zgodnie z truth policy;
* GhostNetwork — techniczno-narracyjny;
* GhostSignal — bardziej enigmatyczny, ale nadal oparty wyłącznie o canonical facts;
* Cyberner / AGI 2108 — styl systemowej inteligencji z 2108, bez prawa do zmiany canonical sender/authenticity/outcome.

3. TASK PACKAGE
   Deterministycznie z Outboxa:
   facts[]
   fact_refs
   allowed_actions / cta refs
   audience
   truth_class_policy
   editorial_profile
   bounded narrative_context
   limits

Task ani request użytkownika nie może dostarczyć:

* system promptu,
* developer promptu,
* modelu,
* output schema,
* model policy,
* arbitrary instructions.

Worker claimuje wyłącznie task z zarejestrowanym prompt_version/schema/model policy. `unassigned` pozostaje fail-closed.

Model nadal zwraca wyłącznie:
title
body
tone
fact_refs[]
cta_ref

Canonical pola pozostają backend-owned.

Dodaj testy:

* registry zwraca właściwy prompt/schema/policy dla każdej obsługiwanej kombinacji;
* nieznana kombinacja → task nieclaimowalny;
* brak pliku promptu → verify fail;
* prompt version mismatch → verify fail;
* task nie może nadpisać system promptu;
* user input zawierający instrukcje typu „ignore previous instructions” pozostaje zwykłym bounded inputem/faktem i nie zmienia warstwy systemowej;
* pełny prompt nie trafia do runtime logów.

To doprecyzowanie jest częścią Sprintu 135.4 i należy je uwzględnić w aktualnej implementacji oraz dokumentacji sprintu.


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

Wire representation facts jest kolumnowa: `fact_columns[]` opisuje pozycje w
każdym wierszu `facts[]`. Pozwala to zachować wszystkie canonical refs bez
powtarzania nazw pól dwadzieścia razy. Kolumny referencyjne są obowiązkowe;
allowlistowane kolumny opisowe są dokładane całymi kolumnami, deterministycznie,
do wyczerpania budżetu. `input_bytes` oznacza rozmiar UTF-8 tego package, a nie
pełnego raw promptu ani odpowiedzi modelu.

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
potwierdzeniu `READY FOR SPRINT 135.4.1`.
