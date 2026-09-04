# CHAOS — Autonomous Players
## Opis modułów

**Status:** rekomendowany podział komponentów  
**Cel:** zbudowanie Player Decision Layer bez tworzenia równoległego świata dla AI

---

# 1. Zasada podziału

Nie rekomenduję tworzenia kilkunastu osobnych mikroserwisów.

Poniższe „moduły” są przede wszystkim **granicami odpowiedzialności w kodzie**. Większość może działać wewnątrz istniejącego procesu CHAOS, natomiast modelowe podejmowanie decyzji powinno pozostać w oddzielnym procesie `chaos-ai-player-worker`.

Podział ma wymusić trzy rzeczy:

1. model nie zna więcej niż gracz,
2. model nie może wykonać więcej niż gracz,
3. awaria modelu nie może uszkodzić świata.

---

# 2. M01 — AI Player Registry

## Odpowiedzialność

Łączy normalny profil gracza CHAOS z metadanymi autonomii.

## Przechowuje

- `player_id`,
- status actor type,
- lifecycle AI,
- aktywność autonomii,
- provider binding,
- model policy version.

## Nie robi

- nie przechowuje osobnego walleta,
- nie przechowuje osobnego inventory,
- nie wykonuje akcji,
- nie przechowuje sekretów API w plaintext.

## Zależności

Player/Profile Store, Provider Binding Store.

## Priorytet

**P0 — fundament.**

---

# 3. M02 — AI Lifecycle Manager

## Odpowiedzialność

Kontroluje przejścia:

```text
CREATED
→ STUDENT_OBSERVE
→ STUDENT_SUGGEST
→ STUDENT_SUPERVISED
→ AUTONOMOUS
→ SUSPENDED
```

## Reguły

- lifecycle jest stanem systemowym,
- model nie może sam awansować do AUTONOMOUS,
- każdy stan ogranicza dozwolone klasy tasków i akcji,
- możliwość natychmiastowego globalnego `autonomy kill switch`.

## Nie robi

Nie definiuje osobowości ani strategii AI.

## Priorytet

**P0.**

---

# 4. M03 — Player Observation Builder

## Odpowiedzialność

Buduje canonical snapshot tego, co aktualnie może zaobserwować konkretny profil.

## Wejścia

- player profile,
- map state,
- Target Registry,
- operation state,
- Googleplex,
- Ghost Exchange,
- Cyberner,
- territory state,
- GhostNetwork visibility.

## Wyjście

`PlayerObservationSnapshot`.

Snapshot jest wejściem do Knowledge Resolvera i nie powinien być bezpośrednio traktowany jako interfejs modelu. Bieżącą selekcję uwagi i kontekstu wykonuje `M29 — AI Perception Layer`.

## Nie robi

- nie ocenia strategii,
- nie tworzy fikcyjnych faktów,
- nie zwraca całego database state.

## Priorytet

**P0.**

---

# 5. M04 — Knowledge Resolver

## Odpowiedzialność

Przekształca obserwowalny stan w wiedzę, którą postać naprawdę posiada.

## Pilnuje

- public / clan / owner,
- scan-derived knowledge,
- własności i provenance informacji,
- historii wiedzy,
- hidden state,
- zasady `UNKNOWN > GUESS`.

## Wyjście

Zbiór canonical knowledge facts.

Knowledge Resolver odpowiada na pytanie **co postać może wiedzieć**. Nie odpowiada za to, **co z tej wiedzy powinno być właśnie teraz na pierwszym planie** — to odpowiedzialność `M29 — AI Perception Layer`.

## Integracja

Powinien wykorzystywać zasady i możliwie wspólne komponenty `Shared Semantic Input Layer`.

## Priorytet

**P0.**

---

# 6. M05 — Semantic Fact Packager

## Odpowiedzialność

Buduje model-friendly, bounded semantic package z wiedzy i bieżącego `AIWorldPerceptionFrame`. Nie powinien samodzielnie ustalać focusu ani priorytetu zdarzeń.

## Przykład

```text
f01: Posiadasz 1260 HC.
f02: Target t01 został wcześniej przez ciebie zeskanowany.
f03: Posiadasz narzędzie i01 zdolne wykonać scan tego typu.
```

## Właściwości

- stable schema,
- bounded size,
- lineage do canonical facts,
- brak technicznego dumpa struktur backendu.

## Nie robi

Nie nadaje nowych uprawnień i nie wymyśla wiedzy.

## Priorytet

**P0.**

---

# 7. M06 — Capability Resolver

## Odpowiedzialność

Wylicza, jakie klasy działań są aktualnie dostępne dla gracza na podstawie stanu świata.

## Analizuje

- pozycję,
- ekwipunek,
- poziom,
- środki,
- cooldowny,
- target state,
- klan,
- terytorium,
- lifecycle AI.

## Wyjście

Canonical capability set.

## Ważne

Capability Resolver nie zastępuje finalnej walidacji Game Engine.

## Priorytet

**P0.**

---

# 8. M07 — Action Catalog Builder

## Odpowiedzialność

Z capability set buduje dokładną listę wyborów wystawionych modelowi w konkretnym tasku.

## Przykład

```text
a01 WAIT
a02 MOVE location_ref=l01
a03 SCAN_TARGET target_ref=t01 tool_ref=i01
a04 SEND_CYBERNER_MESSAGE player_ref=p02
```

## Zasady

- każda akcja ma `action_ref`,
- obiekty mają task-local refs,
- model nie podaje arbitrary canonical IDs,
- lista jest immutable dla danego taska.

## Priorytet

**P0.**

---

# 9. M08 — AI Task Engine

## Odpowiedzialność

Tworzy taski tylko wtedy, gdy świat wymaga nowej decyzji.

Task Engine odpowiada za moment utworzenia decyzji. Po triggerze buduje lub pobiera aktualny `AIWorldPerceptionFrame` z M29 i zapisuje jego identyfikator/fingerprint razem z taskiem.

## Źródła triggerów

- world events,
- Cyberner message,
- operation completion,
- travel completion,
- territory alert,
- cooldown expiry,
- intent condition,
- manual supervised request.

## Tworzy

`AIPlayerTask` zawierający:

- snapshot/revision,
- semantic facts,
- pamięć relewantną,
- intent,
- Action Catalog,
- expiry.

## Nie robi

Nie woła modelu bezpośrednio.

## Priorytet

**P0.**

---

# 10. M09 — AI Player Outbox / Inbox Store

## Odpowiedzialność

Zapewnia trwałą, idempotentną granicę między światem a workerem AI.

## Funkcje

- ready queue,
- claim,
- lease,
- heartbeat,
- retry,
- dead-letter,
- crash recovery,
- accepted candidate decision.

## Rekomendacja

Współdzielić implementacyjne prymitywy z workerem narracyjnym, ale użyć osobnych tabel/typów tasków.

## Priorytet

**P0.**

---

# 11. M10 — CHAOS AI Player Worker

## Proces

```text
chaos-ai-player-worker
```

## Odpowiedzialność

- konsumuje task,
- buduje bounded prompt,
- pobiera model policy,
- wywołuje Decision Router,
- zapisuje structured decision,
- raportuje telemetrykę.

## Nie robi

- nie zapisuje gameplay state,
- nie wykonuje domenowych akcji,
- nie posiada shella jako narzędzia modelu,
- nie daje modelowi dowolnego HTTP.

## Priorytet

**P0.**

---

# 12. M11 — Decision Router

## Odpowiedzialność

Wybiera silnik decyzyjny niezależnie od tożsamości AI Playera.

## MVP

```text
provider = ollama_local
model = llama3.1:8b
```

## Później

- OpenAI,
- Claude,
- Gemini,
- Mistral,
- inne modele lokalne.

## Zasada

Zmiana providera nie zmienia profilu, pamięci, majątku ani relacji AI.

## Priorytet

**P0 lokalny**, **P2 zewnętrzni providerzy**.

---

# 13. M12 — Ollama Decision Adapter

## Odpowiedzialność

Utwardzona domenowa adaptacja istniejącego klienta `/api/chat`.

## Kontrakt

- `stream=false`,
- bounded context,
- bounded output,
- structured JSON schema,
- concurrency control,
- timeout,
- telemetryka modelu.

## Współdzielenie

Może używać wspólnego niskopoziomowego klienta Ollama z narracją, ale posiada własny prompt registry i output schema.

## Priorytet

**P0.**

---

# 14. M13 — External Provider Adapters

## Odpowiedzialność

Implementują ten sam kontrakt co Ollama Adapter.

## Warunek wdrożenia

Dopiero po udowodnieniu poprawności systemu na lokalnym modelu.

## Nie robią

Nie posiadają własnych zasad gameplayowych.

## Priorytet

**P2.**

---

# 15. M14 — Credential Vault

## Odpowiedzialność

Bezpiecznie przechowuje sekrety providerów zewnętrznych oddzielone od profilu AI.

## Zasady

- brak plaintext keys w gameplay DB,
- encryption key poza bazą,
- worker otrzymuje tylko sekret potrzebny dla wywołania,
- brak sekretów w taskach, pamięci i logach.

## Priorytet

**P2 — niepotrzebny dla MVP Ollama.**

---

# 16. M15 — Decision Schema & Validator

## Odpowiedzialność

Waliduje odpowiedź modelu przed wejściem do warstwy gameplayowej.

## Sprawdza

- schema version,
- `action_ref`,
- typy argumentów,
- refs istniejące w tasku,
- bounded text,
- niedozwolone pola,
- duplicate/replay status.

## Ważne

Poprawny JSON nie oznacza legalnej akcji. Po tym module nadal obowiązuje State Revision Guard i Domain Action Gateway.

## Priorytet

**P0.**

---

# 17. M16 — State Revision Guard

## Odpowiedzialność

Chroni świat przed wykonaniem decyzji podjętej na nieaktualnym stanie.

## Rezultaty

- `fresh` → wykonanie,
- `stale` → reject + ewentualny re-task,
- `expired` → reject,
- `already_executed` → no-op.

## Priorytet

**P0.**

---

# 18. M17 — Domain Action Gateway

## Odpowiedzialność

Wspólny punkt wejścia dla działań człowieka i AI.

## Wymaganie

Ten komponent musi wykorzystywać istniejące reguły gry, a nie je kopiować.

## Routing

```text
MOVE              → Movement Domain
SCAN / HACK       → Operations Domain
BUY               → Googleplex Domain
TRADE             → Ghost Exchange Domain
MESSAGE           → Cyberner Domain
TERRITORY ACTION  → Territory Domain
GHOST ACTION      → GhostNetwork Domain
```

## Invariant

`source=ai` nie może odblokowywać innej logiki niż `source=human`.

## Priorytet

**P0 — najważniejszy moduł wykonawczy.**

---

# 19. M18 — Intent Manager

## Odpowiedzialność

Przechowuje jawny cel bieżący AI niezależnie od konkretnego modelu.

## Dane

- primary goal,
- krótki plan,
- warunek oczekiwany,
- timestamps,
- status.

## Nie robi

Nie zapisuje chain-of-thought.

## Priorytet

**P1.**

---

# 20. M19 — Memory Store

## Odpowiedzialność

Trwale zapisuje doświadczenia AI jako dane świata postaci.

## Klasy

- WORLD,
- EPISODIC,
- RELATIONSHIP,
- EXPERIENCE,
- STUDENT.

## Każdy rekord powinien mieć

- provenance,
- visibility,
- subject refs,
- timestamp,
- importance,
- source event/task.

## Priorytet

**P1.**

---

# 21. M20 — Memory Resolver

## Odpowiedzialność

Wybiera niewielki relewantny fragment pamięci dla bieżącego taska.

## Zasady

- bounded context,
- brak zwiększania visibility,
- preferowanie canonical faktów nad swobodnym tekstem,
- recency + relevance + importance.

## Priorytet

**P1.**

---

# 22. M21 — Student Experience Recorder

## Odpowiedzialność

W fazie STUDENT zapisuje doświadczenia nauczyciela w formie obserwowalnej przez AI.

## Rejestruje

```text
stan przed
wykonane działanie
wynik
konsekwencje
```

## Nie robi

Nie zapisuje ukrytych powodów człowieka jako faktów, jeśli nie zostały przez niego przekazane AI.

## Priorytet

**P1.**

---

# 23. M22 — Supervision Gateway

## Odpowiedzialność

Obsługuje tryby SUGGEST i SUPERVISED.

## Funkcje

- prezentuje decyzję nauczycielowi,
- accept/reject,
- opcjonalny feedback,
- po accept puszcza normalny Domain Action Gateway,
- zapisuje różnicę między sugestią AI a decyzją człowieka.

## Priorytet

**P1, ale wymagany przed pierwszą autonomią.**

---

# 24. M23 — Cyberner Social Adapter

## Odpowiedzialność

Mapuje normalne zdarzenia komunikatora CHAOS na taski społeczne AI oraz decyzje AI na normalne wiadomości Cybernera.

## Zasady

- brak specjalnego protokołu AI ↔ AI,
- normalna visibility rozmów,
- wiadomość nie jest komendą administracyjną,
- rate limit jak dla świata/gracza.

## Priorytet

**P1.**

---

# 25. M24 — Gameplay Domain Adapters

Nie powinny to być nowe silniki. Są cienkimi adapterami między Action Catalog / Domain Action Gateway a istniejącymi domenami.

## 24.1 Movement Adapter

- move,
- arrival,
- travel state.

**Priorytet: P0/P1 — pierwszy vertical slice.**

## 24.2 Operations Adapter

- scan,
- start operation,
- operation result,
- Operation Feedback → experience.

**Priorytet: P1.**

## 24.3 Googleplex Adapter

- widoczny katalog,
- zakup,
- ekonomiczne konsekwencje.

**Priorytet: P1.**

## 24.4 Ghost Exchange Adapter

- widoczne oferty,
- buy/sell,
- transakcje.

**Priorytet: P1.**

## 24.5 Territory Adapter

- stan własnych/jawnych terytoriów,
- legalne akcje konfliktowe,
- reakcje na atak.

**Priorytet: P2.**

## 24.6 GhostNetwork Adapter

- wyłącznie wiedza dostępna postaci,
- działania dostępne zwykłemu graczowi,
- pełne respektowanie public/clan/owner i hidden state.

**Priorytet: P2 — wdrożyć po pozostałych domenach.**

---

# 26. M25 — Decision Scheduler / Fairness

## Odpowiedzialność

Kontroluje częstotliwość decyzji i kolejkę wielu AI.

## MVP

- jeden AI,
- concurrency 1,
- jeden outstanding task,
- event-driven scheduling,
- minimalne cooldowny.

## Później

- fair queue,
- priority classes,
- per-provider budgets,
- anti-loop detection.

## Priorytet

**P0 minimalny, P2 skalowanie.**

---

# 27. M26 — Telemetry & Audit

## Odpowiedzialność

Zapewnia pełną obserwowalność bez zapisywania prywatnego chain-of-thought.

## Mierzy

- task rate,
- decision latency,
- retry,
- fallback,
- stale rate,
- invalid schema rate,
- rejected action rate,
- execution success,
- provider/model usage,
- token usage,
- autonomous actions per player.

## Priorytet

**P0.**

---

# 28. M27 — Safety / Autonomy Controls

## Odpowiedzialność

Operacyjne zatrzymanie autonomii bez wyłączania świata.

## Kontrole

- global autonomy enable,
- per-player autonomy enable,
- per-domain enable,
- dry-run mode,
- supervised-only mode,
- max decisions/hour,
- max economic exposure,
- emergency suspend.

## Priorytet

**P0.**

---

# 29. M28 — Diagnostics / Replay Tools

## Odpowiedzialność

Pozwala odtworzyć, dlaczego AI dostało konkretny task i co się z nim stało.

## Tryby

```text
status
inspect-task
inspect-decision
dry-run
replay-validation
verify-provider
```

Replay nie może ponownie wykonywać gameplayowych side effects.

## Priorytet

**P0/P1.**

---

# 30. M29 — AI Perception Layer / AI World Interface

## Odpowiedzialność

Buduje canonical, bounded i wersjonowany **ekran rzeczywistości** konkretnego AI Playera dla konkretnego taska.

Nie odpowiada za to, co istnieje w świecie ani co postać legalnie wie. Te granice pozostają odpowiednio w World/Observation i Knowledge Layer.

M29 odpowiada za pytanie:

> **Co z legalnie dostępnej wiedzy, zdarzeń i możliwości jest właśnie teraz przedstawione postaci jako jej bieżąca sytuacja?**

## Główne sekcje frame'u

```text
NOW
ATTENTION
FOCUS
ACTIVE
BACKGROUND
RECENT
RESOURCES
RELATIONSHIPS
KNOWN_WORLD
CAPABILITIES
AVAILABLE_ACTIONS
```

## Łączy

- M03 Player Observation Builder,
- M04 Knowledge Resolver,
- M06 Capability Resolver,
- M07 Action Catalog,
- M18 Intent Manager,
- M20 Memory Resolver,
- world events,
- runtime focus state.

## Wyjście

`AIWorldPerceptionFrame` z własnym `perception_id` / fingerprintem i lineage do canonical źródeł.

## Kluczowe reguły

- percepcja nie może tworzyć nowych faktów,
- zmiana focusu nie może rozszerzać wiedzy,
- attention policy jest deterministyczna i testowalna,
- krytyczne sygnały nie mogą zniknąć przez przypadkowe obcięcie kontekstu,
- frame jest bounded,
- ten sam canonical input powinien dawać semantycznie ten sam frame,
- worker dostaje frame jako kontrakt, a nie samodzielnie skleja kontekst świata.

## Przykład

```text
NOW
activity: territory_build — Alaska

ATTENTION
territory_attack — Warszawa — HIGH
cyberner_message — RUN — MEDIUM

FOCUS
Alaska

AVAILABLE_ACTIONS
a01 CONTINUE_CURRENT_ACTIVITY
a02 INSPECT_TERRITORY territory_ref=tr02
a03 CHANGE_FOCUS focus_ref=territory_warsaw
a04 TELEPORT destination_ref=loc02
a05 OPEN_CYBERNER_THREAD thread_ref=c01
a06 WAIT
```

M29 nie wybiera za AI, czy Warszawa jest ważniejsza od Alaski. Przedstawia oba sygnały i ich canonical wagę interfejsową, a decyzję podejmuje model.

## Diagnostyka

M29 powinien wspierać:

```text
inspect-perception
rebuild-perception
compare-perception
replay-decision
```

Replay nie może wykonywać gameplayowych side effects.

## Priorytet

**P0 — krytyczny przed oceną jakości pierwszego autonomicznego AI Playera.**

---

# 31. Rekomendowany fizyczny podział kodu

Przykładowo:

```text
chaos/
  ai_players/
    registry.py
    lifecycle.py
    observation.py
    knowledge.py
    perception.py
    attention.py
    focus.py
    semantic_facts.py
    capabilities.py
    action_catalog.py
    task_engine.py
    tasks_store.py
    decisions.py
    validation.py
    revision_guard.py
    action_gateway.py
    intent.py
    memory.py
    supervision.py
    telemetry.py
    controls.py
    domains/
      movement.py
      operations.py
      cyberner.py
      googleplex.py
      ghost_exchange.py
      territory.py
      ghostnetwork.py

  llm/
    ollama_client.py
    model_policy.py
    provider_contract.py

workers/
  ai_player_worker.py
```

To tylko rekomendowana granica logiczna; nazwy powinny zostać dopasowane do faktycznej struktury repo po audycie.

---

# 32. Minimalny zestaw MVP

Do pierwszego prawdziwego vertical slice potrzebne są tylko:

```text
M01 Registry
M02 Lifecycle
M03 Observation
M04 Knowledge
M05 Semantic Facts
M06 Capability Resolver
M07 Action Catalog
M29 AI Perception Layer
M08 Task Engine
M09 Outbox/Inbox
M10 Worker
M11 Decision Router
M12 Ollama Adapter
M15 Decision Validator
M16 Revision Guard
M17 Domain Action Gateway
M26 Telemetry
M27 Controls
```

Memory, pełny Student, providerzy zewnętrzni, terytoria i GhostNetwork mogą wejść później.

---

# 33. Najważniejsze granice odpowiedzialności

### Świat mówi modelowi, co jest prawdą.

Observation + Knowledge.

### Perception mówi modelowi, co jest teraz na jego „ekranie”.

AI Perception Layer + Semantic Facts + Attention + Focus.

### Świat mówi modelowi, co może wybrać.

Capability Resolver + Action Catalog.

### Model tylko wybiera.

Worker + Decision Router.

### Świat ponownie sprawdza decyzję.

Decision Validator + Revision Guard + Domain Action Gateway.

### Świat zapamiętuje konsekwencje.

Events + Memory + Telemetry.

Taki podział jest najbezpieczniejszy i najlepiej pasuje do obecnej architektury CHAOS.
