# Resource Architecture

This document defines how repository JSON files, SQLite resources and player
runtime state relate to each other in CHAOS.

## Layers

```text
Repository Content
        |
        v
static/*.json
        |
        v
JsonResourceStore seed/import
        |
        v
SQLite json_resources
        |
        v
Backend Runtime
        |
        v
Profile Runtime
```

## Rule

`static/*.json` is repository content. It is seed/reference data and is not the
runtime source of truth.

Runtime reads JSON resources from SQLite:

```text
json_resources.key
json_resources.value_json
```

Changing a file under `static/*.json` does not update the running game by
itself. A developer must run an explicit sync/import step.

## Source Of Truth

| Domain | Runtime source of truth | Repository seed/reference | Notes |
| --- | --- | --- | --- |
| App catalog | `json_resources.app_config` | `static/app_config.json` | Googleplex reads the backend catalog from SQLite. |
| User template | `json_resources.user_template` | `static/user_template.json` | Used for new profile defaults and profile sync. |
| User security | `json_resources.user_security` | `static/user_security.json` | Used as security template for targets/profiles. |
| Terminal commands | `json_resources.terminal_command` | `static/terminal_command.json` | Terminal command catalog. |
| Default mail messages | `json_resources.messages` | `static/messages.json` | Legacy/dev seed for mail bootstrap. |
| Default friends | `json_resources.friends` | `static/friends.json` | Legacy/dev seed for old friend UI. |
| Fractions | `json_resources.fractions` | `static/fractions.json` | Future/reference content. |
| Users table | `users` SQLite table | `static/users.json` / `data/game.example.sqlite3` | Runtime users live in SQLite. Example DB is preferred seed. |
| Player profiles | `users.profile_json` | `static/user_template.json` only as default shape | Runtime player state lives in profiles. |
| Player apps | `users.profile_json.apps` | Installed from `json_resources.app_config` | Installed apps are copied into the player profile. |
| Player files | `users.profile_json.files` | none | Runtime inventory. |
| Operations | `users.profile_json.operations` | none | Runtime operation state. |

## Backend Flow

```text
static/app_config.json
        |
        | explicit sync/import
        v
json_resources.app_config
        |
        v
run.py:get_app_catalog()
        |
        v
/resources.json
        |
        v
Browser / Googleplex
        |
        v
/install-app
        |
        v
profile.apps + profile.files.tools
        |
        v
/hack-action -> app.map_actions -> operations
```

## Active Seed Keys

`JsonResourceStore.seed_static_directory()` only seeds the approved resource
keys:

```text
app_config
user_template
user_security
terminal_command
messages
friends
fractions
```

Legacy/reference JSON files may remain in `static/`, but they are not imported
as runtime resources by default.

## Developer Workflow

1. Edit repository content in `static/*.json` only as content/seed.
2. Run a dry-run sync to compare repository content with SQLite runtime.
3. Run sync with `--apply` only when the runtime catalog should be updated.
4. Do not mutate `profile.apps`, `users`, operations or player files during
   static JSON sync.

## Decisions

* Decision: SQLite `json_resources` is the runtime source of truth for JSON
  resources.
* Decision: `static/*.json` remains repository content and explicit seed.
* Decision: player runtime state lives in `users.profile_json`, not in static
  JSON files.
* Decision: legacy JSON files stay in the repository for now, documented as
  reference/demo content rather than deleted.

