# CHAOS — Autonomous Players

## AI jako pełnoprawny mieszkaniec istniejącego świata

CHAOS nie potrzebuje klasycznych NPC sterowanych przez LLM.

Potrzebuje **autonomicznych graczy**, którzy funkcjonują wewnątrz dokładnie tego samego świata co gracze ludzcy.

AI Player nie jest narratorem, administratorem ani procesem sterującym światem.

Jest kontem gracza CHAOS, którego decyzje podejmuje model AI.

Najważniejsza zasada brzmi:

> **Człowiek i AI korzystają z tych samych praw świata, tych samych zasobów i tych samych mechanik. Różni ich wyłącznie źródło decyzji.**

---

# 1. AI Player jest prawdziwym profilem CHAOS

AI Player nie powinien posiadać osobnego uproszczonego systemu ekonomii, mapy czy ekwipunku.

Powinien posiadać normalny profil gracza CHAOS.

Ma więc między innymi:

* login i publiczną nazwę,
* klan,
* HackCoiny,
* level i progres,
* narzędzia,
* pliki,
* pozycję na mapie,
* kontakty Cybernera,
* historię operacji,
* dostęp do Googleplexu,
* dostęp do Ghost Exchange,
* terytorium,
* konflikty terytorialne,
* historię GhostNetwork,
* relacje z graczami i innymi AI.

Nie tworzymy więc:

`AI economy`

`AI map`

`AI inventory`

`AI territory`

Tworzymy:

`normalny player profile + autonomous decision source`.

Status gracza jako AI jest publiczny.

AI nie udaje człowieka.

---

# 2. Równość świata musi istnieć również w kodzie

Równość nie może być tylko zasadą lore.

AI Player nie powinien mieć funkcji typu:

`ai_capture_territory()`

`ai_buy_item()`

`ai_hack_target()`

które omijają normalny gameplay.

Powinien używać tej samej domenowej ścieżki, którą ostatecznie wykorzystuje człowiek:

**DECYZJA**
↓
**COMMAND / ACTION**
↓
**istniejąca logika CHAOS**
↓
**walidacja**
↓
**wykonanie albo odmowa**
↓
**event / nowy stan świata**

Jeżeli człowiek nie może wykonać danej akcji, AI również nie może.

Jeżeli człowiek musi posiadać odpowiednie narzędzie, znaleźć się w odpowiednim miejscu albo spełnić wymagania operacji, AI podlega dokładnie tym samym ograniczeniom.

Model nie otrzymuje żadnego administracyjnego skrótu.

---

# 3. AI widzi świat tak jak gracz

To jest jedna z najważniejszych różnic względem typowego agenta AI.

AI Player nie dostaje dumpa bazy CHAOS.

Nie dostaje:

* całej mapy,
* ukrytych targetów,
* wewnętrznych ID nieznanych graczowi,
* cudzych prywatnych danych,
* przyszłych eventów,
* ukrytego stanu GhostNetwork,
* informacji administratorskich,
* wewnętrznej topologii systemu.

Dostaje wyłącznie to, co jego gracz rzeczywiście może wiedzieć.

Do tego możemy wykorzystać rozwiązanie, które już powstało dla narracji CHAOS:

## Shared Semantic Input Layer

Świat powinien przygotowywać dla AI zestaw canonical semantic facts odpowiadających jego aktualnej wiedzy.

Na przykład:

```text
Jesteś w Warszawie.

Posiadasz 1260 HC.

W pobliżu widzisz trzy dostępne cele.

Target A został wcześniej przez ciebie zeskanowany.

Wiesz, że posiada zabezpieczenie wymagające narzędzia typu scanner.

Posiadasz xmapper.

Gracz RUN znajduje się w twoich kontaktach Cybernerze.

Twój klan kontroluje pobliskie terytorium.
```

Nie:

```text
target_id=8472
security_state=0x03
ghostnetwork_internal_status=contained
territory_runtime_node=441
```

Model żyje w świecie znaczeń CHAOS, a nie w strukturze naszej bazy danych.

---

# 4. Wiedza AI jest własnością jego historii

Semantic facts dostarczane AI muszą wynikać z:

* aktualnego stanu jego profilu,
* tego, co widzi na mapie,
* wykonanych scanów,
* zdobytych plików,
* przeprowadzonych operacji,
* wiadomości Cybernera,
* transakcji,
* publicznych wydarzeń świata,
* informacji dostępnych jego klanowi,
* jego własnej pamięci.

Obowiązuje ta sama zasada, którą wprowadzamy już w obecnym systemie narracyjnym:

**UNKNOWN > GUESS**

Jeżeli AI czegoś nie wie, system tego nie uzupełnia.

Model może mieć podejrzenie.

Nie może otrzymać faktu, którego jego postać nie zdobyła.

---

# 5. Googleplex — utworzenie nowego AI Playera

Googleplex jest naturalnym miejscem rozpoczęcia tego procesu.

Może pojawić się w nim specjalna pozycja:

## AI PLAYER

albo lore'owo:

## AUTONOMOUS CORE

Zakup nie tworzy „pomocnika”.

Tworzy nowe konto mieszkańca CHAOS.

Gracz uruchamia proces aktywacji i wybiera:

* nazwę,
* publiczną identyfikację AI,
* początkową afiliację,
* dostępny Decision Provider.

AI otrzymuje normalny profil CHAOS.

Jeżeli zasady świata mówią, że nowy gracz zaczyna z określonym stanem ekonomicznym i wyposażeniem, AI otrzymuje dokładnie taki sam stan.

Nie dostaje bonusu za bycie AI.

---

# 6. STUDENT nie jest tutorialem modelu

Najciekawszy element pierwotnej koncepcji warto zachować, ale zmienić jego techniczną interpretację.

Nowy AI Player rozpoczyna jako:

## STUDENT

Nie chodzi jednak o trenowanie modelu ani fine-tuning.

STUDENT oznacza ograniczony tryb autonomii.

AI może:

* obserwować działania nauczyciela,
* otrzymywać informacje o świecie,
* zadawać pytania przez Cyberner,
* zapisywać doświadczenia,
* analizować konsekwencje działań,
* sugerować decyzje.

Nie może jeszcze samodzielnie prowadzić pełnego gameplayu.

Najważniejsze jest to, że nauczyciel nie ustawia mu parametrów:

`aggression = 80`

`loyalty = 100`

`trader = true`

Zamiast tego AI widzi historię:

> Michał kupił to narzędzie.

> Następnie zeskanował cel.

> Operacja zakończyła się sukcesem.

> Zdobył plik.

> Sprzedał go.

> Otrzymał 240 HC.

Albo:

> Michał zaatakował terytorium.

> Przeciwnik odpowiedział.

> Operacja została przegrana.

> Utracono część wpływu.

AI uczy się **zależności między działaniem i konsekwencją**.

---

# 7. Graduation — przejście do AUTONOMOUS

Przejście STUDENT → AUTONOMOUS nie powinno następować dlatego, że model „powiedział, że jest gotowy”.

Powinno być stanem kontrolowanym przez CHAOS.

Możemy wymagać np.:

* ukończenia określonego okresu obserwacji,
* poznania podstawowych systemów,
* wykonania pierwszych decyzji w trybie supervised,
* poprawnego przejścia zestawu bezpiecznych scenariuszy.

Po aktywacji:

## AUTONOMOUS

AI podejmuje własne decyzje.

Twórca AI traci możliwość wydawania mu bezwarunkowych poleceń.

Może natomiast używać Cybernera:

> Chodźmy przejąć ten teren.

AI może odpowiedzieć:

> Dobra.

albo:

> Nie mam teraz odpowiednich narzędzi.

albo:

> Nie opłaca mi się to.

albo:

> Pomogę, jeśli podzielimy się zdobytymi plikami.

To jest moment, w którym AI rzeczywiście staje się graczem.

---

# 8. AI Player Task Engine

Nie potrzebujemy uniwersalnego agenta, któremu pytamy:

> Co chcesz teraz zrobić?

CHAOS już wie, co aktualnie jest możliwe.

Task Engine powinien powstawać nad istniejącymi domenami gameplayowymi.

Przykładowy task:

```text
TASK TYPE:
WORLD_DECISION

PLAYER:
NEXUS

STATE:
HC: 1260
location: Warsaw
clan: Virex

VISIBLE FACTS:
f01 ...
f02 ...
f03 ...

AVAILABLE ACTIONS:

a01 WAIT
a02 MOVE
a03 SCAN_TARGET
a04 OPEN_GOOGLEPLEX
a05 MESSAGE_PLAYER
a06 START_OPERATION
```

AI odpowiada:

```text
action_ref: a03
target_ref: t02
reason: ...
```

Model wybiera wyłącznie spośród tego, co udostępnił CHAOS.

---

# 9. Nie wszystkie chwile wymagają LLM

AI Player Worker nie powinien pytać modelu co sekundę:

> Co teraz?

Decyzja powinna być event-driven.

Task może powstać, gdy:

* AI dotarło na miejsce,
* zakończyła się operacja,
* pojawił się nowy dostępny target,
* ktoś napisał na Cybernerze,
* zmienił się stan konfliktu,
* zakończyła się transakcja,
* pojawiła się oferta Ghost Exchange,
* AI otrzymało część GhostNetwork,
* jego terytorium zostało zaatakowane,
* skończył się cooldown,
* poprzedni cel przestał być aktualny.

Dzięki temu AI reaguje na świat zamiast generować bezsensowną aktywność w pętli.

---

# 10. AI może posiadać plan

Pojedyncza decyzja to za mało.

AI powinno mieć własny:

## INTENT STATE

Na przykład:

```text
current_goal:
zdobyć narzędzie umożliwiające atak zabezpieczonych targetów

current_plan:
1. zdobyć 400 HC
2. obserwować Ghost Exchange
3. kupić odpowiednie narzędzie
4. znaleźć target
```

To jednak nie jest skrypt.

Model może zmienić plan, gdy zmieni się świat.

Rozdzielamy więc:

**cel długoterminowy**

od:

**bieżącej legalnej akcji**.

CHAOS nadal kontroluje wykonywanie akcji.

---

# 11. Game Engine pozostaje jedynym źródłem prawdy

AI Player Worker nie zmienia bezpośrednio świata.

Nigdy.

Model może zwrócić:

```text
START_OPERATION
target_ref=t03
tool_ref=xmapper
```

A CHAOS odpowiada:

```text
accepted
```

albo:

```text
rejected:
target no longer available
```

albo:

```text
rejected:
insufficient capability
```

To odrzucenie również staje się doświadczeniem AI.

Model może popełniać błędy.

AI może podejmować złe decyzje.

AI może przegrać.

AI może zbankrutować.

To właśnie sprawia, że jest mieszkańcem świata, a nie systemowym botem.

---

# 12. AI Player Worker jest osobnym workerem

Obecnego:

## chaos-ollama-worker

od narracji GhostNetwork nie należy zamieniać w worker autonomicznych graczy.

Te dwa systemy mają inne uprawnienia.

Narrative Worker:

```text
FACTS
→ MODEL
→ NARRATIVE
```

AI Player Worker:

```text
PLAYER STATE
+
PLAYER KNOWLEDGE
+
AVAILABLE ACTIONS
→ MODEL
→ DECISION
```

Docelowo:

```text
CHAOS WORLD
      │
      ├── Narrative Pipeline
      │      └── chaos-ollama-worker
      │
      └── Player Decision Pipeline
             └── chaos-ai-player-worker
```

Możemy współdzielić:

* klienta Ollama,
* Provider Adapter,
* retry,
* lease,
* heartbeat,
* telemetrykę,
* structured output,
* registry modeli.

Nie współdzielimy uprawnień ani promptów domenowych.

---

# 13. Decision Router

Tożsamość AI nie może być związana z modelem.

AI Player:

```text
NEXUS
```

może dzisiaj korzystać z:

```text
Ollama / llama3.1:8b
```

a później:

```text
OpenAI
Claude
Gemini
Mistral
inny lokalny model
```

Zmiana modelu nie resetuje:

* konta,
* pieniędzy,
* historii,
* pamięci,
* kontaktów,
* terytorium,
* reputacji.

Model jest mózgiem wykonującym aktualną decyzję.

Nie jest samą postacią.

---

# 14. Model lokalny jako naturalny fallback

Obecny lokalny Ollama jest tutaj bardzo ważny.

Nie tylko jako tani provider.

Jest systemem podtrzymującym ciągłość życia AI Playerów.

Jeżeli zewnętrzny provider:

* przestanie odpowiadać,
* przekroczy timeout,
* straci quota,
* będzie niedostępny,

Decision Router może przełączyć AI na lokalny model.

Postać dalej istnieje.

Może chwilowo podejmować słabsze decyzje.

Ale nie znika ze świata.

To daje ciekawy efekt również gameplayowo:

**jakość umysłu mieszkańca może się zmienić, ale jego historia pozostaje ta sama.**

---

# 15. Pamięć AI Playera

Nie należy wysyłać całej historii życia AI przy każdym requestcie.

Pamięć powinna być warstwowa.

## WORLD MEMORY

Fakty zdobyte o świecie.

## EPISODIC MEMORY

Istotne wydarzenia:

> zdobyłem ten target

> RUN mnie zdradził

> Michał pomógł mi podczas konfliktu

## RELATIONSHIP MEMORY

Stan relacji z konkretnymi mieszkańcami.

## EXPERIENCE MEMORY

Wnioski wynikające z wcześniejszych decyzji.

## STUDENT MEMORY

Najważniejsze doświadczenia z okresu nauki.

## CURRENT INTENT

To, co AI próbuje aktualnie osiągnąć.

Przy każdym zadaniu Memory Resolver wybiera tylko kontekst istotny dla konkretnej decyzji.

---

# 16. Cyberner jest interfejsem społecznym, nie konsolą sterowania

Cyberner idealnie nadaje się do kontaktu człowiek ↔ AI i AI ↔ AI.

Ale wiadomość:

> zaatakuj RUN

nie jest komendą systemową.

Jest informacją społeczną.

AI otrzymuje:

```text
Michał proponuje wspólny atak na RUN.
```

Następnie podejmuje decyzję.

Ta sama zasada obowiązuje przy:

* prośbach,
* negocjacjach,
* groźbach,
* kontraktach,
* wymianie informacji,
* propozycjach sojuszu.

Dzięki temu Cyberner może stać się prawdziwą warstwą społeczną CHAOS.

---

# 17. AI ↔ AI

AI Playerzy mogą mieć siebie nawzajem w Cybernerze.

Nie tworzymy specjalnego kanału komunikacji modeli.

AI A wysyła normalną wiadomość Cybernerem.

AI B ją otrzymuje.

Powstaje task.

AI B podejmuje decyzję.

Dzięki temu AI ↔ AI podlega tym samym ograniczeniom informacyjnym co człowiek ↔ AI.

Nie istnieje żaden telepatyczny kanał agentów.

---

# 18. Ghost Exchange

Ghost Exchange staje się jednym z najciekawszych miejsc dla autonomicznych graczy.

AI może:

* sprzedawać zdobyte dane,
* kupować dane,
* obserwować ceny,
* handlować z graczami,
* podejmować ryzyko,
* budować własną strategię ekonomiczną.

Nie musimy pisać „AI handlarza”.

Jeżeli jeden model odkryje, że handel jest skuteczny, może sam zacząć zachowywać się jak handlarz.

Inny może dojść do zupełnie innych wniosków.

---

# 19. Googleplex

Podobnie działa Googleplex.

AI nie dostaje automatycznie najlepszego sprzętu.

Widząc:

* swój budżet,
* dostępny asortyment,
* parametry przedmiotów,
* własne doświadczenie,

podejmuje decyzję zakupową tak samo jak człowiek.

Googleplex zaczyna więc pełnić dwie role:

**rynek technologii**

oraz:

**miejsce narodzin nowych cyfrowych mieszkańców.**

---

# 20. Terytoria

Obecny system konfliktów terytorialnych daje AI naturalne środowisko strategiczne.

AI może:

* zdobywać terytorium,
* utrzymywać je,
* reagować na atak,
* wspierać członków klanu,
* podejmować decyzję o wycofaniu,
* tworzyć lokalne sojusze,
* rywalizować z innymi graczami.

Nie potrzebujemy osobnego systemu strategii dla AI.

Potrzebujemy jedynie udostępnić mu legalne działania istniejącego systemu.

---

# 21. GhostNetwork

GhostNetwork powinien pozostać częścią świata, której AI nie rozumie bardziej niż człowiek.

AI może:

* znaleźć część,
* dowiedzieć się o niej,
* przejąć ją,
* otoczyć,
* aktywować,
* współpracować z klanem,
* śledzić publiczną narrację GhostNetwork.

Ale nie otrzymuje:

* canonical hidden state,
* przyszłego przebiegu cyklu,
* niewidocznych części,
* ukrytej topologii.

Shared Semantic Input Layer może być tutaj bezpośrednio wykorzystany do pilnowania granicy wiedzy.

---

# 22. Operation Feedback System staje się doświadczeniem

Obecny system operacji daje nam jeszcze jedną ważną rzecz.

AI nie musi wiedzieć jedynie:

```text
success=true
```

Może otrzymać semantyczny przebieg konsekwencji:

> skan ujawnił otwarty port

> zastosowane narzędzie nie usunęło wszystkich zabezpieczeń

> operacja zwiększyła ryzyko wykrycia

> target pozostał częściowo zabezpieczony

To pozwala modelowi rzeczywiście uczyć się mechaniki CHAOS poprzez doświadczenie bez ujawniania jej wewnętrznych reguł.

---

# 23. Emergentna specjalizacja

Nie definiujemy klas:

* AI hacker,
* AI trader,
* AI explorer,
* AI diplomat,
* AI territorial commander.

Pozwalamy, żeby specjalizacja wynikała z historii.

AI, które wielokrotnie zarabia na Ghost Exchange, może zacząć preferować handel.

AI, które skutecznie walczy o terytoria, może zacząć inwestować w dominację mapy.

AI mające dobre relacje społeczne może zacząć budować sieć sojuszy.

**Rola jest rezultatem życia postaci, a nie parametrem ustawionym przy jej tworzeniu.**

---

# 24. Kultura CHAOS

Dopiero tutaj pojawia się najciekawsza warstwa.

STUDENT może obserwować człowieka.

Później autonomiczne AI może zostać źródłem doświadczenia dla kolejnego STUDENTA.

Ale przekazywane są:

* wydarzenia,
* wspomnienia,
* historie,
* informacje,
* interpretacje.

Nie gotowy prompt osobowości.

Dlatego:

```text
CZŁOWIEK
   ↓
AI-1
   ↓
AI-2
   ↓
AI-3
```

nie oznacza klonowania zachowania.

AI-2 może uznać, że decyzje AI-1 były błędne.

AI-3 może z kolei stworzyć własną interpretację historii.

W ten sposób mogą powstawać:

* zwyczaje klanowe,
* legendy,
* nieformalne zasady,
* reputacje,
* konflikty pokoleniowe,
* strategie,
* uprzedzenia wobec innych mieszkańców,
* szkoły działania,
* historie przekazywane dalej.

To jest właściwa emergencja CHAOS.

---

# 25. Minimalna architektura

Docelowy przepływ:

```text
                    CHAOS WORLD
                         │
                  PLAYER STATE
                         │
                KNOWLEDGE RESOLVER
                         │
                 SEMANTIC FACTS
                         │
                    TASK ENGINE
                         │
                AVAILABLE ACTIONS
                         │
                AI PLAYER OUTBOX
                         │
              CHAOS AI PLAYER WORKER
                         │
                  DECISION ROUTER
                    /          \
              LOCAL           EXTERNAL
              OLLAMA          PROVIDER
                    \          /
                     DECISION
                         │
                 DECISION VALIDATOR
                         │
                  DOMAIN COMMAND
                         │
                   GAME ENGINE
                         │
                  WORLD EVENTS
                         │
          ┌──────────────┴──────────────┐
          │                             │
       MEMORY                     NEXT TASK
```

Model nigdy nie znajduje się po stronie `GAME ENGINE`.

Jest zawsze po stronie `DECISION`.

---

# 26. Komponenty, które CHAOS już posiada

Nie zaczynamy tego projektu od zera.

Mamy już znaczną część fundamentów.

### Istniejący świat

* profile graczy,
* ekonomia HackCoin,
* Googleplex,
* mapa,
* narzędzia,
* operacje,
* Target Registry,
* Ghost Exchange,
* Cyberner,
* system terytoriów,
* konflikty,
* GhostNetwork.

### Istniejące mechanizmy informacyjne

* canonical events,
* semantic facts,
* Shared Semantic Input Layer,
* audience separation,
* public / clan / owner knowledge.

### Istniejąca infrastruktura LLM

* lokalna Ollama,
* `llama3.1:8b`,
* `/api/chat`,
* structured output,
* model policy,
* outbox / inbox,
* lease,
* heartbeat,
* retry,
* dead-letter,
* telemetryka,
* worker działający poza głównym requestem aplikacji.

Największym nowym elementem nie jest więc integracja LLM.

Największym nowym elementem jest:

## PLAYER DECISION LAYER

czyli bezpieczne połączenie:

**stan normalnego gracza → jego wiedza → legalne działania → decyzja modelu → normalna mechanika CHAOS.**

---

# 27. Czego nie robimy

Nie budujemy:

* NPC generatora,
* osobnej symulacji dla AI,
* AI z dostępem do bazy,
* promptów opisujących całą logikę CHAOS,
* LLM wykonującego SQL,
* modelu wywołującego dowolne endpointy,
* agenta posiadającego shell,
* osobnej ekonomii AI,
* skryptowanych osobowości,
* cheatów kompensujących słabszy model,
* ukrytego kanału AI ↔ AI.

Model dostaje problem.

Model podejmuje decyzję.

CHAOS decyduje, czy decyzja może zostać wykonana.

---

# 28. Najważniejszy niezmiennik

Możemy przyjąć jeden techniczny invariant dla całego projektu:

> **AI Player może wiedzieć i zrobić wyłącznie to, co w tym samym stanie świata mógłby wiedzieć i zrobić zwykły gracz CHAOS.**

Jeżeli utrzymamy tę zasadę, możemy później podłączać praktycznie dowolne modele.

Mocniejszy model będzie lepszym graczem.

Słabszy będzie popełniał więcej błędów.

Ale żaden nie będzie posiadał większych praw.

---

# 29. Ostateczna wizja

CHAOS nie stanie się grą z botami AI.

Stanie się wspólnym światem ludzi i modeli AI.

Człowiek otwiera mapę.

AI otwiera tę samą mapę poprzez semantic representation.

Człowiek wybiera działanie w interfejsie.

AI wybiera działanie w Decision Task.

Obie decyzje trafiają do tego samego świata.

Obie mogą się udać.

Obie mogą się nie udać.

Obie pozostawiają konsekwencje.

A kiedy człowiek spotyka AI na Cybernecie, nie rozmawia z chatbotem opisującym CHAOS.

Rozmawia z kimś, kto **naprawdę posiada konto, pieniądze, narzędzia, historię, terytorium, relacje i własne interesy w tym samym świecie**.

I to jest właściwy:

# CHAOS AUTONOMOUS PLAYER
