# Sprint 136 — GhostNetwork Domain Narrative Bridge

Status: `136.1 SERVER PASS / 136.2 IMPLEMENTED LOCALLY — SERVER VALIDATION REQUIRED`

## Sprint 136.2 — audience projection i kontrola szumu

Etap II został wdrożony lokalnie bez zmiany mechaniki gry i bez tworzenia
drugiej kolejki, workera lub publishera.

- Persisted event rozwiązuje stabilny, bounded zestaw odbiorców wyłącznie z
  canonical event fields i snapshotu payloadu: zawsze `public`, a gdy istnieją
  uprawnione identyfikatory również `clan` i `owner`.
- Publiczne facts pozostają zredagowane. Clan otrzymuje wyłącznie dozwolony
  kontekst własnego klanu, a owner prywatną projekcję części. Resolver nie czyta
  profili ani listy kont; test z profilem 35 MB potwierdza zero wywołań.
- Public audience zachowuje media z event policy. Prywatne projekcje trafiają
  wyłącznie do audience-filtered BlackNetu i nie konkurują z publicznym
  contentem o globalny slot Googleplex News.
- Thread identity jest stabilne dla cyklu, publicznej/prywatnej projekcji
  części, maszyny, konfliktu i sygnału. Prywatny thread używa hasha i nie
  ujawnia ownera ani surowego `part_id`.
- `connection_created` oraz `machine_progress_changed` używają 15-sekundowego
  okna. Pierwszy task jest opóźniony, kolejne eventy aktualizują ten sam ready
  task; high/critical nadal mają `next_attempt_at=created_at`.
- Lekka tabela `ghost_narrative_task_sources` mapuje wiele source eventów do
  jednego canonical taska. Dzięki temu agregacja zachowuje pełny strict lineage
  i exactly-once przy retry.
- Bounded telemetry raportuje events seen/eligible/ignored, taski według
  event/audience/medium, wejścia i wyjścia agregacji, dedupe, błędy oraz średnią
  i maksymalną latencję bridge'a. Strict audit rozumie fan-out oraz agregaty.
- Test agregacji składa 20 realnych `connection_created` w jeden task z 20
  linkami source. Regresja: `253 GhostNetwork tests / PASS` oraz `59 downstream
  worker/publication tests / PASS`.

Wymagana jest walidacja serwerowa fan-outu, agregatu, strict audytu i braku
ciężkiego profilu przed oznaczeniem 136.2 jako `COMPLETE`.

## Remediacja 136.1 — 2026-09-02

Historyczny FAIL opisany poniżej został zamknięty w kodzie lokalnym. Jedna
granica post-commit pobiera event ponownie z `ghost_part_events` po `event_id`,
buduje wyłącznie publiczną projekcję i idempotentnie zapisuje oczekiwane taski
w istniejącym `ghost_narrative_outbox`.

- Podłączono realne entrypointy capture, territory lifecycle, strategic
  conflict, tworzenia cyklu, locka oraz transmisji.
- Dispatch nie zależy już wyłącznie od kształtu zwracanego drzewa. Dla operacji
  wieloeventowych czytane są również bounded rekordy zapisane po wejściowym
  `state_version`, dzięki czemu nie giną eventy pośrednie.
- Source audience (`player`, `owner`, `clan`, `system`) pozostaje metadanym
  mechaniki. Każdy eligible event Etapu I tworzy jedną redagowaną projekcję
  `public`; allowlista nadal blokuje eventy techniczne i nieznane.
- Błąd narracji pozostaje fail-open dla gameplayu. Bounded reconciler workera
  odtwarza brakujące taski z event store także wtedy, gdy preflight Ollamy jest
  chwilowo niedostępny.
- Strict cutover zawiera teraz złączenie `eligible event -> expected media
  tasks` oraz wykrywa brak taska, brak source eventu, zły medium i zły audience.
- Konsument rewardów akceptuje wyłącznie kanoniczne persisted eventy i
  deduplikuje `event_id`, więc task narracyjny nie może zostać policzony jako
  drugi event nagrodowy.
- Lokalna regresja ingress + worker + publication: `87 tests / PASS`.
  Pełna regresja 36 modułów GhostNetwork: `250 tests / PASS`.

### Rewalidacja serwerowa — PASS

- Reconciler naprawił historyczny osierocony `event_d695f50fdafa44fa`, tworząc
  dokładnie dwa publiczne taski: `blacknet` i `googleplex_news`.
- Strict cutover zwrócił `ok=true`, `eligible_without_task=0`,
  `missing_expected_tasks=0`, `tasks_with_missing_event=0`,
  `unexpected_medium=0`, `wrong_audience=0` oraz wszystkie liczniki heavy
  profile równe zero.
- Nowy rzeczywisty drop utworzył `event_5b6d395c4b340577` o
  `2026-09-02T12:29:43.039428+00:00`. Bezpośredni post-commit ingress zapisał
  task BlackNet o `12:29:43.176418+00:00` i Googleplex News o
  `12:29:43.266762+00:00`, oba z `audience_scope=public`.
- Statusy `processing/ready` w chwili odczytu potwierdzają przekazanie do
  istniejącego downstreamu; ukończenie generowania i publikacji należy do
  zakresu Sprintów 137–138.

Remediacja 136.1 ma lokalny i serwerowy dowód. Etap I jest `COMPLETE`.

## Audit integracyjny po walidacji serwerowej — 2026-09-02

W momencie tej walidacji Etap I nie był ukończony. Rzeczywisty drop wykazał, że
zielone testy komponentowe i strict audit 135.6 nie dowodziły przejścia od
trwałego eventu domenowego do canonical outboxa.

Dowód produkcyjny:

```text
ghost_capture_effects
  effect_id:     ghost-capture-effect_f9cde07c4ade62eb
  status:        applied
  last_outcome:  discovered
  attempts:      1
  created_at:    2026-09-02T08:37:45.618504+00:00

ghost_part_events
  event_id:       event_d695f50fdafa44fa
  event_type:     ghost.part_discovered
  state_version:  687
  audience_scope: player
  created_at:     2026-09-02T08:37:45.770840+00:00

ghost_narrative_outbox WHERE source_event_id=event_d695f50fdafa44fa
  0 rows
```

Mechanika dropu i zapis eventu zakończyły się poprawnie, ale task narracyjny
nie powstał. To jest blocker Sprintu 136, nie awaria Ollamy ani publishera.

### Ustalenia audytu

1. `GhostRuntimeCoordinator.process_effect()` obsługuje reward i deltę, lecz
   nie wywołuje `publish_narrative_event()`. To bezpośrednia przyczyna braku
   taska dla rzeczywistego `ghost.part_discovered`.
2. `_audiences_for_event()` dziedziczy `player -> owner`, `clan -> clan`, a
   `internal/system` odrzuca. Etap I wymaga natomiast jednej bezpiecznej
   projekcji `public`; owner/clan fan-out jest zakresem Etapu II. Ponieważ
   `append_event()` domyślnie zapisuje `audience_scope=system`, część eventów
   z allowlisty zostałaby cicho pominięta nawet po dopięciu dispatchu. Samo
   dodanie wywołania publishera nie naprawi więc kontraktu.
3. Dispatch zależy od tego, czy event został przypadkowo dołączony do
   zwracanego drzewa jako `event`, `events` albo `_domain_event`. Sam trwały
   zapis w `ghost_part_events` nie gwarantuje publikacji.
4. `ghost.connection_created` jest zapisywany przy budowie topologii, a
   `ghost.cycle_activated` przy aktywacji cyklu, ale ich producent nie zwraca
   eventu do wspólnego runtime bridge'a.
5. `ghost.cycle_locked` powstaje już po wykonaniu
   `apply_ghostnetwork_runtime_result()`. `ghost.version_changed` i
   `ghost.stabilization_started` powstają wewnątrz transmisji, podczas gdy
   specjalny bridge publikuje tylko GhostSignal. Te eventy nie mają
   potwierdzonego wspólnego dispatchu.
6. Przy przejściu konfliktowym `_apply_part_outcome()` może zapisać
   `ghost.part_conflict_resolved`, następnie pobrać część ponownie i zwrócić
   dopiero kolejny event. Pierwszy persisted event znika wtedy ze zwracanego
   drzewa i nie dociera do kolektora.
7. `part_defended` i `part_recovered` są zwracane przez serwis konfliktów, ale
   audyt nie wykazał produkcyjnego entrypointu, który zawsze przekazuje ten
   wynik do narrative dispatchu.
8. `audit_narrative_cutover.py` kontroluje taski, candidates, receipts i
   records, ale nie wykonuje złączenia `eligible persisted event -> expected
   outbox task`. Dlatego zwrócił `ok=true` mimo osieroconego eventu.
9. Testy 136 wywoływały `publish_narrative_event()` na ręcznie zbudowanym
   publicznym evencie. Udowodniły poprawność komponentu, ale nie osiągalność
   komponentu z realnego producenta. Test territory obejmował tylko jedną
   wybraną ścieżkę i nie sprawdzał publicznego audience.

### Macierz osiągalności eventów — stan po audycie

| Rodzina | Rzeczywisty producent | Obecna droga do bridge'a | Werdykt |
|---|---|---|---|
| `part_discovered` | durable capture effect -> `discover_reserved_part` | reward + delta, bez narrative | **brak** |
| `part_contained/revealed/activated/deactivated/contested` | lifecycle wywołany przez territory reconciliation | `_domain_event` w zwracanej części -> `apply_ghostnetwork_runtime_result` | częściowa; source audience nie jest public-only |
| `part_conflict_resolved` | lifecycle podczas rozstrzygnięcia terytorium | event może zostać utracony przed zwrotem wyniku | **brak gwarancji** |
| `part_defended/recovered` | strategic conflict outcome | wynik zawiera `events`, ale brak dowodu wspólnego produkcyjnego dispatchu | **nieudowodnione** |
| `connection_created` | tworzenie topologii cyklu | persisted event nie wraca z producenta | **brak** |
| `machine_progress_changed/online/offline` | recompute po zmianie części | nested module result -> territory runtime bridge | częściowa; clan audience i brak gwarancji dla innych wywołań |
| `cycle_activated` | tworzenie/aktywacja cyklu | transition zwraca cycle, nie event | **brak** |
| `cycle_locked` | finalizer po readiness | event powstaje po wcześniejszym runtime dispatchu | **brak** |
| `signal_sent` | transmission | osobny `publish_signal_transmission` | działa osobną ścieżką; wymaga testu retry/resume |
| `version_changed/stabilization_started` | transmission | wynik nie jest przekazywany do wspólnego narrative dispatchu | **brak** |

Macierz jest bramką implementacyjną. Wiersz nie może otrzymać statusu `PASS`
na podstawie ręcznego wywołania publishera; wymagany jest test od rzeczywistego
producenta domenowego do wiersza w `ghost_narrative_outbox`.

### Wymagana korekta architektury Etapu I

Nie należy dopisywać kolejnych lokalnych wywołań publishera do przypadkowych
controllerów. Potrzebna jest jedna jawna, idempotentna granica post-commit:

```text
persisted event_id
  -> resolve code-owned event policy
  -> build public visibility projection
  -> enqueue expected canonical task identities
  -> record bounded dispatch outcome
```

Wszystkie producenckie entrypointy muszą przekazywać `event_id` do tej samej
granicy. Zwracane drzewa wyników mogą służyć UI, ale nie mogą być jedynym
źródłem kompletności narracji. Błąd enqueue pozostaje fail-open dla mechaniki,
jednak persisted event musi pozostać wykrywalny jako `eligible_without_task` i
możliwy do bezpiecznego, idempotentnego ponowienia z bounded recent-event
reconciliation. Nie tworzymy nowej kolejki: źródłem recovery jest istniejący
event store, a celem istniejący canonical outbox.

W Etapie I policy określa docelowe audience taska jako `public`, niezależnie od
technicznego audience źródłowego eventu (`player`, `owner`, `clan`, `internal`
lub `system`). Publikacja jest dozwolona wyłącznie dla jawnej allowlisty i musi
zbudować nową bezpieczną publiczną projekcję; nie wolno upublicznić source
payloadu. Source audience pozostaje metadanym domenowym, nie decyzją o
narrative fan-out.

### Macierz osiągalności po remediacji 136.1 — lokalnie

| Rodzina | Wspólna granica post-commit | Dowód lokalny |
|---|---|---|
| `part_discovered` | durable capture -> persisted event -> dispatcher | PASS: capture effect, retry i fail-open |
| `part_contained/revealed/activated/deactivated/contested` | territory entrypoint + persisted version range | PASS: real territory worker path |
| `part_conflict_resolved` | territory entrypoint + persisted version range | PASS: event niewidoczny w końcowym drzewie nadal otrzymuje taski |
| `part_defended/recovered` | strategic conflict entrypoint + persisted version range | PASS: oba realne wyniki konfliktu |
| `connection_created/cycle_activated` | service cycle creation + persisted version range | PASS: wszystkie eligible eventy nowego cyklu |
| `machine_progress_changed/online/offline` | territory module recompute + ten sam version range | PASS: wspólna granica obejmuje eventy pośrednie |
| `cycle_locked` | service lock entrypoint + persisted version range | PASS: runtime finalizer |
| `signal_sent/version_changed/stabilization_started` | transmission + persisted version range | PASS: runtime finalizer i exact task media |

Wszystkie powyższe statusy są lokalne. Produkcyjny PASS wymaga deployu bez
czyszczenia canonical tables, uruchomienia strict audytu i realnego smoke.

## Pierwsza implementacja Etapu I — 2026-09-02 (niezaliczona E2E)

- Dodano jedną wersjonowaną `ghostnetwork-event-policy-v1` z jawną allowlistą,
  listą eventów technicznych, significance, priority, narrative intent, mediami
  i rodziną CTA. Nieznane eventy oraz historyczny `connection_completed` są
  kontrolowanie ignorowane.
- Publiczne facts przechodzą przez bounded `GhostVisibilityService`; surowe
  `part_id`, `entity_id`, profesja, ability i prywatny owner nie trafiają do
  taska. Naprawiono również helper `signal_id`, aby dla eventów części nie
  kopiował `entity_id` do metadanych outboxa.
- Każdy eligible event trafia do BlackNetu. High/critical otrzymuje drugi task
  dla istniejącego `gp-home-world-grid` z CAS `expected_slot_version`, jednym
  backend-selected source i istniejącą polityką `googleplex_world_dispatch`.
- Task zapisuje backend-owned CTA/fixed action, priority, intent, content kind,
  source ref/version oraz stabilny `narrative_thread_id`. Dodano lekką kolumnę
  thread ID do canonical outboxa; bez nowej tabeli, kolejki lub procesu.
- Lokalny baseline rozszerzony z 31 do 35 testów przechodził, ale obejmował
  głównie policy/publisher z syntetycznym eventem. Nie był dowodem E2E.
  Produkcyjny test dropu opisany wyżej obalił kompletność implementacji.

## Kontekst po Sprincie 135.6

Historyczny plan opisywał Sprint 136 jako utworzenie bridge'a zdarzeń do
outboxa. Ten opis został częściowo zastąpiony przez Sprinty 135.2–135.6.
Produkcja posiada już jeden canonical pipeline:

```text
canonical source
  -> ghost_narrative_outbox
  -> Ollama worker
  -> validated candidate
  -> publication receipt
  -> medium record
  -> BlackNet / Googleplex News / Cyberner
```

Sprint 136 nie tworzy drugiej kolejki, drugiego workera, drugiego publishera ani
legacy fallbacku plikowego. Rozszerza istniejący `GhostNarrativePublisher` o
brakującą politykę zdarzeń GhostNetwork, projekcję widoczności i routing do
istniejących mediów.

## Potwierdzony baseline

Komponenty obecnego kodu zapewniają:

- `source_scope=ghostnetwork` w canonical `ghost_narrative_outbox`;
- idempotentny enqueue, gdy bridge zostanie jawnie wywołany z eventem;
- idempotentny task i canonical dedupe;
- fail-open narracji: błąd bridge'a nie cofa mechaniki gry;
- publiczny `public_entity_id` zamiast surowego `part_id` w generic fact;
- niezależną publiczną projekcję dla eligible source eventów, także gdy ich
  audience domenowe ma wartość `internal/system`;
- lekki `UserIdentityProjectionStore` dla odbiorców delt;
- działający worker, walidację candidate, publication receipt i read model;
- brak pełnego profilu w task package.

Baseline testowy przed startem:

```text
tests.test_ghostnetwork_narrative:              PASS
tests.test_ghostnetwork_delta_audience_bridge:  PASS
tests.test_llm_event_producers:                 PASS
razem:                                          31 tests / PASS
```

## Luka, którą zamyka Sprint 136

Obecny bridge jest fundamentem, nie ukończonym kontraktem:

- obsługa zdarzeń jest implicit w `build_facts`, bez jednej jawnej allowlisty;
- kod oczekuje `ghost.connection_completed`, a domena zapisuje
  `ghost.connection_created`;
- `ghost.cycle_activated` nie jest jeszcze narracyjnie obsługiwany;
- każdy event dziedziczy tylko jeden scope, bez kontrolowanego public/clan/owner
  fan-out;
- generic fact nie jest jeszcze audience-specific projekcją
  `GhostVisibilityService`;
- GhostNetwork kieruje taski do BlackNet/Cyberner/Radio, ale nie do
  `googleplex_news`;
- brak code-owned significance, priority, narrative intent i cooldownu;
- CTA dla zwykłych eventów otwiera wyłącznie cały suite, zamiast wskazać
  bezpieczną część albo terytorium;
- brak kontrolowanej agregacji niskopoziomowych zmian maszyny i połączeń;
- brak stabilnego `narrative_thread_id` dla historii części, maszyny,
  konfliktu i sygnału.

## Cel

Ważne zdarzenie GhostNetwork ma deterministycznie utworzyć bezpieczne,
audience-specific fakty. Backend wybiera wydarzenie, odbiorców, medium,
priorytet, CTA i dozwolony asset. Ollama wyłącznie pisze narrację z przekazanych
faktów.

```text
persisted GhostNetwork event
  -> code-owned event policy
  -> visibility projection
  -> one or more canonical tasks
  -> existing 135.6 pipeline
```

## Bezwzględna bramka heavy profile

Na całej ścieżce obowiązuje:

```text
profile_full_read:           0
profile_full_write:          0
profile_bytes:               0
account_scan:                0
all_user_profile_scan:       0
per_recipient_profile_read:  0
```

Zakazane są:

- `users.profile_json` jako źródło bridge'a;
- `get_profile`, `list_profiles`, `load_profile*` i batch parsing profili;
- odświeżanie operacji, plików, mapy, walleta lub Ghost Exchange;
- pełny profil w tasku, logu, fallbacku, dedupe lub audience resolverze;
- wykorzystanie identity projection jako obiektu do `save_profile()`.

Dozwolone są wyłącznie bounded canonical stores, zdarzenie domenowe,
GhostNetwork snapshots oraz lekki identity/recipient projection store.
Fixture profilu 35 MB pozostaje testem fail-closed.

## Code-owned event policy

Jedna wersjonowana mapa ma rozstrzygać:

```text
event_type
eligible / ignored
significance
priority
narrative_intent
audience scopes
target media
CTA family
aggregation family / cooldown
```

### Allowlista startowa

```text
ghost.part_discovered
ghost.part_contained
ghost.part_revealed
ghost.part_activated
ghost.part_deactivated
ghost.part_defended
ghost.part_recovered
ghost.part_contested
ghost.part_conflict_resolved

ghost.connection_created
ghost.machine_progress_changed
ghost.machine_online
ghost.machine_offline

ghost.cycle_locked
ghost.signal_sent
ghost.version_changed
ghost.stabilization_started
ghost.cycle_activated
```

### Dokładna liczność tasków Etapu I

Poniższa tabela jest kontraktem, a nie przykładem. Dla jednego nowego
persisted eventu oczekujemy dokładnie po jednym tasku dla każdego wymienionego
medium i żadnego innego taska. Wszystkie taski mają `audience_scope=public`.

| Event | Oczekiwane media |
|---|---|
| `ghost.part_discovered` | `blacknet`, `googleplex_news` |
| `ghost.part_contained` | `blacknet` |
| `ghost.part_revealed` | `blacknet` |
| `ghost.part_activated` | `blacknet`, `googleplex_news` |
| `ghost.part_deactivated` | `blacknet` |
| `ghost.part_defended` | `blacknet`, `googleplex_news` |
| `ghost.part_recovered` | `blacknet`, `googleplex_news` |
| `ghost.part_contested` | `blacknet`, `googleplex_news` |
| `ghost.part_conflict_resolved` | `blacknet`, `googleplex_news` |
| `ghost.connection_created` | `blacknet` |
| `ghost.machine_progress_changed` | `blacknet` |
| `ghost.machine_online` | `blacknet`, `googleplex_news`, `cyberner` |
| `ghost.machine_offline` | `blacknet` |
| `ghost.cycle_locked` | `blacknet`, `googleplex_news`, `cyberner` |
| `ghost.signal_sent` | `blacknet`, `googleplex_news`, `cyberner`, `radio` |
| `ghost.version_changed` | `blacknet`, `googleplex_news` |
| `ghost.stabilization_started` | `blacknet` |
| `ghost.cycle_activated` | `blacknet`, `googleplex_news` |

Zmiana tej liczności wymaga jawnej zmiany wersji event policy i testów
policy/outbox/registry. Fakt, że source event ma `audience_scope=system`,
`player`, `owner` albo `clan`, nie zmniejsza liczności publicznych tasków z
tej tabeli; bezpieczeństwo zapewnia publiczna visibility projection.

### Zdarzenia techniczne wykluczone

```text
ghost.part_reserved
ghost.part_reservation_attached
ghost.part_reservation_released
ghost.part_reservation_expired
ghost.part_updated
ghost.part_consumed
ghost.reward_pending
ghost.delta_published
ghost.health_check_completed
ghost.cycle_status_changed
```

Nieznany event jest `ignored/unsupported`, a nie automatycznie publikowany.

## Podział realizacji

### Etap I — public event bridge

1. Wprowadzić jawną, testowaną politykę eventów.
2. Ujednolicić realne nazwy eventów, szczególnie
   `ghost.connection_created` i `ghost.cycle_activated`.
3. Budować publiczny fact przez `GhostVisibilityService` lub równoważną
   bounded projekcję, nigdy z surowego event payloadu.
4. Nadać code-owned `narrative_intent`, `priority`, `content_kind`,
   `selected_source_ref/version` i `narrative_thread_id`.
5. Kierować eligible event do BlackNetu.
6. Kierować wyłącznie `high/critical` do istniejącego slotu
   Googleplex News przez jego CAS/slot state; bez nowego HERO i bez duplikatu.
7. Ustalać canonical CTA w tasku backendowym; podłączenie akcji do
   allowlisty i dispatcherów UI jest zakresem Sprintu 138:
   - ujawniona część: `show_ghostnetwork_part`;
   - ukryta część: `show_ghostnetwork_territory`;
   - zdarzenie sieci/cyklu: `open_ghostnetwork_suite`;
   - transmisja: `open_ghostsignal_archive`;
   - Cyberner: `open_cyberner_channel`.
8. Zachować istniejący canonical claim/retry/dead-letter/publication flow.

Etap I nie robi clan/owner fan-out i nie agreguje zdarzeń. Najpierw ma
udowodnić bezpieczny publiczny transport na rzeczywistych eventach.

### Etap II — audience projection i kontrola szumu

1. Dodać niezależne projekcje `public`, `clan`, `owner/player`.
2. Rozwiązywać clan/owner wyłącznie przez bounded canonical indeksy.
3. Każdy task ma zawierać tylko fakty dozwolone dla jego audience.
4. Dodać `narrative_thread_id`:

   ```text
   ghost-cycle:<cycle_id>
   ghost-part:<public_or_private_projection_id>
   ghost-machine:<cycle_id>:<machine_code>
   ghost-conflict:<conflict_id>
   ghost-signal:<signal_id>
   ```

5. Agregować tylko niskopoziomowe `connection_created` i
   `machine_progress_changed` w krótkim oknie.
6. High/critical nigdy nie czeka na agregat.
7. Dodać cooldown i observability, aby jeden cykl nie zalewał mediów.

## Wstępna significance policy

| Rodzina | Significance | Zachowanie |
|---|---:|---|
| `signal_sent`, `cycle_locked`, `version_changed` | critical | natychmiast, bez agregacji |
| `machine_online`, `part_recovered`, `part_conflict_resolved` | high | BlackNet + eligible GGPL News |
| `part_discovered`, `part_activated`, `part_contested`, `part_defended` | high/normal | zależnie od pierwszego wystąpienia i stanu cyklu |
| `part_contained`, `part_revealed`, `part_deactivated`, `machine_offline` | normal | BlackNet, audience-safe |
| `connection_created`, `machine_progress_changed` | low | cooldown/agregacja w Etapie II |
| event techniczny lub nieznany | ignore | audit counter, brak taska |

Priorytet jest decyzją backendu. Model nie może go zmienić.

## Googleplex News

GhostNetwork nie tworzy nowej sekcji. High/critical event może konkurować o
istniejący `gp-home-world-grid` na tych samych zasadach co inne world signals:

- jeden backend-selected source;
- jeden active medium record w slocie;
- `expected_slot_version` i CAS;
- brak dodatkowego HERO;
- asset wybierany z backendowej allowlisty;
- przegrany task kończy się kontrolowanym `slot_assignment_superseded`.

Nie wolno przepuszczać tego samego eventu równolegle przez
`source_scope=ghostnetwork` i pochodny `blacknet_world` bez wspólnej canonical
tożsamości źródła.

## Fallback

Sprint nie przywraca równoległej deterministic publikacji, która wcześniej
potrafiła dublować narrację Ollamy. Jeżeli fallback zostanie potrzebny dla
critical eventu, może powstać dopiero jako terminalny wariant tej samej
publication identity, po wyczerpaniu modelowego retry. Nigdy jako drugi post.

Decyzja o włączeniu fallbacku następuje po Etapie I na podstawie fizycznego
testu awarii Ollamy.

## Obserwowalność

Bounded status ma pokazywać:

```text
events_seen
events_eligible
events_ignored_by_reason
tasks_by_event_type / audience / medium
aggregation_input / output
deduplicated_tasks
slot_superseded
candidate_rejected
published
profile_full_read / write / bytes
account_scan / per_recipient_profile_read
bridge_latency_ms
```

Log nie zawiera raw payloadu, pełnego fact package ani prywatnej projekcji.

## Testy Etapu I — obowiązkowa macierz po korekcie

Testy dzielą się na trzy warstwy i żadnej nie wolno zastąpić inną:

1. **Policy/component:** syntetyczny event sprawdza allowlistę, projekcję,
   routing, CTA, dedupe i heavy-profile guard.
2. **Producer integration:** realna metoda domenowa zapisuje event, a ten sam
   przepływ tworzy oczekiwane taski w outboxie.
3. **Runtime entrypoint:** faktyczny entrypoint używany przez web/worker
   przechodzi od capture/territory/conflict/cycle/transmission do outboxa.

Minimalna asercja dla każdego allowlisted eventu:

```text
persisted event count = 1
expected outbox identities = dokładnie policy.target_media
task source_event_id = persisted event_id
task audience_scope = public
retry producera/dispatchu nie zwiększa liczby tasków
bridge exception nie zmienia committed gameplay state
eligible_without_task = 0
```

- każdy event z allowlisty ma jawny kontrakt;
- każdy event z allowlisty ma realny producer fixture i osiągalny runtime
  entrypoint albo jest jawnie oznaczony jako blocker wdrożenia;
- realny durable capture effect `applied/discovered` tworzy taski dla dokładnie
  tego samego `source_event_id`;
- cycle creation dowodzi outboxa dla `connection_created` i
  `cycle_activated`, nie tylko obecności policy;
- endgame dowodzi osobno outboxa dla `cycle_locked`, `signal_sent`,
  `version_changed` i `stabilization_started`;
- conflict outcome dowodzi osobno `part_conflict_resolved`, `part_defended` i
  `part_recovered`, również gdy w jednej operacji powstaje kilka eventów;
- każdy event techniczny i nieznany nie tworzy taska;
- `connection_created` działa, nieistniejący alias nie ukrywa regresji;
- publiczna część nie ujawnia `part_id`, `entity_id`, profesji, ability ani
  prywatnego właściciela;
- retry tego samego eventu nie tworzy drugiego taska;
- błąd bridge'a nie cofa mechaniki;
- high/critical może wejść do istniejącego GGPL slotu;
- ten sam source nie publikuje się podwójnie przez dwa source scopes;
- CTA taska jest wyłącznie backendowe i zgodne z widocznością;
- fixture 35 MB daje wszystkie heavy-profile counters równe zero.
- bounded audit recent-event lineage raportuje zero
  `eligible_without_expected_task`; strict mode kończy się błędem, gdy choć
  jeden taki event istnieje poza dopuszczonym grace period.

## Testy Etapu II

- public/clan/owner otrzymują różne projected facts tego samego eventu;
- public nie widzi prywatnego factu z taska clan/owner;
- resolver nie wykonuje per-recipient profile I/O ani skanu kont;
- trzy low events mogą utworzyć jeden agregat;
- high/critical nie jest opóźniany przez agregację;
- thread identity jest stabilne przy retry i kolejnych eventach;
- bounded backpressure nie blokuje gameplay workerów;
- publication pozostaje exactly-once po crashu i lease recovery.

## Walidacja serwerowa

1. Deploy bez czyszczenia canonical tables.
2. Restart procesów `13 14 17 18` tylko jeżeli zmienił się kod danego
   procesu; bez resetowania danych.
3. Wygenerować realne zdarzenia przez produkcyjne entrypointy, nie przez
   ręczne wywołanie `publish_narrative_event()` ani insert taska.
4. Najpierw potwierdzić `persisted event -> expected task(s)` dla każdej
   rodziny, a dopiero potem `task -> candidate -> receipt -> medium`.
5. Potwierdzić, że CTA i payload przeszły bez zmiany do candidate/medium
   record; fizyczny dispatcher UI domyka Sprint 138.
6. Potwierdzić brak podwójnego BlackNet/GGPL wpisu.
7. Wykonać strict narrative cutover audit i heavy-profile audit.
8. Zrobić soak SQLite, mapy, operacji, File Managera, GX i walleta.
9. Strict audit musi zawierać bounded sekcję `ghost_event_lineage` z co
   najmniej: `eligible_events`, `expected_tasks`, `eligible_without_task`,
   `tasks_with_missing_event`, `unexpected_medium`, `wrong_audience` i
   przykładowymi ograniczonymi listami ID.

## Definition of Ready

```text
canonical pipeline 135.6:                 COMPLETE
historical 136 reconciled with code:       DONE
existing foundation tests:                31 / PASS
runtime ingress remediation:               SERVER PASS
eligible-event lineage audit:              SERVER PASS
remaining gaps identified:                 DONE
two-stage implementation boundary:        FROZEN
heavy-profile gate:                       FROZEN
no new queue/worker/publisher:             FROZEN
Etap I remediation:                        COMPLETE
```

## Definition of Done

Sprint 136 jest zakończony, gdy zatwierdzone zdarzenia GhostNetwork tworzą
bezpieczne, deduplikowane i audience-specific publikacje w istniejącym
pipeline, high/critical mogą deterministycznie zasilać istniejący slot
Googleplex News, low events nie zalewają feedu, CTA tasków zachowują
widoczność, a
wszystkie heavy-profile counters pozostają równe zero podczas gameplay soak.
Sama obecność policy, poprawny registry i zielony downstream audit nie
wystarczają: każdy wiersz macierzy osiągalności musi mieć producer-level oraz
runtime-entrypoint E2E, a strict lineage audit musi raportować zero
osieroconych eligible eventów.

## Poza zakresem

- nowy outbox, worker, publisher lub file queue;
- zmiana mechaniki GhostNetwork;
- model wybierający event, audience, priorytet, CTA albo URL;
- model czytający bazę, profil, mapę, operacje, pliki, GX lub wallet;
- nowe sekcje Googleplex News;
- masowy backfill historycznych eventów;
- commit, push, deploy i restart w ramach samego przygotowania sprintu.
