# Sprint 137 — GhostNetwork Narrative Generation and Validation

Status: `READY — AFTER SPRINT 136`

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

## Rzeczywista luka Sprintu 137

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
projected canonical facts
fact refs
bounded thread context prepared by backend
fixed CTA capability reference
allowed asset roles
output schema
title/body budgets
```

Model nie otrzymuje:

- `part_id`, jeżeli audience nie ma prawa go znać;
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
  "fact_refs": ["ghost_fact:..."],
  "cta_ref": "c01",
  "asset_ref": null
}
```

Model nie zwraca `task_id`, `source_scope`, `audience`, `truth_class`,
`priority`, `thread_id`, `expires_at`, `cta_action` ani `cta_payload`. Te pola
są kopiowane z taska przez backend. Nie rozszerzamy modelowi uprawnień tylko
dlatego, że historyczny plan przewidywał większy JSON.

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
- CTA ref wskazuje wyłącznie fixed backend action;
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
4. Dodać `narrative_intent`, significance i bounded thread context do package.
5. Rozszerzyć validator o kontrakt GhostNetwork.
6. Zachować jeden generic worker i jeden canonical Inbox.
7. Rozszerzyć registry verification oraz cutover audit.

## Etap II — jakość i failure validation

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

- wszystkie allowlisted warianty 136 mają zarejestrowaną politykę;
- nieznany wariant i stary alias są fail-closed;
- BlackNet/GGPL/Cyberner otrzymują właściwy prompt/schema;
- package pozostaje bounded i profile-free;
- public/clan/owner packages nie przeciekają między audience;
- unknown fact ref i brak fact ref są odrzucone;
- hidden identity, invented outcome i CTA escalation są terminalne;
- invalid JSON i timeout mają kontrolowany retry;
- tylko jeden candidate może zostać canonical wynikiem taska;
- crash po zapisie candidate nie wywołuje modelu drugi raz;
- fixture profilu 35 MB daje wszystkie heavy-profile counters równe zero;
- model failure nie blokuje gameplayu ani bridge'a 136.

## Walidacja serwerowa

1. `verify` registry/model przed claimem.
2. Po jednym realnym tasku: part, conflict, machine, cycle i signal.
3. Dla każdego sprawdzić task/attempt/candidate i rejection report.
4. Osobno sprawdzić public/clan/owner bez konta spoza audience.
5. Wymusić jeden timeout i potwierdzić recovery.
6. Sprawdzić brak nowych ineligible ready tasks.
7. Strict cutover audit oraz heavy-profile audit muszą być `ok=true`.

## Definition of Ready

```text
canonical worker/inbox:                    COMPLETE
claim/lease/heartbeat/retry:               COMPLETE
generic schema and validator:              COMPLETE
publication handoff:                       COMPLETE
baseline worker/publisher tests:           59 / PASS
Sprint 136 task contract:                  REQUIRED
GhostNetwork specialization scope:         FROZEN
```

## Definition of Done

Sprint 137 jest zakończony, gdy każdy eligible task GhostNetwork z 136 ma
wersjonowaną politykę, bounded audience-safe package i candidate przechodzący
semantic validation, a timeout, crash, invalid output i privacy violation są
obsługiwane bez wpływu na gameplay i bez ciężkiego profilu.

## Poza zakresem

- nowy worker, Inbox, Outbox lub file queue;
- zmiana lokalnego modelu bez osobnej decyzji operatorskiej;
- publikacja i UI lifecycle — Sprint 138;
- model wybierający audience, fact, priority, CTA payload, TTL lub thread;
- pełny profil lub zapytania do gameplay stores;
- masowe regenerowanie historycznych tasków;
- commit, push, deploy i restart w ramach przygotowania.
