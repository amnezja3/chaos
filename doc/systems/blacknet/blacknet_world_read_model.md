# BlackNet World Read Model

Sprint 79 prepares BlackNet for future world-aware signals without adding a
backend endpoint, poller, AI generator or direct map/profile sync.

BlackNet v0 remains:

```text
static/local signals
↓
renderBlackNet()
```

Sprint 81 implements the first concrete runtime form of this idea as:

```text
existing profile/catalog/radio facts
↓
blacknet_world_facts
↓
future publisher
```

Artifact:

```text
GET /api/blacknet/world-facts
doc/systems/blacknet/blacknet_world_facts.md
```

The endpoint is read-only and is not consumed by the BlackNet UI yet.

Future BlackNet should become:

```text
existing snapshots / cache / delta-feed
↓
blacknet_world_digest
↓
local blacknet_signal contract
↓
renderBlackNet()
```

## Rule

`blacknet_world_digest` is a read model.

It is not a source of truth and must not calculate gameplay state in a request.
It can only summarize facts that already exist in current systems.

BlackNet must not call:

* `sync_session_profile()`,
* heavy map refresh endpoints,
* territory rebuilds,
* operation finalizers,
* Ghost Exchange settlement,
* AI generation.

## Digest Contract v0

```json
{
  "schema": 1,
  "generated_at": "2026-07-11T00:00:00Z",
  "expires_at": "2026-07-11T00:10:00Z",
  "source_versions": {
    "wallet": 0,
    "storage": 0,
    "apps": 0,
    "mail": 0,
    "ghost_exchange": 0,
    "operations": 0,
    "map": 0
  },
  "facts": []
}
```

## Digest Fact v0

```json
{
  "id": "gx:gps:demand:1845",
  "source": "ghost_exchange",
  "severity": "medium",
  "topic": "market",
  "region": "Warszawa",
  "title": "GPS demand spike",
  "metric_label": "potential price",
  "metric_value": "+34%",
  "stat": "62 packets in motion",
  "timer": "08:18",
  "cta_action": "open_ghost_exchange",
  "cta_target": "gps",
  "created_at": "2026-07-11T00:00:00Z"
}
```

Required fields:

* `id`
* `source`
* `severity`
* `topic`
* `title`
* `created_at`

Optional fields:

* `region`
* `metric_label`
* `metric_value`
* `stat`
* `timer`
* `cta_action`
* `cta_target`
* `expires_at`

## Sources

Potential future sources:

| Source | Existing truth | Safe future input |
| --- | --- | --- |
| Ghost Exchange | `profile.market_history`, summary payload | cached market summary / `ghost_exchange.*` deltas |
| Operations | `profile.operations`, `/api/operations` summary | cached operations summary / operations deltas |
| Map regions | map target and area stores | cached map summary / map deltas |
| PvP activity | territory conflict data | cached conflict summary |
| Cyberner/System | `mail_store`, `system_messages` | unread/thread/system-message deltas |
| Radio | `meta.channel` contracts | local radio channel metadata |

## Mapping To `blacknet_signal`

Digest facts do not replace `blacknet_signal`. They can be converted into the
existing local signal contract.

| Digest field | Signal field |
| --- | --- |
| `id` | `id` |
| `source` | `source` |
| `topic` | `channel` |
| `title` | `title` |
| `metric_label` | `label` |
| `metric_value` | `value` |
| `stat` | `stat` |
| `timer` | `timer` |
| `cta_action` | `cta_action` |
| `cta_target` | `cta_target` |
| `severity` | priority / tone |

## Source Mapping

| Source | Tone | CTA |
| --- | --- | --- |
| `ghost_exchange` | cyan / amber | `open_ghost_exchange` |
| `operations` | lime / amber | `open_map` |
| `map` | lime / red | `open_map` |
| `pvp` | red | `open_map` |
| `cyberner` | cyan | `open_cyberner` |
| `system` | amber / red | disabled or source-specific |
| `radio` | cyan | `open_radio` |

## Severity Mapping

| Severity | Meaning | Priority |
| --- | --- | --- |
| `low` | background signal | low |
| `medium` | useful signal | normal |
| `high` | important trend | high |
| `critical` | world alert / PvP / risk | highest |

The signal roll can sort by severity in the future, but Sprint 79 does not
change current local ordering.

## Retention And Fallback

The digest must have short retention. Recommended v0:

* keep latest digest only,
* or keep last 3-5 generated digests for diagnostics,
* digest expires after 5-15 minutes.

If digest is missing, empty or stale:

* keep using `static/blacknet_signals.json`,
* show no error to the player,
* do not trigger heavy runtime rebuilds.

## Future Generation Rules

When generation is added in a future sprint:

* generate digest after existing world events, not from BlackNet request,
* prefer delta-feed/cache inputs,
* never use BlackNet UI load as a reason to rebuild map/profile,
* AI can summarize digest facts later, but AI is not part of Sprint 79.

## Sprint 81 Update

`blacknet_world_facts` is the first versioned snapshot of aggregated world facts.

It currently reads:

* operations from stored profiles,
* Ghost Exchange sales from market history,
* Googleplex catalog statistics,
* Ghost Hack Radio channel metadata,
* lightweight system-message counts.

It does not generate signals and does not replace `static/blacknet_signals.json`.

## Sprint 82 Update

`blacknet_world_signals` is the first deterministic publisher output built from
`blacknet_world_facts`.

The read path is now:

```text
existing runtime models
↓
blacknet_world_facts
↓
deterministic publisher rules
↓
blacknet_world_signals
↓
renderBlackNet()
```

The publisher uses thresholds, deterministic ids, CTA validation and current
fact expiry. It does not store generated signals as a new source of truth.

The BlackNet frontend loads generated world signals and local static signals
together. Local static signals remain the fallback when generated signals are
empty or unavailable.

## Sprint 83 Update

`blacknet_ollama_outbox` is the controlled export package for the future Ollama
worker.

The read path is:

```text
blacknet_world_facts
↓
blacknet_world_signals
↓
blacknet_ollama_outbox
```

The outbox is not a new source of truth. It is a sanitized editorial package
with fact ids, selected signals, allowed CTA actions, limits and forbidden
claims.

Details:

```text
doc/systems/blacknet/blacknet_ollama_outbox.md
```
