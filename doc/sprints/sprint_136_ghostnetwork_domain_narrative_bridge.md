# Sprint 136 — GhostNetwork Domain Narrative Bridge

Status: `ETAP I IMPLEMENTED LOCALLY — SERVER VALIDATION PENDING`

## Implementacja Etapu I — 2026-09-02

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
- Lokalny baseline rozszerzony z 31 do 35 testów przechodzi. Walidacja
  produkcyjna, strict cutover audit i heavy-profile soak pozostają wymagane
  przed uznaniem Etapu I za potwierdzony produkcyjnie.

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

Obecny kod zapewnia:

- `source_scope=ghostnetwork` w canonical `ghost_narrative_outbox`;
- enqueue po trwałym zdarzeniu domenowym, niezależny od wywołania frontendu;
- idempotentny task i canonical dedupe;
- fail-open narracji: błąd bridge'a nie cofa mechaniki gry;
- publiczny `public_entity_id` zamiast surowego `part_id` w generic fact;
- odrzucenie `internal/system`;
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

## Testy Etapu I

- każdy event z allowlisty ma jawny kontrakt;
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
3. Wygenerować po jednym rzeczywistym zdarzeniu: part, conflict, machine i
   cycle/signal.
4. Prześledzić `source_event_id -> task -> candidate -> receipt -> medium`.
5. Potwierdzić, że CTA i payload przeszły bez zmiany do candidate/medium
   record; fizyczny dispatcher UI domyka Sprint 138.
6. Potwierdzić brak podwójnego BlackNet/GGPL wpisu.
7. Wykonać strict narrative cutover audit i heavy-profile audit.
8. Zrobić soak SQLite, mapy, operacji, File Managera, GX i walleta.

## Definition of Ready

```text
canonical pipeline 135.6:                 COMPLETE
historical 136 reconciled with code:       DONE
existing foundation tests:                31 / PASS
remaining gaps identified:                DONE
two-stage implementation boundary:        FROZEN
heavy-profile gate:                       FROZEN
no new queue/worker/publisher:             FROZEN
Etap I:                                    READY
```

## Definition of Done

Sprint 136 jest zakończony, gdy zatwierdzone zdarzenia GhostNetwork tworzą
bezpieczne, deduplikowane i audience-specific publikacje w istniejącym
pipeline, high/critical mogą deterministycznie zasilać istniejący slot
Googleplex News, low events nie zalewają feedu, CTA tasków zachowują
widoczność, a
wszystkie heavy-profile counters pozostają równe zero podczas gameplay soak.

## Poza zakresem

- nowy outbox, worker, publisher lub file queue;
- zmiana mechaniki GhostNetwork;
- model wybierający event, audience, priorytet, CTA albo URL;
- model czytający bazę, profil, mapę, operacje, pliki, GX lub wallet;
- nowe sekcje Googleplex News;
- masowy backfill historycznych eventów;
- commit, push, deploy i restart w ramach samego przygotowania sprintu.
