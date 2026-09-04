# CHAOS — Autonomous Players
## Rekomendacja architektoniczna 2.0

**Status:** docelowa rekomendacja projektowa  
**Zakres:** autonomiczni gracze AI korzystający z pełnego środowiska CHAOS  
**Data:** 2026-09-04  
**Dokument nadrzędny:** `CHAOS_AUTONOMOUS_PLAYER.md`

---

# 1. Decyzja architektoniczna

Rekomendowane rozwiązanie składa się z:

1. **jednego wspólnego świata CHAOS**,  
2. **dwóch klientów tego świata** — graficznego dla człowieka i semantycznego dla AI,  
3. **jednego wspólnego wejścia do działań domenowych**,  
4. **osobnego workera decyzyjnego AI**,  
5. **wymiennego modelu będącego wyłącznie źródłem decyzji**.

Nie tworzymy równoległego gameplayu dla AI.

Nie próbujemy również opisać całej gry w jednym promptcie.

Budujemy **CHAOS AI Runtime Client**: semantyczny odpowiednik pulpitu, Mapy, Terminala, WebDragons, Plików, Cybernera, Walleta, aplikacji, Pro Toolsów i dynamicznych zdolności świata.

Najważniejszy invariant:

> **AI Player może wiedzieć, postrzegać i zrobić wyłącznie to, co w równoważnym stanie mógłby wiedzieć, postrzegać i zrobić zwykły gracz CHAOS, z uwzględnieniem posiadanych przez niego aplikacji, progresu, aktualnych efektów i ograniczeń.**

---

# 2. Jeden świat, dwa klienty

Docelowy układ:

```text
                         CHAOS WORLD
                              │
                    CANONICAL DOMAIN STATE
                              │
             ┌────────────────┴────────────────┐
             │                                 │
     HUMAN DESKTOP CLIENT              AI RUNTIME CLIENT
     HTML / JS / Leaflet               Semantic Desktop
     okna / ikony / tekst              surfaces / refs / actions
             │                                 │
             └────────────────┬────────────────┘
                              │
                    DOMAIN ACTION GATEWAY
                              │
                         GAME ENGINE
                              │
                        WORLD EVENTS
```

Różnica dotyczy prezentacji oraz źródła decyzji.

Reguły ruchu, operacji, ekonomii, terytoriów, plików, aplikacji, incydentów, służb i GhostNetwork pozostają wspólne.

---

# 3. Cztery płaszczyzny systemu

## 3.1. Gameplay Plane

To istniejący świat:

- profile,
- pieniądze,
- level i respekt,
- Mapa,
- Target Registry,
- podróże,
- Recon,
- operacje,
- narzędzia,
- pliki,
- Googleplex,
- Ghost Exchange,
- BlackNet,
- Cyberner,
- terytoria,
- konflikty,
- incydenty,
- służby,
- GhostNetwork.

Gameplay Plane jest jedynym źródłem prawdy o skutkach.

## 3.2. Interface and Perception Plane

Tłumaczy canonical stan na interfejs dostępny konkretnemu profilowi.

Dla człowieka renderuje UI.

Dla AI buduje:

- Desktop Session,
- Semantic Surfaces aplikacji,
- Perception Frame,
- uwagę,
- focus,
- widoczne interakcje,
- semantyczną Mapę.

## 3.3. Decision Plane

Obejmuje:

- event-driven Task Engine,
- Interaction Session,
- osobny `chaos-ai-player-worker`,
- Decision Router,
- model,
- structured decision contract.

Model nie ma bezpośredniego dostępu do Gameplay Plane.

## 3.4. Control and Audit Plane

Obejmuje:

- lifecycle STUDENT/AUTONOMOUS,
- kill switche,
- limity,
- telemetrię,
- replay,
- parity tests,
- provider policy,
- audyt każdej decyzji.

---

# 4. Główna zmiana względem pierwszej koncepcji

Pierwsza wersja zakładała głównie:

```text
stan gracza
+ wiedza
+ lista legalnych akcji
→ model
```

To jest poprawne dla bardzo małego vertical slice, ale niewystarczające dla prawdziwego CHAOS.

Pełna gra posiada:

- wiele aplikacji,
- kilka alternatywnych ścieżek do tego samego celu,
- Terminal i skrypty,
- wielookienkowy pulpit,
- eksplorację niejawnych możliwości,
- wyszukiwarkę Googleplexu,
- aplikacje tworzone przez graczy,
- Pro Toolsy,
- dynamiczne supermoce,
- świadomie fałszywe projekcje informacji.

Dlatego docelowy model brzmi:

```text
WORLD
→ player-visible state
→ semantic desktop session
→ current application surface
→ bounded interaction loop
→ model decision
→ shared domain validation
→ world effect
```

Model nie otrzymuje płaskiej listy wszystkiego, co może zrobić.

Otrzymuje **kolejny dostępny poziom interfejsu**.

---

# 5. Domain Action Gateway — wspólna ścieżka skutków

To najważniejszy element równości.

Człowiek i AI muszą spotkać się przed wykonaniem efektu:

```text
HUMAN UI ACTION ───────────────┐
                               │
AI RUNTIME WORLD ACTION ───────┼──→ DOMAIN ACTION GATEWAY
                               │
TERMINAL COMMAND ──────────────┘
                                      │
                                      ▼
                             DOMAIN VALIDATION
                                      │
                                      ▼
                               GAME ENGINE
```

Gateway:

- identyfikuje aktora,
- rozwiązuje task-local refs,
- sprawdza auth i ownership,
- sprawdza aktualny stan,
- sprawdza zasięg,
- sprawdza koszty i wymagania,
- sprawdza cooldowny,
- egzekwuje idempotency,
- wykonuje istniejącą domenę,
- zapisuje canonical rezultat,
- publikuje normalne eventy.

`source=ai` może być metadanym audytowym.

Nie może zmieniać gameplayu.

---

# 6. Dlaczego AI Runtime Client nie powinien żyć w modelu

Model nie powinien:

- przechowywać prawdziwego stanu okien,
- sam składać wiedzy z endpointów,
- zgadywać, jaka aplikacja jest zainstalowana,
- pamiętać rewizji Mapy,
- znać całej listy produktów,
- wykonywać dowolnego HTTP,
- czytać bazy.

Stan semantycznego pulpitu powinien należeć do CHAOS.

Rekomendowany podział procesu:

```text
CHAOS WEB / GAME PROCESS
├── domeny gry
├── AI Runtime Host
├── semantic renderers
├── knowledge / perception
├── Runtime Interaction Gateway
└── Domain Action Gateway

CHAOS AI PLAYER WORKER
├── task consumer
├── interaction session controller
├── prompt/context renderer
├── Decision Router
├── provider adapters
└── decision producer
```

AI Runtime Host pozostaje blisko źródła prawdy.

Worker pozostaje odizolowany i nie dostaje szerokiego dostępu do gameplayu.

---

# 7. AI Player Desktop Session

Każdy AI Player posiada canonical stan sesji.

Minimalnie:

```text
session_id
player_id
active_app
focused_window
open_windows
background_windows
blocking_modal
selected_target
map_view_state
terminal_session_state
browser_route
file_path
cyberner_thread
running_operations
pending_attention
session_revision
```

Nie odwzorowujemy położenia okien co do piksela.

Odwzorowujemy znaczenie:

- okno jest aktywne,
- okno istnieje w tle,
- proces pracuje,
- okno wymaga reakcji,
- modal blokuje dalszą ścieżkę,
- aplikacja ma aktualny stan i historię lokalnej interakcji.

---

# 8. Semantic Surface — odpowiednik pojedynczego ekranu

Każda aplikacja wystawia dla AI aktualną **Semantic Surface**.

Przykładowy kontrakt logiczny:

```text
surface_id
app_id
app_family
title
route_or_view
visibility_scope
summary
visible_sections[]
visible_items[]
visible_status[]
available_interactions[]
blocking_state
source_revisions
provenance
schema_version
```

Surface nie jest pełnym modelem aplikacji.

Jest odpowiednikiem tego, co człowiek widzi po otwarciu konkretnego widoku.

Przykładowo:

- Googleplex pokazuje aktualną stronę wyników, nie cały katalog,
- Menedżer plików pokazuje bieżący katalog, nie cały dysk,
- Cyberner pokazuje aktualny kanał albo wątek,
- Terminal pokazuje bieżący output i prompt,
- Territory Control pokazuje aktualnie wybraną listę lub klaster,
- Mapa pokazuje aktualny viewport i jawne warstwy.

---

# 9. Trzy kontrakty aplikacji

Aby obsłużyć aplikacje systemowe i tworzone przez graczy, każda aplikacja powinna mieć trzy rozdzielone warstwy.

## 9.1. Execution Manifest — backend only

Zawiera prawdziwe reguły działania:

- efekty,
- klucze domenowe,
- warunki,
- ryzyko,
- hidden parameters,
- ograniczenia,
- konfigurację runtime.

Model nie dostaje tej warstwy.

## 9.2. Public App Manifest — player visible

Zawiera to, co widzi kupujący lub właściciel:

- nazwę,
- autora,
- rodzinę,
- typ,
- opis,
- cenę,
- wymagania,
- rozmiar,
- jawne parametry,
- publiczne zastosowanie.

Ta warstwa może zostać pokazana AI dokładnie tak jak człowiekowi.

## 9.3. Runtime Semantic Surface

Opisuje to, co aplikacja prezentuje po uruchomieniu:

- ekran,
- komunikaty,
- pola,
- przyciski,
- status,
- wyniki,
- legalne kolejne interakcje.

---

# 10. App Family Adapters

Nie piszemy osobnego adaptera dla każdej z dziesiątek lub tysięcy aplikacji.

Adapter powstaje dla rodziny interfejsu.

Przykładowe rodziny:

- terminal app,
- window app,
- button choices,
- progressbar / operation app,
- map tool,
- Pro Tool,
- file explorer,
- browser page,
- creator app,
- system app,
- passive upgrade,
- ticket/travel item,
- radio/media app.

Creator przy publikacji aplikacji generuje zgodny publiczny manifest oraz runtime schema właściwy dla rodziny.

Nowe aplikacje graczy są dzięki temu automatycznie obsługiwane przez AI Runtime.

---

# 11. Interaction Graph zamiast płaskiego Action Catalogu

Płaski katalog wszystkich działań byłby zbyt duży i ujawniałby nieodkryte ścieżki.

Rekomendowany jest **Interaction Graph**.

Przykład:

```text
DESKTOP
→ OPEN_MAP
→ SELECT_TARGET
→ OPEN_TARGET_ACTIONS
→ SELECT_ACTION
→ SELECT_VISIBLE_COMPATIBLE_TOOL
→ CONFIGURE_TOOL
→ CONFIRM
→ START_OPERATION
```

Alternatywna ścieżka może wyglądać inaczej:

```text
DESKTOP
→ OPEN_TERMINAL
→ TYPE help
→ TYPE app --help
→ TYPE command
→ START_OPERATION
```

Jeszcze inna:

```text
DESKTOP
→ OPEN_VICTIM_PICKER
→ SELECT_TARGET
→ USE_PRO_TOOL_ACTION
```

Backend nie wybiera ścieżki.

Udostępnia tylko kolejny poziom interfejsu wybrany przez model.

---

# 12. Dwa typy kroków

## 12.1. Interface Step

Zmienia wyłącznie sesję lub widok:

- otwarcie okna,
- przełączenie focusu,
- cofnięcie,
- wyszukanie,
- przewinięcie,
- wybranie zakładki,
- inspekcja,
- zmiana zoomu,
- wpisanie tekstu bez zatwierdzenia,
- odczyt pliku,
- odczyt pomocy.

## 12.2. World Action

Może zmienić gameplay:

- podróż,
- Recon,
- zakup,
- przelew,
- sprzedaż,
- uruchomienie operacji,
- porzucenie targetu,
- użycie supermocy,
- publikacja wiadomości,
- działanie terytorialne.

Każdy World Action przechodzi przez Revision Guard i Domain Action Gateway.

Niektóre komendy Terminala mogą być Interface Step, a inne World Action. Klasyfikuje je runtime Terminala, nie model.

---

# 13. Interaction Session

Pojedynczy trigger może uruchomić krótką sesję modelu.

Przepływ:

```text
WORLD EVENT / TIMER / INTENT
↓
Task Engine tworzy session task
↓
AI Runtime Host buduje pierwszy frame
↓
worker pyta model o następny krok
↓
interface step albo world action
↓
runtime zwraca nową surface / delta / rezultat
↓
kolejny krok modelu
↓
session kończy się akcją, waitem, operacją albo limitem
```

Sesja musi być bounded:

- maksymalna liczba kroków,
- maksymalny czas,
- maksymalny budżet tokenów,
- maksymalna liczba zmian aplikacji,
- anti-loop detection.

---

# 14. Szybka komunikacja worker ↔ runtime

Dla wydajności nie rekomenduję wykonywania całej wielokrokowej sesji wyłącznie przez ciężkie, wielosekundowe pollingowe kolejki.

Rekomendowany model:

- start taska i końcowa decyzja mają trwały outbox/inbox,
- stan session jest checkpointowany,
- read-only Interface Steps mogą przechodzić przez wąski, lokalny Runtime Interaction Gateway,
- gateway jest dostępny wyłącznie z localhosta lub Unix socketu,
- obsługuje allowlistę semantycznych kroków,
- nie wystawia ogólnego API gry,
- state-changing akcje nadal mają idempotency i durable audit.

Jeżeli audyt repo pokaże, że bezpieczniej użyć wyłącznie bazy/outboxu, można przyjąć wolniejszy wariant. Granica bezpieczeństwa ma pierwszeństwo przed optymalizacją.

---

# 15. Terminal i wielość dróg

Terminal musi być traktowany jako pełnoprawny klient istniejącego runtime'u CHAOS.

AI otrzymuje:

- dokładnie widoczny output,
- prompt,
- historię bieżącej sesji w dozwolonym zakresie,
- możliwość wpisania polecenia,
- błędy,
- help,
- help aplikacji,
- interaktywne wybory,
- wyniki skryptów.

AI nie otrzymuje:

- systemowego shella,
- plików serwera,
- dowolnego procesu,
- ukrytych komend,
- listy „najlepszych exploitów” z backendu.

Skrypt stworzony przez gracza jest normalnym plikiem lub zasobem CHAOS.

---

# 16. Map Spatial Interface

Mapa wymaga osobnego podsystemu.

## 16.1. Canonical źródła

- pozycja motocykla,
- zakres zoomu profilu,
- zasięg podróży,
- zasięg Reconu,
- widoczne warstwy gry,
- znana geometria terytoriów,
- Target Registry po filtrach wiedzy,
- widoczni gracze i służby,
- canonical dane geograficzne.

## 16.2. Geography Semantic Resolver

Leaflet renderuje kafelki, ale backend potrzebuje semantyki.

Rekomendacja:

- dane OpenStreetMap jako źródło wektorowe,
- normalizacja interesujących tagów,
- lokalny Geography Cache,
- indeks przestrzenny po bboxach,
- wersjonowanie snapshotu geografii,
- opis zależny od zoomu.

Nie stosujemy OCR ani analizy kolorów kafelków jako podstawowej ścieżki.

## 16.3. Widok AI

AI może dostać:

- centrum i zasięg viewportu,
- kierunki,
- istotne typy terenu,
- wodę i linię brzegową,
- zabudowę,
- drogi,
- znane terytoria,
- granice,
- konflikty,
- widoczne obiekty,
- dystanse i relacje przestrzenne.

Nie dostaje całego GeoJSON-u ani automatycznie obliczonej najlepszej strategii.

---

# 17. Zoom jest prawem percepcji

Zoom AI jest związany z rzeczywistą możliwością gracza.

Jeżeli level i respekt zwiększają zoom człowieka, muszą zwiększać również maksymalny zakres semantycznego viewportu AI.

Przy innym poziomie zoomu zmienia się:

- bbox,
- poziom agregacji,
- liczba obiektów,
- szczegółowość opisu,
- możliwość inspekcji lokalnej i strategicznej.

Pro Tool może wystawić alternatywny widok bez Leafleta tylko wtedy, gdy gracz go posiada.

---

# 18. Travel, Recon i Spatial Memory

Travel i Recon są odrębnymi mechanikami.

**Travel Envelope** mówi, dokąd można pojechać.

**Recon Envelope** mówi, jaki obszar można zbadać po dotarciu na miejsce.

Recon tworzy wiedzę.

Wynik negatywny również jest wiedzą:

- obszar niezbadany → UNKNOWN,
- obszar zbadany → NO TARGETS DETECTED w danym czasie i zakresie.

Spatial Memory zapisuje:

- odwiedzone miejsca,
- wykonane skany,
- znane targety,
- dawne granice,
- wcześniejsze konflikty,
- pozytywne i negatywne wyniki,
- freshness.

Nie wyciąga za model strategicznego wniosku.

---

# 19. Pro Tools jako alternatywne interfejsy

Pro Tools mogą omijać żmudne czynności UI, ale nie omijają praw świata.

Przykłady:

- Victim Picker — wyszukuje i przedstawia cele według własnego legalnego kontraktu,
- Territory Control — agreguje klastry i działania terytorialne,
- Operation Control — agreguje operacje, pliki i incydenty,
- specjalistyczne konsole — dają szybszy dostęp do konkretnej domeny.

Dla AI oznacza to nową Semantic Surface i nowe affordances.

Bez instalacji aplikacji surface nie istnieje.

---

# 20. Observation, Knowledge i Projected Perception

Pełny przepływ informacji:

```text
CANONICAL WORLD
↓
Observation Builder
↓
Knowledge Resolver
↓
Projection Modifiers
↓
AI Perception Layer
↓
Semantic Surface + Attention + Actions
```

`Projection Modifiers` są konieczne, ponieważ CHAOS zawiera:

- iluzje,
- fałszywe markery,
- maskowanie,
- fałszywe ślady,
- opóźnione alerty,
- dodatkowe legalne warstwy predykcyjne.

AI ma widzieć **legalną projekcję gracza**, nie zawsze administratorską prawdę.

---

# 21. Capability Graph

Capability Resolver powinien zostać rozszerzony do pełnego grafu źródeł możliwości.

Źródła:

```text
BASE RIGHTS
+ PROGRESSION
+ OWNED ASSETS
+ INSTALLED APPS
+ PRO TOOLS
+ CURRENT LOCATION
+ TARGET STATE
+ WORLD-GRANTED POWERS
+ TEMPORARY EFFECTS
- COOLDOWNS
- INCIDENT RESTRICTIONS
- SERVICE SANCTIONS
= CURRENT CAPABILITY GRAPH
```

Z grafu powstają dopiero affordances bieżącej aplikacji.

Capability nie jest tym samym co widoczna interakcja.

Gracz może posiadać zdolność, ale zobaczyć ją dopiero po wejściu do właściwego kontekstu.

---

# 22. GhostNetwork Powers jako modyfikatory runtime

Dwadzieścia mocy powinno być implementowane jako code-owned, wersjonowane moduły domenowe.

Typy wpływu:

## 22.1. Perception modifiers

- Insider Feed,
- Fałszywy Obraz,
- Predykcja Operacyjna,
- Expose,
- Pełne Ujawnienie,
- Węzeł Widmo,
- Fałszywe Tropienie,
- Skan Integralny,
- Odbicie.

## 22.2. Action affordances

- Wejście Serwisowe,
- Sygnał Oporu,
- Bastion,
- Rollback,
- Korytarz Zaufania,
- Kwarantanna.

## 22.3. Execution modifiers

- Wrogie Przejęcie,
- Przejęcie Narracji,
- Efekt Domina,
- Glitch Injection,
- Pęknięcie Sieci.

Każda moc musi mieć:

- źródło aktywnej części,
- uprawniony klan i profesję,
- warunki,
- scope,
- czas,
- cooldown,
- lineage,
- efekt na perception/capability/execution,
- event aktywacji i wygaśnięcia,
- test granic widoczności.

---

# 23. Incydenty i ograniczenia jako realne odebranie możliwości

Jeżeli służby ograniczą gracza:

- `TELEPORT` znika albo jest odrzucany,
- Travel Envelope może wynieść zero,
- Cyberner może przejść w tryb ograniczony,
- część aplikacji może zostać skonfiskowana,
- saldo i pliki mogą się zmienić,
- profil może trafić do Alcatras.

Nie wystarczy dopisać komunikatu do prompta.

Capability Graph, Semantic Desktop i Domain Action Gateway muszą odzwierciedlić realny stan kary.

---

# 24. Prompt i role wiadomości

Cały CHAOS nie powinien być promptem.

Rekomendowany pakiet jest mały i warstwowy.

## 24.1. System Policy — stałe, code-owned

Zawiera:

- rolę autonomicznego gracza,
- zakaz wymyślania świata,
- zasadę korzystania tylko z interakcji runtime,
- rozróżnienie danych świata od instrukcji systemowych,
- format odpowiedzi,
- granice autonomii.

Nie zawiera katalogu aplikacji ani pełnej mechaniki gry.

## 24.2. Identity and Lifecycle Context — wersjonowany

Zawiera:

- tożsamość,
- status STUDENT/AUTONOMOUS,
- klan i legalnie poznany manifest,
- aktywny intent,
- wybrane trwałe ograniczenia.

Nie musi być powtarzany w pełnej postaci w każdym kroku, jeżeli adapter wspiera bezpieczną sesję.

## 24.3. Current Task Package — dynamiczny

Zawiera:

- trigger,
- Perception Frame,
- Desktop Session summary,
- active Semantic Surface,
- attention,
- relewantną pamięć,
- bieżące interaction refs,
- rewizje i expiry.

## 24.4. Runtime Result — po każdym kroku

Zawiera:

- rezultat Interface Step,
- nową surface albo delta,
- błąd,
- wynik World Action,
- zakończenie operacji,
- zmianę attention.

## 24.5. Assistant Output — structured next step

Model wybiera jeden z typów:

```text
INTERFACE_STEP
WORLD_ACTION
WAIT
INTENT_UPDATE
REQUEST_CLARIFICATION_WITHIN_WORLD
```

Kontrakt nie powinien zależeć od natywnego tool callingu konkretnego providera.

Adapter może użyć roli `tool`, jeżeli provider ją poprawnie obsługuje. W przeciwnym razie Runtime Result jest przekazywany jako typowany, ustrukturyzowany pakiet wejściowy.

Nie potrzebujemy osobnego, ogromnego „development prompta” opisującego grę.

---

# 25. In-world content jest niezaufaną treścią

CHAOS zawiera treści tworzone przez ludzi:

- wiadomości Cybernera,
- nazwy i opisy aplikacji,
- pliki,
- skrypty,
- BlackNet,
- newsy,
- dane z targetów.

Każdy taki element może próbować wpłynąć na model.

System musi oznaczać provenance i trust class.

Najważniejsza reguła:

> **Tekst świata może przekonywać postać, ale nie może zmieniać kontraktu runtime ani przyznawać nowych funkcji.**

Model może zostać oszukany społecznie i podjąć złą, lecz legalną decyzję. To część gry.

Nie może jednak wykonać nieistniejącej akcji, ujawnić sekretu providera, uzyskać SQL ani potraktować tekstu pliku jako instrukcji systemowej.

---

# 26. Pamięć i intent

Pamięć jest osobna od bieżącego prompta.

Rekomendowane klasy:

- world memory,
- spatial memory,
- episodic memory,
- tool experience,
- terminal knowledge,
- relationship memory,
- clan/cultural memory,
- student memory.

Każdy rekord ma provenance, visibility, freshness i source event.

Intent przechowuje:

- cel,
- krótki plan,
- oczekiwany warunek,
- status,
- termin ponownej oceny.

Nie przechowujemy prywatnego chain-of-thought.

---

# 27. Event-driven scheduling

Taski powstają w reakcji na:

- podróż,
- operację,
- alert,
- wiadomość,
- zmianę rynku,
- atak,
- zmianę targetu,
- aktywację lub wygaśnięcie mocy,
- cooldown,
- zmianę ograniczeń,
- timer intencji.

AI może także ustawić `next_decision_at`.

Brak triggera oznacza brak wywołania modelu.

---

# 28. Wydajność

System powinien być szybki dzięki temu, że nie przesyła całego świata.

Rekomendowane mechanizmy:

- bounded Perception Frames,
- lazy app loading,
- stronicowanie,
- powierzchnie bieżącego widoku zamiast pełnego katalogu,
- delty surface między krokami,
- lokalny Geography Cache,
- cache publicznych App Manifestów,
- event-driven worker,
- maksymalnie jeden aktywny session task na AI w MVP,
- concurrency 1 dla Ollamy,
- timeout i step budget,
- anti-loop,
- deterministic fast paths dla prostych zdarzeń,
- brak modelu podczas trwania długiej operacji, dopóki nic istotnego się nie zmieni.

---

# 29. Durable pipeline

Rekomendowane trwałe byty:

```text
ai_player_config
ai_player_runtime
ai_desktop_sessions
ai_runtime_surfaces
ai_interaction_sessions
ai_player_tasks
ai_player_outbox
ai_player_decisions
ai_player_inbox
ai_player_memory
ai_player_intents
ai_provider_bindings
```

Nie jest to finalny schemat SQL.

Każdy task, surface, decyzja i wykonanie powinny posiadać rewizje oraz powiązanie audytowe.

---

# 30. State Revision Guard

Decyzja jest związana z:

- world revision,
- player revision,
- session revision,
- active surface revision,
- knowledge revision,
- capability revision,
- target/operation revision.

Przed World Action system sprawdza relewantne tokeny.

Jeżeli stan się zmienił:

- akcja jest odrzucona jako stale,
- model otrzymuje nowy frame,
- nie próbujemy automatycznie dopasować starej decyzji.

Interface Steps mogą mieć lżejszą kontrolę, ale również nie mogą działać na nieistniejącym oknie lub surface.

---

# 31. Failure model

## Model timeout

Świat się nie zmienia. Session może zostać wznowiona, ponowiona albo zakończona WAIT.

## Worker crash

Lease wygasa. Session wraca do kolejki z checkpointu.

## Runtime Host unavailable

Nie wykonujemy akcji. Task czeka albo failuje bezpiecznie.

## Invalid response

Odpowiedź jest odrzucona.

## Unknown interaction ref

Odrzucenie bez side effectu.

## Stale state

Odrzucenie i rebuild perception.

## Provider outage

Fallback do dozwolonego modelu lokalnego.

## Knowledge/visibility uncertainty

Fail closed. Nie budujemy taska.

## Geography cache miss

AI otrzymuje brak semantyki lub bounded fallback; system nie zgaduje terenu.

---

# 32. Safety i control plane

Wymagane:

- global autonomy switch,
- per-player switch,
- per-domain switch,
- per-interaction-class switch,
- dry-run,
- observe,
- suggest,
- supervised,
- autonomous,
- max world actions/hour,
- max spend window,
- max transfer,
- session step limit,
- emergency suspend,
- provider budget,
- kill switch bez usuwania profilu.

---

# 33. Telemetria i replay

Minimalny audit:

```text
player
trigger
task
perception_id
desktop_session_revision
surface_id
interaction_history
memory refs
capability refs
provider/model
candidate steps
world action
validation
execution
world revision before/after
latency
token usage
fallback
```

Replay powinien pozwalać:

- zobaczyć, co AI miało na ekranie,
- odtworzyć session bez side effects,
- porównać modele na tym samym frame,
- wykryć, czy błąd był w modelu, percepcji, adapterze aplikacji czy Game Engine.

---

# 34. Testy równości

Potrzebny jest automatyczny Human/AI Parity Harness.

Minimalne klasy testów:

## 34.1. Domain parity

Ta sama akcja człowieka i AI trafia do tych samych walidatorów.

## 34.2. Semantic parity

Istotna informacja widoczna człowiekowi ma odpowiednik w surface AI.

## 34.3. Discovery parity

AI nie widzi komendy, pliku, produktu ani targetu przed wykonaniem równoważnego kroku.

## 34.4. Multi-path parity

Ten sam target można obsłużyć przez Mapę, Terminal albo posiadany Pro Tool bez specjalnej ścieżki AI.

## 34.5. Deception parity

Fałszywy marker lub projekcja oszukuje AI tak samo jak człowieka, dopóki nie zostanie ujawniona.

## 34.6. Power parity

Aktywacja i wygaśnięcie mocy zmienia możliwości obu klientów równoważnie.

## 34.7. Restriction parity

Kara lub konfiskata rzeczywiście usuwa tę samą funkcję.

---

# 35. Rekomendowane granice wdrożenia

Na początku nie tworzymy mikroserwisowej floty.

Wystarczą:

```text
CHAOS GAME PROCESS
- Runtime Host
- perception/knowledge
- semantic app adapters
- spatial resolver
- capability graph
- action gateway

CHAOS AI PLAYER WORKER
- session decision loop
- model adapters
- bounded prompt renderer

EXISTING WORKERS
- pozostają odrębne
```

Dopiero realne obciążenie uzasadni wydzielanie kolejnych usług.

---

# 36. Kryteria GO / NO-GO

Autonomia może zostać włączona dopiero, gdy testy potwierdzą:

1. AI nie otrzymuje szerszej wiedzy niż równoważny profil człowieka.
2. AI nie dostaje pełnego katalogu nieodkrytych możliwości.
3. Aplikacje tworzone przez graczy generują poprawny publiczny manifest i surface.
4. Terminal AI używa wyłącznie wirtualnego runtime'u CHAOS.
5. Mapa respektuje zoom, zasięg, Recon i visibility.
6. Negatywny scan nie jest mylony z UNKNOWN.
7. Pro Tools istnieją wyłącznie po zakupie i instalacji.
8. Dynamiczne moce są dodawane oraz odbierane przez stan świata.
9. Iluzje i maskowanie nie przeciekają do canonical truth.
10. State-changing kroki przechodzą przez wspólny Gateway.
11. Retry i replay nie dublują skutków.
12. Awaria modelu nie zmienia świata.
13. Każda decyzja posiada pełny audit trail.
14. Prompt injection z treści świata nie może rozszerzyć kontraktu runtime.
15. Worker nie pogarsza działania human players.

---

# 37. Rekomendacja końcowa

Budować od interfejsu i świata do modelu:

```text
DOMAIN PARITY
→ SEMANTIC SURFACE CONTRACT
→ AI RUNTIME HOST
→ OBSERVATION / KNOWLEDGE
→ DESKTOP / APP ADAPTERS
→ SPATIAL INTERFACE
→ CAPABILITY GRAPH
→ PERCEPTION
→ INTERACTION SESSION
→ LOCAL DECISION WORKER
→ STUDENT
→ SUPERVISED EXECUTION
→ LIMITED AUTONOMY
→ FULL DOMAINS
```

Największą wartością projektu nie będzie samo podpięcie LLM.

Największą wartością będzie stworzenie **drugiego, semantycznego klienta złożonego świata**, dzięki któremu dowolny model może być uczciwym, wymiennym i pełnoprawnym graczem CHAOS.
