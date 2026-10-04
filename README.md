# CHAOS

**Cyber Hacking Adventure Of Senses**

*Hack the digital senses of the modern world.*

CHAOS is a browser-based hacking game built around a living world map, a fake operating system desktop, player-made tools, territorial conflict, and an information economy.

You do not only hack computers. You hack the digital senses of the modern world:

- cameras as eyes,
- microphones as ears,
- networks as nerves,
- phones as identity,
- the internet as the nervous system of the city.

## What This Is

CHAOS is an experimental game project where the map is the entry point to gameplay.

The player scans real-world locations, marks targets, launches apps, runs operations, gathers data, sells information, earns HackCoins, buys better tools, and returns to the map with a stronger arsenal.

Core loop:

```text
World Object
-> Map Action
-> Application
-> Operation
-> Movement
-> Resource
-> File
-> Ghost Exchange
-> Mail
-> HackCoins
-> New Apps
-> Back to Map
```

## Current Features

Status reviewed: **4 October 2026**. Gameplay acceptance and pending work are
tracked separately in the [project journal](doc/history/project_journal.md).

- Browser desktop styled as an in-game operating system.
- Login, onboarding, profile, wallet, email, terminal, file manager and app launcher.
- Real map integration with POI scanning.
- Player avatar on the map with directional motorcycle sprites.
- Friends, contacts, private chat and group chat MVP.
- Player actors on the map with contextual actions.
- Territory and conflict mechanics in active development.
- SQLite-backed game state with dedicated inventory, wallet, security, session and operation stores; bounded reads and deltas on migrated gameplay paths.
- Googleplex app store.
- Simplified TermCreator, WindowMaker, ButtonMaker and AppForge editors: map-action selection, system-generated mechanics, editable projects and versioned publication. **Sprint 148 accepted by the author on 4 October 2026.**
- Installed creator editions remain unchanged until an explicit free update; withdrawal preserves installed copies. File-producing actions require file creation, with the ATM file → batch → Ghost Exchange sale loop confirmed in gameplay.
- Creator action names and icons match all 14 map-menu actions, with object descriptions and mobile-friendly labels. Scan scenes distinguish people, vehicles, cameras, ATMs and venues; cars and restaurant guests spawn at a minimum distance from their parent marker.
- GhostLab IDE: template selection, blueprint validation, compilation, versioned publication, purchases, creator payments, installation and explicit free updates.
- Pro-system tools for hacked player targets:
  - System Log Reader
  - Security Panel Proxy
  - Financial Sniffer
  - Friend Kicker
  - Arsenal Cleaner
  - Intruder Kicker
- GhostLab descendants of all six PvP tool families, with shared family usage limits.
- Player-created travel tickets: immediate single journey, creator-defined destinations, price capped at 150 HC, hidden destination coordinates in ticket flows and three post-travel reactions from customers.
- Own-system maintenance templates: safe cleanup of unsellable files, once-per-version system updates and Open/Low/Regular/All security restoration with change logs.
- Risky firmware updates: creator-configured success chance and bounded disk/scan-range gains, crash/restart on failure and a 24-hour cooldown after either outcome.
- Deep Scanner overlays for the default map scanner: branding, log presets, bounded retries/timeouts and one active application. Stage 1 is accepted; the complete five-pattern effect catalog is prepared for gameplay acceptance.
- Incident consequences, detention, prisons and criminal-record reduction notifications; individual outstanding acceptance checks remain documented.
- GhostNetwork and GhostSignal finale implementation; production finale trigger/E2E remains a separate acceptance gate.

## Design Direction

CHAOS is not just a hacking game.

It is a game about building a digital intelligence empire.

Hacking is the beginning. The real game starts when collected information becomes inventory, files become market goods, market goods become HackCoins, and HackCoins become better tools.

Important design principles:

- The map is not a screen. It is the entrance to the world.
- Apps are not the final effect. Apps start operations.
- Operations live in the world.
- Files are not decoration. Files are gameplay inventory.
- Data is the main commodity.
- Googleplex is progression.
- Ghost Exchange is the information economy.
- Risk is not flavor text. Risk changes decisions.

## Documentation

Sprint 0 and the original Sprint 1–20 roadmap are historical design references.
For current work, start with the status and roadmap below.

Start with the complete [`doc/README.md`](doc/README.md) documentation index.

Key documents:

- [Project journal](doc/history/project_journal.md) — dated progress, acceptance and unresolved checks.
- [Deep Scanner stage 1 deployment and tests](doc/runbooks/sprint_146_4_1_ghostlab_deep_scanners.md).
- [Profile hot-path contract](doc/architecture/profile_hot_path_contract_130_11_plus.md) — performance and persistence requirements.
- [`doc/overview/name_of_game.md`](doc/overview/name_of_game.md) - name, acronym and theme.
- [`doc/gameplay/gameplay_terms.md`](doc/gameplay/gameplay_terms.md) - shared vocabulary.
- [`doc/gameplay/source_type_mapping.md`](doc/gameplay/source_type_mapping.md) - map source type to target type mapping.
- [`doc/gameplay/world_objects.md`](doc/gameplay/world_objects.md) - world object model.
- [`doc/gameplay/map_actions.md`](doc/gameplay/map_actions.md) - map action contract.
- [`doc/gameplay/app_contract.md`](doc/gameplay/app_contract.md) - application contract.
- [`doc/gameplay/operations.md`](doc/gameplay/operations.md) - operation model.
- [`doc/gameplay/movement_model.md`](doc/gameplay/movement_model.md) - active world refresh model.
- [`doc/gameplay/resource_types.md`](doc/gameplay/resource_types.md) - data/resource model.
- [`doc/gameplay/file_model.md`](doc/gameplay/file_model.md) - file inventory model.
- [`doc/gameplay/data_economy.md`](doc/gameplay/data_economy.md) - Ghost Exchange and data economy.
- [`doc/gameplay/risk_events.md`](doc/gameplay/risk_events.md) - risk model.
- [`doc/gameplay/gameplay_loop.md`](doc/gameplay/gameplay_loop.md) - full gameplay loop.
- [`doc/sprints/sprint0_summary.md`](doc/sprints/sprint0_summary.md) - Sprint 0 closure.
- [`doc/history/game_play_260626.md`](doc/history/game_play_260626.md) - implementation roadmap for Sprint 1+.

## Tech Stack

- Python
- Flask
- SQLite
- Vanilla JavaScript
- Leaflet / OpenStreetMap
- HTML/CSS desktop UI

The project is intentionally lightweight and currently behaves like a game prototype/workbench rather than a packaged product.

## Running Locally

Create and activate a virtual environment if you want one:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install the declared Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the app:

```powershell
python run.py
```

Open:

```text
http://127.0.0.1:5000
```

Accounts and game state depend on the local database; there is no guaranteed
shared test account. `python run.py` starts the development server, not the
production worker setup. Deployment procedures live in `doc/runbooks/`.

Run targeted backend tests with isolated temporary runtime data:

```powershell
python -B tools/run_isolated_tests.py tests.test_ghostlab_scanner
node tests/js/test_ghostlab_scanner.js
node tests/js/test_game_sfx.js
```

Node.js is used for the JavaScript test scripts.

## Repository Status

This repository is early-stage game development.

Expect:

- fast iteration,
- evolving data contracts,
- rough edges in UI,
- prototype mechanics becoming formal systems over time.

The current priority is completing Deep Scanner acceptance and its effect catalog,
then the gameplay creators and GhostLab v2.0. A prepared fix is not a production PASS.

## Roadmap Snapshot

| Sprint | Scope | Status as of 30 September 2026 |
|---|---|---|
| 143 | Consequences, detention and prisons | Closed by author; the final 143.6 delivery-order correction has no separate reported acceptance. |
| 144.1–144.3 | GhostLab registry, authoring and product alignment | PASS. |
| 145 | System Log Reader runtime | Closed / PASS, desktop and mobile. |
| 146 | Remaining PvP descendants | Closed by author; additional regression checks moved to general gameplay testing. |
| 146.1 | Travel tickets | Closed / PASS. |
| 146.2 | Three maintenance templates | Closed / PASS. |
| 146.3 | Firmware | Purchase, installation, success, crash and update PASS. |
| [146.4](doc/sprints/sprint_146_4_ghostlab_deep_scanners.md) | Deep Scanners | Closed / author PASS, including final viewfinder effects. |
| [146.5](doc/sprints/sprint_146_5_ghostlab_v1_completion.md) | GhostLab 1.0: .lab, terminal, global/clan PTK and free products | **PASS — 2026-10-01**, accepted by the author. GhostLab 1.0 complete, including PTK editor scrolling, Plexcak and clan catalog visibility. [Runbook](doc/runbooks/sprint_146_5_ghostlab_completion.md). |
| [147](doc/sprints/sprint_147_creator_gameplay_policy.md) | Simplified creators, level-capped random power and validated Button Choice effects | Backend and progression migration deployed; gameplay confirmation recorded. Sprint 148 completes the creator editor, legacy projects and runtime rollout. [Runbook](doc/runbooks/sprint_147_creators.md). |
| [148](doc/sprints/sprint_148_creator_ux_runtime_completion.md) | Final-screen creator UX, project editing, free updates and runtime settlement | **PASS — 2026-10-04**, accepted by the author after rollout and gameplay checks. Historical projects adopted; creator UX, launch flow, required files, updates and map-action consistency completed. [Deployment runbook](doc/runbooks/sprint_148_creators.md). |
| [149](doc/sprints/sprint_149_ghostlab_v2_research.md) | GhostLab v2.0 Research | Planned after creator sprints 147–148. |
| [150](doc/sprints/sprint_150_ghostlab_v2_exchange_import.md) | Official Exchange, packages and import | Planned. |
| [151](doc/sprints/sprint_151_ghostlab_v2_community_versions.md) | Community, sharing and versions | Planned. |
| [152](doc/sprints/sprint_152_ghostlab_v2_completion.md) | Optimizer, dependencies, AI/SDK and full v2.0 acceptance | Planned. |

Research, Exchange and Documentation roadmap descriptions are not evidence of
completed runtime. Their remaining scope is explicitly assigned to 149–152.
See the [documentation index](doc/README.md) for sprint contracts and runbooks.

## License

No license has been selected yet.

Decision pending before public reuse or distribution.
