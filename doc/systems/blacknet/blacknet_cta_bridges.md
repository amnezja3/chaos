# BlackNet CTA Bridges

Sprint 82.5 adds the first central CTA router for BlackNet signals.

BlackNet still does not create its own market, operation engine, messenger,
audio player or map runtime. Every CTA either uses an existing CHAOS mechanism
or returns a controlled message.

## Contract

Signals are routed by:

```json
{
  "cta_action": "open_exchange_market",
  "cta_target": "ghost_exchange",
  "cta_target_id": "gps"
}
```

The renderer must not parse button text.

## Active Bridges

* `open_googleplex` and `open_googleplex_search`
  * opens the existing Googolplex tab,
  * fills the existing search field when a query is available,
  * never buys a product automatically.

* `open_ghost_exchange`, `open_exchange_market`, `open_exchange_category`
  * opens the existing Ghost Exchange tab,
  * can announce the requested sector/category,
  * never lists, sells or buys data automatically.

* `open_map`, `open_map_region`, `focus_map_target`, `show_hotspot`
  * opens the existing map app,
  * stores a lightweight focus hint for existing map runtime,
  * does not start an operation.

* `open_cyberner`, `open_cyberner_thread`
  * opens the existing Cyberner app,
  * uses `openEmailChatWith(peer)` only when a peer/thread is supplied.

* `open_radio`
  * opens the existing Ghost Hack Radio app,
  * can load a concrete channel when the signal carries `cta_target_id` or
    `metadata.channel_id`.

* `open_blacknet_detail`, `open_blacknet_dossier`, `open_blacknet_report`
  * shows a short controlled BlackNet detail through existing system messages.

* `teleport_to_hotspot`
  * requires confirmation,
  * uses the existing profile position and map delta flow,
  * accepts only whitelisted BlackNet hotspots,
  * does not create a second travel or map movement system.

## Guarded Bridges

* `start_operation`, `accept_blacknet_job`
  * require confirmation,
  * do not create a second operation model.

* `play_radio_podcast`
  * uses `GhostRadio.playPodcast()` only if that method exists,
  * otherwise opens Ghost Hack Radio and returns a controlled message.

* `none`
  * informational signal,
  * does not mark the signal as captured.

## Diagnostics

The router logs:

* `signal_id`,
* `source`,
* `cta_action`,
* `cta_target`,
* `cta_target_id`,
* validation result,
* confirmation/cancel state,
* success/error state,
* duration.

Diagnostics are console-only and must not block gameplay.

## Safety Rules

* Unknown `cta_action` returns a controlled warning.
* Expired signals return a controlled warning.
* CTA actions that change world state must be confirmed.
* No CTA may create a parallel market, operation system, messenger or audio
  player.
* BlackNet remains a signal bridge, not a source of truth.
