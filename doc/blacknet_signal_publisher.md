# BlackNet Deterministic Signal Publisher

Sprint 82 adds a deterministic publisher that turns `blacknet_world_facts` into
ready BlackNet signals without AI.

The publisher is not a new source of truth. It reads the Sprint 81 fact snapshot
and emits a presentation snapshot:

```text
blacknet_world_facts
↓
qualification rules
↓
ranking
↓
dedupe
↓
validated CTA
↓
blacknet_world_signals
```

## Endpoint

```text
GET /api/blacknet/world-signals
```

The endpoint requires a logged-in session and returns:

```json
{
  "success": true,
  "snapshot": {
    "schema": 1,
    "snapshot_type": "blacknet_world_signals",
    "source": "world_generated",
    "version": "...",
    "world_facts_version": "...",
    "generated_at": "2026-07-11T12:00:00Z",
    "signals": [],
    "diagnostics": {}
  }
}
```

## Signal Contract

Generated signals keep the same frontend shape as local static BlackNet signals:

```json
{
  "id": "world-...",
  "source": "world_generated",
  "signal_type": "market_watch",
  "fact_id": "bnf:...",
  "world_version": "...",
  "channel": "GHOST MARKET WATCH",
  "title": "RYNEK DANYCH / 7D",
  "label": "OBROT HC",
  "value": "+1200 HC",
  "stat": "32 PLIKOW / 400 MB",
  "timer": "00:09",
  "tone": "cyan",
  "layout": 2,
  "cta": "OTWORZ GHOST EXCHANGE",
  "cta_action": "open_exchange_market",
  "cta_target": "ghost_exchange",
  "radar": {
    "sides": 2,
    "nodes": []
  }
}
```

## Rules v0

Sprint 82 maps only known fact types:

* `operations_active_count` -> `operation_activity`
* `operations_top_type` -> `regional_activity`
* `market_sales_7d` -> `market_watch`
* `market_top_sector_7d` -> `data_demand`
* `googleplex_catalog_size` -> `product_opportunity`
* `radio_channels_available` -> `radio_promotion`
* `system_messages_24h` -> `system_incident`

Facts below rule thresholds do not publish signals.

Expired facts do not publish signals.

## CTA Safety

Generated signals may only use approved `cta_action` values:

* `open_map`
* `open_ghost_exchange`
* `open_googleplex`
* `open_cyberner`
* `open_radio`
* `open_exchange_market`
* `open_exchange_category`
* `open_googleplex_search`
* `open_cyberner_thread`
* `play_radio_podcast`

CTA is selected by rule, not by button text.

## Frontend

BlackNet loads:

```text
static/blacknet_signals.json
+
/api/blacknet/world-signals
```

The UI merges generated signals before local static signals and dedupes by
signal id. If the world endpoint fails or returns no signals, local static
signals remain the fallback.

There is no BlackNet poller in Sprint 82.

## Sprint 82.6 Update

The publisher now has an explicit empty-world state:

```text
out_of_signal
```

If world facts exist but none of them can produce a real signal, or if there are
no facts at all, the publisher returns one neutral BlackNet signal:

```json
{
  "signal_type": "out_of_signal",
  "title": "OUT OF SIGNAL",
  "cta_action": "none"
}
```

This is intentional. BlackNet must not fill an empty world feed with mock
hotspots such as `HOTSPOT / MOKOTOW`.

Frontend rule after Sprint 82.9:

* if `out_of_signal` is present in `world_generated`, local static signals are
  not merged into the visible signal roll;
* if the world endpoint fails completely, the UI shows a local client-side
  `OUT OF SIGNAL` state;
* local static signals may be loaded only when a dev/demo flag is explicitly
  enabled.

New generated signal:

```text
operation_hotspot_activity
```

It is created from `operation_hotspot_activity` facts and points to an existing
map target through `focus_map_target`.

## Sprint 82.7 Update

The deterministic publisher now understands map/conflict signal families:

```text
target_operation_burst
conflict_target_alert
contested_area_alert
```

`target_operation_burst` and `conflict_target_alert` both use:

```text
cta_action = focus_map_target
```

and rely on `cta_target_id` from the fact metadata. The publisher does not infer
targets from rendered text.

`contested_area_alert` uses:

```text
cta_action = open_map
```

because it represents conflict activity without a safe individual target.

These rules keep BlackNet inside the existing map runtime. They do not create a
second target registry, second map store or synthetic district catalog.

## Sprint 82.8 Update

Entity CTA families no longer point to mock text.

Radio signals use:

```text
cta_action = play_radio_podcast
metadata.channel_id
metadata.track_file
metadata.track_index
metadata.track_title
metadata.track_count
```

The frontend opens Ghost Hack Radio and asks the existing `GhostRadio` module to
load the indicated channel and MP3 track.

Googleplex signals use:

```text
cta_action = open_googleplex_search
metadata.product_id
metadata.product_name
metadata.product_type
metadata.price
metadata.category
```

The frontend opens the existing Googleplex tab and searches for the real product
name from the catalog.

Ghost Exchange signals use:

```text
cta_action = open_exchange_market
cta_action = open_exchange_category
metadata.sector_key
metadata.sector_label
metadata.market_category
```

The top-sector signal is published only when the sector exists in the current
Ghost Exchange sector contract. Invalid sector mappings are skipped instead of
creating a broken filter.

Cyberner system signals use:

```text
cta_action = open_cyberner_thread
metadata.thread_scope = group
metadata.thread_peer = global
metadata.thread_channel = world
```

The frontend opens the existing WORLD channel, not a private contact named
`cyberner`.

## Sprint 82.9 Update

BlackNet production runtime now uses the real feed only:

```text
/api/blacknet/world-signals
```

The static file:

```text
static/blacknet_signals.json
```

is no longer loaded by default. It is a dev/demo fixture only and must be
enabled explicitly on the frontend by one of:

```text
?blacknet_demo=1
?blacknet_static=1
localStorage.blacknet_static_signals = "1"
window.BLACKNET_STATIC_SIGNAL_FIXTURE = true
```

If the real feed is empty, invalid or temporarily unavailable, the frontend must
show `OUT OF SIGNAL` instead of merging local posters into the roll.

All generated signals expose a stable:

```text
entity_id
```

derived from the real target/product/channel/sector/thread entity. `entity_id`
is not a display label and should not be inferred from the rendered title.

## Out Of Scope

Sprint 82 does not:

* call Ollama,
* create digest outbox files,
* create missions,
* change market settlement,
* change Ghost Exchange,
* replace local static signals,
* add a new store for signals.
