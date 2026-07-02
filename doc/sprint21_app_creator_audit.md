# Sprint 21 — App Creator Audit + Contract Map

Data audytu: 02.07.2026

Zakres: audyt katalogu aplikacji, kreatorow, Googleplexa, File Managera
`/tools` i wyboru narzedzi z mapy. Sprint 21 nie przebudowuje runtime i nie
wdraza jeszcze pojemnosci, jakosci ani wizardow.

## Zrodla sprawdzone

| Obszar | Pliki / funkcje |
| --- | --- |
| Runtime app catalog | `run.py`: `get_app_catalog()`, `normalize_app_contract()`, `normalize_app_contracts()` |
| Legacy inference | `run.py`: `infer_legacy_map_actions()` |
| Map tool selection | `run.py`: `get_apps_for_map_action()`, `serialize_tool_selection_app()`, `/hack-action` |
| Googleplex | `run.py`: `googleplex_catalog_payload()`, `/resources.json`, `/install-app`; `static/js/terminal.js`: Browser/Googleplex cards |
| File Manager `/tools` | `static/js/terminal.js`: `openToolSelectionForMapAction()`, `activeToolSelection`, `createFileManager()` |
| App creators | `static/js/terminal.js`: `createAppForge()`, `createTermCreator()`, `createWindowMaker()`, `createButtonMaker()`, `createGhostLabHub()`; `run.py`: `/api/apps/generate`, `build_generated_app()` |
| Content seed | `static/app_config.json` |
| Runtime resource layer | `JsonResourceStore`, `json_resources.app_config` |

## Aktualny source of truth

`static/app_config.json` jest seed/reference contentu w repo. Runtime katalogu
aplikacji czytany przez Googleplex i router mapy pochodzi z
`json_resources.app_config` przez `JsonResourceStore`.

Zmiana statycznego JSON-a nie powinna byc traktowana jako runtime update bez
jawnego syncu do SQLite. To jest zgodne z `doc/resource_architecture.md`.

## Aktualny runtime aplikacji

Flow katalogu:

```text
json_resources.app_config
↓
get_app_catalog()
↓
normalize_app_contracts()
↓
Googleplex / resources.json
↓
/install-app
↓
profile.apps + files.tools
↓
/hack-action + get_apps_for_map_action()
```

`get_app_catalog()` doklada tez katalogi systemowe:

- pro-system-tools,
- creator system apps.

Te aplikacje nie sa czescia `static/app_config.json`, ale sa widoczne w runtime
po normalizacji.

## Wynik audytu seed katalogu `static/app_config.json`

Liczba aplikacji w seed katalogu: 50.

| Klasa `map_actions_source` | Liczba | Znaczenie |
| --- | ---: | --- |
| `migration_inferred` | 15 | Aplikacje po migracji ze starych pol `type/detects`; wymagaja review w Sprint 24. |
| `admin_test_seed` | 28 | Testowe aplikacje developerskie dla triggerow mapy. |
| `none` | 7 | Aplikacje bez `map_actions`, zwykle UI/system/support. |

Najczestsze typy:

| `type` | Liczba |
| --- | ---: |
| `scanner` | 12 |
| `exploit` | 8 |
| `sniffer` | 6 |
| `tracker` | 6 |
| `camera_tool` | 4 |
| `financial_tool` | 2 |
| `audio_tool` | 2 |
| `vehicle_tool` | 2 |
| `exploit_suite` | 1 |
| `pro-system-tool` | 1 |

Interfejsy:

| `interface` | Liczba |
| --- | ---: |
| `progressbar_random` | 40 |
| `terminal` | 4 |
| `window` | 3 |
| `button_choices` | 3 |

## Pokrycie `map_actions`

| map_action_id | Aplikacje | `migration_inferred` | Bez `operation_types` i `resource_types` |
| --- | ---: | ---: | ---: |
| `atm_logs` | 2 | 0 | 0 |
| `audio_hack` | 2 | 0 | 0 |
| `camera_shutdown` | 3 | 1 | 0 |
| `camera_stream` | 3 | 1 | 0 |
| `car_hack` | 2 | 0 | 0 |
| `exploit` | 9 | 7 | 7 |
| `install_sniffer` | 2 | 0 | 0 |
| `mic_sniff` | 3 | 1 | 0 |
| `scan_hotspots` | 2 | 0 | 0 |
| `scan_ports` | 4 | 2 | 0 |
| `sniff` | 3 | 1 | 1 |
| `trace` | 6 | 4 | 0 |
| `trace_device` | 4 | 2 | 0 |
| `trace_gps` | 3 | 1 | 0 |

## Aplikacje wymagajace review

### Mylace klasyfikacje przy `scan_ports`

| App | Typ | Zrodlo | Problem | Rekomendacja |
| --- | --- | --- | --- | --- |
| `pencombo_v1` / PenCombo | `exploit_suite` | `migration_inferred` | Ma `map_actions: exploit, scan_ports`, bo stary fallback laczyl `exploit_suite` + `weak_configs/open_ports` ze skanowaniem. Dla gracza exploit suite przy `scan_ports` jest mylace. | W Sprincie 24 usunac `scan_ports`, jesli narzedzie nie jest jawnie skanerem/recon, albo oznaczyc jako hybryde w kontrakcie. |
| `scan_probe_v1` / ScanProbe | `scanner` | `migration_inferred` | Ma `scan_ports, trace`. To moze byc poprawne, ale wymaga potwierdzenia, czy trace jest intencja, czy efekt migracji. | W Sprincie 24 oznaczyc jako jawny scanner/recon albo rozdzielic funkcje. |

### Aplikacje z `map_actions`, ale bez `operation_types/resource_types`

Te aplikacje moga byc support-only, ale dzisiaj Googleplex i `/tools` nie
tlumacza tego graczowi wystarczajaco dobrze.

| App | Typ | Akcje | Problem |
| --- | --- | --- | --- |
| `deep_sniff_r2` / DeepSniff | `scanner` | `sniff` | Brak kontraktu wyniku; gracz nie wie, czy to support, czy data-producing. |
| `injector_x_v1` / InjectorX | `exploit` | `exploit` | Brak jawnej operacji i zasobow. |
| `zeroday_hunter` / ZeroDayHunter | `exploit` | `exploit` | Brak jawnej operacji i zasobow. |
| `mem_overflow_v1` / MemoryOverflow | `exploit` | `exploit` | Brak jawnej operacji i zasobow. |
| `wifibreaker_v1` / WiFiBreaker | `exploit` | `exploit` | Brak jawnej operacji i zasobow. |
| `data_corruptor_v1` / DataCorruptor | `exploit` | `exploit` | Brak jawnej operacji i zasobow. |
| `admin_test_exploit_1` / Admin Exploit Lite | `exploit` | `exploit` | Testowa aplikacja bez finalnego kontraktu. |
| `admin_test_exploit_2` / Admin Exploit Plus | `exploit` | `exploit` | Testowa aplikacja bez finalnego kontraktu. |

Decision:

- Przyjeto: w Sprincie 21 nie poprawiamy tych aplikacji w runtime. To jest
  material dla Sprintu 24, bo zmiana `map_actions` moglaby zmienic gameplay.
- Przyjeto: aplikacja bez `operation_types/resource_types` moze pozostac
  support-only, ale UI powinno to pozniej mowic jawnie.

## Googleplex cards

Obecnie Googleplex pokazuje:

- nazwe,
- opis,
- poziom aplikacji,
- cene,
- wymagania,
- `map_actions`,
- `operation_types`,
- `resource_types`.

To juz jest dobry fundament pod Sprint 21, ale brakuje:

- `target_types`,
- `map_actions_source`,
- informacji, czy kontrakt jest jawny czy migracyjny,
- `file_size` / `disk_usage`,
- `quality_score`,
- `reliability`,
- jasnego statusu support-only.

Decision:

- Przyjeto: Sprint 21 dokumentuje braki, ale nie zmienia kart Googleplexa.
  Widoczna rozbudowa UI nalezy do Sprintu 21.5/22/23.

## File Manager `/tools`

Obecny flow:

```text
/hack-action zwraca tool_selection_required
↓
openToolSelectionForMapAction(payload)
↓
activeToolSelection.matching_apps
↓
createFileManager({ toolSelection })
↓
/tools highlight + przycisk "Uzyj"
```

Podswietlenie narzedzi opiera sie na `app.map_actions` z backendu. To jest
zgodne z kontraktem Sprintu 0.

Braki:

- `/tools` pokazuje, ze narzedzie pasuje, ale nie tlumaczy jeszcze dlaczego:
  `map_actions`, `target_types`, `operation_types`, `resource_types`.
- Brakuje informacji, czy dopasowanie pochodzi z jawnego kontraktu, czy z
  `migration_inferred`.
- Brakuje statusu support-only/data-producing.

Decision:

- Przyjeto: Sprint 21 nie zmienia selection runtime. Rozszerzenie metadanych
  w `/tools` powinno wejsc dopiero po Gameplay Contract w Sprincie 21.5.

## Kreatory aplikacji

### AppForge

Lokalizacja:

- frontend: `static/js/terminal.js`, `createAppForge()`,
- backend: `run.py`, `/api/apps/generate`, `build_generated_app()`.

Aktualnie tworzy aplikacje na starym modelu:

- `type`,
- `detects`,
- `interferes_with`,
- `requires_off`,
- `disables`,
- `affects`,
- `interface`,
- `levels`,
- `creator_username`,
- `creator_nick`,
- `generated`,
- `published`.

Brakuje jawnego kontraktu:

- `map_actions`,
- `target_types`,
- `operation_types`,
- `resource_types`,
- `file_size`,
- `disk_usage`,
- `quality_score`,
- `reliability`.

### TermCreator, WindowMaker, ButtonMaker

Sa wariantami tworzenia aplikacji z konkretnym `interface`. Dzisiaj skupiaja
sie na UI/launcherze, nie na pelnym kontrakcie gameplayowym.

### GhostLab

GhostLab ma juz wlasny pipeline projektowy i publisher do Googleplexa. Jest
najblizej przyszlego modelu, ale dla Sprintu 21 nie zmieniamy jego runtime.

Decision:

- Przyjeto: kreatory zostaja zmapowane do przyszlego Googleplex Tool
  Laboratory, ale Sprint 21 nie zmienia ich UI ani backendu.
- Przyjeto: nowe pola kontraktu powinny byc opisane najpierw w dokumentacji,
  a dopiero potem wprowadzone przez Sprint 21.5/22/23.

## Dlug techniczny

1. `migration_inferred` jest nadal widoczne w aktywnym katalogu aplikacji.
2. `infer_legacy_map_actions()` moze nadal dopisywac akcje w locie jako
   `legacy_inferred`, jesli aplikacja nie ma jawnego `map_actions`.
3. Czesci exploitow brakuje `operation_types/resource_types`.
4. Googleplex nie pokazuje jeszcze zrodla kontraktu.
5. File Manager `/tools` nie pokazuje jeszcze powodow dopasowania.
6. Kreatory tworza aplikacje na starych polach mechanicznych, a nie na pelnym
   kontrakcie gameplayowym.
7. `file_size`, `disk_usage`, `quality_score`, `reliability` istnieja czesciowo
   w danych plikow/ekonomii, ale nie sa jeszcze kontraktem aplikacji.

## Ryzyka

| Ryzyko | Skutek | Sprint docelowy |
| --- | --- | --- |
| Zbyt szybkie usuniecie fallbackow legacy | Stare aplikacje przestana dzialac z mapa. | Sprint 24 |
| Dodanie storage przed kontraktem | Niespojna waga aplikacji i plikow. | Sprint 22 po 21.5 |
| Kreator generuje niepelny kontrakt | Custom tool pojawi sie w Googleplex, ale nie zadziala na mapie. | Sprint 25 |
| Mieszanie UI interface z gameplay routingiem | Powrot do starego problemu: aplikacja odpala sie, bo ma typ/interfejs, nie kontrakt. | Sprint 21.5 |

## Rekomendowany podzial dalszych sprintow

| Sprint | Minimalny zakres zmian | Pliki do zmiany | Testy regresyjne |
| --- | --- | --- | --- |
| 21.5 Gameplay Contract | Runtime checklist, opis wymaganych/opisowych pol aplikacji, status `support_only`/`data_producing` w dokumentach. | `doc/app_contract.md`, `doc/gameplay_terms.md`, `doc/file_model.md` | Audit katalogu, brak zmian mechaniki. |
| 22 Storage | `file_size`, `disk_usage`, `storage_capacity`, usage bar. | `run.py`, `static/js/terminal.js`, `static/css/style.css`, `doc/file_model.md` | Install app, generate file, sale flow, no storage regression. |
| 23 Quality | `quality_score`, `reliability`, `creator_power` w kontrakcie i wycenie. | `run.py`, `static/js/terminal.js`, `doc/app_contract.md`, `doc/data_economy.md` | Two apps same action produce different completeness/price. |
| 24 Classification Cleanup | Oczyszczenie `migration_inferred`, PenCombo/scan_ports, support-only labels. | `static/app_config.json` sync do SQLite, `run.py`, tests | `scan_ports` nie pokazuje exploit suite bez jawnego kontraktu. |
| 25 Wizard | Step-by-step creator, bez recznego JSON. | `static/js/terminal.js`, `run.py`, docs | Generated app has full contract and installs from Googleplex. |

## Definition of Done Sprintu 21

- Zidentyfikowano aplikacje jawne, migracyjne i testowe.
- Zidentyfikowano mylace dopasowania `scan_ports`.
- Sprawdzono Googleplex cards i File Manager `/tools`.
- Sprawdzono kreatory i ich brakujace pola kontraktu.
- Dokumentacja zostala uzupelniona o definicje pol przyszlych sprintow.
- Runtime mapy, Googleplexa i File Managera nie zostal przebudowany.
