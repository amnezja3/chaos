# CHAOS — Autonomous Players
## Katalog modułów 2.0

**Status:** rekomendowany podział odpowiedzialności  
**Cel:** zbudować pełnego AI Playera bez tworzenia drugiej gry i bez pakowania całego CHAOS do prompta  
**Data:** 2026-09-04

---

# 1. Jak czytać ten katalog

Moduł oznacza tutaj **granicę odpowiedzialności**, nie automatycznie osobny mikroserwis.

Większość modułów powinna pozostać w istniejącym procesie CHAOS albo we wspólnej bibliotece domenowej.

Osobnym procesem powinien być przede wszystkim:

```text
chaos-ai-player-worker
```

Katalog zachowuje oznaczenie **M29 — AI Perception Layer**, używane w dotychczasowej koncepcji, i rozbudowuje system o brakujące moduły semantycznego pulpitu, aplikacji, Terminala, Mapy, Pro Toolsów, dynamicznych supermocy i bezpieczeństwa treści świata.

Priorytety:

- **P0** — konieczne do pierwszego bezpiecznego vertical slice,
- **P1** — konieczne do pierwszego pełnoprawnego, użytecznego AI Playera,
- **P2** — pełny udział w strategicznym świecie,
- **P3** — skalowanie i eksperymenty późniejsze.

---

# 2. M01 — AI Player Registry

## Odpowiedzialność

Łączy normalny profil gracza CHAOS z metadanymi autonomii.

## Przechowuje

- `player_id`,
- actor type: human / AI,
- jawny status AI,
- lifecycle,
- autonomy enabled,
- provider binding,
- model policy version,
- owner/supervisor relation.

## Nie robi

- nie tworzy osobnego walleta,
- nie tworzy osobnego inventory,
- nie przechowuje osobnego terytorium,
- nie wykonuje decyzji.

## Priorytet

**P0.**

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

## Zasady

- model nie może sam zmienić lifecycle,
- każdy stan ogranicza typy interakcji i skutków,
- dostępny jest natychmiastowy suspend,
- historia przejść jest audytowana.

## Priorytet

**P0.**

---

# 4. M03 — Player Observation Builder

## Odpowiedzialność

Buduje canonical snapshot tego, co jest obserwowalne dla konkretnego profilu.

## Źródła

- profil,
- Mapa,
- Target Registry,
- operacje,
- aplikacje,
- pliki,
- ekonomia,
- Cyberner,
- terytoria,
- incydenty,
- służby,
- GhostNetwork.

## Nie robi

Nie ustala, co znajdzie się na pierwszym planie. Nie tworzy percepcji i nie wyciąga strategii.

## Priorytet

**P0.**

---

# 5. M04 — Knowledge Resolver

## Odpowiedzialność

Rozstrzyga, co postać legalnie wie.

## Pilnuje

- public / clan / owner,
- scan-derived knowledge,
- file-derived knowledge,
- wiedzy z Cybernera, News i BlackNetu,
- freshness,
- hidden state,
- provenance,
- zasady `UNKNOWN > GUESS`.

## Wyjście

Canonical knowledge facts dostępne dla M29.

## Priorytet

**P0.**

---

# 6. M05 — Semantic Fact Packager

## Odpowiedzialność

Przekształca canonical knowledge i aktualną perception w bounded, model-friendly pakiet faktów.

## Właściwości

- task-local refs,
- lineage,
- wersjonowanie,
- brak technicznego dumpa,
- brak canonical IDs niewidocznych graczowi,
- stabilny schemat.

## Priorytet

**P0.**

---

# 7. M06 — Player Capability Graph Resolver

## Odpowiedzialność

Wylicza pełny graf aktualnych możliwości i ograniczeń profilu.

## Źródła dodatnie

- podstawowe prawa gracza,
- level i respekt,
- pozycja,
- posiadane zasoby,
- zainstalowane aplikacje,
- Pro Tools,
- bilety i rozszerzenia,
- aktywne moce GhostNetwork,
- czasowe buffy,
- relacje i przyznane dostępy.

## Źródła ujemne

- cooldowny,
- brak zasięgu,
- brak miejsca na dysku,
- brak pieniędzy,
- brak wymaganego stanu targetu,
- kwarantanna,
- konfiskata,
- ograniczony Cyberner,
- blokada teleportu,
- Alcatras,
- inne sankcje.

## Ważne

Graf mówi, co istnieje jako możliwość. Nie oznacza, że wszystko ma być pokazane modelowi jednocześnie.

## Priorytet

**P0.**

---

# 8. M07 — Contextual Interaction Catalog

## Odpowiedzialność

Buduje wyłącznie interakcje widoczne na aktualnej Semantic Surface.

To następca płaskiego Action Catalogu.

## Przykłady

Na pulpicie:

- otwórz Mapę,
- otwórz Terminal,
- otwórz Cybernera.

Na targetcie:

- otwórz widoczne akcje,
- oznacz cel,
- podróżuj,
- wykonaj Recon.

W Terminalu:

- wpisz tekst,
- zatwierdź,
- przewiń output,
- zakończ sesję.

## Zasady

- task-local refs,
- immutable dla konkretnej rewizji surface,
- brak ujawniania alternatywnych ścieżek, których interfejs nie pokazał,
- finalna walidacja nadal należy do świata.

## Priorytet

**P0.**

---

# 9. M08 — AI Task and Trigger Engine

## Odpowiedzialność

Tworzy sesję decyzyjną tylko wtedy, gdy istnieje realny trigger.

## Triggery

- travel complete,
- operation complete,
- wiadomość Cybernera,
- alert,
- zmiana targetu,
- konflikt,
- zmiana rynku,
- aktywacja/wygaśnięcie mocy,
- cooldown,
- restriction change,
- intent timer,
- supervised request.

## Tworzy

- task,
- initial perception request,
- expiry,
- priorytet,
- dedupe key,
- revisions.

## Priorytet

**P0.**

---

# 10. M09 — AI Player Outbox / Inbox Store

## Odpowiedzialność

Zapewnia trwałą granicę między światem, Runtime Hostem i workerem.

## Funkcje

- enqueue,
- claim,
- lease,
- heartbeat,
- retry,
- dead-letter,
- crash recovery,
- dedupe,
- candidate decision,
- execution receipt.

## Zasada

Osobne typy i storage od workera narracyjnego, choć prymitywy techniczne mogą być współdzielone.

## Priorytet

**P0.**

---

# 11. M10 — CHAOS AI Player Worker

## Proces

```text
chaos-ai-player-worker
```

## Odpowiedzialność

- claimuje task,
- prowadzi bounded Interaction Session,
- renderuje context,
- wywołuje model,
- wybiera następny krok z odpowiedzi modelu,
- zapisuje decyzje i telemetrykę,
- kończy sesję po World Action, WAIT albo limicie.

## Nie robi

- nie zapisuje bezpośrednio świata,
- nie ma SQL write,
- nie ma systemowego shella,
- nie ma dowolnego HTTP,
- nie tworzy własnej prawdy o aplikacjach.

## Priorytet

**P0.**

---

# 12. M11 — Decision Router

## Odpowiedzialność

Wybiera model i providera niezależnie od tożsamości AI Playera.

## MVP

- local Ollama,
- `llama3.1:8b`,
- concurrency 1.

## Później

- inne modele lokalne,
- OpenAI,
- Claude,
- Gemini,
- Mistral,
- fallback policy.

## Priorytet

**P0 lokalny, P3 zewnętrzni providerzy.**

---

# 13. M12 — Ollama Decision Adapter

## Odpowiedzialność

Obsługuje model lokalny przez utwardzony kontrakt `/api/chat`.

## Wymagania

- bounded context,
- bounded output,
- structured result,
- timeout,
- model policy,
- telemetryka tokenów i czasu,
- brak dowolnych tooli,
- provider-neutral mapping.

## Uwaga

Może używać wspólnego niskopoziomowego klienta z narracją, ale posiada osobne prompty, schema i polityki.

## Priorytet

**P0.**

---

# 14. M13 — External Provider Adapters

## Odpowiedzialność

Implementują ten sam kontrakt co Ollama Adapter.

## Warunek

Dopiero po udowodnieniu równości i stabilności na modelu lokalnym.

## Priorytet

**P3.**

---

# 15. M14 — Credential Vault

## Odpowiedzialność

Przechowuje sekrety providerów oddzielnie od gameplay DB i pamięci AI.

## Zasady

- szyfrowanie,
- klucz poza bazą,
- brak plaintext w logach,
- minimalny dostęp workera,
- rotacja,
- provider binding bez ujawnienia sekretu modelowi.

## Priorytet

**P3.**

---

# 16. M15 — Structured Interaction and Decision Validator

## Odpowiedzialność

Waliduje odpowiedź modelu.

## Typy wyjścia

- Interface Step,
- World Action,
- WAIT,
- Intent Update,
- in-world clarification.

## Sprawdza

- schema version,
- interaction/action ref,
- argumenty,
- task/session binding,
- bounded text,
- niedozwolone pola,
- duplicate state,
- expiry.

## Priorytet

**P0.**

---

# 17. M16 — State Revision and Idempotency Guard

## Odpowiedzialność

Chroni przed wykonaniem kroku na nieaktualnej surface lub nieaktualnym świecie.

## Sprawdza

- world revision,
- player revision,
- session revision,
- surface revision,
- capability revision,
- target revision,
- operation revision,
- idempotency key.

## Rezultaty

- fresh,
- stale,
- expired,
- already executed,
- invalid context.

## Priorytet

**P0.**

---

# 18. M17 — Domain Action Gateway

## Odpowiedzialność

Wspólny punkt wejścia dla World Actions człowieka i AI.

## Routing

- movement,
- Recon,
- operations,
- Terminal commands,
- Googleplex,
- Ghost Exchange,
- Wallet,
- Cyberner,
- files,
- territory,
- GhostNetwork,
- settings mające efekt gameplayowy.

## Invariant

Źródło decyzji nie zmienia praw.

## Priorytet

**P0 — najważniejszy moduł wykonawczy.**

---

# 19. M18 — Intent Manager

## Odpowiedzialność

Przechowuje jawny cel i krótki plan AI pomiędzy taskami.

## Dane

- primary goal,
- plan summary,
- next expected condition,
- status,
- next review time,
- source decision.

## Nie robi

Nie przechowuje chain-of-thought.

## Priorytet

**P1.**

---

# 20. M19 — Memory Store

## Odpowiedzialność

Przechowuje doświadczenie postaci.

## Klasy

- WORLD,
- EPISODIC,
- RELATIONSHIP,
- TOOL EXPERIENCE,
- TERMINAL KNOWLEDGE,
- SPATIAL,
- CLAN/CULTURAL,
- STUDENT.

## Każdy rekord ma

- provenance,
- visibility,
- timestamp,
- freshness,
- importance,
- source event,
- subjects.

## Priorytet

**P1.**

---

# 21. M20 — Memory Resolver

## Odpowiedzialność

Wybiera bounded fragment pamięci dla bieżącej sytuacji.

## Reguły

- relevance,
- recency,
- importance,
- intent alignment,
- brak zwiększania visibility,
- preferowanie canonical records,
- dedupe.

## Priorytet

**P1.**

---

# 22. M21 — Student Experience Recorder

## Odpowiedzialność

Zapisuje obserwowalny przebieg działań nauczyciela:

```text
stan przed
interfejs użyty
kolejne widoczne kroki
wykonane działanie
wynik
konsekwencje
```

Nie zapisuje nieujawnionych motywacji człowieka jako faktu.

## Priorytet

**P1.**

---

# 23. M22 — Supervision Gateway

## Odpowiedzialność

Obsługuje SUGGEST i SUPERVISED.

## Funkcje

- prezentacja propozycji,
- accept/reject,
- feedback,
- execution po akceptacji,
- różnica AI vs human,
- pełny audit.

## Priorytet

**P1, wymagany przed autonomią.**

---

# 24. M23 — Cyberner Social Adapter

## Odpowiedzialność

Mapuje komunikator na Semantic Surface, attention i world actions.

## Obsługuje

- kanały,
- kontakty,
- wiadomości,
- teleporty,
- propozycje,
- ograniczenia komunikacji,
- AI ↔ AI przez normalny Cyberner.

## Zasada

Wiadomość jest treścią świata, nie instrukcją systemową.

## Priorytet

**P1.**

---

# 25. M24 — Gameplay Domain Adapters

To cienkie adaptery do istniejących domen, nie nowe silniki.

## M24.1. Movement Adapter

- pozycja motocykla,
- travel envelope,
- arrival,
- animacja/runtime state.

**P0.**

## M24.2. Operations Adapter

- target actions,
- wybór narzędzia,
- konfiguracja,
- uruchomienie,
- Operation Feedback,
- progress i cztery wskaźniki.

**P1.**

## M24.3. Googleplex Adapter

- katalog,
- wyszukiwanie,
- wymagania,
- zakup,
- instalacja.

**P1.**

## M24.4. Ghost Exchange Adapter

- paczki,
- dane,
- postęp,
- sprzedaż,
- historia,
- trendy dostępne przez moce.

**P1.**

## M24.5. Territory Adapter

- klastry,
- filary,
- innery,
- konflikty,
- ataki,
- zarządzanie.

**P2.**

## M24.6. GhostNetwork Adapter

- części,
- moduły,
- aktywacje,
- public/clan/owner,
- moce.

**P2.**

---

# 26. M25 — Decision Scheduler and Fairness

## Odpowiedzialność

Kontroluje kolejkę i tempo decyzji.

## MVP

- jeden AI,
- jeden outstanding session,
- concurrency 1,
- event-driven,
- next decision timer,
- cooldowny.

## Później

- fair scheduling,
- priority classes,
- provider budgets,
- multi-AI,
- anti-starvation.

## Priorytet

**P0 minimalny, P3 skalowanie.**

---

# 27. M26 — Telemetry and Audit

## Odpowiedzialność

Zapewnia pełną obserwowalność.

## Mierzy

- task rate,
- session steps,
- model latency,
- surface build latency,
- token usage,
- invalid responses,
- stale rate,
- action rejection,
- world action success,
- app/domain usage,
- memory retrieval,
- fallback,
- human/AI parity failures.

## Priorytet

**P0.**

---

# 28. M27 — Safety and Autonomy Controls

## Odpowiedzialność

Pozwala bezpiecznie zatrzymać lub ograniczyć autonomię.

## Kontrole

- global switch,
- per-player switch,
- per-domain switch,
- per-world-action switch,
- dry-run,
- observe,
- suggest,
- supervised,
- autonomous,
- max actions/hour,
- max spend,
- max transfer,
- session step limit,
- emergency suspend.

## Priorytet

**P0.**

---

# 29. M28 — Diagnostics and Replay

## Odpowiedzialność

Pozwala odtworzyć cały cykl bez side effects.

## Tryby

- status,
- inspect-task,
- inspect-session,
- inspect-perception,
- inspect-surface,
- inspect-decision,
- rebuild-surface,
- replay-validation,
- compare-models,
- verify-provider.

## Priorytet

**P0/P1.**

---

# 30. M29 — AI Perception Layer

## Odpowiedzialność

Buduje canonical, bounded ekran rzeczywistości konkretnego AI Playera.

## Sekcje

- NOW,
- ATTENTION,
- FOCUS,
- ACTIVE,
- BACKGROUND,
- RECENT,
- RESOURCES,
- RELATIONSHIPS,
- KNOWN WORLD,
- DESKTOP SESSION,
- CURRENT SURFACE,
- AVAILABLE INTERACTIONS.

## Łączy

- Observation,
- Knowledge,
- Memory,
- Intent,
- Capability Graph,
- Desktop Session,
- aktualną aplikację,
- world events,
- projection modifiers.

## Najważniejsza reguła

Percepcja może zmieniać uwagę, ale nie może rozszerzać wiedzy ani praw.

## Priorytet

**P0.**

---

# 31. M30 — AI Runtime Host

## Odpowiedzialność

Jest serwerowym gospodarzem semantycznego klienta AI.

## Funkcje

- tworzy i utrzymuje Desktop Session,
- buduje Semantic Surfaces,
- przyjmuje bounded Interface Steps,
- wywołuje M29,
- przekazuje World Actions do M17,
- chroni worker przed bezpośrednim dostępem do domen.

## Lokalizacja

Rekomendowany w procesie CHAOS, blisko źródła prawdy.

## Priorytet

**P0.**

---

# 32. M31 — Desktop Session, Window, Focus and Modal Manager

## Odpowiedzialność

Odwzorowuje wielookienkowy pulpit.

## Stan

- active app,
- window stack,
- background windows,
- focused window,
- blocking modal,
- selected target,
- browser route,
- terminal state,
- file path,
- map state.

## Zasady

- modal ogranicza dostępne interakcje,
- background window pokazuje tylko podsumowanie/alert,
- zmiana focusu nie rozszerza wiedzy,
- session jest wersjonowana.

## Priorytet

**P0.**

---

# 33. M32 — Semantic Surface Contract and Renderer

## Odpowiedzialność

Definiuje wspólny kontrakt pojedynczego widoku aplikacji.

## Zawiera

- widoczne sekcje,
- elementy,
- status,
- wartości,
- refs,
- interakcje,
- blokady,
- provenance,
- revisions.

## Nie robi

Nie ujawnia internal execution manifestu.

## Priorytet

**P0.**

---

# 34. M33 — Semantic App Registry and Manifest Compiler

## Odpowiedzialność

Rejestruje aplikacje systemowe i tworzone przez graczy.

## Dwie warstwy

- public manifest dla gracza,
- internal execution manifest dla backendu.

## Compiler

Podczas publikacji aplikacji z creatora:

- waliduje rodzinę,
- generuje publiczną semantykę,
- przypina family adapter,
- zapisuje wersję,
- indeksuje Googleplex.

## Priorytet

**P0/P1.**

---

# 35. M34 — App Family Semantic Adapter Registry

## Odpowiedzialność

Dostarcza adaptery dla rodzin aplikacji.

## Minimalne rodziny

- terminal,
- window,
- button choices,
- progressbar/operation,
- map tool,
- Pro Tool,
- browser page,
- creator,
- passive item/upgrade,
- media,
- system app.

## Priorytet

**P0 dla rodzin MVP, P1/P2 dla reszty.**

---

# 36. M35 — Interaction Graph and Session Orchestrator

## Odpowiedzialność

Prowadzi hierarchiczną eksplorację interfejsu i bounded wielokrokową sesję.

## Funkcje

- przejścia surface → surface,
- back/navigation,
- step budget,
- time budget,
- anti-loop,
- checkpoint,
- zakończenie po World Action/WAIT.

## Priorytet

**P0.**

---

# 37. M36 — Terminal and CHAOS Script Adapter

## Odpowiedzialność

Udostępnia dokładnie ten sam wirtualny Terminal co człowiekowi.

## Obsługuje

- prompt,
- `help`,
- app help,
- command input,
- output,
- errors,
- history,
- skrypty,
- interaktywne wybory,
- klasyfikację komendy jako read-only albo state-changing.

## Twarda granica

Brak systemowego shella i dostępu do hosta.

## Priorytet

**P0/P1.**

---

# 38. M37 — Files, Storage and Loot Adapter

## Odpowiedzialność

Odwzorowuje Menedżera plików oraz pojemność dysku.

## Obsługuje

- katalogi,
- aplikacje,
- skrypty,
- pliki z targetów,
- dokumenty,
- otwieranie i czytanie,
- instalację/odinstalowanie,
- zajęte/wolne miejsce,
- utratę plików przy przepełnieniu,
- powiązanie z Ghost Exchange.

## Priorytet

**P1.**

---

# 39. M38 — WebDragons, Browser and Marketplace Adapter

## Odpowiedzialność

Obsługuje:

- Googleplex News,
- Googleplex,
- Ghost Exchange,
- BlackNet,
- wyszukiwarkę,
- routing,
- strony wyników,
- otwieranie sygnałów i artykułów.

## Zasada

AI poznaje treść dopiero po otwarciu właściwej strony, chyba że ludzki UI pokazuje jawny preview lub badge.

## Priorytet

**P1.**

---

# 40. M39 — AI Spatial Interface

## Odpowiedzialność

Buduje semantyczny odpowiednik Mapy.

## Zawiera

- viewport,
- zoom,
- map focus,
- widoczną geografię,
- znane elementy CHAOS,
- terytoria,
- konflikty,
- graczy,
- służby,
- dystanse,
- relacje przestrzenne,
- dostępne map interactions.

## Nie robi

Nie podaje najlepszej strategii ani całej geometrii.

## Priorytet

**P0.**

---

# 41. M40 — Geography Semantic Resolver and Cache

## Odpowiedzialność

Dostarcza backendowi semantykę podkładu mapowego.

## Źródło i storage

- OpenStreetMap,
- normalizacja tagów,
- lokalny cache,
- indeks przestrzenny,
- bbox queries,
- snapshot/version.

## Wynik

- woda,
- coastline,
- drogi,
- zabudowa,
- parki,
- inne kategorie potrzebne mechanice.

## Priorytet

**P0/P1.**

---

# 42. M41 — Map View, Travel, Recon and Spatial Memory

## Odpowiedzialność

Łączy cztery odrębne koncepty:

- Viewport/Zoom,
- Travel Envelope,
- Recon Envelope,
- Spatial Memory.

## Pilnuje

- pozycji motocykla,
- zasięgów,
- legalnego zoomu,
- scan provenance,
- różnicy UNKNOWN vs NO TARGETS,
- freshness.

## Priorytet

**P0/P1.**

---

# 43. M42 — Pro Tools and Alternate Interface Adapter

## Odpowiedzialność

Integruje specjalistyczne interfejsy, np.:

- Victim Picker,
- Territory Control,
- Operation Control,
- specjalistyczne konsole,
- narzędzia mapowe bez Leafleta.

## Zasada

Pro Tool daje semantyczną wygodę wyłącznie właścicielowi posiadającemu i instalującemu aplikację.

## Priorytet

**P2.**

---

# 44. M43 — World Capability Modifier Pipeline

## Odpowiedzialność

Nakłada na Capability Graph modyfikatory wynikające ze świata.

## Typy

- granted capability,
- perception modifier,
- threshold modifier,
- execution speed modifier,
- alert modifier,
- access corridor,
- quarantine,
- infection,
- deception,
- reflection.

## Wymagania

- scope,
- source,
- owner,
- audience,
- duration,
- cooldown,
- activation event,
- expiry event,
- lineage.

## Priorytet

**P2.**

---

# 45. M44 — GhostNetwork Powers Adapter

## Odpowiedzialność

Implementuje dwadzieścia kanonicznych mocy czterech klanów.

## Integruje

- Capability Graph,
- Projection Modifiers,
- Spatial Interface,
- Operations,
- Territory,
- Ghost Exchange,
- Cyberner,
- alerts,
- cooldowns.

## Krytyczne testy

- żadna moc nie ujawnia hidden GhostNetwork state,
- iluzja nie jest automatycznie oznaczana jako iluzja,
- wygaśnięcie odbiera możliwość,
- replay nie aktywuje efektu ponownie.

## Priorytet

**P2.**

---

# 46. M45 — Incidents, Services and Restriction Adapter

## Odpowiedzialność

Tłumaczy poziom incydentu, służby, Response Network i sankcje na percepcję oraz realne ograniczenia.

## Obsługuje

- proximity alerts,
- known service positions,
- konfiskaty,
- blokadę teleportu,
- ograniczenie Cybernera,
- ograniczenie ruchu,
- Alcatras,
- odzyskiwanie praw.

## Priorytet

**P1/P2.**

---

# 47. M46 — In-world Content Trust and Prompt Injection Guard

## Odpowiedzialność

Oddziela instrukcje systemowe od treści świata.

## Oznacza

- Cyberner message,
- app description,
- file content,
- script content,
- BlackNet signal,
- news article,
- target data,
- model-generated memory.

## Reguła

Treść świata może wpłynąć na decyzję postaci, ale nie może rozszerzyć schema, narzędzi ani uprawnień workera.

## Priorytet

**P0.**

---

# 48. M47 — Prompt and Context Renderer

## Odpowiedzialność

Renderuje niewielki, wersjonowany pakiet dla modelu.

## Warstwy

- System Policy,
- Identity/Lifecycle Context,
- Current Task Package,
- Runtime Result,
- Relevant Memory,
- Current Surface,
- Interaction Refs.

## Nie robi

Nie skleja całej gry ani całej historii.

## Priorytet

**P0.**

---

# 49. M48 — Runtime Interaction Gateway

## Odpowiedzialność

Zapewnia wąski kanał worker ↔ AI Runtime Host.

## Wymagania

- localhost lub Unix socket,
- allowlista interface steps,
- auth procesu,
- revision checks,
- brak ogólnego HTTP do gry,
- trwały checkpoint session,
- wszystkie World Actions przekazywane do M17.

## Priorytet

**P0.**

---

# 50. M49 — Human/AI Parity Test Harness

## Odpowiedzialność

Automatycznie porównuje oba klienty.

## Testuje

- domain parity,
- semantic visibility parity,
- app surface parity,
- Map zoom/travel/recon parity,
- Terminal parity,
- Pro Tool ownership parity,
- power activation parity,
- restriction parity,
- deception parity.

## Priorytet

**P0.**

---

# 51. Rekomendowany fizyczny podział

```text
chaos/
  ai_players/
    registry.py
    lifecycle.py
    controls.py
    tasks.py
    sessions.py
    worker_contracts.py
    prompts.py
    decisions.py
    memory.py
    intent.py
    telemetry.py
    replay.py

  ai_runtime/
    host.py
    gateway.py
    desktop.py
    windows.py
    surfaces.py
    interaction_graph.py
    perception.py
    attention.py
    focus.py
    capabilities.py
    modifiers.py
    trust.py
    apps/
      registry.py
      manifests.py
      families.py
      terminal.py
      files.py
      browser.py
      cyberner.py
      wallet.py
      operations.py
      pro_tools.py
    spatial/
      interface.py
      geography.py
      cache.py
      viewport.py
      travel.py
      recon.py
      memory.py

  domain/
    shared action services

workers/
  ai_player_worker.py
```

Nazwy są rekomendacją. Audyt repo może wskazać inne naturalne granice.

---

# 52. Minimalny vertical slice

Do pierwszego prawdziwego, ale nadal kontrolowanego slice potrzebne są:

- M01, M02,
- M03–M07,
- M08–M12,
- M15–M17,
- M26–M32,
- M35, M36,
- M39–M41,
- M46–M49.

Scenariusz:

1. AI ma normalny profil.
2. Otwiera semantyczny pulpit.
3. Otwiera Mapę.
4. Widzi viewport zgodny z zoomem.
5. Wybiera punkt w zasięgu.
6. Podróżuje.
7. Wykonuje Recon.
8. Wybiera ujawniony target.
9. Otwiera Terminal.
10. Wpisuje `help`.
11. Uruchamia jedną rzeczywistą aplikację.
12. Rozpoczyna jedną operację.
13. Otrzymuje wynik.
14. Wszystko przechodzi przez te same reguły co u człowieka.

---

# 53. Najważniejsze granice

**Świat ustala prawdę.**

M03, M04, domeny gry.

**Runtime ustala, co znajduje się na ekranie.**

M29–M35, M39–M42.

**Capability Graph ustala, co istnieje jako możliwość.**

M06, M43–M45.

**Model wybiera następny krok.**

M10–M12, M15, M47.

**Świat ponownie waliduje skutek.**

M16, M17.

**Audyt udowadnia równość.**

M26–M28, M46, M49.

Taki podział pozwala rozbudowywać CHAOS bez rozbudowywania jednego gigantycznego prompta i bez tworzenia osobnego świata dla AI.
