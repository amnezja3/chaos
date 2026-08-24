# Sprint 112 - GhostNetwork catalog

Status: implemented as canonical static catalog only.

## Artifacts checked

Sprint 112 was checked against:

* `doc/overview/clans_machines.md`
* `doc/systems/ghostnetwork/ghostnetwork_architecture.md`
* `doc/sprints/sprint_110_integration_audit.md`
* `doc/sprints/sprint_111_ghostnetwork_repository.md`
* `doc/history/game_play_180726.md`

Consistency decision: the catalog is a versioned world definition. It is not
active cycle state, does not create `ghost_parts`, does not mutate profiles and
does not own map or territory runtime.

## Implemented

Added `ghostnetwork/catalog.py` as the single canonical source for Sprint 112:

* `catalog_version = ghost-canon-1`;
* four clans;
* four machines;
* twenty professions;
* twenty parts;
* twenty catalog-only ability contracts;
* first topology anchor sequence;
* full catalog validator;
* stable checksum;
* onboarding projection;
* internal catalog diagnostics;
* read-only profile identity normalizer.

The catalog includes:

* VIREX / VIREX ORACLE;
* Echo Wolnosci / ECHO LIBERTAS;
* Siatka Widmo / PHANTOM VEIL;
* Straznicy Ladu / SENTINEL AEGIS.

Canonical part checks:

* `V1` is `Ledger Nexus` and maps to `broker`;
* `S5` is `Judgment Core` and maps to `executor`.

## Service integration

`GhostNetworkService` now exposes:

* `get_catalog_diagnostics()`;
* `get_onboarding_catalog()`;
* `validate_catalog()`;
* catalog validation inside `health_check()`.

`ghostnetwork/contracts.py` now routes clan/profession normalization through
the catalog normalizer instead of local placeholder string formatting.

## Safety boundaries

Sprint 112 does not implement:

* active cycles;
* creation of records in `ghost_parts`;
* runtime topology;
* drops;
* map markers;
* part activation;
* superpower mechanics;
* RSP;
* reputation;
* transmission;
* profile migration.

The onboarding projection does not reveal:

* topology anchor;
* connections;
* locations;
* transmission rules.

## Validation

Executed:

```text
python -m unittest tests.test_ghostnetwork_repository tests.test_ghostnetwork_catalog
python -m py_compile ghostnetwork\__init__.py ghostnetwork\catalog.py ghostnetwork\contracts.py ghostnetwork\service.py
```

Result:

```text
22 tests OK
py_compile OK
```

## DoD

Done:

* one canonical source of four clans;
* four machines;
* exactly 20 professions and 20 parts;
* profession/part 1:1 relation;
* stable part codes;
* catalog-only ability contracts;
* versioned and validated catalog;
* profile normalization to catalog codes;
* onboarding reads catalog without duplicated definitions;
* no current world state in the catalog.
