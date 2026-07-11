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
