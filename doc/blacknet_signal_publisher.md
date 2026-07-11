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

## Out Of Scope

Sprint 82 does not:

* call Ollama,
* create digest outbox files,
* create missions,
* change market settlement,
* change Ghost Exchange,
* replace local static signals,
* add a new store for signals.
