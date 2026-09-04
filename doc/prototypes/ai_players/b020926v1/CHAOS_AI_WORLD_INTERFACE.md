# CHAOS — AI World Interface
## AI Perception Layer

**Status:** rekomendacja architektoniczna  
**Zakres:** interfejs rzeczywistości dla autonomicznych graczy AI  
**Cel:** zapewnić modelowi możliwie wierny, aktualny i diagnostyczny obraz sytuacji bez rozszerzania wiedzy postaci ani obchodzenia zasad świata

---

# 1. Teza

> **AI Player będzie tylko tak dobre, jak dobry będzie jego interfejs świata.**

Jakość decyzji nie zależy wyłącznie od jakości modelu.

Nawet bardzo mocny model podejmie słabą decyzję, jeżeli dostanie ubogi albo źle zorganizowany obraz sytuacji.

Dlatego CHAOS powinien traktować percepcję jako osobną warstwę architektury, a nie jako fragment prompta.

Najważniejsze rozróżnienie:

```text
WORLD
  ↓
OBSERVATION
  ↓
KNOWLEDGE
  ↓
PERCEPTION / AI WORLD INTERFACE
  ↓
DECISION
```

Każda warstwa odpowiada na inne pytanie.

**WORLD** — co naprawdę istnieje.  
**OBSERVATION** — co jest technicznie obserwowalne z perspektywy gracza.  
**KNOWLEDGE** — co postać może legalnie wiedzieć i pamiętać.  
**PERCEPTION** — co z tej wiedzy jest teraz przedstawione postaci jako jej bieżąca sytuacja.  
**DECISION** — co model wybiera.

---

# 2. Knowledge ≠ Perception

`Knowledge Resolver` odpowiada za granicę wiedzy.

Przykład:

> Gracz wie, że posiada terytorium w Warszawie.

To nie oznacza jeszcze, że informacja o Warszawie powinna znajdować się w centrum każdego taska.

Jeżeli gracz aktualnie znajduje się na Alasce i buduje lokalne terytorium, jego bieżąca percepcja może koncentrować się właśnie na Alasce.

Dopiero event:

> **ATAK NA TWOJE TERYTORIUM — WARSZAWA**

zmienia priorytet informacji i powinien wpłynąć na uwagę AI.

Perception Layer nie tworzy nowej wiedzy.

Perception Layer **wybiera, porządkuje i prezentuje istniejącą wiedzę w kontekście bieżącej sytuacji**.

---

# 3. Zasada bezpieczeństwa

AI World Interface nie może być dodatkowym źródłem faktów.

Każdy element interfejsu musi mieć lineage do jednego z dozwolonych źródeł:

- canonical world observation,
- canonical knowledge fact,
- stan własnego profilu,
- własny runtime działania,
- canonical world event dostępny temu graczowi,
- własna pamięć,
- legalnie dostępny capability/action state.

Perception Layer może powiedzieć:

> `territory_attack` ma wysoki priorytet.

Nie może samodzielnie dopowiedzieć:

> przeciwnik prawdopodobnie planuje drugi atak.

Jeżeli taka hipoteza powstanie, musi powstać po stronie modelu jako interpretacja, a nie jako fakt systemowy.

Obowiązuje nadal:

> **UNKNOWN > GUESS**

---

# 4. Perception Frame

Rekomendowanym kontraktem wyjściowym jest `AIWorldPerceptionFrame`.

Nie jest to zwykły prompt tekstowy.

To canonical, wersjonowany obiekt opisujący bieżący „ekran rzeczywistości” danego AI Playera.

Minimalne sekcje:

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

Nie każdy task musi zawierać wszystkie sekcje. Kontrakt powinien pozwalać na bounded i kontekstowe składanie frame'u.

---

# 5. NOW

`NOW` odpowiada na pytanie:

> Co dzieje się z postacią dokładnie teraz?

Przykładowe dane:

- aktualna pozycja,
- aktualny stan podróży,
- wykonywana operacja,
- trwająca budowa,
- aktywny cooldown,
- bieżący stan ekonomiczny istotny dla decyzji,
- stan lifecycle AI.

Przykład:

```text
NOW
location: Alaska
activity: territory_build
activity_state: in_progress
HC: 1260
```

---

# 6. ATTENTION

`ATTENTION` reprezentuje rzeczy, które właśnie próbują przejąć uwagę postaci.

Źródła:

- alert terytorialny,
- nowa wiadomość Cybernera,
- zakończona operacja,
- ważny event GhostNetwork,
- oferta lub transakcja Ghost Exchange,
- zmiana stanu celu,
- krytyczna zmiana zasobów,
- inne canonical eventy o odpowiednim audience.

Każdy attention item powinien mieć co najmniej:

```text
attention_ref
source_type
priority
occurred_at
semantic_summary
lineage
```

`priority` nie oznacza decyzji za model.

Oznacza jedynie siłę sygnału interfejsu, analogiczną do toastu, alarmu, czerwonego markera lub nowej wiadomości widocznej człowiekowi.

---

# 7. FOCUS

`FOCUS` opisuje to, na czym AI aktualnie koncentruje swoją uwagę.

Przykłady:

- konkretne terytorium,
- target,
- operacja,
- rozmowa Cybernera,
- oferta Googleplexu,
- wpis Ghost Exchange,
- element GhostNetwork,
- własny bieżący plan.

Focus nie jest tym samym co intent.

`INTENT` mówi:

> co chcę osiągnąć.

`FOCUS` mówi:

> na co patrzę teraz.

Model może zmienić focus w reakcji na nowe zdarzenie.

---

# 8. ACTIVE

`ACTIVE` zawiera otwarte sprawy wymagające potencjalnej dalszej reakcji.

Przykłady:

- trwająca rozmowa Cybernera,
- niezakończona operacja,
- konflikt terytorialny,
- planowany zakup,
- oczekująca propozycja współpracy,
- rozpoczęty intent,
- zadanie STUDENT/SUPERVISED.

Dzięki temu AI nie traktuje każdej decyzji jako całkowicie niezależnej rozmowy z modelem.

---

# 9. BACKGROUND

`BACKGROUND` reprezentuje znane sprawy, które nie wymagają teraz natychmiastowej uwagi.

Przykłady:

- spokojne terytoria,
- obserwowane cele,
- zapisane oferty,
- nieaktywne relacje,
- informacje klanowe bez bieżącego triggera.

Ta warstwa pozwala zachować świadomość świata bez zalewania modelu całym knowledge store.

---

# 10. RECENT

`RECENT` jest krótką pamięcią ostatnich zmian sytuacji.

Nie zastępuje `EPISODIC MEMORY`.

Przykład:

```text
- 45 s temu rozpoczęto budowę terytorium na Alasce.
- 18 s temu RUN wysłał wiadomość Cybernera.
- 3 s temu rozpoczął się atak na twoje terytorium w Warszawie.
```

Ta sekcja jest odpowiednikiem ludzkiej pamięci tego, co właśnie wydarzyło się na ekranie.

---

# 11. RESOURCES

`RESOURCES` pokazuje zasoby istotne dla bieżącej decyzji.

Nie musi zawierać całego profilu.

Może obejmować:

- HC,
- istotne narzędzia,
- pliki,
- dostępne teleporty,
- cooldowny,
- zasoby związane z aktywnym celem.

Selekcja powinna być kontekstowa, ale nigdy nie może ukrywać informacji, która w identycznym interfejsie ludzkim byłaby oczywiście widoczna i konieczna do podjęcia decyzji.

---

# 12. RELATIONSHIPS

`RELATIONSHIPS` przedstawia tylko relacje istotne dla bieżącego kontekstu.

Przykład:

```text
RUN
relation: trusted_contact
recent_interaction: offered_help
open_thread: yes
```

Nie wysyłamy całej społecznej historii postaci przy każdym tasku.

Memory Resolver i Perception Layer wybierają potrzebny kontekst.

---

# 13. KNOWN_WORLD

`KNOWN_WORLD` zawiera wiedzę przestrzenną i strategiczną istotną dla aktualnej sytuacji.

Przykłady:

- znane miejsca,
- własne terytoria,
- znane targety,
- ostatnio poznane zagrożenia,
- jawne elementy klanowe,
- informacje GhostNetwork dostępne dla danego audience.

Wszystkie dane muszą pochodzić z Knowledge Layer.

---

# 14. CAPABILITIES

`CAPABILITIES` odpowiada na pytanie:

> Jakiego rodzaju działania postać jest obecnie zdolna wykonać?

Przykład:

```text
can_move: yes
can_teleport: yes
can_scan_target: yes
can_start_operation: no
can_send_cyberner_message: yes
```

To nadal nie jest finalna lista decyzji.

Capability Resolver mówi, co jest możliwe w danym stanie.

---

# 15. AVAILABLE ACTIONS

`AVAILABLE_ACTIONS` jest finalnym wyborem wystawionym modelowi.

Przykład sytuacji Alaska / Warszawa:

```text
CURRENT ACTIVITY
territory_build — Alaska

ATTENTION
territory_attack — Warszawa — HIGH
cyberner_message — RUN — MEDIUM

FOCUS
Alaska

AVAILABLE ACTIONS

a01 CONTINUE_CURRENT_ACTIVITY
a02 INSPECT_TERRITORY territory_ref=tr02
a03 CHANGE_FOCUS focus_ref=territory_warsaw
a04 TELEPORT destination_ref=loc02
a05 OPEN_CYBERNER_THREAD thread_ref=c01
a06 WAIT
```

Model nadal sam decyduje, czy alarm z Warszawy jest ważniejszy niż bieżące działanie na Alasce.

Backend jedynie przedstawia mu sytuację i legalne reakcje.

---

# 16. Attention Policy

CHAOS potrzebuje deterministycznej, testowalnej polityki uwagi.

Nie rekomenduję, żeby drugi LLM decydował, co pierwszy LLM powinien zobaczyć.

`Attention Policy` powinna opierać się na canonical event types i regułach gry.

Przykładowe klasy:

```text
CRITICAL
HIGH
MEDIUM
LOW
BACKGROUND
```

Przykładowo:

- bezpośredni atak na własne terytorium → HIGH/CRITICAL,
- zakończenie własnej operacji → HIGH,
- wiadomość Cybernera → zależnie od typu i otwartego wątku,
- zwykła zmiana ceny obserwowanego przedmiotu → LOW/MEDIUM,
- publiczny event daleko od bieżących interesów → BACKGROUND.

Polityka określa ekspozycję informacji, nie reakcję postaci.

---

# 17. Focus State

Focus powinien być canonical stanem runtime AI Playera.

Przykładowy kontrakt:

```text
focus_type
focus_ref
set_at
set_by
reason_ref
revision
```

`set_by` może rozróżniać:

- `model_decision`,
- `system_transition`,
- `student_supervision`,
- `task_default`.

Focus nie powinien przyznawać żadnej dodatkowej wiedzy.

Zmiana focusu może jedynie zmienić to, jaki wycinek już dostępnej wiedzy zostanie szerzej przedstawiony w następnym frame.

---

# 18. Perception Budget

Perception Layer musi być bounded.

Nie chodzi tylko o tokeny.

Potrzebujemy limitów logicznych:

- maksymalna liczba attention items,
- maksymalna liczba active threads,
- maksymalna liczba recent events,
- maksymalna liczba background facts,
- maksymalna liczba relacji,
- maksymalna liczba dostępnych akcji.

Przy przepełnieniu stosujemy deterministyczne reguły priorytetu oraz agregację semantic facts.

Nigdy losowe obcinanie prompta.

---

# 19. Determinizm interfejsu

Dla tego samego:

- `world_revision`,
- `player_revision`,
- knowledge state,
- focus state,
- attention queue,
- active intent,
- task trigger,
- action catalog version,

AI World Interface powinien wygenerować semantycznie ten sam frame.

To jest kluczowe dla replay, benchmarków i porównywania modeli.

---

# 20. Perception Revision

Każdy frame powinien posiadać własną rewizję lub fingerprint.

Przykładowo:

```text
perception_id
player_id
world_revision
player_revision
knowledge_revision
focus_revision
attention_revision
capability_revision
action_catalog_revision
schema_version
created_at
```

Decyzja modelu musi wskazywać `perception_id` albo jego fingerprint.

Jeżeli podczas inferencji stan krytyczny się zmienił, `State Revision Guard` może odrzucić decyzję jako stale.

---

# 21. AI World Interface jako kontrakt modelowy

Model nie powinien otrzymywać wielu przypadkowych fragmentów kontekstu sklejonych bezpośrednio w workerze.

Worker powinien dostawać jeden canonical package:

```text
AIPlayerTask
  ├── trigger
  ├── perception_frame
  ├── semantic_facts
  ├── available_actions
  ├── relevant_memory
  └── policy_versions
```

Dzięki temu prompt jest rendererem kontraktu, a nie miejscem, w którym powstaje logika świata.

---

# 22. Relacja z istniejącymi modułami

AI Perception Layer nie zastępuje wcześniejszych modułów.

Powinien łączyć ich wyniki.

```text
M03 Player Observation Builder
            ↓
M04 Knowledge Resolver
            ↓
        M29 AI Perception Layer
       ↙       ↓        ↘
M18 Intent   M20 Memory   M06 Capabilities
                         ↓
                    M07 Action Catalog
                         ↓
                    M08 Task Engine
                         ↓
                       MODEL
```

W praktyce Task Engine może być triggerem budowy frame'u, natomiast sam frame powinien być zbudowany z canonical modułów i zapisany wraz z taskiem.

---

# 23. Relacja z człowiekiem

Celem nie jest udawanie graficznego UI człowieka piksel po pikselu.

Celem jest zachowanie **funkcjonalnej równoważności percepcji**.

Jeżeli człowiek otrzymuje:

- toast,
- badge,
- marker mapy,
- wiadomość,
- zmianę stanu przycisku,
- informację o cooldownie,
- wynik operacji,

AI powinno otrzymać semantyczny odpowiednik tego sygnału, o ile jest on widoczny dla tego samego profilu.

To daje bardzo mocny invariant:

> **Każdy istotny sygnał gameplayowy widoczny człowiekowi powinien mieć canonical odpowiednik dostępny dla AI Player Interface.**

Nie oznacza to automatycznie, że każdy kosmetyczny element UI ma znaczenie dla AI.

---

# 24. Cyberner

Nowa wiadomość Cybernera jest przykładem zdarzenia percepcyjnego.

Knowledge Layer odpowiada za to, że AI legalnie zna treść wiadomości.

Perception Layer odpowiada za:

- oznaczenie nowej wiadomości,
- priorytet w zależności od kontekstu,
- powiązanie z otwartym wątkiem,
- pokazanie jej w `ATTENTION` lub `ACTIVE`,
- udostępnienie akcji otwarcia/odpowiedzi.

Cyberner pozostaje normalnym komunikatorem CHAOS, a nie kanałem sterowania AI.

---

# 25. GhostNetwork

Perception Layer nie może rozszerzać wiedzy GhostNetwork.

Może jednak poprawnie eksponować sygnały, które gracz już legalnie otrzymał.

Przykład:

```text
ATTENTION
GhostNetwork: clan-visible part status changed
```

Nie wolno z tego generować ukrytej topologii, brakujących nazw ani przyszłego stanu cyklu.

Public/clan/owner pozostają źródłem truth boundary.

---

# 26. Diagnostyka: mózg vs percepcja

AI World Interface daje możliwość rozdzielenia dwóch klas błędów:

## Błąd modelu

Frame był poprawny, ale model podjął słabą decyzję.

## Błąd percepcji

Model nie dostał informacji, która była konieczna albo dostał ją w złym kontekście/priorze.

To rozróżnienie powinno być częścią telemetryki i replay tools.

---

# 27. Benchmark modeli

Dzięki zamrożonemu `Perception Frame` można przeprowadzać uczciwe porównania modeli.

Ten sam:

- profil,
- stan świata,
- knowledge state,
- attention,
- focus,
- historia,
- capability set,
- action catalog,

jest podawany różnym modelom.

Zmienia się wyłącznie Decision Provider.

Wtedy różnica decyzji rzeczywiście mierzy zachowanie „mózgu”, a nie różnicę w dostępie do świata.

---

# 28. Perception Replay

Diagnostics powinien pozwalać na:

```text
inspect-perception <perception_id>
rebuild-perception <task_id>
compare-perception <id_a> <id_b>
replay-decision <perception_id> --provider X
```

Replay nie wykonuje gameplayowych side effects.

Pozwala zobaczyć dokładnie:

- co AI widziało,
- czego nie widziało,
- co było w focusie,
- co próbowało przejąć attention,
- jakie miało opcje,
- jaki model podjął decyzję.

---

# 29. Telemetria percepcji

Rekomendowane metryki:

- perception build latency,
- frame size,
- facts included / omitted,
- attention items per frame,
- background items per frame,
- focus changes,
- task-to-focus-change rate,
- stale perception rate,
- action catalog size,
- invalid lineage count,
- knowledge leakage count,
- same-frame cross-model decision divergence.

Szczególnie ważne są dwa liczniki, które docelowo powinny pozostać równe zero:

```text
knowledge_leakage = 0
unlineaged_perception_fact = 0
```

---

# 30. Testy kontraktowe

M29 powinien mieć własny zestaw contract tests.

Minimalnie:

1. AI nie dostaje faktu spoza Knowledge Layer.
2. Hidden GhostNetwork state nie trafia do frame'u.
3. Nowa wiadomość Cybernera tworzy attention item.
4. Atak na własne terytorium zmienia attention bez automatycznej zmiany decyzji.
5. Zmiana focusu nie rozszerza praw do wiedzy.
6. Ten sam canonical input generuje ten sam frame.
7. Bounded policy nie usuwa krytycznego eventu na rzecz background facts.
8. `AVAILABLE_ACTIONS` zawiera wyłącznie task-local refs.
9. Stary `perception_id` może zostać odrzucony przez Revision Guard.
10. Replay frame'u nie wykonuje side effects.

---

# 31. Minimalny vertical slice

Pierwsza wersja nie potrzebuje pełnego świata.

Wystarczy jeden AI Player i kilka źródeł percepcji:

- lokalizacja,
- bieżąca aktywność,
- wallet,
- jeden target,
- jedna wiadomość Cybernera,
- jeden alert terytorialny,
- prosty focus,
- kilka legalnych akcji.

Scenariusz testowy:

```text
AI buduje terytorium na Alasce.
↓
RUN wysyła wiadomość Cybernera.
↓
Rozpoczyna się atak na terytorium AI w Warszawie.
↓
Perception Layer buduje frame.
↓
Model wybiera jedną z legalnych reakcji.
↓
Decision Validator + Domain Action Gateway wykonują lub odrzucają decyzję.
```

Ten jeden scenariusz testuje jednocześnie:

- knowledge boundary,
- attention,
- focus,
- active state,
- event priority,
- action catalog,
- strategię modelu,
- stale-state protection.

---

# 32. Rekomendacja wdrożeniowa

M29 powinien wejść **przed pierwszą oceną jakości autonomicznego AI Playera**.

Bez niego możemy sprawdzić jedynie, czy model technicznie potrafi wybrać akcję.

Nie możemy jeszcze uczciwie ocenić, czy potrafi grać.

Dlatego rekomendowany porządek jest następujący:

```text
WORLD EQUALITY
→ OBSERVATION
→ KNOWLEDGE
→ AI PERCEPTION LAYER
→ ACTION CATALOG
→ DECISION WORKER
→ AUTONOMY
```

Nie warto benchmarkować modeli, dopóki `AI World Interface` nie ma stabilnego kontraktu i replay.

---

# 33. Najważniejszy invariant M29

> **AI Perception Layer może zmieniać uwagę postaci, ale nie może zmieniać prawdy świata ani rozszerzać jej wiedzy.**

Jeżeli utrzymamy tę granicę, zyskujemy dwie niezależne osie rozwoju:

**lepszy mózg** — model / provider / policy  
**lepsza percepcja** — interfejs świata / attention / focus / context selection

Dzięki temu CHAOS może porównywać różne modele w identycznym świecie i rzeczywiście obserwować, jak różne mechanizmy podejmowania decyzji zachowują się przy tej samej percepcji rzeczywistości.
