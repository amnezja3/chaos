# Static JSON Files

The files in this directory are repository content. They are not live runtime
state.

Runtime reads approved JSON resources from SQLite `json_resources`. Updating a
JSON file here does not change the running game until a developer runs an
explicit sync/import tool.

## Active Seed Files

These files are allowed to seed/sync into `json_resources`:

| File | Runtime key | Role |
| --- | --- | --- |
| `app_config.json` | `app_config` | Googleplex app catalog seed. |
| `user_template.json` | `user_template` | New user/profile template seed. |
| `user_security.json` | `user_security` | Security template seed. |
| `terminal_command.json` | `terminal_command` | Terminal command seed. |

## Mail Legacy / Dev Seed

| File | Runtime key | Role |
| --- | --- | --- |
| `messages.json` | `messages` | Legacy/dev mail bootstrap seed. |
| `friends.json` | `friends` | Legacy/dev contacts seed. |

## Future / Reference

| File | Runtime key | Role |
| --- | --- | --- |
| `fractions.json` | `fractions` | Future/reference fraction content. |

## Legacy / Demo / Reference

These files stay in the repository for now, but are not runtime source of truth:

| File | Role |
| --- | --- |
| `resources.json` | Legacy reference; do not confuse with `/resources.json`, which returns the Googleplex catalog. |
| `targets.json` | Legacy/demo target fixtures. Runtime targets come from profiles, POI/map APIs and SQLite stores. |
| `system_messages.json` | Legacy/reference messages. Runtime system messages live in player profiles. |
| `system_status.json` | Legacy/reference status data. |
| `files_data.json` | Legacy file demo data for the old `/files/<folder>` route. |
| `users-a.json` | Legacy user backup/reference. |
| `interface_template.json` | Legacy interface reference. |

## Rule Of Thumb

If you want to change gameplay/runtime content, update SQLite through the sync
tool or runtime APIs. Static JSON is content in the repository, not a live
database.

