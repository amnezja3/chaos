# CHAOS — Autonomous Players
## Rekomendacja zakresu sprintów

**Proponowana seria:** `1XX.x — Autonomous Players`  
**Założenie:** poprzednia seria domyka istniejący pipeline narracyjny; 1XX.x buduje osobny Player Decision Layer.  
**Strategia:** najpierw udowodnić równość świata i jeden bezpieczny vertical slice, dopiero później rozwijać autonomię.

---

# 1. Zasada prowadzenia serii 1XX.x

Nie zaczynamy od „podłączenia AI do całej gry”.

Budujemy kolejne dowody:

```text
PARITY
→ VISIBILITY
→ LEGAL ACTIONS
→ DRY-RUN DECISION
→ SUPERVISED ACTION
→ LIMITED AUTONOMY
→ MEMORY / INTENT
→ ECONOMY / OPERATIONS
→ TERRITORY / GHOSTNETWORK
→ MULTI-AI / EXTERNAL PROVIDERS
```

Każdy sprint powinien kończyć się mierzalnym gate'em GO / NO-GO.

---

# 2. Sprint 1XX.0 — Architecture Audit & Domain Parity Map

## Cel

Nie pisać jeszcze AI Playera. Najpierw znaleźć prawdziwe punkty wejścia do gameplayu i miejsca, gdzie endpointy UI zawierają reguły, których AI nie mogłoby bezpiecznie współdzielić.

## Zakres

Audyt domen:

- profile,
- movement,
- map visibility,
- Target Registry,
- operations,
- Googleplex,
- Ghost Exchange,
- Cyberner,
- territory/conflicts,
- GhostNetwork.

Dla każdej domeny stworzyć mapę:

```text
UI endpoint
→ auth
→ validation
→ domain logic
→ persistence
→ events
```

Wskazać:

- logikę domenową już współdzielną,
- logikę zaszytą w handlerach HTTP,
- heavy-profile paths,
- side effects,
- revision/version mechanisms,
- możliwości idempotency/replay.

## Artefakt sprintu

`SPRINT_1XX_0_AI_PLAYER_DOMAIN_PARITY_AUDIT.md`

## GO

Mamy kompletną mapę ścieżek, które musi wykorzystywać zarówno human, jak i AI.

## NO-GO

Jeżeli któraś krytyczna domena nie ma możliwej do wyodrębnienia canonical command path.

---

# 3. Sprint 1XX.1 — Shared Domain Action Gateway

## Cel

Zbudować wspólną ścieżkę wykonania akcji zanim pojawi się jakikolwiek model.

## Zakres

- `Domain Action Gateway`,
- actor context `human | ai` tylko do audytu,
- routing do istniejących domen,
- action result contract,
- idempotency key,
- expected revision / stale protection foundations,
- parity tests.

Na tym etapie AI jeszcze nie istnieje jako autonomiczny worker.

Testujemy sztuczne komendy wygenerowane przez testy.

## Pierwszy zakres domenowy

Tylko bezpieczne minimum:

- WAIT/no-op,
- MOVE,
- jeden prosty SCAN / operation entry point, jeśli audyt potwierdzi wspólną ścieżkę.

## Test kluczowy

Dla tego samego profilu i stanu:

```text
human action
AI-labelled action
```

muszą przechodzić przez te same walidatory i powodować równoważny rezultat.

## GO

Brak specjalnej ścieżki gameplayowej dla AI.

---

# 4. Sprint 1XX.2 — Player Observation & Knowledge Boundary

## Cel

Udowodnić, że system potrafi zbudować dokładnie taki obraz świata, jaki posiada konkretny gracz.

## Zakres

- `Player Observation Builder`,
- `Knowledge Resolver`,
- reuse/extension Shared Semantic Input Layer,
- provenance,
- public/clan/owner,
- scan knowledge,
- hidden state protection,
- bounded semantic facts.

## Testy bezpieczeństwa

- cudzy private fact nie przechodzi,
- hidden GhostNetwork state nie przechodzi,
- nieznany target detail nie przechodzi,
- znany przez scan detail przechodzi,
- owner/clan/public działają zgodnie z kontraktem,
- `UNKNOWN > GUESS`.

## GO

Nie ma ścieżki, przez którą AI dostaje szerszą wiedzę niż równoważny human player.

---

# 5. Sprint 1XX.3 — Capability Resolver & Action Catalog

## Cel

Backend ma sam wystawiać modelowi ograniczony zestaw dostępnych wyborów.

## Zakres

- capability resolver,
- action schema registry,
- task-local refs,
- Action Catalog,
- parametry akcji,
- invalid ref rejection,
- catalog versioning.

## Początkowe action types

```text
WAIT
MOVE
SCAN_TARGET
```

Opcjonalnie `SEND_CYBERNER_MESSAGE`, jeśli social adapter jest już łatwy do odseparowania.

## GO

Model nie musiałby znać endpointów ani canonical IDs, żeby legalnie wybrać akcję.

---

# 6. Sprint 1XX.4 — AI Task Engine & Durable Decision Pipeline

## Cel

Zbudować pełny pipeline taska bez uruchamiania modelu.

## Zakres

- event-driven Task Engine,
- `ai_player_tasks`,
- osobny outbox/inbox,
- claim/lease/heartbeat,
- retry,
- dead-letter,
- expiry,
- dedupe,
- crash recovery,
- revision snapshot,
- telemetryka.

## Tryby diagnostyczne

```text
status
inspect-task
dry-run
replay-validation
```

## Ważne

`dry-run` kończy się przed providerem.

## GO

Możemy deterministycznie wyprodukować i odtworzyć task, a replay nie powoduje side effects.

---

# 7. Sprint 1XX.5 — Local Ollama Decision Worker, No Execution

## Cel

Połączyć Decision Task z istniejącym lokalnym Ollama bez możliwości zmiany świata.

## Zakres

- `chaos-ai-player-worker`,
- Decision Router v1,
- Ollama adapter,
- code-owned prompt registry,
- structured decision schema,
- bounded context,
- bounded output,
- concurrency 1,
- telemetryka modelu,
- candidate decision inbox.

## Model

Na start istniejący lokalny:

```text
llama3.1:8b
```

## Publication / execution

**OFF.**

Worker tylko generuje candidate decisions.

## Testy

- nieistniejący action_ref → reject,
- malformed output → reject,
- timeout → retry,
- worker crash → lease recovery,
- duplicate → no duplicate candidate,
- zero gameplay mutation.

## GO

Model potrafi stabilnie wybierać spośród Action Catalogu, a jego błędy są bezpieczne.

---

# 8. Sprint 1XX.6 — STUDENT: Observe & Suggest

## Cel

Pierwsze prawdziwe AI Player konto, nadal bez samodzielnego wykonywania działań.

## Zakres

- AI Player Registry,
- lifecycle CREATED / STUDENT_OBSERVE / STUDENT_SUGGEST,
- jedno testowe konto AI,
- obserwacja działań nauczyciela,
- Student Experience Recorder,
- sugestie AI,
- UI/admin diagnostics do porównania sugestii z faktyczną decyzją człowieka.

## Mierzymy

- zgodność sugestii z dostępnymi akcjami,
- invalid decision rate,
- częstotliwość stale decisions,
- latency,
- sensowność wyborów manualnie.

## GO

AI przez istotną serię tasków nie narusza kontraktu i potrafi podejmować użyteczne decyzje w ograniczonym zakresie.

---

# 9. Sprint 1XX.7 — STUDENT Supervised Execution

## Cel

Po raz pierwszy decyzja modelu może spowodować gameplayowy side effect, ale wyłącznie po akceptacji człowieka.

## Zakres

- lifecycle `STUDENT_SUPERVISED`,
- Supervision Gateway,
- accept / reject,
- optional feedback,
- State Revision Guard,
- Domain Action Gateway execution,
- full audit trail.

## Początkowe akcje wykonawcze

```text
WAIT
MOVE
SCAN_TARGET
```

Nie włączać jeszcze:

- zakupów,
- sprzedaży,
- konfliktów,
- GhostNetwork.

## GO

Zaakceptowana decyzja przechodzi dokładnie tę samą ścieżkę co akcja człowieka i jest idempotentna.

---

# 10. Sprint 1XX.8 — Limited Autonomous Vertical Slice

## Cel

Pierwsza autonomia bez kliknięcia człowieka.

## Ograniczenia

- 1 AI Player,
- local Ollama,
- concurrency 1,
- tylko wybrane action types,
- decision cooldown,
- max actions/hour,
- global kill switch,
- per-player kill switch,
- zero external providers.

## Zakres akcji

```text
WAIT
MOVE
SCAN_TARGET
```

Opcjonalnie Cyberner response, jeżeli komunikacja została wystarczająco przetestowana.

## Warunki GO

- zero unauthorized actions,
- zero duplicate side effects,
- zero hidden knowledge leaks,
- stale decisions fail closed,
- worker/provider failure nie zmienia świata,
- wszystkie decyzje mają audit trail.

To jest najważniejszy gate całej serii.

---

# 11. Sprint 1XX.9 — Intent & Memory v1

## Cel

Dać AI ciągłość zachowania między pojedynczymi taskami bez przesyłania całej historii.

## Zakres

- Intent Manager,
- Memory Store,
- Memory Resolver,
- provenance,
- visibility-preserving memory,
- WORLD / EPISODIC / EXPERIENCE,
- bounded retrieval,
- memory creation z konsekwencji akcji.

## Bez vector DB jako wymagania

Na start rekomendowany prosty canonical store + indeksy/metadata. Vector retrieval można dodać dopiero, jeśli realny corpus pokaże potrzebę.

## GO

AI potrafi utrzymać prosty plan przez wiele tasków bez zwiększania swojej visibility.

---

# 12. Sprint 1XX.10 — Cyberner & Relationship Layer

## Cel

Włączyć AI do społecznego świata CHAOS.

## Zakres

- Cyberner inbound → social task,
- AI response → normalna wiadomość Cybernera,
- task-local player refs,
- relationship memory,
- rate limits,
- player-to-AI,
- AI-to-player,
- AI-to-AI przez ten sam komunikator.

## Zasada

Wiadomość nie jest poleceniem systemowym.

## GO

AI może negocjować i odmawiać, a AI ↔ AI nie posiada żadnego specjalnego kanału bocznego.

---

# 13. Sprint 1XX.11 — Economy: Googleplex & Ghost Exchange

## Cel

Pierwsze autonomiczne decyzje ekonomiczne.

## Zakres

- widoczny katalog Googleplex,
- BUY_ITEM action,
- Ghost Exchange visible offers,
- buy/sell actions,
- economic guardrails,
- budget exposure telemetry,
- intent/memory consequences.

## Początkowy guardrail

Per-AI limit wartości autonomicznych transakcji na okres testowy, jako kontrola rolloutowa — nie jako mechanika gameplayowa dająca bonus AI.

## GO

AI używa dokładnie tej samej ekonomii i tych samych cen co człowiek.

---

# 14. Sprint 1XX.12 — Operations Expansion & Operation Feedback Learning

## Cel

Rozszerzyć autonomię z prostego SCAN na istniejący system operacji.

## Zakres

- więcej operation action types,
- dobór narzędzi,
- operation preconditions,
- feedback → semantic experience,
- rejection learning,
- risk consequences.

## Ważne

Nie przekazujemy AI ukrytych kluczy zabezpieczeń ani technicznych shortcutów. Uczy się na wyniku tak, jak gracz uczy się z UI/feedbacku.

## GO

AI potrafi przechodzić co najmniej jeden pełny rzeczywisty flow operacji bez specjalnych reguł.

---

# 15. Sprint 1XX.13 — Territory & Conflict Autonomy

## Cel

Włączyć strategiczne konsekwencje na mapie.

## Zakres

- territory observation,
- własne/jawne konflikty,
- response tasks,
- legal territory actions,
- intent strategiczny,
- stale protection dla szybko zmieniających się konfliktów,
- ograniczenia częstotliwości decyzji.

## GO

AI może uczestniczyć w konflikcie bez dostępu do ukrytej topologii i bez innej mechaniki niż człowiek.

---

# 16. Sprint 1XX.14 — GhostNetwork Player Integration

## Cel

Dopiero po ustabilizowaniu reszty świata dopuścić AI do GhostNetwork jako normalnego gracza.

## Zakres

- public/clan/owner semantic facts,
- discovered/contained/active knowledge boundaries,
- część jako zasób gracza,
- legal GhostNetwork actions,
- event-driven reactions,
- pełne lineage semantic facts,
- testy hidden-state leakage.

## Szczególne NO-GO

Jakikolwiek przypadek, w którym AI poznaje canonical hidden state niedostępny równoważnemu graczowi.

---

# 17. Sprint 1XX.15 — External Providers & Credential Vault

## Cel

Dopiero teraz uniezależnić mózg AI od lokalnej Ollamy.

## Zakres

- provider contract stabilizacja,
- Credential Vault,
- encrypted provider bindings,
- OpenAI/Claude/Gemini/Mistral według potrzeb,
- fallback policy,
- provider health,
- per-provider budgets,
- model switch bez zmiany AI identity.

## Test kluczowy

Ten sam saved AI Player działa po przełączeniu modelu bez utraty pamięci, konta, intentu i świata.

---

# 18. Sprint 1XX.16 — Multi-AI Scheduling & Fairness

## Cel

Przejście z eksperymentu jednego mieszkańca do populacji.

## Zakres

- wielu AI Playerów,
- fair scheduler,
- provider concurrency,
- task priorities,
- anti-loop,
- rate limits,
- observability per player,
- global capacity controls.

## GO

Wzrost liczby AI nie pogarsza normalnego gameplayu human players i nie destabilizuje workerów.

---

# 19. Sprint 1XX.17 — AI Teaching & Cultural Transmission

## Cel

Dopiero po dojrzałości autonomii wdrożyć najbardziej eksperymentalną część koncepcji: AI uczące kolejne AI.

## Zakres

- AI jako teacher source,
- przekazywanie doświadczeń zamiast prompt-personality clone,
- provenance pokoleń,
- selective inheritance,
- brak automatycznego kopiowania intentów/relacji,
- obserwacja emergentnych zachowań.

## Status

**Eksperymentalny / opcjonalny.** Nie jest potrzebny do pierwszej wersji Autonomous Players.

---

# 20. Rekomendowany podział na releasy

## Release A — Proof of Equality

Sprinty:

```text
1XX.0–1XX.5
```

Rezultat:

- wspólna warstwa akcji,
- poprawna visibility,
- Action Catalog,
- durable task pipeline,
- lokalny model generuje decyzje,
- brak side effects.

To jest techniczny fundament.

---

## Release B — First Living AI

Sprinty:

```text
1XX.6–1XX.10
```

Rezultat:

- prawdziwy AI Player,
- Student,
- supervised execution,
- ograniczona autonomia,
- pamięć/intencja,
- Cyberner.

To jest pierwsza wersja, którą można realnie nazwać mieszkańcem CHAOS.

---

## Release C — Full Player Participation

Sprinty:

```text
1XX.11–1XX.14
```

Rezultat:

- ekonomia,
- pełniejsze operacje,
- terytoria,
- GhostNetwork.

AI zaczyna uczestniczyć w praktycznie całym gameplayu.

---

## Release D — Open Intelligence Ecosystem

Sprinty:

```text
1XX.15–1XX.17
```

Rezultat:

- zewnętrzne modele,
- wielu AI,
- AI → AI teaching,
- możliwość powstawania kultury CHAOS.

---

# 21. Co można scalać

Jeżeli audyt pokaże małą ilość pracy, można łączyć:

- `1XX.2 + 1XX.3` — knowledge + action catalog,
- `1XX.4 + 1XX.5` — task pipeline + local worker,
- `1XX.6 + 1XX.7` — Student suggest + supervised,
- `1XX.9 + 1XX.10` — memory + Cyberner.

Nie rekomenduję łączenia:

- `1XX.1` z LLM,
- `1XX.8` z ekonomią,
- terytoriów z GhostNetwork,
- external providers z pierwszą autonomią.

Te granice są ważnymi punktami bezpieczeństwa i diagnostyki.

---

# 22. Minimalny zakres, jeśli chcemy szybko sprawdzić pomysł

Jeżeli celem jest szybki eksperyment bez pełnej serii, absolutne minimum to:

```text
1XX.0 Audit
1XX.1 Action Gateway
1XX.2 Knowledge + Semantic Facts
1XX.3 Action Catalog
1XX.4 Durable Task Pipeline
1XX.5 Ollama Dry Decision
1XX.6 Student Suggest
1XX.7 Supervised Execution
1XX.8 Limited Autonomous Slice
```

Po `1XX.8` podejmujemy decyzję, czy system rzeczywiście daje oczekiwaną jakość i czy warto inwestować w resztę.

To jest rekomendowany **pierwszy milestone projektu**.

---

# 23. Najważniejsze test gates całej serii

Przed każdym rozszerzeniem autonomii muszą być zielone:

### Visibility gate

AI nie wie więcej niż human player.

### Capability gate

AI nie może wybrać czegoś, czego backend mu nie wystawił.

### Execution parity gate

Human i AI trafiają do tych samych reguł domenowych.

### Stale-state gate

Decyzja wygenerowana na starym stanie nie wykonuje się.

### Idempotency gate

Retry/replay nie tworzy drugiego side effectu.

### Failure gate

Awaria providera lub workera nie zmienia świata.

### Audit gate

Każdy autonomiczny side effect można przypisać do taska, decyzji i canonical stanu wejściowego.

---

# 24. Rekomendowana decyzja startowa

Nie zaczynałbym od budowania pamięci, Cybernera, Vaulta ani wieloagentowości.

Pierwsze zadanie dla Codexa powinno być:

> **Sprint 1XX.0 — przeprowadź audyt istniejących domen gameplayowych i wyznacz wspólny Domain Action Gateway, którego mogą używać zarówno gracze ludzcy, jak i przyszły AI Player, bez implementacji LLM i bez zmian gameplayowych.**

To da nam prawdziwą odpowiedź, ile z projektu już istnieje oraz gdzie są miejsca wymagające refaktoru przed dołożeniem autonomii.
