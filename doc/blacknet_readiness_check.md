# BlackNet Readiness Check

Sprint 80 closes the first BlackNet prototype runtime stage.

Scope:

```text
Sprint 76.1 layout engine
Sprint 77 CTA bridge
Sprint 78 local signal source
Sprint 79 world read model prep
```

## Runtime Status

BlackNet v0 is a stable local signal front.

It is not:

* a second Googleplex,
* a second Ghost Exchange,
* a mission system,
* a market,
* a notification center,
* a backend poller,
* an AI generator.

## Current Data Flow

```text
static/blacknet_signals.json
↓
normalizeBlacknetSignal()
↓
renderBlackNet()
↓
CTA bridge to existing systems
```

## CSS Ownership

Active BlackNet UI classes are owned by:

```text
static/css/blacknet.css
```

The active runtime uses:

* `.blacknet-stage`
* `.bn-*`

Sprint 80 removed the old dead `.blacknet-*` shell/carousel block from
`style.css`. The remaining `style.css` BlackNet rules are only WebDragons
wrapper rules such as hiding the old header/search/tabs while the BlackNet tab
is active.

## Responsive Checkpoints

Manual checkpoints for WebDragons window width:

| Width | Expected |
| --- | --- |
| 1200 px | full two-column composition, CTA visible |
| 1000 px | desktop composition, no clipped CTA |
| 904 px | desktop composition still stable |
| 900 px | transition to narrow composition without blank screen |
| 860 px | narrow composition, single signal remains readable |
| 700 px | compact signal roll, CTA and timer visible |
| 520 px | mobile composition, absolute timer/CTA fit |
| 430 px | smallest mobile composition, no horizontal scroll |

Acceptance:

* no black screen,
* no old search/header in BlackNet,
* title wraps instead of forcing horizontal overflow,
* metric remains on radar,
* timer does not hide CTA,
* CTA remains clickable,
* navigation works in four directions,
* six local signal layouts render.

## CTA Bridge

Current supported actions:

| `cta_action` | Behavior |
| --- | --- |
| `open_googleplex` | switch WebDragons to Googleplex |
| `open_ghost_exchange` | switch WebDragons to Ghost Exchange |
| `open_map` | open existing map app |
| `open_cyberner` | open existing Cyberner app |
| `open_radio` | open existing Ghost Hack Radio app |

CTA is selected by `cta_action`, never by button label.

## Fallbacks

If local signals cannot be loaded:

* WebDragons remains open,
* BlackNet shows an empty/local source error state,
* no backend request is attempted,
* no heavy profile/map sync is triggered.

If a future digest is missing or stale:

* fallback remains `static/blacknet_signals.json`.

## Future Mini-Sprints

Recommended next BlackNet branches:

1. BlackNet AI Digest
   * summarize existing world facts,
   * use `blacknet_world_digest`,
   * do not generate from UI request.
2. BlackNet Radio Hooks
   * connect signals with Ghost Hack Radio channels,
   * do not rebuild the audio player.
3. BlackNet Cyberner Thread
   * open related Cyberner thread for signal discussion,
   * use existing Cyberner flow.
4. BlackNet Market Rumors
   * publish rumors based on Ghost Exchange/Googleplex facts,
   * mark uncertainty clearly.

## Status

BlackNet v0 is ready as a local/static information front.

Future work can add world data through digest/cache/delta-feed without changing
the 76.1 signal roll engine.

