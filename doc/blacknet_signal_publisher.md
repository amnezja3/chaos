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
  "cta_action": "open_ghost_exchange",
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

Frontend rule:

* if `out_of_signal` is present in `world_generated`, local static signals are
  not merged into the visible signal roll;
* if the world endpoint fails completely, local static signals may still be used
  as a compatibility fallback until Sprint 82.9 retires production mocks.

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

## Out Of Scope

Sprint 82 does not:

* call Ollama,
* create digest outbox files,
* create missions,
* change market settlement,
* change Ghost Exchange,
* replace local static signals,
* add a new store for signals.
