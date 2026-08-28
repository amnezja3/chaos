# Sprint 135.3 — LLM Event Producers and Googleplex App Ingress

Status: `SPRINT 135.3 — READY FOR SERVER VALIDATION`.

## Cel

Podłączyć zatwierdzone źródła zdarzeń do canonical task transportu oraz dodać
kontrolowane wejście z dedykowanej aplikacji instalowanej przez Googleplex.
Sprint nadal nie uruchamia Ollamy, nie tworzy Inboxu i nie publikuje treści
modelu.

## Warunek wejścia

Sprint może rozpocząć się dopiero po potwierdzeniu invariants 135.2:

```text
one canonical queue
exactly one semantic task
exactly one active lease
crash recovery without loss or duplication
```

Producer nie może implementować własnej kolejki, retry ani pliku pośredniego.

## Source of truth

Fakty pozostają własnością domen, które je wytworzyły:

- GhostNetwork: canonical events, cycle, signal i immutable lock snapshot;
- BlackNet: `blacknet_world_facts` oraz deterministyczne world signals;
- aplikacja Googleplex: canonical installation entitlement, action receipt i
  backend-resolved facts;
- audience: istniejące visibility/identity/clan projections.

Outbox przechowuje task transportowy, ale nie staje się source of truth stanu
gry.

## Docelowy call chain

```text
canonical domain event / scheduled world digest / installed app action
→ source-specific fact projector
→ audience projection
→ allowed action + truth policy builder
→ canonical enqueue_task()
→ accepted task receipt
```

Request kończy się po idempotentnym enqueue. Nie czeka na model ani publikację.

## Producer GhostNetwork i GhostSignal

Zakres obejmuje wyłącznie jawnie dozwolone rodziny zdarzeń, między innymi:

- część odkryta, otoczona, aktywowana, utracona lub w konflikcie;
- połączenie ukończone;
- maszyna online;
- cykl zamknięty;
- GhostSignal wysłany;
- zatwierdzony outcome/confirmation z 2108, jeżeli backend już go zapisał.

Każdy producer:

- czyta canonical event zamiast inferować transition z renderowanego state;
- używa `source_scope=ghostnetwork`;
- zachowuje `source_event_id`, state/canon/GhostSystem version;
- buduje osobny task per audience i `target_medium`;
- nie wysyła ukrytych części, topology ani owner-only facts do public audience;
- nie cofa gameplayu, gdy enqueue narracji się nie powiedzie;
- nie emituje taska dla snapshotu, redraw, recovery albo replayu bez nowego
  canonical eventu.

## Producer BlackNet world facts

Istniejący deterministic snapshot pozostaje bazą:

```text
blacknet_world_facts
→ blacknet_world_signals
→ bounded narrative task
```

Producer:

- używa `source_scope=blacknet_world`;
- generuje stabilny `source_receipt_id` dla okna/digestu;
- nie skanuje pełnych profili;
- nie tworzy dwóch tasków po ponownym scheduler tick;
- wskazuje `target_medium=blacknet` lub inny jawnie zatwierdzony sink;
- pozostawia sygnały deterministyczne dostępne bez Ollamy.

Legacy file export jest wywoływany z canonical taska zgodnie ze Sprintem 135.2,
a nie bezpośrednio z producenta.

## Dedykowana aplikacja Googleplex

Powstaje kontrakt produktu/aplikacji, ale nie generowany tekst.

### Instalacja i entitlement

- aplikacja jest zwykłym canonical produktem Googleplex;
- uprawnienie pochodzi z bounded `PlayerInventoryStore`/app registry;
- brak instalacji lub aplikacja odwołana → fail-closed i zero tasków;
- endpoint nie czyta ani nie zapisuje pełnego profilu;
- uninstall natychmiast blokuje nowe akcje, ale nie kasuje audit history.

### Request contract

Aplikacja może przesłać wyłącznie:

```text
app_action_id / client_receipt_id
approved_template_id
bounded user input fields przewidziane przez template
optional opaque context reference
```

Nie może przesłać:

- system promptu;
- nazwy/modelu Ollamy;
- surowych faktów świata;
- dowolnej audience;
- zewnętrznego URL;
- arbitralnego CTA;
- gameplay mutation;
- bezpośredniego `target_medium` poza allowlistą produktu.

Backend rozwiązuje template, fakty, audience i CTA. Domyślnym wynikiem jest
owner-scoped task dla `cyberner` (surface AGI-2108). Publiczna publikacja wymaga osobnego,
zatwierdzonego template/policy.

### Session, CAS i idempotency

```text
active session-generation precheck
→ bounded entitlement check
→ validate/rate-limit
→ canonical action receipt
→ session-generation precommit check
→ enqueue task
```

- stara/replaced sesja nie może utworzyć taska;
- retry tego samego `client_receipt_id` zwraca ten sam task/receipt;
- równoległe requesty nie pobierają kosztu i nie tworzą taska dwa razy;
- jeśli aplikacja ma koszt użycia, settlement jest atomowy z receipt albo
  projektowany jako osobny canonical ledger contract, nigdy jako profile write;
- response zwraca `accepted`, `task_id`, `receipt_id` i status asynchroniczny,
  ale nie udaje gotowej odpowiedzi modelu.

## Audience projection

Projection następuje przed enqueue. Jeden task reprezentuje dokładnie jedną
audience:

```text
public
clan:<clan_id>
owner:<user_id>
```

Producer nie może przygotować „pełnego” taska i liczyć, że worker usunie sekrety.
Zmiana relacji po enqueue nie zwiększa widoczności taska; publisher w 135.5
wykona dodatkowy fail-closed prepublish guard dla wrażliwych audience.

## Telemetria

Wymagany correlation chain:

```text
source_event_id/source_receipt_id
→ task_id
→ source_scope
→ audience/target_medium
→ enqueue result: created | deduplicated | rejected
```

Log jest bounded i nie zawiera pełnego promptu ani profilu.

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

### GhostNetwork

- jeden canonical transition → jeden task per audience/medium;
- rebuild/snapshot/recovery bez transition → zero nowych tasków;
- replay tego samego eventu → ten sam task;
- public task nie zawiera hidden part/topology;
- GhostSignal task odwołuje się do immutable lock snapshot i canonical outcome.

### BlackNet

- ten sam digest window uruchomiony dwa razy → jeden task;
- brak Ollamy → deterministic feed nadal działa;
- 35 MB profile fixture → zero full-profile access;
- legacy diagnostic file pochodzi z taska, nie z równoległego flow.

### Googleplex app

- zainstalowana aplikacja + ważna sesja → jeden accepted receipt/task;
- brak instalacji → controlled rejection i zero tasków;
- replaced session przed requestem → zero tasków;
- session zmieniona między precheck i commit → zero tasków;
- dwa równoległe requesty z tym samym receipt → jeden task;
- nieznany template/dowolny prompt/audience/CTA → reject;
- owner-private task nie pojawia się w publicznym zakresie;
- uninstall → następna akcja zablokowana;
- 35 MB profile → zero full read/write/bytes.

## Walidacja

- testy producerów GN/GhostSignal;
- testy BlackNet world facts/signals;
- testy Googleplex install/inventory/uninstall/session generation;
- testy audience visibility i hidden topology;
- testy outbox dedupe/concurrency ze Sprintu 135.2;
- `py_compile`;
- `git diff --check`.

## Poza zakresem

- klient lub proces Ollamy;
- canonical Inbox;
- walidacja realnego outputu modelu;
- publikacja do UI;
- nowy feed Googleplex News;
- synchroniczne oczekiwanie na LLM;
- deploy, restart PM2 i produkcyjne mutacje.

## Exit gate

`ALL APPROVED SOURCES → SAFE CANONICAL TASKS / STILL NO OLLAMA`

Po spełnieniu bramki: `SPRINT 135.3 — READY FOR SERVER VALIDATION`, a po
potwierdzeniu `READY FOR SPRINT 135.4`.

## Wynik implementacji — 2026-08-28

- canonical lifecycle events GhostNetwork/GhostSignal tworzą task po
  projekcji audience; eventy `internal/system` oraz rebuild bez transition
  tworzą zero tasków;
- publiczny task używa opaque `public_entity_id` i nie eksportuje wewnętrznego
  `part_id`, nazw części ani hidden topology;
- bounded BlackNet world digest jest tworzony z publicznych canonical stores,
  ma stabilny receipt okna i nie zależy od działania Ollamy;
- worker jedynie okresowo enqueue'uje digest; nie claimuje tasków i nie
  wykonuje żadnego połączenia z LLM;
- Googleplex ingress wymaga canonical installation entitlement, zatwierdzonego
  template i owner audience; dowolny prompt, model, medium, CTA, URL i pola
  spoza kontraktu są odrzucane;
- entitlement jest sprawdzany ponownie w tej samej transakcji przed enqueue,
  quota jest atomowa, a równoległy replay tego samego receipt tworzy jeden task;
- endpoint statusu receipt jest owner-scoped i nie ujawnia facts, validation
  ani informacji o lease;
- fixture profilu 35 MB potwierdza zero `get_profile()`/`list_profiles()` w
  nowych ścieżkach.

Walidacja lokalna: testy producentów i ingressu, canonical outbox,
GhostNetwork lifecycle/bridge/visibility, BlackNet signals,
session-generation precommit oraz Googleplex install/uninstall przeszły.
`py_compile` i `git diff --check` są wymagane w finalnej bramce zmiany.

Nadal poza zakresem pozostają: klient Ollamy, worker LLM, Inbox, publikacja
wyników, produkt/UI aplikacji Googleplex oraz deploy/restart PM2.

