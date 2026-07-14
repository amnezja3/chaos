# CHAOS — architektura techniczna incydentów i NPC

## Status dokumentu

Dokument jest technicznym kontraktem wdrożenia systemu **Response Network** opisanego w `incidents_npc_gameplay.md`.

Jego celem jest przygotowanie bezpiecznej implementacji głównej pętli rozgrywki:

```text
operacja
→ heat
→ incydent
→ reakcja służb NPC
→ ostrzeżenie i ryzyko
→ hotspot mapy oraz BlackNetu
→ wykrycie albo ucieczka
→ konsekwencje
```

Response Network powstaje przed GhostNetworkiem. Przy okazji wdrożenia należy odciążyć stary system terytoriów, ponieważ GhostNetwork będzie później intensywnie korzystał z własności, konfliktów, widoczności i zmian terytoriów.

Dokument nie ustala ostatecznych wartości balansu. Ustala moduły, odpowiedzialności, kontrakty danych, zabezpieczenia, sposób testowania i kolejność uruchamiania systemu.

## Zasady nadrzędne

1. Incydenty są osobnym modelem runtime, a nie kolejną ciężką warstwą pełnego snapshotu mapy.
2. Każda operacja posiada własny miernik ryzyka i jest bezpośrednim źródłem heat. System nie rekonstruuje heat z logów ani treści wiadomości.
3. Backend inicjuje incydent oraz wydaje kompletną kapsułę NPC. Frontend samodzielnie prowadzi trajektorię, animację i lokalne sprawdzenie wykrycia.
4. Frontend zgłasza wyłącznie kandydata wykrycia. Backend odtwarza stan, waliduje zgłoszenie i dopiero wtedy wykonuje konsekwencje.
5. NPC korzystają z tej samej warstwy aktorów i systemu animacji snikersów co awatar gracza.
6. Silnik decyzji nie modyfikuje bezpośrednio profilu ani operacji gracza.
7. Każda konsekwencja musi wynikać z zapisanej i możliwej do odtworzenia decyzji.
8. Ten sam stan, czas, seed i wersja algorytmu muszą dawać ten sam rezultat trajektorii.
9. Ponowienie feedbacku albo komunikatu nie może wykonać konsekwencji drugi raz.
10. System musi działać początkowo w trybie obserwacyjnym bez kar.
11. Każdą warstwę można osobno włączyć, wyłączyć albo zatrzymać awaryjnie.
12. Gracz offline albo bierny nie może zostać nowym podejrzanym wyłącznie przez ruch NPC.
13. Właściciel jest bezpieczny na swoim stabilnym terytorium, jeżeli incydent nie dotyczy żadnego z jego terytoriów ani działań.
14. Frontendowy ruch NPC nie może wymuszać ponownego przeliczania wszystkich terytoriów ani generować cyklicznych zapisów backendu.
15. Frontend otrzymuje początkowy snapshot oraz późniejsze delty inicjacji i zakończenia, nie kolejne pozycje NPC.
16. GhostNetwork dołącza później jako źródło heat i incydentów, bez zmiany podstawowego silnika.

## Granice systemu

### Response Network odpowiada za

- odczytywanie mierników ryzyka aktywnych operacji;
- wykrywanie przekroczenia progów ostrzeżenia i incydentu;
- grupowanie operacji w incydenty;
- eskalację i wygaszanie incydentów;
- tworzenie kapsuł zachowania jednostek NPC;
- backendową walidację kandydatów wykrycia;
- generowanie ostrzeżeń;
- przygotowanie decyzji o konsekwencjach;
- publiczny stan incydentów dla mapy;
- publikowanie zdarzeń dla BlackNetu, Radia i Cybernera;
- audyt oraz replay zdarzeń.

### Response Network nie odpowiada za

- wykonywanie właściwej operacji hakowania;
- przechowywanie całego profilu gracza;
- budowanie geometrii terytoriów;
- bezpośrednie usuwanie narzędzi i HC;
- renderowanie mapy;
- generowanie narracji przez Ollamę;
- reguły części i transmisji GhostNetworku.
- przesyłanie kolejnych pozycji NPC w czasie rzeczywistym.

## Przepływ danych

```text
operation runtime / PvP / territory conflict
                    │
                    ▼
          operation risk meter
                    │
          ┌─────────┴─────────┐
          ▼                   ▼
   warning issued       incident initializer
          │                   │
          ▼                   ▼
 system-message       NPC behavior capsule
                              │
                              ▼
                  frontend actor runtime
                  snikers + local trajectory
                              │
                              ▼
                    detection candidate
                              │
                              ▼
                   backend validation
                              │
                              ▼
                    consequence intent
                              │
                              ▼
                    consequence executor

incident store
      │
      ├── map snapshot + initiation delta
      ├── BlackNet world fact
      ├── Radio hook
      └── Cyberner system event
```

## Moduły backendu

### `operation_risk_meter`

Każda operacja przechowuje czysty miernik ryzyka. Heat jest wyliczany razem ze stanem operacji, a nie rekonstruowany później z logów, system messages albo śladów aktywności.

Minimalny kontrakt ryzyka operacji:

```json
{
  "operation_id": "operation_...",
  "actor_id": "player_...",
  "target_id": "marker_...",
  "position": {"lat": 0.0, "lng": 0.0},
  "base_heat": 15,
  "time_heat": 10,
  "tool_modifier": 20,
  "security_modifier": 8,
  "conflict_modifier": 25,
  "current_heat": 78,
  "warning_threshold": 45,
  "incident_threshold": 60,
  "warning_issued_at": null,
  "incident_id": null,
  "risk_version": 3
}
```

Miernik jest aktualizowany wyłącznie w domenowych punktach zmiany operacji. Nie wymaga osobnego ciężkiego pollera.

Wyliczenie pozostaje czystą funkcją:

```text
calculate_operation_risk(operation, tool, target, conflict, rules) → risk_state
```

Przekroczenie `warning_threshold` emituje jedno zdarzenie `response_warning_issued`. To samo zdarzenie zapisuje fakt ostrzeżenia i wysyła komunikat przez `system-messages`. Wiadomość jest kanałem komunikacji, nie źródłem prawdy.

Przekroczenie `incident_threshold` uruchamia `incident_initializer`. `operation_id + risk_version + threshold` tworzą klucz idempotencji, dzięki któremu ta sama operacja nie inicjuje tego samego incydentu wielokrotnie.

Kontrakty heat events mogą pozostać późniejszym rozszerzeniem dla PvP, konfliktów albo GhostNetworku, ale podstawowym źródłem jest bezpośredni miernik operacji.

### `incident_initializer`

Tworzy incydent albo dołącza operację do aktywnego incydentu znajdującego się w odpowiednim oknie czasu i odległości.

Initializer:

- odczytuje stan ryzyka operacji;
- określa poziom reakcji;
- przypisuje podejrzanego i powiązane terytoria;
- zapisuje incydent;
- uruchamia ostrzeżenie, jeżeli nie zostało wysłane wcześniej;
- wywołuje `response_dispatcher`;
- publikuje kapsułę NPC do mapy.

### `incident_engine`

Odpowiada za cykl życia incydentu:

```text
candidate
→ warning
→ active
→ escalated
→ cooling
→ resolved
→ archived
```

Po inicjacji silnik:

- scala pobliskie operacje według odległości i okna czasu;
- aktualizuje centrum incydentu bez gwałtownych skoków;
- wybiera poziom reakcji;
- określa promień incydentu;
- przypisuje podejrzanych, operacje i terytoria;
- emituje komendy dla `response_dispatcher`;
- wygasza incydent po ustaniu aktywności.

### `incident_store`

Jest źródłem prawdy dla aktywnych i niedawno zakończonych incydentów.

Nie przechowuje pełnych profili ani geometrii wszystkich terytoriów. Przechowuje identyfikatory oraz minimalny kontekst potrzebny do odtworzenia decyzji.

Minimalny rekord:

```json
{
  "incident_id": "incident_...",
  "version": 7,
  "status": "active",
  "level": 2,
  "heat": 68,
  "center": {"lat": 0.0, "lng": 0.0},
  "search_radius_m": 220,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "expires_at": "ISO-8601",
  "operation_ids": [],
  "suspect_refs": [],
  "territory_refs": [],
  "npc_capsule_ids": [],
  "seed": "stable-seed",
  "last_event_seq": 104
}
```

Zmiana rekordu zwiększa `version` i emituje zdarzenie delta.

### `response_dispatcher`

Na podstawie poziomu incydentu tworzy plan reakcji:

- rodzaje jednostek;
- liczbę jednostek;
- czas pierwszego przyjazdu;
- punkty wejścia;
- promienie patrolu i wykrywania;
- czas działania;
- reguły eskalacji.

Dispatcher zwraca gotowe kapsuły zachowania. Backend nie porusza NPC i nie zapisuje każdej pozycji.

### `npc_capsule_factory`

Buduje kompletną, wersjonowaną instrukcję działania jednostki:

```json
{
  "capsule_id": "capsule_...",
  "incident_id": "incident_...",
  "npc_id": "npc_...",
  "actor_type": "response_npc",
  "service_type": "cyberpolice",
  "service_level": 3,
  "spawn_at": "ISO-8601",
  "expires_at": "ISO-8601",
  "origin": {"lat": 0.0, "lng": 0.0},
  "incident_center": {"lat": 0.0, "lng": 0.0},
  "patrol_radius_m": 240,
  "detection_radius_m": 120,
  "speed_mps": 9,
  "trajectory_type": "orbital_search",
  "trajectory_seed": "stable-seed",
  "behavior_version": 1,
  "visual_family": "cyber_unit",
  "warning_until": "ISO-8601",
  "tracking_tokens": ["opaque-tracking-ref"]
}
```

Kapsuła zawiera wszystko, czego frontend potrzebuje do samodzielnego ruchu i animacji. Backend wysyła inicjację oraz późniejsze zmiany stanu incydentu, ale nie strumieniuje współrzędnych NPC.

Publiczna kapsuła nie ujawnia nazw ani identyfikatorów podejrzanych. Jeżeli frontend ma sprawdzać widocznych aktorów, otrzymuje krótkotrwałe, nieprzeznaczone do prezentacji `tracking_tokens`. Backend rozwiązuje token dopiero podczas walidacji feedbacku.

### `detection_validator`

Frontend wysyła `detection_candidate`, gdy według lokalnej symulacji NPC znalazł podejrzanego:

```json
{
  "candidate_id": "candidate_...",
  "incident_id": "incident_...",
  "npc_id": "npc_...",
  "actor_id": "player_...",
  "operation_id": "operation_...",
  "detected_at": "ISO-8601",
  "npc_position": {"lat": 0.0, "lng": 0.0},
  "actor_position": {"lat": 0.0, "lng": 0.0},
  "behavior_version": 1,
  "trajectory_seed": "stable-seed"
}
```

Backend nie ufa wynikowi klienta. Odtwarza trajektorię dla `detected_at` i ocenia zgłoszenie na podstawie ograniczonego kontekstu:

- pozycji NPC;
- pozycji operatora lub aktywnej operacji;
- odległości;
- statusu podejrzanego;
- poziomu incydentu;
- osłony i modyfikatorów narzędzi;
- relacji incydentu z terytorium;
- statusu online i aktywności gracza;
- zgodności seeda oraz wersji zachowania;
- czasu ostrzeżenia i ważności kapsuły.

Wynik walidacji ma postać decyzji, nie mutacji:

```json
{
  "decision_id": "decision_...",
  "incident_id": "incident_...",
  "npc_id": "npc_...",
  "actor_id": "player_...",
  "operation_id": "operation_...",
  "result": "detected",
  "reasons": ["suspect", "inside_detection_radius", "active_operation"],
  "decided_at": "ISO-8601",
  "candidate_id": "candidate_...",
  "validation_key": "incident+npc+actor+detection-window"
}
```

Kilku klientów może zgłosić to samo wykrycie publicznego NPC. `validation_key` sprawia, że backend zatwierdzi je tylko raz.

### `consequence_policy`

Przekształca zatwierdzoną decyzję wykrycia w intencję konsekwencji:

- anulowanie konkretnej operacji;
- usunięcie postępu przejęcia;
- konfiskata użytego narzędzia;
- konfiskata części HC;
- brak nagrody RSP i LVL;
- nadanie albo podniesienie `Judgment`;
- zapis historii.

Polityka musi uwzględniać poziom incydentu i ochronę przed softlockiem.

### `consequence_executor`

Jest jedynym modułem uprawnionym do wykonywania kar.

Każda intencja posiada unikalny `consequence_id`. Executor przed zapisem sprawdza, czy intencja nie została już wykonana.

```text
prepare intent
→ validate current state
→ atomic apply
→ mark executed
→ emit result
```

Jeżeli stan gry zmienił się i intencji nie można bezpiecznie wykonać, zapisuje ona wynik `rejected` albo `superseded`, zamiast zgadywać.

### `incident_audit_log`

Przechowuje techniczną historię:

- stan miernika ryzyka operacji;
- przekroczenie progu ostrzeżenia albo incydentu;
- połączenie operacji z incydentem;
- zmianę poziomu;
- utworzenie kapsuły NPC;
- otrzymanie detection candidate;
- odtworzenie trajektorii i wynik walidacji;
- ostrzeżenie;
- decyzję wykrycia;
- intencję i wykonanie konsekwencji;
- ręczne zatrzymanie albo kill switch.

Log musi umożliwić odpowiedź na pytanie: **dlaczego ten gracz został wykryty i ukarany?**

### `incident_replay`

Narzędzie diagnostyczne odtwarza incydent na podstawie:

- reguł w konkretnej wersji;
- seeda;
- zegara;
- historii zmian miernika operacji;
- kapsuł i wersji algorytmu zachowania;
- minimalnych snapshotów podejrzanych i terytoriów.

Replay nie wykonuje prawdziwych konsekwencji. Porównuje oczekiwane i rzeczywiste decyzje.

## Czas i deterministyczność

Każdy moduł decyzyjny otrzymuje czas przez jawny `clock`, a nie przez rozproszone wywołania czasu systemowego. Frontend utrzymuje synchronizowany `world_time` i nie używa bezpośrednio lokalnego zegara urządzenia jako źródła prawdy.

Każda inicjacja i walidacja posiada kontekst czasu:

```json
{
  "world_time": "ISO-8601",
  "time_sync_version": 12,
  "sequence": 1402,
  "allowed_clock_drift_ms": 1500
}
```

Frontend i backend korzystają z tej samej wersjonowanej funkcji trajektorii. Pozycja jest funkcją kapsuły i czasu:

```text
position_at(capsule, world_time) → lat, lng, direction, animation_state
```

Losowość ruchu korzysta ze stabilnego `trajectory_seed`. Dzięki temu klient może płynnie animować NPC, a backend może odtworzyć jego pozycję tylko wtedy, gdy otrzyma kandydata wykrycia.

## Model podejrzanego

Podejrzany jest przypisany do incydentu przez działanie, nie przez samą obecność geograficzną.

Minimalny kontekst:

```json
{
  "actor_id": "player_...",
  "operation_ids": [],
  "suspicion": 72,
  "last_active_at": "ISO-8601",
  "online": true,
  "active_in_incident": true,
  "related_territory_ids": []
}
```

Wejście obcego gracza do strefy nie dodaje go automatycznie do podejrzanych. Dopiero emitująca heat aktywność może zmienić jego status.

## Ochrona terytorium i gracza offline

Przed każdą decyzją wykrycia wykonywana jest jawna reguła ochrony:

```text
is_passive_or_offline
AND is_inside_own_stable_territory
AND incident_has_no_relation_to_actor
AND incident_has_no_relation_to_any_actor_territory
→ protected_from_detection
```

Patrol może przejechać przez takie terytorium, ale nie zatrzymuje właściciela i nie generuje konsekwencji.

Ochrona nie działa, jeśli:

- gracz wywołał incydent;
- incydent dotyczy operacji gracza;
- incydent dotyczy któregokolwiek jego terytorium;
- na jego terytorium trwa przeszukanie lub konflikt związany z incydentem;
- gracz rozpoczyna w strefie nową aktywność emitującą heat;
- wcześniej został skutecznie wykryty, a decyzja oczekuje na wykonanie.

Wylogowanie nie kasuje prawidłowo powstałej decyzji, ale nie może samo stworzyć nowej decyzji.

## Moduły frontendu

### `response_actor_runtime`

Frontend przejmuje kapsułę NPC i tworzy aktora na tej samej warstwie co awatar gracza.

NPC nie jest zwykłym markerem. Korzysta z istniejącego systemu **snikersów**:

- pozycji aktora;
- interpolacji ruchu;
- kierunku przemieszczania;
- animacji chodzenia albo biegu;
- stanów bezczynności;
- animacji skanowania;
- wejścia w pościg;
- zakończenia interwencji i zejścia z mapy.

Wspólny renderer rozróżnia encje przez `actor_type`:

```text
player
response_npc
```

Nie wolno duplikować kompletnego systemu animacji tylko dla służb. Rodziny NPC dostają własne skiny, emblematy, tempo, efekty skanowania i zestawy stanów na istniejącym szkielecie aktora.

### `npc_trajectory_runtime`

Oblicza lokalną pozycję jako funkcję kapsuły i czasu. Nie odpytuje backendu o każdy krok i nie zapisuje ruchu.

```text
position_at(capsule, synchronized_world_time)
→ position
→ direction
→ animation_state
```

Zmniejszenie liczby klatek albo chwilowe uśpienie karty nie zmienia logicznej trajektorii. Po wznowieniu frontend wylicza pozycję dla aktualnego czasu, zamiast nadrabiać wszystkie pominięte kroki.

### `local_detection_probe`

Porównuje wyliczoną pozycję NPC z dostępnymi zasobami frontendu mapy:

- pozycjami podejrzanych aktorów;
- stanem ich aktywnych operacji;
- widocznym kontekstem terytoriów;
- czasem ostrzeżenia;
- promieniem wykrywania.

Probe nie wykonuje kary. Po spełnieniu warunków tworzy `detection_candidate` i wysyła go do backendu.

Frontend może ograniczyć powtórzenia lokalnie, ale ostateczna deduplikacja zawsze należy do backendu. Publiczny incydent może być obserwowany przez wielu klientów.

Probe korzysta z `tracking_tokens`, a nie z publicznej listy sprawców. Token jest dołączany do `detection_candidate`; frontend nie rozstrzyga samodzielnie tożsamości ani prawa do nałożenia kary.

### Warstwa wizualna służb

Pierwsza wersja powinna przewidywać rodziny:

- patrol lokalny;
- policja dochodzeniowa;
- cyberpolicja;
- służby specjalne;
- ciężka jednostka interwencyjna.

Każda rodzina może zmieniać wygląd snikersa i animacje specjalne, ale zachowuje ten sam kontrakt aktora. Gracz powinien natychmiast rozumieć, że służba jest ruchomym aktorem zdolnym go znaleźć, a nie dekoracją mapy.

Promień wykrywania nie musi być stale widoczny. Może pulsować podczas skanu, pojawiać się po ostrzeżeniu albo być wskazywany przez efekt sygnału, żeby nie zasłaniać mapy.

## Modernizacja terytoriów

### Problem obecnego systemu

Mapa cyklicznie pobiera ciężkie snapshoty:

- `/api/map/player-areas`;
- `/api/map/clan-vulnerabilities`;
- `/api/operations?summary=1`.

`player-areas` łączy odczyt terytoriów, wykrywanie konfliktów i przygotowanie renderu. Response Network nie może dokładać do tego kolejnego pełnego przeliczenia przy każdym ruchu NPC.

### Docelowy podział

```text
territory store
├── territory geometry snapshot
├── territory ownership state
├── territory conflict state
└── territory change log / delta
```

Geometria zmienia się rzadziej niż stan właściciela, konfliktu albo oznaczeń. Te dane powinny mieć osobne wersje i osobne delty.

### `territory_context_reader`

Response Network korzysta z wąskiego read modelu:

```json
{
  "territory_id": "territory_...",
  "owner_id": "player_...",
  "clan_id": "clan_...",
  "status": "stable",
  "conflict_id": null,
  "bbox": {},
  "version": 18
}
```

Silnik nie pobiera geometrii całego świata. Zapytanie przestrzenne zwraca tylko terytoria przecinające obszar incydentu albo zawierające konkretny punkt.

### Migracja bez big-bang rewrite

1. Dodać pomiary czasu i rozmiaru odpowiedzi istniejących endpointów.
2. Wyodrębnić read-only territory context bez zmiany zasad gameplayu.
3. Dodać wersjonowanie zmian terytoriów.
4. Wystawić snapshot startowy i deltę.
5. Przełączyć jedną warstwę mapy na nowy kontrakt.
6. Zachować stary snapshot jako kontrolowany recovery path.
7. Dopiero po stabilizacji podłączyć Response Network.

Stary i nowy odczyt mogą przez pewien czas działać równolegle w trybie porównawczym.

## Trwałość danych

### Dane trwałe

- identyfikator oraz podsumowanie incydentu;
- powiązane operacje i wersje ich mierników ryzyka;
- podejrzani i relacje z operacjami;
- wykonane decyzje i konsekwencje;
- historia eskalacji;
- końcowy rezultat;
- dane potrzebne do replayu;
- zdarzenia publikowane do innych systemów.

### Dane frontendowe możliwe do odbudowania

- dokładna pozycja patrolu;
- kierunek ruchu;
- krótkotrwały stan animacyjny;
- cache przestrzenny.

Frontend nie zapisuje tych danych na backendzie. Po ponownym otwarciu mapy pobiera aktywną kapsułę i odtwarza bieżący stan z `trajectory_seed`, `behavior_version` oraz aktualnego czasu. Ponowne utworzenie aktora nie może samo wywołać zatrzymania.

## API mapy

### Snapshot początkowy

```text
GET /api/map/incidents
GET /api/map/incident-npc-capsules
```

Snapshot zawiera wyłącznie publiczne dane potrzebne do renderu. Nie ujawnia podejrzanych ani prywatnych powodów incydentu.

### Delta

Preferowany jest jeden wersjonowany strumień albo scope istniejącego mechanizmu zmian:

```text
incident.created
incident.updated
incident.resolved
npc.spawned
npc.updated
npc.removed
territory.updated
territory.conflict_changed
```

`npc.spawned` przenosi pełną kapsułę zachowania. Nie istnieje cykliczna delta `npc.moved`, ponieważ pozycję oblicza frontend. `npc.updated` służy wyłącznie zmianie zachowania, eskalacji albo wcześniejszemu zakończeniu jednostki.

Każda delta posiada `seq`, `entity_id`, `version` i minimalny payload.

Frontend ignoruje starszą wersję encji. Luka w sekwencji uruchamia recovery tylko dla konkretnego scope, nie pełne odświeżenie całej mapy.

### Prywatny stan gracza

Ostrzeżenia i wynik wykrycia nie trafiają do publicznego endpointu mapy. Są dostarczane przez istniejący prywatny kanał zmian albo osobny scope użytkownika.

### Feedback wykrycia

```text
POST /api/map/incidents/detection-candidates
```

Endpoint przyjmuje kandydata z `tracking_token`, identyfikatorem kapsuły, czasem wykrycia i pozycjami obliczonymi przez klienta. Odpowiedź może mieć stan:

```text
accepted
duplicate
rejected
expired
shadow_only
```

`accepted` oznacza zatwierdzenie przez backend, a nie automatycznie wykonaną karę. Konsekwencję wykonuje dopiero idempotentny `consequence_executor`.

## Integracje

### Operacje

Operacja posiada własny miernik ryzyka aktualizowany w punktach domenowych, a nie podczas renderowania jej stanu. Przekroczenie progu tworzy jedno wersjonowane zdarzenie inicjujące.

Przerwanie przez służby następuje wyłącznie przez `consequence_executor` i wskazuje konkretną operację.

### BlackNet

Incydenty publikują zatwierdzone fakty świata:

- typ hotspotu;
- przybliżoną lokalizację;
- poziom reakcji;
- liczbę jednostek;
- trend aktywności;
- czas ważności;
- bezpieczny `cta_action` teleportu albo otwarcia mapy.

BlackNet nie odczytuje prywatnej listy podejrzanych.

### Teleport

Teleport korzysta z przybliżonego punktu wejścia poza bezpośrednim promieniem wykrywania. Zmiana pozycji zawsze wymaga potwierdzenia `OK/ANULUJ`.

### Radio i Cyberner

Otrzymują zdarzenia wysokiego poziomu, nie odpytują tabel runtime. Publikacja narracyjna nie blokuje inicjacji ani walidacji incydentów.

### GhostNetwork

W przyszłości operacje GhostNetworku otrzymują te same mierniki ryzyka z dodatkowymi modyfikatorami. Nie dostają osobnej ścieżki kar ani własnego silnika NPC.

## Feature flagi i kill switche

Minimalny zestaw:

```text
response_operation_risk_enabled
response_incidents_enabled
response_public_map_enabled
response_npc_capsules_enabled
response_frontend_actors_enabled
response_local_detection_enabled
response_detection_validation_enabled
response_detection_shadow_enabled
response_player_warnings_enabled
response_operation_cancel_enabled
response_confiscation_enabled
response_judgment_enabled
response_blacknet_enabled
```

Oddzielne kill switche muszą natychmiast wyłączać:

- tworzenie nowych incydentów;
- wykrywanie;
- wykonywanie konsekwencji;
- publikację na mapę.

Wyłączenie konsekwencji nie usuwa danych potrzebnych do analizy.

## Tryby działania

### `disabled`

Brak przetwarzania.

### `observe`

Ryzyko operacji i incydenty są liczone oraz logowane, ale niewidoczne dla graczy.

### `shadow`

Frontend symuluje NPC i wysyła kandydatów wykrycia. Backend je waliduje i zapisuje, co by się wydarzyło, ale nie ostrzega i nie karze.

### `visible_safe`

Incydenty i NPC są publiczne, ostrzeżenia działają, ale konsekwencje pozostają wyłączone.

### `limited_enforcement`

Możliwe jest przerwanie operacji, lecz konfiskaty i Judgment są wyłączone.

### `full`

Wszystkie zatwierdzone konsekwencje działają.

## Strategia testów

### Testy jednostkowe

Obejmują czyste reguły:

- naliczanie miernika ryzyka operacji;
- progi tworzenia i eskalacji;
- scalanie incydentów;
- ochrona terytorium;
- zachowanie offline;
- identyczność trajektorii frontend/backend;
- walidację detection candidate;
- dobór konsekwencji;
- deduplikacja i idempotencja.

### Scenariusze JSON

Każdy scenariusz definiuje:

- czas początkowy;
- seed;
- graczy i ich stan;
- proste terytoria;
- operacje;
- kolejne wersje miernika ryzyka;
- incydenty i kapsuły NPC;
- czasy próbkowania trajektorii;
- oczekiwane decyzje i delty.

Scenariusze nie wymagają przeglądarki ani rzeczywistego oczekiwania.

Obowiązkowe przypadki:

1. Cicha operacja bez incydentu.
2. Głośna operacja z ostrzeżeniem i ucieczką.
3. Wykrycie właściwego podejrzanego.
4. Obcy bierny gracz przechodzi przez hotspot i nie zostaje ukarany.
5. Offline właściciel na własnym niezwiązanym terytorium jest bezpieczny.
6. Incydent dotyczący terytorium wyłącza ochronę właściciela.
7. Kilka operacji scala się w jeden incydent.
8. Dwa odległe źródła tworzą osobne incydenty.
9. Wielokrotnie wysłany kandydat wykrycia nie wykonuje kary drugi raz.
10. Restart nie generuje fałszywego zatrzymania.
11. Luka delta uruchamia recovery wyłącznie właściwego scope.
12. Wyłączenie kill switcha blokuje karę przygotowaną, lecz niewykonaną.
13. Frontend i backend obliczają tę samą pozycję NPC dla tej samej kapsuły i czasu.
14. Uśpienie karty i wznowienie animacji nie przesuwa logicznej trajektorii.
15. Kilku obserwatorów zgłasza to samo wykrycie, ale backend zatwierdza je tylko raz.
16. Zmieniony seed, czas albo wersja zachowania powodują odrzucenie feedbacku.

### Test replay

Każdy błąd produkcyjny możliwy do zapisania jako paczka replay powinien być odtwarzalny lokalnie jednym poleceniem testowym.

### Testy kontraktowe

Sprawdzają zgodność:

- miernika ryzyka operacji;
- kapsuły NPC i wersji algorytmu trajektorii;
- detection candidate oraz odpowiedzi walidatora;
- publicznego snapshotu i delt mapy;
- prywatnych ostrzeżeń;
- consequence intentów;
- faktów dla BlackNetu.

### Testy wydajności

Osobny zestaw symuluje rosnącą liczbę:

- aktywnych graczy;
- terytoriów;
- aktualizacji mierników ryzyka na minutę;
- równoczesnych incydentów;
- NPC;
- klientów pobierających delty.

Mierzone są co najmniej `avg`, `p95`, `p99`, maksimum, liczba zapytań i rozmiar payloadu.

Test musi wykazać, że ruch NPC nie generuje cyklicznych requestów pozycji, zapisów backendu ani pełnego snapshotu terytoriów.

## Obserwowalność

Wymagane metryki:

```text
operation_risk_updates_total
operation_warning_threshold_total
operation_incident_threshold_total
incidents_active
incidents_created_total
incidents_merged_total
incident_evaluation_ms
npc_capsules_active
npc_capsules_issued_total
detection_candidates_received_total
detection_candidates_deduplicated_total
detection_candidates_rejected_total
trajectory_validation_ms
detection_decisions_total
detection_shadow_mismatch_total
consequences_prepared_total
consequences_executed_total
consequences_rejected_total
incident_delta_events_total
incident_delta_recovery_total
territory_context_query_ms
```

Każdy log decyzji zawiera `incident_id`, `candidate_id`, `decision_id`, `actor_id`, wersję reguł, wersję zachowania i powody.

## Budżety bezpieczeństwa i wydajności

Dokładne wartości zostaną ustalone po pomiarze obecnej produkcji, ale przed uruchomieniem kar muszą istnieć jawne limity:

- maksymalna liczba aktywnych incydentów na obszar;
- maksymalna liczba NPC na incydent i globalnie;
- maksymalną liczbę inicjacji incydentów w oknie czasu;
- maksymalną liczbę kandydatów wykrycia przyjmowanych od klienta;
- maksymalny rozmiar delty;
- limit historii aktywnej w pamięci;
- backpressure dla feedbacku oraz lokalne ograniczenie częstotliwości probe.

W razie przeciążenia frontend może obniżyć częstotliwość animacji albo połączyć efekty wizualne. Logiczna pozycja nadal wynika z czasu. Backend może ograniczać duplikaty feedbacku, ale nie może pomijać zatwierdzonych decyzji i konsekwencji.

## Kolejność wdrożenia

### Etap 1 — pomiary i fundament terytoriów

- zmierzyć istniejące snapshoty mapy;
- stworzyć wąski territory read model;
- dodać wersjonowanie i delta log;
- przygotować kontrolowany recovery snapshot.

### Etap 2 — miernik ryzyka i incydenty w trybie `observe`

- miernik ryzyka w operacji;
- progi ostrzeżenia i incydentu;
- incident engine i store;
- audit log;
- scenariusze oraz deterministyczny clock.

### Etap 3 — publiczna mapa bez ryzyka

- snapshot i delta incydentów;
- render hotspotów;
- integracja BlackNetu;
- brak NPC i konsekwencji.

### Etap 4 — NPC w trybie `shadow`

- response dispatcher;
- fabryka kapsuł NPC;
- frontendowe aktory na warstwie snikersów;
- wspólna funkcja trajektorii frontend/backend;
- lokalny detection probe;
- backendowy validator kandydatów;
- replay.

### Etap 5 — ostrzeżenia i `visible_safe`

- prywatne ostrzeżenia;
- widoczne strefy;
- telemetryczne porównanie przewidywań z zachowaniem graczy;
- nadal brak kar.

### Etap 6 — ograniczone konsekwencje

- consequence policy i executor;
- początkowo tylko przerwanie operacji;
- pełna idempotencja i kill switch;
- analiza odrzuceń oraz reklamacji.

### Etap 7 — pełny Response Network

- konfiskaty;
- Judgment;
- Radio i Cyberner;
- docelowe zasady wygaszania;
- readiness check.

### Etap 8 — fundament pod GhostNetwork

- potwierdzić stabilność terytoriów, konfliktów i incydentów;
- wystawić kontrakty mierników ryzyka dla operacji na częściach;
- nie implementować jeszcze logiki 20 części w module incydentów.

## Warunki uruchomienia konsekwencji

Konfiskaty i Judgment nie mogą zostać włączone, dopóki:

1. deterministyczne scenariusze nie przechodzą;
2. replay odtwarza decyzje;
3. idempotencja została potwierdzona;
4. ochrona offline i własnego terytorium ma osobne testy;
5. restart nie powoduje fałszywych zatrzymań;
6. kill switch działa bez restartu aplikacji;
7. tryb shadow działał przez ustalony okres bez krytycznych rozbieżności;
8. nie występuje regresja p95 mapy;
9. ruch NPC działa lokalnie i nie powoduje cyklicznych zapisów ani pełnego przeliczenia terytoriów;
10. każda kara ma czytelny audit trail.

## Warunki gotowości Response Networku

System jest gotowy jako fundament GhostNetworku, gdy:

- operacje posiadają wersjonowane mierniki ryzyka;
- incydenty poprawnie się scalają, eskalują i wygaszają;
- backend wydaje kompletne kapsuły NPC;
- NPC poruszają się deterministycznie na frontendowej warstwie snikersów;
- backend odtwarza trajektorię i waliduje feedback;
- podejrzani są wybierani na podstawie działań;
- bierni i offline gracze są chronieni zgodnie z zasadami;
- konsekwencje są atomowe oraz idempotentne;
- mapa używa lekkich snapshotów i delt;
- BlackNet publikuje hotspoty bez ujawniania sprawców;
- system można diagnozować przez log, metryki i replay;
- każdy ryzykowny element posiada osobną flagę i kill switch;
- stary system terytoriów nie jest już wymagany do pełnego cyklicznego renderowania każdej zmiany.

## Decyzja końcowa

Response Network zostaje wdrożony jako pierwszy duży mechanizm świata przed GhostNetworkiem.

Modernizacja terytoriów jest częścią fundamentu technicznego tego wdrożenia, ale nie zmienia na początku ich zasad gameplayowych. Najpierw powstaje lekki read model, wersjonowanie oraz delta. Następnie system przechodzi kolejno przez `observe`, `shadow`, `visible_safe`, `limited_enforcement` i dopiero na końcu `full`.

Backend odpowiada za inicjację, frontend za lekką symulację ruchu oraz zgłoszenie wykrycia, a backend ponownie przejmuje kontrolę przy walidacji i konsekwencjach.

Takie podejście pozwala wykorzystać istniejący system aktorów i animacji, testować główny mechanizm rozgrywki na realnym ruchu bez ryzyka przypadkowych kar oraz uniknąć serwerowego przesuwania każdego NPC.
