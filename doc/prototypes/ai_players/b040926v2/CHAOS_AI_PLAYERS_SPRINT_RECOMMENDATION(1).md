# CHAOS — Autonomous Players
## Rekomendacja zakresu sprintów 2.0

**Proponowana seria:** `139.x — Autonomous Players`  
**Status:** rekomendowany plan realizacji  
**Data:** 2026-09-04  
**Założenie:** istniejący CHAOS jest systemem źródłowym; seria 139.x nie tworzy drugiej gry, tylko drugi, semantyczny klient oraz osobny worker decyzyjny.

---

# 1. Strategia realizacji

Nie zaczynamy od podłączenia modelu do całego CHAOS.

Budujemy kolejne dowody:

```text
AUDIT
→ DOMAIN PARITY
→ SEMANTIC UI CONTRACT
→ AI RUNTIME HOST
→ KNOWLEDGE / PERCEPTION
→ MAP / TERMINAL / CORE APPS
→ CAPABILITY GRAPH
→ DURABLE INTERACTION PIPELINE
→ OLLAMA DRY-RUN
→ STUDENT
→ SUPERVISED EXECUTION
→ LIMITED AUTONOMY
→ FULL ECONOMY / OPERATIONS / TERRITORY
→ GHOSTNETWORK POWERS
→ MULTI-AI
```

Każdy sprint ma własny GO / NO-GO.

Nie łączymy pierwszego modelu z pierwszym refaktorem domeny.

---

# 2. Release A — Proof of One World

Zakres:

```text
139.0–139.4
```

Cel:

- udowodnić, że istnieje jeden gameplay,
- wyznaczyć wspólne komendy,
- zdefiniować semantyczny kontrakt aplikacji,
- stworzyć pusty runtime AI bez modelu.

---

# 3. Sprint 139.0 — Full Gameplay, UI and Interaction Audit

## Cel

Zmapować prawdziwy CHAOS przed projektowaniem adapterów.

## Zakres audytu

Domeny:

- profil,
- ustawienia,
- pasek systemowy,
- Mapa,
- podróż,
- zoom,
- Recon,
- Target Registry,
- wszystkie akcje Mapy,
- Terminal,
- skrypty,
- Centrum Operacji,
- Pliki i pojemność dysku,
- Wallet,
- WebDragons,
- Googleplex,
- Ghost Exchange,
- BlackNet,
- Cyberner,
- incydenty,
- służby,
- terytoria,
- konflikty,
- GhostNetwork,
- Pro Tools,
- creatory aplikacji.

Dla każdej domeny ustalić:

```text
Human UI event
→ handler
→ auth
→ validation
→ domain logic
→ persistence
→ canonical event
→ visible result
```

Dodatkowo spisać:

- wszystkie rodziny aplikacji,
- źródła publicznych manifestów,
- sposób filtrowania narzędzi,
- wszystkie modalne flow,
- wszystkie stany paska systemowego,
- miejsca, gdzie UI zna dane niedostępne w backendowym kontrakcie,
- dynamiczne efekty GhostNetwork,
- miejsca zawierające logikę bezpośrednio w JS/handlerach.

## Artefakty

- `SPRINT_139_0_DOMAIN_AND_UI_PARITY_AUDIT.md`,
- `SPRINT_139_0_APP_FAMILY_INVENTORY.md`,
- `SPRINT_139_0_HUMAN_INTERACTION_MAP.md`.

## GO

Mamy kompletną mapę wejść, wyników i side effects.

## NO-GO

Jakakolwiek krytyczna mechanika nie ma możliwej do wydzielenia canonical ścieżki albo jej stan istnieje wyłącznie w frontendzie.

---

# 4. Sprint 139.1 — Shared Domain Action Gateway

## Cel

Wyciągnąć wspólne wejście do działań człowieka i przyszłego AI.

## Zakres

- actor context,
- command registry,
- domain routing,
- canonical action result,
- idempotency key,
- expected revision,
- audit source,
- parity tests.

## Pierwszy zakres

- WAIT,
- jedna bezpieczna zmiana session,
- MOVE,
- podstawowy Recon entry point.

Nie wdrażamy modelu.

## Test kluczowy

Ta sama akcja wykonana przez ścieżkę oznaczoną `human` i testową ścieżkę `ai` przechodzi przez te same reguły i daje równoważny rezultat.

## GO

Brak specjalnej logiki gameplayowej dla AI.

---

# 5. Sprint 139.2 — Semantic Surface Contract and App Manifest Model

## Cel

Zdefiniować wspólny język semantycznego UI.

## Zakres

- `SemanticSurface` schema,
- visible sections/items/status,
- task-local refs,
- interaction refs,
- blocking state,
- source revisions,
- provenance,
- Public App Manifest,
- Internal Execution Manifest,
- App Family registry,
- manifest versioning.

## Rodziny MVP

- desktop/system app,
- window app,
- terminal app,
- browser page,
- passive item/upgrade.

## Ważne

Nie implementujemy jeszcze wszystkich aplikacji.

Definiujemy kontrakt, który pozwala je integrować bez ręcznego prompta.

## GO

Na podstawie testowej aplikacji możemy wygenerować player-visible surface bez ujawnienia hidden execution fields.

---

# 6. Sprint 139.3 — AI Player Identity, Lifecycle and Control Plane

## Cel

Utworzyć normalny profil AI i bezpieczne sterowanie autonomią.

## Zakres

- AI Player Registry,
- actor type,
- jawny status AI,
- CREATED,
- STUDENT_OBSERVE,
- STUDENT_SUGGEST,
- STUDENT_SUPERVISED,
- AUTONOMOUS,
- SUSPENDED,
- global switch,
- per-player switch,
- dry-run,
- audit lifecycle,
- model binding placeholder.

## Bez gameplayowej autonomii

AI konto może istnieć, ale nie wykonuje samodzielnych działań.

## GO

Profil AI jest normalnym profilem CHAOS, a wyłączenie autonomii nie niszczy konta ani majątku.

---

# 7. Sprint 139.4 — AI Runtime Host and Desktop Session Shell

## Cel

Zbudować drugi klient CHAOS bez modelu.

## Zakres

- AI Runtime Host w procesie gry,
- Desktop Session Store,
- active app,
- open windows,
- focus,
- modal,
- background processes,
- selected target,
- system bar surface,
- session revisions,
- testowy Runtime Interaction Gateway,
- ręczny diagnostic driver.

## Test

Operator diagnostyczny może semantycznie:

- otworzyć pulpit,
- otworzyć/zamknąć okno,
- zmienić focus,
- obsłużyć modal,
- zobaczyć pasek systemowy.

## GO

Runtime odwzorowuje session bez renderowania HTML i bez modelu.

---

# 8. Release B — Perception and Core Interface

Zakres:

```text
139.5–139.10
```

Cel:

- zbudować wiedzę i percepcję,
- odtworzyć Mapę, Terminal i najważniejsze aplikacje,
- udowodnić hierarchiczną eksplorację.

---

# 9. Sprint 139.5 — Observation, Knowledge, Provenance and Trust Boundary

## Cel

Udowodnić, że AI może otrzymać wyłącznie legalną wiedzę.

## Zakres

- Observation Builder,
- Knowledge Resolver,
- reuse Shared Semantic Input Layer,
- public/clan/owner,
- file-derived knowledge,
- scan-derived knowledge,
- message/news-derived knowledge,
- provenance,
- freshness,
- trust labels dla treści świata,
- `UNKNOWN > GUESS`.

## Testy

- hidden GhostNetwork nie przechodzi,
- cudzy private fact nie przechodzi,
- unread file content nie przechodzi,
- unread BlackNet signal nie przechodzi,
- przeczytana wiadomość przechodzi,
- prompt-like text pozostaje untrusted world content.

## GO

`knowledge_leakage = 0`.

---

# 10. Sprint 139.6 — AI Perception, Attention and Focus

## Cel

Zbudować M29 jako canonical ekran rzeczywistości.

## Zakres

- Perception Frame,
- NOW,
- system bar,
- ATTENTION,
- FOCUS,
- ACTIVE,
- BACKGROUND,
- RECENT,
- open windows summary,
- current surface,
- bounded policy,
- perception revisions,
- deterministic build,
- replay.

## Scenariusz

AI ogląda jedną aplikację, a w tle:

- kończy się operacja,
- przychodzi wiadomość Cybernera,
- pojawia się alert.

Model jeszcze nie jest podłączony. Diagnostyka pokazuje prawidłową kolejkę uwagi.

## GO

Ten sam canonical input daje ten sam frame, a krytyczny sygnał nie znika przez limit kontekstu.

---

# 11. Sprint 139.7 — Geography Semantic Foundation

## Cel

Dać backendowi semantykę podkładu Mapy.

## Zakres

- źródło danych OpenStreetMap,
- import/normalizacja potrzebnych tagów,
- Geography Cache,
- spatial index,
- bbox query,
- water/coastline/roads/build-up/parks,
- snapshot version,
- cache miss behavior,
- metryki.

## Nie obejmuje

- pełnej gry terytorialnej,
- strategii,
- modelu,
- optymalizacji punktów.

## GO

Dla testowego viewportu backend potrafi deterministycznie powiedzieć, gdzie jest woda, wybrzeże i zabudowa, bez analizy obrazka Leafleta.

---

# 12. Sprint 139.8 — AI Spatial Interface: Viewport, Zoom, Travel and Recon

## Cel

Odtworzyć podstawowy gameplay Mapy.

## Zakres

- Map Semantic Surface,
- pozycja motocykla,
- viewport,
- zoom zgodny z profilem,
- Map Focus,
- Travel Envelope,
- wybór punktu,
- MOVE,
- arrival,
- Recon Envelope,
- Recon action,
- pozytywny i negatywny scan,
- różnica UNKNOWN / NO TARGETS,
- Spatial Memory v0.

## Test scenariuszowy

Wybrzeże Barcelony:

- Mapa pokazuje morze i zabudowę,
- przed Reconem targety są nieznane,
- po Reconie ujawniają się tylko legalne targety,
- negatywny sektor scan zostaje zapisany z freshness.

## GO

AI Spatial Interface nie daje większego zoomu, zasięgu ani wiedzy niż klient człowieka.

---

# 13. Sprint 139.9 — Core Semantic App Adapters

## Cel

Dać AI podstawowy pulpit operacyjny.

## Zakres adapterów

- Terminal,
- Menedżer plików,
- WebDragons shell,
- Wallet,
- Profil,
- Ustawienia,
- Radio,
- Cyberner shell,
- Centrum Operacji summary.

## W tym sprincie

- otwieranie,
- nawigacja,
- odczyt,
- zamykanie,
- foreground/background,
- modal,
- brak pełnych state-changing flow poza wcześniej wspieranymi.

## GO

Diagnostic driver może przejść przez wszystkie podstawowe aplikacje bez gigantycznego snapshotu.

---

# 14. Sprint 139.10 — Terminal Discovery and CHAOS Scripts

## Cel

Udowodnić alternatywną, odkrywaną ścieżkę działania.

## Zakres

- terminal prompt,
- `help`,
- app help,
- typed command,
- output,
- syntax errors,
- history,
- script files,
- submit classification,
- bezpieczny virtual runtime,
- zero system shell.

## Scenariusz

Operator/runtime:

- otwiera Terminal,
- wpisuje `help`,
- odkrywa aplikację,
- sprawdza jej pomoc,
- uruchamia testową komendę,
- otrzymuje normalny rezultat domenowy.

## GO

Terminal AI ma dokładnie możliwości terminalowego profilu gracza i nie ma żadnej ścieżki do hosta.

---

# 15. Release C — App Ecosystem and Capabilities

Zakres:

```text
139.11–139.13
```

Cel:

- obsłużyć rosnący katalog aplikacji,
- stworzyć Capability Graph,
- przygotować Pro Tools i dynamiczne modyfikatory.

---

# 16. Sprint 139.11 — Googleplex Search, User Apps and Family Adapters

## Cel

Obsłużyć 70+ aplikacji i przyszłe aplikacje graczy bez zwiększania prompta.

## Zakres

- Googleplex Semantic Surface,
- search,
- filters/categories dostępne human UI,
- pagination,
- product details,
- public manifest,
- install status,
- purchase preconditions in dry-run,
- AppForge publication → manifest compiler,
- rodziny: button choices, progressbar, map tool, creator.

## Test

Nowa aplikacja utworzona przez creatora:

- publikuje się w Googleplexie,
- otrzymuje publiczny manifest,
- jest wyszukiwalna,
- generuje surface swojej rodziny,
- nie ujawnia hidden effect fields.

## GO

Liczba aplikacji nie wpływa liniowo na rozmiar bieżącego contextu.

---

# 17. Sprint 139.12 — Capability Graph, Contextual Affordances and Restrictions

## Cel

Połączyć wszystkie źródła możliwości.

## Zakres

- base rights,
- level/respect,
- location,
- target state,
- installed apps,
- Pro Tool placeholders,
- disk and money requirements,
- cooldowns,
- restriction model,
- Contextual Interaction Catalog,
- capability revisions,
- diagnostics „why available / why unavailable”.

## Ważne

Capability Graph nie jest przekazywany modelowi w całości.

Bieżąca surface wybiera relewantne affordances.

## GO

Ta sama funkcja pojawia się i znika zgodnie z canonical stanem profilu.

---

# 18. Sprint 139.13 — Pro Tools and Alternate Interface Foundations

## Cel

Udowodnić, że zakupiona aplikacja może dać wygodniejszą drogę do tej samej domeny.

## Zakres MVP

Jeden reprezentatywny Pro Tool, najlepiej Victim Picker albo Operation Control:

- ownership,
- installation,
- semantic surface,
- legal aggregated data,
- alternate navigation,
- same Domain Action Gateway,
- parity tests.

## GO

AI bez Pro Toola nie ma jego affordances. AI z Pro Toolem może użyć wygodniejszej ścieżki bez dostępu do ukrytej prawdy.

---

# 19. Release D — Durable Decision Runtime

Zakres:

```text
139.14–139.18
```

Cel:

- uruchomić osobny worker,
- prowadzić wielokrokowe sesje,
- przejść od dry-run do pierwszej kontrolowanej autonomii.

---

# 20. Sprint 139.14 — Durable Task and Interaction Session Pipeline

## Cel

Zbudować pełny pipeline bez modelu.

## Zakres

- task table,
- outbox/inbox,
- claim,
- lease,
- heartbeat,
- retry,
- dead-letter,
- interaction session,
- session checkpoint,
- Interface Step requests/results,
- World Action candidate,
- expiry,
- dedupe,
- revision binding,
- audit.

## Tryby

- status,
- inspect-task,
- inspect-session,
- replay-session,
- dry-run.

## GO

Pełną testową sesję można odtworzyć i wznowić po crashu bez side effects.

---

# 21. Sprint 139.15 — Local Ollama Worker, Interface Steps Only

## Cel

Podłączyć `chaos-ai-player-worker` do lokalnej Ollamy, nadal bez wykonania World Actions.

## Zakres

- Decision Router v1,
- Ollama Adapter,
- System Policy,
- Current Task Package,
- Runtime Result,
- structured next step,
- bounded context,
- step budget,
- anti-loop,
- telemetryka,
- candidate interaction history.

## Model

`llama3.1:8b`.

## Execution

World Actions są zapisywane, ale nie wykonywane.

Interface Steps mogą działać tylko w bezpiecznym testowym runtime.

## GO

Model potrafi nawigować pulpit, Mapę i Terminal bez wymyślania refs oraz bez niekończących się pętli.

---

# 22. Sprint 139.16 — STUDENT Observe and Suggest

## Cel

Utworzyć pierwszego rzeczywistego AI Playera.

## Zakres

- Student Experience Recorder,
- obserwacja działań człowieka,
- semantyczny zapis flow,
- sugestie modelu,
- porównanie AI vs human,
- Memory v0,
- Intent v0,
- ręczna ocena jakości.

## Testowany flow

- pulpit,
- Mapa,
- podróż,
- Recon,
- target,
- Terminal/help,
- wybór jednej aplikacji.

## GO

Model generuje sensowne, legalne i odtwarzalne sugestie.

---

# 23. Sprint 139.17 — STUDENT Supervised Execution

## Cel

Po raz pierwszy pozwolić decyzji AI zmienić świat po akceptacji człowieka.

## Zakres

- Supervision Gateway,
- accept/reject,
- State Revision Guard,
- Domain Action Gateway,
- pełny audit,
- stale rebuild,
- kill switch.

## Dopuszczone akcje

- WAIT,
- MOVE,
- Recon,
- jeden bezpieczny operation start.

## Niedopuszczone

- zakupy,
- przelewy,
- sprzedaż,
- konflikty,
- GhostNetwork powers.

## GO

Zaakceptowana akcja jest identyczna domenowo jak akcja człowieka i nie dubluje się przy retry.

---

# 24. Sprint 139.18 — First Limited Autonomous Vertical Slice

## Cel

Pierwszy AI Player wykonujący ograniczony, prawdziwy gameplay bez kliknięcia człowieka.

## Scenariusz milestone

AI:

1. budzi się na pulpicie,
2. otwiera Mapę,
3. ogląda viewport,
4. wybiera punkt w zasięgu,
5. podróżuje,
6. robi Recon,
7. wybiera target,
8. otwiera Terminal albo mapowy flow,
9. uruchamia jedną operację,
10. czeka na wynik,
11. reaguje po kolejnym triggerze.

## Guardrails rolloutowe

- 1 AI,
- 1 worker,
- concurrency 1,
- max world actions/hour,
- ograniczone domeny,
- local Ollama,
- global kill switch,
- pełny replay.

## GO

- zero knowledge leak,
- zero unauthorized action,
- zero duplicate side effect,
- zero shell escape,
- human gameplay bez degradacji.

---

# 25. Release E — Full Player Economy and Operations

Zakres:

```text
139.19–139.22
```

Cel:

- dać AI prawdziwy dysk, ekonomię, ryzyko, media i życie społeczne.

---

# 26. Sprint 139.19 — Files, Storage, Loot, Wallet and Ghost Exchange

## Cel

Połączyć operacje z materialnymi konsekwencjami.

## Zakres

- pełny Files Adapter,
- katalogi,
- odczyt plików,
- aplikacje/skrypty/data,
- disk capacity,
- overflow,
- loot retention,
- Wallet history,
- transfer supervised first,
- Ghost Exchange packages,
- sprzedaż,
- purchase/install,
- economic audit.

## Test

Brak miejsca powoduje utratę części danych i mniejszą paczkę, a nie specjalny fallback dla AI.

## GO

AI korzysta z dokładnie tej samej ekonomii plików i HC co człowiek.

---

# 27. Sprint 139.20 — Operations, Tool Experimentation and Concurrent Processes

## Cel

Rozszerzyć AI na prawdziwy system operacji.

## Zakres

- więcej map actions,
- cztery wskaźniki,
- progres celu,
- tool choice,
- konfiguracje,
- agresywny/cichy/maskowanie/metadata/payload,
- równoległe operacje,
- Centrum Operacji,
- Operation Feedback → experience,
- cancellation,
- target abandonment.

## GO

AI potrafi przejść różnymi legalnymi ścieżkami do podobnego celu i uczyć się skutków narzędzi bez otrzymywania ukrytej sekwencji.

---

# 28. Sprint 139.21 — Incidents, Services, Response Network and Sanctions

## Cel

Włączyć ryzyko i realne zagrożenia.

## Zakres

- incident levels,
- service actors,
- spatial visibility,
- movement/proximity,
- alerts,
- confiscation,
- HC/file/tool losses,
- teleport restriction,
- Cyberner restriction,
- mobility restriction,
- Alcatras,
- recovery.

## GO

Ograniczenie rzeczywiście zmienia Capability Graph i UI, a nie tylko tekst prompta.

---

# 29. Sprint 139.22 — Cyberner, News, BlackNet, Radio and Clan Manifest

## Cel

Włączyć AI do informacyjnego i społecznego świata.

## Zakres

- pełny Cyberner,
- messages and threads,
- teleports,
- relationship memory,
- Googleplex News,
- BlackNet signals,
- Radio semantic content,
- unread/badges,
- clan manifest as world content,
- AI ↔ AI przez Cybernera,
- prompt injection tests.

## GO

AI zdobywa informacje przez faktyczne kanały i może kształtować strategię klanową bez twardego skryptu osobowości.

---

# 30. Release F — Strategic World

Zakres:

```text
139.23–139.26
```

Cel:

- terytoria,
- Pro Tools,
- GhostNetwork,
- supermoce,
- deceptive perception.

---

# 31. Sprint 139.23 — Full Pro Tools and Alternate Operational Paths

## Cel

Zintegrować specialistyczne klienty świata.

## Zakres

- Victim Picker,
- Territory Control,
- Operation Control,
- AGI/konsole według audytu,
- legal aggregation,
- direct navigation,
- ownership/install,
- same Gateway,
- semantic surfaces,
- performance comparison basic UI vs Pro Tool.

## GO

Pro Tool daje realną przewagę interfejsową, ale nie administracyjną.

---

# 32. Sprint 139.24 — Territory and Conflict Autonomy

## Cel

Włączyć strategiczną geometrię i konflikty.

## Zakres

- klastry,
- filary,
- innery,
- own/known territory,
- conflict lines,
- territory actions,
- reaction tasks,
- stale-state protection,
- map and Territory Control routes,
- spatial memory,
- coastal and gap scenarios in tests.

## GO

AI może uczestniczyć w konflikcie bez hidden topology oraz samodzielnie wyciągać przestrzenne wnioski.

---

# 33. Sprint 139.25 — GhostNetwork Player Integration

## Cel

Dopuścić AI do części, modułów, aktywacji i informacji GhostNetwork.

## Zakres

- public/clan/owner,
- discovered/contained/active,
- parts as player/world resources,
- module state,
- legal actions,
- narrative signals,
- Shared Semantic Input Layer reuse,
- strict hidden-state tests.

## NO-GO

Jakikolwiek przypadek, w którym AI poznaje canonical hidden state niedostępny równoważnemu graczowi.

---

# 34. Sprint 139.26 — GhostNetwork Powers and Projected Reality

## Cel

Wdrożyć dwadzieścia kanonicznych supermocy.

## Zakres

- World Capability Modifier Pipeline,
- wszystkie 4 klany × 5 mocy,
- activation/expiry,
- profession binding,
- cooldowns,
- perception modifiers,
- action affordances,
- execution modifiers,
- deceptive markers,
- false trails,
- projection lineage,
- Counter/repair flows,
- Cyberner publications.

## Testy krytyczne

- Węzeł Widmo oszukuje AI bez przecieku,
- Skan Integralny może go ujawnić,
- Insider Feed pojawia się tylko w Ghost Exchange,
- Kwarantanna zatrzymuje legalnie kwalifikujące operacje,
- wygaśnięcie części odbiera zdolność,
- replay nie aktywuje efektu drugi raz.

## GO

Moce działają równoważnie dla human i AI oraz nie naruszają visibility GhostNetwork.

---

# 35. Release G — Intelligence Ecosystem

Zakres:

```text
139.27–139.30
```

Cel:

- dojrzała pamięć,
- porównywanie modeli,
- zewnętrzni providerzy,
- wielu AI i kultura.

---

# 36. Sprint 139.27 — Intent, Memory and Strategy v2

## Cel

Dać AI długofalową ciągłość bez przesyłania całej historii.

## Zakres

- pełny Intent Manager,
- spatial memory,
- tool experience,
- terminal knowledge,
- relationship memory,
- clan/cultural memory,
- provenance,
- freshness,
- bounded retrieval,
- memory consolidation,
- forgetting/decay policy,
- no chain-of-thought.

## GO

AI utrzymuje plan przez wiele tasków i wykorzystuje doświadczenie bez zwiększania visibility.

---

# 37. Sprint 139.28 — Model Benchmarking and Perception Quality Lab

## Cel

Rozdzielić jakość mózgu od jakości interfejsu.

## Zakres

- frozen perception frames,
- replay sessions,
- same-world cross-model tests,
- decision divergence,
- human baseline,
- perception omission diagnostics,
- prompt/context version comparison,
- strategy scenario suite.

## GO

Możemy wiarygodnie powiedzieć, czy błąd wynika z modelu, perception, app adaptera czy world logic.

---

# 38. Sprint 139.29 — External Providers and Credential Vault

## Cel

Dodać wymienne mózgi bez zmiany postaci.

## Zakres

- provider contract,
- Vault,
- encrypted bindings,
- provider health,
- fallback,
- budgets,
- rate limits,
- model switch,
- same AI identity and memory.

## GO

AI może zmienić model bez utraty profilu, historii, session state i intentu.

---

# 39. Sprint 139.30 — Multi-AI Scheduling, Fairness and Teaching

## Cel

Przejść od eksperymentu do populacji.

## Zakres

- wielu AI,
- fair scheduler,
- task priorities,
- per-provider concurrency,
- capacity protection human gameplay,
- anti-loop,
- AI ↔ AI social behavior,
- AI as teacher source,
- selective experience transmission,
- provenance pokoleń,
- brak klonowania osobowości.

## Status

Multi-AI jest produkcyjnym celem.

AI teaching pozostaje eksperymentalne i może zostać wydzielone jako osobna seria po ocenie wyników.

---

# 40. Rekomendowane milestone’y

## Milestone 1 — Semantic Client Exists

Po `139.4`.

Mamy AI profil i pusty semantyczny pulpit bez modelu.

## Milestone 2 — AI Can See and Navigate

Po `139.10`.

Runtime potrafi obsłużyć Mapę, Terminal i podstawowe aplikacje.

## Milestone 3 — AI Can Think Safely

Po `139.15`.

Ollama nawigacyjnie korzysta z runtime, ale nie zmienia świata.

## Milestone 4 — First Living AI

Po `139.18`.

Jeden AI Player wykonuje ograniczony realny flow.

## Milestone 5 — Full Economic Player

Po `139.22`.

AI ma pliki, rynek, media, relacje, ryzyko i konsekwencje.

## Milestone 6 — Strategic Player

Po `139.26`.

AI uczestniczy w terytoriach i GhostNetwork z supermocami.

## Milestone 7 — AI Population

Po `139.30`.

Wiele modeli i wielu AI może współistnieć bez destabilizacji świata.

---

# 41. Co można łączyć

Jeżeli audyt pokaże mały zakres:

- `139.2 + 139.4` — schema i runtime shell,
- `139.5 + 139.6` — knowledge i perception,
- `139.7 + 139.8` — geography i Spatial Interface,
- `139.9 + 139.10` — podstawowe aplikacje i Terminal,
- `139.14 + 139.15` — pipeline i worker dry-run,
- `139.16 + 139.17` — Student suggest i supervised,
- `139.19 + 139.20` — Files/economy i operations, tylko po dobrych testach.

Nie rekomenduję łączenia:

- `139.1` z modelem,
- pierwszego workera z autonomią,
- pierwszej autonomii z ekonomią,
- terytoriów z pierwszym GhostNetwork,
- GhostNetwork visibility z supermocami,
- external providers z pierwszym release.

---

# 42. Minimalny wariant eksperymentalny

Jeżeli celem jest szybkie sprawdzenie idei, minimalna ścieżka to:

```text
139.0 Audit
139.1 Domain Gateway
139.2 Semantic Surface
139.3 AI Identity
139.4 Runtime Host
139.5 Knowledge
139.6 Perception
139.7–139.8 Map
139.10 Terminal
139.12 Capability Graph
139.14 Pipeline
139.15 Ollama dry-run
139.16 Student
139.17 Supervised
139.18 Limited Autonomy
```

Nie daje to jeszcze całego CHAOS.

Daje jednak wiarygodną odpowiedź, czy model potrafi być cyfrowym użytkownikiem gry.

---

# 43. Główne test gates całej serii

## World equality gate

AI i human trafiają do tych samych reguł domenowych.

## Knowledge gate

AI nie wie więcej niż human.

## Surface parity gate

Istotny element UI ma semantyczny odpowiednik.

## Discovery gate

AI nie zna nieodkrytych komend, plików, targetów i aplikacji.

## Map gate

Zoom, travel, Recon i geografia są zgodne.

## Terminal gate

Brak dostępu poza virtual runtime CHAOS.

## App ecosystem gate

Nowa aplikacja gracza dostaje bezpieczny manifest i adapter rodziny.

## Capability gate

Aplikacja, Pro Tool, moc i ograniczenie poprawnie zmieniają możliwości.

## Deception gate

AI może zostać oszukane przez legalną mechanikę bez przecieku canonical truth.

## State gate

Stara decyzja nie wykonuje się po krytycznej zmianie.

## Idempotency gate

Retry/replay nie powtarza skutku.

## Failure gate

Awaria modelu lub workera nie zmienia świata.

## Capacity gate

Autonomia nie pogarsza rozgrywki ludzi.

## Audit gate

Każdy krok i skutek jest odtwarzalny.

---

# 44. Rekomendacja startowa

Pierwszym zadaniem dla Codexa powinien być:

> **Sprint 139.0 — przeprowadź pełny audyt istniejących domen, UI, rodzin aplikacji i alternatywnych ścieżek interakcji CHAOS; nie implementuj LLM, nie zmieniaj gameplayu i nie twórz jeszcze AI Playera. Wynikiem ma być mapa wspólnych domen, powierzchni UI, side effects, visibility oraz miejsc wymagających refaktoru przed stworzeniem semantycznego klienta.**

Dopiero po tym audycie można bezpiecznie zatwierdzić finalne granice Sprintu 139.1 i fizyczną strukturę modułów.
