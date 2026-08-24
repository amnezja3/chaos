# CHAOS — Sprint 0 Summary

Sprint 0 zamyka warstwę kontraktów gameplayu dla CHAOS.

CHAOS:

```text
Cyber Hacking Adventure Of Senses
```

Hasło:

```text
Hack the digital senses of the modern world.
Hakuj cyfrowe zmysły współczesnego świata.
```

---

## 1. Lista dokumentów Sprintu 0

| Dokument | Rola |
| --- | --- |
| `doc/overview/name_of_game.md` | Nazwa gry, rozwinięcie CHAOS i hasło. |
| `doc/plans/plan_zero_gameplay_base.md` | Plan bazowy Sprintu 0 i zakres kontraktów. |
| `doc/gameplay/gameplay_terms.md` | Słownik pojęć, identyfikatorów i zasad rozdzielenia odpowiedzialności. |
| `doc/gameplay/source_type_mapping.md` | Mapowanie `source_type -> target_type`. |
| `doc/gameplay/world_objects.md` | Model obiektów świata. |
| `doc/gameplay/map_actions.md` | Kontrakt akcji mapy. |
| `doc/gameplay/app_contract.md` | Kontrakt aplikacji. |
| `doc/gameplay/gameplay_matrix.md` | Macierz gameplayu i szybka tabela relacji akcja-operacja-zasób. |
| `doc/gameplay/operations.md` | Kontrakt operacji jako centralnego bytu gameplayu. |
| `doc/gameplay/movement_model.md` | Model aktywnego świata i odświeżania bez realtime loopa. |
| `doc/gameplay/resource_types.md` | Model danych i zasobów produkowanych przez operacje. |
| `doc/gameplay/file_model.md` | System plików jako gameplay inventory. |
| `doc/gameplay/data_economy.md` | Ekonomia danych, Ghost Exchange i cykl życia sprzedaży. |
| `doc/gameplay/risk_events.md` | Kontrakt systemu ryzyka. |
| `doc/gameplay/gameplay_loop.md` | Pełna pętla gameplayu. |
| `doc/sprints/sprint0_summary.md` | Zamknięcie Sprintu 0 i mapa źródeł prawdy. |

Dokumenty historyczne / robocze:

| Dokument | Status |
| --- | --- |
| `doc/history/game_play_260626.md` | Dokument koncepcyjny, źródło inspiracji, nie główny kontrakt. |
| `doc/gameplay/action_player.md` | Historia i plan player actions / player actor, pomocniczy wobec Sprintu 0. |

---

## 2. Źródła prawdy

| Źródło prawdy | Zakres |
| --- | --- |
| `gameplay_terms.md` | Słownik pojęć i identyfikatorów. |
| `source_type_mapping.md` | Mapowanie źródeł mapy na typy celów. |
| `world_objects.md` | Obiekty świata i ich klasyfikacja. |
| `map_actions.md` | Akcje mapy i ich intencje. |
| `app_contract.md` | Kontrakt aplikacji, `app.interface`, `app.map_actions`, efekty aplikacji. |
| `operations.md` | Kontrakt operacji. |
| `movement_model.md` | Aktywny świat, ruch, timery i refresh. |
| `resource_types.md` | Model danych i zasobów. |
| `file_model.md` | Inventory plików i katalogi. |
| `data_economy.md` | Ghost Exchange, wycena i sprzedaż danych. |
| `risk_events.md` | Ryzyko, eventy, modyfikatory i konsekwencje. |
| `gameplay_loop.md` | Pełny gameplay loop. |

Decision:

* Przyjęto: jeśli starsza prosta tabela w `gameplay_matrix.md` różni się od nowszych dokumentów, wygrywają dokumenty kontraktowe z późniejszych sprintów: `map_actions.md`, `operations.md`, `resource_types.md`, `file_model.md`, `data_economy.md`, `risk_events.md`.
* Przyjęto: `gameplay_matrix.md` zostaje szybką mapą orientacyjną, nie jedynym źródłem prawdy.

---

## 3. Diagram zależności

```text
World Objects
↓
Map Actions
↓
Applications
↓
Operations
↓
Movement
↓
Resources
↓
Files
↓
Ghost Exchange
↓
Risk
↓
Gameplay Loop
```

### Opis zależności

#### World Objects

Obiekty świata są podstawą mapy.

Opisują, co gracz widzi i z czym może wejść w interakcję.

Źródło prawdy:

* `world_objects.md`
* `source_type_mapping.md`

#### Map Actions

Akcje mapy opisują intencję gracza.

Źródło prawdy:

* `map_actions.md`

#### Applications

Aplikacje obsługują akcje mapy przez `app.map_actions` i otwierają UI przez `app.interface`.

Źródło prawdy:

* `app_contract.md`

#### Operations

Operacje są centralnym bytem gameplayu.

Aplikacja tworzy operację, a operacja żyje w świecie gry.

Źródło prawdy:

* `operations.md`

#### Movement

Movement opisuje, jak aktywne operacje i obiekty aktualizują się bez realtime loopa.

Źródło prawdy:

* `movement_model.md`

#### Resources

Resources opisują wartość gameplayową produkowaną przez operacje.

Źródło prawdy:

* `resource_types.md`

#### Files

Files są widoczną reprezentacją zasobów i inventory gracza.

Źródło prawdy:

* `file_model.md`

#### Ghost Exchange

Ghost Exchange domyka ekonomię danych.

Źródło prawdy:

* `data_economy.md`

#### Risk

Risk jest warstwą przekrojową, która może wpływać na akcje, operacje, dane i ekonomię.

Źródło prawdy:

* `risk_events.md`

#### Gameplay Loop

Gameplay loop spina wszystko w powtarzalną pętlę progresu.

Źródło prawdy:

* `gameplay_loop.md`

---

## 4. Definition of Done Sprint 0

### Słownik i identyfikatory

Status: done.

Istnieje:

* `gameplay_terms.md`
* jasne rozróżnienie `map_action_id`, `operation_type`, `target_type`, `source_type`, `target_mode`, `resource_type`, `file_category`, `market_category`, `risk_event`

### Obiekty świata

Status: done.

Istnieje:

* `source_type_mapping.md`
* `world_objects.md`

Wiadomo:

* jak `source_type` mapuje się na `target_type`,
* jak obiekty świata prowadzą do menu mapy.

### Akcje mapy

Status: done.

Istnieje:

* `map_actions.md`

Wiadomo:

* które akcje wymagają aplikacji,
* które akcje uruchamiają operacje,
* które akcje są tylko warunkiem hackowania,
* że `app.map_actions` jest routerem aplikacji z mapy.

### Aplikacje

Status: done.

Istnieje:

* `app_contract.md`

Wiadomo:

* `app.interface` mówi, jak otworzyć UI,
* `app.map_actions` mówi, jakie akcje mapy aplikacja obsługuje,
* `app.resource_types` mówi, co aplikacja może produkować.

### Operacje

Status: done.

Istnieje:

* `operations.md`

Wiadomo:

* aplikacja tworzy instancję operacji,
* operacja może żyć w świecie,
* operacja może produkować zasoby,
* operacja może generować ryzyko.

### Aktywny świat

Status: done.

Istnieje:

* `movement_model.md`

Wiadomo:

* nie ma realtime loopa,
* stan aktywnych obiektów liczy się przy refreshu,
* timestampy i `procedural_seed` są źródłem prawdy,
* checkpointy są eventami gameplayowymi.

### Zasoby

Status: done.

Istnieje:

* `resource_types.md`

Wiadomo:

* które zasoby są plikami,
* które są sprzedawalne,
* które są stanem technicznym,
* jak działa kompletność danych.

### Pliki

Status: done.

Istnieje:

* `file_model.md`

Wiadomo:

* system plików jest inventory,
* `/tools` jest katalogiem aplikacji,
* `/data/*` jest katalogiem danych,
* pliki mogą być sprzedawane albo usuwane.

### Ekonomia danych

Status: done.

Istnieje:

* `data_economy.md`

Wiadomo:

* Ghost Exchange jest głównym rynkiem danych,
* dane mają lifecycle,
* sprzedaż tworzy mail i transfer HC,
* po sprzedaży plik domyślnie znika z `/data`.

### Ryzyko

Status: done.

Istnieje:

* `risk_events.md`

Wiadomo:

* risk pipeline to `Action → Risk signal → Risk score → Risk event → Consequence`,
* nie ma losowania co sekundę,
* ryzyko może dawać warning, detection, cooldown, HC loss, jail, reputation loss.

### Gameplay loop

Status: done.

Istnieje:

* `gameplay_loop.md`

Wiadomo:

* jak gracz przechodzi od obiektu świata do nowych aplikacji,
* jak dane zamieniają się w HC,
* jak HC wracają do progresu przez Googleplex.

---

## 5. Sprint 0 Closure

Sprint 0 zamknięty.

Projekt gotowy do implementacji Sprintu 1.

Sprint 1 powinien rozpocząć się od implementacji.
