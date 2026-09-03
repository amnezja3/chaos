# Sprint 137 — GhostNetwork Narrative Generation and Validation

Status: `137 ACTIVE — 137.1 v5 LOCAL PASS, SERVER VOICE REVALIDATION REQUIRED`

## 137.pre.1 — Shared Semantic Input Layer

Produkcyjny probe ujawnił, że minimalny v3 usuwał techniczne identyfikatory,
ale wraz z nimi usuwał również treść canonical fact. Model widział `f01`,
`event_family` i `narrative_intent`, lecz nie otrzymywał jednoznacznej odpowiedzi
na pytanie „co się wydarzyło?”. Dlatego wcześniejszy status v3 został cofnięty,
a strojenie Sprintu 137 zatrzymane.

137.pre.1 wprowadza wspólny kontrakt
`chaos-llm-semantic-input-v1`, domenowy deterministic converter GhostNetwork,
audience projection przed LLM, canonical label resolution, technical-ID
firewall oraz bounded location retention. Docelowy model input v3 zawiera:

```text
control metadata:
  medium, audience scope, narrative_intent, event_family,
  significance, tone_hint, output_limits, optional aggregate context

semantic content:
  semantic_facts[].fact_ref       — wyłącznie task-local lineage alias
  semantic_facts[].statement      — prosta canonical prawda
  semantic_facts[].entities       — dozwolone human-readable labels
  semantic_facts[].location       — tylko zachowane canonical city/country
  semantic_facts[].attributes     — bounded scalars istotne dla zdarzenia
```

Packer nie rekonstruuje semantyki z globalnej listy pól. Serializuje projekcję
utworzoną przez domenę i odrzuca brak wersji/statement albo przekroczenie
budżetu. `fact_ref_map`, source IDs i `semantic_provenance` pozostają po stronie
backendu. V1/v2 zachowują historyczny package i registry compatibility.

Location przepływa bez zewnętrznego geocodingu:

```text
OSM tags -> scan agreement -> target.location -> mark_target
-> canonical target -> capture anchor -> semantic_fact.location
```

Kontrakt, reguły UNKNOWN > GUESS i bramka są opisane w
`doc/architecture/shared_llm_semantic_input_contract.md`. Read-only
`scripts/audit_semantic_input.py` pokazuje audience-safe ścieżkę
canonical source paths → semantic projection → dokładny model input.

Lokalna bramka obejmuje prawdziwy producer-backed `part_discovered`, wszystkie
aktywne event families, public/clan/owner, brak/missing/conflict location,
canonical labels, alias lineage, size budget, legacy v1/v2 i heavy-profile
zero.

Produkcyjny exit gate przeszedł 2026-09-03 na czterech rzeczywistych taskach
`part_discovered` (`public/blacknet`, `clan/blacknet`, `owner/blacknet`,
`public/googleplex_news`):

```text
audit_semantic_input --strict:       ok=true, errors=[]
sample_count:                        4
semantic contract:                   chaos-llm-semantic-input-v1
canonical location retained:         Zakopane
technical_identifier_leaks:          0 dla każdego package
audience projection:                 public/clan/owner rozdzielone
```

Wynik potwierdza kompletność i bezpieczeństwo rzeczywistego wejścia do modelu,
nie jakość wygenerowanego candidate. 137 zostaje odmrożony, a 137.1 wraca do
generacji oraz oceny outputu. Mojibake widoczne w kanale kopiowania wyniku
trzeba odróżnić od faktycznych bajtów UTF-8 osobnym probe; nie jest samo w sobie
dowodem uszkodzenia model input.

## Sprint 137.1 — CO model dostaje i JAK ma mówić

Etap 137.1 specjalizuje istniejący canonical worker bez dodawania kolejki,
workera ani modelu. Pierwszy server probe v2 ujawnił zbyt szeroki model input:
model otrzymywał canonical `event_id`, `cycle_id`, `public_entity_id` i pełny
`fact_id`, mimo że nie były potrzebne do narracji. Jeden z czterech candidates
został zaakceptowany, dwa pomyliły event ID z fact ref, a jeden ujawnił fragment
public entity ID w treści. Validator prawidłowo poddał trzy wyniki kwarantannie.

Pierwsza remediacja wprowadziła polityki v3 i minimalny semantic package.
Produkcyjny strict generation audit przeszedł technicznie dla pełnego fan-outu
`part_discovered`: cztery taski zostały ukończone, request hashes były zgodne,
lineage był pełny, a candidates zaakceptowane. Ręczna bramka głosu nie przeszła:

- wariant clan dopowiedział, że miejsce zdarzenia należy do klanu odbiorcy;
- wariant owner zrobił z powiązanej maszyny sprawcę odkrycia;
- publiczny BlackNet mechanicznie powtarzał statement i brzmiał raportowo;
- Googleplex skrócił nazwę miasta do urwanego `Zakopn` w tytule.

To nie był błąd kolejki ani validatora strukturalnego. Wejściowe role były zbyt
ogólne, a prompt nie blokował jednoznacznie fałszywych relacji. Aktywne,
addytywne polityki zostały więc podniesione do v4:

```text
BlackNet / Cyberner: ghostnetwork-event-prompt-v4
Googleplex News:     ghostnetwork-googleplex-prompt-v4
GhostSignal / radio: ghostsignal-prompt-v4
```

Model package dla v3 i v4 zawiera wyłącznie minimalny kontrakt narracyjny:

```text
medium
audience scope (bez surowego owner/clan identity)
narrative_intent
event_family
significance
tone_hint
bounded aggregate context tylko gdy event_count > 1
semantic_contract=chaos-llm-semantic-input-v1
semantic_facts z krótkimi aliasami f01/f02, canonical statement,
  audience-safe labels oraz opcjonalną canonical location/attributes
referencje do dozwolonego assetu tylko dla Googleplex
```

Surowe `outbox_id`, `source_event_id`, `event_id`, `cycle_id`,
`public_entity_id`, `audience_owner`, `audience_clan`, canonical `fact_id`,
wersje i puste pola kontekstowe nie są przekazywane modelowi v3/v4. Model zwraca
alias `f01`, a backend mapuje go z powrotem do canonical fact ID przed zapisem
candidate. To zachowuje lineage bez wystawiania identyfikatorów modelowi.
Model nie widzi `semantic_provenance`; audyt wiąże każdą wartość semanticzną z
canonical source path wyłącznie po stronie backendu.

CTA GhostNetwork pozostaje backend-owned. Model nie otrzymuje akcji ani jej
payloadu i schema wymusza `cta_ref=null`; fixed action jest dołączana po stronie
backendu. Schema ogranicza `fact_refs` bezpośrednio do aliasów danego taska.

Backend ustala również limity zależne od medium. Googleplex v5 ma krótki HERO
(`36/120`, jeden fact ref; historyczne wersje zachowują swój kontrakt), BlackNet
i Cyberner `72/420`, a radio `72/520`; schema generacji egzekwuje te same
granice.

W v4 role są wiążące i precyzyjne: target to `lokalizacja zakotwiczenia
zdarzenia`, clan audience to `klan odbiorcy`, a machine to `maszyna powiązana z
elementem`. Prompt zabrania tworzenia pomiędzy nimi relacji własności,
przyczynowości lub działania bez jawnego statement/attribute. BlackNet ma być
przechwytem z 2108, najwyżej dwoma krótkimi zdaniami, bez raportowego
wypełniacza i mechanicznego echa statement. Googleplex nie umieszcza nazw
własnych w tytule, ogranicza go do 36 znaków i przenosi pełne nazwy do leadu.

Pierwszy production candidate v4 potwierdził poprawną semantykę, lecz ponownie
nie przeszedł ręcznej bramki głosu. Publiczny BlackNet zwrócił neutralne
`Odkryto ukryty element sieci GhostNetwork` oraz niemal literalną parafrazę
statement. Samo polecenie stylu okazało się za słabe dla modelu 8B.

V5 przenosi minimalny wyróżnik BlackNet do egzekwowalnego kontraktu outputu:
tytuł musi zaczynać się od `PRZECHWYT //`, a body od `...`. Prompt daje jeden
krótki wzorzec struktury bez danych świata. Backend sprawdza oba prefiksy po
odpowiedzi; neutralny raport zostaje `rejected`.

Pierwszy request v5 z regexami `pattern` w JSON Schema dostał produkcyjne
`ollama_http_500`. Googleplex bez regexów rozpoczął generację, co odizolowało
problem do reprezentacji schema, a nie semantic input. Regexy usunięto z
payloadu Ollamy; twardy kontrakt pozostał backend-only jako `voice_contract`.
Prompt nadal przekazuje modelowi format naturalnym językiem. Istniejący task w
`retry_wait` może zostać wznowiony bez nowego eventu. Reguły faktów i ról nie
uległy zmianie.

Cutover jest addytywny. Nowe taski dostają v5, ale już zapisane taski v1–v4
nadal są claimowalne i publikowalne po swoim pełnym tuple wersji. V3/v4
zachowuje semantic system prompt oraz minimalny semantic package; nie zostaje
przypadkiem cofnięty do technicznego formatu v2. Worker nie przypisuje staremu
taskowi nowego promptu, a publisher nie odrzuca zarejestrowanego starszego
candidate jako superseded. Status kolejki raportuje
`ready_by_prompt_version`, a registry osobno liczbę active i legacy-compatible
policies.

Dowody lokalne i produkcyjne:

- kompletna macierz `GHOST_EVENT_POLICY -> medium -> active v5 policy`;
- producer-backed `cycle_activated` buduje package v5 dla BlackNet i
  Googleplex z poprawnym intent/family/significance;
- historyczne taski v1–v4 pozostają rozwiązywalne, a v3/v4 zachowują semantic
  package;
- production-shaped package nie zawiera canonical fact/event/cycle/entity ID;
- alias `f01` wraca do candidate jako pełny canonical fact ID;
- schema ogranicza fact refs do task-local aliases, a CTA do null;
- aggregate przekazuje bounded `event_count`;
- każdy fact przekazuje modelowi treść w `statement`, a nie sam alias;
- labels i location przechodzą audience projection przed serializacją;
- strict semantic audit na produkcyjnych taskach: `4 samples / PASS`, zero
  technical identifier leaks;
- core policy/worker/publication/cutover: `64 tests / PASS`;
- producer/runtime/publisher regression: `64 tests / PASS`.

Implementacja 137.pre.1 została wdrożona jako `a7fb8db`, a produkcyjny strict
audit zaliczył exit gate. Przed rozpoczęciem 137.2 nadal wymagane są server
verify registry, kontrola kolejki v1–v5 oraz nowy producer-backed task,
attempt i zaakceptowany candidate v5 korzystający z semantic input. Musi on
przejść również ręczną ocenę relacji oraz głosu medium; sam `ok=true` audytu
technicznego nie wystarcza.

### Bramka końcowa 137.1

Read-only `scripts/audit_narrative_generation.py` automatycznie łączy:

```text
persisted event
  -> komplet oczekiwanych audience/medium tasków aktywnego promptu
  -> dokładny semantic model input i request_hash
  -> ostatni attempt
  -> candidate oraz canonical fact lineage
```

Tryb `--strict` zwraca błąd dla brakującego fan-outu, taska bez attemptu,
niezgodnego request hash, taska/attemptu poza stanem completed, brakującego
candidate, kwarantanny/rejection, złego medium/audience/promptu oraz uszkodzonego
fact lineage. Raport pokazuje title/body/tone i semantic facts dla ręcznej oceny
języka oraz głosu medium. Automat nie może sam ogłosić, że tekst jest dobrym
BlackNetem tylko dlatego, że przeszedł schema validator.

Lokalna bramka auditowa obejmuje PASS, quarantine i brak generacji oraz ochronę
przed niepełnym producer fan-outem. Regresja policy/worker/semantic/audit:
`72 tests / PASS` dla policy/worker/semantic/audit/publication v5.

## Odblokowanie po zamknięciu Sprintu 136.2 — 2026-09-02

Sprint 136.2 ma pełny server pass: fan-out `public/clan/owner`, rzeczywisty
low-event aggregate z kompletnymi source links, reconciler pomijający pełne
lineage oraz końcowy strict audit `errors=[]`, `ok=true`. Blokada wejściowa
Sprintu 137 została usunięta.

## Korekta po audycie Sprintu 136 — 2026-09-02

Sprint 137 nie może rozpocząć odbioru produkcyjnego, dopóki Sprint 136 nie
udowodni kompletnego `persisted event -> task`. Produkcyjny
`ghost.part_discovered` został zapisany po poprawnym durable capture effect,
ale nie otrzymał żadnego taska. Registry, worker i validator nie mogą wykryć
braku danych, których nigdy nie przekazano do outboxa.

Od tej chwili test utworzony przez ręczne `enqueue_narrative_task()` albo
bezpośrednie `publish_narrative_event()` jest testem komponentowym, nie E2E
Sprintu 137. Każda rodzina generation/validation musi użyć przynajmniej
jednego taska wytworzonego przez realny producer i runtime entrypoint ze
Sprintu 136.

Remediacja 136.1 przeszła rewalidację serwerową. Historyczny osierocony event
został naprawiony przez bounded recovery, nowy realny drop utworzył oba
oczekiwane publiczne taski bezpośrednio w post-commit ingressie, a strict
lineage audit zwrócił `ok=true`. Bramka wejściowa Sprintu 137 jest otwarta.

Po rozpoczęciu 136.2 bramka została ponownie zamknięta wyłącznie na czas
walidacji nowego audience fan-outu i agregacji low-eventów. 136.1 pozostaje
`SERVER PASS`; 137 może ruszyć po serwerowym potwierdzeniu 136.2.

### Bramka wejściowa 136 -> 137

Przed claimem workera musi przejść automatyczne złączenie kontraktów:

```text
GHOST_EVENT_POLICY.target_media
  == rzeczywiste taski dla persisted source_event_id
  == aktywne kombinacje registry (source_scope, task_variant, medium)
```

Bramka odrzuca:

- eligible event bez wszystkich oczekiwanych tasków;
- task bez istniejącego source eventu;
- task z medium niezgodnym z event policy;
- task z `audience_scope != public` w Etapie I;
- task variant bez aktywnej polityki workera;
- source event przetworzony tylko przez syntetyczny test publishera;
- dwa source scopes reprezentujące ten sam canonical event bez wspólnej
  publication identity.

Dozwolony jest krótki, jawny grace period między zapisem eventu a enqueue.
Po jego upływie `eligible_without_task` jest błędem strict, a nie ostrzeżeniem.
Raport ma być bounded i profile-free.

## Kontekst po Sprintach 135.4–135.6

Historyczny Sprint 137 miał utworzyć pierwszy worker Ollamy, Inbox, claim,
lease, retry, walidację oraz dead letter. Ten zakres jest już wykonany przez
canonical roadmapę 135.4–135.6.

Sprint 137 nie tworzy kolejnego workera ani osobnego GhostNetwork Inbox/Outbox.
Specjalizuje istniejący worker, prompt registry i walidator dla bezpiecznych
tasków zdarzeń GhostNetwork przygotowanych w Sprincie 136.

## Potwierdzony baseline

Obecny runtime zapewnia:

- `OllamaNarrativeWorker` z atomic claim, lease i heartbeat renewal;
- retry, bounded attempts, dead letter i recovery po utracie workera;
- trwałą historię attempts oraz telemetry input bytes/fact count;
- wersjonowany prompt registry i fail-closed policy resolution;
- bounded TASK PACKAGE bez dostępu modelu do bazy i profilu;
- JSON schema oraz parser/validator outputu;
- jeden candidate na task i recovery bez drugiego model call;
- backend-owned source, audience, truth class oraz CTA payload;
- `status`, `verify`, `dry-run`, `run-once` i proces PM2;
- canonical candidate gotowy do istniejącego publication pipeline.

Baseline testowy przed startem Sprintów 137–138:

```text
tests.test_ollama_policy
tests.test_ollama_worker
tests.test_narrative_publications
tests.test_llm_publishers

59 tests / PASS
```

## Rzeczywista luka Sprintu 137 przed etapem 137.1

- registry zawiera stary wariant `connection_completed`, podczas gdy domena
  emituje `ghost.connection_created`;
- registry nie zawiera `cycle_activated`;
- `source_scope=ghostnetwork` nie posiada polityk dla `googleplex_news`;
- `ghostnetwork/event-v1` jest jednym bardzo ogólnym, dwuzdaniowym promptem;
- prompt nie otrzymuje jeszcze wyraźnego code-owned intentu, significance i
  formatu odpowiedniego dla rodziny eventu;
- generic walidator nie ma pełnego kontraktu semantycznego GhostNetwork;
- brak osobnej kontroli, czy model nie zmienił statusu, outcome, widoczności
  węzła albo tożsamości klanu;
- brak testów jakości public/clan/owner dla nowych tasków Sprintu 136;
- brak fizycznej serii generacji dla part/conflict/machine/cycle/signal.

## Cel

Istniejący worker ma przekształcać jeden backend-selected, audience-safe task
GhostNetwork w krótką narrację odpowiednią dla medium. Model nie decyduje,
co się wydarzyło, kto to widzi ani dokąd prowadzi CTA.

```text
Sprint 136 projected task
  -> registered GhostNetwork policy
  -> bounded model package
  -> JSON output
  -> GhostNetwork semantic validation
  -> canonical candidate
```

## Bezwzględna bramka heavy profile

Worker, prompt builder, validator, retry i dry-run muszą zachować:

```text
profile_full_read:           0
profile_full_write:          0
profile_bytes:               0
account_scan:                0
all_user_profile_scan:       0
per_recipient_profile_read:  0
```

Zakazane są importy i wywołania `get_profile`, `list_profiles`,
`load_profile*`, `users.profile_json`, mapy, operacji, plików, GX i walleta.
Walidator nie może doczytywać pełnego wewnętrznego snapshotu tylko po to,
aby sprawdzić tekst modelu. Bezpieczeństwo zapewnia projected input oraz
fail-closed porównanie z taskiem.

## Kontrakt modelu

Model otrzymuje wyłącznie:

```text
medium
audience scope
narrative_intent
event family
significance / tone hint
`semantic_facts[].statement`
task-local fact aliases
audience-safe canonical labels
opcjonalną canonical city/country i bounded attributes
bounded thread context prepared by backend
allowed asset roles
output schema
title/body budgets
```

Model nie otrzymuje:

- `part_id`, jeżeli audience nie ma prawa go znać;
- `event_id`, `cycle_id`, `public_entity_id`, canonical `fact_id` ani inne
  techniczne identyfikatory niezależnie od audience;
- backendowego `semantic_provenance` i canonical source paths;
- pełnej topologii, rewardów, profilu lub listy graczy;
- dowolnych URL i endpointów;
- listy możliwych odbiorców;
- możliwości wyboru CTA payloadu, priority, TTL lub thread identity.

## Kontrakt outputu

Zachowujemy mały canonical schema z 135.4:

```json
{
  "title": "...",
  "body": "...",
  "tone": "warning",
  "fact_refs": ["f01"],
  "cta_ref": null,
  "asset_ref": null
}
```

Model nie zwraca `task_id`, `source_scope`, `audience`, `truth_class`,
`priority`, `thread_id`, `expires_at`, `cta_action` ani `cta_payload`. Te pola
są kopiowane z taska przez backend. Nie rozszerzamy modelowi uprawnień tylko
dlatego, że historyczny plan przewidywał większy JSON.
Po walidacji backend mapuje `f01` na canonical fact ID i dołącza fixed CTA bez
udziału modelu.

## Prompt policy

Jedna wersjonowana polityka może obsługiwać kilka rodzin, ale task musi
zawierać code-owned `narrative_intent`. Minimalne intenty:

```text
ghost_part_discovery
ghost_part_containment
ghost_part_activation
ghost_part_conflict
ghost_part_recovery
ghost_machine_progress
ghost_machine_state
ghost_cycle_state
ghost_signal_transmission
ghost_system_transition
```

### BlackNet

- fragment przechwyconego przekazu z 2108;
- zwięzły, enigmatyczny, ale informacyjny;
- bez raportowego wypełniacza typu "system zarejestrował";
- bez przepisywania label/value/stat słowo w słowo;
- bez wymyślania nazw ukrytych części i lokalizacji.

### Googleplex News

- zweryfikowany world dispatch, nie przechwycona plotka;
- czytelny tytuł i krótki lead dopasowany do istniejącego HERO;
- asset wyłącznie z backendowej allowlisty;
- brak surowych współrzędnych, identyfikatorów i technicznych prefiksów.

### Cyberner / GhostSignal

- enigmatyczna transmisja oparta tylko na faktach;
- model nie rozstrzyga autentyczności, outcome ani odpowiedzi z 2108;
- backend decyduje, czy event w ogóle trafia do tego medium.

## GhostNetwork semantic validator

Oprócz generic schema/safety validator sprawdza:

- wszystkie `fact_refs` należą do taska i co najmniej jeden jest użyty;
- candidate zachowuje task audience i truth class;
- schema wymusza modelowe `cta_ref=null`, a backend dołącza wyłącznie fixed
  action zapisane w tasku;
- output nie zawiera raw `part_id`, `entity_id`, `cycle_id`, hashy i nazw
  technicznych niewidocznych w projected facts;
- public output nie nazywa ukrytej części, maszyny, profesji, ability ani
  prywatnego ownera;
- model nie zmienia `status`, `conflict_state`, `outcome`, wersji i liczników;
- GhostSignal nie staje się delivered/confirmed bez canonical factu;
- Googleplex asset należy do `allowed_asset_roles`;
- limity title/body są zależne od medium i presentation slotu;
- echo source label oraz narrative filler mogą zostać odrzucone kodem.

Naruszenie prywatności, invented fact lub capability escalation jest
terminalne. Timeout, HTTP failure i pierwszy invalid JSON pozostają retryable.

## Etap I — registry, package i validator

1. Wymienić `connection_completed` na realny `connection_created`.
2. Dodać `cycle_activated` oraz polityki Googleplex News wymagane przez 136.
3. Wersjonować nowy prompt contract bez nadpisywania historycznego v1.
4. Używać zaliczonego Shared Semantic Input Layer dla statement, labels,
   location, attributes i task-local lineage aliases.
5. Dodać `narrative_intent`, significance i bounded thread context do package.
6. Rozszerzyć validator o kontrakt GhostNetwork i technical-ID firewall.
7. Zachować jeden generic worker i jeden canonical Inbox.
8. Rozszerzyć registry verification oraz cutover audit.

## Etap II — jakość i failure validation

Produkcyjny probe v4 ujawnił również powtarzalne `sqlite3.OperationalError:
database is locked` podczas `BEGIN IMMEDIATE` w claimie workera. PM2 odzyskał
proces i kolejka ruszyła dalej, więc nie jest to przyczyna złego tekstu, ale
jest konkretnym przypadkiem failure/recovery do zamknięcia w 137.3. Sam restart
przez PM2 nie stanowi jeszcze zaliczenia polityki retry/backoff.

1. Uruchomić model zastępczy dla każdej rodziny eventu.
2. Uruchomić serię realnych generacji dla public/clan/owner.
3. Sprawdzić odmienny głos BlackNet, Googleplex News i GhostSignal.
4. Wstrzyknąć timeout, invalid JSON, invented fact, hidden identity i CTA
   escalation.
5. Potwierdzić heartbeat przy generacji dłuższej od bazowego lease.
6. Potwierdzić candidate recovery bez drugiego model call.
7. Zebrać telemetry latency/tokens/rejection reasons bez logowania faktów
   prywatnych.

## Retry i fallback

Retry pozostaje wspólną polityką canonical workera. Sprint nie dodaje
osobnego `CHAOS_GHOSTNETWORK_OLLAMA_*`, jeżeli istniejące
`CHAOS_OLLAMA_*` rozstrzyga ten sam proces.

Rejected/dead-letter candidate nie publikuje fałszywej odpowiedzi. Ewentualny
canonical fallback dla critical eventu jest decyzją Sprintu 138 i musi użyć
tej samej publication identity; nie jest drugim postem.

## Testy

- dla każdego wariantu test zaczyna się od realnego producenta 136 i pobiera
  task po jego `source_event_id`; ręcznie skonstruowany task pozostaje osobnym
  testem jednostkowym;
- macierz policy -> outbox -> registry jest kompletna dla wszystkich
  docelowych mediów, a nie tylko dla nazw obecnych w setach registry;
- worker preflight nie może być uznany za zdrowy, gdy
  `ghost_event_lineage.eligible_without_task > 0`;
- wszystkie allowlisted warianty 136 mają zarejestrowaną politykę;
- nieznany wariant i stary alias są fail-closed;
- BlackNet/GGPL/Cyberner otrzymują właściwy prompt/schema;
- package pozostaje bounded i profile-free;
- każdy semantic fact ma niepusty canonical statement; sam alias jest
  niewystarczający i blokuje claim fail-closed;
- `semantic_contract`, statement, labels, location i attributes przechodzą
  technical-ID firewall oraz budget przed wywołaniem Ollamy;
- provenance pozostaje backend-only i pozwala audytować canonical source path
  bez ujawnienia go modelowi;
- public/clan/owner packages nie przeciekają między audience;
- unknown fact ref i brak fact ref są odrzucone;
- hidden identity, invented outcome i CTA escalation są terminalne;
- invalid JSON i timeout mają kontrolowany retry;
- tylko jeden candidate może zostać canonical wynikiem taska;
- crash po zapisie candidate nie wywołuje modelu drugi raz;
- fixture profilu 35 MB daje wszystkie heavy-profile counters równe zero;
- model failure nie blokuje gameplayu ani bridge'a 136.

## Walidacja serwerowa

1. Uruchomić strict lineage audit 136 oraz
   `scripts/audit_semantic_input.py --strict` przed `verify` registry/model i
   przed claimem; wszystkie muszą przejść.
2. Semantic audit musi pokazać niepuste statements, oczekiwane audience-safe
   labels/location, backend provenance i zero technical identifier leaks.
3. Po jednym tasku part, conflict, machine, cycle i signal, utworzonym przez
   realny runtime entrypoint i powiązanym z istniejącym persisted eventem.
4. Dla każdego sprawdzić task/attempt/candidate i rejection report.
5. Osobno sprawdzić public/clan/owner bez konta spoza audience.
6. Wymusić jeden timeout i potwierdzić recovery.
7. Sprawdzić brak nowych ineligible ready tasks.
8. Strict cutover audit oraz heavy-profile audit muszą być `ok=true`.
9. Dla każdego taska zachować jeden łańcuch identyfikatorów:
   `event_id -> outbox_id -> attempt_id -> candidate_id`; brak dowolnego
   wcześniejszego ogniwa blokuje zaliczenie późniejszego.
10. Uruchomić `scripts/audit_narrative_generation.py --strict` dla nowego
    producer-backed eventu. Wszystkie taski muszą być accepted, request hashes
    zgodne, a title/body zatwierdzone ręcznie pod kątem języka i głosu medium.

## Definition of Ready

```text
canonical worker/inbox:                    COMPLETE
claim/lease/heartbeat/retry:               COMPLETE
generic schema and validator:              COMPLETE
publication handoff:                       COMPLETE
baseline worker/publisher tests:           59 / PASS
Sprint 136 component task contract:        PRESENT
Sprint 136 runtime ingress:                SERVER PASS
Sprint 136 strict lineage audit:           SERVER PASS
Shared Semantic Input Layer:               SERVER PASS
semantic input technical-ID firewall:      SERVER PASS
GhostNetwork specialization scope:         FROZEN
```

## Definition of Done

Sprint 137 jest zakończony, gdy każdy eligible task GhostNetwork z 136 ma
wersjonowaną politykę, bounded audience-safe package i candidate przechodzący
semantic validation, a timeout, crash, invalid output i privacy violation są
obsługiwane bez wpływu na gameplay i bez ciężkiego profilu.
Dodatkowo każdy testowany task musi pochodzić z osiągalnego producenta 136, a
strict lineage audit nie może wykazywać eligible eventów bez taska ani tasków
bez eventu. Każdy aktywny package musi mieć domenowo utworzoną semantykę,
backend-only provenance, audience projection i zero technical identifier
leaks; sam `fact_ref` bez statement nie spełnia Definition of Done.

## Poza zakresem

- nowy worker, Inbox, Outbox lub file queue;
- zmiana lokalnego modelu bez osobnej decyzji operatorskiej;
- publikacja i UI lifecycle — Sprint 138;
- model wybierający audience, fact, priority, CTA payload, TTL lub thread;
- pełny profil lub zapytania do gameplay stores;
- masowe regenerowanie historycznych tasków;
- commit, push, deploy i restart w ramach przygotowania.
