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

- Browser desktop styled as an in-game operating system.
- Login, onboarding, profile, wallet, email, terminal, file manager and app launcher.
- Real map integration with POI scanning.
- Player avatar on the map with directional motorcycle sprites.
- Friends, contacts, private chat and group chat MVP.
- Player actors on the map with contextual actions.
- Territory and conflict mechanics in active development.
- SQLite-backed profile/game state.
- Googleplex app store.
- GhostLab IDE concept for creating pro-system tools.
- Pro-system tools for hacked player targets:
  - System Log Reader
  - Security Panel Proxy
  - Financial Sniffer
  - Friend Kicker
  - Arsenal Cleaner
- Full Sprint 0 design documentation for gameplay contracts.

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

Sprint 0 is closed and defines the contracts for future implementation.

Start with the complete [`doc/README.md`](doc/README.md) documentation index.

Key documents:

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

Install dependencies as needed. The dependency list is still being formalized.

Run the app:

```powershell
python run.py
```

Open:

```text
http://127.0.0.1:5000
```

Developer test account, if present in the local database:

```text
admin
1234
```

## Repository Status

This repository is early-stage game development.

Expect:

- fast iteration,
- evolving data contracts,
- rough edges in UI,
- prototype mechanics becoming formal systems over time.

The current priority is implementing the Sprint 1+ roadmap after closing Sprint 0 documentation.

## Roadmap Snapshot

Sprint 1+ focuses on implementing the core gameplay loop:

1. Map Action Router + App Contract Runtime
2. Tool Selection UX
3. Operation Core
4. Active Operations and Active Map Objects
5. Movement Refresh Engine
6. Vehicle Tracking + GPS Logs
7. Device Intelligence
8. Camera Stream + Camera Shutdown
9. Audio / Microphone Sniffer
10. ATM + Persistent Sniffer
11. File Inventory
12. Ghost Exchange
13. Sale Flow + Mail + HC
14. Risk MVP
15. Support Operations
16. Operation Lifecycle
17. Resource Completeness + Pricing
18. Googleplex Progression
19. Integration Playtest
20. Gameplay Loop Closure v1

See [`doc/history/game_play_260626.md`](doc/history/game_play_260626.md) for the full roadmap.

## License

No license has been selected yet.

Decision pending before public reuse or distribution.
