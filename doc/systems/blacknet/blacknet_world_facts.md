# BlackNet World Facts Snapshot

Sprint 81 adds the first runtime read model for world facts used by future
BlackNet publishers.

This is not a signal publisher and not an AI layer.

## Runtime Contract

Endpoint:

```text
GET /api/blacknet/world-facts
```

The endpoint requires an active session and returns:

```json
{
  "success": true,
  "snapshot": {
    "schema": 1,
    "snapshot_type": "blacknet_world_facts",
    "version": "hash",
    "generated_at": "2026-07-11T12:00:00Z",
    "expires_at": "2026-07-11T12:10:00Z",
    "source_versions": {},
    "facts": [],
    "diagnostics": {}
  }
}
```

## Fact Contract

Every fact uses the Sprint 81 shape:

```json
{
  "fact_id": "bnf:source:type:hash",
  "fact_type": "operations_active_count",
  "category": "operations",
  "region_id": "global",
  "subject_id": "operations",
  "value": 12,
  "previous_value": null,
  "change_percent": 0,
  "importance": 75,
  "importance_label": "high",
  "confidence": 0.95,
  "observed_at": "2026-07-11T12:00:00Z",
  "expires_at": "2026-07-11T12:10:00Z",
  "source_system": "operations",
  "metadata": {}
}
```

## Sources v0

Sprint 81 aggregates only safe, existing data:

* `operations` from stored profile operation lists,
* `ghost_exchange` from `market_history` and `files.market` transactions,
* `googleplex` from the existing app/product catalog,
* `radio` from local `meta.channel` contracts and MP3 counts,
* `system` from lightweight system-message counts.

## Safety Rules

The snapshot must not call:

* `sync_session_profile()`,
* operation finalizers,
* Ghost Exchange settlement,
* map territory rebuilds,
* AI generation,
* frontend rendering code.

The snapshot does not include:

* passwords,
* salts,
* private message bodies,
* full profiles,
* full map payloads.

## Failure Policy

Each source is isolated.

If one source fails:

* the snapshot is still returned,
* the failed source is marked in `diagnostics.sources`,
* other facts remain usable.

## Relationship To Future Sprints

Sprint 81 only creates facts.

Sprint 82 converts selected facts into deterministic BlackNet signals through
`blacknet_world_signals`.

Sprint 83 may export selected facts into an Ollama outbox.

Sprint 84 may ingest validated AI-enriched signals.

## Sprint 82.6 Update

Sprint 82.6 adds the first real activity snapshot layer for BlackNet.

The facts builder now behaves like a lightweight runtime daemon:

```text
world movement / BlackNet request
↓
short TTL cache
↓
existing world truth
↓
blacknet_world_facts
```

The request path still does not create gameplay state. It only reads existing
models and caches the read model briefly so BlackNet does not rebuild world
facts on every UI open.

New safety rule:

* if there are no publishable real facts, the publisher emits `out_of_signal`;
* local static posters must not pretend that a real hotspot exists;
* district names are not generated from coordinates or external APIs.

New fact type:

```text
operation_hotspot_activity
```

This fact is built from active operations attached to real map targets. It uses:

* `target_id`,
* target label/name,
* target coordinates when available,
* active operation count,
* operation ids,
* operation type counts.

Example:

```json
{
  "fact_type": "operation_hotspot_activity",
  "source_system": "operations",
  "category": "Piekarnia Putka",
  "subject_id": "poi-putka",
  "value": 2,
  "metadata": {
    "target_id": "poi-putka",
    "target_label": "Piekarnia Putka",
    "lat": 52.22001,
    "lng": 21.01002,
    "operation_count": 2
  }
}
```

This is the replacement direction for mock labels such as `HOTSPOT / MOKOTOW`.

## Sprint 82.7 Update

Sprint 82.7 extends the map side of the world facts contract.

New fact types:

```text
target_operation_burst
conflict_target_alert
contested_area_alert
```

`target_operation_burst` is emitted when the operations aggregator sees more
than one active operation attached to the same real map target.

`conflict_target_alert` is emitted from `territory_conflict_store.list_active()`
when an active conflict contains a concrete target. The fact carries:

* stable `target_id`,
* target label,
* target coordinates when available,
* conflict keys,
* participant count,
* conflict / contested status.

`contested_area_alert` is emitted only when conflicts exist but no safe target
can be extracted. It does not invent coordinates.

Safety rule:

* BlackNet must not derive district names from lat/lng.
* BlackNet must not call an external geocoder.
* A missing conflict target produces an area-level signal or no signal, not a
  fake hotspot.

## Sprint 82.8 Update

Entity-oriented facts now carry enough metadata for CTA bridges to open existing
CHAOS systems without guessing.

Ghost Exchange top-sector facts include:

* `sector_id`,
* `sector_key`,
* `sector_label`,
* `market_category`,
* `volume_mb`,
* `sold_today`,
* `average_price`,
* `cta_target_id`.

The top-sector fact is emitted only for sectors known to the Ghost Exchange
sector contract.

Googleplex facts include the featured real catalog entity:

* `product_id`,
* `product_name`,
* `product_type`,
* `price`,
* `category`,
* `cta_query`.

Radio facts include a concrete BlackNet radio track:

* `channel_id`,
* `channel_name`,
* `track_file`,
* `track_title`,
* `track_index`,
* `track_count`.

System-message facts include the Cyberner WORLD thread target:

* `thread_scope = group`,
* `thread_peer = global`,
* `thread_channel = world`.

If a source cannot provide a real entity for a family, that family should not
publish a fake signal. The publisher can fall back to `out_of_signal`.
