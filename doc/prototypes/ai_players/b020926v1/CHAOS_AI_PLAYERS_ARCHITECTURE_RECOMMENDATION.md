# CHAOS — Autonomous Players
## Rekomendacja architektoniczna

**Status:** rekomendacja projektowa  
**Zakres:** autonomiczni gracze AI w istniejącym świecie CHAOS  
**Dokument bazowy:** `CHAOS_AUTONOMOUS_PLAYER.md`

---

# 1. Decyzja architektoniczna

Rekomendowane rozwiązanie nie tworzy osobnego subsystemu gameplayowego dla AI.

AI Player powinien być **normalnym profilem gracza CHAOS**, a jedyną różnicą względem człowieka powinno być źródło decyzji:

- człowiek: UI → domenowa komenda gry,
- AI: Decision Task → model → domenowa komenda gry.

Obie ścieżki muszą spotykać się **przed wykonaniem akcji**, w tym samym `Domain Action Gateway`.

Najważniejszy invariant:

> **AI Player może wiedzieć i zrobić wyłącznie to, co w tym samym stanie świata mógłby wiedzieć i zrobić zwykły gracz CHAOS.**

To powinien być invariant techniczny, testowany automatycznie, a nie tylko zasada lore.

---

# 2. Najważniejsza rekomendacja: najpierw wspólna warstwa akcji, potem LLM

Największym ryzykiem projektu nie jest model AI. Największym ryzykiem jest powstanie dwóch ścieżek gameplayu:

```text
HUMAN → normalne endpointy / reguły
AI    → specjalne funkcje / skróty
```

Tego należy uniknąć.

Rekomendowana ścieżka:

```text
HUMAN UI ───────────────┐
                        │
                        ▼
                 DOMAIN ACTION GATEWAY
                        │
                        ▼
                  GAME ENGINE / STORE
                        ▲
                        │
AI DECISION ────────────┘
```

Jeżeli obecne endpointy HTTP zawierają bezpośrednio część reguł gameplayowych, przed uruchomieniem autonomii należy wyciągnąć tę logikę do współdzielonych komend domenowych.

Przykład:

```text
POST /api/...            AI Action
      │                     │
      └──────┬──────────────┘
             ▼
      execute_game_action(
          actor_profile_id,
          action_type,
          payload,
          expected_revision
      )
```

`execute_game_action()` jest tu symbolem kontraktu, nie propozycją jednej gigantycznej funkcji. Faktyczna implementacja powinna routować do istniejących domen: ruch, operacje, Googleplex, Ghost Exchange, Cyberner, terytoria, GhostNetwork itd.

---

# 3. Architektura logiczna

```text
                         CHAOS WORLD
                              │
                    PLAYER PROFILE / STATE
                              │
                    OBSERVATION BUILDER
                              │
                     KNOWLEDGE RESOLVER
                              │
                     SEMANTIC FACT PACK
                              │
                     CAPABILITY RESOLVER
                              │
                       ACTION CATALOG
                              │
                         TASK ENGINE
                              │
                       AI PLAYER OUTBOX
                              │
                   CHAOS AI PLAYER WORKER
                              │
                        DECISION ROUTER
                         /           \
                    OLLAMA          PROVIDERS
                         \           /
                            DECISION
                              │
                     DECISION VALIDATOR
                              │
                     STATE REVISION GUARD
                              │
                    DOMAIN ACTION GATEWAY
                              │
                         GAME ENGINE
                              │
                         WORLD EVENTS
                      /         |          \
                 MEMORY     NEXT TASK    NARRATIVE
```

Model znajduje się wyłącznie po stronie **decyzji**. Nigdy nie jest źródłem prawdy o stanie świata i nigdy nie wykonuje bezpośrednio zmian w bazie.

---

# 4. Warstwa tożsamości

AI Player powinien używać istniejącego profilu gracza jako canonical identity.

Nie rekomenduję tworzenia równoległego `ai_inventory`, `ai_wallet`, `ai_territory` ani podobnych struktur.

Nowe dane dotyczą tylko autonomii:

- typ aktora: human / AI,
- lifecycle AI: STUDENT / AUTONOMOUS / SUSPENDED,
- binding do Decision Provider,
- bieżący intent,
- runtime autonomii,
- pamięć i relacje,
- historia decyzji.

Profil gameplayowy pozostaje normalnym profilem CHAOS.

---

# 5. Observation Builder

Model nie powinien czytać endpointów UI ani dumpów bazodanowych.

`Observation Builder` buduje chwilowy, canonical obraz tego, co dany gracz może aktualnie zaobserwować.

Źródła mogą obejmować:

- publiczny stan mapy dostępny graczowi,
- jego pozycję,
- jego profil i ekwipunek,
- wykonane scany,
- posiadane pliki,
- dostępne oferty,
- jego terytoria i konflikty,
- własne operacje,
- wiadomości Cybernera,
- publiczne wydarzenia,
- jawne dla niego informacje GhostNetwork.

Observation Builder nie interpretuje strategicznie świata. Zbiera canonical stan widzialny dla gracza.

---

# 6. Knowledge Resolver

`Knowledge Resolver` odpowiada za różnicę między tym, co istnieje w bazie, a tym, co postać rzeczywiście wie.

Powinien współdzielić filozofię i część infrastruktury z istniejącym `Shared Semantic Input Layer`.

Zasada:

> `UNKNOWN > GUESS`

Brak faktu ma pozostać brakiem faktu.

Resolver powinien pilnować między innymi:

- public / clan / owner visibility,
- wiedzy zdobytej poprzez scan,
- własności informacji,
- wiedzy z wiadomości Cybernera,
- wiedzy historycznej postaci,
- hidden state GhostNetwork,
- ukrytej topologii i wewnętrznych identyfikatorów.

Nie powinien przekazywać modelowi technicznych pól, których postać nie zna jako pojęć świata.

---

# 7. Semantic Fact Pack

Model powinien dostawać świat jako pakiet znaczeń, nie jako surowy JSON backendu.

Przykład:

```text
f01: Posiadasz 1260 HC.
f02: Znajdujesz się w Warszawie.
f03: W pobliżu znajduje się zeskanowany przez ciebie target.
f04: Target wymaga możliwości, którą posiada xmapper.
f05: xmapper znajduje się w twoim ekwipunku.
```

`fact_ref` powinien służyć do lineage i późniejszego audytu decyzji.

Model nie powinien otrzymywać canonical ID, jeśli nie jest ono elementem wiedzy gracza. Do wskazywania obiektów w decyzji można używać chwilowych `target_ref`, `item_ref`, `player_ref` generowanych dla konkretnego taska.

---

# 8. Capability Resolver i Action Catalog

To klucz bezpieczeństwa całego rozwiązania.

Model nie odpowiada na pytanie:

> „Co możesz zrobić?”

Backend wylicza aktualnie legalny lub potencjalnie legalny katalog działań.

Przykład:

```text
a01 WAIT
a02 MOVE(location_ref)
a03 SCAN_TARGET(target_ref, tool_ref)
a04 BUY_ITEM(item_ref)
a05 SEND_CYBERNER_MESSAGE(player_ref, message)
```

Action Catalog powinien być generowany na podstawie:

- stanu profilu,
- pozycji,
- cooldownów,
- posiadanych narzędzi,
- stanu targetu,
- reguł klanowych,
- zasad terytorialnych,
- ekonomii,
- aktualnego lifecycle AI.

Model może wybrać tylko `action_ref` istniejący w tym tasku.

Nie oznacza to, że Action Catalog zastępuje Game Engine. Po wyborze akcja jest ponownie walidowana na aktualnym stanie świata.

---

# 9. Task Engine

Task Engine powinien być **event-driven**, nie pollingiem typu „zapytaj model co sekundę”.

Task powstaje wtedy, kiedy pojawia się realny powód do decyzji, np.:

- zakończenie ruchu,
- wynik operacji,
- nowa wiadomość Cybernera,
- atak na terytorium,
- zmiana dostępności targetu,
- zakończenie cooldownu,
- zmiana ceny lub dostępności interesującego zasobu,
- pozyskanie części GhostNetwork,
- zakończenie poprzedniego planu,
- timeout oczekującej decyzji.

Task powinien zawierać:

```text
task_id
player_id
world_revision / relevant revisions
task_type
semantic_facts[]
relevant_memory[]
current_intent
available_actions[]
created_at
expires_at
```

Nie należy umieszczać w nim sekretów providera ani wewnętrznych reguł świata.

---

# 10. Oddzielny AI Player Outbox / Inbox

Rekomenduję wykorzystać wzorzec sprawdzony przy workerze narracyjnym, ale nie współdzielić tabel ani lifecycle tasków narracyjnych.

Powód: narracja i decyzja mają inne skutki oraz inne wymagania bezpieczeństwa.

Proponowany przepływ:

```text
ai_player_task
      ↓
ai_player_outbox
      ↓
worker claim / lease / heartbeat
      ↓
model
      ↓
ai_player_decision_inbox
      ↓
validator
      ↓
action execution
```

Można współdzielić biblioteki:

- lease,
- heartbeat,
- retry,
- dead-letter,
- telemetrykę,
- klienta Ollama,
- structured output.

Nie należy współdzielić promptów, schematów decyzji ani uprawnień.

---

# 11. AI Player Worker

Rekomendowany nowy proces:

```text
chaos-ai-player-worker
```

Worker:

1. claimuje task,
2. pobiera przypisany model policy,
3. buduje bounded prompt,
4. wywołuje Decision Router,
5. waliduje structured output,
6. zapisuje candidate decision,
7. nie wykonuje samodzielnie zmian w świecie.

Worker nie powinien posiadać bezpośredniego API do:

- SQL write,
- shella,
- systemu plików gameplayowych,
- dowolnych endpointów CHAOS,
- nieograniczonego HTTP.

Jego wyjściem jest tylko decyzja zgodna ze schematem.

---

# 12. Decision Router i Provider Adapter

Tożsamość AI Playera nie może być związana z modelem.

`Decision Router` wybiera provider na podstawie konfiguracji AI Playera oraz polityki systemowej.

Pierwsza implementacja powinna obsługiwać wyłącznie:

```text
Ollama / llama3.1:8b
```

Dopiero po przejściu pełnych testów równości świata warto dodać providerów zewnętrznych.

Docelowo adapter może mieć jednolity kontrakt:

```text
generate_decision(task_package, model_policy)
    -> DecisionGenerationResult
```

Model policy powinna być code-owned i wersjonowana.

---

# 13. Structured Decision Contract

Model nie powinien zwracać dowolnego tekstu jako decyzji.

Przykładowy kontrakt:

```json
{
  "action_ref": "a03",
  "arguments": {
    "target_ref": "t02",
    "tool_ref": "i01"
  },
  "reason": "Cel został już rozpoznany, a posiadane narzędzie spełnia wymagania.",
  "intent_update": null
}
```

`reason` jest materiałem do pamięci i audytu, ale nie nadaje uprawnień.

Argumenty są rozwiązywane wyłącznie przez referencje wystawione w danym tasku.

---

# 14. State Revision Guard

Między wygenerowaniem taska a odpowiedzią modelu świat może się zmienić.

Dlatego decyzja musi być wykonywana z ochroną przed stale state.

Rekomendacja:

- task zapisuje relewantne revision/snapshot tokens,
- przed wykonaniem Action Gateway sprawdza ich aktualność,
- jeśli zmiana świata unieważnia decyzję, akcja nie jest wykonywana,
- system zapisuje `stale_decision`,
- Task Engine może wygenerować nowy task.

Nigdy nie należy „dopasowywać” starej decyzji do nowego stanu na siłę.

---

# 15. Domain Action Gateway

To najważniejszy komponent wykonawczy.

Gateway nie jest nowym Game Engine. Jest zunifikowanym wejściem do istniejących domen.

Przykładowe domeny:

```text
MovementCommandService
OperationCommandService
GoogleplexCommandService
GhostExchangeCommandService
CybernerCommandService
TerritoryCommandService
GhostNetworkCommandService
```

Każda domena:

- identyfikuje aktora,
- autoryzuje akcję,
- waliduje aktualny stan,
- wykonuje istniejącą logikę,
- zapisuje canonical rezultat,
- publikuje normalne eventy świata.

Źródło decyzji (`human` / `ai`) może być zapisywane telemetrycznie, ale nie powinno zmieniać reguł gameplayu.

---

# 16. STUDENT jako lifecycle, nie osobny gracz

`STUDENT` powinien być ograniczeniem Action Catalogu i sposobu publikacji decyzji.

Rekomendowane fazy:

### OBSERVE

AI dostaje semantic facts i obserwuje działania nauczyciela. Nie generuje akcji.

### SUGGEST

AI otrzymuje Task, generuje decyzję, ale system pokazuje ją nauczycielowi bez wykonania.

### SUPERVISED

AI proponuje akcję, człowiek może ją zaakceptować. Po akceptacji akcja przechodzi przez ten sam Action Gateway.

### AUTONOMOUS

AI może publikować decyzje do wykonania samodzielnie.

Dzięki temu możemy mierzyć jakość modelu zanim uzyska skutki gameplayowe.

---

# 17. Intent State

Model potrzebuje ciągłości większej niż pojedynczy request.

Rekomenduję mały, jawny `Intent State`, np.:

```text
primary_goal
current_plan_summary
next_expected_condition
started_at
last_replanned_at
```

Nie należy przechowywać tam nieskończonego chain-of-thought ani całych odpowiedzi modelu.

Intent jest stanem gameplayowej intencji postaci, nie prywatnym reasoningiem modelu.

---

# 18. Pamięć

Pamięć powinna być trwała, ale selektywna.

Rekomendowane klasy:

- `WORLD_MEMORY` — fakty poznane przez postać,
- `EPISODIC_MEMORY` — ważne wydarzenia z jej życia,
- `RELATIONSHIP_MEMORY` — historia i stan relacji,
- `EXPERIENCE_MEMORY` — zwięzłe wnioski z konsekwencji,
- `STUDENT_MEMORY` — obserwacje z okresu nauki.

Memory Resolver wybiera tylko relewantny fragment do konkretnego taska.

Pamięć nie może zwiększać visibility. Fakt zapisany w pamięci musi posiadać provenance pokazujące, skąd gracz go poznał.

---

# 19. Cyberner

Cyberner jest normalnym kanałem społecznym świata.

Wiadomość do AI nie jest komendą administracyjną.

```text
„Pomóż mi przejąć ten teren”
```

staje się semantic fact / social event:

```text
Gracz X proponuje wspólną akcję dotyczącą terytorium Y.
```

AI może:

- przyjąć,
- odmówić,
- negocjować,
- zignorować,
- odpowiedzieć pytaniem.

AI → AI również musi przechodzić przez normalny Cyberner. Nie należy tworzyć prywatnej magistrali komunikacyjnej między modelami.

---

# 20. Domeny gameplayowe

AI powinno być integrowane domenami i stopniowo.

Rekomendowana kolejność:

1. ruch / wait,
2. scan i proste operacje rozpoznawcze,
3. Cyberner,
4. Googleplex,
5. Ghost Exchange,
6. pełne operacje,
7. terytoria i konflikty,
8. GhostNetwork.

GhostNetwork powinien wejść późno, ponieważ błędna visibility lub decyzja może naruszyć jeden z najbardziej wrażliwych systemów świata.

---

# 21. Dane i proponowane struktury

Nie jest to finalny schemat SQL, ale rekomendowany podział odpowiedzialności.

### `ai_player_config`

- `player_id`
- `lifecycle_state`
- `provider_binding_id`
- `model_policy_version`
- `autonomy_enabled`

### `ai_player_runtime`

- `player_id`
- `current_intent_id`
- `last_decision_at`
- `next_eligible_decision_at`
- `runtime_status`

### `ai_player_tasks`

Canonical task i jego snapshot/revision metadata.

### `ai_player_decisions`

Candidate decision, validation state, execution state, reject reason.

### `ai_player_memory`

Zwięzłe trwałe rekordy pamięci z provenance i visibility.

### `ai_player_relationships`

Opcjonalny zmaterializowany stan relacji wynikający z historii interakcji.

### `ai_provider_bindings`

Tylko konfiguracja providera. Sekrety nie powinny znajdować się tutaj w plaintext.

---

# 22. Telemetria i audyt

Każdą autonomiczną decyzję powinniśmy móc odtworzyć bez zgadywania.

Minimalny audit record:

```text
task_id
player_id
task_type
semantic_fact_refs
action_catalog_version
model_policy_version
provider
model
candidate_decision
validation_result
execution_result
world_revision_before
world_revision_after
latency
token_usage
fallback_used
```

Nie trzeba zapisywać prywatnego chain-of-thought modelu.

---

# 23. Failure model

System powinien failować bezpiecznie.

### Model timeout

Task przechodzi retry/fallback. Świat nie zmienia się.

### Niepoprawny JSON

Candidate rejected. Świat nie zmienia się.

### Nieistniejący `action_ref`

Candidate rejected. Świat nie zmienia się.

### Stale state

Decyzja wygasa. Powstaje nowy task, jeśli nadal potrzebny.

### Provider down

Fallback do Ollamy, jeżeli polityka na to pozwala.

### Worker down

AI chwilowo nie podejmuje nowych decyzji. Jego konto, majątek i historia pozostają nienaruszone.

### Błąd Memory Resolvera / Knowledge Resolvera

Fail closed. Task nie powinien zostać wysłany do modelu, jeśli visibility nie może być potwierdzona.

---

# 24. Skalowanie

Na początku rekomenduję:

```text
AI players active: 1
provider: local Ollama
worker concurrency: 1
one outstanding decision per AI
bounded context
bounded output
strict cooldown / event-driven tasks
```

Po stabilizacji:

- wielu AI Playerów,
- fair scheduling między graczami,
- per-provider concurrency,
- budgets i rate limits,
- priorytety tasków reaktywnych,
- providerzy zewnętrzni.

Nie należy skalować liczby agentów przed udowodnieniem poprawności pojedynczego autonomicznego gracza.

---

# 25. Rekomendowane granice procesu

Na etapie pierwszej implementacji nie rekomenduję mikroserwisów.

Wystarczy:

```text
CHAOS WEB / GAME PROCESS
    ├── domain services
    ├── observation / knowledge
    ├── action catalog
    ├── task producer
    └── action executor

CHAOS AI PLAYER WORKER
    ├── task consumer
    ├── decision router
    ├── provider adapters
    └── decision producer
```

Baza pozostaje wspólna, ale odpowiedzialności logiczne powinny być wyraźnie oddzielone.

---

# 26. Co wykorzystujemy z obecnego CHAOS

Bez przepisywania od zera można wykorzystać:

- profile graczy,
- ekonomię HackCoin,
- mapę,
- Target Registry,
- operacje,
- Operation Feedback System,
- Googleplex,
- Ghost Exchange,
- Cyberner,
- terytoria i konflikty,
- GhostNetwork,
- canonical events,
- Shared Semantic Input Layer,
- audience visibility,
- lokalną Ollamę,
- klienta `/api/chat`,
- structured output,
- wzorce outbox / inbox,
- lease / heartbeat / retry / dead-letter,
- model policy registry,
- telemetrykę workera narracyjnego.

Największa nowa praca to **Player Decision Layer**, nie integracja samego LLM.

---

# 27. Co świadomie odkładamy

Pierwsza wersja nie powinna obejmować:

- providerów zewnętrznych,
- Credential Vault,
- wielu AI jednocześnie,
- AI → AI teaching,
- kultury wielopokoleniowej,
- pełnej autonomii GhostNetwork,
- wszystkich typów operacji,
- zaawansowanego uczenia strategii,
- vector DB tylko dlatego, że „AI potrzebuje pamięci”.

Te elementy mają sens dopiero po udowodnieniu podstawowego kontraktu świata.

---

# 28. Architektoniczne kryterium GO / NO-GO

Projekt może przejść z trybu supervised do autonomicznego dopiero, gdy automatyczne testy potwierdzą jednocześnie:

1. AI nie otrzymuje danych niewidocznych dla równoważnego gracza ludzkiego.
2. AI nie może wybrać akcji spoza wystawionego Action Catalogu.
3. Action Gateway egzekwuje te same reguły dla `human` i `ai`.
4. Stara decyzja nie wykonuje się na niezgodnym stanie świata.
5. Awaria LLM nie modyfikuje świata.
6. Replay taska nie powoduje podwójnej akcji.
7. Wszystkie skutki autonomicznej decyzji posiadają pełny audit trail.

Jeżeli któregokolwiek punktu nie da się udowodnić testem, autonomia pozostaje wyłączona.

---

# 29. Rekomendacja końcowa

Budowałbym ten system od świata do modelu, a nie od modelu do świata.

Kolejność architektoniczna:

```text
1. wspólne komendy domenowe
2. visibility i semantic facts
3. action catalog
4. task engine
5. dry-run decision worker
6. supervised AI
7. ograniczona autonomia
8. pamięć i intent
9. kolejne domeny gameplayowe
10. zewnętrzni providerzy i wielu AI
```

W ten sposób nawet gdy model okaże się słabszy, wolniejszy albo zostanie później wymieniony, fundament systemu pozostanie poprawny.

**CHAOS ma egzekwować świat. Model ma tylko wybierać.**
